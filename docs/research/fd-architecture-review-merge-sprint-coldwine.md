# Architecture Review: Merge Sprint Tab into Coldwine

**Plan:** `apps/autarch/docs/plans/2026-02-25-merge-sprint-into-coldwine.md`
**Bead:** iv-oguc3
**Reviewer:** fd-architecture
**Date:** 2026-02-25

---

## Summary

The overall direction is correct: `RunDashboardView` and `ColdwineView` share the same Intercore
client, dispatch watcher integration, and `SidebarSelectMsg` protocol. Merging them reduces
duplicated wiring and removes a tab that was only reachable by navigating away from the view
that creates sprint runs in the first place. The critical path (F1 → F2 → F6) is sound.

Four structural issues require attention before execution. None block the merge, but two will
create technical debt that grows with the codebase.

---

## Issue 1 — MUST FIX: `RunDetailPanel` imports `pkg/intercore` from `pkg/tui`

**Location:** Task 1 — `pkg/tui/run_detail_panel.go`, `pkg/tui/run_actions.go`

**Problem:** The plan puts `RunDetailPanel`, `LoadRunDetail`, `LoadRuns`, `RunsLoadedMsg`, and
`RunDetailLoadedMsg` directly in `pkg/tui/`. Each of these depends on `pkg/intercore` types
(`intercore.Run`, `intercore.Dispatch`, `intercore.BudgetResult`, `intercore.Event`,
`intercore.GateResult`, `intercore.Client`). This is a new dependency `pkg/tui → pkg/intercore`.

`pkg/tui` is the shared TUI style and component layer (sidebar, shell layout, chat panel, log
pane, resize coalescer). It currently has zero knowledge of domain types. Adding `pkg/intercore`
to it makes the domain kernel a dependency of a purely presentational package. Every other view
author (Bigend, Gurgeh, Pollard) now compiles against Intercore even if they never use it.
It also creates a precedent: the next feature will add `pkg/autarch` types to `pkg/tui`, and the
package progressively becomes a god module.

**Evidence from codebase:**
- All existing `pkg/tui` files import only `charmbracelet/bubbles`, `charmbracelet/lipgloss`,
  `charmbracelet/x/ansi`, and stdlib. Zero domain imports.
- `pkg/tui/view.go` defines the `View` interface with no domain references.
- The `pkg/intercore` client is currently wired exclusively in `internal/tui/views/` and `cmd/`.

**Correct boundary:** Rendering logic that is specific to Intercore run data belongs in
`internal/tui/views/`, not `pkg/tui/`. The `pkg/tui/` layer should receive only primitives
(`string`, `int`, pre-rendered `[]SidebarItem`) or generic display structs with no domain
coupling.

**Smallest viable fix:**

Keep `RunDetailPanel` in `internal/tui/views/run_detail_panel.go` (new file, same package as
`coldwine.go`). Extract `LoadRunDetail`, `LoadRuns`, and their message types to
`internal/tui/views/run_actions.go` (already a natural boundary — `sprint_commands.go` exists
there). The only things that genuinely belong in `pkg/tui` from this refactor are:

- `RenderRunStatusBadge(status string) string` — pure string, no domain types
- `FormatTokens(n int64) string` — pure math helper, already nameable without domain coupling
- `RenderRunSidebarItems` — if it accepts `[]SidebarItem` already constructed by the caller,
  not `[]intercore.Run`

This keeps `pkg/tui` domain-free and `RunDetailPanel` one directory away from its only consumer.

---

## Issue 2 — MUST FIX: `SetMode` interface leaks `views`-package types into `internal/tui`

**Location:** Task 6, section 6.7 — `modeSettable` interface in `unified_app.go`

**Problem:** The plan proposes:

```go
// In internal/tui/unified_app.go:
type modeSettable interface {
    SetRunsMode()
}
```

