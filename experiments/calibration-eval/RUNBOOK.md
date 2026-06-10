# RUNBOOK — executing the measurement loop on a workstation

This is the step-by-step for running real models. The cloud session that built this
cannot run it (no API key / no portal access), so everything here is for your machine.

## 0. Prerequisites

```bash
cd experiments/calibration-eval
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"     # installs inspect-ai, openai, anthropic, numpy, pandas, matplotlib
pytest                          # 36 tests must pass
python scripts/validate_pipeline.py   # no-API end-to-end check must print "PIPELINE OK"
```

## 1. Configure Nous Portal

Inspect's built-in `openai-api` provider reads `<SERVICE>_API_KEY` and
`<SERVICE>_BASE_URL` from the service prefix in the model string. For service `nous`:

```bash
export NOUS_API_KEY="<from portal.nousresearch.com>"
export NOUS_BASE_URL="https://<verify-exact-host>/v1"
```

**Verify on the portal dashboard (portal.nousresearch.com/api-docs):**
- [ ] exact base URL / `/v1` path
- [ ] exact Hermes model identifier strings (the capability ladder — small → large)
- [ ] does the chat completions response include `logprobs` / `top_logprobs`? (gates RQ3)
- [ ] are Claude / GPT families proxied? (enables the optional cross-family arm)

Fill these into `LADDER` and `LOGPROB_OK` below.

## 2. Smoke test (1 sample, ~cents)

```bash
M=openai-api/nous/<smallest-hermes-model>
inspect eval src/tasks.py@calibration_custom --model "$M" --limit 1 --log-dir runs
```
Confirm it completes and the log shows a parsed `confidence` + `correct`.

### Logprob-availability probe

```bash
inspect eval src/tasks.py@calibration_custom -T elicitation=logprob --model "$M" --limit 3 --log-dir runs
```
Then inspect the log: if `metadata.elicitation == "logprob"`, logprobs work; if it shows
`logprob_fallback_verbalized`, the provider didn't return usable logprobs — note that as
the RQ3 availability finding and skip the logprob arm for that provider.

## 3. Full run matrix

```bash
# Capability ladder (small -> large). Fill in verified strings:
LADDER=( "openai-api/nous/<hermes-small>" "openai-api/nous/<hermes-mid>" "openai-api/nous/<hermes-large>" )
LOGPROB_OK=1   # set to 0 if the probe above fell back

CUSTOM=src/tasks.py@calibration_custom
for M in "${LADDER[@]}"; do
  # custom interest-domain set: verbalized + sampling (+ logprob if available) + reflection
  inspect eval $CUSTOM                          --model "$M" --log-dir runs
  inspect eval $CUSTOM -T elicitation=sampling  --model "$M" --log-dir runs
  inspect eval $CUSTOM -T reflect=true          --model "$M" --log-dir runs
  [ "$LOGPROB_OK" = 1 ] && inspect eval $CUSTOM -T elicitation=logprob --model "$M" --log-dir runs

  # public-benchmark anchors (cap items to control cost/time)
  inspect eval src/tasks.py@calibration_mmlu       --model "$M" --limit 300 --log-dir runs
  inspect eval src/tasks.py@calibration_gpqa       --model "$M"             --log-dir runs
  inspect eval src/tasks.py@calibration_truthfulqa --model "$M"             --log-dir runs
  inspect eval src/tasks.py@calibration_gsm8k      --model "$M" --limit 300 --log-dir runs
done
```

Optional cross-family arm (if the portal proxies them, or with a direct key):
`--model openai-api/nous/<claude-or-gpt-id>` or `--model anthropic/claude-opus-4-8`.

## 4. Analyze

```bash
python -m src.analyze runs/*.eval --out figures --summary runs/summary.csv
```
Produces per-(model, elicitation, domain) reliability diagrams, the per-domain bar chart,
and `runs/summary.csv` with the full sensitivity (`auroc`, `meta_d_prime`, `m_ratio`) +
bias (`ece`, `brier`, ...) panel.

## 5. Read the result

- **RQ1:** plot `m_ratio` / `meta_d_prime` vs ladder position — does *efficiency* rise
  with capability, or only accuracy?
- **RQ2:** compare `m_ratio` across `domain_type`.
- **RQ3:** compare sensitivity across `elicitation` (note any logprob fallback).
- **RQ4:** `reflect=true` vs baseline.

## Cost / time

Behavioral eval, no GPU. The custom set is 45 items; benchmark anchors capped at ~300.
Sampling self-consistency multiplies custom-set calls ~10×. Expect low single-digit
dollars per model on a small Hermes ladder; check portal pricing.

## Commit results

Commit `runs/summary.csv` and `figures/*.png` only (raw `.eval` logs are gitignored).
File bead candidates for follow-ups (dataset expansion, flagship spike) on the workstation.
