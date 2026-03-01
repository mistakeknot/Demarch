# Fleet Registry Enrichment + Flux-Drive Integration

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire actual interstat cost data into fleet-registry.yaml and make flux-drive use the registry as a fallback tier between live interstat and hardcoded budget.yaml defaults.

**Architecture:** Three-layer approach: (1) offline enrichment via `scan-fleet.sh --enrich-costs` writes per-agent×model stats from interstat SQLite into fleet-registry.yaml, (2) runtime delta via `fleet_cost_estimate_live()` in lib-fleet.sh overlays fresher interstat data on top of the YAML baseline, (3) estimate-costs.sh gains a fleet-registry fallback tier between its existing interstat-live path and budget.yaml defaults.

**Tech Stack:** Bash (scan-fleet.sh, lib-fleet.sh, estimate-costs.sh), SQLite3 (interstat metrics.db), yq v4 (YAML merge), jq (JSON output), BATS (tests)

**Prior Learnings:**
- `docs/solutions/patterns/token-accounting-billing-vs-context-20260216.md` — Use `total_tokens` (billing) for cost estimation, not effective context tokens. Both fields exist in interstat.
- `docs/measurements/2026-02-28-north-star-baseline.md` — 34+ production runs in interstat; output:input ratio is 15:1; Opus accounts for 95% of cost.
- SQLite has no `PERCENTILE_CONT` — use `ORDER BY + LIMIT 1 OFFSET` approximation for p50/p90.

---

### Task 1: Add enrichment test fixture (interstat mock DB)

**Files:**
- Create: `os/clavain/tests/fixtures/fleet/interstat-mock.sql`

**Step 1: Create the mock SQLite schema + test data**

