<!-- flux-drive:complete -->
# fd-eval-methodology-holdout — Microrouter Track B6 Evaluation Methodology Review

**Persona**: ML evaluation methodologist with offline-online evaluation experience for production ranking and routing systems.
**Scope**: bead `.19.4` (eval harness) and the parts of `.19.2` that affect holdout integrity. Anti-overlap with cascade design, LoRA pipeline, rollout safety, schema (covered by sibling agents).

## Findings Index

| # | Severity | Title |
|---|----------|-------|
| 1 | **P0** | Calibration feedback loop is the training signal AND a holdout-period artifact — temporal leakage path |
| 2 | **P0** | "Replayed bead-history tasks" is leakage by construction — same tasks were the labels' source |
| 3 | **P1** | ≥ 90% agreement gate (INPUT.md:62) and ≥ 20% reroute gate are mutually exclusive given baseline distribution |
| 4 | **P1** | Three workloads aggregated into single matrix metric obscures per-distribution failures |
| 5 | **P1** | Oracle-upper-bound construction protocol is unspecified — what features does it see? |
| 6 | **P2** | "Holdout is by-time (last 2 weeks) not random" is necessary but insufficient for leakage prevention |
| 7 | **P2** | pass@1 is measured per call; no protocol for tasks where the same prompt was retried |
| 8 | **P3** | "Synthetic adversarial set" is an undefined target — author can construct it after seeing test results |

## Verdict

**REWORK BEFORE TRAINING.** Two P0 leakage paths invalidate the holdout. The eval harness as specified will produce optimistic point estimates that the production rollout cannot match. The single most important pre-training change is to define the holdout-construction protocol *and* the calibration-file freeze protocol *before* dataset construction begins. Without this, the eval matrix outputs cannot be trusted.

## Summary

Bead `.19.4` defines a 4-comparator matrix (`none`, `microrouter-shadow`, `microrouter-enforce`, `oracle-upper-bound`) crossed with three workloads (LCB v6, replayed bead-history, synthetic adversarial). The intent is sound. The execution as specified has two structural leakage paths and one combinatorial gate-design error that would be catastrophic in production:

1. **Calibration-file leakage.** `routing-calibration.json` is written by interspect from verdict outcomes. The microrouter is trained on those same outcomes. If the calibration file is updated *during the holdout window*, training-time signals contaminate the test split. The current spec doesn't freeze the calibration file at the holdout cut date.
2. **Bead-history leakage.** The "replayed bead-history tasks from holdout split" workload (INPUT.md:282) replays tasks whose verdicts were *the source of the labels*. This is the same data; running it as an eval workload measures memorization, not generalization.
3. **Gate incoherence.** The promotion criterion "≥ 90% agreement with calibrated baseline" (INPUT.md:62) and "≥ 20% reroute rate" (INPUT.md:300) are mutually exclusive in any reasonable distribution. They cannot both be true simultaneously.

## Issues Found

### P0 — Calibration feedback loop creates temporal leakage through training labels

The system architecture has this loop:

```
flux-drive runs → interspect records verdicts → calibrate command computes hit rates →
  routing-calibration.json updated → calibration mode applies it → next sprint runs →
  verdicts recorded → ...
```

The microrouter trains on `(task_text, agent, phase, model_used, passed)` tuples (`.19.2`, INPUT.md:157). The `passed` field comes from interspect verdicts. Those same verdicts feed `routing-calibration.json`. If, during the holdout window, the calibration file is updated *and* judge augmentation in `.19.3` consults the calibration file (e.g., "current calibration says agent X performs 0.67 on Sonnet — adjust judge prompt accordingly"), the holdout test split contains signal that was unavailable at the start of training.

The proposal's "by-time holdout (last 2 weeks)" (INPUT.md:183) protects against *random* leakage but not against this *temporal* leakage path, because the calibration file is a *running average* — its state at any moment incorporates information from after the holdout cut date.

**Concrete remedy:**
1. Define a "calibration freeze date" in `.19.2` that matches the holdout cut date.
2. Snapshot `routing-calibration.json` at that date and pin training to the snapshot. Any judge augmentation, any `_calibration_field` lookup during training, any feature engineering that consults calibration must use the snapshot, not the live file.
3. Add to `.19.4` "Done when": "Calibration file snapshot hash matches across training, judge, and eval phases." A simple SHA check.
4. Coordinate with rollout-safety sibling: shadow-mode soak after training will see the *live* calibration file, which is the desired behavior — that's online evaluation, not offline. The freeze applies only to training/eval.

### P0 — "Replayed bead-history tasks" is the same data the labels came from

INPUT.md:282: `Replayed bead-history tasks from holdout split — realistic distribution`. This is the holdout split of the bead-history corpus. But the bead-history corpus *is* `(task_text, agent, phase, model_used, passed)` (`.19.2`, INPUT.md:157) — the same tuples that were the source of training labels.

