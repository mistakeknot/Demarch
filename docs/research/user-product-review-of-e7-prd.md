# User & Product Review: Bigend Migration to Kernel State (E7)

**PRD:** `/root/projects/Interverse/docs/prds/2026-02-20-bigend-kernel-migration.md`
**Brainstorm:** `/root/projects/Interverse/docs/brainstorms/2026-02-20-bigend-migration-brainstorm.md`
**Bead:** iv-ishl
**Reviewer:** Flux-drive User & Product Reviewer
**Date:** 2026-02-20

---

## Primary User and Job Statement

The primary user is the developer who runs multiple AI agents across multiple projects simultaneously. Their job is mission control: knowing which agents are running, which are blocked, which need attention, and how much compute is being consumed — all at a glance, without navigating into individual project directories or attaching to tmux sessions.

This is not a project management user (who thinks in terms of backlogs and timelines). This is an operator user who thinks in terms of current system state. The key question they repeat throughout their session is: "What needs my attention right now?"

This distinction matters throughout this review because several design decisions in the PRD optimize for a project-management mental model (projects as primary, runs under projects, navigate in to see detail) rather than an operator mental model (cross-project status at a glance, blocked agents surfaced immediately).

---

## Summary Verdict

The migration strategy is sound. Additive enrichment with vertical slices is the right approach — it delivers value incrementally and avoids breaking existing functionality. The underlying data layer (internal/status/data.go) is proven, and the exec-based ic CLI access is the right abstraction boundary for now.

The problems are in the UX layer. Three of the five focus areas have issues that, if unresolved, will make the E7 dashboard harder to use than the current pre-migration state:

1. The 4-state status model discards the one distinction operators care about most — blocked vs idle.
2. The navigation model buries the cross-project "what's running now" question.
3. The dashboard metrics surface throughput counts but not the actionable signal (blocked agents, phase duration).

These are all fixable within the E7 scope, but they require explicit decisions in the PRD before implementation.

---

## 1. Navigation: Projects-as-Primary with Runs Underneath

### 1.1 The mental model mismatch

Projects-as-primary is the right model for project management (planning, backlog, history). It is the wrong primary model for mission control (current state, triage, intervention).

The layout from the brainstorm:

```
+- Projects ------+- Project Detail ----------------------------------------+
| Interverse      | RUNS                                                     |
|   Autarch       | tkjd6vhn  Cost scheduling  [phase P2]                    |
|   Clavain       | 6m0lbold  Skip Test        [phase P1]                    |
|                 |                                                          |
|                 | DISPATCHES (tkjd6vhn)                                    |
|                 | D12  reviewer-arch  running  2m14s                       |
+-----------------|----------------------------------------------------------+
```

To answer "what is running right now?", the operator must:
1. Select a project from the sidebar
2. Scan the runs in the main pane
3. Select a run to see dispatches
4. Repeat for each project

If their work is spread across 3 projects, they navigate 3 times to build a complete picture. The dashboard stats row shows aggregate counts (3 active runs, 7 dispatches), but counts alone are not triage-sufficient — the operator needs to know which specific runs are in which states.

### 1.2 What is missing

A top-level cross-project active-runs surface. This does not replace the project-scoped detail view. It adds a triage surface that serves the operator's primary question.

The pattern is well-established: it is how Bigend already handles Intermute agents (a flat cross-project agent list in the main dashboard view). Runs should follow the same pattern — a global runs view on the dashboard tab, with project-scoped detail available when navigating into a project.

The brainstorm's resolved decision "Navigation axis: Projects as primary — Preserves existing mental model; runs appear under projects" is correct as a secondary view. The missing piece is a primary view that shows cross-project active runs in a single flat list.

### 1.3 Recommendation

Add a cross-project "Active Runs" section to the dashboard tab (the top-level view, not the project detail view). Columns: project name, run ID, goal (truncated), current phase, phase duration, status indicator. Navigate from this list into the project detail for full run context. This is additive and does not change the project-scoped detail view — it gives the operator a triage entry point that matches their job.

