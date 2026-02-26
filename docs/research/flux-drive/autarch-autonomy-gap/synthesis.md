# Synthesis Report: Autarch Autonomy Gap Analysis

**Review Date:** 2026-02-25
**Document Under Review:** `/home/mk/projects/Demarch/docs/research/autarch-autonomy-gap-analysis.md`
**Agents:** 6 launched, 6 completed, 0 failed
**Verdict:** NEEDS-CHANGES (risky)

---

## Executive Summary

The gap analysis correctly diagnoses real structural misalignment between Autarch's operator-centric UX and Demarch's executive-centric autonomy vision. The proposed three-mode hierarchy (Executive/Supervisor/Operator) is architecturally sound. However, the analysis significantly understates implementation complexity in three areas:

1. **Data model prerequisites** — The proposed modes and escalation protocol require schema changes in Coldwine, Intercore, and Clavain that are not acknowledged.
2. **Infrastructure gaps** — Autonomous phase advancement, recursive ring support, and escalation state management require kernel or OS-layer work beyond "configuration."
3. **Architectural coherence** — The recursive ring model is presented as an existing vision commitment when it is actually a new proposal that would require updates to all four canonical vision documents (Demarch, Clavain, Intercore, Autarch).

The document should be revised to distinguish between architectural diagnosis (solid) and remedy design (incomplete). A PRD written from this document would ship a partially functional Executive mode that appears complete but lacks the data model to populate it.

---

## Verdict Summary by Agent

| Agent | Specialty | Status | Key Finding |
|-------|-----------|--------|------------|
| fd-user-product | Product & UX | NEEDS_ATTENTION | 9 concerns identified; attention queue mixes incompatible item types; mode transitions unspecified |
| fd-autonomy-ux-hierarchy | UX modes & protocols | NEEDS_ATTENTION | Mode switching criteria are not implementable; data model work is prerequisite; modes are simultaneous not exclusive |
| fd-recursive-ring-architecture | Distributed systems | NEEDS_ATTENTION | Recursive rings require kernel extensions; autonomous advancement has no driver; failure modes unaddressed |
| fd-delegation-escalation-protocol | Protocol design | NEEDS_ATTENTION | Escalation triggers are categories not conditions; no escalation lifecycle state machine; timeout behavior missing |
| fd-migration-transition-path | Migration sequencing | NEEDS_ATTENTION | No incremental adoption path; conflates two parallel migrations (backend + UX); irreversibility analysis missing |
| fd-vision-coherence | Architecture alignment | NEEDS_ATTENTION | Ring model misattributed to existing architecture; 3 of 7 gaps are one gap restated; autonomy term used 3 incompatible ways |

---

## Critical Findings (P0 — Blocks PRD)

### 1. No Implementable Mode Switching Criteria
**Sources:** fd-autonomy-ux-hierarchy (P0), fd-user-product (Concern 1), fd-migration-transition-path (Finding 1)

The three-mode table presents modes by human role and autonomy level but never specifies who decides which mode is active. Three plausible models conflict:

- **User-selected mode:** Simple but allows Executive mode on L0 projects (mismatch)
- **Autonomy-derived mode:** Requires autonomy level per run (Intercore has `auto_advance` boolean, not graduated scale)
- **Hybrid per-project:** Feasible but requires new data structure not mentioned

**Missing requirement:** Add `engagement_level` field (OPERATOR/SUPERVISOR/EXECUTIVE) to Autarch's project settings, defaulting to autonomy level. Mode = min(autonomy_capability, user_preference). State machine for mode transitions must be specified before any dashboard design begins.

### 2. Recursive Rings Require Kernel Extensions Not Acknowledged
**Sources:** fd-recursive-ring-architecture (P0), fd-vision-coherence (P0)

The analysis claims rings "compose recursively" but Intercore only supports a single nesting level (`parent_run_id` → children). Supporting rings within rings requires:

- **Recursive relay:** `portfolio.Relay()` has no descent logic for portfolio children
- **Transitive gate checks:** `CheckChildrenAtPhase` only inspects direct children
- **Budget hierarchy:** Inner ring budgets are independent of outer ring budgets
- **State table conflicts:** Relay processes at different levels updating same keys causes race conditions

**Missing requirement:** Explicitly acknowledge recursive rings as a kernel epic. Specify relay depth, transitive gates, budget cascade enforcement as separate deliverables before recursive architecture can function.

