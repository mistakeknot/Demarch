# PRD: Bigend Migration to Kernel State (E7)

**Bead:** iv-ishl
**Date:** 2026-02-20
**Status:** Approved
**Brainstorm:** [brainstorm](../brainstorms/2026-02-20-bigend-migration-brainstorm.md)
**Reviews:** [architecture](../research/architecture-review-of-e7-prd.md) · [user/product](../research/user-product-review-of-e7-prd.md) · [correctness](../research/correctness-review-of-e7-prd.md)

---

## Problem

Bigend — the multi-project agent mission control dashboard — has zero kernel awareness. It discovers projects via filesystem scanning, monitors agents via tmux scraping and Intermute REST, and has a TODO stub for its activity feed. Meanwhile, a complete `ic` data layer exists in `internal/status/data.go` but is isolated to the standalone `autarch status` TUI. Users cannot see runs, phases, dispatches, events, or token consumption in the main dashboard.

Additionally, the TUI has a status detection split: the aggregator computes rich 4-tier state (hook → pattern → repetition → activity) but the TUI ignores it and re-runs a simpler detector on every render tick.

## Solution

Promote the existing `internal/status` data layer into Bigend's `Aggregator.Refresh()` pipeline via additive enrichment. Both old and new data sources run in parallel — kernel data is added as new fields on `aggregator.State`. Each feature ships as a vertical slice (data layer → TUI rendering → web template). The status model consolidates fragmented status representations and surfaces the existing rich detection results.

## Pre-Implementation Gates

Three pre-existing bugs in the aggregator must be fixed before any E7 feature slice lands. These are not E7 features — they are correctness fixes to the existing codebase that E7 would otherwise aggravate.

### Gate 1: Fix Activities wipe-on-refresh

**File:** `aggregator.go:390-404`

`Refresh()` replaces the entire `State` struct every 2 seconds, resetting `Activities` to an empty slice. WebSocket events prepended by `addActivity()` between cycles are silently discarded. This is hidden today because the Activities feed has no visible TUI renderer, but F3 and F5 both depend on Activities accumulating correctly.

**Fix:** Preserve existing activities across state replacement. Before the `a.state = State{...}` assignment, snapshot `oldActivities := a.state.Activities` and carry it forward. Kernel events go into `KernelEvents` (not Activities), but Intermute WebSocket events must survive Refresh cycles.

### Gate 2: Fix data race on wsConnected/wsCtx/wsCancel

**File:** `aggregator.go:118, 160, 193, 203, 211`

`wsConnected`, `wsCtx`, and `wsCancel` are written in `ConnectWebSocket()`/`DisconnectWebSocket()` without holding `a.mu`, but read from the Bubble Tea render goroutine via `IsWebSocketConnected()`. This is a data race that `go test -race` will flag.

**Fix:** Use `atomic.Bool` for `wsConnected`. Protect `wsCtx`/`wsCancel` under `a.mu`.

### Gate 3: Refactor I/O-under-lock in enrich goroutines

**File:** `aggregator.go:275-302`

The spec/insight event goroutines acquire `a.mu.Lock()` before calling `enrichWithGurgStats()`/`enrichWithPollardStats()`, which perform filesystem I/O while holding the write lock. This blocks all `GetState()` readers (including the 60fps Bubble Tea render loop) for the duration of that I/O. E7's `enrichWithKernelState()` would add N×4 ic subprocess execs under the same lock, causing visible dashboard freezes.

**Fix:** Refactor to the correct pattern (already used by the agent-event goroutine at lines 285-293): do all I/O outside the lock, acquire `a.mu.Lock()` only to publish results. Fix the existing Gurgeh/Pollard goroutines first so there is no temptation to copy the broken pattern.

### Gate 4: Extract `internal/icdata` from `internal/status`

`internal/status` bundles data types + fetch functions (no UI deps) alongside Bubble Tea pane structs + rendering code (imports `pkg/tui`, `charmbracelet/bubbletea`). The aggregator currently has zero UI dependencies. If it imports `internal/status` to call `FetchRuns()`, Bubble Tea flows transitively into the web server binary.

