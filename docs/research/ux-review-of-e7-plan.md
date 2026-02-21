# UX / Product Review: Bigend Kernel Migration (E7) Implementation Plan

**Reviewer:** Flux-drive User & Product Reviewer
**Date:** 2026-02-20
**Plan file:** `hub/autarch/docs/plans/2026-02-20-bigend-kernel-migration-plan.md`
**PRD file:** `docs/prds/2026-02-20-bigend-kernel-migration.md`
**Code reviewed:** `hub/autarch/internal/bigend/tui/model.go`, `hub/autarch/internal/bigend/tui/pane.go`, `hub/autarch/pkg/tui/keys.go`, `hub/autarch/pkg/tui/components.go`, `hub/autarch/pkg/tui/help.go`

---

## Primary User and Job-to-Be-Done

**Primary user:** A single operator running multiple AI agent workstreams concurrently.
**Job:** "Which of my agents is blocked right now?" — answered in under 30 seconds without leaving Bigend.
**Secondary job:** Drill into a specific blocked agent to understand why it is blocked and what it needs.

This review evaluates whether the plan's UX choices serve that job. The 30-second clock starts from the moment the operator opens the dashboard, not from a context switch into a different tool.

---

## Finding 1 — F4.1 Metrics Bar: Five Data Points on One Line

**Severity: P2**

The plan specifies the following single-line stats bar:

```
4 projects · 3 active runs · 1 blocked · 5 dispatches · 12,450 in / 3,200 out tokens
```

That is seven distinct numeric values (projects, active runs, blocked, dispatches, tokens-in, tokens-out) packed onto one line with dot separators. Observed behavior in the existing `renderDashboard()` code (model.go:1429-1494) already shows that the current card-style layout (four stat panels side by side) is easier to scan at a glance than a prose-like run-on string, because each panel isolates one number with its label.

**Specific concerns:**

1. The "blocked" count is the most urgent signal in the entire bar. On this line it is the third item, positioned after two lower-urgency numbers. A user scanning quickly will likely read left to right and stop at "active runs" — not reaching "blocked" without deliberate effort.

2. "12,450 in / 3,200 out tokens" mixes two values into a slash-separated substring. This format is unusual enough in TUI dashboards that operators may read the slash as a ratio or division rather than two separate counts.

3. The plan also specifies a cross-project Active Runs section immediately below (F4.2). If blocked count is visible in both the metrics bar and as `▲` icons in the run list, the bar entry provides no additional navigation affordance — it is a count without a click target. In a TUI, a pure informational count only earns its space if it dramatically reduces time-to-comprehension.

**Recommendation:** Invert priority. The blocked count should either be first or appear alone in a highlighted box. Consider keeping the existing card-style panels (already implemented in `renderDashboard()`) and adding "Blocked" as a dedicated fifth card, styled in warning color when non-zero. This preserves scannability and matches the operator's mental model (one number = one concept). The token totals, while useful for budget awareness, are low-urgency and can be deferred to a detail view or a collapsible footer rather than cluttering the primary metrics bar.

**Alternative to full redesign:** If the single-line format is non-negotiable, reorder to: `1 blocked · 3 active runs · 5 dispatches · 4 projects · 12,450 in / 3,200 out tokens`. Blocked first. The existing `renderDashboard()` code at model.go:1466-1470 already conditionally styles blocked count in error color, which is the right instinct — the position just needs to match the visual priority.

---

## Finding 2 — F6 Focus Ring: Discoverability and Keystroke Cost

**Severity: P2**

The plan proposes Tab/h/l to cycle focus through three panes: sidebar, run list, detail pane. Two issues:

**2a. The `h`/`l` bindings conflict with Vim motion expectations in the wrong direction.**

The existing codebase uses `[` and `]` for FocusLeft and FocusRight (model.go:515-528). The plan introduces `h` and `l` as aliases for Tab cycling. In Vim convention, `h` and `l` move the cursor left/right within a list, not between panes. If any embedded list component (the run list itself) passes `h`/`l` through to its own handler, the result is undefined behavior at the boundary between pane navigation and item navigation.

