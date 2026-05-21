# Findings — fd-marshall-rebbelib-stick-chart-pedagogy

**Target:** `/home/mk/projects/Sylveste/docs/research/flux-review/anthropic-cc-platform-gaps-sylveste/2026-05-06-target.md`
**Lens:** Marshall Islands rebbelib/mattang/meddo stick-chart pedagogy — training-time-only artifacts (the chart never goes to sea), behavior-baseline shaping vs runtime tool, somatic internalization (the navigator's spine reading lagoon swells).

---

## P0 — Anthropic ships durable memory as runtime query API without a training-time compilation primitive

**Finding.** The prior pass (target.md item 1) names "durable, hierarchical agent memory" as the deepest gap. The rebbelib lens raises a structural question the prior pass does not surface: *is durable memory shaped as a runtime query (consulted during work, paying tokens on every consultation) or as a training-time compilation (absorbed into the agent's behavior at session-start, paying tokens once)?* The Marshallese rebbelib is deliberately a training artifact — the navigator memorizes wave patterns from the chart on the beach, then sails without it. The chart never goes to sea. The Sylveste cost baseline ($2.93/landable change with a documented 2,285-token-per-session preamble trim, target.md context section) demonstrates that runtime context loading is a structural cost line; the trim *itself* is evidence that compilation is the missing primitive.

**Failure scenario.** Anthropic ships "durable memory" as a runtime API. Every plugin currently doing context-shaping (intermem, interknow, interlearn, interlore, interfluence, interlens, interscribe, interseed — eight of the 63) remains runtime-query-shaped because the API is the only primitive offered. Each session pays a query overhead per consultation. Multiply across 785 sessions/month: thousands of consultations, all token-dominant. The 2,285-token preamble trim was a one-time win against this exact cost; without compilation, the trim is structurally re-incurred every time new content is added.

**Smallest viable fix.** Target.md prior-pass item 1 should be split into two primitives, not one:
1a. *"Durable memory as runtime query API"* — for facts the agent fetches on demand.
1b. *"Training-time compilation primitive"* — for content that should modify session-start behavior, with declared content absorbed into agent baseline before first turn.

The split is load-bearing. Item 1a deprecates intermem (graduation queries) and interknow (semantic retrieval). Item 1b deprecates interfluence (voice profile applied at session start), interlens (cognitive lens conditioning), interlore (philosophy artifacts as baseline behavior), interscribe (style guides), and parts of intermem (auto-memory facts elevated to baseline). These are different shapes; the prior pass merges them.

**Plugin reclassification under the split:**

| Plugin | Currently | Under split |
|---|---|---|
| intermem | runtime + graduation | 1a (queries) + 1b (graduated facts) |
| interknow | runtime retrieval | 1a |
| interfluence | runtime style | 1b (voice as baseline) |
| interlens | runtime lens lookup | 1b (lens conditioning) |
| interlore | runtime drift detection | 1b (philosophy as baseline) |
| interscribe | runtime quality | 1b (style as baseline) |
| interlearn | runtime cross-repo | 1a |
| interseed | runtime idea garden | 1a + 1b (graduated seeds) |

Eight plugins, two primitives — currently bundled as one in the prior pass.

---

## P1 — AGENTS.md cross-vendor standardization conflates file format with compilation semantics

**Finding.** Target.md success criterion 5 names AGENTS.md cross-vendor standardization as a strategic question but treats it as a single primitive. The rebbelib lens shows the file is a *training-time artifact* and the interpretation is a *compilation behavior* — these are separable. A rebbelib that two different navigation traditions interpret with different mnemonic mappings produces nominal portability with practical fragmentation. The AGENTS.md analog: Codex, Cursor, and Gemini may all read the same file but compile its instructions into agent behavior with different semantics. The standard must specify both file format (portable) and compilation semantics (canonical, with documented vendor extensions).

**Failure scenario.** AGENTS.md v1 is published. All three vendors adopt it. Codex compiles the "tone" attribute as a system-prompt injection; Claude Code compiles it as a behavior modifier at session start; Gemini compiles it as a runtime style filter. Same file, three behaviors. Users assume portability; produce content with subtle vendor lock-in via undocumented compilation differences. Six months later, "AGENTS.md works everywhere" is technically true and operationally false.

**Smallest viable fix.** Target.md success criterion 5 should specify the strategic angle as: *"Cross-vendor standardization requires both (a) a portable file format and (b) canonical compilation semantics with explicitly documented vendor extension points. Without (b), portability is nominal."* This is the lesson the rebbelib teaches: the artifact alone is insufficient; the practitioner's compiled mastery is the runtime.

---

## P2 — Marketplace economics under runtime-tool framing miss the behavior-input opportunity

**Finding.** Target.md success criterion 5 (strategic angle) frames marketplace economics around plugins as runtime tools competing with model behavior. The rebbelib lens reframes: many plugins are *not* competing with the model — they are providing *inputs to a missing compilation step*. Voice profiles (interfluence), lens libraries (interlens), philosophy artifacts (interlore), style guides (interscribe), naming conventions (intername), agent precedent corpora (interdoc) — these all want to feed the model better baseline behavior, not interrupt the model at runtime. The current marketplace position is "plugin offers runtime tool that competes with native model capability." The rebbelib position is "plugin offers compilable input that the model absorbs into baseline before runtime." The latter is structurally more defensible.

**Failure scenario.** Anthropic ships better runtime memory + better runtime style + better runtime lenses; runtime-tool plugins die. Plugins providing compilable inputs *also* die because the prior pass did not name the compilation primitive that would have absorbed them as inputs. The marketplace loses both layers simultaneously, when only one needed to die.

**Smallest viable fix.** Add a strategic-angle paragraph to target.md: *"A training-time compilation primitive shifts marketplace economics from runtime-tool competition to behavior-baseline input feeding. Plugins providing voice, lens, philosophy, style, and naming inputs become input-feeders to native compilation, not competitors with native runtime. This is a structurally different and more defensible marketplace shape; the prior pass under-specifies it because it has not named the compilation primitive."*

---

## Counter-arguments — what NOT to build natively (the rebbelib counter-argument harvest)

Target.md success criterion 3 demands at least two strong counter-arguments. The rebbelib lens generates four:

**Counter-argument 1: Voice/style conditioning should NOT be a runtime API.**
Reasoning: voice is training-time, not runtime. A rebbelib navigator does not consult the chart while sailing — they sail with the chart compiled into perception. interfluence currently applies voice at runtime because no compilation primitive exists; if Anthropic ships compilation, voice should feed it, not become a runtime API. A runtime voice API perpetuates the runtime-cost line the trim was meant to address.

**Counter-argument 2: AGENTS.md should NOT have a runtime interpretation surface.**
Reasoning: AGENTS.md is a training-time artifact (read once, compiled into baseline). Native "AGENTS.md as runtime queryable surface" reproduces the rebbelib-on-the-canoe failure: the artifact is consulted continuously instead of compiled into mastery. Build the compilation step; let AGENTS.md remain inert at runtime.

**Counter-argument 3: Cognitive lenses should NOT be a runtime tool catalog.**
Reasoning: 288 FLUX lenses (interlens) as a runtime catalog means the agent queries the catalog when stuck — paying tokens per query, choosing per query, applying per query. The rebbelib alternative: a small subset of lenses is compiled into the agent's baseline reasoning at session start; the catalog exists for *training the compilation*, not for runtime consultation.

**Counter-argument 4: Trust scoring should NOT be a runtime dashboard.**
Reasoning: trust scoring as dashboard is runtime-consumed observability; trust scoring as routing-input modifier is compiled into the dispatch policy at decision time. The dashboard duplicates the routing decision in human-readable form; the dashboard alone, without compilation into routing, leaves the loop open.

---

## Strategic angle: the training-artifact-as-pedagogy reframing

The rebbelib's most counter-intuitive feature is that it is *deliberately not the runtime tool* — the navigator's mastery is the runtime tool. Apply to Claude Code: the strategic question is not "what runtime tools should Anthropic ship" but "what compilation primitive should Anthropic ship so that user-authored artifacts produce capable agents at session start, with minimal runtime consultation?" This inverts the prior-pass framing. The prior pass asks "what runtime APIs deprecate these 63 plugins?" The rebbelib reframing asks: *"what one compilation primitive deprecates 8-12 of these 63 plugins by absorbing their content into baseline rather than runtime?"*

---

## Defers to peer agents

- fd-heian-warifu-tally-certificates on artifact-shape, registry-vs-portable concerns, and graceful degradation (this finding focuses on training-time vs runtime classification).
- fd-yoruba-ifa-babalawo-verification-chain on integrated canon-plus-peer-review-plus-reputation protocol (this finding focuses on knowledge-compilation pedagogy and behavior-baseline shaping).
