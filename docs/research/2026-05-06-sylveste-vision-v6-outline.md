---
artifact_type: outline
target: docs/sylveste-vision.md (v6)
predecessor: docs/sylveste-vision.md (v5.0, 2026-04-11)
sources:
  - docs/research/flux-drive/sylveste-vision-20260426T0621/ (10 lens reviews, 20 P0 + 28 P1 findings)
  - docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md (4 flux-explore agents)
bead: sylveste-mj11
date: 2026-05-06
status: gate-test
---

# Vision v6 — Outline

This is the outline gate-test for the v6 specification (sylveste-mj11). The bead's
acceptance criteria call for an outline check before doc-writing: if the outline
produces only rephrasings of v5, abort and revisit Option 2 from the 2026-04-30
strategy session. Verdict at the bottom of this file.

## Annotation legend

- **[SAME]** — section carries over from v5 with no substantive change
- **[REVISE]** — section reworked to tighten/correct an assertion v5 makes loosely
- **[NEW]** — section did not exist in v5
- **[APPEND]** — new appendix-grade content at end of doc
- Each new spec-bearing bullet is tagged with the P0/P1 finding(s) it resolves and
  whether it is `spec` (v6 prose), `ship` (child bead), or `defer` (with reason).

---

## §1. The Pitch [REVISE]

- Carry the v5 thesis ("evidence compounds → earned trust → progressive authority")
  unchanged — this is the load-bearing wall.
- **Add: heart-note designation.** v5 lists six pillars equally; v6 names a single
  daily-driver capability that, if removed, changes what Sylveste is. Candidate:
  *kernel-driven sprint lifecycle with evidence-loop gating*. Resolves
  `fd-perfumer-accord P0-1`. **Triage: spec.**
- **Add: v4→v5→v6 reformulation note.** One sentence acknowledging that v5 expanded
  from one evidence source (Interspect) to five and v6 hardens the integration
  contract for those five. Resolves `fd-perfumer-accord P1-3`. **Triage: spec.**

## §2. Two Brands, One Architecture [SAME]

- No change. The register-layering doctrine is intact and the v5 prose is correct.
  Note for follow-up only: `fd-perfumer-accord P1-1` flags that the vision doc itself
  is the bridge between SF and garden registers — accept this as a doc-level fact
  rather than a contradiction. **Triage: defer (doc-meta, not spec).**

## §3. Why This Exists [SAME]

- v5 prose is the strongest section of the doc. Untouched.

## §4. The Stack [REVISE]

- v5 layer descriptions stay.
- **Add: substrate-dependency table.** For each of the five evidence sources
  (Interspect, Interweave, Interop, Factory Substrate, FluxBench) plus Ockham, list
  (a) write-path identity (which storage, which process), (b) substrate-independence
  rating: independent / partially-independent / shared-with-kernel. Used as the input
  for §7 substrate-independence stance. Resolves `fd-polynesian-wayfinding P0-1`,
  `fd-tidal-bore P0-1`, `fd-assay-office-hallmarks P1-1`,
  `brainstorm: load-path independence audit`. **Triage: spec (the table) +
  ship (a one-time audit bead under mj11 to populate it).**

## §5. The Flywheel [REVISE]

- v5 diagram and reinforcing-loop description carry over.
- **Replace** the single sentence "bootstrapped by manually-set initial governance
  policy" with a §5.1 subsection.

### §5.1 Phase 3-4 Bootstrap [NEW]

- Specify (a) initial governance-policy schema and source (likely a YAML in
  `core/intercore/config/`), (b) the criteria under which evidence-derived policy
  takes over from initial policy (e.g., Measurement reaches M2 *and* Governance has
  recorded ≥N policy decisions whose outcomes are observable), (c) the rollback path
  if the transition destabilizes the loop. Resolves `fd-flywheel-dynamics P0-1`.
  **Triage: spec.**

### §5.2 Loop Recursion & Self-Influence [NEW]

