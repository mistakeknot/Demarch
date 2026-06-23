---
title: "Scoping: BHQ speed optimization via autoresearch (sylveste-naj)"
date: 2026-06-22
type: scope-spike
bead: sylveste-naj
status: scoping-only
related: [sylveste-d5e, sylveste-ipu, Sylveste-wfz]
verdict: park
---

# Scoping: BHQ speed optimization via autoresearch

**Bead:** `sylveste-naj` — `[interfere] BHQ speed optimization via autoresearch`
**This doc is scoping only. No code was run, no benchmark executed, no bead written or closed.**

## What the bead asks

Close a measured ~30% throughput gap between BHQ-4 (Lloyd-Max centroid KV
quantization, "TurboQuant v3") and MLX-native quantized attention. Original
measurement: 56 vs 82 tps on Qwen2.5-3B-Instruct-4bit
(`docs/solutions/2026-03-27-bhq-validation-results.md`). Proposed method:
`interlab autoresearch` over `interlab-bhq-tune.sh`, exploring three
optimizations — batch/incremental dequantization, binary-search quantization
(replace argmin), and incremental attention accumulation.

## Claims verified against actual code

All three named bottlenecks are real and present in
`interverse/interfer/server/experiments/turbo_quant.py`:

1. **argmin over all centroids, per coordinate** — `bhq_quantize`
   (`turbo_quant.py:280-281`) materializes a `(..., head_dim, n_centroids)`
   distance tensor then `mx.argmin`. For 4-bit that's 16 centroids; the diff
   tensor is 16x the key size before reduction. Confirmed.

2. **Full-history re-dequantize every decode step** — `update_and_fetch`
   (`turbo_quant.py:389-391`) calls `bhq_dequantize(self._key_indices, ...)`
   on the *entire* accumulated `_key_indices`, then rescales by all norms,
   *every* token. The residual variant repeats this at `575-577`. At decode
   only one new token is appended but O(seq) work is redone. This is the
   dominant asymptotic cost and the most defensible optimization target.
   Confirmed.

3. **Non-fused attention path** — `bhq_attention` (`turbo_quant.py:667-724`)
   is a hand-rolled scores→softmax→matmul. It cannot use MLX's fused SDPA
   kernel because keys live in rotated centroid space. The monkey-patch
   (`install_turbo_quant_attention`, `944-952`) routes BHQ caches here.
   Confirmed.

So the technical premise is sound. The strategic premise is where the spike
is weak.

## Where the bead is weak (be skeptical)

### A. The harness benchmarks a model BHQ doesn't work on

The bead title and validation doc both reference **Qwen2.5-3B** (head_dim=128).
But `interlab-bhq-tune.sh:17` defaults `BHQ_MODEL` to
`mlx-community/Qwen2.5-0.5B-Instruct-4bit` (head_dim=64). The *same validation
doc* (`2026-03-27-bhq-validation-results.md:38-40`) states 0.5B **failed for
quality** — head_dim=64 is too small for the Beta-distribution concentration
BHQ relies on, and 4-bit weights make it double-quantization. An autoresearch
loop pointed at the default model would optimize tps on a config where BHQ
produces garbage. The harness must be re-pointed at 3B (and `BHQ_MODEL` set
explicitly) before any number is meaningful. This is a latent footgun, not a
blocker, but it signals the spike was filed without re-checking the harness.

### B. BHQ is off by default and not on the production path

`server/experiments/defaults.yaml` ships every experiment `enabled: false`.
BHQ is gated behind an experiment config flag (`inference.py:102-104`,
`271-306`) that no production model config turns on. Optimizing the speed of a
code path that nothing currently uses is optimizing a benchmark, not a product.

### C. The KV-pressure premise predates the M5 Max

The 3B validation (2026-03-27) framed KV quantization as worth a throughput
hit because it buys *quality* at low bit-width (BHQ-4 coherent, Native-4
garbage). That tradeoff matters when KV cache is the binding memory
constraint. On **M5 Max 128GB**, a 3B model's KV cache at full fp16 is
trivially small even at 64k context. The workload that motivates *any* KV
quantization for small models barely exists on this hardware. The bead never
asks "do we need KV quantization here at all" — it jumps to "make our KV
quantizer faster." That is optimizing a leaf when the branch is in question.

### D. Tests may be red

The 2026-06-22 backlog digest flags **Sylveste-wfz: TurboQuant test failure**
as an open investigation bead. `tests/test_turbo_quant.py` has 32 tests
covering BHQ. Running an autoresearch keep/discard loop against a module with
a known-failing test risks chasing a moving baseline. Sylveste-wfz should be
resolved first regardless.

