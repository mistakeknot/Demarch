# Sylveste Philosophy

The design bets, tradeoffs, and principles that guide how we build. See MISSION.md for why this project exists.

Three principles, applied recursively:

1. **Every action produces evidence.** Receipts, not narratives. Durable, replayable, content-addressed.
2. **Evidence earns authority.** Trust is a dial. Each level requires proof from the previous level.
3. **Authority is scoped and composed.** Many small controllers with explicit scope. Composition over capability.

The cycle: authority enables actions → actions produce evidence → evidence earns authority. This is the flywheel stated at the philosophical level.

---

## Operational Philosophy

These sections govern current build, review, routing, evidence, and authority behavior. They are the rules active agents should apply today.

### The Core Bet

Four claims, all of which must be true for Sylveste to be right:

1. **Infrastructure unlocks autonomy.** The bottleneck for agent capability is infrastructure (durability, coordination, feedback loops), not model intelligence. Better plumbing produces better agents.
2. **Review phases are where the leverage is.** Most agent tools skip brainstorm, strategy, and specification. The thinking phases are more valuable than the building phases.
3. **The flywheel compounds.** More autonomy produces more outcome data. More data improves routing and review. Better routing cuts cost. Lower cost enables more autonomy. The system that runs the most sprints learns the fastest.
4. **Efficiency and quality are not in tension.** Wasted tokens dilute context, increase hallucination risk, and slow feedback loops. A quality floor is non-negotiable; above it, route to the cheapest model that clears the bar.

If any of these claims is wrong, the project is misguided.

#### The OODARC Lens

The flywheel (authority → actions → evidence → authority) is an instance of **OODARC** — Observe, Orient, Decide, Act, Reflect, Compound — operating at nested timescales:

- **Per-turn:** Agent observes tool results, orients on context, decides next action, acts, reflects on the outcome, and compounds by updating working memory.
- **Per-sprint:** Phase gates observe artifacts, orient on sprint state, decide phase transitions, advance phases, reflect at sprint end, and compound by calibrating estimates and persisting learnings.
- **Cross-session:** Interspect observes evidence, orients via pattern classification, decides routing proposals, acts via override application, reflects via canary monitoring, and compounds by writing routing overrides that change future behavior.

OODARC extends Boyd's OODA loop with two phases, not one:

- **Reflect** extracts the lesson: what happened, what was expected, what differed. This is observation of one's own process — per-sprint, ephemeral until captured.
- **Compound** persists the lesson in a form that changes future behavior: calibration files that adjust estimates, routing overrides that reclassify agents, solution docs that prevent repeated mistakes. This is what closes the loop — without it, Reflect is journaling.

The distinction matters because Reflect without Compound is write-only learning (OODA with a diary). Compound without Reflect is cargo-culting (copying patterns without understanding why). The **Closed-loop by default** principle (below) is the operational implementation of Compound: the 4-stage calibration pattern (defaults → collect → calibrate → fallback) is how the C in OODARC feeds back into O (Orient) for the next cycle.

Situation assessments are prompt aids, not ground truth. Always verify recent evidence against cached assessments.

The runtime reinforcement of OODARC across the polyrepo — failing gates closed so Compound is trustworthy, naming the per-turn loop in the surface agents read, wiring `ic situation` as the shared Observe call, and reaching Codex/interserve parity — is tracked in `docs/plans/2026-06-20-oodarc-runtime-reinforcement-polyrepo.md`.

---

### Receipts Close Loops

*Principle 1 applied everywhere: every action produces evidence, and that evidence feeds back into the system.*

**Durability.** Every meaningful action produces a durable receipt (event + artifacts + evidence). If it didn't produce a receipt, it didn't happen. The goal behind durability is replayability — any sprint should be reconstructable from its receipts. You can't earn trust without proof.

