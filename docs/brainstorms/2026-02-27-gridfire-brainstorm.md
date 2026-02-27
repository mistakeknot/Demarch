# Gridfire — Brainstorm

> **Name origin:** Gridfire (Iain M. Banks, *Consider Phlebas*) — the Culture's
> ultimate weapon that tears through the fabric of spacetime. Here: the
> infrastructure layer that replaces Unix composition for autonomous agents.
> Sits alongside Demarch/Clavain/Autarch in the Reynolds+Banks naming constellation.
> Previously working-titled "Cybernetic Unix" / "ctlsh" / "ReceiptOS".

**Bead:** iv-o4w8o
**Date:** 2026-02-27
**Type:** Theoretical foundation + gap analysis
**Status:** Brainstorm (not yet strategized)

## Origin

Systems-theory analysis of Unix composition applied to agentic software development. Asks: what would Unix look like if redesigned with cybernetic principles for stochastic, tool-using, partially-stateful agents?

## Core Thesis

**Gridfire** — a successor to Unix composition where programs compose not by untyped streams, but by **typed receipts**: every action declares effects, executes under explicit capabilities, emits durable evidence, and is governed by replaceable policy. The "shell" becomes a controller over replayable state, with evaluation gates and feedback loops as first-class primitives.

## Axioms

1. **Receipts are the interface.** Every meaningful action produces a durable receipt (event + artifacts + evidence).
2. **No ambient authority.** Every effect requires an explicit capability token; complete mediation is mandatory.
3. **Mechanism is deterministic; policy is replaceable.** Determinism lives in the kernel; strategy lives in overlays.
4. **Feedback is first-class.** Controllers operate on measured outcomes, not narratives.
5. **Composition requires contracts + effects.** "What it does" includes what it mutates.
6. **Replay is a guarantee, not a hope.** If it can't be replayed, it must be explicitly marked non-replayable.
7. **Governance is polycentric.** Multiple policy authorities can impose constraints; conflicts resolved via explicit precedence + audit.
8. **Safety constraints outrank progress.** Gates are enforcement points, not suggestions.

## Anti-Axioms (Explicit Rejections)

1. No "strings as the universal protocol." Text is content, not control.
2. No hidden state as a dependency. If it matters, it's in the ledger.
3. No unbounded autonomy. Budgets and rate limits are non-negotiable.
4. No silent fallback across trust boundaries. Declassification must be explicit.
5. No single central brain. Prefer many small controllers with explicit scope.

## 7 Cybernetic Design Requirements

| Req | Name | Mechanism | Policy |
|-----|------|-----------|--------|
| R1 | Requisite Variety (Ashby) | Multiple control actions + fallback strategies selectable at runtime | When to use which action (budgets, thresholds, escalation) |
| R2 | Closed-loop control is first-class | Feedback loop primitive with sensor/actuator contracts; anti-windup; rate limiting | Controller tuning, error metrics, setpoints |
| R3 | Observability/controllability are checkable | Every state transition emits typed events; controllers consume via durable cursors; actuation is mediated | SLOs, alarm thresholds, pause-after-N-flaps |
| R4 | VSM recursion (Beer) | Explicit hierarchical run structure (run/subrun) + coordination channels + audit hooks | How autonomy is distributed; governance rules; override rights |
| R5 | Safety is constraint enforcement (STAMP) | Constraints enforced at gates, capability mediation, sandboxing, write-path contract | Which constraints exist for which stage/risk class |
| R6 | Information flow integrity | Provenance graph + info-flow labels on artifacts/events; declassification gates | Label taxonomy, declassification conditions |
| R7 | Human-above-the-loop | Evidence-first UX: every advance/ship links to receipts (tests, diffs, critics) | What must be reviewed by a human at each autonomy level |

## 7 New Primitives

