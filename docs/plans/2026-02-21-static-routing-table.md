# Plan: Static Routing Table (B1)

**Bead:** iv-1kd4 (sprint), iv-dd9q (original)
**Phase:** planned (as of 2026-02-21T04:15:56Z)
**PRD:** [docs/prds/2026-02-21-static-routing-table.md](../prds/2026-02-21-static-routing-table.md)

## Overview

Implement a unified `config/routing.yaml` with two-section schema (subagents + dispatch), a shell reader library, and integration into dispatch.sh and /model-routing command.

## Task Sequence

### Task 1: Create `config/routing.yaml` (F1)
**Bead:** iv-n4tt
**Phase:** planned (as of 2026-02-21T04:15:56Z)
**Files:** `hub/clavain/config/routing.yaml` (new)

Create the routing config file with the schema from the PRD:
- `subagents:` section with `defaults:` (model + categories), `phases:` (per-phase overrides), `overrides:` (per-agent pinning)
- `dispatch:` section with `tiers:` and `fallback:` (content copied from current `config/dispatch/tiers.yaml`)
- Self-documenting inline comments explaining the resolution order

**Verification:** File parses cleanly with `grep` for expected keys. All current tier values preserved.

---

### Task 2: Write `scripts/lib-routing.sh` (F2)
**Bead:** iv-yo9i
**Phase:** planned (as of 2026-02-21T04:15:56Z)
**Files:** `hub/clavain/scripts/lib-routing.sh` (new)
**Depends on:** Task 1

Implement the shell reader library with these functions:

#### `_routing_find_config()`
Find `routing.yaml` relative to the script directory (same discovery logic as dispatch.sh uses for tiers.yaml):
1. `$script_dir/../config/routing.yaml`
2. `$CLAVAIN_SOURCE_DIR/config/routing.yaml`
3. `find ~/.claude/plugins/cache -path '*/clavain/*/config/routing.yaml'`
Return path or empty string.

#### `_routing_load_cache()`
Parse routing.yaml once into global associative arrays. Guard with `_ROUTING_LOADED` flag so N calls per process don't re-read. Populate:
- `_ROUTING_SA_DEFAULT_MODEL` — `subagents.defaults.model`
- `_ROUTING_SA_DEFAULTS[category]` — `subagents.defaults.categories.*`
- `_ROUTING_SA_PHASE_MODEL[phase]` — `subagents.phases.*.model`
- `_ROUTING_SA_PHASE_CAT[phase:category]` — `subagents.phases.*.categories.*`
- `_ROUTING_SA_OVERRIDE[agent]` — `subagents.overrides.*`
- `_ROUTING_DISPATCH_TIER[tier]` — `dispatch.tiers.*.model`
- `_ROUTING_DISPATCH_DESC[tier]` — `dispatch.tiers.*.description`
- `_ROUTING_DISPATCH_FALLBACK[tier]` — `dispatch.fallback.*`

Parser approach: Line-by-line, track section state with variables (`in_subagents`, `in_dispatch`, `in_defaults`, `in_phases`, `current_phase`, etc.). Max 3 levels of nesting — consistent with dispatch.sh pattern.

#### `routing_resolve_model()`
Named flags: `--phase <phase> [--category <category>] [--agent <agent-name>]`

Resolution order:
1. If `--agent` provided and `_ROUTING_SA_OVERRIDE[agent]` exists → return it
2. If `--phase` + `--category` and `_ROUTING_SA_PHASE_CAT[phase:category]` exists → return it
3. If `--phase` and `_ROUTING_SA_PHASE_MODEL[phase]` exists → return it
4. If `--category` and `_ROUTING_SA_DEFAULTS[category]` exists → return it
5. If `_ROUTING_SA_DEFAULT_MODEL` is set → return it
6. Return empty string (caller uses its own default)

#### `routing_resolve_dispatch_tier()`
Arg: `<tier-name>`. Reads `_ROUTING_DISPATCH_TIER[tier]`. If not found, checks `_ROUTING_DISPATCH_FALLBACK[tier]` and recurses (max 2 hops). Returns model string or empty.

#### `routing_list_mappings()`
Print human-readable routing table for status display:
```
Subagent Routing:
  Default model: sonnet
  Categories: research=haiku, review=sonnet, workflow=sonnet, synthesis=haiku
  Phases:
    brainstorm: model=opus, research=haiku
    strategy: model=opus
    ...
  Overrides: (none)

Dispatch Tiers:
  fast: gpt-5.3-codex-spark
  ...
```

**Verification:** Source lib-routing.sh and test each function:
```bash
source scripts/lib-routing.sh
routing_resolve_model --phase brainstorm --category research  # → haiku
routing_resolve_model --phase brainstorm                       # → opus
routing_resolve_model --phase quality-gates --category review  # → opus
routing_resolve_model --category review                        # → sonnet
routing_resolve_model                                          # → sonnet
routing_resolve_dispatch_tier fast                             # → gpt-5.3-codex-spark
routing_resolve_dispatch_tier fast-clavain                     # → gpt-5.3-codex-spark-xhigh
routing_list_mappings                                          # → full table
```

Also test missing-file case: rename routing.yaml, verify all functions return empty string.

---

### Task 3: Wire dispatch.sh to lib-routing.sh (F3)
**Bead:** iv-re4l
**Phase:** planned (as of 2026-02-21T04:15:56Z)
**Files:** `hub/clavain/scripts/dispatch.sh` (modify)
**Depends on:** Task 2

