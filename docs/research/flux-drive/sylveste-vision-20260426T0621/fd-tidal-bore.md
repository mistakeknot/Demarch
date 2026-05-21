# fd-tidal-bore — Review of sylveste-vision.md v5.0

**Lens:** Coastal hydrodynamicist studying tidal bores in funnel estuaries.
**Decision question:** Where in the Sylveste flywheel does ordinary signal accumulation become a tidal bore — a sudden, concentrated, hard-to-stop wave — and is the system designed for that asymmetry?

## Domain Framing
A tidal bore is what happens when ordinary distributed tidal energy meets a funnel-shaped estuary. The water column shallows, the channel narrows, the tide's leading edge can no longer disperse — it stacks into a propagating wall. Three properties define the phenomenon: (1) bore-formation requires phase alignment of incoming waves; (2) bore amplitude is non-linear in input — small geometry changes produce large amplitude changes; (3) bores are predictable from tide tables but only if the tables are calibrated. Without the tables, a fishing village just sees the wall arrive.

## P0 Findings

### P0-1: No detection for phase-aligned spurious evidence across sources
The v5.0 expansion adds four upstream evidence sources to the one Interspect already consumes. The doc treats this as enrichment. But five sources that are not independent can phase-align and produce a spurious bore — a moment of correlated noise across sources that promotes a subsystem (or triggers a routing change) that no single source would produce. The likely correlation: all five derive from the same kernel events, so any kernel-level anomaly is replicated to all five "independent" sources simultaneously.
**Fix:** Specify a cross-source independence test. If correlation between any two source's signals exceeds a threshold over a window, the system flags reduced effective evidence count and dampens decisions accordingly. Without this, "five sources" is operationally one source amplified.

### P0-2: Authority advancement has no bore-detector
The L0→L5 authority ladder, as described in the Ship phase, advances based on accumulated evidence. The doc says "L3: human sets shipping policy … L4-L5: agent pushes autonomously within policy bounds." Nothing prevents the kind of single-window phase alignment where a single good week of evidence (which happens to coincide with calm operational conditions, low load, no edge cases) advances the system from L3 to L4 in one step. A bore-aware system distinguishes a sustained tide from a wind-driven spike.
**Fix:** Require advancement evidence to span N independent windows with no single window contributing more than M% of the supporting evidence. Equivalent to a tide-table calibration: only sustained alignment counts.

## P1 Findings

### P1-1: Campaign-level dispatch is bore-vulnerable
"Autonomous epic execution" via /campaign dispatches multiple features in parallel through phase-gated pipelines. When many features simultaneously meet the same gate at the same moment (because they were dispatched together and progressed at similar rates), a single mistuned gate produces a wall of failures, or worse, a wall of bad-but-passing changes. The doc celebrates "topological sort by dependency graph, phase-gated dispatch" but doesn't address the simultaneity hazard.
**Fix:** Stagger gate transitions across simultaneously-dispatched features, or require gate-pass evidence to be evaluated per-feature with independent thresholds.

### P1-2: Epoch resets lack a tide-table
The doc names epoch triggers ("major model API change, architecture migration, subsystem replacement") but treats them as reactive events. A tide table predicts arrival times; an epoch table would predict triggering conditions. Without forecast, epochs surprise the system — a model deprecation that's been announced for three months still triggers an unanticipated reset on the day. The infrastructure exists (cost data, model lifecycles) to forecast some of this.
**Fix:** Maintain a forward-looking epoch calendar — anticipated triggers with target dates and pre-trigger preparation procedures.

### P1-3: V4 → V5 expansion adds new constructive-interference modes during transition
Bringing FluxBench, Factory Substrate, Interweave, Ockham from M0/M1 to operational maturity introduces four new evidence sources during a multi-quarter window. During that window, each source is variously noisy, biased, or partial. Their additions to the loop are not coordinated. The risk: two newly-online sources can phase-align with the existing Interspect signal in their first weeks of operation and produce a bore that the system promotes as evidence of cross-source convergence.
**Fix:** Require new sources to operate in shadow mode (their signals tracked but not influencing decisions) for an explicit calibration window, with releases gated on demonstrated independence from existing sources.

### P1-4: Sustained vs spike evidence is not formally distinguished
Throughout the doc, "evidence" is undifferentiated by temporal pattern. A 30-day sustained gate-pass-rate of 72% and a single-day spike of 95% are both technically "evidence." A bore-aware system would weight these very differently — the spike could be either a regression front or measurement noise, and the system can't tell which until later. The "evidence quarantine (48h delay)" is mentioned but is the only temporal control named.
**Fix:** Specify a sustained-vs-spike classification on incoming evidence, with spikes routed to investigation and sustained signals routed to advancement.

## P2 Findings

### P2-1: Goodhart and bores are related — both are non-linear amplifications of small inputs
The doc's Goodhart caveat acknowledges the metric-as-target problem but doesn't connect it to phase alignment. Agents that learn to satisfy the metric will produce phase-aligned evidence (all hitting the threshold at the same moments). This is a Goodhart-induced bore.

### P2-2: Cost trajectory is itself a candidate bore
The $1.17 → $2.93 jump is presented as caused by review-scope expansion. From a bore perspective, that is a step in the cost time series — a wall arriving. The doc explains it post-hoc but doesn't say what early warning would have surfaced this in the days before the wall.

### P2-3: Mesh advancement is bore-vulnerable in coordinated-rollout phases
Phase 2 of the upstream rollout (Ontology + Measurement in parallel) implies coordinated advancement. If both reach M2 in the same week, downstream decisions that depend on either get a sudden capability surge. Smooth would be better than synchronized.

## Cross-track signal
Converges with **fd-evidence-pipeline-integrity** on the cross-source aggregation gap; with **fd-flywheel-dynamics** on the dampening-parameter omission; with **fd-assay-office-hallmarks** on the missing immutable record of past advancement (which would let the system distinguish a real bore from a noise spike).

## Summary
Sylveste's flywheel has evidence sources that look distributed but plausibly are coupled. The doc names balancing loops but doesn't model the phase-alignment failure mode. A handful of explicit independence tests would harden this against the most likely concentration event.
