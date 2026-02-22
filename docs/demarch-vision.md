# Demarch — Vision

**Version:** 3.0
**Date:** 2026-02-21
**Status:** Draft

---

## The Pitch

Demarch is an open-source autonomous software development agency platform that pushes the frontier on three axes simultaneously: state-of-the-art autonomy, uncompromising quality, and relentless token efficiency.

Most agent systems pick two. Full autonomy with quality? Expensive — you throw tokens at everything and hope the review fleet catches the mess. Autonomy with efficiency? Fast and cheap, but the output is slop. Quality with efficiency? Sure — just keep a human in the loop for every decision, defeating the point.

Demarch refuses to choose. It orchestrates the full development lifecycle from problem discovery through shipped code, selecting the right model for each task with the discipline, durability, and accountability that shipping real software demands. And it gets cheaper and better every time it runs, because it learns from what happened last time.

Not a coding assistant. Not an AI gateway. Not a framework for calling LLMs. A platform for autonomous software development agencies that build software with discipline, at a cost that keeps declining.

The whole thing is open source.

## Why This Exists

LLM-based agents have a fundamental problem: nothing survives. Context windows compress. Sessions end. Networks drop. Processes crash. An agent that ran for an hour, produced three artifacts, dispatched two sub-agents, and advanced through four workflow phases leaves behind... a chat transcript. The state, the decisions, the evidence, the coordination signals: gone. Not a prompting problem. An infrastructure problem. And most agent systems today handle it with temp files, environment variables, in-memory state, and hope.

Demarch handles it with a durable kernel (SQLite-backed Go CLI), an opinionated OS that encodes development discipline, a profiler that learns from outcomes, and 33+ companion drivers. But the infrastructure is not the aspiration.

The bet: if you build the right infrastructure beneath agents, they become capable of the full development lifecycle. Not just code generation, but discovery, design, review, testing, shipping, and compounding what was learned. And if you build a learning loop on top of that infrastructure, one that measures outcomes per dollar and feeds that signal back into model routing, agent selection, and gate calibration, you get a system where autonomy, quality, and efficiency aren't tradeoffs. They're a flywheel. More autonomy produces more outcome data. More outcome data improves routing and review. Better routing cuts cost. Lower cost enables more autonomy. The system that runs the most sprints learns the fastest.

## The Stack

Five pillars, organized in three layers plus one cross-cutting profiler. Each pillar has a clear owner, a clear boundary, and a clear survival property.

```
Layer 3: Apps (Autarch)
├── Interactive TUI surfaces for kernel state
├── Bigend (monitoring), Gurgeh (PRD generation),
│   Coldwine (task orchestration), Pollard (research)
└── Swappable — if Autarch is replaced, everything beneath survives

Layer 2: OS (Clavain) + Drivers (Companion Plugins)
├── The opinionated workflow — phases, gates, model routing, dispatch
├── 33+ companion plugins, each wrapping one capability
├── Every driver independently installable and useful standalone
└── If the host platform changes, opinions survive; UX adapters are rewritten

Layer 1: Kernel (Intercore)
├── Host-agnostic Go CLI + SQLite WAL database
├── Runs, phases, gates, dispatches, events — the durable system of record
├── Mechanism, not policy — doesn't know what "brainstorm" means
└── If everything above disappears, the kernel and all its data survive

Cross-cutting: Profiler (Interspect)
├── Reads kernel events, correlates with human corrections
├── Proposes changes to OS configuration (routing, agent selection, gates)
├── The learning loop — the thing that makes the system improve over time
└── Never modifies the kernel — only the OS layer
```

The survival properties are the point. Each layer can be replaced, rewritten, or removed without destroying the layers beneath it. The kernel outlives the OS. The OS outlives its host platform. The apps outlive any particular rendering choice. Practical architecture for a system that must survive the agent platform wars. Not paranoia, just planning.

### What Each Layer Does

**The kernel (Intercore)** provides mechanism. Runs, phases, gates, dispatches, events, state, locks, sentinels. A Go CLI binary: no daemon, no server, no background process. Every `ic` invocation opens the database, does its work, and exits. The SQLite database is the system of record. The kernel says "a gate can block a transition." It doesn't say "brainstorm requires an artifact." That's policy, and policy belongs in the OS.

