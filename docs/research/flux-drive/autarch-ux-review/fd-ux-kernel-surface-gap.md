# Autarch UX Review: Kernel Surface Gap Analysis

**Reviewer:** fd-ux-kernel-surface-gap
**Date:** 2026-02-25
**Scope:** Kernel state legibility and actionability from the TUI surface
**Verdict:** CONDITIONAL PASS -- Sprint tab is strong, but significant gaps exist in Bigend/Coldwine observability and the absence of two of four vision write-path intents

---

## Executive Summary

The Autarch TUI has a functional Go client for Intercore (`pkg/intercore/`) that covers the full kernel API surface: runs, dispatches, gates, artifacts, events, agents, budget, state, locks, and sentinels. The **Sprint tab** (`RunDashboardView`) is the closest realization of the vision's "Autarch status tool" and does a creditable job surfacing phase timelines, budgets, gate conditions, dispatches, and events. However, the overall TUI has significant kernel surface gaps:

1. **Two of four vision write-path intents are missing entirely** from any TUI surface (gate-override, submit-artifact).
2. **Bigend shows dispatches but not runs** -- the most fundamental kernel concept is invisible on the dashboard tab.
3. **Kernel unavailability is invisible** on Bigend and Coldwine -- only the Sprint tab and footer badge communicate degraded state.
4. **The event stream is polling-based and stale** -- `EventsTail` with `--follow` (the streaming API) is implemented in the client but unused; the EventWatcher uses batch polling with a 10-second sleep.
5. **Agent registry, artifacts, and locks** exist in the kernel client but are not surfaced anywhere in the TUI.

---

## Findings

### F1. Missing write-path intent: gate-override [P1 -- HIGH]

**Location:** Vision doc `docs/autarch-vision.md:84`, client `pkg/intercore/operations.go:134-137`

**Description:** The vision defines four app-to-OS write intents. Two are implemented:
- `start-run`: Coldwine "Create Sprint" command (`coldwine.go:876-897`), Sprint `/sprint create` (`sprint_commands.go:121-133`)
- `advance-run`: Sprint "Advance Phase" (`run_dashboard.go:376-387`), Sprint `/sprint advance` (`sprint_commands.go:77-91`), keyboard `a` (`run_dashboard.go:298-301`)

Two are **completely absent from any TUI surface**:
- `override-gate`: The Go client has `GateOverride(ctx, runID, reason)` (`operations.go:135`), but no view, command, slash command, or palette entry invokes it. When a gate blocks advancement, the only feedback is "Gate blocked" in the status message (`run_dashboard.go:161`). The user must drop to CLI (`ic gate override <runID> --reason=...`) to proceed.
- `submit-artifact`: Only `researchForSprint()` in `run_dashboard.go:460-527` uses `ArtifactAdd` -- and only for Pollard research results. There is no general-purpose "register artifact" affordance. Users cannot register a plan document, a review output, or any other artifact type from the TUI.

**Smallest viable fix:**
- Gate override: Add an `o` keybinding in `RunDashboardView.handleKey()` that opens a text prompt for the override reason, then calls `ic.GateOverride()`. Also add a palette command "Override Gate" and a `/sprint override [reason]` slash command in `SprintCommandRouter`.
- Submit artifact: Add a palette command "Register Artifact" that prompts for path and type, then calls `ic.ArtifactAdd()`.

---

### F2. Bigend tab shows dispatches but not runs [P1 -- HIGH]

**Location:** `internal/tui/views/bigend.go:447-483`

**Description:** The Bigend dashboard is supposed to be the "multi-project mission control" and the vision (`autarch-vision.md:103`, `autarch-vision.md:131-136`) describes it as the primary surface for:
- Run list with phase progress bars
- Event stream tail
- Dispatch status dashboard

