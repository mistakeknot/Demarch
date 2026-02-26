# Correctness Review: Interspect Pattern Detection + Propose Flow
**Plan:** `docs/plans/2026-02-23-interspect-pattern-detection-propose-flow.md`
**Library:** `os/clavain/hooks/lib-interspect.sh`
**Tests:** `os/clavain/tests/shell/test_interspect_routing.bats`
**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-23

---

## Invariants

Before findings: these are the correctness invariants that must remain unbroken.

1. **Dedup invariant.** A given agent must never have more than one entry in `routing-overrides.json` after a successful write.
2. **Commit-SHA invariant.** The last line of `_interspect_flock_git`'s stdout is always a 40-character SHA or `ALREADY_EXISTS`. The caller parses it with `tail -1` — anything else is a silent misread.
3. **Subshell isolation.** All code inside `(...)` passed to `_interspect_flock_git` runs in a subshell. Variable assignments there do not propagate to the caller's scope.
4. **Accumulation correctness.** `_interspect_get_overlay_eligible` must produce `agent_wrong_pct` that equals `total agent_wrong events / total override events` for each agent, considering ALL `override_reason` values, not just `agent_wrong`.
5. **Exit-code transparency.** Test assertions on exit codes are correct only when `run` is used; direct calls conflate exit code with side-effect success.
6. **Flock scope.** The lock protects only what runs inside the subshell passed to `_interspect_flock_git`. Both the locked body and its DB queries must execute before the subshell exits.

---

## Finding 1 — CRITICAL: `ALREADY_EXISTS` marker corrupts the commit-SHA parse

**Severity:** Data integrity / silent wrong-path execution

**Location:** `_interspect_apply_propose_locked` (plan lines 436-439) and `_interspect_apply_propose` caller (plan line 407).

### Description

`_interspect_apply_propose_locked` writes `ALREADY_EXISTS` to stdout and returns 0 when a duplicate is detected:

```bash
# plan, _interspect_apply_propose_locked, dedup branch
echo "INFO: Override for ${agent} already exists ..." >&2
echo "ALREADY_EXISTS"
return 0
```

The caller does:

```bash
# plan, _interspect_apply_propose, after flock
local commit_sha
commit_sha=$(echo "$flock_output" | tail -1)
echo "SUCCESS: Proposed excluding ${agent}. Commit: ${commit_sha}"
```

### Exact failure interleaving

1. Agent A calls `_interspect_apply_propose "fd-game-design" ...`.
2. Agent A holds the lock, finds the existing override, emits `ALREADY_EXISTS` to the subshell's stdout, returns 0.
3. `_interspect_flock_git` exits 0. `flock_output` equals `"ALREADY_EXISTS"`.
4. Back in `_interspect_apply_propose`: `exit_code=0` so the success branch runs.
5. `commit_sha=$(echo "ALREADY_EXISTS" | tail -1)` yields `"ALREADY_EXISTS"`.
6. The function prints `SUCCESS: Proposed excluding fd-game-design. Commit: ALREADY_EXISTS` — a lie. No proposal was written, yet the caller believes one was.
7. Any downstream logic that stores or displays this SHA (e.g., modification records, status pages) contains `"ALREADY_EXISTS"` as a SHA, which will fail any SHA-aware validation or lookup.

### Test gap

The test `"apply_propose skips if override already exists"` (plan) uses `run` and checks for `"already exists"` in output. It does NOT assert that `$output` does NOT contain `"SUCCESS"` or that the last line is not treated as a SHA. The assertion:
```bash
echo "$output" | grep -qi "already exists"
```
will match the stderr INFO line if stderr is mixed into `$output` by bats, but not necessarily. The test does not guard the caller's `commit_sha` variable at all.

### Fix

The locked function must communicate the skip condition differently from a successful commit. Two safe patterns:

