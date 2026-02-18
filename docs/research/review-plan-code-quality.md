# Code Quality Review: Intercore Hook Adapter Plan

**Plan:** `docs/plans/2026-02-18-intercore-hook-adapter.md`
**Date:** 2026-02-17
**Reviewer:** Flux-drive Quality & Style Reviewer

## Executive Summary

This plan migrates Clavain's 6 hooks from `/tmp/clavain-*` temp files to intercore DB sentinels via bash wrappers. The architecture is sound: fail-safe wrappers, transparent fallback, and incremental migration. The code patterns are idiomatic and consistent with the existing codebase.

**Overall assessment:** P1-P2 severity only. No P0 blocking issues. Most findings are preventive guidance and naming clarifications.

---

## Universal Quality Checks

### P1: Naming Consistency

**Finding 1.1:** The plan uses `intercore_sentinel_check_or_legacy` but describes copying `lib-intercore.sh` to Clavain hooks. This creates TWO versions of the library: the source in `infra/intercore/lib-intercore.sh` (extended with new functions) and the copy in `hub/clavain/hooks/lib-intercore.sh`. The plan doesn't specify how to keep them in sync.

**Impact:** When new wrappers are added to the intercore library (Task 7 adds `intercore_sentinel_reset_all`), the Clavain copy diverges unless manually re-copied. This is a maintenance hazard.

**Recommendation:**
Either (a) document that Clavain's copy is a snapshot pinned to the plugin release, updated only via manual re-copy + version bump, OR (b) use a symlink or install-time copy script. The plan mentions "the library version is pinned to the Clavain release, which is the correct semantic" — this is good, but **add a comment in the copy** stating:
```bash
# lib-intercore.sh — Snapshot from infra/intercore/lib-intercore.sh
# Last synced: 2026-02-XX (iv-wo1t)
# Re-copy on major intercore updates; version is pinned to plugin release.
```

**Finding 1.2:** The mapping table uses names like `compound_throttle` and `drift_throttle`, but these are never defined anywhere in the plan text. They appear only in the table. For consistency, document that these names are INTERNAL sentinel keys and won't collide with user-facing names because they're scoped to `clavain:hooks` namespace (implicitly).

**Recommendation:** Add a note after the mapping table:
```
Sentinel names are internal to Clavain hooks and isolated by scope_id (usually session ID).
No namespace collisions with user-facing keys because hooks use session scope.
```

### P1: Error Handling Patterns

**Finding 2.1:** Task 1 adds `intercore_sentinel_check_or_legacy` with a legacy fallback that uses `stat -c %Y` (GNU) / `stat -f %m` (BSD). This pattern exists in `auto-compound.sh` lines 58-59 and is correct. However, the plan's version has a subtle bug:

```bash
file_mtime=$(stat -c %Y "$legacy_file" 2>/dev/null || stat -f %m "$legacy_file" 2>/dev/null || echo 0)
```

This is correct. But the plan doesn't show the initialization pattern used in existing hooks:
```bash
insert_status=0
sqlite3 "$DB" "INSERT ..." >/dev/null 2>&1 || insert_status=$?
```

For the `stat` fallback, the `|| echo 0` is sufficient — no need for pre-initialization. **This is actually correct as-is.** No change needed, but worth documenting that `|| echo 0` is the right pattern for command substitution fallbacks (not `status=0; cmd || status=$?` which is for separate status variables).

**Finding 2.2:** `intercore_sentinel_reset_or_legacy` uses:
```bash
# shellcheck disable=SC2086
rm -f $legacy_glob 2>/dev/null || true
```

The `SC2086` disable is correct because `legacy_glob` is intentionally unquoted to allow glob expansion (`/tmp/clavain-*.cache`). However, **this is unsafe if `legacy_glob` contains spaces or special characters**. The plan passes literal glob strings like `"/tmp/clavain-discovery-brief-*.cache"` (quoted in the call), so when the function receives it, the `$legacy_glob` is a single string with a literal `*` that bash should expand.

**BUT:** If `legacy_glob` is `"/tmp/clavain-catalog-remind-${_SID}.lock"` (a single file, no glob), the unquoted `rm -f $legacy_glob` is also correct. The plan's usage is **correct** because all callers pass safe `/tmp/clavain-*` patterns. No change needed, but verify that all call sites pass safe paths.

**Verified:** All 6 hooks use `/tmp/clavain-<pattern>` with no user-controlled segments. Safe.

