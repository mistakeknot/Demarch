# Correctness Review: Merge Sprint Tab into Coldwine

**Plan:** `apps/autarch/docs/plans/2026-02-25-merge-sprint-into-coldwine.md`
**Reviewer:** Julik (flux-drive Correctness Reviewer)
**Date:** 2026-02-25
**Bead:** iv-oguc3

---

## Invariants Under Review

Before scanning for violations, I write down the invariants that must hold after the merge.

1. **Bubble Tea goroutine model**: `Update()` and `View()` are always called on the same goroutine. `tea.Cmd` closures run on the runtime goroutine pool. Model fields must never be read inside a closure without snapshotting them first on the Update goroutine.
2. **DispatchCompletedMsg fan-out**: `UnifiedApp.Update()` delivers every `DispatchCompletedMsg` to ALL `dashViews`, not just the active tab. This must continue to work correctly after ColdwineView absorbs the RunDashboard behaviour.
3. **Auto-advance atomicity**: The check `shouldAutoAdvance` reads `v.activeRun` state captured at message delivery time. The goroutine that executes `tryAutoAdvance` captures `runID` and `phase` before launch. These snapshots must not diverge.
4. **Mode state as a gate**: Operations specific to Runs mode (auto-advance, cancel, advance phase) must not execute side effects when `v.mode == ModeEpics`.
5. **Selected-index validity**: `selectedRun` and `selected` (epic) must always be in bounds for their respective slices when used to dereference. Any async load that replaces a slice must reset or clamp the cursor.
6. **Orphan-run detection consistency**: `computeOrphanRuns` reads both `v.runs` and `v.epicRuns`. Both are populated by separate async loads. Reading both without a common synchronisation point can yield a stale cross-product.
7. **`runDetail` panel mutation inside View()**: `View()` is pure in the Bubble Tea model; mutating `v.runDetail` inside `View()` is legal only because Update/View are on the same goroutine, but it still creates ordering hazards if the same panel pointer is shared across layout modes.
8. **Slash-command `/sprint` mode-set before tab switch**: `SetRunsMode()` must execute on the Update goroutine before `Focus()` is called, otherwise the freshly focused view renders in the wrong mode for one frame and may fire an incorrect load.

---

## Findings

### CRITICAL — C1: `DispatchCompletedMsg` Auto-Advance Fires in Epics Mode

**Severity:** High — incorrect Intercore mutations driven by ambient events.

**Location:** Plan Task 2.5, "Move DispatchCompletedMsg auto-advance logic from RunDashboardView into ColdwineView's Runs mode handler."

The plan says gate auto-advance on `v.mode == ModeRuns`, but this is stated only in the risk table as a mitigation. The concrete `Update()` code sketch (Task 2.5) does not show the guard. The existing `RunDashboardView.Update()` (run_dashboard.go:191-200) has no mode concept; it acts whenever `v.activeRun != nil && msg.Dispatch.RunID == v.activeRun.ID`.

`DispatchCompletedMsg` is broadcast to ALL views by `UnifiedApp`. After the merge, ColdwineView will receive every dispatch completion regardless of which tab is active or which mode ColdwineView is in. If the user is browsing epics (ModeEpics), a dispatch completion will still trigger `tryAutoAdvance()` — issuing a gate check and potentially a `RunAdvance` call to Intercore — with no visual feedback to the user.

**Failure narrative:**

1. User is on Coldwine tab, ModeEpics, reading an epic.
2. An agent dispatch for a background run completes.
3. `UnifiedApp` fans out `DispatchCompletedMsg` to all views including the merged ColdwineView.
4. `Update()` matches `v.activeRun.ID == msg.Dispatch.RunID`, calls `tryAutoAdvance()`.
5. Gate passes; `RunAdvance` is called. Phase changes in Intercore.
6. User did not see this happen. Next time they switch to Runs mode, the run has advanced silently.

The silent mutation is the problem. Auto-advance from an invisible background tab is expected. Auto-advance while on the same tab in the wrong sub-mode is confusing, but more importantly the `statusMsg` written in `Update()` is silently lost if the mode-specific rendering does not display it.

