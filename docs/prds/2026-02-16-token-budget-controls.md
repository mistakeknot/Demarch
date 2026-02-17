# PRD: Token Budget Controls + Cost-Aware Agent Dispatch

**Bead:** iv-8m38
**Date:** 2026-02-16
**Status:** PRD
**Brainstorm:** `docs/brainstorms/2026-02-16-token-budget-controls-brainstorm.md`

## Problem

Flux-drive dispatches all triage-selected agents regardless of cost. A 7-agent Opus review can consume 500K+ tokens (~$45 billing) when 2-3 targeted agents would produce equivalent findings for 150K tokens (~$13). Users have no visibility into per-review cost, no way to set budgets, and no way for the system to make cost-quality tradeoffs. This blocks AgentDropout (iv-qjwz) and blueprint distillation (iv-6i37), both of which need per-agent cost attribution.

## Users

- **Primary:** Clavain sprint users running flux-drive reviews as part of quality gates
- **Secondary:** Manual flux-drive users reviewing individual documents/codebases
- **Tertiary:** Future consumers of per-agent cost data (AgentDropout, interspect)

## Goals

1. **Budget-aware dispatch:** Flux-drive selects agents within a configurable token budget, deferring low-scoring agents when budget is tight
2. **Cost visibility:** Triage table shows estimated tokens per agent; synthesis reports actual vs. estimated
3. **Measurement standard:** Formal definitions for token types, scopes, and baselines (Oracle requirement)
4. **User control:** Override capability at triage confirmation — never hard-block without escape hatch
5. **Unblock downstream:** Provide per-agent cost attribution for iv-qjwz (AgentDropout) and iv-6i37 (blueprint distillation)

## Non-Goals

- Session-level token tracking (future: interbudget)
- Sprint-level budget enforcement (future: Clavain integration)
- Real-time PostToolUse budget gating (future: requires JSONL parsing in hot path)
- Model routing (which model per agent) — acknowledged as 3-5x cost lever but separate concern
- Dollar-cost display (token counts are sufficient; dollar conversion is model-pricing-dependent)

## Architecture

### Approach: Variant A+D Hybrid (from brainstorm)

Combine flux-drive internal budget config (Variant D) with historical cost estimates from interstat (Variant A). No new module required.

### Components

#### 1. Budget Configuration (`config/flux-drive/budget.yaml`)

```yaml
# Default token budgets per review type
# Values are total billing tokens (input + output) across ALL agents
budgets:
  plan: 150000
  brainstorm: 80000
  prd: 120000
  spec: 150000
  diff-small: 60000    # < 500 lines
  diff-large: 200000   # >= 500 lines
  repo: 300000
  other: 150000

# Per-agent default estimates (cold-start fallback when interstat has no data)
agent_defaults:
  review: 40000        # fd-* review agents
  cognitive: 35000     # fd-systems, fd-decisions, etc.
  research: 15000      # research agents
  oracle: 80000        # cross-AI Oracle

# Budget enforcement mode
enforcement: soft      # soft = warn + offer override | hard = block without override
warning_thresholds:
  - 0.75               # warn at 75% of budget
  - 0.90               # warn at 90% of budget
```

#### 2. Cost Estimator (query interstat)

Query `v_agent_summary` for historical per-agent averages:

```sql
SELECT agent_name, avg_total as est_tokens, runs as sample_size
FROM v_agent_summary
WHERE model = :current_model
  AND runs >= 3  -- minimum sample size for reliable estimate
ORDER BY agent_name;
```

**Cold-start behavior:** If interstat returns no data (or < 3 runs) for an agent, use `agent_defaults` from budget.yaml. Log the fallback so users know estimates are rough.

**Slicing adjustment:** If document slicing is active (>= 200 lines), apply a 0.5x multiplier to file-input agent estimates (slicing reduces per-agent consumption by ~50%). Diff-input agents are unaffected.

#### 3. Budget-Aware Triage (modify Phase 1.2b scoring)

After computing `final_score` for all agents:

1. Lookup budget for `INPUT_TYPE` from budget.yaml
2. Lookup per-agent cost estimates from interstat (or defaults)
3. Sort selected agents by `final_score` descending
4. Walk sorted list, accumulating estimated tokens
5. Agents whose cumulative cost exceeds budget → mark as `deferred`
6. Deferred agents shown in triage table with status "Deferred (budget)"

