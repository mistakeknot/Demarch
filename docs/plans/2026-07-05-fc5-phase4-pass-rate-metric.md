# fc5 Phase 4 — plan→execution pass-rate metric in interspect (Sylveste-fc5.4)

Execution-grade plan. Author: fable. Repos touched: `interverse/interspect` (primary) and `os/Clavain` (one block appended to quality-gates.md). Do NOT run git commands. Depends on Phase 3 (criteria-results artifact + plan-conformance verdict must exist in the working tree).

**Context (verified review findings):** the doctrine's metric (Rule 7) must be plan→execution pass rate, not shipped count. f-027 (top finding): escalation censors the executor-tier sample — record `escalation_count` and the FINAL executor tier per outcome, from the chain state Phase 2 built. f-036: aggregation needs a validator axis or validator drift reads as executor improvement. f-043: reuse the existing `source_weight` classifier (0.5/0.7/1.0) so pilot-era rows don't pool at full weight. f-008/f-028: an explicit `min_n` distinct from the B3 `>=3 sessions` precedent. Evidence conventions: event names end in `_outcome`; write via `_interspect_insert_evidence` (10-arg signature, quarantine applies); per-metric JSON output carries `schema_version`.

## Step 1 — evidence emission: append to `os/Clavain/commands/quality-gates.md` Phase 2b

At the end of the Phase 2b section Phase 3 added (after the plan-conformance verdict write), append:

~~~markdown
**Record the plan→execution outcome** (fc5.4 — the doctrine's Rule-7 metric; silent on error):

```bash
_il="${INTERSPECT_LIB:-$(git rev-parse --show-toplevel 2>/dev/null)/interverse/interspect/hooks/lib-interspect.sh}"
if [[ -f "$_il" ]]; then
  source "$_il"
  _interspect_ensure_db 2>/dev/null || true
  _author=$(bd state "$CLAVAIN_BEAD_ID" plan_author_model 2>/dev/null | tr -d '[:space:]') || _author=""
  [[ -z "$_author" || "$_author" == *"(no"* ]] && _author="unknown"
  _executor="${CLAUDE_MODEL:-${ANTHROPIC_MODEL:-unknown}}"
  _crit_total=$(grep -cE '^\| *[0-9]' "$results_path" 2>/dev/null || echo 0)
  _crit_failed=$(grep -cE '\| *fail' "$results_path" 2>/dev/null || echo 0)
  _esc=0
  if command -v ic >/dev/null 2>&1 && [[ -n "${CLAVAIN_BEAD_ID:-}" ]]; then
    _chain=$(ic state get "dispatch.chain.${CLAVAIN_BEAD_ID}" escalation 2>/dev/null) || _chain=""
    [[ -n "$_chain" ]] && _esc=$(printf '%s' "$_chain" | jq -r '.escalations // 0' 2>/dev/null || echo 0)
  fi
  _src=$(_interspect_classify_session_source "$CLAVAIN_BEAD_ID" 2>/dev/null) || _src="normal"
  _ctx=$(jq -nc --arg a "$_author" --arg e "$_executor" --arg v "opus" \
    --argjson ct "${_crit_total:-0}" --argjson cf "${_crit_failed:-0}" --argjson esc "${_esc:-0}" \
    --arg src "$_src" --arg bead "$CLAVAIN_BEAD_ID" --arg cp "${criteria_path:-}" \
    '{author_model:$a, executor_model:$e, validator_model:$v, criteria_total:$ct, criteria_failed:$cf, pass:($cf==0 and $ct>0), escalation_count:$esc, session_source:$src, bead:$bead, criteria_path:$cp}')
  _interspect_insert_evidence "${CLAUDE_SESSION_ID:-unknown}" "quality-gates" "plan_execution_outcome" "" "$_ctx" 2>/dev/null || true
fi
```
~~~

Note: `$results_path` and `$criteria_path` are in scope from Phase 2b. `validator_model` is `"opus"` because Phase 2b pins the validator tier (f-036: the axis is recorded even though it is currently constant — the drift check needs it the day it varies).

## Step 2 — stats reader: `interverse/interspect/hooks/lib-interspect.sh`

Add after `_interspect_compute_delegation_stats` (find it near line 3788; mirror its structure exactly):

```bash
# --- Plan→execution pass rate (fc5.4, capability-routing doctrine Rule 7) ---
# Aggregates plan_execution_outcome evidence per (author, executor, validator)
# tier triple. Weights rows by session_source (f-043: pilot/self-building-era
# evidence discounted 0.5/0.7 vs normal 1.0). Explicit min_n distinct from the
# B3 >=3-sessions precedent (f-008/f-028).
_interspect_compute_plan_execution_stats() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    [[ -f "$db" ]] || { echo '{"sufficient_data":false,"total":0}'; return 0; }
    local min_n="${INTERSPECT_PLAN_EXEC_MIN_N:-5}"

    sqlite3 -json "$db" "
        SELECT
            json_extract(context, '\$.author_model')    AS author,
            json_extract(context, '\$.executor_model')  AS executor,
            json_extract(context, '\$.validator_model') AS validator,
            json_extract(context, '\$.pass')            AS pass,
            json_extract(context, '\$.escalation_count') AS escalations,
            json_extract(context, '\$.session_source')  AS session_source
        FROM evidence
        WHERE event='plan_execution_outcome'
          AND (quarantine_until IS NULL OR quarantine_until <= strftime('%s','now'));
    " 2>/dev/null | python3 -c "
import json, sys, collections
rows = json.load(sys.stdin) if sys.stdin.read(1) else []
sys.stdin.seek(0) if hasattr(sys.stdin, 'seek') else None
" 2>/dev/null || true

    # NOTE FOR EXECUTOR: the python inline above is a placeholder marker —
    # implement the aggregation as a single python3 heredoc exactly like the
    # existing _interspect_compute_agent_scores does (grep how it feeds sqlite
    # -json output into python3). Aggregation spec:
    #   weights = {'bootstrap':0.5, 'self-building':0.7, 'normal':1.0}
    #   key = (author, executor, validator) tier triple (f-036: validator axis kept)
    #   per cell: n, weighted_pass_rate = sum(w*pass)/sum(w), escalated = count(escalations>0)
    #   overall: total n, weighted overall pass rate
    #   sufficient_data = total >= min_n
    # Output ONE compact JSON object:
    #   {"sufficient_data":bool, "total":N, "min_n":N, "overall_pass_rate":x,
    #    "cells":{"author|executor|validator":{"n":..,"weighted_pass_rate":..,"escalated":..}, ...}}
}

_interspect_write_plan_execution_calibration() {
    local stats out root
    stats=$(_interspect_compute_plan_execution_stats) || return 0
    root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}" || root=""
    [[ -z "$root" ]] && return 0
    out="${root}/.clavain/interspect/plan-execution-calibration.json"
    printf '%s' "$stats" | jq --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{schema_version: 1, generated_at: $ts} + .' > "${out}.tmp" 2>/dev/null && mv "${out}.tmp" "$out"
}
```

Implement the aggregation python for real (replace the placeholder marker) following `_interspect_compute_agent_scores`'s sqlite→python pattern. Retention (f-030, cheap version): at the top of `_interspect_compute_plan_execution_stats` after the db check, add:
```bash
    _interspect_sqlite_write "$db" "DELETE FROM evidence WHERE event='plan_execution_outcome' AND ts < datetime('now','-180 days');" 2>/dev/null || true
```

## Step 3 — calibrate + status surfacing

**`interverse/interspect/commands/calibrate.md`**: after the delegation-calibration step (`_interspect_write_delegation_calibration` at ~line 81), add:

~~~markdown
### Plan→execution pass rate (capability-routing doctrine)

```bash
_interspect_write_plan_execution_calibration 2>/dev/null || true
pe_stats=$(_interspect_compute_plan_execution_stats)
if [[ "$(echo "$pe_stats" | jq -r '.sufficient_data')" == "true" ]]; then
  echo "Plan→execution pass rate (weighted): $(echo "$pe_stats" | jq -r '.overall_pass_rate') over $(echo "$pe_stats" | jq -r '.total') outcomes"
  echo "$pe_stats" | jq -r '.cells | to_entries[] | [.key, (.value.n|tostring), (.value.weighted_pass_rate|tostring), (.value.escalated|tostring)] | @tsv' | column -t -s$'\t'
else
  echo "Plan→execution: insufficient data ($(echo "$pe_stats" | jq -r '.total')/$(echo "$pe_stats" | jq -r '.min_n // 5') outcomes) — pilot still filling the sample (doctrine Rule 6)"
fi
```
~~~

**`interverse/interspect/commands/delegation-status.md`**: append a short final section:

~~~markdown
## Plan→Execution (capability routing)

```bash
PE="${ROOT}/.clavain/interspect/plan-execution-calibration.json"
if [[ -f "$PE" ]]; then
  jq -r '"Overall: " + (.overall_pass_rate|tostring) + " (n=" + (.total|tostring) + ", min_n=" + (.min_n|tostring) + ")"' "$PE"
  jq -r '.cells | to_entries[] | .key + "  n=" + (.value.n|tostring) + "  pass=" + (.value.weighted_pass_rate|tostring) + "  escalated=" + (.value.escalated|tostring)' "$PE"
else
  echo "No plan-execution calibration yet — run /interspect:calibrate after quality-gates has recorded plan_execution_outcome evidence."
fi
```
~~~

## Step 4 — functional test: `interverse/interspect/tests/plan-execution-metric-test.sh` (new; if a tests/ convention already exists, place it accordingly)

```sh
#!/usr/bin/env bash
# fc5.4 acceptance: plan_execution_outcome aggregation with source weighting.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
export _INTERSPECT_DB="$tmp/interspect.db"
export INTERSPECT_QUARANTINE_HOURS=0
export INTERSPECT_PLAN_EXEC_MIN_N=3
source hooks/lib-interspect.sh
_interspect_ensure_db >/dev/null 2>&1 || true

ins() { # pass|fail  source  escalations
  local pass="$1" src="$2" esc="$3"
  local ctx
  ctx=$(jq -nc --arg a fable --arg e sonnet --arg v opus --argjson p "$pass" --argjson esc "$esc" --arg s "$src" \
    '{author_model:$a,executor_model:$e,validator_model:$v,criteria_total:3,criteria_failed:(if $p then 0 else 1 end),pass:$p,escalation_count:$esc,session_source:$s,bead:"t"}')
  _interspect_insert_evidence "sess-$RANDOM" "quality-gates" "plan_execution_outcome" "" "$ctx"
}
ins true normal 0; ins true normal 0; ins false normal 1; ins true bootstrap 0

stats=$(_interspect_compute_plan_execution_stats)
fail() { echo "FAIL: $1 — got: $stats" >&2; exit 1; }
[[ "$(echo "$stats" | jq -r '.total')" == "4" ]] || fail "total != 4"
[[ "$(echo "$stats" | jq -r '.sufficient_data')" == "true" ]] || fail "sufficient_data (min_n=3) not true"
[[ "$(echo "$stats" | jq -r '.cells | keys | length')" == "1" ]] || fail "expected 1 tier-triple cell"
# weighted: (1+1+0+0.5*1)/(1+1+1+0.5) = 2.5/3.5 ≈ 0.714 — bootstrap discounted (f-043)
wpr=$(echo "$stats" | jq -r '.cells[] | .weighted_pass_rate')
python3 -c "import sys; v=float('$wpr'); sys.exit(0 if abs(v-0.714)<0.02 else 1)" || fail "weighted_pass_rate $wpr != ~0.714 (source weighting broken)"
[[ "$(echo "$stats" | jq -r '.cells[] | .escalated')" == "1" ]] || fail "escalated count != 1 (f-027 attribution)"
echo "PASS: plan-execution metric suite"
```
`chmod +x`. Note: `_interspect_ensure_db` uses `_INTERSPECT_DB`? — verify: the lib resolves via `_interspect_db_path` unless `_INTERSPECT_DB` is already set; `_interspect_insert_evidence` honors `${_INTERSPECT_DB:-...}` (confirmed at line 2990). If `_interspect_ensure_db` ignores the override and writes elsewhere, create the schema directly in the test (`sqlite3 "$_INTERSPECT_DB" < <(sed -n '/CREATE TABLE IF NOT EXISTS evidence/,/;/p' hooks/lib-interspect.sh)`) — the test must exercise the REAL insert + compute functions either way.

## Acceptance Criteria (validator: mechanical, pass/fail)

1. **emission-wired**: `grep -n 'plan_execution_outcome' os/Clavain/commands/quality-gates.md` shows the `_interspect_insert_evidence` call inside Phase 2b; the context JSON includes `author_model`, `executor_model`, `validator_model`, `escalation_count`, `session_source` (grep each key in the block).
2. **escalation-attribution**: the quality-gates block reads `dispatch.chain.<bead>` via `ic state get` for `escalation_count` (grep `dispatch.chain` in quality-gates.md) — f-027's attribution decision, wired to Phase 2's chain state.
3. **stats-fn**: `bash -n interverse/interspect/hooks/lib-interspect.sh` clean; `grep -n '_interspect_compute_plan_execution_stats' hooks/lib-interspect.sh` shows the function; `grep -n "'-180 days'" hooks/lib-interspect.sh` shows retention (f-030).
4. **validator-axis**: the aggregation key includes validator (grep `validator` inside the new stats function) — f-036.
5. **weighting**: the weights `0.5`/`0.7`/`1.0` appear in the new aggregation (f-043), and **functional-test** `bash interverse/interspect/tests/plan-execution-metric-test.sh` prints `PASS: plan-execution metric suite` and exits 0 (this test proves weighting + escalation attribution end-to-end).
6. **min-n-explicit**: `grep -n 'INTERSPECT_PLAN_EXEC_MIN_N' hooks/lib-interspect.sh` hits with default 5 (f-008/f-028).
7. **calibrate-surfaced**: `grep -n 'plan_execution' interverse/interspect/commands/calibrate.md` and `grep -n 'plan-execution-calibration.json' interverse/interspect/commands/delegation-status.md` both hit.
8. **schema-version**: `grep -n 'schema_version: 1' hooks/lib-interspect.sh` appears in the calibration writer (per-metric JSON convention).
9. **no-commits**: `git -C /Users/sma/projects/Sylveste/interverse/interspect log --oneline -1` and `git -C /Users/sma/projects/Sylveste/os/Clavain log --oneline -1` unchanged from before execution.