**Measurement.** Instrument first, optimize later. Most agent systems have zero outcome feedback. Having any measurement is vastly better than none. Three sub-principles, in tension, all enforced simultaneously:
- *Outcomes over proxies.* Gate pass rates are gameable. Post-merge defect rates are not.
- *Rotate and diversify.* No single metric stays dominant. Diverse evaluation resists Goodhart pressure.
- *Anti-gaming by design.* Agents will optimize for any stable target. Rotate metrics, cap optimization rate, randomize audits. Goodhart pressure exists from day one.

**Closed-loop by default.** Any system that makes a judgment — estimates, classifications, routing decisions, triage scores, gate thresholds — MUST close the loop: predict, observe the outcome, feed the outcome back to improve the next prediction. Automatically, not manually. This is the mechanism by which receipts become intelligence rather than inert records. The implementation pattern has four stages, and shipping fewer than all four is incomplete work:

1. **Hardcoded defaults** — ship a reasonable starting point.
2. **Collect actuals** — instrument the real outcome alongside the prediction.
3. **Calibrate from history** — read past actuals to adjust future predictions.
4. **Defaults become fallback** — the hardcoded values still fire when history is absent.

If you ship stages 1-2 without 3-4, you've built a constant masquerading as intelligence. If you ship stage 3 without stage 4, you've built a system that breaks when the database is empty. The pattern applies everywhere predictions exist:

| Domain | Prediction | Actual | Calibration |
|---|---|---|---|
| Cost estimation | `phaseCostEstimate()` | interstat per-phase actuals | `calibrate-phase-costs` reads history |
| Agent routing | model tier selection | post-merge defect rate by model | interspect canary monitoring |
| Complexity scoring | `classifyComplexity()` | actual sprint duration/tokens | reflect-phase calibration |
| Review triage | agent relevance scores | which findings got acted on | interspect evidence → routing overrides |
| Gate thresholds | phase gate hardness | false-positive/negative rates | threshold tuning from outcomes |
| Fleet budgets | agent token estimates | interstat per-agent actuals | `scan-fleet.sh --enrich-costs` |
| Decomposition quality | predicted child count + complexity dist | actual children, completion rate, re-planning count | interspect `decomposition_outcome` events (N>=30 auto-trigger) |

The fleet enrichment pipeline is the existence proof: `estimate-costs.sh` reads historical actuals from interstat, blends them with registry baselines, and writes calibrated estimates back. Every other row in this table should work the same way.

**Wired or it doesn't exist.** Library code that isn't called from a runtime path is inventory, not capability. A function with tests but no callers is a liability — it passes CI, looks like progress, but delivers zero user value while accruing maintenance cost. The completion bar for any feature is: (1) the code exists and is tested, (2) it is wired into the runtime path that triggers it, (3) it emits evidence when it activates so we can observe it working, and (4) that evidence feeds back into calibration so it improves over time. Steps 1-2 are implementation. Steps 3-4 are the closed-loop pattern (above) applied to the feature itself. Shipping step 1 without steps 2-4 is the most common form of incomplete work in agent-built codebases — the agent writes clean code, the tests pass, the PR looks good, but the feature is dead on arrival because nothing invokes it and nothing measures it. The antidote is simple: every feature bead's acceptance criteria must include "where is it called from?" and "what evidence does it emit?"

**Disagreement.** Disagreement between models is the highest-value signal. Agreement is cheap (consensus bias). Disagreement drives the learning loop: disagreement at time T, human resolution at T+1, routing signal at T+2. Triage by impact: does resolving this change a decision? If yes, amplify. If no, apply default policy. When agents disagree with humans, the human wins in the moment — but receipts remember. Agents escalate high-confidence disagreements rather than silently comply.

**Failure.** Failures will happen. Every failure produces a receipt, no failure cascades unbounded, and every failure is replayable. Optimize for time-to-recovery, not mean-time-between-failures. Defense in depth: contracts, gates, multi-model review, human oversight, post-hoc measurement. Any single layer can fail. All five failing simultaneously is the real risk.

**Self-building.** Sylveste builds itself with its own tools. This is simultaneously a design constraint (if Sylveste can't build Sylveste, the tools aren't good enough), a trust-earning mechanism (each cycle produces evidence for the trust ladder), and a transparency artifact (every decision is auditable via beads and review receipts). Agent friction IS the signal for technical debt — when agents hit the same problem across sessions, that's actionable.

