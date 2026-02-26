# Quality Review: Merge Sprint Tab into Coldwine

**Plan:** `apps/autarch/docs/plans/2026-02-25-merge-sprint-into-coldwine.md`
**Reviewer:** fd-quality (flux-drive)
**Date:** 2026-02-25
**Languages in scope:** Go (Bubble Tea TUI, lipgloss)

---

## Summary

The plan is structurally sound. The dependency graph is correct, the interface-escape
pattern for the circular import is well-chosen, and the feature decomposition into
sequential tasks maps cleanly to the existing codebase shape. The findings below are
concrete issues that will cause bugs, test gaps, or maintainability friction during
execution — not stylistic preferences.

---

## Findings

### F1 — `RunDetailPanel.View()` name collides with the `View` interface

**Severity: High**

The plan gives `RunDetailPanel` a method named `View() string`. The `pkg/tui.View`
interface (`view.go` line 12) already defines `View() string`. Any caller that holds a
`*RunDetailPanel` in a `View`-typed variable will accidentally satisfy the interface,
and any future refactor that passes `RunDetailPanel` to a View slot (plausible for the
split-pane path) will silently compile and then panic when `Init`, `Update`, `Focus`,
`Blur`, or `Name` are called.

**Fix:** Rename the render method to `Render() string` (matches `lipgloss.Style.Render`
convention and the `ShellLayout.Render` call already used by all views). Every call site
in the plan (`compact.CompactView()` becomes `compact.CompactRender()`, etc.) should
follow the same pattern.

```go
// pkg/tui/run_detail_panel.go
func (p *RunDetailPanel) Render() string
func (p *RunDetailPanel) CompactRender() string  // was CompactView()
```

---

### F2 — `ColdwineMode` and `LayoutMode` declared in the wrong file

**Severity: Medium**

Task 2 declares `ColdwineMode` inside `coldwine.go` and Task 7 declares `LayoutMode`
inside `coldwine.go` as well. Both are package-level types in the `views` package that
are needed from `unified_app.go` (which lives in the parent `tui` package). The plan
correctly identifies the circular import problem and solves it with a narrow interface
(`modeSettable`/`SetRunsMode()`). That pattern is right.

However, the plan also drafts `ColdwineView.SetMode(mode ColdwineMode)` (Task 2.2) as
part of the exported surface, and then the `/sprint` slash-command handler in
`unified_app.go` is shown type-asserting to a `modeSettable` interface with
`SetRunsMode()`. These two APIs for the same operation will exist simultaneously. Pick
one: either `SetRunsMode()` (narrowest, no type export needed) or export `ColdwineMode`
to a new `pkg/tui` type so `SetMode(mode pkgtui.ColdwineMode)` can be used from
`unified_app.go` without an interface dance. The current plan ships both — that is the
inconsistency to resolve.

**Fix (recommended):** Keep `ColdwineMode` unexported and use only `SetRunsMode()` from
`unified_app.go`. Drop `SetMode(mode ColdwineMode)` from the exported surface or make
it package-internal (`setMode`). If you later need more modes from outside `views`,
move `ColdwineMode` to `pkg/tui` at that point.

---

### F3 — `RunDetailPanel` allocated inside `View()` / `renderDocument()` — allocation-per-frame

**Severity: Medium**

Task 3.2 shows this in `renderDocument()`:

```go
compact := pkgtui.NewRunDetailPanel()
compact.SetData(run, nil, nil, nil, nil)
compact.SetMaxEvents(3)
compact.SetSize(v.width-4, 12)
lines = append(lines, compact.CompactView())
```

Bubble Tea calls `View()` on every frame. Allocating and discarding a `RunDetailPanel`
each frame is wasteful and will cause visible GC pressure at high frame rates (e.g.,
during dispatch polling). The existing `ColdwineView` already caches `runDetail
*pkgtui.RunDetailPanel` in its struct (Task 2.1 adds this field). The inline-expansion
path in Task 3 should reuse `v.runDetail` instead of constructing a throw-away panel.

**Fix:** In Task 3.2, gate on `v.runDetail != nil` (initialize it lazily in
`handleRunsKey` or when `sprintExpanded` becomes true) and call `v.runDetail.SetMaxEvents(3)` /
`v.runDetail.SetSize(...)` before calling `v.runDetail.Render()`. Same fix applies to
Task 4.2 (`renderSprintPanelForEpic` already shows this pattern correctly — use it as
the model).

---

### F4 — `SetData(run, nil, nil, nil, nil)` in both layout paths passes nil dispatches/events

**Severity: Medium**

