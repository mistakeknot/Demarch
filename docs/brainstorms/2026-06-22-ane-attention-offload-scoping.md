# Scoping: ANE (Apple Neural Engine) Offload for Attention

**Bead:** sylveste-0zc (`[interfere] Experiment: ANE offload for attention`)
**Date:** 2026-06-22
**Status:** Scoping only — NOT run. Recommendation below.
**Doctrine:** test-null-hypothesis-first (a multi-week experiment needs a Phase-1 measurement with a pre-registered kill rule).

## The proposal (as filed)

> Apple's M5 Max has a 16-core ANE that sits idle during MLX GPU inference. Research whether
> standard attention (Q@K^T → softmax → scores@V) can be offloaded to ANE while the GPU handles
> expert forward passes. This would break the serial GPU→SSD→GPU pipeline constraint that
> flash-moe identified. Risk: ANE programming is undocumented beyond CoreML. Approach: profile
> ANE utilization during inference, test CoreML attention dispatch.

## Skeptical read — three problems with the premise

### 1. The named bottleneck is SSD bandwidth, not attention compute

The spike claims ANE offload "would break the serial GPU→SSD→GPU pipeline constraint that
flash-moe identified." But the flash-moe feasibility study
(`interverse/interfer/docs/investigations/2026-03-26-flash-moe-feasibility.md`) is explicit that
the constraint is **expert weight streaming from SSD**, not attention:

- Throughput on M5 Max is estimated **7-12 tok/s** for a 397B-A17B model (lines 22-29), gated by
  per-layer SSD I/O (~1.6ms/layer) and the ~85-90% expert cache hit rate.
- The flux-gen spec for this work
  (`interverse/interfer/.claude/flux-gen-specs/ssd-streaming-architecture.json`) names the decision
  lens as: "Prioritizes findings that reveal hard physical limits (NVMe sequential bandwidth, PCIe
  lane contention, Metal shared-memory copy costs) before evaluating software strategies. Dismisses
  optimizations that cannot move the needle past the bandwidth bottleneck."

In a 397B MoE with 17B active params, attention is a small minority of per-token FLOPs; the dominant
cost is moving ~17B worth of expert weights (a few GB) per token across the SSD/page-cache boundary.
Moving attention to a *different* compute unit does not reduce the bytes that must stream. By the
spec's own decision lens, this optimization "cannot move the needle past the bandwidth bottleneck."

The "serial GPU→SSD→GPU pipeline" the spike wants to break is a *streaming* pipeline. Attention
runs on already-resident KV state; it is not what serializes against SSD. Even a *free* attention
unit (zero latency) leaves the streaming wall untouched.

### 2. ANE is not a free lunch — it is a constrained, undocumented coprocessor

- **No low-level API.** The only public path to the ANE is CoreML, which requires ahead-of-time
  model compilation (`.mlmodelc`). A decode loop with a dynamic, growing, *quantized* KV cache
  (interfer uses `install_turbo_quant_attention`, `inference.py:279-344`) is the opposite of a
  static compiled graph. There is no documented way to dispatch a single fused-attention op to the
  ANE from inside an MLX generation loop. The spike concedes this ("undocumented beyond CoreML").
- **Numeric format.** ANE is fp16/int8-oriented. interfer's whole attention thesis is custom
  KV quantization (TurboQuant / BHQ). Round-tripping the quantized KV through a CoreML fp16 graph
  every decode step is a format-conversion tax, not a saving.
- **Memory traffic, not idle FLOPs, is the question.** The ANE shares unified memory but reaches it
  with lower effective bandwidth than the GPU for this access pattern. "Sits idle" describes compute
  occupancy, not whether the unit can usefully absorb a memory-bound op. The premise conflates idle
  silicon with available headroom.
- **Copy cost.** Per-token handoffs GPU↔ANE↔GPU add shared-memory copy + synchronization overhead
  on the critical decode path — exactly the "Metal shared-memory copy costs" the spec flags as a
  hard limit.

### 3. It overlaps with two better-targeted sibling spikes

The same followon batch contains optimizations aimed at the *actual* bottleneck:

- **sylveste-xc8** — page-cache / `mlx` memory wiring / expert prefetch. Directly attacks SSD
  streaming. Estimated 10-20% throughput.
