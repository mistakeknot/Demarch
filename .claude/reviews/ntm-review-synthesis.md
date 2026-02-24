# NTM Competitive Analysis — Synthesis Report

**Date:** 2026-02-22
**Reviewed by:** Flux-drive Multi-Agent Review Engine (5 agent outputs synthesized)
**Target Codebase:** ntm (Go CLI/TUI, 256k LOC, 1,442 files)
**Purpose:** Identify patterns, products, and anti-patterns for Demarch/Autarch adoption

---

## Executive Summary

ntm is a mature multi-agent orchestration platform that manages Claude Code, Codex, and Gemini agents across tmux sessions. Its codebase spans 80+ internal packages organized in three clear layers: Infrastructure (tmux, config, state, events), Orchestration (swarm, coordinator, ensemble, supervisor), and Delivery (CLI, robot API, TUI).

**Key Finding:** ntm's greatest strength is not any single feature, but its comprehensive coordination infrastructure. It handles work assignment, agent lifecycle, context management, safety gates, audit trails, and human-in-the-loop workflows as first-class primitives. Demarch's plugin architecture gains sophistication by adopting these patterns.

**Deduplication Note:** The five agent reviews converge on the same top patterns with consistent ranking. This synthesis prioritizes by (value × feasibility) and groups by adoption timeframe (P0/P1/P2/P3).

---

## Part 1: Top 10 Highest-Leverage Takeaways

### 1. **Multi-Factor Assignment Scoring Engine (P0 — Copy Now)**

**Value:** 9/10 | **Effort:** 8/10 | **Leverage:** High
**Convergence:** 5/5 agents flagged this as critical

**Pattern:** Score every agent-task pair using weighted factors:
- Agent-type bonus (Claude: complex, Codex: simple, Gemini: medium)
- Critical path centrality (PageRank over bead dependency graph)
- Profile tag affinity (persona match)
- File focus overlap (agent specialization)
- Context penalty (ramp at 80%+ usage)
- File reservation penalty (existing locks)

**Implementation in Demarch:**
- Build in Intercore as `AssignmentScorer` interface
- Integrate with bv (graph engine) for centrality calculation
- Agent capabilities come from agent-mail profiles
- File reservations queried from interlock

**Why now:** This is the single highest-impact automation primitive. Without it, work assignment remains manual or round-robin, which wastes context windows and delays work.

**Implementation sketch:**
```
func (s *Scorer) ScoreAssignment(agent *Agent, bead *Bead) float64 {
    base := s.taskComplexityScore(bead)
    base += s.agentTypeBonus(agent, bead)
    base += s.criticalPathBonus(bead, allBeads)
    base -= s.contextPenalty(agent)
    base -= s.fileOverlapPenalty(agent, bead)
    return base
}
```

---

### 2. **Tamper-Evident Audit Trail (P0 — Copy Now)**

**Value:** 10/10 | **Effort:** 8/10 | **Leverage:** Critical for compliance
**Convergence:** 5/5 agents flagged as highest priority

**Pattern:** Hash-chain audit logging with:
- SHA-256 hash-chain (each entry includes `prev_hash` and `checksum`)
- Monotonic sequence numbers per session (gap detection)
- JSONL append-only storage (crash-safe)
- Automatic pre-write redaction (secrets never logged)
- Integrity verification (`VerifyIntegrity()` walks chain and validates hashes)

**Demarch targets:**
- Intercore session events
- Interlock file reservations/releases
- Agent-mail message routing
- Clavain orchestration steps

**Why now:** Any multi-agent system handling production code requires non-repudiation. This is a legal/compliance requirement, not optional.

**Implementation sketch:**
```
type AuditEntry struct {
    Timestamp   time.Time
    SessionID   string
    EventType   string              // "reserve", "release", "send", "approve"
    Actor       string              // agent or user
    Target      string              // file path or operation
    Payload     map[string]interface{}
    PrevHash    string
    Checksum    string              // SHA256(omit_checksum_field)
    SequenceNum uint64
}

func (a *AuditLog) Append(entry AuditEntry) error {
    prev, _ := a.lastEntry()
    entry.PrevHash = prev.Checksum
    entry.Checksum = computeChecksum(entry)
    // persist JSONL
}

func (a *AuditLog) VerifyIntegrity() error {
    // walk all entries, validate chain
}
```

