---
name: interchart
description: "Interactive ecosystem diagram — scans Interverse monorepo and generates a D3.js force graph showing all plugins, skills, MCP tools, hooks, and their relationships."
---
# Gemini Skill: interchart

You have activated the interchart capability.

## Base Instructions
# interchart — AGENTS.md

Interactive ecosystem diagram generator for Interverse. Scans all plugins, skills, agents, MCP servers, hooks, and infrastructure nodes across the monorepo and produces a self-contained D3.js force graph.

**Live diagram:** https://mistakeknot.github.io/interchart/

## Architecture

```
scripts/scan.js          → Scans monorepo, outputs JSON graph (nodes + edges)
scripts/generate.sh      → Runs scanner → injects JSON into HTML template → writes output
templates/ecosystem.html → D3.js force graph template with /*DATA_PLACEHOLDER*/ marker
scripts/regenerate-and-deploy.sh  → Generate + deploy to gh-pages branch
scripts/watch-and-deploy.sh       → Cron wrapper — fingerprint-based change detection
```

### Pipeline

```
scan.js ─→ JSON ─→ generate.sh ─→ ecosystem.html
                        │
              template + data injection
                        │
              (/*DATA_PLACEHOLDER*/ → JSON blob)
```

The generated HTML is fully self-contained — the only external dependency is the D3.js v7 CDN script.

## File Layout

```
.claude-plugin/plugin.json    → Plugin manifest (name, version, skills)
scripts/
  scan.js                     → Node.js scanner (455 lines)
  generate.sh                 → Generate HTML from template + scanned data
  regenerate-and-deploy.sh    → Full pipeline: generate → compare → deploy to gh-pages
  watch-and-deploy.sh         → Cron-friendly: SHA fingerprint → regenerate if changed
templates/
  ecosystem.html              → D3.js visualization template (~850 lines)
skills/interchart/SKILL.md    → Claude Code skill for /interchart command
.last-scan-state              → SHA256 fingerprint of last cron run (gitignored)
```

## Scanner Data Model (scan.js)

### Node Types

| Type | Description | Size | Example |
|------|-------------|------|---------|
| `monorepo` | Interverse root | 24 | Interverse |
| `hub` | Clavain hub | 20 | clavain |
| `kernel` | Intercore kernel | 16 | intercore |
| `service` | Go services | 14 | intermute |
| `tui` | TUI frontends | 14 | autarch |
| `sdk` | Shared SDKs | 12 | interbase |
| `plugin` | Claude Code plugins | 12 | interflux |
| `mcp-server` | MCP servers | 7 | serena |
| `hook-event` | Hook event types | 7 | PostToolUse |
| `agent` | Plugin agents | 6 | fd-architecture |
| `skill` | Plugin skills | 6 | flux-drive |

### Edge Types

| Type | Meaning | Visual |
|------|---------|--------|
| `part-of` | Structural containment | Solid gray |
| `provides-skill` | Plugin → skill | Solid green |
| `provides-agent` | Plugin → agent | Solid orange |
| `provides-mcp` | Plugin → MCP server | Dashed purple |
| `fires-hook` | Plugin → hook event | Dotted red |
| `companion-of` | Plugin → hub companion | Dashed yellow |
| `depends-on` | Hard dependency | Dashed teal |
| `overlaps-with` | Functional overlap | Not rendered as edges (see Domains) |
| `participates-in` | Sprint phase → ecosystem plugin | Dashed cyan (injected dynamically) |

### Overlap / Domain System

Overlap edges are **not drawn as edges** — they're visualized as **convex hull domain overlays**. Each domain is a colored translucent polygon enclosing all plugins that share that capability area.

**How overlaps are computed** (in `computeOverlapEdges()`):

1. Each plugin/hub/kernel/service node gets its description text matched against `OVERLAP_DOMAIN_RULES` (regex patterns → domain names with weights)
2. `FORCED_OVERLAP_GROUPS` add curated groupings (e.g., analytics stack, doc lifecycle)
3. Two nodes overlap if they share 2+ domains OR score >= 2.4 OR belong to a forced group

**Current domains** (11): analytics-observability, analytics-quality-stack, coordination-dispatch, design-product, discovery-context-stack, discovery-research, doc-lifecycle-stack, docs-artifacts, phase-gate-control, phase-gates, quality-review

To add a domain: add a rule to `OVERLAP_DOMAIN_RULES` in `scan.js` or a group to `FORCED_OVERLAP_GROUPS`.

## Visualization (ecosystem.html)

### Toggle Architecture

The app uses a **unified force graph** with two independent toggle buttons in the toolbar:

| Toggle | Content | Default |
|--------|---------|---------|
| **Ecosystem** | D3.js force-directed graph of all Interverse modules | ON |
| **Sprint** | Sprint phase nodes pinned in horizontal arc + flow arrows | OFF |

Both toggles can be active simultaneously. When both are on, sprint phases become gravitational anchors in the force simulation — plugins cluster near the phases they participate in via `participates-in` edges.

**Toggle behavior** (`toggleLayer()`):
- Each button toggles independently (not mutually exclusive)
- Ecosystem ON/OFF: shows/hides ecosystem nodes, links, search box, sidebar toggle, stats
- Sprint ON/OFF: injects/removes sprint phase nodes and `participates-in` edges into the simulation, draws/removes flow arrows and gate diamonds
- `rebuildGraph()` removes old sprint data, re-injects if active, rebuilds D3 selections, restarts simulation
- Sprint phase filter section in sidebar appears when sprint is active

**Phase-to-plugin mapping** (`PHASE_PLUGINS`): Curated static mapping of which ecosystem nodes participate in each sprint phase. Creates `participates-in` force links when both toggles are active.

### UI Layout

- **Toolbar** (top, 44px): "Interverse" title, toggle bar (Ecosystem/Sprint), stats, search box
- **Sidebar toggle** (fixed position, top-left): Hamburger button to expand filter sidebar
- **Filter sidebar** (left, 240px, overlay): Type filters + domain hull toggles + sprint phase toggles (when sprint active). Starts collapsed.
- **Graph area** (center): Single D3.js force-directed SVG (full viewport)
- **Detail panel** (right, slides in): Shows node metadata for both ecosystem and sprint nodes

### Sprint Nodes in Force Graph

Sprint phase nodes are rendered as **rounded rectangles** (160×56px) in a separate SVG layer on top of the force graph. They are **pinned** (fixed `fx`/`fy`) in a horizontal arc:

```
Top row (steps 1-5):    [Brainstorm] [Strategize] [Write Plan] [Review Plan] [Execute]
Bottom row (steps 6-10): [Test] [Quality Gates] [Resolve] [Reflect] [Ship]
```

**Visual elements**:
- Rounded rect nodes with step number badge, label, phase name, and artifact hint
- Blue flow arrows between consecutive phases (decorative SVG layer, not force links)
- Dashed orange skip arc: Brainstorm → Write Plan for trivial tasks
- Gate diamonds on flow arrows: red = hard gate (blocking), orange = soft gate (advisory)
- Dashed teal `participates-in` edges from phase nodes to ecosystem plugins (force links)

**Phase colors**: ideation=#F39C12, planning=#3498DB, building=#2ECC71, quality=#E74C3C, learning=#9B59B6, shipping=#1ABC9C

**Sprint data**: `var SPRINT_PHASES` — 10-element array, each with `{id, step, label, phase, command, description, artifact, gate}`. Fully static — no scanning needed.

### Interactions

- **Click ecosystem node**: Highlight node + neighbors + connected sprint phases, dim everything else, open detail panel
- **Click sprint phase node**: Highlight phase + participating plugins + adjacent phases, open detail panel with command, artifact, gate info, and participating plugins list
- **Click background**: Deselect all, close panel
- **Search** (when ecosystem active): Filter + highlight matching nodes by name/ID
- **Type filters**: Show/hide node types (sidebar checkboxes)
- **Domain toggles**: Show/hide convex hull overlays per domain
- **Phase toggles** (when sprint active): Show/hide individual sprint phase nodes
- **Drag**: Reposition ecosystem nodes (sprint phases stay pinned)
- **Zoom/pan**: Mouse wheel + drag on background
- **Detail panel links**: Click to navigate to connected nodes; external links to GitHub repos

### Template Variable Ordering

The template uses inline `<script>` with `const`/`let` — these are NOT hoisted. Variables must be defined before first use. Current safe order:

```
1. TYPE_COLORS, TYPE_SIZES, TYPE_LABELS (constants)
2. activeFilters, selectedNode, searchQuery (state)
3. Build type filter buttons (reads TYPE_*)
4. graphNodes, graphLinks (from data — filters out overlaps-with)
5. domainMembers, DOMAIN_COLORS, DOMAIN_LABELS, activeDomains (domain extraction)
6. Stats line (reads domainNames.length)
7. Build domain toggle buttons (reads DOMAIN_*)
8. D3 setup, simulation, node/link rendering (linkGroup, nodeGroup_eco)
9. Hull computation (reads domainMembers, nodeById)
10. Interaction handlers (functions — hoisted)
11. SPRINT_PHASES, PHASE_COLORS, PHASE_PLUGINS (sprint data — uses var)
12. Toggle state, sprint layer groups, phase positions, phase filter buttons
13. Arrow markers (SVG defs)
14. toggleLayer(), rebuildGraph(), rebuildSimulation() (toggle logic)
15. Sprint rendering: renderSprintNodes(), drawSprintFlowArrows()
16. Sprint interactions: selectSprintNode(), showSprintDetail()
```

