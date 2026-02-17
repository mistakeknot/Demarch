# Token Budget Controls — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Add budget-aware agent dispatch to flux-drive using historical per-agent cost estimates from interstat, with configurable per-review-type token budgets, enhanced triage display, and actual-vs-estimated cost reporting in synthesis.

**Architecture:** Budget config in `config/flux-drive/budget.yaml`. Cost estimator queries interstat's `v_agent_summary`. Triage in SKILL-compact.md gains a budget-cut step after scoring. Synthesis gains a cost report section. No new modules.

**Tech Stack:** YAML config, SQLite queries (interstat), Markdown skill files (flux-drive)

**PRD:** `docs/prds/2026-02-16-token-budget-controls.md`
**Bead:** iv-8m38 (epic)
**Phase:** executed (as of 2026-02-16T22:50:00Z)

---

## Task 1: Create budget configuration file

**Files:**
- Create: `plugins/interflux/config/flux-drive/budget.yaml`

**Step 1: Create budget.yaml**

```yaml
# Token budget configuration for flux-drive agent dispatch
# Budgets are in billing tokens (input_tokens + output_tokens) across ALL agents in a run.
# Override per-project via {PROJECT_ROOT}/.claude/flux-drive-budget.yaml

# Default budgets by input type
budgets:
  plan: 150000
  brainstorm: 80000
  prd: 120000
  spec: 150000
  diff-small: 60000      # diff < 500 lines
  diff-large: 200000     # diff >= 500 lines
  repo: 300000
  other: 150000

# Per-agent token estimates (cold-start fallback)
# Used when interstat has < 3 runs for an agent+model pair
agent_defaults:
  review: 40000           # fd-architecture, fd-safety, fd-correctness, fd-quality, fd-user-product, fd-performance, fd-game-design
  cognitive: 35000         # fd-systems, fd-decisions, fd-people, fd-resilience, fd-perception
  research: 15000          # best-practices-researcher, framework-docs-researcher, etc.
  oracle: 80000            # cross-AI Oracle review
  generated: 40000         # flux-gen project-specific agents

# Slicing discount: multiply estimate by this factor when document slicing is active
slicing_multiplier: 0.5

# Minimum agents to always dispatch (regardless of budget)
min_agents: 2

# Budget enforcement
enforcement: soft          # soft = warn + offer override | hard = block
```

**Acceptance:** File exists at `plugins/interflux/config/flux-drive/budget.yaml`. Valid YAML.

---

## Task 2: Create cost estimator script

**Files:**
- Create: `plugins/interflux/scripts/estimate-costs.sh`

**Step 1: Write the estimator script**

This script queries interstat for per-agent cost averages and falls back to budget.yaml defaults.

