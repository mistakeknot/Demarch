# Safety Floors Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire `min_model` from `agent-roles.yaml` into `lib-routing.sh` so safety-critical agents can never be routed below their declared floor model.

**Architecture:** Add a post-resolution clamping step to both `routing_resolve_model()` and `routing_resolve_model_complex()` in `lib-routing.sh`. The clamp reads agent-role mappings from `agent-roles.yaml` (parsed at cache load time), compares tier values (haiku=1, sonnet=2, opus=3), and upgrades the resolved model if it falls below the floor. Structured log to stderr on clamp.

**Tech Stack:** Bash (lib-routing.sh), YAML (agent-roles.yaml), bats (tests)

**Prior Learnings:**
- `docs/solutions/patterns/set-e-arithmetic-and-accumulator-functions-20260222.md` — Use `VAR=$((expr))` not `((...))` for arithmetic under set -e. Affects tier comparison logic.
- `docs/solutions/patterns/guard-fallthrough-null-validation-20260216.md` — Fail closed: if agent-roles.yaml is missing, don't silently skip the floor check.

---

### Task 1: Add agent-roles.yaml Parsing to lib-routing.sh Cache

**Files:**
- Modify: `os/clavain/scripts/lib-routing.sh:19-29` (global cache declarations)
- Modify: `os/clavain/scripts/lib-routing.sh:71-77` (`_routing_load_cache` function)
- Reference: `interverse/interflux/config/flux-drive/agent-roles.yaml`

**Step 1: Write the failing test**

Add to `os/clavain/tests/shell/test_routing.bats`:

```bash
# ═══════════════════════════════════════════════════════════════════
# Safety floor tests
# ═══════════════════════════════════════════════════════════════════

@test "safety floor: agent in role with min_model gets clamped up" {
    # Create agent-roles.yaml alongside routing.yaml
    cat > "$TEST_DIR/config/agent-roles.yaml" << 'YAML'
roles:
  reviewer:
    min_model: sonnet
    agents:
      - fd-safety
      - fd-correctness
  checker:
    agents:
      - fd-perception
YAML
    # Routing config that would resolve fd-safety to haiku via category
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: haiku
YAML
    _source_routing
    result="$(routing_resolve_model --agent fd-safety)"
    [[ "$result" == "sonnet" ]]
}

@test "safety floor: agent without min_model is not clamped" {
    cat > "$TEST_DIR/config/agent-roles.yaml" << 'YAML'
roles:
  checker:
    agents:
      - fd-perception
YAML
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: haiku
YAML
    _source_routing
    result="$(routing_resolve_model --agent fd-perception)"
    [[ "$result" == "haiku" ]]
}

@test "safety floor: agent already at or above floor is not changed" {
    cat > "$TEST_DIR/config/agent-roles.yaml" << 'YAML'
roles:
  reviewer:
    min_model: sonnet
    agents:
      - fd-safety
YAML
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: opus
YAML
    _source_routing
    result="$(routing_resolve_model --agent fd-safety)"
    [[ "$result" == "opus" ]]
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats --filter "safety floor"`
Expected: FAIL — `routing_resolve_model` does not read agent-roles.yaml yet.

**Step 3: Add cache declarations for safety floor data**

In `os/clavain/scripts/lib-routing.sh`, after line 29 (`declare -g _ROUTING_CACHE_POPULATED=""`), add:

```bash
# --- Safety floor cache (from agent-roles.yaml) ---
declare -gA _ROUTING_SF_AGENT_MIN=()        # [agent_name]=min_model (e.g. fd-safety=sonnet)
```

**Step 4: Add agent-roles.yaml discovery to `_routing_find_config`**

After `_routing_find_config()`, add a new function:

```bash
# --- Find agent-roles.yaml (companion to routing.yaml) ---
_routing_find_roles_config() {
  # 0. Explicit env var
  if [[ -n "${CLAVAIN_ROLES_CONFIG:-}" && -f "$CLAVAIN_ROLES_CONFIG" ]]; then
    echo "$CLAVAIN_ROLES_CONFIG"
    return 0
  fi

  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # 1. Interflux plugin config (canonical location)
  local interflux_dirs=(
    "${INTERFLUX_ROOT:-}/config/flux-drive"
    "$script_dir/../../interverse/interflux/config/flux-drive"
    "${CLAUDE_PLUGIN_ROOT:-}/../interflux/config/flux-drive"
  )
  local d
  for d in "${interflux_dirs[@]}"; do
    if [[ -f "$d/agent-roles.yaml" ]]; then
      echo "$d/agent-roles.yaml"
      return 0
    fi
  done

  # 2. Same directory as routing.yaml
  if [[ -n "$_ROUTING_CONFIG_PATH" ]]; then
    local config_dir
    config_dir="$(dirname "$_ROUTING_CONFIG_PATH")"
    if [[ -f "$config_dir/agent-roles.yaml" ]]; then
      echo "$config_dir/agent-roles.yaml"
      return 0
    fi
  fi

  return 1  # Not found — safety floors will be inactive
}
```

