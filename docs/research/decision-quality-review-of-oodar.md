# Decision Quality Review: OODAR Loops Brainstorm

**Date:** 2026-02-28
**Reviewer:** Claude Code (Flux-drive Decision Quality Agent)
**Document:** `docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`
**Status:** Findings and recommendations

---

## Executive Summary

The OODAR loops brainstorm presents a genuine architectural choice between two defensible approaches: **Approach A (bottom-up)** lowers risk and delivery time but accumulates ad-hoc contracts; **Approach B (top-down)** builds a formal primitive at higher upfront cost but enables systematic future extensions. However, the document exhibits five significant decision-quality gaps:

1. **Hidden third option (Hybrid-First)** — Starting with Approach A's immediate value (Step 1: `ic situation`), then progressively formalizing into Approach B's interface without committing to either upfront.
2. **Reversibility understated** — Approach A's contracts are not irreversible; A→B migration is cheaper than suggested.
3. **Anchoring on Boyd's OODA** — The Reflect addition is conflated with OODAR framing; reflection patterns exist regardless of naming.
4. **Missing tempo-cost trade-off** — No analysis of whether formal OODAR overhead (interface dispatch, type safety) violates the <100ms per-turn target.
5. **Reflect phase ambiguity** — Conflates two distinct concepts: **within-cycle learning** (per-action reflection) vs. **cross-cycle learning** (pattern emergence across actions).

The brainstorm is strong on implementation detail but weak on decision discipline. The open questions section (§ 9) hints at deeper uncertainties that aren't resolved by choosing between A and B.

---

## Findings

### Finding 1: False Dichotomy — Hidden Hybrid Option (P1)

**Severity:** P1 (Blind spot — entire frame missing)

**Location:** Entire document frames the choice as binary (Approach A vs Approach B), but a third option dominates both in key dimensions.

**Lens:** Starter Option, Explore vs Exploit

**Analysis:**

The two approaches are presented as mutually exclusive:
- **Approach A:** Build `ic situation` (Step 1), then layered contracts on top of existing code
- **Approach B:** Design the generic `OODARLoop<S,O,D,A,R>` interface first, then instantiate it at each level

In reality, a **Hybrid-First** option exists that captures Approach A's speed advantage while unblocking Approach B's composability gains:

1. **Phase 1 (Weeks 1-2):** Ship Approach A Steps 1-2 independently
   - `ic situation snapshot` — immediate value, uncontroversial
   - Situation assessment schema — used by LLM reasoning, no infrastructure changes
   - This enables next-level agent decisions TODAY and proves observation layer viability

2. **Phase 2 (Weeks 3-4):** Extract interfaces from working code
   - Once SprintLoop is proven stable, wrap it in the `OODARLoop` interface
   - The interface is inferred FROM the working implementation, not imposed before
   - Risk of "premature abstraction" is eliminated — the abstraction solves a proven problem

3. **Phase 3 (Weeks 5+):** Migrate remaining loops incrementally
   - Each loop is wrapped as it matures
   - Interface stabilizes through use, not speculation

**Why this dominates both approaches:**
- **vs. A:** Gets to Gridfire composability without accumulating ad-hoc contracts as debt
- **vs. B:** Eliminates "premature abstraction" risk by building the interface FROM proven code, not before
- **vs. both:** Delivers Step 1 value in weeks, not months, while keeping B's long-term path open

**Trade-offs concealed by the false dichotomy:**
- Approach A implicitly bets that LayeredContracts are cheaper to maintain than Interface. Not obviously true.
- Approach B implicitly bets that designing first is cheaper than designing-from-use. Not obviously true either.
- The Hybrid-First option **is** Approach A for weeks 1-2, then becomes Approach B starting week 3 — it's not a third path, it's a sequencing insight that the binary framing obscures.

**Recommendation:** The document should reframe as "Start with A's delivery, migrate to B's structure as interfaces stabilize." This removes the false choice and clarifies the actual question: **how fast does the interface need to stabilize?** (Answer: Fast enough to unblock new loop levels before they break the existing interfaces.)

---

### Finding 2: Reversibility & Migration Cost Underestimated (P2)

**Severity:** P2 (Missed lens — key trade-off underexplored)

