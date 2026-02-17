# Multi-framework Interoperability Benchmark — Implementation Plan
**Bead:** iv-qznx
**Phase:** planned (as of 2026-02-17T00:00:00Z)

## Goal
Deliver a runnable benchmark harness that executes the same task corpus across 6+ frameworks and reports comparable quality/cost/latency outcomes.

### Task 1: Task corpus and schema
- Create `infra/interbench/tasks/agent-framework-corpus.yaml` with 25+ normalized task templates.
- Add task metadata: intent, risk, expected artifact, runtime constraints, deterministic seed.
- Add smoke task set (5 tasks) for CI execution in under 15 minutes.

### Task 2: Framework adapter scaffolding
- Add `infra/interbench/adapters/frameworks/` with runner shells for ADK, LangGraph, AutoGen, agno, smolagents, CrewAI, SWE-agent.
- Implement common input/output contract in a `RunResult` struct/table.
- Add adapter health checks for startup/import/runtime failures.

### Task 3: Scoring pipeline
- Add `infra/interbench/metrics/framework_score.py` with evaluator plugins and normalization rules.
- Write result export to JSON/CSV at `out/framework-benchmark/<date>/`.
- Publish comparative reports with pass rate and Pareto summary.

### Task 4: CI and reporting
- Add workflow target to run smoke suite weekly.
- Add manual rerun target for full suite.
- Add `docs/research/` note summarizing which frameworks lead on which task classes.

### Task 5: Routing integration
- Add a short recommendation matrix for `interflux`/`clavain` defaults.
- Gate adoption on minimum sample size and no-regression constraints.
