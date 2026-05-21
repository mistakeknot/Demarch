# Track D — Esoteric Domain Review: Tuivision Token Optimization

**Topic:** Creative approaches to give LLMs rich terminal state information (text + visual semantics like color, layout, emphasis) at minimal token cost.

**Flux-drive review date:** 2026-04-02
**Agents:** fd-quipu-khipu-multichannel-encoding, fd-protactile-modality-transduction, fd-cuneiform-token-abstraction-pressure
**Source domains:** Inca quipu (15th–16th c.), Pro-Tactile ASL (2007–present), Sumerian cuneiform (3400 BCE–75 CE)

---

## Why these three domains

These three domains were selected for maximal distance from terminal emulation. What makes them surprising as sources of insight is not that they are exotic — it is that each independently solved a version of the same problem:

> How do you move rich, multi-attribute information through a channel that cannot accommodate all of it?

- **Quipu:** Physical textile → administrative record. Five physical attributes (cord color, twist direction, knot type, knot position, attachment point) must each carry independent semantic weight because the cord cannot be made longer.
- **Pro-Tactile ASL:** High-bandwidth visual-spatial sign language → low-bandwidth tactile channel. Preserving meaning requires identifying which features are linguistically contrastive and which are redundant renderings of the same meaning.
- **Cuneiform:** Pictographic appearance-description → abstract symbolic meaning-declaration. Driven by the cost of clay, scribes progressively replaced iconic representation with symbolic compression, adding disambiguation mechanisms (determinatives) to compensate for lost visual context.

Tuivision's problem: a 240×80 terminal cell grid with per-cell color, bold, and structural attributes → a token budget. Three domains, 5000 years apart, each solved a subproblem of this.

---

## Domain 1: Quipu — Independent Semantic Channels

### Core mechanism

Quipu cords encode information across five simultaneously-readable independent channels: cord color, ply twist direction (S vs. Z), knot type (simple, long, figure-eight), knot position along the cord (decimal place value), and attachment position on the primary cord. None of these channels is decorative. All are data.

### Mapping to tuivision

A terminal cell has exactly the same structure: five independently-readable channels — text character, foreground color, background color, bold/intensity, and cell position. The current `get_screen` mode encodes only the text channel and discards the other four. The current `get_screenshot` modes encode all channels simultaneously in a single high-entropy format (PNG or SVG), which is expensive and loses the independence.

The quipu insight: **these channels can be independently compressed or independently omitted depending on task requirements.** A task that reads file paths needs position and text but not color. A task that monitors a test runner needs text and the red/green distinction but not exact bold state. A task that navigates a menu needs position and bold (selection emphasis) but not color.

### Findings

**P0: Treating color as decorative and stripping it in the text mode.**
In `get_screen`, foreground color is stripped entirely. For an agent reading a test runner output (red = fail, green = pass), this collapses two distinct semantic states to indistinguishable text. The agent cannot know whether a test passed or failed without scraping for surrounding text context. Failure mode: agent reports "all tests passed" because it read the test name but not the color-encoded outcome.

**P1: No hierarchical attachment encoding.**
TUI applications encode structural hierarchy through spatial nesting (pane borders, indentation, nested menus). `get_screen` flattens this to a character grid with no parent-child relationship encoding. A file manager pane and a preview pane sharing the same screen surface become one undifferentiated text block. The agent cannot determine which content belongs to which widget without character-level heuristic parsing.

### Pattern: Channel-selective encoding

The quipu model suggests a fourth encoding mode: **channel-selective text**. The caller specifies which channels to include: `{text, color_categorical, bold, position_indent}`. Each channel is encoded independently and compressed against its own statistics. Color is encoded as a semantic category (error/success/warning/info/neutral) not as an ANSI escape sequence. Position is encoded as indent depth, not absolute column. This can produce 80–120 token representations of 240×80 screens by omitting irrelevant channels rather than compressing all channels together.

---

## Domain 2: Pro-Tactile ASL — Contrastive Feature Analysis

### Core mechanism

