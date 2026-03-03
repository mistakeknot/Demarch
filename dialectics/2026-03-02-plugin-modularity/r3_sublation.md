# Phase 5 (Round 3): Sublation — Composition Depth as Coupling Metric

## The Synthesis

The composition paradox dissolves when you stop treating composition depth as binary (shallow or deep) and recognize it as a **continuous measurement of coupling**. The depth of documentation required to compose two plugins is an empirical metric — not a classification scheme, not a stranger test, not a commit count, but a directly measurable quantity that answers the question Round 1 couldn't: **how coupled are these plugins, actually?**

Both monks assumed the gap had a single cause. It doesn't. The accuracy gap decomposes into three components:

1. **Discovery gap** (tool not surfaced) — closeable with shallow metadata: tags, co-occurrence, domain groups. This is Monk A's territory.
2. **Sequencing gap** (wrong call order, missed preconditions) — requires cross-tool knowledge of ordering and state dependencies. This is where Monk B is right.
3. **Scale gap** (inherent degradation at 50+ tools) — irreducible regardless of composition. This is where model improvements (Opus 4.5 at 88.1%) are the real solution.

The composition layer should have **heterogeneous depth per plugin pair**, matching the coupling reality of each relationship.

### The Doc Depth Litmus Test (Revised)

Monk B proposed: "measure the depth of composition docs as a coupling litmus test." This is genuinely new — but Monk B applied it as a binary (one sentence = independent, pages = consolidate). The correct application is a spectrum with different actions at each level:

| Composition Depth | What It Means | Example | Action |
|---|---|---|---|
| **None** (0 sentences) | No interaction | interflux + intermonk | Keep separate, no composition metadata needed |
| **Shallow** (1-2 sentences) | Related tools, no ordering | interflux + intercheck (review + quality) | Tags and co-occurrence groups. Interchart-style domain overlays. |
| **Moderate** (1 paragraph) | Sequencing hints, loose ordering | interlock + interpath (resolve before reserve) | One-line sequencing hints in tool descriptions: "typically called after interpath.resolve" |
| **Deep** (1+ pages) | Full sequencing, shared state, error propagation, precondition chains | (hypothetical tightly coupled pair) | **This IS the consolidation signal.** If you need pages, the boundary is wrong. Consolidate or introduce a facade/orchestrator. |