**The OS (Clavain)** provides policy. Which phases make up a development sprint, what conditions must be met at each gate, which model to route each agent to, when to advance automatically. Clavain orchestrates the full lifecycle from problem discovery through shipped code. It's opinionated about what "good" looks like at every phase, and those opinions are encoded in gates, review agents, and quality disciplines. Today it ships as a Claude Code plugin; the architecture is designed so the opinions survive even if the host platform doesn't.

**The profiler (Interspect)** provides learning. It reads the kernel's event stream, correlates dispatch outcomes with both human signals (review dismissals, gate overrides, manual corrections) and automated signals (CI results, revert frequency, finding density), and proposes changes to OS configuration. The signal mix shifts as autonomy increases: human-heavy at L0-L2, automated-heavy at L3-L4. Static orchestration is table stakes; a system that improves its own agents through evidence rather than intuition is what makes Demarch different. Interspect never touches the kernel. It modifies the OS layer through safe, reversible overlays. (Full signal taxonomy in the [Interspect vision](./interspect-vision.md).)

**The drivers (companion plugins)** provide capabilities. Multi-agent review (interflux), file coordination (interlock), ambient research (interject), token-efficient code context (tldr-swinton), agent visibility (intermux), multi-agent synthesis (intersynth), and two dozen more. Each wraps one capability and integrates with kernel primitives when present. Every driver is independently installable, usable in vanilla Claude Code without Clavain, Intercore, or any other Demarch module. Without the kernel, drivers use local or ephemeral state; with it, they get durability, coordination, and event history. The full stack provides enhanced integration, but each driver is valuable on its own.

**The apps (Autarch)** provide surfaces. Bigend (monitoring), Gurgeh (PRD generation), Coldwine (task orchestration), Pollard (research intelligence). Each renders kernel state into interactive TUI experiences. The apps are a convenience layer; everything they do can be done via CLI.

## The Frontier

Demarch advances three axes simultaneously. Every roadmap decision, every new module, every architectural choice is filtered through this lens: does it improve at least two axes without materially weakening the third?

**Autonomy.** How much of the development lifecycle runs without human intervention. Not autonomy for its own sake, but autonomy that frees the human to operate at the strategic level where their judgment matters most. Measured by sprint completion rate, gate pass rate on first attempt, intervention frequency at each autonomy level.

**Quality.** Defect escape rate, review signal precision, the ratio of actionable findings to false positives. Quality is not a phase you bolt on at the end. It's the cumulative result of discipline at every phase: brainstorm rigor, plan review depth, gate enforcement, multi-perspective code review, and the learning loop that tightens all of these over time.

