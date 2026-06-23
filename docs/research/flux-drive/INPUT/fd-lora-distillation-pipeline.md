<!-- flux-drive:complete -->
# fd-lora-distillation-pipeline — Microrouter Track B6 Training Pipeline Review

**Persona**: Practitioner shipping LoRA adapters via mlx-lm on Apple Silicon, fluent in distillation collapse modes, rank/alpha sensitivity for classification, judge-augmentation bias.
**Scope**: bead `.19.3` (LoRA training pipeline) and the parts of `.19.2` that flow into training labels. Anti-overlap with resolver design, eval methodology, rollout safety, schema (covered by sibling agents).

## Findings Index

| # | Severity | Title |
|---|----------|-------|
| 1 | **P0** | Holdout target ≥ 0.85 accuracy is satisfied by majority-class collapse — no per-tier recall floor |
| 2 | **P1** | < 100ms p95 latency benchmark is specified in isolation, not under concurrent B5 load |
| 3 | **P1** | "Cost-weighted regret" (RouteLLM pattern) is misapplied — Codex OAuth is free at point of use |
| 4 | **P1** | GPT-5.5 judge augmentation has no de-biasing protocol; will amplify Sonnet over-representation |
| 5 | **P2** | Rank 8/16, alpha 32 is a generative-task default — classification heads typically use lower rank |
| 6 | **P2** | Encoder-only Phase 2 has no quantitative trigger criterion — switch is indefinitely deferred |
| 7 | **P2** | Adapter checkpoint path is in `~/.cache/huggingface/...` but interfer serving discovery is unspecified |
| 8 | **P3** | No ablation distinguishes distillation wins from "more training data" wins |

## Verdict

**REWORK BEFORE CODE.** The training pipeline as written has a load-bearing P0 (the holdout gate is satisfiable by a model that routes everything to Sonnet, the majority class) and two P1s that interact: the latency benchmark and the loss function are both specified for a regime that doesn't match Sylveste's actual cost structure. The pipeline should not start training until per-tier recall gates, a no-monetary-cost loss design, and a load-aware latency benchmark are agreed.

## Summary

Bead `.19.3` (INPUT.md:203-256) trains a LoRA adapter on Qwen3.5-3B-Instruct via mlx-lm, with rank 8 or 16, alpha 32, and judge augmentation from GPT-5.5 xhigh fast for examples missing ground truth. The done-when criteria require holdout accuracy ≥ 0.85 vs. calibrated baseline and inference p95 < 100ms on M5 Max.

This setup has three structural problems that compound:

1. **Class imbalance is unaddressed.** The training corpus is built from interspect verdicts where the *current* policy routes the vast majority of execute-phase calls to Sonnet (`phases.executing.model: sonnet`, `routing.yaml:564`). The labels-via-pass-rate definition therefore contains the inherent prior "Sonnet works for most things." A 3B classifier trained with naive cross-entropy on this corpus will learn that prior and predict Sonnet always, which trivially clears the 0.85 bar but produces 0% reroute rate — the metric the eval harness gates on for shadow→enforce promotion (≥ 20% reroute rate, INPUT.md:300).
2. **The loss function is borrowed from a different cost regime.** RouteLLM's regret loss assumes monetary cost differences between tiers (haiku $0.X / sonnet $Y / opus $Z) drive the routing decision. Sylveste's Codex OAuth is free at point of use (the proposal says so, INPUT.md:33). A cost-weighted loss with monetary weights is therefore measuring the wrong thing — quality and latency, not dollars, are what matter. The risk section's "distillation collapses to always pick Sonnet" mitigation (INPUT.md:70) names the disease but the prescription (cost-weighted loss) treats a different one.
3. **Judge augmentation is the most leverage-y piece and the least specified.** GPT-5.5 xhigh fast filling label gaps with a `(task, model_options) → "which tier?"` prompt has no chain-of-thought structure, no calibration anchor, and no per-tier prior — it will fill the long tail with whatever the model defaults to, which is almost certainly Sonnet for ambiguous cases.

## Issues Found

### P0 — Holdout accuracy ≥ 0.85 is satisfied by majority-class collapse

If the training corpus is 85% Sonnet (a plausible distribution given `phases.executing.model: sonnet` and the safety-floor overrides), a model that predicts "sonnet" for every input achieves exactly 0.85 accuracy on a class-balanced holdout — the metric in the bead. The model would ship to shadow mode, the eval harness would log 0% reroute rate, the ≥ 20% reroute rate gate (INPUT.md:300) would fail, and ~6 weeks of LoRA training would have produced a constant function.

The risk section (INPUT.md:70) names this risk and proposes "per-tier calibration and cost-weighted loss" as the mitigation. Per-tier calibration in the loss is the right idea but the *gate* is wrong — the holdout gate measures aggregate accuracy, not per-tier recall. A model that under-predicts Haiku / over-predicts Sonnet can satisfy aggregate accuracy *and* have catastrophic minority-class recall.

**Concrete remedy:** Replace the holdout gate with a *vector* of per-tier metrics. Concrete numbers, derivable from the proposal's own `≥ 20% reroute rate` target:

- For a 3-way decision space (`haiku|sonnet|opus`), require **per-tier recall ≥ 0.60** on holdout, *and* aggregate accuracy ≥ 0.85.
- For the binary local/cloud space, require **balanced accuracy ≥ 0.80**, not raw accuracy.
- Track per-tier confusion matrix as a first-class artifact (the bead lists it under "Output" already, INPUT.md:230 — promote it to a gate).

This single change converts the holdout from a metric a collapsed model can pass into a real signal.

### P1 — < 100ms p95 latency benchmark is in isolation, not under concurrent B5 load

INPUT.md:237: `Inference-time latency benchmarked locally — must be < 100ms p95 on M5 Max for the eval bead to even bother`.

`routing.yaml:728` shows B5 (`local_models`) in shadow mode, which means interfer is *already* running Qwen3.6-35B-A3B inference for shadow logging on every B5-eligible call. The 35B-A3B model uses ~18GB resident (`routing.yaml:738`). The microrouter adapter on Qwen3.5-3B is ~2GB resident on top of that. On M5 Max with 128GB unified memory this fits comfortably for steady state, but:

- **Cold-start interaction.** The first call to the 3B adapter after a 35B inference allocates KV cache; if mlx's allocator is cold, p99 spikes well past 100ms even when p95 is comfortable. The benchmark needs to include cold/warm distinction.
- **Memory bandwidth contention.** M5 Max has shared bandwidth between CPU/GPU/Neural Engine; concurrent 35B inference saturates it. 3B inference scheduled during a 35B forward pass measures *bandwidth-starved* p95, not the headline number.
- **Thermal interaction.** The proposal correctly notes (`routing.yaml:735`) that thinking mode hurts at <600s budgets due to thermal effects. Sustained 3B inference adds to thermal pressure on top of 35B; the benchmark must be a sustained run (≥ 1k calls), not a microbenchmark.

This interacts directly with the routing-cascade-design sibling's P1 (`timeout_ms: 100` vs `p95 < 50ms` gate at different measurement points). Together: the gate is too loose *and* measured under wrong conditions.

**Concrete remedy:** Specify the latency benchmark protocol explicitly in `.19.3`'s "Done when":

1. Run ≥ 1000 router calls.
2. Concurrently run B5 shadow workload at production rate (matches whatever an active sprint hits).
3. Measure both warm-cache p95 *and* cold-start p99.
4. Record GPU/Neural Engine utilization during the run.
5. Gate: warm p95 < 50ms AND cold p99 < 100ms.

The interfer benchmark harness in `interverse/interfer/benchmarks/` already has the load-generation primitives — reuse rather than re-build.

### P1 — Cost-weighted regret loss is borrowed from a regime that doesn't apply

INPUT.md:217-219 says the loss is "cross-entropy over tier classes for v0, cost-weighted regret for v1". The cost-weighted regret in RouteLLM is `regret = (selected_cost - oracle_cost) + λ × (selected_quality - oracle_quality)` where the cost term has *monetary* weight.

INPUT.md:33 explicitly says: "Cloud delegation via codex/ChatGPT OAuth is free at point of use, so the economic squeeze is smaller than typical FrugalGPT setups". The two non-cost wins (latency, privacy, INPUT.md:34-35) are real but require a different loss design:

- **Latency-weighted regret**: `regret = (selected_latency_ms - oracle_latency_ms) + λ × (selected_pass - oracle_pass)`. This needs per-tier latency distributions, which the eval harness can produce. Easy.
- **Privacy-weighted regret**: indicator function — a `sensitive` task routed to cloud is infinity loss. This is structurally different from a continuous weight; better implemented as a *constraint* in the resolver (the privacy-routing extension `.19.6` is essentially this) and removed from the loss entirely.

**Concrete remedy:** Drop "cost-weighted regret" from `.19.3` and replace with "latency-weighted regret with privacy implemented as a constraint." Coordinate the privacy constraint with the routing-cascade-design sibling (it lives in the resolver, not the model).

### P1 — GPT-5.5 judge augmentation amplifies Sonnet over-representation

`.19.3` (INPUT.md:218) describes judge augmentation as: "where dataset lacks ground truth, prompt GPT-5.5 with `(task, model_options) → 'which tier?'` to fill gaps". Three issues:

1. **No calibration anchor.** The judge is asked to make a tier choice without seeing what the *current production policy* would choose. For ambiguous tasks, it will default to the more capable tier (Sonnet over Haiku). This systematically over-recommends Sonnet, *amplifying* the existing class imbalance.
2. **No CoT or per-tier prior.** A single-shot tier choice from a generative model has high variance. The same task asked twice can get different answers. There's no protocol for resolving disagreements (sample N, take mode? require unanimity? report uncertainty?).
3. **Judge-leak risk.** GPT-5.5 may be the same model family as GPT-5 used for some downstream calls. If the judge's biases match the production model's biases, the holdout will look great but production will hit the same biases the judge missed.

