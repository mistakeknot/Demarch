# Roadmap — a metacognition program, sequenced

The calibration/sensitivity eval is the **measurement loop**: the credibility ship *and*
the target-finder for the real work. "Building metacognition" is a measure → understand →
build ladder, and the binding constraint is to ship one clean thing before starting the
next. These are **sequenced, not parallel.**

## Step 1 — Measure it right (this directory) — *in progress*

Metacognitive sensitivity/efficiency (meta-d′, M-ratio, type-2 AUROC), not just
calibration; Hermes ladder via Nous Portal; logprob arm where available; one figure
(sensitivity vs capability × domain) + a short writeup. **Done means done** — publish the
repo + note, then move on. See `README.md` / `RUNBOOK.md`.

## Step 2 — Mechanistic introspection (the flagship) — *next, after Step 1 ships*

**Full design sketch: [`../introspection-probe/DESIGN.md`](../introspection-probe/DESIGN.md).**

**Question:** is a model's verbalized confidence *read from* an internal uncertainty
representation, or confabulated after the answer?

- **Why now:** open weights (Hermes, via Nous) are largely wasted on a behavioral eval but
  are *required* to look inside — this is the real payoff of the provider choice.
- **Targets:** the items Step 1 flags where confidence and correctness dissociate (high
  confidence + wrong, low confidence + right) are the highest-signal probes.
- **Method:** probe for an uncertainty direction / signal (linear probes on residual
  stream; `nnsight` / `transformer-lens`); test whether self-reported confidence is
  predictable from it; then *intervene* (steer the signal) and see if stated confidence
  and metacognitive sensitivity move — the first step from *measuring* to *building*.
- **Behavioral bridge already in place:** the logprob-vs-verbalized gap (RQ3) is the
  cheap, no-interp precursor — does token-level uncertainty match the stated number?
- **Tooling:** add `transformer-lens` / `nnsight` (deferred from the eval on purpose);
  needs a GPU rental for the larger Hermes sizes.
- **Audience:** Anthropic's introspection/interpretability lane.

## Step 3 — Agentic metacognition — *parked*

Self-monitoring control loops: an agent that acts on self-assessed competence —
abstain / escalate / ask-for-help / route — instead of answering at fixed confidence.
Best Sylveste + Nous + comparative-advantage fit (this repo already has routing-confidence
and "calibration loop" machinery to plug into), and the most genuine "building," but the
fuzziest to make publishable quickly. Revisit once Step 2 yields a usable uncertainty
signal to drive the policy.

## Parked idea — Critic-audience divergence study

The genuine contested-taste instrument (vs the `consensus_recall` tier, which only measures
canon-knowledge). Uses **real, published dual reference distributions** — Metacritic/RT
Tomatometer-vs-Audience, AOTY critic-vs-user — so no invented ground truth.

- **Instrument:** pairwise *"did critics or audiences score X higher?"* + confidence;
  ground truth = `sign(critic − audience)`; `|gap|` is a built-in difficulty axis. Headline:
  does confidence track the gap, or stay flat-high near genuine ties (false precision)?
- **Second finding (media ecology):** when they diverge, which consensus does the model
  encode — institutional-critical (literate canon) or popular-audience (vernacular)?
- **Domains:** film first (best-documented divergence, cleanest data, SME), AOTY music as
  domain 2 → cross-media consensus-encoding is a free comparison.
- **Build notes:** stratify by fame × recency × |gap| so contamination becomes a *measured
  axis* (memorized vs inferred), not a threat; pin a snapshot date; ToS-safe citeable
  source. Lives at a sibling `experiments/critic-audience-divergence/` with a pre-registered
  DESIGN.md — authored *after* Step 1 ships.

## Out of scope (for now)

- The Hermes **Agent framework** is for Step 3 / the P2 Atropos direction — *not* for
  measuring metacognition, where an agent harness would confound the model's own signal.
- Other model directions from the brief (broad interpretability, value-transmission) stay
  sequenced behind this program.
