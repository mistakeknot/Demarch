# Interverse Plugin Ecosystem Structure

**Date:** 2026-02-20  
**Scope:** Complete analysis of the 31-plugin ecosystem, Clavain hub, Autarch, and Intercore infrastructure

## Executive Summary

Interverse is a monorepo organizing 31 Claude Code plugins, the Clavain autonomous agent orchestrator (hub), auxiliary AI tools (Autarch), and three infrastructure layers:

1. **Layer 1 (Kernel)**: `intercore` — SQLite-backed state machine for runs, phases, gates, dispatches, and tokens
2. **Layer 2 (OS)**: `clavain` (hub/clavain/) — 15 skills, 52 commands, 12 hooks, orchestrates development lifecycle
3. **Layer 3 (Drivers)**: 31 companion plugins, each adding specialized capabilities

All components follow lowercase naming (`interflux`, `interlock`, etc.), except proper nouns (Clavain, Autarch, Interverse).

---

## 1. Plugin Directory — 31 Plugins

### Multi-Agent Review & Research
- **interflux** (v0.2.18) — 12 review agents + 5 research agents, flux-drive protocol, qmd + exa MCP, scored triage
- **interpeer** — Cross-AI peer review with Oracle/GPT escalation
- **intersynth** — Multi-agent synthesis engine (verdict aggregation)

### Documentation & Knowledge Management
- **interkasten** (v0.4.3) — Bidirectional Notion sync, adaptive AI docs, 21 MCP tools, WAL protocol
- **intermem** (v0.2.1) — Memory synthesis, graduates auto-memory to AGENTS.md/CLAUDE.md
- **interdoc** — AGENTS.md generator
- **interwatch** — Doc freshness monitoring

### Code Analysis & Architecture
- **intermap** — Project-level code mapping (Go binary + Python bridge), 6 MCP tools (call graphs, impact analysis, code structure)
- **tldr-swinton** — Token-efficient code context (vendored in intermap/python/vendor/)
- **interleave** — Deterministic skeleton + LLM islands pattern (spec + library)

### Multi-Agent Coordination
- **interlock** (v0.2.1) — File reservation, agent coordination, 11 MCP tools, wraps intermute HTTP API
- **intermux** — Agent activity visibility + tmux monitoring (MCP)
- **interserve** (v0.1.2) — Codex spark classifier + context compression (MCP), delegates to dispatch.sh

### Workflow & Phase Management
- **interphase** — Phase tracking + gates
- **interpath** — Product artifact generator
- **internext** — Work prioritization + tradeoff analysis

### Quality & Testing
- **intertest** (v0.1.1) — 3 skills: systematic-debugging, test-driven-development, verification-before-completion
- **intercheck** — Code quality guards + session health monitoring
- **intercraft** — Agent-native architecture patterns

### Development Tooling
- **interdev** — Developer tooling + skill/plugin authoring
- **interpub** — Plugin publishing
- **interform** — Design patterns + visual quality
- **interline** — Statusline renderer
- **interlens** — Cognitive augmentation lenses (FLUX podcast)

### Data & Analytics
- **interfluence** (v0.2.5) — Voice profile + style adaptation (TypeScript MCP server)
- **intersearch** — Shared embedding + Exa search library
- **interstat** — Token efficiency benchmarking
- **tool-time** — Tool usage analytics
- **interject** — Ambient discovery + research engine (MCP)

### User Integration
- **interslack** — Slack integration
- **tuivision** (v0.1.4) — TUI automation + visual testing (Python-based Playwright for terminal apps)

---

## 2. Typical Plugin Structure

### File Layout Pattern

All 31 plugins follow this structure:

```
plugin-name/
├── .claude-plugin/
│   ├── plugin.json              # Manifest (name, version, skills, commands, agents, mcpServers)
│   └── integration.json         # Integration details (optional)
├── CLAUDE.md                    # Quick reference for Claude Code sessions
├── AGENTS.md                    # Comprehensive development guide (if present)
├── .git/                        # Each plugin has its own Git repo
├── hooks/                       # SessionStart/Stop/PreToolUse/PostToolUse/etc.
├── skills/                      # Markdown skill definitions (optional, many plugins have none)
├── commands/                    # Markdown command definitions (optional)
├── agents/                      # Agent prompt templates (optional)
├── src/ or cmd/                 # Source code (TypeScript, Go, Python)
├── docs/                        # Plugin-specific documentation
├── README.md                    # High-level overview
├── .env.example                 # Environment variable template
└── package.json / go.mod        # Language-specific build config
```

### Example: interflux (Comprehensive)

```
interflux/
├── .claude-plugin/plugin.json
├── CLAUDE.md (defines namespace "interflux:", describes protocol spec)
├── AGENTS.md
├── skills/flux-drive/ (contains SKILL.md)
├── skills/flux-research/
├── commands/flux-drive.md, flux-research.md, flux-gen.md (3 commands)
├── agents/review/ (12 fd-* agents: fd-architecture, fd-safety, etc.)
├── agents/research/ (5: framework-docs-researcher, repo-research-analyst, etc.)
├── config/flux-drive/domains/ (11 Research Directive profiles)
├── config/flux-drive/knowledge/ (compounded knowledge storage)
├── docs/spec/ (9 flux-drive protocol spec documents)
├── .git/
└── hooks/
```

### Example: interkasten (MCP + Tools)

```
interkasten/
├── .claude-plugin/plugin.json (21 MCP tools registered)
├── server/ (TypeScript + Drizzle ORM + SQLite)
│   ├── src/
│   │   ├── daemon/tools/ (21 tool handlers)
│   │   ├── sync/ (Notion client, merge engine, WAL protocol)
│   │   └── store/ (SQLite schema)
│   ├── package.json
│   └── npm run build
├── skills/layout, onboard, doctor
├── commands/onboard.md, doctor.md
├── CLAUDE.md (describes WAL protocol, hierarchy, 3-way merge)
└── AGENTS.md
```

### Example: interlock (Go MCP + Bash Hooks)

```
interlock/
├── .claude-plugin/plugin.json (1 MCP server, "interlock" entry point)
├── cmd/interlock-mcp/ (Go binary, mcp-go SDK)
├── internal/ (Go implementation: file reservation, messaging, conflict checks)
├── hooks/ (Bash hooks: PreToolUse:Edit for advisory, git pre-commit for mandatory)
├── CLAUDE.md (negotiation protocol, advisory-only vs mandatory enforcement)
└── go.mod
```

---

## 3. Skills Declaration in plugin.json

Skills are optional Markdown skill definitions. A plugin declares skills via:

```json
{
  "name": "plugin-name",
  "skills": [
    "./skills",           // Directory containing skill.md files OR
    "./skills/skill-name" // Specific directory for a skill
  ]
}
```

### Skill Structure

Each skill is a directory containing `SKILL.md` (the actual content exposed to Claude Code).

### Examples

| Plugin | Skills | Count | Purpose |
|--------|--------|-------|---------|
| **interflux** | `flux-drive`, `flux-research` | 2 | Multi-agent review protocol, research orchestration |
| **interkasten** | `layout`, `onboard`, `doctor` | 3 | Project discovery, classification, diagnostics |
| **intertest** | `systematic-debugging`, `test-driven-development`, `verification-before-completion` | 3 | QA disciplines |
| **interlock** | (no explicit skills dir) | — | Coordination via MCP tools only |
| **intermem** | `synthesize` | 1 | Memory graduation workflow |
| **interfluence** | (all under `./skills`) | ~5 | Voice analysis, profile application, learning |
| **interserve** | (no skills) | — | MCP tools only |
| **tuivision** | (no skills) | — | MCP tools only |

### Key Pattern: Skills vs MCP Servers

- **Skills** = Markdown workflows that Claude Code surfaces as learnable patterns (`/skill-name`, `/command-name`)
- **MCP Servers** = Binaries exposing tools (CLI-like functions) for agents to invoke programmatically