The fact that the holdout is by-time doesn't fix this if the *task texts* are similar across time (which they are — repeated chores, doc updates, the same agent prompts called many times). A 3B classifier with rank-16 LoRA will memorize task-text → tier mappings during training; the holdout sees those same mappings with later timestamps. Holdout accuracy will look stellar. Production tasks (genuinely novel) will look worse.

This is the central reason routing literature usually evaluates on *out-of-distribution* tasks (e.g., training on one benchmark, evaluating on another). The proposal does not have this property.

**Concrete remedy:** Add a fourth eval workload: `held-out-agents`. Take 2-3 agents that have ≥ 50 tasks in the corpus (e.g., `fd-architecture`, `fd-quality`) and *exclude all their tasks from training*. Evaluate on them as if they were new agents. This measures how well the router generalizes to agents whose behavior wasn't seen at train time. This is a much harder bar than the proposed bead-history-replay, and a much more honest one.

The eval harness should report all four workloads separately (cf. P1 below).

### P1 — ≥ 90% agreement and ≥ 20% reroute rate are mutually exclusive

INPUT.md:62: `≥ 90% agreement with calibrated baseline on holdout`.
INPUT.md:300: `Shadow → enforce: ... ≥ 20% reroute rate`.

If "reroute" means "router picks a different tier than the baseline would," then by definition reroute rate = 1 - agreement rate. The two gates require, simultaneously:

- Agreement ≥ 90% (reroute ≤ 10%), AND
- Reroute ≥ 20%

These are mathematically contradictory. The router cannot satisfy both gates against the same baseline.

The likely intended distinction is:

- "Agreement" measured against B3 calibration *signal* (which agent should run on which tier).
- "Reroute" measured against B1 default policy (`phases.executing.model: sonnet`), which is what production actually uses today since calibration is in enforce mode.

If that's the read, the spec should *say so* explicitly. Even then, the gates are nontrivial — a router that agrees with calibration 90% of the time and reroutes from defaults 20% of the time is mostly mirroring calibration's existing reroutes. That's a fine outcome but it means the router is replacing calibration, not adding new value, and the proposal's stated motivation ("a learned router can decide haiku vs. sonnet vs. local-Qwen3.6-35B-A3B per call", INPUT.md:31) is overpromised.

**Concrete remedy:**
1. Rewrite both gates against named baselines: `agreement_with_B3 ≥ 0.90 AND reroute_from_B1_default ≥ 0.20`.
2. Add a third metric: `unique_decisions = decisions where router != B1 AND router != B3` — calls where B6 is providing genuinely novel routing. If this is < 5% of calls, the router is just B3 in a different shape and should be rejected on cost-benefit grounds (the LoRA serving cost vs. the calibration JSON cost).
3. Coordinate with cascade-design sibling on the chain order — if microrouter ends up *below* `overrides[agent]` per their P0 fix, then "agreement with calibration" only matters for the subset of calls that aren't safety-floored.

### P1 — Three workloads aggregated into single matrix metric obscures per-distribution failures

The eval matrix axes (INPUT.md:271-273) cross `router_variant × policy × workload`. The output (INPUT.md:294, "JSONL + summary") implies aggregation. If the harness reports a single "router accuracy" and "pass@1" across the union of LCB v6 + bead-history + synthetic adversarial, two failure modes are invisible:

1. **Workload-distribution mismatch.** LCB v6 is structured competitive code, bead-history is ops-heavy ad-hoc tasks, synthetic adversarial is hand-crafted hard cases. A router that excels on LCB v6 (where Sonnet-vs-Opus is a real choice) and fails on bead-history (where Haiku-vs-Sonnet is the live decision) can pass an aggregate gate while being useless for the actual production traffic.
2. **Promotion-gate gaming.** The shadow→enforce gates (`≥ 20% reroute rate`, no pass@1 regression) measured on the union are dominated by whichever workload has the highest call count. The proposal doesn't define call counts per workload, so the gate's behavior is unspecified.

**Concrete remedy:**
1. Report the matrix metrics *per workload*, not aggregated. JSONL row schema: `{workload, router_variant, policy, accuracy, reroute_rate, pass@1, p50, p95, p99}`.
2. Make per-workload gates: shadow→enforce requires `reroute_rate ≥ 0.15 AND pass@1_regression ≤ 0.02` *on each of bead-history and held-out-agents independently*. LCB v6 is a sanity check, not a gate — it's not the production distribution.
3. Add the `held-out-agents` workload from P0 above.

### P1 — Oracle-upper-bound construction is unspecified

INPUT.md:290: `oracle-upper-bound — perfect routing (post-hoc, with ground truth) — establishes ceiling`.

The construction protocol matters enormously:

