### Findings Index
- P1 | GRID-1 | "sylveste-s3z6.19.3 — Training Pipeline" | Training loss design deferred to bead 1 with no gate blocking bead 3 if cost-weighted loss is not chosen — pure cross-entropy loss is a valid bead 3 outcome
- P1 | GRID-2 | "sylveste-s3z6.19 — Epic / sylveste-s3z6.19.5 — Resolver" | B3 calibration freshness not a promotion prerequisite — router can be promoted to enforce with stale contingency reserve
- P1 | GRID-3 | "sylveste-s3z6.19.3 — Training Pipeline / sylveste-s3z6.19.1 — Design" | Local model tier labels (B5 tier_mappings) not specified as required label space — router may learn haiku/sonnet/opus-only, making local-fleet dispatch economically blind
- P2 | GRID-4 | "sylveste-s3z6.19 — Epic" | Shadow soak sprint selection criteria not specified — cherry-picked sprint with low microrouter-eligible call volume could clear the promotion gate
- P2 | GRID-5 | "sylveste-s3z6.19.5 — Resolver Integration" | model-not-loaded auto-degrade to shadow not distinguished from planned maintenance in logged state transitions
Verdict: needs-changes

### Summary

From an economic dispatch perspective, Track B6 has a well-structured optimization objective at the epic level — the ≥20% reroute rate target with no pass@1 regression maps directly to a security-constrained economic dispatch: reduce cost subject to a quality constraint. However, three findings reduce confidence that the dispatch will be economically correct: the cost-weighted loss design is deferred to bead 1 without a hard gate blocking bead 3 from using cross-entropy only, the B5 local model tiers are not specified as required training label outputs (so the router may never learn to dispatch to the local fleet), and the B3 contingency reserve freshness is not a prerequisite for promotion. A router promoted to enforce with stale B3 data and no local-tier dispatch knowledge is economically weaker than the current B3+B5 baseline it is supposed to improve.

### Issues Found

#### GRID-1. Training loss design deferred to bead 1 with no gate blocking bead 3 from using pure cross-entropy

**Severity**: P1
**Section**: sylveste-s3z6.19.3 — Training Pipeline (§ "Loss" and § "Depends on: design bead")
**Finding**: Bead 3's training spec states: "Loss: depends on design bead — likely cross-entropy over tier classes for v0, cost-weighted regret for v1." The "depends on design bead" dependency is correct, but the spec does not define a gate: "If the design bead chooses cross-entropy loss, this is acceptable for v0." The epic's Risks section explicitly calls out "Distillation collapses to 'always pick Sonnet' if loss is naive — mitigated by per-tier calibration and cost-weighted loss." The mitigation is cost-weighted loss, but bead 3 permits cross-entropy as a v0 choice without flagging this as the distillation-collapse risk condition. In economic dispatch terms: the optimization objective allows a formulation that ignores the cost term entirely (pure cross-entropy = maximize accuracy, not minimize cost), which will produce a schedule that minimizes visible error while maximizing cloud spend.

**Failure scenario**: Bead 1 completes. The design doc recommends "cross-entropy for v0 to establish a baseline, cost-weighted loss for v1." Bead 3 implements cross-entropy for v0. The corpus is 83% sonnet-routed. The router achieves 87% accuracy by predicting sonnet for everything. Bead 4 runs: router accuracy is 87% (clears ≥90% holdout gate? No — below threshold — actually this would fail the gate. But let's consider the variant: if the gate threshold is set at 85% based on bead 1's design doc recommendation, the router passes with 87% accuracy and 0% reroute rate). The ≥20% reroute rate gate is the only protection — but if both gates are evaluated as pass/fail independently, the accuracy gate passing could create pressure to proceed despite the reroute rate gate failing.

**Fix**: Add an explicit condition to bead 3: "If the design bead specifies cost-weighted loss, that loss implementation is REQUIRED for the training run to be considered complete. Using cross-entropy loss when cost-weighted loss was specified by the design doc constitutes a deviation and requires explicit approval before bead 3 can be closed." This is a one-sentence addition to bead 3's Done When criteria. Also add to the eval matrix (bead 4): the routing-distribution entropy metric described in BESTEXEC-2 serves double duty as a loss-type quality gate — if entropy is below the collapse threshold, bead 3 must be re-run with cost-weighted loss regardless of accuracy.

---

#### GRID-2. B3 calibration freshness not a promotion prerequisite — router can be promoted to enforce with stale contingency reserve

