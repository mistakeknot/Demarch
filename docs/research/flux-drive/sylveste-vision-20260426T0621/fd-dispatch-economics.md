# fd-dispatch-economics — Review of sylveste-vision.md v5.0

**Lens:** MLOps practitioner auditing mixed-model agent fleets for cost variance and Goodhart drift.
**Decision question:** Does the cost trajectory ($1.17 → $2.93) reflect genuine improvement or improvement-via-spending-more-on-review, and how would the doc distinguish?

## P0 Findings

### P0-1: Cost-per-landable-change is not normalized for change size
The metric is the doc's named north star, but the doc never defines the denominator's normalization. A "landable change" is presumably a merged commit, but commits range from one-line typo fixes to thousand-line feature implementations. Without per-line or per-complexity normalization, the metric is a function of the workload mix as much as of the system. The trajectory $1.17 → $2.93 (described as "expanded review scope rather than efficiency regression") is offered as an interpretation, but the metric structurally cannot distinguish those two stories.
**Fix:** Define a normalized variant — cost per N-line landable change, or cost per task-of-typed-complexity. Publish both raw and normalized series. The doc's own cost-baseline note suggests this is needed to read the trajectory honestly.

### P0-2: Goodhart caveat acknowledged, not engineered
The doc names the Goodhart problem ("Any stable metric becomes a target … rotate emphasis, diversify, watch for agents optimizing"). All three mitigations are operator behaviors, not system properties. Agents in the loop will, over time, learn to satisfy the metric. The system has no anti-Goodhart counter-mechanism (e.g., shadow metrics that the optimizer can't see, periodic blind-eval runs against held-out tasks).
**Fix:** Commit to at least one structural anti-Goodhart mechanism — e.g., a held-out task set evaluated quarterly that the routing system has never seen, with the result published as a check on the live metric.

## P1 Findings

### P1-1: 589-agent fleet has no tail-management story
"~589 review agents (12 specialized + generated fleet)" is named in "Where We Are" with no companion claim about utilization. With per-tier scoring (stub/generated/used/proven) and a registry, the data exists to identify the long tail. The doc could say "of 589, N are tier=proven and contribute X% of findings" but doesn't. The flux-agent prune capability exists but isn't part of the vision's discipline.
**Fix:** Add a "fleet hygiene" commitment to the vision — e.g., agents that don't reach tier=used within Y sprints are auto-archived. Surface fleet utilization in the metric table.

### P1-2: Opus-95%-of-cost is a structural fact dressed as an incidental one
Feb 2026 baseline: "Opus 95% of cost." This is the Sylveste cost story in one number — almost everything spent goes to Opus reasoning. The doc says the "trajectory is expected to improve as model routing matures" but the ratio is not just a routing question; it is a question of which decisions actually need Opus. The vision could commit to "Opus share below X% by date Y" as a derived target.
**Fix:** Add an Opus-share trajectory commitment, or explicitly defend the 95% as the right structure.

### P1-3: Evidence quarantine (48h) is offered without a derivation
"Evidence quarantine (48h delay before influencing routing) shipped." The number is presented as a fact. The doc earlier discusses evidence freshness implicitly but never derives 48h. Too short for slow drifts (a Tuesday sprint regression isn't visible until Thursday and may have already polluted Wednesday's runs); too long for sharp regressions (a Tuesday morning bad model rev produces 48 hours of wasted spend before quarantine releases).
**Fix:** Specify the quarantine window as a function of evidence tier. Tier-1 controlled experiments: short or zero quarantine (already controlled). Tier-2 observational: longer. Tier-3 anecdotal: should not influence routing at all without escalation.

### P1-4: North star metric has no confidence interval
"$2.93/landable change" is reported as a point value. Across what sample? What's the variance? $2.93 with σ=$2.00 is a different story from $2.93 with σ=$0.30. The doc's own caveat "watch for agents optimizing the metric" is harder to act on without a sense of the metric's precision.
**Fix:** Report mean ± stddev, sample size, and date range. The interstat infrastructure already supports this.

## P2 Findings

### P2-1: Per-sprint cost reported but not per-bead-type stratified
The 1,456-bead corpus contains sprints of widely different shape (epic decomposition vs single-feature vs hotfix). Cost rolled up across all of them obscures whether the system is cheap on hotfixes and expensive on features, or vice versa.

### P2-2: Reaction-round and multi-track review cost is acknowledged as the source of $2.93
"Increase reflects expanded review scope (multi-agent review, reaction rounds)." Good honesty, but the doc doesn't say whether the expanded review is paying for itself in defect-escape-rate reduction. The Quality column of the metric table has "Defect escape rate" listed — its value is not reported.

### P2-3: Model routing accuracy metric has no baseline
"% of model selections matching the outcome-optimal model" is in the table. Is this measured today? At what value? Without a baseline, it cannot be tracked.

## Summary
The cost story is the most measurable part of the vision and the part with the most undefended assertions. The metric is named, but its denominator, its decomposition, and its anti-Goodhart properties are all hand-waved. This is the easiest part of the document to harden.
