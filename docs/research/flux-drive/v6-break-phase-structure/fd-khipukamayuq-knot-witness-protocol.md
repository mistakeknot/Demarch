---
agent: fd-khipukamayuq-knot-witness-protocol
source_domain: Inka tawantinsuyu khipukamayuq tribute-record verification — knot-by-knot in-unison handover reading vs. kuraka-summons recital
decision_lens: Does the Break protocol maintain a standing knot-by-knot verification trace that exists prior to and independent of the gate event, so that the gate (when triggered) ratifies an existing record rather than constituting it?
date: 2026-05-06
target_spec: sylveste-vision.md §7.1 (lines 456-465)
---

# Khipukamayuq Knot-Witness Protocol: Break Phase Structure Review

## The Specific Mechanism

In the Inka tawantinsuyu tribute and census administration, the khipukamayuq (knot-keeper) maintained cord records of extraordinary fidelity across extended custody periods. The verification practice is distinguished by two entirely separate protocols, each with its own evidential standing:

1. **The handover reading** (knot-by-knot in-unison trace): when a khipu passed between custodians — when a cord was handed from one khipukamayuq to another, from a village to the provincial level, or from one administrative period to the next — **both** the outgoing and incoming khipukamayuq read the cord aloud together, knot by knot, cord by cord. Divergences between their simultaneous recitations were flagged immediately. This practice was continuous and occurred at every transition event, regardless of the cord's status or the administrative hierarchy. Its function was to establish a **standing chain-of-custody trace**: a running record of who had verified what, at which transition, with what observed state.

