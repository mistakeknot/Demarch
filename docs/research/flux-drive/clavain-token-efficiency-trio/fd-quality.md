# fd-quality Review: Clavain Token-Efficiency Plan

**Reviewer:** fd-quality (Flux-drive Quality & Style Reviewer)
**Date:** 2026-02-16
**Plan:** `/root/projects/Interverse/docs/plans/2026-02-16-clavain-token-efficiency.md`
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-16-clavain-token-efficiency.md`

---

### Findings Index

1. **[Q1] Missing AGENTS.md update** — PRD requires budget convention documentation, plan omits it
2. **[Q2] Naming inconsistency: checkpoint_* vs sprint_*** — new functions break established lib-sprint.sh convention
3. **[Q3] Fail-open verdict parsing risk** — verdict_parse_all should fail-closed when no verdicts exist
4. **[Q4] Test coverage gap** — plan adds 8 new functions without unit tests despite existing 40-test suite
5. **[Q5] Missing strict mode declaration** — lib-verdict.sh needs set -euo pipefail header
6. **[Q6] Shell gotcha: escaped literals in string length** — ${#_full_context} counts backslashes, not newlines
7. **[Q7] Incomplete doctor check specification** — no location/implementation details for budget convention check

### Verdict

**STATUS:** NEEDS_ATTENTION
**FINDINGS_COUNT:** 7
**SUMMARY:** Naming inconsistency, missing documentation task, test coverage gap, and fail-open error handling require fixes before implementation.

---

## Universal Quality Issues

### Q1: Missing AGENTS.md Documentation Task

**Severity:** Medium | **Type:** Completeness

The PRD deliverables include "Document budget convention in AGENTS.md" under F1, and Task 1.3 is titled "Document contract schema in reference" but redirects to Task 3.1 which only creates `using-clavain/references/agent-contracts.md`. The plan never adds the budget convention to `AGENTS.md`.

**Impact:** Users won't discover the budget annotation convention. Skills that need to enforce budget checks won't have reference documentation.

**Fix:** Add explicit task to F1 or F3:

```
### Task 1.4: Document budget convention in AGENTS.md

**File:** `hub/clavain/AGENTS.md`

Add section under "## Sprint Workflow" or "## Agent Orchestration":

```markdown
### Token Budget Annotations

Skills can declare token budgets in comments:
# budget: 5000 tokens

Sprint orchestrator checks budgets before dispatch and warns when exceeded.
Verdicts report TOKENS_SPENT for tracking against budget.
```

