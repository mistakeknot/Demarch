# PRD: Agent Capability Discovery

## Problem

Agents register with intermute but never declare what they can do. Consumers like flux-drive rely on hardcoded static rosters, so custom agents from companion plugins are invisible to the dispatch system. This blocks dynamic agent discovery and capability-scoped dispatch.

## Solution

Wire the existing but unpopulated `capabilities_json` field end-to-end: producers advertise capabilities at registration, the server filters by capability, and a new MCP tool exposes discovery to any consumer.

## Features

### F1: Capability Registration
**What:** Enhance `interlock-register.sh` to read agent capabilities from the plugin manifest and include them in the POST `/api/agents` payload.
**Acceptance criteria:**
- [ ] `interlock-register.sh` reads `$CLAUDE_PLUGIN_ROOT/.claude-plugin/plugin.json` agents array
- [ ] Each agent's `capabilities` field is extracted and included in the registration POST body
- [ ] Plugins without agent declarations register with empty capabilities (backward compatible)
- [ ] Registered agents appear in intermute with populated `capabilities_json`

### F2: Capability Query Filter
**What:** Add `?capability=` query parameter to intermute's GET `/api/agents` endpoint for server-side filtering.
**Acceptance criteria:**
- [ ] GET `/api/agents?capability=review:architecture` returns only agents with that capability
- [ ] Comma-separated values use OR matching: `?capability=review:architecture,review:safety`
- [ ] Existing `?project=` filter continues to work, composable with `?capability=`
- [ ] Empty or missing `?capability=` returns all agents (backward compatible)
- [ ] Go unit test covers: single capability match, multi-capability OR, no match, combined project+capability

### F3: discover_agents MCP Tool
**What:** Add a `discover_agents` tool to the interlock MCP server that wraps the capability query.
**Acceptance criteria:**
- [ ] Tool accepts optional `capability` string parameter
- [ ] Returns array of `{name, capabilities, status, last_seen}` objects
- [ ] Works with no arguments (returns all agents, same as `list_agents`)
- [ ] Interlock client.go gets a `DiscoverAgents(ctx, capability)` method
- [ ] Tool is registered in interlock's tool list

### F4: Interflux Capability Declarations
**What:** Add capability tags to interflux's plugin.json agents section as the first adopter.
**Acceptance criteria:**
- [ ] Each agent in interflux's plugin.json has a `capabilities` array with `domain:specialization` tags
- [ ] Tags follow the convention: `review:architecture`, `review:safety`, `research:docs`, etc.
- [ ] Plugin validates correctly after changes (`python3 -c "import json; json.load(open('plugin.json'))"`)
- [ ] At least the 7 technical review agents and 5 research agents have declarations

## Non-goals

- Capability versioning or semantic matching
- Automatic flux-drive roster replacement (future Phase 2)
- Capability-scoped dispatch in intercore (iv-5pvo, separate bead)
- Cross-project capability federation
- Structured capability schemas with parameters

## Dependencies

- intermute service running (existing)
- interlock plugin installed (existing)
- interflux plugin installed (existing)

## Open Questions

None — all resolved in brainstorm. Per-agent capabilities with `domain:specialization` tag format.
