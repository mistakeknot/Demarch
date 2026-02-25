# MCP Tool Instrumentation Middleware — Sprint Plan

**Bead:** iv-wnurj
**Phase:** executing (as of 2026-02-25T20:30:33Z)
**Brainstorm:** docs/brainstorms/2026-02-25-mcp-instrumentation-middleware-brainstorm.md

## Sprint Scope

Create `mcputil` package in `sdk/interbase/go/` providing a `ToolHandlerMiddleware` that wraps mcp-go handlers with: timing metrics, error counting, automatic ToolError wrapping for unhandled errors, and panic recovery. Migrate interlock to use it.

Deferred: capability enforcement, retry logic, intermap/intermux/interserve migration (future beads).

## Task 1: Create mcputil package

- [x] Create `sdk/interbase/go/mcputil/` directory
- [x] Add `mcp-go v0.43.2` dependency to `sdk/interbase/go/go.mod`
- [x] Create `sdk/interbase/go/mcputil/instrument.go` with:
  - `Metrics` struct: per-tool atomic counters (call count, error count, total duration)
  - `ToolMetrics()` method returning snapshot of all tool metrics
  - `InstrumentTools() server.ToolHandlerMiddleware` factory function

## Task 2: Implement InstrumentTools middleware

The middleware wraps each handler call with:
- [x] **Timing**: record `time.Since(start)` per call, accumulate in atomic int64 (nanoseconds)
- [x] **Error wrapping**: if handler returns `(nil, error)`, convert to `(ToolError.JSON(), nil)` via `toolerror.Wrap`
- [x] **Error counting**: increment per-tool error counter on any error (both Go error and `isError` result)
- [x] **Panic recovery**: `defer recover()` → return `toolerror.New(ErrInternal, "panic: %v")` (like mcp-go's `WithRecovery` but with structured error)
- [x] **Tool name from `request.Params.Name`** — used as map key for per-tool metrics

Key types:
```go
type ToolStats struct {
    Calls    int64         `json:"calls"`
    Errors   int64         `json:"errors"`
    Duration time.Duration `json:"total_duration"`
}

type Metrics struct {
    mu    sync.RWMutex
    tools map[string]*toolCounters
}
```

## Task 3: Add tests for mcputil

- [x] Create `sdk/interbase/go/mcputil/instrument_test.go`
- [x] Test: middleware wraps successful handler (timing recorded, no error)
- [x] Test: Go error return → converted to ToolError JSON result
- [x] Test: panic in handler → recovered, returns ErrInternal
- [x] Test: per-tool metrics tracked independently
- [x] Test: `ToolMetrics()` returns correct snapshot
- [x] Test: concurrent calls are safe (run with `-race`)

## Task 4: Adopt middleware in interlock

- [x] Update `interverse/interlock/cmd/interlock-mcp/main.go`:
  - Create `mcputil.NewMetrics()`
  - Pass `server.WithToolHandlerMiddleware(metrics.Instrument())` to `server.NewMCPServer`
- [x] Keep `toToolError()` for domain-specific mapping (ConflictError→ErrConflict, HTTP codes→types). Middleware provides safety net for panics, timing, and unhandled errors.
- [x] Replace explicit `toolerror.New(...)` validation calls with `mcputil.ValidationError(...)` helpers
- [x] Run `go test ./...` in interlock

## Task 5: Update documentation

- [x] Update `sdk/interbase/CLAUDE.md` — add mcputil to Go SDK section
- [x] Update `sdk/interbase/AGENTS.md` — add mcputil reference
- [x] Update `sdk/interbase/go/README.md` — add mcputil package docs
- [x] Update `docs/sdk-toolerror.md` — add middleware adoption note

## Task 6: Test, commit, close

- [ ] Run `go test ./...` in interbase
- [ ] Run `go test ./...` in interlock
- [ ] Commit in interbase, interlock
- [ ] Commit docs in Demarch root
- [ ] Close iv-wnurj
- [ ] Push
