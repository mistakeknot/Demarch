# Architecture Review: E7 Bigend Kernel Migration Plan

**Plan:** `hub/autarch/docs/plans/2026-02-20-bigend-kernel-migration-plan.md`
**Date:** 2026-02-20
**Reviewer:** Flux-drive Architecture & Design Reviewer

---

## Executive Summary

The plan is well-structured and the existing implementation (icdata, aggregator/kernel.go, discovery) is architecturally sound. The flow `ic CLI subprocess → icdata types → aggregator → TUI/web` has a clean dependency direction and good layering. Three issues warrant action before shipping: a misclassified responsibility in F2.3 (Intermute merge logic placed in the wrong layer), an already-present LRU dedup ownership divergence in F5.1, and the continued accumulation of rendering concerns into model.go for F6. A plan-level stale reference is also noted.

Findings are graded P0–P3:

- **P0** — Must fix; incorrect or will cause bugs
- **P1** — High risk; likely to harm maintainability or correctness
- **P2** — Medium; technical debt with growing cost
- **P3** — Low; cleanup or stylistic

---

## 1. Module Boundaries and Dependency Direction

### Finding 1.1 — F2.3: Intermute merge logic placed in the wrong layer (P1)

**Plan text:**
> "When an Intermute agent name matches a kernel dispatch agent name, merge into a single display row. Files: `internal/bigend/aggregator/kernel.go` (new `mergeAgentDispatches()` helper)"

**Problem:**
`aggregator/kernel.go` is scoped to Intercore kernel data — it owns `KernelState`, `enrichRuns`, `enrichDispatches`, `enrichEvents`, and `computeKernelMetrics`. All of those operate exclusively on `icdata.*` types. Placing `mergeAgentDispatches()` there crosses a layer boundary: it would reach across to the Intermute data model (the `[]Agent` list and their `Name` field) to perform a display-oriented join.

The correct owner for cross-source joins is `aggregator.go` itself, inside `Refresh()`, where all data sources are already assembled together. At the point where `kernelActivities` and `mergedActivities` are computed (lines 445–462 of `aggregator.go`), both `agents` (from `loadAgents()`) and `kernelState.Dispatches` are available in scope. That is the seam where a dispatch-to-agent name match should be performed, either inline or in a new `mergeDispatchAgents(agents []Agent, ks *KernelState)` function in `aggregator.go`.

Placing the merge in `kernel.go` would require that file to import or reference `aggregator.Agent`, which is defined in the same package but semantically belongs to the Intermute layer — creating a conceptual circular dependency within the package where the kernel file starts caring about non-kernel data.

**Smallest fix:** Move `mergeAgentDispatches()` to `aggregator.go` and call it from `Refresh()` after both `agents` and `kernelState` are populated. The function signature becomes:

```go
func mergeDispatchAgents(agents []Agent, ks *KernelState) // mutates ks.Dispatches in place or returns merged view
```

Keep `kernel.go` Intercore-only.

---

### Finding 1.2 — pkg/tui imports internal/icdata (P2, existing)

`pkg/tui/components.go` already imports `github.com/mistakeknot/autarch/internal/icdata` for `UnifiedStatusSymbol` and related helpers. This is a `pkg/` package depending on an `internal/` package — a Go layering inversion. `pkg/` is meant to be importable by multiple tools within the module; `internal/bigend/` is private to the bigend subsystem.

The E7 plan worsens this slightly by adding `UnifiedStatusStyle` to the same file (F8.1), but the violation predates E7.

The plan's note about `UnifiedStatusSymbol` being added to `pkg/tui/styles.go` is also stale — the function already exists in `pkg/tui/components.go` and is already being called from `model.go` at line 1518. F8.1 as written would create a duplicate. This needs to be reconciled before implementing F8.1.

**Smallest fix for F8.1:** Verify that `UnifiedStatusStyle()` does not yet exist in `pkg/tui/components.go`, then add it there (not `styles.go`, which has no functions). Do not add `UnifiedStatusSymbol()` again. The plan's stated file target (`styles.go`) is wrong.

