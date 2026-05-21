---
agent: fd-nuclear-maintenance-rule
source_domain: Nuclear power plant maintenance — 10 CFR 50.65 (Maintenance Rule)
decision_lens: a-category vs b-category monitoring classification; rolling-window functional failure rate vs discrete inspection gate
reviewed: 2026-05-06
target_passage: sylveste-vision.md §7.1 lines 456–465 (Break phase spec)
---

# Nuclear Maintenance Rule Review — §7.1 Break Phase Structure

## Stance on Gate vs Continuous

**Continuous-mode (a-category) is required, with a tiered carve-out for low-criticality subsystems.**

The Maintenance Rule (10 CFR 50.65) established a-category monitoring precisely because the nuclear industry learned that periodic inspection gates — pre-approved inspection intervals, single-point pass/fail re-qualifications — were insufficient for safety-critical systems that could degrade silently between gates. A system that passed its last inspection is not a system that is currently performing its intended function. The rule mandates that for any system in a-category, the licensee must establish performance or condition monitoring criteria and monitor against them on a rolling window, not wait for a scheduled gate.

The Break phase as currently specified in §7.1 — "a subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window" — is structurally b-category: a count threshold at a boundary. It produces a binary gate result, not a rate signal. Whether the subsystem's self-observation mechanism is currently operating is not visible from the gate result; only whether it operated well enough, at some point during Compound, to accumulate N receipts.

The post-Three-Mile-Island lesson that motivated the Maintenance Rule was precisely this: the plant passed every scheduled inspection. The degradation was not episodic — it was continuous and below the resolution of the inspection grid.

---

## P0 Finding — No Rolling Window; Lifetime-Cumulative Count Enables Front-Loaded Compliance

**Severity: P0**

**Location:** `docs/sylveste-vision.md` lines 457–459: "A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window."

**The failure scenario:** A subsystem that is actively self-monitoring at the start of Compound accumulates N Break receipts in the first two sprints. For the remaining 10 sprints of the Compound window, the self-observation mechanism goes effectively silent — no further contradictions are surfaced. Under the current spec, this subsystem passes the Break gate at the end of Compound. The gate result carries no information about the silence in sprints 3–12. The subsystem enters Epoch carrying a Break clearance that was earned by behavior it no longer exhibits.

In Maintenance Rule terms: this is a system that was in a-category compliance in January and has been trending toward failure since March, but the next scheduled gate is in December. The gap between gate results is where silent degradation lives.

**What breaks:** Epoch inherits a subsystem whose self-observation health was real at the start of Compound and may be entirely absent by the end of it. The trust lifecycle's explicit goal — "a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind" (§7.1 lines 464–465) — is precisely the failure mode the gate cannot detect.

**Smallest viable fix:** Require that ≥N Break receipts be distributed across the Compound window with a defined minimum cadence — e.g., at least one qualifying receipt per observation sub-period (per sprint, or per N-day rolling window). The spec text change at line 459 would read: "...logged ≥N Break receipts distributed across the Compound window at no less than one qualifying receipt per [observation sub-period]."

This mirrors the Maintenance Rule's requirement that performance criteria be monitored continuously, not evaluated at gate time against a lifetime accumulation.

---

## P1 Finding — Break Threshold N Is Not Pre-Specified Before Compound Opens

**Severity: P1**

**Location:** §7.1 does not specify where or when N is published relative to the Compound window opening. The spec says subsystems "publish promotion criteria" (lines 439–441) but does not explicitly require that the Break goal (N and the observation window sub-period) be locked before Compound evidence begins accumulating.

**The failure scenario:** A subsystem enters Compound. After 8 sprints of evidence accumulation, Ockham or a governance agent reviews the evidence base and sets N = 4 (a value the subsystem has already satisfied). The gate was never pre-specified; it was calibrated post-hoc to match the data. This is not a Break signal — it is a retroactive compliance certification.

In Maintenance Rule terms: this is equivalent to a licensee setting their performance criteria after observing 12 months of operational data, then declaring the criteria met. The NRC explicitly prohibits post-hoc goal-setting for a-category systems because it destroys the independence of the monitoring signal.