**Stage interaction:** Budget cut applies AFTER stage assignment. If all Stage 1 agents fit within budget but Stage 2 would exceed it, Stage 2 is deferred by default. User can override to launch Stage 2 anyway.

**Minimum guarantee:** Always dispatch at least 2 agents (top-2 by score) regardless of budget. Reviews with fewer than 2 agents are not useful.

#### 4. Enhanced Triage Table

Current:
```
Agent | Score | Stage | Reason | Action
```

New:
```
Agent | Score | Stage | Est. Tokens | Reason | Action
fd-architecture | 6 | 1 | ~42K | boundaries + coupling | Selected
fd-quality | 5 | 1 | ~38K | naming + conventions | Selected
fd-safety | 4 | 2 | ~45K | credentials + deploy | Deferred (budget)
                            Budget: 80K / 80K (100%)
```

#### 5. Actual vs. Estimated Reporting (synthesis Phase 3)

After all agents complete, report:

```
## Cost Report
| Agent | Estimated | Actual | Delta |
|-------|-----------|--------|-------|
| fd-architecture | 42K | 38K | -10% |
| fd-quality | 38K | 41K | +8% |
| TOTAL | 80K | 79K | -1% |

Budget: 80K. Spent: 79K (99%). Deferred: fd-safety (45K est.)
```

**Actual tokens:** Read from interstat after agents complete. If interstat data not yet backfilled (SessionEnd hasn't run), use result_length as a proxy or note "actual tokens pending backfill."

#### 6. Measurement Definitions (AGENTS.md section)

Formal definitions per Oracle requirement:

- **Token types:** input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, total_tokens
- **Cost types:** billing_tokens = input + output; effective_context = input + cache_read + cache_creation
- **Scopes:** per-agent, per-invocation, per-session, per-sprint
- **Budget unit:** billing_tokens (what costs money). Context checks use effective_context separately.
- **Baseline:** post-slicing per-agent averages from interstat (rolling 30-day window)

## Feature Breakdown

### F0: Budget configuration file + cost estimator query
- Create `config/flux-drive/budget.yaml` with defaults
- Write helper script/function to query interstat for per-agent estimates
- Cold-start fallback logic
- **Effort:** 0.5 day

### F1: Budget-aware triage logic
- Modify flux-drive Phase 1.2b to incorporate budget
- Cumulative cost calculation with defer logic
- Minimum 2-agent guarantee
- Stage interaction (Stage 2 deferred if budget exceeded)
- **Effort:** 1 day

### F2: Enhanced triage table + user override
- Add "Est. Tokens" column to triage display
- Add budget summary line
- Override option: "Launch deferred agents anyway"
- **Effort:** 0.5 day

### F3: Cost reporting in synthesis
- Query interstat for actual tokens after completion
- Actual vs. estimated delta table
- Budget utilization summary
- **Effort:** 0.5 day

### F4: Measurement definitions documentation
- Add measurement section to interflux AGENTS.md
- Document budget.yaml configuration options
- **Effort:** 0.5 day

## Success Metrics

1. **Budget adherence:** Flux-drive reviews stay within configured budget ≥ 80% of the time (without user override)
2. **Estimation accuracy:** Estimated tokens are within ±30% of actual for agents with ≥ 5 historical runs
3. **Unblocking:** iv-qjwz and iv-6i37 can query per-agent cost estimates via the same interstat interface
4. **No regressions:** Reviews that were previously dispatching 2-3 agents (within budget) see no behavior change

## Risks

1. **Cold start accuracy:** Without interstat history, default estimates may be wildly off. Mitigation: conservative defaults (40K per review agent) and soft enforcement mode.
2. **Slicing interaction:** Document slicing changes per-agent token consumption. Historical averages from pre-slicing era are misleading. Mitigation: 0.5x slicing multiplier + rolling 30-day window that naturally picks up post-slicing data.
3. **User friction:** Budget warnings could annoy users who always override. Mitigation: `enforcement: soft` default, per-project config, and override memory ("always launch all for this project").

## Dependencies

- **interstat** (existing): v_agent_summary view for historical per-agent costs. Already shipped.
- **document slicing** (iv-7o7n, shipped): affects per-agent token estimates.

## Timeline

Total effort: ~3 days (F0-F4 implemented sequentially, each building on the previous).