**Longer-term:** If `icdata.UnifiedStatus` needs to be visible to `pkg/tui`, consider moving the type to `pkg/` or a neutral shared package so the dependency direction is correct. This is outside E7 scope.

---

### Finding 1.3 — Dependency direction is otherwise clean (no action)

The core flow is well-directed:

```
internal/icdata/     (pure data types + ic subprocess calls)
    ↓
internal/bigend/aggregator/kernel.go   (enrichment, metrics)
    ↓
aggregator.State.Kernel *KernelState
    ↓
internal/bigend/tui/model.go           (read-only rendering)
    ↓
pkg/tui/                               (shared styles and components)
```

The `aggregatorAPI` interface in `model.go` (lines 50–60) correctly abstracts the aggregator from the TUI so tests can inject mocks. `icdata` is never imported directly by `model.go` — it accesses kernel data only through aggregator types. This is the right design.

---

## 2. Pattern Analysis

### Finding 2.1 — F8.1 plan references a stale file and duplicates an existing function (P0)

**Plan text (F8.1):**
> "Add `UnifiedStatusSymbol(status icdata.UnifiedStatus) string` and `UnifiedStatusStyle(status) lipgloss.Style` to `pkg/tui/styles.go`"

**Actual state:**
- `UnifiedStatusSymbol()` already exists at `pkg/tui/components.go:24`
- `UnifyStatusForRender()` already exists at `pkg/tui/components.go:43`
- Both are already imported by `model.go` via `shared "github.com/mistakeknot/autarch/pkg/tui"` and called at line 1518
- `pkg/tui/styles.go` contains only `var` declarations and no functions; adding a function there would be an inconsistency with the existing package convention

If an implementer follows F8.1 as written, they will create a compilation error (duplicate `UnifiedStatusSymbol` function) or silently create a parallel unused copy. The plan must be corrected before implementation begins.

**Action:** Update F8.1 to read: "Add `UnifiedStatusStyle(status icdata.UnifiedStatus) lipgloss.Style` to `pkg/tui/components.go` (alongside existing `UnifiedStatusSymbol`). `UnifiedStatusSymbol` already exists — do not redeclare."

---

### Finding 2.2 — Duplication of grouping logic between Model and VauxhallPane (P3, existing)

`model.go` defines `groupSessionItemsByProject()` and `groupAgentItemsByProject()` (lines 388–499). `pane.go` (VauxhallPane) defines its own `groupSessionItems()` and `groupAgentItems()` (lines 340–406) with identical logic. E7 does not add more duplication, but F6's new run-list rendering will add a third grouping pattern unless this is addressed.

This is existing technical debt and out-of-scope for E7, but F6 implementers should be aware: reuse the existing grouping helpers rather than writing a third variant.

---

### Finding 2.3 — statusForSession() duplication is correctly targeted by F8.3 (no additional action)

`model.go` (line 653) and `pane.go` (line 259) both implement `statusForSession()` with TTL cache. F8.3 correctly eliminates the render-path invocation in model.go by reading from `TmuxSession.UnifiedState` instead. This is the right call — the aggregator already runs detect and stores the result. The pane.go version is acceptable to leave for its isolated rendering context.

---

## 3. Simplicity and YAGNI

### Finding 3.1 — model.go god-object risk is real and F6 will make it worse (P1)

**Current state:** model.go is 1598 lines. It contains:
- The `Model` struct (31 fields)
- Bubble Tea `Init()`, `Update()`, `View()` implementations
- Key binding definitions (a separate `keyMap` struct and `keys` var)
- Item types for 4 list models (`SessionItem`, `ProjectItem`, `GroupHeaderItem`, `AgentItem`, `MCPItem`)
- Filter parsing and filtering functions (`parseFilter`, `filterSessionItems`, `filterAgentItems`)
- Grouping functions for sessions and agents
- Layout computation (`paneWidths`, `renderTwoPane`, `renderThreePane`)
- Rendering functions (`renderHeader`, `renderFooter`, `renderDashboard`, `renderFilterLine`, `renderPrompt`)
- Status cache management

