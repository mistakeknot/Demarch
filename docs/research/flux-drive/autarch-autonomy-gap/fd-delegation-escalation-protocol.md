# fd-delegation-escalation-protocol Review

**Document:** `docs/research/autarch-autonomy-gap-analysis.md`
**Reviewer:** fd-delegation-escalation-protocol (protocol designer, distributed systems escalation)
**Date:** 2026-02-25

---

## Summary

The gap analysis correctly identifies that Autarch lacks a delegation and escalation protocol (Gap 7) and that this absence is structural, not cosmetic. However, the document's own treatment of escalation remains aspirational -- it describes what the protocol should contain (typed messages, priority classification, context/options/recommendation) without specifying the state machine, timeout behavior, integration with Intercore's gate model, or recovery paths for non-response. The result is that the document diagnoses an absence and then partially reproduces it.

Six findings follow, ordered by severity. Each traces a concrete failure scenario through the proposed architecture to identify where the protocol breaks down.

---

## [P0] Escalation triggers are described by category but not by condition

**Location:** Gap 7 (lines 107-117), Architectural Requirements item 1 (line 205)

**The problem:** The document lists four escalation types (decision requests, exception reports, approval gates, priority/urgency classification) but never specifies the conditions that produce them. What observable state in a ring causes an escalation signal to be emitted? The document says "3 retries failed, budget exceeded, contradictory requirements" (line 75) as examples of exceptions, but these are prose illustrations, not protocol-level trigger definitions.

**Failure scenario -- stalled inner ring:**

1. The Execution Ring (Coldwine) dispatches an agent via `ic dispatch spawn`.
2. The agent runs for 45 minutes, consuming tokens, but produces no artifact.
3. The dispatch status is "running" -- not failed, not timed out, not budget-exceeded.
4. No gate is blocking because the run has not attempted to advance.
5. No escalation fires because no defined trigger condition has been met.
6. The ring is stuck. The outer ring (Strategic/Bigend) sees "running" status indefinitely.
7. The human is never notified because nothing entered the attention queue.

**What is missing:** A trigger taxonomy that maps observable kernel states to escalation signals. For each trigger, the protocol needs:

- **Condition** (what is observed -- e.g., dispatch running > N minutes with no artifact, token consumption > M% of budget with no phase advancement)
- **Signal type** (which of the four escalation categories it maps to)
- **Signal destination** (which ring or entity receives it)
- **Timeout** (how long the condition must persist before the signal fires)

Without this, the "exception-based attention" model (Gap 3) has no mechanism to detect exceptions. The system degrades to polling, which is the operator model the document argues against.

**Recommendation:** Define a `TriggerRule` schema analogous to Intercore's `gateRule` (see `core/intercore/internal/phase/gate.go`, lines 86-91). Each trigger rule specifies a check type, a threshold, a signal type, and a destination. Trigger rules are evaluated by a watcher process (or by the ring itself on a timer) against kernel state. This makes triggers declarative, auditable, and configurable via Interspect overlays -- the same pattern the gate system already uses.

---

## [P0] No state machine for escalation lifecycle

**Location:** Gap 7 (lines 107-117), Recommended Next Steps item 2 (line 242)

**The problem:** The document describes escalation as a message (decision request with context/options/recommendation) but not as a stateful process. An escalation is not a single message -- it is a lifecycle: created, acknowledged, resolved (or timed out, or superseded). Without a state machine, there is no way to detect lost escalations, measure escalation latency, or reason about what happens when the human (or outer ring) does not respond.

**Failure scenario -- lost escalation:**

1. The Design Ring (Gurgeh) encounters contradictory requirements during PRD generation.
2. It emits a "decision request" escalation to the human.
3. The human is away. The escalation sits in the attention queue.
4. Meanwhile, Gurgeh's autonomous sprint continues on a different section.
5. Gurgeh reaches a gate that depends on the unresolved decision.
6. The gate blocks. Gurgeh cannot advance.
7. No escalation is emitted for the gate block because the original escalation (which would resolve the blocker) is already "pending."
8. The system is deadlocked: the gate waits for the decision, but nothing re-escalates because the first escalation was never acknowledged.

**What is missing:** Escalation states and transitions:

```
Created --> Acknowledged --> Resolved
    |            |              |
    +--> Timed Out         Superseded
    |
    +--> Re-escalated (N times, then terminal)
```

