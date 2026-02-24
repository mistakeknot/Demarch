# UX and Product Review: NTM — Competitive Analysis for Autarch/Demarch

**Reviewer:** Flux-drive User & Product Reviewer
**Date:** 2026-02-22
**Subject:** NTM (Named Tmux Manager) at `/home/mk/projects/Demarch/research/ntm`
**Purpose:** Competitive analysis for Autarch TUI apps (Bigend, Gurgeh, Coldwine, Pollard) and broader Demarch platform design

---

## Primary User and Job-to-Be-Done

NTM's primary user is an individual developer or researcher who runs multiple AI coding agents simultaneously and needs to coordinate them without losing context or breaking flow. The job is: spawn, direct, observe, and recover a fleet of AI agents across a tmux session with minimal friction. The user is comfortable in a terminal, tolerates configuration files, but does not want to write orchestration scripts by hand.

This differs from Demarch's primary user, who is likely an agency operator or team using Demarch as the platform layer under their own workflows. Autarch surfaces are more likely to be used by an agent overseer or human reviewer checking on autonomous work-in-progress, rather than someone typing individual prompts. This distinction is critical for all downstream design decisions.

---

## 1. Multi-Agent Orchestration UX

### What NTM Does

NTM's mental model is intentionally tmux-native. Sessions are tmux sessions. Agents are panes. Pane names encode agent type and index: `myproject__cc_1`, `myproject__cod_2`. This creates a greppable, stable identifier space that works across SSH, scripts, and the TUI without additional abstraction.

The spawn interface is declarative at the CLI level:

```bash
ntm spawn myproject --cc=3 --cod=2 --gmi=1
```

This single command creates the tmux session, tiles panes, names them, and starts each agent. The `swarm` package (`/internal/swarm/`) handles staggered pane creation (300ms delay between panes) to avoid rate-limiting the tmux server — a production-learned detail that reveals real operational experience.

Multi-session labels allow running multiple swarms against the same project directory:

```bash
ntm spawn myproject --label frontend --cc=3
ntm spawn myproject --label backend --cc=2
```

This is honest about the coordination mechanism: agents communicate via Agent Mail (a message-passing layer), not shared state. The label is purely organizational.

### UX Strengths to Leverage

**Stable, typed pane IDs as first-class identifiers.** Every downstream system — health checks, dashboard, robot API, ensemble assignment — keys off pane IDs. Demarch's Autarch should establish an equally stable naming convention for agent panes or process slots. Intermux already monitors tmux, but does it expose a stable pane ID that Autarch can key routing, health, and history against? If not, NTM's naming approach is worth adopting.

**Stagger delay as a first-class config concern.** NTM exposes `StaggerDelay` in `SessionOrchestrator`. This is evidence that naive parallel spawning fails in practice. Autarch should not assume agents can be started simultaneously.

**One command, full environment.** `ntm quick myproject --template=go` creates the directory, git repo, VSCode config, Claude config, and spawns agents. The user's first success is in one command. Autarch's onboarding flow should target this level of completeness. Currently Demarch's setup requires multiple steps across Clavain, intermux, and interlock — an obvious gap.

### UX Weaknesses to Avoid

**Tmux coupling is a liability.** The entire system depends on tmux being installed and on the PATH. The robot mode, dashboard, approval flow, and ensemble all break without tmux. NTM acknowledges this (`tmux.IsInstalled()` gates most features gracefully) but the conceptual architecture is tmux-first. Demarch, building for a broader audience including potential web clients and remote operators, should keep the process/session abstraction decoupled from the transport layer. Intercore's kernel is the right place for this — tmux should be one possible backend, not the foundation.

**Session naming is a global namespace.** NTM uses tmux session names as the primary key. Two projects with the same name on the same machine collide. Labels partially address this but the problem is structural. Demarch should establish per-project isolation earlier in the design.

---

## 2. Command Palette — `/internal/palette/model.go`, `/internal/palette/selector.go`

### What NTM Does

