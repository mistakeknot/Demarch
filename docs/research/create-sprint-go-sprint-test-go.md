# Task 2: Create sprint.go and sprint_test.go

## Summary

Created two files in `apps/autarch/pkg/clavain/`:
- `sprint.go` — Sprint lifecycle methods for the Clavain client
- `sprint_test.go` — Unit tests for sprint option types and cancel stub

## Files Created

### sprint.go

Adds five methods to `*Client` plus the `SprintOption` functional options pattern:

| Method | Purpose | Returns |
|--------|---------|---------|
| `SprintCreate` | Creates a sprint via `clavain-cli sprint-create` | bead ID string |
| `SprintAdvance` | Advances sprint to next phase | pause reason (empty = success) |
| `SprintCancel` | Stub — returns error directing caller to `ic.RunCancel()` | error always |
| `SprintReadState` | Reads full sprint state JSON | raw text |
| `resolveRunID` | Parses sprint state JSON to extract ic run ID | run ID string |

Functional options:
- `WithSprintComplexity(n int)` — sets complexity 1-5
- `WithSprintLane(lane string)` — sets thematic lane label (auto-fills default complexity=3 if not set)

### sprint_test.go

Three tests:
1. `TestSprintCreate_MissingBinary` — verifies `New()` fails when clavain-cli not on PATH
2. `TestSprintCreateOptions` — unit test for functional option application on `sprintOpts`
3. `TestSprintCancel_ReturnsError` — verifies the unimplemented stub returns an error

## Compatibility Verification

- **Package**: `clavain` — matches `types.go` and `client.go`
- **Dependencies**: Uses `execText` and `execRaw` methods from `client.go` — both exist and have matching signatures
- **Types**: `SprintOption` / `sprintOpts` are new types; no conflicts with existing `Option` type (client-level)
- **Tests**: Pattern matches `client_test.go` (same use of `t.Setenv`, `WithBinPath`, etc.)

## Build & Test Results

```
$ go vet ./pkg/clavain/
(clean — no output)

$ go test -race ./pkg/clavain/
ok  	github.com/mistakeknot/autarch/pkg/clavain	1.011s
```

All tests pass with the race detector enabled.

## Observations

### Potential Bug: SprintAdvance stdout-on-error

`SprintAdvance` has logic to capture stdout (pause reason) when the subprocess exits non-zero:

```go
result, err := c.execText(ctx, args...)
if err != nil {
    if result != "" {
        return result, nil
    }
    ...
}
```

However, `execText` in `client.go` (line 87-89) returns `("", err)` on error — it discards stdout when `execRaw` returns an error. This means `result` will always be empty when `err != nil`, so the pause-reason-on-exit-1 path is dead code.

To fix this in a future iteration, `SprintAdvance` should call `execRaw` directly and handle the stdout bytes itself, similar to how `resolveRunID` already does. This was not changed since the task specifies exact file contents.

### Design Notes

- `SprintCancel` is an explicit stub that returns an error with guidance — this is intentional since cancel semantics bypass Clavain policy and should go through `ic` directly.
- `resolveRunID` is unexported (lowercase `r`) — it's a package-internal helper, not part of the public API. Callers needing run IDs should use `SprintReadState` and parse the result themselves.
- The lane positional arg handling (auto-inserting default complexity=3) mirrors the bash `sprint-create` interface where lane is the 3rd positional argument after goal and complexity.
