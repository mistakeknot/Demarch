# Correctness Review: `_interspect_approve_override` / `_interspect_approve_override_locked`

**Reviewed files:**
- `/home/mk/projects/Demarch/os/clavain/hooks/lib-interspect.sh` lines 1158-1397
- `/home/mk/projects/Demarch/os/clavain/commands/interspect-approve.md`

**Compared against:**
- `_interspect_apply_override_locked` (lines 858-1014)
- `_interspect_apply_propose_locked` (lines 1092-1156)

**Date:** 2026-02-23

---

## Invariants

Before assigning severity to each finding, the invariants the system must maintain:

1. **State machine integrity**: An entry in `routing-overrides.json` is always in exactly one of: `propose` or `exclude`. No entry should silently disappear; no entry should be stuck in an inconsistent transient action value.
2. **Atomicity**: A successful `approve` leaves the filesystem, git history, and SQLite database all consistent. A partial commit where the JSON file changed but DB has no record is a split-brain state.
3. **Idempotency**: Running `approve` twice on the same agent produces exit code 0 on the second call, and the second call creates no duplicate DB records.
4. **Monotonicity**: `propose` entries can only be promoted to `exclude`, never downgraded. The in-place promotion must not mutate any other entries in the `overrides` array.
5. **Rollback completeness**: If the git commit fails after the file has been written, the working tree must be restored to the pre-write state.
6. **SQL injection safety**: No caller-controlled string reaches SQLite without sanitisation.
7. **Exit code contract**: 0 = success (including idempotent no-op), 1 = error, 2 = already-excluded (inside flock). The outer function maps 2 to 0 before returning to callers.
8. **Canary baseline correctness**: The baseline must be computed from sessions that pre-date the modification timestamp, not sessions that ran after the override was activated.

---

## Findings

### F1 (MEDIUM) — TOCTOU Window: Pre-check Reads Unlocked File

**Location:** `_interspect_approve_override`, lines 1191-1204

**Code:**
```bash
# Pre-check: verify a propose entry exists (fast-fail before flock)
if [[ -f "$fullpath" ]]; then
    if ! jq -e --arg agent "$agent" '.overrides[] | select(.agent == $agent and .action == "propose")' "$fullpath" >/dev/null 2>&1; then
        # Check if already excluded (idempotent)
        if jq -e --arg agent "$agent" '.overrides[] | select(.agent == $agent and .action == "exclude")' "$fullpath" >/dev/null 2>&1; then
            echo "INFO: ${agent} is already excluded. Nothing to approve."
            return 0
        fi
        echo "ERROR: No proposal found for ${agent}. Run /interspect:propose first." >&2
        return 1
    fi
fi
```

**The race:**
1. Session A reads `routing-overrides.json` outside the flock and finds `fd-safety` with `action=propose`. The pre-check passes.
2. Session B acquires the flock, runs `_interspect_approve_override_locked`, promotes `fd-safety` to `exclude`, and releases the flock.
3. Session A acquires the flock and enters `_interspect_approve_override_locked`. Step 2 inside the lock finds no `propose` entry for `fd-safety` (it was already promoted). It finds an `exclude` entry instead and returns exit code 2.
4. Session A's outer function maps exit code 2 to "INFO: already excluded" and returns 0.

**Assessment:** The code is actually safe because the locked function re-checks the state inside the flock (lines 1266-1273). Exit code 2 is handled correctly. The pre-check is purely a fast-fail optimisation: if no proposal exists, it avoids acquiring the lock at all. The false-alarm path (pre-check says "already excluded", returns 0 early at line 1195) is also correct.

**However, there is a subtler TOCTOU for the "no proposal, no exclusion" case.** If the pre-check at line 1192 finds a `propose` entry, the outer function proceeds to write a commit message file and acquire the flock. Between those two moments, the propose entry could be reverted by another session (`_interspect_revert_routing_override`). When the locked function then runs, it finds neither `propose` nor `exclude`. It outputs "ERROR: No proposal for ${agent}" and returns 1. The user sees an opaque error when the real explanation is a concurrent revert. This is not a correctness bug (the invariant is maintained), but the error message misleads the operator. The recommendation is to add a note in the error path like "a concurrent revert may have removed the proposal."

