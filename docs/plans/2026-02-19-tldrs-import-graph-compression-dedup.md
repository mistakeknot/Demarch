# Plan: tldrs Import Graph Compression and Dedup

**Bead:** `iv-44dz`
**Date:** 2026-02-19

## Inputs
- Token efficiency synthesis: `docs/research/token-efficiency-agent-orchestration-2026.md`
- Bead context: "Brainstorm #8 (tldrs-swinton-aqm)"

## Goal
Reduce context-pack token cost by deduplicating ubiquitous import edges and emitting only differential import information.

## Scope
- Build import graph normalization pass.
- Collapse repeated imports by source module.
- Emit compact per-symbol differential import sets.
- Preserve enough detail for downstream reasoning/debug.

## Milestones
1. Graph model + dedup rules
Define canonical import identity and deterministic merge rules.

2. Compression algorithm
Implement grouping and differential emission with stable ordering.

3. Format integration
Add compressed import section to relevant tldrs outputs with fallback toggle.

4. Test + benchmark
Add fixtures for large codebases and quantify token savings + fidelity impact.

## Dependency Plan
- No hard blocker; can execute directly.
- Coordinate with other tldrs compression tasks to avoid format drift.

## Validation Gates
- Deterministic output across runs.
- Import facts preserved for dependency tracing use-cases.
- Token reduction target: 10%+ on representative repos.

## Risks and Mitigations
- Over-compression may hide important edge context: keep optional verbose fallback.
- Non-deterministic grouping: enforce stable sort keys and snapshot tests.
