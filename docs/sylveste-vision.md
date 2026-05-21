# Sylveste — Vision

**Version:** 6.0
**Date:** 2026-05-06
**Status:** Active
**Predecessor:** [v5.0 archive](./archive/sylveste-vision-v5.md)

---

## The Pitch

The bottleneck to autonomous knowledge work isn't intelligence — it's
infrastructure. But infrastructure alone is table stakes. What makes a system
improve is **evidence that compounds**.

Sylveste builds the evidence infrastructure that lets AI agents earn progressively
more authority: ontology to track what's known across systems, governance to gate
what's allowed based on earned trust, integration to verify across system
boundaries, measurement to prove what worked. Every sprint produces evidence
artifacts. Evidence compounds per-subsystem. Trust advances when the evidence
warrants it, and falls when it doesn't.

The heart of Sylveste, the daily-driver capability that defines what the system
*is*, is the **kernel-driven sprint lifecycle**: every meaningful unit of work —
brainstorm, plan, build, ship, reflect, research — passes through phases the
kernel records, gates the kernel enforces, and dispatches the kernel attributes,
cycle after cycle. Remove that, and Sylveste becomes a fleet of plugins. Keep
it, and the fleet earns its authority through the receipts that lifecycle
produces.

For developers and platform builders who want autonomous agencies that earn trust
through receipts, not claims.

Not a coding assistant. Not an AI gateway. Not a framework for calling LLMs. A
platform for autonomous agencies that do complex knowledge work with discipline,
at a cost that keeps declining. Software engineering is the proving ground; the
primitives generalize.

The whole thing is open source.

### From v5 to v6

v4 told the routing-via-Interspect story: one evidence source proposing
configuration changes the kernel could safely apply. v5 expanded the picture to
five evidence sources (Interspect, Interweave, Interop, Factory Substrate,
FluxBench) and named the trust lifecycle that ties them together. v6 hardens the
contract: it bounds the demotion latency v5 left open, parameterizes the tier
weights v5 named qualitatively, replaces the assertion of substrate independence
with an honest debt registry, and inserts a Break stage between Compound and
Epoch so a confident pillar must surface its own contradictions before it
advances. The thesis is unchanged. The mechanism is now specified well enough to
audit.

## Two Brands, One Architecture

Sylveste is the infrastructure. Garden Salon is the experience. Meadowsyn is the
bridge.

**Sylveste** (SF register) — the durable kernel, opinionated OS, evidence-based
learning loop, and plugin ecosystem that makes AI agent orchestration reliable,
composable, and self-improving. For developers and platform builders. Named
after Revelation Space.

**Garden Salon** (organic register) — the multiplayer workspace where humans and
agents think together on shared projects in real-time. Agents are participants,
not tools. The CRDT shared state is stigmergic: agents coordinate through the
document, not through messages. For everyone. Named after what it is.

**Meadowsyn** (bridge) — the visualization layer that connects infrastructure to
experience. Donella Meadows (systems thinking) + Cybersyn (real-time operations).
The connective tissue between SF and organic registers.

The layer boundary IS the brand boundary. Infrastructure speaks SF. Experience
speaks garden. The inter-\* neutral register (~64 modules) coexists with both.
Garden-salon language does not appear in kernel, OS, or plugin documentation —
those stay in the SF register.

## Why This Exists

LLM-based agents have a fundamental problem: nothing survives. Context windows
compress. Sessions end. Networks drop. Processes crash. An agent that ran for an
hour, produced three artifacts, dispatched two sub-agents, and advanced through
four workflow phases leaves behind a chat transcript. The state, the decisions,
the evidence, the coordination signals: gone. Not a prompting problem. An
infrastructure problem. And most agent systems today handle it with temp files,
environment variables, in-memory state, and hope.

Sylveste handles it with a durable kernel (SQLite-backed Go CLI), an opinionated
OS that encodes development discipline, a profiler that learns from outcomes, and
a constellation of companion drivers. But the infrastructure is not the
aspiration.

The bet: if you build the right infrastructure beneath agents — durable state,
quality gates, evidence collection, independent measurement — they become
capable of the full development lifecycle. Not just code generation, but
discovery, design, review, testing, shipping, and compounding what was learned.
And if you build a learning loop that measures outcomes per dollar and feeds
that signal back into routing, agent selection, and gate calibration, you get a
system where evidence compounds into earned trust. The system that runs the most
sprints produces the most evidence. The system with the most evidence makes the
best decisions. The system that makes the best decisions ships the cheapest.
That's the flywheel.

## The Stack

Six pillars, organized in three layers plus cross-cutting systems. Each pillar
has a clear owner, a clear boundary, and a clear survival property.

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

The survival properties are the point. Each layer can be replaced, rewritten, or
removed without destroying the layers beneath it. The kernel outlives the OS.
The OS outlives its host platform. The apps outlive any particular rendering
choice. Practical architecture for a system that must survive the agent platform
wars.

### What Each Layer Does

**The kernel (Intercore)** provides mechanism. Runs, phases, gates, dispatches,
events, state, locks, sentinels. A Go CLI binary: no daemon, no server, no
background process. Every `ic` invocation opens the database, does its work, and
exits. The SQLite database is the system of record. The kernel says "a gate can
block a transition." It doesn't say "brainstorm requires an artifact." That's
policy, and policy belongs in the OS.

**The OS (Clavain + Skaffen)** provides policy. Clavain is the reference agency:
which phases make up a development sprint, what conditions must be met at each
gate, which model to route each agent to, when to advance automatically. It
orchestrates the full lifecycle from problem discovery through shipped code,
opinionated about what "good" looks like at every phase. Today it ships as a
Claude Code plugin; the architecture is designed so the opinions survive even if
the host platform doesn't. Skaffen is the sovereign agent runtime: a standalone
Go binary with its own OODARC agent loop, multi-provider support, and TUI. The
Auraken intelligence layer (lens library, style fingerprinting, profile
generation) is migrating from Python into Go packages within Skaffen. Clavain
and Skaffen are L2 peers — different runtimes sharing the same kernel.

**The evidence infrastructure** provides the learning loop. Five cross-cutting
systems, each independently valuable but collectively forming the flywheel's
input stage. Interspect reads kernel events and proposes routing changes. Ockham
translates principal intent into dispatch weights and monitors for anomalies.
Interweave indexes entities across systems without owning their data. Interop
synchronizes state across external systems (Notion, GitHub, Google Drive)
through a neutral event bus. Factory Substrate and FluxBench measure outcomes —
sprint-level attribution and model-specific qualification respectively. Today,
only Interspect approaches full operational maturity. The others are in early
phases (see Capability Mesh below).

**The drivers (companion plugins)** provide capabilities. Multi-agent review
(interflux), file coordination (interlock), ambient research (interject),
token-efficient code context (tldr-swinton), agent visibility (intermux),
multi-agent synthesis (intersynth), and ~58 more. Each wraps one capability and
integrates with kernel primitives when present. Every driver is independently
installable, usable in vanilla Claude Code without Clavain, Intercore, or any
other Sylveste module. The full stack provides enhanced integration, but each
driver is valuable on its own.

**The apps (Autarch, Intercom)** provide surfaces. Autarch delivers interactive
TUI experiences: Bigend (monitoring), Gurgeh (PRD generation), Coldwine (task
orchestration), Pollard (research intelligence). Intercom provides a
multi-runtime AI assistant bridging Claude, Gemini, and Codex. The apps are a
convenience layer; everything they do can be done via CLI.

### Substrate Dependency Map

The five evidence sources plus Ockham each consume kernel state. v5 asserted
"architectural independence" for Interspect; that claim was overdrawn. The
honest picture is a substrate-dependency table — and the implications run
through §7.6.

| Source | Write path | Read path | Substrate independence | Debt |
|---|---|---|---|---|
| Interspect | Intercore SQLite | Intercore events | Logically separated namespace, physically shared substrate | Cannot detect kernel-level event loss |
| Interweave | Intercore SQLite (entity tables) | Cross-source via Interop | Shared substrate | Same as Interspect |
| Interop | External adapter targets + Intercore event hub | Adapter targets | Partially independent (external systems are substrate-independent of kernel) | Reconciliation logic still runs in-kernel |
| Factory Substrate | Intercore SQLite (attribution) | Intercore events | Shared substrate | Same as Interspect |
| FluxBench | Independent harness DB | Independent | Substrate-independent (separate process, separate store) | Currently M0; potential is unrealized |
| Ockham | Intercore SQLite | Intercore events | Shared substrate | Same as Interspect |

