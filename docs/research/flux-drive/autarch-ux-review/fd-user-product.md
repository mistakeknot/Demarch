# Autarch — UX and Product Review

**Reviewer role:** Flux-drive User and Product Reviewer
**Date:** 2026-02-25
**Sources read:** CLAUDE.md, AGENTS.md, autarch-vision.md, demarch-vision.md, FLOWS.md, unified_app.go, onboarding.go, views/gurgeh.go, views/gurgeh_onboarding.go, views/sprint_view.go, views/bigend.go, views/coldwine.go, views/pollard.go, docs/WORKFLOWS.md, gurgeh feedback, coldwine feedback

---

## Primary User and Job

The primary user is a solo developer or small team technical lead who is:

1. Trying to go from a rough idea to dispatched agent tasks without losing the thread between thinking and building.
2. Managing a running fleet of agents mid-sprint and needing to know what is blocked, stalled, or complete.
3. Iterating on a product spec and wanting research to feed back into that spec without manual copy-paste.

The job Autarch serves is: reduce the distance between "I have an idea" and "agents are running against it with a coherent plan." The platform north star is cost per landable change. Autarch is how that cost becomes visible and steerable.

---

## 1. Onboarding Flow: The 8-Phase Spec Sprint

### What the flow does today

The onboarding path is: Kickoff form → SprintView (8 Arbiter phases) → SpecSummary → EpicReview → TaskReview → Dashboard. The 8 Arbiter phases are: Vision, Problem, Users, Features and Goals, Requirements, Scope and Assumptions, Critical User Journeys, Acceptance Criteria.

The SprintView is a chat-driven flow. The arbiter generates a draft for the current phase. The user can type feedback to iterate, type "accept" or press ctrl+right to advance, or press Esc to revert to the prior phase.

### Friction point: the entry ramp is inverted for the target user

The kickoff form asks for project name, description, and path. The description field is the seed for the entire sprint. If the user types "build a CLI tool for managing dotfiles," the arbiter generates a Vision draft immediately. If they have an existing repo, the codebase scan runs Claude Code exploration and pre-fills all phase artifacts before the sprint starts.

The problem is that first-time users see a blank chat panel with a placeholder ("Chat about the current phase...") and a draft already in the document panel. The system is in propose-first mode, but there is no visible signal that this has happened. The user is expected to read the draft in the left panel and respond in the right chat panel. This requires understanding the split-pane convention before the first interaction.

Evidence: the sprint composer hint reads "enter send · ctrl+right accept · tab focus doc · pgup/pgdn scroll." These are four controls in one hint line and none of them answer the first question: "what am I supposed to do right now?" The chat also shows two system messages ("Draft for vision is ready. Review in the left panel." and "Type feedback to iterate, or accept to advance to the next phase.") but these appear in the message history, not as a persistent instruction above the composer. A new user whose instinct is to type before reading has already lost the context.

Recommendation: on first entry to SprintView, show a brief inline welcome state that names the current phase, shows the word count or confidence score of the draft already generated, and offers a single obvious next action. A one-line "Vision draft ready — type feedback or press ctrl+right to accept" in the composer hint (replacing the generic hint) would cost zero implementation effort and halve the confusion.

### Friction point: 8 phases with no time estimate

The onboarding breadcrumb shows: Project → Interview → Spec → Epics → Tasks → Dashboard. The "Interview" step contains 8 Arbiter phases, but the breadcrumb only shows one step for all of them. A user who accepted Vision and Problem and is now on Users has no way to know they are 3 of 8 phases through, or that Acceptance Criteria is the last. The PhaseSidebar exists and renders the 8 phases, but it requires the user to tab-focus to the sidebar to see it — it is not visible by default in the shell layout.

The sidebar defaults to collapsed behavior (the sidebar has 20% of horizontal width per the ShellLayout spec, and the user must know to press ctrl+b to toggle it). This means the phase progress — the single most useful orientation signal during onboarding — is hidden behind a keypress that is not in the sprint composer hint.

Recommendation: during the spec sprint, show the sidebar open by default. The 8 phase labels with completion status (greyed, active, done) communicate progress without any additional text. This is a one-line change in SprintView.Init() to set default focus or explicitly open the sidebar.

### Friction point: Esc and navigate-back collision

