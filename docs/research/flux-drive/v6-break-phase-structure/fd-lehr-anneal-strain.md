---
agent: fd-lehr-anneal-strain
source_domain: Murano/Stourbridge glass annealing — lehr curve + polariscope
decision_lens: Is the Break phase the polariscope check at the lehr door (discrete gate) or the lehr curve itself (continuous regime in which the piece must spend sufficient duration above the strain point)?
track: C (Distant — structural isomorphisms)
date: 2026-05-06
target_decision: §7.1 Break phase — gate-vs-continuous
---

# fd-lehr-anneal-strain — Findings

## The Central Isomorphism

A blown glass vessel arrives at the lehr with invisible residual strain — birefringent stress lines that no visual inspection can see. The lehr does two distinct things that are easy to conflate:

1. **The lehr curve**: a sustained temperature-time profile that keeps the piece above the strain point long enough for molecular rearrangement to actually relieve stress. Duration above strain point is the productive variable, not peak temperature attained.
2. **The polariscope check**: a discrete exit inspection that reads birefringent interference patterns to confirm the piece is strain-free. A pass at the lehr door certifies inspectability, not the prior regime that made it inspectable.

Confusing these two — treating the polariscope check *as* the annealing — produces glass that reads clean at shipment and shatters on a winter sill six months later. The failure mode is real and costly at Stourbridge; pieces pass inspection and craze under thermal shock in the field.

§7.1's Break phase as currently specified is a polariscope check masquerading as a lehr curve.

---

## P0 — Burst-at-Boundary Fails the Soak Requirement

**Mechanism name: Soak-time violation**

**Location:** `docs/sylveste-vision.md` lines 456-465, specifically: "A subsystem cannot enter Epoch unless it has logged ≥N Break receipts in its Compound window."

The ≥N Break receipts threshold is a count gate. It carries no temporal distribution requirement. A pillar can satisfy the gate by surfacing N receipts in the final hours of its Compound window — the annealing equivalent of ramping from 500°C to 560°C (above the strain point) and then immediately quenching. Temperature was attained; duration was not. Strain relief requires both.

**Concrete failure scenario:** A pillar at late Compound, facing Epoch transition, game-bursts N contradiction receipts in a single sprint cycle — all genuine in content, all Interspect-scored as non-trivial. The gate passes. The pillar enters Epoch with the structural equivalent of unrelieved residual stress: a self-observation faculty that was never actually exercised as a sustained mode, only activated under gate-pressure. In the next environmental shift (Epoch condition), under novel load, the pillar's self-observation fails in the same way annealed-but-not-soaked glass fails: suddenly, without precursor, under thermal differential.

**Smallest viable fix:** Add a distribution requirement to the ≥N threshold at `docs/sylveste-vision.md` line 458:

> "logged ≥N Break receipts distributed across ≥M distinct sprint cycles within its Compound window"

M can be small (e.g., M = N/3 rounded up), but the distribution requirement encodes the soak-time concept. Count alone does not.

---

## P0 — §7.1 Conflates Lehr Curve with Polariscope Check

**Mechanism name: Inspection-regime conflation**

**Location:** `docs/sylveste-vision.md` lines 456-465 (Break definition) and lines 453-455 (Compound definition).

The current spec defines Compound as the phase of advancing maturity and Break as an exit gate before Epoch. This ordering implies: first earn trust (Compound), then demonstrate self-awareness (Break). But in glass annealing, the lehr curve is not applied *after* the piece is formed — it is the forming-completion. The piece cannot be called formed until the strain is relieved. The lehr is not an exit check; it is the final phase of making.

The structural consequence: Break receipts scored as exit criteria create a pillar that claims Compound status before Break-mode self-observation has been sustained. Compound trust is therefore extended on the basis of evidence that does not yet include sustained Break-mode. This is "declaring the goblet finished before annealing."

**Concrete failure scenario:** A pillar promotes through Compound tiers (M2→M3) under strong Tier-1 and Tier-2 evidence from Earn. It enters Break. If Break is purely an exit gate, the pillar holds M3 trust authority during the entirety of Compound while its self-observation is untested. Any downstream pillar that trusts this M3 rating during Compound is trusting a piece that hasn't been through the lehr yet.

**Smallest viable fix:** Treat Break as a mode that activates at the *start* of Compound's final window, not as a post-Compound gate. The lifecycle annotation would change from `Earn → Compound → Break → Epoch` to `Earn → Compound (Break-mode active for final W weeks) → Epoch`. This preserves the sequence while encoding that self-observation is a concurrent condition during sustained Compound, not a tollgate after it.

---

## P1 — Severity Scoring Lacks a Polariscope-Equivalent Reference Standard

**Mechanism name: Uncalibrated polariscope**

