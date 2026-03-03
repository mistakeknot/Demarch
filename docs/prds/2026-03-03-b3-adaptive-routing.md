# PRD: B3 Adaptive Routing — Interspect Outcomes Drive Model/Agent Selection

**Bead:** iv-i198
**Priority:** P0
**Brainstorm:** docs/brainstorms/2026-03-03-b3-adaptive-routing-brainstorm.md

## Problem

Clavain's agent routing is static — every sprint uses the same model tiers regardless of historical performance. Expensive agents that rarely produce useful findings cost the same as agents that consistently catch real issues. There's no feedback loop from sprint outcomes to routing decisions.

Interspect collects evidence but the data never acts on routing. The evidence pipeline itself is partially broken (PostToolUse hook not recording agent_dispatch events). The closed-loop pattern from PHILOSOPHY.md is incomplete: stages 1-2 exist (defaults + collection infrastructure), but stages 3-4 (calibrate + fallback) are missing for agent routing.

## Goal

After this sprint, completed sprints automatically improve routing for future sprints. Specifically:
1. Agent dispatch events flow into interspect evidence (fix broken pipeline)
2. Flux-drive verdict outcomes create quality signals per agent
3. A calibration command computes agent scores and writes routing recommendations
4. lib-routing reads recommendations in shadow mode (log what would change)

## Non-Goals (This Sprint)

- Enforce mode (auto-applying calibrated routing without human review)
- Automatic graduation from propose → active
- Cost signal integration from interstat
- Cross-project routing calibration
- Per-language/per-type scoping (columns exist but are NULL)

## Features

### F1: Fix PostToolUse evidence pipeline
**Priority:** P0 (prerequisite for everything else)

Diagnose and fix why `interspect-evidence.sh` records zero `agent_dispatch` events despite the hook matcher working for interstat. Most likely cause: `_interspect_db_path()` can't find the project DB from the hook's CWD context.

**Acceptance:** After fix, dispatching an Agent subagent creates an `agent_dispatch` evidence row in `.clavain/interspect/interspect.db`.

### F2: Wire flux-drive verdict outcomes into evidence
**Priority:** P1

After flux-drive verdict consumption (quality-gates step), record per-agent outcomes as interspect evidence. Each agent verdict (CLEAN/NEEDS_ATTENTION) plus whether findings were acted on or dismissed becomes a quality signal.

**Schema:** `event = "verdict_outcome"`, `source = "fd-<agent>"`, `context = {status, findings_count, acted_on, dismissed, model_used}`.

New hook_id: `interspect-verdict` (add to allowlist).

**Acceptance:** After a sprint with quality-gates, evidence DB contains one `verdict_outcome` event per reviewed agent.

### F3: Agent scoring + calibration command
**Priority:** P1

New command `/interspect:calibrate` that:
1. Reads evidence (agent_dispatch + verdict_outcome + override/correction events)
2. Computes per-agent scores:
   - `hit_rate` = findings acted on / total findings
   - `cost_efficiency` = tokens per acted-on finding (from interstat if available)
   - `override_rate` = corrections where agent was wrong / total corrections
3. Writes `.clavain/interspect/routing-calibration.json`
4. Requires ≥3 evidence sessions per agent before scoring (matches cost calibration threshold)

**Acceptance:** Running `/interspect:calibrate` produces a calibration file with scored agents.

### F4: lib-routing reads calibration (shadow mode)
**Priority:** P2

Add a new resolution layer in `routing_resolve_model` that reads `.clavain/interspect/routing-calibration.json`. In shadow mode: resolves both base model and calibrated model, logs the difference, returns base.

**Resolution priority (updated):**
1. Kernel-stored per-run model overrides
2. Per-agent overrides in routing.yaml
3. **NEW: Interspect routing calibration** (shadow → enforce)
4. Phase-specific category model
5. Phase-level model
6. Default category model
7. Default model → "sonnet"

Safety floors still enforce lower bounds.

**Acceptance:** When calibration file exists, `routing_resolve_model` logs shadow comparisons showing what would change.

### F5: Calibration trigger in reflect phase
**Priority:** P2

Add `/interspect:calibrate` call after reflect captures learnings (same pattern as `calibrate-phase-costs`). Silent on failure.

**Acceptance:** Reflect phase automatically runs calibration.

## Technical Design

### Calibration file format
```json
{
  "calibrated_at": "2026-03-03T...",
  "schema_version": 1,
  "min_sessions": 3,
  "agents": {
    "fd-architecture": {
      "recommended_model": "sonnet",
      "current_model": "sonnet",
      "hit_rate": 0.72,
      "evidence_sessions": 8,
      "confidence": 0.85,
      "reason": "high hit rate, appropriate tier"
    },
    "fd-game-design": {
      "recommended_model": "haiku",
      "current_model": "sonnet",
      "hit_rate": 0.15,
      "evidence_sessions": 5,
      "confidence": 0.70,
      "reason": "low hit rate in non-game projects"
    }
  }
}
```

### Model recommendation logic
- hit_rate ≥ 0.6 AND current model is sonnet → keep sonnet
- hit_rate ≥ 0.6 AND current model is haiku → recommend sonnet (promotion)
- hit_rate < 0.3 AND ≥ 3 sessions → recommend haiku (demotion)
- hit_rate 0.3–0.6 → no change (insufficient signal)
- Safety floor agents (architecture/correctness/safety/quality) → never recommend below sonnet

## Dependencies

- Both dependencies (B2: complexity routing, E4: interspect kernel) are closed ✓
- F2 propose flow (iv-8fgu) name normalization is done ✓
- interstat cost-query.sh available for cost signal (nice-to-have, not blocking)

## Success Metrics

- Evidence pipeline: ≥1 agent_dispatch event per Agent tool call
- Verdict pipeline: ≥1 verdict_outcome event per quality-gates run
- Calibration: command produces valid JSON with scored agents
- Shadow mode: routing logs show calibrated vs base model comparisons