Write a SQL file that creates the `agent_runs` table (matching interstat's init-db.sh schema) and inserts test rows for several agents with known token counts.

```sql
-- Mock interstat agent_runs for fleet enrichment tests
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    invocation_id TEXT,
    subagent_type TEXT,
    description TEXT,
    wall_clock_ms INTEGER,
    result_length INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_creation_tokens INTEGER,
    total_tokens INTEGER,
    model TEXT,
    parsed_at TEXT,
    bead_id TEXT DEFAULT '',
    phase TEXT DEFAULT ''
);

-- test-reviewer-a: 5 runs on sonnet (sorted total_tokens: 30000, 35000, 38000, 40000, 50000)
-- mean=38600, p50=38000 (index 2), p90=50000 (index 4)
INSERT INTO agent_runs (timestamp, session_id, agent_name, subagent_type, input_tokens, output_tokens, total_tokens, model)
VALUES
  ('2026-02-01T10:00:00Z', 's1', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 10000, 20000, 30000, 'claude-sonnet-4-6'),
  ('2026-02-02T10:00:00Z', 's2', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 12000, 23000, 35000, 'claude-sonnet-4-6'),
  ('2026-02-03T10:00:00Z', 's3', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 13000, 25000, 38000, 'claude-sonnet-4-6'),
  ('2026-02-04T10:00:00Z', 's4', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 15000, 25000, 40000, 'claude-sonnet-4-6'),
  ('2026-02-05T10:00:00Z', 's5', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 20000, 30000, 50000, 'claude-sonnet-4-6');

-- test-reviewer-a: 3 runs on opus
INSERT INTO agent_runs (timestamp, session_id, agent_name, subagent_type, input_tokens, output_tokens, total_tokens, model)
VALUES
  ('2026-02-01T11:00:00Z', 's1', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 20000, 40000, 60000, 'claude-opus-4-6'),
  ('2026-02-02T11:00:00Z', 's2', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 25000, 45000, 70000, 'claude-opus-4-6'),
  ('2026-02-03T11:00:00Z', 's3', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 22000, 48000, 70000, 'claude-opus-4-6');

-- test-reviewer-b: 2 runs on sonnet (< 3, should get preliminary: true)
INSERT INTO agent_runs (timestamp, session_id, agent_name, subagent_type, input_tokens, output_tokens, total_tokens, model)
VALUES
  ('2026-02-01T12:00:00Z', 's1', 'test-reviewer-b', 'test-plugin:review:test-reviewer-b', 8000, 12000, 20000, 'claude-sonnet-4-6'),
  ('2026-02-02T12:00:00Z', 's2', 'test-reviewer-b', 'test-plugin:review:test-reviewer-b', 10000, 15000, 25000, 'claude-sonnet-4-6');

-- test-researcher: 4 runs on haiku
INSERT INTO agent_runs (timestamp, session_id, agent_name, subagent_type, input_tokens, output_tokens, total_tokens, model)
VALUES
  ('2026-02-01T13:00:00Z', 's1', 'test-researcher', 'other-plugin:research:test-researcher', 5000, 5000, 10000, 'claude-haiku-4-5'),
  ('2026-02-02T13:00:00Z', 's2', 'test-researcher', 'other-plugin:research:test-researcher', 6000, 6000, 12000, 'claude-haiku-4-5'),
  ('2026-02-03T13:00:00Z', 's3', 'test-researcher', 'other-plugin:research:test-researcher', 7000, 7000, 14000, 'claude-haiku-4-5'),
  ('2026-02-04T13:00:00Z', 's4', 'test-researcher', 'other-plugin:research:test-researcher', 8000, 8000, 16000, 'claude-haiku-4-5');

-- Post-enrichment run (timestamp after enrichment baseline)
INSERT INTO agent_runs (timestamp, session_id, agent_name, subagent_type, input_tokens, output_tokens, total_tokens, model)
VALUES
  ('2026-03-01T10:00:00Z', 's10', 'test-reviewer-a', 'test-plugin:review:test-reviewer-a', 18000, 27000, 45000, 'claude-sonnet-4-6');
```

**Step 2: Commit**

```bash
git add os/clavain/tests/fixtures/fleet/interstat-mock.sql
git commit -m "test: add interstat mock DB fixture for fleet enrichment tests"
```

---

### Task 2: Add `--enrich-costs` to scan-fleet.sh (F1)

**Files:**
- Modify: `os/clavain/scripts/scan-fleet.sh`

**Step 1: Write failing tests for enrichment**

Add to `os/clavain/tests/shell/test_fleet.bats`:

```bash
# ═══════════════════════════════════════════════════════════════
# scan-fleet.sh --enrich-costs tests
# ═══════════════════════════════════════════════════════════════

# Helper: create mock interstat DB from fixture SQL
_create_mock_interstat() {
    local db_path="$1"
    sqlite3 "$db_path" < "$FIXTURES_DIR/interstat-mock.sql"
}

@test "enrich-costs writes actual_tokens for agents with >= 3 runs" {
    local db="$TEST_DIR/metrics.db"
    _create_mock_interstat "$db"
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$TEST_DIR/registry.yaml"

    run bash "$SCRIPTS_DIR/scan-fleet.sh" --enrich-costs --registry "$TEST_DIR/registry.yaml" --interstat-db "$db" --in-place
    [[ "$status" -eq 0 ]]

    # test-reviewer-a has 5 sonnet runs — should have actual_tokens
    local mean
    mean="$(yq '.agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".mean' "$TEST_DIR/registry.yaml")"
    [[ "$mean" -eq 38600 ]]

    local runs
    runs="$(yq '.agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".runs' "$TEST_DIR/registry.yaml")"
    [[ "$runs" -eq 5 ]]
}

@test "enrich-costs marks agents with < 3 runs as preliminary" {
    local db="$TEST_DIR/metrics.db"
    _create_mock_interstat "$db"
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$TEST_DIR/registry.yaml"

    run bash "$SCRIPTS_DIR/scan-fleet.sh" --enrich-costs --registry "$TEST_DIR/registry.yaml" --interstat-db "$db" --in-place
    [[ "$status" -eq 0 ]]

    # test-reviewer-b has only 2 sonnet runs — should have preliminary: true
    local preliminary
    preliminary="$(yq '.agents.test-reviewer-b.models.actual_tokens."claude-sonnet-4-6".preliminary' "$TEST_DIR/registry.yaml")"
    [[ "$preliminary" == "true" ]]
}

@test "enrich-costs writes last_enrichment timestamp" {
    local db="$TEST_DIR/metrics.db"
    _create_mock_interstat "$db"
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$TEST_DIR/registry.yaml"

    run bash "$SCRIPTS_DIR/scan-fleet.sh" --enrich-costs --registry "$TEST_DIR/registry.yaml" --interstat-db "$db" --in-place
    [[ "$status" -eq 0 ]]

    local ts
    ts="$(yq '.last_enrichment' "$TEST_DIR/registry.yaml")"
    # Should be an ISO timestamp (YYYY-MM-DDTHH:MM:SSZ format)
    [[ "$ts" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T ]]
}

@test "enrich-costs dry-run shows changes without modifying file" {
    local db="$TEST_DIR/metrics.db"
    _create_mock_interstat "$db"
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$TEST_DIR/registry.yaml"
    local before_hash
    before_hash="$(md5sum "$TEST_DIR/registry.yaml" | cut -d' ' -f1)"

    run bash "$SCRIPTS_DIR/scan-fleet.sh" --enrich-costs --registry "$TEST_DIR/registry.yaml" --interstat-db "$db" --dry-run
    [[ "$status" -eq 0 ]]
    [[ "$output" == *"test-reviewer-a"* ]]

    local after_hash
    after_hash="$(md5sum "$TEST_DIR/registry.yaml" | cut -d' ' -f1)"
    [[ "$before_hash" == "$after_hash" ]]
}

@test "enrich-costs handles missing interstat DB gracefully" {
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$TEST_DIR/registry.yaml"

    run bash "$SCRIPTS_DIR/scan-fleet.sh" --enrich-costs --registry "$TEST_DIR/registry.yaml" --interstat-db "/nonexistent/db"
    [[ "$status" -eq 0 ]]
    [[ "$output" == *"not found"* || "$output" == *"Warning"* ]]
}

@test "enrich-costs computes p50 and p90 correctly" {
    local db="$TEST_DIR/metrics.db"
    _create_mock_interstat "$db"
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$TEST_DIR/registry.yaml"

    run bash "$SCRIPTS_DIR/scan-fleet.sh" --enrich-costs --registry "$TEST_DIR/registry.yaml" --interstat-db "$db" --in-place
    [[ "$status" -eq 0 ]]

    # test-reviewer-a sonnet: sorted tokens = [30000, 35000, 38000, 40000, 50000]
    # p50 = index floor(5*0.5) = index 2 → 38000
    # p90 = index floor(5*0.9) = index 4 → 50000
    local p50
    p50="$(yq '.agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".p50' "$TEST_DIR/registry.yaml")"
    [[ "$p50" -eq 38000 ]]

    local p90
    p90="$(yq '.agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".p90' "$TEST_DIR/registry.yaml")"
    [[ "$p90" -eq 50000 ]]
}
```

**Step 2: Run tests to verify they fail**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: New tests FAIL (--enrich-costs not implemented yet)

**Step 3: Implement --enrich-costs in scan-fleet.sh**

Add to `os/clavain/scripts/scan-fleet.sh`:

1. Add new CLI flags in arg parsing (after line 98):
```bash
      --enrich-costs) enrich_costs=true; shift ;;
      --interstat-db) interstat_db="$2"; shift 2 ;;
```

2. Add `enrich_costs=false` and `interstat_db=""` to variable declarations (after line 86).

3. Add the enrichment function before `main()`:

```bash
# --- Enrich with interstat cost data ---
_enrich_costs() {
  local registry="$1"
  local db="$2"
  local dry_run="$3"

  if [[ ! -f "$db" ]]; then
    echo "scan-fleet: interstat DB not found at $db — skipping enrichment" >&2
    return 0
  fi

  if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "scan-fleet: sqlite3 not found — cannot enrich costs" >&2
    return 0
  fi

  # Query all (agent_name, model) pairs with their stats
  local query
  query="
    SELECT
      agent_name,
      model,
      COUNT(*) as run_count,
      CAST(ROUND(AVG(total_tokens)) AS INTEGER) as mean_tokens
    FROM agent_runs
    WHERE total_tokens IS NOT NULL AND model IS NOT NULL
    GROUP BY agent_name, model
    ORDER BY agent_name, model;
  "

  local rows
  rows="$(sqlite3 -separator '|' "$db" "$query" 2>/dev/null)" || {
    echo "scan-fleet: failed to query interstat DB" >&2
    return 0
  }

  if [[ -z "$rows" ]]; then
    echo "scan-fleet: no agent run data in interstat DB"
    return 0
  fi

  if [[ "$dry_run" == true ]]; then
    echo "=== ENRICHMENT DRY RUN ==="
    echo ""
  fi

  while IFS='|' read -r agent_name model run_count mean_tokens; do
    [[ -z "$agent_name" ]] && continue

    # Check if agent exists in registry
    local exists
    exists="$(id="$agent_name" yq '.agents[env(id)] != null' "$registry")"
    [[ "$exists" != "true" ]] && continue

    # Compute p50 and p90 via ORDER BY + OFFSET
    local p50 p90
    p50="$(sqlite3 "$db" "
      SELECT total_tokens FROM agent_runs
      WHERE agent_name='${agent_name}' AND model='${model}' AND total_tokens IS NOT NULL
      ORDER BY total_tokens ASC
      LIMIT 1 OFFSET CAST(${run_count} * 0.5 AS INTEGER)
    " 2>/dev/null)" || p50="$mean_tokens"

    p90="$(sqlite3 "$db" "
      SELECT total_tokens FROM agent_runs
      WHERE agent_name='${agent_name}' AND model='${model}' AND total_tokens IS NOT NULL
      ORDER BY total_tokens ASC
      LIMIT 1 OFFSET CAST(${run_count} * 0.9 AS INTEGER)
    " 2>/dev/null)" || p90="$mean_tokens"

    # Clamp p90 offset: if offset >= count, use last row
    [[ -z "$p90" ]] && p90="$(sqlite3 "$db" "
      SELECT total_tokens FROM agent_runs
      WHERE agent_name='${agent_name}' AND model='${model}' AND total_tokens IS NOT NULL
      ORDER BY total_tokens DESC LIMIT 1
    " 2>/dev/null)"

    local preliminary=false
    [[ "$run_count" -lt 3 ]] && preliminary=true

    if [[ "$dry_run" == true ]]; then
      local flag=""
      [[ "$preliminary" == true ]] && flag=" (preliminary)"
      echo "  ${agent_name} × ${model}: mean=${mean_tokens} p50=${p50} p90=${p90} runs=${run_count}${flag}"
    else
      id="$agent_name" m="$model" mean="$mean_tokens" p50v="$p50" p90v="$p90" runs="$run_count" yq -i '
        .agents[env(id)].models.actual_tokens[env(m)].mean = (env(mean) | tonumber) |
        .agents[env(id)].models.actual_tokens[env(m)].p50 = (env(p50v) | tonumber) |
        .agents[env(id)].models.actual_tokens[env(m)].p90 = (env(p90v) | tonumber) |
        .agents[env(id)].models.actual_tokens[env(m)].runs = (env(runs) | tonumber)
      ' "$registry"

      if [[ "$preliminary" == true ]]; then
        id="$agent_name" m="$model" yq -i '
          .agents[env(id)].models.actual_tokens[env(m)].preliminary = true
        ' "$registry"
      fi
    fi
  done <<< "$rows"

  # Write last_enrichment timestamp
  if [[ "$dry_run" != true ]]; then
    local now
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    ts="$now" yq -i '.last_enrichment = env(ts)' "$registry"
  fi
}
```

4. In `main()`, after arg parsing and before the scan logic, add the enrichment branch:

```bash
  # --- Enrichment mode (separate from scan) ---
  if [[ "$enrich_costs" == true ]]; then
    if [[ -z "$interstat_db" ]]; then
      interstat_db="${HOME}/.claude/interstat/metrics.db"
    fi
    _enrich_costs "$registry_path" "$interstat_db" "$dry_run"
    return $?
  fi
```

**Step 4: Run tests to verify they pass**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add os/clavain/scripts/scan-fleet.sh os/clavain/tests/shell/test_fleet.bats
git commit -m "feat(fleet): add --enrich-costs flag to scan-fleet.sh (F1)

Queries interstat SQLite DB for per-agent×model token stats (mean, p50, p90)
and writes them into fleet-registry.yaml. Handles < 3 runs with preliminary
flag. Writes last_enrichment ISO timestamp."
```

---

### Task 3: Add `fleet_cost_estimate_live` to lib-fleet.sh (F2)

**Files:**
- Modify: `os/clavain/scripts/lib-fleet.sh`

**Step 1: Write failing tests**

Add to `os/clavain/tests/shell/test_fleet.bats`:

```bash
# ═══════════════════════════════════════════════════════════════
# fleet_cost_estimate_live tests (F2)
# ═══════════════════════════════════════════════════════════════

# Helper: create enriched fixture registry
_create_enriched_fixture() {
    local registry="$1"
    cp "$FIXTURES_DIR/fleet-registry.yaml" "$registry"
    # Add last_enrichment and actual_tokens
    yq -i '
      .last_enrichment = "2026-02-15T00:00:00Z" |
      .agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".mean = 38600 |
      .agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".p50 = 38000 |
      .agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".p90 = 50000 |
      .agents.test-reviewer-a.models.actual_tokens."claude-sonnet-4-6".runs = 5
    ' "$registry"
}

@test "fleet_cost_estimate_live returns registry data when no interstat" {
    local registry="$TEST_DIR/registry.yaml"
    _create_enriched_fixture "$registry"
    _source_fleet "$registry"

    run fleet_cost_estimate_live test-reviewer-a claude-sonnet-4-6
    [[ "$status" -eq 0 ]]
    [[ "$output" == "38600" ]]
}

@test "fleet_cost_estimate_live falls back to cold_start_tokens when no actual_tokens" {
    _source_fleet
    run fleet_cost_estimate_live test-researcher claude-haiku-4-5
    [[ "$status" -eq 0 ]]
    [[ "$output" == "300" ]]
}

@test "fleet_cost_estimate_live returns error for unknown agent" {
    _source_fleet
    run fleet_cost_estimate_live nonexistent-agent claude-sonnet-4-6
    [[ "$status" -ne 0 ]]
}

@test "fleet_cost_estimate_live uses interstat delta when DB has newer runs" {
    local registry="$TEST_DIR/registry.yaml"
    _create_enriched_fixture "$registry"
    _source_fleet "$registry"

    # Create mock DB with a post-enrichment run
    local db="$TEST_DIR/metrics.db"
    _create_mock_interstat "$db"

    INTERSTAT_DB="$db" run fleet_cost_estimate_live test-reviewer-a claude-sonnet-4-6
    [[ "$status" -eq 0 ]]
    # Should incorporate the post-enrichment run (45000 token run from 2026-03-01)
    # Combined: original 5 runs + 1 new = 6 runs, recalculated mean
    # (30000+35000+38000+40000+50000+45000)/6 = 39667
    [[ "$output" -gt 38600 ]]
}

@test "fleet_cost_estimate_live defaults to preferred model when model not specified" {
    local registry="$TEST_DIR/registry.yaml"
    _create_enriched_fixture "$registry"
    _source_fleet "$registry"

    run fleet_cost_estimate_live test-reviewer-a
    [[ "$status" -eq 0 ]]
    # test-reviewer-a preferred model is sonnet → should use sonnet actual_tokens
    [[ "$output" == "38600" ]]
}
```

**Step 2: Run tests to verify they fail**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: New tests FAIL

**Step 3: Implement fleet_cost_estimate_live in lib-fleet.sh**

Add to `os/clavain/scripts/lib-fleet.sh`, before the existing `_FLEET_LOADED` guard or at end of public API section:

```bash
# Interstat DB path for runtime delta lookups
_FLEET_INTERSTAT_DB="${INTERSTAT_DB:-${HOME}/.claude/interstat/metrics.db}"

# Live cost estimate: registry actual_tokens + interstat delta overlay
# Returns mean token estimate (integer) for agent+model pair.
# Falls back: actual_tokens → cold_start_tokens → error
fleet_cost_estimate_live() {
  local agent_id="${1:?usage: fleet_cost_estimate_live <agent_id> [model]}"
  local model="${2:-}"
  _fleet_init || return 1
  _fleet_check || return 1

  # Verify agent exists
  local exists
  exists="$(id="$agent_id" yq '.agents[env(id)] != null' "$_FLEET_REGISTRY_PATH")"
  if [[ "$exists" != "true" ]]; then
    echo "lib-fleet: agent '$agent_id' not found" >&2
    return 1
  fi

  # Default to preferred model if not specified
  if [[ -z "$model" ]]; then
    model="$(id="$agent_id" yq '.agents[env(id)].models.preferred // "sonnet"' "$_FLEET_REGISTRY_PATH")"
    # Map short model name to full model ID for DB queries
    case "$model" in
      sonnet) model="claude-sonnet-4-6" ;;
      opus)   model="claude-opus-4-6" ;;
      haiku)  model="claude-haiku-4-5" ;;
    esac
  fi

  # Try interstat delta: check for runs newer than last_enrichment
  if [[ -f "$_FLEET_INTERSTAT_DB" ]] && command -v sqlite3 >/dev/null 2>&1; then
    # Read last_enrichment without yq (grep/sed per PRD requirement)
    local last_enrichment=""
    last_enrichment="$(grep '^last_enrichment:' "$_FLEET_REGISTRY_PATH" 2>/dev/null | sed 's/^last_enrichment: *//' | tr -d '"' | tr -d "'")" || true

    if [[ -n "$last_enrichment" ]]; then
      # Query interstat for runs after last_enrichment
      local delta_result
      delta_result="$(sqlite3 -separator '|' "$_FLEET_INTERSTAT_DB" "
        SELECT CAST(ROUND(AVG(total_tokens)) AS INTEGER), COUNT(*)
        FROM agent_runs
        WHERE agent_name='${agent_id}' AND model='${model}'
          AND total_tokens IS NOT NULL
          AND timestamp > '${last_enrichment}'
      " 2>/dev/null)" || delta_result=""

      if [[ -n "$delta_result" && "$delta_result" != "|0" ]]; then
        local delta_mean delta_count
        delta_mean="${delta_result%%|*}"
        delta_count="${delta_result##*|}"

        if [[ "$delta_count" -gt 0 && -n "$delta_mean" ]]; then
          # Get registry baseline stats
          local reg_mean reg_runs
          reg_mean="$(id="$agent_id" m="$model" yq '.agents[env(id)].models.actual_tokens[env(m)].mean // 0' "$_FLEET_REGISTRY_PATH")" || reg_mean=0
          reg_runs="$(id="$agent_id" m="$model" yq '.agents[env(id)].models.actual_tokens[env(m)].runs // 0' "$_FLEET_REGISTRY_PATH")" || reg_runs=0

          if [[ "$reg_runs" -gt 0 ]]; then
            # Weighted average: combine registry + delta
            local total_runs=$((reg_runs + delta_count))
            local combined=$(( (reg_mean * reg_runs + delta_mean * delta_count) / total_runs ))
            echo "$combined"
            return 0
          else
            echo "$delta_mean"
            return 0
          fi
        fi
      fi
    fi
  fi

  # Fallback: registry actual_tokens (static)
  local actual
  actual="$(id="$agent_id" m="$model" yq '.agents[env(id)].models.actual_tokens[env(m)].mean // ""' "$_FLEET_REGISTRY_PATH")" || actual=""
  if [[ -n "$actual" && "$actual" != "null" && "$actual" != "" ]]; then
    echo "$actual"
    return 0
  fi

  # Fallback: cold_start_tokens
  local cold
  cold="$(id="$agent_id" yq '.agents[env(id)].cold_start_tokens // ""' "$_FLEET_REGISTRY_PATH")" || cold=""
  if [[ -n "$cold" && "$cold" != "null" ]]; then
    echo "$cold"
    return 0
  fi

  echo "lib-fleet: no cost data for '$agent_id' (model=$model)" >&2
  return 1
}
```

**Step 4: Run tests to verify they pass**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add os/clavain/scripts/lib-fleet.sh os/clavain/tests/shell/test_fleet.bats
git commit -m "feat(fleet): add fleet_cost_estimate_live for runtime cost delta (F2)

Checks interstat for runs newer than last_enrichment timestamp and computes
weighted average with registry baseline. Falls back: actual_tokens →
cold_start_tokens → error."
```

