---
artifact_type: review-synthesis
method: flux-review
target: "tuivision screenshot-to-text token optimization"
target_description: "Creative approaches to give LLMs rich terminal state information at minimal token cost"
tracks: 4
track_a_agents: [fd-terminal-emulation-fidelity, fd-token-encoding-representation, fd-svg-xml-optimization, fd-llm-vision-token-economics, fd-llm-context-management-tui]
track_b_agents: [fd-medical-imaging-compression, fd-accessibility-screen-reader, fd-game-rendering-lod, fd-wire-protocol-serialization]
track_c_agents: [fd-heraldic-blazon-notation, fd-choreographic-notation, fd-astronomical-plate-annotation, fd-textile-weaving-draft, fd-wayfinding-signage-hierarchy]
track_d_agents: [fd-quipu-khipu-multichannel-encoding, fd-protactile-modality-transduction, fd-cuneiform-token-abstraction-pressure]
date: 2026-04-02
---

# Tuivision Token Optimization — Cross-Track Synthesis

17 agents across 4 semantic distance tiers reviewed tuivision's terminal state representation system. This document synthesizes their findings with emphasis on cross-track convergence.

## Critical Findings (P0/P1)

### P0: Color stripped in text mode — red errors indistinguishable from green success

- **Agents:** fd-quipu-khipu (Track D), fd-terminal-emulation-fidelity (Track A), fd-accessibility-screen-reader (Track B), fd-heraldic-blazon-notation (Track C)
- **Convergence:** 4/4 tracks independently identified this as the highest-severity gap
- **Impact:** Any agent reading test output, git diff, or status displays cannot determine pass/fail from text mode alone
- **Fix:** Add semantic color annotations to text output. The quipu model (color is DATA, not decoration) and blazon model (7 named tinctures) converge on the same solution: quantize to ~7 semantic color categories (error, success, warning, info, highlight, dim, neutral) instead of 16M RGB values

### P1: No mode between ~250 tokens (text, blind) and ~5000 tokens (SVG, verbose)

- **Agents:** All 17 agents across all 4 tracks
- **Convergence:** 4/4 tracks — the unanimous highest-priority finding
- **Impact:** Agents either operate blind (text) or pay 10-20x overhead (SVG/PNG) for color/style information
- **Fix:** New `annotated` format at ~400-600 tokens. Track A (token encoding) benchmarked ANSI-inspired markers `[r]error[/]` as the optimal syntax. Track B (accessibility) proposed ARIA-like role tags `[selected]`, `[status]`, `[title]`. Track C (blazon) proposed semantic region names. Track D (cuneiform) proposed determinative-style type tags. All converge on: inline text markers with semantic color names.

### P1: `get_screen` defaults to `full` JSON at ~12,000 tokens

- **Agent:** fd-token-encoding-representation (Track A)
- **Impact:** Agents calling `get_screen` without format specification burn 12K tokens per capture. Context overflow by turn 6-7.
- **Fix:** Change default to `compact` or `text`. Add cost warning to `full` format description.

### P1: Per-cell SVG `<text>` elements — 65-75% token waste

- **Agent:** fd-svg-xml-optimization (Track A), fd-wire-protocol-serialization (Track B)
- **Impact:** Each character gets its own `<text>` element. `class="terminal-text"` repeated 1150 times per screen.
- **Fix:** Run-length encode same-styled spans. CSS class dictionary instead of inline styles.

### P1: Vision tokens cannot be cached — 10-32x multi-turn cost disadvantage

- **Agent:** fd-llm-vision-token-economics (Track A)
- **Impact:** Anthropic's 90% prompt caching discount applies to text but not vision tokens. A 10-turn session with PNG screenshots costs 10-32x more than the equivalent annotated text.
- **Fix:** This finding makes the case for text-based representations decisive for multi-turn agent sessions.

### P1: Inverse attribute silently resolved — focus/selection semantics destroyed

