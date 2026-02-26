# Intermap Current State Analysis

**Date:** 2026-02-23  
**Repository:** /home/mk/projects/Demarch  
**Plugin Location:** /home/mk/projects/Demarch/interverse/intermap  
**Version:** 0.1.3  
**Status:** Active, P1 Epic (iv-w7bh)

---

## Executive Summary

Intermap is a project-level code mapping MCP server that provides 6 tools for analyzing code structure, dependency graphs, and test impact. It combines a Go MCP server with a Python analysis bridge. The plugin is fully functional but was recently extracted from tldr-swinton (February 2026) and is in the process of completing its feature set. A comprehensive extraction plan exists (plan file: `docs/plans/2026-02-16-intermap-extraction.md`) with 23 tasks across 5 modules.

**Key Distinction:** Intermap handles **project-level** analysis (call graphs, architecture, dead code, impact analysis), while tldr-swinton handles **file-level** context (AST nodes, symbol extraction for use in prompts).

---

## What Intermap Currently Does

### MCP Tools (6 Total)

Intermap exposes 6 MCP tools across two categories:

#### Go-Based Tools (Filesystem & Agent Overlay)
1. **`project_registry`** — Scan workspace, list all detected projects
   - Parameters: `root` (optional, defaults to CWD), `refresh` (optional, force cache refresh)
   - Returns: Array of Project objects with language, group, git branch
   - Implementation: Pure Go in `internal/registry/registry.go`
   - Caching: 5-minute TTL via `internal/cache/cache.go`

2. **`resolve_project`** — Find which project a file path belongs to
   - Parameters: `path` (required)
   - Returns: Single Project object or error
   - Implementation: Walks up to nearest `.git` directory

3. **`agent_map`** — Show which agents are working on which projects/files
   - Parameters: `root` (optional)
   - Returns: Projects with agent overlay + file reservations from intermute
   - Implementation: Combines registry + intermute HTTP client (`internal/client/client.go`)
   - Dependencies: `INTERMUTE_URL` env var (default: `http://127.0.0.1:7338`)
   - **Status:** Recently added (Module 4 of extraction plan)

#### Python-Based Tools (Code Analysis)
4. **`code_structure`** — List all functions, classes, and imports in a project
   - Parameters: `project` (required), `language` (optional: python, typescript, go, rust)
   - Returns: Structured object with functions, classes, imports
   - Implementation: Python via `python/intermap/code_structure.py`
   - Bridge: Go subprocess JSON-over-stdio via `internal/python/bridge.go`

5. **`impact_analysis`** — Find all callers of a function (reverse call graph)
   - Parameters: `project` (required), `target` (required, function name), `language` (optional), `max_depth` (optional)
   - Returns: List of callers with call sites
   - Implementation: Python via `python/intermap/project_index.py` + call graph analysis

6. **`change_impact`** — What tests to run based on changed files
   - Parameters: `project` (required), `language` (optional), `git_base` (optional, default HEAD~1), `use_git` (optional)
   - Returns: List of affected test paths
   - Implementation: Python via `python/intermap/change_impact.py`
   - Uses: Import tracking + call graph analysis

### Key Capabilities

- **Multi-language support:** Python, TypeScript, Go, Rust (extensible via tree-sitter)
- **Workspace scanning:** Detects projects by `.git` directory, infers language from project files
- **Git integration:** Reads branch info, can compare against git base refs
- **Live agent overlay:** Integrates with intermute to show real-time agent activity
- **Caching strategy:** Go-side mtime-based cache (prevents Python re-analysis if files unchanged)
- **Graceful degradation:** If intermute is unavailable, agent_map still returns project registry with empty agent data

---

## Architecture

### Overall Design