---

## 2. The 4-State Status Model

### 2.1 The Waiting/Idle collapse is the most significant product risk in E7

The 4-state model maps: working/running → Active; waiting/blocked/idle → Waiting; completed/done → Done; failed/error/cancelled/timeout/stalled → Error.

The critical collapse is `waiting`, `blocked`, and `idle` all mapping to the same `Waiting` state.

For an operator, these three conditions require completely different responses:
- `blocked` — needs immediate intervention. Agent cannot proceed without human action (permission prompt, gate failure, missing dependency, human-approval loop). This is the highest-priority signal in mission control.
- `waiting` — agent is in a dependency wait or interagent coordination pause. May be self-resolving. Check in 5 minutes.
- `idle` — agent has finished its current work and is dormant. No action needed.

When all three display identically, the operator has no reliable way to know whether their 4 "Waiting" agents need them now or can be left alone. They must click into each agent to determine which case applies.

The existing statedetect model (4-tier NudgeNik detection: hook → pattern → repetition → activity) already distinguishes these cases. F8's stated goal is to "surface the existing rich detection results" — but collapsing `blocked` into the same visual state as `idle` and `waiting` actually discards the richest part of that detection.

### 2.2 The stalled → Error mapping creates false alarms

`stalled` is mapped to `Error` alongside `failed`, `cancelled`, and `timeout`. These are semantically different:
- `failed`, `cancelled`, `timeout` — terminal states. The agent is done, with a bad outcome. Requires investigation and cleanup.
- `stalled` — a repetition-loop detection. The agent may be about to self-recover, or may need a nudge. It is not terminal.

Grouping stalled with terminal failures will cause operators to treat self-resolving stalls as errors requiring cleanup — creating unnecessary interruption of in-progress work.

### 2.3 The Unknown → Active default creates phantom-active counts

F8: "Unknown/empty status maps to Active (safe default — prefer showing something)."

This is the wrong safe default for a dashboard. An agent with unknown status is most likely a stale process or a session where status detection failed. Displaying it as Active inflates the active count in dashboard metrics (F4), making the "Active Runs: N" stat unreliable.

For dashboard users, "prefer showing something" should mean "prefer showing uncertainty" — display Unknown as a distinct gray/dim state that clearly communicates "status unavailable." This is not a semantic status claim; it is an honest display of a detection gap.

### 2.4 Recommended model refinement

Instead of 4 states, define 5:
- `Active` — working, running (agent is doing compute)
- `Blocked` — waiting-on-human, permission-required, gate-failed (needs operator intervention)
- `Waiting` — inter-agent dependency, queue pause (self-resolving, low urgency)
- `Done` — completed, finished (no action needed)
- `Error` — failed, cancelled, timeout (terminal, needs review)

And one display state (not a kernel state):
- `Unknown` — status detection unavailable (shown as dim/gray, excluded from Active count)

`Stalled` maps to `Blocked` rather than `Error` — it signals "this agent may need a nudge" which is intervention-appropriate but not terminal.

The acceptance criteria should define the exact mapping and the visual treatment (icon + color) for each of the 5 states. The mapping function `UnifyStatus()` should be updated to reflect this.

---

## 3. The Unified Event Stream

### 3.1 Mixed sources are legible only with visual differentiation

The unified Activity stream merges kernel events, Intermute events, and potentially tmux state events into one timeline. The design is correct — one timeline is better than three separate feeds. The risk is that without visual differentiation, the stream becomes noise.

Kernel events describe structured work progress (phase.advance, gate.passed, dispatch.completed). Intermute events describe coordination (agent.registered, inbox.message). These have very different operator significance. An operator scanning the stream needs to pattern-match instantly — "is this a phase transition I should track, or a routine agent registration?"

The brainstorm specifies a `Source` field on the Activity struct and filtering by source. Filtering is opt-in and requires the operator to know which sources they want. The default unsorted merged view is the first impression — and it needs to be scannable without enabling filters.

### 3.2 Source prefix convention

