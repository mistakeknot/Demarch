# fd-ux-onboarding-friction -- Findings

## Summary

The onboarding flow has a strong golden-path spine (Kickoff -> Sprint/Interview -> Spec Summary -> Epics -> Tasks -> Dashboard) but suffers from three categories of friction: orphaned state machine states that create phantom breadcrumb steps, silent dead-ends when the coding agent is absent or generation fails, and a lack of any persistence-based gate that distinguishes first-run users from returning users. The most impactful issues are the AgentNotFoundMsg black hole (P0) and the missing back-navigation from Interview/Sprint state (P1), both of which can permanently stall a user mid-flow.

## Findings

### [P0] AgentNotFoundMsg is silently swallowed -- user hits dead end with no feedback

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh_onboarding.go:186-187`
- **Issue:** When `generateEpicsWithAgent` or `generateTasksWithAgent` detects `codingAgent == nil`, they emit `tui.AgentNotFoundMsg` (lines 811, 859). The onboarding view's Update handler catches this message at line 186 and returns `v, nil` -- doing absolutely nothing. The `Instructions` field of the message (which contains helpful setup instructions from `agent.NoAgentError`) is never displayed to the user. The state has already been set to `OnboardingEpicReview` with `generating = true` (line 537-538 via `handleSpecAccepted`), so the user is stuck in a phantom "generating epics" state with no spinner, no error, and no way to recover.
- **Impact:** Any user who runs Autarch without Claude Code or Codex installed (the `filterSupportedAgentOptions` call at `unified_app.go:252-264` only accepts "codex" and "claude") hits a permanent dead-end after accepting their spec. This is the most critical conversion-killing moment: the user has invested significant effort writing a project description and completing the spec interview, only to have the flow silently die.
- **Fix:** In the `case tui.AgentNotFoundMsg:` handler (line 186), forward the message to `currentView` so the SprintView or SpecSummaryView can display the error in its chat panel. At minimum: `if v.currentView != nil { v.currentView, _ = v.currentView.Update(msg) }`. Additionally, set `v.generating = false` to clear the phantom loading state.

### [P0] Orphaned ScanVision/ScanProblem/ScanUsers states create unreachable breadcrumb steps

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/onboarding.go:8-10` (enum declaration) vs `/home/mk/projects/Demarch/apps/autarch/internal/tui/onboarding.go:19-27` (`AllOnboardingStates()`)
- **Issue:** Three `OnboardingState` values (`OnboardingScanVision`, `OnboardingScanProblem`, `OnboardingScanUsers`) are declared in the iota enum at lines 8-10, and are given ID/Label entries in the `ID()` and `Label()` switch statements (lines 35-40, 61-66). However, they are deliberately excluded from `AllOnboardingStates()` (line 19-27), which only returns `[Kickoff, Interview, SpecSummary, EpicReview, TaskReview, Complete]`. This means the breadcrumb (built from `AllOnboardingStates()` at `breadcrumb.go:32`) never shows these three states. Yet the `navigateToStep` function at `gurgeh_onboarding.go:735` has a case arm for these three states that sets `v.state` and `v.breadcrumb.SetCurrent(state)` -- but since the breadcrumb has no matching step for these states, `SetCurrent` at `breadcrumb.go:66-78` silently fails to find a match and does nothing. The result: the state machine transitions to a state with no visual representation, and the breadcrumb becomes desynchronized from the actual state.
- **Impact:** If any code path ever triggers `NavigateToStepMsg{State: OnboardingScanVision}`, the user's breadcrumb freezes while the internal state advances invisibly. Currently this is unlikely to fire in production (no known trigger), but the latent code path exists and any future refactoring could activate it. More practically, the three dead enum values add 18 lines of dead switch-arm code across `onboarding.go` that confuses contributors.
- **Fix:** Either (a) remove the three orphaned states entirely from the iota, from `ID()`, from `Label()`, and from the `navigateToStep` case arm -- they are artifacts of a planned scan decomposition that never shipped; or (b) if the scan decomposition is planned for a future iteration, add them to `AllOnboardingStates()` and implement proper view factories for them.

