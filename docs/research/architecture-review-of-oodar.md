# Architecture Review: OODAR Loops for Agent Decision-Making

**Source document:** `docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`
**Reviewer context:** Root `AGENTS.md`, `PHILOSOPHY.md`, Gridfire brainstorm, intercore internal packages, clavain scripts
**Date reviewed:** 2026-02-28
**Status:** Architecture review — pre-plan

---

## Executive Summary

The OODAR brainstorm names something real. Demarch already has the four timescale loops; the document is largely an audit of existing infrastructure reframed through a cybernetic lens, plus a proposal for formalizing what exists. The naming clarity alone is valuable. The two approaches differ primarily in _when_ the abstraction hardens, not in the underlying semantics. The critical architectural question — kernel (L1) vs OS (L2) — has a defensible answer, and the generic Go interface design has one structural flaw that needs addressing before committing to either path.

The bottom line: the Shared Observation Layer (the `ic situation snapshot` proposal) belongs in intercore and should ship first regardless of approach. The generic `OODARLoop` interface proposed in Approach B should not go in intercore's public package surface — it belongs in an intercore-internal package at most, with instantiation and policy-carrying implementations remaining in clavain. The generic interface as written has a premature extensibility problem that the brainstorm partially acknowledges but understates.

---

## 1. Module Boundary: Where Does the OODAR Primitive Live?

### The Mechanism/Policy Question

PHILOSOPHY.md states the core principle clearly: "The kernel doesn't know about Claude Code; the OS is a thin adapter." The AGENTS.md description of intercore is equally precise: "The kernel is mechanism, not policy — it does not know what 'brainstorm' means, only that a phase transition happened and needs recording."

Applying this to OODAR:

**What is mechanism in OODAR:**
- The event log that lets any loop observe system state (already in intercore as `ic events`, `ic dispatch`, `ic coordination`)
- The snapshot aggregator that collapses multiple queries into one (`ic situation` — proposed in both approaches)
- The durable cursor over the event stream (`ic events tail --consumer`)
- The significance classifier threshold enforcement (signal scoring is an `ic`-queryable value)

**What is policy in OODAR:**
- What constitutes an "observation" for a per-turn loop (tool result vs LLM output vs file diff)
- What the Orient phase concludes — the mental model content
- What decision thresholds mean (signal_score ≥ 4 is a policy number, not a mechanism invariant)
- When to escalate from per-turn to sprint scope
- The specific Sensor/Model/Actuator/Reflector implementations for each of the four levels

**Verdict on placement:**

The `ObservationStore` interface and `ic situation` implementation belong in intercore. These are query aggregation with no policy content — the kernel already aggregates events, dispatch states, phase log, coordination locks, and budget state as separate CLI commands; `ic situation snapshot` is a convenience projection over existing tables, which is precisely the kind of mechanism addition that fits L1.

The `OODARLoop[S,O,D,A,R]` generic interface does **not** belong in intercore as a public exported type. Exporting it from the kernel would mean the kernel has a formal dependency on a 5-phase loop model that constrains how all future control structures must be shaped. This is premature generalization at the wrong layer. The kernel should remain a ledger of transitions and a provider of queries, not a framework for how consumers must structure their decision logic.

If Approach B is pursued, the `OODARLoop` interface should live in `core/intercore/internal/oodar/` — an internal package that is not importable by outside consumers, accessible only to intercore's own CLI commands. Alternatively, and this is the cleaner path, it could live in `sdk/interbase/` as a shared library contract that both intercore commands and clavain can depend on, without polluting the kernel's stable public surface.

**The coordination packages already in intercore clarify the right pattern.** `internal/lifecycle/` defines the agent state machine. `internal/dispatch/` defines the dispatch record. `internal/phase/` defines the phase transition machine. None of these are OODAR loops — they are narrow mechanisms. OODAR is a composition pattern _over_ these mechanisms; it belongs one level up.

### Where Each Loop's Implementation Lives