**Severity**: P1
**Section**: sylveste-s3z6.19 — Epic (§ "Success criteria") and sylveste-s3z6.19.5 — Resolver Integration (§ "Done when")
**Finding**: The epic's success criteria for shadow→enforce promotion include: ≥1 sprint shadow soak, ≥90% holdout accuracy, ≥20% reroute rate. None of these criteria include a check on the freshness of `.clavain/interspect/routing-calibration.json` (the B3 calibration file). The microrouter is designed to slot above B3 with B3 as the fallback. If routing-calibration.json has not been updated since the last interspect calibration run (which the epic notes occurred with 498 closed beads as the baseline), the B3 fallback is operating on data that may be significantly stale relative to the current sprint's agent distribution. In economic dispatch terms: the contingency reserve (B3) may have degraded capacity that was not measured before the new dispatch unit (B6) was committed.

**Failure scenario**: B6 is promoted to enforce. The microrouter operates correctly for 90% of calls. For the 10% that fall through to B3 (timeouts, endpoint unavailable), B3 uses routing-calibration.json. Unknown to the team, that file was last updated 3 months ago — before a significant shift in agent mix (interflux agents added, several agents promoted to higher tiers). B3 routes some of those fallthrough calls to haiku for agents that now require sonnet based on recent performance data. Pass@1 regression is observed in enforce mode, but the attribution analysis points to B3 fallthrough calls, not the microrouter itself. The team investigates the microrouter rather than the B3 calibration data, wasting a sprint.

**Fix**: Add a promotion prerequisite to the epic's success criteria: "Before shadow→enforce promotion, verify that `.clavain/interspect/routing-calibration.json` was updated within the current sprint (or within the last N sprints — set in design bead). If the file is stale, run `/interspect:calibrate` before promoting." This is a one-bullet addition to the success criteria and a one-line check in the promotion script.

---

#### GRID-3. Local model tier labels (B5 tier_mappings) not specified as required router output labels

**Severity**: P1
**Section**: sylveste-s3z6.19.1 — Design (§ "Decision space") and sylveste-s3z6.19.3 — Training Pipeline (§ "Base model selection")
**Finding**: The design bead asks: "Decision space: 2-way (local/cloud) vs. 3-way (haiku/sonnet/opus) vs. full-tier (haiku/sonnet/opus/local-C2/local-C3) vs. binary 'delegate-to-codex y/n'." This is the right question. But the training pipeline in bead 3 does not require that the answer include local model tiers. The existing routing stack in routing.yaml:738-741 defines four local model tiers (qwen3.5-9b-4bit as tier 1, qwen3.6-35b-a3b-4bit as tier 2, nemotron-30b-a3b-8bit as tier 2, qwen3.5-122b-a10b-4bit as tier 3). If the router is trained with only {haiku, sonnet, opus} as output classes, it cannot dispatch to the local fleet — it can only decide between cloud tiers. This makes the router blind to the most economically significant routing decision for the M5 Max hardware (cloud vs. local), which is explicitly listed as one of the two non-cost wins in the epic (privacy routing requires local dispatch).

**Failure scenario**: Bead 1 design doc recommends "3-way: haiku/sonnet/opus" as the decision space for v0 simplicity. Bead 3 trains accordingly. The router reaches enforce mode. Privacy-tagged tasks are handled by the privacy extension (bead 6), which bypasses the router's tier output and constrains to local. But non-privacy tasks have no mechanism for the router to prefer local:qwen3.6-35b-a3b-4bit over sonnet, even for C2 tasks where the local model has demonstrated ≥equal quality (per the LCB v6 matrix: 40.0% pass@1 at 5× speed for Qwen3.6 vs. cloud). The router systematically prefers cloud for all non-privacy tasks because cloud tiers are the only output classes it was trained on.

**Fix**: Add to bead 1's decision space item: "The decision space MUST include local-model tiers as first-class options, not just as a privacy-routing bypass. At minimum, the label set should include {haiku, sonnet, opus, local:C1, local:C2}. The training data from bead 2 must include labels for local model completions from the interspect verdict data (B5 shadow logs show local routing decisions)." This is the most consequential architectural decision in the design space — the router's ability to dispatch to the local fleet is what makes B6 different from B2 complexity routing.

---

#### GRID-4. Shadow soak sprint selection criteria not specified