- **Strong oracle**: sees the actual `passed` outcome for each tier and picks the cheapest tier that passes. This is unreachable in production (you can't run all tiers and pick the winner) so the gap to oracle is huge — misleadingly so.
- **Weak oracle**: sees the same features the router sees plus the historical hit rate of each tier on this agent. Still post-hoc but uses only feature-space information, not outcome-space. This is what RouteLLM and FrugalGPT use.
- **Implicit oracle**: just B3 calibration applied perfectly. Then "oracle gap" measures how much the router improves over calibration, which is interesting but not a ceiling.

The spec doesn't say which. The three give wildly different "headroom" numbers. A research engineer can pick the most flattering definition post-hoc.

**Concrete remedy:** Specify in `.19.4` "Done when": "Oracle comparator uses *weak oracle* construction: at inference time it sees task features plus the per-tier historical hit rate from the calibration file, but does not see the outcome of the current call. Construction code is committed alongside the eval matrix."

### P2 — "Holdout is by-time, not random" is necessary but insufficient

INPUT.md:183: `Holdout split is by-time (last 2 weeks) not random — to catch temporal leakage from calibration feedback`. Correct intent, but it only catches *direct* temporal leakage. It does not catch:

- The calibration-file leakage from P0.
- Counterfactual augmentation from `.19.2` (INPUT.md:168, "Counterfactual labels from interspect shadow-mode logs"). If shadow logs from the holdout window are used as augmentation, that's leakage.
- Synthetic perturbations from `.19.2` (INPUT.md:170, "paraphrase prompts to expand the surface"). If paraphrases of holdout tasks are used as training, that's leakage.

The proposal mentions "any counterfactual augmentation from shadow logs is also excluded from the test window" implicitly through the by-time split, but doesn't make it explicit.

**Concrete remedy:** Make the holdout-protection rules explicit in `.19.2` "Done when":
1. No data point with timestamp > cut_date appears in training.
2. No paraphrase of a data point with timestamp > cut_date appears in training.
3. No counterfactual derived from a shadow log entry with timestamp > cut_date appears in training.
4. The calibration file used for any judge augmentation has hash matching the snapshot at cut_date.

These are checkable invariants. Add a CI check that fails if any are violated.

### P2 — pass@1 measurement is undefined for retried prompts

If a task in the bead-history corpus was retried (e.g., first run on Haiku failed, then re-run on Sonnet succeeded), `pass@1` is ambiguous:

- Is it 0 (the first attempt failed) or 1 (the task eventually passed)?
- If the router predicts Haiku for this task, does it credit the eventual Sonnet success or only the Haiku failure?

The eval harness will silently pick a convention; if it's not the same convention used by the calibration file, the agreement metric will look wrong without it being wrong.

**Concrete remedy:** In `.19.2`, define `passed` as "the first model attempted passed." Tasks that required retry record the first model and `passed = false`. This is the production-honest convention — the router is making a routing decision, not a multi-shot escalation policy. Coordinate with cascade-design sibling on whether multi-shot escalation is in scope (it isn't, per INPUT.md:464-466).

### P3 — "Synthetic adversarial set" is an undefined target

INPUT.md:283: `Synthetic adversarial set: tasks designed to look easy but require deep reasoning (catch over-routing to haiku)`. This is constructed by the team. There is no defined protocol or hold-out from this set. After seeing matrix results, the constructor can add or remove tasks to flatter the router's strengths.

**Concrete remedy:** Define and freeze the adversarial set *before* training begins. Commit it under `interverse/interfer/benchmarks/microrouter_v0_adversarial.jsonl` with N ≥ 50 tasks. Tasks are reviewed by a second pair of eyes (the design-bead author or the user). Once frozen, no edits without explicit changelog entry.

## Improvements

- **Per-tier confusion matrix as a JSONL artifact, not a markdown table.** The harness consumes it programmatically for gate decisions. Already mentioned in `.19.3` outputs (INPUT.md:230); promote to `.19.4` outputs as well.
- **Track call latency *and* end-to-end latency separately.** Router latency is what `.19.4` measures (INPUT.md:275). End-to-end latency (router + downstream model) is what users feel. They are different by 1-3 orders of magnitude depending on the downstream model. Both belong in the matrix.
- **Add a "no-router" baseline that uses today's exact production policy** (B1+B2+B3+B4+B5 as currently configured) to anchor regressions. The "none" comparator (INPUT.md:289) implies this but doesn't specify whether B5 shadow logging is included.

## Anti-Overlap (handed off to siblings)

- Resolver chain semantics, fall-through behavior, mode interactions → **fd-routing-cascade-design**
- Loss design, judge protocol, training corpus construction → **fd-lora-distillation-pipeline**
- Shadow soak, distribution-coverage of soak sprints → **fd-production-rollout-safety**
- Eval-harness reproducibility, schema for matrix outputs → **fd-config-resolver-architecture**
