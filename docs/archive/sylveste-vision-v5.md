# Sylveste — Vision

**Version:** 5.0
**Date:** 2026-04-11
**Status:** Active

---

## The Pitch

The bottleneck to autonomous knowledge work isn't intelligence — it's infrastructure. But infrastructure alone is table stakes. What makes a system improve is **evidence that compounds**.

Sylveste builds the evidence infrastructure that lets AI agents earn progressively more authority: ontology to track what's known across systems, governance to gate what's allowed based on earned trust, integration to verify across system boundaries, measurement to prove what worked. Every sprint produces evidence artifacts. Evidence compounds per-subsystem. Trust advances when the evidence warrants it.

For developers and platform builders who want autonomous agencies that earn trust through receipts, not claims.

Not a coding assistant. Not an AI gateway. Not a framework for calling LLMs. A platform for autonomous agencies that do complex knowledge work with discipline, at a cost that keeps declining. Software engineering is the proving ground; the primitives generalize.

The whole thing is open source.

## Two Brands, One Architecture

Sylveste is the infrastructure. Garden Salon is the experience. Meadowsyn is the bridge.

**Sylveste** (SF register) — the durable kernel, opinionated OS, evidence-based learning loop, and plugin ecosystem that makes AI agent orchestration reliable, composable, and self-improving. For developers and platform builders. Named after Revelation Space.

**Garden Salon** (organic register) — the multiplayer workspace where humans and agents think together on shared projects in real-time. Agents are participants, not tools. The CRDT shared state is stigmergic: agents coordinate through the document, not through messages. For everyone. Named after what it is.

**Meadowsyn** (bridge) — the visualization layer that connects infrastructure to experience. Donella Meadows (systems thinking) + Cybersyn (real-time operations). The connective tissue between SF and organic registers.

The layer boundary IS the brand boundary. Infrastructure speaks SF. Experience speaks garden. The inter-\* neutral register (~64 modules) coexists with both. Garden-salon language does not appear in kernel, OS, or plugin documentation — those stay in the SF register.

## Why This Exists

LLM-based agents have a fundamental problem: nothing survives. Context windows compress. Sessions end. Networks drop. Processes crash. An agent that ran for an hour, produced three artifacts, dispatched two sub-agents, and advanced through four workflow phases leaves behind... a chat transcript. The state, the decisions, the evidence, the coordination signals: gone. Not a prompting problem. An infrastructure problem. And most agent systems today handle it with temp files, environment variables, in-memory state, and hope.

Sylveste handles it with a durable kernel (SQLite-backed Go CLI), an opinionated OS that encodes development discipline, a profiler that learns from outcomes, and a constellation of companion drivers. But the infrastructure is not the aspiration.

The bet: if you build the right infrastructure beneath agents — durable state, quality gates, evidence collection, independent measurement — they become capable of the full development lifecycle. Not just code generation, but discovery, design, review, testing, shipping, and compounding what was learned. And if you build a learning loop that measures outcomes per dollar and feeds that signal back into routing, agent selection, and gate calibration, you get a system where evidence compounds into earned trust. The system that runs the most sprints produces the most evidence. The system with the most evidence makes the best decisions. The system that makes the best decisions ships the cheapest. That's the flywheel.

## The Stack

Six pillars, organized in three layers plus cross-cutting systems. Each pillar has a clear owner, a clear boundary, and a clear survival property.

```
Layer 3: Apps (Autarch + Intercom)
├── Interactive TUI surfaces for kernel state (Autarch)
├── Bigend (monitoring), Gurgeh (PRD generation),
│   Coldwine (task orchestration), Pollard (research)
├── Multi-runtime AI assistant: Claude, Gemini, Codex (Intercom)
└── Swappable — if apps are replaced, everything beneath survives

Layer 2: OS (Clavain + Skaffen) + Drivers (Companion Plugins)
├── Clavain: opinionated workflow — phases, gates, model routing, dispatch
├── Skaffen: sovereign agent runtime — standalone Go binary, OODARC loop, multi-provider
│   (Auraken intelligence layer migrating to Go packages within Skaffen)
├── Companion plugins (~64), each wrapping one capability
├── Every driver independently installable and useful standalone
└── If the host platform changes, opinions survive; UX adapters are rewritten

Layer 1: Kernel (Intercore)
├── Host-agnostic Go CLI + SQLite WAL database
├── Runs, phases, gates, dispatches, events — the durable system of record
├── Mechanism, not policy — doesn't know what "brainstorm" means
└── If everything above disappears, the kernel and all its data survive

Cross-cutting: Evidence Infrastructure
├── Interspect (profiler): reads kernel events, proposes routing/gate changes
├── Ockham (governor): intent → weights, algedonic signals, graduated authority
├── Interweave (ontology): cross-system entity tracking, never owns data
├── Interop (integration): event-driven hub, adapters, neutral conflict resolver
├── Factory Substrate + FluxBench (measurement): outcome attribution, model qualification
└── These systems feed the flywheel — they are the preconditions for adaptive improvement
```