**Fix:** Extract data types and fetch functions to `internal/icdata/` (~80 lines moved):
- `internal/icdata/types.go` — Run, Dispatch, Event, TokenSummary structs
- `internal/icdata/fetch.go` — FetchRuns, FetchDispatches, FetchEvents, FetchTokens, runIC

`internal/status` keeps its Bubble Tea model and pane structs. The aggregator imports only `internal/icdata`.

---

## Features

### F1: Project Discovery — Kernel Awareness (iv-lemf)
**What:** Add `.clavain/intercore.db` detection to the project scanner and fetch runs for each kernel-aware project. Slice 1 also establishes the structural foundation for parallel slice development.

**Acceptance criteria:**
- [ ] `discovery.Project` struct has `HasIntercore bool` field
- [ ] `Scanner.Scan()` detects `.clavain/intercore.db` (or `.clavain/` dir) alongside existing tool dirs
- [ ] Scanner updates both WalkDir trigger (line 103) and inclusion gate (line 111) atomically — test covers `.clavain`-only project appearing in scan results
- [ ] Scanner canonicalizes project paths via `filepath.EvalSymlinks()` before keying — symlinked projects do not produce duplicate entries
- [ ] `Aggregator.Refresh()` calls `enrichWithKernelState(projects)` for projects with `HasIntercore`
- [ ] Kernel fields grouped in `*KernelState` sub-struct on `aggregator.State` (nil when no kernel-aware projects exist)
- [ ] `enrichWithKernelState()` defined with complete structure and per-method stubs: `enrichRuns()`, `enrichDispatches()`, `enrichEvents()`, `enrichMetrics()` — each stub is a no-op that later slices fill
- [ ] Per-project kernel enrichment runs concurrently via bounded goroutine pool (semaphore of 5) with per-project timeout of 2-3 seconds
- [ ] Refresh goroutine pileup guarded: `atomic.Bool` flag prevents new `Refresh()` dispatch while previous is in flight
- [ ] Projects with only `.clavain/` (no `.gurgeh`/`.coldwine`/`.pollard`) appear in project list
- [ ] TUI sidebar shows run count badge next to project name (e.g., `Interverse [2 runs]`)
- [ ] Per-project kernel fetch failure logs error and leaves that project's kernel state stale from previous cycle — other projects unaffected
- [ ] Kernel-aware projects where kernel data fetch failed show warning indicator (`!`) in sidebar
- [ ] Web dashboard shows runs section on project pages

### F2: Agent Monitoring — Dispatch Integration (iv-9au2)
**What:** Fetch dispatches from `ic dispatch list` and display them alongside Intermute agents.

**Acceptance criteria:**
- [ ] `KernelState.Dispatches map[string][]icdata.Dispatch` keyed by project path
- [ ] `enrichDispatches()` stub (from F1) filled: calls `icdata.FetchDispatches()` for each kernel-aware project
- [ ] TUI shows dispatches under the selected run in the project detail view
- [ ] Dispatch rows show: ID, agent name, status indicator, duration, model
- [ ] Status icons use `pkg/tui.StatusIndicator` with the unified status model (F8)
- [ ] Web shows dispatch list on project detail page
- [ ] Intermute agents and kernel dispatches coexist — Intermute provides registration/inbox, `ic` provides lifecycle. If agent name matches dispatch agent name (same string), merge into single display row showing both inbox state and lifecycle data. If names differ, display as separate labeled sections.

### F3: Run Progress — Event Stream (iv-gv7i)
**What:** Fetch kernel events via `ic events tail` and merge them into the unified activities feed.