**Severity: LOW** — No invariant violation. User-facing clarity issue under concurrent revert.

---

### F2 (HIGH) — `set -e` Kills Flock Subshell on Unguarded `sqlite3` INSERT

**Location:** `_interspect_approve_override_locked`, lines 1349-1351

**Code (step 8):**
```bash
# Modification record
sqlite3 "$db" "INSERT INTO modifications (group_id, ts, tier, mod_type, target_file, commit_sha, confidence, evidence_summary, status)
    VALUES ('${escaped_agent}', '${ts}', 'persistent', 'routing', '${filepath}', '${commit_sha}', ${confidence}, '${escaped_reason}', 'applied');"
```

This `sqlite3` call is NOT inside an `if !` guard. The function starts with `set -e`. If this INSERT fails (database locked, constraint violation, disk full, table schema mismatch), `set -e` immediately terminates the function with a non-zero exit. The flock subshell propagates that exit code to `_interspect_flock_git`, which returns it to `_interspect_approve_override`.

The caller then interprets any non-zero exit (that is not 2) as an error and prints "Could not approve override. Check git status and retry." — but the git commit has ALREADY SUCCEEDED at this point (line 1333). The file has been written, the git commit exists, and the JSON now contains the `exclude` entry. The DB has no `modifications` record. The caller cannot roll back the git commit at this stage.

**Concrete interleaving causing split-brain:**
1. `_interspect_approve_override_locked` writes JSON file (line 1329), commits (line 1333). Commit succeeds.
2. The `modifications` INSERT fails — for example, SQLite is momentarily locked by another hook reading the DB (`sqlite3` returns exit 5, SQLITE_BUSY).
3. `set -e` fires. Function exits 1. Flock releases. Outer function sees exit 1, prints error.
4. Caller reports "Could not approve override" but `routing-overrides.json` now has `action=exclude` committed. The DB has no `modifications` row and no `canary` row for this commit SHA.
5. User re-runs `approve`. The locked function finds `action=exclude` and returns 2 (idempotent). Outer prints "already excluded". The DB never gets a `modifications` row or a `canary` row for this agent. Canary monitoring is permanently absent for the activated exclusion.

**Comparison with `_interspect_apply_override_locked`:** The sibling function wraps the `modifications` INSERT inside `if (( is_new == 1 ))` which still has the same unguarded-sqlite3 problem, but it IS the same pattern — neither function treats this INSERT as non-fatal. The overlay writer (`_interspect_write_overlay_locked`, line ~2373) does `set +e` before canary work, explicitly acknowledging the lesson. The approve function lacks that discipline.

**Fix:** Wrap the step-8 `modifications` INSERT in a non-fatal guard, the same way the canary INSERT is already guarded at line 1388. Or, before the INSERT block, do `set +e` to match the overlay pattern.

```bash
# Step 8 fix — treat DB record failure as non-fatal, same as canary
if ! sqlite3 "$db" "INSERT INTO modifications ..."; then
    sqlite3 "$db" "..." 2>/dev/null || true  # best-effort status update
    echo "WARN: Modification record failed — override active but not tracked." >&2
fi
```

**Severity: HIGH** — Causes permanent canary monitoring gap with no user-visible warning. The git commit is committed, the DB is missing a record. The condition is reproducible on any SQLite busy timeout.

---

### F3 (MEDIUM) — Confidence Query Misses Multi-Variant Agent Name Sources

**Location:** `_interspect_approve_override_locked`, lines 1280-1281

**Code:**
```bash
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent}' AND event = 'override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent}' AND event = 'override' AND override_reason = 'agent_wrong';")
```

The `_interspect_is_routing_eligible` function (lines 506-507) queries three name variants:
```sql
WHERE (source = '${escaped}' OR source = 'interflux:${escaped}' OR source = 'interflux:review:${escaped}')
```

The `approve` locked function (step 3) uses only the bare `fd-*` name. If all evidence rows were inserted with `source = 'interflux:fd-safety'` (the format used when the hook runs inside the interflux pipeline), the query returns `total=0`. The function then sets `confidence="1.0"` — the synthetic default — instead of the real measured value.

