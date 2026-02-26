# Correctness Review: Interspect Routing Overrides Schema Plan
# File: docs/plans/2026-02-23-interspect-routing-overrides-schema.md
# Reviewer: Julik (flux-drive correctness reviewer)
# Date: 2026-02-23

---

## Invariants Established Before Review

These must hold at all times. Every finding below is framed as a violation of one or more of them.

1. **Atomicity invariant**: The routing-overrides.json file, the git commit, and the DB records (modifications + canary) for a single override must all succeed or all roll back together. A partial write leaves the system in a corrupt state.
2. **Snapshot staleness contract**: The `confidence` and `canary.status` fields in routing-overrides.json are explicitly creation-time snapshots. The DB is authoritative for live state. Any code or documentation that conflates the two violates this contract.
3. **Argument identity invariant**: Every positional parameter received by `_interspect_apply_override_locked` must map to exactly the variable it is assigned to. A shift-based misassignment is a silent data corruption bug.
4. **Input safety invariant**: No user-controlled or DB-derived value should reach `awk BEGIN {...}` without validation, because `awk` executes arithmetic expressions, not string templates.
5. **Reader contract**: The reader must return a consistent, usable structure regardless of what it finds in the file. Mixing `return 1` (error) with valid-looking JSON output is an inconsistency that callers cannot reason about safely.
6. **Test determinism invariant**: Tests that insert evidence rows without `session_id`, `seq`, `ts`, or `project` values will fail against the actual schema and produce misleading CI results.

---

## Finding 1 (CRITICAL): Confidence Computed Outside Lock — Evidence Can Change Before Write

**Severity:** High — silent data integrity corruption

**Location:** Plan Task 2, Step 3: `_interspect_apply_routing_override` (outer function, before flock call)

### Description

The plan computes `confidence` in the outer function body — after pre-flock validation but before entering `_interspect_flock_git`. The computed value is then passed as an argument to `_interspect_apply_override_locked` for writing.

The race is:

```
Thread A (apply)                        Thread B (any evidence writer)
─────────────────────────────────────   ───────────────────────────────
total=$(sqlite3 ... COUNT(*) wrong)     [running concurrently]
wrong=$(sqlite3 ... COUNT(*) wrong)
confidence=awk(wrong/total)             INSERT INTO evidence (agent_wrong)
                                        INSERT INTO evidence (agent_wrong)
flock acquired
write confidence=$old_value to JSON     [too late — 2 new rows missed]
```

The window is small but nonzero. The evidence DB uses WAL mode, so inserts from the interspect-evidence hook or from another `_interspect_apply_routing_override` call can land between the two `sqlite3` COUNT queries, or between the second COUNT and the `flock` acquisition.

The confidence value written to the JSON file can be lower than the actual evidence ratio at the moment of commit. This is not catastrophic (confidence is a snapshot) but it means the snapshot can be stale by the time it is written, which undermines the purpose of recording it.

### Minimal Corrective Change

Move both `sqlite3` COUNT queries and the `awk` division inside `_interspect_apply_override_locked`, after the flock is held. The outer function should not touch the DB for confidence computation — it already passes `$db` through for exactly this purpose. Since the locked function runs `set -e`, a failed sqlite3 call will abort cleanly.

```bash
# INSIDE _interspect_apply_override_locked, after step 2 (dedup check):
local total wrong confidence
escaped_agent=$(_interspect_sql_escape "$agent")
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source='${escaped_agent}' AND event='override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source='${escaped_agent}' AND event='override' AND override_reason='agent_wrong';")
if (( total > 0 )); then
    confidence=$(awk "BEGIN {printf \"%.2f\", ${wrong}/${total}}")
else
    confidence="1.0"
fi
```

This eliminates the window entirely: confidence is computed while the exclusive flock is held, so no concurrent evidence insert can affect it.

---

## Finding 2 (HIGH): `shift 9` Positional Arg Passing — Fragile and Underdocumented

**Severity:** High — silent misassignment if caller or callee arg count diverges

**Location:** Plan Task 2, Step 5; proposed `_interspect_apply_override_locked` signature

### Description

The plan proposes this signature for the locked function:

```bash
_interspect_apply_override_locked() {
    set -e
    local root="$1" filepath="$2" fullpath="$3" agent="$4"
    local reason="$5" evidence_ids="$6" created_by="$7"
    local commit_msg_file="$8" db="$9"
    shift 9
    local confidence="${1:-1.0}" canary_window_uses="${2:-20}" canary_expires_at="${3:-null}"
```

The existing call site in `_interspect_apply_routing_override` at line 652-654 passes exactly 9 positional args:

```bash
flock_output=$(_interspect_flock_git _interspect_apply_override_locked \
    "$root" "$filepath" "$fullpath" "$agent" "$reason" \
    "$evidence_ids" "$created_by" "$commit_msg_file" "$db")
```

The plan's Step 4 updates this to pass 12 args by appending `"$confidence" "$canary_window_uses" "$canary_expires_at"`.

The failure mode is not today's code but the future. `shift 9` is a position-sensitive trap:

- If a caller adds an argument before position 9 (e.g., inserts a `scope` param), all post-shift indices silently shift. `confidence` becomes `canary_window_uses`, `canary_window_uses` becomes `canary_expires_at`, and the third arg (the real `canary_expires_at`) is silently dropped — falling back to the `"${3:-null}"` default. No error, no warning. The canary snapshot written to JSON is wrong.
- `$9` in bash is special: `${10}` requires braces, but `"$9"` alone captures only `$9`. This is correct for `db` since it IS the 9th arg, but the comment "use `shift 9` for params beyond `$9`" is not universal knowledge and will confuse the next editor.
- `_interspect_flock_git` itself calls `"$@"` (line 1363), passing all its own arguments through. The first argument consumed by `_interspect_flock_git` is the function name. So from the locked function's perspective, `$1` is `root` — correct. But `_interspect_flock_git` must not have any consumed-but-not-shifted args of its own. Reviewing line 1350-1364 confirms it does not: it calls `"$@"` directly. This is fine, but the comment in the plan that calls it "avoiding quote-nesting hell" undersells the real risk.

### Minimal Corrective Change

Replace `shift 9` + positional extension with named parameters passed as `KEY=value` pairs, or encode the new fields into a single JSON argument:

```bash
# Caller constructs a JSON params object:
local extra_params
extra_params=$(jq -n \
    --argjson confidence "$confidence" \
    --argjson canary_window_uses "$canary_window_uses" \
    --arg canary_expires_at "$canary_expires_at" \
    '{confidence:$confidence,canary_window_uses:$canary_window_uses,canary_expires_at:$canary_expires_at}')

flock_output=$(_interspect_flock_git _interspect_apply_override_locked \
    "$root" "$filepath" "$fullpath" "$agent" "$reason" \
    "$evidence_ids" "$created_by" "$commit_msg_file" "$db" "$extra_params")
```

Inside the locked function, `$10` (with braces) receives the JSON blob, and jq extracts fields. This makes adding future parameters safe: you add a key to the JSON, not a new positional slot.

Alternatively, if the approach in Finding 1 is adopted (compute confidence inside the lock), the extra params reduce to only `canary_window_uses` and `canary_expires_at`, which can safely be `$10` and `$11` with braces — far less dangerous than three post-shift params.

---

## Finding 3 (HIGH): Canary Snapshot in JSON Is Creation-Time — Reader Must Not Present It as Live

**Severity:** High — correctness contract violation in reader + SKILL.md display

**Location:** Plan Task 3 (reader) and Task 4 (SKILL.md display)

### Description

The schema correctly annotates `canary` as a creation-time snapshot:

```json
"description": "Canary monitoring snapshot at creation time. DB is authoritative for live state."
```

But the plan's Task 4 Step 1 instructs flux-drive to display this snapshot directly to the user:

```
"agent1 [canary: active, expires 2026-03-09]"
```

The snapshot `status` is always "active" at creation time (it is hardcoded in the jq template: `--arg status "active"`). After 20 sessions, the DB canary record may have moved to `passed`, `alert`, `expired_unused`, or `reverted`. The JSON file is never updated after initial write.

A user reading the triage output sees `[canary: active, expires 2026-03-09]` three weeks after the override passed canary and was promoted to permanent — the canary is no longer active, but the JSON says it is. This is not "stale" in a harmless way: it actively misleads the user into thinking monitoring is still ongoing.

