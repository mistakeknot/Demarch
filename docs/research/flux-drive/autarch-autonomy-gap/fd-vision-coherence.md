# fd-vision-coherence: Autarch Autonomy Gap Analysis Review

**Reviewer:** fd-vision-coherence
**Date:** 2026-02-25
**Document under review:** `/docs/research/autarch-autonomy-gap-analysis.md`
**Decision lens:** Diagnosis/remedy misalignment, terminological consistency, unstated assumptions

---

## Gap-by-Gap Verdicts

### Gap 1: Operator UX vs Executive UX

**Verdict: Correctly diagnosed and addressed by proposal.**

The gap accurately identifies a real phase mismatch between Autarch's L0-L1 interaction model and Demarch's L2+ trajectory. The Demarch vision explicitly states "the human is above the loop, not in it" (design principle 5) and the autonomy ladder defines L2 as "the human observes and intervenes on exceptions." The three-mode hierarchy (Executive/Supervisor/Operator) is a reasonable proposal for bridging this.

One nuance: the gap implies Gurgeh and Coldwine are equally misaligned, but the Autarch vision doc already acknowledges this as "architectural debt" and schedules arbiter extraction. The gap analysis adds the insight that extraction alone is insufficient without autonomization -- this is a genuine contribution, not a restatement.

### Gap 2: Tools as Workflow Steps vs Tools as Agency Rings

**Verdict: Correctly diagnosed but not addressed by proposal -- the proposed remedy introduces a concept not present in the published architecture.**

The diagnosis is sound: the four tools map to sequential workflow steps and the human drives the sequence. This is a real limitation at L2+.

However, the proposed remedy -- the "recursive ring model" -- is a new architectural concept that does not appear in any canonical Demarch document. The term "ring" does not appear in the Demarch vision, the Clavain vision, the Intercore vision, or the Autarch vision. The Demarch vision uses "layers" (three architectural layers plus one cross-cutting profiler), "macro-stages" (five lifecycle stages), and "sub-agency" (each macro-stage is a sub-agency). The Clavain vision describes "sub-agencies" with model routing and agent composition per phase.

The gap analysis introduces "ring" as though it is an existing concept being applied ("this is already what the Demarch vision describes" -- line 237) when it is actually a new proposal being introduced by the analysis itself. This is a significant coherence problem: the document claims to identify a gap in Autarch relative to the existing architecture, but the architecture it claims Autarch should catch up to does not exist yet. The ring model may be a good idea, but presenting it as an existing vision that Autarch has "fallen behind" on is misleading.

### Gap 3: Per-Item Interaction vs Exception-Based Attention

**Verdict: Correctly diagnosed but is the same gap as Gap 1, viewed from the interaction frequency axis.**

Gap 1 says: the human role should shift from operator to executive. Gap 3 says: the interaction rate should shift from 100% to <10%. These are two descriptions of the same structural issue. "Operator interacts with every item" (Gap 1) and "the human touches every item" (Gap 3) are the same sentence.

The quantitative framing in Gap 3 (the <10% interaction target) adds specificity, but the underlying diagnosis and the proposed remedy (exception-based attention, attention queue) are direct consequences of the executive-mode design already proposed in Gap 1. An executive mode inherently means exception-based attention.

### Gap 4: Chat-Centric vs Dashboard-Centric

**Verdict: Correctly diagnosed but is a symptom of Gap 1, not an independent gap.**

If the human role shifts from operator to executive (Gap 1), the primary interface naturally shifts from conversation (driving each step) to dashboard (observing outcomes and making decisions). The chat-to-dashboard transition is a UX consequence of the role transition, not a separate architectural gap.

