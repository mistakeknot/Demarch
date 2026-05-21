# Track B — Orthogonal Disciplines: tuivision Token Optimization

**Review date:** 2026-04-02
**Track:** B — Orthogonal professional disciplines
**Topic:** Creative approaches to give LLMs rich terminal state information (text + visual semantics) at minimal token cost
**Agents:** fd-medical-imaging-compression · fd-accessibility-screen-reader · fd-game-rendering-lod · fd-wire-protocol-serialization

---

## Context

tuivision is an MCP server for TUI automation ("Playwright for TUIs"). It exposes three capture modes:

| Mode | File | Cost |
|------|------|------|
| `get_screen text` | `src/tools/screen.ts` | ~200–400 tokens, no color/style |
| `get_screenshot png` | `src/tools/screenshot.ts` | ~1600 vision tokens |
| `get_screenshot svg` | `src/screenshot.ts:renderToSvg()` | ~2000–8000 tokens naive |

The core data structure is `ScreenState` (`src/terminal-renderer.ts`): a 2D grid of `CellData` objects, each carrying `char`, `fg`, `bg`, `bold`, `italic`, `underline`, `dim`, `inverse`. The full state for an 80×24 terminal is 1920 cells.

The three modes represent a hard tradeoff: text is cheap but blind; PNG is rich but vision-only; SVG is verbose but LLM-parseable. The gap between cheap-and-blind and rich-and-expensive is where all four orthogonal disciplines converge.

---

## Agent 1 — fd-medical-imaging-compression
*Medical imaging informaticist: DICOM, lossy compression, region-of-interest encoding*

**Decision lens:** Would the LLM make the same decision from the compressed terminal state as from the full one?

### Finding 1.1 — No region-of-interest (ROI) encoding [P1]

**What medical imaging does:** DICOM supports JPEG 2000 ROI encoding (ISO 15444-2). Radiologists mark diagnostically significant regions — tumors, lesion margins — and the codec allocates bit budget there first. Background tissue is aggressively compressed. A chest X-ray compressed 40:1 is clinically lossless because the lungs get almost all the bits.

**What tuivision does today:** `getScreenState()` in `terminal-renderer.ts` iterates all 1920 cells identically (lines 172–246). Every cell — active dialog, static border, empty padding — gets the same treatment. `getScreenText()` linearizes the result with no weighting.

**The terminal ROI problem:** Most TUI screens are predominantly static chrome: menu bars, status lines, border characters (`─`, `│`, `╭`, `╮`), empty cells. The diagnostically significant region — the focused element, the error message, the active form field — is typically 10–20% of screen area. The `get_screen text` mode discards all style information, which means a red error message and a green success message serialize identically. The `get_screenshot svg` mode charges ~8000 tokens for the entire screen equally.

**Concrete failure scenario:** An LLM is navigating an interactive installer. The active focused option is highlighted with `bg: "#0000ee"`. The LLM calls `get_screen text` (cheap, ~250 tokens) and receives the option text — but cannot distinguish it from surrounding options because the `full` format is too expensive to use routinely (~8000 tokens). It guesses wrong about which option is selected.

**Fix — ROI-aware text mode:** Add a `semantic` format to `getScreen()` that serializes only cells where style information carries meaning: cells adjacent to the cursor, cells with non-default `bg`, cells that are `bold` or have `inverse`. Cells with default style and non-cursor position get only their `char`. Estimated output: 400–800 tokens, with all decision-critical information preserved.

```typescript
// In src/tools/screen.ts — add to getScreenSchema format enum:
.enum(["full", "text", "compact", "semantic"])

// New case in getScreen():
case "semantic": {
  const state = session.renderer.getScreenState();
  return buildSemanticSummary(state); // encodes ROI at full fidelity, chrome at text-only
}
```

### Finding 1.2 — No progressive resolution path [P2]

**What medical imaging does:** DICOM with JPEG 2000 progressive transmission sends a low-resolution thumbnail in the first packet. The viewer renders immediately. Subsequent packets refine to full diagnostic quality. Radiologists can triage at the thumbnail level and invest bandwidth only on interesting cases.

**What tuivision does today:** Every `get_screenshot` call returns the full image at full resolution. There is no mechanism to say "give me a coarse view first, then refine the area near the cursor."