Example: **interkasten**
- Skills: `/interkasten:layout` (interactive discovery), `/interkasten:onboard` (classification)
- MCP Tools: `interkasten_health`, `interkasten_sync`, `interkasten_triage`, etc.

---

## 4. Intermap — Code Analysis & Architecture

**Location:** `/root/projects/Interverse/plugins/intermap/`  
**Type:** Hybrid Go + Python (MCP server bridging compiled + scripting languages)

### Purpose

Provides 6 MCP tools for project-level code understanding:
1. `project_registry` — Scan workspace for projects
2. `resolve_project` — Find project for a file path
3. `agent_map` — Active agents overlay (integrates intermute data)
4. `code_structure` — Functions, classes, imports
5. `impact_analysis` — Reverse call graph ("who calls this?")
6. `change_impact` — Affected tests given file changes

### Architecture

```
go/ (CLI entry point)
├── cmd/intermap-mcp/main.go       → MCP server, stdio transport
├── internal/python/bridge.go      → Subprocess JSON-over-stdio to Python
└── test helpers

python/ (Analysis engine)
├── intermap/call_graphs.py        → Reverse call graph
├── intermap/impact_analysis.py    → Test impact prediction
├── intermap/code_structure.py     → Symbol extraction
└── vendor/                         → Files vendored from tldr-swinton
```

### Relationship to Other Plugins

- **Vendored from tldr-swinton**: Copies token-efficient extraction logic
- **Called by**: interflux (research agents use for code analysis), interlock (agents check affected files)
- **Integrates with**: intermute (for `agent_map`)
- **Not used by**: intertest, intercheck (quality plugins work at different scope)

---

## 5. Clavain Skills — hub/clavain/skills/

**Location:** `/root/projects/Interverse/hub/clavain/skills/`  
**Count:** 17 directories (15 SKILL.md + 2 utility libs)

### Skills Directory

```
skills/
├── brainstorming/                  # Brainstorm pattern + facilitation
├── code-review-discipline/         # Code review process
├── dispatching-parallel-agents/    # Launch multi-agent dispatch
├── engineering-docs/               # Doc engineering patterns
├── executing-plans/                # Plan execution workflow
├── file-todos/                     # Task-based organization
├── galiana/                        # REDACTED (sensitive)
├── interserve/                     # Codex spark classifier integration
├── landing-a-change/               # Change integration workflow
├── refactor-safely/                # Safe refactoring patterns
├── subagent-driven-development/    # Sub-agent orchestration
├── upstream-sync/                  # Git sync patterns
├── using-clavain/                  # Clavain usage guide (injected at SessionStart)
├── using-tmux-for-interactive-commands/ # tmux patterns
└── writing-plans/                  # Plan composition

Utility libs (not SKILL.md):
├── engineering-docs/impl/          # Implementation helpers
└── interserve/*/                   # Interserve integration code
```

### Clavain 15 Core Skills (with SKILL.md)

1. **brainstorming** — Facilitated ideation
2. **code-review-discipline** — Multi-agent code review
3. **dispatching-parallel-agents** — Launch agents Task()
4. **engineering-docs** — Docs as code patterns
5. **executing-plans** — Plan execution
6. **file-todos** — /file-todos integration
7. **landing-a-change** — Change workflow
8. **refactor-safely** — Safe refactoring
9. **subagent-driven-development** — Delegation
10. **upstream-sync** — Git sync
11. **using-clavain** — Clavain reference (injected via SessionStart hook)
12. **using-tmux-for-interactive-commands** — tmux usage
13. **writing-plans** — Plan authoring
14. **interserve** — Codex integration
15. **galiana** — (redacted)

### How Skills Are Exposed

**SessionStart hook** (`hooks/session-start.sh`):
1. Injects `using-clavain/SKILL.md` content as `additionalContext` JSON
2. Claude Code loads plugin + skills
3. All skills become `/clavain:<skill>` or `/skill-name` commands
4. User can `/skill brainstorming` to see the full workflow

---

## 6. Autarch — Unified AI Agent Development Tools

**Location:** `/root/projects/Interverse/hub/autarch/`  
**Type:** Unified monorepo (Go, plugins, CLI tools)

