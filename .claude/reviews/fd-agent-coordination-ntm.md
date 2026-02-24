# NTM Agent Coordination: Competitive Analysis for Demarch

**Date:** 2026-02-22
**Scope:** `/home/mk/projects/Demarch/research/ntm/internal/` -- coordinator, swarm, ensemble, supervisor, agentmail, handoff, scheduler, assignment, pipeline, workflow, approval, policy modules
**Purpose:** Identify coordination patterns worth adopting to strengthen Demarch's Intercore kernel, interlock, intermux, and agent-mail systems.

---

## 1. Architecture Overview

NTM (Neural Turing Machine) is a Go-based multi-agent orchestrator that coordinates Claude Code (`cc`), Codex (`cod`), and Gemini (`gmi`) agents running in parallel tmux panes. Its coordination stack is layered:

```
Pipeline/Workflow (declarative YAML orchestration)
    |
Ensemble (multi-reasoning-mode analysis + synthesis)
    |
Coordinator (real-time monitoring, assignment, conflicts)
    |
Swarm (tmux session/pane lifecycle, respawn, limits)
    |
Scheduler (rate-limited spawn queue with fair scheduling)
    |
Agent Mail (MCP-based inter-agent messaging + file reservations)
    |
Supervisor (daemon lifecycle: health, restart, port allocation)
```

Demarch's equivalent stack: Clavain (orchestration OS) -> Intercore (kernel) -> Interlock + Agent-Mail (coordination) -> Intermux (visibility). The key difference: NTM is a single monolithic Go binary with all layers tightly integrated; Demarch is a plugin ecosystem where each concern is a separate module.

---

## 2. Coordination Patterns Worth Adopting

### 2.1 Multi-Factor Assignment Scoring (HIGH VALUE)

**NTM pattern:** `coordinator/assign.go` implements `ScoreAndSelectAssignments()` which scores every possible agent-task combination using a weighted multi-factor breakdown:

```
TotalScore = BaseScore
           + AgentTypeBonus      (agent-task complexity match)
           + CriticalPathBonus   (PageRank/blocker graph centrality)
           + ProfileTagBonus     (agent persona tag overlap)
           + FocusPatternBonus   (file pattern affinity)
           - FileOverlapPenalty  (existing reservation count)
           - ContextPenalty      (context window exhaustion)
```

Then it uses a greedy selection algorithm: sort all candidates by score, pick top unassigned pairs ensuring no agent or task is double-assigned.

**Key details:**
- Agent-type matching: Claude gets +15% for complex epics/features, Codex +15% for simple fixes, Gemini small bonus for medium complexity
- Task complexity estimation from bead type (epic > feature > bug > task > chore), priority, and unblock-count
- Context penalty ramps when usage > 80% (configurable threshold)
- Profile-based routing uses persona tag matching and file focus patterns
- Five strategies: `balanced`, `speed`, `quality`, `dependency`, `round-robin`

**Demarch gap:** Interlock handles file reservations but has no multi-factor scoring for work assignment. The agent-mail MCP has `reserve_files` and `send_message` but no automated assignment engine.

**Recommendation:** Build a scoring engine in Intercore that considers agent capabilities (model strengths), current context usage, file reservation overlap, and dependency-graph centrality when routing work. This is the single highest-value pattern to adopt.

### 2.2 Real-Time Agent State Machine (HIGH VALUE)

**NTM pattern:** `coordinator/coordinator.go` runs a poll-based monitor loop (default 5s) that:
1. Calls `tmux.GetPanesWithActivity()` -- single tmux call for all panes
2. Parallel-captures pane output (50 lines each, 2s timeout per pane)
3. Feeds output to `UnifiedDetector` (pattern matching) and `ActivityMonitor` (velocity tracking)
4. Updates agent state map with transitions: `Waiting -> Generating -> Thinking -> Error -> Stalled`
5. Emits typed events on state transitions: `agent_idle`, `agent_busy`, `agent_error`, `agent_recovered`

The state machine enables automatic work assignment (assign to idle agents), conflict detection, and digest generation.

**Key detail:** The optimized path (`GetAgentStatusWithOutput`) avoids redundant tmux captures by passing pre-captured output through the pipeline. This is critical for scaling -- NTM can monitor 20+ panes without tmux call explosion.