| Loop | Sensor lives in | Orient/Decide lives in | Act/Reflect lives in |
|------|----------------|----------------------|----------------------|
| Per-Turn | intercore (tool result events) | clavain (LLM reasoning, routing tables) | clavain (signal scoring, `/compound`) |
| Sprint | intercore (phase state, gate results) | clavain (`sprint_read_state()`, `phase_actions`) | intercore + clavain (phase.Advance + reflect phase) |
| Multi-Agent | intercore (coordination locks, dispatch states) | clavain / intermute (conflict model) | intercore (dispatch spawn/kill) |
| Cross-Session | interspect (evidence store) | interspect (pattern classification) | clavain (routing-overrides.json) |

All four loops _read_ from intercore mechanisms. All four _decide and act_ through clavain policies or interspect overlays. The Shared Observation Layer is a read-only projection of intercore state — it belongs in intercore. The loop logic does not.

---

## 2. Coupling Analysis: Bottom-Up vs Top-Down

### Approach A Coupling Profile

Approach A adds contracts as a series of schema agreements. Each contract is a point coupling: the caller knows what the snapshot looks like, the orient output schema, the decision format. These are data contracts, not behavioral contracts.

**Coupling risk in A:** The main risk is that four bespoke OODAR implementations will subtly diverge. The per-turn loop's situation assessment schema will accumulate fields that the cross-session loop cannot produce, because they were designed for different callers. Schema drift between levels is the predictable failure mode. The brainstorm documents this as "no guarantee they compose well" but understates the maintenance cost: each level's orient output being schematically independent means the shared observation layer has no type-enforced consumer, which invites silent version skew.

There is also a hidden coupling in Approach A's Step 3 (Decision Contracts). Routing tables extracted to JSON and made queryable are a good step. But the "fast path confidence ≥ 0.8" threshold is being introduced as a shared decision rule that spans all four loop levels. This is a policy value that will need different calibration at different timescales — 0.8 confidence appropriate for a per-turn decision is not the same as 0.8 confidence appropriate for a routing override that persists for weeks. Encoding this as a single threshold creates false uniformity.

### Approach B Coupling Profile

Approach B front-loads coupling into the generic interface definition. The `OODARLoop[S,O,D,A,R]` interface has five type parameters, each an interface itself. This means implementers must satisfy not just the method signatures but also implement five sub-interfaces: `Sensor`, `Orientation`, `Decision`, `Action`, `Reflection`.

**Coupling risk in B:** The interface design as written conflates the _loop structure_ (cycle, observe-orient-decide-act-reflect) with the _type parameters_ (what kind of sensor, what kind of orientation). The `Observe(ctx, sensor S) (Observation, error)` signature passes the sensor as a parameter to Observe — this means the loop struct and the sensor are separate allocations, but Observe is called with the sensor passed in. This is an inversion: in a typical control loop, the controller holds a reference to its sensor and calls it; the sensor is not passed in at each invocation. This design would force callers to manage sensor lifecycle externally and pass it in on every call, which is an awkward API for a loop that is supposed to run continuously.

The `Cycle` and `RunLoop` methods appear both as methods on the interface, which means any implementor of `OODARLoop` must also implement the loop runner. This violates the interface segregation principle — consumers that only want to call `Observe` or `Reflect` must accept the full loop implementation contract.

More fundamentally: the brainstorm's Approach B directly extends Gridfire's `Controller<S,M,A>` by adding `R` (Reflect). But the Gridfire brainstorm explicitly classifies the Controller primitive as a future goal (step 5 in the strangler-fig migration path), noting that Demarch is currently at step 3 (Evaluator subsystem). Approach B would jump from step 3 to step 5, bypassing the capability layer (step 4). This is the premature abstraction risk the brainstorm identifies — but it is not just "medium risk," it is specifically misaligned with the Gridfire migration sequence.

### Coupling Between Loop Levels

Both approaches use a shared observation layer with hierarchical decisions. The coupling between levels is primarily through writes to the shared observation layer (Reflect writes back, inner loops read changes on next cycle). This hybrid model is sound in principle — it avoids tight call coupling while maintaining information flow.

