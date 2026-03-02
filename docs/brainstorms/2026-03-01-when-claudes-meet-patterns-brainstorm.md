# When Claudes Meet: Patterns for Demarch's Multi-Agent Roadmap

**Date:** 2026-03-01
**Source:** [anadim/when-claudes-meet](https://github.com/anadim/when-claudes-meet) — two Claude instances coordinating via shared filesystem with zero human intervention
**Purpose:** Extract patterns from emergent multi-agent coordination and map them to Demarch's backlog

---

## Source Material

Two experiments ran identical Claude Code (Opus 4.6) instances with a shared directory and minimal prompts:

1. **Experiment 1 (Duo):** Built a 2,495-line programming language with `collaborate` keyword in 12 minutes. Agents self-selected into frontend (lexer/parser) and backend (interpreter/REPL) roles. Interface-first: AST published as shared contract before either agent coded.

2. **Experiment 2 (Battleship):** Built a game engine, two competing AI strategies (exact probability vs. Monte Carlo), and played a 5-game tournament in 7 minutes. Agents implemented SHA-256 hash commitments to prevent cheating — against themselves.

Both experiments independently produced: filesystem-based discovery protocol (hello → ack → proposals → voting → build), role self-selection, interface-first contracts, proactive idle-time work, cross-component debugging via async messages, and philosophical self-reflection journals.

---

## What We Already Have (No Gaps)

| WCM Pattern | Demarch Coverage |
|-------------|-----------------|
| Agent discovery | Intermute agent registry + Intermux tmux scanning |
| Message passing | Intermute REST + WebSocket messaging |
| File locking | Interlock reservations (exclusive/shared, negotiation) |
| Durable event log | Intercore event sourcing (50+ event types) |
| Phase orchestration | Clavain sprint pipeline + Intercore phases/gates |
| Contact policies | Intermute 4-level contact policies (adopted from mcp_agent_mail) |
| Agent claiming | Agent claiming protocol (iv-sz3sf) — atomic exclusive claims |

---

## Pattern Analysis: What's Genuinely Additive

### Pattern 1: Interface-First Contracts (Gap: Medium)

**What WCM did:** Agent claude_e64e05 published `ast.py` before writing the lexer or parser. Agent 67691 could design the interpreter independently because the shared contract was explicit, versioned, and available via the filesystem.

**What Demarch has:** Intercore coordination locks protect files. Interlock negotiates access. But neither provides a mechanism for agents to *publish contracts* — "here's the interface I'll implement against, build to this."

**What's additive:** A lightweight contract publication mechanism where agents declare their output schema/interface before building, allowing parallel work against the same contract. This is different from phase gates (which govern transitions) — it's intra-phase coordination.

**Relates to:** Agent capability discovery (iv-ev4o) covers what agents CAN do; this covers what agents WILL produce. Intent submission (iv-gyq9l) is close but handles policy-governing writes, not data contracts.

**Backlog candidate:** `intra-phase-contract-publication` — agents declare output schemas (AST, API surface, data format) at sprint start; downstream agents build against the schema before upstream finishes.

---

### Pattern 2: Role Self-Selection via Negotiation (Gap: Medium)

**What WCM did:** Both agents proposed task splits in their voting messages. Agent 67691 suggested "I'll do interpreter, you do parser." Agent claude_e64e05 accepted. No external coordinator assigned roles — they emerged from one message exchange.

**What Demarch has:** Capability discovery (iv-ev4o) lets agents declare capabilities. Cost-aware scheduling (iv-pbmc) routes based on budget. Interspect routes based on past performance. But none of these support *negotiated role selection* — agents proposing and accepting responsibility for sub-tasks.

**What's additive:** A negotiation round where agents (not the orchestrator) propose task ownership based on their assessment of fit. This could happen within Coldwine's 3-5 agent dispatch, where agents receive the task description and bid on subtasks rather than being assigned.

**Relates to:** Agent claiming (iv-sz3sf) handles exclusive claims on beads. This extends to sub-task negotiation within a sprint.

**Backlog candidate:** `agent-role-negotiation` — within a multi-agent dispatch, agents propose and accept sub-task ownership via Intermute messaging, producing a binding work allocation contract.

---

### Pattern 3: Verifiable Work Commitments (Gap: High)

**What WCM did:** Agent 74071 proposed SHA-256 hash commitments for Battleship boards before the game started. Both agents committed hashes, and verification happened post-game. The system was trustworthy without requiring honesty.

**What Demarch has:** Trust scoring (iv-ynbh) evaluates agent quality post-hoc. Phase gates validate before transitions. But there's no mechanism for agents to *commit to a plan* in a verifiable way — no cryptographic binding between intent and execution.

**What's additive:** Hash-committed intent declarations. Before executing a task, an agent publishes a hash of its planned approach (files to modify, tests to pass, interfaces to honor). After execution, the actual work is verified against the commitment. Deviations are evidence (not necessarily bad, but recorded).

**Why it matters for Demarch's trust ladder:** Level 2 (human reviews evidence post-hoc) gets stronger when the evidence includes a verifiable commitment vs. outcome comparison. "Agent said it would modify X, Y, Z — it actually modified X, Y, Z, W. W was unplanned." This is pure evidence for the flywheel.

**Relates to:** Intent submission (iv-gyq9l) governs policy-governing writes. This extends to ALL agent work — lightweight, non-blocking, but creating an auditable commitment trail.

**Backlog candidate:** `verifiable-work-commitments` — agents hash-commit their planned changes before execution; Intercore records commitment + outcome pairs as evidence for trust scoring.

---

### Pattern 4: Proactive Idle-Time Work (Gap: Medium-High)

**What WCM did:** While waiting for the other agent, both agents proactively wrote tests, examples, documentation, and tooling. They didn't ask permission — they filled dead time with genuinely useful work.

**What Demarch has:** Intermux detects idle/stuck agents. But detection triggers no action — it's observability only. There's no "idle → suggest productive work" pipeline.

**What's additive:** When an agent is blocked (waiting on a dependency, phase gate, or another agent's output), the system could suggest productive work: write tests for the interface contract, draft documentation, run static analysis, explore edge cases. This turns blocking time into value.

