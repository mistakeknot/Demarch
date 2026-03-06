---
bead: iv-sksfx.1
date: 2026-03-05
type: research
status: draft
---

# Offline Routing Evals and Safe Canary Policy

**Question:** What evaluation and rollout policy should Demarch use before routing overrides are trusted broadly?

## Executive Summary

1. Routing overrides should use a two-stage gate: **offline counterfactual evaluation first, live canary second**. Pattern counts alone are not enough, and rollout should begin in **shadow mode**, not immediate enforcement.

2. The unit of evaluation should be a **review opportunity**: a completed routing decision with its candidate set, selected agents, resulting findings, review resolutions, and cost. For exclusion policies, the counterfactual is "what would have happened if this agent had not run?"

3. The primary quality signals should come from **typed review outcomes** and later outcome attribution, not raw override counts. Until landed-change attribution is canonical, accepted/disagreed findings are the best available correctness surface.

4. Current replay and canary surfaces are useful but not autonomy-grade. Intercore can record replay inputs and typed review events, but replay reconstruction still focuses on phase/dispatch transitions, `interspect_events` are still off the main bus, and current canaries are based on project-global session metrics with overlapping-canary confounding.

5. The safe near-term policy is: use offline eval to decide whether a routing override is canary-eligible, keep **safety floors** active regardless of routing experiments, use canaries only for **project-scoped, low-risk exclusions**, and keep **human-triggered revert** as the only rollback path until attribution and cohorting are stronger.

## What Decision Is Being Evaluated

For this bead, the decision is not "is an agent sometimes wrong?" It is:

`Given project P and task/routing context C, should agent A be excluded from the routing set for some period of time?`

That decision needs more context than the current override evidence table alone. A trustworthy evaluation record needs:

- routing context: project, phase/task class, policy version, candidate agents, selected agents, excluded agents
- execution context: runs, dispatches, models, cost, latency
- review context: findings by agent, disagreement resolution, severity/impact
- outcome context: later landed/reverted/escaped outcome when available

Without that full record, routing policy is judged on a narrow proxy instead of actual review quality.

## Current Usable Surface

The repo already has important building blocks:

| Surface | What exists now | Why it matters |
|---|---|---|
| Replay input store | `run_replay_inputs` table plus `ic run replay` simulate/reexecute flows | There is already a kernel place to record deterministic replay inputs |
| Typed review events | `review_events` store `finding_id`, `agents_json`, `resolution`, `dismissal_reason`, `chosen_severity`, `impact`, `session_id`, `project_dir` | This is the best current correctness signal |
| Typed interspect events | `interspect_events` capture correction/dispatch signals | Human correction evidence is durable |
| Routing override state | project-local `routing-overrides.json` plus modification/canary records | Current rollout mechanism exists |
| Canary monitoring | 20-use / 14-day window, baseline/sample storage, thresholded alerting | There is already a live rollout safety hook |

But there are still important gaps between "exists" and "is sufficient for policy trust."

## Current Validity Limits

### 1. Replay is still decision-centric, not outcome-centric

`ic run replay` can reconstruct deterministic timelines from event and replay-input data, but the reconstruction path currently keeps only **phase** and **dispatch** decisions. Review events create replay inputs, yet replay reconstruction does not currently rebuild review or interspect outcome timelines.

That means replay is good at answering:

- what phases and dispatches happened?
- which nondeterministic inputs were attached?

It is not yet good at answering:

- which findings would have been lost under a different routing policy?
- which disagreement outcomes or correction signals should score the counterfactual?

### 2. The generic event bus is still incomplete for this use case

`review_events` appear in `ListAllEvents`, but with flattened fields. `interspect_events` remain on a typed side path instead of the global stream. That leaves routing evaluation split across multiple surfaces.

### 3. Current canaries are cohort-light and confounded

The current canary implementation is pragmatic but weak as a policy judge:

- baselines are computed with an empty project filter at override-apply time
- per-session samples are written to **every active canary**
- metrics are project-global proxies (`override_rate`, `fp_rate`, `finding_density`), not agent- or cohort-specific quality outcomes
- the implementation already notes confounding when multiple active canaries overlap

This is enough for "something changed after this override" alerts. It is not enough for trustworthy attribution of *which* override helped or hurt.

### 4. Canary implementation integrity is itself a rollout gate

The surrounding review docs also show why "the metrics exist" is not the same as "the canary is trustworthy." Recent plan/code reviews called out failure modes around sample-write locking, split-brain states where an override can commit without durable canary/DB records, and other correctness issues in the hook-local path.

So the policy should treat **canary implementation verification** as part of the eligibility gate:

- no known P0 correctness defects in baseline/sample/verdict storage
- override activation and canary record creation must fail or succeed together from the operator's point of view
- canary samples must be concurrency-safe
- advisory canaries are acceptable while these are being hardened, but enforcement-grade promotion is not

### 5. Session/bead/run joins are still being hardened

The previous `iv-544dn` research remains directly relevant: until the attribution chain is durable, routing outcomes are still only partially joinable to broader quality/economics metrics.

## Recommended Offline Eval Method

### Evaluation unit

Use a **review opportunity** as the canonical offline-eval row:

`(routing decision, selected agents, findings, review outcomes, cost, project/task metadata)`

For routing exclusion, construct rows only from historical opportunities where the candidate agent actually ran.

### Counterfactual family for v1

Start with one counterfactual only:

`exclude agent A from historical routing decisions where A was selected`

For each historical opportunity:

1. remove the excluded agent's cost and latency contribution
2. remove findings attributable to that agent
3. recompute outcome proxies using the remaining agents
4. compare baseline vs simulated-exclusion outcome

This gives a clear answer to the question that matters now: did excluding this agent historically save cost without dropping meaningful review signal?

### Corpus eligibility

A run should enter offline evaluation only if all of the following are true:

- completed run / completed review opportunity
- routing decision can be identified
- selected agents are known
- findings can be attributed back to producing agents
- typed review outcomes exist for the findings
- cost data exists for the participating dispatches

Anything less should be excluded from the scored corpus rather than guessed.

### Scoring

Use two score layers.

#### Primary quality score

This decides whether a candidate is eligible for canary:

- **critical rule:** zero loss of accepted high-severity / high-impact findings in the offline corpus
- **coverage rule:** no more than 5% loss in total accepted findings attributable to the removed agent
- **precision rule:** disagreement-adjusted precision must improve or remain flat

If a candidate fails the critical rule, it does not enter canary.

#### Secondary economics score

This decides whether the candidate is worth trying even if quality is flat:

- token cost saved
- wall-clock / latency delta when available
- reduction in total findings needing human review

Recommended admission threshold: projected median cost reduction of at least 10% in the affected routing cohort, unless the quality gain alone is compelling.

### Minimum offline evidence window

For a candidate routing exclusion to enter canary:

- at least 20 historical review opportunities in the scored cohort
- at least 10 opportunities where the candidate agent actually ran
- at least 3 sessions and at least 2 distinct projects or 2 distinct task classes for general-purpose agents
- cross-cutting / safety agents never auto-qualify; they remain propose-only

These numbers are conservative but consistent with the existing 20-use canary window and the current counting-rule style used elsewhere in Interspect.

## Recommended Live Canary Policy

### Canary cohort

The canary should be scoped as narrowly as possible:

- one project
- one excluded agent
- one routing context family if available (review/task class/domain)

Do not run overlapping canaries that affect the same cohort unless the system can explicitly model interaction effects.

The first eligible cohorts should be:

- non-cross-cutting agents
- stable projects with enough historical traffic
- repos already protected by routing safety floors

Rare agents, cross-cutting agents, and safety-critical agents should remain propose-only unless a human explicitly opts in.

### Entry criteria

An override becomes canary-eligible only if:

- it passes offline eval
- it is not a cross-cutting / safety-critical exclusion, or a human explicitly approves the extra risk
- baseline data exists for the target cohort, or the canary is explicitly marked observational-only
- there is no other active canary in the same cohort
- the canary implementation path itself has passed correctness verification for the active code version

### Canary window

Keep the current window as the default:

- 20 uses or 14 days

But interpret a "use" as a **completed review opportunity in the target cohort**, not just any session that emitted evidence.

### Canary metrics

Use two tiers of metrics.

#### Tier A: required decision metrics

These should determine pass vs alert once instrumentation exists:

- accepted-finding retention
- accepted high-severity / high-impact finding retention
- later defect-escape or revert signal, when attribution is available

#### Tier B: interim proxy metrics

These are acceptable for v1 alerting, but not for autonomy-grade promotion:

- override rate
- disagreement-adjusted false-positive rate
- finding density

### Thresholds

Recommended default thresholds:

- **hard alert:** any attributable loss of accepted high-severity / high-impact findings
- **proxy alert:** >20% degradation vs baseline on proxy metrics, with a 0.1 absolute noise floor
- **pass:** no hard alerts and all proxy metrics within threshold at window close

### Stick, expire, or revert

At canary completion:

- **stick / promote** when the override passes and no governance rule is violated
- **expire** when traffic is too low to judge, when project/roster shape changes materially, or when a human edit invalidates the baseline
- **recommend revert** when a hard alert or repeated proxy alert fires

Current recommendation: keep **manual revert** as the only rollback action. Alerting can be automatic; reversion should not be, because attribution is not yet strong enough to trust a fully automatic rollback loop.

## Rollout Stance

The right rollout order is:

1. **shadow only** for new routing logic and calibration layers
2. **enforce only for narrow canary cohorts**
3. **broader enforcement only after attribution and canary integrity are trustworthy**

This matches the broader routing direction in the repo: quality floors come before token optimization, and shadow telemetry must not be bypassed by fast paths.

## Minimum Instrumentation Needed

The current system can support exploratory rollout, but these additions are needed before routing overrides become autonomy-grade.

### 1. Record routing decisions as replayable facts

Each routing decision should durably capture:

- candidate set
- selected set
- excluded set
- policy version
- task/routing context
- why the candidate won or lost

Without this, offline evaluation has to reconstruct the decision from side effects instead of facts.

### 2. Extend replay from dispatch/phase to review/outcome analysis

Replay needs to preserve and reconstruct:

- review outcomes with full fidelity
- interspect corrections with lineage
- finding-to-agent attribution

Today, replay inputs exist for review events, but reconstruction is still centered on phase and dispatch decisions.

### 3. Make the event surface complete enough for one-pass consumers

For routing evaluation, one consumer should be able to read the relevant evidence without stitching together partial buses and side APIs. That means:

- preserve typed review fields as a first-class contract
- expose interspect evidence through the same measurement-grade surface

### 4. Scope canary baselines and samples to the actual cohort

Baselines and samples should be:

- project-scoped
- cohort-scoped where possible
- aware of overlapping active overrides

Current project-global sampling is too confounded for strong claims.

### 5. Finish durable attribution joins

The `session -> bead -> run -> outcome` chain still matters here. Routing policy can be evaluated with review outcomes first, but long-horizon trust still depends on durable links to landed, reverted, and escaped outcomes.

## Recommended Sequence

1. Use the existing pattern-detection logic only to surface **candidates**, not winners.
2. Add routing-decision capture and review/outcome replay support.
3. Implement offline scoring for single-agent exclusion counterfactuals.
4. Limit live rollout to one low-risk project-scoped canary at a time.
5. Treat current proxy-metric canaries as advisory until the attribution and cohorting gaps are closed.

## Bottom Line

The right answer is not "ship more routing overrides once enough override evidence accumulates." The right answer is:

`candidate detection -> offline counterfactual score -> narrow live canary -> human-governed promotion or revert`

Demarch already has enough substrate to begin this flow, but not enough to trust it blindly. The missing pieces are not exotic ML; they are measurement integrity, cohort definition, and replayable routing facts.
