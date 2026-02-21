# Correctness Review: E7 PRD — Bigend Migration to Kernel State

**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-20
**PRD:** `docs/prds/2026-02-20-bigend-kernel-migration.md`
**Brainstorm:** `docs/brainstorms/2026-02-20-bigend-migration-brainstorm.md`
**Findings JSON:** `/tmp/fd-correctness-e7-prd.json`

---

## Invariants That Must Hold

Before assigning severity, I wrote down the invariants E7 must preserve:

1. **Activity stream is additive** — events that arrived at time T must still be visible at time T+N for any N > 0 within the display window (100 events cap).
2. **Project kernel data is isolated** — a failure fetching kernel state for project A must not corrupt, erase, or prevent fetching kernel state for project B.
3. **State reads are consistent** — `GetState()` returns a coherent snapshot; partial writes from two concurrent goroutines cannot interleave within a single published State.
4. **Event dedup is correct** — the same physical event is never displayed twice; two different events from different projects that happen to share a numeric ID are not conflated.
5. **Status indicators are truthful** — Active means confirmed liveness, not "we don't know."
6. **Project identity is stable** — the same physical project on disk maps to the same key across refresh cycles.
7. **Subprocess cancellation is bounded** — no orphaned `ic` child processes survive Bigend shutdown.

---

## Executive Summary

The PRD as written will introduce **three P0 correctness failures** into the existing codebase before E7 adds a single line of kernel code. Two of them already exist (the Activities wipe and the `wsConnected` data race); E7 will aggravate both by adding more concurrent writers. The remaining findings are genuine implementation gaps — places where the PRD specifies a behavior ("dedup by event ID," "fail-open per project") without specifying the mechanism, leaving the implementation to make a wrong choice by default.

The additive-enrichment strategy is architecturally sound. The problems are in the concurrency contract of the existing `Aggregator` and the underspecified dedup/isolation behaviors in the new features.

---

## Findings

### P0-1: Activities Feed Wiped on Every Refresh() — Kernel and Intermute Events Lost Every 2 Seconds

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go`
**Lines:** 390–404 (Refresh), 253–265 (addActivity)

**The bug exists today.** `Refresh()` initializes `activities := []Activity{}` at line 391, then publishes the entire State with `Activities: activities` at line 401. The `addActivity()` function (called from the WebSocket event handler) prepends events to `a.state.Activities` under `a.mu.Lock()`. These two paths race:

```
T=0.0s  addActivity() acquires mu.Lock, prepends event E1 → Activities=[E1]
T=0.0s  addActivity() releases mu.Lock
T=0.1s  addActivity() acquires mu.Lock, prepends event E2 → Activities=[E2,E1]
T=2.0s  Refresh() acquires mu.Lock
T=2.0s  Refresh() assigns a.state = State{..., Activities: []Activity{}}
T=2.0s  Refresh() releases mu.Lock → Activities=[], E1 and E2 are gone
```

The line-391 comment `// TODO: Load recent activities` confirms this is known to be incomplete. When E7 adds `enrichWithKernelState()` and F5's dedup logic, both will operate on a feed that is guaranteed empty at the start of every 2-second cycle. The dedup seen-set will never find any previous events to deduplicate against, so every poll will re-add the same 50 historical events as "new."

**Recommendation:** In `Refresh()`, preserve accumulated activities across the full-state replacement. Before the `a.state = State{...}` assignment, snapshot `oldActivities := a.state.Activities` (under the lock). Assign `Activities: oldActivities` in the new State. Kernel events fetched fresh each cycle do not use this path — they go into `KernelEvents` — but Intermute WebSocket events do and must survive.

---