---

### Task 4: Wire fleet registry into estimate-costs.sh (F3)

**Files:**
- Modify: `interverse/interflux/scripts/estimate-costs.sh`

**Step 1: Write failing test**

Create `interverse/interflux/tests/test_estimate_costs.bats`:

```bash
#!/usr/bin/env bats
# Tests for estimate-costs.sh fleet registry integration

bats_require_minimum_version 1.5.0

setup() {
    SCRIPT_DIR="$BATS_TEST_DIRNAME/../scripts"
    TEST_DIR="$(mktemp -d)"
    export PATH="$HOME/.local/bin:$PATH"
}

teardown() {
    [[ -d "$TEST_DIR" ]] && rm -rf "$TEST_DIR"
}

@test "estimate-costs falls back to fleet registry when interstat has < 3 runs" {
    # Create a minimal interstat DB with only 1 run for fd-safety
    local db="$TEST_DIR/metrics.db"
    sqlite3 "$db" "
      CREATE TABLE agent_runs (
        id INTEGER PRIMARY KEY, timestamp TEXT, session_id TEXT, agent_name TEXT,
        invocation_id TEXT, subagent_type TEXT, description TEXT, wall_clock_ms INTEGER,
        result_length INTEGER, input_tokens INTEGER, output_tokens INTEGER,
        cache_read_tokens INTEGER, cache_creation_tokens INTEGER, total_tokens INTEGER,
        model TEXT, parsed_at TEXT, bead_id TEXT DEFAULT '', phase TEXT DEFAULT ''
      );
      INSERT INTO agent_runs (timestamp, session_id, agent_name, total_tokens, model)
      VALUES ('2026-03-01T10:00:00Z', 's1', 'fd-safety', 42000, 'claude-sonnet-4-6');
    "

    # Mock fleet registry with actual_tokens for fd-safety
    local registry="$TEST_DIR/fleet-registry.yaml"
    cat > "$registry" << 'YAML'
version: "1.0"
last_enrichment: "2026-02-15T00:00:00Z"
agents:
  fd-safety:
    source: interflux
    category: review
    models:
      preferred: sonnet
      supported: [sonnet, opus]
      actual_tokens:
        claude-sonnet-4-6: {mean: 35000, p50: 33000, p90: 45000, runs: 8}
    cold_start_tokens: 800
YAML

    # Run estimate-costs with overrides
    CLAVAIN_FLEET_REGISTRY="$registry" HOME="$TEST_DIR" \
      run bash "$SCRIPT_DIR/estimate-costs.sh" --model claude-sonnet-4-6
    [[ "$status" -eq 0 ]]

    # fd-safety should have source: fleet-registry (not interstat, not default)
    echo "$output" | jq -e '.estimates["fd-safety"].source == "fleet-registry"'
}

@test "estimate-costs reports source correctly for each tier" {
    # No DB → should use defaults
    HOME="$TEST_DIR" run bash "$SCRIPT_DIR/estimate-costs.sh" --model claude-sonnet-4-6
    [[ "$status" -eq 0 ]]
    # With no DB and no registry, all agents get defaults → JSON should have empty estimates
    local est_count
    est_count="$(echo "$output" | jq '.estimates | length')"
    [[ "$est_count" -eq 0 ]]
}
```

