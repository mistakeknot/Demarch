# fd-systems findings — microrouter deferral PRD

## P0 findings

### P0.1 — Heuristic-stratified eval split is ergonomic window-dressing, not a thermometer

The PRD names heuristic-stratified eval split as the "minimum required mitigation" before `.19.3` LoRA training (Caveat 1 mitigation pre-registration). This is framed as addressing the P0 from the brainstorm synthesis ("β's circularity is deferred, not broken"). But the PRD glosses over a critical dynamic: **stratified measurement is descriptive (measures a gap) not prescriptive (closes the gap)**. 

The PRD cites heuristic-stratified eval as "most diagnostic" — it explicitly answers "does the router beat heuristic on heuristic-hard cases." But asking the question is not the same as fixing the problem. When `.19.3` design phase reviews the stratified-eval results and finds the router only beats heuristic on 5% of hard cases (but heuristic already covers 95% of easy cases), the router is still a marginal improvement that learned to imitate the heuristic, not to do strictly better.

**The feedback loop is: heuristic → outcome accumulation → router learns heuristic+noise → eval finds router≈heuristic → decision pressure to ship anyway because four sprints are "done."** The stratified-eval mitigation is a thermometer showing the temperature of this problem, not a thermostat that fixes it. 

**Implication for PRD:** Requiring heuristic-stratified eval split before `.19.3` ships is sound practice (gives visibility into the loop). But without one of the three other mitigations (off-policy randomization, manual-override weighting, loss penalty), the PRD *promises* risk-reduction without *delivering* it. The PRD should either: (a) explicitly require one of the other three to land before `.19.3` starts, OR (b) reframe heuristic-stratified eval as a pre-mortem diagnostic tool that informs a `.19.1` design decision (i.e., "if stratified eval shows <10% headroom on hard cases, escalate to γ or close epic"), not as a mitigation.

---

## P1 findings

### P1.1 — D2 checkpoint coordination is a veto gate disguised as a checkpoint

The PRD designates D2 as a **CHECKPOINT (not a gate)** with explicit language: "If D2 says 'kill epic' before 2026-06-30, immediately re-open `.19.10` and close epic. If D2 hasn't run by 2026-06-30, run it BEFORE resuming `.19.1`."

This creates a causal chain: D2 result → decision to kill/proceed → `.19.10` re-opened if kill. But the PRD never specifies *who receives the D2 signal* or *when they must act*. The phrase "immediately re-open .19.10" appears to assume the operator reads D2's output and makes a decision. If D2 runs at week 5 but the operator doesn't check the result until week 8 (deferral deadline), the "immediately" is past tense.

**The real feedback loop is: D2 runs → result written to disk → operator eventually sees it → operator decides → .19.10 state changes.** With no polling, no alert, no escalation trigger for "D2 returned kill, awaiting operator decision," the checkpoint becomes a passive measurement divorced from control. Schelling-trap risk increases: if D2 returns "kill epic" at week 3, and the operator misses the signal, and the deferral deadline approaches, there's implicit pressure to declare D2 "inconclusive" and proceed anyway because 7 paused beads are blocking downstream work.

**Implication:** F3's keep-alive cadence partially addresses this (two-sprint check-ins would surface D2 results). But the PRD does not require the check-in protocol to *explicitly verify D2 status* at each check-in. Add: "At each `deferral_check_in`, operator confirms: (1) has D2 run? If yes, (2) what was the result? If D2 says 'kill epic,' close `.19.10` and end deferral."

### P1.2 — Sprint-counting OR-condition is gameable under deadline pressure

The operational definition for "4 sprints" states: **"One sprint = one calendar week OR one full `.beads/` close burst of ≥5 closed beads with verdict_status set, whichever produces more data."**

This is an OR-gate that allows the operator to satisfy either temporal OR volumetric thresholds. Under deadline pressure (approaching 2026-06-30), this creates a Schelling trap: if the calendar hits day 28 (4 weeks) but volume is still low, the operator can declare "we've hit the calendar gate, proceed to resume .19.1." Conversely, if volume is low but a large `.beads/` burst happens (e.g., a sprint closes 8 beads), the operator can declare "we've hit the volume gate, proceed."

The trap manifests when:
- Week 3: volume is 30 verdicts per cell (target: 80), calendar shows 21 days elapsed
- Week 4: volume still 45 per cell, but a coincidental closure burst happens (6 beads close in one day)
- Operator faces: "Volume is insufficient, but we have a burst. Calendar is almost 4 weeks. Pick whichever satisfies first."

**The feedback loop is: deadline approaches → lower bar gets emphasized → whichever gate could plausibly be declared first → gate declared reached → deferral ends early with weak data.**

