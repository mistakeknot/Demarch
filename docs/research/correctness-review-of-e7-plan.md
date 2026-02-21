# Correctness Review: E7 Bigend Kernel Migration Plan

**Date:** 2026-02-20
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Subject:** `/root/projects/Interverse/hub/autarch/docs/plans/2026-02-20-bigend-kernel-migration-plan.md`
**PRD cross-reference:** `/root/projects/Interverse/docs/prds/2026-02-20-bigend-kernel-migration.md`
**Code base reviewed:**
- `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go`
- `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/kernel.go`
- `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/kernel_test.go`
- `/root/projects/Interverse/hub/autarch/internal/icdata/types.go`
- `/root/projects/Interverse/hub/autarch/internal/icdata/fetch.go`
- `/root/projects/Interverse/hub/autarch/internal/icdata/kernelevents.go`
- `/root/projects/Interverse/hub/autarch/internal/icdata/unifiedstatus.go`

---

## Invariants

The following invariants must hold for the system to be correct:

1. **Activities are append-only across Refresh cycles** — Intermute WebSocket events prepended via `addActivity()` must not be silently discarded by the next `Refresh()` call.
2. **No unsynchronized access to Aggregator fields** — all fields of `Aggregator` written or read from multiple goroutines must be protected by `a.mu` (or an appropriate atomic for scalars).
3. **SyntheticID is globally unique** — `kernel:projectPath:eventID` must never collide across different projects for events with the same integer ID.
4. **Seen-set is consistent** — `seenEvents`/`seenOrder` are only accessed from one goroutine at a time; their LRU state must not be corrupted by concurrent calls.
5. **Bootstrap pre-populates before emit** — historical events must be in the seen-set before they are appended to Activities, so they are never re-emitted on the next poll.
6. **Phase duration reflects current phase** — `time.Time` from the most recent `phase.advance` event must be zero-safe on first render.
7. **Dispatch merge is deterministic** — the join between Intermute agents and kernel dispatches produces no phantom or duplicate rows regardless of data-source timing.

---

## Findings

### F5.1 — RACE: Seen-set (`seenEvents`/`seenOrder`) is accessed without the lock (P0)

**File:** `aggregator.go` lines 449–462, `kernel.go` line 446

The `Aggregator` struct holds `seenEvents map[string]struct{}` and `seenOrder []string` (aggregator.go:121-122). These fields are written inside `Refresh()` at lines 449–462 — outside any lock:

```go
// aggregator.go:449-462 — no lock held at this point
for _, act := range mergedActivities {
    if act.SyntheticID != "" {
        if _, ok := a.seenEvents[act.SyntheticID]; !ok {
            a.seenEvents[act.SyntheticID] = struct{}{}
            a.seenOrder = append(a.seenOrder, act.SyntheticID)
        }
    }
}
for len(a.seenOrder) > 500 {
    oldest := a.seenOrder[0]
    a.seenOrder = a.seenOrder[1:]
    delete(a.seenEvents, oldest)
}
```

`Refresh()` is guarded by `refreshing.CompareAndSwap`, so two `Refresh()` calls cannot overlap. However, the plan states that `enrichWithKernelState()` itself fans out to goroutines that call `kernelEventsToActivities()` and then `mergeActivities()`. The seen-set access happens after those goroutines complete (after `wg.Wait()`), so there is no concurrent map write from the pool itself. That part is safe.

**The real race is with `addActivity()`**, which is called from the Intermute WebSocket event goroutine at any time. `addActivity()` acquires `a.mu.Lock()` to modify `a.state.Activities`. But `Refresh()` reads from `a.state.Activities` under `a.mu.RLock()` (lines 440-443) and then updates `a.seenEvents`/`a.seenOrder` *without any lock*. A concurrent call to `addActivity()` does not touch `seenEvents`/`seenOrder` — so there is no direct map-concurrent-write race there.

However, the plan for F5.2 (bootstrap batch) says the bootstrap call "pre-populates seen-set". If bootstrap is called from a goroutine separate from `Refresh()`, and `Refresh()` is simultaneously mutating the seen-set, then two goroutines would write to `seenEvents` concurrently — a data race the Go race detector will catch and which can silently corrupt the map.

