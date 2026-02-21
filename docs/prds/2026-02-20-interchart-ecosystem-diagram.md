# PRD: Interchart — Interactive Ecosystem Diagram Plugin
**Bead:** iv-fgde

## Problem

The Interverse ecosystem has 31+ plugins, 50+ skills, multiple MCP servers, Clavain hub, Intercore kernel, Autarch TUI, and supporting services. There's no visual way to understand how these components relate to each other — onboarding requires reading dozens of CLAUDE.md files, and planning new modules means mentally tracking which plugins depend on which.

## Solution

A Claude Code plugin (`interchart`) that scans the monorepo structure and generates a self-contained interactive HTML diagram using D3.js force-directed graph. Nodes represent components (plugins, skills, MCP tools, services), edges represent relationships (provides, depends-on, fires-hook). The diagram supports zoom, pan, click-to-expand detail panels, and filtering by component type.

## Features

### F1: Ecosystem Scanner
**What:** A Node.js/bash scanner that reads plugin.json, skills directories, hooks.json, and CLAUDE.md files across the entire Interverse monorepo and outputs a structured JSON graph.
**Acceptance criteria:**
- [ ] Scans all `plugins/*/plugin.json` and extracts: name, version, skills list, MCP server config, hooks
- [ ] Scans `plugins/*/skills/` and extracts skill names + descriptions from SKILL.md files
- [ ] Scans `plugins/*/hooks/hooks.json` and extracts hook events + handler types
- [ ] Includes Clavain hub (`hub/clavain/`) — skills, commands, dispatch targets
- [ ] Includes Intercore (`infra/intercore/`) — kernel capabilities
- [ ] Includes Autarch (`Interforge/` or external ref) — TUI component
- [ ] Includes services (`services/intermute/`) and SDK (`sdk/interbase/`)
- [ ] Outputs structured JSON with nodes (id, type, label, metadata) and edges (source, target, type)

### F2: D3.js Force Graph Visualization
**What:** An interactive force-directed graph rendered in a self-contained HTML file with embedded data and D3.js library.
**Acceptance criteria:**
- [ ] Renders nodes as circles with color-coding by type (plugin=blue, skill=green, mcp-tool=orange, etc.)
- [ ] Renders edges as lines with style by relationship type (solid=provides, dashed=depends-on)
- [ ] Force-directed layout naturally clusters related components
- [ ] Supports zoom (scroll wheel) and pan (drag background)
- [ ] Node labels visible, sized by importance (plugins larger than skills)
- [ ] Self-contained single HTML file — works offline, no external dependencies

### F3: Click-to-Expand Detail Panels
**What:** When clicking a node, a side panel shows detailed information about that component.
**Acceptance criteria:**
- [ ] Click any node to open a detail panel
- [ ] Panel shows: component name, type, description, version (if applicable)
- [ ] For plugins: lists all skills and MCP tools it provides
- [ ] For skills: shows which plugin provides it, description
- [ ] Panel can be closed by clicking elsewhere or an X button
- [ ] Highlight connected nodes/edges when a node is selected

### F4: Type Filters
**What:** Toolbar with toggle buttons to show/hide node types, enabling focused exploration.
**Acceptance criteria:**
- [ ] Filter bar at the top with toggles for each node type
- [ ] Toggling off a type hides those nodes and their edges
- [ ] Active filter state reflected in button styling
- [ ] "Show all" / "Hide all" convenience buttons
- [ ] Filter state persists during the session (not across page reloads)

### F5: Generation Skill
**What:** A `/interchart` skill that triggers the scanner, generates the HTML output, and reports the result.
**Acceptance criteria:**
- [ ] `/interchart` or `/interchart generate` scans and generates the diagram
- [ ] Outputs to `docs/diagrams/ecosystem.html` (or configurable path)
- [ ] Reports: number of nodes, number of edges, output file path
- [ ] Handles missing directories gracefully (warns but doesn't fail)

## Non-goals

- **Live runtime overlay** — no MCP queries for active agent state (future iteration)
- **Diff mode** — no change highlighting between generations (future)
- **Edit capabilities** — diagram is read-only, no drag-to-rearrange-and-save
- **Automatic regeneration** — no hooks to auto-rebuild on plugin changes (future)
- **External hosting** — no web server or deployment; local file only

## Dependencies

- D3.js v7 (embedded via CDN link or inlined in HTML)
- Node.js or bash for the scanner script
- Access to the Interverse monorepo file structure

## Open Questions

- Should the scanner be a Node.js script (richer JSON parsing) or pure bash (no dependencies)?
  **Resolution:** Node.js — plugin.json files are JSON, and generating the HTML template is cleaner in JS.
