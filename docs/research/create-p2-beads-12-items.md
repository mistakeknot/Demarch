# Create 12 P2 Beads from Autarch UX Review

**Date:** 2026-02-25
**Parent Epic:** iv-eblwb (Autarch UX Review)
**Status:** All 12 beads created successfully

## Summary

Created 12 priority-2 beads capturing architectural and UX debt from the Autarch UX review. Beads focus on messaging architecture gaps, cross-tool navigation deficiencies, hidden UI state, unused API surface, and architecture extraction work. All use parent reference `iv-eblwb`.

## Beads Created

### 1. iv-eblwb.1 — Messages Route Only to Active View [Type: feature]

**Title:** [P2] Messages route only to active view — background ops silently dropped

**Description:** unified_app.go:560-564 sends non-key messages only to currentView. Only dispatchBatchMsg fans out to all views. Research progress, sync completion, and other background operation results are silently dropped on tab switch. Root cause behind several cross-tool composition issues.

**Root Cause:** The message dispatch router in unified_app uses a single-view message route for most event types. Background operations (research completion, sync status, signal updates) only reach the currently active view. When a user switches tabs, in-flight background messages destined for hidden views are discarded.

**Impact:**
- Research progress updates lost when switching away from Pollard tab
- Sync completion notifications don't reach background views
- Signal updates disappear on tab switch
- Cross-tool composition breaks because views can't coordinate

**Fix:** Extend the dispatch fan-out pattern (currently only used for dispatchBatchMsg) to research/signal message types. Use a broadcast channel or observer pattern so all views receive state updates regardless of visibility.

---

### 2. iv-eblwb.2 — Pollard Link Insight Is Fire-and-Forget [Type: bug]

**Title:** [P2] Pollard Link Insight is fire-and-forget — no cross-tool navigation

**Description:** Link Insight at pollard.go:514-541 creates backend link but Gurgeh never displays linked insights. No navigation from Pollard to linked spec. Auto-selects first validated spec with no user choice.

**Root Cause:** The Link Insight action in Pollard creates a backend link record (insight relationships) but the UI never surfaces it. GurgehView has no section for linked insights, and Pollard provides no "Go to linked spec" keybinding. When multiple specs are valid, auto-selection with no user choice creates a poor UX.

**Impact:**
- Users can't discover linked insights from the UI
- Pollard's link creation is invisible
- No cross-tab navigation path from Pollard to related Gurgeh specs
- Link relationships exist in backend but unreachable from TUI

**Fix:**
1. Add "Linked Insights" section to GurgehView showing incoming links
2. Add Enter key handler in Pollard Link Insight to navigate to selected target spec
3. Replace auto-selection with explicit user choice when multiple specs are valid

---

### 3. iv-eblwb.3 — Signals Overlay Is Read-Only [Type: feature]

**Title:** [P2] Signals overlay is read-only — no drill-down or action

**Description:** signals_overlay.go:114-143 handles only esc/q/up/down/tab/ctrl+r. No Enter key handler for drill-down. No cross-tool navigation from signal to source. Detail field not shown.

**Root Cause:** The signals overlay is a passive list viewer. It supports navigation but not interaction. The Detail field exists in the signal struct but isn't rendered. No navigation path exists from a signal back to its source (which might be in Pollard, Sprint, Coldwine, etc.).

**Impact:**
- Users can't drill into signals to understand context
- Signal detail information hidden
- No way to navigate from signal to source operation
- Overlay feels incomplete and non-interactive

**Fix:**
1. Add Enter handler that navigates to source tool based on signal.Source
2. Render Detail field in the signal list
3. Implement cross-tab navigation for signal source routing

---

### 4. iv-eblwb.4 — Sprint/Coldwine Tab Duplication [Type: bug]

**Title:** [P2] Sprint/Coldwine tab duplication — two places to manage sprints

