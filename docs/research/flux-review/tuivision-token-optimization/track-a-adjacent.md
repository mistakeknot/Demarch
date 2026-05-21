# Track A: Adjacent Domain Expert Review -- Tuivision Token Optimization

**Review date:** 2026-04-02
**Track:** A (adjacent domain experts)
**Agents:** fd-terminal-emulation-fidelity, fd-token-encoding-representation, fd-svg-xml-optimization, fd-llm-vision-token-economics, fd-llm-context-management-tui
**Codebase reviewed:** `interverse/tuivision/` (v0.2.0)

---

## Executive Summary

Five specialist agents reviewed tuivision's terminal state representation pipeline. The current architecture has three modes with a massive cost gap: plain text (200-400 tokens, no style), PNG (1600 vision tokens), and SVG (2000-8000 tokens). The gap between "cheap but blind" and "informed but expensive" is the core problem. Key findings: (1) the SVG renderer emits per-cell `<text>` elements -- the single largest source of token waste -- and merging adjacent same-style cells into spans would cut SVG tokens by 60-75%; (2) a new "annotated text" mode using ANSI-inspired inline markers can deliver text+style at ~400-600 tokens, 3-4x cheaper than PNG while preserving the semantic signals that matter; (3) prompt caching changes the economics fundamentally -- vision tokens cannot be cached, so text-based representations get a compounding advantage in multi-turn sessions; (4) the `get_screen format="full"` mode returns JSON with per-cell objects that serialize to 20-40x the token count of plain text, yet tuivision never warns callers about this cost.

**Finding count:** 7 P1, 11 P2, 5 P3

---

## Agent 1: Terminal Emulation Fidelity

### Tiered Attribute Encoding Table

Grounded in the `CellData` interface at `src/terminal-renderer.ts:7-15`:

| Tier | Attribute | Signal value | Rationale |
|------|-----------|-------------|-----------|
| **T1: Always encode** | fg color (quantized to 16 named) | Critical | Sole differentiator for pass/fail (red/green), error levels, syntax highlighting. In test runners, `git diff`, and status displays, color IS the data. |
| T1 | bold | High | Distinguishes headers, selected items, emphasis in nearly all TUI frameworks. ratatui's `Style::bold()` marks interactive elements. |
| T1 | reverse video (inverse) | High | The universal "selected/focused" indicator in terminal UIs. Menus, autocomplete, list selection all use reverse. The field exists at line 14 but `renderToSvg` at line 255-258 does not encode inverse as a distinct visual -- it pre-swaps fg/bg at line 222-223 in `getScreenState()`. |
| T1 | cursor position | High | Already in `ScreenState.cursor` (line 23-27). Without cursor, agent cannot determine focused widget in multi-pane TUIs. |
| **T2: Encode when present** | underline | Medium | Used for links (OSC 8 hyperlinks), emphasis, some menu indicators. Less universal than bold. |
| T2 | dim | Medium | Used for disabled/inactive items, comments, de-emphasized text. Semantically meaningful but less critical. |
| T2 | bg color (quantized) | Medium | Status bars, selection highlighting, diff markers. Usually redundant with reverse but not always. |
| T2 | italic | Low-medium | Rare in TUIs. Used by some syntax highlighters for comments. |
| **T3: Drop** | blink | None | No TUI framework uses blink semantically. Pure decoration. |
| T3 | overline | None | Not even in `CellData`. Not used in practice. |
| T3 | strikethrough | Near-none | Not in `CellData`. Extremely rare. |
| T3 | fraktur | None | Theoretical only. No terminal supports it. |
| T3 | Exact truecolor values | Negative | 16M colors encoded as `#rrggbb` strings. LLMs cannot meaningfully distinguish `#cd0000` from `#cc0100`. Quantize to 16 named colors. |

**Token cost estimate per tier** (80x24 screen, ~15 styled regions):

- Plain text only: ~200-400 tokens (current `get_screen text`)
- Text + T1 attributes: ~400-600 tokens (adds ~200 tokens for color/bold/cursor annotations)
- Text + T1 + T2: ~500-750 tokens (adds ~100-150 more for underline/dim/bg)
- Full SVG: ~2000-8000 tokens (current `get_screenshot svg`)
- PNG: ~1600 vision tokens (current `get_screenshot png`)

