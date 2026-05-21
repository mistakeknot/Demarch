# Tuivision Token Optimization — Track C: Distant Domains

**Flux-drive review | 2026-04-02**
**Focus:** Structural isomorphisms from distant knowledge domains
**Agents:** fd-heraldic-blazon-notation, fd-choreographic-notation, fd-astronomical-plate-annotation, fd-textile-weaving-draft, fd-wayfinding-signage-hierarchy

---

## Problem Statement

Tuivision is an MCP server that gives AI agents visual access to terminal applications. Three current modes expose the token cost/fidelity tradeoff starkly:

| Mode | Tokens | What's Lost |
|---|---|---|
| `get_screen` text | ~200–400 | All color, style, emphasis |
| `get_screenshot` PNG | ~1600 vision | Position semantics, diffability |
| `get_screenshot` SVG | ~2000–8000 | Compressibility |

The core problem: terminal screens carry two distinct information streams — **text content** and **visual semantics** (color, emphasis, layout hierarchy). Current modes force an all-or-nothing choice: transmit one or the other, never both efficiently.

---

## Agent 1: Heraldic Blazon Notation

**Lens:** Does the representation encode visual composition through semantic vocabulary rather than coordinate geometry?

### Core Isomorphism

Blazon is a 600-year-old formal grammar for describing complex visual compositions — heraldic shields — in minimal structured text. "Azure, a lion rampant or" describes a blue shield with a standing gold lion in five words. The grammar operates through:

1. **Named tinctures, not color values** — 7 standard colors (or, argent, azure, gules, sable, vert, purpure) instead of hex codes
2. **Named regions, not coordinates** — chief (top), base (bottom), dexter (right), sinister (left), fess point (center)
3. **Charges by role and attitude, not pixels** — "a lion rampant" (rearing, facing dexter) encodes behavior, not appearance
4. **Marshalling** — composing multiple arms into one through quartering or impalement
5. **Cadency marks** — minimal additions that differentiate related arms without re-describing the whole

### Findings

**Finding B-1 (P1): Terminal encoding uses coordinate geometry where semantic regions exist**

Current `get_screen` output provides text with row/column position metadata when available. An error at "row 24, col 0" could instead be "prompt region" or "status bar, left." The agent reading the output must reconstruct the semantic role of every position from scratch on every call.

Blazon's insight: position-independence is not just compression — it is meaning-preservation. "The lion is in the center" conveys intent; "the lion is at pixel 128,96" conveys geometry that requires interpretation.

Concrete failure scenario: when a terminal application repositions its status bar (e.g., when help text appears above the prompt), coordinate-based descriptions break the agent's mental model silently. Semantic region names would survive layout shifts.

**Finding B-2 (P2): No tincture vocabulary — color information either absent or raw**

`get_screen` strips all color. `get_screenshot` PNG/SVG preserves it at high token cost. Neither option provides a semantic color vocabulary like blazon's tinctures.

A terminal's color palette is semantically loaded: red almost always means error or warning, green almost always means success, cyan/blue often means informational highlighting. This vocabulary is application-specific but stable within a session. A tincture-equivalent mapping — `gules` → error-red, `vert` → success-green, `or` → highlighted — established once per session and referenced thereafter, could convey color semantics for ~10 tokens per reference instead of embedding them in pixel data.

**Finding B-3 (P2): Pane composition lacks marshalling semantics**

When a terminal has multiple panes (e.g., tmux with editor + shell + log pane), the current SVG output concatenates all regions without a marshalling grammar that names how they relate. Blazon quartering encodes "this is a composite of four distinct arms, positioned thus." Terminal output should carry: "this screen is quartered: [editor, col 0-79] [shell, col 80-159] [status, row 24]."

**Finding B-4 (P3): No cadency/diff encoding**

Blazon cadency marks differentiate related-but-changed arms minimally. Terminal state between polling calls is similarly related-but-changed. A blazon-inspired diff grammar — "as before, except the status bar now reads: BUILD FAILED" — would be far cheaper than re-describing the whole screen.

