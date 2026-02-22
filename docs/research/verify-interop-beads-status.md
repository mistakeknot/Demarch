# Interop Beads Status Verification

**Date:** 2026-02-21  
**Scope:** Verify implementation status of 4 interop beads against actual codebase

---

## Bead 1: iv-sk8t (F2: Interline statusline enrichment — pressure, coordination, budget)

**Status:** IMPLEMENTED ✓

### Evidence

File: `/root/projects/Interverse/plugins/interline/scripts/statusline.sh`

**Layer 4 - Context Pressure (lines 379-397):**
- Reads pressure signal from `~/.interband/intercheck/pressure/{session_id}.json`
- Extracts `level` field from interband payload
- Color-codes pressure levels: yellow (80%+), orange, red
- Renders as ambient indicator in statusline

**Layer 5 - Budget Alert (lines 399-420):**
- Reads budget signal from `~/.interband/interstat/budget/{session_id}.json`
- Extracts `pct_consumed` field from interband payload
- Renders budget consumption % at thresholds: 50%+ (yellow), 80%+ (red/critical)
- Rendered as: `"${_il_budget_int}% budget"` with color coding
- Displayed as ambient indicator alongside pressure

**Coordination Status (lines 169-235):**
- Reads coordination state from interlock signal files
- Sources: `~/.interband/interlock/coordination/{project}-{agent-id}.json` (interband)
- Fallback: `/var/run/intermute/signals/{project}-{agent-id}.jsonl` (legacy JSONL)
- Displays agent count + optional coordination signal text
- Only active when `INTERMUTE_AGENT_ID` env var is set

**Configuration:** All layers have feature toggles in `~/.claude/interline.json`:
- `layers.pressure` (default true)
- `layers.budget` (default true)
- `layers.coordination` (default true)

### Conclusion
Fully implemented. Both pressure and budget layers read interband signals and render in statusline with color-coded thresholds.

---

## Bead 2: iv-gye6 (F3: Interbase batch SDK adoption — 6 plugins)

**Status:** PARTIALLY IMPLEMENTED (4/6 plugins)

### Evidence

**6 required plugins:**
1. **interline** — ✓ HAS `hooks/interbase-stub.sh` + `.claude-plugin/integration.json`
2. **intersynth** — ✓ HAS `hooks/interbase-stub.sh` + `.claude-plugin/integration.json`
3. **intermem** — ✓ HAS `hooks/interbase-stub.sh` + `.claude-plugin/integration.json`
4. **intertest** — ✗ NO `hooks/interbase-stub.sh` (hooks/ dir exists but is empty except hook.sh and hooks.json) + HAS `.claude-plugin/integration.json`
5. **internext** — ✗ NO `hooks/interbase-stub.sh` (hooks/ dir does NOT exist) + HAS `.claude-plugin/integration.json`
6. **tool-time** — ✗ NO `hooks/interbase-stub.sh` (hooks/ dir exists with agent-output-redirect.sh only) + HAS `.claude-plugin/integration.json`

### Interbase-stub.sh Content

All present stubs (interline, intersynth, intermem) are identical:
```bash
# interbase-stub.sh — shipped inside each plugin
# Sources live ~/.intermod/ copy if present; falls back to inline stubs

[[ -n "${_INTERBASE_LOADED:-}" ]] && return 0

# Try centralized copy first (ecosystem users)
_interbase_live="${INTERMOD_LIB:-${HOME}/.intermod/interbase/interbase.sh}"
if [[ -f "$_interbase_live" ]]; then
    _INTERBASE_SOURCE="live"
    source "$_interbase_live"
    return 0
fi

# Fallback: inline stubs (standalone users)
_INTERBASE_LOADED=1
_INTERBASE_SOURCE="stub"
ib_has_ic()          { command -v ic &>/dev/null; }
ib_has_bd()          { command -v bd &>/dev/null; }
ib_has_companion()   { compgen -G "${HOME}/.claude/plugins/cache/*/${1:-_}/*" &>/dev/null; }
ib_get_bead()        { echo "${CLAVAIN_BEAD_ID:-}"; }
ib_in_ecosystem()    { return 1; }
ib_in_sprint()       { return 1; }
ib_phase_set()       { return 0; }
ib_nudge_companion() { return 0; }
ib_emit_event()      { return 0; }
ib_session_status()  { return 0; }
```

### Integration.json Status

All 6 plugins have `.claude-plugin/integration.json`:
- **interline:** ecosystem=true, interbase_min_version 1.0.0, standalone features + integrated features
- **intersynth:** ecosystem=true, interbase_min_version 1.0.0
- **intermem:** ecosystem=true, interbase_min_version 1.0.0
- **intertest:** ecosystem=true, interbase_min_version 1.0.0, integrated feature from intercheck
- **internext:** ecosystem=true, interbase_min_version 1.0.0, integrated features from interstat + interject
- **tool-time:** ecosystem=true, interbase_min_version 1.0.0, integrated feature from interstat

### Conclusion
**NOT COMPLETE.** 4/6 plugins have both stub + integration.json, but 3 plugins (intertest, internext, tool-time) are missing the interbase-stub.sh hook file. The integration.json files are present and declare ecosystem intent, but the hooks are incomplete.

---

## Bead 3: iv-1sc0 (F7: Companion plugin dependency graph)

**Status:** IMPLEMENTED ✓

### Evidence

**File:** `/root/projects/Interverse/companion-graph.json` exists