**Severity**: P2
**Section**: sylveste-s3z6.19 — Epic (§ "Risks" and promotion criteria)
**Finding**: The ≥1 sprint shadow soak requirement does not specify how the sprint is selected. A sprint dominated by `brainstorm` and `shipping` phases has very few `executing`-phase subagent calls (where the microrouter fires). A sprint dominated by `executing` phase with 200+ subagent calls provides orders of magnitude more signal. Using a low-volume sprint as the evidence base for promotion is equivalent to conducting a grid dispatch shadow simulation on a day with minimal load — the simulation validates the dispatch algorithm on the easy case, not the load conditions that would reveal its failure modes.

**Failure scenario**: B6 enters shadow mode on a Friday. The team is in a reflect/done sprint. Monday begins a new sprint with 8 executing-phase calls (brainstorm work only). Tuesday a sprint completes (shipping phase). The ≥1 sprint gate is cleared on Tuesday. The shadow log has 8 entries. The promotion decision is presented. The evidence base is 8 calls.

**Fix**: Add sprint selection criteria to the promotion prerequisites: "The qualifying shadow-soak sprint must include ≥N router-eligible calls (recommended: 100, set in design bead) and must be representative of a normal executing-phase sprint (not a pure brainstorm/shipping sprint)." Add a check in the promotion script: before computing the reroute rate, verify that the shadow log entry count from the qualifying sprint meets the floor.

---

#### GRID-5. model-not-loaded auto-degrade to shadow not distinguished from planned maintenance in logged state transitions

**Severity**: P2
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Failure modes to handle": "Router model not loaded → mode auto-degrades to shadow")
**Finding**: The spec states that when the router model is not loaded (e.g., the adapter weights file is missing or the interfer server hasn't loaded the adapter), the mode auto-degrades to shadow rather than staying in enforce. This is correct behavior. However, the spec does not require that this degradation be logged with enough detail to distinguish "model not loaded because it was never loaded (fresh install)" from "model not loaded because the file was deleted (rollback)" from "model not loaded because interfer crashed (incident)." In grid dispatch terms, this is the reserve margin being consumed for reasons that are not classified — planned outage (maintenance) vs. forced outage (failure) have different economic implications and require different responses.

**Failure scenario**: Mode is `enforce`. interfer crashes due to an OOM event (Qwen3.6-35B-A3B at 18GB + Qwen3.5-3B-Instruct at 2GB exhausts the ~128GB budget under other memory pressure). The mode auto-degrades to shadow. The log entry (if it exists) says "model not loaded." The on-call engineer sees "mode degraded to shadow" but cannot determine if this is the expected behavior or an unexpected OOM event without inspecting the interfer process logs separately. The shadow mode persists until interfer is restarted, but there is no alert and no escalation path.

**Fix**: Add a log entry schema to bead 5 for the model-not-loaded degradation event: `{event: "mode-auto-degrade", from: "enforce", to: "shadow", reason: "model-not-loaded", model_path: "<path>", interfer_status: "running|crashed|not-started"}`. The `interfer_status` field distinguishes planned (not-started) from unplanned (crashed) degradation and enables automated alerting when `interfer_status=crashed`.

---

### Improvements

1. **Eval matrix contingency row**: Add a named row to the eval matrix in bead 4 for the contingency case: "microrouter down, B3 active, B5 shadow." This row measures the degraded-mode quality floor — what is the observed pass@1 when B6 is unavailable and B3+B5 handle all calls. This is the baseline quality the production system must not fall below.

2. **Cost component audit in design doc**: Bead 1's design doc should include an explicit list of all cost components that the training loss must capture: (a) cloud API cost per tier (proxy: token count × tier price), (b) latency per tier (measured: p95 per tier in routing.yaml), (c) privacy routing compliance (binary: did local tasks route locally), (d) quality preservation (pass@1). If any component is deliberately excluded from the loss, document the tradeoff.

3. **B3 calibration as fallback quality baseline**: Include in the eval matrix a measurement of "B3 calibration quality on the holdout set" as the lower bound for acceptable microrouter performance. The ≥90% holdout accuracy gate is relative to the calibrated baseline, but the calibrated baseline quality is not itself reported. If B3 has degraded since the last calibration run, the ≥90% relative accuracy gate may be clearing a lower absolute bar than intended.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 3, P2: 2)
SUMMARY: Three P1 gaps in loss design gate, B3 contingency freshness requirement, and local-tier label space would produce a router that is economically suboptimal or operates on a degraded fallback without detection. The local-tier label gap is the most strategically significant: a router that cannot dispatch to the local fleet cannot realize the latency and privacy wins that motivated Track B6.
---
<!-- flux-drive:complete -->