### Proposed Mechanism: Terminal Blazon

```
SCREEN: [80x24 | tmux-quartered]
PANES:
  chief: [editor | file=main.rs | line=42]
  base-sinister: [shell | prompt | awaiting-input]
  dexter: [log | gules=ERROR | 3 new lines]
FOCUS: base-sinister
DIFF-FROM-LAST: dexter.log +3 gules lines
```

Token estimate: 50–80 tokens for a complete screen description, compared to 200–400 for raw text and 2000+ for SVG. Color semantics preserved. Position semantics preserved. Diff encoding possible.

---

## Agent 2: Choreographic Notation (Labanotation)

**Lens:** What level of abstraction captures the state without losing agent-relevant information? Can structure, content, and emphasis be separated into independent channels?

### Core Isomorphism

Labanotation encodes 3D human movement in a 2D staff through strict channel separation:

- **Support column** — what is weight-bearing (structural)
- **Gesture columns** — what limbs are doing (content)
- **Effort graph** — quality of movement (dim/bold/accented — emphasis)
- **Motif notation** — simplified intent-level summary vs. full-fidelity reproduction notation

The key insight is not compression through any single technique but through **lossless decomposition into independent channels** that can each be transmitted at their own fidelity level.

### Findings

**Finding C-1 (P1): No motif-level summary mode exists**

Tuivision has no equivalent of motif notation — a high-level intent summary that omits exact positions but conveys what is happening and why the agent should care. An agent that asks "what is the terminal doing?" must parse the full screen even when a 20-token summary would suffice.

Concrete failure scenario: an agent polling a long-running build process calls `get_screen` every 5 seconds. Each call costs 200–400 tokens. A motif-level summary — "BUILD: in progress, 47/120 tests, no errors" — costs 15 tokens and contains all information the agent needs to decide whether to intervene.

**Finding C-2 (P2): Structure, content, and emphasis are conflated in all three current modes**

- `get_screen` strips emphasis entirely, conflating structure and content in a flat text stream
- `get_screenshot` PNG conflates all three into undifferentiated pixel values
- `get_screenshot` SVG conflates all three into geometry + style attributes

No mode allows an agent to say "give me structure and emphasis but not full content" — equivalent to reading a Labanotation staff for body position and effort quality without transcribing every gesture symbol.

Practical impact: an agent navigating a menu only needs structure (which items exist, which is selected) and emphasis (which is highlighted). It does not need the full text of every menu item. Current modes force the full payload or nothing.

**Finding C-3 (P2): No temporal channel — state is always full snapshot, never delta + time**

Labanotation encodes movement across time on a single staff; the spatial and temporal dimensions are cleanly separated. Terminal state updates are structurally similar — the screen at time T+1 is mostly the screen at time T with specific changes applied.

Current `get_screen` has no temporal channel: every call returns a complete snapshot with no relationship to previous snapshots. An agent's context grows linearly with polling frequency.

### Proposed Mechanism: Three-Channel Terminal Notation

```
STRUCTURE: [prompt@row24 | menu:items=7,selected=3 | log:rows=22]
CONTENT: [prompt="$ cargo test" | menu=["run","build","test"(sel),"clean",...] | log=TRUNC]
EMPHASIS: [menu.selected=INVERSE | log.line22=GULES | prompt=NONE]
DELTA: [log +1 line GULES from T-1]
```

An agent asking for high-level orientation receives only STRUCTURE + EMPHASIS (30 tokens). An agent ready to act receives CONTENT for the relevant region only. DELTA replaces full snapshots for polling.

---

## Agent 3: Astronomical Plate Annotation

**Lens:** Are annotations separable from content? Do important regions receive more encoding fidelity? Is there a catalog cross-referencing mechanism for repeated patterns?

### Core Isomorphism