**Fix — LOD-indexed screenshot:** Add a `detail` parameter to `getScreenshot` (`"thumb"` | `"full"`). At `thumb`, `renderToSvg` renders only every other character column and every other row — a 2x spatial reduction that reduces token count by 4x while preserving layout structure. The LLM can identify the region of interest and request a cropped `full` capture.

### Finding 1.3 — Windowing absent: same data, one rendering [P3]

**What medical imaging does:** A CT scan of the chest is one dataset. Radiologists apply different "windows" — lung window, bone window, mediastinal window — each revealing different diagnostic information from the same raw Hounsfield values.

**What tuivision does today:** `getScreenState()` returns one fixed rendering. There is no concept of a "task-adapted view" — the same data always renders the same way regardless of what the agent is trying to do.

**Proposed pattern:** Caller-specified rendering profiles. An agent navigating menus wants `"interactive"` (emphasize cursor position, focused elements, `inverse` cells). An agent reading logs wants `"content"` (strip all color/style, maximize text density). An agent checking layout wants `"structure"` (emphasize background regions, borders, spatial blocks). Each profile is a projection of the same `ScreenState` — no new capture cost.

---

## Agent 2 — fd-accessibility-screen-reader
*Accessibility engineer: screen readers, ARIA roles, semantic role serialization*

**Decision lens:** Does the serialization preserve the information needed to navigate and act, even without pixels?

### Finding 2.1 — No semantic role layer [P1]

**What screen readers do:** NVDA, VoiceOver, and JAWS don't describe what they see — they announce what things *are*. A focused button gets announced as "Submit, button." A live region update says "Error: invalid password, alert." The ARIA role taxonomy (button, alert, heading, menuitem, status, progressbar, textbox) is the semantic layer that converts visual layout to navigational meaning.

**What tuivision does today:** `getScreenText()` returns a flat string of characters. The text for a focused menu item and a status bar message are indistinguishable in the output. The LLM must infer roles from spatial position and textual content. This inference fails regularly — a ">" character can be a shell prompt, a selected menu indicator, or part of a file path.

**The ARIA-for-terminals opportunity:** Terminal applications signal roles through consistent visual conventions:
- `inverse` cell at cursor position → focused/selected element
- `bold` text in a border row (top/bottom 2 rows) → heading/title
- Cells with `bg` different from the majority → highlighted/active region
- Text matching error patterns (`[ERROR]`, red `fg`) → alert role
- Bottom status line (row 23 on 24-row terminal) → status role
- `dim` text → disabled/hint role

None of these role inferences are computed in the current codebase. `getScreenText()` (`terminal-renderer.ts:252–255`) collapses 24 rows of semantic information into a single flat string.

**Concrete failure scenario:** An LLM is operating a curses-based menu (htop, midnight commander). The selected item has `inverse: true` and `bg: "#0000ee"`. `get_screen text` returns the text of all visible menu items with no indication of which is selected. The LLM sends the wrong keypress.

**Fix — semantic annotation format:** A new `get_screen` format `"annotated"` that walks the `ScreenState` and produces role-annotated output. Modeled on ARIA live region announcements:

```
[title] Process Manager — htop 3.3.0
[status] Tasks: 128, 45 thr; 0 kthr; 0 running
[selected] 1234 mk   20   0  512M  48M  32M S  1.2  0.8  0:12 node
[menu] F1Help  F2Setup  F3Search  [F5Tree]  F6SortBy  F9Kill  F10Quit
```

Cost: ~180 tokens (similar to `text` mode). Benefit: cursor position, selected row, active function key — all preserved without any visual tokens.

### Finding 2.2 — No live region / change-signal model [P2]

**What screen readers do:** ARIA `aria-live="polite"` and `aria-live="assertive"` let page authors signal which content changes matter. A polite region waits for the user to be idle. An assertive region (error alerts) interrupts immediately. Screen readers use this to avoid announcing every `innerText` mutation — only semantically significant ones.

**What tuivision does today:** The MCP protocol offers `wait_for_output` and `wait_for_stable` tools, but no concept of change significance. After any interaction, the agent must call `get_screen` and process the full state — there is no mechanism to say "tell me only what changed that matters for my current task."

**Fix — semantic diff output:** Add a `get_screen_diff` tool that returns only cells that changed since the last snapshot *and* have semantic significance (non-default style, cursor-adjacent, or in a designated live region). A typical interactive navigation step changes 2–5 cells — the diff would be under 50 tokens.

### Finding 2.3 — Verbosity levels absent [P3]

