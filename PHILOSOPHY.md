# Demarch Philosophy

The design bets, tradeoffs, and convictions that inform everything else.

CLAUDE.md says *how to work here*. AGENTS.md says *what to build and how*. This document says *why these tradeoffs and not others*.

Three principles, applied recursively:

1. **Every action produces evidence.** Receipts, not narratives. Durable, replayable, content-addressed.
2. **Evidence earns authority.** Trust is a dial. Each level requires proof from the previous level.
3. **Authority is scoped and composed.** Many small controllers with explicit scope. Composition over capability.

The cycle: authority enables actions → actions produce evidence → evidence earns authority. This is the flywheel stated at the philosophical level.

---

## The Core Bet

Four claims, all of which must be true for Demarch to be right:

1. **Infrastructure unlocks autonomy.** The bottleneck for agent capability is infrastructure (durability, coordination, feedback loops), not model intelligence. Better plumbing produces better agents.
2. **Review phases are where the leverage is.** Most agent tools skip brainstorm, strategy, and specification. The thinking phases are more valuable than the building phases.
3. **The flywheel compounds.** More autonomy produces more outcome data. More data improves routing and review. Better routing cuts cost. Lower cost enables more autonomy. The system that runs the most sprints learns the fastest.
4. **Efficiency and quality are not in tension.** Wasted tokens dilute context, increase hallucination risk, and slow feedback loops. A quality floor is non-negotiable; above it, route to the cheapest model that clears the bar.

If any of these claims is wrong, the project is misguided.

---

## Receipts Close Loops

*Principle 1 applied everywhere: every action produces evidence, and that evidence feeds back into the system.*

**Durability.** Every meaningful action produces a durable receipt (event + artifacts + evidence). If it didn't produce a receipt, it didn't happen. The goal behind durability is replayability — any sprint should be reconstructable from its receipts. You can't earn trust without proof.

**Measurement.** Instrument first, optimize later. Most agent systems have zero outcome feedback. Having any measurement is vastly better than none. Three sub-principles, in tension, all enforced simultaneously:
- *Outcomes over proxies.* Gate pass rates are gameable. Post-merge defect rates are not.
- *Rotate and diversify.* No single metric stays dominant. Diverse evaluation resists Goodhart pressure.
- *Anti-gaming by design.* Agents will optimize for any stable target. Rotate metrics, cap optimization rate, randomize audits. Goodhart pressure exists from day one.

**Disagreement.** Disagreement between models is the highest-value signal. Agreement is cheap (consensus bias). Disagreement drives the learning loop: disagreement at time T, human resolution at T+1, routing signal at T+2. Triage by impact: does resolving this change a decision? If yes, amplify. If no, apply default policy. When agents disagree with humans, the human wins in the moment — but receipts remember. Agents escalate high-confidence disagreements rather than silently comply.

**Failure.** Failures will happen. Every failure produces a receipt, no failure cascades unbounded, and every failure is replayable. Optimize for time-to-recovery, not mean-time-between-failures. Defense in depth: contracts, gates, multi-model review, human oversight, post-hoc measurement. Any single layer can fail. All five failing simultaneously is the real risk.

**Self-building.** Demarch builds itself with its own tools. This is simultaneously a design constraint (if Demarch can't build Demarch, the tools aren't good enough), a trust-earning mechanism (each cycle produces evidence for the trust ladder), and a transparency artifact (every decision is auditable via beads and review receipts). Agent friction IS the signal for technical debt — when agents hit the same problem across sessions, that's actionable.

**Documentation.** Docs are agent memory (persistent state across sessions), decision evidence (auditable receipts of brainstorms, plans, PRDs), and the product interface (CLAUDE.md is agent configuration, skill descriptions are agent capabilities). The quality of docs directly determines the quality of agent output. Stale documentation is silent technical debt — no single stale sentence breaks anything, but together they degrade every agent decision that depends on them. interwatch quantifies this: 14 signal types detect drift between project state and docs, scored into confidence tiers that drive graduated responses from report-only to auto-refresh. Making drift measurable makes the invisible visible.

**Technical debt.** *When* to care: before stabilization, debt is exploration cost; after, it's liability. Don't pay too early — cementing wrong abstractions is worse than messy scripts. *How* to pay: strangler-fig, never rewrite. Wrap old in new. *What* to pay first: whatever causes the most agent friction, surfaced by the self-building feedback loop.

---

## Earned Authority

*Principle 2 applied everywhere: trust is progressive, evidence-based, and never assumed.*

**Autonomy.** A dial, not a binary. The goal is human-above-the-loop — humans govern outcomes via receipts, not step-by-step supervision.

Progressive trust ladder:
- Level 0: Human approves every action.
- Level 1: Human approves at phase gates.
- Level 2: Human reviews evidence post-hoc.
- Level 3: Human sets policy, agent executes.
- Level 4: Agent proposes policy changes.
- Level 5: Agent proposes mechanism changes.