**What Bigend actually renders:**
- Sessions (from `autarch.Client.ListSessions`) -- these are Intermute sessions, not kernel runs
- Ready tasks (from Coldwine's task proposals)
- Dispatches (from `ic.DispatchList`) -- shown in a simple list

**What is missing:**
- **Runs** -- the fundamental kernel concept. There is no `RunList` call in Bigend. The user cannot see active sprint runs, their phases, or their status from the Bigend tab.
- **Phase progress** -- no progress bars or phase timelines
- **Budget status** -- no budget information
- **Event stream** -- no events section
- **Per-run dispatch grouping** -- dispatches are listed flat, not grouped by run

The `loadDispatches()` method (`bigend.go:148-163`) calls `ic.DispatchList(ctx, false)` but never calls `ic.RunList()`. The dispatches are rendered without run context -- just agent name, status, and elapsed time.

**Smallest viable fix:** Add a `loadRuns()` method mirroring `loadDispatches()`, render a "Runs" section above or alongside Sessions showing active run ID + phase + status, and add a compact budget indicator. This would make the Bigend tab actually useful as a kernel monitoring surface. The `RunDetailPanel` component already exists (`run_detail_panel.go`) and can be reused in compact mode via `CompactRender()`.

---

### F3. Kernel unavailability silent on Bigend and Coldwine [P1 -- HIGH]

**Location:** `internal/tui/views/bigend.go:148-150`, `internal/tui/views/coldwine.go:188-189`

**Description:** When `iclient` is nil (Intercore unavailable), the following happens:

- **Bigend**: `loadDispatches()` returns `nil` immediately (`bigend.go:149`). The Dispatches section simply disappears from the view. No badge, no message, no indication that kernel observability is degraded. The "Sessions" header still renders, which could mislead users into thinking the dashboard is showing all available data.

- **Coldwine**: `loadEpicRuns()` returns `nil` immediately (`coldwine.go:189`). Sprint information disappears from epic details. The "d dispatch" hint disappears (`coldwine.go:627-629`). The "Create Sprint" and "Dispatch Task" commands are silently removed from the palette (`coldwine.go:869-898`). No message tells the user that kernel-dependent capabilities are unavailable.

- **Sprint tab**: Properly handles this -- shows "Intercore Unavailable" with install instructions (`run_dashboard.go:866-870`) and sidebar shows "ic unavailable" (`run_dashboard.go:533`).

- **Footer**: Shows `[offline -- reading local files]` badge when Intermute is unreachable (`unified_app.go:975-977`), but there is **no equivalent badge for Intercore unavailability**. The footer badge only covers the Intermute data source fallback, not the kernel connection.

**Smallest viable fix:** Add an `[ic offline]` footer badge when `iclient == nil`. In Bigend and Coldwine, add a degraded-state indicator where the Dispatches/Sprint sections would appear (e.g., dimmed text "Intercore unavailable -- sprint and dispatch features disabled").

---

### F4. Event stream uses polling with 10s sleep, not the streaming API [P2 -- MEDIUM]

**Location:** `internal/tui/event_watcher.go:54-93`, `pkg/intercore/events.go:14-57`

**Description:** The kernel client implements `EventsTail(ctx, runID, follow, opts)` which spawns a long-lived `ic events tail --follow` subprocess and streams events line-by-line over a channel. This is the correct mechanism for real-time event delivery.

However, the `EventWatcher` does not use it. Instead, it:
1. Calls `ic.RunList(ctx, true)` to find active runs
2. For each run, calls `ic.RunEvents(ctx, run.ID)` to batch-fetch all events
3. Filters to events from the last 30 seconds (`event_watcher.go:78`)
4. Sleeps for 10 seconds (`event_watcher.go:91`)
5. Repeats

This means:
- **Latency**: Events appear in the signals overlay up to 10 seconds after they occur. For phase changes and gate failures, this is a significant delay.
- **Redundant work**: Every poll re-fetches the entire event history for all active runs, discarding everything older than 30 seconds.
- **Missed events**: If an event occurs and another event follows within the same 30-second window, both appear. But if two events are more than 10 seconds apart but within the same poll window, duplicate filtering relies on the signal broker's ID-based dedup. Events that arrive between polls and fall outside the 30-second cutoff window could be missed entirely.
- **Blocking sleep**: `time.Sleep(10 * time.Second)` inside a `tea.Cmd` goroutine (`event_watcher.go:91`) blocks the goroutine and prevents prompt shutdown.

The `DispatchWatcher` uses `tea.Tick()` correctly (`dispatch_watcher.go:48`) -- the `EventWatcher` should follow the same pattern.

**Smallest viable fix (incremental):** Replace `time.Sleep(10 * time.Second)` with returning `eventWatcherTickMsg{}` and using `tea.Tick(10*time.Second, ...)` in the `Tick()` method. This fixes the blocking sleep and follows the DispatchWatcher pattern. Full fix: Switch to `EventsTail` with `--follow` per active run.

---

### F5. Registered agents not surfaced anywhere [P2 -- MEDIUM]

**Location:** `pkg/intercore/operations.go:239-263`, `pkg/intercore/types.go:170-178`

**Description:** The kernel tracks agents registered on runs via `RunAgentAdd`, `RunAgentList`, and `RunAgentUpdate`. The `RunAgent` type includes agent ID, type, name, dispatch ID, and status. This is distinct from dispatches -- agents persist across dispatch lifecycles (an agent can be registered, then dispatched multiple times).

No TUI view calls `RunAgentList()`. The Sprint tab shows dispatches but not the agent registry. The Bigend tab shows tmux-scraped panes but not kernel-registered agents. There is a complete disconnect between the kernel's agent model and what the TUI surfaces.

The vision describes Bigend migrating to `ic dispatch list --active` for agent monitoring (`autarch-vision.md:134`), but the intermediate step of showing registered agents alongside dispatches is missing.

**Smallest viable fix:** In the Sprint tab's `loadDetail()` method, add a `RunAgentList(ctx, runID)` call and render agents as a section below dispatches. Each agent entry would show name, type, status, and linked dispatch ID.

---

### F6. Artifact list not surfaced in Sprint tab [P2 -- MEDIUM]

**Location:** `pkg/intercore/operations.go:161-172`, `internal/tui/views/run_dashboard.go:342-372`

**Description:** The kernel client has `ArtifactList(ctx, runID, phase)` which returns all registered artifacts for a run. The `loadDetail()` method (`run_dashboard.go:342-372`) fetches run status, dispatches, budget, events, and gate check -- but **does not fetch artifacts**.

Artifacts are a core kernel concept: they represent the work products of each phase (plans, reviews, research results, code). Without artifact visibility, the user cannot verify that expected deliverables were produced for a given phase. They must use `ic run artifact list <runID>` from the CLI.

The `researchForSprint()` method (`run_dashboard.go:460-527`) creates artifacts but the user has no way to verify they were registered or browse the full artifact list for a run.

**Smallest viable fix:** Add `artifacts, _ := ic.ArtifactList(ctx, runID, "")` to `loadDetail()`, store it in the message, and add a "Phase Artifacts" section in `renderDocument()` listing artifact paths and types per phase.

---

### F7. Gate rules not browseable [P3 -- LOW]

**Location:** `pkg/intercore/operations.go:140-147`, `pkg/intercore/types.go:118-128`

**Description:** The kernel client has `GateRules()` which returns all configured gate transition rules with their required checks. The Sprint tab shows the current gate status (pass/blocked) with evidence conditions (`run_dashboard.go:735-782`), but there is no way to browse what the gate rules *require* for upcoming transitions.

This means the user can see "Gate blocked: artifact_exists" but cannot see what the next phase's gate requires before attempting advancement. They must use `ic gate rules` from the CLI to plan their work.

**Smallest viable fix:** Add a `/sprint gates` slash command in `SprintCommandRouter` that calls `GateRules()` and renders the transition requirements as formatted text in the chat panel. Future enhancement: show next-gate requirements inline in the phase timeline.

---

### F8. Sprint tab (SprintView) is a PRD sprint, not a kernel sprint [P2 -- MEDIUM]

**Location:** `internal/tui/views/sprint_view.go:1-561`

**Description:** There are **two different Sprint views** in the codebase:
1. `SprintView` (`sprint_view.go`) -- drives Gurgeh's 8-phase PRD generation via `arbiter.Orchestrator`. This is **not** a kernel rendering surface. It manages its own phases (vision, problem, users, features, CUJs, requirements, scope, acceptance) and owns LLM conversation sequencing. It has zero interaction with `intercore.Client`.
2. `RunDashboardView` (`run_dashboard.go`) -- the actual kernel sprint dashboard, which surfaces runs, phases, dispatches, budgets, gates, and events from Intercore.

The tab labeled "Sprint" in the unified app maps to `RunDashboardView` (the kernel surface) -- this is correct (`cmd/autarch/main.go:261`). However, `SprintView` is still used inside `GurgehView` for the PRD generation flow. The naming overlap is confusing but the tab wiring is correct.

**No fix needed for tab wiring.** The naming confusion is worth noting for documentation but does not cause user-facing issues.

---

### F9. Coldwine epic-to-run mapping depends on Intercore state store, not the run list [P3 -- LOW]

**Location:** `internal/tui/views/coldwine.go:188-219`

**Description:** Coldwine maps epics to kernel runs via `ic.StateGet(ctx, "epic.run_id", epicID)` -- a key-value lookup in Intercore's state store. This means:
- If the state key is never set (e.g., sprint created via CLI), the TUI shows no sprint association for the epic.
- If the state key is stale (sprint cancelled, new one created), the TUI shows the wrong run.
- There is no discovery mechanism -- Coldwine does not enumerate all runs and match by scope ID.

The kernel tracks `scope_id` on runs (`types.go:21`), which maps to epic IDs. The correct approach would be to query `RunList` and match `Run.ScopeID` to epic IDs, but `RunList` does not support filtering by scope.

**Smallest viable fix:** On `loadEpicRuns()`, after checking the state key, fall back to scanning `RunList(ctx, true)` for runs whose `ScopeID` matches the epic ID. This handles CLI-created sprints.

---

### F10. Dispatch token usage not displayed in Sprint tab dispatches [P3 -- LOW]

**Location:** `internal/tui/views/run_dashboard.go:784-831`, `pkg/intercore/types.go:58-59`

**Description:** The `Dispatch` type includes `InputTokens` and `OutputTokens` fields (`types.go:58-59`), but the Sprint tab's dispatch rendering (`renderDispatches()` at `run_dashboard.go:784-831`) only shows icon, ID prefix, agent, status, and exit code. Token consumption per dispatch is not shown.

This data is critical for budget analysis -- when the budget bar shows 80% consumed, the user needs to know which dispatches are consuming the most tokens. Currently they must use `ic dispatch status <id>` from the CLI.

**Smallest viable fix:** Append token info to the dispatch line: `if d.InputTokens+d.OutputTokens > 0 { line += fmt.Sprintf(" %s tok", formatTokens(int64(d.InputTokens+d.OutputTokens))) }`.

---

### F11. No "kill dispatch" affordance in any TUI view [P2 -- MEDIUM]

**Location:** `pkg/intercore/operations.go:107-110`

**Description:** The kernel client has `DispatchKill(ctx, dispatchID)` but no TUI view calls it. The Sprint tab shows running dispatches but provides no way to kill one. The only options are:
- Cancel the entire run (the `c` keybinding or "Cancel Sprint" command)
- Wait for the dispatch to complete or time out
- Drop to CLI: `ic dispatch kill <dispatchID>`

For long-running dispatches (reviews that hang, misconfigured agents), the inability to kill a single dispatch without cancelling the entire run is a significant gap.

**Smallest viable fix:** Add a `k` keybinding in the Sprint tab that kills the selected dispatch (if dispatches were selectable -- which they currently are not). Alternatively, add a `/dispatch kill <id>` slash command in `SprintCommandRouter`.

---

### F12. No live event stream tail in the Sprint tab [P3 -- LOW]

**Location:** `internal/tui/views/run_dashboard.go:833-864`

**Description:** The Sprint tab's "Recent Events" section (`renderEvents()`) shows the last 8 events from a batch fetch at load time. Events are only refreshed when:
- The user presses `ctrl+r` to reload
- A dispatch completes (triggers `loadDetail`)
- Phase advancement succeeds (triggers `loadDetail`)

Between these triggers, events are stale. The vision's "Autarch status tool" mockup (`autarch-vision.md:236-240`) shows a "live-updating" event stream. The `EventsTail` streaming API exists in the client but is unused.

**Smallest viable fix:** Add a periodic refresh (e.g., 5-second tick) that re-fetches events for the active run and updates the view. Full solution: use `EventsTail` with `--follow` for the selected run.

---

## Summary Matrix

| # | Finding | Priority | Vision Intent Gap | Kernel API Exists | TUI Surface |
|---|---------|----------|-------------------|-------------------|-------------|
| F1 | gate-override missing | P1 | Yes | `GateOverride()` | None |
| F1 | submit-artifact missing | P1 | Yes | `ArtifactAdd()` | Only research |
| F2 | Bigend has no runs | P1 | Yes | `RunList()` | None on Bigend |
| F3 | Silent kernel degradation | P1 | N/A | N/A | No badge/indicator |
| F4 | Polling not streaming events | P2 | Yes | `EventsTail()` | Polling with sleep |
| F5 | Agent registry invisible | P2 | Partial | `RunAgentList()` | None |
| F6 | Artifact list not shown | P2 | Yes | `ArtifactList()` | None |
| F7 | Gate rules not browseable | P3 | Partial | `GateRules()` | None |
| F8 | SprintView naming confusion | Info | N/A | N/A | Wiring correct |
| F9 | Epic-run mapping fragile | P3 | N/A | `StateGet()` | State-key only |
| F10 | Dispatch tokens not shown | P3 | N/A | Fields exist | Not rendered |
| F11 | No kill-dispatch affordance | P2 | N/A | `DispatchKill()` | None |
| F12 | No live event tail | P3 | Yes | `EventsTail()` | Batch only |

## Kernel Client Methods -- Usage Inventory

| Client Method | Used in TUI? | Where |
|---------------|-------------|-------|
| `RunCreate` | Yes | Coldwine, Sprint commands |
| `RunStatus` | Yes | Coldwine (epic runs), RunDashboard |
| `RunList` | Yes | RunDashboard, Sprint commands, EventWatcher |
| `RunAdvance` | Yes | RunDashboard |
| `RunCancel` | Yes | RunDashboard, Sprint commands |
| `RunPhase` | **No** | -- |
| `RunCurrent` | **No** | -- |
| `RunSet` | Yes | RunDashboard (auto-advance toggle) |
| `RunTokens` | **No** | -- |
| `RunBudget` | Yes | RunDashboard |
| `RunEvents` | Yes | RunDashboard, EventWatcher |
| `EventsTail` | **No** | Client only, never called |
| `DispatchSpawn` | Yes | Coldwine, Sprint commands |
| `DispatchStatus` | **No** | -- |
| `DispatchList` | Yes | Bigend, RunDashboard, DispatchWatcher, Sprint commands |
| `DispatchWait` | **No** | -- |
| `DispatchKill` | **No** | -- |
| `GateCheck` | Yes | RunDashboard |
| `GateOverride` | **No** | -- |
| `GateRules` | **No** | -- |
| `ArtifactAdd` | Yes | RunDashboard (research only) |
| `ArtifactList` | **No** | -- |
| `StateSet` | Yes | Coldwine (epic.run_id, task.dispatch_id) |
| `StateGet` | Yes | Coldwine (epic.run_id, task.dispatch_id) |
| `StateDelete` | **No** | -- |
| `LockAcquire` | **No** | -- |
| `LockRelease` | **No** | -- |
| `RunAgentAdd` | **No** | -- |
| `RunAgentList` | **No** | -- |
| `RunAgentUpdate` | **No** | -- |
| `SentinelCheck` | **No** | -- |

**Summary:** 15 of 28 client methods (54%) are unused in the TUI layer. Of these, 7 represent kernel capabilities that users must access via CLI: `GateOverride`, `GateRules`, `ArtifactList`, `DispatchKill`, `RunAgentList`, `EventsTail`, and `RunCurrent`.

---

## Positive Observations

1. **RunDashboardView is well-built.** It loads runs, dispatches, budget, events, and gate status in a single async batch. Phase timeline rendering is clear. Budget bar uses color coding. Gate evidence conditions are individually enumerated. This is close to the vision's "Autarch status tool" mockup.

2. **RunDetailPanel is reusable.** The extracted `RunDetailPanel` component (`run_detail_panel.go`) with `Render()` and `CompactRender()` methods enables embedding kernel state in any view. This is the right abstraction for cross-tab kernel observability.

3. **DispatchWatcher uses correct Bubble Tea patterns.** It uses `tea.Tick` for scheduling, broadcasts completions to all views (not just the active one), and handles dedup via known-status tracking.

4. **EventWatcher-to-signal conversion is comprehensive.** The `eventToSignal()` function (`event_watcher.go:104-181`) covers phase changes, gate blocks, budget exceeded, dispatch completed/failed, and run cancelled -- all mapped to appropriate severity levels.

5. **SprintCommandRouter provides CLI parity for slash commands.** The `/sprint status|advance|cancel|list|create` and `/dispatch list|spawn` commands give chat-panel users access to key kernel operations without switching tabs.

6. **Graceful degradation pattern is consistent.** All views check `v.iclient == nil` before kernel operations. The Sprint tab shows "Intercore Unavailable" with actionable guidance. The pattern is correct even if the indicator is missing from some views (F3).