### [P1] navigateBack() has no handler for OnboardingInterview/OnboardingSpecSummary -- pressing Back is a no-op

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh_onboarding.go:687-704`
- **Issue:** `navigateBack()` only handles two cases: `OnboardingEpicReview` (goes to kickoff) and `OnboardingTaskReview` (goes to epic review). When the user is in `OnboardingInterview` or `OnboardingSpecSummary` state and triggers `NavigateBackMsg` (e.g., SprintView's Esc on first phase emits `SprintExitRequestedMsg`, which calls `onBack()` -> `NavigateBackMsg`), the switch falls through to `return nil`. The user presses Esc and nothing happens. There is no way to go back to the Kickoff screen from the Sprint/Interview state except by switching tabs entirely.
- **Impact:** A user who starts a sprint, realizes they made a typo in the project description or want to start over, cannot go back. The only escape is to switch to another tab and switch back -- but switching back re-enters the Sprint view in the same state. Effectively the user is trapped in the sprint until they complete it, switch tabs, or quit the TUI entirely.
- **Fix:** Add cases for `OnboardingInterview` and `OnboardingSpecSummary` to `navigateBack()`:
  ```go
  case tui.OnboardingInterview:
      return v.navigateToKickoff()
  case tui.OnboardingSpecSummary:
      // Go back to interview/sprint
      return v.navigateToKickoff() // or recreate sprint view
  ```

### [P1] skipOnboarding field is set but never read -- deprecated flag has no effect

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:66,119` (field and setter), `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go:146-148` (caller)
- **Issue:** The `skipOnboarding` field on `UnifiedApp` is set by `SetSkipOnboarding(true)` when `--skip-onboard` is passed, but the field is never read anywhere in the codebase. The `Init()` method at line 287 always calls `enterDashboard()` unconditionally. Meanwhile, `GurgehConfig` is always non-nil (constructed at `main.go:154`), so `GurgehView` always creates an onboarding sub-view. The deprecated flag does nothing -- it prints a warning to stderr but has zero functional effect.
- **Impact:** A returning user who remembers using `--skip-onboard` in a previous version gets a false deprecation warning but still sees the onboarding flow. There is no functional mechanism to skip onboarding for returning users. Every launch of `./dev autarch tui` shows the Kickoff screen in the Gurgeh tab, even for users who have completed onboarding dozens of times.
- **Fix:** Either (a) implement the skip: when `skipOnboarding` is true, pass `nil` as `gurgehCfg` so `NewGurgehView` sets `showBrowser = true` immediately; or (b) implement persistence-based auto-detection: if `~/.autarch/projects/` contains completed projects, auto-skip to the spec browser. The latter is the better UX since it eliminates the flag entirely.

