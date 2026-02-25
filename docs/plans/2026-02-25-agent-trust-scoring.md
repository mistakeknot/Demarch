# Agent Trust and Reputation Scoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Close the feedback loop from flux-drive review findings back into agent triage scoring, so high-precision agents get priority and low-value agents get deprioritized.

**Architecture:** Four-layer pipeline: (1) resolve hook emits evidence events, (2) trust engine computes per-agent per-project scores with global fallback, (3) triage scoring applies trust as a multiplier, (4) observability functions for debugging. All state stored in existing interspect SQLite DB.

**Tech Stack:** Bash (lib-interspect.sh patterns), SQLite, jq, existing interspect evidence schema.

**Bead:** iv-ynbh
**Phase:** planned (as of 2026-02-25T16:33:03Z)

---

### Task 1: Add trust evidence schema migration

**Files:**
- Modify: `interverse/interspect/hooks/lib-interspect.sh` (the `_interspect_ensure_db` function, around line 76-97)

**Step 1: Add migration SQL for trust_feedback table**

The existing `evidence` table could store trust events, but a dedicated table is cleaner for aggregation queries. Add a new table in the migration block inside `_interspect_ensure_db`:

```sql
CREATE TABLE IF NOT EXISTS trust_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    project TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    outcome TEXT NOT NULL,
    review_run_id TEXT,
    weight REAL NOT NULL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_trust_agent_project ON trust_feedback(agent, project);
CREATE INDEX IF NOT EXISTS idx_trust_ts ON trust_feedback(ts);
CREATE INDEX IF NOT EXISTS idx_trust_outcome ON trust_feedback(outcome);
```

Add this in the `_interspect_ensure_db` function's fast-path migration block (after the existing `CREATE TABLE IF NOT EXISTS blacklist` block, around line 78-96). Use the same pattern: `sqlite3 "$_INTERSPECT_DB" <<'MIGRATE' ... MIGRATE`.

**Step 2: Run syntax check**

Run: `bash -n interverse/interspect/hooks/lib-interspect.sh`
Expected: No output (clean syntax)

**Step 3: Commit**

```bash
git add interverse/interspect/hooks/lib-interspect.sh
git commit -m "feat(interspect): add trust_feedback table schema migration"
```

---

### Task 2: Create trust evidence emission functions

**Files:**
- Create: `interverse/interspect/hooks/lib-trust.sh`

**Step 1: Write the trust library**

Create `interverse/interspect/hooks/lib-trust.sh` with the following functions:

```bash
#!/usr/bin/env bash
# lib-trust.sh — Trust scoring engine for agent reputation.
#
# Usage:
#   source hooks/lib-trust.sh
#   _trust_record_outcome "$session_id" "fd-safety" "my-project" "P1-1" "P1" "accepted" "run-123"
#   score=$(_trust_score "fd-safety" "my-project")
#   _trust_report  # table of all scores

[[ -n "${_LIB_TRUST_LOADED:-}" ]] && return 0
_LIB_TRUST_LOADED=1

# Source lib-interspect for DB access
_TRUST_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_TRUST_SCRIPT_DIR}/lib-interspect.sh"

# Severity weights: P0=4x, P1=2x, P2=1x, P3=0.5x
_trust_severity_weight() {
    case "${1:-P2}" in
        P0|p0) echo "4.0" ;;
        P1|p1) echo "2.0" ;;
        P2|p2) echo "1.0" ;;
        P3|p3) echo "0.5" ;;
        *)     echo "1.0" ;;
    esac
}

# Record a finding outcome (accepted or discarded).
# Args: session_id agent project finding_id severity outcome [review_run_id]
# outcome: "accepted" or "discarded"
_trust_record_outcome() {
    local session_id="${1:?session_id required}"
    local agent="${2:?agent required}"
    local project="${3:?project required}"
    local finding_id="${4:?finding_id required}"
    local severity="${5:?severity required}"
    local outcome="${6:?outcome required}"
    local review_run_id="${7:-}"

    _interspect_ensure_db || return 0
    local weight
    weight=$(_trust_severity_weight "$severity")

    # Sanitize inputs
    agent=$(_interspect_sanitize "$agent" 100) || return 0
    project=$(_interspect_sanitize "$project" 200) || return 0
    finding_id=$(_interspect_sanitize "$finding_id" 100) || return 0
    severity=$(_interspect_sanitize "$severity" 10) || return 0
    outcome=$(_interspect_sanitize "$outcome" 20) || return 0

    # Validate outcome
    case "$outcome" in
        accepted|discarded) ;;
        *) return 0 ;;
    esac

    local ts
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    sqlite3 "$_INTERSPECT_DB" "INSERT INTO trust_feedback
        (ts, session_id, agent, project, finding_id, severity, outcome, review_run_id, weight)
        VALUES
        ('$ts', '${session_id//\'/\'\'}', '${agent//\'/\'\'}', '${project//\'/\'\'}',
         '${finding_id//\'/\'\'}', '${severity//\'/\'\'}', '${outcome//\'/\'\'}',
         '${review_run_id//\'/\'\'}', $weight);" 2>/dev/null || true
}

# Compute trust score for an (agent, project) pair.
# Returns float 0.05-1.0 on stdout. Returns 1.0 if no data.
# Uses exponential decay (half-life 30 days) and blends project/global scores.
_trust_score() {
    local agent="${1:?agent required}"
    local project="${2:?project required}"

    _interspect_ensure_db || { echo "1.0"; return 0; }

    # Query: weighted accepted / weighted total, with decay.
    # Decay: weight * 0.5^(days_old / 30)
    # Project-specific score
    local project_result
    project_result=$(sqlite3 "$_INTERSPECT_DB" "
        SELECT
            COALESCE(SUM(CASE WHEN outcome='accepted' THEN weight * (0.5 * (1.0 / (1.0 + (julianday('now') - julianday(ts)) / 30.0))) ELSE 0 END), 0) as accepted_w,
            COALESCE(SUM(weight * (0.5 * (1.0 / (1.0 + (julianday('now') - julianday(ts)) / 30.0)))), 0) as total_w,
            COUNT(*) as review_count
        FROM trust_feedback
        WHERE agent='${agent//\'/\'\'}' AND project='${project//\'/\'\'}';
    " 2>/dev/null) || { echo "1.0"; return 0; }

    local project_accepted project_total project_count
    project_accepted=$(echo "$project_result" | cut -d'|' -f1)
    project_total=$(echo "$project_result" | cut -d'|' -f2)
    project_count=$(echo "$project_result" | cut -d'|' -f3)

    # Global score (all projects for this agent)
    local global_result
    global_result=$(sqlite3 "$_INTERSPECT_DB" "
        SELECT
            COALESCE(SUM(CASE WHEN outcome='accepted' THEN weight * (0.5 * (1.0 / (1.0 + (julianday('now') - julianday(ts)) / 30.0))) ELSE 0 END), 0) as accepted_w,
            COALESCE(SUM(weight * (0.5 * (1.0 / (1.0 + (julianday('now') - julianday(ts)) / 30.0)))), 0) as total_w,
            COUNT(*) as review_count
        FROM trust_feedback
        WHERE agent='${agent//\'/\'\'}';
    " 2>/dev/null) || { echo "1.0"; return 0; }

    local global_accepted global_total global_count
    global_accepted=$(echo "$global_result" | cut -d'|' -f1)
    global_total=$(echo "$global_result" | cut -d'|' -f2)
    global_count=$(echo "$global_result" | cut -d'|' -f3)

    # No data at all → neutral trust
    if [[ "$global_count" -eq 0 ]]; then
        echo "1.0"
        return 0
    fi

    # Compute scores via awk for floating point
    awk -v pa="$project_accepted" -v pt="$project_total" -v pc="$project_count" \
        -v ga="$global_accepted" -v gt="$global_total" -v gc="$global_count" \
        'BEGIN {
        # Global score
        global_score = (gt > 0) ? ga / gt : 1.0

        # Project score
        project_score = (pt > 0) ? pa / pt : global_score

        # Blend weight: min(1.0, project_reviews / 20)
        w = pc / 20.0
        if (w > 1.0) w = 1.0

        # Blended score
        trust = (w * project_score) + ((1.0 - w) * global_score)

        # Floor at 0.05
        if (trust < 0.05) trust = 0.05
        # Cap at 1.0
        if (trust > 1.0) trust = 1.0

        printf "%.2f\n", trust
    }'
}

# Batch-load trust scores for all known agents in a project.
# Output: agent\ttrust_score (one per line). Used by triage to avoid N queries.
_trust_scores_batch() {
    local project="${1:?project required}"

    _interspect_ensure_db || return 0

    # Get all agents with feedback data
    local agents
    agents=$(sqlite3 "$_INTERSPECT_DB" "
        SELECT DISTINCT agent FROM trust_feedback;
    " 2>/dev/null) || return 0

    while IFS= read -r agent; do
        [[ -z "$agent" ]] && continue
        local score
        score=$(_trust_score "$agent" "$project")
        printf "%s\t%s\n" "$agent" "$score"
    done <<< "$agents"
}

# Report trust scores for all agents across all projects.
# Output: formatted table for debugging.
_trust_report() {
    _interspect_ensure_db || { echo "No interspect DB found"; return 0; }

    printf "%-20s %-20s %6s %8s %8s %10s\n" "AGENT" "PROJECT" "TRUST" "ACCEPTED" "DISCARD" "REVIEWS"
    printf "%-20s %-20s %6s %8s %8s %10s\n" "----" "----" "----" "----" "----" "----"

    # Per-project scores
    local rows
    rows=$(sqlite3 "$_INTERSPECT_DB" "
        SELECT agent, project,
            SUM(CASE WHEN outcome='accepted' THEN 1 ELSE 0 END) as accepted,
            SUM(CASE WHEN outcome='discarded' THEN 1 ELSE 0 END) as discarded,
            COUNT(*) as total
        FROM trust_feedback
        GROUP BY agent, project
        ORDER BY agent, project;
    " 2>/dev/null) || return 0

    while IFS='|' read -r agent project accepted discarded total; do
        [[ -z "$agent" ]] && continue
        local score
        score=$(_trust_score "$agent" "$project")
        # Highlight low trust
        local marker=""
        if (( $(echo "$score < 0.30" | bc -l 2>/dev/null || echo 0) )); then
            marker=" <!>"
        fi
        printf "%-20s %-20s %6s %8s %8s %10s%s\n" "$agent" "$project" "$score" "$accepted" "$discarded" "$total" "$marker"
    done <<< "$rows"

    # Global summary
    echo ""
    echo "Global averages:"
    local global_rows
    global_rows=$(sqlite3 "$_INTERSPECT_DB" "
        SELECT agent,
            SUM(CASE WHEN outcome='accepted' THEN 1 ELSE 0 END) as accepted,
            SUM(CASE WHEN outcome='discarded' THEN 1 ELSE 0 END) as discarded,
            COUNT(*) as total
        FROM trust_feedback
        GROUP BY agent
        ORDER BY agent;
    " 2>/dev/null) || return 0

    while IFS='|' read -r agent accepted discarded total; do
        [[ -z "$agent" ]] && continue
        local ratio="N/A"
        if [[ "$total" -gt 0 ]]; then
            ratio=$(awk -v a="$accepted" -v t="$total" 'BEGIN { printf "%.0f%%", (a/t)*100 }')
        fi
        printf "  %-20s %s accepted (%s/%s)\n" "$agent" "$ratio" "$accepted" "$total"
    done <<< "$global_rows"
}
```

