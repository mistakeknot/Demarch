# intersight — Development Guide

## Architecture

intersight is an Interverse plugin that extracts design systems from live websites. It has NO MCP server — all extraction happens via:

1. **Playwright MCP** (peer dependency) — `browser_evaluate` runs JS extraction scripts in the page context. Start with `--snapshot-mode none` to avoid ~70-80% token waste on auto-appended accessibility snapshots (only Phase 4's `browser_snapshot` needs them)
2. **Dembrandt CLI** (hard dependency) — `npx dembrandt <url> --dtcg --json-only` provides baseline token extraction
3. **Claude vision** (implicit) — screenshot analysis for layout patterns
4. **intercache MCP** (optional) — per-URL caching with content-hash invalidation

## Extraction Pipeline (7 Phases)

| Phase | Name | Tools Used | Depth: tokens | standard | full |
|-------|------|------------|---------------|----------|------|
| 0 | Preflight | browser_evaluate (robots.txt), intercache | Yes | Yes | Yes |
| 1 | Setup | browser_navigate | Yes | Yes | Yes |
| 2 | Dembrandt | Bash (npx) | Yes | Yes | Yes |
| 3 | DOM/CSS | browser_evaluate (7 scripts) | Yes | Yes | Yes |
| 4 | Structural | browser_snapshot + browser_evaluate | No | Yes | Yes |
| 5 | Visual | browser_take_screenshot + Claude vision | No | Yes | Yes |
| 6 | Interactions | browser_hover + browser_evaluate | No | No | Yes |
| 7 | Synthesis | Claude reasoning | Yes | Yes | Yes |

## File Map

- `.claude-plugin/plugin.json` — Plugin manifest
- `skills/analyze/SKILL.md` — Orchestration (the brain)
- `scripts/extraction/*.js` — 9 browser_evaluate scripts (the hands)
- `scripts/extraction/schema.json` — W3C DTCG output template
- `scripts/bump-version.sh` — Version management
- `tests/structural/` — Plugin structure validation tests

## Testing

```bash
cd tests && uv sync && uv run pytest -v && cd ..
```

Tests validate plugin structure (required files, plugin.json schema, skill frontmatter) — they do NOT test extraction logic (that requires a live browser).

## Output Format

W3C Design Tokens Community Group (DTCG) 2025.10 JSON with `intersight:*` extensions:
- `intersight:meta` — source URL, timestamp, depth, content hash, phase completion
- `intersight:components` — component inventory array
- `intersight:ux_flow` — navigation patterns, primary actions
- `intersight:visual_analysis` — layout pattern, hierarchy, responsive behavior
