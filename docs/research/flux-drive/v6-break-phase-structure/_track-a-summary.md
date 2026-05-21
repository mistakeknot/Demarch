# Track A Summary — v6 §7.1 Break Phase Structure

**Track:** Adjacent (operational/quality engineering domains)
**Decision under review:** Should Break be (a) discrete gate (≥N receipts at Compound→Epoch boundary) or (b) continuous-mode (sustained receipt rate as Tier-2 evidence)?
**Date:** 2026-05-06
**Source passage:** `docs/sylveste-vision.md:432-482` (Trust Lifecycle), particularly lines 456-465 (Break)
**Source brainstorm:** `docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md:25-27, 62-67`

---

## Convergence

**Hybrid, with continuous in-process monitoring primary and a count floor as a backstop.** All five Track A agents reject the gate-as-drafted; four explicitly recommend hybrid; one (runtime-assurance) recommends pure continuous on grounds that the property line 464-465 asserts is a liveness invariant the gate cannot enforce.

The convergent shape across all five lenses:

1. **Break receipt rate becomes a Tier-2 evidence stream during Compound** (not just at boundary), with per-subsystem-specified threshold form.
2. **A count floor survives** (≥N) but cannot be cleared by a late-window burst — an additional constraint (max-quiet-gap, temporal uniformity, control-chart Western-Electric run rules) blocks front-loading and end-of-window catch-up.
3. **Mid-Compound excursions fire as Tier-2 regression signals immediately** per §7.4, not at boundary evaluation.
4. **Threshold form is a multi-dimensional tuple** — not a single integer N — combining count, window, severity floor, and (per agent's vocabulary) sample-size calibration / control limits / liveness rolling-window / Goodhart coverage.

No agent recommends pure-gate-as-drafted. No agent recommends pure-continuous-without-floor.

---

## Highest-Confidence Finding

**The spec is internally inconsistent: line 459 (count gate) does not enforce the property line 464-465 asserts ("self-observation has gone blind").** This is flagged as P0 by fd-runtime-assurance-break-observability and reinforced by fd-sre-burn-rate-vs-gate's quiet-Compound-indistinguishability finding, fd-ml-canary's calculation that the gate's false-promotion rate is ≈19% at N=3 with realistic baseline rates, and fd-spc's incoming-inspection-antipattern framing.

This is not a question of preference between two valid designs. **The gate variant cannot deliver the design intent the same passage articulates.** Either line 459 must be replaced with a continuous/rolling mechanism, or line 464-465 is wishful prose to be deleted. Five independent operational-engineering lenses converge on this read.

---

## Surprises

1. **The §6 shadow-apprenticeship precedent is structurally identical to the Break problem, and four of five agents either explicitly cite it or describe a fix that recapitulates it without naming it.** I expected at most one or two to invoke it; the convergence suggests the existing Sylveste design canon already contains the right pattern and §7.1 should extend it rather than introduce a new one. (Surfaced explicitly by fd-progressive-delivery-shadow-eval; implicit in fd-sre's heartbeat proposal, fd-runtime-assurance's rolling-window monitor, and fd-spc's in-process control chart.)

2. **The brainstorm's explicit Goodhart-mitigation ("Interspect scores severity, not the pillar") is incomplete in a way none of the source documents flag.** fd-ml-canary's P1 #3 distinguishes *severity gaming* (which Interspect scoring addresses) from *generation gaming* (which it does not). The mitigation as drafted catches subsystems that file trivial receipts; it does not catch subsystems that learn Interspect's severity model and produce moderate-severity receipts on demand. This is a structural defect in the brainstorm-to-spec translation that requires a held-out validation slice analogous to §8.4.

3. **fd-spc-break-process-control surfaced a hysteresis-band-scoping question (P1 #3) that no other Track A agent saw.** When a subsystem fails Break and demotes, can it re-promote using mostly the same Compound window's evidence sans the Break failure? The hysteresis text at line 479-482 is ambiguous on whether it is evidence-scoped or trigger-scoped. This is a thrash-vector that survives even hybrid Break designs unless explicitly closed. Track A would not have caught this without the SPC lens.

4. **fd-runtime-assurance flagged Interspect's scoring latency as forcing a binary choice between filed-but-unscored receipts (real-time monitoring) and scored receipts (correct severity weighting, but lagged).** The architecture must explicitly handle this with retroactive re-evaluation — none of the source docs name the retroactive-evaluation requirement.

5. **No Track A agent argued for the gate variant on its own merits.** I expected at least one to defend gate's simplicity, audit-clarity, or implementation-cost. Instead all five frame the gate-as-drafted as definitively wrong-shape from their domain's standpoint. This is unusually strong convergence for an adjacent track.

---

## Per-Agent Verdicts (One-Line)

| Agent | Verdict |
|---|---|
| fd-sre-burn-rate-vs-gate | **Hybrid.** Count floor + max-quiet-gap + heartbeat liveness probe; gate alone cannot distinguish healthy-quiet from blind-quiet. |
| fd-progressive-delivery-shadow-eval | **Hybrid leaning continuous.** N is uncalibrated (P0); §6 shadow-apprenticeship is precedent the Break phase should extend, not contradict. |
| fd-runtime-assurance-break-observability | **Continuous (pure).** Line 464-465 asserts a liveness invariant; only a rolling-window monitor enforces it; gate is a category error. |
| fd-ml-canary-break-rate | **Continuous canary with anti-Goodhart guard.** Gate has ≈19% false-promotion at N=3; receipt-generation surface is gameable; needs §8.4-style held-out validation. |
| fd-spc-break-process-control | **In-process SPC.** Gate is incoming-inspection antipattern; control chart with LCL + Western Electric rules; spec lacks non-conformance disposition (P1) and hysteresis evidence-scoping (P1). |

---

## Recommendation to Synthesis

Track A's combined output strongly supports replacing the §7.1 lines 456-465 prose with a hybrid specification along the following shape:

1. **Threshold form as a tuple per subsystem** in promotion criteria: `{count_floor N, rolling_window W, min_severity S, baseline_rate r0, LCL, max_quiet_gap G, goodhart_coverage_floor C}`.
2. **Mid-Compound monitoring** fires Tier-2 regression signals on LCL excursion, max-quiet-gap exceedance, or rolling-window invariant violation — at time of violation, not at boundary.
3. **Boundary evaluation** retains a hard count floor (`count ≥ N`) plus a temporal-uniformity test (no front-loading) plus a Goodhart-coverage check (filed receipts cover Interspect-surfaced contradictions).
4. **Non-conformance disposition** explicit: window extension on first failure, demote on consecutive failures, evidence-scoped hysteresis on post-demotion re-promotion.
5. **Interspect roles** specified: severity scorer (post-hoc audit, async), control-chart maintainer (real-time), Goodhart auditor (held-out contradiction surfacing).
6. **Cross-link to §6 shadow-apprenticeship** as the architectural precedent; cross-reference §8.4 anti-Goodhart pattern; cross-reference §7.4 regression indicators as the integration point for mid-Compound signals.

Track B (orthogonal) and Track C (esoteric) reviews should be checked for whether they reinforce, complicate, or contradict this shape before locking the §7.1 rewrite.