**Documentation.** Docs are agent memory (persistent state across sessions), decision evidence (auditable receipts of brainstorms, plans, PRDs), and the product interface (CLAUDE.md is agent configuration, skill descriptions are agent capabilities). The quality of docs directly determines the quality of agent output. Stale documentation is silent technical debt — no single stale sentence breaks anything, but together they degrade every agent decision that depends on them. interwatch quantifies this: 14 signal types detect drift between project state and docs, scored into confidence tiers that drive graduated responses from report-only to auto-refresh. Making drift measurable makes the invisible visible.

**Technical debt.** *When* to care: before stabilization, debt is exploration cost; after, it's liability. Don't pay too early — cementing wrong abstractions is worse than messy scripts. *How* to pay: strangler-fig, never rewrite. Wrap old in new. *What* to pay first: whatever causes the most agent friction, surfaced by the self-building feedback loop.

---

### Earned Authority

*Principle 2 applied everywhere: trust is progressive, evidence-based, and never assumed.*

**Autonomy.** A dial, not a binary. The goal is human-above-the-loop — humans govern outcomes via receipts, not step-by-step supervision. Authority is delegated progressively along the L0–L5 trust ladder, and each level requires demonstrated safety at the previous one. No shortcuts.

The kernel boundary (L1 cannot be modified by agents) is a trust threshold, not an architectural invariant — it softens as trust is earned, but through gated processes, not direct modification.

> **Definitions live in [`docs/canon/autonomy.md`](docs/canon/autonomy.md)** — the L0–L5 delegation ladder and the current position on it, the M0–M4 capability mesh, phase chains, and discovery confidence tiers. That page also records why these four scales are orthogonal, and which terms only look like levels. Cite it rather than restating any of them here.

**Graduated authority as mechanism.** Capability is tracked per subsystem on an ordinal maturity scale (M0–M4). Promotion requires pre-specified evidence thresholds. Demotion is triggered by sustained regression indicators exceeding threshold for a defined observation window. Evidence epochs reset trust when environmental conditions shift (major model changes, architecture migrations, subsystem replacements). The principle (evidence earns authority) is permanent. The mechanism (specific thresholds, epoch triggers, demotion criteria) is revisable by human authority regardless of accumulated evidence — the right to redefine trust criteria remains with humans.

**Safety.** Structural, not moral. Sylveste enforces structural constraints (bounded blast radius, auditable decisions, revocable authority) through architecture, not ethical reasoning. More autonomy means more responsibility to get safety right. The blast radius is scoped to the actual risk domain: wrong code committed, bad PRs merged, wasted tokens.

**Security.** The end state is capability-based, deny-by-default (Gridfire: unforgeable tokens with effects allowlists and resource bounds). Today it's pragmatic layered defense. The threat model prioritizes system boundaries: prompt injection, secret exfiltration, provenance laundering. Trust internal code; spend security budget at boundaries.

**Governance.** Polycentric: multiple independent evaluation authorities, no single judgment final. Today: different review agents assess different dimensions, Oracle provides cross-model checks, humans override. Tomorrow: multiple human operators with scoped authority, explicit conflict resolution. The architecture works for both solo and team use.

---

### Composition Over Capability

*Principle 3 applied everywhere: small, scoped, composed units beat large integrated ones.*

**Unix heritage.** Sylveste is a spiritual successor to Unix. Keep: small tools, explicit interfaces, mechanism/policy separation. Replace: untyped streams, ambient authority, text-as-control, hidden state. The problems are fundamentally different (stochastic actors, partial state, trust boundaries everywhere), but composition beating capability is permanent.

**Agent architecture.** Many small agents with explicit scope over monolithic generalists. Route to the best model for the job — automated measurement determines which. Multi-model diversity is an epistemic hedge: different models have different blind spots, and disagreement is signal. Routing evolves from static tiers through complexity-aware to fully adaptive, where selection becomes empirical.