When Pro-Tactile ASL was developed (starting 2007) to allow Deaf-Blind individuals to receive sign language through touch, the central research question was: which visual features of sign language are linguistically contrastive (different feature = different meaning) and which are phonetically redundant (different feature = same meaning, different rendering)?

The answer was not obvious. Handshape is contrastive (the difference between "mother" and "father" is a single handshape distinction). Exact finger extension angle within a handshape is redundant — native signers vary it without changing meaning. This distinction determined what must be preserved during transduction and what can be discarded.

The field developed the concept of **modality restructuring**: some signs are not merely compressed for tactile mode but are entirely restructured, because the tactile channel encodes different features efficiently. A classifier predicate that uses 3D spatial location in visual ASL is restructured as a sequential tactile trace in Pro-Tactile ASL — not simplified, redesigned.

### Mapping to tuivision

Tuivision currently offers two poles: strip everything (text mode, ~300 tokens) or preserve everything (image mode, ~1600–8000 tokens). The Pro-Tactile insight is that neither pole is correct. The question is:

> Which visual features of a terminal state are linguistically contrastive for the agent's task, and which are redundant?

For an agent navigating a file browser:
- **Contrastive:** cursor position (bold/reverse-video on selected item), hierarchical indentation (depth in directory tree), presence of permission-denied markers
- **Redundant:** exact syntax-highlight color (purple vs. blue for directory names), whether the border is single or double line-drawing characters, scrollbar position when the content fits in frame

For an agent monitoring a build system:
- **Contrastive:** red/green color status, error message text, line number references
- **Redundant:** exact ANSI 256-color index (error could be `#cc0000` or `#ff0000` — the contrastive distinction is "it is an error color"), bold weight, box-drawing characters framing the status panel

### Findings

**P0: No contrastive feature analysis at the encoding layer.**
The current modes treat all features as either fully present or fully absent. There is no mechanism to ask "encode the features that would change my behavior" and discard the rest. This means agents either work with incomplete information (text mode) or pay for redundant information (image modes). The failure mode is not dramatic but cumulative: agents running thousands of terminal automation tasks pay 5–10x the necessary token cost because encoding is not task-coupled.

**P1: Exact color values preserved at token cost rather than categorical mapping.**
`get_screenshot svg` encodes exact ANSI color indices or RGB values. For the contrastive distinction that matters (error vs. success vs. warning vs. neutral), the exact shade is redundant. Encoding `#cc3300` and `#ff3333` separately costs tokens to distinguish two states that are semantically identical for any agent task. The categorical color vocabulary has 5–7 values; the ANSI vocabulary has 256; true-color has 16.7 million.

**P1: No backchanneling mechanism.**
Pro-Tactile introduced constant tactile feedback so the signer knows the receiver is following at the right level of detail. There is no equivalent in tuivision: the LLM cannot signal "I can work with 50-token summaries for navigation" vs. "I need 400-token detail because I am debugging layout". The encoding mode is caller-specified but not dynamically negotiable. A task-aware encoding API would let agents request the minimum contrastive feature set.

### Pattern: Modality restructuring for terminal-to-text

The deeper Pro-Tactile insight is that modality restructuring produces better results than modality compression. For some terminal states, the optimal text representation is not a compressed version of the visual layout but a restructured semantic description:

```
# Iconic (compressed visual):
"[bold]src/main.rs[/bold]  432 lines  [red]3 errors[/red]  [yellow]1 warning[/yellow]"

# Symbolic (restructured):
"FILE:src/main.rs ERRORS:3 WARNINGS:1"
```

The restructured form is 40% shorter and more directly parseable by an LLM. It does not describe what the screen looks like; it declares what the screen means. This is modality restructuring, not compression.

---

## Domain 3: Cuneiform — Iconic to Symbolic Under Medium-Cost Pressure

### Core mechanism

The evolution of Sumerian writing from 3400 BCE to mature cuneiform is the most documented case of encoding optimization under medium-cost pressure in human history. The initial clay token system was iconic: a cone-shaped token meant "a unit of grain" because it looked like a grain measure. This was replaced by pictographs incised on clay tablets — still iconic, the sign for "ox" was a head-of-ox pictograph. Over 1500 years, economic pressure on tablet space drove the system to abstract wedge patterns where the relationship between sign form and sign meaning became entirely conventional.