### 3. Autonomous Phase Advancement Has No Specified Driver
**Sources:** fd-recursive-ring-architecture (P1), fd-delegation-escalation-protocol (P0)

The document claims "all phase advancement is kernel-driven" (line 103) but Intercore is a pull-based CLI. `Advance()` requires an external caller. Today Clavain's hooks provide this; the document proposes autonomous rings must advance themselves.

Options not acknowledged:
- **Polling relay per ring:** Requires persistent sidecar process per ring
- **Event-driven from dispatch completion:** Works for L2 but breaks recursion (inner ring events are in inner DB)
- **Phase action crons:** Triggered on entry, not when gates asynchronously pass

**Missing requirement:** Specify whether autonomous advancement is relay-based (with ops cost), daemon-based (with complexity), or event-subscription-based (with recursion challenges). Each has different infrastructure needs.

### 4. Escalation Protocol Lacks State Machine and Trigger Taxonomy
**Sources:** fd-delegation-escalation-protocol (P0 findings 1 and 2)

The escalation model is described as a message but not a process. Missing:

- **Trigger conditions:** Document lists "3 retries failed, budget exceeded" as prose examples, not conditions. No observable state mapping to escalation signals.
- **Lifecycle states:** Created → Acknowledged → Resolved, with timeouts and re-escalation. No durability model specified (kernel table? OS event? App-layer store?).
- **Timeout fallbacks:** No specification of what happens if human does not respond (critical for async delegation).

**Missing requirements:**
- Define `TriggerRule` schema (condition, signal type, destination, timeout)
- Add `escalations` table to Intercore with status lifecycle
- Define timeout policies per escalation type with fallback actions
- Map escalation types to blocking (hard gate injection) vs advisory (informational)

### 5. The Recursive Ring Model Is Not in Published Architecture
**Sources:** fd-vision-coherence (P0 findings 1 and 2)

The analysis states (line 237): "This is already what the Demarch vision describes. Autarch just hasn't caught up."

This is factually incorrect. The Demarch vision describes:
- Three layers (kernel, OS, apps) + profiler
- Five macro-stages per agency, each a sub-agency
- Autonomy ladder L0-L4

It does NOT describe recursive nesting of autonomous agencies or "rings." The term "ring" does not appear in any canonical Demarch, Clavain, Intercore, or Autarch vision document.

The ring model is a legitimate architectural proposal but should be presented as a new proposal, not as an existing commitment Autarch has missed. **Adopting the ring model would require updates to all four vision documents** — it is not a gap in Autarch's implementation but a gap between the analysis and the published architecture.

---

## Important Findings (P1 — Blocks Execution Plan)

### 6. Exception-Based Interaction (Gap 3) Requires Coldwine Schema Changes
**Source:** fd-migration-transition-path (Finding 3)

Gap 3 claims the system should interact with <10% of items via "attention queue," but Coldwine's current schema (`epics`, `stories`, `work_tasks` tables) has no `attention_required` or `escalation_state` fields.

Three options with different risk profiles:
- **Option A:** Add `attention_required` boolean + `attention_reason` text to Coldwine tables (additive schema migration, low risk)
- **Option B:** Separate `attention_queue` table (lowest risk)
- **Option C:** Derive from kernel events only (requires complete Coldwine→Intercore migration, highest risk, last in sequence)

The document claims "most primitives already exist in Intercore" but ignores that gates/events are run-level concepts, not task-level. Coldwine's Epic→Story→WorkTask hierarchy has no kernel representation today.

**Missing requirement:** Acknowledge the schema change and choose Option A, B, or C explicitly. Sequence accordingly — cannot defer to end of Intercore migration if attention queue is needed now.

### 7. Portfolio View Requires Cross-Project Aggregation Layer
**Source:** fd-autonomy-ux-hierarchy (P1)

The portfolio health summary ("3 sprints active, 1 blocked, 2 completed today") requires aggregating data across multiple per-project Intercore databases. Intercore provides:
- Per-run status queries
- Per-run budget tracking
- Portfolio dependency edges

It does NOT provide:
- Aggregated metrics across projects (total active runs, total blocked, total tokens spent)
- Cross-project attention items sorted by urgency
- Portfolio-level budget with burn rate and projected exhaustion

Either Intercore needs new `ic portfolio metrics` / `ic portfolio attention` commands (kernel-side), or Autarch needs an aggregation engine managing N database connections (app-side).

**Missing requirement:** Acknowledge aggregation as a necessary component. Specify whether it lives in kernel or app layer. Each choice couples the app's display needs differently.

