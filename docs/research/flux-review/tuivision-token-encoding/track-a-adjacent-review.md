# Track A (Adjacent) Review: Tuivision Token-Efficient Terminal State Encoding

**Brainstorm:** `docs/brainstorms/2026-04-03-tuivision-token-encoding-brainstorm.md`
**Bead:** sylveste-sn7
**Date:** 2026-04-02
**Track:** Adjacent (domain-expert findings requiring specialist knowledge)

## Summary

| Severity | Count |
|----------|-------|
| P0       | 1     |
| P1       | 4     |
| P2       | 5     |
| P3       | 3     |
| **Total** | **13** |

---

## [P0] Unsafe internal API usage for cell color extraction will break on xterm.js minor updates

**Agent:** fd-xterm-headless-renderer-architecture

**Finding:** The current `getScreenState()` at `terminal-renderer.ts:208` casts the cell to `unknown` and reads `.fg` and `.bg` as raw numeric properties. This bypasses the public `IBufferCell` API entirely.

**Evidence:** At `terminal-renderer.ts:208`:
```typescript
const cellAny = cell as unknown as { fg: number; bg: number };
const fg = this.extractColor(cellAny.fg, "#ffffff");
const bg = this.extractColor(cellAny.bg, "#000000");
```
The `IBufferCell` interface in `@xterm/headless` v5.5.0 exposes `getFgColor()`, `getBgColor()`, and `getFgColorMode()` / `getBgColorMode()` as the stable public API for reading cell colors. The raw `.fg` and `.bg` numeric properties are internal implementation details of the `CellData` class. The brainstorm proposes building `getAnnotatedText()` on top of the same buffer traversal pattern, which means the new method would inherit this fragility. Any xterm.js minor version bump that changes the internal bit layout of the packed fg/bg integer will silently produce wrong colors in both `getScreenState()` and the new `getAnnotatedText()`, with no compile-time or runtime error.

**Recommendation:** Refactor `extractColor()` to use the public API: `cell.getFgColorMode()` to determine the color space (0=default, 1=16-color, 2=256-color, 3=truecolor), then `cell.getFgColor()` for the value. This is a prerequisite for child .1, not a separate task -- the annotated format should not be built on an internal API that has already been identified as fragile. The refactor is ~15 lines and eliminates the `as unknown` cast entirely.

---

## [P1] Default format change from `full` to `compact` silently breaks structured-output consumers

**Agent:** fd-mcp-tool-api-breaking-change

**Finding:** The brainstorm (child .2) proposes changing the default from `full` to `compact` and describes it as "low risk." The actual blast radius is larger than acknowledged. The `get_screen` tool is registered in `index.ts:165` with a fallback `?? "full"`, and the Zod schema in `screen.ts:9-10` has `.default("full")`. Any MCP client that calls `get_screen` without specifying `format` currently receives a `ScreenState` JSON object containing `width`, `height`, `cursor`, and `lines[]` with per-cell `CellData`. After the default change to `compact`, the same call receives a `CompactScreenState` with only `width`, `height`, `cursor`, and a flat `text` string. The `lines` array and all `CellData` disappear.

**Evidence:** The tool's own SKILL.md at line 147 instructs agents: "Use `get_screen format="full"` to verify color/attribute rendering." But the tool description at `index.ts:152` says "Use 'text' format for quick checks, 'full' for detailed cell info" without mentioning what the default is. An agent following the tool description alone and omitting the format parameter gets `full` today and `compact` tomorrow. The `getScreen()` return type in `screen.ts:28` is a union (`ScreenState | CompactScreenState | string`) -- downstream callers that destructure `.lines` from the result will hit a runtime TypeError after the default changes.

**Recommendation:** Instead of changing the default, add `annotated` as a new format and update the tool description at `index.ts:152` to recommend it: "Use 'annotated' for efficient color-aware output, 'text' for quick checks, 'full' for raw cell data." If the default must change, gate it behind a semver major bump (tuivision v1.0.0) and emit a deprecation notice in the `full`-format response for one release cycle first. At minimum, add `format` to the schema description's first sentence so agents see it before making their first call.

---

## [P1] Token cost claim of "2-3 tokens per marker pair" is unvalidated and likely understated for dense screens

