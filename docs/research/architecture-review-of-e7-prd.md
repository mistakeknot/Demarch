# Architecture Review: E7 PRD — Bigend Migration to Kernel State

**Reviewed:** 2026-02-20
**PRD:** `docs/prds/2026-02-20-bigend-kernel-migration.md`
**Brainstorm:** `docs/brainstorms/2026-02-20-bigend-migration-brainstorm.md`
**Codebase:** `hub/autarch/` (Go monorepo, Bubble Tea TUIs)
**Bead:** iv-ishl

---

## Review Method

All findings are grounded in direct codebase inspection. Key files examined:

- `internal/bigend/aggregator/aggregator.go` (877 lines) — State struct, Refresh(), enrichWith* methods, WebSocket path
- `internal/bigend/discovery/scanner.go` — Scan(), examineProject(), inclusion gate
- `internal/status/data.go` — FetchRuns, FetchDispatches, FetchEvents, types
- `internal/status/model.go`, `runs.go`, `dispatches.go`, `events.go` — pane structs, Bubble Tea model
- `internal/bigend/tui/model.go` — imports, statusForSession(), aggregatorAPI interface
- `internal/bigend/statedetect/types.go` — AgentState enum
- `pkg/signals/agent_signal.go` — conflicting AgentState definition
- `internal/bigend/tmux/client.go` — tmux.Status enum
- `pkg/tui/components.go` — StatusIndicator, existing status rendering

---

## Summary

The additive enrichment strategy is sound in principle — no existing functionality breaks, rollback is a single function call removal, and vertical slices deliver visible value independently. The structural risks are real but bounded. Two findings (P0, P1-boundary) must be resolved before implementation begins. The remaining findings can be addressed within slice delivery without blocking parallelism.

---

## Findings

### P0 — WebSocket Activities wipe-on-refresh is a pre-existing bug that E7 makes structurally permanent

**File:** `internal/bigend/aggregator/aggregator.go`, lines 390–401 and 245–262

**Evidence:**

```go
// Refresh() — runs every 2 seconds
activities := []Activity{}           // line 390: always empty
a.mu.Lock()
a.state = State{
    ...
    Activities: activities,           // line 401: zeroes the slice
}
a.mu.Unlock()

// addActivity() — called by WebSocket goroutine between Refresh cycles
a.state.Activities = append([]Activity{activity}, a.state.Activities...)
```

`Refresh()` replaces the entire State struct wholesale. Every call zeroes `Activities`, discarding whatever the WebSocket goroutine has prepended since the last cycle. This is already broken for Intermute events; it is currently hidden because the Activities feed has no visible TUI renderer (the TODO stub at line 390 exists precisely because the feed is empty anyway).

E7's F3 (kernel event merge into Activities feed) and F5 (event viewport with bootstrap-then-stream) both depend on `Activities` accumulating correctly across refresh cycles. Implementing those features without fixing this write conflict means the event viewport will flicker empty on every 2-second boundary as Refresh wipes kernel events that were just appended.

**Recommendation — smallest viable fix:**

In `Refresh()`, preserve the existing activities when constructing the replacement State:

```go
a.mu.RLock()
existingActivities := a.state.Activities
a.mu.RUnlock()

// ... compute newKernelActivities from FetchEvents results ...

merged := mergeActivities(existingActivities, newKernelActivities, 100)

a.mu.Lock()
a.state = State{
    ...
    Activities: merged,
}
a.mu.Unlock()
```

`mergeActivities` deduplicates by event ID (kernel events have integer IDs; Intermute events need a stable ID assigned on receipt). No new struct fields, no new interfaces, no change to the TUI read path. This fix belongs in Slice 1 delivery, not deferred to a later slice.

---

### P1 — Importing internal/status into the aggregator pulls Bubble Tea rendering into the data pipeline

**File:** `internal/status/model.go` imports `github.com/mistakeknot/autarch/pkg/tui`; `internal/status/runs.go`, `dispatches.go`, `events.go` contain Bubble Tea pane structs.

**Evidence:**

`internal/status` contains two distinct concerns bundled in one package:
1. Data types and fetch functions: `Run`, `Dispatch`, `Event`, `TokenSummary`, `FetchRuns()`, `FetchDispatches()`, `FetchEvents()`, `FetchTokens()` in `data.go` — no UI dependencies.
2. Bubble Tea rendering: `RunsPane`, `DispatchPane`, `EventsPane`, `Model` (with `Init()`, `Update()`, `View()`) in `model.go`, `runs.go`, `dispatches.go`, `events.go` — imports `pkg/tui`, `charmbracelet/bubbletea`, `charmbracelet/lipgloss`.

The aggregator currently has zero UI dependencies. Its import list is pure data infrastructure:

```
internal/bigend/{agentcmd,coldwine,colony,config,discovery,mcp,statedetect,tmux}
internal/gurgeh/specs
pkg/intermute
pkg/timeout
```

If the aggregator imports `internal/status` to call `FetchRuns()`, it transitively pulls in the Bubble Tea pane structs and their rendering dependencies. The aggregator is used by both `internal/bigend/tui/model.go` (TUI) and `internal/bigend/web/server.go` (web server). Pulling Bubble Tea into the aggregator means it flows into the web server binary — a Bubble Tea terminal dependency in a server that renders htmx + Tailwind.

**Recommendation — smallest viable change:**

Extract data types and fetch functions out of `internal/status` into a new package, for example `internal/icdata`:

```
internal/icdata/
    types.go    — Run, Dispatch, Event, TokenSummary structs
    fetch.go    — FetchRuns, FetchDispatches, FetchEvents, FetchTokens, runIC
```

`internal/status` keeps its Bubble Tea model, pane structs, and rendering code. `cmd/autarch/status.go` updates its import from `internal/status` to `internal/icdata` for the data types, and continues importing `internal/status` for the TUI model. The aggregator imports only `internal/icdata`.

This is approximately 80 lines of `data.go` moved to a new file and one import path update — no behavior changes, no interface changes.

---

### P1 — aggregator.State becomes a god struct with four new path-keyed maps

**File:** `internal/bigend/aggregator/aggregator.go`, lines 68–76 (current State struct)

**Current State struct:**

```go
type State struct {
    Projects   []discovery.Project
    Agents     []Agent
    Sessions   []TmuxSession
    Colonies   []colony.Colony
    MCP        map[string][]mcp.ComponentStatus
    Activities []Activity
    UpdatedAt  time.Time
}
```

**After E7 as specified:**

```go
type State struct {
    Projects       []discovery.Project
    Agents         []Agent
    Sessions       []TmuxSession
    Colonies       []colony.Colony
    MCP            map[string][]mcp.ComponentStatus
    Activities     []Activity
    UpdatedAt      time.Time
    // New kernel fields (F1, F2, F3, F4):
    Runs           map[string][]status.Run        // keyed by project path
    Dispatches     map[string][]status.Dispatch   // keyed by project path
    KernelEvents   map[string][]status.Event      // keyed by project path
    KernelMetrics  KernelMetrics
}
```

Four new fields, three of them path-keyed maps, alongside the existing flat slices. Every consumer — TUI model, web handler, tests — receives all kernel data even when rendering non-kernel views. Path-keyed lookups are pushed into render-time code. State snapshots copied via `GetState()` (which returns by value) now copy all four maps on every render tick.

The inconsistency is structural: existing sources (Projects, Agents, Sessions) are flat slices; new kernel sources are path-keyed maps. A developer writing a new consumer must understand the hybrid access pattern.

**Recommendation:**

Group the four kernel fields into a sub-struct:

```go
type KernelState struct {
    Runs       map[string][]icdata.Run
    Dispatches map[string][]icdata.Dispatch
    Events     map[string][]icdata.Event
    Metrics    KernelMetrics
}

type State struct {
    // ... existing fields unchanged ...
    Kernel *KernelState   // nil when no kernel-aware projects exist
}
```

Consumers check `state.Kernel == nil` once. `enrichWithKernelState()` returns a `*KernelState`. Refresh assigns it. This is a pure struct reorganization — no behavioral changes, no interface changes, proportionally smaller diff.

---

### P1 — Scanner discovery gate has a two-location update trap for kernel-only projects

**File:** `internal/bigend/discovery/scanner.go`, lines 103 and 111

**Evidence — two separate code paths:**

```go
// Line 103 — WalkDir trigger (stops recursion into the dir)
if d.IsDir() && (d.Name() == ".gurgeh" || d.Name() == ".praude" ||
    d.Name() == ".coldwine" || d.Name() == ".tandemonium" ||
    d.Name() == ".pollard" || d.Name() == ".agent_mail") {

    // Line 111 — Inclusion gate (decides whether to add the project)
    if project.HasGurgeh || project.HasColdwine || project.HasPollard {
        projects = append(projects, project)
    }
}
```

F1 requires `.clavain`-only projects to appear in Bigend. The fix requires two coordinated changes: adding `.clavain` to the WalkDir trigger check (line 103) and adding `|| project.HasIntercore` to the inclusion gate (line 111). These are separate conditions with different failure modes if only one is updated:

- Trigger updated, gate not updated: `.clavain` directories stop recursion correctly but projects are never added to the list. Silent miss.
- Gate updated, trigger not updated: `HasIntercore` is always false because the trigger never fires to call `examineProject()`. Also a silent miss.
- Neither updated: the WalkDir does not stop at `.clavain` dirs, potentially walking into intercore DB internals up to depth 3.

