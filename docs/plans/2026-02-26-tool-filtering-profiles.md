# Plan: Tool Filtering Profiles for MCP Context Reduction

**Bead:** iv-moyco
**PRD:** [2026-02-26-tool-filtering-profiles.md](../prds/2026-02-26-tool-filtering-profiles.md)
**Date:** 2026-02-26

## Batch 1: Filter Package + Interlock (largest server)

### Step 1: Create `mcpfilter` package in Interlock

New file: `interverse/interlock/internal/mcpfilter/filter.go`

```go
package mcpfilter

import "os"

type Profile string
const (
    ProfileFull    Profile = "full"
    ProfileCore    Profile = "core"
    ProfileMinimal Profile = "minimal"
)

type Cluster string

// ReadProfile reads the tool profile from env vars.
// Priority: server-specific > global > default (full).
func ReadProfile(serverEnvKey string) Profile {
    if v := os.Getenv(serverEnvKey); v != "" {
        return parseProfile(v)
    }
    if v := os.Getenv("MCP_TOOL_PROFILE"); v != "" {
        return parseProfile(v)
    }
    return ProfileFull
}

func parseProfile(s string) Profile {
    switch Profile(s) {
    case ProfileFull, ProfileCore, ProfileMinimal:
        return Profile(s)
    default:
        return ProfileFull
    }
}

// Filter returns only the tools whose names pass the profile filter.
// toolClusters maps tool name → cluster. profileClusters maps profile → allowed clusters.
func Filter[T any](
    tools []T,
    getName func(T) string,
    profile Profile,
    toolClusters map[string]Cluster,
    profileClusters map[Profile][]Cluster,
) []T {
    if profile == ProfileFull {
        return tools
    }
    allowed := make(map[Cluster]bool)
    for _, c := range profileClusters[profile] {
        allowed[c] = true
    }
    var filtered []T
    for _, t := range tools {
        name := getName(t)
        if c, ok := toolClusters[name]; ok && allowed[c] {
            filtered = append(filtered, t)
        }
    }
    return filtered
}
```

### Step 2: Define Interlock clusters

New file: `interverse/interlock/internal/mcpfilter/clusters.go`

```go
package mcpfilter

const (
    ClusterFileOps     Cluster = "file_ops"
    ClusterMessaging   Cluster = "messaging"
    ClusterNegotiation Cluster = "negotiation"
    ClusterAgentMgmt   Cluster = "agent_mgmt"
    ClusterSession     Cluster = "session"
    ClusterGuard       Cluster = "guard"
)

// InterlockClusters maps each tool to its cluster.
var InterlockClusters = map[string]Cluster{
    "reserve_files":             ClusterFileOps,
    "release_files":             ClusterFileOps,
    "release_all":               ClusterFileOps,
    "check_conflicts":           ClusterFileOps,
    "my_reservations":           ClusterFileOps,
    "send_message":              ClusterMessaging,
    "broadcast_message":         ClusterMessaging,
    "fetch_inbox":               ClusterMessaging,
    "fetch_stale_acks":          ClusterMessaging,
    "list_topic_messages":       ClusterMessaging,
    "request_release":           ClusterNegotiation,
    "negotiate_release":         ClusterNegotiation,
    "respond_to_release":        ClusterNegotiation,
    "force_release_negotiation": ClusterNegotiation,
    "list_agents":               ClusterAgentMgmt,
    "set_contact_policy":        ClusterAgentMgmt,
    "get_contact_policy":        ClusterAgentMgmt,
    "list_window_identities":    ClusterSession,
    "rename_window":             ClusterSession,
    "expire_window":             ClusterSession,
}

// InterlockProfiles defines which clusters are included in each profile.
var InterlockProfiles = map[Profile][]Cluster{
    ProfileCore:    {ClusterFileOps, ClusterMessaging, ClusterAgentMgmt},
    ProfileMinimal: {ClusterFileOps, ClusterMessaging},
}
// Note: ProfileFull handled by short-circuit in Filter(), no entry needed.
// Minimal: reserve_files, release_files, release_all, check_conflicts, my_reservations,
//          send_message, broadcast_message, fetch_inbox, fetch_stale_acks, list_topic_messages = 10 tools
```

