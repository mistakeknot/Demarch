### Findings Index
- P1 | BESTEXEC-1 | "sylveste-s3z6.19.5 — Resolver Integration" | Shadow log schema omits reason-code field — timed-out and ineligible-filtered calls are indistinguishable from normal B3 fallthroughs
- P1 | BESTEXEC-2 | "sylveste-s3z6.19.4 — Eval Harness" | Routing distribution collapse not a named failure mode in eval matrix — distillation-collapse is flagged as a risk but has no dedicated detector
- P1 | BESTEXEC-3 | "sylveste-s3z6.19 — Epic" | Shadow-to-enforce promotion gate specifies calendar duration (≥1 sprint) but no minimum shadow-log entry count or minimum reroute rate
- P2 | BESTEXEC-4 | "sylveste-s3z6.19.5 — Resolver Integration" | Ineligible-agent filter placement unspecified — spec does not state whether filter runs before or after the HTTP call to the router endpoint
- P2 | BESTEXEC-5 | "sylveste-s3z6.19.4 — Eval Harness" | Per-call audit trail schema not specified — holdout eval output format does not enumerate required fields for best-execution attribution
Verdict: needs-changes

### Summary

From a smart order routing audit perspective, the Track B6 microrouter proposal has strong structural bones — the mode=off|shadow|enforce gating pattern mirrors proven SOR promotion workflows, and the comparator matrix in bead 4 directly parallels venue-performance matrices used for best-execution compliance. However, three gaps create the same class of post-incident analysis failures that plague SOR deployments: the shadow log schema does not define a `reason` field distinguishing timed-out from ineligible-filtered from normally-decided calls, the eval harness has no named detector for routing distribution collapse (the always-sonnet distillation failure), and the shadow-to-enforce gate is a duration requirement not an evidence requirement. A shadow soak that completes one sprint with zero eligible calls currently satisfies the gate as written.

### Issues Found

#### BESTEXEC-1. Shadow log schema omits reason-code field — timed-out and ineligible-filtered calls indistinguishable from normal B3 fallthroughs

**Severity**: P1
**Section**: sylveste-s3z6.19.5 — Resolver Integration (shadow_log: ".clavain/interspect/microrouter-shadow.jsonl")
**Finding**: The proposed shadow log schema in bead 5 records routing decisions but does not specify a `reason` field with values distinguishing: `decided` (router ran and returned a tier), `timed-out` (timeout_ms exceeded, fell through to B3), `agent-ineligible` (fd-safety/fd-correctness filtered before call), and `endpoint-unreachable` (HTTP call failed, fell through to B3). Without a reason field, a shadow soak period where 30% of calls timed out will report a reroute rate computed only over decided calls, inflating the apparent router accuracy. In SOR systems, this is the equivalent of a best-execution report that excludes all executions that missed the NBBO — the compliance audit fails.

**Failure scenario**: During the shadow soak (≥1 sprint), interfer serves the router endpoint on localhost:8421. If the endpoint is cold-starting or under memory pressure from the Qwen3.6-35B-A3B model (which uses the bulk of M5 Max RAM per routing.yaml:739), some router calls will time out. If timeout events are not written to the shadow log with a distinct reason code, they are simply absent from the log. The soak's reroute rate is computed over the entries that exist — which excludes all timeouts — producing an inflated estimate of router performance. When the decision to promote to enforce is reviewed, the shadow log appears to show zero timeout events and a healthy reroute rate, both of which may be artifacts of logging gaps rather than router quality.

**Fix**: Add a required `reason` field to the shadow_log schema in bead 5. Enumerate the four values (decided, timed-out, agent-ineligible, endpoint-unreachable) and add a test that verifies each reason code appears in the log under its triggering condition. One-line schema addition: `reason: "decided" | "timed-out" | "agent-ineligible" | "endpoint-unreachable"`.

---

#### BESTEXEC-2. Routing distribution collapse not a named failure mode in eval matrix — always-sonnet distillation failure has no dedicated detector

