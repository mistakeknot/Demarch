---
artifact_type: review-synthesis
method: flux-review
target: "/Users/sma/projects/Sylveste/docs/research/flux-review/microrouter-track-b6/INPUT.md"
target_description: "Track B6 microrouter epic + 7 children — small-model router proposal extending Clavain's 5-track routing stack"
tracks: 4
tracks_completed: 3
track_a_agents: [fd-routing-cascade-design, fd-lora-distillation-pipeline, fd-eval-methodology-holdout, fd-production-rollout-safety, fd-config-resolver-architecture]
track_b_agents: [fd-trading-router-bestexec, fd-triage-acuity-routing, fd-dispatch-economic-grid, fd-ss7-cascade-routing]
track_c_agents: [fd-gongfu-cha-cascade-discernment, fd-glacial-sediment-cascade-sorting, fd-ifa-divination-verifier-corpus, fd-yaki-ire-temper-promotion-gates]
track_d_agents: [fd-khipukamayuq-paired-audit, fd-fulani-garso-shadow-soak, fd-curare-titration-feedback]
track_d_status: "timed out — agents designed but not run; absorbed into B/C runs partially"
date: 2026-05-01
---

# Microrouter Track B6 — Multi-Track Flux-Review Synthesis

## Critical Findings (P0/P1)

The review surfaced 12 distinct P0-class issues across the three completed tracks (de-duplicated from 14 raw P0 findings). Each is a genuine blocker: the proposal cannot ship to shadow without resolving them. They cluster into four themes — **safety-floor integrity**, **circular calibration**, **rollout invisibility**, and **architectural facts the bead bodies got wrong**.

### P0-A: Safety-floor bypass via the resolver insertion point (3 tracks)

**Source agents**: `fd-routing-cascade-design` (A), `fd-triage-acuity-routing` (B), `fd-yaki-ire-temper-promotion-gates` (C). Convergence score 3/3.

The proposal places the microrouter resolver layer *above* `overrides[agent]` in the chain, but `subagents.overrides` (`routing.yaml:540-544`) is where the fd-safety / fd-correctness sonnet floors live. The defense is an `ineligible_agents` list inside the `microrouter:` section — but that list duplicates safety state with no convergence check, uses bare names while the existing overrides use qualified namespaces (`interflux:review:fd-safety`), and is the only thing standing between a learned router and a silent safety-floor violation.

Three independent disciplines (cascade theory, hospital triage, Japanese sword tempering) all surfaced the same defect from different angles: cascade-design saw it as a chain-order error, triage-acuity saw it as a missing pre-call hard gate, yaki-ire saw it as a clay-coating asymmetry where the static ineligible list cannot honor dynamic safety floors.

**Fix**: Move the microrouter resolver layer *below* `overrides[agent]`, then fd-safety/fd-correctness exit at the override step before B6 is consulted. Make `ineligible_agents` a defense-in-depth layer derived at config-load time from `agent-roles.yaml` `min_model >= sonnet`, not a hand-maintained second list. Add the `_microrouter_validate_response` subroutine that does pre-call eligibility and post-call response validation against the agent's allowed tier set. **Requires**: bead-body edit on `.19.5` plus code change in `lib-routing.sh`.

### P0-B: Circular calibration — same model family judges labels and anchors holdout (1 track, but P0×2)

**Source agent**: `fd-gongfu-cha-cascade-discernment` (C). Convergence score 1/3 (a single-track find, but the agent flagged it as two stacked P0s).

`.19.3` augments missing labels with GPT-5.5/Opus, and the epic's success criterion (`≥ 90% agreement with calibrated baseline`) is anchored to `routing-calibration.json`, which was constructed from interspect verdicts where Opus/Sonnet was both the executing model and the implicit pass/fail judge. The router is therefore calibrating against itself: a model that learns "what Opus would have recommended" and is graded on agreement with "what Opus actually did" is not detecting an independent signal — it is learning to imitate the evaluator.

This is the kind of finding only a distance-3 distant-domain agent catches. The Track A specialists noted "judge bias" (`fd-lora-distillation-pipeline` P1) but framed it as a class-imbalance issue, not a structural circularity. The gongfu cha lens — where the apprentice cannot be graded by his own teacher posing as an external examiner — names it directly.

**Fix**: Use a different model family (Gemini 2.5 or local Qwen3.6-35B consensus) as the augmentation judge. Measure holdout agreement against observed downstream pass@1 outcomes (actual task results), not against the judge family's prior recommendations. **Requires**: bead-body edit on `.19.3` and `.19.4`, plus epic success-criteria revision.

### P0-C: Calibration feedback temporal leakage (1 track)

**Source agent**: `fd-eval-methodology-holdout` (A). Convergence 1/3.

`routing-calibration.json` is the *training signal* (verdict outcomes feed it) AND a *running artifact* (it updates after the holdout cut date). Judge augmentation in `.19.3` consulting the live file injects post-cutoff signal into training. The "by-time holdout (last 2 weeks)" protects against random leakage but not this calibration-loop leakage.

**Fix**: Define a "calibration freeze date" matching the holdout cut. Snapshot `routing-calibration.json` at that date; pin all training/judge/eval reads to the snapshot. Add a SHA hash check across phases. **Requires**: bead-body edit on `.19.2` and `.19.3`.