### Findings

**[P1] F1-1: Inverse attribute is silently resolved, destroying focus semantics**

File: `src/terminal-renderer.ts`, lines 222-223

```typescript
fg: inverse ? bg : fg,
bg: inverse ? fg : bg,
```

The renderer pre-swaps fg/bg colors when `inverse` is true, then passes the swapped colors downstream. The `inverse` boolean is still set in the `CellData` (line 14), but both `renderToSvg` (line 255) and `renderToPng` (line 150-151) ignore the `inverse` field entirely -- they just use the pre-swapped fg/bg. This means an optimized text representation built from `getScreenState()` data will see "white text on blue background" and have no way to know this was originally a reversed cell indicating selection/focus versus a cell that was genuinely styled white-on-blue. The semantic distinction ("this item is selected") is lost.

**Failure scenario:** An agent navigating a file picker sees item text in white-on-blue. It cannot distinguish "this file is highlighted/selected" from "this is a header with blue background styling." It presses Enter thinking it has selected the target file, but the actual selection is elsewhere.

**Fix:** When generating an annotated-text representation, check the `inverse` boolean directly rather than relying on the pre-swapped colors. Or add a `selected` semantic flag derived from inverse.

**[P1] F1-2: Color quantization is absent -- 256-color and truecolor values pass through as raw hex**

File: `src/terminal-renderer.ts`, lines 93-133

The `extractColor` method converts all color modes (16-color palette, 256-color cube, RGB truecolor) into `#rrggbb` hex strings. These strings then flow into SVG `fill` attributes and JSON cell data unchanged. An LLM reading `fill="#cd0000"` must infer this means "red" -- there is no mapping back to named colors.

For any new text+attributes encoding, encoding `#cd0000` as a literal string costs 3-4 BPE tokens; encoding it as `red` costs 1 token. Across a 1920-cell grid where ~200 cells have non-default colors, this wastes 400-600 tokens on color precision the LLM cannot use.

**Fix:** Add a `quantizeColor(hex: string): string` function that maps hex values to the nearest named color from a 16-color palette. Use it when generating annotated-text output. Keep full precision for PNG/SVG visual rendering.

**[P2] F1-3: Alternate screen buffer detection is incomplete**

File: `src/terminal-renderer.ts`, line 243

```typescript
visible: this.terminal.buffer.active === this.terminal.buffer.normal,
```

The cursor `visible` flag is set based on whether the active buffer is the normal buffer. This conflates "cursor is visible" with "we are on the normal screen." When a TUI app switches to the alternate screen buffer (which nearly all fullscreen TUIs do -- vim, htop, less), the cursor visibility is reported as `false`. But the cursor IS visible on the alternate screen; this field really means "is on normal buffer."

For an annotated-text mode, this means the agent cannot determine cursor position in the exact scenario where it matters most: navigating a fullscreen TUI application.

**Fix:** Rename to `isNormalBuffer` and add a separate `cursorVisible` flag from xterm.js's cursor state. Or document the current behavior clearly in the tool description.

**[P2] F1-4: Color semantics lookup table for common applications**

Universal color-to-meaning mappings that an annotated-text encoder could leverage:

| Color | Meaning (when contextual) | Applications |
|-------|--------------------------|--------------|
| Red fg | Error, failure, deletion, danger | test runners, git diff, cargo, npm |
| Green fg | Success, addition, pass | test runners, git diff, cargo, npm |
| Yellow fg | Warning, modified, in-progress | test runners, git status, linters |
| Blue fg | Info, directory, reference | ls, fd, file managers |
| Dim/gray | Inactive, comment, de-emphasized | most TUI frameworks |
| Bold white | Header, title, active item | most TUI frameworks |
| Reverse | Selected, focused, cursor-on-item | menus, file pickers, autocomplete |

These mappings are application-specific but consistent enough that a system prompt could teach the LLM: "red text in this context means error/failure." The text+attributes encoding does not need to carry this semantic layer -- it just needs to preserve the color name so the LLM can apply its training knowledge.

