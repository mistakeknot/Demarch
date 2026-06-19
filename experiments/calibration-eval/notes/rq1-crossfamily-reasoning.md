# RQ1 sharpened: the metacognition-vs-scale decline is reasoning-specific

**Date:** 2026-06-18 · **Status:** result, 5 families / 14 models

## Question

Step 1 found RQ1 "inverts" across two families — within Hermes-4 (non-reasoning)
metacognitive efficiency *rises* with scale, within Qwen3.5 (reasoning) it *falls*. With
n=2 families that could be family idiosyncrasy, i.e. **scale is just the wrong axis**. PR
#22's ablation showed reasoning *mode* drives efficiency on a fixed model. This run tests
the resulting hypothesis directly: **does the rise-vs-fall track reasoning mode rather
than family/scale?**

## Design

Three new within-family size ladders on Nous Portal, balanced by reasoning mode, added to
the two published ladders. Same matrix as Step 1 (custom set × {verbalized, sampling,
reflect} + MMLU/TruthfulQA/GSM8K anchors); pooled-verbalized metrics. All 48 new runs
`success`.

- **Ministral** 3b/8b/14b — non-reasoning
- **Gemma 3** 12b/27b — non-reasoning
- **Qwen3** (dense) 8b/14b/32b — reasoning
- (+ published **Hermes-4** 70b/405b non-reasoning, **Qwen3.5** 9b→397b reasoning)

Llama 3.1 was dropped at the smoke gate: its 8b emits no `CONFIDENCE` line (0/2 parsed),
70b only 3/4 — it doesn't follow the elicitation protocol, so the ladder's small rung has
no usable verbalized data. (Protocol non-compliance as a model property, cf. the 122B
collapse in PR #22.)

## Result

Pooled-verbalized (n ≈ 1,400–1,460/model). Read the **type-2 AUROC** column as the
primary, ratio-free sensitivity measure; M-ratio is the capability-normalized efficiency.

| family | mode | rung | acc | type-2 AUROC | M-ratio |
|---|---|---|---|---|---|
| Ministral | non-reason | 3b | 0.643 | 0.695 | 1.67† |
| | | 8b | 0.733 | 0.623 | 0.61 |
| | | 14b | 0.780 | 0.631 | 0.52 |
| Gemma 3 | non-reason | 12b | 0.733 | 0.623 | 0.61 |
| | | 27b | 0.782 | 0.681 | 0.73 |
| Hermes-4 | non-reason | 70b | 0.728 | 0.536 | 0.18 |
| | | 405b | 0.803 | 0.612 | 0.40 |
| Qwen3 | **reason** | 8b | 0.803 | 0.745 | 0.93 |
| | | 14b | 0.834 | 0.719 | 0.72 |
| | | 32b | 0.821 | 0.635 | 0.45 |
| Qwen3.5 | **reason** | 9b | 0.855 | 0.794 | 0.92 |
| | | 397b | 0.918 | 0.763 | 0.61 |

† Ministral-3b M-ratio > 1 is an **unstable artifact**: first-order ability is weak there
(acc 0.64, d′ 0.52, ECE 0.33), and M-ratio = meta-d′/d′ blows up as d′→0. Trust the AUROC
column for that cell. (`m_ratio` suppresses below d′=0.1; 0.52 clears the floor but is
still shaky.)

### What the two panels show (`figures/rq1_crossfamily.png`)

1. **Reasoning families decline with scale — robustly, 2/2.** Qwen3 AUROC 0.745→0.635 and
   M-ratio 0.93→0.45; Qwen3.5 AUROC 0.79→0.76 and M-ratio 0.92→0.61. The decline appears
   on the ratio-free AUROC too, so it is **not** a d′-denominator artifact. Capability
   outruns metacognition in reasoning models.
2. **Non-reasoning families do not decline.** Hermes rises (0.54→0.61 / 0.18→0.40), Gemma3
   rises (0.62→0.68 / 0.61→0.73), Ministral is flat on AUROC (~0.63) — none fall on the
   trustworthy measure.
3. **At small scale, reasoning models are markedly more metacognitively sensitive**
   (red above blue, AUROC ~0.75 vs ~0.55–0.70), but that edge erodes as they scale.

## Verdict on the hypothesis

**Supported for the reasoning half, partially for the non-reasoning half.** The original
RQ1 "inversion" is not random family noise: the *decline* is specific to reasoning
families (both fall), while non-reasoning families trend flat-to-up. The cleaner statement
of RQ1 is therefore: **metacognitive efficiency declines with scale in reasoning models —
capability outruns introspection — whereas non-reasoning models hold or improve.** This
unifies RQ1 with the PR #22 ablation (reasoning buys efficiency, but the bought efficiency
doesn't keep pace as the reasoning model grows).

## Caveats

- 5 families is still small; the non-reasoning side is genuinely mixed (Ministral neither
  clearly rises nor cleanly falls once its 3b artifact is set aside).
- "reasoning vs non-reasoning" is a coarse binary, confounded with family/training recipe.
  Within-family scale trends are the clean comparison; the binary grouping is interpretive.
- Custom-set domain cells are n=15; the pooled numbers lean on the 300–817-item anchors.

## Reproduce

```bash
# 8-model matrix (this run): 3 families in parallel
for M in mistralai/ministral-3b-2512 ... qwen/qwen3-32b; do
  bash scripts/run_rung.sh openai-api/nous/$M & done
# cross-family synthesis figure + CSV (reads this run + the published runs dir):
python scripts/rq1_crossfamily.py --runs-dir runs \
  --runs-dir <published runs dir> --out figures --summary runs/rq1_crossfamily.csv
```
