# Interdoc Analysis: Demarch Root AGENTS.md

**Date:** 2026-02-25
**Target:** `/home/mk/projects/Demarch/AGENTS.md` (376 lines)
**Method:** Read current AGENTS.md + CLAUDE.md, explored all top-level and subproject directories, compared documented vs actual structure.

## Summary of Changes

The AGENTS.md was mostly accurate but had accumulated several gaps from recent plugin additions and structural changes. The rewrite adds 5 missing interverse plugins, 1 missing app, updates the plugin count from "33+" to 40, adds a missing operational guide reference, and documents previously-undocumented top-level directories. Final line count stays under 400.

## Gaps Identified

### 1. Missing Interverse Plugins (5 new plugins not in directory layout)

| Plugin | Description | Evidence |
|--------|-------------|----------|
| `intercache` | Cross-session semantic cache (MCP, Python) | Has CLAUDE.md, `.claude-plugin/`, 10 MCP tools |
| `interfin` | Expense tracker plugin companion (CLI at `apps/interfin/`) | Has CLAUDE.md, AGENTS.md, `.claude-plugin/` |
| `interpulse` | Session context pressure monitoring (hooks) | Has CLAUDE.md, `.claude-plugin/` |
| `interskill` | Unified skill authoring toolkit (skills: create, audit) | Has CLAUDE.md, `.claude-plugin/` |
| `intertrust` | Agent trust scoring engine (hooks, extracted from Interspect) | Has CLAUDE.md with full design doc |

### 2. Missing App

| App | Description | Evidence |
|-----|-------------|----------|
| `apps/interfin/` | Local business expense & receipt tracker CLI (Python) | Has `pyproject.toml`, `config/`, `data/`, `out/` |

### 3. Stale Plugin Count

- **CLAUDE.md** says "33+ Claude Code companion plugins"
- **AGENTS.md Overview** says "33+ companion plugins"
- **Actual count**: 40 directories in `interverse/`

### 4. Missing Top-Level Directory Documentation

These exist at the repo root but are not mentioned in AGENTS.md:

| Path | What It Is |
|------|-----------|
| `research/` | Gitignored clones of external repos for research (has own AGENTS.md) |
| `Interforge/` | Contains `docs/vision-feedback.md` -- appears to be early-stage/placeholder |
| `companion-graph.json` | Machine-readable plugin dependency graph (consumed by `/clavain:doctor`) |
| `CONVENTIONS.md` | Canonical documentation path conventions (referenced but not listed) |
| `GEMINI.md` | Gemini (Antigravity) context file for non-Claude agents |
| `install.sh` / `uninstall.sh` | Curl-fetchable installer/uninstaller for Demarch |

### 5. Missing Operational Guide Reference

The guide `docs/guides/interband-sideband-protocol.md` exists but is not listed in the Operational Guides table.

### 6. Module Relationships Section Gaps

The Module Relationships section doesn't mention:
- `intercache` (standalone MCP)
- `interfin` (standalone, companion to `apps/interfin/`)
- `interpulse` (standalone hooks)
- `interskill` (standalone skills)
- `intertrust` (used by interflux and clavain for trust scoring)

### 7. MCP Server List Incomplete

The "MCP server plugins" line in the testing section lists 10 servers but doesn't include `intercache`.

## Changes Made in Rewrite

1. **Directory Layout table**: Added `intercache`, `interfin`, `interpulse`, `interskill`, `intertrust` to interverse section. Added `apps/interfin/`. Added `research/` to the non-pillar rows.
2. **Overview**: Updated plugin count from "33+" to "40".
3. **Module Relationships**: Added the 5 new plugins to the relationship list.
4. **MCP server list**: Added `intercache` to the MCP server testing line.
5. **Operational Guides table**: Added `interband-sideband-protocol.md` entry.
6. **Prerequisites**: Added `intercache` to the `uv` row since it's a Python MCP server.
7. **Minor fixes**: Sorted the directory layout table entries within each section for easier scanning.

## Items NOT Changed (Intentional)

- **Interforge**: Too sparse (just a vision-feedback doc) to document as a real module. Left out.
- **`dev/` directory**: Empty, not worth documenting.
- **`companion-graph.json`**: Infrastructure artifact, not a module. Mentioned in CONVENTIONS.md reference already.
- **`GEMINI.md`**: This is a peer to CLAUDE.md for a different agent runtime; AGENTS.md is the unified guide and already covers what GEMINI.md needs.
- **`install.sh`/`uninstall.sh`**: Mentioned in Prerequisites/setup context but not given their own section -- appropriate for a root overview doc.
- **`apps/Intermute` symlink**: Already covered by the Compatibility section.
- **`structure.md`**: Historical planning document, not active documentation.