The PRD F1 acceptance criteria do not call out both locations.

**Recommendation:**

Implement F1 in a single commit that touches both locations atomically. Add a test case:

```go
// Given a project directory with only .clavain/intercore.db
// When Scanner.Scan() is called
// Then the project appears in the result with HasIntercore: true and no other Has* flags set
```

The two-location update is not a design flaw — it is a consequence of the scanner's correct separation between traversal control and project classification. It just needs explicit test coverage.

---

### P1 — Three existing AgentState enums will become four with F8; none are retired

**Files:**
- `pkg/signals/agent_signal.go` — `AgentState` (bracket signal semantics, 5 values)
- `internal/bigend/statedetect/types.go` — `AgentState` (NudgeNik detection semantics, 7 values)
- `internal/bigend/tmux/client.go` — `Status` (tmux pane capture semantics, 5 values)

F8 proposes a fourth: `UnifiedStatus` (4 values: Active, Waiting, Done, Error) in `pkg/tui/components.go`. Plus ic dispatch statuses (running, completed, failed, cancelled, timeout) as a fifth string vocabulary mapped through `UnifyStatus`.

None of the three existing enums are retired in E7. The statedetect and tmux enums survive explicitly into E9. The `UnifyStatus` mapping function in `pkg/tui/components.go` must handle all five vocabularies simultaneously with no type safety — it accepts `string` and switches on raw string values.

The status detection split fix (TUI uses `TmuxSession.State` from aggregator rather than re-running `tmux.Client.DetectStatus()`) improves accuracy but does not reduce vocabulary count. `TmuxSession.State` is stored as a raw statedetect string (e.g. `"working"`, `"stalled"`) then mapped through `UnifyStatus` at render time.

**Recommendation:**

Have `detectSessionState()` in the aggregator store `TmuxSession.State` as the `UnifiedStatus` string value rather than the raw statedetect value. The mapping from statedetect 7-value to unified 4-value happens once at write time (in the aggregator), not on every render tick. This removes one string vocabulary from the TUI's render path entirely:

```go
// In detectSessionState():
unified := unifyFromStatedetect(result.State)  // called once, at aggregator write time
session.State = string(unified)
```

`UnifyStatus()` in `pkg/tui/components.go` then only needs to handle: ic dispatch strings, Intermute agent strings, and the unified values already stored in Session.State. Reduces the mapping fan-in from five vocabularies to three.

---

### P2 — enrichWithKernelState() is a shared write point for three parallel slices

**Dependency graph from brainstorm:**

```
Slice 1 (project discovery)  ──→  Slice 2 (agent monitoring)
                             ──→  Slice 3 (run progress)
                             ──→  Slice 4 (dashboard metrics)
```

The graph models data dependency correctly. What it does not model: Slices 2, 3, and 4 all write into `enrichWithKernelState()` and into `aggregator.State`. If they are developed in parallel (as recommended in the execution order), each developer adds fields to State and calls inside the same function concurrently. This is a merge conflict trap.

**Recommendation:**

Define the complete `enrichWithKernelState()` function with stub implementations for all three callers as part of Slice 1 delivery:

```go
func (a *Aggregator) enrichWithKernelState(ctx context.Context, projects []discovery.Project) *KernelState {
    ks := &KernelState{
        Runs:       make(map[string][]icdata.Run),
        Dispatches: make(map[string][]icdata.Dispatch),
        Events:     make(map[string][]icdata.Event),
    }
    for _, p := range projects {
        if !p.HasIntercore {
            continue
        }
        a.enrichRuns(ctx, p, ks)       // Slice 2 fills this
        a.enrichDispatches(ctx, p, ks) // Slice 2 fills this
        a.enrichEvents(ctx, p, ks)     // Slice 3 fills this
        a.enrichMetrics(ctx, p, ks)    // Slice 4 fills this
    }
    return ks
}
```

Each slice fills one method stub. No merge conflicts. This should be a Slice 1 acceptance criterion.

---

### P2 — Refresh() synchronous chain will exceed the 2-second cycle budget with N projects

**File:** `internal/bigend/aggregator/aggregator.go`, Refresh() steps

Current Refresh() is fully synchronous. Adding `enrichWithKernelState()` in the same chain means per-project ic execs block state delivery. F1–F4 each add at least one ic subprocess call per kernel-aware project:

- F1: `ic run list --active --json` (FetchRuns)
- F2: `ic dispatch list --json` (FetchDispatches)
- F3: `ic events tail --all --limit=50` (FetchEvents)
- F4: metrics computed from F1+F2 results (no additional exec)

