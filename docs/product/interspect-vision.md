# Interspect — Vision Document

**Version:** 2.0 (post-Oracle review)
**Date:** 2026-02-15
**PRD:** `docs/product/interspect-prd.md`
**Roadmap:** `docs/product/interspect-roadmap.md`
**Oracle review:** `docs/research/oracle-interspect-review.md`

---

## The Core Idea

Every time a human overrides a code review finding, dismisses a false positive, or manually corrects an agent's output, information is created and then lost. Interspect captures that information and turns it into systematic improvement.

Clavain dispatches agents. Agents produce findings. Humans evaluate findings. Today, the evaluation signal evaporates. Tomorrow, with Interspect, it compounds.

## Where We Are

Clavain is a multi-agent rig that orchestrates code review, planning, debugging, and shipping workflows. It routes work to specialized agents (fd-architecture, fd-safety, fd-correctness, etc.) and synthesizes their outputs. It works. But it doesn't learn.

The agents are static. Their prompts are handcrafted. Their routing is rule-based. When an agent produces a false positive, the human dismisses it and moves on. When the same false positive recurs three sessions later, the human dismisses it again. The system has no memory of its mistakes.

## Where We're Going

### v1: Observability + Safe Overlays

Interspect v1 is an **observability platform first, modification engine second.** The product is visibility into agent performance. Modification is a feature of the platform, not the platform itself.

**Phase 1** closes the simplest loop: **observe agent performance, detect patterns, surface actionable insights.** No modifications. The user can answer "what changed and why" in 10 seconds.

**Phase 2** adds safe, reversible modifications via an **overlay system** — not direct prompt editing:
1. **Context overlays** — Feature-flag files layered onto agent prompts at runtime ("this project uses parameterized queries, stop flagging SQL injection"). Rollback = disable the overlay.
2. **Routing overrides** — Per-project agent exclusions via toggle artifacts. No prompt changes required.
3. **Prompt tuning** (propose-only, requires eval corpus) — Overlay-based additions to agent behavior, gated behind a real evaluation suite built from production reviews.

**Phase 3** earns autonomy through data: counterfactual shadow evaluation on real traffic before any change auto-applies, privilege separation between an unprivileged proposer and a privileged applier, and eval corpus as a hard prerequisite for prompt modifications.

The safety model is conservative: propose mode by default, canary monitoring that **alerts on degradation** (not auto-reverts), counting-rule thresholds that are debuggable and explainable, and protected paths for safety infrastructure. Canonical agent prompts are never directly edited — changes are always layered via overlays that can be instantly toggled off.

This is not AI improving itself. This is a feedback system that turns human evaluations into agent improvements, with the human in the loop at every decision point.

### v2: Closing More Loops

Once v1 proves the evidence-to-improvement pipeline works:

- **Skill rewriting** — Restructure entire skills (not just prompts) when evidence shows systematic issues
- **Workflow optimization** — Adjust agent dispatch timing, parallelization, and model selection based on cost/quality data
- **Bandit learning for routing** — Replace counting rules with contextual bandit policies that handle non-stationarity and project-specificity gracefully
- **Cross-model evaluation** — Use GPT-5.2 Pro (Oracle) as an independent judge for shadow testing, eliminating the self-referential bias of Claude evaluating Claude
- **Outcome-first evidence** — Expand beyond overrides/dismissals to downstream signals: test failures introduced vs avoided, CI deltas, defect escapes, time-to-resolution

### v3: Intrinsic Metacognition

The long-term vision — informed by the ICML 2025 position paper on metacognitive learning — is an agent system that doesn't just improve its outputs but improves its improvement process.

Today's Interspect is "extrinsic metacognition": a human-designed OODA loop with fixed cadences, thresholds, and safety gates. v3 would allow the loop itself to evolve:

- Confidence thresholds calibrated continuously, not manually reviewed every 90 days
- Evidence collection strategies that adapt (adding new signal types when existing ones prove insufficient)
- Safety gates that scale with demonstrated track record (not just time-based)