The reader validation added in Task 3 does not consult the DB at all. It has no mechanism to return live canary state because it only reads the JSON file.

**Concrete failure scenario:**

1. Interspect applies override for `fd-perception`. Canary snapshot written: `{status: "active", window_uses: 20, expires_at: "2026-03-09"}`.
2. 20 sessions pass. DB updates canary to `status = "passed"`.
3. User runs flux-drive six weeks later.
4. Triage output reads JSON, displays: `fd-perception [canary: active, expires 2026-03-09]`.
5. User believes monitoring is ongoing and the override is still provisional.
6. User does not act on `/interspect:status` because they trust the triage output.

### Minimal Corrective Change

Two options:

**Option A (preferred):** Instruct flux-drive in SKILL.md to treat the canary field as a historical annotation only:

```markdown
- If the override has a `canary` field, display: `(canary was active at creation — run /interspect:status for current monitoring state)`
- Do NOT display canary.status as if it reflects live state.
```

**Option B:** Update `_interspect_apply_override_locked` to also write canary state back to the JSON on every canary evaluation (`_interspect_evaluate_canary`). This keeps the JSON file in sync with DB state. The cost is that the JSON file then requires the write lock for every canary evaluation, not just override creation.

Option A is lower risk and correctly separates concerns: the JSON is for routing decisions, the DB is for monitoring state.

---

## Finding 4 (MEDIUM): `awk "BEGIN {printf ..., ${wrong}/${total}}"` With Unvalidated Inputs

**Severity:** Medium — injection risk if inputs are not integers

**Location:** Plan Task 2, Step 3; confidence computation in outer function

### Description

The plan proposes:

```bash
confidence=$(awk "BEGIN {printf \"%.2f\", ${wrong}/${total}}")
```

This embeds shell variables directly into an `awk` program string. `awk BEGIN {...}` is not a printf format string — it is an arbitrary awk program. If `wrong` or `total` contain non-integer content, `awk` executes it.

The values come from `sqlite3` COUNT queries. SQLite COUNT always returns a non-negative integer. However:

- If the sqlite3 binary returns an error (DB locked, file missing), the output is empty. `awk "BEGIN {printf \"%.2f\", /}"` — that is a syntax error, and awk exits nonzero. With `set -e` inside the locked function, this kills the locked function and the override is not applied. This is safe but silent.
- If someone sets `_INTERSPECT_DB` to a controlled path and the DB is replaced with a view that returns non-integer data, the `wrong` variable could be a string. `awk "BEGIN {printf \"%.2f\", somestring/5}"` evaluates `somestring` as 0 in awk — silently wrong, not injected.
- The existing code at line 1000 in `_interspect_compute_canary_baseline` uses identical `awk` patterns for `override_rate` and `fp_rate`. So this is an established pattern in the codebase, not new debt introduced by the plan.

The actual injection risk is low because sqlite3 COUNT output is always a non-negative integer on success. However, the plan moves this computation to the outer function where `set -e` is NOT active (the outer function does not call `set -e`). A sqlite3 failure here produces an empty `wrong` or `total`, and `awk "BEGIN {printf \"%.2f\", /}"` will emit an error to stderr but still exit 0 on some awk implementations (gawk exits 2 on syntax error; mawk exits 1). The caller does not check awk's exit code, so `confidence` may be set to an empty string, and `--argjson confidence ""` in jq will fail — raising an error inside the locked function where `set -e` is active. The overall failure is non-silent, but the error message will be confusing ("jq: invalid JSON, unexpected end of input").

### Minimal Corrective Change

Validate that both counts are non-negative integers before the awk call. Since this computation should move inside the lock (see Finding 1), `set -e` will catch the sqlite3 failures. Additionally:

```bash
# Validate counts are integers before awk
if [[ ! "$total" =~ ^[0-9]+$ ]] || [[ ! "$wrong" =~ ^[0-9]+$ ]]; then
    confidence="1.0"  # safe fallback
else
    confidence=$(awk "BEGIN {printf \"%.2f\", ${wrong}/${total}}")
fi
```