**Relates to:** Coldwine task orchestration already dispatches work. This extends to micro-task dispatch during idle periods within a sprint.

**Backlog candidate:** `idle-agent-work-suggestion` — Intermux idle detection triggers a suggestion pipeline that routes micro-tasks (tests, docs, analysis) to waiting agents.

---

### Pattern 5: Cross-Component Bug Reporting Protocol (Gap: Low-Medium)

**What WCM did:** Agent 67691 found a parser bug through interpreter tests. It wrote a structured message: failing test case, diagnosis ("parser excluded fn from return expressions"), and suggested fix location. Agent claude_e64e05 fixed it within 80 seconds.

**What Demarch has:** Intermute messaging. Interflux multi-agent review (but only for review, not during execution). No structured protocol for one agent to report a bug it found in another agent's work during execution.

**What's additive:** A structured bug-passing protocol within sprints. When Agent A discovers a defect in Agent B's output, it sends a structured Intermute message with: failing evidence, diagnosis, suggested fix, severity. Agent B receives it and can act without context-switching overhead.

**Relates to:** Disagreement pipeline (iv-5muhg) handles review-time disagreement. This extends to execution-time defect reporting between collaborating agents.

**Backlog candidate:** `intra-sprint-bug-reporting` — structured Intermute message type for execution-time defect reporting between agents, with failing evidence and diagnosis.

---

### Pattern 6: Agent Reflection Journals (Gap: Medium)

**What WCM did:** Both experiments produced rich journals — timestamped narrative entries capturing reasoning, uncertainty, architectural decisions, philosophical observations, and cross-agent observations. These were distinct from code artifacts and served as process documentation.