### Overview

Autarch is NOT a Claude Code plugin — it's a standalone tool suite for agent development, mission control, and research. Complements Clavain.

### Four Main Tools

| Tool | Purpose | Type | Key Features |
|------|---------|------|--------------|
| **Bigend** | Multi-project agent mission control | Web + TUI | Dashboard, real-time status, project oversight |
| **Gurgeh** | TUI-first PRD generation + validation | CLI + API | Spec authoring, version diffing, prioritization |
| **Coldwine** | Task orchestration for human-AI collaboration | CLI + State | Task graph, assignments, progress tracking |
| **Pollard** | General-purpose research intelligence | CLI + API | Tech, medicine, law, economics; multi-domain hunters; watch mode |

### Execution Mode

```bash
./dev autarch tui                    # Unified TUI (recommended)
./dev autarch tui --tool=gurgeh      # Jump to specific tool
./dev pollard scan --hunter github   # Research via CLI
./dev gurgeh export PRD-001          # Export spec to briefs
```

### Architecture

```
autarch/
├── cmd/autarch/      → Unified TUI dispatcher
├── cmd/gurgeh/       → Spec authoring + validation
├── cmd/coldwine/     → Task orchestration
├── cmd/pollard/      → Research intelligence (multi-domain hunters)
├── cmd/signals/      → WebSocket server for real-time signals
├── internal/{tool}/  → Tool-specific code
├── pkg/tui/          → Shared TUI styles (Tokyo Night colors, Bubble Tea)
├── .pollard/         → Pollard data directory (sources, watch state, reports)
├── .gurgeh/specs/    → Spec versioning + history
└── autarch-plugin/   → Claude Code plugin wrapper
```

### Plugin Wrapper

**Location:** `/root/projects/Interverse/hub/autarch/autarch-plugin/`  
- Exposes Autarch via Claude Code as commands
- Can dispatch to `autarch tui` or individual tool CLIs
- Separate from Autarch core (which is self-contained)

### Relationship to Clavain

- **Orthogonal**: Clavain is sprint orchestration; Autarch is tool development + research
- **Integration point**: Clavain can dispatch Autarch agents (e.g., Pollard research via Gurgeh specs)
- **Shared infrastructure**: Both use Intermute for cross-tool coordination

---

## 7. Intercore — Layer 1 Kernel

**Location:** `/root/projects/Interverse/infra/intercore/`  
**Type:** Go CLI binary + SQLite WAL database  
**Role:** Durable system of record for runs, phases, gates, dispatches, events, and token budgets

### Concept

Intercore is the **kernel** of Clavain — the layer below the OS. It provides:
- **Durability**: SQLite with WAL protocol
- **Mechanism, not policy**: Records phase transitions but doesn't define "brainstorm"
- **Host-agnostic**: Survives OS/platform changes
- **Bash-friendly**: CLI interface (`ic` binary) for hook integration

### Key Data Models

| Entity | Purpose | Example |
|--------|---------|---------|
| **Run** | A development task with phases, budget, complexity | Goal: "Implement auth feature", 5 phases, 500k token budget |
| **Phase** | State in run lifecycle | brainstorm → plan → execute → review → done |
| **Dispatch** | Agent execution (process spawn + result collection) | Spawn agent, poll liveness, collect verdict |
| **Gate** | Policy check before phase advance | Budget check, correctness check, peer review approval |
| **Event** | Audit trail (phase transition, dispatch result) | Logged to database + event bus |
| **Token Budget** | Token accounting across dispatches | Track in/out/cache; warn at 80%, fail at 100% |

### CLI Commands (30+)

**State Management:**
- `ic state set/get/delete/list` — JSON key-value store with TTL

**Sentinel (Atomic Throttle):**
- `ic sentinel check/reset/list/prune` — Prevent thundering herd

**Dispatch (Agent Execution):**
- `ic dispatch spawn` — Launch process
- `ic dispatch poll/wait` — Liveness & result collection
- `ic dispatch tokens --set` — Update token counts
- `ic dispatch list/prune` — Lifecycle management

