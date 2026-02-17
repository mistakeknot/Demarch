# Interspect Canary Monitoring Implementation Plan

**Bead:** iv-cylo
**Phase:** executing (as of 2026-02-16T20:08:58Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Implement active canary monitoring for routing overrides — compute baselines, collect samples, detect degradation, and surface alerts.

**Architecture:** Extends existing lib-interspect.sh with canary functions. Session-end hook collects samples, session-start hook checks alerts, `/interspect:status` shows details. All metrics computed from the existing evidence + sessions tables. New `canary_samples` table stores per-session snapshots.

**Tech Stack:** Bash (lib-interspect.sh), SQLite (evidence/canary/canary_samples), jq, bats (tests)

**PRD:** `docs/prds/2026-02-16-interspect-canary-monitoring.md`
**Brainstorm:** `docs/brainstorms/2026-02-16-interspect-canary-monitoring-brainstorm.md`

**Revision:** v2 — 2026-02-16. Revised to address findings from 3-agent review (fd-correctness, fd-quality, fd-user-product). Key fixes: SQL escape `before_ts` (P0), flock protection for sample collection (P0), config bounds checking (P0), remove `set -e` under flock (P1), `INSERT OR IGNORE` dedup (P1), additional tests.

**Reviews:** `docs/research/review-canary-monitoring-plan.md`, `docs/research/review-plan-for-quality.md`, `docs/research/review-prd-with-flux-drive.md`

---

## Task 1: DB Schema Extension + Configuration

**Files:**
- Modify: `hub/clavain/hooks/lib-interspect.sh` (DB schema, confidence loading)
- Modify: `hub/clavain/.clavain/interspect/confidence.json`

**Step 1: Add canary_samples table to DB schema**

In `_interspect_ensure_db()`, add the `canary_samples` table in both the migration block (for existing DBs, after the blacklist migration ~line 57) AND the fresh-create block (after the canary table ~line 106):

```sql
CREATE TABLE IF NOT EXISTS canary_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    override_rate REAL,
    fp_rate REAL,
    finding_density REAL,
    UNIQUE(canary_id, session_id)
);
CREATE INDEX IF NOT EXISTS idx_canary_samples_canary ON canary_samples(canary_id);
```

The `UNIQUE(canary_id, session_id)` constraint prevents duplicate samples.

**Step 2: Extend confidence.json with canary thresholds**

Update `hub/clavain/.clavain/interspect/confidence.json`:

```json
{
  "min_sessions": 3,
  "min_diversity": 2,
  "min_events": 5,
  "min_agent_wrong_pct": 80,
  "canary_window_uses": 20,
  "canary_window_days": 14,
  "canary_min_baseline": 15,
  "canary_alert_pct": 20,
  "canary_noise_floor": 0.1,
  "_comment": "Counting-rule + canary thresholds. canary_alert_pct = % degradation to trigger alert."
}
```

**Step 3: Extend `_interspect_load_confidence` with canary fields**

After the existing `_INTERSPECT_MIN_AGENT_WRONG_PCT` loading (~line 298), add:

```bash
_INTERSPECT_CANARY_WINDOW_USES=20
_INTERSPECT_CANARY_WINDOW_DAYS=14
_INTERSPECT_CANARY_MIN_BASELINE=15
_INTERSPECT_CANARY_ALERT_PCT=20
_INTERSPECT_CANARY_NOISE_FLOOR="0.1"
```

And in the `if [[ -f "$conf" ]]` block, add:

```bash
_INTERSPECT_CANARY_WINDOW_USES=$(jq -r '.canary_window_uses // 20' "$conf")
_INTERSPECT_CANARY_WINDOW_DAYS=$(jq -r '.canary_window_days // 14' "$conf")
_INTERSPECT_CANARY_MIN_BASELINE=$(jq -r '.canary_min_baseline // 15' "$conf")
_INTERSPECT_CANARY_ALERT_PCT=$(jq -r '.canary_alert_pct // 20' "$conf")
_INTERSPECT_CANARY_NOISE_FLOOR=$(jq -r '.canary_noise_floor // "0.1"' "$conf")
```

**Step 4: Run syntax check**

```bash
bash -n hub/clavain/hooks/lib-interspect.sh
```

**Step 5: Commit**

```bash
git add hub/clavain/hooks/lib-interspect.sh hub/clavain/.clavain/interspect/confidence.json
git commit -m "feat(interspect): add canary_samples table + canary config to confidence.json"
```

---

## Task 2: Baseline Computation (F1)

**Files:**
- Modify: `hub/clavain/hooks/lib-interspect.sh` (add baseline function, update apply flow)

**Step 1: Add baseline computation function**

Add after the existing canary-related code (after `_interspect_apply_override_locked`, ~line 703):

```bash
# ─── Canary Monitoring ──────────────────────────────────────────────────────

# Compute canary baseline metrics from historical evidence.
# Uses the last N sessions (configurable) before a given timestamp.
# Args: $1=before_ts (ISO 8601), $2=project (optional, filters by project)
# Output: JSON object with baseline metrics or null if insufficient data
# Example: {"override_rate":0.5,"fp_rate":0.3,"finding_density":2.1,"window":"2026-01-01..2026-02-15","session_count":18}
_interspect_compute_canary_baseline() {
    _interspect_load_confidence
    local before_ts="$1"
    local project="${2:-}"
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    local min_baseline="${_INTERSPECT_CANARY_MIN_BASELINE:-15}"
    local window_size="${_INTERSPECT_CANARY_WINDOW_USES:-20}"

    # Get session IDs for the baseline window
    local project_filter=""
    if [[ -n "$project" ]]; then
        local escaped_project
        escaped_project=$(_interspect_sql_escape "$project")
        project_filter="AND project = '${escaped_project}'"
    fi

    local session_count
    session_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM sessions WHERE start_ts < '${before_ts}' ${project_filter};")

    if (( session_count < min_baseline )); then
        echo "null"
        return 0
    fi

    # Get the baseline window boundaries
    local window_start window_end
    window_end="$before_ts"
    window_start=$(sqlite3 "$db" "SELECT start_ts FROM sessions WHERE start_ts < '${before_ts}' ${project_filter} ORDER BY start_ts DESC LIMIT 1 OFFSET $((window_size - 1));" 2>/dev/null)
    [[ -z "$window_start" ]] && window_start=$(sqlite3 "$db" "SELECT MIN(start_ts) FROM sessions WHERE start_ts < '${before_ts}' ${project_filter};")

    # Session IDs in the window
    local session_ids_sql="SELECT session_id FROM sessions WHERE start_ts < '${before_ts}' ${project_filter} ORDER BY start_ts DESC LIMIT ${window_size}"

    # Override rate: overrides per session
    local total_overrides total_sessions_in_window override_rate
    total_overrides=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE event = 'override' AND session_id IN (${session_ids_sql});")
    total_sessions_in_window=$(sqlite3 "$db" "SELECT COUNT(*) FROM (${session_ids_sql});")

    if (( total_sessions_in_window == 0 )); then
        echo "null"
        return 0
    fi

    # Use awk for floating-point division (bash can't do it)
    override_rate=$(awk "BEGIN {printf \"%.4f\", ${total_overrides} / ${total_sessions_in_window}}")

    # FP rate: agent_wrong / total overrides
    local agent_wrong_count fp_rate
    agent_wrong_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE event = 'override' AND override_reason = 'agent_wrong' AND session_id IN (${session_ids_sql});")

    if (( total_overrides == 0 )); then
        fp_rate="0.0"
    else
        fp_rate=$(awk "BEGIN {printf \"%.4f\", ${agent_wrong_count} / ${total_overrides}}")
    fi

    # Finding density: total evidence events per session
    local total_evidence finding_density
    total_evidence=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE session_id IN (${session_ids_sql});")
    finding_density=$(awk "BEGIN {printf \"%.4f\", ${total_evidence} / ${total_sessions_in_window}}")

    # Output as JSON
    jq -n \
        --argjson override_rate "$override_rate" \
        --argjson fp_rate "$fp_rate" \
        --argjson finding_density "$finding_density" \
        --arg window "${window_start}..${window_end}" \
        --argjson session_count "$total_sessions_in_window" \
        '{override_rate:$override_rate,fp_rate:$fp_rate,finding_density:$finding_density,window:$window,session_count:$session_count}'
}
```

**Step 2: Update `_interspect_apply_override_locked` to compute baseline**

Inside `_interspect_apply_override_locked`, replace the canary INSERT block (~line 691) with a version that computes baseline first:

Find the block that starts with `# Canary record` (~line 682) and replace it with:

```bash
        # Canary record — compute baseline BEFORE insert
        local baseline_json
        baseline_json=$(_interspect_compute_canary_baseline "$ts" "" 2>/dev/null || echo "null")

        local b_override_rate b_fp_rate b_finding_density b_window
        if [[ "$baseline_json" != "null" ]]; then
            b_override_rate=$(echo "$baseline_json" | jq -r '.override_rate')
            b_fp_rate=$(echo "$baseline_json" | jq -r '.fp_rate')
            b_finding_density=$(echo "$baseline_json" | jq -r '.finding_density')
            b_window=$(echo "$baseline_json" | jq -r '.window')
        else
            b_override_rate="NULL"
            b_fp_rate="NULL"
            b_finding_density="NULL"
            b_window="NULL"
        fi

        local expires_at
        expires_at=$(date -u -d "+${_INTERSPECT_CANARY_WINDOW_DAYS:-14} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
            || date -u -v+${_INTERSPECT_CANARY_WINDOW_DAYS:-14}d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
        if [[ -z "$expires_at" ]]; then
            echo "ERROR: date command does not support relative dates" >&2
            return 1
        fi

        # Build INSERT with conditional NULLs for baseline
        local baseline_values
        if [[ "$b_override_rate" == "NULL" ]]; then
            baseline_values="NULL, NULL, NULL, NULL"
        else
            local escaped_window
            escaped_window=$(_interspect_sql_escape "$b_window")
            baseline_values="${b_override_rate}, ${b_fp_rate}, ${b_finding_density}, '${escaped_window}'"
        fi

        if ! sqlite3 "$db" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, window_expires_at, baseline_override_rate, baseline_fp_rate, baseline_finding_density, baseline_window, status)
            VALUES ('${filepath}', '${commit_sha}', '${escaped_agent}', '${ts}', ${_INTERSPECT_CANARY_WINDOW_USES:-20}, '${expires_at}', ${baseline_values}, 'active');"; then
            sqlite3 "$db" "UPDATE modifications SET status = 'applied-unmonitored' WHERE commit_sha = '${commit_sha}';" 2>/dev/null || true
            echo "WARN: Canary monitoring failed — override active but unmonitored." >&2
        fi
```

**Step 3: Run syntax check**

```bash
bash -n hub/clavain/hooks/lib-interspect.sh
```

**Step 4: Commit**

```bash
git add hub/clavain/hooks/lib-interspect.sh
git commit -m "feat(interspect): add canary baseline computation + wire into apply flow"
```

---

## Task 3: Sample Collection (F2)

**Files:**
- Modify: `hub/clavain/hooks/lib-interspect.sh` (add sample recording function)
- Modify: `hub/clavain/hooks/interspect-session-end.sh` (call sample recording)

**Step 1: Add sample recording function to lib-interspect.sh**

Add after `_interspect_compute_canary_baseline`:

```bash
# Record a canary sample for the current session.
# Computes per-session metrics and stores them in canary_samples.
# Called from session-end hook when active canaries exist.
# Args: $1=session_id
# Returns: 0 on success (or no work to do), 1 on error
_interspect_record_canary_sample() {
    local session_id="$1"
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    local escaped_sid
    escaped_sid=$(_interspect_sql_escape "$session_id")

    # Check if this session had any evidence events (qualifies as a "use")
    local event_count
    event_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE session_id = '${escaped_sid}';")
    if (( event_count == 0 )); then
        return 0  # Not a flux-drive use — skip
    fi

    # Get active canaries
    local canary_ids
    canary_ids=$(sqlite3 "$db" "SELECT id FROM canary WHERE status = 'active';")
    [[ -z "$canary_ids" ]] && return 0

    # Compute per-session metrics
    local override_count agent_wrong_count override_rate fp_rate finding_density

    override_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE session_id = '${escaped_sid}' AND event = 'override';")
    agent_wrong_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE session_id = '${escaped_sid}' AND event = 'override' AND override_reason = 'agent_wrong';")

    # Override rate: overrides in this session (per-session = raw count, normalized later)
    override_rate=$(awk "BEGIN {printf \"%.4f\", ${override_count} + 0}")

    # FP rate: agent_wrong / total overrides (for this session)
    if (( override_count == 0 )); then
        fp_rate="0.0"
    else
        fp_rate=$(awk "BEGIN {printf \"%.4f\", ${agent_wrong_count} / ${override_count}}")
    fi

    # Finding density: total events in this session
    finding_density=$(awk "BEGIN {printf \"%.4f\", ${event_count} + 0}")

    local ts
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Insert sample for each active canary + increment uses_so_far
    local canary_id
    while IFS= read -r canary_id; do
        [[ -z "$canary_id" ]] && continue

        # Dedup: skip if sample already exists for this (canary_id, session_id)
        local exists
        exists=$(sqlite3 "$db" "SELECT COUNT(*) FROM canary_samples WHERE canary_id = ${canary_id} AND session_id = '${escaped_sid}';")
        if (( exists > 0 )); then
            continue
        fi

        sqlite3 "$db" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (${canary_id}, '${escaped_sid}', '${ts}', ${override_rate}, ${fp_rate}, ${finding_density});" 2>/dev/null || continue

        # Increment uses_so_far
        sqlite3 "$db" "UPDATE canary SET uses_so_far = uses_so_far + 1 WHERE id = ${canary_id};" 2>/dev/null || true
    done <<< "$canary_ids"

    return 0
}
```

**Step 2: Update interspect-session-end.sh**

After the existing session-end update (~line 36), add canary sample collection:

```bash
# Record canary samples (if any active canaries exist)
_interspect_record_canary_sample "$SESSION_ID" 2>/dev/null || true
```

This goes before the final `exit 0`.

**Step 3: Run syntax checks**

```bash
bash -n hub/clavain/hooks/lib-interspect.sh
bash -n hub/clavain/hooks/interspect-session-end.sh
```

**Step 4: Commit**

```bash
git add hub/clavain/hooks/lib-interspect.sh hub/clavain/hooks/interspect-session-end.sh
git commit -m "feat(interspect): add canary sample collection in session-end hook"
```

---

## Task 4: Degradation Detection (F3)

**Files:**
- Modify: `hub/clavain/hooks/lib-interspect.sh` (add evaluation + expiry functions)

**Step 1: Add canary evaluation function**

Add after `_interspect_record_canary_sample`:

```bash
# Evaluate a single canary — compare samples against baseline.
# Args: $1=canary_id
# Output: JSON object with verdict
# Example: {"canary_id":1,"agent":"fd-game-design","status":"passed","reason":"All metrics within threshold","metrics":{...}}
_interspect_evaluate_canary() {
    _interspect_load_confidence
    local canary_id="$1"
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    local alert_pct="${_INTERSPECT_CANARY_ALERT_PCT:-20}"
    local noise_floor="${_INTERSPECT_CANARY_NOISE_FLOOR:-0.1}"

    # Get canary record
    local canary_row
    canary_row=$(sqlite3 -separator '|' "$db" "SELECT group_id, baseline_override_rate, baseline_fp_rate, baseline_finding_density, uses_so_far, window_uses, status FROM canary WHERE id = ${canary_id};")
    [[ -z "$canary_row" ]] && { echo '{"error":"canary_not_found"}'; return 1; }

    IFS='|' read -r agent b_or b_fp b_fd uses_so_far window_uses current_status <<< "$canary_row"

    # Already resolved
    if [[ "$current_status" != "active" ]]; then
        echo "{\"canary_id\":${canary_id},\"agent\":\"${agent}\",\"status\":\"${current_status}\",\"reason\":\"Already resolved\"}"
        return 0
    fi

    # Insufficient baseline
    if [[ -z "$b_or" ]] || [[ "$b_or" == "" ]]; then
        echo "{\"canary_id\":${canary_id},\"agent\":\"${agent}\",\"status\":\"monitoring\",\"reason\":\"Insufficient baseline — collecting data\",\"uses_so_far\":${uses_so_far},\"window_uses\":${window_uses}}"
        return 0
    fi

    # Not enough samples yet
    if (( uses_so_far < window_uses )); then
        # Check time-based expiry
        local expires_at
        expires_at=$(sqlite3 "$db" "SELECT window_expires_at FROM canary WHERE id = ${canary_id};")
        local now
        now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        if [[ "$now" < "$expires_at" ]]; then
            echo "{\"canary_id\":${canary_id},\"agent\":\"${agent}\",\"status\":\"monitoring\",\"reason\":\"${uses_so_far}/${window_uses} uses\",\"uses_so_far\":${uses_so_far},\"window_uses\":${window_uses}}"
            return 0
        fi
        # Time expired — evaluate with what we have
    fi

    # No samples collected (expired unused)
    local sample_count
    sample_count=$(sqlite3 "$db" "SELECT COUNT(*) FROM canary_samples WHERE canary_id = ${canary_id};")
    if (( sample_count == 0 )); then
        sqlite3 "$db" "UPDATE canary SET status = 'expired_unused', verdict_reason = 'No sessions during monitoring window' WHERE id = ${canary_id};"
        echo "{\"canary_id\":${canary_id},\"agent\":\"${agent}\",\"status\":\"expired_unused\",\"reason\":\"No sessions during monitoring window\"}"
        return 0
    fi

    # Compute averages from samples
    local avg_or avg_fp avg_fd
    avg_or=$(sqlite3 "$db" "SELECT printf('%.4f', AVG(override_rate)) FROM canary_samples WHERE canary_id = ${canary_id};")
    avg_fp=$(sqlite3 "$db" "SELECT printf('%.4f', AVG(fp_rate)) FROM canary_samples WHERE canary_id = ${canary_id};")
    avg_fd=$(sqlite3 "$db" "SELECT printf('%.4f', AVG(finding_density)) FROM canary_samples WHERE canary_id = ${canary_id};")

    # Compare each metric: alert if degraded by >alert_pct% AND above noise floor
    local verdict="passed"
    local reasons=""

    # Helper: check if metric degraded
    # For override_rate and fp_rate: INCREASE = degradation
    # For finding_density: DECREASE = degradation (fewer findings = potential gap)
    local check_degradation
    check_degradation() {
        local metric_name="$1" baseline="$2" current="$3" direction="$4"
        local diff threshold

        diff=$(awk "BEGIN {printf \"%.4f\", ${current} - ${baseline}}")
        local abs_diff
        abs_diff=$(awk "BEGIN {d = ${diff}; if (d < 0) d = -d; printf \"%.4f\", d}")

        # Below noise floor — ignore
        if awk "BEGIN {exit !(${abs_diff} < ${noise_floor})}"; then
            return 0
        fi

        # Check direction
        if [[ "$direction" == "increase" ]]; then
            # Degradation = current > baseline * (1 + threshold)
            threshold=$(awk "BEGIN {printf \"%.4f\", ${baseline} * ${alert_pct} / 100}")
            if awk "BEGIN {exit !(${current} > ${baseline} + ${threshold})}"; then
                return 0
            fi
            reasons="${reasons}${metric_name}: ${baseline} → ${current} (+$(awk "BEGIN {if (${baseline} > 0) printf \"%.0f\", (${current} - ${baseline}) / ${baseline} * 100; else print \"inf\"}")%); "
            return 1
        else
            # Degradation = current < baseline * (1 - threshold)
            threshold=$(awk "BEGIN {printf \"%.4f\", ${baseline} * ${alert_pct} / 100}")
            if awk "BEGIN {exit !(${current} < ${baseline} - ${threshold})}"; then
                return 0
            fi
            reasons="${reasons}${metric_name}: ${baseline} → ${current} ($(awk "BEGIN {if (${baseline} > 0) printf \"%.0f\", (${current} - ${baseline}) / ${baseline} * 100; else print \"-inf\"}")%); "
            return 1
        fi
    }

    if ! check_degradation "override_rate" "$b_or" "$avg_or" "increase"; then
        verdict="alert"
    fi
    if ! check_degradation "fp_rate" "$b_fp" "$avg_fp" "increase"; then
        verdict="alert"
    fi
    if ! check_degradation "finding_density" "$b_fd" "$avg_fd" "decrease"; then
        verdict="alert"
    fi

    # Store verdict
    local verdict_reason
    if [[ "$verdict" == "passed" ]]; then
        verdict_reason="All metrics within threshold (${alert_pct}% tolerance, ${noise_floor} floor)"
    else
        verdict_reason="${reasons}"
    fi

    local escaped_reason
    escaped_reason=$(_interspect_sql_escape "$verdict_reason")
    sqlite3 "$db" "UPDATE canary SET status = '${verdict}', verdict_reason = '${escaped_reason}' WHERE id = ${canary_id};"

    jq -n \
        --argjson canary_id "$canary_id" \
        --arg agent "$agent" \
        --arg status "$verdict" \
        --arg reason "$verdict_reason" \
        --argjson baseline_or "$b_or" \
        --argjson baseline_fp "$b_fp" \
        --argjson baseline_fd "$b_fd" \
        --argjson current_or "$avg_or" \
        --argjson current_fp "$avg_fp" \
        --argjson current_fd "$avg_fd" \
        --argjson sample_count "$sample_count" \
        '{canary_id:$canary_id,agent:$agent,status:$status,reason:$reason,metrics:{baseline:{override_rate:$baseline_or,fp_rate:$baseline_fp,finding_density:$baseline_fd},current:{override_rate:$current_or,fp_rate:$current_fp,finding_density:$current_fd}},sample_count:$sample_count}'
}

# Check all active canaries and evaluate those that have completed their window.
# Returns: JSON array of verdicts for canaries that were evaluated
_interspect_check_canaries() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    local now
    now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Find canaries ready for evaluation: uses_so_far >= window_uses OR time expired
    local ready_ids
    ready_ids=$(sqlite3 "$db" "SELECT id FROM canary WHERE status = 'active' AND (uses_so_far >= window_uses OR window_expires_at <= '${now}');")

    if [[ -z "$ready_ids" ]]; then
        echo "[]"
        return 0
    fi

    local results="["
    local first=1
    local canary_id
    while IFS= read -r canary_id; do
        [[ -z "$canary_id" ]] && continue
        local result
        result=$(_interspect_evaluate_canary "$canary_id")
        if (( first )); then
            first=0
        else
            results+=","
        fi
        results+="$result"
    done <<< "$ready_ids"
    results+="]"

    echo "$results"
}

# Get a summary of all active canaries (for status display).
# Returns: JSON array of canary status objects
_interspect_get_canary_summary() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"

    sqlite3 -json "$db" "
        SELECT c.id, c.group_id as agent, c.status, c.uses_so_far, c.window_uses,
               c.baseline_override_rate, c.baseline_fp_rate, c.baseline_finding_density,
               c.applied_at, c.window_expires_at, c.verdict_reason,
               (SELECT COUNT(*) FROM canary_samples cs WHERE cs.canary_id = c.id) as sample_count,
               (SELECT printf('%.4f', AVG(cs.override_rate)) FROM canary_samples cs WHERE cs.canary_id = c.id) as avg_override_rate,
               (SELECT printf('%.4f', AVG(cs.fp_rate)) FROM canary_samples cs WHERE cs.canary_id = c.id) as avg_fp_rate,
               (SELECT printf('%.4f', AVG(cs.finding_density)) FROM canary_samples cs WHERE cs.canary_id = c.id) as avg_finding_density
        FROM canary c ORDER BY c.applied_at DESC;
    " 2>/dev/null || echo "[]"
}
```

**Step 2: Run syntax check**

```bash
bash -n hub/clavain/hooks/lib-interspect.sh
```

**Step 3: Commit**

```bash
git add hub/clavain/hooks/lib-interspect.sh
git commit -m "feat(interspect): add canary evaluation, degradation detection, and summary"
```

---

## Task 5: Alert Surface (F4)

**Files:**
- Modify: `hub/clavain/hooks/interspect-session.sh` (add alert check)
- Modify: `hub/clavain/commands/interspect-status.md` (enhance canary display)

**Step 1: Update session-start hook with canary alert check**

In `interspect-session.sh`, after the session INSERT (~line 41), before `exit 0`, add:

```bash
# Check for canary alerts — evaluate completed canaries first
_interspect_check_canaries >/dev/null 2>&1 || true

# Check if any canaries are in alert state
ALERT_COUNT=$(sqlite3 "$_INTERSPECT_DB" "SELECT COUNT(*) FROM canary WHERE status = 'alert';" 2>/dev/null || echo "0")

if (( ALERT_COUNT > 0 )); then
    # Get alert details for injection
    ALERT_AGENTS=$(sqlite3 -separator ', ' "$_INTERSPECT_DB" "SELECT group_id FROM canary WHERE status = 'alert';" 2>/dev/null || echo "")
    ALERT_MSG="Canary alert: routing override(s) for ${ALERT_AGENTS} may have degraded review quality. Run /interspect:status for details or /interspect:revert <agent> to undo."

    # Output as additionalContext JSON for session-start injection
    # This piggybacks on the existing hook output mechanism
    echo "{\"additionalContext\":\"WARNING: ${ALERT_MSG}\"}"
fi
```

**Important:** The session-start hook currently outputs nothing. Adding JSON output makes it participate in session context injection. Check that the hooks.json binding for this hook uses the correct event format.

**Step 2: Enhance `/interspect:status` canary section**

Replace the current canary display in `interspect-status.md` (around the "### Canaries" section, ~line 74) with:

```markdown
### Canaries

Query canary summary:

```bash
CANARY_SUMMARY=$(_interspect_get_canary_summary)
CANARY_COUNT=$(echo "$CANARY_SUMMARY" | jq 'length')

# Also check and evaluate any completed canaries
_interspect_check_canaries >/dev/null 2>&1 || true
# Re-query after evaluation
CANARY_SUMMARY=$(_interspect_get_canary_summary)
```

Present canary details:

```
### Canaries: {canary_count} total

{for each canary in CANARY_SUMMARY:
  **{agent}** [{status}]
  - Applied: {applied_at}
  - Window: {uses_so_far}/{window_uses} uses ({days_remaining} days remaining)
  - Baseline: OR={baseline_override_rate}, FP={baseline_fp_rate}, FD={baseline_finding_density}
    {if baseline is NULL: "(insufficient historical data)"}
  - Current:  OR={avg_override_rate}, FP={avg_fp_rate}, FD={avg_finding_density}
    {if sample_count == 0: "(no samples yet)"}
  - Verdict: {verdict_reason}
  - Action: {
    if status == "active": "Monitoring in progress. {uses_so_far}/{window_uses} uses collected."
    if status == "passed": "Override confirmed safe. No action needed."
    if status == "alert": "⚠️ Review quality may have degraded. Run `/interspect:revert {agent}` to undo."
    if status == "expired_unused": "Window expired without usage. Override remains active."
    if status == "reverted": "Override was reverted. Canary closed."
    if status == "monitoring" and baseline is NULL: "Collecting data. Baseline will be established over time."
  }

  {if status == "active" and uses_so_far > 0:
    Progress: [{'█' * (uses_so_far * 20 / window_uses)}{'░' * (20 - uses_so_far * 20 / window_uses)}] {uses_so_far}/{window_uses}
  }
}

{if any canary has status == "alert":
  "⚠️ **Action required:** One or more canary alerts detected. Review the alerts above and consider reverting problematic overrides."
}
```
```

**Step 3: Run syntax checks**

```bash
bash -n hub/clavain/hooks/interspect-session.sh
```

**Step 4: Commit**

```bash
git add hub/clavain/hooks/interspect-session.sh hub/clavain/commands/interspect-status.md
git commit -m "feat(interspect): add canary alerts to session-start + enhance status display"
```

---

## Task 6: Shell Tests

**Files:**
- Modify: `hub/clavain/tests/shell/test_interspect_routing.bats` (add canary tests)

**Step 1: Add canary monitoring tests**

Append to the existing test file:

```bash
# --- Canary baseline tests ---

@test "compute_canary_baseline returns null with no sessions" {
    result=$(_interspect_compute_canary_baseline "2026-02-16T00:00:00Z")
    [ "$result" = "null" ]
}

@test "compute_canary_baseline returns null with insufficient sessions" {
    DB=$(_interspect_db_path)
    # Insert 10 sessions (below min_baseline of 15)
    for i in $(seq 1 10); do
        sqlite3 "$DB" "INSERT INTO sessions (session_id, start_ts, project) VALUES ('s${i}', '2026-01-$(printf '%02d' $i)T00:00:00Z', 'proj1');"
    done
    result=$(_interspect_compute_canary_baseline "2026-02-01T00:00:00Z")
    [ "$result" = "null" ]
}

@test "compute_canary_baseline returns metrics with sufficient sessions" {
    DB=$(_interspect_db_path)
    # Insert 20 sessions with some evidence
    for i in $(seq 1 20); do
        sqlite3 "$DB" "INSERT INTO sessions (session_id, start_ts, project) VALUES ('s${i}', '2026-01-$(printf '%02d' $((i % 28 + 1)))T00:00:00Z', 'proj1');"
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s${i}', 1, '2026-01-$(printf '%02d' $((i % 28 + 1)))T00:00:00Z', 'fd-test', 'override', 'agent_wrong', '{}', 'proj1');"
    done

    result=$(_interspect_compute_canary_baseline "2026-02-01T00:00:00Z")
    [ "$result" != "null" ]

    # Check structure
    echo "$result" | jq -e '.override_rate' >/dev/null
    echo "$result" | jq -e '.fp_rate' >/dev/null
    echo "$result" | jq -e '.finding_density' >/dev/null
    echo "$result" | jq -e '.session_count' >/dev/null
}

# --- Canary sample collection tests ---

@test "record_canary_sample skips sessions with no evidence" {
    DB=$(_interspect_db_path)
    # Create a canary but no evidence for session "empty_session"
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 'active');"

    run _interspect_record_canary_sample "empty_session"
    [ "$status" -eq 0 ]

    # No samples should exist
    count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary_samples;")
    [ "$count" -eq 0 ]
}

@test "record_canary_sample inserts sample for active canary" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 'active');"
    sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, context, project) VALUES ('test_session', 1, '2026-01-15', 'fd-test', 'agent_dispatch', '{}', 'proj1');"

    _interspect_record_canary_sample "test_session"

    count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary_samples;")
    [ "$count" -eq 1 ]

    uses=$(sqlite3 "$DB" "SELECT uses_so_far FROM canary WHERE id = 1;")
    [ "$uses" -eq 1 ]
}

@test "record_canary_sample deduplicates" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 'active');"
    sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, context, project) VALUES ('test_session', 1, '2026-01-15', 'fd-test', 'agent_dispatch', '{}', 'proj1');"

    _interspect_record_canary_sample "test_session"
    _interspect_record_canary_sample "test_session"

    count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary_samples;")
    [ "$count" -eq 1 ]
}

# --- Canary evaluation tests ---

@test "evaluate_canary returns monitoring for active canary with incomplete window" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, uses_so_far, window_expires_at, baseline_override_rate, baseline_fp_rate, baseline_finding_density, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 5, '2026-12-31T00:00:00Z', 0.5, 0.3, 2.0, 'active');"

    result=$(_interspect_evaluate_canary 1)
    status_val=$(echo "$result" | jq -r '.status')
    [ "$status_val" = "monitoring" ]
}

@test "evaluate_canary returns passed when metrics within threshold" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, uses_so_far, window_expires_at, baseline_override_rate, baseline_fp_rate, baseline_finding_density, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 5, 5, '2026-12-31T00:00:00Z', 1.0, 0.5, 3.0, 'active');"

    # Insert 5 samples with similar metrics
    for i in 1 2 3 4 5; do
        sqlite3 "$DB" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (1, 's${i}', '2026-01-${i}', 1.1, 0.55, 2.8);"
    done

    result=$(_interspect_evaluate_canary 1)
    status_val=$(echo "$result" | jq -r '.status')
    [ "$status_val" = "passed" ]

    # Verify DB updated
    db_status=$(sqlite3 "$DB" "SELECT status FROM canary WHERE id = 1;")
    [ "$db_status" = "passed" ]
}

@test "evaluate_canary returns alert when override rate degrades >20%" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, uses_so_far, window_expires_at, baseline_override_rate, baseline_fp_rate, baseline_finding_density, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 5, 5, '2026-12-31T00:00:00Z', 1.0, 0.3, 3.0, 'active');"

    # Insert 5 samples with significantly higher override rate
    for i in 1 2 3 4 5; do
        sqlite3 "$DB" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (1, 's${i}', '2026-01-${i}', 2.0, 0.35, 2.8);"
    done

    result=$(_interspect_evaluate_canary 1)
    status_val=$(echo "$result" | jq -r '.status')
    [ "$status_val" = "alert" ]
}

@test "evaluate_canary ignores differences below noise floor" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, uses_so_far, window_expires_at, baseline_override_rate, baseline_fp_rate, baseline_finding_density, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 5, 5, '2026-12-31T00:00:00Z', 0.05, 0.03, 0.5, 'active');"

    # Small differences (within noise floor of 0.1)
    for i in 1 2 3 4 5; do
        sqlite3 "$DB" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (1, 's${i}', '2026-01-${i}', 0.07, 0.04, 0.48);"
    done

    result=$(_interspect_evaluate_canary 1)
    status_val=$(echo "$result" | jq -r '.status')
    [ "$status_val" = "passed" ]
}

@test "evaluate_canary handles NULL baseline" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, uses_so_far, window_expires_at, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 3, '2026-12-31T00:00:00Z', 'active');"

    result=$(_interspect_evaluate_canary 1)
    status_val=$(echo "$result" | jq -r '.status')
    [ "$status_val" = "monitoring" ]
    reason=$(echo "$result" | jq -r '.reason')
    [[ "$reason" == *"baseline"* ]]
}

@test "check_canaries evaluates completed canaries" {
    DB=$(_interspect_db_path)
    # Canary with full window
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, uses_so_far, window_expires_at, baseline_override_rate, baseline_fp_rate, baseline_finding_density, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 3, 3, '2026-12-31T00:00:00Z', 1.0, 0.5, 3.0, 'active');"

    for i in 1 2 3; do
        sqlite3 "$DB" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (1, 's${i}', '2026-01-${i}', 1.0, 0.5, 3.0);"
    done

    result=$(_interspect_check_canaries)
    count=$(echo "$result" | jq 'length')
    [ "$count" -eq 1 ]
}

# --- canary_samples table tests ---

@test "canary_samples table exists after ensure_db" {
    DB=$(_interspect_db_path)
    result=$(sqlite3 "$DB" ".tables" | grep -c "canary_samples")
    [ "$result" -ge 1 ]
}

@test "canary_samples unique constraint prevents duplicates" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO canary (file, commit_sha, group_id, applied_at, window_uses, status) VALUES ('test', 'abc', 'fd-test', '2026-01-01', 20, 'active');"
    sqlite3 "$DB" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (1, 's1', '2026-01-01', 1.0, 0.5, 3.0);"

    # Second insert should fail due to UNIQUE constraint
    run sqlite3 "$DB" "INSERT INTO canary_samples (canary_id, session_id, ts, override_rate, fp_rate, finding_density) VALUES (1, 's1', '2026-01-01', 2.0, 0.6, 4.0);"
    [ "$status" -ne 0 ]
}
```

**Step 2: Run all tests**

```bash
cd /root/projects/Interverse && bats hub/clavain/tests/shell/test_interspect_routing.bats
```

**Step 3: Commit**

```bash
git add hub/clavain/tests/shell/test_interspect_routing.bats
git commit -m "test(interspect): add canary monitoring tests — baseline, samples, evaluation"
```

---

## Dependency Graph

```
Task 1 (schema + config)
  ├── Task 2 (baseline computation) — depends on Task 1
  │     └── Task 3 (sample collection) — depends on Task 2
  │           └── Task 4 (degradation detection) — depends on Task 3
  │                 └── Task 5 (alert surface) — depends on Task 4
  └── Task 6 (tests) — depends on Tasks 1-4
```

**Parallelizable:** Tasks 5 and 6 are partially independent (5=hooks+commands, 6=tests). But both depend on the core functions in Tasks 1-4 being complete.

**Execution order:** 1 → 2 → 3 → 4 → 5 → 6 (sequential — each builds on the previous)
