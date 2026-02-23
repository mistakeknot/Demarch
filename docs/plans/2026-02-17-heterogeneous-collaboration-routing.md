# Heterogeneous Collaboration and Routing — Implementation Plan
**Bead:** iv-jc4j
**Phase:** planned (as of 2026-02-17T00:00:00Z)

## Goal
Measure the impact of mixed-role, mixed-cost routing on quality, time, and reliability.

### Task 1: Task classifier
- [x] Add task classifier in `clavain`/`interflux` entrypoint — already implemented as B2 complexity tiers (C1-C5) in `lib-routing.sh` with `routing_classify_complexity`.
- [x] Produce labels: routine / risky / high-complexity / recovery-needed — mapped to C1-C5 tiers in `routing.yaml`.

### Task 2: Policy engine experiments
- [x] Implement policy options: homogeneous (B1 static), cost-first (B2 C1/C2→haiku), and quality-first (B2 C4/C5→opus) — defined in `routing.yaml` complexity overrides.
- [ ] Record policy version and assignment rationale in run artifacts — needs experiment execution (Phase C).

### Task 3: Collaboration topology matrix
- Add orchestration modes: sequential, parallel, staged handoff.
- Log conflict and handoff rates per mode and workflow.

### Task 4: Evaluation harness
- [x] Add synthetic and repo tasks to a routing test harness — benchmark harness shipped (iv-qznx, 25+ task corpus in interbench).
- [ ] Track cost, p95 latency, first-success latency, and rework count — needs experiment execution (Phase C).

### Task 5: Policy gate and rollout
- Define acceptance thresholds for token savings vs. quality regression.
- Add canary override toggle and rollback switch in routing settings.
