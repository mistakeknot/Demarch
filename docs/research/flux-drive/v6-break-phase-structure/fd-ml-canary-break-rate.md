# fd-ml-canary-break-rate — Findings

**Decision lens:** ML platform engineering. Holdout-gate (boundary, evaluate on held-out set) vs production canary (continuous, monitor live metrics during partial rollout). Diagnostic question: how many bad models pass the gate before the error rate becomes detectable? Is the evaluation set at the boundary representative of the deployment distribution? Is the metric gameable by a model that learned the gate's structure?

**Stance:** **Continuous canary preferred; gate is gameable and statistically underpowered as drafted.** The §7.1 spec at `docs/sylveste-vision.md:456-465` describes a holdout-style gate with two ML-pathology-prone defects: (1) N is an arbitrary integer with no false-promotion rate calculation, and (2) the evaluation surface — Break receipts scored by Interspect — is gameable in a way that is structurally identical to reward-hacking in RLHF. The fix is to treat Break-receipt rate as a continuous canary signal during Compound, with an explicit anti-Goodhart guard analogous to the §8.4 held-out task set.

---

## P0 — Arbitrary N has unbounded false-promotion rate; degraded self-observers pass through noise

**Location:** `docs/sylveste-vision.md:459` ("≥N Break receipts in its Compound window") — N is named and never grounded in a probability calculation.

**Failure scenario (with numbers):** Suppose the true Break-surface rate of a healthy subsystem is `p_healthy = 0.30` per evaluable opportunity (sprint, evidence event, etc.) and a degraded self-observer has `p_bad = 0.05`. A 30-opportunity Compound window with N=3:
- Healthy observer: E[count] = 9. P(count ≥ 3) ≈ 0.999.
- Degraded observer: E[count] = 1.5. P(count ≥ 3) = 1 − P(0) − P(1) − P(2) ≈ 1 − 0.21 − 0.34 − 0.26 ≈ 0.19.

**The gate's false-promotion rate is ≈19% for this degradation profile.** Across a platform with dozens of subsystems cycling Compound→Epoch repeatedly over years, this compounds: the long-run fraction of Epoch subsystems with degraded self-observation cannot be bounded.

For comparison, ML model deployment gates routinely require false-promotion rates ≤ 1% (often ≤ 0.1% for safety-critical paths). A 19% false-promotion rate would be rejected at code-review on any production model-promotion pipeline.

**Why P0:** The vision document's central claim is "evidence that compounds" (line 14). A trust gate with an unbounded false-promotion rate compounds the wrong evidence: degraded self-observers in Epoch generate confident-looking promotion artifacts, which become Tier-2 evidence (line 443) for *other* subsystems' promotion criteria, which propagates the error. ML pipelines call this "label leakage from a contaminated upstream dataset"; in Sylveste's terms it is silent corruption of the trust corpus. Drop everything.

**Smallest viable fix:** Reformulate N as a derived quantity:

> `N = ceil(BinomialInverseCDF(1 - false_promotion_target, opportunity_count, p_bad_threshold))`

with `false_promotion_target` (e.g., 0.01), `opportunity_count` (per Compound window), and `p_bad_threshold` (the degradation rate the architecture commits to detecting) declared in promotion criteria per §7.1 line 449-450. Subsystems that cannot specify these declare them unknown and N defaults to a conservative high value until baselines are observed.

---

## P1 — Front-loaded receipts cannot be distinguished from sustained self-observation

**Location:** `docs/sylveste-vision.md:459` (count over full Compound window, no temporal-distribution constraint).

**Failure scenario:** Subsystem A files all N Break receipts in the first 10% of its Compound window (e.g., during an early integration burst), then experiences silent observation failure for the remaining 90%. Subsystem B files ~N/30 receipts in each of the 30 sprints of its Compound window — sustained self-observation throughout. Under the gate, both pass with identical scores. The gate cannot distinguish front-loaded from sustained.

This is the ML-domain analogue of training-distribution shift: A's evaluation distribution (early-Compound activity) differs systematically from its Epoch-operation distribution (post-promotion behavior). B's evaluation distribution is representative of Epoch behavior. The gate certifies them identically despite radically different generalization probabilities.

**Why P1:** The brainstorm source is explicit at `docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md:25` — "skipping the 'ha' break-open phase produces a counterfeit kyū." A front-loaded receipt pattern is structurally equivalent to skipping the ha phase: a brief burst of contradiction-surfacing followed by quiet build-toward-promotion. The gate certifies the counterfeit kyū. Required to exit v6 quality gate because the spec's stated design intent (line 461-465) is operationally violated by the gate's count semantics.

**Smallest viable fix:** Add a holdout-style evaluation: gate counts only receipts from the **last K% of the Compound window** (e.g., last 30%), or equivalently, requires the temporal distribution of receipts to satisfy a uniformity test (Kolmogorov-Smirnov against uniform-over-window) above a threshold p-value. Either fix denies the front-loaded pattern.

---

## P1 — Break-receipt-as-evidence is gameable: Goodhart on the contradiction surface

**Location:** `docs/sylveste-vision.md:457-458` (subsystem files Break receipts; Interspect scores severity) — combined with line 459's count threshold creates a learnable optimization surface.

**Failure scenario:** A subsystem (or its operators, or the AI agent driving its evolution) observes that Interspect scores certain receipt patterns as severity-passing. Optimization toward those patterns becomes implicit: file receipts that look like contradictions to Interspect's scorer, regardless of whether they reflect genuine self-observation. This is reward hacking. The subsystem learns to *generate* receipts rather than to *find* contradictions. Receipt count rises; actual self-observation health does not.

