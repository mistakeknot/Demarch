# Task 1 Execution: Add `?capability=` filter to intermute GET /api/agents

**Date:** 2026-02-22
**Status:** COMPLETE -- all tests pass
**Plan:** `/root/projects/Demarch/docs/plans/2026-02-22-agent-capability-discovery.md`

---

## Summary

Implemented the `?capability=` query parameter on the `GET /api/agents` endpoint in intermute, enabling OR-matching capability-based agent discovery. Added a non-breaking `DiscoverAgents` method to the public Go client. All 87 tests across 11 packages pass.

---

## Files Modified

### 1. `core/intermute/internal/storage/storage.go` (Store interface + InMemory impl)

**Interface change** (line 30):
```go
// Before:
ListAgents(ctx context.Context, project string) ([]core.Agent, error)

// After:
ListAgents(ctx context.Context, project string, capabilities []string) ([]core.Agent, error)
```

**InMemory implementation** (line 241):
- Updated `ListAgents` to accept `capabilities []string` parameter
- Changed from single `if` filter to sequential `continue` guards (project check, then capability check)
- Added `hasAnyCapability(agentCaps, queryCaps []string) bool` helper function using nested loop O(n*m) comparison

### 2. `core/intermute/internal/storage/sqlite/sqlite.go` (SQLite impl, line 765)

**Query building** updated from simple `WHERE project = ?` to dynamic condition builder:
- `conditions []string` and `args []any` accumulators
- Project filter added as first condition when non-empty
- Capability filter uses `EXISTS (SELECT 1 FROM json_each(...) WHERE json_each.value IN (?,...))` subquery
- **Critical NULL guard**: `CASE WHEN capabilities_json IS NULL OR capabilities_json = '' OR capabilities_json = 'null' THEN '[]' ELSE capabilities_json END` wraps the `json_each()` input to handle legacy agents with no capabilities
- Conditions joined with `AND`; the rows scan loop is unchanged

### 3. `core/intermute/internal/storage/sqlite/resilient.go` (line 126)

**Passthrough update**: `ResilientStore.ListAgents` signature updated to forward the `capabilities []string` parameter to `r.inner.ListAgents(ctx, project, capabilities)`.

### 4. `core/intermute/internal/http/handlers_agents.go` (line 58)

**Handler update** in `handleListAgents`:
- Added `?capability=` query parameter parsing after the project/auth block
- Comma-split with trailing-comma guard: `strings.Split` + `strings.TrimSpace` + empty-string filter
- Passes parsed `capabilities` slice to `s.store.ListAgents(r.Context(), project, capabilities)`

### 5. `core/intermute/client/client.go` (after line 196)

**New method** `DiscoverAgents(ctx context.Context, capabilities []string) ([]Agent, error)`:
- Non-breaking addition alongside existing `ListAgents` (which keeps its original `(ctx, project)` signature)
- Uses `url.Values` to build query with project from `c.Project` and `capability=` from joined capabilities
- Returns `[]Agent` with standard error handling

### 6. `core/intermute/internal/storage/sqlite/sqlite_test.go`

**Caller fixes**: Updated 3 `ListAgents` call sites to pass `nil` as the new capabilities parameter:
- Line 61: `st.ListAgents(ctx, "", nil)` (was `st.ListAgents(ctx, "")`)
- Line 70: `st.ListAgents(ctx, "proj-a", nil)` (was `st.ListAgents(ctx, "proj-a")`)
- Line 93: `st.ListAgents(ctx, "proj", nil)` (was `st.ListAgents(ctx, "proj")`)

### 7. `core/intermute/internal/http/handlers_agents_test.go`

**Two new test functions added** (inserted before `TestPatchAgentMetadata`):

#### `TestListAgentsCapabilityFilter` (5 subtests)
Registers 4 agents with varying capabilities (including one with empty caps), then tests:
1. **single match** -- `capability=review:architecture` returns 2 agents (agent-arch + agent-both)
2. **multi OR match** -- `capability=review:architecture,review:security` returns 3 agents
3. **no match** -- `capability=research:docs` returns 0 agents
4. **no filter returns all** -- no capability param returns all 4 agents
5. **trailing comma ignored** -- `capability=review:architecture,` returns 2 (not error)

All subtests include HTTP status code assertions (`resp.StatusCode != http.StatusOK`).

#### `TestCapabilityDiscoveryEndToEnd`
Simulates the full interlock registration flow:
- Registers 4 agents including realistic names (fd-architecture, fd-safety, repo-research-analyst, agent-nocaps)
- Verifies single-capability query returns exact match (review:architecture vs research:architecture distinction)
- Verifies OR query across capability domains (review:safety + research:codebase)
- Verifies capabilities are returned in the response JSON

---

## Design Decisions

1. **Non-breaking client API**: `ListAgents(ctx, project)` signature preserved on the public `Client` type. New `DiscoverAgents` method added alongside it. The `client_test.go` callers at lines 92 and 119 are unchanged.

2. **OR semantics**: Capability filtering uses OR matching -- an agent is returned if it has *any* of the requested capabilities. This matches the discovery use case ("find me any agent that can do architecture OR safety review").

3. **SQL injection safety**: Capability values are passed as parameterized `?` placeholders, never interpolated into the query string.

4. **NULL/empty guard**: The `CASE WHEN ... THEN '[]' ELSE capabilities_json END` pattern ensures `json_each()` never receives NULL or empty string, which would cause SQLite errors on legacy agents registered before capabilities were populated.

5. **Trailing comma tolerance**: The handler trims whitespace and filters empty strings from the comma-split, so `capability=a,b,` and `capability=a, b` both work correctly.

---

## Test Results

```
ok  github.com/mistakeknot/intermute/client                    0.014s
ok  github.com/mistakeknot/intermute/cmd/intermute              0.004s
ok  github.com/mistakeknot/intermute/internal                   0.040s
ok  github.com/mistakeknot/intermute/internal/auth              0.005s
ok  github.com/mistakeknot/intermute/internal/cli               0.005s
ok  github.com/mistakeknot/intermute/internal/glob              0.004s
ok  github.com/mistakeknot/intermute/internal/http              0.250s
ok  github.com/mistakeknot/intermute/internal/names             0.003s
ok  github.com/mistakeknot/intermute/internal/server            0.006s
ok  github.com/mistakeknot/intermute/internal/storage           0.005s
ok  github.com/mistakeknot/intermute/internal/storage/sqlite    0.710s
ok  github.com/mistakeknot/intermute/internal/ws                0.535s
```

ALL PASS (87 tests across 11 packages, 0 failures).

---

## What's Left (Not in Task 1 Scope)

- **Task 2**: Add capabilities field to `interlock-register.sh` (reads per-agent capability files)
- **Task 3**: Extend `list_agents` MCP tool in interlock with optional `capability` param
- **Task 4**: Add capability declarations to interflux `plugin.json` + session hook to write per-agent files
- **Task 5**: End-to-end test already written as part of Task 1 (TestCapabilityDiscoveryEndToEnd)
