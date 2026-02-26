# Task 1: Create pkg/clavain Client Types

**Date:** 2026-02-25
**Status:** Complete

## Summary

Created the `pkg/clavain` package in `apps/autarch/` with 3 files providing a Go client wrapper for the `clavain-cli` binary. This mirrors the existing `pkg/intercore` pattern for the `ic` binary, establishing the OS-layer client that Autarch will use for policy-governing write operations.

## Files Created

### 1. `apps/autarch/pkg/clavain/types.go`

Defines the package-level error sentinel and four result types:

- **`ErrUnavailable`** — sentinel error returned when `clavain-cli` is not found on PATH
- **`SprintCreateResult`** — bead_id + run_id from sprint creation
- **`AdvanceResult`** — phase transition result (advanced bool, from/to phase, reason)
- **`GateResult`** — gate enforcement result (passed bool, reason)
- **`DispatchResult`** — task dispatch result (dispatch_id + run_id)

All types use JSON struct tags matching the expected clavain-cli JSON output format.

### 2. `apps/autarch/pkg/clavain/client.go`

Implements the `Client` struct with functional options pattern:

- **`New(opts ...Option)`** — constructor that discovers `clavain-cli` via `exec.LookPath`, returns `ErrUnavailable` if not found
- **`Available()`** — convenience function for quick availability checks
- **`WithBinPath(path)`** — option to force a specific binary path (skips PATH lookup)
- **`WithTimeout(d)`** — option to override the default 15-second subprocess timeout
- **`execRaw`** — low-level subprocess execution, captures stdout/stderr, applies context timeout
- **`execText`** — returns trimmed stdout as string
- **`execJSON`** — unmarshals JSON stdout into a destination struct

Key design decisions:
- Context-aware: all exec methods accept `context.Context`, apply timeout only if no deadline already set
- Error messages include the full clavain-cli command and stderr output for debuggability
- Matches the `pkg/intercore` pattern already established in the codebase

### 3. `apps/autarch/pkg/clavain/client_test.go`

Four tests covering:
- `TestNew_BinaryNotFound` — verifies `ErrUnavailable` when PATH is empty
- `TestAvailable_NoError` — smoke test that `Available()` doesn't panic
- `TestWithBinPath` — verifies the option correctly sets `binPath`
- `TestWithTimeout` — verifies the option correctly sets `timeout`

## Test Results

```
=== RUN   TestNew_BinaryNotFound
--- PASS: TestNew_BinaryNotFound (0.00s)
=== RUN   TestAvailable_NoError
--- PASS: TestAvailable_NoError (0.00s)
=== RUN   TestWithBinPath
--- PASS: TestWithBinPath (0.00s)
=== RUN   TestWithTimeout
--- PASS: TestWithTimeout (0.00s)
PASS
ok  	github.com/mistakeknot/autarch/pkg/clavain	0.002s
```

All 4 tests pass. Package compiles cleanly with no warnings.

## Architecture Notes

- The `execText` and `execJSON` helper methods are unexported — they exist as building blocks for the public methods that will be added in subsequent tasks (sprint creation, dispatch, advance, gate enforcement)
- The `execRaw` method returns both stdout bytes and error on failure, allowing callers to inspect partial output if needed
- The timeout strategy (apply only when context has no existing deadline) prevents double-timeout scenarios when callers already set their own deadlines
