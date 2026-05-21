---
agent: fd-postmarket-surveillance
source_domain: Pharmaceutical post-market surveillance — EU Risk Management Plans (RMP); FDA REMS; ICH E2E pharmacovigilance planning; 21 CFR 314.81 post-marketing reporting
decision_lens: NDA/BLA approval gate (permits market entry) vs ongoing pharmacovigilance signal detection (monitors whether the approved risk-benefit profile remains valid under real-world conditions)
reviewed: 2026-05-06
target_passage: sylveste-vision.md §7.1 lines 456–465 (Break phase spec)
---

# Post-Market Surveillance Review — §7.1 Break Phase Structure

## Stance on Gate vs Continuous

**Continuous-mode is structurally necessary; gate-only is a pre-1962 drug approval model.**

The 1962 Kefauver-Harris Amendment to the Federal Food, Drug, and Cosmetic Act was triggered by thalidomide. The pre-1962 model required demonstration of safety sufficient to earn market entry — an approval gate. What the thalidomide disaster revealed was that gate passage did not predict post-market behavior: a drug safe in controlled pre-approval conditions could exhibit entirely different risk profiles in heterogeneous real-world populations, over longer time horizons, in combinations with other drugs that were never part of the approval trial.

The post-1962 framework separated two obligations that the pre-1962 model had collapsed into one: the approval gate (does the evidence at this moment warrant market entry?) and post-market surveillance (does the evidence as it accumulates in the real world continue to warrant continued presence?). Crucially, in the modern pharmacovigilance framework, approval is not the end of the evidence obligation — it is the beginning of the surveillance obligation.

The Break phase as specified — "a subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window" — is the approval gate. It is the NDA/BLA: sufficient evidence to permit entry to Epoch. What the spec does not address is the post-market surveillance equivalent: what evidence obligation does the subsystem carry after Epoch entry? Does it continue to surface contradictions? At what rate? If the risk-benefit profile of its self-observation deteriorates post-Epoch, what is the detection mechanism?

If Break is a one-time gate that unlocks Epoch, and Epoch carries no Break-equivalent surveillance requirement, the design has replicated the pre-1962 model: prove it once, operate indefinitely.

---

## P0 Finding — Break Passage Grants Epoch Entry Without Post-Epoch Contradiction-Surfacing Obligation

**Severity: P0**

**Location:** `docs/sylveste-vision.md` lines 456–477 — the Break phase spec (lines 456–465) and the Epoch phase spec (lines 466–470) are specified as sequential phases with no overlap in monitoring obligation. Nothing in the Epoch spec requires continued surfacing of contradictions.

**The failure scenario:** Subsystem reaches Epoch. The Break gate was passed — N receipts were logged during Compound. In Epoch, the subsystem retains its maturity tier and must "re-demonstrate at that tier under new conditions" (lines 469–470) when an Epoch trigger fires. But between Epoch entry and the next Epoch trigger, there is no requirement to continue surfacing contradictions. The self-observation mechanism that earned the Break attestation can atrophy silently. When the next Epoch trigger fires (e.g., a major model API change, §7.11), the subsystem is evaluated for re-demonstration — but the re-demonstration criteria are not specified as including a Break-equivalent requirement.

In pharmacovigilance terms: the drug is approved (NDA passed), enters the market (Epoch), and is subject to re-assessment if a major new condition triggers a label update (Epoch trigger = major change requiring re-demonstration). But between NDA approval and a label-change trigger, the drug is subject to periodic safety reporting, signal detection, and potential REMS obligations — none of which are equivalent to "wait for a trigger." The Break spec, applied only pre-Epoch, mirrors the pre-1962 model.

**What breaks:** A subsystem in Epoch has its trust preserved as long as "evidence remains fresh (per §7.3 decay model) and regression indicators are absent" (line 454). But the decay model (§7.3) is not specified in this passage, and "regression indicators" are not defined as including "absence of contradiction-surfacing." This means a subsystem in Epoch can maintain its trust level indefinitely without ever surfacing a contradiction again — as long as its positive evidence doesn't decay and no explicit regression indicator fires. The self-observation blindness that Break was designed to prevent can develop fully in Epoch, undetected.

