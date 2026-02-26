# Flux-Drive User & Product Review: Autarch Autonomy Gap Analysis

**Date:** 2026-02-25
**Reviewer:** fd-user-product
**Document under review:** docs/research/autarch-autonomy-gap-analysis.md
**Supporting sources:** docs/demarch-vision.md, apps/autarch/docs/autarch-vision.md, apps/autarch/CLAUDE.md

---

## Primary User and Job Statement

The gap analysis targets a user it calls "the executive" — a product-minded engineer running autonomous software development agencies at L2-L3 autonomy. Their job is: set project objectives, accept or reject escalated decisions, and review sprint outcomes. They are explicitly not in the loop for per-item operations.

The analysis correctly identifies this user. However it conflates three distinct user states that will coexist in practice:

- The engineer onboarding a new domain at L0-L1 (genuinely needs Operator mode)
- The same engineer running a trusted project at L2-L3 (the Executive target)
- The engineer debugging a stuck sprint (needs Supervisor drill-down, not Executive summary)

All three states belong to one person across different moments in the same day. The document treats them as separate "modes," which is product-correct, but the transition between modes is unexplored — and transitions are where users get lost.

---

## What the Document Gets Right

The core diagnosis is accurate. The seven gaps are real and the phase-mismatch framing is the right way to think about them. Gap 3 (per-item vs exception-based interaction) and Gap 4 (chat-centric vs dashboard-centric) are the most important, and the document correctly names them first among the implications.

The recursive ring model matches Demarch's published architecture. The mapping of Bigend/Gurgeh/Coldwine/Pollard to strategic/design/execution/research rings is conceptually clean and consistent with what the vision documents describe.

The attention metric claim — "the human should interact with less than 10% of items the agency processes at L2-L3" — is an appropriately concrete success signal. This kind of quantified target is what makes post-release validation possible. It should survive into any PRD.

---

## Concern 1: The Mode Transition Problem Is the Actual UX Problem

The three-mode table (Executive / Supervisor / Operator) is the document's strongest structural contribution. But the document immediately pivots to describing Executive mode in detail and leaves the other two as labels.

The transition UX is the hard problem, and it is entirely unaddressed:

- How does the user move from Executive dashboard to Supervisor drill-down when they spot something wrong? Is it a keystroke? A click on the active ring summary line?
- How does the user enter Operator mode for a specific ring without losing visibility of the rest of the portfolio?
- When a user is in Operator mode for one ring (debugging a stuck sprint), does the Executive attention queue still surface? Or does full Operator engagement mean they lose portfolio visibility entirely?
- What triggers automatic mode suggestion? If a sprint has been stuck for 30 minutes, does the system prompt the user to shift from Executive to Supervisor for that ring?

The dashboard mockup shows an "Active Rings [expand for detail]" section with a drill-down affordance, but the behavior on drill-down is not specified. "Clicking an active ring opens the current Gurgeh/Coldwine/Pollard view" is a single sentence that carries enormous UX weight without any detail.

This is not an implementation concern — it is a product definition gap that will cause the Executive mode to feel like a trap. An executive dashboard that does not let you quickly drop into operator detail when needed is an unusable dashboard.

Recommendation: Before writing a PRD, map one complete scenario end-to-end: an executive user notices the interlock sprint is stuck at a gate, drills down, performs an override, and returns to the portfolio view. Every screen transition in that scenario must be specified.

---

## Concern 2: The Attention Queue Concept Solves a Real Problem, But the Design Has a Fatal Gap

The attention queue is the document's most operationally important concept, and it is directionally correct. Exception-driven interaction rather than continuous monitoring is the right model for L2-L3.

But the mockup as shown has a critical UX problem: it mixes two fundamentally different interaction types in the same queue without distinguishing them by the user's required response time.

The mockup's "Attention Required" section shows:
- A gate failure with 3 exhausted remediations — this is urgent, the sprint is blocked
- A dependency tradeoff question — this is advisory, the sprint may be continuing on the recommended default

These require different handling. A blocked sprint needs the user to respond before the sprint can resume. A tradeoff question may have a default that keeps things moving. Presenting them in the same queue without urgency or blocking-state indicators means the user cannot triage at a glance. The natural reading of a list is top-to-bottom sequential, which will cause users to spend time on advisory items before addressing blockers.

The mockup does use a warning indicator for the gate failure and a question mark for the tradeoff, but these are glyph-level distinctions. At a portfolio scale with many concurrent sprints, glyph scanning is insufficient.