The survival properties are the point. Each layer can be replaced, rewritten, or removed without destroying the layers beneath it. The kernel outlives the OS. The OS outlives its host platform. The apps outlive any particular rendering choice. Practical architecture for a system that must survive the agent platform wars.

### What Each Layer Does

**The kernel (Intercore)** provides mechanism. Runs, phases, gates, dispatches, events, state, locks, sentinels. A Go CLI binary: no daemon, no server, no background process. Every `ic` invocation opens the database, does its work, and exits. The SQLite database is the system of record. The kernel says "a gate can block a transition." It doesn't say "brainstorm requires an artifact." That's policy, and policy belongs in the OS.

**The OS (Clavain + Skaffen)** provides policy. Clavain is the reference agency: which phases make up a development sprint, what conditions must be met at each gate, which model to route each agent to, when to advance automatically. It orchestrates the full lifecycle from problem discovery through shipped code, opinionated about what "good" looks like at every phase. Today it ships as a Claude Code plugin; the architecture is designed so the opinions survive even if the host platform doesn't. Skaffen is the sovereign agent runtime: a standalone Go binary with its own OODARC agent loop, multi-provider support, and TUI. The Auraken intelligence layer (lens library, style fingerprinting, profile generation) is migrating from Python into Go packages within Skaffen. Clavain and Skaffen are L2 peers — different runtimes sharing the same kernel.

**The evidence infrastructure** provides the learning loop. Five cross-cutting systems, each independently valuable but collectively forming the flywheel's input stage. Interspect reads kernel events and proposes routing changes. Ockham translates principal intent into dispatch weights and monitors for anomalies. Interweave indexes entities across systems without owning their data. Interop synchronizes state across external systems (Notion, GitHub, Google Drive) through a neutral event bus. Factory Substrate and FluxBench measure outcomes — sprint-level attribution and model-specific qualification respectively. Today, only Interspect approaches full operational maturity. The others are in early phases (see Capability Mesh below).

**The drivers (companion plugins)** provide capabilities. Multi-agent review (interflux), file coordination (interlock), ambient research (interject), token-efficient code context (tldr-swinton), agent visibility (intermux), multi-agent synthesis (intersynth), and ~58 more. Each wraps one capability and integrates with kernel primitives when present. Every driver is independently installable, usable in vanilla Claude Code without Clavain, Intercore, or any other Sylveste module. The full stack provides enhanced integration, but each driver is valuable on its own.

**The apps (Autarch, Intercom)** provide surfaces. Autarch delivers interactive TUI experiences: Bigend (monitoring), Gurgeh (PRD generation), Coldwine (task orchestration), Pollard (research intelligence). Intercom provides a multi-runtime AI assistant bridging Claude, Gemini, and Codex. The apps are a convenience layer; everything they do can be done via CLI.

## The Flywheel

The central mechanism. Evidence flows up from sprints, gets processed through the evidence infrastructure, and feeds back into decisions that make the next sprint better.

```
                                              Evidence Infrastructure
                                     ┌─────────────────────────────────────┐
Interweave (what's known) [planned] ┐│                                     │
Ockham (what's allowed) [planned] ──┤│    Interspect [operational]          │
Interop (what's verified) [planned] ┼┤──→ (correlate, propose, apply) ─────┤
Factory Substrate (attrib.) [planned]│                                     │
FluxBench (model quality) [planned] ┘│                                     │
                                     └──────────────┬──────────────────────┘
                                                    │
                                                    ▼
                                          Routing decisions
                                          Gate calibration
                                          Agent selection
                                                    │
                                                    ▼
                                          Lower cost per sprint
                                          Higher quality per sprint
                                                    │
                                                    ▼
                                          More sprints complete autonomously
                                                    │
                                                    ▼
                                          More evidence produced ──────────→ (back to top)
```