---

### 3. **Redaction Engine — Secret Detection & Deterministic Placeholder (P0 — Copy Now)**

**Value:** 9/10 | **Effort:** 6/10 | **Leverage:** High
**Convergence:** 5/5 agents flagged this as highest priority shared library

**Pattern:** Four redaction modes (off, warn, redact, block) with:
- 13 secret categories (OpenAI, Anthropic, GitHub, AWS, JWT, database URLs, etc.)
- Priority-based deduplication (provider-specific patterns > generic patterns)
- Deterministic placeholders: `[REDACTED:CATEGORY:hash8]` (enables audit correlation without exposing secret)
- Allowlist support (suppress known false positives)
- Line/column enrichment (source location tagging)

**Why now:** Every component that logs, transmits, or persists text should run through redaction. Demarch must build this in from day one, not retrofit it.

**Demarch integration points:**
- Agent-mail message routing (redact before inter-agent transmission)
- Intercore event bus (redact before persistence)
- Intercheck code quality guards (redact before reporting)
- Intermux activity feeds (redact before display)

**Reference implementation exists:** Port `/home/mk/projects/Demarch/research/ntm/internal/redaction/` directly as `core/redaction/` Go package.

---

### 4. **Reservation Transfer with Rollback Semantics (P0 — Copy Now)**

**Value:** 9/10 | **Effort:** 7/10 | **Leverage:** Critical for session rotation
**Convergence:** 4/5 agents flagged this

**Pattern:** Atomic handoff of file locks between agents:
1. Release old agent's reservations
2. Attempt exclusive reservation for new agent
3. On conflict: wait grace period (2s), retry once
4. On persistent conflict: rollback to old reservations

**Demarch target:** agent-mail MCP as `transfer_file_reservations` operation

**Why now:** When context exhaustion forces agent rotation, file locks must transfer atomically. Without this, two agents could simultaneously edit the same file.

---

### 5. **Agent State Machine with Real-Time Monitoring (P0 — Copy Now)**

**Value:** 9/10 | **Effort:** 7/10 | **Leverage:** Foundation for automation
**Convergence:** 5/5 agents flagged this

**Pattern:** Formalized agent lifecycle transitions:
```
Waiting -> Generating -> Thinking -> (Idle | Error | Stalled)
```

With monitoring:
- Poll-based state detector (default 5s interval)
- Pattern matching on agent output (unstructured LLM output -> state)
- Activity velocity tracking (tokens/minute over sliding window)
- State transition events emitted to event bus
- Configurable detection thresholds and timeouts

**Demarch target:** Intercore kernel as `AgentStateMonitor`

**Why now:** Without formal state transitions, automatic work assignment, conflict detection, and health alerts are impossible. This is foundational.

**Implementation sketch:**
```
type AgentState string
const (
    StateWaiting AgentState = "waiting"
    StateGenerating = "generating"
    StateThinking = "thinking"
    StateIdle = "idle"
    StateError = "error"
    StateStalled = "stalled"
)

type Detector interface {
    DetectState(paneOutput string) (AgentState, confidence float32)
}

// Output patterns:
// "Generating" -> "Generating..." or "Thinking..." text
// "Thinking" -> Consistent pane output but no visible completion
// "Idle" -> Prompt visible, waiting for input
// "Error" -> "Error:" or "fatal:" or exception text
// "Stalled" -> No change > 5 minutes
```

---

### 6. **Handoff Format with Token Context & Reservation Transfer (P1 — Adapt Soon)**

**Value:** 8/10 | **Effort:** 5/10 | **Leverage:** Critical for continuity
**Convergence:** 5/5 agents flagged this

**Pattern:** Structured YAML handoff (~400 tokens) preserving:
- `goal` (required): What this session accomplished
- `now` (required): What next session should do first
- `done_this_session`: Task records with files
- `blockers`, `questions`, `decisions`, `findings`: Unstructured notes
- `worked`, `failed`: Pattern observations
- `token_context`: `{used, max, percentage}`
- `reservation_transfer`: Instructions for interlock