**Description:** Both tabs handle DispatchCompletedMsg and show sprint data. Sprint shows kernel state (phases/gates/budget); Coldwine shows tasks. No cross-links between them. Merge plan exists at docs/plans/2026-02-25-merge-sprint-into-coldwine.md.

**Root Cause:** The Sprint tab displays kernel-level abstractions (phases, gates, budget) while Coldwine displays task-level state (epics, stories, tasks). Both subscribe to the same DispatchCompletedMsg and maintain separate state views of the same underlying work. This creates two points of truth.

**Impact:**
- Users must context-switch between two tabs for sprint management
- State synchronization burden across two views
- No cross-links to help navigation
- Violates single responsibility principle

**Fix (Interim):** Add "View Sprint Details / View in Coldwine" bidirectional shortcuts
**Fix (Long-term):** Implement merge plan to unify into single tab with layered detail

---

### 5. iv-eblwb.5 — Event Stream Uses 10s Polling [Type: bug]

**Title:** [P2] Event stream uses 10s polling, not streaming EventsTail API

**Description:** EventWatcher at event_watcher.go:54-93 uses batch polling with time.Sleep(10s) instead of EventsTail with --follow (which exists in the client at events.go:14-57). Causes up to 10s latency, redundant re-fetches, blocking sleep in tea.Cmd goroutine.

**Root Cause:** The event watcher was implemented with a simple polling loop sleeping 10 seconds between fetches. The Intercore client already supports streaming with EventsTail --follow, but the TUI doesn't use it. The blocking sleep wastes goroutine capacity and adds latency.

**Impact:**
- Up to 10s delay in event visibility
- Inefficient polling creates redundant API calls
- Blocks a tea.Cmd goroutine during sleep
- User waits seconds to see event updates

**Fix (Phase 1):** Migrate to tea.Tick pattern (like DispatchWatcher) with shorter polling intervals
**Fix (Phase 2):** Implement true streaming with EventsTail --follow API

---

### 6. iv-eblwb.6 — Intercore Methods Not Surfaced in TUI [Type: feature]

**Title:** [P2] Agent registry, artifact list, dispatch kill not surfaced in TUI

**Description:** 15 of 28 Intercore client methods (54%) are unused in the TUI. RunAgentList, ArtifactList, DispatchKill, GateRules, EventsTail, RunCurrent, DispatchStatus — all require CLI access.

**Root Cause:** The Intercore Go client exposes 28 methods but the TUI only uses ~13. Critical operations like viewing agent registry, listing artifacts, killing dispatches, and querying gate rules are missing from the UI. Users must drop to CLI for these operations.

**Impact:**
- 54% of client API surface unused
- Users forced to CLI for common operations
- Poor UX for multi-agent debugging and orchestration
- Incomplete feature surface

**Fix:**
1. Add agent registry section to Sprint tab
2. Add artifact list to run detail view
3. Add kill keybinding (e.g., ctrl+x) for selected dispatch
4. Surface GateRules in phase sidebar
5. Add dispatch status detail view

---

### 7. iv-eblwb.7 — Dual Quality Scoring Systems [Type: bug]

**Title:** [P2] Dual quality scoring systems — arbiter confidence vs review package

**Description:** Two independent scoring systems: arbiter confidence calculator (5-axis weighted, confidence/calculator.go) and review package (penalty deductions, criteria.go). Overlapping concerns with incompatible scoring semantics.

**Root Cause:** Quality assessment evolved in two directions. The arbiter's confidence calculator uses weighted multi-axis scoring while the review package uses penalty-based deductions. They answer different questions but overlap in domain. Vision Phase 1 extraction doesn't address unification.

**Impact:**
- Two incompatible scoring semantics
- Unclear which system is authoritative
- Maintenance burden on both codepaths
- Confusing signal to users

**Fix:** During Vision Phase 1 extraction, reconcile into single OS-level quality API with clear semantics (weighted axes vs penalties, decision rules)

---

