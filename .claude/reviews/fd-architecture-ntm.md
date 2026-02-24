# Architecture Review: ntm — Multi-Agent Tmux Orchestration

**Reviewer:** Flux-drive Architecture & Design Reviewer
**Date:** 2026-02-22
**Target:** `/home/mk/projects/Demarch/research/ntm` (Go CLI/TUI, 1,442 files, ~256k LOC)
**Purpose:** Competitive analysis for Demarch/Autarch. Identify patterns worth adopting,
patterns to avoid, and structural observations relevant to building similar Go/Bubble Tea
multi-agent TUI tooling.

> This review operates in codebase-aware mode for ntm (using its AGENTS.md), and in
> codebase-aware mode for Demarch (using the Demarch CLAUDE.md). Recommendations are
> grounded in Demarch's 3-layer (L1/L2/L3) and 5-pillar (Intercore, Clavain, Interverse,
> Autarch, Interspect) architecture.

---

## 1. What ntm Actually Is

ntm is a tmux session manager with a multi-agent orchestration layer bolted on top of it.
Its primary loop is: spawn tmux sessions with agent processes in panes, send prompts to
those panes via `tmux send-keys`, capture output by reading pane scrollback, detect agent
state from terminal output patterns, and coordinate work across panes using a mix of
Agent Mail (MCP-based async messaging) and direct prompt injection.

The codebase explicitly acknowledges in its design doc that it is currently "blind" after
sending a prompt (sees itself as infrastructure, not intelligence), and the high-priority
work is making it smarter about routing, state detection, and synthesis.

Stack: Cobra CLI + Bubble Tea TUI + SQLite state + chi HTTP router + gorilla WebSocket +
SQLite-backed event bus + TOML config. All pure Go.

---

## 2. Module Decomposition

### 2.1 Package Topology

ntm has roughly 80 `internal/` packages. They fall into identifiable tiers:

**Tier 1 — Core infrastructure (stable, depended on by nearly everything):**
- `internal/tmux` — Process-level tmux wrapper; Client struct, binary resolution,
  session/pane CRUD, capture, send-keys.
- `internal/config` — TOML config loading; flat `Config` struct with deeply nested
  sub-configs for every subsystem.
- `internal/state` — SQLite-backed store with versioned migrations (6 so far);
  WAL mode, mutex-serialized writes.
- `internal/events` — Pub/sub EventBus (ring-buffer history, semaphore-capped goroutine
  dispatch); global `DefaultBus` singleton plus per-instance bus.
- `internal/agent` — Agent type enum (cc, cod, gmi, user, ollama, cursor, windsurf, aider)
  with parser for detecting agent state from pane output.
- `internal/kernel` — Thin command registry: `Command` metadata type (name, schema refs,
  REST binding, safety level, emitted events), `Registry` with handler dispatch.
  Purely declarative; no business logic.
- `internal/util` — Shared utilities.

**Tier 2 — Orchestration domain:**
- `internal/swarm` — Plan-then-execute session creation. `SessionOrchestrator` creates
  tmux sessions from a `SwarmPlan`. `AgentLauncher` sends agent start commands to panes.
  `PromptInjector` injects initial prompts. `AutoRespawner` detects agent crashes/limits
  and restarts. `AccountRotator` cycles API accounts on limit-hit.
- `internal/coordinator` — `SessionCoordinator`: active per-session monitor that polls
  agent state, maintains `AgentState` map, detects conflicts, routes work, and sends
  digests via Agent Mail.
- `internal/ensemble` — The highest-level orchestration abstraction: 80-mode reasoning
  taxonomy (12 category schema A-L), `EnsemblePreset` definitions (9 built-in), `Synthesizer`
  with 11 selectable synthesis strategies, `EnsembleManager` that wires swarm, launcher,
  and injector together. Large volume: 43k LOC in this package alone.
- `internal/supervisor` — Daemon lifecycle manager (start/stop/health/restart) for
  long-running helper processes (cm, bd, am). PID-file based ownership; HTTP health
  checks.
- `internal/pipeline` — Sequential multi-stage agent pipelines: route to pane by type,
  inject prompt, wait for idle, capture output, feed to next stage.