### [P1] No onboarding completion persistence -- every session restarts from Kickoff

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh.go:48-69` (NewGurgehView), `/home/mk/projects/Demarch/apps/autarch/cmd/autarch/main.go:154-238` (always creates GurgehConfig)
- **Issue:** There is no mechanism to detect that a user has previously completed onboarding. `gurgehCfg` is always constructed and always non-nil, so `NewGurgehView` always creates a `GurgehOnboardingView`. The `persistAndComplete()` function at `gurgeh_onboarding.go:598-621` creates a spec via `client.CreateSpec()`, but this persistence is never checked at startup to determine whether to show onboarding or the spec browser. The `loadRecentProjects()` function at `kickoff.go:311-380` reads from `~/.autarch/projects/` and displays them in the recents list, but this data is never used to gate whether onboarding should show at all.
- **Impact:** Returning users must click through or immediately switch tabs on every session. This trains users to ignore the Gurgeh tab entirely, which is the opposite of what onboarding should achieve. The golden path (zero-to-dispatched-task) is obscured because returning users see the same first-run screen they have already completed.
- **Fix:** At startup in `NewGurgehView` (or in the dashboard factory), check whether specs exist via `client.ListSpecs("")`. If specs are found, pass `nil` for `cfg` so the spec browser is shown immediately. The Kickoff flow should be accessible via a "New Project" command in the palette or sidebar, not as the default landing.

### [P2] Tab bar is fully accessible during onboarding -- accidental tab switch loses all progress

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:479-485` (tab switching keybindings)
- **Issue:** During onboarding, all tab-switching mechanisms work: `ctrl+left/right`, `ctrl+pgup/pgdown`, slash commands (`/big`, `/cold`, `/pol`), and the command palette. If a user accidentally presses ctrl+right mid-interview, they switch to the Coldwine tab. When they switch back to Gurgeh, the onboarding view's state is preserved (since `GurgehOnboardingView` maintains its own state), but the user may not realize they can switch back, or may think their progress is lost.
- **Impact:** While the state is technically preserved, the experience is jarring. There is no visual indication that onboarding is in progress when viewing other tabs, and no "return to onboarding" affordance. Users who accidentally switch tabs during a long AI generation may not realize Gurgeh is still processing.
- **Fix:** Two options: (a) During onboarding, show a small persistent indicator in the tab bar (e.g., a dot or progress badge on the Gurgeh tab) so the user knows onboarding is active. (b) When switching away from Gurgeh during onboarding, show a brief toast or the footer could indicate "Onboarding in progress in Gurgeh tab". Neither requires blocking tab switches -- just providing orientation.

### [P2] GenerationErrorMsg during epic/task generation shows error only in SprintView chat, not in the view that is about to replace it

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh_onboarding.go:182-184`
- **Issue:** When `GenerationErrorMsg` arrives (e.g., agent timeout, network error during epic generation), the handler at line 182 sets `v.generating = false` and then falls through to pass the message to `currentView`. However, by the time epic generation fails, the state is already `OnboardingEpicReview` (set in `handleSpecAccepted` at line 536) but no `currentView` transition has happened yet for the EpicReview view -- that only happens in `handleEpicsGenerated`. So the error message goes to whatever view was previously current (the SprintView or SpecSummaryView), which may display it in its chat panel. But the user sees no actionable recovery path -- there is no retry button, no "go back" prompt, and no indication of what went wrong at the flow level.
- **Impact:** A user whose agent call fails during epic generation sees an error in the chat but has no clear next step. The breadcrumb still shows the previous state. The only recovery is to navigate back and re-accept the spec, which is not discoverable.
- **Fix:** After setting `v.generating = false`, check if the error is retryable and show a message with clear instructions: "Epic generation failed. Press Enter to retry or Esc to go back." Wire a retry mechanism that re-calls `generateEpicsWithAgent`.

### [P2] Breadcrumb "Dashboard" label for OnboardingComplete is misleading

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/onboarding.go:49-50`
- **Issue:** The `OnboardingComplete` state has `ID: "dashboard"` and `Label: "Dashboard"`. In the breadcrumb, this appears as the final step. But the actual transition when reaching `OnboardingComplete` is not to a "dashboard" -- it calls `persistAndComplete()` which emits `OnboardingCompleteMsg`, which then triggers `showBrowser = true` in `GurgehView`, switching to the spec browser. The user sees "Dashboard" in the breadcrumb but ends up in a spec browser view.
- **Impact:** Minor confusion -- the breadcrumb suggests the end state is a "dashboard" (which evokes Bigend), but the actual end state is the Gurgeh spec browser. This could cause users to expect they will be taken to the Bigend dashboard tab.
- **Fix:** Rename the label from "Dashboard" to "Done" or "Specs" to accurately represent the end state.