**Step 2: Run syntax check**

Run: `bash -n interverse/interspect/hooks/lib-trust.sh`
Expected: No output (clean syntax)

**Step 3: Commit**

```bash
git add interverse/interspect/hooks/lib-trust.sh
git commit -m "feat(interspect): add trust scoring engine — lib-trust.sh"
```

---

### Task 3: Wire evidence emission into resolve workflow

**Files:**
- Modify: `os/clavain/commands/resolve.md` (add evidence emission after step 4)

**Step 1: Add trust feedback emission section**

After the existing "### 4. Commit" section in `resolve.md`, add a new section:

```markdown
### 5. Record Trust Feedback

After resolving findings, emit trust evidence for each finding that was acted on. This feeds the agent trust scoring system.

**Only emit when findings came from flux-drive review** (check: `.clavain/quality-gates/findings.json` exists).

```bash
# Load findings attribution
FINDINGS_JSON=".clavain/quality-gates/findings.json"
if [[ -f "$FINDINGS_JSON" ]]; then
    # Source trust library
    INTERSPECT_PLUGIN=$(find ~/.claude/plugins/cache -path "*/interspect/*/hooks/lib-trust.sh" 2>/dev/null | head -1)
    if [[ -n "$INTERSPECT_PLUGIN" ]]; then
        source "$INTERSPECT_PLUGIN"
        PROJECT=$(_interspect_project_name)
        SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
    fi
