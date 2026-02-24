# PRD: Intermap — Project-Level Code Mapping

**Bead:** iv-w7bh
**Date:** 2026-02-23

## Problem

Agents operating in a monorepo need spatial awareness — not just what's in a single file, but how projects relate, what architectural patterns exist, and what's changing right now. Intermap v0.1.3 has working MCP tools but carries extraction debt from tldr-swinton, has untested accuracy, and lacks cross-project and live-change capabilities.

## Solution

Audit the existing 6 tools, complete the tldr-swinton extraction, then add three new capabilities: cross-project dependency graphs, architecture pattern detection, and live change awareness. This makes Intermap the comprehensive spatial awareness layer for multi-agent development.

## Features

### F1: Audit existing MCP tools
**What:** Run every MCP tool against real Demarch projects and evaluate accuracy, performance, and integration ergonomics.
**Acceptance criteria:**
- [ ] Each of the 6 tools tested against at least 3 real Demarch projects (Go, Python, mixed)
- [ ] Accuracy report: call graphs verified against manual inspection, false positives/negatives documented
- [ ] Performance benchmarks: response time per tool, memory usage, cache hit rates
- [ ] Integration gaps documented: what's missing for interflux, Clavain, and other consumers
- [ ] Bug list with severity from audit findings

### F2: Close already-done beads
**What:** Verify and close iv-728k (Go MCP scaffold) and iv-h3jl (project registry + path resolver) which have working code but unclosed beads.
**Acceptance criteria:**
- [ ] iv-728k verified: Go MCP server builds, serves tools, handles MCP protocol correctly
- [ ] iv-h3jl verified: project_registry scans workspace, resolve_project maps paths correctly
- [ ] Both beads closed with verification notes

### F3: Extract Python modules from tldr-swinton
**What:** Move vendored Python analysis code into proper intermap-owned modules with clean import paths. Corresponds to existing bead iv-vwj3.
**Acceptance criteria:**
- [ ] `python/intermap/vendor/` directory eliminated
- [ ] All Python modules use `intermap.*` import paths (not `tldr_swinton.*`)
- [ ] Python tests pass with new import structure
- [ ] Go bridge updated to call intermap modules directly
- [ ] No functional regressions — all 6 tools return identical output before/after

### F4: Remove moved tools from tldr-swinton
**What:** Delete the project-level tools from tldr-swinton that are now in intermap. Corresponds to existing bead iv-mif9.
**Acceptance criteria:**
- [ ] `code_structure`, `impact_analysis`, `change_impact` removed from tldr-swinton MCP server
- [ ] tldr-swinton tests updated to reflect removal
- [ ] tldr-swinton plugin.json updated (tool count, description)
- [ ] No other plugin references the removed tldr-swinton tools
- [ ] Version bump on tldr-swinton

### F5: Write real vision and roadmap docs
**What:** Replace stub vision and roadmap docs with real content reflecting the audit results and new capability direction.
**Acceptance criteria:**
- [ ] `docs/intermap-vision.md` written with design principles, architecture overview, frontier axes
- [ ] `docs/intermap-roadmap.md` written with now/next/later structure
- [ ] `docs/roadmap.json` generated for interpath aggregation

### F6: Cross-project dependency graph
**What:** New MCP tool that maps how monorepo projects depend on each other — import chains, shared types, API contracts between projects.
**Acceptance criteria:**
- [ ] New `cross_project_deps` MCP tool registered
- [ ] Detects Go module dependencies (`go.mod` replace directives, import paths)
- [ ] Detects Python dependencies (path dependencies in `pyproject.toml`, relative imports)
- [ ] Detects plugin dependencies (MCP server references, skill invocations)
- [ ] Returns structured JSON: `{project: string, depends_on: [{project, type, via}]}`
- [ ] Tested against Demarch monorepo — correctly identifies interlock→intermute, interject→intersearch, etc.

### F7: Architecture pattern detection
**What:** New MCP tool that identifies and labels structural patterns in a project — layers, boundaries, handler chains, MCP registrations.
**Acceptance criteria:**
- [ ] New `detect_patterns` MCP tool registered
- [ ] Detects Go patterns: handler chains, middleware stacks, interface-implementation pairs, MCP tool registrations
- [ ] Detects Python patterns: FastMCP server patterns, CLI command groups, plugin skill structures
- [ ] Detects cross-language patterns: MCP server ↔ plugin manifest alignment, Go↔Python bridge interfaces
- [ ] Returns structured JSON: `{patterns: [{type, location, confidence, description}]}`
- [ ] At least 5 pattern types detected across Demarch projects

### F8: Live change awareness
**What:** New MCP tool that reports what has changed since a baseline (git diff based), with structural annotation of which functions/classes were affected.
**Acceptance criteria:**
- [ ] New `live_changes` MCP tool registered
- [ ] Uses `git diff` against configurable baseline (HEAD, branch, commit SHA)
- [ ] Annotates changes with structural context (which function was modified, not just line numbers)
- [ ] Integrates with existing mtime cache — changed files invalidate cache entries
- [ ] Returns structured JSON: `{changes: [{file, hunks: [{old_start, new_start, symbols_affected}]}]}`
- [ ] Sub-second response time for typical working tree diffs

## Non-goals

- Rewriting the Go MCP server or Python analysis engine architecture
- Supporting languages beyond Go and Python in this iteration
- Building a persistent database of code structure (keep it stateless, cache-only)
- Creating a web UI or dashboard — MCP tools only
- Real-time filesystem watching (git-diff based, not inotify)

## Dependencies

- intermute running for agent_map overlay (graceful degradation if unavailable)
- tldr-swinton source access for extraction comparison
- Go 1.22+ and Python 3.11+ build environments
- mark3labs/mcp-go SDK for new tool registration

## Open Questions

- **Vendoring strategy:** Extract to proper pip package or keep as local modules? Leaning local for simplicity.
- **Cache invalidation for cross-project:** Git hooks vs. mtime polling? Git hooks are more reliable but require per-project setup.
- **Pattern detection confidence:** How to score pattern confidence without training data? Heuristic thresholds initially, calibrate from audit.
