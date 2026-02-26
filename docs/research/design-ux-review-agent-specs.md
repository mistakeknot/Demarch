# Agent Specs: Autarch UX Review

Generated: 2026-02-25
Target: /home/mk/projects/Demarch/apps/autarch/

## Analysis Summary

Before the agent specs, this section captures the key architectural and UX facts
discovered during analysis. It informs why the five agents are shaped as they are.

### What exists today

**Unified TUI** (`internal/tui/`): 5 tabs — Bigend, Gurgeh, Coldwine, Sprint, Pollard.
Tab switching via slash commands (/bigend, /gurgeh, etc.) or Ctrl+Left/Right cycling.
Ctrl+P opens the command palette. A Sprint tab was added as a 5th tab alongside the
canonical 4, creating a documentation–reality gap (AGENTS.md says "exactly 4 tabs").

**Onboarding** (`internal/tui/onboarding.go`): 9 states (Kickoff → ScanVision/Problem/Users
→ Interview → SpecSummary → EpicReview → TaskReview → Complete). ScanVision/ScanProblem/ScanUsers
exist as defined states but do NOT appear in the canonical ordered list returned by
AllOnboardingStates() — they are latent/orphaned. The interview has 8 substeps. Completion
lands at OnboardingComplete with ID "dashboard" — onboarding is entirely housed inside Gurgeh,
not the shell, which means other tabs are inaccessible during onboarding. OnboardingCompleteMsg
is a no-op in the shell (handled in Gurgeh).

**Command palette** (`internal/tui/palette.go`): Single injected command list per tab switch
(SetCommands updated via updateCommands()). Max 8 results shown. Non-broadcast commands
execute locally; broadcast commands go through Target → Confirm phases. Targets are agent
runtimes (Claude/Codex/Gemini), NOT tools or kernel concepts.

**Bigend** (`internal/tui/views/bigend.go`): Tasks + Sessions panes in 2-col (width≥80) or
stacked layout. Agency logic delegated to autarch.Client (ListSessions/CreateSession) and
optional intercore.Client (DispatchList). Local focus state (FocusSessions/FocusTasks) with
F3 toggle. Chat is third pane. Coldwine tab has a dispatch key `d` — single-letter hotkey
that AGENTS.md prohibits during typing.

**Gurgeh** (`internal/tui/views/gurgeh.go`): Onboarding-first or direct browser. Main UX is
Sidebar (spec list + status icons) + Spec Details + Chat. "Generate Epics" emits SpecHandoffMsg
to Coldwine — but the user must manually switch tabs; no auto-navigation occurs. Agency logic
is delegated to autarch.Client; arbiter execution is outside this view but the oracle review
found ArbiterView holds a coordinator it doesn't use, and RunTargetedScan is a no-op.

**Coldwine** (`internal/tui/views/coldwine.go`): 3-pane shell, task navigation. Dispatch (`d`)
triggers Intercore run creation. Intercore integration is conditional — if absent, users get
planning but no execution path. Agency logic: local planning CRUD against autarch.Client then
Intercore dispatch. Some agency logic (epic/task state machine) lives in the TUI view, not OS.

**Pollard** (`internal/tui/views/pollard.go`): Sidebar (hunter statuses or insight list) +
document pane (insight details) + chat. "Run Research" in palette calls coordinator.StartRun
with hardcoded hunters (competitor-tracker, hackernews-trendwatcher, github-scout). "Link
Insight" links to a spec. No mechanism to surface research findings proactively to Bigend or
Gurgeh while on another tab.

**Sprint tab** (`internal/tui/views/sprint_view.go`): A 5th tab not mentioned in most docs.
Surfaces Intercore run/dispatch/event state — the closest thing to "pure kernel rendering".

### Key gaps vs vision

1. **Onboarding locks the user into Gurgeh**: Other tabs unreachable during the 8-substep
   interview. No progress indicator visible in the tab bar.

