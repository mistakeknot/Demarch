# OODAR Loops Synthesis Report

**Date:** 2026-02-28
**Document synthesized:** `docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`
**Reviewers:** 6 flux-drive agents (Architecture, Systems Thinking, Decision Quality, User/Product, Resilience, Sensemaking)
**Status:** Pre-plan review synthesis
**Verdict:** **NEEDS CHANGES** — Design is sound, but critical gaps block implementation

---

## Executive Summary

The OODAR (Observe → Orient → Decide → Act → Reflect) framework names something real in Demarch's architecture and is philosophically grounded in PHILOSOPHY.md's evidence-driven flywheel. The brainstorm demonstrates strong architectural thinking and correctly identifies the Reflect phase as the missing explicit layer.

**Verdict:** The design is architecturally defensible and philosophically correct, but has **five critical blind spots** that must be resolved before implementation can begin. The primary recommendation is **Approach A (bottom-up)**, starting immediately with the Shared Observation Layer, but with mandatory design amendments to address resilience, temporal reasoning, and sensemaking concerns identified across reviews.

**Key constraint:** The choice between Approach A (incremental contracts) and Approach B (generic interface) should not block work. Recommend starting with Approach A's Step 1 immediately, with planned interface extraction at milestone N+3.

---

## Convergent Findings (Multi-Agent Agreement)

### CONVERGENCE 1: Shared Observation Layer (`ic situation snapshot`) Is High-Value, Low-Risk (Severity: None — Strength, 6/6 agents agree)

All six agents identified `ic situation snapshot` as the highest-priority, immediately deployable component:

- **Architecture:** "Single round-trip instead of five CLI queries"
- **Systems:** "Foundation that every other OODAR leg benefits from"
- **Decision Quality:** "Uncontroversial, immediately useful"
- **User/Product:** "Clear beneficiary: every agent running a sprint"
- **Resilience:** "Wraps existing sources; independently useful"
- **Sensemaking:** Implicitly supporting (notes self-contained observation layer risks)

**Recommendation:** Ship this immediately as standalone deliverable, blocking nothing else. Should require <2 weeks implementation.

---

### CONVERGENCE 2: Multi-Agent Loop (Loop 3) Is Least Mature, Should Be Deferred (Severity: P2 — Process Risk, 5/6 agents explicitly flag)

All agents identified Loop 3 as architecturally premature:

- **Architecture:** "Least developed; implementing it last lets interface stabilize first"
- **Systems:** "Biggest gap — agents don't model each other's state"
- **User/Product:** "Dependency doesn't exist yet"; "High risk"
- **Resilience:** "Explicit deadlock prevention unspecified"; "lowest maturity"
- **Sensemaking:** "Least mature yet framed as parallel peer"; "should be spiked separately"

**Convergent recommendation:** Do not implement Loop 3 as a full OODAR cycle in the initial plan. Defer formal Loop 3 implementation to N+6 or later. Spike a minimal coordination model separately if needed for concurrent sprints.

---

### CONVERGENCE 3: Reflect Phase Conflates Two Distinct Concepts (Severity: P2 — Ambiguity, 3/6 agents, but critical)

Three agents independently identified the same ambiguity:

- **Decision Quality** (Finding 5): "Conflates within-cycle learning (Inline Reflect) vs cross-cycle learning (Async Reflect)"
- **Resilience** (Finding 3): "Reflect phase does not guarantee improved decisions on re-entry"
- **Sensemaking** (implicit): Notes that Reflect lacks verification mechanism

**Convergent problem:** The dual-mode Reflect (inline for signal_score ≥ 4, async for routine) conflates two different learning cycles that have different storage, latency, and authority models. They should be distinct phases.

**Convergent recommendation:** Split into **React** (within-cycle, updates session context, sync) and **Reflect** (cross-cycle, accumulates evidence, async). Update the terminology or explicitly document the distinction.

---

### CONVERGENCE 4: Per-Turn OODAR Tempo Budget Is Tight, Risky (Severity: P2 — Performance Risk, 4/6 agents)

Four agents flag the <100ms per-turn overhead target as a hard constraint that may not be achievable:

- **Architecture:** "Latency risk; fights LLM-native reasoning"
- **Decision Quality:** "Interface dispatch cost analysis … is the overhead worth the abstraction?"
- **User/Product:** "Latency risk; fights LLM-native reasoning"
- **Sensemaking:** Notes temporal discounting risk (fast-path speed could disable multi-agent safety)

**Convergent problem:** Per-turn OODAR assumes Orient can be cached and run in <100ms. But LLM-driven Orient is inherently non-deterministic, and cache invalidation is the hard problem (noted as open question 1).