**Demarch target:** Formalize across Clavain + interphase

**Why now:** Context continuity is essential for long-running projects. Without structured handoffs, each agent restart loses context.

**Key insight:** Required fields (`goal`, `now`) enforced at type level, not by convention. This prevents invalid handoffs.

---

### 7. **Semantic Color Palette & Theme System (P1 — Adapt Soon)**

**Value:** 8/10 | **Effort:** 5/10 | **Leverage:** Visual consistency
**Convergence:** 5/5 agents flagged this for Autarch

**Pattern:** Two-tier color system:
- `Theme`: Raw Catppuccin palette (Mocha, Latte, Macchiato, Nord) + plain fallback
- `SemanticPalette`: Role-based aliases (`StatusSuccess`, `AgentClaude`, `BorderFocused`, etc.)
- Components reference semantic palette, never raw colors
- Agent-specific colors: Claude (Mauve), Codex (Blue), Gemini (Yellow)
- `theme.Semantic().StatusColor(status)` and `theme.Semantic().AgentColor(agentType)` lookups

**Demarch target:** Autarch apps (Bigend, Gurgeh, Coldwine, Pollard)

**Why now:** Currently Autarch hardcodes colors. This pattern enables theme swapping without code changes.

**Reference implementation:** Port `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/` to Autarch as `pkg/tui/theme/`.

---

### 8. **Layout Tier System with Hysteresis (P1 — Adapt Soon)**

**Value:** 7/10 | **Effort:** 3/10 | **Leverage:** Prevents UI flicker
**Convergence:** 5/5 agents flagged this

**Pattern:** Five width tiers with 5-column hysteresis margin:
```
Narrow   <120 columns
Split    120-199 columns
Wide     200-239 columns
Ultra    240-319 columns
Mega     >=320 columns
```

Without hysteresis, dragging terminal edges causes rapid tier toggling. With hysteresis, tier sticks until crossing boundary + margin.

**Demarch target:** Autarch TUI all panels (Bigend, Gurgeh, etc.)

**Why now:** Simple fix (20 lines) that eliminates an entire class of UX bugs.

---

### 9. **Approval Engine with SLB (Two-Person Rule) (P1 — Adapt Soon)**

**Value:** 8/10 | **Effort:** 6/10 | **Leverage:** Safety gate
**Convergence:** 5/5 agents flagged this

**Pattern:** Request/approve/deny workflow with:
- SLB enforcement: approver ≠ requester (and delegates to external SLB system if available)
- Expiry: Approvals expire after 24h (configurable)
- Event emission on state transitions
- Blocking wait with channel-based notification
- Best-effort notifications (never block core operation)

**Demarch targets:**
- Interlock: force-release requires approval
- Clavain: destructive git operations
- Intercheck: production deployments

**Why now:** Any autonomous system needs safety gates. SLB is standard for sensitive operations.

---

### 10. **Phase-Based Confirmation Flow (P1 — Adapt Soon)**

**Value:** 7/10 | **Effort:** 5/10 | **Leverage:** Safety UX
**Convergence:** 5/5 agents flagged this for Autarch broadcast actions

**Pattern:** Multi-phase flow for broadcast actions:
```
Select Command -> Select Target -> Confirm -> Execute
```

Each phase transition prevents accidental sends. Target selection shows live pane counts: "Send to Claude (3)" not just "Claude".

**Demarch target:** Autarch broadcast actions (Bigend, Gurgeh)

**Why now:** Broadcast actions (send-all, deploy-all, force-release) are high-risk. Three-phase flow catches most mistakes.

---

## Part 2: Complete Ranked List of Adoption Candidates

### Tier P0 — Critical Infrastructure (Implement First, Concurrently)

| Priority | Pattern | ntm Source | Demarch Target | Effort | Value | Status |
|----------|---------|-----------|----------------|--------|-------|--------|
| **P0** | **Multi-factor assignment scoring** | coordinator/assign.go | Intercore | 8 | 9 | Copy Now |
| **P0** | **Tamper-evident audit trail** | internal/audit/ | Intercore + Interlock | 8 | 10 | Copy Now |
| **P0** | **Redaction engine** | internal/redaction/ | core/ (shared lib) | 6 | 9 | Copy Now |
| **P0** | **Reservation transfer with rollback** | handoff/transfer.go | agent-mail MCP | 7 | 9 | Copy Now |
| **P0** | **Agent state machine + monitoring** | coordinator/coordinator.go | Intercore | 7 | 9 | Copy Now |
| **P0** | **Handoff format (goal/now + tokens)** | handoff/types.go | Clavain + interphase | 5 | 8 | Copy Now |

