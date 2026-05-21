---
artifact_type: flux-review
track: D (Esoteric)
bead: sylveste-sn7
brainstorm: docs/brainstorms/2026-04-03-tuivision-token-encoding-brainstorm.md
date: 2026-04-03
reviewers:
  - fd-marshallese-stick-chart-crossmodal-encoding
  - fd-geez-fidel-syllabary-quantized-modification
  - fd-tibetan-mandala-positional-chromatic-semantics
---

# Track D (Esoteric) Review — Tuivision Token-Efficient Terminal State Encoding

## Summary

| Severity | Count | Findings |
|----------|-------|----------|
| P0 | 0 | — |
| P1 | 4 | Color-as-appearance vs. color-as-meaning; format levels as detail gradations not purpose-differentiated; xterm palette quantization; span-merging ignores semantic boundaries |
| P2 | 3 | Cursor/active-pane absent from annotated format; BPE tokenization inconsistency across color markers; no structural preamble before detail stream |
| P3 | 2 | Single-read vs. reference-doc optimization; exception cost in mixed-case marker grammar |

**Total: 9 findings.**

The brainstorm is strong on the token-cost problem and MVP scoping. The critical design flaw across all three esoteric lenses converges on the same root issue: the annotated format is designed as *visual compression* (same information, fewer tokens) rather than *semantic transduction* (different information, optimized for LLM understanding). The P1s are load-bearing because they determine whether agents using the annotated format will build accurate working models of the terminal or merely cheaper-to-obtain visual noise.

---

## [P1] Default marker encodes color identity, not semantic meaning

**Agent:** fd-marshallese-stick-chart-crossmodal-encoding

**Source domain:** Marshallese stick charts (ri-meto navigation, Micronesia) — pre-colonial wave-piloting tradition where charts encode what waves *feel like through the hull*, not what the ocean *looks like* from above. Charts are never carried on voyages; they train body-memory, then stay on shore.

**Finding:** The brainstorm frames the annotated format's value as "semantic color and style information at ~400-600 tokens." But the default `[r]...[/]` marker encodes *which color the text is rendered in*, not *what that color means*. This is same-modal compression — reproducing the terminal's visual appearance at lower fidelity — rather than cross-modal transduction into LLM-comprehensible semantic state. A stick chart that tries to depict what ocean waves look like is useless to a navigator; the chart's value comes from encoding wave refraction as a spatial-tactile grammar. Similarly, `[r]Error: file not found[/]` tells the LLM "this text is red," but not "this text signals an operational failure." The `role=error` attribute carries the semantic signal, but the brainstorm makes it opt-in via `include_roles: true`, leaving the default encoding as same-modal compression. The brainstorm states roles incur "~100 token premium" and defers role detection heuristics to a follow-up child (Open Question 1), which means the MVP ships with the lower-fidelity encoding as the default.

**Mechanism:** Stick charts were study aids — never taken on voyages — because their value was transduction, not reproduction. The navigator internalized wave-feel patterns and left the chart behind. The annotated format serves LLMs that must act on terminal state, not view it. An agent reading `[r]...[/]` must then infer what "red" means in context, which collapses back to the same interpretive problem as reading raw terminal text. The cross-modal value requires the encoding to carry semantic weight, not color identity.

**Recommendation:** Promote the base heuristics — `bold+top-row = heading`, `inverse = selected`, `red = error`, `green = success` — from opt-in `include_roles: true` to the default annotated output. The brainstorm already lists these heuristics in Open Question 1 and acknowledges they are "app-specific and fragile." Fragility is acceptable in a default heuristic that the caller can suppress; the alternative (a default that provides no semantic signal) is definitively worse. Concretely: in `getAnnotatedText()`, apply role detection unconditionally; add a `suppress_roles: true` parameter for callers that want pure color markers.

---

## [P1] Format levels are detail-graduated, not purpose-differentiated

