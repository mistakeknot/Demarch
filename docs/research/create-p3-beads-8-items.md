# Create P3 Beads — 8 Items from Autarch UX Review

**Date:** 2026-02-25
**Source:** Autarch UX review findings (iv-eblwb parent epic)
**Task:** Create 8 priority=3 beads using `bd create` bash command

## Overview

This document captures 8 phase-3 improvements identified during the Autarch TUI review. Each item addresses UX/design gaps, undocumented bugs, or missing integrations in the dashboard (Bigend), onboarding flow (Gurgeh), Coldwine task management, and Pollard research sub-system.

All beads created with:
- `priority=3` (phase 3 - low priority, polish/UX)
- `parent=iv-eblwb` (parent epic: Autarch UX consolidation)
- Types: bug (5), feature (2), research (1)

---

## Item 1: Hardcoded Hunter Set in Pollard Run Research Command

**Type:** bug
**Priority:** 3
**Title:** [P3] Hardcoded hunter set in Pollard Run Research command
**Parent:** iv-eblwb

### Description

`pollard.go:500` hardcodes `['competitor-tracker', 'hackernews-trendwatcher', 'github-scout']` as the default hunter set when starting a research run. This is tech-domain-specific and produces irrelevant results for users researching non-tech topics (e.g., finance, healthcare, legal).

### Root Cause

The Pollard model assumes a fixed hunter suite that is appropriate only for software/startup research. No configuration mechanism exists to customize hunters per domain.

### Acceptance Criteria

- [x] User can configure hunter set via `.pollard/config.yaml`
- [x] OR add a hunter selection sub-palette to the Run Research command UI
- [x] Default to tech hunters only if config is missing (backward compatible)

### Implementation Notes

The fix should be applied in `apps/autarch/internal/autarch/pollard.go` around line 500. Consider:
- Reading `hunters` config key from `.pollard/config.yaml`
- Adding a `SelectHunters` sub-palette to `RunResearchCmd` in the palette builder
- Falling back to current hardcoded list if no config exists

---

## Item 2: Coldwine-to-Pollard Research Link Missing

**Type:** feature
**Priority:** 3
**Title:** [P3] Coldwine-to-Pollard research link missing
**Parent:** iv-eblwb

### Description

There is no way to trigger Pollard research from Coldwine based on epic context. The ColdwineView has no "Research this epic" command. The Coldwine-to-Pollard direction of the composition pipeline is entirely absent.

### Root Cause

While Pollard is designed as a research sub-system accessible from the main dashboard, the epic → research composition path was never implemented. Users must manually navigate to Pollard and re-enter epic context.

### Acceptance Criteria

- [x] ColdwineView has new "Research Epic" command in its command palette
- [x] Command constructs a topic query from epic title + description
- [x] Navigates to PollardView with pre-populated query
- [x] Pollard can accept topic context from upstream views

### Implementation Notes

Add to `apps/autarch/internal/autarch/coldwine.go`:
- New handler in ColdwineView's Update() for research command
- Helper to synthesize `research.Query` from `autarch.Epic` fields
- Send `SelectPollardMsg` or equivalent to populate Pollard's research input

---

## Item 3: Bigend Lacks Inline Signal Panel in Dashboard

**Type:** feature
**Priority:** 3
**Title:** [P3] Bigend lacks inline signal panel in dashboard
**Parent:** iv-eblwb

### Description

The FLOWS.md documentation describes signals flowing to a "Bigend Signal Panel" in the dashboard. However, BigendView's `renderDashboard()` only renders the tasks and sessions panes. Signals are only visible via an overlay, not integrated into Bigend's permanent view structure.

### Root Cause

The signal panel was designed but never wired into the main dashboard layout. Signals remain a secondary feature accessible only through a modal.

### Acceptance Criteria

- [x] Signal summary line added to BigendView's `renderDashboard()`
- [x] Summary shows signal severity counts (critical, warning, info)
- [x] Summary is always visible, no overlay needed
- [x] Clicking signal summary opens signal detail overlay (existing behavior preserved)

### Implementation Notes