**Current state:** Today the flywheel operates on Interspect evidence alone — the v4.0 configuration. Interspect reads kernel events, correlates with human corrections and automated signals, and proposes routing overrides. This loop is operational. The v5.0 expansion adds four upstream evidence sources that are in early phases. As each source reaches operational maturity (M2+), it enriches the evidence Interspect can act on. The flywheel doesn't wait for all sources — it operates with whatever evidence is available and improves as more sources come online.

**The closing link:** increased autonomy means more sprints complete without human intervention. Each sprint produces evidence artifacts (gate outcomes, dispatch results, review findings, human corrections). Autonomy literally increases the evidence production rate.

**Balancing loops:** The flywheel is not a pure reinforcing loop. At least two balancing dynamics constrain it: (B1) the weakest-link constraint — system-level trust cannot exceed the least mature subsystem, creating a "limits to growth" archetype that prevents runaway advancement; (B2) evidence saturation — once a model or agent is well-characterized, additional evidence produces diminishing returns. These are features, not bugs. They prevent the system from over-extrapolating from thin evidence.

**Upstream dependency ordering:** The four upstream sources are not parallel; they have internal dependencies. The sequencing:

```
Phase 1 (independent):  Integration (Interop) — can operate without other evidence systems
Phase 2 (parallel):     Ontology (Interweave) + Measurement (Factory Substrate, FluxBench)
Phase 3 (convergence):  Governance (Ockham) — needs ontology and measurement as inputs
Phase 4 (adaptive):     Routing (Interspect with full evidence) — needs all upstream sources

Note: Persistence (Intercore) is the shared substrate beneath all phases, not a
      peer root. Phases 3-4 form a feedback cycle (Governance → Routing → Measurement
      → Governance) bootstrapped by manually-set initial governance policy.
```

## The Capability Mesh

How mature is each subsystem? The mesh replaces the v4.0 linear autonomy ladder (L0-L4) with a multi-dimensional view where different subsystems mature at different rates. Each subsystem is independently measurable, though not all are independently maturable — some depend on upstream subsystems reaching sufficient maturity first.

### Maturity Scale

Five levels, with observable criteria:

| Level | Name | Criteria |
|-------|------|----------|
| **M0** | Planned | Design exists (brainstorm, PRD), no implementation |
| **M1** | Built | Code shipped and tests pass, not operationally tested |
| **M2** | Operational | Running under real conditions, evidence signals yielding data for 30+ days. Example: Routing M1→M2 requires gate pass rate >70% sustained over 30 consecutive days, evaluated by Interspect, with at least 1 Tier-1 or Tier-2 signal meeting threshold. |
| **M3** | Calibrated | Evidence thresholds defined and tested, promotion/demotion criteria met |
| **M4** | Adaptive | Self-improving based on evidence, minimal human intervention needed |

System-level trust = min(maturity across M1+ mesh cells). Subsystems at M0 (not yet built) are excluded — they represent planned capabilities, not operational components. Critical-tier subsystems have stricter evidence requirements at each maturity level than Medium-tier ones. System trust is a step function: it advances when the weakest *operational* subsystem catches up. Evidence compounds per-subsystem, but system-level trust is gated on the weakest link.

### Current Mesh State

| Subsystem | Owner | Implementation | Maturity | Evidence Signal | Collection | Criticality |
|-----------|-------|---------------|----------|-----------------|------------|-------------|
| Persistence | Intercore | 8/10 epics shipped | M2 | Event integrity, query latency | Operational | High |
| Coordination | Interlock | Shipped | M2 | Conflict rate, reservation throughput | Operational | Medium |
| Discovery | Interject | Shipped, kernel-integrated | M2 | Promotion rate, source trust scores | Operational | Medium |
| Review | Interflux | Reaction round + ~589 agents | M2 | Finding precision, false positive rate | Operational | High |
| Integration | Interop | Phase 1 shipped | M1 | Conflict resolution rate, sync latency | Partial | High |
| Execution | Hassease + Codex | Brainstorm/plan phase | M0 | *Task completion rate, model utilization* | Planned | Medium |
| Ontology | Interweave | F1-F3 shipped, F5 in progress | M1 | *Query hit rate, confidence scores* | Planned | Medium |
| Measurement | Factory Substrate + FluxBench | ~80% implemented (3,515 LOC Go) | M1 | *Attribution chain completeness* | Partial | High |
| Governance | Ockham | F1-F7 shipped | M1 | *Authority events, INFORM signals* | Partial | Critical |
| Routing | Interspect | Static + complexity-aware | M2 | Gate pass rate, model cost ratio | Operational | High |