Missing from the queue design:
- Blocking vs advisory classification at the structural level (not just a glyph)
- Time-sensitivity: how long has this been waiting? Is a sprint accumulating idle token cost while blocked?
- Consequence of ignoring: what happens if the user closes this session without responding? Does the sprint time out? Does it use the recommended default?
- Group-by ring: if two items both come from the interflux sprint, grouping them communicates that the same sprint has multiple issues requiring attention

A decision queue that does not communicate urgency, blocking state, and consequence is a notification feed with actions bolted on. The product thinking needs to distinguish these at the data model level, not just the visual level.

Recommendation: Define three queue item types with explicit semantics: BLOCKED (sprint cannot proceed, response required), PENDING (sprint continues with a default, response improves it), and REVIEW (sprint completed, outcome requires acknowledgment). These types should drive both display and escalation behavior.

---

## Concern 3: "Normal Operation Is Invisible" Will Feel Like Loss of Control

The document states as a virtue: "Normal operation is invisible. The 90% of work that proceeds without issues shows as summary lines, not individual items."

This is correct for an experienced user with high trust in the agency. It is a significant adoption risk for new users and for users entering new domains.

The problem: invisibility of normal operation removes the feedback loop that builds trust. A user who cannot observe what the agency is doing in normal operation has no basis for developing calibrated trust in the agency's judgment. They can only evaluate the 10% of escalations they see, which are by definition the cases where the agency was uncertain or stuck. This creates a systematically negative sample of agency behavior.

The Demarch vision document explicitly names "proof by demonstration" as a credibility pillar. The Executive dashboard as described removes the demonstration from view.

This is not an argument for returning to per-item interaction. It is an argument for a "healthy activity" signal in the portfolio view — not individual operation details, but an activity pulse that shows the agency is working and progressing. Something like: "interflux sprint: 7 phases completed in the last 2 hours, 0 exceptions" gives the user enough to calibrate trust without requiring them to engage with each step.

The mockup's "Active Rings" section approximates this with phase progress indicators, but the ring summary lines show only current phase and agent count. Completed work since the user's last session is not surfaced as activity evidence. Without it, the user returning to the dashboard cannot distinguish "the agency completed a lot of work while I was gone" from "the agency was stuck and waiting for me."

Recommendation: Add a "since your last visit" summary to each ring in the portfolio view — phase transitions completed, gates passed, dispatches resolved. This is distinct from the "Completed Since Last Visit" section at the portfolio level, which only shows milestone completions. The ring-level activity evidence is what builds trust for ongoing sprints.

---

## Concern 4: The Portfolio View Assumes Flat Project Semantics

Gap 5 correctly identifies the need for a portfolio view, but the mockup shows projects as a flat list of rings. This works at the current scale (a few concurrent sprints) but does not handle the organizational structure that emerges when using Demarch at the stated target scale.

The Demarch vision references "concurrent agencies" and "cross-project verification" as kernel primitives. At any meaningful scale, the portfolio has structure: some projects are dependencies of others, some sprints are children of larger initiatives, some rings are research feeding a design feeding an execution chain.

A flat ring list loses this structure. The user cannot tell from the mockup whether "interflux sprint" and "interlock sprint" are independent or related. If the interlock sprint's output feeds the interflux sprint's input, and the interlock sprint is blocked, the user needs to know that two rings are affected, not one.

The document acknowledges the recursive ring model but the dashboard mockup does not render it. The mockup is implicitly flat — the "Active Rings" section shows rings at the same level with no parent-child or dependency relationships.

This is not a fatal gap for an MVP, but it needs to be explicitly deferred as a known limitation rather than accidentally designed out. If the data model does not support ring relationships from day one, adding them later is expensive.

Recommendation: Make the portfolio structure explicit in the PRD. Either (a) define a flat portfolio as a deliberate MVP constraint and state the criteria for when ring relationships will be added, or (b) model ring relationships in the attention queue data format even if the UI renders them flat initially, so the data model does not block a richer display later.

---

## Concern 5: The Dashboard Mockup Is Operator-Friendly, Not Executive-Friendly

This is the document's central tension and the mockup does not fully resolve it.

The mockup as drawn contains:
- Portfolio health summary (2 lines) — genuinely executive-level
- Attention required (2 items with action options) — executive-level
- Completed since last visit (5 items, one per sprint) — executive-level
- Interspect insights (3 lines) — executive-level
- Active rings (3 lines with detailed phase/agent counts) — starts to drift toward operator-level