**Concrete remedy:** Specify the judge protocol in `.19.3` "Done when":
- Sample N=5 per task, require ≥ 4/5 agreement, otherwise mark "uncertain" and exclude from training.
- Include in the judge prompt: `"The current production policy would route this to {baseline_tier} based on {feature_summary}. Disagree only if you have a specific reason."` This anchors the judge against the calibration baseline.
- Hold out a 100-task subset where ground truth is *certain* (highly-passed tasks across multiple agents) and benchmark the judge against ground truth on that. Reject the judge entirely if its agreement with ground truth is < 0.85.
- Track judge-augmented vs ground-truth subsets separately in the eval harness — coordinate with eval-methodology sibling.

### P2 — Rank 8/16, alpha 32 is a generative-task default; classification typically uses lower rank

LoRA rank for a classification head is typically much lower than for generative fine-tuning. The empirical pattern in published distillation-to-router work (RouteLLM, FrugalGPT student models) uses rank 4-8 with alpha 8-16 for similar-scale classifiers, because the head only needs to project the final hidden state to ~3-5 logits.

Rank 16 with alpha 32 is reasonable for "make Qwen3.5-3B speak in a new persona" but excessive for "Qwen3.5-3B classifies tier in 3 buckets." The cost is (a) longer training, (b) higher-dimensional adapter (~2x size on disk), and (c) higher overfit risk on the minority classes — *exactly* what we're trying to avoid given the class imbalance P0.

**Concrete remedy:** Make rank a sweep, not a fixed value. Train rank ∈ {4, 8, 16}, alpha ∈ {8, 16, 32}, pick the configuration with the best per-tier recall floor (not aggregate accuracy). Mlx-lm's training script supports this trivially; the cost is wall-clock, not engineering.

### P2 — Encoder-only Phase 2 has no quantitative trigger

INPUT.md:225: "Open question for design bead: encoder-only Phase 2 if 3B latency is too high." The decision is deferred to the design bead, but the design bead (`.19.1`) doesn't include a concrete latency threshold or evaluation criterion either.

A sub-100ms p95 target may force the architectural switch to ModernBERT-encoder anyway. Without a defined criterion, the team will keep grinding on the 3B decoder past the point of diminishing returns.

**Concrete remedy:** In `.19.1`, add a decision criterion: "If after Round 1 of training, warm-cache p95 > 75ms on M5 Max under concurrent B5 load, switch to ModernBERT-encoder for v1." 75ms gives 25ms headroom under the 100ms ceiling for resolver overhead. The number is editable; the *criterion* is what the design bead is missing.

### P2 — Adapter checkpoint discovery is unspecified

INPUT.md:230: `~/.cache/huggingface/hub/models--sylveste--qwen3.5-3b-microrouter-v0/`. The interfer serving layer endpoint (INPUT.md:343, `endpoint: "http://localhost:8421/route"`) consumes the adapter, but the discovery mechanism isn't specified. Two questions:

1. **Path discovery.** Does interfer probe a known path, or take a config flag, or accept the path via routing.yaml? Until this is specified, training to a path the server doesn't know about is the default failure mode.
2. **Adapter swap protocol.** When v1 ships, does the server load the new adapter on a SIGHUP, restart, or hot-swap? If it requires restart, the rollback procedure (config-resolver-architecture and rollout-safety siblings) needs to know that.

**Concrete remedy:** Spec the path in routing.yaml's `microrouter:` section as `adapter_path: "<absolute-path>"`. Spec the swap protocol in `.19.5` (the integration bead).

### P3 — No ablation distinguishes distillation wins from data-volume wins

The proposal trains the router *and* simultaneously builds the dataset (`.19.2`). If v0 hits the targets, the team will not know whether the win came from (a) the LoRA distillation methodology or (b) just having ≥5K labeled examples. This matters for v1: if the win was from data, a non-LoRA classifier might be cheaper and faster.

**Concrete remedy:** As a stretch in `.19.4` (eval), include an ablation: train a logistic regression on hand-engineered features (token count, agent name, phase, file count) on the same data. Report its accuracy and per-tier recall. If logistic regression hits > 80% of the LoRA model's metrics, v1 should consider the simpler architecture. Coordinate with eval-methodology sibling.

## Improvements

- **Make the dataset bead `.19.2` produce stratified train/val/test splits and a class-imbalance report as outputs** — not just a JSONL. This is needed for the per-tier recall gates and for the judge-augmentation de-biasing protocol.
- **Track *agent name* as a first-class feature**, not just task text. The current proposal mentions it as an open question (INPUT.md:111), but it's the single highest-information feature for routing — agents have stable behavior profiles.
- **Add a `confused matrix` artifact gate** in `.19.3` "Output" that the eval harness can consume directly. Per-tier recall and per-tier precision are nondnegotiable inputs to the eval matrix.

## Anti-Overlap (handed off to siblings)

- Resolver chain insertion, mode interactions, response validation → **fd-routing-cascade-design**
- Holdout integrity, leakage, oracle-upper-bound construction → **fd-eval-methodology-holdout**
- Production rollback, adapter-swap operational safety → **fd-production-rollout-safety**
- Endpoint port conflict, schema bump, zero-cost-bypass test → **fd-config-resolver-architecture**