The analysis could have folded Gap 3 and Gap 4 into Gap 1 as sub-findings. The three-mode hierarchy already implies that Executive mode uses a dashboard (the analysis even shows this in the mockup under Gap 1's "Reframe" section, not under Gap 4). The mock-up under "What Executive Mode Looks Like" is presented as Gap 1's remedy but it is actually Gap 4's remedy.

### Gap 5: Single-Project Focus vs Portfolio View

**Verdict: Correctly diagnosed and addressed by proposal.**

This is a genuinely independent gap. The existing vision docs confirm portfolio orchestration as a shipped capability (Demarch vision: "the kernel manages concurrent runs across multiple projects, portfolio primitives landed"). Yet no Autarch app surfaces this capability as a first-class view. Bigend shows a flat project list but does not expose cross-project budget allocation, dependency-driven verification, or portfolio-level attention routing.

The proposal (portfolio ring in Bigend) aligns with the existing architecture without introducing new concepts.

### Gap 6: Manual Phase Advancement vs Autonomous Sprint Progression

**Verdict: Correctly diagnosed -- real issue is deeper than the gap statement claims, and the analysis correctly identifies this.**

The gap statement starts by identifying arbiter extraction debt (already acknowledged in the Autarch vision doc). It then makes a genuinely valuable observation: "the arbiter's existence assumes the human is present to drive it." This correctly identifies that extraction is necessary but not sufficient -- the extracted logic must also become autonomous. This is the one place where the analysis adds something the vision docs miss.

However, this gap overlaps substantially with Gap 1. The autonomization of the arbiter is a specific instance of the general operator-to-executive shift. The difference is that Gap 6 names a concrete mechanism (the arbiter code) while Gap 1 names the abstract principle. Both useful, but not independent.

### Gap 7: No Delegation/Escalation Protocol

**Verdict: Correctly diagnosed and addressed, but the remedy is under-specified relative to the gap statement.**

The gap correctly identifies that no formal escalation protocol exists. The proposed typed protocol (decisions, exceptions, approvals, priority classification) is reasonable. The connection to Interspect's signal taxonomy is apt -- structured escalation enables efficient human signal collection at higher autonomy levels.

However, the remedy section does not address where this protocol lives architecturally. Is the escalation protocol a kernel primitive (like gates and events), an OS policy (like phase chains), or an app-layer concern (like the attention queue)? The analysis proposes it under "Architectural Requirements" as a kernel-level priority queue (item 2), but the Demarch vision explicitly positions the kernel as "mechanism, not policy." An attention queue that prioritizes items by urgency/impact is policy, not mechanism. This is a real architectural question the analysis does not resolve.

---

## Cross-Cutting Findings

## [P0] The recursive ring model is not in the published architecture and the document claims it is

The analysis states (line 237): "This is already what the Demarch vision describes. Autarch just hasn't caught up to the architecture it's supposed to surface."

This is false. The Demarch vision describes:
- Three architectural layers (kernel, OS, apps) plus one cross-cutting profiler
- Five macro-stages (Discover, Design, Build, Ship, Reflect), each a sub-agency
- An autonomy ladder (L0-L4) with decreasing human intervention
- Companion plugins as capability drivers

None of these use the term "ring" or describe a recursive nesting of autonomous agencies. The Demarch vision's sub-agency concept is per-macro-stage (each macro-stage is a sub-agency), not per-Autarch-tool. The analysis maps Autarch tools to rings (Pollard = research ring, Gurgeh = design ring, Coldwine = execution ring, Bigend = portfolio ring), but the Demarch vision maps tools to rendering surfaces for kernel state -- the vision explicitly says "apps render; the OS decides; the kernel records."

The ring model is a legitimate architectural proposal. But it should be presented as a new proposal, not as an existing commitment that Autarch has failed to meet. If adopted, the ring model would require updates to the Demarch vision, the Clavain vision, and the Autarch vision -- it is not a gap in implementation but a gap between the analysis and the published architecture.

## [P0] Three gaps (1, 3, 4) are the same gap described from different vantage points

- Gap 1: The human role should be executive, not operator
- Gap 3: The interaction rate should be <10%, not ~100%
- Gap 4: The primary surface should be a dashboard, not a chat

These are one gap with three facets: the human's role (Gap 1), the interaction frequency that follows from that role (Gap 3), and the UI modality that follows from that frequency (Gap 4). The three-mode hierarchy proposed as Gap 1's remedy already implies Gaps 3 and 4. Presenting them as independent gaps inflates the count from 5 genuine gaps to 7, which distorts priority-setting: a reader might distribute effort across 7 work streams when 5 would be more appropriate.

Recommended consolidation: Gap 1 (executive UX) as the primary gap, with interaction frequency and dashboard modality as sub-findings.

## [P1] The three-mode hierarchy and the recursive ring model serve different purposes and are not clearly connected

The analysis proposes two distinct models:

1. **Three-mode hierarchy** (Executive/Supervisor/Operator) -- describes the human's relationship to the system at different autonomy levels
2. **Recursive ring model** -- describes the system's internal structure as nested autonomous agencies

These could exist independently. The three-mode hierarchy works without rings: you could build Executive mode as a dashboard over the existing layer architecture. The ring model works without modes: you could nest autonomous agencies while keeping a single interaction style.

The analysis presents them as complementary parts of a single "reframe" but does not explain their dependency. If Executive mode requires rings, that dependency is unstated. If they are independent, the analysis would benefit from acknowledging this -- a reader could implement the three-mode hierarchy (which aligns with the published architecture) without committing to the ring model (which does not).

## [P1] The term "autonomy" is used inconsistently across sections

The analysis uses "autonomy" in three distinct senses:

1. **Autonomy ladder levels** (L0-L4) -- the Demarch vision's definition: how much of the development lifecycle runs without human intervention. This is a property of the system measured by sprint completion rate and intervention frequency.

2. **Ring autonomy** -- each ring "runs without human intervention in normal operation." This is a structural property of a subsystem, not a system-level metric. A ring being "autonomous" means something different from the system being at "L3 autonomy."

3. **Autonomous sprint mode** -- proposed in the architectural requirements as "full lifecycle without human gates." This is a Clavain operating mode, distinct from both the ladder level and ring autonomy.

The analysis does not distinguish these senses. When it says "Autarch was correct for L0-L1 autonomy" (line 14), it uses sense 1. When it says each ring is "autonomous" (line 218), it uses sense 2. When it proposes "autonomous sprint mode in Clavain" (requirement 3), it uses sense 3. A reader could conflate these and conclude that implementing autonomous rings (sense 2) advances the autonomy ladder (sense 1), but that does not follow -- you could have autonomous subsystems that still require L2-level human oversight at the portfolio level.

## [P1] The "agency" term shifts between organizational unit and software capability

The analysis uses "agency" in at least three ways:
- **Agency as organization** -- "the agency processes items" (Gap 3), meaning Clavain and its agents as a collective
- **Agency as architectural concept** -- "agency rings" (Gap 2), meaning structurally nested autonomous units
- **Agency as capability** -- "agency logic" (Gap 6), meaning the arbiter code that makes decisions

The Demarch vision uses "agency" primarily in sense 1 ("autonomous software development agency"). The Autarch vision uses "agency logic" in sense 3 to describe code that belongs in the OS. The ring analysis introduces sense 2, which is novel.

## [P2] The analysis assumes Interspect operates per-ring, but Interspect's vision describes per-agent profiling

The ring model proposes Interspect as a "meta ring" that "observes all rings and proposes improvements" (line 229). But the Interspect vision describes profiling at the agent level -- finding density per agent, false positive rate per reviewer, model routing accuracy per dispatch. Interspect's counting rules (3 sessions, 2 projects, N events) operate on individual agent evidence, not ring-level aggregates.

For Interspect to profile rings rather than agents, it would need ring-level metrics that do not currently exist in its signal taxonomy. The analysis does not address this gap in Interspect's design, despite listing "self-improving" as a ring property.

## [P2] The "attention queue" is proposed as a kernel primitive but is policy by the kernel's own definition

Architectural requirement 2 proposes a "kernel-level priority queue of items requiring human judgment." The Demarch vision states the kernel provides "mechanism, not policy -- the kernel doesn't know what 'brainstorm' means." Priority classification (urgency/impact sorting) is policy. The kernel can store and order items (mechanism), but deciding which items need human attention and how to rank them is an OS-level concern.

This matters because placing the attention queue in the kernel would violate the mechanism/policy boundary that is foundational to the three-layer architecture. The attention queue is more likely an OS-level component (Clavain aggregates escalation signals and presents them through the write-path contract) rendered by an app-level surface (the Autarch dashboard).

## [P2] The document's conclusion is not fully supported by the analysis

The concluding section ("Recommended Next Steps") lists 6 items. Items 1-3 follow from the analysis. Items 4-6 (extract arbiter, connect Pollard to Intercore, add autonomous sprint mode) are already planned in the Autarch vision doc and the Clavain vision doc. They are not new recommendations arising from this analysis -- they are pre-existing roadmap items restated.

The analysis would be more valuable if its conclusion distinguished between "new work this analysis reveals" (the escalation protocol, the executive mode dashboard, the three-mode hierarchy) and "existing planned work this analysis contextualizes" (arbiter extraction, Pollard kernel integration, autonomous sprint mode).

## [P3] Minor: The "supervisor" term in the three-mode hierarchy conflicts with potential future usage

The three-mode hierarchy uses "Supervisor" for the middle tier (monitors progress, intervenes on exceptions). In multi-agent systems, "supervisor" often refers to an agent that manages other agents (supervisor trees, supervisor strategies). If the ring model is adopted and rings have agent supervisors, the human role of "Supervisor" and the agent role of "supervisor" will collide. Consider "Monitor" or "Steward" for the human role to avoid future confusion.

---

## Summary

The analysis correctly identifies a real phase mismatch between Autarch's interaction model and Demarch's autonomy trajectory. Of the seven gaps, five are genuinely distinct (1, 2, 5, 6, 7) and two are restatements (3 and 4 are aspects of 1). The three-mode hierarchy (Executive/Supervisor/Operator) is well-aligned with the published architecture. The recursive ring model is a substantive new architectural proposal but is incorrectly presented as an existing vision -- it would require changes to all four vision documents if adopted. The two proposals (modes and rings) are independent and should be evaluated separately.

| Rating | Count | Summary |
|--------|-------|---------|
| P0 | 2 | Ring model misattributed to existing vision; 3 of 7 gaps are one gap |
| P1 | 3 | Mode/ring coupling unclear; "autonomy" used 3 ways; "agency" used 3 ways |
| P2 | 3 | Interspect per-ring assumption; attention queue layer violation; conclusion mixes new and existing work |
| P3 | 1 | "Supervisor" term collision risk |
