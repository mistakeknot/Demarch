---
artifact_type: flux-review
track: C (Distant)
bead: sylveste-sn7
brainstorm: docs/brainstorms/2026-04-03-tuivision-token-encoding-brainstorm.md
date: 2026-04-03
reviewers:
  - fd-medieval-rubrication-marginalia
  - fd-kodo-incense-classification
  - fd-polynesian-stick-chart-navigation
  - fd-girih-geometric-tiling
---

# Track C — Distant Review: Tuivision Token Encoding

## Summary

| Severity | Count | Findings |
|----------|-------|----------|
| P0       | 0     | —        |
| P1       | 4     | Format ladder is a pure fidelity gradient, not a purpose gradient; 16-color quantization bins by visual hue rather than agent-actionable semantics; marker vocabulary lacks dynamic-state encoding; marker enumerates rather than composes |
| P2       | 5     | Monolithic annotation architecture; role= vs base color semantic conflict; marker nesting/composition undefined; per-capture full retransmission with no baseline/delta; marker density collapses urgency gradient |
| P3       | 2     | Color names should carry functional vocabulary; role= should be documented as purely additive overlay |

**Total: 11 findings (0 P0, 4 P1, 5 P2, 2 P3)**

---

## [P1] Format ladder is a pure fidelity gradient, not a purpose gradient

**Agent:** fd-polynesian-stick-chart-navigation
**Source domain:** Marshall Islands stick chart navigation — mattang (abstract wave-pattern training), meddo (regional chart), rebbelib (full archipelago chart)

**Finding:** The five-format ladder (text → compact → annotated → full → SVG) is described entirely as a cost/fidelity gradient: each step adds "more information" at higher token cost. The brainstorm frames the gap as a "25x cost gap" and the annotated format as closing it by providing the same information more cheaply. There is no articulated difference in *what kind of decision* each format serves. Text is "blind to color/style." Annotated adds "semantic color and style." Full gives "complete state." These are three levels of the same dimension (visual fidelity), not three instruments for different navigational acts.

**Structural parallel:** Marshall Islands navigators built three fundamentally distinct chart types. The mattang was not a low-resolution rebbelib — it encoded wave interference *patterns* (how swells deform near land) with no islands at all, used only for training perception. The meddo encoded specific regional relationships for a voyage in progress. The rebbelib encoded the full archipelago for planning. Each answered a different question. A fleet of rebbelibs at three zoom levels would be useless — the navigator needed the *kind* of information to change, not just the amount. The tuivision format ladder risks being three rebbelibs.

**Recommendation:** Annotate each format with the decision type it serves, not just its cost. Concretely in the brainstorm's Key Decisions section, add: text = "what does this screen contain?" (content extraction), annotated = "what is the semantic state?" (error/selection/focus parsing), full/SVG = "what does this look like precisely?" (visual comparison or screenshot diffing). This purpose labeling prevents future callers from picking format by cost alone and collapsing the ladder into a single dimension. No implementation change needed for MVP — this is a specification and documentation fix.

---

## [P1] 16-color quantization bins by visual hue, not agent-actionable semantic distinctions

**Agent:** fd-kodo-incense-classification
**Source domain:** Japanese Kodo — rikkoku-gomi taxonomy (six countries, five tastes) discretizes continuous aromatic space by preserving only the distinctions practitioners can act on

**Finding:** The brainstorm specifies "map all hex/256/truecolor to 16 named colors" to eliminate hex strings and save 400-600 tokens/screen (child .3). The 16 named colors are the standard xterm named palette: black, red, green, yellow, blue, magenta, cyan, white, and their bright variants. This discretization is organized by visual color space (hue × brightness), not by the distinctions an agent needs. The distinction between `bright-red` and `red` is a luminance distinction; the distinction between `red` (error) and `yellow` (warning) is a semantic distinction. The current design preserves both equally, with no mapping from color names to functional categories.

