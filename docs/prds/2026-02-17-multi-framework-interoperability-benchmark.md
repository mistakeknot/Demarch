# PRD: Multi-framework Interoperability Benchmark

**Bead:** iv-qznx  
**Date:** 2026-02-17

## Problem
Interverse uses several orchestration patterns, but there is no common empirical baseline across frameworks. As ADK, LangGraph, AutoGen, agno, smolagents, CrewAI, and SWE-agent evolve, we risk over-indexing on one stack without measuring cross-framework quality, robustness, and cost.

## Goal
Create a reproducible benchmark that runs the same task corpus across framework backends and produces comparable cost/quality/latency signals for routing and procurement decisions.

## Core Capabilities

### F0: Shared task corpus
- Define a canonical task schema (input, context budget, constraints, expected artifact shape).
- Include token-sensitive and non-token-sensitive tasks.
- Add deterministic seed/run metadata for repeatability.

### F1: Adapter layer
- Add framework runners for ADK, LangGraph, AutoGen, agno, smolagents, CrewAI, and SWE-agent.
- Normalize run input/output shape and runtime metadata across runners.

### F2: Comparable metrics
- Add outcome score, success status, latency, invocation count, and approximate token cost.
- Add protocol for evaluator models and human-review overrides.
- Export normalized CSV + JSON result artifacts for interbench and Interphase decisions.

### F3: Decision support
- Add a scoreboard page in interbench with Pareto ranking (quality vs. cost vs. latency).
- Add model-agnostic routing defaults for `interflux` and `clavain`.

## Non-goals
- Replacing existing module-specific benchmarks.
- Full UI for public leaderboard publishing.
- Re-training any framework model.

## Dependencies
- `infra/interbench` runner changes
- CI for benchmark jobs
- API access for OpenAI-compatible providers used by each framework
- Open-research baselines referenced in roadmap watch list

## Open Questions
1. Which evaluator policy should be authoritative when framework outputs are structurally different?
2. Should cost normalization use raw provider billable tokens or normalized token proxy for fairness?
3. How often should scoring refresh for fast-moving frameworks?

