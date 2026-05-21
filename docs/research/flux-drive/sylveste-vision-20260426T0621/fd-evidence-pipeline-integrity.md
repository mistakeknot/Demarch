# fd-evidence-pipeline-integrity — Review of sylveste-vision.md v5.0

**Lens:** Evidence-systems engineer auditing attribution pipelines.
**Decision question:** Does every evidence claim have a concrete pipeline stage that produces, validates, and decays it?

## P0 Findings

### P0-1: Tier weights described qualitatively only, no aggregation function
The doc names Tier 1 (controlled) / Tier 2 (observational) / Tier 3 (anecdotal) and asserts "highest weight / standard weight / lowest weight" but never specifies the numerical model. Two reviewers given the same evidence cannot independently compute the same maturity score. The promotion rule "at least one Tier-1 or Tier-2 signal meeting threshold" hides the question of how mixed-tier evidence aggregates when conflicting (e.g., a Tier-1 fail and ten Tier-2 passes).
**Fix:** Specify (a) the per-tier weight constants, (b) the aggregation function (weighted-min vs weighted-mean vs gated-AND), (c) the conflict-resolution rule when tiers disagree.

### P0-2: No evidence schema versioning or migration story
Evidence is "stored" implicitly in SQLite but the doc says nothing about what happens when the schema evolves. If kernel events gain a field, do existing maturity computations re-run on the new shape? Do they compute on the old shape? Does Interspect freeze evidence at write time or re-evaluate at read time? Without this, a schema migration silently invalidates promotion criteria.
**Fix:** Specify either (a) evidence is immutable post-write and old schemas are evaluated by old rules (versioned evaluators), or (b) evidence is migrated and migration is itself an epoch trigger.

## P1 Findings

### P1-1: Independent verification claim is structurally weak
"Interspect serves as the architecturally independent verification layer" but Interspect runs on the same Intercore kernel, reads the same SQLite DB, and lives in the same process tree. If the kernel has a bug that drops events, Interspect cannot see it because Interspect's input is those same events. The "assay office" principle requires substrate separation, not just code separation. The doc itself notes Interspect is the "one exception" and is evaluated by "human attestation and controlled FluxBench experiments" — but FluxBench is itself M0/planned, so the exception is currently un-instantiated.
**Fix:** Either (a) acknowledge that until FluxBench is M2, Interspect's own maturity has only human attestation, or (b) commit to a non-Intercore evidence channel for Interspect verification (independent log shipper, external timeseries store).

### P1-2: Per-subsystem promotion criteria specified for only one subsystem
The Routing M1→M2 example is concrete (>70% gate pass rate sustained 30 days, evaluated by Interspect, ≥1 Tier-1/2 signal). The other nine subsystems get no concrete criteria — only the abstract framework. This is the most important place to be precise, and it isn't.
**Fix:** Add a per-subsystem promotion criteria table or appendix. At minimum: Persistence, Coordination, Discovery, Review, Integration, Ontology, Measurement, Governance.

### P1-3: No evidence-decay model
The doc says "trust persists as long as evidence remains fresh and regression indicators are absent" but never specifies a freshness window. After how many days does a Tier-2 signal stop counting? Does freshness vary by tier? Without decay, evidence accumulates monotonically and trust ratchets up regardless of operational reality.
**Fix:** Specify per-tier freshness windows (e.g., Tier-1: 90 days, Tier-2: 30 days, Tier-3: 7 days). Tie freshness to epoch-trigger logic.

### P1-4: Attribution chain is end-to-end-asserted but not end-to-end-tested
The chain "kernel event → Interspect signal → routing override → outcome measurement" is described, but there is no claim that the full chain has been instrumented end-to-end on a single decision. The "Routing/Measurement: Attribution chain integrity" interface signal is named in the table but no sample data is shown.
**Fix:** Commit to a smoke-test: trace one routing decision end-to-end and publish the result as an artifact in the doc.

## P2 Findings

### P2-1: Evidence quarantine (48h) is presented without a derivation
"48h delay before influencing routing" appears as a fact under "Where We Are" but the doc never explains why 48h. Too short for slow drifts, too long for fast model regressions. Without a derivation, this is a magic number waiting to be wrong.

### P2-2: Sprint-output-as-evidence treats all sprints as equal-weight
The closing-link claim "more sprints → more evidence" doesn't stratify by sprint quality. A failed sprint produces evidence too — but does it weigh the same as a clean sprint? If yes, the loop reinforces noise.

### P2-3: Goodhart caveat is acknowledged but unprotected
The doc mentions "Goodhart caveat" but the only mitigation is "rotate emphasis, diversify dimensions, watch for agents optimizing the metric." This is the operator's job, not the system's. No automated counter-Goodhart mechanism is named.

## Summary
The evidence pipeline thesis is conceptually solid but operationally underspecified. The Tier-weight aggregation, schema versioning, decay model, and per-subsystem criteria are the four most load-bearing pieces — and the doc punts on three of them.