The PRD attempts to lock thresholds pre-registration ("pin operational definitions before accumulation begins"), but the OR-condition itself is the gameable surface. Once accumulated, the data is sunk; reversing course (extending deadline) looks like wasted time.

**Implication:** F3 should specify: "If 4 calendar weeks elapse but volume < 60 verdicts per cell for stable-7, automatically extend `deferral_check_in` by 2 sprints and do not resume `.19.1`." Make the volume threshold the primary gate; clock-time is secondary (capped at some absolute date like 2026-07-30 to prevent indefinite deferral).

### P1.3 — Auto-revert action depends on a routing-related sprint actually running after 2026-06-30

F3 specifies: `auto_revert_action=run-D2-then-resume-decision` — "if 2026-06-30 passes without explicit human decision, the next routing-related sprint runs D2 unconditionally and re-enters this decision via `/clavain:route sylveste-s3z6.19.10`."

This is a **single point of failure masked as a default.** The auto-revert assumes:
1. A routing-related sprint is scheduled to run after 2026-06-30
2. The sprint's orchestrator knows to trigger `/clavain:route sylveste-s3z6.19.10`
3. The routing epic is not itself paused or de-prioritized by then

If no routing-related work lands between 2026-06-30 and 2026-08-15 (three months), the auto-revert never fires. The operator is then in a state where the deferral deadline has passed, no explicit decision was made, but the system is silently waiting for a sprint that may never come.

The PRD's Open Question 1 asks "Alternative: 'default to closing the epic' (more conservative)." But the chosen "run D2 then decide" path is not more optimistic — it's **non-deterministic.** If no routing sprint fires, it's equivalent to "do nothing."

**Implication:** F3 should either: (a) schedule D2 to run unconditionally at 2026-07-15 (a fixed date, not "the next routing sprint"), OR (b) explicitly state that if no routing-related work lands by 2026-07-15, the operator must manually run D2 or close the epic. The current phrasing transfers the default-action burden onto a future unknown sprint.

### P1.4 — Keep-alive cadence creates a recurring micro-decision burden with unclear escalation path

F3 requires: `deferral_check_in=2026-05-20` (every 2 sprints), with a check-in protocol: "at each `deferral_check_in` date, sprint orchestrator runs `bd state` and surfaces 'deferral check-in due' notice... Operator confirms (extends date by 2 sprints) or escalates (re-opens decision)."

This is 5-6 check-ins over a 2-month deferral window (2026-05-20, 2026-06-03, 2026-06-17, and implicit stops at 2026-06-30/2026-07-15). Each check-in requires an operator confirmation: "is the deferral still correct?" 

The PRD names no condition under which the operator *should* escalate at a check-in. The escalation trigger is vague: "re-opens decision" — reopens to ask what? If D2 has run and returned "kill epic," the check-in should surface that. If D2 hasn't run yet, the check-in should... what? Confirm patience? File a bead to run D2?