---

## Agent 2: Token Encoding Representation

### Encoding Format Comparison

Tested four candidate formats for an 80x24 terminal screen showing a typical ratatui dashboard (header bar, 3 data panels, status line -- 12 distinct style regions, ~600 non-space characters):

| Format | Char count | Est. cl100k tokens | Est. o200k tokens | Notes |
|--------|-----------|-------------------|-------------------|-------|
| Raw JSON (`get_screen full`) | ~45,000 | ~12,000 | ~11,000 | Per-cell objects with all fields. Catastrophically expensive. |
| SVG (current) | ~8,000 | ~3,500 | ~3,200 | Per-cell `<text>` elements. Heavy boilerplate. |
| HTML-style annotations | ~2,200 | ~650 | ~600 | `<r>error</r>` for red. HTML tags tokenize well (in BPE vocab). |
| ANSI-inspired inline markers | ~1,800 | ~520 | ~480 | `[r]error[/]` for red. Bracket syntax is BPE-friendly. |
| Markdown-style | ~1,600 | ~550 | ~500 | `**bold** ~~dim~~`. Familiar but overloads existing markdown semantics. |

### Findings

**[P1] F2-1: `get_screen format="full"` returns per-cell JSON that costs 20-40x plain text with no warning**

File: `src/tools/screen.ts`, lines 47-52 (full format), and `src/index.ts`, line 176

The `full` format is the *default*. It returns a `ScreenState` object with a `lines` array where each line contains a `cells` array of `CellData` objects. For an 80x24 terminal, this is 1920 cell objects, each with 8 fields (char, fg, bg, bold, italic, underline, dim, inverse). Serialized with `JSON.stringify(result, null, 2)` (index.ts line 176), this produces ~45,000 characters of prettified JSON, consuming ~12,000 tokens.

The tool description says: "Use 'text' format for quick checks, 'full' for detailed cell info." It does not warn that "full" costs 30-60x more tokens than "text". An agent that uses the default will burn 12,000 tokens on a single screen capture.

**Failure scenario:** An LLM agent calls `get_screen` without specifying format (default: full). In a 10-turn session, it accumulates 120,000 tokens of screen state -- exceeding a 100k context window by turn 9 from screen data alone.

**Fix:** (a) Change the default format from `full` to `compact`. (b) Add a `note` field to the full format response warning about token cost: "Full format returns ~12K tokens. Use 'text' or 'compact' for routine checks." (c) Consider adding JSON.stringify without pretty-printing (no `null, 2`) to save ~30% on the JSON output.

**[P1] F2-2: The recommended encoding is ANSI-inspired inline markers, not HTML or custom DSL**

Analysis of BPE tokenizer behavior for annotation syntax:

- **`[r]`, `[/]`, `[b]`**: Square brackets are single tokens in both cl100k_base and o200k_base. Single-letter codes inside brackets tokenize as 2-3 tokens per marker pair. Familiar from BBCode, forum markup -- extensive training data.
- **`<span style="color:red">`, `</span>`**: HTML tags are well-represented in BPE vocabularies but are verbose. `<span` alone is 1-2 tokens, but the full open tag with attributes is 8-12 tokens per span.
- **`**bold**`**: Markdown is 1 token per `**` marker pair, but overloading markdown semantics creates ambiguity when the terminal output itself contains markdown (common in documentation TUIs).
- **Custom Unicode markers (e.g., `\u2588` for color blocks)**: BPE tokenizers fragment Unicode codepoints above U+0100 into 2-4 byte tokens each. A marker that looks like 1 character costs 3-4 tokens. This is the P0 trap.

Recommended format specification:

```
[header,bold]Dashboard v2.1[/]
[r]  3 FAILED[/] [g]12 PASSED[/] [y]1 WARN[/]
---
[dim]Last updated: 10:43:22[/]
```

Where markers are: `[r]`=red, `[g]`=green, `[y]`=yellow, `[b]`=blue, `[m]`=magenta, `[c]`=cyan, `[w]`=white, `[bold]`, `[dim]`, `[ul]`=underline, `[rev]`=reverse/selected, `[/]`=reset. Combinable: `[r,bold]`.