### Tier P1 — High-Value UX/Safety Patterns (Implement Next)

| Priority | Pattern | ntm Source | Demarch Target | Effort | Value | Status |
|----------|---------|-----------|----------------|--------|-------|--------|
| **P1** | **Semantic color palette** | tui/theme/semantic.go | Autarch pkg/tui/theme | 5 | 8 | Adapt Soon |
| **P1** | **Layout tier + hysteresis** | tui/layout/layout.go | Autarch all panels | 3 | 7 | Adapt Soon |
| **P1** | **Approval engine (SLB)** | internal/approval/ | Intercore + Interlock | 6 | 8 | Adapt Soon |
| **P1** | **Phase-based confirmation** | palette/model.go | Autarch broadcast | 5 | 7 | Adapt Soon |
| **P1** | **Design token system** | tui/styles/tokens.go | Autarch pkg/tui/styles | 5 | 7 | Adapt Soon |
| **P1** | **Fair spawn scheduler** | scheduler/scheduler.go | Intercore | 7 | 7 | Adapt Soon |
| **P1** | **Context estimation (multi-strategy)** | internal/context/monitor.go | Intercore + Intermux | 8 | 8 | Adapt Soon |
| **P1** | **Predictive context exhaustion** | internal/context/predictor.go | Clavain | 6 | 7 | Adapt Soon |

### Tier P2 — Valuable Refinements (Implement in Next Iteration)

| Priority | Pattern | ntm Source | Demarch Target | Effort | Value | Status |
|----------|---------|-----------|----------------|--------|-------|--------|
| **P2** | **Three-tier icon fallback system** | tui/icons/icons.go | Autarch pkg/tui/icons | 3 | 6 | Inspiration |
| **P2** | **Shimmer/gradient rendering** | tui/styles/styles.go | Autarch TUI polish | 4 | 5 | Inspiration |
| **P2** | **Conflict detection + negotiation** | coordinator/conflicts.go | Interlock enhanced | 6 | 6 | Inspiration |
| **P2** | **Auto-respawner (limit detection)** | swarm/auto_respawner.go | Intermux lifecycle | 6 | 7 | Inspiration |
| **P2** | **Health checking** | internal/health/ | Intermux signals | 5 | 7 | Inspiration |
| **P2** | **Badge system** | tui/styles/badges.go | Autarch components | 4 | 5 | Inspiration |
| **P2** | **Panel interface** | tui/dashboard/panels/panel.go | Autarch architecture | 5 | 7 | Inspiration |
| **P2** | **Cost tracking** | internal/cost/ | Interstat | 5 | 6 | Inspiration |
| **P2** | **Proactive handoff generation** | internal/context/handoff_trigger.go | Clavain | 7 | 7 | Inspiration |
| **P2** | **Kernel registry for API parity** | internal/kernel/ | Intercore | 6 | 7 | Inspiration |

### Tier P3 — Interesting but Lower Priority

| Priority | Pattern | ntm Source | Demarch Target | Effort | Value | Status |
|----------|---------|-----------|----------------|--------|-------|--------|
| **P3** | **Ensemble reasoning taxonomy** | ensemble/modes.go | intersynth reference | 8 | 6 | Study Only |
| **P3** | **Workflow template system** | workflow/template.go | Clavain reference | 7 | 5 | Study Only |
| **P3** | **Metrics + Prometheus export** | internal/metrics/ | Observability | 5 | 4 | Study Only |
| **P3** | **Privacy manager** | internal/privacy/ | Intercore opt-in | 3 | 4 | Study Only |
| **P3** | **Profiler with recommendations** | internal/profiler/ | Intercore debugging | 4 | 3 | Study Only |

---

## Part 3: Anti-Patterns to Explicitly Avoid

