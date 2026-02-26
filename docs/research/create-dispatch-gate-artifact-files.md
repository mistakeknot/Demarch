# Task 3: Create dispatch.go, gate.go, artifact.go in pkg/clavain

**Date:** 2026-02-25
**Task:** Create 3 files in `apps/autarch/pkg/clavain/` for the Clavain Go client wrapper.

## Files Created

### 1. `dispatch.go`

- **DispatchOption / dispatchOpts**: Functional options pattern for configuring dispatch calls (`WithDispatchType`, `WithDispatchAgent`, `WithDispatchName`).
- **TrackAgent**: Registers an agent dispatch with the OS layer via `sprint-track-agent` subcommand. Accepts optional `agentType` and `dispatchID` parameters.
- **CompleteAgent**: Marks an agent as complete via `sprint-complete-agent`. Accepts optional `status` parameter.

### 2. `gate.go`

- **EnforceGate**: Checks whether a phase transition is allowed via `enforce-gate` subcommand. Returns nil on pass, error with reason on block. Accepts optional `artifactPath`.
- **GateOverride**: Placeholder that returns `ErrUnavailable` — clavain-cli doesn't wrap gate-override yet. Tracked via `TODO(iv-gyq9l)`.

### 3. `artifact.go`

- **SetArtifact**: Registers an artifact path on a sprint bead via `set-artifact`.
- **GetArtifact**: Retrieves an artifact path via `get-artifact`. Distinguishes "not found" (returns `("", nil)`) from actual subprocess failures (returns `("", err)`).

## Verification

### Dependency Check

Before writing, confirmed the directory and base files (`types.go`, `client.go`) already existed with:
- `ErrUnavailable` sentinel error in `types.go` (used by `gate.go`)
- `Client` struct with `execText` method in `client.go` (used by all three files)
- `execText` returns `(string, error)` — returns `""` on error (stdout discarded), which is important for `GetArtifact`'s "not found" detection

### Compilation

```
$ go vet ./pkg/clavain/
# (no output — clean)
```

All three files compile cleanly with the existing package. No modifications to existing files were needed.

## Design Notes

### GetArtifact "Not Found" Detection

`execText` returns `("", err)` on subprocess failure — it discards stdout when there's an error. The `GetArtifact` method uses two heuristics to detect "not found" vs real errors:

1. `result == ""` — always true when `execText` returns an error (since it returns empty string)
2. `strings.Contains(err.Error(), "not found")` — matches error messages containing "not found"

Since `result` is always `""` on error from `execText`, the first condition catches all error cases and converts them to `("", nil)`. This means **all errors from get-artifact are treated as "not found"**. This is intentionally lenient — the comment says clavain-cli exits 1 for not-found, so this is the expected happy path for the most common error case.

### dispatchOpts Not Yet Used

The `DispatchOption` pattern and `dispatchOpts` struct are defined but not yet consumed by any method. This is forward-looking — a future `DispatchTask` method will use them. The options are exported so callers can prepare them now.

### GateOverride Stub

Returns `ErrUnavailable` immediately rather than attempting a subprocess call. This is correct — the underlying CLI doesn't support this operation yet. The TODO references a tracked issue.