**Structural parallel:** Kodo's rikkoku-gomi classifies hundreds of aromatic wood types using five taste dimensions (sweet, sour, hot, salty, bitter) determined by which distinctions practitioners actually use to identify origin and quality. The system deliberately excludes olfactory dimensions that practitioners cannot reliably discriminate or act upon. A system that instead classified by wood grain pattern or fiber density — which practitioners can see but cannot smell — would be visually organized but functionally useless during a ceremony. The 16-color palette is organized by what the display produces, not by what the agent consumes.

**Recommendation:** Validate the 16-color bins against observed agent decision patterns before finalizing. The minimum discriminating set for most terminal applications is: error state, warning state, success state, neutral/content, muted/disabled, highlighted/focused, inverse/selected. This is 7 functional categories, not 16 visual ones. Either collapse the 16 to a smaller functional set, or augment the 16 names with a mapping layer (in color quantization documentation) that groups `red` + `bright-red` → error-class, `green` + `bright-green` → success-class, so agents receive the semantic grouping alongside the visual name. Concretely: add a `SEMANTIC_COLOR_GROUPS` constant alongside the quantization table in the planned color quantization helper.

---

## [P1] Marker vocabulary encodes only visual appearance, not dynamic state

**Agent:** fd-polynesian-stick-chart-navigation
**Source domain:** Marshall Islands stick charts encoded wave refraction dynamics (how swells bend around islands), not static bathymetric positions

**Finding:** The annotated format's marker vocabulary as described — `[r]`, `[b]`, `[B]`, `[I]`, `[U]`, `[D]`, with optional `role=` — is entirely a visual appearance vocabulary. Every marker describes how something looks. The inverse boolean (`[I]`) is the closest thing to a dynamic state marker: the brainstorm correctly notes that `inverse = selected/focused` is a semantic signal. But interactivity, focus, and change-since-last-capture have no representation. An agent using this format can determine "this text is red and bold" but cannot determine "this element is currently focused and accepts keyboard input" or "this value changed since my last capture."

**Structural parallel:** A stick chart navigator who saw only island positions (static bathymetry) could not navigate — they needed wave refraction patterns showing how swells deform in the presence of land, which encode the dynamic process the navigator must detect with their body. A stick chart showing only island positions is a map; one showing swell interference is a navigational instrument. The annotated format as specified is a map of the terminal's appearance, not an instrument for TUI navigation.

**Recommendation:** Add at minimum two dynamic markers for MVP — or reserve them explicitly in the specification with clear open-question framing so they are not forgotten. Suggested additions: `[F]` for focused element (receives keyboard input), `[X]` for changed since previous capture (requires diff tracking). These would allow agents to answer "where should I type?" and "what just happened?" without full-screen analysis. If diff tracking is out of MVP scope (it is listed as deferred in child .6-.22), explicitly note in the format specification that dynamic state is intentionally deferred and callers should use the inverse boolean as a focus proxy until dynamic markers are implemented.

---

## [P1] Marker vocabulary is enumerative, not generative — will require expansion for each new TUI class

**Agent:** fd-girih-geometric-tiling
**Source domain:** Girih tile system (Isfahan, 1453 CE) — five tile shapes with edge-matching rules generate patterns of arbitrary complexity without vocabulary expansion

**Finding:** The marker set (`[r]`, `[b]`, `[B]`, `[I]`, `[U]`, `[D]`, `role=error`, `role=heading`, `role=selected`) is designed by enumeration: one marker per observed terminal styling convention. Each marker names a specific visual outcome. The brainstorm acknowledges that role detection heuristics are "app-specific and fragile" (Open Question 1) but treats this as a detection problem, not a vocabulary problem. The deeper issue is that as tuivision encounters new TUI frameworks — terminal dashboards, TUI game UIs, specialized editors — new visual conventions will appear that are not covered by the current enumeration, requiring either new marker types (vocabulary expansion) or silent misclassification.