### P0-2: Data Race on wsConnected, wsCtx, wsCancel — Written Without Mutex

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go`
**Lines:** 160, 193, 203, 210–212

`wsConnected` (bool), `wsCtx` (context.Context), and `wsCancel` (context.CancelFunc) are plain fields on `Aggregator`. They are written in `ConnectWebSocket()` (lines 160, 193) and `DisconnectWebSocket()` (lines 201, 203) without holding `a.mu`. They are read in `IsWebSocketConnected()` (line 211) and implicitly by the WebSocket callback goroutine that reads `wsCtx` for lifecycle awareness.

`ConnectWebSocket()` is called from the TUI init goroutine. `IsWebSocketConnected()` is called from the Bubble Tea render goroutine. These are different goroutines with no happens-before edge on `wsConnected`. `go test -race` will flag this.

**Consequence:** `IsWebSocketConnected()` returns stale `true` after the connection has dropped. The TUI shows a connected indicator; no one knows events are being silently lost.

**Recommendation:** Protect `wsConnected`, `wsCtx`, and `wsCancel` under `a.mu`. In `ConnectWebSocket()` and `DisconnectWebSocket()`, acquire `a.mu.Lock()` before writing. In `IsWebSocketConnected()`, use `a.mu.RLock()`. Alternatively, use `sync/atomic.Bool` for `wsConnected` (cheaper, still correct for a single bool).

---

### P0-3: enrichWithGurgStats and enrichWithPollardStats Perform Filesystem I/O Under mu.Lock() — Sets the Pattern for a Frozen Dashboard When enrichWithKernelState() Follows It

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go`
**Lines:** 275–280 (spec event goroutine), 297–302 (insight event goroutine)

Both goroutines acquire `a.mu.Lock()` **before** calling `enrichWithGurgStats(a.state.Projects)` and `enrichWithPollardStats(a.state.Projects)`. These enrich functions do filesystem I/O while holding the write lock. This blocks all `GetState()` readers for the duration of that I/O.

The PRD's brainstorm documents that `enrichWithKernelState()` will call `FetchRuns()`, `FetchDispatches()`, `FetchEvents()`, and `FetchTokens()` per project — 4 × `ic` subprocess execs × N projects. At the brainstorm's own estimate of ~50ms each, 5 projects = 250ms of write-lock hold per partial refresh if implemented following the existing pattern. The Bubble Tea model calls `GetState()` on every render tick (60fps). A 250ms write-lock hold produces a visible freeze.

Worse: `ic` can hang. `runIC()` uses `exec.CommandContext` but inherits whatever context is passed. If a project's SQLite DB is locked by a concurrent writer, `ic` stalls. If `enrichWithKernelState()` holds `a.mu.Lock()` while `ic` stalls, the dashboard freezes until the context deadline.

This antipattern already exists for the Gurgeh and Pollard enrich goroutines. E7 must not replicate it for kernel enrichment.

**Recommendation:** I/O must never happen under `a.mu`. The correct pattern (already used correctly by the agent-event goroutine at lines 285–293):

```
// CORRECT: I/O outside lock
go func() {
    // 1. Snapshot inputs (no lock needed for read-only project list snapshot)
    paths := snapshotProjectPaths()      // brief RLock read
    // 2. Do all I/O without any lock
    results := fetchKernelState(ctx, paths)
    // 3. Acquire lock only to publish results
    a.mu.Lock()
    a.state.Runs = results.runs
    a.state.Dispatches = results.dispatches
    a.state.KernelEvents = results.events
    a.state.UpdatedAt = time.Now()
    a.mu.Unlock()
}()
```

The existing `enrichWithGurgStats` and `enrichWithPollardStats` goroutines should be fixed to this pattern before E7 lands.

---

### P1-1: Event ID Collision in Merged Activities Feed — kernel int64 vs Intermute string IDs

**Specification:** F5 — "dedup by event ID"
**Data types confirmed:**
- `internal/status/data.go:60` — `Event.ID int64` (SQLite auto-increment, scoped to one project DB)
- `aggregator.go:93–99` — `Event.EntityID string` (Intermute entity UUID)
- `aggregator.go:Activity` struct — no ID field at all

The dedup key space is undefined. Two concrete collision classes:

**Class 1: Cross-project kernel ID collision.** Project A's `intercore.db` has an event with `ID=42`. Project B's `intercore.db` also has an event with `ID=42` (both are SQLite row IDs from separate DBs starting at 1). If the dedup seen-set uses bare `int64` or `strconv.Itoa(id)`, both projects' event 42 hash to the same key. The second project's event is dropped silently.