The plan does not specify where bootstrap runs. If it runs during `enrichWithKernelState()` (from the Refresh goroutine) there is no race. If it runs from an `init`-style call that can overlap the first `Refresh()`, there is a race.

**Concrete interleaving:**

```
Goroutine A (startup bootstrap): reads seenEvents, writes seenEvents["kernel:/p1:1"]
Goroutine B (Refresh ticker fires before bootstrap completes):
  mergeActivities() returns "kernel:/p1:1" as new
  writes seenEvents["kernel:/p1:1"] simultaneously with A
  → concurrent map write → runtime panic or silent corruption
```

**Fix:** Protect all accesses to `seenEvents`/`seenOrder` under `a.mu`. Move the seen-set update block inside the `a.mu.Lock()` that already wraps the state assignment (lines 465-476). Bootstrap must run under the same lock or be completed before `Refresh()` is started.

---

### F5.1 — DESIGN GAP: LRU cap is 500, plan says "limit * 10" (P1)

**File:** `aggregator.go` lines 458-462

The plan (F5.1) says the seen-set is "capped at `limit * 10` with LRU eviction." The `mergeActivities()` call uses `limit=100`, so the intended cap is 1,000 entries. The actual code evicts when `len(seenOrder) > 500`.

This is a silent correctness discrepancy: the seen-set discards entries twice as fast as the plan specifies. If the viewport holds 100 activities and refreshes 50-event batches, a cap of 500 will cause entries to be evicted while they may still be in the viewport. Evicted entries become "new" on the next poll, producing re-emission of already-displayed events.

The LRU implementation is also not truly LRU — it's FIFO by insertion order. A true LRU would promote entries on access. For a dedup seen-set (checked but never promoted), FIFO is acceptable in practice, but the plan says "LRU" and should clarify this is insertion-order eviction.

**Fix:** Set the eviction threshold to `100 * 10 = 1000` (or parameterize based on the `maxActivities` argument). Add a comment that this is insertion-order eviction, not access-order LRU.

---

### F2.3 — RACE: `mergeAgentDispatches()` joins two data sources with different update frequencies (P1)

**File:** plan section F2.3, `aggregator.go`

The plan says: "When an Intermute agent name matches a kernel dispatch agent name, merge into a single display row showing both inbox state (from Intermute) and lifecycle data (from kernel)."

The two data sources are updated at different times and under different lock disciplines:

- **Intermute agents** (`a.state.Agents`): updated by `Refresh()` under `a.mu.Lock()` every 2s, and also by `refreshForEvent("agent.*")` goroutines triggered by WebSocket events.
- **Kernel dispatches** (`a.state.Kernel.Dispatches`): updated by `Refresh()` under `a.mu.Lock()` every 2s.

A `Refresh()` cycle reads agents and kernel dispatches, and then the proposed `mergeAgentDispatches()` will join them. Since both are read from the same snapshot of `a.state` under one `GetState()` call, this join is safe at the rendering layer.

**The problem is the agent refresh goroutine.** In `refreshForEvent()` at lines 315-325:

```go
case strings.HasPrefix(eventType, "agent.") ||
    strings.HasPrefix(eventType, "message."):
    go func() {
        ctx, cancel := withTimeoutOrCancel(context.TODO(), timeout.HTTPDefault)
        defer cancel()
        agents := a.loadAgents(ctx)
        a.mu.Lock()
        a.state.Agents = agents
        a.state.UpdatedAt = time.Now()
        a.mu.Unlock()
    }()
```

This goroutine writes `a.state.Agents` independently of `a.state.Kernel`. A consumer calling `GetState()` between this goroutine's lock release and the next `Refresh()` will see a state where `Agents` is current (just fetched from Intermute) but `Kernel.Dispatches` is up to 2s stale. The merge produces a row with fresh inbox data but stale lifecycle data, or vice versa. This is a TOCTOU on the composite view.

This is not a race condition in the Go memory model sense (the read is correctly locked), but it is a logical consistency gap: the merged display row reflects two different points in time. For a dashboard this is tolerable if the staleness window is short (it is, 2s). However, if an operator sees "agent X: active in inbox, dispatch: done" and acts on it, they could be misled.