**Agent:** fd-bpe-marker-tokenization

**Finding:** The brainstorm's core economic argument rests on `[r]...[/]` costing "2-3 tokens per marker pair." This was reportedly benchmarked against cl100k and Claude's BPE tokenizer, but no tokenization table is provided. In cl100k_base, `[r]` tokenizes as 2 tokens (`[r` + `]`) and `[/]` as 2 tokens (`[/` + `]`), giving 4 tokens per marker pair, not 2-3. With attribute content like `[r fg=red]`, the sequence tokenizes to approximately 5-6 tokens (`[r`, ` fg`, `=red`, `]`). The brainstorm targets 400-600 tokens for an 80x24 screen, but a realistic terminal screen (vim with syntax highlighting, htop) has 100-300 styled runs. At 4 tokens per bare marker pair, markers alone consume 400-1200 tokens before any text content.

**Evidence:** Brainstorm section "Format choice" claims "[r]...[/] -- 2-3 tokens per marker pair (winner)." This is the only quantitative justification for choosing this format over alternatives. The brainstorm does not include a tokenization table or worked example with a real screen. The 400-600 token target is stated as a design goal but the arithmetic of (number of styled runs * tokens per marker pair + text tokens) is never shown.

**Recommendation:** Before committing to the `[r]...[/]` format in child .1, run an actual tokenization benchmark: capture a real htop and vim screen via `getScreenState()`, generate the annotated output, and tokenize it with `tiktoken` for cl100k_base and a SentencePiece estimator for Claude. If the total exceeds 800 tokens, evaluate single-character markers (e.g., using `|r|` or bare ANSI-inspired `\x1b[31m`-like abbreviations that may tokenize more favorably). The benchmark should be a one-hour task and determines whether the entire approach is viable.

---

## [P1] Inverse preservation (child .4) has limited effectiveness -- most TUI frameworks do not set SGR 7 for selection

**Agent:** fd-inverse-video-selection-semantics

**Finding:** The brainstorm frames child .4 as fixing "semantic loss" where `terminal-renderer.ts:220-223` pre-resolves inverse by swapping fg/bg. However, the majority of production TUI applications do not use SGR 7 (the terminal-level inverse attribute) for selection. Ratatui's default `Style::default().add_modifier(Modifier::REVERSED)` does set SGR 7, but its `highlight_style()` with explicit fg/bg colors (used by most production apps) does not. Bubbletea's `lipgloss.NewStyle().Reverse(true)` sets SGR 7, but `lipgloss.NewStyle().Foreground(color).Background(color)` (used for custom themes) does not. Ncurses `A_REVERSE` sets SGR 7, but applications using `COLOR_PAIR()` with explicit colors simulate inverse visually without setting the attribute. Blessed's `inverse: true` style sets SGR 7, but `{fg: 'black', bg: 'white'}` does not.

The result is that the `[I]` marker will fire for default-styled selections in some frameworks but miss the majority of customized selections. This makes the marker unreliable as a selection signal.

**Evidence:** The brainstorm states: "Current code at terminal-renderer.ts:220-223 swaps fg/bg when inverse is true, destroying the semantic signal." The actual code at lines 220-222:
```typescript
fg: inverse ? bg : fg,
bg: inverse ? fg : bg,
```
This pre-resolves but preserves `inverse: true` in the output struct (line 227). The pre-resolution affects `getScreenState()` consumers (the `full` format) and the SVG/PNG renderers which read from the struct. For the annotated format, the fix would emit original colors + `[I]`, but the signal is only present when the application explicitly set SGR 7.

**Recommendation:** Retain the inverse preservation fix (it is correct for the cases where it fires), but do not frame it as solving the selection detection problem in the brainstorm or documentation. Document that `[I]` indicates SGR 7 inverse, not application-level selection. Consider deferring child .4 from the MVP 5-child scope if the implementation effort competes with higher-impact children, since its coverage of real-world selection patterns is partial.

---

## [P1] Color quantization to 16 names assumes xterm default palette but the renderer hardcodes non-standard RGB values

**Agent:** fd-color-quantization-palette

