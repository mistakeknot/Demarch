# [Intercore] E7: Autarch Phase 1 — Bigend Migration to Kernel State

**Bead:** iv-ishl
**Phase:** brainstorm (as of 2026-02-20T21:12:30Z)
**Date:** 2026-02-20
**Status:** Brainstorm complete

---

## What We're Building

Migrating Bigend — the multi-project agent mission control dashboard — from its current data sources (filesystem scanning, tmux scraping, Intermute REST) to reading kernel state via `ic` CLI. After migration, Bigend shows runs, dispatches, events, and metrics sourced from Intercore, while retaining existing data pipelines during the transition.

The scope is the 8 existing beads under the E7 epic, organized into vertical slices that each deliver end-to-end from data layer through rendering.

## Why This Approach

### The Current Data Flow (pre-migration)

Bigend's `Aggregator.Refresh()` runs a synchronous pipeline every 2 seconds:

1. **`discovery.Scanner.Scan()`** — filesystem walk (`~/projects/`, depth ≤ 3) looking for `.gurgeh/`, `.coldwine/`, `.pollard/` directories. No kernel awareness. Projects that only have `.clavain/intercore.db` are invisible.

2. **`loadAgents()`** — Intermute REST API (`ListAgentsEnriched`). N+1 pattern: one GET for all agents, one GET per agent for inbox counts. If Intermute is offline, agents list is empty.

3. **`loadTmuxSessions()`** — `tmux list-windows -a` (2s cache), then `tmux.Detector.EnrichSessions()` for agent type detection from session name patterns, then `statedetect.Detector.Detect()` with 4-tier NudgeNik detection (hook files → regex patterns → repetition hashing → activity fallback).

4. **`Activities`** — TODO stub. Only populated via Intermute WebSocket events; otherwise empty.

5. **The aggregator publishes `State`** (projects, agents, sessions, activities) under a write lock. TUI/web read snapshots.

### Key Problem

There is **zero kernel integration in the main Bigend pipeline**. A complete `ic` integration exists in `internal/status/data.go` but is isolated — used only by the standalone `autarch status` TUI. Bigend can't show runs, phases, dispatches, events, or token consumption.

Additionally, there's a **status detection split**: `Aggregator.detectSessionState()` computes rich 4-tier state (hook → pattern → repetition → activity), stores it in `TmuxSession.State`, but the TUI ignores this field and re-runs the simpler `tmux.Client.DetectStatus()` on every render tick. The richer detection results are computed but never displayed.

### Migration Strategy: Additive Enrichment

Both old and new data pipelines run in parallel. Kernel data is added as new fields on `aggregator.State` alongside existing sources. Consumers pick the best available source. Old sources are removed later in E9 (Autarch Phase 2).

This is safe because:
- No existing functionality breaks during migration
- Each vertical slice can be shipped and verified independently
- Rollback is trivial — remove the new enrichment call
- Performance impact is bounded (one `ic` exec per project per refresh, ~50ms each)

## Key Decisions

### 1. Vertical Slice Delivery

Each of the 8 beads ships end-to-end: aggregator change → TUI rendering → web template update. No "data layer first, rendering later" phasing. This means each slice delivers visible user value immediately.

### 2. Projects as Primary Navigation Axis

The projects sidebar remains the primary navigation. Runs appear under each project in the main content pane — not as a top-level navigation axis. This preserves the existing mental model: users think in projects, not in runs.

Layout after migration:
```
┌─ Projects ──────┬─ Project Detail ────────────────────────┐
│ ● Interverse    │ RUNS                                     │
│   Autarch       │ ● tkjd6vhn  Cost scheduling  ██░░ P2    │
│   Clavain       │ ● 6m0lbold  Skip Test        ███░ P1    │
│                 │                                          │
│                 │ DISPATCHES (tkjd6vhn)                    │
│                 │ D12  reviewer-arch  running  2m14s       │
│                 │ D13  reviewer-qual  running  1m48s       │
│                 │                                          │
│                 │ EVENTS                                   │
│                 │ 14:23:01  dispatch.completed  D14        │
│                 │ 14:22:58  gate.passed          R42       │
│                 │                                          │
│                 │ SESSIONS  ─  AGENTS  ─  TOKENS           │
│                 │ (existing tmux sessions/Intermute data)  │
└─────────────────┴──────────────────────────────────────────┘
```

### 3. Exec-Based ic CLI Access

Re-use `internal/status/data.go` as-is for all kernel data fetching. The existing `FetchRuns()`, `FetchDispatches()`, `FetchEvents()`, `FetchTokens()` functions are proven and handle all error cases. No direct SQLite reads — stays decoupled from DB schema.

