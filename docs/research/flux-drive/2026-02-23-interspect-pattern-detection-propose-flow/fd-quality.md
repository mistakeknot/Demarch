# Quality Review: Interspect Pattern Detection + Propose Flow

**Plan:** `docs/plans/2026-02-23-interspect-pattern-detection-propose-flow.md`
**Reviewer:** Flux-drive Quality & Style
**Date:** 2026-02-23
**Scope:** 4 new functions + 16 tests targeting `os/clavain/hooks/lib-interspect.sh` and `os/clavain/tests/shell/test_interspect_routing.bats`

---

## Summary

The plan is structurally sound and follows the project's Bash/SQLite/bats patterns well. Three issues require fixes before implementation: a correctness bug in the propose-dedup signal path, a missing `_interspect_load_confidence` call in `get_routing_eligible`, and an inconsistent merge strategy in `apply_propose_locked`. The remaining findings are lower-priority but worth addressing.

---

## Findings

### 1. CORRECTNESS — Dedup signal path breaks when caller checks exit code

**Severity: Bug (must fix)**

**File:** `docs/plans/2026-02-23-interspect-pattern-detection-propose-flow.md` — Task 3, `_interspect_apply_propose` and `_interspect_apply_propose_locked`

The locked function returns `ALREADY_EXISTS` on stdout and `return 0`, so `_interspect_flock_git` exits 0. The outer function then reaches this block:

```bash
local commit_sha
commit_sha=$(echo "$flock_output" | tail -1)

echo "SUCCESS: Proposed excluding ${agent}. Commit: ${commit_sha}"
```

When `flock_output` is `"ALREADY_EXISTS"`, `commit_sha` becomes the literal string `"ALREADY_EXISTS"` and the function prints `"SUCCESS: Proposed excluding fd-game-design. Commit: ALREADY_EXISTS"` — which is wrong and will confuse callers.

The test for the dedup case (`apply_propose skips if override already exists`) uses `run _interspect_apply_propose ...` and asserts `grep -qi "already exists"` against `$output`. This assertion relies on the `INFO:` message printed to stderr inside the locked function — but `run` in bats captures stdout only by default. The test may pass incidentally in some configurations but is fragile.

**Fix:** Follow the pattern used in `_interspect_apply_routing_override`: distinguish dedup from success before printing. Either:

(a) Parse `flock_output` for the sentinel before extracting `commit_sha`:
```bash
if echo "$flock_output" | grep -q "^ALREADY_EXISTS$"; then
    echo "INFO: Override for ${agent} already exists (propose or exclude). Skipping." >&2
    return 0
fi
local commit_sha
commit_sha=$(echo "$flock_output" | tail -1)
```

(b) Or route the `INFO:` message to stdout instead of stderr inside the locked function so the test assertion works reliably. Routing to stdout is the simpler fix since the test uses it without `2>&1`.

The test assertion should also be updated to match whichever output stream carries the message:
```bash
run _interspect_apply_propose "fd-game-design" "test" '[]' "interspect"
[ "$status" -eq 0 ]
echo "$output" | grep -qi "already"  # only works if message is on stdout
```

---

### 2. CORRECTNESS — `_interspect_get_routing_eligible` omits `_interspect_load_confidence` call

**Severity: Bug (must fix)**

**File:** Plan, Task 1 — `_interspect_get_routing_eligible` implementation

The function calls `_interspect_is_routing_eligible "$src"`, which in turn calls `_interspect_load_confidence` internally. However `_interspect_get_routing_eligible` also computes `total`, `wrong`, and `pct` directly from SQLite without calling `_interspect_load_confidence` first. This is currently harmless because `_INTERSPECT_MIN_AGENT_WRONG_PCT` is not used in the pct computation — pct is only included in output, not compared. But the companion function `_interspect_get_overlay_eligible` *does* call `_interspect_load_confidence` explicitly (line 217 of the plan: `_interspect_load_confidence`). The inconsistency is a maintenance hazard: if a threshold comparison is added to `get_routing_eligible` later, its absence will silently use whatever the process-level default is.

**Fix:** Add `_interspect_load_confidence` at the top of `_interspect_get_routing_eligible`, matching the pattern in `_interspect_get_overlay_eligible` and `_interspect_is_routing_eligible`:

```bash
_interspect_get_routing_eligible() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    [[ -f "$db" ]] || return 0
    _interspect_load_confidence   # add this line
    ...
```

---

### 3. CORRECTNESS — Inconsistent merge strategy in `apply_propose_locked` vs `apply_override_locked`

**Severity: Correctness risk**