**Class 2: Kernel-vs-Intermute type mismatch.** `ic` event ID `1` (int64) and Intermute EntityID `"1"` (if any entity happened to have a single-digit UUID suffix, which won't happen for full UUIDs but could for custom IDs) would collide if both are stringified into the same namespace.

**Recommendation:** Use a composite dedup key: `source + ":" + projectPath + ":" + strconv.FormatInt(id, 10)` for kernel events, `"intermute:" + entityID + ":" + eventType` for Intermute events. The `Activity` struct should carry a `SyntheticID string` field populated at ingestion. This partitions the namespace completely.

---

### P1-2: Refresh() Full-State Replacement Races With Partial-Refresh Goroutines That Mutate a.state.Projects In-Place

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go`
**Lines:** 275–280, 297–302 (goroutines), 394–404 (Refresh state replacement)

The spec/insight event goroutines call `enrichWithGurgStats(a.state.Projects)` and `enrichWithPollardStats(a.state.Projects)` under `a.mu.Lock()`. These functions receive a slice — a reference to the `Projects` slice inside the current `State` value. They mutate project entries in-place.

Meanwhile, `Refresh()` replaces `a.state` with a new `State` struct containing a fresh `Projects` slice. The sequence that produces a lost write:

```
T=0.0s  Refresh() runs, produces new Projects slice P_new
T=0.0s  Refresh() acquires mu.Lock, writes a.state = State{Projects: P_new}
T=0.0s  Refresh() releases mu.Lock
T=0.0s  spec.created event arrives → goroutine G1 spawned
T=0.1s  G1 acquires mu.Lock, calls enrichWithGurgStats(a.state.Projects)
         → enriches P_new in-place, writes gurgeh stats to P_new[i]
T=0.1s  G1 releases mu.Lock
T=2.0s  Refresh() runs again → new P_new2 scan, without gurgeh enrichment from G1
         → gurgeh stats are fresh from disk anyway, so this is not a bug here
```

The current design is accidentally safe for Gurgeh/Pollard because they re-read from disk. But when `enrichWithKernelState()` is added with its own partial-refresh path (e.g., a kernel event triggers a targeted kernel re-fetch), two goroutines can write different kernel data to the same project entry. The second writer's data silently overwrites the first's. With 5 projects and 4 concurrent ic calls per project, this window is real.

**Recommendation:** Kernel state (Runs, Dispatches, KernelEvents, KernelMetrics) should live in dedicated fields on `State` keyed by project path (`map[string][]status.Run`, etc.) rather than embedded in the `Project` struct. Partial-refresh goroutines write only their keyed entries — they cannot clobber a different project's data. `Refresh()` either preserves the previous kernel maps or rebuilds them from scratch, not both.

---

### P1-3: One Hung ic Exec Stalls enrichWithKernelState() for All Projects, Piling Up Refresh Goroutines

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/tui/model.go`
**Lines:** 1012–1015 (tickMsg handler), 671–679 (refresh() cmd)

The `tickMsg` handler fires unconditionally every 2 seconds and dispatches `m.refresh()`. The `refresh()` tea.Cmd runs in a goroutine. There is no guard checking whether a previous refresh is still in flight. If `enrichWithKernelState()` is added to `Refresh()` and one project's `ic` call hangs (DB locked, process table full, `ic` binary missing from PATH of the exec environment), `Refresh()` does not return until the context deadline.

With `timeout.HTTPDefault` as the context (which is typically 30s based on the package name's convention), the timer fires 15 times before the first `Refresh()` returns. Each tick spawns a new `Refresh()` goroutine. They all block on `a.mu.Lock()` (since the first one holds it or is waiting for it). At timeout, all 15 goroutines wake up sequentially, each executing a full scan + enrich cycle back-to-back, causing a 30-second dashboard freeze followed by a burst of 15 sequential full-state replacements.

**Recommendation:**

1. Add an `atomic.Bool` flag `refreshInFlight` to the Bubble Tea model. In the `tickMsg` handler, check it before dispatching `m.refresh()`. Skip the tick if true.
2. Apply a per-project timeout of 2–3 seconds for `ic` subprocess calls — shorter than the overall Refresh context.
3. Fan out project enrichment concurrently using `errgroup` rather than a serial loop.

---

### P1-4: F8 Maps unknown/empty → Active — Crashed Agents Display as Healthy

**Specification:** F8 — "Unknown/empty status maps to Active (safe default — prefer showing something)"

The safety claim is backwards. In a mission control dashboard, Active is the most operationally loaded state — it means "this agent is doing work, do not interrupt, budget is being consumed." The decision to map `unknown` and `""` (empty string from a missing JSON field) to Active means:

- A Claude Code session that crashed mid-task (tmux pane shows shell prompt, `DetectStatus` returns `StatusUnknown`) renders as Active with a green indicator.
- A dispatch row where the `status` field was missing from the `ic` JSON output (e.g., schema version mismatch) renders as Active.
- A `BudgetExceeded` dispatch whose status field is corrupted to empty renders as Active rather than Error.

An operator monitoring 5 projects sees 3 Active agents. One is genuinely working, two have crashed. The operator does not intervene because the dashboard says everything is fine. This is a 3am incident.

The rationale "prefer showing something" is valid — but the correct "something" for unknown state is Unknown (grey question mark), not Active (green indicator). If only 4 states are acceptable, the correct fallback is Waiting (yellow), not Active.

**Recommendation:** Map unknown/empty to a fifth state `Unknown` with a grey `?` indicator. If the enum must stay at 4 states, map unknown/empty to `Waiting`. Reserve `Active` exclusively for statuses with a confirmed liveness signal: `working`, `running`. Document the invariant in the mapping function's godoc.

---

### P1-5: Project Path Instability — Symlinks Produce Different Keys Per Scan

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/discovery/scanner.go`
**Lines:** 90, 104, 108

The scanner uses `filepath.WalkDir` which follows symlinks. The Interverse CLAUDE.md documents: "Compatibility symlinks exist at `/root/projects/<name>` pointing into this monorepo for backward compatibility." A project may be discovered via both `/root/projects/intermute` (symlink) and `/root/projects/Interverse/services/intermute` (canonical path) in the same scan walk, producing two `Project` entries if the dedup map at line 81 does not canonicalize paths before keying.

Even if within-cycle dedup works (it appears to: `seen[projectPath]` at line 105 will catch both entries if they're identical strings), the canonical vs symlink path may differ across Refresh() cycles depending on walk order, producing different map keys in `state.Runs`, `state.Dispatches`, `state.KernelEvents`. The TUI sidebar would show the same project appearing twice, or run counts flickering between 0 and N on alternate cycles.

`runIC()` at `data.go:184–186` sets `cmd.Dir = projectDir`. The OS resolves symlinks when changing directories, so `ic` itself runs correctly regardless. The instability is purely in the key used to store and look up results.

**Recommendation:** At `scanner.go:104`, canonicalize the path before storing:

```go
projectPath := filepath.Dir(path)
if resolved, err := filepath.EvalSymlinks(projectPath); err == nil {
    projectPath = resolved
}
```

Apply the same normalization to all `map[string][]status.Run` lookups. This is a one-line fix per call site.

---

### P2-1: enrichWithKernelState() Failure Isolation Unspecified — One Bad DB Corrupts All Projects' Kernel Metrics

**Specification:** F1, F4 — "fail-open: no ic = no kernel data"

The fail-open statement covers the binary not being in PATH. It does not cover the common case: `ic` is in PATH but one project's `intercore.db` is locked, schema version is old, or permissions are wrong. `runIC()` returns an error in all these cases. If `enrichWithKernelState()` is a loop over projects and treats any project error as fatal (the natural implementation given the current enrich function signatures), one bad project aborts kernel enrichment for all subsequent projects.

If it log-and-continues, `KernelMetrics` in F4 silently undercounts — the dashboard shows "3 Active Runs" when the true answer is "3 confirmed Active Runs + 1 project where we couldn't check." An operator might make scheduling decisions based on undercounted metrics.

**Recommendation:** Require explicit per-project error handling. The `enrichWithKernelState()` function signature should return `map[string]error` (per-project errors) in addition to populating the state maps. Surface errors in the TUI as a warning badge (`?` or `!`) next to the affected project name. Add `KernelErrors map[string]string` to `KernelMetrics` so the web dashboard can also show the health indicator. The `KernelMetrics.ActiveRuns` display should read "3/4 projects" when one project's kernel data is unavailable.

---

### P2-2: context.TODO() in Partial-Refresh Goroutines Orphans ic Subprocesses on Shutdown

**File:** `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go`
**Line:** 286

The agent-event partial-refresh goroutine uses `context.TODO()`:

```go
ctx, cancel := withTimeoutOrCancel(context.TODO(), timeout.HTTPDefault)
```

When `enrichWithKernelState()` is added to a partial-refresh path (which F5's streaming model implies — new kernel events trigger a targeted re-fetch), its `ic` subprocess calls will also use `context.TODO()` or a derived context. When Bigend exits, `wsCancel()` is called (cancelling `wsCtx`) but the partial-refresh goroutines' contexts are not cancelled. Their `ic` child processes continue running, hold read locks on `intercore.db`, and appear in `ps` output after the dashboard has exited.

**Recommendation:** Replace `context.TODO()` at line 286 (and any new partial-refresh goroutines) with `a.wsCtx`. Add a `sync.WaitGroup` to `Aggregator` to track in-flight goroutines. `DisconnectWebSocket()` / `Close()` should: (1) call `wsCancel()`, (2) wait on the WaitGroup. This gives in-flight goroutines a clean cancellation signal and guarantees no orphaned subprocesses.

---

### P2-3: F5 Dedup Seen-Set Lifecycle Is Undefined — Re-Bootstrap Re-Adds 50 Historical Events as New

**Specification:** F5 — "dedup by event ID" / "on startup, viewport bootstraps with last N events"

The bootstrap-then-stream model requires a persistent seen-set to distinguish between "this event was already shown" and "this event is new." The PRD does not specify:

- Where the seen-set lives (on `Aggregator`? on the TUI model? in a package-level var?)
- What its eviction policy is (bounded? LRU? time-based?)
- Whether it survives dashboard restart

Without a persistent seen-set surviving across `Refresh()` cycles (which already don't survive due to P0-1), every 2-second poll re-fetches `--limit=50` events and must check all 50 against the seen-set. If the seen-set is cleared with `Activities` (per P0-1), all 50 events appear new on every cycle. The event viewport would show the same 50 historical events arriving as a burst every 2 seconds, not a stream of new events.

After a dashboard restart, the bootstrap intentionally re-fetches the last N events — but should display them as history, not as "new" notifications. Without a persisted or pre-populated seen-set, a restart causes 50 "new" event notifications to fire at once.

**Recommendation:** The seen-set must live on `Aggregator` and survive `Refresh()` cycles. Use a `map[string]struct{}` keyed by composite ID (see P1-1). Cap at `limit * 10` entries with LRU eviction. Pre-populate the seen-set from the initial bootstrap batch before emitting events to the viewport, so bootstrap history is silent. Document the restart behavior explicitly: historical events re-fetched on startup are marked seen before display.

---

## Summary Table

| ID | Severity | Title | File |
|----|----------|-------|------|
| P0-1 | P0 | Activities wiped every Refresh() | `aggregator.go:391` |
| P0-2 | P0 | Data race on wsConnected/wsCtx/wsCancel | `aggregator.go:118,193,203` |
| P0-3 | P0 | I/O under mu.Lock in enrich goroutines | `aggregator.go:275-302` |
| P1-1 | P1 | Event ID collision across sources/projects | `data.go:60`, F5 spec |
| P1-2 | P1 | Partial-refresh goroutines race with Refresh() state replacement | `aggregator.go:275-302,394-404` |
| P1-3 | P1 | Unbounded Refresh() goroutine pileup on hung ic exec | `model.go:1012-1015` |
| P1-4 | P1 | unknown/empty maps to Active in F8 status model | F8 spec |
| P1-5 | P1 | Symlink paths produce unstable map keys | `scanner.go:104` |
| P2-1 | P2 | Per-project failure isolation unspecified | F1, F4 spec |
| P2-2 | P2 | context.TODO() in goroutines orphans ic subprocesses | `aggregator.go:286` |
| P2-3 | P2 | Dedup seen-set lifecycle undefined | F5 spec |

---

## Pre-Implementation Gates Recommended

Before any E7 feature slice lands in code:

1. **Fix P0-1** (Activities wipe) — it exists today and will silently break F5 dedup.
2. **Fix P0-2** (wsConnected race) — run `go test -race ./internal/bigend/aggregator/...` and confirm clean before adding more concurrent writers.
3. **Fix P0-3** (I/O under lock) — refactor `enrichWithGurgStats` and `enrichWithPollardStats` goroutines to the correct pattern before adding `enrichWithKernelState` so there is no temptation to copy the broken pattern.
4. **Define composite event ID** (P1-1) — agree on the `SyntheticID` format before F3 and F5 are implemented.
5. **Resolve P1-4** (status model) — change the unknown/empty mapping before F8 ships.

Slices F1, F7 (KernelEvent enum), and the path canonicalization fix (P1-5) can proceed in parallel with the above fixes.