**Convergent recommendation:** Do not commit to per-turn OODAR formalization until after `ic situation snapshot` is proven and its actual latency is measured. If measured latency is >50ms, the <100ms target is infeasible and per-turn formalization should be deferredor redesigned.

---

### CONVERGENCE 5: Escalation and De-Escalation Contracts Are Undefined (Severity: P2 — Design Gap, 5/6 agents)

Five agents identified the same undefined contract:

- **Architecture:** "Escalation contracts undefined"; "what signals trigger escalation?"
- **Systems:** "Causal inversion in escalation chain"; de-escalation arrives too late to be causal
- **Decision Quality:** "Escalation signals unspecified"
- **User/Product:** "Loop conflict protocol undefined"
- **Resilience:** Implicitly (failure propagation model undefined)

**Convergent problem:** The hybrid architecture (hierarchical escalation + shared observation de-escalation) has no explicit contract for when escalation happens or what de-escalation means (binding vs advisory). This is the highest-risk gap in the design.

**Convergent recommendation:** Before implementing any loop, design and document:
1. What constitutes escalation at each level (signal_score ≥ X? Confidence < Y? Timeout?)
2. What de-escalation means (a write to shared observation that adjusts inner loop behavior)
3. What happens if loops disagree (per-turn wants to continue, sprint wants to stop)
4. Deadlock prevention for simultaneously escalating loops

---

## Unique Findings by Severity

### P1 CRITICAL — MUST FIX BEFORE PLAN (Severity: P1, 3 unique issues from separate agents)

#### Issue 1.1: Shared Observation Layer Is a Single Point of Failure (RESILIENCE)

**Agent:** Resilience Review
**Location:** "Finding 1: Shared Observation Layer is a Single Point of Failure"
**Severity:** P1 — Blind Spot

The design proposes all four OODAR loops depend on `ic situation snapshot`, but provides no failure mode or fallback:

- What happens when snapshot is slow (>50ms)?
- What's the SLA and timeout policy?
- Do loops have degradation paths if snapshot is unavailable?

**Impact:** If `ic situation snapshot` is down or slow, all four loops degrade in unspecified ways. Per-turn loop hitting snapshot timeout could cascade to sprint loop, causing system-wide stall.

**Recommendation:** Add a "Observation Layer Resilience" section defining:
1. SLA for snapshot (<10ms target, <50ms maximum)
2. Circuit breaker: return cached data with `stale: true` flag on timeout
3. Per-loop fallback Orient (what each loop does without fresh snapshot)
4. Health check: `ic situation health` command
5. Monitoring: metrics for snapshot latency and cache hit rate

---

#### Issue 1.2: Reflect Phase Does Not Verify Lessons Before Reuse (RESILIENCE)

**Agent:** Resilience Review
**Location:** "Finding 3: Reflect Phase Does Not Guarantee Improved Decisions On Re-Entry"
**Severity:** P1 — Blind Spot

Inline Reflect (signal_score ≥ 4) pauses the loop and produces a lesson that immediately influences the next cycle. But there's no mechanism to verify the lesson is correct before re-entry:

**Example failure:** Test fails unexpectedly → Reflect fires → LLM lesson: "Tests are brittle; skip this test" → Loop resumes and skips the test → Test that should have been fixed is never debugged.

This violates PHILOSOPHY.md's core principle: "Evidence earns authority. Each level requires proof from the previous level."

**Impact:** Reflect can generate bad lessons that degrade subsequent decisions. The system gets worse, not better, when it "learns."

**Recommendation:** Implement two-stage Reflect:
1. **Stage 1 (inline):** Shallow reflection, emit evidence with `confidence < 1.0` (unproven)
2. **Apply cautiously:** If lesson suggests new routing, use it but monitor. If lesson suggests skipping a step, move it to "monitor" list instead.
3. **Stage 2 (async):** Deep reflection, interspect analyzes trends, lessons earn authority only after repeated demonstration (>15% improvement) or formal verification
4. Add Reflect audit loop: every 10 uses of a tentative lesson, check if it improved outcomes. If not, revert confidence.

---

#### Issue 1.3: Orient's "Mental Models" Are Not Implemented — Reification Risk (SENSEMAKING)

**Agent:** Sensemaking Review
**Location:** "Finding 1: Orient's Mental Models Are Not Yet Implemented"
**Severity:** P1 — Blind Spot

The brainstorm describes Orient producing "structured situation assessments" with fields like `current_state`, `active_patterns`, `anomalies`, `recommended_mental_model`. But the document never specifies:

- How agents **acquire** mental models (learning mechanism?)
- How agents **update** them after Reflect (gradient descent? Pattern matching? LLM reasoning?)
- What makes a model **valid** (test against territory?)
- How models degrade when conditions change