**Impact:**
- The `confidence` stored in `routing-overrides.json` and `modifications` is 1.0 regardless of actual evidence quality.
- Canary evaluation that uses `confidence` as a weighting factor will treat every approve-path exclusion as maximally certain, suppressing alerts that would fire for lower-confidence overrides.
- This is invisible: no error is emitted, and the stored value looks plausible.

The same bug exists identically in `_interspect_apply_override_locked` lines 887-888. Both functions were written with the same narrower query pattern.

**Fix:** Use the three-variant OR query pattern from `_interspect_is_routing_eligible`:
```bash
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped_agent}' OR source = 'interflux:${escaped_agent}' OR source = 'interflux:review:${escaped_agent}') AND event = 'override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped_agent}' OR source = 'interflux:${escaped_agent}' OR source = 'interflux:review:${escaped_agent}') AND event = 'override' AND override_reason = 'agent_wrong';")
```

**Severity: MEDIUM** — Silently produces incorrect confidence values, undermining canary effectiveness. Shared with `_interspect_apply_override_locked`.

---

### F4 (LOW) — `cd "$root"` in `_interspect_apply_override_locked` Under `set -e`

**Location:** `_interspect_apply_override_locked`, line 941

**Code:**
```bash
cd "$root"
git add "$filepath"
```

The MEMORY.md project notes record: "Use `git -C "$root"` instead of `cd "$root"` inside `set -e` locked functions. If `cd` fails, the shell exits before rollback code, leaving files written but uncommitted."

`_interspect_apply_override_locked` still uses `cd "$root"` at line 941. If `$root` is unavailable (removed, NFS timeout, permission change), `cd` fails, `set -e` fires, the function exits before reaching the git rollback block. The JSON file has already been written to `$fullpath` but is neither staged nor committed. The lock releases, leaving the working tree dirty.

By contrast, the newer `_interspect_apply_propose_locked` (line 1144) and `_interspect_approve_override_locked` (line 1332) correctly use `git -C "$root"`. This is an inconsistency with the established pattern, present specifically in `_interspect_apply_override_locked`.

**Fix:** Change line 941-942:
```bash
# Before
cd "$root"
git add "$filepath"

# After
git -C "$root" add "$filepath"
```

**Severity: LOW** — Only triggers when `$root` becomes unavailable after the file write, which is uncommon but not impossible in NFS or container environments.

---

### F5 (LOW) — `escaped_reason` Used Before `local` Declaration in `_interspect_apply_override_locked`

**Location:** `_interspect_apply_override_locked`, line 955

**Code:**
```bash
# 9. DB inserts INSIDE flock (atomicity with git commit)
escaped_reason=$(_interspect_sql_escape "$reason")
```

At line 955, `escaped_reason` is assigned without a `local` declaration. This means it is set in the function's local scope only by accident (bash functions do not have implicit scoping). If the caller or any other function in the same shell has a variable named `escaped_reason` in scope, this assignment silently overwrites it. More critically, the `local escaped_reason` declaration that would normally prevent bleed-out is missing. The variable leaks into the calling shell context (within the flock subshell, which is a subprocess, so the leak is contained — but the practice is inconsistent and fragile).

Compare: `_interspect_approve_override_locked` correctly declares `local escaped_reason` at line 1346 before use.

**Fix:** Add `local` before line 955:
```bash
local escaped_reason
escaped_reason=$(_interspect_sql_escape "$reason")
```

**Severity: LOW** — Contained within the flock subshell. Does not cause a correctness failure in the current structure but is a hygiene defect and violation of the local-variable discipline used everywhere else.

---

### F6 (LOW) — Canary Baseline `before_ts` Uses `$ts` Which Is Set AFTER the Commit

**Location:** `_interspect_approve_override_locked`, lines 1344-1355

**Code:**
```bash
# 8. DB inserts INSIDE flock (atomicity with git commit)
local ts
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
...
# 9. Canary record — compute baseline BEFORE insert
local baseline_json
baseline_json=$(_interspect_compute_canary_baseline "$ts" "" 2>/dev/null || echo "null")
```