The key insight: **moderate depth is the sweet spot that both monks missed.** It's deeper than routing hints (Monk A's limit) but shallower than system specifications (Monk B's starting point). A one-line sequencing hint — "call resolve before reserve" — is not a system specification. It's a foreign key with directionality. It doesn't prove the plugins are one thing. It proves they have a known interface ordering. This is the same kind of metadata that compiler passes, Unix pipelines, and Kubernetes resources use without being "one system."

### Why This Resolves the Paradox

The paradox stated: "rich enough to close the gap → proves consolidation; thin enough to preserve independence → doesn't close the gap."

The resolution: **most of the gap is closeable at moderate depth, which doesn't prove consolidation.** Only the deep-doc cases prove consolidation — and those cases SHOULD be consolidated. The paradox is not false (Monk A's claim) or fatal (Monk B's claim). It is *diagnostic*. It applies specifically and correctly to the plugin pairs where it triggers, and those are the ones where consolidation is the right answer.

The paradox becomes a *tool*: when you try to write composition docs for a plugin pair and find yourself writing pages of sequencing, state coherence, and error handling, that is the signal. Not a stranger test. Not a commit count. Not a subjective judgment. The document itself tells you what to do.

### What This Means for Demarch's 49 Plugins

Apply the doc-depth test across the ecosystem:

- **None/Shallow (vast majority):** interflux, intermonk, interwatch, interstat, tldr-swinton, interskill, etc. These are genuinely independent. Shallow metadata (interchart-style domain overlays) is sufficient. No structural change needed.
- **Moderate:** interlock + interpath (resolve → reserve ordering), possibly interflux + intercheck (review → quality gates). Add one-line sequencing hints to tool descriptions. Keep separate.
- **Deep (if any exist):** If writing the coordination workflow context for interlock + intermux + interpath requires pages specifying shared state, error propagation, and identity contracts — that is the consolidation signal. Introduce an orchestrator tool (a coordination facade) or merge the plugins. The doc depth will tell you.

**The architect doesn't need to decide in advance.** Try writing the composition docs. If they're short, the plugins are independent. If they're long, consolidate. The metric is self-revealing.

### What This Preserves

**From Round 3 Monk A:**
- Shallow metadata works for most plugin pairs (discovery gap)
- The selection/use distinction is real — composition operates at selection time
- Co-occurrence signals from agent usage traces can generate routing metadata automatically

**From Round 3 Monk B:**
- The incidental/essential composition distinction is preserved and operationalized
- Doc depth as a coupling metric — the genuinely new tool from this round
- Essential composition (deep docs) IS consolidation evidence — applied correctly to the cases where it holds

**From Round 2:**
- Two-layer model survives: developer packaging + agent composition layer
- Uniform directory structure stays for developer; dynamic views for agent
- Interchart domain overlays as the existence proof for shallow composition

**From Round 1:**
- Sovereignty preserved for genuinely independent plugins (vast majority)
- No uniform classification system — the metric is per-pair, not per-plugin
- Priority is not architecture (from the user's correction)

### What Changed Across Three Rounds

| Round | Mechanism | Verdict |
|---|---|---|
| R1 | Stranger test (can a stranger contribute independently?) | Rejected — subjective, gameable, no empirical ground |
| R2 | Composition layer (database tables vs views) | Accepted as architecture, but composition paradox found |
| R3 | Doc depth spectrum (how much composition doc does each pair need?) | Resolves the paradox — doc depth IS the coupling metric, with different actions at each threshold |

## Abduction Test

- **Monk A is predictable:** "Shallow metadata works" — can't see that the sequencing gap requires more than routing and that some deep-doc cases warrant consolidation.
- **Monk B is predictable:** "Deep docs prove consolidation" — can't see that most plugin pairs need only moderate depth (sequencing hints) which doesn't prove coupling, and applies the litmus test as a binary when it's a spectrum.

Both are partial. Monk A correctly identifies the discovery gap. Monk B correctly identifies the essential composition indicator. Neither sees that the gap decomposes into components with different solutions, and that doc depth is a continuous metric with action thresholds. **Passes.**

Abduction type: **(c) creative** — the doc-depth spectrum as a per-pair coupling metric that resolves the paradox into a diagnostic tool is genuinely new. It doesn't recombine the monks' positions; it reframes the paradox from "structural impossibility" to "diagnostic instrument."

## New Contradictions

1. **Who writes the doc-depth test?** The architect. Which means the architect is still the judge — the "gerrymanderer" concern from Round 1 returns at a different level. Can the doc-depth test be automated or crowd-sourced?
2. **Moderate depth may creep toward deep.** A one-line sequencing hint today becomes a paragraph of error handling next month. Is there a ratchet that catches this drift?
3. **Model improvements may make all of this moot.** If Opus 5.0 achieves 92%+ accuracy with 50 tools and no composition layer, the entire three-round dialectic was solving a temporary problem. Should architecture be designed for current model limitations?
4. **The multi-agent escape persists.** Maybe the answer is not "compose tool surfaces for one agent" but "give each agent 5-7 tools and orchestrate between agents." This was never fully addressed.

## Model Update

- **Before (Round 2):** Developer packaging and agent tool surfaces are independent concerns. Build a composition layer.
- **After (Round 3):** Build the composition layer with heterogeneous depth per plugin pair. Use doc depth as a coupling metric: none/shallow → routing metadata only; moderate → sequencing hints in tool descriptions; deep → consolidation signal. The metric is self-revealing: try writing the docs, and their length tells you what to do.
- **Because:** The composition paradox is real for deep-doc cases (proving consolidation) but false for shallow/moderate cases (where routing and sequencing hints suffice). Most plugin pairs fall in the none-to-moderate range. The paradox becomes a diagnostic tool rather than a structural impossibility.