**Acceptance criteria:**
- [ ] `KernelState.Events map[string][]icdata.Event` keyed by project path
- [ ] `enrichEvents()` stub (from F1) filled: calls `icdata.FetchEvents()` with `--all --limit=50` per project
- [ ] Kernel events merge into `Activities` feed with `Source: "kernel"`
- [ ] `Activity` struct carries `SyntheticID string` populated at ingestion — composite key: `source + ":" + projectPath + ":" + eventID` for kernel, `"intermute:" + entityID + ":" + eventType` for Intermute
- [ ] Events display with source prefix and per-source color: `[K]` kernel (blue), `[M]` Intermute (green), `[T]` tmux (gray) — always shown, not conditional on filter state
- [ ] Events show phase transitions, gate checks, dispatch lifecycle in the TUI
- [ ] Web dashboard and project pages show the unified activity stream
- [ ] Activity timestamps display correctly (HH:MM:SS format in TUI)

### F4: Dashboard Metrics — Kernel Aggregates (iv-1d9u)
**What:** Compute and display aggregate metrics from kernel state on the dashboard.

**Acceptance criteria:**
- [ ] `KernelState.Metrics` struct with: `ActiveRuns`, `ActiveDispatches`, `BlockedAgents`, `TotalTokensIn`, `TotalTokensOut`, `KernelErrors map[string]string` (per-project error messages)
- [ ] `enrichMetrics()` stub (from F1) filled: computed from aggregated runs/dispatches across all kernel-aware projects
- [ ] `BlockedAgents` count: dispatches/agents with Blocked status (requires F8 status model). Shown in warning color if >0.
- [ ] `KernelErrors` populated when per-project fetch fails — display shows "3/4 projects" when one project's kernel data unavailable
- [ ] TUI dashboard stats row shows: Projects | Active Runs | Blocked | Dispatches | Tokens
- [ ] Token totals formatted with comma separators (e.g., `12,450 in / 3,200 out`)
- [ ] Cross-project "Active Runs" section on dashboard tab: flat list showing project name, run ID, goal (truncated), current phase, phase duration, status indicator. Navigate from this list into project detail view.
- [ ] Web dashboard template shows kernel metrics and cross-project active runs
- [ ] Zero-value graceful: metrics show `0` when no kernel data available, no errors

### F5: Event Viewport — Bootstrap-then-Stream (iv-4c16)
**What:** A dedicated event viewport that bootstraps with historical events and streams new ones on each poll.

**Acceptance criteria:**
- [ ] On startup, viewport bootstraps with last N events per project via `ic events tail`
- [ ] On each 2s refresh cycle, new events are appended (dedup by `SyntheticID` — composite key per F3)
- [ ] Dedup seen-set lives on `Aggregator`, survives `Refresh()` cycles, capped at `limit * 10` entries with LRU eviction
- [ ] Bootstrap batch pre-populates the seen-set before emitting events to viewport — historical events display as history, not as "new" notifications
- [ ] Intermute WebSocket events continue flowing into the same stream
- [ ] Viewport auto-scrolls to newest event
- [ ] Filtering supported: by event type, by project, by source (kernel/intermute)
- [ ] Uses `pkg/tui.LogPane` for rendering
- [ ] Web shows equivalent event stream on dashboard

### F6: Two-Pane Layout — List + Detail (iv-4zle)
**What:** Refactor the project detail view to support a list+detail split for runs.