- `internal/scheduler` — Global spawn rate limiter and priority queue. Prevents
  resource exhaustion when many panes are created simultaneously. Per-agent-type caps.
- `internal/workflow` — TOML-defined multi-agent workflow templates (ping-pong, pipeline,
  parallel, review-gate). Embedded builtins; user and project-level overrides.
- `internal/assign` — Work assignment strategies (balanced, speed, quality, dependency,
  round-robin) against a set of `Agent` structs with context usage and capability scores.
- `internal/context` — Context window monitoring: per-model token limits, pane output
  scanning, rotation triggers, handoff triggers.
- `internal/handoff` — YAML handoff format for session continuity. Compact (~400 tokens).
  Reader/writer/validator/generator/transfer.
- `internal/checkpoint` — Full session state snapshot/restore. Incremental + integrity
  checks. Separate from handoff (handoff = LLM-readable summary; checkpoint = machine-
  readable recreation state).

**Tier 3 — Delivery/surface:**
- `internal/cli` — 140+ Cobra command files. Very large: root.go alone is 4,226 lines.
  Imports kernel, robot, session, config, pipeline, plugins, events, state, tmux, startup.
- `internal/robot` — Machine-readable JSON API layer. Wraps orchestration domain
  functions with consistent JSON output structs. Explicitly maintains CLI/TUI parity
  (tui_parity.go).
- `internal/tui` — Bubble Tea TUI. Sub-packages: `dashboard/` (main BubbleTea model,
  6,716 lines), `dashboard/panels/` (23 separate panels), `components/`, `layout/`,
  `theme/`, `styles/`, `icons/`, `synthesizer/`, `terminal/`.
- `internal/serve` — chi HTTP router + WebSocket server. Exposes robot API over REST.
  Also generates OpenAPI spec from kernel registry.
- `internal/plugins` — TOML-defined custom agent types. Scan-and-load from
  `~/.config/ntm/plugins/`.
- `internal/hooks` — Git hook installation (pre-commit UBS scan integration).

### 2.2 Dependency Direction Assessment

The dependency direction is mostly sound at the boundary between delivery and domain:
- `internal/cli` does not export symbols to other internal packages (confirmed: no
  other internal package imports `internal/cli`).
- `internal/kernel` is a pure metadata/registry layer with no business logic
  dependencies — correctly sits at the foundation.
- `internal/tmux` is the leaf-level process adapter and is imported widely up the stack.

However, there are notable coupling problems:

**Problem A — `internal/dashboard` is a god consumer.** The dashboard imports 28+
internal packages directly (agentmail, alerts, bv, cass, checkpoint, clipboard, config,
context, cost, ensemble, health, history, integrations/pt, integrations/rano, robot,
scanner, session, state, status, tmux, tokens, tools, tracker, tui/components,
tui/dashboard/panels, tui/icons, tui/layout, tui/styles, tui/synthesizer, tui/theme,
watcher). This is expected for a dashboard but signals that there is no stable "view
model" or data aggregation service between the data layer and the rendering layer.
The 6,716-line `dashboard.go` is directly polling the tmux layer, the state store, the
event bus, and domain packages in a single Bubble Tea model.

**Problem B — `internal/robot` is a parallel delivery layer, not a clean facade.** robot
packages import ensemble, swarm, tmux, alerts, bv, cass, config, handoff, health, recipe,
redaction, status, tools, tracker simultaneously. It is structurally equivalent to the CLI
layer but targeting JSON output. This means business logic around "how to get CASS status"
or "how to spawn an ensemble" is duplicated or scattered across `cli/ensemble.go`,
`robot/ensemble.go`, and sometimes `ensemble/manager.go`. The tui_parity.go comment is
honest: this parallelism is intentional but maintenance-costly.

**Problem C — `internal/config` is a catch-all.** The Config struct has sections for
Agents, Palette, PaletteState, Tmux, Robot, AgentMail, Integrations, Models, Alerts,
Checkpoints, Notifications, Resilience, Health, Scanner, CASS, Accounts, Rotation,
GeminiSetup, and more. Every subsystem configures itself through one root struct rather
than owning its own config type at its own package boundary.

