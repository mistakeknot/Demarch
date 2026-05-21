# fd-polynesian-wayfinding — Review of sylveste-vision.md v5.0

**Lens:** Master Polynesian wayfinder in the Hokulea revival tradition.
**Decision question:** When all the evidence sources go dark — Interspect down, FluxBench unbuilt, GitHub unreachable — does Sylveste still know where it is, or does it drift?

## Domain Framing
A wayfinder navigates without continuous instruments. The discipline rests on four pillars: (1) etak — mental tracking of position relative to a reference island that may itself be invisible; (2) redundant cues — swell direction, star paths, bird species, water color, each separately fallible but jointly reliable; (3) apprenticeship — voyaging is preceded by years of cue-reading on shore, so the navigator's instruments are calibrated before they cast off; (4) dead reckoning — when one cue fails, the others maintain orientation; when many fail, learned procedure carries the canoe through the void.

## P0 Findings

### P0-1: All evidence appears to derive from the same substrate (kernel events)
A wayfinder who relies on stars and only stars cannot navigate through cloud cover. Sylveste's five evidence sources (Interspect, Interweave, Interop, Factory Substrate, FluxBench) and the cross-cutting profiler, governance, and integration systems all consume kernel events as their primary input — that's what makes the kernel "the system of record." But this means cue-failure at the kernel level (a buggy event emitter, a database write loss, a clock drift) propagates into every supposedly-independent evidence source simultaneously. The "five sources" are five filtered views of one substrate. A wayfinder would say: this is one star, repeatedly named.
**Fix:** Identify which evidence sources are genuinely substrate-independent (different write path, different storage). For the ones that all derive from kernel events, acknowledge the dependency in the doc and either (a) designate one source as substrate-independent (e.g., FluxBench as controlled-experiment with its own data path), or (b) introduce an external cross-check (third-party log shipper, periodic out-of-band measurement).

### P0-2: No dead-reckoning procedure for instrument outage
The doc describes the system as evidence-driven throughout. There is no description of how the system operates when its evidence channel fails. If Interspect goes down for 48 hours, what happens to routing? Does it revert to a known-good baseline? Freeze at last decision? Continue without evidence input until restoration? The wayfinder's discipline says: when stars vanish, dead-reckon from last known position using known speed and heading. Sylveste has no equivalent specified.
**Fix:** Specify a fallback mode: "when evidence pipeline is degraded for >X hours, the system reverts to baseline routing (snapshot from date Y), suppresses adaptive proposals, and logs the outage as a dead-reckoning interval that does not contribute to evidence."

## P1 Findings

### P1-1: No apprenticeship/shadow mode generalized to all evidence sources
The "Interspect Phase 2" item under "What's Next" mentions "shadow evaluation" as a future capability. Polynesian wayfinding requires apprenticeship before voyaging — the navigator reads cues from shore for years before they read them from sea. New evidence sources (FluxBench, Factory Substrate, Ockham, Interweave) coming online in the v5 expansion are going live without explicit shadow periods. The doc names mesh maturity levels (M1 Built, M2 Operational) but doesn't say a freshly-M2 source must shadow before influencing decisions.
**Fix:** Require new evidence sources to operate in shadow (signals collected but not influencing decisions) for an explicit calibration window — e.g., M2-shadow before M2-active, with promotion based on demonstrated agreement with established sources.

### P1-2: Etak — no reference frame for system state
A wayfinder always knows where they are relative to a reference island. Sylveste's mesh table reports current state per cell, but there is no persistent reference frame against which present state is measured. "Cost is $2.93/landable change" — relative to what? The Feb 28 baseline of $1.17? Then the system's etak position is "drifted +$1.76 since the last reference fix." The doc doesn't formalize this. Without an etak, drift is invisible until it is large.
**Fix:** Establish a periodic reference fix — quarterly or monthly snapshot of the full system state (mesh maturity, cost, fleet utilization, evidence freshness) — against which intervening state is reported as drift.

### P1-3: No procedure for total disorientation recovery
Epoch resets are named but their recovery procedure is not. After a major model API change (epoch trigger), the system has lost some calibration. A wayfinder caught by storm executes a known recovery procedure: reduce sail, hove-to, wait for cues to return, re-fix position. Sylveste has no documented post-epoch recovery — what does the system do in the hours and days after an epoch fires? Does it freeze advancement until evidence accumulates? Continue at degraded confidence?
**Fix:** Document a post-epoch procedure: reduced authority across all dependent cells, accelerated re-verification protocol, explicit recovery-period boundary.

### P1-4: Human-as-wayfinder role is implicit but not named
"Human attention is the bottleneck" (Design Principle #5) frames the human as approver and strategist. A wayfinder's role is different — they read cues that instruments don't, hold the dead-reckoning when sensors lie, recognize landfall before the GPS does. The doc has a place for this role but doesn't explicitly name it. When evidence pipelines are degraded, who is the wayfinder?
**Fix:** Name a human-wayfinder role in operational documentation — the operator who carries calibration through outages and disagrees with instruments when conditions warrant.

## P2 Findings

### P2-1: "Above the loop, not in it" is the right framing but undertested
Design Principle #5 places the human strategically. The wayfinder analogy says the human is also tactical during instrument failure. The doc's framing is correct for steady state; it's incomplete for outage.

### P2-2: Cross-cue independence is asserted in the interface evidence table
The "Interface Evidence" table (Ontology/Governance, Routing/Measurement, etc.) is the closest thing in the doc to redundant-cue discipline — pairwise consistency checks. This is the right structure; it just needs to be elevated to a first-class principle rather than a sub-table.

### P2-3: 1,456-bead corpus is a learning record but not a calibration record
A wayfinder's apprenticeship produces calibration data — what each cue means under what conditions. Beads are the closest Sylveste analog but they're work records, not calibration records. The system has been building itself for several months but has no equivalent of "what does this signal mean here, calibrated against last quarter."

## Cross-track signal
Converges strongly with **fd-evidence-pipeline-integrity** on the source-substrate-independence gap; with **fd-tidal-bore** on the cross-source phase-alignment risk; with **fd-trust-mechanics** on what happens during transition periods (epoch, transfer); with **fd-flywheel-dynamics** on the bootstrap problem (apprenticeship before voyaging).

## Summary
Sylveste navigates by evidence, but most of its instruments derive from the same star. The system has no dead-reckoning, no documented recovery from instrument failure, and no apprenticeship requirement for new sources. In calm seas this is invisible; the first storm exposes it.