Each project with `.clavain/intercore.db` gets its own set of `ic` calls per refresh cycle, scoped by `cmd.Dir = project.Path`.

### 4. Unified Event Stream

Kernel events (from `ic events tail`) and Intermute events (from WebSocket) merge into one `Activities` feed with a `Source` tag. One timeline, sorted by timestamp. The event viewport (iv-4c16) shows both sources with visual differentiation.

Event unification model:
```go
type Activity struct {
    Time      time.Time
    Type      string    // "phase.advance", "dispatch.completed", "agent.registered", etc.
    Source    string    // "kernel" | "intermute" | "tmux"
    AgentName string
    ProjectPath string
    Summary   string
    RunID     string    // set for kernel events, empty for Intermute-only events
}
```

### 5. Surface Existing statedetect Results

Fix the status detection split: the TUI should use `TmuxSession.State` from the aggregator (4-tier NudgeNik detection) instead of re-running the simpler `tmux.Client.DetectStatus()`. This eliminates redundant `capture-pane` calls, improves accuracy (hook-based state is authoritative), and is a natural fit with the 4-state status model bead (iv-xu31).

### 6. Keep autarch status Separate

`autarch status` stays as a lightweight single-project viewer. Bigend becomes the full multi-project dashboard. Different use cases: quick check from any project dir vs. full mission control.

## Scope: The 8 Beads as Vertical Slices

### Slice 1: Project Discovery (iv-lemf)
**Bigend: swap project discovery to `ic run list`**

Add `.clavain/intercore.db` detection to `discovery.Scanner`. Add `HasIntercore bool` to `Project` struct. In `Aggregator.Refresh()`, add `enrichWithKernelState(projects)` that calls `status.FetchRuns()` for each project with `HasIntercore`. Add `Runs []status.Run` to `aggregator.State`.

TUI: show run count badge next to project name in sidebar. Web: show runs section on project detail page.

### Slice 2: Agent Monitoring Swap (iv-9au2)
**Bigend: swap agent monitoring to `ic dispatch list`**

Add `Dispatches []status.Dispatch` to `aggregator.State`. In `enrichWithKernelState()`, call `status.FetchDispatches()` for each project. Dispatches complement (not replace) Intermute agents — Intermute provides registration/inbox, `ic` provides lifecycle/status.

TUI: show dispatches under the selected run in the main pane. Status icons from `pkg/tui.StatusIndicator`. Web: dispatch list on project detail page.

### Slice 3: Run Progress (iv-gv7i)
**Bigend: swap run progress to `ic events tail`**

Add `KernelEvents []status.Event` to `aggregator.State`. In `enrichWithKernelState()`, call `status.FetchEvents()` with `--all --limit=50` for each project. Merge kernel events into the unified `Activities` feed with `Source: "kernel"`.

TUI: event stream pane in project detail view. Events show phase transitions, gate checks, dispatch lifecycle. Web: activity stream on dashboard and project pages.

### Slice 4: Dashboard Metrics (iv-1d9u)
**Bigend: dashboard metrics from kernel aggregates**

Compute aggregate metrics from kernel state: active runs count, dispatches in-flight, total tokens consumed, phase distribution histogram. Add `KernelMetrics` struct to `aggregator.State`.

TUI: replace/augment the 4-panel stats row on the dashboard tab. Show: Projects | Active Runs | Dispatches | Tokens. Web: dashboard template shows kernel-sourced metrics.

### Slice 5: Event Viewport (iv-4c16)
**Bigend: bootstrap-then-stream event viewport**

Bootstrap: on startup, fetch last N events per project via `ic events tail`. Stream: continue polling every refresh cycle (2s). For Intermute events, the existing WebSocket reactive path continues.

The viewport auto-scrolls, supports filtering by event type and project, and uses `pkg/tui.LogPane` for rendering. Follow mode (like `tail -f`) is deferred to v2.

### Slice 6: Two-Pane Layout (iv-4zle)
**Bigend: two-pane lazy layout (list + detail)**

Refactor the main content pane to support list+detail split within the project view. Left: run list with phase progress bars. Right: detail for selected run (dispatches, events, tokens).

This extends the existing `paneWidths()` logic. When no run is selected, the full pane shows the legacy view (sessions, agents). When a run is selected, the pane splits.

### Slice 7: Typed KernelEvent Enum (iv-jaxw)
**Typed KernelEvent enum for all observable state changes**