- Acknowledge that Interspect proposals modify the system Interspect observes.
  Specify a counterfactual-tracking requirement: every Interspect proposal records a
  predicted no-op metric value, which is later compared against the actual under-
  proposal value. Resolves `fd-flywheel-dynamics P1-4`. **Triage: spec
  (requirement) + ship (instrumentation bead).**

### §5.3 Balancing-Loop Parameterization [REVISE]

- v5 names B1 (weakest-link) and B2 (saturation) as virtues. v6 keeps the names but
  parameterizes them: per-tier saturation curve shapes, percentile-aggregation
  variant of B1 to fix the min() pathology. Resolves `fd-flywheel-dynamics P1-1`,
  `fd-flywheel-dynamics P0-2`, `fd-trust-mechanics P1-2`.
  **Triage: spec (curves named) + ship (move from min() to weighted-percentile is a
  child bead, since it changes how System Trust is computed).**

## §6. The Capability Mesh [REVISE]

- Maturity scale (M0-M4) carries over.
- **Revise: System trust formula.** From `min(maturity)` to a criticality-weighted
  percentile (or weighted-min) so a non-critical M1 doesn't drag a critical M3
  system down. Resolves `fd-trust-mechanics P1-2`, `fd-flywheel-dynamics P0-2`.
  **Triage: ship (formula change is a child bead).**
- **Add: per-subsystem promotion criteria appendix pointer.** v5 has criteria for
  Routing only. v6 commits to publishing criteria for Persistence, Coordination,
  Discovery, Review, Integration, Ontology, Measurement, Governance. Resolves
  `fd-evidence-pipeline-integrity P1-2`. **Triage: ship (per-subsystem criteria are
  separate beads under mj11).**
- **Add: shadow/apprenticeship requirement** for newly-M2 sources. New evidence
  sources must run shadow-mode (signals collected, decisions not influenced) for an
  explicit calibration window before going active. Resolves
  `fd-polynesian-wayfinding P1-1`, `fd-tidal-bore P1-3`. **Triage: spec.**

## §7. Trust Architecture [REVISE — heaviest section]

This is where the bulk of new spec lands. v5's four phases (Earn → Compound →
Epoch → Demote) are correct vocabulary; v6 adds a Break stage between Compound and
Epoch and parameterizes every phase.

### §7.1 The Trust Lifecycle [REVISE]

- New ordering: **Earn → Compound → Break → Epoch → Demote**.
- **Break (NEW phase).** Between Compound and Epoch, a pillar must surface
  self-contradicting evidence — observations that argue against its own promotion
  case. Severity scored by Interspect, not the pillar. A pillar cannot enter Epoch
  unless it has logged ≥N Break receipts in its Compound window. Resolves
  `brainstorm: jo-ha-kyū "ha" break-open stage`. **Triage: spec (lifecycle change)
  + ship (Interspect Break-scoring is a child bead).**
- **Symmetric promotion/demotion with hysteresis.** Demotion threshold ≠ promotion
  threshold — a band between them prevents thrash. A pillar that demoted M3→M2
  cannot re-promote on the same evidence window that triggered demotion. Resolves
  `brainstorm: hysteresis-banded promotion/demotion`. **Triage: spec.**

### §7.2 Tier-Weight Aggregation [NEW]

- v5 says Tier 1 / 2 / 3 carry "highest / standard / lowest" weight without
  specifying an aggregation function or weight constants. v6 will specify weight
  constants, an aggregation function (gated-AND vs weighted-mean choice + rationale),
  and the conflict-resolution rule when tiers disagree (e.g., one Tier-1 fail and
  ten Tier-2 passes). Resolves `fd-evidence-pipeline-integrity P0-1`,
  `fd-assay-office-hallmarks P2-1`. **Triage: ship — sylveste-mj11.2 already filed.**

### §7.3 Evidence Decay Model [NEW]

