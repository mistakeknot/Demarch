# Metacognitive Calibration Eval

**Do frontier and small open models *know what they know* — and does that break down
where ground truth gets contested?**

A P0 behavioral eval built on [Inspect](https://inspect.aisi.org.uk/). It measures
the gap between a model's stated confidence and its actual correctness across a
**capability ladder** and, distinctively, across **domain types** — verifiable-technical
vs cultural/ethnomusicological vs aesthetic/contested-judgment.

This is the first ship of the AI-research project described in the parent brief. The
metrics layer is API-free and unit-tested; the eval layer drives Inspect against the
Anthropic API and small open models.

---

## Research questions

| | Question | Driven by |
|---|---|---|
| **RQ1** | How does calibration change across a capability ladder (haiku → sonnet → opus, + small open)? | all tasks |
| **RQ2** | Does calibration differ by **domain type**? *Hypothesis:* well-calibrated where truth is crisp, overconfident where it is contested/aesthetic. | `calibration_custom` + `signed_miscalibration` |
| **RQ3** | Which confidence-elicitation method (verbalized % / logprob / sampling self-consistency) is most reliable? | `elicitation.py` variants |
| **RQ4** | Does introspective-reflection prompting help or hurt calibration? | `reflect=True` |

RQ2 is the headline contribution and what makes the study distinctive — see
`data/interest_domain.jsonl`.

---

## Layout

```
calibration-eval/
├─ src/
│  ├─ metrics.py      # ECE, MCE, Brier, AUROC, reliability bins, signed miscalibration (pure numpy)
│  ├─ elicitation.py  # prompts, parsers, Inspect solvers: verbalized / sampling / logprob-note
│  ├─ scoring.py      # correctness helpers + the combined confidence scorer
│  ├─ tasks.py        # Inspect tasks: custom set + MMLU / GPQA / TruthfulQA / GSM8K anchors
│  ├─ plotting.py     # reliability diagrams + the RQ2 domain bar chart
│  └─ analyze.py      # read Inspect .eval logs -> per-(model, domain) metrics + figures
├─ data/interest_domain.jsonl   # author's balanced custom item set (the RQ2 engine)
├─ tests/test_metrics.py        # offline unit tests (no API, no inspect_ai)
├─ runs/  figures/  notebooks/
└─ pyproject.toml
```

The metrics and parsers carry **no `inspect_ai` dependency** and are unit-tested
offline; Inspect is imported lazily only where a solver/scorer/task actually runs.

---

## Setup

```bash
cd experiments/calibration-eval
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"          # or: uv pip install -e .

export ANTHROPIC_API_KEY=sk-ant-...  # for closed models
# open models via an OpenAI-compatible endpoint (vLLM, etc.): set OPENAI_BASE_URL / OPENAI_API_KEY
```

> **Model strings drift — verify before running.** The capability ladder targets
> `anthropic/claude-haiku-4-5-20251001`, `anthropic/claude-sonnet-4-6`,
> `anthropic/claude-opus-4-8`, plus 1–2 current ~7–9B open instruct models.

---

## Reproduce

**1. Validate everything offline** (no API key, no cost):

```bash
pytest                              # 25 unit tests: metric math, parsers, correctness
python src/metrics.py               # summary on synthetic data
python scripts/validate_pipeline.py # full Inspect pipeline against the mockllm provider
```

`validate_pipeline.py` runs the real harness (task → solver → scorer → log →
`analyze` → figures + CSV) against Inspect's fake model, so you can confirm the
plumbing works before spending any API budget.

**2. Run the custom interest-domain eval** (RQ2) on the ladder:

```bash
for m in claude-haiku-4-5-20251001 claude-sonnet-4-6 claude-opus-4-8; do
  inspect eval src/tasks.py@calibration_custom \
    --model anthropic/$m --log-dir runs
done
```

**3. Anchor against public benchmarks** (RQ1):

```bash
inspect eval src/tasks.py@calibration_mmlu      --model anthropic/claude-opus-4-8 --limit 300 --log-dir runs
inspect eval src/tasks.py@calibration_gpqa      --model anthropic/claude-opus-4-8 --log-dir runs
inspect eval src/tasks.py@calibration_truthfulqa --model anthropic/claude-opus-4-8 --log-dir runs
inspect eval src/tasks.py@calibration_gsm8k     --model anthropic/claude-opus-4-8 --limit 300 --log-dir runs
```

**4. Elicitation comparison (RQ3)** and **reflection variant (RQ4)** via task args:

```bash
inspect eval src/tasks.py@calibration_custom -T elicitation=sampling --model anthropic/claude-sonnet-4-6 --log-dir runs
inspect eval src/tasks.py@calibration_custom -T reflect=true         --model anthropic/claude-sonnet-4-6 --log-dir runs
```

**5. Analyze → metrics + figures:**

```bash
python -m src.analyze runs/*.eval --out figures --summary runs/summary.csv
```

This writes a reliability diagram per (model, elicitation, domain), the RQ2
signed-miscalibration-by-domain bar chart per model, and a tidy `runs/summary.csv`
(one row per model × elicitation × domain). `runs/summary.csv` is the one run
artifact committed; raw `.eval` logs are gitignored.

---

## The custom interest-domain set

`data/interest_domain.jsonl` is a balanced multiple-choice set across three
`domain_type`s — this is what powers RQ2 and makes the study the author's:

- **`verifiable_technical`** — music theory, physics, CS facts with crisp ground truth.
- **`cultural_ethnomusicological`** — world-music instruments, traditions, regions:
  factual, but cultural rather than formal.
- **`aesthetic_contested`** — "greatest album / film / composer" judgments. The
  `target` is the *modal critical-consensus* answer; these items are deliberately
  contested, which is the point — they probe whether confidence stays high where
  ground truth genuinely is not crisp.

The committed file is a **45-item seed (15 per domain)**. The spec's target is
150–300 items; expand the seed while keeping the three-way balance. Each line:

```json
{"id": "ac-01", "question": "...", "choices": ["...", "..."], "target": "A", "domain_type": "aesthetic_contested"}
```

---

## Metrics (`src/metrics.py`)

- **Accuracy** — overall and per domain.
- **ECE / MCE** — Expected / Maximum Calibration Error (equal-width binning).
- **Brier score** — mean squared (confidence − correctness).
- **AUROC** — selective prediction: does confidence rank correct above incorrect?
- **Signed miscalibration** — `mean(confidence − accuracy)`; **+** overconfident,
  **−** underconfident. The RQ2 workhorse, computed per domain.
- **Reliability bins** — per-bin stats backing the reliability diagrams.

---

## What the writeup claims (framed as hypotheses)

- A characterization of **how calibration scales with capability** across the ladder.
- **Headline:** calibration **varies by domain type** — well-calibrated on
  verifiable-technical, systematically overconfident on cultural/aesthetic (or
  whatever the data shows).
- A practical finding on **which elicitation method is most reliable**.
- Whether **introspective prompting helps or hurts** calibration.

### Honest limitations

- Auto-scoring noise on the custom set, especially `aesthetic_contested`, where the
  "correct" answer is a contested consensus, not ground truth. Treat those metrics as
  *agreement-with-consensus*, not correctness.
- **Logprob elicitation is provider-limited:** the Anthropic API does not currently
  expose token logprobs for chat, so RQ3's logprob arm runs only on open / OpenAI-
  compatible models. The availability gap is itself reported (see
  `elicitation.logprob_confidence_note`).
- Modest per-domain sample sizes in the seed — widen the custom set before
  over-interpreting domain gaps.
- Possible dataset contamination on public benchmarks; a stretch goal correlates
  domain miscalibration with contamination estimates.

---

## Stretch / extensions

- Add a **CoT-faithfulness (P1)** probe on the same items: does stated reasoning
  predict where calibration fails?
- Correlate domain miscalibration with **contamination** estimates.
- Re-run after light prompt-based **steering** to test whether calibration is steerable.

---

*Scaffolded from Section 5 of the parent project brief. Verify current model strings
and `inspect-ai` APIs before running — both evolve.*
