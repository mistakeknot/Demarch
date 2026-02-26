# Autarch UX Review — Synthesis

**Date:** 2026-02-25
**Agents dispatched:** 6 (5 custom UX + 1 core user-product)
**Target:** /home/mk/projects/Demarch/apps/autarch/
**Verdict:** CONDITIONAL PASS — strong foundations, but 4 P0 issues and 8 P1 issues prevent the TUI from delivering the Autarch and Demarch visions

---

## Verdict

Autarch has solid engineering foundations: a well-designed DataSource abstraction with transparent fallback, a functional Intercore Go client covering 28 kernel methods, a reusable RunDetailPanel component, correct Bubble Tea patterns in the DispatchWatcher, and a consistent Tokyo Night theme. The Sprint tab (RunDashboardView) is close to the vision's "Autarch status tool" mockup.

However, the UX fails to deliver the vision in four structural ways:

1. **The golden path has silent dead ends.** A user without a coding agent hits a permanent dead end after investing effort in the spec sprint. AgentNotFoundMsg is silently dropped (P0, confirmed by 3 agents independently).

2. **The four tools don't compose into a product.** Cross-tool handoffs require manual bridging; messages only route to the active view; the Gurgeh-to-Coldwine handoff navigates but doesn't trigger generation; signals are read-only with no drill-down.

3. **54% of kernel capabilities are invisible.** 15 of 28 Intercore client methods are never called from the TUI. Gate override, artifact list, dispatch kill, agent registry, and the streaming event API exist in the client but have no TUI surface.

4. **The north star metric has zero visibility.** "Cost per landable change" — the metric the entire platform is designed to minimize — appears nowhere in any view. No token counts, no model cost attribution, no efficiency signals.

---

## P0 Findings (4 — Blocking User Success)

| # | Finding | Agents | File | Fix Complexity |
|---|---------|--------|------|----------------|
| 1 | **AgentNotFoundMsg silently dropped** — user hits dead end after completing spec sprint with no error, no instructions, no recovery path | onboarding, user-product, vision-gap | `gurgeh_onboarding.go:186-187` | Low (5 lines) |
| 2 | **Bigend is single-project in unified TUI** — the vision's "multi-project mission control" delivers single-project tasks+sessions; the aggregator code exists but isn't wired to BigendView | vision-gap, kernel-gap | `bigend.go:61-75`, `main.go:257-258` | Medium (wire aggregator) |
| 3 | **Intent submission mechanism does not exist** — Coldwine calls `ic.RunCreate` directly, bypassing OS policy layer; makes "apps are swappable" false for writes | agency-leak, vision-gap | `coldwine.go:891`, vision:74-87 | High (Clavain intent API) |
| 4 | **Orphaned onboarding states (ScanVision/Problem/Users)** — defined in enum, given ID/Label entries, but excluded from AllOnboardingStates(); latent code path could desync breadcrumb from state | onboarding | `onboarding.go:8-10` vs `:19-27` | Low (remove or implement) |

## P1 Findings (8 — Undermining Product Value)

