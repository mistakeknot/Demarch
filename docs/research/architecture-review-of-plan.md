# Architecture Review: Agent Capability Discovery Plan
**Plan reviewed:** `docs/plans/2026-02-22-agent-capability-discovery.md`
**Date:** 2026-02-22
**Reviewer:** Flux-drive Architecture & Design Agent

---

## Summary

The plan wires a capability-discovery path across four modules: intermute (server-side storage + HTTP), interlock (MCP tool + registration script), and interflux (plugin manifest). The existing SQLite schema already stores `capabilities_json`, so the main work is plumbing that field through filters and surfacing it to clients. The plan is directionally correct and the scope is appropriate. There are three structural concerns worth resolving before implementation, one silent-failure risk in the bash path, and one simplicity improvement on the interface signature. None are blockers that require a design restart.

---

## 1. Boundaries and Coupling

### 1.1 `discover_agents` tool duplicates `list_agents` — wrong split point

The plan adds `discover_agents` as a new MCP tool in interlock alongside the existing `list_agents`. The two tools do the same thing — query `/api/agents` for a project — differing only by the presence of a `?capability=` query parameter.

This creates two tools that diverge on a single boolean axis (filtered vs. unfiltered), while sharing identical auth, error-handling, and serialization behavior. The correct split is to extend `list_agents` with an optional `capability` argument, not to add a parallel tool. The MCP protocol supports optional parameters; the existing `list_agents` tool in `interverse/interlock/internal/tools/tools.go:605` passes no arguments at all (its Handler ignores `req.Params.Arguments` entirely), which makes adding an optional `capability` string trivial.

**Concrete change:** In `interverse/interlock/internal/tools/tools.go`, add `mcp.WithString("capability", mcp.Description("..."))` to the existing `listAgents` tool definition. In `interverse/interlock/internal/client/client.go`, change the `ListAgents` method to accept a capability string (empty string means no filter). Remove the proposed `discoverAgents` function and registration from `RegisterAll`. This keeps the tool count at 11, avoids parallel data paths, and keeps the consumer surface minimal.

### 1.2 `CLAUDE_PLUGIN_ROOT` is not available in interlock-register.sh

The plan's capability extraction block in Task 2 relies on `CLAUDE_PLUGIN_ROOT` to locate the plugin.json of the calling plugin:

```bash
PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json}"
```

`CLAUDE_PLUGIN_ROOT` is set by Claude Code to the installed cache directory of the plugin that owns the hook. In this case the hook is interlock's `session-start.sh`. When `session-start.sh` calls `interlock-register.sh` (confirmed at `interverse/interlock/hooks/session-start.sh:36`), `CLAUDE_PLUGIN_ROOT` points to interlock's own cache directory — not to the calling agent's plugin root.

The script is trying to read capabilities from interflux's plugin.json, but interflux's `CLAUDE_PLUGIN_ROOT` is unavailable in interlock's hook execution context. The `[[ -n "$AGENT_CAPS" ]]` guard means this silently produces an empty `[]` for every agent — the capabilities field is always sent as `[]`, and the feature does not work. No error or warning is emitted.

