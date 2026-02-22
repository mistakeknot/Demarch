# Intermap Module 1: Go MCP Scaffold Build Report

**Date:** 2026-02-16
**Module:** intermap -- project-level code mapping MCP server
**Location:** `/root/projects/Interverse/plugins/intermap/`

## Summary

Module 1 of the intermap plugin has been successfully scaffolded as a Go MCP server following the interlock pattern. The scaffold includes a project registry with workspace scanning, project resolution, language detection, git branch tracking, an mtime-based LRU cache, and an agent overlay tool that integrates with intermute. All 18 tests pass and the MCP server responds correctly to `tools/list` requests, exposing 3 tools.

## Files Created

### Directory Structure

```
plugins/intermap/
  .claude-plugin/plugin.json     # Plugin manifest with MCP server config
  .gitignore                     # Ignore compiled binaries
  bin/
    .gitkeep
    launch-mcp.sh                # Auto-build launcher (executable)
  cmd/intermap-mcp/
    main.go                      # MCP server entry point (with intermute client)
  go.mod                         # Go module (github.com/mistakeknot/intermap)
  go.sum                         # Dependency checksums
  internal/
    cache/
      cache.go                   # Generic mtime-based LRU cache
      cache_test.go              # 5 cache tests
    client/
      client.go                  # Intermute HTTP client
      client_test.go             # 6 client tests
    registry/
      registry.go                # Project scanner + resolver
      registry_test.go           # 5 registry tests
    tools/
      tools.go                   # MCP tool registration (3 tools)
      tools_test.go              # 2 helper tests
  python/                        # Python components (pre-existing skeleton)
```

### Task 1.1: Infrastructure

**`go.mod`** -- Go 1.23.0 module with `github.com/mark3labs/mcp-go v0.43.2` dependency (matching interlock exactly). `go mod tidy` resolved 9 indirect dependencies.

**`bin/launch-mcp.sh`** -- Executable launcher that auto-builds the binary if missing, following the interlock pattern. Outputs JSON error to stderr if Go is not installed.

**`.claude-plugin/plugin.json`** -- MCP server plugin manifest declaring stdio transport, INTERMUTE_URL env var for intermute integration, and PYTHONPATH for the python subdirectory.

### Task 1.2: Project Registry (`internal/registry/registry.go`)

Core functionality:

- **`Scan(root string) ([]Project, error)`** -- Two-level directory walk: scans `root/<group>/<project>` looking for `.git` directories. Also checks if root itself is a project. Returns projects sorted by group then name.
- **`Resolve(path string) (*Project, error)`** -- Walks up from any file path to find the nearest `.git` directory. Detects group from parent directory name.
- **`MtimeHash(projectPath string) (string, error)`** -- SHA-256 hash of all source file modification times for cache invalidation. Skips hidden dirs, vendor, node_modules, __pycache__, venv.
- **`detectLanguage(projectPath string)`** -- Checks for marker files (go.mod, pyproject.toml, package.json, Cargo.toml, etc.) to identify project language.
- **`readGitBranch(gitDir string)`** -- Reads `.git/HEAD` to extract branch name or short detached hash.

The `Project` struct carries: Name, Path, Language, Group, GitBranch.

### Task 1.3: Cache (`internal/cache/cache.go`)

Generic `Cache[T any]` with:
- Mtime-hash-based invalidation (cache miss if hash changes)
- TTL expiry (configurable duration)
- LRU eviction when at capacity
- Thread-safe via `sync.Mutex`

### Task 1.4: MCP Server

**`cmd/intermap-mcp/main.go`** -- Creates an MCP server named "intermap" v0.1.0 with tool capabilities, initializes intermute client from INTERMUTE_URL env var, registers all tools, serves via stdio.

**`internal/tools/tools.go`** -- Registers three MCP tools:

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `project_registry` | Scan workspace and list all projects with language, group, git branch | None (root defaults to CWD) |
| `resolve_project` | Find which project a file path belongs to | `path` (required) |
| `agent_map` | Show which agents are working on which projects and files (combines registry + intermute agents + reservations) | None (root defaults to CWD) |

