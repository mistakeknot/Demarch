# Plan: Interchart — Interactive Ecosystem Diagram Plugin
**Bead:** iv-fgde
**Phase:** planned (as of 2026-02-21T02:04:24Z)

## Goal

Create a new `interchart` plugin under `plugins/interchart/` that scans the Interverse monorepo and generates a self-contained interactive HTML diagram (D3.js force graph) showing all plugins, skills, MCP servers, hooks, services, and their relationships. Includes a `/interchart` skill for on-demand generation and a filter/detail panel UI.

## Scope

- New plugin: `plugins/interchart/` with `.claude-plugin/plugin.json`, scanner script, HTML template, skill
- Scanner reads `.claude-plugin/plugin.json` from 31 plugins + Clavain hub
- D3.js force graph with color-coded nodes, styled edges, zoom/pan
- Click-to-expand detail panels, type filter toolbar
- Self-contained HTML output to `docs/diagrams/ecosystem.html`
- **Out of scope:** MCP server, live runtime overlay, auto-regeneration hooks, diff mode

## Tasks

### Task 1: Scaffold plugin structure (`plugins/interchart/`)

Create the plugin directory with standard structure:

**Files to create:**
- `plugins/interchart/.claude-plugin/plugin.json` — manifest with name, version, description, skills array
- `plugins/interchart/CLAUDE.md` — minimal quick reference
- `plugins/interchart/skills/interchart/SKILL.md` — generation skill

**plugin.json contents:**
```json
{
  "name": "interchart",
  "version": "0.1.0",
  "description": "Interactive ecosystem diagram — scans Interverse monorepo and generates a D3.js force graph showing all plugins, skills, MCP tools, hooks, and their relationships.",
  "author": { "name": "mistakeknot" },
  "license": "MIT",
  "keywords": ["visualization", "ecosystem", "diagram", "d3", "architecture"],
  "skills": ["./skills/interchart"]
}
```

**SKILL.md:** Instructs Claude to run the scanner script and report results. Frontmatter: `name: interchart`, `description: Generate interactive ecosystem diagram...`.

**Depends on:** nothing
**Bead:** iv-eg90
**Phase:** planned (as of 2026-02-21T02:04:24Z)

### Task 2: Build the ecosystem scanner (`plugins/interchart/scripts/scan.js`)

Node.js script that walks the monorepo and outputs a JSON graph to stdout.

**Scanning logic:**
1. Read all `plugins/*/.claude-plugin/plugin.json` files — extract: name, version, description, skills (array of paths), commands (array of paths), agents (array of paths), mcpServers (object keys), hooks path
2. For each plugin's skills paths, read `SKILL.md` frontmatter (name, description) — use simple regex, no YAML parser needed
3. Read `hub/clavain/.claude-plugin/plugin.json` — same extraction
4. Read Clavain skills from `hub/clavain/skills/*/SKILL.md`
5. Add fixed nodes for: Intercore (`infra/intercore/`), Intermute (`services/intermute/`), Interbase (`sdk/interbase/`), Autarch/Interforge (`Interforge/`), Interverse (root)
6. Read `plugins/*/hooks/hooks.json` where it exists — extract event names (SessionStart, PreToolUse, etc.)

**Output JSON schema:**
```json
{
  "generated": "2026-02-20T...",
  "nodes": [
    { "id": "interflux", "type": "plugin", "label": "interflux", "description": "...", "version": "0.2.18", "meta": {} }
  ],
  "edges": [
    { "source": "interflux", "target": "interflux:flux-drive", "type": "provides-skill" }
  ]
}
```

**Node types:** `plugin`, `skill`, `mcp-server`, `agent`, `service`, `hub`, `kernel`, `sdk`, `tui`, `monorepo`
**Edge types:** `provides-skill`, `provides-agent`, `provides-mcp`, `fires-hook`, `companion-of`, `part-of`

**Companion-of edges:** Parse Clavain's plugin.json description for "Companions:" list. Also check each plugin's description for "Companion plugin for Clavain" → create `companion-of` edge to `clavain`.

**Implementation notes:**
- Use `fs.readdirSync` / `fs.readFileSync` — no external deps, runs with system Node.js
- Gracefully skip missing dirs/files (warn to stderr, continue)
- Script is invoked as: `node plugins/interchart/scripts/scan.js /path/to/interverse/root`

**Bead:** iv-drxi
**Phase:** planned (as of 2026-02-21T02:04:24Z)

### Task 3: Build the HTML template (`plugins/interchart/templates/ecosystem.html`)

Self-contained HTML file with embedded D3.js and a `DATA_PLACEHOLDER` marker that the generator replaces with the scanned JSON.

**Structure:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>Interverse Ecosystem</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>/* all CSS inline */</style>
</head>
<body>
  <div id="toolbar"><!-- type filter buttons --></div>
  <div id="graph"><!-- SVG rendered here --></div>
  <div id="detail-panel"><!-- click-to-expand panel --></div>
  <script>
    const data = /*DATA_PLACEHOLDER*/;
    // D3 force simulation setup
    // Node rendering with color by type
    // Edge rendering with style by type
    // Zoom/pan behavior
    // Click handlers for detail panel
    // Filter toggle handlers
  </script>