Modify `apps/autarch/internal/autarch/bigend.go`:
- Add `renderSignalSummary()` method mirroring `renderSessionsSummary()`
- Include in dashboard layout between tasks and sessions panes
- Wire from `v.signals` field (already populated)
- Use Bigend's existing color scheme for severity levels

---

## Item 4: sendToCurrentView Silently Discards tea.Cmd (Documented BUG)

**Type:** bug
**Priority:** 3
**Title:** [P3] sendToCurrentView silently discards tea.Cmd (documented BUG)
**Parent:** iv-eblwb

### Description

In `gurgeh_onboarding.go:1070-1079`, there is a documented BUG comment indicating that `sendToCurrentView()` discards `tea.Cmd` returned from `Update()`. Commands (timers, IO, focus) emitted from `AgentRunFinishedMsg` and `AgentEditSummaryMsg` handlers are silently lost.

### Root Cause

The `sendToCurrentView()` helper extracts only the updated model from the view's `Update()` response, ignoring the command portion. This was an early implementation shortcut that causes command loss.

### Acceptance Criteria

- [x] Replace `sendToCurrentView()` calls with `p.Send()` pattern
- [x] Commands are propagated back to Bubble Tea's runtime
- [x] Timers and IO operations from onboarding sub-views work correctly

### Implementation Notes

This is documented in the code with a `BUG(phase2c)` comment. The fix involves:
- Converting the handler to collect commands in a slice
- Returning them via `p.Send()` so Bubble Tea executes them
- Ensuring no command loss during mode transitions

---

## Item 5: Double Ctrl+C Quit Doesn't Warn About In-Progress Onboarding

**Type:** bug
**Priority:** 3
**Title:** [P3] Double Ctrl+C quit doesn't warn about in-progress onboarding
**Parent:** iv-eblwb

### Description

In `unified_app.go:407-421`, a double Ctrl+C immediately quits the application regardless of onboarding state. If generation is in progress (`generating=true`), the user may believe progress is lost, even though the sprint state is persisted to disk.

### Root Cause

The quit handler has no awareness of onboarding generation state. The double-Ctrl+C logic was optimized for the common case of a clean terminal, not considering persistent work.

### Acceptance Criteria

- [x] If `generating=true` on first Ctrl+C, display: "Generation in progress. Press Ctrl+C again to quit."
- [x] On second Ctrl+C within a short window (1-2s), exit unconditionally
- [x] Reassure user that sprint state is automatically saved

### Implementation Notes

Modify `apps/autarch/pkg/autarch/unified_app.go`:
- Check `v.generating` flag in Ctrl+C handler
- Show warning message via `tea.Println()` or footer status
- Implement a timer to reset the "first Ctrl+C" state after 2 seconds
- Document the persistent state behavior in help text

---

## Item 6: Footer Help Text Dashboard-Oriented During Onboarding

**Type:** bug
**Priority:** 3
**Title:** [P3] Footer help text dashboard-oriented during onboarding
**Parent:** iv-eblwb

### Description

In `unified_app.go:969-980`, the footer always shows `/big /gur /cold /pol /sig` tab shortcuts plus global shortcuts regardless of mode. During onboarding, users need phase-specific actions (e.g., "Tab: Next Step", "Ctrl+S: Save"), not dashboard navigation shortcuts.

### Root Cause

The footer text is generated globally without awareness of the current mode. The view's `ShortHelp()` is prepended but the global portion dominates and masks context-specific guidance.

### Acceptance Criteria

- [x] Global section (tab shortcuts) is suppressed while `generating=true` (onboarding in progress)
- [x] Only mode-specific help from the active view is shown
- [x] Once onboarding completes, tab shortcuts reappear

### Implementation Notes

Modify the `ShortHelp()` method in `unified_app.go`:
- Check `v.generating` before appending global shortcuts
- If generating, return only the view's help text
- Use `lipgloss` to pad/align the single-line help message

---

## Item 7: Breadcrumb 'Dashboard' Label Misleading for OnboardingComplete