FluxBench is the only source whose substrate is genuinely separate today, and
FluxBench is M0. Until FluxBench reaches M2, every operational evidence source
shares one substrate. §7.6 captures this as a known structural debt rather than
hiding it.

## The Flywheel

The central mechanism. Evidence flows up from sprints, gets processed through
the evidence infrastructure, and feeds back into decisions that make the next
sprint better.

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

**Current state:** Today the flywheel operates on Interspect evidence alone —
the v4.0 configuration. Interspect reads kernel events, correlates with human
corrections and automated signals, and proposes routing overrides. This loop is
operational. The v5.0 expansion added four upstream evidence sources, all in
early phases. The v6.0 contract: each new source operates in shadow mode (signals
collected, decisions not influenced) for a calibration window before it goes
active, with promotion gated on demonstrated independence from existing sources.
The flywheel doesn't wait for all sources, but it doesn't promote on phase-aligned
noise either.

**The closing link:** increased autonomy means more sprints complete without
human intervention. Each sprint produces evidence artifacts (gate outcomes,
dispatch results, review findings, human corrections). Autonomy literally
increases the evidence production rate.

**Balancing loops.** The flywheel is not a pure reinforcing loop. Two balancing
dynamics constrain it: (B1) the weakest-link constraint — system-level trust
cannot exceed the least mature critical subsystem, creating a "limits to growth"
archetype that prevents runaway advancement; (B2) evidence saturation — once a
model or agent is well-characterized, additional evidence produces diminishing
returns. Both are parameterized: B1 uses a criticality-weighted aggregation
(see §6) so a non-critical M1 doesn't drag a critical M3 system down. B2 uses
per-tier saturation curves so the dampening is observable and tunable rather
than implicit.

### Phase 3-4 Bootstrap Procedure

The four upstream sources have internal dependencies. The sequencing:

```
Phase 1 (independent):  Integration (Interop) — can operate without other evidence systems
Phase 2 (parallel):     Ontology (Interweave) + Measurement (Factory Substrate, FluxBench)
                        — both consume Interop's outputs once Interop reaches M2
Phase 3 (convergence):  Governance (Ockham) — needs Ontology and Measurement as inputs
Phase 4 (adaptive):     Routing (Interspect with full evidence) — needs all upstream

Note: Persistence (Intercore) is the shared substrate beneath all phases.
```

Phases 3-4 form a feedback cycle (Governance → Routing → Measurement →
Governance). It cannot bootstrap from itself. The bootstrap procedure:

1. **Initial governance policy** lives in `core/intercore/config/initial-governance.yaml`,
   shipped with the kernel. It encodes the conservative defaults: every routing
   override requires explicit operator approval, every gate runs at full rigor,
   no auto-shipping above L2.
2. **Transition criterion.** Initial policy gives way to evidence-derived policy
   only when (a) Measurement reaches M2, (b) Governance has recorded ≥100 policy
   decisions whose outcomes are observable in the evidence pipeline, and (c) the
   evidence agrees with initial policy on ≥90% of those decisions. The 90%
   agreement threshold prevents the loop from booting on a policy that already
   diverges from observed reality.
3. **Rollback path.** If evidence-derived policy produces a sustained regression
   (defined per §7.4 demotion bounds), the kernel reverts to initial policy, logs
   the rollback as a hallmark event (§7.8), and freezes evidence-derived
   advancement until the regression is investigated.

### Loop Self-Influence

Interspect proposes changes to a system Interspect observes. Without
acknowledgment, the loop appears to converge when it is actually drifting along
its own influence. v6 requires every Interspect proposal to record a
counterfactual estimate — what the metric would be without the proposal — and
that counterfactual is tracked alongside the post-proposal value. When the gap
between counterfactual and observed widens beyond a threshold, the proposal is
flagged for human review even if the observed metric improved.

### Sprint-as-Evidence Quality Filter

Not every sprint produces equal evidence. A sprint that reaches Ship contributes
as Tier-2 observational evidence; an aborted or abandoned sprint contributes
only as Tier-3 anecdotal and only when accompanied by a closeout note explaining
why it aborted. This prevents the loop from reinforcing on noise — a half-built
sprint that exposed a gate calibration problem is more valuable than a clean
sprint that ran on auto-pilot, but neither carries the same weight as a Ship.

## The Capability Mesh

How mature is each subsystem? The mesh replaces the v4.0 linear autonomy ladder
(L0-L4) with a multi-dimensional view where different subsystems mature at
different rates. Each subsystem is independently measurable, though not all are
independently maturable — some depend on upstream subsystems reaching sufficient
maturity first.

### Maturity Scale

Five levels, with observable criteria:

| Level | Name | Criteria |
|-------|------|----------|
| **M0** | Planned | Design exists (brainstorm, PRD), no implementation |
| **M1** | Built | Code shipped and tests pass, not operationally tested |
| **M2** | Operational | Running under real conditions, evidence signals yielding data for 30+ days. Example: Routing M1→M2 requires gate pass rate >70% sustained over 30 consecutive days, evaluated by Interspect, with at least 1 Tier-1 or Tier-2 signal meeting threshold. |
| **M3** | Calibrated | Evidence thresholds defined and tested, promotion criteria met, **demotion procedure exercised end-to-end on FluxBench substrate** (§7.5) |
| **M4** | Adaptive | Self-improving based on evidence, minimal human intervention needed |

**System-level trust** = criticality-weighted percentile of operational mesh
cells. v5 used `min(maturity)`; that formula created a perverse incentive to
keep work in M0 to avoid dragging the floor down. v6 replaces `min` with a
weighted percentile: criticality-weighted across cells, with the percentile
chosen so a single non-critical M1 cannot cap a critical M3 system. The exact
weights and percentile are specified in the §6 child bead [pending] that
implements the formula change.

System trust still advances stepwise — incremental evidence in a single cell
does not move the system trust value — but advancement no longer requires the
weakest cell catch up before any cross-system progress shows. Per-cell trust
remains the operational signal for tuning; system trust remains the published
headline.

### Shadow / Apprenticeship Requirement

A new evidence source does not influence decisions on the day it reaches M2. It
operates in shadow: signals collected, written to the kernel, available for
analysis, *not* fed into routing or gate calibration. Promotion from
shadow-M2 to active-M2 requires demonstrated agreement with established sources
on a calibration set, evaluated over an explicit window. The window length
varies by source criticality (see §7.4 for the analogous demotion bounds). This
prevents two newly-online sources from phase-aligning with the existing
Interspect signal in their first weeks of operation and producing a "bore" that
the system promotes as cross-source convergence.

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

**Criticality tiers** (inspired by aviation Design Assurance Levels): subsystems
with higher failure consequences require more rigorous evidence at each
maturity level. Governance failure (unauthorized agent actions) is critical;
Coordination failure (file lock retry) is medium. Rigor is proportional to
consequence.

### Per-Subsystem Promotion Criteria

v5 specified concrete promotion criteria for Routing only. v6 commits to
publishing per-subsystem criteria for Persistence, Coordination, Discovery,
Review, Integration, Ontology, Measurement, and Governance, each as a child
bead under sylveste-mj11. Each criterion specifies: the M-tier transition, the
evidence signals required, the time window, the evaluating authority, the
threshold value, and the demotion-rehearsal expectation at M3+. Until those
criteria publish, advancement of any cell beyond Routing requires explicit
human approval rather than evidence-derived promotion.

### Dependency DAG

Not all cells can mature independently:

```
Independent roots: Persistence, Coordination, Discovery, Review, Execution
First-order deps:  Integration → Persistence
Second-order deps: Ontology → Integration; Measurement → Persistence
Convergence:       Governance → Ontology + Measurement
                   Routing (adaptive) → Measurement + Governance
```

### Interface Evidence

Individual subsystem maturity is necessary but not sufficient. Critical
cross-subsystem interfaces are monitored:

| Interface | Signal | What It Detects |
|-----------|--------|-----------------|
| Ontology / Governance | Entity identity agreement rate | Schema divergence between what's indexed and what's governed |
| Routing / Measurement | Attribution chain integrity | Broken evidence pipeline between routing decisions and outcomes |
| Integration / Ontology | Sync-to-entity success rate | Data representation mismatch at the system boundary |
| Review / Routing | Finding parse success rate | Format incompatibility between review output and routing input |
| Measurement / Governance | Evidence-to-policy latency | Feedback loop delay between observation and governance response |

The mesh is provisional. Cells may merge, split, or be added as subsystems
demonstrate operational reality. The mesh reflects current understanding, not a
permanent commitment.