The last section is the problem. Showing "3 agents, gate pending" for the interlock sprint is operator-level information. An executive does not need to know how many agents are running in a given ring — they need to know whether the ring is progressing, blocked, or needs their attention. The agent count and gate-pending status are supervisor-level concerns that belong in the drill-down.

More importantly, the mockup's information hierarchy places the Interspect insights section before the Active Rings section. This is wrong for executive interaction. An executive's natural workflow when opening the dashboard is:
1. Is anything blocked? (Attention queue — correctly placed second)
2. What got done since I was last here? (Completed — correctly placed third)
3. Is anything currently in flight that I should know about? (Active rings — correctly placed fourth)
4. How is the system improving over time? (Interspect — this is weekly review content, not session-open content)

Interspect insights are strategic input for policy adjustment, not operational input for the current session. Leading with them before active ring status inverts the priority.

Recommendation: Rearrange the information hierarchy to match executive priority: (1) needs your attention now, (2) what completed while you were away, (3) what is currently running, (4) system health and learning trends. The current mockup has items 3 and 4 swapped. The layout should also remove agent-count and gate-pending details from the ring summary lines — those belong one level deeper.

---

## Concern 6: Budget Tracking Is Undersurface for the Primary Restraint

The gap analysis mentions budget tracking as an Executive mode element, and the mockup shows "Budget: 42K/100K" as a header metric. This is correct to include, but the treatment is thin relative to how central budget is to the Executive mental model.

At L2-L3 autonomy, the executive's primary control lever is budget allocation. Setting a sprint budget is how the executive grants autonomy — "run this until you hit 50K tokens, then stop and report." The current mockup shows only total portfolio budget with no per-ring breakdown, no burn rate, and no projected-to-exhaustion estimate.

An executive cannot make sound portfolio decisions without knowing: which ring is consuming budget fastest, which ring has room to continue, and whether any ring is on track to exhaust its budget before the next expected review.

The vision document's "budget-constrained autonomy" concept (item 4 under Architectural Requirements) is the mechanism for this. But "Budget: 42K/100K" as a single header number does not surface it as an actionable executive control.

Recommendation: Budget should be a first-class portfolio dimension shown per ring: consumed, allocated, and projected. The attention queue should include "approaching budget limit" as a PENDING-type item with options to extend, pause, or accept current output. This is one of the few cases where proactive notification (before exhaustion) is more valuable than reactive notification (after blocking).

---

## Concern 7: The Gap Analysis Does Not Account for the Dual-Write Migration Period

The autarch-vision.md notes that Gurgeh and Coldwine are not currently swappable because they contain arbiter logic. During the migration period (arbiter extraction scheduled for v1.5 and v2), the Executive dashboard will be rendering state from sources that have not yet migrated to the kernel.

A user adopting the Executive dashboard during the migration period will see:
- Some sprints with full kernel state (Bigend-driven sprints)
- Some sprints with partial kernel state (Gurgeh/Coldwine sprints where arbiter is still in-app)
- Potentially missing attention items because escalations from non-migrated apps are not surfaced through the kernel event bus

This is a product gap, not just an engineering one. The Executive dashboard's value proposition — "one surface for all your agencies" — cannot be delivered until all apps complete migration. A partial dashboard that shows some rings but not others is potentially worse than the current per-tool experience, because it creates an illusion of completeness.

The gap analysis does not mention the migration dependency, which means a PRD written from this document could produce an Executive mode that is technically delivered but functionally incomplete for 12-18 months while migrations complete.

Recommendation: The PRD should define which apps must be migration-complete before Executive mode is considered shipped. Releasing Executive mode while Gurgeh's arbiter is still in-app is shipping a degraded experience under the name of a target state experience. Better to be explicit: Executive mode reaches MVP when Bigend migration is complete, reaches v1 when Pollard migration is complete, reaches full vision when Gurgeh and Coldwine arbiter extraction is complete.

---

## Concern 8: "Executive" Is the Wrong Name for This Mode