**Step 2: Run test to verify it fails**

Run: `cd interverse/interflux && bats tests/test_estimate_costs.bats`
Expected: FAIL (fleet-registry integration not implemented)

**Step 3: Implement fleet registry fallback in estimate-costs.sh**

Modify `interverse/interflux/scripts/estimate-costs.sh`:

1. After the interstat query block (after line 95), add fleet registry fallback:

```bash
# --- Fleet registry fallback for agents with < 3 interstat runs ---
# Source lib-fleet.sh if available (Clavain companion)
_FLEET_AVAILABLE=false
_find_lib_fleet() {
  # Check common locations
  local candidates=(
    "${CLAVAIN_SOURCE_DIR:-}/scripts/lib-fleet.sh"
    "${CLAUDE_PLUGIN_ROOT:-}/../../os/clavain/scripts/lib-fleet.sh"
  )
  # Plugin cache discovery
  local cache_dir="${HOME}/.claude/plugins/cache"
  if [[ -d "$cache_dir" ]]; then
    local latest
    latest="$(ls -d "$cache_dir"/*/clavain/*/scripts/lib-fleet.sh 2>/dev/null | tail -1)"
    [[ -n "$latest" ]] && candidates+=("$latest")
  fi
  for f in "${candidates[@]}"; do
    if [[ -f "$f" ]]; then
      echo "$f"
      return 0
    fi
  done
  return 1
}

LIB_FLEET="$(_find_lib_fleet 2>/dev/null)" || LIB_FLEET=""
if [[ -n "$LIB_FLEET" ]]; then
  source "$LIB_FLEET" 2>/dev/null && _FLEET_AVAILABLE=true
fi
```