**Agent:** fd-marshallese-stick-chart-crossmodal-encoding

**Source domain:** Same as above — the three Marshallese chart types (mattang, meddo, rebbelib) are not zoom levels; they encode *different kinds of information* for *different purposes*.

**Finding:** The brainstorm presents five format levels — `text`, `annotated`, `compact`, `SVG`, `full` — as a cost ladder. Text is cheapest, full is most expensive, and annotated sits at a sweet spot. The framing is: annotated is SVG with less detail. But the mattang/meddo/rebbelib principle says purpose-differentiated formats should encode *different information*, not the same information at different fidelities. `text` encodes character content. `full` encodes character content + color + position + metadata. `annotated` (as designed) encodes character content + color. This is a strict subset of `full`, making it a zoom level, not a purpose-differentiated format. A format genuinely optimized for LLM semantic understanding would encode things `full` does not: semantic role, pane identity, UI region type, widget classification. The brainstorm's deferred scope (.6-.22) contains role annotations and multi-pane encoding — these are the purpose-differentiation, and they're cut from MVP.

**Mechanism:** A meddo chart does not include wave refraction theory; a mattang chart does not include island coordinates. Each format answers a different question. `annotated` as designed answers "what does the screen look like at lower token cost?" A purpose-differentiated format would answer "what is the terminal's semantic state right now?" — which requires structural information `full` doesn't prioritize (pane roles, widget types) while omitting information `full` includes (exact pixel-equivalent positioning).

**Recommendation:** Add one differentiating element to `annotated` that `full` does not provide: a one-line structural preamble encoding pane count, cursor position, and active pane identity. This requires ~15-20 tokens but makes `annotated` answer a genuinely different question than `full`. Something like `[screen 80x24 panes=1 cursor=12,8]` as the first token of annotated output. This preamble is the mattang-to-meddo inflection that makes the format purpose-differentiated rather than merely cheaper.

---

## [P1] Color quantization calibrated to hardware palette, not terminal semantic categories

**Agent:** fd-geez-fidel-syllabary-quantized-modification

**Source domain:** Ge'ez fidel (Ethiopic script) — a writing system that quantized continuous vowel space into 7 vowel orders via consistent geometric modifications to consonant characters. The quantization worked because boundaries were placed at *phonologically natural* categories, not at calligraphically convenient ones.

**Finding:** The brainstorm states color quantization maps "all hex/256/truecolor to 16 named colors" and that "the 16-color palette maps cleanly from the xterm defaults." The xterm-16 palette is a hardware artifact: it encodes the 8 CGA colors + 8 bright variants, a legacy of early PC video hardware from 1981. These categories are not semantically natural for terminal applications. Applications use color to signal: error, success, warning, info, path/identifier, selection, disabled, critical-metric, heading, diff-addition, diff-deletion. The xterm-16 palette crosses these semantic boundaries: "bright red" and "dark red" are two hardware variants of one semantic category (error/danger), while "bright blue" and "blue" might represent two different semantic categories (info vs. heading) in a well-designed TUI. A quantization that maps to hardware artifacts produces 16 color names that are visually accurate ("lightblue") but semantically arbitrary — the Ge'ez equivalent of a fidel vowel order system calibrated to calligraphic ease rather than phonological distinctness.

**Mechanism:** The Ge'ez fidel's 7-order quantization succeeded because it matched natural phonological categories that native speakers already distinguished. A color quantization calibrated to terminal semantic categories would match what TUI application developers already express — the categories they use when calling `tput setaf 1` (error-red) vs. `tput setaf 9` (bright-red / warning). The brainstorm's Open Question 2 ("truecolor applications will lose fidelity") hints at the problem without naming the root cause: it's not fidelity loss that matters, it's whether the quantization boundaries land at semantically meaningful divisions.