### 8. No Incremental Adoption Path for Three Modes
**Source:** fd-migration-transition-path (Finding 1)

The "Recommended Next Steps" list six parallel items with no sequencing. This risks a flag-day rewrite affecting all four apps simultaneously while also extracting arbiters.

**Missing requirement:** Define three adoption phases:
1. **Phase A:** Supervisor mode for Bigend and Pollard only (no arbiter changes needed, low risk)
2. **Phase B:** Supervisor mode for Gurgeh/Coldwine (requires arbiter extraction, already planned)
3. **Phase C:** Executive dashboard as new surface (additive, built on working Supervisor modes)

Without explicit staging, implementation will attempt all modes in parallel, which is extremely high risk.

### 9. Attention Queue Design Mixes Incompatible Item Types
**Source:** fd-user-product (Concern 2)

The attention queue mockup shows gate failures (urgent, blocking) and tradeoff decisions (advisory, non-blocking) in the same visual list with only glyph-level distinction. At portfolio scale with many concurrent sprints, users cannot triage at a glance.

**Missing requirement:** Define three queue item types at the data model level:
- **BLOCKED:** Sprint cannot proceed, response required immediately
- **PENDING:** Sprint continues with default, response improves outcome
- **REVIEW:** Sprint completed, outcome requires acknowledgment

These types drive both display hierarchy and escalation behavior — not just visual glyphs.

### 10. Mode Boundaries Are Not Mutually Exclusive (Modes Are Simultaneous)
**Source:** fd-autonomy-ux-hierarchy (P2)

The mode table presents Executive/Supervisor/Operator as discrete modes. But line 173 says "drill-down reveals operator mode from Executive dashboard," implying simultaneous occupancy: Executive mode at portfolio level, Operator mode at item level.

**Missing requirement:** Reframe modes as hierarchical scopes (Executive scope: portfolio, Supervisor scope: project, Operator scope: item), not mutually exclusive states. Drill-down narrows the viewport; back-navigation widens it. Specify whether updates to other scopes arrive in the background (requires multi-scope polling).

### 11. Autonomous Advancement Conflicts with Gap 6 (Arbiter Extraction)
**Source:** fd-recursive-ring-architecture (P1), fd-vision-coherence

Gap 6 claims the arbiter's extraction makes phase advancement autonomous. But extraction moves the logic to Clavain (OS layer), not the kernel. Clavain's hooks still call `ic run advance` — nothing in the system autonomously calls it without external triggering.

The document's claim "arbiter extraction enables autonomous advancement" is incomplete. Extraction is necessary but not sufficient; a watcher or relay must drive the advancement.

### 12. Three of Seven Gaps Are One Gap Restated
**Source:** fd-vision-coherence (P0)

- Gap 1: Human role shifts from operator to executive
- Gap 3: Interaction rate shifts from 100% to <10%
- Gap 4: UI modality shifts from chat to dashboard

These are one gap with three facets: role (Gap 1) → frequency (Gap 3) → modality (Gap 4). The three-mode hierarchy already implies all three. Presenting them as separate gaps inflates priority and causes effort to spread across 7 work streams when 5 would be more appropriate.

**Recommendation:** Consolidate to five gaps: operator-to-executive role shift (Gap 1), tools-as-steps-to-tools-as-rings (Gap 2), single-project-to-portfolio (Gap 5), manual-to-autonomous-phase-advancement (Gap 6), no-escalation-protocol-to-structured-escalation (Gap 7).

---

## Moderate Findings (P2 — Should Be Resolved in PRD)

### 13. Mode Naming ("Executive") May Not Fit Primary Audience
**Source:** fd-user-product (Concern 8)

The Demarch vision's primary user is "one product-minded engineer as effective as a full team," not a manager. The term "Executive" carries corporate connotations that may not resonate. Consider "Steady-State," "Steward," or "Monitor" instead of "Executive."

### 14. Budget Tracking Is Undersurfaced
**Source:** fd-user-product (Concern 6)

The mockup shows "Budget: 42K/100K" as a single header number. But at L2-L3 autonomy, the executive's primary control lever is budget allocation per ring. Missing: per-ring consumption, burn rate, projected exhaustion, and budget-approaching notifications.

### 15. Migration Path Ignores Existing Autarch Vision Roadmap
**Source:** fd-migration-transition-path (Finding 8)