**Token efficiency.** Not just raw tokens, but tokens per *impact*: cost per landable change, cost per actionable finding, cost per defect caught. The goal is not to spend less but to get more per dollar. Twelve agents should cost less than eight through orchestration optimization, *and* catch more bugs. Two tactics make this concrete: model routing as a first-class decision (no one model is best at everything: Gemini for long-context exploration, Opus for reasoning, Codex for parallel implementation, Haiku for quick checks, Oracle for cross-validation), and context hygiene via a strict write-behind protocol (raw sub-agent output persists to the kernel, but only synthesized summaries enter the orchestrator's context window, preventing the context flooding that kills long-running sprints).

The flywheel connecting these three axes is Interspect. The profiler reads outcome data from every sprint and proposes configuration changes: model downgrades where Haiku catches the same issues as Opus, agent retirement where a reviewer consistently produces findings no one acts on, gate relaxation where a check always passes. Each optimization simultaneously increases autonomy (less human calibration needed), improves quality (resources reallocated to where they matter), and reduces cost (less waste). The system that ships the most sprints learns the fastest, and the system that learns the fastest ships the cheapest.

## Design Principles

### 1. Mechanism over policy

The kernel provides primitives. The OS provides opinions. A phase chain is a mechanism: an ordered sequence with transition rules. The decision that software development should flow through ten phases is a policy that Clavain configures at run creation time.

That separation is what makes the system extensible without modification. A documentation project uses `draft → review → publish`. A hotfix uses `triage → fix → verify`. A research spike uses `explore → synthesize`. The kernel doesn't care. New workflows don't require new kernel code.

### 2. Durable over ephemeral

If it matters, it's in the database. Phase transitions, gate evidence, dispatch outcomes, event history, all persisted atomically in SQLite. Temp files, environment variables, and in-memory state are never acceptable for the system of record.

The cost is write latency. The benefit: any session, any agent, any process can query the true state of the system at any time. When a session crashes mid-sprint, the run state is intact and resumable. When a new agent joins, it reads the same truth everyone else reads.

### 3. Compose through contracts

Small, focused tools composed through explicit interfaces beat large integrated platforms. The inter-\* constellation follows Unix philosophy: each companion does one thing well. Composition works because boundaries are explicit (typed interfaces, schemas, manifests, and declarative specs rather than prompt sorcery).

The naming convention reflects this: each companion occupies the space *between* two things. interphase (between phases), interflux (between flows), interlock (between locks), interpath (between paths). They are bridges and boundary layers, not monoliths.

### 4. Independently valuable

Any capability driver works standalone. Install interflux for multi-agent review, tldr-swinton for code context, or interlock for file coordination. No Clavain, no Intercore, no rest of the stack required. Drivers degrade gracefully: they use ephemeral state alone, durable state with the kernel. The full Demarch stack adds adaptive improvement (profiler) and opinionated workflow (OS), but these are enhancements, not prerequisites.

The constraint also prevents consolidation creep. The temptation to fold a driver into its nearest layer (interphase into Intercore, intersynth into interflux) is always wrong if it would break standalone installation.

### 5. Human attention is the bottleneck

Agents are cheap. Human focus is scarce. The system optimizes for the human's time, not the agent's. Token efficiency is not the same as attention efficiency. Multi-agent output must be presented so humans can review quickly and confidently, not just cheaply.

The human drives strategy (what to build, which tradeoffs to accept, when to ship) while the agency drives execution (which model, which agents, what sequence, when to advance, what to review). The human is above the loop, not in it. The autonomy ladder below tracks how this plays out as intervention frequency decreases.

### 6. Discipline before speed

Quality gates matter more than velocity. Agents without discipline ship slop. The system resolves all open questions before execution because ambiguity costs more during building than during planning. The review phases are not overhead; they are the product.

Gates are kernel-enforced invariants, not prompt suggestions. An agent cannot bypass a gate regardless of what the LLM requests. This is the difference between "please check for a plan artifact" and "the system will not advance without a plan artifact." The kernel enforces gates for transitions matching its gate rules map; the OS provides additional gates (via agency specs) for OS-specific phases. Both layers contribute to enforcement; neither alone covers the full chain.

### 7. Self-building as proof

Every capability must survive contact with its own development process. Clavain builds Clavain. The agency runs its own sprints. The credibility engine: a system that autonomously builds itself is a more convincing proof than any benchmark. Also the highest-fidelity eval, because it tests the full stack under real conditions with real stakes.

## The Development Lifecycle

Demarch covers the full product development lifecycle through five macro-stages. Each macro-stage is a sub-agency, a team of models and agents selected for the work at hand.

### Discover

Research, brainstorming, and problem definition. The agency scans sources, identifies opportunities, and frames the problem worth solving.

The discovery pipeline closes the loop between what the world knows and what the system is working on. Sources (arXiv, Hacker News, GitHub, Exa, Anthropic docs, RSS) are scored against a learned interest profile. High-confidence discoveries auto-create work items. Medium-confidence ones surface for human review. Low-confidence ones are logged for later.

The feedback loop is the interesting part: human promotions and dismissals shift the interest profile vector. Sources that consistently produce promoted discoveries earn trust. Sources that produce noise lose it. The thresholds adapt.

### Design

Strategy, specification, planning, and plan review. The agency designs the solution and validates it through multi-perspective review before any code is written.

Most agent tools fall down here: they treat product work as prompt fluff and skip straight to code. Demarch makes brainstorm and strategy first-class phases with real artifacts, real gates, and real review. The plan review uses flux-drive with formalized cognitive lenses (security, resilience, architecture, user experience) to combat AI consensus bias.

### Build

Implementation and testing. The agency writes code, runs tests, and verifies correctness.

Codex handles parallel implementation. Opus and Sonnet handle complex reasoning. Haiku handles quick checks. Test-driven development is a discipline, not a suggestion; the TDD agents write failing tests first.

### Ship

Final review, deployment, and knowledge capture. The agency validates the change, lands it, and compounds what was learned.

The interflux fleet deploys explicit cognitive diversity lenses during final review. Oracle provides cross-AI validation. The system never pushes code to a remote repository without human confirmation (this invariant holds regardless of autonomy level).

### Reflect

Capture what was learned. The agency documents patterns discovered, mistakes caught, decisions validated, and complexity calibration data. Closes the recursive learning loop: every sprint feeds knowledge back into the system.

Each macro-stage produces typed artifacts that become the next stage's input. The kernel enforces handoff via `artifact_exists` gates at macro-stage boundaries. The OS defines which artifact types satisfy each gate.

## The Autonomy Ladder

How much human intervention does a single sprint require? The ladder tracks this one dimension. The human's role is fixed at every level (set objectives, make tradeoffs, approve deployments); what changes is how often they need to exercise it.

**Level 0: Record.** The kernel records what happened. Runs, phases, dispatches, artifacts, all tracked. The human drives everything. The kernel is a logbook. *(Shipped.)*

**Level 1: Enforce.** Gates evaluate real conditions. A run cannot advance without meeting preconditions. The kernel says "no" when evidence is insufficient. The human reviews every phase transition. *(Shipped.)*

**Level 2: React.** Events trigger automatic reactions. Phase transitions spawn agents. Completed dispatches advance phases. The human observes and intervenes on exceptions. *(Shipped.)*

**Level 3: Auto-remediate.** The system retries failed gates, substitutes agents, and adjusts parameters without human intervention. The human is notified of remediations but only intervenes when the system exhausts its options. *(Planned.)*

**Level 4: Auto-ship.** The system merges and deploys when confidence thresholds are met. The human approves shipping policy (which thresholds, which repos), not individual changes. *(Future.)*

No level is self-promoting. The system advances only when outcome data justifies it, and any level can be revoked if the evidence stops supporting it.

### Capability Tracks (orthogonal to autonomy)

Two capabilities cut across the autonomy ladder rather than sitting on it:

**Discovery.** The pipeline that finds work before it can be recorded. Scans sources, scores relevance, routes findings through confidence-tiered gates. Operates at any autonomy level. *(Shipped, kernel primitives landed.)*

**Adaptation.** Interspect reads kernel events, correlates with outcomes, and proposes configuration changes. Agents that produce false positives get downweighted. Gate rules evolve based on evidence. Operates at any autonomy level, but its value compounds as more sprints produce more data. *(In progress, the current frontier.)*

**Portfolio orchestration.** The kernel manages concurrent runs across multiple projects. Token budgets prevent runaway costs. Changes in one project trigger verification in dependents. Operates at any autonomy level. *(Shipped, portfolio primitives landed.)*

## North Star Metric

**What does it cost to ship a reviewed, tested change?**

The metric where the three frontier axes collapse into a single number. A low cost-per-landable-change requires all three: autonomy (the sprint ran without babysitting), quality (the change landed without rework), and efficiency (the right models and agents were selected, not the most expensive ones).

Supporting metrics, organized by axis:

| Axis | Metric | What It Measures |
|------|--------|-----------------|
| **Efficiency** | Tokens per landable change | Total token spend for a sprint that produces a merged commit |
| **Efficiency** | Agent utilization | % of dispatched agents whose output contributes to the final change |
| **Efficiency** | Model routing accuracy | % of model selections that match the outcome-optimal model |
| **Efficiency** | Time to merge | Wall-clock minutes from sprint creation to landed commit |
| **Quality** | Defect escape rate | Bugs found after Ship that were present during Build |
| **Quality** | Cost per actionable finding | Token cost of quality gate findings that aren't false positives |
| **Autonomy** | Sprint completion rate | % of sprints that reach Ship without abandonment |
| **Autonomy** | Gate pass rate | % of phase transitions that pass on first attempt |
| **Learning** | Self-improvement rate | Interspect proposals that improve metrics when applied |

The north star is economic because the platform play only works if other people can afford to run it. But cost alone is a vanity metric. A system that's cheap and wrong is worthless. The point is outcomes per dollar: defects caught per token, merge-ready changes per session, signal per gate. Interspect drives this number down over time, and the self-building loop generates the evidence Interspect needs to learn.

## Audience

Demarch is an open-source platform for anyone building autonomous software development agencies. Intercore is the kernel. Clavain is the reference agency. The personal rig is the highest-fidelity eval: built by using it to build itself.

Three concentric circles, in priority order:

1. **Platform.** Open Intercore as infrastructure for anyone building autonomous software development agencies. Open Clavain as the reference agency. The whole stack, open source, from launch.

2. **Proof by demonstration.** Build the system with the system. Every capability must survive contact with its own development process. A system that autonomously builds itself is a more convincing proof than any benchmark.

3. **Personal rig.** One product-minded engineer, as effective as a full team. The personal rig is both the daily driver and the proving ground for the platform. Optimized relentlessly for one workflow, but the architecture ensures those optimizations generalize.

## Open Source Strategy

Everything is open source. All five pillars: the kernel (Intercore), the OS (Clavain), the companion plugins (Interverse), the TUI tools (Autarch), and the profiler (Interspect).

The bet is on ecosystem effects. If the kernel is good enough, people will build their own agencies on top of it. If the reference agency is good enough, people will write their own companions. The value of the platform increases with every external contribution, and the learning loop (Interspect) benefits from a larger evidence base.

Revenue, when it matters, comes from managed hosting, enterprise support, and premium companions. Not from restricting access to the core infrastructure.

## Where We Are

As of February 2026:

- **Kernel:** 10 of 12 epics shipped. Runs, phases, gates, dispatches, events, discovery pipeline, rollback, portfolio orchestration, TOCTOU prevention, cost-aware scheduling. All landed and tested.
- **OS:** Version 0.6.60. 16 skills, 4 agents, 53 commands, 22 hooks. Full sprint lifecycle (brainstorm → ship) is kernel-driven.
- **Model routing:** Static routing and complexity-aware routing (C1-C5) shipped. 22 routing tests.
- **Review engine:** 7 specialized review agents + 5 research agents, deployed through interflux with multi-agent synthesis.
- **Ecosystem:** 33+ companion plugins shipped, each independently installable.
- **Profiler:** Evidence collection shipped (override tracking, false positive rates, finding density). Proposal engine and automatic routing adjustments are next.
- **Self-building:** 1,419 beads tracked, 1,098 closed. The system has been building itself for months.

## What's Next

Three parallel tracks converging toward a self-building agency with adaptive model routing and fleet-optimized dispatch:

**Track A: Kernel integration.** Done. Sprint is fully kernel-driven.

**Track B: Model routing.** Static and complexity-aware routing done. Next: Interspect outcome data driving model selection (B3).

**Track C: Agency architecture.** The next frontier. Declarative agency specs (C1), agent fleet registry with cost/quality profiles (C2), budget-constrained fleet composition (C3), cross-phase handoff protocol (C4), and the convergence point: a self-building loop where Clavain uses its own agency specs to run its own development sprints (C5).

```
Track A (Kernel)      Track B (Routing)     Track C (Agency)
    A1 ✓                  B1 ✓                  C1 ←
    │                     │                     │
    A2 ✓                  B2 ✓─────────────→    C2 ←
    │                     │                     │
    A3 ✓                  B3                    C3
    │                                           │
    └───────────────────────────────────────→   C4
                                                │
                                               C5 ← convergence
                                          (self-building)
```

## What This Is Not

- **Not a general AI gateway.** It doesn't route arbitrary messages to arbitrary agents. It orchestrates software development specifically.
- **Not a coding assistant.** It doesn't help you write code; it *builds software*. The coding is one phase of five.
- **Not a no-code tool.** It's for people who build software with agents. Full stop.
- **Not self-modifying.** Interspect can modify OS-level configuration. It cannot modify the kernel. This is a deliberate safety boundary.
- **Not just an agency.** Demarch is the platform; Clavain is the reference agency built on it. The kernel and drivers are infrastructure anyone can use to build their own agency.

## Origins

Demarch (from Alastair Reynolds' Democratic Anarchists, reflecting the continuous polling and consensus-driven architecture of the system). Clavain is a protagonist from the same series. The inter-\* naming convention describes what each component does: the space *between* things. Interverse is the universe that contains them all.

The project began by merging [superpowers](https://github.com/obra/superpowers), [superpowers-lab](https://github.com/obra/superpowers-lab), [superpowers-developing-for-claude-code](https://github.com/obra/superpowers-developing-for-claude-code), and [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin). It has since grown into an autonomous software development agency platform with five pillars and 42 modules.

---

*Module inventory, model routing stages, and adoption ladder: [demarch-reference.md](./demarch-reference.md). Layer-specific vision docs: [Intercore](../core/intercore/docs/intercore-roadmap.md) (kernel), [Clavain](../os/clavain/docs/clavain-vision.md) (OS), [Autarch](../apps/autarch/docs/autarch-vision.md) (apps), [Interspect](./interspect-vision.md) (profiler).*