The baseline is computed with `$ts` as `before_ts` in `_interspect_compute_canary_baseline`. The `$ts` here is the DB record insertion timestamp, not the commit timestamp (which is recorded in git). The comment says "compute baseline BEFORE insert" — this is correct in the sense that the canary row has not yet been inserted when the baseline query runs. However, `$ts` is set to `date -u +...` AFTER the git commit succeeds (line 1333). Any sessions that start and complete in the few milliseconds between `git commit` succeeding and `$ts` being set could theoretically be included in the baseline when they should not be. This is an extremely narrow window and effectively harmless in practice.

The more meaningful concern is: `_interspect_compute_canary_baseline` filters sessions with `start_ts < '${escaped_ts}'`. The `$ts` used is the DB insert time, which is a few milliseconds after the commit. Sessions that started before the `_interspect_approve_override` call was invoked but whose `start_ts` falls between the commit and the DB insert will be included in the baseline. Given sessions are long-lived (minutes to hours), this window is negligible.

**Assessment:** No real correctness failure. The comment is accurate. Document this for future maintainers.

**Severity: LOW / INFORMATIONAL**

---

### F7 (LOW) — `jq` In-Place Promotion Mutates Only First Matching Entry

**Location:** `_interspect_approve_override_locked`, lines 1310-1317

**Code:**
```jq
'(.overrides |= map(
    if .agent == $agent and .action == "propose" then
        .action = "exclude"
        | .approved = $approved
        | .confidence = $confidence
        | (if $canary != null then .canary = $canary else . end)
    else . end
))'
```

This uses `map` over the full `overrides` array with an `if/then/else` guard. It correctly mutates every element where `.agent == $agent and .action == "propose"`. If there were multiple `propose` entries for the same agent (which the data model should prevent, but is not enforced by the schema — there is no UNIQUE constraint in the JSON), all of them would be promoted. The `dedup check` at line 1266 only checks for a `propose` entry (returns 2 if `exclude` is found). The `_interspect_apply_propose_locked` function appends without dedup (line 1129: `'.overrides = (.overrides + [$override])'`), and `_interspect_apply_override_locked` uses `unique_by(.agent)` which only keeps the last entry.

The `propose` function's dedup at line 1111 checks for ANY action for the agent (`select(.agent == $agent)` with no `.action` filter). So two `propose` entries for the same agent are impossible through the normal write paths. The `map/if` approach is correct.

**Difference from `_interspect_apply_override_locked`:** That function uses `unique_by(.agent)` on line 926 to dedup, which silently discards earlier entries for the same agent. The `approve` approach of in-place mutation with `map` is strictly more correct for its use case because it preserves all other array entries and does not silently drop anything.

**Assessment:** The jq transformation is correct. No finding.

---

### F8 (MEDIUM) — Pre-check Returns `0` for "Already Excluded" Without Verifying DB Consistency

**Location:** `_interspect_approve_override`, lines 1193-1196

**Code:**
```bash
# Check if already excluded (idempotent)
if jq -e --arg agent "$agent" '.overrides[] | select(.agent == $agent and .action == "exclude")' "$fullpath" >/dev/null 2>&1; then
    echo "INFO: ${agent} is already excluded. Nothing to approve."
    return 0
fi
```

When the pre-check finds an existing `exclude` entry and returns 0, it skips the flock entirely. This is the "already excluded" fast path. It is a valid idempotency optimisation.

However, this path does not verify whether the `modifications` or `canary` DB records exist for that `exclude` entry. If the split-brain from F2 occurred in a prior call (commit succeeded, DB insert failed), this fast path will silently confirm success to the user and never attempt to repair the missing DB records.

This is not a new failure mode introduced by the approve function — it is the residue of F2 materialising. If F2 is fixed by making the `modifications` INSERT non-fatal with a warning, the user would have been warned at the time and could run a repair path. Without fixing F2, the idempotency path at F8 makes the missing DB records permanent.

**Severity: MEDIUM** — Dependent on F2. If F2 is fixed, F8 becomes informational.

---

### F9 (INFORMATIONAL) — Command File Uses `find` to Locate `lib-interspect.sh`

**Location:** `/home/mk/projects/Demarch/os/clavain/commands/interspect-approve.md`, lines 16-17

**Code:**
```bash
INTERSPECT_LIB=$(find ~/.claude/plugins/cache -path '*/clavain/*/hooks/lib-interspect.sh' 2>/dev/null | head -1)
[[ -z "$INTERSPECT_LIB" ]] && INTERSPECT_LIB=$(find ~/projects -path '*/os/clavain/hooks/lib-interspect.sh' 2>/dev/null | head -1)
```

