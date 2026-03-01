# Safety Floors for Safety-Critical Agents

**Bead:** iv-db5pc
**Date:** 2026-03-01
**Status:** Brainstorm complete

## What We're Building

Enforce `min_model` from `agent-roles.yaml` at dispatch time in `lib-routing.sh`, so safety-critical flux-drive agents (fd-safety, fd-correctness, fd-architecture, fd-systems) can never be routed to a model weaker than their declared floor — regardless of phase, category defaults, or complexity routing.

## Why This Approach

Three safety floor mechanisms already exist independently:
1. **routing.yaml agent overrides** — hard-coded overrides for fd-safety and fd-correctness (enforced today)
2. **agent-roles.yaml min_model** — declares `min_model: sonnet` for the reviewer role (informational only, not enforced)
3. **budget.yaml exempt_agents** — prevents AgentDropout from pruning fd-safety/fd-correctness

The gap: `min_model` in agent-roles.yaml is not consumed by the dispatch code. If routing.yaml overrides are removed or complexity routing (B2) moves from shadow to enforce mode, nothing prevents safety-critical agents from being demoted to Haiku.

The chosen approach wires `min_model` into `lib-routing.sh` as a hard clamp, making agent-roles.yaml the single source of truth for safety policy. The routing.yaml overrides remain as a defense-in-depth layer but are no longer the sole enforcement point.

## Key Decisions

1. **Single source of truth**: `agent-roles.yaml` `min_model` becomes the authoritative safety floor. `routing.yaml` overrides are kept as defense-in-depth.
2. **Clamp, don't reject**: If the resolved model is below `min_model`, silently upgrade to `min_model` rather than failing the dispatch. Log when clamping occurs for observability.
3. **Expand coverage**: Add `min_model: sonnet` to the `planner` role (fd-architecture, fd-systems), not just `reviewer`. These agents make architectural decisions and shouldn't run on Haiku.
4. **Model tier ordering**: Define a clear ordering (haiku < sonnet < opus) for comparison in the dispatch code.
5. **Interspect integration**: Log clamping events so interspect can track how often safety floors activate — this feeds back into routing optimization experiments.

## Empirical Basis

- Experiment iv-jocaw: fd-safety ran on Haiku 47% of the time, fd-correctness 26%
- Experiment iv-dthn Loop 4: established the "never below Sonnet" rule
- Experiment iv-jc4j: confirmed B1 + safety floors is Pareto-optimal

## Open Questions

1. Should `editor` role (fd-performance, fd-user-product, fd-game-design) also get a floor? Currently no — they're less safety-critical. Revisit if experiment data shows quality degradation.
2. Should clamping events emit interspect evidence directly, or just log to stderr for passive collection?
3. When B2 complexity routing moves to `enforce` mode, should it respect min_model or should min_model be a separate post-resolution step? (Recommendation: post-resolution clamp, so the ordering is always resolution → clamp.)