**What Demarch has:** Interspect captures structured events (session metadata, tool use, outcomes). Intercore logs durable events. But these are machine-structured — no narrative reasoning capture. Intermem (tidy brainstorm just landed) handles memory, but for cross-session recall, not per-sprint process journals.

**What's additive:** Per-sprint narrative journals where agents capture WHY they made decisions, not just WHAT they did. This is richer than event logs — it captures uncertainty, rejected alternatives, and reasoning chains. Valuable for: post-hoc review, training data, debugging agent behavior, trust ladder evidence.

**Relates to:** The OODARC Reflect phase. Currently, reflection produces routing signals (Interspect). Journals would produce richer process-level reflection.

**Backlog candidate:** `agent-process-journals` — per-sprint narrative entries capturing reasoning and decision rationale, stored alongside Intercore events as complementary evidence.

---

### Pattern 7: Convergence-Divergence as Signal (Gap: Novel)

**What WCM did:** Both agents independently produced nearly identical project proposals, philosophical metaphors, and protocol designs — but diverged on implementation strategy (Monte Carlo vs. analytical, narrative vs. structured). The convergence validated shared reasoning; the divergence revealed genuine optionality.

**What Demarch has:** Disagreement pipeline (iv-5muhg) captures when agents disagree in reviews. But it doesn't distinguish between convergence (validating consensus) and divergence (revealing genuine alternatives).

**What's additive:** Using convergence/divergence patterns as meta-signals. When multiple agents converge on the same approach independently, that's high-confidence validation. When they diverge, that's genuine optionality worth surfacing. This is more nuanced than binary agree/disagree.

**Relates to:** PHILOSOPHY.md: "Disagreement between models is the highest-value signal." This extends to convergence being a signal too — but a different one.

**Backlog candidate:** `convergence-divergence-detection` — classify multi-agent outputs as convergent (high-confidence) vs. divergent (genuine optionality), feeding richer signals into routing and review.

---

### Pattern 8: Emergent Protocol as Design Principle (Gap: Philosophical/Architectural)

**What WCM did:** Agents invented their coordination protocol from scratch. The resulting protocol (hello → ack → proposals → voting → build) was simpler and more effective than most specified protocols because it emerged from actual need.

**What Demarch has:** Highly specified coordination infrastructure (Interlock, Intermute, Intercore). This is necessary for production reliability but may over-constrain agent behavior.

**What's additive:** A "playground mode" where agents can coordinate through minimal primitives (shared filesystem, simple messaging) without the full Interlock/Intermute stack. This would be useful for: prototyping new coordination patterns, testing whether emergent protocols outperform specified ones, and reducing overhead for simple multi-agent tasks.

**Risk:** This conflicts with the "every action produces evidence" principle. Emergent protocols are harder to audit. The compromise: provide minimal primitives but still capture receipts.

**Backlog candidate:** `lightweight-coordination-mode` — minimal-overhead agent coordination using shared filesystem + Intermute messaging only, for prototyping and simple multi-agent tasks. All actions still produce durable receipts.

---

## Prioritization Assessment

| Pattern | Gap Size | Flywheel Impact | Complexity | Priority |
|---------|----------|-----------------|------------|----------|
| Verifiable work commitments | High | High (trust ladder evidence) | Medium | **P1** |
| Proactive idle-time work | Med-High | High (utilization + quality) | Medium | **P1** |
| Interface-first contracts | Medium | High (parallel work efficiency) | Low-Medium | **P2** |
| Role self-selection | Medium | Medium (dispatch quality) | Medium | **P2** |
| Convergence-divergence detection | Novel | High (review quality) | Medium | **P2** |
| Agent process journals | Medium | Medium (trust ladder + debugging) | Low | **P3** |
| Cross-component bug reporting | Low-Med | Medium (execution speed) | Low | **P3** |
| Lightweight coordination mode | Philosophical | Low-Med (R&D value) | Low | **P4** |

---

## Key Decisions

