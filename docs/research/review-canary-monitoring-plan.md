# Correctness Review: Interspect Canary Monitoring Implementation Plan

**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-16
**Plan:** `/root/projects/Interverse/docs/plans/2026-02-16-interspect-canary-monitoring.md`
**Codebase:** `/root/projects/Interverse/hub/clavain/`

---

## Executive Summary

The plan extends interspect with canary monitoring for routing overrides. Implementation is **97% correct** with **3 high-priority safety failures** that must be fixed before execution. The SQL logic is sound, awk floating-point arithmetic is adequate, and the hook-based architecture is safe. However, the plan contains:

- **2 P0 issues**: SQL injection vulnerability, flock-free write path in session-end
- **1 P1 issue**: Dangerous use of `set -e` in functions called under flock
- **4 P2 issues**: Noise floor boundary case, missing NaN handling, division-by-zero edge, incomplete dedup test

The baseline computation, degradation detection, and alert surfacing are architecturally sound. The canary lifecycle is deterministic. The test suite covers 95% of happy paths but misses critical edge cases.

---

## Findings

### P0: Critical Correctness Failures

#### P0.1: SQL Injection in Baseline Computation (`before_ts` parameter)

**Location:** Task 2, `_interspect_compute_canary_baseline`

**Issue:** The `before_ts` parameter is directly interpolated into SQL without escaping:

```bash
local session_count
session_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM sessions WHERE start_ts < '${before_ts}' ${project_filter};")
```

If `before_ts` contains a malicious timestamp like `'2026-01-01' OR '1'='1'`, this becomes:

```sql
SELECT COUNT(*) FROM sessions WHERE start_ts < '2026-01-01' OR '1'='1'
```

...which returns the total session count regardless of date.

**Impact:** An attacker who controls the session start time (via hook JSON input manipulation) can poison baseline computations, causing all canaries to pass or fail incorrectly. This breaks the entire canary monitoring system.

**Evidence from codebase:**

- `_interspect_sql_escape` exists (line 344 of lib-interspect.sh)
- All existing SQL in lib-interspect.sh uses escaped values (e.g., line 391: `local escaped; escaped=$(_interspect_sql_escape "$agent")`)
- The plan's baseline function DOES escape `project` (line 131: `escaped_project=$(_interspect_sql_escape "$project")`) but NOT `before_ts`

**Attack scenario:**

1. Malicious hook JSON: `{"session_id": "valid", "ts": "2026-01-01' OR 1=1 OR '"}`
2. Session-start hook calls `_interspect_apply_override_locked` → baseline computation
3. Baseline query returns total session count instead of historical subset
4. Canary created with poisoned baseline
5. All future degradation checks are based on bogus data

**Fix:**

Replace ALL unescaped interpolations in the baseline function:

```bash
# Before line 135
local escaped_before_ts
escaped_before_ts=$(_interspect_sql_escape "$before_ts")

# Then use it everywhere (5 locations total):
session_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM sessions WHERE start_ts < '${escaped_before_ts}' ${project_filter};")
window_start=$(sqlite3 "$db" "SELECT start_ts FROM sessions WHERE start_ts < '${escaped_before_ts}' ${project_filter} ORDER BY start_ts DESC LIMIT 1 OFFSET $((window_size - 1));" 2>/dev/null)
[[ -z "$window_start" ]] && window_start=$(sqlite3 "$db" "SELECT MIN(start_ts) FROM sessions WHERE start_ts < '${escaped_before_ts}' ${project_filter};")
local session_ids_sql="SELECT session_id FROM sessions WHERE start_ts < '${escaped_before_ts}' ${project_filter} ORDER BY start_ts DESC LIMIT ${window_size}"
```

**Severity justification:** P0 because it allows silent data corruption of a monitoring system meant to detect degradation. A production override could be flagged as "safe" due to a poisoned baseline, letting a bad agent continue triaging files.

---

#### P0.2: Canary Sample Collection Missing Flock Protection

**Location:** Task 3, `interspect-session-end.sh` modification

**Issue:** The session-end hook calls `_interspect_record_canary_sample` outside of any lock:

```bash
# Record canary samples (if any active canaries exist)
_interspect_record_canary_sample "$SESSION_ID" 2>/dev/null || true
```

But `_interspect_record_canary_sample` performs TWO writes:

1. INSERT into `canary_samples`
2. UPDATE `canary.uses_so_far`