- v5 says trust persists "as long as evidence remains fresh" without defining
  freshness. v6 specifies per-tier freshness windows (e.g., Tier-1: 90 days,
  Tier-2: 30 days, Tier-3: 7 days), the decay function (step / linear / exponential),
  and how decay couples to epoch-trigger logic. Resolves
  `fd-evidence-pipeline-integrity P1-3`. **Triage: spec.**

### §7.4 Demotion Latency Bounds [NEW]

- Per-criticality-tier upper bounds:
  - **Critical** (Governance): hours-scale demotion window
  - **High** (Routing, Persistence, Review, Integration, Measurement): hours-to-day
  - **Medium** (Coordination, Discovery, Ontology, Execution): day-to-week
- Specify the clock-start (when does the observation window begin?) and the
  evidence-rate threshold that triggers immediate demotion vs slow demotion.
  Resolves `fd-trust-mechanics P0-1`. **Triage: spec.**

### §7.5 Demotion-Rehearsal as M3+ Precondition [NEW]

- A pillar cannot promote to M3+ unless its demotion procedure has been exercised
  end-to-end in a non-production substrate (FluxBench harness), with the system
  observed to remain functional during the simulated demotion. Resolves
  `brainstorm: demotion-rehearsal`, related bead `sylveste-v3ck`. **Triage: spec
  (criterion stated) + ship (rehearsal harness is a child bead, likely mj11.3).**

### §7.6 Substrate Independence Stance [NEW]

- Replace the v5 assertion that Interspect is "architecturally independent" with
  the substrate-dependency table from §4 plus a debt registry. For each evidence
  source: independence rating, current debt (if shared substrate), planned redundant
  path, and acceptance that until the debt is paid, that source's findings about
  the substrate it shares carry reduced weight. Resolves
  `fd-polynesian-wayfinding P0-1`, `fd-assay-office-hallmarks P1-1`,
  `brainstorm: evidence-substrate independence`. **Triage: spec (stance) +
  ship (load-path audit) + defer (full third-party external check is post-Mythos).**

### §7.7 Trust Transfer Protocol [REVISE]

- v5's "probationary access with verification period" gets numerical bounds:
  probation duration in calendar days *and* sprint count, the metric thresholds
  that count as "equivalent or better performance," and the rollback criteria.
  Concrete example: Auraken→Skaffen and Auraken→Hermes Agent. Resolves
  `fd-trust-mechanics P0-2`. **Triage: spec.**

### §7.8 Hallmark Log [NEW]

- Append-only `advancement_events` table records every M-tier transition with
  (subsystem, from_level, to_level, timestamp, evidence_snapshot_hash,
  assayer_identity, optional human_witness_signature). Demotion writes a new event;
  it does not edit the prior advancement. Threshold revisions and trust-transfers
  produce hallmarks of their own. Resolves `fd-assay-office-hallmarks P0-1`,
  `fd-trust-mechanics P1-4`, `fd-scriptorium P1-2/P1-4`. **Triage: ship —
  sylveste-mj11.1 already filed.**

### §7.9 Cascade Demotion Rule [NEW]

- Specify cascade: any demotion of an upstream cell caps downstream cells at
  upstream-maturity until they re-prove. Synchronous (immediate cap) vs
  evidence-driven (cap when downstream evidence reflects upstream regression) —
  v6 picks synchronous-cap for safety, with re-prove pathway documented. Resolves
  `fd-trust-mechanics P1-3`. **Triage: spec.**

### §7.10 Degraded-Mode Operation [NEW]

- Dead-reckoning procedure when the evidence pipeline is degraded for >N hours:
  revert to baseline-snapshot routing, suppress adaptive proposals, log the outage
  as a dead-reckoning interval that does not contribute to evidence. Name a
  human-wayfinder operator role. Resolves `fd-polynesian-wayfinding P0-2/P1-4`.
  **Triage: spec.**

### §7.11 Epoch Trigger Rubric [REVISE]

