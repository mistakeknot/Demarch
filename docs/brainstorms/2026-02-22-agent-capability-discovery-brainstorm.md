# Agent Capability Discovery via Intermute Registration
**Bead:** iv-ev4o
**Date:** 2026-02-22
**Status:** Brainstorm

## What We're Building

A capability advertisement and discovery system so agents can declare what they do at registration time, and consumers (flux-drive, intercore dispatch) can query by capability instead of using hardcoded rosters.

## Current State

**The plumbing exists but is disconnected:**

1. **Schema ready**: `agents` table has `capabilities_json TEXT` column (core/intermute schema.sql:73)
2. **Go model ready**: `core.Agent` has `Capabilities []string` (core/models.go:56)
3. **HTTP API ready**: POST `/api/agents` accepts `capabilities` field, GET `/api/agents` returns it (handlers_agents.go:19,40)
4. **Registration sends nothing**: `interlock-register.sh` builds `{id, name, project, session_id}` — no capabilities (line 37-42)
5. **No query filtering**: `handleListAgents` only filters by `?project=`, no `?capability=` param (line 58-94)
6. **Static consumer**: flux-drive uses `agent-roster.md` with hardcoded agent tables — never queries intermute

## Why This Approach

The "schema is ready, producers don't populate it" pattern is the cheapest kind of interop gap to close. We don't need new tables, new APIs, or new protocols — just wire the existing fields end-to-end.

## Key Decisions

### 1. Capability format: flat string tags (not structured)

Use simple string tags like `["review:architecture", "review:safety", "research:docs"]` rather than a structured capability schema. Reasoning:
- Matches the existing `[]string` type in Go model
- Easy to grep, easy to filter
- Structured schemas (with versions, parameters) are premature — we have <20 agent types

### 2. Capability source: plugin.json agents section

Each plugin already declares agents in `plugin.json`. Extract capability tags from there at registration time. No new `capabilities.json` file needed — one source of truth.

Example from interflux's plugin.json agents section:
```json
{
  "agents": [
    {"name": "fd-architecture", "capabilities": ["review:architecture", "review:code"]},
    {"name": "fd-safety", "capabilities": ["review:safety", "review:security"]}
  ]
}
```

Fallback for plugins without agent declarations: register with empty capabilities (backward compatible, same as today).

### 3. Registration: interlock-register.sh reads plugin manifest

At session start, `interlock-register.sh` already runs. Enhance it to:
1. Find the plugin's `plugin.json` (via `$CLAUDE_PLUGIN_ROOT`)
2. Extract agent names and capabilities from the `agents` array
3. Include `capabilities` in the POST payload

### 4. Query: add `?capability=` filter to GET /api/agents

Server-side filtering in `handleListAgents`. Supports comma-separated values for OR matching: `?capability=review:architecture,review:safety` returns agents with either capability.

### 5. Consumer: new `discover_agents` MCP tool in interlock

Add a `discover_agents` tool to the interlock MCP server that wraps the capability query:
```
discover_agents(capability: "review:architecture") → [{name, capabilities, status, last_seen}]
```

This lets flux-drive (and any other consumer) dynamically discover agents instead of reading a static roster.

### 6. Flux-drive migration: gradual, not big-bang

Phase 1: Add dynamic discovery alongside static roster (union of both).
Phase 2: When all plugins advertise capabilities, deprecate static roster.

## Scope

### In scope
- Add `capabilities` field to interlock-register.sh payload
- Add `capabilities` to plugin.json agent declarations (interflux as first adopter)
- Add `?capability=` query param to intermute GET /api/agents
- Add `discover_agents` MCP tool to interlock
- Integration test: register with capabilities, query by capability, verify result

### Out of scope (future work)
- Capability versioning or semantic matching
- Automatic flux-drive roster replacement (Phase 2, separate bead)
- Capability-scoped dispatch in intercore (iv-5pvo, blocked by this)
- Cross-project capability federation

## Open Questions

1. **Should capabilities be per-agent or per-plugin?** Recommendation: per-agent (an agent named `fd-architecture` has different capabilities than `fd-safety`, even though both come from interflux).
2. **Namespace convention for tags?** Recommendation: `domain:specialization` format — `review:architecture`, `research:docs`, `coordination:files`.

## Modules Touched

| Module | Change |
|--------|--------|
| core/intermute | Add `?capability=` filter to handleListAgents |
| interverse/interlock | Enhance register script, add discover_agents MCP tool, update client |
| interverse/interflux | Add capabilities to plugin.json agents, consume discover_agents in flux-drive (Phase 2) |