**Finding:** The brainstorm (child .3) proposes mapping "all hex/256/truecolor to 16 named colors" using the xterm default palette as centroids. However, `terminal-renderer.ts:34-51` hardcodes a `DEFAULT_COLORS` array whose values do not match the xterm default palette exactly. For example, index 4 (Blue) is `#0000ee` and index 12 (Bright Blue) is `#5c5cff`. These are the classic xterm defaults, but many terminal emulators (and all themed terminals) override these. The quantization problem is that a cell with truecolor `#268bd2` (Solarized blue) will be nearest-neighbor matched against these hardcoded centroids. In RGB Euclidean distance, `#268bd2` is closer to `#00cdcd` (Cyan, index 6) than to `#0000ee` (Blue, index 4), so the quantizer would output `cyan` instead of `blue` -- semantically incorrect for any application using Solarized's blue to mean "directory" or "link."

**Evidence:** `DEFAULT_COLORS` at `terminal-renderer.ts:34-51` defines the centroid positions. The quantization helper (not yet implemented) will map arbitrary hex to the nearest of these 16 entries. The brainstorm acknowledges "truecolor applications (e.g., image viewers, color pickers) will lose fidelity" but does not address the more common case of themed terminals where the palette is non-standard.

**Recommendation:** For mode 1 (16-color palette) and mode 2 (256-color palette indices 0-15), use the palette index directly -- the terminal told us "this is color 4 (blue)" and that is the correct semantic label regardless of the RGB value. Only apply nearest-neighbor quantization for mode 2 indices 16-255 and mode 3 (truecolor). For truecolor, consider CIELAB distance instead of RGB Euclidean distance. This distinction between "the terminal said blue" and "this hex value looks closest to blue" is the difference between a correct and an incorrect quantizer.

---

## [P2] Wide characters (CJK, emoji) will produce doubled markers in annotated output

**Agent:** fd-xterm-headless-renderer-architecture

**Finding:** xterm.js represents wide characters (CJK, emoji) as a primary cell with `getWidth() === 2` followed by a continuation cell with `getWidth() === 0` and empty `getChars()`. The current `getScreenState()` at `terminal-renderer.ts:186-229` iterates every column `x` from 0 to `_cols` and emits a `CellData` for each, including the continuation cell (which gets `char: " "` because `getChars()` returns empty). The brainstorm's proposed `getAnnotatedText()` using run-length encoding on styled cells needs to handle continuation cells: if not skipped, each wide character produces a marker for the primary cell and a separate marker (or inclusion in the next run) for the invisible continuation cell.

**Evidence:** `terminal-renderer.ts:203`: `const char = cell.getChars() || " ";` -- continuation cells get `" "` as their character. The brainstorm does not mention wide character handling. A CJK-heavy TUI (e.g., a Japanese file manager) would have ~40 wide characters per line, each producing an extra space character in the annotated output, inflating text content and potentially splitting styled runs incorrectly.

**Recommendation:** In `getAnnotatedText()`, check `cell.getWidth()` (available via the public `IBufferCell` API). Skip cells where `getWidth() === 0` (continuation cells). This is a single `if` guard in the inner loop and must be specified in child .1's implementation plan.

---

## [P2] Three buffer traversal methods with no shared abstraction create maintenance risk

**Agent:** fd-xterm-headless-renderer-architecture

**Finding:** The brainstorm proposes adding `getAnnotatedText()` "alongside existing `getScreenText()` and `getScreenState()`." Currently, `getScreenText()` calls `getScreenState()` and maps the result (`terminal-renderer.ts:252-254`), so there are effectively two traversal paths: one full traversal in `getScreenState()` and the alias in `getScreenText()`. Adding `getAnnotatedText()` as a third method that reads the raw buffer independently creates a second full traversal with its own cell iteration logic. Any bug fix to cell handling (e.g., the wide character fix above, the internal API fix in P0) must be applied in two places.

**Evidence:** `getScreenText()` at line 253 delegates to `getScreenState()`. The brainstorm says "Add `getAnnotatedText()` alongside existing `getScreenText()` and `getScreenState()`" and "~150 new lines." If `getAnnotatedText()` reads from the raw xterm.js buffer independently, cell attribute extraction (bold, italic, inverse, color) will be duplicated from `getScreenState()`.

