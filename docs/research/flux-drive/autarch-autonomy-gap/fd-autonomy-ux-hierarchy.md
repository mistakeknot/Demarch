# fd-autonomy-ux-hierarchy: UX Mode Hierarchy & Interaction Model Review

**Reviewer:** fd-autonomy-ux-hierarchy (product design / multi-persona UX)
**Document:** `docs/research/autarch-autonomy-gap-analysis.md`
**Date:** 2026-02-25
**Scope:** Mode boundary precision, gap-to-mode mapping, dashboard-vs-chat resolution, per-item vs exception data model, portfolio aggregation layer, mutual exclusivity of modes

---

## P0 Findings

### [P0] The Executive/Supervisor/Operator mode boundaries have no implementable switching criteria (lines 122-128)

The mode hierarchy table at lines 122-128 defines three modes by human role, interaction rate, and autonomy level:

| Mode | Interaction Rate | When |
|------|-----------------|------|
| Executive | <5% of items | L3-L4 |
| Supervisor | ~10% of items | L2-L3 |
| Operator | ~100% of items | L0-L1 |

A developer reading this cannot implement mode-switching logic. The document gives no answer to the most basic implementation question: **who decides which mode is active, and when does the switch happen?**

Three plausible interpretations exist, each with fundamentally different implementation:

1. **User-selected mode.** The human picks Executive/Supervisor/Operator as a preference. This is a settings toggle. Trivial to implement but contradicts the document's claim that mode maps to autonomy level -- the user might select Executive mode on a project at L0, creating a mismatch where the dashboard shows "no attention items" because the agency has no autonomous capability yet.

2. **Autonomy-derived mode.** The system infers mode from the run's autonomy level. This requires Intercore to expose an autonomy level per run (it does not today -- `Run.AutoAdvance` is a boolean, not a graduated scale). It also means the user cannot override -- they are locked into Operator mode for L0-L1 runs even if they want a hands-off summary view.

3. **Hybrid: per-project mode with system defaults.** The system defaults to a mode based on autonomy level but the user can override per project. This is the most realistic but requires a new data structure (project-mode mapping) not mentioned anywhere in the document.

The table's "When" column conflates the *recommended* mode with the *active* mode. A developer needs a state machine: initial mode, transition triggers, override rules, and what happens when a single TUI session shows projects at different autonomy levels simultaneously. None of this is specified.

**Recommendation:** Define mode as a two-dimensional choice: (a) a per-project autonomy level reported by Intercore (the system's capability), and (b) a per-project user preference for engagement depth (the human's intent). Mode = min(capability, preference). Add an `engagement_level` field to whatever project-settings structure Autarch uses, defaulting to the autonomy level. Specify the state transitions explicitly.

---

### [P0] Per-item vs exception-based interaction (Gap 3) is a data model problem, not a UX mode problem (lines 69-78)

Gap 3 states that the human currently touches ~100% of items and should touch <10% at L2-L3. The document frames this as an interaction model change -- switch the UX from "show everything" to "show exceptions." But the deeper issue is: **what generates the exception signal?**

Today's data flow in Autarch is:

1. `BigendView` loads runs, dispatches, and sessions via `intercore.Client` and `autarch.Client`.
2. `ColdwineView` loads epics, stories, tasks, and runs.
3. `PollardView` loads insights from file-based hunters.
4. None of these data sources emit a "this item needs human attention" signal.

For exception-based attention to work, every item must carry a classification: **needs-attention vs proceeding-normally**. This classification does not exist in any current data type. Looking at `pkg/intercore/types.go`:

- `Run` has `Status` (active/completed/cancelled/failed) but no "blocked-needs-human" status.
- `Dispatch` has `Status` but no "escalated" status.
- `GateResult` has `Result` (pass/fail) but a failed gate does not automatically mean "needs human" -- it could mean "will auto-retry" at L3.

The gap analysis proposes an "attention queue" (line 202) as an architectural requirement, but treats it as an infrastructure piece to wire up. In reality, the attention queue requires a new data classification layer:

- Every run needs a `human_attention_required` flag with a reason enum (gate_exhausted, budget_exceeded, tradeoff_decision, milestone_completed).
- Every dispatch needs escalation metadata (retry count, remediation attempts, whether auto-remediation is available).
- Every gate failure needs an urgency classification (blocking with no auto-fix vs blocking with retry available vs informational).

This is not something the UX layer can paper over. If the kernel and OS do not emit structured "needs-attention" events, the Executive mode dashboard has nothing to populate its decision queue with. The document skips this, listing "Structured escalation protocol" as step 1 of architectural requirements (line 205) without acknowledging that it requires schema changes in Intercore's event types and Clavain's gate evaluation logic.

