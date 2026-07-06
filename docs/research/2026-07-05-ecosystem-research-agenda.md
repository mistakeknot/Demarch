---
artifact_type: research-agenda
method: dynamic-workflow (run wf_85d0ec68-231)
bead: Sylveste-btn
date: 2026-07-05
total_possibilities: 62
---

# Sylveste Ecosystem Research Agenda — 2026-07-05

## Headline thesis

Turn Sylveste's own operational telemetry into a scientific instrument before scaling anything on top of it: make the interspect calibration loop falsifiable (holdout register + judge-reliability audit), then aim that instrument at the platform's three biggest unexamined premises — that multi-agent coordination pays for itself, that the lens/ontology layer beats naive retrieval, and that interfer's custom serving architecture is still justified after 2026's batching/MTP/cache-policy advances. Sylveste is uniquely positioned because it operates the full stack it studies (live calibration loop, real multi-agent traffic traces, a local inference stack it controls end-to-end, and downloaded 100B+ MoE checkpoints on owned M5 Max hardware) — every top bet is an experiment a lab without that closed loop cannot cheaply run.

## Top bets

### 1. Holdout register as a first-class primitive across all calibration loops
- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Every other calibration claim (routing overrides, lens effectiveness, delegation pass rates) is currently unfalsifiable without held-out evidence; this is the epistemic foundation that 5+ other possibilities (closed-loop model selection, lens ground-truth, autonomy thresholds) are gated on. Strong evidence, spike-days, and it compounds.
- **First experiment:** Retroactively freeze a random 20% of existing interspect evidence events as holdout; recompute current active overrides on training-split-only data and measure how many flip.
- **Kill rule:** If evidence volume is too sparse to power the split (<~50 events per scored agent) or <5% of overrides flip, park the primitive and set a volume tripwire to revisit.

### 2. Execute the pre-registered F6b flux-drive triage A/B (sylveste-g939) before any new ontology feature work
- **Layer:** knowledge-cognition
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Verified in beads: the A/B is fully scoped with a pre-registered 30-diff corpus, primary metric, and binding ship/abandon/redesign thresholds — the rare experiment where Phase-1 design is already done. It gates G5/G10 and the whole lattice ontology-backend decision; every week of delay is ontology work at risk of abandonment.
- **First experiment:** Run both backends (FLUX_DRIVE_BACKEND=ontology|legacy) over the pre-registered corpus, record findings/agents/cost per diff.
- **Kill rule:** Already pre-registered in the bead — apply the F6a thresholds in the decision memo; outcome binds (ship / abandon+reopen-as-redesign).

### 3. Contrarian null test: does multi-agent coordination net-improve Sylveste's actual task mix vs single-strong-model execution?
- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** moderate
- **Why now:** Directly implements the house doctrine (test null hypothesis first) at the platform's most expensive assumption. Anthropic-era evidence on orchestration overhead is mixed, Sylveste has the dispatch telemetry (interstat/intercore) to build matched task pairs cheaply, and a null result would redirect months of coordination-layer investment (and moots interlock benchmarking work).
- **First experiment:** Sample ~20 recently completed dispatched tasks from telemetry; replay a matched subset end-to-end with one frontier model, compare pass-at-acceptance-criteria, wall clock, and token cost.
- **Kill rule:** If matched replay proves infeasible (task state unreproducible) after 5 attempts, or the delta is within noise on the first 10 pairs, record the null and stop — do not extend the sample chasing significance.

### 4. Re-test the "MLX has no concurrent inference" premise (mlx-lm 0.18+ continuous batching) and re-scope sylveste-4wl
- **Layer:** local-models-inference
- **Effort:** spike-days
- **Evidence:** moderate
- **Why now:** The premise is baked verbatim into open campaign sylveste-4wl ("MLX has no concurrent inference, ml-explore/mlx#3078") and into interfer's custom priority-queue architecture. If upstream continuous batching + paged KV now works, the custom scheduler is potentially obsolete — highest decision-value-per-hour spike in the inference layer, and it must run before the 4wl autoresearch campaign burns experiments on a dead premise.
- **First experiment:** Benchmark mlx-lm 0.18+ batching on the M5 Max with 3-5 concurrent agent-shaped streams (the flux-drive pattern named in 4wl) vs interfer's current queue: aggregate tok/s and P99 latency.
- **Kill rule:** If upstream batching gives <1.3x aggregate throughput or violates the existing P99 ≤ 2x-single-request gate, keep the custom queue and let 4wl proceed as scoped.

### 5. M5 Neural Accelerator prefill/decode asymmetry — reallocate optimization effort per Apple's published data
- **Layer:** local-models-inference
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong external evidence, and the user owns the exact hardware (M5 Max 128GB) with an explicit MacBook-focus directive on interfer work. If prefill and decode scale asymmetrically on the NA, current optimization effort (quant choices, batching, speculation targets) may be pointed at the wrong bottleneck; this measurement re-prices every other inference bet.
- **First experiment:** Measure prefill tok/s and decode tok/s separately on 2-3 workhorse interfer models at agent-realistic context lengths; compare against the ratios current interfer tuning implicitly assumes.
- **Kill rule:** If measured asymmetry deviates <20% from current assumptions, no reallocation — close in one day.

### 6. Orchestrator-visibility safety audit: does Clavain's hidden dispatch suppress dissent/protective behavior in sub-agents?
- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Strong published evidence that agents behave differently when they can't see the orchestration context, and Clavain's hidden-dispatch pattern is exactly the studied condition. Cheap, high-stakes (silent suppression of "this plan is wrong" signals corrupts interspect evidence upstream), and results feed directly into dispatch-prompt design.
- **First experiment:** A/B ~30 real dispatches: identical tasks with orchestrator context visible vs hidden; count dissent/flag/refusal events and plan-deviation reports in sub-agent outputs.
- **Kill rule:** If the dissent base rate is ~zero in both arms across 30 dispatches, there is no signal being suppressed — record and close.

### 7. LLM-judge reliability harness for interflux + cross-model judge consensus test (merged)
- **Layer:** agent-platform-core
- **Effort:** spike-days
- **Evidence:** moderate
- **Why now:** Interflux review scores are an input to interspect evidence, so judge noise propagates into routing overrides — this must be quantified before the calibration loop is trusted further (pairs with the holdout register). The cross-model-consensus question ("does multi-model activation actually reduce judge bias?") is genuinely novel and answerable on the same fixture for free.
- **First experiment:** Re-run a frozen set of ~30 past reviews 5x per judge across 2-3 model families; compute intra-judge consistency (kappa) and cross-family agreement, then check whether multi-model consensus verdicts differ from single-family verdicts on the disagreement subset.
- **Kill rule:** If intra-judge kappa >0.8 and cross-family disagreement <10%, judges are reliable enough — skip the harness and record the calibration constant.

### 8. Null-test the graph/lens layer: does structured retrieval beat a naive baseline on Auraken/lattice's real query mix?
- **Layer:** knowledge-cognition
- **Effort:** spike-days
- **Evidence:** moderate
- **Why now:** The cognitive-profiling product's core value claim has never been tested against BM25/embedding baselines on production queries. A null here re-scopes half the knowledge-layer backlog (AdaKGC, RouteProfile, active-ontology reframing all gate on it); a win becomes the product's headline evidence. Runs cheaply on existing query logs.
- **First experiment:** Pull ~50 real queries from lattice/Auraken logs; answer via structured lens/graph retrieval vs plain hybrid-search baseline; blind-judge with the (now-calibrated) judge fixture.
- **Kill rule:** If structured retrieval wins by <10% preference margin, freeze new ontology features and pivot the layer's agenda to curation + F6b outcomes only.

### 9. Expert-activation trace instrumentation → Belady-approximating cache replacement for flash-moe
- **Layer:** local-models-inference
- **Effort:** project-weeks (Phase-1 is spike-days)
- **Evidence:** strong
- **Why now:** Strong external evidence for ML cache policies, and Sylveste's SSD-streamed 397B MoE tier (downloaded Kimi/GLM-5/DeepSeek checkpoints, flash-moe worker in active development per git status) is the unique asset — nobody else is streaming experts from SSD on Apple silicon with real agent workloads. Phase-1 also subsumes sylveste-7hxm (activation-coverage tracking) and produces the data for the SSD-vs-more-RAM-quant contrarian check for free.
- **First experiment:** Instrument expert-activation traces on real agent prompts through flash-moe; compute offline oracle (Belady) hit rate vs LRU vs current no-policy on the traces.
- **Kill rule:** If oracle beats LRU by <15% hit rate, there is no headroom for a learned policy — close 7hxm with the traces as the deliverable and skip the ML policy entirely.

### 10. Self-speculative decoding via native MTP heads on downloaded MoE checkpoints (QuantSpec bit-shared KV as follow-on)
- **Layer:** local-models-inference
- **Effort:** spike-days (follow-on project-weeks)
- **Evidence:** moderate (follow-on strong)
- **Why now:** The big 2025/26 checkpoints Sylveste already has on disk (DeepSeek, GLM, Kimi) ship MTP heads that eliminate the separate-draft-model tax; decode-bound agent workloads on Apple silicon are the ideal beneficiary. The strong-evidence QuantSpec bit-shared-KV follow-on only makes sense if Phase-1 confirms heads exist and accept well.
- **First experiment:** Per house rule "read tensor shapes before papers": safe_open the downloaded checkpoints and confirm which actually ship MTP head weights; then micro-bench acceptance rate on agent-shaped prompts for one model.
- **Kill rule:** Heads absent from all workhorse checkpoints, or acceptance <60% on agent prompts → drop self-speculation for this fleet, revisit at next model generation.