**Structural parallel:** Girih achieves arbitrary decorative complexity from exactly five tile shapes because the shapes are compositional primitives, not specific patterns. The master craftsman does not add a sixth tile when encountering a new mosque's geometry — the five tiles compose to describe any geometry. If the system had instead enumerated common Isfahan mosque patterns as tiles, it would require new tiles for each new building. The annotated format's markers currently enumerate common terminal application conventions rather than providing compositional primitives that could describe any convention.

**Recommendation:** Restructure the marker vocabulary around composable primitives rather than named conventions. The base vocabulary is already nearly there: `[r]`/`[b]`/`[g]`/`[y]` etc. are color primitives, `[B]`/`[I]`/`[U]` are style primitives. The problem is the `role=` system adds named conventions on top. Instead of `role=error`, `role=heading`, the role system should compose base markers: `role=error` means "this agent should treat this as an error state" — and the heuristics for detecting it should be documented separately from the marker itself. The marker `[r role=error]` adds no information if `[r]` already implies error-class to a well-trained agent. Document that `role=` is reserved for cases where the semantic meaning differs from what the base color implies — e.g., `[g role=warning]` for a TUI that uses green as a warning (not success).

---

## [P2] `getAnnotatedText()` risks monolithic implementation coupling content and annotation

**Agent:** fd-medieval-rubrication-marginalia
**Source domain:** Medieval manuscript production — scribe (text) and rubricator (marks) were separate specialists in separate passes, enabling the mark vocabulary to evolve without touching the text

**Finding:** The brainstorm specifies: "Add `getAnnotatedText()` alongside existing `getScreenText()` and `getScreenState()`. Color quantization as a private helper... No new files or classes needed — keeps all rendering in one place (~150 new lines)." The explicit design goal of keeping everything "in one place" and avoiding new classes exactly inverts the scribe/rubricator separation that makes annotation systems maintainable. When annotation logic is interleaved with text extraction logic, improving the color quantization algorithm requires touching the same code path as character extraction.

**Structural parallel:** Medieval scriptoria separated the scribe's text-writing pass from the rubricator's annotation pass because the two required different expertise and different revision cycles. A rubricator could improve the annotation vocabulary — add a new symbol type, change the color convention for quotation — without the scribe needing to rewrite any text. The separation also enabled parallel production: scribe finished first, left gaps, rubricator filled them independently. In the proposed `getAnnotatedText()`, color quantization is a "private helper" inside the same method that extracts characters — the rubricator and scribe are the same person.

**Recommendation:** Implement `getAnnotatedText()` as a two-phase composition rather than a monolithic method. Phase 1: call `getScreenText()` to get raw text with style data (the scribe's pass). Phase 2: pass style data through an `AnnotationLayer` helper (the rubricator's pass) that applies color quantization and emits markers. This does not require new files — it can be a private inner function — but it should be a distinct callable that takes `{ char, style }[]` and returns `string`. This separation means the annotation vocabulary can be iterated (different quantization strategies, role detection, marker format changes) without touching character extraction logic.

---

## [P2] `role=` annotation and base color markers have overlapping semantics with no precedence rule

**Agent:** fd-girih-geometric-tiling
**Source domain:** Girih strap-line overlay — decorative lines applied atop tile geometry must *enhance* without *contradicting* the underlying tile structure

**Finding:** The brainstorm introduces `role=error` as an opt-in semantic annotation and `[r]` (red marker) as a base visual marker. In most terminal applications, `role=error` and `[r]` will co-occur: the heuristic for detecting `role=error` is "red text." An agent receiving `[r role=error]text[/]` has redundant information that simply confirms what it already knew from `[r]`. But in applications where the color-to-role mapping deviates — a TUI that uses yellow for errors — an agent receives `[y role=error]text[/]`, where the base marker and the role annotation point in different directions. Open Question 1 in the brainstorm acknowledges that role detection heuristics are "app-specific and fragile," but does not address what an agent should do when base color and role annotation conflict.

**Structural parallel:** Girih strap-line decoration is designed to enhance the underlying tile geometry: the lines follow tile edges and internal symmetries, never crossing tile boundaries in ways that contradict the tiling structure. A strap-line that contradicted the tile geometry — crossing a tile boundary at an arbitrary angle — would undermine the viewer's ability to read the pattern at all. The `role=` system as underspecified can produce contradictions between base and overlay that corrupt the agent's state model.

