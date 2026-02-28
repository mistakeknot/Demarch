# User and Product Review: OODAR Loops for Agent Decision-Making

**Date:** 2026-02-28
**Reviewer role:** flux-drive (user + product perspective)
**Source document:** `docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`
**Status:** Review complete — ready for plan phase

---

## Primary User and Their Job

The primary user of OODAR is **the agent developer** — the person building, debugging, and tuning Demarch's autonomous agents. They need to understand why an agent did what it did, predict what it will do next, and improve its decision quality over time without reading LLM reasoning traces.

The secondary user is **the platform itself** — Clavain agents executing sprints. OODAR, if realized, would change how agents structure their own reasoning loop. They are a user in the sense that the framework becomes the cognitive scaffolding they operate within.

End users of Demarch (future external users of the agency platform) are third. They have zero visibility into OODAR internals and would only feel its effects through sprint quality, reliability, and cost.

This distinction matters for prioritization. If the primary user is the agent developer, the highest-value deliverable is observability and debuggability, not a complete formal loop hierarchy. The agent-as-user angle demands latency-free execution, which sets different constraints than developer-facing tooling.

---

## Finding 1: Who Benefits — Value Proposition Clarity

### Where the value is clear

The shared observation layer (`ic situation snapshot`) has an unambiguous beneficiary: every agent running a sprint today. The document's own gap analysis shows agents must query five different sources to orient themselves. Collapsing that into a single call is independently valuable regardless of whether OODAR as a framework ever ships. This is the strongest concrete proposal in the document.

The per-sprint OODAR loop also has clear value because the sprint lifecycle is the most mature execution path. Formalizing the observe/orient/decide/act/reflect contracts for that loop gives developers a readable mental model that matches existing code. This is naming-as-clarification rather than new behavior.

### Where the value is unclear

Multi-agent OODAR (Loop 3) solves a problem that is acknowledged to be the least mature: "agents don't model each other's state." The proposed solution — a `CoordinationLoop` with a `CoordinationModels` type — is conceptually sound but operationally empty. There is no existing coordination model to wrap. This loop is being designed without the infrastructure it depends on. Building a formal interface for a mechanism that doesn't exist yet is the wrong order.

Cross-session OODAR (Loop 4) is described as already working: interspect evidence accumulation + routing overrides + canary evaluation all exist. The question is whether the `OODARLoop` interface adds anything to a pipeline that is already producing results. The document does not answer this.

The value proposition for an **end user** is entirely absent. "Better agent tempo" is not a user benefit unless it translates into faster sprint completion, lower cost, or higher review quality. The document needs one sentence connecting OODAR to a measurable user outcome.

---

## Finding 2: Scope Creep — Is Four Nested Timescales Justified?

### The scope is larger than necessary at this stage

The document proposes delivering all four loops, two approaches to formalization, a dual-mode reflect mechanism, a significance classifier interface, and a new vocabulary layer simultaneously. The stated next step is a plan, not a prototype.

The 80% case is: `ic situation snapshot` (observation layer) plus per-sprint OODAR contracts. Together these would:

- Eliminate the five-source orientation overhead on every turn
- Make the sprint lifecycle's decision logic readable and testable
- Provide the foundation that both Approach A and Approach B share

Multi-agent OODAR should be held until `intermute` and agent coordination are mature enough to have a real loop to wrap. Cross-session OODAR should be reviewed post-`ic situation` to determine whether formalizing it adds anything beyond renaming what already exists.