With 5 projects: 3 execs × 50ms × 5 projects = 750ms added to a synchronous chain that already runs loadAgents (one HTTP + N HTTP calls), loadTmuxSessions (tmux exec + statedetect), and filesystem scan. The brainstorm's open question 1 acknowledges this but underestimates the call count (estimates 1 ic call per project; the feature set requires 3).

**Recommendation:**

Run per-project kernel enrichment concurrently inside `enrichWithKernelState()` using a bounded worker pool. A semaphore of 5 concurrent goroutines is appropriate given the expected project count:

```go
sem := make(chan struct{}, 5)
var wg sync.WaitGroup
for _, p := range kernelProjects {
    wg.Add(1)
    go func(proj discovery.Project) {
        defer wg.Done()
        sem <- struct{}{}
        defer func() { <-sem }()
        // per-project ic calls with per-project deadline
        pctx, cancel := context.WithTimeout(ctx, 800*time.Millisecond)
        defer cancel()
        a.enrichProject(pctx, proj, ks)
    }(p)
}
wg.Wait()
```

This is infrastructure work that belongs in Slice 1. Retrofitting concurrency after Slices 2–4 add more execs per project is significantly more expensive.

---

### P2 — F7 KernelEvent enum placed in pkg/signals conflicts with existing signal package purpose

**File:** `pkg/signals/agent_signal.go` (existing); proposed `pkg/signals/kernelevents.go` (F7)

`pkg/signals` contains: cross-tool signal types (research/competitor alerts), bracket-signal parsing infrastructure, and a full broker/server/client for cross-tool communication. These are runtime signaling concerns — events that fire in real time across tools.

KernelEvent (F7) is a classification enum for historical ic database events: `PhaseAdvance`, `GateCheck`, `DispatchSpawned`, etc. These are record types — categories of things already stored in the intercore SQLite DB. Their change driver is ic schema evolution, which is independent of the signals broker protocol.

Placing KernelEvent in `pkg/signals` means ic schema changes require modifying a package imported by the signal server, broker, and parse infrastructure — none of which need to know about phase transitions.

**Recommendation:**

Place `KernelEvent` in `internal/icdata/` alongside the other ic data types (per the P1 boundary recommendation). If the enum is needed by `pkg/tui` for rendering, export it through the icdata package. `pkg/signals` should remain scoped to real-time cross-tool signaling.

---

## Decision Validation

| PRD Decision | Assessment |
|---|---|
| Additive enrichment strategy | Correct — safe rollback, no breakage. Validated. |
| Exec-based ic CLI (no direct SQLite) | Correct — decoupled from schema. Validated. |
| Projects as primary navigation axis | Correct — preserves mental model. Validated. |
| Unified event stream with source tags | Correct in design, but depends on fixing the P0 Activities wipe first. |
| Surface statedetect in TUI | Correct — eliminates redundant capture-pane. Improved by storing UnifiedStatus at write time rather than raw statedetect string. |
| Keep autarch status separate | Correct — different use case, different update frequency. Validated. |
| Vertical slice delivery | Correct — but enrichWithKernelState() shared write point needs P2 stub-out in Slice 1. |

---

## Sequencing Recommendation (revised)

**Before any slice begins:**

1. Fix the Activities wipe-on-refresh bug (P0). This is a 5-line change that unblocks F3 and F5.
2. Extract data types to `internal/icdata` (P1 boundary). This is ~80 lines moved, unblocks aggregator import without Bubble Tea contamination.

**Slice 1 (project discovery) — expanded scope:**

In addition to PRD acceptance criteria, Slice 1 must deliver:
- Complete `enrichWithKernelState()` with per-method stubs (unblocks parallel Slice development)
- Concurrent per-project enrichment with bounded goroutine pool (P2 performance)
- `KernelState` sub-struct in aggregator.State (P1 struct growth)

**Slices 2, 3, 4 — can parallelize** once Slice 1 delivers the stubs.

**F8 (4-state status model):**

- Store `UnifiedStatus` value in `TmuxSession.State` at aggregator write time (eliminates one render-time mapping vocabulary).
- `UnifyStatus()` function in `pkg/tui` handles only ic dispatch strings, Intermute strings, and already-unified session strings.

**F7 (KernelEvent enum):**

- Place in `internal/icdata/kernelevents.go`, not `pkg/signals`.

---

## What Does Not Need Changing

- The `internal/status` Bubble Tea model and pane structs — they serve `autarch status` correctly and need no modifications.
- The `aggregatorAPI` interface in `internal/bigend/tui/model.go` — no new methods needed; kernel data flows through the existing `GetState()` return value.
- The web server's rendering pipeline — kernel data available in `state.Kernel` is additive; existing template paths are unaffected.
- The WebSocket subscription event types — Intermute WebSocket continues unchanged; kernel events enter through the polling path.