fi
```

For each finding resolved in step 3:
- If the finding was **fixed** (code changed to address it): call `_trust_record_outcome "$SESSION_ID" "<agent>" "$PROJECT" "<finding_id>" "<severity>" "accepted" "<review_run_id>"`
- If the finding was **dismissed** (skipped, wont_fix, or deemed irrelevant): call `_trust_record_outcome "$SESSION_ID" "<agent>" "$PROJECT" "<finding_id>" "<severity>" "discarded" "<review_run_id>"`

The `agent` field comes from `findings.json` → `.findings[].agents[0]` (primary attribution). The `review_run_id` comes from `findings.json` → `.synthesis_timestamp`.

**Silent failures:** If lib-trust.sh is not found or any call fails, continue normally. Trust feedback is opportunistic, never blocking.
```

**Step 2: Commit**

```bash
git add os/clavain/commands/resolve.md
git commit -m "feat(clavain): wire trust feedback emission into resolve workflow"
```

---

### Task 4: Wire trust scores into triage scoring

**Files:**
- Modify: `interverse/interflux/skills/flux-drive/phases/launch.md` (Phase 1.2 scoring section)

**Step 1: Add trust multiplier to triage scoring**

In launch.md, find the Phase 1.2 scoring section (after domain_boost, project_bonus, domain_agent_bonus are computed). Add a trust multiplier step:

After the existing scoring computation, before the final sort, add:

```markdown
### Step 1.2e: Apply trust multiplier (interspect feedback)

Load trust scores for all candidate agents in the current project:

```bash
# Source trust library if available
INTERSPECT_PLUGIN=$(find ~/.claude/plugins/cache -path "*/interspect/*/hooks/lib-trust.sh" 2>/dev/null | head -1)
if [[ -n "$INTERSPECT_PLUGIN" ]]; then
    source "$INTERSPECT_PLUGIN"
    PROJECT=$(_interspect_project_name)
    # Batch load: outputs "agent\tscore" lines
    TRUST_SCORES=$(_trust_scores_batch "$PROJECT")
fi
```

For each candidate agent, look up its trust score from `TRUST_SCORES`. If found, multiply the final score:

```
final_score = (base_score + domain_boost + project_bonus + domain_agent_bonus) * trust_multiplier
```

If no trust data exists for an agent: `trust_multiplier = 1.0` (no change).

**Debug output** (when `FLUX_DEBUG=1`):
```
Trust: fd-safety=0.85, fd-correctness=0.92, fd-game-design=0.15, fd-quality=0.78
```

**Fallback:** If lib-trust.sh is not found or `_trust_scores_batch` fails, skip the multiplier entirely (all agents get 1.0). Trust is a progressive enhancement, never a gate.
```