This is the correct pattern — it mirrors `specHandoffReceiver`, `agentSelectorSetter`, etc.
already in the file. However Task 6.3 also shows an earlier draft of this approach that does
not use an interface:

```go
if modeView, ok := a.dashViews[2].(interface{ SetMode(ColdwineMode) }); ok {
    modeView.SetMode(ModeRuns)
}
```

`ColdwineMode` is defined in `internal/tui/views/`. This type assertion form would require
`unified_app.go` to import `views`, completing the circular import. The plan mentions the
correct fix in 6.7 but the earlier code sample in 6.3 contradicts it and will cause a compile
error if copied literally.

**Smallest viable fix:** Delete the `interface{ SetMode(ColdwineMode) }` type assertion entirely
from the plan. Only the `modeSettable` interface approach in 6.7 is correct. Rename it to
`sprintModeActivator` to align with the naming style of existing interfaces in `unified_app.go`
(`specHandoffReceiver`, `slashCommandHandler`, etc.). The implementation method on `ColdwineView`
is `SetRunsMode()` — a zero-argument method that sets `v.mode = ModeRuns` internally.

---

## Issue 3 — STRUCTURAL: Inline expansion allocates a new `RunDetailPanel` on every `View()` call

**Location:** Task 3, section 3.2

**Problem:** The plan's inline expansion code inside `renderDocument()` creates a fresh panel
each render:

```go
compact := pkgtui.NewRunDetailPanel()
compact.SetData(run, nil, nil, nil, nil)
compact.SetMaxEvents(3)
compact.SetSize(v.width-4, 12)
lines = append(lines, compact.CompactView())
```

Bubble Tea calls `View()` on every frame — typically on every key event and every tick. Allocating
and discarding a struct each frame is not catastrophic for a small struct, but the pattern
contradicts the existing approach: both `ShellLayout` and `ChatPanel` are stored as fields on
the view struct and reused. More importantly, if `RunDetailPanel` grows to own a scroll offset
or accumulated display state (as similar panels in this codebase do), this pattern silently
resets that state on every render.

**Smallest viable fix:** Move `runDetail *RunDetailPanel` (already proposed for Runs mode in
Task 2, section 2.1) to serve double duty for the inline mode as well. Initialize it lazily
on first expand. The compact/full distinction is controlled by `SetMaxEvents` before calling
`View()`, not by separate panel instances. This is one field, not two.

---

## Issue 4 — STRUCTURAL: Split pane duplicates `SplitLayout` which already exists in `pkg/tui`

**Location:** Task 4, section 4.1

**Problem:** The plan implements split rendering manually with `lipgloss.JoinHorizontal` and
inline width arithmetic:

```go
leftWidth := (v.width - v.shell.SidebarWidth()) / 2
rightWidth := v.width - v.shell.SidebarWidth() - leftWidth
document := lipgloss.JoinHorizontal(lipgloss.Top,
    lipgloss.NewStyle().Width(leftWidth).Render(epicDoc),
    lipgloss.NewStyle().Width(rightWidth).BorderLeft(true)...Render(sprintDoc),
)
```

`pkg/tui/splitlayout.go` already exists and provides exactly this abstraction: `SplitLayout`
with `LeftWidth()`, `RightWidth()`, `IsStacked()`, and a `Render(left, right string) string`
method. The same file already handles the narrow-terminal fallback. `SprintView` (a sibling in
the same `views` package) already uses `v.shell.SplitLayout()` for exactly this purpose.

Rolling a bespoke implementation introduces two width-calculation paths and means the split
breakpoint (120 cols in the plan, vs `minWidth` in `SplitLayout`) will differ from `SprintView`
behaviour.

**Smallest viable fix:** Replace the manual width arithmetic in Task 4 with:

```go
split := pkgtui.NewSplitLayout(0.5) // 50/50 for epic vs sprint
split.SetMinWidth(120)
split.SetSize(v.width - v.shell.SidebarWidth(), v.height)
document := split.Render(epicDoc, sprintDoc)
```