This mirrors the `_interspect_clamp_int` pattern already used in the codebase for similar inputs.

---

## Finding 5 (MEDIUM): Reader Returns `return 1` With Valid JSON — Inconsistent Error Contract

**Severity:** Medium — callers cannot distinguish "error" from "empty overrides"

**Location:** Plan Task 3, Step 3: `_interspect_read_routing_overrides`

### Description

The proposed reader returns `return 1` in three cases:

1. Path traversal detected — returns `'{"version":1,"overrides":[]}'` then `return 1`
2. Malformed JSON — returns `'{"version":1,"overrides":[]}'` then `return 1`
3. Version > 1 — returns `'{"version":1,"overrides":[]}'` then `return 1`

In all three error cases, the function outputs valid, usable JSON to stdout AND returns exit code 1. The existing call sites use the output for routing decisions:

```bash
# _interspect_override_exists (line 594-596)
current=$(_interspect_read_routing_overrides)
echo "$current" | jq -e --arg agent "$agent" '.overrides[] | select(.agent == $agent)'
```

This call does not check the return code of `_interspect_read_routing_overrides`. It captures stdout. So the JSON is always used, exit code is always ignored. The exit code 1 is meaningless to all current callers.

The BATS test for version validation (Task 3, Step 1) asserts `[ "$status" -eq 1 ]` AND `[[ "$output" == *'"version":1'* ]]`. This test is itself inconsistent: it expects both a failure exit code AND valid JSON output. The test passes, but it validates a contract that no real caller checks.

The inconsistency is also visible in the happy path: when the file is missing, the function returns exit 0 with `'{"version":1,"overrides":[]}'`. When the file has invalid version, it returns exit 1 with the exact same JSON. Callers that do `result=$(_interspect_read_routing_overrides)` cannot tell the difference.

**Compare with the "validates override entries" test:**

```bash
@test "read_routing_overrides validates override entries have agent+action" {
    ...
    # Should warn about missing action but still return data (non-blocking)
    [ "$status" -eq 0 ]
}
```

The missing-action case returns 0 (non-blocking warning). The version-mismatch case returns 1. The malformed-JSON case returns 1. These three different error severities produce two different status codes, but all three produce the same stdout. A caller using only stdout (which all existing callers do) cannot distinguish them.

### Minimal Corrective Change

Decide on one of two contracts and apply it consistently:

**Option A — stdout is always valid JSON, caller uses exit code to decide urgency:**
Document explicitly that callers MUST check `$?` to distinguish "valid data" from "fallback data." Update `_interspect_override_exists` and flux-drive to check exit code. Mark the test assertions as `# exit code 1 means fallback was used`.

**Option B — error cases return empty stdout, caller checks for empty:**
On path traversal, malformed JSON, and version > 1: return an empty string (or no output) with exit 1. Callers must test for empty output and use a hardcoded fallback. This is the Unix convention for read functions that fail.

Option A matches existing behavior and requires fewer callers to change. Option B is cleaner but touches more code. Either is acceptable; the current plan leaves the contract unspecified.

---

## Finding 6 (MEDIUM): BATS Test Evidence Rows Missing Required NOT NULL Columns

**Severity:** Medium — tests fail against actual schema, producing false CI confidence

**Location:** Plan Task 2, Step 1; new BATS tests for confidence and canary

### Description

The proposed confidence test inserts evidence rows as:

```bash
sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
```

But the actual evidence table schema (lines 92-105 of lib-interspect.sh) requires:

```sql
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    source TEXT NOT NULL,
    source_version TEXT,
    event TEXT NOT NULL,
    override_reason TEXT,
    context TEXT NOT NULL,
    project TEXT NOT NULL,
    ...
```

`ts`, `session_id`, `seq`, `context`, and `project` are all `NOT NULL`. The test insert omits all of them. SQLite will reject these inserts with "NOT NULL constraint failed: evidence.ts" (or similar). The test will fail at the `sqlite3` insert step, not at the assertion — meaning `status` from `run _interspect_apply_routing_override` may still be 0 if the function skips the evidence check when total=0 (it returns confidence="1.0" in that case). The confidence assertion `[ "$confidence" = "0.8" ]` will then fail with "0.8" != "1.0".