The unresolved coupling concern is escalation. The brainstorm lists "when exactly does a per-turn loop escalate to sprint?" as an open question, but this is not just a design gap — it is a coupling contract. For the hybrid model to be coherent, the escalation signal must be a first-class type: not just a threshold crossed but a typed event that the outer loop can consume and act on without reading the inner loop's internal state. Neither approach specifies this contract. Approach A's incremental path makes it easier to defer; Approach B's interface cannot cleanly express it without adding an `Escalate` method to the interface or a separate escalation channel, both of which expand the interface surface before it has been validated.

---

## 3. Pattern Analysis: The Generic Interface Design

### The Five-Parameter Generic Interface

The `OODARLoop[S Sensor, O Orientation, D Decision, A Action, R Reflection]` interface is the most structurally significant decision in Approach B. It deserves close examination.

**What the type parameters buy:** Type safety between the Sensor output and the Orient input; type safety between the Decide output and the Act input. These are real benefits — they prevent a per-turn TurnSensor result from being silently passed to a SprintOrient method.

**What the type parameters cost:** Five interface constraints define the shape of every OODAR loop forever. If the multi-agent loop needs a two-sensor model (both agent state and lock state independently observable), the interface forces it into a single `S Sensor` — requiring either a composite sensor struct (fine) or an interface redesign. If the cross-session loop's Reflect does not produce an immediate `R` value (because canary evaluation takes 20 uses across hours), the `Reflect(ctx, outcome, significance) (R, error)` synchronous signature is incorrect — asynchronous reflect needs a different model.

The brainstorm partially anticipates this with the "async vs inline reflect" distinction, but the interface does not express it. The `significance float64` parameter to Reflect is a policy threshold embedded in a mechanism interface — the interface is asking "should this be inline or async?" but the answer is policy-dependent and the interface cannot carry that distinction at compile time.

**Alternative pattern:** The Gridfire brainstorm's `Controller<S,M,A>` is deliberately three parameters (Sense, Model, Act), which maps directly to the cybernetic control loop. OODAR's addition of Reflect is conceptually sound but does not need to be a fifth type parameter — Reflect can be an optional compositional behavior applied to a `Controller<S,M,A>` instance. This is the composition over capability principle from PHILOSOPHY.md applied to the pattern itself: a Controller that also implements a Reflector is a ReflectiveController, not a fundamentally different interface. This formulation avoids cementing the five-parameter interface as a permanent constraint on all loop implementations.

### Existing Patterns in the Codebase

Intercore's internal packages use narrow, concrete types rather than generic interfaces. `phase.Advance()` takes explicit querier interfaces (`RuntrackQuerier`, `VerdictQuerier`, `PortfolioQuerier`, `DepQuerier`, `BudgetQuerier`) — not a single generic `Querier[T]`. This is deliberate: the existing code trades generality for clarity and avoids the fragile coupling that large generic interfaces create.

The `lifecycle` package defines a concrete state machine with fixed states. The `dispatch` package defines a concrete `Dispatch` struct. Neither uses generics. This pattern is consistent with the CLAUDE.md design decision: "CLI only (no Go library API in v1)." The kernel is a CLI that shells to a database; it is not a library framework. Introducing a generic interface framework at this layer would be architecturally inconsistent.

The scoring package (`internal/scoring/`) is the closest thing to a generic abstraction in intercore, and it uses concrete structs (`Task`, `Agent`, `Assignment`) rather than interfaces. This is the pattern to follow.

---

## 4. Anti-Pattern Assessment

### Approach A Anti-Patterns

**Hidden god-module risk in `ic situation`.** A single command that aggregates phase log, dispatch states, event bus, interspect DB, coordination locks, and budget state into one JSON object is a projection of system state, which is fine. The risk is what happens when its JSON schema becomes the de facto integration contract for OODAR. Every loop that calls `ic situation snapshot` couples itself to the full snapshot schema. Adding a new field to the snapshot becomes a migration event; removing a field breaks all consumers. The schema should be versioned and filtered by consumer from day one, or the snapshot will become the god-object it was meant to replace. Approach A's Step 1 does not address this.

