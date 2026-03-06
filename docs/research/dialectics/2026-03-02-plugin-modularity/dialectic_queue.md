# Dialectic Queue: Plugin Modularity

## Final Status: 3 Rounds Complete — Redirected to Empirical Testing

### Round 1: "How many plugins?"
- Synthesis: "Sovereign by Design" — tiered packaging via stranger test
- Verdict: **Competent compromise.** Stranger test rejected as subjective/gameable/ungrounded.
- Surviving insight: packaging strength should be heterogeneous, not uniform

### Round 2: "Whose model wins — developer or agent?"
- Synthesis: "Two Consumers, One Codebase" — database tables/views architecture
- Verdict: **Sophisticated compromise.** Composition paradox found: rich docs prove consolidation, thin docs don't close gap.
- Surviving insights: developer packaging ≠ agent tool surface (decouple); uniform directory structure stays; interchart domain overlays as existence proof

### Round 3: "Is the composition paradox real?"
- Synthesis: "Composition Depth as Coupling Metric" — doc depth spectrum with action thresholds
- Verdict: **Both positions restated as conjunction** (auditor). Moderate tier is underexamined, unfalsifiable, and may be a polite fiction. The real answer requires empirical measurement, not philosophical argument.
- Surviving insights: the paradox is diagnostic (fires correctly for deep-doc cases); gap has multiple causes (discovery + sequencing + scale); co-occurrence telemetry may auto-generate the composition layer

## Stable Conclusions (Agreed Across All Rounds)

1. **Keep uniform directory structure.** No tiers, no classification, no heterogeneous packaging. The monorepo's uniform structure is genuine infrastructure. (Universally agreed R1-R3.)

2. **The agent is a first-class consumer.** Token cost and selection cost are both real. 92%→74% accuracy gap with Tool Search. The developer's conceptual model should not be the agent's operational model. (Accepted R2, reinforced R3.)

3. **Developer packaging and agent views should be decoupled.** Same code, different access patterns — like database tables and views. Interchart domain overlays are the visualization-layer existence proof. (Accepted R2.)

4. **Static classification fails.** Stranger test, commit history, tier tables — all produce governance overhead, Goodhart targets, and stale labels. (Rejected R1, reinforced R2-R3.)

5. **Static workflow bundling fails.** Agent workflows are emergent and overlapping. Packaging by workflow produces overlapping boundaries or code duplication. (Rejected R2, confirmed R3.)

6. **Some plugin pairs may genuinely be over-separated.** The composition paradox fires correctly for deeply-coupled clusters. If writing their composition docs produces pages of sequencing, shared state, and error handling, that IS the consolidation signal. (Emerged R2, refined R3.)

## The Redirect: From Philosophy to Engineering

The dialectic's most important output is the **redirect**: the question "should we have 49 plugins or 10?" cannot be answered philosophically. It must be answered empirically.

### Actionable Engineering Steps

**Step 1: Instrument agent sessions.**
Measure where tool selection actually fails. For each failure, classify:
- Discovery failure: agent didn't surface the right tool candidate
- Sequencing failure: agent found the right tools but called them in wrong order or missed preconditions
- Scale degradation: inherent accuracy loss at 50+ tools regardless of composition

**Step 2: Build shallow composition layer.**
Using interchart's existing architecture (pattern rules + forced groups), create tool-routing metadata:
- Tags and domain groupings (discovery)
- Co-occurrence signals from successful sessions (auto-generated routing)
- One-line sequencing hints where data shows sequencing failures ("typically called after interpath.resolve")

**Step 3: Measure the gap.**
Compare agent accuracy with and without composition layer on the same tasks. The 18-point gap (74% → 92%) decomposes into:
- Portion closed by shallow metadata → this much is "just infrastructure" (Monk A wins)
- Portion requiring sequencing knowledge → this much needs moderate composition (new territory)
- Portion requiring deep docs → for these pairs, consolidation is the honest response (Monk B wins)
- Irreducible scale portion → wait for model improvements (Opus 4.5 already at 88.1%)

**Step 4: Let data determine plugin boundaries.**
For each plugin pair with high sequencing failure rates:
- If one-line hints close it → keep separate, add hint to tool description
- If hints don't close it and deep docs are needed → consolidate or introduce facade
- If model improvements close it → do nothing, the problem is temporary

### What NOT To Do
- Don't reclassify 49 plugins into tiers (R1's rejected approach)
- Don't statically bundle plugins by workflow (R2's rejected approach)
- Don't hand-author a comprehensive composition documentation system (R3's audit finding: unmaintainable)
- Don't wait for a perfect framework before building the shallow composition layer

## Open Questions (For Future Rounds If Needed)

1. **Is the moderate band real or a polite fiction?** Requires the empirical audit from Step 3. If 60%+ of interacting pairs genuinely need only one-line hints, the synthesis holds. If pairs cluster bimodally (shallow or deep), Monk B is right.

2. **Can co-occurrence telemetry auto-generate composition?** If successful agent sessions produce co-invocation patterns that serve as routing + sequencing data, the composition layer is learned, not authored. This changes everything.

3. **Will model improvements make this moot?** Opus 4.5 at 88.1%. If Opus 5.0 hits 92%+ with 50 tools, the architecture question dissolves into "just upgrade the model."

4. **The multi-agent escape.** Maybe the answer is not "compose tool surfaces for one agent" but "fewer tools per agent, more agents per task." Never fully explored.
