### Findings Index
- P0 | GS-1 | "Resolver Integration" | Audit-trail unconformity: resolver no-op short-circuit erases microrouter layer when decision matches B3 calibration output
- P1 | GS-2 | "Design Doc + Paper Deep-Read" | Decision-space cardinality mismatch: binary local/cloud collapses 5-way C1–C5 complexity tiers into 2 horizons
- P1 | GS-3 | "Eval Harness" | Shadow-soak diversity: ≥1 sprint gate does not require multi-regime coverage (research vs. implementation vs. mixed)
- P2 | GS-4 | "Build Labeled Dataset" | Source-area provenance absent: training dataset mixes 4+ source types without per-source tagging for confusion back-trace
- P2 | GS-5 | "Eval Harness" | Eval workloads are proximal-heavy (LCB v6 cached + replayed bead-history are both near-distribution); distal distribution test absent
- IMP | GS-I1 | "Resolver Integration" | Always log microrouter decision to shadow log even when decision is identical to B3 — distinguish active no-op from skipped layer
- IMP | GS-I2 | "Design Doc + Paper Deep-Read" | If binary decision space is chosen for v0, add a second field `complexity_tier_hint` carrying the B2 tier so the resolver can reconstruct the full stratigraphy
Verdict: risky

### Summary
The microrouter's insertion between B2 complexity and overrides[agent] (bead .19.5) creates a stratigraphic unconformity: when the router's decision matches what B3 calibration would have produced anyway, the resolver may short-circuit without logging — making it impossible to determine from the audit trail whether the microrouter was active on any given decision. Additionally, the proposal's decision space options include "binary local/cloud," which would collapse the 5-way C1–C5 complexity tier system (routing.yaml lines 614-661) into two horizons, permanently destroying the interpretability of the routing record. The shadow-soak promotion gate ("≥1 sprint") counts time, not regime diversity — a sprint composed entirely of research tasks would certify a router that fails completely on implementation workloads.

### Issues Found

GS-1. P0: Audit-trail unconformity — microrouter decision can be invisible when it matches B3.

Bead .19.5 specifies the resolver failure mode: "Router model not loaded → mode auto-degrades to shadow (don't fail-closed)." It also specifies `shadow_log: ".clavain/interspect/microrouter-shadow.jsonl"`. The proposed resolver chain (bead .19.5) inserts microrouter between B2 and overrides[agent]. In the common case where the microrouter recommends "sonnet" for a task that B3 calibration also recommends "sonnet," a performance-conscious implementation will short-circuit — record nothing, proceed with the B3 result. The audit trail cannot distinguish "microrouter said sonnet" from "microrouter was skipped."

Concrete failure scenario: The router is promoted to enforce mode. Three weeks later, operators want to understand why a particular class of tasks is being routed to Haiku. They query the shadow log and find that 40% of decisions have no microrouter entry — because those decisions matched B3 and were silently passed through. The audit trail has an unconformity: the microrouter horizon is invisible wherever its grain size matched the layer below. Root-causing a routing regression becomes a multi-hour investigation.

Fix: In bead .19.5 schema, add `log_all_decisions: true` to the microrouter config block. Shadow log must record every decision including pass-through/no-op, with a `decision_type: "override" | "passthrough" | "skipped"` field. The overhead is a single JSONL append per subagent call — acceptable at 100ms timeout budget.

GS-2. P1: Binary decision space collapses 5-way complexity tier system.

Bead .19.1's decision space options include "2-way (local/cloud)." The existing routing.yaml defines 5 complexity tiers (C1–C5, lines 614–661) with distinct model mappings:
- C1/C2 → haiku / local:qwen3.6-35b-a3b-4bit
- C3 → inherit (cloud escalation per lines 750-752)
- C4/C5 → opus

A binary local/cloud router cannot distinguish "router wanted local because task is C1" from "router wanted local because task is C2 with light prompt but high file_count" from "router wanted local because task is a C3 that the model thinks it can handle." Post-hoc analysis of routing decisions will be unable to reconstruct which complexity regime drove each decision.