**Recommendation:** Add one sentence to the format specification: "When `role=` is present, it is authoritative over base color for semantic interpretation. Base color remains informative for visual description. Agents should use `role=` for decision-making when present." This resolves the conflict without changing the implementation — it is a documentation addition to the format spec that should be written before child .1 ships.

---

## [P2] Marker nesting and sequencing semantics are undefined

**Agent:** fd-girih-geometric-tiling
**Source domain:** Girih edge-matching rules — local constraints on tile adjacency produce globally coherent patterns; without edge-matching rules, tiles produce incoherent mosaics

**Finding:** The brainstorm specifies markers `[r]...[/]`, `[B]...[/]`, `[I]...[/]` for color, bold, and inverse, but does not specify composition behavior. A syntax-highlighted terminal editor will routinely produce text that is both red and bold — a string literal that is also an error. The annotated format must represent this. Two representations are plausible: sequential (`[r][B]text[/][/]`) or nested (`[r][B]text[/r][/B]`), and it is unclear whether the single closing marker `[/]` closes only the immediately preceding marker, all markers, or the nearest-same-type marker. The brainstorm does not address this.

**Structural parallel:** Girih tiles connect only where their decorated edges match — a pentagon's edge connects only to another pentagon's compatible edge, not to an arbitrary decagon edge. This local constraint ensures that patterns assembled from individual tiles are globally coherent. Without edge-matching rules, tiles would be placed by eye and the pattern would be locally sensible but globally incoherent. The `[/]` closing marker without compositional semantics is a tile edge with no matching rule — it will connect to whatever is nearest, producing output that looks plausible but is structurally ambiguous.

**Recommendation:** Before child .1 implementation begins, specify: "Markers do not nest. Multiple open markers apply simultaneously until the next `[/]` which closes *all* currently open markers." This simplifies parsing and BPE encoding (no stack to maintain), at the cost of requiring a new open sequence after `[/]` if only some attributes change. Alternatively specify stacking semantics explicitly. Either decision is acceptable; the absence of any decision is not.

---

## [P2] Each `get_screen` call retransmits complete terminal state with no baseline mechanism

**Agent:** fd-polynesian-stick-chart-navigation
**Source domain:** Marshall Islands navigator's protocol — memorize the chart completely before sailing, then navigate by detecting deviations from the memorized pattern rather than re-reading the chart on every observation

**Finding:** The annotated format transmits a complete screen state on every `get_screen` call. For a multi-turn agent session automating a TUI application, most calls will observe a screen that differs from the previous call by a small amount: a value changed, a selection moved, a status message updated. The static elements — menu structure, labels, borders, column headers — are identical across calls. These elements are transmitted in full on every call despite being unchanged.

The brainstorm lists "diff mode" in the deferred children (.6-.22) but does not flag the cost structure this creates for multi-turn sessions. A 20-turn session where only 10% of the screen changes per turn is nonetheless charged for 20 full screen transmissions. The 400-600 token target applies per-call; the session cost is 20× that.

**Structural parallel:** A Pacific navigator who re-read the entire stick chart at every observation interval would exhaust their attention before completing the voyage. The mattang was memorized *once*, completely, before departure. Navigation then consisted of detecting deviations from the memorized swell pattern — the body felt what was not expected. Encoding per-observation cost is O(1) because the chart was established as a session-level baseline.

**Recommendation:** Elevate the diff-mode concept from deferred to a near-term design constraint. For MVP, add a `screen_id` or `session_hash` output field to `get_screen` annotated responses. This enables a future diff mode to refer back to a baseline without changing the MVP implementation. Document in the format spec: "Consumers may use the returned `screen_id` to construct delta requests in a future diff mode." This is a ~5-line addition to screen.ts and a spec annotation — not a full diff implementation.

---

## [P2] Marker density on heavily-styled screens collapses the urgency gradient

