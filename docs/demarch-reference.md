# Demarch — Reference

Companion to [demarch-vision.md](./demarch-vision.md). Module inventory, model routing stages, and adoption ladder.

---

## The Five Pillars

Demarch's top-level organizational units. Each pillar has a clear owner and boundary. See [glossary.md](./glossary.md) for how pillars relate to the 3-layer architecture.

| Pillar | Role | Layer |
|--------|------|-------|
| **Intercore** | Orchestration kernel — durable system of record | L1 (Kernel) |
| **Clavain** | Agent OS — workflow policy, reference agency | L2 (OS) |
| **Interverse** | Companion plugins, each independently valuable (`ls interverse/ \| wc -l`) | L2 (Drivers) |
| **Autarch** | TUI surfaces — Bigend, Gurgeh, Coldwine, Pollard | L3 (Apps) |
| **Interspect** | Adaptive profiler — the learning loop | Cross-cutting |

## The Constellation

Modules organized by architectural role within the pillars.

### Infrastructure (Intercore pillar)

| Module | What It Does |
|--------|-------------|
| **intercore** | Orchestration kernel — runs, phases, gates, dispatches, events, state, locks |
| **interspect** | Adaptive profiler — reads kernel events, proposes OS configuration changes |
| **intermute** | Multi-agent coordination service (Go) — message routing between agents |

### Operating System (Clavain pillar)

| Module | What It Does |
|--------|-------------|
| **clavain** | Autonomous software agency — the opinionated workflow, skills, hooks, routing |

### Core Drivers (Interverse pillar)

| Module | Capability |
|--------|-----------|
| **interflux** | Multi-agent review and research dispatch |
| **interlock** | Multi-agent file coordination |
| **interject** | Ambient research and discovery engine |
| **tldr-swinton** | Token-efficient code context |
| **intermux** | Agent visibility and session monitoring |
| **intersynth** | Multi-agent output synthesis |
| **interserve** | Codex dispatch and context compression |

Additional drivers cover artifact generation (interpath), document freshness (interwatch), plugin publishing (interpub), cross-AI review (interpeer), Notion sync (interkasten), TUI testing (tuivision), cognitive lenses (interlens), voice adaptation (interfluence), and more. The full listing is in [CLAUDE.md](../CLAUDE.md).

### Applications (Autarch pillar)

| Module | What It Does |
|--------|-------------|
| **autarch** | Interactive TUI surfaces — Bigend, Gurgeh, Coldwine, Pollard |

Every companion started as a tightly-coupled feature inside Clavain. Tight coupling is a feature during the research phase: build integrated, test under real use, extract when the pattern stabilizes enough to stand alone. The constellation represents crystallized research outputs. Each companion earned its independence through repeated, successful use.

## Model Routing

Model routing operates at three stages, each building on the one below:

**Stage 1: Kernel mechanism.** All dispatches flow through the kernel with an explicit model parameter. The kernel records which model was used, tracks token consumption, and emits events. *(Shipped.)*

**Stage 2: OS policy.** Plugins declare default model preferences. Clavain's routing table overrides per-project, per-run, or per-complexity-level. C1-C5 complexity classification drives model selection; not everything needs Opus. *(Shipped, static + complexity-aware routing.)*

**Stage 3: Adaptive optimization.** The agent fleet registry stores cost/quality profiles per agent×model combination. The composer optimizes the entire fleet dispatch within a budget constraint. "Run this review with $5 budget" → the composer allocates Opus to the 2 highest-impact agents and Haiku to the rest. Interspect's outcome data drives profile updates. *(Planned, where outcomes-per-dollar gets optimized.)*

## Adoption Ladder

Demarch is adoptable incrementally — one pillar at a time. Each step adds capability on top of the previous:

**Step 1: Interverse (one driver).** Install a single companion plugin (interflux for code review, tldr-swinton for code context). Works in vanilla Claude Code. No other pillars required.

**Step 2: Clavain (OS).** Install the OS pillar for the sprint workflow, quality gates, and brainstorm→ship lifecycle. Drivers are auto-discovered and integrated.

**Step 3: Intercore (kernel).** Install the kernel pillar for durable state. Runs, phases, gates, and events persist across sessions. Crash recovery. Audit trails.

**Step 4: Interspect (profiler).** Enable the profiler pillar. Agent routing improves based on outcome data. Gate rules tighten or relax based on evidence. The system starts learning.

**Step 5: Autarch (apps).** Install the apps pillar for interactive dashboards, PRD generation, and task orchestration.

Each step is optional. Step 1 is useful without Step 2. Step 2 is useful without Step 3. The stack rewards depth but doesn't demand it.
