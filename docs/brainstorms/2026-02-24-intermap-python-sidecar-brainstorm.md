# Intermap Python Sidecar

**Bead:** iv-3wmf2
**Phase:** brainstorm (as of 2026-02-25T06:32:50Z)

## What We're Building

A persistent Python sidecar process for intermap's Go MCP server. Instead of spawning a fresh `python3 -m intermap` subprocess per tool call (current behavior), the Go bridge spawns one long-lived Python process at startup and communicates via stdin/stdout JSON-RPC.

**Problem:** Each MCP tool call spawns a fresh Python subprocess. Python's FileCache dies with each call — no warm in-memory cache. For analysis-heavy workflows (architecture mapping, impact analysis across 9 tools), this means repeated cold starts (~200ms Python startup + import overhead per call).

**Goal:** Warm Python process with persistent in-memory cache. First call pays startup cost, subsequent calls skip Python startup entirely.

## Why This Approach

**Stdin/stdout JSON-RPC** chosen over Unix sockets and HTTP because:

1. **Zero dependencies** — no socket libraries, no HTTP framework. Just `json.loads(stdin)` / `json.dumps(stdout)`
2. **Same pattern as MCP stdio transport** — well-understood in this ecosystem
3. **Works everywhere** — containers, sandboxes, no port conflicts
4. **Simple crash recovery** — Go detects EOF on stdout, respawns the sidecar

Serial request processing (one at a time) is acceptable because MCP tool calls from Claude Code are inherently sequential — the agent waits for each tool result before deciding the next call.

## Key Decisions

- **IPC mechanism:** Stdin/stdout JSON-RPC (not Unix socket, not HTTP)
- **Lifecycle:** Go spawns Python sidecar on first bridge call (lazy init), kills on MCP server shutdown via context cancellation
- **Crash recovery:** EOF on stdout triggers automatic respawn with exponential backoff (max 3 retries)
- **Cache location:** Python in-memory cache (dict/LRU) lives in the sidecar process; Go-side LRU cache remains for `project_registry` as a second layer
- **Python flush:** Every response must `sys.stdout.flush()` to avoid buffering deadlocks. Use `python3 -u` (unbuffered) flag as belt-and-suspenders.
- **Protocol:** Newline-delimited JSON (one JSON object per line). Request includes `{"id": N, "tool": "...", "args": {...}}`. Response includes `{"id": N, "result": {...}}` or `{"id": N, "error": "..."}`.
- **Backward compatibility:** Keep `--args` CLI mode working for debugging/testing. Add `--sidecar` flag for persistent mode.

## Open Questions

- Should the sidecar have a health-check mechanism (periodic ping), or is EOF detection sufficient?
- What's the right in-memory cache eviction policy for Python? Simple TTL or LRU?
- Should we add `--sidecar` to the existing `__main__.py` or create a separate `sidecar.py` entry point?
