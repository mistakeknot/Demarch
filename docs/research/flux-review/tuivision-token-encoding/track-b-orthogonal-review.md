---
artifact_type: flux-review
track: B (Orthogonal)
bead: sylveste-sn7
brainstorm: docs/brainstorms/2026-04-03-tuivision-token-encoding-brainstorm.md
date: 2026-04-02
reviewers:
  - fd-cartographic-symbology
  - fd-market-data-feed
  - fd-subtitle-caption-encoding
  - fd-avionics-data-bus
---

# Track B Orthogonal Review — Tuivision Token Encoding

## Summary

| Severity | Count |
|----------|-------|
| P0       | 1     |
| P1       | 3     |
| P2       | 3     |
| P3       | 2     |
| **Total**| **9** |

---

## [P0] Breaking default change has no consumer failure detection path

**Agent:** fd-avionics-data-bus
**Source discipline:** Avionics data bus engineering (ARINC 429, MIL-STD-1553)
**Finding:** Decision .2 changes the default `get_screen` output format from `full` (12K tokens) to `compact` without any mechanism for consumers to detect the change has happened. In avionics bus design, mandatory fields carry a label word that identifies their format version; a consumer that misreads the label will silently interpret the wrong field as valid data — a hazard class called "latent failure." The brainstorm notes this is a breaking change and mitigates by keeping `full` available, but no mechanism is specified for existing callers to (a) detect they received a different format than expected, or (b) fail loudly rather than silently misparse compact markers as raw text content.
**Operational pattern:** Avionics data buses mandate a format identifier in every message. Receivers that encounter an unknown format code must assert a "data invalid" flag and halt processing — never silently degrade. The asymmetry matters: a receiver that proceeds on bad data may take a dangerous action; one that halts surfaced a known failure mode.
**Recommendation:** Add a `format` field to every `get_screen` response envelope (e.g., `{"format": "compact", "version": 1, "content": "..."}`). This is a P0 because callers built against the current `full` format will silently receive compact output with `[r]...[/]` markers and interpret them as literal text content — a quiet corruption, not a loud error. Without this, any agent session that doesn't explicitly pin the format parameter will silently degrade on the next tuivision upgrade.

---

## [P1] Color quantization has no declared precision tier — consumers cannot calibrate expectations

**Agent:** fd-cartographic-symbology
**Source discipline:** Cartographic symbol vocabulary design and map generalization
**Finding:** The 16-color quantization (child .3) is presented as a binary: either the exact hex/truecolor color is preserved (full/SVG modes) or it is mapped to one of 16 named colors (annotated mode). Cartographic symbology engineering distinguishes between display-level generalization (acceptable loss) and classification-level generalization (semantic loss). Map features generalized below their minimum visual dimension lose meaning, not just fidelity. The brainstorm acknowledges this for truecolor apps ("image viewers, color pickers will lose fidelity") but does not specify which loss class this represents or whether the 16-color floor is a calibrated choice.
**Operational pattern:** Cartographic generalization standards (ICA, ISO 19117) require that each symbol vocabulary level carry a declared precision tier and a minimum-feature threshold below which the tier must not be applied. A physical map at 1:250000 may generalize rivers but must not generalize coastlines below 50m; the rule is stated, not implied. The annotated format lacks this: there is no statement of which terminal application classes fall below the 16-color floor's semantic threshold.
**Recommendation:** Define and document a quantization threshold rule: which classes of terminal output are semantically safe to quantize (navigation TUIs, code editors, shells) versus which should fall back to SVG or full mode automatically (color pickers, image renderers, high-fidelity visualizers). This should appear in the format selection guide, not just the open questions section. Without it, callers have no basis for choosing between annotated and SVG — they will default to annotated for everything, causing semantic loss in high-fidelity apps.

---

## [P1] Marker grammar has no reserved-character escaping specification