## Trust Architecture

How trust actually works — the mechanism by which evidence compounds into
earned authority.

### The Trust Lifecycle

Each subsystem moves through a five-phase trust lifecycle:

**1. Earn.** Accumulate evidence against pre-specified thresholds. Each
subsystem publishes promotion criteria: evidence type, time window, evaluating
authority, success threshold. Evidence has quality tiers:
- **Tier 1 (controlled):** FluxBench experiments, human-resolved agent
  disagreements. Highest weight.
- **Tier 2 (observational):** Interspect gate pass rates, Interop sync metrics,
  Interflux finding density. Standard weight.
- **Tier 3 (anecdotal):** Interject source promotions, ambient scanning results.
  Lowest weight.

Promotion requires at least one Tier-1 or Tier-2 signal meeting threshold;
Tier-3 evidence alone is insufficient for maturity advancement. Per-subsystem
promotion criteria specify the exact signals, windows, and thresholds.

**2. Compound.** When evidence meets the promotion threshold, the subsystem
advances one maturity level. Trust persists as long as evidence remains fresh
(per §7.3 decay model) and regression indicators are absent.

**3. Break.** Between Compound and Epoch, the subsystem must operate a
continuous self-observation practice that surfaces evidence contradicting its
own promotion case. Continuous practice is constitutive; the gate at
Compound→Epoch ratifies it but cannot constitute it. Each Break receipt
references the specific Compound-window event it contradicts (sprint, gate
pass, transition) and is filed within that event's window — receipts batched
at boundary without event association carry retrospective weight only.
Receipts are scored for severity by an Interspect instance whose
substrate-independence and longitudinal observational history with the
subsystem are pre-declared (per **sylveste-mj11.3**); receipts above a
severity floor receive a second independent assessment. Promotion criteria
publish a Break invariant tuple — count floor, rolling window, max quiet gap,
baseline rate, lower control limit, required contradiction-axes with per-axis
floors, regime-coverage requirement across high-load and low-load sprint
cycles, Goodhart coverage floor against Interspect-surfaced held-out
contradictions, and zero-receipt-floor escalation ladder (per
**sylveste-mj11.4**). Mid-Compound excursions below LCL, quiet gaps exceeding
max, axis-concentration above Bauschinger-positive threshold, and zero-receipt
sub-periods fire as Tier-2 regression signals (§7.4) at time of violation,
not at boundary. Epoch entry requires the count floor met across the
axis-covering set with no chain-of-custody gaps; the gate ratifies the
standing trace of sealed periodic Break formalizations within the window
(per **sylveste-mj11.5**), not a raw receipt stream. The Break phase is
borrowed from the jo-ha-kyū rhythm of Noh theatre: the climax is legitimate
only if the slow build is interrupted by an honest break. Without Break,
confident subsystems accumulate compounding evidence in only their own
favor — the counterfeit kyū. With Break, a subsystem whose self-observation
rate departs from its calibrated baseline beyond the invariant's tolerance
is investigated, not assumed degraded; silence is potential blindness, not
definitional blindness, and dormancy is distinguished from degradation by
the continuous record (per **sylveste-mj11.6**). Substrate-changing Epoch
triggers reset the Break baseline; prior receipts brief the new corridor but
do not authorize it.

**4. Epoch.** When environmental conditions shift — a major model API change,
an architecture migration, a subsystem replacement — trust is partially reset.
The subsystem retains its maturity tier but must re-demonstrate at that tier
under new conditions. Epochs are triggered by defined events, not by time
alone (see §7.11 for the rubric). This prevents accumulated evidence from
permanently inflating trust when the world beneath it has changed.

**5. Demote.** When evidence shows sustained degradation (regression indicators
exceeding threshold for the per-tier observation window in §7.4), trust drops
one level. Demotion propagates to dependent subsystems per §7.9. In-flight work
continues at the lower trust level and the demotion is hallmarked (§7.8).

**Hysteresis.** Promotion and demotion thresholds are separated by a band: a
subsystem that just demoted M3→M2 cannot re-promote on the same evidence window
that triggered demotion. Without a band, the system thrashes; with one, it
converges.

### §7.2 Tier-Weight Aggregation

v5 named Tier 1 / 2 / 3 weights qualitatively. v6 commits the defaults inline
so two operators evaluating the same evidence corpus compute identical
maturity scores; **sylveste-mj11.2** holds the per-subsystem calibration
overrides where the defaults are too loose or too strict.

**Default weights** (used when a subsystem's promotion criteria do not
specify otherwise): Tier 1 (controlled) = 1.0; Tier 2 (observational) = 0.3;
Tier 3 (anecdotal) = 0.05.

**Aggregation function: gated-AND with veto.** Promotion to the next maturity
level requires every gate condition in the subsystem's promotion criteria to
pass. Conditions are typically per-tier signals plus the Break invariant
tuple from §7.1. Conditions are conjunctive, not weighted-mean — passing
nine of ten gates is not a pass. This aligns with the Break-phase structure:
count floors, axis-covering sets, and chain-of-custody requirements are all
gated-AND in form, and §7.2 following the same shape keeps the lifecycle's
evidence logic uniform.

**Conflict resolution.** When tiers disagree, the higher-tier signal is
decisive. A Tier-1 controlled-experiment failure vetoes promotion regardless
of Tier-2 volume. A Tier-2 fail can be outweighed by a Tier-1 pass on the
same dimension, but a Tier-3 signal cannot override either Tier-1 or Tier-2.
The asymmetry reflects evidence quality: a controlled experiment that shows
degradation is a stronger signal than any number of observational passes
against an unmeasured confound.

**Reproducibility requirement.** The aggregation function and weights are
deterministic. Per-subsystem overrides in mj11.2 must be published as
hallmark events (§7.8) before they take effect. Without reproducibility,
"evidence earns trust" reduces to "whoever computes the score earns
authority."

### §7.3 Evidence Decay Model

Trust persists as long as evidence remains fresh. v6 quantifies fresh:

| Tier | Freshness window | Decay function |
|---|---|---|
| Tier 1 (controlled) | 90 days | linear decay over the window |
| Tier 2 (observational) | 30 days | linear decay over the window |
| Tier 3 (anecdotal) | 7 days | linear decay over the window |

When an evidence record ages past its window, it is preserved (never
deleted — the hallmark log at §7.8 retains the original record permanently)
but its weight in current maturity computation drops to zero. The continuous
record stays available for forensic reconstruction; only its evidential
authority decays.

Decay couples to two adjacent mechanisms. **Epoch triggers (§7.11)** fire a
partial reset that ages out evidence collected under the prior environmental
conditions regardless of decay window. **The §7.1 Break invariant** carries
its own time scales (`rolling_window`, `max_quiet_gap`) that operate within
the §7.3 window for the receipt's tier — a Break receipt is Tier-2 by
default and ages on the 30-day linear curve, but the Break invariant tuple
in mj11.4 can declare a per-subsystem override. When §7.1 and §7.3 disagree
on whether evidence is current, the more conservative window wins.

Without decay, evidence accumulates monotonically and trust ratchets up
regardless of operational reality.

### §7.4 Demotion Latency Bounds

v5 said "demotion is graduated, not instant" without bounding the latency. A
subsystem emitting bad routing decisions had an unspecified observation window
to do damage. v6 bounds the latency per criticality tier:

| Criticality | Maximum demotion observation window | Clock starts |
|---|---|---|
| Critical (Governance) | 4 hours | At first regression indicator above threshold |
| High (Routing, Persistence, Review, Integration, Measurement) | 24 hours | At first regression indicator above threshold |
| Medium (Coordination, Discovery, Ontology, Execution) | 7 days | At first regression indicator above threshold |

A regression indicator that exceeds an emergency-rate threshold (defined
per-subsystem alongside promotion criteria) triggers immediate demotion rather
than waiting out the window. Slower drifts use the full window. Demotion
windows are upper bounds; the system can demote faster when evidence warrants.

### §7.5 Demotion-Rehearsal as M3+ Precondition

Trust is granted only to elements whose removal procedure has been demonstrated.
A subsystem cannot promote to M3 unless its demotion procedure has been
exercised end-to-end on FluxBench substrate (or an equivalent isolated harness),
with the system observed to remain functional during the simulated demotion.
The pattern is borrowed from Gothic masonry: a vault is not declared complete
until centering is removed and re-installed cleanly — the removal exercises the
load path. A subsystem at M3+ that has never had its demotion exercised is a
keystone on uncured mortar.

### §7.6 Substrate Independence Stance