2. **Cross-tool handoffs require manual tab switches**: Gurgeh→Coldwine emits SpecHandoffMsg
   but user must switch manually. Pollard findings don't surface proactively to Gurgeh/Bigend.

3. **Agency logic in the wrong layer**: Coldwine task/epic state machine and dispatch wiring
   are TUI-layer code. Gurgeh arbiter logic (confidence scoring, phase consistency) has
   duplicate implementations. Vision says this should live in Clavain (OS).

4. **Kernel capabilities not surfaced**: Sprint tab surfaces Intercore state but Bigend (the
   primary monitoring view) only shows tasks+sessions, not run/dispatch/event state from the
   kernel. Users can't see kernel phase/gate/budget state without switching to Sprint.

5. **Discoverability fragmentation**: Tab switching relies on slash commands (chat input
   focus required), Ctrl+left/right cycling (no visual affordance), or clicking — mixing
   paradigms. Palette commands update per-tab but there's no cross-tab navigation command in
   the palette.

6. **Sprint tab exists but isn't in the tab naming convention**: AGENTS.md lists 4 tools;
   Sprint is a 5th. The merge-sprint-into-coldwine PRD (2026-02-25) plans to resolve this.

7. **ScanVision/Problem/Users states are orphaned**: Defined in onboarding.go but excluded
   from AllOnboardingStates(). If these represent quick-scan integration points (Pollard
   feeding into Gurgeh interview), they're dead code masking a missing capability.

8. **Swallowed errors on critical paths**: Intermute Start() errors dropped; scan/research
   errors not surfaced. Users see silent failures as empty data rather than actionable errors.

---

## Agent Specs (JSON)

