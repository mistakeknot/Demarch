---
artifact_type: review-synthesis
method: flux-review
target: "docs/brainstorms/2026-04-03-tuivision-token-encoding-brainstorm.md"
target_description: "Tuivision token-efficient terminal state encoding brainstorm"
tracks: 4
track_a_agents: [fd-xterm-headless-renderer-architecture, fd-bpe-marker-tokenization, fd-color-quantization-palette, fd-inverse-video-selection-semantics, fd-mcp-tool-api-breaking-change]
track_b_agents: [fd-cartographic-symbology, fd-market-data-feed, fd-subtitle-caption-encoding, fd-avionics-data-bus]
track_c_agents: [fd-medieval-rubrication-marginalia, fd-kodo-incense-classification, fd-polynesian-stick-chart-navigation, fd-girih-geometric-tiling]
track_d_agents: [fd-marshallese-stick-chart-crossmodal-encoding, fd-geez-fidel-syllabary-quantized-modification, fd-tibetan-mandala-positional-chromatic-semantics]
date: 2026-04-03
findings_total: 42
findings_by_severity: {P0: 2, P1: 15, P2: 16, P3: 9}
---

# Brainstorm Review Synthesis — Tuivision Token Encoding

16 agents across 4 semantic distance tiers reviewed the tuivision token-encoding brainstorm. This synthesis merges findings with emphasis on cross-track convergence.

## Critical Findings (P0/P1)

### P0: Default format change has no consumer failure detection

- **Agents:** fd-avionics-data-bus (Track B), fd-mcp-tool-api-breaking-change (Track A)
- **Convergence:** 2/4 tracks
- **Issue:** Changing default from `full` to `compact` silently changes the response shape — callers expecting `ScreenState` JSON with `lines[]` receive a flat `CompactScreenState` with just `text`. No in-band signal tells consumers the format changed. Track B (avionics) classifies this as a "latent failure" — quiet corruption, not a loud error.
- **Fix:** Add a `format` field to every `get_screen` response envelope. Consider recommending `annotated` as the new default instead of `compact`, since it carries more signal. Gate the default change behind a semver major bump or add a deprecation notice.

### P0: Unsafe internal API usage at terminal-renderer.ts:208

- **Agent:** fd-xterm-headless-renderer-architecture (Track A)
- **Issue:** `cell as unknown as { fg: number; bg: number }` bypasses xterm.js public `IBufferCell` API. The new `getAnnotatedText()` would inherit this fragility. Any xterm.js minor version bump that changes the internal bit layout will silently produce wrong colors.
- **Fix:** Refactor to use `cell.getFgColorMode()` + `cell.getFgColor()` (public API). ~15 lines. Prerequisite for child .1.

### P1: Color quantization is calibrated to hardware palette, not terminal semantics (4/4 convergence)

- **Agents:** fd-color-quantization-palette (Track A), fd-cartographic-symbology (Track B), fd-kodo-incense-classification (Track C), fd-geez-fidel-syllabary (Track D)
- **Convergence:** 4/4 tracks — the highest-confidence finding in this review
- **Issue:** The 16 xterm colors are a hardware artifact (1981 CGA). The quantization maps visual hue, not agent-actionable meaning. Track A: Solarized blue maps to cyan (wrong semantic). Track B: no declared precision tier for when quantization is safe. Track C: `bright-red` vs `red` is a luminance distinction agents can't act on. Track D: calibrated to calligraphic convenience, not phonological distinctness (Ge'ez analogy).
- **Fix:** For palette indices 0-15, use the palette index directly ("the terminal said blue"). For truecolor, consider CIELAB distance over RGB Euclidean. Add a `SEMANTIC_COLOR_GROUPS` constant grouping colors into functional classes (error, success, warning, info, muted, highlight, neutral).

### P1: Marker grammar has no escape sequence (2/4 convergence)

- **Agents:** fd-subtitle-caption-encoding (Track B), fd-girih-geometric-tiling (Track C)
- **Convergence:** 2/4 tracks
- **Issue:** No specification for when terminal content contains literal `[r]`, `[/]`, or `[I]`. Track B: WebVTT learned this the hard way — SRT went unspecified and fragmented. Track C: without escape rules, the grammar's edge-matching is undefined.
- **Fix:** Specify double-bracket escaping (`[[r]]` renders as literal `[r]`) before child .1 is implemented. This must be in the format spec before any consumer is written.

### P1: Token cost claim of "2-3 tokens per marker pair" is unvalidated (3/4 convergence)