**Sparse topology in multi-agent collaboration.** Fully-connected agent networks converge faster but to worse answers (Zollman effect — epistemic network theory). Default to sparse or ring topologies for multi-agent review and discourse. The diversity cost of full connectivity is real: agents anchored on each other's output collapse to consensus before exploring the solution space. Shift to full connectivity only when rapid convergence is explicitly worth the diversity cost, or when subsystem maturity is low enough (M0-M1) that information sharing matters more than independent exploration.

**Plugin ecosystem.** Keep splitting. Each plugin does one thing well. The right count is however many single-responsibility units exist. Growth is a feature. Plugins declare capabilities; the platform composes them. Plugins are Actions with declared effects; the platform is the RunGraph.

Plugins exist in two tiers:

- **Standalone plugins** (default): Fail-open, degrade gracefully without intercore. Value proposition is self-contained. The platform recommends compositions and detects missing companions, but no plugin requires another to function. Examples: interlens, interlock, interkasten, tldr-swinton.
- **Kernel-native plugins**: May require intercore as a hard dependency. These are extensions of kernel subsystems — their value IS the kernel integration. Forcing standalone mode would create parallel stores that diverge, which is worse than the dependency. Examples: interject (discovery inflow), interspect (evidence pipeline), interphase (sprint discovery).

Criteria for kernel-native designation:
1. Plugin feeds or consumes a kernel subsystem (discovery, events, dispatch, runs).
2. Standalone mode would require duplicating kernel state into a local store.
3. The plugin's downstream consumers (routing, events, gates) depend on kernel integration.

The bar is high — kernel-native is earned by architectural role, not convenience. Most plugins should be standalone. When in doubt, standalone wins.

**External tools.** Adopt mature external tools as dependencies rather than rebuilding them. If a tool is well-maintained, useful, and not worth reinventing, install the binary and call it from Sylveste — the same way `bd` (beads) works today. The verdict tiers are: adopt (wire in directly), port-partially (extract patterns or algorithms), inspire-only (borrow design ideas), skip. Source doesn't matter — evaluate the tool, not the contributor. Rebuilding a working tool is accidental complexity; composing with it is the Unix way.

**Complexity.** The problem IS complex. The goal isn't simplicity — it's managing essential complexity through boundaries, contracts, and composition. Accidental complexity is the enemy. Every addition draws from a complexity budget. Gridfire is the long-term paydown: replace many ad-hoc mechanisms with a few powerful primitives.

**Architecture.** The current decomposition (6 pillars, 3 layers) reflects where we are, not a permanent structure. The principles behind pillar boundaries are stable: separation of mechanism and policy, independence of UI from logic, pluggable capability ecosystem, closed-loop learning. The number of pillars is empirical. Gridfire may become a pillar. The principles decide, not tradition.

---

## Roadmap Philosophy

These sections describe longer-horizon doctrine and roadmap-shaping decisions. They guide direction without overriding the operational rules above.

### Memory Architecture

*Composition applied to knowledge: many scoped stores with explicit boundaries, unified through retrieval, not migration.*

Sylveste has 10 memory-shaped systems across 3 layers. Each was built to solve a specific problem. The taxonomy below prevents future systems from creating yet another knowledge store without checking if an existing category fits.

#### Five Categories

| Category | Name | What it holds | Owner | Decay model |
|----------|------|---------------|-------|-------------|
| C1 | Operational State | Run state, dispatches, sprints, locks, sessions | Intercore kernel | TTL-based (30d for completed runs) |
| C2 | Evidence & Calibration | Agent accuracy, canary windows, routing calibration, feedback signals | Interspect + Interject | Rolling window (90d evidence, 14d canary) |
| C3 | Learned Preferences | Interest profiles, voice profiles, source weights | Plugin-local | Exponential moving average (existing) |
| C4 | Curated Knowledge | Human-validated patterns, solutions, reference material | docs/solutions/ | Provenance-based (10-review + 180d staleness) |
| C5 | Ephemeral Context | Per-session working memory, auto-memory, cache blobs | Plugin-local filesystem | Intermem promotion model (14d grace + decay) |