**The more serious version:** if `mergeAgentDispatches()` is implemented as a mutating aggregator method that updates state (rather than a view-layer pure function), and it runs from a goroutine, it could race with `Refresh()`.

**Fix:** Implement `mergeAgentDispatches()` as a pure function over a state snapshot (no mutation of `a.state`). Call it from the TUI/web render path, not from within `Refresh()`. Document that the merged view is a best-effort join of the most recent snapshot; no sub-second consistency is promised.

---

### F3 — SyntheticID collision across projects (P1)

**File:** `kernel.go` lines 129

The SyntheticID format is:

```go
synID := fmt.Sprintf("kernel:%s:%d", projPath, ev.ID)
```

This is `kernel:/absolute/project/path:eventID`. Since `projPath` is the full filesystem path and `ev.ID` is an `int64`, this key is globally unique as long as two projects have different paths. Two projects cannot share an absolute path, so collision is impossible by construction.

However, there is a subtlety: the discovery scanner canonicalizes paths via `filepath.EvalSymlinks()` (per the F1 acceptance criteria). If the aggregator stores the canonical path but the event's `ProjectDir` field (from `ic` output) contains the original symlink path, the keys will diverge.

For example:
- Scanner path (canonical): `/root/projects/Autarch`
- `ic` output `project_dir`: `/home/mk/projects/autarch` (a symlink to the same location)
- SyntheticID from kernel: `kernel:/home/mk/projects/autarch:42`
- Key used in seen-set: stored under canonical path
- Result: the dedup check misses, the event is re-emitted every refresh cycle

**Fix:** Normalize `projPath` through `filepath.EvalSymlinks()` at the point where `SyntheticID` is constructed in `kernelEventsToActivities()`. This must use the same canonicalization as the scanner. Add a test that covers symlinked project paths.

The PRD acceptance criterion for F3 says the composite key is `source + ":" + projectPath + ":" + eventID`. It does not specify whether `projectPath` is canonical. This should be made explicit.

---

### F6.1 — Nil/zero time on first render for phase duration (P2)

**File:** plan section F6.1

The plan says:

> Phase duration derived from most recent `phase.advance` event timestamp via `ic run events --json`.

On the very first render cycle, the events may not yet have been fetched. The sequence is:

1. `Refresh()` starts — `enrichWithKernelState()` begins
2. TUI render tick fires (60fps) — tries to display phase duration
3. `enrichEvents()` has not completed yet
4. `ks.Events[projectPath]` is empty or the prior cycle's data
5. The code that computes phase duration searches for the most recent `phase.advance` event in the events list
6. If the list is empty, it finds nothing

The plan does not specify a fallback. Two outcomes are possible:

- **Zero time.Time**: `time.Time{}` (year 0001). `time.Since(zero)` returns ~2024 years. If this value is passed to a duration color function, the run will display as red (>4h) on first render. This is a misleading false positive that vanishes on the next refresh.
- **Panic**: if the code does `events[0]` without bounds-checking (likely in new code following the pattern), it will panic on the render goroutine.

**Concrete scenario:** operator opens Bigend immediately after startup. Every run shows red phase duration for up to 2 seconds. A nervous operator may think something is wrong.

**Fix:** In the phase-duration calculation, return `""` (empty/dash) when no `phase.advance` event is found in the event list. The PRD acceptance criterion already specifies `--` for completed runs; apply the same treatment to runs with no event data yet. Add an explicit zero-time guard.

---

### F5.2 — TOCTOU between bootstrap and first Refresh cycle (P1)

**File:** plan section F5.2, `aggregator.go`

The plan says:

> On first `enrichWithKernelState()` call (or when Aggregator starts), bootstrap with historical events. Pre-populate seen-set before emitting to Activities.

The exact sequencing is not specified. Two interpretations:

**Interpretation A (safe):** Bootstrap runs as the first step of the first `enrichWithKernelState()` call, synchronously, before any events are appended to `Activities`. The pileup guard (`refreshing.CompareAndSwap`) prevents a second `Refresh()` from running concurrently, so there is no window between bootstrap and first event emission.

