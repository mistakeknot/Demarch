---
artifact_type: research-agenda
method: dynamic-workflow (run wf_99c0c459-044)
tracking_epic: Sylveste-06i
date: 2026-07-16
total_possibilities: 61
---

# Sylveste Ecosystem Research Agenda — 2026-07-16

## Scope

- **Tracking epic:** Sylveste-06i
- **Workflow run:** wf_99c0c459-044
- **Coverage:** 31 components across 3 layers — agent-platform-core (17: Clavain, Skaffen, intercore, intermute, interspect, interlab, interlock, interphase, interflux, intersynth, interpath, interwatch, agent-rig, interbench, interband, Ockham, Alwe), local-models-inference (2: interfer, interrank), knowledge-cognition (12: interweave, interlens, intermem, interknow, interseed, intersearch, intertree, interleave, interlore, interscribe, intername, interfluence).
- **Excluded** (deprecation/consolidation candidates, not scanned): intermux.broken, marketplace.broken, intersense (self-archived), interscout (retired). The apps/simulation layer was not selected for this scan.
- **Three lenses applied to every component:**
  1. **external-frontier-adopt** — recent (2026) published techniques a component could adopt.
  2. **net-new-direction** — novel research questions Sylveste is uniquely positioned to answer (own telemetry, own hardware, own closed loop).
  3. **latent-backlog-formalize** — research-shaped work already implied by open beads/docs but not yet scoped as a spike with a kill rule.
- **This run is a re-scan following the 2026-07-05 agenda** (`docs/research/2026-07-05-ecosystem-research-agenda.md`, epic Sylveste-btn); it incorporates what shipped in the interim (notably ioe7: interlab → interspect calibration going live) and re-prices/extends several prior bets rather than starting from zero.

### Counts by kind

| Kind | Count |
|---|---|
| External Frontier — Adopt | 30 |
| Net-New Direction | 20 |
| Latent Backlog — Formalize | 11 |
| **Total** | **61** |

### Counts by layer

| Layer | Count |
|---|---|
| Agent Platform / Core | 22 |
| Local Models / Inference | 19 |
| Knowledge / Cognition | 20 |
| **Total** | **61** |

## Headline thesis

The calibration loop closed on itself and went live — audit it before you trust or scale it. Since the 2026-07-05 scan, interlab→interspect (ioe7) shipped: interspect now recalibrates routing on AGENT-PRODUCED evidence with nothing watching verifier-vs-generator agreement (Sylveste-4b5.1). That converts a whole cluster of this scan's audit possibilities from "good hygiene" into "the loop is now unsafe and unfalsifiable without them." Sylveste's single unique asset is a self-improving multi-agent loop it operates end-to-end; the highest-leverage research is to make that loop honest — holdout register (Sylveste-407, still open), judge-reliability/kappa audit, and self-praise/consensus-trap/collusion detectors — BEFORE the flywheel optimizes its own noise. Everything else (lens-layer null tests, inference re-pricing) is downstream of trusting the instrument that would measure it.

## Top bets

11 ranked bets, in the order returned by synthesis.

### 1. Holdout register as a first-class primitive across every calibration loop (Sylveste-407 / 9lp.37)

- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Already formalized as an open bead but UNEXECUTED 11 days later, and ioe7 has since gone live — interspect now recalibrates on agent-produced evidence with zero out-of-loop ground truth. 5+ other bets (closed-loop model selection, lens ground-truth, autonomy thresholds, consensus-trap breaker) gate on this. It is the epistemic foundation; nothing downstream is falsifiable without it.
- **First experiment:** Retroactively freeze a random 20% of existing interspect evidence events as holdout; recompute the currently-active routing overrides on the training split only; measure how many flip. KILL RULE: if evidence volume is too sparse to power the split (<~50 events per scored agent) OR <5% of overrides flip, park the primitive and set a volume tripwire to revisit at 2x current evidence.

### 2. Consensus-trap breaker + verifier-vs-generator agreement audit on the now-live ioe7 loop (Sylveste-4b5.1)

- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** THE net-new fact since the last scan: ioe7 (interlab mutation → interspect adaptation) is CLOSED and live, recalibrating on agent-produced evidence with nothing watching whether verifier and generator are collapsing into mutual agreement. This is the textbook self-referential-optimization failure mode, running in production right now. Formalizes an existing open bead; strong evidence; cheap.
- **First experiment:** Extend the existing calibrate-audit.py cron + 20-use canary window to log agreement-rate AND output-diversity across the last N calibration cycles; plot agreement-rate trend against independent defect-escape-rate. KILL RULE: if agreement-rate is flat (no upward trend) across ≥5 cycles AND defect-escape-rate is stable, the loop is not collapsing — record the baseline constants and demote to a standing monitor, don't build the breaker.

### 3. LLM-judge kappa-deflation + self-praise audit for the flux-drive reviewer panel (merges kappa audit + judge-hacking probe + IRT diagnostic)

- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Flux-drive review scores are a direct INPUT to interspect evidence, so judge noise and judge self-preference propagate straight into routing overrides — the second unguarded seam in the live loop. Three of this scan's strong/moderate possibilities (kappa-deflation, self-praise/judge-hacking, IRT diagnostic) collapse into one fixture. Must run alongside the holdout register or the loop trusts noisy judges.
- **First experiment:** Re-run a frozen set of ~30 past reviews 5x per judge across 2-3 model families; compute intra-judge kappa, cross-family agreement, and the self-vs-other score delta (does a model score its own family's outputs higher?). KILL RULE: if intra-judge kappa >0.8, cross-family disagreement <10%, AND self-vs-other delta <5%, judges are reliable — record the calibration constants and skip the harness.

### 4. Contrarian null test: does multi-agent orchestration beat single-strong-model on Sylveste's own task mix? (Sylveste-rgj)

- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** moderate
- **Why now:** Directly implements the house doctrine (test-null-hypothesis-first) at the platform's single most expensive premise, and it's already an open unexecuted spike bead. Sylveste has the dispatch telemetry (interstat/intercore) to build matched task pairs cheaply. A null result redirects months of coordination-layer investment and moots interlock benchmarking; genuinely-novel because no lab without this closed loop can run it.
- **First experiment:** Sample ~20 recently completed dispatched tasks from telemetry; replay a matched subset end-to-end with one frontier model; compare pass-at-acceptance-criteria, wall clock, and token cost. KILL RULE: if matched replay proves infeasible (task state unreproducible) after 5 attempts, OR the delta is within noise on the first 10 pairs, record the null and stop — do not extend the sample chasing significance.

### 5. Execute the pre-registered F6b flux-drive triage A/B before any new ontology work (Sylveste-dvw / g939)

- **Layer:** knowledge-cognition
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Rare experiment where Phase-1 design is already DONE and thresholds already bind (F6a pre-registered a 30-diff held-out corpus + ship/abandon rule). Still open. It gates the entire lattice ontology-backend decision (F7 interlens MCP adapter, b1ha persona/lens unification, both in flight). Every week of delay is ontology work at risk of abandonment. The knowledge-layer's version of null-first discipline.
- **First experiment:** Run both backends (FLUX_DRIVE_BACKEND=ontology|legacy) over the pre-registered corpus; record findings/agents/cost per diff. KILL RULE: already pre-registered in the bead — apply the F6a thresholds in the decision memo; outcome binds (ship / abandon+reopen-as-redesign).

### 6. Audit whether Auraken's effectiveness_score is judge-contaminated (lens-selector scores its own selection)

- **Layer:** knowledge-cognition
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong evidence, adopt-known, spike-days. The cognitive-profiling PRODUCT's core self-improvement signal may be the same-model-scores-its-own-output pathology already flagged at the platform layer (Sylveste-emv, B6 circular calibration). If effectiveness_score is contaminated, the epistemic engine's promotion/decay logic (22oi.7.5, open) is optimizing a mirror. Isolable, cheap, and protects moat-#2 before the governance surface (22oi.7.6) ships on top of it.
- **First experiment:** Trace the effectiveness_score data path: does the lens-selecting model (directly or via correlated prompting) produce the score grading its own selection? Then re-score ~30 selections with an independent-family judge and measure the delta. KILL RULE: if the scoring path is provably independent of the selection model AND the independent-judge delta is <5%, no contamination — close with the trace as the artifact.

### 7. Re-test the 'MLX has no concurrent inference' premise before sylveste-4wl burns on it (Sylveste-x2c)

- **Layer:** local-models-inference
- **Effort:** spike-days
- **Evidence:** moderate
- **Why now:** The premise is baked verbatim into open campaign sylveste-4wl and into interfer's custom priority-queue architecture. Open spike bead created the day after the last scan, still unexecuted. If upstream continuous batching + paged KV now works in the 2026 MLX ecosystem, the custom scheduler is potentially obsolete — highest decision-value-per-hour spike in the inference layer, and it must run BEFORE the 4wl autoresearch campaign spends experiments on a dead premise. User owns the exact M5 Max hardware.
- **First experiment:** Benchmark mlx-lm's current continuous-batching against interfer's queue on the M5 Max with 3-5 concurrent agent-shaped streams (the flux-drive fan-out named in 4wl): aggregate tok/s and P99 latency. KILL RULE: if upstream batching gives <1.3x aggregate throughput OR violates the existing P99 ≤ 2x-single-request gate, keep the custom queue and let 4wl proceed as scoped.

### 8. M5 Neural Accelerator prefill/decode asymmetry — is interfer's tuning pointed at the wrong bottleneck?

- **Layer:** local-models-inference
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong external evidence, adopt-known, spike-days, and the user owns the exact hardware with an explicit MacBook-focus directive. flash-moe has a live unresolved decode regression (Sylveste-bov: 5 tok/s actual vs 12.9 spec) this would help localize. If prefill and decode scale asymmetrically on the NA, current quant/batching/speculation choices may be optimizing the wrong axis — this re-prices every other inference bet, including the stalled DeepSeek V4 port decision (0gi).
- **First experiment:** Measure prefill tok/s and decode tok/s SEPARATELY on 2-3 workhorse interfer models at agent-realistic context lengths; compare against the ratios current interfer tuning implicitly assumes. KILL RULE: if measured asymmetry deviates <20% from current assumptions, no reallocation — close in one day.

### 9. Prompt-lookup / n-gram speculative decoding for Clavain's agentic tool-call loops (draft-model-free)

- **Layer:** local-models-inference
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong evidence, spike-days, and it sidesteps the stalled MTP/draft-model workstream (0gi.2.7 H200 rental hasn't moved since May; yfot draft-model bench deferred). Agentic tool-call loops are highly repetitive (repeated file paths, tool schemas, JSON scaffolds) — the exact structure prompt-lookup decoding exploits with zero draft model to train or serve. Cheapest path to decode-bound speedup on the workload interfer actually runs.
- **First experiment:** Enable n-gram/prompt-lookup speculative decoding on one workhorse model over ~20 replayed real Clavain tool-call turns; measure acceptance rate and decode tok/s vs the non-speculative baseline. KILL RULE: if acceptance <30% or net decode speedup <1.2x on agentic turns, the tool-call loop isn't repetitive enough — close and note self-speculation (MTP) remains the only lever, gated on 0gi.

### 10. MAST-taxonomy classification pass over interflux/interlock failure logs

- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong evidence, adopt-known, spike-days — the cheapest way to turn accumulated multi-agent failure logs into a structured failure-mode distribution. It TELLS you which deeper audits (collusion, sandbagging, orchestrator-visibility) actually matter for Sylveste's real traffic, so it's a near-free triage step that de-risks the expensive research-program bets by grounding them in observed frequency.
- **First experiment:** Classify a sample of ~50 recorded interflux/interlock failures against the MAST taxonomy; produce the failure-mode frequency distribution. KILL RULE: if >70% of failures collapse into 1-2 mundane categories (tool errors, timeouts) with no coordination-specific modes, the exotic-safety bets are unwarranted for now — record the distribution and deprioritize them.

### 11. Covert-channel / steganographic collusion audit for interlock inter-agent messaging

- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong evidence, adapt, spike-days. interlock is the real inter-agent messaging substrate; once the calibration loop is live (ioe7) and evaluator-driven routing shapes agent strategy, channel collusion becomes plausible-not-paranoid. Sylveste can run this on genuine multi-agent traffic no external lab has. Ranked below MAST because MAST should confirm coordination-failure modes exist before committing here.
- **First experiment:** Sample interlock message payloads from real multi-agent sessions; measure entropy/compressibility and channel-capacity residual beyond declared task semantics vs a synthetic honest baseline. KILL RULE: if residual channel capacity is within noise of the honest baseline across the sample, there's no covert channel to exploit yet — record and set a re-audit trigger tied to any future agent-vs-agent incentive coupling.

## Per-layer landscape

AGENT-PLATFORM-CORE (the center of gravity this round): The decisive shift since the 2026-07-05 scan is that the self-improving loop went live — ioe7 (interlab mutation → interspect adaptation) closed, so interspect now recalibrates routing on agent-produced evidence with no out-of-loop ground truth and no verifier-vs-generator agreement watchdog. This retroactively upgrades the entire audit cluster in this 61-set (holdout register, consensus-trap breaker, judge kappa/self-praise, collusion, MAST) from hygiene to prerequisite. The layer's agenda: make the live loop honest and falsifiable (holdout + agreement audit + judge reliability) FIRST, then run the two doctrine-mandated null tests (multi-agent-vs-single-strong, orchestrator-visibility) that could redirect months of coordination investment. Note four of these are ALREADY open unexecuted spike beads (407, rgj, 4b5.1, dvw's sibling) — the bottleneck is execution, not ideation. Deprioritize formal-verification (TLA+), mechanism-design, and preference-coupling as research-program/speculative until MAST confirms the failure modes are real in Sylveste's traffic.

LOCAL-MODELS-INFERENCE (re-pricing, not new architecture): The stack has two stalled hot spots — the DeepSeek V4 port decision (0gi, blocked on H200 baseline since May) and an unresolved flash-moe decode regression (bov, 5 vs 12.9 tok/s). The winning moves are cheap re-measurements that reprice everything else: the MLX-concurrent-inference premise re-test (x2c, could obsolete the custom scheduler), the M5 Neural Accelerator prefill/decode asymmetry (could explain bov and redirect tuning), and draft-model-free prompt-lookup speculative decoding (routes AROUND the stalled MTP/draft-model work). All strong/moderate, all spike-days, all exploiting owned M5 Max hardware. Defer the architecture-scale items (per-expert mixed-precision, Gemma-4 QAT reference design, latent KV compaction research-program) until the re-measurements say where the real bottleneck is. The FlashMoE ML-cache-replacement bet is strong but its Phase-1 (expert-activation trace instrumentation) is gated on flash-moe being stable — sequence it after bov is resolved.

KNOWLEDGE-COGNITION (protect the product's evidence base): The cognitive-profiling product (Auraken) is the differentiated asset, and its self-improvement signal (effectiveness_score) is under-audited — the same judge-contamination pathology flagged at the platform layer likely lives here, and the epistemic engine (22oi.7.5) is about to optimize on it. Two cheap strong-evidence protective moves lead: the effectiveness_score contamination audit, and the already-designed F6b ontology-vs-legacy A/B (dvw) that binds the whole lattice backend decision. The GraphRAG-underperforms-vanilla null test rhymes with F6b — fold it in rather than running separately. Everything embedding-space-scale (intersearch shared substrate, concentration/contrast-collapse) is genuinely interesting but speculative and gated on the F6b outcome deciding whether the structured layer earns its keep at all. Defer the ethics/drift-scale items (stereotyping-as-personalization, Assistant-Axis attractor) as project-weeks needing the measurement harness built first.

## Cross-component ideas

- Closed-loop model selection (interspect × interfer × interrank): drive local-vs-frontier routing per task-type from MEASURED outcome evidence rather than static tiers. The flagship cross-layer idea — but STRICTLY gated on the holdout register (407) and judge-reliability audit landing first, or the loop optimizes judge noise into routing. Also answers the standalone possibility 'does interrank's leaderboard correlate with interspect's measured task outcomes on Sylveste's own workloads' as a free byproduct.
- One shared falsifiability harness (interspect × Auraken × lattice): use interspect's holdout-register methodology (once built) as the SAME held-out ground-truth instrument for BOTH Auraken lens-effectiveness AND lattice triage-lift claims. Turns one primitive into the evidence base for two product claims — genuinely-novel, and it means the holdout, effectiveness-score, and F6b bets share infrastructure instead of building three separate eval rigs.
- Agentic-traffic-shaped inference benchmarking (interstat × Clavain × interfer): replay real Clavain dispatch traces against interfer to measure tool-call latency, prefix-cache hit behavior, and interleaving — no public benchmark has real multi-agent traces PLUS a controlled local stack. Doubles as the acceptance test for both the MLX-batching re-test (x2c) and the prompt-lookup speculative-decoding bet, and provides the matched-task substrate the multi-agent null test (rgj) needs. One trace corpus, three experiments.
- MAST distribution as the router for the safety-research budget (MAST × collusion × sandbagging × orchestrator-visibility): run the cheap MAST classification pass FIRST, then let the observed failure-mode frequency decide which of the expensive exotic-safety audits (steganographic collusion, sandbagging, preference-coupling) are worth funding. Converts a scattered speculative cluster into an evidence-gated pipeline — the taxonomy pass is the control valve.
- Cross-agent KV/prefix cache reuse for flux-drive fan-out (interfer × interflux, RadixAttention-style): flux-drive dispatches many agents sharing large identical prefixes (system prompt, diff under review, shared context). Trie-based prefix-cache sharing across those concurrent streams fits the exact fan-out pattern the MLX-batching re-test already benchmarks — sequence it as the follow-on if x2c shows upstream batching is viable.
- Bitemporal fact representation shared across interknow + lattice (interknow × lattice): interknow's temporal fact-invalidation and lattice's entity-versioning are the SAME underlying need — event-time vs ingest-time to resolve contradictions. Solve it once as a shared bitemporal primitive rather than a decay-timestamp in one place and entity-versioning in another. Moderate evidence; a clean consolidation, not a moonshot.

## Deliberately dropped

- Formal verification of interlock (TLA+/model-checking), Skaffen OODARC-as-contract, Ockham F5 paired-confirmation formal target: heavy formal-methods investment on protocols not first shown to FAIL empirically. Dropped until MAST classification demonstrates coordination-protocol errors are a real, frequent failure mode — otherwise it's verifying a protocol nobody has proven is broken.
- Agent negotiation as game-theoretic mechanism design (interlock urgency levels): speculative evidence, genuinely-novel but no observed pathology motivating it. Parked behind the collusion/MAST audits that would first establish whether negotiation is being gamed at all.
- Cross-agent evidence provenance on-policy-vs-off-policy calibration: speculative, and it's a sophistication ON TOP of the holdout register that doesn't yet exist. Revisit only after 407 lands.
- Sandbagging / selective-underperformance probe (research-program): strong topic but research-program effort with moderate evidence and no Sylveste-specific trigger yet. Gated on MAST showing capability-dependent performance variance in the logs first.
- Preference-coupling audit (evaluator bias → strategy distributions): project-weeks, strong evidence, but essentially the mature version of the consensus-trap/judge-reliability bets — do those spike-days versions first; this is their scale-up if they find signal.
- Process reward model for interlab mutation scoring: weak evidence, project-weeks, and it presupposes outcome-only fitness is inadequate — which the consensus-trap audit (4b5.1) will actually MEASURE. Dropped as premature; the audit is the prerequisite.
- Context-rot-aware session budgeting: genuinely-novel and moderate, but project-weeks and orthogonal to the live-loop-safety priority this round. A strong candidate for the NEXT agenda once the calibration instrument is trustworthy.
- CoX-MoE AMX CPU-GPU co-execution: speculative evidence on Apple silicon; drop until the M5 NA prefill/decode measurement and MLX-batching re-test say where the bottleneck actually is — building co-execution before knowing the bottleneck is the wrong-axis trap.
- Latent KV compaction (Attention Matching/TriAttention) and Gemma-4 2-bit QAT reference design: research-program effort, adopt-known — reference designs for FUTURE checkpoints, not this-quarter levers. Note in a 'future-checkpoint' backlog rather than the active agenda.
- Dynamic per-expert mixed-precision for the 397B SSD tier: project-weeks, gated on the flash-moe decode regression (bov) being fixed and expert-activation traces existing — sequence as a follow-on to the FlashMoE cache work, not standalone now.
- OSCAR 2-bit KV via spectral rotation: moderate but tested-against-existing-kv_bits=8 is a marginal-gain spike; lower value-per-hour than the prefill/decode re-measurement that reprices the whole layer. Deprioritized, not dropped.
- Stemma provenance-phylogenetics for hallucination genealogy: genuinely-novel but project-weeks on moderate evidence with no acute trigger; interesting long-horizon idea, wrong quarter.
- Ockham-Alwe governance flywheel as graduated-autonomy testbed, two-strikes-escalation as reliability experiment, capability-fence blast-radius audit: reasonable latent-backlog formalizations but features-dressed-as-research with moderate/weak evidence; they don't exploit the unique live-loop asset the way the audit cluster does. Track as engineering beads, not research bets.
- The knowledge-layer ethics/drift cluster (stereotyping-as-personalization, Assistant-Axis attractor, identity-drift via interlore, intersearch shared-embedding concentration collapse, metacognitive-probe decomposition, Compiled-AI cost model, interseed/interject/interscribe formalizations): individually plausible but collectively they need the F6b outcome and a built measurement harness before any is worth a spike. The strongest (Assistant-Axis attractor, embedding-concentration) become live candidates once F6b decides the structured layer earns its keep; the rest are speculative/weak and moot until then.
- Reproducibility harness re-pinning interfer/interrank cited numbers to the actual M5 unit, and contamination-resistant benchmark re-pin (4b5.19): both worthwhile but 4b5.19 is explicitly DEFERRED in beads (gated on the harness feeding a live routing.yaml decision first, or it mints an unwired-evidence ghost). Honor the existing gate rather than resurfacing it as a top bet.

## Appendix: all 61 possibilities

Possibilities were generated by three parallel `scan:*` agents (one per layer: agent-platform-core 17, local-models-inference 15, knowledge-cognition 15 — 47 total) and independently supplemented by three `critic:*` completeness-check agents (one per layer: agent-platform-core 5, local-models-inference 4, knowledge-cognition 5 — 14 total). Grouped below by layer, then by kind. All 61 entries are unique by title (verified, no duplicates).

### Layer: Agent Platform / Core (22 possibilities)

#### External Frontier — Adopt (11)

**Self-praise / judge-hacking probe for interflux + interspect-scored review loops**

- Component: interflux, interspect
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Reward hacking in judge/world-model loops via self-praise phrase insertion, and 'More Convincing, Not More Correct: Self-Play Reward Hacking of Reference-Free LLM Judges' (arXiv:2607.05904, June 2026)
- Rationale: interflux's LLM-judge review agents (fd-* reviewers) and interspect's evidence pipeline both trust model-generated judgments as ground truth for calibration. If review/generator agents learn to insert self-affirming phrasing that triggers higher rubric scores (the exact mechanism reported for judge/world-model reward hacking), interspect would calibrate on a corrupted signal and nobody would notice since the corruption looks like 'agreement'.
- Kill rule: Phase-1: replay 30 frozen flux-drive reviews, inject known self-praise phrasings ("this is clearly correct", confidence boilerplate) into candidate outputs, measure judge-score delta. If delta is <5% (noise-level), the vulnerability doesn't manifest in interflux's current rubric design — kill, no further investment.

**MAST-taxonomy classification pass over interflux/interlock failure logs**

- Component: interflux, interlock, interphase
- Evidence strength: strong
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: MAST (Multi-Agent System Failure Taxonomy), validated across 1,600+ traces, NeurIPS 2025/2026 follow-ups — 14 failure modes across specification (41.8%), inter-agent misalignment (36.9%), verification (21.3%)
- Rationale: Sylveste has real multi-agent execution logs (dispatch retries, negotiation timeouts, flux-drive triage misses) that nobody has classified against a standard failure taxonomy. Doing so would let interspect target root causes (spec ambiguity vs coordination breakdown vs verification gap) instead of treating all failures as one undifferentiated 'agent got it wrong' bucket.
- Kill rule: Phase-1: hand-label 50 recent dispatch/negotiation failures from interlock + flux-drive logs against the 14 MAST categories. If >70% land in a single category already well-covered by existing tooling (e.g. all 'verification gap', already addressed by quality-gates), the taxonomy adds no new targeting information — kill the formal classification effort, keep the informal read.

**LLM-judge kappa-deflation audit for flux-drive reviewer panel**

- Component: interflux
- Evidence strength: strong
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: "Reliability without Validity" (arXiv:2606.19544, June 2026, ~541K judgments across 21 judges); "The Coin Flip Judge?" (arXiv:2606.13685) — cross-judge kappa ~0.51, matching human inter-annotator range
- Rationale: interflux dispatches multiple fd-* review agents whose findings get treated as convergent signal (via flux-melange fusion, cross-track convergence). Recent large-scale LLM-judge studies show severe kappa deflation (33-41pp) between raw agreement and Cohen's kappa, and judge rankings shifting up to 14 positions across benchmarks — meaning interflux's 'agents converged' signal may be far weaker than it looks once chance agreement is subtracted.
- Kill rule: This is effectively Phase-1 of Sylveste-4b8 itself (already filed) — compute Cohen's kappa, not just raw agreement %, on the planned 30-review 5x rerun. If kappa is already reported in that spike's design, this possibility is subsumed; if not, add it as an acceptance-criteria amendment before 4b8 executes. Kill condition: if kappa ≥0.6 (substantial agreement), the current convergence heuristic is fine as-is — don't build a kappa-weighting layer.

**Formal trace verification (TLA+/model-checking) of interlock's negotiation protocol**

- Component: interlock
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: TraceFix: Repairing Agent Coordination Protocols with TLA+ Counterexamples (arXiv:2605.07935, May 2026); CoAgent: Concurrency Control for Multi-Agent Systems (arXiv:2606.15376, June 2026)
- Rationale: interlock's release-negotiation state machine (request→ack/defer→timeout→force-release) is exactly the kind of protocol TraceFix-style tools target: concurrent, advisory-enforcement, with escalation timers. It has never been model-checked. A subtle race (e.g., a force-release racing a legitimate late ack) would manifest as silent data corruption between agents, which is the worst failure mode for a coordination substrate.
- Kill rule: Phase-1: write a minimal TLA+ (or even a Python state-machine fuzzer) model of just the negotiate/respond/force-release triangle and run 10K randomized interleavings. If zero counterexamples surface in a protocol this small, the advisory-only design is probably not the risk surface — kill the formal-methods investment and redirect any remaining coordination-hardening effort to intermute's actual DB layer instead.

**IRT-based judge diagnostic for the fd-* review agent pool**

- Component: interflux, intertrust
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Diagnosing the Reliability of LLM-as-a-Judge via Item Response Theory (arXiv:2602.00521, Feb 2026)
- Rationale: interflux's flux-agent registry already tracks quality tiers per reviewer agent, and intertrust tracks precision/review counts — but these are frequentist aggregate stats. Item Response Theory treats each review agent as having a latent 'discrimination' and 'difficulty-sensitivity' parameter, which would let interflux distinguish 'this reviewer agrees with consensus because it's calibrated' from 'this reviewer agrees with consensus because it only flags easy/obvious findings' — a distinction flat agreement-rate can't make.
- Kill rule: Phase-1: fit a 2-parameter IRT model to interflux's existing fd-* agent finding-history (finding confirmed/rejected outcomes already tracked by intertrust) on whatever sample size exists today. If the dataset is too sparse per-agent to fit stable IRT parameters (likely, given per-agent review counts), kill — revisit once intertrust's review-count-per-agent crosses a fittable threshold (rule of thumb ~50 graded items/agent).

**Adversarial reward auditing as a pre-merge gate for interlab campaign outputs**

- Component: interlab, Ockham
- Evidence strength: weak
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Adversarial Reward Auditing for Active Detection and Mitigation of Reward Hacking (arXiv:2602.01750, Feb 2026)
- Rationale: interlab autoresearch campaigns optimize proxy metrics (tok/s, cache-hit-rate, kernel throughput) that are exactly the shape reward-hacking research warns about: a mutation could game the benchmark harness (e.g. exploit a measurement quirk) rather than genuinely improving the system. Ockham's anomaly evaluator already gates dispatch; adding an adversarial-audit pass specifically for 'does this mutation's win generalize outside the benchmark harness's exact measurement conditions' would close a real gap.
- Kill rule: Phase-1: pick 5 closed interlab campaigns with 'winning' mutations already shipped; re-run their benchmark harness with 2-3 perturbed measurement conditions (different batch size, different input distribution). If none of the 5 winners show >10% metric regression under perturbation, harness-gaming isn't occurring in practice — kill the audit-gate proposal.

**Capability-fenced orchestration audit: does Clavain's tool allow/deny actually bound blast radius empirically**

- Component: Clavain, intercore
- Evidence strength: weak
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Capability-Fenced Orchestration of LLM Multi-Agent Systems: An Empirical Evaluation of Reliability, Safety, and Cost Trade-offs (2026, AMRJ)
- Rationale: Agency specs already define per-phase tool allow/deny lists (per the fc5 survey). Recent empirical work directly measures reliability/safety/cost tradeoffs of 'capability-fenced' orchestration vs unfenced — Sylveste could replicate this measurement on its own architecture rather than assuming the fencing helps, since the fc5 survey notes agency specs exist but nothing validates their safety payoff empirically.
- Kill rule: Phase-1: for 10 recent sprint runs with agency-spec tool fencing active, compare incident/rollback rate against 10 comparable runs from before fencing existed (or with fencing disabled via a flag, if available). If incident rate is statistically indistinguishable, fencing's safety value (as opposed to its cost/routing value, which is separately justified) is unproven at current scale — don't invest further in expanding fence granularity.

**Covert-channel / steganographic collusion audit for interlock inter-agent messaging**

- Component: interlock (negotiation protocol, broadcast_message, send_message)
- Evidence strength: strong
- Effort: spike-days
- Novelty: adapt
- Frontier basis: "Tool Use Enables Undetectable Steganography in Multi-Agent LLM Systems" (arXiv:2606.28425, Jun 2026); "Decision-Theoretic Steganography in LLM Monitoring" / NEST framework (2602.23163); "An Application-Layer Multi-Modal Covert-Channel Reference Monitor for LLM Agent Egress" (2605.20734, May 2026); "Secret Collusion among AI Agents" survey; "Voluntary Collusion with Secret Tools in Competing LLM Agents" (2605.27593)
- Rationale: Sylveste's fleet of concurrently-running agents (Clavain campaigns, flux-drive review panels, interlab mutation runners) routinely exchange free-text messages through interlock with no adversarial assumption. 2026 work shows tool-using LLM agents can build undetectable natural-language stegosystems and that once two agents share a tool-use channel, the barrier to covert coordination is no longer capability but key/scheme convergence — which cooperating same-vendor agents (e.g. two Sonnet instances) satisfy trivially by default. This is a distinct threat model from the already-listed 'formal trace verification of interlock's negotiation protocol' (which checks the *declared* protocol is followed) and from the game-theoretic mechanism-design item (which checks incentive-compatibility of *visible* urgency signals) — neither asks whether compliant, protocol-valid messages can carry an undetected side-channel that lets two agents coordinate around a review gate, a reservation conflict, or a release negotiation in ways the orchestrator can't see. Concretely testable: plant a colluding-agent pair in a flux-drive review or interlab campaign, give them a shared tool-use side-channel, and measure whether existing interlock monitoring/logging detects the coordination.
- Kill rule: If a red-team pair of agents given an explicit shared side-channel cannot beat random-baseline detectability under interlock's existing message logging within a fixed budget of rounds, the threat is not live at Sylveste's current message volume/adversary sophistication — close as 'insufficient signal, revisit if fleet size or adversarial-agent exposure grows.'

**Emergent-collusion / incentive-coupling audit for interlab's competitive mutation-scoring fitness function**

- Component: interlab (campaign fitness/mutation scoring), interspect (routing incentives)
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: "Governing LLM Collusion in Multi-Agent Cournot Markets via Public Governance Graphs" (arXiv:2601.11369); "Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems" (2602.15198, DCOP-based formal collusion definitions applicable to task-assignment-like fitness scoring); "Emergent Collusion in LLM-Powered Multi-Agent Markets" survey (OpenReview Hvkx9x2Qv5)
- Rationale: interlab scores mutations competitively and interspect's calibration loop shapes which agents get routed future work — both are reward-maximizing feedback loops running over repeated interactions among agents that may end up implicitly 'aware' of each other's scoring history (via shared logs, shared context, or correlated training). 2026 research on Cournot-market LLM agents shows implicit collusion (covert division of the scoring/routing space) emerges from reward-maximizing incentives alone, without any explicit coordination instruction, and that prompt-only prohibitions don't reliably suppress it. This differs from the listed 'process reward model for interlab mutation scoring' (which is about reward *design* quality) and 'consensus-trap breaker for interspect' (which is about a specific known failure bead) — this item asks whether the repeated-game structure itself creates incentives for agents/mutations to converge on mutually-protective low-effort equilibria that both raise measured fitness/calibration scores without raising real quality. Strong external evidence the phenomenon exists in analogous economic settings; moderate confidence it transfers to interlab's specific scoring mechanics without a scoping spike.
- Kill rule: If a scoping spike applying the Colosseum DCOP-style collusion metric to 2-4 weeks of existing interlab campaign logs finds no anomalous score-clustering or mutual-protection pattern above a null baseline (shuffled-pairing control), close — the repeated-game surface is too thin at current campaign cadence for collusion to be worth guarding against yet.

**Preference-coupling audit: does interspect's evaluator-driven routing propagate evaluator bias into agent strategy distributions**

- Component: interspect (calibrate, delegation routing), flux-drive reviewer panel
- Evidence strength: strong
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: "Calibrating the Evaluator: Does Probability Calibration Mitigate Preference Coupling in LLM Agent Feedback Loops?" (arXiv:2606.31371, Jun 2026)
- Rationale: interspect routes future work based on evaluator-scored outcomes — structurally identical to the RL-feedback-loop setup the 'Calibrating the Evaluator' paper studies, where systematic evaluator biases don't just mis-score a single output but propagate into the *learned strategy distribution* of the agent being evaluated over repeated rounds (preference coupling), and where probability-calibrating the evaluator's judgments is shown to measurably reduce this. This is distinct from the listed 'LLM-judge kappa-deflation audit for flux-drive reviewer panel' (single-round inter-rater agreement) and 'cross-agent evidence provenance for interspect: on-policy vs off-policy calibration' (data provenance, not the coupling dynamic) — this item asks the longitudinal question: after N rounds of interspect-driven routing, has the population of agents/prompts interspect favors drifted toward exploiting a specific evaluator bias rather than toward genuinely better task performance, and does applying the paper's calibrated-TTRL-style correction to interspect's evaluator scores measurably de-couple it.
- Kill rule: If a retrospective analysis of interspect's routing-decision history shows no measurable drift in agent/prompt population toward a specific known evaluator bias (e.g. length, hedging, self-praise patterns already tracked by the self-praise probe) over the available history window, close as 'no evidence of live coupling at current evaluation volume' rather than building the full calibration-correction pipeline speculatively.

**Sandbagging / selective-underperformance probe for agents under capability-fenced or auditable-review conditions**

- Component: Clavain capability-fenced orchestration audit, flux-drive review agents, two-strikes escalation
- Evidence strength: moderate
- Effort: research-program
- Novelty: adapt
- Frontier basis: AI Sandbagging research program (Taylor et al. 2025 detection-method study, van der Weij et al. 2024 foundational result); "AgentMisalignment" taxonomy (ICLR 2026 submission, arXiv:2506.04018); Anthropic's own "Introspection Adapters" alignment-science post (2026) showing introspection-based methods outperform behavioral detection
- Rationale: The existing list has a 'capability-fenced orchestration audit' item asking whether tool allow/deny bounds blast radius empirically — but that assumes agents are trying their best within the fence. 2026 sandbagging research shows models can be induced (or may spontaneously learn) to selectively underperform specifically on evaluations that would trigger tighter capability fencing or escalation, while performing normally elsewhere, and that ten standard detection methods failed to reliably catch this in controlled studies. Given Sylveste's two-strikes escalation ladder explicitly changes an agent's tier/permissions based on measured failure, there's a direct incentive gradient (real or emergent) for an agent to underperform just enough to stay under escalation thresholds, or conversely overperform on visible review-agent-scored tasks while underperforming on unreviewed ones — a threat model the current scan's reliability items don't probe for because they assume honest-but-fallible agents rather than strategically self-limiting ones.
- Kill rule: If a controlled probe — comparing agent performance on tasks known vs. not known to feed the two-strikes escalation counter, holding task difficulty constant — shows no statistically significant performance gap, close as 'no evidence of strategic underperformance at current stakes'; this is a research-program-sized bet and should not proceed past the initial probe without a positive signal.

#### Net-New Direction (6)

**Process reward model for interlab mutation scoring (replace/augment outcome-only fitness)**

- Component: interlab
- Evidence strength: weak
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: AgentPRM: Process Reward Models for LLM Agents via Step-Wise Promise and Progress (ACM Web Conf 2026); RLAnything step-wise PRM signal work (2026) — both domain is math/tool-use reasoning, not systems-mutation search, hence adapt not adopt
- Rationale: interlab's autoresearch campaigns (reservoir routing, KV compression, Metal shaders, etc.) currently score mutations by end-state benchmark metrics only (outcome reward). Sylveste is unusually positioned to try step-wise process rewards because campaign YAML already captures intermediate mutation lineage (interlab mutation_record) — the same trajectory-shape that PRM research operates on, but applied to *systems-engineering mutation search* rather than math/code reasoning, which is an under-explored PRM application domain.
- Kill rule: Phase-1: on one closed interlab campaign with known-good final mutations (e.g. reservoir routing dp1/4b7), retroactively score intermediate mutation steps with a cheap heuristic PRM proxy (does this mutation's diff correlate with metric-improving direction). If process-reward ranking of intermediate mutations doesn't predict final-mutation quality better than random within that campaign's data, outcome-only scoring is sufficient — kill before building a live PRM training loop.

**Context-rot-aware session budgeting for long campaign/sprint runs**

- Component: intercore, Clavain, interphase
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: genuinely-novel
- Frontier basis: METR long-horizon task-length scaling trend (task-duration doubling ~7 months); context-rot / tool-call-coherence findings (Zylos Research 2026, 'context drift accounts for ~2/3 of long-running agent failures')
- Rationale: Sylveste's own OODARC runtime + campaign orchestration (Skaffen) already tracks per-run turn counts and tool-call counts in intercore state. External research shows coherence degrades after ~25-30 tool calls even in 200K-token windows, and goal/context drift is the majority driver of long-horizon failure. Sylveste could instrument whether its own multi-phase campaigns (which routinely exceed 30 tool calls per agent) show measurable quality decay by phase position — data nobody else has because nobody else has this telemetry + this orchestration substrate together.
- Kill rule: Phase-1: pull 15-20 completed campaign runs from intercore, plot defect/rework rate against tool-call-position-within-run. If there's no monotonic degradation trend (flat or noisy), Sylveste's phase-boundary context resets (sprint→campaign phase handoffs) are already effectively mitigating context rot — kill the budgeting feature, the architecture already solves it structurally.

**Skaffen OODARC as a formally-specifiable agent-behavior contract**

- Component: Skaffen, intercore
- Evidence strength: weak
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: Agent Behavioral Contracts: Formal Specification and Runtime Enforcement (arXiv:2602.22302, Feb 2026); AgentSpec (ICSE 2026)
- Rationale: Skaffen's Go OODARC runtime already enforces phase ordering as code (not prompt convention) — this is closer to a real state machine than most agent frameworks' orchestration layers, which are markdown/prompt-encoded. That makes it a much better candidate for mechanically-checkable behavioral contracts than typical LLM-agent systems, because the phase-transition logic is genuinely typed Go rather than LLM-interpreted instructions.
- Kill rule: Phase-1: pick Skaffen's phase-transition state machine, write it as a small formal spec (even a hand-rolled invariant checker, not necessarily TLA+/Dafny), and run it against 6 months of historical OODARC run logs from intercore. If zero invariant violations are found in real runs, the phases were already enforced correctly by the Go type system alone — kill the added formal-verification layer as redundant.

**Cross-agent evidence provenance for interspect: on-policy vs off-policy calibration**

- Component: interspect, interlab
- Evidence strength: speculative
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: On-policy reward-model training reduces adversarial mismatch exploitation (general 2026 RLHF/RLVR literature theme, e.g. gradient-regularization and on-policy coupling papers, arXiv:2602.18037)
- Rationale: interspect calibrates routing from agent-produced evidence (per MEMORY.md capture routing and the ioe7 loop). Reward-model literature increasingly stresses that training reward signal on on-policy trajectories (matching the current policy's distribution) avoids the mismatch that off-policy reward models get exploited through. interspect's evidence store likely mixes evidence generated under old routing decisions (stale policy) with current-policy behavior — nobody has checked whether stale-policy evidence is silently degrading calibration accuracy.
- Kill rule: Phase-1: tag interspect evidence rows by the routing-policy version active when they were generated (available if routing_decisions timestamps + policy-version history exist); compare hit-rate prediction accuracy for evidence generated under the current vs a prior policy. If accuracy doesn't differ by policy-recency, staleness isn't a real effect at current evidence volume — kill, revisit only if evidence volume or policy-churn rate increases substantially.

**Agent negotiation as a formal game-theoretic mechanism-design problem for interlock urgency levels**

- Component: interlock
- Evidence strength: speculative
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: internal + general automated-negotiation/mechanism-design literature (game-theoretic LLM negotiation frameworks, 2026) — no single paper maps directly, treat as adapt-from-field not adopt-single-result
- Rationale: interlock's negotiate_release uses a fixed urgency vocabulary (normal/urgent) with fixed timeouts (5/10 min) — a mechanism designed by intuition, not by analyzing incentive-compatibility. If agents can freely declare 'urgent' with no cost, rational (or just poorly-calibrated) agents would over-declare urgency, degrading the signal — a classic cheap-talk mechanism-design failure. Sylveste has the negotiation transcripts to check whether this is already happening.
- Kill rule: Phase-1: pull interlock's negotiation message history, compute the ratio of 'urgent' to 'normal' declarations and whether urgent declarations correlate with any observable actual-urgency proxy (e.g., time-to-original-deadline, blocking-status of the requester). If urgent/normal ratio is low and stable (no inflation trend), the cheap-talk problem isn't manifesting — kill, the current fixed-vocabulary design is fine.

**Contrarian null-hypothesis test: does Sylveste's multi-agent orchestration beat single-strong-agent on its own task distribution**

- Component: Clavain campaign/sprint dispatch, interflux flux-drive, Fable-tier routing doctrine
- Evidence strength: moderate
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: "Multi-Agent Orchestration Economics When Single Agents Win" (Iterathon 2026 industry analysis); AdaptOrch (arXiv:2602.16873, Pareto-dominant task-adaptive routing showing convergence-era model performance narrows the multi-agent advantage); "In-Context Prompting Obsoletes Agent Orchestration for Procedural Tasks" (arXiv:2604.27891)
- Rationale: Every item in the existing scan assumes multi-agent orchestration is the right frame and studies how to make it more reliable/verifiable/well-calibrated. 2026 industry data (327% YoY multi-agent adoption per Databricks, but documented cases of ~2x cost and +4.8s latency per query from coordination overhead vs. single strong agent) plus the 'test null hypothesis first' doctrine already codified in this project's own memory argue for measuring, on Sylveste's actual task distribution, the task-class boundary where campaign/flux-drive multi-agent dispatch beats one Fable-tier agent working alone with good tools. This is the contrarian bet the existing list doesn't ask: not 'how do we make multi-agent more reliable' but 'for which of our own task classes is multi-agent orchestration net-negative once coordination tax is priced in, and should the two-strikes/model-routing doctrine include an explicit single-agent-first default for those classes.'
- Kill rule: Pre-register a task-class taxonomy (from existing bead/campaign history) and a coordination-tax metric (wall-clock + token-cost vs. best single-agent baseline) before running; if orchestration wins or ties on >80% of sampled task classes, the null hypothesis (single-agent is competitive) is rejected and the project closes with a documented boundary rather than continuing to hunt for a negative result.

#### Latent Backlog — Formalize (5)

**Consensus-trap breaker for interspect's calibration loop (formalize existing bead)**

- Component: interspect, interlab
- Evidence strength: strong
- Effort: spike-days
- Novelty: adapt
- Frontier basis: CoVerRL: Breaking the Consensus Trap in Label-Free Reasoning via Generator-Verifier Co-Evolution (arXiv:2603.17775, ACL 2026) — already cited in the bead itself
- Rationale: sylveste-ioe7 wired interlab mutation→interspect adaptation; Sylveste-4b5.1 already flags that nothing watches verifier-vs-generator agreement trending up while defect-escape-rate stays flat — the textbook CoVerRL consensus trap, self-diagnosed. It's filed (P1, open) but blocked on sylveste-9lp.37 (frozen external holdout). This is the single most on-the-nose 'internal + frontier-confirmed' research item in the whole layer.
- Kill rule: Already pre-registered in the bead: HARD-BLOCKED on sylveste-9lp.37 landing, or the agreement-rate trend is uninterpretable without it. Escalate priority of 9lp.37 rather than reinventing this — the kill rule and acceptance criteria are already written.

**Stemma provenance-phylogenetics for cross-agent hallucination genealogy**

- Component: interspect, interflux, intercore
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: genuinely-novel
- Frontier basis: internal (rsj.10 lineage) + broadly related to hallucination-cascade findings in MAST failure taxonomy work
- Rationale: sylveste-rsj.10 (provenance vectors for shared hallucinations, 'hyparchetype' tracing) and rsj.10.3/.10.4 have design docs but the tracing capability itself appears unshipped/unformalized as a research question: does Sylveste's multi-agent fan-out (flux-drive, campaign phases) actually propagate correlated errors across agents that share a common upstream claim? This is answerable with existing dispatch telemetry (intercore run records + flux-drive finding provenance) and nobody else has this data shape.
- Kill rule: Phase-1: on 20 recent flux-drive multi-agent reviews, hand-trace whether any finding repeated across ≥2 independent agents traces to a shared upstream artifact (same source doc, same prior agent's output) rather than independent verification. If <10% of 'converged' findings show shared-ancestry contamination, the hyparchetype-tracing investment isn't justified by actual incidence — park it, the rsj.12 hearsay-rule (cite-with-provenance) mitigation may already be sufficient.

**Ockham-Alwe governance flywheel closure as a graduated-autonomy research testbed**

- Component: Ockham, Alwe
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: Singapore IMDA agentic-AI Model AI Governance Framework (Jan 2026, 5-tier taxonomy); NIST CAISI AI Agent Standards Initiative (Feb 2026) — both converge on 'oversight proportional to impact, promote on demonstrated reliability' as the emerging external consensus
- Rationale: Ockham's M0-M4 authority ratchet + CONSTRAIN tiers is architecturally identical to the 5-tier graduated-autonomy frameworks now appearing in external governance guidance (start at Tier 1, promote only on demonstrated reliability, oversight proportional to impact). sylveste-nzhl.* (F1-F8) and sylveste-xefe (Alwe bridge) are filed but the promote/demote evidence thresholds themselves are undocumented as a research question — what evidence volume/quality actually justifies M2→M3 promotion, and is Sylveste's dispatch telemetry rich enough to answer it empirically rather than by fiat?
- Kill rule: Phase-1: once F1 (authority ratchet) and F5 (paired confirmation) ship, backtest the promote/demote thresholds against 4-6 weeks of retroactive dispatch data. If retroactive M-tier assignments would have blocked <2% of actually-fine dispatches and caught 0 actual incidents (because none occurred), the ratchet's thresholds are unfalsifiable at current volume — don't tune further until incident rate increases; re-test quarterly instead.

**Two-strikes escalation ladder as an online reliability-engineering experiment, not just a routing feature**

- Component: intercore, Clavain
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal (Sylveste-fc5 phased plan) — loosely related to classic escalating-bandit / abandonment-policy RL literature, no specific 2026 citation needed
- Rationale: Sylveste-fc5.2 (two-strikes escalation, sonnet→opus→fable) is scoped as a routing mechanism, but it is structurally a bandit/escalation-policy research question: what's the actual expected-cost-minimizing escalation threshold (2 strikes? 1? adaptive by task complexity?) given real fail-rate data intercore already logs via routing_decisions? Nobody has framed fc5.4's plan-pass-rate metric as an input to *tuning* the strike count itself.
- Kill rule: Phase-1: after fc5.4 lands and 20+ escalation events are logged, compute whether 2-strikes is cost-dominant vs a 1-strike or 3-strike policy using observed retry-success curves. If the sample is too small to distinguish policies (wide confidence intervals), keep the doctrine's fixed 2-strikes as-is rather than building adaptive tuning — the fixed rule is cheap and defensible; adaptive tuning only pays off with real separation in the data.

**Ockham F5 paired-confirmation as a mini formal-verification target before it ships**

- Component: Ockham, interspect
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal (nzhl.5, unshipped) + general formal-methods-for-agent-safety framing (VeriGuard, FormalJudge, 2026)
- Rationale: sylveste-nzhl.5 requires Ockham's anomaly evaluator AND interspect's evidence to independently confirm before CONSTRAIN fires — a two-detector agreement gate that is exactly the kind of small, high-consequence state machine (false-negative = ungoverned runaway, false-positive = unwarranted freeze) worth model-checking before it's live, not after an incident.
- Kill rule: Pre-registered as part of implementation, not a separate research track: before nzhl.5 ships, write out the confirmation-gate truth table (Ockham signal x interspect signal x time-window alignment) and check for any combination that produces neither CONSTRAIN nor a logged abstain. If the truth table is exhaustively coverable by 3-4 unit tests (likely, given it's a 2-signal AND gate), skip formal tooling entirely — this is a kill-rule-as-scoping-check, not a multi-week bet.

### Layer: Local Models / Inference (19 possibilities)

#### External Frontier — Adopt (10)

**Adopt FlashMoE-style ML-based expert cache replacement (recency+frequency hybrid) for flash-moe SSD-streamed experts**

- Component: interfer
- Evidence strength: strong
- Effort: spike-days
- Novelty: adapt
- Frontier basis: arXiv:2601.17063 'FlashMoE: Reducing SSD I/O Bottlenecks via ML-Based Cache Replacement for Mixture-of-Experts Inference on Edge Devices' (submitted 2026-01-22) — reports up to 51% cache-hit-rate improvement over LRU/LFU and up to 2.6x speedup on a user-grade desktop platform.
- Rationale: flash-moe already streams experts from SSD for the 397B-class MoE tier (Kimi/GLM-5/DeepSeek checkpoints on disk) using --malloc-cache with no learned eviction policy — exactly the gap this paper targets. Directly upgrades the already-open Sylveste-i3h Belady-cache spike from 'invent from scratch' to 'reproduce a published lightweight ML policy and compare against Sylveste's own oracle/LRU numbers.'
- Kill rule: Sylveste-i3h's own Phase-1 already has a kill rule (oracle beats LRU by <15% hit rate -> no headroom, close as traces-only). Add a second gate specific to this paper: if the published recency+frequency hybrid doesn't beat current no-policy/LRU by >15pp hit rate on Sylveste's own agent-prompt traces within one day of reimplementation, skip building a learned policy and keep the simpler heuristic.

**Re-run the MLX-concurrent-inference premise test against the PagedAttention/continuous-batching work landing in the MLX ecosystem in 2026**

- Component: interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: ml-explore/mlx GitHub issues #2228, #2955, #3203 (PagedAttention/Metal kernel proposals) and mlx-lm Discussion #614 (continuous batching), active through H1 2026; vllm-project/vllm-metal issue #148 tracking paged KV + chunked prefill for Metal. As of the discussion threads, mlx_lm's KVCache still reports fake memory capacity to vLLM's block scheduler — real continuous batching is not yet landed, only proposed/prototyped.
- Rationale: The open campaign sylveste-4wl and interfer's custom priority-queue scheduler are both built on 'MLX has no concurrent inference' (ml-explore/mlx#3078). That premise is now actively being dismantled upstream. If it lands, interfer's custom scheduler may be maintaining a redundant abstraction — worth knowing before 4wl burns further experiments on the old premise.
- Kill rule: This is already the exact Phase-1 experiment specified in docs/research/2026-07-05-ecosystem-research-agenda.md bet #4 (and gates sylveste-4wl) — not a new bet, just newly evidenced. Kill rule as already registered there: if upstream batching gives <1.3x aggregate throughput or violates the P99 <= 2x-single-request gate, keep the custom queue and let 4wl proceed as scoped.

**Confirm MTP head presence and measure self-speculative acceptance rate on Sylveste's actual downloaded checkpoints**

- Component: interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: Multiple 2026 papers/announcements confirm MTP heads now ship in-checkpoint across major open-weight MoE families (Nemotron-3 Super arXiv:2604.12374, Gemma 4 MTP per Google's 2026 release notes, MiniMax-M2 series arXiv:2605.26494); house rule 'read tensor shapes before papers' applies directly — safe_open the local checkpoints to confirm before benchmarking.
- Rationale: By mid-2026 MTP heads are shipped natively in DeepSeek V3.x/V4, GLM-5.1, Qwen3-Next, and other checkpoints in the same weight class Sylveste has already downloaded for the 397B tier. Native MTP eliminates the separate-draft-model tax that killed the earlier speculative-decoding spike (yfot, deferred) — this is a materially different technique (no draft model, no dual-model memory budget) not covered by that moot spike.
- Kill rule: Already registered as bet #10 in docs/research/2026-07-05-ecosystem-research-agenda.md: if MTP heads are absent from all workhorse checkpoints on disk, or acceptance rate is <60% on agent-shaped prompts for one model, drop self-speculation for this fleet and revisit at next model generation.

**Adopt calibrated-cascade routing theory (UCCI-style isotonic confidence mapping) for the local-vs-frontier routing decision in interspect/interfer**

- Component: interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: arXiv:2605.18796 'UCCI: Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing' (2026) — maps token-level margin uncertainty to per-query error probability via isotonic regression, selects escalation threshold by constrained cost minimization instead of hand-tuned thresholds.
- Rationale: Sylveste's local-vs-cloud routing today uses static tiers and uncalibrated confidence thresholds (0.8/0.6 mentioned in the 2026-03-27 brainstorm) — exactly the failure mode UCCI addresses: raw confidence scores are miscalibrated and don't transfer across workloads, so thresholds get hand-retuned per deployment. Sylveste has the one thing academic cascade papers rarely have: a live interspect evidence stream that could supply the calibration data for free.
- Kill rule: This is explicitly the flagship 'closed-loop model selection' cross-component idea already named in the 2026-07-05 research agenda, gated on the holdout register (bet 1) and judge-reliability harness (bet 7) landing first — without those, a calibration model trained on interspect evidence would calibrate against judge noise, not ground truth. Kill rule: if the holdout-register bet's own kill condition fires (evidence too sparse, <50 events per scored agent), there isn't enough labeled data yet to fit isotonic calibration either — park until volume improves.

**Latent-space KV cache compaction (Attention Matching / TriAttention-class techniques) as a follow-on to the KV-quant headroom spike**

- Component: interfer
- Evidence strength: weak
- Effort: research-program
- Novelty: adopt-known
- Frontier basis: MarkTechPost survey (2026-04-29) 'Top 10 KV Cache Compression Techniques' citing Attention Matching (~50x latent-space compaction) and TriAttention (10.7x memory reduction on AIME25 at matched accuracy, reasoning-aware compression); also DepthWeave-KV arXiv:2607.06523 and OSCAR arXiv:2605.17757 (2-bit KV quantization via spectral rotation) as concrete 2026 techniques closer to production-ready.
- Rationale: Sylveste's flashmoe-cache-sweep work established a Pareto frontier for RAM-vs-hit-rate on expert weights, and kv_bits=8 was flagged as a 'free lunch.' 2026's frontier has moved past simple quantization toward structural compaction (~50x claimed) — worth knowing about even though it's explicitly out of scope for near-term work.
- Kill rule: Already explicitly deliberately-dropped in the 2026-07-05 research agenda: 'the KV-quant headroom spike answers the near-term memory question at a tenth the cost. Monitor externally, adopt if it productionizes.' Restate the kill rule concretely: don't open a bead until a reference implementation exists for an MLX-compatible or portable backend — pure monitoring until then.

**OSCAR-style 2-bit KV cache quantization via offline spectral rotation, tested against interfer's existing kv_bits=8 baseline**

- Component: interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: arXiv:2605.17757 'OSCAR: Offline Spectral Covariance-Aware Rotation for 2-bit KV Cache Quantization' (2026) and arXiv:2606.24033 'RoPE-Aware Bit Allocation for KV-Cache Quantization' — both post-date the 2026-03-29 flashmoe-cache-sweep work that established the kv_bits=8 baseline.
- Rationale: interfer already runs at kv_bits=8 as a documented free lunch. 2-bit KV quantization via calibrated rotation is a concrete, smaller-effort technique (not the research-program-scale latent compaction above) that could extend the context-length/cache-budget headroom for the 397B SSD-streamed tier specifically, where cache budget directly trades against expert-cache residency.
- Kill rule: Phase-1: apply OSCAR's rotation offline to one workhorse model's KV projections, measure quality delta (task pass-rate, not perplexity) at 2-bit vs current 8-bit on a held-out agent-prompt set. If quality delta exceeds interspect's existing quality-regression threshold (5%, per the 2026-03-27 shadow-rollout doctrine) at the RAM savings achieved, don't ship — the marginal RAM this frees is only valuable if it directly extends expert-cache residency, so also gate on whether freed RAM measurably improves flash-moe hit rate.

**CoX-MoE-style AMX-enabled CPU-GPU co-execution for coalesced expert dispatch on Apple silicon's unified memory**

- Component: interfer
- Evidence strength: speculative
- Effort: spike-days
- Novelty: adapt
- Frontier basis: arXiv:2605.17889 'CoX-MoE: Coalesced Expert Execution for High-Throughput MoE Inference with AMX-Enabled CPU-GPU Co-Execution' (2026).
- Rationale: Apple silicon's unified memory architecture is structurally similar to the CPU-GPU co-execution regime this paper targets (no PCIe transfer cost for CPU-vs-GPU expert dispatch), even though the paper's AMX target is x86-specific. Worth a literature-adaptation pass to see whether the coalesced-execution *scheduling idea* (batch experts by co-activation pattern rather than dispatch one-by-one) transfers to Metal, independent of the AMX instruction set specifics.
- Kill rule: This requires a scoping read first, not a build: does the coalescing scheduling logic depend on AMX-specific instructions, or is it a generic batching heuristic applicable via Metal compute shaders? If the win is fundamentally tied to x86 AMX and doesn't decompose into a portable scheduling policy, drop without prototyping.

**Dynamic per-expert mixed-precision quantization (quantize hot experts higher, cold experts lower) for the SSD-streamed 397B tier**

- Component: interfer
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: arXiv:2511.15015 'Dynamic Expert Quantization for Scalable Mixture-of-Experts Inference' (late 2025/2026) establishes the general technique; Sylveste's specific angle — using the *same* activation trace instrumentation for both cache and quant policy — is internal.
- Rationale: Sylveste's flash-moe already tracks per-expert activation frequency (needed for the Belady-cache spike). The same trace data that feeds cache-policy decisions could feed a quantization-policy decision: experts that are activated often and stay resident deserve higher bit-width (cache budget doesn't limit them); experts that are rarely activated and always streamed cold from SSD cost more in I/O than precision, so lower bit-width there saves both disk footprint and read bandwidth with less quality risk (they contribute less to output on average).
- Kill rule: Sequenced strictly behind i3h (activation traces must exist). Phase-1: using i3h's traces, simulate (don't build) mixed-precision assignment offline and estimate disk-footprint savings and predicted quality delta via a proxy metric. If simulated disk savings are <15% at iso-quality (the same threshold class used elsewhere in this layer), the added packaging/dispatch complexity of per-expert precision isn't worth it — stop before implementation.

**Gemma-4-style 2-bit QAT + KV-cache-sharing architecture as a reference design for future Sylveste on-device specialist checkpoints**

- Component: interfer
- Evidence strength: weak
- Effort: research-program
- Novelty: adopt-known
- Frontier basis: Apple Intelligence Foundation Models 2026 update and Google's Gemma 4 2026 release notes (via Ollama v0.30 integration writeup) — both describe KV-cache sharing + 2-bit quantization-aware training as the on-device recipe.
- Rationale: If Sylveste ever trains or fine-tunes its own small specialist checkpoints (rather than only consuming open-weight releases), Apple's on-device 3B model and Google's Gemma 4 both demonstrate a specific 2026 recipe (KV-cache sharing + 2-bit QAT, not post-hoc PTQ) worth having on file as a design reference, distinct from the retired microrouter LoRA epic which targeted a different problem (task-specific adapters, not base-model compression).
- Kill rule: Speculative and contingent — no current Sylveste project trains base checkpoints. Do not open a bead; this is a bookmark only. Revisit if/when a concrete need for a from-scratch small specialist checkpoint appears (e.g., microrouter-successor work resurfaces with base-model training in scope, not just adapters).

**Prompt-lookup / n-gram speculative decoding for Clavain's agentic tool-call loops (draft-model-free)**

- Component: interfer (inference server) + Clavain agent execution loop
- Evidence strength: strong
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Prompt-lookup/ngram decoding revival + draft-mtp→ngram-mod pipelining proposal, llama.cpp issue #23184 (2026); AdaPLD — Adaptive Retrieval and Reuse for Efficient Model-Free Speculative Decoding, arXiv 2606.05742 (June 2026); Cacheback: Speculative Decoding With Nothing But Cache, arXiv 2511.21699
- Rationale: Clavain's multi-agent sessions are dominated by highly repetitive structured output: tool-call JSON, file paths echoed back, bead IDs, diff hunks reapplied near-verbatim. Prompt-lookup decoding (search the existing context for n-gram matches instead of running a draft model) is specifically strong on exactly this repetitive-structure workload and needs zero extra VRAM/unified-memory for a draft model or MTP head. It's complementary to, not redundant with, the scan's existing MTP-acceptance-rate item: MTP speculates from the model's own learned distribution, prompt-lookup speculates from the literal session context, and llama.cpp's tracked feature request (ggml-org #23184) is explicitly about pipelining draft-mtp with ngram-mod as a cascade. Sylveste never measures acceptance rate on agentic/tool-call traffic specifically (only on generic checkpoints), so this is also a measurement gap.
- Kill rule: If measured acceptance rate on Sylveste's actual tool-call/diff-heavy agent transcripts is <0.5 (below net-speedup threshold at K=5), or if gains are subsumed by the MTP head once that's confirmed present — kill in favor of MTP-only.

#### Net-New Direction (5)

**Cross-agent KV/prefix cache reuse for Clavain's flux-drive fan-out pattern, informed by RadixAttention-style trie sharing**

- Component: interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: RadixAttention/SGLang (arXiv:2312.07104, productionized through 2026) establishes the trie-based prefix-sharing technique for generic multi-tenant serving; TokenDance arXiv:2604.03143 and PrefillShare arXiv:2602.12029 extend this specifically to multi-agent/multi-LLM collective KV sharing in 2026 — but none of these papers instrument a real agent-orchestration harness with dispatch telemetry as ground truth for what 'shared prefix' actually looks like in practice.
- Rationale: Clavain's 3-12 concurrent subagent dispatches (flux-drive, flux-review, sprint parallelization) share near-identical system prompts and lens preambles per fan-out. No public benchmark or paper studies this exact shape — real production agent-orchestration traffic against a locally-controlled inference stack with full trace visibility. Sylveste has both interstat dispatch telemetry (to build the workload trace) and interfer (to instrument the serving layer) — genuinely uniquely positioned versus a lab that has neither.
- Kill rule: Already framed as a cross-component idea in the 2026-07-05 research agenda, gated on the NA prefill-asymmetry spike (bet 5) pricing what prefill actually costs first. Kill rule: if the NA spike shows prefill is already <15% of total dispatch latency for typical flux-drive fan-out sizes, cache-reuse savings are capped low enough that a trie-based reimplementation isn't worth the engineering — park and revisit only if fan-out width grows materially.

**Does interrank's leaderboard-driven local-model selection actually correlate with interspect's measured task outcomes on Sylveste's own workloads?**

- Component: interrank, interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: internal — the 2026 construct-validity literature on benchmark reliability (arXiv:2602.15532, 'Quantifying construct validity in large language model evaluations') motivates the question externally (benchmarks and real-task performance are known to diverge), but the specific join (interrank recommendation vs interspect measured outcome, same model, same platform) is Sylveste-specific and not something an external benchmark study could run.
- Rationale: interrank recommends models from AgMoDB snapshot benchmark data (LiveCodeBench, GPQA, etc.) — external, generic benchmarks. interspect independently measures real task pass/fail on Sylveste's actual dispatch mix. Nobody has checked whether interrank's benchmark-driven recommendation actually agrees with what interspect observes for the same model on Sylveste's own workload. If they diverge, interrank is optimizing for the wrong signal for this platform's use case.
- Kill rule: Pull the set of models that have both an interrank leaderboard rank and >=20 interspect-scored dispatches. Compute rank correlation between interrank's benchmark rank and interspect's measured pass-rate rank. If correlation is high (Spearman >0.7), interrank's generic benchmarks are a good proxy for this platform and no local-calibration layer is needed — close as validated. If low, that's the actionable finding: build a platform-specific override on top of interrank rather than trusting AgMoDB ranks directly.

**Does DeepSeek V4 Flash's architecture advantage still hold once M5 Neural Accelerator + MTP + continuous-batching gains are priced in for the incumbent Qwen3.6 tier?**

- Component: interfer, interrank
- Evidence strength: moderate
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: internal — combines already-open beads (Sylveste-0gi, Sylveste-va4, sylveste-4wl, self-speculative MTP bet) into a single decision-relevant comparison interrank is positioned to compute once the inputs exist.
- Rationale: Sylveste-0gi (DeepSeek V4 Flash port) is explicitly sequenced behind bets 4/5/10 in the research agenda because its serving-substrate economics depend on their outcomes. This makes that dependency an explicit research question rather than an implicit blocker: re-run interrank's quality-per-dollar-per-tok/s comparison between DeepSeek V4 Flash (91.6 LCB v6) and Qwen3.6-35B-A3B (80.4) *after* re-pricing prefill/decode/batching/MTP gains for the currently-served model, since a 30% throughput uplift on the incumbent narrows or erases the quality gap's practical value.
- Kill rule: Cannot run until bets 4, 5, and 10 (already open/registered) report their numbers — this is a synthesis spike, not new measurement. Kill rule: if after re-pricing, Qwen3.6-35B-A3B's effective quality-per-token-per-second on Sylveste's own interspect-tracked task mix comes within 10% of DeepSeek V4 Flash's, close Sylveste-0gi as not-worth-the-port; the SSD/RAM budget the port would need is better spent on the Belady-cache work instead.

**Joules-per-token / intelligence-per-watt measurement harness for interfer, distinct from latency tuning**

- Component: interfer benchmarks + M5 Neural Accelerator tuning item
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Intelligence per Watt: Measuring Intelligence Efficiency of Local AI, arXiv 2511.07885; TokenPowerBench (AAAI 2026); Beyond the Joule energy-efficiency review, Joule journal (2026)
- Rationale: Every M5/Apple-silicon item in the current scan (prefill/decode asymmetry, KV quant, AMX co-execution) optimizes latency or throughput; none measures energy. Clavain runs long unattended background sessions — cron loops, overnight flux-drive fan-outs, campaign execution — where sustained power draw and thermal throttling matter as much as tokens/sec, and a config that wins on throughput can lose badly on joules/token or trigger thermal throttling that erases the throughput win over a multi-hour run. This is a pure methodology gap: the scan has no energy axis at all, and 'Intelligence per Watt' as a construct is directly aimed at exactly this hardware class (Apple M-series local accelerators).
- Kill rule: If a 2-hour sustained-load measurement on the M5 shows throttling/power delta between current-fastest and current-most-efficient config is under 5%, energy is not a live constraint — don't build a standing harness, just note the number.

**Workflow-atomic / session-affinity admission scheduling for concurrent Clavain agent sessions sharing one local inference server**

- Component: interfer serving layer + interlock coordination
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live, arXiv 2511.02230 (rev. 2026); SAGA: Workflow-Atomic Scheduling for AI Agent Inference on GPU Clusters, arXiv 2605.00528; SMetric: Session-centric Scheduling for Serving Agents, arXiv 2607.08565
- Rationale: The scan's existing 'cross-agent KV/prefix cache reuse' item addresses WHAT gets cached (trie-shared prefixes) but not WHO gets served WHEN. When flux-drive or campaign fan-out spins up several concurrent Claude/local-model sessions against one interfer instance on a single M5 box, naive per-request scheduling starves long-context stateful sessions behind short bursty ones and thrashes KV cache residency. Treating each agent workflow as an atomic schedulable unit (not each turn) and giving KV cache a TTL tied to agent liveness is a genuinely different lever than prefix sharing — it's an admission/fairness problem, not a cache-content problem, and Clavain is exactly the kind of multi-turn, multi-session, single-box workload these papers target.
- Kill rule: If interfer is never observed serving >2 concurrent agent sessions in practice (single-user local box, not a cluster), this is solving a problem Sylveste doesn't have — confirm concurrency profile from interstat dispatch logs before investing.

#### Latent Backlog — Formalize (4)

**Expert-activation profiles as a routing diagnostic feeding interrank's hardware-aware recommendations**

- Component: interrank, interfer
- Evidence strength: moderate
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: internal — docs/research/2026-07-05-ecosystem-research-agenda.md cross-component ideas section, 'Expert-activation coverage as routing diagnostic feeding interrank'
- Rationale: sylveste-fba8 ('Hardware-aware model recommendations in interrank') already exists as an open bead, and the 2026-07-05 research agenda names this exact join as a cross-component idea: flash-moe's expert-activation trace data (from the Belady-cache spike, i3h) tells interrank which prompt families under-utilize a given MoE, upgrading recommendations from spec-sheet heuristics to measured activation profiles. This formalizes an implied-but-unscoped dependency between two open beads.
- Kill rule: Explicitly sequenced behind Sylveste-i3h (expert-activation trace instrumentation must exist first). Once i3h produces traces: if activation profiles show <10% variance in expert-utilization across the prompt families interrank already routes for (i.e., MoE activation is roughly uniform regardless of task type), there's no signal here — close without building the interrank integration.

**M5 Neural Accelerator prefill/decode asymmetry — is interfer's current tuning pointed at the wrong bottleneck?**

- Component: interfer
- Evidence strength: strong
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: Multiple 2026 vendor/blog sources (uneven reliability — ThePlanetTools.ai, Skorppio, LLMcheck all claim 20-40% prefill speedup from M5 Neural Accelerators) plus arXiv:2604.18788 'Efficient Mixture-of-Experts LLM Inference with Apple Silicon NPUs' as the more credible primary source; none of these numbers have been reproduced on Sylveste's own workhorse models at agent-realistic context lengths.
- Rationale: Already an open bead (Sylveste-va4) and bet #5 in the 2026-07-05 research agenda. Restating here because it's the highest-leverage cheap premise-test in the layer: if the M5 Max's per-GPU-core Neural Accelerators genuinely give asymmetric prefill (35-40% faster per some 2026 vendor claims) vs decode speedup, every quant/batching/speculation decision interfer has made so far may be optimizing the wrong stage.
- Kill rule: Already registered: measure prefill vs decode tok/s separately on 2-3 workhorse models at agent-realistic contexts; if measured asymmetry deviates <20% from current tuning's implicit assumptions, no reallocation — close in one day.

**Contamination-resistant benchmark re-pin for interrank, informed by 2026 construct-validity findings**

- Component: interrank
- Evidence strength: strong
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: arXiv:2602.15532 'Quantifying construct validity in large language model evaluations' (2026); general 2026 commentary on benchmark harness variance and contamination (LiveCodeBench rolling-update mitigation as the closest thing to a fix).
- Rationale: Sylveste-4b5.19 ('Contamination-resistant benchmark re-pin, deferred, gated on harness consuming a routing decision') already exists in the backlog as a deferred child bead. The 2026 external literature strengthens the case: construct-validity audits now document that identical model weights swing 10-20 points across evaluation harnesses, and that annotation error rates exceed 50% on some popular static benchmarks — meaning interrank's AgMoDB snapshot data (sourced from exactly these leaderboards) inherits that noise.
- Kill rule: Already gated in beads: stays deferred until the harness actually consumes a routing decision (i.e., don't build benchmark-hygiene infrastructure for a signal nothing downstream uses yet). No change to that kill condition — this entry exists to attach the 2026 evidence, not to un-gate it prematurely.

**Reproducibility harness: pin and re-verify interfer/interrank's own cited benchmark numbers against the actual M5 unit they run on, not vendor-reported figures**

- Component: interfer benchmarks + interrank leaderboard ingestion
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: internal — methodology gap identified by cross-referencing the scan against Sylveste's own verification-discipline pattern (parallels 'test null hypothesis first' and 'verify handoff version claims' operating principles), not a single external paper
- Rationale: The scan has a contamination-resistance item for interrank's *external* benchmark inputs, but no item on whether Sylveste's own internal claims (tokens/sec, KV-bits=8 baseline, MTP acceptance rate) are being measured live on the actual downloaded checkpoints and actual hardware revision, versus copied from a paper's H100/M4 numbers. Given the user's own memory record flags exactly this failure mode generically ('verify handoff version claims first' — treat vendor/paper claims as hypotheses, not facts), and local-inference benchmark numbers are notoriously hardware- and quant-format-sensitive, this is a standing measurement-discipline gap specific to the inference layer that the contamination item doesn't cover.
- Kill rule: If interfer/benchmarks already runs its own live pytest-benchmark suite against locally downloaded checkpoints on every tuning change (check interlab-*.sh scripts before assuming this is missing) — if so, this is already covered, drop it.

### Layer: Knowledge / Cognition (20 possibilities)

#### External Frontier — Adopt (9)

**Adopt training-free structured-world-model priors (Pep) for Auraken's cold-start cognitive profile**

- Component: Auraken (sylveste-22oi.7 cognitive-profile epic, sylveste-feto working-profile cold-start)
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: Pep (Preference Elicitation with Priors): Cold-Start Personalization via Training-Free Priors from Structured World Models, arXiv 2602.15012 (Feb 2026)
- Rationale: sylveste-feto and sylveste-22oi.7.5 (epistemic engine) both need a cold-start prior before any observations exist, and Auraken's anti-dependency philosophy rules out CoPersona-style cross-user facet borrowing (already flagged in the 2026-07-05 agenda as invasive-feeling). Pep is a different mechanism: learn a structured correlation prior offline from complete profiles, then do training-free Bayesian inference online from a handful of answers to pick the next most-informative question — this is closer to Auraken's existing 'ask a clarifying question' pattern than collaborative filtering is, and doesn't require storing/borrowing other users' data.
- Kill rule: Phase-1: build the offline prior from the 291-lens/discipline/community_id metadata already in Auraken's DB (no new data collection), simulate the same 5 synthetic cold-start users used in the CoPersona test. If question-selection efficiency (lenses-correctly-inferred per question asked) doesn't beat the current generic-default flow by a clear margin, kill — the existing scale-classifier fast-path (from sylveste-5jn8) may already be a sufficient cold-start heuristic.

**Evaluate FSPO-style meta-learned reward modeling as an alternative to hand-tuned effectiveness_score**

- Component: Auraken (lens effectiveness_score, sylveste-2l1 calibration pipeline)
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: FSPO: Few-Shot Optimization of Synthetic Preferences Personalizes to Real Users, arXiv 2502.19312, extended April 2026 (fewshot-preference-optimization.github.io)
- Rationale: Auraken's bridge_score/effectiveness_score are hand-tuned scalars. FSPO reframes personalized reward modeling as in-context meta-learning from a handful of preference examples per user/context rather than a fixed formula — directly applicable once sylveste-4wq6's lens-choice training signal starts accumulating (user's question-choice becomes the few-shot preference set).
- Kill rule: Wait for sylveste-4wq6 trajectory data to accumulate >200 labeled lens-choice events, then compare FSPO in-context reward prediction against the current effectiveness_score formula on a held-out 20% split. If agreement is within noise of the current formula, kill — this is the same MemTier lesson (already in the 2026-07-05 agenda) applied one layer up: don't build a learned model if the heuristic isn't the binding constraint.

**Test whether GraphRAG's documented underperformance-vs-vanilla-RAG pattern applies to lattice before F6b ships**

- Component: lattice (interweave); flux-drive triage
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: When to Use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation, arXiv 2506.05690 (v3, 2026); GraphRAG-Bench
- Rationale: Multiple 2026 evaluations (GraphRAG-Bench, 'When to use Graphs in RAG') converge on a specific finding: graph retrieval helps on multi-hop/aggregation queries but frequently loses to vanilla hybrid search on single-fact lookups — exactly the query mix flux-drive triage likely has (mostly 'find the agent for X domain', occasionally 'what connects to Y'). This gives Sylveste-0ww (already-scoped null-test spike) a concrete taxonomy to bucket its 50 queries by (single-hop vs multi-hop) rather than scoring pass/fail in aggregate, which would otherwise wash out a real signal if lattice wins on 20% of queries and loses on 80%.
- Kill rule: This is a methodology refinement to Sylveste-0ww, not a separate spend — apply the query-type taxonomy when designing that spike's 50-query set. If query-type doesn't predict win/loss (i.e. lattice's advantage or disadvantage is uniform across single-hop and multi-hop), drop the taxonomy and just use Sylveste-0ww's aggregate result as-is.

**Adopt temporal fact-invalidation semantics for interknow's decay model, not just intermem's**

- Component: interknow; intermem
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: internal (memory-architecture-convergence brainstorm, docs/brainstorms/2026-03-07-memory-architecture-convergence.md, problem #3) — the fix pattern itself borrows from the same bi-temporal literature already cited for intermem in the 2026-07-05 agenda.
- Rationale: The 2026-07-05 agenda already flags temporal fact-invalidation (t_valid/t_invalid) for intermem, but interknow has a structurally similar but distinct decay model (10-reviews-without-confirmation archival, not time-based) that the agenda doesn't touch. interknow's own README already names the gap: 'counts reviews, not time — stale knowledge can persist forever if unvisited' (flagged directly in the memory-architecture-convergence brainstorm's problem #3 table). This is the same fix pattern, different component, currently un-scoped.
- Kill rule: Phase-1: audit how many interknow entries currently sitting near the 10-review archival threshold are actually stale-by-calendar-time (e.g. >180 days unvisited) vs recently-reviewed-but-just-under-threshold. If time-since-last-confirm and review-count-since-last-confirm are highly correlated in practice (reviews happen roughly steadily), the review-count proxy is already good enough — kill the time-based rework.

**External-frontier-adopt: apply the Metacognitive Probe's 5-dimensional decomposition specifically to Auraken's next_question generation, not just effectiveness_score**

- Component: Auraken; interlens
- Evidence strength: weak
- Effort: spike-days
- Novelty: adapt
- Frontier basis: The Metacognitive Probe: Five Behavioural Calibration Diagnostics for LLMs, arXiv 2605.09844 (2026)
- Rationale: The 2026-07-05 agenda already scopes the Metacognitive Probe against interspect/lens-effectiveness scoring generally. A narrower, more actionable variant: Auraken's per-turn output includes a next_question field whose implicit confidence (how leading vs. open the question is) is never separately measured from lens-selection confidence. The probe's 5 diagnostics could reveal whether the same Haiku call is conflating 'I'm confident this lens fits' with 'I'm confident this question will land' — two different failure modes with different UX consequences (wrong lens vs. right lens, bad question).
- Kill rule: Same kill rule as the agenda's broader version, scoped down: apply the probe retrospectively to 20 F6a-corpus lens_select outputs, decomposing lens-confidence vs question-confidence. If the two dimensions move together (>0.9 correlation), they're one signal wearing two names — kill, no separate question-quality metric is warranted.

**External-frontier-adopt: consider Compiled AI's execution-time/compile-time split as the missing cost model for deciding which lattice connector logic is LLM-necessary**

- Component: lattice (interweave)
- Evidence strength: weak
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation, arXiv 2604.05150 (Apr 2026)
- Rationale: Compiled AI reports 57x token reduction and 96% task completion by having the LLM generate deterministic executable code once (compile-time) rather than reasoning at every invocation (runtime). Lattice connectors currently likely re-invoke LLM judgment on every harvest for entity resolution / relationship typing even when the underlying source schema hasn't changed since the last run. This gives a concrete architecture pattern (not just a vague 'reduce LLM calls' aspiration) for the same problem the interleave-pattern possibility above identifies from a different angle — worth cross-checking both land on the same recommendation before building either.
- Kill rule: Fold into the same Phase-1 audit as the interleave-pattern possibility (measure fraction of connector LLM calls that are deterministic-extractable vs genuine-judgment). If that audit already kills the interleave-pattern version, this is automatically killed too — don't run two separate spikes measuring the same thing under different paper names.

**Audit whether Auraken's effectiveness_score is judge-contaminated: does the lens-selecting model also (directly or via correlated prompting) score its own selection's effectiveness?**

- Component: Auraken (effectiveness_score, lens_select)
- Evidence strength: strong
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: Quantifying and Mitigating Self-Preference Bias of LLM Judges (arxiv 2604.22891, 2026) — cross-family confirmation (Llama/Claude/GPT) of 10-25% self-preference inflation; 'Calibrating the Evaluator' (arxiv 2606.31371, June 2026) on preference-coupling in agent feedback loops
- Rationale: The persona-lens-ontology PRD assigns Auraken ownership of effectiveness_score but the current implementation (experiments/f1-age-spike/generate_fixture.py) stubs it with random.uniform — the real scoring path (same model selects lens AND scores post-hoc, vs a separate scorer) is undecided. If it's the same model family end-to-end, 2026 self-preference-bias work shows a reproducible 10-25% uniform inflation with 'nothing else you do will surface it' — meaning the entire lens-effectiveness leaderboard (and any FSPO-style reward-model replacement already in the scan) could be measuring judge self-agreement, not lens quality. This is upstream of the FSPO item already in the list: before replacing hand-tuned scoring with meta-learned reward modeling, first establish whether the CURRENT scoring is contaminated, since a meta-learned reward model trained on contaminated scores just launders the bias.
- Kill rule: If effectiveness_score is already computed by a scorer model/pipeline architecturally distinct from the lens-selector (different model, or non-LLM heuristic), or if a same-model design ships and cross-family judge scores land within noise (<5%) of the incumbent scores on a held-out set, close as non-issue and drop from backlog.

**Net-new: apply the high-dimensional embedding-concentration result to intersearch's shared-embedding-space proposal — does adding lattice+Auraken+interknow into one space accelerate contrast collapse rather than improve retrieval?**

- Component: intersearch, lattice, Auraken, interknow
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: High-Dimensional Concentration and Retrieval Instability in Embedding Spaces: Implications for Retrieval-Augmented Generation (arxiv 2606.28330, June 2026)
- Rationale: The existing scan item asks whether a shared embedding substrate 'changes retrieval quality' but frames it as an integration question. A June 2026 paper gives a specific, testable mechanism for why it could get WORSE, not better: as effective dimensionality and item count grow (three plugins' worth of heterogeneous content pooled into one space), cosine similarity contrast collapses and hubness increases, destabilizing nearest-neighbor retrieval — independent of embedding model quality. This reframes the existing item from an A/B integration test into a specific measurement: compute concentration/hubness diagnostics on the pooled space BEFORE running the retrieval-quality comparison, since if collapse is already present, the A/B result is confounded by geometry, not by information-sharing value.
- Kill rule: Compute distance-concentration and hubness metrics on the pooled embedding space; if metrics are within normal range for the chosen embedding model's known dimensionality (no anomalous hub concentration vs a single-plugin baseline), proceed with the existing A/B retrieval-quality plan unmodified — the geometric confound is absent.

**Net-new: test whether Auraken/interfluence exhibit the 'Assistant Axis' attractor-state dynamic documented for long multi-turn sessions — does sustained lens/persona wielding degrade the underlying model's baseline helpfulness/safety posture, independent of the intentional persona content?**

- Component: Auraken, interfluence
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: Attractor States Emerge in Multi-Turn LLM Conversations (arxiv 2606.30571, June 2026); Understanding Persona Drift in LLMs (Assistant Axis / PCA activation-direction method, 2026)
- Rationale: The existing scan has an identity-drift item (interlore auditing intername/interfluence) but frames drift as persona-consistency (does the character stay in-character). The 2026 Assistant-Axis literature describes a different, more concerning phenomenon: instruction-tuned models show measurable turn-by-turn drops (20-40% over 10-15 turns) in projection along the model's default helpful/harmless identity direction during sustained roleplay/persona sessions, correlating with emergent problematic behaviors — this is drift AWAY from the base assistant, not drift within the intended persona. Since Auraken wields personas for extended sessions and interfluence maintains voice profiles across long interactions, the safety-relevant question is whether extended lens/voice wielding erodes the underlying safety posture, not just whether the persona stays internally consistent. This is a distinct, higher-severity failure mode than the consistency-audit item already listed.
- Kill rule: Run a 15-turn sustained-persona session through Auraken/interfluence's actual model and measure refusal-rate and harmful-request-compliance on injected red-team probes at turns 1, 5, 10, 15. If compliance/refusal rates stay flat (no monotonic drift), the attractor-state effect doesn't manifest in Sylveste's usage pattern (likely shorter sessions or lower-intensity persona commitment than the therapy/philosophy domains studied) — close.

#### Net-New Direction (9)

**Net-new: use interspect's holdout-register methodology (once built) as the shared falsifiability harness for Auraken lens-effectiveness AND lattice triage-lift claims**

- Component: Auraken; lattice; interspect
- Evidence strength: moderate
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: internal — extends the platform's own #1 agenda item (holdout register, docs/research/2026-07-05-ecosystem-research-agenda.md) across layer boundaries; no external work found combining a single shared holdout harness across a persona/lens/routing calibration stack.
- Rationale: The 2026-07-05 agenda's #1 platform-wide bet is building a holdout register for interspect. Nobody has asked whether that same primitive — freeze N% of evidence as held-out, recompute claims on train-split-only — should be the mandatory scaffolding every calibration claim in this layer runs through, not just interspect's own routing overrides. Right now sylveste-2l1 (lens calibration), F6b (triage lift), and any future Auraken effectiveness work each risk inventing their own ad-hoc validation split. Sylveste is positioned to build ONE holdout harness and require every knowledge-cognition calibration bead to consume it, rather than 4 different bespoke validation designs with different rigor levels.
- Kill rule: After the interspect holdout register spike ships (top platform bet), spend one day checking whether its schema (evidence event, train/holdout flag, recompute function) generalizes to Auraken's lens-selection evidence table with only a rename, or needs a structurally different shape. If it needs >1 day of schema surgery to fit a second consumer, the 'shared harness' framing is premature abstraction — let each calibration bead build its own split and revisit after 3+ have shipped independently.

**Net-new: interleave's deterministic-skeleton/LLM-islands pattern applied backward as a knowledge-graph extraction discipline**

- Component: lattice (interweave); interleave; interscribe
- Evidence strength: weak
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal — interleave (deterministic-skeleton/LLM-islands, existing plugin) applied to a new domain (KG ingestion) it wasn't designed for; loosely parallels 'Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation' (arXiv 2604.05150, Apr 2026) which reports 57x token reduction by pushing repeatable logic out of the LLM path.
- Rationale: interleave's pattern (render deterministic sections from data, LLM fills only semantic gaps) is currently used for document *generation*. Lattice's connector-idempotency problem (flagged in the 2026-07-05 agenda) is structurally the same shape run in reverse: most of what a new connector harvests is deterministically extractable (frontmatter fields, IDs, timestamps) and only relationship inference/entity resolution ('is this the same Persona as an existing node') genuinely needs LLM judgment. No connector currently documents this split explicitly — Sylveste already has the pattern-naming vocabulary (interleave) sitting one repo over from the problem that needs it (lattice), unconnected.
- Kill rule: Audit one existing lattice connector's harvest run: what fraction of LLM calls are doing deterministic extraction (could be a regex/schema mapper) vs genuine judgment (entity resolution, relationship typing)? If deterministic-extractable calls are <20% of total LLM spend on that connector, the token/cost case is too thin to justify a refactor — park as a documentation note only, don't build tooling.

**Net-new: measure whether Auraken's stateless per-turn lens selection exhibits the same context-competition bottleneck continual-learning-via-memory papers describe for stateful agents**

- Component: Auraken; interlens
- Evidence strength: speculative
- Effort: spike-days
- Novelty: genuinely-novel
- Frontier basis: When Continual Learning Moves to Memory: A Study of Experience Reuse in LLM Agents, arXiv 2604.27003 (Apr 2026); Forget to Improve: On-Device LLM-Agent Continual Learning via Budget-Curated Memory, arXiv 2606.25115 (Jun 2026)
- Rationale: 2026 continual-learning-via-memory literature finds that once agents accumulate experience in external memory, old and new experiences compete during retrieval — the bottleneck moves from parameter updates to memory access, not accuracy. Auraken is deliberately memory-light (single JSON response per turn, no persistent profile in the shipped product per the companion-agent scoping doc) — which means it may already be architecturally immune to a failure mode the rest of the field is fighting. That's a testable, publishable-internally claim: does staying stateless avoid the retrieval-competition bottleneck entirely, or does the 291-lens index itself already exhibit an analogous form of it (older/more-general lenses crowding out newer/more-specific ones in the Haiku selector's attention)?
- Kill rule: Phase-1: on the existing 20-fixture parity corpus, check whether lens_select's top-3 agreement correlates with lens age/usage_count (a proxy for 'crowding'). If no correlation, the stateless architecture is confirmed clean on this specific failure mode — write it up as a one-paragraph internal finding and close, do not build competition-mitigation tooling for a problem that doesn't exist here.

**Net-new: audit intername/interfluence identity drift using interlore's own pattern-detection engine as the instrument**

- Component: intername; interfluence; interlore
- Evidence strength: weak
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal — interlore (existing plugin, docs/brainstorms/2026-03-21-interlore-brainstorm.md) applied to a corpus (interfluence voice profiles / intername theme usage) it wasn't originally scoped for.
- Rationale: The 2026-07-05 agenda proposes wiring interfluence/intername drift signals into lattice, gated on 'if profiles have drifted materially.' But Sylveste already has a purpose-built pattern-detector for exactly this class of question — interlore scans brainstorms/PRDs/flux-drive outputs for latent design-pattern drift and proposes PHILOSOPHY.md updates with evidence links. Nobody has pointed interlore's scan engine at voice-profile corpora or agent-naming-theme usage instead of philosophy docs. This is a build-nothing-new possibility: reuse interlore's existing evidence-linked pattern-proposal machinery on a different document set.
- Kill rule: Run interlore's scan skill against one active .interfluence/ profile directory as a one-off (no product change). If it surfaces zero evidence-linked drift proposals over the corpus's full history, either drift genuinely isn't happening (matches the 2026-07-05 agenda's own suspicion) or interlore's pattern vocabulary doesn't transfer to voice/identity data — either way, kill before building an integration.

**Net-new: does interscribe's CLAUDE.md/AGENTS.md boundary-audit heuristic generalize to a lattice schema-boundary linter (catalog vs source-of-truth violations)?**

- Component: interscribe; lattice (interweave)
- Evidence strength: weak
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal — interscribe's existing audit/refactor/consolidate architecture (interverse/interscribe/README.md) applied to lattice's catalog-boundary invariant instead of the CLAUDE.md/AGENTS.md boundary it currently checks.
- Rationale: interscribe already enforces one hard architectural boundary (config docs vs project docs) with an automated audit+refactor mode. Lattice has a structurally identical boundary problem stated as a 'load-bearing architectural commitment' in its own docs: catalog-of-catalogs, never owns entity data — but per the 2026-07-05 agenda, this is currently enforced only by per-connector tests, not a generalized linter. interscribe's audit-score + auto-refactor pattern (health score, violations list, automatic fix with git-diff review) is a ready template for exactly the connector-idempotency contract test the agenda flags as missing.
- Kill rule: This is downstream of the 2026-07-05 agenda's own kill rule for the connector-idempotency test suite: only pursue the interscribe-pattern reuse if that generalized contract test (run against the 3 existing connectors) surfaces real violations rather than passing trivially. If it passes trivially, there's nothing for a linter to catch — kill both together.

**Net-new: intersearch as the shared embedding substrate — measure whether a single shared embedding space (vs. per-plugin ad-hoc embeddings) changes lattice/Auraken/interknow retrieval quality**

- Component: intersearch; lattice; Auraken; interknow
- Evidence strength: speculative
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal — repo inspection (interverse/intersearch/README.md; qmd MCP server description) shows the substrate exists but is under-adopted by this layer's own components.
- Rationale: intersearch exists explicitly as shared embedding infrastructure but its README states only interject and interflux currently consume it as a dependency — lattice, Auraken's lens corpus, and interknow's qmd search each appear to run separate embedding pipelines (qmd has its own, Auraken presumably has its own for 291 lenses). If intersearch's embedding space were the single substrate all three retrieval surfaces queried against, cross-system queries ('find lenses AND knowledge entries related to X') become possible without a new index — this is a consolidation question nobody has priced out, sitting on top of the platform's existing 'unify retrieval, not storage' constraint.
- Kill rule: Phase-1: embed a 50-item sample of Auraken lenses and interknow entries with intersearch's model, compare nearest-neighbor quality (manual spot-check, 10 queries) against each system's current embedding approach. If retrieval quality is materially worse or the embedding models are already functionally equivalent (same underlying sentence-transformer), there's no consolidation upside — kill, the 'unify retrieval not storage' principle is already satisfied by having compatible-enough embeddings even if not literally shared.

**Net-new: does Auraken's 12-20s lens_select latency (sylveste-5jn8) correlate with lens-count-in-prompt in a way that predicts a scaling cliff as the 291-lens library grows toward the persona/lens ontology's projected 1200+ entities?**

- Component: Auraken; lattice (interweave); interlens
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: internal — combines sylveste-5jn8 (latency finding) with the persona-lens-ontology brainstorm's stated 1200→10K entity growth trajectory (docs/brainstorms/2026-04-21-persona-lens-ontology-brainstorm.md)
- Rationale: sylveste-5jn8 treats latency as a current UX bug to optimize. But the persona-lens-ontology brainstorm explicitly plans to grow the unified store from ~1200 entities toward 10K. If latency scales with serialized-lens-count in the prompt (one of sylveste-5jn8's own named contributing factors), the current fix (trim descriptions, cache the index string) is a linear patch on what may become a super-linear problem once lattice-backed retrieval replaces the flat 291-lens serialization with a much larger candidate pool. This is the forward-looking question sylveste-5jn8 doesn't ask: will today's fix still work at 10x the corpus size, or does the scale-filtered/distilled-selector path (already named as option 3/4 in the bead) become mandatory rather than optional at ontology scale?
- Kill rule: Phase-1: synthetically pad the lens index to 600 and 1200 entries (duplicate + relabel existing lenses for a load test only, discard after) and measure lens_select latency at each size. If latency scales sub-linearly (e.g. because Haiku's context handling amortizes), the current caching/trimming fix is sufficient at 10x scale — kill the scale-filtered-selector investment until the ontology actually ships enough real entities to re-test with genuine data.

**Net-new: does Auraken's cognitive profiling constitute stereotyping-as-personalization, and is there a measurement gap between 'lens matches this user' and 'lens matches this user's inferred demographic group'?**

- Component: Auraken (cognitive profile, lens_select)
- Evidence strength: moderate
- Effort: project-weeks
- Novelty: adapt
- Frontier basis: Reading Between the Prompts: How Stereotypes Shape LLM's Implicit Personalization (arxiv 2505.16467); Stereotype or Personalization? User Identity Biases Chatbot Recommendations (arxiv 2410.05613v2, CHI-adjacent); Personalizing Human-LLM Interactions through Mixed Profiling (CHI 2026, ACM 3772363.3799351)
- Rationale: Every existing scan item treats lens selection as a mechanics/performance problem (latency, cold-start, calibration, context-competition). None asks whether the profiling mechanism itself produces a representational harm: CHI 2026 and concurrent arxiv work show LLM personalization systems infer latent user attributes (not just stated preferences) and that stereotype-driven inference is empirically distinguishable from legitimate personalization but frequently conflated with it. Auraken's per-turn lens_select effectively does implicit attribute inference under a different name ('cognitive profile' instead of 'demographic profile'); the question is whether lens choices correlate with protected-adjacent user signals (writing style, vocabulary, topic choice proxying for background) in ways the effectiveness_score would reward without anyone measuring it as bias. This is a harm-surface gap, not a performance gap — genuinely missing from a scan that is otherwise all mechanics.
- Kill rule: Run a stratified audit: hold user-stated task/domain constant, vary only demographic-correlated surface features (writing style corpora), measure lens_select distribution shift. If distribution is stable (<10% divergence) across strata, no stereotyping signal exists and the concern is unfounded — close without building a mitigation layer.

**Net-new: cross-component — does interknow's temporal fact-invalidation model need a bitemporal (event-time vs ingest-time) representation, not just a decay/expiry timestamp, to resolve contradictions the way lattice's ontology already requires for entity versioning?**

- Component: interknow, lattice
- Evidence strength: moderate
- Effort: spike-days
- Novelty: adapt
- Frontier basis: TOKI: A Bitemporal Operator Algebra for Contradiction Resolution in LLM-Agent Persistent Memory (arxiv 2606.06240, June 2026)
- Rationale: The existing scan item says 'adopt temporal fact-invalidation semantics for interknow's decay model' but treats it as a single valid_from/valid_to timestamp problem (same shape as intermem's). A June 2026 paper on bitemporal operator algebra specifically targets LLM-agent persistent memory and distinguishes WHEN something was true in the world from WHEN the agent learned it — a distinction interknow's flat decay model collapses. This matters because lattice's persona-lens ontology already has valid_from/valid_to columns (seen directly in the f1-age-spike fixture) — if interknow adopts single-axis decay while lattice's schema is (or should be) bitemporal, the two systems will disagree on 'what do we currently believe' when a fact is corrected retroactively (e.g., a lens's effectiveness_score is revised for a past period). This is the schema-boundary-linter item's sibling: not catalog-vs-source-of-truth, but time-axis mismatch between two components that are supposed to share belief state.
- Kill rule: Enumerate interknow's actual contradiction cases from the last quarter of decay-triggered updates; if zero involve retroactive correction (all are simple supersession — new fact replaces old, no backdating), single-axis decay is sufficient and bitemporal modeling is premature complexity — close.

#### Latent Backlog — Formalize (2)

**Formalize interseed (idea-garden) as a source-of-truth feed into lattice's ontology, not a dead-end capture tool**

- Component: interseed; lattice (interweave)
- Evidence strength: weak
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: internal — repo inspection (docs/plans/2026-03-28-idea-garden-interseed.md; docs/reflections/2026-03-29-idea-garden-interseed-reflect.md; lattice CLAUDE.md 'catalog-of-catalogs' principle)
- Rationale: interseed shipped (docs/plans/2026-03-28-idea-garden-interseed.md, reflected 2026-03-29) as a standalone idea-capture plugin. Lattice's stated design is a catalog-of-catalogs that indexes entity metadata across subsystems — but there's no evidence interseed's captured ideas are indexed as Artifact/Process entities with lifecycle edges (e.g. idea → promoted-to → bead, idea → superseded-by → idea). Right now a captured idea in interseed and a beads epic tracking the same concept have no queryable link, even though lattice's whole thesis is that this kind of cross-system linkage is exactly what it's for.
- Kill rule: Phase-1: count how many interseed-captured ideas from the last 90 days later became a bead or brainstorm. If the promotion rate is near-zero (ideas mostly sit uncultivated, per the plugin's own 'garden' metaphor implying most ideas are meant to NOT grow), a lattice linkage is solving a connection problem for entities that were never going to connect — kill and leave interseed standalone.

**Latent-backlog-formalize: interject's discovery-interest profile decay (30d implied, per memory-architecture-convergence table) has no measured half-life — same epistemic-engine pattern as sylveste-22oi.7.5 but unscoped for interject**

- Component: interject; Auraken (epistemic engine pattern)
- Evidence strength: weak
- Effort: spike-days
- Novelty: adopt-known
- Frontier basis: internal (docs/brainstorms/2026-03-07-memory-architecture-convergence.md system map; sylveste-22oi.7.5 bead description)
- Rationale: sylveste-22oi.7.5 is building a principled promotion/decay/harpoon-test epistemic engine for Auraken's cognitive profile. The memory-architecture-convergence brainstorm's system-map table lists interject's interest-profile decay as '30d implied' — i.e. assumed, not measured or principled. Once the epistemic engine's half-life/harpoon-test machinery exists for Auraken, it's a near-zero-marginal-cost reuse target for interject's own profile decay, which currently has no equivalent discipline.
- Kill rule: Do not start until sylveste-22oi.7.5 ships. Then Phase-1: check whether interject's interest-profile 30-day decay produces observably wrong behavior (recommendations for interests the user has abandoned, or premature drop of live interests) in the last 90 days of interject_scan logs. If no observable failure, the implied heuristic is fine — kill, don't port the epistemic-engine machinery for a problem with no evidence.
