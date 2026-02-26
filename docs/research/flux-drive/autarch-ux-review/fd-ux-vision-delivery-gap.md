# Autarch Vision-vs-Delivery Gap Audit

**Agent:** fd-ux-vision-delivery-gap (product manager, vision-against-reality audit)
**Date:** 2026-02-25
**Scope:** Autarch TUI codebase vs. autarch-vision.md, demarch-vision.md, FLOWS.md, AGENTS.md
**Decision Lens:** Cost per landable change (autonomy, quality, token efficiency). Gaps immediately visible to a user who read the vision first.

---

## Executive Summary

Autarch has strong foundational infrastructure: a well-designed DataSource abstraction with fallback, a 5-tab unified TUI shell, Intercore integration for sprint operations, and a functional status tool. However, the gap between the vision documents and the shipped product is significant in three areas that directly affect the north-star metric:

1. **Bigend is not multi-project mission control in the unified TUI** -- the flagship tab delivers single-project task/session lists, not the cross-project observatory described in the vision.
2. **The intent submission mechanism does not exist** -- Coldwine calls `ic.RunCreate` directly (kernel primitives), bypassing the OS layer, making the "apps are swappable" claim false for write operations.
3. **The Autarch Status Tool described in the vision (lines 191-249) exists as a standalone CLI** but is not the "primary wedge" the vision recommends shipping first -- it lacks the event stream and discovery inbox features.

These gaps matter because they affect autonomy (users cannot observe multi-project sprint progress from one place) and efficiency (no OS-mediated policy enforcement on writes, so the architecture cannot enforce routing/budgeting from a single control plane).

---

## Gap Catalog

### GAP-01: Bigend is Single-Project in Unified TUI (P0 -- Vision Credibility)

**Vision promise (autarch-vision.md:103):**
> "Bigend -- Multi-project mission control. A read-only aggregator that monitors agent activity, displays run progress, and provides a dashboard view across projects."

**Vision promise (autarch-vision.md:131-137):**
> "Bigend is a pure observer. Today it discovers projects via filesystem scanning and monitors agents by scraping tmux panes. Migration swaps these data sources: Project discovery -> `ic run list` across project databases."