**Finding 2.3:** Task 7 adds `intercore_sentinel_reset_all` which loops over `ic sentinel list` output using `while IFS=$'\t' read -r _name scope _fired`. The plan doesn't handle errors if `ic sentinel list` fails mid-stream (partial output). The `|| true` at the end makes the function return 0 even if the list command fails entirely, which is fail-safe. **Correct.**

However, the loop has a logic bug:
```bash
while IFS=$'\t' read -r _name scope _fired; do
    [[ "$_name" == "$name" ]] || continue
    "$INTERCORE_BIN" sentinel reset "$name" "$scope" >/dev/null 2>&1 || true
done < <("$INTERCORE_BIN" sentinel list 2>/dev/null || true)
```

The `|| true` on the process substitution means if `sentinel list` fails, the loop receives **empty input** and silently succeeds. This is fail-safe (falls through to legacy `rm`), but it's worth noting. No change needed — this is the correct fail-safe pattern.

**Finding 2.4:** The plan uses `type intercore_sentinel_check_or_legacy &>/dev/null` as a guard before calling the function. This is correct — `type` checks if the function exists. However, **the plan sources lib-intercore.sh unconditionally** in all hooks:
```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
```

If the source succeeds, the `type` check is redundant — the function WILL exist. If the source fails, the `type` check correctly prevents calls to an undefined function. This is **defensive redundancy**, which is good in bash. No change needed.

**But:** The plan's Task 2 revised approach copies lib-intercore.sh into the hooks directory, so the source will ALWAYS succeed (file exists locally). The `type` check becomes truly redundant — it's only checking "did source succeed", not "is ic available". The **real** availability check happens inside `intercore_sentinel_check_or_legacy` via `intercore_available`.

**Recommendation:** The `type ... &>/dev/null` checks are safe but unnecessary given the always-present local copy. You can simplify to:
```bash
source "${BASH_SOURCE[0]%/*}/lib-intercore.sh" 2>/dev/null || true
intercore_sentinel_check_or_legacy "catalog_remind" "$_SID" 0 "/tmp/clavain-catalog-remind-${_SID}.lock" || exit 0
```