**Step 5: Add agent-roles.yaml parsing to `_routing_load_cache`**

At the end of `_routing_load_cache()` (before the final `_ROUTING_CACHE_POPULATED=1`), add:

```bash
  # --- Parse agent-roles.yaml for safety floors ---
  local roles_path
  roles_path="$(_routing_find_roles_config)" || roles_path=""
  if [[ -n "$roles_path" && -f "$roles_path" ]]; then
    local current_role="" current_min="" in_agents=0
    while IFS= read -r line || [[ -n "$line" ]]; do
      # Strip comments and trailing whitespace
      line="${line%%#*}"
      [[ -z "${line// /}" ]] && continue

      # Role name (top level under roles:)
      if [[ "$line" =~ ^[[:space:]]{2}[a-z] && ! "$line" =~ ^[[:space:]]{4} ]]; then
        local role_name="${line%%:*}"
        role_name="${role_name#"${role_name%%[![:space:]]*}"}"  # trim leading
        current_role="$role_name"
        current_min=""
        in_agents=0
        continue
      fi

      # min_model field
      if [[ "$line" =~ ^[[:space:]]+min_model: ]]; then
        current_min="${line#*min_model:}"
        current_min="${current_min#"${current_min%%[![:space:]]*}"}"  # trim leading
        current_min="${current_min%"${current_min##*[![:space:]]}"}"  # trim trailing
        continue
      fi

      # agents: list header
      if [[ "$line" =~ ^[[:space:]]+agents: ]]; then
        in_agents=1
        continue
      fi

      # Agent list item (- agent_name)
      if [[ $in_agents -eq 1 && "$line" =~ ^[[:space:]]+-[[:space:]] ]]; then
        local agent_name="${line#*- }"
        agent_name="${agent_name#"${agent_name%%[![:space:]]*}"}"
        agent_name="${agent_name%"${agent_name##*[![:space:]]}"}"
        if [[ -n "$current_min" && -n "$agent_name" ]]; then
          _ROUTING_SF_AGENT_MIN["$agent_name"]="$current_min"
        fi
        continue
      fi

      # Any other field resets agents context
      if [[ $in_agents -eq 1 && ! "$line" =~ ^[[:space:]]+-[[:space:]] ]]; then
        in_agents=0
      fi
    done < "$roles_path"
  fi
```

**Step 6: Run test to verify parsing works (tests still fail — clamping not added yet)**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats --filter "safety floor"`
Expected: Still FAIL — parsing populates cache but `routing_resolve_model` doesn't clamp yet.

**Step 7: Commit**

```bash
git add os/clavain/scripts/lib-routing.sh os/clavain/tests/shell/test_routing.bats
git commit -m "feat(routing): add agent-roles.yaml parsing for safety floor cache"
```

---

### Task 2: Add Model Tier Comparison and Clamping to routing_resolve_model

**Files:**
- Modify: `os/clavain/scripts/lib-routing.sh:322-394` (`routing_resolve_model` function)
- Modify: `os/clavain/scripts/lib-routing.sh:449-501` (`routing_resolve_model_complex` function)

**Step 1: Add tier comparison helper**

After the safety floor cache declarations, add:

```bash
# --- Model tier ordering for safety floor comparison ---
# Returns numeric tier: haiku=1, sonnet=2, opus=3. Unknown=0.
_routing_model_tier() {
  case "${1:-}" in
    haiku)  echo 1 ;;
    sonnet) echo 2 ;;
    opus)   echo 3 ;;
    *)      echo 0 ;;
  esac
}
```

**Step 2: Add clamping to `routing_resolve_model()`**

In `routing_resolve_model()`, replace the final block (lines 389-393):

```bash
  # Guard: resolve_model MUST never return "inherit"
  [[ "$result" == "inherit" ]] && result="sonnet"

  [[ -n "$result" ]] && echo "$result"
  return 0