- v5's loose triggers ("major model API change, architecture migration, subsystem
  replacement") become a decision rubric: API change is "major" if it changes the
  cost function, latency profile, or answer distribution on a held-out eval set.
  Architecture migration is "major" if it changes kernel SQL schema, event taxonomy,
  or layer boundary. **Add: forward-looking epoch calendar** (anticipated triggers
  with target dates and pre-trigger preparation). Resolves
  `fd-trust-mechanics P1-1`, `fd-tidal-bore P1-2`. **Triage: spec.**

## §8. The Outcome Axes [REVISE]

- Three axes (autonomy, quality, token efficiency) carry over.

### §8.1 Cost Normalization Denominator [REVISE]

- v5 reports `$2.93/landable change` without defining what counts. v6 commits to
  publishing both raw and normalized series — normalized variants:
  cost-per-100-line landable change, cost-per-task-of-typed-complexity. Resolves
  `fd-dispatch-economics P0-1`. **Triage: spec (denominator defined) + ship
  (normalized series instrumentation bead).**

### §8.2 Cache-Corrected Cost [NEW]

- Report headline cost and cache-warmth-corrected cost as separate numbers; track
  the gap as a watch-metric. Extends `interstat/scripts/cost-query.sh`. Resolves
  `brainstorm: cache-corrected cost-per-landable-change`. **Triage: ship
  (additive metric, separate child bead).**

### §8.3 Confidence Interval & Stratification [REVISE]

- North-star reported as mean ± stddev with sample size and date range. Stratified
  by sprint type (epic / single-feature / hotfix). Resolves
  `fd-dispatch-economics P1-4/P2-1`. **Triage: spec (publishing format).**

### §8.4 Anti-Goodhart Mechanism [NEW]

- Commit to one structural anti-Goodhart counter-mechanism: a held-out task set
  evaluated quarterly that the routing system has never seen, with the result
  published as a check on the live metric. Resolves
  `fd-dispatch-economics P0-2`, `fd-evidence-pipeline-integrity P2-3`. **Triage:
  ship (held-out eval is its own child bead).**

### §8.5 Routing-Decision Evidence Schema [NEW]

- Every dispatch decision (Ockham + Clavain gate-tier choices) emits structured
  evidence: `{chosen-tier, considered-alternatives, rationale-tag, fallback-chain,
  realized-cost, cache-state}`. Schema lives in Intercore as a shared type.
  Resolves `brainstorm: routing-decision evidence schema`. **Triage: ship
  (schema + instrumentation is a child bead, intersects intercept project).**

### §8.6 Fleet Hygiene & Effective-Count [NEW]

- Report fleet utilization alongside inventory: "of 589 review agents, N are
  tier=proven and contribute X% of findings." Auto-archive agents that don't reach
  tier=used within Y sprints. Resolves `fd-dispatch-economics P1-1`,
  `fd-perfumer-accord P1-4`. **Triage: spec (commitment) + ship (auto-archive
  policy is a child bead).**

### §8.7 Activation Rate [SAME]

- Carry forward v5 passive-v1 paragraph unchanged. Phase 0 spike already shipped.

## §9. Design Principles [REVISE]

- Eight v5 principles carry over; refine #8 ("Evidence is independently verified")
  to acknowledge that "independent" means substrate-separated, not just
  code-separated, and reference §7.6 for the current debt position.

## §10. The Development Lifecycle [SAME]

- v5 macro-stages and L0-L5 ladder unchanged.

## §11. North Star Metric [REVISE]

- Same metric, new presentation per §8 (denominator, confidence interval,
  cache-correction, anti-Goodhart, fleet effective-count).
- **Add: colophon discipline.** Every published cost figure carries (as-of date,
  fleet snapshot hash, routing-overrides snapshot, model versions, review
  configuration, sample size). Older figures without colophons are explicitly
  marked as informally citable. Resolves `fd-scriptorium P0-2/P2-2`. **Triage:
  spec (commitment) + ship (instrumentation bead).**

