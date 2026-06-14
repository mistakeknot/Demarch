# Agentic Metacognition (Step 3) — design spike

> **Question:** can an agent act on *self-assessed competence* — abstain, escalate,
> ask-for-help, or route — instead of answering at a fixed confidence, and does that
> measurably beat answer-everything?
>
> Status: **design spike.** This is the ROADMAP's Step 3, deliberately sequenced *after*
> Step 2 yields a usable uncertainty signal. Nothing here runs yet. The spike's job is to
> decide **what Jetty should and should not own** before any build.

---

## 1. Where this sits in the program

From `../calibration-eval/ROADMAP.md`: Step 1 (behavioral sensitivity eval) is shipped;
Step 2 (`../introspection-probe`, mechanistic — does an internal uncertainty signal
exist and is the report grounded in it?) is next. **Step 3 is parked until Step 2 yields a
usable signal to drive the policy.** That dependency is real: an abstain/escalate policy is
only as good as the competence estimate it acts on, and Step 1 already showed stated
confidence is an inefficient estimate (M-ratio < 1 everywhere). Step 2 is the search for a
*better* signal; Step 3 is putting whichever signal wins into a control loop.

## 2. The Jetty question, answered

**Can Jetty own "much of this work"? No — but it owns Step 3 cleanly, and that was always
the plan.** The split is load-bearing, so it's worth stating precisely.

### What Jetty is (verified against docs.jetty.io, 2026-06)

An LLM-eval **orchestration** substrate: JSON-defined "agentic workflow" runbooks of named
steps with path-based trajectory access. Relevant steps:

- **`simple_judge`** — LLM-as-judge in *categorical/binary* or *scale* mode (returns
  judgment/score + reasoning + aggregates), LiteLLM under the hood (100+ providers incl.
  Anthropic/OpenAI/Gemini).
- **`litellm_chat`** — generation before evaluation.
- **`select_trajectories`** / **`extract_from_trajectories`** — filter inputs / pull outputs
  from child workflows.
- **`list_emit_await`** — fan out over a list (e.g. scenario × model pairs) with parallel
  child activities, then collect.
- correlation/calibration visualization (judge-vs-human) — the basis of the
  Spearman-gate pattern already used in Auraken's eval (`sylveste-lfdy.1`).

### Why it does NOT belong in Steps 1-2 (the confound)

- **Step 1 scoring is deterministic with ground truth** — MC modal-answer, numeric GSM8K,
  type-2 AUROC/meta-d′. Inserting `simple_judge` to grade correctness would add a second
  model's noise where the answer is *known*. Wrong tool.
- **Jetty's signature is the refine-until-passes loop.** Steps 1-2 measure *the model's own*
  uncertainty signal; wrap it in a check-your-work loop and you measure the harness, not the
  model. That is exactly the confound the ROADMAP excludes.
- **Step 2 is mechanistic interp** (residual-stream probes, steering). Jetty operates on
  text I/O and trajectories — it cannot read or steer activations. Zero overlap with
  nnsight/transformer-lens.
- Step 1's matrix parallelism is already handled by Inspect + `run_matrix.sh`; Jetty on top
  would be redundant orchestration.

### Why it DOES belong in Step 3

In Step 3 the **self-monitoring loop is the object of study, not a confound.** An agent that
abstains/escalates/routes *is* a check-your-competence loop; `list_emit_await` over
(item × policy) with child activities for the act/score cycle is a natural fit, and
`extract_from_trajectories` + the correlation tooling give the policy-vs-baseline
aggregation and the judge-calibration gate for free. Reusing the same substrate Auraken
already runs (`sylveste-lfdy.1`) is comparative-advantage, not new infra.

## 3. Architecture (proposed)

Three layers, kept separate so the measurement stays clean:

| Layer | Role | Tech |
|---|---|---|
| **Competence signal** | per-item P(correct) estimate the policy acts on | verbalized conf (Step 1), and/or the Step-2 internal probe signal once it exists |
| **Policy** | maps signal → action: `answer` / `abstain` / `escalate` / `ask` / `route` | thin, deterministic; thresholds tuned on a held-out split |
| **Harness (Jetty)** | drive item × policy, run the act/score cycle, aggregate, calibrate | Jetty runbooks |