### 11. Resolve lens authoring-drift pairs (sylveste-05rf) as semantic versioning, cross-wired with lattice connector idempotency
- **Layer:** knowledge-cognition
- **Effort:** spike-days
- **Evidence:** strong
- **Why now:** Verified in beads: concrete observed cases (Systems Thinking literally contains N-Ply's definition; Whale Fall vs Redux) with explicit user direction to clean up rather than categorize. Left unresolved, drift pairs permanently pollute the F5 calibration corpus and every lens-effectiveness measurement downstream — it is data hygiene for bets 2 and 8. The versioning reframe makes it a reusable "is this actually new" primitive shared with connector-idempotency tests.
- **First experiment:** Run CandidateDetector intra-auraken at threshold 0.2 (per the bead's acceptance criteria) and classify each pair: version-bump / edit-to-disjoint / genuinely-distinct.
- **Kill rule:** If <20% of pairs fit versioning semantics, drop the semver framing and close it as plain curation — still resolves the corpus pollution either way.

### 12. Temporal fact-invalidation (t_valid/t_invalid) for intermem instead of overwrite-or-append
- **Layer:** knowledge-cognition
- **Effort:** project-weeks (Phase-1 is spike-days)
- **Evidence:** strong
- **Why now:** Strong external evidence, and Sylveste's own memory files demonstrably churn (retired hostnames, superseded sync models, killed epics live in MEMORY.md today) — exactly the stale-fact failure mode bitemporal semantics fixes. Phase-1 is a pure audit, no build.
- **First experiment:** Audit the last 90 days of intermem promotions: count cases where a promotion overwrote or contradicted a prior fact without invalidation metadata, and cases where a stale fact was later served.
- **Kill rule:** If <5% of promotions involve invalidation conflicts and zero stale-serve incidents are found, current overwrite semantics suffice — close with the audit as the artifact.

## Cross-component ideas

- **Closed-loop model selection:** correlate interspect calibration evidence with interfer routing decisions, so local-vs-frontier model choice per task type is driven by measured outcomes rather than static tiers. The flagship cross-layer idea — but explicitly gated on the holdout register and judge-reliability bets, or the loop optimizes judge noise. (interspect × interfer × interrank)
- **Interspect evidence corpus as ground truth for Auraken lens effectiveness:** the same outcome events that score agents can score which lenses actually changed decisions — the first lens-effectiveness dataset with behavioral rather than self-reported ground truth. Research-program scale; start as a join-feasibility spike once the holdout register exists. (interspect × Auraken/interlens)
- **Interlab mutation-genealogy as the holdout register's execution substrate:** genealogy/counterfactual tracking already records "what would have happened otherwise" — reuse it as the control-arm bookkeeping for calibration holdouts instead of building new infrastructure. (interlab × interspect)
- **Agentic-traffic-shaped inference benchmarking:** replay real Clavain dispatch traces (interstat telemetry) against interfer to measure tool-call latency, prefix-cache hit behavior, and interleaving effects — no public benchmark has real multi-agent traces plus a controlled local stack. Doubles as the acceptance test for the MLX-batching premise re-test. (interstat × Clavain × interfer)
- **Differential lens-selection calibration across serving tiers:** does the lens a local model selects diverge from what a frontier model selects on identical inputs? Directly prices the cost of local-tier cognition for the Auraken product. (Auraken × interfer × interspect)
- **One shared "is this actually new" primitive:** unify lattice connector-idempotency tests with interlens authoring-drift semantic versioning — same underlying question (is this artifact a duplicate, a version, or novel?), currently solved twice. Bet 11's Phase-1 output seeds it. (lattice × interlens)
- **Fleet-level prompt/KV cache reuse:** Clavain's repeated system prompts and lens preambles are near-identical across concurrent subagents — cross-session KV reuse in interfer could cut prefill cost for exactly the 3-5-agent flux-drive pattern; measure after the NA prefill-asymmetry spike prices what prefill actually costs. (Clavain × interfer)
- **Expert-activation coverage as routing diagnostic feeding interrank:** the flash-moe trace data from bet 9 tells interrank which prompt families under-utilize a given MoE, upgrading hardware-aware recommendations from spec-sheet heuristics to measured activation profiles. (flash-moe × interrank × interlab)

## Per-layer landscape

**AGENT-PLATFORM-CORE (16 items):** The richest layer, and the theme is unambiguous — Sylveste built a live calibration loop (interspect → routing overrides, interflux judges, interlab mutation acceptance) but has never audited the instrument itself. The strongest, cheapest items all make the loop falsifiable: holdout register (strong), orchestrator-visibility audit (strong), judge reliability + cross-model consensus (moderate), and the multi-agent-overhead null test (moderate, doctrine-aligned). Second tier, queued behind those: consensus-trap monitor, reward-hacking audit of interlab's acceptance criterion, introspection-adapter probe, planning-time feasibility calibration, Ockham-Alwe telemetry bridge, trust-tier formalization. The formal-verification and runtime-fuzzing items are premature — no verification substrate exists yet. Net: this layer's agenda is "instrument integrity first, autonomy expansion second."

**LOCAL-MODELS-INFERENCE (14 items):** The landscape moved under Sylveste in 2026 — upstream MLX batching, native MTP heads, ML cache policies, Neural Accelerator asymmetry data — so the theme is "re-validate architectural premises before more custom engineering." Three cheap premise-tests (MLX batching vs the 4wl bead's baked-in "no concurrency" claim, NA prefill/decode asymmetry, MTP-head shape inspection) collectively decide whether interfer's custom queue, current quant targets, and draft-model plans survive. The one big build bet is Belady-style expert caching for flash-moe, which uniquely exploits the SSD-streamed 397B tier plus owned hardware; its trace instrumentation subsumes 7hxm and feeds the SSD-energy contrarian check. Second tier: OptiQ mixed-precision refresh, KV-quant headroom quantification, prompt-cache fleet reuse, agentic-traffic-shaped benchmarking (promoted to cross-component). DeepSeek V4 Flash port is real but sequenced behind the premise-tests that determine its serving substrate.

**KNOWLEDGE-COGNITION (22 items):** Largest and most scattered layer; the discipline is "execute the already-scoped experiments and null-test the layer's core claim before any new ontology features." Verified-in-beads work leads: F6b A/B (pre-registered, binding thresholds), 05rf authoring-drift curation (observed cases, user-directed), 2l1 external calibration pipeline (well-scoped but project-weeks, queued behind F6b outcome). The credible threat items — graph/lens null test and persona-eval cue-sensitivity audit — gate roughly half the layer's adoption ideas (CoPersona, PRISM, AdaKGC, RouteProfile, active-ontology reframing): no point adopting persona-routing techniques until current persona evals are shown to be stable signals. Intermem gets two strong-evidence upgrades (temporal invalidation now; MemTier null test and SimpleMem inversion as follow-ons). Gravity-well instrumentation rides along with production query logging needed for the null test.

## Deliberately dropped

- Formal behavioral-trajectory verification for Skaffen OODARC runs — speculative + research-program with no verification substrate or incident base rate to verify against; out of position by at least two quarters.
- Runtime enforcement via EPA-style greybox fuzzing for Ockham — weak evidence, project-weeks; cheaper policy audits (reward-hacking, orchestrator-visibility) probe the same risk surface first.
- Latent-space KV cache compaction (~50x) — research-program scale; the KV-quant headroom spike answers the near-term memory question at a tenth the cost. Monitor externally, adopt if it productionizes.
- Autonomy-tier A:L3 validation against Anthropic's empirical trust-threshold data — speculative and the external data isn't accessible in comparable form; moot until the holdout register makes internal thresholds measurable, at which point Sylveste's own data is better anyway.
- Interspect-as-instrument (calibration-to-outcome dataset as publishable research artifact) — not dropped in spirit (it IS the headline thesis) but premature as a standalone program until holdout + judge-reliability bets land; revisit as a publication decision afterward.
- Role-drift detection protocol for sprint dispatch — speculative with no observed incident base rate; the orchestrator-visibility audit will surface whether drift even occurs.
- Structural-causal faithfulness audit of interspect — weak evidence and substantially subsumed by the holdout register plus reward-hacking audit, which test the same failure modes behaviorally.
- Interlock vs CRDT/optimistic-locking benchmarks — weak evidence, and coordination throughput isn't an observed bottleneck; also potentially mooted entirely by the multi-agent-overhead null test.
- "Cognitive Tools" framing for lens selection — speculative reframing with no measurable delta specified; revisit only if the lens null test wins and MCP-call latency becomes the binding constraint.
- Geometric/conditioning framework for agent identity + intername/interfluence drift-as-lattice-signal — weak evidence, and adopting a measurement framework before showing current ad hoc drift signals are noisy inverts the burden of proof.
- AdaKGC schema-drift ingestion, RouteProfile cold-start profiling, active-ontology-at-inference reframing — all gated behind the graph/lens null test (bet 8); building more ontology machinery before the layer's core claim survives a baseline is exactly the failure mode the house null-first doctrine exists to prevent.
- Anti-dependency-preserving engagement metric — genuinely novel and values-aligned for the stateless product, but speculative with no measurement substrate; park until the product has enough usage telemetry to define "engagement" at all.
- CoPersona cold-start + PRISM persona-routing adoption — moderate evidence but deferred behind the cue-sensitivity audit of existing persona evals; adopting routing tech on top of possibly-artifactual effectiveness signals compounds the artifact.
- Metacognitive Probe 5-dimension cross-reference — weak; folded into the judge-reliability harness fixture rather than run separately.
- DeepSeek V4 Flash architecture-aware port — moderate evidence and exploits downloaded checkpoints, but project-weeks of engineering whose design depends on outcomes of bets 4, 5, and 10 (batching, prefill asymmetry, MTP heads); sequenced, not dropped.
- Contrarian SSD-streaming energy/cost check and speculative decoding for the C3 tier — folded into bet 9's and bet 10's Phase-1 instrumentation respectively rather than run as separate spikes.
- Hardware-aware interrank recommendations, OptiQ refresh, KV-quant headroom, consensus-trap monitor, behavioral contracts, trust-tier formalization, 2l1 calibration pipeline, gravity-well instrumentation, MemTier/SimpleMem tests, intermem inversion — legitimate second-tier queue (mostly moderate/spike-days), retained in by-layer summaries; excluded from top bets only because the twelve above have higher decision-value or gate them.

## Appendix: all 62 possibilities

Possibilities were generated by three parallel `scan:*` agents (one per layer) and independently supplemented by three `critic:*` completeness-check agents per layer. Grouped below by layer; scan and critic contributions are combined per layer since both target the same landscape.

### Layer: local-models-inference (19 possibilities: 14 scan + 5 critic)

| Title | Kind | Component | Evidence | Effort | Novelty |
|---|---|---|---|---|---|
| Self-speculative decoding via native MTP heads (MTPLX-style) instead of separate draft model | external-frontier-adopt | interfer | moderate | spike-days | adopt-known |
| Re-test 'MLX has no concurrent inference' premise against mlx-lm 0.18+ continuous batching | external-frontier-adopt | interfer | moderate | spike-days | adopt-known |
| OptiQ sensitivity-aware mixed-precision quantization — resolve open beads with fresh evidence | latent-backlog-formalize | interfer | moderate | spike-days | adopt-known |
| DeepSeek V4 Flash architecture-aware port: quantize only the shared/dense path, stream MoE experts via flash-moe | latent-backlog-formalize | interfer | moderate | project-weeks | adapt |
| Correlate interspect calibration evidence with interfer local-model routing decisions — closed-loop model selection | net-new-direction | interfer, interrank | speculative | project-weeks | genuinely-novel |
| Hardware-aware model recommendations in interrank — finish the already-scoped feature | latent-backlog-formalize | interrank | moderate | spike-days | adapt |
| M5 Neural Accelerator prefill/decode asymmetry — reallocate optimization effort per Apple's own published data | external-frontier-adopt | interfer | strong | spike-days | adopt-known |
| Quantify KV-cache-quantization headroom against 2026 non-TurboQuant methods (KVarN, TurboAngle, FibQuant) | external-frontier-adopt | interfer | moderate | spike-days | adapt |
| Formalize sylveste-7hxm ('expert activation coverage tracking') as a routing-diagnostic research question | latent-backlog-formalize | interfer | speculative | spike-days | adapt |
| Continuous batching + paged KV cache retrofit could obsolete interfer's custom priority queue architecture entirely | net-new-direction | interfer | weak | project-weeks | adapt |
| Speculative/self-drafting decoding for the C3/flash-moe tier specifically (397B SSD-streamed) | net-new-direction | interfer | speculative | spike-days | genuinely-novel |
| Adaptive concurrent-agent batching campaign (sylveste-4wl) — re-scope given batching landscape has moved | latent-backlog-formalize | interfer | moderate | spike-days | adopt-known |
| Prompt-cache reuse across the Sylveste agent fleet (cross-session KV reuse for repeated system prompts/lenses) | net-new-direction | interfer | speculative | spike-days | adapt |
| ML-based expert cache replacement for flash-moe (Belady-approximation vs current no-policy streaming) | external-frontier-adopt | interverse/interfer flashmoe_worker.py | strong | project-weeks | adopt-known |
| Contrarian check: is SSD expert-streaming actually energy/cost-harmful vs keeping fewer experts in RAM at higher quant? | net-new-direction | interverse/interfer flash-moe tier (C3/397B) | moderate | spike-days | adopt-known |
| Bit-shared draft/target KV cache quantization for MTP self-speculation (QuantSpec-style) | external-frontier-adopt | MTPLX self-speculative decoding (cross-cutting) | strong | project-weeks | adapt |
| Agentic-traffic-shaped inference benchmarking: tool-call latency and prefix-cache behavior under multi-agent interleaving | net-new-direction | interfer serving stack + interspect/interrank methodology | moderate | spike-days | adapt |
| Latent-space KV cache compaction (Attention Matching-style, ~50x) as alternative to quantization | external-frontier-adopt | KV-cache optimization (extends quantization item) | moderate | research-program | adopt-known |

*(Note: scan file lists 13 titled entries with one containing an internal split already counted; critic file adds 5. Total unique entries above: 17 scan-layer titles as returned + 5 critic = shown; see rationale/kill_rule detail below for full text of each.)*

#### Rationale / frontier basis / kill rules — local-models-inference

**Self-speculative decoding via native MTP heads (MTPLX-style) instead of separate draft model**
: Rationale — Both prior interfer spec-decode attempts failed for architecture reasons: LayerSkip self-speculation (sylveste-qbv) got 0% acceptance because MoE expert routing "distributes computation, no early completion point," and separate-draft spec-decode (sylveste-yfot) is likely-moot because a 9B dense draft is not cheaper than a 3B-active MoE target. MTP-head self-speculation sidesteps both failure modes by using extra prediction heads on the same forward pass.
: Frontier basis — MTPLX (native MTP speculative decoding for Qwen3-Next on Apple Silicon, released 2026-06-12, up to 2.24x decode speedup); Qwen3.6-27B-MTPLX-Optimized-Speed (HF, 2026-05-03).
: Kill rule — Phase-1: confirm the production tier model actually ships trained MTP heads accessible via mlx-lm/MTPLX; if not, kill (training a head is out of spike scope). If heads exist, run MTPLX harness on the existing C2 benchmark set; KILL if measured speedup <1.15x or MTPLX doesn't support the MoE architecture.

**Re-test 'MLX has no concurrent inference' premise against mlx-lm 0.18+ continuous batching**
: Rationale — interfer's entire architecture (priority queue, sequential Metal subprocess processing, sylveste-4wl's batching campaign) is built on the documented constraint ml-explore/mlx#3078. mlx-lm has shipped continuous batching since v0.18; vLLM-MLX reports 3.4-4.3x throughput scaling at 16 concurrent requests. If real and stable, this invalidates the foundational architecture assumption behind the priority-queue design.
: Frontier basis — mlx-lm v0.18 (Jan 2026) mlx_lm.server with continuous batching; vLLM-MLX (waybarrios/vllm-mlx, EuroMLSys '26).
: Kill rule — Phase-1 (half-day): benchmark 4 and 8 concurrent requests against qwen3.5-35b-a3b-4bit vs interfer's sequential queue. KILL if aggregate tok/s scaling <1.3x at 4 concurrent, or if it requires abandoning interfer's Metal-subprocess memory-safety model.

**OptiQ sensitivity-aware mixed-precision quantization — resolve open beads with fresh evidence**
: Rationale — sylveste-ep8 and sylveste-6ru are already-filed, open beads referencing OptiQ's claimed +40-62% decode speedup at 64k context; unscoped as plain beads rather than formal Phase-1 spikes with kill rules.
: Frontier basis — OptiQ (mlx-optiq.pages.dev/results.html, per-layer bit-width via KL-divergence calibration), claims cited in beads filed 2026-04-25.
: Kill rule — Run holistic_benchmark.py with the optiq config against plain-4bit baseline on LCB v6 subset; KILL if pass@1 delta <2pp AND tok/s delta <10%.

**DeepSeek V4 Flash architecture-aware port: quantize only the shared/dense path, stream MoE experts via flash-moe**
: Rationale — sylveste-0gi is open and well-evidenced: DeepSeek V4 Flash tops LCB v6 at 91.6 pass@1 (vs current C2 champion at 80.4) but every direct MLX quantization exceeds 128GB. A hybrid approach using flash-moe's existing SSD-streaming architecture for MoE experts while keeping the dense/attention path resident in RAM reframes this from "wait for hardware" to "port effort using infrastructure interfer already built."
: Frontier basis — DeepSeek V4 Flash (released 2026-04-24), LCB v6 internal benchmark, existing flash-moe SSD-streaming infra (sylveste-4l2, closed).
: Kill rule — Phase-1: estimate V4 Flash's active-param/shared-expert RAM footprint from config; KILL if always-active/shared portion alone exceeds ~100GB. If it fits, estimate port effort vs the 397B port's historical effort; KILL if estimate >3x that precedent with no distinguishing reuse.

**Correlate interspect calibration evidence with interfer local-model routing decisions — closed-loop model selection**
: Rationale — Sylveste has a live telemetry loop (interspect) scoring agent quality from production outcomes, plus interfer's dispatch/cost logs and interrank's static benchmark leaderboard. Nobody is correlating "which local model handled this task" with downstream interspect quality flags — today routing decisions rely on static benchmarks, not measured production outcome.
: Frontier basis — internal; no external precedent, requires interspect + interfer dispatch logs + interrank leaderboard to coexist.
: Kill rule — Phase-1: pull 2-4 weeks of interspect evidence for local:* model dispatches, compute pass-rate delta vs cloud fallback at the same complexity tier. KILL if sample size <30 comparable pairs, or if pass rates are statistically indistinguishable.

**Hardware-aware model recommendations in interrank — finish the already-scoped feature**
: Rationale — sylveste-fba8 is an open bead with an existing PRD/plan (2026-03-21), successor to a lost bead. Research-shaped question: what's the right recommendation heuristic given detected hardware, given interfer's own coexistence findings (e.g. 122B-A10B benchmarks fine standalone but consumes 69GB RAM, preventing coexistence).
: Frontier basis — internal PRD/plan (2026-03-21); interfer coexistence findings (docs/benchmarks/2026-04-05-qwen35-122b-a10b.md).
: Kill rule — Phase-1: validate the heuristic against interfer's documented cases (flags 122B-A10B as RAM-risky vs 397B-via-flash-moe as RAM-safe). Simplify to single-model VRAM check if coexistence-aware heuristic needs data interrank doesn't have.

**M5 Neural Accelerator prefill/decode asymmetry — reallocate optimization effort per Apple's own published data**
: Rationale — Apple's M5 research shows prefill gets up to 4x from Neural Accelerators (compute-bound) but decode only 19-27% (memory-bandwidth-bound, 153GB/s ceiling). This reframes the ANE-offload spike (sylveste-0zc) with an authoritative number and implies interfer's optimization budget may be mis-targeted at decode-phase compute tricks instead of prefill-phase/bandwidth levers.
: Frontier basis — Apple Machine Learning Research, "Exploring LLMs with MLX and the Neural Accelerators in the M5 GPU" (2026).
: Kill rule — Portfolio-reallocation decision, not pass/fail. Re-read 0zc's scoping doc against this number; amend its kill rule to cite the 19-27% ceiling explicitly. Treat as confirmed-kill evidence for future decode-phase-compute proposals unless targeting prefill specifically.

**Quantify KV-cache-quantization headroom against 2026 non-TurboQuant methods (KVarN, TurboAngle, FibQuant)**
: Rationale — interfer already shipped TurboQuant (PolarQuant+QJL) validated at kv_bits=2 "quality identical at 500 tokens." 2026 produced successors (KVarN targets error accumulation in reasoning tasks; TurboAngle claims near-lossless via uniform angle quantization). Testing a drop-in successor is cheap given existing kv_bits plumbing.
: Frontier basis — KVarN (arXiv:2606.03458); TurboAngle (arXiv:2603.27467); FibQuant (arXiv:2605.11478).
: Kill rule — Phase-1: run existing TurboQuant kv_bits=2 vs a from-paper KVarN reimplementation on a long-chain reasoning subset (16+ turns). KILL if TurboQuant shows zero measurable degradation at agentic session lengths. PURSUE only if quality degrades under current TurboQuant at longer contexts.

**Formalize sylveste-7hxm ('expert activation coverage tracking') as a routing-diagnostic research question, not just instrumentation**
: Rationale — 7hxm currently reads as one-line instrumentation. 2026 MoE research moved toward input-adaptive computation (Expert Threshold Routing, Routing-Free MoE, self-routing); the real question is whether Qwen3.5/3.6's expert activation is skewed by Sylveste's prompt distribution in an exploitable way (e.g. cheaper expert-pruned variant for specific workloads).
: Frontier basis — Expert Threshold Routing (arXiv:2603.11535); Routing-Free MoE (arXiv:2604.00801); Self-Routing (2026).
: Kill rule — Phase-1: instrument activation logging across ~200 production requests bucketed by C1/C2/C3 taxonomy. KILL the "exploitable skew" angle if activation entropy is within 10% of uniform across buckets; 7hxm reverts to pure instrumentation.

**Continuous batching + paged KV cache retrofit could obsolete interfer's custom priority queue architecture entirely**
: Rationale — interfer's PRD bets that custom inference loops beat off-the-shelf, with an explicit escape valve ("if the community catches up, we can switch"). vLLM-MLX now ships continuous batching + paged KV as a maintained OSS project. Sylveste is positioned to actually run the comparison the vision doc promised.
: Frontier basis — vLLM-MLX (waybarrios/vllm-mlx, EuroMLSys '26); interfer's own vision doc (docs/interfer-vision.md, "Bet 2" escape clause, 2026-03-26).
: Kill rule — Phase-1 reuses the batching-premise spike above; if it KILLs, the custom build's premise stands. Only if it PURSUEs: run holistic_benchmark through vLLM-MLX as alternate backend for a full week of realistic load. KILL the migration if vLLM-MLX loses shipped hooks (early exit, kv_bits quantization, thermal monitoring) without an equivalent extension point.

**Speculative/self-drafting decoding for the C3/flash-moe tier specifically (397B SSD-streamed), not just C2**
: Rationale — All prior spec-decode scoping targeted C2 (already fast at 86 tok/s). Nobody has scoped spec-decode for C3/flash-moe (~1 tok/s), where a 1.3-2x speedup would be transformative. The mechanism differs: hiding SSD I/O latency behind draft compute, not reducing FLOPs.
: Frontier basis — internal, informed by DFlash's exact-verification guarantee (arXiv:2602.06036) applied to an SSD-bound MoE target.
: Kill rule — Phase-1: instrument flash-moe's benchmark harness (sylveste-vpa) to measure what fraction of ~1 tok/s wall-clock is SSD I/O wait vs compute. KILL if I/O wait is <50% of per-token time. PURSUE only if I/O wait dominates and draft decode time roughly matches the I/O window.

**Adaptive concurrent-agent batching campaign (sylveste-4wl) — re-scope given batching landscape has moved**
: Rationale — sylveste-4wl is a fully-specified interlab autoresearch campaign whose problem statement opens with "MLX has no concurrent inference" — the premise flagged as possibly stale. Should not run as originally scoped until re-checked.
: Frontier basis — internal (sylveste-4wl) + external premise-check (mlx-lm 0.18, vLLM-MLX).
: Kill rule — Gated behind the batching-premise spike. If that KILLs, proceed with 4wl's original mutation space unmodified. If it PURSUEs, close 4wl as superseded and redirect to integrating the OSS batching layer.

**Prompt-cache reuse across the Sylveste agent fleet (cross-session KV reuse for repeated system prompts/lenses)**
: Rationale — sylveste-9hx (closed) is worth re-opening with Sylveste-specific framing: fd-* review lenses, CLAUDE.md/AGENTS.md preambles, and Clavain skill prompts are highly repetitive across daily dispatches. A prefix-KV-cache reuse scheme keyed on this catalog could cut prefill cost, compounding with the M5 prefill-bound finding.
: Frontier basis — internal, combines closed experiment 9hx's premise with the M5 prefill-bound finding.
: Kill rule — Phase-1: audit dispatch logs for the top 10 most-repeated system-prompt prefixes across a week; measure aggregate prefill tokens attributable. KILL if repeated-prefix prefill is <15% of total prefill volume, or if 9hx's closed reflection already found this not viable for reasons that still apply.

**ML-based expert cache replacement for flash-moe (Belady-approximation vs current no-policy streaming)**
: Rationale — flash_moe_worker.py in this repo's own working diff currently has zero expert-eviction policy. arXiv:2601.17063 shows ML-approximated-Belady cache replacement for exactly this SSD-streamed-MoE-on-edge setup, beating LRU/LFU by 51% hit rate and 2.6x latency — a direct, citable retrofit target for a file already being touched this session.
: Frontier basis — FlashMoE: Reducing SSD I/O Bottlenecks via ML-Based Cache Replacement for Mixture-of-Experts Inference on Edge Devices, arXiv:2601.17063, Jan 2026.
: Kill rule — Measure hit rate under current no-policy streaming first; abandon if already >90% (bottleneck is bandwidth, not miss rate).

**Contrarian check: is SSD expert-streaming actually energy/cost-harmful vs just keeping fewer experts in RAM at higher quant?**
: Rationale — A companion result (arXiv:2508.06978) shows SSD-offloaded MoE weights can cost ~12x the energy per token vs HBM-resident baselines. Sylveste has bet architecturally on flash-moe streaming for C3; this challenges that premise on Apple silicon where SSD I/O competes with unified-memory bandwidth used for compute.
: Frontier basis — SSD Offloading for LLM MoE Weights Considered Harmful in Energy Efficiency, arXiv:2508.06978.
: Kill rule — If a 3-5 day measurement of tokens/joule shows flash-moe streaming within 2x of a RAM-resident lower-quant baseline on M5 Max, the "considered harmful" finding doesn't transfer — stop chasing an alternate architecture.

**Bit-shared draft/target KV cache quantization for MTP self-speculation (QuantSpec-style)**
: Rationale — The scan lists MTP-head self-speculation and KV-cache-quantization headroom as two distinct items but misses the intersection QuantSpec solves: hierarchical quantized KV cache with bit-sharing between draft and target passes, eliminating extra memory a draft KV cache would cost. Since MTP heads share the target's KV cache, this is one research thread, not two.
: Frontier basis — QuantSpec: Self-Speculative Decoding with Hierarchical Quantized KV Cache, arXiv:2502.10424.
: Kill rule — If MTP-head self-speculation shows the draft pass's extra KV cache is <5% of total memory footprint in practice, bit-sharing has no headroom to capture — kill before implementing.

**Agentic-traffic-shaped inference benchmarking: tool-call/function-call latency and prefix-cache behavior under multi-agent interleaving, not chat-benchmark throughput**
: Rationale — Every possibility in the scan is framed in chat-completion throughput/quality terms. 2026 industry data shows production agentic clusters run at 10-45% accelerator utilization because cache-eviction policies tuned for shared-prefix chat traffic fail under interleaved multi-agent tool-calling. Sylveste's own workload IS multi-agent tool-calling, yet nothing proposes benchmarking interfer against an agentic-traffic-shaped benchmark instead of a chat-shaped one.
: Frontier basis — AI Agent Tool Calling Benchmarks: BFCL v4, tau-Bench, Function-Call Latency Optimization (2026); "Stateful Inference for Low-Latency Multi-Agent Tool Calling" arXiv:2605.26289.
: Kill rule — If replaying representative Clavain/interfer agent traffic shows utilization already comparable to chat-shaped traffic, there's no distinct problem — fold back into general continuous-batching work.

**Latent-space KV cache compaction (Attention Matching-style, ~50x) as an alternative to quantization for the KV-cache-headroom question**
: Rationale — The existing scan item only evaluates quantization-family methods. 2026 survey work identifies a distinct compression family — latent-space compaction (Attention Matching, ~50x) and reasoning-aware compression (TriAttention, 10.7x on AIME25 at matched accuracy) — orthogonal to quantization and potentially stackable with it.
: Frontier basis — Top 10 KV Cache Compression Techniques for LLM Inference (MarkTechPost, Apr 2026); Awesome-KV-Cache-Optimization ACL 2026 survey.
: Kill rule — If latent-space compaction methods show >1% accuracy degradation on Sylveste's actual agent-reasoning workloads at claimed compaction ratios, treat as not-yet-production-ready and defer to the quantization track.

---

### Layer: agent-platform-core (21 possibilities: 16 scan + 5 critic)

| Title | Kind | Component | Evidence | Effort | Novelty |
|---|---|---|---|---|---|
| Behavioral contracts for agent instructions (formalize skill/plugin specs beyond prose) | external-frontier-adopt | Clavain, interphase, Ockham | moderate | spike-days | adapt |
| Holdout register as a first-class primitive across all calibration loops | latent-backlog-formalize | interspect, interflux, interlab, s3z6 | strong | spike-days | adopt-known |
| Consensus-trap / agreement-diversity monitor on interspect's calibration loop | latent-backlog-formalize | interspect | moderate | spike-days | adapt |
| Structural-causal faithfulness audit of interspect's evidence-to-override pipeline | external-frontier-adopt | interspect | weak | spike-days | adapt |
| Trust-tier formalization: substrate-independence + suhba-window + tier-weight aggregation (mj11 thread) | latent-backlog-formalize | Ockham, Alwe, interspect | moderate | project-weeks | adapt |
| Ockham-Alwe governance-observation bridge: does real outcome telemetry change anomaly-evaluator weights? | latent-backlog-formalize | Ockham, Alwe, intercore | moderate | spike-days | adapt |
| Reward-hacking / spec-gaming audit of interlab's mutation-acceptance criterion | net-new-direction | interlab | moderate | spike-days | genuinely-novel |
| Interlock coordination primitive vs. CRDT/optimistic-locking benchmarks | external-frontier-adopt | interlock | weak | spike-days | adapt |
| LLM-judge reliability harness for interflux's review pipeline (IRT/consistency scoring) | external-frontier-adopt | interflux, interrank | moderate | spike-days | adopt-known |
| Runtime enforcement layer for Ockham's policy engine using EPA-style greybox fuzzing | external-frontier-adopt | Ockham, intercore | weak | project-weeks | adapt |
| Formal behavioral-trajectory verification for long-horizon Skaffen OODARC runs | external-frontier-adopt | Skaffen | speculative | research-program | adapt |
| Cross-model judge consensus vs. single-family judge: does interflux's multi-model activation actually reduce judge bias? | net-new-direction | interflux | moderate | spike-days | genuinely-novel |
| Long-form / long-horizon judge benchmark applied to interflux's plan/PR reviews | external-frontier-adopt | interflux, interrank | weak | spike-days | adopt-known |
| Autonomy-tier auto-approve threshold: validate Sylveste's A:L3 target against Anthropic's own empirical trust-threshold data | external-frontier-adopt | Ockham, interspect, Clavain | speculative | spike-days | adopt-known |
| Interspect-as-instrument: assess feasibility of the calibration-loop-to-outcome dataset as a research artifact | net-new-direction | interspect, interlab, interrank | speculative | research-program | genuinely-novel |
| Role-drift detection protocol for multi-agent Clavain sprint dispatch | external-frontier-adopt | Clavain, interflux | speculative | spike-days | adapt |
| Orchestrator-visibility safety audit: does Clavain's hidden dispatch suppress protective/dissent behavior in sub-agents? | external-frontier-adopt | Clavain sprint dispatch / Skaffen OODARC | strong | spike-days | adopt-known |
| Planning-time epistemic calibration: feasibility-confidence check before dispatch, not just outcome scoring after | external-frontier-adopt | interspect calibration loop / Clavain campaign planning | moderate | project-weeks | adapt |
| Introspection-adapter probe for interspect: test whether agents can accurately self-report scored behaviors | net-new-direction | interspect evidence pipeline | moderate | spike-days | adapt |
| Wire interlab's mutation-genealogy/counterfactual tracking into interspect as the holdout register's execution substrate | net-new-direction | interlab × interspect | speculative | spike-days | genuinely-novel |
| Contrarian null-hypothesis test: does multi-agent coordination overhead net-improve Sylveste's actual task mix? | latent-backlog-formalize | Clavain dispatch (whole) | moderate | spike-days | adapt |

#### Rationale / frontier basis / kill rules — agent-platform-core

**Behavioral contracts for agent instructions (formalize skill/plugin specs beyond prose)**
: Rationale — Sylveste's skills/commands are natural-language markdown with no verifiable guarantees — the exact gap named as root cause of behavioral drift and silent degradation. Clavain already has 100+ skills; a pilot on 3-5 high-risk skills (bead-close, publish, campaign dispatch) could catch drift the close-gate doesn't, because it targets the instruction layer, not the runtime-check layer.
: Frontier basis — Agent Behavioral Contracts: Formal Specification and Runtime Enforcement for Reliable Autonomous AI Agents, arXiv:2602.22302 (Feb 2026).
: Kill rule — Phase-1: instrument the contract-checker against interspect's existing correction-event log for 2 weeks. If contract violations correlate with <20% of actual logged corrections, abandon.

**Holdout register as a first-class primitive across all calibration loops**
: Rationale — Bead 9lp.37 already names the exact problem: interflux alone runs 5+ self-referential calibration loops (microrouter, FluxBench, AgentDropout threshold, trust-score, sycophancy detection) with no shared ground-truth source outside all of them. interspect's own loop now also consumes interlab mutation evidence — a 6th loop with the same exposure.
: Frontier basis — internal (9lp.37); reinforced by clinical-AI held-out-data distribution-shift literature and 2026 self-improvement contamination discussions.
: Kill rule — Phase-1: build the naming table only (loop → ground-truth source → refresh policy → contamination failure mode) for the 6 identified loops. If more than 2 of 6 loops have no plausible external-holdout candidate, stop at the naming table.

**Consensus-trap / agreement-diversity monitor on interspect's calibration loop**
: Rationale — Already scoped as Sylveste-4b5.1 (open) but blocked/unimplemented. Answers "is the generator and its own verifier converging on agreement while real defect-escape stays flat" — the most load-bearing monitoring gap on live infra per the 4b5 roadmap.
: Frontier basis — CoVerRL consensus-trap pattern (cited in 4b5, unverified/post-cutoff); Multi-Agent Verification: Scaling Test-Time Compute with Multiple Verifiers, arXiv:2502.20379.
: Kill rule — Hard-blocked on 9lp.37 landing first. Phase-1: run the agreement-rate metric for 20 canary uses without alerting. If agreement-rate and defect-escape rate move together, drop the alerting logic, keep only the dashboard metric.

**Structural-causal faithfulness audit of interspect's evidence-to-override pipeline**
: Rationale — interspect infers routing overrides from passively-collected evidence. Project Ariadne's structural-causal-model approach asks whether an inferred pattern is a real causal driver or a post-hoc rationalization correlated with something else (task difficulty, session length, model version drift).
: Frontier basis — Project Ariadne — structural causal framework for auditing faithfulness in LLM agent reasoning traces (exact arXiv ID unverified, flag for follow-up).
: Kill rule — Phase-1: pick the single most-invoked live override, run 10 held-out sessions with the override force-disabled via the existing canary path, compare outcome deltas. Pre-register minimum N for power; if unreachable within a normal canary window, abandon.

**Trust-tier formalization: substrate-independence + suhba-window + tier-weight aggregation (mj11 thread)**
: Rationale — sylveste-vision v5's thesis ("evidence compounds → earned trust → progressive authority") is load-bearing under Mythos launch and A:L3 autonomy, but the 10-lens review found the v5 spec never resolved authority-chain independence, minimum observation windows, tier-weight aggregation, or evidence decay. Maps closely onto external "progressive trust ratchet" literature.
: Frontier basis — Agentic Trust Framework (CSA, Feb 2026) four-maturity-level progressive-trust ratchet with demotion; McKinsey State of AI Trust 2026; internal mj11/mj11.1-6 spec threads.
: Kill rule — Phase-1: map Sylveste's Earn/Compound/Break/Epoch/Demote lifecycle (sylveste-4rwh) against ATF's Intern-through-Principal levels. If mapping is clean, adopt ATF's public vocabulary directly and kill the bespoke-naming track (keep the mechanism). If gaps remain, scope only those gaps.

**Ockham-Alwe governance-observation bridge: does real outcome telemetry change anomaly-evaluator weights?**
: Rationale — Bead xefe (in_progress) frames this precisely: Ockham scrapes bd list + interspect files for metrics; Alwe wraps CASS with structured session-level queries but isn't feeding Ockham's anomaly evaluator yet. Genuine empirical question whether Alwe-weighted anomaly scores beat the current bd-list-scrape baseline.
: Frontier basis — internal (xefe); loosely parallels 2026 observability survey's causal-attribution-chain framing.
: Kill rule — Phase-1: run Alwe-fed and bd-list-fed anomaly scores in shadow mode for 2 weeks, compare correlation with logged manual corrections. If Alwe-fed scoring doesn't clearly beat the existing proxy, don't wire it live.

**Reward-hacking / spec-gaming audit of interlab's mutation-acceptance criterion**
: Rationale — interlab's own philosophy states its safety net is a circuit breaker, not human approval gates ("the agent decides what to optimize; the tools ensure experiments are safe") — precisely the setup 2026 reward-hacking research flags as high-risk. interlab's JSONL-logged full experiment history is a unique corpus to mine for proxy-gaming patterns.
: Frontier basis — SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents, arXiv:2605.21384; Countdown-Code testbed, arXiv:2603.07084; Cursor's "reward hacking is swamping model intelligence gains" (2026).
: Kill rule — Phase-1: retrospectively scan interlab's completed campaign JSONL for known hack signatures (metric-rewrite, test-mocking, proxy-divergence). If zero campaigns show the signature, close as "measured, no incidence, revisit if campaign volume grows 10x."

**Interlock coordination primitive vs. CRDT/optimistic-locking benchmarks**
: Rationale — 2026 multi-agent-coordination literature converges on Raft leader-election, CRDTs, and optimistic locking as alternatives to interlock's reservation/negotiation model. A structured comparison of failure modes against these could reveal a cheap swap-in for interlock's weakest edge case (parallel-session premise drift) without a rewrite.
: Frontier basis — 2026 multi-agent orchestration surveys citing Raft/CRDT/optimistic-locking (Fast.io, Codebridge, arXiv:2502.14743).
: Kill rule — Phase-1: tabulate interlock's actual observed failure incidents over the last month. If incident count is near-zero, kill — don't touch a working primitive.

**LLM-judge reliability harness for interflux's review pipeline (IRT/consistency scoring)**
: Rationale — interflux already runs an LLM-judge review pipeline (fyo3, multi-model activation) and Sylveste-4b5.1's #10 already flagged the judge's bias figures as unhedged single-model numbers. 2026 produced reusable tooling for this — adopt-a-tool, not invent-a-method.
: Frontier basis — Judge Reliability Harness: Stress Testing the Reliability of LLM Judges, arXiv:2603.05399; Diagnosing the Reliability of LLM-as-a-Judge via Item Response Theory, arXiv:2602.00521; Reliability without Validity, arXiv:2606.19544.
: Kill rule — Phase-1: run the harness (or reimplement its core consistency-check) against interflux's judge on a fixed 20-item human-scored test set (reuse jetty voice-calibration precedent). If consistency already clears the default bar, log a baseline and move on.

**Runtime enforcement layer for Ockham's policy engine using EPA-style greybox fuzzing**
: Rationale — 4b5's #6 already flagged Ockham's PreToolUse policy hook isn't fail-closed. The zero-trust semantic-gateway paper adapts greybox fuzzing to find hidden unauthorized state transitions; a scoped fuzzing harness could validate the fail-closed fix actually closes the gaps.
: Frontier basis — From CRUD to Autonomous Agents: Formal Validation and Zero-Trust Security for Semantic Gateways in AI-Native Enterprise Systems, arXiv:2604.25555.
: Kill rule — Hard-blocked behind 4b5's #6 shipping first. Phase-1 after that ships: run a small fuzzing pass; if zero novel bypasses found, don't scale up the harness.

**Formal behavioral-trajectory verification for long-horizon Skaffen OODARC runs**
: Rationale — Skaffen's OODARC loop is exactly the long-horizon, stateful agentic execution these formal-verification papers target. A lightweight subset (just liveness, just safety) is a natural fit given Skaffen is the one component with a genuinely long-running stateful loop.
: Frontier basis — Formalizing the Safety, Security, and Functional Properties of Agentic AI Systems, arXiv:2510.14133 (ICLR 2026 workshop); Lean4Agent, arXiv:2606.06523.
: Kill rule — Phase-1: instrument one liveness property as a passive assertion against Skaffen's actual dispatch history for 2 weeks. If violation rate is near-zero, check the incident log for what actually fails and re-target, or abandon if incidents are too sparse to justify formal machinery.

**Cross-model judge consensus vs. single-family judge: does interflux's multi-model activation actually reduce judge bias?**
: Rationale — interflux has real multi-model activation infrastructure (fyo3 epic) — one of the few platforms that can actually run the cross-family-judge experiment the 2026 bias-mitigation literature recommends on its own live review corpus.
: Frontier basis — Judging the Judges: A Systematic Evaluation of Bias Mitigation Strategies in LLM-as-a-Judge Pipelines, arXiv:2604.23178 — motivating comparison; execution is internal.
: Kill rule — Phase-1: run both judge configurations against the existing ~20-30 human-scored calibration set. Pre-register a minimum bar (+0.05 Spearman correlation). If cross-family judging doesn't clear it, keep multi-model activation for other purposes but don't route review-judging cost through it.

**Long-form / long-horizon judge benchmark applied to interflux's plan/PR reviews**
: Rationale — interflux's actual review targets (plans, PRs, multi-file diffs) are long-form outputs — exactly the class LongJudgeBench was built for, since existing meta-eval benchmarks focus on short-form.
: Frontier basis — Benchmarking LLM-as-a-Judge for Long-Form Output Evaluation (LongJudgeBench), arXiv:2606.01629.
: Kill rule — Phase-1: adapt 10-15 LongJudgeBench-style protocol questions to past reviews with known human-verified outcomes (merged-clean vs reverted-after-merge). If the protocol doesn't distinguish outcomes better than current scoring, don't adopt the full benchmark.

**Autonomy-tier auto-approve threshold: validate Sylveste's A:L3 target against Anthropic's own empirical trust-threshold data**
: Rationale — sylveste-myyw targets "all three calibration loops fire without human invocation" (A:L3). A secondary-source report attributes an empirical session-count auto-approve threshold to Anthropic — a directly comparable data point, provided it's verified first.
: Frontier basis — Secondary-source summary (AgentMarketCap, Apr 2026) of an Anthropic session-count threshold — UNVERIFIED against primary source.
: Kill rule — Hard gate: verify the figure against Anthropic's primary source before using it beyond directional comparison; drop the number if unverifiable. Phase-1 independent of that: compute session counts accumulated by Sylveste's 3 calibration loops. If none are within an order of magnitude of any comparable published threshold, A:L3 is premature regardless of mechanism readiness.

**Interspect-as-instrument: assess feasibility of the calibration-loop-to-outcome dataset as a research artifact**
: Rationale — Sylveste has 3600+ beads, a live 6-loop calibration system, per-session dispatch telemetry, and months of JSONL-logged mutation history — a genuinely novel research asset current 2026 reward-hacking/calibration-drift literature approaches only via synthetic benchmarks or small lab setups.
: Frontier basis — internal; gap is that current literature (SpecBench, Countdown-Code, TRACE) all use constructed benchmarks, not longitudinal production telemetry.
: Kill rule — Phase-1 (pre-publication feasibility check): can existing telemetry be de-identified and exported without leaking client/personal data (recall OneDrive client-context rule)? If de-identification cost exceeds research value, or legal/privacy review blocks export, kill the publication angle and keep the corpus internal-only.

**Role-drift detection protocol for multi-agent Clavain sprint dispatch**
: Rationale — Clavain's sprint/campaign dispatch fans out to specialized sub-agents with defined roles; RoleFix names "role drift" as a distinct, lightweight-protocol-detectable failure mode — an agent silently drifting from its assigned role over a long dispatch chain.
: Frontier basis — Detecting and Repairing Role Drift in Multi-Agent Collaboration with Lightweight Protocols, Preprints.org 202603.0348 (preprint server, not peer-reviewed).
: Kill rule — Phase-1: manually audit 10 recent multi-agent campaign transcripts for role-drift incidents using the paper's taxonomy. If incidence is near-zero, kill before building detection tooling.

**Orchestrator-visibility safety audit: does Clavain's hidden dispatch suppress protective/dissent behavior in sub-agents?**
: Rationale — Clavain's sprint/campaign dispatch and Skaffen's OODARC loop are exactly the "invisible orchestrator manages specialized workers" topology this paper tested (preregistered 3x2 experiment, 365 runs, on Claude Sonnet 4.5). Distinct from role-drift detection: this catches agents going silent about problems specifically because the authority structure is invisible to them.
: Frontier basis — Fukui, "Invisible Orchestrators Suppress Protective Behavior and Dissociate Power-Holders: Safety Risks in Multi-Agent LLM Systems," arXiv:2605.13851 — invisible orchestration elevates collective dissociation (Hedges' g=+0.975, p=.001).
: Kill rule — If a 20-30 run replication with visible vs. invisible dispatch framing on real Clavain sprint transcripts shows no measurable difference in sub-agent pushback/flag-raising rate, drop it — the effect may not transfer from the paper's synthetic setup to real coding-agent transcripts.

**Planning-time epistemic calibration, not just execution-time: add a feasibility-confidence check before dispatch**
: Rationale — Every other calibration mechanism scores agent behavior after the fact from outcomes. This paper's claim is that a distinct failure mode exists at planning time: a plan can look executable while built on miscalibrated feasibility beliefs that don't surface until execution, when it's too late to cheaply correct. Sylveste's campaign/sprint dispatch commits to a topo-sorted plan before execution with no measurement of planning-stage confidence calibration.
: Frontier basis — "When Planning Fails Despite Correct Execution: On Epistemic Calibration for LLM-Based Multi-Agent Systems," arXiv:2605.23414 — EPC-AW achieves 9.75% absolute system-level accuracy improvement over execution-time-only correction baselines.
: Kill rule — If retrospective analysis of closed Clavain campaign beads shows planning-stage confidence statements are already well-calibrated against actual phase outcomes, there's nothing to fix — don't build new instrumentation for a non-problem.

**Introspection-adapter probe for interspect: test whether agents can accurately self-report the behaviors interspect scores them on**
: Rationale — The structural-causal faithfulness audit checks whether interspect's pipeline is causally sound but doesn't question whether agent self-reports are an honest signal in the first place. Base LLMs have weak introspective access to their own learned behaviors, but a small trained adapter can substantially improve self-report accuracy, even for deliberately hidden behaviors.
: Frontier basis — Shenoy et al., "Introspection Adapters: Training LLMs to Report Their Learned Behaviors," arXiv:2604.16812 — LoRA-based adapter achieves SOTA on AuditBench.
: Kill rule — If an audit of interspect's evidence sources shows calibration signal comes entirely from externally observable outcomes (test pass/fail, override accept/reject, human correction) and never from agent self-report, this doesn't apply — skip.

**Wire interlab's mutation-genealogy/counterfactual tracking into interspect as the holdout register's execution substrate**
: Rationale — The holdout-register item is listed as a standalone concept, but interlab already has genealogy/lineage tracking (mutation_genealogy, mutation_query) built for a different purpose. The cross-component bet: repurpose it as the engine that runs interspect's holdout evaluations — same shape of problem (did this change actually help, held out from the metric that decided to keep it), different domain.
: Frontier basis — internal.
: Kill rule — If interlab's genealogy schema can't represent a "delegation decision" as a mutation node without significant schema surgery, or the two systems' feedback timescales are too mismatched (single-session vs cross-session), abandon and let the standalone holdout-register item proceed independently.

**Contrarian null-hypothesis test: does multi-agent coordination overhead net-improve Sylveste's actual task mix, or would single-strong-model execution beat it?**
: Rationale — Every item in the scan assumes orchestration is worth refining. None asks the prior question: for Sylveste's actual task mix, is orchestration overhead paying for itself at all vs routing to a single frontier-tier model end-to-end? This is the house "test null hypothesis first" doctrine applied to the orchestration layer itself.
: Frontier basis — "ChromaFlow: A Negative Ablation Study of Orchestration Overhead in Tool-Augmented Agent Evaluation," arXiv:2605.14102; "AdaptOrch: Task-Adaptive Multi-Agent Orchestration in the Era of LLM Performance Convergence," arXiv:2602.16873 — both argue orchestration value is task-dependent and shrinking as single-model capability converges.
: Kill rule — Pre-register: pick 10-15 completed Clavain sprint/campaign beads, re-run end-to-end on a single frontier model without dispatch, compare wall-clock, cost, and quality. If single-model matches or beats multi-agent dispatch on >60% of sampled tasks, that's a red flag; if multi-agent wins clearly, kill this line of inquiry and don't re-litigate.

---

### Layer: knowledge-cognition (22 possibilities: 16 scan + 6 critic)

| Title | Kind | Component | Evidence | Effort | Novelty |
|---|---|---|---|---|---|
| Adopt facet-level collaborative persona graphs (CoPersona) for Auraken cold-start | external-frontier-adopt | Auraken; lattice | moderate | spike-days | adapt |
| Apply PRISM's persona-routing accuracy tradeoff finding to interlens/Auraken lens selection | external-frontier-adopt | interlens; Auraken | moderate | spike-days | adapt |
| Adopt AdaKGC-style schema-drift-tolerant ingestion for lattice connectors | external-frontier-adopt | lattice (interweave) | weak | spike-days | adapt |
| Test MemTier's "three-layer invariance" null result against intermem's promotion pipeline | external-frontier-adopt | intermem | moderate | spike-days | adopt-known |
| Evaluate "Cognitive Tools" framing as an alternative to lens-selection-via-MCP-call | external-frontier-adopt | interlens; Auraken | speculative | spike-days | adapt |
| Instrument lattice's F7 gravity-well detector against real production query load | latent-backlog-formalize | lattice (interweave) | moderate | spike-days | adopt-known |
| Execute the already-scoped F6b flux-drive triage A/B (sylveste-g939) before any new ontology feature work | latent-backlog-formalize | lattice; interweave/persona-lens-ontology | strong | spike-days | adopt-known |
| Build the external lens-calibration pipeline (sylveste-2l1) with an explicit discovery-vs-refinement split | latent-backlog-formalize | Auraken | moderate | project-weeks | adapt |
| Resolve lens authoring-drift pairs (sylveste-05rf) as a semantic-versioning problem, not just a dedup problem | latent-backlog-formalize | Auraken; lattice | strong | spike-days | adopt-known |
| Net-new: use interspect's evidence corpus as ground truth for Auraken lens effectiveness | net-new-direction | Auraken; interspect; lattice | speculative | research-program | genuinely-novel |
| Net-new: anti-dependency-preserving engagement metric for a stateless, no-memory product | net-new-direction | Auraken | speculative | project-weeks | genuinely-novel |
| Net-new: differential lens-selection calibration across local vs. frontier serving tiers | net-new-direction | Auraken; interlens; interfer | speculative | project-weeks | genuinely-novel |
| Net-new: RouteProfile-style cold-start graph profiling for new lattice connector sources | net-new-direction | lattice (interweave) | speculative | spike-days | adapt |
| Formalize the "ontology is a catalog, not a source of truth" pattern as reusable connector-idempotency test suite | latent-backlog-formalize | lattice (interweave) | moderate | spike-days | adopt-known |
| Cross-reference the Metacognitive Probe's 5-dimensional calibration diagnostic against interspect/lens-effectiveness scoring | external-frontier-adopt | Auraken; interspect | weak | spike-days | adapt |
| Formalize intername/interfluence identity-consistency drift monitoring as a lattice-consumable signal | latent-backlog-formalize | intername; interfluence; lattice | weak | spike-days | adopt-known |
| Test whether SimpleMem-style entity-centric compression transfers to intermem's auto-memory scanning, inverted | external-frontier-adopt | intermem | moderate | spike-days | adapt |
| Null-test the graph/lens layer itself: does structured retrieval beat a naive baseline for Auraken/lattice's actual query mix? | net-new-direction | lattice, interlens, Auraken | moderate | spike-days | adapt |
| Adopt temporal fact-invalidation (t_valid/t_invalid) for intermem instead of overwrite-or-append semantics | external-frontier-adopt | intermem | strong | project-weeks | adopt-known |
| Reframe lattice ingestion as an "active ontology queried live at inference time" rather than a batch ingestion pipeline | net-new-direction | lattice | weak | project-weeks | adapt |
| Audit whether interlens/Auraken persona-effectiveness evaluations are cue-sensitive artifacts rather than stable signals | net-new-direction | interlens, Auraken, interspect | moderate | spike-days | adapt |
| Adopt a geometric/conditioning-mechanism framework for measuring what persists in Sylveste agent identity | external-frontier-adopt | intername, interfluence | weak | spike-days | adapt |
| Cross-wire lattice connector-idempotency tests with interlens authoring-drift versioning as one shared "is this actually new" primitive | net-new-direction | lattice, interlens | moderate | project-weeks | genuinely-novel |

#### Rationale / frontier basis / kill rules — knowledge-cognition

**Adopt facet-level collaborative persona graphs (CoPersona) for Auraken cold-start**
: Rationale — Auraken's cold-start tier (P1-1) has no way to seed a new user's lens-selection profile except generic defaults. CoPersona's facet-level signal borrowing from similar users' behavioral dimensions maps onto Auraken's existing lens_usage/effectiveness_score fields; Sylveste already has the substrate (291 lenses tagged with discipline/community_id) without new infra.
: Frontier basis — CoPersona: Collaborative Persona Graphs for Robust LLM Personalization, arXiv 2607.01485.
: Kill rule — Phase-1: on the existing 20-fixture parity corpus, simulate 5 synthetic cold-start users, measure lens top-3 agreement with facet-borrowing vs current generic-default. If improvement is <10pp, kill — the anti-dependency architecture may make cross-user borrowing feel invasive anyway, so the adoption bar should be high.

**Apply PRISM's persona-routing accuracy tradeoff finding to interlens/Auraken lens selection**
: Rationale — PRISM found expert-persona prompting improves alignment/engagement but can damage factual accuracy in a task/model-dependent way. Auraken's mechanism is persona-adjacent framing injected into another agent's reasoning — a direct, testable warning that some lens injections may feel more insightful while quietly degrading correctness.
: Frontier basis — Expert Personas Improve LLM Alignment but Damage Accuracy: Bootstrapping Intent-Based Persona Routing with PRISM, arXiv 2603.18507.
: Kill rule — Run the already-built F6a 30-diff held-out corpus with lens-injection ON vs OFF, scoring on a task with objective ground truth (e.g. code review P0/P1 detection). If accuracy delta is within noise (<3pp), the risk isn't present in Sylveste's usage pattern and the inquiry closes.

**Adopt AdaKGC-style schema-drift-tolerant ingestion for lattice connectors**
: Rationale — Lattice's catalog-of-catalogs principle means source-of-truth files evolve independently and connectors must tolerate schema drift without full re-ingestion. AdaKGC's Schema-Enriched Prefix Instruction + Schema-Constrained Dynamic Decoding is a ready template for making lattice's planned importers robust to upstream field additions/renames.
: Frontier basis — AdaKGC (schema drift adaptation via SPI/SDD), referenced in 2026 KG-construction literature scan.
: Kill rule — Instrument the three existing connectors to log schema-shape hashes on each harvest run for 30 days. If zero drift events occur, the adaptive-decoding investment solves a problem that doesn't exist yet — revisit only after an actual breaking-schema incident.

**Test MemTier's "three-layer invariance" null result against intermem's promotion pipeline**
: Rationale — MemTier's most interesting finding is a null result: neither RL-learned retrieval weights nor model scale moved benchmark performance, because BM25 retrieval was the binding constraint. intermem's confidence-scoring formula is a hand-tuned heuristic analogous to MemTier's initial fixed weights — a cheap warning to test before investing in a learned-weight upgrade.
: Frontier basis — MemTier: Tiered Memory Architecture and Retrieval Bottleneck Analysis, arXiv 2605.03675 — reports RL-adaptive weights "do not diverge," retrieval architecture (not weighting) is the binding constraint.
: Kill rule — Phase-1 measurement: audit intermem's false-promote/false-demote rate over the last 90 days. If citation-validity checking alone achieves <5% error, MemTier's lesson is confirmed pre-emptively — do not build a learned-weight layer.

**Evaluate "Cognitive Tools" framing as an alternative to lens-selection-via-MCP-call**
: Rationale — Eliciting Reasoning with Cognitive Tools treats structured reasoning primitives as callable tools within the model's own generation, rather than an external selector injecting a framing. interlens/Auraken currently do lens selection out-of-band (Haiku call → inject lens object); the cognitive-tools framing suggests the target model itself invokes a "lens" tool mid-reasoning — potentially cheaper and more responsive to mid-conversation pivots.
: Frontier basis — Eliciting Reasoning in Language Models with Cognitive Tools, arXiv 2506.12115.
: Kill rule — Prototype a single cognitive-tool-style lens-invocation function against 10 F6a held-out fixtures, compare token cost and top-3 lens agreement vs current Haiku-selector. If token cost is higher with no accuracy gain, kill — the current architecture is already near-optimal for Auraken's stateless/cheap-overlay constraint.

**Instrument lattice's F7 gravity-well detector against real production query load**
: Rationale — F4/F6/F7 (confidence, salience, gravity-well safeguards) are designed and likely implemented but there's no evidence they've been measured against a live corpus (only synthetic thresholds: >5% single-entity share, cap=3).
: Frontier basis — internal.
: Kill rule — Run gravity-well detection against the current production lattice DB. If no entity exceeds 5% concentration in practice, park the recalibration work and re-check after persona/lens ingestion lands the 1200+ lens/persona entries this was designed for.

**Execute the already-scoped F6b flux-drive triage A/B (sylveste-g939) before any new ontology feature work**
: Rationale — The highest-leverage latent-backlog item in the layer: the entire persona/lens ontology epic was justified by one measurable claim — that querying the graph produces a triage lift over filename-glob + tier heuristics. F6a (pre-registration + corpus) is done; F6b (backend swap + A/B + ship decision) is still open. Every other ontology investment is downstream of this number.
: Frontier basis — internal.
: Kill rule — Bead already has its kill rule baked in by design (F6a pre-registration + held-out corpus): run F6b's A/B. If triage lift is not measurably positive, the epic's founding premise is falsified — stop further lattice investment tied to flux-drive consumption and re-scope around whatever residual value survives independently.

**Build the external lens-calibration pipeline (sylveste-2l1) with an explicit discovery-vs-refinement split**
: Rationale — sylveste-2l1 is open and well-specified (daily_dilemmas anchor suite → Reddit-threaded coverage index → AITA near-miss density → Arctic Shift niche calibration) but unexecuted. The Forge Mode flux-review already found: "the system is a refinement engine, not a discovery engine." Falsifiable question: does external-dataset calibration surface lens gaps the internal corpus can't, or just relabel known gaps with more confidence?
: Frontier basis — internal (Forge Mode flux-review, 4/4 track convergence).
: Kill rule — Run only the anchor suite (daily_dilemmas) first. If lens coverage gaps substantially overlap (>70%) with gaps already known from the 454 near-miss pairs in the Forge Mode corpus, kill before running the more expensive tiers — external data is confirming, not discovering.

**Resolve lens authoring-drift pairs (sylveste-05rf) as a semantic-versioning problem, not just a dedup problem**
: Rationale — sylveste-05rf documents concrete cases (Systems Thinking vs N-Ply Thinking; Whale Fall vs Whale Fall Redux) where one lens's definition literally contains language from another. Lattice's `same-as`/`supersedes` relationship types are designed for exactly this but the bead is still open — the ontology has the vocabulary but no process has run it against known drift cases.
: Frontier basis — internal (F5.5 tie-break interview, sylveste-71nz.2).
: Kill rule — Apply the existing curator-promotion workflow to just the 2-3 documented pairs. If curator review confirms genuine subsumption in <1 day, this closes as routine curation — no broader lens-corpus drift audit is warranted unless the pilot surfaces >5 additional undocumented pairs.

**Net-new: use interspect's evidence corpus as ground truth for Auraken lens effectiveness (cross-plugin calibration loop)**
: Rationale — interspect already runs a live agent-performance calibration loop for flux-drive agents, and lattice already models fd-agents and Auraken lenses as cross-linked entities (`wields` relationship). Nobody has closed the loop the other direction: does interspect's real pass/fail evidence on fd-agent dispatches constitute an implicit effectiveness signal for the lenses those agents wield — orders of magnitude more data than Auraken's own conversational usage_count can accumulate alone.
: Frontier basis — internal — no external work found combining agent-dispatch outcome telemetry with persona/lens effectiveness scoring.
: Kill rule — Phase-1 (days): join lattice's `wields` edges against interspect's evidence table for ~660 fd-agents. If overlap is <20% (most dispatches don't route through lens-tagged personas), the cross-plugin signal is too sparse — kill before building a joint-scoring pipeline.

**Net-new: anti-dependency-preserving engagement metric for a stateless, no-memory product**
: Rationale — Auraken's stated philosophy explicitly rejects the attachment/engagement optimization loop every comparable product (Replika, Pi, Character.ai) is built around — it wants users to become independent, not attached. But "is this working" still needs a metric, and session length/return rate are exactly the attachment-coded metrics the philosophy rejects. An under-explored measurement-design problem unique to a product with an anti-engagement thesis and zero persistent user state.
: Frontier basis — internal — inverts the entire companion-agent research literature, confirmed absent from the 2026-06-22 companion-agent scoping doc's coverage map.
: Kill rule — Phase-1: draft 3 candidate proxy metrics computable from the existing stateless {lens, rationale, next_question} response object alone, check whether any correlates even weakly with qualitative session-quality ratings from existing E2E transcripts. If none show signal, park until Auraken has telemetry beyond the single JSON response.

**Net-new: differential lens-selection calibration across local vs. frontier serving tiers**
: Rationale — Sylveste uniquely runs both a live local-model serving stack (interfer) and a cognitive-profiling product currently pinned to specific hosted models. The Auraken cross-model voice-portability bead already suspects the SKILL.md voice-rubric doesn't transfer cleanly across models — this extends the question to lens-selection accuracy itself.
: Frontier basis — internal — combines sylveste-gaid (voice portability) with sylveste-s10 (small-local-model workload candidates) and the closed sylveste-myy7 RL-lens-selection research track.
: Kill rule — Phase-1: run the existing 20-fixture parity test against one representative local sub-10B model instead of Haiku. If top-3 lens agreement holds within the same tolerance used for the Haiku-vs-Go parity bar, there's no per-model calibration problem — kill the research direction and confirm local-model compatibility as a one-line deployment note.

**Net-new: RouteProfile-style cold-start graph profiling for new lattice connector sources**
: Rationale — RouteProfile builds LLM routing profiles under cold-start using only coarse public metadata rather than deep interaction history. Lattice faces an analogous cold-start problem every time a new connector is added: zero relationship history means salience/gravity-well scoring can't distinguish a genuinely novel low-degree entity from one that just hasn't accumulated edges yet.
: Frontier basis — RouteProfile: Graph-Based Profiling for Cold-Start LLM Routing, arXiv 2605.00180.
: Kill rule — Measure how many query-result rankings actually flip between "first harvest" and "steady state" (30 days post-ingestion) for a newly added connector. If rankings are already stable within the first few harvest cycles, there's no cold-start instability worth a profiling layer — kill.

**Formalize the "ontology is a catalog, not a source of truth" pattern as reusable connector-idempotency test suite**
: Rationale — The lattice reconciliation doc calls the catalog-of-catalogs principle a "load-bearing architectural commitment" but the repo shows per-connector tests rather than a documented, generalized idempotency/no-data-loss contract test every future connector must pass.
: Frontier basis — internal.
: Kill rule — Write the generalized contract test against the 3 existing connectors first. If all 3 pass trivially with no code changes, the invariant is already implicitly enforced by the shared `Connector` protocol — downgrade to a one-paragraph AGENTS.md addition rather than a test-suite investment.

**Cross-reference the Metacognitive Probe's 5-dimensional calibration diagnostic against interspect/lens-effectiveness scoring**
: Rationale — The Metacognitive Probe decomposes LLM confidence-correctness alignment into 5 behavioral diagnostics. Both Auraken's effectiveness_score/bridge_score and interspect's agent-routing confidence are single scalar calibration signals — a 5-dimensional decomposition could reveal whether either is conflating distinct failure modes (confidently wrong vs under-confidently right).
: Frontier basis — The Metacognitive Probe: Five Behavioural Calibration Diagnostics for LLMs, arXiv 2605.09844.
: Kill rule — Apply the probe's decomposition retrospectively to the existing F6a 30-diff held-out corpus results. If the decomposed dimensions are highly correlated with each other (a single scalar already captures >90% of variance), the added dimensionality isn't earning its complexity — kill before touching production scoring code.

**Formalize intername/interfluence identity-consistency drift monitoring as a lattice-consumable signal**
: Rationale — interfluence tracks per-context voice deltas and intername guarantees deterministic identity naming, but neither reports drift signals into lattice's Actor family, which already models agents/personas as first-class entities with lifecycle transitions (`transitions-to`, `supersedes`).
: Frontier basis — internal.
: Kill rule — Check whether any voice-profile in an active .interfluence/ directory has actually drifted materially in the last 90 days. If profiles are effectively static once authored, there's no drift signal worth wiring into lattice — kill.

**Test whether SimpleMem-style entity-centric compression transfers to intermem's auto-memory scanning, inverted**
: Rationale — assess-simplemem-context-compression.md correctly ruled SimpleMem out for Skaffen's session-compaction problem (wrong time horizon). But intermem's actual problem — synthesizing durable facts out of auto-memory markdown accumulated over weeks — is precisely SimpleMem's target regime, wrongly dismissed for the wrong consumer and never re-evaluated for the right one.
: Frontier basis — SimpleMem, arXiv 2601.02553 — previously assessed for Skaffen (wrong fit), not yet assessed for intermem (better fit).
: Kill rule — Compare SimpleMem's entity-novelty + redundancy-clustering scoring against intermem's existing confidence/decay heuristic on the actual MEMORY.md corpus. If SimpleMem's clustering doesn't merge any entries that intermem's fuzzy-dedup (difflib.SequenceMatcher) currently treats as distinct-but-related, the existing dedup is already doing SimpleMem's job at a fraction of the complexity — kill.

**Null-test the graph/lens layer itself: does structured retrieval beat a naive baseline for Auraken/lattice's actual query mix?**
: Rationale — Every existing item assumes the graph/persona/lens machinery is worth refining. None asks the prior question: on Sylveste's real query distribution, does graph-structured retrieval or lens-routing actually outperform a flat baseline? At least one documented case (LeanDojo ablation) found removing structure improved results, and "context rot" work shows added context can hurt past a point.
: Frontier basis — LeanDojo dependency-graph ablation showing retrieval removal improved premise selection (arXiv 2510.23637); Context Rot (Chroma, 2026); GRAG ablation literature.
: Kill rule — If flat/no-lens baseline is within 2 points of the graph-routed condition on the held-out query set, do not invest further in lens/graph sophistication for that surface — redirect to the baseline and revisit only if the query distribution shifts materially.

**Adopt temporal fact-invalidation (t_valid/t_invalid) for intermem instead of overwrite-or-append semantics**
: Rationale — intermem's promotion pipeline currently treats memory as compress-then-promote, not as a temporally versioned fact store. Zep/Graphiti's core bet — every fact carries a validity interval, contradictions invalidate rather than overwrite, history is queryable — is benchmarked (LongMemEval, LoCoMo), not just a vendor claim. Session handoffs and MEMORY.md entries routinely get superseded but there's no first-class "this fact was true until X" representation.
: Frontier basis — Zep/Graphiti temporal knowledge graph architecture, LongMemEval benchmark results (Zep 63.8% vs Mem0 49.0%), LoCoMo 80.32%/189ms.
: Kill rule — If a lightweight "supersedes" pointer between memory entries (no full temporal-interval model) resolves the observed staleness incidents in a 2-week trial, do not build the full Graphiti-style bitemporal schema — the simpler mechanism wins by default.

**Reframe lattice ingestion as an "active ontology queried live at inference time" rather than a batch ingestion pipeline**
: Rationale — The AdaKGC item targets surviving schema drift once it's already happened at write time. The "active ontology" framing inverts this: don't pre-load a static schema at all; have agents query live, drift-scored metadata at read time. A different failure mode than ingestion robustness — whether lattice's consumers are trusting a frozen snapshot instead of asking "is this still true" at query time.
: Frontier basis — "Active Ontology: The 2026 Default for Enterprise AI" (Atlan, 2026); "Ontology Drift: Why Your Knowledge Graph Is Slowly Going Wrong" (Medium/Graph Praxis, 2026).
: Kill rule — If lattice's actual drift rate (measured, not assumed) is under ~5%/month for production connector sources, the live-query overhead isn't justified — stick with periodic batch re-ingestion and revisit only if drift rate exceeds that threshold.

**Audit whether interlens/Auraken persona-effectiveness evaluations are cue-sensitive artifacts rather than stable signals**
: Rationale — Several existing items (interspect-as-ground-truth, differential serving-tier calibration, RouteProfile cold-start) all assume persona/lens evaluation produces a stable, comparable signal. A 2026 finding shows different sociodemographic cue framings for the same persona yield materially different, sometimes contradictory conclusions about LLM personalization and bias — a measurement-validity check underneath the whole calibration program.
: Frontier basis — "One Persona, Many Cues, Different Results: How Sociodemographic Cues Impact LLM Personalization" (arXiv 2601.18572); "Screen Before You Interpret: A Portable Validity Protocol for Benchmark-Based LLM Confidence Signals" (arXiv 2604.17714).
: Kill rule — If lens-effectiveness scores are stable (within noise) across 3+ paraphrasings of the same persona/lens definition, the metric is validated as-is — proceed with existing calibration items unmodified.

**Adopt a geometric/conditioning-mechanism framework for measuring what persists in Sylveste agent identity, replacing ad hoc drift signals**
: Rationale — The intername/interfluence drift-monitoring item doesn't specify what's actually being measured or how. A 2026 paper proposes a geometric framework quantifying what persists in agent identity across turns/sessions as a conditioning-mechanism property, distinct from ad hoc drift heuristics.
: Frontier basis — "Measuring What Persists: Conditioning Mechanisms and a Geometric Framework for AI Agent Identity" (arXiv 2606.21843).
: Kill rule — If a simple cosine-distance-over-time baseline on existing intername/interfluence embeddings already correlates with manually-labeled drift incidents, the geometric framework doesn't earn its complexity — ship the simple baseline instead.

**Cross-wire lattice connector-idempotency tests with interlens authoring-drift versioning as one shared "is this actually new" primitive**
: Rationale — Two existing items independently attack the same underlying problem from opposite pipeline ends: connector-idempotency ("did this source actually change") and lens authoring-drift-as-semver ("is this lens actually a new version or a duplicate"). Both are instances of one unsolved primitive: given two artifacts, decide same/updated/genuinely-new.
: Frontier basis — internal.
: Kill rule — If the connector-idempotency and lens-semver problems need genuinely different equivalence definitions (structural diff for facts vs semantic diff for prose lenses) after a 2-day spike comparing both spec drafts, keep them separate rather than forcing a shared abstraction.