**Recommendation:** Before designing Executive mode UX, define the attention classification schema as a kernel-level data type. Add an `EscalationEvent` to Intercore's event bus with fields: `urgency` (blocking/advisory), `category` (decision/exception/approval/milestone), `remediation_attempts` (int), `options` (structured action set). Without this, Executive mode is a dashboard with no data source.

---

## P1 Findings

### [P1] Dashboard-centric vs chat-centric (Gap 4) is relocated, not resolved (lines 80-91)

The document proposes that chat becomes "a drill-down tool" while the dashboard becomes the primary surface (line 91). But the current architecture has chat deeply embedded in every view -- `BigendView`, `ColdwineView`, `GurgehView`, and `PollardView` all instantiate a `pkgtui.ChatPanel` and a view-specific `ChatHandler`. The `ShellLayout` 3-pane model (sidebar | document | chat) is the structural foundation of every Autarch view.

The proposed Executive mode dashboard (lines 135-166) has no chat panel. It is a decision queue with expand/collapse sections. This is not a mode switch within the existing `ShellLayout` -- it is a fundamentally different view architecture. The document says "Drill-down reveals the operator mode. Clicking an active ring opens the current Gurgeh/Coldwine/Pollard view" (line 173), which means the Executive dashboard must be a *parent* view that can instantiate child views on demand.

This creates a new navigation problem the document does not address: when the user drills down from Executive dashboard into Coldwine's operator mode, how do they get back? Is the Executive dashboard a tab alongside Bigend/Gurgeh/Coldwine/Pollard? Does it replace the tab bar entirely? Can the user have both the Executive dashboard and an Operator-mode Coldwine view open simultaneously?

The current `UnifiedApp` manages views as a flat tab list (line references: `unified_app.go:133` `SetDashboardViewFactory`). The Executive dashboard needs to be either (a) a new tab that coexists with the four tool tabs, creating a 5-tab model where one tab is structurally different from the others, or (b) a replacement for the tab bar that relegates tool views to drill-down sub-views. Option (a) is simpler but undermines the "Executive mode is the default" claim. Option (b) requires rewriting the navigation model.

**Recommendation:** Explicitly choose between "Executive dashboard as a new tab" (coexists with tool tabs, user picks their default) vs "Executive dashboard as the root view" (tool views are drill-down children). The former is implementable within the current `UnifiedApp` architecture. The latter requires a navigation hierarchy refactor. The document implies (b) but never commits to it, which will force the implementer to make an unreviewed architectural decision.

---

### [P1] Gap 5 (portfolio view) requires a cross-project aggregation layer that Intercore's portfolio primitives do not provide (lines 95-97)

The document states that "Intercore already has portfolio orchestration primitives (run budgets, cross-project verification)" and implies the gap is in composition, not infrastructure (line 211).

After reviewing the actual `ic portfolio` implementation (`core/intercore/cmd/ic/portfolio.go`), the portfolio primitives are:

1. **`ic portfolio dep add/list/remove`** -- manages dependency edges between projects within a portfolio.
2. **`ic portfolio relay`** -- a polling loop that relays events between child project databases.
3. **`ic portfolio order`** -- topological sort of project dependencies.
4. **`ic portfolio status`** -- shows per-child run status with blocked-by annotations.

What these primitives do NOT provide:

- **Aggregated metrics across projects.** There is no `ic portfolio summary` that returns total tokens spent, total runs active, total gate failures across the portfolio. The Executive dashboard's "Portfolio Health" section (line 138: "3 sprints active, 1 blocked, 2 completed today") requires aggregating data from multiple per-project databases. The `DBPool` in `portfolio/dbpool.go` opens read-only handles to child DBs, but no query function aggregates across them.

- **Cross-project attention items.** The "Attention Required" section (lines 141-148) needs to collect exceptions from all projects and sort them by urgency. No Intercore API returns this. The relay copies events between DBs but does not classify or rank them.

- **Budget tracking across projects.** The dashboard shows "Budget: 42K/100K" (line 138). Intercore has per-run budgets (`Run.TokenBudget`) but no portfolio-level budget. Summing run budgets across projects requires iterating all active runs in all child DBs.

