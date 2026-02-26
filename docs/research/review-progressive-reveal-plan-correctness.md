# Correctness Review: Pollard Progressive Reveal Plan
**Plan file:** `docs/plans/2026-02-23-pollard-progressive-reveal.md`
**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-23
**Full review:** `.claude/reviews/fd-correctness-progressive-reveal.md`

---

## Invariants

These must hold for the implementation to be correct:

1. All tea messages sent via `program.Send()` from hunter goroutines arrive on the Bubble Tea event loop and are processed by `Update()`.
2. `PollardView.hunterStatuses` and `PollardView.insights` are only ever touched in `Update()` — on the single Bubble Tea goroutine. No synchronization is needed for those fields.
3. Messages from a cancelled or superseded run must not alter the view state for the current run.
4. `v.selected` must never index out of bounds into `v.insights`.
5. A shared coordinator instance must not bleed one view's research state into another view's display.
6. Hunter goroutines must not outlive the user's intent (i.e., tab switch or TUI shutdown must stop them).

---

## Finding 1 — CRITICAL: Coordinator never has SetProgram called; all messages are silently dropped

**Severity:** P0 — the entire feature does not work.

**Location:** `cmd/autarch/main.go` (plan Task 1, Step 2) and `internal/pollard/research/coordinator.go:390-397`

**What the plan proposes:**

```go
researchCoord := research.NewCoordinator(nil)
// ...
views.NewPollardView(c, researchCoord),
```

**What actually happens:**

`Coordinator.sendMsg` only delivers messages if `c.program != nil`:

```go
// coordinator.go:390-397
func (c *Coordinator) sendMsg(msg tea.Msg) {
    c.mu.RLock()
    p := c.program
    c.mu.RUnlock()

    if p != nil {
        p.Send(msg)
    }
}
```

`SetProgram` is never called on the research coordinator anywhere in the production code. A search of the entire codebase confirms this — only the log handler's `SetProgram` is invoked at `cmd/autarch/main.go:391`. The research coordinator's `program` field is always `nil` at runtime.

**Result:** Every `RunStartedMsg`, `HunterUpdateMsg`, `HunterCompletedMsg`, `HunterErrorMsg`, and `RunCompletedMsg` is silently discarded. `PollardView` never receives a single research message. The spinner stays static, no findings appear, and `runActive` is never set to `true` — yet no error is surfaced. This failure is invisible at compile time and test time (tests construct the view in isolation without needing the program).

**Fix:** After creating `tea.NewProgram(app, ...)`, call `researchCoord.SetProgram(p)`. The existing pattern with `logHandler.SetProgram(p)` shows the correct place in `internal/tui/unified_app.go` (around line 993) or in `cmd/autarch/main.go` after `tea.NewProgram` is created.

```go
// In tui.Run (unified_app.go), after p := tea.NewProgram(app, progOpts...)
// The coordinator needs to be threaded out to the Run function, or
// stored on the app so Run can wire it:
researchCoord.SetProgram(p)
```

This requires either threading the coordinator through `tui.Run` options, or storing it on `UnifiedApp` with a `SetResearchCoordinator` method so `Run()` can call `SetProgram` after the program is created. The plan makes no provision for this.

---

## Finding 2 — CRITICAL (pre-existing, newly triggered): Deadlock in coordinator.StartRun when a run is already active

**Severity:** P0 when "Run Research" is clicked a second time — the TUI freezes permanently.

**Location:** `internal/pollard/research/coordinator.go:64-85`

**The interleaving:**

```
goroutine A (tea.Cmd callback, i.e. background goroutine from Bubble Tea):
    StartRun() called
    c.mu.Lock()                     // A holds write lock
    c.activeRun != nil, so:
    c.sendMsg(RunCancelledMsg{...}) // sendMsg calls c.mu.RLock()
    <goroutine A blocks — it holds Lock and is trying to acquire RLock on same mutex>
    <DEADLOCK: Lock() is not released until RLock() returns, but RLock() waits for Lock() to be released>
```