This requires solving the reflexive control loop problem: ensuring the system can't degrade the signals it uses to evaluate its own performance. The protected paths manifest and privilege separation are the v1 answer. A formal verification approach (inspired by the "Guaranteed Safe AI" framework) would be the v3 answer.

## Design Principles

### 1. Observe Before Acting
Phase 1 collects evidence for 4 weeks before any modifications are proposed. The product ships value (observability, debugging UX) before it ships risk (modifications). Autonomy is opt-in, earned through demonstrated quality, and instantly revocable.

### 2. Overlays, Not Rewrites
Canonical agent prompts are never directly edited. Changes are layered via feature-flag overlays that can be toggled independently. This means instant rollback (disable overlay, not git revert), A/B testability (toggle overlays), and upstream mergeability (no long-lived prompt forks).

### 3. The Safety Infrastructure is Not the System's to Modify
Meta-rules are human-owned. The counting rules, canary thresholds, protected paths, and judge prompts are mechanically enforced — not policy statements. Privilege separation ensures the proposer literally cannot write to the repo; only the allowlisted applier can. Interspect can improve agents, but it cannot improve (or degrade) itself.

### 4. Measure What Matters, Not What's Easy
Override rate alone is a trap (Goodhart's Law). Three metrics — override rate, false positive rate, and finding density — cross-check each other. Galiana's defect escape rate provides an independent recall signal. Counterfactual shadow evaluation builds paired comparison datasets before changes go live. When metrics conflict, conservatism wins.

### 5. Evidence Compounds; Assumptions Don't
Phase 1 collects evidence for 4 weeks before any modifications are attempted. Counting-rule thresholds are simple and debuggable — no weighted formulas until real data proves they add value. Type 3 (prompt tuning) requires a real eval corpus, not synthetic tests. Types 4-6 are deferred not because they're bad ideas but because there's no evidence they're needed yet.

## The Broader Context

The AI agent ecosystem (2025-2026) is converging on self-improvement:
- **SICA** achieves 17-53% gains via agent source code self-editing
- **Darwin Godel Machine** evolves agents from 20% to 50% on SWE-bench
- **Devin** improved from 34% to 67% PR merge rate over 18 months
- **NVIDIA LLo11yPop** uses OODA loops for datacenter agent optimization

But safety lags capability. No production system has solved the reflexive control loop. The Cursor RCE advisory demonstrated that agent write-access to git config/hooks creates real attack surface. Anthropic's own research on browser-use prompt injection shows that once an agent processes untrusted content, the attack surface explodes.

Interspect's contribution is not inventing a new algorithm. It's building the disciplined evidence-to-improvement pipeline with safety gates that actually work — privilege separation over policy enforcement, overlays over rewrites, counting rules over opaque formulas, alerting over auto-revert — in a real production system, not a benchmark. If Clavain can demonstrate that observability-driven agent improvement works safely in practice, the patterns generalize.

## Success at Each Horizon

| Horizon | Timeframe | What Success Looks Like |
|---------|-----------|------------------------|
| v1 | 3-6 months | Override rate decreasing, >80% proposal acceptance, <10% canary alert rate, user can debug agent behavior in 10 seconds |
| v2 | 6-12 months | Eval corpus covers 80% of agent domains, cross-model shadow testing operational, bandit routing outperforming static rules |
| v3 | 12-24 months | Self-calibrating thresholds, adaptive evidence collection, formal verification of safety invariants |

## What This Is Not

- **Not AGI self-improvement.** Interspect layers overlays onto a specific set of code review agents. It does not modify itself or its own safety infrastructure.
- **Not a replacement for human judgment.** Propose mode is the default because humans are better at evaluating agent quality than agents are. Interspect reduces the toil of manually tuning agents, not the responsibility.
- **Not an autonomous system by default.** Every deployment starts in evidence-collection-only mode. Autonomy is earned through data, not assumed by design.
- **Not prompt rewriting.** Canonical agent prompts are upstream artifacts. Interspect layers overlays; it never edits the source.