**Interpretation B (racy):** Bootstrap is called from `New()` or from a startup goroutine before the first `Refresh()` ticker fires. The startup bootstrap completes; `Refresh()` fires; `Refresh()` calls `enrichWithKernelState()`; the first refresh does NOT re-bootstrap; events are fetched fresh and checked against the seen-set. This is also safe if bootstrap is complete before `Refresh()` starts.

**The actual risk** is if bootstrap is called from a goroutine that runs concurrently with the first `Refresh()`. Then:

```
T=0: New() spawns bootstrap goroutine
T=0: First Refresh() timer fires immediately (e.g., ticker with zero initial delay)
T=1: Refresh() calls enrichWithKernelState(), fetches events
T=1: bootstrap goroutine also writing to seenEvents
T=1: concurrent write to seenEvents map → data race
```

Additionally, there is a subtlety in the fetch: `enrichEvents()` fetches the last 50 events. Bootstrap also fetches the last N events. If they run concurrently (or if bootstrap runs with a larger limit), they may fetch overlapping event sets and populate the seen-set with different subsets. This creates a window where some events are in bootstrap's seen-set but not yet in `Refresh()`'s local merge scope.

**Fix:** Bootstrap must be completed synchronously before the first `Refresh()` is started, OR bootstrap must be integrated as the first step of `enrichWithKernelState()` with a boolean flag (`a.bootstrapped atomic.Bool`) to skip on subsequent calls. The flag approach is cleaner and avoids any startup ordering dependency.

```go
func (a *Aggregator) enrichWithKernelState(ctx context.Context, projects []discovery.Project) *KernelState {
    // On first call, use a larger historical window and mark all events as seen
    // without emitting them to Activities.
    isBootstrap := a.bootstrapped.CompareAndSwap(false, true)
    limit := 50
    if isBootstrap {
        limit = 200 // or configurable
    }
    // ...
    // After populating seenEvents with historical events:
    if isBootstrap {
        return ks // return state but do NOT merge into Activities
    }
    // Normal path: merge new events (deduped by seenEvents)
}
```

This guarantee is not stated in the plan and must be made explicit.

---

### F5.2 — Bootstrap seen-set write is unprotected if called separately (P0 if Interpretation B)

**File:** aggregator.go, implicit in plan

If bootstrap writes to `seenEvents` from outside `Refresh()` (e.g., a `Bootstrap()` method called from `main.go`), and the first `Refresh()` concurrently reads/writes `seenEvents`, this is an unambiguous data race on the map. Go's runtime will detect and terminate the program under `-race`.

This is a P0 (process crash) if bootstrap runs concurrently with any `Refresh()` tick. The plan must nail down the execution model: bootstrap is either synchronous within the first `Refresh()`, or it must acquire `a.mu` before touching `seenEvents`.

---

### Missing: context propagation to seen-set bootstrap goroutine (P2)

**File:** plan section F5.2

The plan does not address what happens when the Aggregator is shut down while bootstrap is in flight. The PRD resolved decision says: "Use `a.wsCtx` (not `context.TODO()`) for partial-refresh goroutines; `sync.WaitGroup` for clean shutdown."

If bootstrap is implemented as a goroutine in `enrichWithKernelState()`, it inherits the per-project 3s timeout context. That is correct.

If bootstrap is a separate startup goroutine, it needs its own cancellation handle tied to the Aggregator lifecycle. The plan does not mention this. An orphaned bootstrap goroutine after Aggregator shutdown would write to a garbage-collected `seenEvents` map after the Aggregator is freed — undefined behavior in Go (GC will collect, but the goroutine leak is real until it finishes).

**Fix:** Any bootstrap goroutine must be started with `a.wsCtx` and tracked with a `sync.WaitGroup` that is drained during shutdown.

---

### Missing: `mergeActivities()` builds a local `seen` map every call (P2, performance)

**File:** `kernel.go` lines 147-178

Every call to `mergeActivities()` allocates a new `seen` map seeded from `existing`. Since `Refresh()` runs every 2s and `existing` can be up to 100 entries, this is 100 map inserts per call. At 60fps this is not called on render — it is called once per Refresh, so the allocation is bounded and acceptable.