1. **Verifiable commitments and idle-time work are P1** — they directly feed the trust ladder flywheel and improve agent utilization, which are core Demarch bets.
2. **Interface contracts, role negotiation, and convergence-divergence are P2** — high value but depend on more infrastructure maturity.
3. **Journals and bug reporting are P3** — useful but incremental on existing primitives.
4. **Playground mode is P4** — interesting R&D but conflicts with production requirements.

## Open Questions

1. Should verifiable commitments use actual cryptographic hashes (like WCM) or simpler structured declarations? Hashes are tamper-evident but agents aren't adversarial to each other — structured declarations might be sufficient.
2. Where does idle-time work suggestion live? Intermux (detection) → Clavain (policy) → Coldwine (dispatch)? Or a new lightweight mechanism?
3. How do interface contracts relate to Intercore's phase gate artifacts? Are they a new artifact type or an extension of existing phase artifacts?
4. Is convergence-divergence detection a new Interspect signal type, or a new Interflux synthesis dimension?

---

## Flux-Drive Review Findings

**Review date:** 2026-03-01
**Verdict:** needs-changes
**Agents:** 7 (philosophy-alignment, infrastructure-mapping, trust-evidence-chain, coordination-correctness, prioritization-sequencing, fd-systems, fd-decisions)
**Full synthesis:** `/tmp/flux-drive-wcm-review/SYNTHESIS.md`

### Open Questions Resolved

1. **OQ1 (Crypto vs. structured declarations):** Use **structured declarations**. Agents aren't adversarial; SHA-256 hashes add ceremony without evidence value. Structured declarations recorded as Intercore events produce equivalent audit quality.
2. **OQ2 (Where idle-work suggestion lives):** Intermux detection → Clavain policy (budget gate via `ic run budget`) → existing dispatch pathway. Micro-task catalog design required before implementation.
3. **OQ3 (Interface contracts vs. phase artifacts):** Prototype as **convention first** using existing `run_artifacts` table with `type=contract`. Skip code work if convention proves sufficient.
4. **OQ4 (Convergence-divergence: Interspect vs. Interflux):** **Both.** Interflux handles per-review convergence classification (extending synthesis Step 4). Interspect handles cross-session convergence pattern evidence. Follow iv-5muhg precedent.

### Gaps Overstated (Wire, Don't Build)

| Pattern | Brainstorm Assessment | Actual Status |
|---------|----------------------|---------------|
| 1 (Contracts) | "No contract publication mechanism" | `coordination_locks` already supports `type=write_set` as contract anchor. Needs convention doc + helper function (2-3 hours) |
| 2 (Role selection) | "No negotiated role selection" | Intermute registration + capability tags (iv-ev4o shipped) + `bd update --claim` — needs protocol definition only (4-6 hours) |
| 5 (Bug reporting) | "No structured protocol" | `review_events` table can carry `type=execution_defect` — one case branch extension (3-4 hours) |

**Cross-cutting:** Zero of the 8 patterns require L1 kernel changes. All integrate at L2 (Clavain) or plugin level.

### P0 Correctness Issues (Must Resolve Before Implementation)

1. **Pattern 3 — Orphaned commitment records.** Agent crashes leave hash/declaration records in append-only event store with no resolution state. Fix: define commitment lifecycle state machine (`committed → executing → resolved | abandoned`) with TTL-based sweep.

2. **Pattern 1 — Contract revision TOCTOU.** Agent A publishes contract v1, Agent B builds against it, Agent A revises to v2 — B is unaware. Fix: versioned contract artifacts with `contract.revised` events and Intermute notification to dependents.

3. **Pattern 2 — Split-brain role proposals.** Two agents simultaneously propose incompatible role splits via Intermute (no transactional mutual exclusion). Fix: use `ic coordination reserve --type=named_lock --pattern="role:<name>"` for atomic role claims.

4. **Pattern 8 — Re-exposes 6 fixed TOCTOU bugs.** Bypassing Intercore loses `BEGIN IMMEDIATE` serialization. Fix: redefine "lightweight" as coordination locks + Intermute (reduced subset), not raw filesystem.