**Risk (Map/Territory Confusion):** When SituationAssessment JSON becomes the dominant artifact, agents will optimize for producing valid-looking JSON rather than accurate models. Agents will believe cached assessment even when conditions change (change blindness).

**Impact:** Agents develop overconfidence in their cached assessments, missing anomalies outside the schema's fields. The JSON becomes the territory, not a map of it.

**Recommendation:** Before formalizing OODAR loops:
1. Specify the mental model update mechanism (e.g., "Reflect computes delta_from_expectation and writes to evidence store; Orient reads evidence since last session to adjust priors")
2. Define success/failure criteria for a model (e.g., "model is valid if predictions match outcomes on last 10 similar situations")
3. Add a guard in Orient: "SituationAssessment is a prompt aid, not ground truth. Always verify recent evidence against cached assessment."

---

### P2 IMPORTANT — SHOULD FIX DURING PLANNING (Severity: P2, 8 unique issues)

#### Issue 2.1: Shared Observation Layer Is Self-Contained, Lacks External Signal (SENSEMAKING)

**Agent:** Sensemaking Review
**Location:** "Finding 2: Shared Observation Layer Could Be Itself a Single-Model Blind Spot"
**Severity:** P2

The observation layer aggregates **internal** Demarch state only: phase_log, dispatch_states, event bus, interspect DB, budget tracker. It includes no:

- External signal (test results from external CI? API uptime? User feedback?)
- Divergence detection (actual outcomes ≠ model predictions?)
- Boundary signals (anything breaking assumptions?)

**Example:** Model assumes "passing tests = agent did right thing." But tests are under-specified. All loops read the same snapshot and share the same blind spot. No loop detects the test suite is broken.

**Recommendation:**
1. Add "external signal" as required component of ObservationStore
2. Document which sources can fail independently
3. In multi-agent loop, require agents to exchange observations, not just actions. Disagreement is itself a signal.

---

#### Issue 2.2: Causal Inversion in De-Escalation (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 3: Causal Inversion in Escalation Chain"
**Severity:** P2

The escalation diagram shows de-escalation as "outer loops write to shared observation, inner loops read and adjust." But the causal direction is inverted due to pace layer mismatch:

- Per-turn operates at milliseconds
- By the time cross-session (hours) writes a calming assessment, per-turn has completed 100,000 cycles
- The "adjustment" arrives after the behavior it was trying to prevent

**Impact:** De-escalation only works if response arrives before the next significant decision. At stated tempo targets, cross-session de-escalation cannot causally prevent per-turn behavior within the same sprint.

**Recommendation:**
1. Distinguish **synchronous de-escalation** (sprint → per-turn, maybe feasible) from **asynchronous de-escalation** (cross-session → sprint, too slow to be causal)
2. For async de-escalation, accept it as "soft signal" not "binding constraint"
3. Design loop-pair specific escalation/de-escalation contracts

---

#### Issue 2.3: Reflection Storm via Shared Observation Layer (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 1: Reflection Storm via Shared Observation Layer"
**Severity:** P1 (ranked as P1 in original review, grouped here for synthesis)

When Inline Reflect fires (signal_score ≥ 4) and writes to shared observation layer, all four loops read the update and may simultaneously trigger their own Inline Reflect:

```
Inline Reflect fires → writes update → all loops read → each fires Inline Reflect
→ each writes more updates → cycle repeats (reinforcing loop, no rate limit)
```

In multi-agent scenarios, a single high-signal event could cause every agent to pause simultaneously, creating a reflection storm.

**Recommendation:** Add write-rate limiter to shared observation layer (anti-windup mechanism from Gridfire). Prevent single events from cascading across all loops simultaneously.

---

#### Issue 2.4: Orient Model Drift via Asymmetric Update Velocity (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 2: Orient Model Drift via Asymmetric Update Velocity"
**Severity:** P1 (ranked P1 in original)

The four loops' Reflect paths close at vastly different velocities:

- Per-turn Reflect: updates immediately (inline)
- Sprint Reflect: updates at phase end
- Cross-session Reflect: updates after 20-use canary window (hours/days)

Result: Fastest loop learns immediately and acts on updated models, while slowest loop is still operating on stale routing decisions. Per-turn agent fighting its own cross-session routing assignment for entire sprint.

**Impact:** PHILOSOPHY.md's flywheel (authority → actions → evidence → authority) assumes feedback closes in coherent timescale. Here they close at 1:1000:100,000 ratio. System could run in opposite directions simultaneously at different scales.

**Recommendation:** Define explicit "model reconciliation" semantics:
- When per-turn model conflicts with cross-session routing model, which wins?
- Is there a path for fast-loop learning to short-circuit canary window on strong evidence?
- Conduct BOTG analysis for routing model convergence velocity

---

#### Issue 2.5: Pace Layer Mismatch for Multi-Agent Loop (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 4: Pace Layer Mismatch for Multi-Agent Loop"
**Severity:** P2

