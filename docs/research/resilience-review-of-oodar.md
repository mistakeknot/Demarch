# Resilience Review: OODAR Loops for Agent Decision-Making

**Reviewer:** Flux-drive Adaptive Capacity Reviewer
**Date:** 2026-02-28
**Document reviewed:** `/home/mk/projects/Demarch/docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`
**Grounding:** PHILOSOPHY.md (evidence-driven, defense in depth, earned authority), AGENTS.md (progressive trust, escalation contracts)

---

## Executive Summary

The OODAR brainstorm names a critical loop structure that Demarch already executes informally. The design is philosophically sound but has **three critical resilience blindspots**: the shared observation layer is an undefended single point of failure, failure propagation paths between loops are unmapped, and Reflect's dual-mode structure doesn't guarantee that inline reflections actually improve decision quality before re-entering the cycle. These gaps are not architectural errors — they're design decisions that should be explicit rather than emergent.

**Severity:** P2 (Missed Lens) for all findings except #3, which is P1 (Blind Spot).

---

## Finding 1: Shared Observation Layer is a Single Point of Failure (P1)

**Location:** Brainstorm §Loop Communication, "Shared Observation Layer"; Approach A §Step 1, "ic situation snapshot"; Approach B §Step 2, "ObservationStore interface"

**The issue:** The design proposes a unified snapshot (`ic situation snapshot`) that **all four OODAR loops** depend on:

- Per-turn loops read it to understand current phase state
- Sprint loops read it to assess gate readiness
- Multi-agent loops read it to detect conflicts
- Cross-session loops read it for routing evidence

The document acknowledges no explicit failure mode for this layer. What happens when `ic situation snapshot` is slow, returns stale data, or fails entirely?

**Resilience lens: Single Point of Failure + Graceful Degradation**

Each loop should have a **fallback Orient** path:

1. **Primary (fast, in-process):** Loop caches its last Orient output. Confidence decays over time.
2. **Secondary (slow, calls ic situation):** If cache is stale (>10s), fetch fresh snapshot.
3. **Tertiary (degraded, no snapshot):** Use last known state + heuristics. All loops continue; decisions are lower-confidence.

Example degraded behavior:
- Per-turn loop: "ic situation snapshot timed out; using cached session context + signal_score instead of phase-aware routing"
- Sprint loop: "Snapshot unavailable; proceeding with bash-only phase state assessment, lower confidence gate pass"
- Multi-agent loop: "Snapshot unavailable; hold locks longer, escalate conflicts to human"

The brainstorm should specify:
- SLA for `ic situation snapshot` (< 50ms, aim for <10ms)
- Degradation paths if SLA is violated
- How loops detect snapshot staleness (version/timestamp)
- Timeout and fallback strategy per loop

**Recommendation:** Add a "Observation Layer Resilience" section defining:
1. Snapshot SLA and circuit breaker (fail-open, returning cached data with `stale: true` flag)
2. Per-loop fallback Orient contracts (what each loop does without a fresh snapshot)
3. Health checks: `ic situation health` to verify layer availability
4. Monitoring: emit metrics for snapshot latency and cache hit rate

---

## Finding 2: Failure Propagation Between Loops is Unmapped (P2)

**Location:** All four loop descriptions (§Loop 1-4); Approach A+B communication diagram

**The issue:** The hybrid architecture (shared observation layer + hierarchical decisions + de-escalation) is described as a communication protocol but has no explicit failure propagation model. What happens when:

1. **Per-turn loop reaches a bad state?** Does it automatically escalate to sprint loop? How does sprint know?
2. **Sprint loop fails to advance phase?** Does it loop-retry, escalate, or write a blocker to shared observation?
3. **Multi-agent loop detects a conflict it can't resolve?** Does it escalate to sprint loop or human?
4. **Cross-session loop proposes a routing change that breaks multiple per-turn loops?** How is this reverted?

The document defines escalation direction (per-turn → sprint → cross-session) but not **failure propagation contracts**:

- What is a "failure" at each level? (Timeout? Decision confidence < threshold? Outcome != expected?)
- How does a failure at level N get signaled to levels N+1 and N-1?
- Does a per-turn loop failure cascade to sprint, or can sprint ignore it?
- Are there circuit breakers? Can a failing loop go into "degraded mode" instead of bubbling errors?

**Resilience lens: Graceful Degradation + Antifragility**

The design claims the system "improves from disorder" (antifragility via Reflect phase), but doesn't specify how a loop learns that it failed. Without explicit failure signals, loops may loop-retry forever (livelock) or proceed silently with corrupted state.

**Recommendation:** Add a "Failure Propagation Model" section:

```
Failure Detection:
- Per-turn: signal_score < -2 (novel situation, unexpected outcome)
- Sprint: gate result != expected (decision model incorrect)
- Multi-agent: lock acquisition timeout > 10s (coordination failure)
- Cross-session: canary evaluation failure rate > 5% (routing model incorrect)

Escalation:
- Per-turn → sprint: escalate if confidence < 0.7 (decision routing failed)
- Sprint → cross-session: escalate if phase decision mismatched goals (strategy update needed)
- Multi-agent → sprint: escalate if conflicts unresolved > 3x (coordination model broken)
- De-escalation (outer → inner): write corrected situation assessment to shared observation layer

Circuit Breaker Behavior:
- Per-turn: limit retries to 2; switch to degraded mode (simpler heuristics, less ambitious actions)
- Sprint: retry phase decision 1x; escalate to human if repeated failure
- Multi-agent: timeout + escalate to sprint
- Cross-session: hold proposed routing changes in canary mode for 40 uses (not 20)
```

---

## Finding 3: Reflect Phase Does Not Guarantee Improved Decisions On Re-Entry (P1 — Blind Spot)

**Location:** Brainstorm §What We're Building "The Fifth Phase: Reflect"; Approach A §Step 4 "Reflect Contracts — Dual-Mode Formalization"; PHILOSOPHY.md §Receipts Close Loops, "Failure" subsection

**The critical issue:** The brainstorm proposes **inline Reflect** (signal_score ≥ 4): "Pause the loop. Debrief. Update mental models NOW. Compound learnings before next cycle."

But it provides no mechanism to verify that the Reflect phase actually produced a *correct* lesson. The loop could:

1. Pause after a surprising outcome
2. LLM produces a lesson ("this failure was due to X")
3. Loop resumes with updated mental model
4. Loop makes the same mistake again because the lesson was wrong

Example failure case:
- Per-turn loop sees a test fail unexpectedly
- Inline Reflect fires (signal_score = 4)
- LLM produces lesson: "Tests are brittle; skip this test next time"
- Loop resumes with updated model
- **Next cycle, loop actually skips the important test, wasting time before root cause is found**

The current Reflect implementation:
- Writes lessons to evidence store
- Updates session context
- Signal scoring is rule-based (works well)
- BUT: **No verification that the lesson is correct before it influences the next decision**

This violates PHILOSOPHY.md's core principle: "Evidence earns authority. Each level requires proof from the previous level." A lesson produced by Reflect is evidence; it should earn authority only after being tested.

**Resilience lens: Antifragility + Earned Authority + Creative Constraints**

True antifragility requires that failures improve future decisions, not just that they're recorded. The current design allows Reflect to generate bad lessons that degrade subsequent decisions. This is brittleness disguised as learning.

Additionally, the dual-mode (inline vs. async) creates a constraint: **inline Reflect must be fast enough to re-enter the loop immediately without latency regret.** This forces Reflect to be shallow (quick heuristics, no deep analysis). Shallow reflections are more likely to be wrong.

**Recommendation:** Reframe Reflect as a two-stage process:

```
Stage 1: Inline Reflection (signal_score ≥ 4) — Immediate, shallow
  - Pause loop
  - Structured reflection: { outcome, expectation, delta, tentative_lesson }
  - Emit to evidence store with confidence < 1.0 (not yet proven)
  - Resume loop with CAUTIOUS application of lesson

  Cautious application examples:
  - Routing table lookup: if lesson suggests new route, use it but monitor
  - Decision threshold: if lesson suggests higher/lower threshold, adjust by 10% not 100%
  - Decision: if lesson suggests skipping a step, add that step to "monitor" list instead of "skip"

Stage 2: Deep Reflection (async, high-signal-score evidence accumulated)
  - interspect analyzes evidence trends
  - Cross-session loop: "This routing change worked 18/20 times; promote to high confidence"
  - Or: "This decision lesson failed 4/10 times; revert, escalate to human"
  - Verified lessons earn authority; unverified lessons stay low-confidence
```

Additionally, add a **Reflect audit loop**:
- Every 10 decisions using a "tentative_lesson," check if outcomes improved
- If improvement < 5%, mark lesson as "unproven" and revert confidence
- If improvement > 15%, promote lesson to "verified" and increase confidence
- Report findings in cross-session loop so future reflections are calibrated

This ensures PHILOSOPHY.md's principle holds: evidence must earn authority through repeated demonstration, not on first iteration.

---

## Finding 4: Creative Constraints May Block Useful Shortcuts (P3 — Consider Also)

**Location:** Brainstorm §Loop Communication "hierarchical decisions + shared observations"; Approach A+B "escalation contracts"

**The issue:** The OODAR framework enforces a strict **observe → orient → decide → act → reflect** sequence at every level. This is powerful for reproducibility but may prevent agents from taking useful shortcuts that violate the sequence.

Examples of useful shortcuts that OODAR blocks:

1. **Omit Observe if the answer is obvious.** "I see the test is failing; I've seen this 100 times; just fix it immediately" — per-turn loop must observe first, then decide. Observable check might take 200ms; agent could have acted in 10ms.

2. **Decide before Orienting if the trust is high.** "I have 99% confidence this decision is right; skip expensive Orient, just Act immediately" — but OODAR forces Orient to run.

3. **Skip Reflect if low signal.** "This routine code fix is boring; don't Reflect; just continue" — inline Reflect is triggered by signal_score ≥ 4, but some agents may want to force-skip Reflect even for significant outcomes.

The brainstorm acknowledges this implicitly: "Tempo target: <100ms overhead per turn for fast-path decisions" (§Loop 1). But there's no explicit mechanism to **bypass or compress OODAR phases when confidence is high enough**.

**Resilience lens: Creative Constraints as Design Tools**

Constraints are valuable for safety (forcing deliberation) but should be **earned relaxations, not permanent chains**. Once an agent proves it can make decisions in a constrained frame reliably, it should earn permission to compress phases:

- High-confidence routing: skip Orient (cached from 1000 prior cycles)
- Trivial decisions: compress observe+orient into <10ms
- Verified-safe actions: act before reflect (reflect async instead of inline)

**Recommendation:** Add an "Earned Deviations from OODAR Sequence" section:

```
Condition: Agent trust_score > 0.95 for this decision type
Action: Compress OODAR phases
- Observe + Orient: combine into <10ms lookup (skip expensive data gathering)
- Decide: use routing table (skip LLM deliberation)
- Act: proceed immediately
- Reflect: defer to async (emit signal_score, don't pause)

Condition: Agent discovers a shortcut that saves >50% latency and maintains quality
Action: Proposal path
- Log shortcut attempt with detailed outcome
- If repeated success > 20x, propose to trust ladder: "This agent earned the right to skip Orient"
- Escalate to human for approval (earned authority, not assumed)
- If approved: add to agent's default policy; if rejected: document why for future reference

Safety net: If shortcut confidence degrades (success < 90%), revert to full OODAR
```

This preserves the benefits of OODAR (structure, reproducibility, safety) while allowing agents to prove they can operate faster when they've earned it.

---

## Finding 5: Cross-Session Loop Recovery Time is Unspecified (P2 — Missed Lens)

**Location:** Brainstorm §Loop 4: Cross-Session "Tempo target: Pattern classification within same session, override proposals within 24h"