**Root cause:** The registration script conflates two distinct responsibilities — agent identity (session-based, computed from tmux/git) and agent capabilities (plugin-manifest-based, belonging to the calling plugin's context). These two concerns have different access models.

**Correct approach:** Capabilities should be pushed by the agent's own plugin context, not pulled by interlock's hook. Two viable paths:

**Option A (preferred):** Add a convention where each plugin that uses interlock writes its capabilities to a well-known path at session start — for example `~/.config/clavain/capabilities-${AGENT_NAME}.json` — and `interlock-register.sh` reads from that path. This keeps the registration script stateless and eliminates the dependency on `CLAUDE_PLUGIN_ROOT` entirely.

**Option B:** Accept capabilities as an optional argument to `interlock-register.sh` (e.g. `$2`), so callers that know their capabilities can pass them. The current call site at `session-start.sh:36` passes only `$SESSION_ID`:

```bash
RESULT=$("${SCRIPT_DIR}/../scripts/interlock-register.sh" "$SESSION_ID" 2>/dev/null)
```

Under Option B, interflux would add its own SessionStart hook that passes capabilities explicitly. This requires each agent plugin to understand interlock's registration protocol, increasing coupling in the wrong direction.

Option A is the better boundary because it decouples the capability declaration from the registration call entirely.

### 1.3 `agentCapabilities` in interflux plugin.json creates a parallel data structure that will drift

The plan adds a top-level `agentCapabilities` map to `interverse/interflux/.claude-plugin/plugin.json` alongside the existing `agents` array. The `agents` array contains paths to agent `.md` files. The `agentCapabilities` map contains agent name strings as keys. These two data structures describe the same set of 17 agents by different identifiers.

This creates a drift surface:
- `agents` uses file path fragments: `"./agents/review/fd-architecture.md"`
- `agentCapabilities` uses bare names: `"fd-architecture"`

The derivation rule (strip `./agents/review/` prefix and `.md` suffix) is implicit and not enforced anywhere. When an agent is renamed, added, or removed, the `agentCapabilities` map has no mechanism to stay in sync.

**Correct approach:** Move the capability declarations into each agent's `.md` file as a front-matter or structured metadata block. Capability data belongs next to the agent definition it describes, not in a sibling structure in the manifest.

If the plugin.json approach must be used (e.g. because agent `.md` files are a Claude Code primitive that cannot be annotated), then the map keys should use the full relative path from `agents` to create a verifiable link:

```json
"agentCapabilities": {
  "agents/review/fd-architecture.md": ["review:architecture", "review:code", "review:design-patterns"]
}
```

This allows a validation step: every key in `agentCapabilities` must appear in `agents`. Without this constraint, drift is undetectable. The current plan provides no such validation.

---

## 2. Pattern Analysis

### 2.1 Interface signature: positional param is correct for the internal Store

The plan changes the `Store` interface in `core/intermute/internal/storage/storage.go:30` from:

```go
ListAgents(ctx context.Context, project string) ([]core.Agent, error)
```

to:

```go
ListAgents(ctx context.Context, project string, capabilities []string) ([]core.Agent, error)
```

This is a breaking change to every implementation (SQLite at `sqlite.go:765`, InMemory at `storage.go:241`, ResilientStore at `resilient.go:126`) and all call sites. The plan identifies these correctly. The approach is correct — nil slices are idiomatic Go for "no filter," and the internal Store interface is not a public API.

For the public Go client at `core/intermute/client/client.go:172`, the existing `ListAgents(ctx, project)` already has a project parameter separate from the struct's `c.Project` field. Adding a third positional parameter makes call sites harder to read:

```go
agents, err := c.ListAgents(ctx, "", []string{"review:architecture"})
```

An options struct is worth the small overhead at the public client boundary:

```go
type ListAgentsOptions struct {
    Project      string
    Capabilities []string
}

func (c *Client) ListAgents(ctx context.Context, opts ListAgentsOptions) ([]Agent, error)
```

The internal Store interface positional parameters are fine. The public client is consumed by Bigend/autarch — keep its call sites readable.

### 2.2 `json_each` SQLite approach is sound

The SQLite driver is `modernc.org/sqlite v1.29.0` (confirmed in `core/intermute/go.mod`). This driver compiles the SQLite amalgamation with JSON1 enabled by default. The `json_each()` table-valued function is available and does not require any explicit extension loading.

The proposed query pattern is correct:

```sql
EXISTS (SELECT 1 FROM json_each(capabilities_json) WHERE json_each.value IN (?, ?, ?))
```

This correctly handles OR semantics (any matching capability), avoids loading all rows into Go for filtering, and is safe from injection because placeholders are used for all capability values.

Edge case: if `capabilities_json` is `NULL` or an empty array `[]` (agents registered before this feature), `json_each(NULL)` returns zero rows with no error, so the EXISTS clause correctly evaluates to false. No guard is needed.

One naming note in the proposed Go code: the loop variable `cap` shadows the builtin `cap()` function:

```go
for i, cap := range capabilities {
```

Rename to `c`, `v`, or `capStr` to avoid the shadow.

---

## 3. Simplicity and YAGNI

### 3.1 Two MCP tools for one query endpoint is the wrong abstraction

Already covered in section 1.1. The structural consequence stated plainly: adding `discover_agents` as a distinct tool forces every agent that wants to discover peers to know two different tool names for what is semantically one operation. Extend `list_agents` with an optional `capability` param. This removes the proposed `DiscoverAgents` client method, the `discoverAgents` tool function, and the updated `RegisterAll` comment entirely.

### 3.2 The integration test in Task 5 belongs in the existing unit test file

The plan proposes creating `core/intermute/internal/http/handlers_agents_integration_test.go` for what is an in-process unit test using `httptest.NewServer` and `storage.NewInMemory()`. This is not an integration test — it does not open a real SQLite file or use a real network socket. The file name implies a different test category than what it is, complicating future test organization.

Merge `TestCapabilityDiscoveryEndToEnd` into the existing `core/intermute/internal/http/handlers_agents_test.go`. The test itself is good and should be kept. The file split is not justified.

### 3.3 The `InMemory.agentHasAnyCapability` helper is correct as proposed

The O(n*m) nested loop is appropriate for the test-only in-memory store. Do not complicate it. This is correct as written.

### 3.4 The `?capability=` comma-split approach is sufficient

The plan uses `?capability=review:architecture,review:safety` with a comma split. This is simpler than repeated `?capability=X&capability=Y` and consistent with the existing single-value `?project=` parameter style. The choice is fine for the current use cases.

---

## Prioritized Findings

**Must fix before implementation:**

1. **`CLAUDE_PLUGIN_ROOT` environment problem in interlock-register.sh (Section 1.2):** The plan's capability extraction will silently produce empty capabilities for all agents. The feature will appear to work (no errors, `[]` sent) but register nothing. This is a design error in the data-flow ownership, not an implementation bug. Resolve before writing the bash code. Recommended: use a well-known per-agent capabilities file written by each plugin's own session hook (Option A).

2. **`agentCapabilities` map will drift from `agents` array (Section 1.3):** The plan creates a parallel data structure with an implicit derivation rule between path-based identifiers and name-based identifiers. Either move capability declarations into the agent `.md` files, or change map keys to full relative paths and add a validation step that keys must appear in `agents`.

**Should fix — structural cleanup:**

3. **Remove `discover_agents` tool, extend `list_agents` with optional `capability` param (Sections 1.1 and 3.1):** One tool, one query endpoint. Add `mcp.WithString("capability", ...)` to the existing `listAgents` tool. Update `ListAgents` on the interlock client to accept a capability string argument. This eliminates the `discoverAgents` function, the `DiscoverAgents` client method, and avoids inflating the registered tool count.

**Minor — low effort:**

4. **Rename `cap` loop variable to avoid shadowing builtin (Section 2.2):** One-character fix in the proposed SQLite query builder.

5. **Merge integration test into existing `handlers_agents_test.go` (Section 3.2):** Avoid creating a misleading file name for an in-process test.

6. **Consider options struct on the public `core/intermute/client/client.go` `ListAgents` (Section 2.1):** Internal Store interface positional params are fine. The public client call sites in autarch deserve a readable API.

---

## Files Referenced

- `/home/mk/projects/Demarch/core/intermute/internal/storage/storage.go` — Store interface (line 30: current `ListAgents` signature), InMemory implementation (line 241)
- `/home/mk/projects/Demarch/core/intermute/internal/storage/sqlite/sqlite.go` — SQLite `ListAgents` (line 765), `capabilities_json` usage (lines 620, 661, 681, 702, 705)
- `/home/mk/projects/Demarch/core/intermute/internal/storage/sqlite/resilient.go` — ResilientStore passthrough (line 126)
- `/home/mk/projects/Demarch/core/intermute/internal/http/handlers_agents.go` — `handleListAgents` (line 58), `s.store.ListAgents` call (line 71), `listAgentsResponse` and `agentJSON` structs
- `/home/mk/projects/Demarch/core/intermute/client/client.go` — Public Go client `ListAgents` (line 172), `Agent` struct (line 43)
- `/home/mk/projects/Demarch/core/intermute/go.mod` — SQLite driver: `modernc.org/sqlite v1.29.0` (JSON1 included)
- `/home/mk/projects/Demarch/interverse/interlock/internal/tools/tools.go` — `RegisterAll` (line 27), `listAgents` tool (line 605)
- `/home/mk/projects/Demarch/interverse/interlock/internal/client/client.go` — `Agent` struct (line 102: missing `Capabilities` and `LastSeen`), `ListAgents` (line 239)
- `/home/mk/projects/Demarch/interverse/interlock/scripts/interlock-register.sh` — current POST payload (lines 36-44), no capabilities field
- `/home/mk/projects/Demarch/interverse/interlock/hooks/session-start.sh` — hook that calls register script (line 36), `CLAUDE_PLUGIN_ROOT` not passed through
- `/home/mk/projects/Demarch/interverse/interflux/.claude-plugin/plugin.json` — `agents` array (17 entries, no `agentCapabilities` yet)