**What screen readers do:** JAWS, NVDA, and VoiceOver have configurable verbosity: character-level (announces every letter), word-level, sentence-level, paragraph-level. The user chooses based on task. Navigation tasks want heading-level; proofreading wants character-level.

**What tuivision does today:** Three static modes — `text`, `compact`, `full` — with no concept of task-adaptive verbosity. There is no "tell me just the structural landmarks" equivalent.

**Proposed pattern:** A `landmarks` format that returns only the top-level structural blocks of the terminal — title bars, status bars, dialog boundaries, identified regions — without inner text. Cost: ~50–100 tokens. Useful for orientation before drilling into a specific region.

---

## Agent 3 — fd-game-rendering-lod
*Game engine rendering engineer: LOD systems, occlusion culling, performance budgets*

**Decision lens:** The right detail level is the one that achieves the task without exceeding the context budget.

### Finding 3.1 — No LOD system — always maximum detail [P1]

**What game engines do:** Unreal Engine's Hierarchical LOD (HLOD) and Unity's LOD Groups select mesh complexity based on screen-space coverage and distance from camera. A tree 500m away renders as a billboard sprite (2 triangles). The same tree 10m away renders at 50,000 polygons. The frame budget is constant; the allocation is dynamic.

**What tuivision does today:** `getScreen("full")` always returns all 1920 cells with all 9 fields per cell. `getScreenshot("svg")` always renders all 80×24 positions. There is no system that asks "what is the agent's current task complexity?" and selects detail accordingly. The context window (the frame budget) is fixed; the allocation never adapts.

**Concrete failure scenario:** An LLM is running a batch test suite and watching a progress bar. It calls `get_screen text` in a loop to check completion — cheap, correct. But the progress bar percentage is in a styled region; `text` mode cannot tell the difference between "47%" and "100%". The LLM switches to `get_screenshot svg` — and now every check costs 3000 tokens. Over 20 checks, it spends 60,000 tokens watching a progress bar.

**Fix — LOD-indexed mode selector:** Three formal LOD levels with documented cost/fidelity contracts:

| LOD | Format | Tokens | Use case |
|-----|--------|--------|----------|
| LOD0 | `landmarks` | ~80 | Orientation, navigation |
| LOD1 | `annotated` | ~250 | Interaction, state checking |
| LOD2 | `svg_roi` | ~600 | Visual verification of specific region |
| LOD3 | `svg` (current) | ~2000–8000 | Full visual regression |

The LLM specifies its current LOD budget; tuivision returns the best representation within budget.

### Finding 3.2 — No occlusion culling [P2]

**What game engines do:** Occlusion culling skips rendering objects that are behind other objects. A wall blocking a room means the room geometry is never processed. This is cheap computation that eliminates expensive rendering work.

**What tuivision does today:** `renderToSvg()` in `screenshot.ts` renders all cells including those covered by modal dialogs, popups, or overlapping panels. A dialog box drawn over the main content renders both layers — the background content is occluded to the user but still costs tokens.

**The terminal occlusion opportunity:** Terminal applications with modal dialogs (confirmation prompts, error overlays, selection lists) draw the dialog on top of existing content. The background content is semantically occluded — it doesn't influence the user's current decision. But `getScreenState()` returns all cells, and `renderToSvg()` renders all layers.

**Fix — dialog detection and culling:** Detect modal regions by identifying rectangles with uniform `bg` that are smaller than the terminal and positioned centrally. Cull background cells within the modal boundary from the serialized output, replacing them with a `[occluded]` marker. Estimated token saving: 20–40% when a modal is present.

### Finding 3.3 — No temporal coherence / diff-based updates [P2]

**What game engines do:** Temporal anti-aliasing (TAA) and reprojection reuse previous frame pixel values for regions that haven't changed. Instead of computing every pixel every frame, the renderer reuses stable regions and only processes changed areas. Frame budget goes to motion and new content.

**What tuivision does today:** Every `get_screen` call returns the full terminal state regardless of what changed since the last call. If the agent typed one character into a text field, it receives all 1920 cells again — 1919 of which are identical to the previous call.

**Fix — snapshot-delta mode:** The session manager (`src/session-manager.ts`) already maintains session state. Add a `since` parameter to `get_screen` that accepts a snapshot token (opaque hash of the previous state). The tool computes a cell-level diff and returns only changed cells with their coordinates. A typical keystroke changes 1–3 cells. A typical menu navigation changes 1–2 rows. The delta representation would be 10–30 tokens instead of 250.