All tools return JSON-encoded results. `project_registry` uses the mtime-based cache with 5-minute TTL and supports a `refresh` boolean to force cache bypass. `agent_map` gracefully degrades when intermute is unavailable, returning project count with an error message.

### Task 1.5: Tests

**Registry tests** (5 tests in `internal/registry/registry_test.go`):
- `TestScan_Interverse` -- Scans actual Interverse monorepo, verifies interlock and clavain are found
- `TestScan_LanguageDetection` -- Verifies interlock and intermute detected as Go
- `TestResolve` -- Resolves a deep file path to the interlock project
- `TestResolve_NotInProject` -- Verifies error for `/tmp`
- `TestMtimeHash` -- Verifies deterministic hash and stability across calls

**Cache tests** (5 tests in `internal/cache/cache_test.go`):
- `TestCache_GetPut` -- Basic put/get cycle
- `TestCache_MtimeInvalidation` -- Different mtime hash causes miss
- `TestCache_TTLExpiry` -- Entry expires after TTL (50ms)
- `TestCache_LRUEviction` -- Capacity=2, verifies LRU entry is evicted
- `TestCache_Invalidate` -- Manual invalidation

**Client tests** (6 tests in `internal/client/client_test.go`):
- `TestListAgents`, `TestListReservations`, `TestClient_Unavailable`, `TestClient_ServerDown`, `TestListReservations_WithProject`, `TestListAgents_HTTPError`

**Tools tests** (2 tests in `internal/tools/tools_test.go`):
- `TestStringOr` -- String helper default behavior
- `TestStringOr_NonStringTypes` -- Non-string type handling

## Build & Test Results

### Build
```
$ go build -o bin/intermap-mcp ./cmd/intermap-mcp/
BUILD OK
```

### Tests
```
ok  github.com/mistakeknot/intermap/internal/cache     0.062s   (5 tests)
ok  github.com/mistakeknot/intermap/internal/client    0.007s   (6 tests)
ok  github.com/mistakeknot/intermap/internal/registry  0.009s   (5 tests)
ok  github.com/mistakeknot/intermap/internal/tools     0.004s   (2 tests)
```

All 18 tests PASS.

### MCP Tool Listing
```
$ echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ./bin/launch-mcp.sh

Tools:
  - agent_map: Show which agents are working on which projects and files.
  - project_registry: Scan workspace and list all projects with their language, group, and git branch.
  - resolve_project: Find which project a file path belongs to by walking up to the nearest .git directory.
```

Server responds correctly with protocol version `2024-11-05`, tool capabilities enabled.

## Design Decisions

1. **Follows interlock pattern exactly** -- Same go.mod structure, same mcp-go version, same launch-mcp.sh pattern, same cmd/internal layout.

2. **Intermute client integration** -- `main.go` initializes a `client.Client` from `INTERMUTE_URL` and passes it to `tools.RegisterAll`. The `agent_map` tool uses this to fetch agent and reservation data. When intermute is unavailable, it degrades gracefully returning just the project count.

3. **Two-level scan depth** -- `Scan()` looks for `root/<group>/<project>/.git` matching the Interverse monorepo structure (`plugins/interlock`, `services/intermute`, `os/clavain`). Also checks if root itself is a git project.

4. **Mtime-hash cache** -- Rather than re-scanning on every call, the cache stores results keyed by root path. The `MtimeHash` function provides source-file-aware invalidation for future use by more expensive operations (call graphs, architecture analysis).

5. **Agent overlay pattern** -- The `agent_map` tool combines three data sources (filesystem scan, intermute agents, intermute reservations) into a unified view showing which agents are working on which projects and files.

## Next Steps (Module 2+)

- Add call graph analysis tools (likely via tree-sitter or Go AST parsing)
- Add architecture analysis (dependency graphs between projects)
- Add `project_structure` tool for file tree summaries
- Register in Interverse marketplace