In SprintView, pressing Esc while on the first phase sends the user out of the sprint entirely (SprintExitRequestedMsg triggers the onBack callback). On any other phase, Esc reverts to the prior phase. This is consistent internally but collides with the global TUI convention where Esc means "go back one level." A user who presses Esc while reading Vision expects to get to the kickoff form, but on a non-first phase they unexpectedly revert to the previous spec draft. This will surprise users who press Esc to cancel a half-typed chat message.

The revert-on-Esc pattern is genuinely useful for iterating backwards through phases, but it should be a deliberate action, not the default for Esc. Ctrl+z or a visible "Revert" command in the slash command list would be less ambiguous.

### Silent failure on missing agent

If no coding agent is detected, `generateEpicsWithAgent` returns an `AgentNotFoundMsg` with instructions. The `GurgehOnboardingView.Update` handles this message by returning early with `return v, nil` — no action, no message displayed. The `GeneratingMsg` shows `generating: true` and `generatingWhat: "epics"` but `AgentNotFoundMsg` sets `generating = false` and does nothing else visible. The user who has no agent installed sees the "generating epics" spinner stop and then... nothing. There is no error, no instructions displayed, no state recovery path.

This is the most actionable error gap identified. The fix is to display the `AgentNotFoundMsg.Instructions` in the chat panel just as other errors are shown.

Code reference: `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh_onboarding.go`, line 187:
```go
case tui.AgentNotFoundMsg:
    return v, nil
```

This should be:
```go
case tui.AgentNotFoundMsg:
    if setter, ok := v.currentView.(tui.ChatStreamSetter); ok {
        setter.AppendChatLine("No coding agent found. " + msg.Instructions)
    }
    return v, nil
```

### Known bug in generation dispatch

There is a self-documented bug in `gurgeh_onboarding.go` at line 1070:

> BUG(phase2c): sendToCurrentView discards the tea.Cmd returned by Update(). Any commands the view returns (timers, IO, focus requests) are silently lost.

This bug affects the epic and task generation completion path. When epic generation finishes and `finalizeAgentRun` fires, the view's response to `AgentRunFinishedMsg` and `AgentEditSummaryMsg` may involve commands that are silently dropped. The user impact is uncertain but the bug could cause visual state inconsistency at exactly the moment onboarding transitions from epics to tasks.

---

## 2. Four-Tool Composition: Does the Product Cohere?

### The mental model gap

Autarch presents four tool tabs at the top: Bigend, Gurgeh, Coldwine, Sprint, Pollard. Five tabs. The CLAUDE.md lists five tools (Bigend, Gurgeh, Coldwine, Sprint, Pollard) but the autarch-vision.md and the Demarch documentation describe four tools. Sprint is a fifth tab that sits alongside Gurgeh, and Gurgeh contains the sprint wizard in onboarding mode. These are related but not the same: Gurgeh is the spec browser after a sprint completes; Sprint is the dashboard for ongoing Intercore sprints.

This naming doubles the cognitive load of the tab bar. A new user looking at "Gurgeh" and "Sprint" cannot deduce from the names which one to use to start a new PRD spec. The onboarding flow (which starts in Gurgeh) is the correct entry point, but the tab bar places Sprint between Coldwine and Pollard, visually suggesting it is a peer of them rather than a phase of Gurgeh's work.

Recommendation: the Sprint tab should either be a sub-view within Gurgeh (accessible after the spec has been created and promoted to a kernel run), or it should be renamed to reflect what it actually shows: "Runs" or "Dispatches." The current name creates a false parallelism with the other four tools.

### The handoff path: Gurgeh to Coldwine

The SpecHandoffMsg flow is implemented: user invokes "Generate Epics" from the command palette in Gurgeh, a `SpecHandoffMsg` is sent to UnifiedApp, Coldwine's `SetHandoffSpec` is called, and the Coldwine tab is automatically activated. The chat panel adds a system message: "Spec handoff: [title] — generate or review epics for this spec."

This is the correct mechanism and it works. Three gaps weaken it in practice:

First, the handoff is only available via the command palette (ctrl+p), not from a visible button or keybinding in the Gurgeh document view. A user who has just reviewed their spec and wants to proceed to tasks has no visible affordance for the next step. The document view renders Title, Status, Project, Vision, Problem, and Users — but no "Next: Generate Tasks" call to action.

Second, after the handoff, Coldwine shows a system message in the chat panel but the main document pane still shows whatever epics were already loaded. If there are no epics yet, the document shows "No epics found." If there were prior epics from a different spec, they are still selected. The spec filter is not applied automatically because `SetHandoffSpec` only selects the first epic matching the specID, and if no epics exist yet, the selection falls back to index 0 of whatever is in the list.