Looking at model.go:1033-1044, the current code delegates unhandled keys to the active list. If `h`/`l` are consumed by the pane focus handler before reaching the list, list items that use `h`/`l` for their own navigation break. If the priority is reversed, pane focus never activates. The plan does not specify the resolution.

**2b. Two keystrokes to reach the detail pane is acceptable; discoverability of the focus ring is not.**

The current footer (model.go:1269-1297) lists only the first-level keys. Tab is shown as "switch" which already refers to tab switching. Adding a second semantic meaning of Tab (pane cycling within the detail view) creates a mode ambiguity: does Tab switch tabs (Dashboard/Sessions/Agents) or cycle panes (sidebar/run list/detail)? The plan says Tab cycles panes, but the existing Tab binding cycles the top-level tabs. These are the same key doing different things depending on which pane has focus, and there is no visible indicator of current mode.

**Recommendation:**
- Keep the existing `[`/`]` for pane focus left/right — they are already defined, already documented, and have no semantic conflict with list navigation.
- Drop `h`/`l` as Tab aliases to avoid Vim-convention confusion and list-key ambiguity.
- The footer hint for focus must be updated to reflect both `tab` (top tabs) and `[`/`]` (pane focus) as distinct concepts. Without this, users will not discover pane cycling without reading documentation.

---

## Finding 3 — F6.4 Narrow Fallback: Esc Semantic Conflict

**Severity: P1**

The plan specifies: below 100 columns, Enter opens full-screen detail overlay, Esc returns to run list.

This is a direct conflict with the established Esc semantic in CommonKeys (keys.go:43-46): `Esc` = "back" (navigating up a level in the hierarchy). The existing key handler at model.go:707-737 uses `KeyEsc` to cancel prompt mode. The help overlay handler at model.go:739-743 uses `Esc` to dismiss the overlay. A third Esc semantic — dismissing the narrow-mode detail overlay — creates a three-way contextual meaning for the same key.

**Observed behavior in comparable TUIs:** Esc as "cancel / close / go back" works when there is only one active modal layer. When the user has a narrow terminal and an overlay open, pressing Esc expecting to quit the tool (or navigate back) instead closes the overlay. This is surprising and disorienting because nothing on screen indicates that Esc has been "claimed" by the overlay rather than behaving globally.

**The more fundamental question:** In an 80-column terminal (the 80x24 minimum), pressing Esc to "return to list" is reasonable. But what does Ctrl+C do in this state? The plan does not specify. If Ctrl+C quits the tool while the overlay is open, that is correct. If the overlay intercepts all keypresses including Ctrl+C, the user has no escape hatch from a broken state.

**Recommendation:**
- Use `q` or `Esc` for the overlay dismiss with an explicit on-screen hint inside the overlay: `[esc] close`. This makes the scope of Esc visible rather than relying on operator inference.
- Specify that Ctrl+C always propagates to the quit handler regardless of overlay state. This should be enforced in the key handler priority chain.
- Consider whether the narrow-mode overlay is necessary at all. An alternative: in narrow mode, the run list and detail view are simply stacked vertically (list above, detail below), eliminating the Enter/Esc indirection entirely. This is simpler to implement, requires no new modal state, and matches operator expectations better.

---

## Finding 4 — Source Prefix Tags [K]/[M]/[T]: Operator Legibility

**Severity: P2**

The plan specifies source prefixes `[K]` kernel (blue), `[M]` intermute (green), `[T]` tmux (gray), always shown. Looking at the current implementation in model.go:1583-1590, the prefix rendering is already coded but the labels are opaque to a new operator.

**The problem is not color — it is label meaning.** An operator seeing `[K]` for the first time must already know that "K" means kernel (ic CLI), not Kubernetes, not key-value store, not any other K-acronym common in developer tooling. `[M]` similarly: Intermute is the internal coordination service, but "M" maps to nothing in the visible product vocabulary. The header says "Vauxhall" (model.go:1231). The registered names are Bigend, Gurgeh, Coldwine, Pollard. "M" for Intermute requires reading the CLAUDE.md to understand.