F6 adds to this file: a run list pane, a run detail pane, a focus ring extending the `Pane` enum, and responsive layout fallback in `paneWidths()`. Based on the plan's task descriptions, F6 alone is estimated to add 200–350 lines to model.go, bringing it to ~1900 lines. The `Pane` enum currently has 3 values (PaneProjects, PaneMain, PaneTerminal); F6.3 extends it with run-list and detail panes, changing the meaning of `activePane` switching logic throughout.

**The structural risk:** The `Update()` function in model.go (lines 700–1047) is already a 347-line switch statement. Adding F6 key handling inline here means navigation logic for 5 pane contexts lives in one function. When a bug report says "arrow keys navigate the wrong pane," there is no isolation boundary to help narrow the cause.

**Recommended decomposition for F6 (smallest viable change):**

1. Extract item types and filter functions into a new file: `internal/bigend/tui/items.go`. These are pure types with no Bubble Tea dependency. Estimated: ~300 lines moved, zero behavior change.

2. Extract `renderDashboard()` into `internal/bigend/tui/render_dashboard.go`. This function is already 173 lines (1425–1597) and will grow with F4 additions. It has no state mutation — it takes a read from `m.agg.GetState()` and returns a string.

3. For F6 specifically: implement `renderRunList()` and `renderRunDetail()` as methods on a new `RunListPane` struct in `internal/bigend/tui/runlistpane.go`, following the same pattern as `TerminalPane` in `terminal.go`. The `Model` holds a `*RunListPane` field. Key handling for run-list navigation delegates to `RunListPane.Update()`. This keeps the new pane's key map, selection state, and filter state out of the already-large `Model.Update()`.

None of these require changing the `aggregatorAPI` interface or any aggregator behavior. They are purely file-level extractions.

**If the team opts not to decompose before F6:** the minimum guard is to add F6 key handling to a clearly delimited `case key.Matches(msg, ...) // F6 run list` block at the top of the switch and leave a comment marking the section boundary. This costs nothing but prevents future readers from losing the F6 additions in the existing 347-line switch.

---

### Finding 3.2 — F5.1: LRU dedup ownership is split and the plan misidentifies the location (P1)

**Plan text (F5.1):**
> "Add `seenEvents map[string]struct{}` field on Aggregator (or KernelState). Capped at `limit * 10` entries with LRU eviction."

**Actual state:** The LRU dedup is already fully implemented on `Aggregator` in `aggregator.go`:
- `seenEvents map[string]struct{}` field at line 121
- `seenOrder []string` field at line 122 (the ring-buffer backing the LRU)
- Both initialized in `New()` at line 156
- Populated in `Refresh()` at lines 449–462 with a 500-entry eviction cap

The plan proposes adding this but it already exists. The discrepancy between the plan's stated cap (`limit * 10`) and the existing cap (500 fixed) needs to be resolved: is the existing implementation the right one, or does the plan intend to replace it with a dynamically sized cap?

More critically, the plan raises a design question: "seenEvents on Aggregator vs KernelState." The existing implementation puts it on `Aggregator`, which is correct. `KernelState` is a snapshot value type — it is replaced wholesale on every refresh cycle (line 466: `a.state = State{..., Kernel: kernelState, ...}`). A seen-set on `KernelState` would be reset every 2 seconds and would never accumulate history. The plan should not revisit this question — the answer is `Aggregator`.

**Action:** F5.1 should be updated to reflect that the dedup mechanism already exists. The actual remaining work is: (a) verify the 500-entry cap is sufficient for `limit * 10` expectations (the plan mentions a separate `limit` parameter that is not currently in scope), and (b) ensure the bootstrap path (F5.2) pre-populates `seenEvents` before emitting to Activities so historical events are not re-emitted as new.

---

### Finding 3.3 — F6.4 responsive fallback extends paneWidths() cleanly (no action)

The plan adds `<100 column` narrow fallback to `paneWidths()` (lines 1314–1334). The existing function returns `(leftW, rightW int, singlePane bool)` and already has a narrow-screen collapse path when `width < minLeft+minRight+gap`. The F6 extension — adding a `<100 col` threshold for run-list-only mode — fits naturally into the existing return signature without needing a new function. No architecture concern here.