Third, the generation of epics from a spec requires a slash command or chat command in Coldwine. There is no programmatic trigger that auto-generates epics from the handoff spec. The system message says "generate or review epics for this spec" but does not initiate generation. This requires the user to know to type `/epic generate` or similar. The onboarding path generates epics automatically; the post-onboarding path does not.

### The handoff path: Pollard to Gurgeh

Pollard's insights can be linked to specs via `InsightLink`. The code to link an insight exists (`insightLinkedMsg`). There is no UI in PollardView that exposes this. The command palette has no "Link insight to spec" command. The chat handler may support it, but the `PollardChatHandler` is not included in the reviewed code. In practice, the Pollard → Gurgeh direction is the orphaned half of the research feedback loop.

### The cost-per-landable-change axis

The Demarch north star is cost per landable change: tokens per impact, not raw spend. There is nothing in any of the four tool views that displays this metric, approximates it, or even mentions tokens. The Bigend view shows sessions and dispatches. The Sprint tab shows run phase and status. No view shows:

- Token cost of the current sprint (even approximately)
- Cost breakdown by phase or dispatch
- Comparison of this sprint to prior sprints for similar features
- Whether the active model routing is economical for the current task type

This is not a small gap. The north star metric is invisible to the user. A user cannot optimize what they cannot see. The Interspect profiler is designed to close this loop, but Autarch has no surface where Interspect's recommendations appear.

A minimal viable signal here would be a cost badge in the Sprint tab footer showing total tokens dispatched in the current run. Even a static number without comparison context gives the user a reference point.

---

## 3. Cross-Tool Navigation and Handoff Moments

### Tab switching: functional but not guided

Ctrl+left and ctrl+right cycle tabs. Slash commands `/big /gur /cold /pol` jump to tabs by name. The command palette offers "Switch to [name]" entries. All of these work, but none of them communicate *what to do* on arrival. Switching to Coldwine when there are no epics shows "No epics found." Switching to Bigend when no sessions are running shows "No sessions running" and "Start a task to launch an agent." These empty states name the condition but do not offer a direct action.

A better empty state pattern would couple the "no data" message to a direct action. "No epics found — use ctrl+p > Generate Epics to create epics from your spec" is more useful than "No epics found."

### Focus management across tabs

Each tab maintains its own focus state (Sidebar, Document, Chat). When you switch from Gurgeh's chat panel back to Gurgeh, focus resumes in the chat. This is correct. However, when the Gurgeh tab is switched away from during onboarding (e.g., user presses ctrl+right to look at Bigend during a long epic generation), and then switches back, the SprintView streaming is cancelled via `Blur()` which calls `cancelStreaming()` and `cancelContext()`. If generation was in progress, switching tabs destroys the in-flight context.

The generation itself runs in a goroutine that writes to a channel, but the Bubble Tea command chain that reads from that channel is cancelled when the view blurs. The result is that generation is interrupted if the user multi-tasks across tabs during onboarding. This is a known Bubble Tea challenge, but it means the onboarding flow is fragile in a multi-task scenario that is completely natural: start a sprint, switch to Bigend to check on running sessions, come back.

The fix is to make generation commands long-lived background commands that survive tab switches, not view-local context cancellations. This is a non-trivial refactor but the user impact is high — lost generation progress is disorienting.

---

## 4. The Golden Path: Zero to Dispatched Agent Task

### Mapped path

1. `./dev autarch tui` — opens Autarch on Bigend tab. Gurgeh tab contains the onboarding.
2. Switch to Gurgeh. Onboarding kickoff form appears.
3. Enter project name, description. Optionally scan codebase.
4. SprintView activates. 8 phases of propose-accept-revise.
5. Sprint completes. SpecSummaryView appears.
6. Accept spec. EpicReview appears with agent-generated epics.
7. Accept epics. TaskReview appears with task list.
8. Accept tasks. Dashboard opens. Bigend tab is now active.
9. In Bigend, select a ready task. Press Enter to launch it (via onTaskSelect callback).
10. Agent is dispatched. Session appears in Sessions pane.

### Where the path breaks