2. Before the final JSON output (before line 103), add the fleet registry lookup for agents not in ESTIMATES:

```bash
# For agents with interstat data but < 3 runs, try fleet registry
# The caller provides agent names via --agents flag; here we just make
# fleet_cost_estimate_live available in our output by adding a lookup function
if [[ "$_FLEET_AVAILABLE" == true ]]; then
  # Query all agents in registry that have actual_tokens
  local fleet_agents
  fleet_agents="$(fleet_list 2>/dev/null)" || fleet_agents=""
  while IFS= read -r fleet_agent; do
    [[ -z "$fleet_agent" ]] && continue
    # Skip if already in interstat estimates (>= 3 runs)
    if echo "$ESTIMATES" | jq -e --arg a "$fleet_agent" '.[$a]' >/dev/null 2>&1; then
      continue
    fi
    # Try fleet registry
    local fleet_est
    fleet_est="$(fleet_cost_estimate_live "$fleet_agent" "$MODEL" 2>/dev/null)" || continue
    if [[ -n "$fleet_est" && "$fleet_est" != "0" ]]; then
      ESTIMATES="$(echo "$ESTIMATES" | jq -c --arg a "$fleet_agent" --argjson t "$fleet_est" \
        '. + {($a): {est_tokens: $t, sample_size: 0, source: "fleet-registry"}}')"
    fi
  done <<< "$fleet_agents"
fi
```