## §12. Audience [SAME]

## §13. Open Source Strategy [SAME]

## §14. Where We Are [REVISE]

- v5 inventory metrics carry over.
- **Replace bare counts** with paired (inventory, effective) where data exists:
  "64 plugins (N at tier=proven)", "589 review agents (N tier=proven, contributing
  X% of findings)", "1,456 beads (N closed-as-shipped vs closed-as-superseded)".
  Resolves `fd-perfumer-accord P1-4`, `fd-dispatch-economics P1-1`. **Triage:
  spec (presentation) + ship (closed-bead reason instrumentation is a separate
  bead — currently no `closure_reason` field).**

## §15. What's Next [SAME]

- Six themes carry over; rerank only if mj11 child beads change priorities.

## §16. Horizons [SAME]

## §17. What This Is Not [REVISE]

- v5 list carries over.
- **Add: subtraction discipline declarations.** Items the project commits to NOT
  doing or to retiring. First entries: explicitly defer Garden Salon MVP build
  until prereqs reached; sunset register pointer (see §18). Resolves
  `fd-perfumer-accord P0-2/P2-1`. **Triage: spec.**

## §18. Sunset Register [APPEND]

- New appendix: capabilities below usage threshold scheduled for sunsetting, with
  trigger criteria and target dates. Quarterly review cadence. Resolves
  `fd-perfumer-accord P0-2`. **Triage: spec (register exists in v6) + ship
  (review cadence + auto-archive policy are child beads under mj11).**

## §19. Triage Table [APPEND]

The acceptance-criterion appendix. Every P0/P1 finding from the 10 lens reviews
plus the 4 brainstorm domains (~50 rows) listed with triage. Schema:

| Source | Finding ID | Brief | Triage | Resolved By |
|---|---|---|---|---|
| fd-evidence-pipeline-integrity | P0-1 | Tier-weight aggregation undefined | ship | sylveste-mj11.2 |
| fd-assay-office-hallmarks | P0-1 | Hallmark log missing | ship | sylveste-mj11.1 |
| fd-trust-mechanics | P0-1 | Demotion latency unbounded | spec | §7.4 |
| fd-flywheel-dynamics | P0-1 | Phase 3-4 bootstrap unspecified | spec | §5.1 |
| fd-perfumer-accord | P0-2 | Subtraction discipline missing | spec | §17 + §18 |
| fd-kernel-boundary | P0-2 | Host-agnostic claim untested | defer | post-Mythos host-portability test |
| ... | ... | ... | ... | ... |

Full ~50-row table compiled when v6 prose is drafted; all P0/P1 entries get a
triage call before publication.

## §20. Origins [SAME]

---

# Self-test: rephrasing or new spec?

A rephrasing-only outline would re-shuffle v5 prose under new headings. The test
is whether the outline produces *engineering specification that v5 does not
contain*. The new content lands in:

- **§5.1 (Phase 3-4 bootstrap)** — v5 has one sentence; v6 specifies schema, source,
  transition criteria, rollback path. **New spec.**
- **§5.2 (loop self-influence)** — v5 doesn't see this; v6 commits to counterfactual
  tracking. **New spec.**
- **§7.1 (Break stage)** — v5 has a 4-phase lifecycle; v6 has a 5-phase lifecycle.
  **New spec.**
- **§7.2 (tier-weight aggregation function)** — v5 uses qualitative weights; v6
  specifies constants and aggregation. **New spec (deferred to mj11.2).**
- **§7.3 (evidence decay model)** — v5 says "fresh" undefined; v6 quantifies. **New
  spec.**
- **§7.4 (demotion latency bounds)** — v5 has no bound; v6 has per-tier bounds.
  **New spec.**
- **§7.5 (demotion-rehearsal precondition)** — v5 has no rehearsal concept; v6
  makes it an M3+ gate. **New spec.**
