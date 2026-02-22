# Demarch Glossary

> Canonical terminology for the Demarch platform. When terms are used differently across documents, this glossary defines the correct usage. See [architecture.md](architecture.md) for the 3-layer model diagram.

## Pillars

Demarch has five pillars — the major components that make up the platform:

| Pillar | What it is | Layer |
|--------|-----------|-------|
| **Intercore** | Orchestration kernel — runs, phases, gates, dispatches, events. The durable system of record. | L1 (Kernel) |
| **Clavain** | Agent OS — workflow policy, sprint lifecycle, model routing, agent dispatch. The reference agency. | L2 (OS) |
| **Interverse** | 33+ companion plugins, each wrapping one capability. Independently installable. | L2 (Drivers) |
| **Autarch** | Application layer — TUI tools (Bigend, Gurgeh, Coldwine, Pollard). | L3 (Apps) |
| **Interspect** | Adaptive profiler — reads kernel events, proposes OS configuration changes. The learning loop. | Cross-cutting |

"Pillar" is the organizational term for major components. "Layer" (L1/L2/L3) describes the architectural dependency hierarchy between them. Use "pillar" when listing what Demarch is made of; use "layer" when discussing how components interact, write-path contracts, or survival properties.

## Kernel (L1 — Intercore)

| Term | Definition |
|------|------------|
| **Run** | A kernel lifecycle primitive — a named execution with a phase chain, gate rules, event trail, and token budget. The atomic unit of orchestrated work. |
| **Phase** | A named stage within a run. The kernel enforces ordering and gate checks; the OS defines phase names and semantics. |
| **Phase chain** | The ordered sequence of phases a run advances through (e.g., `brainstorm → plan → execute → done`). Custom chains are supported. |
| **Gate** | An enforcement point between phases. The kernel evaluates pass/fail based on rules; the OS defines what evidence is required. Gates can be `hard` (blocking) or `soft` (advisory). |
| **Dispatch** | A kernel record tracking an agent spawn — PID, status, token usage, artifacts. One run may have many dispatches. |
| **Event** | A typed, immutable record of a state change in the kernel. Append-only log with consumer cursors for at-least-once delivery. |
| **State** | Key-value storage scoped by (key, scope_id). Used for session context, configuration, and workflow metadata. Supports TTL for auto-expiration. |
| **Lock** | A filesystem-based named mutex with owner tracking and stale detection. Works even when the database is unavailable. |
| **Sentinel** | A rate-limiting primitive — tracks "last seen" timestamps to throttle repeated operations. |
| **Artifact** | A file produced during a run phase (brainstorm doc, plan file, test output). Tracked with content hashes for integrity. |
| **Token budget** | Per-run or per-dispatch limits on LLM token consumption (billing tokens: input + output), with warning thresholds. Sprint defaults by complexity: C1=50K, C2=100K, C3=250K, C4=500K, C5=1M. Enforcement is soft (warn + override). |

## OS (L2 — Clavain + Drivers)

| Term | Definition |
|------|------------|
| **Sprint** | An OS-level run template with preset phases (brainstorm → strategize → plan → review → execute → ship → reflect). The full development lifecycle. |
| **Bead** | Clavain's work-tracking primitive — adds priority (P0-P4), type (epic/feature/task/bug), dependencies, and sprint association on top of kernel runs. Managed via the `bd` CLI. |
| **Macro-stage** | OS-level workflow grouping: Discover, Design, Build, Ship, Reflect. Each maps to sub-phases in the kernel. |
| **Skill** | A reusable prompt template that defines a specific capability (brainstorming, plan writing, code review). Invoked via `/clavain:<name>`. |
| **Command** | A user-invocable slash command (e.g., `/sprint`, `/work`). May invoke one or more skills. |
| **Hook** | A shell script triggered by Claude Code lifecycle events (SessionStart, PostToolUse, etc.). Used for state injection, validation, and telemetry. |
| **Driver** | A companion plugin that extends the OS layer with a specific capability. Not a separate architectural layer. Also called "companion plugin." |
| **Companion plugin** | An `inter-*` capability module (interflux, interlock, interject, etc.) — wraps one capability as an OS extension. Synonym for "driver." |
| **Quality gates** | The review step before shipping — auto-selects reviewer agents based on what changed, runs them in parallel, synthesizes findings. |
| **Flux-drive** | Multi-agent document/code review workflow — triages relevant review perspectives, dispatches specialist agents. |
| **Day-1 workflow** | The core loop a new user experiences: brainstorm → plan → review plan → execute → test → gates → ship. |
| **Safety posture** | The level of caution enforced at each macro-stage (low for Discover, highest for Ship). |

## Apps (L3 — Autarch)

