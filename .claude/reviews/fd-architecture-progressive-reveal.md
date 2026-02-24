# Architecture Review: Pollard Progressive Result Reveal
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-pollard-progressive-reveal.md`
**Date:** 2026-02-23
**Reviewer:** fd-architecture

---

## Executive Summary

The plan correctly identifies the integration goal — wiring the Coordinator into PollardView for progressive display — but introduces three structural problems that will produce silent runtime failures and state incoherence before the first line of feature logic runs. The core issues are: (1) the Coordinator's message delivery mechanism is never activated in this plan, making all message-based progressive reveal inert; (2) PollardView duplicates status tracking that ResearchOverlay already owns, creating two divergent state machines reading the same event stream; (3) the shared Coordinator instance creates a cross-view interference problem that is not acknowledged or mitigated.

---

## 1. Boundaries and Coupling

### 1.1. Must-Fix: Coordinator.SetProgram Is Never Called — All Messages Are Silent

**Severity: Blocker**

The Coordinator delivers messages by calling `p.Send(msg)` via its `sendMsg` method:

```go
// apps/autarch/internal/pollard/research/coordinator.go:390-396
func (c *Coordinator) sendMsg(msg tea.Msg) {
    c.mu.RLock()
    p := c.program
    c.mu.RUnlock()

    if p != nil {
        p.Send(msg)
    }
}
```

If `c.program` is nil, `sendMsg` is a no-op. The Coordinator's `program` field is set only via `SetProgram(*tea.Program)`. Searching the entire codebase, `coordinator.SetProgram` is called nowhere — not in `main.go`, not in `unified_app.go`, not in any view factory. The existing `GurgehOnboardingView` uses the coordinator only to call `GetActiveRun()` and `GetHunterStatuses()` (polling on refresh, not message-driven).

The plan's Task 2 adds `case research.HunterStartedMsg:`, Task 3 adds `case research.RunStartedMsg:`, and so on — but these cases will never fire because the Coordinator's `program` is nil and `p.Send()` is never invoked. The feature compiles cleanly and appears to work structurally, while silently doing nothing.

**The plan also does not show how `StartRun` is triggered in the production flow.** Task 5 wires a "Run Research" command, but that command calls `StartRun` which itself tries to send `RunStartedMsg` via `sendMsg` — which is still a no-op because `SetProgram` was never called.

**Fix required:** `SetProgram` must be called with the `*tea.Program` after the program is created. The correct location is in the `Run` function in `unified_app.go` alongside the existing `handler.SetProgram(p)` call at line 993. Both the GurgehConfig's coordinator and any coordinator passed to PollardView must have `SetProgram` called before `p.Run()`. Since the plan already proposes sharing a single coordinator instance, this is a single call:

```go
// apps/autarch/internal/tui/unified_app.go (Run function, after line 993)
p := tea.NewProgram(app, progOpts...)
handler.SetProgram(p)
// If the app holds a reference to the coordinator:
if app.researchCoord != nil {
    app.researchCoord.SetProgram(p)
}
_, err := p.Run()
```

This requires the `UnifiedApp` to hold a reference to the coordinator, or the coordinator must be passed alongside the `GurgehConfig` into the wiring layer. The plan skips this entirely.

---

### 1.2. Must-Fix: Dual State Machines for the Same Event Stream

**Severity: Blocker**

The plan proposes that `PollardView` maintain its own `hunterStatuses map[string]research.HunterStatus` (Task 1, Task 2) and build its own status-to-badge rendering (Task 3, `hunterStatusIcon`). `ResearchOverlay` already owns identical state:

```go
// apps/autarch/internal/tui/views/research_overlay.go:32-34
hunterStatuses map[string]research.HunterStatus
findings       []research.Finding
filteredIdx    []int
```

`ResearchOverlay` is initialized by the plan with `NewResearchOverlay(coordinator)` and stored as `PollardView.researchOverlay`. The plan also puts `PollardView.researchOverlay` in the struct but never calls `v.researchOverlay.Update(msg)` in the Update method. So there are now two independent trackers:

- `PollardView.hunterStatuses` — updated by the message cases the plan adds (Task 2)
- `PollardView.researchOverlay.hunterStatuses` — updated by `loadFromCoordinator()` when the overlay's `Update` is called

The overlay's `Update` only processes messages when `o.visible == true` (line 109: `if !o.visible { return o, nil }`). If the overlay is not visible (default), its `hunterStatuses` will be stale. The sidebar badges will show PollardView's inline state, but when the user opens the overlay, it will show the overlay's independently loaded state — potentially inconsistent.

More critically: `ResearchOverlay.loadFromCoordinator()` discards both maps and rebuilds from scratch by calling `run.GetHunterStatuses()` and `run.GetAllUpdates()`. PollardView's message-driven accumulation into `v.hunterStatuses` does incremental updates. Two separate paths, same data, different strategies, inevitable divergence.

**The correct design is one of these two approaches — not both:**

**Option A (preferred): Remove PollardView's inline status tracking. Delegate entirely to ResearchOverlay.**

PollardView should call `v.researchOverlay.Update(msg)` for all research messages, and read status from the overlay rather than from a parallel map. The sidebar badge rendering can call `v.researchOverlay.GetHunterStatuses()` (add that getter if absent) rather than maintaining `v.hunterStatuses`. This keeps ResearchOverlay as the single authority for run state.

**Option B: Remove ResearchOverlay from PollardView entirely.**

If PollardView wants to be the primary consumer of research state and render it directly, do not create a `ResearchOverlay` inside it. PollardView owns state, ResearchOverlay is not used in Pollard's tab. This removes the hidden split but loses the richer overlay UI if that is intended.

The plan as written creates Option C — both tracking paths active simultaneously — which should be rejected.

---

### 1.3. Must-Fix: ResearchOverlay Instantiated but Never Routed Messages

**Severity: Blocker**

The plan creates a `ResearchOverlay` and stores it in `PollardView.researchOverlay` (Task 1):

```go
researchOverlay: NewResearchOverlay(coordinator),
```

But in Task 2's `Update` method, the plan handles research messages directly in `PollardView.Update` and returns early from each case (`return v, nil`). The overlay's `Update` is never called for any research message. The overlay is instantiated but receives no messages, maintains no live state, and its `View()` is never called from `PollardView.View()`.

Either the overlay is intended as the rendering component (in which case messages must be forwarded to it and its `View()` output composited into the layout), or it should not be allocated at all in PollardView.

---

### 1.4. Must-Fix: Cross-View Coordinator Interference

**Severity: High**

The plan proposes sharing one coordinator instance between GurgehConfig and PollardView:

```go
researchCoord := research.NewCoordinator(nil)
// ... gurgehCfg uses researchCoord ...
views.NewPollardView(c, researchCoord),
```

`Coordinator.StartRun` cancels any active run when a new one is started:

```go
// coordinator.go:67-73
if c.activeRun != nil {
    c.activeRun.Cancel()
    c.sendMsg(RunCancelledMsg{...})
}
```

This means: if Gurgeh initiates a research run during onboarding (e.g., for spec summary), and the user navigates to the Pollard tab and triggers "Run Research", the Gurgeh run is silently cancelled. The cancellation message is sent to the TUI, but both the GurgehOnboarding view and PollardView will receive `RunCancelledMsg` — neither currently handles it.

The symmetrical case: a Pollard research run in progress is killed when Gurgeh's onboarding transitions into a spec summary step and calls `StartRun`.

The Coordinator's comment acknowledges this is intentional for project-switching (the field comment: "ensures only one run is active per project"), but the documented use case is same-view navigation, not cross-tab interference.

**Minimum viable fix:** Give PollardView its own coordinator instance rather than sharing Gurgeh's. The coordinator is cheap to construct (`research.NewCoordinator(nil)` allocates a registry and that's all). There is no shared state or benefit from sharing across unrelated views. The plan's rationale for sharing is not stated; the comment "Extract researchCoord to a local variable so both GurgehConfig and PollardView share the same instance" gives no justification.

```go
// main.go — separate coordinators
gurgehCfg := &tui.GurgehConfig{
    ResearchCoord: research.NewCoordinator(nil),
    ...
}
pollardCoord := research.NewCoordinator(nil)
// both get SetProgram called on them after p := tea.NewProgram(...)
views.NewPollardView(c, pollardCoord),
```

---

## 2. Pattern Analysis

### 2.1. Message Handling Pattern Mismatch

The existing Bubble Tea update pattern in this codebase uses short-circuit returns: `if _, isKey := msg.(tea.KeyMsg); !isKey { v.chatPanel, cmd = v.chatPanel.Update(msg) }`. This means non-key messages are passed to the chat panel first, and if it returns a command, the parent returns early. The plan's research message cases sit after this block, which is correct structurally. However, the plan's cases return `v, nil` unconditionally, never forwarding to the overlay or chat panel. If the overlay is retained, research messages must be forwarded to it before (or instead of) the parent handling them directly.

The Autarch CLAUDE.md documents this explicitly: "In parent Update() methods, never swallow messages that child views need. Default to fall-through."

Every `return v, nil` at the end of a research message case violates this rule if `researchOverlay` is in scope and needs those messages.

### 2.2. Inconsistent Icon Sets

Task 3 introduces a `hunterStatusIcon` function in `pollard.go` that is a verbatim copy of the icon logic in `research_overlay.go:renderHunterStatus`. The overlay uses lipgloss `Style.Render` with `ColorWarning`/`ColorSuccess`/`ColorError` colors; the plan's sidebar implementation returns bare Unicode strings without styling. This is the same function, duplicated, stripped of styling. Single enforcement point violation.

If the overlay is removed from PollardView (Option B above), `hunterStatusIcon` stays only in `pollard.go`. If the overlay is retained as the canonical renderer (Option A), `hunterStatusIcon` should not exist in `pollard.go` at all.

### 2.3. The addFinding Method Performs a Slice-level Sort Insert on Every Finding

Task 2 proposes:

```go
func (v *PollardView) addFinding(f research.Finding, hunterName string) {
    idx := sort.Search(len(v.insights), func(i int) bool {
        return v.insights[i].Score < insight.Score
    })
    v.insights = append(v.insights, autarch.Insight{})
    copy(v.insights[idx+1:], v.insights[idx:])
    v.insights[idx] = insight
}
```

The binary search finds the first element strictly less-than the new score, then shifts the slice. This is correct but O(n) per insert due to the `copy`. For a typical research run producing tens of findings this is not a correctness problem, but it is accidental complexity — `RunCompletedMsg` already triggers `v.loadInsights()` which reloads from Intermute sorted server-side. The progressive-insert sorted list is discarded and replaced on completion. The sort-insert is speculative complexity for a transient display state.

The simpler approach: `v.insights = append(v.insights, insight)` during the run, then `sort.Slice` once on `RunCompletedMsg` or rely on the `loadInsights` reload. Binary-insert-per-finding is premature.

---

## 3. Simplicity and YAGNI

### 3.1. hunterStatuses In PollardView Is Redundant Given ResearchOverlay

The plan adds `hunterStatuses map[string]research.HunterStatus` and `runActive bool` to `PollardView` alongside the `researchOverlay *ResearchOverlay` that holds the same data. If the overlay is the canonical state holder, these fields are redundant. If the plan's intent is to always show live badges in the sidebar regardless of overlay visibility, then `runActive` and `hunterStatuses` are needed — but the overlay should still be the source of truth they read from, not a parallel accumulator.

The minimum surface that achieves the stated goal (sidebar badges + progressive document pane) requires:
- One tracking location (overlay or view, not both)
- One rendering path for status icons

The plan's five tasks add ~200 lines to `pollard.go` that overlap with ~260 lines already in `research_overlay.go`. This is a net addition of complexity, not an integration of an existing component.

### 3.2. Hardcoded Hunter Names in Run Research Command

Task 5 hardcodes hunter names in the command action:

```go
hunterNames := []string{"competitor-tracker", "hackernews-trendwatcher", "github-scout"}
```

These names must match registered hunter names in the registry. The registry is initialized with `hunters.DefaultRegistry()` inside `NewCoordinator`. If any of these names is misspelled or not registered, `executeRun` silently sends `HunterErrorMsg` and continues. There is no validation at construction time. This is a test-failure waiting to happen and a confusing user experience (run starts, no results, no clear error in the UI). The correct approach is to query `coordinator.registry.List()` at command time and use only registered names, or expose a `DefaultHunterNames()` function from the registry.

### 3.3. nil Coordinator Guard Duplicated Across Every Message Case

The plan has `if v.coordinator == nil { return nil }` in the Run Research command action, but the message cases in Task 2 do not guard against nil coordinator. They guard against missing keys in `v.hunterStatuses` (`if hs, ok := v.hunterStatuses[msg.HunterName]; ok`), which is correct. However if coordinator is nil and someone externally sends a `RunStartedMsg` through the program (edge case but possible in tests), `v.hunterStatuses` is also nil at that point — `make` in the `RunStartedMsg` case resolves this, but the test in Task 6 creates the view with `nil` coordinator and then sends `RunStartedMsg` directly. That test bypasses coordinator entirely, which is valid for unit testing, but the production guard is inconsistent.

---

## 4. Ordered Findings

| # | Severity | Finding |
|---|----------|---------|
| 1 | Blocker | `Coordinator.SetProgram` never called — all message delivery is a no-op; progressive reveal silently does nothing |
| 2 | Blocker | `PollardView.hunterStatuses` and `PollardView.researchOverlay.hunterStatuses` are parallel state machines receiving the same events; divergence is guaranteed |
| 3 | Blocker | `PollardView.researchOverlay` is allocated but receives no messages and its `View()` is never called; the field is dead weight |
| 4 | High | Shared coordinator between GurgehConfig and PollardView causes `StartRun` to cancel the sibling's active run across tab switches |
| 5 | High | Research message cases call `return v, nil` — violates the Autarch Bubble Tea rule "never swallow messages child views need" |
| 6 | Medium | `hunterStatusIcon` function is a duplicated copy of `ResearchOverlay.renderHunterStatus` logic without styling |
| 7 | Medium | Hardcoded hunter names in `StartRun` call will silently error for any unregistered name |
| 8 | Low | Binary-insert sort per finding is O(n) per call; results are discarded at `RunCompletedMsg`; `append` + deferred sort is sufficient |

---

## 5. Minimum Viable Fix Path

**Before implementing any task in the plan:**

1. Decide on the single tracking authority: is `ResearchOverlay` the state owner for PollardView, or is PollardView standalone? The existing `ResearchOverlay` code is more complete (search, expand, scroll, styling). Use it.

2. Remove `hunterStatuses map[string]research.HunterStatus` and `runActive bool` from PollardView. Forward all research messages to `v.researchOverlay.Update(msg)`. Read state from the overlay for sidebar rendering.

3. Give PollardView its own coordinator: `pollardCoord := research.NewCoordinator(nil)` in `main.go`. Do not share with GurgehConfig.

4. Wire `coordinator.SetProgram(p)` for both coordinators in the `Run` function in `unified_app.go` after `p := tea.NewProgram(...)`. This requires either passing coordinators to the app struct or calling it from `main.go` before `tui.Run`. The cleanest path is to add a `SetResearchCoord` method to `UnifiedApp` and call `coord.SetProgram(p)` inside `Run` before `p.Run()`.

5. After the above is in place, Tasks 2-5 of the plan become simpler: most of the inline status-tracking code is removed, replaced by delegating to the overlay's existing `Update` and reading from it in the sidebar renderer.

The plan's Task 6 tests are structurally sound and worth keeping, but `TestPollardView_RunStartedMsg` will need updating to match the revised struct (no `hunterStatuses` field if the overlay owns that state).
