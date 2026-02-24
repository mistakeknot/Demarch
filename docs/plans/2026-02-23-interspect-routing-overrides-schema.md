# Interspect Routing Overrides Schema + Flux-Drive Reader — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Formalize the routing-overrides.json contract with a JSON Schema, update the writer to populate confidence + canary fields, add schema-aware validation to the reader, and update flux-drive SKILL.md to display scope/canary info.

**Architecture:** The routing-overrides.json file is a cross-repo contract: Clavain writes it (lib-interspect.sh), flux-drive reads it (SKILL.md Step 1.2a.0). We add a formal JSON Schema as the source of truth, extend the writer's jq template with new optional fields, add lightweight jq-based validation to the reader, and update the SKILL.md instructions.

**Tech Stack:** JSON Schema (draft-07), bash/jq (writer + reader), BATS (tests), markdown (SKILL docs)

**Bead:** iv-r6mf

---

### Task 1: Create the JSON Schema file

**Files:**
- Create: `os/clavain/config/routing-overrides.schema.json`

**Step 1: Write the schema**

Create the JSON Schema at `os/clavain/config/routing-overrides.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "routing-overrides.schema.json",
  "title": "Interspect Routing Overrides",
  "description": "Agent exclusion and override configuration for flux-drive triage. Written by Interspect (lib-interspect.sh), read by flux-drive (SKILL.md Step 1.2a.0).",
  "type": "object",
  "required": ["version", "overrides"],
  "additionalProperties": true,
  "properties": {
    "version": {
      "type": "integer",
      "const": 1,
      "description": "Schema version. Readers must reject version > 1."
    },
    "overrides": {
      "type": "array",
      "description": "Agent-level routing overrides. Each entry modifies how flux-drive dispatches one agent.",
      "items": {
        "$ref": "#/definitions/override"
      }
    },
    "overlays": {
      "type": "array",
      "description": "Prompt tuning overlays (placeholder — not yet implemented). Reserved for iv-6liz.",
      "items": {
        "type": "object"
      },
      "default": []
    }
  },
  "definitions": {
    "override": {
      "type": "object",
      "required": ["agent", "action"],
      "additionalProperties": true,
      "properties": {
        "agent": {
          "type": "string",
          "pattern": "^fd-[a-z][a-z0-9-]*$",
          "description": "Agent name to override. Must match fd-<name> format."
        },
        "action": {
          "type": "string",
          "enum": ["exclude"],
          "description": "Override action. Currently only 'exclude' is supported."
        },
        "reason": {
          "type": "string",
          "description": "Human-readable explanation of why this override exists."
        },
        "evidence_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Interspect evidence IDs that motivated this override."
        },
        "created": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 timestamp when override was created."
        },
        "created_by": {
          "type": "string",
          "description": "Who created this override (e.g., 'interspect', 'manual')."
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Evidence strength at creation time (agent_wrong_pct / 100). Snapshot — does not update."
        },
        "scope": {
          "$ref": "#/definitions/scope",
          "description": "Optional scope restriction. When absent, override applies globally."
        },
        "canary": {
          "$ref": "#/definitions/canary_snapshot",
          "description": "Canary monitoring snapshot at creation time. DB is authoritative for live state."
        }
      }
    },
    "scope": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "domains": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Domain names from flux-drive domain detection (e.g., 'claude-code-plugin', 'tui-app'). Override only applies when detected domain matches."
        },
        "file_patterns": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Glob patterns for file paths (e.g., 'interverse/**'). Override only applies when input files match."
        }
      }
    },
    "canary_snapshot": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "status": {
          "type": "string",
          "enum": ["active", "passed", "failed", "expired"],
          "description": "Canary status at creation time."
        },
        "window_uses": {
          "type": "integer",
          "minimum": 1,
          "description": "Number of uses in the canary monitoring window."
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "description": "When the canary monitoring window expires."
        }
      }
    }
  }
}
```

**Step 2: Verify the schema is valid JSON**

Run: `jq '.' os/clavain/config/routing-overrides.schema.json`
Expected: Pretty-printed JSON output, exit 0.

**Step 3: Commit**