**Incremental schema drift without a unifying type.** Approach A produces four bespoke situation assessment schemas (per-turn, sprint, multi-agent, cross-session) defined in documentation, not code. Schema drift is the predictable outcome. The brainstorm's weakness acknowledgment — "no formal abstraction, each level's OODAR is ad-hoc; no guarantee they compose well" — is not just a composability concern; it is a long-term maintenance tax.

**Policy values in Step 3 masquerading as mechanism.** Extracting routing tables from YAML to queryable JSON is sound. But centralizing all decision logic into a single "fast-path if confidence ≥ 0.8" contract creates a false uniformity. The 0.8 threshold is a policy parameter that different operators and different loop levels need to tune independently. Making it a shared constant couples all loops to a single policy setting.

### Approach B Anti-Patterns

**Premature generalization before the loops are independently validated.** The brainstorm's own implementation sequence (SprintLoop first, then TurnLoop, then CrossSessionLoop, then CoordinationLoop) reveals that the loops have different maturity levels. The sprint lifecycle is "most mature"; the multi-agent coordination loop is "least developed." Designing a unified interface before the least-understood loop (multi-agent) has been built means the interface will be shaped by three of the four loops, and the fourth will be a forcing function that exposes where the interface is wrong. The cost of that discovery is high when the interface is in `intercore/internal/oodar/` and multiple concrete implementations depend on it.

**Synchronous Reflect signature for an inherently asynchronous loop.** `Reflect(ctx, outcome Outcome, significance float64) (R, error)` is synchronous. The cross-session loop's reflect is explicitly async: "background process accumulates evidence, updates models. Benefits arrive on the next cycle." A synchronous interface method that returns `R` cannot represent async reflect without a stub return value or a channel, both of which break the type contract's semantic intent. The brainstorm notes the dual-mode reflect as a feature but does not resolve the interface mismatch.

**Interface bloat through Cycle + RunLoop.** Having both `Cycle(ctx) error` and `RunLoop(ctx) error` as interface methods means every implementor must provide a loop runner. The loop runner is not a meaningful differentiator between the per-turn and cross-session loops — they differ in Sensor, Orient, Decide, Act, and Reflect, not in how they iterate. The loop runner logic should be provided by the framework, not required from implementors. This is the same mistake as requiring every Unix process to implement its own scheduler.

### Both Approaches: The Orient Formalization Problem

Both approaches propose formalizing Orient as a structured output. This is correct in intent. The gap is that "Orient" in the per-turn loop is primarily LLM reasoning — it cannot be fully formalized without either over-constraining what the LLM reasons about or accepting that the structured output is a post-hoc summary of unconstrained reasoning.

Approach A's formalization is "better LLM inputs" — the situation assessment is a richer prompt context, not a replacement for LLM Orient. This is honest about the limitation. Approach B's formalization is "first-class interface method" — Orient becomes a callable that returns `O Orientation`. But for the TurnLoop, the implementation of `Orient` is calling the LLM, which is a network call with variable latency and non-deterministic output. Wrapping this in an interface method does not change its nature; it just adds an abstraction layer over an inherently non-deterministic operation.

The <100ms overhead target for per-turn loops is incompatible with LLM-driven Orient unless Orient is cached. Caching is acknowledged in the brainstorm ("cached across turns in the session") but the cache invalidation problem is noted as the open question. Neither approach provides a cache invalidation model, and this is the hardest part of making per-turn OODAR viable. The architecture review should flag this as a prerequisite design problem, not a follow-up.

---

## 5. Integration with the Existing 5-Pillar, 3-Layer Structure

### Layer Dependency Direction

The 3-layer rule is: L3 (apps) depends on L2 (OS), L2 depends on L1 (kernel). L1 must not depend on L2 or L3.

The `ic situation snapshot` command in Approach A is fine: it is an L1 command that reads L1 data sources (events, dispatch, phase, coordination, budget). Interspect is noted as a source for the snapshot. Interspect is currently "cross-cutting" and "currently housed in Clavain" per AGENTS.md. If `ic situation` queries interspect's SQLite directly, this is a L1 query against L2 data, which violates the layer boundary. If `ic situation` queries an interspect data store that has been moved to L1 (as a separate SQLite or as tables in intercore's own DB), the dependency is clean. This boundary question must be resolved before implementing the shared observation layer.