**The feedback loop is: decision deferred → next check-in arrives (scheduled task) → operator receives notice → operator decides "still deferring" → repeat.** This is a recurring cognitive load that has no load-shedding path. If the operator confirms "deferring" five times without new information (because D2 hasn't run, volume is still accumulating normally), the check-in cadence becomes a false signal of active governance over a system in passive wait.

**Implication:** Define escalation triggers explicitly. F3 check-in protocol should include: "If at any check-in: (a) D2 has run, surface its result immediately; (b) if D2 says 'kill epic,' close `.19.10` without further check-in; (c) if no D2 result and no new volume data, confirm extend-by-2-sprints; (d) if volume < 50 per cell after 4 weeks, escalate to γ contingency decision."

### P1.5 — Cascade of 7 paused beads + 3 new child beads compounds governance overhead

The deferral pauses `.19.1`/`.19.2`/`.19.3`/`.19.4`/`.19.5`/`.19.6`/`.19.7` and creates 3 new beads: F1 (bead-body updates), F2 (D2 sibling bead), F3 (keep-alive cadence + state fields). The 7 paused beads depend on `.19.9` + "4 sprints" in a chain with no intermediate milestones until the deferral deadline.

**The feedback loop is: deferral pins 7 beads → sprint planning tries to schedule around paused beads → beads stay paused for 8+ weeks → epic re-evaluation happens late (after 4 sprints) → downstream planning pressure to "just pick an architecture" to unblock beads.**

The PRD's keep-alive cadence is an attempt to add visibility checkpoints (check-in every 2 sprints). But the cascade itself creates a second-order effect: dependencies downstream of `.19.1` (e.g., `.19.5` / `.19.6` / `.19.7`) remain paused for the deferral duration, meaning any work that could start given a "routing solution of any kind" (heuristic-only improvements, privacy extensions) must wait for the architecture decision to land.

The 3 new beads (F1, F2, F3) are the *governance beads* — they exist to manage the deferral, not to advance the router. F1 is mechanical (bead-body updates). F2 is the measurement work (valuable if D2 returns a kill signal). F3 is operational overhead (state fields + check-in protocol). If D2 doesn't run until week 8, F2 delivers zero value for 8 weeks while F1 and F3 are "done."

**Implication:** The governance overhead (F1 + F3 state fields + check-in protocol) is proportional to the *number of paused beads* and *length of deferral*, not to the decision value. For 7 paused beads over 8 weeks, is a 2-sprint check-in cadence (5-6 check-ins) worth the cognitive load? The PRD does not quantify this. Consider: if a single check-in at 2026-06-15 (roughly midpoint) is sufficient to surface "D2 status unknown, volume tracking okay, continue," then the 2-sprint cadence is over-specified.

### P1.6 — `.19.9` deadline is unspecified; deferral depends on a sprint that may never ship

The brainstorm decision states: "defer to β after `.19.9` ships + 4 sprints of pass@1 telemetry." The PRD elevates `.19.9` to "critical-path P0" but does not specify when `.19.9` is scheduled to ship.

**The feedback loop is: deferral decision assumes `.19.9` ships → deferral countdown starts `.19.9` + 4 sprints → if `.19.9` is delayed or de-prioritized, deferral deadline drifts → operator faces choice: (a) hold deferral deadline at 2026-06-30 even if `.19.9` hasn't shipped (contradiction), OR (b) shift deferral deadline (but to when? `.19.9` + 4 sprints is relative).**

The PRD's Open Question 4 flags: "Should the deadline be calendar-locked at 2026-06-30 regardless?" But the answer determines whether the deferral is actually time-bound or event-bound. If `.19.9` ships on 2026-05-20, the 4-sprint count starts then, and 2026-06-30 gives only ~5 calendar weeks for a 4-sprint accumulation (tight). If `.19.9` slips to 2026-06-10, the deadline is already in the accumulation window.

The PRD should either: (a) pin a `.19.9` ship date (e.g., "by 2026-05-15"), making the deferral deadline relative and predictable, OR (b) use a purely calendar deadline (2026-06-30) and add a contingency: "if `.19.9` hasn't shipped by 2026-06-30, auto-revert = escalate to γ contingency or close epic."

**Implication:** F3 state fields should include `critical_prereq_shipped_date` or `critical_prereq_estimated_ship`. Without visibility into when `.19.9` will actually land, the "4 sprints" count is a phantom variable.

---

## P2 findings

### P2.1 — F1 bead-body updates distribute cognitive load across 5 beads with no async checksum

F1 requires updates to `.19.10` notes, `.19.1` body, `.19.2` body, `.19.8` closing note, `.19.9` body, and regeneration of `.beads/issues.jsonl`. These are 5-6 separate edits in a single commit (A1.5: "All updates land in a single commit").

If the updates are split across parallel sessions or if the operator edits one bead-body without seeing the cross-references, the system falls into an inconsistent state. For example:
- Session A edits `.19.1` body to add "blocked on `.19.9` + 4 sprints"
- Session B edits `.19.9` body independently, doesn't know about A's changes
- Both sessions commit separately
- Result: `.19.1` references `.19.9`'s "critical-path role," but `.19.9`'s body doesn't actually declare that role

The PRD's acceptance criterion (single commit) helps, but the work is still distributed (5 separate files). If any one file is missed (e.g., operator forgets to update `.19.8`'s closing note), future readers of `.19.8` will see a closed bead with no explanation of why it's closed, leading them back to the brainstorm-as-source-of-truth.

**Implication:** F1 should include: "After commit, run `bd show .19.1 .19.2 .19.8 .19.9 .19.10` and verify each body mentions the deferral decision and links to the PRD or brainstorm." Or file a follow-up bead after F1 closes to audit cross-references.

### P2.2 — Pace-layer mismatch: PRD pins thresholds, but .19.9 ship pace is external

The PRD pins several operational thresholds (80 verdicts per cell for stable-7, >30% label noise triggers escalation, 5% headroom for D2). These are committed pre-registration numbers. But all of them depend on `.19.9` shipping first and producing the telemetry infrastructure (the event family, the pass@1 outcome column).