**Demarch gap:** Intermux provides visibility (peek, activity feed, who-is-editing) but the state transitions are not formalized into an event-driven machine that triggers automatic actions.

**Recommendation:** Formalize agent state as a state machine in Intercore with event emission. This becomes the foundation for automated assignment, respawn, and health alerting.

### 2.3 Conflict Detection + Negotiation Protocol (MEDIUM VALUE)

**NTM pattern:** `coordinator/conflicts.go` implements a three-tier conflict handling system:

1. **Detection:** `ConflictDetector.DetectConflicts()` queries all active reservations via Agent Mail, groups by pattern, flags any pattern with 2+ holders
2. **Notification:** `NotifyConflict()` sends markdown messages to all holders describing the conflict and suggesting resolution options
3. **Negotiation:** `NegotiateConflict()` identifies the lowest-priority holder and sends them a structured request to release, with options: Release / Keep / Coordinate

The conflict includes glob pattern matching (`matchesPattern`) supporting exact, prefix, single-star, and double-star patterns.

**Demarch gap:** Interlock's `check_conflicts` and `negotiate_release` cover similar ground, but the priority-based automatic negotiation (lowest-priority holder gets asked first) and the three-option negotiation protocol are more structured.

**Recommendation:** Add priority-weighted negotiation to interlock's release protocol. When conflicts arise, automatically target the lowest-priority holder rather than requiring manual selection.

### 2.4 Session Handoff with Reservation Transfer (HIGH VALUE)

**NTM pattern:** `handoff/types.go` + `handoff/transfer.go` define a YAML-based handoff format (~400 tokens) that preserves:
- Goal + Now (required fields for continuity)
- Completed tasks with file lists
- Blockers, questions, decisions, findings
- Token context (used/max/percentage)
- **Reservation transfer instructions** with from-agent, to-agent, TTL, grace period

The `TransferReservations()` function implements a careful protocol:
1. Release old agent's reservations
2. Attempt reservation for new agent (with exclusive/shared distinction)
3. On conflict: wait grace period (2s default), retry once
4. On persistent conflict: **roll back** to old agent's reservations for approximate atomicity

**Demarch gap:** Agent-mail has `release_file_reservations` and `reserve_files` but no atomic transfer protocol with rollback semantics. Handoff context is ad-hoc rather than structured.

**Recommendation:** Implement reservation transfer as a first-class operation in agent-mail MCP with rollback semantics. This is essential for session rotation (context exhaustion) without losing file locks.

---

## 3. Inter-Agent Communication Design

### 3.1 NTM's Agent Mail vs Demarch's Agent-Mail MCP

Both systems use the same underlying `mcp-agent-mail` server. NTM wraps it with a Go HTTP client (`agentmail/client.go`) while Demarch accesses it via MCP tool calls.

**NTM's client features:**
- HTTP client with bearer token auth, 10s/30s timeouts
- Availability caching with 30s TTL and thundering-herd protection (mutex + double-check)
- `HasArchive()` fallback detection when HTTP unavailable (checks `~/.mcp_agent_mail_git_mailbox_repo`)
- `FlexTime` wrapper handling bare ISO8601 timestamps without timezone
- Structured types for Agent, Message, FileReservation, ContactLink, ThreadSummary

**Communication patterns used:**
- **Work Assignment messages** with structured markdown: bead ID, title, priority, score, reasons, impact, step-by-step instructions, ack-required
- **Conflict negotiation messages** with three clear options
- **Digest summaries** sent periodically to human agent with agent status, alerts, work summary
- Messages use `importance: "high"` for conflicts and `ack_required: true` for assignments

**Demarch difference:** Agent-mail MCP provides the same primitives but communication patterns are defined by plugins (interlock for conflicts, agent-mail for general messaging). There is no centralized communication protocol defining message formats for assignment, negotiation, or digests.

**Recommendation:** Define canonical message schemas in Intercore for common coordination patterns (assignment, conflict, digest, handoff). This allows any plugin to produce/consume structured coordination messages.

### 3.2 Digest System

NTM's coordinator generates periodic digests (`DigestSummary`) sent to the configured human agent via Agent Mail:
- Agent count, active/idle/error breakdown
- Per-agent status with context usage and idle duration
- Alerts for error states, stalled agents, high context (>85%)
- Work summary: pending, in-progress, completed today, blocked, top ready items