**Agent:** fd-subtitle-caption-encoding
**Source discipline:** Subtitle and caption encoding (SRT, WebVTT, SMPTE-TT)
**Finding:** The `[r]...[/]` inline marker grammar is defined for the happy path — styling a run of terminal output. No specification exists for what happens when the terminal output itself contains the literal strings `[r]`, `[/]`, `[I]`, or `[r role=...]`. Caption encoding standards (WebVTT §8, SRT informal spec) treat this as a primary design concern: caption text routinely contains angle brackets, slash sequences, and tag-like strings, so all inline markup formats define an escaping mechanism before declaring the format stable.
**Operational pattern:** WebVTT defines `&lt;`, `&gt;`, and `&amp;` entities specifically because caption content often contains HTML-like text (error messages with `<tag>` strings, documentation excerpts, code). The rule is: no inline marker grammar is complete until its escape sequence is specified and tested against adversarial content. SRT went unspecified on this and the result is a decade of fragmented player-specific escape handling.
**Recommendation:** Before implementing child .1, specify the escape rule for the marker grammar. The simplest approach consistent with BPE efficiency: double-bracket escaping (`[[r]]` renders as literal `[r]`). This must be in the format spec before any consumer is written against it — retroactively adding escaping is a breaking change to an already-deployed format.

---

## [P1] SVG span-merging drops the "no-advantages" claim without structural verification

**Agent:** fd-subtitle-caption-encoding
**Source discipline:** Subtitle and caption encoding — span-merge edge cases
**Finding:** Child .5 (SVG span-merging) proposes replacing per-cell `<text>` elements with merged span runs and asserts "the per-cell format has no advantages." In caption engineering, span-merge operations have well-documented edge cases: bidirectional text, zero-width joiners, combining diacritics, and ligature-sensitive fonts all produce rendering differences between per-character and per-run encoding. The brainstorm treats SVG span-merging as a pure token reduction with no semantic risk, but does not identify which SVG consumer is rendering the output and whether it is span-safe.
**Operational pattern:** WebVTT and TTML both preserve per-character positioning for ruby text and bidirectional runs precisely because span-merge produces wrong layout in these cases. The invariant is: span-merge is safe only when the renderer is character-layout-independent (i.e., monospace, left-to-right, no combining characters). Terminal output is usually safe, but "usually" is not "always," and the format claim is "no advantages" not "no advantages for typical terminal output."
**Recommendation:** Qualify the claim: span-merging is safe for monospace LTR terminal output without combining characters. Add a regression test case using a terminal that renders RTL text or combining diacritics (Arabic shell prompt, Hebrew filename). If the SVG consumer is always a fixed renderer (e.g., the tuivision screenshot pipeline), document that constraint explicitly rather than claiming the per-cell format has no advantages in the abstract.

---

## [P2] Format version signaling is absent — future schema evolution has no upgrade path

**Agent:** fd-market-data-feed
**Source discipline:** Market data feed engineering (FIX protocol, FAST encoding, SBE)
**Finding:** The annotated format is defined with no version field in its marker grammar and no version envelope in the `get_screen` response. Market data feed engineers classify this as a "cold upgrade" dependency: every consumer must be updated simultaneously with the producer because there is no in-band signal to negotiate capability. The FIX protocol's `MsgType` and `BeginString` fields exist entirely to solve this — a feed that omits them cannot be upgraded without a coordinated flag day.
**Operational pattern:** SBE (Simple Binary Encoding) and FAST both mandate a schema version in every message header. The rule is: any format that may evolve must carry its version from day one, because adding a version field later is itself a breaking change. The brainstorm defers 17 children to future iterations — each of those (LOD ladder, diff mode, dictionaries) will modify the annotated format. Without a version field, each future child is a silent breaking change to every existing consumer.
**Recommendation:** Reserve a `v` attribute in the marker grammar now: `[r v=1 ...]...[/]` or a top-level response envelope `{"format":"annotated","schema":1}`. The cost is negligible (1-2 tokens per screen); the benefit is that all 17 deferred children can be deployed without coordinated consumer upgrades. This is lower severity than the P0 only because the format is not yet deployed — the window to add versioning is open.

---

## [P2] Role detection heuristics are app-specific but treated as universally applicable

**Agent:** fd-cartographic-symbology
**Source discipline:** Cartographic symbol vocabulary — context-dependent symbol meaning
**Finding:** The ARIA-inspired role attributes (`role=error`, `role=heading`, `role=selected`) are described with heuristics tied to visual properties: bold+top-row = heading, red = error, green = success. In cartographic symbology, this pattern is called "symbol overloading" — using a single visual property to signal a category that varies by map type. A red boundary on a political map means "national border"; on a geological map it means "fault line." The heuristic is only valid within a declared context. The role heuristics in the brainstorm have the same problem: in a terminal using a red color scheme, all text is red, but none of it is an error.
**Operational pattern:** Cartographic standards require that symbol semantics be declared in a legend that is part of the map product, not inferred from visual properties alone. The legend is the context that makes symbol overloading safe. The annotated format's role detection has no equivalent — it relies on universal color-to-role mappings that break in any non-default terminal theme.
**Recommendation:** When implementing `include_roles: true`, either (a) require the caller to pass a theme context that maps colors to roles (making the heuristic explicit and overridable), or (b) restrict role detection to structural signals only (position, bold, inverse) and explicitly disclaim color-based role inference as theme-dependent. Document this limitation in the open questions resolution, not as a future-iteration concern.

