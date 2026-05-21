---
artifact_type: brainstorm
method: flux-explore
target: "Sylveste evidence flywheel: an autonomous AI agent platform that earns trust through receipts."
rounds: 2
total_agents: 4
date: 2026-04-26
---

# Flux-Explore — Sylveste Evidence Flywheel

## Per-Domain Highlights

### fd-autonomy-ladder-progression (`.claude/agents/fd-autonomy-ladder-progression.md`)
- Promotion and demotion must be **symmetric and explicit**: every M-tier transition needs a counter-criterion that triggers the reverse move. Asymmetric gates ratchet trust upward without recovery, which is how progressive-delivery systems silently accumulate latent failure.
- **Hysteresis bands** prevent thrash: a pillar that just demoted from M3→M2 cannot re-promote on the same evidence window that triggered demotion. Transfer: Sylveste's Earn/Compound/Epoch/Demote cycle needs an explicit cooldown plus a re-qualification window distinct from the original promotion window.
- **Blast-radius scoping** per tier: M-level should bound not just trust claims but the surface area a pillar can affect during promotion. A newly-M3 Clavain shouldn't immediately exercise M3-scope authority; the rollout needs canary cohorts within the cohort of one user.

### fd-model-routing-economics (`.claude/agents/fd-model-routing-economics.md`)
- **Routing decisions as first-class evidence**: every tier-selection (Haiku vs Sonnet vs Opus) is recorded with rationale, fallback chain, and realized cost. Transfer: Ockham's dispatch decisions and Clavain's gate-tier choices should emit the same structured-evidence shape Interspect already consumes for hooks.
- **Cache-hit economics shape the trust signal**: a pillar appearing cheap may be riding cache; trust-per-dollar must be normalized against cache-warmth or it inflates falsely. Transfer: cost-per-landable-change baseline ($2.93) should report a cache-corrected variant alongside the headline number.
- **Attributable spend per pillar**: routing economics insists every dollar trace to a routing decision; mirrors Sylveste's "evidence per subsystem" ambition but adds the spend dimension explicitly.

### fd-noh-jo-ha-kyu (`.claude/agents/fd-noh-jo-ha-kyu.md`)
- **Climax-legitimacy is borrowed from opening-patience**: a pillar's M4 declaration is only legitimate if the M0→M2 phase was unhurried. Skipping the "ha" break-open phase (where contradictory evidence is actively surfaced) produces a counterfeit kyū — a confident pillar with no break tested.
- **Recursive nesting**: jo-ha-kyū applies at the gesture, scene, and play level simultaneously. Transfer: trust rhythm should hold within a single change, within a sprint, and within an epoch — and the rhythms must be independently observable, not collapsed into one composite metric.
- **The "ha" phase is where trust is actually earned**: not in slow build (jo) nor in confident execution (kyū), but in the explicit break where the system must reveal its own contradiction. Sylveste currently lacks a named "break" stage in the lifecycle.

### fd-cathedral-keystone-loadpath (`.claude/agents/fd-cathedral-keystone-loadpath.md`)
- **Every element's thrust must trace to ground through redundant paths**: no pillar may be load-bearing for trust unless at least two independent evidence paths reach an unconditionally-trusted floor. Transfer: Interspect auditing the kernel it runs on is a single-path load — the cathedral mason would refuse this construction.
- **Keystone-last sequence**: the pillar that closes the arch (the one whose trust completes the flywheel) must be set after every supporting course is self-sustaining. Declaring Autarch trustworthy before Intercore is M3 is "keystone on uncured mortar."
- **Centering-frame removability**: every element must be replaceable via temporary scaffolding without collapse. Transfer: any pillar at M3+ must have a documented demotion procedure that holds the system up while the pillar is rebuilt — and this procedure must have been exercised, not just specified.

## Cross-Domain Structural Isomorphisms