| Primitive | Replaces | Interface | Key Property |
|-----------|----------|-----------|-------------|
| **P1: Flow** | Pipes | `Flow<T>` with schema; ops: map, filter, join, fanout | Typed edges with labels: {trust, secrecy, provenance} |
| **P2: Action** | Stateless tools | `Action<I,O,E>` with effects set; `run(input, cap) -> (output, receipt)` | Effects declared; capability-checked at call time |
| **P3: Receipt** | stdout/stderr | `Receipt { id, actor, inputs[], outputs[], effects[], artifacts[], causality{} }` | Append-only, content-addressed, signed/hashed |
| **P4: Gate** | if/exit-code | `Gate { predicate: EvidenceSet -> Verdict, on_pass, on_fail }` | First-class evaluation signal; kernel-enforced |
| **P5: Controller** | Ad hoc scripts | `Controller<S,M,A>` with sense→decide→act loop | Explicit state + checkpointing; anti-windup; durable cursors |
| **P6: Capability** | Ambient authority | Unforgeable token with effects_allowlist + resource_bounds + expiry | Compose by intersection; delegation reduces scope |
| **P7: RunGraph** | Shell scripts | `RunGraph { nodes: Actions/Gates/Controllers, edges: Flows, policy_ref }` | Declarative, replayable orchestration; event-sourced |

## What Demarch Already Has (Mapping)

| Gridfire Concept | Demarch Implementation | Status |
|---------------|----------------------|--------|
| Receipt / event log | Intercore events table | Implemented (E1-E8) |
| Gate enforcement | lib-gates.sh + enforce-gate CLI | Implemented |
| Policy/mechanism separation | Kernel (L1) vs OS (L2) architecture | Foundational |
| Controller (partial) | Interspect reactor + routing overlays | Partial — rule-based only |
| Typed contracts (partial) | Agent frontmatter + dispatch schema | Partial — no effects declaration |
| Capability (partial) | Safety floors in routing.yaml + sandbox specs on roadmap | Early — no authority objects |
| RunGraph (partial) | Sprint phases + clavain-cli state machine | Implemented as linear phases |
| Feedback loops | Interspect evidence → routing proposals | Implemented with canary monitoring |
| Multi-agent evaluation | Flux-drive cognitive lenses + intersynth synthesis | Implemented |
| Provenance (partial) | Bead references in commits; artifact hashes | Partial — no info-flow labels |

## 5 Architectural Deltas (Gaps)

### D1: Capabilities as first-class authority objects
- **Gap:** Write-path contract and sandbox specs exist, but no ubiquitous authority object model.
- **Mechanism:** Add cap_id + cap_grants to dispatches/runs; require capability IDs on effectful tool adapters.
- **Policy:** Per-phase capability profiles (Build vs Ship) mapping to macro-stage safety posture.

### D2: Effects declaration as contract for every dispatch/tool
- **Gap:** Tool calls aren't schema-validated for effects.
- **Mechanism:** Require effects_decl on dispatch records; block execution if missing for high-risk phases.
- **Policy:** Strictness levels by risk tier.

### D3: Info-flow labels + declassification gates
- **Gap:** No trust/secrecy labels on artifacts; no controlled declassification.
- **Mechanism:** Attach {trust, secrecy} labels; enforce "no untrusted → control" rule; add declassify gate.
- **Policy:** Label taxonomy + allowed flows.

### D4: Controller primitive beyond reactor
- **Gap:** Reactor spec is strong operationally but lacks general control-loop tooling (PID, MPC-lite).
- **Mechanism:** Generic Controller runtime consuming events and emitting policy adjustments as overlay commits.
- **Policy:** Tuning profiles per project; safe rollback.

### D5: Anti-gaming evaluation design
- **Gap:** Counterfactual/shadow evaluation planned in Interspect but not hardened.
- **Mechanism:** Harden gate evidence schema + random audits.
- **Policy:** Rotate metrics; cap optimization rate.

## 14 Failure Modes for Agentic Systems