---

## [P2] `[I]` inverse marker does not specify interaction with color markers

**Agent:** fd-avionics-data-bus
**Source discipline:** Avionics data bus — mandatory vs. optional field composability
**Finding:** The brainstorm specifies that inverse boolean will be preserved via an `[I]` marker (child .4) so agents can interpret selection/focus semantics. However, the grammar does not specify how `[I]` composes with `[r]` color markers on the same cell. A cell that is both red and inverse-selected has two valid marker interpretations: `[I][r]...[/][/I]` (nested), `[r I]...[/]` (combined attribute), or sequential `[I][/I][r]...[/]`. In avionics bus design, fields that can co-occur must have a defined composition rule in the ICD (Interface Control Document); the absence of a rule is treated as an underdefined interface, which triggers a review hold.
**Operational pattern:** ARINC 429 word formats specify field priority and mask order for combined status words. When two status bits can be simultaneously set, the bit-combination semantics are explicit in the standard — never left to implementer interpretation. "Undefined when both set" is a documented state, not an omission.
**Recommendation:** Define the composition rule for `[I]` and `[r]` before child .4 is implemented. The most BPE-efficient approach is a combined attribute: `[rI]...[/]` for inverse-red, treating `I` as a modifier flag alongside the color code. Specify this in the format grammar, not in implementation comments.

---

## [P3] "No new files or classes" architecture constraint is not evaluated against future children

**Agent:** fd-market-data-feed
**Source discipline:** Market data feed engineering — format version evolution and schema migration
**Finding:** The brainstorm commits to implementing the annotated format in ~150 new lines within `TerminalRenderer` and `screen.ts` as a design virtue ("keeps all rendering in one place"). Market data feed engineers recognize this pattern as "schema monolith" — all format logic in one module is appropriate when the schema is stable, but creates a merge bottleneck when the format evolves. The 17 deferred children include LOD ladder, diff mode, and dictionary encoding — each is a significant format extension. Concentrating all format logic in one renderer class means every future child touches the same file.
**Operational pattern:** FIX protocol implementations eventually extract format handling into a codec layer separate from the session layer, not because of elegance but because concurrent format evolution requires independent modification. The constraint is: single-file format logic is fine at MVP; it becomes a bottleneck at the third concurrent format extension.
**Recommendation:** The current architecture is appropriate for the 5-child MVP. Document explicitly that the format codec should be extracted to a dedicated module before child .6 (LOD ladder) is implemented. This avoids the extraction becoming an unplanned prerequisite during a future sprint.

---

## [P3] Marker grammar token count benchmarks lack adversarial test cases

**Agent:** fd-market-data-feed
**Source discipline:** Market data feed — format benchmark methodology
**Finding:** The format selection benchmarked `[r]...[/]` at 2-3 tokens per marker pair against cl100k and Claude's BPE tokenizer. Market data feed format selection uses adversarial benchmarks — worst-case payloads, not typical payloads. The 2-3 token figure is for simple color codes (`[r]`, `[b]`); longer codes like `[r role=error]` or future attributes will tokenize differently. The brainstorm notes the role attribute adds "~100 token premium" but does not break this down by attribute complexity.
**Operational pattern:** FIX encoding benchmarks test minimum, maximum, and p95 message sizes, not just typical sizes. Format selection decisions based on typical-case token counts tend to produce worse-than-expected results in production because production content is not typical.
**Recommendation:** Before finalizing the marker grammar, benchmark the full attribute space: `[r role=error]`, `[rI]` (combined inverse), `[r v=1]` (versioned), and the worst-case combined form. If any combination exceeds 6-8 tokens per marker pair, the grammar needs tightening. This is P3 because the typical-case numbers are solid; the concern is that format extensions will push into worse tokenization territory without a pre-established budget.