**Fix:** In the `DispatchCompletedMsg` handler that calls `v.tryAutoAdvance()`, also persist the `statusMsg` independently of mode. For the auto-advance call itself, make no change — the server enforces gate conditions so the call is safe. The real bug is that `statusMsg` set during Epics mode is swallowed by the mode-specific `View()` switch. Ensure `statusMsg` is rendered in both modes, or suppress the auto-advance status message when mode is Epics.

---

### CRITICAL — C2: `v.runs` and `v.activeRun` Are Two Different Things That Can Diverge After Mode Switch

**Severity:** High — stale pointer leads to advance/cancel operating on wrong run.

**Location:** Plan Task 2.1 struct additions; Task 2.2 `handleRunsKey`.

The existing `RunDashboardView` keeps a single `activeRun *intercore.Run` that is set when `runDashDetailLoadedMsg` arrives. The plan proposes adding `runs []intercore.Run` and `selectedRun int` to ColdwineView. The `activeRun` pointer comes from a separate `loadDetail` call.

The mode-switching path is:

```
user presses "m"
→ v.switchMode()
→ v.mode = ModeRuns
→ return v, v.loadRunsForMode()      // tea.Cmd launched
// ... frames pass ...
→ RunsLoadedMsg arrives, v.runs = msg.Runs, v.selectedRun = 0
→ return v, v.loadDetail(v.runs[0].ID)  // second tea.Cmd launched
// ... more frames pass ...
→ RunDetailLoadedMsg arrives, v.activeRun = msg.run
```

During the gap between `RunsLoadedMsg` and `RunDetailLoadedMsg`, `v.runs` is populated but `v.activeRun` is nil (or stale from a previous run). If the user presses `a` (advance) during this window:

```
v.advancePhase() checks v.activeRun == nil → returns nil (safe)
```

That is fine. But the inverse failure is worse. Suppose the user:

1. Enters ModeRuns. `v.runs[0]` is Run A. Detail loads. `v.activeRun = &RunA`.
2. User navigates to `v.runs[1]` (Run B). `loadDetail(RunB)` is launched.
3. Before `RunDetailLoadedMsg` for Run B arrives, user presses `a`.
4. `v.advancePhase()` reads `v.activeRun` — still `&RunA`.
5. `RunAdvance` is called for Run A, not the visually selected Run B.

**Failure narrative:**

Event sequence:
- T1: `v.selectedRun = 1` (Run B selected visually)
- T1: `loadDetail(RunB)` goroutine launched
- T2: user presses `a` — advance fired for `v.activeRun` (still Run A)
- T3: RunDetailLoadedMsg for Run B arrives, `v.activeRun = &RunB`
- Result: Run A was advanced; user thought they advanced Run B.

This is an exact TOCTOU between visual selection and loaded detail pointer.

**Fix:** Derive the target run ID directly from `v.runs[v.selectedRun].ID` in `advancePhase`/`cancelRun`, not from `v.activeRun`. Optionally disable `a`/`c` with a "loading" indicator while detail is in flight (set `v.detailLoading = true` on key press, cleared by `RunDetailLoadedMsg`).

---

### CRITICAL — C3: `computeOrphanRuns` Races Two Independently Loaded Maps

**Severity:** Medium-high — produces incorrect orphan set, can show runs that belong to epics as "Unscoped."

**Location:** Plan Task 5.1.

```go
func (v *ColdwineView) computeOrphanRuns() {
    associated := make(map[string]bool)
    for _, run := range v.epicRuns {      // v.epicRuns loaded by loadEpicRuns()
        if run != nil {
            associated[run.ID] = true
        }
    }
    for _, r := range v.runs {            // v.runs loaded by loadRunsForMode()
        if !associated[r.ID] {
            v.orphanRuns = append(v.orphanRuns, r)
        }
    }
}
```

`v.epicRuns` is populated by `epicRunsLoadedMsg` (triggered after `epicsLoadedMsg`). `v.runs` is populated by `RunsLoadedMsg` (triggered when entering Runs mode). These arrive independently and in non-deterministic order.

**Concrete bad interleaving:**

1. User opens Coldwine tab. `loadEpicRuns()` is in flight.
2. User immediately presses `m` to switch to Runs mode. `loadRunsForMode()` is also in flight now.
3. `RunsLoadedMsg` arrives first. `v.runs` = [RunA, RunB]. `computeOrphanRuns()` runs with `v.epicRuns == nil`. Both RunA and RunB are marked orphan.
4. `epicRunsLoadedMsg` arrives. `v.epicRuns = {epic1: &RunA}`. But `computeOrphanRuns` is not re-invoked. RunA stays in `v.orphanRuns`.
5. User sees RunA under "Unscoped" even though it is correctly scoped to epic1.