**Recommendation:** Have `getAnnotatedText()` build on the `ScreenState` output from `getScreenState()`, iterating over `LineData[]` rather than the raw buffer. This is slightly less efficient (two passes: one to build the struct, one to format it) but eliminates code duplication. The performance cost is negligible for 80x24 (1920 cells). If performance for large terminals (220x50) becomes a concern, extract a shared `forEachCell(callback)` iterator that both methods use.

---

## [P2] SVG span-merging (child .5) is an undocumented breaking change to `get_screenshot` output

**Agent:** fd-mcp-tool-api-breaking-change

**Finding:** The brainstorm proposes child .5 to "replace the existing SVG output" with span-merged SVG. The current SVG at `screenshot.ts:217-274` emits one `<text>` element per cell with exact `x` and `y` coordinates. Span-merging would change this to one `<text>` element per styled run, altering both the element count and the coordinate structure. Any consumer that parses SVG by counting `<text>` elements, selecting by exact coordinates, or using CSS selectors on the per-cell structure will silently break.

**Evidence:** The brainstorm says "The per-cell format has no advantages" and proposes replacing it. `screenshot.ts:263`:
```typescript
`<text class="terminal-text" x="${xPos}" y="${textY}" fill="${cell.fg}"${styleAttr}>${char}</text>`
```
After span-merging, the `x` attribute would point to the run start, not each cell. The brainstorm does not propose a format flag or version bump for this change.

**Recommendation:** Add a `svg_mode` parameter to `get_screenshot` with values `per_cell` (current default) and `merged` (new optimization). This avoids breaking existing consumers while letting new callers opt into the cheaper format. Alternatively, if the per-cell format truly has zero consumers (verify by auditing test fixtures and skill documentation), ship it as a semver minor with a changelog entry.

---

## [P2] Prompt caching asymmetry undermines the cost analysis

**Agent:** fd-llm-vision-token-economics

**Finding:** The brainstorm states "Anthropic's prompt caching gives 90% discount on text tokens but 0% on vision tokens." This is the correct directional claim, but the cost analysis does not account for the fact that the annotated format's text changes on every `get_screen` call (cursor position varies, content updates). Changing text in the MCP tool response breaks the prompt cache prefix for all subsequent tokens. In a 20-turn agent session, each annotated response invalidates the cache suffix, meaning the 90% text discount applies only to the static system prompt prefix, not to the screen capture itself. The effective savings over cached vision (where a static PNG reference can be cached) may be smaller than the brainstorm suggests.

**Evidence:** Brainstorm "Why This Approach" section: "prompt caching gives 90% discount on text tokens but 0% on vision tokens. A 10-turn agent session using PNG screenshots costs 10-32x more than equivalent annotated text." This comparison assumes the annotated text benefits from caching, but tool responses in the conversation turn are not cacheable at the same rate as the system prompt.

**Recommendation:** Add a note to the brainstorm acknowledging that per-call text is not cache-eligible in the same way as system prompt text. The cost advantage of annotated over PNG is still real (text input tokens are cheaper than vision tokens at base rate), but the 10-32x multiplier should be recalculated using base input token pricing for both, not cached-text vs uncached-vision.

---

## [P2] `include_roles: true` parameter design needs schema specification before implementation

**Agent:** fd-mcp-tool-api-breaking-change

**Finding:** The brainstorm mentions `include_roles: true` as an optional parameter for the annotated format but does not specify where it lives in the schema. It could be: (a) a top-level parameter on `get_screen`, (b) a sub-parameter only valid when `format: "annotated"`, or (c) a separate parameter that works across formats. The current Zod schema in `screen.ts:5-14` has no conditional validation -- adding a parameter that only applies to one format variant creates a confusing API where `include_roles: true` combined with `format: "text"` is silently ignored.

**Evidence:** Brainstorm: "Optional `include_roles: true` parameter appends ARIA-inspired semantic role attributes." The current schema pattern at `screen.ts:7-13` uses a flat `z.object()` with `.optional()` parameters. Zod does support discriminated unions but the existing schema does not use them.