The stated timescales are:

- Per-turn: milliseconds–seconds
- Per-sprint: minutes–hours
- Multi-agent: seconds–minutes ← sits BETWEEN per-turn (fast) and per-sprint (slow)
- Cross-session: hours–days

Loop 3 (conflict detection <1s, resolution <5s) is **faster than Loop 2** (phase transitions <5s). This violates pace layer theory: faster layers should innovate, slower layers should stabilize.

**Impact:** Loop 3 produces coordination decisions before Loop 2's context (sprint-level Orient) is current. Multi-agent reassignment could conflict with sprint phase advance, causing incoherent decisions.

**Recommendation:** Either:
1. Slow Loop 3 to be strictly between Loop 2 and Loop 4 (acceptable delays), OR
2. Add explicit lock-ordering protocol when Loop 3 and Loop 2 must decide within same 5s window, OR
3. Design Loop 2 to request coordination from Loop 3 rather than Loop 3 acting independently

---

#### Issue 2.6: Fast-Path Decision Routing as Goodhart Attractor (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 5: Fast-Path Decision Routing as Goodhart Attractor"
**Severity:** P2

Decision contract specifies: "If fast-path has match with confidence ≥ 0.8, use it." This creates optimization loop:

```
Reflect finds pattern → writes to model store → fast-path updated → future similar situations
hit fast-path → LLM deliberation bypassed → no new Reflect evidence → pattern calcifies
```

Over time, system handles more via fast-path, less via deliberation, less evidence generation, over-optimization for observed conditions, poor handling of novel situations.

**Impact:** System becomes brittle. Perfect optimization for observed history means any novel condition is catastrophic.

**Recommendation:** Apply PHILOSOPHY.md's anti-Goodhart principle:
1. Random audit rate: 5% of fast-path-eligible decisions forced through deliberate path
2. Track deliberate-path invocation rate as health metric
3. If deliberate path drops below threshold (e.g., 3% of decisions), trigger model refresh

---

#### Issue 2.7: Loop Conflict Resolution Undefined (USER/PRODUCT)

**Agent:** User/Product Review
**Location:** "Finding 4: Missing Edge Cases — When loops disagree"
**Severity:** P2

The document describes escalation and de-escalation but does not define:

- What constitutes disagreement vs normal escalation
- What happens if per-turn wants to continue but sprint detected budget overrun and wants to stop
- Whether de-escalation is binding or advisory
- What inner loop does if it disagrees with de-escalation

**Example scenario:** Per-turn OODAR produces signal_score = 6 (wants inline Reflect), but sprint OODAR is mid-phase-transition. Does per-turn Reflect pause mid-transition? Does sprint subsume per-turn Reflect?

**Recommendation:** Define conflict resolution protocol:
1. Priority ordering: when loops want different actions, which wins?
2. Timeout handling: if pause exceeds N seconds, does loop resume or escalate?
3. Binding vs advisory: de-escalation guidance vs constraint

---

#### Issue 2.8: Success Criteria and Metrics Missing (USER/PRODUCT)

**Agent:** User/Product Review
**Location:** "Finding 5: Success Criteria"
**Severity:** P2

The document defines tempo targets but provides no measurable success criteria:

- Leading indicator (observable within 2 sprints): Does `ic situation snapshot` reduce CLI calls before first action?
- Lagging indicator (observable in 30 days): Does per-sprint OODAR reduce mid-sprint course corrections?
- Quality indicator: Does Reflect increase signal_score distribution?
- Cost indicator: Does OODAR reduce cost per landable change?

**Impact:** Plan has no completion criterion beyond "it ships." Without metrics, can't measure whether OODAR is working or causing regression.

**Recommendation:** Define before planning:
1. One leading indicator measurable within 2 sprints
2. One lagging indicator measurable within 30 days
3. Cost impact on north star metric ($1.17 per landable change)

---

### P3 NICE-TO-HAVE / CONSIDER ALSO (Severity: P3, 6 unique issues)

#### Issue 3.1: Cache Invalidation Problem Is Understated (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 7: Orient Cache Invalidation Problem Is Understated"
**Severity:** P3

The document correctly identifies cache invalidation as "the hard problem" in Open Question 1, but understates it. At <100ms per turn, a stale cache lasting 10 seconds means 100+ decisions on incorrect context.

**Recommendation:** Define:
1. Maximum acceptable staleness window for per-turn situation assessment cache
2. Is cache invalidated on push (event subscription) or pull (per-cycle check)?
3. Failure mode when two per-turn loops hold conflicting cached Orients simultaneously

---

#### Issue 3.2: Reflect Phase Has No Defined Failure Mode (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Finding 6: Reflect Has No Defined Failure Mode"
**Severity:** P3

