# Interspect F2: Pattern Detection + Propose Flow — Implementation Plan
**Phase:** executing (as of 2026-02-24T02:24:19Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Implement library functions for routing-eligible pattern detection and the propose writer that creates `"propose"` entries in routing-overrides.json, completing the detection→proposal pipeline for `/interspect:propose`.

**Architecture:** Three new library functions in `lib-interspect.sh` (get_routing_eligible, get_overlay_eligible, apply_propose) that compose existing classified-pattern queries with eligibility filtering and the atomic JSON write pattern. Tests in the existing bats test file.

**Tech Stack:** Bash, SQLite3, jq, bats-core (testing)

**Review Amendments (flux-drive 2026-02-23):**
- Fix 1: `ALREADY_EXISTS` sentinel — use exit code 2 from locked function, handle in outer
- Fix 2: Overlay-eligible `ready` filter — accumulate ALL override rows, track `has_ready` flag
- Fix 3: `agent_wrong` accumulation — use `+=` not `=`
- Fix 4: Overlay band upper bound — use `_INTERSPECT_MIN_AGENT_WRONG_PCT` from config
- Fix 5: Sanitize `$reason` before commit message
- Fix 6: `agent_sessions`/`agent_projects` — use max-over-rows, not last-write-wins
- Fix 7: Cross-cutting agent list — add sourcing comment
- Fix 8: bats `run` captures stdout — emit skip message to stdout

---

### Task 1: Add `_interspect_get_routing_eligible()` helper

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh` (insert after `_interspect_is_routing_eligible`, ~line 490)
- Test: `os/clavain/tests/shell/test_interspect_routing.bats`

**Step 1: Write the failing test**

Add to `test_interspect_routing.bats`:

```bash
# ─── Pattern Detection Helpers ──────────────────────────────────────

@test "get_routing_eligible returns agents meeting all criteria" {
    DB=$(_interspect_db_path)
    # Insert 6 agent_wrong events across 3 sessions and 3 projects for fd-game-design
    for i in 1 2 3 4 5 6; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-game-design', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
    done

    result=$(_interspect_get_routing_eligible)
    echo "result: $result"
    [ -n "$result" ]
    echo "$result" | grep -q "fd-game-design"
}

@test "get_routing_eligible excludes agents below 80% wrong" {
    DB=$(_interspect_db_path)
    # 3 agent_wrong + 3 deprioritized = 50% wrong (below 80%)
    for i in 1 2 3; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-test-agent', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
    done
    for i in 4 5 6; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-test-agent', 'override', 'deprioritized', '{}', 'proj$((i % 3 + 1))');"
    done

    result=$(_interspect_get_routing_eligible)
    echo "result: $result"
    # Should NOT contain fd-test-agent (50% < 80%)
    if [ -n "$result" ]; then
        ! echo "$result" | grep -q "fd-test-agent"
    fi
}

@test "get_routing_eligible excludes already-overridden agents" {
    DB=$(_interspect_db_path)
    # Insert enough evidence to be eligible
    for i in 1 2 3 4 5 6; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-game-design', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
    done
    # Create an existing override
    mkdir -p "$TEST_DIR/.claude"
    cat > "$TEST_DIR/.claude/routing-overrides.json" << 'EOF'
{"version":1,"overrides":[{"agent":"fd-game-design","action":"exclude","reason":"test"}]}
EOF
    git add .claude/routing-overrides.json && git commit -q -m "add override"

    result=$(_interspect_get_routing_eligible)
    echo "result: $result"
    # Should be empty — agent already overridden
    [ -z "$result" ]
}

@test "get_routing_eligible returns empty on no evidence" {
    result=$(_interspect_get_routing_eligible)
    [ -z "$result" ]
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "get_routing_eligible" -t`
Expected: FAIL with "_interspect_get_routing_eligible: command not found"

**Step 3: Write minimal implementation**

Insert after `_interspect_is_routing_eligible()` in `lib-interspect.sh` (~line 490):

```bash
# Get agents eligible for routing override proposals.
# Filters classified patterns for: ready + routing-eligible + not already overridden.
# Output: pipe-delimited rows: agent|event_count|session_count|project_count|agent_wrong_pct
# Note: _interspect_is_routing_eligible handles multi-variant source names
#       (fd-X, interflux:fd-X, interflux:review:fd-X) so pct is always correct.
_interspect_get_routing_eligible() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    [[ -f "$db" ]] || return 0

    _interspect_load_confidence

    # Accumulate per-agent totals across all classified pattern rows.
    # An agent can appear in multiple rows (e.g., separate rows for
    # agent_wrong and deprioritized override_reasons).
    local -A seen_agents
    _interspect_get_classified_patterns | while IFS='|' read -r src evt reason ec sc pc cls; do
        # Only "ready" patterns with override events
        [[ "$cls" == "ready" ]] || continue
        [[ "$evt" == "override" ]] || continue
        [[ "$reason" == "agent_wrong" ]] || continue

        # Dedup: only emit each agent once (first ready+agent_wrong row wins)
        [[ -z "${seen_agents[$src]+x}" ]] || continue
        seen_agents[$src]=1

        # Must be a valid fd-* agent
        _interspect_validate_agent_name "$src" 2>/dev/null || continue

        # Check routing eligibility (blacklist + >=80% wrong via multi-variant query)
        local eligible_result
        eligible_result=$(_interspect_is_routing_eligible "$src")
        [[ "$eligible_result" == "eligible" ]] || continue

        # Skip if already overridden (exclude or propose)
        if _interspect_override_exists "$src"; then
            continue
        fi

        # Get pct from _interspect_is_routing_eligible's own multi-variant query
        # (it already computed this; re-extract it from the DB for the output row)
        local escaped
        escaped=$(_interspect_sql_escape "$src")
        local total wrong pct
        total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped}' OR source = 'interflux:${escaped}' OR source = 'interflux:review:${escaped}') AND event = 'override';")
        wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE (source = '${escaped}' OR source = 'interflux:${escaped}' OR source = 'interflux:review:${escaped}') AND event = 'override' AND override_reason = 'agent_wrong';")
        pct=$(( total > 0 ? wrong * 100 / total : 0 ))

        echo "${src}|${ec}|${sc}|${pc}|${pct}"
    done
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "get_routing_eligible" -t`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh os/clavain/tests/shell/test_interspect_routing.bats
git commit -m "feat(interspect): add _interspect_get_routing_eligible helper"
```

---

### Task 2: Add `_interspect_get_overlay_eligible()` helper

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh` (insert after `_interspect_get_routing_eligible`)
- Test: `os/clavain/tests/shell/test_interspect_routing.bats`

**Step 1: Write the failing test**

```bash
@test "get_overlay_eligible returns agents in 40-79% wrong band" {
    DB=$(_interspect_db_path)
    # Insert 6 events: 4 agent_wrong + 2 deprioritized = 67% wrong across 3 sessions, 3 projects
    for i in 1 2 3 4; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-overlay-test', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
    done
    for i in 5 6; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-overlay-test', 'override', 'deprioritized', '{}', 'proj$((i % 3 + 1))');"
    done

    result=$(_interspect_get_overlay_eligible)
    echo "result: $result"
    [ -n "$result" ]
    echo "$result" | grep -q "fd-overlay-test"
}

@test "get_overlay_eligible excludes agents at 80%+ (routing territory)" {
    DB=$(_interspect_db_path)
    # Insert 6 agent_wrong events = 100% wrong (should be routing, not overlay)
    for i in 1 2 3 4 5 6; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-too-wrong', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
    done

    result=$(_interspect_get_overlay_eligible)
    echo "result: $result"
    if [ -n "$result" ]; then
        ! echo "$result" | grep -q "fd-too-wrong"
    fi
}

@test "get_overlay_eligible excludes agents below 40%" {
    DB=$(_interspect_db_path)
    # Insert 6 events: 2 agent_wrong + 4 deprioritized = 33% wrong (below 40%)
    for i in 1 2; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-low-wrong', 'override', 'agent_wrong', '{}', 'proj$((i % 3 + 1))');"
    done
    for i in 3 4 5 6; do
        sqlite3 "$DB" "INSERT INTO evidence (session_id, seq, ts, source, event, override_reason, context, project) VALUES ('s$i', $i, '2026-01-0${i}', 'fd-low-wrong', 'override', 'deprioritized', '{}', 'proj$((i % 3 + 1))');"
    done

    result=$(_interspect_get_overlay_eligible)
    echo "result: $result"
    if [ -n "$result" ]; then
        ! echo "$result" | grep -q "fd-low-wrong"
    fi
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "get_overlay_eligible" -t`
Expected: FAIL

**Step 3: Write minimal implementation**

```bash
# Get agents eligible for prompt tuning overlay proposals.
# Filters for: has at least one "ready" row + 40-<routing_threshold>% agent_wrong + not overlaid.
# Accumulates ALL override rows (not just "ready") for correct pct denominator.
# Output: pipe-delimited rows: agent|event_count|session_count|project_count|agent_wrong_pct
_interspect_get_overlay_eligible() {
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    [[ -f "$db" ]] || return 0

    _interspect_load_confidence

    # Accumulate ALL override events per agent (not just "ready"),
    # but track which agents have at least one "ready" row.
    local -A agent_total agent_wrong agent_sessions agent_projects agent_has_ready
    while IFS='|' read -r src evt reason ec sc pc cls; do
        [[ "$evt" == "override" ]] || continue
        _interspect_validate_agent_name "$src" 2>/dev/null || continue

        # Accumulate totals using += (not assignment)
        agent_total[$src]=$(( ${agent_total[$src]:-0} + ec ))
        if [[ "$reason" == "agent_wrong" ]]; then
            agent_wrong[$src]=$(( ${agent_wrong[$src]:-0} + ec ))
        fi
        # Track max sessions/projects across rows (not last-write-wins)
        if (( sc > ${agent_sessions[$src]:-0} )); then
            agent_sessions[$src]=$sc
        fi
        if (( pc > ${agent_projects[$src]:-0} )); then
            agent_projects[$src]=$pc
        fi
        # Track if any row for this agent is "ready"
        if [[ "$cls" == "ready" ]]; then
            agent_has_ready[$src]=1
        fi
    done < <(_interspect_get_classified_patterns)

    local src
    for src in "${!agent_total[@]}"; do
        # Must have at least one "ready"-classified row
        [[ "${agent_has_ready[$src]:-}" == "1" ]] || continue

        local total=${agent_total[$src]}
        local wrong=${agent_wrong[$src]:-0}
        (( total > 0 )) || continue

        local pct=$(( wrong * 100 / total ))

        # Overlay band: 40% to below routing threshold (config-driven, not hard-coded 80)
        (( pct >= 40 && pct < _INTERSPECT_MIN_AGENT_WRONG_PCT )) || continue

        # Skip if already has routing override
        if _interspect_override_exists "$src"; then
            continue
        fi

        echo "${src}|${agent_total[$src]}|${agent_sessions[$src]}|${agent_projects[$src]}|${pct}"
    done
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "get_overlay_eligible" -t`
Expected: 3 PASS

**Step 5: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh os/clavain/tests/shell/test_interspect_routing.bats
git commit -m "feat(interspect): add _interspect_get_overlay_eligible helper"
```

---

### Task 3: Add `_interspect_apply_propose()` function

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh` (insert after `_interspect_apply_routing_override` and its locked function, before `_interspect_revert_routing_override`)
- Test: `os/clavain/tests/shell/test_interspect_routing.bats`

**Step 1: Write the failing test**

```bash
# ─── Propose Writer ─────────────────────────────────────────────────

@test "apply_propose writes propose action to routing-overrides.json" {
    _interspect_apply_propose "fd-game-design" "Agent produces irrelevant findings" '["ev1","ev2"]' "interspect"

    local root
    root=$(git rev-parse --show-toplevel)
    local overrides
    overrides=$(cat "$root/.claude/routing-overrides.json")

    # Verify action is "propose" not "exclude"
    local action
    action=$(echo "$overrides" | jq -r '.overrides[0].action')
    [ "$action" = "propose" ]

    # Verify agent name
    local agent
    agent=$(echo "$overrides" | jq -r '.overrides[0].agent')
    [ "$agent" = "fd-game-design" ]

    # Verify it was committed
    local log
    log=$(git log --oneline -1)
    echo "$log" | grep -q "Propose excluding fd-game-design"
}

@test "apply_propose skips if override already exists" {
    # Create an existing exclude override
    mkdir -p "$TEST_DIR/.claude"
    cat > "$TEST_DIR/.claude/routing-overrides.json" << 'EOF'
{"version":1,"overrides":[{"agent":"fd-game-design","action":"exclude","reason":"test"}]}
EOF
    git add .claude/routing-overrides.json && git commit -q -m "add override"

    run _interspect_apply_propose "fd-game-design" "test" '[]' "interspect"
    echo "output: $output"
    # Exit 0 (skip is not an error) and stdout says "already exists"
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "already exists"
}

@test "apply_propose skips if propose already exists" {
    # Create an existing propose override
    mkdir -p "$TEST_DIR/.claude"
    cat > "$TEST_DIR/.claude/routing-overrides.json" << 'EOF'
{"version":1,"overrides":[{"agent":"fd-game-design","action":"propose","reason":"test"}]}
EOF
    git add .claude/routing-overrides.json && git commit -q -m "add propose"

    run _interspect_apply_propose "fd-game-design" "test" '[]' "interspect"
    echo "output: $output"
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "already exists"
}

@test "apply_propose does not create canary record" {
    DB=$(_interspect_db_path)
    _interspect_apply_propose "fd-test-propose" "test reason" '[]' "interspect"

    local canary_count
    canary_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM canary WHERE group_id = 'fd-test-propose';")
    [ "$canary_count" -eq 0 ]
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "apply_propose" -t`
Expected: FAIL with "_interspect_apply_propose: command not found"

**Step 3: Write minimal implementation**

```bash
# ─── Propose Routing Override ────────────────────────────────────────────────

# Write a "propose" entry to routing-overrides.json.
# Proposals are informational — flux-drive shows them in triage but does NOT exclude.
# No canary monitoring or modification record (lighter than apply_routing_override).
# Args: $1=agent_name $2=reason $3=evidence_ids_json $4=created_by
# Returns: 0 on success, 1 on failure
_interspect_apply_propose() {
    local agent="$1"
    local reason="$2"
    local evidence_ids="${3:-[]}"
    local created_by="${4:-interspect}"

    # Pre-flock validation
    if ! _interspect_validate_agent_name "$agent"; then
        return 1
    fi
    if ! printf '%s\n' "$evidence_ids" | jq -e 'type == "array"' >/dev/null 2>&1; then
        echo "ERROR: evidence_ids must be a JSON array (got: ${evidence_ids})" >&2
        return 1
    fi

    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    local filepath="${FLUX_ROUTING_OVERRIDES_PATH:-.claude/routing-overrides.json}"

    if ! _interspect_validate_overrides_path "$filepath"; then
        return 1
    fi

    local fullpath="${root}/${filepath}"

    if ! _interspect_validate_target "$filepath"; then
        echo "ERROR: ${filepath} is not an allowed modification target" >&2
        return 1
    fi

    # Sanitize reason to prevent credential leakage and control chars in commit message
    local sanitized_reason
    sanitized_reason=$(_interspect_sanitize "$reason" 500)

    local commit_msg_file
    commit_msg_file=$(mktemp)
    printf '[interspect] Propose excluding %s from flux-drive triage\n\nReason: %s\nEvidence: %s\nCreated-by: %s\n' \
        "$agent" "$sanitized_reason" "$evidence_ids" "$created_by" > "$commit_msg_file"

    local flock_output
    flock_output=$(_interspect_flock_git _interspect_apply_propose_locked \
        "$root" "$filepath" "$fullpath" "$agent" "$sanitized_reason" \
        "$evidence_ids" "$created_by" "$commit_msg_file")

    local exit_code=$?
    rm -f "$commit_msg_file"

    # Exit code 2 = dedup skip (already exists), not an error
    if (( exit_code == 2 )); then
        echo "INFO: Override for ${agent} already exists. Skipping."
        return 0
    fi

    if (( exit_code != 0 )); then
        echo "ERROR: Could not write proposal. Check git status and retry." >&2
        echo "$flock_output" >&2
        return 1
    fi

    local commit_sha
    commit_sha=$(echo "$flock_output" | tail -1)

    echo "SUCCESS: Proposed excluding ${agent}. Commit: ${commit_sha}"
    echo "Visible in /interspect:status and flux-drive triage notes."
    echo "To apply: /interspect:approve ${agent} (or re-run /interspect:propose)"
    return 0
}

# Inner function called under flock. Do NOT call directly.
_interspect_apply_propose_locked() {
    set -e
    local root="$1" filepath="$2" fullpath="$3" agent="$4"
    local reason="$5" evidence_ids="$6" created_by="$7"
    local commit_msg_file="$8"

    local created
    created=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # 1. Read current file
    local current
    if [[ -f "$fullpath" ]]; then
        current=$(jq '.' "$fullpath" 2>/dev/null || echo '{"version":1,"overrides":[]}')
    else
        current='{"version":1,"overrides":[]}'
    fi

    # 2. Dedup check (inside lock — TOCTOU-safe)
    #    Exit code 2 = skip (already exists). Caller handles this distinctly from error (1).
    if echo "$current" | jq -e --arg agent "$agent" '.overrides[] | select(.agent == $agent)' >/dev/null 2>&1; then
        return 2
    fi

    # 3. Build new propose entry (no confidence or canary — proposals are informational)
    local new_override
    new_override=$(jq -n \
        --arg agent "$agent" \
        --arg action "propose" \
        --arg reason "$reason" \
        --argjson evidence_ids "$evidence_ids" \
        --arg created "$created" \
        --arg created_by "$created_by" \
        '{agent:$agent,action:$action,reason:$reason,evidence_ids:$evidence_ids,created:$created,created_by:$created_by}')

    # 4. Merge
    local merged
    merged=$(echo "$current" | jq --argjson override "$new_override" \
        '.overrides = (.overrides + [$override])')

    # 5. Atomic write
    mkdir -p "$(dirname "$fullpath")" 2>/dev/null || true
    local tmpfile="${fullpath}.tmp.$$"
    echo "$merged" | jq '.' > "$tmpfile"

    if ! jq -e '.' "$tmpfile" >/dev/null 2>&1; then
        rm -f "$tmpfile"
        echo "ERROR: Write produced invalid JSON, aborted" >&2
        return 1
    fi
    mv "$tmpfile" "$fullpath"

    # 6. Git add + commit (use git -C to avoid cd side-effect under set -e)
    git -C "$root" add "$filepath"
    if ! git -C "$root" commit --no-verify -F "$commit_msg_file"; then
        git -C "$root" reset HEAD -- "$filepath" 2>/dev/null || true
        git -C "$root" restore "$filepath" 2>/dev/null || git -C "$root" checkout -- "$filepath" 2>/dev/null || true
        echo "ERROR: Git commit failed. Proposal not applied." >&2
        return 1
    fi

    # No canary or modification records for proposals

    # 7. Output commit SHA
    git -C "$root" rev-parse HEAD
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "apply_propose" -t`
Expected: 4 PASS

**Step 5: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh os/clavain/tests/shell/test_interspect_routing.bats
git commit -m "feat(interspect): add _interspect_apply_propose for propose-action entries"
```

---

### Task 4: Add cross-cutting agent detection helper

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh`
- Test: `os/clavain/tests/shell/test_interspect_routing.bats`

**Step 1: Write the failing test**

```bash
@test "is_cross_cutting identifies architecture agent" {
    run _interspect_is_cross_cutting "fd-architecture"
    [ "$status" -eq 0 ]
}

@test "is_cross_cutting identifies safety agent" {
    run _interspect_is_cross_cutting "fd-safety"
    [ "$status" -eq 0 ]
}

@test "is_cross_cutting identifies quality agent" {
    run _interspect_is_cross_cutting "fd-quality"
    [ "$status" -eq 0 ]
}

@test "is_cross_cutting identifies correctness agent" {
    run _interspect_is_cross_cutting "fd-correctness"
    [ "$status" -eq 0 ]
}

@test "is_cross_cutting rejects non-cross-cutting agent" {
    run _interspect_is_cross_cutting "fd-game-design"
    [ "$status" -eq 1 ]
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "is_cross_cutting" -t`
Expected: FAIL

**Step 3: Write minimal implementation**

```bash
# Check if an agent is cross-cutting (structural coverage agents).
# Cross-cutting agents get extra safety gates in the propose flow —
# they provide foundational review coverage that should not be silently excluded.
# This list is intentionally static and NOT derived from the agent registry or DB.
# Source of truth: Demarch CLAUDE.md "7 core review agents" — these 4 are the
# structural subset (architecture, quality, safety, correctness) vs domain-specific
# (user-product, performance, game-design).
# When adding or reclassifying agents, update this list AND the /interspect:propose
# command spec (os/clavain/commands/interspect-propose.md).
# Args: $1=agent_name
# Returns: 0 if cross-cutting, 1 if not
_interspect_is_cross_cutting() {
    local agent="$1"
    case "$agent" in
        fd-architecture|fd-quality|fd-safety|fd-correctness) return 0 ;;
        *) return 1 ;;
    esac
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats --filter "is_cross_cutting" -t`
Expected: 5 PASS

**Step 5: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh os/clavain/tests/shell/test_interspect_routing.bats
git commit -m "feat(interspect): add _interspect_is_cross_cutting helper"
```

---

### Task 5: Update function index and run full test suite

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh` (header comment section, ~lines 1-25)

**Step 1: Update the function index comment**

The header comment in `lib-interspect.sh` lists available functions. Add the 4 new functions to the index.

**Step 2: Run full test suite**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_interspect_routing.bats -t`
Expected: ALL PASS (existing tests + new tests)

Also run the general routing tests:
Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats -t`
Expected: ALL PASS (no regressions)

**Step 3: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh
git commit -m "docs(interspect): update function index with new detection helpers"
```

---

## Checklist

- [x] Task 1: `_interspect_get_routing_eligible()` + 4 tests
- [x] Task 2: `_interspect_get_overlay_eligible()` + 3 tests
- [x] Task 3: `_interspect_apply_propose()` + locked inner + 4 tests
- [x] Task 4: `_interspect_is_cross_cutting()` + 5 tests
- [x] Task 5: Function index + full test suite green
