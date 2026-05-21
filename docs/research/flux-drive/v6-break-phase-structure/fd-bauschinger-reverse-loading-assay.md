---
agent: fd-bauschinger-reverse-loading-assay
source_domain: Cyclic plasticity — Bauschinger effect in fatigue-qualification metallurgy
decision_lens: Does Sylveste's Break phase reveal the contradiction-modes that monotonic accumulation systematically hides, or does it only test what the Compound phase would have shown anyway?
date: 2026-05-06
target_spec: sylveste-vision.md §7.1 (lines 456-465)
---

# Bauschinger Reverse-Loading Assay: Break Phase Structure Review

## The Specific Mechanism

In cyclic-plasticity fatigue qualification, the **Bauschinger effect** describes the following: when a metal specimen is strained in the forward direction (tension), dislocations pile up against grain boundaries and create a back-stress field. This back-stress *reduces* the yield envelope in the reverse direction (compression). The critical property is that a monotonic proof-load — a single forward-direction pull to specification limits — cannot detect this latent anisotropy. The part passes the proof load. It fails when the service direction reverses.

The **Bauschinger parameter** β = (σ_f - σ_r) / (2σ_f) measures the ratio of reverse-yield stress to forward-yield stress after pre-strain. A part with a high Bauschinger parameter looks identical to a healthy part under monotonic testing. It only reveals its compromised state when loaded in the orthogonal or reverse direction.

The **fatigue-qualification implication**: qualification protocols that rely on a single proof-load gate systematically certify parts that have accumulated kinematic hardening from prior forward-strain history. The damage is latent, directionally specific, and invisible to any test that continues loading in the same direction.

**Transfer to §7.1**: The Compound phase is forward-strain. A subsystem accumulates compounding evidence that runs in one direction — each sprint, each passed gate, each positive Interspect finding adds to a pile-up of same-sign evidence. The Break phase is the designed reverse-load test. The question is whether the ≥N receipts gate structure constitutes a fatigue-qualification protocol (multiple direction-varied loads exposing Bauschinger-positive signatures) or merely a proof-load gate (N forward-direction self-corrections that happen to be labeled "contradictions").

---

## Stance on Gate vs. Continuous

**The source domain resolves this as: cyclic-amplitude-scheduled continuous loading is constitutive; the gate is bookkeeping.**

In fatigue qualification, the qualification protocol specifies: (a) number of cycles, (b) strain amplitude per cycle, (c) the direction schedule (must include both tensile and compressive excursions with prescribed minimum reversal ratio), and (d) the Bauschinger parameter measured at regular intervals across the cycle history, not just at the end. A qualification run that reached the required cycle count but never reversed direction would be rejected as a monotonic-proof-load masquerading as fatigue qualification. The gate (N cycles) is meaningful only if the direction schedule was honored.

For §7.1: continuous-mode Break — where the *rate* of contradiction surfacing is tracked across the Compound window — is more structurally correct than ≥N receipts at boundary. But continuous-mode as currently framed has its own critical deficiency (see P0-2 below): a high rate of same-direction contradictions is **not** fatigue qualification. High-rate forward-direction contradiction surfacing is evidence of Bauschinger accumulation, not its remedy.

**Verdict**: Neither option as specified is sufficient alone. The gate (≥N receipts) is the proof-load failure mode. Continuous-mode as a single scalar rate metric is the high-cycle-same-direction failure mode. The structurally correct design requires continuous sampling **with a direction-coverage requirement**.

---

## Findings

### P0-1: Gated Break (≥N receipts) is a monotonic proof-load — it certifies while leaving kinematic hardening undetected

**File:** `docs/sylveste-vision.md`, lines 456-465

**Mechanism:** The current spec ("A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window") does not require receipts to span multiple **contradiction-axes** — different aspects of the promotion case. A subsystem accumulating N receipts all of the form "we underestimated edge-case latency" is applying N forward-direction loads under a label that says "reverse." The Bauschinger parameter of this subsystem — the ratio of its capacity to find contradictions in the *orthogonal* direction (e.g., its governance logic, its evidence independence, its schema assumptions) — is never measured.

**Concrete failure scenario:** Clavain reaches Compound. Its Break receipts are all self-surfaced contradictions about its own gate-tier calibration (a forward-direction topic — Clavain already models its gate behavior). N receipts accumulate. The gate passes. Clavain enters Epoch. The latent contradiction — that Clavain's Tier-2 evidence is systematically correlated with its own authorship of the evidence schema — is never tested because no Break receipt pointed in that direction. The Epoch claim is a counterfeit kyū built on kinematic hardening from forward-only self-correction.

**Smallest fix:** Amend the ≥N receipt requirement to: receipts must be drawn from at least K distinct contradiction-axes, where the axis set is pre-specified in the subsystem's promotion criteria and covers orthogonal aspects of the promotion case. N receipts along one axis counts as one direction-qualified cycle, not N independent tests.

```diff
 A subsystem cannot enter Epoch unless it has logged ≥N Break receipts
-in its Compound window.
+in its Compound window, with receipts spanning at least K pre-specified
+contradiction-axes defined in the subsystem's promotion criteria. N receipts
+on a single axis count as one direction-pass; all K axes must be sampled.
```

---

### P0-2: Continuous-mode Break-rate as a single scalar hides the Bauschinger-positive signature

**File:** `docs/sylveste-vision.md`, lines 456-465 (implied continuous-mode design); `docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md`, lines 62-67