**Run (Phase Machine):**
- `ic run create` — New run with phases + budget
- `ic run advance` — Phase transition (gated)
- `ic run status/phase/events` — Query state
- `ic run agent add/list/update` — Agent tracking
- `ic run artifact add/list` — Artifact tracking
- `ic run tokens/budget` — Token accounting

**Gate (Policy):**
- `ic gate check` — Dry-run gate evaluation
- `ic gate override` — Force-advance
- `ic gate rules` — Display rule table

**Event Bus:**
- `ic events tail/cursor` — At-least-once event stream

**Lock (Filesystem Mutex):**
- `ic lock acquire/release/list` — POSIX mkdir-based locks

### Database Schema

```sql
state                  -- JSON key-value store with TTL
sentinels              -- Atomic throttle guards
dispatches             -- Agent process metadata + results
runs                   -- Phase machine state
phase_events           -- Audit trail for phase transitions
dispatch_events        -- Audit trail for dispatch results
run_agents             -- Agents participating in run
run_artifacts          -- Artifacts produced in phases
```

### Bash Integration

**File:** `lib-intercore.sh` (wrappers for hooks)

```bash
intercore_run_create --project=. --goal="..."
intercore_run_advance <run-id>
intercore_run_phase <run-id>
intercore_run_agent_add <run> --type=claude
```

### Design Decisions

- **CLI only** (no Go library API in v1) — Bash hooks shell out to `ic`
- **SQLite with WAL** — No external DB; survives network loss
- **PRAGMA user_version** — Single-version number (no schema_version table)
- **No CTE + UPDATE ... RETURNING** — Not supported by modernc.org/sqlite
- **SetMaxOpenConns(1)** — Pure Go SQLite, thread-safe with single connection

---

## 8. Services Layer

**Location:** `/root/projects/Interverse/services/`

### intermute (Multi-Agent Coordination Service)

**Type:** Go HTTP + WebSocket service  
**Port:** 7338 (local by default)  
**Socket:** `/var/run/intermute.sock` (Unix socket preferred)

**Purpose:**
- Central coordination hub for file reservations (conflict detection)
- Agent messaging (non-blocking pub/sub)
- Dispute resolution (negotiation protocol)
- Real-time activity feed

**How Interlock Uses It:**
- Interlock (plugin) wraps intermute HTTP API
- File reservation requests → interlock MCP tools → intermute HTTP
- Negotiation thread → intermute → back to interlock

---

## 9. SDK Layer

**Location:** `/root/projects/Interverse/sdk/`

### interbase (Shared Integration SDK)

**Type:** Dual-mode plugin SDK  
**Purpose:** Provides shared patterns for plugins that need:
- Both Claude Code plugin AND standalone CLI mode
- Shared state + config management
- Dual authentication (Claude context + CLI credentials)

**Used By:** (documentation placeholder; verify usage)

---

## 10. Infrastructure Components

### marketplace

**Location:** `/root/projects/Interverse/infra/marketplace/`  
**Purpose:** Plugin listing, versioning, publishing pipeline

### interbench

**Location:** `/root/projects/Interverse/infra/interbench/`  
**Purpose:** Benchmarking framework for plugin performance

### interband

**Location:** `/root/projects/Interverse/infra/interband/`  
**Purpose:** (TBD — monitoring/observability)

### agent-rig

**Location:** `/root/projects/Interverse/infra/agent-rig/`  
**Purpose:** Testing harness for multi-agent scenarios

---

## 11. Dependency Graph — How Components Relate

### Plugin Dependency Chains

```
clavain (hub)
├── interflux (review agents, research orchestration)
│   ├── qmd MCP (documentation search)
│   ├── exa MCP (web search)
│   └── interserve (Codex spark classifier)
├── interlock (file coordination)
│   └── intermute (HTTP backend)
├── interphase (phase tracking, gates)
├── intermap (code analysis)
│   ├── tldr-swinton (vendored token efficiency)
│   └── Python analysis bridge
├── interpeer (cross-AI review)
│   └── Oracle/GPT escalation
└── 26+ other plugins (skills, tools, integrations)
```