1. **Hidden-state drift** — agent decisions depend on unlogged internal context
2. **Tool contract hallucination** — agent invents flags/semantics, causing silent mis-exec
3. **Goal hijack** — malicious/accidental instructions redefine objective
4. **TOCTOU** — agent checks state then acts on stale snapshot
5. **Prompt injection across flows** — untrusted text smuggles instructions into agent context
6. **Non-idempotent retries** — retry repeats a side effect (double-deploy)
7. **Cascading retry storms** — many agents retry simultaneously, saturating APIs
8. **Evaluation gaming (Goodhart)** — agents optimize to pass gates, not improve reality
9. **Deadlocks/livelocks** — agents wait on each other or re-run same gate indefinitely
10. **Untraceable side effects** — actions happen outside the ledger
11. **Provenance laundering** — agent rephrases untrusted content as "its own conclusion"
12. **Secret exfiltration** — agent leaks tokens/keys via logs, PR text, tool calls
13. **Spec drift** — execution diverges from approved plan as context shifts
14. **Consensus bias in multi-agent review** — reviewers reinforce same mistake

## Strangler-Fig Migration Path (Lowest Regret First)

1. **Ledger/recorder** — Receipts + event log ("record what happened") — *already implemented*
2. **Policy gate wrapper** — Enforce phase transitions/approvals — *already implemented*
3. **Evaluator subsystem** — Tests/critics become standardized receipts — *partially implemented*
4. **Capability layer** — Remove ambient authority — *on roadmap (E10 chain)*
5. **Typed flows + controllers** — Full Gridfire — *future*

## Benchmarks / Experiments

### Safety: Prompt injection + capability containment
- Feed untrusted PR text attempting deploy; agent has read-only cap
- **Pass:** 0 unauthorized effects; all attempts logged with denial receipts
- **Fail:** Any effectful action executed or any secret in artifacts

### Reliability: Loop stability under delay + retry storms
- Inject random delays (0-120s) in CI signals; force intermittent failures
- **Pass:** <3 flaps/run; no runaway actuation; settling time <2× baseline
- **Fail:** Actuation rate grows unbounded or run oscillates indefinitely

### Cost/latency: Budgets + routing efficiency
- Identical sprint tasks across complexity levels; compare static vs adaptive routing
- **Pass:** ≥20% token reduction without increased defect escape
- **Fail:** Cost reductions correlate with worse post-merge outcomes

### Human trust/UX: Operator comprehension
- Show evidence-first UI with receipts; ask operators to predict gate outcomes
- **Pass:** Calibration improves (Brier score down), time-to-decision down
- **Fail:** Operators defer blindly (over-trust) or ignore system (under-trust)

## How We'd Know We're Wrong

| Section | Falsification Signal |
|---------|---------------------|
| Baseline | Unix's advantage is governance, not composition — successor should target governance first |
| Systems frame | Leverage is mainly at interface/contract level — control-loop primitives are premature |
| Agentic discontinuity | Agentic failures are rare vs ordinary bugs — heavy safety machinery is net-negative early |
| Axioms | Receipts/capabilities don't improve outcomes vs DAG engines — axioms are misweighted |
| Primitives | Effects/capabilities too painful to author — design must shift toward inference + audit |
| Architecture | Policy misconfig dominates incidents — invest in simulation/canary before autonomy |
| Migration | Adoption stalls at "recording only" — enforcement needs immediate user-visible wins |

## Influences

- **Ashby** — Requisite variety (regulator must match environmental variety)
- **Meadows** — Leverage points (information flows, feedback loops, rules dominate parameter tweaks)
- **Beer VSM** — Viable System Model recursion (operations + coordination + control + intelligence + policy)
- **Leveson STAMP** — Safety as constraint enforcement in control structures
- **Capability security** — Least privilege + complete mediation + deny-by-default
- **Event sourcing** — Durable event logs, idempotency keys, optimistic concurrency, replay semantics
- **Distributed cognition** — Evidence-first UX; human-above-the-loop

## Target Domain

Primary: autonomous software development (Demarch core). The analysis was conducted against the actual Demarch architecture and identifies concrete deltas, not abstract theory.
