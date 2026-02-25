# Agent Trust and Reputation Scoring

**Bead:** iv-ynbh
**Phase:** brainstorm (as of 2026-02-25T16:26:01Z)
**Date:** 2026-02-25
**Status:** Brainstorm complete

## What We're Building

A feedback loop from flux-drive review synthesis back into agent triage scoring. Currently, flux-drive dispatches review agents based on static base scores and domain bonuses. There is no tracking of whether an agent's findings are actually useful -- fd-game-design produces irrelevant findings on CLI tool reviews forever, with no mechanism to learn from this.

The system will:
1. Record accept/discard signals when findings are resolved (via `/clavain:resolve`)
2. Compute per-agent per-project trust scores (precision = accepted / total)
3. Apply trust as a multiplier on existing triage scores
4. Use cross-project global averages as fallback for cold-start scenarios

## Why This Approach

### Resolve-time feedback (not synthesis-time)

Synthesis can infer convergence (multi-agent agreement = likely useful) but the real signal is whether the user actually fixes the finding. Recording at resolve-time gives us ground truth. Single integration point -- hook into the resolve workflow where accept/discard decisions are already being made.

### Multiplier (not hard threshold)

A multiplicative trust score (0.0-1.0) on the existing triage score is graceful. Low-trust agents get deprioritized but never fully excluded. This avoids premature exclusion before enough data accumulates. If fd-game-design has trust=0.15 on a CLI project, it still gets dispatched when other higher-priority agents are unavailable, but it won't steal slots from fd-safety or fd-correctness.

### Per-agent per-project scope with global fallback

The problem is domain mismatch -- fd-game-design is useless on CLI tools but could be valuable on game-design docs. Per-project scoping captures this. For cold start (new project or new agent), we inherit the agent's cross-project global average. This requires cross-project aggregation from day 1 but eliminates the chicken-and-egg problem.

### Cold start: 5-review threshold

New (agent, project) pairs use the global average until 5+ reviews accumulate. At 5 reviews, the project-specific score starts blending in. Full project-specific weight at 20+ reviews. This gives directional signal early without overreacting to small samples.

## Key Decisions

1. **Feedback source:** Resolve-time only. Hook into `/clavain:resolve` to emit `finding_accepted` / `finding_discarded` evidence events via interspect.
2. **Storage:** New interspect evidence types (`finding_accepted`, `finding_discarded`) with fields: agent_name, project, finding_id, severity, review_run_id.
3. **Aggregation:** Trust = accepted / (accepted + discarded) per (agent, project). Global average = same formula across all projects for a given agent.
4. **Cold start:** Inherit global average. Blend formula: `trust = (project_weight * project_score) + ((1 - project_weight) * global_score)` where `project_weight = min(1.0, project_reviews / 20)`.
5. **Triage integration:** Multiply existing triage score by trust score. New field in triage scoring: `trust_multiplier`.
6. **Minimum floor:** Trust score never goes below 0.05 -- even the worst agent gets occasional dispatch to allow recovery.

## Architecture

### Data flow

```
/resolve (user acts on finding)
  --> interspect evidence (finding_accepted / finding_discarded)
    --> trust score computation (on-demand or cached)
      --> triage scoring (trust_multiplier applied)
        --> agent dispatch (higher trust = higher priority)
```

### Integration points

1. **Resolve hook** (`os/clavain/hooks/` or resolve skill): Emit evidence events when findings are acted on. Need to map each finding back to its source agent.
2. **Interspect evidence tables**: Two new event types. Existing SQLite schema supports this -- just new `event` values in the `evidence` table.
3. **Trust computation** (`os/clavain/hooks/lib-interspect.sh` or new `lib-trust.sh`): Query evidence, compute scores, cache in interspect state.
4. **Triage scoring** (`interverse/interflux/skills/flux-drive/phases/launch.md`): Read trust scores during Phase 1.2 scoring, apply as multiplier.

### Finding-to-agent mapping

Synthesis writes `findings.json` with agent attribution. Each finding has a source agent. When `/resolve` processes a finding, it reads this attribution to emit the right evidence event. Key requirement: findings.json must persist until resolve completes.

## Open Questions

1. **Decay:** Should trust scores decay over time? An agent that was bad 6 months ago might have been improved. Tentative: yes, exponential decay with half-life of 30 days on individual events.
2. **Severity weighting:** Should accepting a P0 finding count more than accepting a P3? Tentative: yes, weight by severity (P0=4x, P1=2x, P2=1x, P3=0.5x).
3. **Relationship to AgentDropout (iv-qjwz):** Trust scoring feeds into triage (pre-dispatch). AgentDropout eliminates redundancy (post-dispatch). They're complementary, not mutually exclusive. Trust scoring should land first as it's simpler.
4. **Relationship to token ledger (iv-8m38):** Interstat already tracks tokens. Trust scoring doesn't need the ledger directly, but cost-per-useful-finding (tokens / accepted findings) is a natural extension metric.

## Scope

- ~3-4 days implementation
- Touches: interspect evidence schema, resolve workflow, triage scoring, lib-interspect.sh
- Does NOT touch: synthesis logic, agent prompts, dispatch mechanism
- Prerequisite: iv-vrc4 (interspect overlay, done)
- Unblocks: iv-qjwz (AgentDropout)
