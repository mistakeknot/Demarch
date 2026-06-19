# Null result: `reasoning-effort` is not a graded dial on Nous Portal Qwen3.5

**Date:** 2026-06-16 · **Status:** apparatus finding, dose-response not runnable here

## Question

PR #22 (reasoning-mode ablation) showed that turning reasoning **off** collapses
metacognitive efficiency (pooled M-ratio 0.92→0.63 on qwen3.5-9b) while barely moving
accuracy. The natural follow-up: is the effect **graded** — does M-ratio rise
monotonically with the *reasoning budget* as set by `--reasoning-effort
minimal→low→medium→high`?

That experiment presupposes the effort parameter actually administers graded doses. It
does not on this provider, so the curve isn't measurable here. This note records the
precondition probe so nobody re-attempts it.

## Probe

`scripts/probe_reasoning_effort.py` — MMLU per-sample `reasoning_tokens` by effort level.
Measures the *delivered* reasoning budget, not a downstream metric, so it isolates the
apparatus from the science.

## Result — flat / non-monotone (the dial is binary)

Mean reasoning tokens per MMLU sample (`runs/reasoning_effort_probe.csv`):

| model | none | minimal | low | medium | high |
|---|---|---|---|---|---|
| qwen3.5-9b (n=20) | 0 | 3295 | 4243 | 4207 | 3641 |
| qwen3.5-27b (n=15) | — | 3089 | — | — | 3003 |
| qwen3.5-397b-a17b (n=15) | — | 3385 | — | — | 3451 |

- `none` cleanly disables reasoning (0 tokens). Every other level turns reasoning **on**.
- Across `minimal/low/medium/high` the budget is **flat and non-monotone**: 9b peaks at
  `low`/`medium` and *drops* at `high`; 27b and 397b are indistinguishable at the extremes
  (`minimal`≈`high`). Within-level spread is huge (9b range 78–18k tokens) — the budget is
  set by **item difficulty**, not by the effort setting.
- Figure: `figures/reasoning_effort_not_graded.png`.

## Conclusion & implications

On Nous Portal, Qwen3.5 reasoning effort is effectively **binary** (`none` vs on); the
graded levels are not honored. Therefore:

1. **The dose-response curve is not runnable on this provider.** Running the 30-run matrix
   would have produced statistically indistinguishable M-ratios across effort levels —
   wasted spend on a non-varying independent variable. Stopped at the gate.
2. **The on/off ablation (PR #22) already captures the only reasoning axis this portal
   exposes.** No further reasoning-budget experiment adds signal here.
3. **Where the graded experiment *could* live:** a provider/run path that honors a real
   reasoning-token budget — local weights with an explicit `max reasoning tokens` cap
   (the Step-2 4090 path), or an API that exposes a numeric thinking budget. Filed as a
   bead candidate; deferred to Step 2.

## Reproduce

```bash
# re-run the probe (spends API): writes runs/effortprobe-<model>-<effort>/
python scripts/probe_reasoning_effort.py run --model qwen3.5-9b --n 20
# rebuild CSV + figure from any probe logs on disk (no API):
python scripts/probe_reasoning_effort.py report
```