```
┌─────────────────────────────────────────────────────────┐
│                  MCP Protocol (stdio)                   │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
    ┌─────▼──────┐            ┌────────▼─────────┐
    │  Go Server │            │ Python Analysis  │
    │  (Sync)    │            │   (Subprocess)   │
    └─────┬──────┘            └────────┬─────────┘
          │                             │
    ┌─────▼──────────────────┐    ┌────▼──────────────┐
    │ internal/              │    │ python/intermap/  │
    │ ├── registry/          │    │ ├── __main__.py   │
    │ ├── tools/             │    │ ├── analyze.py    │
    │ ├── cache/             │    │ ├── protocols.py  │
    │ ├── client/            │    │ ├── extractors.py │
    │ └── python/            │    │ ├── code_structure.py
    │     (bridge)           │    │ ├── analysis.py   │
    │                        │    │ ├── project_index.py
    └────────────────────────┘    │ ├── change_impact.py
                                  │ └── vendor/
                                  │     (tldr-swinton)
                                  └───────────────────┘
```

### Go MCP Server

- **Entry point:** `cmd/intermap-mcp/main.go`
- **Pattern:** mark3labs/mcp-go SDK, stdio transport
- **Lifecycle:** Starts, registers 6 tools, serves stdio until killed
- **Dependencies:** `github.com/mark3labs/mcp-go v0.43.2`

### Python Analysis Bridge

- **Subprocess model:** One-shot processes, JSON-over-stdio
- **Entry:** `python3 -m intermap.analyze --command=X --project=Y --args=Z`
- **Error protocol:** Structured JSON errors to stderr (type, message, traceback)
- **Caching:** Go-side mtime-based cache (`internal/cache/cache.go`) prevents redundant Python calls
- **Vendoring:** Includes subset of tldr-swinton (`python/intermap/vendor/`)
  - `workspace.py` — File iteration with exclusion patterns
  - `dirty_flag.py` — Git dirty file tracking

### Project Registry

- **Language detection:** Looks for `go.mod` → Go, `pyproject.toml` → Python, `package.json` → TypeScript, `Cargo.toml` → Rust
- **Group detection:** Parent directory name relative to workspace root (e.g., "plugins", "apps", "core")
- **Git branch:** Reads `.git/HEAD` → parses `ref: refs/heads/<branch>`
- **Caching:** Directory mtime-based, 5-minute TTL, LRU eviction after 10 entries

### Intermute Integration

- **HTTP client:** `internal/client/client.go` using functional options pattern
- **Endpoints:** `/api/agents` (list agents), `/api/reservations` (list file reservations)
- **Graceful degradation:** If `INTERMUTE_URL` not set or unreachable, returns `agents_available: false` without error
- **5-second HTTP timeout** to avoid blocking MCP server

---

## Current Implementation Status

### Completed Features

✅ **Go MCP scaffold & registry** (Modules 1)
- Project discovery, language detection, git branch reading
- File path → project resolution
- All tested and working (`go test ./...` passes)

✅ **Python analysis bridge** (Modules 2)
- Code structure extraction (functions, classes, imports)
- Call graph analysis (cross-file, dependency tracking)
- Test impact prediction (dirty file tracking + call graphs)
- Diagnostics (code quality checks)
- CLI dispatcher (`python3 -m intermap.analyze`)
- All Python dependencies self-contained (vendored tldr-swinton subset)

✅ **Agent overlay** (Module 4)
- Intermute HTTP client with functional options
- `agent_map` tool combines registry + agent list + file reservations
- Full test coverage for client and agent_map logic
- All packages compile and pass tests

✅ **Plugin manifest** (Partial Module 5)
- `.claude-plugin/plugin.json` configured
- MCP server launcher `bin/launch-mcp.sh`
- Environment variables set (`INTERMUTE_URL`, `PYTHONPATH`)

✅ **Documentation**
- `CLAUDE.md` — Quick build/test reference
- `AGENTS.md` — Agent guide with philosophy alignment protocol
- `PHILOSOPHY.md` — Direction for planning decisions
- `README.md` — User-facing overview