---

## Agent 4 — fd-wire-protocol-serialization
*Protocol engineer: protobuf, msgpack, CBOR, ASN.1, compact wire format design*

**Decision lens:** Bytes-per-semantic-field and LLM parseability — the best format encodes the most meaning in the fewest tokens while remaining parseable without a schema in context.

### Finding 4.1 — SVG format has redundant per-cell field names [P1]

**What protocol engineering identified:** JSON and XML are verbose because field names repeat with every record. Protobuf eliminates this with schema-driven field numbering — field 3 is always `fg`. msgpack achieves 30–50% size reduction over JSON by using binary type tags. For LLM consumption the format must remain text-parseable, but the verbosity of repeated field names is still the dominant cost.

**What tuivision's SVG does today:** `renderToSvg()` emits one `<text>` element per non-space character, each with `class`, `x`, `y`, `fill` attributes, and optionally `style`. For a typical 80×24 terminal with 60% character density, this is ~1150 `<text>` elements. Each element repeats `class="terminal-text"` — 18 characters × 1150 = 20,700 characters of redundant class name.

**Concrete failure scenario:** An htop-style process viewer has ~800 non-space characters. The SVG output is 6,000+ tokens. The LLM pays for a full screenshot to see 800 characters of actual information, of which 200 are the process names and numbers it actually cares about.

**Fix — run-length encoded text format (ANSI-like DSL):** Design a compact text format that LLMs can parse without a schema. The key insight from wire protocol design: encode runs of identical style, not individual cells.

```
# Terminal State v1 (80x24, cursor=15,3)
# Format: ^STYLE text | STYLE is f=fg b=bg attrs (B=bold I=italic U=underline D=dim R=inverse)
# Default style omitted; only changes encoded
L0: Process Manager ─────────────────────────────────── htop 3.3.0
L1: ^f#00ff00B Tasks:^f#ffffff  128, 45 thr; 0 kthr; 0 running
L2: ^f#00cdcd Mem[^f#00ff00||||||||||||||||^f#00cdcd 1.2G/15.7G]
L3: ^f#000000b#0000ee  1234 mk   20   0  512M  48M  32M S  1.2  0.8  0:12 node
L4: ^f#ffffff 1235 root  0 -20     0     0     0 I  0.0  0.0  0:00 kworker
```

Key encoding decisions from wire protocol design:
- **Delta style encoding:** Only emit a style marker `^STYLE` when style changes from the previous cell. Most text runs share the same style — the marker amortizes to near-zero.
- **Run-length compression:** Spaces with default style encode as a count: `_20` instead of 20 space characters.
- **Per-line framing:** Line numbers are implicit (`L0:`, `L1:`) eliminating x/y coordinate repetition.
- **Schema in the header:** One comment block at the top describes the format — ~40 tokens paid once.

Estimated cost: 300–600 tokens for a full 80×24 terminal with full color/style information. This is the "missing mode" — richer than `text` (has color/style), far cheaper than SVG (~3–8x reduction), and LLM-parseable without vision.

### Finding 4.2 — Dictionary compression opportunity for repeated colors [P2]

**What protocol engineering does:** Dictionary compression (LZ77, DEFLATE, Brotli) identifies repeated byte sequences and replaces them with short back-references. In structured data, explicit dictionaries (like HPACK in HTTP/2) pre-register common values for near-zero encoding cost.

**What tuivision does today:** SVG output repeats full hex color strings (`fill="#00ff00"`) for every cell. In a typical htop view, the green color (`#00ff00`) appears on dozens of cells. Each repetition costs 9 characters.

**Fix — SVG with CSS class dictionary:** The SVG already has a `<style>` block (screenshot.ts:208–213). Extend it to pre-define classes for the terminal's active color palette (typically 8–16 colors in use at any time). Replace per-cell `fill="#00ff00"` with `class="f2"` (2 characters). Estimated token saving on SVG: 25–40% with no fidelity loss. No changes to the core renderer — only the SVG serializer.

```typescript
// In renderToSvg(): before rendering cells, scan lines to build color palette
const fgPalette = new Map<string, string>(); // color hex → CSS class name
// ...generate <style>.f0{fill:#ffffff}.f1{fill:#00ff00}...</style>
// Then reference .f0, .f1 in each <text> element
```

### Finding 4.3 — No varint/delta encoding for coordinates [P3]