### Step 3: Wire filtering into RegisterAll

Modify: `interverse/interlock/internal/tools/tools.go`

In `RegisterAll()`, after building the `[]server.ServerTool` slice, apply the filter before calling `s.AddTools()`:

```go
import "github.com/mistakeknot/interlock/internal/mcpfilter"

func RegisterAll(s *server.MCPServer, c *client.Client) {
    profile := mcpfilter.ReadProfile("INTERLOCK_TOOL_PROFILE")

    allTools := []server.ServerTool{
        reserveFiles(c),
        releaseFiles(c),
        // ... all 20 tools ...
    }

    filtered := mcpfilter.Filter(allTools, func(t server.ServerTool) string {
        return t.Tool.Name
    }, profile, mcpfilter.InterlockClusters, mcpfilter.InterlockProfiles)

    s.AddTools(filtered...)
}
```

### Step 4: Tests

New file: `interverse/interlock/internal/mcpfilter/filter_test.go`

- Test `ReadProfile()` with various env var combinations
- Test `Filter()` with full/core/minimal profiles
- Test that unknown profile defaults to full
- Test that tool names not in cluster map are excluded from non-full profiles

## Batch 2: Intermux + Intermap

### Step 5: Copy mcpfilter to Intermux

Copy the `mcpfilter` package pattern to Intermux, define its clusters:

New files:
- `interverse/intermux/internal/mcpfilter/filter.go` (same as Interlock's)
- `interverse/intermux/internal/mcpfilter/clusters.go`

Intermux clusters (7 tools):
```
ClusterMonitoring: activity_feed, agent_health, session_info
ClusterInspection: peek_agent, search_output, who_is_editing
ClusterDiscovery:  list_agents
```

Profiles:
- core: monitoring + inspection + discovery (all 7 — intermux is already small)
- minimal: list_agents, session_info, agent_health (3 tools: discovery + monitoring essentials)

Modify: `interverse/intermux/internal/tools/tools.go` — same wiring pattern as Interlock.

### Step 6: Copy mcpfilter to Intermap

Copy the `mcpfilter` package pattern to Intermap, define its clusters:

New files:
- `interverse/intermap/internal/mcpfilter/filter.go` (same as Interlock's)
- `interverse/intermap/internal/mcpfilter/clusters.go`

Intermap clusters (9 tools):
```
ClusterStructure:  code_structure, project_registry, resolve_project
ClusterAnalysis:   impact_analysis, change_impact, detect_patterns
ClusterNavigation: cross_project_deps, agent_map, live_changes
```

Profiles:
- core: structure + analysis (6 tools)
- minimal: project_registry, code_structure, impact_analysis (3 tools)

Modify: `interverse/intermap/internal/tools/tools.go` — same wiring pattern, but note that `RegisterAll` also returns a Python bridge. The bridge lifecycle is independent of filtering — all Python-backed tools still create the bridge, but only exposed ones are registered.

## Build & Test

```bash
# Each server independently
cd interverse/interlock && go build ./cmd/... && go test -race ./...
cd interverse/intermux && go build ./cmd/... && go test -race ./...
cd interverse/intermap && go build ./cmd/... && go test -race ./...
```

## Estimated Size

~350 lines across 3 servers (filter.go ~50 lines + clusters.go ~40 lines + test ~60 lines + wiring ~10 lines, x3).

## Summary Table

| Profile | Interlock (20) | Intermux (7) | Intermap (9) | Total (36) |
|---------|---------------|-------------|-------------|-----------|
| full | 20 | 7 | 9 | 36 |
| core | 13 | 7 | 6 | 26 (-28%) |
| minimal | 10 | 3 | 3 | 16 (-56%) |

At ~200 tokens/tool, minimal saves ~4,000 tokens per session loading these 3 servers.
