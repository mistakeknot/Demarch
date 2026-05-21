---
track: D (Esoteric — maximum semantic distance)
date: 2026-05-06
decision_question: "§7.1 Break phase structure: discrete gate (≥N receipts) vs. continuous-mode (sustained rate as Tier-2 evidence)"
agents:
  - fd-bauschinger-reverse-loading-assay
  - fd-coptic-synaxis-correction-discipline
  - fd-khipukamayuq-knot-witness-protocol
---

# Track D Summary: Break Phase Structure Review

## Convergence Verdict

**Hybrid — with an explicit directed dependency that neither the gate-only nor the continuous-only option captures.**

All three agents converge on rejecting both pure-gate and pure-continuous-scalar variants, but the convergence is not a simple "do both." The structural argument shared across all three source domains is:

> One component is constitutive (it produces the evidence substrate). The other is ratifying (it converts the substrate into canonical record). The ratifying event cannot substitute for the constitutive practice, and constitutive practice that is never ratified decays into informal memory. The dependency is directed and non-reversible.

Each domain names this dependency using its own mechanism and its own vocabulary for the failure mode of confusing the two. The failure modes are not symmetric: the two errors (empty ratification, unratified practice) produce different epistemic deficits and require different remedies.

---

## Per-Agent Verdicts

**fd-bauschinger-reverse-loading-assay:** Gate-only is a monotonic proof-load that certifies while leaving kinematic hardening undetected; continuous scalar rate is high-cycle same-direction loading that produces Bauschinger-positive false-passes. The correct structure requires continuous sampling with a per-axis direction schedule, and a gate that ratifies direction-coverage — not count alone. Verdict: **hybrid with direction-axis covering-set requirement**.

**fd-coptic-synaxis-correction-discipline:** Gate-only is the void synaxis (ceremony with no preceding practice); continuous-only with no formalization event is unsealed practice (observation that decays into folklore). The correct structure is continuous fellow-witness practice (temporally distributed receipts) followed by periodic hebdomadarius-presided Break Synaxis events that seal receipts into canonical evidence, followed by the Epoch gate ratifying the series of sealed records. Verdict: **hybrid with three-layer temporal structure and explicit directed dependency**.

**fd-khipukamayuq-knot-witness-protocol:** Gate-only is a summons-recital with no standing chain-of-custody trace (legally void in tawantinsuyu adjudication); aggregate rate metric erases the per-event trace structure. The correct structure requires per-event Break receipts timestamped against specific Compound-window transitions (the standing trace), with the gate ratifying the existing trace. Verdict: **hybrid where gate is legally valid only if standing trace exists prior to it**.

---

## Most Surprising Structural Insight

**The Bauschinger direction-axis finding opens a design direction no other track would reach.**

The Coptic and khipu agents both converge on a temporal-distribution requirement (receipts must be spread across the Compound window, tied to specific events, not batched at boundary). This is significant and actionable, but it is a structural refinement that Tracks A/B/C likely identified through symmetry and hysteresis arguments.

The Bauschinger finding is genuinely novel: **a high Break-rate in the forward direction is not health evidence — it is the diagnostic signature of a subsystem on the verge of reverse-direction failure.** The kinematic hardening mechanism means that abundant same-type contradictions suppress the yield envelope in orthogonal directions. A subsystem that surfaces many contradictions about, say, its routing decisions may have zero capacity to surface contradictions about its evidence-independence assumptions — not because it is healthy in that direction but because Compound's forward-strain accumulation has stiffened it.

This implies that **high Break-rate can be a demotion signal, not a promotion signal** — specifically when the high rate is directionally concentrated on the same axes the Compound phase already exercised. No other track would derive this from first principles because no other track models the inverse relationship between forward-strain history and reverse-yield capacity. The design direction this opens: Break receipt scoring must track axis-coverage as a distinct metric from receipt count, and Interspect must flag directionally concentrated Break patterns as Bauschinger-positive rather than treating high count as health.

---

## Qualitative Difference from Tracks A/B/C

Track D contributed two findings that are qualitatively distinct from what familiar-analogy tracks would produce:

1. **The direction-axis covering-set requirement** (Bauschinger): the gate is not "≥N receipts" but "≥n_i receipts per axis i, for all pre-specified axes." N receipts along one axis counts as one direction-qualified cycle, not N independent tests. This is a structural constraint on the *shape* of the evidence set, not its size. Tracks A/B/C would likely recommend "diverse" contradictions without specifying the formal covering-set structure.

2. **The legal-standing distinction between constitutive and ratifying evidence** (khipu): the Epoch gate is not valid if it constitutes its own evidence. The gate's legal standing derives from the standing trace that precedes it. This is not a sequencing recommendation — it is a claim about the ontological category of the evidence. A receipt submitted at the gate boundary to satisfy ≥N is a different kind of evidence than a receipt timestamped against the event it describes, even if both receipts are textually identical. No SRE, Noh, or cathedral analogy makes this distinction with the same precision.

The Coptic finding (void synaxis + unsealed practice as symmetric failure modes) likely overlaps with what Track B (periodic/episodic analyses) would produce, stated in different vocabulary. Its unique contribution is the three-role separation: Interspect-as-fellow-witness, Interspect-as-hebdomadarius, and the canonical prohibition on self-correction — which refines the already-known evidence-independence debt into a Break-specific protocol requirement.

---

## Actionable Design Recommendations Unique to Track D

1. **Break receipt schema must include `contradiction_axis_id`** — a pre-specified axis drawn from the subsystem's promotion criteria axis-set. The ≥N gate condition is replaced by a covering-set condition: `∀ axis ∈ specified_axes: receipts(axis) ≥ n_axis`. (Bauschinger)

2. **High directionally-concentrated Break-rate is a Bauschinger-positive flag, not a health signal.** Interspect must compute an axis-concentration metric alongside Break-rate and treat concentration above threshold as a potential demotion trigger, not a promotion accelerant. (Bauschinger)

3. **Break receipts must carry `parent_event_id` referencing the Compound-window event (sprint, gate pass, transition) they describe, and must be submitted before the subsequent event begins.** Receipts submitted at the Epoch boundary without event association are retrospective context, not standing-trace evidence. (Khipu)

4. **The Epoch gate checks chain-of-custody completeness — every Compound-window transition above a significance threshold must have at least one standing-trace Break receipt.** A gate that finds gaps in the per-event trace defers Epoch until gaps are remediated; it does not substitute batch receipts for the missing per-event records. (Khipu)

5. **Continuous-mode Break requires periodic formalization events (Break Synaxis) within the Compound window** — not only at the Epoch boundary. The Epoch gate ratifies the series of sealed synaxis records. The cadence of Break Synaxis events is a per-subsystem parameter in promotion criteria, calibrated to the subsystem's transition density. (Coptic)

6. **Interspect's fellow-witness role and hebdomadarius role must be explicitly separated in the Break protocol.** The authority-independence of the scoring instance must be verified before a receipt enters the standing trace with full weight. Where Interspect shares an authority chain with the pillar whose contradiction it is scoring, the receipt is marked as self-corrected-equivalent and routed to an independent scorer. (Coptic)