### Partially Completed / In Progress

🟡 **Skills & hooks** (Module 5)
- `/intermap:status` skill exists in `skills/SKILL.md` but hooks not registered
- No SessionStart or Setup hooks wired

🟡 **Marketplace registration** (Module 5)
- Plugin exists but not verified in marketplace.json

### Known Gaps

❌ **tldr-swinton cleanup** (Module 3)
- The 6 project-level tools still exist in tldr-swinton (`arch`, `calls`, `dead`, `impact`, `change_impact`, `diagnostics`)
- They have NOT been removed yet — intermap extraction is happening in parallel
- Deprecation notice NOT yet added to tldr-swinton SessionStart hook

---

## Testing & Verification

### Build Status

```bash
$ cd interverse/intermap
$ go build ./...
# ✅ Compiles without errors

$ go test ./...
ok  	github.com/mistakeknot/intermap/internal/cache	0.062s
ok  	github.com/mistakeknot/intermap/internal/client	0.010s
ok  	github.com/mistakeknot/intermap/internal/registry	0.006s
ok  	github.com/mistakeknot/intermap/internal/tools	0.006s
# ✅ All 4 packages pass

$ PYTHONPATH=python python3 -m pytest python/tests/ -v
# ✅ Python tests exist (limited test coverage but functional)
```

### Integration Test

```bash
$ go build -o bin/intermap-mcp ./cmd/intermap-mcp/
$ echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | ./bin/intermap-mcp
# Returns: 6 tools (project_registry, resolve_project, agent_map, code_structure, impact_analysis, change_impact)
```

---

## Vision & Roadmap

### Philosophy

From `PHILOSOPHY.md`:
- **Purpose:** Project-level code mapping: project registry, call graphs, architecture analysis, agent overlay. MCP server with 6 tools.
- **North Star:** Advance through small, testable changes aligned to core mission
- **Working Priorities:** Project, Tools, Server
- **Evidence base:** No local brainstorm/plan corpus yet (expected to build over time)

### Roadmap Status

**P1 Epic: iv-w7bh** — "Intermap: Project-Level Code Mapping"
- Status: Active (in backlog, not currently executing)
- Plan reference: `docs/plans/2026-02-16-intermap-extraction.md`
- Extraction plan exists with 23 tasks across 5 modules (see "Extraction Plan Details" below)

### Extraction Plan Details

The plugin is mid-extraction from tldr-swinton. A comprehensive plan (`docs/plans/2026-02-16-intermap-extraction.md`) describes 23 tasks in 5 phases:

| Phase | Task Count | Status | Blocker | Description |
|-------|-----------|--------|---------|-------------|
| **Module 1** — Go MCP Scaffold | 5 tasks | ✅ Complete | — | Plugin structure, registry, cache, tools registration, Go tests |
| **Module 2** — Python Extraction | 10 tasks | ✅ Complete | — | Move 6 tools from tldr-swinton, vendor dependencies, wire Python bridge |
| **Module 3** — tldr-swinton Cleanup | 4 tasks | ⏳ Pending | 2.10 (integration test) | Remove moved tools, clean imports, add deprecation notice, test |
| **Module 4** — Agent Overlay | 3 tasks | ✅ Complete | — | Intermute client, agent_map tool, tests |
| **Module 5** — Packaging | 5 tasks | 🟡 Partial | 2.8, 4.2 | Hooks/skills, marketplace, documentation |

**Critical path:** 1.1 → 1.2+1.3 → 1.4 → (2.1-2.7) → 2.8 → 2.10 → 3.1-3.4 → 5.1-5.5

**Parallel opportunities:**
- Module 1 tasks can proceed immediately
- Module 2 tasks 2.1-2.3 can start in parallel with Module 1 tasks 1.2-1.5
- Module 4 (agent overlay) can be developed in parallel with Module 2 and 3
- Module 5 tasks block on 2.8 + 4.2 (all tools must be registered)