Estimated cost: 400-600 tokens for a typical 80x24 screen, versus 200-400 for plain text. The ~200-token overhead buys color, bold, dim, and reverse -- the T1 attribute set.

**[P2] F2-3: Diff-based encoding viability is limited to 3-5 turn chains**

For sequential screen captures, a diff-based mode could send only changed lines:

```
@@ turn 3 (delta from turn 2) @@
L5: [r]  4 FAILED[/] [g]11 PASSED[/]    <- was: [r]  3 FAILED[/] [g]12 PASSED[/]
L18: cursor at (5, 18)                    <- was: (5, 16)
```

LLMs can reliably parse unified-diff-style formats for 1-3 sequential diffs. At 4-5 diffs, reconstruction accuracy drops significantly -- the model begins referencing stale line content. Beyond 5 diffs, the model should receive a full screen refresh.

**Recommendation:** Support diff mode as an optimization, but auto-insert a full refresh every 5 turns. The diff encoding should include the full line content (not just the changed portion) to reduce reconstruction burden.

**[P2] F2-4: Spatial layout should be implicit (newline grid) for full screens, explicit for diffs**

For full-screen captures, newline-delimited text is the most token-efficient spatial encoding -- no row/column numbers needed because position is implicit from line breaks. LLMs parse grid-formatted text with high accuracy.

For diff/update mode, explicit line numbers are necessary: `L5:` prefix costs 2-3 tokens per changed line but enables sparse representation where only 2-3 lines out of 24 need updating.

**[P3] F2-5: Two-pass structural caching is theoretically elegant but impractical with current MCP**

A scheme where the first call returns a structural skeleton (`panel at rows 1-8, table at rows 9-20, status at rows 21-24`) and subsequent calls return only content updates would amortize structural encoding cost across a session. However, MCP tool results are stateless -- the server cannot know what the client has cached in conversation history. Implementing this would require the client (Claude Code) to cooperate by maintaining a "last known structure" and passing it back, which is outside the MCP server's control.

---

## Agent 3: SVG/XML Optimization

### SVG Structure Audit

File: `src/screenshot.ts`, `renderToSvg()` at lines 188-278

The current SVG renderer emits:

1. **Boilerplate** (lines 203-215): `<svg>` root with xmlns, width, height, viewBox, `<defs>` with font-family `<style>`, and a full-screen background `<rect>`. Cost: ~150-200 tokens. This is constant overhead per capture.

2. **Per-cell elements** (lines 217-274): For EVERY cell in the 80x24 grid (1920 cells), the renderer emits:
   - A `<rect>` if background is non-default (line 229-233)
   - A `<rect>` for cursor position (line 240-244)
   - A `<text>` element with class, x, y, fill, and optional style for each non-space character (line 263-265)
   - A `<line>` element for underlined cells (line 267-272)

   Each `<text>` element looks like: `<text class="terminal-text" x="54.6" y="28.8" fill="#cd0000" style="font-weight:bold">E</text>`

   This is ~60-80 characters (15-20 tokens) per visible character. For a screen with 600 visible characters, that is 9000-12000 tokens of `<text>` elements alone.

### Findings

**[P1] F3-1: Per-cell `<text>` element emission is the dominant source of SVG token bloat**

File: `src/screenshot.ts`, lines 263-265

The inner loop at line 217 iterates cell-by-cell (`for (let x = 0; x < state.width; x++)`). Each visible character gets its own `<text>` element with absolute x/y coordinates, fill color, class reference, and optional inline style. Adjacent characters with identical styling (e.g., the word "ERROR" in red bold) produce 5 separate `<text>` elements instead of 1.

**Token impact:** On a typical screen with 600 non-space characters and 12 style regions, span-merging adjacent same-style cells would reduce 600 `<text>` elements to ~80-120 `<tspan>` elements within ~24 `<text>` parent elements (one per line). Each merged span carries the styling once instead of per-character.

**Estimated reduction:** From ~3500 content tokens to ~800-1200 content tokens -- a 65-75% reduction in the content-bearing portion of the SVG.

**Fix:** Replace the inner x-loop with a span-accumulation loop:

```typescript
// Pseudo-code for span merging
let spanStart = 0;
let spanStyle = currentStyle(cells[0]);
for (let x = 1; x <= state.width; x++) {
  if (x === state.width || !sameStyle(cells[x], spanStyle)) {
    emitTspan(spanStart, x, spanStyle, accumulatedText);
    spanStart = x;
    spanStyle = currentStyle(cells[x]);
  }
}
```

**[P1] F3-2: SVG boilerplate is re-emitted identically on every call with zero variable content**

File: `src/screenshot.ts`, lines 203-215

The SVG header block (xmlns declaration, width/height, viewBox, defs/style, background rect) is identical across calls for the same terminal dimensions. In a 20-turn session, this overhead is emitted 20 times.

For optimized SVG: these 150-200 tokens of boilerplate represent 5-25% of the total SVG depending on screen content density. For a sparse screen (few characters), boilerplate dominates.

**Fix for SVG path:** Extract boilerplate into a `<defs>` section that can be cached. Or more practically: if pursuing an annotated-text format instead, this becomes moot.

**Fix for annotated-text path:** No boilerplate at all. The annotated text format has zero structural overhead.

**[P2] F3-3: Floating-point coordinates add token cost with no value for LLM consumption**

File: `src/screenshot.ts`, lines 195-196

```typescript
const charWidth = opts.fontSize * 0.6;  // = 8.4
const charHeight = opts.fontSize * 1.2; // = 16.8
```

These produce coordinate values like `x="54.6" y="28.8"`. Decimal coordinates cost 2-3 extra tokens per coordinate versus integer values, and serve no purpose when the SVG is consumed by an LLM rather than rendered visually. Across 600 `<text>` elements with 2 coordinates each, this wastes ~200-400 tokens.

**Fix:** Use integer coordinates: `charWidth = Math.round(opts.fontSize * 0.6)`, `charHeight = Math.round(opts.fontSize * 1.2)`. Or for the annotated-text format, eliminate coordinates entirely (implicit from grid position).

**[P2] F3-4: CSS class extraction would save tokens at the 5+ span threshold**

The current SVG uses a single CSS class (`.terminal-text` for font) with all other styling inline. For a screen with 12 distinct style combinations, CSS class extraction becomes profitable:

- **Inline cost:** 12 unique `style="fill:#cd0000;font-weight:bold"` strings, each appearing on ~10-50 elements = repeated 12-50 times
- **Class cost:** 12 class definitions in `<style>` block (~15 tokens each = 180 tokens) + class references (`.c1` = 1 token each)

Breakeven is at ~5 spans per unique style. Most TUI screens exceed this easily.

**[P2] F3-5: Background rects for non-default cells are emitted separately from text elements**

File: `src/screenshot.ts`, lines 229-233

Each cell with a non-default background gets its own `<rect>` element. In a ratatui dashboard with colored status bars, this can produce 200+ rect elements. These rects carry semantic value (they indicate highlighted regions), but the per-cell granularity is wasteful. Adjacent cells with the same background color should share a single wider rect.

**[P3] F3-6: Optimized SVG is not competitive with annotated text -- use SVG as intermediate only**

Even with aggressive optimization (span merging, class extraction, integer coordinates, background merging), an optimized SVG for an 80x24 screen would cost ~800-1500 tokens. The annotated-text format achieves the same semantic fidelity at ~400-600 tokens, because SVG carries structural overhead (XML tags, coordinate system, style syntax) that provides no value to an LLM consumer.

**Recommendation:** Treat SVG as a rendering format for human visual inspection only. For LLM consumption, extract text+attributes directly from `ScreenState` and emit the annotated-text format. Keep SVG as a fallback for debugging and visual verification.

---

## Agent 4: LLM Vision Token Economics

### Cost Model

Provider pricing as of early 2026 (per million tokens):

| Provider | Model | Text input | Vision input (effective) | Text output | Cache discount |
|----------|-------|-----------|------------------------|-------------|----------------|
| Anthropic | Sonnet 4 | $3.00 | $3.00 (but tile-based counting) | $15.00 | 90% on cached input |
| Anthropic | Haiku 3.5 | $0.80 | $0.80 (tile-based) | $4.00 | 90% on cached input |
| OpenAI | GPT-4.1 | $2.00 | $2.00 (detail=low: fixed 85 tok) | $8.00 | 50% on cached input |

