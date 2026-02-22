# Interspect — Vision

**Version:** 1.0
**Date:** 2026-02-22
**Status:** Draft
**Implementation detail:** [core/intercore/docs/product/interspect-vision.md](../core/intercore/docs/product/interspect-vision.md)

---

## The Problem

Agent systems don't learn. They ship. They review. They test. They advance through phases. And then the next sprint starts from scratch, with exactly the same configuration, the same routing, the same gate thresholds, the same blind spots.

When a human dismisses a false positive from fd-safety for the third time, information is created and then lost. When Opus produces the same quality as Haiku on a simple review but costs 30x more, nobody notices. When a gate always passes, nobody asks whether it's still worth running. The evidence exists in the event stream; nothing reads it.

Interspect reads it.

## What Interspect Is

The cross-cutting profiler for the Demarch stack. It sits alongside the three architectural layers (kernel, OS, apps) and does one thing: turn outcome data into system improvements.

Concretely: Interspect reads the kernel's event stream, correlates what happened with what should have happened, and proposes changes to OS-level configuration. Model routing adjustments. Agent exclusions. Gate threshold changes. Context overlays that tune agent behavior for specific projects. All proposed as safe, reversible overlays that a human (or, eventually, a shadow evaluation) approves before they take effect.

Interspect never modifies the kernel. It never edits canonical agent prompts. It never changes its own safety infrastructure. These are mechanical constraints, not policy statements.

## Why It Matters

Static orchestration is table stakes. Any system can dispatch agents and enforce gates. The system that gets cheaper and better over time is the one worth building.

Demarch advances three axes (autonomy, quality, token efficiency) connected by a flywheel. Interspect is that flywheel. Without it, the three axes are just three independent metrics. With it, they compound:

- Model downgrades where Haiku catches the same issues as Opus → **cheaper**
- Agent retirement where a reviewer consistently produces findings no one acts on → **less noise**
- Gate relaxation where a check always passes → **faster**
- Context overlays that reduce false positives for a specific codebase → **more signal**

Each optimization simultaneously increases autonomy (less human calibration needed), improves quality (resources reallocated to where they matter), and reduces cost (less waste). The system that ships the most sprints learns the fastest, and the system that learns the fastest ships the cheapest.

## The Signal Taxonomy

Interspect learns from two categories of signal, and the mix shifts as autonomy increases.

### Human signals (high-fidelity, expensive)

These require a human to evaluate agent output. They're the richest source of ground truth but they don't scale.

| Signal | Source | What It Tells Interspect |
|--------|--------|--------------------------|
| Review dismissals | Human rejects a finding during `/resolve` | The finding was noise for this context |
| Gate overrides | Human forces past a failed gate | The gate condition is too strict or irrelevant |
| Manual corrections | `/interspect:correction` command | An agent got something specific wrong |
| Proposal acceptance/rejection | Human accepts or rejects an Interspect overlay | Whether the proposed improvement was actually an improvement |

At low autonomy levels (L0-L2), human signals are the primary feedback channel. The human reviews every phase transition, evaluates every finding, and Interspect captures each evaluation.

### Automated signals (lower-fidelity, scales without humans)

These come from the system itself. No human in the loop required.

| Signal | Source | What It Tells Interspect |
|--------|--------|--------------------------|
| CI results | Test suite pass/fail after agent changes | Whether the agent's work actually works |
| Build failures | Compilation errors post-implementation | Agent produced syntactically or structurally broken code |
| Revert frequency | `git revert` of agent-produced commits | The change was bad enough to undo |
| Runtime errors | Exceptions or panics in deployed code | Defects escaped all gates |
| Gate pass rate | Kernel event stream | Whether gates are too strict, too loose, or well-calibrated |
| Token consumption | Kernel dispatch records | Whether model routing is cost-efficient |
| Finding density | Agent output volume vs actionable findings | Whether an agent is producing signal or noise |
| Sprint completion rate | Kernel run lifecycle events | Whether sprints finish or get abandoned |

At higher autonomy levels (L3-L4), automated signals become the primary channel. The human sets policy ("auto-remediate gate failures," "auto-ship when confidence thresholds are met") and Interspect learns from what happens next. Did the auto-remediation fix the problem? Did the auto-shipped change survive production? These are machine-readable outcomes that don't require human attention per event.

### The handoff

The transition from human-heavy to automated-heavy signals is not a cliff. It's a gradient:

- **L0-L1:** Almost entirely human signals. Interspect is an observer.
- **L2:** Human signals plus gate pass rates and finding density. Interspect starts detecting patterns.
- **L3:** Automated signals dominate. Human signals come from exceptions and periodic reviews. Interspect proposes configuration changes.
- **L4:** Automated signals almost exclusively. Human signals come from policy-level reviews (weekly or monthly). Interspect runs shadow evaluations before applying changes.

The key insight: automated signals don't replace human signals. They provide a different kind of ground truth. CI failures tell you "this broke." Human dismissals tell you "this was irrelevant." Both are needed. At higher autonomy, there are simply fewer opportunities for human signals because fewer decisions pass through human review. Interspect compensates by leaning harder on outcome-based signals (did the code work? did the change survive?) rather than evaluation-based signals (did the human approve?).

