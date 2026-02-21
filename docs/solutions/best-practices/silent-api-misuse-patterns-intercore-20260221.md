---
module: Intercore
date: 2026-02-21
problem_type: best_practice
component: cli
symptoms:
  - "fmt.Sscanf silently accepts invalid input (--days=0, --days=abc) with no error"
  - "err == sql.ErrNoRows fails when error is wrapped by middleware"
  - "rows.Err() not checked after scan loop allows partial reads on context cancellation"
  - "byte-indexed truncate corrupts multi-byte UTF-8 lane names"
root_cause: missing_validation
resolution_type: code_fix
severity: medium
tags: [go, silent-failure, error-handling, utf8, sql, quality-gates, multi-agent-review]
---

# Best Practice: Silent API Misuse Patterns in Go

## Problem

During the thematic work lanes sprint (iv-jj97), a 10-task feature implementation across 4 repos (intercore, autarch, clavain, interphase) passed all unit and integration tests but was flagged by multi-agent quality gates with 26 findings. Two HIGH-severity issues and several MEDIUM issues all share a common theme: Go APIs that silently accept invalid usage without returning errors.

## Environment
- Module: Intercore + Autarch
- Framework Version: Go 1.22 / Go 1.24
- Affected Component: CLI, store, TUI
- Date: 2026-02-21

## Symptoms
- `--days=abc` silently accepted — `fmt.Sscanf` returns (0, error) but neither was checked
- `err == sql.ErrNoRows` compiled and passed tests — but fails when errors are wrapped
- `rows.Next()` returning false on context cancellation left partial data in map, used as if complete
- `s[:max-1]` split multi-byte UTF-8 characters, producing invalid strings in TUI

## What Didn't Work

**Direct solution:** All four patterns were caught by quality gate review agents, not by tests. The code compiled, tests passed, and integration tests passed — the silent failures only manifest under specific conditions (wrapped errors, cancelled contexts, non-ASCII input, invalid CLI args).

## Solution

### Pattern 1: `fmt.Sscanf` — always check return count

```go
// Before (broken):
fmt.Sscanf(val, "%d", &days)  // silently fails on "abc", "0", "-1"

// After (fixed):
n, err := fmt.Sscanf(val, "%d", &days)
if err != nil || n != 1 {
    return fmt.Errorf("invalid --days value: %s", val)
}
if days < 1 {
    return fmt.Errorf("--days must be >= 1, got %d", days)
}
```

### Pattern 2: `errors.Is` — never use `==` for sentinel errors

```go
// Before (broken):
if err == sql.ErrNoRows {  // fails when err is wrapped

// After (fixed):
if errors.Is(err, sql.ErrNoRows) {  // traverses error chain
```

### Pattern 3: `rows.Err()` — always check after scan loop

```go
// Before (broken):
for rows.Next() {
    rows.Scan(&val)
    existing[val] = true
}
rows.Close()
// proceeds with partial data if context was cancelled mid-scan

// After (fixed):
for rows.Next() { ... }
rows.Close()
if err := rows.Err(); err != nil {
    return fmt.Errorf("scan interrupted: %w", err)
}
// now safe to use existing map
```

### Pattern 4: Rune-safe truncation

```go
// Before (broken):
func truncate(s string, max int) string {
    if len(s) <= max { return s }
    return s[:max-1] + "…"  // splits multi-byte runes
}

// After (fixed):
func truncate(s string, max int) string {
    if utf8.RuneCountInString(s) <= max { return s }
    runes := []rune(s)
    return string(runes[:max-1]) + "…"
}
```

## Why This Works

All four patterns share a root cause: **Go APIs that accept invalid usage without panicking or returning errors**. The language design philosophy of explicit error handling means silent acceptance is intentional — the caller is expected to check. But in practice, especially during rapid feature development, these checks are easy to skip because the code compiles and tests pass with valid inputs.

Multi-agent quality review catches these because each agent brings a different lens:
- **fd-quality** found Q1 (errors.Is) and Q2 (Sscanf) via Go idiom checking
- **fd-correctness** found C-03 (rows.Err) via database/sql contract analysis
- **fd-quality** found Q5 (truncate) via UTF-8 safety analysis
- 3/3 agents converged on the dual membership divergence risk (A2)

## Prevention

- **`fmt.Sscanf`**: Always check both return values `(n, err)`. Use `strconv.Atoi` for simple integer parsing — it's more explicit.
- **Sentinel errors**: Search-and-replace `== sql.ErrNoRows` with `errors.Is(err, sql.ErrNoRows)` project-wide. Consider a linter rule.
- **`rows.Err()`**: After every `for rows.Next()` loop, check `rows.Err()` before using collected data.
- **String truncation**: Always use `utf8.RuneCountInString` and `[]rune` for display truncation. Add to code review checklist.
- **Multi-agent review**: Run quality gates on every feature landing. Three agents with different perspectives catch patterns that tests miss.

## Related Issues

- See also: [intercore-schema-upgrade-deployment-20260218.md](../patterns/intercore-schema-upgrade-deployment-20260218.md) — schema migration patterns
- See also: [toctou-gate-check-cas-dispatch-intercore-20260221.md](../database-issues/toctou-gate-check-cas-dispatch-intercore-20260221.md) — intercore correctness patterns