**Reality:**
- `internal/tui/views/bigend.go` receives a single `*autarch.Client` (line 61-75), which is bound to one Intermute URL and one project context.
- The view shows two panes: "Ready Tasks" (from a single project's task proposals) and "Sessions" (from a single Intermute server) plus Intercore dispatches.
- No multi-project discovery, no cross-project aggregation, no project list sidebar.
- The standalone `bigend --tui` mode (`internal/bigend/tui/`) DOES use the aggregator + scanner for multi-project, but the unified TUI (`autarch tui`) does not.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/bigend.go:61-75` -- constructor takes single client
- `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go:257-258` -- factory wires single client
- `/home/mk/projects/Demarch/apps/autarch/internal/bigend/aggregator/aggregator.go:77-80` -- State struct with multi-project support exists but is NOT used by BigendView

**Impact:** A user reading the vision expects Bigend to answer "what's running across all my projects?" The unified TUI's Bigend answers "what tasks are ready in this one project?" This is the most immediately visible gap because Bigend is the default landing tab.

**Priority:** P0 -- directly undermines the "mission control" claim and the demarch-vision north-star metric ("what does it cost to ship a reviewed, tested change?" requires multi-project visibility).

---

### GAP-02: Intent Submission Mechanism Does Not Exist (P0 -- Architecture)

**Vision promise (autarch-vision.md:74-87):**
> "Autarch apps are read-only consumers of kernel state. They submit intents to the OS (Clavain) for any action that implies policy... the v1 mechanism is direct CLI invocation [of Clavain operations]."
> Minimal Intent Contract: `start-run`, `advance-run`, `override-gate`, `submit-artifact`.

**Reality:**
- Coldwine calls `ic.RunCreate` directly via the Intercore client (`internal/tui/views/coldwine.go:891`).
- RunDashboardView calls `ic` operations directly (advance, cancel, dispatch) via `pkg/intercore/operations.go`.
- No call goes through Clavain CLI or any OS-layer policy enforcement.
- The vision explicitly says "Only policy-governing mutations go through the OS" -- all mutations currently bypass the OS.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go:891` -- `ic.RunCreate(ctx, ".", goal, ...)` direct kernel call
- `/home/mk/projects/Demarch/apps/autarch/pkg/intercore/operations.go` -- all operations call `ic` directly
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/run_dashboard.go:584` -- help text references `ic run create`

**Impact:** Without OS-mediated intent submission, the kernel has no policy enforcement on writes from the app layer. Model routing, budget limits, complexity-aware dispatch -- none of these can be enforced at the OS layer when apps call the kernel directly. This makes the "apps are swappable" claim false -- a replacement app would need to reimplement the same direct kernel calls, not just render state and submit intents.

**Priority:** P0 -- this is the architectural seam that makes the three-layer separation real. Without it, Layer 2 (Clavain) is bypassed for all write operations from Layer 3 (Autarch). The vision acknowledges this gap explicitly ("intent submission mechanism does not exist yet" at line 51).

---

### GAP-03: Autarch Status Tool -- Incomplete vs. Vision Wireframe (P1)

**Vision promise (autarch-vision.md:191-249):**
> Describes a minimal TUI with: Run list with phase progress bars, Event stream tail (live-updating), Dispatch status dashboard, Discovery inbox for confidence-tiered review. "This minimal TUI is the first app that should ship."

**Reality:**
- `autarch status` exists (`cmd/autarch/status.go`) and launches a standalone TUI (`internal/status/model.go`).
- It has three panes: RunsPane, DispatchPane, EventsPane with 3-second polling.
- Missing: Phase progress bars (just shows phase name), Discovery inbox, confidence-tiered review.
- Not accessible as a tab in the unified TUI -- it's a separate `autarch status` command.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/status.go:15-57` -- standalone command
- `/home/mk/projects/Demarch/apps/autarch/internal/status/model.go:20-34` -- three panes, no progress bars or discovery inbox

**Impact:** The vision positions this as "the primary wedge" that validates the full stack. It exists as a basic implementation but lacks the visual polish (progress bars) and the discovery inbox feature entirely. A user who read the vision would find the status tool functional but notably incomplete.

**Priority:** P1 -- the tool works for "what's running right now?" but misses the discovery inbox that closes the loop with Pollard.

---

### GAP-04: The 5th Tab (Sprint/RunDashboard) is Undocumented in Vision (P2)

**Vision promise (autarch-vision.md:101-109):**
> Describes four tools: Bigend, Gurgeh, Coldwine, Pollard. No mention of a Sprint tab.

**Reality:**
- The unified TUI has 5 tabs: Bigend, Gurgeh, Coldwine, Sprint, Pollard (`unified_app.go:82`).
- The Sprint tab (`RunDashboardView` in `run_dashboard.go`) shows Intercore run status with phase advancement, dispatches, budget, events, and gates.
- CLAUDE.md describes it: "Sprint: Intercore sprint run dashboard -- phase advancement, budget, gates, dispatches" (line 11).

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:82` -- tab names include "Sprint"
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/run_dashboard.go:22-45` -- RunDashboardView struct
- `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go:261` -- Sprint wired as 4th view (index 3)

**Impact:** The Sprint tab overlaps significantly with what the status tool should be (runs, dispatches, events). The vision says four tools; the product ships five. This is not necessarily wrong -- the Sprint tab may be the unified-TUI evolution of the status tool concept -- but the vision document should be updated. A user reading the vision would not expect this tab and wouldn't know its relationship to the status tool.

**Priority:** P2 -- documentation drift, not a product defect. The Sprint tab delivers real value.

---

### GAP-05: Gurgeh Arbiter Logic Still in App Layer (P1 -- Acknowledged Debt)

**Vision promise (autarch-vision.md:47-55):**
> "Current reality: Gurgeh's arbiter contains agency logic (LLM conversation sequencing, confidence evaluation, phase advancement). A replacement app would need to reimplement this, violating 'apps are swappable.' This logic is scheduled for extraction to Clavain."

**Reality:**
- The Orchestrator (`internal/gurgeh/arbiter/orchestrator.go`) drives the 8-phase spec sprint including LLM calls, confidence scoring, and phase advancement.
- SprintView (`internal/tui/views/sprint_view.go:18-43`) owns the Orchestrator directly (line 19: `orch *arbiter.Orchestrator`).
- No extraction to Clavain has occurred. The extraction schedule (autarch-vision.md:89-99, Phases 1-3) targets v1.5-v2.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/sprint_view.go:19` -- SprintView owns Orchestrator
- `/home/mk/projects/Demarch/apps/autarch/internal/gurgeh/arbiter/` -- full arbiter engine in app layer

**Impact:** The vision explicitly acknowledges this as debt (line 155: "This is an acknowledged architectural debt, not an intentional design choice"). The extraction schedule is clear but not started. Until extraction, Gurgeh is not swappable. This affects the platform play: external developers building on Demarch cannot write a web-based PRD tool without reimplementing the arbiter.

**Priority:** P1 -- acknowledged debt with a clear extraction schedule (v1.5-v2). Not blocking current usage but blocking the platform vision.

---

### GAP-06: Intermute Startup Failure is Silent (P1 -- User Experience)

**Vision promise (FLOWS.md:55):**
> "Local-only default: Autarch runs fully local. Intermute and Signals are optional local services."

**Reality:**
- When Intermute fails to start, `IntermuteStartFailedMsg` is handled by logging an error to slog (`unified_app.go:555-557`): `slog.Error("intermute startup failed", "error", msg.Error)`.
- This log is only visible if the log pane is open (Ctrl+L). The user sees no visible indication of failure.
- The fallback mechanism (`client.go:86-95`) activates on ECONNREFUSED and shows an `[offline -- reading local files]` badge in the footer -- but only after the first failed API call, not proactively on startup failure.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:555-557` -- silent slog.Error
- `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/client.go:86-95` -- tryFallback activates lazily

**Impact:** A user launching `autarch tui` may not realize Intermute failed to start until they try to create a spec and get ErrFallbackReadOnly. The fallback badge appears after the first failed read, not at startup. The gap between "optional local services" (vision) and "writes unavailable with no upfront notice" (reality) is a first-run friction point.

**Priority:** P1 -- affects first-time user experience. Fix: surface Intermute failure as a visible banner/toast immediately, not just in the log pane.

---

### GAP-07: WebSocket Real-Time Updates Not Connected (P2)

**Vision promise (autarch-vision.md:202-215):**
> "Signal broker -- In-process pub/sub fan-out with typed subscriptions... WebSocket streaming to TUI and web consumers."
> "Status: This architecture exists in Autarch's current codebase... It has not yet been connected to Intercore's event bus."

**Reality:**
- The signal broker exists (`pkg/signals/broker.go`), wired in main.go (line 249-253).
- The EventWatcher polls Intercore events and publishes them through the broker (`internal/tui/event_watcher.go`).
- WebSocket client exists (`pkg/autarch/websocket.go`) but is not used by the unified TUI views.
- BigendView, ColdwineView, PollardView all use polling (loadSessions, loadEpics, loadInsights) -- no push-based updates.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go:249-253` -- broker wired
- `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/websocket.go` -- client exists
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/bigend.go:137-163` -- polling-based data loading

**Impact:** The vision correctly caveats this as "rendering optimization" and says "if the signal broker is removed entirely, the system works identically -- TUI updates are slightly slower." The polling approach works. However, the event-driven reactivity described in FLOWS.md sections 5 and 11 is not delivered to TUI views.

**Priority:** P2 -- the vision honestly labels this as transitional. Polling works. The gap is acknowledged.

---

### GAP-08: Coldwine Task Orchestration Overlap with Clavain Sprint (P2)

**Vision promise (autarch-vision.md:50-51):**
> "Coldwine's task orchestration overlaps with Clavain's sprint skill. Both drive agent dispatch. The resolution is that Coldwine submits intents to the OS -- but this intent submission mechanism does not exist yet."

**Reality:**
- ColdwineView has its own task hierarchy (epics/stories/tasks from Intermute) AND Intercore sprint operations (`sprintCreatedMsg`, `taskDispatchedMsg`).
- The Sprint tab (`RunDashboardView`) also shows Intercore runs with advance/cancel operations.
- Both tabs can create runs via `ic.RunCreate` -- overlapping write paths to the same kernel.
- The "resolution" (intent submission) does not exist, so the overlap persists.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/coldwine.go:886-894` -- RunCreate in Coldwine
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/run_dashboard.go` -- RunCreate in Sprint tab

**Impact:** Users have two places to manage sprints (Coldwine tab and Sprint tab) with no clear guidance on which to use. This is a navigation/IA issue that creates confusion about where to look for sprint progress.

**Priority:** P2 -- acknowledged in the vision. The Sprint tab partially addresses this by being the kernel-native view while Coldwine retains the task-hierarchy view. The overlap will resolve when intent submission lands.

---

### GAP-09: Pollard RunTargetedScan Not Integrated in Unified TUI (P2)

**Vision promise (FLOWS.md:686-695):**
> "The Arbiter sprint now triggers Pollard research at each phase transition... Config: `internal/gurgeh/arbiter/research_phases.go`"

**Reality:**
- PollardView's "Run Research" command palette action (`pollard.go:491-513`) invokes `v.coordinator.StartRun` with hardcoded hunter names (`competitor-tracker`, `hackernews-trendwatcher`, `github-scout`).
- The per-phase targeted scan (`internal/pollard/api/targeted.go`) exists but is not wired into the unified TUI's Pollard tab.
- The arbiter's research bridge (`arbiter.NewResearchBridge`) exists and is wired in SprintView (`sprint_view.go:66-70`), but only for the spec sprint flow -- not for standalone Pollard research.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/pollard.go:491-513` -- hardcoded hunter list
- `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/sprint_view.go:66-70` -- research bridge wired for sprint

**Impact:** The Pollard tab is a passive insight viewer. Users cannot trigger targeted scans matching the research plan from the vision. The research integration works within the spec sprint flow (good) but not as a standalone Pollard capability.

**Priority:** P2 -- the research integration works where it matters most (during spec generation). The standalone Pollard tab is less critical.

---

### GAP-10: DataSource Swappability Claim is Partially Delivered (P2 -- Credit)

**Vision promise (autarch-vision.md:57-59):**
> "Autarch is one realization of the application layer... Swappable."

**Reality (positive):**
- `pkg/autarch/source.go` defines a clean `DataSource` interface with `WritableDataSource` extension.
- `Client` implements transparent fallback (`client.go:86-95`): on ECONNREFUSED, switches to `LocalSource`.
- `internal/autarch/local/` implements `LocalSource` reading from `.gurgeh/`, `.coldwine/`, `.pollard/` files.
- Footer badge shows `[offline -- reading local files]` when in fallback mode.

**Files:**
- `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/source.go:5-20` -- DataSource + WritableDataSource
- `/home/mk/projects/Demarch/apps/autarch/pkg/autarch/client.go:46-95` -- fallback mechanism

**Impact:** This is well-executed. The data source abstraction genuinely supports swapping backends. The gap is that swappability refers to the app layer (Autarch itself being replaceable), which requires intent submission (GAP-02) -- but the data source pattern is good infrastructure.

**Priority:** P2 credit -- good delivery on this sub-claim. The DataSource pattern is production-quality.

---

## Priority Summary

| Priority | Gap | North-Star Impact | Fix Complexity |
|----------|-----|-------------------|----------------|
| **P0** | GAP-01: Bigend single-project in unified TUI | High (visibility) | Medium (wire aggregator into BigendView) |
| **P0** | GAP-02: No intent submission mechanism | High (architecture) | High (requires Clavain intent API) |
| **P1** | GAP-03: Status tool incomplete vs. wireframe | Medium (first impression) | Low (add progress bars, discovery inbox) |
| **P1** | GAP-05: Gurgeh arbiter in app layer | Medium (platform play) | High (extraction to Clavain, v1.5-v2) |
| **P1** | GAP-06: Intermute failure is silent | Medium (first-run UX) | Low (surface banner on startup failure) |
| **P2** | GAP-04: Sprint tab undocumented in vision | Low (doc drift) | Trivial (update vision doc) |
| **P2** | GAP-07: WebSocket not connected to views | Low (acknowledged) | Medium (wire broker to views) |
| **P2** | GAP-08: Coldwine/Sprint overlap | Low (acknowledged) | High (needs intent submission) |
| **P2** | GAP-09: Pollard targeted scan not in TUI | Low (works in sprint flow) | Medium |
| **P2** | GAP-10: DataSource swappability (credit) | Positive | -- |

## Recommendations for North-Star Impact

**Immediate (cost: low, impact: high):**
1. Wire the aggregator into BigendView in the unified TUI. The code exists (`internal/bigend/aggregator`); it just needs to be passed through the dashboard factory instead of the raw client.
2. Surface Intermute startup failure as a visible banner, not just slog.

**Next sprint (cost: medium, impact: high):**
3. Add the Autarch Status Tool wireframe features (progress bars, discovery inbox) to the Sprint tab, consolidating the two concepts.
4. Update the vision document to reflect the 5-tab reality and the Sprint tab's role.

**Track-level (cost: high, impact: architectural):**
5. Implement the v1 intent submission mechanism (Clavain CLI calls from apps for policy-governing mutations). This is the architectural prerequisite for the platform play.
6. Extract Gurgeh arbiter to Clavain (v1.5-v2 schedule per vision doc).

---

*This audit is read-only research. No code or files were modified.*