The Goldsmiths' Company assayed silver in a building separate from the
goldsmiths' workshops. Sylveste's evidence sources currently do not. Interspect,
Interweave, Factory Substrate, and Ockham all read the same Intercore SQLite
substrate; an event the kernel fails to write is invisible to every "independent"
source simultaneously. v5 asserted "architectural independence." v6 acknowledges
the asserter and the asserted run in the same process tree on the same substrate,
and treats this as known structural debt rather than hiding it.

The position v6 commits to:

1. **FluxBench is the only substrate-independent source** today. Its harness
   runs in a separate process with a separate store. FluxBench is M0 and
   reaching M2 is a §15 priority.
2. **Until FluxBench reaches M2**, every operational evidence source carries
   a substrate-shared discount: findings from a source about the substrate it
   shares are weighted lower than findings about substrates other than its own.
   The discount factor lives in the §7.2 aggregation specification.
3. **The load-path audit** (one-time, child bead under mj11) traces every
   evidence-emission path to an unconditionally-trusted floor and records
   single-path loads as defects. The audit produces a load-path diagram
   published alongside this vision document.
4. **Periodic external replay.** While full third-party verification is
   deferred to post-Mythos, v6 commits to a quarterly replay: a sample of
   recent maturity decisions is re-derived from raw evidence using a frozen
   kernel snapshot in an isolated environment, and divergences are flagged.

The doctrine is unchanged: evidence is independently verified. The mechanism
is honest: today, "independent" means logically separated; tomorrow,
substrate-separated; verification by external replay covers the gap.

### §7.7 Trust Transfer Protocol

When a subsystem is replaced (Auraken → Skaffen, Auraken → Hermes Agent), trust
is not automatically inherited. The replacement receives probationary access to
the predecessor's maturity level, with concrete bounds:

- **Probation duration.** 30 calendar days *and* ≥5 sprint completions whose
  outcomes touch the replaced subsystem.
- **Equivalence threshold.** Performance on the predecessor's evidence profile
  within ±10% on the headline metric for the subsystem (gate pass rate,
  attribution completeness, etc.). Better counts; within-tolerance counts;
  worse than tolerance fails probation.
- **All interfaces re-tested.** Every cross-subsystem signal in §6 that
  involves the replaced subsystem must produce a passing reading during the
  probation window.
- **Rollback.** Probation failure restores the predecessor to its prior
  maturity tier (if still operationally available) and demotes the replacement
  to M1. Both events are hallmarked.
- **Hallmark.** The transfer itself is a hallmark event (§7.8): replaced
  subsystem, replacement, evidence at handoff, probation parameters, success
  criteria, eventual outcome.

### §7.8 The Hallmark Log

A 1545 London assay inspector stamped silver with marks that could not be
silently removed. Sylveste's maturity changes have been computed values
displayed in a mesh table — a current-state view, not a hallmark. v6
introduces the **advancement_events** table, append-only, schema specified
in **sylveste-mj11.1**:

| Field | Purpose |
|---|---|
| subsystem | Which mesh cell |
| from_level / to_level | M-tier transition |
| timestamp | When the transition was decided |
| evidence_snapshot_hash | Hash anchor over the evidence supporting the decision |
| assayer_identity | Who/what made the call (Interspect proposal ID, human operator, FluxBench harness) |
| human_witness_signature | Optional co-signer for high-criticality transitions |
| supersedes | Reference to prior advancement event being corrected (rasura) |

Demotions are events, not edits. Threshold revisions are events. Trust
transfers are events. Human overrides of routing decisions are events. The
log is queryable by operators and forensically reconstructable for any past
moment in system history. Without the log, a subsystem that silently demotes
can erase its own past; with it, every advancement and reversal lives forever.

### §7.9 Cascade Demotion

Demotion propagates through the dependency DAG. v5 asserted cascade without
specifying the rule. v6 picks **synchronous-cap**: the moment an upstream cell
demotes, every downstream cell is immediately capped at the upstream maturity
until the downstream re-proves at its prior tier under the new upstream
conditions. The synchronous variant is safer than evidence-driven cascade,
which would let a downstream cell continue at the higher tier while its
foundation degraded. Re-prove follows the standard Earn → Compound → Break
cycle scoped to the upstream change.

### §7.10 Degraded-Mode Operation

A wayfinder dead-reckons when stars vanish. Sylveste needs an equivalent.

When the evidence pipeline is degraded for more than two hours (any of the
five sources unable to write or be read), the system enters degraded mode:

1. **Routing reverts** to the last known-good baseline snapshot.
2. **Adaptive proposals are suppressed** — Interspect collects but does not
   propose.
3. **The outage is logged** as a dead-reckoning interval that does not
   contribute to evidence, with start time, end time, sources affected.
4. **A human-wayfinder operator** is named in the operational documentation —
   the on-call who carries calibration through outages and disagrees with
   instruments when conditions warrant. The role is not "approver." It is
   "navigator who can recognize landfall before the GPS does."

After the pipeline recovers, evidence collected before the outage rejoins the
flow at its original weight; evidence from the outage interval is excluded.

### §7.11 Epoch Triggers

v5 named loose triggers ("major model API change, architecture migration,
subsystem replacement") and left interpretation to operators. v6 specifies a
rubric:

- **Model API change is "major"** if any of: (a) it changes the cost function
  per token, (b) it changes the latency profile by more than 25%, (c) it
  changes the answer distribution on a held-out evaluation set by more than a
  configured KL-divergence threshold.
- **Architecture migration is "major"** if any of: (a) it changes the kernel
  SQL schema, (b) it changes the event taxonomy in a way that requires
  consumer migration, (c) it changes a layer boundary defined in this
  document.
- **Subsystem replacement** always fires an epoch for the replaced subsystem
  (see §7.7).

**Forward-looking epoch calendar.** Anticipated triggers are tracked in
`docs/epochs/calendar.md` (file populated as a child bead under mj11) with
target dates and pre-trigger preparation procedures. A model deprecation
announced three months out should not surprise the system on the day. The
calendar exists so it doesn't.

**Break-baseline reset on substrate-changing triggers.** When an epoch fires
on a substrate-changing trigger (kernel schema migration, event taxonomy
change, layer-boundary change, subsystem replacement), the affected
subsystem's Break invariant baseline (§7.1) is reset to its conservative
default, regardless of accumulated standing trace. Prior Break receipts
brief the new Compound corridor but do not authorize advancement under it.
Non-substrate-changing triggers (cost or latency shifts on the same model
substrate) carry the existing baseline forward with a recalibration window.

### §7.12 Independent Verification

No subsystem self-reports its maturity. Interspect serves as the architecturally
independent verification layer for everything except itself; per §7.6,
"architecturally independent" today means substrate-shared, and the load-path
audit carries the debt. Interspect's own maturity is evaluated by human
attestation and FluxBench experiments. Until FluxBench reaches M2, Interspect
maturity advancements require explicit human attestation hallmarked under §7.8.

### §7.13 Human Authority Reservation

Evidence thresholds are revisable by human authority regardless of accumulated
evidence to the contrary. The principle (evidence earns authority) is permanent.
The mechanism (specific thresholds, epoch triggers, demotion criteria) is
revisable. v6 adds the instrument: every threshold revision is itself a
hallmark event under §7.8, with operator identity, prior value, new value,
justification, and (for critical-tier changes) a co-signer. A high-trust agent
that can write to threshold config has bounded authority, because every write
leaves a permanent mark.

## The Outcome Axes

Autonomy, quality, and token efficiency remain the measurable outcomes. They
are the *results* of the evidence loop, not the framing — the flywheel
produces them as byproducts of good evidence infrastructure.

**Autonomy.** How much of the development lifecycle runs without human
intervention. Measured by sprint completion rate, gate pass rate on first
attempt, intervention frequency. Not autonomy for its own sake; autonomy that
frees the human to operate at the strategic level where their judgment matters
most.

**Quality.** Defect escape rate, review signal precision, the ratio of
actionable findings to false positives. Quality is the cumulative result of
discipline at every phase: brainstorm rigor, plan review depth, gate
enforcement, multi-perspective code review, and the learning loop that
tightens all of these over time.

**Token efficiency.** Tokens per *impact*: cost per landable change, cost per
actionable finding, cost per defect caught. The goal is not to spend less but
to get more per dollar. Model routing is a first-class decision (Opus for
reasoning, Codex for parallel implementation, Haiku for quick checks, Oracle
for cross-validation). Context hygiene via strict write-behind protocol
prevents the context flooding that kills long-running sprints.

### External Validation

Two independent research threads validate the core thesis from outside
software engineering:

**Orchestration beats raw capability.** Symbolica AI's Arcgentica achieved 36%
on ARC-AGI-3 (abstract reasoning) at $1,005 total — while raw Claude Opus 4.6
scored 0.25% at $8,900. A 340x cost-efficiency improvement from
orchestrator-delegates-to-sub-agents architecture, not from a better model.
The architecture is structurally isomorphic to how Clavain dispatches companion
plugins. Validates PHILOSOPHY.md claim #1 (infrastructure bottleneck, not
intelligence) on abstract reasoning, not just coding.

