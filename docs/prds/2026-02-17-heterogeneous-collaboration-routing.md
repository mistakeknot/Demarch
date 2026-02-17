# PRD: Heterogeneous Collaboration and Routing Experiments

**Bead:** iv-jc4j  
**Date:** 2026-02-17

## Problem
Existing dispatch patterns are mostly homogeneous, and routing is often static for all task classes. That can over-spend tokens and underperform complex tasks where model-capability/risk tradeoffs matter.

## Goal
Evaluate routing policies that mix model size, role assignment, and collaboration topology inspired by SC-MAS and Dr. MAS.

## Core Capabilities

### F0: Task taxonomies
- Tag incoming tasks by risk, novelty, and required rigor.
- Add a light classification stage to map task tags to candidate agent topologies.

### F1: Routing policies
- Implement at least 3 routing strategies: homogeneous baseline, cost-first, and quality-first.
- Support role-aware assignments (planner/editor/reviewer/bot-checker) per subtask.

### F2: Collaboration modes
- Add experiments for sequential, parallel, and staged collaboration.
- Compare redundancy, conflict rates, and time-to-completion.

### F3: Evaluation and guardrails
- Publish success, fail-closed behavior, and token/cost deltas per policy.
- Add safety/quality gates before auto-adoption in `interflux` and `clavain` workflows.

## Non-goals
- Replacing interlock arbitration policies.
- Full production rollout without evidence gate pass.

## Dependencies
- `intermute` for routing signals and conflict telemetry
- `interspect` for policy-aware analytics
- Existing hook and dispatch telemetry in `clavain`

## Open Questions
1. What minimum evidence window should each policy pass before a switch is safe?
2. Can a dynamic policy degrade gracefully when telemetry is missing?
3. How much parallelism is acceptable before conflict cost exceeds gains?