**Problem D — `internal/ensemble` is gated behind a build tag but partially isn't.**
`pipeline.go`, `manager.go`, `dryrun.go`, and `injector.go` carry `//go:build ensemble_experimental`
but `types.go`, `modes.go`, `synthesizer.go`, `strategy.go`, and the large type taxonomy
are unconditional. This means the type system ships in all builds but the pipeline
execution paths are feature-flagged. The result is architectural ambiguity: it is unclear
whether "ensemble" is an experimental subsystem or a stable one.

---

## 3. Agent Orchestration Patterns

### 3.1 The Three-Layer Orchestration Model

ntm has three distinct orchestration layers that compose:

```
Layer 3 (Ensemble):  EnsembleManager
                     |-- defines reasoning modes (80-mode taxonomy)
                     |-- selects synthesis strategy (11 strategies)
                     |-- creates EnsembleConfig -> calls Layer 2
Layer 2 (Swarm):     SessionOrchestrator + AgentLauncher + PromptInjector
                     |-- creates tmux sessions from SwarmPlan
                     |-- launches agent processes in panes
                     |-- injects initial prompts
                     |-- AutoRespawner: crash detection + account rotation
Layer 1 (Coordinator): SessionCoordinator
                     |-- polls agent state every 5s (configurable)
                     |-- detects conflicts via AgentMail reservations
                     |-- routes work via assign strategies
                     |-- sends periodic digests to human agent
```

The swarm layer is the execution primitive. The ensemble layer is the planning primitive.
The coordinator layer is the runtime monitoring primitive. These three are cleanly separated.

### 3.2 The SwarmPlan / Allocation Pattern

`SwarmPlan` is a declarative intermediate representation: scan projects by bead count,
compute agent allocations per tier, build `SessionSpec` and `PaneSpec` lists, then hand
the plan to `SessionOrchestrator` to execute. This separation between planning and
execution is the strongest structural pattern in the codebase. It enables dry-run,
preview, and remote execution (the orchestrator accepts an SSH host).

**This is worth adopting.** Autarch's session management would benefit from a similar
`Plan` type that separates the "what should we create" computation from the "how do we
create it" execution.

### 3.3 AutoRespawner: Limit Detection + Account Rotation

`AutoRespawner` watches pane output for limit-hit patterns, then:
1. Sends Ctrl+C (soft exit) with a wait for graceful exit.
2. Falls back to hard exit (kill pane + relaunch) if soft fails.
3. Optionally calls `AccountRotator.OnLimitHit()` to rotate API credentials before
   relaunching.
4. Enforces per-pane retry caps with time-based reset.

This is the most operationally mature pattern in the codebase. It reflects real-world
Claude Code usage where context window exhaustion and account rate limits are daily events.

**Worth adopting** for Autarch's session lifecycle management.

### 3.4 Ensemble Reasoning Taxonomy

80 reasoning modes organized in 12 categories (A-L: Formal, Ampliative, Uncertainty,
Vagueness, Change, Causal, Practical, Strategic, Dialectical, Modal, Domain, Meta).
9 preset ensembles (project-diagnosis, idea-forge, spec-critique, safety-risk,
architecture-review, bug-hunt, root-cause-analysis, code-review, decision-making).
11 synthesis strategies (manual, adversarial, consensus, creative, analytical,
deliberative, prioritized, dialectical, meta-reasoning, voting, argumentation).

The taxonomy is implemented as embedded Go slices of `ReasoningMode` and `EnsemblePreset`
structs. There is no external data file — modes are code. This avoids a runtime loading
step but makes the taxonomy hard to extend without recompile. The `ModeTier` (core vs.
advanced vs. experimental) system is solid for controlling surface area.