Step 2 is the first break. The Gurgeh tab defaults to GurgehOnboardingView only if `GurgehConfig` is provided and `cfg != nil` check passes. Looking at the code, `NewGurgehView` receives a `*tui.GurgehConfig` from the dashboard view factory. If this is nil (no onboarding config), `showBrowser = true` and the spec browser appears immediately without onboarding. This is correct for users who have existing specs. But there is no explicit prompt that says "you have no specs yet — start the onboarding flow." The empty state says "No specs found. Use the command palette (ctrl+p) to create a new spec." That leads to "New Spec" which creates an untitled draft spec without triggering the 8-phase sprint wizard. The onboarding sprint wizard is only triggered when the tab initializes with a config, not from the "New Spec" command.

This means a returning user who wants to create a second spec goes through a different flow than a first-time user who just installed the tool. The first-time flow is: Gurgeh loads with onboarding config → SprintView. The repeat flow is: Gurgeh shows spec browser → "New Spec" → creates a blank spec → no sprint wizard. The 8-phase workflow is not accessible for spec iteration in the browser mode.

Step 9 is a conditional break. The Bigend task selection callback (`onTaskSelect`) is wired from the dashboard view factory but depends on `SetTaskSelectCallback` being called. If the callback is not wired (which depends on how the factory constructs the views), pressing Enter on a ready task does nothing. There is no error and no feedback. The user is left wondering if something happened.

Step 10 depends on tmux being available. Bigend's agent launch path uses `tmux.NewClient()` which calls `IsAvailable()`. If tmux is not running, launching an agent silently does nothing (the `slog.Warn` appears in the log pane but not in the main UI). The log pane is hidden by default. A user without tmux gets no explanation.

### Net assessment of the golden path

The path is technically complete for a user with: (a) a coding agent installed, (b) tmux running, (c) knowledge that the sprint wizard is accessed via the Gurgeh tab on first run, and (d) patience to discover that ctrl+p is needed to handoff from Gurgeh to Coldwine. That is a narrow corridor.

The path breaks silently for: (a) users without an agent (no error shown), (b) users wanting a second spec (wizard not accessible), (c) users whose generation was interrupted by tab switching (no recovery path), (d) users without tmux (no explanation).

---

## 5. Error Visibility

### Summary of error handling patterns

| Scenario | Error Surface | Actionable? |
|---|---|---|
| Intermute unavailable | Footer badge `[offline — reading local files]` | Informational only |
| Agent not found during epic generation | Silently drops AgentNotFoundMsg | No — bug |
| Data load failure (epics, tasks, sessions) | Sets data to nil, shows empty state | No — no recovery action shown |
| Sprint generation error | Chat panel: "Error: [message]" | Partial — user sees the message but has no guidance |
| Dispatch failure | Chat panel: "Dispatch failed: [error]" | Partial |
| Task status persistence failure | Chat panel: "Failed to persist task status: [error]" | No recovery path shown |
| tmux unavailable for agent launch | slog.Warn in log pane (hidden by default) | No |
| Agent generation interrupted (context cancel) | No message — generation just stops | No |

The strongest pattern is the footer fallback badge and the `[offline — reading local files]` indicator. This is well-executed: visible, persistent, unobtrusive. The weakest pattern is the silent AgentNotFoundMsg drop and the tmux-unavailable-no-feedback case.

The general pattern is that errors go to the chat panel if a chat panel is active, which means they are invisible in views that have no chat panel (the onboarding kickoff form, the epic review, the task review) and invisible when those views are not currently focused.

### Recovery path analysis

None of the error states in the code offer a recovery path beyond "try again." There is no retry button, no "check what went wrong" link, no guidance on what the user should change. For a platform targeting developers who will run this tool repeatedly, this is low priority. But for a tool being evaluated by a new user who hits an agent-not-found condition in the first 60 seconds, recovery guidance is the difference between "this tool is broken" and "I need to install claude first."

---

## 6. Cost Per Landable Change: Does Autarch Help?

The north star metric is tokens per impact. Autarch's contribution to that metric should be: (a) making the spec good enough that execution requires fewer correction cycles, (b) surfacing which agents are expensive and which are effective, (c) letting the user see and act on Interspect's routing recommendations.

None of these are currently visible in the TUI.

### What is visible

Bigend shows: sessions (by name and status), dispatches (by ID and status), ready tasks. The Sprint tab shows: run ID, phase name, phase status. Neither shows token counts, cost, or any proxy for efficiency.

### What should be visible for the north star to be actionable

A minimal set of signals that would make cost-per-landable-change visible without becoming noise:

1. **Sprint cost summary**: total tokens dispatched in the current run, broken down by phase. Even a rough estimate ("~120k tokens, ~$0.40 at Sonnet rates") in the Sprint tab footer gives the user a reference point.

2. **Dispatch cost per task**: in the Coldwine task list, after a dispatch completes, show the token count alongside the status badge. "Done [42k tok]" next to the task name.

3. **Model routing visibility**: the agent selector shows which model is selected globally, but the dispatch list in Bigend does not show which model was used for which dispatch. The `ic dispatch list` output includes this in `AgentName`. Rendering it in the Sessions pane would let users see whether expensive models are being used for cheap tasks.

4. **Interspect signal integration**: the signals overlay exists and works. If Interspect proposes "this reviewer consistently produces 0 actionable findings — consider removing it," that signal should appear in the signals overlay, not only in the kernel event log. The signals overlay renders `competitor_shipped`, `assumption_decayed`, and `spec_health_low` — all research/quality signals. There is no routing efficiency signal type defined.

---

## 7. Information Hierarchy and Progressive Disclosure

### Footer density

The global footer content (from `renderFooterContent`) is:

```
[view-specific short help]  │  /big /gur /cold /pol /sig  ctrl+l logs  ctrl+p palette  ctrl+, settings  /help  ctrl+c×2 quit
```

This is a single line with 10 distinct items separated by spaces. On a standard 80-column terminal, this wraps or truncates. At 100 columns (the stated minimum for `ShellLayout`), it is marginally legible. The commands are undifferentiated — navigation shortcuts, feature toggles, and quit all share the same visual weight. There is no grouping by urgency or frequency of use.

A developer who knows the tool ignores this line. A new user who reads it sees: /big /gur /cold /pol /sig (tab names without context), ctrl+l (unknown), ctrl+p (unknown), ctrl+, (unknown), /help (probably useful), ctrl+c×2 quit (useful). The most useful commands for a new user (ctrl+p, /help) are buried at the end.

### Help overlay

The help overlay (triggered by `?`) renders view-specific bindings plus the global list. The global section lists "ctrl+g: Agent selector" but the agent selector shortcut in the sprint view is F2. These are inconsistent — the sprint view shows F2 in its footer hint while the help overlay claims ctrl+g. This will confuse users who press ctrl+g in the sprint view expecting the agent selector.

### Empty state guidance

As noted above, empty states tell the user what is missing but not what to do. The spec browser's empty state ("No specs found. Use the command palette (ctrl+p) to create a new spec.") is the best example — it names the action and the keypress. The Bigend empty state ("No sessions running. Start a task to launch an agent.") names the action but not how to perform it. The Coldwine empty state ("No epics found") names nothing.

---

## 8. Scope and Product Fit Assessment

### Problem definition is sharp, solution fit has gaps

The problem Autarch solves is real and well-defined: the distance between idea and dispatched agents is large, and the existing CLI tooling (raw `ic` commands, Clavain skill invocations) is not accessible to users who think in products, not in kernels. The TUI surface that bridges spec creation, epic generation, task orchestration, and research intelligence is the right answer to this problem.

The solution fit has three gaps:

**Gap 1: The onboarding flow is the product, but it is nested three levels deep.** To access the 8-phase spec sprint, the user must: (a) run `./dev autarch tui`, (b) switch to the Gurgeh tab, (c) know that Gurgeh contains onboarding. Nothing on the Bigend landing screen (the default tab) says "start here." A user who opens Autarch for the first time sees the Bigend dashboard, which shows empty sessions and empty tasks. There is no visible entry point to creating a spec.

**Gap 2: The four tools are independent dashboards that share a tab bar but do not share a workflow.** The autarch-vision.md is explicit that this is temporary (arbiter extraction to Clavain is scheduled, Coldwine orchestration intents are planned), but today the user must carry the thread manually. After accepting a spec in Gurgeh, nothing in the UI says "now go to Coldwine." After dispatching a task in Coldwine, nothing in the UI says "now monitor in Bigend."

**Gap 3: Sprint is an orphan tab.** The Sprint tab renders Intercore run state for ongoing sprints. It is the most directly relevant view for a user who is mid-sprint and wants to see phase progress and gate status. But it has no connection to the Gurgeh spec that initiated the sprint, no link to the Coldwine tasks executing under it, and no cost visibility. It is an observer of kernel state that does not participate in the user's workflow.

### Scope creep risk

