# Brainstorm: B3 Adaptive Routing — Interspect Outcomes Drive Model/Agent Selection

**Bead:** iv-i198
**Date:** 2026-03-03

## Goal

Use historical outcome data from Interspect to dynamically adjust which agents run and at what model tier. Sprints that build evidence should improve routing for future sprints. This is the OODARC Compound phase applied to agent routing.

## Current State

### What Exists
- **Interspect evidence DB** — 54 records, all `kernel-phase` events. Zero agent-level signals.
- **Routing overrides** — `.claude/routing-overrides.json` schema v1. Supports `exclude`/`propose` actions. Currently empty (no overrides ever applied).
- **F2 propose flow** — Name normalization fixed (iv-8fgu). `_interspect_get_classified_patterns()` and `_interspect_is_routing_eligible()` work but require override/correction events that don't exist.
- **F3 apply+canary** — Override application, git commit, canary monitoring all implemented. Canary window: 20 uses over 14 days with 20% regression alert.
- **lib-routing.sh** — Model tier resolution (haiku/sonnet/opus) per agent/phase. B2 complexity routing in shadow mode. Safety floors enforced.
- **Flux-drive agent selection** — Domain-based pre-filtering, 0-7 scoring, routing override exclusion at Step 1.2a.0.
- **Cost calibration** — Just shipped: per-phase and per-model cost calibration (calibrate-phase-costs).

### The Gap
Two disconnected systems:
1. **Interspect** controls agent inclusion/exclusion (binary: in or out)
2. **lib-routing.sh** controls model selection (haiku/sonnet/opus tier)

Neither uses outcome data to adapt. The evidence pipeline exists but no quality signals flow into it. The propose flow exists but has no signal to work with.

## Problem Decomposition

Three problems, in dependency order:

### Problem 1: No agent-level quality signal flows into Interspect

The PostToolUse hook records `agent_dispatch` events but they never reach the DB (the hook fires but 0 dispatch records exist). The kernel `review_events` consumer reads disagreement_resolved events but none have been written. Without signals, there's nothing to route on.

**Diagnosed root cause:**
- The PostToolUse `Task` matcher DOES fire (interstat records 530 agent_runs with subagent_type data via the same matcher)
- hook_id `interspect-evidence` IS in the allowlist
- The interspect DB exists and has 54 records (all kernel-phase)
- **Likely cause:** `_interspect_db_path()` resolves via git root detection, but the PostToolUse hook may execute in a different CWD context where git root detection fails, causing `_interspect_ensure_db` to return early. The hook exits 0 silently (fail-open design).
- **Fix:** Verify CWD in hook context, add fallback DB path resolution, or log diagnostic output to confirm.

### Problem 2: Model-tier routing is static

Even with evidence, interspect can only exclude agents (binary). There's no mechanism to say "run fd-architecture on haiku instead of sonnet" based on outcome data. Cost savings come from model downgrade, not just exclusion.

**Options:**
- **A. Extend routing-overrides.json** — Add `action: "downgrade"` with `model: "haiku"`. Requires schema v2. Flux-drive reads the override and passes model hint to lib-routing.
- **B. Write to routing.yaml overrides** — Interspect writes to `subagents.overrides` section directly. lib-routing already reads this. No new schema needed.
- **C. New interspect-routing.json** — Separate file for model recommendations. lib-routing reads it as a new priority layer. Clean separation of concerns.

**Recommendation: Option B** — Use the existing routing.yaml override mechanism. It's already wired into lib-routing's resolution chain (priority 2: per-agent overrides). Interspect writes calibrated model overrides into a dedicated section that lib-routing already knows how to read.

### Problem 3: No closed-loop feedback on routing changes

When interspect changes routing, there's no measurement of whether the change helped. The canary system monitors for regression but doesn't track improvement. We need:
- Baseline metrics before override (agent finding rate, cost, override rate)
- Post-override metrics after canary window
- Automatic rollback on regression, graduation on improvement

The canary system partially covers this (20-use window, regression alert). What's missing: automatic graduation from `propose` → `exclude`/`downgrade` when the canary passes.

