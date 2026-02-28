# Sensemaking Review: OODAR Loops Brainstorm
**Date:** 2026-02-28
**Reviewer Role:** Flux-drive Sensemaking Agent
**Review Scope:** Mental models, information quality, temporal reasoning, perceptual biases
**Document:** `/home/mk/projects/Demarch/docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`

---

## Executive Summary

The OODAR loops brainstorm presents a sophisticated framework for nested decision-making across four timescales. **Strengths**: grounded in philosophy (PHILOSOPHY.md), addresses a real gap (explicit Reflect phase), and preserves incremental value via Approach A. **Blind spots**: 1) the "mental models" and "situation assessment" abstractions are performative (described as "explicit" but unimplemented), 2) the shared observation layer risks becoming a map that agents mistake for territory, 3) the four timescales assume cleaner separation than real agent workflows exhibit, 4) both approaches under-specify how Orient distinguishes signal from noise, and 5) the multi-agent coordination loop (Loop 3) is the most immature yet framed as parallel to mature loops.

**Key Finding**: The document conflates "naming existing patterns with OODAR vocabulary" (Approach A) and "building formal abstractions" (Approach B) as different paths to the same destination. They're not. Approach A is descriptive; Approach B is prescriptive. Choosing one requires acknowledging the other's cost, not pretending both deliver equivalent value.

---

## Findings

### 1. **[P1 BLIND SPOT] Orient's "Mental Models" Are Not Yet Implemented — Reification Risk**

**Location:** Sections "Step 2: Situation Assessment Schema" (lines 155-175) and "The OODAR Primitive" (lines 244-284).