Photographic plate annotation adds structured meaning to visual data through a separate layer. The plate (raw image) is never modified. Annotations — spectral classifications, magnitudes, catalog IDs, coordinate references — exist as an overlay. Key properties:

1. **Separability** — annotation and content are cleanly distinguished; a researcher can study the plate or the annotations independently
2. **Classification vocabulary** — standardized type tags (O/B/A/F/G/K/M for stars, Sa/Sb/Sc for galaxies) not free-form descriptions
3. **Magnitude as fidelity signal** — bright objects receive more detailed annotation; faint objects get minimal marks
4. **Catalog cross-referencing** — "HD 12345" references a catalog entry, not a description; the catalog holds the details

### Findings

**Finding A-1 (P1): Annotation and content are not separable in any current mode**

`get_screen` returns a flat text stream where UI chrome (box-drawing characters, separator lines, status bar text) is indistinguishable from actual content. An LLM cannot determine whether `│` is a tmux pane border or a pipe character in a log line without full-screen context.

Concrete failure scenario: an agent parsing log output from a pane-split terminal accumulates box-drawing characters, pane borders, and status line text as noise in its content window. Over a 10-call session, this noise can exceed the signal.

Fix: add a semantic annotation layer that marks UI chrome separately from content. The raw text stream is the plate; the chrome map is the overlay.

**Finding A-2 (P2): No importance weighting — all regions receive identical encoding depth**

A static top navigation bar and an active error output region both appear at the same detail level in `get_screen`. In plate annotation terms, a magnitude-2 star (bright, central to the observation) and a magnitude-19 background object receive identical annotation depth.

Terminal regions have clear importance gradients: the line where the cursor is has maximum importance; the static help text in the corner has minimum importance. An encoding that allocates fidelity by importance would spend tokens where they matter.

**Finding A-3 (P2): No session-local catalog for repeated patterns**

Terminals repeat patterns heavily: the same prompt string appears on every command line; the same status bar format appears on every screen; the same menu items appear whenever a menu is open.

Plate annotation addresses this through catalog cross-referencing: once NGC 224 is classified and described in the catalog, every subsequent plate that captures it references "NGC 224" not the full spectral description.

A terminal session catalog — established at session start through a cheap full-screen parse — would allow subsequent calls to reference "PROMPT-1" instead of re-encoding `$ cargo build --release` on every screen.

**Finding A-4 (P3): No coordinate system relative to landmarks**

Plate coordinates use Right Ascension and Declination relative to reference stars, not absolute pixel positions. Terminal coordinates could similarly be landmark-relative: "3 lines above PROMPT-1" instead of "row 21."

This makes descriptions resilient to terminal resize events, which shift all absolute coordinates but preserve landmark-relative relationships.

### Proposed Mechanism: Terminal Plate Annotation

Session initialization creates a catalog:
```
CATALOG:
  PROMPT-1: "$ " (appears row 24 in current layout)
  STATUS-1: "INSERT | main.rs | 42,1" (appears row 0)
  BORDER-H: "─" repeated (separates panes)
  BORDER-V: "│" (separates panes)
```

Subsequent screen calls annotate by reference:
```
CONTENT: [row1-21 stripped of BORDER-V occurrences | raw text]
OVERLAY:
  @PROMPT-1 row24: awaiting input
  @STATUS-1 row0: [mag=2] INSERT | cargo/src/main.rs | 89,14
  @row22: [mag=3, gules] error[E0382]: use of moved value `x`
  @row23: [mag=3, gules]   --> src/main.rs:89:14
  CHROME: [BORDER-H at row0-separator, BORDER-V at col80]
```

Token budget: catalog ~50 tokens once; subsequent calls ~80–120 tokens without chrome noise.

---

## Agent 4: Textile Weaving Draft

**Lens:** Can the visual pattern be regenerated from structural rules alone? If yes, transmit rules not pixels.

### Core Isomorphism

A weaving draft is a compact binary grid that encodes a complex visual fabric pattern. The draft has three components:

1. **Threading draft** — which warp threads pass through which harnesses (the structural rule)
2. **Tie-up grid** — which treadles activate which harnesses (the lookup table)
3. **Treadling sequence** — which treadles are pressed in order (the program)

The finished cloth — with its full visual complexity — is the output. Weavers transmit the draft (100–200 cells) not the cloth (millions of threads). Pattern repeats are noted once; the count specifies how many times to repeat.

### Findings

**Finding W-1 (P1): Tuivision encodes the cloth, not the draft — output patterns instead of generative rules**

`get_screen` returns the rendered output of the terminal: the actual characters at every position. For UIs with significant structural regularity (tables, lists, trees, menus, log streams), this is transmitting the cloth when the draft would suffice.

Concrete failure scenario: a terminal application displays a file browser — 40 rows, each with [icon, filename, size, date, permissions]. `get_screen` encodes all 40 rows at full fidelity: ~400 tokens for what amounts to a pattern repeat of 1 template applied to 40 data items. The weaving-draft equivalent: encode the template once (15 tokens) and the 40 data items in their natural compact representation (60–80 tokens). Total: ~90 tokens vs 400.

**Finding W-2 (P2): No repeat detection or pattern compression**

The current modes have no mechanism to detect that rows 2–41 of a file listing are structural repeats of a single template. Each row is encoded individually. In weaving terms: the full treadling sequence is transmitted instead of "repeat this treadling 40 times."

This is the highest-leverage compression opportunity for structured terminal UIs (file browsers, process lists, log viewers, test runners).

**Finding W-3 (P2): No tie-up table — style vocabulary requires per-occurrence encoding**

The tie-up grid maps treadle presses to harness lifts in a compact lookup table; once the tie-up is known, a treadle number encodes the full harness pattern. Terminal styling works the same way: a compact style vocabulary established once maps style names to ANSI sequences. "gules" encodes the full red-error style.

Current SVG mode embeds full style attributes on every styled element. A style dictionary established in a session preamble would replace per-element style repetition with single-token references.

**Finding W-4 (P3): Draft shorthand for common terminal patterns**

Expert weavers abbreviate frequently-used draft patterns. Terminal UIs have highly standardized patterns: bash prompt, vim statusline, tmux status bar, less navigation hints. A shorthand library — "this is a BASH-PROMPT-1 at row 24" — would apply the draft shorthand pattern, requiring the agent to maintain only the delta from the known canonical form.

### Proposed Mechanism: Terminal Weaving Draft

```
TIE-UP:
  GULES: fg=red bold
  VER: fg=green
  DIM: fg=gray
  SEL: bg=blue fg=white

THREADING: [file-browser | col-template=[icon:1, name:32, size:8, date:12, perms:10]]

TREADLING x40:
  row2:  [icon=DIR VER, name="src/", size="—", date="2026-04-01", perms="drwxr-xr-x"]
  row3:  [icon=FILE, name="main.rs", size="4.2K", date="2026-04-02", perms="-rw-r--r--"]
  ...  (remaining rows as compact data, not re-encoded template)
  row5:  [SEL | icon=FILE, name="lib.rs", size="12K", date="2026-04-02", perms="-rw-r--r--"]
```

Token estimate for a 40-row file browser: ~150 tokens vs. 400 tokens for raw text, with full structural and style semantics preserved.

---

## Agent 5: Wayfinding Signage Hierarchy

**Lens:** Does the information hierarchy match the agent's decision sequence? Is the most decision-relevant information surfaced first?

### Core Isomorphism

Wayfinding design is the discipline of guiding decision-making through minimal, hierarchically organized visual cues in physical space. Key principles:

1. **Progressive disclosure** — broad orientation first (which floor?), then specific direction (which corridor?), then final destination (room 4B)
2. **Decision-point signage** — signs appear where decisions must be made, not continuously
3. **Landmark-based navigation** — "turn left at the blue wall" not "proceed 23.7 meters at bearing 271°"
4. **Information density thresholds** — wayfinding research identifies maximum useful sign density before cognitive overload causes navigation failures