```json
[
  {
    "name": "fd-ux-onboarding-friction",
    "focus": "Review the Gurgeh onboarding wizard for UX friction, accessibility during flow, and alignment with a first-run-to-dispatched-task golden path",
    "persona": "A product UX reviewer with expertise in TUI wizard flows and first-run conversion. Approaches onboarding as a critical user acquisition moment where every unnecessary step or blocked state loses the user permanently.",
    "decision_lens": "Prioritizes friction that blocks or discourages completion of the golden path (zero-to-dispatched-task). Flags any point where the user cannot understand what to do next, cannot escape, or cannot see progress.",
    "review_areas": [
      "Verify AllOnboardingStates() ordering matches the 9 defined states in onboarding.go — ScanVision/ScanProblem/ScanUsers are defined but excluded from the canonical flow, which may represent dead capability or a missing integration point with Pollard quick-scan",
      "Check whether other tabs (Bigend, Coldwine, Pollard, Sprint) are reachable during onboarding, and whether the tab bar communicates that they are locked — assess the UX cost of the full-session lock-in",
      "Evaluate the 8-substep interview (vision, problem, users, features/goals, requirements, scope/assumptions, critical journeys, acceptance criteria) for cognitive load — is the ordering optimal, are intermediate saves possible, and can users resume an interrupted session?",
      "Assess progress visibility: does the tab bar, breadcrumb, or any other chrome communicate which onboarding stage the user is at and how many remain?",
      "Verify the transition from OnboardingComplete to dashboard — does the app navigate to a useful starting state, and is there a handoff moment that telegraphs what to do next (e.g., 'your spec is ready, go to Coldwine')?",
      "Check whether onboarding is re-enterable for existing projects — can a user who has specs invoke onboarding again, and is the skip path (`--skip-onboard`) sufficiently discoverable?"
    ],
    "success_hints": [
      "Onboarding completion should leave the user on a screen that makes the next action (switch to Coldwine, generate epics) immediately obvious without documentation",
      "A user seeing the TUI for the first time should be able to infer their current stage and remaining steps from visible UI chrome alone",
      "The golden-path smoke test (scripts/golden-path-smoke.sh) should correspond to an actual user-executable sequence, not just file-level event verification"
    ],
    "task_context": "Autarch is a 4-tool tabbed Bubble Tea TUI (Bigend, Gurgeh, Coldwine, Pollard) serving as Layer 3 of the Demarch autonomous software development platform. The onboarding wizard lives inside Gurgeh and is the primary first-run experience. The vision's north star is cost per landable change across autonomy, quality, and token efficiency axes.",
    "anti_overlap": [
      "fd-ux-cross-tool-composition covers post-onboarding cross-tab handoffs and tool-to-tool data flows",
      "fd-ux-kernel-surface-gap covers the gap between kernel/OS capabilities and TUI rendering",
      "fd-ux-vision-delivery-gap covers high-level gaps between what vision docs promise and what the TUI delivers"
    ]
  },
  {
    "name": "fd-ux-cross-tool-composition",
    "focus": "Review whether the four tools (Bigend, Gurgeh, Coldwine, Pollard) compose into a coherent product experience, specifically examining cross-tab navigation, handoff moments, and signal propagation",
    "persona": "A product experience architect who has designed multi-tool development environments. Evaluates composition through the lens of progressive disclosure: can a user stay in flow as they move from ideation through execution, or do they experience jarring context breaks?",
    "decision_lens": "Prioritizes findings where a user must perform manual bridging work (switching tabs, re-entering context, re-running commands) that the system could handle automatically, and cases where a tool's output is not visibly consumed by the downstream tool.",
    "review_areas": [
      "Trace the Gurgeh→Coldwine handoff: when 'Generate Epics' emits SpecHandoffMsg, does the TUI auto-navigate to Coldwine or leave the user stranded in Gurgeh? Check whether ColdwineView is even subscribed to SpecHandoffMsg when it is not the active tab",
      "Evaluate Pollard→Gurgeh research integration: Pollard findings can be linked to specs via 'Link Insight', but does Gurgeh visibly reflect linked insights when browsing specs? Does Bigend surface active Pollard hunter runs as signals?",
      "Check the Sprint tab's relationship to Coldwine: if Sprint is being merged into Coldwine (per the 2026-02-25 PRD), assess whether their current UX models are compatible or whether merging creates a split-personality view with incompatible information densities",
      "Audit the command palette's cross-tool reach: are there palette commands for 'switch to Coldwine', 'link current spec to Pollard', or similar cross-tool navigation actions, or does the palette only expose within-tab actions?",
      "Review slash command discoverability for tab navigation — /bigend, /gurgeh, /coldwine, /sprint, /pollard require the user to know the magic strings and have chat focused; compare this to the Ctrl+left/right cycling and assess which model wins for multi-tab power users",
      "Verify that signals emitted by one tool (e.g., Pollard hunter completion, Coldwine dispatch completion) are visible on the Bigend signals panel, and that the signal flow documented in FLOWS.md matches the actual event wiring in the codebase"
    ],
    "success_hints": [
      "A user completing a Gurgeh spec should be able to reach a running Coldwine dispatch in 3 or fewer explicit interactions, with no manual data re-entry",
      "Bigend should be able to serve as a passive dashboard that a user can glance at from any other tab — signals from all tools should flow there without the user switching to Bigend"
    ],
    "task_context": "Autarch is a 4-tool tabbed Bubble Tea TUI (Bigend, Gurgeh, Coldwine, Pollard) serving as Layer 3 of the Demarch autonomous software development platform. The documented composition pipeline is Gurgeh→Coldwine→Pollard (Bigend observes all). FLOWS.md describes cross-tool handoffs via SpecHandoffMsg, EpicProposal, InsightLink, and the Event Spine.",
    "anti_overlap": [
      "fd-ux-onboarding-friction covers the first-run wizard flow within Gurgeh exclusively",
      "fd-ux-kernel-surface-gap covers the gap between Intercore/Clavain capabilities and TUI rendering",
      "fd-ux-agency-layer-leak covers agency logic that has migrated into the TUI layer instead of living in Clavain/Intercore"
    ]
  },
  {
    "name": "fd-ux-kernel-surface-gap",
    "focus": "Review where the TUI fails to make Intercore kernel and Clavain OS capabilities accessible, visible, or actionable to the user",
    "persona": "A systems UX specialist who has designed observability interfaces for distributed systems. Evaluates whether the operational state of the underlying platform (runs, dispatches, phases, gates, budgets, events) is legible and actionable from the TUI surface.",
    "decision_lens": "Prioritizes capabilities that exist in the kernel/OS but are invisible to the user, cases where the user must drop to the CLI (`ic` commands) to perform actions that the TUI should surface, and cases where degraded kernel connectivity silently removes capabilities without user notification.",
    "review_areas": [
      "Audit Bigend's current kernel surface: it shows tasks+sessions via autarch.Client and optionally DispatchList via intercore.Client — but does it show run phase, gate status, budget consumed/remaining, or event log? Cross-reference with the 'Autarch status tool' section of autarch-vision.md which defines exactly these four views as the target",
      "Review how Coldwine communicates kernel connectivity status to the user: sprint/dispatch commands are conditionally added only when Intercore is present, but is there a visible affordance that tells the user 'kernel is offline — execution disabled'? Or does the user discover this only by trying to dispatch?",
      "Check the Sprint tab against autarch-vision.md's description of the Autarch status tool — does it surface run/dispatch/event state in the format the vision specifies, and is the phase advancement / gate override / submit-artifact write path exposed?",
      "Verify whether the four app→OS write intents (start-run, advance-run, override-gate, submit-artifact) are surfaced anywhere in the TUI — palette commands, chat commands, or explicit UI affordances — or whether they require CLI knowledge",
      "Assess Bigend's fallback behavior (LocalSource) — does the TUI communicate clearly that it is running in degraded/offline mode, and does it guide the user toward restoring kernel connectivity?",
      "Review whether the onboarding wizard or any first-run flow establishes Intercore connectivity as a prerequisite or detects its absence gracefully"
    ],
    "success_hints": [
      "A user should never need to run `ic` CLI commands to understand what is happening in a running sprint — all state visible via `ic run list`, `ic dispatch list`, `ic budget`, and `ic event log` should be surfaceable within the TUI",
      "When Intercore is unavailable, the TUI should present a clear call to action (e.g., 'Start kernel' or a setup guide) rather than silently hiding execution features"
    ],
    "task_context": "Autarch is a 4-tool tabbed Bubble Tea TUI serving as Layer 3 of the Demarch platform, sitting atop Clavain (OS, Layer 2) and Intercore (kernel, Layer 1). The vision defines a minimal write-path (4 intents: start-run, advance-run, override-gate, submit-artifact) and direct kernel reads for observability. The Sprint tab is the closest thing to a pure kernel rendering surface.",
    "anti_overlap": [
      "fd-ux-agency-layer-leak covers the reverse problem: agency logic that should be in the kernel/OS but lives in the TUI",
      "fd-ux-onboarding-friction covers onboarding wizard UX specifically",
      "fd-ux-cross-tool-composition covers cross-tab handoffs and signal propagation between tools"
    ]
  },
  {
    "name": "fd-ux-agency-layer-leak",
    "focus": "Review where agency logic that belongs in Clavain (OS) or Intercore (kernel) has leaked into the TUI layer, creating coupling that prevents the TUI from being a pure rendering surface",
    "persona": "An architecture reviewer specializing in layered systems and separation of concerns. Treats every business rule, state machine, or policy decision found in the TUI as a defect against the vision's 'apps are pure renderers' contract.",
    "decision_lens": "Prioritizes findings by blast radius: logic that must be duplicated if a second UI client is built is higher priority than logic that is merely inconveniently placed. Flags duplicate implementations as the most concrete evidence of layer violations.",
    "review_areas": [
      "Identify which parts of Coldwine's task/epic state machine (todo→in_progress→working→done) live in coldwine.go vs in Intercore kernel state — if the TUI is computing or caching task readiness rather than reading it from the kernel, that is a layer violation",
      "Audit the two duplicate confidence/consistency implementations (arbiter/confidence vs gurgeh/confidence, arbiter/consistency vs gurgeh/consistency) identified in the oracle review — are they still present, and which one does the TUI currently use? The duplication is direct evidence of arbiter logic that was never extracted to the OS",
      "Check whether Coldwine's dispatch mapping (correlating Intercore dispatch-completion events to local task objects and updating task status) is TUI-layer logic or whether a kernel/OS mechanism owns this mapping — the TUI should receive pre-computed task status, not compute it from raw dispatch events",
      "Review Gurgeh's onboarding wizard: the 8-substep interview with phase sequencing, scan triggers, and confidence gating — does any of this phase logic belong in the Clavain OS phase/gate model rather than in the TUI's state machine?",
      "Assess whether Pollard's hardcoded hunter set in 'Run Research' (competitor-tracker, hackernews-trendwatcher, github-scout) is a policy decision that should live in the OS, and whether the research coordination protocol belongs at the TUI layer or below",
      "Verify whether the vision's four write intents (start-run, advance-run, override-gate, submit-artifact) are the only writes Autarch makes to Clavain/Intercore, or whether the TUI is making additional writes that bypass the intended OS policy layer"
    ],
    "success_hints": [
      "If a second UI client (e.g., a web UI) were built tomorrow, it should be able to replicate Autarch's core workflows by implementing only the four write intents and read-from-kernel — any logic that would have to be duplicated in the second client is a layer leak",
      "The sprint-merge PRD (2026-02-25) merging Sprint into Coldwine should result in more kernel-read rendering, not more TUI-layer state machines"
    ],
    "task_context": "Autarch is a 4-tool tabbed Bubble Tea TUI serving as Layer 3 of the Demarch platform. The vision explicitly states: apps should be pure rendering surfaces that read kernel state and submit intents to the OS. Today, Gurgeh contains arbiter logic and Coldwine contains dispatch-to-task mapping — both identified as extraction candidates in autarch-vision.md.",
    "anti_overlap": [
      "fd-ux-kernel-surface-gap covers the opposite problem: kernel capabilities not surfaced in the TUI",
      "fd-ux-cross-tool-composition covers cross-tab handoffs and signal routing between tools",
      "fd-ux-vision-delivery-gap covers high-level narrative gaps between vision doc claims and actual TUI capabilities"
    ]
  },
  {
    "name": "fd-ux-vision-delivery-gap",
    "focus": "Review the gaps between what the Autarch and Demarch vision documents promise and what the TUI actually delivers today, focusing on missing critical user journeys and feature gaps that would be invisible to a code reader",
    "persona": "A product manager doing a vision-against-reality audit. Reads vision documents as customer promises and the codebase as the current product, then catalogs the delta — not to blame but to prioritize what must ship to make the vision credible.",
    "decision_lens": "Prioritizes gaps that affect the core north-star metric (cost per landable change across autonomy, quality, token efficiency) and gaps that would be immediately apparent to a user who read the vision before trying the product. Deprioritizes style/polish issues.",
    "review_areas": [
      "Audit the 'Autarch status tool' vision section (autarch-vision.md:191-198, 244-249) against the Sprint tab and Bigend: the vision defines four views (what's running, dispatch state, event log, token/budget) — which of these are actually rendered today and which are absent or placeholder?",
      "Check whether the Demarch north-star metric 'cost per landable change' is surfaced anywhere in the TUI — if token budget and run cost are captured by Intercore, is there a view that helps users understand the efficiency axis of the three-axis metric?",
      "Review the 'swappable toolset' and 'reference implementation' claims (vision.md:59-61): does the current TUI architecture actually support being replaced by an alternative UI client, or are there hardcoded dependencies (Intermute-specific types, autarch.Client concrete types) that would require forking rather than re-implementing?",
      "Identify capabilities described in FLOWS.md as existing (e.g., RunTargetedScan, ArbiterView coordinator wiring, targeted research brief → Pollard flow) that the oracle review found to be no-ops or disconnected — these are documented features that the TUI claims but does not deliver",
      "Assess the 'Bigend as multi-project mission control' vision: autarch-vision.md:103 and FLOWS.md describe cross-project monitoring, but bigend.go shows a single-project tasks+sessions view — is multi-project aggregation implemented, partially implemented, or entirely absent?",
      "Review the error visibility gap identified in the oracle review: Start() drops Intermute errors, scan/research paths swallow errors — does the user ever see actionable error states, or does every failure mode degrade silently to empty data?"
    ],
    "success_hints": [
      "A user who reads autarch-vision.md and then launches the TUI should be able to find the features described in the vision's 'Key user journeys' section without needing to read source code",
      "Silent failure modes (swallowed errors, no-op stubs, orphaned states) should be treated as P1 vision gaps because they degrade the autonomy axis of cost-per-landable-change"
    ],
    "task_context": "Autarch is a 4-tool tabbed Bubble Tea TUI serving as Layer 3 of the Demarch autonomous software development agency platform. The vision documents (autarch-vision.md, vision.md, FLOWS.md, AGENTS.md) describe the target state; the codebase represents current delivery. The Demarch north star is cost per landable change across autonomy, quality, and token efficiency.",
    "anti_overlap": [
      "fd-ux-onboarding-friction covers the onboarding wizard flow specifically, not the broader vision-vs-reality gap",
      "fd-ux-agency-layer-leak covers the architectural layer violation problem, not the feature completeness gap",
      "fd-ux-kernel-surface-gap covers specifically the kernel/OS capability surfacing problem, not the general vision gap"
    ]
  }
]
```