**The issue:** The cross-session loop has the loosest tempo (24 hours for proposals), which is appropriate for slow-changing patterns. But the brainstorm doesn't specify **recovery time when the cross-session loop model is catastrophically wrong**.

Example failure scenario:
- For 3 days, the routing model sends complex tasks to Haiku (cheap, dumb)
- On day 4, someone notices post-merge quality dropped to 50%
- Cross-session loop detects the problem (canary evaluation)
- **How long until the system recovers?**

The current design:
- Canary window: 20 uses
- Proposal cycle: wait for ~100 uses to accumulate signal
- Human approval: sync at next session (could be hours)
- Actual fix deployment: next time agent is routed using the new model (could be delayed)

This is **fragile for slow-changing, high-impact problems**. A bad routing decision can remain in production for days before recovery.

**Resilience lens: Recovery Time + Antifragility**

The brainstorm's 24-hour tempo is slow-to-recover. But more importantly, there's no **circuit breaker** for catastrophic failures. If a routing override consistently fails, does the system:
- Auto-revert it after 5 failures?
- Escalate to human immediately (breaking the "async" model)?
- Only revert when canary confidence drops below threshold?

**Recommendation:** Add an "Anomaly Fast Path" to the cross-session loop:

```
Standard path: accumulate evidence → classify pattern → propose override (24h cycle)

Fast path (anomaly detection):
- If canary failure rate exceeds 20% in a single 20-use window (anomaly, not noise)
- Immediately escalate to human with evidence
- Optionally: auto-revert the routing override (return to previous model)
- Rationale: 20% failure rate is catastrophic; wait 24h is unacceptable

Consequence:
- Faster recovery for severe problems (hours instead of days)
- Preserves async model for normal cases (no human blocking)
- Escalation is automated; human approves the revert, not the diagnosis
```

Also, add canary monitoring with **progressive confidence decay**:
- After 20 uses: confidence = accuracy
- After 100 uses: confidence = accuracy * 0.8 (decay for staleness)
- After 500 uses: confidence = accuracy * 0.5 (older data less reliable as world changes)
- Reset confidence to 1.0 when new override proposal replaces this one

This ensures old decisions don't stay live forever; they eventually lose authority and get re-evaluated.

---

## Finding 6: Multi-Agent Loop Has No Explicit Deadlock Prevention (P2 — Missed Lens)

**Location:** Brainstorm §Loop 3: Multi-Agent "Orient: No explicit coordination model" and "Decide: Lock acquisition, claiming protocol — Reactive (wait for conflict), not proactive"

**The issue:** The multi-agent loop is described as **reactive**: agents acquire locks and resolve conflicts post-hoc. This works for occasional contention but has a latent deadlock vulnerability:

Scenario:
- Agent A holds lock X, waits for lock Y (Agent B holds it)
- Agent B holds lock Y, waits for lock X (Agent A holds it)
- Multi-agent loop detects conflict (after 1s+ timeout)
- **No explicit contract for how to break the deadlock**

The brainstorm doesn't specify:
- Deadlock detection SLA (how quickly is a deadlock discovered?)
- Deadlock recovery strategy (who backs off? Who holds priority?)
- Escalation path (does it go to sprint loop or human?)

**Resilience lens: Graceful Degradation + Antifragility**

Deadlock is a classic system failure. The OODAR design should explicitly handle it:

1. **Detection:** Lock wait timeout > 5s = probable deadlock
2. **Diagnosis:** Multi-agent loop queries both agents' lock state; confirms circular dependency
3. **Resolution:**
   - Option A (fast, local): lower-priority agent yields (backed off by signal score)
   - Option B (formal, slow): escalate to sprint loop; human breaks tie
   - Option C (recovery, experimental): both agents release locks, retry with randomized backoff (exponential jitter)

**Recommendation:** Add a "Deadlock Prevention and Recovery" section:

```
Proactive: Lock acquisition ordering
- All agents acquire locks in the same order (e.g., alphabetical by lock name)
- Prevents circular wait (violates one deadlock condition)
- Requires lock_acquisition_order to be documented and enforced

Reactive: Deadlock detection
- Lock acquisition timeout: if lock wait > 5s, suspect deadlock
- Diagnostics: query lock state of both agents
- If circular dependency confirmed: trigger deadlock recovery

Recovery:
1. Grace period: 1s for voluntary release (agents respect lock hints)
2. Forced release: lower-priority agent (signal_score < threshold) yields
3. Escalation: if no voluntary yield and both agents are high-priority, escalate to human

Monitoring:
- Count deadlock_attempts per session
- If deadlock_attempts > 3, escalate to sprint loop: "coordination model is broken"
```

---

## Finding 7: Tempo Measurement Lacks Tolerance for Outliers (P3 — Consider Also)

**Location:** All four loop descriptions; brainstorm §Open Questions "How do we measure OODAR tempo?"

**The issue:** The brainstorm proposes tempo targets:
- Per-turn: <100ms
- Sprint: <5s
- Multi-agent: <1s detection, <5s resolution
- Cross-session: <24h proposals

But real systems have outliers. Occasionally, `ic situation snapshot` will take 500ms (network hiccup). A phase advance might stall (gate re-evaluation blocked by human). Lock contention might resolve slowly on a busy server.

**Are these tempo targets:**
- **Medians** (50th percentile)?
- **P95 / P99** (tail latency)?
- **Maximums** (hard guarantees)?

The brainstorm doesn't specify. This matters for resilience: if the target is a maximum, a single outlier breaks the contract. If it's a median, most operations are faster, but users hit timeout pain points regularly.

**Resilience lens: Graceful Degradation Under Tail Load**

When tempo targets are exceeded, loops should:
1. Emit a "slow OODAR cycle" event
2. Raise confidence cost (decisions using stale Orient are less confident)
3. Escalate if repeated (3 consecutive slow cycles = escalate to human)

**Recommendation:** Specify tempo targets as percentiles with fallback behavior:

```
Per-turn OODAR tempo:
- Target: <100ms at P95 (95% of cycles complete in 100ms or less)
- Outlier handling: if cycle > 500ms, emit "slow_cycle" event
  - If 1 slow cycle: continue, no action
  - If 3 consecutive slow cycles: escalate to sprint loop (investigate)
- Grace period: first 5 cycles of a session are exempt (cold start)

Sprint OODAR tempo:
- Target: <5s at P95
- Outlier: if phase advance > 30s, escalate to human (gate may be blocked)

Multi-agent tempo:
- Conflict detection: target <1s at P95
- Conflict resolution: target <5s at P95
- If resolution > 30s: deadlock suspected, trigger recovery (see Finding 6)

Measurement:
- Emit histogram: latencies bucketed by phase, agent, loop level
- Run daily report: "P95 loop latencies" to detect degradation
- Alert if P95 > 2x baseline for any loop
```

This makes tempo expectations explicit and gives operators a way to diagnose slow loops.

---

## Finding 8: Approach A vs B Decision Left Hanging (P2 — Process Issue)

**Location:** Brainstorm §Next Steps "Run /flux-drive review on this document to synthesize the best of both approaches"

**The issue:** The brainstorm explores two approaches (Bottom-Up formalize-existing, Top-Down design-primitive-first) but defers the decision. This is intellectually honest but leaves the design in limbo. The team can't plan implementation without knowing which path will be taken.

**Resilience lens: Staged Rollout + Reversibility**

From a resilience standpoint, **Approach A (bottom-up) is lower-risk for the next 6 months**, because:
- It ships value immediately (`ic situation` alone improves all loops)
- It's reversible (contracts over existing code; removal doesn't break anything)
- It doesn't commit to premature abstraction (Approach B's `OODARLoop[S,O,D,A,R]` assumes composition)

Approach B is a better long-term architecture (testability, type safety, Gridfire alignment) but requires higher upfront investment and risks over-generalizing from 4 loops.

