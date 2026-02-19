# Plan: tldrs Cross-Session Symbol Popularity Index

**Bead:** `iv-b6zm`
**Date:** 2026-02-19

## Inputs
- Token efficiency synthesis: `docs/research/token-efficiency-agent-orchestration-2026.md`
- Bead context: "Brainstorm #4 (tldrs-swinton-e5g)"

## Goal
Track cross-session symbol usage/popularity and use that signal to allocate context budget toward high-value symbols.

## Scope
- Record delivered symbols and observed reuse.
- Build popularity index with recency decay.
- Feed index into budget allocation/pruning logic.
- Keep behavior deterministic and explainable.

## Milestones
1. Telemetry schema
Define what symbol usage events are logged and retained.

2. Index builder
Implement score calculation (frequency + recency + optional role weights).

3. Budget integration
Use popularity scores to prioritize symbol retention under budget pressure.

4. Evaluation
Measure token savings and usefulness of retained context.

## Dependency Plan
- No hard blocker; can execute now.
- Should align with precompute bundle prioritization (`iv-4o3m`).

## Validation Gates
- Index updates are stable/idempotent.
- Popularity-informed pruning improves signal density under tight budgets.
- Token reduction target: 10%+ without quality drop.

## Risks and Mitigations
- Popularity can entrench stale symbols: include decay and freshness caps.
- Privacy/noise in telemetry: log minimal metadata and aggregate locally.
