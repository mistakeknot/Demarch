---
bead: sylveste-ji6
date: 2026-06-22
type: scoping
status: draft
recommend: likely-moot
---

# Scoping: Multi-head Latent Attention (MLA) for KV compression

Scoping-only doc for bead `sylveste-ji6` ("[interfere] Experiment: Multi-head
Latent Attention (MLA) for KV compression"). No code written. Per platform
doctrine (test-null-hypothesis-first), this pre-registers a Phase-1 measurement
and a kill rule before any multi-week commitment.

## The bead's ask (verbatim premise)

> DeepSeek-V2 introduced MLA which compresses KV states into a latent vector,
> achieving 93.3% KV cache reduction with 5.76x throughput increase. Research
> whether MLA can be applied as a post-training retrofit to existing models
> (Qwen3.5 uses standard GQA). If not retrofittable, MLA-native models
> (DeepSeek V3.2, Kimi K2.5) already have this — measure the KV savings on our
> hardware. This determines whether DeepSeek/Kimi have a structural advantage
> over Qwen for long-context local inference.

The bead has two sub-questions and a decision goal:
- **Q1 (retrofit):** Can MLA be bolted onto an already-trained GQA model
  (Qwen3.5) post hoc?
- **Q2 (native measurement):** If not, measure MLA's KV savings on the
  MLA-native models we have (DeepSeek V3.2, Kimi K2.5).
- **Goal:** Decide whether DeepSeek/Kimi structurally beat Qwen for long-context
  local inference.

## What the code and prior benchmarks already say (verified)

1. **Production models are GQA.** `server/inference.py:289-300` builds the KV
   cache from `num_attention_heads` / `num_key_value_heads` — the GQA shape.
   `AGENTS.md:61-63` pins the live routing tiers to `qwen3.5-9b-4bit` (C1) and
   `qwen3.5-35b-a3b-4bit` (C2). These are GQA throughout. MLA is not present in
   any deployed path.

2. **A mature KV-compression line already exists and targets the GQA models.**
   `server/experiments/turbo_quant.py` documents v1→v3: PolarQuant (NEGATIVE),
   TurboQuant affine (NEGATIVE), and BHQ (Lloyd-Max non-uniform scalar quant,
   paper-faithful). `inference.py:273-345` wires `kv_bits`, TurboQuant, and BHQ
   as live KV-compression options. There is also `sylveste-naj` (BHQ speed
   optimization) and `interlab-kv-group-size.sh` actively tuning this surface.
   The team's existing answer to "compress the KV cache on the models we run" is
   quantization of the GQA cache — which is orthogonal to MLA and already
   shipped.

3. **The MLA-native models the bead names do not run on this hardware.**
   `docs/benchmarks/2026-03-28-deepseek-v32-4bit.md`: DeepSeek V3.2 4-bit
   (352GB, 2.75x RAM ratio) → **GPU timeout**. Kimi K2.5 3-bit (418GB, 3.3x) →
   **GPU timeout**. GLM-5 4-bit (390GB, 3.0x) → **GPU timeout**. Only Qwen 397B
   4-bit (209GB, 1.6x ratio) runs, via flash-moe SSD streaming, at ~11 tok/s.
   The bottleneck on M5 Max 128GB is **total weight footprint**, not KV-cache
   size. MLA shrinks the KV cache; it does nothing for the 352-418GB weight
   load that is what actually times out. So Q2 ("measure KV savings on our
   hardware") is **non-runnable** for the named models until the weight-streaming
   problem is solved — which is a separate, much larger epic (SSD-streaming MLA
   port, estimated 2-3 days *just for the infer.m MLA kernel*, per
   `2026-03-28-kimi-k25-benchmark.md` Approach 2).

4. **MLA is an architectural choice, not a cache format.** MLA replaces the K/V
   projection matrices with a down-projection to a shared latent
   (`kv_lora_rank=512` in both DeepSeek V3.2 and Kimi K2.5 per their model-fact
   docs) plus per-head up-projections, trained jointly with the rest of the
   network. The "93.3% reduction / 5.76x throughput" figures are DeepSeek-V2
   **pretraining-time** results, not a retrofit result. There is no published
   method to convert trained GQA weights to MLA without retraining the attention
   block (and realistically a recovery fine-tune). That makes Q1 (retrofit)
   effectively answered NO from the literature, before any spike.

## Hypothesis (testable)

> **H:** On Sylveste's actual long-context local-inference workload, switching to
> an MLA-native model would deliver a materially better quality-per-token-of-
> context-or-latency outcome than the current Qwen3.5-GQA + TurboQuant/BHQ KV
> quantization path — *and* that MLA model is runnable on M5 Max 128GB.

The conjunction matters: MLA only wins if (a) the KV cache is actually the
binding constraint for some real workload, and (b) an MLA model that exploits it
can run at all on this hardware.

## Null hypothesis (what we expect to be true)

> **H0:** The KV cache is not the binding constraint for any current Sylveste
> workload. The binding constraints are (i) total weight footprint for the large
> MoE models (which MLA does not address) and (ii) decode throughput for the
> Qwen tiers (where BHQ/TurboQuant already operate on the GQA cache). Therefore
> MLA delivers no measurable end-to-end win available to us.

## Phase-1 measurement (cheap, before any port)

Run **only** these desk/measurement steps — no MLA implementation, no model
port:

1. **Workload context-length audit (hours).** Pull the actual prompt+generation
   token distributions from the live request path. Sources: `server/shadow_log.py`
   output and the holistic benchmark traces. Compute the P50/P95/P99 total
   sequence length seen in production routing. KV-cache pressure is
   O(seq_len * n_kv_heads * head_dim); if P95 context is small (e.g. <8k), the
   KV cache is a rounding error against weights and MLA is moot by construction.

2. **KV-vs-weight memory share at the deployed tiers (hours).** For
   `qwen3.5-9b-4bit` and `qwen3.5-35b-a3b-4bit`, compute KV-cache bytes at P95
   context vs. resident weight bytes. If KV is <~10% of footprint at P95, MLA's
   ~90% KV reduction buys <~9% total — below any threshold worth a multi-day
   architectural change.

3. **Re-confirm the MLA-native runnability gate (minutes).** The
   2026-03-28 benchmarks already show DeepSeek V3.2 / Kimi K2.5 GPU-timeout on
   this box. Confirm nothing has changed (new mlx-lm streaming, more RAM). If
   they still cannot run, Q2's "measure on our hardware" is dead on arrival.

## Pre-registered KILL RULE

Close `sylveste-ji6` **MOOT** and file no MLA followups if **any** of:

- **(K1) KV is not the constraint.** P95 production context length implies the KV
  cache is <10% of the deployed-tier memory footprint (Phase-1 steps 1-2). MLA's
  best case (~90% KV reduction) then yields <~9% total — under threshold.
- **(K2) The MLA models can't run.** DeepSeek V3.2 and Kimi K2.5 still GPU-
  timeout on M5 Max 128GB (Phase-1 step 3), so "structural advantage for
  long-context local inference" is unobservable on this hardware — and the
  weight-streaming port that would change this is a different, larger epic, not
  this bead.
- **(K3) Retrofit is not real.** No published GQA→MLA post-hoc conversion exists
  that avoids retraining the attention block; the bead's Q1 is answered NO by
  the literature, and we are not in the business of pretraining attention.

Conversely, **only escalate to a Phase-2 spike** if Phase-1 shows BOTH (a) P95
context where KV exceeds ~25% of footprint on a deployed tier, AND (b) at least
one MLA-native model that actually runs end-to-end on this hardware. Absent that
conjunction, there is nothing to measure.

## Method in brief (if it survived Phase-1 — it likely won't)

Phase-2 would NOT be "retrofit MLA to Qwen" (ruled out by K3). It would be:
benchmark a runnable MLA-native model against the Qwen-GQA+BHQ baseline at the
P95 context length, on the same LCB/holistic harness, measuring quality, decode
tok/s, and peak memory. That is gated entirely on a runnable MLA model existing,
which today it does not.

## Effort

- Phase-1 measurement: **hours** (log analysis + arithmetic + one runnability
  re-check; no new code).
- Phase-2 (only if Phase-1 escalates, which is unlikely): **weeks** (depends on a
  separate SSD-streaming MLA kernel port that is its own epic).

## Recommendation: likely-moot

Three independent reasons converge:

1. **Wrong layer for retrofit.** MLA is a trained architecture, not a cache
   codec. The bead's headline option (retrofit to Qwen) has no path that avoids
   retraining attention. The retrofit question is answerable as NO from the
   literature in an afternoon.

2. **Wrong bottleneck for the native option.** The MLA-native models the bead
   wants to measure already fail on this hardware for a reason MLA does not fix
   (total weight footprint, not KV size). "Measure KV savings on our hardware"
   cannot be executed today.

3. **The need is already served.** The team's real KV-pressure question —
   "compress the KV cache of the models we actually run" — is owned by the live
   TurboQuant/BHQ line and `sylveste-naj`, which operate on the GQA cache and
   ship today. MLA does not compose with or improve that path.

The honest move is the cheap Phase-1 audit (hours) purely to **document** the KV-
vs-weight share and the runnability gate, then close `sylveste-ji6` MOOT under
K1/K2/K3. This mirrors the microrouter-cluster lesson recorded in memory: "we
could apply technique X" is not a reason to spend weeks — the workload must
demand it, and here the binding constraints point elsewhere.

## What MLA evaluation would legitimately attach to

Not this bead, but worth noting for routing: if/when the SSD-streaming weight
problem for 350GB+ MoE models is solved (a separate epic — see flash-moe port in
`2026-03-28-kimi-k25-benchmark.md` Approach 2), then a DeepSeek/Kimi vs Qwen
long-context bake-off becomes runnable and MLA's KV advantage becomes one
measured variable among many. File that against then-current hardware/workload
if it ever arises; do not pre-commit it from here.