The brainstorm flagged this risk explicitly: line 67 of the source — "pillars game Break by surfacing trivial contradictions. Mitigation: contradiction-severity scored by Interspect, not the pillar." But severity-scoring by Interspect addresses the *severity* dimension of gaming, not the *generation* dimension. A subsystem that learns Interspect's severity model can produce moderate-severity receipts on demand. The mitigation is incomplete.

**Why P1:** Reward hacking compounds the same way label leakage does: gameable evidence flows into the corpus, contaminates downstream Tier-2 aggregation per §7.2, propagates to other subsystems' promotion criteria. Required to exit quality gate.

**Smallest viable fix:** Apply the §8.4 anti-Goodhart pattern (held-out task set for the routing system) to the Break phase. Break receipts must include a held-out validation slice: a subset of contradictions that Interspect surfaces from its own analysis (not the subsystem's filing) and matches against the subsystem's filed receipts. A subsystem whose filed receipts diverge from Interspect-surfaced contradictions has a Goodhart score; high Goodhart score blocks Epoch independent of count.

Add to §7.1 around line 458:

> Break receipts are subject to held-out validation: Interspect independently surfaces contradictions from the subsystem's evidence stream and computes a coverage score against the subsystem's filed receipts. A coverage score below threshold C indicates filing-pattern divergence from genuine self-observation and blocks Epoch advancement, with C per-subsystem-specified in promotion criteria.

---

## P1 — Distribution shift between Compound (evaluation) and Epoch (deployment) is unaddressed

**Location:** `docs/sylveste-vision.md:467-470` (Epoch represents environmental shift) interacting with `:456-465` (Break gate evaluated under Compound conditions).

**Failure scenario:** Compound-window evidence is collected under one operational envelope. Epoch begins with explicit acknowledgment that conditions have changed (line 468-470). The Break gate's certification — "≥N receipts in Compound window" — was computed against the prior envelope. The subsystem enters Epoch with a Break-validity claim that does not generalize to its new operating conditions.

**ML analogue:** Training-test distribution shift. The boundary evaluation (Break gate) used data from a distribution that the post-promotion deployment will not match. Standard ML practice: re-validate after distribution shift detected.

**Why P1:** Inconsistency between Epoch's "conditions have changed" semantics (line 468-470) and the gate's reliance on prior-conditions evidence.

**Smallest viable fix:** Add to §7.1 line 469-470: "Break receipts from the prior Compound window do not transfer through Epoch. The post-Epoch Compound window must satisfy the Break invariant freshly under new conditions."

---

## P2 — Continuous-rate granularity is unspecified; cross-subsystem comparison broken

**Location:** Hypothetical continuous-mode variant of `docs/sylveste-vision.md:456-465`. The continuous-mode variant in the question's framing does not specify rate units (receipts/sprint, receipts/week, receipts/Compound-window-fraction).

**Failure scenario:** Subsystem A has 4-week Compound windows; B has 12-week. A files 1 receipt/week → rate = 1.0/week or 4/window or 0.083/window-fraction depending on unit. B files 1 receipt/2-weeks → 0.5/week or 6/window or 0.083/window-fraction. Tier-2 evidence aggregation per §7.2 cannot meaningfully combine these without a normalized unit.

**Smallest viable fix:** Specify rate as `receipts / unit_evidence_event` (events per Compound window are the natural denominator since they normalize subsystem activity volume). Document in §7.1 alongside the continuous-mode specification.

---

## Implications for downstream calls

- **#2 (who scores):** Interspect must score severity AND surface its own held-out contradictions for coverage validation (per P1 #3 above). Two roles: severity grader and Goodhart auditor. The architecture must specify both — current spec at line 457-458 only names the severity role.
- **#3 (threshold form):** Threshold cannot be a static integer. Must be a derived quantity from `{p_healthy, p_bad, opportunity_count, false_promotion_target}` per P0. Plus a temporal-distribution constraint per P1 #1. Plus a Goodhart-coverage threshold per P1 #2. Per-subsystem tuned in promotion criteria.
- **#5 (consequence framing):** Three failure modes, three consequences:
  - Count below derived N: hard-fail, no Epoch.
  - Front-loaded distribution: soft-fail, Compound window extends with new evidence required.
  - Goodhart coverage below threshold: investigation trigger; subsystem flagged for Interspect review of self-observation channel before Epoch consideration.

## Cross-references / anti-overlap

- The progressive-delivery agent (**fd-progressive-delivery-shadow-eval**) is likely landing on similar sample-size-calculation findings. We agree on the false-promotion-rate calculation framing. My contribution beyond theirs: explicit Goodhart/reward-hacking analysis on the receipt-generation surface (P1 #3), which is ML-domain-specific.
- I am leaving SLO/burn-rate alert ladder framing to **fd-sre-burn-rate-vs-gate**. Their lens names the operational "wake someone at 3 AM" scenario for late-burst behavior; my P1 #1 covers the same data pattern from a training-distribution-shift angle.
- I am leaving liveness-vs-safety property characterization to **fd-runtime-assurance-break-observability**. My findings are about the *signal quality* and *gameability* of the evaluation; theirs are about the *property shape* of what is being evaluated.
- I am leaving SPC control-chart and inspection-gaming framing to **fd-spc-break-process-control**. Their P1 on filing-gaming will overlap with my P1 #3 on Goodhart; the SPC framing emphasizes process-level gaming behavior, mine emphasizes the ML-style learnable-surface gaming. Both are right; cite both in synthesis.