The function will ALWAYS exist (it's in the local file), and `intercore_available` inside the function handles the `ic` binary check. The `type` guard was useful when `lib-intercore.sh` was in a different repo location — now it's just extra. But leaving it in is harmless and adds no runtime cost.

**Verdict:** Keep the `type` checks for defensive safety, but document that they're redundant noise once the local copy is in place. Alternatively, remove them for cleaner code. Either choice is valid.

### P2: File Organization

**Finding 3.1:** Task 1 extends `infra/intercore/lib-intercore.sh` with three new functions, then Task 2 copies the file to `hub/clavain/hooks/lib-intercore.sh`. Task 7 adds ANOTHER function (`intercore_sentinel_reset_all`) to `infra/intercore/lib-intercore.sh`.

The plan has Task 7 committing changes to **both** files:
```bash
git add hub/clavain/hooks/lib-sprint.sh infra/intercore/lib-intercore.sh
```

But it doesn't show re-copying the extended lib-intercore.sh to the Clavain hooks directory. **This is a task ordering bug.**

**Impact:** After Task 7, `infra/intercore/lib-intercore.sh` has 4 new functions (from Task 1) + 1 more (from Task 7) = 5 total. But `hub/clavain/hooks/lib-intercore.sh` (copied in Task 2) only has the first 4. The hooks in Tasks 3-6 call `intercore_sentinel_check_or_legacy` (defined in Task 1, present in the copy), so they work. But `lib-sprint.sh` (Task 7) calls `intercore_sentinel_reset_all` (added in Task 7), which is **not yet in the Clavain copy**.

**Fix:** Task 7 Step 1 should read:
```
Step 1: Add intercore_sentinel_reset_all to infra/intercore/lib-intercore.sh, then re-copy to hub/clavain/hooks/lib-intercore.sh
```

Alternatively, move Task 7's function addition to Task 1, so the initial copy includes all 4 functions. Then Task 7 just uses it.

**Recommendation:** **Move `intercore_sentinel_reset_all` to Task 1.** It's a general-purpose wrapper like the others. Define all 4 functions in Task 1, copy once in Task 2, use everywhere. Cleaner.

### P2: Test Strategy

**Finding 4.1:** Task 1 extends the integration test with wrapper tests. The test pattern is:
```bash
intercore_sentinel_check_or_legacy "wrapper_test" "test-session" 0 "/tmp/clavain-wrapper-test" && pass "first check allowed" || fail "should be allowed"
intercore_sentinel_check_or_legacy "wrapper_test" "test-session" 0 "/tmp/clavain-wrapper-test" && fail "should be throttled" || pass "second check throttled"
```

This tests the **intercore path** (ic available). It doesn't test the **legacy fallback path** (ic unavailable). The plan's integration test forces `INTERCORE_BIN="$IC_BIN"` so intercore is always available.

**Impact:** The legacy fallback code in `intercore_sentinel_check_or_legacy` (lines 62-76 of the planned function) is **never tested**. If there's a bug in the `stat` logic or the temp file logic, the test won't catch it.

**Recommendation:** Add a second test block that unsets `INTERCORE_BIN` and tests the legacy path:
```bash
# Test legacy fallback (no ic binary)
INTERCORE_BIN=""
intercore_sentinel_check_or_legacy "legacy_test" "test-session" 0 "/tmp/clavain-legacy-test" && pass "legacy: first check allowed" || fail "legacy: should be allowed"
[[ -f "/tmp/clavain-legacy-test" ]] && pass "legacy: sentinel created" || fail "legacy: sentinel missing"
intercore_sentinel_check_or_legacy "legacy_test" "test-session" 0 "/tmp/clavain-legacy-test" && fail "legacy: should be throttled" || pass "legacy: second check throttled"
rm -f /tmp/clavain-legacy-test
INTERCORE_BIN="$IC_BIN"  # restore
```

This exercises the temp-file codepath.

**Finding 4.2:** Task 8 runs `bash -n` syntax checks on all hooks but doesn't test them **in a real session**. The syntax check only catches parse errors, not logic errors (e.g., wrong variable names, missing functions, incorrect jq paths).

**Recommendation:** Add a smoke test that sources each hook script and calls any exported functions with dummy inputs. For example:
```bash
# Smoke test catalog-reminder.sh
source hub/clavain/hooks/lib-intercore.sh
INTERCORE_BIN="" CLAUDE_SESSION_ID="test-smoke" bash hub/clavain/hooks/catalog-reminder.sh <<< '{"tool_input":{"file_path":"commands/test.md"}}'
# Should exit 0 (success) and create a sentinel
```

This is LOW priority (P2) because syntax checks + integration tests already give high confidence. But it's worth considering for a future task.

---

## Bash-Specific Checks

### P1: `set -euo pipefail` Compliance

**Finding 5.1:** All existing hooks use `set -euo pipefail` at the top. The plan's new wrapper functions are in `lib-intercore.sh`, which is **sourced**, not executed. The plan correctly notes:
```bash
# lib-intercore.sh — Bash wrappers for intercore CLI
# This file is SOURCED by hooks. Do NOT use set -e here — it would exit
# the parent shell on any failure.
```

This is correct. No `set -e` in sourced libraries. **Good.**

**Finding 5.2:** The plan's wrapper functions use `|| true` and `|| return 0` extensively to prevent failures from propagating. This is correct for a sourced library under `set -e`. The existing `lib-intercore.sh` (lines 1-44 in the Read output) follows the same pattern. **Consistent.**

### P1: jq Null Safety

**Finding 6.1:** The hooks read JSON input via:
```bash
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
```

This uses `// "unknown"` and `// empty` for null handling. Correct. The plan doesn't change any jq pipelines, so no new null-slice bugs introduced. **Safe.**

### P2: Quoting and Expansion

**Finding 7.1:** The plan uses `"${BASH_SOURCE[0]%/*}/lib-intercore.sh"` to derive the hook directory. This is correct — `BASH_SOURCE[0]` is the sourcing script's path, `%/*` strips the filename, leaving the directory. Always quoted. **Good.**

**Finding 7.2:** The `rm -f $legacy_glob` line (Finding 2.2) is intentionally unquoted for glob expansion. All call sites pass `/tmp/clavain-*` patterns — no user input. **Safe.**

### P2: Portability (stat)

**Finding 8.1:** The `stat -c %Y ... || stat -f %m ...` pattern is already used in `auto-compound.sh` and `auto-drift-check.sh`. The plan's new wrapper uses the same pattern. Portable across GNU (Linux) and BSD (macOS). **Good.**

---

## Test Coverage Assessment

### P1: Integration Test Gaps

**Finding 9.1:** (Duplicate of Finding 4.1) — No legacy fallback test. Add test with `INTERCORE_BIN=""`.

**Finding 9.2:** Task 1 Step 4 expects "All tests pass including new wrapper tests". But the existing `test-integration.sh` (lines 1-98) has a hardcoded "All integration tests passed" message at the end. The plan says to add the new tests **before** that line, which is correct. But the plan's test snippet uses `pass "..."` and `fail "..."` helpers that are defined at the top of `test-integration.sh`. **This is correct** — the new tests will use the same helpers.

**Verified.** No issue.

---

## Consistency with Existing Hooks

### P0: Sentinel Name Collisions

**Finding 10.1:** The plan maps temp file names to sentinel keys:
- `/tmp/clavain-stop-$SID` → `stop`
- `/tmp/clavain-handoff-$SID` → `handoff`
- `/tmp/clavain-compound-last-$SID` → `compound_throttle`
- `/tmp/clavain-drift-last-$SID` → `drift_throttle`
- `/tmp/clavain-autopub.lock` → `autopub`
- `/tmp/clavain-catalog-remind-$SID.lock` → `catalog_remind`
- `/tmp/clavain-discovery-brief-*.cache` → `discovery_brief`

The `stop` sentinel is **shared across multiple hooks** (session-handoff, auto-compound, auto-drift-check). In the temp-file implementation, they all check the same file `/tmp/clavain-stop-$SID`. In the intercore implementation, they all call:
```bash
intercore_sentinel_check_or_legacy "stop" "$SESSION_ID" 0 "/tmp/clavain-stop-${SESSION_ID}"
```

This is correct — same key `"stop"`, same scope `$SESSION_ID`, so the first hook to fire claims it, and subsequent hooks are throttled. **Semantics preserved.** No collision issue.

**Verified.** No issue.

### P2: Sentinel Cleanup

**Finding 11.1:** The plan's `intercore_cleanup_stale` calls:
```bash
"$INTERCORE_BIN" sentinel prune --older-than=1h >/dev/null 2>&1 || true
```

But `ic sentinel prune` is not shown in the plan's intercore CLI commands (the plan references `sentinel check`, `sentinel reset`, `sentinel list`). The integration tests don't test `prune`.

**Impact:** If `ic sentinel prune` doesn't exist yet, this command will fail silently (`|| true`) and fall through to the legacy cleanup. This is **fail-safe**, but it means the intercore DB will accumulate stale sentinels indefinitely.

**Recommendation:** Verify that `ic sentinel prune` exists. If not, either (a) add it to the intercore CLI in a prior task, or (b) change the cleanup to use `sentinel list + sentinel reset` in a loop (same pattern as `intercore_sentinel_reset_all`).

**Alternative:** Check the intercore CLI code to see if `prune` exists.

**ACTION REQUIRED:** Verify `ic sentinel prune` command exists or add it.

---

## Style and Idioms

### P2: Function Naming

**Finding 12.1:** The wrapper functions are named:
- `intercore_sentinel_check_or_legacy`
- `intercore_sentinel_reset_or_legacy`
- `intercore_sentinel_reset_all`
- `intercore_cleanup_stale`

Three of these follow the pattern `intercore_<noun>_<verb>_or_legacy`. But `intercore_cleanup_stale` breaks the pattern — it's not `intercore_cleanup_stale_or_legacy`. This is intentional (cleanup has no direct legacy equivalent, it's a new behavior), but it's worth noting for consistency.