**Fix:** Call `computeOrphanRuns()` from both `epicRunsLoadedMsg` handler and `RunsLoadedMsg` handler (whenever either input changes). Add an explicit check: only compute if both `v.runs != nil` and `v.epicRuns != nil`. Also note `computeOrphanRuns` must nil-check its own inputs at the top.

---

### HIGH — H1: `renderSprintPanelForEpic()` Mutates `v.runDetail` Inside `View()`

**Severity:** High — violates the principle that `View()` is read-only; creates ordering hazard between modes.

**Location:** Plan Task 4.2.

```go
func (v *ColdwineView) renderSprintPanelForEpic() string {
    // ...
    if v.runDetail == nil {
        v.runDetail = pkgtui.NewRunDetailPanel()   // mutation in View()
    }
    v.runDetail.SetData(run, nil, nil, nil, nil)   // mutation in View()
    return v.runDetail.View()
}
```

`v.runDetail` is also the panel used by Runs mode (`runsModeDocument`). If the user is in Runs mode with fully loaded detail data, then switches to Epics + Split layout, `renderSprintPanelForEpic()` calls `v.runDetail.SetData(run, nil, nil, nil, nil)` — overwriting the Runs mode data with partial data (nil dispatches, nil budget, nil events, nil gate).

The panel is now corrupted for any subsequent frame that switches back to Runs mode. The next `View()` call in Runs mode will render the partial data until a new `RunDetailLoadedMsg` arrives.

The CLAUDE.md Bubble Tea rule is "Update/View are on the same goroutine — shared pointer fields are safe without mutexes." This is true for data races in the Go memory model sense, but the plan creates a logical state corruption across mode switches.

**Fix:** Use two separate `RunDetailPanel` instances: `v.epicsRunDetail` (for inline/split Epics mode) and `v.runsRunDetail` (for Runs mode). Never share a single panel across modes. Or: do not call `SetData` in `View()`. Instead, set data in `Update()` when `epicRunsLoadedMsg` arrives (already available — `v.epicRuns[selectedEpic.ID]`).

---

### HIGH — H2: Index Bounds Risk When `v.epics` is Replaced While `v.selected` Retains Old Value

**Severity:** High — panic or silently wrong epic displayed.

**Location:** Plan Task 2.1, implicitly; existing `ColdwineView` has this partially mitigated in `renderDocument()` (line 574) but the new mode logic adds more dereference points.

When `loadData()` completes (e.g., on ctrl+r refresh or after sprint creation), `v.epics` is replaced with a new slice. If the new slice is shorter than the old one, `v.selected` can be out of bounds. The existing `renderDocument()` has a bounds check at line 574. However the plan adds new dereference points in:

- `runsModeSidebarItems()` — iterates using epic selection to show "current epic's run"
- `renderSprintPanelForEpic()` — dereferences `v.epics[v.selected]`
- The `s` key handler in Task 3.3 — dereferences `v.epics[v.selected]` without a bounds check

The plan does not specify that these new functions inherit the bounds check. Pattern from existing code (coldwine.go:574-577) should be replicated in every new function that dereferences `v.epics[v.selected]`:

```go
if v.selected >= len(v.epics) {
    // handle gracefully
}
```

**Fix:** Each new function that dereferences `v.epics[v.selected]` must start with a bounds check. More robustly: clamp `v.selected` to `max(0, len(v.epics)-1)` in the `epicsLoadedMsg` handler when the slice shrinks.

---

### HIGH — H3: `SetRunsMode()` Called from `unified_app.go` Before `Focus()` — One-Frame Mode Inconsistency

**Severity:** Medium-high — incorrect initial load triggered, or load not triggered at all.

**Location:** Plan Task 6.3 and 6.7.

The plan routes `/sprint` slash command as:

```go
case "sprint", "spr":
    if modeView, ok := a.dashViews[2].(interface{ SetRunsMode() }); ok {
        modeView.SetRunsMode()
    }
    return a, a.switchToTab(2)
```