#### Decision Rule

When a new piece of memory needs a home:

- Is it about current system status? → **C1** (kernel)
- Is it an observation about agent/system behavior? → **C2** (evidence)
- Is it a learned model parameter? → **C3** (plugin-local)
- Is it a human-validated pattern or solution? → **C4** (docs/solutions/)
- Is it a working note that might become permanent? → **C5** (auto-memory → intermem promotion)

#### Design Decisions

**Unify retrieval, not storage.** The real problem is fragmented read paths, not fragmented stores. A thin retrieval layer that queries across systems and returns ranked, deduplicated results solves discoverability without migration risk. Each system keeps its storage.

**Intermem's decay model is the standard.** Grace period + linear decay + hysteresis. Systems without decay adopt this pattern rather than inventing their own. Intermem already solved false-positive demotion prevention and crash recovery.

**Learned preferences stay plugin-local.** C3 models (interest profiles, voice profiles) are ML parameters specific to each plugin's domain. The kernel provides the evidence (C2) that feeds these models, but the models themselves don't need kernel-level treatment. No other system needs to read them.

**Curated knowledge converges.** Multiple C4 stores (interknow, compound docs) converge into a single write path and read path, with shared provenance metadata. The goal is one place to look for validated engineering knowledge, not three.

See `docs/prds/2026-03-07-memory-architecture-convergence.md` for the full system map, per-system recommendations, and implementation sequence.

---

### Strong Defaults, Replaceable Policy

*Mechanism/policy separation applied to the product itself.*

**Opinions.** Strong opinions, loosely held. Ship with strong defaults (phase gates, review before merge, brainstorm before plan). Every opinion is a policy overlay that can be replaced. The mechanism enforces structure; opinions are defaults, not mandates. Overrides are always explicit and auditable. But the opinions ARE the product — without them, it's just infrastructure.

**Shipping.** The goal isn't more review — it's faster safe shipping. If review phases slow you down more than they catch bugs, the gates are miscalibrated. Match rigor to risk. Gates define "good enough," not human feelings in the moment. Move fast. Pre-1.0 means no stability guarantees. Premature stability commitments freeze wrong abstractions.

**Scope.** Software development is the first-class citizen. But the Gridfire primitives are not software-specific, and the system already does brainstorming, research, strategy, and documentation. Software dev is the proving ground; generalization follows once primitives are battle-tested.

**Host platform.** Claude Code first, multi-host near-term, host-agnostic long-term. Agent IDEs will commoditize. The value is in the infrastructure, not which editor runs the agents. The kernel doesn't know about Claude Code; the OS is a thin adapter.

---

### Naming

Names are compressed design arguments, not decoration.

The SF canon (Banks, Reynolds, Wolfe, Palmer, Gibson, Mieville) is the only literature that seriously explores governance, autonomy, identity, and systems thinking at scale — which is literally what Sylveste builds. The project was originally named Demarch (Reynolds' Demarchists — Democratic Anarchists), evoking governance. It was renamed to Sylveste (Dan Sylveste, Reynolds' Revelation Space protagonist) in March 2026 when namespace collision checks confirmed zero conflicts across all registries. Clavain evokes leadership, Gridfire evokes paradigm-level infrastructure.

Two syllables. Feels right in your hands. You learn what they mean once; you feel what they mean every time you type them.

See [docs/guides/naming-conventions.md](docs/guides/naming-conventions.md) for the practical guide.

#### Brand Architecture

The launch-facing Sylveste surface stays in the SF/infrastructure register: Clavain, Skaffen, Intercore, Interspect, Autarch, Interverse, and the `inter-*` capability layer. Internal product-family boundaries and launch-suppression rules live in [docs/canon/brand-architecture.md](docs/canon/brand-architecture.md). Do not reintroduce Garden Salon or Meadowsyn into public Sylveste launch copy until their own surfaces are ready.

### End State

There is no "done." The flywheel doesn't converge — it compounds. There is no end state for learning.