### P0-D: Replayed bead-history is leakage by construction (1 track)

**Source agent**: `fd-eval-methodology-holdout` (A). Convergence 1/3.

The "replayed bead-history tasks from holdout split" eval workload (INPUT.md:282) replays tasks whose verdicts were *the source of the labels*. A 3B classifier with rank-16 LoRA will memorize task-text → tier mappings during training; the holdout sees those same mappings with later timestamps. Holdout accuracy looks stellar, production tasks (genuinely novel) look worse.

**Fix**: Add a fourth eval workload `held-out-agents` — exclude all tasks from 2-3 specific agents during training, evaluate as if they were new agents. **Requires**: bead-body edit on `.19.4`.

### P0-E: Holdout target ≥ 0.85 satisfied by majority-class collapse (1 track)

**Source agent**: `fd-lora-distillation-pipeline` (A). Convergence 1/3.

If the training corpus is ~85% Sonnet (plausible given `phases.executing.model: sonnet` and safety overrides), a model that predicts "sonnet" always trivially clears the 0.85 gate, ships to shadow with 0% reroute rate, and never advances to enforce. The risk section names this risk; the gate doesn't catch it.

**Fix**: Replace single-aggregate-accuracy gate with a vector — per-tier recall ≥ 0.60 AND aggregate accuracy ≥ 0.85. Promote the per-tier confusion matrix to a first-class gating artifact. **Requires**: bead-body edit on `.19.3` "Done when".

### P0-F: Endpoint port collision with B5 interfer server (1 track)

**Source agent**: `fd-config-resolver-architecture` (A). Convergence 1/3.

Confirmed by code: `interverse/interfer/server/__main__.py:22` defaults to port 8421; B5 `local_models.endpoint` is `http://localhost:8421`. The proposed B6 `localhost:8421/route` shares the port. If "same server, two paths" is intended, the interfer server modification is unscoped; if "different servers" is intended, the port collision is a deployment failure.

**Fix**: Move B6 to a different port (e.g., 8422) for v0. Re-evaluate when there's a real reason to colocate. **Requires**: bead-body edit on `.19.5`.

### P0-G: "Bump routing-overrides.schema.json" targets the wrong schema (1 track)

**Source agent**: `fd-config-resolver-architecture` (A). Convergence 1/3.

That file (124 lines, read in this review) is the flux-drive interspect-overrides schema with `pattern: ^fd-[a-z][a-z0-9-]*$` and `action: exclude|propose`. It has nothing to do with routing.yaml validation. There is no JSON Schema validator for routing.yaml in the repo.

**Fix**: Drop the reference from `.19.5`. Either (a) accept that routing.yaml has no schema validator (documented explicitly) or (b) author `routing.schema.json` as separate work. **Requires**: bead-body edit on `.19.5`.

### P0-H: "Clavain Go resolver (path TBD)" — the resolver is Bash, not Go (1 track)

**Source agent**: `fd-config-resolver-architecture` (A). Convergence 1/3.

`os/Clavain/scripts/lib-routing.sh` is the actual resolver — 1475 lines of Bash with a YAML parser state machine and `routing_resolve_model_complex` called from hooks. The Go side consumes routing decisions but doesn't make them. `.19.5`'s implementation plan assumes the wrong language and module.

**Fix**: Update `.19.5` "Files touched" to: `lib-routing.sh` (new parser block, new runtime function, wiring), `routing.yaml` (new section), Bash tests for the resolver chain. **Requires**: bead-body edit on `.19.5`.

### P0-I: Auto-degrade `enforce → shadow` is invisible to the operator (1 track)

