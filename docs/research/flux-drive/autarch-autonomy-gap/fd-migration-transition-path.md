# fd-migration-transition-path — Autarch Autonomy Gap Analysis

**Reviewer:** fd-migration-transition-path
**Document:** `docs/research/autarch-autonomy-gap-analysis.md`
**Date:** 2026-02-25
**Verdict:** Revise — the analysis correctly identifies seven structural gaps, but treats the transition from current state to target state as a single leap rather than a migration. No incremental adoption path is specified. Two of the seven gaps require data model changes that aren't acknowledged. The document should not proceed to a plan without explicit migration staging.

---

## Finding 1: No Incremental Adoption Path for the Three Modes [P0 — Breaking]

**What the document says:** Three interaction modes (Executive, Supervisor, Operator) replace the current single-mode UX. The document's "Recommended Next Steps" lists six parallel work items with no sequencing or dependency ordering.

**What's missing:** The document never specifies whether one mode can be enabled without the other two. This is the first-order migration question. Specifically:

- Can Supervisor mode ship without Executive mode? (Yes, if it's implemented as a filter layer on top of existing Operator views.)
- Can Executive mode ship without Supervisor mode? (No, because Executive drill-down requires Supervisor as the intermediate view.)
- Can any mode ship without the arbiter extraction? (Partially — Bigend and Pollard can, but Gurgeh and Coldwine cannot, because their arbiters embed the interaction assumptions.)

**The risk:** Without explicit staging, implementation will attempt all three modes simultaneously, which is a rewrite of the entire Autarch interaction layer. A rewrite of a 2200+ line TUI (Coldwine alone) while simultaneously extracting its arbiter to Clavain is extremely high risk.

**Recommendation:** Define three adoption phases:
1. **Phase A: Supervisor mode for Bigend and Pollard only.** These two apps are already read-only (Bigend) or loosely coupled (Pollard). Add exception-based filtering and attention queue to these apps first. Existing Operator mode remains the default. Zero breaking changes.
2. **Phase B: Supervisor mode for Gurgeh and Coldwine.** Requires arbiter extraction (already planned in Autarch vision doc Phases 1-3). Supervisor mode is added to the extracted arbiters, not the embedded ones.
3. **Phase C: Executive mode as a new top-level dashboard.** Built on top of working Supervisor modes. This is additive — it doesn't replace anything, it composes the existing views.

**Classification:** Breaking if adopted as-is. The document's six "next steps" would trigger simultaneous changes to all four apps, the OS layer, and the kernel. That's a flag-day migration, not an evolution.

---

## Finding 2: Existing Autarch Users Survive — But Only If Operator Mode Remains Default [P1 — Additive if handled correctly]

**What the document says:** "Autarch's apps shouldn't be redesigned. They should be re-layered." The document frames Operator mode as the L0-L1 mode and Executive mode as the L2+ default.

**What's correct:** The re-layering framing is sound. The existing UX is Operator mode. Adding Supervisor and Executive modes on top is architecturally additive.

**What's missing:** The document doesn't state that Operator mode remains the default during transition. This matters because:

- The Autarch vision doc (v1.1) already has a migration plan in progress: Bigend migration (read-only, lowest risk) → Pollard → Gurgeh → Coldwine. This migration is from tool-specific storage to Intercore backend.
- The gap analysis proposes a second, orthogonal migration: from Operator UX to Executive UX.
- These two migrations must be sequenced, not interleaved. Running both simultaneously means changing the data source (Intercore backend) and the interaction model (Executive UX) at the same time, which makes debugging failures impossible.

**Recommendation:** Explicitly state: "Operator mode remains the default entry point until all four apps have completed their Intercore backend migration (Autarch vision doc phases 1-4). Executive mode becomes the default only after the backend migration is stable." This prevents the two migration tracks from colliding.

**Classification:** Additive, but only if the document commits to preserving Operator mode as the default. Without that commitment, existing workflows are at risk during the transition.

---

## Finding 3: Exception-Based Interaction (Gap 3) Requires a Data Model Change in Coldwine [P1 — Breaking]

**What the document says:** The human should interact with less than 10% of items. Items are surfaced via an "attention queue" with decisions, exceptions, and milestones. The document lists this as an "architectural requirement" (item 2) but describes it as a kernel-level priority queue.

**What the document doesn't acknowledge:** Coldwine's current data model (`internal/coldwine/storage/schema.go`) has no concept of attention state. The schema defines:

- `EpicStatus`: draft, open, in_progress, done, closed
- `StoryStatus`: draft, open, in_progress, done, closed
- `TaskStatus`: todo, in_progress, blocked, done

None of these status enums distinguish between "proceeding normally" (no attention needed) and "requires human judgment" (attention needed). To implement exception-based interaction, every entity in Coldwine's hierarchy needs either:

- **Option A:** A new `attention_required` boolean column on `epics`, `stories`, and `work_tasks` tables, plus an `attention_reason` text column. This is an additive schema migration (ALTER TABLE ADD COLUMN) — low risk.
- **Option B:** A separate `attention_queue` table that references entities by type+ID. This is additive and doesn't touch existing tables — lowest risk.
- **Option C:** Rely entirely on Intercore's event stream to derive attention state at render time. This avoids Coldwine schema changes but requires the kernel to emit structured escalation events (which it doesn't today).