### [P2] Kickoff sidebar shows interview phase steps (Vision, Problem, Users, etc.) before interview has started

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/kickoff.go:149-161` (`SidebarItems`)
- **Issue:** The KickoffView's `SidebarItems()` method returns the full `InterviewSteps()` list (Vision, Problem, Users, Features + Goals, Requirements, Scope + Assumptions, Critical User Journeys, Acceptance Criteria) with all-empty-circle icons. These appear in the left sidebar of the Kickoff screen before the user has even described their project. The steps are not clickable (they are just display items with "circle" icons), and they preview a process the user has not committed to yet.
- **Impact:** A new user seeing 8 interview phases in the sidebar before typing a single word may feel overwhelmed. The sidebar content is aspirational (showing what will happen) rather than contextual (showing what is relevant now). This front-loads cognitive load at the moment when the user should be focused on a single action: describing their project.
- **Fix:** Return an empty `[]pkgtui.SidebarItem` from `KickoffView.SidebarItems()` until the user has initiated a scan or started typing. Alternatively, show a simplified 3-step overview ("Describe -> Interview -> Build") instead of the full 8-phase list.

### [P3] sendToCurrentView silently discards tea.Cmd -- known bug with no timeline

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh_onboarding.go:1070-1079`
- **Issue:** The `BUG(phase2c)` comment documents that `sendToCurrentView` discards the `tea.Cmd` returned by `Update()`. This means any commands the view returns (timers, IO requests, focus changes) from `AgentRunFinishedMsg` and `AgentEditSummaryMsg` are silently lost. The comment acknowledges this is called from goroutines that cannot return commands to the Bubble Tea runtime.
- **Impact:** Potential for subtle UI glitches -- focus not restoring after an agent run, timers not starting, etc. The practical impact is limited because the two messages being sent (`AgentRunFinishedMsg`, `AgentEditSummaryMsg`) are informational and most views do not return commands from them. But it is a latent correctness issue.
- **Fix:** Convert to the `p.Send()` pattern as noted in the comment. This requires access to the `tea.Program` instance, which can be threaded through via the `GurgehConfig` or via a callback.

### [P3] Double Ctrl+C quit does not warn about in-progress onboarding

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:407-421`
- **Issue:** The double Ctrl+C quit mechanism immediately quits the TUI regardless of onboarding state. If a user is mid-interview or mid-generation and hits Ctrl+C twice within 500ms, the TUI exits without warning. The first Ctrl+C clears the chat input (via `ClearInput()`), which is good, but there is no differentiation between "user wants to clear input" and "user wants to quit" when the user has in-flight AI operations.
- **Impact:** Low severity -- the sprint state is persisted to disk (via the orchestrator's save mechanism), so progress can be resumed via the "recent projects" list on next launch. But the user does not know this, and the abrupt exit could feel like data loss.
- **Fix:** During active onboarding with `generating == true`, show a brief "Generation in progress. Press Ctrl+C again to quit." message instead of immediately quitting. This is a minor polish item.

### [P3] Footer help text during onboarding is dashboard-oriented, not onboarding-oriented

- **File:** `/home/mk/projects/Demarch/apps/autarch/internal/tui/unified_app.go:969-980`
- **Issue:** The footer always shows `/big /gur /cold /pol /sig  ctrl+l logs  ctrl+p palette  ctrl+, settings  /help  ctrl+c x2 quit` regardless of whether the user is in onboarding or dashboard mode. During onboarding, the user does not need to know about tab-switching shortcuts -- they need to know about the current onboarding step's actions (Enter to submit, Ctrl+S to scan, Esc to go back).
- **Impact:** The footer is wasted screen real estate during onboarding. The view's `ShortHelp()` (which returns contextual help like "enter create  ctrl+s scan  ctrl+g model  tab focus") is prepended to the global help, but the global portion dominates and pushes contextual help off-screen on narrow terminals.
- **Fix:** During onboarding, suppress or abbreviate the global footer section. The view-specific `ShortHelp()` already provides the right context -- just give it more room.
