# Plan: tldrs Structured Output Serialization Optimization

**Bead:** `iv-sm9n`
**Date:** 2026-02-19

## Inputs
- Bead context: serialization optimizations (key aliasing, column layout, null elision)
- Token efficiency synthesis: `docs/research/token-efficiency-agent-orchestration-2026.md`

## Goal
Reduce structured output token footprint through compact serialization while preserving compatibility and parseability.

## Scope
- Introduce compact key aliases for verbose fields.
- Add column-oriented encoding for repetitive records.
- Elide null/empty fields safely.
- Keep compatibility mode for existing consumers.

## Milestones
1. Serialization contract
Define compact schema and version marker.

2. Encoder implementation
Implement aliasing, column mode, and null elision.

3. Compatibility + migration
Provide dual-mode output (legacy + compact) and client compatibility guidance.

4. Tests + benchmarks
Add round-trip tests and token-size benchmarks across typical payloads.

## Dependency Plan
- No blockers; can start immediately.
- Coordinate with import graph and popularity index tasks to avoid overlapping format churn.

## Validation Gates
- Round-trip integrity for all optimized payload types.
- Token reduction target: 15%+ on structured output paths.
- Backward compatibility preserved for existing parsers.

## Risks and Mitigations
- Consumer breakage from schema changes: use explicit versioning and fallback mode.
- Readability tradeoffs: document compact schema clearly and keep debug render option.
