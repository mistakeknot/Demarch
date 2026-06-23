---
date: 2026-06-22
bead: sylveste-eka
title: "Scoping — thermodynamic-inspired annealing for MoE expert selection"
status: scoping
type: scope-spike
recommend: park
author: Claude Code (subagent scoping pass)
---

# Scoping: thermodynamic-inspired annealing for expert selection (sylveste-eka)

## The bead, restated

> Treat expert selection as simulated annealing. Instead of always picking
> top-K experts by router score, use a temperature parameter that starts high
> (explore diverse experts) and anneals low (exploit best experts) as
> generation progresses. Hypothesis: early tokens benefit from diverse expert
> perspectives (brainstorming), later tokens from focused expertise (editing).
> Could compose with MoE streaming to predictively pre-fetch "warm" experts.

P4, `issue_type: feature`, created 2026-03-26, last touched 2026-03-27. Zero
dependencies, zero dependents. It has been dormant for the entire life of the
project since its second day. Sibling esoteric bead **sylveste-c57** (ant colony
optimization for expert routing) is the same vintage, same P4, same dormancy,
and shares the same load-bearing assumption.

## What the code actually does (verified, not speculated)

Expert selection happens in exactly one place that interfer controls:
`interverse/interfer/server/streaming_switch.py:144-155`:

```python
gates = self.gate(x)
gates = mx.softmax(gates, axis=-1, precise=True)
k = self.top_k
inds = mx.argpartition(gates, kth=-k, axis=-1)[..., -k:]   # deterministic top-k
scores = mx.take_along_axis(gates, inds, axis=-1)
if self.norm_topk_prob:
    scores = scores / scores.sum(axis=-1, keepdims=True)
```

Three facts that bound the entire spike:

1. **This is the streaming PoC path only.** The class docstring
   (`streaming_switch.py:88-94`) states plainly that MLX's `nn.Module.__call__`
   uses C++ dispatch and ignores instance-level `__call__` overrides, which is
   why interfer had to *replace the whole `layer.mlp`* with a Python wrapper.
   The normal in-memory inference path (`inference.py`) routes through mlx-lm's
   compiled `SwitchGLU` and exposes **no hook** for top-k modification. So an
   annealing experiment can only run inside the SSD-streaming worker — the same
   path that is currently the slowest thing interfer ships.

2. **`temperature` in this codebase is token-sampling temperature, not expert
   temperature.** `inference.py:204,262` and `flashmoe_worker.py:305,331` all
   pass `temperature` into `make_sampler(temp=...)` — that controls vocabulary
   logits, not the router. There is no existing expert-temperature plumbing;
   this would be net-new and would have to thread through the experiment-config
   system (`server/experiments/config.py` + `defaults.yaml`).

3. **The streaming bottleneck is the number of unique experts loaded per layer.**
   `streaming_switch.py:158-160` computes `unique_experts = sorted(set(flat_inds))`
   and `pread()`s each one from NVMe. Cost is linear in unique experts.
   High-temperature stochastic selection *by construction* widens the set of
   experts touched per token — i.e. it makes the current worst path strictly
   slower. (See sylveste-Bov below.)

## Why the premise is suspect (the skeptical read)

The hypothesis anthropomorphizes MoE experts. In a trained sparse MoE, the gate
learned a fixed top-k routing policy *jointly with* the expert weights. Experts
are not human-legible specialists; there is no "brainstorming expert" and
"editing expert." Forcing activations through experts the gate did **not**
select feeds tokens into subnetworks trained on a different conditional input
distribution — an out-of-distribution intervention on a frozen network. The
expected outcome is degraded coherence, not "diverse perspectives." This is
categorically different from sampling temperature (which perturbs the final
output distribution the model was trained to produce) — it perturbs an internal
routing decision the model was never trained to have perturbed.

The "early tokens want diversity, late tokens want focus" intuition is a
narrative about *prompts*, not about per-token MoE routing. The model already
expresses uncertainty through its gate scores; if early-token routing were
genuinely flatter, top-k already captures it. There is no evidence in-tree, and
none cited in the bead, that the gate's entropy correlates with generation
position in a way an annealing schedule could exploit.

The streaming pre-fetch upside ("warm experts") is real but **inverted**:
stochastic selection *reduces* expert-locality, the opposite of what the cache
wants. The cache-warming gain belongs to a *narrowing* policy (the ant-colony
bead c57 at least points the right direction), not a high-temperature one.

## Where interfer's real pain is (opportunity cost)

