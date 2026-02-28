# OODAR Loops for Agent Decision-Making — Brainstorm

**Date:** 2026-02-28
**Type:** Architecture design
**Status:** Brainstorm (not yet strategized)

## What We're Building

An explicit OODAR (Observe → Orient → Decide → Act → Reflect) framework for Demarch that operates at four nested timescales: per-turn, per-sprint, multi-agent, and cross-session. Extends Boyd's OODA loop with a fifth phase (Reflect) to formalize the learning/compounding step that Demarch's philosophy already demands.

### Why OODAR, Not OODA

Boyd's OODA assumes Orient implicitly incorporates learning from past cycles. For AI agents, this is too important to leave implicit:

- **Agents don't have intuition.** Human operators implicitly learn from each OODA cycle — their Orient phase naturally improves. LLM agents start from scratch each session unless learning is explicitly captured.
- **Compounding is Demarch's flywheel.** PHILOSOPHY.md defines the cycle: authority → actions → evidence → authority. The Reflect phase IS the evidence-to-authority conversion.
- **Demarch already has Reflect.** The sprint lifecycle includes a mandatory `reflect` phase. Signal scoring triggers `/compound`. Interspect accumulates evidence. OODAR names what exists.

### The Fifth Phase: Reflect

Reflect operates in **dual mode** based on action significance:

- **Inline Reflect** (signal_score ≥ 4): Pause the loop. Debrief. Update mental models NOW. Compound learnings before next cycle. Used for novel situations, important decisions, errors, recoveries.
- **Async Reflect** (signal_score < 4): Continue immediately. Background process accumulates evidence, updates models. Benefits arrive on the next cycle. Used for routine actions.