```bash
#!/usr/bin/env bash
# estimate-costs.sh — Query interstat for per-agent token cost estimates
# Usage: estimate-costs.sh [--model MODEL] [--slicing]
# Output: JSON object mapping agent_name -> estimated_tokens
# Requires: sqlite3, jq, budget.yaml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUDGET_FILE="${PLUGIN_DIR}/config/flux-drive/budget.yaml"
DB_PATH="${HOME}/.claude/interstat/metrics.db"

MODEL="${1:---model}"
SLICING=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --slicing) SLICING=true; shift ;;
    *) shift ;;
  esac
done

# Default model if not specified
if [[ "$MODEL" == "--model" ]]; then
  MODEL="claude-opus-4-6"
fi

# Read default estimates from budget.yaml using simple grep (no yq dependency)
get_default() {
  local agent_type="$1"
  local default_val="40000"
  local line
  line=$(grep "^  ${agent_type}:" "$BUDGET_FILE" 2>/dev/null || echo "")
  if [[ -n "$line" ]]; then
    default_val=$(echo "$line" | sed 's/.*: *//' | tr -d '[:space:]')
  fi
  echo "$default_val"
}

get_slicing_multiplier() {
  local line
  line=$(grep "^slicing_multiplier:" "$BUDGET_FILE" 2>/dev/null || echo "")
  if [[ -n "$line" ]]; then
    echo "$line" | sed 's/.*: *//' | tr -d '[:space:]'
  else
    echo "0.5"
  fi
}

# Classify agent into type for default lookup
classify_agent() {
  local name="$1"
  case "$name" in
    fd-systems|fd-decisions|fd-people|fd-resilience|fd-perception) echo "cognitive" ;;
    *-researcher|*-analyzer|*-analyst) echo "research" ;;
    oracle*) echo "oracle" ;;
    fd-*) echo "review" ;;
    *) echo "generated" ;;
  esac
}

# Query interstat for historical averages
ESTIMATES="{}"
if [[ -f "$DB_PATH" ]]; then
  # Query agents with >= 3 runs for reliable estimates
  INTERSTAT_DATA=$(sqlite3 -json "$DB_PATH" "
    SELECT agent_name, CAST(ROUND(AVG(COALESCE(input_tokens,0) + COALESCE(output_tokens,0))) AS INTEGER) as est_tokens, COUNT(*) as sample_size
    FROM agent_runs
    WHERE (model = '${MODEL}' OR model IS NULL)
      AND (input_tokens IS NOT NULL OR output_tokens IS NOT NULL)
    GROUP BY agent_name
    HAVING COUNT(*) >= 3
    ORDER BY agent_name;
  " 2>/dev/null || echo "[]")

  if [[ "$INTERSTAT_DATA" != "[]" && -n "$INTERSTAT_DATA" ]]; then
    ESTIMATES=$(echo "$INTERSTAT_DATA" | jq -c '
      reduce .[] as $row ({};
        . + {($row.agent_name): {est_tokens: $row.est_tokens, sample_size: $row.sample_size, source: "interstat"}}
      )
    ')
  fi
fi

# Apply slicing multiplier if active
MULTIPLIER="1.0"
if [[ "$SLICING" == "true" ]]; then
  MULTIPLIER=$(get_slicing_multiplier)
fi

# Output JSON with estimates (interstat data + defaults for unknown agents)
# The caller will merge this with the list of selected agents
echo "$ESTIMATES" | jq -c --arg mult "$MULTIPLIER" \
  --arg review_default "$(get_default review)" \
  --arg cognitive_default "$(get_default cognitive)" \
  --arg research_default "$(get_default research)" \
  --arg oracle_default "$(get_default oracle)" \
  --arg generated_default "$(get_default generated)" \
  '{
    estimates: .,
    defaults: {
      review: ($review_default | tonumber),
      cognitive: ($cognitive_default | tonumber),
      research: ($research_default | tonumber),
      oracle: ($oracle_default | tonumber),
      generated: ($generated_default | tonumber)
    },
    slicing_multiplier: ($mult | tonumber)
  }'
```

Make executable: `chmod +x plugins/interflux/scripts/estimate-costs.sh`

**Acceptance:** Script runs without error. Output is valid JSON with `estimates`, `defaults`, and `slicing_multiplier` keys.

---

## Task 3: Add budget-aware triage to SKILL-compact.md

**Files:**
- Edit: `plugins/interflux/skills/flux-drive/SKILL-compact.md`

**Step 1: Add Step 1.2c (Budget Cut) after Step 1.2b (Score)**

Insert after the `Stage assignment` line (after line ~91) and before Step 1.3:

```markdown
### Step 1.2c: Budget-aware agent selection

After scoring and stage assignment, apply budget constraints.

**Step 1.2c.1: Load budget config**

Read `${CLAUDE_PLUGIN_ROOT}/config/flux-drive/budget.yaml`. Look up the budget for the current `INPUT_TYPE`:
- `file` → use the `Document Profile → Type` value (plan, brainstorm, prd, spec, other)
- `diff` with < 500 lines → `diff-small`
- `diff` with >= 500 lines → `diff-large`
- `directory` → `repo`

If a project-level override exists at `{PROJECT_ROOT}/.claude/flux-drive-budget.yaml`, use that instead.

Store as `BUDGET_TOTAL`.

**Step 1.2c.2: Estimate per-agent costs**

Run the cost estimator:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/estimate-costs.sh --model {current_model} [--slicing if slicing active]
```

For each selected agent, look up its estimate:
1. If `estimates[agent_name]` exists (from interstat, >= 3 runs): use `est_tokens`, note `source: interstat (N runs)`
2. Else: classify agent (review/cognitive/research/oracle/generated) and use `defaults[type]`, note `source: default`
3. If slicing is active AND agent is NOT cross-cutting (fd-architecture, fd-quality): multiply estimate by `slicing_multiplier`

**Step 1.2c.3: Apply budget cut**

Sort all selected agents by `final_score` descending. Walk the list, accumulating estimated tokens:

```
cumulative = 0
for agent in sorted_agents:
    if cumulative + agent.est_tokens > BUDGET_TOTAL and agents_selected >= min_agents:
        agent.action = "Deferred (budget)"
    else:
        agent.action = "Selected"
        cumulative += agent.est_tokens
```

`min_agents` comes from budget.yaml (default 2). The top-scoring agents are always selected.

**Stage interaction:** If all Stage 1 agents fit within budget but adding Stage 2 would exceed it, mark Stage 2 as "Deferred (budget)" by default. The expansion decision (Step 2.2b) will still offer the user the option to override.

**No-data graceful degradation:** If interstat DB doesn't exist or returns no data, use defaults for ALL agents. Log: "Using default cost estimates (no interstat data)." Do NOT skip budget enforcement — defaults provide reasonable bounds.
```

**Step 2: Enhance Step 1.3 (User Confirmation) triage table**

Replace the triage table format in Step 1.3 (around line ~95-98):

Old:
```
Present triage table: Agent | Score | Stage | Reason | Action
```

New:
```
Present triage table with budget context:

Agent | Score | Stage | Est. Tokens | Source | Reason | Action

After the table, add a budget summary line:
Budget: {cumulative_selected}K / {BUDGET_TOTAL/1000}K ({percentage}%) | Deferred: {N} agents ({deferred_total}K est.)

If agents were deferred, include an override option in AskUserQuestion:
Options: Approve, Launch all (override budget), Edit selection, Cancel
```

**Acceptance:** SKILL-compact.md contains Step 1.2c with budget cut logic. Triage table shows Est. Tokens column. Budget summary line present.

---

## Task 4: Add budget-aware triage to full SKILL.md (Phase 1)

**Files:**
- Edit: `plugins/interflux/skills/flux-drive/SKILL.md`

**Step 1: Add equivalent budget logic**

The full SKILL.md delegates to phase files, so add a reference after the Step 1.2 section. Insert after the existing scoring description:

```markdown
### Step 1.2c: Budget-Aware Selection

After scoring and stage assignment, apply budget constraints using `config/flux-drive/budget.yaml` and the cost estimator at `scripts/estimate-costs.sh`. See the compact skill (SKILL-compact.md Step 1.2c) for the complete algorithm.

Key points:
- Budget lookup by INPUT_TYPE (plan, brainstorm, diff-small, diff-large, repo, etc.)
- Per-agent cost from interstat historical data, falling back to budget.yaml defaults
- Slicing multiplier (0.5x) applied for non-cross-cutting agents when slicing is active
- Minimum 2 agents always selected regardless of budget
- Deferred agents shown in triage table with override option
```

**Acceptance:** SKILL.md references Step 1.2c and points to compact skill for the full algorithm.

---

## Task 5: Add cost reporting to synthesis (Phase 3)

**Files:**
- Edit: `plugins/interflux/skills/flux-drive/phases/synthesize.md`

**Step 1: Add Step 3.4b (Cost Report) after Step 3.4a (findings.json)**

Insert after the `findings.json` generation (after line ~146):

```markdown
### Step 3.4b: Generate cost report

After collecting findings and generating findings.json, compile a cost report comparing estimated vs actual token consumption.

**Step 3.4b.1: Collect actual token data**

For each launched agent, query interstat for actual tokens:
```bash
sqlite3 ~/.claude/interstat/metrics.db "
  SELECT agent_name,
         COALESCE(input_tokens,0) + COALESCE(output_tokens,0) as billing_tokens,
         COALESCE(input_tokens,0) + COALESCE(cache_read_tokens,0) + COALESCE(cache_creation_tokens,0) as effective_context
  FROM agent_runs
  WHERE session_id = '{current_session_id}'
    AND agent_name IN ({launched_agents_quoted})
  ORDER BY agent_name;
"
```

**Fallback:** If interstat has no data yet (tokens not backfilled until SessionEnd), use `result_length` as a proxy and note "Actual tokens pending backfill — showing result length."

**Step 3.4b.2: Compute deltas**

For each agent:
```
delta_pct = ((actual - estimated) / estimated) * 100
```

**Step 3.4b.3: Add to findings.json**