Define a Go enum for all kernel event types: `PhaseAdvance`, `PhaseRollback`, `GateCheck`, `GatePassed`, `GateFailed`, `DispatchSpawned`, `DispatchCompleted`, `DispatchFailed`, `DispatchCancelled`, `ArtifactAdded`, `TokensRecorded`, `BudgetExceeded`.

This replaces string matching on event types throughout the codebase. The enum lives in `pkg/signals/` (shared across Autarch tools) and maps 1:1 to `ic` event type strings.

### Slice 8: 4-State Status Model (iv-xu31)
**Adopt 4-state status model with consistent icons**

Consolidate the fragmented status representations:
- tmux.Client.DetectStatus: `StatusRunning`, `StatusWaiting`, `StatusIdle`, `StatusError`, `StatusUnknown`
- statedetect.Detector: `working`, `waiting`, `blocked`, `stalled`, `done`, `error`, `unknown`
- Intermute agents: `active`, `idle`
- ic dispatches: `running`, `completed`, `failed`, `cancelled`, `timeout`

Unified 4-state model: **Active** (working, running), **Waiting** (waiting, blocked, idle), **Done** (completed, done), **Error** (failed, error, cancelled, timeout, stalled).

Each state gets a consistent icon and color from `pkg/tui/styles.go`. The mapping function lives in `pkg/tui/components.go`.

Fix the status detection split: TUI uses `TmuxSession.State` from the aggregator instead of re-running `tmux.Client.DetectStatus()`.

## Sequencing and Dependencies

```
Slice 7 (KernelEvent enum)  ──┐
                               ├──→ Slice 5 (Event viewport)
Slice 8 (4-state status)   ──┤
                               ├──→ Slice 2 (Agent monitoring)
Slice 1 (Project discovery) ──┤
                               ├──→ Slice 3 (Run progress)
                               ├──→ Slice 4 (Dashboard metrics)
                               └──→ Slice 6 (Two-pane layout)
```

**Foundation slices (no dependencies, can parallelize):**
- Slice 1 (project discovery) — adds HasIntercore + enrichWithKernelState
- Slice 7 (KernelEvent enum) — pure type definitions
- Slice 8 (4-state status) — status mapping + TUI fix

**Dependent slices (need Slice 1 for kernel data):**
- Slices 2, 3, 4, 5 all need `enrichWithKernelState()` from Slice 1
- Slice 5 (event viewport) benefits from Slice 7 (typed events)
- Slice 2 (agent monitoring) benefits from Slice 8 (unified status model)
- Slice 6 (two-pane layout) needs Slices 1+2+3 to have data to display

**Recommended execution order:**
1. Slices 1 + 7 + 8 in parallel (foundation)
2. Slices 2 + 3 + 4 in parallel (data enrichment)
3. Slice 5 (event viewport — builds on 3 + 7)
4. Slice 6 (two-pane layout — builds on all)

## What's Already Done

- **`autarch status` TUI** (iv-qloe, closed) — validated `ic` data layer. `internal/status/data.go` is the reusable asset.
- **Rollback system** (iv-0k8s, closed) — `ic run rollback` shipped. Enables the rollback event type in Slice 7.
- **TUI validation tests** (iv-knwr, open) — plan written but not executed. Tests verify `pkg/tui` components render kernel data correctly. Should execute before or during Slice 8.
- **`pkg/tui/` shared components** — styles, StatusIndicator, StatusSymbol, AgentBadge, PriorityBadge, LogPane, CommonKeys all exist.

## Open Questions

1. **Refresh coalescing** — The 2-second poll adds `ic` exec calls per project. With 5+ projects, that's 20+ subprocess calls per cycle. Should we add rate limiting or coalescing? Or is 50ms × 5 projects = 250ms fast enough?

2. **Project-scoped vs global event view** — Should the dashboard show a global event stream (all projects merged) or only the selected project's events? Leaning toward global on dashboard, project-scoped in detail view.

3. **Signal broker integration (iv-0v7j)** — The signal broker bead is P1 and currently open. Should E7 integrate with the signal broker for real-time kernel event push, or keep polling and let E9 add signal broker integration?

4. **TUI validation tests timing** — iv-knwr has a plan but hasn't been executed. Should it gate Slice 8, or can they proceed in parallel with tests running after the status model is implemented?

## Non-Goals (E7)

- Removing old data sources (Intermute, tmux, filesystem) — deferred to E9
- Direct SQLite reads — exec-based ic CLI is sufficient
- Signal broker / WebSocket for kernel events — deferred
- Multi-project aggregation across separate DBs — each project polled independently
- Follow mode for events (`ic events tail --follow`) — deferred to v2
- Write operations in Bigend (creating runs, advancing phases) — read-only dashboard
