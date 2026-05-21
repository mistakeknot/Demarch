# fd-trust-mechanics — Review of sylveste-vision.md v5.0

**Lens:** Security engineer auditing graduated-authority systems for blast radius and revocation latency.
**Decision question:** If a subsystem misbehaves at 3 AM Saturday, does the trust architecture constrain blast radius, or merely document a philosophy of constraint?

## P0 Findings

### P0-1: Demotion latency is unbounded
"Demotion is graduated, not instant" is stated as a virtue, but the doc never specifies an upper bound. "Sustained degradation … exceeding threshold for a defined observation window" — what window? If a subsystem at M3 begins emitting bad routing decisions, does it keep emitting them for hours? Days? An attacker, or a regression, has a free observation window of unspecified length to do damage.
**Fix:** Specify per-tier demotion windows. Critical-tier (Governance): hours. High-tier (Routing, Persistence, Review, Integration, Measurement): hours-to-day. Medium-tier: day-to-week. The doc has criticality tiers — use them.

### P0-2: Trust transfer protocol on subsystem replacement is a vibe-check
Auraken→Skaffen migration is named as the test case. The doc says the replacement gets "probationary access … with a verification period" and "actual behavior is compared against the inherited evidence profile." No verification period length, no comparison threshold, no abort criteria. In practice, this means trust transfer is whatever a human decides it is at the time of migration.
**Fix:** Specify (a) probation duration in calendar time and sprint count, (b) what counts as "equivalent or better performance" with concrete metrics, (c) the rollback procedure if probation fails.

## P1 Findings

### P1-1: Epoch triggers are loose
Named triggers: "major model API change, an architecture migration, a subsystem replacement." Each is undefined. Is moving from claude-opus-4.5 to claude-opus-4.6 a major API change? (The model card moves a fingerprint changes, but the API surface might not.) Is replacing the SQLite WAL mode an architecture migration? Different operators will draw the line in different places, and the line determines whether evidence is preserved or partially reset.
**Fix:** Provide a decision rubric — model API change is "major" if it changes the cost function, the latency profile, or the answer distribution on a held-out eval set. Architecture migration is "major" if it changes the kernel SQL schema, event taxonomy, or layer boundary.

### P1-2: weakest-link min() trust creates a perverse incentive
System trust = min(maturity across M1+ cells). This means a team that ships a new subsystem at M1 immediately drags system trust down. The rational play is to keep work in M0 (planned) for as long as possible to avoid the floor calculation, then promote everything at once. The doc acknowledges balancing loops but doesn't see this incentive.
**Fix:** Either (a) weight the min() by criticality so a non-critical M1 doesn't drag a critical M3 system down, or (b) move from min() to a percentile (10th-percentile maturity), which preserves the "weakest link" intuition without punishing parallel investment.

### P1-3: Cascade demotion in DAG is asserted but not specified
"Demotion … propagates to dependent subsystems." Does Routing demote when Measurement demotes by one level? By two? Is it synchronous (Routing demoted immediately) or evidence-driven (Routing demoted when its own evidence reflects the upstream regression)? The dependency DAG is named but the cascade rule is not.
**Fix:** Specify cascade rule: e.g., "any demotion of an upstream cell caps downstream cells at upstream-maturity until they re-prove."

### P1-4: Human authority reservation can be subverted by audit-trail gaps
"Evidence thresholds are revisable by human authority regardless of accumulated evidence." Good. But the doc doesn't specify that the human override itself is logged, witnessed, or rate-limited. A high-trust agent that can write to the threshold config has an effective unbounded authority through a single edit. The principle is good; the mechanism around it is missing.
**Fix:** Treat threshold revisions as a Tier-1 evidence event with their own immutable log, signature, and reviewer-other-than-author requirement.

## P2 Findings

### P2-1: In-flight work continues at lower trust level — but quality is unknown
"In-flight work continues at the lower trust level." What does this mean operationally? If a Critical-tier (Governance) subsystem demotes mid-sprint, does the sprint complete with reduced authority, abort, or pause? The doc doesn't say.

### P2-2: No counter-evidence channel for human overrides
When a human overrides a routing decision, does Interspect log that as Tier-1 evidence against the prior decision? The interspect-correction skill exists but is not referenced in the trust architecture. The loop is open: human corrections don't formally compound into the trust model.

### P2-3: Trust transfer doesn't address the "bigger replacement" case
The Auraken→Skaffen example is module-scale. What about kernel replacement? The doc says "the kernel and all its data survive" but doesn't address what trust transfer looks like if Intercore itself is replaced (e.g., Postgres backend, distributed kernel).

## Summary
The trust lifecycle is well-named and poorly bounded. The four phases (Earn/Compound/Epoch/Demote) are the right vocabulary, but each phase has at least one critical timing/threshold parameter unspecified. The doctrine survives a friendly read but not an adversarial one.
