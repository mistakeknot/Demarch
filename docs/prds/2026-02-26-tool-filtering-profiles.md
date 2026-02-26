# PRD: Tool Filtering Profiles for MCP Context Reduction

**Bead:** iv-moyco
**Date:** 2026-02-26
**Brainstorm:** [2026-02-26-tool-filtering-profiles.md](../brainstorms/2026-02-26-tool-filtering-profiles.md)

## Problem

Demarch MCP servers expose ~111 tools total. Each tool definition costs ~100-300 tokens in system prompt context. Agents loading 5 MCP servers pay 15-30k tokens before any work begins. Most tasks only need 10-20 tools. There is no filtering mechanism — every agent sees every tool.

## Solution

Add startup-time tool filtering with named profiles (full/core/minimal) to Go MCP servers. Each server defines tool clusters and profiles. Agents select a profile via environment variable. This is the same pattern proven in mcp-agent-mail's `_should_expose_tool()`.

## Feature Spec

### F1: Tool Filter Package

Add `pkg/mcpfilter/` to each target server (colocated, not shared for v0):
- `Profile` type: `full`, `core`, `minimal`
- `ReadProfile()` reads `MCP_TOOL_PROFILE` env var, with per-server override (e.g., `INTERLOCK_TOOL_PROFILE`)
- `ShouldExpose(profile, toolName, clusterMap)` returns bool
- Default profile: `full` (backward compatible — no behavior change without opt-in)

### F2: Interlock Filtering (20 tools)

Define clusters for Interlock's 20 tools:
- `file_ops` — reserve_files, release_files, check_conflicts, renew_reservations, force_release (~5)
- `messaging` — send_message, fetch_inbox, broadcast_message, list_topic_messages (~4)
- `negotiation` — negotiate_release, request_release, respond_to_release (~3)
- `agent_mgmt` — list_agents, register_agent, set_contact_policy, get_contact_policy (~4)
- `session` — list_window_identities, rename_window, expire_window (~3)
- `guard` — install_precommit_guard, uninstall_precommit_guard (~2 — rarely needed)

Profiles:
- `full`: all 20 tools
- `core`: file_ops + messaging + agent_mgmt (13 tools)
- `minimal`: reserve_files, release_files, send_message, fetch_inbox, list_agents, check_conflicts (6 tools)

### F3: Intermux Filtering (15 tools)

Define clusters for Intermux's 15 tools:
- `monitoring` — activity_feed, agent_health, session_info (~3)
- `inspection` — peek_agent, search_output, who_is_editing (~3)
- `management` — list_agents + others (~9)

Profiles:
- `full`: all 15 tools
- `core`: monitoring + inspection (8 tools)
- `minimal`: list_agents, session_info, activity_feed, who_is_editing (4 tools)

### F4: Intermap Filtering (9 tools)

Define clusters for Intermap's 9 tools:
- `structure` — code_structure, project_registry (~2)
- `analysis` — impact_analysis, change_impact, detect_patterns (~3)
- `navigation` — cross_project_deps, agent_map, live_changes, resolve_project (~4)

Profiles:
- `full`: all 9 tools
- `core`: structure + analysis (5 tools)
- `minimal`: code_structure, project_registry, impact_analysis (3 tools)

## Acceptance Criteria

1. Each target server builds and passes tests
2. Default behavior unchanged (`MCP_TOOL_PROFILE` unset = all tools exposed)
3. `MCP_TOOL_PROFILE=minimal` reduces tools to documented counts
4. Per-server override env vars work (e.g., `INTERLOCK_TOOL_PROFILE=core`)
5. Filtered tools do not appear in MCP tool list (verified via `mcp-cli`)

## Non-Goals

- Shared cross-server filtering library (Phase 2)
- Dynamic profile switching mid-session
- Claude Code plugin.json profile integration
- Python MCP server filtering (mcp-agent-mail already has it)
- Ecosystem-wide "minimal" profile spanning multiple servers