**Recommendation:** Choose Approach A for the next sprint, with a **planned transition to B at milestone N**:

```
Sprint N (now): Implement Approach A
- ic situation snapshot (§Step 1) — foundation
- Situation assessment schema (§Step 2) — per-turn, sprint, cross-session
- Decision contracts (§Step 3) — formalize routing tables
- Reflect contracts (§Step 4) — dual-mode formalization
- Docs (§Step 5) — vocabulary in PHILOSOPHY, skills
- Outcome: shared observation layer is live and proven; all agents see value

Sprint N+3 (planned): Evaluation and decision
- Measure if contracts are stable (how many revisions to routing tables? to decision thresholds?)
- Assess if Approach B's abstraction would help (are we copy-pasting loop logic?)
- Evaluate team bandwidth (can we afford 6-week intensive design work?)
- Decision gate: if contracts are stable, proceed to Approach B; otherwise, extend A

Sprint N+6: Implement Approach B (if decision gate passes)
- Define OODARLoop interface
- Wrap SprintLoop (most mature) first
- Wrap TurnLoop, LearningLoop second
- CoordinationLoop last (least mature)
- Outcome: formal composability, testability, Gridfire step forward
```

This approach combines the benefits: ship value now (A) without foreclosing better architecture later (B).

---

## Summary of Findings

| # | Lens | Severity | Title | Mitigation |
|---|------|----------|-------|-----------|
| 1 | Single Point of Failure | P1 | Shared observation layer lacks failover path | Add degradation paths per loop; circuit breaker for snapshot timeout |
| 2 | Graceful Degradation | P2 | Failure propagation between loops is unmapped | Define failure detection, escalation, and circuit-breaker per level |
| 3 | Antifragility / Earned Authority | **P1** | Reflect phase doesn't verify lessons before reuse | Verify lessons through 2-stage reflection (tentative → verified); audit loop |
| 4 | Creative Constraints | P3 | OODAR sequence may block useful shortcuts | Add earned-deviation mechanism for high-trust agents |
| 5 | Recovery Time | P2 | Cross-session loop recovery is slow for catastrophic failures | Add anomaly fast-path with auto-revert for >20% canary failure rate |
| 6 | Graceful Degradation | P2 | Multi-agent loop lacks deadlock prevention | Add lock ordering + deadlock detection + resolution strategies |
| 7 | Graceful Degradation | P3 | Tempo targets lack outlier handling | Specify as percentiles (P95); escalate on repeated slow cycles |
| 8 | Staged Rollout | P2 | Approach A vs B decision deferred | Recommend Approach A now; plan transition to B at N+6 |

---

## Connections to Demarch Philosophy

**Finding 3** (Reflect without verification) directly violates PHILOSOPHY.md's core principle: "Evidence earns authority. Each level requires proof from the previous level." The fix requires implementing a two-stage lesson-verification process.

**Finding 1** (shared observation SPOF) contradicts the defense-in-depth principle: "Every single layer can fail. All five failing simultaneously is the real risk." The observation layer must have degradation paths for each loop.

**Finding 2** (unmapped failure propagation) breaks the flywheel: "authority enables actions → actions produce evidence → evidence earns authority." Without explicit failure signals, loops can't escalate intelligently.

**Finding 6** (deadlock prevention) relates to "Governance → Polycentric: multiple independent evaluation authorities." If deadlock occurs, resolution must involve escalation to the next authority level (sprint loop or human).

All findings are resolvable through architectural amendments to the brainstorm; none require invalidating the core OODAR concept.

---

## Next Steps

1. **Review decision (this document):** Choose between Approach A (now) + Approach B (N+6), or a hybrid path.
2. **Planning phase:** Convert findings into acceptance criteria for the chosen approach.
3. **Implementation:** Build with explicit failure modes, tempo measurement, and escalation contracts.
4. **Validation:** Run stress tests simulating each failure mode (SPOF timeout, deadlock, bad Reflect lesson, tail latency). Verify degradation paths work.