The cross-session loop's data flow is:
- Observe: interspect evidence (L2 data store, currently in clavain)
- Act: write `routing-overrides.json` (L2 config, read by `lib-routing.sh`)

Both ends of this loop are L2 artifacts. The loop itself cannot live in L1 without importing L2 data. This confirms the earlier placement conclusion: cross-session OODAR belongs in clavain or interspect, not intercore.

### Interspect's Ambiguous Layer

Interspect is described as "cross-cutting (not a layer)" and "currently housed in Clavain." The OODAR brainstorm implicitly treats interspect as a shared L1 service (the `ModelStore` in Approach B reads from interspect). This is an architectural promotion of interspect from L2 to L1, or at least to cross-cutting infrastructure. This is not necessarily wrong, but it is an architectural change that should be explicit. If interspect's evidence store becomes part of the shared observation layer, the question of which layer owns it needs a deliberate answer, not an implicit one baked into a OODAR implementation.

### Gridfire Alignment

The Gridfire brainstorm's strangler-fig migration path positions the Controller primitive at step 5 (future). Demarch is currently at step 3 (evaluator subsystem, partially implemented). The OODAR brainstorm's Approach B jumps to step 5. Approach A advances step 3 (better evaluators, better observation) and stays on the migration path.

Approach B is not wrong — it just assumes the Controller primitive design is stable enough to formalize. The Gridfire brainstorm suggests it is not: "D4: Controller primitive beyond reactor — Gap: Reactor spec is strong operationally but lacks general control-loop tooling." Building `OODARLoop` on top of a controller primitive that is acknowledged to be incomplete creates a layer built on unstable foundations.

The `ic situation snapshot` command from Approach A directly implements the observation half of Gridfire's R3 requirement: "Every state transition emits typed events; controllers consume via durable cursors." This is a concrete step toward Gridfire compatibility without requiring the full controller primitive.

### The Multi-Agent Loop's Structural Gap

The brainstorm identifies the multi-agent Orient as "biggest gap — agents don't model each other's state." This is accurate. But the structural consequence is that the CoordinationLoop's implementation does not yet exist, which means the `OODARLoop` interface cannot be validated against four concrete instantiations — only three. Approach B's type-safety argument ("Go generics enforce that each level's Sensor/Model/Actuator/Reflector are type-compatible") applies only to the three implemented levels. The fourth level, which is the least mature and most likely to reveal interface flaws, will be the last to exercise the design.

This is a concrete argument for Approach A's sequencing: build the multi-agent loop's Orient first (as a bespoke implementation), then extract the shared interface once you know what four real Orient implementations need.

---

## 6. Recommended Path

### Must-Fix Structural Issues

**1. Resolve interspect's layer affiliation before designing the shared observation layer.**
The `ic situation snapshot` command should not query L2 data stores directly. Either interspect's evidence tables migrate to intercore's schema (clean L1), or the snapshot command omits interspect data (acceptable for an initial version), or interspect becomes a separate L1 service with its own `ic`-callable interface. This boundary must be explicit before any OODAR implementation work begins.

**2. Do not place `OODARLoop` as a public exported type in intercore.**
If Approach B's interface is built, it belongs in `core/intercore/internal/oodar/` (intercore-private) or `sdk/interbase/` (shared library). Exporting a five-parameter generic interface from the kernel's public surface would make it a permanent architectural commitment before any of the four implementations are validated.

**3. Design the escalation contract before implementing any loop.**
The hybrid communication model depends on escalation signals from inner to outer loops. Without a typed escalation contract, the Decide phase of each loop has no mechanism to trigger behavior in an outer loop except through writes to the shared observation layer (which is a polling model, not an event model). This creates latency for the very situations — novel circumstances, blockers — where fast escalation matters most.

### Optional Cleanup with Concrete Benefit

**4. Scope the `ic situation snapshot` schema from the start.**
Rather than a single omnibus JSON object, design the snapshot to accept a consumer filter: `ic situation snapshot --consumer=per-turn` returns the fields relevant to per-turn decisions, `--consumer=sprint` returns sprint-relevant fields. This prevents all loops from coupling to the full schema and makes the snapshot incrementally buildable.