**Severity**: P1
**Section**: sylveste-s3z6.19.4 — Eval Harness (§ "Routing distribution" metric)
**Finding**: The epic correctly identifies distillation collapse ("router becomes always-pick-Sonnet") as a named risk in the Risks section, and bead 3 names cost-weighted loss as the mitigation. However, bead 4's eval harness does not specify a named failure mode or threshold for routing distribution collapse. The "Routing distribution: % to each tier; flag if collapse to one tier" line in the eval spec is a metric definition, not a failure detector — it does not specify what % threshold constitutes collapse, what the eval summary reports when collapse is detected, or what action is required if the matrix run ends with collapse detected. In a SOR audit, "all flow to one venue" is a named failure condition that blocks promotion, not a footnote in the metrics table.

**Failure scenario**: The microrouter training completes. The cost-weighted loss was implemented correctly, but the training corpus was 88% sonnet-routed tasks (consistent with the ≥90% sonnet baseline described in the epic motivation). The router learns a near-optimal policy of "always sonnet" with 88% accuracy. Bead 4 runs the eval matrix. The "Routing distribution" column shows 98% sonnet. Because there is no defined collapse threshold and no named failure condition, the eval report notes "high sonnet routing share" and continues to the promotion gate check. The ≥90% holdout accuracy gate clears (98% of calls routed correctly to sonnet). The ≥20% reroute gate fails — but if the reroute gate threshold is soft-coded as a success criterion rather than a hard gate, the shadow-to-enforce promotion proceeds. The router ships to enforce mode and provides zero economic benefit.

**Fix**: Add a named failure condition to bead 4's eval harness: "If routing-distribution entropy < 0.5 bits (equivalent to ≥88% of calls to any single tier), emit `COLLAPSE DETECTED` in the matrix summary and block promotion regardless of other gate metrics." The threshold should be set in bead 1's design doc to be consistent with the expected reroute rate (≥20% reroute implies ≥0.72 bits entropy at minimum).

---

#### BESTEXEC-3. Shadow-to-enforce promotion gate specifies calendar duration, not evidence requirements

**Severity**: P1
**Section**: sylveste-s3z6.19 — Epic (§ "Success criteria" and § "Risks — Router becomes new failure mode")
**Finding**: The promotion gate for shadow→enforce states "≥ 1 sprint of shadow-mode soak" as a prerequisite, alongside the ≥90% holdout accuracy and ≥20% reroute rate metrics from bead 4. Calendar duration is a necessary but insufficient promotion criterion — it does not guarantee that the shadow log contains enough entries to support a statistically meaningful reroute rate estimate. A sprint that consists entirely of brainstorm-phase or shipping-phase work (where the microrouter only fires during executing phase) could complete with fewer than 20 router-eligible calls logged. The ≥20% reroute rate computed over 20 calls has a 95% CI of ±19%, meaning the gate could be cleared or failed by pure sampling noise.