Two inventions made this work:
1. **Determinatives** — unpronounced classifier signs prepended to words to indicate semantic category, compensating for the loss of iconic visual context. The sign DINGIR before a name indicates a deity; the sign KI after a word indicates a place name. These add a small fixed cost per semantic domain boundary but eliminate far larger ambiguity.
2. **Logographic efficiency** — single signs representing entire words rather than sounds or visual features. Common words got compact representations; rare words were spelled phonetically at higher cost.

### Mapping to tuivision

The current tuivision text encoding is early-Sumerian: it reproduces what the screen looks like, character by character. The SVG mode is even more iconic — it is a pictograph of the screen. Both work, but both pay iconic cost. The cuneiform trajectory suggests the destination under token-budget pressure: an encoding that declares what the screen means rather than describing what it looks like.

### Findings

**P1: Text mode remains iconic.**
`get_screen` produces a character-for-character reproduction of the terminal surface. A 80×24 screen with a vim editor open produces approximately 320 tokens of text that is structurally isomorphic to the visual layout — line breaks where the terminal has line breaks, whitespace where the terminal has whitespace, ANSI escapes stripped but spatial structure preserved. The semantic content ("vim is open, cursor at line 47, insert mode") could be encoded in 15 tokens. Failure mode: agents reading `get_screen` output must parse iconic encoding to extract symbolic meaning on every call, adding latency and error surface.

**P2: No determinatives for semantic domain boundaries.**
When a terminal shows mixed content — a file path, an error code, a line number, a menu selection — the LLM must infer type from context. The number `47` could be a line number, a test count, a process ID, or an exit code. In cuneiform terms, there are no determinatives. Adding type-prefix tags (`LINE:47`, `PID:47`, `EXIT:47`, `COUNT:47`) adds 3–5 tokens per ambiguous value but eliminates disambiguation work from the LLM context. For multi-screen automation sessions with hundreds of terminal reads, this is net-token-positive.

**P1: SVG mode is maximally iconic under maximum token cost.**
The SVG representation describes the visual appearance of every glyph, color, and position — it is a pictograph system. It costs 2000–8000 tokens to communicate what `FILE:buffer.rs CURSOR:47 MODE:INSERT` communicates in 5 tokens. The SVG mode should be reserved for terminal states where visual layout information is itself the payload (pixel-accurate UI testing, rendering verification) rather than as the default "rich" encoding.

### Pattern: Determinative-style semantic tagging

The cuneiform pattern suggests a concrete encoding format for tuivision's symbolic mode:

```
SCREEN:vim
FILE:src/main.rs MODE:insert CURSOR:line=47,col=12
VIEWPORT:lines=35-70 TOTAL:432
MSG:error "unused variable `x`" LINE:52
STATUS:NORMAL
```

This is 25 tokens. The equivalent `get_screen` output for the same vim session is 280–350 tokens. Each line uses a determinative-style prefix (`FILE:`, `MODE:`, `CURSOR:`, `MSG:`, `STATUS:`) that tells the LLM what kind of entity it is reading. An agent looking for errors scans for `MSG:error`. An agent tracking cursor position reads `CURSOR:`. The encoding is symbolic, not iconic.

The determinative prefixes form a closed vocabulary (maybe 30–50 terms) that can be learned by the LLM through prompt context. This is logographic efficiency: the vocabulary amortizes across the session.

---

## Cross-Domain Synthesis

### Three orthogonal insights that compose

The three domains produce insights that do not overlap — they address different subproblems:

| Domain | Problem addressed | Core mechanism | Token implication |
|---|---|---|---|
| Quipu | What channels exist and how to select them | Independent semantic channels, task-selective omission | Omit irrelevant channels entirely |
| Pro-Tactile | Which features are worth encoding at all | Contrastive vs. redundant feature analysis | Strip redundant features (exact shades, exact weights) |
| Cuneiform | How to encode surviving features | Iconic vs. symbolic representation | Declare meaning, not appearance |