The gap is not "composition" as the document claims. It is a missing aggregation query layer. Either Intercore needs new portfolio-level query commands (e.g., `ic portfolio metrics`, `ic portfolio attention`), or Autarch needs an in-process aggregation engine that polls multiple DBs and computes cross-project views. The latter is what `BigendView` partially does today (it loads runs and dispatches from a single project's Intercore DB), but extending it to multiple projects means managing N database connections and N polling loops.

**Recommendation:** Acknowledge that the Executive dashboard's portfolio view requires a new aggregation component -- either kernel-side (`ic portfolio metrics/attention`) or app-side (a portfolio aggregator in Autarch that manages multi-DB queries). The choice has significant implications: kernel-side is authoritative but couples the app layer's display needs into the kernel; app-side is flexible but duplicates query logic across potential app implementations (violating "apps are swappable").

---

### [P1] The document conflates "ring" as organizational metaphor with "ring" as runtime architecture (lines 212-236)

The Recursive Ring Model section (lines 212-236) maps each Autarch app to an "agency ring" and claims each ring is "autonomous," "budget-constrained," "escalation-capable," "observable," and "self-improving." But today these apps are Go view structs (`BigendView`, `ColdwineView`, etc.) running in a single Bubble Tea process. They are rendering surfaces, not autonomous agents.

For a ring to be "autonomous" in the described sense, it must be a separate process (or at minimum a separate goroutine with its own event loop) that makes decisions without the main TUI process driving it. The current architecture is the opposite: Bubble Tea's `Update()` loop is the single event processor, and all views are synchronous renderers within it.

The document seems to use "ring" in two incompatible senses:

1. **Organizational ring:** A domain boundary for grouping related work (design, execution, research). This is a labeling exercise with no runtime implications.
2. **Autonomous ring:** A self-driving sub-agency that runs independently and escalates to the human. This requires a fundamentally different runtime -- likely Clavain sprint processes running in the background, with Autarch observing them.

The vision doc for Autarch (lines 65-73 of `autarch-vision.md`) explicitly says apps are rendering surfaces that read kernel state and submit intents. Autonomous rings are OS-level constructs (Clavain sprints), not app-level constructs. The gap analysis muddles this by saying "Autarch apps should map to agency rings" -- but the mapping is observational (the app *observes* the ring), not identity (the app *is* the ring).

**Recommendation:** Clarify that the "ring" in the Executive dashboard is a visualization of a Clavain-managed autonomous sprint, not an Autarch-owned construct. The ring's autonomy lives in the OS layer. Autarch renders ring status and routes human input to the OS. This distinction matters because it determines where the implementation work goes: ring autonomy is a Clavain sprint mode feature, not an Autarch UX feature.

---

## P2 Findings

### [P2] Gap 6 (manual phase advancement) is already acknowledged in the Autarch vision doc and adds no new analysis (lines 99-105)

Lines 99-105 restate the arbiter extraction debt from the Autarch vision doc (lines 89-99 of `autarch-vision.md`) and add the observation that "the extracted logic must also become autonomous." This is correct but not novel -- the Autarch vision doc's Phase 2 and Phase 3 extraction schedule already imply autonomous operation ("Gurgeh becomes a TUI renderer for the spec sprint"). The gap analysis's added value here is the framing sentence "the arbiter's existence assumes the human is present to drive it," but this is a restatement of the operator-vs-executive tension from Gap 1.

Gap 6 should be folded into Gap 1 as a specific instance rather than standing as a separate gap, since the proposed resolution (extract + autonomize) is identical to the resolution for Gap 1 (move from operator to executive mode). Having 7 gaps when 6 are sufficient dilutes the analysis's focus.

**Recommendation:** Merge Gap 6 into Gap 1 as a subsection, or explicitly state what Gap 6 requires beyond what Gap 1's mode hierarchy already addresses. As written, Gap 6 is not a separate gap -- it is the mechanism by which Gap 1 gets resolved for Gurgeh and Coldwine specifically.

---

### [P2] Modes are presented as mutually exclusive but the interaction model requires simultaneous occupancy (lines 122-128, 170-173)

The mode table (lines 122-128) presents Executive, Supervisor, and Operator as discrete modes with distinct interaction rates. But line 173 says "Drill-down reveals the operator mode" from within the Executive dashboard. This means a user in Executive mode temporarily enters Operator mode for a specific ring, then returns to Executive mode.

This is not mode switching -- it is mode layering. The user occupies Executive mode at the portfolio level and Operator mode at the project level simultaneously. The document does not acknowledge this, which matters because:

1. **State management:** When the user drills into Operator mode for one ring, do updates to other rings' attention items still arrive? If yes, the Executive dashboard must remain active in the background. If no, the user loses portfolio awareness while drilling down.

2. **Per-project mode:** Different projects may warrant different engagement levels. A new, untrusted project might be in Operator mode while a mature project is in Executive mode. The mode hierarchy does not accommodate per-project mode assignment.

3. **Transition friction:** If Executive mode is the default and Operator mode is drill-down, the user must navigate back after each intervention. This creates a "hub and spoke" navigation pattern that may be more cumbersome than the current flat tab model for users who frequently intervene.

**Recommendation:** Redefine the modes as hierarchical scopes rather than mutually exclusive states: Executive scope (portfolio), Supervisor scope (project), Operator scope (item). The user always exists at all three scopes but their *default view* is one scope. Drill-down moves the viewport to a narrower scope; back navigation returns to the wider scope. This is a navigation model, not a mode model, and should be described as such.

---

### [P2] The "Attention Required" mockup assumes structured action options that no current system produces (lines 141-148)

The Executive dashboard mockup shows:

```
[interlock] Gate failed: safety review found P0 issue
  -> 3 remediation attempts exhausted. Options: [override] [investigate] [reassign] [abort]
```

This implies the system knows: (a) the gate failed, (b) remediation was attempted 3 times, (c) remediation is exhausted, and (d) exactly four actions are available. Today:

- Gate failures emit a `GateResult` with pass/fail and evidence. No retry count.
- `GateResult.Evidence.Conditions` lists which checks passed/failed but not remediation attempts.
- Available actions depend on the run's current state, the user's permissions, and the OS configuration -- no single API returns "here are your options."

The structured action set (`[override] [investigate] [reassign] [abort]`) is the escalation protocol from Gap 7, which the document lists as a future requirement (lines 107-117). The mockup presents it as a solved problem to illustrate Executive mode, but it depends on the very infrastructure the document says does not exist yet. This creates a circular dependency: the mockup motivates the infrastructure, but the infrastructure's design depends on knowing what the mockup needs.

**Recommendation:** Separate the mockup into two versions: (1) what Executive mode can show with today's kernel primitives (gate failed, run blocked, no structured options -- just "view details"), and (2) what it can show after the escalation protocol is implemented. This grounds the near-term implementation and clarifies the dependency chain.

---

## P3 Findings

### [P3] The Interspect Insights section of the mockup conflates two data sources (lines 157-159)

The mockup shows:

```
Interspect Insights
  Token efficiency up 12% this week (model downgrades)
  fd-architecture false positive rate: 8% (was 23%)
  Sprint completion rate: 94% (7-day rolling)
```

"Token efficiency up 12%" and "fd-architecture false positive rate" are Interspect profiler metrics (Phase 1 evidence collection). "Sprint completion rate: 94%" is a kernel metric (derived from run lifecycle events). Mixing them under "Interspect Insights" implies Interspect owns sprint completion rate, which it does not -- Interspect reads it from the kernel but the metric is a kernel aggregate.

This matters for implementation: the Interspect insights panel would need to query both the Interspect DB (`.clavain/interspect/interspect.db`) and the kernel DB. If presented as a single data source, a developer might try to read everything from one DB and get stale or missing data.

**Recommendation:** Split into "Interspect Insights" (profiler-owned metrics) and "Sprint Metrics" (kernel-owned aggregates), or add a note that the panel is a composite view joining two data sources.

---

### [P3] "Recommended Next Steps" omit the data model work that every UX change depends on (lines 239-246)

The six recommended steps are all UX and OS features: write a PRD, define protocol, prototype dashboard, extract arbiter, connect Pollard, add autonomous sprint mode. None of them address the prerequisite data model changes identified in this review:

- Attention classification schema (P0 finding above)
- Portfolio aggregation queries
- Per-project engagement level setting
- Escalation event type in the kernel event bus

Without these, the PRD (step 1) will be designed against an idealized data model and the prototype (step 3) will have no real data to render.

**Recommendation:** Insert a step 0: "Define the attention/escalation data model in Intercore and Clavain" before any UX design work begins. This grounds the subsequent steps in implementable primitives rather than aspirational mockups.

---

## Summary

The gap analysis correctly identifies the tension between Autarch's operator-centric UX and Demarch's executive-centric vision. The seven gaps are real and well-observed. However, the proposed resolution -- a three-mode hierarchy (Executive/Supervisor/Operator) -- remains at the label level. The document does not specify:

1. **Who controls mode selection** (user choice vs system inference vs hybrid)
2. **What data model changes are prerequisite** (attention classification, escalation events, portfolio aggregation)
3. **How modes compose** (simultaneous occupancy across portfolio/project/item scopes)
4. **Where autonomous behavior lives** (OS-layer sprints, not app-layer "rings")

The core risk is that the document's mockups and ring diagrams create the impression that Executive mode is a UX design problem, when it is primarily a data model and OS-layer autonomy problem. The UX is the last mile; the infrastructure is the first 90%.