The LogPane (used in F5) is the rendering surface. The acceptance criteria should specify:
- A 1-2 character bracketed source prefix per event, with per-source color: `[K]` kernel (blue), `[M]` Intermute (green), `[T]` tmux (gray)
- This prefix is always shown, not conditional on filter state
- Filter by source hides rows from unwanted sources; it does not remove the prefix from visible rows

This is a low-implementation-cost change that transforms the stream from "mixed noise" to "scannable multi-source timeline."

### 3.3 Event ID dedup has a correctness bug

F5 specifies dedup by event ID. Kernel events are fetched per-project, each from its own SQLite DB. Each DB has its own auto-increment sequence. Two projects will have overlapping event IDs (both have event ID 1, event ID 2, etc.). Deduplication by event ID alone will silently drop real events from one project when they share an ID with an already-seen event from another project.

The composite dedup key must be `(project_path, event_id)`. The Activity struct already carries ProjectPath — the fix is to use it in the dedup map key.

This is a correctness issue that will manifest silently: events disappear from the stream with no error, and the operator sees an incomplete history. It is particularly insidious because it is nondeterministic — which project's events survive depends on polling order.

### 3.4 Intermute/kernel agent coexistence creates duplicate representation

F2 specifies that Intermute agents and kernel dispatches coexist. A logical agent may appear in both the Intermute agent section (registration/inbox data) and the kernel dispatch section (lifecycle data). If both sections are visible simultaneously in the project detail pane, the operator sees two entries for the same agent — one from each source.

There is no merge key specified. If the Intermute agent name matches the ic dispatch agent name (same string), they can be merged into a single row showing both inbox state and lifecycle. If they differ, they cannot be automatically merged and must be displayed as separate sections with clear labeling.

The PRD must resolve this before implementation since it affects the data model and the detail pane layout. The resolved decisions table says "Intermute provides registration/inbox, ic provides lifecycle" — the missing piece is how these two data sources combine into a single display row.

---

## 4. Dashboard Metrics

### 4.1 The stats row shows throughput, not attention

F4 defines KernelMetrics: ActiveRuns, ActiveDispatches, TotalTokensIn, TotalTokensOut. The TUI stats row shows: Projects | Active Runs | Dispatches | Tokens.

These metrics answer "how much is happening?" They do not answer "what needs my attention?" For an operator, the most actionable metric is blocked agent count — agents that cannot proceed without human intervention.

The current metrics row has no signal for blocked state. An operator looking at "Active Runs: 5" cannot tell if all 5 are running clean or 3 are blocked on permission prompts. They must navigate into each project and inspect each run's dispatch list.

### 4.2 Phase duration is a missing high-value signal

A run stuck in the same phase for an abnormally long time is the most common early indicator of a problem. The current run list (F6) shows phase (current state) but not phase duration (time in current state). Without this, the operator cannot distinguish a healthy run from a stalled one at list-scan speed.

Phase duration belongs in the run list as a column. It is the single highest-information-density addition to the list view because it converts the run list from a status display to an anomaly detector.

Format: compact elapsed time since phase entry ("14m", "2h3m"). Color: green (normal), yellow (>1h), red (>4h). Thresholds are approximate and do not need to be configurable in v1.

### 4.3 Token display should proxy cost, not expose raw counts

F4 specifies: "Token totals formatted with comma separators (e.g., 12,450 in / 3,200 out)."

Raw token counts require mental arithmetic to assess significance. The operator wants to know "am I burning through money faster than expected?" not "are there more tokens than last time I checked?"

If dispatch metadata includes model name, compute an estimated cost using static pricing table (stored in the binary, updated manually). Display: "$0.47 est." with the token breakdown in a tooltip or detail pane.

If model information is not available or pricing is uncertain, simplify to output-only token count (output tokens dominate cost) with a note. The in/out split is useful in a per-run detail view but adds noise at the dashboard aggregate level.

---

## 5. The Two-Pane Layout

### 5.1 Focus model is undefined

