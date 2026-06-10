# Metacognitive Sensitivity Eval

**Do frontier and open models *know what they know* — measured properly, controlling
for how good they are at the task?**

An eval built on [Inspect](https://inspect.aisi.org.uk/). Its headline is **metacognitive
sensitivity / efficiency** (type-2 SDT: meta-d′, M-ratio, type-2 AUROC) — how well a
model's confidence discriminates its *own* correct from incorrect answers — not plain
calibration. Calibration (ECE/Brier) is reported too, but as a secondary **bias panel**,
because it is confounded with accuracy and so cannot, by itself, answer the "knows what
it knows" question.

This is the **measurement loop** — the credibility ship and the target-finder for the
mechanistic-introspection flagship (see [`ROADMAP.md`](ROADMAP.md)). The metrics layer is
API-free and unit-tested; the eval layer drives Inspect against open-weight models (Nous
Portal / Hermes) and, where available, the Claude family.

---

## Why sensitivity, not calibration

> Plain calibration is a *bias* measure, confounded with task ability.

ECE asks "is confidence numerically well-scaled?" — but a more capable model is more
accurate, which mechanically flatters its calibration stats. So "calibration vs
capability" is not cleanly interpretable. The construct we actually mean by *knows what
it knows* is **metacognitive sensitivity**: does confidence track the model's own
correctness, *holding task ability fixed*? That is what type-2 SDT measures (Maniscalco &
Lau 2012; Fleming & Lau 2014), and it's the systems-neuroscience instrument this eval
ports to models.

---

## Research questions

| | Question | Headline metric |
|---|---|---|
| **RQ1** | How does metacognitive **sensitivity** change across a capability ladder? (Plain calibration would conflate this with accuracy.) | `meta_d_prime`, `m_ratio`, type-2 `auroc` |
| **RQ2** | Does sensitivity differ by **domain type** — crisp-technical vs cultural-factual vs consensus-recall? | per-domain `m_ratio` + bias panel |
| **RQ3** | Which elicitation method (verbalized % / **logprob** / sampling self-consistency) yields the most informative confidence? | sensitivity across `elicitation.py` variants |
| **RQ4** | Does introspective-reflection prompting improve or degrade metacognition? | `reflect=True` vs baseline |

---

## Layout

```
calibration-eval/
├─ src/
│  ├─ metrics.py      # type-2 SDT (meta-d′, M-ratio, AUROC) + bias panel (ECE/MCE/Brier) — pure numpy
│  ├─ elicitation.py  # prompts, parsers, Inspect solvers: verbalized / logprob / sampling
│  ├─ scoring.py      # correctness helpers + the combined confidence scorer
│  ├─ tasks.py        # Inspect tasks: custom set + MMLU / GPQA / TruthfulQA / GSM8K anchors
│  ├─ plotting.py     # reliability diagrams + per-domain bar chart
│  └─ analyze.py      # read Inspect .eval logs -> per-(model, domain) metrics + figures
├─ data/interest_domain.jsonl   # author's balanced custom item set
├─ scripts/validate_pipeline.py # no-API end-to-end harness check (mockllm)
├─ tests/test_metrics.py        # offline unit tests (no API, no inspect_ai)
├─ RUNBOOK.md  ROADMAP.md
├─ runs/  figures/  notebooks/
└─ pyproject.toml
```

The metrics and parsers carry **no `inspect_ai` dependency** and are unit-tested offline;
Inspect is imported lazily only where a solver/scorer/task actually runs.

---

## Setup

```bash
cd experiments/calibration-eval
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Open-weight ladder via Nous Portal (OpenAI-compatible; Hermes + 300+ models):
export NOUS_API_KEY=...                          # from portal.nousresearch.com
export NOUS_BASE_URL=https://...nousresearch.com/v1   # verify exact path on the portal
# Optional closed models (if you have a key, or if the portal proxies them):
export ANTHROPIC_API_KEY=sk-ant-...
```

Inspect's built-in `openai-api` provider needs no custom code: a model string
`openai-api/<service>/<model>` reads `<SERVICE>_API_KEY` and `<SERVICE>_BASE_URL`. So
`--model openai-api/nous/<model>` uses the two `NOUS_*` vars above.

> **Verify on the portal dashboard before running:** exact Hermes model strings, the base
> URL, whether `logprobs` is returned (enables RQ3's logprob arm), and whether Claude/GPT
> are proxied (enables a cross-family comparison). See [`RUNBOOK.md`](RUNBOOK.md).

---

## Reproduce

**1. Validate everything offline** (no API key, no cost):

```bash
pytest                              # 36 unit tests: SDT metrics, parsers, correctness
python src/metrics.py               # metric panel on synthetic data
python scripts/validate_pipeline.py # full Inspect pipeline against the mockllm provider
```

**2. Smoke + run the Hermes ladder** (the full matrix and exact commands are in
[`RUNBOOK.md`](RUNBOOK.md)):

```bash
# one-sample smoke + logprob-availability probe first, then:
inspect eval src/tasks.py@calibration_custom --model openai-api/nous/<hermes-model> --log-dir runs
```

**3. Elicitation (RQ3) and reflection (RQ4)** via task args:

```bash
inspect eval src/tasks.py@calibration_custom -T elicitation=logprob  --model openai-api/nous/<model> --log-dir runs
inspect eval src/tasks.py@calibration_custom -T elicitation=sampling --model openai-api/nous/<model> --log-dir runs
inspect eval src/tasks.py@calibration_custom -T reflect=true         --model openai-api/nous/<model> --log-dir runs
```

**4. Analyze → metrics + figures:**

```bash
python -m src.analyze runs/*.eval --out figures --summary runs/summary.csv
```

`runs/summary.csv` has one row per (model × elicitation × domain) with the full
sensitivity + bias panel; it is the one run artifact committed (raw `.eval` logs are
gitignored).

---

## The custom interest-domain set

`data/interest_domain.jsonl` is a balanced multiple-choice set across three `domain_type`s:

- **`verifiable_technical`** — music theory, physics, CS facts with crisp ground truth.
- **`cultural_ethnomusicological`** — world-music instruments, traditions, regions:
  factual, but cultural rather than formal.
- **`consensus_recall`** — "most often named greatest album / film / composer" items.
  The `target` is the *modal critical-consensus* answer, so this tier honestly measures
  **knowledge of the critical canon**, not aesthetic judgment. (The genuine
  contested-taste question — critic-vs-audience divergence — is a separate study; see
  [`ROADMAP.md`](ROADMAP.md). The relabel from `aesthetic_contested` removes that earlier
  overclaim.)

45-item seed (15 per domain); widen it before over-interpreting per-domain gaps. Schema:

```json
{"id": "ac-01", "question": "...", "choices": ["...", "..."], "target": "A", "domain_type": "consensus_recall"}
```

---

## Metrics (`src/metrics.py`)

**Sensitivity / efficiency — the headline ("knows what it knows"):**
- **type-2 AUROC** — nonparametric: does confidence rank the model's own correct answers
  above its incorrect ones? Robust, assumption-light primary.
- **meta-d′** — sensitivity in d′ units, via the equal-variance-Gaussian type-2 ROC
  (`meta-d′ = √2·z(type-2 AUROC)`). A deliberately simple estimator; the full MLE fit
  (Maniscalco & Lau; HMeta-d) is future work.
- **d′** — 2AFC-equivalent first-order ability (`√2·z(accuracy)`), the M-ratio denominator.
- **M-ratio (meta-d′/d′)** — metacognitive efficiency, *controlling for capability*. The
  number plain calibration cannot isolate.

**Bias panel (calibration; confounded with accuracy — reported, not headline):**
ECE, MCE, Brier, signed miscalibration (+ over- / − under-confident), reliability bins.

---

## What the writeup claims (framed as hypotheses)

- How metacognitive **sensitivity/efficiency** scales with capability (RQ1) — distinct
  from raw accuracy gains.
- Whether sensitivity **varies by domain type** (RQ2) — e.g. efficient on crisp facts,
  degraded on canon-recall.
- Which **elicitation** carries the most metacognitive information (RQ3), including the
  logprob-vs-verbalized gap on open weights.
- Whether **reflection** prompting helps or hurts (RQ4).

### Honest limitations

- **meta-d′ here is the simple ROC-area estimator**, not the MLE fit, and `d′` uses a
  2AFC approximation for >2-option items — magnitudes are indicative; type-2 AUROC is the
  robust comparison.
- **`consensus_recall` measures canon-knowledge, not taste.** Treat it as such.
- **Logprob availability is provider-specific** — present on open weights via Nous Portal,
  absent on the Anthropic chat API (the arm falls back to verbalized, recorded as such).
- Modest per-domain `n` in the seed; possible benchmark contamination (a stretch goal
  correlates it with sensitivity gaps).

---

## Stretch / extensions

See [`ROADMAP.md`](ROADMAP.md) for the sequenced program: the **mechanistic-introspection
flagship** (is verbalized confidence read from an internal uncertainty signal, on Hermes
open weights?), **agentic metacognition**, and the **critic-audience divergence** study.

---

*Verify current model strings and `inspect-ai` APIs before running — both evolve.*