2. **The summons-recital** (kuraka or tukuyrikuq presided): periodically, a senior authority (kuraka, or the Inka's own inspector, the tukuyrikuq — "he who sees all") would summon the khipukamayuq and require a recital of the cord's contents. This was a high-ceremony, rare event, conducted before a witnessing authority. It was the gate event — the formal certification of the cord's state. But its epistemic validity was entirely grounded in the standing handover trace: a khipukamayuq reciting before the kuraka was reporting the verified state of a cord whose verification history was traceable back through the in-unison readings at each prior handover.

**The critical chain-of-custody principle**: the summons-recital cannot legally substitute for the standing trace. A khipukamayuq who appeared before the kuraka with no standing trace — no record of in-unison handover readings — was reciting from memory, not from the cord. This was considered a disqualifying failure. The cord's contents as recited from memory had no standing as administrative testimony because there was no trail proving the recitation tracked the actual knot state rather than the khipukamayuq's belief about the knot state. The standing trace is what gives the summons-recital its authority.

**The in-unison reading principle**: the handover reading requires two voices. A single khipukamayuq reading alone does not constitute a valid handover — divergence between two independent readers is the detection mechanism. A solo reading cannot detect the failure mode where the reader's expectation substitutes for the actual knot configuration. Two readers reciting simultaneously, with divergence noted, is a concurrent independent verification: neither reader can drift without the other flagging it.

**Transfer to §7.1:** Each Compound-window event (each sprint, each gate pass, each maturity-level transition) is a cord handover. A Break receipt is the in-unison handover reading: a contradiction surfaced and scored at the moment of the event, while the event is occurring, by a reader independent of the subsystem that holds the cord. The Epoch gate is the summons-recital: a high-ceremony event before a presiding authority (Ockham, or a FluxBench harness) at which the subsystem presents its Break history. The gate's legitimacy is borrowed from the standing handover trace. A subsystem that arrives at the Epoch gate with N receipts that were accumulated without per-event structure is presenting a memory-recital with no standing trace.

---

## Stance on Gate vs. Continuous

**The source domain resolves this as: the standing knot-by-knot trace is constitutive; the summons-recital is ratifying. They are not interchangeable. The trace cannot be reconstructed from the recital, and the recital cannot substitute for the trace.**

The khipu protocol draws a sharp ontological distinction between the two verification events: they are different in kind, not just in frequency. The handover trace exists prior to and independent of any summons. The summons cannot call the trace into being retroactively — it can only report what the trace already established. This is not merely a sequencing requirement; it is a legal standing requirement. Evidence produced by a summons-recital that was not grounded in a standing trace had no standing in tawantinsuyu administrative adjudication.

**Verdict for §7.1:** The gate (≥N receipts at Epoch boundary) alone is the summons-recital with no standing trace. Continuous-mode Break with an aggregate rate metric is an attempt to approximate a standing trace via summary statistics, but aggregate rate metrics erase the per-handover structure — they do not preserve which specific Compound-window events were accompanied by contradiction passes. The correct structure requires per-event Break receipts (the standing trace) and a gate-ceremony that ratifies the existing trace (the summons-recital). The gate form determines whether Epoch is granted; the per-event trace determines whether the gate has anything to ratify.

---

## Findings

### P0-1: Pure-gate Break (≥N receipts at boundary) is a summons-recital with no standing trace — constitutive evidence reconstructed from memory

**File:** `docs/sylveste-vision.md`, lines 456-465

**Mechanism:** The spec requires Break receipts logged during the Compound window but does not require receipts to be temporally tied to specific Compound-window events (specific sprints, specific gate passes, specific maturity-level transitions). A subsystem can satisfy ≥N by generating receipts in batch, disconnected from the events they nominally describe. These receipts are recitations from memory: the subsystem reports contradictions about its Compound activity without those contradictions having been witnessed at the time the activity occurred.

**This is the failure mode the khipu protocol was designed to prevent.** A khipukamayuq reciting before the kuraka what the cord contained, without an in-unison handover trace establishing that the cord's verified state matched the recitation, had no evidentiary standing. The cord's contents "as remembered" were not the cord's contents "as verified." In the Sylveste context: contradictions "as later enumerated" are not contradictions "as witnessed during the behavior that produced them."

**Concrete failure scenario:** Interflux reaches Compound. During three sprints, its finding density is high and its evidence is compounding. In the fourth sprint, Interflux generates eight Break receipts describing contradictions in its finding-classification logic. Interspect scores them. The gate passes (≥N satisfied). Epoch is granted. The problem: the eight receipts were surfaced in the fourth sprint, describing behavior from sprints one through three — behavior that occurred without a concurrent in-unison verification at the time. Interspect cannot verify that the contradictions were surfaced when the relevant behavior occurred. The receipts may accurately describe real contradictions, or they may be Interflux's memory of what it thinks contradictions existed — there is no way to distinguish these. The Epoch grant has no standing trace.

**Smallest fix:** Break receipts must carry a `parent_event_id` referencing the Compound-window event (sprint, gate pass, or maturity transition) they describe, and they must be timestamped before the subsequent event occurs. Receipts submitted after the event window closes are marked as retrospective and carry no standing-trace weight — they may inform the summons-recital context but do not satisfy the per-event trace requirement.

```diff
 Self-surfaced contradictions, scored for severity by Interspect rather
-than by the pillar surfacing them, recorded as evidence in their own right.
+than by the pillar surfacing them, recorded as evidence in their own right.
+Each Break receipt must reference the specific Compound-window event it
+contradicts (via event_id) and must be submitted within the event's window,
+not batched at the Epoch boundary. Retrospective receipts are marked as
+summons-context only and do not satisfy the per-event trace requirement.
```

---

### P0-2: Continuous-mode Break with aggregate rate metric erases the per-handover structure — rate satisfied by off-event contradictions

**File:** `docs/sylveste-vision.md`, lines 456-465 (implied continuous-mode design)

**Mechanism:** If continuous-mode Break tracks an aggregate contradictions-per-period rate, any Compound-window event can pass without an associated contradiction-pass. A high-frequency burst of Break receipts unconnected to specific events satisfies the rate threshold. The per-handover structure — the requirement that each cord transition be verified in-unison — is erased by the aggregate. The rate says "the standing trace was active," but cannot say "this specific transition was verified."

**The khipu protocol requires per-handover verification, not aggregate verification density.** A tribute cord that passed through three provincial khipukamayuq in a season, with the first and third handovers verified in-unison but the second skipped, was considered unverified for the purposes of the second-to-third transition — even if the overall verification density for the season was high. The specific transition with no in-unison reading was a break in the chain of custody. That specific cord segment was legally suspect even if surrounded by verified segments.

**Concrete failure scenario:** Lattice has a healthy Break-rate during Compound — it surfaces contradictions frequently. But three specific sprint-level gate passes in the Compound window were not accompanied by Break receipts. The aggregate rate metric does not register these gaps because the surrounding sprints had high Break density. Lattice enters Epoch. Post-hoc audit reveals that one of the three unverified sprint transitions introduced a schema assumption that later caused evidence corruption. The standing trace had a gap at exactly that transition. The rate metric was satisfied; the chain of custody was not.

**Smallest fix:** Continuous-mode Break must be implemented as a per-event obligation, not an aggregate rate. The Tier-2 self-observation health metric tracks per-event receipt existence, not per-period receipt count. A subsystem with a high per-period count but gaps at specific events has a broken chain of custody, regardless of its overall rate.

---

### P1: Single-scorer severity assessment is a solo reading — no concurrent independent voice to flag divergence

**File:** `docs/sylveste-vision.md`, line 458 ("scored for severity by Interspect rather than by the pillar surfacing them")

**Mechanism:** The in-unison reading principle requires two voices reciting simultaneously. A single khipukamayuq reading alone cannot detect the failure mode where expectation substitutes for actual knot state — there is no concurrent independent signal to diverge from. The spec assigns Break-receipt severity scoring entirely to Interspect. This is correct insofar as it removes the subsystem from its own scoring. But it creates a single-reader verification: Interspect alone scores, with no concurrent second channel.

The risk is the expectation-substitution failure mode. If Interspect's scoring model has been trained on or primed by the same evidence corpus the subsystem used to build its promotion case, Interspect's scoring of a contradiction may track Interspect's expectation of what a contradiction should look like rather than the actual contradiction-content. With two concurrent independent readers, this divergence surfaces. With one reader, it cannot.

**Concrete failure scenario:** Ockham surfaces a contradiction about its dispatch rationale quality. Interspect scores the contradiction as P2 (low severity). But Interspect's scoring heuristics for dispatch-rationale quality were calibrated on Ockham's own dispatch history — the corpus that produced the Compound evidence now being contradicted. Interspect's expectation of "what a good dispatch rationale looks like" is shaped by the substrate under examination. Its score may reflect that expectation rather than the actual content of the contradiction. A second independent scorer — a separate Interspect instance, a FluxBench harness, or a cross-pillar peer — would be needed to flag the divergence between the two severity assessments.

**Smallest fix:** For Break receipts above a minimum severity threshold (P1 or higher as scored by the primary Interspect scorer), require a second independent severity assessment before the receipt enters the standing trace with full weight. The second assessment may come from a FluxBench replay, a different Interspect routing tier, or a designated peer subsystem's contradiction-scoring channel. Receipts where the two assessments diverge by more than one severity tier are flagged for human review before being counted toward the ≥N total.

---

### P2: Tributary-cord vs. census-cord distinction — per-subsystem handover frequency must determine Break obligation density

**File:** `docs/sylveste-vision.md`, lines 448-450 (per-subsystem promotion criteria)

**Observation:** In the tawantinsuyu record system, tributary cords had frequent handovers (high-frequency administrative events) while census cords had rare handovers (decadal-equivalent events). A uniform per-handover verification obligation would be appropriate for a tributary cord and catastrophically burdensome for a census cord. The protocol calibrated the obligation to the handover frequency inherent to the cord's function.

§7.1 specifies a uniform Break receipt obligation (≥N per Compound window) without calibrating to subsystem event-frequency. A subsystem like Ockham, which participates in dozens of sprint-level gate events per Compound window, has a rich handover-equivalent schedule; a census-equivalent subsystem like Lattice's core ontology schema may have few Compound-window transitions of significance. Does the spec require per-event Break receipts calibrated to actual transition density, or does it impose a uniform N regardless of the subsystem's natural handover rhythm? If the latter, Lattice's genuine sparsity of transition events will cause it to fail a Break threshold calibrated for Ockham's tributary density — or will cause it to manufacture off-event contradictions to pad the count.

---

## Implications for Downstream Calls

**For #2 (scoring):** Interspect's scoring of Break receipts must record not only severity but also (a) the `parent_event_id` of the Compound-window event the receipt references, (b) whether the receipt was submitted within the event window (standing-trace weight) or retrospectively (summons-context weight), and (c) whether a concurrent second-voice assessment was performed and at what divergence. The standing-trace weight and the summons-context weight are different evidence classes and must not be aggregated.

**For #3 (threshold form):** The threshold is correctly expressed as two separate conditions: (a) per-event trace coverage — every Compound-window transition event above a minimum significance threshold must have at least one associated Break receipt with standing-trace weight; and (b) count coverage — the total of standing-trace-weight receipts must reach N. Condition (b) can be satisfied independently of condition (a) only if condition (a) is satisfied first. A subsystem that satisfies (b) without (a) has a summons-recital with no standing trace: Epoch is not available.

**For #5 (consequence framing):** A gap in the per-event trace (a Compound-window transition with no Break receipt) is a chain-of-custody break, not a quality signal. The consequence is that the subsystem cannot present that transition segment as verified evidence — the Epoch claim excludes that segment, or the Epoch is deferred until the gap is remediated. This is different from a subsystem with a high gap rate (which suggests systematic failure to verify, warranting investigation) and different from a subsystem whose receipts score consistently low (which suggests the subsystem is genuinely finding no meaningful contradictions and may need external prompting to surface them). The three failure modes have different consequences and must be distinguishable in the evidence record.

---

## Summary Verdict

**The standing knot-by-knot trace (per-event Break receipts timestamped against Compound-window transitions) is constitutive. The gate (≥N receipts at Epoch boundary) is the summons-recital: it ratifies an existing trace. A gate with no standing trace is legally void — the recitation has no chain of custody. Continuous aggregate-rate metrics are not standing traces; they are summaries that erase the per-event structure the chain of custody requires.**

The most structurally important implication: the gate form in §7.1 must specify that Epoch grants are grounded in a standing trace, and must define what constitutes a break in that trace. Without this, the subsystem presenting N receipts at the Epoch boundary is a khipukamayuq reciting from memory — the testimony may be accurate, but it has no legal standing.