F6 specifies arrow keys navigate the run list and Enter selects a run. But:
- Arrow keys are also used in the project sidebar
- The PRD does not specify which pane has focus on initial project selection
- The PRD does not specify how focus transfers between sidebar, run list, and run detail pane
- Tab behavior is unspecified

In Bubble Tea, focus is explicit. The parent model must route key events to the correct child model based on focus state. Without a specified focus model, the implementer makes an arbitrary decision that users encounter as inconsistent behavior.

The existing paneWidths() logic handles layout geometry, not focus. A third focusable pane (the new run list) added without a specified focus ring is a behavior gap.

Specify: Tab (or h/l) cycles focus between sidebar, run list, and run detail. Focused pane shows a distinct border color or header highlight. Arrow keys navigate within the focused pane only. This should be in F6's acceptance criteria and the key shortcuts should appear in Bigend's help text.

Check for conflicts with existing CommonKeys in pkg/tui/ — particularly any existing Tab or h/l bindings.

### 5.2 Narrow terminal collapse loses selection state

F6: "Layout adapts to terminal width (collapses detail below minimum width)."

The collapse behavior is underspecified:
- What is the minimum width threshold?
- Does the collapsed view show the run list or the detail view?
- When the terminal widens, is the selected run restored?
- What keyboard interaction exists in the collapsed state?

In practice, terminals narrower than ~100 columns are common in SSH sessions and tmux splits. An operator who has selected a run and is watching its events will lose that view when they resize their terminal or arrange their tmux layout. If the selected run is not preserved in state, they must re-navigate after every resize.

Specify: minimum split width is 100 columns. Below 100 columns, show run list only. Selected run is preserved in model state and restored when terminal widens. In list-only view, Enter opens a full-screen detail overlay with Esc to return. Add this to F6 acceptance criteria.

### 5.3 Goal field truncation is unspecified

F6 lists "goal" as a run list column. Run goals are free-form text of arbitrary length. In a fixed-width list column, untruncated goal text will corrupt the layout or wrap misaligned columns.

Specify: goal is right-truncated to available column width minus 2 characters with an ellipsis. Fixed-width column allocations for all other fields (ID: 8, status: 1, phase: 12, progress bar: 8, complexity: 2, duration: 6 — goal fills remaining). Full goal text appears in the detail pane header.

This prevents a common TUI layout regression where test data passes (short strings) but production use fails (long user-supplied strings).

---

## 6. Flow Analysis

### 6.1 Happy path: operator opens Bigend, scans for active work

1. Bigend starts, Aggregator.Refresh() runs.
2. Scanner detects projects with .clavain/intercore.db.
3. enrichWithKernelState() fetches runs, dispatches, events, tokens per project.
4. TUI renders dashboard tab: stats row shows aggregate counts, agent list shows cross-project agents.
5. Operator selects a project in sidebar.
6. Project detail pane shows run list (F6) and run summary.
7. Operator selects a run.
8. Detail pane splits: left shows run list, right shows selected run's dispatches/events/tokens.
9. Operator identifies blocked dispatch, navigates to tmux session.

This path is coherent. The gap is step 4: the dashboard tab does not show a cross-project run list, so the operator cannot identify which projects have active runs without visiting each one.

### 6.2 Error path: ic CLI not in PATH

F1: "fail-open: no ic = no kernel data." The TUI renders without kernel data — projects without .clavain/intercore.db appear as before, projects with .clavain/intercore.db appear with the HasIntercore flag but no run/dispatch/event data.

Unspecified: Does the TUI show any indication that kernel data is unavailable? If a project has HasIntercore=true but all kernel calls fail, the operator sees a project with 0 runs — indistinguishable from a project with no runs. This is a silent failure that gives the operator false confidence ("nothing is running").

Add a visual indicator for kernel-aware projects where kernel data fetch failed: a warning icon or a "kernel unavailable" label next to the project in the sidebar. This distinguishes "zero active runs" from "could not check for runs."

### 6.3 Error path: single project's ic exec fails mid-refresh