### E. autoresearch is a heavy instrument for a 3-knob search

The three proposed optimizations are not a hyperparameter sweep — they are
three distinct code rewrites (incremental dequant, binary-search quant, fused
path). `interlab autoresearch` shines for many-iteration metric chasing over a
mutation surface; here the win is mostly the single structural fix in (2).
A targeted edit + one A/B benchmark would capture ~80% of the available gain
without standing up an autoresearch campaign.

## Hypothesis (testable)

> The dominant BHQ decode-time cost is the full-history re-dequantize in
> `update_and_fetch` (`turbo_quant.py:389-391`), not the argmin in
> `bhq_quantize`. Caching dequantized keys and dequantizing only the newly
> appended token each step will recover the majority of the 30% gap on
> Qwen2.5-3B-Instruct-4bit, closing it to <10% — **without** touching the
> argmin or building the fused path.

This reframes the bead: the spike's real value is one structural fix, and the
hypothesis is falsifiable with a single before/after benchmark.

## Pre-registered KILL RULE (Phase-1 measurement first)

Per platform doctrine (test-null-hypothesis-first), Phase 1 is a measurement,
not a build:

**Phase 0 (prerequisite, ~30 min):** Resolve or confirm Sylveste-wfz so the
test baseline is green. If TurboQuant tests cannot be made green in <1 hr,
**STOP** — do not optimize a broken module.

**Phase 1 (measurement, ~half day):**
1. Re-point the harness at `Qwen2.5-3B-Instruct-4bit` explicitly.
2. Profile a 200-token decode to attribute wall-time across the three
   bottlenecks (incremental timing around `bhq_quantize`, `bhq_dequantize`,
   `bhq_attention`).
3. Confirm the 30% gap still reproduces on current MLX (the original number is
   ~3 months old; MLX kernels and the affine-quant baseline may have moved).

**KILL conditions (any one → close `sylveste-naj` MOOT, file nothing):**
- The 30% gap no longer reproduces (gap already <10% on current MLX), OR
- The profile shows dequant is **not** the dominant cost AND no single fix is
  projected to recover >15 percentage points, OR
- Phase 0 reveals BHQ quality is broken on 3B too (regression since March), OR
- No production or near-term planned model config enables BHQ, i.e. the speed
  of this path is load-bearing on nothing (this is the most likely kill).

Only if Phase 1 shows (a) the gap reproduces, (b) incremental dequant is
projected to close it to <10%, and (c) there is a concrete consumer for BHQ
KV quantization, proceed to Phase 2 (the targeted edit + A/B). Do **not** open
the autoresearch campaign unless Phase 2's single fix underdelivers and a
multi-knob search is genuinely warranted.

## Method in brief

- Phase 0: green the tests (Sylveste-wfz).
- Phase 1: profile + reproduce on 3B (correct model), attribute the gap.
- Phase 2 (conditional): cache dequantized keys, dequantize only the appended
  token, re-benchmark A/B vs native-4 and vs current BHQ.
- Phase 3 (conditional, unlikely): autoresearch over argmin→binary-search and
  fused-path variants only if Phase 2 leaves >15% on the table.

## Effort

- Phase 0+1 (the part worth doing now): **~half a day**.
- Full pursuit through Phase 2: ~1-2 days.
- Phase 3 autoresearch: another 1-2 days (likely never reached).

## Recommendation: **PARK**

The technical bottleneck analysis is correct and the one high-value fix
(incremental dequant) is real. But the spike optimizes the speed of an
opt-in, off-by-default experimental code path with no current consumer, on
hardware (M5 Max 128GB) where the original KV-pressure motivation is weak for
small models, while a related test (Sylveste-wfz) is flagged failing. The
honest cost-of-miss is near zero: nothing in production gets slower by leaving
BHQ unoptimized.

Park until there is a concrete consumer that (a) enables BHQ in a real model
config and (b) hits a measured KV-memory or throughput wall that BHQ's
quality-at-low-bits actually relieves. If that consumer appears, the work
collapses to Phase 0+1+2 (~1-2 days) and the autoresearch framing in the bead
is overkill — a single targeted edit captures most of the gain. Do not pursue
as a standalone benchmark exercise.

**Not MOOT** (the bottlenecks are real and the fix is known, so there is
latent value), but **not pursue-soon** (no consumer, weak hardware
motivation, failing-test precondition). Park with the kill rule above so that
if it is ever revived, Phase 1 can cheaply confirm or kill it.