**Step 2: Commit**

```bash
git add interverse/interflux/skills/flux-drive/phases/launch.md
git commit -m "feat(interflux): apply trust multiplier to triage scoring"
```

---

### Task 5: Add trust status command

**Files:**
- Create: `interverse/interspect/commands/trust-status.md`

**Step 1: Write the command**

```markdown
---
name: trust-status
description: Show agent trust scores — precision, review counts, and suppression candidates
argument-hint: "[agent-name]"
---

Display agent trust and reputation scores across projects. Shows which agents are producing useful findings and which are wasting tokens.

## Workflow

### 1. Load Trust Data

```bash
INTERSPECT_PLUGIN=$(find ~/.claude/plugins/cache -path "*/interspect/*/hooks/lib-trust.sh" 2>/dev/null | head -1)
if [[ -z "$INTERSPECT_PLUGIN" ]]; then
    echo "Interspect plugin not found. Trust scoring requires the interspect companion plugin."
    exit 0
fi
source "$INTERSPECT_PLUGIN"
```

### 2. Display Report

If an agent name is provided as argument, show detailed scores for that agent only.
Otherwise, run `_trust_report` to show the full table.

### 3. Highlight Suppression Candidates

After the report, list agents with trust < 0.30 on the current project:

> These agents are candidates for suppression. Their findings are rarely accepted. Consider:
> - Reviewing their domain match for this project type
> - Checking if their prompts need domain-specific tuning
> - Using `/clavain:interspect-propose` to create routing overrides

### 4. Show Recommendations

If any agent has trust > 0.90 with 10+ reviews:
> High-trust agents: These consistently produce actionable findings. Consider prioritizing them in Stage 1 dispatch.
```

**Step 2: Verify command count**

Run: `ls interverse/interspect/commands/*.md | wc -l`
Expected: 13 (was 12, now +1)

**Step 3: Update CLAUDE.md command count**

In `interverse/interspect/CLAUDE.md`, update the command count from 12 to 13:
```
ls commands/*.md | wc -l              # Should be 13
```

**Step 4: Commit**

```bash
git add interverse/interspect/commands/trust-status.md interverse/interspect/CLAUDE.md
git commit -m "feat(interspect): add trust-status command for agent reputation visibility"
```

---

### Task 6: Integration test — end-to-end trust scoring

**Files:**
- Create: `interverse/interspect/tests/test_trust_scoring.sh`

**Step 1: Write the test script**