```bash
git add os/clavain/config/routing-overrides.schema.json
git commit -m "feat(interspect): add JSON Schema for routing-overrides.json v1"
```

---

### Task 2: Update writer to include confidence + canary snapshot

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh:700-710` (jq template in `_interspect_apply_override_locked`)
- Modify: `os/clavain/hooks/lib-interspect.sh:604-608` (add confidence param to `_interspect_apply_routing_override`)
- Modify: `os/clavain/hooks/lib-interspect.sh:650-654` (pass confidence + canary args through flock call)

**Step 1: Write the failing test**

Add to `os/clavain/tests/shell/test_interspect_routing.bats`:

```bash
@test "apply_routing_override writes confidence field" {
    DB=$(_interspect_db_path)
    # Insert evidence so eligibility check passes
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_correct');"

    run _interspect_apply_routing_override "fd-perception" "test reason" '["ev-1"]' "test"
    [ "$status" -eq 0 ]

    # Check confidence field in written JSON
    local filepath="${TEST_DIR}/.claude/routing-overrides.json"
    confidence=$(jq -r '.overrides[0].confidence' "$filepath")
    [ "$confidence" = "0.8" ]
}

@test "apply_routing_override writes canary snapshot" {
    DB=$(_interspect_db_path)
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_wrong');"
    sqlite3 "$DB" "INSERT INTO evidence (source, event, override_reason) VALUES ('fd-perception', 'override', 'agent_correct');"

    run _interspect_apply_routing_override "fd-perception" "test reason" '["ev-1"]' "test"
    [ "$status" -eq 0 ]

    # Check canary snapshot in written JSON
    local filepath="${TEST_DIR}/.claude/routing-overrides.json"
    canary_status=$(jq -r '.overrides[0].canary.status' "$filepath")
    [ "$canary_status" = "active" ]

    canary_uses=$(jq -r '.overrides[0].canary.window_uses' "$filepath")
    [ "$canary_uses" = "20" ]

    canary_expires=$(jq -r '.overrides[0].canary.expires_at' "$filepath")
    [ "$canary_expires" != "null" ]
}
```

**Step 2: Run tests to verify they fail**

Run: `bats os/clavain/tests/shell/test_interspect_routing.bats --filter "writes confidence|writes canary"`
Expected: FAIL — confidence and canary fields not present in current output.

**Step 3: Modify `_interspect_apply_routing_override` to accept confidence param**

In `os/clavain/hooks/lib-interspect.sh`, at line 604, change the function signature to accept a 5th param. Before the flock call, compute confidence from evidence if not provided:

```bash
_interspect_apply_routing_override() {
    local agent="$1"
    local reason="$2"
    local evidence_ids="${3:-[]}"
    local created_by="${4:-interspect}"

    # --- Pre-flock validation (fast-fail) ---
    # ... (existing validation unchanged) ...

    # --- Compute confidence from evidence ---
    local db="${_INTERSPECT_DB:-$(_interspect_db_path)}"
    _interspect_load_confidence
    local total wrong confidence
    local escaped_agent_q
    escaped_agent_q=$(_interspect_sql_escape "$agent")
    total=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent_q}' AND event = 'override';")
    wrong=$(sqlite3 "$db" "SELECT COUNT(*) FROM evidence WHERE source = '${escaped_agent_q}' AND event = 'override' AND override_reason = 'agent_wrong';")
    if (( total > 0 )); then
        # Use awk for float division — bash only does integer math
        confidence=$(awk "BEGIN {printf \"%.2f\", ${wrong}/${total}}")
    else
        confidence="1.0"
    fi

    # --- Compute canary params for JSON snapshot ---
    local canary_window_uses="${_INTERSPECT_CANARY_WINDOW_USES:-20}"
    local canary_expires_at
    canary_expires_at=$(date -u -d "+${_INTERSPECT_CANARY_WINDOW_DAYS:-14} days" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
        || date -u -v+"${_INTERSPECT_CANARY_WINDOW_DAYS:-14}"d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
    if [[ -z "$canary_expires_at" ]]; then
        canary_expires_at="null"
    fi
```

**Step 4: Pass new params through the flock call**

Update the flock call (line ~652) to pass confidence + canary args:

```bash
    flock_output=$(_interspect_flock_git _interspect_apply_override_locked \
        "$root" "$filepath" "$fullpath" "$agent" "$reason" \
        "$evidence_ids" "$created_by" "$commit_msg_file" "$db" \
        "$confidence" "$canary_window_uses" "$canary_expires_at")
```

**Step 5: Update `_interspect_apply_override_locked` to receive and use new params**

At line 677, add new positional params after `$9`:

```bash
_interspect_apply_override_locked() {
    set -e
    local root="$1" filepath="$2" fullpath="$3" agent="$4"
    local reason="$5" evidence_ids="$6" created_by="$7"
    local commit_msg_file="$8" db="$9"
    shift 9
    local confidence="${1:-1.0}" canary_window_uses="${2:-20}" canary_expires_at="${3:-null}"
```

**Step 6: Update the jq template (line ~703) to include confidence + canary**

Replace the existing jq -n command:

```bash
    # 3. Build new override using jq --arg (no shell interpolation)
    local new_override
    local canary_json
    if [[ "$canary_expires_at" != "null" ]]; then
        canary_json=$(jq -n \
            --arg status "active" \
            --argjson window_uses "$canary_window_uses" \
            --arg expires_at "$canary_expires_at" \
            '{status:$status,window_uses:$window_uses,expires_at:$expires_at}')
    else
        canary_json="null"
    fi

    new_override=$(jq -n \
        --arg agent "$agent" \
        --arg action "exclude" \
        --arg reason "$reason" \
        --argjson evidence_ids "$evidence_ids" \
        --arg created "$created" \
        --arg created_by "$created_by" \
        --argjson confidence "$confidence" \
        --argjson canary "$canary_json" \
        '{agent:$agent,action:$action,reason:$reason,evidence_ids:$evidence_ids,created:$created,created_by:$created_by,confidence:$confidence} + (if $canary != null then {canary:$canary} else {} end)')
```

**Step 7: Run tests to verify they pass**

Run: `bats os/clavain/tests/shell/test_interspect_routing.bats`
Expected: All tests PASS including new confidence and canary tests.

**Step 8: Run bash syntax check**

Run: `bash -n os/clavain/hooks/lib-interspect.sh`
Expected: No output, exit 0.

**Step 9: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh os/clavain/tests/shell/test_interspect_routing.bats
git commit -m "feat(interspect): write confidence + canary snapshot to routing-overrides.json"
```

---

### Task 3: Add schema-aware validation to the reader

**Files:**
- Modify: `os/clavain/hooks/lib-interspect.sh:510-535` (`_interspect_read_routing_overrides`)

**Step 1: Write the failing test**

Add to `os/clavain/tests/shell/test_interspect_routing.bats`:

```bash
@test "read_routing_overrides validates version field" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":2,"overrides":[]}' > "${TEST_DIR}/.claude/routing-overrides.json"

    run _interspect_read_routing_overrides
    [ "$status" -eq 1 ]
    [[ "$output" == *'"version":1'* ]]  # Returns empty structure
    [[ "${lines[0]}" == *"WARN"* ]] || [[ "$output" == *"version"* ]]
}

@test "read_routing_overrides validates overrides is array" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":1,"overrides":"not-array"}' > "${TEST_DIR}/.claude/routing-overrides.json"

    run _interspect_read_routing_overrides
    [ "$status" -eq 1 ]
    [[ "$output" == *'"overrides":[]'* ]]
}

@test "read_routing_overrides validates override entries have agent+action" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":1,"overrides":[{"agent":"fd-test"}]}' > "${TEST_DIR}/.claude/routing-overrides.json"

    run _interspect_read_routing_overrides
    # Should warn about missing action but still return data (non-blocking)
    [ "$status" -eq 0 ]
}

@test "read_routing_overrides ignores unknown fields" {
    mkdir -p "${TEST_DIR}/.claude"
    echo '{"version":1,"overrides":[{"agent":"fd-test","action":"exclude","future_field":"ok"}],"unknown_root":"ok"}' > "${TEST_DIR}/.claude/routing-overrides.json"

    run _interspect_read_routing_overrides
    [ "$status" -eq 0 ]
    # Unknown fields preserved in output
    [[ "$output" == *"future_field"* ]]
}
```

**Step 2: Run tests to verify they fail**

Run: `bats os/clavain/tests/shell/test_interspect_routing.bats --filter "validates version|validates overrides|validates override entries|ignores unknown"`
Expected: FAIL — current reader doesn't check version or array structure.

**Step 3: Add validation to `_interspect_read_routing_overrides`**

Replace the function body (lines 510-535):

```bash
_interspect_read_routing_overrides() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    local filepath="${FLUX_ROUTING_OVERRIDES_PATH:-.claude/routing-overrides.json}"

    # Path traversal protection
    if ! _interspect_validate_overrides_path "$filepath"; then
        echo '{"version":1,"overrides":[]}'
        return 1
    fi

    local fullpath="${root}/${filepath}"

    if [[ ! -f "$fullpath" ]]; then
        echo '{"version":1,"overrides":[]}'
        return 0
    fi

    # Parse JSON
    local content
    if ! content=$(jq '.' "$fullpath" 2>/dev/null); then
        echo "WARN: ${filepath} is malformed JSON" >&2
        echo '{"version":1,"overrides":[]}'
        return 1
    fi

    # Validate version
    local version
    version=$(echo "$content" | jq -r '.version // empty')
    if [[ -z "$version" ]] || (( version > 1 )); then
        echo "WARN: ${filepath} has unsupported version (${version:-missing}), ignoring" >&2
        echo '{"version":1,"overrides":[]}'
        return 1
    fi

    # Validate overrides is array
    if ! echo "$content" | jq -e '.overrides | type == "array"' >/dev/null 2>&1; then
        echo "WARN: ${filepath} .overrides is not an array, ignoring" >&2
        echo '{"version":1,"overrides":[]}'
        return 1
    fi

    # Warn about entries missing required fields (non-blocking)
    local missing_count
    missing_count=$(echo "$content" | jq '[.overrides[] | select(.agent == null or .action == null)] | length')
    if (( missing_count > 0 )); then
        echo "WARN: ${filepath} has ${missing_count} override(s) missing agent or action field" >&2
    fi

    echo "$content"
}
```

**Step 4: Run tests to verify they pass**

Run: `bats os/clavain/tests/shell/test_interspect_routing.bats`
Expected: All tests PASS.

**Step 5: Run bash syntax check**

Run: `bash -n os/clavain/hooks/lib-interspect.sh`
Expected: No output, exit 0.

**Step 6: Commit**

```bash
git add os/clavain/hooks/lib-interspect.sh os/clavain/tests/shell/test_interspect_routing.bats
git commit -m "feat(interspect): add schema-aware validation to routing-overrides reader"
```

---

### Task 4: Update flux-drive SKILL.md with scope + canary display

**Files:**
- Modify: `interverse/interflux/skills/flux-drive/SKILL.md:263-278` (Step 1.2a.0)
- Modify: `interverse/interflux/skills/flux-drive/SKILL-compact.md:63` (Step 1.2a.0 compact)

**Step 1: Update SKILL.md Step 1.2a.0**

Replace lines 263-278 in `interverse/interflux/skills/flux-drive/SKILL.md` with:

```markdown
#### Step 1.2a.0: Apply routing overrides

Before pre-filtering by content, check for project-level routing overrides:

1. **Read file:** Check if `$FLUX_ROUTING_OVERRIDES_PATH` (default: `.claude/routing-overrides.json`) exists in the project root.
2. **If missing:** Continue to Step 1.2a with no exclusions.
3. **If present:**
   a. Parse JSON. If malformed, log `"WARNING: routing-overrides.json malformed, ignoring overrides"` in triage output, move file to `.claude/routing-overrides.json.corrupted`, and continue with no exclusions.
   b. Check `version` field. If `version > 1`, log `"WARNING: Routing overrides version N not supported (max 1). Ignoring file."` and continue with no exclusions.
   c. Read `.overrides[]` array. For each entry with `"action": "exclude"`:
      - **Scope check:** If the entry has a `scope` field:
        - If `scope.domains` is set, check if the current document's detected domain (from Step 1.1) matches any domain in the list. If no match, skip this override (agent stays in pool).
        - If `scope.file_patterns` is set, check if any input file path matches any glob pattern. If no match, skip this override.
        - If both are set, BOTH must match (AND logic).
      - If no `scope` field, the override applies globally (all domains, all files).
      - Remove the agent from the candidate pool (they will not appear in pre-filter or scoring).
      - If the agent is not in the roster (unknown name), log: `"WARNING: Routing override for unknown agent {name} — check spelling or remove entry."`
      - If the excluded agent is cross-cutting (fd-architecture, fd-quality, fd-safety, fd-correctness), add a **prominent warning** to triage output: `"Warning: Routing override excludes cross-cutting agent {name}. This removes structural/security coverage."`
4. **Triage table note:** After the scoring table, add: `"N agents excluded by routing overrides: [agent1, agent2, ...]"`
   - For each excluded agent with a `canary` field, append canary status: `"agent1 [canary: active, expires 2026-03-09]"`
   - For each excluded agent with a `confidence` field, append: `"(confidence: 0.85)"`
5. **Discovery nudge:** If the same agent has been overridden 3+ times in the current session (via user declining findings or explicitly overriding), add a note after the triage table: `"Tip: Agent {name} was overridden {N} times this session. Run /interspect:correction to record this pattern. After enough evidence, /interspect can propose permanent exclusions."`
6. **Continue to Step 1.2a** with the reduced candidate pool.
```

**Step 2: Update SKILL-compact.md**

Replace the Step 1.2a.0 line (around line 63) in `interverse/interflux/skills/flux-drive/SKILL-compact.md`:

```markdown
**Step 1.2a.0: Routing Overrides** — Read `.claude/routing-overrides.json` if exists. Exclude any agent with `"action":"exclude"`. If override has `scope` (domains/file_patterns), only exclude when scope matches current input. Warn if excluded agent covers a cross-cutting domain. Show canary status `[canary: <status>, expires <date>]` and confidence `(<value>)` in triage notes when present.
```

**Step 3: Verify no broken markdown**

Visually inspect that the SKILL.md changes don't break the numbered list or surrounding sections.

**Step 4: Commit**

```bash
git add interverse/interflux/skills/flux-drive/SKILL.md interverse/interflux/skills/flux-drive/SKILL-compact.md
git commit -m "feat(flux-drive): update routing override reader for scope + canary display"
```

---

### Task 5: Integration smoke test

**Files:**
- No new files — validates the end-to-end flow.

**Step 1: Create a test routing-overrides.json with all fields**

Write a temporary test file at `.claude/routing-overrides.json`:

```json
{
  "version": 1,
  "overrides": [
    {
      "agent": "fd-perception",
      "action": "exclude",
      "reason": "Test override for smoke test",
      "evidence_ids": ["ev-smoke-1"],
      "created": "2026-02-23T20:00:00Z",
      "created_by": "manual",
      "confidence": 0.9,
      "scope": {
        "domains": ["claude-code-plugin"]
      },
      "canary": {
        "status": "active",
        "window_uses": 20,
        "expires_at": "2026-03-09T20:00:00Z"
      }
    }
  ],
  "overlays": []
}
```

**Step 2: Validate it reads correctly**

Source lib-interspect.sh and run `_interspect_read_routing_overrides`. Verify:
- Returns the full JSON including new fields
- No warnings on stderr
- Confidence and canary fields are present

Run: `bash -c 'source os/clavain/hooks/lib-interspect.sh && _interspect_read_routing_overrides' 2>&1`
Expected: Full JSON output, no WARN messages.

**Step 3: Validate schema file parses**

Run: `jq '.definitions.override.properties | keys' os/clavain/config/routing-overrides.schema.json`
Expected: Array containing agent, action, reason, evidence_ids, created, created_by, confidence, scope, canary.

**Step 4: Clean up test file**

Remove the temporary `.claude/routing-overrides.json` if it was created.

**Step 5: Run full test suite**

Run: `bats os/clavain/tests/shell/test_interspect_routing.bats`
Expected: All tests PASS.

**Step 6: Final commit (if any cleanup needed)**

```bash
git add -A && git commit -m "test(interspect): add integration smoke test for routing-overrides schema"
```
