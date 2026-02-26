# UX Review: Cross-Tool Composition in Autarch

> **Reviewer:** fd-ux-cross-tool-composition (product experience architect)
> **Lens:** Progressive disclosure and flow continuity across multi-tool composition
> **Scope:** Cross-tool handoffs, message routing, signal consumption, and context bridging
> **Date:** 2026-02-25

---

## Executive Summary

Autarch's 5-tab TUI (Bigend, Gurgeh, Coldwine, Sprint, Pollard) has a well-designed core architecture for cross-tool composition: `SpecHandoffMsg` for Gurgeh-to-Coldwine transitions, `DispatchCompletedMsg` fan-out to all views, and a signal system with per-tool emitters. However, the composition pipeline has several flow breaks where the user must perform manual bridging work that the system could handle automatically. The most significant gap is the Gurgeh-to-Coldwine handoff, which navigates to Coldwine and displays a message but does not trigger epic generation -- leaving the user to manually invoke it. The Pollard-to-Gurgeh insight-to-spec link is similarly one-directional. The signals overlay is read-only with no drill-down actions. Together these gaps mean a user moving through the documented Gurgeh-to-Coldwine-to-Pollard pipeline must make 3-4 manual context switches that could be automated.

---

## Finding 1: SpecHandoffMsg Navigates but Does Not Generate

**Priority:** P1 (high)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh.go:435-448` (emission)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:508-516` (routing)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go:90-101` (reception)

**Description:**
Gurgeh's "Generate Epics" command (palette action at line 435) emits `SpecHandoffMsg` with the spec ID and title. `UnifiedApp.Update()` correctly catches this at line 508, calls `SetHandoffSpec()` on `ColdwineView`, and switches to the Coldwine tab. However, `SetHandoffSpec()` only does two things: (1) attempts to select the first epic matching the spec ID (which will match nothing if no epics exist yet, since this is supposed to trigger generation), and (2) adds a system chat message saying "generate or review epics for this spec."

The name "Generate Epics" implies automation, but the user arrives at Coldwine with a chat message instructing them to generate epics manually. There is no `tea.Cmd` returned from `SetHandoffSpec()` to kick off `GenerateEpics` (which exists at `internal/coldwine/initflow/generate.go:40`). The user must then use the palette or slash command to actually create epics.

**Impact:** The primary documented cross-tool flow (FLOWS.md section 2) breaks at the handoff point. Users experience a jarring expectation mismatch: they invoked "Generate Epics" but landed at an empty Coldwine tab with a hint.

**Smallest viable fix:** Add an optional `autoGenerate bool` field to `SpecHandoffMsg`. When true, `SetHandoffSpec()` should return a `tea.Cmd` that calls the epic generation initflow with the spec context. The `switchDashboardTab` call at line 516 would need to batch this cmd with the tab switch. Alternatively, have `ColdwineView.SetHandoffSpec()` emit a `tea.Cmd` (requires changing it from a setter to return a command), and batch that into the `switchDashboardTab` call.

---

## Finding 2: Messages Route Only to Active View (Except Dispatch)

**Priority:** P2 (medium)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:560-564` (default message routing)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:305-320` (dispatch fan-out)

**Description:**
The default message routing at line 560-564 sends non-key messages only to `a.currentView`:

```go
if a.currentView != nil {
    var cmd tea.Cmd
    a.currentView, cmd = a.currentView.Update(msg)
    return a, cmd
}
```

Only `dispatchBatchMsg` (lines 305-320) fans out to all views. This means:

1. **Research progress messages** (`research.RunStartedMsg`, `HunterUpdateMsg`, `RunCompletedMsg`) from the coordinator only reach PollardView if the Pollard tab is active. If the user triggers research from the Gurgeh arbiter's quick scan and switches to a different tab, research progress messages are dropped silently.

2. **Signal broker messages** (`brokerOverlaySignalMsg`) reach the overlay because it is handled before view routing (lines 518-520), which is correct. But any signal that should update a tool's internal state (e.g., a `research_invalidation` signal that should mark a Gurgeh spec as stale) has no path unless that tool's view is active.

3. **Sync completion** (`syncCompletedMsg`) from Coldwine only reaches Coldwine if that tab is active. If the user switches away during a sync, the result is silently dropped.

**Impact:** Users lose feedback on background operations when they switch tabs during long-running processes. Research runs can complete without any visible indication if the user is on a different tab.

**Smallest viable fix:** For research messages specifically: buffer them in the coordinator and replay on `Focus()`. For the general case, add a `BackgroundUpdate(msg) tea.Cmd` method to the View interface that views can optionally implement for messages that matter even when the view is not active.

---

## Finding 3: Pollard "Link Insight" Is Fire-and-Forget with No Cross-Tool Navigation

**Priority:** P2 (medium)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go:514-541` (Link Insight command)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go:135-141` (insightLinkedMsg handler)

**Description:**
The "Link Insight" palette command (line 514) links an insight to the first validated spec by calling `client.LinkInsight()`. On success, it displays a chat message: "Linked insight X to spec Y". However:

1. The user has no way to navigate to the linked spec from here. There is no "View in Gurgeh" action after linking.
2. The link target is auto-selected (first validated spec, fallback to first spec) with no user choice. If multiple specs exist, the user cannot select which one.
3. After linking, Gurgeh has no awareness that a new insight was linked. The GurgehView does not reload or display insight links anywhere in `renderDocument()` (lines 328-376 -- only Vision, Problem, Users are shown; no insight section).
4. Conversely, `PollardView.renderDocument()` shows `i.SpecID` (line 392) if an insight has a linked spec, but there is no action to navigate to that spec.

**Impact:** The `InsightLink` type documented in FLOWS.md (section 4) exists in the data model but its output is not visibly consumed by the downstream tool (Gurgeh). The link is created in the backend but invisible from the spec side. Users must mentally track which insights they linked to which specs.

**Smallest viable fix:** (a) Add `Linked Insights` section to `GurgehView.renderDocument()` that queries `client.ListInsights(specID, "")`. (b) Add an "enter" key handler on `insightLinkedMsg` that emits a cross-tab navigation message (analogous to `SpecHandoffMsg` but Pollard-to-Gurgeh). (c) Add a spec selector to the "Link Insight" command instead of auto-selecting.

---

## Finding 4: Signals Overlay Is Read-Only -- No Drill-Down or Action

**Priority:** P2 (medium)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/signals_overlay.go:114-143` (key handling)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/signals_overlay.go:244-287` (signal rendering)

**Description:**
The signals overlay displays signals from all three emitters (Gurgeh: `assumption_decayed`, `hypothesis_stale`, `spec_health_low`; Coldwine: `execution_drift`; Pollard: `competitor_shipped`, `research_invalidation`). Each signal carries `SpecID` and `Source` fields. However:

1. **No "Enter" key handler.** The overlay only handles `esc`/`q` (close), `up`/`down` (navigate), `tab` (category switch), `ctrl+r` (refresh). There is no way to act on a selected signal.
2. **No cross-tool navigation.** A `research_invalidation` signal with `Source: "pollard"` should navigate to the Pollard tab with the relevant insight. An `assumption_decayed` signal should navigate to the Gurgeh spec. Neither is possible.
3. **Signal detail is truncated.** The rendering at line 275 shows only severity icon, timestamp, source, and title -- all on one line. The `Detail` field (which contains actionable information like "confidence dropped to low") is not shown anywhere.

**Impact:** Signals are the cross-tool feedback mechanism documented in FLOWS.md section 12. Without drill-down actions, they function as notifications that the user must manually investigate by switching to the right tab and finding the right entity. This breaks the progressive disclosure principle: the system surfaces a problem but does not help the user navigate to it.

**Smallest viable fix:** Add an `enter` key handler that emits a navigation message based on `signal.Source` and `signal.SpecID`: Gurgeh signals navigate to the Gurgeh tab and select the spec; Pollard signals navigate to Pollard. Show `Detail` on the line below the selected signal (two-line rendering for selected item only).

---

## Finding 5: Hardcoded Hunter Set in PollardView "Run Research" Command

**Priority:** P3 (low)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go:500`

