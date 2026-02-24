# Intermap: Project-Level Code Mapping

**Bead:** iv-w7bh
**Phase:** brainstorm (as of 2026-02-23T21:30:09Z)
**Date:** 2026-02-23
**Status:** Brainstorming

## What We're Building

A comprehensive project-level code mapping system that gives agents structural understanding of codebases — not just files and functions, but how projects relate to each other, what architectural patterns are in play, and what's changing right now. Intermap is the spatial awareness layer for multi-agent software development.

## Current State

Intermap v0.1.3 already exists as a Go MCP server with 6 tools:

| Tool | Status | Source |
|------|--------|--------|
| project_registry | Working | Go |
| resolve_project | Working | Go |
| agent_map | Working | Go + intermute |
| code_structure | Working | Python bridge |
| impact_analysis | Working | Python bridge |
| change_impact | Working | Python bridge |

Architecture: Go MCP server (mark3labs/mcp-go) + Python analysis layer (vendored from tldr-swinton) communicating via JSON-over-stdio subprocess calls.

Child beads:
- iv-728k (F1: Go MCP scaffold) — code exists, bead unclosed
- iv-vwj3 (F2: Extract Python modules) — open, needs work
- iv-mif9 (F3: Remove moved tools from tldr-swinton) — open, needs work
- iv-h3jl (F4: Project registry + path resolver) — code exists, bead unclosed

## Why This Approach

### Phase 1: Audit (understand before changing)

Run every MCP tool against real Demarch projects. Evaluate:

1. **Accuracy & completeness** — Are call graphs correct? Does impact_analysis catch real dependencies? Is code_structure missing important symbols?
2. **Performance & reliability** — Go→Python subprocess latency, caching effectiveness, failure modes, timeout handling.
3. **Integration gaps** — Can interflux consume intermap data? Can Clavain's sprint workflow use it? Is the MCP interface ergonomic for agents?

The audit tells us what to fix in extraction and what new capability matters most.

### Phase 2: Complete extraction + cleanup

- Close already-done beads (iv-728k, iv-h3jl) with proper verification
- Finish Python module extraction from tldr-swinton (iv-vwj3)
- Remove moved tools from tldr-swinton (iv-mif9) — clean break
- Write real vision and roadmap docs (currently stubs)
- Fix any accuracy/reliability issues found in audit

### Phase 3: New capabilities (audit-informed priority)

Three new capabilities, ordered by expected impact:

**A. Cross-project dependency graph**
Map how monorepo projects depend on each other — import chains, shared types, API contracts. Essential for multi-project impact analysis. This is the natural extension of the existing single-project impact_analysis tool.

**B. Architecture pattern detection**
Detect and label structural patterns (MVC layers, plugin boundaries, handler chains, MCP tool registrations). Agents need to understand design intent, not just code topology. This feeds into interflux review quality — reviewers that understand architecture give better feedback.

**C. Live change awareness**
Track file modifications via git diff and update the code map continuously. Currently intermap returns static snapshots; live awareness means agents always see current state. This integrates with the existing mtime cache in the Go bridge.

## Key Decisions

1. **Audit before touching code** — Don't fix what isn't broken. Let real usage data drive priorities.
2. **Clean extraction before new features** — Technical debt in the tldr-swinton vendoring will complicate every new feature. Clear it first.
3. **All three new capabilities** — Scoped as sequential work within the epic, not separate sprints.
4. **Go stays as MCP host, Python stays as analysis engine** — The current architecture works. Don't rewrite.
5. **Cross-project deps first** — Most likely highest audit-revealed impact. Pattern detection and live awareness build on top.

## Open Questions

- **Vendoring strategy:** Should extracted Python modules become a proper pip package, or stay vendored? Vendoring is simpler but harder to share with other plugins.
- **Agent_map scope:** Currently uses intermute for agent overlay. Should it also track non-intermute agent activity (e.g., tmux sessions via intermux)?
- **Cache invalidation:** The mtime cache works for single files. Cross-project deps need a different invalidation strategy — git hooks? Filesystem watches? Polling?
- **Pattern detection approach:** AST-based pattern matching vs. heuristic-based detection? AST is more accurate but language-specific; heuristics generalize better.

## Success Criteria

- All 6 existing tools pass accuracy audit against real Demarch projects
- tldr-swinton extraction complete — no vendored files, clean import paths
- Cross-project dependency graph covers the Demarch monorepo
- At least one interflux review agent consumes intermap data
- Vision and roadmap docs written (replacing stubs)