### Findings

**Finding N-1 (P1): All terminal information delivered at a single priority level — no hierarchy**

All three current modes transmit the complete terminal state at uniform fidelity. An agent that needs only to know "is there an error?" must parse the full screen. An agent that needs to know "what is the current prompt?" parses the same full screen.

Concrete failure scenario: an agent orchestrating a multi-step build process polls the terminal after each step. Each `get_screen` call returns the complete terminal state — 80 columns × 24 rows of text — even though the agent's decision ("did this step succeed?") requires only the last two lines. Over a 20-step pipeline, the agent pays for 20 × 400 = 8,000 tokens when the relevant signal is in 20 × 15 = 300 tokens.

Fix: implement a tiered output hierarchy:
- **L0 (orientation):** 10–15 tokens — what is the terminal currently showing? (menu, shell prompt, error screen, progress indicator)
- **L1 (decision point):** 40–60 tokens — what decision or input does the terminal currently require?
- **L2 (detail):** full fidelity — everything, for when the agent needs to read actual content

**Finding N-2 (P2): No landmark system — agents cannot navigate to relevant screen regions without full parse**

When an agent knows it needs to read the error message, it cannot ask "give me the error block" — it must request the full screen and locate the error block itself. Wayfinding equivalent: no directory signs, so every visitor must walk every corridor to find their destination.

A landmark registry — established at session start, updated when layout changes — would let agents request named regions directly: `get_region("error-block")`, `get_region("prompt")`, `get_region("status-bar")`.

**Finding N-3 (P2): No decision-point detection — all polling calls are equivalent regardless of terminal state**

Wayfinding signs appear at decision points, not continuously. An agent polling a terminal should receive richer output when the terminal is at a decision point (awaiting input, displaying a menu, showing an error) than when it is mid-execution (showing scrolling build output).

Current modes return identical-structure output regardless of terminal state. A decision-point detector — even a simple heuristic (cursor at prompt = decision point; scrolling output = not decision point) — would enable the agent to poll cheaply during execution and receive rich output only at decision points.

**Finding N-4 (P3): Information density calibration — no maximum useful detail threshold**

Wayfinding research (e.g., Passini 1984) establishes that navigators can absorb approximately 5–7 independent information items at a decision point before confusion increases navigation errors. LLMs have an analogous threshold where additional terminal state detail increases hallucination rates in downstream reasoning.

Current modes have no mechanism to cap information density. A wayfinding-informed mode would: identify the decision point, extract the 5–7 most relevant items, and return those with a "X more items available" indicator.

### Proposed Mechanism: Tiered Terminal Wayfinding

```
ORIENTATION [L0, always]:
  state: AWAITING-INPUT
  landmark: BASH-PROMPT
  decision: "enter next command"

DECISION-POINT [L1, at decision points]:
  prompt: "$ "
  context: "last command: cargo test — 3 FAILED (exit 101)"
  relevant-landmarks: [ERROR-BLOCK @row18-22, SUMMARY @row23]

DETAIL [L2, on request]:
  region: ERROR-BLOCK
  content: [full text of rows 18-22]
```

An agent can make a minimum-cost L0 call first (10–15 tokens), determine from orientation whether to continue, then escalate to L1 (40–60 tokens) for the decision context, and finally L2 (full fidelity) only for the specific region it needs to read.

---

## Cross-Agent Synthesis

Five distant domains produced remarkably convergent findings despite completely different source mechanisms. The convergences point to three structural principles that tuivision's token optimization should be built on:

### Principle 1: Semantic Vocabulary Over Coordinate Geometry

All five domains encode *what something is* rather than *where it is in pixel space*. Blazon uses named regions and tinctures. Labanotation uses directional symbols and named body parts. Plate annotation uses catalog IDs and spectral classes. Weaving drafts use threading and tie-up vocabulary. Wayfinding uses landmark names and decision categories.

