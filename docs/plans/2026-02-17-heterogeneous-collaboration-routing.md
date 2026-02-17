# Heterogeneous Collaboration and Routing — Implementation Plan
**Bead:** iv-jc4j
**Phase:** planned (as of 2026-02-17T00:00:00Z)

## Goal
Measure the impact of mixed-role, mixed-cost routing on quality, time, and reliability.

### Task 1: Task classifier
- Add task classifier in `clavain`/`interflux` entrypoint.
- Produce labels: routine / risky / high-complexity / recovery-needed.

### Task 2: Policy engine experiments
- Implement policy options: homogeneous, cost-first, and quality-first in `interflux` dispatch layer.
- Record policy version and assignment rationale in run artifacts.

### Task 3: Collaboration topology matrix
- Add orchestration modes: sequential, parallel, staged handoff.
- Log conflict and handoff rates per mode and workflow.

### Task 4: Evaluation harness
- Add synthetic and repo tasks to a routing test harness in `infra/interbench`.
- Track cost, p95 latency, first-success latency, and rework count.

### Task 5: Policy gate and rollout
- Define acceptance thresholds for token savings vs. quality regression.
- Add canary override toggle and rollback switch in routing settings.