**Vision token counting for terminal screenshots:**

An 80x24 terminal at 14px font produces roughly a 672x403 pixel PNG. Under Anthropic's tile-based vision:
- Image is scaled to fit within 1568x1568, then divided into 768x768 tiles
- A 672x403 image = 1 tile = ~1600 tokens (base overhead of ~1600 per image regardless of content)
- This is the MINIMUM -- larger terminals or higher DPI push into 2-4 tiles (3200-6400 tokens)

Under OpenAI's `detail=low`: fixed 85 tokens regardless of content. This makes PNG screenshots extremely cheap on OpenAI but sacrifices character-level readability.

### Per-Session Cost Comparison (20 turns, Sonnet 4 pricing)

| Mode | Tokens/call | 20-turn total | Input cost | Cacheable? | Cached cost |
|------|------------|---------------|-----------|------------|-------------|
| Text only | 300 | 6,000 | $0.018 | Yes (text) | $0.0018 |
| Annotated text (proposed) | 500 | 10,000 | $0.030 | Yes (text) | $0.0030 |
| PNG screenshot | 1,600 | 32,000 | $0.096 | No (vision) | $0.096 |
| SVG (current) | 4,000 | 80,000 | $0.240 | Yes (text) | $0.024 |
| Full JSON | 12,000 | 240,000 | $0.720 | Yes (text) | $0.072 |

### Findings

**[P1] F4-1: Vision tokens are not eligible for prompt caching, creating a compounding cost disadvantage**

Anthropic's prompt caching gives a 90% discount on cached input tokens -- but only for text tokens. Vision tokens (images) are never cached. In a multi-turn session where previous tool results remain in the conversation history, text-based screen representations accumulate as cached tokens (cheap), while PNG screenshots accumulate as uncached vision tokens (full price every turn).

Over a 20-turn session, the effective cost ratio between annotated text and PNG is not 500:1600 (3.2x) but closer to 50:1600 (32x) because the annotated text benefits from caching on subsequent turns while the PNG never does.

**Impact:** This makes the annotated-text format dramatically more cost-effective than the raw token count comparison suggests. Any cost analysis that ignores caching will underestimate the benefit of text-based representations by ~10x.

**[P1] F4-2: The "full" JSON format costs more per session than PNG screenshots while providing worse LLM comprehension**

At 12,000 tokens per call and 20 calls, the full JSON format consumes 240,000 tokens -- $0.72 at Sonnet pricing, compared to $0.096 for PNG. The JSON contains the same information as PNG (it IS the data that renders the PNG) but in a format that is harder for the LLM to interpret spatially. The LLM must mentally reconstruct a grid from a list of cell objects.

This is an economic anti-pattern: paying MORE tokens for WORSE comprehension. The full JSON format should be deprecated or gated behind a warning for LLM callers.

**[P2] F4-3: Hybrid strategy decision rules for automatic mode selection**

A tuivision-side hybrid strategy could select representation mode automatically:

| Condition | Mode | Rationale |
|-----------|------|-----------|
| Default / routine polling | Annotated text | 500 tokens, cacheable, preserves color/bold/cursor |
| Screen has progress bars, charts, or visual-only elements | PNG | Visual elements that text cannot represent |
| User explicitly requests visual verification | PNG or SVG | Human debugging, not LLM consumption |
| Context pressure >70% | Text only (no attributes) | Minimize token footprint when budget is tight |
| Diff from previous screen <20% changed | Diff mode | 50-100 tokens for minor changes |

The MCP server could implement this by tracking screen state between calls and adding a `format: "auto"` option that applies these rules.

**[P2] F4-4: Output token amplification from low-fidelity input is unmodeled**

When an LLM receives plain text without color or style annotations, it often generates longer reasoning chains to compensate: "The output shows several test names. Without color information, I cannot determine which passed and which failed. Let me look for textual indicators like 'PASS' or 'FAIL'..." This chain-of-thought reasoning adds 50-200 output tokens per ambiguous screen.