### **Anti-Pattern A: Config God Struct**

**Problem:** ntm's `config.Config` owns configuration for every subsystem (agents, palette, tmux, robot, mail, integrations, models, alerts, etc.). Every subsystem adding config keys here creates tight coupling.

**How Demarch should differ:** Subsystem configs should own themselves. Root config loader assembles them by calling `subsystem.LoadConfig(root *RootConfig)`.

**Demarch impact:** Keep `CLAUDE.md` and `settings.json` minimal. Plugins own their own config files or define config types in their packages.

---

### **Anti-Pattern B: Two Width-Tier Systems**

**Problem:** ntm has overlapping breakpoint definitions:
- `tui/styles/tokens.go`: 40/60/80/120/160/200/240
- `tui/layout/layout.go`: 120/200/240/320
- `tui/dashboard/layout.go`: 60/100/140/180

**How Demarch should differ:** One canonical tier system, one place, enforced everywhere. If you need different values for different contexts, make them explicit variants, not hidden duplicates.

**Demarch impact:** Autarch must have a single `pkg/tui/layout/tiers.go` with canonical breakpoints. All panels reference this file.

---

### **Anti-Pattern C: Monolithic Dashboard God Model**

**Problem:** ntm's `dashboard.go` is 6,716 lines, maintains 500+ state fields, imports 28+ internal packages, and polls every data source directly. State collection is tightly coupled to rendering.

**How Demarch should differ:** Separate data aggregation from rendering. Introduce a DataBus or ViewModel layer that subscribes to data sources and emits typed update messages. The model subscribes to update messages, not to data sources.

**Demarch impact:** Autarch's dashboard(s) must compose from typed sub-models (one per concern). Start with a `DataBus` interface that aggregates state from all sources and emits typed messages.

---

### **Anti-Pattern D: CLI Absorbing Business Logic**

**Problem:** ntm's CLI files (`internal/cli/*.go`) are large and contain business logic that should be in domain packages. This creates duplication when the robot API implements the same operations.

**How Demarch should differ:** CLI parses flags and calls domain functions. Robot API calls the same domain functions. Application service layer is the single source of truth.

**Demarch impact:** Clavain's commands and Autarch's TUI actions should both call shared application services, not duplicate business logic.

---

### **Anti-Pattern E: Partial Experimental Build Tags**

**Problem:** ntm's ensemble is behind `//go:build ensemble_experimental` but the type system (`types.go`, `modes.go`, `synthesizer.go`) ships in all builds. This creates architectural ambiguity.

**How Demarch should differ:** Gate the entire feature or gate nothing. If a feature is experimental, make it a separate plugin, not a partial gate.

**Demarch impact:** Intersynth features should be independently toggleable, not partially gated. Use separate MCP tools or feature flags, not build tags.

---

### **Anti-Pattern F: Hardcoded Pricing Tables**

**Problem:** ntm embeds model pricing in Go source code. When pricing changes, you must recompile.

**How Demarch should differ:** Externalize all pricing to YAML/JSON config files. Load at runtime.

**Demarch impact:** If Demarch tracks costs (which it should), pricing must be configurable, not hardcoded.

---

### **Anti-Pattern G: PTY-Based CLI Output Parsing**

**Problem:** ntm's quota fetcher sends `/usage` commands to tmux panes and parses the output with regex. This breaks when CLI output formats change.

**How Demarch should differ:** Prefer API-based approaches where available (Claude API, Gemini API). Use PTY parsing only as fallback.

**Demarch impact:** Agent health checks should use APIs when available, not shell output parsing.

---

## Part 4: Specific Patterns Worth Copying Verbatim

### 1. **Icon Fallback Chain** (3 lines of logic)

```go
// NerdFonts -> Unicode -> ASCII with field-by-field merging
NerdFonts.WithFallback(Unicode).WithFallback(ASCII)
```

**Why:** Fixes rendering issues in limited terminals without degradation.

---

### 2. **Shimmer Function** (40 lines)

Time-offset gradient that wraps around. Simple math + ANSI output. Directly applicable to Autarch banner rendering.

---

### 3. **Layout Tier Hysteresis** (30 lines)

