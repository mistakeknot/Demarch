# MCP Tool Instrumentation Middleware

**Bead:** iv-wnurj
**Phase:** brainstorm (as of 2026-02-25T20:29:00Z)

## What We're Building

Shared middleware for mcp-go that wraps MCP tool handlers with centralized cross-cutting concerns: timing/metrics, error counting, structured error wrapping (ToolError), and retry logic for transient failures.

## Why This Approach

Each Demarch MCP server (interlock 12 tools, intermap 9, interserve 3, intermux 7) implements ad-hoc error handling. Interlock just adopted ToolError via manual `toToolError()` calls in every handler. This middleware centralizes that pattern.

## Key Discovery

mcp-go v0.43.2 already provides `ToolHandlerMiddleware`:
```go
type ToolHandlerMiddleware func(ToolHandlerFunc) ToolHandlerFunc
func WithToolHandlerMiddleware(middleware ToolHandlerMiddleware) ServerOption
```

No Demarch server uses it yet. This is the natural integration point.

## Key Decisions

- **Use mcp-go's native `WithToolHandlerMiddleware`** — not a custom wrapper around `RegisterAll`
- **Package location**: `sdk/interbase/go/mcputil/` — sits alongside toolerror
- **Scope for this sprint**: interlock migration only. Intermap/intermux/interserve are future work.
- **Metrics storage**: in-memory atomic counters (no external dependencies). Expose via a `Stats()` method.
- **No capability enforcement in v1** — YAGNI. Add when a consumer needs it.
- **No retry in v1** — transient errors are already tagged recoverable by ToolError. Agent-side retry is more appropriate than server-side retry for MCP tools (the agent chooses retry strategy).

## Open Questions

- Should metrics be per-server or global? (Recommend: per-server, passed as middleware config)
- Expose metrics via MCP resource or just programmatic API? (Recommend: programmatic first, resource later)