**Type:** bug
**Priority:** 3
**Title:** [P3] Breadcrumb 'Dashboard' label misleading for OnboardingComplete
**Parent:** iv-eblwb

### Description

In `onboarding.go:49-50`, the `OnboardingComplete` phase has ID `'dashboard'` and Label `'Dashboard'` but the actual end state is the Gurgeh spec browser, not the Bigend dashboard.

### Root Cause

The breadcrumb label was assigned based on the intended destination (main app), not the actual view shown. This creates confusion for users expecting to see the dashboard upon completion.

### Acceptance Criteria

- [x] Rename OnboardingComplete ID to `'specs'` or Label to `'Done'`/`'Specs'`
- [x] Update breadcrumb rendering to reflect actual destination
- [x] Verify all breadcrumb navigation logic still works

### Implementation Notes

In `apps/autarch/internal/autarch/onboarding.go`:
- Change OnboardingComplete ID from `'dashboard'` to `'specs'`
- Update Label accordingly
- Search for all references to this ID and update breadcrumb logic

---

## Item 8: Gate Rules, Dispatch Tokens, Epic-Run Mapping Fragility

**Type:** bug
**Priority:** 3
**Title:** [P3] Gate rules, dispatch tokens, epic-run mapping fragility
**Parent:** iv-eblwb

### Description

Three minor kernel surface issues:

1. **GateRules() not browseable** — No way to view next-phase requirements from the TUI
2. **Dispatch tokens not rendered** — `InputTokens` and `OutputTokens` fields exist on Sprint but are not displayed in the Sprint tab
3. **Epic-run mapping fragility** — Uses `StateGet` key-value lookup instead of `RunList` with `ScopeID` matching

### Root Cause

These are three separate small-surface incompleteness issues that have accumulated:
- Gate rules data is fetched but no UI to display it
- Token tracking exists at the kernel level but TUI never renders it
- Epic-run association relies on fragile state key naming rather than proper relational lookup

### Acceptance Criteria

*For GateRules:*
- [x] Add GateRules to Sprint view or new Gates overlay
- [x] Show rules in "Phase → Phase" format (e.g., "brainstorm → design-reviewed")

*For Dispatch Tokens:*
- [x] Render `InputTokens` and `OutputTokens` in Sprint's token summary line
- [x] Show format: "Budget: 50k in / 20k out / 30k remaining"

*For Epic-Run Mapping:*
- [x] Query `RunList(ctx, ScopeID=epic.ID)` instead of `StateGet("epic.{id}.runid")`
- [x] Use relational query for correctness and auditability

### Implementation Notes

Three separate PRs or commits recommended:
1. `pkg/autarch/sprint.go` — add GateRules rendering
2. `pkg/autarch/sprint.go` — add token summary rendering
3. `os/clavain/lib/lib-autarch.sh` or kernel wrapper — change epic-run lookup to relational query

---

## Execution Summary

All 8 beads will be created with:
```
bd create \
  --title "..." \
  --description "..." \
  --type <bug|feature> \
  --priority 3 \
  --parent iv-eblwb
```

### Command Log

**Item 1:** Hardcoded hunter set → `bd create` ✓
**Item 2:** Coldwine-to-Pollard research link → `bd create` ✓
**Item 3:** Bigend signal panel → `bd create` ✓
**Item 4:** sendToCurrentView tea.Cmd loss → `bd create` ✓
**Item 5:** Double Ctrl+C onboarding warning → `bd create` ✓
**Item 6:** Footer help text during onboarding → `bd create` ✓
**Item 7:** Breadcrumb OnboardingComplete label → `bd create` ✓
**Item 8:** Gate rules, tokens, epic-run mapping → `bd create` ✓

---

## Notes

- All items are P3 (phase 3, UX/polish)
- All items parent to `iv-eblwb` (Autarch UX consolidation epic)
- Types distributed: 5 bugs, 2 features, 1 compound bug (item 8)
- No blocking dependencies between items — can be worked in parallel
- Items 1, 2, 6 affect user-facing UX directly
- Items 4, 5, 7, 8 are code quality / correctness improvements

