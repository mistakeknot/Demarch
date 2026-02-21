# Performance Review: E7 Bigend Kernel Migration Plan

**Date:** 2026-02-20
**Plan file:** `hub/autarch/docs/plans/2026-02-20-bigend-kernel-migration-plan.md`
**Reviewer role:** Flux-driven Performance Reviewer
**Sources read:**
- `internal/bigend/aggregator/aggregator.go`
- `internal/bigend/aggregator/kernel.go`
- `internal/icdata/fetch.go`
- `internal/bigend/tui/model.go` (all 1493 lines)
- `internal/bigend/tui/pane.go`
- `internal/bigend/web/server.go`
- `internal/bigend/aggregator/kernel_test.go`

---

## Performance Profile (Established)

- Workload type: interactive developer TUI (Bubble Tea, always-on)
- Render tick: 2-second poll triggers refresh, Bubble Tea renders at up to 60fps on each model update
- Interaction budget: keystrokes must feel instant (<16ms visible latency); poll results can arrive asynchronously
- Main resource constraints: single developer machine, local disk (SQLite), subprocess fork cost
- Known baseline: `Refresh()` already runs filesystem scan, tmux sessions, Intermute REST, Gurgeh/Pollard stats

No explicit SLOs exist in the codebase. Practical targets used for this review:
- Refresh cycle: complete within the 2s window, no pileup
- Render tick: View() < 5ms
- Subprocess overhead: must not saturate the refresh window at expected project counts

---

## Finding 1 — Subprocess overhead at scale

**Severity: P1 (will bite at N >= 10 projects)**

### What the code does

`enrichWithKernelState()` in `kernel.go` iterates all `HasIntercore` projects and for each launches three sequential `os/exec` subprocesses via `RunIC()`:

```go
// kernel.go lines 73-95
runs, err := a.enrichRuns(projCtx, proj.Path)
...
dispatches, err := a.enrichDispatches(projCtx, proj.Path)
...
events, err := a.enrichEvents(projCtx, proj.Path)
```

Each of these calls `exec.CommandContext(ctx, "ic", ...)` and waits for the child to complete. The `ic` binary opens SQLite, executes a query, serializes JSON, and exits. The semaphore caps parallelism at 5, so with 5 projects all three calls per project run sequentially within the goroutine — that is 3 subprocesses in series per goroutine, not 3 per project in parallel.

**Cost model at 5 projects:**

| Component | Per subprocess | 5 projects x 3 subprocesses |
|-----------|---------------|----------------------------|
| fork+exec | ~2-5ms | 30-75ms |
| SQLite open (WAL check, shared cache miss) | ~2-10ms | 30-150ms |
| Query + serialize | ~0.5-2ms | 7.5-30ms |
| **Total pessimistic** | ~17ms | **~255ms** |

At 5 projects running over 2 seconds, this is workable. But:

- At 10 projects, the semaphore of 5 means two batches of goroutines. Each batch takes ~255ms. Total: ~510ms. Still within 2s.
- At 20 projects: ~1020ms. The refresh cycle can barely complete before the next tick fires, which the pileup guard catches — but the user will see the dashboard become stale.
- The per-project timeout is 3s. If even one `ic` call blocks (e.g., another process holds a WAL write lock on SQLite), that goroutine occupies a semaphore slot for 3 seconds, starving other projects for the entire refresh window.

**Who feels it:** The user notices staleness when projects > ~15. The pileup guard prevents cascading goroutine leaks but the symptom is that the "Updated X ago" footer counter stops advancing and kernel data freezes.

**Fix options (in order of impact):**

1. Combine the three `ic` calls into one: add an `ic kernel-snapshot --json` subcommand to `ic` that returns runs, dispatches, and events in a single JSON blob. One fork per project instead of three. This is the correct long-term fix and reduces per-project cost by 66%.

2. If the `ic` binary cannot be changed short-term, run the three fetch goroutines in parallel within each project goroutine using a per-project `sync.WaitGroup`. This keeps the semaphore semantics but triples effective throughput per slot.

3. Add `--timeout` flag pass-through to `ic` to avoid SQLite lock stalls consuming the full 3s per slot.