**Recommendation:** Rename to `intercore_sentinel_cleanup_stale` for consistency, OR document that `cleanup_stale` is a higher-level operation (not a direct wrapper). Either is fine.

**Severity:** P2 (style only).

### P2: Comment Density

**Finding 13.1:** The plan's new wrapper functions have minimal inline comments. The existing `lib-intercore.sh` (lines 1-44) has function-level comments like:
```bash
# intercore_state_set() {
#     local key="$1" scope_id="$2" json="$3"
```

The plan's new functions have multi-line header comments:
```bash
# intercore_sentinel_check_or_legacy — try ic sentinel, fall back to temp file.
# Args: $1=name, $2=scope_id, $3=interval_sec, $4=legacy_file (temp file path)
# Returns: 0 if allowed (proceed), 1 if throttled (skip)
# Side effect: touches legacy file as fallback when ic unavailable
```

This is **better** than the existing style (minimal comments). Good improvement. Consistent within the new code.

**Recommendation:** Apply the same header-comment style to the existing functions in lib-intercore.sh for consistency. **Out of scope for this plan**, but worth noting for future cleanup.

---

## Self-Correction Quality

### P2: Task 2 Revision

**Finding 14.1:** Task 2 initially tries to source `lib-intercore.sh` from the monorepo root using git, then realizes this is "over-engineered" and revises to **copy the file locally**. The revision reasoning is sound:
> "The hooks run inside the Clavain plugin, and the intercore binary `ic` is installed globally. The `lib-intercore.sh` wrappers just need `ic` on PATH. Simplest approach: **copy `lib-intercore.sh` into Clavain's hooks directory** so it's always available alongside the hooks."