**Partially worth adopting.** The concept of named reasoning modes that get assigned to
agent panes is directly applicable to Demarch's interflux multi-review engine. The
synthesis strategy pattern (select a strategy, let the Synthesizer compose outputs
according to that strategy's template key) maps well onto intersynth.

### 3.5 The Workflow Template System

`WorkflowTemplate` (TOML files with embedded builtins) defines coordination types:
ping-pong, pipeline, parallel, review-gate. Workflow files embed agent roles, count,
prompts, and a flow state machine (initial stage, transitions). User and project-level
overrides layer over builtins.

This is a pragmatic extensibility mechanism that does not require recompilation. It maps
directly onto what Demarch's intercraft module describes as "agent-native architecture
patterns." The key insight is that workflows are data, not code — the loader resolves
them at runtime with a clear precedence chain (project > user > builtin).

**This is worth adopting for Autarch's session template system.**

### 3.6 Assignment Strategies

`assign.Strategy` has five modes: balanced, speed, quality, dependency, round-robin.
The `Matcher` scores agents by context availability, capability affinity, and file
reservation status (via Agent Mail). Assignment is a pure function of agent list and
bead list — no side effects, highly testable.

The dependency strategy (`StrategyDependency`) respects bead blocking chains, which means
work assignment is graph-aware. This is where bv (the graph triage engine) integrates into
the routing layer.

---

## 4. TUI Architecture

### 4.1 Structure

```
internal/tui/
  dashboard/           -- Main BubbleTea Model (6,716 lines)
    layout.go          -- Width-tier responsive layout (mobile/compact/split/wide/ultrawide)
    commands.go        -- BubbleTea Cmd factories
    panels/            -- 23 panel types (each is a tea.Model + Panel interface)
  components/          -- Reusable primitives (state, scroll, progress, spinner, list, etc.)
  layout/              -- Width tier constants and TierForWidth() function
  theme/               -- Catppuccin Mocha + Latte + Nord theme structs
  styles/              -- Style tokens and breakpoints
  icons/               -- Icon sets (fancy vs. basic terminal fallback)
  synthesizer/         -- Ensemble mode selection view (modes_view.go)
  terminal/            -- Terminal capability detection
```

### 4.2 Responsive Layout System

The `layout.Tier` system is the strongest TUI-specific pattern. It defines five width
tiers: Narrow (<120), Split (120-199), Wide (200-239), Ultra (240-319), Mega (>=320).
`TierForWidthWithHysteresis()` adds a 5-column hysteresis band to prevent flickering at
tier boundaries.

`dashboard/layout.go` provides a second, partially overlapping tier system (Mobile, Compact,
Split, Wide, UltraWide) with different thresholds (60/100/140/180). This is an active
inconsistency in the codebase — two tier systems for the same concern with different
boundaries. The `layout/` package tier system is documented as the canonical one aligned
with `styles/tokens.go`, but `dashboard/layout.go` predates it and has not been unified.

**This is an anti-pattern Autarch should avoid by design.** Define one width-tier system
in one place and enforce it across all TUI surfaces.

### 4.3 Panel System

The `Panel` interface extends `tea.Model` with `Config()`, `Priority()`, `SetSize()`,
`NeedsRefresh()`, and keybinding methods. `PanelConfig` stores ID, title, priority,
refresh interval, min dimensions, collapsibility, and tier visibility hints.

This is a clean composition pattern. Each panel is independently testable (23 panel test
files exist), has its own refresh interval, and uses priority to control render order.

**Worth adopting for Autarch.** Define a `Panel` interface that extends `tea.Model` with
metadata (ID, priority, refresh interval) and wire panels into a host model that owns
the layout decision.

### 4.4 Theme System

Catppuccin Mocha as the primary theme, with Latte (light), Macchiato (dark), and Nord
as alternatives. The `Theme` struct is a flat set of 30+ `lipgloss.Color` values covering
base palette, semantic roles, and agent-specific colors (Claude, Codex, Gemini, User).

`theme.Current()` returns the active global theme singleton. `semantic.go` adds semantic
role aliases that avoid hardcoding specific palette slots in component code.

**Worth adopting.** The semantic layer between raw palette and component code is the key
idea — agents reference `theme.Success` not `lipgloss.Color("#a6e3a1")`.

### 4.5 Dashboard as God Model

The 6,716-line `dashboard.go` file is the primary architectural concern in the TUI layer.
It is a single BubbleTea model that maintains all TUI state, owns all polling goroutines,
dispatches to 23 panels, handles all keyboard input, and implements adaptive tick rate.

The problem is not rendering decomposition (panels handle that), it is state collection
coupling. Every new data source must be wired into the top-level model.

**The architectural fix ntm has not yet applied** is a DataBus or ViewModel layer that
aggregates data from all sources and emits typed update messages to the model. The model
would subscribe to update messages rather than directly importing and polling every data
source. Autarch should start with this layer in place.

---

## 5. State Management Patterns

### 5.1 Three Parallel State Stores

ntm has three distinct state mechanisms:

| Store | Package | Backend | Lifetime | Purpose |
|-------|---------|---------|----------|---------|
| SessionState | `internal/session` | JSON file | Session lifetime | Pane layout, agent config for restore |
| SQLite Store | `internal/state` | SQLite WAL | Persistent | Ensemble runs, metrics, bead history, WebSocket events |
| In-memory EventBus | `internal/events` | ring buffer | Process lifetime | Pub/sub for coordination |

These three do not overlap badly, but require the developer to know which store serves
which purpose.

### 5.2 Config as God Struct

`config.Config` is a single type that owns config for every subsystem. Every subsystem
adding config keys here creates tight coupling. Import cycles result (e.g.,
`validateSynthesisStrategy` duplicated in config to avoid importing ensemble).

**Autarch should avoid this pattern.** Config for a subsystem should live in that
subsystem's package and be assembled by the root config loader.

### 5.3 Checkpoint vs. Handoff Separation

ntm draws a clean and useful distinction:
- **Checkpoint** (`internal/checkpoint`): machine-readable JSON state for exact session
  recreation (pane dimensions, agent commands, git state).
- **Handoff** (`internal/handoff`): human/LLM-readable YAML summary (~400 tokens) of
  "what happened / what to do next".

**Directly applicable to Autarch and Clavain.** Keep these as separate formats with
separate packages.

---

## 6. Plugin / Extension System

### 6.1 Agent Plugins

`internal/plugins` loads TOML files from `~/.config/ntm/plugins/` at startup. Each file
defines an `AgentPlugin` (name, alias, command, description, env, tags). Minimal and
correct — solves one narrow extension point without a general plugin framework.

### 6.2 Workflow Templates as Extension

`//go:embed builtins/*.toml` + runtime load from user config + project-level override,
with precedence: project > user > builtin. No registration step required.

**Worth adopting for Autarch's session templates and agent profiles.**

### 6.3 Tool Registry Adapter Pattern

`internal/tools` wraps each external CLI tool behind an `Adapter` interface:
`Name()`, `IsInstalled()`, `Exec()`, `Health()`. The dashboard queries the registry
rather than importing tool-specific packages directly.

**Worth adopting for Autarch/Interverse integration.** Wrap br, bv, oracle, interflux,
and other Interverse plugins behind adapters. This isolates availability checks and keeps
tool dependencies optional at the TUI layer.

---

## 7. Robot API / CLI-TUI Parity Pattern

ntm maintains explicit parity between robot JSON API, CLI output, and TUI dashboard.
The `internal/kernel` registry is the mechanism: every command is registered with name,
schema refs, REST binding, safety level, and emitted events. OpenAPI spec is generated
from this registry. Robot commands mirror TUI panels one-to-one.

**This is a strong pattern for Autarch.** Autarch's TUI and Clavain's robot/agent API
should be designed from a shared model layer. Defining the kernel registry equivalent
early constrains the delivery surfaces to stay consistent across CLI, TUI, MCP, and HTTP.

---

## 8. Ranked Adoption Recommendations for Demarch/Autarch

### Must Adopt (High Structural Value)

1. **SwarmPlan intermediate representation** — Separate session planning from execution.
   Plan type is serializable, previewable, remotable.
   *ntm reference: `internal/swarm/types.go` SwarmPlan, SessionSpec, PaneSpec.*

2. **Panel interface on top of tea.Model** — Panel adds ID, Priority, RefreshInterval,
   SetSize. Host model holds panel list and dispatches messages. Keeps panels isolated
   and testable.
   *ntm reference: `internal/tui/dashboard/panels/panel.go` Panel interface.*

3. **Single width-tier system** — One `Tier` type, one `TierForWidth()` function, one
   `TierForWidthWithHysteresis()` function. Never let a second tier system grow alongside.
   *ntm reference: `internal/tui/layout/layout.go` — adopt this, skip dashboard/layout.go.*

4. **AutoRespawner: soft-then-hard recovery** — Ctrl+C -> wait -> verify -> relaunch.
   Per-pane retry caps with time-based reset. Optional account rotation before relaunch.
   *ntm reference: `internal/swarm/auto_respawner.go`.*

5. **Handoff / Checkpoint as separate formats** — Machine-readable checkpoint for
   recreation; LLM-readable YAML handoff for context continuity.
   *ntm reference: `internal/checkpoint/` and `internal/handoff/`.*

### Should Adopt (Medium Value)

6. **Kernel registry for multi-surface parity** — Register commands with schema refs,
   REST binding, safety level. Generate OpenAPI, verify TUI parity from registry.
   *ntm reference: `internal/kernel/registry.go` and `internal/kernel/types.go`.*

7. **Semantic theme layer** — `theme.Success`, `theme.AgentClaude` rather than raw
   `lipgloss.Color`. Enables theme swap without touching component code.
   *ntm reference: `internal/tui/theme/semantic.go`.*

8. **Embedded workflow templates with precedence** — `//go:embed builtins/*.toml`,
   runtime load from user config and project override. No registration step.
   *ntm reference: `internal/workflow/loader.go`.*

9. **Tool registry adapter pattern** — `Adapter` interface per external tool:
   `IsInstalled()`, `Exec()`, `Health()`. Registry queried at TUI level.
   *ntm reference: `internal/tools/registry.go`.*

### Adopt Concept, Adapt Form (Partial Value)

10. **Reasoning mode taxonomy** — Named modes assigned to agent panes, with tier
    (core/advanced/experimental) controlling surface area. The 80-mode set is ntm-specific
    but the pattern applies to Demarch's interflux review lenses and intersynth strategies.
    *ntm reference: `internal/ensemble/modes.go`, `internal/ensemble/strategy.go`.*

### Do Not Adopt (Anti-Patterns to Explicitly Avoid)

- Config god struct — subsystem configs should own themselves.
- Dashboard god model — introduce a DataBus/ViewModel layer from day one.
- Two width-tier systems — one canonical system, enforced everywhere.
- CLI files absorbing business logic — CLI parses flags, calls domain functions.
- Parallel CLI/robot/TUI implementation of the same operations — use a shared application
  service layer.
- Partial experimental build tags — gate the entire feature or gate nothing.

---

## 9. Files and Packages of Primary Interest

The following ntm files are worth studying directly when implementing the adopted patterns:

- `/home/mk/projects/Demarch/research/ntm/internal/kernel/types.go` — Command registry type
- `/home/mk/projects/Demarch/research/ntm/internal/kernel/registry.go` — Registry implementation
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/types.go` — SwarmPlan, SessionSpec, PaneSpec
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/orchestrator.go` — Plan execution
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/auto_respawner.go` — Crash recovery
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/account_rotator.go` — Account rotation
- `/home/mk/projects/Demarch/research/ntm/internal/tui/dashboard/panels/panel.go` — Panel interface
- `/home/mk/projects/Demarch/research/ntm/internal/tui/layout/layout.go` — Width tier system
- `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` — Theme struct
- `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/semantic.go` — Semantic roles
- `/home/mk/projects/Demarch/research/ntm/internal/workflow/loader.go` — Precedence loading
- `/home/mk/projects/Demarch/research/ntm/internal/workflow/template.go` — WorkflowTemplate type
- `/home/mk/projects/Demarch/research/ntm/internal/tools/registry.go` — Tool adapter registry
- `/home/mk/projects/Demarch/research/ntm/internal/handoff/types.go` — Handoff format
- `/home/mk/projects/Demarch/research/ntm/internal/checkpoint/types.go` — Checkpoint format
- `/home/mk/projects/Demarch/research/ntm/internal/events/bus.go` — EventBus pub/sub
- `/home/mk/projects/Demarch/research/ntm/docs/ORCHESTRATION_FEATURES.md` — Design intent
- `/home/mk/projects/Demarch/research/ntm/docs/robot-api-design.md` — API design principles