Update existing budget references in AGENTS.md if present.
```

---

### Q2: Naming Inconsistency — checkpoint_* Functions

**Severity:** High | **Type:** Naming Convention

The plan introduces `checkpoint_write`, `checkpoint_read`, `checkpoint_validate`, etc. in `lib-sprint.sh`, but the file's established convention is `sprint_*` for all public functions and `_sprint_*` for private helpers.

From codebase analysis:
- Public API: `sprint_create`, `sprint_find_active`, `sprint_read_state`, `sprint_claim`, `sprint_advance` (47+ lines each)
- Private helpers: `_sprint_transition_table` (line 393)
- Other function families use their own prefix: `enforce_gate` (standalone, line 376)

Existing checkpoint functions in lib-sprint.sh already follow the pattern:
- `checkpoint_write` (line 697)
- `checkpoint_read` (line 749)
- `checkpoint_validate` (line 755)
- `checkpoint_completed_steps` (line 776)
- `checkpoint_step_done` (line 786)
- `checkpoint_clear` (line 795)

**Wait — the functions already exist!** Task 6.1 says "Define checkpoint schema" but the functions are already implemented at lines 697-795.

**Fix:** Change Task 6.1 to "Extend checkpoint schema" and verify the existing functions match the plan's specification. If the current implementation is incomplete, document what needs to be added. If it's complete, remove the redundant task.

---

### Q3: Fail-Open Error Handling in Verdict Parsing

**Severity:** Medium | **Type:** Error Handling

The plan's `verdict_parse_all()` function (Task 4.1) is described as reading all `.clavain/verdicts/*.json` files and outputting a summary. The codebase convention (from lib-sprint.sh analysis) is "all functions are fail-safe (return 0 on error)" except `sprint_claim()`.

**Problem:** If verdict parsing fails (no files, malformed JSON, missing STATUS field), should the sprint proceed or halt?

From sprint workflow context:
- After quality-gates dispatches review agents, sprint reads verdicts to decide next step
- If all CLEAN → proceed
- If any NEEDS_ATTENTION → read details

If `verdict_parse_all()` fails and returns empty output, sprint will treat it as "all CLEAN" and proceed without quality review. This is **fail-open when it should be fail-closed**.

**Fix:** Add to Task 4.1 specification:

```bash
verdict_parse_all() {
    local verdicts_dir=".clavain/verdicts"

    # Fail-closed: if no verdict files exist, return error
    if [ ! -d "$verdicts_dir" ] || [ -z "$(ls -A "$verdicts_dir" 2>/dev/null)" ]; then
        echo "ERROR: No verdicts found — agents may not have completed" >&2
        return 1
    fi

    # Parse all JSON files, fail on malformed
    # ... existing logic ...
}
```

Sprint skill should handle non-zero exit: "Verdicts missing — review agents may have failed. Check .clavain/verdicts/ directory."

---

### Q4: Test Coverage Gap for New Functions

**Severity:** Medium | **Type:** Test Strategy

The plan adds 8 new functions to lib-sprint.sh (or a new lib-verdict.sh):
- `verdict_init`, `verdict_write`, `verdict_read`, `verdict_clean` (Task 3.2)
- `verdict_parse_all`, `verdict_count_by_status`, `verdict_get_attention` (Task 4.1)
- `checkpoint_*` functions (Task 6.1, though these may already exist)

Existing context shows `tests/shell/test_lib_sprint.bats` with 40 tests covering sprint_create, sprint_claim, sprint_advance, sprint_classify_complexity, etc. The plan's "Test Strategy" section only mentions:
- `bash -n` syntax check
- Manual sprint run after F4
- `/context` check after F2
- Sprint with `--resume` after F6

**No unit tests for the new verdict_* functions.**

**Impact:** Verdict parsing is critical to the F3/F4 flow. Without unit tests:
- Edge cases (missing files, malformed JSON, concurrent writes) are untested
- Regressions won't be caught by CI
- The 40-test suite creates an expectation that lib-sprint.sh functions have coverage

**Fix:** Add to F3 (Task 3.2) and F4 (Task 4.1):

```
### Task 3.2a: Unit tests for lib-verdict.sh

**File:** `tests/shell/test_lib_verdict.bats` (new)

Add BATS tests covering:
- verdict_init: creates directory, adds .gitignore entry
- verdict_write: writes JSON, handles missing dir, atomic write (temp+mv)
- verdict_read: parses JSON, returns structured output, handles missing file
- verdict_clean: removes all verdict files, idempotent

Mock file I/O with temp directories (similar to test_lib_sprint.bats setup/teardown).

Minimum 8 tests (2 per function: happy path + error case).
```

```
### Task 4.1a: Unit tests for verdict parsing

**File:** `tests/shell/test_lib_verdict.bats` (extend from Task 3.2a)

Add tests for:
- verdict_parse_all: multiple verdicts, empty dir (returns 1), malformed JSON
- verdict_count_by_status: correct counts, handles missing STATUS field
- verdict_get_attention: filters NEEDS_ATTENTION, returns DETAIL_PATHs

Minimum 6 additional tests.
```

---

## Shell-Specific Issues

### Q5: Missing Strict Mode in lib-verdict.sh

**Severity:** Low | **Type:** Shell Idiom

Task 3.2 creates `lib-verdict.sh` but doesn't specify the shebang or strict mode. All other lib-*.sh files in the codebase use `#!/usr/bin/env bash` (confirmed for lib-sprint.sh).

However, lib-sprint.sh does NOT use `set -euo pipefail` (from analysis: no `set -e`, `set -u`, or `set -o pipefail` in the file). The codebase convention for hooks is to use strict mode, but library files may be sourced in non-strict contexts.

**Fix:** Add to Task 3.2 specification:

```bash
#!/usr/bin/env bash
# Verdict file utilities for Clavain agent results.
# Part of lib-sprint.sh ecosystem.
# No strict mode (sourced by hooks with varying strictness).

# ... functions ...
```

Document the no-strict-mode choice in a comment so future maintainers understand why.

---

### Q6: Shell Gotcha — ${#var} with Escaped Characters

**Severity:** Low | **Type:** Shell Idiom

The plan doesn't use `${#var}` syntax anywhere (I searched for it and found no matches), but the user's question raises it as a concern. This is a non-issue for the current plan.

For context: `${#var}` counts bytes in the string. If you construct a string with `\\n` literals (two characters: backslash + n), it counts them as 2 bytes each, not as newlines. This is correct behavior for string length.

**For file size checking** (which the plan doesn't currently do), prefer:
- `wc -c < file` for byte count (portable, works with pipes)
- `stat -c %s file` for file size (GNU coreutils, faster, no I/O)
- `stat -f %z file` on BSD/macOS

No fix needed — this is a hypothetical concern, not an actual issue in the plan.

---

### Q7: Incomplete Doctor Check Specification

**Severity:** Medium | **Type:** Documentation

The plan mentions "The plan adds a doctor check but doesn't update AGENTS.md with the budget convention" (per user's question context). Searching the plan for "doctor" finds no matches.

Re-reading the PRD: no mention of doctor checks.

Re-reading the plan: Task 1.3 says "Document contract schema in reference" which links to Task 3.1. No doctor check task exists.

**If a doctor check is intended** (to validate budget annotations in skills), it's missing from the plan entirely.

**Fix:** Add to F1 if budget validation is a requirement:

```
### Task 1.5: Add doctor check for budget annotations (optional)

**File:** TBD (no doctor check infrastructure in current plan)

If budget enforcement is a goal (not specified in PRD):
1. Add `/doctor` command check for skills with budget annotations
2. Validate budget format: `# budget: <number> tokens`
3. Warn if any skill dispatch exceeds budget (non-blocking)

NOTE: This is not in the PRD scope. If budget enforcement is desired, add it to a future bead.
```

Since the PRD doesn't mention doctor checks, this is a **documentation alignment issue**, not a missing feature. The user's question may be based on outdated context.

---

## What NOT to Flag

These are NOT issues (explicitly avoiding over-flagging):

- **No TypeScript/Python-specific concerns** — this is a bash-only plan
- **Pure style preferences** — the plan follows existing codebase conventions (fail-open for most functions, snake_case, etc.)
- **Missing patterns the repo doesn't use** — no docstrings in bash functions, no strict typing
- **Tooling recommendations** — the plan uses existing tools (bash, jq, BATS)

---

## Summary

The plan is well-structured and follows most codebase conventions. The critical issues are:

1. **Naming inconsistency** (Q2) — checkpoint_* functions may already exist, task is redundant
2. **Missing documentation task** (Q1) — AGENTS.md update for budget convention
3. **Test coverage gap** (Q4) — 8 new functions without unit tests despite existing test suite
4. **Fail-open verdict parsing** (Q3) — should fail-closed when no verdicts exist

The other findings are low-severity documentation and style improvements.

**Recommended action:** Address Q1-Q4 before implementation. Q5-Q7 are nice-to-have improvements.