Tasks 3.2 and 4.2 call `SetData(run, nil, nil, nil, nil)` with nil slices for
dispatches, budget, events, and gate. The plan notes "populate from cached data" but
`ColdwineView` has no fields that cache these — they live on `RunDashboardView`, which
is being deleted. After Task 6 removes `RunDashboardView`, there is nowhere to source
this data from.

The plan introduces `LoadRunDetail` (Task 1.2) and `RunDetailLoadedMsg`, and shows
wiring it on `s` keypress (Task 3.3). But the `runDetail` panel is rendered on every
`View()` call. If detail has not yet loaded (the `s` expand just triggered a `tea.Cmd`
that hasn't completed), the panel will render with nil slices, showing an incomplete
view on the first frame. This is acceptable as a loading state only if the
`RunDetailPanel.Render()` handles nil slices gracefully with a "Loading..." placeholder
— the plan must explicitly state this as a requirement in Task 1, otherwise Task 3 will
silently produce a blank section.

**Fix:** Add an explicit requirement in Task 1.1: `Render()` must display a "Loading
sprint detail..." placeholder when `run` is non-nil but `dispatches`, `budget`,
`events`, and `gate` are all nil. Document this as the intended loading state contract.

---

### F5 — `epicRuns` map not populated when entering Runs mode (Task 2 data flow gap)

**Severity: Medium**

`ColdwineView.epicRuns` is populated by `loadEpicRuns()`, which is triggered after
`epicsLoadedMsg`. In the existing code, `epicRuns` maps `epicID → *Run`. The plan's
Runs mode (`ModeRuns`) wants to show all runs, not just epic-linked runs. Task 1.2
introduces `LoadRuns` → `RunsLoadedMsg` with a flat `[]intercore.Run`. These two
populations are independent and complement each other.

The gap: in Task 5.1 (`computeOrphanRuns`), the plan iterates `v.runs` (the flat list
from `LoadRuns`) and `v.epicRuns` (the map from `loadEpicRuns`). But `loadEpicRuns` is
only called from `epicsLoadedMsg` handler — it is not called from `loadRunsForMode`.
When the user switches to Runs mode on a fresh session where `epicRuns` has been
populated, the data is stale (it reflects the run IDs from Intercore state, not live
run objects). When `computeOrphanRuns` checks `associated[run.ID]`, it compares run
IDs from `v.runs` (freshly fetched) with run objects from `epicRuns` (loaded via
separate Intercore state key). If a run was added after the initial `epicRuns` load,
it will be misclassified as orphan.

**Fix:** In `loadRunsForMode`, chain `loadEpicRuns()` as a second command so that
`epicRuns` is refreshed whenever the user explicitly enters Runs mode. The cost is a
second set of Intercore `StateGet` calls — acceptable since the user just triggered a
mode switch.

---

### F6 — `__mode_epics` / `__mode_runs` sentinel IDs in `SidebarSelectMsg`

**Severity: Low-Medium**

The plan proposes prepending sentinel items with IDs like `"__mode_epics"` to the
sidebar and routing them in the `SidebarSelectMsg` handler. This works but is fragile:
any code that iterates sidebar items and assumes all IDs are epic/run IDs (e.g., future
index lookups, persistence, analytics) will silently process the sentinel as data.

The existing code already has a better primitive: the `SidebarSelectMsg` routing in
`unified_app.go` uses named interface checks. The sidebar's own selection model could
be made to emit a distinct message type for structural controls vs. content selection.

**Fix (pragmatic):** Keep the sentinel approach but document the `__` prefix convention
as "system-reserved IDs that must not be treated as entity IDs" in `sidebar.go`. Add a
compile-time-enforced guard in the `SidebarSelectMsg` handler: put the sentinel case
blocks before the `default` and add a comment referencing the convention. This is low
cost and prevents silent data pollution.

---

### F7 — Command palette `Action` closures capture `v` (pointer to struct value)

**Severity: Medium**

Task 7.4 shows:

```go
tui.Command{
    Name: "Layout: Mode Toggle",
    Action: func() tea.Cmd { v.layoutMode = LayoutToggle; return nil },
},
```

The existing `Commands()` in `coldwine.go` already uses the same pattern for "New
Epic", "New Story", etc., and the MEMORY.md entry for `iv-1pkt` records that Action
closures run on a goroutine pool, NOT the Update/View goroutine. Reading `v.layoutMode`
inside an `Action` closure would be a data race.

However, in this specific case the Action only *writes* `v.layoutMode` and returns
`nil` (no `tea.Cmd` launched, just a field mutation). In Bubble Tea, the `Action` fires
and its returned `tea.Cmd` is sent back to the program — but the field write happens
inside the closure on the wrong goroutine before the tea.Cmd runs. This is the same
race pattern flagged in the MEMORY.md.

**Fix:** The layout mode toggle should not write directly in the `Action` closure.
Instead, return a `tea.Cmd` that emits a message:

```go
type layoutModeChangedMsg struct{ mode LayoutMode }

Action: func() tea.Cmd {
    return func() tea.Msg { return layoutModeChangedMsg{mode: LayoutToggle} }
},
```

Handle `layoutModeChangedMsg` in `Update()` to write `v.layoutMode`. This is the
correct pattern for all state mutations from the command palette.

---

### F8 — Task 3 guard `v.layoutMode == LayoutInline` references a field added in Task 7

**Severity: Low-Medium**

Task 3 adds inline expansion behavior gated on `v.layoutMode == LayoutInline`. Task 7
adds the `layoutMode` field and `LayoutMode` type. In the sequential execution order
(Tasks 1–7), Task 3 runs before Task 7, which means the code added in Task 3 will
reference an undefined field. The dependency graph in the plan shows Tasks 3, 4, and 7
as parallelizable after F1 — but they are not independent: Task 3 and Task 4 both
depend on `layoutMode` from Task 7.

**Fix:** Reorder: move Task 7 before Tasks 3 and 4, or add the `layoutMode` field stub
(with the `LayoutMode` type and iota constants) to `coldwine.go` at the end of Task 2
so that Tasks 3 and 4 can proceed. Update the dependency graph:

```
F1 → F2 → F7 → F3
F1 → F2 → F7 → F4
F1 → F2 → F6
F5 after F2
```

---

### F9 — No tests for `ColdwineView` mode-switching behavior (Task 2 test gap)

**Severity: Medium**

Task 2 is the largest behavioral change in the plan (new struct fields, new message
types, keybinding changes, sidebar mutation) and has no test specification. The plan
only says "existing `coldwine_dispatch_test.go` still passes" as the verification step.

The existing `coldwine_dispatch_test.go` tests `taskMatchesDispatch`, a pure function
with no state. It provides zero coverage for the mode toggle logic.

The risk profile of Task 2 is high: sidebar items change shape, `SidebarSelectMsg`
routing gains sentinel-ID branches, `Update()` gains new message handlers, and
`DispatchCompletedMsg` is moved from `RunDashboardView` to `ColdwineView` (different
context — the run may not be `v.activeRun`, it may be in `v.epicRuns`).

**Fix:** Add a `coldwine_mode_test.go` to Task 2 covering at minimum:

- `TestColdwineView_ModeSwitchKeybinding` — send `tea.KeyMsg("m")` in
  `FocusDocument`, assert `RunsLoadedMsg` is requested (check returned `tea.Cmd` is
  non-nil)
- `TestColdwineView_SidebarSelectMsg_SentinelModeEpics` — verify no epic selection
  side-effect on sentinel IDs
- `TestColdwineView_DispatchCompletedMsg_RunsMode` — the `DispatchCompletedMsg` handler
  that moves from RunDashboardView should have coverage; in ColdwineView it correlates
  with `v.epicRuns` not `v.activeRun`

---

### F10 — `loadDetail` errors are silently swallowed in `RunDashboardView`

**Severity: Low (pre-existing, surfaces in extraction)**

In `run_dashboard.go` line 350:

```go
run, _ := v.iclient.RunStatus(ctx, runID)
dispatches, _ := v.iclient.DispatchList(ctx, false)
budget, _ := v.iclient.RunBudget(ctx, runID)
events, _ := v.iclient.RunEvents(ctx, runID)
gate, _ := v.iclient.GateCheck(ctx, runID)
```

All five errors are discarded. This is an existing issue, but Task 1 extracts this
logic into `LoadRunDetail` in `pkg/tui` — a shared, reusable function. Promoting silent
error swallowing into a shared package hardens this pattern across future consumers.

**Fix:** In `LoadRunDetail` (Task 1.2), collect partial errors into the
`RunDetailLoadedMsg`:

```go
type RunDetailLoadedMsg struct {
    Run        *intercore.Run
    Dispatches []intercore.Dispatch
    Budget     *intercore.BudgetResult
    Events     []intercore.Event
    Gate       *intercore.GateResult
    Err        error // non-nil if any fetch failed; partial data may still be present
}
```

Callers can log or display `Err` without blocking the render (since partial data is
still useful in the TUI). This matches the pattern used by `runDashRunsLoadedMsg` which
already carries `err`.

---

### F11 — `renderSprintPanelForEpic` writes to `v.runDetail` inside `View()`

**Severity: High**

Task 4.2:

```go
func (v *ColdwineView) renderSprintPanelForEpic() string {
    if v.runDetail == nil {
        v.runDetail = pkgtui.NewRunDetailPanel()  // write inside View()
    }
    v.runDetail.SetData(run, nil, nil, nil, nil)  // write inside View()
    return v.runDetail.View()
}
```

`View()` is called by Bubble Tea to produce the rendered string. Writing to struct
fields inside `View()` violates the Bubble Tea threading model documented in
`apps/autarch/CLAUDE.md`: "In parent `Update()` methods, never swallow messages that
child views need." More directly, the Bubble Tea contract treats `View()` as a pure
render function. Mutating `v.runDetail` inside `View()` can cause subtle rendering
artifacts when Bubble Tea batches updates.

`v.runDetail` initialization belongs in `Update()` — either lazily in the message
handler for `RunDetailLoadedMsg` or eagerly in `NewColdwineView()`. The `SetData` call
belongs in the `RunDetailLoadedMsg` handler, not in `View()`.

**Fix:** Initialize `v.runDetail = pkgtui.NewRunDetailPanel()` in `NewColdwineView()`.
Call `v.runDetail.SetData(...)` only in `Update()` handlers. `renderSprintPanelForEpic`
becomes a pure reader:

```go
func (v *ColdwineView) renderSprintPanelForEpic() string {
    if v.selected < 0 || v.selected >= len(v.epics) {
        return "  No epic selected"
    }
    epic := v.epics[v.selected]
    run, ok := v.epicRuns[epic.ID]
    if !ok || run == nil {
        return "  No sprint for this epic"
    }
    return v.runDetail.Render()
}
```

---

### F12 — `ShouldAutoAdvance` extraction omits the `tryAutoAdvance` function

**Severity: Low**

Task 1.2 proposes extracting `ShouldAutoAdvance` as a package-level function in
`pkg/tui/run_actions.go`. The current `RunDashboardView.shouldAutoAdvance` at line 419
is simple and pure — a good extraction candidate. However, `tryAutoAdvance` (line 428)
is tightly coupled to `RunDashboardView` via `v.iclient`, `v.activeRun`, and it
produces a `runDashAdvancedMsg` (a `views`-internal message type).

The plan does not say what happens to `tryAutoAdvance` after Task 6 deletes
`RunDashboardView`. If it stays in `views` as a method on `ColdwineView`, the caller
needs to produce a message — but the message type changes from `runDashAdvancedMsg` to
whatever `ColdwineView` uses for its advance result. This is a gap in Task 6's deletion
checklist.

**Fix:** Add to Task 6's checklist: "Port `tryAutoAdvance` to `ColdwineView` producing
the Coldwine-local advance message type. `ShouldAutoAdvance` stays as a pure helper in
`pkg/tui`."

---

## Approved Patterns (No Change Needed)

- Interface escape for circular import (`modeSettable`) — matches existing
  `specHandoffReceiver` pattern, correct choice.
- Width-based degradation for split pane at <120 columns — the threshold is
  reasonable and the auto-fallback pattern is clean.
- `orphanRuns` computed after `epicRunsLoadedMsg` — the deferred computation is the
  right approach; avoids re-fetching.
- Sequential task order (F1 → F2 → F6 critical path) — correct.
- Keeping `RenderRunStatusBadge` and `FormatTokens` as package-level functions — they
  have no state dependency, correct extraction target.

---

## Priority Order for Fixes

| # | Finding | Fix cost |
|---|---------|----------|
| F1 | `View()` name collision on `RunDetailPanel` | 5 min rename |
| F11 | Struct mutation inside `View()` | 15 min refactor |
| F7 | Race in command palette `Action` closures | 10 min message pattern |
| F8 | Task ordering: `layoutMode` used before defined | Reorder tasks |
| F4 | Nil data contract not specified for `RunDetailPanel` | Add one sentence to Task 1 |
| F2 | Dual exported API for mode setting | Drop one, keep the other |
| F3 | Per-frame allocation in `renderDocument` | Reuse cached `v.runDetail` |
| F5 | Stale `epicRuns` in orphan detection | Chain `loadEpicRuns()` from `loadRunsForMode` |
| F9 | No tests for mode switching | Add `coldwine_mode_test.go` |
| F10 | Silent error swallowing promoted to shared pkg | Add `Err` field to `RunDetailLoadedMsg` |
| F12 | `tryAutoAdvance` missing from Task 6 deletion checklist | One line in checklist |
| F6 | Sentinel ID fragility | Document `__` convention |
