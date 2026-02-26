# Brainstorm: Tool Filtering Profiles for MCP Context Reduction

**Bead:** iv-moyco
**Date:** 2026-02-26

## Problem Statement

Combined tool surface across loaded Demarch MCP servers exceeds 110 tools. Every agent sees every tool regardless of task scope. Each tool definition consumes ~100-300 tokens of system prompt context, meaning an agent loading 5 MCP servers pays ~15-30k tokens before any work begins. Most tasks only need 10-20 tools.

## Current State

### Tool Counts by MCP Server

| Server | Tools | Language | Pattern |
|--------|-------|----------|---------|
| mcp-agent-mail | 46 | Python | FastMCP + `@_instrument_tool` |
| Interlock | 20 | Go | mcp-go `server.ServerTool` |
| Intermux | 15 | Go | mcp-go |
| Intermap | 9 | Go | mcp-go |
| Interserve | 3 | Go | mcp-go |
| Intersearch | 2 | Python | FastMCP |
| **Total** | **~111** | | |

Note: Intermute is an HTTP/WebSocket coordination service, NOT an MCP server. The bead description incorrectly lists it as a target — the actual MCP targets are the plugin servers above.

### Reference Implementation: mcp-agent-mail

`research/mcp_agent_mail/src/mcp_agent_mail/app.py` has a mature cluster/profile system:

**Clusters** (8 defined):
- `infrastructure` — health_check, ensure_project
- `identity` — create_agent_identity, register_agent, list_window_identities, rename_window, expire_window, whois
- `messaging` — send_message, reply_message, fetch_inbox, mark_message_read, acknowledge_message, search_messages, fetch_topic, fetch_summary, summarize_recent, summarize_thread
- `contact` — request_contact, respond_contact, list_contacts, set_contact_policy
- `file_reservations` — file_reservation_paths, renew_file_reservations, release_file_reservations, force_release_file_reservation, install_precommit_guard, uninstall_precommit_guard
- `workflow_macros` — macro_start_session, macro_contact_handshake, macro_prepare_thread, macro_file_reservation_cycle
- `search` — search_messages
- `build_slots` — (if applicable)

**Profiles** (4 predefined):
- `full` — all tools
- `core` — identity + messaging + file_reservations + macros
- `minimal` — 6 essential tools (register, send, fetch_inbox, reserve, release, health)
- `messaging` — identity + messaging + contact

**Configuration**: `ToolFilterSettings` class in `config.py` — `profile`, `include_clusters`, `exclude_clusters`, `include_tools`, `exclude_tools`.

**Mechanism**: `_should_expose_tool(tool_name)` checks profile → cluster membership → custom include/exclude. Applied at MCP server startup time.

### What's Missing

- No Go-side equivalent of `_should_expose_tool`
- No shared filtering library (each server would need to implement independently)
- No convention for how agents specify their desired profile
- No way to dynamically change profiles mid-session

## Design Options

### Option A: Server-Side Startup Filtering (Like mcp-agent-mail)

Each MCP server reads a `TOOL_PROFILE` env var (or CLI flag) at startup. Tools not in the profile are never registered, so they don't appear in the MCP tool list at all.

**Pros:**
- Simplest to implement — filter at registration time
- Zero runtime overhead — filtered tools don't exist
- Matches the proven mcp-agent-mail pattern
- Works with Claude Code's current MCP integration (no protocol changes)

**Cons:**
- Requires MCP server restart to change profiles
- Each server needs its own cluster definitions
- No cross-server coordination (Interlock "minimal" and Intermap "minimal" are independent)

### Option B: Interbase SDK Filtering Layer

Build a `toolfilter` package in `core/interbase/` that both Go and Python servers import. Provides shared cluster definitions, profile resolution, and a `ShouldExpose(toolName)` function.

**Pros:**
- Single source of truth for clusters and profiles
- Cross-server consistency (same profile name means same scope)
- Can define "ecosystem profiles" that span multiple servers

**Cons:**
- Adds a dependency from every MCP server to interbase
- Python servers need a separate implementation (or subprocess call)
- Cross-server profiles are complex (Interlock's "minimal" tools + Intermap's "minimal" tools = ecosystem "minimal")

### Option C: Plugin.json Profile Declarations

Define profiles in each plugin's `plugin.json` alongside the `mcpServers` entry. Claude Code reads the profile and passes it as an env var when spawning the server.

**Pros:**
- Declarative — profiles are visible in plugin metadata
- Could be extended for Claude Code's deferred tool loading
- No runtime dependency on interbase

**Cons:**
- Claude Code doesn't currently support profile selection in plugin.json
- Would require Claude Code changes or a workaround

## Recommendation

**Option A (startup filtering)** for v0, with cluster/profile definitions colocated in each server. This matches the proven pattern and requires no protocol or SDK changes.

**Phase 2** (deferred): Extract common cluster vocabulary into interbase for cross-server consistency.

## Scope for v0

### Target Servers (by impact)

1. **Interlock** (20 tools → ~6 in minimal) — highest tool count among Go MCP servers
2. **Intermux** (15 tools → ~4 in minimal) — agent visibility tools, many are read-only
3. **Intermap** (9 tools → ~3 in minimal) — code analysis tools

### Profile Definitions

For each target server, define 3 profiles:
- **full** — all tools (default, backward compatible)
- **core** — frequently used tools (~50% reduction)
- **minimal** — essential tools only (~70% reduction)

### Configuration

- Env var: `MCP_TOOL_PROFILE=full|core|minimal` (default: `full`)
- Per-server override: `INTERLOCK_TOOL_PROFILE`, `INTERMUX_TOOL_PROFILE`, etc.
- Cluster membership: defined in each server's tool registration code

### Expected Impact

| Server | Full | Core | Minimal | Reduction (minimal) |
|--------|------|------|---------|---------------------|
| Interlock | 20 | ~12 | ~6 | 70% |
| Intermux | 15 | ~8 | ~4 | 73% |
| Intermap | 9 | ~5 | ~3 | 67% |
| **Total** | **44** | **~25** | **~13** | **~70%** |

At ~200 tokens/tool, minimal profile saves ~6,200 tokens per agent session across these 3 servers.

## Implementation Pattern (Go)

```go
// pkg/mcpfilter/filter.go (in each server, or shared if extracted)
type Profile string
const (
    ProfileFull    Profile = "full"
    ProfileCore    Profile = "core"
    ProfileMinimal Profile = "minimal"
)

type Cluster string
// Each server defines its own clusters

func ShouldExpose(profile Profile, toolName string, clusters map[string][]Cluster) bool {
    if profile == ProfileFull { return true }
    toolClusters := clusters[toolName]
    // Check if any cluster is in the profile's allowed set
}
```

## Open Questions

1. Should profiles be set globally (`MCP_TOOL_PROFILE`) or per-server? → Per-server override with global fallback.
2. Should we add profile to plugin.json for documentation? → Yes, but informational only (no Claude Code integration needed).
3. Should mcp-agent-mail adopt the same env var convention? → Deferred — it already works, just different config path.
