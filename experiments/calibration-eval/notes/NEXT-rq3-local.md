# NEXT — RQ3 logprob study on local inference (+ optional Step-2 decode spike)

Pickup prompt for a new **workstation** session (128GB Apple Silicon MacBook).
Paste the fenced block below into a fresh Claude Code session on this repo.

## Where things stand (2026-06)

Step 1 is fully merged to `main`:
- behavioral eval (type-2 SDT: AUROC, meta-d′, M-ratio) — PR #21
- reasoning on/off ablation — PR #22
- dose-response null result (reasoning-effort isn't a graded dial on Nous Portal) — PR #26
- multi-family RQ1 sharpening — PR #27

**Net finding:** metacognitive efficiency is bought by *reasoning*, not scale, and
*declines* with scale in reasoning models (capability outruns introspection).

**The gap this picks up:** the RQ3 logprob-elicitation arm was dead all program —
Nous Portal returns `null` logprobs for almost every open model (`granite-4.1-8b`
was the lone exception). Local inference exposes real token logprobs for any open
model, so we can finally run the three-way RQ3 comparison (logprob vs verbalized
vs sampling confidence) on the families where we measured the RQ1 decline. The
same local setup is the substrate for the Step-2 introspection flagship.

## Why local (128GB MacBook) rather than cloud

- Local inference engines (llama.cpp / MLX) return per-token logprobs natively —
  removing the portal limitation that crippled RQ3.
- 128GB unified memory runs the small-to-mid ladder rungs (≤~70B quantized); the
  portal still serves the 235B/397B/405B giants.
- Workstation session ⇒ beads are writable (file follow-ups directly).
- Doubles as the Step-2 activation-access substrate.

---

## Prompt

```
Run the RQ3 logprob study with LOCAL inference (128GB Apple Silicon MacBook),
in the metacognitive-calibration-eval program (experiments/calibration-eval/).
Fresh branch off main. WORKSTATION session (beads writable — file follow-ups
directly instead of parking them in the PR).

WHY LOCAL: Step 1 is fully merged (behavioral eval + reasoning on/off ablation +
dose-response null + multi-family RQ1). Net finding: metacognitive efficiency
(type-2 SDT M-ratio) is bought by *reasoning*, not scale, and DECLINES with scale
in reasoning models. Throughout, the RQ3 logprob-elicitation arm was dead: Nous
Portal returns null logprobs for almost every open model (granite-4.1-8b the lone
exception). Running models LOCALLY exposes real token logprobs for ANY open model,
enabling the three-way RQ3 comparison — logprob vs verbalized vs sampling
confidence — on the same families where we measured the RQ1 decline. This local
setup is also the substrate for the Step-2 introspection flagship (see tail).

SETUP:
1. Clone, cd experiments/calibration-eval, uv venv && uv pip install -e ".[dev]";
   pytest (39) + python scripts/validate_pipeline.py must pass.
2. Stand up a local OpenAI-compatible server exposing /v1/chat/completions WITH
   per-token logprobs. Pick by whichever actually returns logprobs:
     - llama.cpp `llama-server` (most logprob-proven; n_probs), or
     - MLX `mlx_lm.server` (Mac-native, fast; verify logprobs in the response).
   The inspect harness reuses its openai-api provider: set
     LOCAL_API_KEY=local-dummy
     LOCAL_BASE_URL=http://localhost:<port>/v1
   and address models as  openai-api/local/<served-model-name>  (same
   <SERVICE>_API_KEY/<SERVICE>_BASE_URL mechanism we used for NOUS).

HARD GATE 1 (do NOT skip — this is the whole premise):
   inspect eval src/tasks.py@calibration_mmlu -T elicitation=logprob \
     --model openai-api/local/<model> --limit 5 --log-dir runs/gate
   Confirm metadata.elicitation == "logprob" (NOT "logprob_fallback_verbalized")
   AND the parsed confidences VARY (the solver reads the answer-letter token's
   probability — verify that token appears with a logprob; may need top_logprobs).
   Use ANCHORS (mmlu/truthfulqa/gsm8k), not the custom set (logprob-confidence
   pegs near 100 on easy custom items). If logprobs don't come through, switch
   server (llama.cpp <-> MLX). No matrix until this gate is green.

MODELS (public weights fitting ~100GB; match RQ1 ladder families where public
checkpoints exist): Qwen3 8b/14b/32b, Mistral Ministral 3b/8b/14b, Gemma 3
12b/27b, Llama 3.1 8b (+70b @4-bit), granite-4.1-8b. NOT the 235B/397B/405B
giants (portal still serves those). Pick 2-3 spanning a ladder; note the quant.

MATRIX (per model, after a per-model smoke + the logprob gate): all four arms —
verbalized, sampling, logprob, reflect — on custom + mmlu(--limit 300)/
truthfulqa/gsm8k(--limit 300). Use scripts/run_rung.sh (passes args through; add
the logprob arm). All runs status:success; check parse rates per arm.

ANALYZE — RQ3 headline is a WITHIN-MODEL comparison across elicitation methods
(self-consistent regardless of quant/finetune): per model, compare type-2 AUROC /
meta-d' / M-ratio across {verbalized, sampling, logprob}. Which elicitation best
discriminates the model's right vs wrong answers? Comparison figure: reuse
scripts/reasoning_ablation_compare.py / scripts/rq1_crossfamily.py patterns.

DELIVERABLE: commit runs/summary.csv + figure(s) + notes/<name>.md; gitignore
exception for any new committed CSV (match runs/summary.csv). DRAFT PR to main;
CI (.github/workflows/calibration-eval.yml) runs pytest + validate_pipeline.
File bead candidates directly (workstation session).

CAVEATS TO RECORD:
   - Quantization can perturb logprobs — note the quant; spot-check one model
     higher-precision if feasible.
   - Local weights may differ from the portal's finetunes — frame RQ3 within-model
     across elicitation methods, NOT local-vs-portal on identical weights.
   - Size ceiling: logprob arm covers small-to-mid rungs (complements the portal).

================================================================================
OPTIONAL TAIL — Step-2 introspection spike (decode-only; do ONLY if RQ3 lands and
there's time/appetite). This is Probe A from the ROADMAP / introspection-probe
DESIGN.md: "is stated confidence read from an internal uncertainty signal, or
confabulated?" Decode-only — NO steering yet (that's Probe B/C, deferred).

PREMISE: the RQ3 run already labels each item with correctness, verbalized
confidence, and logprob confidence. The spike adds a fourth predictor — an
INTERNAL probe — and asks: does a linear probe on the residual stream predict the
model's own correctness BETTER than its stated confidence does? If yes, the model
"knows more than it says" (headroom), which is the result that motivates the whole
flagship.

SPIKE STEPS:
1. Pick the smallest gated model (e.g. granite-4.1-8b or qwen3-8b). Load it in
   PyTorch/HF on the MPS backend (separate from the MLX serving runtime — MLX is
   for fast logprob serving; activation capture needs HF/torch hooks, or
   nnsight/transformer_lens if the architecture is supported).
2. Re-run the ANCHOR items (300+ for enough probe data) through a forward pass,
   capturing the residual-stream activation at a fixed position — document the
   choice (last prompt token = pre-answer state, vs the answer/CONFIDENCE-line
   token = at-report state; the latter is more apt for "does it know it's right").
   Sweep a few mid/late layers.
3. Train a logistic-regression probe (correctness ~ activation) with a held-out
   test split (or k-fold); the anchors give enough n. Report best-layer test AUROC.
4. THE COMPARISON: on the held-out items, internal-probe AUROC vs verbalized-
   confidence AUROC vs logprob-confidence AUROC at predicting correctness.
   Headroom = internal_AUROC - verbalized_AUROC. Positive headroom = confabulation
   gap (knows more than it says); ~zero = stated confidence already reads out the
   internal signal.
5. DELIVERABLE: a notes/step2-decode-spike.md with the AUROC table + one figure,
   committed alongside the RQ3 PR or its own draft PR. File a bead for Probe B
   (causal steering of the uncertainty direction) as the explicit next step.

SPIKE CAVEATS: correlational only (a probe finding a decodable signal != the model
USES it — that's what steering tests); small n, so cross-validate and report CIs;
probe AUROC can inflate with layer/hyperparam search — lock the test split first.
Tooling: transformer_lens supports MPS for many archs; nnsight wraps arbitrary HF
models; raw forward hooks on model.model.layers[i] are the most portable fallback.
```

## Open follow-ups parked elsewhere

- Remote branches `claude/reasoning-ablation-qwen3.5`, `claude/reasoning-dose-response`,
  `claude/rq1-multifamily` are merged but not auto-deleted on the remote — clean from
  the GitHub UI (the environment's git proxy refuses branch deletes).
- Lower-priority experiments: Qwen3-dense reasoning on/off (confirm the decline in a
  third family); frontier-open robustness pass (verbalized/sampling only — they return
  null logprobs); dataset expansion (cultural tier saturates at 100%).