`switchToTab` calls `switchDashboardTab` which calls `a.currentView.Focus()` — which in turn calls `v.loadData()` (existing ColdwineView.Focus). That is the `epicsLoadedMsg` trigger. After that, `loadRunsForMode()` must be triggered separately.

The problem: `SetRunsMode()` sets `v.mode = ModeRuns` synchronously on the Update goroutine. But `loadRunsForMode()` is NOT triggered here — it must be triggered either from `SetRunsMode` itself or from `Focus()`. The plan's `SetRunsMode` implementation (Task 6.7) is:

```go
func (v *ColdwineView) SetRunsMode() {
    v.mode = ModeRuns
}
```

No `loadRunsForMode()` is issued. The view will render ModeRuns immediately but with `v.runs == nil` until the user triggers a load manually.

If instead `SetRunsMode` returns a `tea.Cmd` (changing its signature from the plan's interface), then `unified_app.go` needs to handle the returned cmd. The plan uses a void method to avoid this, which is the correct pattern for cross-package interface dispatch, but leaves the view in a "mode set, data not loaded" state.

**Failure narrative:**

1. User types `/sprint` in chat.
2. `SetRunsMode()` sets `v.mode = ModeRuns`. No load issued.
3. `switchToTab(2)` calls `Focus()` → `loadData()` → epics data path.
4. ColdwineView renders ModeRuns with `v.runs == nil`. Document shows "No sprints" or panics on nil dereference.
5. User must press ctrl+r or `m` twice to get data loaded.

**Fix:** `Focus()` in ColdwineView should check `if v.mode == ModeRuns { return tea.Batch(epicsLoad, v.loadRunsForMode()) }`. This means `Focus()` is mode-aware. Alternatively, after calling `SetRunsMode()`, explicitly issue `loadRunsForMode()` as a tea.Cmd that `unified_app.go` handles — but this requires the interface to return `tea.Cmd`, breaking the void interface design. The `Focus()` approach is cleaner and consistent with how RunDashboardView.Focus() works (it calls `loadRuns()` directly).

---

### MEDIUM — M1: `tryAutoAdvance` Captures Stale `phase` At Closure Creation Time

**Severity:** Medium — misleading gate failure message; no data corruption.

**Location:** `run_dashboard.go:428-455` (to be ported to ColdwineView).

```go
func (v *RunDashboardView) tryAutoAdvance() tea.Cmd {
    runID := v.activeRun.ID
    phase := v.activeRun.Phase    // captured NOW
    ic := v.iclient
    return func() tea.Msg {
        gate, err := ic.GateCheck(ctx, runID)
        // ...
        return runDashAdvancedMsg{
            result: &intercore.AdvanceResult{
                FromPhase:  phase,    // this is the phase at closure-creation time
                // ...
            },
        }
    }
}
```

If the run advances (by another path) between `tryAutoAdvance()` being created and the gate check completing, the synthesized `AdvanceResult.FromPhase` is wrong. This is a display-only issue — the server returns the correct result on success — but the synthetic failure message `"auto-advance: gate not ready"` uses the stale phase, which can confuse diagnostics.

This is existing behaviour inherited from `run_dashboard.go`. The merge does not make it worse. Flagging it here so it is not accidentally made worse during the port.

**Fix during port:** Remove the `phase` capture from the closure. Use the `result.FromPhase` from the actual `RunAdvance` response, which already carries the correct phase. On gate-blocked synthetic return, omit `FromPhase` or fetch a fresh `RunStatus` for the phase.

---

### MEDIUM — M2: `loadRunsForMode` Triggered Twice on Rapid Mode Toggle

**Severity:** Medium — double API calls, potential for interleaved `RunsLoadedMsg` to overwrite newer data with older data.

**Location:** Task 2.5, `m` key handler and `SidebarSelectMsg` handler both call `loadRunsForMode()`.

If the user presses `m` twice quickly (toggle to Runs and back to Epics and back to Runs), two `loadRunsForMode()` closures are in flight. Both return `RunsLoadedMsg`. The second response to arrive overwrites `v.runs` with potentially stale data.

Additionally, `SidebarSelectMsg` for `__mode_runs` also calls `loadRunsForMode()`. If the user clicks the sidebar item while the `m` key response is still in flight, a third request is in flight.

Bubble Tea makes this safe from data-race perspective (all handled on one goroutine). But the last-writer-wins overwrite can leave `v.selectedRun` pointing at a stale index for the newer slice.

**Fix:** Add a `runsLoadSeq uint64` counter incremented each time a load is launched. `RunsLoadedMsg` carries the sequence number. The handler ignores messages with `msg.seq < v.runsLoadSeq`. This is the standard generation-counter pattern for Bubble Tea async loads. It is already implicitly used in Pollard (RunID check) per the MEMORY.md note.

---

### MEDIUM — M3: Inline Expansion Creates a New `RunDetailPanel` on Every `View()` Call

**Severity:** Medium — O(n) allocations per render frame when inline-expanded.

**Location:** Task 3.2.

```go
if v.sprintExpanded {
    compact := pkgtui.NewRunDetailPanel()   // new allocation every frame
    compact.SetData(run, nil, nil, nil, nil)
    compact.SetMaxEvents(3)
    compact.SetSize(v.width-4, 12)
    lines = append(lines, compact.CompactView())
}
```

`View()` is called on every frame (key press, window resize, tick). Allocating a new `RunDetailPanel` every call is wasteful and, more importantly, the panel is stateless (no MaxEvents persistence, no width persistence) — it will be reset on every render. If `RunDetailPanel` ever caches layout computations internally, this defeats that cache.

**Fix:** Store the compact panel as `v.inlineRunDetail *pkgtui.RunDetailPanel` on the struct. Create it once in `Update()` when `sprintExpanded` transitions to true. Update it in `Update()` when `epicRunsLoadedMsg` arrives (same as the regular run detail path).

---

### MEDIUM — M4: Width Degrades from Split to Inline, But Inline State (`sprintExpanded`) May Already Be False

**Severity:** Medium — user loses their expansion state on terminal resize.

**Location:** Task 4.3.

The plan says: "if `v.layoutMode == LayoutSplit && v.width < 120`, fall through to `LayoutInline` rendering automatically." `LayoutInline` rendering is gated on `v.sprintExpanded`. If the user was in split mode (which shows sprint detail always), resizes below 120 columns, they now see inline mode with expansion collapsed. The sprint panel disappears without user action.

This is a UX inconsistency rather than a data corruption, but it can confuse users mid-operation (e.g., mid-gate-check review).

**Fix:** When falling back from Split to Inline due to narrow terminal, set `v.sprintExpanded = true` automatically so the panel remains visible. Record `v.forcedExpand bool` to distinguish user-collapsed from auto-expanded, so on resize back above 120, Split mode resumes correctly.

---

### LOW — L1: Commands() Captures `v.layoutMode` at Closure-Creation Time, Not Invocation Time

**Severity:** Low — command palette entries can act on stale layout mode.

**Location:** Task 7.4.

```go
tui.Command{
    Name: "Layout: Mode Toggle",
    Action: func() tea.Cmd { v.layoutMode = LayoutToggle; return nil },
},
```

The `Action` closure closes over `v` (the pointer receiver). When `Action()` is called (by the palette), it reads `v.layoutMode` at call time. This is correct — the closure modifies the receiver, not a copy. However, `Commands()` is called by `updateCommands()` in `unified_app.go` at view creation time. The palette command list is snapshotted then. If the view's available commands change (Task 2.6 — mode-gated commands), those changes are not reflected in the palette until `updateCommands()` is called again.

`unified_app.go` currently calls `updateCommands()` only in `enterDashboard()`. Mode switches inside ColdwineView do not trigger `updateCommands()`. So the palette will show Epic commands in Runs mode and vice versa.

**Fix:** Either (a) make `Commands()` always return the full union of commands regardless of mode, with mode-gating at execution time (check `v.mode` inside each `Action` closure), or (b) emit a message from `switchMode()` that `unified_app.Update()` handles to re-call `updateCommands()`. Option (a) is simpler and avoids adding a new cross-layer message type.

---

### LOW — L2: `sprintCreatedMsg` Handler Writes a Partial `intercore.Run` Stub into `v.epicRuns`

**Severity:** Low — stale partial stub read by downstream code before refresh.

**Location:** `coldwine.go:331-356` (existing, carried into merged view).

```go
v.epicRuns[msg.epicID] = &intercore.Run{
    ID:    msg.runID,
    Goal:  msg.goal,
    Phase: "brainstorm",   // hardcoded assumption
}
```

The plan's new `renderSprintPanelForEpic()` will dereference this stub via `v.epicRuns[epic.ID]`. The stub has no `Phases`, no `Status`, no `AutoAdvance`, no `Complexity`, no `CreatedAt`. `renderPhaseTimeline()` will iterate over `run.Phases` — an empty slice — and render nothing. `renderBudget()` will short-circuit on `v.budget == nil` (correct). `renderGateStatus()` will short-circuit on `v.gate == nil` (correct). So the panel renders a header with run ID, an empty phase timeline, and nothing else.

This is not catastrophic. But it creates a 5-second window where the inline/split panel silently shows an incomplete run. The existing code in `loadEpicRuns()` would fetch the real run on next ctrl+r or tab focus.

**Fix:** After writing the stub, also issue `loadDetail(msg.runID)` (the new `pkgtui.LoadRunDetail`) so the full run replaces the stub immediately.

---

## Summary Table

| ID | Title | Severity | Blocks Ship? |
|----|-------|----------|-------------|
| C1 | Auto-advance fires in Epics mode without visible feedback | Critical | Yes |
| C2 | TOCTOU: advance/cancel operates on `activeRun` while user has navigated to different run | Critical | Yes |
| C3 | Orphan run detection races two independent async loads | Critical | Yes |
| H1 | `renderSprintPanelForEpic()` corrupts shared `runDetail` panel across mode switches | High | Yes |
| H2 | Index bounds unchecked in new mode-specific dereferences | High | Yes |
| H3 | `/sprint` sets mode but issues no load; view renders in Runs mode with nil data | High | Yes |
| M1 | Stale `phase` captured in auto-advance closure (inherited from run_dashboard.go) | Medium | No |
| M2 | Rapid mode toggle causes interleaved `RunsLoadedMsg` with last-write-wins | Medium | No |
| M3 | New `RunDetailPanel` allocated every `View()` call in inline expansion | Medium | No |
| M4 | Resize below 120 cols collapses sprint panel silently | Medium | No |
| L1 | Palette command list not refreshed on mode switch | Low | No |
| L2 | `sprintCreatedMsg` stub in `epicRuns` shows incomplete panel until explicit refresh | Low | No |

---

## Recommended Pre-Implementation Changes to the Plan

### Required Before Task 2 (Mode Toggle):

1. **Add generation counters** to `RunsLoadedMsg` and `RunDetailLoadedMsg`. Both messages should carry a `seq uint64` field. ColdwineView tracks `v.runsLoadSeq` and `v.detailLoadSeq`, incremented on each load, and ignores stale messages. This resolves C2, M2.

2. **Derive run target from `v.runs[v.selectedRun]`** in `advancePhase`/`cancelRun`, not from `v.activeRun`. `activeRun` becomes read-only display state, not action target. This resolves C2.

3. **Use two `RunDetailPanel` instances**: `v.inlineRunDetail` for Epics mode rendering and `v.runsRunDetail` for Runs mode. Never share. This resolves H1.

### Required Before Task 3 (Inline Expansion):

4. **Move `RunDetailPanel` allocation out of `View()`** into `Update()` in `epicsLoadedMsg`/`epicRunsLoadedMsg` handlers. Resolves M3.

5. **Bounds-guard every `v.epics[v.selected]` dereference** in new functions. Boilerplate: `if v.selected < 0 || v.selected >= len(v.epics) { return "..." }`. Resolves H2.

### Required Before Task 5 (Orphan Runs):

6. **Invoke `computeOrphanRuns()` from both** `epicRunsLoadedMsg` and `RunsLoadedMsg` handlers. Guard at top of `computeOrphanRuns` with `if v.runs == nil || v.epicRuns == nil { return }`. Resolves C3.

### Required Before Task 6 (Tab Removal):

7. **Make `ColdwineView.Focus()` mode-aware**: `if v.mode == ModeRuns { return tea.Batch(v.loadData(), v.loadRunsForMode()) }`. Resolves H3.

8. **Add mode guard to auto-advance status message rendering**: render `v.statusMsg` in the document area in both Epics and Runs modes (or redirect to chat panel message). Resolves C1.

9. **Make `Commands()` return mode-gated commands via runtime check inside Action closures**, not by filtering at `Commands()` call time. Resolves L1.