The feature set (8-phase PRD generation, multi-domain research, task dependency DAGs, agent coordination, competitor monitoring, signal overlay) is architecturally coherent but onboarding-heavy. The first value a user gets from Autarch should be achievable in under 10 minutes without reading documentation. Today that is not the case. The fastest path to first value is probably a stripped-down entry point: "Start new project" → Sprint wizard → Dispatch first task. Everything else (Pollard watch, assumption decay, competitor signals) is a power-user feature that should be discoverable but not required.

### Alternative: non-code approaches for specific gaps

The Gurgeh→Coldwine handoff gap could be resolved with a single workflow document that the user opens alongside the TUI, not with a new UX feature. The cost-per-landable-change visibility gap could be addressed by making `ic run show --json` output readable in the Sprint tab without building a dedicated cost panel. These are not recommendations to avoid building, but they are honest about which gaps are product architecture gaps versus gaps that could be closed by better documentation for the current design.

---

## Priority Finding Summary

### P0: Blocking user success

1. **AgentNotFoundMsg is silently dropped during epic generation** — `/home/mk/projects/Demarch/apps/autarch/internal/tui/views/gurgeh_onboarding.go` line 187. User who lacks a coding agent sees no error and no recovery path.

2. **No entry point from Bigend to the onboarding flow** — the default tab shows empty state with no visible path to starting. New users cannot discover the spec sprint without reading docs.

### P1: Undermining product value

3. **Cost per landable change is invisible** — The north star metric has no surface in any of the four tool views. Users cannot see or optimize the metric the platform is designed to minimize.

4. **Sprint tab is disconnected from Gurgeh and Coldwine** — it shows kernel run state in isolation without spec context or task context. Users cannot answer "is this run worth continuing?" from the Sprint tab.

5. **Generation context cancelled on tab switch** — switching away from Gurgeh during epic or task generation cancels the in-flight request. There is no recovery path.

### P2: Adoption risk

6. **PhaseSidebar hidden by default during sprint** — the most useful orientation signal in the sprint wizard (8 phases, which one is current, how many remain) is behind a ctrl+b toggle that is not in the sprint hint line.

7. **No second-spec path** — "New Spec" in the command palette creates a blank draft, not a sprint wizard. Repeat use of the 8-phase flow is not accessible after onboarding.

8. **Gurgeh→Coldwine handoff requires command palette** — there is no visible affordance in the Gurgeh document view that says "proceed to task generation."

9. **tmux unavailability fails silently in log pane** — agent launch fails without notification in the main UI.

10. **Footer renders all controls at equal weight** — most valuable commands for new users (ctrl+p, /help) are buried at the end.

### P3: Polish

11. **Help overlay agent selector shortcut inconsistency** — "ctrl+g" in help, "F2" in sprint footer.

12. **Esc/revert collision** — pressing Esc in the chat pane reverts the spec phase rather than cancelling the chat input. Users expect Esc to cancel, not navigate.

13. **Empty states name conditions without naming actions** — Coldwine, Pollard, and Bigend empty states are informational but not actionable.

---

## Measurable Success Signals

For the changes above, the following are observable proxies for improved outcome:

- **Time from first run to first dispatched task** — target under 15 minutes for a user with a coding agent installed and a project in mind.
- **Onboarding completion rate** — percentage of users who reach TaskReview without abandoning. Measurable by presence of `.coldwine/tasks.json` after a session.
- **Agent-not-found error encounter rate** — measurable by logging AgentNotFoundMsg receipt rather than silently dropping it.
- **Tab switches during sprint generation** — if users are switching tabs during generation, the context cancellation bug is actively harming them.

---

## Smallest Change Set for Meaningful Improvement

In priority order, the changes that would most improve user outcome confidence without requiring architectural changes:

1. Display AgentNotFoundMsg.Instructions in the chat panel (5 lines of code, P0 fix).
2. Add a "Start new project" prompt to Bigend's empty state that switches to Gurgeh (1-line navigation command).
3. Open PhaseSidebar by default in SprintView.Init() (1 line change, communicates progress immediately).
4. Replace the generic sprint composer hint with a phase-specific hint ("Vision draft ready — type feedback or ctrl+right to accept").
5. Add a "Proceed to Coldwine" call-to-action in the Gurgeh spec document view once a spec is in Validated status.
6. Render token count in Sprint tab footer once a run is active (read from `ic run show`, display in status line).

These six changes are low-risk, low-effort, and directly address the P0 and P1 findings.