Extend the findings.json schema with a `cost_report` field:
```json
{
  "cost_report": {
    "budget": 150000,
    "budget_type": "plan",
    "estimated_total": 120000,
    "actual_total": 115000,
    "agents": [
      {
        "name": "fd-architecture",
        "estimated": 42000,
        "actual": 38000,
        "delta_pct": -10,
        "source": "interstat",
        "slicing_applied": false
      }
    ],
    "deferred": [
      {
        "name": "fd-safety",
        "estimated": 45000,
        "reason": "budget"
      }
    ]
  }
}
```
```

**Step 2: Add cost report to Step 3.5 (Report to User)**

In the report template (around line ~152), add a Cost Report section after the Files section:

```markdown
### Cost Report
| Agent | Estimated | Actual | Delta | Source |
|-------|-----------|--------|-------|--------|
| {agent} | {est}K | {actual}K | {delta}% | {interstat|default} |
| **TOTAL** | **{est_total}K** | **{actual_total}K** | **{delta}%** | |

Budget: {budget_type} ({BUDGET_TOTAL/1000}K). Used: {actual_total/1000}K ({pct}%).
[If agents deferred:] Deferred: {N} agents ({deferred_total/1000}K est.) — override available at triage.
[If actual_total > BUDGET_TOTAL:] ⚠️ Over budget by {(actual_total - BUDGET_TOTAL)/1000}K.
```

**Acceptance:** synthesize.md contains Step 3.4b with cost report logic. Report template includes Cost Report section.

---

## Task 6: Add measurement definitions to AGENTS.md

**Files:**
- Edit: `plugins/interflux/AGENTS.md`

**Step 1: Add Measurement Definitions section**

Add a new top-level section (after Architecture or before Appendix, wherever fits best):

```markdown
## Measurement Definitions

Standard definitions for token metrics used across interflux and companion plugins.

### Token Types
| Type | Field | Description |
|------|-------|-------------|
| Input | `input_tokens` | Tokens sent to the model (prompt + system + tool results) |
| Output | `output_tokens` | Tokens generated by the model |
| Cache Read | `cache_read_tokens` | Previously cached input tokens reused (free for billing) |
| Cache Creation | `cache_creation_tokens` | New tokens added to cache this turn |
| Total | `total_tokens` | All tokens (input + output + cache_read + cache_creation) |

### Cost Types
| Type | Formula | Use For |
|------|---------|---------|
| Billing tokens | `input_tokens + output_tokens` | Cost estimation, budget enforcement |
| Effective context | `input_tokens + cache_read_tokens + cache_creation_tokens` | Context window decisions |

**Critical:** Billing tokens and effective context can differ by 600x+ due to cache hits being free for billing but consuming context. Budget caps use billing tokens (what costs money). Context overflow checks use effective context (what fits in the window).

### Scopes
| Scope | Granularity | Source |
|-------|-------------|--------|
| Per-agent | Single Task dispatch | interstat `agent_runs` table |
| Per-invocation | All agents in one flux-drive run | interstat `v_invocation_summary` |
| Per-session | All tokens in a Claude Code session | Session JSONL |
| Per-sprint | All sessions in a Clavain sprint | Future: interbudget |

### Budget Configuration
See `config/flux-drive/budget.yaml` for token budgets per review type, per-agent defaults, slicing multipliers, and enforcement mode.
```

**Acceptance:** AGENTS.md contains a Measurement Definitions section with Token Types, Cost Types, Scopes, and Budget Configuration reference.

---

## Task 7: Write tests

**Files:**
- Create: `plugins/interflux/tests/test-budget.sh`

**Step 1: Write budget config validation tests**

```bash
#!/usr/bin/env bash
# Test budget configuration and cost estimation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0
FAIL=0

pass() { echo "  ✓ $1"; ((PASS++)); }
fail() { echo "  ✗ $1"; ((FAIL++)); }

echo "=== Budget Configuration Tests ==="

# Test 1: budget.yaml exists and is valid YAML
if python3 -c "import yaml; yaml.safe_load(open('${PLUGIN_DIR}/config/flux-drive/budget.yaml'))" 2>/dev/null; then
  pass "budget.yaml is valid YAML"
else
  fail "budget.yaml is not valid YAML"
fi

# Test 2: budget.yaml has required top-level keys
for key in budgets agent_defaults slicing_multiplier min_agents enforcement; do
  if grep -q "^${key}:" "${PLUGIN_DIR}/config/flux-drive/budget.yaml"; then
    pass "budget.yaml has key: ${key}"
  else
    fail "budget.yaml missing key: ${key}"
  fi