Compare with the existing eligible-at-80% test at line 192-201 in the test file, which correctly provides all required columns:

```bash
sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-game-design', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
```

The plan's proposed tests use the shorter form, which fails against the NOT NULL schema. This is a straightforward fix but if missed, the "tests turn green" confirmation in Step 7 is not achievable without schema-compatible inserts.

### Minimal Corrective Change

Update the proposed test inserts to match the pattern from the existing eligible test:

```bash
sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s1', 1, '2026-01-01', 'fd-perception', 'override', 'agent_wrong', '{}', 'proj1');"
```

Five such inserts for the confidence test, with distinct `session_id`/`seq`/`ts`/`project` values to satisfy uniqueness where applicable.

---

## Finding 7 (LOW): Missing BATS Coverage for Edge Cases Explicitly Requested

**Severity:** Low — incomplete guard for documented failure modes

**Location:** Plan Task 2 (test coverage), Plan Task 3 (test coverage)

### Description

The task requests review of these edge cases. The plan's proposed test suite does not cover them:

**Empty overrides array on write:** The plan adds confidence/canary to a freshly written override. There is no test that calls `_interspect_apply_routing_override` on an agent with zero evidence rows (the `confidence="1.0"` fallback path). The only validation that `confidence="1.0"` is correct when `total=0` is the code comment. A test would confirm the JSON contains `"confidence":1.0` (not `"confidence":"1.0"` — note that `--argjson confidence "1.0"` correctly produces a number, but the fallback is a shell string that `--argjson` will treat as a bare number literal, which is fine — but it is worth confirming).

**Override with only required fields (agent + action):** There is no read test for a minimal override `{"agent":"fd-test","action":"exclude"}` that lacks confidence, canary, reason, and evidence_ids. The reader should pass this through without error (the schema marks all of these as optional). The existing "ignores unknown fields" test covers forward-compatibility in one direction but not backward-compatibility for missing optional fields.

**Concurrent apply during read:** The `_interspect_read_routing_overrides_locked` function uses `flock -s -w 1` (shared lock, 1-second timeout) and falls through to an unlocked read if the lock is unavailable. There is no test for the scenario where:
1. A write lock is held (apply in progress)
2. A locked read times out
3. The fallback unlocked read sees a partially-written `.tmp.$$` temp file

In practice, the atomic rename (`mv "$tmpfile" "$fullpath"`) ensures the file is either the old version or the new version — never a partial write visible to readers. But the test would confirm this guarantee survives the timeout path. The `flock -s -w 1` timeout message ("showing latest available data") is also the only indication to callers that stale data may have been returned. No caller checks stderr for this warning.

### Minimal Corrective Change

Add three focused tests:

```bash
@test "apply_routing_override with zero evidence writes confidence 1.0" {
    # No evidence inserted
    run _interspect_apply_routing_override "fd-perception" "no evidence" '[]' "test"
    [ "$status" -eq 0 ]
    confidence=$(jq -r '.overrides[0].confidence' "${TEST_DIR}/.claude/routing-overrides.json")
    [ "$confidence" = "1" ] || [ "$confidence" = "1.0" ]
}

@test "read_routing_overrides handles minimal override with only required fields" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":1,"overrides":[{"agent":"fd-test","action":"exclude"}]}' \
        > "${TEST_DIR}/.claude/routing-overrides.json"
    run _interspect_read_routing_overrides
    [ "$status" -eq 0 ]
    [[ "$output" == *"fd-test"* ]]
}

@test "locked read returns data even when write lock is held" {
    # Start a background process holding the write lock for 2 seconds
    (
        exec 9>"${TEST_DIR}/.clavain/interspect/.git-lock"
        flock -x 9
        sleep 2
        flock -u 9
    ) &
    local bg_pid=$!
    sleep 0.1  # Let background acquire lock

    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":1,"overrides":[]}' > "${TEST_DIR}/.claude/routing-overrides.json"

    # Should return data despite lock contention (with 1s timeout fallback)
    result=$(_interspect_read_routing_overrides_locked 2>/dev/null)
    version=$(echo "$result" | jq -r '.version')
    [ "$version" = "1" ]
    wait $bg_pid 2>/dev/null || true
}
```

---