**The risk:** The document says "most of these already exist as primitives in Intercore (gates, budgets, events, dispatches)" — but `gates` and `events` are run-level concepts, not task-level. Coldwine's `Epic → Story → WorkTask` hierarchy has no kernel representation. Tasks are Coldwine-internal entities. The attention queue cannot be purely kernel-derived unless the task hierarchy migrates to kernel primitives first, which is the most complex migration in the Autarch vision doc (item 4, migrate last).

**Recommendation:** Acknowledge that Gap 3 requires either (a) Coldwine schema changes (Option A or B, additive, low risk) or (b) completion of the Coldwine→Intercore migration (high risk, last in sequence). The document should explicitly choose which path and sequence it accordingly.

**Classification:** Breaking if the document assumes attention can be derived from kernel state alone. The kernel has no representation of Coldwine's task hierarchy today.

---

## Finding 4: Portfolio View (Gap 5) Does NOT Require Intercore Schema Changes [P3 — Additive]

**What the document says:** The human manages a portfolio of concurrent agencies. Intercore already has portfolio orchestration primitives.

**Verification:** Confirmed. Intercore's schema (v10) includes:
- `runs` table with `parent_run_id` for hierarchical run composition
- `project_deps` table with `portfolio_run_id`, `upstream_project`, `downstream_project` for cross-project dependency tracking
- `runs.token_budget` and `runs.budget_enforce` for budget-constrained execution

The portfolio view described in Gap 5 can be built entirely from existing `ic run list`, `ic run status`, and `ic run tokens` queries across project databases. No schema changes needed.

**One caveat:** The document's mockup shows "3 sprints active, 1 blocked, 2 completed today" across projects. Intercore databases are per-project (one `.intercore.db` per project directory). A portfolio view requires querying multiple databases. Bigend already does this via filesystem scanning today. The Intercore Go wrapper plan (`docs/plans/2026-02-25-autarch-intercore-go-wrapper.md`) mirrors this pattern. This is an implementation detail, not a schema change.

**Classification:** Additive. Existing primitives are sufficient.

---

## Finding 5: Interspect's Profiler Data Is Compatible With the Ring Model — But the Ring Model Adds No New Profiling Surface [P2 — Unclear value]

**What the document says:** Each ring is "self-improving — Interspect profiles each ring and proposes optimizations." The recursive ring model composites research, design, execution, portfolio, and meta rings.

**Assessment:** Interspect's existing evidence model (`interspect_events` table in Intercore) tracks:
- `agent_name` — the agent being profiled
- `event_type` — what happened (dismissal, override, correction)
- `run_id` — which run the event occurred in
- `context_json` — arbitrary structured context

This model is agent-centric, not ring-centric. Interspect profiles individual agents (fd-safety, fd-architecture) and proposes per-agent optimizations (exclusion overlays, model downgrades).

