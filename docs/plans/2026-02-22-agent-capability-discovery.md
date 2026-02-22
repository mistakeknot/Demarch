# Agent Capability Discovery Implementation Plan
**Phase:** planned (as of 2026-02-22T16:50:21Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire the existing but unpopulated `capabilities_json` field end-to-end so agents advertise capabilities at registration and consumers can query by capability.

**Architecture:** Four independent modules touched: intermute (server-side filter), interlock (registration script + extended MCP tool), interflux (capability declarations). The intermute Go model, HTTP structs, and SQLite schema already support capabilities — changes are at the producer (registration) and consumer (query/discovery) edges.

**Tech Stack:** Go 1.24 (intermute, interlock), Bash (interlock-register.sh), JSON (plugin.json manifests)

**Review Fixes Applied:** Plan updated after flux-drive review (3 agents: architecture, correctness, quality). Key changes from original:
- **M1**: Registration reads per-agent capability files (`~/.config/clavain/capabilities-<name>.json`) instead of `CLAUDE_PLUGIN_ROOT` (which points to interlock's cache, not the calling plugin)
- **M2**: SQL `json_each()` wrapped in CASE guard for NULL/empty `capabilities_json`
- **M3**: Capability declarations use full relative paths as keys in `agentCapabilities` map
- **S1**: Extend existing `list_agents` MCP tool with optional `capability` param instead of adding `discover_agents`
- **S2**: Add `DiscoverAgents` method alongside `ListAgents` on intermute client (non-breaking)
- **Minor**: Renamed `cap`→`capability`, fixed jq `-r`→`-c`, added empty-caps fixture, trailing-comma guard, decode error checks, cleaned self-correcting comments

---

### Task 1: Add `?capability=` filter to intermute GET /api/agents

**Files:**
- Modify: `core/intermute/internal/storage/storage.go:30` (interface)
- Modify: `core/intermute/internal/storage/storage.go:241-248` (InMemory impl)
- Modify: `core/intermute/internal/storage/sqlite/sqlite.go:765-810` (SQLite impl)
- Modify: `core/intermute/internal/storage/sqlite/resilient.go:126-132` (resilient wrapper)
- Modify: `core/intermute/internal/http/handlers_agents.go:58-94` (handler)
- Modify: `core/intermute/client/client.go:172-196` (add DiscoverAgents method)
- Modify: `core/intermute/client/client_test.go:92,119` (fix caller signatures)
- Test: `core/intermute/internal/http/handlers_agents_test.go`

**Step 1: Write the failing tests**

Add to `core/intermute/internal/http/handlers_agents_test.go`:

```go
func TestListAgentsCapabilityFilter(t *testing.T) {
	svc := NewService(storage.NewInMemory())
	srv := httptest.NewServer(NewRouter(svc, nil, nil))
	defer srv.Close()

	// Register agents with capabilities — includes one with empty caps
	for _, tc := range []struct {
		name string
		caps []string
	}{
		{"agent-arch", []string{"review:architecture", "review:code"}},
		{"agent-safety", []string{"review:safety", "review:security"}},
		{"agent-both", []string{"review:architecture", "review:safety"}},
		{"agent-nocaps", []string{}},
	} {
		payload := map[string]any{"name": tc.name, "project": "proj-a", "capabilities": tc.caps}
		buf, _ := json.Marshal(payload)
		resp, err := http.Post(srv.URL+"/api/agents", "application/json", bytes.NewReader(buf))
		if err != nil {
			t.Fatalf("register failed: %v", err)
		}
		resp.Body.Close()
	}

	tests := []struct {
		name     string
		query    string
		expected int
	}{
		{"single match", "?project=proj-a&capability=review:architecture", 2},
		{"multi OR match", "?project=proj-a&capability=review:architecture,review:security", 3},
		{"no match", "?project=proj-a&capability=research:docs", 0},
		{"no filter returns all", "?project=proj-a", 4},
		{"trailing comma ignored", "?project=proj-a&capability=review:architecture,", 2},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp, err := http.Get(srv.URL + "/api/agents" + tc.query)
			if err != nil {
				t.Fatalf("request failed: %v", err)
			}
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusOK {
				t.Fatalf("expected 200, got %d", resp.StatusCode)
			}

			var result listAgentsResponse
			if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
				t.Fatalf("decode failed: %v", err)
			}
			if len(result.Agents) != tc.expected {
				t.Fatalf("expected %d agents, got %d", tc.expected, len(result.Agents))
			}
		})
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd core/intermute && go test ./internal/http/ -run TestListAgentsCapabilityFilter -v`
Expected: FAIL — ListAgents signature doesn't accept capability parameter yet.

**Step 3: Update the Store interface**

In `core/intermute/internal/storage/storage.go`, change the `ListAgents` signature:

```go
ListAgents(ctx context.Context, project string, capabilities []string) ([]core.Agent, error)
```

**Step 4: Update InMemory implementation**

In `core/intermute/internal/storage/storage.go`, update `InMemory.ListAgents`:

```go
func (m *InMemory) ListAgents(_ context.Context, project string, capabilities []string) ([]core.Agent, error) {
	var out []core.Agent
	for _, agent := range m.agents {
		if project != "" && agent.Project != project {
			continue
		}
		if len(capabilities) > 0 && !hasAnyCapability(agent.Capabilities, capabilities) {
			continue
		}
		out = append(out, agent)
	}
	return out, nil
}

// hasAnyCapability reports whether agentCaps contains at least one element from queryCaps.
func hasAnyCapability(agentCaps, queryCaps []string) bool {
	for _, qc := range queryCaps {
		for _, ac := range agentCaps {
			if ac == qc {
				return true
			}
		}
	}
	return false
}
```

**Step 5: Update SQLite implementation**

In `core/intermute/internal/storage/sqlite/sqlite.go`, update `Store.ListAgents`:

```go
func (s *Store) ListAgents(_ context.Context, project string, capabilities []string) ([]core.Agent, error) {
	query := `SELECT id, session_id, name, project, capabilities_json, metadata_json, status, created_at, last_seen
		FROM agents`
	var conditions []string
	var args []any
	if project != "" {
		conditions = append(conditions, "project = ?")
		args = append(args, project)
	}
	if len(capabilities) > 0 {
		// OR match: agent has any of the requested capabilities
		// Guard against NULL/empty capabilities_json (legacy agents)
		capPlaceholders := make([]string, len(capabilities))
		for i, capability := range capabilities {
			capPlaceholders[i] = "?"
			args = append(args, capability)
		}
		conditions = append(conditions,
			fmt.Sprintf("EXISTS (SELECT 1 FROM json_each(CASE WHEN capabilities_json IS NULL OR capabilities_json = '' OR capabilities_json = 'null' THEN '[]' ELSE capabilities_json END) WHERE json_each.value IN (%s))",
				strings.Join(capPlaceholders, ",")))
	}
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	query += " ORDER BY last_seen DESC"
	// ... rest unchanged (rows scan loop)
```

Note: only the query building changes. The rows.Next() scan loop stays identical.

**Step 6: Update ResilientStore wrapper**

In `core/intermute/internal/storage/sqlite/resilient.go`, update the `ListAgents` passthrough:

```go
func (r *ResilientStore) ListAgents(ctx context.Context, project string, capabilities []string) ([]core.Agent, error) {
	var result []core.Agent
	err := r.withRetry(ctx, "ListAgents", func() error {
		var innerErr error
		result, innerErr = r.inner.ListAgents(ctx, project, capabilities)
		return innerErr
	})
	return result, err
}
```

**Step 7: Update handler to parse `?capability=` with trailing-comma guard**

In `core/intermute/internal/http/handlers_agents.go`, update `handleListAgents`:

```go
func (s *Service) handleListAgents(w http.ResponseWriter, r *http.Request) {
	project := r.URL.Query().Get("project")
	info, _ := auth.FromContext(r.Context())

	if info.Mode == auth.ModeAPIKey {
		if project == "" {
			project = info.Project
		} else if project != info.Project {
			w.WriteHeader(http.StatusForbidden)
			return
		}
	}

	var capabilities []string
	if capParam := r.URL.Query().Get("capability"); capParam != "" {
		for _, c := range strings.Split(capParam, ",") {
			if c = strings.TrimSpace(c); c != "" {
				capabilities = append(capabilities, c)
			}
		}
	}

	agents, err := s.store.ListAgents(r.Context(), project, capabilities)
	// ... rest unchanged
```

**Step 8: Fix all callers of Store.ListAgents**

Run `grep -rn 'ListAgents(' core/intermute/` and update every call site to pass `nil` for capabilities where no filtering is needed.

Key callers to update:
- `core/intermute/internal/storage/sqlite/sqlite_test.go` — update test calls to `ListAgents(ctx, project, nil)`
- `core/intermute/internal/storage/sqlite/resilient.go:126,131` — already updated in Step 6
- `core/intermute/internal/http/handlers_agents.go:71` — already updated in Step 7

**Do NOT change `core/intermute/client/client.go:172`** — the public client `ListAgents` method stays at its current signature for backward compatibility. Instead, add a new `DiscoverAgents` method (Step 9).

**Step 9: Add DiscoverAgents method to intermute client (non-breaking)**

In `core/intermute/client/client.go`, add alongside the existing `ListAgents`:

```go
// DiscoverAgents lists agents filtered by capability tags.
// Capabilities uses OR matching — agents with any of the given capabilities are returned.
func (c *Client) DiscoverAgents(ctx context.Context, capabilities []string) ([]Agent, error) {
	path := "/api/agents?project=" + url.QueryEscape(c.Project)
	if len(capabilities) > 0 {
		path += "&capability=" + url.QueryEscape(strings.Join(capabilities, ","))
	}
	resp, err := c.doRequest(ctx, http.MethodGet, path, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result struct {
		Agents []Agent `json:"agents"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result.Agents, nil
}
```

Note: `client/client_test.go:92,119` call `c.ListAgents(ctx, "")` — these are unchanged because `ListAgents` signature is preserved.

**Step 10: Run tests to verify they pass**

Run: `cd core/intermute && go test ./... -v`
Expected: ALL PASS

**Step 11: Commit**

```bash
cd core/intermute && git add internal/ client/ && git commit -m "feat: add ?capability= filter to GET /api/agents with DiscoverAgents client method"
```

---

### Task 2: Add `capabilities` field to interlock-register.sh

**Files:**
- Modify: `interverse/interlock/scripts/interlock-register.sh`

**Design note:** `CLAUDE_PLUGIN_ROOT` in the hook context points to interlock's own cache directory, NOT to the calling agent's plugin. Each plugin that wants capabilities must write them to a per-agent file at session start. The registration script reads from that well-known path.

**Step 1: Update registration payload to include capabilities**

In `interverse/interlock/scripts/interlock-register.sh`, after the PROJECT detection (line 32), add capability extraction from the per-agent capability file:

```bash
# Extract capabilities from per-agent capability file (written by each plugin's session hook)
CAPABILITIES="[]"
CAPS_FILE="${HOME}/.config/clavain/capabilities-${AGENT_NAME}.json"
if [[ -f "$CAPS_FILE" ]]; then
    AGENT_CAPS=$(jq -c '.' "$CAPS_FILE" 2>/dev/null)
    if [[ -n "$AGENT_CAPS" ]] && [[ "$AGENT_CAPS" != "null" ]]; then
        CAPABILITIES="$AGENT_CAPS"
    fi
fi
```

Then update the POST payload (line 37-42) to include capabilities:

```bash
RESPONSE=$(intermute_curl POST "/api/agents" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg id "claude-${SESSION_ID:0:8}" \
        --arg name "$AGENT_NAME" \
        --arg project "$PROJECT" \
        --arg session_id "$SESSION_ID" \
        --argjson capabilities "$CAPABILITIES" \
        '{id: $id, name: $name, project: $project, session_id: $session_id, capabilities: $capabilities}')" \
    2>/dev/null) || exit 1
```

**Step 2: Test manually**

Run: `mkdir -p ~/.config/clavain && echo '["review:architecture","review:code"]' > ~/.config/clavain/capabilities-test-agent.json`
Run: `AGENT_NAME=test-agent SESSION_ID=test-123 bash interverse/interlock/scripts/interlock-register.sh test-123`

Verify the POST body includes `"capabilities": ["review:architecture","review:code"]`. If intermute isn't running, the registration will fail — that's fine, we're validating the payload construction.

**Step 3: Commit**

```bash
cd interverse/interlock && git add scripts/interlock-register.sh && git commit -m "feat: send capabilities from per-agent file on registration"
```

---

### Task 3: Extend `list_agents` MCP tool with capability filtering

**Files:**
- Modify: `interverse/interlock/internal/client/client.go:102-107` (Agent struct)
- Modify: `interverse/interlock/internal/client/client.go` (add DiscoverAgents method)
- Modify: `interverse/interlock/internal/tools/tools.go:605-621` (extend list_agents)

**Design note:** Instead of adding a separate `discover_agents` tool (which duplicates `list_agents`), we extend the existing `list_agents` tool with an optional `capability` parameter. This keeps the tool count at 11.

**Step 1: Update interlock Agent struct**

In `interverse/interlock/internal/client/client.go`, add missing fields to `Agent`:

```go
type Agent struct {
	AgentID      string   `json:"agent_id"`
	Name         string   `json:"name"`
	Project      string   `json:"project"`
	Capabilities []string `json:"capabilities"`
	Status       string   `json:"status"`
	LastSeen     string   `json:"last_seen"`
}
```

**Step 2: Add DiscoverAgents client method**

In `interverse/interlock/internal/client/client.go`, add after `ListAgents`:

```go
// DiscoverAgents lists agents filtered by capability tags.
// Capabilities uses OR matching — agents with any of the given capabilities are returned.
// Pass nil or empty slice to list all agents (same as ListAgents).
func (c *Client) DiscoverAgents(ctx context.Context, capabilities []string) ([]Agent, error) {
	path := "/api/agents?project=" + url.QueryEscape(c.project)
	if len(capabilities) > 0 {
		path += "&capability=" + url.QueryEscape(strings.Join(capabilities, ","))
	}
	var result struct {
		Agents []Agent `json:"agents"`
	}
	if err := c.doJSON(ctx, "GET", path, nil, &result); err != nil {
		return nil, err
	}
	return result.Agents, nil
}
```

**Step 3: Extend list_agents tool with optional capability param**

In `interverse/interlock/internal/tools/tools.go`, modify the existing `listAgents` function:

```go
func listAgents(c *client.Client) server.ServerTool {
	return server.ServerTool{
		Tool: mcp.NewTool("list_agents",
			mcp.WithDescription("List agents registered with intermute. Optionally filter by capability tag (e.g. 'review:architecture'). Comma-separated capabilities use OR matching."),
			mcp.WithString("capability",
				mcp.Description("Capability tag to filter by (e.g. 'review:architecture'). Comma-separated for OR matching. Omit to list all agents."),
			),
		),
		Handler: func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			capability, _ := req.Params.Arguments["capability"].(string)
			var agents []client.Agent
			var err error
			if capability != "" {
				var caps []string
				for _, c := range strings.Split(capability, ",") {
					if c = strings.TrimSpace(c); c != "" {
						caps = append(caps, c)
					}
				}
				agents, err = c.DiscoverAgents(ctx, caps)
			} else {
				agents, err = c.ListAgents(ctx)
			}
			if err != nil {
				return mcp.NewToolResultError(fmt.Sprintf("list agents: %v", err)), nil
			}
			if agents == nil {
				agents = make([]client.Agent, 0)
			}
			return jsonResult(agents)
		},
	}
}
```

No changes to `RegisterAll` — tool count stays at 11.

**Step 4: Build and verify**

Run: `cd interverse/interlock && go build ./...`
Expected: Compiles successfully.

**Step 5: Run existing tests**

Run: `cd interverse/interlock && go test ./... -v`
Expected: ALL PASS (no regressions).

**Step 6: Commit**

```bash
cd interverse/interlock && git add internal/ && git commit -m "feat: extend list_agents MCP tool with optional capability filtering"
```

---

### Task 4: Add capability declarations to interflux + write per-agent capability files

**Files:**
- Modify: `interverse/interflux/.claude-plugin/plugin.json`
- Create: `interverse/interflux/hooks/write-capabilities.sh` (SessionStart hook)
- Modify: `interverse/interflux/.claude-plugin/hooks/hooks.json` (register new hook)

**Design note:** The `agentCapabilities` map uses full relative paths as keys (matching the `agents` array) to prevent drift. A session-start hook writes per-agent capability files to `~/.config/clavain/capabilities-<name>.json` so interlock's registration script can read them.

**Step 1: Add `agentCapabilities` map to plugin.json**

Use full relative paths as keys to match the `agents` array entries:

```json
{
  "agentCapabilities": {
    "./agents/review/fd-architecture.md": ["review:architecture", "review:code", "review:design-patterns"],
    "./agents/review/fd-safety.md": ["review:safety", "review:security", "review:deployment"],
    "./agents/review/fd-correctness.md": ["review:correctness", "review:concurrency", "review:data-consistency"],
    "./agents/review/fd-user-product.md": ["review:user-experience", "review:product", "review:scope"],
    "./agents/review/fd-quality.md": ["review:quality", "review:style", "review:conventions"],
    "./agents/review/fd-game-design.md": ["review:game-design", "review:balance", "review:pacing"],
    "./agents/review/fd-performance.md": ["review:performance", "review:bottlenecks", "review:scaling"],
    "./agents/review/fd-systems.md": ["review:systems-thinking", "review:feedback-loops", "review:emergence"],
    "./agents/review/fd-decisions.md": ["review:decisions", "review:cognitive-bias", "review:strategy"],
    "./agents/review/fd-people.md": ["review:trust", "review:communication", "review:team-dynamics"],
    "./agents/review/fd-resilience.md": ["review:resilience", "review:antifragility", "review:innovation"],
    "./agents/review/fd-perception.md": ["review:mental-models", "review:sensemaking", "review:information-quality"],
    "./agents/research/framework-docs-researcher.md": ["research:docs", "research:frameworks"],
    "./agents/research/repo-research-analyst.md": ["research:codebase", "research:architecture"],
    "./agents/research/git-history-analyzer.md": ["research:git-history", "research:code-evolution"],
    "./agents/research/learnings-researcher.md": ["research:learnings", "research:institutional-knowledge"],
    "./agents/research/best-practices-researcher.md": ["research:best-practices", "research:industry-standards"]
  }
}
```

**Step 2: Create capability file writer hook**

Create `interverse/interflux/hooks/write-capabilities.sh`:

```bash
#!/usr/bin/env bash
# Write per-agent capability files for interlock registration.
# Reads agentCapabilities from plugin.json, extracts caps for each agent,
# and writes to ~/.config/clavain/capabilities-<agent-name>.json
set -euo pipefail

PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
[[ -f "$PLUGIN_JSON" ]] || exit 0

CAPS_DIR="${HOME}/.config/clavain"
mkdir -p "$CAPS_DIR"

# Extract agent names from paths and write capability files
jq -r '.agentCapabilities // {} | to_entries[] | .key' "$PLUGIN_JSON" 2>/dev/null | while IFS= read -r agent_path; do
    # Derive agent name from path: ./agents/review/fd-architecture.md → fd-architecture
    agent_name=$(basename "$agent_path" .md)
    caps=$(jq -c --arg path "$agent_path" '.agentCapabilities[$path] // []' "$PLUGIN_JSON" 2>/dev/null)
    if [[ -n "$caps" ]] && [[ "$caps" != "null" ]] && [[ "$caps" != "[]" ]]; then
        echo "$caps" > "${CAPS_DIR}/capabilities-${agent_name}.json"
    fi
done
```

**Step 3: Register the hook in hooks.json**

In `interverse/interflux/.claude-plugin/hooks/hooks.json`, add a SessionStart hook entry for the capability writer. The hook should run the script:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/write-capabilities.sh"
      }
    ]
  }
}
```

If hooks.json already has a `SessionStart` array, append to it. If hooks.json doesn't exist at this path, check the actual hooks location and add there.