- **Agents:** fd-bpe-marker-tokenization (Track A), fd-market-data-feed (Track B), fd-geez-fidel-syllabary (Track D)
- **Convergence:** 3/4 tracks
- **Issue:** Track A: cl100k tokenizes `[r]...[/]` as 4 tokens per pair, not 2-3. Dense screens (vim, htop) have 100-300 styled runs — markers alone could reach 400-1200 tokens. Track B: no adversarial benchmarks. Track D: long color names (`[lightcyan]`) tokenize as 4-5 tokens, breaking grammar consistency.
- **Fix:** Run actual tokenization benchmark on 3 representative screens (vim, htop, empty shell) before committing to the format. If single-char abbreviations (`[r]`, `[R]` for bright) are needed, decide now — changing the color vocabulary after release is breaking.

### P1: SVG span-merging needs semantic boundary awareness (3/4 convergence)

- **Agents:** fd-mcp-tool-api-breaking-change (Track A), fd-subtitle-caption-encoding (Track B), fd-tibetan-mandala (Track D)
- **Convergence:** 3/4 tracks
- **Issue:** Track A: per-cell SVG replacement is an undocumented breaking change. Track B: merge fails for bidi text and combining diacritics. Track D: adjacent same-styled cells from different semantic units (end of error message, start of filename) merge into one span, destroying the boundary.
- **Fix:** Add boundary conditions to merge: do not merge across line boundaries or whitespace gaps. Add a `svg_mode` parameter (`per_cell` | `merged`) to preserve backward compatibility. Test with RTL and combining characters.

### P1: Marker composition rules undefined (2/4 convergence)

- **Agents:** fd-avionics-data-bus (Track B), fd-girih-geometric-tiling (Track C)
- **Convergence:** 2/4 tracks
- **Issue:** A cell that is both red and bold has two valid representations: `[r][B]text[/][/]` (nested) or `[rB]text[/]` (combined). The `[/]` closer's scope is unspecified — does it close one marker or all markers? Track B: avionics treats undefined composability as a review hold. Track C: girih without edge-matching rules produces locally plausible but globally incoherent patterns.
- **Fix:** Specify before child .1: "Markers do not nest. `[/]` closes all currently open markers. Multiple attributes combine as `[rBI]...[/]`." This simplifies parsing and BPE cost.

### P1: Format ladder is fidelity-graduated, not purpose-differentiated (2/4 convergence)

- **Agents:** fd-polynesian-stick-chart-navigation (Track C), fd-marshallese-stick-chart (Track D)
- **Convergence:** 2/4 tracks (independent, different cultural traditions)
- **Issue:** All five formats answer the same question at different resolution levels. Track C: Marshall Islands navigators built three chart types that answered different questions. Track D: the annotated format as designed is SVG with less detail, not a genuinely different instrument.
- **Fix:** Add purpose labels to each format in the specification. Add a structural preamble to annotated output (`[screen 80x24 cursor=12,8]`) that provides information `full` does not — making annotated purpose-differentiated rather than merely cheaper.

## Cross-Track Convergence

| Finding | Tracks | Score | Category |
|---------|--------|-------|----------|
| Color quantization: semantic not visual | A, B, C, D | 4/4 | Design flaw |
| Token cost claims unvalidated | A, B, D | 3/4 | Risk |
| SVG span-merge needs boundaries | A, B, D | 3/4 | Design flaw |
| Default change: no failure detection | A, B | 2/4 | Breaking change |
| Marker grammar: no escaping | B, C | 2/4 | Specification gap |
| Marker composition rules undefined | B, C | 2/4 | Specification gap |
| Format ladder: fidelity not purpose | C, D | 2/4 | Architectural |
| Visual compression vs semantic transduction | C, D | 2/4 | Philosophical |

The 4/4 convergence on color quantization is decisive: every track independently identified that the 16-color palette organizes by hardware hue, not by what agents can act on.

## Domain-Expert Insights (Track A)

Track A's 5 adjacent-domain specialists produced 13 findings grounded in actual source code:

- **Internal API fragility (P0):** The `as unknown as { fg: number; bg: number }` cast at terminal-renderer.ts:208 is the single highest-risk line in the codebase for this feature. Building the annotated format on this foundation is structurally unsound.
- **Token arithmetic gap:** The brainstorm's economic argument lacks a worked example. 100-300 styled runs at 4 tokens per marker pair puts markers alone at 400-1200 tokens, potentially exceeding the 400-600 target before any text content.
- **Inverse coverage is partial:** Most production TUI frameworks (ratatui, bubbletea with custom themes, blessed) use explicit fg/bg colors rather than SGR 7. The `[I]` marker fires for default-styled selections in some frameworks but misses customized ones.
- **Wide character handling:** CJK/emoji continuation cells will produce doubled markers in annotated output without a `getWidth() === 0` guard.
- **Double traversal in compact format:** `screen.ts` calls `getScreenState()` then `getScreenText()` which internally calls `getScreenState()` again — a pattern to avoid when adding the annotated path.

## Parallel-Discipline Insights (Track B)

Track B's 4 orthogonal-domain agents surfaced operational patterns from cartography, market data, subtitles, and avionics:

- **Avionics frame labeling (P0):** Every message on a data bus carries a format identifier. The `get_screen` response needs a `format` field in the envelope so consumers can detect unexpected format changes rather than silently misparsing.
- **Subtitle escape grammar (P1):** WebVTT's entity escaping exists because caption text routinely contains tag-like strings. The annotated format's markers will appear in terminal content (log messages, test output) — escaping must be specified before the format ships.
- **Market data versioning (P2):** Any format that will evolve (17 deferred children) must carry its version from day one. Adding a version field retroactively is itself a breaking change.
- **Cartographic symbol overloading (P2):** Color-to-role heuristics (`red = error`) are valid only within a declared context. Themed terminals break universal mappings. Role detection needs either a theme context parameter or explicit disclaimer.

## Structural Insights (Track C)

Track C's 4 distant-domain agents applied medieval scribal, Japanese incense, Polynesian navigation, and Islamic geometric traditions:

- **Stick chart purpose differentiation (P1):** The deepest architectural insight from Track C. The format ladder is three rebbelibs at different zoom levels when it needs a mattang, a meddo, and a rebbelib. Each format should answer a different question, not the same question at different cost.
- **Kodo discrimination gradient (P1):** The 16-color palette preserves distinctions (bright-red vs red) that agents cannot act on, while treating genuinely different semantic categories (red/error vs yellow/warning) as equally important.
- **Girih composability (P1):** The `role=` system adds named conventions that will require expansion for each new TUI class. Composable primitives (the 5 girih tiles) would be more extensible than enumerated roles.
- **Rubrication urgency gradient (P2):** On syntax-highlighted screens, markers become ubiquitous — every token carries color. When markers are everywhere, they signal nothing. A density threshold (suppress markers for the modal/default color) would preserve the urgency gradient.
- **Per-call retransmission (P2):** A 20-turn session where 10% changes per turn still transmits 20 full screens. Add a `screen_id` field now to enable future delta encoding.

## Frontier Patterns (Track D)

Track D's 3 esoteric agents applied Marshallese wave-piloting, Ethiopian syllabary design, and Tibetan mandala construction:

- **Cross-modal transduction (P1):** The root diagnosis across all three D-track agents. The annotated format is designed as *visual compression* (same information, fewer tokens) rather than *semantic transduction* (different information, optimized for LLM understanding). `[r]` tells the LLM "this text is red" but not "this text signals an operational failure." The role attributes carry the semantic signal but are opt-in.
- **Fidel modification grammar (P2):** BPE tokenization inconsistency across color names (`[r]` = 2 tokens, `[lightcyan]` = 4-5 tokens) breaks the learnable grammar pattern. Single-character codes would give consistent 2-token cost across all 16 colors.
- **Mandala positional semantics (P1):** SVG span-merging groups by visual style without checking semantic boundaries. Adjacent red cells from different semantic units merge into one span, destroying the boundary.
- **Mandala center-outward protocol (P2):** Annotated output streams detail (color markers) before establishing structure (screen dimensions, pane layout). The LLM interprets character-level annotations without a spatial model.

## Synthesis Assessment

**Overall quality:** The brainstorm is well-scoped, grounded in prior research (17-agent flux-review synthesis), and correctly identifies the 25x cost gap as the primary problem. The MVP scope of 5 children is pragmatic. The core weakness is that the brainstorm treats the annotated format as a compression problem (same information, fewer tokens) when the opportunity is a transduction problem (different information, better for LLM reasoning).

**Highest-leverage improvement:** Specify the marker grammar completely before implementation. Three specification gaps (escaping, composition, version) were independently surfaced by 6 agents across 3 tracks. Fixing these post-release is breaking; fixing them pre-release costs a few hours of spec writing.

**Surprising finding:** The 4/4 convergence on color quantization. Every track independently identified that the 16-color palette organizes by 1981 hardware categories, not by what agents can act on. Track A found the technical bug (Solarized misclassification). Track B found the cartographic principle (no declared precision tier). Track C found the Kodo principle (preserve only actionable distinctions). Track D found the Ge'ez principle (quantization boundaries must match natural categories). Four completely independent reasoning paths arriving at "the color buckets are wrong" is the strongest signal in this review.

**Semantic distance value:** The outer tracks (C/D) contributed qualitatively different insights from the inner tracks (A/B). Track A found the implementation bugs (internal API, wide chars, double traversal). Track B found the operational discipline gaps (escaping, versioning, failure detection). Track C found the architectural misalignment (fidelity ladder vs purpose ladder, enumerative vs generative vocabulary). Track D found the philosophical frame (compression vs transduction). Without C/D, the review would recommend "fix these bugs and add these fields." With C/D, the review recommends "reconsider what this format is for" — a qualitatively different intervention that shapes every implementation decision downstream.