If `SplitLayout.Render()` does not exist yet, check the actual method signature — the public
API is `LeftWidth()`, `RightWidth()`, `IsStacked()`, which are enough to compose the render
inline with the correct values. Either way, reuse the existing type rather than duplicate the
arithmetic.

---

## Additional Observations (Optional, Non-Blocking)

### Orphan run detection couples epicRuns and runs load ordering (Task 5)

`computeOrphanRuns()` iterates `v.epicRuns` to build the associated set, then filters `v.runs`.
Both maps are populated by separate async loads (`loadEpicRuns` and `loadRunsForMode`). If
`loadRunsForMode` completes before `epicRuns` is populated, `associated` is empty and every run
appears orphaned. The plan does not specify when `computeOrphanRuns` is called.

Call `computeOrphanRuns` in the handler for whichever message arrives second — check both fields
are non-nil before computing. A nil `epicRuns` map should be treated as "epic data not yet
loaded" and the orphan sidebar item suppressed entirely.

### `renderRunStatusBadge` is already package-level in `run_dashboard.go`

The plan notes: "`renderRunStatusBadge()` → stays as package-level `RenderRunStatusBadge()`".
In the actual file it is already a package-level function (`func renderRunStatusBadge(status string) string`,
line 638 of `run_dashboard.go`). The rename to exported is the only change needed — no extraction
required. Verify this before Task 1 to avoid double-work.

### `WindowSizeMsg` width adjustment inconsistency

`ColdwineView.Update` subtracts chrome: `v.width = msg.Width - 6`. `RunDashboardView.Update`
sets width directly: `v.width = msg.Width`. When runs-mode content moves into `ColdwineView`,
it will receive the already-trimmed width. The `RunDetailPanel.SetSize` call in Task 2 should
use `v.width` (the trimmed value), not `msg.Width`. This is consistent with how `ColdwineView`
already works but could silently clip content if copied from the dashboard's unadjusted paths.

### `/sprint` shortcut hardcodes tab index 2

In Task 6.3, the fallback sets `a.dashViews[2]`. The tab resolution in `enterDashboard()` already
does name-based matching via `v.Name()`. Prefer:

```go
for i, v := range a.dashViews {
    if strings.ToLower(v.Name()) == "coldwine" {
        // apply modeSettable
        break
    }
}
```

This is more resilient if tab order ever changes again and costs nothing.

### `renderFooterContent` hardcodes tab shortcut hints

Line 974 of `unified_app.go`:
```go
help += "  │  /big /gur /cold /pol /sig  ctrl+l logs ..."
```

After removing the Sprint tab, `/spr` still works (it redirects to Coldwine). The footer should
mention this or update to `/spr` → Coldwine Runs. This is a UX note, not a structural issue.

---

## Dependency Graph Correctness

The plan's stated critical path (F1 → F2 → F6) is correct. One implicit dependency is missing:
F5 (orphan runs) depends on both F2 (runs mode data fields on ColdwineView) and the async
load ordering fix noted above. Mark F5 as depending on F2 in the bead tracker.

F7 (layout config) is truly independent and can be deferred entirely without blocking the merge.
The config key can default to `"toggle"` on first load and the feature can ship in a follow-on
bead once the core merge is stable.

---

## Verdict

The plan is architecturally coherent and the circular import problem is correctly identified and
solved by the interface pattern. Two structural corrections are required before coding starts:

1. Move `RunDetailPanel` to `internal/tui/views/` — do not introduce `pkg/intercore` into
   `pkg/tui`. This is a hard boundary violation with compounding cost.
2. Remove the `interface{ SetMode(ColdwineMode) }` type assertion from Task 6.3 — only the
   zero-argument `SetRunsMode()` interface approach in 6.7 compiles.

Corrections 3 and 4 (panel allocation in `View()`, reuse of `SplitLayout`) are straightforward
substitutions that reduce the implementation surface and prevent future drift.
