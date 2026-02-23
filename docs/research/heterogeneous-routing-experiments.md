# Heterogeneous Agent Routing: Experiment Design

**Bead:** iv-jc4j
**Date:** 2026-02-23
**Prerequisites:** iv-qznx (benchmark harness, shipped), iv-dthn (feedback loops, shipped)

## Context

Demarch has three routing systems:
1. **Static routing** (`routing.yaml` + `lib-routing.sh`) — phase→model mapping, shipped as B1
2. **Agent scoring** (flux-drive protocol) — domain-aware 0-7 scoring, shipped
3. **Interspect overrides** — evidence-driven exclusions, collecting but not yet applying

All three are essentially **homogeneous per task type**: every review gets Sonnet, every research agent gets Haiku, every brainstorm gets Opus. This is safe but wasteful — some reviews are trivial (Haiku could handle them) and some research tasks are complex (need Sonnet).

## SC-MAS / Dr. MAS Inspiration

**SC-MAS** (Self-Coordinating Multi-Agent Systems): agents self-assign roles based on capability matching. No central dispatcher — agents bid on subtasks.

**Dr. MAS** (Dynamic Role Multi-Agent Systems): a meta-agent dynamically assigns model/role per task chunk based on estimated complexity and cost. Roles include: Planner (high capability), Editor (medium), Reviewer (medium-high), Checker (low).

**Key insight from both:** heterogeneous teams outperform homogeneous teams on complex tasks, but homogeneous teams are more predictable on routine tasks. The routing policy should be task-aware, not agent-aware.

## Experiment Design

### Experiment 1: Task-Complexity-Aware Model Selection

**Hypothesis:** Routing agents to model tiers based on per-task complexity (not per-phase defaults) reduces cost 30-50% with <5% quality degradation.

**Setup:**
- Use the complexity classifier from `lib-routing.sh` (C1-C5 tiers, currently mode=off)
- Enable B2 complexity routing on a subset of flux-drive reviews
- Compare against B1 static baseline (all review agents → Sonnet)

**Protocol:**
1. Run 20 flux-drive reviews with B1 (static Sonnet) — establish baseline quality + cost
2. Enable B2 complexity routing for the same 20 codebases
3. Measure: pass rate, unique finding rate per agent, cost per review, retry rate

**Thresholds (from iv-dthn):**
- Quality floor: normalized score > 0.7 (else revert to B1)
- Retry rate: < 15% (else over-optimized)
- Haiku task success: must be > 85% for task types routed to Haiku

**Metrics:**
| Metric | B1 Baseline | B2 Target |
|--------|------------|-----------|
| Cost per review | $X (measure) | 30-50% less |
| Quality score | baseline | within 5% |
| Retry rate | baseline | < 15% increase |
| Unique finding rate | baseline | maintained |

### Experiment 2: Role-Aware Collaboration Topology

**Hypothesis:** Assigning explicit roles (Planner, Editor, Reviewer, Checker) to agents with matched model capability reduces redundant work by 20%+.

**Setup:**
- Define 4 roles: Planner (Opus), Editor (Sonnet), Reviewer (Sonnet), Checker (Haiku)
- Map flux-drive agents to roles by concern:
  - fd-architecture, fd-systems → Planner (architectural decisions need high capability)
  - fd-correctness, fd-quality, fd-safety → Reviewer (detailed checking)
  - fd-performance, fd-user-product → Editor (practical suggestions)
  - fd-perception, fd-resilience → Checker (pattern matching, lower complexity)

**Protocol:**
1. Run 10 reviews with current homogeneous Sonnet assignment
2. Run 10 reviews with role-aware model assignment
3. Compare: finding overlap rate, unique findings per role, total cost

**Key risk (from iv-dthn Loop 4):** AgentDropout interaction — if Checker-role agents get Haiku and miss findings, the coverage gap may not be detected until calibration window passes.

**Guardrail:** Shadow mode first — run role-aware routing alongside homogeneous, compare outputs without acting on differences. Minimum 20 reviews before any production switch.

### Experiment 3: Collaboration Mode Comparison

**Hypothesis:** Staged collaboration (Stage 1 core → Stage 2 expansion) outperforms parallel-all on cost-efficiency while matching quality.

**Current state:** Flux-drive already implements staged dispatch (score-based Stage 1/2). This experiment varies the staging strategy.

**Modes to test:**
| Mode | Description | Expected Profile |
|------|------------|-----------------|
| Parallel-all | Launch all agents simultaneously | Highest quality, highest cost, fastest |
| Sequential | Each agent sees previous agents' findings | Lowest redundancy, slowest, dependency chains |
| Staged (current) | Stage 1 core, Stage 2 expansion | Balanced |
| Adaptive staged | Stage 2 only launches if Stage 1 found issues | Lowest cost, risk of missed findings |

**Protocol:**
- Use interbench to capture runs for each mode on 5 diverse codebases
- Score using framework_score.py (Pareto ranking: quality vs cost vs latency)

### Experiment 4: Cost-Quality Pareto Frontier

**Hypothesis:** There exists a Pareto-optimal routing policy that dominates both homogeneous-Sonnet (expensive) and homogeneous-Haiku (cheap but low quality).

**Setup:**
- Use the benchmark harness (iv-qznx) to run the smoke task set across:
  - All-Haiku (cheapest)
  - All-Sonnet (baseline)
  - All-Opus (most expensive)
  - Mixed (complexity-routed)
  - Role-aware (per-agent model)

**Deliverable:** Pareto frontier chart showing cost vs quality for each policy. Any policy on the frontier is "valid" — the right choice depends on budget constraints.

## Implementation Plan

### Phase A: Enable B2 Complexity Routing (~1 day)
- Set `complexity.mode: shadow` in `routing.yaml`
- Add logging to lib-routing.sh to emit `{task, complexity_tier, model_chosen, model_baseline}`
- Run 20+ reviews in shadow mode, collect data

### Phase B: Role-Aware Agent Configuration (~1 day)
- Add `role` field to flux-drive agent profile (Planner/Editor/Reviewer/Checker)
- Add `model_override` per role in `routing.yaml`
- Shadow mode: log what model WOULD be used, compare output quality

### Phase C: Experiment Execution (~2 days)
- Run experiments 1-4 using interbench for capture
- Score using framework_score.py
- Document results in `docs/research/heterogeneous-routing-results.md`

### Phase D: Decision Document (~0.5 day)
- Based on results, write routing recommendation matrix
- Update `routing.yaml` with approved policy changes
- Set evidence gates for production rollout

## Decision Gates

Before any routing policy goes to production:

1. **Minimum evidence:** 20+ reviews with the policy (from iv-dthn Loop 4 threshold)
2. **Quality preservation:** Normalized score within 5% of baseline
3. **Retry rate:** < 15% increase over baseline
4. **Safety exception:** fd-safety and fd-correctness never route below Sonnet
5. **Rollback ready:** One config change to revert to B1 (`complexity.mode: off`)

## Files to Create/Modify

| File | Change |
|------|--------|
| `os/clavain/config/routing.yaml` | Add `complexity.mode: shadow`, add role mappings |
| `interverse/interflux/config/flux-drive/agent-roles.yaml` | New: agent → role mapping |
| `docs/research/heterogeneous-routing-results.md` | New: experiment results (after execution) |
| `core/interbench/tasks/routing-experiment-corpus.yaml` | New: routing-specific task variants |

## Non-Goals

- No production rollout in this sprint — shadow mode and data collection only
- No changes to interlock arbitration
- No Interspect integration (B3 adaptive routing is separate, depends on more data)
- No modifications to flux-drive protocol spec