- **sylveste-ji6** — MLA KV compression (93% KV reduction, DeepSeek-V2). Directly attacks KV
  memory footprint and bandwidth.

Both target where the time actually goes. ANE-attention does not. Effort is better spent there.

## If we run it anyway — Phase-1 framing (test null hypothesis first)

The honest version is not "build a CoreML attention path" (weeks). It is a **half-day measurement**
that can kill the idea before any integration work:

### Hypothesis (testable)
On the M5 Max, end-to-end attention compute is a large-enough share of per-token wall-clock during
MoE-streaming inference that moving it off the GPU could yield ≥10% throughput, AND the ANE can
absorb a fused-attention op faster than the GPU does today.

### Phase-1 method (brief)
1. **Profile attention share.** Instrument the existing MLX decode loop and measure the fraction of
   per-token wall-clock spent in the attention block (Q@K^T → softmax → scores@V) vs expert/MLP
   matmuls vs SSD/streaming stall, on a representative MoE config. Use `mx.metal` timing / the
   existing benchmark harness (`server/benchmark.py`, `benchmarks/holistic_benchmark.py`).
2. **Microbench ANE attention ceiling.** Build a *standalone* CoreML fused-attention model at a
   single representative shape (heads, head_dim, seq_len) and measure its latency in isolation
   (`coremltools` convert + `coremltools` predict timing). No integration — just the ceiling.
3. **Compare.** Put the ANE op latency next to the measured GPU attention time from step 1.

### Pre-registered KILL RULE
Abandon (close MOOT, file no followups) if **any** of:
- (a) Attention is **< 15%** of per-token wall-clock in step 1 (then even a free ANE attention path
  yields < 15% upside before any handoff/copy overhead — not worth the integration cost). This is
  the primary kill condition; the bandwidth analysis above predicts attention will land in the
  single-digit-percent range.
- (b) Standalone ANE fused-attention latency (step 2) is **≥** measured GPU attention latency
  (step 1) at the representative shape — the ANE is not even faster in isolation.
- (c) No `coremltools` path produces a runnable fused-attention `.mlmodelc` for the quantized-KV
  shape within the half-day budget (the undocumented-API risk materializes).

Pre-registering (a) at 15% follows the spec's own decision lens: optimizations that cannot move the
needle past the bandwidth wall are dismissed up front.

### Effort
- Phase-1 measurement: **hours** (half a day).
- Full integration if Phase-1 somehow passes: **weeks** (CoreML compilation, per-shape model cache,
  GPU↔ANE handoff plumbing, quant round-trip) — and even then it would not help the streaming
  bottleneck that motivated the bead.

## Recommendation

**park.** Not "kill" outright — there is a cheap, well-bounded Phase-1 measurement (profile attention
share) that is genuinely informative and reusable for *any* attention-path work (BHQ tuning,
sylveste-ji6 MLA, sylveste-naj BHQ speed). But the spike as written rests on a misdiagnosis: it
targets attention compute when the documented bottleneck is SSD expert streaming. Do not greenlight
the CoreML integration. If/when someone runs the Phase-1 attention-share profile (worth doing for
the sibling spikes regardless), let kill-rule (a) settle this bead — the bandwidth analysis predicts
it will fire. Until then this sits behind sylveste-xc8 and sylveste-ji6, which attack the real wall.

## Sources verified
- `interverse/interfer/docs/investigations/2026-03-26-flash-moe-feasibility.md` (lines 9, 16, 22-29) — SSD streaming is the bottleneck; 7-12 tok/s estimate.
- `interverse/interfer/.claude/flux-gen-specs/ssd-streaming-architecture.json` (line 6) — decision lens dismisses non-bandwidth optimizations.
- `interverse/interfer/server/inference.py` (lines 279-344) — attention path is custom quantized (TurboQuant/BHQ), not a static graph; hostile to CoreML AOT compilation.
- `~/.claude/.../memory/user_hardware.md` — M5 Max 128GB confirmed; no ANE-specific characterization on record.
- Sibling spikes sylveste-xc8 (page cache), sylveste-ji6 (MLA) — both target the real bottleneck.