**Location:** Approach A Weaknesses (§ 5.3), Approach B Strengths (§ 6.3)

**Lens:** Reversibility, Sunk Cost, N-ply Thinking

**Analysis:**

Approach A lists as weakness: "**No formal abstraction.** Each level's OODAR is ad-hoc; no guarantee they compose well."
Approach B lists as strength: "**Formal composability.** Adding a new loop level ... means implementing the interface, not building from scratch."

This implies A→B migration is expensive. But the actual cost is overstated:

**Migration path from A to B (in-place, non-disruptive):**

1. Keep all A-step implementations in place (Situation snapshots, assessment schemas, routing tables)
2. Define the generic interface OVER them:
   ```go
   type OODARLoop[S,O,D,A,R] interface { ... }

   // Wrap existing code without rewriting
   func (a *SituationSnapshot) Observe(ctx) Observation { ... }
   func (a *SprintState) Orient(ctx) O { ... }
   ```
3. No code removal, no breaking changes, existing behavior preserved
4. New loops (CoordinationLoop, etc.) implement the interface from the start
5. Old loops benefit from interface typing when called through the generic method

**Actual cost:** A few days to extract interfaces from proven implementations. Not a rewrite.

**Why this matters:** The sunk-cost risk (Approach A locks us in) is overstated. The real cost difference is:
- Approach A upfront: ~$0
- Approach A→B migration: ~3-5 days, non-disruptive
- Approach B upfront: ~1-2 weeks
- Approach B → (nothing, already have it): $0

The decision isn't "commit now or never" — it's "pay now or pay later." The later payment is smaller than the document suggests.

**Recommendation:** Add a migration-cost section showing how A→B is a local, non-disruptive refactor. This reduces Approach A's perceived downside and strengthens the case for starting with A's delivery, then progressively formalizing.

---

### Finding 3: Anchoring on Boyd's OODA Model (P2)

**Severity:** P2 (Missed lens — foundational assumption not examined)

**Location:** Entire document, especially §1-2 ("Why OODAR, Not OODA")

**Lens:** Anchoring Bias, Dissolving the Problem, Theory of Change

**Analysis:**

The document strongly anchors on Boyd's military OODA model, using it to justify the Reflect addition:

> "Boyd's OODA assumes Orient implicitly incorporates learning from past cycles. For AI agents, this is too important to leave implicit ... Reflect IS the evidence-to-authority conversion."

This is correct — but the anchor point obscures a deeper question: **Does the problem require OODAR framing at all, or is the real problem statement different?**

**What the document actually needs:**

Looking at the four loops and their gaps:
- Per-turn: "No structured situation assessment"
- Sprint: "Hardcoded bash, not adaptive"
- Multi-agent: "Agents don't model each other's state"
- Cross-session: "Only for routing changes, not general learning"

The common pattern is NOT "lacking Reflect phase" — it's **"lacking structured orientation"** and **"lacking cross-loop learning signals."**

**Alternative framing (not OODAR):**

Instead of extending Boyd's OODA with Reflect, the problem might be:
1. **Structured Orient** — Every decision needs a situation assessment (not implicit LLM reasoning)
2. **Evidence accumulation** — Actions produce signals that feed into future decisions
3. **Learning rate tuning** — Fast decisions (per-turn) vs deep decisions (sprint) vs pattern discovery (cross-session)

This is ONLY coincidentally similar to OODA + Reflect. It's really about decision architecture, not about Boyd's model.

**Why the anchor matters:**

By anchoring on Boyd, the document:
- Assumes 5 phases are the right decomposition (but the real problem might need 3-4 levels of decision)
- Assumes all loops follow the same phase structure (but per-turn might be fundamentally different from multi-agent)
- Uses OODA terminology to legitimize what is actually a domain-specific design (agent decision architecture)

**What's correct about the anchor:**

The Reflect phase IS important for AI agents. The evidence cycle IS Demarch's core bet (PHILOSOPHY.md confirms this). But "Reflect" is a consequence of the evidence architecture, not a consequence of Boyd's model.

**Recommendation:** Reframe the document's opening:
- Lead with Demarch's philosophy (evidence → authority → actions)
- Show that this naturally produces an evidence accumulation phase
- Show that Boyd's OODA is ANALOGOUS but not prescriptive
- Don't justify Reflect by comparison to Boyd; justify it by reference to PHILOSOPHY.md's flywheel