**Agent:** fd-medieval-rubrication-marginalia
**Source domain:** Hierarchy through mark rarity — a Lombard initial marked a major manuscript division *because* it appeared rarely; ubiquitous Lombard initials would signal nothing

**Finding:** The annotated format applies markers to every styled span on the screen. On a syntax-highlighted code editor (vim, helix, emacs), essentially every token carries a distinct color: keywords in blue, strings in red, comments in grey, operators in cyan. On such a screen, the annotated format will emit hundreds of marker pairs — `[r]`, `[b]`, `[y]`, `[c]` — in dense alternation. An agent scanning this output cannot distinguish "this is red because it is an error" from "this is red because it is a string literal" without application-specific color-to-meaning knowledge.

The brainstorm does not address the marker-to-content ratio problem for dense styling applications. The 400-600 token target likely assumes moderate styling density (a shell prompt, a TUI dashboard). A vim buffer in annotated mode could easily exceed 1000-1500 tokens as markers become more numerous than content characters.

**Structural parallel:** In 12th-century manuscripts, rubric red appeared on headings and liturgical cues — perhaps 5-10 uses per folio. Its power came from rarity within predominantly black text. A manuscript where every third word was rubricated would be illegible: the signal would become noise. The annotated format has no density floor — it will apply markers at whatever density the terminal application's styling produces, which for code editors is near-continuous.

**Recommendation:** Add a density threshold to the color quantization logic. If more than N% of cells on a screen carry non-default styling, the annotated format should either (a) apply markers only to styling that deviates from the screen's modal style (making the modal style the implicit baseline), or (b) suppress color markers and apply only semantic role markers where detected. This is a per-screen adaptive decision, not a global setting. Concretely: compute modal foreground color across all cells; suppress markers for cells matching the modal color; emit markers only for cells that deviate. This preserves the "urgency gradient" — markers appear where the screen deviates from baseline, not everywhere.

---

## [P3] Color names should carry functional vocabulary as primary, visual description as secondary

**Agent:** fd-kodo-incense-classification
**Source domain:** Kodo "listening" metaphor — monko demands active interpretive engagement; the ceremony is structured to force classification through structure, not appearance

**Finding:** The planned 16-color names are the standard xterm names: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, plus their `bright-` variants. These names describe visual hue. For an agent consuming annotated output, these names will require a learned mapping to functional meaning: agent must infer that `red` → error, `green` → success, etc., and must re-learn this mapping for each TUI application with non-standard conventions.

**Recommendation:** Expose dual naming in the color quantization output. Instead of emitting only `red`, emit `red` as the canonical name but include a `semantic` field in the format spec documentation that groups names into functional classes. Alternatively, use a naming convention that encodes function where the standard palette matches common convention: `red` → `red:error`, `green` → `green:success`, `yellow` → `yellow:warning`. This is a P3 because agents can learn the mapping empirically; it is a usability improvement, not a correctness requirement.

---

## [P3] Role= system should be documented as purely additive before MVP ships

**Agent:** fd-girih-geometric-tiling
**Source domain:** Girih strap-line overlay — decoration atop tile geometry must be structurally consistent with the tile pattern, never replacing or contradicting it

**Finding:** The brainstorm describes `role=` as opt-in and adds ~100 tokens when included. It does not specify whether `role=` is intended to be used when base color is *insufficient* (additive, non-redundant) or when the role should be *confirmed* regardless of base color (confirmatory, potentially redundant). This ambiguity will cause callers to use `role=` inconsistently: some will use it only when color is uninformative, others will include it on every styled span as belt-and-suspenders.

**Recommendation:** Add a one-sentence principle to the `include_roles` parameter documentation: "Role annotations supplement base color markers and are emitted only when the role cannot be reliably inferred from color alone (e.g., when an application uses non-standard color conventions, or when structural position rather than color determines the role)." This constrains the annotation system to remain additive rather than confirmatory, keeps the 100-token role premium meaningful, and prevents role= bloat on screens where base markers are already sufficient.
