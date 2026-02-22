---
module: scripts
date: 2026-02-22
problem_type: shell_pattern
component: validate-plugin.sh
symptoms:
  - "Script exits silently after first iteration in batch loop"
  - "ERR trap does not fire"
  - "Only first plugin processed in --all mode"
  - "bash -x trace stops mid-function with no error"
root_cause: arithmetic_exit_code_under_set_e
resolution_type: pattern
severity: medium
tags: [bash, set-e, arithmetic, batch-loop, error-accumulation, shell]
---

# `set -e` with Bash Arithmetic and Error-Accumulating Functions

## Problem

A validator script processes plugins in a loop, accumulating error/warning counts. Under `set -euo pipefail`, the script silently exits after the first plugin — no error message, no ERR trap fired, trace just stops.

## Root Cause 1: `((...))` Returns Exit Code 1 When Result Is 0

```bash
set -euo pipefail
ERRORS=0
((ERRORS++))  # ERRORS becomes 1 — works
# Later, in the loop:
ERRORS=0
((total_errors += ERRORS))  # 0 += 0 = 0 → exit code 1 → script dies
```

Bash `((...))` returns exit code 0 when the expression evaluates to non-zero, and exit code 1 when it evaluates to zero. Under `set -e`, a zero-valued arithmetic expression kills the script.

This also affects `((count++))` when `count` starts at 0 — the *pre-increment* value (0) determines the exit code.

### Fix

Use assignment form instead of `((...))`:

```bash
# Wrong — dies when result is 0
((ERRORS++))
((total_errors += ERRORS))

# Right — assignment always returns exit code 0
ERRORS=$((ERRORS + 1))
total_errors=$((total_errors + ERRORS))
```

## Root Cause 2: `&&` Short-Circuit as Last Statement

```bash
set -euo pipefail
for plugin in plugins/*/; do
    # ...
    [ "$ERRORS" -gt 0 ] && failed_count=$((failed_count + 1))
    # When ERRORS=0: [ ] is false → && not taken → whole line returns 1 → script dies
done
```

Under `set -e`, a `&&` chain that short-circuits false at the end of a block kills the script.

### Fix

Use `if` instead of `&&` for conditional increments:

```bash
if [ "$ERRORS" -gt 0 ]; then failed_count=$((failed_count + 1)); fi
```

## Root Cause 3: Error-Accumulating Functions Exit Non-Zero

A function like `validate_plugin()` is designed to accumulate errors in a counter, not fail-fast. But internal commands (process substitutions, `find` with `-o`, `grep -q` with no match) can return non-zero, and `set -e` propagates this as the function's exit code.

The ERR trap doesn't fire because the failure occurs in a context where ERR traps are suppressed (inside `&&`, `||`, `if`, or process substitution).

### Fix

Call accumulator functions with `|| true`:

```bash
# In batch mode — function tracks errors via counter, not exit code
validate_plugin "$dir" || true
# Check ERRORS counter afterward, not $?
```

## Investigation Steps That Worked

1. **Redirect stdout/stderr separately** — the error wasn't in either stream
2. **`bash -x` trace** — showed exact stop point but not why
3. **ERR trap didn't fire** — narrowed to `set -e` in suppressed context
4. **`|| true` on function call** — confirmed function was the exit source
5. **Counting trace lines** (`wc -l`) — verified the script wasn't hanging, it was dying

## Key Lesson

When writing `set -e` scripts with batch loops and error counters:
1. Never use `((...))` for arithmetic — always use `VAR=$((expr))` form
2. Never use `&&` as the last statement in a loop/block — use `if/then/fi`
3. Always call error-accumulating functions with `|| true` and check counters afterward

## Cross-References

- `scripts/validate-plugin.sh` — the script where this was discovered
- `docs/solutions/patterns/set-e-with-fallback-paths-20260216.md` — complementary: covers `set -e` with command failure fallbacks
- `docs/guides/shell-and-tooling-patterns.md` — general shell patterns guide