**Step 4: Run tests to verify they pass**

Run: `cd interverse/interflux && bats tests/test_estimate_costs.bats`
Expected: PASS

**Step 5: Run all fleet tests too**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: All PASS

**Step 6: Commit**

```bash
git add interverse/interflux/scripts/estimate-costs.sh interverse/interflux/tests/test_estimate_costs.bats
git commit -m "feat(flux-drive): wire fleet registry as cost estimation fallback (F3)

Resolution order: interstat live (>= 3 runs) → fleet-registry actual_tokens
→ budget.yaml defaults. Reports source in output JSON."
```

---

### Task 5: Update lib-fleet.sh public API header

**Files:**
- Modify: `os/clavain/scripts/lib-fleet.sh:12-22`

**Step 1: Update the public API comment block**

Add `fleet_cost_estimate_live` to the API listing in the header comment:

```bash
#   fleet_cost_estimate_live <agent_id> [model] — live cost estimate (registry + interstat delta)
```

Add after the existing `fleet_cost_estimate` line (line 19).

**Step 2: Commit**

```bash
git add os/clavain/scripts/lib-fleet.sh
git commit -m "docs(fleet): add fleet_cost_estimate_live to lib-fleet.sh API header"
```

---

### Task 6: Run full test suite and verify

**Files:** (no changes — verification only)

**Step 1: Run all fleet tests**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: All tests PASS (original 24 + new enrichment/live tests)

**Step 2: Run estimate-costs tests**

Run: `cd interverse/interflux && bats tests/test_estimate_costs.bats`
Expected: All PASS

**Step 3: Run scan-fleet.sh --enrich-costs manually**

Run: `cd os/clavain && bash scripts/scan-fleet.sh --enrich-costs --dry-run`
Expected: Shows enrichment data from actual interstat DB (or graceful "not found" warning)

**Step 4: Verify existing fleet tests still pass**

Run: `cd os/clavain && bats tests/shell/test_fleet.bats`
Expected: No regressions