This is correct. The revision improves clarity and robustness. **Good self-correction.**

### P2: Task 7 Revision

**Finding 14.2:** Task 7 initially tries to pass `"*"` as the scope_id for sentinel reset, then realizes:
> "The `*` scope_id for the sentinel reset means 'reset all scopes for this sentinel name'. Check if `ic sentinel reset` supports wildcards — if not, we need to use `ic sentinel list | grep discovery_brief` and reset each."

Then adds a new helper `intercore_sentinel_reset_all` that loops over `sentinel list` output. This is correct — SQL wildcards don't work in `DELETE WHERE scope_id = '*'` (matches literal `*`, not glob). **Good self-correction.**

**BUT:** This adds a new function in Task 7, which should have been in Task 1 (see Finding 3.1). The self-correction is good, but the task ordering is still wrong.

---

## Missing Considerations

### P2: Intercore Availability on Older Systems

**Finding 15.1:** The plan assumes `ic` is available on systems where Clavain is installed. If `ic` is not installed, all hooks fall back to temp files (legacy mode). This is correct and documented. But the plan doesn't address **what happens if a user upgrades Clavain but hasn't installed intercore yet**.

**Scenario:** User has Clavain v0.5.x (uses temp files). Upgrades to v0.6.0 (this plan). Clavain now sources `lib-intercore.sh` and calls `intercore_sentinel_check_or_legacy`. The function checks `intercore_available`, returns 1 (no `ic` binary), falls back to legacy. **Works correctly.**

No issue. The fail-safe design handles this. But it's worth documenting in the commit message or a migration note: "Hooks now prefer intercore DB when available, but fall back to temp files if `ic` is not installed. No user action required."

### P3: Performance (Negligible)

**Finding 16.1:** Each hook now sources `lib-intercore.sh` (50+ lines of bash functions) and calls `intercore_available` which runs `command -v ic` and `ic health`. This adds ~10ms latency per hook invocation compared to the direct temp-file check.

**Impact:** Negligible. Hooks run on SessionStart (once per session), PostToolUse (after writes/commits), and Stop (once per turn). Adding 10ms to a 100ms+ hook script is unnoticeable.

No change needed. Just noting for completeness.

---

## Summary of Findings

| Severity | Count | Category |
|----------|-------|----------|
| P0 | 0 | Blocking issues |
| P1 | 5 | High-priority fixes (sync comment, test coverage, task ordering) |
| P2 | 8 | Medium-priority improvements (naming, style, docs) |
| P3 | 1 | Low-priority notes (performance) |

### P1 Action Items (Must Fix Before Execution)

1. **Finding 3.1:** Move `intercore_sentinel_reset_all` to Task 1 so it's included in the initial copy.
2. **Finding 1.1:** Add version/sync comment to the copied lib-intercore.sh.
3. **Finding 4.1:** Add legacy fallback test to integration tests.
4. **Finding 11.1:** Verify `ic sentinel prune` exists or implement it.

### P2 Recommendations (Should Consider)

1. **Finding 1.2:** Document sentinel namespace isolation in the mapping table.
2. **Finding 2.4:** Consider removing redundant `type` checks (or document why they're kept).
3. **Finding 4.2:** Add smoke tests for hook execution (future work).
4. **Finding 12.1:** Rename `intercore_cleanup_stale` to `intercore_sentinel_cleanup_stale` for consistency.

### What's Good (No Changes Needed)

- Bash idioms: `set -euo pipefail` in hooks, no `set -e` in sourced libs ✓
- Error handling: `|| true`, `|| return 0` for fail-safe ✓
- Portability: `stat -c/-f` pattern for GNU/BSD ✓
- Naming: `intercore_*` prefix consistent with existing lib ✓
- Test approach: Simple pass/fail with trap cleanup ✓
- Fail-safe design: Transparent fallback to legacy on all failures ✓
- Self-correction: Task 2 and Task 7 revisions improve clarity ✓

---

## Conclusion

This is a well-structured plan with sound architecture and idiomatic bash. The main issues are:

1. **Task ordering** (Task 7 adds a function that should be in Task 1)
2. **Test coverage** (legacy fallback not tested)
3. **Documentation** (version sync comment, namespace isolation)

All are P1-P2 severity. No P0 blocking issues. Fix the P1 items before execution and the plan is solid.