The Autarch vision doc contains a detailed four-stage migration plan (Bigend → Pollard → Gurgeh → Coldwine). The gap analysis proposes six "next steps" that do not reference this existing plan. Risk: two parallel migration tracks with conflicting sequencing.

**Recommendation:** Build new autonomy modes on top of the existing migration sequence, not in parallel. Interleave: complete Bigend backend → add Supervisor mode, complete Pollard → add Supervisor mode, etc.

### 16. Normal Operation Invisibility Undermines Trust
**Source:** fd-user-product (Concern 3)

The dashboard hides the 90% of work that proceeds normally, surfacing only exceptions. This removes feedback loops that build trust in the agency. A new user cannot calibrate trust based on only the 10% of cases where the agency was uncertain.

**Recommendation:** Add "since your last visit" activity summary per ring (phases completed, gates passed, dispatches resolved) — not individual details, but evidence that the agency is working.

### 17. Information Hierarchy in Mockup Is Wrong
**Source:** fd-user-product (Concern 5)

The mockup shows Interspect insights before active rings. But an executive's natural workflow is: (1) blocked items, (2) completed items, (3) active rings, (4) system trends. Weekly learning trends belong lower in the priority stack than real-time ring status.

### 18. Dashboard Mockup Assumes Structured Action Options That Don't Exist
**Source:** fd-autonomy-ux-hierarchy (P2)

