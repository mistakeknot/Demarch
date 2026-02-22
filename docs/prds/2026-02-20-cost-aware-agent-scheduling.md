# Cost-Aware Agent Scheduling — PRD
**Bead:** iv-pbmc | **Sprint:** iv-suzr
**Date:** 2026-02-20

## Problem Statement

Sprint workflows have no token budget enforcement. A C4 sprint can consume 500K+ billing tokens with no awareness until after the session ends. Flux-drive dispatches agents against its own static budget.yaml values without knowing the sprint's remaining budget. The intercore kernel has budget algebra and CLI commands (`ic run budget`, `ic run tokens`), but nothing in the OS layer writes token data or reads budget constraints.

## Goal

Make token spend a first-class sprint resource: trackable at phase granularity, enforceable at sprint advance, and visible to flux-drive triage for cost-aware agent selection.

## Non-Goals

- Real-time per-tool-call token accounting (deferred — requires PostToolUse JSONL parsing)
- Hard budget enforcement (always soft with override)
- New standalone modules or databases (extend existing infrastructure)
- Interspect cost-effectiveness v2 (stretch goal within this sprint, deferrable)

## Approach: Hybrid Estimation + Post-Phase Writeback

Use pre-computed cost estimates for forward-looking budget decisions, with post-phase actual token writeback to close the data loop for subsequent phases.

### Key Insight

We don't need real-time per-tool-call accuracy. Phase-granularity writeback gives the sprint advance check real data by phase 3-4, which is exactly when budgets start mattering (brainstorm/strategy phases are cheap, 20-40K each; execute/quality-gates are expensive, 100-200K each).

## Features

### F1: Sprint Budget Parameter (lib-sprint.sh)

**What:** `sprint_create()` passes token budget to `ic run create`. `sprint_read_state()` surfaces `token_budget` and `tokens_spent`.

**Acceptance criteria:**
- `sprint_create` accepts optional budget parameter, defaults by complexity tier
- `sprint_read_state` JSON includes `token_budget` (from ic run) and `tokens_spent` (from `ic run tokens`)
- User can override: `bd set-state <sprint> token_budget=300000`
- Default budgets: C1=50K, C2=100K, C3=250K, C4=500K, C5=1M (calibratable)
- Beads-only sprints (no ic run): budget stored in bead state, no enforcement

**Files:** `os/clavain/hooks/lib-sprint.sh`

### F2: Sprint Advance Budget Check (lib-sprint.sh)

**What:** `sprint_advance()` checks budget before advancing. Budget exhaustion is a new pause trigger type.

**Acceptance criteria:**
- Before advancing, call `ic run budget <id>` (exit 1 = exceeded, exit 0 = OK)
- If exceeded: return structured pause reason `budget_exceeded|<phase>|<spent>/<budget>`
- If warn threshold crossed: emit warning message but continue
- Sprint command's auto-advance protocol handles `budget_exceeded` like `gate_blocked`
- User override: `CLAVAIN_SKIP_BUDGET='reason'` env var
- Beads-only sprints: skip check (no ic run = no budget enforcement)

**Files:** `os/clavain/hooks/lib-sprint.sh`, `os/clavain/commands/sprint.md`

### F3: Flux-Drive Budget Integration (interflux)

**What:** Sprint step passes remaining token budget to flux-drive. Triage uses it as effective budget ceiling.

**Acceptance criteria:**
- Sprint command sets `FLUX_BUDGET_REMAINING` env var before invoking flux-drive steps
- Remaining = `token_budget - tokens_spent` (from `sprint_read_state`)
- Flux-drive triage Step 1.2c uses `min(budget.yaml default, FLUX_BUDGET_REMAINING)` as effective budget
- If no env var, falls back to budget.yaml (backward compatible)
- Triage summary line shows: `Budget: Xk / Yk (Z%) [sprint-constrained]` when sprint budget is tighter

**Files:** `plugins/interflux/skills/flux-drive/SKILL-compact.md`, `os/clavain/commands/sprint.md`

### F4: Post-Phase Token Writeback (lib-sprint.sh)

**What:** After each phase completes, write estimated or actual token counts to intercore dispatch records.

**Acceptance criteria:**
- After phase completion, call `ic dispatch tokens <dispatch_id> --set --in=N --out=N`
- For agent-dispatching phases (quality-gates, execute): query interstat `agent_runs` for session-scoped token sum
- For non-agent phases (brainstorm, strategy, plan): use default estimate from a lookup table
- Token estimates table: brainstorm=30K, strategy=25K, plan=35K, plan-review=50K, execute=varies, quality-gates=varies, resolve=20K, reflect=10K, ship=5K
- This feeds `ic run tokens` / `ic run budget` for subsequent phase budget checks
- Creates synthetic dispatch records per phase if none exist

**Files:** `os/clavain/hooks/lib-sprint.sh`

### F5: Interspect Cost-Effectiveness Signal (stretch)

**What:** After flux-drive synthesis, record per-agent cost-effectiveness in interspect evidence.

**Acceptance criteria:**
- After synthesis, count accepted vs total findings per agent (from verdict files)
- Query interstat for per-agent billing tokens (may be NULL — use estimate if so)
- Compute: `effectiveness = accepted_findings / billing_tokens` (findings per 1K tokens)
- Write to interspect evidence: `source=<agent>, event=cost_effectiveness, context={effectiveness, tokens, findings}`
- Interspect's routing eligibility check can factor in effectiveness alongside override rate

**Files:** `os/clavain/hooks/lib-interspect.sh`, `os/clavain/hooks/interspect-evidence.sh`

## Feature Dependencies

```
F1 (budget param) ──→ F2 (advance check) ──→ F3 (flux-drive integration)
       │                                           │
       └──→ F4 (token writeback) ─────────────────┘
                                                    │
                                               F5 (interspect, stretch)
```

F1 is the foundation. F2 and F4 can be built in parallel after F1. F3 depends on F2 (needs `sprint_read_state` with budget). F5 is independent and deferrable.

## Success Metrics

1. Sprint summary shows `Budget: Xk / Yk (Z%)` for every sprint with a budget
2. Sprint advance warns when >80% budget consumed
3. Flux-drive triage defers agents when sprint budget is tighter than static budget.yaml
4. `ic run tokens <id>` returns non-zero values for completed phases
5. Existing sprints without budgets work identically (backward compatible)

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Token estimates are wildly inaccurate | Medium | Low | Soft enforcement — bad estimates just produce bad warnings |
| interstat queries return NULL mid-session for writeback | High for agent phases | Medium | Fallback to estimates when NULL, backfill corrects post-session |
| `ic run budget` not wired to event recorder | Known | Low | Budget check via exit code works fine; event bus is future work |
| Sprint advance latency from ic commands | Low | Low | ic commands are <100ms; one extra call per phase advance |
