# Adopt mcp_agent_mail Patterns — Sprint Plan

**Bead:** iv-bg0a0
**Phase:** executing (as of 2026-02-25T07:21:25Z)
**Brainstorm:** docs/brainstorms/2026-02-24-adopt-mcp-agent-mail-patterns-brainstorm.md

## Sprint Scope

This sprint closes the epic by implementing the ToolError contract (iv-gkory) — the foundational P0 that unblocks the middleware bead (iv-wnurj). Decision beads (iv-osph4, iv-upzm9, iv-x46ly) and circuit breaker (iv-q62fr) are already resolved. Remaining implementation beads (iv-wnurj, iv-t4pia, etc.) are unblocked when the epic closes and can proceed independently.

## Task 1: Create Go module in interbase SDK
- [x] Create `sdk/interbase/go/go.mod` with module `github.com/mistakeknot/interbase`
- [x] Require `github.com/mark3labs/mcp-go v0.43.2` (matching interlock/intermute)
- [x] Create `sdk/interbase/go/toolerror/` package directory

## Task 2: Implement ToolError struct and error type catalog
- [x] Create `sdk/interbase/go/toolerror/toolerror.go` with:
  - `ToolError` struct: `Type string`, `Message string`, `Recoverable bool`, `Data map[string]any`
  - `Error()` method (implements `error` interface)
  - Constructor: `New(errType, message string, args ...any) *ToolError`
  - Chaining: `WithRecoverable(bool)`, `WithData(map[string]any)`
- [x] Error type constants:
  - `ErrNotFound` — resource doesn't exist
  - `ErrConflict` — concurrent modification conflict
  - `ErrValidation` — invalid input/arguments
  - `ErrPermission` — access denied
  - `ErrTransient` — temporary failure, safe to retry
  - `ErrInternal` — unexpected server error
- [x] `JSON()` — serializes error as JSON string for MCP tool results
- [x] `FromError(err error) *ToolError` — unwraps a ToolError from a standard error
- [x] `Wrap(err error) *ToolError` — converts any error to ToolError (passthrough or ErrInternal)

## Task 3: Add tests for ToolError
- [x] Create `sdk/interbase/go/toolerror/toolerror_test.go`
- [x] Test: New() creates correct struct
- [x] Test: Error() returns formatted message
- [x] Test: JSON() produces valid JSON
- [x] Test: FromError() unwraps correctly, returns nil for non-ToolError
- [x] Test: Recoverable flag defaults (Transient=true, others=false)
- [x] All 9 tests pass

## Task 4: Adopt ToolError in interlock MCP handlers
- [x] Add `replace github.com/mistakeknot/interbase => ../../sdk/interbase/go` to interlock go.mod
- [x] Update interlock MCP tool handlers to return ToolError instead of flat `fmt.Errorf`
- [x] Focus on the highest-traffic tools: `reserve_files`, `release_files`, `check_conflicts`
- [x] Run `go test ./...` in interlock

## Task 5: Update documentation
- [x] Update `sdk/interbase/CLAUDE.md` to document the Go SDK packages
- [x] Update `sdk/interbase/AGENTS.md` if it exists

## Task 6: Close epic and commit
- [ ] Run all tests
- [ ] Commit in interbase, interlock
- [ ] Commit docs in Demarch root
- [ ] Close iv-gkory (ToolError implemented)
- [ ] Close iv-bg0a0 (epic — unblocks remaining children)
- [ ] bd sync + push