However, the Aggregator already maintains `seenEvents` as a persistent seen-set. `mergeActivities()` rebuilds this seen-set from scratch every call from `existing`, then the caller updates `a.seenEvents` from the merged result. This creates a redundant dual-tracking of the same information. The persistent `a.seenEvents` is the canonical dedup state; the local `seen` map in `mergeActivities()` is reconstructed from `existing` (which itself was already deduped). This is not a correctness bug but a design confusion that makes the code harder to reason about.

**Fix:** Remove the local `seen` map from `mergeActivities()` and instead pass `a.seenEvents` as a parameter. Simplify: dedup only against the persistent seen-set, not against `existing`. This eliminates the N-entry scan of `existing` on every call.

---

### F6.1 — Run duration derived from `Run.CreatedAt` vs phase entry time (P2)

**File:** plan section F6.1, `icdata/types.go`

The plan says phase duration is derived from "the most recent `phase.advance` event timestamp." This requires a separate `ic run events` call per run (to find the last `phase.advance` event and its timestamp). The plan does not include this extra fetch in the enrichment pipeline.

Currently `enrichEvents()` fetches all events for a project with `--all --limit=50`. If a run has been through many phase transitions, the 50-event limit may not include the most recent `phase.advance` for an older run. The duration computed for those runs would use the wrong event, or no event at all.

`Run` struct has `UpdatedAt int64` (epoch seconds) which likely reflects the most recent state change, but it is not explicitly documented as the phase-entry time. Using `UpdatedAt` as a proxy would avoid the event-lookup, but could give wrong durations when runs are updated for reasons other than phase advances.

**Fix:** Either increase the event limit for phase-advance lookup, or add a `PhaseEnteredAt` field to the `Run` struct (from `ic run status --json` if available), or accept that the duration is approximate and document the 50-event limit as a known accuracy constraint.

---

### F2.3 — Agent name matching is case-sensitive string equality (P2)

**File:** plan section F2.3

The plan says: "If agent name matches dispatch agent name (same string), merge into single display row."

"Same string" means case-sensitive byte-for-byte equality. If an Intermute agent registers as `"Claude-Reviewer"` and the kernel dispatch records the name as `"claude-reviewer"` (because `ic` normalizes to lowercase), the merge produces two separate rows for the same entity. The operator sees apparent duplication.

This is not a data corruption issue, but it produces a misleading display and defeats the purpose of the merge. There is no test for this case.

**Fix:** Define canonical normalization for the join key (e.g., `strings.ToLower(strings.TrimSpace(name))`). Apply it at both sources before comparison. Add a test with mismatched case.

---

### Missing: Partial enrichment failure leaves stale `Dispatches`/`Events` in merged state (P2)

**File:** `kernel.go` lines 73-96

When `enrichRuns()` fails for a project, the goroutine returns early:

```go
runs, err := a.enrichRuns(projCtx, proj.Path)
if err != nil {
    slog.Warn("kernel enrichment: runs failed", "project", proj.Path, "error", err)
    mu.Lock()
    ks.Metrics.KernelErrors[proj.Path] = err.Error()
    mu.Unlock()
    return  // <-- Dispatches and Events for this project are never set
}
```

This is correct: if runs fail, dispatches/events are also skipped. The project is excluded from `ks.Runs`, `ks.Dispatches`, and `ks.Events`. The caller gets a consistent view (all-or-nothing per project).

However, `enrichDispatches()` and `enrichEvents()` can fail independently without aborting the project goroutine:

```go
dispatches, err := a.enrichDispatches(projCtx, proj.Path)
if err != nil {
    slog.Warn("kernel enrichment: dispatches failed", "project", proj.Path, "error", err)
    // CONTINUES — dispatches is nil, stored as nil
}

events, err := a.enrichEvents(projCtx, proj.Path)
if err != nil {
    slog.Warn("kernel enrichment: events failed", "project", proj.Path, "error", err)
    // CONTINUES — events is nil, stored as nil
}

mu.Lock()
ks.Runs[proj.Path] = runs        // has data
ks.Dispatches[proj.Path] = dispatches  // nil
ks.Events[proj.Path] = events    // nil
mu.Unlock()
```