### Order-of-construction matters more than per-element quality
- **Agents**: cathedral-keystone-loadpath, noh-jo-ha-kyu, autonomy-ladder-progression
- **Mechanisms**: keystone-last sequencing (mason); jo legitimizes kyū (Noh); promotion-cohort ordering with blast-radius scoping (SRE).
- **Abstract principle**: the legitimacy of a high-trust state is a function of the sequence of states that produced it, not just the current evidence. A pillar that passes M3 criteria via a different path than the canonical one is a different artifact.
- **Sylveste mapping**: the trust lifecycle should record promotion-path provenance, not just current M-level. Two pillars at M3 reached via different sequences are not interchangeable; Ockham's dispatch authority should weight them differently.

### Symmetric reversibility as a precondition for trust
- **Agents**: autonomy-ladder-progression, cathedral-keystone-loadpath
- **Mechanisms**: hysteresis-banded promotion/demotion (SRE); centering-frame removability (mason — every stone removable without collapse).
- **Abstract principle**: trust is granted only to elements whose removal procedure has been demonstrated. Irreversible promotion is not promotion; it is commitment.
- **Sylveste mapping**: M3+ promotion gates should require a successful demotion-rehearsal as part of the evidence bundle. The Demote phase isn't a failure mode — it's a precondition for Earn.

### Evidence must be independent of the substrate it audits
- **Agents**: cathedral-keystone-loadpath, model-routing-economics, noh-jo-ha-kyu
- **Mechanisms**: redundant load paths to ground (mason); routing rationale recorded outside the router (LLM platform); the "ha" break must come from outside the performer's intent (Noh — the audience and form, not the actor, surface the contradiction).
- **Abstract principle**: self-audit is not audit. A subsystem's evidence about itself must terminate in a path that does not pass through that subsystem.
- **Sylveste mapping**: Interspect running on the kernel it audits is the central architectural debt. Either Interspect needs an independent execution substrate, or its kernel-audit findings must be marked as a distinct evidence class with lower trust-weight than findings about other pillars.

### Cost/economics as a trust signal, not a separate axis
- **Agents**: model-routing-economics, autonomy-ladder-progression
- **Mechanisms**: cache-corrected cost-per-task (router); blast-radius proportional to tier (SRE — implicitly an economic claim about acceptable damage).
- **Abstract principle**: trust and cost are coupled. A pillar whose cost is unexplained is a pillar whose behavior is unexplained.
- **Sylveste mapping**: cost-per-landable-change should be decomposed per-pillar and per-routing-decision, not aggregated. An unexplained cost delta is itself a demotion signal.

## Novel Mechanism Transfers

### The "ha" break-open stage in the trust lifecycle
- **Source**: Noh theatre, fd-noh-jo-ha-kyu. In Zeami's doctrine, jo (slow build) and kyū (rapid finish) are connected by ha — a deliberate break where the established pattern is contradicted, exposing the form's structure.
- **Mechanism**: between Compound and Epoch, insert an explicit Break stage where the pillar must surface evidence that contradicts its own promotion case. Not adversarial testing imposed externally — self-surfaced contradictions, recorded as evidence.
- **Sylveste mapping**: modify the trust lifecycle in the v5 vision: Earn → Compound → **Break** → Epoch → Demote. Ockham enforces Break: a pillar cannot Epoch without N self-surfaced contradiction-receipts in the Compound window.
- **Benefit**: removes the failure mode where confident pillars accumulate compounding evidence in only their favor (the "counterfeit kyū").
- **Risk**: pillars game Break by surfacing trivial contradictions. Mitigation: contradiction-severity scored by Interspect, not the pillar.

### Demotion-rehearsal as promotion precondition
- **Source**: Gothic masonry, fd-cathedral-keystone-loadpath. A vault is not declared complete until centering is removed and re-installed cleanly — the removal exercises the load path.
- **Mechanism**: M3+ promotion requires a successful rehearsal of the demotion procedure within the evaluation window, with the system observed to remain functional during the simulated demotion.
- **Sylveste mapping**: extends Skaffen's gate-tier criteria. Each pillar's `MATURITY.md` (or equivalent) must include a demotion runbook that has been executed end-to-end, with FluxBench harness recording the substrate's behavior during the rehearsal.
- **Benefit**: catches pillars whose demotion is theoretical-only — currently the most likely place for hidden coupling.
- **Risk**: rehearsal cost. Mitigation: rehearse on FluxBench substrate, not production.