**5. Implement CoordinationLoop's Orient before committing to the interface.**
Build the multi-agent Orient as a standalone `ic coordination assess` command without reference to the `OODARLoop` interface. Once that Orient is working, the interface design across all four loops will be empirically validated. This is the strangler-fig principle applied to the interface itself.

### Recommended Hybrid Path

The brainstorm's final line suggests `/flux-drive` will synthesize a hybrid. The natural hybrid is:

- **Adopt Approach A's sequencing.** Ship steps 1-3 (shared observation layer, situation assessment schema, decision contracts) as standalone improvements with immediate value.
- **Adopt Approach B's typing discipline within clavain.** Define the internal `OODARLoop` interface in clavain (not intercore) once the SprintLoop and TurnLoop implementations are working. This preserves type safety for the two most mature loops without committing the kernel to a framework contract.
- **Treat the generic interface as a clavain-internal abstraction.** If a 5th loop level is ever needed, the interface is available. If the four implementations diverge enough to make the interface awkward, the cost of keeping it is bounded to clavain, not spread across the kernel.
- **Block on interspect layer clarification.** The shared observation layer is the highest-value first step, but it cannot be correctly designed without knowing interspect's layer affiliation.

---

## 7. Summary Table

| Issue | Severity | Approach A | Approach B | Recommendation |
|-------|----------|-----------|-----------|----------------|
| `ic situation` queries L2 interspect | Must-Fix | Unaddressed | Unaddressed | Resolve before any OODAR work |
| `OODARLoop` in intercore | Must-Fix | Not applicable | High risk | Keep in clavain-internal if used |
| Escalation contract undefined | Must-Fix | Deferred | Deferred | Design before implementation |
| Schema drift across levels | Significant | High risk | Mitigated by types | A: version snapshot schema; B: use interface |
| Async Reflect / interface mismatch | Significant | Not applicable | Interface flaw | B must use callback/channel model for async |
| Confidence threshold uniformity | Moderate | Risk | N/A | Per-loop threshold config, not shared constant |
| Gridfire migration sequence | Moderate | Aligned | Skips step 4 | A is lower-regret; B is acceptable if grounded in clavain |
| CoordinationLoop maturity | Moderate | Defer cleanly | Forces premature interface | Build multi-agent Orient before interface |
| Per-turn latency + LLM Orient | Moderate | Partial | Partial | Cache invalidation model required first |

---

## 8. File and Module References

The following files are directly relevant to this review:

- `/home/mk/projects/Demarch/core/intercore/internal/phase/machine.go` — phase state machine; the sprint loop's Act mechanism lives here
- `/home/mk/projects/Demarch/core/intercore/internal/dispatch/dispatch.go` — dispatch lifecycle; per-turn and multi-agent Act mechanisms
- `/home/mk/projects/Demarch/core/intercore/internal/lifecycle/lifecycle.go` — agent state machine; the closest existing analog to a sensor interface
- `/home/mk/projects/Demarch/core/intercore/internal/coordination/` — multi-agent lock state; the Multi-Agent Loop's Observe source
- `/home/mk/projects/Demarch/core/intercore/internal/observability/observability.go` — trace/span infrastructure; relevant to the shared observation layer's instrumentation
- `/home/mk/projects/Demarch/os/clavain/scripts/lib-routing.sh` — routing tables; the fast-path decision mechanism the OODAR Decide phase would wrap
- `/home/mk/projects/Demarch/os/clavain/scripts/dispatch.sh` — agent dispatch; the Sprint and Multi-Agent loops' Act mechanism at the OS layer
- `/home/mk/projects/Demarch/core/intercore/AGENTS.md` (lines 27-29) — kernel/OS separation contract that defines the hard L1/L2 boundary
- `/home/mk/projects/Demarch/PHILOSOPHY.md` (lines 83-91) — composition over capability; the design principle that constrains the generic interface question
- `/home/mk/projects/Demarch/docs/brainstorms/2026-02-27-gridfire-brainstorm.md` (lines 124-130) — strangler-fig migration path; Approach B skips step 4