Currently operating at Level 1-2. Each level requires demonstrated safety at the previous level. No shortcuts. The kernel boundary (L1 cannot be modified by agents) is a trust threshold, not an architectural invariant — it softens as trust is earned, but through gated processes, not direct modification.

Note: this is the *human delegation* ladder — how much authority the human delegates. The vision doc's autonomy ladder (L0-L4: Record → Enforce → React → Auto-remediate → Auto-ship) tracks *system capability* — what the platform can do. The two are orthogonal and advance independently.

**Safety.** Structural, not moral. Demarch enforces structural constraints (bounded blast radius, auditable decisions, revocable authority) through architecture, not ethical reasoning. More autonomy means more responsibility to get safety right. The blast radius is scoped to the actual risk domain: wrong code committed, bad PRs merged, wasted tokens.

**Security.** The end state is capability-based, deny-by-default (Gridfire: unforgeable tokens with effects allowlists and resource bounds). Today it's pragmatic layered defense. The threat model prioritizes system boundaries: prompt injection, secret exfiltration, provenance laundering. Trust internal code; spend security budget at boundaries.

**Governance.** Polycentric: multiple independent evaluation authorities, no single judgment final. Today: different review agents assess different dimensions, Oracle provides cross-model checks, humans override. Tomorrow: multiple human operators with scoped authority, explicit conflict resolution. The architecture works for both solo and team use.

---

## Composition Over Capability

*Principle 3 applied everywhere: small, scoped, composed units beat large integrated ones.*

**Unix heritage.** Demarch is a spiritual successor to Unix. Keep: small tools, explicit interfaces, mechanism/policy separation. Replace: untyped streams, ambient authority, text-as-control, hidden state. The problems are fundamentally different (stochastic actors, partial state, trust boundaries everywhere), but composition beating capability is permanent.

**Agent architecture.** Many small agents with explicit scope over monolithic generalists. Route to the best model for the job — automated measurement determines which. Multi-model diversity is an epistemic hedge: different models have different blind spots, and disagreement is signal. Routing evolves from static tiers through complexity-aware to fully adaptive, where selection becomes empirical.

**Plugin ecosystem.** Keep splitting. Each plugin does one thing well. The right count is however many single-responsibility units exist. Growth is a feature. Plugins are dumb and independent (fail-open, standalone viable). The platform is smart and aware (recommends compositions, detects missing companions). Plugins declare capabilities; the platform composes them. Plugins are Actions with declared effects; the platform is the RunGraph.

**Complexity.** The problem IS complex. The goal isn't simplicity — it's managing essential complexity through boundaries, contracts, and composition. Accidental complexity is the enemy. Every addition draws from a complexity budget. Gridfire is the long-term paydown: replace many ad-hoc mechanisms with a few powerful primitives.

**Architecture.** The current decomposition (5 pillars, 3 layers) reflects where we are, not a permanent structure. The principles behind pillar boundaries are stable: separation of mechanism and policy, independence of UI from logic, pluggable capability ecosystem, closed-loop learning. The number of pillars is empirical. Gridfire may become a pillar. The principles decide, not tradition.

---

## Strong Defaults, Replaceable Policy

*Mechanism/policy separation applied to the product itself.*

**Opinions.** Strong opinions, loosely held. Ship with strong defaults (phase gates, review before merge, brainstorm before plan). Every opinion is a policy overlay that can be replaced. The mechanism enforces structure; opinions are defaults, not mandates. Overrides are always explicit and auditable. But the opinions ARE the product — without them, it's just infrastructure.

**Shipping.** The goal isn't more review — it's faster safe shipping. If review phases slow you down more than they catch bugs, the gates are miscalibrated. Match rigor to risk. Gates define "good enough," not human feelings in the moment. Move fast. Pre-1.0 means no stability guarantees. Premature stability commitments freeze wrong abstractions.

**Scope.** Software development is the first-class citizen. But the Gridfire primitives are not software-specific, and the system already does brainstorming, research, strategy, and documentation. Software dev is the proving ground; generalization follows once primitives are battle-tested.

**Host platform.** Claude Code first, multi-host near-term, host-agnostic long-term. Agent IDEs will commoditize. The value is in the infrastructure, not which editor runs the agents. The kernel doesn't know about Claude Code; the OS is a thin adapter.

---

## Naming

Names are compressed design arguments, not decoration.

The SF canon (Banks, Reynolds, Wolfe, Palmer, Gibson, Mieville) is the only literature that seriously explores governance, autonomy, identity, and systems thinking at scale — which is literally what Demarch builds. Demarch evokes governance, Clavain evokes leadership, Gridfire evokes paradigm-level infrastructure.

Two syllables. Feels right in your hands. You learn what they mean once; you feel what they mean every time you type them.

See [docs/guides/naming-conventions.md](docs/guides/naming-conventions.md) for the practical guide.

## End State

There is no "done." The flywheel doesn't converge — it compounds. There is no end state for learning.
