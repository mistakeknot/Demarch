# Module 4: Agent Overlay — Build Analysis

## Overview

Module 4 adds the agent overlay capability to intermap, showing which agents are working on which projects and files. This is accomplished through three components: an intermute HTTP client, the `agent_map` MCP tool, and supporting tests.

## Files Created/Modified

### Created

1. **`/root/projects/Interverse/plugins/intermap/internal/client/client.go`**
   - Intermute HTTP client using functional options pattern (consistent with interlock's `internal/client/client.go`)
   - Types: `Agent`, `Reservation`, `Client`, `Option`
   - Methods: `NewClient()`, `WithBaseURL()`, `Available()`, `ListAgents()`, `ListReservations()`
   - Graceful degradation: `Available()` check returns `nil, nil` when no base URL is configured
   - 5-second HTTP timeout to avoid blocking the MCP server

2. **`/root/projects/Interverse/plugins/intermap/internal/client/client_test.go`**
   - 6 tests using `httptest.NewServer` for mock HTTP:
     - `TestListAgents` — happy path with 2 agents
     - `TestListReservations` — happy path with 1 reservation
     - `TestClient_Unavailable` — no base URL returns nil without error
     - `TestClient_ServerDown` — unreachable server returns error
     - `TestListReservations_WithProject` — project query parameter filtering
     - `TestListAgents_HTTPError` — HTTP 500 returns error

3. **`/root/projects/Interverse/plugins/intermap/internal/tools/tools_test.go`**
   - `TestStringOr` — string, empty string, nil cases
   - `TestStringOr_NonStringTypes` — int, bool fall through to default

### Modified

4. **`/root/projects/Interverse/plugins/intermap/internal/tools/tools.go`**
   - Added `"strings"` and `client` imports
   - Changed `RegisterAll(s *server.MCPServer)` to `RegisterAll(s *server.MCPServer, c *client.Client)`
   - Added `agentMap(c)` to `s.AddTools()` call
   - Added types: `AgentOverlay`, `AgentMapResult`
   - Added `agentMap()` function implementing the `agent_map` MCP tool

5. **`/root/projects/Interverse/plugins/intermap/cmd/intermap-mcp/main.go`**
   - Added `client` import
   - Creates `client.NewClient(client.WithBaseURL(os.Getenv("INTERMUTE_URL")))` before server setup
   - Passes client to `tools.RegisterAll(s, c)`

## Design Decisions

### Client Architecture
- **Functional options pattern** (`WithBaseURL`) matches interlock's client, maintaining ecosystem consistency
- **Simpler than interlock's client** — intermap is read-only (no reservations to create, no messages to send), so no need for `doJSON` helper, auth headers, or socket transport
- **Nil-safe** — `Available()` check prevents any HTTP calls when `INTERMUTE_URL` is empty, returning `nil, nil` instead of errors

### agent_map Tool Behavior
The tool combines three data sources into a single overlay:

1. **Project registry** (filesystem scan via `registry.Scan`) — always available
2. **Agent list** (intermute `/api/agents`) — optional, depends on intermute being reachable
3. **File reservations** (intermute `/api/reservations`) — optional, depends on intermute

The response always includes `agents_available` and `agents_error` fields so callers can understand the data completeness:

| Scenario | `agents_available` | `agents_error` | `agents` |
|---|---|---|---|
| INTERMUTE_URL not set | false | "intermute not configured..." | [] |
| Intermute unreachable | true | "intermute unreachable: ..." | [] |
| Reservations fail | true | "reservations unavailable: ..." | agents without reservations |
| All healthy | true | "" | full overlay |

### Project-Agent Matching
Agents are matched to projects by:
1. **Exact name match** — agent's `project` field matches a discovered project name
2. **Path substring** — fallback: check if agent's project name appears in any project path, or any project name appears in the agent's project string

This handles cases where agents register with either the project name ("interlock") or the full path.

### Reservation Indexing
Reservations are indexed by `agent_id` into a `map[string][]string` of file patterns. Only active reservations (`IsActive: true`) are included. This gives each agent overlay entry a list of file patterns they're currently working on.

## Build and Test Results

```
$ go build ./cmd/intermap-mcp/
# success, no errors

$ go test ./...
?   	github.com/mistakeknot/intermap/cmd/intermap-mcp	[no test files]
ok  	github.com/mistakeknot/intermap/internal/cache	0.062s
ok  	github.com/mistakeknot/intermap/internal/client	0.010s
ok  	github.com/mistakeknot/intermap/internal/registry	0.006s
ok  	github.com/mistakeknot/intermap/internal/tools	0.006s
```

All packages build cleanly. All tests pass across all 4 internal packages.

## Integration Points

- **INTERMUTE_URL** environment variable — configured in `.claude-plugin/plugin.json` as `http://127.0.0.1:7338` (intermute's default port)
- **interlock compatibility** — the client types (`Agent`, `Reservation`) match intermute's API responses, which are the same endpoints interlock uses
- **MCP tool registration** — `agent_map` is registered alongside `project_registry` and `resolve_project` via `RegisterAll()`

## Potential Future Improvements

1. **Caching** — Agent/reservation data could be cached with short TTL (10-30s) to avoid hitting intermute on every call
2. **Unix socket transport** — Like interlock, could add `WithSocketPath()` option for local intermute connections
3. **Agent heartbeat status** — Could calculate "stale" agents based on `LastSeen` timestamp
4. **Reservation conflict visualization** — Could highlight overlapping reservations between agents