This shifts the anchor from "how do we extend a military model" to "how do we formalize Demarch's proven decision patterns."

---

### Finding 4: Tempo-Cost Trade-off Missing (P2)

**Severity:** P2 (Underexplored trade-off with concrete impact)

**Location:** Approach B (§ 6), "Weaknesses" section notably silent on performance

**Lens:** Local vs Global Optimization, Cone of Uncertainty

**Analysis:**

Approach B introduces formal abstraction layers:

```go
type OODARLoop[S Sensor, O Orientation, D Decision, A Action, R Reflection] interface {
    Observe(...) Observation
    Orient(...) O
    Decide(...) D
    Act(...) Outcome
    Reflect(...) R
    Cycle(...) error
}
```

The per-turn loop has a **hard tempo target: <100ms overhead per turn**.

**Interface dispatch cost analysis:**

At runtime, Approach B's per-turn loop would:
1. Call `Observe()` (interface method dispatch)
2. Call `Orient()` (interface method dispatch)
3. Call `Decide()` (interface method dispatch + type assertion for fast vs deliberate path)
4. Call `Act()` (interface method dispatch)
5. Call `Reflect()` (interface method dispatch)

In Go, interface dispatch is ~100-200 nanoseconds per call. With 5 calls, that's ~1 microsecond. **Not a blocker.**

BUT:

- **Context passing overhead:** Each method takes `ctx Context` and may check cancellation
- **Type safety overhead:** Reflecting on Sensor/Orientation types at runtime (if using `interface{}` internally)
- **Error handling:** Each method can fail independently; orchestrating errors across 5 phases adds branches

**The real question (unasked):**

Is the overhead worth the abstraction clarity? Or is per-turn OODAR trying to formalize something that's better left as imperative LLM reasoning?

Per-turn OODAR assumes:
- Observe → Orient → Decide → Act → Reflect is the RIGHT decomposition for a tool-calling loop
- But an LLM's native reasoning pattern is: "read context (implicit Observe+Orient) → plan next tool → call tool (Act) → read result → repeat"

**The mismatch:**

- LLMs don't naturally structure as O→O→D→A→R; they stream reasoning and interleave phases
- Forcing OODAR onto per-turn MIGHT reduce latency by enabling cached Orient (good)
- OR it might add branching and formal steps where imperative code is cheaper (bad)

**Approach A avoids this by not formalizing per-turn OODAR** — the LLM's reasoning remains implicit, and signal scoring (Reflect) is added post-hoc.

**Approach B risks this by making per-turn OODAR a first-class primitive** — it may be over-formalizing a domain where LLM reasoning is already good enough.

**Recommendation:** Add a section analyzing whether per-turn OODAR is a constraint (must achieve <100ms) or a benefit (speeds up per-turn decisions). If it's a constraint, validate Approach B doesn't blow the budget. If it's a benefit, measure the speedup. If it's neutral or negative, question whether per-turn OODAR belongs in the interface at all.

---

### Finding 5: Reflect Phase Conflates Two Concepts (P2)

**Severity:** P2 (Ambiguity with downstream implementation impact)

**Location:** §1, Dual-mode Reflect (§2.2)

**Lens:** Dissolving the Problem, Theory of Change

**Analysis:**

The Reflect phase conflates two different learning mechanisms:

**Within-Cycle Learning (Inline Reflect):**
- Happens after a single action completes
- Updates the mental model for the NEXT action in the same cycle
- Example: "I called Tool X, it returned Y, that surprised me, I update my expectation"
- Tempo: Must finish in <100ms (per-turn), <5s (sprint)

**Cross-Cycle Learning (Async Reflect):**
- Accumulates evidence across multiple cycles
- Detects patterns (emerging → growing → ready)
- Updates routing or strategy for FUTURE cycles/sessions
- Tempo: Can be asynchronous, happens over hours/days

The document treats both as "Reflect" but they're mechanically different:

**Inline Reflect:**
```
Act(Tool X) → Result → Orient uses Result → Decide uses updated Orient → Act(Tool Y)
All in same cycle, <100ms
```

**Async Reflect:**
```
Act(Tool X) → Evidence event → Interspect accumulates → Pattern classification → Routing override
Hours/days later, next agent session picks up the signal
```