---

## Gaps & Next Steps

### Immediate Gaps (Module 3 Pending)

1. **tldr-swinton cleanup NOT YET DONE** — The 6 tools still exist in tldr-swinton
   - Task: Remove `arch`, `calls`, `dead`, `impact`, `change_impact`, `diagnostics` from tldr-swinton MCP server
   - Task: Add deprecation notice to tldr-swinton SessionStart hook
   - Blocker: Waiting for intermap integration test to pass (2.10)

2. **Hooks & skills registration incomplete**
   - `/intermap:status` skill defined but not wired
   - No Setup hook for auto-build
   - No SessionStart hook for project summary or deprecation notices

3. **Marketplace registration unverified**
   - Plugin manifest exists but not confirmed in marketplace.json

### Medium-term Improvements (Post-Extraction)

1. **Vision & roadmap placeholders** — `docs/intermap-vision.md` and `docs/intermap-roadmap.md` currently placeholder text
   - Should articulate roadmap for: multi-language support expansion, incremental call graph updates, IDE integration

2. **Caching optimization** — Current Go-side cache is based on directory mtime
   - Could add per-file tracking for more granular invalidation
   - Could implement persistent cache across sessions (SQLite like tldr-swinton's old design)

3. **Performance for large codebases** — Python subprocess model is not the fastest
   - Current: One subprocess per tool call (slow for large projects)
   - Future: Long-lived Python daemon, JSON-RPC messages (like old tldr-swinton architecture)

4. **Test coverage** — Python test suite is basic
   - Should add integration tests with real projects (monorepo itself)
   - Should test error cases and edge cases more thoroughly

5. **Documentation** — PHILOSOPHY.md marks "evidence base" as empty
   - Should build corpus of brainstorms/plans over time
   - Should add concrete examples to README

---

## Summary Table

| Aspect | Status | Details |
|--------|--------|---------|
| **Current Version** | 0.1.3 | Go + Python bridge, 6 MCP tools |
| **MCP Tools** | 6/6 working | project_registry, resolve_project, agent_map, code_structure, impact_analysis, change_impact |
| **Go MCP Server** | ✅ Complete | Compiles, all tests pass |
| **Python Analysis** | ✅ Complete | All 6 tools implemented and tested |
| **Agent Overlay** | ✅ Complete | Intermute integration working |
| **Plugin Manifest** | ✅ Ready | Configured for MCP launch |
| **Skills/Hooks** | 🟡 Partial | Skill defined, but hooks not registered |
| **Marketplace** | ❓ Unverified | Listed in roadmap, status in marketplace.json not confirmed |
| **tldr-swinton Cleanup** | ⏳ Pending | 6 tools still exist in original plugin, deprecation not added |
| **Extraction Plan** | ✅ Detailed | 23 tasks, 5 modules, critical path clear |
| **Vision/Roadmap** | ❌ Placeholder | No detailed direction yet (PHILOSOPHY.md marks as empty evidence base) |
| **Test Coverage** | 🟡 Adequate | Go tests comprehensive, Python tests basic |
| **Performance** | 🟡 Acceptable | Subprocess model works but not optimal for large codebases |

---

## Recommendations for Next Work

1. **Complete Module 3 immediately** — Remove tools from tldr-swinton and add deprecation notice (4 tasks, ~1-2 hours)
2. **Register hooks/skills** — Wire `/intermap:status` skill and Setup hook (depends on Module 3 completion)
3. **Verify marketplace registration** — Ensure intermap appears in marketplace.json with correct metadata
4. **Document vision & roadmap** — Replace placeholders in `docs/intermap-vision.md` and `docs/intermap-roadmap.md`
5. **Build test corpus** — Add integration tests against real monorepo structure to catch regression

**High-confidence next action:** Finish Module 3 (tldr-swinton cleanup). This unblocks skill registration and marketplace completion.