**Option A: Distinct exit code.**
```bash
# In _interspect_apply_propose_locked, dedup branch:
echo "INFO: Override for ${agent} already exists (propose or exclude). Skipping." >&2
return 2   # distinct from 0 (success) and 1 (error)
```
Then in `_interspect_apply_propose`:
```bash
if (( exit_code == 2 )); then
    echo "INFO: Override for ${agent} already exists. Skipping."
    return 0
fi
if (( exit_code != 0 )); then
    ...
fi
```
`ALREADY_EXISTS` on stdout is then never emitted and `tail -1` is safe.

**Option B: Prefix sentinel on stdout (never parseable as SHA).**
```bash
echo "SKIP:ALREADY_EXISTS"
return 0
```
Caller pattern-matches `SKIP:` prefix before treating last line as SHA.

Option A is cleaner and matches the existing `apply_override_locked` convention (which uses `is_new` to skip re-inserting DB records but does NOT skip the commit — a different pattern, so be careful not to conflate).

---

## Finding 2 — HIGH: Subshell variable scope voids `_interspect_get_routing_eligible`'s SQLite queries

**Severity:** Correctness / silent wrong results

**Location:** `_interspect_get_routing_eligible` (plan Task 1, lines 99-128), specifically the `while IFS='|' read -r` pipeline.

### Description

The plan's implementation is:

```bash
_interspect_get_classified_patterns | while IFS='|' read -r src evt reason ec sc pc cls; do
    ...
    _interspect_is_routing_eligible "$src"
    ...
    if _interspect_override_exists "$src"; then
        continue
    fi
    ...
    total=$(sqlite3 "$db" "SELECT COUNT(*) ...")
    wrong=$(sqlite3 "$db" "SELECT COUNT(*) ...")
    pct=$(( total > 0 ? wrong * 100 / total : 0 ))
    echo "${src}|${ec}|${sc}|${pc}|${pct}"
done
```