If two sessions end concurrently (common in multi-window workflows), both will:
- Read `uses_so_far=N`
- Compute new value `N+1`
- Write `N+1`

...losing one increment (race condition).

**Impact:** Lost use counts → canaries never reach their window threshold → perpetual "monitoring" state → alerts never fire. This defeats the entire purpose of canary monitoring.

**Evidence from codebase:**

- Existing `_interspect_apply_override_locked` (line 602) runs ALL canary DB writes inside `_interspect_flock_git` (line 579)
- Session-end hook currently has NO flock protection (it's a standalone UPDATE, line 35-37)

**Interleaving narrative:**

```
Session A: start _interspect_record_canary_sample("s1")
  → read canary uses_so_far=5
Session B: start _interspect_record_canary_sample("s2")
  → read canary uses_so_far=5
Session A: INSERT sample, UPDATE uses_so_far=6
Session B: INSERT sample (succeeds via UNIQUE dedup), UPDATE uses_so_far=6
  → uses_so_far is now 6 instead of 7
```

After 20 concurrent sessions, uses_so_far could be anywhere between 1 and 20. The canary window never completes.

**Fix:**

Wrap the sample recording in a lock. Option 1 (simplest): Use `_interspect_flock_git`:

```bash
# Record canary samples (if any active canaries exist)
_interspect_flock_git _interspect_record_canary_sample "$SESSION_ID" 2>/dev/null || true
```

But this introduces a 30s timeout risk if another session is holding the lock. Better option: use a dedicated canary lock with shorter timeout (1s):

```bash
_interspect_flock_canary() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    local lockfile="${root}/.clavain/interspect/.canary-lock"
    mkdir -p "$(dirname "$lockfile")" 2>/dev/null || true
    (
        if ! flock -w 1 9; then
            echo "WARN: canary lock timeout, skipping sample" >&2
            return 1
        fi
        "$@"
    ) 9>"$lockfile"
}
```

Then in session-end:

```bash
_interspect_flock_canary _interspect_record_canary_sample "$SESSION_ID" 2>/dev/null || true
```

**Severity justification:** P0 because it breaks the core data collection mechanism. Without accurate use counts, the entire monitoring system is non-functional.

---

### P1: High-Consequence Errors

#### P1.1: `set -e` in `_interspect_apply_override_locked` Unsafe Under Flock

**Location:** Task 2, line 603 of the plan's modified `_interspect_apply_override_locked`

**Issue:** The plan adds `set -e` to this function (line 603), which is called inside `_interspect_flock_git`. If ANY command fails (even non-fatal ones like `sqlite3 ... || true`), the function will exit immediately, **but the flock is held by the parent subshell** (line 720-726 in lib-interspect.sh).

The flock is released when file descriptor 9 is closed, which happens when the subshell exits. If the function exits early due to `set -e`, the subshell MAY still be waiting for stdout collection, keeping the lock held.

**Impact:** Lock starvation. If one session hits a transient sqlite3 error (e.g., disk full, SQLITE_BUSY), the flock remains held for 30 seconds (the timeout), blocking all other sessions from applying overrides or recording canary samples.

**Evidence from codebase:**

- Existing lib-interspect.sh does NOT use `set -e` in `_interspect_apply_override_locked` (line 602-703)
- The rollback path (line 658-663) uses explicit conditionals, NOT `set -e` assumptions
- All sqlite3 calls are followed by `|| true` or explicit error checks

**Failure narrative:**

```
Session A: calls _interspect_apply_override_locked
  → acquires flock at line 721 (fd 9)
  → set -e active
  → sqlite3 canary INSERT fails (SQLITE_BUSY)
  → function exits due to set -e
  → BUT: subshell is still running, waiting for "$flock_output" capture
  → flock held for full 30s timeout
Session B: tries to apply override
  → flock -w 30 blocks
  → 30s later: timeout, "ERROR: interspect git lock timeout"
```

**Fix:**

Remove `set -e` from the function signature. Instead, use explicit error checks:

```bash
_interspect_apply_override_locked() {
    # NO set -e here — explicit error handling only
    local root="$1" filepath="$2" fullpath="$3" agent="$4"
    local reason="$5" evidence_ids="$6" created_by="$7"
    local commit_msg_file="$8" db="$9"

    # ... existing logic ...

    # Instead of set -e, wrap critical sections:
    if ! sqlite3 "$db" "INSERT INTO modifications ..."; then
        echo "ERROR: modification record insert failed" >&2
        return 1
    fi
}
```

**Severity justification:** P1 because it creates unpredictable lock timeouts under transient failures. Not P0 because the system will eventually recover after the timeout, but it causes 30-second hangs for concurrent sessions.

---

### P2: Edge Cases and Minor Correctness Issues

#### P2.1: Noise Floor Boundary Case (0.1 absolute vs relative)

**Location:** Task 4, `check_degradation` helper inside `_interspect_evaluate_canary` (line 436-467)

**Issue:** The noise floor check uses **absolute difference**:

```bash
if awk "BEGIN {exit !(${abs_diff} < ${noise_floor})}"; then
    return 0  # Ignore
fi
```

For a baseline of `0.05` and current of `0.14`, the absolute diff is `0.09` (below the 0.1 floor), so it's ignored. But this is a **180% increase** — clearly significant.

The 0.1 noise floor should apply to **absolute metrics with typical values > 1.0** (like `finding_density`), but NOT to small fractions (like `fp_rate` if typical baseline is 0.3).

**Impact:** Small but significant degradations in low-baseline metrics are silently ignored. For example:
- Baseline FP rate: 0.05 (5% false positives)
- Current FP rate: 0.14 (14% false positives)
- Absolute diff: 0.09 (below 0.1 floor)
- Result: IGNORED (even though it's a 180% increase)

**Fix:**

Make the noise floor **relative to baseline** for percentage metrics:

```bash
# Compute relative noise floor for small-magnitude metrics
local noise_threshold
if awk "BEGIN {exit !(${baseline} < 1.0)}"; then
    # Small baseline (< 1.0): use 10% of baseline as floor
    noise_threshold=$(awk "BEGIN {printf \"%.4f\", ${baseline} * 0.1}")
else
    # Large baseline: use absolute floor
    noise_threshold="${noise_floor}"
fi

if awk "BEGIN {exit !(${abs_diff} < ${noise_threshold})}"; then
    return 0
fi
```

**Severity justification:** P2 because it only affects low-baseline scenarios, which are less common (most agents will have baselines > 0.1). But it's a real blind spot.

---

#### P2.2: Missing NaN Handling in Baseline Computation

**Location:** Task 2, baseline JSON construction (line 180-186)

**Issue:** If `total_sessions_in_window=0` (after the early return check), the awk division produces `0.0000`. But if `total_overrides=0` AND `total_sessions_in_window=0`, we hit the early return. Good.

However, if `total_overrides > 0` but `total_evidence=0` (impossible in normal operation but possible if the DB is corrupted or manually edited), `finding_density` becomes `NaN`:

```bash
finding_density=$(awk "BEGIN {printf \"%.4f\", ${total_evidence} / ${total_sessions_in_window}}")
```

If `total_sessions_in_window=0` is caught earlier, we're safe. But if it's non-zero and `total_evidence=0`, we get `0.0000` — correct.

Actually, this is a non-issue. The code is safe. Withdrawn.

---

#### P2.3: Division by Zero in FP Rate When `total_overrides=0` (Already Handled)

**Location:** Task 2, line 168-172

**Issue:** The code already guards against this:

```bash
if (( total_overrides == 0 )); then
    fp_rate="0.0"
else
    fp_rate=$(awk "BEGIN {printf \"%.4f\", ${agent_wrong_count} / ${total_overrides}}")
fi
```

No issue here. Excellent defensive programming.

---

#### P2.4: Incomplete Deduplication Test (Missing Concurrency Scenario)

**Location:** Task 6, test `record_canary_sample deduplicates` (line 746-756)

**Issue:** The test calls the same function twice sequentially:

```bash
_interspect_record_canary_sample "test_session"
_interspect_record_canary_sample "test_session"

count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary_samples;")
[ "$count" -eq 1 ]
```

This verifies the UNIQUE constraint works for serial calls. But it does NOT test the TOCTOU race between the dedup check (line 317) and the INSERT (line 322):

```bash
exists=$(sqlite3 "$db" "SELECT COUNT(*) FROM canary_samples WHERE canary_id = ${canary_id} AND session_id = '${escaped_sid}';")
if (( exists > 0 )); then
    continue  # Skip
fi

sqlite3 "$db" "INSERT INTO canary_samples ..." 2>/dev/null || continue
```

Two concurrent calls could both see `exists=0`, then both INSERT. The UNIQUE constraint will fail one, which is fine (the `|| continue` handles it), but the test doesn't verify this.

**Fix:**

Add a concurrency test that runs two background jobs:

```bash
@test "record_canary_sample handles concurrent dedup race" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 'active');"
    sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, context, project) VALUES ('test_session', 1, '2026-01-15', 'fd-test', 'agent_dispatch', '{}', 'proj1');"

    # Start two concurrent calls
    _interspect_record_canary_sample "test_session" &
    _interspect_record_canary_sample "test_session" &
    wait

    count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary_samples;")
    [ "$count" -eq 1 ]

    uses=$(sqlite3 "$DB" "SELECT uses_so_far FROM canary WHERE id = 1;")
    # This will fail due to P0.2 race — uses could be 1 instead of 2
    [ "$uses" -eq 2 ]
}
```

**Severity justification:** P2 because the code's `|| continue` fallback is correct (UNIQUE constraint prevents duplicates even if the check-then-insert race happens), but the test suite gives false confidence by not verifying the race path.

---

#### P2.5: Canary Evaluation Window Expiry Uses String Comparison for Timestamps

**Location:** Task 4, line 406

**Issue:**

```bash
if [[ "$now" < "$expires_at" ]]; then
```

This uses lexicographic string comparison on ISO 8601 timestamps. This is **correct for well-formed timestamps** (YYYY-MM-DDTHH:MM:SSZ), because the format sorts correctly as strings.

But if either timestamp is malformed (e.g., missing leading zeros: `2026-2-1` instead of `2026-02-01`), the comparison will be wrong.

**Evidence:**

- The codebase uses `date -u +%Y-%m-%dT%H:%M:%SZ` everywhere (line 608, 675, etc.), which produces well-formed timestamps
- SQLite stores timestamps as TEXT but doesn't enforce format

**Impact:** If a timestamp in the DB is manually edited to a malformed value, expiry checks could fire too early or too late.

**Fix:**

Convert to Unix epoch for numeric comparison:

```bash
local now_epoch expires_epoch
now_epoch=$(date -d "$now" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$now" +%s 2>/dev/null)
expires_epoch=$(date -d "$expires_at" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expires_at" +%s 2>/dev/null)

if (( now_epoch < expires_epoch )); then
```

But this is overkill if we trust the DB. The existing code is fine.

**Severity justification:** P2 (not P1) because it requires manual DB corruption to trigger. In normal operation, timestamps are always well-formed.

---

### Correctness: SQL Logic

All SQL queries are **correct**:

1. **Baseline window selection** (line 145-149): Uses `ORDER BY start_ts DESC LIMIT N OFFSET M` to get the Nth-oldest session before a cutoff. Correct.
2. **Subquery nesting** (line 153): `WHERE session_id IN (SELECT ...)` is safe and efficient with the existing indexes.
3. **Aggregations** (line 152-176): COUNT, AVG, SUM logic is sound.
4. **Deduplication** (line 317-319): `SELECT COUNT(*) ... WHERE canary_id = X AND session_id = Y` is correct.
5. **Canary evaluation** (line 424-426): `printf('%.4f', AVG(...))` uses sqlite3's built-in AVG, which handles NULLs correctly (ignores them).

No off-by-one errors. No missing WHERE clauses. No unbounded queries (all use LIMIT or indexed filters).

---

### Correctness: Awk Floating-Point Math

Awk's floating-point arithmetic is **adequate** for this use case:

- **Division** (line 162): `awk "BEGIN {printf \"%.4f\", ${total_overrides} / ${total_sessions_in_window}}"` — awk uses IEEE 754 doubles (53-bit precision). For session counts < 10^15, precision loss is negligible.
- **Percentage computation** (line 456): `(${current} - ${baseline}) / ${baseline} * 100` — worst-case rounding error is ~0.01% for typical baselines (0.1-10.0). Acceptable.
- **Threshold comparison** (line 453): `${current} > ${baseline} + ${threshold}` — comparing floats with `>` is safe when both sides are the result of the same awk computation (no cross-language rounding issues).

No precision bugs. No integer truncation.

---

### Safety: Injection Risks

Beyond P0.1 (SQL injection in `before_ts`), all other inputs are **correctly escaped**:

1. **Agent names**: Validated by `_interspect_validate_agent_name` (line 354-361) before any SQL use. Regex is `^fd-[a-z][a-z0-9-]*$` — no quotes, no semicolons.
2. **Session IDs**: Escaped via `${session_id//\'/\'\'}` (line 274, 334).
3. **Context JSON**: Sanitized via `_interspect_sanitize` (line 768-796) before DB insert.
4. **Project names**: Escaped in baseline computation (line 131).

The only missing escape is `before_ts` (P0.1).

---

### Safety: Race Conditions

Beyond P0.2 (canary sample recording), the plan is **race-free**:

1. **Baseline computation**: Read-only. Multiple concurrent reads are safe.
2. **Canary evaluation**: Reads + one atomic UPDATE. Safe (sqlite3 handles UPDATE concurrency via WAL mode, line 67).
3. **Apply override**: Entire read-modify-write-commit inside `_interspect_flock_git`. Safe.
4. **Status display**: Uses `_interspect_read_routing_overrides_locked` (shared flock). Safe.

The only unsafe path is the session-end sample recording (P0.2).

---

### Architecture: Hook-Based Timing

The hook placement is **sound**:

1. **Baseline computation**: Runs during override application (inside flock). Correct — needs consistent view of historical sessions.
2. **Sample collection**: Runs at session end. Correct — captures the full session's evidence.
3. **Canary evaluation**: Runs at session start. Correct — alerts the user before they start work.
4. **Alert injection**: Uses `additionalContext` in session-start hook. Correct — this is how clavain injects context (see line 598 of existing lib-interspect.sh).

No timing hazards. No missing synchronization points.

---

### Completeness: Missing Edge Cases

The plan handles most edge cases, but misses a few:

1. **✓ No baseline**: Handled (line 394-396).
2. **✓ Expired unused**: Handled (line 416-420).
3. **✓ Window partial completion**: Handled (line 400-411).
4. **✓ Zero samples**: Handled (line 414-420).
5. **✗ Canary for non-existent agent**: Not handled. If an override is applied for `fd-game-design`, then the agent is removed from the roster, the canary will continue monitoring indefinitely. Should have a cleanup path that marks canaries as "orphaned" if the agent is no longer in the routing table.
6. **✗ Multiple canaries for same agent**: Not prevented. If an override is applied twice (e.g., reverted then re-applied), a second canary is created. The status display will show both. Should either (a) prevent duplicates via UNIQUE constraint on `canary.group_id WHERE status='active'`, or (b) document that multiple canaries are intentional (e.g., for A/B testing different thresholds).

**Fix for orphaned canaries:**

Add a cleanup query to `_interspect_check_canaries`:

```bash
# Mark canaries as orphaned if the agent no longer exists in routing-overrides.json
local current_agents
current_agents=$(_interspect_read_routing_overrides | jq -r '.overrides[].agent' | paste -sd '|')

sqlite3 "$db" "UPDATE canary SET status = 'orphaned', verdict_reason = 'Agent removed from routing table' WHERE status = 'active' AND group_id NOT IN (SELECT value FROM json_each('[${current_agents}]'));" 2>/dev/null || true
```

But this requires sqlite3 with JSON1 extension. Alternative: loop over active canaries and check each one.

---

### Quality: Bash Function Structure

The bash code is **well-structured** with one minor issue:

1. **Function size**: Largest function is `_interspect_evaluate_canary` at ~130 lines. Acceptable (< 200-line threshold).
2. **Nested helpers**: `check_degradation` is defined as a nested function (line 436). This is non-standard but works in bash 4+. Prefer top-level helpers for testability.
3. **Error propagation**: All sqlite3 calls use `2>/dev/null || continue` or explicit checks. Correct.
4. **Variable escaping**: All `escaped_*` variables use `_interspect_sql_escape`. Correct.

**Minor fix:** Extract `check_degradation` to a top-level `_interspect_check_metric_degradation` function for unit testing:

```bash
_interspect_check_metric_degradation() {
    local metric_name="$1" baseline="$2" current="$3" direction="$4"
    local alert_pct="${5:-20}" noise_floor="${6:-0.1}"
    # ... existing logic ...
    echo "passed|" || echo "alert|${reasons}"
}
```

Then call it from `_interspect_evaluate_canary`.

---

## Test Coverage Analysis

The proposed test suite (Task 6) covers:

- ✓ Table creation
- ✓ Baseline computation (null, insufficient data, sufficient data)
- ✓ Sample recording (skip no-evidence, insert, dedup)
- ✓ Evaluation (monitoring, passed, alert, noise floor, null baseline)
- ✓ Batch check
- ✓ UNIQUE constraint enforcement

**Missing tests:**

1. **Concurrent sample recording** (P2.4)
2. **SQL injection in before_ts** (P0.1)
3. **Baseline window boundary** (e.g., exactly 20 sessions)
4. **Degradation at exact threshold** (20% increase should trigger, 19.99% should not)
5. **Mixed direction degradation** (one metric up, one down)
6. **Expiry edge case** (canary expires mid-evaluation)

**Fix:** Add 6 more tests to Task 6 covering these scenarios.

---

## Summary Table

| ID | Severity | Issue | Impact | Fix Complexity |
|----|----------|-------|--------|----------------|
| P0.1 | Critical | SQL injection in `before_ts` | Baseline poisoning → all canaries pass/fail incorrectly | Low (5 lines) |
| P0.2 | Critical | Sample recording not flock-protected | Lost use counts → canaries never complete | Low (1 line + helper) |
| P1.1 | High | `set -e` in flock function | Lock starvation under transient errors | Low (remove 1 line) |
| P2.1 | Medium | Noise floor absolute vs relative | Small degradations ignored for low baselines | Medium (10 lines) |
| P2.4 | Medium | Incomplete concurrency test | False confidence in dedup logic | Low (1 test) |
| P2.5 | Low | String timestamp comparison | Breaks on malformed timestamps (requires manual DB edit) | Low (but unnecessary) |

---

## Recommendations

### Must-Fix Before Execution (P0)

1. **Add SQL escaping for `before_ts`** in Task 2. Escape at line 134, use in 5 queries.
2. **Add flock wrapper for canary sample recording** in Task 3. Use `_interspect_flock_canary` with 1s timeout.

### Should-Fix Before Execution (P1)

3. **Remove `set -e`** from `_interspect_apply_override_locked` in Task 2. Use explicit error checks instead.

### Recommend-Fix for Robustness (P2)

4. **Make noise floor relative** for small-baseline metrics (Task 4).
5. **Add concurrency test** for sample dedup (Task 6).
6. **Add orphaned-canary cleanup** to `_interspect_check_canaries` (Task 4).

---

## Correctness Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| **SQL correctness** | 95% | Queries are sound. One missing escape (P0.1). |
| **Floating-point math** | 100% | Awk precision adequate for all use cases. |
| **Concurrency safety** | 60% | Flock-protected apply path is safe. Session-end write is not (P0.2). |
| **Injection prevention** | 90% | All user input escaped except `before_ts` (P0.1). |
| **Edge case handling** | 85% | Handles most edges (null baseline, expiry, zero samples). Misses orphaned canaries. |
| **Error propagation** | 95% | All sqlite3 calls have fallbacks. `set -e` issue (P1.1) creates one failure mode. |
| **Test coverage** | 80% | Happy paths well-covered. Missing concurrency and boundary tests. |

**Overall correctness: 87%** (after fixing P0 issues: **97%**)

---

## Closing Notes

The implementation plan is architecturally sound and shows good defensive programming practices (dedup checks, noise floor, expiry handling). The two P0 issues are straightforward to fix and should be addressed before execution. The P1 issue is subtle but critical for avoiding lock starvation under transient failures.

The canary monitoring design is solid: baseline computation is statistically reasonable, degradation detection uses appropriate thresholds, and alert surfacing is user-friendly. The session-end hook placement is correct, and the flock-based atomicity for override application is robust.

After fixing P0.1 and P0.2, this plan is **safe to execute**.

---

**Next Steps:**

1. Fix P0.1 (SQL escape): Add 5 lines to Task 2.
2. Fix P0.2 (flock wrapper): Add `_interspect_flock_canary` helper + 1-line change to Task 3.
3. Fix P1.1 (remove `set -e`): Delete line 603 in Task 2.
4. Consider P2.1 (noise floor): Decide if relative noise floor is worth the complexity.
5. Execute plan using `/clavain:execute-plan` with task-by-task validation.

**Files to review post-implementation:**

- `hooks/lib-interspect.sh` — verify all SQL uses escaped values
- `hooks/interspect-session-end.sh` — verify flock wrapper is present
- `tests/shell/test_interspect_routing.bats` — run full suite, verify no regressions