```

With:

```bash
  # Guard: resolve_model MUST never return "inherit"
  [[ "$result" == "inherit" ]] && result="sonnet"

  # Safety floor: clamp up to min_model if agent has one
  if [[ -n "$agent" && -n "$result" && -n "${_ROUTING_SF_AGENT_MIN[$agent]:-}" ]]; then
    local floor="${_ROUTING_SF_AGENT_MIN[$agent]}"
    local result_tier floor_tier
    result_tier=$(_routing_model_tier "$result")
    floor_tier=$(_routing_model_tier "$floor")
    if [[ $result_tier -lt $floor_tier ]]; then
      echo "[safety-floor] agent=$agent resolved=$result clamped_to=$floor role=routing_resolve_model" >&2
      result="$floor"
    fi
  fi

  [[ -n "$result" ]] && echo "$result"
  return 0
```

**Step 3: Add clamping to `routing_resolve_model_complex()`**

In `routing_resolve_model_complex()`, replace the enforce mode block (lines 496-500):

```bash
  # Enforce mode: return overridden result
  # Guard: never return "inherit"
  [[ "$final_result" == "inherit" ]] && final_result="$base_result"
  [[ -n "$final_result" ]] && echo "$final_result"
  return 0
```

With:

```bash
  # Enforce mode: return overridden result
  # Guard: never return "inherit"
  [[ "$final_result" == "inherit" ]] && final_result="$base_result"

  # Safety floor: clamp up to min_model (post-complexity resolution)
  if [[ -n "$agent" && -n "$final_result" && -n "${_ROUTING_SF_AGENT_MIN[$agent]:-}" ]]; then
    local floor="${_ROUTING_SF_AGENT_MIN[$agent]}"
    local result_tier floor_tier
    result_tier=$(_routing_model_tier "$final_result")
    floor_tier=$(_routing_model_tier "$floor")
    if [[ $result_tier -lt $floor_tier ]]; then
      echo "[safety-floor] agent=$agent resolved=$final_result clamped_to=$floor role=routing_resolve_model_complex" >&2
      final_result="$floor"
    fi
  fi

  [[ -n "$final_result" ]] && echo "$final_result"
  return 0
```

Also add the same clamping to the **shadow mode** return path (line 492). Replace:

```bash
    [[ -n "$base_result" ]] && echo "$base_result"
    return 0
```

With:

```bash
    # Safety floor applies even in shadow mode — safety is non-negotiable
    local shadow_result="$base_result"
    if [[ -n "$agent" && -n "$shadow_result" && -n "${_ROUTING_SF_AGENT_MIN[$agent]:-}" ]]; then
      local floor="${_ROUTING_SF_AGENT_MIN[$agent]}"
      local result_tier floor_tier
      result_tier=$(_routing_model_tier "$shadow_result")
      floor_tier=$(_routing_model_tier "$floor")
      if [[ $result_tier -lt $floor_tier ]]; then
        echo "[safety-floor] agent=$agent resolved=$shadow_result clamped_to=$floor role=routing_resolve_model_complex(shadow)" >&2
        shadow_result="$floor"
      fi
    fi
    [[ -n "$shadow_result" ]] && echo "$shadow_result"
    return 0
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats --filter "safety floor"`
Expected: All 3 safety floor tests PASS.

**Step 5: Run full routing test suite to check for regressions**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats`
Expected: All existing tests still PASS.

**Step 6: Commit**

```bash
git add os/clavain/scripts/lib-routing.sh
git commit -m "feat(routing): enforce min_model safety floors in resolve_model and resolve_model_complex"
```

---

### Task 3: Expand agent-roles.yaml Coverage

**Files:**
- Modify: `interverse/interflux/config/flux-drive/agent-roles.yaml`

**Step 1: Write test for planner role floor**

Add to `os/clavain/tests/shell/test_routing.bats`:

```bash
@test "safety floor: planner role agents get sonnet floor" {
    cat > "$TEST_DIR/config/agent-roles.yaml" << 'YAML'
roles:
  planner:
    min_model: sonnet
    agents:
      - fd-architecture
      - fd-systems
  checker:
    agents:
      - fd-perception
YAML
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: haiku
YAML
    _source_routing
    result="$(routing_resolve_model --agent fd-architecture)"
    [[ "$result" == "sonnet" ]]
}
```