**Criticality tiers** (inspired by aviation Design Assurance Levels): subsystems with higher failure consequences require more rigorous evidence at each maturity level. Governance failure (unauthorized agent actions) is critical; Coordination failure (file lock retry) is medium. Rigor is proportional to consequence.

### Dependency DAG

Not all cells can mature independently. Known dependency chains:

```
Independent roots: Persistence, Coordination, Discovery, Review, Execution
First-order deps:  Integration → Persistence
Second-order deps: Ontology → Integration; Measurement → Persistence
Convergence:       Governance → Ontology + Measurement
                   Routing (adaptive) → Measurement + Governance
```

### Interface Evidence

Individual subsystem maturity is necessary but not sufficient. Critical cross-subsystem interfaces are monitored:

| Interface | Signal | What It Detects |
|-----------|--------|-----------------|
| Ontology / Governance | Entity identity agreement rate | Schema divergence between what's indexed and what's governed |
| Routing / Measurement | Attribution chain integrity | Broken evidence pipeline between routing decisions and outcomes |
| Integration / Ontology | Sync-to-entity success rate | Data representation mismatch at the system boundary |
| Review / Routing | Finding parse success rate | Format incompatibility between review output and routing input |
| Measurement / Governance | Evidence-to-policy latency | Feedback loop delay between observation and governance response |

The mesh is provisional. Cells may merge, split, or be added as subsystems demonstrate operational reality. The mesh reflects current understanding, not a permanent commitment.

## Trust Architecture

How trust actually works — the mechanism by which evidence compounds into earned authority.

### The Trust Lifecycle

Each subsystem moves through a 4-phase trust lifecycle:

**1. Earn.** Accumulate evidence against pre-specified thresholds. Each subsystem publishes promotion criteria: evidence type, time window, evaluating authority, and success threshold. Evidence has quality tiers:
- **Tier 1 (controlled):** FluxBench experiments, human-resolved agent disagreements. Highest weight.
- **Tier 2 (observational):** Interspect gate pass rates, Interop sync metrics, Interflux finding density. Standard weight.
- **Tier 3 (anecdotal):** Interject source promotions, ambient scanning results. Lowest weight.

Promotion requires at least one Tier-1 or Tier-2 signal meeting threshold; Tier-3 evidence alone is insufficient for maturity advancement. Per-subsystem promotion criteria specify the exact signals, windows, and thresholds required.

**2. Compound.** When evidence meets the promotion threshold, the subsystem advances one maturity level. Trust persists as long as evidence remains fresh and regression indicators are absent.

**3. Epoch.** When environmental conditions shift — a major model API change, an architecture migration, a subsystem replacement — trust is partially reset. The subsystem retains its maturity tier but must re-demonstrate at that tier under new conditions. Epochs are triggered by defined events, not by time alone. This prevents accumulated evidence from permanently inflating trust when the world beneath it has changed.

**4. Demote.** When evidence shows sustained degradation (regression indicators exceeding threshold for a defined observation window), trust drops one level. Demotion is graduated, not instant. It propagates to dependent subsystems in the dependency DAG. In-flight work continues at the lower trust level.

### Independent Verification

No subsystem self-reports its maturity. Interspect serves as the architecturally independent verification layer — it observes subsystem behavior through its own instrumentation (kernel events, gate outcomes, dispatch results), not through subsystem-reported metrics. This is the "assay office" principle: the entity that assesses quality must be structurally independent of the entity being assessed. Interspect itself is the one exception — as the assessor, its own maturity is evaluated by human attestation and controlled FluxBench experiments, not by self-assessment.

### Human Authority Reservation

Evidence thresholds are revisable by human authority regardless of accumulated evidence to the contrary. The evidence thesis earns trust for autonomous operation, but the right to redefine trust criteria remains permanently with humans. The principle (evidence earns authority) is permanent. The mechanism (specific thresholds, epoch triggers, demotion criteria) is revisable.

### Trust Transfer