**Step 4: Validate plugin.json**

Run: `python3 -c "import json; d=json.load(open('interverse/interflux/.claude-plugin/plugin.json')); ac=d.get('agentCapabilities',{}); agents=d.get('agents',[]); print('agents:', len(agents), 'caps:', len(ac)); missing=[k for k in ac if k not in agents]; print('missing from agents:', missing or 'none')"`
Expected: `agents: 17 caps: 17` and `missing from agents: none`

**Step 5: Commit**

```bash
cd interverse/interflux && git add .claude-plugin/plugin.json hooks/write-capabilities.sh && git commit -m "feat: declare agent capabilities in plugin.json and write per-agent files"
```

---

### Task 5: End-to-end test — capability discovery

**Files:**
- Modify: `core/intermute/internal/http/handlers_agents_test.go` (add test to existing file)

**Design note:** This is an in-process test using `httptest.NewServer` and `InMemory` store, so it belongs in the existing test file, not a separate integration test file.

**Step 1: Add end-to-end test**

Add to `core/intermute/internal/http/handlers_agents_test.go`:

```go
func TestCapabilityDiscoveryEndToEnd(t *testing.T) {
	svc := NewService(storage.NewInMemory())
	srv := httptest.NewServer(NewRouter(svc, nil, nil))
	defer srv.Close()

	// Simulate registration with capabilities (as interlock-register.sh would)
	agents := []struct {
		name string
		caps []string
	}{
		{"fd-architecture", []string{"review:architecture", "review:code"}},
		{"fd-safety", []string{"review:safety", "review:security"}},
		{"repo-research-analyst", []string{"research:codebase", "research:architecture"}},
		{"agent-nocaps", nil},
	}

	for _, a := range agents {
		payload := map[string]any{
			"name":         a.name,
			"project":      "demarch",
			"capabilities": a.caps,
		}
		buf, _ := json.Marshal(payload)
		resp, err := http.Post(srv.URL+"/api/agents", "application/json", bytes.NewReader(buf))
		if err != nil {
			t.Fatalf("register %s failed: %v", a.name, err)
		}
		resp.Body.Close()
	}

	// Query by single capability — only fd-architecture has review:architecture
	// (repo-research-analyst has research:architecture — different domain prefix)
	resp, err := http.Get(srv.URL + "/api/agents?project=demarch&capability=review:architecture")
	if err != nil {
		t.Fatalf("query failed: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result listAgentsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("decode failed: %v", err)
	}
	if len(result.Agents) != 1 {
		t.Fatalf("expected 1 agent for review:architecture, got %d", len(result.Agents))
	}
	if result.Agents[0].Name != "fd-architecture" {
		t.Fatalf("expected fd-architecture, got %s", result.Agents[0].Name)
	}

	// Query by OR across domains
	resp2, err := http.Get(srv.URL + "/api/agents?project=demarch&capability=review:safety,research:codebase")
	if err != nil {
		t.Fatalf("query failed: %v", err)
	}
	defer resp2.Body.Close()
	if resp2.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d", resp2.StatusCode)
	}

	var result2 listAgentsResponse
	if err := json.NewDecoder(resp2.Body).Decode(&result2); err != nil {
		t.Fatalf("decode failed: %v", err)
	}
	if len(result2.Agents) != 2 {
		t.Fatalf("expected 2 agents for safety+codebase, got %d", len(result2.Agents))
	}

	// Verify capabilities are returned in the response
	for _, a := range result2.Agents {
		if len(a.Capabilities) == 0 {
			t.Errorf("agent %s has no capabilities in response", a.Name)
		}
	}
}
```

**Step 2: Run the test**

Run: `cd core/intermute && go test ./internal/http/ -run TestCapabilityDiscoveryEndToEnd -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `cd core/intermute && go test ./...`
Expected: ALL PASS

**Step 4: Commit**

```bash
cd core/intermute && git add internal/http/handlers_agents_test.go && git commit -m "test: add end-to-end capability discovery test"
```