The current interfer priority surface, from the most recent handoff
(`docs/handoffs/2026-05-11-policy-gate-fix-and-k8c-J.md`) and open beads:

- **sylveste-Bov (P2, open, bug):** flash-moe decode is ~5 tok/s vs the 12.9
  tok/s spec — 3x slower than target, "cost-effectiveness math is upside-down."
  This is the live, measured, load-bearing problem in the exact same code path
  eka would touch. Any engineering hour spent in `streaming_switch.py` should go
  here first.
- **k8c review-quality calibration** — the active, shipping workstream.

Against that backdrop, eka is a high-risk P4 with a contested premise that, even
if it worked, would worsen the metric Bov is trying to fix. The interfer
PHILOSOPHY.md is explicit: "Economics Before Elegance — a beautiful technique
that doesn't move a metric is research debt."

## Testable hypothesis (if it were ever run)

> On a fixed decode workload through the streaming MoE path, a position-annealed
> stochastic expert-selection schedule (T_high → T_low over generation) produces
> output quality (pass@1 on LCB v6, or judge-scored coherence) within 2% of
> deterministic top-k while the deterministic baseline is the control. The
> falsifiable, pre-registered direction is that annealing will *not* beat
> baseline quality and *will* increase unique-experts-per-layer (slower decode).

## Pre-registered KILL RULE (Phase-1 measurement, test-null-first)

Phase 1 is a **one-day, code-light probe**, not the experiment. Before building
any annealing schedule, instrument the existing deterministic path to measure
the two quantities the whole idea rests on:

- **K1 — routing-entropy-vs-position.** Log per-layer gate softmax entropy
  bucketed by generation position over ~200 decode steps on a representative
  prompt set. If early-token routing entropy is **not** materially higher than
  late-token entropy (Δ < 0.1 nats median, or no monotone trend), the
  "early=diverse, late=focused" premise is dead → **close eka MOOT**, do not
  build the schedule.
- **K2 — quality floor of any perturbation.** Run a single static-temperature
  perturbation (replace top-k argpartition with one Gumbel-softmax / temperature
  sample at a fixed moderate T) on a 30-problem LCB subset. If quality drops
  >5% pass@1 at *any* T that meaningfully changes expert selection, the OOD-
  intervention thesis is confirmed and annealing (which still perturbs early
  tokens) cannot recover it → **close eka MOOT**.

Either K1 or K2 failing kills the bead. Both passing only earns a *second*
scoping pass against then-current priorities (notably whether Bov is resolved).
This mirrors the microrouter-cluster discipline: "we could do X" is not a reason;
the workload must demand it, and a cheap measurement must clear the gate first.

## Method in brief (only if K1 + K2 both pass)

1. Add `expert_anneal` to `server/experiments/defaults.yaml` + `config.py`
   (params: `t_start`, `t_end`, `schedule`, `layers`), gated `enabled: false`
   like every other experiment.
2. In `StreamingMoeBlock.__call__`, replace the argpartition at lines 148-149
   with a temperature-scaled stochastic top-k (Gumbel-top-k) driven by the
   per-sequence generation step. Streaming path only; no attempt to hook the
   compiled in-memory path.
3. Run as an interlab campaign: baseline = deterministic top-k, treatment =
   annealed, metrics = pass@1 (LCB v6 subset) + median decode tok/s + mean
   unique-experts-per-layer. Kill criterion already pre-registered above.

## Rough effort

- Phase-1 probe (K1 + K2): **hours** (instrumentation is a handful of lines in a
  path that already exists; LCB subset harness already exists).
- Full experiment if it survives: weeks (schedule design, interlab campaign,
  quality regression analysis) — but it almost certainly will not survive K1/K2.

## Recommendation: PARK (lean MOOT)

Park, do not pursue. The honest read is this is closer to MOOT than to
pursue-soon, but the K1 entropy probe is genuinely cheap and would *also* inform
the streaming-cache work (sylveste-Bov / sylveste-2ss expert-cache-hit-rate
residual) regardless of eka's fate. If anyone is already in `streaming_switch.py`
for Bov, fold the K1 entropy instrumentation in for free and let the data close
eka. Standalone, eka does not clear the bar: contested premise, wrong direction
for the live bottleneck, P4 dormant 15 months, and a sibling esoteric bead
(c57) competing for the same speculative slot. Do not file followups; do not
revive c57 on eka's account.

## Followup beads to consider (for the workstation, not filed here)

- Fold a routing-entropy-vs-position probe (K1) into sylveste-Bov / the
  expert-cache-hit-rate residual instead of treating eka as standalone.