## How It Works

### Phase 1: Evidence (shipped)

Interspect collects evidence in a SQLite database (`.clavain/interspect/interspect.db`, WAL mode). Session lifecycle hooks capture start/end events. The `/resolve` workflow captures dismissals. The `/interspect:correction` command captures explicit human corrections. Four reporting commands let the user inspect what's been collected and what patterns have emerged.

No modifications. Just observation. The user can answer "what changed and why" in 10 seconds.

### Phase 2: Overlays (next)

Safe, reversible modifications via an overlay system. Two types:

**Context overlays.** Feature-flag files layered onto agent prompts at runtime. "This project uses parameterized queries; stop flagging SQL injection." Rollback is instant: disable the overlay.

**Routing overrides.** Per-project agent exclusions via toggle artifacts. fd-safety produces no actionable findings on this Go CLI project? Exclude it from the review fleet for this project, not globally.

All modifications go through propose mode by default. Counting-rule thresholds gate proposals: at least 3 sessions, at least 2 projects, at least N events of the same pattern. Simple, debuggable, no opaque weighted formulas.

Canary monitoring watches each active overlay across a 20-use window, tracking three metrics (override rate, false positive rate, finding density) against a rolling baseline. On degradation: alert. Not auto-revert. The human decides.

### Phase 3: Autonomy (planned)

Earned through data. Counterfactual shadow evaluation runs candidate changes on real traffic before they auto-apply. Changes must win in shadow eval, not just pass a threshold. Privilege separation splits the system into an unprivileged proposer (can only write to a staging directory) and a privileged applier (enforces an allowlisted patch format). The proposer literally cannot write to the repo.

Prompt tuning (overlay-based, not direct edits) requires a real eval corpus built from production reviews. No eval corpus, no prompt tuning. Rare agents stay in propose-only mode permanently because there isn't enough data to validate changes.

## Design Principles

### Observe before acting

Phase 1 collects evidence before any modifications are proposed. The product ships value (observability, debugging UX) before it ships risk (modifications). Not caution for its own sake, but the mechanism that validates which signals are actually useful before betting on them.

### Overlays, not rewrites

Canonical agent prompts are never directly edited. Changes are layered via feature-flag overlays that can be toggled independently. Instant rollback. A/B testability. Upstream mergeability. No long-lived prompt forks.

### The safety infrastructure is not the system's to modify

Meta-rules are human-owned. The counting rules, canary thresholds, protected paths, and judge prompts are mechanically enforced. Privilege separation ensures the proposer cannot write to the repo; only the allowlisted applier can. Interspect can improve agents, but it cannot improve (or degrade) itself.

### Measure what matters, not what's easy

Override rate alone is a trap (Goodhart's Law). Three metrics cross-check each other: override rate, false positive rate, and finding density. Galiana's defect escape rate provides an independent recall signal. When metrics conflict, conservatism wins.

### Evidence compounds; assumptions don't

Counting-rule thresholds are simple and debuggable. No weighted formulas until real data proves they add value. Prompt tuning requires a real eval corpus, not synthetic tests. Capabilities are deferred not because they're bad ideas but because there's no evidence they're needed yet.

## What Interspect Is Not

- **Not AGI self-improvement.** It layers overlays onto specific agents. It does not modify itself or its own safety infrastructure.
- **Not a replacement for human judgment.** Propose mode is the default because humans are better at evaluating agent quality than agents are. Interspect reduces the toil of manually tuning agents, not the responsibility.
- **Not autonomous by default.** Every deployment starts in evidence-collection-only mode. Autonomy is earned through data, not assumed by design.
- **Not prompt rewriting.** Canonical agent prompts are upstream artifacts. Interspect layers overlays; it never edits the source.

## Where We Are

Phase 1 is shipped. Evidence collection is operational across 14 projects. The SQLite schema supports evidence, sessions, canary monitoring, and modification tracking. Four reporting commands are functional. Session lifecycle hooks capture start/end events. The `/interspect:correction` command captures explicit human corrections.

Phase 2 (overlays + canary alerting) is designed and beaded. Phase 3 (autonomy + eval corpus) is designed. The Oracle review (GPT-5.2 Pro) validated the observability-first approach and informed several design simplifications: dropping session-scoped modifications, replacing weighted confidence with counting rules, switching from auto-revert to alert-only canaries, and adding privilege separation.

## Success Metrics

| Horizon | What Success Looks Like |
|---------|------------------------|
| Phase 1 (now) | User can debug agent behavior in 10 seconds. Evidence collection covers all review agents. |
| Phase 2 | Override rate decreasing. >80% proposal acceptance rate. <10% canary alert rate. |
| Phase 3 | Eval corpus covers >=3 agent domains. Shadow testing operational. Privilege separation enforced. |
| Long-term | Model routing accuracy improving quarter over quarter. Cost per landable change declining. Interspect proposals that improve metrics when applied >70%. |

---

*Implementation detail (SQLite schema, overlay file format, hook integration, command reference): [core/intercore/docs/product/interspect-vision.md](../core/intercore/docs/product/interspect-vision.md). Roadmap and bead tracking: [core/intercore/docs/product/interspect-roadmap.md](../core/intercore/docs/product/interspect-roadmap.md).*