Changes to dispatch.sh:

1. **Source lib-routing.sh** near the top (after variable declarations):
   ```bash
   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-routing.sh"
   ```

2. **Add `--phase` flag** to the argument parser (between `--tier` and `-i|--image`):
   ```bash
   --phase)
     require_arg "$1" "${2:-}"
     PHASE="$2"
     shift 2
     ;;
   ```
   Initialize `PHASE=""` with other vars at top.

3. **Replace `resolve_tier_model`** function with a call to `routing_resolve_dispatch_tier`:
   - Keep the interserve mode tier remapping logic (`fast` → `fast-clavain` when `CLAVAIN_INTERSERVE_MODE=true`)
   - Change the resolution call from reading tiers.yaml directly to calling `routing_resolve_dispatch_tier "$TIER"`
   - If `routing_resolve_dispatch_tier` returns empty (routing.yaml not found), fall back to the old `resolve_tier_model` logic reading tiers.yaml directly (backward compat during migration)

4. **Store `--phase` for future use** — B2 will use it. For now, just capture and log:
   ```bash
   if [[ -n "$PHASE" ]]; then
     echo "Phase context: $PHASE" >&2
   fi
   ```

5. **Delete tiers.yaml** after confirming dispatch.sh works with routing.yaml.

**Verification:**
```bash
# Test with --tier (should resolve from routing.yaml dispatch section)
bash scripts/dispatch.sh --tier fast --help 2>&1 | grep "Tier 'fast' resolved"

# Test without routing.yaml (should fall back gracefully)
mv config/routing.yaml config/routing.yaml.bak
bash scripts/dispatch.sh --tier fast --help 2>&1
mv config/routing.yaml.bak config/routing.yaml

# Test --phase flag accepted
bash scripts/dispatch.sh --phase brainstorm --tier deep --help 2>&1 | grep "Phase context"
```

---

### Task 4: Update /model-routing command (F4)
**Bead:** iv-pg8t
**Phase:** planned (as of 2026-02-21T04:15:56Z)
**Files:** `hub/clavain/commands/model-routing.md` (modify)
**Depends on:** Task 2

Rewrite the model-routing command to read/write routing.yaml:

#### `status` (or no argument)
- Source `lib-routing.sh` and call `routing_list_mappings`
- Also show current agent frontmatter values (as fallback indicator)
- Display: "Source: routing.yaml" or "Source: agent frontmatter (routing.yaml not found)"

#### `economy`
- If routing.yaml exists: update `subagents.defaults.categories` to `research: haiku, review: sonnet, workflow: sonnet`
- If routing.yaml doesn't exist: fall back to current sed behavior (backward compat)
- Use `sed -i` on routing.yaml to update category values (simple value replacements within known structure)

#### `quality`
- If routing.yaml exists: update `subagents.defaults` to `model: inherit` and all categories to `inherit`
- If routing.yaml doesn't exist: fall back to current sed behavior

The command still edits agent frontmatter as a secondary action (for backward compat when routing.yaml is absent). But when routing.yaml exists, it's the primary source of truth.

**Verification:** Run `/model-routing status` and verify it shows routing.yaml values. Run `/model-routing economy` then `status` — verify categories updated. Run `/model-routing quality` then `status` — verify all set to inherit.

---

### Task 5: Update interserve skill to pass `--phase` (F3 supplement)
**Bead:** iv-re4l (same as Task 3)
**Phase:** planned (as of 2026-02-21T04:15:56Z)
**Files:** `hub/clavain/skills/interserve/SKILL.md` (modify), `hub/clavain/skills/interserve/references/cli-reference.md` (modify)
**Depends on:** Task 3

Update the interserve skill documentation to:
1. Document the new `--phase` flag in cli-reference.md
2. Add guidance in SKILL.md for passing phase context when available:
   ```bash
   CLAVAIN_DISPATCH_PROFILE=interserve bash "$DISPATCH" \
     --prompt-file "$TASK_FILE" \
     --phase "$SPRINT_PHASE" \
     --tier deep
   ```

**Verification:** Read updated docs, confirm `--phase` is documented.

---

## Dependency Graph

```
Task 1 (config/routing.yaml)
  └─→ Task 2 (lib-routing.sh)
        ├─→ Task 3 (dispatch.sh integration)
        │     └─→ Task 5 (interserve docs)
        └─→ Task 4 (model-routing command)
```

## Risk Mitigations

1. **Backward compatibility**: Every consumer falls back to existing behavior when routing.yaml is absent. No breaking changes.
2. **Dispatch.sh is production-critical**: Keep `resolve_tier_model` as fallback during migration. Only delete tiers.yaml after confirming routing.yaml dispatch section works.
3. **Parser complexity**: Schema is designed for max 3 nesting levels, matching the proven dispatch.sh parser pattern.
4. **Testing**: Each task has explicit verification commands. Run them sequentially after each task.

## Estimated Scope

- **Task 1**: ~30 lines of YAML (copy from PRD schema + tiers.yaml content)
- **Task 2**: ~150-200 lines of bash (parser + 4 functions)
- **Task 3**: ~40 lines changed in dispatch.sh (source lib, add flag, replace resolver call)
- **Task 4**: ~50 lines rewritten in model-routing.md
- **Task 5**: ~10 lines added to skill docs