With 5 projects in parallel refreshes (recommended goroutine pool approach), one project's ic exec may fail while others succeed. The PRD does not specify whether a per-project failure blocks the full State update or only that project's kernel data.

The data model uses maps keyed by project path — so a per-project failure should only affect that project's entries in the map, not the full state. This should be explicit in the acceptance criteria: "Per-project kernel data fetch failure logs an error and leaves that project's kernel state stale from the previous cycle. Other projects are unaffected."

### 6.4 Missing flow: pagination for large run histories

FetchRuns() fetches all runs for a project. A project with 100+ completed runs will return a large result that is mostly noise in a mission control context. The run list has no pagination or filtering spec. Operators will see a long list dominated by old Done/Error runs and have to scroll past them to find active work.

Specify a default filter: run list shows active and recent runs by default (active runs first, then Done/Error runs from the last 24h). A keyboard shortcut ("a" for "all") shows the full unfiltered run history. This keeps the mission control view signal-dense without discarding historical data.

### 6.5 Edge case: project renamed or moved mid-session

The maps in aggregator.State use project path as the key. If a project is moved or renamed between Aggregator.Refresh() cycles, the old path key still has data in the map and the new path creates a new empty entry. This produces a ghost project in the TUI until the stale path's data is flushed.

This is a pre-existing issue with the filesystem-scan-based discovery, not new to E7. But it becomes more visible with kernel data because the ghost project will appear to have runs (stale data from the old path). The flush logic (or staleness detection) should be mentioned in F1 since enrichWithKernelState() propagates the bug.

---

## 7. Product Validation

### 7.1 Problem definition is strong

The problem is clearly stated and the evidence is credible: a data layer exists (internal/status/data.go, proven in autarch status) and is not connected to the main dashboard. This is a straightforward gap, not a speculative opportunity. No user research is needed — the missing connection is observable in the code.

### 7.2 Solution fit is correct for the migration scope

Additive enrichment is the right strategy. Running old and new pipelines in parallel removes migration risk, vertical slices deliver incremental value, and rollback is trivial. The decision to use exec-based ic CLI rather than direct SQLite reads is the right tradeoff — it stays decoupled from schema and reuses proven code.

The decision to keep autarch status as a separate tool is correct. Different use cases (quick single-project check vs. full multi-project dashboard) should not be collapsed.

### 7.3 Opportunity cost check

The 8 beads in E7 represent significant engineering effort. The opportunity cost question: is getting kernel data into Bigend the highest-value work, or would something else deliver more operator value?

The answer is yes, this is the right work to do now. The pre-migration Bigend has a TODO stub for its activity feed and no run/phase/dispatch visibility. These are fundamental gaps in a mission control tool. Filling them is not incremental — it enables a qualitatively different operator experience.

### 7.4 Success signal

The PRD has no stated success metric. What would indicate E7 worked?

Proposed success signal: after E7 ships, the operator can answer "which of my agents is blocked right now?" in under 30 seconds without leaving Bigend. This is measurable (timing, count of navigations) and directly tied to the operator job statement.

Secondary signal: the autarch status TUI is used less frequently after E7 (because Bigend provides the same information plus cross-project context). If autarch status usage drops after E7 ships, Bigend has successfully absorbed the single-project monitoring use case.

### 7.5 Non-goal boundary is appropriate

Deferring write operations, signal broker integration, follow mode, and direct SQLite reads is correct. These are all v2 improvements that do not block the core data layer migration. The decision to remove old data sources in E9 rather than E7 is also correct — removing dependencies before the replacement is stable is how you create regressions.

---

## 8. Scope Assessment

The 8-slice structure is sound. The sequencing dependency graph in the brainstorm (foundation slices first, dependent slices second, layout last) is the correct execution order.

One scope concern: the 4-state status model (F8) is listed as a foundation slice that other slices depend on. If the status model ships with the Waiting/Idle collapse described in this review, every subsequent slice that uses StatusIndicator will inherit the confusing behavior. The status model decision should be made and finalized before any dependent slices begin implementation.

