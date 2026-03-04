# intersight

> See `AGENTS.md` for full development guide.

## Overview

Automated UI/UX design analysis plugin — 1 skill (`analyze`), 9 JS extraction scripts, 0 MCP servers. Orchestrates Dembrandt CLI + Playwright MCP + Claude vision to extract W3C DTCG design tokens, component inventories, and layout analysis from any URL. Three depth modes: `tokens` (DOM-only), `standard` (+ screenshot), `full` (+ responsive + interactions).

## Quick Commands

```bash
# Run structural tests
cd tests && uv sync && uv run pytest -q && cd ..

# Verify plugin structure
cat .claude-plugin/plugin.json | python3 -m json.tool

# Check extraction scripts are present
ls scripts/extraction/*.js | wc -l  # expect 9
```

## Design Decisions (Do Not Re-Ask)

- No dedicated MCP server — uses Playwright MCP's browser_evaluate for all DOM extraction
- Dembrandt CLI is a hard dependency (npm) — provides 80-95% of token extraction baseline
- intercache is optional — works without it, just slower
- W3C DTCG 2025.10 output format with `intersight:*` extension namespace
- 9 focused extraction scripts (not fewer combined scripts) — modularity over fewer round-trips
- robots.txt compliance mandatory — Phase 0 checks before any extraction
- Playwright MCP `--snapshot-mode none` recommended — only Phase 4 (`browser_snapshot`) needs the accessibility tree; all other ~15 tool calls discard it. Saves ~70-80% tokens per action