When a subsystem is replaced (e.g., Auraken → Skaffen), earned trust is not automatically inherited. The replacement receives probationary access to the predecessor's maturity level with a verification period. During probation, actual behavior is compared against the inherited evidence profile. All interfaces to neighboring mesh cells are re-tested. Trust is confirmed only when the replacement demonstrates equivalent or better performance under current conditions.

## The Outcome Axes

Autonomy, quality, and token efficiency remain the measurable outcomes. They are the *results* of the evidence loop, not the framing — the flywheel produces them as byproducts of good evidence infrastructure.

**Autonomy.** How much of the development lifecycle runs without human intervention. Measured by sprint completion rate, gate pass rate on first attempt, intervention frequency. Not autonomy for its own sake — autonomy that frees the human to operate at the strategic level where their judgment matters most.

**Quality.** Defect escape rate, review signal precision, the ratio of actionable findings to false positives. Quality is the cumulative result of discipline at every phase: brainstorm rigor, plan review depth, gate enforcement, multi-perspective code review, and the learning loop that tightens all of these over time.

**Token efficiency.** Tokens per *impact*: cost per landable change, cost per actionable finding, cost per defect caught. The goal is not to spend less but to get more per dollar. Model routing is a first-class decision (Opus for reasoning, Codex for parallel implementation, Haiku for quick checks, Oracle for cross-validation). Context hygiene via strict write-behind protocol prevents the context flooding that kills long-running sprints.

### External Validation

Two independent research threads validate the core thesis from outside software engineering:

**Orchestration beats raw capability.** Symbolica AI's Arcgentica achieved 36% on ARC-AGI-3 (abstract reasoning) at $1,005 total — while raw Claude Opus 4.6 scored 0.25% at $8,900. A 340x cost-efficiency improvement from orchestrator-delegates-to-sub-agents architecture, not from a better model. The architecture is structurally isomorphic to how Clavain dispatches companion plugins. Validates PHILOSOPHY.md claim #1 (infrastructure bottleneck, not intelligence) on abstract reasoning, not just coding.