A second scope concern: F5's dedup logic and F3's event merging are listed as dependent on F1 (project discovery), but they have a correctness dependency on each other — the dedup key design affects the merged Activity struct design. These two acceptance criteria should be reviewed together before implementation of either begins.

The scope boundary (read-only dashboard, no write operations) is clean and correctly enforced across all 8 slices.

---

## 9. Prioritized Issues

### P0

**Issue 1: 4-state model collapses Blocked/Waiting/Idle — hides the most actionable operator signal.**
The mapping `waiting/blocked/idle → Waiting` makes it impossible to distinguish agents that need immediate human intervention from agents that are self-resolving or dormant.
Recommendation: Expand to 5 states: Active, Blocked (needs intervention), Waiting (self-resolving), Done, Error. Map stalled → Blocked rather than Error. The UnifyStatus() function and StatusIndicator must reflect this before any dependent slice ships.

**Issue 2: Unknown/empty status defaults to Active — creates phantom-active agents in dashboard metrics.**
The `Unknown → Active` default inflates the Active count in the stats row (F4) and makes the dashboard metrics unreliable.
Recommendation: Unknown maps to a distinct display state (dim/gray, excluded from Active count, labeled "status unavailable"). This is a display state, not a kernel state.

### P1

**Issue 3: Projects-as-primary navigation buries the cross-project triage view.**
Operators cannot answer "what is running right now?" without visiting each project individually. The dashboard tab needs a cross-project active runs surface.
Recommendation: Add a cross-project run list to the dashboard tab: project, run ID, goal, phase, phase duration, status.

**Issue 4: Two-pane layout focus model is undefined.**
Focus transfer between sidebar, run list, and run detail is unspecified in F6. This will produce inconsistent keyboard behavior.
Recommendation: Specify focus ring (Tab or h/l), focused-pane visual indicator, and include in F6 acceptance criteria.

**Issue 5: Dashboard metrics missing blocked-agent count — the highest-value operator signal.**
The stats row (F4) shows total active counts but no blocked count. Operators cannot triage without knowing how many agents need intervention.
Recommendation: Add BlockedAgents to KernelMetrics. Show Blocked count in warning color if >0. Make it navigable (pressing the metric jumps to a filtered blocked-agent view).

**Issue 6: Run list missing phase duration — the primary anomaly detection signal.**
Without time-in-current-phase, the run list cannot distinguish healthy runs from stalled ones.
Recommendation: Add a phase duration column to the run list. Color-coded: green (normal), yellow (>1h), red (>4h).

**Issue 7: Unified event stream lacks visual source differentiation in the default unfiltered view.**
Mixed kernel/Intermute/tmux events without source prefixes create noise that operators cannot pattern-match.
Recommendation: Add per-source prefix with per-source color ([K]/[M]/[T]). Always visible, not conditional on filter state.

### P2

**Issue 8: Event ID dedup is per-ID, not per (project, ID) — will silently drop events.**
SQLite auto-increment sequences across project DBs overlap. The dedup map must use (project_path, event_id) as the composite key.
File: F5 acceptance criteria and the Activities dedup implementation.

**Issue 9: Intermute agent / kernel dispatch coexistence has no merge key.**
Same agent may appear in both the Intermute agents section and the kernel dispatches section with no merge key. Requires an explicit design decision before implementation.
Recommendation: Specify the merge key (agent name string, if consistent) or explicit separate sections with clear labels.

**Issue 10: Token display exposes raw counts rather than cost-proxied signal.**
Raw in/out token counts require mental arithmetic. Prefer estimated cost or output-token-only proxy at the dashboard aggregate level.
Recommendation: Estimated cost if model pricing is available; output-only count with emphasis if not.

**Issue 11: Narrow-terminal collapse behavior is underspecified (F6).**
Minimum width threshold, selection state preservation on resize, and keyboard interaction in collapsed mode are all undefined.
Recommendation: Specify minimum width (100 columns), state preservation, and Enter-for-overlay pattern.

