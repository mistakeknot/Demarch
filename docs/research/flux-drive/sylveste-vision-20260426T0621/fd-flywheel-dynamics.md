# fd-flywheel-dynamics — Review of sylveste-vision.md v5.0

**Lens:** Systems-dynamics modeler auditing reinforcing/balancing-loop behavior.
**Decision question:** If the flywheel runs for six months on real data, does it converge, oscillate, or saddle?

## P0 Findings

### P0-1: Phase 3-4 bootstrap is not specified
The dependency ordering says: Phase 3 (Governance) needs ontology+measurement; Phase 4 (adaptive Routing) needs all upstream. The doc itself notes "Phases 3-4 form a feedback cycle (Governance → Routing → Measurement → Governance) bootstrapped by manually-set initial governance policy." But that's the only sentence on bootstrap. What is the initial policy? How is it removed? Is removal triggered by evidence accumulation, or by human decision? Without bootstrap specification, the loop cannot be initialized — or worse, it can be initialized by accident with whatever policy was lying around at startup.
**Fix:** Specify (a) the schema and source of the initial governance policy, (b) the criteria under which initial policy gives way to evidence-derived policy, (c) the rollback path if the transition destabilizes the loop.

### P0-2: System trust = min(maturity) creates a stuck-loop dynamic
With ten subsystems and weakest-link aggregation, system trust advances only when the slowest cell catches up. The doc treats this as a virtue (B1 limits-to-growth). Dynamically, this means: most evidence accumulation produces no system-trust change; advancement comes in steps as the laggard catches up. This creates long flat periods where the loop's reinforcing engine produces no observable advancement, which makes operational tuning blind. Worse, the laggard cell becomes the only thing that matters — investment elsewhere shows no aggregate return.
**Fix:** Either (a) report per-cell trust separately as the operational signal (system trust as a derived but not primary view), (b) move to a percentile aggregation that rewards cross-system progress.

## P1 Findings

### P1-1: Balancing loop dampening is unparameterized
B1 (weakest-link) and B2 (saturation, "once a model is well-characterized additional evidence produces diminishing returns") are named but not parameterized. What is the saturation curve shape? At what evidence count does additional evidence weight halve? Without dampening parameters, the system cannot detect when reinforcement is overwhelming dampening — the classic limits-to-growth pathology where damage shows only when growth stalls.
**Fix:** Specify saturation curves per evidence tier or per subsystem class.

### P1-2: Phase 1 → Phase 2 unblocking is asserted, hidden Interop dependencies are likely
Phase 1 (Interop, independent) is listed as a root. Phase 2 (Ontology, Measurement) is "parallel" after Phase 1. But Ontology likely consumes data that Interop synchronizes (cross-system entity tracking presumably uses Interop's event hub). Measurement likely needs Interop for outcome attribution across system boundaries. The "parallel" framing under-describes this coupling.
**Fix:** Either (a) explicitly state that Ontology and Measurement consume Interop's outputs and require Interop M2 before they can reach M2 themselves, or (b) demonstrate that Ontology/Measurement can mature on internal-only signals first, then upgrade when Interop matures.

### P1-3: Sprint-as-evidence is undifferentiated by quality
"More sprints → more evidence" is the closing reinforcing link. But not all sprints produce equal-quality evidence: a thoroughly-failed sprint, a one-line trivial change, and a clean feature ship all count. Without quality-weighted contribution, the loop reinforces noise. The Goodhart warning anticipates this for individual metrics but not for the loop itself.
**Fix:** Specify a quality filter on sprint-as-evidence — e.g., only sprints reaching Ship contribute; abandoned/aborted sprints contribute as Tier-3 only.

### P1-4: Interspect changes are themselves part of the loop and the doc doesn't see this
Interspect proposes routing/gate changes based on evidence. Those changes affect the next sprint's evidence. Interspect is therefore observing a system it has just modified — a recursive self-influence the loop doesn't acknowledge. Without this recognition, the loop appears to converge when it is actually drifting.
**Fix:** Add a "loop-effect" check — e.g., Interspect proposals include a counterfactual estimate (what the metric would be without the proposal) and that counterfactual is tracked.

## P2 Findings

### P2-1: Epoch-reset propagation through balancing loops is unspecified
When an epoch fires, evidence is partially reset. Does the saturation curve also reset? If yes, the system can re-promote on stale conditions. If no, the saturation acts as a stabilizer through epochs.

### P2-2: The "evidence saturation = feature, not bug" claim needs a falsification test
The doc says saturation prevents over-extrapolation. True in well-characterized regimes. But saturation also prevents detecting late-onset regression (a model that subtly degrades after the saturation regime). The feature/bug framing should be defended.

### P2-3: No mention of loop frequency
What's the loop's natural period? Per-sprint? Per-day? Per-quarter? The flywheel diagram is timeless. Different loop periods produce different stability behaviors; the doc could commit to a period.

## Summary
The flywheel is conceptually correct but dynamically vague. The bootstrap problem and the min()-aggregation pathology are the two structural issues; the dampening parameterization and the Interspect-self-recursion are the two unwatched failure modes.