**Description:**
The "Run Research" palette command hardcodes three hunters:

```go
hunterNames := []string{"competitor-tracker", "hackernews-trendwatcher", "github-scout"}
```

The system has 12+ hunters (documented in FLOWS.md section 4: GitHub Scout, HackerNews, arXiv, OpenAlex, PubMed, USDA, Legal, Economics, Wiki, Agent Hunter, Context7, Competitor Tracker). The user has no way to select which hunters to run from the TUI. The arbiter's `DefaultResearchPlan` (referenced in FLOWS.md section 14) varies hunters per phase (e.g., arxiv-scout for Problem phase, competitor-tracker for Features/Goals), but the manual "Run Research" command always runs the same 3 tech-focused hunters.

**Impact:** Users working on non-tech domains (medical, legal, agricultural) get irrelevant results from the TUI's research command. They must use the CLI (`pollard scan --hunter pubmed`) for domain-specific research, which breaks the flow of staying in the TUI.

**Smallest viable fix:** Accept `hunterNames` as a parameter on the command (e.g., via a sub-palette or chat input). Alternatively, read the hunter list from `.pollard/config.yaml` if it exists, matching the CLI behavior.

---

## Finding 6: Bigend Does Not Surface Cross-Tool Signals in Its Dashboard

**Priority:** P3 (low)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/bigend.go:272-281` (View rendering)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/bigend.go:284-338` (renderDashboard)

**Description:**
FLOWS.md section 12 documents that signals flow to a "Bigend Signal Panel." The signal system exists and is wired to the signals overlay (accessible via `/signals` or ctrl+p). However, BigendView's `renderDashboard()` contains only two panes: "Ready Tasks" and "Sessions" (with dispatches). There is no signal panel, signal count, or signal indicator in the Bigend dashboard itself.