**File:** Plan, Task 3 — `_interspect_apply_propose_locked`

`_interspect_apply_override_locked` uses `unique_by(.agent)` on merge, which means a concurrent duplicate is silently deduplicated at the JSON level — last write wins for metadata:

```bash
# apply_override_locked (existing, line 797-798)
merged=$(echo "$current" | jq --argjson override "$new_override" \
    '.overrides = (.overrides + [$override] | unique_by(.agent))')
```

`_interspect_apply_propose_locked` uses a simple append and relies entirely on the in-lock dedup check (lines 433-439 of plan) to prevent duplicates. Under the same lock this is fine, but the append-without-`unique_by` means that if the dedup check ever has a gap (e.g., concurrent process using a different lock path, manual file edit), two propose entries for the same agent will accumulate silently.

Since proposals are informational-only and `_override_exists` checks for *any* action (`exclude` or `propose`), the risk is low. But the inconsistency creates a subtle behavioral difference: applying an override is idempotent (upserts), while applying a proposal is strictly once. Document this intentional difference with a comment, or adopt `unique_by` for defensive consistency:

```bash
# Merge — append-only (proposals are not upserted; dedup enforced above inside lock)
merged=$(echo "$current" | jq --argjson override "$new_override" \
    '.overrides = (.overrides + [$override])')
```

At minimum, add the comment so the next implementer doesn't assume they should match the override pattern.

---

### 4. BASH IDIOM — Associative arrays not used elsewhere in lib-interspect.sh

**Severity: Low (compatibility note)**

**File:** Plan, Task 2 — `_interspect_get_overlay_eligible` implementation

The plan introduces `local -A agent_total agent_wrong agent_sessions agent_projects` — associative arrays. Searching `lib-interspect.sh` finds zero existing uses of `declare -A` or `local -A`. The file uses indexed arrays (`_INTERSPECT_PROTECTED_PATHS=()`) and plain string vars.

Bash 4+ associative arrays work fine on this Linux environment. The concern is:

- The `for src in "${!agent_total[@]}"` loop enumerates keys in **hash order** (non-deterministic). Test output will vary between runs. The tests do not sort results, so assertions like `grep -q "fd-overlay-test"` are fine — but any future test asserting output ordering would be brittle.
- `local -A` is technically valid but unusual in this codebase. If the coding style is eventually enforced with `shellcheck`, `local -A` inside a function is correctly handled since bash 4.2.

No change required, but add a comment noting the non-deterministic iteration order. If the function eventually needs deterministic output (e.g., for display), a sort step will be needed.

---

### 5. BASH IDIOM — `local` inside the `while` loop body in `get_routing_eligible`

**Severity: Acceptable (matches existing precedent)**