**Content Structure:**
```json
{
  "$comment": "Machine-readable companion dependency graph for Interverse plugins...",
  "version": "1.0.0",
  "edges": [
    {
      "from": "interline",
      "to": "intercheck",
      "relationship": "enhances",
      "benefit": "Shows context pressure indicator in statusline"
    },
    ...
  ]
}
```

**Graph Contents (102 lines, 13 edges):**
1. interline → intercheck (enhances: pressure indicator)
2. interline → interstat (enhances: budget alert)
3. interline → interphase (enhances: bead context)
4. interline → interlock (enhances: coordination state)
5. interflux → intersynth (requires-for-feature: verdict synthesis)
6. interflux → interwatch (enhances: auto-trigger on drift)
7. interflux → interstat (enhances: budget-aware triage)
8. intermem → interwatch (enhances: citation freshness)
9. intermem → intercheck (enhances: context pressure checkpoints)
10. internext → interstat (enhances: historical calibration)
11. internext → interject (enhances: discovery confidence)
12. intersynth → interflux (enhances: verdict consumption)
13. interflux → interphase (enhances: review completion tracking)

Plus 2 additional edges for intersynth→interphase and tool-time→interstat.

**Purpose:** Consumed by `/clavain:doctor` command for dependency validation.

### Conclusion
Graph file exists and is properly structured with semantic relationships and benefits documented.

---

## Bead 4: iv-sprh (F6: Cost-aware review depth — always-on budget signal)

**Status:** IMPLEMENTED ✓

### Evidence

**Signal Production:** `/root/projects/Interverse/os/clavain/commands/sprint.md`
- Lines show budget calculation and export:
  ```bash
  remaining=$(sprint_budget_remaining "$CLAVAIN_BEAD_ID")
  if [[ "$remaining" -gt 0 ]]; then
      export FLUX_BUDGET_REMAINING="$remaining"
  fi
  ```

**Signal Consumption:** `/root/projects/Interverse/plugins/interflux/skills/flux-drive/SKILL-compact.md`
- Budget override logic:
  ```
  **Sprint budget override:** If `FLUX_BUDGET_REMAINING` env var is set and non-zero, 
  apply: `effective_budget = min(yaml_budget, FLUX_BUDGET_REMAINING)`. 
  This allows sprint-level budget constraints to cap flux-drive dispatch. 
  Note in triage summary: `[sprint-constrained]` when sprint budget is tighter.
  ```

**How it works:**
1. Sprint controller reads remaining tokens from the bead's kernel run
2. Exports `FLUX_BUDGET_REMAINING` environment variable if positive
3. Flux-drive skill receives this signal during agent triage phase
4. Flux-drive applies budget constraint: `effective_budget = min(yaml_budget, FLUX_BUDGET_REMAINING)`
5. Budget-aware triage reduces agent count at high token spend (per companion-graph.json edge: interflux→interstat)
6. Triage output notes `[sprint-constrained]` when sprint budget is tighter than default

**Interline Integration:** Statusline layer 5 (lines 399-420) also reads budget signal from interstat interband signal file as an independent check.

### Conclusion
Fully implemented. Budget signal flows from sprint controller → flux-drive triage → agent count reduction, with always-on statusline indicator via interstat signal.

---

## Summary Table

| Bead | Title | Status | Gaps |
|------|-------|--------|------|
| iv-sk8t | Interline enrichment (pressure, budget) | ✓ DONE | None — both layers implemented |
| iv-gye6 | Interbase SDK (6 plugins) | ⚠️ PARTIAL | intertest, internext, tool-time missing interbase-stub.sh |
| iv-1sc0 | Companion graph | ✓ DONE | None — JSON graph exists and complete |
| iv-sprh | Budget-aware review depth | ✓ DONE | None — signal flows end-to-end |

---

## Actionable Next Steps

**High Priority (iv-gye6):**
- Create `/root/projects/Interverse/plugins/intertest/hooks/interbase-stub.sh` (copy from interline template)
- Create `/root/projects/Interverse/plugins/internext/hooks/interbase-stub.sh` (copy from interline template)
- Create `/root/projects/Interverse/plugins/tool-time/hooks/interbase-stub.sh` (copy from interline template)
- All 3 can be identical stubs; they just need to exist for the ecosystem loader

**Low Priority (for iv-gye6 verification):**
- Add hooks declarations to `.claude-plugin/plugin.json` for each plugin (if not already present)
- Verify `_INTERBASE_LOADED` guard works correctly across all plugins

---

## Technical Details for iv-sprh Implementation

**Budget Signal Flow:**
1. **Source:** Kernel run state in `.clavain/intercore.db` (row: run_id)
2. **Signal Export:** `sprint_budget_remaining()` in lib-sprint.sh queries kernel, calculates `total_budget - cumulative_tokens`
3. **Environment:** Export as `FLUX_BUDGET_REMAINING` before invoking flux-drive
4. **Consumption Point:** Flux-drive Phase 1.2 (agent triage), applies soft cap to agent count
5. **Observability:** 
   - Statusline shows real-time budget % (via interstat signal from session, independent of sprint state)
   - Flux-drive triage notes `[sprint-constrained]` in summary when sprint budget tighter than default

**Budget vs Pressure Signals:**
- **Pressure (intercheck signal):** Context window utilization % (80%+ yellow, 95%+ red)
- **Budget (interstat signal):** Token consumption % (50%+ yellow, 80%+ red) — a soft cap, not hard enforcement
- Both are ambient indicators (always visible in statusline regardless of dispatch/coord/bead state)
- Both inform review depth: pressure triggers checkpoints, budget triggers agent count reduction