`find` returns results in filesystem order, which is non-deterministic. If there are multiple plugin cache entries (e.g., two versions installed during a blue-green rollout), `head -1` silently picks an arbitrary one. The fallback to `~/projects` is also a broad search. This pattern is identical across other interspect commands, so it is a systemic issue rather than new to the approve command.

The risk: if an older cached version of `lib-interspect.sh` is found first, the `_interspect_approve_override` called will be the older version, which may not have the `_interspect_approve_override` function at all (if it was just added). The error will be a cryptic "command not found" rather than a version mismatch notice.

**Recommendation:** Sort by modification time (`find ... | xargs ls -t | head -1`) or lock to a known version path. This aligns with the CLAUDE.md note that older cached plugin versions can be stale.

**Severity: INFORMATIONAL** — Affects reliability of command dispatch, not correctness of the reviewed functions.

---

### F10 (LOW) — SQL Injection via Unescaped `$confidence` and Numeric Fields

**Location:** `_interspect_approve_override_locked`, lines 1350-1351 and 1388-1389

**Code:**
```bash
sqlite3 "$db" "INSERT INTO modifications (..., confidence, ...) VALUES (..., ${confidence}, ...);"
sqlite3 "$db" "INSERT INTO canary (..., window_uses, ...) VALUES (..., ${_INTERSPECT_CANARY_WINDOW_USES:-20}, ...);"
```

`$confidence` is set by `awk`:
```bash
confidence=$(awk -v w="$wrong" -v t="$total" 'BEGIN {printf "%.2f", w/t}')
```

`$wrong` and `$total` are outputs of `sqlite3` COUNT queries on sanitised data. `awk`'s `printf "%.2f"` produces exactly a decimal float with two digits. This cannot produce SQL-injectable output.

`$_INTERSPECT_CANARY_WINDOW_USES` is either unset (defaulting to `20`) or set from `_interspect_load_confidence` which reads from a JSON config file. If the config file is user-controlled and contains a malformed `window_uses` value, injection is theoretically possible. In practice, `_interspect_load_confidence` reads via `jq -r`, which would produce a numeric string or `null`. The `:-20` default handles null. A non-numeric value from `jq -r` would cause a SQLite syntax error (not injection) since there are no quotes around the value. This is a defence-in-depth concern rather than an exploitable path given the current config structure.

`_interspect_sql_escape` is correctly applied to all string-typed values: `escaped_agent`, `escaped_reason`, `escaped_bwindow`, `commit_sha` (which is a hex SHA, safe without escaping).

`$filepath` is NOT escaped in the INSERT on line 1350 and 1388. `filepath` is derived from `FLUX_ROUTING_OVERRIDES_PATH` (environment variable) or the default `.claude/routing-overrides.json`. It passes `_interspect_validate_overrides_path` which rejects absolute paths and path traversal. However, it does not reject single quotes. A `filepath` containing a single quote would produce broken SQL. In practice the default path has no single quotes, and `_interspect_validate_overrides_path` constrains the format, but an explicit allowlist regex that also excludes quotes would make this fully safe.

**Severity: LOW** — Not exploitable through current write paths but missing defensive escaping for `$filepath` in INSERT statements.

---

## Summary Table

| ID | Location | Severity | Description |
|----|----------|----------|-------------|
| F1 | `_interspect_approve_override` L1191-1204 | LOW | TOCTOU fast-path race, but locked function re-checks; confusing error message under concurrent revert |
| F2 | `_interspect_approve_override_locked` L1350-1351 | HIGH | Unguarded `sqlite3` INSERT under `set -e` — DB failure after git commit leaves split-brain state |
| F3 | `_interspect_approve_override_locked` L1280-1281 | MEDIUM | Confidence query misses `interflux:fd-*` and `interflux:review:fd-*` agent name variants |
| F4 | `_interspect_apply_override_locked` L941 | LOW | `cd "$root"` instead of `git -C "$root"` — fails silently under `set -e` if root disappears |
| F5 | `_interspect_apply_override_locked` L955 | LOW | `escaped_reason` assigned without `local` declaration |
| F6 | `_interspect_approve_override_locked` L1344-1355 | LOW | Baseline `before_ts` uses post-commit timestamp; sub-millisecond gap is negligible |
| F7 | `_interspect_approve_override_locked` L1310-1317 | NONE | jq `map/if` promotion is correct; no finding |
| F8 | `_interspect_approve_override` L1193-1196 | MEDIUM | Idempotency fast-path does not detect or repair split-brain DB state from F2 |
| F9 | `interspect-approve.md` L16-17 | INFO | Non-deterministic `find` for library location could load stale cached version |
| F10 | `_interspect_approve_override_locked` L1350, 1388 | LOW | `$filepath` interpolated into SQL without `_interspect_sql_escape` |