**Issue 12: Goal field in run list has no truncation specification.**
Free-form goal text of arbitrary length will corrupt the layout.
Recommendation: Right-truncate to column width minus 2 with ellipsis. Full text in detail pane header.

### P3

**Issue 13: Sidebar run count badge ambiguity — active vs total.**
"[2 runs]" could mean 2 active or 2 total. The mission control context calls for active-only.
Recommendation: Badge shows active runs (Active + Blocked states). Zero active runs shows no badge or muted "[0]".

**Issue 14: Refresh coalescing open question is underweighted.**
Sequential ic exec calls (4 per project × 5 projects × 50ms) may consume ~1,000ms of the 2-second refresh cycle.
Recommendation: Resolve before implementation: parallelize exec calls with a goroutine pool (bounded semaphore) in enrichWithKernelState(). Specify this in F1's acceptance criteria.

**Issue 15: Web/TUI parity is assumed but not independently specified.**
Web acceptance criteria describe layout concepts that are TUI-driven and may not translate cleanly to HTML templates.
Recommendation: Separate web acceptance criteria specify data requirements (not layout). TUI is primary surface; web is read-only monitoring.

**Issue 16: No success metric defined.**
The PRD has no measurable outcome criteria.
Recommendation: Success signal: operator can answer "which of my agents is blocked right now?" in under 30 seconds without leaving Bigend. Secondary: reduced autarch status usage post-ship.

---

## 10. Questions That Could Change Implementation Direction

1. **Should the 4-state model be expanded to 5 before any dependent slice ships?** If yes, F8 scope increases slightly but all dependent slices (F2, F5, the stats row in F4) inherit the correct behavior from the start. If no, the model ships with the Blocked/Waiting/Idle collapse and requires a second pass.

2. **Do Intermute agent names and ic dispatch agent names share a common identifier?** If yes, the two data sources can be merged per-row (the cleaner UX). If no, they must be displayed as separate sections with explicit labeling. This is an implementation-time data archaeology question, but it should be answered before F2 is coded.

3. **What is the actual per-project ic exec call count per refresh cycle?** The brainstorm estimates 50ms per call, but does not count how many calls FetchRuns + FetchDispatches + FetchEvents + FetchTokens represents. At 5 projects × 4 calls × 50ms = 1,000ms — half the refresh cycle. Is this acceptable, or does enrichWithKernelState() need to parallelize before the first slice ships?

4. **What is the default run list filter?** All runs (including historical Done/Error), or only active + recent runs? The answer determines whether the run list is useful for triage (active-first, recent-only default) or for project history (all runs). The mission control use case calls for the former.

5. **Is the web surface a real monitoring surface or a documentation artifact?** If actual operators use the web view in production, the web acceptance criteria need more specificity. If it is primarily a "nice to have" for async review, the acceptance criteria can remain vague and implementation can be minimal.

---

## Appendix: Reference Patterns from Prior Research

The TUI tools research (`/root/projects/Interverse/docs/research/find-tui-tools-matching-autarch-subapps.md`) identified directly applicable patterns for E7:

- **agent-deck's 3-state status model** distinguishes Running/Waiting/Idle with content hashing and 2-second cooldown — directly applicable to resolving the Blocked/Waiting/Idle collapse in F8.

- **lazyactions' two-pane lazygit layout** with context-sensitive right pane is the established pattern for list+detail. Their key insight: the detail pane changes content on navigate, no explicit "open" required. F6's Enter-to-select pattern creates an extra step that the lazygit pattern eliminates.

- **claude-swarm's htop-style layout** with cost column per agent is directly applicable to the dashboard metrics gap — cost (or a proxy) should be a visible column, not a detail-pane-only value.

- **tmuxcc's approval flow** surfaces blocked agents without requiring tmux attach. This is the blocked-agent-count feature requested in issue 5 above — a pattern that is proven in the wild for this exact use case.

The prior research recommends the 3-state status detection (agent-deck) as the single highest-priority adoption for Bigend. The E7 4-state model goes in the opposite direction — collapsing states. This tension should be explicit in the design decision.