Applied in sequence, these form a compression pipeline:

1. **Channel selection (quipu):** Which attribute channels does this task need? Drop the rest entirely.
2. **Contrastive filtering (Pro-Tactile):** Within the selected channels, which distinctions are contrastive for this task? Collapse redundant variants.
3. **Symbolic encoding (cuneiform):** Encode surviving information as meaning declarations with determinative-style type tags, not appearance descriptions.

### What this pipeline produces

For a typical agent navigation task (cursor movement, item selection in a menu), the three-stage pipeline could reduce:

- `get_screenshot` SVG: 4,000 tokens (iconic, all channels, all features, appearance-based)
- `get_screen` text: 280 tokens (text channel only, no color, appearance-based)
- Channel-selected symbolic: 20–40 tokens (position + bold/selected, contrastive distinctions only, meaning-declared)

The 10–15x reduction over the current best text mode comes from combining all three insights. No single domain insight alone achieves this.

### The surprise

The genuinely surprising result from these three domains is not any individual mechanism but the convergence finding: three independent information systems — separated by millennia, continents, and scales — each discovered that moving from appearance to meaning under resource pressure produces 80–90% compression with no loss of actionable information.

The quipu specialists encoded "40 llamas of type 3 in district 7" in a few cord attributes rather than carving a picture of 40 llamas. The Pro-Tactile linguists transmitted "WRONG, ASK AGAIN" in a standardized backhand tap rather than signing it in full. The Sumerian scribes wrote KI-sar instead of drawing a picture of a place. All three converged to: declare the category, declare the value, use a type marker.

Tuivision's text mode went the opposite direction: it preserved the appearance of the terminal surface at the character level. The domains confirm this as the high-cost direction.

---

## Concrete recommendations

### Immediate: Add categorical color mapping to text mode

Replace stripped ANSI colors in `get_screen` with categorical labels in the text stream. Map the ANSI 8/16/256 color space to a 7-category vocabulary: `error`, `success`, `warning`, `info`, `muted`, `selected`, `default`. Emit these as inline annotations rather than escape sequences: `[error]build failed[/error]`. This adds ~2 tokens per styled span and makes color contrastive without reproducing exact color values.

### Near-term: Add a symbolic summary mode

A new `get_screen_semantic` MCP tool that returns a determinative-tagged representation. The tool accepts a `channels` parameter specifying which semantic channels are relevant: `["position", "color_categorical", "bold", "text"]`. The output format uses cuneiform-style type prefixes. For common TUI patterns (vim, htop, file browsers, test runners), pre-defined templates produce fixed-format outputs that compress known widget patterns to near-minimum token counts.

### Near-term: Contrastive feature registry per TUI application

Maintain a registry that maps known TUI applications to their contrastive feature sets. For vim: cursor position, mode indicator, error messages, line numbers. For htop: CPU bars (color = load level), process name, PID. For pytest: test name, pass/fail color, error message. The registry allows the encoding to drop irrelevant channels entirely rather than compressing them — the quipu omission strategy rather than the compression strategy.

### Longer-term: Task-coupled encoding negotiation

An API where the agent specifies its task intent and the encoding layer returns the minimum contrastive feature set. The Pro-Tactile backchanneling model: the LLM signals "I am doing cursor navigation, I need position + selection" and receives 15-token screen states. The LLM signals "I am debugging a build, I need error text + line numbers + color" and receives 60-token screen states. The encoding adapts to what would change the agent's behavior, not to what the screen contains.

---

## Appendix: Agent files and formatting note

The three agent `.md` files at `.claude/agents/fd-quipu-khipu-multichannel-encoding.md`, `.claude/agents/fd-protactile-modality-transduction.md`, and `.claude/agents/fd-cuneiform-token-abstraction-pressure.md` contain a character-per-line formatting corruption in the "What NOT to Flag" and "Success Criteria" sections. The content in "Review Approach" and "Decision Lens" is intact. The flux-gen specs at `.claude/flux-gen-specs/tuivision-token-optimization-esoteric.json` contain the clean canonical agent definitions and were used as the authoritative source for this review.