In bash, the right-hand side of a pipe runs in a subshell. Inside the `while` loop:
- `_interspect_is_routing_eligible "$src"` calls `_interspect_load_confidence`, which reads from `$_INTERSPECT_CONFIDENCE_LOADED`. That global may or may not be set in the subshell (it is copied at subshell fork time if already set in the parent), but any changes made inside are lost.
- `_interspect_override_exists "$src"` calls `_interspect_read_routing_overrides` which calls `git rev-parse --show-toplevel`. This uses `$HOME` as set by the test. That works, but introduces a new `git` subprocess per row — one per classified pattern.
- The additional `sqlite3` queries for `total` and `wrong` per row are a correctness concern: `_interspect_is_routing_eligible` already queries `total` and `wrong` internally using the multi-variant source query (`source = 'fd-X' OR source = 'interflux:fd-X' OR source = 'interflux:review:fd-X'`). But `_interspect_get_routing_eligible` then runs a second, different query — `WHERE source = '${escaped}'` — that only counts the bare `fd-X` form. If evidence was stored under `interflux:fd-game-design`, the eligibility check passes (via `_interspect_is_routing_eligible`'s multi-variant query), but the `pct` reported in the output row will be computed from bare-name rows only — likely 0 — producing a misleading output row.

### Concrete example

1. Evidence is inserted as `source = 'interflux:fd-game-design'` (common when interflux dispatches the review).
2. `_interspect_get_classified_patterns` normalizes it to `fd-game-design` in its SELECT (via `SUBSTR`).
3. `_interspect_is_routing_eligible "fd-game-design"` checks `source = 'fd-game-design' OR source = 'interflux:fd-game-design' OR source = 'interflux:review:fd-game-design'` — finds rows, computes pct correctly, returns `"eligible"`.
4. `_interspect_get_routing_eligible` then runs `SELECT COUNT(*) FROM evidence WHERE source = '${escaped}'` — i.e. `WHERE source = 'fd-game-design'` — finds 0 rows (evidence is stored as `interflux:fd-game-design`).
5. `pct` = 0. Output row: `fd-game-design|6|3|3|0`. The caller sees 0% but the eligibility gate passed 80%+. This contradiction will confuse any downstream that trusts the pct field.

### Fix

Replace the redundant per-agent `sqlite3` queries with the values already available in the classified patterns row. `_interspect_get_classified_patterns` filters by `override` event + `agent_wrong` reason before grouping, so the `ec` column from the classified row is already the agent_wrong count for that (source, event, reason) tuple. If routing eligibility is required, the pct should be computed using the same multi-variant logic used in `_interspect_is_routing_eligible`, or at minimum use the same source variants:

```bash
# Replace the bare-name query with the multi-variant form:
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source='${escaped}' OR source='interflux:${escaped}' OR source='interflux:review:${escaped}') AND event='override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source='${escaped}' OR source='interflux:${escaped}' OR source='interflux:review:${escaped}') AND event='override' AND override_reason='agent_wrong';")
```

Even better: avoid the extra queries entirely. The classified patterns query already groups by `(norm_source, event, reason)`, so the row where `event='override'` and `reason='agent_wrong'` already gives `ec` = the agent_wrong count. Accumulating totals from classified pattern rows in the same way `_interspect_get_overlay_eligible` does (using associative arrays) would eliminate the per-row `sqlite3` calls and the source-variant mismatch.

---

## Finding 3 — HIGH: `agent_wrong` count only takes the last classified-row's `ec` per agent in `_interspect_get_overlay_eligible`

**Severity:** Data integrity / wrong eligibility decisions

**Location:** `_interspect_get_overlay_eligible` (plan Task 2, lines 221-252).

### Description

The accumulation loop is:

```bash
while IFS='|' read -r src evt reason ec sc pc cls; do
    [[ "$cls" == "ready" ]] || continue
    [[ "$evt" == "override" ]] || continue
    ...
    agent_total[$src]=$(( ${agent_total[$src]:-0} + ec ))
    agent_sessions[$src]=$sc
    agent_projects[$src]=$pc
    if [[ "$reason" == "agent_wrong" ]]; then
        agent_wrong[$src]=$ec     # <-- assignment, not accumulation
    fi
done < <(_interspect_get_classified_patterns)
```

`_interspect_get_classified_patterns` groups by `(norm_source, event, override_reason)`. An agent with two classified rows for override events — one for `agent_wrong` (ec=4) and one for `deprioritized` (ec=2) — will be seen in two loop iterations. On the second iteration, if `reason == 'agent_wrong'` again (unlikely with two rows for the same agent, but possible if sources vary), `agent_wrong[$src]` is overwritten not accumulated. More critically:

If the database has evidence rows stored as both `fd-game-design` (bare) and `interflux:fd-game-design`, the normalization in `_interspect_get_classified_patterns` maps both to `fd-game-design`. SQLite's `GROUP BY norm_source, event, override_reason` will merge them, so the classified output should have one row per (agent, event, reason) combination — the accumulation is fine in that case.

However, there is a genuine accumulation bug for `agent_sessions` and `agent_projects`. These are simple assignment (`=$sc`, `=$pc`), so only the last row's session/project count is stored. For the `agent_total` accumulation, `ec` is summed across all rows for that agent. But `sc` and `pc` are distinct counts across the *entire* evidence for that (agent, event, reason) group — not across all reasons. After accumulation, the output row reports `agent_sessions[$src]` which reflects only the last row's session count, not the union across all override reasons.

Consider:
- Row 1: `fd-overlay-test|override|agent_wrong|4|3|3|ready` (4 events, 3 sessions, 3 projects)
- Row 2: `fd-overlay-test|override|deprioritized|2|2|2|ready` (2 events, 2 sessions, 2 projects)

After the loop:
- `agent_total[fd-overlay-test]` = 6 (correct)
- `agent_wrong[fd-overlay-test]` = 4 (correct, set on row 1)
- `agent_sessions[fd-overlay-test]` = 2 (wrong — last row wins, should be max or distinct count)
- `agent_projects[fd-overlay-test]` = 2 (wrong — same issue)

The output row emits session/project counts from whichever classified row is processed last, not the maximum or union. If the confidence thresholds depend on session count (they do: `min_sessions=3`), using `2` instead of `3` may cause under-counting that incorrectly suppresses eligible agents. More importantly, the pct computation is correct (4/6 = 66%) but the session count shown to the caller is understated.

This is particularly relevant because `_interspect_get_overlay_eligible` does not itself re-check `_interspect_classify_pattern` — it trusts the `ready` classification from the classified patterns query, but that classification was per-row. An agent whose total across all override reasons passes the `min_events` threshold but whose individual rows do not may or may not be correctly classified as `ready`. In practice, if either row is `ready`, the agent appears; but if the agent's `agent_wrong` row alone is `ready` and the `deprioritized` row is `growing`, both are admitted, which is the correct behavior (the `ready` filter does apply per row).

### Fix

Track `agent_sessions` and `agent_projects` as running maximums:

```bash
agent_sessions[$src]=$(( ${agent_sessions[$src]:-0} > sc ? ${agent_sessions[$src]:-0} : sc ))
agent_projects[$src]=$(( ${agent_projects[$src]:-0} > pc ? ${agent_projects[$src]:-0} : pc ))
```

Or, if session/project counts need to be precise totals, run a direct DB query after the accumulation loop (one query per output agent, not per classified row), analogous to what `_interspect_is_routing_eligible` does for its multi-variant source count.

---

## Finding 4 — HIGH: `_interspect_get_routing_eligible` runs N SQLite queries inside a pipeline subshell with no flock

**Severity:** Concurrency / TOCTOU on override check

**Location:** `_interspect_get_routing_eligible`, the `_interspect_override_exists` call (plan line 114).

### Description

`_interspect_override_exists` reads `routing-overrides.json` without holding the git lock. This is documented as intentional for reads (`_interspect_read_routing_overrides` comments: "optimistic locking: accepts TOCTOU race for reads"). However, there is a subtle consequence specific to `_interspect_get_routing_eligible`:

1. Agent session A calls `_interspect_get_routing_eligible`. It reads the overrides file and sees no entry for `fd-game-design`. Proceeds to emit the row.
2. Concurrently, Agent session B calls `_interspect_apply_propose "fd-game-design" ...`, acquires the lock, writes the propose entry, commits, releases the lock.
3. Agent session A's caller receives `fd-game-design` as eligible and immediately calls `_interspect_apply_propose "fd-game-design"` again.
4. `_interspect_apply_propose_locked` re-checks inside the lock (dedup at step 2) and finds the existing entry. If the `ALREADY_EXISTS` path is fixed per Finding 1, this is handled safely. But if Finding 1 is not fixed, the caller gets a confused success message.

This TOCTOU is structurally inherent to the optimistic-read design and is only a problem in combination with Finding 1. Once Finding 1 is fixed (dedup in the locked function returns a clearly-differentiated result), the TOCTOU is safe by design.

**One additional concern:** `_interspect_override_exists` opens and parses the JSON file, which can fail with empty output if the file is being written (during the `mv tmpfile fullpath` rename). On Linux, `mv` on the same filesystem is atomic at the VFS level, so a concurrent read will see either the old or new complete file — this is safe. On cross-filesystem `mv` (not the case here, tmp file and destination are in the same git tree), it would not be safe.

No fix required beyond fixing Finding 1.

---

## Finding 5 — MEDIUM: `_interspect_flock_git` is a subshell — function-local variable assignments do not propagate

**Severity:** Correctness / subtle state loss

**Location:** `_interspect_flock_git` implementation (lib-interspect.sh line 1431), called by `_interspect_apply_propose`.

### Description

```bash
_interspect_flock_git() {
    ...
    (
        if ! flock -w "$_INTERSPECT_GIT_LOCK_TIMEOUT" 9; then ...
        "$@"
    ) 9>"$lockfile"
}
```

The `(...)` is an explicit subshell. `"$@"` calls `_interspect_apply_propose_locked` (or `_interspect_apply_override_locked`) inside that subshell. Any variables set inside the locked function do not affect the parent shell. This is the documented intended behavior and the existing `apply_override` code correctly uses the subshell only for its stdout output (captured via `$(...)`).

However, `_interspect_apply_propose_locked` uses `set -e`. If `set -e` is already active in the caller's shell, the subshell inherits it. This is harmless because `set -e` inside a `$(...)` subshell causes the subshell to exit on error, which causes `$()` to produce empty output and the assignment to succeed (not abort the parent). The exit code of the subshell is what the parent sees via `$?`.

The comment in the function header says "functions run in the same sourced context, NOT as a subprocess" — this comment is WRONG for the `_interspect_apply_propose_locked` use case. The locked function runs in a subshell, not the same process. The comment is correct only for the case where `_interspect_flock_git git add <file>` is called with an external command, but internal shell functions called via `"$@"` inside `(...)` still run in a subshell.

This is not a new bug introduced by the plan, but the plan's new `_interspect_apply_propose_locked` replicates the same pattern and the misleading comment in the header will confuse implementors.

**Recommendation:** Update the function header comment to accurately state that all code inside the flock subshell runs in a subshell, so all state must be passed via positional arguments (as the existing code already does correctly).

---

## Finding 6 — MEDIUM: `_interspect_apply_propose_locked` does not make the `cd "$root"` atomic with the file write

**Severity:** Correctness / git state confusion on partial failure

**Location:** `_interspect_apply_propose_locked`, step 6 (plan lines 469-477).

### Description

```bash
# 6. Git add + commit
cd "$root"
git add "$filepath"
if ! git commit --no-verify -F "$commit_msg_file"; then
    git reset HEAD -- "$filepath" 2>/dev/null || true
    git restore "$filepath" 2>/dev/null || git checkout -- "$filepath" 2>/dev/null || true
    echo "ERROR: Git commit failed. Proposal not applied." >&2
    return 1
fi
```

`set -e` is active inside the locked function. If `cd "$root"` fails (e.g., the git root was deleted or remounted), `set -e` will cause an immediate exit before the rollback logic can run. The file has already been atomically written (`mv "$tmpfile" "$fullpath"`). The result: the JSON file contains the new propose entry, the git index does not, no commit was made. The lock is released. The next caller reads the file and (correctly) sees the entry in the dedup check. So the data is not corrupted — the file state is consistent and correct, and the dedup invariant still holds.

However, the function returns failure (non-zero exit from `set -e`), and the rollback code does not run. The JSON file contains a propose entry that is not backed by a commit. This is a silent inconsistency between file state and git history. The entry will prevent future proposals for the same agent (dedup guard). This is arguably the desired behavior (the file is the source of truth), but the lack of a commit means the entry can be silently lost on `git checkout .` or `git restore .` by an unaware user.

This is the same vulnerability as in `_interspect_apply_override_locked`. The plan replicates the pattern faithfully, including this subtle race.

**Fix:** Wrap the `cd + git add + git commit` sequence in a conditional block that runs after the file write has succeeded and before `set -e` can abort without rollback:

```bash
# After mv "$tmpfile" "$fullpath" succeeds:
if ! ( cd "$root" && git add "$filepath" && git commit --no-verify -F "$commit_msg_file" ); then
    # Rollback: the mv already committed, so restore from git
    git -C "$root" reset HEAD -- "$filepath" 2>/dev/null || true
    git -C "$root" restore "$filepath" 2>/dev/null || git -C "$root" checkout -- "$filepath" 2>/dev/null || true
    echo "ERROR: Git commit failed. Proposal not applied." >&2
    return 1
fi
```

Using `-C "$root"` avoids the `cd` side-effect that is subject to `set -e` abort.

---

## Finding 7 — MEDIUM: Test `"apply_propose skips if override already exists"` and `"apply_propose skips if propose already exists"` use `run` but earlier tests make direct calls — exit-code semantics differ

**Severity:** Test correctness / misleading test results

**Location:** `test_interspect_routing.bats`, plan Task 3 tests.

### Description

The plan mixes `run` and direct calls across the four `apply_propose` tests:

- `"apply_propose writes propose action..."` — direct call (no `run`). If `_interspect_apply_propose` returns non-zero, the test itself exits non-zero, which bats reports as a test failure with the appropriate error. This is fine.
- `"apply_propose skips if override already exists"` — uses `run`. Correct: `$status` and `$output` are captured.
- `"apply_propose skips if propose already exists"` — uses `run`. Correct.
- `"apply_propose does not create canary record"` — direct call. Fine.

The inconsistency is not a bug, but there is a specific hazard in the `"apply_propose skips"` tests: the assertions check for `"already exists"` in `$output`, but `_interspect_apply_propose_locked` emits the `INFO:` message to **stderr** (`>&2`), not stdout. When bats uses `run`, it captures both stdout and stderr into `$output` only when they are merged, which depends on the bats version and configuration. In bats-core 1.x, `run` captures only stdout by default; stderr goes to the terminal. The `grep -qi "already exists"` check may silently pass (empty `$output`, no match, grep returns 1) — but the test uses a positive assertion without checking exit code — actually the test does:

```bash
run _interspect_apply_propose "fd-game-design" "test" '[]' "interspect"
echo "output: $output"
echo "$output" | grep -qi "already exists"
```

There is no `[ ... ]` assertion after the grep. The grep result is the last command, so `$status` from `run` and the grep result are not connected. The test passes if `run` exits 0 AND the grep exits 0. But if the INFO message went to stderr (not captured in `$output`), the `grep -qi` fails (exit 1), and the overall test fails. If this is intended behavior, the test is correct. But if the plan intends to assert that the skip message appears, the assertion is fragile.

After fixing Finding 1 (the `ALREADY_EXISTS` path), the correct assertion is:

```bash
run _interspect_apply_propose "fd-game-design" "test" '[]' "interspect"
[ "$status" -eq 0 ]
# The function now returns 0 for skip; assert no "SUCCESS" in output
! echo "$output" | grep -qi "^SUCCESS:"
# And the function should print an INFO-level message on stdout
echo "$output" | grep -qi "already exists"
```

But this requires `_interspect_apply_propose` to emit the `already exists` message on stdout (not just pass through stderr from the locked function).

**Fix:** After fixing Finding 1, `_interspect_apply_propose` should detect the skip condition and emit a stdout message before returning 0, so the test assertion on `$output` is reliable.

---

## Finding 8 — LOW: `_interspect_get_classified_patterns` uses integer division — cross-classification boundary agents may be inconsistently categorized

**Severity:** Logic / statistical edge case

**Location:** `_interspect_classify_pattern` (lib-interspect.sh line 377), called inside `_interspect_get_classified_patterns` pipeline.

### Description

`_interspect_classify_pattern` is called once per classified row (per `(agent, event, reason)` group). An agent with multiple classified rows may have:
- Row 1 (agent_wrong): ec=5, sc=4, pc=3 → `ready` (all three thresholds met)
- Row 2 (deprioritized): ec=2, sc=2, pc=1 → `emerging` (only event threshold met)

`_interspect_get_routing_eligible` filters by `cls == "ready"` AND `evt == "override"` AND `reason == "agent_wrong"`. For this agent, Row 1 passes all filters. Row 2 is skipped. Correct.

`_interspect_get_overlay_eligible` also filters by `cls == "ready"`. Row 1 (agent_wrong) has `cls=ready`, Row 2 (deprioritized) has `cls=emerging`. Both are admitted to the accumulation loop because `cls == "ready"` check only applies to rows individually. Wait — the check is:

```bash
[[ "$cls" == "ready" ]] || continue
```

So Row 2 (`emerging`) is skipped. `agent_total[$src]` only accumulates from `ready` rows, not all override rows. This means the denominator for pct is wrong: it only counts events from `ready` classified rows, not all override events.

For the test case in the plan (4 agent_wrong + 2 deprioritized = 67%), if the deprioritized row is `emerging` (ec=2, sc=2, pc=1 — below min_sessions=3, below min_events=5), it is skipped. `agent_total[fd-overlay-test]` = 4. `agent_wrong[fd-overlay-test]` = 4. Pct = 100%. The agent would be placed in the routing band (100% >= 80%), not the overlay band (40-79%), and the test `"get_overlay_eligible returns agents in 40-79% wrong band"` would FAIL.

This is a correctness bug in the plan's `_interspect_get_overlay_eligible` design. The `[[ "$cls" == "ready" ]] || continue` filter should not be applied before accumulation, or the accumulation should use raw DB queries rather than classified row counts.

### Concrete test failure

The test inserts 6 events: 4 agent_wrong + 2 deprioritized. The classified patterns query groups by `(fd-overlay-test, override, agent_wrong)` → (4, 3, 3) → `ready`, and `(fd-overlay-test, override, deprioritized)` → (2, 2, 2) → `emerging`. The loop in `_interspect_get_overlay_eligible` skips the `emerging` row. `agent_total` = 4, `agent_wrong` = 4. Pct = 100%. The band filter `(( pct >= 40 && pct < 80 ))` fails. The agent is not emitted. The test asserts `[ -n "$result" ]` and `grep -q "fd-overlay-test"` — both fail.

### Fix

Remove the `[[ "$cls" == "ready" ]] || continue` guard before accumulation, and instead apply it only as a gate to decide whether the agent is "seen" at all (i.e., only output agents that have at least one `ready` row). Or, more robustly: query the DB directly for per-agent totals, bypassing the classified-row filtering entirely. The classification is meant to gate proposal generation, not to filter which events count in the percentage.

A minimal fix preserving the plan structure:

```bash
_interspect_get_overlay_eligible() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    [[ -f "$db" ]] || return 0

    _interspect_load_confidence

    local -A agent_total agent_wrong agent_sessions agent_projects agent_has_ready

    while IFS='|' read -r src evt reason ec sc pc cls; do
        [[ "$evt" == "override" ]] || continue
        _interspect_validate_agent_name "$src" 2>/dev/null || continue

        # Track which agents have at least one ready row
        [[ "$cls" == "ready" ]] && agent_has_ready[$src]=1

        # Accumulate ALL override events regardless of classification
        agent_total[$src]=$(( ${agent_total[$src]:-0} + ec ))
        # Use max for sessions/projects (distinct counts are non-additive)
        (( sc > ${agent_sessions[$src]:-0} )) && agent_sessions[$src]=$sc
        (( pc > ${agent_projects[$src]:-0} )) && agent_projects[$src]=$pc
        if [[ "$reason" == "agent_wrong" ]]; then
            agent_wrong[$src]=$(( ${agent_wrong[$src]:-0} + ec ))
        fi
    done < <(_interspect_get_classified_patterns)

    for src in "${!agent_total[@]}"; do
        # Only emit agents that have at least one ready-classified row
        [[ "${agent_has_ready[$src]:-}" == "1" ]] || continue

        local total=${agent_total[$src]}
        local wrong=${agent_wrong[$src]:-0}
        (( total > 0 )) || continue

        local pct=$(( wrong * 100 / total ))
        (( pct >= 40 && pct < 80 )) || continue

        if _interspect_override_exists "$src"; then
            continue
        fi

        echo "${src}|${agent_total[$src]}|${agent_sessions[$src]}|${agent_projects[$src]}|${pct}"
    done
}
```

This change also addresses the session/project max-tracking problem from Finding 3.

---

## Finding 9 — LOW: Concurrent DB access from multiple sqlite3 calls inside the pipeline subshell

**Severity:** Concurrency / potential lock contention

**Location:** `_interspect_get_routing_eligible`, multiple `sqlite3` calls per loop iteration (plan lines 122-125).

### Description

`_interspect_get_routing_eligible` runs 3 sqlite3 processes per eligible classified row: one in `_interspect_is_routing_eligible` (which itself runs two queries), and two more for the per-row pct computation. Each sqlite3 invocation opens a new connection. The database is in WAL mode (`PRAGMA journal_mode=WAL`), which allows concurrent readers and one writer. Multiple readers opening simultaneously will not deadlock — WAL handles this correctly.

However, if `_interspect_apply_propose_locked` is writing (holding the exclusive lock via flock), sqlite3 readers will not block at the sqlite3 level (WAL readers do not wait for writers). The flock is a shell-level advisory lock, not a sqlite3-level lock. So the interspect git flock and sqlite3's own WAL locking are orthogonal. This is safe.

The concern is performance: 6+ sqlite3 processes per classified row (on top of the main `_interspect_get_classified_patterns` query) creates N*6 subprocesses for N eligible agents. For typical usage (single-digit agents), this is acceptable. For a database with many agents, this degrades linearly.

No fix required for correctness, but consider consolidating the per-agent queries into a single SQL window-function query for future optimization.

---

## Finding 10 — LOW: `_interspect_apply_propose` creates a temp file that may leak on signal interruption

**Severity:** Resource management / minor

**Location:** `_interspect_apply_propose`, commit_msg_file (plan lines 388-410).

### Description

```bash
local commit_msg_file
commit_msg_file=$(mktemp)
printf '...' > "$commit_msg_file"

local flock_output
flock_output=$(_interspect_flock_git _interspect_apply_propose_locked ... "$commit_msg_file")

local exit_code=$?
rm -f "$commit_msg_file"
```

If the process receives SIGTERM or SIGKILL between `mktemp` and `rm -f`, the temp file leaks in `/tmp`. This is identical to the pattern used in the existing `_interspect_apply_routing_override`. The existing code also does not set a trap to clean up on signal. Since Bash does not execute the `rm -f` after a SIGKILL, the leak is unavoidable without a trap.

The existing functions have the same pattern, so this is not a regression introduced by the plan. The same accepted risk applies.

**Recommendation (low priority):** Use a `trap` pattern for robust cleanup:
```bash
trap 'rm -f "$commit_msg_file"' EXIT INT TERM
```
This is consistent across all callers. Not required for this plan's scope.

---

## Summary Table

| # | Severity | Function | Issue | Fix Required |
|---|----------|----------|-------|-------------|
| 1 | CRITICAL | `_interspect_apply_propose_locked` / caller | `ALREADY_EXISTS` string treated as commit SHA | Yes — use exit code 2 or prefixed sentinel |
| 2 | HIGH | `_interspect_get_routing_eligible` | Per-row pct computed with bare source name, not multi-variant query | Yes — use multi-variant SQL or eliminate redundant queries |
| 3 | HIGH | `_interspect_get_overlay_eligible` | `agent_wrong[$src]` is assignment not accumulation; session/project is last-wins | Yes — use `+=` and max-tracking |
| 4 | HIGH | `_interspect_get_overlay_eligible` | `ready` filter applied before accumulation, causing wrong denominator for pct | Yes — accumulate all `override` events, gate emission on `agent_has_ready` |
| 5 | MEDIUM | `_interspect_flock_git` header comment | States functions run "in same context" — incorrect, they run in subshell | Yes — fix misleading comment |
| 6 | MEDIUM | `_interspect_apply_propose_locked` | `cd "$root"` failure under `set -e` leaves file written but no commit | Low priority — same as existing override code |
| 7 | MEDIUM | Tests for `apply_propose skips ...` | Assertions on `"already exists"` in `$output` may fail if message goes to stderr | Yes — add explicit stdout message from caller after skip detection |
| 8 | LOW | `_interspect_get_classified_patterns` pipeline | Per-row classification creates inconsistency for multi-row agents | Addressed by fix for #4 |
| 9 | LOW | `_interspect_get_routing_eligible` | 6+ sqlite3 processes per agent | Acceptable for now, future optimization |
| 10 | LOW | `_interspect_apply_propose` | Temp file leaks on SIGKILL | Same as existing code, not a regression |

## Blocker for Implementation

Findings 1, 3, and 4 are blockers. Together they mean:
- Finding 1: the propose flow's "already exists" path produces a false SUCCESS with a non-SHA in the commit field.
- Findings 3+4: the overlay eligibility function will compute pct against only the `ready`-classified rows' event counts, causing the test `"get_overlay_eligible returns agents in 40-79% wrong band"` to fail (the test agent will show 100% not 67%).

These must be corrected in the plan before implementation begins.