| Term | Definition |
|------|------------|
| **Autarch** | The application layer — four TUI tools (Bigend, Gurgeh, Coldwine, Pollard) plus shared `pkg/tui` library. |
| **Bigend** | Multi-project agent mission control (web + TUI dashboard). |
| **Gurgeh** | TUI-first PRD generation and validation tool. |
| **Coldwine** | Task orchestration for human-AI collaboration. |
| **Pollard** | General-purpose research intelligence (tech, medicine, law, economics). |
| **Intent** | A high-level action request from L3 to L2 (e.g., start-run, advance-run, override-gate, submit-artifact). Apps express intents; the OS translates them to kernel operations. |

## Cross-Cutting

| Term | Definition |
|------|------------|
| **Interspect** | Adaptive profiler that consumes kernel events and proposes OS configuration changes. Read-only — never writes to the kernel. Cross-cutting, not a layer. |
| **Write-path contract** | The invariant that all durable state flows through the kernel (L1). Higher layers call `ic` CLI commands — they never write to the database directly. |
| **Host adapter** | Platform integration layer (Claude Code plugin interface, Codex CLI, bare shell). Not a companion plugin. |
| **Dispatch driver** | Agent execution backend (Claude CLI, Codex CLI, container runtime) — the runtime that executes a dispatch. |

## Sprint Phase Mapping (OS ↔ Kernel)

The OS (Clavain) and kernel (Intercore) both use 9-phase chains, but with different phase names. This table shows the canonical mapping.

| # | OS Phase (`PHASES_JSON`) | Kernel Phase (`DefaultPhaseChain`) | Kernel Gate Fires? | Notes |
|---|---|---|---|---|
| 1 | `brainstorm` | `brainstorm` | Yes — `artifact_exists(brainstorm)` | Same name, gate fires |
| 2 | `brainstorm-reviewed` | `brainstorm-reviewed` | Yes — `artifact_exists(brainstorm-reviewed)` | Same name, gate fires |
| 3 | `strategized` | `strategized` | Yes — `artifact_exists(strategized)` | Same name, gate fires |
| 4 | `planned` | `planned` | Yes — `artifact_exists(planned)` | Same name, gate fires |
| 5 | `plan-reviewed` | *(no equivalent)* | No — OS-only | OS enforces via agency-spec gate (min 2 agents, max 3 P1 findings) |
| 6 | `executing` | `executing` | No — from-phase mismatch | Kernel expects `planned→executing`; OS sends `plan-reviewed→executing` |
| 7 | `shipping` | `polish` | No — name mismatch | Kernel expects `review→polish`; OS sends `executing→shipping` |
| 8 | `reflect` | `reflect` | No — from-phase mismatch | Kernel expects `polish→reflect`; OS sends `shipping→reflect` |
| 9 | `done` | `done` | Yes — `artifact_exists(reflect)` | Same from/to names, gate fires |

**Kernel gate rule coverage:** Kernel gates fire for 5 of 8 transitions in OS-created sprints (phases 1-4 and the final `reflect→done`). The middle transitions (5-8) bypass kernel gates because the OS phase names don't match the kernel's gate rules map keys. The OS compensates with its own gate enforcement via agency-spec.yaml, but this is OS-level policy enforcement, not kernel-enforced invariants.

**Why divergent:** `plan-reviewed` exists in the OS because flux-drive plan review is an OS-level gate with no kernel equivalent. `shipping` was the original name for the quality-gates/ship step; renaming it to `polish` requires migration of all existing sprints (deferred to iv-52om). The `plan-reviewed` insertion shifts all subsequent from-phase values, causing cascade mismatches.

**Resolution path:** Align the OS phase chain to use kernel phase names (replacing `plan-reviewed` with a gate on the `planned→executing` transition, and `shipping` with `polish`). This makes kernel gate enforcement cover the full chain. Tracked as iv-v5al.

## Terms to Avoid

| Don't say | Say instead | Why |
|-----------|-------------|-----|
| L4, L5 | Driver, Cross-cutting | The 3-layer model has L1-L3 only; drivers are L2 extensions, Interspect is cross-cutting |
| "interphase" (for new code) | `ic gate`, `ic run` | interphase is a legacy compatibility shim; new code should call intercore directly |
| "workflow engine" | kernel, orchestration kernel | Intercore provides primitives, not a workflow DSL |
| "API" (for intercore v1) | CLI surface | There is no Go library API in v1; the CLI is the contract |
| "component" (for top-level) | pillar | Intercore, Clavain, Interverse, Autarch, and Interspect are pillars; "component" is vague |
| "pillar" (for sub-modules) | driver, companion plugin, tool | Pillars are only the 5 top-level entries; interflux, interlock, etc. are drivers |
