# Token Budget Controls + Cost-Aware Agent Dispatch

**Bead:** iv-8m38
**Phase:** brainstorm (as of 2026-02-16T20:15:20Z)
**Date:** 2026-02-16
**Status:** Brainstorm

## Problem Statement

Interflux's flux-drive dispatches agents based purely on relevance scoring (0-7 scale) with no awareness of token cost. A 7-agent review on a large codebase can consume 500K+ tokens when 200K would suffice with targeted dispatch. There is no per-session cost visibility, no budget guardrails, and no way for the system to make cost-quality tradeoffs.

**Why this matters now:**
- Document slicing (iv-7o7n) just shipped — reduces per-agent token consumption by 50-70%
- interstat tracks agent-level tokens via PostToolUse:Task hook + JSONL backfill — the data exists
- AgentDropout (iv-qjwz) and blueprint distillation (iv-6i37) both need a token ledger as prerequisite
- Oracle review (GPT-5.2 Pro) explicitly flagged "no primary measurements" as the #1 gap

## What Exists Today

### interstat (token tracking — read-only)
- PostToolUse:Task hook fires on every Task dispatch → inserts row into `~/.claude/interstat/metrics.db`
- Fields: session_id, agent_name, invocation_id, result_length, wall_clock_ms
- Token data (input_tokens, output_tokens, cache_read/creation, total_tokens, model) backfilled by SessionEnd hook parsing session.jsonl
- Views: v_agent_summary (avg tokens per agent+model), v_invocation_summary (per-invocation totals)
- **Gap:** Data is post-hoc only. No real-time session-level running total. No budget enforcement.

### flux-drive (dispatch — cost-blind)
- Triage: `final_score = base_score(0-3) + domain_boost(0-2) + project_bonus(0-1) + domain_agent(0-1)`
- Dynamic slot ceiling: `4(base) + scope(0-3) + domain(0-2) + generated(0-2)`, hard max 12
- Stage 1 = top 40% of slots (min 2, max 5). Stage 2 = remainder. Expansion decision via adjacency scoring.
- **Gap:** No budget input to triage. All scored agents within slot ceiling get dispatched regardless of cost.

### tool-time (usage counts — no tokens)
- Tracks tool usage patterns (call counts, errors, rejections)
- No token or cost data. No per-agent attribution.

## Design Space

### Variant A: Budget-aware triage (modify flux-drive)

Add a `budget_remaining` parameter to flux-drive triage. After scoring, estimate per-agent token cost from historical data (interstat v_agent_summary), then dispatch top-N agents whose cumulative estimated cost fits within budget.

**How it works:**
1. Query interstat: `SELECT agent_name, avg_total FROM v_agent_summary WHERE model='opus'` → per-agent cost estimates
2. Sort selected agents by triage score (descending)
3. Walk the sorted list, accumulating estimated tokens. Stop when next agent would exceed budget_remaining.
4. Agents below the cut get deferred to Stage 2 (or dropped) with a user notification: "Skipped fd-performance (est. 45K tokens) — budget insufficient. Override?"

**Pros:** Minimal new code. Uses existing interstat data. No new module.
**Cons:** interstat averages may be stale or misleading (a code review costs differently from a plan review). No persistent budget tracking across sessions.

### Variant B: Session token ledger (new interbudget module)

New plugin/module that maintains a running session-level token counter. PostToolUse hook reads Claude Code's session JSONL to extract cumulative tokens. Provides budget config (per-session cap, per-sprint cap), enforcement hooks (PreToolUse gate for expensive tools), and cost dashboard.

**How it works:**
1. SessionStart hook reads budget config from `~/.interbudget/budget.yaml`
2. PostToolUse hook parses latest session JSONL entry → updates running total in memory (env file or temp file)
3. PreToolUse hook checks running total against budget cap → if exceeded, blocks tool use with warning
4. Flux-drive reads budget remaining from interbudget → uses for Variant A logic
5. SessionEnd hook writes final session cost to persistent store

**Pros:** Full cost visibility. Enforcement at every tool call. Sprint-level budgets.
**Cons:** New module to build and maintain. Parsing session JSONL in every PostToolUse is expensive. Complex state management (env files, temp files).

### Variant C: Extend interstat with budget mode

Rather than a new module, extend interstat's existing infrastructure to support budget tracking. Add a `budget_config` table and a `session_budget` view. PostToolUse hook already fires — add real-time token parsing to it (not just agent dispatch tracking).

**How it works:**
1. New table: `budget_config(project TEXT, session_cap INTEGER, sprint_cap INTEGER, routing_policy TEXT)`
2. New view: `v_session_cost` — aggregates token totals from session JSONL parser
3. Extend PostToolUse hook: if tool is Task with expensive subagent, estimate cost from v_agent_summary and emit budget warning if threshold exceeded
4. Flux-drive queries interstat's v_session_cost + budget_config to determine remaining budget

**Pros:** No new module. Leverages existing SQLite schema + hooks. Single source of truth.
**Cons:** Bloats interstat beyond its "benchmarking" scope. Real-time parsing still needed.

### Variant D: Flux-drive internal budget (self-contained)

Keep budget logic entirely within interflux. No external module. Flux-drive maintains a per-run token estimate based on historical agent costs, and makes dispatch decisions locally.

**How it works:**
1. `config/flux-drive/budget.yaml` defines default token budgets per review type (plan: 150K, brainstorm: 80K, repo: 300K)
2. Triage phase reads budget config + queries interstat for historical agent costs
3. Dispatch phase implements budget-aware agent selection (same as Variant A step 2-4)
4. Post-synthesis: report actual vs. estimated tokens consumed