done

# Test 3: All input types have budgets
for type in plan brainstorm prd spec diff-small diff-large repo other; do
  if grep -q "  ${type}:" "${PLUGIN_DIR}/config/flux-drive/budget.yaml"; then
    pass "Budget defined for type: ${type}"
  else
    fail "Budget missing for type: ${type}"
  fi
done

# Test 4: All agent categories have defaults
for cat in review cognitive research oracle generated; do
  if grep -q "  ${cat}:" "${PLUGIN_DIR}/config/flux-drive/budget.yaml"; then
    pass "Default estimate for category: ${cat}"
  else
    fail "Default estimate missing for category: ${cat}"
  fi
done

# Test 5: estimate-costs.sh exists and is executable
if [[ -x "${PLUGIN_DIR}/scripts/estimate-costs.sh" ]]; then
  pass "estimate-costs.sh is executable"
else
  fail "estimate-costs.sh is not executable"
fi

# Test 6: estimate-costs.sh produces valid JSON
OUTPUT=$(bash "${PLUGIN_DIR}/scripts/estimate-costs.sh" 2>/dev/null || echo "SCRIPT_FAILED")
if [[ "$OUTPUT" != "SCRIPT_FAILED" ]] && echo "$OUTPUT" | jq -e '.defaults' >/dev/null 2>&1; then
  pass "estimate-costs.sh produces valid JSON with defaults"
else
  fail "estimate-costs.sh did not produce valid JSON"
fi

# Test 7: estimate-costs.sh handles --slicing flag
OUTPUT=$(bash "${PLUGIN_DIR}/scripts/estimate-costs.sh" --slicing 2>/dev/null || echo "SCRIPT_FAILED")
if [[ "$OUTPUT" != "SCRIPT_FAILED" ]] && echo "$OUTPUT" | jq -e '.slicing_multiplier' >/dev/null 2>&1; then
  MULT=$(echo "$OUTPUT" | jq -r '.slicing_multiplier')
  if [[ "$MULT" == "0.5" ]]; then
    pass "Slicing multiplier is 0.5"
  else
    fail "Slicing multiplier is $MULT (expected 0.5)"
  fi
else
  fail "estimate-costs.sh --slicing failed"
fi

# Test 8: SKILL-compact.md references Step 1.2c
if grep -q "Step 1.2c" "${PLUGIN_DIR}/skills/flux-drive/SKILL-compact.md"; then
  pass "SKILL-compact.md references Step 1.2c (budget cut)"
else
  fail "SKILL-compact.md missing Step 1.2c reference"
fi

# Test 9: SKILL-compact.md mentions Est. Tokens in triage table
if grep -q "Est. Tokens" "${PLUGIN_DIR}/skills/flux-drive/SKILL-compact.md"; then
  pass "Triage table includes Est. Tokens column"
else
  fail "Triage table missing Est. Tokens column"
fi

# Test 10: synthesize.md references cost report
if grep -q "Cost Report\|cost_report\|Step 3.4b" "${PLUGIN_DIR}/skills/flux-drive/phases/synthesize.md"; then
  pass "synthesize.md references cost report"
else
  fail "synthesize.md missing cost report reference"
fi

# Test 11: AGENTS.md contains Measurement Definitions
if grep -q "Measurement Definitions" "${PLUGIN_DIR}/AGENTS.md"; then
  pass "AGENTS.md contains Measurement Definitions"
else
  fail "AGENTS.md missing Measurement Definitions"
fi

# Test 12: min_agents >= 2
MIN=$(grep "^min_agents:" "${PLUGIN_DIR}/config/flux-drive/budget.yaml" | sed 's/.*: *//' | tr -d '[:space:]')
if [[ "$MIN" -ge 2 ]]; then
  pass "min_agents is >= 2 (value: $MIN)"
else
  fail "min_agents is < 2 (value: $MIN)"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
```

Make executable: `chmod +x plugins/interflux/tests/test-budget.sh`

**Acceptance:** All 12 tests pass.

---

## Implementation Order

Tasks 1-2 are independent (config + script). Task 3-4 depend on 1-2 (triage needs budget config + estimator). Task 5 depends on 3-4 (synthesis reports what triage decided). Task 6 is independent (documentation). Task 7 validates everything.

Parallelizable: Tasks 1+2 in parallel, then Tasks 3+4+6 in parallel, then Task 5, then Task 7.