**Source agent**: `fd-production-rollout-safety` (A). Convergence 1/3 (cross-referenced from cascade-design's P2 angle).

INPUT.md:372 says "Router model not loaded → mode auto-degrades to shadow" with no log entry, metric, or alert. The configured `mode: enforce` stays "enforce" while the runtime acts as `shadow`. Production incident profile: silent fall-through for an entire sprint that gets attributed to enforce-mode B6 in calibration data, corrupting future analysis.

**Fix**: Don't mutate runtime mode. Keep configured mode; treat each call as fall-through-to-B3 when the model is unloaded; emit structured log + metric on every fall-through; alarm on sustained fall-through. **Requires**: bead-body edit on `.19.5`.

### P0-J: Rollback procedure reuses B3/B4 single-file pattern; B6 has 4 artifacts (1 track)

**Source agent**: `fd-production-rollout-safety` (A). Convergence 1/3.

B3/B4 rollback is "delete one JSON file." B6 rollback must address (a) `routing.yaml` mode toggle, (b) adapter checkpoint, (c) interfer endpoint at `localhost:8421/route`, (d) shadow log. The phrase "delete calibration file pattern, same as B3/B4" (INPUT.md:64) is actively misleading — an operator following that instruction will at most disable the YAML toggle, leaving the endpoint and shadow log running.

**Fix**: Write a B6 section in `os/Clavain/AGENTS.md` next to where B2-B5 are documented, with three rollback paths (quick / full / failed-promotion). **Requires**: new doc work plus bead-body edit on `.19.5`.

### P0-K: Audit-trail unconformity — no-op short-circuit erases microrouter layer (1 track)

**Source agent**: `fd-glacial-sediment-cascade-sorting` (C). Convergence 1/3.

When the router's decision matches what B3 would have produced anyway, a performance-conscious implementation will short-circuit. The shadow log cannot distinguish "microrouter said sonnet" from "microrouter was skipped." Three weeks into enforce, an operator investigating a routing regression finds 40% of decisions have no microrouter entry — the layer is invisible wherever its grain matched the layer below.

**Fix**: Add `log_all_decisions: true` to schema. Shadow log records every decision including pass-through, with `decision_type: "override" | "passthrough" | "skipped"`. **Requires**: bead-body edit on `.19.5`.

### P0-L: Privacy cloud leak — sensitive tasks fall through to cloud when router is down (1 track)

**Source agent**: `fd-yaki-ire-temper-promotion-gates` (C). Convergence 1/3.

`.19.6` extends privacy_routing so internal/sensitive tasks engage the microrouter even when global `mode=off`. But `.19.5`'s failure mode "Router endpoint unreachable → fall through to B3" doesn't differentiate privacy traffic. B3 calibration may recommend cloud for a task that should stay local. The privacy_routing block (lines 767-769) mandates local-only, but enforcement is by the privacy_routing section, not by the microrouter fallback path.

**Fix**: Add `privacy_fallback_model: "local:qwen3.6-35b-a3b-4bit"` to the schema. Privacy=sensitive AND endpoint-unreachable must fail-closed to a local model, never delegate to B3. **Requires**: bead-body edit on `.19.5` and `.19.6`.

---

The P1 layer (19 findings across the JSON, with several more in the Track A files) is dominated by gate-design defects, missing test cases for individually-named failure modes, and observability gaps. The most cross-cutting P1 patterns are summarized in the next section.

## Cross-Track Convergence

Findings that appeared independently in 2+ tracks — the highest-confidence signals.

### Convergence 3/3: Safety-floor / ineligible-agents pre-call enforcement

- Track A: `fd-routing-cascade-design` — chain insertion above `overrides[agent]` shadows safety floors; `ineligible_agents` duplicates safety state across two lists with no convergence check (P0).
- Track B: `fd-triage-acuity-routing` — `ineligible_agents` not specified as a pre-call resolver gate; garbage-response could route fd-safety to haiku (P0). `fd-trading-router-bestexec` — ineligible filter placement unspecified, may run after HTTP call wasting latency (P2).
- Track C: `fd-yaki-ire-temper-promotion-gates` — clay-coating asymmetry: ineligible list is hardcoded, can't honor dynamic safety floors defined elsewhere (P2).

Each frame is different (chain ordering, hospital triage protocol, smith's eye on hamon line) but the underlying defect is the same: the safety floor is not enforced as a *first* check, by *construction*, derivable from a single source of truth.

### Convergence 3/3: Promotion gate is calendar duration, not evidence

- Track A: `fd-production-rollout-safety` — "≥1 sprint shadow soak" treats sprints as fungible when their phase distributions vary by 5×; doc-update sprints don't exercise implementation routing (P1).
- Track B: `fd-trading-router-bestexec` — promotion gate has no minimum entry count or reroute rate floor (P1). `fd-dispatch-economic-grid` — sprint selection criteria not specified; cherry-picked sprint with low call volume could clear the gate (P2).
- Track C: `fd-glacial-sediment-cascade-sorting` — "≥1 sprint" gate doesn't require multi-regime coverage (research vs implementation vs mixed) (P1). `fd-yaki-ire-temper-promotion-gates` — promotion auto-proceeds on aggregate metrics with no operator review gate (P1).

The trading-systems and grid-dispatch lenses both name the statistical-power problem (8 calls is not evidence). The glacial-sedimentology lens names the regime-diversity problem (one sprint type doesn't cover the production distribution). The yaki-ire lens names the operator-judgment problem (stopwatch is not the smith's eye). All three together specify what the gate should be: ≥N entries (statistical power) AND multi-regime coverage (distributional power) AND operator sign-off (judgment).

### Convergence 2/3: Shadow log schema is unspecified

- Track A: `fd-production-rollout-safety` — schema unspecified, can't reconstruct eval metrics from production data (P1).
- Track B: `fd-trading-router-bestexec` — no `reason` field; timed-out, ineligible-filtered, and B3-fallthrough calls indistinguishable (P1). `fd-ss7-cascade-routing` — per-layer fallthrough reason not logged; can't distinguish microrouter-decided-sonnet from microrouter-timed-out-then-B3-decided-sonnet (P2).
- Track C: `fd-glacial-sediment-cascade-sorting` — same finding from the audit-trail-unconformity angle (P0). `fd-ifa-divination-verifier-corpus` — no verse-provenance fields (adapter hash, top-k training example IDs, raw logits) (P2).

This is genuinely the most under-specified piece of the proposal — INPUT.md just says `shadow_log: ".clavain/interspect/microrouter-shadow.jsonl"` and stops. Five agents independently flagged the gap, four naming specific schema additions. The convergent recommendation: add `reason` (decided/timed-out/agent-ineligible/endpoint-unreachable/garbage-response), `decision_type` (override/passthrough/skipped), `resolver_path` array (per-layer fallthrough trace), `adapter_checkpoint_hash`, and `routing_yaml_hash`.

### Convergence 2/3: Garbage-response failure mode unnamed

- Track A: `fd-routing-cascade-design` — "garbage response" is asserted but never specified — what counts as garbage? (P1).
- Track C: `fd-yaki-ire-temper-promotion-gates` — resolver does not enumerate behavior for malformed router output (P1).

This finding's cleanest formulation is from cascade-design: enumerate the garbage cases (malformed JSON, valid JSON with non-existent tier, valid JSON with tier-the-agent-is-ineligible-for, valid JSON with empty string), and write a `_microrouter_validate_response` subroutine with named test cases for each.

### Convergence 2/3: Local-tier label space missing from router output

- Track A: `fd-lora-distillation-pipeline` — implicit in P2 on Adapter checkpoint discovery and decision-space-output-labels-not-pinned-to-tier_mappings.
- Track B: `fd-dispatch-economic-grid` — local model tier labels not required in router label space; router cannot dispatch to local fleet (P1).

If the router is trained with only {haiku, sonnet, opus}, it can't realize the latency and privacy wins that motivated the epic. Bead `.19.1` decision space must include `{local:C1, local:C2}` as first-class output classes.

## Domain-Expert Insights (Track A)

Most valuable findings from adjacent-domain specialists, grouped by theme.

### Resolver chain integrity (cascade-design + config-resolver-architecture)

The two specialists who studied the actual `lib-routing.sh` resolver and the proposed chain insertion both reached the same conclusion: the proposal places the microrouter in the *middle* of the chain (between B2 and `overrides[agent]`), which is the position with the worst combinatorial-interaction surface. Every learned-routing literature reference cited (RouteLLM, FrugalGPT, Hybrid LLM) treats the small-model gate as either a first-stage filter or a terminal stage gated by all prior policy. The proposal as written treats it as a peer of complexity (B2) rather than a consumer of it.

The structural recommendation, articulated most clearly by `fd-config-resolver-architecture`, is to make the resolver chain a *YAML list* in routing.yaml that lib-routing.sh honors. The current state (chain order encoded in code with documentation in comments) means every "is the chain in the right order?" question becomes a code-review judgment call instead of a config diff.

### Training pipeline economics (lora-distillation-pipeline)

The most penetrating finding here is that the proposal borrows RouteLLM's cost-weighted regret loss from a regime that doesn't apply. RouteLLM assumes monetary cost differences between tiers drive routing; Sylveste's Codex OAuth is free at point of use, and the proposal itself (INPUT.md:33) says so. The two real wins are latency and privacy, which require different loss design: latency-weighted regret (continuous) and privacy-as-constraint (in the resolver, not the loss).

The pipeline-side prescription pairs with this: drop "cost-weighted regret" from `.19.3` and replace with "latency-weighted regret with privacy implemented as a constraint." Coordinate the privacy constraint with the resolver bead (it lives in code, not the model).

### Eval methodology rigor (eval-methodology-holdout)

Two structural defects beyond the calibration-leakage P0: (a) the `≥ 90% agreement with baseline` and `≥ 20% reroute rate` gates are mutually exclusive against the same baseline (reroute = 1 − agreement, by definition); the spec needs to name distinct baselines for each gate; (b) the oracle-upper-bound construction protocol is unspecified — *strong oracle* (sees outcomes) vs *weak oracle* (sees features + historical hit rates) vs *implicit oracle* (just B3 perfectly applied) give wildly different "headroom" numbers. A research engineer can pick the most flattering definition post-hoc unless the spec pins it down.

### Production-readiness gaps (production-rollout-safety)

Beyond the rollback runbook P0, the most actionable insight is that the eval-side promotion gates have no demotion counterpart. There is no metric that auto-triggers rollback during enforce. In a production routing system this is the difference between "we noticed the regression" and "the regression noticed itself." The minimum tripwire is the safety-floor violation case: if microrouter chooses `local:*` for an `fd-safety` or `fd-correctness` call, that's an immediate revert-to-off plus alarm.

## Parallel-Discipline Insights (Track B)

Operational patterns from orthogonal-domain agents.

### Smart Order Routing / best-execution audit (fd-trading-router-bestexec)

**Practice**: SOR systems require shadow log entries with explicit reason codes for every routing decision so post-incident best-execution audits can distinguish timed-out fills from ineligible-instrument filters from normal venue choices. Distribution collapse ("all flow to one venue") is a *named failure condition* that blocks promotion, not a footnote in the metrics table.

**Mapping**: Add `reason` field to shadow log (decided/timed-out/agent-ineligible/endpoint-unreachable). Add a named "COLLAPSE DETECTED" failure condition to the eval matrix when routing-distribution entropy < 0.5 bits (≥88% of calls to any single tier). Add a minimum entry floor (≥100 router-eligible calls) to the promotion gate.

### Hospital triage / acuity classification (fd-triage-acuity-routing)

**Practice**: In hospital triage system validation, each failure mode of the decision-support tool is a separate test scenario. "Triage tool down: nurse applies ESI protocol directly" is not the same test as "triage tool returns wrong acuity: nurse overrides." Grouping them under one "failure mode handling" test allows an implementation that only tests one of the three modes to pass the criteria as written.

**Mapping**: Replace the grouped `Resolver tests cover all failure modes` criterion in `.19.5` with three individually named tests: `TestMicrorouterEndpointUnreachable`, `TestMicrorouterTimeout` (wall-clock, not HTTP read timeout), `TestMicrorouterModelNotLoaded`. Add a fourth: `TestMicrorouterGarbageResponse` covering each garbage subtype.

### Electric grid economic dispatch / SCUC (fd-dispatch-economic-grid)

**Practice**: A grid dispatch shadow simulation conducted on a low-load day validates the algorithm on the easy case, not the load conditions that would reveal failure modes. Contingency reserve (the fallback) must be measured for *current* capacity before a new dispatch unit is committed — promoting B6 with stale B3 calibration data is committing a unit while the contingency reserve has unmeasured degradation.

**Mapping**: Make B3 calibration freshness a promotion prerequisite — verify `.clavain/interspect/routing-calibration.json` was updated within the last N sprints before promoting B6. Make local-model tiers first-class router output classes (the most consequential decision-space architectural choice — without it, B6 can't realize the latency/privacy wins).

### SS7 telephone signaling / intelligent network routing (fd-ss7-cascade-routing)

**Practice**: SS7 routing cascades require a hardcoded last-resort terminal below all configurable trunk groups — the call must never fail entirely. Per-hop CDRs (Call Detail Records) capture each signaling point traversed, not just the final route. Route-flap (a trunk alternating between available and unavailable within the routing decision window) is its own named failure mode.

**Mapping**: Add `HARDCODED_LAST_RESORT = "sonnet"` as a compile-time constant in lib-routing.sh below all YAML lookups; add `TestResolverChainExhaustionFallback`. Extend shadow log schema with `resolver_path` array recording per-layer traversal. Add a warmup probe pattern: don't route to the endpoint until it has responded to a recent warmup probe — eliminates cold-start flap. Specify `timeout_ms` measurement point as wall-clock at resolver entry, not HTTP read timeout.

## Structural Insights (Track C)

Novel patterns from distant-domain agents. The Track C agents were the most-anticipated payoff of running parallel tracks at increasing semantic distance, and three of the four delivered insights that no Track A or Track B agent surfaced.

### Chinese gongfu cha multi-infusion sensory protocol (fd-gongfu-cha-cascade-discernment)

**Domain**: Multi-stage tea brewing where each infusion reveals different qualities, and a master tea-taster (cha shi) must avoid the trap of grading an apprentice's brew using the apprentice's own teacher as the supposedly-external judge.

**Isomorphism**: The microrouter's training judge (GPT-5.5/Opus) is the same model family that produced the interspect verdicts that built `routing-calibration.json`, which is the baseline the router is graded against. Master-apprentice contamination — the apprentice is being graded by his own teacher pretending to be an external examiner.

**Concrete improvement**: Use a different model family (Gemini 2.5 or local Qwen3.6-35B consensus) as the augmentation judge. Measure holdout agreement against observed downstream pass@1 outcomes, not against the judge family's prior recommendations. Add a *sprint-aggregate regret metric* (`sprint_regret = Σ(oracle_quality − router_quality) / sprint_length`) and gate shadow→enforce on `sprint_regret < 5%`. Tag each training tuple with `routing_yaml_hash` so per-regime confusion analysis is possible — gongfu cha's "water source" matters because it changes the brew. The aftertaste channel (`hui gan`): pair each eval run with a 24-hour lookback for re-opens / follow-up correctness failures.

This is the highest-impact Track C insight and the single finding most clearly produced by semantic distance — Track A's eval methodologist saw judge bias as a class-balance issue and missed the structural circularity.

### Glacial-fluvial sedimentology / stratigraphic sorting (fd-glacial-sediment-cascade-sorting)

**Domain**: A river deposits sediments in stratigraphic layers; an unconformity is when a layer is missing or invisible because its grain size matched the layer above. Geologists reading the rock record cannot reconstruct what they cannot see.

**Isomorphism**: When the microrouter recommends "sonnet" for a task that B3 calibration also recommends "sonnet," a performance-conscious implementation will short-circuit and record nothing. The audit trail cannot distinguish "microrouter said sonnet" from "microrouter was skipped." Wherever the router's grain matched B3's, the layer is invisible.

**Concrete improvement**: Always log microrouter decisions including pass-through, with `decision_type: "override" | "passthrough" | "skipped"` field. If binary local/cloud is chosen for v0, add `complexity_tier_hint: <B2_tier>` to every shadow log entry — preserves the stratigraphy without requiring the router to produce 5 outputs. Replace "≥1 sprint" with "≥1 sprint spanning ≥3 distinct sprint phases and ≥3 distinct agent categories." Add per-source provenance tags to training data (4+ source types are mixed without per-source labels; debugging is a manual cross-reference exercise).

### Yoruba Ifá divination / 256-odu corpus / babalawo confirming-cast (fd-ifa-divination-verifier-corpus)

**Domain**: A babalawo divines using a 256-odu corpus; for any verdict, a *confirming cast* must be performed by a second babalawo who has not heard the first divination — independent judgment is the entire point. Before a session, the babalawo performs a sanity cast on a known question to verify the system is reading correctly.

**Isomorphism**: `.19.7`'s confidence-cascade verifier proposes a small model trained on the same labeled corpus (`.19.2`) by the same judge (GPT-5.5/Opus) as the microrouter. Two models trained on the same data by the same teacher fail in correlated ways. The microrouter has no startup self-test (iyere-bowl equivalent) — it could load weights correctly, pass health checks, and silently produce garbage on all inputs due to a corrupted adapter. The 5K example floor doesn't guarantee per-(agent, phase, tier) cell coverage — for rare cells the router will confidently invent verdicts.

**Concrete improvement**: If `.19.7` is pursued, require disjoint corpus (different time-slice), different judge family, and verifier features that exclude the routing decision itself. Add a startup probe block: known canonical cases with expected tiers; on probe failure degrade to shadow. Add per-cell coverage gate: minimum N=20 examples per (agent, complexity_tier) cell; resolver must implement empty-cell escalation to safe default when router confidence is below threshold.

### Japanese sword-tempering / Bizen-Osafune yaki-ire (fd-yaki-ire-temper-promotion-gates)

**Domain**: A swordsmith heat-treats a blade in clay coatings of differing thickness — the spine cools slowly (ductile), the edge cools fast (hard). Stopwatch alone is insufficient evidence; the smith must personally read the steel's color (hamon line) before stamping mei.

**Isomorphism**: The shadow→enforce gate is fully automated by aggregate metric thresholds (≥20% reroute rate, no pass@1 regression). A router that satisfies aggregate metrics while routing badly on a small set of high-stakes agents (fd-architecture at C5) will auto-promote. Privacy-routing extension is the *inner quench* — the differential clay coating that keeps sensitive tasks local. But the inner-quench currently shares endpoint liveness with the outer circuit: when the router endpoint is down and `privacy_override=always`, the resolver falls through to B3, which may route to cloud — silently violating the privacy floor.

**Concrete improvement**: Add operator-review checklist as a required shadow→enforce gate (routing distribution histogram, per-agent sample at C4/C5, no systematic tier collapse). Add `privacy_fallback_model: "local:qwen3.6-35b-a3b-4bit"` — privacy=sensitive AND endpoint-unreachable must fail-closed to local, never delegate to B3. Replace "delete calibration file pattern" with a documented 3-step rollback runbook (delete adapter, SIGTERM interfer or call /reload, verify B3 re-engages).

## Synthesis Assessment

### Overall quality of the proposal

The B6 epic is conceptually well-shaped — the mode=off|shadow|enforce pattern mirrors B2/B3/B4/B5, the LoRA distillation approach is sound, and the eval matrix axes are correct. But three classes of defect block readiness: (1) **factual errors** in `.19.5` (wrong schema target, wrong language, port collision), (2) **gate design** that cannot detect the failure modes the risk section names (collapse-resistant accuracy gate, calendar-only soak, mutually-exclusive agreement-vs-reroute), and (3) **observability gaps** (silent auto-degrade, unspecified shadow log schema, no per-layer audit trail). Verdict: **rework before shadow** — none of the defects block design discussion, but all twelve P0s must be resolved before code lands.

### Highest-leverage improvement

**Move the resolver chain from code-encoded order to a YAML list in routing.yaml that lib-routing.sh honors.** This single change would: (a) make the B6 chain insertion a config diff reviewable in one PR, (b) make safety-floor enforcement order auditable, (c) eliminate the "comment in YAML and code disagree about chain order" drift hazard, (d) allow future tracks (the planned `.19.7` verifier and beyond) to be structural insertions rather than code edits, (e) enable a single source of truth that a JSON Schema can later validate. Cost: a few hundred lines of refactor in lib-routing.sh. Benefit: every future track is a config change.

### Surprising finding

**The circular calibration P0 from `fd-gongfu-cha-cascade-discernment` is the single finding no Track A specialist surfaced and no Track B parallel-discipline agent surfaced either.** The Track A LoRA pipeline reviewer noted "judge bias" but framed it as a class-imbalance amplifier. The Track A eval methodologist noted "calibration feedback temporal leakage" but framed it as a holdout-cut-date issue. Neither named the structural circularity: that the model family being used to fill missing labels is the same model family that produced the verdicts in `routing-calibration.json` that anchor the success criterion. The gongfu cha master-apprentice frame names it directly. This is the textbook payoff of running parallel tracks at semantic distance — distant-domain agents catch class-of-error blind spots that adjacent-domain expertise rationalizes away.

### Semantic distance value

**Track C contributed insights qualitatively different from Track A**, not restatements. Specifically: gongfu cha (master-apprentice circular calibration), glacial sedimentology (audit-trail unconformity from no-op short-circuits), Ifá (confirming-cast independence requirements for `.19.7`, startup self-test, per-cell coverage gate), and yaki-ire (privacy inner-quench fail-closed requirement, operator smith's-eye gate) all surfaced findings absent from Track A. Three of those four are distinct P0s. The one Track C finding that *did* converge with Tracks A and B (safety-floor / ineligible-agents pre-call enforcement) reframed the problem productively — yaki-ire's "clay-coating asymmetry" frame names the static-vs-dynamic safety-floor mismatch more sharply than triage-acuity's pre-call-gate frame or cascade-design's chain-order frame.

The lesson: at the design-review stage of a moderately complex system (routing cascades, multi-track promotion, distillation pipelines), Track C agents pay for themselves. The operating cost was 4 distant-domain Sonnet runs (one timed out as Track D); the payoff is at least 2 distinct P0s that would have shipped.

### Process Issues

**Track D timeout**: Three agents were designed but never executed — `fd-khipukamayuq-paired-audit` (Inca paired-audit accounting), `fd-fulani-garso-shadow-soak` (Fulani cattle-knot growth tracking), `fd-curare-titration-feedback` (Amazonian curare dose-response titration). Tracks B and C absorbed two of these into their concurrent runs (peer-findings.jsonl shows cross-track awareness), but the third — curare-titration-feedback, which would have specifically targeted the dose-titration analogy for shadow→enforce promotion — was the most clearly missed. The promotion-gate cluster (3/3 convergence) might have been deeper with a fourth Track C agent on titration explicitly. Coverage impact: minor for P0 surfacing (cross-track convergence already captured the highest-confidence findings), moderate for the promotion-gate detail layer.

**14 auto-created beads from Tracks B and C without explicit user permission**: The Tracks B/C run created beads for each finding without asking. These need user-driven triage rather than autonomous closure. Listing them with one-line summaries:

| Bead ID | Severity | Title | Triage recommendation |
|---|---|---|---|
| Sylveste-jm4 | P0 | ineligible_agents pre-call placement unspecified — safety floor bypass path exists | **MERGE** into `s3z6.19.5` body edit (P0-A above) — duplicates Track A's cascade-design P0 |
| Sylveste-emv | P0 | Circular calibration — judge and baseline from same model family | **KEEP** as new bead under `s3z6.19` — Track-C-only finding (P0-B), not in any existing child |
| Sylveste-a5u | P0 | Audit-trail unconformity — microrouter no-op short-circuit erases resolver layer | **MERGE** into `s3z6.19.5` body edit (P0-K above) — same root cause as shadow-log-schema cluster |
| Sylveste-906 | P0 | Privacy inner-quench — sensitive tasks can fall through to cloud when router is down | **MERGE** into `s3z6.19.6` body edit (P0-L above) — directly belongs in the privacy-extension bead |
| Sylveste-7pq | P1 | Resolver chain terminal not proven reachable — no hardcoded last-resort constant | **MERGE** into `s3z6.19.5` body edit — defensive-programming addition |
| Sylveste-b1e | P1 | Route flap — 100ms timeout enables incoherent routing from cold-start variance | **MERGE** into `s3z6.19.5` body edit — warmup-probe + cold-start handling |
| Sylveste-v3b | P1 | Loss design unblocked — no gate prevents bead 3 from using pure cross-entropy | **MERGE** into `s3z6.19.3` body edit — adds gate condition to existing bead |
| Sylveste-2lh | P1 | Local model tier labels absent from router label space — local-fleet dispatch blind | **MERGE** into `s3z6.19.1` body edit — decision-space architecture choice |
| Sylveste-j6t | P1 | Simultaneous failure combinations (timeout + stale B3) not tested | **MERGE** into `s3z6.19.5` body edit — adds test cases |
| Sylveste-w6j | P1 | B3 calibration freshness not a promotion prerequisite | **KEEP** as new bead under `s3z6.19` — promotion-script work, cross-cuts `.19.5` and `.19.4` |
| Sylveste-gxl | P1 | Shadow log schema gap — no decision_type/reason-code field | **KEEP** as new bead under `s3z6.19.5` — substantial schema authoring (multiple converging requirements) |
| Sylveste-t0g | P1 | Shadow-soak gate is calendar not evidence — no entry floor or workload diversity | **MERGE** into `s3z6.19.4` body edit — promotion-gate revision (Convergence 3/3 finding) |
| Sylveste-96p | P1 | By-time holdout straddles routing regime change (2026-04-29 C2 promotion) | **MERGE** into `s3z6.19.2` body edit — holdout-cut protocol |
| Sylveste-d3r | P1 | Per-cell coverage gap — 5K total examples, no empty-cell escalation | **MERGE** into `s3z6.19.2` body edit — coverage-report requirement |

Recommended approach: **merge 11 of 14 into existing s3z6.19.* children body edits; keep 3 as standalone new beads (emv, w6j, gxl).** None should be closed without addressing — these are real P0/P1 findings that the existing children's bodies don't currently cover. The user should review and approve this triage before any bead lifecycle changes.

**Output directory split**: Track A wrote to `/Users/sma/projects/Sylveste/docs/research/flux-drive/INPUT/`; Tracks B and C wrote to a sibling timestamped directory `/Users/sma/projects/Sylveste/docs/research/flux-drive/INPUT-20260501T2239/`. This made synthesis fragile — there is no single landing zone for "all findings from this review." Recommendation for future flux-review runs: use a single timestamped directory for all tracks, write a small `flux-review.json` index at the top level naming the review's input target, the agents launched, and the per-track output files. The current synthesis directory `docs/research/flux-review/microrouter-track-b6/` is the right home for the synthesis artifact but didn't receive the per-agent files.

## Recommended Next Steps

Ranked by leverage. Each step is concrete (file path or bead ID).

1. **Edit the four highest-error bead bodies first** — bead `s3z6.19.5` (port collision, schema-bump target, Bash-vs-Go, chain-order, ineligible-agents pre-call, garbage-response taxonomy, shadow-log schema, hardcoded last resort, warmup probe, auto-degrade visibility, rollback runbook) is the dominant target with at least 7 P0/P1 findings concentrated in it. Then `s3z6.19.3` (per-tier recall gates, latency-not-cost-weighted loss, judge protocol, cross-entropy gate). Then `s3z6.19.2` (calibration freeze date, by-time-cut protocol, per-cell coverage). Then `s3z6.19.4` (workload stratification, oracle construction, sprint-regret metric, operator review gate). Estimated: a 2-hour disciplined editing pass through the four bead bodies. **Output**: edited bead descriptions in beads DB.

2. **Reorder the resolver chain** to put microrouter *below* `overrides[agent]` (P0-A). One-line change to the proposed chain in `.19.5` plus a corresponding two-line change to `lib-routing.sh`. Eliminates the safety-floor bypass risk by construction. **File**: `os/Clavain/scripts/lib-routing.sh` plus `.19.5` body.

3. **Resolve the circular calibration (P0-B) before any training run**. Switch judge family from GPT-5.5/Opus to Gemini 2.5 OR local Qwen3.6-35B consensus. Re-anchor the `≥ 90% agreement` success criterion against observed downstream pass@1 outcomes, not against the judge family's prior recommendations. **File**: epic body of `s3z6.19` (success criteria) plus `.19.3` (judge protocol). **New work**: validate Gemini API access and quota before committing.

4. **Triage the 14 auto-created beads** per the table above — 11 merge, 3 keep. Get user sign-off before closing any. **Tool**: `bd` CLI; preserve the user's veto on irreversible bead lifecycle changes.

5. **Author `routing.schema.json`** as a follow-up bead under `s3z6.19` covering all six tracks (B1-B6). The current proposal references the wrong schema (P0-G); the absence of any routing.yaml validator is a long-standing gap that B6 is a good time to close. Estimated: 1 day. **File**: new `os/Clavain/config/routing.schema.json` plus CI integration.

6. **Promote chain order to a YAML list in routing.yaml** that lib-routing.sh honors (the highest-leverage improvement, named in two Track A specialists' findings). Cost: a few hundred lines of refactor. Benefit: every future track is a config change. **File**: `os/Clavain/scripts/lib-routing.sh` plus `routing.yaml` schema. **New bead**: candidate for new sibling under `s3z6.19` or peer to it.

7. **Write the rollback runbook** in `os/Clavain/AGENTS.md` covering the four B6 artifacts (config mode, adapter checkpoint, interfer endpoint, shadow log) with three rollback paths (quick, full, failed-promotion). Replace INPUT.md:64's "rollback documented" with "rollback runbook merged at AGENTS.md#b6-microrouter." **File**: `os/Clavain/AGENTS.md`.

8. **Specify the shadow log schema** (Convergence 2/3, named explicitly by `Sylveste-gxl`). Required fields: `task_id`, `agent`, `phase`, `complexity_tier`, `router_decision`, `actual_model_used`, `passed`, `latency_router_ms`, `latency_total_ms`, `reason` (decided/timed-out/agent-ineligible/endpoint-unreachable/garbage-response), `decision_type` (override/passthrough/skipped), `resolver_path` array, `adapter_checkpoint_hash`, `routing_yaml_hash`, `version`. **File**: `.19.5` body. **Test**: a `replay-from-shadow-log` mode in the eval harness that reads production shadow logs and recomputes matrix metrics — makes shadow soak self-validating.

9. **Add startup-probe and per-cell coverage gates** (Track C: Ifá). Probe: 2-4 known canonical tasks with expected tier, run on first request after load, on failure degrade to shadow. Coverage: minimum N=20 examples per (agent, complexity_tier) cell; resolver must implement empty-cell escalation to safe default when router confidence is below threshold. **Files**: `.19.2` body (coverage report), `.19.5` body (startup probe schema).

10. **Decide on the local-tier label space** in `.19.1`'s decision-space choice. The Track A + Track B convergence makes this clear: the router must include `{local:C1, local:C2}` as first-class output classes, otherwise B6 cannot realize the latency/privacy wins that motivated the epic. **File**: `.19.1` design-bead body.

After these ten, the remaining P1 layer is concentrated in eval-harness rigor (workload-per-stratification, sprint-regret metric, oracle construction protocol, operator-review gate) and individual test-case naming (each failure mode gets a named test, not a grouped one). Those are mechanical fixes once the structural issues above are resolved.