**Demarch gap:** Intermux provides `activity_feed` and `peek_agent` but no automated digest generation. Intercheck does session health monitoring but doesn't produce periodic human-readable summaries.

**Recommendation:** Add a digest generator to Intermux or Intercore that periodically summarizes swarm health and sends it via agent-mail.

---

## 4. Swarm/Ensemble Orchestration

### 4.1 Tiered Resource Allocation

**NTM pattern:** `swarm/allocation.go` implements a tiered allocation calculator:
- Projects are sorted by open bead count (highest priority first)
- Three tiers based on configurable thresholds determine agent allocation per project
- Per-tier allocation specifies cc/cod/gmi agent counts
- `GenerateSwarmPlan()` produces a complete execution plan with session specs and pane specs

This maps directly to a `SwarmPlan` with `SessionSpec[]` containing `PaneSpec[]`, ready for the `SessionOrchestrator` to create tmux sessions.

**Demarch gap:** No automatic resource allocation based on work volume. Agent count per project is manually configured.

### 4.2 Ensemble Reasoning Modes (UNIQUE TO NTM)

**NTM pattern:** `ensemble/` is NTM's most distinctive feature. It implements a **reasoning mode taxonomy** with 12 categories (Formal, Ampliative, Uncertainty, Vagueness, Change, Causal, Practical, Strategic, Dialectical, Modal, Domain, Meta) and three maturity tiers (core, advanced, experimental).

