# Demarch Vision & Architecture Analysis

**Date:** 2026-02-24  
**Scope:** Comprehensive review of Demarch vision, pillars, layers, and multi-agent coordination  
**Source documents:** CLAUDE.md, AGENTS.md, demarch-vision.md, interspect-vision.md, intermute/interlock docs, multi-agent-coordination.md

---

## 1. Overall Demarch Vision

Demarch is an **open-source autonomous software development agency platform** that simultaneously advances three frontier axes:

1. **Autonomy** — How much of the development lifecycle runs without human intervention
2. **Quality** — Defect escape rates, review signal precision, actionable findings vs false positives
3. **Token efficiency** — Cost per *impact* (tokens per landable change, per actionable finding, per defect caught)

**The bet:** If you build the right infrastructure, you can have all three without tradeoffs. They become a flywheel connected by **Interspect** (the profiler/learner).

**Core philosophy:** Not a coding assistant. Not an AI gateway. Not a framework. A **platform for autonomous software development agencies** that ships real code with discipline, durability, and learning. The system that runs the most sprints learns the fastest.

### Why It Exists

LLM agents have an infrastructure problem: nothing survives. Session contexts compress. State dies. Networks drop. Processes crash. An agent that ran for an hour, produced artifacts, dispatched sub-agents, and advanced through phases leaves behind a chat transcript. Demarch handles this with a durable kernel (SQLite-backed Go CLI), an opinionated OS (development discipline), a profiler (learning loop), and 33+ companion drivers.

---

## 2. The Five Pillars & Three-Layer Architecture

### Five Pillars (Organizational Structure)
1. **Intercore** (kernel/L1) — Orchestration engine, Go CLI, SQLite
2. **Clavain** (OS/L2) — Reference autonomous software agency
3. **Interverse** (drivers/L2) — 33+ companion plugins (each solves one problem)
4. **Autarch** (apps/L3) — TUI surfaces (Bigend, Gurgeh, Coldwine, Pollard)
5. **Interspect** (cross-cutting) — Profiler + learning loop

### Three Architectural Layers + One Cross-Cutting Profiler

```
L3: Apps (Autarch)
    ↓ Interactive TUI surfaces; swappable without breaking layers below
    
L2: OS (Clavain) + Drivers (Interverse)
    ↓ Opinionated workflow: phases, gates, model routing, dispatch
    ↓ 33+ plugins, each independently installable
    
L1: Kernel (Intercore)
    ↓ Go CLI + SQLite WAL database (durable system of record)
    ↓ Runs, phases, gates, dispatches, events
    ↓ Mechanism, not policy
    
X-cutting: Profiler (Interspect)
    Reads kernel events → correlates with outcomes → proposes OS changes
    Never modifies kernel, only OS configuration (overlays)
```

### Survival Properties

Each layer can be replaced/rewritten without destroying layers beneath:
- Kernel outlives OS
- OS outlives host platform
- Apps outlive any rendering choice

This is deliberate architecture for a system that must survive the agent platform wars.

---

## 3. What Each Layer Does

### Layer 1: Kernel (Intercore)
**Provides:** Mechanism  
**Responsibility:** Runs, phases, gates, dispatches, events, state, locks, sentinels