```bash
#!/usr/bin/env bash
# test_trust_scoring.sh — End-to-end test for trust scoring pipeline.
# Creates a temp DB, records mock outcomes, verifies score computation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/../hooks"

# Create temp directory with git init (required for _interspect_project_name)
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
git init -q
mkdir -p .interspect

# Source libraries
source "$LIB_DIR/lib-interspect.sh"
source "$LIB_DIR/lib-trust.sh"

# Force DB path to temp
_interspect_db_path() { echo "$TMPDIR/.interspect/interspect.db"; }
_interspect_ensure_db

PASS=0
FAIL=0

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "PASS: $label"
        ((PASS++))
    else
        echo "FAIL: $label (expected=$expected actual=$actual)"
        ((FAIL++))
    fi
}

assert_range() {
    local label="$1" min="$2" max="$3" actual="$4"
    if awk -v a="$actual" -v lo="$min" -v hi="$max" 'BEGIN { exit !(a >= lo && a <= hi) }'; then
        echo "PASS: $label ($actual in [$min, $max])"
        ((PASS++))
    else
        echo "FAIL: $label ($actual not in [$min, $max])"
        ((FAIL++))
    fi
}

# Test 1: No data → trust = 1.0
score=$(_trust_score "fd-safety" "test-project")
assert_eq "No data returns 1.0" "1.0" "$score"

# Test 2: All accepted → high trust
for i in $(seq 1 10); do
    _trust_record_outcome "sess-1" "fd-safety" "test-project" "finding-$i" "P1" "accepted" "run-1"
done
score=$(_trust_score "fd-safety" "test-project")
assert_range "All accepted → high trust" "0.80" "1.00" "$score"

# Test 3: All discarded → low trust (but above floor)
for i in $(seq 1 10); do
    _trust_record_outcome "sess-2" "fd-game-design" "test-project" "finding-$i" "P2" "discarded" "run-2"
done
score=$(_trust_score "fd-game-design" "test-project")
assert_range "All discarded → low trust (above 0.05 floor)" "0.05" "0.20" "$score"

# Test 4: Mixed outcomes → intermediate trust
for i in $(seq 1 5); do
    _trust_record_outcome "sess-3" "fd-quality" "test-project" "finding-a$i" "P2" "accepted" "run-3"
done
for i in $(seq 1 5); do
    _trust_record_outcome "sess-3" "fd-quality" "test-project" "finding-d$i" "P2" "discarded" "run-3"
done
score=$(_trust_score "fd-quality" "test-project")
assert_range "50/50 → ~0.50 trust" "0.40" "0.60" "$score"

# Test 5: Severity weighting — P0 accepted counts more than P3 discarded
for i in $(seq 1 3); do
    _trust_record_outcome "sess-4" "fd-correctness" "test-project" "p0-$i" "P0" "accepted" "run-4"
done
for i in $(seq 1 10); do
    _trust_record_outcome "sess-4" "fd-correctness" "test-project" "p3-$i" "P3" "discarded" "run-4"
done
score=$(_trust_score "fd-correctness" "test-project")
assert_range "P0 accepted outweighs P3 discarded" "0.55" "0.85" "$score"

# Test 6: Global fallback for new project
score=$(_trust_score "fd-safety" "new-project")
assert_range "New project inherits global score" "0.80" "1.00" "$score"

# Test 7: Batch loading
batch=$(_trust_scores_batch "test-project")
agents_count=$(echo "$batch" | grep -c '\t' || echo 0)
assert_range "Batch loads multiple agents" "3" "10" "$agents_count"

# Test 8: Report runs without error
output=$(_trust_report 2>&1)
assert_range "Report has content" "5" "999" "$(echo "$output" | wc -l)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
```

**Step 2: Run the test**

Run: `bash interverse/interspect/tests/test_trust_scoring.sh`
Expected: All tests PASS, exit 0

**Step 3: Commit**

```bash
git add interverse/interspect/tests/test_trust_scoring.sh
git commit -m "test(interspect): add end-to-end trust scoring tests"
```

---

### Task 7: Update plugin.json and documentation

**Files:**
- Modify: `interverse/interspect/CLAUDE.md` (command count already updated in Task 5)
- Modify: `interverse/interspect/AGENTS.md` (add trust scoring section if it exists)

**Step 1: Update AGENTS.md**

Add a section documenting the trust scoring system:

```markdown
## Trust Scoring

Agent trust scores are computed from resolve-time feedback. When findings are fixed (accepted) or dismissed (discarded), the outcome is recorded per agent per project.

### Score computation

- Per-project: `accepted_weighted / total_weighted` with severity weights (P0=4x, P1=2x, P2=1x, P3=0.5x)
- Global: same formula across all projects
- Blend: `trust = (w * project) + ((1-w) * global)` where `w = min(1.0, reviews/20)`
- Decay: events lose weight with age (~30-day half-life)
- Floor: 0.05 (never fully exclude an agent)

### Integration

- Triage scoring: `final_score = base_score * trust_multiplier` (launch.md Step 1.2e)
- Observability: `/interspect:trust-status` command
- Data source: `trust_feedback` table in `.interspect/interspect.db`
```

**Step 2: Commit**

```bash
git add interverse/interspect/AGENTS.md
git commit -m "docs(interspect): document trust scoring system"
```