**Stigmergic coordination scales.** Research on agent coordination via shared
environmental traces (stigmergy) shows 36-41% performance advantage over direct
messaging at 500+ agents ([Pressure Fields and Temporal Decay, 2025](https://arxiv.org/abs/2601.08129)).
Garden Salon's planned CRDT shared-state design — where agents would coordinate
through the document, not through messages — is modeled on this pattern.

## Design Principles

### 1. Mechanism over policy

The kernel provides primitives. The OS provides opinions. A phase chain is a
mechanism: an ordered sequence with transition rules. The decision that
software development should flow through ten phases is a policy that Clavain
configures at run creation time.

That separation is what makes the system extensible without modification. A
documentation project uses `draft → review → publish`. A hotfix uses
`triage → fix → verify`. The kernel doesn't care. New workflows don't require
new kernel code.

### 2. Durable over ephemeral

If it matters, it belongs in the database. Phase transitions, gate evidence,
dispatch outcomes, event history, all persisted atomically in SQLite. Temp
files, environment variables, and in-memory state are not acceptable as the
long-term system of record.

The cost is write latency. The benefit: any session, any agent, any process
can query the true state of the system at any time. When a session crashes
mid-sprint, the run state is intact and resumable.

### 3. Compose through contracts

Small, focused tools composed through explicit interfaces beat large
integrated platforms. The inter-\* constellation follows Unix philosophy: each
companion does one thing well. Composition works because boundaries are
explicit (typed interfaces, schemas, manifests, and declarative specs rather
than prompt sorcery).

The naming convention reflects this: each companion occupies the space
*between* two things. interphase (between phases), interflux (between flows),
interlock (between locks), interpath (between paths). They are bridges and
boundary layers, not monoliths.

### 4. Independently valuable

Any capability driver works standalone. Install interflux for multi-agent
review, tldr-swinton for code context, or interlock for file coordination. No
Clavain, no Intercore, no rest of the stack required. Drivers degrade
gracefully: they use ephemeral state alone, durable state with the kernel. The
full Sylveste stack adds adaptive improvement (profiler) and opinionated
workflow (OS), but these are enhancements, not prerequisites.

### 5. Human attention is the bottleneck

Agents are cheap. Human focus is scarce. The system optimizes for the human's
time, not the agent's. Multi-agent output must be presented so humans can
review quickly and confidently, not just cheaply.

The human drives strategy (what to build, which tradeoffs to accept, when to
ship) while the agency drives execution (which model, which agents, what
sequence, when to advance, what to review). The human is above the loop, not
in it — except during instrument outage, when the human becomes the
wayfinder (§7.10).

### 6. Gates enable velocity

Quality gates are not the opposite of speed — they are the mechanism that
makes speed safe. The goal isn't more review; it's faster shipping with fewer
regressions. If review phases slow you down more than they catch bugs, the
gates are miscalibrated. Match rigor to risk. Gates with graduated authority
can tighten or relax based on evidence — a subsystem that consistently passes
a gate at M3 maturity earns lighter review at M4.

### 7. Self-building as proof

Every capability must survive contact with its own development process.
Clavain builds Clavain. The agency runs its own sprints. A system that
autonomously builds itself is a more convincing proof than any benchmark. Also
the highest-fidelity eval, because it tests the full stack under real
conditions with real stakes.

### 8. Evidence is independently verified

No subsystem stamps its own hallmark. Maturity assessments come from
independent observation (Interspect reading kernel events), not from
self-reported metrics. The entity that assesses quality must be structurally
separate from the entity being assessed.

"Independent" means substrate-separated, not just code-separated. Today most
sources share the kernel substrate (§7.6); the structural debt is recorded
and the load-path audit is the path to paying it down. Without separation,
"evidence earns trust" collapses into "claims earn trust" — and the thesis is
false.

## The Development Lifecycle

Sylveste covers the full product development lifecycle through six
macro-stages, run cycle after cycle. Each macro-stage is a sub-agency, a team
of models and agents selected for the work at hand. Each produces typed
artifacts that become the next stage's input; the kernel enforces handoff via
`artifact_exists` gates at macro-stage boundaries.

### Brainstorm

Collaborative problem framing. Human and agent shape what a specific work
item *is*: its constraints, its success conditions, the prior art that bears
on it, the unknowns worth flagging before plan-time. Brainstorms inherit
context through Research — the surfaced beads (hill-climbing or hill-finding),
the promoted discoveries, the patterns this cycle's flux-review produced —
which Research itself shaped from the prior Reflect. Most agent tools skip
the brainstorm and jump to plan or code; Sylveste makes it a first-class
phase with real artifacts and real gates.

### Plan

Strategy, specification, and plan review. The plan review uses flux-drive
with formalized cognitive lenses to combat AI consensus bias. A plan that
hasn't been reviewed by lenses orthogonal to the planner's own is a plan that
inherits the planner's blind spots.

### Build

Implementation and testing. Codex handles parallel implementation. Opus and
Sonnet handle complex reasoning. Haiku handles quick checks. Test-driven
development is a discipline, not a suggestion; the TDD agents write failing
tests first.

### Ship

Final review, deployment, and knowledge capture. The interflux fleet deploys
explicit cognitive diversity lenses during final review. Code pushes are
gated on human confirmation, where the scope of "confirmation" evolves with
the human delegation ladder (see PHILOSOPHY.md § Earned Authority):
- **L0-L2 (current):** Per-change human confirmation before each push.
- **L3:** Human sets shipping policy (which repos, which confidence
  thresholds). Agent pushes when policy conditions are met.
- **L4-L5:** Human approves the policy itself; agent pushes autonomously
  within policy bounds.

### Reflect

Look inward at the cycle just completed. Patterns discovered, mistakes caught,
decisions validated, complexity calibration data. The artifacts of Reflect are
internal: lessons named clearly enough that future cycles can recall them, and
calibration deltas that update the system's models of itself (per-tier
saturation curves, gate threshold candidates, model routing observations).
Reflect updates the learned interest profile that Research will use next.

### Research

Look outward to seed the next cycle. Signals from external sources (arXiv,
Hacker News, GitHub, Exa, Anthropic docs, RSS) are scored against the interest
profile updated by Reflect, then run through autonomous flux-review — a
multi-lens evaluation that surfaces follow-up work in two distinct shapes:

- **Hill-climbing beads.** Refinements to the trajectory the current cycle
  was already on. A paper that suggests a better dampening parameter for the
  saturation curve §5 named, a benchmark result that updates a routing
  heuristic §11 already tracks, a corrected derivation for the demotion
  latency bound §7.4 published. The flux-review tags these as
  trajectory-aligned: same hill, higher up.
- **Hill-finding beads.** Signals that point off the current trajectory. An
  approach that obviates a subsystem rather than refining it, a paradigm-shift
  finding that would invalidate a current assumption, an external result that
  suggests a different problem is more leveraged than the one we're working
  on. The flux-review tags these as trajectory-divergent: a different hill,
  potentially taller.

Both categories produce work items for next-cycle Brainstorms. The system
needs both: hill-climbing-only research is how a project optimizes itself into
a local maximum and stays there. Hill-finding-only research is how a project
chases novelty until nothing ships. The ratio between the two is a watch-metric
in its own right — sustained drift toward one side suggests the interest
profile or the flux-review lenses need recalibration. Human promotions and
dismissals shift the profile; sources that consistently produce promoted
discoveries earn trust.

Cycle-1 Research runs against neutral defaults until enough Reflects accumulate
to make the profile load-bearing.

## North Star Metric

**What does it cost to ship a reviewed, tested change?**

The metric where all three outcome axes collapse into a single number. A low
cost-per-landable-change requires autonomy (the sprint ran without
babysitting), quality (the change landed without rework), and efficiency
(the right models and agents were selected).

| Category | Metric | What It Measures |
|----------|--------|-----------------|
| **Efficiency** | Tokens per landable change (raw + normalized) | Total token spend for a sprint producing a merged commit; normalized variant per 100-line change |
| **Efficiency** | Cache-corrected cost-per-landable-change | Headline cost adjusted for cache warmth; gap between raw and corrected is itself a watch-metric |
| **Efficiency** | Agent utilization (inventory + effective) | % of dispatched agents whose output contributes to the final change; effective fleet count separated from inventory count |
| **Efficiency** | Model routing accuracy | % of model selections matching the outcome-optimal model |
| **Quality** | Defect escape rate | Bugs found after Ship that were present during Build |
| **Quality** | Cost per actionable finding | Token cost of findings that aren't false positives |
| **Quality** | Activation rate | % of merged subsystems with telemetry-confirmed invocation within 14 days, counted only after ≥3 distinct sessions show activation |
| **Quality** | Anti-Goodhart held-out score | Quarterly evaluation on a task set the routing system has never seen |
| **Autonomy** | Sprint completion rate | % of sprints reaching Ship without abandonment |
| **Autonomy** | Gate pass rate | % of phase transitions passing on first attempt |
| **Learning** | Self-improvement rate | Interspect proposals that improve metrics when applied (with counterfactual tracking per §5.2) |
| **Trust** | Maturity advancement rate | Mesh cells advancing to the next maturity level per quarter |

### Cost Normalization

v5 reported `$2.93/landable change` without defining the denominator. v6
publishes both raw and normalized series:

- **Raw cost per landable change.** Total token spend for a sprint producing a
  merged commit, divided by sprint count. Headline number, retained for
  continuity with the v4/v5 baseline.
- **Cost per 100-line landable change.** Sprint cost divided by lines of code
  changed in the merged commit (additions + deletions, ignoring whitespace).
- **Cost per task-of-typed-complexity.** Sprint cost divided by a complexity
  score derived from sprint inputs (number of beads touched, fan-out of
  dispatch, gate count). Calibrated against actual sprint outcomes.

Each variant is reported with mean ± standard deviation, sample size, and date
range, stratified by sprint type (epic / single-feature / hotfix).

### Cache-Corrected Cost

Cache warmth distorts cost figures. A pillar appearing cheap may be riding
cache. v6 reports headline cost and cache-warmth-corrected cost as paired
numbers. Divergence between them is itself a watch-metric: a growing gap
suggests the system is benefiting from corpus warmth rather than from genuine
efficiency improvement. The instrumentation extends `interstat/scripts/cost-query.sh`
under a child bead.

### Anti-Goodhart Mechanism

Any stable metric becomes a target, and any target becomes gamed. v5
acknowledged the problem with operator-discipline mitigations. v6 adds a
structural counter-mechanism: a held-out task set, evaluated quarterly, that
the routing system has never seen. The held-out result is published alongside
the live metric. When the live metric improves but the held-out result does
not, the system is optimizing the metric at the expense of actual quality.
The held-out set itself rotates annually so it cannot leak into the training
distribution.

### Routing-Decision Evidence Schema

Every dispatch decision (Ockham routing, Clavain gate-tier selection) emits
structured evidence: `{chosen-tier, considered-alternatives, rationale-tag,
fallback-chain, realized-cost, cache-state, decision-source}`. Schema lives
in Intercore as a shared type so Ockham, Clavain, and the intercept project's
distillation pipeline cannot drift. The decision corpus is queryable and
becomes the input for future dispatch calibration.

### Cost Colophon Discipline

Every published cost figure carries a colophon: as-of date, fleet snapshot
hash, routing-overrides snapshot, model versions, review configuration, sample
size. Older figures without colophons are explicitly marked as informally
citable. Without colophons, the $1.17 → $2.93 trajectory is a folk-fact; with
them, future operators can reconstruct the conditions that produced each
number and judge whether the comparison is meaningful.

### Activation Rate

Passive v1 measures whether a merged subsystem is actually invoked within 14
days by combining existing telemetry-adjacent receipts — CASS traces, git
history, closeout artifacts, and route/phase evidence — before explicit
subsystem-event emits are required. A subsystem counts as activated only when
evidence spans at least three distinct sessions. The first three weeks are
baseline observation and report-only: findings should produce follow-up beads
or patches, not hard gates. Any v2 soft-block must wait for explicit
calibration approval and a documented Goodhart review. Because the Phase 0
spike recorded `passive_spike_recall:3/3` and `next_phase:passive-v1`, explicit
emit infrastructure remains deferred until passive reporting misses a
confirmed activation gap.

### Cost Trajectory

The cost-per-landable-change baseline was established on 2026-02-28 at $1.17
(Opus 95% of cost, no colophon — informally citable). As of 2026-03-18, the
figure is $2.93 — the increase reflects expanded review scope (multi-agent
review, reaction rounds) rather than efficiency regression. The trajectory is
expected to improve as model routing matures and the cache-corrected variant
becomes the operational signal. Future figures will publish with colophons.

## Audience

Two brands serve two audiences through shared infrastructure:

**Sylveste** (infrastructure) — for developers and platform builders who want
to build autonomous agencies. Intercore is the kernel. Clavain is the
reference agency. Open source from launch.

**Garden Salon** (experience) — for anyone who wants to think with AI agents
on shared projects. Agents are participants in the workspace, not tools
invoked from a sidebar. The CRDT substrate means agents coordinate through
the document itself.

Three concentric circles, in priority order:

1. **Platform.** Open Intercore as infrastructure for anyone building
   autonomous agencies. Open Clavain as the reference agency. Software
   development is the first vertical; the primitives are domain-general.

2. **Proof by demonstration.** Build the system with the system. Every
   capability must survive contact with its own development process. The
   autonomous epic execution track (rsj.1) is the latest proof: the system
   sequences its own multi-feature work.

3. **Personal rig.** One product-minded engineer, as effective as a full
   team. The personal rig is both the daily driver and the proving ground
   for the platform.

## Open Source Strategy

Everything is open source. All pillars: the kernel (Intercore), the OS
(Clavain), the sovereign runtime (Skaffen), the companion plugins
(Interverse), the TUI tools (Autarch), the profiler (Interspect), and the
evidence infrastructure (Ockham, Interweave, Interop).

The bet is on ecosystem effects. If the kernel is good enough, people will
build their own agencies on top of it. If the reference agency is good
enough, people will write their own companions. The learning loop (Interspect)
benefits from a larger evidence base.

Revenue, when it matters, comes from managed hosting, enterprise support, and
premium companions. Not from restricting access to the core infrastructure.

## Where We Are

As of May 2026 (1,456 beads tracked, 1,239 closed):

- **Kernel:** 8 of 10 epics shipped (E1-E8). Runs, phases, gates, dispatches,
  events, discovery pipeline, rollback, portfolio orchestration, TOCTOU
  prevention, cost-aware scheduling, sandbox specs, durable session
  attribution. Remaining: E9 (Autarch Phase 2) and E10 (Sandboxing).
- **OS:** Full sprint lifecycle (brainstorm → ship) is kernel-driven. 17
  skills, adaptive single-entry workflow (`/route → /sprint → /work`).
- **Autonomous epic execution:** `/campaign` orchestrates epic-level build
  sequences — topological sort by dependency graph, phase-gated dispatch,
  resume-aware checkpointing, strategic contradiction escalation,
  decomposition quality calibration.
- **Evidence infrastructure:** Ockham F1-F7 shipped (intent scoring, connector
  protocol, check hook, INFORM signals, health bypass). Interweave F1-F3
  shipped, F5 in progress (type families, identity crosswalk, connector
  protocol, named queries). Interop Phase 1 shipped (event hub, adapter
  interface, conflict resolver). Factory Substrate ~80% implemented (3,515
  LOC Go, 518 tests). FluxBench at brainstorm/plan phase.
- **Model routing:** Static routing, complexity-aware routing (C1-C5), and
  routing override chain (F1-F5) shipped. Evidence quarantine (per-tier
  freshness windows under §7.3) shipped. Adaptive routing (B3) is next —
  blocked on measurement hardening.
- **Review engine:** ~589 review agents (effective-count instrumentation
  pending under §11). Deployed through interflux with multi-agent synthesis,
  reaction rounds, and cross-model dispatch.
- **Ecosystem:** 64 companion plugins, 81 total modules. Each independently
  installable. Effective-count breakdown by tier (stub / generated / used /
  proven) is pending under §11 fleet-hygiene work.
- **Apps:** Autarch TUI (Bigend, Gurgeh, Coldwine, Pollard). Intercom
  multi-runtime assistant bridging Claude, Gemini, and Codex.
- **Intelligence replatforming:** Auraken Python → Skaffen Go migration in
  progress; Auraken → Hermes Agent overlay supersedes the prior Go-only
  pivot. Hassease (multi-model execution daemon) at brainstorm/plan phase.
- **Self-building:** 1,456 beads tracked, 1,239 closed. The system has been
  building itself continuously since January 2026. Closure-reason
  instrumentation (shipped vs superseded vs abandoned) is pending under §11.

## What's Next

Six active themes, in priority order:

1. **Integration fabric** (Interop) — P0. Event-driven hub replacing
   fragmented sync. Bidirectional Beads ↔ GitHub, Notion ↔ Beads, neutral
   conflict resolution. The foundation that Ontology and Governance depend
   on.
2. **Factory governance** (Ockham) — P0. Intent → dispatch weight offsets,
   algedonic signals (weight-drift detection, first-attempt pass rate
   trends), graduated authority with demotion. Wave 1 F1-F7 shipped; Wave 2
   (anomaly detection, quality subsystem) next.
3. **Intelligence replatforming** (Auraken → Skaffen + Hassease + Hermes
   Agent overlay) — P0. Go packages (lens library, fingerprinting,
   extraction, profile generation) integrated into Skaffen. Hassease routes
   ~80% to GLM/Qwen, escalates planning and review to Claude.
4. **Generative ontology** (Interweave) — P1. Finding-aid for entities
   across 6+ subsystems. Five type families, identity crosswalk, named query
   templates. Permanent constraint: the finding-aid test — delete Interweave
   and everything still works.
5. **Model qualification** (FluxBench) — P1, *substrate-independent
   dependency*. Closed-loop discovery for interflux. Custom benchmarks for
   domain-specific agent prompts, 8 scores per model to AgMoDB. FluxBench
   reaching M2 is the precondition for retiring the substrate-shared
   discount in §7.6.
6. **Evidence pipeline closure** (Interspect Phase 2) — P1. Evidence-driven
   agent selection, canary monitoring, counterfactual shadow evaluation. The
   flywheel's missing link. Depends on Measurement reaching M2.

## Horizons

Future commitments with explicit dependencies. Not "What's Next" — these
require current infrastructure to mature first.

- **Garden Salon MVP** — Multiplayer workspace with CRDT shared state,
  stigmergic agent participation. The experience brand. Depends on: Interop
  M2, Interweave M2, Ockham M2.
- **Domain-general north star** — "Cost per landable change" is
  software-dev-specific. The platform needs a domain-general metric. Depends
  on: Measurement M3.
- **Cross-project federation** — Portable developer identity and learnings
  across projects. Depends on: Interweave M3, Interop M3.
- **L4 auto-ship** — The system merges and deploys when confidence
  thresholds are met. Depends on: Governance M3, Routing M3.

## What This Is Not

- **Not a general AI gateway.** It doesn't route arbitrary messages to
  arbitrary agents. The platform orchestrates complex knowledge work through
  discipline and evidence. Software development is the first vertical; the
  primitives are domain-general.
- **Not a coding assistant.** It doesn't help you write code; it *builds
  software*. The coding is one phase of five.
- **Not a no-code tool.** It's for people who build software with agents.
- **Not uncontrollably self-modifying.** Interspect modifies OS-level
  configuration through safe, reversible overlays. The kernel boundary
  softens as trust is earned — through gated, evidence-based processes with
  independent verification, not direct modification. (See PHILOSOPHY.md §
  Earned Authority.)
- **Not just an agency.** Sylveste is the platform; Clavain is the reference
  agency built on it. The kernel and drivers are infrastructure anyone can
  use to build their own agency.

### Subtraction Discipline

What the project commits to *not* doing, or to retiring. v5 had no equivalent
section; v6 introduces the discipline because a platform that lists six
themes and adds capabilities every quarter without naming sunsets becomes a
muddy blend.

- **Garden Salon MVP build is deferred** until Interop, Interweave, and
  Ockham reach M2. Premature build is a horizon commitment, not a
  near-term workstream.
- **Plugin sunset register** lives in §18. Capabilities below usage threshold
  are scheduled for retirement quarterly.
- **Plugin count is reported alongside effective-count.** Inventory growth
  without effective-count growth is a regression signal, not a celebration.
- **Self-modification stays bounded by hallmark.** Any change Interspect
  makes is hallmarked under §7.8; bounded authority is the precondition for
  earned authority.

## §18 Sunset Register

Capabilities below usage threshold scheduled for sunsetting. Quarterly review
cadence. Each entry: subsystem or capability, usage signal that triggered the
sunset candidate, planned action (deprecate / consolidate / retire), target
date, reversal criteria.

The register is initialized empty in v6 and populated by the first quarterly
review (target 2026-08). The sunset review is itself a hallmark event under
§7.8 so retirement decisions can be reconstructed historically.

## Origins

Sylveste (from Alastair Reynolds' Democratic Anarchists, reflecting the
continuous polling and consensus-driven architecture of the system). Clavain
is a protagonist from the same series. The inter-\* naming convention
describes what each component does: the space *between* things. Interverse is
the universe that contains them all.

The project began by merging
[superpowers](https://github.com/obra/superpowers),
[superpowers-lab](https://github.com/obra/superpowers-lab),
[superpowers-developing-for-claude-code](https://github.com/obra/superpowers-developing-for-claude-code),
and
[compound-engineering](https://github.com/EveryInc/compound-engineering-plugin).
It has since grown into an autonomous software development agency platform
with 81 modules across six pillars.

---

## Appendix A — Lens-Finding Triage

Per the v6 acceptance criteria: every P0 and P1 finding from the 10-lens
flux-drive review of v5.0 (2026-04-26) plus the 4-domain flux-explore is
listed below with triage. `spec` = resolved in v6 prose at the named section.
`ship` = decomposed into a child bead under sylveste-mj11. `defer` = not paid
for in v6 (reason given).

| Source | ID | Brief | Triage | Resolved by |
|---|---|---|---|---|
| fd-tidal-bore | P0-1 | Cross-source independence test | spec | §4 substrate table + §7.6 |
| fd-tidal-bore | P0-2 | Authority advancement bore-detector | spec | §6 shadow + §7.4 demotion bounds |
| fd-tidal-bore | P1-1 | Campaign-level dispatch bore | ship | gate-staggering bead under mj11 |
| fd-tidal-bore | P1-2 | Epoch table | spec | §7.11 epoch calendar |
| fd-tidal-bore | P1-3 | New sources during transition | spec | §6 shadow requirement |
| fd-tidal-bore | P1-4 | Sustained vs spike not distinguished | spec | §7.3 decay model |
| fd-perfumer-accord | P0-1 | No heart note | spec | §1 |
| fd-perfumer-accord | P0-2 | Subtraction discipline missing | spec | §17 + §18 |
| fd-perfumer-accord | P1-1 | SF/garden register mix | defer | doc-meta; vision doc itself is the bridge |
| fd-perfumer-accord | P1-2 | External validation as volatile | defer | acceptable as-is |
| fd-perfumer-accord | P1-3 | v4→v5 reformulation unnamed | spec | §1 "From v5 to v6" |
| fd-perfumer-accord | P1-4 | Plugin count without composition | spec | §11 + §14 effective-count |
| fd-polynesian-wayfinding | P0-1 | All evidence from same substrate | spec | §7.6 |
| fd-polynesian-wayfinding | P0-2 | No dead-reckoning | spec | §7.10 |
| fd-polynesian-wayfinding | P1-1 | No apprenticeship for new sources | spec | §6 shadow |
| fd-polynesian-wayfinding | P1-2 | No reference frame (etak) | ship | quarterly state-snapshot bead |
| fd-polynesian-wayfinding | P1-3 | No total disorientation recovery | spec | §7.10 + §7.11 |
| fd-polynesian-wayfinding | P1-4 | Human-as-wayfinder unnamed | spec | §7.10 |
| fd-flywheel-dynamics | P0-1 | Phase 3-4 bootstrap unspecified | spec | §5.1 |
| fd-flywheel-dynamics | P0-2 | min() aggregation pathology | ship | system-trust formula bead under mj11 |
| fd-flywheel-dynamics | P1-1 | Dampening unparameterized | spec | §5 + per-tier saturation curves bead |
| fd-flywheel-dynamics | P1-2 | Phase 1→2 hidden Interop dep | spec | §5 dependency annotation |
| fd-flywheel-dynamics | P1-3 | Sprint-as-evidence undifferentiated | spec | §5 quality filter |
| fd-flywheel-dynamics | P1-4 | Interspect self-recursion | spec | §5.2 + counterfactual instrumentation bead |
| fd-dispatch-economics | P0-1 | Cost normalization | spec | §11 normalization |
| fd-dispatch-economics | P0-2 | Anti-Goodhart | ship | held-out eval bead under mj11 |
| fd-dispatch-economics | P1-1 | 589-fleet tail-management | spec | §11 fleet hygiene + auto-archive bead |
| fd-dispatch-economics | P1-2 | Opus-95% structural | spec | §11 commitment to track Opus-share trajectory |
| fd-dispatch-economics | P1-3 | 48h quarantine derivation | spec | §7.3 per-tier freshness |
| fd-dispatch-economics | P1-4 | North-star confidence interval | spec | §11 mean ± stddev |
| fd-trust-mechanics | P0-1 | Demotion latency unbounded | spec | §7.4 |
| fd-trust-mechanics | P0-2 | Trust transfer vibe-check | spec | §7.7 |
| fd-trust-mechanics | P1-1 | Epoch triggers loose | spec | §7.11 rubric |
| fd-trust-mechanics | P1-2 | Weakest-link perverse incentive | ship | system-trust formula bead (same as fd-flywheel-dynamics P0-2) |
| fd-trust-mechanics | P1-3 | Cascade demotion unspecified | spec | §7.9 synchronous-cap |
| fd-trust-mechanics | P1-4 | Human authority audit-trail gap | spec | §7.13 + §7.8 |
| fd-kernel-boundary | P0-1 | Multi-OS L2 coordination | ship | L2 coordination contract bead under mj11 |
| fd-kernel-boundary | P0-2 | Host-agnostic untested | defer | post-Mythos host-portability test |
| fd-kernel-boundary | P1-1 | Mechanism vs policy lint | ship | kernel-policy lint bead under mj11 |
| fd-kernel-boundary | P1-2 | Event taxonomy versioning | ship | event-taxonomy versioning bead under mj11 |
| fd-kernel-boundary | P1-3 | SQLite scaling envelope | ship | kernel throughput observation bead under mj11 |
| fd-scriptorium | P0-1 | No canonical exemplar | ship | per-evidence-type canonical store bead under mj11 |
| fd-scriptorium | P0-2 | Cost-baseline lineage broken | spec | §11 colophon + instrumentation bead |
| fd-scriptorium | P1-1 | Copy-error discipline missing | ship | derivation-hashing bead under mj11 |
| fd-scriptorium | P1-2 | SQLite silent overwrite | ship | append-only event-table bead under mj11 |
| fd-scriptorium | P1-3 | Bead corpus no exemplar | ship | bead-state snapshot bead under mj11 |
| fd-scriptorium | P1-4 | Sprint-output correction protocol | spec | §7.8 hallmark log generalizes (supersedes field) |
| fd-evidence-pipeline-integrity | P0-1 | Tier-weight aggregation | ship | sylveste-mj11.2 (already filed) |
| fd-evidence-pipeline-integrity | P0-2 | Schema versioning | ship | evidence-schema versioning bead under mj11 |
| fd-evidence-pipeline-integrity | P1-1 | Independent verification weak | spec | §7.6 |
| fd-evidence-pipeline-integrity | P1-2 | Per-subsystem promotion criteria | ship | 8 child beads (Persistence, Coordination, Discovery, Review, Integration, Ontology, Measurement, Governance) under mj11 |
| fd-evidence-pipeline-integrity | P1-3 | No decay model | spec | §7.3 |
| fd-evidence-pipeline-integrity | P1-4 | Attribution chain end-to-end test | ship | smoke-test bead under mj11 |
| fd-assay-office-hallmarks | P0-1 | Hallmark log missing | ship | sylveste-mj11.1 (already filed) |
| fd-assay-office-hallmarks | P0-2 | No wardens of the touch | spec | §7.6 + §7.12 (FluxBench M2 precondition is in §15) |
| fd-assay-office-hallmarks | P1-1 | Substrate separation logical only | spec | §7.6 |
| fd-assay-office-hallmarks | P1-2 | Trust transfer ceremony missing | spec | §7.7 + §7.8 |
| fd-assay-office-hallmarks | P1-3 | Human authority no hallmark | spec | §7.13 + §7.8 |
| brainstorm | jo-ha-kyū | "Ha" Break stage | spec | §7.1 (Break phase) |
| brainstorm | masonry | Demotion-rehearsal precondition | spec | §7.5 (related: sylveste-v3ck) |
| brainstorm | model-routing | Routing-decision evidence schema | ship | dispatch-evidence schema bead under mj11 |
| brainstorm | masonry | Load-path independence audit | ship | load-path audit bead under mj11 |
| brainstorm | model-routing | Cache-corrected cost | ship | cost-query.sh extension bead under mj11 |
| brainstorm | autonomy-ladder | Hysteresis bands | spec | §7.1 |
| brainstorm | autonomy-ladder | Promotion-path provenance | spec | §7.8 hallmark records the path |

## Appendix B — Child Beads Implied by v6

Already filed under `sylveste-mj11`:

- `sylveste-mj11.1` — Hallmark log (advancement_events table)
- `sylveste-mj11.2` — Tier-weight aggregation specification
- `sylveste-mj11.3` — Interspect substrate-independence and suhba-window
  classification per subsystem (filed 2026-05-06 from Break-phase synthesis)
- `sylveste-mj11.4` — Break invariant tuple schema and per-subsystem
  calibration (filed 2026-05-06)
- `sylveste-mj11.5` — Break Synaxis cadence + chain-of-custody schema +
  axis-set publication (filed 2026-05-06)
- `sylveste-mj11.6` — Dormancy/degradation rubric + Bauschinger-positive
  demotion + tarbiya pathway + non-conformance disposition (filed 2026-05-06)

Still to file:

1. System-trust formula change (`min` → criticality-weighted percentile)
2. Per-tier saturation curve specification for B2 dampening
3. Substrate-independence load-path audit (one-time, produces diagram)
4. Demotion-rehearsal harness on FluxBench (overlaps `sylveste-v3ck` —
   reconcile before duplicating)
5. Counterfactual-tracking instrumentation on Interspect proposals
6. Forward-looking epoch calendar at `docs/epochs/calendar.md`
7. Cost-normalization instrumentation (per-100-line, per-complexity)
8. Cache-corrected cost extension to `interstat/scripts/cost-query.sh`
9. Held-out task set + quarterly anti-Goodhart eval
10. Routing/dispatch evidence schema as Intercore shared type
11. Auto-archive policy for stub/used review agents
12. Bead `closure_reason` field instrumentation
13. Cost-figure colophon instrumentation
14. Per-subsystem promotion criteria (eight beads: Persistence, Coordination,
    Discovery, Review, Integration, Ontology, Measurement, Governance)
15. L2 coordination contract between Clavain and Skaffen
16. Kernel mechanism-vs-policy lint
17. Event taxonomy versioning
18. Kernel throughput observation under WAL contention
19. Per-evidence-type canonical store
20. Derivation-hashing for evidence transformations
21. Append-only event table for SQLite history
22. Bead-state snapshot policy
23. Evidence-schema versioning policy
24. Attribution-chain end-to-end smoke test
25. Quarterly state-snapshot ceremony (etak reference fix)
26. Gate-staggering for `/campaign` simultaneous dispatch

(The original Appendix B item "Interspect Break-scoring" is subsumed by
mj11.3 + mj11.4 + mj11.5 + mj11.6, which collectively specify the scoring
authority, invariant tuple, formalization protocol, and consequence ladder
that the Break-scoring concept implied.)

Some entries above will reconcile against existing related beads
(`sylveste-v3ck`, `sylveste-4rwh`, `sylveste-5lla`) before new beads are
filed.

---

*Module inventory, model routing stages, and adoption ladder:
[sylveste-reference.md](./sylveste-reference.md). Layer-specific vision docs:
[Intercore](../core/intercore/docs/intercore-roadmap.md) (kernel),
[Clavain](../os/Clavain/docs/clavain-vision.md) (OS),
[Skaffen](../os/Skaffen/PHILOSOPHY.md) (sovereign runtime),
[Autarch](../apps/Autarch/docs/autarch-vision.md) (apps),
[Interspect](./interspect-vision.md) (profiler,
[roadmap](./interspect-roadmap.md)). Outline gate-test:
[2026-05-06-sylveste-vision-v6-outline.md](./research/2026-05-06-sylveste-vision-v6-outline.md).*