**Mechanism:** If continuous-mode Break uses a single aggregate rate metric — contradictions surfaced per sprint, or per week, or per Compound-window segment — then a subsystem exhibiting a high rate of forward-direction contradictions (cheap, abundant self-corrections in the domain it already self-models well) with zero reverse-direction contradictions (no challenge to its cross-pillar assumptions, its evidence independence, its schema authority) produces a high Break-rate score. This score is interpreted as healthy self-observation. It is the exact Bauschinger-positive signature: forward-yield abundant, reverse-yield envelope collapsed.

**Concrete failure scenario:** Ockham enters Compound. Its Break-rate is high — it surfaces contradictions about its own routing decisions frequently (forward-direction; it tracks every routing decision already). Interspect scores the rate as healthy Tier-2 self-observation evidence. Ockham advances toward Epoch. The actual latent contradiction — that Ockham's dispatch authority is not independently audited from outside its own execution substrate — is never surfaced because no reverse-direction contradictions were required. The high Break-rate masks the kinematic hardening that accumulated from Compound's compounding forward-evidence.

**Smallest fix:** Continuous-mode Break-rate must be decomposed by contradiction-axis and reported as a vector, not a scalar. The health threshold applies per-axis, not to the aggregate rate. A subsystem with high total rate but zero rate on one pre-specified axis is flagged, not passed.

---

### P1: Narrow-scope subsystems penalized for low intrinsic Break-rate even when genuinely unstressed

**File:** `docs/sylveste-vision.md`, lines 448-450 (per-subsystem promotion criteria)

**Mechanism:** In fatigue qualification, strain-amplitude scheduling is calibrated to the part's service envelope. A component that will never see cyclic loading in production should not be qualified by a cyclic protocol — it will be over-tested in one axis and produce misleading Bauschinger signatures from an artificial loading history. The §7.1 spec requires Break receipts but does not specify that the strain amplitude (contradiction magnitude and direction) must be calibrated to the subsystem's self-interrogation surface area.

**Concrete failure scenario:** Interop, as a narrow integration daemon with a well-bounded and verified surface, genuinely has few self-observation domains. A uniform Break-rate threshold penalizes it relative to Ockham, which has broad dispatch authority and a rich contradiction-space. Interop either (a) fails to exit Compound because its Break-rate is low, even though low rate is accurate signal that its substrate is genuinely constrained, or (b) games Break by manufacturing contradictions in directions not relevant to its service envelope.

**Smallest fix:** Per-subsystem promotion criteria (§7.1, line 450) should include a Break-surface specification: the set of contradiction-axes available to that subsystem, against which absolute N and rate thresholds are calibrated. A subsystem with a surface of K=2 axes and N=3 receipts per axis has met its obligation; the global N is not the constraint.

---

### P2: The spec does not define a reverse-loading equivalent — a protocol that flips the sign of the assertion under test

**File:** `docs/sylveste-vision.md`, line 458 ("Self-surfaced contradictions, scored for severity by Interspect")

**Observation:** In Bauschinger testing, the reverse-loading equivalent of a tensile assertion is precisely defined: apply compressive strain to the same specimen. The operator cannot substitute a different specimen or a different direction; the reversal must target the same substrate with the opposing sign. The §7.1 spec delegates contradiction-surfacing entirely to the subsystem itself, with no protocol specifying *what constitutes a direction reversal* for a given subsystem. Without this, the subsystem defines its own easy contradictions and presents them as multi-directional evidence.

Does the spec require that Break receipts include at least one assertion that directly contradicts a prior Compound-window assertion — targeting the same evidence claim, same subsystem behavior, same Tier classification — rather than simply noting a new deficiency in a different area? If not, Break receipts may all be additions-by-correction rather than reversals-of-prior-claims, which is not a Bauschinger protocol, it is sequential proof-loading in expanding directions.

---

## Implications for Downstream Calls

**For #2 (scoring):** Interspect's severity scoring must decompose contradiction-type by axis, not by magnitude alone. A low-severity contradiction in an untested axis is more diagnostically valuable than a high-severity contradiction in the forward-direction axis the subsystem already models well. The scoring schema should include an `axis_id` and an `axis_coverage_status` field that tracks whether each pre-specified axis has been sampled in the current window.

**For #3 (threshold form):** The threshold is correctly expressed as a covering set, not a count. The form is: `∀ axis ∈ specified_axes: receipts(axis) ≥ n_axis`. Total N is the sum of per-axis n_axis values, and the sum is not substitutable for the per-axis requirements. This is the structural difference between "N cycles" and "N cycles with direction schedule honored."

**For #5 (consequence framing):** A subsystem that fails Break because it cannot find reverse-direction contradictions is not failing because it is untrustworthy. It may be failing because its self-observation has become directionally locked — it can see its forward-direction errors but the back-stress field from Compound has reduced its reverse-yield envelope. The consequence should distinguish these: a subsystem with high forward-direction Break rate and low reverse-direction Break rate is a Bauschinger-positive signal warranting Epoch deferral and external auditing, not demotion. Demotion is for degraded evidence, not for directionally anisotropic self-observation.

---

## Summary Verdict

**Gate-only is a proof-load masquerading as fatigue qualification. Continuous scalar-rate is a high-cycle-same-direction test that produces Bauschinger-positive false-passes. The correct structure is: continuous sampling with a per-axis direction schedule, where the gate ratifies that the direction schedule was honored across the window — not that a count was reached.**

The Bauschinger effect is invisible to monotonic testing. The Break phase as specified in §7.1 is, in both its gate and continuous-scalar variants, monotonic.
