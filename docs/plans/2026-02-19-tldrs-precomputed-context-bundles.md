# Plan: tldrs Workspace-Scoped Precomputed Context Bundles

**Bead:** `iv-4o3m`
**Date:** 2026-02-19

## Inputs
- Token efficiency synthesis: `docs/research/token-efficiency-agent-orchestration-2026.md`
- Bead context: "Brainstorm #10 (tldrs-swinton-jji)"

## Goal
Precompute reusable context bundles on repository changes so first-query latency is near zero for common analysis paths.

## Scope
- Define bundle schema keyed by repo/workspace state.
- Trigger precompute on commit/update hooks.
- Cache and invalidate bundles safely.
- Provide runtime selection logic for best bundle match.

## Milestones
1. Bundle contract + keys
Specify bundle contents, cache key strategy, and invalidation semantics.

2. Precompute pipeline
Implement background/async bundle generation path.

3. Retrieval integration
Wire bundle lookup into tldrs request path with fallback to live computation.

4. Benchmark and tuning
Measure cold-start latency and cache hit ratio across real workflows.

## Dependency Plan
- No hard blocker; can start immediately.
- Coordinate with symbol popularity/index work (`iv-b6zm`) for smarter precompute priorities.

## Validation Gates
- Cold-start latency improves materially for cache hits.
- Cache invalidation correctness on file changes and branch switches.
- Fallback path always returns correct output when cache misses.

## Risks and Mitigations
- Stale bundles: include strict state hash and invalidation checks.
- Background cost spikes: throttle precompute and prioritize hot paths.