| # | Finding | Agents | File | Fix Complexity |
|---|---------|--------|------|----------------|
| 5 | **SpecHandoffMsg navigates but doesn't generate** — "Generate Epics" switches to Coldwine with a hint message but does not trigger actual epic generation | composition, user-product | `gurgeh.go:435`, `coldwine.go:90-101` | Low (add autoGenerate cmd) |
| 6 | **Two of four vision write-path intents missing** — `GateOverride()` and `ArtifactAdd()` exist in client but no TUI view invokes them; users must drop to CLI | kernel-gap | `operations.go:134-137`, `:152-159` | Medium (add keybindings) |
| 7 | **Bigend shows dispatches but not runs** — the fundamental kernel concept is invisible on the primary monitoring surface | kernel-gap | `bigend.go:447-483` | Medium (add RunList call) |
| 8 | **Kernel unavailability is silent on Bigend/Coldwine** — sections silently disappear when iclient is nil; only Sprint tab communicates degraded state | kernel-gap, vision-gap | `bigend.go:148-150`, `coldwine.go:188-189` | Low (add badge/indicator) |
| 9 | **No onboarding completion persistence** — every session restarts from Kickoff regardless of existing specs; skipOnboarding flag is dead code | onboarding | `gurgeh.go:48-69`, `main.go:146-148` | Low (check existing specs) |
| 10 | **navigateBack() missing Interview/SpecSummary cases** — pressing Back during the spec sprint is a no-op; user is trapped until completion | onboarding | `gurgeh_onboarding.go:687-704` | Low (add case arms) |
| 11 | **North star metric invisible** — cost per landable change appears nowhere; no token counts, no cost breakdown, no Interspect signals in any view | user-product | All views | Medium (add footer badge) |
| 12 | **Generation cancelled on tab switch** — switching away from Gurgeh during epic generation calls cancelStreaming()/cancelContext(); no recovery path | user-product | `sprint_view.go` blur handler | Medium (survive tab switch) |

## P2 Findings (12 — Quality/Adoption Risk)

| # | Finding | Agents |
|---|---------|--------|
| 13 | Messages route only to active view (except dispatches) — background operations lost on tab switch | composition |
| 14 | Pollard "Link Insight" is fire-and-forget — no cross-tool navigation, Gurgeh never displays linked insights | composition |
| 15 | Signals overlay is read-only — no drill-down, no cross-tool navigation from signal to source | composition |
| 16 | Sprint/Coldwine tab duplication — two places to manage sprints with no cross-links | composition |
| 17 | Event stream uses 10s polling with time.Sleep, not the streaming EventsTail API | kernel-gap |
| 18 | Agent registry, artifact list, dispatch kill not surfaced anywhere in TUI | kernel-gap |
| 19 | Dual quality scoring systems (arbiter confidence vs review package) — extraction plan doesn't address unification | agency-leak |
| 20 | Dispatch watcher polling protocol is app-layer logic any client must duplicate (~50 LOC) | agency-leak |
| 21 | Task decomposition rules (foundational epic detection, auto test tasks) embedded in app | agency-leak |
| 22 | PhaseSidebar hidden by default during sprint — most useful progress signal behind ctrl+b | user-product |
| 23 | No second-spec path — "New Spec" creates blank draft, not sprint wizard | user-product |
| 24 | Intermute startup failure is silent — only visible in hidden log pane | vision-gap |

## P3 Findings (8 — Polish)

| # | Finding | Agents |
|---|---------|--------|
| 25 | Hardcoded hunter set in Pollard "Run Research" (3 tech hunters only) | composition, agency-leak |
| 26 | Coldwine-to-Pollard research link missing | composition |
| 27 | Bigend lacks inline signal panel in dashboard | composition |
| 28 | sendToCurrentView silently discards tea.Cmd (documented BUG) | onboarding |
| 29 | Double Ctrl+C quit doesn't warn about in-progress onboarding | onboarding |
| 30 | Footer help text dashboard-oriented during onboarding | onboarding, user-product |
| 31 | Breadcrumb "Dashboard" label is misleading (actual end state is spec browser) | onboarding |
| 32 | Gate rules, dispatch tokens, epic-run mapping fragility | kernel-gap |

---

## Structural Root Causes

Three structural patterns explain most findings:

### 1. Active-View-Only Message Routing
`unified_app.go:560-564` sends non-key messages only to `currentView`. Only `dispatchBatchMsg` fans out to all views. This means research progress, sync completion, and other background operation results are silently dropped when the user switches tabs. The dispatch fan-out pattern (lines 305-320) is the correct model that should be extended.

### 2. Agency Logic in the Wrong Layer (~3,380 lines)
The Gurgeh arbiter (~2,500 LOC), Coldwine's dispatch-to-task state machine (~100 LOC), direct kernel calls (~60 LOC), task decomposition rules (~150 LOC), and miscellaneous policy (~570 LOC) all live in the app layer. A second UI client must duplicate all of this. The vision's 3-phase extraction schedule addresses the largest items but misses the dual scoring systems, dispatch watcher protocol, and Pollard hunter policy.