The plan declares `local eligible_result`, `local escaped`, `local total wrong pct` inside the `while IFS='|' read -r` loop. This is redundant (locals persist for the function's lifetime regardless of loop iteration), but it is already the established pattern in `_interspect_get_classified_patterns` (line 417: `local cls` inside a while loop). No change needed — the plan is consistent with the codebase.

---

### 6. TEST — Conditional `! grep -q` assertions are non-fatal

**Severity: Low (test reliability)**

**File:** Plan, Tasks 1 and 2 — multiple tests

Several tests guard exclusion assertions with `if [ -n "$result" ]; then`:

```bash
result=$(_interspect_get_routing_eligible)
if [ -n "$result" ]; then
    ! echo "$result" | grep -q "fd-test-agent"
fi
```

When `$result` is empty, the test body is skipped and the test passes vacuously. This is appropriate for the "excludes agents below threshold" cases where empty output is the expected outcome — but the test name does not convey which outcome was actually validated. The existing test suite does not use this pattern; instead it explicitly asserts `[ -z "$result" ]` for the empty case (as in `get_routing_eligible returns empty on no evidence`).

For the exclusion tests, the intent is: "result is not empty, AND does not contain the agent". The current guard loses the "result is not empty" part. Consider:

```bash
# get_routing_eligible excludes agents below 80% wrong
result=$(_interspect_get_routing_eligible)
# With 6 events and a different agent in scope, result may be empty or contain other agents.
# Either is acceptable — the one assertion is that fd-test-agent is absent.
! echo "$result" | grep -q "fd-test-agent"
```

Removing the `if` guard and unconditionally running the negative assertion is cleaner. If `$result` is empty, `grep -q "fd-test-agent"` returns 1, and `! 1` is 0 — test passes correctly without silent skip.

---

### 7. TEST — Task 3 test for `apply_propose_locked` does not commit-stage `.claude` directory

**Severity: Low (test correctness)**

**File:** Plan, Task 3 — `"apply_propose writes propose action to routing-overrides.json"` test

The test calls `_interspect_apply_propose` and then asserts `git log --oneline -1 | grep -q "Propose excluding fd-game-design"`. The locked function does `cd "$root" && git add "$filepath" && git commit --no-verify -F ...`. For this to work, `$TEST_DIR` must be the git root and `$filepath` (`.claude/routing-overrides.json`) must be a relative path resolvable from there.

The setup in the existing test suite (`cd "$TEST_DIR"` in setup, `git init -q`, empty initial commit) provides this. However, the `.claude/` directory does not exist before the call — the locked function creates it with `mkdir -p`. This is fine, but the test does not assert that `$root/.claude/routing-overrides.json` actually exists after the call. Adding that assertion makes the test more specific and easier to debug on failure:

```bash
local root
root=$(git rev-parse --show-toplevel)
[ -f "$root/.claude/routing-overrides.json" ]
```

This pattern is already used in `revert_routing_override removes override and commits` in the existing tests.

---

### 8. NAMING — `_interspect_apply_propose_locked` naming vs `_interspect_apply_override_locked`

**Severity: Minor (consistency)**

The existing locked function is `_interspect_apply_override_locked`. The plan introduces `_interspect_apply_propose_locked`. The suffix `_locked` is consistent. The prefix difference (`_apply_propose` vs `_apply_override`) correctly reflects the different action type. No change needed — this is the right naming.

However, `_interspect_get_routing_eligible` and `_interspect_get_overlay_eligible` follow the `_get_` prefix naming scheme consistently with how `_interspect_get_classified_patterns` and `_interspect_get_canary_summary` are named. This is good — the plan respects the existing vocabulary.

---

### 9. ERROR HANDLING — `_interspect_is_cross_cutting` hardcodes four agent names with no extension point

**Severity: Design note**

**File:** Plan, Task 4 — `_interspect_is_cross_cutting`

The implementation uses a `case` statement with four literal names:

```bash
case "$agent" in
    fd-architecture|fd-quality|fd-safety|fd-correctness) return 0 ;;
    *) return 1 ;;
esac
```

This is the correct pattern for a simple, stable set. The existing `_interspect_validate_agent_name` uses a regex (`^fd-[a-z][a-z0-9-]*$`) for open-ended validation. The cross-cutting list is intentionally closed — architectural agents that get extra safety gates. The `case` approach is appropriate and consistent with how the rest of this codebase handles fixed allowlists (see `_interspect_validate_hook_id`).

No change needed, but document in the function comment that the list is intentionally static and should be updated manually when new structural agents are added:

```bash
# Cross-cutting agents are those whose absence would leave entire concern categories
# uncovered. This list is INTENTIONALLY STATIC — add new agents only after deliberate
# architectural review. Do not derive this list from the DB.
```

---

## Not Flagged

- The arithmetic ternary `$(( total > 0 ? wrong * 100 / total : 0 ))` is valid bash 4+ and matches the identical pattern at line 511 of `lib-interspect.sh` in `_interspect_is_routing_eligible`. No issue.
- The `set -e` in locked functions is consistent with `_interspect_apply_override_locked` and `_interspect_revert_override_locked`. Correct.
- The `printf` pattern for commit messages (rather than heredocs) matches the existing `_interspect_apply_routing_override` and avoids the settings-hygiene issue documented in global CLAUDE.md.
- The `_interspect_validate_target` call in `apply_propose` matches `apply_routing_override`. Both protect against the modification allow-list enforcement.
- The `local` declaration of `src` before the associative array `for` loop in `get_overlay_eligible` (`local src`) is correct — it shadows the outer `src` variable cleanly.

---

## Priority Summary

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| 1 | Dedup signal path: `ALREADY_EXISTS` leaks into `commit_sha` | Bug | Fix before implementation |
| 2 | Missing `_interspect_load_confidence` in `get_routing_eligible` | Bug | Fix before implementation |
| 3 | Inconsistent merge strategy (append vs `unique_by`) | Correctness risk | Add comment or adopt `unique_by` |
| 4 | Associative array hash order non-deterministic | Compat note | Add comment |
| 5 | `local` inside loop | Matches precedent | No change |
| 6 | Vacuous exclusion test guards | Test reliability | Remove `if` guard, use unconditional `!` assertion |
| 7 | Test missing file-existence assertion | Test clarity | Add `[ -f "$root/.claude/routing-overrides.json" ]` |
| 8 | Naming consistency | Good | No change |
| 9 | `is_cross_cutting` static list undocumented | Design note | Add comment |