---

## Design Rationale

### Why these five agents

The five focus areas map directly to the five review dimensions in the task brief:

| Agent | Task Brief Dimension |
|---|---|
| fd-ux-onboarding-friction | (1) UX friction in the onboarding flow |
| fd-ux-cross-tool-composition | (3) whether the four tools compose into a coherent product experience |
| fd-ux-kernel-surface-gap | (4) where the TUI fails to make kernel/OS capabilities accessible |
| fd-ux-agency-layer-leak | (2) tab switching / cross-tool navigation + layer violations |
| fd-ux-vision-delivery-gap | (5) gaps between vision docs and what the TUI actually delivers |

Note: dimension (2) "tab switching and cross-tool navigation" is split between
fd-ux-cross-tool-composition (the handoff UX) and fd-ux-agency-layer-leak (the architectural
coupling that makes clean handoffs impossible). This is intentional — the navigation friction
has two distinct root causes that require different reviewers.

### Key file references for agents

- `internal/tui/unified_app.go` — tab switching, palette, onboarding shell wiring
- `internal/tui/onboarding.go` — onboarding state machine
- `internal/tui/palette.go` — command palette, command injection model
- `internal/tui/tabs.go` — tab bar rendering, Next/Prev navigation
- `internal/tui/views/bigend.go` — Bigend UX, kernel client wiring
- `internal/tui/views/gurgeh.go` — Gurgeh UX, handoff emit point
- `internal/tui/views/coldwine.go` — Coldwine UX, dispatch→task mapping
- `internal/tui/views/pollard.go` — Pollard UX, hardcoded hunter set
- `internal/tui/views/sprint_view.go` — Sprint/kernel rendering surface
- `docs/autarch-vision.md` — canonical vision with layer model
- `docs/vision.md` — write-intent model, swappability claim
- `docs/FLOWS.md` — cross-tool handoff documentation
- `docs/oracle-architecture-review-2026-02-01.md` — prior review findings
- `docs/prds/2026-02-25-merge-sprint-into-coldwine.md` — pending Sprint merge