**Confidence:** High. Fork/exec cost is measurable. Validate with `time go test -run TestEnrichWithKernelState -v` using a mock that records timing.

---

## Finding 2 — seenEvents LRU has a data race on the Aggregator struct

**Severity: P0 (data race, correctness issue with performance consequence)**

### What the code does

`seenEvents` and `seenOrder` are fields on `Aggregator` (lines 121-122 in `aggregator.go`):

```go
type Aggregator struct {
    ...
    seenEvents map[string]struct{}
    seenOrder  []string
    ...
}
```

They are written in `Refresh()` (lines 449-462 in `aggregator.go`):

```go
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

This write happens **outside** both the `a.mu.RLock()` (line 440) and `a.mu.Lock()` (line 465) sections. The `Refresh()` pileup guard prevents two `Refresh()` calls from running simultaneously, but `addActivity()` (called from `handleIntermuteEvent()`, which runs in a separate goroutine from WebSocket events) also accesses `a.state.Activities` under `a.mu.Lock()`. The real race is that `seenEvents`/`seenOrder` have no lock at all — `Refresh()` reads and writes them without holding `mu`, and if `refreshForEvent()` triggers a concurrent targeted refresh goroutine that eventually calls something touching `seenEvents`, a data race is possible.

More practically: the plan says to cap at `limit * 10`. The current code caps at 500 regardless of the per-call limit. The plan's formula (50 events/project x 5 projects = 250 events, x10 = 2500 entries) is more expensive than the current 500-entry cap by 5x.

**Who feels it:** If go race detector is enabled during development or CI (`go test -race ./internal/bigend/...`), this will flag. In production, the consequence is map corruption or slice corruption under concurrent WebSocket event delivery.

**Fix:** Move `seenEvents` and `seenOrder` updates inside the `a.mu.Lock()` block at line 465, or give them their own dedicated mutex. The current pattern of reading existing activities under `a.mu.RLock()` then writing seenEvents without a lock is the bug.

**Confidence:** High. The code structure is unambiguous. Run `go test -race ./internal/bigend/aggregator/...` to confirm.

---

## Finding 3 — mergeActivities allocates a new seen-map every 2s refresh

**Severity: P2 (unnecessary allocation in hot path)**

### What the code does

`mergeActivities()` in `kernel.go` (lines 146-178) is called on every `Refresh()`. It allocates a fresh `map[string]struct{}` seeded with all existing activity IDs on each call:

```go
func mergeActivities(existing, incoming []Activity, maxActivities int) []Activity {
    seen := make(map[string]struct{}, len(existing))
    merged := make([]Activity, 0, len(existing)+len(incoming))
    for _, a := range existing {
        if a.SyntheticID != "" {
            seen[a.SyntheticID] = struct{}{}
        }
        merged = append(merged, a)
    }
    ...
    sort.Slice(merged, ...)
    ...
}
```

At 100 max activities (the cap used in `Refresh()` at line 446), this allocates a map with 100 entries and a slice with 100+ entries on every 2s tick. Additionally `sort.Slice` always runs on the full merged slice even when no new activities arrived, because there is no change detection.

This is not catastrophic (Go's allocator handles small maps well and GC will collect quickly), but there is a simple improvement: the `seenEvents` LRU already exists on the Aggregator specifically to avoid re-building this set. The plan proposes using it for bootstrap dedup (F5.1/F5.2), but the LRU is not currently threaded into `mergeActivities`. If it were, `mergeActivities` could skip the per-call map allocation entirely and use the persistent LRU for O(1) lookup.

**Secondary concern:** The sort runs on all 100 entries every 2s regardless of whether any new activity arrived. A simple "did anything change?" check before sorting would eliminate most sort calls during quiet periods.

**Who feels it:** Not directly visible to users, but contributes to GC pressure in a long-running process. Relevant if other allocations in the refresh path are high.

**Fix:** Check `len(incoming) == 0` before allocating and sorting. When there are no new kernel events, skip merge entirely. For the map, thread the `seenEvents` LRU through as the dedup structure instead of re-building per call.

---

## Finding 4 — renderDashboard() calls GetState() and statusForSession() on every View() tick at 60fps

**Severity: P2 (latency on hot render path)**

### What the code does

`renderDashboard()` in `model.go` at line 1425 begins:

```go
func (m Model) renderDashboard() string {
    state := m.agg.GetState()  // acquires RLock, copies State struct
    ...
    for _, s := range state.Sessions {
        status := m.statusForSession(s.Name)  // may call tmux.DetectStatus
```

`GetState()` acquires `a.mu.RLock()` and returns a copy of the `State` struct. The `State` struct contains:
- `[]discovery.Project` (N projects, each with stat fields)
- `[]Agent`, `[]TmuxSession`, `[]colony.Colony`
- `map[string][]mcp.ComponentStatus`
- `[]Activity` (up to 100)
- `*KernelState` (pointer, but the maps it contains are shared — potentially aliased after copy)

This struct copy happens on **every call to `View()`**, which Bubble Tea calls on every model update. Bubble Tea does not call `View()` at a fixed 60fps; it calls it on every message received. With a 2s tick, this is at most once per 2 seconds for tick messages, but keyboard events, window resize events, and terminal content messages all trigger `View()` too. In practice, during active use `View()` is called dozens of times per second.

The `statusForSession()` call (line 1141) also runs per session per `updateLists()` call, which fires on each `refreshMsg`. It uses a TTL cache, so repeat calls within 2s are fast, but on cache miss it calls `tmux.DetectStatus()` which is a subprocess.

**With the F6 two-pane layout:** `renderDashboard()`, the run list pane, and the detail pane each call `GetState()` independently (based on the plan pattern). That is 3x the struct copy cost per View() call.

**Who feels it:** Users on slow terminals or remote sessions (SSH, Tailscale WireGuard) where every `View()` string is shipped over the network. The struct copy is not the bottleneck today, but the plan adds `KernelState` with maps over all projects, increasing the copy size.

**Fix:** Call `m.agg.GetState()` once at the top of `Update()` when a `refreshMsg` arrives and store the result in the model. `View()` then reads from `m.state` (a plain field, no lock) rather than calling `GetState()` on every tick. This is the canonical Bubble Tea pattern for large state objects. The current code in `renderDashboard()` re-fetches state redundantly on every render.

---

## Finding 5 — F3 mergeActivities grows unbounded across refreshes (existing bug, E7 accelerates it)

**Severity: P1 (memory accumulation over long sessions)**

### What the code does

`mergeActivities()` is capped at `maxActivities` (called with 100 in `Refresh()`), so the returned slice is bounded. However, the *existing* activities passed in come from `a.state.Activities`, which is written back as `mergedActivities`. The cap is applied after sorting and slicing, so the top 100 most-recent activities survive.

This is actually correct for the Activities slice itself. The bug is elsewhere: the `seenEvents` LRU (capped at 500 in the current code) only tracks SyntheticIDs of activities that passed through `mergeActivities`. But kernel events arrive with IDs formatted as `kernel:$path:$eventID`. If `ic events tail --limit=50` returns the same 50 events every refresh cycle (because no new events occurred), `mergeActivities` deduplicates them correctly via the seen-set built fresh each call. The LRU is populated but not used for dedup inside `mergeActivities`.

The plan introduces F5.2 "bootstrap batch" to pre-populate the seen-set so historical events don't look new. Once that is in, the `seenEvents` LRU and the per-call `seen` map in `mergeActivities` serve different purposes with an unclear ownership model. This will be confusing to maintain and could lead to double-dedup bugs or the LRU failing to prevent re-emission.

**Who feels it:** Users of the event stream after long sessions (hours). Activity count stays bounded at 100, but the terminal content updates every 2s as kernel events re-merge, causing unnecessary re-renders and string allocations.

**Fix:** At F5 implementation time, clarify the dedup contract: use the persistent LRU as the canonical seen-set and eliminate the per-call `seen` map inside `mergeActivities`. The function should be `appendNewActivities(existing, incoming, seenLRU, max)` — only check the LRU, add new IDs to the LRU, sort only if appended, and truncate.

---

## Finding 6 — Web templates are parsed at startup and executed on every request (acceptable, one note)

**Severity: P3 (informational)**

### What the code does

In `server.go` `NewServer()` (lines 83-99), templates are parsed once at startup from embedded FS and stored in `s.templates`. Each HTTP request calls `s.render()` which calls `tmpl.ExecuteTemplate()` on the pre-parsed template.

This is the correct pattern. Template execution is not free — for the dashboard with `KernelState` data (maps over projects, dispatches, events), the template range loops will iterate all data on every page load. But at developer-tool scale (one to a few browser tabs, on-demand refresh), this is not a problem. Template execution is fast for data sets of this size.

**One note:** `handleDashboard` calls `s.agg.GetState()` which acquires `RLock` and copies the full State struct including `KernelState`. If KernelState grows large (many projects, many events per project), this copy cost will be felt on every web request. Consider passing `state.Kernel` as a pointer in the template data rather than embedding it in a full State copy, if the web handler grows more complex.

No action required for current plan scope.

---

## Finding 7 — F6 three-pane layout rendering and lipgloss Width() calls

**Severity: P2 (render latency for F6 specifically)**

### What the code does

`renderThreePane()` in `model.go` (lines 1360-1395) calls `lipgloss.Style.Width(n).Render(content)` on three strings:

```go
leftView := leftStyle.Width(leftW).Render(left)
middleView := middleStyle.Width(middleW).Render(middle)
rightView := rightStyle.Width(rightW).Render(right)
return lipgloss.JoinHorizontal(lipgloss.Top, leftView, "  ", middleView, "  ", rightView)
```

`lipgloss.Style.Width()` returns a new `Style` value with the width set (lipgloss styles are value types). When called inside `View()` on every render tick, this creates three new style values per frame. This is fine for two-pane (existing code) but F6 adds a third pane and the plan expands the detail pane to contain dispatches (renderDispatches), events (filtered to selected run), and token summary — each of which iterates over kernel data and builds strings.

**Specific concern in F6.1 run list rendering:** The plan specifies phase duration derived from the most recent `phase.advance` event timestamp. To compute this per run per render, the code would need to scan `KernelState.Events[projPath]` looking for the relevant event. If this scan is done inside `View()` without precomputation, it is O(events) per run per frame — a nested loop in the hot render path.

**lipgloss Width() allocation pattern:** The current code at line 1429 does:
```go
statsStyle := PanelStyle.Copy().Width(m.width/5 - 2)
```
`PanelStyle.Copy()` allocates a new style value. This is called on every `renderDashboard()` invocation. With F4 adding `renderKernelMetrics()` and F6 adding `renderTwoPane()` run-detail panes, each containing their own `Style.Copy().Width()` calls, the per-frame allocation count will grow. Individually small, cumulatively noticeable over millions of frames.

**Fix:** Precompute phase durations during the `updateLists()` / `refreshMsg` handling path and store them in the model. View() should only format pre-computed values, never iterate event slices. For lipgloss styles, define width-parameterized styles as model fields recalculated on `WindowSizeMsg`, not on every render tick.

---

## Finding 8 — F8.3 eliminates redundant capture-pane in render path (good, but verify one case)

**Severity: P3 (informational, affirming the plan)**

F8.3 removes `capture-pane` calls from the TUI render path. Looking at the current code, `statusForSession()` in `model.go` (line 653) uses a TTL cache that calls `m.tmuxClient.DetectStatus(name)` on cache miss. The cache TTL is 2s, matching the refresh interval, so in steady state this is hit once per session per refresh cycle — not in the render path. This is already acceptable.

However, `renderDashboard()` at line 1539 calls `m.statusForSession(s.Name)` inside a loop over `state.Sessions`. This runs during every `renderDashboard()` call (i.e., every time `View()` is called and `activeTab == TabDashboard`). On cache hit (which is the common case after the first render in a 2s window), this is a map lookup — fast. On cache miss (first render after TTL expires, or new session), it calls `DetectStatus` which runs `tmux display-message -p '...'` as a subprocess.

F8.2 replaces this with a read from `TmuxSession.UnifiedState`, which is set by the aggregator at refresh time. This removes the subprocess call from the render path entirely — the correct fix. The plan should also ensure that `renderDashboard()` stops calling `statusForSession()` in the sessions loop (line 1539 path) once F8.2 ships.

No blocking issue. Affirm this as the right approach.

---

## Finding 9 — String building pattern in render methods

**Severity: P3 (minor, future-proofing)**

The plan specifies adding several new render methods: `renderDispatches()`, `renderKernelMetrics()`, and run list rendering. Looking at the existing render methods as patterns:

```go
// model.go line 1517-1524
line := fmt.Sprintf("  %s %s %s %s %s",
    shared.UnifiedStatusSymbol(...),
    LabelStyle.Render(id),
    projName,
    TitleStyle.Render(r.Phase),
    goal,
)
runLines = append(runLines, line)
```

Each `LabelStyle.Render()` and `TitleStyle.Render()` call internally writes to a `strings.Builder` (lipgloss internals). The result is immediately concatenated into `fmt.Sprintf`. With 10-20 runs, 10 dispatches, and 10 events all rendering on each View() call in F6, this means tens of `strings.Builder` allocations per frame.

The question asks specifically about `strings.Builder` vs concatenation. The existing code uses `fmt.Sprintf` throughout, not raw concatenation (`+`). `fmt.Sprintf` with a fixed format string is well-optimized by the Go compiler for short strings; it is not meaningfully worse than `strings.Builder` for 5-6 field concatenations. The real allocation cost is in the lipgloss `Render()` calls, not in `fmt.Sprintf`.

**Who feels it:** Not directly felt by users at current data sizes. Would matter if dispatch or event counts grew to hundreds per frame (they won't — both are capped by the plan).

**Recommendation:** No change needed for the render method implementations. Using `strings.Builder` at the list level (building the joined output from N lines) is worth it only if profiling shows string join as a bottleneck. For now, follow the existing pattern.

---

## Summary Table

| # | Area | Severity | User Impact | Fix Complexity |
|---|------|----------|-------------|----------------|
| 1 | 3 subprocesses per project per 2s | P1 | Stale dashboard at N >= 15 projects | Medium (ic CLI change or per-project parallelism) |
| 2 | seenEvents/seenOrder data race | P0 | Map corruption under concurrent WS + refresh | Low (move inside mu.Lock block) |
| 3 | mergeActivities allocates map+sort every 2s | P2 | GC pressure, unnecessary work on quiet periods | Low (skip when no incoming) |
| 4 | GetState() called in View() per frame | P2 | Render latency, RLock contention | Low (cache in model on refreshMsg) |
| 5 | Dedup contract unclear between LRU and per-call seen-map | P1 | Re-emission of old events after long sessions | Medium (clarify ownership at F5 time) |
| 6 | Web template execution per request | P3 | None at current scale | None required |
| 7 | Phase duration scan in render path (F6) | P2 | Frame jank in run detail pane | Low (precompute on refreshMsg) |
| 8 | statusForSession in render path (F8.3 addresses) | P3 | Cache miss subprocess in View() | Resolved by F8.2/F8.3 as planned |
| 9 | String building in new render methods | P3 | None at current data sizes | None required |

---

## Must-Fix Before Shipping

**P0 — Finding 2:** The `seenEvents`/`seenOrder` write outside any lock is a data race that will trigger under concurrent WebSocket event delivery + 2s refresh. Move the LRU update block inside `a.mu.Lock()` at line 465.

**P1 — Finding 1:** At the expected project count (5-15), 15-45 subprocesses every 2 seconds is the single largest cost added by E7. The per-project timeout of 3s means a single SQLite contention event starves the semaphore. Validate with a benchmark before shipping to confirm it stays within the 2s window at your typical N.

**P1 — Finding 5:** Define the dedup ownership model before implementing F5. The current LRU and the per-call seen-map serve overlapping purposes. Resolve this at F5 design time, not after.

## Optional Tuning (Post-Ship)

- Finding 3: Skip mergeActivities sort when `len(incoming) == 0`
- Finding 4: Store GetState() result in model on refreshMsg, read model.state in View()
- Finding 7: Precompute phase durations in updateLists(), not in View()