**Critical:** Moving code blocks out of this order will cause `ReferenceError` and a blank page with no visible error to the user.

**Sprint code safety:** All sprint code uses `var` and function declarations (hoisted) rather than `const`/`let`, and lives at the end of the `<script>` block to avoid ordering issues with the ecosystem code above it.

## Deployment

### Agent-driven (primary)

Agents regenerate the diagram as a final step after any change that adds, removes, or renames plugins, skills, agents, MCP servers, or hooks. This is documented in the Interverse root `AGENTS.md` under "Ecosystem Diagram (interchart)".

```bash
# Generate + deploy to gh-pages (safe — uses git worktree, never touches main)
bash scripts/regenerate-and-deploy.sh /root/projects/Interverse

# Generate only (no deploy)
bash scripts/generate.sh /root/projects/Interverse
```

### GitHub Pages

- Branch: `gh-pages`
- Files: `index.html` (generated diagram), `.nojekyll`
- URL: https://mistakeknot.github.io/interchart/

The `gh-pages` branch only contains the generated `index.html` — do NOT merge it into `main`.

## Adding New Components

### New plugin appears

The scanner auto-discovers plugins in `plugins/*/`. Just add the plugin with a `.claude-plugin/plugin.json` manifest and regenerate. Skills, agents, MCP servers, and hooks are all discovered from the manifest and `hooks/hooks.json`.

### New node type

1. Add scan logic in `scan.js` (create nodes with `addNode()`)
2. Add color to `TYPE_COLORS` in `templates/ecosystem.html`
3. Add size to `TYPE_SIZES`
4. Add label to `TYPE_LABELS`

### New edge type

1. Add creation logic in `scan.js` (create edges with `addEdge()`)
2. Add CSS class `.link.<type>` in the template `<style>` block

### New overlap domain

Add a rule to `OVERLAP_DOMAIN_RULES` in `scan.js`:
```js
{ domain: 'my-domain', weight: 1.0, patterns: [/\bkeyword\b/i] }
```

Or add a forced group to `FORCED_OVERLAP_GROUPS`:
```js
{ domain: 'my-stack', boost: 1.0, ids: ['plugin-a', 'plugin-b', 'plugin-c'] }
```

## Testing

No test framework — verify manually:

```bash
# Scanner produces valid JSON with expected counts
node scripts/scan.js /root/projects/Interverse 2>/dev/null | \
  node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{
    const j=JSON.parse(d);
    console.log('Nodes:', j.stats.nodes, 'Edges:', j.stats.edges, 'Overlaps:', j.stats.overlaps);
    console.log('Types:', Object.keys(j.stats.byType).join(', '));
  })"

# Generate HTML and check file exists
bash scripts/generate.sh /root/projects/Interverse /tmp/test-ecosystem.html
ls -la /tmp/test-ecosystem.html

# Verify variable ordering (no use-before-define)
node scripts/scan.js /root/projects/Interverse 2>/dev/null | \
  bash scripts/generate.sh /root/projects/Interverse /tmp/test.html && \
  echo "Generation succeeded"
```

## Gotchas

- **Blank page = JS error**: The template runs as a single inline `<script>` block. Any `ReferenceError` kills the entire script silently — the page renders as blank with no console visible to most users. Always verify variable ordering after edits.
- **`regenerate-and-deploy.sh` uses a worktree**: It creates a temporary git worktree for `gh-pages`, copies the file, commits, pushes, and cleans up — it never touches the `main` working tree.
- **Scanner skips itself**: `interchart` is excluded from scanning (line 339 in `scan.js`) to avoid a self-referential node.
- **D3 CDN dependency**: The generated HTML loads `https://d3js.org/d3.v7.min.js` — it will not render offline.
- **`box-sizing: border-box`**: The template uses this globally. The sidebar overlays the graph (no `padding-left`) so the SVG content area is the full `100vw`.
- **Convex hull edge case**: `d3.polygonHull()` requires 3+ non-collinear points. Two-point domains use a custom rounded-rectangle path. Single-point domains are skipped.
- **gh-pages branch isolation**: The `gh-pages` branch has only `index.html` and `.nojekyll`. Never merge it into `main` or vice versa.