### 8. iv-eblwb.8 — Dispatch Watcher Polling Protocol [Type: bug]

**Title:** [P2] Dispatch watcher polling protocol is app-layer logic (~50 LOC)

**Description:** dispatch_watcher.go implements full polling protocol with known-status tracking and dedup that any replacement client must duplicate. Terminal state definitions, state tracking, and completion detection are agency logic that should be kernel event subscription.

**Root Cause:** The dispatch watcher contains ~50 lines of polling orchestration logic that properly belongs in the kernel event system. Any alternative client must reimplement terminal state detection, dedup tracking, and polling coordination.

**Impact:**
- 50 LOC of duplicative polling logic
- Terminal state semantics leak to app layer
- Difficult to swap event subscription mechanism
- Protocol knowledge scattered

**Fix:** Move terminal state definitions and completion detection to kernel event subscription API. Reduce TUI dispatch watcher to simple observer of kernel events.

---

### 9. iv-eblwb.9 — Task Decomposition Rules in App Layer [Type: bug]

**Title:** [P2] Task decomposition rules embedded in app layer (~150 LOC)

**Description:** internal/coldwine/tasks/generate.go encodes policies: foundational epic detection, automatic test task generation, dependency wiring. These decomposition rules are business logic about work structure. Vision Phase 3 targets extraction to Clavain.

**Root Cause:** Task generation logic including epic classification, test task synthesis, and dependency inference is implemented in the TUI's task generation module. These are OS-level policies that should be computed by Clavain, not the app.

**Impact:**
- ~150 LOC of business logic in app layer
- Non-composable task generation
- Other tools can't access decomposition policy
- Policy tightly coupled to Coldwine view state

**Fix:** Extract to Clavain during Vision Phase 3. Define decomposition API at OS layer. Coldwine becomes a pure consumer of pre-decomposed work.

---

### 10. iv-eblwb.10 — PhaseSidebar Hidden by Default [Type: bug]

**Title:** [P2] PhaseSidebar hidden by default during sprint — progress invisible

**Description:** The 8-phase progress indicator (most useful orientation signal during onboarding) is behind ctrl+b toggle, not mentioned in sprint hint.

**Root Cause:** The phase sidebar is initialized in hidden state. During first-run onboarding (the moment when users most need progress orientation), the sidebar must be explicitly toggled visible.

**Impact:**
- Users miss the most valuable orientation signal
- Onboarding flow doesn't guide users to the sidebar
- Hidden functionality discourages exploration
- Progress tracking is opt-in rather than default

**Fix:** Change `SprintView.Init()` to initialize PhaseSidebar in visible state (~1 LOC). Update sprint hint to mention sidebar toggle.

---

### 11. iv-eblwb.11 — No Second-Spec Path [Type: bug]

**Title:** [P2] No second-spec path — New Spec creates blank draft, not sprint wizard

**Description:** New Spec in command palette creates an untitled draft without triggering the 8-phase sprint wizard. The 8-phase flow is only accessible during first-run onboarding, not for spec iteration.

**Root Cause:** The sprint wizard is wired only into the first-run onboarding flow. Subsequent spec creation goes through a different code path (new blank draft without wizard) that lacks the structure and guidance.

**Impact:**
- Onboarding users get the full 8-phase wizard
- Returning users get weaker UX (blank draft)
- Inconsistent spec creation flows
- New specs lack the guidance structure

**Fix:** Route "New Spec" from command palette through the same 8-phase wizard. Add context flag to distinguish first-run vs iteration mode if needed.

---

### 12. iv-eblwb.12 — Intermute Startup Failure Is Silent [Type: bug]

**Title:** [P2] Intermute startup failure is silent — only visible in log pane

**Description:** IntermuteStartFailedMsg handled by slog.Error at unified_app.go:555-557. Log pane hidden by default. User sees no visible indication until first failed API call triggers fallback badge lazily.

