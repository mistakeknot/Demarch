---
module: Clavain
date: 2026-02-16
problem_type: runtime_error
component: cli
symptoms:
  - "jq exits with code 5 (runtime error) when piped output from shell function is empty string"
  - "Script aborts under set -e when jq tries to slice null: Cannot index null with number"
  - "Downstream checkpoint_completed_steps returns nothing instead of [] when no checkpoint exists"
root_cause: missing_validation
resolution_type: code_fix
severity: high
tags: [jq, null-safety, shell, bash, checkpoint, json, empty-string, runtime-error]
---

# Troubleshooting: jq Null-Slice Runtime Error from Empty-String Function Returns

## Problem

Shell functions that wrap JSON file access return `""` (empty string) when the file doesn't exist. Downstream callers pipe this to `jq`, which parses `""` as `null`. Any subsequent array or object operations on `null` (like `null[:5]` or `null | length`) cause a jq runtime error (exit code 5), which aborts the script under `set -euo pipefail`.

## Environment
- Module: Clavain (hooks/lib-sprint.sh)
- Affected Component: Session checkpointing (checkpoint_read, checkpoint_completed_steps, checkpoint_step_done)
- Date: 2026-02-16

## Symptoms
- `jq` exits with code 5: `Cannot index null with number`
- The `//` (alternative operator) does NOT fire because the input is `null` at the point of the slice — `null[:5]` errors before `//` can evaluate
- Sprint resume fails silently when no checkpoint file exists
- `checkpoint_completed_steps` returns nothing (empty output) instead of `[]`

## What Didn't Work

**Attempted Solution 1:** Using jq's `//` alternative operator to provide defaults
- **Why it failed:** `null[:10]` is a runtime error (exit code 5), NOT a null value. The `//` alternative operator never fires because jq aborts before evaluating it. This is a well-known jq gotcha.

**Attempted Solution 2:** Adding `2>/dev/null` to suppress jq errors
- **Why it failed:** Suppresses the error message but still produces no output and returns non-zero exit code, causing `set -e` to abort the script.

## Solution

**Two-layer fix:**

1. **Return valid JSON, never empty string** — change the wrapper function to return `{}` (empty JSON object):

```bash
# Before (broken):
checkpoint_read() {
    [[ -f "$CHECKPOINT_FILE" ]] && cat "$CHECKPOINT_FILE" 2>/dev/null || echo ""
}

# After (fixed):
checkpoint_read() {
    [[ -f "$CHECKPOINT_FILE" ]] && cat "$CHECKPOINT_FILE" 2>/dev/null || echo "{}"
}
```

2. **Guard array access with `// []`** at the point of use, BEFORE slicing:

```bash
# Before (broken — null[:5] crashes):
echo "$checkpoint" | jq '.completed_steps[:5]'

# After (fixed — converts null to [] before slicing):
echo "$checkpoint" | jq '(.completed_steps // [])[:5]'
```

3. **Update emptiness checks** in callers to match the new return value:

```bash
# Before (broken — never matches when return is "{}"):
[[ -z "$checkpoint" ]] && return 0

# After (fixed):
[[ "$checkpoint" == "{}" ]] && return 0
```

## Why This Works

1. **Root cause:** jq treats empty string input as `null`. Unlike most jq operations that propagate `null` silently, array/object indexing operations (`null[0]`, `null[:5]`, `null.field`) are runtime errors. The `//` alternative operator evaluates AFTER the expression, so `null[:5] // []` never reaches the `// []` because `null[:5]` already crashed.

2. **Why `{}` works:** An empty JSON object `{}` is valid input. `.completed_steps` on `{}` returns `null`, but `(.completed_steps // [])` converts that to `[]`, and `[][:5]` returns `[]` — no error.

3. **Why the `//` must wrap the FIELD access, not the slice:** The fix is `(.completed_steps // [])[:5]`, NOT `.completed_steps[:5] // []`. Parentheses force jq to evaluate the alternative before the slice.

## Prevention

- **Rule:** Shell functions that read JSON files must return `{}` (empty object) or `[]` (empty array) as their fallback, NEVER `""` (empty string).
- **Rule:** All jq field access that feeds into array operations must use `(.field // [])` to guard against missing fields.
- **Detection:** Search for `|| echo ""` in functions that return JSON — each one is a potential null-slice bug.
- **Testing:** Test every JSON-returning function with the file missing to verify it returns valid JSON.

```bash
# Detection command — find all potential instances:
grep -rn '|| echo ""' hooks/lib-*.sh | grep -v '#'
```

## Related Issues

- See also: [guard-fallthrough-null-validation-20260216.md](../patterns/guard-fallthrough-null-validation-20260216.md) — similar "silent skip on null" pattern in TypeScript
- See also: [set-e-with-fallback-paths-20260216.md](../patterns/set-e-with-fallback-paths-20260216.md) — related `set -e` interaction patterns
- Cross-reference: MEMORY.md jq gotcha section documents the same `null[:10]` behavior