**Recommendation:** Define the 16 quantization buckets by terminal semantic function first, then determine which RGB ranges map to each. The semantic taxonomy is: error, success, warning, info, path, selection/inverse, heading, disabled, normal, diff-add, diff-del, critical, highlight, muted, background, foreground. Map xterm palette entries to these semantic buckets rather than vice versa. Concretely: change the quantization function in `.3` from "find nearest xterm-16 by visual distance" to "classify by application semantic intent using heuristic ranges." This is a ~30-line change to the color quantization helper referenced in the brainstorm as a "private helper" in `TerminalRenderer`.

---

## [P1] SVG span-merging ignores semantic boundaries

**Agent:** fd-tibetan-mandala-positional-chromatic-semantics

**Source domain:** Tibetan Buddhist sand mandala construction — four monks build simultaneously from center outward, each responsible for one directional quadrant. Adjacent quadrants may use the same color sand at a shared boundary, but each grain belongs to a different semantic context. Merging across the boundary destroys the distinction between Amitabha Buddha (west, red) and the fire element (south, red).

**Finding:** Child `.5` (SVG span-merging) proposes grouping "adjacent same-styled cells into spans." The brainstorm states this "reduces SVG from ~5000 to ~800-1500 tokens" — a strong result. But the merging algorithm as described considers only visual style equality: same foreground color, same background color, same bold/italic flags. Two adjacent cells can share all these visual properties while belonging to different semantic units: the last character of `[ERROR]` and the first character of a red-highlighted filename in the adjacent column; or two consecutive red cells from different display rows that happen to be adjacent in the SVG stream. The span-merging logic has no concept of semantic boundaries — word boundaries, field boundaries, line boundaries projected through the SVG coordinate system, or pane boundaries if multi-pane captures are ever supported (deferred to .6-.22 but architecturally adjacent).

**Mechanism:** The mandala's four monks never merge their quadrant work even when adjacent grains are the same color, because the quadrant assignment is the semantic context. Span-merging without boundary awareness is the equivalent of a fifth monk sweeping same-colored sand across quadrant lines for efficiency. The visual result is identical, but the semantic grammar is destroyed. An LLM consuming the merged SVG cannot recover the boundary: it sees one long red span where there were two semantically distinct red regions.

**Recommendation:** Add a semantic boundary set to the span-merging logic. At minimum: do not merge across newline/line-end cells (row boundaries), and do not merge across whitespace cells (which typically separate semantic units). The merge condition changes from `cell.style == prev.style` to `cell.style == prev.style AND same_row(cell, prev) AND !whitespace_gap(cell, prev)`. This is a conservative boundary: it will undermerge slightly but never overmerge across semantic units. The brainstorm references this as "span-merging adjacent same-styled cells" — add the boundary condition to the acceptance criteria for `.5`.

---

## [P2] Cursor position and active-pane identity absent from annotated format

**Agent:** fd-marshallese-stick-chart-crossmodal-encoding

**Source domain:** Cowrie shells on Marshallese stick charts mark island positions — the only *absolute-position* elements in an otherwise relational encoding. All other elements (sticks) encode relationships between wave patterns; shells encode fixed landmarks.

**Finding:** The brainstorm's annotated format encodes text content, color markers, and the inverse boolean (`[I]` for selected/focused cells). Cursor position and active-pane identity are not mentioned in the MVP scope. These are the "cowrie shells" of terminal state — absolute-position landmarks that cannot be derived from the relational encoding (color markers express what a cell looks like, not where interaction focus lies). Without cursor position, an agent cannot determine where typed input will land. Without active-pane identity (in tmux/multi-pane scenarios), an agent cannot determine which panel is receiving commands. The `inverse` boolean partially covers focus (selected items show inverse video), but cursor position is distinct from selection — a cursor can sit in an unselected cell, and the inverse flag on surrounding cells does not reveal cursor coordinates.