**What protocol engineering does:** Coordinates are most compactly encoded as deltas from the previous position. In a 80×24 grid where text runs left-to-right, successive x coordinates differ by 1 (or a few). Varint encoding of delta-x eliminates the constant-width `x="8.4"` repetition.

**What tuivision does today:** Every `<text>` element in the SVG has explicit `x` and `y` floating-point pixel coordinates. For 1150 cells at charWidth=8.4, x values are `8.4`, `16.8`, `25.2`... — 4–5 characters each × 1150 = 4,600–5,750 characters of coordinate data.

**Fix — run-per-line SVG structure:** Group text elements by row into `<tspan>` with `dy` offset, using `x` only at line start and relying on character advance for within-line positioning. This is standard SVG text rendering. Estimated savings: 30–40% of SVG size from coordinate elimination alone. Implementation is localized to `renderToSvg()` in `screenshot.ts`.

---

## Synthesis — The Four Missing Modes

Each discipline independently converges on the same gap: tuivision has no mode that sits between cheap-and-blind (`text`, ~250 tokens) and expensive-and-visual (`svg`, ~5000 tokens). The orthogonal disciplines each propose a different path to fill that gap:

| Source discipline | Proposed mode | Estimated tokens | Key information preserved |
|-------------------|--------------|-----------------|--------------------------|
| Medical imaging (ROI) | `semantic` (active regions only) | 400–800 | All style on cursor-adjacent + styled cells |
| Accessibility (ARIA) | `annotated` (role labels) | 150–250 | Semantic roles, selected state, alert content |
| Game engines (LOD) | `landmarks` (structural blocks) | 50–100 | Layout topology, dialog presence |
| Wire protocols (DSL) | `styled-text` (ANSI-like compact) | 300–600 | Full color/style, all text, compact encoding |

These four modes are additive and non-overlapping. Together they form a complete LOD ladder:

```
50 tokens ── landmarks (orientation)
     ↓
250 tokens ── annotated (navigation/interaction)  ← closes the gap
     ↓
600 tokens ── styled-text (full information, no vision)  ← closes the gap
     ↓
2000 tokens ── svg_roi (visual verification, focused region)
     ↓
8000 tokens ── svg (full visual regression)
```

### Implementation sequencing

**Phase 1 (closes the critical gap):** `annotated` mode in `get_screen`. Requires: semantic role inference from `CellData`, format of ~150–250 tokens. Single file change in `src/tools/screen.ts` + a new `buildAnnotatedSummary()` function in `terminal-renderer.ts`. This eliminates the primary failure scenario (LLM can't distinguish selected from unselected menu items).

**Phase 2 (high ROI):** `styled-text` DSL format. Requires: a run-length encoder that walks `ScreenState.lines` and emits style markers on change. Localized to a new serializer function. This gives the LLM full color/style information at 10–20% of SVG cost — the "missing mode" that makes `get_screenshot` unnecessary for most decision tasks.

**Phase 3 (SVG cost reduction):** CSS palette dictionary + `<tspan>` coordinate elimination in `renderToSvg()`. No semantic change; reduces existing SVG mode cost by 40–60%. Localized to `screenshot.ts:renderToSvg()`.

**Phase 4 (delta/diff):** Snapshot diff mode in session manager. Requires session-level state snapshotting in `src/session-manager.ts`. High value for agent loops (watch-mode). Lower priority since Phase 1–2 eliminate the main cost driver.

---

## Cross-Cutting Observations

**Alignment with tuivision philosophy:** The Philosophy's working priorities are "deterministic waits, low flake rate, visual regression fidelity." The LOD ladder proposal supports these: `annotated` mode for interaction (deterministic), `styled-text` for state verification (low flake from semantic grounding), `svg` reserved for visual regression (fidelity). The proposal reduces cost without degrading the regression use case.

**The 80/20 observation from all four disciplines:** Medical imaging calls it ROI encoding. Screen readers call it live regions. Game engines call it LOD. Protocol engineers call it dictionary compression. All four disciplines converge on the same empirical observation: the useful information is concentrated. For a typical interactive terminal session, ~15% of cells carry ~85% of the decision-relevant information. The current tuivision modes either pay for 100% of cells (SVG) or discard the useful 15% (text). The gap is the design space.

**Conflict/Risk:** Adding modes increases the API surface and the agent's decision burden ("which mode should I use?"). Mitigate with documented cost/fidelity contracts and a `budget` parameter that auto-selects the appropriate mode.