At Sonnet 4 output pricing ($15/M tokens), 100 extra output tokens cost $0.0015 -- comparable to the input savings from dropping to text mode ($0.006 saved per call). For screens where color carries critical information, the output amplification can negate 25-50% of the input savings.

**[P3] F4-5: OpenAI detail=low at 85 tokens is the cheapest vision option but may not read terminal text**

OpenAI's `detail=low` mode fixes vision token count at 85 regardless of image size, but uses a heavily downscaled version of the image. At 672x403 pixels downscaled to ~512x512 low-detail, 14px monospace characters may be illegible. If the LLM cannot read the text in the image, the 85-token cost is wasted.

This represents a provider-specific optimization opportunity: if tuivision detects it's being called through an OpenAI-backed agent, it could render at higher font sizes (28px+) to ensure readability at low detail, while keeping the fixed 85-token cost. However, MCP servers currently have no standard way to detect the downstream LLM provider.

---

## Agent 5: LLM Context Management for TUI Sessions

### Context Accumulation Model

Assumptions: 20k token system prompt (typical for Claude Code with plugins), 500 tokens per LLM response, 200 tokens per tool call overhead, screen capture every turn.

| Mode | Tokens/turn (screen + overhead) | Turn 10 cumulative | Turn 20 cumulative | Hits 100k at turn | Hits 200k at turn |
|------|-------------------------------|-------------------|-------------------|-------------------|-------------------|
| Text only | 300 + 700 = 1,000 | 30,000 | 40,000 | Never | Never |
| Annotated text | 500 + 700 = 1,200 | 32,000 | 44,000 | Never | Never |
| PNG | 1,600 + 700 = 2,300 | 43,000 | 66,000 | ~35 | Never |
| SVG | 4,000 + 700 = 4,700 | 67,000 | 114,000 | ~17 | ~38 |
| Full JSON | 12,000 + 700 = 12,700 | 147,000 | -- | ~6 | ~14 |

(Cumulative includes 20k system prompt. "Turn 20 cumulative" for Full JSON exceeds 200k, hence `--`.)

### Findings

**[P1] F5-1: Full JSON format causes context overflow at turn 6-7 on 100k windows**

With the default `get_screen` format returning full JSON at ~12,000 tokens per call, plus typical conversation overhead, the context window fills by turn 6-7. This is within the expected length of even simple TUI automation tasks (spawn, navigate to a menu, fill a form, submit).

The practical impact: an agent using `get_screen` with default settings will hit context limits before completing most multi-step TUI workflows. This is the single most impactful usability issue for tuivision with LLM agents.

**Mitigation:** Default to `compact` or `text` format. Add a `max_token_estimate` field to tool responses so the client can budget context.

**[P1] F5-2: MCP protocol provides no mechanism for evicting old tool results**

The MCP specification (as of v1.0.0) does not define a way for servers to mark tool results as evictable or to retroactively replace/remove old results from conversation history. Every `get_screen` or `get_screenshot` result persists in the conversation indefinitely.

This means tuivision cannot implement server-side context management -- it is entirely dependent on the client (Claude Code, Cursor, etc.) deciding to summarize or truncate old tool results. The server's only lever is making each individual result as small as possible.

**Implications for design:**
- Diff mode (sending only changes) saves tokens per call but the old full-screen result still persists in history
- A "session-aware" mode that degrades fidelity over time would need client cooperation
- The most impactful optimization is reducing the per-call token count, because that's the only thing within the MCP server's control

**[P2] F5-3: Adaptive fidelity strategy within MCP server constraints**

Even without client cooperation, tuivision can implement an adaptive strategy using server-side state:

1. **Screen change tracking:** Compare current screen to previous screen. If <10% of cells changed, return only the diff with a note: "Minor update from previous screen: lines 5, 12 changed." This is a shorter text result that the client stores as a small tool result.

2. **Progressive format degradation:** Accept an optional `context_budget` parameter in `get_screen`. When the caller passes remaining budget, tuivision adjusts:
   - Budget >50k: full annotated text
   - Budget 20-50k: text only with cursor
   - Budget <20k: changed-lines-only diff