Reflect has two failure modes with different consequences:

- **Inline Reflect failure:** Loop paused, reflection fails → indeterminate state. Loop expected to resume with updated inputs but inputs never updated.
- **Async Reflect failure:** Silent failure → no evidence written but loop continues unaware.

PHILOSOPHY.md states "every failure produces a receipt." Reflect's failure to produce evidence should produce its own receipt.

**Recommendation:** Define:
1. Timeout policy for inline Reflect. If pause > N seconds, resume with old model or escalate?
2. Monitoring for async Reflect failure (liveness check on evidence accumulation process)
3. Transactional semantics for model store (prevent partial updates)

---

#### Issue 3.3: Multi-Agent Deadlock Prevention Is Unspecified (RESILIENCE)

**Agent:** Resilience Review
**Location:** "Finding 6: Multi-Agent Loop Has No Explicit Deadlock Prevention"
**Severity:** P2 (ranked P2 in original)

The multi-agent loop is reactive: agents acquire locks and resolve conflicts post-hoc. Latent deadlock vulnerability:

```
Agent A: holds lock X, waits for lock Y (held by B)
Agent B: holds lock Y, waits for lock X (held by A)
```

No explicit deadlock detection SLA, recovery strategy, or escalation path.

**Recommendation:**
1. **Proactive:** Lock acquisition ordering (all agents acquire in same order)
2. **Reactive:** Detect deadlock at lock wait > 5s
3. **Recovery:** Grace period for voluntary release → forced yield (lower-priority agent) → escalation to human
4. **Monitoring:** Count deadlock attempts per session; if >3, escalate

---

#### Issue 3.4: Cross-Session Loop Recovery Time is Unspecified (RESILIENCE)

**Agent:** Resilience Review
**Location:** "Finding 5: Cross-Session Loop Recovery Time is Unspecified"
**Severity:** P2

Cross-session loop has 24-hour tempo (slow, appropriate). But no circuit breaker for catastrophic failures:

Example: Bad routing sends complex tasks to Haiku for 3 days, post-merge quality drops 50%. How long to recover? Canary window (20 uses) + proposal cycle (100 uses) + human approval = potentially days of degradation.

**Recommendation:** Add anomaly fast-path:
1. If canary failure rate exceeds 20% in single window → immediately escalate to human
2. Optionally auto-revert routing override
3. Use progressive confidence decay: older data loses authority over time

---

#### Issue 3.5: Approach A vs B False Dichotomy (DECISION QUALITY)

**Agent:** Decision Quality Review
**Location:** "Finding 1: False Dichotomy — Hidden Hybrid Option"
**Severity:** P1 (ranked P1 in original)

The document frames choice as binary (Approach A vs B), but a **Hybrid-First option** dominates both:

1. **Phase 1 (weeks 1-2):** Ship Approach A Steps 1-2 (immediate value, proven)
2. **Phase 2 (weeks 3-4):** Extract interfaces from working code (risk eliminated, interface inferred not imposed)
3. **Phase 3 (weeks 5+):** Migrate remaining loops incrementally

This gets Gridfire composability without accumulating ad-hoc contracts as debt, and avoids premature abstraction by building interface FROM proven code.

**Recommendation:** Reframe decision as sequencing, not binary choice: "Start with A's delivery, migrate to B's structure as interfaces stabilize."

---

#### Issue 3.6: Reversibility and Migration Cost Understated (DECISION QUALITY)

**Agent:** Decision Quality Review
**Location:** "Finding 2: Reversibility and Migration Cost Underestimated"
**Severity:** P2

Approach B lists weakness "no formal abstraction" implies A→B migration is expensive. But actual cost is overstated:

Migration path (non-disruptive, in-place):
1. Keep all A implementations (snapshots, schemas, tables)
2. Define generic interface OVER them
3. Wrap existing code without rewriting
4. New loops implement interface from start

Actual cost: ~3-5 days non-disruptive refactor, not rewrite.

**Recommendation:** Add migration-cost section showing A→B is low-cost local refactor. This reduces A's perceived downside.

---

#### Issue 3.7: Missing T=0, T=6mo, T=2yr Analysis (SYSTEMS THINKING)

**Agent:** Systems Thinking Review
**Location:** "Cross-Cutting Observation: The Document Is Missing T=0, T=6mo, T=2yr Analysis"
**Severity:** P3

The document describes system at steady-state, not temporal trajectory:

- **T=0:** Fast-path routing tables empty, every decision hits deliberate path, system slower than current bash implementation
- **T=6mo:** Fast-path hit rate rising, over-adaptation risk becomes visible
- **T=2yr:** System optimized for observed patterns, blind spots correspond to systematic biases in task selection