This is a terminology concern with product adoption implications. The document uses "Executive" to mean "sets objectives and reviews outcomes." In the context of a personal engineering rig (Demarch's stated primary audience: "one product-minded engineer, as effective as a full team"), "executive" carries corporate connotations that do not fit the user.

The Demarch audience is a technical individual contributor who also does product strategy. Calling their primary operating mode "Executive" may feel aspirational in a way that creates friction — it sounds like a feature for managers, not engineers.

More precisely, what the document describes is the "steady-state" mode — what the user does when things are working. The complementary modes are "intervention" (Supervisor) and "exploration/onboarding" (Operator). These names are more neutral and more descriptive of what the user is actually doing.

This is a small concern relative to the structural issues above, but terminology shapes how teams build, document, and pitch features. If the mode is called Executive throughout the codebase and docs, it will subtly bias the implementation toward monitoring-dashboard patterns (passive oversight) rather than decision-queue patterns (active judgment). The document's own insight — "the dashboard is a decision queue, not a monitoring wall" — argues against the Executive name.

Recommendation: Rename the modes in the PRD to reflect what the user is doing, not their organizational role: Steady-State (was Executive), Intervention (was Supervisor), Direct (was Operator). Or if mode naming is a secondary concern, at minimum note in the PRD that "Executive" is a working label, not final product terminology.

---

## Concern 9: No User for "Completed Since Last Visit"

The mockup's "Completed Since Last Visit" section is a strong UX choice — it solves the "what happened while I was away" question directly. But the document does not address what "last visit" means in the context of an autonomous agency.

If the user opens the dashboard twice in quick succession, does "last visit" refer to the previous day? The previous session? The last time they took an action? If sprints complete multiple times per hour, a user opening the dashboard after 4 hours could have a very long "completed" list. The mockup shows 5 items, which is manageable. At scale (many concurrent projects), this section could have 30+ entries.

There is also a question about "completed" semantics. Does "completed" mean the sprint reached its final phase? Or that a milestone within a sprint completed? The mockup shows both sprint-level completions ("v0.3.0 shipped") and within-sprint completions ("Bug fix sprint — 2 issues closed"). Mixing granularity in the same list is an information hierarchy problem.

Recommendation: Define the granularity of "completed" items (sprint-level vs milestone-level vs any gate passage), define "last visit" with explicit semantics (time-based or action-based), and cap the list display to a maximum of 5-7 items with a "see all" expansion. The cap prevents the "I was away for a week" case from burying the attention queue.

---

## Positive Findings Worth Preserving

The following are strong enough to call out explicitly so they survive into the PRD:

The "drill-down reveals operator mode" principle is correct and should be a hard design constraint. The four existing apps should not be redesigned — they become the drill-down experience. This avoids rebuilding working surfaces and correctly scopes the new work to the executive-level wrapper.

The "attention is demand-pulled, not supply-pushed" principle is the right interaction model for L2-L3. Do not compromise this under pressure to surface "more information" at the portfolio level.

The structured escalation protocol (decision requests with context/options/tradeoffs/recommendation) is the right foundation. The typed escalation message format should be designed before any dashboard implementation begins — the dashboard renders escalation messages, so the message format determines what the dashboard can show.

The connection of Interspect signals to the Executive dashboard is the right long-term direction. Showing token efficiency trends and false positive rates at the portfolio level closes the feedback loop that lets the human adjust policy. This is genuinely differentiated from any monitoring tool that stops at "is it running?"

---

## Summary of Issues by Priority

Blocking for product definition (must resolve before writing a PRD):

1. Mode transition UX is unspecified. Map one complete scenario through all three modes before writing the PRD.
2. Attention queue item types are not typed. Define BLOCKED / PENDING / REVIEW semantics at the data model level.
3. Migration dependency is unacknowledged. Define which app migrations are prerequisites for Executive mode MVP vs v1 vs full vision.

Important for usability (should be resolved in PRD, can be deferred to design phase):

4. Normal operation invisibility needs a trust-building signal. Add ring-level activity evidence to the portfolio view.
5. Portfolio structure is implicitly flat. Decide whether ring relationships are in-scope for the data model.
6. Budget is undersurfaced as an executive control. Show per-ring budget with burn rate and projected exhaustion.
7. Information hierarchy in the mockup is wrong. Reorder: blocked items, completed items, active rings, learning trends.

Secondary (address before engineering, not before product definition):

8. Mode naming ("Executive") may not fit the primary audience.
9. "Completed since last visit" granularity and "last visit" semantics need definition.
10. Active ring summary line includes operator-level details (agent count, gate state) that belong in drill-down.

---

*This review covers user and product concerns only. Architecture, safety, and correctness concerns are addressed in separate flux-drive reviewer outputs.*