**Smallest viable fix:** Add a post-Epoch surveillance clause to §7.1's Epoch phase spec (after line 470): "A subsystem in Epoch carries a post-Epoch surveillance obligation: it must continue to surface Break-equivalent contradiction receipts at the rate established during its Compound window. Break-silence anomalies in Epoch are Tier-2 evidence of degraded self-observation health and are factored into the §7.3 trust decay calculation. An Epoch trigger does not reset the surveillance obligation; it resets the re-demonstration threshold." This is the pharmacovigilance pattern: approval is followed by periodic safety reporting, not silence.

---

## P1 Finding — No Minimum-Detectable-Signal Specification for the Break Counting Instrument

**Severity: P1**

**Location:** `docs/sylveste-vision.md` lines 458–460: "Self-surfaced contradictions, scored for severity by Interspect rather than by the pillar surfacing them, recorded as evidence in their own right."

**The failure scenario:** The Break spec requires ≥N receipts, scored by Interspect. But the spec does not establish what Interspect's minimum detectable signal is — i.e., what is the smallest contradiction that Interspect can reliably detect and score? Without this, the system cannot distinguish between two conditions:

1. A subsystem that genuinely has no material contradictions to surface (rare but possible at high maturity).
2. A subsystem that has genuine contradictions but whose self-observation mechanism lacks the sensitivity to detect them, or whose interaction with Interspect's scoring pipeline means that low-severity contradictions fall below the detection threshold.

In pharmacovigilance, this is the signal-detection calibration problem. The FDA's MedWatch system and the EU's EudraVigilance database are required to demonstrate, via periodic signal-detection performance assessments, that they can detect a safety signal of defined magnitude with defined sensitivity and specificity. A pharmacovigilance system that has not been calibrated against a known signal population cannot be trusted to report absence-of-signal as genuine health.

The Break spec has no equivalent calibration requirement. If Interspect's scoring pipeline is tuned (accidentally or by design) to score most contradictions below the Break receipt qualification threshold, the system will surface very few Break receipts — not because the subsystem is healthy, but because the detection instrument is miscalibrated.

**What breaks:** N Break receipts are treated as evidence that the subsystem's self-observation is functioning. But N receipts from an uncalibrated instrument are not evidence of self-observation health — they are evidence that N contradictions exceeded the instrument's threshold. If the threshold is set too high, a genuinely self-aware subsystem surfaces 2 receipts and fails the gate; if set too low, a blind subsystem surfaces 20 receipts of trivial severity and passes. The "scored by Interspect rather than by the pillar" independence (line 459) addresses gaming risk but not calibration risk.

**Smallest viable fix:** Add to §7.1 Break spec: "Interspect's Break receipt scoring must include a periodic calibration check — a synthetic contradiction of defined severity is submitted to the scoring pipeline and the output verified against the expected severity score. The calibration check result is recorded as Tier-2 evidence of Interspect's scoring health. A failed calibration check suspends Break gate evaluation for the affected subsystems until the pipeline is recalibrated." This is the MedWatch signal-detection validation equivalent: you must demonstrate the instrument works before trusting what it reports.

---

## P2 Finding — Break Receipts Not Isolated by Compound Window; Lifetime Aggregation Inflates Apparent Self-Observation History

**Severity: P2**

**Location:** §7.1 does not specify how Break receipts are stored or aggregated across Compound windows. The §7.3 decay model is referenced but not described in this passage.

**The failure scenario:** A subsystem that was actively self-observing in M2 Compound (3 epochs ago) accumulated 15 Break receipts. In its current M3 Compound window, it has surfaced 2 receipts — below the N = 5 threshold. If the Break receipt ledger is lifetime-cumulative and the decay model does not expire old receipts, the subsystem's apparent Break history looks robust even though its current self-observation is degraded.