- **Agent:** fd-terminal-emulation-fidelity (Track A)
- **Impact:** `terminal-renderer.ts:222-223` pre-swaps fg/bg for inverse cells. Downstream cannot distinguish "selected item" from "blue-background header."
- **Fix:** Check `inverse` boolean directly in annotated mode. Or derive a `selected` semantic flag.

## Cross-Track Convergence

Findings that appeared independently across multiple tracks, ranked by convergence score.

### 4/4 Tracks: Semantic encoding over visual reproduction

| Track | Agent(s) | Framing |
|-------|----------|---------|
| A (Adjacent) | token-encoding, context-management | "ANSI-inspired markers with quantized named colors" |
| B (Orthogonal) | accessibility, wire-protocol | "ARIA role annotations" / "run-length encoded DSL" |
| C (Distant) | blazon, weaving-draft, cuneiform | "semantic vocabulary" / "generative rules" / "iconic→symbolic" |
| D (Esoteric) | quipu, Pro-Tactile, cuneiform | "channel-selective" / "contrastive features only" / "meaning not appearance" |

**Synthesis:** All 4 tracks independently arrived at the same architectural direction — tuivision needs a mode that encodes *what the terminal means* rather than *what the terminal looks like*. The ancient domains (blazon, cuneiform, quipu) are particularly clear: under medium-cost pressure, representation systems always evolve from iconic to symbolic.

### 4/4 Tracks: Hierarchical detail levels

| Track | Agent(s) | Framing |
|-------|----------|---------|
| A | context-management | "progressive disclosure — cheap summary first, detail on demand" |
| B | game-LOD, medical-imaging | "4-level LOD ladder" / "progressive resolution" |
| C | wayfinding, choreography | "L0/L1/L2 signage" / "motif vs. full notation" |
| D | Pro-Tactile | "contrastive feature filtering by task" |

**Synthesis:** Every domain that deals with information-under-constraint independently develops a hierarchical fidelity system. Tuivision currently has flat modes (text OR image). The converged recommendation is a LOD ladder:

| Level | Name | Tokens | Content |
|-------|------|--------|---------|
| L0 | Motif | 15-40 | Symbolic summary: `BUILD:running TESTS:47/120 ERRORS:0` |
| L1 | Annotated | 400-600 | Full text + semantic color/bold/selection markers |
| L2 | ROI-SVG | 800-1500 | Optimized SVG with span-merging, only styled regions at full fidelity |
| L3 | Full SVG/PNG | 1600-8000 | Current modes, for visual debugging |

### 3/4 Tracks: Session-local dictionary / catalog

| Track | Agent(s) | Framing |
|-------|----------|---------|
| A | token-encoding | "diff-based encoding with full refresh every 5 turns" |
| B | wire-protocol | "dictionary compression for repeated strings" |
| C | astronomy | "catalog cross-referencing — objects reference IDs not descriptions" |
| D | cuneiform | "determinatives — type-context markers for disambiguation" |

**Synthesis:** Repeated patterns (shell prompts, file paths, status bar text) should be assigned short IDs on first appearance and referenced by ID thereafter. Combined with diff-mode (send only changed lines), this could reduce multi-turn costs by 60-80%.

### 3/4 Tracks: Independent semantic channels

| Track | Agent(s) | Framing |
|-------|----------|---------|
| A | terminal-fidelity | "tiered attributes: T1 (always), T2 (when present), T3 (drop)" |
| C | choreography | "structure/content/emphasis as separable channels" |
| D | quipu | "five independent channels, independently omittable" |

**Synthesis:** The caller should be able to request specific channels: `{text, color, bold}` for monitoring, `{text, position, selection}` for navigation. This is the quipu insight operationalized.

## Domain-Expert Insights (Track A)

The five adjacent-domain specialists produced 23 findings grounded in actual source code:

- **Tiered attribute table** — Comprehensive classification of all terminal attributes into T1 (always encode: color, bold, reverse, cursor), T2 (when present: underline, dim, bg), T3 (drop: blink, overline, exact truecolor). This is the implementation spec for the annotated mode.
- **BPE tokenizer benchmarks** — ANSI-inspired `[r]error[/]` format costs 2-3 tokens per marker pair and outperforms HTML tags (8-12 tokens), custom Unicode (3-4 tokens per "character"), and markdown (ambiguity issues). This settles the format question.
- **Color quantization function** — Map all hex/256-color/truecolor to 16 named colors at `terminal-renderer.ts`. Saves 400-600 tokens per screen capture.
- **Diff viability window** — LLMs reliably reconstruct from diffs for 3-5 turns, then need a full refresh. Auto-insert full screen every 5 turns.

## Parallel-Discipline Insights (Track B)

- **Medical imaging ROI** — Not all screen regions are diagnostically significant. The cursor-adjacent area and styled regions are the "tumor"; static chrome is the "background tissue." Encode at different fidelity levels.
- **Screen reader ARIA roles** — Terminal UIs signal roles through visual conventions (inverse=selected, bold+top-row=heading, red=error). These can be auto-detected and annotated.
- **Game LOD** — The absence of temporal coherence (full state returned every call) and occlusion culling (modal dialogs render background content) are the two biggest waste sources after the format gap.
- **Wire protocol** — The "missing mode" is a run-length encoded DSL with CSS-like class definitions. A format designed for the wire (token channel) rather than for human eyes.

## Structural Insights (Track C)

- **Blazon's "Terminal Blazon" format** — A complete screen description in 50-80 tokens using named regions, semantic tinctures, marshalling for multi-pane layouts, and cadency marks for diffs. The most aggressive compression proposal.
- **Weaving drafts' generative encoding** — Structured UI (tables, lists, trees) should transmit template+data instead of fully-rendered output. A 40-row file browser: 400→90 tokens.
- **Wayfinding's decision-point focus** — Not every terminal call requires screen state. When the terminal is mid-execution (not awaiting input), a motif-level "still running" costs 5 tokens vs. 300.

## Frontier Patterns (Track D)

- **Quipu channel independence** — The deepest architectural insight: terminal cell attributes are independent data channels, not bundled visual properties. The annotated mode should let callers select channels.
- **Pro-Tactile contrastive analysis** — Not a compression technique but a design methodology: before building any encoding, identify which visual features are *contrastive* (change agent behavior) vs. *redundant* (different rendering, same meaning). Apply per-task.
- **Cuneiform abstraction pressure** — The meta-insight that unifies all tracks: under token budget pressure, terminal encoding will inevitably evolve from iconic (reproducing appearance) to symbolic (declaring meaning). Building the symbolic mode now is building the destination, not a waypoint.

## Synthesis Assessment

**Overall quality:** Tuivision's architecture is sound — the ScreenState data model captures everything needed. The gap is in the *output* layer: three modes with a 25x cost gap between "useful but expensive" and "cheap but blind."

**Highest-leverage improvement:** Add a single new `annotated` text format to `get_screen` at ~400-600 tokens with `[r]error[/]` inline markers, quantized to 16 named colors. This single change closes the 25x cost gap for 80%+ of agent use cases. Implementation touches `src/tools/screen.ts` (new format case) and `src/terminal-renderer.ts` (color quantization + annotation rendering). Estimated: 200-300 lines of TypeScript.

**Surprising finding:** The cuneiform-quipu-Pro-Tactile convergence. Three domains separated by 5000 years, 10000 miles, and completely different physical substrates all independently solved "rich information through constrained channel" with the same three-step pattern: (1) identify independent data channels, (2) determine which channels are contrastive for the task, (3) encode symbolically rather than iconically. This is not a metaphor — it's a specific, implementable pipeline.

**Semantic distance value:** The outer tracks (C/D) contributed insights qualitatively different from the inner tracks (A/B). Track A found the implementation details (which BPE format, which source lines). Track B found the architectural patterns (ROI, LOD, wire protocol). Track C found the design language (blazon grammar, generative encoding, progressive disclosure). Track D found the *meta-principles* (channel independence, contrastive analysis, abstraction pressure) that explain WHY the A/B recommendations work. Without C/D, the recommendation would be "add an annotated mode." With C/D, the recommendation is "add an annotated mode, and here is the principled framework for evolving it over time."