**What breaks:** Interspect's severity scoring of Break receipts cannot be independent (§7.1 line 459: "scored for severity by Interspect rather than by the pillar surfacing them") if the threshold N is calibrated against the population of receipts Interspect has already scored. The scoring independence and the threshold independence are coupled.

**Smallest viable fix:** Add to §7.1's promotion criteria publication requirement (line 440): "Break goals — minimum receipt count N, minimum cadence requirement, and observation sub-period definition — must be published in the per-subsystem promotion criteria document before the Compound window opens."

---

## P2 Finding — Uniform Gate Across Criticality Tiers

**Severity: P2**

**Location:** §7.1 specifies a single ≥N Break gate structure without distinguishing between M1/M2 subsystems (low-criticality, b-category may be appropriate) and M3+ subsystems (governance, routing, kernel — high-criticality, a-category is warranted).

The Maintenance Rule distinguishes systems by safety function: those whose failure would directly challenge reactor safety are a-category by default; others may be b-category unless performance history warrants reclassification. The critical insight is that the classification is driven by consequence, not by inspection convenience.

Ockham (dispatch authority), Interspect (audit authority), and Intercore (kernel integrity) are Sylveste's equivalent of safety-critical systems. A ≥N gate that was designed for a lower-criticality subsystem is not automatically appropriate for these. High-criticality subsystems warrant a-category treatment regardless of their inspection history.

**Smallest viable fix:** Add a subsystem criticality classification to §7.1's promotion criteria framework — analogous to the Maintenance Rule's safety-function classification — such that M3+ governance and routing subsystems are placed in a-category Break monitoring by default, with a documented rationale required to exempt any such subsystem to b-category gate treatment.

---

## Implications for Downstream Calls

**Call #2 (scoring):** If Break receipt severity scoring is performed by Interspect against a pre-specified threshold, the a-category/b-category distinction maps cleanly to Tier-2 vs Tier-3 evidence weight. A rolling-rate Break signal with pre-specified goals earns Tier-2 weight; a post-hoc gate count does not.

**Call #3 (threshold form):** N should be expressed as a rate (receipts per observation sub-period) rather than a lifetime count, with a minimum observation sub-period defined per criticality tier. High-criticality subsystems should have shorter sub-periods (more frequent minimum-cadence checks).

**Call #5 (consequence framing):** Demotion from Epoch triggered by a Break-silence anomaly detected by continuous monitoring is a structurally different event than demotion triggered by a gate failure. The former can be caught early and demoted before a full Epoch cycle; the latter only catches the failure at the next scheduled gate. §7.4 (decay model) and §7.9 (demotion propagation) should distinguish between early-continuous-detection demotions and gate-failure demotions — the former carry less compounding damage because they are caught earlier.

---

## Cross-References to Track B

- **fd-continuous-controls-monitoring:** The CCM "control-silence anomaly" (zero exceptions flagged as suspicious rather than healthy) is the financial-domain equivalent of this P0 finding. Both point to the same structural gap: the current spec has no zero-receipt floor that fires when Break receipts drop to zero post-accumulation.
- **fd-postmarket-surveillance:** The pharmacovigilance "false-negative risk" — a subsystem that has genuine contradictions but surfaces zero receipts — is a direct analog to the a-category concern about a system that was functional in January and is failing silently in March.
- **fd-atc-surveillance:** The ATC "clearance without surveillance loop" P0 maps to this finding's core claim: a gate result authorizes entry but does not maintain situational awareness about post-entry corridor behavior.

---

## Summary Verdict

The current Break spec is b-category by structure: it produces a one-time gate result. For low-criticality subsystems (M1–M2), this may be acceptable. For high-criticality subsystems (M3+ governance, routing, kernel), 10 CFR 50.65 operational practice requires a-category continuous monitoring — rolling window, pre-specified goals, cadence requirement, and a zero-receipt floor that triggers re-classification. The spec's own stated intent ("a subsystem that cannot find contradictions to surface is a subsystem whose self-observation has gone blind") is a continuous-mode claim. The implementation should match the intent.

**Verdict: Continuous (a-category) for M3+ subsystems; tiered gate acceptable for M1–M2 with explicit criticality classification.**