The ring model introduces a new abstraction level (ring = sub-agency = collection of agents). Interspect has no concept of "ring performance" — only agent performance within a run. To profile rings, Interspect would need:
- A way to identify which agents belong to which ring (currently agents belong to runs, not rings)
- Ring-level aggregated metrics (completion rate per ring, cost per ring)
- Cross-ring correlation (did the research ring's output quality affect the execution ring's defect rate?)

None of this requires schema changes if rings are implemented as nested `runs` (using `parent_run_id`). Interspect can derive ring membership from the run hierarchy. But the document doesn't acknowledge that ring profiling is a new Interspect capability that needs design, not an automatic consequence of the ring model.

**Recommendation:** Add a note that ring-level profiling requires Interspect Phase 2+ (overlays), specifically: aggregation of evidence across agents within a ring (run), and cross-ring correlation. State whether this is a blocker for the ring model or a follow-on optimization.

**Classification:** Not a schema change, but an unacknowledged capability gap in Interspect. The profiling surface claimed by the document doesn't exist yet.

---

## Finding 6: The Document Does Not Identify Irreversible Transition Steps [P1 — Missing analysis]

**What the document says:** Nothing. The word "irreversible" does not appear. The document does not distinguish additive changes from breaking ones.

**What's irreversible in this proposal:**

1. **Arbiter extraction (Gurgeh/Coldwine → Clavain).** Once the arbiter logic moves to the OS layer and Gurgeh/Coldwine are reduced to rendering surfaces, reverting requires reimplementing agency logic in the app layer. This is acknowledged in the Autarch vision doc as a staged extraction (Phase 1-3), but the gap analysis treats it as a precondition without acknowledging its irreversibility.

2. **Dashboard replacement.** If the four-tab model (Bigend/Gurgeh/Coldwine/Pollard) is replaced by a single Agency Dashboard as the default entry point, the tab-based navigation is effectively deprecated. Users who prefer the current model need an explicit opt-out path.

3. **Interaction model change.** Shifting from ~100% human interaction rate to <10% changes what data is surfaced by default. If the Executive dashboard hides individual items and surfaces only exceptions, users lose the ability to review everything unless they drill down. The drill-down path must be complete (every item reachable) and obvious.

**What's reversible:**
- Adding Supervisor mode (filter layer on top of Operator views) — purely additive
- Adding an attention queue — additive table or column, removable
- Adding budget tracking dashboard — read-only rendering of existing kernel data
- Adding Interspect insights panel — read-only rendering of existing profiler data

**Recommendation:** Add a section titled "Reversibility Analysis" that classifies each proposed change as additive (rollback = remove), transformative (rollback = reimplementation), or irreversible (rollback = impossible). This is standard practice for platform migrations.

**Classification:** Missing. The absence of irreversibility analysis is a first-order risk for a document proposing fundamental UX changes.

---

## Finding 7: The Escalation Protocol (Gap 7) Has No Specified Kernel Representation [P2 — Additive but unscoped]

**What the document says:** A typed escalation protocol with decision requests, exception reports, approval gates, and priority/urgency classification. Listed as architectural requirement 1.

**Assessment:** Intercore's current event system (`dispatch_events`, `phase_events`, `interspect_events`) is observation-oriented — it records what happened. The escalation protocol requires a request-oriented primitive — it asks the human to do something.

The kernel's `state` table (generic key-value store) could hold escalation requests without schema changes:
```
key: "escalation.decision", scope_id: "run-xyz"
payload: {"type":"tradeoff","context":"...","options":[...],"recommendation":"...","urgency":"high"}
```

But this is a workaround, not a design. Escalations need:
- Status tracking (pending, acknowledged, resolved)
- Priority ordering (for the attention queue)
- Expiration (stale escalations should age out)
- Response capture (what the human decided, for Interspect learning)

The `discoveries` table is the closest existing model — it has status lifecycle, confidence tiers, and feedback signals. The escalation protocol could be modeled as a new entity type in Intercore (an `escalations` table) or as a discovery subtype. Either way, this is a kernel schema change the document doesn't acknowledge.

**Recommendation:** Acknowledge that the escalation protocol requires either (a) a new Intercore table (schema version bump, migration path needed) or (b) a creative use of existing `state` table with conventions (no schema change but fragile). Recommend option (a) because escalations are a first-class entity in the target architecture, not a transient state value.