### Hook Wiring

**clavain hooks/** call these services:
1. **intercore** (`ic` CLI) — state machines, phase transitions
2. **intermute** (HTTP) — file reservations (via interlock)
3. **interphase** (MCP) — gate checks, discovery
4. **interserve** (MCP) — Codex spark classification

### Data Flow Example: Code Review

```
1. Clavain skill: /code-review-discipline
2. User invokes review
3. clavain dispatches agents via Task(interflux:review:fd-*)
4. Each fd-* agent (lives in interflux)
5. Agents use intermap for code_structure, impact_analysis
6. Agents call interflux synthesis
7. Result → clavain artifact store
8. clavain advances phase via intercore
9. Gate check via interphase
10. Notify via intermux activity
```

---

## 12. Key Design Decisions (Ecosystem-Level)

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Lowercase naming** | Consistency, CLI-friendly | All 31 plugins follow; exceptions: Clavain (proper noun), Interverse (monorepo name) |
| **Physical monorepo** | Unified CI/CD, shared docs | Not git monorepo; each subproject has `.git` |
| **Separate Git repos per plugin** | Independent versioning, publishing | Marketplace can version each plugin separately |
| **Layer 1 ≠ Layer 2** | Plugin-agnostic kernel | Intercore survives plugin/platform changes |
| **Skills + MCP dual mode** | Workflows + tools | Skills = learnable patterns, MCP = programmatic tools |
| **Bash hook integration** | Glue to OS layer | All stateful operations via `ic` CLI |
| **Optional MCP servers** | Gradual adoption | Plugins can be CLI-only (intertest) or MCP-only (tuivision) |
| **Notion bidirectional sync** | Documentation as source of truth | interkasten + interwatch + intermem feedback loop |
| **Autarch orthogonal** | Tool development ≠ sprint orchestration | Both use intermute for coordination |
| **Intermute central hub** | Single conflict detection point | All multi-agent plugins can reserve files atomically |

---

## 13. Terminology Reference

| Term | Meaning | Examples |
|------|---------|----------|
| **Companion plugin** | Plugin that extends Clavain or another hub | interflux, interlock, interpeer |
| **Skill** | Markdown workflow exposed as `/skill-name` | `/clavain:brainstorming`, `/interfluence:apply` |
| **Command** | Markdown entry point to a skill | `/flux-drive`, `/interkasten:onboard` |
| **Agent** | Prompt template for LLM (often persona + task) | fd-architecture (lives in interflux) |
| **MCP tool** | Programmatic function exposed to agents | `project_registry`, `interkasten_sync` |
| **Hook** | Event handler (SessionStart, PostToolUse, etc.) | Pre-commit guard in interlock, memory synthesis in intermem |
| **Dispatch** | A single agent execution (spawn + poll + result) | "Spawn fd-architecture agent on this code" |
| **Run** | A development task with phases (managed by intercore) | "Implement auth feature" across 5 phases |
| **Gate** | Policy check before phase advance | "Peer review approved" before execute → review |
| **Flux-drive** | Protocol for multi-agent review + research | Defined in interflux spec, 12 review + 5 research agents |
| **Spark** | Classification label (domain, concern) | interserve assigns sparks; interphase routes by spark |

---

## Appendix: Plugin Count & Roles

**31 plugins, grouped by role:**

### Core Review & Research (3)
- interflux, interpeer, intersynth

### Knowledge & Docs (4)
- interkasten, intermem, interdoc, interwatch

### Code Analysis (3)
- intermap, tldr-swinton, interleave

### Coordination (3)
- interlock, intermux, interserve

### Workflows (3)
- interphase, interpath, internext

### Quality (3)
- intertest, intercheck, intercraft

### DevOps & Tooling (6)
- interdev, interpub, interform, interline, interlens, tool-time

### Data & Analytics (5)
- interfluence, intersearch, interstat, interject, tuivision

### External (1)
- interslack

---

**End of Research Document**