### Routing-decision evidence schema, applied to Ockham dispatch
- **Source**: LLM platform engineering, fd-model-routing-economics.
- **Mechanism**: every routing decision emits {chosen-tier, considered-alternatives, rationale-tag, fallback-chain, realized-cost, cache-state}. Recorded as structured evidence, queryable.
- **Sylveste mapping**: Ockham's dispatch decisions and Clavain's gate-tier selections adopt this schema. Interspect ingests it. The corpus becomes the input to a distilled xgboost classifier (already the intercept project's pattern) for future dispatch.
- **Benefit**: dispatch becomes auditable evidence rather than opaque infra; closes the loop with intercept's existing distillation pipeline.
- **Risk**: schema drift between Ockham, Clavain, and intercept. Mitigation: schema lives in Intercore as a shared type.

### Load-path independence audit for the evidence-infra ring
- **Source**: Gothic masonry, fd-cathedral-keystone-loadpath.
- **Mechanism**: for every cross-cutting subsystem (Interspect, Ockham, Interweave, Interop, Factory Substrate), trace the dependency path from its evidence-emission to an unconditionally-trusted floor. Mark single-path loads as construction defects.
- **Sylveste mapping**: a one-time audit producing a load-path diagram of the evidence flywheel. Interspect almost certainly fails first (audits its own kernel). Document as a known structural debt with a planned redundant path (e.g., periodic external replay of Interspect findings on a frozen kernel snapshot).
- **Benefit**: makes the "evidence compounds per-subsystem" claim defensible by showing the compounding is actually independent.
- **Risk**: discovers more single-path loads than can be remediated near-term. Mitigation: explicit debt registry with prioritization, rather than silent assumption of independence.

### Cache-corrected cost-per-landable-change
- **Source**: LLM platform engineering, fd-model-routing-economics.
- **Mechanism**: report two numbers — headline cost and cache-warmth-corrected cost. Track the gap as a separate signal.
- **Sylveste mapping**: extends interstat's existing cost-query.sh. Adds a cache-state column to session metrics; the divergence between cached and uncached cost-per-landable-change becomes a watch-metric.
- **Benefit**: protects the $2.93 north-star from quiet inflation as the corpus warms.
- **Risk**: low — purely additive metric.

## Open Questions

- **Immune systems / clonal selection (biology)** — expected insight: how a system distinguishes self-evidence from non-self-evidence without a central authority. High value for the "Interspect audits its own kernel" problem; offers decentralized-verification mechanisms with no methodological overlap with software audit.
- **Double-entry bookkeeping (15th c. Venice)** — expected insight: every transaction recorded twice in independent ledgers that must reconcile. Direct map to evidence-independence requirement; medium-high value, possibly redundant with cathedral load-path findings.
- **Naval prize courts (18th c. admiralty law)** — expected insight: adjudication of captures by courts independent of the capturing vessel; a procedural answer to self-audit. Medium value; specific to the Interspect problem.
- **Sourdough starter maintenance** — expected insight: continuous-culture stewardship under contamination pressure; how a long-lived evidence corpus stays trustworthy across personnel and substrate changes. Medium value for the Compound phase specifically.
- **Constitutional amendment procedures** — expected insight: meta-rules for changing the rules; how the trust framework itself gets revised without the revision laundering trust. High value, directly addresses the v5 vision's own promotion path.
- **Surveying / triangulation (pre-GPS cartography)** — expected insight: position fixed only by sightings to multiple known points; closure-error as a quality signal. Medium value, formalizes the redundant-load-path principle quantitatively.
- **Glassblowing annealing schedules** — expected insight: stress-relief cycles required after forming, where skipping anneal causes delayed catastrophic failure. Medium value for the Epoch phase — formalizes "rest before declaring done."