```go
const HysteresisMargin = 5
func TierForWidthWithHysteresis(width int, prevTier Tier) Tier {
    newTier := TierForWidth(width)
    if newTier == prevTier { return newTier }
    // Check if within margin before switching
}
```

---

### 4. **Semantic Palette Lookups** (10 lines)

```go
func (p *SemanticPalette) StatusColor(status string) lipgloss.Color {
    switch status {
    case "success": return p.StatusSuccess
    case "error": return p.StatusError
    // ...
    }
}

func (p *SemanticPalette) AgentColor(agentType string) lipgloss.Color {
    switch agentType {
    case "claude": return p.AgentClaude
    // ...
    }
}
```

---

### 5. **SSH Theme Detection Guard** (4 lines)

```go
if os.Getenv("SSH_CONNECTION") != "" || os.Getenv("SSH_TTY") != "" {
    return true // Default to dark theme over SSH
    // Prevents OSC response race conditions
}
```

---

### 6. **Step Progress CLI Output** (30 lines)

Clean step-by-step progress with automatic color/no-color fallback.

---

## Part 5: Demarch-Specific Adoption Roadmap

### Phase 1: Foundation (Months 1-2)

**Goals:** Build safety and audit infrastructure that enables all future work.

1. **Port redaction engine** to `core/redaction/`
   - Integrate into Intercore event bus (redact before persistence)
   - Integrate into agent-mail (redact before transmission)

2. **Implement audit trail** in Intercore
   - Hash-chain JSONL logging for all session events
   - Interlock integration for reservation/release events
   - `intercheck doctor` verification

