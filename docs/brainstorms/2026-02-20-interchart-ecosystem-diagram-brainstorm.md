# Interchart: Interactive Ecosystem Diagram Plugin
**Bead:** iv-fgde

## What We're Building

A Claude Code plugin that generates and maintains an interactive HTML diagram showing how all Interverse components relate to each other — plugins, skills, services, Clavain hub, Intercore kernel, Autarch TUI, and the Interverse monorepo itself.

The diagram is a D3.js force-directed graph where:
- **Nodes** represent plugins, skills, MCP servers, services, and major components
- **Edges** represent dependencies (plugin→skill, skill→MCP tool, hook→event, etc.)
- **Interaction** allows zoom, pan, click-to-expand, and filtering by component type

### Primary use cases (layered)
1. **Onboarding / overview** — new contributors and AI agents understand how the ecosystem fits together
2. **Planning tool** — during brainstorm/strategy, explore what exists, identify gaps, plan new modules
3. **Live dashboard** (future) — show runtime state overlaid on the structural map

## Why This Approach

### Static scanning for data gathering
- Parse `plugin.json`, skills directories, `CLAUDE.md`, `hooks.json` from each plugin/module
- Rebuild on demand via a skill/command (`/interchart` or `interchart generate`)
- No runtime dependencies — works offline, deterministic, easy to debug
- Future: optional MCP overlay for live state (which agents are running, tool call frequency)

### D3.js force graph for visualization
- Battle-tested for interactive network diagrams
- Force-directed layout naturally clusters related components
- Supports zoom, pan, click-to-expand detail panels
- Can handle 30+ plugins × 100+ skills without performance issues
- Self-contained HTML file — no server needed, can be opened in any browser

### Alternatives considered
- **Mermaid + static HTML**: Simpler to generate but limited interactivity and layout control. Good for README diagrams, not for exploration.
- **Cytoscape.js**: Purpose-built for graphs but heavier. Overkill for this use case; D3 is more flexible for adding non-graph UI elements (filters, legends, detail panels).
- **MCP-based live query**: Interchart querying other MCP servers for live data. More complex, fragile, and not needed for MVP. Better as a future overlay layer.

## Key Decisions

1. **Plugin, not service** — interchart is a Claude Code plugin (like intermap), not a standalone service. It generates static HTML files.
2. **Static scanning** — reads plugin.json, hooks.json, skills dirs, CLAUDE.md files to discover relationships. No runtime dependencies.
3. **D3.js force graph** — interactive force-directed layout with zoom/pan/click.
4. **Self-contained HTML** — single HTML file with embedded data + D3.js. Can be committed, served, or opened locally.
5. **Scan scope** — covers the full Interverse: 31 plugins, Clavain hub (15+ skills), Intercore kernel, Autarch TUI, services (intermute), SDK (interbase).
6. **Node types**: plugin, skill, mcp-tool, hook-event, service, hub, kernel, tui
7. **Edge types**: provides-skill, uses-mcp-tool, fires-hook, depends-on, extends

## What Interchart Scans

| Source | What it extracts |
|--------|-----------------|
| `plugins/*/plugin.json` | Plugin name, version, skills list, MCP server config, hooks |
| `plugins/*/skills/` | Skill names and descriptions (from SKILL.md frontmatter) |
| `plugins/*/hooks/hooks.json` | Hook events and their handlers |
| `os/clavain/` | Clavain skills, dispatch targets, command definitions |
| `infra/intercore/` | Kernel capabilities (phases, gates, runs, dispatches) |
| `services/intermute/` | Multi-agent coordination service |
| `sdk/interbase/` | Shared SDK functions |
| Project CLAUDE.md files | Architecture descriptions, module relationships |

## Open Questions

1. **Output location** — `docs/diagrams/ecosystem.html`? Or `plugins/interchart/output/`? Probably docs/ since it's a project-level artifact.
2. **Update trigger** — manual (`/interchart generate`) only, or also auto-generate on plugin changes via a hook?
3. **Detail panels** — when you click a node, how much detail to show? Just name+description, or full skill lists and tool inventories?
4. **Grouping** — should plugins be visually grouped by category (review, coordination, analysis, etc.)? Force layout may cluster naturally by connectivity.
5. **Diff mode** — highlight what changed since last generation? Useful for seeing new plugins/skills at a glance.

## Scope for MVP

- Scanner that reads all plugin.json + skills + hooks
- D3.js force graph with node types color-coded
- Click-to-expand showing skills and MCP tools for each plugin
- Filter by node type (plugins only, skills only, etc.)
- Single self-contained HTML file output
- `/interchart` skill to trigger generation
