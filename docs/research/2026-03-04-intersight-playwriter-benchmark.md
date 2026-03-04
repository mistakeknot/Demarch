# Benchmark: Playwriter vs Playwright MCP for Intersight

**Bead:** iv-rmn75
**Date:** 2026-03-04
**Status:** Complete — Playwriter not recommended; fast-playwright-mcp identified as better alternative

## Summary

Playwriter (remorses/playwriter) is **not viable** for Intersight due to its Chrome-extension architecture requiring a visible browser. However, the benchmark uncovered a better alternative: `@tontoko/fast-playwright-mcp`, a fork of Microsoft's Playwright MCP that adds per-tool snapshot suppression (`includeSnapshot: false`) and batch execution — exactly the features Intersight needs.

## Candidates Evaluated

### 1. Playwriter (remorses/playwriter)

**Architecture:** Chrome extension + WebSocket server + single `execute` MCP tool wrapping the full Playwright API.

**Token efficiency claim:** 80% less schema overhead (1 tool vs 25+).

**Disqualifying factors:**
- **Requires a visible Chrome browser with extension installed.** Intersight needs headless automated extraction — a running Chrome window is an operational burden and blocks CI/headless usage.
- **No headless mode.** By design, connects to an existing browser via Chrome's debugger API.
- **Session management complexity.** Requires `playwriter session new`, extension activation (click to turn green), WebSocket on localhost:19988.
- **Bot detection advantage irrelevant.** Intersight analyzes design systems, not protected content — it doesn't need to bypass bot detection.

**Verdict:** Architecturally incompatible. Skip.

### 2. Playwrightess (mitsuhiko/playwrightess-mcp)

**Architecture:** Single `playwright_eval` ubertool with persistent state.

**Disqualifying factors:**
- **Explicitly unpublished.** README states "This is an experiment and intentionally not published."
- **No documentation** on parameters, headless support, or screenshot handling.
- **No community** — experimental project by Armin Ronacher, not maintained for production use.

**Verdict:** Not production-grade. Skip.

### 3. @tontoko/fast-playwright-mcp (recommended)

**Architecture:** Fork of Microsoft's `@playwright/mcp` with added optimization features. Drop-in compatible with upstream tool names.

**Key features for Intersight:**
- **Per-tool `includeSnapshot: false`** via `expectation` parameter — exactly what iv-bco0o originally wanted
- **`browser_batch_execute`** — combine multiple sequential actions into one tool call, eliminating redundant intermediate responses
- **Snapshot options:** `selector` for targeted snapshots, `format: "aria"` for optimized output
- **Diff mode:** `diffOptions.enabled: true` shows only changes (useful for Phase 6 hover state extraction)
- **Image compression:** JPEG with configurable quality for screenshots (reduces screenshot token cost)

**Token savings estimate for Intersight:**

| Depth | Tool calls | Snapshot overhead (upstream) | With fast-playwright-mcp |
|-------|-----------|----------------------------|--------------------------|
| `tokens` | 16 | 16 × ~4,000 = ~64,000 tokens | ~0 (all suppressed) |
| `standard` | 18 | 17 × ~4,000 = ~68,000 tokens | ~4,000 (1 snapshot for Phase 4) |
| `full` | ~40 | ~39 × ~4,000 = ~156,000 tokens | ~4,000 (1 snapshot for Phase 4) |

Note: With upstream `--snapshot-mode none`, savings are similar but applied server-wide. Fast-playwright-mcp allows per-tool control, which is more precise — but for Intersight's case, where only 1 of 16-40 calls needs snapshots, server-wide `none` is equally effective.

**Batch execution savings:**
Phase 3 (DOM/CSS extraction) runs 7 sequential `browser_evaluate` calls. With `browser_batch_execute`, these could be combined into 1 tool call, saving 6 round-trips of response overhead. Estimated additional savings: ~2,000-3,000 tokens from eliminated intermediate responses.

**Installation:** `claude mcp add fast-playwright npx @tontoko/fast-playwright-mcp@latest`

**Stability:** 598 commits, 31 stars, 3 open issues. Active maintenance. npm published.

## Comparison Matrix

| Feature | Playwright MCP | + `--snapshot-mode none` | fast-playwright-mcp | Playwriter | Playwrightess |
|---------|---------------|-------------------------|---------------------|------------|---------------|
| Headless | Yes | Yes | Yes | **No** | Unknown |
| Per-tool snapshot control | No | No | **Yes** | N/A | N/A |
| Batch execution | No | No | **Yes** | No | No |
| Drop-in compatible | Baseline | Yes | **Yes** | No | No |
| Published/stable | Yes | Yes | Yes | Yes | **No** |
| JS execution | browser_evaluate | browser_evaluate | browser_evaluate | execute | playwright_eval |
| Tool count overhead | 25+ tools | 25+ tools | 25+ tools + batch | 1 tool | 1 tool |

## Recommendation

**Tier 1 (immediate, already done):** `--snapshot-mode none` on upstream Playwright MCP. Zero migration cost. Implemented in iv-bco0o.

**Tier 2 (low-effort upgrade):** Switch to `@tontoko/fast-playwright-mcp`. Drop-in replacement with added benefits:
- Per-tool snapshot control (future-proofs if Intersight needs selective snapshots)
- Batch execution for Phase 3 (7 scripts → 1 call)
- Image compression for Phase 5 screenshots
- Diff mode for Phase 6 hover state comparison

**Tier 3 (not recommended):** Playwriter/Playwrightess. Wrong architecture for headless extraction.

## Next Steps

1. Update Intersight SKILL.md to mention `@tontoko/fast-playwright-mcp` as recommended alternative
2. Optionally batch Phase 3 extraction scripts using `browser_batch_execute` in a future iteration
3. Close iv-fvch0 (Playwright CLI evaluation) as P4/backlog — the fast-playwright-mcp fork provides sufficient optimization without CLI migration