The mockup shows "[override] [investigate] [reassign] [abort]" action options for gate failures. Today gate failures do not emit remediation attempt counts or structured action sets. These are future capabilities (part of Gap 7's escalation protocol), not current state.

**Recommendation:** Separate mockup into two versions: (1) what Executive mode can show with today's primitives, and (2) what it can show after escalation protocol is implemented.

### 19. Interspect Profiling Is Agent-Scoped, Not Ring-Scoped
**Source:** fd-recursive-ring-architecture (P1), fd-vision-coherence (P2)

The ring model proposes Interspect as a "meta ring" that profiles rings and proposes ring-level optimizations. But Interspect's vision describes agent-level profiling: false positive rate per reviewer, efficiency per agent. Ring-level signals (completion rate per ring, cost per ring, cross-ring correlation) require new evidence types and aggregation logic not yet designed.

**Recommendation:** Document ring profiling as Phase 2+ work for Interspect, not an implicit consequence of the ring model.

### 20. Delegation Model Unclear (Push vs Pull vs Pull-with-Heartbeat)
**Source:** fd-delegation-escalation-protocol (P1)

The document describes rings as autonomous but also as delegated-to by outer rings. This is ambiguous: does the outer ring push work down (requires tracking delegation), or does the inner ring pull attention only on failure (requires heartbeat detection to catch silent failures)?

**Recommendation:** Commit to pull-with-heartbeat. Define heartbeat interval per ring. Outer ring treats N missed heartbeats as escalation trigger.

### 21. Ring Failure Modes Are Entirely Absent
**Source:** fd-recursive-ring-architecture (P2)

When an inner ring fails (child run status = failed), Intercore's portfolio gate `CheckChildrenAtPhase` blocks the outer ring permanently. No auto-remediation path. No timeout. No cascade handling. The document proposes rings as a first-class primitive but does not address failure recovery.

**Recommendation:** Add ring failure protocol to architectural requirements: inner ring failure, budget exhaustion, stall/timeout, cascading failure. Specify kernel vs OS handling for each.

---

## Convergence and Conflicts

### Convergence on Core Issues

All six agents converge on these critical problems:

1. **Data model work is prerequisite** (5/6 agents) — Attention classification, escalation events, engagement level settings, and state machine for escalations must be designed before dashboard design.
2. **Infrastructure gaps are understated** (4/6 agents) — Autonomous advancement, recursive rings, and aggregation layers require more than configuration.
3. **Mode switching is unspecified** (4/6 agents) — Who decides which mode is active? The document provides no implementable criteria.
4. **Ring model is new architecture, not existing** (2/6 agents with strong consensus from vision-coherence) — The term "ring" does not appear in published vision documents.

### No Contradictions

All agents agree on the fundamental diagnosis: Autarch's operator UX and Demarch's executive vision are misaligned. Agents differ on implementation path complexity, but not on whether the gap is real.

---

## Positive Findings Worth Preserving

The following are strong enough to survive into a PRD:

1. **Three-mode hierarchy is sound** — Mapping human roles to autonomy levels is the right principle (Executive/Supervisor/Operator, with clear scope boundaries).
2. **Drill-down reveals operator mode** — This avoids redesigning existing apps. Operator mode becomes the deep-dive experience; Executive is the summary wrapper.
3. **Attention is demand-pulled, not supply-pushed** — Exception-based interaction rather than continuous monitoring is correct for L2-L3.
4. **Structured escalation protocol is the right foundation** — Typed messages (decision requests, exceptions, approvals) with context/options/recommendation should be designed before dashboard implementation.
5. **Recursive ring model has merit** — Even if not in current published vision, the idea of nested autonomous agencies with per-ring budgets and phases is a coherent architectural direction worth pursuing (but should be explicitly proposed as new, not claimed as existing).
6. **Portfolio orchestration primitives exist** — Intercore has parent/child runs, dependency edges, and budget tracking. Gap is in app-layer aggregation, not kernel primitives.

---

## Recommendations for Next Steps

### Before Writing a PRD

1. **Define mode switching criteria** — Add per-project `engagement_level` preference. Specify state machine for mode transitions.
2. **Audit data model requirements** — Map all proposed features to kernel schema changes, OS-layer data structures, and app-layer additions. Estimate schema work separately.
3. **Clarify ring model scope** — Decide: is the ring model adopted as new architecture (requires vision document updates), or deferred in favor of simpler three-mode hierarchy (sufficient for MVP)?
4. **Sequence migrations explicitly** — Build new autonomy modes on top of existing Autarch backend migration (Bigend → Pollard → Gurgeh → Coldwine). Do not run migrations in parallel.
5. **Define one complete scenario** — Map executive user noticing blocked sprint → drilling down → performing override → returning to portfolio. Specify every screen transition and data flow.

### Before Implementation Begins

1. **Design escalation schema** — Add `escalations` table to Intercore, or commit to state-table workaround with durability guarantees. Define lifecycle states, timeout policies, and blocking rules.
2. **Design aggregation layer** — Specify whether portfolio metrics live in kernel (`ic portfolio metrics`) or app layer (Autarch aggregator). Define cross-project attention routing.
3. **Prototype mode transitions** — Build a working prototype that switches between modes for a single ring. Verify that back-navigation preserves portfolio state.
4. **Design attention queue item types** — Define BLOCKED/PENDING/REVIEW at the schema level, not just the UI level. Implement sorting and filtering rules.

### Deferred (Not Blocking MVP)

1. Ring recursion support (kernel epic, estimate separately)
2. Ring-level Interspect profiling (Phase 2+ work for Interspect)
3. Dashboard rearrangement and budget breakdown (UX polish, can follow MVP)
4. Mode naming refinement (can be done post-MVP)

---

## Files Referenced

- Reviewed document: `/home/mk/projects/Demarch/docs/research/autarch-autonomy-gap-analysis.md`
- Agent reports: All in `/home/mk/projects/Demarch/docs/research/flux-drive/autarch-autonomy-gap/`
  - `fd-user-product.md` — UX and product concerns (9 detailed findings)
  - `fd-autonomy-ux-hierarchy.md` — Mode boundaries and data model (4 P0-P1 findings)
  - `fd-recursive-ring-architecture.md` — Distributed systems implications (4 findings)
  - `fd-delegation-escalation-protocol.md` — Protocol design gaps (6 findings)
  - `fd-migration-transition-path.md` — Migration sequencing (8 findings)
  - `fd-vision-coherence.md` — Architecture alignment (6 P0-P2 findings)

---

## Final Verdict

**Status:** NEEDS-CHANGES

**Summary:** The analysis correctly diagnoses a real structural gap between Autarch's operator UX and Demarch's executive vision. The proposed three-mode hierarchy is architecturally sound. However, the remedy design significantly understates implementation complexity in data model prerequisites, infrastructure requirements, and architectural coherence. The recursive ring model is presented as an existing commitment when it is a new proposal. The document should be revised to:

1. Distinguish architectural diagnosis (solid) from remedy design (incomplete)
2. Acknowledge data model and infrastructure gaps explicitly
3. Present the ring model as a new proposal requiring vision document updates, not as a missed implementation detail
4. Define an incremental adoption path on top of the existing Autarch backend migration
5. Provide detailed architectural specifications (mode switching, escalation state machine, aggregation layer) before any PRD or implementation

A PRD written from the current document would ship a visually complete Executive mode that appears functional but lacks the data model to populate its decision queue. Revision is required before this can proceed to product design.