### 3. Missing Orchestration Layer Between Tools
Each tool operates as an independent dashboard. The only cross-tool message is `SpecHandoffMsg` (Gurgeh→Coldwine), and even that doesn't trigger downstream action. There is no mechanism for: Pollard findings proactively surfacing in Gurgeh, Coldwine execution drift triggering Pollard research, or Bigend aggregating signals from all tools into its dashboard. The signals overlay exists but is read-only with no drill-down navigation.

---

## Highest-Impact Fix Sequence

**Tier 1 — Fix now (low effort, high impact):**
1. Display `AgentNotFoundMsg.Instructions` in chat panel (~5 LOC)
2. Add `[ic offline]` footer badge when `iclient == nil` (~10 LOC)
3. Surface Intermute startup failure as visible banner (~10 LOC)
4. Open PhaseSidebar by default in SprintView.Init() (~1 LOC)
5. Add navigateBack() cases for Interview/SpecSummary (~5 LOC)
6. Remove orphaned ScanVision/ScanProblem/ScanUsers states (~18 LOC)

**Tier 2 — Next sprint (medium effort, high impact):**
7. Wire the existing aggregator into BigendView for multi-project
8. Add `autoGenerate` flag to SpecHandoffMsg so Gurgeh→Coldwine triggers epic generation
9. Add `RunList()` call to Bigend so runs are visible on the dashboard
10. Add gate-override keybinding (`o`) and palette command to Sprint tab
11. Add token count to Sprint tab footer from `ic run show`
12. Skip onboarding when specs already exist (check ListSpecs at startup)
13. Add "Start New Project" action to Bigend empty state

**Tier 3 — Track-level (high effort, architectural):**
14. Extend dispatch fan-out pattern to research/signal messages (all-view routing)
15. Implement v1 intent submission mechanism (Clavain CLI from apps)
16. Begin Gurgeh arbiter extraction to Clavain (Phase 1: confidence scoring)
17. Make generation commands survive tab switches (long-lived background cmds)
18. Switch EventWatcher from polling to EventsTail streaming API
19. Add signal drill-down navigation (enter on signal → navigate to source tool)

---

## Cross-Agent Convergence

Several findings were independently identified by multiple agents, increasing confidence:

| Finding | Confirmed by |
|---------|-------------|
| AgentNotFoundMsg silently dropped | onboarding, user-product, vision-gap |
| Bigend is single-project | vision-gap, kernel-gap, user-product |
| Intent submission bypass | agency-leak, vision-gap |
| Kernel unavailability silent | kernel-gap, vision-gap |
| North star metric invisible | user-product, vision-gap |
| SpecHandoffMsg doesn't trigger generation | composition, user-product |
| Hardcoded Pollard hunter set | composition, agency-leak |

---

## Positive Observations

1. **DataSource abstraction** — `pkg/autarch/source.go` with transparent HTTPSource/LocalSource fallback is production-quality infrastructure
2. **RunDashboardView** — close to the vision's status tool with phase timelines, budget bars, gate evidence
3. **RunDetailPanel** — extracted component with CompactRender() enables cross-view kernel observability
4. **DispatchWatcher** — correct Bubble Tea patterns (tea.Tick, all-view broadcast, dedup)
5. **Signal emitters** — per-tool signal types with cross-tool aggregation overlay
6. **SprintCommandRouter** — CLI parity via slash commands in the chat panel
7. **Tokyo Night theming** — consistent, professional appearance across all views

---

*Individual agent reports: `fd-ux-onboarding-friction.md`, `fd-ux-cross-tool-composition.md`, `fd-ux-kernel-surface-gap.md`, `fd-ux-agency-layer-leak.md`, `fd-ux-vision-delivery-gap.md`, `fd-user-product.md`*