This resolves the tempo-vs-depth tension: routine cycles stay fast (Boyd's speed advantage), significant cycles pause to learn (compounding advantage).

## Loop Communication: Hybrid Architecture

All four OODAR loops communicate via a **hybrid model**: hierarchical decisions + shared observations.

```
┌─────────────────────────────────────────────┐
│         Shared Observation Layer             │
│  (read-only for all loops)                  │
│  - event stream (phase + dispatch events)   │
│  - evidence store (interspect SQLite)       │
│  - agent state (lifecycle, heartbeat)       │
│  - phase state (current phase, gate results)│
│  - situation assessments (cached Orient)    │
└──────────┬──────────────────────────────────┘
           │ any loop reads any layer
     ┌─────┴──────┐
     │ Per-Turn   │──escalate──→ Sprint ──escalate──→ Cross-Session
     │ OODAR      │              OODAR                OODAR
     └────────────┘              │
                    de-escalate ←─┘ (writes to shared obs,
                                     inner loops read & adjust)
```

**Key properties:**
- Observe: all loops read the shared observation layer (no authority needed)
- Orient: each loop produces situation assessments at its own timescale
- Decide: hierarchical — inner loops own fast decisions, escalate beyond their scope
- Act: hierarchical — each loop acts within its authority boundary
- Reflect: writes back to shared observation layer (evidence, updated models)
- De-escalation: outer loops calm inner loops by writing to shared observations

## The Four OODAR Loops

### Loop 1: Per-Turn (milliseconds–seconds)

The tightest loop. Runs after every agent tool call or LLM response.

| Phase | Current Implementation | Gap |
|-------|----------------------|-----|
| **Observe** | Tool result, file state, test output | No unified snapshot |
| **Orient** | LLM reads prompt + context (implicit) | No structured situation assessment |
| **Decide** | LLM picks next tool/action (implicit) | No fast-path for known patterns |
| **Act** | Tool call execution | Solid — dispatch works |
| **Reflect** | Signal scoring (auto-stop-actions.sh) | Only fires on Stop, not per-tool |

**Tempo target:** <100ms overhead per turn for fast-path decisions.

### Loop 2: Per-Sprint (minutes–hours)

The phase lifecycle loop. Runs at each phase gate evaluation.

| Phase | Current Implementation | Gap |
|-------|----------------------|-----|
| **Observe** | Phase state, gate results, artifacts | Requires multiple CLI queries |
| **Orient** | Sprint state assessment (lib-sprint.sh) | Hardcoded bash, not adaptive |
| **Decide** | phase_actions table + sprint_next_step() | Moving from bash to kernel — good |
| **Act** | Phase advance + agent dispatch | Solid — gated, transactional |
| **Reflect** | Mandatory reflect phase at end | Only at sprint end, not per-phase |

**Tempo target:** Phase transitions in <5s, including observation and orientation.

### Loop 3: Multi-Agent (seconds–minutes)

The coordination loop. Runs when multiple agents operate on shared resources.

| Phase | Current Implementation | Gap |
|-------|----------------------|-----|
| **Observe** | Agent heartbeats, lock state, dispatch poll | Fragmented across interlock/intermute/dispatch |
| **Orient** | No explicit coordination model | **Biggest gap** — agents don't model each other's state |
| **Decide** | Lock acquisition, claiming protocol | Reactive (wait for conflict), not proactive |
| **Act** | Dispatch spawn/kill, lock acquire/release | Solid |
| **Reflect** | Post-review convergence scoring (intersynth) | Only in review context, not general coordination |

**Tempo target:** Conflict detection in <1s, resolution in <5s.

### Loop 4: Cross-Session (hours–days)

The learning loop. Runs between sessions, accumulating evidence and adapting routing.

| Phase | Current Implementation | Gap |
|-------|----------------------|-----|
| **Observe** | Interspect evidence collection | Solid — every override/correction stored |
| **Orient** | classify_pattern (emerging/growing/ready) | Rule-based only, no LLM orientation for novel patterns |
| **Decide** | Routing override proposals | Requires human approval — by design |
| **Act** | routing-overrides.json → flux-drive pre-filter | Solid — canary monitoring, circuit breaker |
| **Reflect** | Canary evaluation (20-use window) | Only for routing changes, not general learning |

**Tempo target:** Pattern classification within same session, override proposals within 24h of sufficient evidence.

---

## Approach A: Bottom-Up — Formalize What Exists

### Philosophy

Name the OODAR legs on top of existing infrastructure. No new primitives — just contracts, interfaces, and a unified observation surface over existing code. Ship incrementally; each step is independently useful.

### Implementation Path

#### Step 1: Shared Observation Layer — `ic situation`

Build a unified observation snapshot command that queries all existing data sources in a single call.

```
ic situation snapshot
```

Returns:
```json
{
  "timestamp": "2026-02-28T10:30:00Z",
  "phase": { "current": "executing", "history": [...] },
  "agents": [
    { "id": "a1", "state": "thinking", "velocity": 42.5, "assigned": "beads-xyz" }
  ],
  "events": { "recent": [...], "unprocessed_count": 3 },
  "evidence": { "patterns": [...], "pending_proposals": 1 },
  "artifacts": { "produced": [...], "expected": [...] },
  "blockers": [...],
  "budget": { "spent": 15000, "remaining": 85000, "burn_rate": 2.3 }
}
```

**Implementation:** Go function in intercore that queries phase_log, dispatch_states, event bus, interspect DB, and budget tracker. Serializes to JSON. Single round-trip.

**What this enables:** Any OODAR loop at any level can start with `ic situation snapshot` instead of querying 5 different sources. Observation becomes O(1) calls instead of O(n).

#### Step 2: Situation Assessment Schema — Orient Output

Define a structured output type that the Orient phase produces at every level.

```json
{
  "assessment_type": "per_turn | sprint | multi_agent | cross_session",
  "current_state": "what's happening now",
  "recent_changes": ["what just changed"],
  "active_patterns": ["known patterns matching current situation"],
  "anomalies": ["things that don't match expectations"],
  "constraints": { "budget": "...", "time": "...", "dependencies": "..." },
  "confidence": 0.85,
  "recommended_mental_model": "debugging | building | reviewing | shipping"
}
```

**Per-turn:** Agent produces this as structured output in its reasoning, cached across turns in the session.
**Sprint:** `sprint_read_state()` returns this instead of raw bash vars.
**Multi-agent:** New `ic coordination assess` produces this from lock state + agent heartbeats.
**Cross-session:** `interspect assess` produces this from evidence patterns.

#### Step 3: Decision Contracts — Fast Path + Deliberate Path

Extract decision logic from LLM prompts and bash scripts into executable lookup tables.

**Fast path (rule-based):**
- Routing tables (routing-tables.md → routing-tables.json, queryable)
- Phase action resolution (phase_actions table — already moving to kernel)
- Signal scoring thresholds (already in auto-stop-actions.sh)
- Interspect classify_pattern (already rule-based)

**Deliberate path (LLM-driven):**
- Novel situations where no pattern matches
- High-stakes decisions (ship/no-ship, architecture changes)
- Situations where fast-path confidence < threshold

**Decision:** If fast-path has a match with confidence ≥ 0.8, use it. Otherwise, invoke LLM deliberation with the situation assessment as input.

#### Step 4: Reflect Contracts — Dual-Mode Formalization

Formalize the existing signal scoring + /compound pattern:

**Inline reflect (signal_score ≥ 4):**
1. Pause loop
2. Produce structured reflection: `{ outcome, delta_from_expectation, lesson, model_update }`
3. Write lesson to evidence store
4. Update situation assessment cache
5. Resume loop with updated Orient inputs

**Async reflect (signal_score < 4):**
1. Emit evidence event to interspect
2. Continue loop immediately
3. Background: interspect accumulates, classifies when threshold met

#### Step 5: OODAR Vocabulary in Docs and Skills

Label existing loops with OODAR terminology in:
- PHILOSOPHY.md (flywheel IS OODAR)
- Sprint skills (phase lifecycle IS sprint OODAR)
- Agent skills (per-turn reasoning IS turn OODAR)
- Interspect docs (evidence accumulation IS cross-session OODAR)

### Strengths

- **Low risk.** No new primitives, just contracts over existing code.
- **Incremental delivery.** Each step ships independently and provides immediate value.
- **Battle-tested foundations.** Built on infrastructure that already works.
- **Fast to first value.** `ic situation` alone would improve every agent's orientation.

### Weaknesses

- **No formal abstraction.** Each level's OODAR is ad-hoc; no guarantee they compose well.
- **Harder to add new loops.** Adding a 5th timescale (e.g., cross-project) means building another bespoke implementation.
- **Orient remains mostly LLM-driven.** Situation assessments improve LLM inputs but don't formalize orientation as a primitive.
- **Technical debt accumulates.** More contracts layered on existing code = more coupling to maintain.

---

## Approach B: Top-Down — Design the OODAR Primitive First

### Philosophy

Define a generic `OODARLoop` abstraction in intercore. Design the interface first, then implement it at each level. Existing infrastructure becomes concrete implementations of abstract interfaces. Gridfire's Controller<S,M,A> extended to Controller<S,M,A,R>.

### The OODAR Primitive

```go
// The generic OODAR loop interface
type OODARLoop[S Sensor, O Orientation, D Decision, A Action, R Reflection] interface {
    // Observe: gather raw data from the environment
    Observe(ctx context.Context, sensor S) (Observation, error)

    // Orient: make sense of observations using mental models
    Orient(ctx context.Context, obs Observation, models ModelStore) (O, error)

    // Decide: choose an action (fast-path or deliberate)
    Decide(ctx context.Context, orientation O) (D, error)

    // Act: execute the decision
    Act(ctx context.Context, decision D, actuator A) (Outcome, error)

    // Reflect: learn from the outcome (inline or async based on significance)
    Reflect(ctx context.Context, outcome Outcome, significance float64) (R, error)

    // Run: execute one full OODAR cycle
    Cycle(ctx context.Context) error

    // RunLoop: continuously execute cycles until stopped
    RunLoop(ctx context.Context) error
}

// Shared observation layer — readable by all loops
type ObservationStore interface {
    Snapshot(ctx context.Context) (SituationSnapshot, error)
    Subscribe(ctx context.Context, filter EventFilter) (<-chan Event, error)
}

// Model store — updated by Reflect, read by Orient
type ModelStore interface {
    Get(ctx context.Context, key string) (Model, error)
    Update(ctx context.Context, key string, update ModelUpdate) error
    Patterns(ctx context.Context, filter PatternFilter) ([]Pattern, error)
}

// Significance classifier — determines inline vs async reflect
type SignificanceClassifier interface {
    Classify(ctx context.Context, outcome Outcome) (float64, error)
}
```

### Instantiation at Each Level

```go
// Per-Turn OODAR
type TurnLoop struct {
    sensor    ToolResultSensor      // observes tool call results
    models    SessionContextModels  // mental models = session context + cached assessments
    actuator  ToolCallActuator      // acts by calling tools
    reflector TurnReflector         // signal scoring + evidence emit
    classifier SignalScoreClassifier // signal_score threshold
}

// Sprint OODAR
type SprintLoop struct {
    sensor    PhaseStateSensor      // observes phase state + gate results
    models    SprintModels          // mental models = sprint state + phase_actions
    actuator  PhaseAdvanceActuator  // acts by advancing phases + dispatching agents
    reflector SprintReflector       // per-phase + end-of-sprint reflection
    classifier PhaseSignificanceClassifier
}

// Multi-Agent OODAR
type CoordinationLoop struct {
    sensor    AgentStateSensor      // observes agent heartbeats, locks, dispatch
    models    CoordinationModels    // mental models = who's doing what, conflict history
    actuator  DispatchActuator      // acts by spawn/kill/reassign
    reflector CoordReflector        // convergence scoring, conflict lessons
    classifier ConflictSignificanceClassifier
}

// Cross-Session OODAR
type LearningLoop struct {
    sensor    EvidenceSensor        // observes interspect evidence
    models    RoutingModels         // mental models = agent trust scores, routing overrides
    actuator  RoutingActuator       // acts by proposing/applying routing changes
    reflector CanaryReflector       // canary monitoring, circuit breaker
    classifier PatternSignificanceClassifier
}
```

### Implementation Path

#### Step 1: Define Core Interfaces in Intercore

Create `internal/oodar/` package with the generic interface, shared types (Observation, Outcome, Model, Pattern), and the ObservationStore / ModelStore contracts.

#### Step 2: Implement ObservationStore (Shared Observation Layer)

Same as Approach A's Step 1 — unified snapshot over event bus + interspect + phase state. But now it implements the `ObservationStore` interface, making it composable.

#### Step 3: Implement SprintLoop First (Most Mature)

The sprint phase lifecycle is the most fully implemented OODAR loop today. Wrap existing phase machine + sprint library in the `OODARLoop` interface:
- Sensor: wraps `ic phase show` + `ic events tail`
- Orient: wraps `sprint_read_state()` → produces `SituationAssessment`
- Decide: wraps `phase_actions` table lookup (fast) + LLM phase planning (deliberate)
- Act: wraps `phase.Advance()` + `dispatch.Spawn()`
- Reflect: wraps signal scoring + reflect phase + /compound

#### Step 4: Implement TurnLoop Second

Per-turn OODAR wraps around the agent's tool-call cycle:
- Sensor: tool result + file diff + test output
- Orient: structured situation assessment (cached across turns)
- Decide: routing table lookup (fast) + LLM reasoning (deliberate)
- Act: tool call
- Reflect: signal scoring per-turn + evidence emit

#### Step 5: Implement CrossSessionLoop Third

Wraps interspect's evidence accumulation and routing override flow:
- Sensor: interspect evidence queries
- Orient: classify_pattern + LLM for novel patterns
- Decide: routing override proposal
- Act: write routing-overrides.json
- Reflect: canary monitoring over 20-use window

#### Step 6: Implement CoordinationLoop Last (Least Mature)

Multi-agent coordination is the least developed; implementing it last lets the interface stabilize first.

### Strengths

- **Formal composability.** Adding a new loop level (e.g., cross-project, cross-team) means implementing the interface, not building from scratch.
- **Type safety.** Go generics enforce that each level's Sensor/Model/Actuator/Reflector are type-compatible.
- **Testable in isolation.** Each OODAR component can be unit-tested with mock sensors/actuators.
- **Gridfire alignment.** Directly extends Controller<S,M,A> with R, advancing the Gridfire roadmap.
- **Principled Orient.** Orient becomes a first-class interface method, not ad-hoc LLM reasoning.

### Weaknesses

- **Premature abstraction risk.** If the four levels differ more than expected, the generic interface becomes a straitjacket.
- **Higher upfront cost.** Interface design + 4 implementations before full value.
- **Abstraction overhead.** Indirection layers add complexity for contributors to navigate.
- **May over-formalize.** Per-turn OODAR might fight against LLM-native reasoning patterns rather than complement them.

---

## Key Decisions Made

1. **OODAR, not OODA.** The Reflect phase is explicit — too important for AI agents to leave implicit.
2. **Dual-mode Reflect.** Inline for significant actions (signal_score ≥ 4), async for routine. Preserves tempo while compounding learnings.
3. **Hybrid communication.** Shared observation layer (any loop reads any data) + hierarchical decisions (inner loops escalate to outer loops). De-escalation via shared observation writes.
4. **Explicit Orient primitives.** Situation assessments as structured output, not implicit LLM reasoning. Fast-path + deliberate-path decision routing.
5. **Shared Observation Layer first.** Foundation that every other OODAR leg benefits from, regardless of approach.
6. **Four nested loops.** Per-turn (ms), sprint (min), multi-agent (sec), cross-session (hrs). Each owns its timescale.

## Open Questions

1. **How to handle Orient for per-turn loops without adding latency?** Caching situation assessments helps, but cache invalidation is the hard problem.
2. **Should the OODAR primitive be in intercore (kernel) or clavain (OS)?** Mechanism vs. policy question — the loop structure is mechanism, but Orient content is policy.
3. **How does OODAR interact with the trust ladder?** Higher trust levels should enable faster OODAR cycles (less human gating). How is this formalized?
4. **What are the escalation contracts?** When exactly does a per-turn loop escalate to sprint? What signals trigger it?
5. **How do we measure OODAR tempo?** If faster loops win, we need to measure loop latency per level and optimize it.

## Approach Comparison Summary

| Dimension | Bottom-Up (A) | Top-Down (B) |
|-----------|---------------|--------------|
| **Risk** | Low — contracts over existing code | Medium — premature abstraction possible |
| **Time to first value** | Fast — `ic situation` alone helps | Slower — interface + 1st impl before value |
| **Composability** | Ad-hoc per level | Formal generic interface |
| **Gridfire alignment** | Incremental toward Gridfire | Direct step toward Controller primitive |
| **Orient formalization** | Better LLM inputs | First-class interface method |
| **New loop levels** | Build from scratch each time | Implement the interface |
| **Maintenance** | More contracts = more coupling | More abstraction = more indirection |
| **Testing** | Integration-level | Unit-testable components |

## Next Steps

Run `/flux-drive` review on this document to synthesize the best of both approaches into a recommended hybrid path.

Then: `/clavain:write-plan` to create the implementation plan.