**Mechanism:** Stick charts without cowrie shells are navigationally incomplete: the navigator can read wave refraction patterns but cannot place themselves relative to any island. Similarly, an annotated output without cursor position and active-pane identity enables semantic understanding of screen content but not of *interaction state* — where is the agent's cursor, and which panel would receive a keypress?

**Recommendation:** Add a compact cursor-position token to the annotated format output, before the line stream: `[cursor 45,12]` (column, row, 0-indexed). If pane information is available from the terminal state, add `[pane active=0]`. These two tokens cost ~5-8 tokens and complete the absolute-position picture. This is not the same as the structural preamble in the P1 finding (fd-marshallese finding #2); that preamble covers screen dimensions and pane layout. This finding covers *interaction focus* — where is the cursor right now.

---

## [P2] BPE tokenization inconsistency across color marker names

**Agent:** fd-geez-fidel-syllabary-quantized-modification

**Source domain:** Ge'ez fidel modification grammar — the same geometric perturbation encodes the same vowel order regardless of which of the 33 base consonants it modifies. The consistency is the system's learnability guarantee.

**Finding:** The brainstorm states the `[r]...[/]` format was benchmarked as "2-3 tokens per marker pair (winner)" against alternatives. But this benchmark appears to have been run for `[r]` specifically — a one-character color abbreviation. The 16-color palette includes names of very different lengths: `[r]`, `[g]`, `[b]` versus `[cyan]`, `[white]`, `[black]` versus `[lightblue]`, `[lightcyan]`, `[lightgreen]`, `[lightmagenta]`. The brainstorm does not confirm that all 16 color marker names tokenize consistently. In cl100k and Claude's BPE, `[lightcyan]` is likely 4-5 tokens (bracket + "light" + "cyan" + bracket, possibly split further) while `[r]` is 2 tokens. If the modification grammar is inconsistent — different colors cost different token amounts — the LLM cannot learn a stable pattern and must memorize per-color costs. Worse, the token budget estimate ("400-600 tokens") will be wrong for screens dominated by long-name colors.

**Mechanism:** The fidel's power is that learning one consonant's modification pattern teaches you all 33. If some consonants used leg extensions and others used ring additions for the same vowel order, the system would require 33 × 7 memorizations instead of 7 pattern applications. Inconsistent BPE costs across color markers impose the same memorization tax on LLMs.

**Recommendation:** Before committing to full color names, run BPE token counts on all 16 marker names across both cl100k and Claude's tokenizer. If counts are inconsistent, switch to a single-character code system: `[r]`=red, `[g]`=green, `[b]`=blue, `[c]`=cyan, `[m]`=magenta, `[y]`=yellow, `[w]`=white, `[k]`=black, `[R]`=bright-red, etc. This sacrifices human readability (partially addressed by the P3 finding) for tokenization consistency. A lookup comment in the format specification (`# r=red, g=green, ...`) serves the human-readability need without infecting the token stream.

---

## [P2] Color annotations emitted without structural context preamble

**Agent:** fd-tibetan-mandala-positional-chromatic-semantics

**Source domain:** Sand mandala construction protocol — monks work strictly center-outward because outer ring meanings depend on established inner context. The central deity determines the interpretation of the surrounding cosmological court.

**Finding:** The brainstorm describes the annotated format as outputting "inline markers" for color and style within the text stream. The output is structured as a flat line-by-line stream: line 1 (with its color markers), line 2, line 3, etc. There is no structural preamble establishing screen dimensions, pane layout, or cursor position before the detail stream begins. The LLM receives character-level annotations before it has a spatial model of the screen. This is equivalent to building a mandala by scattering sand in concentric rings without first establishing the center point and ring boundaries — the outer elements cannot be correctly interpreted without the inner structure being established first.

**Mechanism:** In mandala construction, the center deity is placed first because all directional associations flow outward from it. The four monks know which quadrant is "south" because the center is fixed. An LLM interpreting `[r]Error[/]` on line 3 cannot determine whether line 3 is a status bar, a log pane, or a file listing without first knowing the screen's structural layout. The same annotation means different things in different regions — the color-free-color fallacy (P1, tibetan finding) is compounded by this ordering issue.

**Recommendation:** Prepend a 10-20 token structural header to annotated output: screen dimensions, line count, and at minimum whether the terminal appears to be single-pane or split. This is distinct from the cursor-position token (P2, marshallese finding) and the preamble in the P1 format-differentiation finding — this is specifically about establishing structural context *before* the color annotation stream begins, enabling the LLM to build a spatial model incrementally. Concretely: `[screen 220x50]\n` before the first line of annotated text.

---

## [P3] Encoding optimized for reference re-reading, not single-read comprehension

**Agent:** fd-marshallese-stick-chart-crossmodal-encoding

**Source domain:** The never-carried principle — stick charts trained the navigator's body-memory and stayed on shore. The chart is a study aid, not a reference document carried on the voyage.

**Finding:** The brainstorm does not explicitly model how LLMs will consume annotated screen captures. Two consumption patterns are plausible: (A) the LLM reads the capture once, builds an internal representation of the terminal state, and discards the capture; (B) the LLM re-reads the same capture text multiple times as it reasons about the screen, treating it as a reference document. These consumption patterns have different optimal encodings. Pattern A (single-read) benefits from density and implicit structure — the LLM extracts meaning and moves on. Pattern B (reference) benefits from explicit redundancy — repeated headers, clear delimiters, named sections. The brainstorm's format design (flat line stream with inline markers) is somewhat optimized for Pattern A but has no explicit design intent stated. If agents are expected to re-read captures (a common pattern in chain-of-thought reasoning), the encoding may need explicit structural delimiters that add tokens but reduce re-reading friction.

**Mechanism:** Stick charts were never reference documents because their value was transduced into the navigator's embodied knowledge. The information became part of the navigator, not a document. LLMs do not have embodied knowledge — they process text in context windows and may re-read the same capture text multiple times in one session.

**Recommendation:** Document the intended consumption pattern as an explicit design decision. If single-read, state that in the format specification and optimize for density. If reference-document, add structural delimiters (row numbers, section markers). This is a P3 because the current encoding is functional either way — it just lacks intentionality about which pattern it optimizes for. A one-paragraph design note in the tuivision docs would close this.

---

## [P3] Mixed-case exception in marker grammar imposes learning cost

**Agent:** fd-geez-fidel-syllabary-quantized-modification

**Source domain:** Ge'ez fidel's pattern-breaking exceptions — certain consonant+vowel combinations produce irregular forms that must be memorized rather than derived from the modification pattern. Each exception is a learning-cost tax.

**Finding:** The brainstorm uses `[r]` (lowercase) for color markers and `[I]` (uppercase) for the inverse boolean. The role attribute uses `role=error` (lowercase). This is a minor inconsistency in the marker grammar: the modification rule is "lowercase bracket tags for everything except inverse, which is uppercase `[I]`." The exception exists for a plausible reason — `[i]` might be ambiguous with italic — but the ambiguity should be examined. If italic is encoded as `[b]` (bold) with no italic marker in MVP, then `[i]` is unambiguous and the uppercase exception is unnecessary. If italic is not in MVP scope, using lowercase `[i]` for inverse avoids the grammar exception entirely.

**Mechanism:** The fidel's irregular forms exist for historical/calligraphic reasons that predate modern usage — they are technical debt inherited from the script's evolution. The uppercase `[I]` exception would similarly become inherited technical debt: once callers start using `[I]`, changing it to `[i]` is a breaking change.

**Recommendation:** Before publishing the marker format, determine whether `[i]` for inverse conflicts with any future marker. If italic, info, or any other planned marker would use `[i]`, keep `[I]`. If not, change to `[i]` now, before any callers exist, to preserve the all-lowercase modification grammar. This is a one-character change with zero runtime impact, but it must be decided before the format is released.