**Stigmergic coordination scales.** Research on agent coordination via shared environmental traces (stigmergy) shows 36-41% performance advantage over direct messaging at 500+ agents ([Pressure Fields and Temporal Decay, 2025](https://arxiv.org/abs/2601.08129)). Garden Salon's planned CRDT shared-state design — where agents would coordinate through the document, not through messages — is modeled on this pattern.

## Design Principles

### 1. Mechanism over policy

The kernel provides primitives. The OS provides opinions. A phase chain is a mechanism: an ordered sequence with transition rules. The decision that software development should flow through ten phases is a policy that Clavain configures at run creation time.

That separation is what makes the system extensible without modification. A documentation project uses `draft → review → publish`. A hotfix uses `triage → fix → verify`. The kernel doesn't care. New workflows don't require new kernel code.

### 2. Durable over ephemeral

If it matters, it belongs in the database. Phase transitions, gate evidence, dispatch outcomes, event history, all persisted atomically in SQLite. Temp files, environment variables, and in-memory state are not acceptable as the long-term system of record.

The cost is write latency. The benefit: any session, any agent, any process can query the true state of the system at any time. When a session crashes mid-sprint, the run state is intact and resumable.

### 3. Compose through contracts

Small, focused tools composed through explicit interfaces beat large integrated platforms. The inter-\* constellation follows Unix philosophy: each companion does one thing well. Composition works because boundaries are explicit (typed interfaces, schemas, manifests, and declarative specs rather than prompt sorcery).

The naming convention reflects this: each companion occupies the space *between* two things. interphase (between phases), interflux (between flows), interlock (between locks), interpath (between paths). They are bridges and boundary layers, not monoliths.

### 4. Independently valuable

Any capability driver works standalone. Install interflux for multi-agent review, tldr-swinton for code context, or interlock for file coordination. No Clavain, no Intercore, no rest of the stack required. Drivers degrade gracefully: they use ephemeral state alone, durable state with the kernel. The full Sylveste stack adds adaptive improvement (profiler) and opinionated workflow (OS), but these are enhancements, not prerequisites.

### 5. Human attention is the bottleneck

Agents are cheap. Human focus is scarce. The system optimizes for the human's time, not the agent's. Multi-agent output must be presented so humans can review quickly and confidently, not just cheaply.

The human drives strategy (what to build, which tradeoffs to accept, when to ship) while the agency drives execution (which model, which agents, what sequence, when to advance, what to review). The human is above the loop, not in it.

### 6. Gates enable velocity

Quality gates are not the opposite of speed — they are the mechanism that makes speed safe. The goal isn't more review; it's faster shipping with fewer regressions. If review phases slow you down more than they catch bugs, the gates are miscalibrated. Match rigor to risk. Gates with graduated authority can tighten or relax based on evidence — a subsystem that consistently passes a gate at M3 maturity earns lighter review at M4.

### 7. Self-building as proof

Every capability must survive contact with its own development process. Clavain builds Clavain. The agency runs its own sprints. A system that autonomously builds itself is a more convincing proof than any benchmark. Also the highest-fidelity eval, because it tests the full stack under real conditions with real stakes.

### 8. Evidence is independently verified

No subsystem stamps its own hallmark. Maturity assessments come from independent observation (Interspect reading kernel events), not from self-reported metrics. The entity that assesses quality must be structurally separate from the entity being assessed. Without this separation, "evidence earns trust" collapses into "claims earn trust" — and the thesis is false.

## The Development Lifecycle

Sylveste covers the full product development lifecycle through five macro-stages. Each macro-stage is a sub-agency, a team of models and agents selected for the work at hand.

### Discover

Research, brainstorming, and problem definition. Sources (arXiv, Hacker News, GitHub, Exa, Anthropic docs, RSS) are scored against a learned interest profile. High-confidence discoveries auto-create work items. Human promotions and dismissals shift the profile. Sources that consistently produce promoted discoveries earn trust.

### Design

Strategy, specification, planning, and plan review. Most agent tools skip straight to code. Sylveste makes brainstorm and strategy first-class phases with real artifacts, real gates, and real review. The plan review uses flux-drive with formalized cognitive lenses to combat AI consensus bias.

### Build

Implementation and testing. Codex handles parallel implementation. Opus and Sonnet handle complex reasoning. Haiku handles quick checks. Test-driven development is a discipline, not a suggestion; the TDD agents write failing tests first.

### Ship

Final review, deployment, and knowledge capture. The interflux fleet deploys explicit cognitive diversity lenses during final review. Code pushes are gated on human confirmation, where the scope of "confirmation" evolves with the human delegation ladder (see PHILOSOPHY.md § Earned Authority):
- **L0-L2 (current):** Per-change human confirmation before each push.
- **L3:** Human sets shipping policy (which repos, which confidence thresholds). Agent pushes when policy conditions are met.
- **L4-L5:** Human approves the policy itself; agent pushes autonomously within policy bounds.

### Reflect

Capture what was learned. Patterns discovered, mistakes caught, decisions validated, and complexity calibration data. Each macro-stage produces typed artifacts that become the next stage's input. The kernel enforces handoff via `artifact_exists` gates at macro-stage boundaries.

## North Star Metric

**What does it cost to ship a reviewed, tested change?**

The metric where all three outcome axes collapse into a single number. A low cost-per-landable-change requires autonomy (the sprint ran without babysitting), quality (the change landed without rework), and efficiency (the right models and agents were selected).

| Category | Metric | What It Measures |
|----------|--------|-----------------|
| **Efficiency** | Tokens per landable change | Total token spend for a sprint producing a merged commit |
| **Efficiency** | Agent utilization | % of dispatched agents whose output contributes to the final change |
| **Efficiency** | Model routing accuracy | % of model selections matching the outcome-optimal model |
| **Quality** | Defect escape rate | Bugs found after Ship that were present during Build |
| **Quality** | Cost per actionable finding | Token cost of findings that aren't false positives |
| **Quality** | Activation rate | % of merged subsystems with telemetry-confirmed invocation within 14 days, counted only after ≥3 distinct sessions show activation |
| **Autonomy** | Sprint completion rate | % of sprints reaching Ship without abandonment |
| **Autonomy** | Gate pass rate | % of phase transitions passing on first attempt |
| **Learning** | Self-improvement rate | Interspect proposals that improve metrics when applied |
| **Trust** | Maturity advancement rate | Mesh cells advancing to the next maturity level per quarter |

**Goodhart caveat:** Any stable metric becomes a target, and any target becomes gamed. Rotate emphasis, diversify evaluation dimensions, and watch for agents optimizing the metric at the expense of actual quality. (See PHILOSOPHY.md § Receipts Close Loops, Measurement.)

**Activation-rate baseline.** Passive v1 measures whether a merged subsystem is actually invoked within 14 days by combining existing telemetry-adjacent receipts — CASS traces, git history, closeout artifacts, and route/phase evidence — before explicit subsystem-event emits are required. A subsystem counts as activated only when evidence spans at least three distinct sessions. The first three weeks are baseline observation and report-only: findings should produce follow-up beads or patches, not hard gates. Any v2 soft-block must wait for explicit calibration approval and a documented Goodhart review. Because the Phase 0 spike recorded `passive_spike_recall:3/3` and `next_phase:passive-v1`, explicit emit infrastructure remains deferred until passive reporting misses a confirmed activation gap.

The cost-per-landable-change baseline was established on 2026-02-28 at $1.17 (Opus 95% of cost). As of 2026-03-18, the figure is $2.93 — the increase reflects expanded review scope (multi-agent review, reaction rounds) rather than efficiency regression. The trajectory is expected to improve as model routing matures.

## Audience

Two brands serve two audiences through shared infrastructure:

**Sylveste** (infrastructure) — for developers and platform builders who want to build autonomous agencies. Intercore is the kernel. Clavain is the reference agency. Open source from launch.

**Garden Salon** (experience) — for anyone who wants to think with AI agents on shared projects. Agents are participants in the workspace, not tools invoked from a sidebar. The CRDT substrate means agents coordinate through the document itself.

Three concentric circles, in priority order:

1. **Platform.** Open Intercore as infrastructure for anyone building autonomous agencies. Open Clavain as the reference agency. Software development is the first vertical; the primitives are domain-general.

2. **Proof by demonstration.** Build the system with the system. Every capability must survive contact with its own development process. The autonomous epic execution track (rsj.1) is the latest proof: the system sequences its own multi-feature work.

3. **Personal rig.** One product-minded engineer, as effective as a full team. The personal rig is both the daily driver and the proving ground for the platform.

## Open Source Strategy

Everything is open source. All pillars: the kernel (Intercore), the OS (Clavain), the sovereign runtime (Skaffen), the companion plugins (Interverse), the TUI tools (Autarch), the profiler (Interspect), and the evidence infrastructure (Ockham, Interweave, Interop).

The bet is on ecosystem effects. If the kernel is good enough, people will build their own agencies on top of it. If the reference agency is good enough, people will write their own companions. The learning loop (Interspect) benefits from a larger evidence base.

Revenue, when it matters, comes from managed hosting, enterprise support, and premium companions. Not from restricting access to the core infrastructure.

## Where We Are

As of April 2026 (1,456 beads tracked, 1,239 closed):

- **Kernel:** 8 of 10 epics shipped (E1-E8). Runs, phases, gates, dispatches, events, discovery pipeline, rollback, portfolio orchestration, TOCTOU prevention, cost-aware scheduling, sandbox specs, durable session attribution. Remaining: E9 (Autarch Phase 2) and E10 (Sandboxing).
- **OS:** Full sprint lifecycle (brainstorm → ship) is kernel-driven. 17 skills, adaptive single-entry workflow (`/route → /sprint → /work`).
- **Autonomous epic execution:** `/campaign` orchestrates epic-level build sequences — topological sort by dependency graph, phase-gated dispatch, resume-aware checkpointing, strategic contradiction escalation, decomposition quality calibration.
- **Evidence infrastructure:** Ockham F1-F7 shipped (intent scoring, connector protocol, check hook, INFORM signals, health bypass). Interweave F1-F3 shipped, F5 in progress (type families, identity crosswalk, connector protocol, named queries). Interop Phase 1 shipped (event hub, adapter interface, conflict resolver). Factory Substrate ~80% implemented (3,515 LOC Go, 518 tests). FluxBench at brainstorm/plan phase.
- **Model routing:** Static routing, complexity-aware routing (C1-C5), and routing override chain (F1-F5) shipped. Evidence quarantine (48h delay before influencing routing) shipped. Adaptive routing (B3) is next — blocked on measurement hardening.
- **Review engine:** ~589 review agents (12 specialized + generated fleet), deployed through interflux with multi-agent synthesis, reaction rounds, and cross-model dispatch.
- **Ecosystem:** 64 companion plugins, 81 total modules. Each independently installable.
- **Apps:** Autarch TUI (Bigend, Gurgeh, Coldwine, Pollard). Intercom multi-runtime assistant bridging Claude, Gemini, and Codex.
- **Intelligence replatforming:** Auraken Python → Skaffen Go migration in progress. Hassease (multi-model execution daemon) at brainstorm/plan phase.
- **Self-building:** 1,456 beads tracked, 1,239 closed. The system has been building itself continuously since January 2026.

## What's Next

Six active themes, in priority order:

1. **Integration fabric** (Interop) — P0. Event-driven hub replacing fragmented sync. Bidirectional Beads ↔ GitHub, Notion ↔ Beads, neutral conflict resolution. The foundation that Ontology and Governance depend on.
2. **Factory governance** (Ockham) — P0. Intent → dispatch weight offsets, algedonic signals (weight-drift detection, first-attempt pass rate trends), graduated authority with demotion. Wave 1 F1-F7 shipped; Wave 2 (anomaly detection, quality subsystem) next.
3. **Intelligence replatforming** (Auraken → Skaffen + Hassease) — P0. Go packages (lens library, fingerprinting, extraction, profile generation) integrated into Skaffen. Hassease routes ~80% to GLM/Qwen, escalates planning and review to Claude.
4. **Generative ontology** (Interweave) — P1. Finding-aid for entities across 6+ subsystems. Five type families, identity crosswalk, named query templates. Permanent constraint: the finding-aid test — delete Interweave and everything still works.
5. **Model qualification** (FluxBench) — P1. Closed-loop discovery for interflux. Custom benchmarks for domain-specific agent prompts, 8 scores per model to AgMoDB. Drift detection and proactive model surfacing.
6. **Evidence pipeline closure** (Interspect Phase 2) — P1. Evidence-driven agent selection, canary monitoring, counterfactual shadow evaluation. The flywheel's missing link. Depends on Measurement reaching M2.

## Horizons

Future commitments with explicit dependencies. Not "What's Next" — these require current infrastructure to mature first.

- **Garden Salon MVP** — Multiplayer workspace with CRDT shared state, stigmergic agent participation. The experience brand. Depends on: Interop M2, Interweave M2, Ockham M2.
- **Domain-general north star** — "Cost per landable change" is software-dev-specific. The platform needs a domain-general metric. Depends on: Measurement M3.
- **Cross-project federation** — Portable developer identity and learnings across projects. Depends on: Interweave M3, Interop M3.
- **L4 auto-ship** — The system merges and deploys when confidence thresholds are met. Depends on: Governance M3, Routing M3.

## What This Is Not

- **Not a general AI gateway.** It doesn't route arbitrary messages to arbitrary agents. The platform orchestrates complex knowledge work through discipline and evidence. Software development is the first vertical; the primitives are domain-general.
- **Not a coding assistant.** It doesn't help you write code; it *builds software*. The coding is one phase of five.
- **Not a no-code tool.** It's for people who build software with agents.
- **Not uncontrollably self-modifying.** Interspect modifies OS-level configuration through safe, reversible overlays. The kernel boundary softens as trust is earned — through gated, evidence-based processes with independent verification, not direct modification. (See PHILOSOPHY.md § Earned Authority.)
- **Not just an agency.** Sylveste is the platform; Clavain is the reference agency built on it. The kernel and drivers are infrastructure anyone can use to build their own agency.

## Origins

Sylveste (from Alastair Reynolds' Democratic Anarchists, reflecting the continuous polling and consensus-driven architecture of the system). Clavain is a protagonist from the same series. The inter-\* naming convention describes what each component does: the space *between* things. Interverse is the universe that contains them all.

The project began by merging [superpowers](https://github.com/obra/superpowers), [superpowers-lab](https://github.com/obra/superpowers-lab), [superpowers-developing-for-claude-code](https://github.com/obra/superpowers-developing-for-claude-code), and [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin). It has since grown into an autonomous software development agency platform with 81 modules across six pillars.

---

*Module inventory, model routing stages, and adoption ladder: [sylveste-reference.md](./sylveste-reference.md). Layer-specific vision docs: [Intercore](../core/intercore/docs/intercore-roadmap.md) (kernel), [Clavain](../os/Clavain/docs/clavain-vision.md) (OS), [Skaffen](../os/Skaffen/PHILOSOPHY.md) (sovereign runtime), [Autarch](../apps/Autarch/docs/autarch-vision.md) (apps), [Interspect](./interspect-vision.md) (profiler, [roadmap](./interspect-roadmap.md)).*