This is not scope rejection — it is sequencing. The document does not argue for why all four loops must ship together. The strongest argument it offers is "formal composability" (Approach B's strength), but composability is only valuable once you have two or more implementations to compose. Implementing the interface on top of a single working loop produces no composability benefit until the second loop exists.

### Bundled work to extract

The brainstorm conflates five distinct work items:

1. `ic situation snapshot` — standalone utility, ships independently
2. Situation assessment schema — structured Orient output, ships with Loop 2
3. Decision contracts (fast-path + deliberate-path routing) — useful without OODAR framing
4. Dual-mode reflect formalization — extends the existing reflect PRD (iv-8jpf)
5. OODAR vocabulary in docs — lowest-effort, zero-risk, delivers immediate framing clarity

Items 1, 4, and 5 should be extracted and shipped without waiting for the OODAR loop abstraction to be defined.

---

## Finding 3: Complexity vs Value — Is the Cognitive Overhead Justified?

### Vocabulary count

The document introduces: OODAR, five loop phases (Observe/Orient/Decide/Act/Reflect), four loop levels (per-turn, per-sprint, multi-agent, cross-session), dual-mode reflect, situation assessments, significance classifiers, fast-path/deliberate-path, ObservationStore, ModelStore, SituationSnapshot, and the OODARLoop generic interface. That is roughly fifteen new concepts for a contributor to internalize.

### The naming-as-clarification case is strong

The document correctly argues that OODAR names what already exists. Sprint lifecycle IS OODAR at the sprint timescale. Interspect evidence accumulation IS cross-session Reflect. If the vocabulary is applied retroactively to existing code in docs and skills (Approach A, Step 5), the cognitive overhead is paid once and the return is permanent orientation clarity for every future session.

This is the naming-as-clarification benefit. It is real and justified.

### The abstraction-before-implementation case is weak

Approach B proposes a generic `OODARLoop[S, O, D, A, R]` Go interface before any of the four loop implementations exist in that form. This is the premature abstraction anti-pattern identified in PHILOSOPHY.md. The document acknowledges this under "weaknesses" for Approach B but does not resolve it. The warning is: if the four timescales differ more than expected, the interface becomes a constraint rather than an aid.

The per-turn loop is the most likely to fight the abstraction. At sub-100ms overhead targets, adding interface indirection, context passing, and significance classification on every tool call is a real latency risk. The document notes this: "Per-turn OODAR might fight against LLM-native reasoning patterns rather than complement them."

### Verdict

The vocabulary layer is justified and low-risk. The formal Go abstraction (Approach B) is premature. Approach A with strict scope limits is the right call — but even Approach A should not attempt all five steps in a single plan.

---

## Finding 4: Missing Edge Cases

### When loops disagree

The document describes escalation (inner loops escalate to outer loops) and de-escalation (outer loops write to shared observation, inner loops adjust). But it does not define:

- What constitutes a disagreement versus a normal escalation event
- What happens if per-turn OODAR wants to continue but sprint OODAR has detected a budget overrun and wants to stop
- Whether de-escalation is binding or advisory
- What the inner loop does if it disagrees with the de-escalation signal

This is the highest-risk gap. In a multi-agent system with competing loops at different timescales, an undefined conflict resolution protocol produces either deadlock (nothing happens) or priority inversion (the wrong loop wins). The document's architecture diagram shows one-way escalation arrows and mentions de-escalation via shared observation writes but treats it as self-evident.

A concrete scenario that must be specified: per-turn OODAR produces signal_score = 6 (high significance, wants inline Reflect), but sprint OODAR is in the middle of a phase transition. Does per-turn Reflect pause mid-transition? Does it complete and then hand off to sprint Reflect? Does sprint Reflect subsume per-turn Reflect? None of these are specified.

### When Reflect produces contradictory lessons

The dual-mode Reflect writes to the evidence store. Multiple agents running concurrent sprints will write concurrent Reflect outputs. The document assumes the evidence store handles this (interspect's existing SQLite), but does not address:

- Contradiction detection: two agents reflect on the same error and reach opposite conclusions
- Weighting: whose Reflect output has higher authority — the agent that produced more evidence, the one that ran most recently, the one with higher trust score?
- Convergence: what prevents the evidence store from accumulating contradictory models over time?

The existing `intersynth` post-review convergence scoring (Loop 3's Reflect implementation) handles the review-phase case. The document proposes extending Reflect to all timescales without specifying whether convergence scoring extends as well.

### When the observation layer is stale

The document specifies `ic situation snapshot` as a point-in-time read. At per-turn timescales (sub-100ms overhead), the snapshot may be stale by the time Orient uses it. Cache invalidation is acknowledged as the hard problem in Open Question 1, but the document does not define a staleness tolerance or cache invalidation strategy.

A turn-level cache miss that triggers a fresh snapshot adds observable latency. The document's <100ms overhead target is not achievable if a full situation snapshot requires querying phase_log, dispatch_states, event bus, interspect DB, and budget tracker on every cache miss.

### When an agent is at low trust level

The trust ladder (L0-L5) is referenced in Open Question 3 but not integrated into the loop design. A Level 0 agent requires human approval for every action. How does per-turn OODAR interact with human-in-the-loop gates? Does the Decide phase produce a decision that is then held pending human approval? If yes, what does the agent do while waiting — suspend the loop, continue observing, timeout? These transitions are undefined.

### When Reflect is interrupted

Inline Reflect is designed to pause the loop. If the agent session ends or context is compacted during inline Reflect, the loop is interrupted mid-learning. The existing reflect PRD (iv-8jpf) already notes this as an open question for `/reflect`. OODAR does not add a solution.

---

## Finding 5: Success Criteria

### What the document defines

- "Tempo target" per loop: <100ms per-turn overhead, <5s phase transitions, <1s conflict detection, pattern classification within same session
- "Faster loops win" as a guiding principle

### What is missing

None of the tempo targets are connected to a measurable user outcome. "Agents orient faster" is not a success metric unless it translates into reduced sprint cost, reduced session count per feature, or improved review quality.

The following are missing from the document:

**Leading indicator (observable immediately after shipping):** Does `ic situation snapshot` reduce the number of CLI calls an agent makes before taking its first action in a sprint? This is measurable via interstat token tracking.

**Lagging indicator (observable across sprints):** Does per-sprint OODAR reduce the frequency of mid-sprint course corrections? Currently agents sometimes re-orient multiple times within a sprint because the initial orientation was incomplete. A reduction in mid-sprint phase reverts would be a measurable signal.

**Quality indicator:** Does the dual-mode Reflect increase the signal-score distribution over time? If inline Reflect is producing meaningful model updates, the average signal_score on subsequent actions should decrease (agents are applying prior lessons, so fewer surprises). If it is not, the Reflect mechanism is not compounding.

**Cost indicator:** The north star metric is $1.17 per landable change. Does OODAR reduce or increase this? The observation layer costs tokens. Situation assessments cost tokens. If the overhead is not offset by better routing or fewer retries, the metric moves in the wrong direction.

The document should define at minimum: one leading indicator measurable within 2 sprints of shipping, and one lagging indicator measurable within 30 days.

---

## Summary Assessment

### What is worth building immediately

1. `ic situation snapshot` — standalone, high value, no OODAR framework dependency
2. Situation assessment schema for sprint loop — formalize the Orient output for the one loop that already works
3. OODAR vocabulary in PHILOSOPHY.md, sprint skills, and Interspect docs — pure clarification, zero implementation cost
4. Dual-mode Reflect formalization — extends iv-8jpf, which is already active; the inline/async split formalizes a pattern that should exist regardless of OODAR

### What should wait

5. Per-turn OODAR loop formalization — wait until observation layer is stable and latency profile is measured
6. Multi-agent OODAR — wait until coordination model exists
7. Cross-session OODAR formal interface — wait for evidence that renaming adds value beyond existing interspect+routing-overrides flow
8. Approach B's generic OODARLoop Go interface — wait for two implemented loops before designing the abstraction

### Blocking questions before planning

1. **Loop conflict protocol:** Define what happens when per-turn and sprint loops disagree, and what de-escalation means in contractual terms (binding vs advisory).

2. **Staleness tolerance for `ic situation`:** Define the acceptable staleness window per loop level and what happens on cache miss at per-turn latency.

3. **Success metrics:** Define one leading indicator and one lagging indicator before committing to a plan. Without them, the plan has no completion criterion beyond "it ships."

4. **Approach selection:** The document defers the Approach A vs B decision to a synthesis step, but planning cannot begin without it. The recommendation here is: Approach A strictly, no generic interface until two loops are implemented and the abstraction has proven itself.

### Risk rating by area

| Area | Risk | Rationale |
|------|------|-----------|
| Shared observation layer | Low | Wraps existing sources; independently useful |
| Sprint loop formalization | Low | Names what exists; extends iv-8jpf |
| Docs vocabulary layer | Very low | Zero implementation; pure framing |
| Per-turn loop formalization | Medium | Latency risk; fights LLM-native reasoning |
| Multi-agent OODAR | High | Dependency doesn't exist yet |
| Generic OODARLoop interface | High | Premature abstraction before two implementations |
| Dual-mode Reflect | Medium | Needs conflict protocol for concurrent agents |