- **§7.6 (substrate independence stance + debt registry)** — v5 asserts
  independence; v6 dismantles the assertion and replaces with debt registry. **New
  spec — and a v5 correction.**
- **§7.7 (trust-transfer numerical bounds)** — v5 vibe-checks; v6 quantifies. **New
  spec.**
- **§7.8 (hallmark log)** — v5 has no immutable advancement record; v6 introduces
  it. **New spec (deferred to mj11.1).**
- **§7.9 (cascade demotion rule)** — v5 asserts cascade without rule; v6 picks
  synchronous-cap. **New spec.**
- **§7.10 (degraded-mode operation)** — v5 has no outage procedure; v6 has dead-
  reckoning. **New spec.**
- **§7.11 (epoch trigger rubric + forward calendar)** — v5 has loose triggers; v6
  has a rubric. **New spec.**
- **§8.1 (cost normalization)** — v5 has undefined denominator; v6 commits to
  normalized series. **New spec.**
- **§8.2 (cache-corrected cost)** — v5 has one number; v6 has paired numbers.
  **New spec.**
- **§8.4 (anti-Goodhart held-out eval)** — v5 names the problem; v6 commits a
  structural counter-mechanism. **New spec.**
- **§8.5 (dispatch evidence schema)** — v5 has no dispatch-decision schema; v6 has
  one. **New spec.**
- **§8.6 (fleet effective-count)** — v5 reports inventory; v6 reports
  inventory + effective. **New spec.**
- **§11 (colophon discipline)** — v5 publishes raw numbers; v6 attaches provenance.
  **New spec.**
- **§17/§18 (subtraction + sunset register)** — v5 has neither; v6 has both. **New
  spec.**

**Verdict: not a rephrasing.** The outline produces engineering specification
substantively beyond v5: a 5-phase lifecycle replacing a 4-phase one, bounded
demotion latency replacing unbounded, decay-windowed evidence replacing
"as long as fresh," substrate-debt registry replacing the independence assertion,
a hallmark log that does not exist, a Break phase that does not exist,
demotion-rehearsal that does not exist, a normalized cost denominator, a structural
anti-Goodhart mechanism, dispatch evidence schema, sunset register. Several items
are corrections to v5 claims rather than additions.

**Proceed to v6 prose drafting.** Recommended order: §7 first (heaviest delta,
includes mj11.1 + mj11.2 specs which need to be referenceable from the prose);
then §5 + §8 (the other heavy-delta sections); then revisions; then triage table
last (compiles findings into one place once §1-§19 are settled).

# Open work surfaced by the outline

Beyond mj11.1 and mj11.2, the outline implies these additional child beads under
mj11:

1. **System Trust formula change** (min → criticality-weighted percentile) —
   §6 + §5.3
2. **Substrate-independence load-path audit** — §4 substrate-dependency table +
   §7.6 debt registry
3. **Demotion-rehearsal harness** on FluxBench — §7.5 (overlaps `sylveste-v3ck`
   already filed; check before duplicating)
4. **Cost normalization instrumentation** (per-line / per-complexity series) —
   §8.1
5. **Cache-corrected cost-query.sh extension** — §8.2
6. **Held-out task set + quarterly anti-Goodhart eval** — §8.4
7. **Routing/dispatch evidence schema in Intercore** — §8.5
8. **Auto-archive policy for stub/used agents** — §8.6
9. **Bead `closure_reason` field instrumentation** — §14
10. **Cost-figure colophon instrumentation** — §11
11. **Per-subsystem promotion criteria publication** (Persistence, Coordination,
    Discovery, Review, Integration, Ontology, Measurement, Governance) — §6
12. **Interspect Break-scoring** — §7.1
13. **Counterfactual tracking on Interspect proposals** — §5.2
14. **Forward-looking epoch calendar** — §7.11

These should be filed as child beads of mj11 *after* the v6 prose is drafted, so
the prose can authoritatively cite their bead IDs. Filing them before drafting
risks scoping work that doesn't ultimately make the cut.