---

### Finding 3.4 — Signal broker readiness claim is accurate; no premature hooks needed (no action)

The plan's assessment at the end is correct: `KernelState` being a separate struct means a future signal broker can populate it via WebSocket without changing the TUI or web layer contracts. The `mergeActivities()` dedup by `SyntheticID` is source-agnostic. The 2s polling timer in `model.go:tick()` is the only coupling to polling. No preparatory hooks are needed.

---

## 4. Concurrency and Integration Risk

### Finding 4.1 — seenEvents accessed outside the aggregator mutex (P1)

In `aggregator.go`, the seen-set update (lines 449–462) happens between the `a.mu.RUnlock()` at line 443 and the `a.mu.Lock()` at line 465. During this window, `seenEvents` and `seenOrder` are mutated without holding the mutex. Because `Refresh()` is guarded by `a.refreshing` (the atomic pileup guard), only one `Refresh()` call runs at a time. However, `addActivity()` (line 268) also reads/writes `a.state.Activities` under `a.mu.Lock()` and does NOT interact with `seenEvents`. If a WebSocket event fires `addActivity()` concurrently while `Refresh()` is in the window between lines 443 and 465, `seenEvents` is not consulted for that incoming event, and the activity will bypass dedup.

This is a latent bug: under normal 2s polling with no active WebSocket, it is harmless. Under active WebSocket connection, it can produce duplicate activities in the feed.

This is not introduced by E7 (the existing code has this gap), but F5's bootstrap work (F5.2) will amplify the impact: if bootstrap pre-populates `seenEvents` while WebSocket events are flowing, the race window grows.

**Smallest fix:** Move `seenEvents` and `seenOrder` updates inside the `a.mu.Lock()` block at line 465, or add a separate `a.seenMu sync.Mutex` protecting only the seen-set. The simpler option is to fold the seen-set update into the existing lock.

---

## 5. Summary Table

| # | Feature | Severity | Finding | Action |
|---|---------|----------|---------|--------|
| 1.1 | F2.3 | P1 | `mergeAgentDispatches` belongs in `aggregator.go`, not `kernel.go` | Move to `aggregator.go`, call from `Refresh()` |
| 1.2 | F8 | P2 | `pkg/tui` importing `internal/icdata` is a layering inversion | Accept for now; track for future type move |
| 2.1 | F8.1 | P0 | Plan instructs adding `UnifiedStatusSymbol` to `styles.go`; it already exists in `components.go` | Correct plan before implementation; only add `UnifiedStatusStyle` |
| 2.2 | F6 | P3 | Grouping logic duplicated between `model.go` and `pane.go` | Note for F6 implementer; reuse existing helpers |
| 3.1 | F6 | P1 | model.go will grow to ~1900 lines; `Update()` becomes unwieldy | Extract `items.go`, `render_dashboard.go`, `runlistpane.go` before or during F6 |
| 3.2 | F5.1 | P1 | LRU dedup already exists on Aggregator; plan misidentifies state | Update plan; verify cap; fix bootstrap path |
| 4.1 | F5 | P1 | `seenEvents` mutated outside `mu` lock; race with WebSocket `addActivity` | Move seen-set update inside existing `mu.Lock()` block |

---

## 6. Recommended Implementation Order Adjustment

The plan's sequencing (F8 → F1 → F3 → F2+F4 → F5 → F6) is reasonable. With the above findings, add these steps:

1. Before F8.1: verify `UnifiedStatusStyle` does not exist; add only it to `components.go`.
2. Before F2.3: move `mergeAgentDispatches` to `aggregator.go`; keep `kernel.go` Intercore-only.
3. Before F5: fix `seenEvents` mutex gap; update F5.1 plan text to reflect existing implementation.
4. Alongside F6 (not after): extract `items.go` and `render_dashboard.go` so F6 rendering additions land in a smaller file.

These adjustments add at most 1–2 hours of setup work and prevent later refactors under feature pressure.