**Step 2: Run test — should already pass (clamping is generic)**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats --filter "planner role"`
Expected: PASS — the clamping logic is agent-agnostic, driven by agent-roles.yaml data.

**Step 3: Update agent-roles.yaml**

In `interverse/interflux/config/flux-drive/agent-roles.yaml`, update the file:

Replace the comment block and planner role:

```yaml
# model_tier maps to routing.yaml subagent overrides when complexity routing
# is in shadow or enforce mode. Currently informational — consumed by
# experiment scoring, not by lib-routing.sh dispatch.

# Safety rule (from iv-dthn Loop 4): fd-safety and fd-correctness NEVER
# route below Sonnet regardless of role assignment.

roles:
  planner:
    description: Architectural decisions requiring high reasoning capability
    model_tier: opus
    agents:
      - fd-architecture
      - fd-systems
```

With:

```yaml
# model_tier: declared preference for experiment scoring and cost analysis.
# min_model: ENFORCED safety floor — lib-routing.sh clamps resolved model
# to at least this tier. Added iv-db5pc (2026-03-01).
#
# Safety rule (from iv-dthn Loop 4): fd-safety and fd-correctness NEVER
# route below Sonnet regardless of role assignment.

roles:
  planner:
    description: Architectural decisions requiring high reasoning capability
    model_tier: opus
    min_model: sonnet   # safety floor — never downgrade below this
    agents:
      - fd-architecture
      - fd-systems
```

**Step 4: Commit**

```bash
git add interverse/interflux/config/flux-drive/agent-roles.yaml os/clavain/tests/shell/test_routing.bats
git commit -m "feat(agent-roles): add min_model floor to planner role, update comments to reflect enforcement"
```

---

### Task 4: Add Clamping Observability Tests

**Files:**
- Modify: `os/clavain/tests/shell/test_routing.bats`

**Step 1: Write test for stderr logging on clamp**

```bash
@test "safety floor: clamping emits structured log to stderr" {
    cat > "$TEST_DIR/config/agent-roles.yaml" << 'YAML'
roles:
  reviewer:
    min_model: sonnet
    agents:
      - fd-safety
YAML
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: haiku
YAML
    _source_routing
    run bash -c "source '$SCRIPTS_DIR/lib-routing.sh' && export CLAVAIN_ROUTING_CONFIG='$TEST_DIR/config/routing.yaml' && unset _ROUTING_LOADED && source '$SCRIPTS_DIR/lib-routing.sh' && routing_resolve_model --agent fd-safety 2>&1 1>/dev/null"
    [[ "$output" == *"[safety-floor]"* ]]
    [[ "$output" == *"agent=fd-safety"* ]]
    [[ "$output" == *"resolved=haiku"* ]]
    [[ "$output" == *"clamped_to=sonnet"* ]]
}

@test "safety floor: no log when not clamping" {
    cat > "$TEST_DIR/config/agent-roles.yaml" << 'YAML'
roles:
  reviewer:
    min_model: sonnet
    agents:
      - fd-safety
YAML
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: opus
YAML
    _source_routing
    run bash -c "source '$SCRIPTS_DIR/lib-routing.sh' && export CLAVAIN_ROUTING_CONFIG='$TEST_DIR/config/routing.yaml' && unset _ROUTING_LOADED && source '$SCRIPTS_DIR/lib-routing.sh' && routing_resolve_model --agent fd-safety 2>&1 1>/dev/null"
    [[ -z "$output" ]]
}

@test "safety floor: no roles file means no clamping (graceful)" {
    # Don't create agent-roles.yaml
    cat > "$TEST_DIR/config/routing.yaml" << 'YAML'
subagents:
  defaults:
    model: haiku
YAML
    _source_routing
    result="$(routing_resolve_model --agent fd-safety)"
    [[ "$result" == "haiku" ]]
}
```

**Step 2: Run all safety floor tests**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats --filter "safety floor"`
Expected: All 7 safety floor tests PASS.

**Step 3: Run full test suite**

Run: `cd /home/mk/projects/Demarch/os/clavain && bats tests/shell/test_routing.bats`
Expected: All tests PASS (existing + new).

**Step 4: Commit**

```bash
git add os/clavain/tests/shell/test_routing.bats
git commit -m "test(routing): add safety floor observability and edge case tests"
```