The PRD does not specify:
- How fast `.19.9` will populate that outcome column (per-bead? daily? weekly batch?)
- Whether "4 sprints" = 4 calendar weeks or 4 calendar weeks from `.19.9` ship date (or something else)
- Whether the verdict_status field (used to count closed beads) is already being set by `.19.9` or if that's a separate instrumentation effort

If `.19.9` ships a barebones outcome column (e.g., "outcome = pass/fail" with no nuance), the measurement protocols (label-noise > 30%, volume per tier cell) may be impossible to execute. The PRD assumes a fast telemetry feedback loop; if actual feedback is one week lag per bead close, the "4 sprints = 28 calendar days" definition is moot.

**Implication:** The PRD should reference `.19.9`'s design spec (or a link to it) and explicitly state: "These operational definitions assume `.19.9` ships with [specific outcome field schema and refresh cadence]. If the outcome column is less granular than [X], escalate to γ or extend accumulation window."

---

## P3 findings

### P3.1 — F2 D2 sibling bead is independent-runnable but has no resource budget

F2 specifies: "Bead is independently runnable: doesn't block on `.19.9`, doesn't block `.19.9`. Work can land any time."

D2 requires: "replay shadow over the existing `.beads/` verdict corpus (closed beads with verdict_status)" and "Oracle upper bound: synthesized from `verdict_outcome` aggregation OR from manual relabeling of a 200-sample stratified subset."

The manual relabeling is labor (a few hours). The PRD does not assign a sprint slot, priority, or responsible party for F2. It is created as a "bead under `.19`" but with no owner or scheduling context.

**The feedback loop is: F2 is filed as independent → low priority (P1 is stated; P1 is not urgent) → never scheduled during the 2-sprint deferral window → D2 result arrives at week 7-8 (too late to influence architecture choice for a 8-week deferral) → D2 signal is treated as "nice to know, but deferral is already wrapping up".**

If the goal is for D2 to be an "early-warning signal" (per the brainstorm), it should run within the first 2 weeks of deferral (by 2026-05-20). That requires explicit sprint allocation.

**Implication:** F2 acceptance criteria should include: "D2 work scheduled in the first sprint slot after `.19.10` bead closes (by 2026-05-20)." Or state explicitly: "D2 is a contingency check, not a critical path signal. If D2 doesn't run before 2026-06-30, proceed with deferral decision as planned."

---

## Verdict

**NEEDS_ATTENTION** — The PRD operationalizes the deferral from passive to active and addresses most of the brainstorm's P1 findings. But three structural dynamics create residual risk:

1. **Heuristic-stratified eval split is diagnostic, not prescriptive** (P0.1). The PRD promises risk-reduction via required measurement, but without one of the three other mitigations, a router trained on heuristic-imitation + noise will still ship. The eval split shows the problem; it doesn't fix it.

2. **D2 checkpoint has no active polling or escalation trigger** (P1.1). The PRD marks D2 as a checkpoint, but if D2 returns "kill epic" at week 3 and the operator doesn't check until week 7, the 4-week "kill signal" is buried. F3's check-in cadence should explicitly surface D2 status.

3. **Deferral deadline is calendar-pinned but gates are volumetric + gameable** (P1.2). The OR-condition (4 calendar weeks OR sufficient volume) allows deadline pressure to push whichever gate satisfies first. If volume is 50/80 per cell at week 4, the calendar gate can be declared "reached" and deferral can end with weak data.

4. **Auto-revert depends on a future sprint that may never arrive** (P1.3). The chosen default behavior ("next routing sprint runs D2") is non-deterministic if no routing sprint is scheduled after 2026-06-30.

5. **Cascade governance overhead is unquantified** (P1.5). The keep-alive cadence is 5-6 check-ins for 7 paused beads over 8 weeks. The cost/benefit of this recurring micro-decision load is not analyzed.

The deferral decision itself (β over α/γ) is sound per the brainstorm review synthesis. The PRD's operationalization is mostly correct. But these five dynamics create points of failure where deadline pressure, passive signal-detection, and undefined sprint scheduling could cause the deferral to become a rope around the microrouter epic for 3 months without delivering new information.

**Recommended fixes before shipping:**
- P0.1: Require one of {off-policy randomization, manual-override weighting, loss penalty} to land before `.19.3` trains, not just heuristic-stratified eval.
- P1.1: Explicit check-in protocol that surfaces D2 status and auto-escalates if D2 says "kill epic."
- P1.2: Volume threshold is the primary gate; extend `deferral_check_in` if volume < 60/80 at 4-week mark.
- P1.3: D2 runs unconditionally at 2026-07-15 (fixed date), not "next routing sprint."
- P1.5: Consider a single check-in at 2026-06-15 (midpoint) instead of 2-sprint cadence for 7 paused beads.