## Architecture Proposal

### Phase 1: Fix the signal pipeline (prerequisite)

1. **Fix PostToolUse hook** — Verify interspect-evidence hook fires on Task tool calls. Check hook_id allowlist. Get `agent_dispatch` events flowing.
2. **Wire review_events** — After flux-drive verdict consumption, write review outcomes (clean/needs_attention/overridden per agent) to kernel `review_events` table. This feeds disagreement_resolved events.
3. **Add cost signal** — After sprint completion, record per-agent cost data from interstat as evidence (event: `cost_report`, context: `{agent, model, tokens, usd}`).

**Validation:** After one sprint with these fixes, evidence DB should have agent_dispatch + review_outcome + cost_report events.

### Phase 2: Model-tier recommendations

1. **Agent scoring function** — Given evidence for an agent:
   - `hit_rate` = (findings acted on) / (total findings) across recent sprints
   - `cost_per_hit` = total USD / findings acted on
   - `override_rate` = (agent_wrong corrections) / total corrections
   - Agents with low hit_rate AND high cost → downgrade candidates
   - Agents with high hit_rate AND low cost → promotion candidates

2. **Calibration-style output** — Write `.clavain/interspect/routing-calibration.json`:
   ```json
   {
     "calibrated_at": "2026-03-03T...",
     "agents": {
       "fd-architecture": {
         "recommended_model": "sonnet",
         "hit_rate": 0.72,
         "cost_per_hit_usd": 1.25,
         "evidence_count": 15,
         "confidence": 0.85
       }
     }
   }
   ```

3. **lib-routing reads calibration** — New priority layer in `routing_resolve_model`:
   - Between "per-agent overrides in routing.yaml" and "phase-specific category model"
   - Only applies when confidence > threshold (0.7)
   - Safety floors still enforce lower bounds
   - Shadow mode first (log what would change), then enforce mode

### Phase 3: Closed-loop graduation

1. **Baseline snapshot** — Before applying a routing change, record current metrics for affected agents.
2. **Canary comparison** — After canary window, compare post-change metrics to baseline.
3. **Auto-graduation** — If metrics improve or hold steady: graduate from propose → active. If regress: revert and blacklist pattern.

## Scoping for This Sprint

This is an epic. A single sprint should deliver Phase 1 (fix signal pipeline) + the scoring function from Phase 2. Phases 2-3 are follow-up sprints.

**Deliverables for this sprint:**
1. Fix PostToolUse evidence collection (get agent_dispatch events flowing)
2. Wire flux-drive verdict outcomes into review_events
3. Add `/interspect:calibrate` command that reads evidence, computes agent scores, writes routing-calibration.json
4. Add lib-routing.sh reader for routing-calibration.json (shadow mode)
5. Tests for scoring function

**Not this sprint:**
- Enforce mode for calibrated routing (needs canary validation first)
- Automatic graduation (Phase 3)
- Cost signal integration (nice-to-have after core pipeline works)

## Key Decisions

1. **Shadow mode first** — All routing calibration starts in shadow mode. Log what would change, measure impact, graduate to enforce after manual review.
2. **Separate calibration file** — Don't extend routing-overrides.json (binary exclusion) or routing.yaml (static config). New file `routing-calibration.json` keeps concerns clean.
3. **Confidence threshold** — Require ≥3 sprints of evidence before calibrated routing applies (matches cost calibration pattern).
4. **4-stage closed-loop** — Following PHILOSOPHY.md: hardcoded defaults → collect actuals → calibrate from history → defaults become fallback. This sprint ships stages 1-3; stage 4 is inherent (no calibration file = current behavior).

## Open Questions

1. **Why are PostToolUse agent_dispatch events not recording?** — Need to diagnose before proceeding. Could be hook_id issue, filter issue, or the hook not firing at all.
2. **How to map flux-drive verdicts to review_events?** — Verdict files have STATUS (CLEAN/NEEDS_ATTENTION) but review_events expects dismissal_reason. Need a mapping.
3. **Should model recommendations be per-project or global?** — Start per-project (calibration file in .clavain/), generalize later if patterns are consistent across projects.