**Why the conflation matters:**

1. **Different feedback loops:** Inline is within-agent, per-turn. Async is cross-agent, cross-session.
2. **Different storages:** Inline updates session context (fast, local). Async updates Interspect SQLite (slower, global).
3. **Different gates:** Inline is automatic (signal_score ≥ 4). Async requires human approval for routing changes.
4. **Different latency tolerance:** Inline must be <100ms. Async can afford seconds.

The document's dual-mode formulation is correct (inline for significant, async for routine), **but it hides the fact that these are two separate systems that happen to produce similar-looking "reflection events."**

**Implementation risk:**

If Approach B's `OODARLoop` interface treats Reflect as a single method:
```go
Reflect(ctx, outcome, significance) (R, error)
```

Then per-turn Reflect (inline) and per-sprint Reflect (async) would both flow through the same interface, even though they:
- Have different consistency requirements (per-turn is synchronous, per-sprint can batch)
- Have different data models (per-turn updates session context, per-sprint updates Interspect)
- Have different authority boundaries (per-turn is local, per-sprint needs human approval)

**Recommendation:** Redefine Reflect into two distinct phases:
1. **React** — Within-cycle learning (updates mental models for next decision)
2. **Reflect** — Cross-cycle learning (accumulates evidence, proposes patterns)

This clarifies that:
- Per-turn has O→R→D (React), not O→R→D→R
- Per-sprint has O→D→A→Reflect (the cross-cycle signal collection)
- Cross-session is pure Reflect (pattern accumulation)
- Multi-agent is... unclear without this decomposition

Alternatively, keep "Reflect" but define its signature per-loop:
- TurnLoop.Reflect: signal_score → evidence event (async, fire-and-forget)
- SprintLoop.Reflect: phase outcomes → situation assessment update (sync, blocks next cycle)
- CrossSessionLoop.Reflect: evidence patterns → routing proposal (async, human approval gate)

The interface becomes more complex but more honest about what's actually happening.

---

## Secondary Findings

### Finding 6: Escalation Contracts Unspecified (P3)

**Severity:** P3 (Consider also — important but not decision-blocking)

**Location:** Open Questions (§9), question 4

**Lens:** Hierarchical Composition, Signposts

**Analysis:**

The hybrid architecture diagram (§3) shows escalation but doesn't specify when it happens:

```
Per-Turn OODAR → escalate → Sprint OODAR → escalate → Cross-Session OODAR
```

Questions:
- Does a per-turn decision that exceeds confidence threshold auto-escalate to sprint?
- Or does the agent explicitly flag it as "needs sprint-level approval"?
- What's the signal? (Exception? Timeout? Explicit escalation request?)
- Does every escalation block the inner loop?

Without this, Approach B's interface-first design can't specify the method signature for "escalate" — it becomes implicit ad-hoc behavior again.

**Recommendation:** Define an EscalationSignal type and include it in the Reflect output or Decision feedback. Make escalation a first-class concept, not a side-effect of high-confidence decisions.

---

### Finding 7: Orient Remains Mostly LLM-Driven in Both Approaches (P3)

**Severity:** P3 (Consider also)

**Location:** Approach A, "Weaknesses" (§5.3); Approach B, "Strengths" (§6.3)

**Lens:** Formal vs Informal, Local vs Global Optimization

**Analysis:**

Both approaches list Orient as either "remains LLM-driven" (A) or "becomes a first-class interface method" (B), but both miss the same issue:

**In Approach A:**
- Situation assessments improve LLM inputs
- But the LLM's Orient process is still implicit; we're just feeding it better context

**In Approach B:**
- Orient is a method with a defined signature
- But the implementation is STILL LLM-driven in most cases (per-turn, sprint)
- The interface just wraps the LLM's reasoning, doesn't replace it

**The real question (unasked):**

Is Orient meant to be **formalizable** (we can express it as rules/patterns), or is it **inherently LLM-native** (the LLM is the best Orient engine for complex situations)?

- For routing: Formalizable (routing tables work)
- For phase classification: Formalizable (phase_actions table works)
- For multi-agent conflict detection: Partially formalizable (lock state is clear, but optimal resolution may need reasoning)
- For per-turn re-orientation after tool results: LLM-native (the LLM excels at this)