**Recommendation:** Address: what does healthy model store evolution look like? How is stagnation detected?

---

## Unique Findings by Agent (Non-Convergent)

### Architecture Review Unique Insights

1. **Module boundary must be explicit:** `ObservationStore` and `ic situation` belong in intercore. `OODARLoop` generic interface does NOT belong in intercore public surface—should live in `intercore/internal/oodar/` or `sdk/interbase/`.

2. **Interspect's layer affiliation unclear:** Is interspect L1 (kernel service) or L2 (OS)? This must be resolved before designing shared observation layer, or `ic situation` will violate layer boundaries.

3. **Premature abstraction risk in Approach B:** Generic interface with 5 type parameters before all four loops are validated means interface could become a straitjacket. Multi-agent loop (least developed) will be last to exercise design.

### Systems Thinking Review Unique Insights

1. **Temporal dimensionality:** Document lacks T=0/T=6mo/T=2yr analysis. System performance will degrade over time as it over-optimizes for observed patterns.

2. **Anti-Goodhart mechanism missing:** Fast-path confidence threshold (0.8) is a Goodhart attractor. Must include forced deliberation audit rate (5%) to keep LLM capabilities calibrated.

### Decision Quality Review Unique Insights

1. **Anchoring on Boyd's OODA:** Document strongly anchors on military model. Real problem is "structured orientation + learning signals," not OODA extension. Should reframe to Demarch's philosophy (evidence → authority).

2. **Reflect phase conflation (distinct from convergent finding):** The two learning modes (within-cycle React vs cross-cycle Reflect) should be distinct primitives with different signatures and storage.

### User/Product Review Unique Insights

1. **Scope creep risk:** Document proposes shipping all 4 loops, 2 approaches, dual-mode reflect, significance classifiers simultaneously. 80% case is: `ic situation` + per-sprint OODAR. Multi-agent and cross-session should be deferred.

2. **Bundled work items:** Five distinct work items conflated:
   - `ic situation snapshot` (standalone, ship independently)
   - Situation assessment schema (with Loop 2)
   - Decision contracts (useful without OODAR)
   - Dual-mode reflect formalization (extends iv-8jpf)
   - OODAR vocabulary in docs (zero-cost, pure clarification)

3. **Loop conflict protocol undefined:** When per-turn and sprint loops disagree, which wins? De-escalation binding or advisory?

### Resilience Review Unique Insights

1. **Staged rollout recommendation:** Choose Approach A for next sprint with planned transition to B at N+3 (after Approach A proven). Combines immediate value with long-term option.

2. **Two-stage Reflect:** Inline reflection should emit tentative lessons with low confidence, applied cautiously. Deep reflection (async) verifies lessons, earning authority through repeated demonstration.