**Pros:** Self-contained. No cross-module dependencies. Easy to test.
**Cons:** No session-level or sprint-level budgets. Only covers flux-drive, not other expensive operations (Oracle, research agents).

## Measurement Definitions (Oracle requirement)

Oracle (GPT-5.2 Pro) flagged that all token optimization claims need a standardized measurement framework:

### Units
- **Token type:** input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, total_tokens
- **Cost type:** billing_tokens (input + output), effective_context (input + cache_read + cache_creation)
- **Dollar cost:** model-specific pricing (Opus: $15/$75 per 1M in/out, Sonnet: $3/$15, Haiku: $0.25/$1.25)

### Scopes
- **Per-agent:** tokens consumed by a single Task dispatch
- **Per-invocation:** tokens consumed across all agents in a single flux-drive run
- **Per-session:** total tokens in a Claude Code session
- **Per-sprint:** tokens across all sessions in a Clavain sprint

### Baselines
- **Pre-slicing baseline:** avg total_tokens per flux-drive invocation before iv-7o7n shipped
- **Post-slicing baseline:** avg total_tokens per flux-drive invocation with document slicing active
- **Budget effectiveness:** (useful_findings / tokens_consumed) ratio, measured per-agent

### Critical distinction: billing vs. effective context
Decision gates about whether to dispatch more agents MUST use effective_context (not billing_tokens) because:
- Cache hits are free for billing but consume context window
- Effective context can be 600x larger than billing tokens
- Budget caps should be expressed in billing_tokens (what costs money) but context checks in effective_context (what fits in the window)

## Integration Points

### Where budget info enters flux-drive

The cleanest integration point is **Phase 1.2b (Score)** in the triage algorithm. After computing `final_score` for all agents:

1. Query token estimates: `SELECT agent_name, avg_total FROM v_agent_summary WHERE model = '{current_model}'`
2. Compute cumulative cost for scored agents (descending by score)
3. Mark agents beyond budget as "deferred" instead of "selected"
4. Show in triage table: `Agent | Score | Stage | Est. Tokens | Action`
5. User can override: "Launch deferred agents anyway"

### Where budget info enters Clavain sprint

Sprint workflow could pass a budget parameter to each phase:
- Brainstorm: 80K budget (Haiku OK)
- Strategy: 100K budget (Sonnet recommended)
- Plan: 60K budget (Sonnet)
- Flux-drive reviews: 200K budget (split across agents)
- Execution: remainder of sprint budget

This is **future work** — not in scope for iv-8m38. But the budget infrastructure should be designed to support it.

## Variant Evaluation

| Criterion | A (triage mod) | B (interbudget) | C (extend interstat) | D (internal) |
|-----------|:---:|:---:|:---:|:---:|
| Scope of budget enforcement | flux-drive only | all tools | all tools | flux-drive only |
| New module required | No | Yes | No | No |
| Real-time token tracking | No (historical avg) | Yes | Partial | No (historical avg) |
| Sprint-level budgets | No | Yes | Yes | No |
| Effort (days) | 1-2 | 5-7 | 3-4 | 1 |
| Unblocks iv-qjwz (AgentDropout) | Yes | Yes | Yes | Yes |
| Unblocks iv-6i37 (blueprint distillation) | Yes | Yes | Yes | Partially |

## Recommended Approach: Variant A + D hybrid

Start with the minimal viable budget: **Variant D** (flux-drive internal budget config) combined with **Variant A** (historical cost estimates from interstat). This gives:

1. Per-review-type token budgets in `config/flux-drive/budget.yaml`
2. Historical per-agent cost estimates from interstat's existing data
3. Budget-aware triage that defers low-scoring agents when budget is tight
4. Actual vs. estimated reporting in synthesis output
5. User override capability at triage confirmation step

**Why not Variant B/C now?**
- Session-level and sprint-level budgets (Variant B/C) are valuable but are a separate feature (interbudget)
- Real-time token parsing in every PostToolUse is architecturally complex and has performance implications
- iv-8m38 explicitly says "cost-aware agent dispatch" — flux-drive dispatch is the primary target
- AgentDropout (iv-qjwz) needs per-agent cost attribution, not per-session budgets

**Future path:**
- iv-8m38: Variant A+D (this sprint) → unblocks iv-qjwz, iv-6i37
- Future bead: Variant C or B → session/sprint budgets, cross-tool enforcement
- iv-qjwz: Uses iv-8m38's per-agent costs for redundancy elimination scoring

## Open Questions

1. **Cold start:** What if interstat has no historical data for an agent? Use a default estimate (e.g., 40K tokens for review agents, 15K for research agents)?
2. **Model routing:** Should budget config specify which model to use per agent? (e.g., "use Haiku for fd-quality on brainstorms") This is the 3-5x cost lever from research.
3. **Slicing interaction:** Document slicing reduces per-agent tokens. Should budget estimates use post-slicing averages? How to handle the transition period where historical data is pre-slicing?
4. **User override UX:** Soft warning vs. hard block? Recommendation: soft warning with override ("Budget exceeded — launch anyway?") since hard blocks frustrate power users.
5. **Sprint budget pass-through:** Should `/clavain:sprint` pass a budget parameter to flux-drive? Not for v1, but the config format should anticipate it.

## Deliverables

1. `config/flux-drive/budget.yaml` — default token budgets per review type
2. Measurement definitions section in interflux AGENTS.md (Oracle requirement)
3. Budget-aware triage logic in flux-drive Phase 1.2 (score + estimate + cut)
4. Triage table enhancement: show estimated tokens per agent
5. User override flow at triage confirmation
6. Actual vs. estimated cost reporting in synthesis Phase 3
7. Documentation: budget configuration guide