## Finding 8 (LOW): `date -d` vs `date -v` Portability — Silent Failure Sets `canary_expires_at="null"`

**Severity:** Low — degrades gracefully but silently eliminates canary tracking

**Location:** Plan Task 2, Step 3; `canary_expires_at` computation

### Description

The plan computes `canary_expires_at` using:

```bash
canary_expires_at=$(date -u -d "+${_INTERSPECT_CANARY_WINDOW_DAYS:-14} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -v+"${_INTERSPECT_CANARY_WINDOW_DAYS:-14}"d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
if [[ -z "$canary_expires_at" ]]; then
    canary_expires_at="null"
fi
```

If both `date` invocations fail (neither GNU `date -d` nor BSD `date -v` syntax), `canary_expires_at` is set to the string `"null"`. The subsequent jq template uses:

```bash
if [[ "$canary_expires_at" != "null" ]]; then
    canary_json=$(jq -n ... --arg expires_at "$canary_expires_at" ...)
else
    canary_json="null"
fi
```

When `canary_json="null"`, the override is written without any canary snapshot. The locked function at line 780 (current code) already handles this case: `if [[ -z "$expires_at" ]]; then ... return 1`. The plan's outer computation is inconsistent with the locked function's treatment: the locked function treats a missing `expires_at` as a fatal error (`return 1`), but the plan's outer code treats it as a `null` to pass through silently.

The same identical pattern already exists in `_interspect_apply_override_locked` at lines 776-781 of the current code. This is not new debt introduced by the plan — the plan replicates it in the outer function. But duplicating the same date computation in two places (inner and outer) means they can diverge, and the outer one's `"null"` string might not round-trip correctly through `--argjson` if future jq code tests for null type rather than string comparison.

### Minimal Corrective Change

Keep the date computation in exactly one place — inside the locked function, where it already exists and where `return 1` correctly prevents a bad canary from being written. The outer function should not duplicate this computation. This is consistent with Finding 1's recommendation to move all evidence-dependent computation inside the lock.

---

## Summary Table

| # | Severity | Finding | Invariant Violated |
|---|----------|---------|-------------------|
| 1 | CRITICAL | Confidence computed outside lock — evidence can change before write | Atomicity (invariant 1) |
| 2 | HIGH | `shift 9` positional args — silent misassignment if arg count changes | Argument identity (invariant 3) |
| 3 | HIGH | Canary snapshot presented as live state in SKILL.md display | Snapshot staleness contract (invariant 2) |
| 4 | MEDIUM | `awk "BEGIN {printf ..., ${wrong}/${total}}"` without integer validation | Input safety (invariant 4) |
| 5 | MEDIUM | Reader returns `return 1` with valid JSON — inconsistent error contract | Reader contract (invariant 5) |
| 6 | MEDIUM | BATS tests insert evidence without required NOT NULL columns | Test determinism (invariant 6) |
| 7 | LOW | Missing tests for zero-evidence, minimal override, and concurrent-read paths | Test determinism (invariant 6) |
| 8 | LOW | `date` failure sets `canary_expires_at="null"` silently, duplicated computation | Atomicity (invariant 1) |

---

## Recommended Changes, Ordered by Impact

1. **Move confidence computation inside `_interspect_apply_override_locked`** (Finding 1). This also resolves Finding 8 (date duplication). One code path for all evidence-dependent writes.

2. **Replace `shift 9` with a JSON params bundle** (Finding 2). Pass `extra_params` as a single `$10` argument using `${10}` braces. Safe against future extension.

3. **Update SKILL.md canary display to label it as a historical snapshot** (Finding 3). Add "run /interspect:status for live state" to every canary display instruction.

4. **Add integer guard before awk in confidence path** (Finding 4). Pattern is already in codebase (`_interspect_clamp_int`).

5. **Document reader exit-code contract explicitly** (Finding 5). Pick Option A or B and add a comment. Update `_interspect_override_exists` to propagate the exit code if needed.

6. **Fix BATS test inserts to include all NOT NULL columns** (Finding 6). Copy the insert pattern from the existing "eligible at 80%" test.

7. **Add three edge-case BATS tests** (Finding 7). Zero evidence, minimal override, concurrent-read timeout path.