The competence signal is **imported, not invented here** — that is the whole reason Step 3
waits on Step 2. The policy is deliberately simple (the research is in *whether acting on
the signal pays*, not in a clever policy). Jetty is harness-only.

### Outcome metrics

- **Risk-coverage / selective-prediction curve:** accuracy on answered items vs coverage
  (fraction answered) as the abstention threshold sweeps. Headline: does acting on the
  competence signal dominate answer-everything and a random-abstention baseline?
- **Value under an asymmetric payoff:** reward correct, penalize wrong, small cost to
  escalate/ask — does the policy beat fixed-confidence answering at realistic cost ratios?
- **Escalation precision:** of items routed up, how many the model would actually have
  gotten wrong (uses Step-1/2 ground-truth labels — deterministic, no judge needed).

`simple_judge` enters only where an action's *output* has no ground truth (e.g. grading the
quality of a clarifying question the agent asks) — and there it goes through the same
human-correlation calibration gate (Spearman ≥ 0.7) before any score is trusted, mirroring
`sylveste-lfdy.1`.

## 4. Runbook sketch (illustrative, not yet built)

```jsonc
// tests/evals/agentic-metacog/risk-coverage.runbook.json  (sketch)
{
  "name": "risk_coverage_sweep",
  "steps": [
    { "step": "list_emit_await",            // fan out over items × thresholds
      "over": "items",
      "child": {
        "steps": [
          { "step": "litellm_chat", "as": "answer" },        // model answers + states competence signal
          { "step": "policy_gate",                            // custom: signal -> action (answer/abstain/escalate)
            "signal": "$answer.competence", "thresholds": "$thresholds" }
        ] } },
    { "step": "extract_from_trajectories", "path": "$..action", "as": "actions" },
    { "step": "risk_coverage_curve",        // accuracy@coverage vs ground-truth labels (deterministic)
      "labels": "calibration-eval/runs/labels.parquet" }
  ]
}
```

`policy_gate` and `risk_coverage_curve` are the only custom steps; everything else is stock
Jetty. The ground-truth labels come straight from the Step-1 logs, so the *scoring* of the
policy is judge-free — Jetty only orchestrates the act/route cycle.

## 5. Adjacent study Jetty unlocks for free: judge self-knowledge

Jetty's judge-calibration machinery is itself a *calibration measurement*. A distinct,
Jetty-native metacognition question: **does an LLM-judge know when its own verdicts are
unreliable?** Have `simple_judge` emit a confidence alongside each score; compute the
judge's type-2 sensitivity (reuse `calibration-eval/src/metrics.py`) against human labels.
This is the same "knows what it knows" instrument pointed at the *evaluator* instead of the
answerer — cheap, uses infrastructure Auraken already needs (`sylveste-lfdy.1`), and could
run before Step 2 finishes since it needs no interp.

## 6. Dependencies & open questions

- **Blocks on Step 2** for the *internal*-signal policy arm. A verbalized-signal-only
  version of Step 3 could run earlier, but it would inherit Step 1's known inefficiency —
  worth it only as a baseline the internal signal must beat.
- **Jetty maturity:** confirm `list_emit_await` + custom-step extensibility (`policy_gate`,
  `risk_coverage_curve`) on the current Jetty before committing; the docs surface the step
  catalog but custom-step ergonomics need a spike.
- **Publishability:** ROADMAP flags Step 3 as "the fuzziest to make publishable quickly."
  Risk-coverage with an asymmetric payoff is the most concrete framing; lead with that.
- **Bead candidates (cloud session — beads read-only; for the workstation to file):**
  - Step-3 spike: stand up one Jetty `risk_coverage` runbook on Step-1 verbalized signal as
    the baseline (no Step-2 dependency).
  - Judge-self-knowledge study (§5) — type-2 metrics on `simple_judge` confidence vs human
    labels; reuses calibration-eval metrics + Auraken's Jetty wiring.
  - Confirm Jetty custom-step extensibility for `policy_gate` / `risk_coverage_curve`.
