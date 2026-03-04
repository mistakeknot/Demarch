# intersight

Automated UI/UX design analysis for Claude Code. Extracts W3C DTCG design tokens, component inventories, and layout analysis from any URL.

## Usage

```
/intersight:analyze <URL> [--depth tokens|standard|full] [--format json|markdown|tokens-only] [--fresh] [--pages /path1,/path2]
```

### Depth Modes

| Mode | Output | Cost |
|------|--------|------|
| `tokens` | Color, typography, spacing, shadow tokens in DTCG JSON (DOM extraction only) | ~$0.02/URL |
| `standard` | Tokens + component inventory + desktop layout analysis via Claude vision | ~$0.05/URL |
| `full` | Standard + responsive breakpoint analysis + hover/focus state capture | ~$0.10/URL |

### Formats

- `json` (default) — Full W3C DTCG JSON with `intersight:*` extensions
- `markdown` — Human-readable design system report
- `tokens-only` — Bare DTCG tokens without extensions

## Requirements

- **Playwright MCP server** — Must be configured in Claude Code MCP settings. For best token efficiency, start with `--snapshot-mode none` (saves ~70-80% tokens per action).
- **Dembrandt** — `npx dembrandt` must work (Node.js required)
- **intercache** (optional) — Enables per-URL caching

## How It Works

intersight runs a 7-phase extraction pipeline:
1. **Preflight** — robots.txt compliance, cache lookup
2. **Setup** — Navigate and wait for page stability
3. **Dembrandt** — Baseline token extraction via CLI
4. **DOM/CSS** — 7 focused JS scripts extract tokens from the live DOM
5. **Structural** — Accessibility tree + component inventory
6. **Visual** — Screenshot + Claude vision analysis
7. **Synthesis** — Merge all results into W3C DTCG format

## License

MIT