3. **Define Demarch invariants** (expand ntm's 6)
   - `no_silent_data_loss`
   - `graceful_degradation`
   - `idempotent_orchestration`
   - `recoverable_state`
   - `auditable_actions`
   - `safe_by_default`
   - `plugin_isolation` (new)
   - `mcp_audit_completeness` (new)
   - `secret_hygiene` (new)

### Phase 2: Orchestration Intelligence (Months 2-3)

1. **Agent state machine** in Intercore
   - Formalize state transitions
   - Event emission on state changes
   - Integration with intermux visibility

2. **Multi-factor assignment scoring** in Intercore
   - Integrate with bv (dependency graph)
   - Integrate with agent-mail (profiles + capabilities)
   - Route work automatically instead of round-robin

3. **Reservation transfer** in agent-mail
   - Atomic handoff with rollback semantics
   - Integration with handoff format

### Phase 3: UX Polish (Months 3-4)

1. **Autarch theme system**
   - Semantic color palette
   - Agent-specific colors
   - NO_COLOR support

2. **Autarch layout tiers**
   - Canonical breakpoints
   - Hysteresis margin
   - All panels aligned

3. **Autarch components**
   - Panel interface
   - Badge system
   - Progress bars with terminal fallback

### Phase 4: Advanced Capabilities (Months 4-5)

1. **Context management** (proactive handoff + predictive exhaustion)
2. **Approval engine** (force-release + destructive commands)
3. **Auto-respawner** (crash detection + account rotation)
4. **Health monitoring** (per-agent state tracking)

---

## Part 6: Product Validation

### What ntm Gets Right

1. **Addresses real operational pain:** Handoff, checkpoint, approval, and reservation systems solve genuine multi-agent problems. These are not academic features — they emerged from running agents at scale.

2. **Monolithic architecture enables sophisticated coordination:** ntm's single Go binary achieves tight integration of scheduling, assignment, conflict detection, and respawn that would be harder to implement across distributed plugins.

3. **Ensemble reasoning taxonomy is substantive:** 80 modes, 12 categories, 9 presets represent real attempts to make AI reasoning strategies legible and composable. This deserves study for Demarch's intersynth design.

### What ntm Reveals About Autarch's Gaps

1. **No structured onboarding:** ntm has `ntm tutorial` and `ntm deps -v`. Autarch has no first-run health check or interactive tutorial.

2. **Approval workflow has no TUI visibility:** ntm's approval engine exists but the dashboard doesn't show pending approvals. Autarch must make approvals a first-class panel.

3. **Session naming convention not standardized:** ntm's `{project}__{type}_{index}` is explicit and machine-parseable. Autarch/intermux should adopt equivalent conventions.

4. **Broadcast action model not confirmed:** Does Autarch have an equivalent to `ntm send --all`? If not, this is a missing orchestration primitive.

5. **Handoff-to-recovery integration missing:** ntm shows goal/now from the handoff in the dashboard. Autarch's Bigend/Coldwine should do the same.

---

## Part 7: Implementation Checklist

### Highest-Priority (Start Immediately)

- [ ] Port redaction engine to `core/redaction/`
- [ ] Define Demarch's 9 invariants
- [ ] Implement hash-chain audit logging in Intercore
- [ ] Build multi-factor assignment scorer
- [ ] Formalize agent state machine
- [ ] Implement reservation transfer in agent-mail
- [ ] Adopt handoff format (goal/now + tokens)

### High-Priority (Next Sprint)

- [ ] Semantic color palette for Autarch
- [ ] Layout tier system + hysteresis for Autarch
- [ ] Approval engine (SLB + expiry)
- [ ] Phase-based confirmation for broadcast actions
- [ ] Design token system for Autarch

### Medium-Priority (Next Iteration)

- [ ] Context estimation (multi-strategy)
- [ ] Predictive exhaustion + proactive handoff
- [ ] Fair spawn scheduler
- [ ] Auto-respawner (crash detection)
- [ ] Health monitoring signals

---

## Part 8: Code Reference Guide

**Files worth studying in ntm:** (Absolute paths)

### Coordination Infrastructure
- `/home/mk/projects/Demarch/research/ntm/internal/coordinator/assign.go` — Multi-factor scoring
- `/home/mk/projects/Demarch/research/ntm/internal/coordinator/coordinator.go` — Agent state machine
- `/home/mk/projects/Demarch/research/ntm/internal/handoff/transfer.go` — Reservation transfer
- `/home/mk/projects/Demarch/research/ntm/internal/approval/engine.go` — Approval workflow
- `/home/mk/projects/Demarch/research/ntm/internal/audit/logger.go` — Audit trail
- `/home/mk/projects/Demarch/research/ntm/internal/redaction/redaction.go` — Redaction engine

### TUI Infrastructure
- `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/theme.go` — Theme system
- `/home/mk/projects/Demarch/research/ntm/internal/tui/theme/semantic.go` — Semantic palette
- `/home/mk/projects/Demarch/research/ntm/internal/tui/layout/layout.go` — Layout tiers + hysteresis
- `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/tokens.go` — Design tokens
- `/home/mk/projects/Demarch/research/ntm/internal/tui/styles/styles.go` — Shimmer/gradient rendering
- `/home/mk/projects/Demarch/research/ntm/internal/tui/icons/icons.go` — Icon fallback chain

### Orchestration
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/types.go` — SwarmPlan
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/orchestrator.go` — Session creation
- `/home/mk/projects/Demarch/research/ntm/internal/swarm/auto_respawner.go` — Crash recovery
- `/home/mk/projects/Demarch/research/ntm/internal/context/monitor.go` — Context estimation
- `/home/mk/projects/Demarch/research/ntm/internal/context/predictor.go` — Exhaustion prediction

---

## Conclusion

ntm represents ~5 years of production experience running multiple AI agents simultaneously. Its three standout contributions are:

1. **Comprehensive coordination infrastructure** (assignment, scheduling, conflict resolution, approval) — Demarch should adopt these as Intercore primitives.

2. **Mature safety and audit patterns** (redaction, audit trails, approval gates, invariant enforcement) — Critical for any platform handling production code.

3. **Production-grade TUI architecture** (theme system, layout tiers, panel composition) — Directly applicable to Autarch with minimal adaptation.

The highest-leverage adoptions are the multi-factor assignment scorer, audit trail, and redaction engine — these three would immediately strengthen Demarch's foundation. The phase-based adoption roadmap above makes this concrete: foundation → intelligence → UX polish → advanced capabilities.

Demarch's plugin architecture is structurally superior to ntm's monolithic design (modularity wins long-term), but Intercore must provide the coordination primitives that ntm gets from being tightly coupled. By adopting these patterns, Demarch gains the sophistication of a tightly-integrated system while retaining the flexibility of an extensible architecture.