**Issue:** The brainstorm describes Orient producing a "structured situation assessment" with fields like `current_state`, `active_patterns`, `anomalies`, `recommended_mental_model`. But the document never specifies:
- How agents **acquire** mental models (what's the learning mechanism?)
- How agents **update** mental models after Reflect (is it gradient descent? Pattern matching? Conversation?)
- What makes a mental model **valid** (how do we test it against the territory?)
- How models degrade when conditions change (e.g., codebase structure changes, deployment pipeline breaks).

**Per-turn example (Loop 1, line 172):** "Agent produces [situation assessment] as structured output in its reasoning, cached across turns." But the agent's reasoning IS the LLM's token-by-token inference—there's no separate "mental model" object being manipulated. The cache would store the LLM's summary, not a model of the agent's internal beliefs.

**Risk - Map/Territory Confusion:** When the SituationAssessment JSON becomes the dominant artifact, agents will optimize for producing valid-looking JSON rather than accurate models. The JSON structure will become the territory ("the situation IS what the assessment says"), causing:
- Agents to believe their cached assessment even when external conditions change (change blindness)
- Overconfidence in the assessment confidence field (Goodhart: optimizing a metric that measures confidence)
- Missed anomalies outside the schema's fields

**Recommendation:**
- Specify the mental model update mechanism before naming OODAR loops (e.g., "Reflect computes delta_from_expectation and writes to evidence store; next session, Orient queries evidence store to adjust expectations").
- Define success/failure criteria for a mental model (e.g., "model is valid if its predictions match outcomes on the last 10 similar situations").
- Acknowledge the reification risk in PHILOSOPHY.md or add a guard: "SituationAssessment is a prompt aid, not ground truth. Orient always verifies recent evidence against cached assessment."

---

### 2. **[P1 BLIND SPOT] Shared Observation Layer Could Be Itself a Single-Model Blind Spot**

**Location:** Section "Loop Communication: Hybrid Architecture" (lines 28-57), particularly the Observation snapshot structure (lines 136-148).

**Issue:** The shared observation layer (ObservationStore) aggregates state from:
- `phase_log` (phase state)
- `dispatch_states` (agent state)
- `event bus` (phase + dispatch events)
- `interspect DB` (evidence patterns)
- `budget tracker` (token spend)

All these sources are **internal to Demarch**. The snapshot includes no:
- External signal (test results from external CI? API uptime? User feedback?)
- Divergence detection (are actual outcomes matching our model's predictions?)
- Boundary signals (anything that breaks our assumptions about the environment?)

**Scenario:** Suppose Demarch's internal model assumes "successful test execution = agent did the right thing." The ObservationStore will never see that the test suite is under-specified or that the codebase's external contracts are broken. The agent's Orient phase will read the observation snapshot, find "tests passing," and proceed with high confidence in a wrong model.

**Information Quality Problem:** The observation layer is **informationally self-contained**. All loops read the same snapshot, so they share the same blind spots. A diversified observation system would include external signal sources (external validators, user corrections, production metrics) that **disagree with internal signal**.

**Recommendation:**
- Add "external signal" as a required component of ObservationStore (e.g., last external validation result, drift from expected behavior per interspect).
- Document which observation sources can fail independently (if the event bus is down, what do agents believe?).
- In the multi-agent loop, require agents to exchange **observations**, not just coordinate on actions. Disagreement between agents' internal states and shared observation is itself a signal.

---

### 3. **[P2 MISSED LENS] Orient Receives Raw Data But Never Formalizes Signal/Noise Separation**

**Location:** Loop descriptions (lines 61-116), particularly the "Observe" phases across all four loops.

**Issue:** Each loop's Observe phase gathers data:
- Per-turn: "Tool result, file state, test output" (line 67)
- Sprint: "Phase state, gate results, artifacts" (line 81)
- Multi-agent: "Agent heartbeats, lock state, dispatch poll" (line 95)
- Cross-session: "Interspect evidence collection" (line 109)

But there is **no filtering mechanism** described. What makes a tool result "signal" vs "noise"? How does Orient distinguish a meaningful change in file state from a transient compile error? How does a sprint loop know if a phase transition's delay is concerning (blocks decision) vs routine (expected variance)?

**Current State:** The document mentions "signal scoring" in Reflect (line 71, 184) but signal scoring is a **decision** about whether to pause the loop—it's not a measurement of observation quality. Example: `auto-stop-actions.sh` likely looks at whether something went wrong, not at whether the signal is strong enough to update the model.

**Variant of Availability Heuristic:** Vivid signals (test failures, deadline reached, lock contention) will be over-weighted. Absence of signal (no recent evidence of a pattern) will be under-weighted (failure to detect that something stopped happening). Orient will optimize for reacting to present data, not for noticing what's absent.

**Recommendation:**
- Define a signal classification for each loop (e.g., "per-turn signal classes: error, state_change, completion, timeout, anomaly; each has a threshold for triggering Orient update").
- In the SituationAssessment schema, add `signal_quality` (range 0-1) indicating how confident the observation is. High-quality signal updates cached models; low-quality signal is noted but doesn't update.
- Document which observations are **required** (Orient must fail safely if unavailable) vs **optional** (useful but not blocking).

---

### 4. **[P2 MISSED LENS] Temporal Reasoning: Four Timescales Assume Cleaner Separation Than Reality Exhibits**

**Location:** Loop definitions (lines 61-116) and timescale assignments (lines 73, 87, 101, 115).

**Issue:** The four loops are assigned distinct timescales:
- Per-turn: milliseconds–seconds (line 73)
- Per-sprint: minutes–hours (line 87)
- Multi-agent: seconds–minutes (line 101)
- Cross-session: hours–days (line 115)

In reality, agent workflows blur these boundaries:
1. **A per-turn decision cascades to sprint scope.** An agent's tool call fails; the turn loop records signal_score=5; this immediately triggers escalation to sprint loop to reconsider the phase. Per-turn and sprint loops execute simultaneously, not in sequence.
2. **A multi-agent conflict blocks per-turn progress.** Agent A's turn loop is waiting for a lock held by Agent B (multi-agent loop's scope). The per-turn loop can't proceed because of multi-agent timescale concerns.
3. **Cross-session learning arrives mid-session.** Interspect finishes processing evidence and proposes a routing override (cross-session loop outcome). A sprint loop decides to dispatch a different agent for the next task. Now the cross-session loop affects per-sprint decisions mid-session.

**Temporal Discounting:** The brainstorm under-weights consequences across timescales. Example: optimizing per-turn speed (fast-path decisions, <100ms overhead) might disable the multi-agent loop's conflict detection, which causes costly re-work at sprint scope. The document emphasizes tempo targets (line 73, 87, 101, 115) but doesn't balance speed against safety across scales.

**Paradigm Shift Risk:** If timescales blur in practice, the abstraction (four nested loops with clean separation) becomes a "mental model mismatch with reality." Agents will act as if loops are independent when they're actually entangled, leading to deadlocks or missed escalations.

**Recommendation:**
- Document explicit **escalation triggers** (when does a per-turn loop signal escalate to sprint? when does sprint escalation trigger multi-agent coordination?).
- Specify **wait semantics**: when a per-turn loop discovers it needs multi-agent coordination, what's the blocking behavior? (Pause? Retry? Escalate?)
- In temporal reasoning, acknowledge the tension: "Four timescales assume independence; in practice, they'll interfere. Design for safe degradation: what's the minimum set of signal each loop needs from others to avoid bad decisions?"

---

### 5. **[P2 MISSED LENS] Multi-Agent Coordination Loop (Loop 3) Is Least Mature Yet Framed As Parallel Peer**

**Location:** Loop 3 definition (lines 89-101) and Approach B's implementation order (lines 355-365).

**Issue:** The document correctly identifies Loop 3 as the biggest gap:
> "Orient: No explicit coordination model — **Biggest gap** — agents don't model each other's state" (line 96)

But then Approach B proposes implementing CoordinationLoop **last** (lines 362-365), after TurnLoop, SprintLoop, and LearningLoop are mature. This is a valid architectural choice—stabilize interfaces before tackling the hardest problem.

**However**, the document frames all four loops as **compositional peers** (line 407 in comparison table: all three approaches show them equally). The mental model is: "All four loops are OODAR instances; they differ only in scope." But Loop 3 lacks:
- A clear **model store** (what does "coordination models" mean? line 308: agent trust scores + conflict history—vague)
- A proven **significance classifier** (what makes a conflict worth inlining reflection vs async?)
- Any example of the **feedback loop** (agent commits a conflict; does it update the coordination model for next session?)

**Perspective-Taking Failure:** The brainstorm doesn't model what the **human operator** sees. From their perspective:
- Loops 1, 2, 4 are mostly infrastructure already in place. Approach A would add naming and caching; manageable risk.
- Loop 3 is a new capability, and it's being designed in a vacuum (no tested foundations, no reference implementations).

Framing Loop 3 as a parallel peer hides the risk that implementing it **last** means less time for iteration. If it's truly parallel, it should be designed and tested in parallel with others, or its immaturity should be explicitly marked as P0 risk in decision-making.

**Recommendation:**
- Distinguish **infrastructure-level loops** (1, 2, 4—fit into existing architecture) from **new-capability loops** (3—requires new mechanisms).
- If Loop 3 is deferred to "last," mark it as P0: "Multi-agent coordination is not yet a first-class loop. Loop 3 implementations will be reactive (lock-based claims) until coordination models and significance classifiers are designed separately."
- Alternatively: spike Loop 3 in parallel. Design the CoordinationModel interface with minimal implementation. Test with two agents and one conflict scenario.

---

### 6. **[P3 CONSIDER ALSO] Model Store Evolution and Paradigm Shifts Are Under-Specified**

**Location:** Approach B, lines 273-278 (ModelStore interface) and across both approaches—no mention of paradigm shifts.

**Issue:** The ModelStore interface assumes models can be **updated** incrementally:
```go
Update(ctx context.Context, key string, update ModelUpdate) error
```

But what happens when the underlying **category of things** changes? Examples:
- A test suite becomes unreliable (the category "passing test = good" becomes invalid).
- An agent's assigned role changes (its operational model shifts).
- A new pillar is added to Demarch (the coordination model needs new concepts).

The document mentions "paradigm shifts" in the perceptual biases context (line 8 in this sensemaking review: "Paradigm Shift") but never addresses how OODAR loops detect or adapt to them. A paradigm shift is invisible to Orient unless **reflection explicitly checks for category errors**.

**Example of Risk:** Interspect accumulates evidence that routing-to-Agent-A is working poorly. Reflect updates the routing model: "reduce Agent A's load." But what if the real problem is "Agent A's skill tier has changed"—a paradigm shift, not a parameter adjustment? Incrementally lowering Agent A's allocation won't fix it. The system will confuse a **category shift** with **parameter drift** (temporal discounting applied to structural change).

**Recommendation:**
- In Reflect, add a step: "Does the evidence violate assumptions about the model's category?" Example: "Did we assume all agents can execute the full agent lifecycle? Is that still true?"
- Define a "model invalidation threshold" for each mental model (e.g., "if prediction error exceeds 0.5 for 3 consecutive cycles, invalidate and rebuild").
- Document that Orient must be prepared to replace models, not just update them.

---

### 7. **[P3 CONSIDER ALSO] Fast-Path vs. Deliberate-Path Confidence Coupling**

**Location:** Step 3 (lines 177-192) and "Decision Contracts" discussion.

**Issue:** The proposed decision routing (line 192):
> "If fast-path has a match with confidence ≥ 0.8, use it. Otherwise, invoke LLM deliberation."

This couples **two independent things**:
1. **Routing decision** (which decision engine to invoke)
2. **Confidence threshold** (when to trust the fast path)

A fast-path match with 0.8 confidence is still a decision. Who decided 0.8 is the right threshold? If the decision's consequence is high-stakes (shipping a change), 0.8 might be too low. If it's low-stakes (which test to run first), 0.8 might be too high. But the brainstorm treats the threshold as universal.

**Goodhart's Law Risk:** Once the 0.8 threshold is published, fast-path routing tables will optimize to produce confidence scores that exceed 0.8, rather than honest confidence estimates. "This pattern matches the current situation" (honest) becomes "this pattern matches the current situation with 0.85 confidence" (optimized for threshold).

**Recommendation:**
- Decouple confidence from routing: report confidence honestly, but use a **separate significance classifier** (already mentioned in line 280-283) to decide routing. Example: "Fast-path confidence=0.7, but the decision's stakes are high, so invoke LLM."
- Make the confidence-to-routing mapping explicit and auditable.

---

### 8. **[P2 MISSED LENS] Approach Comparison Hides a Real Trade-Off: Implementation Complexity vs. Reusability**

**Location:** "Approach Comparison Summary" (lines 401-412).

**Issue:** The comparison table presents "Risk," "Time to first value," etc. as independent dimensions. But they're coupled:

| Dimension | Root Cause |
|-----------|-----------|
| **Approach A (low risk)** → But higher coupling, harder to add new loops | Contracts layered on existing code re-implement OODAR at each level |
| **Approach B (slower start)** → But more reusable, easier to add loops | Generic interface requires upfront investment, payoff scales with loop count |

The real trade-off is: **how many loops will exist in the end state?**

- If ≤ 4 loops ever exist, Approach A wins (lower total implementation cost).
- If ≥ 5 loops will exist (e.g., cross-project loop, cross-team loop, analytics loop), Approach B wins (amortized cost of the generic interface drops below ad-hoc implementations).

The brainstorm doesn't forecast the number of loops. It only specifies four now, with "open questions" about scope (line 395: "Should the OODAR primitive be in intercore or clavain?"), not about the long-term loop count.

**Narrative Fallacy:** The comparison presents both approaches as "paths to the same destination," implying they're equivalent given different constraints. But Approach A is inherently limited: each new loop costs O(n) effort where n = complexity of that loop's context. Approach B is inherently better at reuse: each new loop costs O(1) interface implementations.

**Recommendation:**
- Forecast: how many loops does Demarch need by 2026-Q4? If >4, Approach B wins outright despite higher upfront cost.
- If uncertain, propose Approach A + plan for eventual interface extraction (strangler-fig pattern): build contracts, prove them work at two scales, then generalize.

---

## Key Lenses Applied

| Lens | Finding |
|------|---------|
| **Map vs. Territory** | SituationAssessment JSON risks becoming the territory agents believe in, causing change blindness when reality diverges |
| **Reification** | "Mental models" and "situation assessments" are treated as first-class objects in Orient, but implementation is missing—descriptions are performative |
| **Signal vs. Noise** | Observe gathers raw data; Orient receives it unfiltered; no separation mechanism specified |
| **Leading vs. Lagging Indicators** | Timescale separation assumes independence; real workflows blur boundaries, risking cascading decisions across scales |
| **Temporal Discounting** | Fast-path speed optimization (per-turn: <100ms) could disable multi-agent safety detection, with costs only visible at sprint scale |
| **Paradigm Shift** | Model updates assume incremental change; cannot detect category errors or fundamental assumption violations |
| **Change Blindness** | Multi-agent loop is called "least mature" but ranked as peer to mature loops; hidden assumption that it will stabilize as quickly |
| **Availability Heuristic** | Vivid signals (failures, deadlines) over-weighted; absence of signal (thing stopped happening) under-weighted in Orient |
| **Perspective Taking** | Human operator sees Loops 1/2/4 as low-risk naming, Loop 3 as new capability; brainstorm treats all as peers |

---

## Severity Assessment

| ID | Severity | Why |
|----|----------|-----|
| 1. Orient mental models | P1 | Entire abstraction layer underdefined; agents could build models on JSON, not reality |
| 2. Self-contained observation | P1 | All loops share same blind spots; no structural diversity in signal |
| 3. Signal/noise separation | P2 | Orient is data-dumb; relies on reflection to correct mistakes, not prevention |
| 4. Timescale coupling | P2 | Real cascades blow up the abstraction; design assumes independence that won't hold |
| 5. Loop 3 immaturity | P2 | Framed as parallel peer; actually a new capability with deferred design |
| 6. Model paradigm shifts | P3 | Incremental updates can't fix category errors; should be detectable |
| 7. Fast-path confidence | P3 | Coupling confidence to routing creates Goodhart pressure; solvable but overlooked |
| 8. Approach trade-off | P3 | Comparison hides that choice depends on forecast (num loops); forecast missing |

---

## Missing Analysis for Successful Implementation

Before moving forward, the brainstorm should address:

1. **Orient as a primitive:** Define the mental model update mechanism. Example: "Reflect writes delta_from_expectation; Orient reads evidence since last session to adjust priors."

2. **Observation diversity:** Specify external signal sources that disagree with internal state. Include failure modes: "If event bus is unavailable, all loops revert to last-known snapshot plus manual escalation."

3. **Signal classification:** Define per-loop signal classes (error, state_change, completion, timeout, anomaly) and thresholds for triggering Orient updates.

4. **Escalation contracts:** Explicit rules: "Per-turn loop observes signal_score ≥ 4 → escalate to sprint loop. Sprint loop observes phase_stuck for >60s → escalate to multi-agent loop."

5. **Loop count forecast:** How many OODAR loops will Demarch have by end of year? Forecast drives Approach selection.

6. **Change detection:** In Reflect, how do agents detect that a model category (not just parameters) has shifted?

7. **Multi-agent spike:** Design CoordinationModel with minimal implementation. Test with 2 agents, 1 conflict, before declaring Loop 3 a full peer.

---

## Recommendations for Next Step

**Recommended direction:** Hybrid of Approach A + Approach B.

- **Phase 1:** Implement Approach A's Shared Observation Layer and signal classification (low risk, immediate value).
- **Phase 2:** Spike a minimal `OODARLoop` interface in intercore with SprintLoop as first implementation (tests the abstraction with a mature loop).
- **Phase 3:** If spike succeeds, roll out TurnLoop and LearningLoop against the interface. If spike reveals interface is wrong, it's cheaper to fix early.
- **Phase 4:** Loop 3 (CoordinationLoop) gets designed separately after loops 1/2/4 prove the interface stable.

This sequence preserves low risk (Approach A's strength), maintains optionality (interface is testable before committing), and defers the highest-risk component (Loop 3) until others are proven.

---

## Summary for Project Memory

This brainstorm is **philosophically sound** (extends PHILOSOPHY.md's flywheel) but **operationally under-specified** on the actual mechanisms. The gap isn't between Approach A and B—it's between naming patterns and implementing primitives. The document correctly identifies what's missing (explicit Reflect, Orient schema) but conflates "describing existing patterns with OODAR vocabulary" with "building formal abstractions." They're different paths; choosing requires acknowledging costs, not pretending equivalence.

**Critical unknown:** How many OODAR loops will Demarch need in the end state? Answer drives Approach choice.