3. **Anomaly fast-path for routing:** Add circuit breaker for cross-session loop: if canary failure > 20%, immediately escalate to human (don't wait 24h).

### Sensemaking Review Unique Insights

1. **Reification risk is acute:** "Mental models" are described as first-class Orient outputs but implementation is missing. Agents will optimize for valid-looking JSON rather than accurate maps of reality.

2. **Signal/noise separation missing:** Observe gathers raw data; Orient receives it unfiltered. No classification mechanism specifies which observations should trigger model updates vs which are noise.

3. **Loop count forecast missing:** Choice between A (low cost for 4 loops) vs B (high upfront, better for 5+ loops) depends on forecastedloop count by end of year. Forecast is absent.

---

## Verdict

### Overall Assessment: **NEEDS CHANGES**

**The OODAR design is architecturally sound and philosophically grounded, but has critical gaps that must be resolved before implementation. The primary recommendation is Approach A (bottom-up), starting immediately with the Shared Observation Layer.**

**Verdict breakdown by approach:**

**Approach A (Bottom-Up):** ✅ **RECOMMENDED** for immediate work (next 2-4 sprints)
- **Pros:** Low risk, incremental delivery, battle-tested foundations, ships value immediately
- **Cons:** Contracts couple to existing code, harder to add new loops, technical debt accumulates
- **Recommendation:** Implement Approach A Steps 1-2 immediately. Plan transition to B at N+3 once patterns stabilize.

**Approach B (Top-Down):** ⚠️ **DEFER** until proof of concept
- **Pros:** Formal composability, type safety, aligns with Gridfire, testable in isolation
- **Cons:** Premature abstraction risk (multi-agent loop unvalidated), higher upfront cost, interface may constrain future design
- **Recommendation:** Do NOT commit to generic interface before SprintLoop and TurnLoop are proven stable. Approach A→B migration path is cheaper than document suggests.

**Hybrid-First (Recommended):** ✅ **START HERE**
1. **Phase 1 (now):** Implement Approach A Steps 1-3 (`ic situation`, schemas, decision contracts)
2. **Phase 2 (N+2):** Measure impact; decide on Approach B based on evidence
3. **Phase 3 (N+3):** If abstraction cost is justified, extract interfaces from working code

---

## Critical Blockers (Must Resolve Before Plan)

The following must be addressed in planning phase before any OODAR implementation begins:

### BLOCKER 1: Resolve Interspect's Layer Affiliation
**Severity:** P1 — Blocks observation layer design
**Action:** Determine whether interspect (evidence store) is L1 (kernel), L2 (OS), or separate service. This determines whether `ic situation` can query it without violating layer boundaries.

### BLOCKER 2: Design Escalation and De-Escalation Contracts
**Severity:** P1 — Blocks loop implementation
**Action:** Define when loops escalate (what signal? what thresholds?), what de-escalation means (binding vs advisory?), and what happens when loops disagree.

### BLOCKER 3: Verify Per-Turn Tempo Budget
**Severity:** P2 — Blocks per-turn OODAR formalization
**Action:** Measure `ic situation snapshot` latency and Orient caching costs with realistic data. If total > 50ms, the <100ms target is infeasible.

### BLOCKER 4: Design Reflect Verification Mechanism
**Severity:** P1 — Blocks learning loop viability
**Action:** Specify how inline Reflect verifies lessons before reuse. Implement two-stage reflection (tentative → verified) with audit loop to prevent bad lessons from degenerating future decisions.

### BLOCKER 5: Define Mental Model Update Mechanism
**Severity:** P1 — Blocks Orient abstraction
**Action:** Specify how agents acquire, update, and validate mental models. Prevent reification risk where JSON assessment becomes the territory agents believe in.

---

## Recommended Path: Phased Implementation

### **Phase 1 (Weeks 1-2): Observation Layer Ship**

**Goal:** `ic situation snapshot` in production, all other loops benefit immediately
**Scope:** Approach A, Steps 1-2
- Build unified observation command (`ic situation snapshot --consumer=<loop>`)
- Define situation assessment schema (per-turn, sprint, cross-session versions)
- Add health checks and circuit breaker for timeout handling

**Blockers to resolve:** Interspect layer affiliation, snapshot SLA and fallback paths

**Deliverables:**
- `ic situation snapshot` command
- Situation assessment JSON schema (versioned)
- Monitoring: snapshot latency, cache hit rate, timeout events

**Success criteria:**
- Every OODAR loop can call `ic situation snapshot` instead of 5+ separate CLI queries
- Snapshot latency <50ms at P95 (required for per-turn budget)
- Zero unhandled snapshot timeouts (circuit breaker working)

---

### **Phase 2 (Weeks 3-4): Decision and Reflect Contracts**

**Goal:** Formalize Orient output schema and decision routing; verify loop-level contracts work
**Scope:** Approach A, Steps 3-4
- Extract routing tables to queryable JSON (fast-path decision mechanism)
- Formalize Reflect dual-mode (inline vs async) with verification mechanism
- Add OODAR vocabulary to PHILOSOPHY.md, sprint skills, Interspect docs (zero-effort, high clarification value)

**Blockers to resolve:** Escalation contracts, Reflect verification mechanism, mental model update spec

**Deliverables:**
- Routing tables JSON schema + query interface
- Situation assessment schema (refined from Phase 1)
- Reflect contract: inline (tentative lesson, low confidence) vs async (verified, high confidence)
- Documentation: OODAR vocabulary in existing docs

**Success criteria:**
- Per-sprint OODAR loop successfully uses routing tables (fast-path confidence >= 0.8)
- Inline Reflect fires for signal_score >= 4, emits tentative lesson with confidence < 1.0
- Async Reflect accumulates evidence and verifies lessons (no bad lessons deployed)

---

### **Phase 3 (Weeks 5-8): Interface Extraction (If Justified)**

**Goal:** Evaluate whether generic `OODARLoop` interface adds value; extract if justified
**Scope:** Conditional on Phase 1-2 proving contracts are stable
- Measure: How many times did situation assessment schema need revision? How many decision routing conflicts?
- Measure: Is there >20% code duplication between sprint and per-turn loop implementation?
- Decision gate: If contracts stable AND duplication present, proceed to interface extraction

**If gate passes:**
- Define generic `OODARLoop` interface in `sdk/interbase/` (not intercore public surface)
- Implement for SprintLoop first (most mature)
- Plan TurnLoop next; CoordinationLoop last (least mature)

**If gate fails:**
- Continue with Approach A contracts indefinitely (proven working, low-risk)
- Document decision and rationale for future reference

**Blockers to resolve:** None (previous phases cleared blockers)

**Deliverables:**
- Generic interface (if justified)
- SprintLoop + TurnLoop implementations of interface
- Interface stability report

**Success criteria:**
- Interface reduces code duplication by >30%
- Adding new loop level requires <5 days work (vs >2 weeks for bespoke implementation)

---

### **Phase 4 (Weeks 9+): Multi-Agent Coordination Loop (Deferred)**

**Goal:** Implement CoordinationLoop once other loops proven stable
**Scope:** Deferred until Phase 3 complete
- Spike minimal coordination model (2 agents, 1 conflict scenario)
- Test interface against real multi-agent scenario
- Design deadlock prevention and recovery

**Note:** This is the highest-risk loop and should not be attempted until other loops are production-proven.

---

## Action Items (Priority Order)

### Immediate (Block implementation planning)

1. **Resolve interspect layer affiliation**
   - Is it L1 (kernel service)? L2 (OS artifact)? Separate service?
   - Document answer and impact on `ic situation` design
   - Owner: Architecture decision

2. **Design escalation/de-escalation contracts**
   - Define when loops escalate (thresholds, signals)
   - Specify de-escalation mechanism (binding vs advisory)
   - Define loop conflict resolution
   - Document per-loop pair specific contracts

3. **Specify Reflect verification mechanism**
   - Define two-stage reflection (tentative → verified)
   - Design audit loop (verify lesson effectiveness every 10 uses)
   - Implement confidence decay for tentative lessons

4. **Verify per-turn tempo budget**
   - Measure `ic situation snapshot` actual latency with production data
   - Measure LLM Orient latency (inference + caching overhead)
   - If combined < 50ms achievable, proceed to Phase 1. If not, redesign or defer per-turn OODAR.

5. **Define mental model update mechanism**
   - Specify how agents acquire, update, validate models
   - Add reification guards to prevent JSON becoming territory
   - Document model validity criteria and failure modes

---

### Phase 1 Prep (Weeks -1 to 0)

6. **Design `ic situation snapshot` command**
   - Scope: which fields per consumer type (per-turn vs sprint vs cross-session)?
   - SLA: <50ms at P95, circuit breaker on timeout
   - Fallback: what each loop does without snapshot?

7. **Define situation assessment schema**
   - Versioning strategy
   - Required fields (per-turn, sprint, cross-session)
   - `signal_quality` field (confidence in observation)

8. **Plan monitoring and success metrics**
   - Snapshot latency histogram
   - Cache hit rate per loop
   - Timeout/circuit-breaker events
   - Leading indicator: CLI call reduction for agents

---

### Phase 1 Execution (Weeks 1-2)

9. **Implement `ic situation snapshot` command**
   - Query phase_log, dispatch_states, event bus, budget tracker
   - Return JSON per consumer filter
   - Add circuit breaker (return cached data with `stale: true` on timeout)
   - Add health check: `ic situation health`

10. **Update PHILOSOPHY.md**
    - Add OODAR vocabulary section
    - Clarify evidence → authority → actions cycle IS OODAR at nested timescales
    - Add reification guard: "SituationAssessment is a prompt aid, not ground truth"

---

## Appendix: Convergence Matrix

| Finding | Architecture | Systems | Decision | User/Product | Resilience | Sensemaking | Severity | Verdict |
|---------|--------------|---------|----------|--------------|------------|-------------|----------|---------|
| Observation layer high-value | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P0 (Strength) | SHIP FIRST |
| Loop 3 immaturity | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | P2 | DEFER TO N+6 |
| Reflect conflates concepts | ✅ | ✅ | ✅ |  | ✅ | ✅ | P2 | MUST SPLIT |
| Per-turn tempo risky | ✅ | ✅ | ✅ | ✅ |  |  | P2 | MEASURE FIRST |
| Escalation undefined | ✅ | ✅ | ✅ | ✅ | ✅ |  | P2 | DESIGN FIRST |
| Shared observation SPOF | ✅ | ✅ |  | ✅ | ✅ | ✅ | P1 | DESIGN FALLBACK |
| Reflect verification missing |  |  |  |  | ✅ | ✅ | P1 | DESIGN FIRST |
| Orient not implemented |  |  |  |  |  | ✅ | P1 | DESIGN FIRST |

---

## Summary for Next Phase

The OODAR brainstorm is **ready for planning with amendments**. Do NOT proceed to detailed implementation without resolving the five blockers listed above.

**Recommended next step:** Convene planning session with findings from this synthesis. Allocate 3-4 days to:
1. Resolve five blockers (decision, design, or documented rationale)
2. Sketch Phase 1 detailed scope (Weeks 1-2)
3. Define success metrics and rollout strategy

**Do NOT choose between Approach A and B now.** The hybrid-first path (A → B transition) is lower-regret and keeps options open.

The design is sound. The implementation path is achievable. The gap is in the details of loops, contracts, and edge cases. Address those first, then the plan will be solid.