In pharmacovigilance, the Periodic Safety Update Report (PSUR / PBRER under ICH E2D) is explicitly scoped to the reporting interval — typically the International Birth Date to the present period. Prior periods are not aggregated into the current assessment without explicit annotation. The point is to assess the current signal rate against the current evidence base, not against a lifetime accumulation that may reflect a product profile that no longer exists.

The EU RMP requires per-period benefit-risk assessments precisely because a drug that was safe in 2015 may have developed new safety signals in 2025, and aggregating the two periods' data would dilute the new signal into an apparently acceptable overall profile.

**Smallest viable fix:** Require that Break receipt counts for gate evaluation be computed per-Compound-window only, with explicit window boundaries: "Break gate evaluation uses only receipts logged within the current Compound window. Receipts from prior Compound windows are retained in the subsystem's evidence ledger but are not counted toward the ≥N threshold for the current window." This is additive: it constrains evaluation scope without deleting historical data.

---

## Implications for Downstream Calls

**Call #2 (scoring):** The minimum-detectable-signal gap (P1) must be resolved before scoring can be meaningful. Break receipts carry Tier-2 weight only if the scoring instrument is calibrated; uncalibrated scoring output is closer to Tier-3. The scoring call should surface the calibration requirement as a precondition for Tier-2 classification.

**Call #3 (threshold form):** N should be evaluated per-Compound-window (P2), not lifetime-cumulative. If the threshold form call adopts a rate-per-sub-period structure (consistent with nuclear and CCM recommendations), the per-window scoping is implicit. If the gate form is retained, explicit window scoping is required.

**Call #5 (consequence framing):** The post-Epoch surveillance obligation (P0) implies a new consequence class: post-Epoch Break-silence anomaly. This is distinct from a Demote trigger — it should trigger an expedited Epoch re-demonstration, not a maturity level drop. The pharmacovigilance equivalent is a Type II variation to the EU label (significant change, expedited review) rather than a full marketing authorization withdrawal. The consequence framing should preserve this distinction.

---

## Cross-References to Track B

- **fd-nuclear-maintenance-rule:** Both disciplines converge on the front-loaded compliance problem (P0 in nuclear, underlying mechanism of P2 here). Nuclear frames it as a rolling window requirement; pharmacovigilance frames it as per-window isolation. The recommendation is consistent: break the lifetime-cumulative count into window-scoped evaluation.
- **fd-continuous-controls-monitoring:** The CCM zero-receipt floor and the pharmacovigilance "absence of signal is not evidence of health" are the same operational principle. CCM's control-silent escalation ladder is the financial-domain operationalization of the pharmacovigilance "investigate before concluding absence."
- **fd-atc-surveillance:** The ATC "radar handoff at Epoch transition" directly addresses the P0 here: at Epoch entry, the surveillance obligation should transfer explicitly to a post-Epoch monitoring regime, not be inherited silently from the Break gate result. ATC's handoff protocol is the procedural equivalent of the pharmacovigilance post-approval surveillance program initiation.

---

## Summary Verdict

The Break phase as specified is an NDA/BLA approval gate. This is necessary but not sufficient. The post-1962 pharmacovigilance framework requires that approval be followed by ongoing surveillance — and this obligation is non-negotiable for high-risk products (REMS-eligible) regardless of how clean the approval evidence was. The Sylveste equivalent: Break receipts unlock Epoch entry (gate retained), but Epoch itself must carry a post-Epoch surveillance obligation (Break-equivalent monitoring continues at the rate established during Compound). The minimum-detectable-signal gap in Interspect's scoring pipeline is the most technically specific finding: an uncalibrated counting instrument produces receipt counts that carry less evidential weight than the spec currently implies.

**Verdict: Continuous — gate is the entry event, not the end of the evidence obligation. Epoch requires explicit post-market surveillance equivalent.**