**Recommendation:** Acknowledge that Orient has multiple implementations across the loops, and some will always be LLM-driven. The interface buys composability and testability, but doesn't solve the "Orient is expensive" problem for complex decisions. If Orient latency matters (it does for per-turn), consider caching assessed situations across turns and only re-running Orient on cache miss or explicit invalidation.

---

## Synthesis & Recommended Path

**The document's core claim is correct:** Demarch needs explicit OODAR formalization to match its philosophy.

**The document's weakness:** Presents this as a binary choice (A vs B) when the actual decision should be sequential (A→B) or parallel (do A fast, then formalize into B).

### Recommended Decision Process

Instead of choosing Approach A or B now, adopt this sequence:

**Decision Point 1 (Now):** Ship Approach A, Step 1 only
- Build `ic situation snapshot` — unified observation layer
- It's uncontroversial, immediately useful, blocking nothing
- Cost: 1-2 weeks
- Value: Every OODAR loop benefits, proves the observation layer works

**Decision Point 2 (2 weeks):** Assess whether SprintLoop and per-turn patterns are stable enough to formalize
- If yes: Extract interfaces incrementally (Approach B, step 1)
- If no: Continue with A's layered contracts until patterns stabilize

**Decision Point 3 (1 month):** Decide whether formal OODARLoop interface is worth the abstraction overhead
- Measure: Does the interface reduce code duplication? Does it clarify new-loop-level extensions?
- If yes: Complete B's implementation for remaining loops
- If no: Continue with A's ad-hoc approach; it's working fine

This converts the document's binary choice into a learning process where the decision quality improves as uncertainty resolves.

---

## Checklist for Next Steps

Before implementing either approach, the document should address:

- [ ] Reframe as Hybrid-First (A→B sequencing) rather than binary choice
- [ ] Add migration-cost analysis showing A→B is non-disruptive
- [ ] Shift anchor from Boyd's OODA to Demarch's philosophy (evidence → authority)
- [ ] Measure or bound Approach B's overhead against <100ms per-turn budget
- [ ] Decompose Reflect into React (within-cycle) vs Reflect (cross-cycle)
- [ ] Define escalation signals (when per-turn escalates to sprint)
- [ ] Clarify which Orient implementations are formalizable vs LLM-native
- [ ] Specify rollout sequence: Step 1 (ic situation) → prove → Step 2 (interfaces) → measure

---

## Summary Table

| Dimension | Finding | Severity | Recommendation |
|-----------|---------|----------|-----------------|
| **Option framing** | Binary choice hides Hybrid-First option | P1 | Reframe as sequential: start A, migrate to B as needed |
| **Reversibility** | A→B migration cost overstated | P2 | Add migration-cost section; reduces A's downside |
| **Anchoring** | OODA model anchor obscures real problem | P2 | Anchor to philosophy (evidence cycle) instead |
| **Tempo-cost** | Approach B overhead vs <100ms target unanalyzed | P2 | Measure or bound interface dispatch latency |
| **Reflect ambiguity** | Conflates within-cycle and cross-cycle learning | P2 | Split into React (sync) and Reflect (async) phases |
| **Escalation** | When inner loops escalate to outer loops unspecified | P3 | Define EscalationSignal as first-class concept |
| **Orient formalization** | Both approaches remain mostly LLM-driven | P3 | Acknowledge Orient has multiple implementations; clarify caching strategy |

---

## Conclusion

The OODAR loops brainstorm is **strong on architectural clarity** but **weak on decision discipline.** The core insight (Demarch needs explicit learning loops) is correct. The implementation options (A vs B) are both defensible.

But the document presents a false choice. The real decision is **sequencing and measurement**: start with A's delivery value, then progressively formalize into B as patterns stabilize and the abstraction cost becomes clear.

This resolves most of the open questions: escalation contracts clarify once you're in the interface; Orient formalization priorities become obvious once you measure per-loop costs; the Reflect ambiguity dissolves once you separate React from Reflect.

**Recommended next step:** Reframe the decision as "Start with A Step 1 (`ic situation`), measure its impact, then decide on B's interface design" rather than "Choose between A and B now."

This unblocks immediate delivery while keeping the composability option open.