Go's `sync.RWMutex` is not reentrant. A goroutine holding a write lock cannot also acquire a read lock on the same mutex — that is an unconditional deadlock. The existing code at lines 67-73 calls `sendMsg` (which acquires `RLock`) while already holding `Lock`. This fires only when `c.activeRun != nil`, which is the second invocation of "Run Research" in the same session.

The plan does not mention this pre-existing defect, but it is directly on the critical path — the plan's Task 5 enables the "Run Research" command, which makes it user-triggerable for the first time. Before the plan, no code called `StartRun` from PollardView.

**Fix:** Capture the program pointer before acquiring the lock, then send after releasing it:

```go
func (c *Coordinator) StartRun(ctx context.Context, projectID string, hunterNames []string, topics []TopicConfig) (*Run, error) {
    var cancelledRunID string

    c.mu.Lock()
    if c.activeRun != nil {
        cancelledRunID = c.activeRun.RunID
        c.activeRun.Cancel()
    }
    run := NewRunWithContext(ctx, projectID)
    c.activeRun = run
    for _, name := range hunterNames {
        run.RegisterHunter(name)
    }
    c.mu.Unlock() // Release before any sends

    if cancelledRunID != "" {
        c.sendMsg(RunCancelledMsg{RunID: cancelledRunID, Reason: "new run started"})
    }
    c.sendMsg(RunStartedMsg{...})
    go c.executeRun(run, hunterNames, topics)
    return run, nil
}
```

---

## Finding 3 — MEDIUM: No RunID validation in message handlers; stale messages corrupt view state

**Severity:** P1 — produces wrong UI state under normal usage patterns (tab switch during a run, then start new run).

**Location:** Plan Task 2, Step 1 — all message handler cases

**What happens:**

The plan's `Update()` cases for `HunterStartedMsg`, `HunterUpdateMsg`, `HunterCompletedMsg`, and `HunterErrorMsg` do not validate that `msg.RunID` matches the current active run. Every message carries a `RunID` field specifically for this purpose (see `run.go:53-59`, `messages.go:16-41`, and the comment "Must match active run").

**Concrete interleaving that corrupts state:**

```
t=0: User is on Pollard tab. Gurgeh starts a research run (run-A).
     RunStartedMsg{RunID: "run-A"} arrives.
     PollardView.Update: v.runActive = true, v.hunterStatuses populated with Gurgeh's hunters.
t=1: User clicks "Run Research" on Pollard (run-B starts).
     RunStartedMsg{RunID: "run-B"} arrives, resets hunterStatuses correctly.
t=2: Stale HunterCompletedMsg{RunID: "run-A", HunterName: "github-scout", FindingCount: 42} arrives.
     PollardView.Update: hs.Status = StatusComplete, hs.Findings = 42.
     v.hunterStatuses["github-scout"] now shows "complete (42)" even though run-B's github-scout is still running.
```

The `ResearchOverlay` in `research_overlay.go` avoids this by fetching state through `run.GetAllUpdates()` — which is always attached to the coordinator's current `activeRun` — rather than applying message deltas directly. The plan takes the delta approach without adding the runID guard.

**Fix:** Each message handler must check the RunID. Add a `currentRunID string` field to `PollardView` (set in `RunStartedMsg` handler), and guard every other handler:

```go
case research.HunterStartedMsg:
    if msg.RunID != v.currentRunID {
        return v, nil // discard stale message
    }
    // ... rest of handler
```

---

## Finding 4 — MEDIUM: Shared coordinator bleeds Gurgeh's research into PollardView

**Severity:** P1 — wrong data displayed.

**Location:** Plan Task 1, Step 2 (`cmd/autarch/main.go`)

**What the plan proposes:**

The plan says: "Extract `researchCoord` to a local variable so both GurgehConfig and PollardView share the same instance."