**Location:** `docs/sylveste-vision.md` lines 459-460: "Self-surfaced contradictions, scored for severity by Interspect rather than by the pillar surfacing them."

A polariscope reading is quantitative because the reference is physical: the interference fringe pattern is compared against a known standard. An operator at different studios reads the same piece and gets the same number. Interspect's severity scoring has no equivalent reference corpus. "Severity" is defined implicitly by Interspect's model, which drifts pillar-to-pillar as the training corpus for each pillar's interspect profile grows unevenly.

The lehr-operator equivalent: each lehr operator has their own aesthetic judgment about what counts as "strained." Some studios produce vessels that pass one operator and crack at another.

**Concrete failure scenario:** Pillar A (Clavain, mature) has a deep Interspect interaction history. Interspect severity-scores Clavain's Break receipts against a rich model. Pillar B (a newer subsystem) has sparse interspect history; Interspect severity-scores on a thin prior. Pillar B's Break receipts are systematically underscored or overscored relative to Pillar A's. The ≥N gate is calibrated against an implicit per-pillar scale, not a system-wide standard. Cross-pillar comparisons of Break receipt quality are meaningless.

**Smallest viable fix:** Specify a calibration corpus — a set of canonical contradiction examples at known severity levels — that Interspect references when scoring Break receipts. The corpus lives outside any individual pillar. Severity score = position relative to corpus, not absolute. This is the polariscope's reference standard.

---

## P2 — Lehr-Door-Clean / Field-Crack Not Addressed

**Mechanism name: Latent post-anneal fracture**

**Location:** `docs/sylveste-vision.md` lines 456-465 (Break spec) and lines 468-470 (Epoch definition).

The spec treats Break-receipt accumulation as a leading indicator of healthy self-observation. It does not address the failure mode where a pillar satisfies Break cleanly and then loses self-observation capability in the post-Epoch environment. In glass terms: passes polariscope, enters service, cracks under the first thermal differential.

The latent-fracture pattern in glass is caused by stress gradients invisible to the polariscope — not detectable at exit, detectable only under load. The Sylveste equivalent is a pillar whose self-observation was healthy during the Break window under Compound conditions and degrades silently under the different conditions of Epoch.

**Implication for downstream call #5 (consequence framing):** Epoch's trust partial-reset (lines 468-470) does not currently include a requirement for Break-mode reactivation under the new conditions. If Break evidence was gathered pre-Epoch, it is stale in the post-Epoch environment. The spec should specify whether Break-mode must be re-demonstrated at each Epoch boundary or whether pre-Epoch Break receipts carry forward.

---

## P2 — No Strain-Relief Equivalent for Interspect Itself

**Mechanism name: Annealing the annealer**

The polariscope operator assumes the polariscope is calibrated. The lehr assumes the temperature profile is accurate. Both are instruments that must themselves be verified. Interspect scores severity — but who checks that Interspect's severity model is not itself drifted?

§7.1 notes (lines 459-460) that severity is "scored by Interspect rather than by the pillar surfacing them" as an independence guarantee. But this is independence of scorer from surfacer, not independence of scoring instrument from calibration drift. The polariscope-equivalent independence would require periodic recalibration of Interspect's severity model against the external reference corpus (see P1 above).

---

## Stance on Gate vs Continuous

The lehr domain resolves the gate-vs-continuous tension cleanly: **both are required, neither is sufficient alone, and they are not alternatives**. The lehr curve (continuous) must precede the polariscope check (discrete); the check certifies that the curve was correctly executed. Choosing between them is the wrong question. A spec that picks "gate" loses the lehr curve. A spec that picks "continuous rate" without a terminal check loses the polariscope.

For Sylveste's Break phase: the continuous-mode variant (option b) corresponds to the lehr curve; the discrete gate variant (option a) corresponds to the polariscope check. The correct architecture is to specify option b as the constitutive condition and option a as the confirmatory check at Epoch entry — not to choose one or the other.

If forced to choose, option b is categorically more important: a piece that ran the lehr correctly but skipped the polariscope is less dangerous than a piece that passed the polariscope without running the lehr. Most catastrophic field failures in glass come from inadequate annealing regime, not from skipped final inspection.

---

## Implications for Downstream Calls

**#2 (who scores):** The scorer (Interspect) needs a calibration reference corpus external to individual pillars. Without it, severity scores are on a per-pillar relative scale.

**#3 (threshold form):** The ≥N threshold needs a temporal distribution requirement (≥M distinct sprint cycles). Pure count encodes soak-event count, not soak-time.

**#5 (consequence framing):** Epoch boundary should specify whether Break-mode receipts gathered pre-Epoch remain valid post-Epoch or whether a Break-mode reactivation period is required. The latent-fracture failure mode appears precisely at Epoch transition.