**Terminal encoding that names elements semantically will be 5–10x more token-efficient than coordinate-based encoding and more robust to layout changes.**

### Principle 2: Layered Fidelity With Independent Channels

All five domains decompose their information into separable channels that can be read at different fidelity levels:
- Blazon: tinctures (color) + regions (position) + charges (content) + cadency (delta) — independently readable
- Labanotation: structure + content + emphasis channels — independently readable
- Plate annotation: content layer + annotation overlay — independently readable
- Weaving draft: threading (structure) + tie-up (style map) + treadling (content) — independently readable
- Wayfinding: L0 orientation + L1 decision context + L2 detail — independently readable

**Tuivision should expose structure, content, emphasis, and delta as separable channels rather than fusing them in any single mode.**

### Principle 3: Generative Encoding Over Output Encoding

Three of five domains explicitly encode rules/templates rather than outputs:
- Weaving drafts encode generative rules (threading + tie-up) not the finished cloth
- Plate annotation encodes a catalog of patterns referenced by ID, not descriptions
- Wayfinding encodes landmark locations and decision-point properties, not full spatial maps

**For structured terminal UIs (file browsers, process lists, menus, log viewers), transmit the template + data separately rather than the fully rendered output.**

---

## Priority Findings Summary

| ID | Severity | Finding | Token Impact |
|---|---|---|---|
| C-1 | P1 | No motif-level summary mode (choreographic) | 200–400 tokens → 15 tokens for polling |
| N-1 | P1 | Uniform priority level — no information hierarchy (wayfinding) | 8,000 → 300 tokens over 20-step pipeline |
| B-1 | P1 | Coordinate geometry instead of semantic regions (blazon) | Breaks silently on layout change |
| A-1 | P1 | Chrome not separable from content (astronomy) | Accumulated noise per call |
| W-1 | P1 | Output encoding not generative encoding (weaving) | 400 → 90 tokens for file browser |
| B-2 | P2 | No tincture vocabulary for semantic color (blazon) | Color lost or costs 1600+ tokens |
| C-2 | P2 | Structure/content/emphasis conflated (choreographic) | Forces all-or-nothing payload |
| C-3 | P2 | No temporal channel — full snapshot every call (choreographic) | Linear context growth with polling |
| A-2 | P2 | No importance weighting across regions (astronomy) | Tokens spent on static chrome |
| A-3 | P2 | No session-local catalog for repeated patterns (astronomy) | Prompt re-encoded every call |
| W-2 | P2 | No repeat detection for structured UI (weaving) | 4-10x redundancy in list/table UIs |
| N-2 | P2 | No landmark system for region-targeted queries (wayfinding) | Agent can't request what it needs |
| N-3 | P2 | No decision-point detection (wayfinding) | Polling cost independent of terminal state |

---

## Recommended Implementation Order

1. **Session catalog + motif summary** (Astronomy A-3 + Choreographic C-1): lowest implementation cost, highest token reduction for polling agents. A session-start scan establishes the catalog; subsequent calls reference it. A motif mode returns L0 orientation in 15 tokens.

2. **Landmark registry + tiered output** (Wayfinding N-1, N-2): implement L0/L1/L2 tiers. L0 is a heuristic (cursor-at-prompt = decision point; scrolling = not). Landmark registry is a stable JSON structure maintained across calls.

3. **Semantic region naming** (Blazon B-1): map screen layout to named regions at session start, output region names instead of row/column coordinates. Resilient to resize.

4. **Tincture vocabulary** (Blazon B-2): establish a session-local color-to-semantic-role mapping. 7 named tinctures replaces the full ANSI color space for agent-facing output.

5. **Generative encoding for repeated structures** (Weaving W-1, W-2): detect template+data patterns in structured UI screens; transmit template once and data compactly.

6. **Channel separation** (Choreographic C-2, C-3): expose structure, content, and emphasis as independent query parameters; add delta mode for polling.