Concrete failure scenario: Router ships as binary. Interspect begins collecting microrouter-shadow logs. Six weeks later, operators notice a 12% increase in C3 escalations (cloud costs up). Investigation requires comparing shadow log entries against B2 complexity scores to reconstruct what should have happened. Because the binary router erased the tier signal, the analysis cannot determine whether the router is mis-classifying C1 as local-eligible or C3 as local-eligible — these look identical in the binary log.

Fix: If binary is chosen for v0, add `complexity_tier_hint: <B2_tier>` as a required field in every shadow log entry. This preserves the stratigraphy without requiring the router to produce 5 outputs. If the design bead chooses full-tier (5-way), this finding is resolved by default.

GS-3. P1: Shadow-soak promotion gate counts elapsed time, not workload regime diversity.

Bead .19.4 gate: "Shadow → enforce: ≥1 sprint of shadow-mode soak, no pass@1 regression vs. B3 baseline, ≥20% reroute rate." One sprint could be an all-research sprint (agents: repo-research-analyst, best-practices-researcher — all Haiku-eligible, all proximal to the router's training distribution). The router could achieve ≥20% reroute rate and zero pass@1 regression on such a sprint while failing completely on implementation sprints (agents: fd-correctness, fd-architecture — where C4/C5 complexity means Opus floors matter).

Concrete failure scenario: Router promotes to enforce during a documentation sprint. The first implementation sprint hits the enforce router. C4 architectural tasks that need Opus get routed to Sonnet (router trained mostly on research tasks). fd-correctness fires on 3 beads that fail quality gates. Rollback requires deleting the calibration file and re-running shadow for another sprint — losing 1-2 days.

Fix: In bead .19.4, change the shadow-soak gate from "≥1 sprint" to "≥1 sprint of each of: mixed-workload sprint (containing ≥3 agent categories), implementation-heavy sprint (≥40% fd-* agents from implementation category), research sprint." Add a `shadow_soak_diversity_report` to the promotion checklist showing phase distribution of decisions logged.

GS-4. P2: Training dataset lacks per-source provenance labels.

Bead .19.2 lists 4+ source types: routing-calibration.json, delegation-calibration.json, bead history (Dolt), interspect evidence files, sprint logs, session JSONLs. The output format is `(task_text, agent, phase, complexity_tier, model_used, passed, latency_ms, cost_proxy)` — no `source_type` field. When the router makes a misroute on a bead .19.4 eval workload, diagnosing "which source taught this bad routing" requires manually cross-referencing timestamps. Like sediment from multiple source rocks, the provenance is lost in the mixing.

GS-5. P2: Eval workloads skew proximal to training distribution.

Bead .19.4's three workloads: LCB v6 cached problems (code reasoning, similar to sprint implementation tasks), replayed bead-history (directly from training distribution), synthetic adversarial (tasks that "look easy but require deep reasoning"). The first two are proximal — close to the training source rocks. The synthetic adversarial set is distal in difficulty but still sourced from the same domain. There is no workload representing out-of-distribution task types (e.g., tasks from a new agent type not in the training corpus, tasks from a post-routing-change era). Distal eval would catch grain-size fining with transport distance.

### Improvements

GS-I1. Log all microrouter decisions including pass-through — add `decision_type: "override" | "passthrough" | "skipped"` to `.clavain/interspect/microrouter-shadow.jsonl` schema in bead .19.5.

GS-I2. If binary v0 is chosen in bead .19.1, add `b2_complexity_tier` to the shadow log entry so the full stratigraphy is reconstructable without requiring the router to output a tier.

GS-I3. Shadow-soak diversity gate — replace "≥1 sprint" with "≥1 sprint spanning ≥3 distinct sprint phases and ≥3 distinct agent categories" in bead .19.4 promotion criteria.

<!-- flux-drive:complete -->