Each state must be durable (persisted in Intercore's event bus or a dedicated table). The "Timed Out" transition needs a configurable duration. "Re-escalated" needs a retry count with a terminal condition (after N re-escalations, the escalation becomes a hard block that cannot be auto-remediated).

**Where state lives:** The document never specifies where escalation state is stored. Given Intercore's design principles ("if it matters, it's in the database"), escalation records belong in the kernel's SQLite database alongside runs, dispatches, and events. This is not a UX concern (fd-autonomy-ux-hierarchy) -- it is a durability concern. If a session crashes between escalation creation and resolution, the escalation must survive and be resumable.

**Recommendation:** Add an `escalations` table to Intercore's schema with columns for `run_id`, `ring`, `type`, `status`, `created_at`, `acknowledged_at`, `resolved_at`, `timeout_at`, and `resolution`. Expose via `ic escalation create/ack/resolve/list`. The gate evaluator (`core/intercore/internal/phase/gate.go`) already supports custom check types via `gateRule.check` -- add a `CheckEscalationResolved` check type that blocks advancement until a named escalation is resolved.

---

## [P1] Delegation model is inconsistently push and pull

**Location:** Gap 2 (lines 29-67), The Recursive Ring Model (lines 212-237)

**The problem:** The document uses two contradictory delegation models without distinguishing them:

1. **Push model (top-down):** "The Strategic Ring delegates down to Design/Execute/Research rings" (line 52, the diagram). The outer ring decomposes work and pushes tasks to inner rings.
2. **Pull model (bottom-up):** "Each ring is an autonomous sub-agency that escalates to the ring above only on exception" (line 33). Inner rings run autonomously and pull the outer ring's attention only when needed.

These are different protocols with different failure modes. In a push model, the outer ring must track what it delegated and detect non-completion. In a pull model, the outer ring trusts inner rings to self-report failures and must handle the case where a ring fails silently.

**Failure scenario -- silent inner ring failure under pull model:**

1. The Strategic Ring (Bigend) assumes the Execution Ring (Coldwine) is running autonomously.
2. Coldwine's agent crashes mid-dispatch. The dispatch status in Intercore is "running" (no crash detection).
3. Under pull model, Coldwine is responsible for escalating. But Coldwine's process is dead.
4. Under push model, Bigend would poll Coldwine's status and detect the stall. But the document describes Bigend as a passive observer that receives escalations, not a poller.
5. The crash is invisible until the human manually checks.

**What is missing:** An explicit choice between push and pull, with the failure modes of the chosen model addressed. The most robust approach is pull-with-heartbeat: inner rings run autonomously (pull model) but emit periodic liveness signals. The outer ring (or a dedicated monitor) watches for missing heartbeats and escalates on silence. This maps directly to Intercore's existing `ic dispatch poll` mechanism (see CLAUDE.md dispatch reference), which already implements liveness checking for dispatches.

**Recommendation:** Commit to pull-with-heartbeat. Define a heartbeat interval per ring (e.g., every 60 seconds, the ring emits an `ic events` liveness event). The outer ring (or a dedicated watcher) treats N missed heartbeats as a trigger for escalation. This avoids the overhead of push-model tracking while addressing the silent-failure gap.

---

## [P1] Timeout and non-response handling is entirely absent

**Location:** Gap 3 (lines 69-78), Gap 7 (lines 107-117), Architectural Requirements (lines 203-211)

**The problem:** The document describes an attention queue where items appear for the human to act on. It never specifies what happens if the human does not act. This is the most critical gap in the escalation protocol because the entire architecture depends on exception-based human attention -- and exceptions are, by definition, the cases where prompt response matters most.

**Failure scenario -- human non-response to P0 escalation:**

1. The Execution Ring detects a P0 safety finding during review.
2. A decision request escalation is created: "override, investigate, reassign, or abort" (line 147).
3. The human does not respond for 6 hours (asleep, busy, weekend).
4. The run is blocked. Agents are idle. Tokens are not being spent, but wall-clock time is accumulating.
5. Other runs that depend on this run (portfolio orchestration) are also blocked via `CheckChildrenAtPhase` gates (`core/intercore/internal/phase/gate.go`, line 157).
6. The cascade stalls the entire portfolio.

**What is missing:** A timeout policy for each escalation type with a defined fallback action:

| Escalation Type | Default Timeout | Fallback Action |
|----------------|----------------|-----------------|
| Decision request (reversible) | 4 hours | Accept agency recommendation |
| Decision request (irreversible) | No timeout | Re-escalate with increased urgency |
| Exception report (budget) | 1 hour | Pause run (preserve state) |
| Exception report (safety P0) | No timeout | Block indefinitely (safety invariant) |
| Approval gate | Configurable | Per-gate policy (some auto-approve on timeout) |

The document's "Recommended Next Steps" (line 242) calls for defining the escalation protocol but does not include timeout handling in the scope. This must be first-class: an escalation protocol without timeout handling is like a gate system without the block/advance decision.

**Recommendation:** Add timeout and fallback as required fields in the escalation schema. For reversible decisions, the agency's recommended default (already mentioned on line 148: "Agency recommends: reimplement") becomes the timeout fallback. For safety-critical decisions, the timeout fallback is "block indefinitely and re-escalate." Make these policies configurable per project and per autonomy level, stored as Intercore configuration.

---

## [P1] Escalation does not integrate with Intercore's gate model

**Location:** Gap 6 (lines 99-105), Gap 7 (lines 107-117), Architectural Requirements items 3 and 5 (lines 207-209)

**The problem:** The document describes escalations and gates as separate concepts. But in Intercore's architecture, gates are the mechanism that blocks phase advancement (`core/intercore/internal/phase/machine.go`, lines 180-211). If an escalation does not map to a gate, it is advisory -- the run can advance past it. If it does map to a gate, it blocks advancement until resolved. The document never specifies which behavior applies.

**Failure scenario -- advisory escalation ignored during advancement:**

1. The Design Ring (Gurgeh) escalates a "contradictory requirements" decision to the human.
2. The escalation is advisory (no gate integration).
3. Gurgeh's autonomous sprint continues with its best guess.
4. The sprint reaches the `planned -> executing` gate. The gate checks `CheckArtifactExists` for the plan phase. A plan artifact exists (Gurgeh generated one despite the contradiction).
5. The gate passes. Execution begins based on a plan with unresolved contradictions.
6. The human eventually responds to the escalation, but execution is already underway with the wrong assumptions.

**What Intercore already supports:** The gate system has a three-level precedence for gate rules: per-run stored rules > agency spec rules > hardcoded defaults (`core/intercore/internal/phase/gate.go`, lines 140-155). An escalation could inject a per-run gate rule that blocks advancement until the escalation is resolved. This is the `CheckEscalationResolved` check type proposed in the P0 finding above.

**The choice the document must make:** Are escalations blocking or advisory? The answer should be: it depends on the escalation type. Decision requests for reversible choices are advisory (the agency proceeds with its recommendation and reverses if the human disagrees). Decision requests for irreversible choices and safety exceptions are blocking (they inject a hard gate that prevents advancement). The document's Gap 7 lists escalation types but does not classify them along this axis.

**Recommendation:** Extend the escalation type taxonomy with a `blocking: bool` field. When `blocking: true`, escalation creation also creates a per-run gate rule via `ic run` that adds a `CheckEscalationResolved` condition for the next phase transition. When the escalation is resolved, the gate rule is removed. This reuses Intercore's existing gate infrastructure rather than building a parallel blocking mechanism.

---

## [P2] Circular escalation is not addressed

**Location:** The Recursive Ring Model (lines 212-237), Gap 2 (lines 29-67)

**The problem:** The document proposes a recursive ring model where each ring can escalate to the ring above. But it does not address what happens when escalation creates a cycle. In a recursive structure, cycles are possible whenever an outer ring delegates remediation to a different inner ring.

**Failure scenario -- escalation cycle:**

1. The Execution Ring (Coldwine) fails to build a feature. It escalates to the Strategic Ring (Bigend): "build failed, need redesign."
2. The Strategic Ring delegates the redesign to the Design Ring (Gurgeh): "revise the spec for this feature."
3. Gurgeh discovers the spec requires research it cannot do. It escalates to the Strategic Ring: "need research before I can redesign."
4. The Strategic Ring delegates research to the Research Ring (Pollard): "investigate feasibility."
5. Pollard's research concludes: "this approach is infeasible as designed. Recommend rearchitecting."
6. Pollard escalates back to the Strategic Ring. The Strategic Ring delegates back to Gurgeh. Gurgeh needs more research. The cycle continues.

**What is missing:** Cycle detection. Each escalation should carry a trace (a list of ring IDs and escalation IDs that preceded it). If the trace contains a ring that already appears in the chain, the escalation is flagged as a cycle and escalated to the human instead of to another ring. This is the distributed systems equivalent of loop detection in routing protocols.

**Recommendation:** Add an `escalation_chain` field (ordered list of `[ring, escalation_id]` tuples) to the escalation message. Before delegating to an inner ring, the outer ring checks whether that ring already appears in the chain. If so, the escalation is promoted to the human with a summary: "Cycle detected: Execution -> Design -> Research -> Design. Human judgment required to break the cycle."

---

## [P2] Partial vs full delegation is not specified

**Location:** Gap 2 (lines 29-67), The Recursive Ring Model (lines 212-237)

**The problem:** The document describes delegation as a binary act: the outer ring delegates to an inner ring, and the inner ring runs autonomously. But real delegation has granularity:

- **Full delegation:** The inner ring owns the entire outcome. The outer ring monitors but does not retain responsibility.
- **Partial delegation:** The outer ring delegates execution but retains responsibility for specific sub-decisions (e.g., "execute this plan, but check with me before adding new dependencies").
- **Supervised delegation:** The outer ring delegates but requires periodic check-ins (not just exception-based escalation).

The Executive Mode dashboard (lines 133-166) implicitly assumes full delegation (the human sees outcomes, not operations). But the Supervisor mode (line 126-127) implies partial delegation (the human "monitors progress, intervenes on exceptions" at ~10% interaction rate). The document does not specify how a ring knows which delegation mode it is operating under, or how delegation mode affects the escalation protocol.

**Failure scenario -- delegation mode mismatch:**

1. The human sets a sprint to Supervisor mode (expecting ~10% interaction).
2. The Execution Ring treats this as full delegation (runs autonomously, escalates only on failure).
3. The ring makes 15 design decisions that the human would have wanted to review (e.g., choosing between two API designs, selecting a dependency, deciding on error handling strategy).
4. The sprint completes. The human reviews the outcome and finds the decisions unacceptable.
5. Rework cost is high because 15 downstream decisions built on the unreviewed choices.

**What is missing:** A delegation contract that specifies, per-delegation, which decision categories the inner ring owns and which require escalation. This maps to the Interspect signal taxonomy's concept of "configurable mandatory gates" (Architectural Requirements item 3, line 207) -- but applied to delegation scope, not just phase advancement.

**Recommendation:** Define a `DelegationContract` that accompanies each delegation act. The contract lists decision categories (e.g., "dependency selection", "API design", "error handling") and for each specifies: `autonomous` (ring decides), `escalate` (ring escalates before deciding), or `report` (ring decides and reports after). The contract is stored per-run in Intercore and evaluated by the ring before making decisions in each category. This makes delegation granularity explicit and auditable.

---

## Observations (not findings)

These are observations that fall outside my review scope but are worth noting because they affect escalation protocol design:

1. **Intercore's gate system is blocking, not advisory.** The `Advance` function in `core/intercore/internal/phase/machine.go` (line 180) returns without advancing when a hard gate fails. This means any escalation that integrates with gates inherits blocking semantics automatically. The document should build on this rather than designing a parallel mechanism.

2. **Intercore already has the building blocks for escalation state.** The event bus (`ic events tail`), consumer cursors (`ic events cursor`), and the phase event audit trail provide durable, queryable state. An escalation table would be a natural extension, not a new subsystem.

3. **The Interspect signal taxonomy (in `docs/interspect-vision.md`, lines 39-82) is the right framework for classifying escalation signals.** Human signals (review dismissals, gate overrides, manual corrections) are already tracked. Escalation responses are a new human signal type that fits the existing taxonomy. The document references this connection (line 117) but does not make it concrete.

4. **The `auto_advance` flag on runs (checked in `machine.go`, line 108) is already a primitive form of delegation control.** When `auto_advance` is false, the run pauses at every phase transition, requiring explicit advancement -- this is Operator mode. When true, it advances automatically through passing gates -- this is closer to Executive mode. The delegation contract proposed above would extend this from a binary flag to a per-category policy.