The documented flow shows Bigend as the aggregation layer that surfaces signals from all tools. In practice, signals are only visible via the overlay (which is a separate, floating panel) and not integrated into Bigend's permanent dashboard view. A user monitoring their project from Bigend would not see any signals unless they explicitly toggle the overlay.

**Impact:** The "mission control" role of Bigend is diminished. Users must remember to check the signals overlay periodically rather than seeing signal counts or severity badges in their default view.

**Smallest viable fix:** Add a signal summary line to `renderDashboard()` that shows active signal counts by severity (e.g., "Signals: 2 critical, 1 warning"). Make it clickable (enter key or palette action) to open the signals overlay.

---

## Finding 7: Coldwine-to-Pollard Research Link Is Missing

**Priority:** P3 (low)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go:823-908` (Commands)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go:489-543` (Commands)

**Description:**
FLOWS.md documents a bidirectional flow where Pollard insights link to specs/epics, and Coldwine's `execution_drift` signals trigger research. In practice:

1. ColdwineView has no "Research this epic" command. There is no way to trigger Pollard research from the Coldwine tab based on the selected epic's context.
2. PollardView has no awareness of epics or tasks. It only links to specs (via `LinkInsight`), not to epics or stories.
3. The `InsightLink` type in `pkg/contract/types.go` has a `FeatureRef` field, but the TUI's "Link Insight" command never sets it -- it only uses `InsightID` and `InitiativeID` (mapped to specID).

**Impact:** The Coldwine-to-Pollard direction of the composition pipeline is entirely missing from the TUI. Users who discover an execution drift (task taking 3x longer than expected) cannot trigger targeted research from within Coldwine. They must switch to Pollard manually and run research with no context carried over.

**Smallest viable fix:** Add a "Research Epic" command to ColdwineView's `Commands()` that constructs topic queries from the selected epic's title and description, then starts a research run via the coordinator (requires injecting `*research.Coordinator` into ColdwineView, similar to how PollardView already receives it).

---

## Finding 8: Sprint/Coldwine Tab Duplication Creates Confusion

**Priority:** P2 (medium)
**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:82` (tab list)
- `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go:256-270` (dashboard factory)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/run_dashboard.go:22-45` (RunDashboardView)
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go:19-44` (ColdwineView)

**Description:**
The tab bar contains 5 tabs: `["Bigend", "Gurgeh", "Coldwine", "Sprint", "Pollard"]`. Both Coldwine and Sprint deal with task orchestration and Intercore sprint state. The dashboard factory creates them as separate views at indices 2 and 3. Both views:

- Have an `iclient *intercore.Client` field
- Handle `DispatchCompletedMsg`
- Show sprint/run data
- Have chat handlers for sprint commands

ColdwineView shows epics/stories/tasks with sprint info as secondary data (line 585-587: "Sprint: {id} Phase: {phase}"). RunDashboardView shows runs/dispatches/budget/events/gates as primary data. A planning document exists at `docs/plans/2026-02-25-merge-sprint-into-coldwine.md` proposing to merge them.

**Impact:** Users must decide between two tabs for execution-related work. Sprint information is split: Coldwine shows task status but Sprint shows phase gates and budget. Moving between them requires manual tab switching and mental context recombination. The documented FLOWS.md diagram shows only 4 tools (Bigend, Gurgeh, Coldwine, Pollard) with no separate Sprint, suggesting the 5th tab is an implementation artifact.

**Smallest viable fix:** This is already recognized -- the merge plan exists. In the interim, add cross-links: when viewing an epic in Coldwine that has an active sprint, show a "View Sprint" shortcut that switches to the Sprint tab with that run selected. Conversely, when viewing a run in Sprint, show which epics/tasks it covers with a "View in Coldwine" shortcut.

---

## Composition Health Summary

| Flow | FLOWS.md Status | Implementation Status | Gap |
|------|----------------|----------------------|-----|
| Gurgeh -> Coldwine (SpecHandoffMsg) | Documented | Tab switch works; generation does not trigger | P1 |
| Coldwine -> Sprint (dispatch) | Implicit | Both handle DispatchCompletedMsg independently | P2 tab confusion |
| Pollard -> Gurgeh (InsightLink) | Documented | Backend link works; UI is fire-and-forget | P2 |
| Signals -> Any tool (drill-down) | Documented | Overlay is read-only | P2 |
| Coldwine -> Pollard (research) | Documented | Not implemented in TUI | P3 |
| Bigend signal aggregation | Documented | Overlay only; not in dashboard | P3 |
| Event Spine -> Intermute bridge | Documented as planned | Not implemented | Noted (not a UX gap yet) |

**Active view routing** is the structural root cause behind several findings: messages only reach `currentView` (except dispatches). This means any background operation's completion message is lost if the user switched tabs. The dispatch fan-out pattern at lines 305-320 is the correct model and should be extended to other cross-tool messages.