**Root Cause:** The startup failure message is logged but not surfaced to the user. The log pane is hidden by default. The fallback indicator (badge) only appears lazily on the first failed API call.

**Impact:**
- User doesn't see startup failure immediately
- Requires opening hidden log pane to diagnose
- Fallback activation hidden until first API error
- Poor error visibility in first-run experience

**Fix:** Surface startup failure as visible banner/toast immediately. Keep it visible until Intermute successfully connects or user dismisses. Update fallback indicator to highlight on startup failure as well.

---

## Cross-Cutting Themes

### 1. Messaging Architecture (3 beads: 1, 3, 5)
The core messaging dispatch system needs architectural work:
- **Bead 1**: Message delivery only to active view
- **Bead 3**: Overlay signal actions require navigation support
- **Bead 5**: Event streaming needs architectural upgrade

### 2. Cross-Tool Navigation (3 beads: 2, 3, 4)
Tools can't navigate between each other:
- **Bead 2**: Pollard → Gurgeh navigation missing
- **Bead 3**: Signal → Source navigation missing
- **Bead 4**: Sprint ↔ Coldwine links missing

### 3. Hidden UI State (3 beads: 10, 11, 12)
Critical features or state are hidden or opt-in:
- **Bead 10**: Phase sidebar hidden by default
- **Bead 11**: Sprint wizard unreachable for new specs
- **Bead 12**: Startup failures not visible

### 4. Unused API Surface (3 beads: 6, 8, 9)
The kernel and app layer have capability/logic that TUI doesn't expose:
- **Bead 6**: 54% of Intercore client API unused
- **Bead 8**: Dispatch watcher protocol is app logic
- **Bead 9**: Task decomposition rules in app layer

---

## Command Execution Log

All 12 beads created using `bd create` with `--priority 2` and `--parent iv-eblwb`:

```
✓ iv-eblwb.1  Messages route only to active view [feature]
✓ iv-eblwb.2  Pollard Link Insight fire-and-forget [bug]
✓ iv-eblwb.3  Signals overlay read-only [feature]
✓ iv-eblwb.4  Sprint/Coldwine tab duplication [bug]
✓ iv-eblwb.5  Event stream 10s polling [bug]
✓ iv-eblwb.6  Intercore methods not surfaced [feature]
✓ iv-eblwb.7  Dual quality scoring systems [bug]
✓ iv-eblwb.8  Dispatch watcher polling protocol [bug]
✓ iv-eblwb.9  Task decomposition rules in app [bug]
✓ iv-eblwb.10 PhaseSidebar hidden by default [bug]
✓ iv-eblwb.11 No second-spec path [bug]
✓ iv-eblwb.12 Intermute startup failure silent [bug]
```

---

## Architecture Insights

### Messaging Layer Refactoring Needed
The single-view message routing (Bead 1) is the root cause blocking cross-tool composition. Fixing this unlocks Beads 2, 3 and improves event visibility (Bead 5).

### API Exposure Gap
54% of Intercore API unused (Bead 6) suggests significant feature surface missing from TUI. Combined with Beads 8-9 (kernel logic in app), indicates extraction and API-driven design would improve composability.

### UX Onboarding Bottleneck
Three UX beads (10, 11, 12) identify hidden/opt-in features that should be visible during first-run. These are quick wins that improve onboarding significantly.

### Duplication Smell
Beads 4, 7 identify significant duplication (tabs, scoring systems) that should be unified. Bead 4's merge plan is already documented; Bead 7 is targeted for Vision Phase 1.

---

## Next Steps

1. **Immediate (session)**: Implement quick wins (Beads 10, 12) — ~5 LOC total
2. **Short-term (week)**: Fix messaging architecture (Bead 1) to unblock cross-tool work
3. **Medium-term (2 weeks)**: Implement cross-tool navigation (Beads 2, 3, 4)
4. **Long-term (Vision phases)**: Extract app-layer logic (Beads 6-9) per architecture roadmap