**Classification:** Additive schema change, but unacknowledged and unscoped. The kernel team needs to be consulted.

---

## Finding 8: The Migration Sequence in the Autarch Vision Doc Is Sound — The Gap Analysis Should Build On It, Not Ignore It [P1 — Process risk]

**What the document says:** The "Recommended Next Steps" list six items as though starting from scratch: write PRD, define protocol, prototype dashboard, extract arbiter, connect Pollard, add autonomous sprint.

**What already exists:** The Autarch vision doc (v1.1) contains a detailed four-stage migration plan:
1. Bigend (read-only — migrate first)
2. Pollard (research → discovery pipeline)
3. Gurgeh (PRD → run lifecycle)
4. Coldwine (task orchestration — migrate last)

It also contains an arbiter extraction schedule (Phase 1: confidence scoring, Phase 2: sprint sequencing, Phase 3: task orchestration) and a migration coexistence strategy (dual-write mode, legacy fallback, one-time import scripts).

The gap analysis's "next steps" don't reference any of this existing plan. They risk creating a parallel, conflicting migration track.

**Recommendation:** The gap analysis should explicitly build on the Autarch vision doc's migration sequence:
1. Complete Bigend's Intercore migration (already planned, lowest risk)
2. Add Supervisor mode to Bigend (attention filtering on top of Intercore data)
3. Complete Pollard's Intercore migration (already planned)
4. Add Supervisor mode to Pollard (auto-triage on top of discovery pipeline)
5. Extract Gurgeh's arbiter (already planned, Phase 1-2)
6. Add Supervisor mode to Gurgeh (autonomous sprint with escalation)
7. Extract Coldwine's arbiter (already planned, Phase 3)
8. Add Supervisor mode to Coldwine (autonomous execution with escalation)
9. Build Executive dashboard on top of working Supervisor modes

This interleaves the two migration tracks (backend migration and UX mode migration) so each step is independently valuable and testable.

**Classification:** Process risk. Two parallel migration plans for the same apps will cause confusion and wasted work.

---

## Summary

| # | Finding | Severity | Type | Action |
|---|---------|----------|------|--------|
| 1 | No incremental adoption path for three modes | P0 | Breaking | Define three adoption phases (A/B/C) |
| 2 | Operator mode must remain default during transition | P1 | Additive if handled | Explicit commitment to preserve default |
| 3 | Exception-based interaction requires Coldwine schema change | P1 | Breaking | Choose attention model (schema or kernel-derived) |
| 4 | Portfolio view needs no schema changes | P3 | Additive | No action needed |
| 5 | Ring profiling is unacknowledged Interspect capability gap | P2 | Unclear value | Document as follow-on, not implicit |
| 6 | No irreversibility analysis | P1 | Missing | Add reversibility classification |
| 7 | Escalation protocol needs kernel representation | P2 | Additive unscoped | Acknowledge schema change or state-table workaround |
| 8 | Ignores existing Autarch vision migration plan | P1 | Process risk | Build on existing 4-stage plan, don't replace it |

## Recommended Migration Sequence

The safe adoption order, interleaving the existing Autarch backend migration with the new autonomy modes:

```
Existing migration (Autarch vision doc)     Autonomy mode additions (this doc)
─────────────────────────────────────────   ──────────────────────────────────
1. Bigend → Intercore backend            →  2. Bigend: add Supervisor mode
3. Pollard → Intercore discovery         →  4. Pollard: add Supervisor mode
5. Gurgeh arbiter extraction Phase 1-2   →  6. Gurgeh: add Supervisor mode
7. Coldwine arbiter extraction Phase 3   →  8. Coldwine: add Supervisor mode
                                         →  9. Executive dashboard (new surface)
```

Each numbered step is independently valuable. Each can be shipped, tested, and rolled back without affecting subsequent steps. The existing migration plan is preserved as the backbone; autonomy modes are additive layers on top of each completed migration.

This is how you evolve a platform. Not by redesigning four apps in parallel, but by extending each app as its foundation stabilizes.