**Acceptance criteria:**
- [ ] Project detail pane splits into list (runs) and detail (selected run's dispatches/events/tokens)
- [ ] Run list shows: ID, goal (truncated), current phase, phase duration, phase progress bar, complexity badge
- [ ] Phase duration: compact elapsed time since phase entry ("14m", "2h3m"). Color: green (normal), yellow (>1h), red (>4h). Thresholds not configurable in v1. Derived from most recent `phase.advance` event timestamp via `ic run events --json`.
- [ ] Goal field right-truncated to available column width minus 2 with ellipsis. Fixed-width allocations: ID (8), status (1), phase (12), duration (6), progress bar (8), complexity (2) — goal fills remaining. Full goal in detail pane header.
- [ ] Run list defaults to active + recent runs (active first, then Done/Error from last 24h). Press `a` for full unfiltered history.
- [ ] Detail pane shows dispatches, events, and token summary for the selected run
- [ ] Arrow keys navigate within focused pane only; Tab (or h/l) cycles focus between sidebar, run list, and detail pane
- [ ] Focused pane shows distinct border color or header highlight
- [ ] Focus ring and key shortcuts documented in Bigend help text (check for conflicts with existing CommonKeys in pkg/tui/)
- [ ] When no run is selected, full pane shows legacy view (sessions, agents)
- [ ] Below 100 columns: show run list only. Enter opens full-screen detail overlay, Esc returns. Selected run preserved in model state and restored when terminal widens.
- [ ] Existing `paneWidths()` logic extended, not replaced

### F7: Typed KernelEvent Enum (iv-jaxw)
**What:** Define a Go enum for all kernel event types, replacing string matching.

**Acceptance criteria:**
- [ ] `internal/icdata/kernelevents.go` defines typed constants for all event types (NOT `pkg/signals` — that package is scoped to real-time cross-tool signaling; kernel events are historical record types)
- [ ] Event types: `PhaseAdvance`, `PhaseRollback`, `GateCheck`, `GatePassed`, `GateFailed`, `DispatchSpawned`, `DispatchCompleted`, `DispatchFailed`, `DispatchCancelled`, `ArtifactAdded`, `TokensRecorded`, `BudgetExceeded`
- [ ] Each constant maps to the corresponding `ic` event type string via `String()` method
- [ ] `ParseKernelEvent(string) KernelEvent` parser function
- [ ] All event type matching in `internal/icdata/` and TUI code uses typed constants
- [ ] Tests cover all known event types + unknown event fallback

### F8: 5-State Unified Status Model (iv-xu31)
**What:** Consolidate fragmented status representations into a unified 5-state model and fix the status detection split.

**Acceptance criteria:**
- [ ] Unified status enum with 5 kernel states + 1 display-only state:
  - `Active` — working, running (agent is doing compute)
  - `Blocked` — waiting-on-human, permission-required, gate-failed, stalled (needs operator intervention)
  - `Waiting` — inter-agent dependency, queue pause, idle (self-resolving, low urgency)
  - `Done` — completed, finished
  - `Error` — failed, cancelled, timeout (terminal)
  - Display-only: `Unknown` — gray `?` indicator, excluded from Active/Blocked counts
- [ ] Mapping function `UnifyStatus(rawStatus string) UnifiedStatus` in `pkg/tui/components.go`
- [ ] Exact mappings: `working`/`running` → Active; `blocked`/`stalled`/`permission-required` → Blocked; `waiting`/`idle`/`queued` → Waiting; `completed`/`done` → Done; `failed`/`error`/`cancelled`/`timeout` → Error; `""`/unknown → Unknown
- [ ] Each state has consistent icon and color in `pkg/tui/styles.go`
- [ ] TUI `statusForSession()` uses `TmuxSession.State` from aggregator (4-tier statedetect) instead of re-running `tmux.Client.DetectStatus()`
- [ ] Aggregator stores `UnifiedStatus` value in `TmuxSession.State` at write time (not raw statedetect string) — mapping happens once at aggregator, not on every render tick
- [ ] Redundant `capture-pane` calls eliminated from TUI render path
- [ ] All status display points (sessions, agents, dispatches) use unified model
- [ ] Unknown/empty status maps to `Unknown` display state — never to Active

## Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Migration strategy | Additive enrichment | Both pipelines run in parallel; safe rollback; no existing breakage |
| Navigation axis | Projects as primary (detail); cross-project surface on dashboard (triage) | Projects-as-primary correct for detail view; operators need a flat active-runs surface for triage — see Decision 2 |
| Data access | Exec-based ic CLI | Re-use proven internal/status/data.go; decoupled from schema |
| Event model | Unified stream with source tags + visual prefixes | One timeline; `[K]`/`[M]`/`[T]` prefixes with per-source color always visible |
| Event dedup | Composite `SyntheticID` key | `source:projectPath:eventID` — prevents cross-project ID collision |
| Status detection | Surface statedetect in TUI; store UnifiedStatus at aggregator write time | Eliminates redundant capture-pane; reduces render-time mapping from 5 vocabularies to 3 |
| Unknown/empty status | Distinct display state (gray `?`), excluded from Active counts | Unknown ≠ Active; prefer honest uncertainty over false confidence |
| autarch status | Keep separate | Different use case: quick check vs mission control |
| Delivery model | Vertical slices with F1 providing structural stubs | Each feature ships end-to-end; F1 delivers enrichWithKernelState() skeleton with per-method stubs so slices 2-4 can parallelize |
| Kernel data types | `internal/icdata` package (extracted from `internal/status`) | Prevents Bubble Tea dependency contamination of aggregator/web server |
| KernelEvent enum | `internal/icdata/kernelevents.go` | Not `pkg/signals` — different change driver (ic schema vs signal protocol) |
| Refresh concurrency | Bounded goroutine pool (semaphore of 5) + per-project timeout | 5 projects × 4 calls × 50ms = 1s if serial; concurrent pool keeps total <200ms |
| Refresh pileup guard | `atomic.Bool` flag; skip tick if previous Refresh() still in flight | Prevents goroutine pileup when ic exec hangs |
| Per-project failure | Log-and-continue with warning badge | One bad DB does not corrupt all projects' kernel metrics |
| Subprocess lifecycle | Use `a.wsCtx` (not `context.TODO()`) for partial-refresh goroutines; `sync.WaitGroup` for clean shutdown | No orphaned ic processes after Bigend exit |
| Dashboard event scope | Global on dashboard tab, project-scoped in detail view | Resolved from original open question |

## Non-Goals

- Removing old data sources (Intermute, tmux, filesystem) — deferred to E9
- Direct SQLite reads of intercore.db — exec-based ic CLI is sufficient for v1
- Signal broker / WebSocket for real-time kernel events — keep polling for now
- Follow mode for events (`ic events tail --follow`) — deferred
- Write operations in Bigend (creating runs, advancing phases) — read-only dashboard
- Multi-project DB aggregation — each project polled independently

## Dependencies

- `internal/icdata/` — extracted from `internal/status/data.go` as part of Gate 4
- `ic` CLI — must be in PATH for kernel data to appear (fail-open: no `ic` = no kernel data)
- `pkg/tui/` shared components — styles, StatusIndicator, LogPane
- `.clavain/intercore.db` — must exist per project for kernel awareness
- iv-knwr (TUI validation tests) — should execute before or during F8
- Gates 1-4 (pre-existing bug fixes) — must land before any E7 feature slice

## Success Signal

After E7 ships, the operator can answer "which of my agents is blocked right now?" in under 30 seconds without leaving Bigend. Secondary: reduced `autarch status` usage post-ship (Bigend absorbs the single-project monitoring use case).

## Decisions Resolved During Review

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Status model cardinality | **5 states** (Active, Blocked, Waiting, Done, Error) + display-only Unknown | Preserves the most actionable operator signal: blocked-vs-self-resolving. stalled → Blocked. |
| 2 | Cross-project runs on dashboard | **Yes** — flat active runs list on dashboard tab | Operators need "what's running now?" without per-project navigation. Matches existing Intermute agent pattern. |
| 3 | Pre-E7 bug fix timing | **Standalone commit first** | Gates 1-3 ship as pre-E7 commit. Clean base, clear git history, no risk of copying broken patterns. |
| 4 | Phase duration in run list | **Yes** — color-coded time-in-current-phase | Turns run list from status display to anomaly detector. Green/yellow/red thresholds at normal/>1h/>4h. |

## Remaining Open Questions

1. **Signal broker timing** — iv-0v7j is P1. Should E7 prepare hooks for signal broker integration even if not wired yet?