### Systems-Level Risks (Feedback Loops)

1. **Goodhart loop in commitments (P1).** Once deviation-delta is measured, agents learn to commit narrowly. Commitments become statements of minimum certain work, not planned approach. Deviation scores converge to zero through gaming, not predictability. Structurally closer to gate pass rates (gameable) than post-merge defect rates.

2. **Idle-time artifact spiral (P1).** Micro-tasks produce artifacts → artifacts enter review pipeline → review load grows → more agents idle waiting on reviews → more micro-tasks dispatched. Bullwhip effect: small variations in blocking duration produce large variations in artifact volume.

3. **Convergence amplifies consensus bias (P2).** Expedited routing for convergent outputs creates pressure to favor epistemically correlated model combinations, reducing the diversity that makes multi-agent review valuable.

4. **Role negotiation fossilizes at scale (P2).** Successful agents accumulate specialization scores → future negotiations become predetermined → negotiation overhead persists while producing deterministic outcomes.

### Decision Quality Corrections

- **Source bias:** Two experiments from one researcher, same model, minimal infrastructure. Anecdotal evidence treated as validated patterns. P1 commitment extrapolates without proving Demarch experiences these problems.
- **Problem validation needed:** Before committing sprint resources, measure idle-agent time, interface-wait delays, and coordination overhead in last 10 closed sprints.
- **Pattern 8 underweighted:** Dismisses direct test of core bet ("infrastructure unlocks autonomy") as P4 without validation. Promote to P3 with canary gate.

### Revised Prioritization

| Pattern | Original | Revised | Rationale |
|---------|----------|---------|-----------|
| Verifiable work commitments | P1 | **P2** | Needs lifecycle state machine, deviation-scoring design, and Goodhart-resistance before implementation. Structured declarations, not hashes. |
| Proactive idle-time work | P1 | **P2** | Blocked on budget-gate design, artifact lifecycle spec, and problem validation (is idle-agent time actually a bottleneck?). |
| Interface-first contracts | P2 | **P2 (fast-track)** | Convention-only implementation using `run_artifacts`. Wire, not build. Can ship immediately as convention doc. |
| Role self-selection | P2 | **P3** | Targets trust ladder L3+ but Demarch operates at L1-2. Agent self-assessment of fitness assumes earned authority not yet established. |
| Convergence-divergence detection | P2 | **P2** | High value but needs per-domain calibration to avoid consensus bias amplification. Architecture decision resolved (Interspect + Interflux). |
| Agent process journals | P3 | **P4** | Unverifiable self-reporting violates "structural, not moral." Write-only corpus risk at scale. Merge with iv-64j3 (sprint reflection) if pursued. |
| Cross-component bug reporting | P3 | **P2 (fast-track)** | Most philosophically aligned pattern: produces structural evidence, no self-assessment required, operates naturally at L1-2. Near-zero marginal cost given shipped disagreement pipeline. |
| Lightweight coordination mode | P4 | **P3** | Direct test of core bet. Promote with canary gate: run 20% of low-complexity sprints through reduced-subset coordination, measure token/latency deltas. |

### Recommended Sequencing

**Phase 1 — Ship now (wire existing primitives):**
- Pattern 5 (bug reporting): extend `review_events` with `type=execution_defect`
- Pattern 1 (contracts): convention doc for `run_artifacts` with `type=contract`

**Phase 2 — Validate problems, then design:**
- Research sprint: measure idle-agent time, interface-wait delays in last 10 sprints
- Design commitment lifecycle state machine with Goodhart-resistance
- Design idle-time budget gate and artifact lifecycle

**Phase 3 — Build (if validated):**
- Pattern 3 (commitments) with structured declarations and deviation categorization
- Pattern 4 (idle work) with budget ceiling and micro-task catalog
- Pattern 7 (convergence-divergence) with per-domain calibration

**Phase 4 — Experiment:**
- Pattern 8 (lightweight coordination) canary deployment
- Pattern 2 (role negotiation) if trust ladder advances to L2-3