The palette is a Bubble Tea model with five phases: Command selection, Target selection, Confirm, XF search, and XF results. This phased flow is the most important UX pattern NTM demonstrates.

The data structures reveal the design intent:

- `filtered []config.PaletteCmd` — commands filtered by the live text search
- `visualOrder []int` — maps visual position to slice index, because commands are grouped by category, not sorted by relevance alone
- `recents []string`, `paletteState config.PaletteState` — persisted recent commands and pin/favorite state, stored per-session
- `paneCounts paneCounts` — async-fetched count of each agent type, used to populate the target selector (prevents sending to agents that don't exist)
- `xfResults []tools.XFSearchResult` — cross-file search results that can be injected into prompts

Key bindings:
- `↑/↓` and `j/k` (vim-style) for navigation
- `1-9` for quick select
- `Ctrl+P` to pin, `Ctrl+F` to favorite
- `Ctrl+K` to switch to XF cross-file search mode
- `?` / `F1` for help overlay
- `Esc` to go back between phases (not quit)
- `q` / `Ctrl+C` to quit entirely

The five layout tiers (narrow/split/wide/ultra from the `layout.Tier` type) mean the palette adapts to terminal width. Preview pane shows prompt text and target metadata only in split/wide/ultra layouts.

The target selector (TargetAll, TargetClaude, TargetCodex, TargetGemini) is a major safety feature: before sending, the user must explicitly confirm or change the target. This creates a clear moment of intent before a potentially expensive or irreversible broadcast.

The `command_palette.md` file reveals that the palette is **user-configurable via a markdown file with a defined format** — categories, keys, and prompt text. The format is:

```
## Category Name
### command_key | Display Label
The prompt text
```

This is elegant: prompts are documentation, stored in version-controlled text, editable without touching Go code.

### UX Strengths to Leverage

**Phase-based flow as confirmation architecture.** The palette forces the user through Command → Target → Confirm before anything is sent. This is exactly the right pattern for any broadcast action in Autarch. Bigend or Gurgeh should have equivalent confirmation phases for any action that touches multiple agents simultaneously.

**User-defined prompts as markdown.** The palette's command format is discoverable (read the file, understand the format, add a command). Autarch could adopt a similar convention for Clavain's skill prompts or Autarch's action library.

**Recents and pinning.** Pinning commands that are used repeatedly reduces the search burden for the most common workflows. This is worth building into Autarch's action dispatch from the start — not as a future enhancement.

**XF search integration.** The palette's Ctrl+K switch to cross-file search mode and injection into the prompt is a power-user feature that turns the palette into a context-builder, not just a prompt-sender. Autarch should consider an equivalent: allow attaching file/symbol context to any action before dispatch.

**Live pane count in target selector.** The palette fetches actual pane counts asynchronously and shows them in the target selector. Sending to "Claude (3)" is safer than sending to "Claude" with no indication of how many panes will receive it. Autarch's broadcast actions should show recipient counts before confirmation.

### UX Weaknesses to Avoid

**Ctrl+F conflicts.** `Ctrl+F` is bound to "favorite" in the palette. In many terminal emulators (especially when running inside tmux), `Ctrl+F` triggers tmux prefix sequences, find-in-page, or forward-word shortcuts. This is a known terminal keyboard conflict. Demarch should audit all key bindings against the tmux prefix key (default `Ctrl+B`), common SSH terminal mappings, and VS Code terminal behavior before finalizing Autarch's keymap.

**Ctrl+P conflict.** `Ctrl+P` is bound to "pin" in the palette, but is also the default prefix for many IDE command palettes and a common readline shortcut for previous history. Same audit recommendation.

**Phase navigation is not immediately obvious.** A new user launching `ntm palette` for the first time sees a command list but may not realize they need to press Enter to proceed to target selection, then Enter again to confirm. The `?` help overlay exists but requires the user to know to press it. Progressive disclosure here is weak — the current phase is not labeled prominently enough to guide a first-time user.

---

## 3. Robot Mode — `/internal/robot/`

### What NTM Does

Robot mode is an automation-first output contract: every `--robot-*` flag writes JSON to stdout and diagnostics to stderr. Exit code 0 means success; non-zero means failure. This is a clean API contract for scripting and agent-to-agent communication.

The schema system (`/internal/robot/schema.go`) exposes the complete JSON Schema for every robot output type via `--robot-schema=<type>` or `--robot-schema=all`. This allows consumers (including agents) to introspect the output format before parsing it.

The `RobotResponse` base type (inferred from usage: `NewRobotResponse(true)`, `NewErrorResponse(err, ErrCodeX, hint)`) provides a consistent envelope with:
- `ok bool` — success flag
- Error code constants (`ErrCodeDependencyMissing`, `ErrCodeInternalError`, `ErrCodeInvalidFlag`)
- Human-readable action hints on errors

The `Get*` / `Print*` function pairs throughout `robot.go` are architecturally clean: `GetCASSStatus()` returns the struct, `PrintCASSStatus()` is a thin wrapper that calls `encodeJSON()`. This enables CLI/REST parity — the same data can be served over HTTP without duplicating logic. NTM's web API plans (the `PLAN_TO_ADD_WEB_UI_AND_REST_AND_WEBSOCKET_API_LAYERS_TO_NTM__*.md` files in the root) rely on this pattern.

The `DashboardOutput` in `robot_dashboard.go` provides a fleet-level view for AI orchestrators: sessions, agents per session, system info, beads summary, progress, alerts, conflicts, file changes, and agent mail state — all in a single JSON document.

### UX Strengths to Leverage

**stdout/stderr split as a user contract.** This is the most transferable pattern in the entire codebase. Demarch's robot/machine-readable interface (whatever it becomes) must commit to this split. Mixing human-readable text into stdout breaks every downstream consumer silently.

**Error envelopes with actionable hints.** `NewErrorResponse(err, ErrCodeX, "Install cass to enable search")` is a great pattern. The hint tells the caller what to do, not just what went wrong. Autarch's error surfaces (both TUI and API) should use this pattern.

**Schema introspection as first-class.** `--robot-schema=all` is forward-looking: any tool that consumes ntm can discover the contract at runtime. Demarch's Intercore kernel or any REST surface for Autarch should expose equivalent schema endpoints.

**Fleet dashboard as a single JSON document.** The `DashboardOutput` struct is a polling target for an orchestrator — one call gives the entire system state. For Demarch's Autarch, this is the pattern for the "status heartbeat" that Clavain or any external coordinator would poll.

### UX Weaknesses to Avoid

**Robot mode is only a flag namespace, not a subcommand.** Every robot operation is accessed via `--robot-<operation>`. This creates a flat namespace that will eventually conflict or become unwieldy as more operations are added. Demarch should consider a `ntm robot <subcommand>` structure for its equivalent interface.

**No authentication or rate limiting on robot endpoints.** NTM robot mode is designed for local trusted execution. If Demarch exposes equivalent functionality over a REST or WebSocket layer (which the web plans suggest), authentication must be designed in from the start, not retrofitted.

---

## 4. Dashboard and Monitoring — `/internal/tui/dashboard/`

### What NTM Does

The dashboard is a Bubble Tea model with aggressive adaptive refresh architecture. Key design decisions:

**Per-subsystem refresh sequencing.** Every data source has a `refreshSource` enum entry and a corresponding `uint64` generation counter (`refreshSeq`, `lastUpdated`). Async responses carry their generation number, and stale responses (from a previous generation) are discarded. This prevents the TUI from regressing to older state when a slow fetch completes after a faster retry.

**Fetch state tracking.** `fetchingSession`, `fetchingBeads`, `fetchingAlerts`, etc. are boolean flags that prevent pile-up: if a fetch is already in-flight, a new one is not started. This is more sophisticated than a simple timer and prevents the classic "thundering herd on slow endpoints" TUI failure mode.

**Adaptive tick rate.** `StateActive` vs `StateIdle` activity states reduce the animation tick rate when the user is not interacting. This is a CPU/battery consideration that many TUIs ignore.

**Responsive layout with five breakpoints.** Thresholds at 60, 100, 140, 180 columns drive a layout mode from LayoutMobile to LayoutUltraWide. Column visibility is progressive: status column appears at 60+, context column at 100+, model column at 140+, command column at 180+. This is the right approach for a tool that runs in both 80x24 SSH sessions and wide developer workstations.

**Fourteen panel types.** `PanelPaneList`, `PanelDetail`, `PanelBeads`, `PanelAlerts`, `PanelConflicts`, `PanelMetrics`, `PanelHistory`, `PanelSidebar`, and more. Focus rotates between panels. The dashboard is not a static status page — it is a multi-panel workspace.

**Integrated subsystems in the dashboard:** beads (work queue), agent mail (inter-agent messaging), alerts, CASS search, handoff status, checkpoint status, file conflicts, DCG (dangerous command guard), RCH (rate/cost health), and process_triage health states. This is a comprehensive monitoring surface.

### UX Strengths to Leverage

**Generation-counter based staleness rejection.** This pattern eliminates an entire class of async TUI bugs. Autarch's dashboards should adopt this from the start. The pattern is: every async command gets a monotonically increasing generation number at dispatch time; the handler discards any response whose generation does not match the current expected generation.

**Per-subsystem refresh intervals.** Different data has different staleness tolerance: pane status needs to refresh every few seconds, cost estimates can refresh every minute. NTM's architecture supports this explicitly. Autarch should not use a single global refresh timer.

**Progressive column disclosure.** Showing fewer columns on narrow terminals, not truncating or wrapping them, is the correct terminal UX pattern. Autarch's TUI components should implement the same progressive column hiding.

**Fetch-in-flight guards.** Never starting a second fetch when one is already running prevents pile-up. This is not optional — it is required for any TUI that has multiple async data sources.

**Context and handoff status in the dashboard.** The dashboard shows `HandoffUpdateMsg` with `Goal`, `Now`, `Age`, and `Status` fields from the handoff YAML. This gives the user a persistent "where are we and what's next" panel that survives across dashboard sessions. Autarch's monitoring surface should include equivalent continuity context.

### UX Weaknesses to Avoid

**Dashboard as a separate command, not embedded in the main interface.** Users must run `ntm dashboard myproject` to get the visual overview, then return to the normal tmux panes to see actual agent output. There is no single pane that shows both. This creates a context-switching cost that Autarch should avoid — Autarch's TUI should integrate the monitoring and the action surfaces.

**Fourteen panels is too many without a clear navigation model.** The `PanelID` enum has eight named panels plus a count. Navigating between them requires knowing what panels exist. NTM addresses this with `?` overlays, but the discoverability surface is thin. Autarch should design panel navigation as an explicit information architecture, not a list of IDs with tab rotation.

---

## 5. Ensemble Workflows — `/internal/ensemble/`

### What NTM Does

The ensemble is NTM's most conceptually ambitious feature. It is behind a build tag (`ensemble_experimental`) but the non-experimental parts (types, strategies, modes, presets, synthesizer) are stable.

The architecture has three stages:
1. Intake — gather context about the question/session
2. Mode Run — spawn agents, assign reasoning modes, inject prompts, collect outputs
3. Synthesis — aggregate outputs using a configured strategy

**80 reasoning modes** organized into 12 categories (A-L): Formal, Ampliative, Uncertainty, Vagueness, Change, Causal, Practical, Strategic, Dialectical, Modal, Domain, Meta. Each mode has an ID, code (e.g., A1), tier (core/advanced/experimental), short description, full description, expected outputs, best-use cases, and failure modes. The failure modes field is a standout — each mode documents where it goes wrong, not just where it works.

**9 built-in ensemble presets** include: project-diagnosis, idea-forge, spec-critique, safety-risk, architecture-review, tech-debt-triage, bug-hunt, root-cause-analysis, and debate. Each preset specifies which modes to use and which synthesis strategy to apply.

**6 synthesis strategies:** manual (mechanical merge), adversarial (challenge/defense), consensus (find agreement), creative (recombine into novel insights), analytical (systematic decomposition), deliberative (tradeoff weighing), and prioritized.

The synthesizer streams output in typed chunks: `status`, `finding`, `risk`, `recommendation`, `question`, `explanation`, `complete`. This streaming model allows the TUI to display synthesis progress in real-time.

Mode assignment uses three strategies: round-robin, affinity (match agent capability to mode type), and category (group modes by category across agents). Mode assignment is managed by `EnsembleManager.SpawnEnsemble()` in the `swarm` integration.

Budget controls: `MaxTokensPerMode`, `MaxTotalTokens`, `TimeoutPerMode`, `TotalTimeout`. These are not estimates — they are enforcement limits.

### UX Strengths to Leverage

**Reasoning mode as a UX primitive.** NTM makes "reasoning mode" a named, documentable, discoverable thing with a code (A1), a description, best-use cases, and failure modes. This is superior to "send a prompt" or "pick an agent." Demarch's interflux (multi-agent review engine) and intersynth (verdict aggregation) would benefit from adopting a similar named-mode vocabulary. The FLUX podcast's interlens plugin already goes in this direction with cognitive lenses — that work should align with or connect to this taxonomy.

**Ensemble presets as curated workflows.** A user can say `ntm ensemble spawn myproject --preset architecture-review` and get a specific multi-agent workflow without understanding the underlying mode composition. This is the right UX for power features: provide named, opinionated presets for common cases, and expose the composition API for advanced users. Autarch's action library should offer equivalent "recipe" presets for common development workflows.

**Failure modes as first-class documentation.** Every reasoning mode in NTM documents its failure modes explicitly. This is worth adopting as a convention in Demarch's AGENTS.md descriptions for each interverse plugin and Autarch action.

**Budget enforcement, not just guidance.** Token budgets are enforced limits on mode runs, not soft suggestions. This is necessary for managing cost in a multi-agent system. Autarch should build cost controls into the action dispatch layer.

**Streaming synthesis output.** Chunk types (finding, risk, recommendation, question) allow the dashboard to render synthesis results progressively. Autarch's synthesis views should not wait for full completion before showing results.

### UX Weaknesses to Avoid

**Ensemble is behind an experimental build flag.** The most distinctive and differentiating capability in NTM is not available in standard builds. Users who install NTM from the recommended path do not get ensemble. This is a discovery failure: the feature that most justifies the system's complexity is hidden. Demarch should not gate its most valuable orchestration primitives behind build flags or undiscoverable configuration.

**Mode assignment is automatic but opaque.** When an ensemble spawns agents and assigns modes via round-robin or affinity, the user cannot easily see which pane got which mode without querying the ensemble status. The TUI dashboard shows `EnsembleModesDataMsg` but navigating to it requires knowing to look. Assignment should be visible immediately at spawn time.

**The 80-mode taxonomy is powerful but overwhelming for first exposure.** Core tier has approximately 28 modes; advanced adds 50+ more. A user encountering `ntm modes list` for the first time will not know where to start. The preset system partially solves this (use a preset, not individual modes), but the path from "I want to review this architecture" to `--preset architecture-review` requires the user to already know that preset exists. Demarch should invest in better decision-tree or recommendation UI — "what are you trying to do?" before "which mode?"

---

## 6. Safety and Approval UX — `/internal/approval/`, `/internal/safety/redaction/`

### What NTM Does

The approval engine is a formal workflow with the following states: pending, approved, denied, expired. Key parameters:
- `Action` — what is being approved (e.g., "force_release")
- `Resource` — what is being acted on
- `RequestedBy` — which agent or user initiated the request
- `RequiresSLB` — two-person rule (the approver cannot be the same identity as the requester)
- `ExpiresIn` — approval requests expire (default 24 hours)

The `WaitForApproval()` method blocks with a timeout and uses a channel-based waiter map, so multiple goroutines can wait on the same approval ID without polling.

SLB (two-person rule) is enforced in `Approve()`: if `RequiresSLB` is true and `approverID == approval.RequestedBy`, the approval is rejected with "SLB violation: approver cannot be the same as requester." An authorized approver list is also configurable.

Notifications are sent on request creation and decision (via the `notify.Notifier`), with a best-effort policy: notification failures do not block the approval operation.

The redaction engine (`/internal/redaction/`) has four modes: off, warn, redact, block. It scans for sensitive content (likely secrets, credentials, PII) in agent outputs and can prevent that content from being logged, displayed, or transmitted.

### UX Strengths to Leverage

**Approval as a workflow, not a prompt.** NTM's approval engine is a proper state machine with IDs, expiry, audit trail, and event emission. This is the right level of formality for an agency platform handling production code changes. Demarch's human-in-the-loop design should be this rigorous, not a simple Y/N confirmation dialog.

**Two-person rule (SLB) as a named, configurable constraint.** Making SLB a first-class, named concept — not just a comment in the code — is valuable. Demarch's Autarch should expose SLB-equivalent concepts (perhaps "requires oversight" or "requires second agent review") as configurable per-action.

**Expiry on approvals.** Approvals that are not acted on within a time window expire automatically. This prevents the system from blocking indefinitely on abandoned requests. Autarch should adopt the same pattern for any human-in-the-loop gate.

**Redaction modes with allowlists.** The redaction engine's four modes give operators control over the sensitivity of output handling. This is necessary for any platform that handles production code, secrets, or credentials in agent context.

### UX Weaknesses to Avoid

**No UI for pending approvals in the dashboard.** The approval engine exists, the event system emits `approval.requested` events, but the dashboard model (`dashboard.go`) does not show a pending approvals panel. A user waiting for an approval decision has no ambient awareness that one is pending. Autarch must surface pending approvals as a first-class dashboard element, not an invisible background state.

**Approval identity is a string, not an authenticated principal.** `RequestedBy` and the approver are arbitrary strings. In a shared or multi-user context, this is trivially spoofable. Demarch building toward an agency platform should design identity and authentication into the approval model from the start.

---

## 7. Handoff and Recovery — `/internal/handoff/`, `/internal/checkpoint/`

### What NTM Does

The handoff is a YAML document representing session context at ~400 tokens (versus ~2000 for equivalent markdown). Required fields are `goal` (what this session accomplished) and `now` (what the next session should do first). Optional fields include:
- `done_this_session` — task records with associated files
- `blockers`, `questions`, `decisions`, `findings`
- `worked`, `failed` — what patterns succeeded and failed
- `next` — prioritized next steps
- `files` — created/modified/deleted file tracking
- `active_beads`, `agent_mail_threads`, `cm_memories` — integration references
- Token context at handoff time (`tokens_used`, `tokens_max`, `tokens_pct`)
- `reservation_transfer` — structured instructions for transferring file locks to the next agent

The `Generator` creates handoffs from agent output text by analyzing it for accomplishments, next steps, blockers, tasks, and decisions. It also enriches handoffs with git state.

The `transfer.go` module handles reservation transfers between agents: release old reservations, reserve for new agent, roll back on conflicts with a grace period. This is approximately atomic file lock transfer, which prevents two agents from editing the same file simultaneously during a handoff.

The handoff status is surfaced in the dashboard as a `HandoffUpdateMsg` with `Goal`, `Now`, `Age`, `Path`, and `Status` fields.

### UX Strengths to Leverage

**Handoff as a compact, structured, versioned document.** NTM's `HandoffVersion = "1.0"` with explicit forward-compatibility planning is the right approach. Demarch's Clavain already uses handoffs (likely via interline and interphase), but the structure should be as explicit as NTM's. The `goal`/`now` fields as required fields is a design constraint worth enforcing — a handoff without a clear "now" is not a valid handoff.

**Token budget at handoff time.** Recording `tokens_used`, `tokens_max`, `tokens_pct` at handoff time lets the next session know how close the previous agent was to context limits. This is critical information for continuity — a session handed off at 90% context needs a different strategy than one at 30%. Autarch's continuity model should include this signal.

**Reservation transfer as an atomic operation.** The `TransferReservations` function with rollback-on-conflict is a sophisticated and necessary primitive for multi-agent systems working on shared files. Interlock in Demarch handles file coordination, but handoff integration — transferring locks at session boundary — may be missing or implicit.

**Outcome taxonomy.** NTM's handoff has a defined outcome vocabulary: `SUCCEEDED`, `PARTIAL_PLUS`, `PARTIAL_MINUS`, `FAILED`. This is more honest than a binary success/failure. Autarch's session completion states should use a similar graduated vocabulary.

**Generator that analyzes agent output.** The `GenerateFromOutput()` function extracts handoff fields from unstructured agent text. This means agents do not need to follow a strict output protocol to produce a valid handoff — the generator does the extraction. Demarch's handoff generation should have an equivalent fallback path.

### UX Weaknesses to Avoid

**Recovery is not clearly surfaced.** NTM has a `recovery` package (listed in `internal/`) but it is not prominently featured in the README or command interface. A user whose agent session dies due to context limit or network failure must know to look for recovery tools. Autarch should make recovery the default first-action after any abnormal session termination, not an opt-in command.

**Handoff age is shown but not acted upon.** The dashboard shows handoff age (`HandoffUpdateMsg.Age`), but there is no alert or action triggered by a stale handoff (e.g., "handoff is 4 hours old — the session may have been abandoned"). Autarch should define a staleness threshold and prompt the user with recovery options when exceeded.

---

## 8. Cross-Cutting UX Findings

### Terminal Compatibility

NTM uses Nerd Font icons with explicit ASCII fallbacks (`icons` package, `IconSet` type in the palette and dashboard). This is the correct approach. Any Autarch TUI component should default to Unicode-safe symbols and treat Nerd Font icons as an opt-in enhancement.

NTM's layout responds at 60, 100, 140, 180 columns. The 60-column mobile threshold is the minimum for any meaningful display. Autarch must test all TUI components at 80x24, which remains the effective minimum for SSH and CI environments.

### Keyboard Navigation Model

NTM uses vim-style keys (`j/k`, `g/G`) alongside arrow keys throughout. This is consistent and correct for a power-user terminal tool. The numeric quick-select (`1-9`) for both commands and target selection reduces navigation time for frequently-used items. Autarch should adopt the same dual-model: arrow keys for discoverability, vim keys for efficiency.

### Tutorial and Onboarding

NTM has a built-in interactive tutorial (`ntm tutorial`) with an `--skip` flag for accessibility/animation-off environments. This is a strong onboarding primitive. Autarch's Bigend or Gurgeh interface should include equivalent guided onboarding that walks through the multi-agent workflow, not just a README.

### Dependency Check

`ntm deps -v` checks all required tools and reports versions. Autarch should expose an equivalent `bd doctor` or Autarch-specific dependency check as a first-run health gate.

### Self-Update

`ntm upgrade` with `--check`, `--yes`, and `--force` flags is a well-designed self-update UX. Autarch's plugin/app update flow should follow the same pattern.

---

## 9. Product Validation

### What NTM Gets Right as a Product

NTM correctly identifies that the painful part of multi-agent development is not spawning agents — it is maintaining orientation across agents, recovering from context limits, and coordinating work on shared files without conflicts. The handoff, checkpoint, approval, and reservation transfer systems all address real operational pain.

The robot mode / REST parity design (`Get*` / `Print*` function split) is forward-looking. NTM is designed to grow into a headless API while keeping CLI parity. This is the right architecture for a platform tool.

The ensemble reasoning mode taxonomy (80 modes, 12 categories, 9 presets) is ambitious and substantive. It is not a novelty feature — it represents a real attempt to make AI reasoning strategies legible and composable. This is worth studying carefully for Demarch's intersynth and interflux design.

### What NTM Reveals About Autarch's Gaps

1. **Autarch has no equivalent to `ntm tutorial`.** New-user onboarding is a missing surface in the current Autarch design. The first-run experience needs explicit design work.

2. **Autarch has no equivalent to `ntm deps -v`.** Dependency health is a common support problem. A first-run health check prevents an entire category of user confusion.

3. **The approval workflow exists in NTM but has no TUI visibility.** Autarch should not make the same mistake. Pending approvals must be a first-class dashboard panel.

4. **Autarch's session naming convention is not documented or standardized.** NTM's `{project}__{type}_{index}` convention is explicit and machine-parseable. Autarch and intermux need an equivalent stable convention.

5. **Autarch's broadcast action model is not confirmed.** Does Autarch have an equivalent to `ntm send --all`? If the agent supervision TUIs (Bigend, Gurgeh) do not have broadcast actions, they are missing a core orchestration primitive.

6. **Handoff-to-recovery integration.** NTM shows the goal/now from the handoff in the dashboard. Autarch's Bigend or Coldwine should show the same — the current session's stated goal, the blocker if any, and the next action, all visible without leaving the TUI.

---

## 10. Patterns to Directly Adopt in Autarch

Listed by priority:

**Adopt immediately:**
- `stdout = JSON, stderr = diagnostics, exit code = contract` for any robot/API interface
- Generation counters on all async TUI data fetches
- Per-subsystem refresh intervals with in-flight guards
- Phase-based confirmation flow for all broadcast actions (Select → Target → Confirm)
- Handoff `goal`/`now` as required fields enforced at the type level

**Adopt in next design iteration:**
- 5-breakpoint responsive layout (60/100/140/180 column thresholds with progressive column hide)
- Stable pane/agent ID convention (`{session}__{type}_{index}`)
- Named ensemble presets as the primary UX for multi-agent workflows (not raw mode selection)
- Streaming synthesis output with typed chunks (finding, risk, recommendation)
- Reservation transfer as a handoff primitive (interlock integration at session boundary)

**Study before committing:**
- The 80-mode reasoning taxonomy — align with or connect to interlens before duplicating
- Approval SLB enforcement — validate whether Demarch's user base requires two-person rules
- The palette's markdown-format command definition — evaluate against Autarch's action registry design

---

## Files Referenced

- `/home/mk/projects/Demarch/research/ntm/cmd/ntm/main.go` — entry point
- `/home/mk/projects/Demarch/research/ntm/internal/palette/model.go` — palette UX model (2017 lines)
- `/home/mk/projects/Demarch/research/ntm/internal/palette/selector.go` — session selector component
- `/home/mk/projects/Demarch/research/ntm/internal/robot/robot.go` — robot mode implementation
- `/home/mk/projects/Demarch/research/ntm/internal/robot/schema.go` — JSON Schema generation
- `/home/mk/projects/Demarch/research/ntm/internal/robot/robot_dashboard.go` — fleet dashboard output
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/types.go` — mode/category type system
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/modes.go` — 80-mode taxonomy
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/ensembles.go` — 9 built-in presets
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/strategy.go` — 6 synthesis strategies
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/synthesizer.go` — streaming synthesis
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/manager.go` — ensemble lifecycle
- `/home/mk/projects/Demarch/research/ntm/internal/ensemble/state.go` — SQLite persistence
- `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/dashboard.go` — dashboard model
- `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/layout.go` — responsive layout
- `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/commands.go` — async commands
- `/home/mk/projects/Demarch/research/ntm/internal/approval/engine.go` — approval workflow
- `/home/mk/projects/Demarch/research/ntm/internal/handoff/types.go` — handoff document structure
- `/home/mk/projects/Demarch/research/ntm/internal/handoff/generator.go` — output-to-handoff extraction
- `/home/mk/projects/Demarch/research/ntm/internal/handoff/transfer.go` — reservation transfer
- `/home/mk/projects/Demarch/research/ntm/internal/redaction/redaction.go` — output redaction
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/orchestrator.go` — session orchestration
- `/home/mk/projects/Demarch/research/ntm/command_palette.md` — user-configurable palette commands
- `/home/mk/projects/Demarch/research/ntm/README.md` — product overview