This results in: runs showing 3 active runs, dispatches showing 0, events empty. The operator sees a project that appears to have active work but no dispatches or events. This is not obviously a fetch failure — it looks like there are no dispatches. The warning badge (`!`) only appears when `KernelErrors[proj.Path]` is set, which only happens on `enrichRuns()` failure.

**Fix:** When `enrichDispatches()` or `enrichEvents()` fail, add the error to `ks.Metrics.KernelErrors[proj.Path]` (possibly with a suffix to indicate which call failed). This ensures the warning badge appears when any part of the enrichment fails, not only when runs fail.

---

### Missing: `parseEventTimestamp()` returns `time.Now()` on parse failure (P2)

**File:** `kernel.go` lines 181-189

```go
func parseEventTimestamp(ts string) time.Time {
    if t, err := time.Parse(time.RFC3339, ts); err == nil {
        return t
    }
    if t, err := time.Parse("2006-01-02T15:04:05Z07:00", ts); err == nil {
        return t
    }
    return time.Now()  // <-- fallback
}
```

When the `ic` CLI returns an event with a timestamp in an unexpected format (e.g., SQLite's `DATETIME` default format `"2006-01-02 15:04:05"`), parsing silently falls back to `time.Now()`. The event appears as "just happened" regardless of its actual time. In `mergeActivities()`, which sorts by time descending, this makes stale events float to the top of the feed. If this happens consistently (new `ic` version, different timestamp format), the activity feed shows a random mix of stale events sorted as if they are current.

The RFC3339 fallback is redundant — `"2006-01-02T15:04:05Z07:00"` is a subset of RFC3339 format. The actual missing case is SQLite's space-separated datetime format.

**Fix:** Add `time.Parse("2006-01-02 15:04:05", ts)` as a third attempt. Return `time.Time{}` (zero time) on complete parse failure, not `time.Now()`. Callers that need to display a time should check `t.IsZero()` and show a dash. This makes parse failures visible rather than silently misrepresenting event timing.

---

### F8.1 — `UnifiedStatus` iota ordering breaks zero-value semantics (P2)

**File:** `icdata/unifiedstatus.go` lines 9-16

```go
const (
    StatusActive  UnifiedStatus = iota // 0
    StatusBlocked                      // 1
    StatusWaiting                      // 2
    StatusDone                         // 3
    StatusErr                          // 4
    StatusUnknown                      // 5
)
```

The zero value of `UnifiedStatus` is `StatusActive` (0). Any newly-allocated `TmuxSession`, `Run`, or `Dispatch` struct will have `UnifiedState: StatusActive` by default — before any state detection runs. This violates the invariant stated in the PRD: "Unknown/empty status maps to Unknown display state — never to Active."

For example, `TmuxSession` has `UnifiedState icdata.UnifiedStatus` (aggregator.go:55). When a session is first constructed in `loadTmuxSessions()` before `detectSessionState()` runs, its `UnifiedState` is 0 = `StatusActive`. If the TUI renders before `detectSessionState()` completes (which can happen when a new session appears mid-refresh), the session briefly shows as "active" when it should show as "unknown."

**Fix:** Reorder the constants so `StatusUnknown = 0` is the zero value. This makes uninitialized structs display correctly without requiring explicit initialization. Update all tests that rely on the current iota ordering.

---

### Missing PRD acceptance criteria not covered by the plan (P1, completeness)

Cross-referencing the PRD against the plan reveals these uncovered acceptance criteria:

**F1 (iv-lemf):**
- "Scanner updates both WalkDir trigger (line 103) and inclusion gate (line 111) atomically — test covers `.clavain`-only project appearing in scan results" — the plan mentions the scanner but does not specify test coverage for the atomic update of both gates.
- "Projects with only `.clavain/` (no `.gurgeh`/`.coldwine`/`.pollard`) appear in project list" — the plan mentions this but there is no test for it in `kernel_test.go`.

**F2 (iv-9au2):**
- "Status icons use `pkg/tui.StatusIndicator` with the unified status model (F8)" — this dependency is implicit in the plan but not stated as a prerequisite.

**F3 (iv-gv7i):**
- "Activity timestamps display correctly (HH:MM:SS format in TUI)" — no test covers timestamp rendering.

**F5 (iv-4c16):**
- "Intermute WebSocket events continue flowing into the same stream" — the plan describes this architecturally but there is no integration test that verifies the merged stream contains both kernel and Intermute events simultaneously.
- "Filtering supported: by event type, by project, by source (kernel/intermute)" — filter logic is not described in the plan at all (F5.3 only mentions it exists).

**F6 (iv-4zle):**
- "Focus ring and key shortcuts documented in Bigend help text (check for conflicts with existing CommonKeys in pkg/tui/)" — the plan mentions Tab/h/l but does not require a conflict check.
- "When no run is selected, full pane shows legacy view (sessions, agents)" — the plan covers the narrow fallback but does not explicitly cover the no-selection state.
- "Selected run preserved in model state and restored when terminal widens" — the plan mentions this in F6.4 but does not specify where in model state the selection is persisted.

**F8 (iv-xu31):**
- PRD: "Mapping function `UnifyStatus(rawStatus string) UnifiedStatus` in `pkg/tui/components.go`" — actual implementation is in `internal/icdata/unifiedstatus.go`. This package split differs from the PRD, but the decision note in the PRD says "store UnifiedStatus at aggregator write time" which requires `icdata` to have the type, so `icdata` is the right location. The PRD acceptance criterion for the `pkg/tui/components.go` location should be updated or the plan should note the divergence.

---

## Summary of Findings

| ID | Severity | Description |
|----|----------|-------------|
| R1 | P0 | `seenEvents`/`seenOrder` written without lock; bootstrap goroutine racing with Refresh crashes the map |
| R2 | P0 | Bootstrap can run concurrently with first Refresh, producing concurrent map write (if bootstrap is a separate goroutine) |
| R3 | P1 | LRU cap is 500, plan says 1000 (`limit * 10`); entries evicted prematurely, causing re-emission of deduped events |
| R4 | P1 | TOCTOU between Intermute agent refresh goroutine and Kernel state; merged dispatch view reflects two different points in time |
| R5 | P1 | SyntheticID symlink mismatch: canonical path vs. ic-reported path can diverge, causing dedup to miss every cycle |
| R6 | P1 | Bootstrap pre-population guarantee not stated; plan leaves the execution model ambiguous, enabling the race described in R2 |
| R7 | P2 | Zero/nil time on first render for phase duration: runs show red (>4h) before first event fetch completes |
| R8 | P2 | `parseEventTimestamp()` returns `time.Now()` on parse failure; stale events appear at the top of the feed |
| R9 | P2 | `UnifiedStatus` zero value is `StatusActive`, not `StatusUnknown`; new structs show "active" before state detection runs |
| R10 | P2 | Partial enrichment failure (dispatches/events) does not set KernelErrors; warning badge never appears for these failures |
| R11 | P2 | Agent name join is case-sensitive; mismatched capitalization produces duplicate rows for the same entity |
| R12 | P2 | Several PRD acceptance criteria have no corresponding test coverage in the plan |
| R13 | P2 | `mergeActivities()` allocates a local seen map from `existing` every 2s; redundant with persistent `a.seenEvents` |

### Priority order for implementation team

1. **R1 and R2 first** — lock the seen-set before any code that accesses it; nail down bootstrap execution model. These are the only P0s and will produce detectable crashes under `-race` or concurrent load.
2. **R5** — symlink path normalization in `SyntheticID` construction; testable and has a clear fix.
3. **R6** — document and enforce the bootstrap sequencing invariant; this is mostly a design-clarity fix.
4. **R3** — fix the cap to 1000; one-line change.
5. **R9** — reorder `UnifiedStatus` iota; small change but affects every consumer of the zero value.
6. **R7, R8, R10, R11** — these are observable but not crash-inducing; address in the feature slice where they become visible.
7. **R4** — document the consistency model; not fixable without a more complex snapshot mechanism.
8. **R12, R13** — test coverage gaps and design clarity; address in code review.