**Failure scenario**: The first sprint after shadow-mode activation is a release sprint: most work is `shipping` and `reflect` phase. The resolver chain for these phases does not enter the microrouter (bead 5's schema adds microrouter above B3 "during /sprint execute phase"). The sprint completes. The shadow log has 8 router-eligible calls from a brief executing-phase window. The reroute rate is 25% (2/8). The 95% confidence interval is [3%, 65%]. The ≥1 sprint gate is cleared by calendar. The ≥20% reroute rate gate clears on the point estimate. Promotion to enforce proceeds on the basis of 8 calls.

**Fix**: Add a minimum entry floor to the promotion gate: "shadow log must contain ≥N router-eligible calls (suggested: 100) before the reroute rate metric is computed." N should be set in bead 1's design doc based on the desired statistical power for detecting a 20% reroute rate at 80% confidence. Add a bead 5 requirement: the promotion script must read the shadow log entry count and refuse promotion if below the floor.

---

#### BESTEXEC-4. Ineligible-agent filter placement unspecified — filter may run after HTTP call to router endpoint

**Severity**: P2
**Section**: sylveste-s3z6.19.5 — Resolver Integration (§ "Resolver chain change" and `ineligible_agents:` schema)
**Finding**: The proposed resolver chain in bead 5 inserts microrouter "between complexity (B2) and overrides[agent]" but does not specify whether the `ineligible_agents` check (fd-safety, fd-correctness) is performed before or after the HTTP call to `http://localhost:8421/route`. In SOR systems, instrument-level hard eligibility filters must execute before the routing algorithm runs — not after — to avoid consuming latency budget on calls that will be filtered regardless. If the filter runs after the HTTP call returns, every fd-safety call during a sprint incurs 50-100ms of router latency before the filter discards the result and applies the safety floor.

**Failure scenario**: `mode: enforce`. A sprint has 40 fd-safety calls (typical for a flux-drive review sprint). If the ineligible check fires after the HTTP call, each of the 40 calls waits up to 100ms for the router before the result is discarded. Total wasted latency: up to 4 seconds per sprint, compounded across the duration of the soak period. This is not a correctness issue (the filter still applies), but it is a measurable performance regression for the agents most sensitive to latency (safety and correctness reviews run sequentially in the resolver chain).

**Fix**: Specify in bead 5's resolver spec that `ineligible_agents` check fires as the FIRST step of the microrouter resolver layer, before the HTTP call is initiated. Add a test: verify that a call for an ineligible agent does not produce an HTTP request to the router endpoint (mock the endpoint and assert zero calls for fd-safety).

---

#### BESTEXEC-5. Per-call audit trail schema not specified — holdout eval output does not enumerate required fields for pass@1 attribution

**Severity**: P2
**Section**: sylveste-s3z6.19.4 — Eval Harness (§ "Output")
**Finding**: Bead 4 specifies that the eval harness outputs to `interverse/interfer/benchmarks/microrouter_v0_matrix/` in JSONL format (mirroring LCB v6 layout) and a narrative findings doc, but does not specify the per-call schema for the JSONL records. For best-execution attribution — being able to say "this pass@1 failure was caused by routing this task to haiku when the router predicted haiku would pass" — the per-call record must include at minimum: `(call_id, agent_name, router_prediction, actual_tier_used, task_passed, router_latency_ms, fallthrough_reason)`. Without a specified schema, the harness implementation in bead 4 may produce output that cannot answer the post-hoc attribution question.

**Failure scenario**: The eval matrix runs. Several tasks fail in `microrouter-enforce` mode that passed in the `none` (baseline) comparator. The diff is attributed to microrouter routing decisions. Investigation requires knowing which calls were routed to haiku vs. sonnet, but the JSONL schema only records `(task_id, comparator, passed)`. The attribution analysis cannot be performed without re-running the eval, which takes hours. The promotion decision is delayed.

**Fix**: Add a required per-call JSONL schema to bead 4's output spec: at minimum `call_id`, `agent_name`, `router_prediction`, `actual_tier_used`, `task_passed`, `router_latency_ms`, `fallthrough_reason`. Specify that the harness must write one record per subagent call (not one record per task), since a single task may involve multiple subagent calls.

---

### Improvements

1. **Shadow log sampling rate**: For very high-volume sprints, consider writing a sampling flag to the shadow log schema (e.g., `sampled: bool`) to distinguish complete logs from sampled logs. This prevents a future sampling optimization from silently degrading the soak evidence quality.

2. **Promotion script automation**: Bead 5 documents the promotion gate requirements but does not specify a promotion script. Consider adding a `bd promote-microrouter` command (or similar) that reads the shadow log, computes entry count and reroute rate, checks against the gate thresholds, and either approves or blocks promotion with a printout of the evidence. This makes the gate machine-readable rather than a manual checklist.

3. **SOR-style venue performance report**: The eval matrix in bead 4 measures overall reroute rate and pass@1. Consider adding a per-tier "venue performance" breakdown: for calls routed to haiku, sonnet, and each local model tier, show the pass@1 rate. This is the direct analog of per-venue fill quality in SOR and lets you identify which tier is underperforming rather than just seeing an aggregate degradation.

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 3, P2: 2)
SUMMARY: Three P1 gaps in shadow log observability, collapse detection, and promotion gate evidence requirements would make post-incident analysis impossible and could allow promotion to enforce on insufficient evidence. Two P2 issues in filter placement and per-call schema are correctness-adjacent performance and attribution concerns.
---
<!-- flux-drive:complete -->