**Recommendation:** Add `include_roles` as a top-level `.optional().default(false)` parameter with a description that explicitly states it only affects the `annotated` format. Silently ignoring it for other formats is acceptable and consistent with how `font_size` in `get_screenshot` is ignored for PNG metadata. Document this in the tool description string.

---

## [P3] Color name vocabulary should be validated against BPE tokenization cost

**Agent:** fd-bpe-marker-tokenization

**Finding:** The quantization output uses named colors like `red`, `green`, `blue`, `cyan`, `magenta`, `yellow`, `white`, `black`, and their `bright_` prefixed variants. Single-word color names (`red`, `green`, `blue`) are each a single BPE token in both cl100k_base and Claude's tokenizer. However, compound names like `bright_cyan` and `bright_magenta` tokenize as 2-3 tokens (`bright`, `_`, `cyan`). Since color names appear inside markers (`[r fg=bright_cyan]`), compound names inflate marker cost.

**Evidence:** The brainstorm claims color quantization will "save 400-600 tokens/screen" by eliminating hex strings. Hex colors like `#cd00cd` tokenize as 3-4 tokens. A compound name like `bright_magenta` also tokenizes as 3 tokens. The savings come from replacing hex with single-word names, not compound names.

**Recommendation:** Use single-character abbreviations for the 16 colors in the marker syntax: `r` (red), `g` (green), `b` (blue), `c` (cyan), `m` (magenta), `y` (yellow), `w` (white), `k` (black), and `R`, `G`, `B`, `C`, `M`, `Y`, `W`, `K` for bright variants. This reduces every color name to 1 token. Include a legend line at the top of the annotated output so agents can decode abbreviations. Alternatively, if readability is preferred over maximum compression, keep full names but use `bred`, `bgrn`, `bblu` 4-character abbreviations that each tokenize as a single token.

---

## [P3] `getScreenText()` calls `getScreenState()` unnecessarily for the `compact` format path

**Agent:** fd-xterm-headless-renderer-architecture

**Finding:** The `compact` format in `screen.ts:39-47` calls `getScreenState()` (full cell traversal with color extraction) to get `state.cursor`, then separately calls `getScreenText()` which internally calls `getScreenState()` again. This means the compact format traverses the buffer twice. For an 80x24 terminal this is negligible, but it indicates a pattern where adding `annotated` as a fourth format will compound traversal overhead.

**Evidence:** `screen.ts:40`: `const state = session.renderer.getScreenState();` followed by `screen.ts:45`: `text: session.renderer.getScreenText()`, where `getScreenText()` at `terminal-renderer.ts:253` calls `this.getScreenState()` again.

**Recommendation:** For the `compact` case, use the already-computed `state` to derive text: `text: state.lines.map(l => l.text).join("\n")` instead of calling `getScreenText()`. This is a one-line fix. More importantly, when implementing the `annotated` format, build it from the `ScreenState` struct returned by a single `getScreenState()` call rather than re-traversing the buffer.

---

## [P3] SVG token reduction estimate of "65-75% of SVG token budget" lacks measurement

**Agent:** fd-llm-vision-token-economics

**Finding:** The brainstorm claims per-cell `<text>` elements "waste 65-75% of SVG token budget." This is plausible but unvalidated. The actual SVG overhead per cell includes the tag structure (`<text class="terminal-text" x="..." y="..." fill="...">c</text>`) which is ~80-90 characters per cell. For an 80x24 screen with 50% non-space cells (~960 cells), this is ~80KB of SVG. Span-merging groups consecutive same-styled cells, reducing element count by the average run length. The savings depend heavily on the terminal content: a plain text file in vim has long runs (high savings); htop with per-cell coloring has short runs (low savings).

**Evidence:** Brainstorm child .5: "Per-cell `<text>` elements waste 65-75% of SVG token budget." `screenshot.ts:263` shows the per-cell SVG template. The brainstorm claims span-merging "reduces SVG from ~5000 to ~800-1500 tokens" but provides no measurement.

**Recommendation:** Generate SVG for 3 representative screens (vim, htop, empty terminal), tokenize each, then simulate span-merging and tokenize the result. Include the benchmark in the child .5 implementation plan to set accurate expectations for the optimization's yield across different content types.