**The tags are always shown** (per spec), so there is no progressive disclosure here. Every event line has a colored `[K]`, `[M]`, or `[T]` that the operator must decode on first use.

**Recommendation:**
- Use expanded labels on first render or when the activity feed is sparse: `[kernel]`, `[intermute]`, `[tmux]`. Abbreviate to `[K]`, `[M]`, `[T]` when lines are truncated due to width constraints.
- Alternatively, place a one-line legend above the activity feed: `[K] kernel  [M] intermute  [T] tmux`. This costs one line of vertical space and eliminates all decoding overhead.
- At minimum, the help overlay (help.go) should include a "Source tags" section explaining the abbreviations. Currently the help overlay only documents key bindings, not data vocabulary.

---

## Finding 5 — F1.1 Sidebar Badge: `[2 runs]` vs Blocked Count

**Severity: P2**

The plan specifies: sidebar project item shows `[2 runs]` badge. Looking at the current implementation in model.go:337-346 (`ProjectItem.Title()`), the badge currently shows run count (`[%d]`) without the "runs" label — but the plan's prose says "2 runs".

**The actionability problem:** Run count is a quantity. The operator's question is not "how many runs does this project have?" — it is "do any of those runs need my attention?" A badge showing `[2 runs]` when both runs are progressing normally provides no triage signal. A badge showing `[1 blocked]` immediately answers the question and motivates navigation.

**Looking at what the code already knows:** `state.Kernel.Runs[project.Path]` is already iterated and the UnifiedStatus is computed per run in `enrichMetrics()`. The blocked count is computable at sidebar render time with minimal overhead — it is the same loop that produces `ActiveRuns` and `BlockedAgents` in the metrics struct.

**The plan acknowledges** that `BlockedAgents` count is shown in warning color in the metrics bar (F4.1). But the metrics bar is on the Dashboard tab. The sidebar is visible on all tabs. An operator on the Sessions tab gets no blocked signal from the sidebar under the current plan.

**Recommendation:**
- Change the badge to show blocked count when non-zero: `[1 blocked]` styled in warning color.
- Fall back to run count when blocked is zero: `[2 runs]` in normal style.
- The combined format is: show `[N blocked]` (warning) if blocked > 0, else `[N runs]` (dim) if runs > 0, else nothing.
- This makes the sidebar a live triage surface across all tabs, not just a count display.

**Implementation note:** The `ProjectItem.Title()` method at model.go:337-346 already has the `KernelError` and `RunCount` fields. A `BlockedCount int` field can be added alongside `RunCount` and populated in the same `updateLists()` loop where `item.RunCount` is set (model.go:1116-1122).

---

## Finding 6 — No Empty State Handling

**Severity: P1**

The plan has zero specification for what the dashboard shows when:
- There are no kernel-aware projects (no `.clavain/intercore.db`)
- There are kernel-aware projects but all runs are completed or there have never been any runs
- The `ic` binary is not in PATH

The PRD notes "fail-open: no `ic` = no kernel data" but the plan's rendering tasks only specify the non-empty cases. Looking at the current code, model.go:1500-1530 shows that the Active Runs section is simply omitted when `state.Kernel` is nil or when `runLines` is empty. This is a silent omission — the operator sees a dashboard missing a section they expected, with no explanation.

**Why this matters for the 30-second success signal:** If an operator opens Bigend and the kernel section is absent because `ic` is not in PATH, they may spend the 30 seconds wondering whether their agents are fine (no blocked agents!) or whether data collection failed. Silent omission fails at honest uncertainty — the PRD correctly notes `Unknown` status should show `?` rather than being excluded from Active counts.

**Three distinct empty states that need handling:**

**6a. No ic binary:** Should show a one-line diagnostic in the kernel section: "Kernel data unavailable — `ic` not found in PATH". This is already implied by the "fail-open" policy but never rendered.

**6b. No kernel-aware projects:** The Active Runs section should show "No kernel-aware projects detected. Create `.clavain/intercore.db` with `ic init` to enable run tracking." — not simply disappear.

**6c. Kernel-aware projects with zero active runs:** Show "No active runs" as an explicit state, not an absent section. The operator needs to confirm the system is idle, not guess.