`program.Send()` is a broadcast — every view's `Update()` receives every message. When Gurgeh's hunters start, `RunStartedMsg` arrives at `PollardView.Update()`. The plan's handler immediately sets `v.runActive = true` and populates `v.hunterStatuses` with Gurgeh's hunter names. Pollard's sidebar then shows Gurgeh's research status, and progressive findings from Gurgeh's hunters are inserted into Pollard's insights list.

If sharing is intentional (they want Pollard to reflect all ecosystem research), then the plan needs to document it explicitly and consider the implications. If each view should show only its own runs, they need separate coordinator instances.

**Fix (if intent is separate):** Instantiate a separate coordinator for PollardView:

```go
pollardCoord := research.NewCoordinator(nil)
// ... call pollardCoord.SetProgram(p) after program creation
views.NewPollardView(c, pollardCoord),
```

**Fix (if intent is shared):** Document the sharing explicitly, and implement RunID filtering (Finding 3) to avoid cross-contamination of statuses.

---

## Finding 5 — MEDIUM: insightsLoadedMsg replaces progressively-built insights during an active run; Focus() triggers this path

**Severity:** P2 — visible data loss / flicker, but no crash.

**Location:** Current `pollard.go:104-111`, plan Task 2 (`RunCompletedMsg` handler), current `pollard.go:301` (`Focus()`)

**The sequence:**

1. User starts "Run Research". `HunterUpdateMsg` arrives. `addFinding` populates `v.insights` with 5 entries.
2. User switches to another tab and back. `Focus()` is called.
3. `Focus()` calls `v.loadInsights()` unconditionally (line 301: `return tea.Batch(v.chatPanel.Focus(), v.loadInsights())`).
4. `insightsLoadedMsg` arrives. Handler: `v.insights = msg.insights` — replaces everything with the persisted server state, which may have 0 items because the run hasn't completed yet.
5. All 5 progressive findings vanish. The sidebar goes blank.

**Fix:** Guard `insightsLoadedMsg` application: if `v.runActive` is true, discard the server load result.

```go
case insightsLoadedMsg:
    v.loading = false
    if msg.err != nil {
        v.err = msg.err
    } else if !v.runActive { // Don't overwrite in-flight progressive state
        v.insights = msg.insights
    }
    return v, nil
```

Also guard `Focus()`:

```go
func (v *PollardView) Focus() tea.Cmd {
    v.shell.SetFocus(pkgtui.FocusChat)
    cmds := []tea.Cmd{v.chatPanel.Focus()}
    if !v.runActive {
        cmds = append(cmds, v.loadInsights())
    }
    return tea.Batch(cmds...)
}
```

---

## Finding 6 — MEDIUM: v.selected not reset when insights slice is replaced or extended

**Severity:** P2 — confusing UX; no crash because `renderDocument` guards with `if v.selected >= len(v.insights)`.

**Location:** Plan Task 2, `addFinding` helper and `insightsLoadedMsg` handler

When `insightsLoadedMsg` replaces `v.insights` with a shorter server list, `v.selected` may be beyond the new length and `renderDocument` silently shows "No insight selected" instead of selecting the nearest valid item.

When `addFinding` inserts a new finding at index `idx` where `idx <= v.selected`, the previously selected item shifts to `v.selected + 1`, but `v.selected` stays at the same index — pointing at the newly-inserted item instead of the one the user was viewing.

**Fix:** After replacing the slice, clamp the selection:

```go
if v.selected >= len(v.insights) {
    v.selected = max(0, len(v.insights)-1)
}
```

After insertion in `addFinding`, if `idx <= v.selected`, increment `v.selected`.

---

## Finding 7 — MEDIUM: RunCancelledMsg not handled; runActive stays true permanently after cancellation

**Severity:** P2 — spinner and "Research active" banner never clear if the run is cancelled externally.

**Location:** Plan Task 2, Step 1 — missing case in the message switch