Each reasoning mode has:
- Preamble injection (prompt template that sets the agent's reasoning approach)
- Best-for lists, failure modes, differentiators
- Category letter codes (A1, B3, etc.)

The **EnsembleManager** lifecycle:
1. Spawn: create tmux session with panes per mode
2. Assign: map modes to agent panes (round-robin, affinity, category, explicit)
3. Inject: send preamble + question to each agent
4. Collect: capture outputs from each pane
5. Synthesize: combine outputs using one of 10 strategies

**Synthesis strategies:** manual, adversarial, consensus, creative, analytical, deliberative, prioritized, dialectical, meta-reasoning, argumentation-graph. Each strategy has metadata about whether it needs a synthesizer agent, what mode that agent should use, and what the output emphasizes.

**Demarch relevance:** Demarch's intersynth (multi-agent synthesis engine) and interlens (cognitive augmentation lenses) could adopt the formal taxonomy of reasoning modes and the multi-strategy synthesis approach. The NTM ensemble system is significantly more developed.

**Recommendation:** Study NTM's ensemble types and synthesis strategies as a reference design for intersynth. The taxonomy (12 categories x 3 tiers) and the pluggable synthesis strategy pattern are architecturally clean.

### 4.3 Auto-Respawner with Account Rotation

**NTM pattern:** `swarm/auto_respawner.go` handles automatic agent recovery:
- `LimitDetector` monitors panes for usage limit patterns (rate limits, context exhaustion)
- On limit hit: graceful exit (2s), clear pane, respawn agent
- Optional `AccountRotator` switches API accounts on limit hit
- `PromptInjector` re-sends marching orders after respawn
- Retry limits per pane (default 3, reset after 1 hour)
- Adaptive delay learning from rate limit events

The respawn pipeline: detect limit -> kill agent -> rotate account (optional) -> respawn in same pane -> inject marching orders -> verify ready

**Demarch gap:** No automatic respawn-on-limit. Agents that hit limits require manual intervention.

**Recommendation:** Build a respawn capability into Intermux or Intercore that detects context exhaustion and automatically rotates agents, carrying forward the handoff context.

---

## 5. Safety/Approval Gates

### 5.1 Destructive Command Policy

**NTM pattern:** `policy/policy.go` implements a three-tier YAML-based command policy:
1. **Allowed** (checked first): explicitly safe commands (e.g., `git push --force-with-lease`)
2. **Blocked** (checked second): dangerous commands blocked entirely (e.g., `git reset --hard`, `rm -rf /`)
3. **Approval Required** (checked third): potentially dangerous commands requiring human approval (e.g., `git rebase -i`, `force_release`)

Rules use regex patterns and can require SLB (two-person rule) for the most sensitive operations.

The `AutomationConfig` controls:
- `auto_push: false` (require explicit push)
- `auto_commit: true` (allow auto-commit)
- `force_release: "approval"` (require approval for force-releasing another agent's reservation)

### 5.2 Approval Engine

**NTM pattern:** `approval/engine.go` implements a full approval workflow:
- Requests with expiry (default 24h), correlation IDs, SLB requirement flag
- State machine: pending -> approved/denied/expired
- Event emission on approval lifecycle
- SLB integration: routes to external two-person-rule system when available, graceful fallback to internal approvals
- Notification on request and decision
- Blocking wait with channel-based completion notification

**Demarch gap:** Interlock has file reservation negotiation but no general-purpose approval engine. There is no destructive command policy system.

**Recommendation:**
1. Add a policy file (`.demarch/policy.yaml`) with allowed/blocked/approval-required command patterns
2. Build a lightweight approval engine in Intercore for sensitive operations (force-release, destructive git, production deployment)
3. The SLB pattern (two-person rule with graceful fallback) is worth adopting for force-release scenarios

---

## 6. Scheduling and Work Assignment

### 6.1 Fair Scheduler with Rate Limiting

**NTM pattern:** `scheduler/scheduler.go` implements a sophisticated spawn scheduler:
- **Priority queue** with fair scheduling across agent types
- **Global rate limiter** preventing spawn storms
- **Per-agent-type rate limiters** (different limits for cc/cod/gmi)
- **Per-agent concurrency caps** limiting simultaneous spawns per type
- **Backoff controller** with exponential backoff on resource errors
- **Headroom guard** checking CPU/memory before spawning (pre-spawn resource check)
- **Job lifecycle hooks:** enqueued, started, completed, failed, retrying, backpressure, guardrail-triggered
- **Batch submission** with batch cancellation
- **Backpressure detection** with configurable threshold (default 50 queued jobs)

The scheduler runs 4 concurrent worker goroutines (configurable) that pull from the fair queue, check rate limits and headroom, then execute.

**Demarch gap:** No spawn scheduler. Agent creation is direct. No rate limiting, backoff, or headroom checking.

**Recommendation:** Implement a spawn scheduler in Intercore with:
- Rate limiting (global + per-agent-type)
- Backoff on API errors
- Headroom guard (at minimum, check tmux pane count and process count)
- Job lifecycle hooks for observability

### 6.2 Assignment Store with State Machine

**NTM pattern:** `assignment/store.go` provides persistent bead-to-agent assignment tracking:
- States: `assigned -> working -> completed/failed/reassigned`
- Invalid state transitions are rejected with typed errors
- Persisted to `~/.ntm/sessions/<session>/<bead_id>.json`
- Thread-safe with read-write mutex
- Event emission on state changes

**Demarch gap:** Agent-mail tracks messages and reservations but there is no centralized assignment registry mapping work items to agents.

**Recommendation:** Build an assignment store in Intercore (or extend beads) that tracks which agent is working on what, with a formal state machine. This is essential for answering "who is working on what?" and detecting orphaned work.

---

## 7. Pipeline/Workflow Orchestration

### 7.1 Declarative Workflow Engine

**NTM pattern:** `pipeline/` implements a YAML-based workflow engine with:
- **Steps** with agent selection (by type, pane index, or routing strategy: least-loaded, first-available, round-robin)
- **Dependencies** (`depends_on` between steps) with a full dependency graph and validation
- **Parallel execution** (parallel step groups)
- **Loops** (for-each, while, times) with safety limits, collect, and break/continue
- **Conditionals** (`when` expressions with variable interpolation)
- **Variables** with types, defaults, and output parsing (json, yaml, lines, regex)
- **Error handling** per-step: fail, fail-fast, continue, retry (with linear/exponential backoff)
- **Wait conditions:** completion (idle detection), time-based, fire-and-forget
- **State persistence** for resume after crash
- **Notifications** on complete/error via desktop, webhook, or agent mail

The `Executor` runs workflows with global timeout, progress events, and resumable state.

### 7.2 Workflow Templates

**NTM pattern:** `workflow/template.go` defines reusable multi-agent patterns:
- **Coordination types:** ping-pong, pipeline, parallel, review-gate
- **Flow config** as a state machine with transitions triggered by: file_created, file_modified, command_success, command_failure, agent_says, all_agents_idle, manual, time_elapsed
- **Approval mode** within flows: any, all, quorum

**Demarch gap:** Clavain provides brainstorm-to-ship orchestration but no declarative YAML workflow engine. Interphase tracks phase gates but doesn't define executable workflow schemas.

**Recommendation:** The full pipeline engine is complex to replicate, but the workflow template concept (named patterns with coordination type and trigger-based transitions) is worth adopting in Intercore. Start with the coordination types (ping-pong, pipeline, parallel, review-gate) as first-class primitives.

---

## 8. Patterns That Would Strengthen Intercore

Ranked by impact and implementation complexity:

| Priority | Pattern | Source Module | Intercore Impact |
|----------|---------|---------------|------------------|
| P0 | Multi-factor assignment scoring | coordinator/assign.go | Automated work routing |
| P0 | Agent state machine with events | coordinator/coordinator.go | Foundation for all automation |
| P0 | Reservation transfer with rollback | handoff/transfer.go | Session rotation without lock loss |
| P1 | Fair spawn scheduler with headroom | scheduler/scheduler.go | Prevent resource exhaustion |
| P1 | Approval engine with SLB | approval/engine.go | Safety gates for autonomous ops |
| P1 | Assignment store with state machine | assignment/store.go | Work tracking and orphan detection |
| P1 | Destructive command policy | policy/policy.go | Prevent catastrophic operations |
| P2 | Auto-respawner with account rotation | swarm/auto_respawner.go | Autonomous recovery from limits |
| P2 | Periodic digest generation | coordinator/digest.go | Human oversight without polling |
| P2 | Conflict negotiation protocol | coordinator/conflicts.go | Automated conflict resolution |
| P3 | Ensemble reasoning taxonomy | ensemble/types.go | Reference for intersynth design |
| P3 | Declarative workflow engine | pipeline/executor.go | Complex orchestration patterns |

---

## 9. Key Architectural Differences

| Dimension | NTM | Demarch |
|-----------|-----|---------|
| Architecture | Monolithic Go binary | Plugin ecosystem (MCP + hooks) |
| Agent communication | HTTP client to Agent Mail | MCP tool calls to Agent Mail |
| State management | In-process maps + file persistence | Distributed per-plugin state |
| Coordination | Centralized coordinator | Distributed across interlock/intermux/agent-mail |
| Workflow | YAML pipeline engine | Clavain orchestration OS |
| Ensemble | Built-in reasoning mode taxonomy | Separate intersynth + interlens plugins |
| Scheduling | Built-in fair scheduler | None (direct spawning) |
| Safety | Policy file + approval engine | Per-plugin guards (intercheck) |

**NTM's monolithic advantage:** Everything is in one process, so cross-cutting concerns (scheduling + assignment + conflict detection + respawn) can share state cheaply. State transitions are atomic within a mutex.

**Demarch's plugin advantage:** Each concern is independently deployable and testable. New coordination patterns can be added without modifying a kernel binary. The MCP protocol enables heterogeneous agent participation.

**Bridging strategy:** Intercore should be the "thin coordinator" that provides the event bus, state machine, and scoring engine, while delegating implementation details to plugins. NTM's tightly-coupled design is effective but fragile -- Demarch's plugin model is the right architecture, but it needs Intercore to provide the coordination primitives that NTM gets from being monolithic.

---

## 10. Summary

NTM's coordination layer is mature and well-engineered, particularly in three areas where Demarch currently has gaps:

1. **Automated work assignment** with multi-factor scoring (agent capability, context usage, file overlap, dependency centrality, persona affinity)
2. **Formal agent lifecycle management** (state machine, health monitoring, automatic respawn, account rotation, handoff with reservation transfer)
3. **Safety infrastructure** (destructive command policies, approval workflows with SLB, headroom guards)

The highest-value adoptions for Demarch are: (a) the assignment scoring engine as an Intercore primitive, (b) agent state machine with event emission, and (c) reservation transfer with rollback semantics in agent-mail. These three together would give Demarch's distributed plugin architecture the coordination intelligence that NTM gets from its monolithic design.