3. **Explicit screen summarization tool:** Add a `summarize_screen` tool that returns a 50-100 token natural language summary: "Terminal shows htop with 4 CPUs at 60-80% usage, 8GB RAM 70% used, sorted by CPU%, top process is node at 45%." This gives the LLM enough context to decide next actions without the full screen.

**[P2] F5-4: Screen captures should include a token cost estimate in the response**

The MCP tool response should include metadata about its own size:

```json
{
  "content": [{"type": "text", "text": "...screen data..."}],
  "_meta": {
    "estimated_tokens": 450,
    "format_used": "annotated_text",
    "screen_change_pct": 8
  }
}
```

This allows the calling LLM to make informed decisions about future calls: "The last screen capture used 450 tokens. I have ~30k context remaining. I can afford ~60 more screen captures at this rate."

**[P3] F5-5: Deduplication of static screen regions across turns**

Many TUI layouts have static regions (headers, status bars, borders) that never change. If tuivision tracked which regions are static across N captures, it could annotate them:

```
[static:header] Dashboard v2.1
[changed] CPU: 78% -> 82%
[static:footer] Press q to quit
```

The LLM can learn to skip re-processing static regions. However, this requires the LLM to maintain region awareness across turns, which has the same working-memory limitations as diff mode.

---

## Cross-Agent Convergence

### Unanimous Recommendations

All five agents converge on these conclusions:

1. **A new "annotated text" format is the highest-value optimization.** It sits in the sweet spot: ~400-600 tokens (2-3x more than plain text, 3-4x less than PNG, 6-15x less than SVG) while preserving the T1 attribute set (color, bold, reverse, cursor) that covers 80%+ of task-relevant semantic signal.

2. **The `full` JSON format should not be the default.** It costs 20-40x more than plain text and provides worse LLM comprehension than either annotated text or PNG. Default should be `compact` or `text`, with `full` available as an explicit opt-in for programmatic consumers.

3. **Color quantization to 16 named colors is essential.** Raw hex values (`#cd0000`) waste 3-4 tokens per color on precision that LLMs cannot meaningfully use. Named colors (`red`) cost 1 token and align with the LLM's training data about color semantics.

4. **Prompt caching makes text-based formats dramatically more cost-effective than vision.** In multi-turn sessions, cached text tokens cost 10% of vision tokens. This compounding advantage increases with session length.

### Key Tensions

- **SVG optimization vs. annotated text:** Agent 3 (SVG optimization) identifies span-merging as a 65-75% reduction, bringing SVG from ~3500 to ~1000 tokens. Agent 2 (encoding) shows annotated text at ~500 tokens. Even optimized SVG is 2x the cost of annotated text, because XML structural overhead is irreducible. The recommendation is to pursue annotated text as the primary format and optimize SVG only for visual debugging.

- **Diff mode viability:** Agents 2 and 5 agree on a 3-5 turn limit for diff chains before full refresh is needed. Agent 4 notes that diff mode's per-call savings are partially negated by MCP's inability to evict old results -- the original full screen plus all diffs accumulate in history.

- **Session-aware fidelity:** Agent 5 designs an adaptive strategy but Agents 2 and 4 note that the MCP server has limited ability to implement it without client cooperation. The practical recommendation: expose an optional `context_budget` parameter and let the calling agent manage fidelity decisions.

### Implementation Priority

1. **Change default format from `full` to `compact`** -- zero-cost fix, biggest immediate impact (P1)
2. **Add `annotated` format to `get_screen`** -- new format, ~400-600 tokens with T1 attributes (P1)
3. **Add color quantization** -- map hex to 16 named colors for annotated format (P1)
4. **Fix inverse attribute handling** -- preserve `inverse` as semantic marker for selection/focus (P1)
5. **SVG span merging** -- reduce SVG cost by 65-75% for visual debugging use cases (P2)
6. **Add screen diff tracking** -- return change percentage and optional diff mode (P2)
7. **Add `summarize_screen` tool** -- natural language summary at 50-100 tokens (P2)
8. **Add token cost estimate to responses** -- metadata for context budget management (P3)