**Recommendation:**
- Add explicit empty state strings for each of these three cases in the F1/F4 rendering tasks.
- The F4.1 metrics bar should show `0 active runs · 0 blocked` rather than disappearing entirely when there are no runs. This gives the operator a confirmed-zero baseline.
- The plan's current spec for `Zero-value graceful: show 0 when no kernel data available` (PRD F4 acceptance criteria) addresses point 6c but not 6a or 6b.

---

## Finding 7 — F2.1 Dispatch View Column Widths

**Severity: P3**

The plan specifies dispatch table columns: ID (8), agent/model (16), task (fill), status (8), duration (6). Fixed total: 38 chars. In an 80-column terminal with a left sidebar (~26 chars) and gaps, the right pane is approximately 52 columns wide. After borders (2 cols each side = 4), the usable content width is ~48 columns. Fixed columns consume 38, leaving 10 chars for the task description.

Ten characters for task description is not enough to convey meaning. "reviewing" is nine characters. "blocked on gate" truncates to "blocked on". This forces the operator to select each dispatch row to see what it is doing — defeating the purpose of the list view.

**Wider terminal (120 cols):** Left sidebar ~38 chars, gaps, right pane ~78 cols, usable ~74. Fixed columns: 38. Task gets 36 chars. This is workable.

**The problem is the 80-col case specifically.** The narrow fallback at F6.4 triggers below 100 cols and switches to run-list-only view. But F2's dispatch view is a sub-panel within the run detail pane, which in narrow mode is behind an overlay. So in narrow mode the dispatch view only appears after Enter, when the full screen is available — at which point column widths are no longer constrained to 48.

**The narrow case is actually fine** once you realize the overlay uses full width. The issue is the 100-119 column "medium" range: wide enough to show the two-pane layout, too narrow to show useful task descriptions.

**Recommendation:**
- Add a medium-width breakpoint at 100 columns. Below 120 columns, collapse the agent/model column from 16 to 10, freeing 6 chars for the task field. In the 100-119 col range, task gets 16 chars — still short but enough for common task prefixes.
- Make the duration column compress to 5 chars (drop seconds for durations over 1 minute: "14m" vs "14m02s"). This frees 1 more char.
- Document the responsive breakpoints in the F6.4 spec rather than treating <100 as the only threshold.

---

## Finding 8 — The 30-Second Success Signal: Flow Analysis

**Severity: P1**

The PRD success signal is: "the operator can answer 'which of my agents is blocked right now?' in under 30 seconds." Let me trace the flow against the plan as specified:

**Optimal flow (120-col terminal, kernel data loaded):**

1. Open Bigend. Dashboard tab is default. [0s]
2. Read the metrics bar: "1 blocked". Note: per Finding 1, the blocked count is the third item in the bar. The operator must read past "projects" and "active runs" first. [~5s]
3. Look at the Active Runs section below. Find the `▲` (blocked) icon on a run. [~5s]
4. The run shows project name, run ID, phase, duration. The operator knows which project has a blocked run. [~3s]
5. Navigate to the project: press `[` to focus sidebar, arrow to select project, `]` to return to main pane. [~5s]
6. In project detail view (not yet F6's two-pane — that's the next tab and requires Tab to the Sessions view? — unclear from plan). Find the blocked run in the run list. [~5s]
7. Tab to the detail pane to see dispatch information explaining why it is blocked. [~3s]

Total: ~26 seconds. Barely under 30. This assumes the operator already knows the `[`/`]` pane focus keys, which are not visible in the footer.

**Degraded flow (operator does not know pane focus keys):**

Steps 5-6 become: switch to Dashboard tab, look at the Active Runs list, press Enter on the blocked run (if Enter navigates — the plan says Enter opens project detail focused on that run for F4.2, but Enter is also the Toggle key for other contexts). If Enter does navigate, the operator reaches the project detail. [~15s additional]

Total: ~41 seconds. Over 30 seconds.