</body>
</html>
```

**Visual design:**
- Node colors: plugin=#4A90D9 (blue), skill=#50C878 (green), agent=#FF8C42 (orange), mcp-server=#9B59B6 (purple), service=#E74C3C (red), hub=#F39C12 (gold), kernel=#1ABC9C (teal), sdk=#95A5A6 (gray), tui=#E91E63 (pink), monorepo=#34495E (dark gray)
- Node sizes: hub/monorepo=20px, plugin/service/kernel=14px, skill/agent/mcp-server=8px
- Edge styles: provides-skill=solid thin, provides-agent=solid thin, provides-mcp=dashed, companion-of=dotted thick, part-of=solid light gray
- Dark background (#1a1a2e), light text, glowing nodes on hover
- Detail panel: fixed right sidebar (300px wide), slides in on click

**Interaction:**
- D3 force simulation with collision avoidance
- Zoom: d3.zoom() on SVG container
- Pan: drag background
- Click node: populate detail panel, highlight connected nodes (increase opacity of connected, decrease others)
- Click background: dismiss detail panel

**Filter toolbar:**
- Row of pill buttons at top, one per node type
- Each button toggles visibility of that type
- "All" and "None" convenience buttons
- Active = filled, inactive = outline-only

**Bead:** iv-58ik, iv-zwdz, iv-q0b4 (F2 + F3 + F4 combined into one HTML file)
**Phase:** planned (as of 2026-02-21T02:04:24Z)

### Task 4: Build the generator script (`plugins/interchart/scripts/generate.sh`)

Bash script that orchestrates: run scanner → inject data into template → write output file.

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
INTERVERSE_ROOT="${1:-$(cd "$PLUGIN_DIR/../.." && pwd)}"
OUTPUT="${2:-$INTERVERSE_ROOT/docs/diagrams/ecosystem.html}"

# Run scanner
DATA=$(node "$SCRIPT_DIR/scan.js" "$INTERVERSE_ROOT")

# Count nodes/edges for reporting
NODE_COUNT=$(echo "$DATA" | node -e "process.stdin.on('data',d=>{const j=JSON.parse(d);console.log(j.nodes.length)})")
EDGE_COUNT=$(echo "$DATA" | node -e "process.stdin.on('data',d=>{const j=JSON.parse(d);console.log(j.edges.length)})")

# Read template, replace placeholder, write output
mkdir -p "$(dirname "$OUTPUT")"
node -e "
  const fs = require('fs');
  const tmpl = fs.readFileSync('$PLUGIN_DIR/templates/ecosystem.html', 'utf8');
  const data = fs.readFileSync('/dev/stdin', 'utf8');
  const out = tmpl.replace('/*DATA_PLACEHOLDER*/', data);
  fs.writeFileSync('$OUTPUT', out);
" <<< "$DATA"

echo "Generated: $OUTPUT ($NODE_COUNT nodes, $EDGE_COUNT edges)"
```

**Bead:** iv-eg90
**Phase:** planned (as of 2026-02-21T02:04:24Z)

### Task 5: Write the `/interchart` SKILL.md

Skill markdown that instructs Claude to run the generator and report results.

```markdown
---
name: interchart
description: Generate interactive ecosystem diagram showing all Interverse plugins, skills, and their relationships as a D3.js force graph.
---

# Interchart: Ecosystem Diagram Generator

Run the ecosystem scanner and generate an interactive HTML diagram.

## Steps

1. Run the generator:
   ```bash
   bash ${CLAUDE_PLUGIN_ROOT}/scripts/generate.sh "<interverse_root>" "<output_path>"
   ```
   Default output: `docs/diagrams/ecosystem.html` in the Interverse root.

2. Report the result to the user: number of nodes, edges, and the output file path.

3. Suggest opening the file in a browser to explore the diagram.
```

**Bead:** iv-eg90
**Phase:** planned (as of 2026-02-21T02:04:24Z)

### Task 6: Initialize git repo and create CLAUDE.md/AGENTS.md

- `cd plugins/interchart && git init`
- Create `CLAUDE.md` with overview, quick commands, design decisions
- Create minimal `AGENTS.md` (or skip — can be generated later with `/interdoc`)
- Ensure `docs/diagrams/` directory exists in Interverse root

**Bead:** iv-fgde
**Phase:** planned (as of 2026-02-21T02:04:24Z)

### Task 7: Test end-to-end

- Run `node plugins/interchart/scripts/scan.js /root/projects/Interverse` and verify JSON output has expected node/edge counts
- Run `bash plugins/interchart/scripts/generate.sh` and verify `docs/diagrams/ecosystem.html` is created
- Verify the HTML file is valid and self-contained (check for DATA_PLACEHOLDER replaced)
- Count: expect ~31 plugin nodes, ~50+ skill nodes, ~17 agent nodes, several MCP server nodes, plus hub/kernel/service/sdk/tui/monorepo fixed nodes

**Bead:** iv-fgde
**Phase:** planned (as of 2026-02-21T02:04:24Z)