The plan adds handlers for 6 message types but omits `RunCancelledMsg`. The coordinator sends this in two places: when `StartRun` replaces an existing run, and when `CancelActiveRun` is called. With no handler, `v.runActive` stays `true` indefinitely.

**Fix:**

```go
case research.RunCancelledMsg:
    if msg.RunID == v.currentRunID {
        v.runActive = false
    }
    return v, nil
```

---

## Finding 8 — LOW: Hunter goroutines outlive the tab; no cancellation on Blur or shutdown

**Severity:** P3 — resource leak and spurious post-close messages, but no data corruption.

**Location:** Plan Task 5, Step 1 (`Run Research` action) and `pollard.go:305-308` (`Blur()`)

The plan's `Run Research` action passes `context.Background()` to `StartRun`. This context is never cancelled. When the user switches away from Pollard, `Blur()` fires but does not call `CancelActiveRun`. Hunters continue running and sending messages to the program indefinitely.

**Fix:** Cancel on `Blur()`:

```go
func (v *PollardView) Blur() {
    if v.runActive && v.coordinator != nil {
        v.coordinator.CancelActiveRun("tab blurred")
    }
    v.chatPanel.CancelStream()
    v.chatPanel.Blur()
}
```

---

## Finding 9 — LOW: Non-deterministic sidebar order from map range

**Severity:** P3 — cosmetic flicker, no data corruption.

**Location:** Plan Task 3, Step 1 (`SidebarItems()` — hunter status section)

`for name, status := range v.hunterStatuses` iterates in random order. On every render tick (spinner ticks), the hunter badges reorder. Fix: sort the hunter names before iterating.

---

## Finding 10 — INFO: sort.Search insertion for descending sort is correct

**Severity:** None — confirmed correct.

The `addFinding` insertion using `sort.Search` with predicate `v.insights[i].Score < insight.Score` correctly finds the insertion point for descending order. Verified empirically: inserting 0.3, 0.9, 0.6 produces [0.9, 0.6, 0.3]. Equal scores are appended after existing equal-score items (stable).

---

## Summary Table

| # | Severity | Issue | Plan Task |
|---|----------|-------|-----------|
| 1 | P0 CRITICAL | `SetProgram` never called; all messages dropped silently | Task 1 (missing) |
| 2 | P0 CRITICAL | Deadlock in `StartRun` when cancelling existing run | Pre-existing; triggered by Task 5 |
| 3 | P1 MEDIUM | No RunID validation; stale messages corrupt view state | Task 2 |
| 4 | P1 MEDIUM | Shared coordinator bleeds Gurgeh state into Pollard | Task 1 |
| 5 | P2 MEDIUM | `Focus()` / `insightsLoadedMsg` wipes progressive findings during active run | Task 2 |
| 6 | P2 MEDIUM | `v.selected` not clamped after slice replacement or insertion shift | Task 2, Task 4 |
| 7 | P2 MEDIUM | `RunCancelledMsg` unhandled; `runActive` never clears on cancellation | Task 2 |
| 8 | P3 LOW | Hunter goroutines leak on tab switch; no `Blur()` cancellation | Task 5 |
| 9 | P3 LOW | Non-deterministic sidebar order from map range during active run | Task 3 |
| 10 | INFO | `sort.Search` descending insertion is correct | Task 2 |

---

## Required Changes Before Implementation

**P0-1: Wire SetProgram.** Thread the coordinator to the `tui.Run` call site and call `researchCoord.SetProgram(p)` after `tea.NewProgram` is constructed. Without this the feature is a silent no-op at runtime.

**P0-2: Fix the deadlock in coordinator.StartRun.** Move `sendMsg` calls outside the `c.mu.Lock()` section. Collect the cancelledRunID before acquiring the lock, then send `RunCancelledMsg` after `c.mu.Unlock()`. This is a one-function fix in `coordinator.go`.

The P1 issues (RunID guard, coordinator sharing decision) should also be resolved before the feature is considered correct.