**The primary flow failure:** The dashboard's Active Runs section (F4.2) specifies "Navigate: Enter opens project detail view focused on that run." This is the fastest path to answering the question. But `Enter` is already bound to `Toggle` in CommonKeys (keys.go:81-87) and is the group-header expander (model.go:783-787). The plan must explicitly specify that in the Active Runs list, Enter triggers project navigation rather than the default toggle behavior. This is not specified in the implementation tasks.

**Second flow failure:** After reaching project detail via F4.2's Enter navigation, the operator is in the run-focused detail view (F6). The blocked dispatch is in the detail pane. Getting from the run list to the detail pane requires Tab or `]`. This is not shown in the footer by default. The operator must already know the key.

**Recommendation:**
- The Active Runs section in F4.2 must specify explicit Enter-to-navigate behavior with a footer hint: `enter → open project`. Without this, the fastest triage path (dashboard → blocked run → project detail) is not discoverable.
- The sidebar badge change recommended in Finding 5 (showing `[N blocked]` rather than `[N runs]`) provides a persistent ambient signal on every tab, reducing the operator's need to navigate to the Dashboard tab at all. An operator on the Sessions tab can immediately see which project has blocked agents.
- The help overlay (help.go:56-93) should gain a "Dashboard Navigation" section documenting the Enter-to-navigate and pane-focus flows. Currently the overlay shows only generic key bindings.

---

## Finding 9 — Existing `a` Key Conflict

**Severity: P2**

The plan specifies in F6.1: press `a` to toggle full run history (unfiltered).

The existing key bindings at model.go:538-541 bind `a` to Attach: "attach to session". This binding is only active when `activeTab == TabSessions` (model.go:900-909). F6's run list is within project detail, which is a different view context.

However: the current code at model.go:900-909 checks `m.activeTab == TabSessions` but does not check which pane is focused. If the pane focus rings are added and the run list pane uses `a` for history toggle while `a` is globally bound to Attach in the Sessions tab, an operator focused on the run list pane while the Sessions tab is also visible might get unexpected behavior.

More concretely: the two-pane layout shows sidebar + detail within the Sessions or Agents tab (the plan does not clearly specify which tab hosts the F6 layout). If F6's run detail is shown on the Dashboard tab only, the `a` conflict does not arise. If it appears on the Sessions tab, the conflict is live.

**Recommendation:**
- Clarify which tab hosts the F6 two-pane layout. If it is a new tab or the Dashboard tab, `a` for history is safe. If it is the Sessions tab, rename F6's history key to `H` (shift+a) or `*` to avoid the conflict.
- Document the chosen tab for F6 in the implementation plan.

---

## Finding 10 — Status Symbol Inconsistency Between Old and New Code

**Severity: P3**

The plan (F8.1) specifies the Blocked symbol as `▲` (triangle). The existing `components.go:29` renders Blocked as `!` (exclamation mark). The plan's dispatch view mock (F2.1) shows `▲` for blocked. The `UnifiedStatusSymbol()` function at components.go:24-39 uses `!` not `▲`.

The code has already been partially written (components.go is the current state) and the plan's mock UI uses a different symbol. One of them will ship and one will not — but the plan does not acknowledge this divergence or specify which wins.

Separately: the StatusIndicator function in components.go renders blocked as "✗ BLOCKED" (the error symbol), while UnifiedStatusIndicator renders Blocked as "! BLOCKED". Two different symbols for the same concept within the same file.

**Recommendation:**
- Standardize on one blocked symbol across all paths before F8 ships. The plan's `▲` is the better choice because it is visually distinct from `✗` (error) — the two most important operator-visible states should not share a family of symbols.
- F8.1 should explicitly state: "replace `!` in `UnifiedStatusSymbol()` with `▲`" as a concrete code change, not just a table entry.
- The legacy `StatusIndicator()` function (components.go:55-110) uses different symbols than the new unified system. If it survives E7, it will render inconsistent status displays on the Sessions and Agents tabs. F8.4 says "all status display points use unified model" but the plan does not explicitly say to remove or alias `StatusIndicator()`. This should be made explicit.

---

## Flow: What the Plan Gets Right

These are not issues — they are decisions the plan makes correctly that deserve acknowledgment:

- **Active-first sort in run list (F6.1):** Active runs first, then blocked, then done. Correct operator priority ordering.
- **Phase duration color coding (F6.1):** Green/yellow/red thresholds for time-in-phase. This is the most useful anomaly signal in the entire feature — a run stuck in "plan" for 4h is more diagnostic than its status string.
- **Bootstrap-then-stream dedup (F5):** The composite SyntheticID prevents historical events from appearing as new notifications. This is the right call for operator cognition.
- **Fail-open for missing `ic`:** Projects without kernel data still appear; kernel section is absent rather than blocking the whole dashboard.
- **Per-project failure isolation (PRD):** One bad DB does not corrupt all projects' metrics. Correct.
- **F4.2 Enter navigation from Active Runs to project detail:** The intent is right even if the implementation conflicts need resolution (Finding 8).

---

## Summary of Findings by Priority

| # | Finding | Severity | 30s Goal Impact |
|---|---------|----------|-----------------|
| 8 | Active Runs Enter-to-navigate not specified; focus ring not discoverable | P1 | Direct — blocks the primary triage flow |
| 6 | No empty state handling for no-ic, no-kernel-projects, zero-runs cases | P1 | Direct — silent failure reads as "all clear" |
| 3 | F6.4 Esc semantic conflict with existing Back/dismiss behaviors | P1 | Indirect — traps operators in narrow-mode overlay |
| 1 | F4.1 metrics bar buries blocked count behind lower-priority values | P2 | Direct — slows time-to-blocked-signal |
| 2 | F6 focus ring: Tab ambiguity (tabs vs panes); h/l Vim conflict | P2 | Indirect — slows pane navigation |
| 4 | [K]/[M]/[T] source tags undefined for first-time operators | P2 | Indirect — activity feed noise until decoded |
| 5 | Sidebar badge shows run count, not blocked count | P2 | Direct — no ambient blocked signal outside Dashboard tab |
| 9 | `a` key conflict: history toggle (F6.1) vs Attach (Sessions tab) | P2 | Indirect — wrong action fires in ambiguous context |
| 7 | Dispatch column widths too narrow in 100-119 col range | P3 | Low — task descriptions truncated, forces row selection |
| 10 | Blocked symbol inconsistency (`▲` vs `!` vs `✗`) across old/new code | P3 | Low — visual noise, no triage impact |

---

## Minimum Changes to Achieve 30-Second Goal

If the team wants to ship E7 and have a reasonable chance of the 30-second success signal being met in practice, three changes are required before F4 and F6 ship:

**M1 (from Finding 8):** In F4.2, explicitly specify that Enter on an Active Runs row navigates to project detail focused on that run. Add a footer hint. This is the primary triage shortcut.

**M2 (from Finding 5):** Change the sidebar badge to show blocked count when non-zero (`[N blocked]` in warning color). This gives the operator ambient signal without navigating to the Dashboard tab.

**M3 (from Finding 6):** Add explicit empty states for the three no-data cases (no ic, no kernel projects, zero active runs). Without these, a misconfigured environment looks identical to a healthy idle system.

The remaining P2 and P3 findings are real UX debt but they do not block the core triage flow — they slow it or confuse it, which is measurably bad but recoverable.

---

## Open Questions for the Implementor

1. Which top-level tab hosts the F6 two-pane layout? Dashboard, Sessions, or a new "Runs" tab? This determines whether the `a` key conflict (Finding 9) is live.

2. When the operator presses Enter on an Active Runs row (F4.2), does this switch the active tab? Change the active pane? Open a modal? The plan says "opens project detail view focused on that run" but does not specify the navigation mechanism or what happens to the current tab state.

3. Is the narrow fallback overlay (F6.4) scoped to the detail pane only, or does it cover the full terminal? If full-terminal, Ctrl+C behavior inside the overlay must be specified.

4. The plan says Tab/h/l cycles focus, but the existing code uses Tab for top-level tab switching. Does Tab have different semantics depending on which element is focused? If yes, this must be documented in the footer or help overlay — not just in the plan.

5. The PRD says the secondary success signal is "reduced autarch status usage post-ship." How will this be measured? If there is no instrumentation plan, the secondary signal cannot be validated.