---

## Priority Fixes

### Fix 1 (Addresses F2, root cause of F8)

In `_interspect_approve_override_locked`, guard the `modifications` INSERT the same way the `canary` INSERT is already guarded:

```bash
# Step 8 — was unguarded, now non-fatal
if ! sqlite3 "$db" "INSERT INTO modifications (group_id, ts, tier, mod_type, target_file, commit_sha, confidence, evidence_summary, status)
    VALUES ('${escaped_agent}', '${ts}', 'persistent', 'routing', '${filepath}', '${commit_sha}', ${confidence}, '${escaped_reason}', 'applied');"; then
    echo "WARN: Modification record failed — override committed to git but not tracked in DB. Manual repair may be needed." >&2
fi
```

### Fix 2 (Addresses F3)

Replace the single-variant confidence queries in both `_interspect_approve_override_locked` (lines 1280-1281) and `_interspect_apply_override_locked` (lines 887-888) with the three-variant pattern from `_interspect_is_routing_eligible`:

```bash
total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped_agent}' OR source = 'interflux:${escaped_agent}' OR source = 'interflux:review:${escaped_agent}') AND event = 'override';")
wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped_agent}' OR source = 'interflux:${escaped_agent}' OR source = 'interflux:review:${escaped_agent}') AND event = 'override' AND override_reason = 'agent_wrong';")
```

### Fix 3 (Addresses F4)

In `_interspect_apply_override_locked`, replace lines 941-942:
```bash
# Before
cd "$root"
git add "$filepath"

# After (matches the pattern in all other locked functions)
git -C "$root" add "$filepath"
```

### Fix 4 (Addresses F5)

In `_interspect_apply_override_locked`, add the missing `local` declaration at line 955:
```bash
local escaped_reason
escaped_reason=$(_interspect_sql_escape "$reason")
```

### Fix 5 (Addresses F10)

Escape `$filepath` before SQLite insertion in both `_interspect_approve_override_locked` and `_interspect_apply_override_locked`:
```bash
local escaped_filepath
escaped_filepath=$(_interspect_sql_escape "$filepath")
# Then use '${escaped_filepath}' in INSERT statements
```

---

## Comparison with Sibling Functions

| Concern | `_interspect_apply_override_locked` | `_interspect_apply_propose_locked` | `_interspect_approve_override_locked` |
|---------|-------------------------------------|-------------------------------------|---------------------------------------|
| `git -C` vs `cd` | Uses `cd "$root"` (F4 — regression) | Uses `git -C "$root"` (correct) | Uses `git -C "$root"` (correct) |
| Unguarded sqlite3 INSERT | Yes (modifications) | N/A (no DB writes) | Yes (modifications) — F2 |
| Confidence multi-variant query | No (F3) | N/A | No (F3) |
| `local` for `escaped_reason` | Missing (F5) | N/A | Present (correct) |
| `$filepath` SQL escape | Missing (F10) | N/A | Missing (F10) |
| Dedup strategy | `unique_by(.agent)` | exit 2 on any existing entry | exit 2 on `exclude`; in-place map on `propose` |
| Rollback on commit failure | Works (uses `cd "$root"` already so git commands inherit CWD) | Works (git -C) | Works (git -C) |

The `_interspect_approve_override_locked` function is structurally the cleanest of the three, correctly using `git -C`, correctly scoping `local escaped_reason`, and using the correct `map/if` pattern for in-place promotion. The two issues it shares with its siblings are F2 (unguarded `modifications` INSERT) and F3 (single-variant confidence query).