- Go CLI binary (no daemon, no server)
- Every `ic` invocation opens database, does work, exits
- SQLite database is the system of record
- Kernel says "a gate can block a transition" but NOT "brainstorm requires an artifact" (that's policy)

### Layer 2: OS (Clavain)
**Provides:** Policy  
**Responsibility:** Development discipline

- Which phases comprise a sprint (discover → design → build → ship → reflect)
- What conditions must be met at each gate
- Which model to route each agent to
- When to advance automatically

Encodes opinions in gates, review agents, quality disciplines. Today ships as Claude Code plugin; architecture designed so opinions survive even if host platform doesn't.

### Layer 2: Drivers (Interverse — 33+ Plugins)
**Provides:** Capabilities  
**Responsibility:** One thing each, well

- **interflux** — Multi-agent document review + research
- **interlock** — Multi-agent file coordination (MCP)
- **intermute** — Coordination service (SQLite + HTTP/WebSocket)
- **interject** — Ambient discovery + research engine
- **tldr-swinton** — Token-efficient code context
- **intermux** — Agent activity visibility + tmux monitoring
- **intersynth** — Multi-agent synthesis engine (verdict aggregation)
- **interpeer** — Cross-AI peer review (Oracle escalation)
- **intertest** — Engineering quality disciplines (TDD, debugging)
- **interphase** — Phase tracking, gates, discovery
- Plus ~24 more

**Key principle:** Each driver is independently installable and valuable standalone. Without kernel = ephemeral state. With kernel = durability, coordination, event history.

### Layer 3: Apps (Autarch)
**Provides:** Surfaces  
**Responsibility:** Render kernel state into interactive TUI experiences

- **Bigend** — Monitoring/status
- **Gurgeh** — PRD generation
- **Coldwine** — Task orchestration
- **Pollard** — Research intelligence

Everything they do can be done via CLI. Convenience layer only.

### Cross-cutting: Profiler (Interspect)
**Provides:** Learning  
**Responsibility:** Adaptive improvement

- Reads kernel event stream
- Correlates dispatch outcomes with human signals (dismissals, overrides, corrections)
- Proposes changes to OS configuration (routing, agent selection, gates)
- Never modifies kernel (mechanical constraint)
- All modifications are safe, reversible overlays

---

## 4. Multi-Agent Coordination — Current Implementation

### The Stack

Three major systems handle coordination:

#### 4.1 Intermute (Core L1 Service)
**Type:** Go HTTP + WebSocket service  
**Port:** 7338  
**Database:** SQLite (intermute.db)  
**Role:** Central coordination hub

**What it manages:**
- Agent lifecycle (registration, heartbeats)
- Project-scoped messaging with threading
- Event sourcing of domain entities (specs, epics, stories, tasks, insights, sessions)
- Real-time delivery via WebSocket
- Durable system of record

**Key design:**
- **Composite PKs:** (project, id) for multi-tenancy
- **Append-only events table:** cursor=PK, type=(message.created|ack|read|heartbeat)
- **Materialized inbox_index:** Agent → [(cursor, message_id)] ordered by cursor
- **Thread indexing:** Tracks (project, thread_id, agent) → (last_cursor, message_count)
- **Authentication:** Localhost bypassed; non-localhost requires API key + project parameter

**API Endpoints:**
- Agent: `POST /api/agents`, `GET /api/agents?project=...`, `POST /api/agents/{id}/heartbeat`
- Messaging: `POST /api/messages`, `GET /api/inbox/{agent}?since_cursor=...`, ack/read endpoints
- Threads: `GET /api/threads?agent=...&cursor=...`, `GET /api/threads/{thread_id}`
- Domain: CRUD on specs, epics, stories, tasks, insights, sessions
- WebSocket: `WS /ws/agents/{agent_id}?project=...` for real-time streams

#### 4.2 Interlock (MCP Layer on Top of Intermute)
**Type:** Go MCP server + Bash hooks  
**Role:** Practical file coordination companion

**12 MCP Tools:**
1. `reserve_files` — Reserve patterns before editing (15min TTL)
2. `release_files` — Release reservations by ID
3. `release_all` — Release all active reservations for this agent
4. `check_conflicts` — Dry-run conflict check (no mutation)
5. `my_reservations` — List current active reservations
6. `send_message` — Direct message to another agent
7. `fetch_inbox` — Fetch inbox + check negotiation timeouts
8. `list_agents` — List active agents in project
9. `negotiate_release` — Request release with urgency + optional blocking wait
10. `respond_to_release` — Acknowledge (release) or defer with ETA
11. `force_release_negotiation` — Escalation: force-release after timeout
12. `request_release` — Legacy (deprecated)

**Negotiation Protocol (NEW):**
- `negotiate_release` sends message with `urgency` (normal/urgent) + generated `thread_id`
- `wait_seconds` enables blocking-wait: polls thread, returns `release`/`defer`/`timeout`
- `respond_to_release` handles both: `action='release'` or `action='defer'` with ETA
- `force_release_negotiation` escalates: force-releases after timeout exceeded
- Timeout thresholds: urgent=5min, normal=10min
- `CheckExpiredNegotiations` is **advisory-only** — reports but does NOT force-release

**5-Layer Defense (Coordination):**
1. **Convention** — Package ownership zones, beads `Files:` annotation
2. **Blocking edit hook** — `pre-edit.sh` blocks on exclusive conflict, auto-reserves (15min TTL)
3. **Per-session GIT_INDEX_FILE** — `GIT_INDEX_FILE=.git/index-$SESSION_ID` for independent staging
4. **Commit serialization** — `mkdir` atomicity (not flock, because flock releases when hook exits)
5. **Pre-commit validation** — Acquire lock → `git read-tree HEAD` → check reservations → release

**Hook Behaviors:**
- Post-commit: Refresh index → auto-release reservations for committed files → broadcast
- `CheckExpiredNegotiations` advisory-only (no force-release)
- `ReleaseByPattern` treats 404 as success (idempotent concurrent DELETE)

**Advisory-Only Enforcement Pattern:** Convert background state-mutating actors to read-only observers. Push mutation to edges. Let state owner make explicit decisions. Read-only code cannot race — eliminates entire TOCTOU class.

#### 4.3 MCP-Agent-Mail (Research/Future Integration)
**Type:** MCP server (separate from intermute)  
**Status:** Research project in `/research/mcp_agent_mail/`  
**Purpose:** Agent-to-agent messaging + coordination

**Current state:**
- Separate implementation with Docker support
- Agent-friendliness report generated
- AGENTS.md with full documentation
- Deployment configs (systemd, logrotate)
- Schema + SQL design

**Relation to intermute:**
- MCP-agent-mail is a **parallel research project** exploring additional messaging capabilities
- Not yet integrated into main Demarch workflow
- Could complement or eventually replace parts of intermute's messaging API
- Design explores how to make coordination more agent-friendly

### Coordination Data Flow

```
Claude Code Session (Agent A)
    ↓
interlock-mcp (Go server)
    ↓ (HTTP/Unix socket)
intermute (port 7338)
    ↓ (SQLite writes)
    ├→ messages table (sender, recipients, body, thread_id)
    ├→ events table (append-only: type=message.created|ack|read|heartbeat)
    ├→ agents table (registry: id, session_id, name, project, capabilities[], metadata)
    ├→ inbox_index (materialized view: agent → messages ordered by cursor)
    ├→ thread_index (participant tracking: who's in this thread)
    └→ reservations table (exclusive/shared file patterns with TTL)
    ↓ (WebSocket broadcast)
Claude Code Session (Agent B)
Claude Code Session (Agent C)
```

**Real-time delivery:**
- Agents subscribe to `WS /ws/agents/{agent_id}?project=...`
- Hub broadcasts when messages created/acked/read
- Negotiation thread updates broadcast to participants

**Async coordination pattern:**
- Agent A calls `negotiate_release` → creates message in thread
- intermute broadcasts to all agents in thread
- Agent B receives via WebSocket
- Agent B calls `respond_to_release` with `action=release` or `action=defer`
- intermute updates thread, broadcasts response
- If `wait_seconds` set, Agent A's `negotiate_release` unblocks with result

---

## 5. Design Principles Across All Layers

### Mechanism over Policy
- Kernel provides primitives (phases, gates, transitions)
- OS provides opinions (which phases, what conditions)
- Drivers provide capabilities (what each solves)
- Flexible: documentation project uses `draft → review → publish`; hotfix uses `triage → fix → verify`

### Durable over Ephemeral
- If it matters, it's in the database
- SQLite with WAL mode for all critical state
- Processes crash, sessions end, networks drop — state survives
- Any session/agent can query true state at any time

### Compose through Contracts
- Small, focused tools beat large integrated platforms
- Unix philosophy: each companion does one thing well
- Boundaries explicit: typed interfaces, schemas, manifests, declarative specs
- Naming reflects this: **inter-\*** occupies the space *between* things

### Independently Valuable
- Install interflux for review, tldr-swinton for context, interlock for coordination
- No Clavain, no Intercore required
- Drivers degrade gracefully: ephemeral state alone, enhanced with kernel

### Human Attention is the Bottleneck
- Agents are cheap, human focus is scarce
- System optimizes for human's time, not agent's
- Multi-agent output presented for rapid confident review, not just cheap review
- Human drives strategy; agency drives execution

### Discipline before Speed
- Quality gates matter more than velocity
- Agents without discipline ship slop
- Gates are kernel-enforced invariants, not prompt suggestions
- Resolve all open questions before execution (ambiguity costs during building)

### Self-Building as Proof
- Every capability must survive contact with its own development process
- Clavain builds Clavain
- Credibility engine: system autonomously building itself is more convincing than benchmarks

---

## 6. Development Lifecycle & Autonomy Ladder

### Five Macro-Stages

1. **Discover** — Research, brainstorming, problem definition
2. **Design** — Strategy, specification, planning, plan review
3. **Build** — Implementation and testing
4. **Ship** — Final review, deployment, knowledge capture
5. **Reflect** — Document patterns, mistakes, decisions, complexity calibration

Each produces typed artifacts that become next stage's input. Kernel enforces handoff via `artifact_exists` gates.

### Autonomy Levels

- **L0: Record** — Kernel records what happened; human drives everything
- **L1: Enforce** — Gates evaluate real conditions; run cannot advance without meeting preconditions
- **L2: React** — Events trigger automatic reactions; phase transitions spawn agents
- **L3: Auto-remediate** — System retries failed gates, substitutes agents, adjusts parameters
- **L4: Auto-ship** — System merges and deploys when confidence thresholds met

No level is self-promoting. System advances only when outcome data justifies it.

---

## 7. Frontier Axes & North Star Metric

### Three Axes (Interconnected by Interspect Flywheel)

| Axis | Measured By | Goal |
|------|-----------|------|
| **Autonomy** | Sprint completion rate, gate pass rate, intervention frequency | Reduce human babysitting; human operates at strategic level |
| **Quality** | Defect escape rate, review signal precision, actionable findings ratio | Catch defects early, before Ship; minimize false positives |
| **Token efficiency** | Tokens per landable change, cost per actionable finding, agent utilization | Outcomes per dollar, not just cheap (cheap+wrong is worthless) |

### North Star Metric

**"What does it cost to ship a reviewed, tested change?"**

The metric where all three axes collapse into one number. Requires all three:
- Autonomy (sprint ran without babysitting)
- Quality (change landed without rework)
- Efficiency (right models/agents selected, not most expensive)

### Interspect Learning Loop

```
More autonomy → More outcome data
                    ↓
         Better routing and review
                    ↓
         Lower cost
                    ↓
More autonomy ← Enables more sprints
```

Concrete improvements:
- Model downgrades where Haiku catches same issues as Opus (30x cheaper) → **cheaper**
- Agent retirement where reviewer produces findings no one acts on → **less noise**
- Gate relaxation where check always passes → **faster**
- Context overlays reducing false positives → **more signal**

---

## 8. Gaps in Current Coordination Story

### Known Gaps & Future Work

#### 8.1 Multi-Project Portfolio Orchestration (In Progress)
**Status:** Kernel primitives landed, shipping next  
**Gap:** Current system handles single project well; multi-project coordination partially designed  
**What's needed:**
- Token budget enforcement across projects
- Dependency tracking between projects (changes in one trigger verification in dependents)
- Cross-project dispatch routing
- Portfolio-level reporting

#### 8.2 Interspect Phase 2: Overlays & Canary Alerting (Designed, Not Shipped)
**Status:** Phase 1 (evidence collection) shipped; Phase 2 designed  
**Gap:** Evidence collected but no configuration changes proposed/applied yet  
**What's needed:**
- Context overlay system (feature-flag files layered onto agent prompts)
- Routing override system (per-project agent exclusions)
- Canary monitoring (watch metrics across 20-use window, alert on degradation)
- Propose mode (collect evidence, propose changes, let human approve)

#### 8.3 Interspect Phase 3: Autonomy & Eval Corpus (Future)
**Status:** Designed but not shipped  
**Gap:** No counterfactual evaluation of proposed changes  
**What's needed:**
- Shadow evaluation (run candidates on real traffic before auto-apply)
- Privilege separation (proposer can't write repo, only staged artifacts)
- Eval corpus from production reviews
- Prompt tuning capability (overlay-based, not direct edits)

#### 8.4 MCP-Agent-Mail Integration (Research)
**Status:** Separate research project; not yet integrated  
**Gap:** Currently intermute handles all messaging; separate MCP server explores agent-friendliness improvements  
**What's needed:**
- Decision: merge MCP-agent-mail into intermute, or keep as complementary service?
- Agent-friendly API surface validation
- Integration testing with Clavain/Interlock workflows
- Performance characteristics under parallel multi-agent load

#### 8.5 Agency Specs & Fleet Registry (Track C, Planned)
**Status:** Designed but not shipped  
**Gap:** No declarative agency definitions; hard to compose agents, difficult to reason about cost/quality tradeoffs  
**What's needed:**
- Declarative agency spec format (agents, roles, capabilities, model assignments)
- Fleet registry with cost/quality profiles per agent
- Budget-constrained fleet composition
- Cross-phase handoff protocol (how artifacts flow between phases)
- Clavain using its own specs to run its own development sprints (C5 convergence)

#### 8.6 Static vs Adaptive Routing (Model Selection)
**Status:** Static and complexity-aware (C1-C5) routing shipped; outcome-driven selection next  
**Gap:** Routing not yet data-driven; Interspect can't yet propose model downgrades  
**What's needed:**
- Interspect proposal engine for routing changes (use outcome data to justify downgrades)
- Shadow A/B testing for routing hypotheses
- Cross-phase routing coherence (consistency across brainstorm, plan, build, ship)

#### 8.7 Cross-AI Validation & Oracle Integration (Partial)
**Status:** interpeer plugin ships Oracle escalation path; limited production use  
**Gap:** Oracle expensive; need better signal for when escalation is worth it  
**What's needed:**
- Evidence-driven Oracle dispatch (only escalate when other reviews conflict/uncertain)
- Oracle as last-mile quality gate (not routine checks)
- Cost-benefit analysis of escalation (when does Oracle ROI exceed cost?)

#### 8.8 Test-Driven Development Enforcement (In Progress)
**Status:** TDD agents exist; not yet first-class phase gate  
**Gap:** Tests optional within Build phase; can be skipped  
**What's needed:**
- TDD as mandatory first substep in Build (write failing test first)
- Test coverage gates at Ship phase
- Automated coverage regression detection

#### 8.9 Ambient Discovery at Scale (Partial)
**Status:** Kernel primitives for discovery shipped; routing through confidence tiers works  
**Gap:** Interest profile learning not yet adaptive  
**What's needed:**
- Human promotion/dismissal signal amplification (user gives few signals, system infers intent)
- Source reputation learning (which sources consistently produce relevant findings?)
- Thresholds adapting based on false positive rate feedback

#### 8.10 Codex/GPT-5/Gemini Parity (Track B, Partial)
**Status:** Static model routing shipped; no multi-model testing harness  
**Gap:** Hard to validate that Codex parallel impl matches Claude quality  
**What's needed:**
- Codex syntax/logic validation parity tests
- GPT-5.2 Pro Oracle integration (validation layer)
- Gemini long-context validation (when to use vs when not to)
- Unified eval harness across all three models

---

## 9. Summary: Demarch's Coordination Story

### The Completed Stack
1. **Kernel (Intercore)** — Runs, phases, gates, dispatches, events all persisted
2. **OS (Clavain)** — Sprint phases, routing, review agents
3. **Drivers (Interverse)** — 33+ independent plugins; interlock/intermute handle coordination
4. **Profiler (Interspect)** — Evidence collection shipping; proposals designed
5. **File Coordination (Interlock)** — 5-layer defense with negotiation protocol
6. **Messaging (Intermute)** — Durable coordination service with real-time delivery
7. **MCP Research (MCP-agent-mail)** — Separate exploration of agent-friendly messaging

### How Coordination Currently Works
- Agents register with intermute, reserve files via interlock
- Pre-edit hook warns about conflicts (advisory only)
- Pre-commit hook blocks commits with reserved files (mandatory)
- Negotiation protocol allows graceful coordination without hard locks
- Interspect watches outcomes but doesn't yet propose changes

### What's Missing
1. **Outcome-driven routing** — Interspect not yet proposing model downgrades
2. **Multi-project budgeting** — Primitives exist but not orchestrated
3. **Overlay system** — Evidence collected but no safe configuration changes
4. **Shadow evaluation** — Proposed changes not yet validated before auto-apply
5. **Agency specs** — No declarative definitions of agent teams
6. **Cross-AI validation** — Oracle exists but not yet smartly integrated

### Convergence Vision
Track C (Agency Architecture) is the next frontier: declarative specs, budget-aware composition, cross-phase handoffs, and the convergence point where Clavain uses its own specs to build itself (C5). This closes the self-building loop and proves the entire system works.

