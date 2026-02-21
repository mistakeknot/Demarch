# Plugin Synergy Interop Implementation Plan
**Phase:** executing (as of 2026-02-21T03:46:36Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire Interverse plugins together through interband signals, statusline enrichment, interbase SDK adoption, and cross-plugin data bridges.

**Architecture:** Plugins communicate via interband (atomic JSON files under `~/.interband/<namespace>/<channel>/`). Publishers write signals, consumers read them. The interbase SDK provides ecosystem detection and companion nudges. No direct plugin-to-plugin RPC.

**Tech Stack:** Bash (hooks, interband library), JSON (interband envelopes, config), SQLite (interstat), jq (payload construction/parsing)

---

### Review Fixes Applied (2026-02-20)

Three review agents (architecture, correctness, quality) analyzed this plan. All fixes have been incorporated inline with `[ID]` tags tracing back to the findings. Summary of structural changes:

| ID | Severity | Fix |
|----|----------|-----|
| C1 | CRITICAL | Read `session_id` from stdin JSON, not phantom `CLAUDE_SESSION_ID` env var (Task 8) |
| C2 | CRITICAL | Consolidate all interband.sh changes into Task 1 (was split across Tasks 1, 2, 10) |
| H1 | HIGH | Use 5-candidate interband sourcing pattern from `lib-gates.sh` (Tasks 1, 2) |
| H2 | HIGH | Use heredoc for SQL queries, matching existing `post-task.sh` pattern (Task 2) |
| H3 | HIGH | Implement actual threshold-crossing logic with tier tracking (Task 2) |
| H4 | HIGH | Replace 30-char prefix dedup with agent-name-keyed session map (Task 9) |
| H5 | HIGH | Atomic `mkdir` rate-limit for checkpoint, atomic write for state (Task 10) |
| H6 | HIGH | Add `\|\| true` to all `source` calls under `set -euo pipefail` (Tasks 1, 2) |
| M1 | MEDIUM | Guard placement bug in stub template — set `_INTERBASE_LOADED=1` unconditionally (NOT in this plan — fix in `sdk/interbase/templates/interbase-stub.sh` before implementing) |
| M2 | MEDIUM | Remove hardcoded `/intermem:synthesize` from intercheck output (Task 10) |
| M3 | MEDIUM | Split Task 6 into four sub-tasks (6a-6d) for per-plugin rollback (Task 6) |
| M4 | MEDIUM | Rename `_ic_` temporaries to `_icm_` to avoid library namespace collision (Task 1) |
| M5 | MEDIUM | Source interband.sh for `interband_read_payload` envelope validation (Task 8) |
| M6 | MEDIUM | Add numeric guards on `INTERSTAT_TOKEN_BUDGET` and computed values (Task 2) |
| M7 | MEDIUM | Remove phantom `python3` guard around bash-only code (Task 10) |
| M8 | MEDIUM | Fix nudge `_ib_nudge_is_dismissed` jq-absent fallback: return 0 (silent), not 1 (fire always) — fix in interbase.sh, not this plan |
| M9 | MEDIUM | Replace destructive `mv ~/.intermod` test with `INTERMOD_LIB=/nonexistent` (Task 8) |
| C4 | SCOPE | Defer session-start hooks for plugins without concrete features (Task 6b-6d: integration.json only) |
| L1 | LOW | Use existing `$LEVEL` variable instead of duplicating thresholds (Task 1) |
| L2 | LOW | Add `set -euo pipefail` to all new session-start hooks (Tasks 4, 5, 6a) |
| L3 | LOW | Remove dead `_ic_interband_root` variable (Task 1) |
| L4 | LOW | Numeric guard on `_il_budget_int` against non-numeric strings (Task 3) |
| L5 | LOW | Add `interband_prune_channel` after writes (Tasks 1, 10) |
| L7 | LOW | Collapse multi-line for loops to one-liners (Task 6) |
| L8 | LOW | Add envelope structure validation to verify steps (Tasks 1, 2) |
| L9 | LOW | Remove unreliable `$(pwd)/.intermem` check; guard jq against non-array (Tasks 9, 10) |
| L10 | LOW | Cross-validate companion-graph.json edges against integration.json (Task 7) |
| L11 | LOW | Change Task 8 from "replace contents" to "append block" (Task 8) |

**Pre-implementation prerequisite (NOT in this plan):** Fix `_INTERBASE_LOADED=1` guard in `sdk/interbase/templates/interbase-stub.sh` — set unconditionally before live source attempt, not only in fallback path [M1]. Also fix `_ib_nudge_is_dismissed` jq-absent fallback to return 0 (treated as dismissed) instead of 1 [M8].

---

### Task 1: Register All Interband Signals + Add Pressure Publisher to intercheck

> **Review fix [C2]:** All interband.sh changes consolidated here (was split across Tasks 1, 2, 10). Tasks 2 and 10 no longer modify interband.sh.

**Files:**
- Modify: `infra/interband/lib/interband.sh:167-196` (add validation for all three new payload types)
- Modify: `plugins/intercheck/hooks/context-monitor.sh:62-97` (after state write, before threshold output)

**Step 1: Add ALL new payload validations to interband.sh**

Add three new cases to `interband_validate_payload()` in `infra/interband/lib/interband.sh`. Insert after the `interlock:coordination_signal` case (line 196):

```bash
        intercheck:context_pressure)
            echo "$payload_json" | jq -e '
                (.level | type == "string" and test("^(green|yellow|orange|red)$")) and
                (.pressure | type == "number" and . >= 0) and
                (.est_tokens | type == "number" and . >= 0) and
                (.ts | type == "number")
            ' >/dev/null 2>&1 || return 1
            ;;
        interstat:budget_alert)
            echo "$payload_json" | jq -e '
                (.pct_consumed | type == "number" and . >= 0 and . <= 100) and
                (.total_tokens | type == "number" and . >= 0) and
                (.session_id | type == "string" and length > 0) and
                (.ts | type == "number")
            ' >/dev/null 2>&1 || return 1
            ;;
        intercheck:checkpoint_needed)
            echo "$payload_json" | jq -e '
                (.trigger | type == "string" and length > 0) and
                (.ts | type == "number")
            ' >/dev/null 2>&1 || return 1
            ;;
```

**Step 2: Add ALL interband channel defaults**

In `interband.sh`, add to `interband_default_retention_secs()`:

```bash
        intercheck:pressure)    echo "3600" ;;   # 1h (ephemeral, per-session)
        interstat:budget)       echo "21600" ;;  # 6h
        intercheck:checkpoint)  echo "3600" ;;   # 1h
```

And to `interband_default_max_files()`:

```bash
        intercheck:pressure)    echo "64" ;;
        interstat:budget)       echo "64" ;;
        intercheck:checkpoint)  echo "32" ;;
```

**Step 3: Add interband write to context-monitor.sh**

> **Review fixes applied:** [M4] Use `_icm_` prefix (avoids collision with `_ic_*` library namespace). [H1] Use 5-candidate sourcing pattern from `lib-gates.sh`. [L1] Use existing `$LEVEL` variable instead of duplicating thresholds. [H6] Add `|| true` to `source`. [L3] Remove dead `_icm_ib_root` variable. [L5] Add `interband_prune_channel` after write.

In `plugins/intercheck/hooks/context-monitor.sh`, after line 63 (`_ic_write_state "$SF" "$NEW_STATE"`), but **before** the `case "$LEVEL"` block so `$LEVEL` is computed first, add the interband signal write. Note: the interband write must be placed **inside or after** the `case "$LEVEL"` computation so `$LEVEL` is available. If `$LEVEL` is computed at line 67 and the `case` begins at line 72, insert the interband block between lines 67 and 72:

```bash
# Write pressure level to interband for statusline and other consumers
_icm_ib_lib=""
_icm_repo_root="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
for _icm_ib_candidate in \
    "${INTERBAND_LIB:-}" \
    "${SCRIPT_DIR}/../../../infra/interband/lib/interband.sh" \
    "${SCRIPT_DIR}/../../../interband/lib/interband.sh" \
    "${_icm_repo_root}/../interband/lib/interband.sh" \
    "${HOME}/.local/share/interband/lib/interband.sh"; do
  [[ -n "$_icm_ib_candidate" && -f "$_icm_ib_candidate" ]] && _icm_ib_lib="$_icm_ib_candidate" && break
done

if [[ -n "$_icm_ib_lib" ]]; then
  source "$_icm_ib_lib" || true

  _icm_ib_payload=$(jq -n -c \
    --arg level "$LEVEL" \
    --argjson pressure "$PRESSURE" \
    --argjson est_tokens "$EST_TOKENS" \
    --argjson ts "$(date +%s)" \
    '{level:$level, pressure:$pressure, est_tokens:$est_tokens, ts:$ts}')
  _icm_ib_file=$(interband_path "intercheck" "pressure" "$SID" 2>/dev/null) || _icm_ib_file=""
  if [[ -n "$_icm_ib_file" ]]; then
    interband_write "$_icm_ib_file" "intercheck" "context_pressure" "$SID" "$_icm_ib_payload" 2>/dev/null || true
    interband_prune_channel "intercheck" "pressure" 2>/dev/null || true
  fi
fi
```

**Step 4: Verify context-monitor.sh still works**

Run: `echo '{"session_id":"test-123","tool_name":"Read","tool_output":"hello"}' | bash plugins/intercheck/hooks/context-monitor.sh`
Expected: No output (green level). Check `/tmp/intercheck-test-123.json` exists. Check `~/.interband/intercheck/pressure/test-123.json` was created.

Verify the interband envelope structure:

```bash
jq -e '(.version | startswith("1.")) and .namespace == "intercheck" and .type == "context_pressure" and (.payload.level | type == "string") and (.payload.pressure | type == "number") and (.payload.est_tokens | type == "number")' ~/.interband/intercheck/pressure/test-123.json && echo "Envelope valid" || echo "FAIL: invalid envelope"
```

**Step 5: Clean up test artifacts**

```bash
rm -f /tmp/intercheck-test-123.json ~/.interband/intercheck/pressure/test-123.json
```

**Step 6: Commit**

```bash
git -C infra/interband add lib/interband.sh && git -C infra/interband commit -m "feat(interband): add intercheck + interstat payload validation and channel defaults"
git -C plugins/intercheck add hooks/context-monitor.sh && git -C plugins/intercheck commit -m "feat(intercheck): publish context pressure to interband"
```

---

### Task 2: Add Interband Budget Signal to interstat [DONE]

> **Review fix [C2]:** interband.sh validation and defaults already added in Task 1. This task only modifies `post-task.sh`.

**Files:**
- Modify: `plugins/interstat/hooks/post-task.sh:41-61` (after SQLite INSERT)

**Step 1: Add budget alert emission to post-task.sh**

> **Review fixes applied:** [H1] Use 5-candidate sourcing pattern from `lib-gates.sh`. [H2] Use heredoc for SQL query (matches existing INSERT pattern). [M6] Add numeric guards on `_is_budget` and `_is_total`. [H3] Implement actual threshold-crossing logic with tier tracking. [H6] Add `|| true` to `source`.

In `plugins/interstat/hooks/post-task.sh`, after the successful SQLite INSERT (after line 61), add:

```bash
# Emit budget alert to interband if sprint budget tracking is active
_is_interband_lib=""
_is_repo_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null || true)"
for _is_lib_candidate in \
    "${INTERBAND_LIB:-}" \
    "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../infra/interband/lib" 2>/dev/null && pwd)/interband.sh" \
    "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../interband/lib" 2>/dev/null && pwd)/interband.sh" \
    "${_is_repo_root}/../interband/lib/interband.sh" \
    "${HOME}/.local/share/interband/lib/interband.sh"; do
  [[ -n "$_is_lib_candidate" && -f "$_is_lib_candidate" ]] && _is_interband_lib="$_is_lib_candidate" && break
done

if [[ -n "$_is_interband_lib" && -n "$session_id" ]]; then
  source "$_is_interband_lib" || true

  # Query total tokens for this session (heredoc matches existing INSERT pattern)
  _is_total=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
PRAGMA busy_timeout=5000;
SELECT COALESCE(SUM(result_length / 4), 0)
FROM agent_runs
WHERE session_id='$(printf "%s" "$session_id" | sed "s/'/''/g")';
SQL
  )

  # Guard against non-numeric values
  _is_budget="${INTERSTAT_TOKEN_BUDGET:-0}"
  [[ "$_is_budget" =~ ^[0-9]+$ ]] || _is_budget=0
  [[ "$_is_total" =~ ^[0-9]+$ ]] || _is_total=0

  if [[ "$_is_budget" -gt 0 && "$_is_total" -gt 0 ]]; then
    _is_pct=$(awk "BEGIN{printf \"%.1f\", ($_is_total / $_is_budget) * 100}" 2>/dev/null || echo "0")
    _is_pct_int="${_is_pct%.*}"
    [[ "$_is_pct_int" =~ ^[0-9]+$ ]] || _is_pct_int=0

    # Determine current tier
    _is_tier=""
    if [[ "$_is_pct_int" -ge 95 ]]; then _is_tier="critical"
    elif [[ "$_is_pct_int" -ge 80 ]]; then _is_tier="high"
    elif [[ "$_is_pct_int" -ge 50 ]]; then _is_tier="medium"
    fi

    # Only emit at threshold crossings (tier changes), not every event above 50%
    if [[ -n "$_is_tier" ]]; then
      _is_tier_file="/tmp/interstat-budget-tier-${session_id}"
      _is_last_tier=$(cat "$_is_tier_file" 2>/dev/null || echo "")
      if [[ "$_is_tier" != "$_is_last_tier" ]]; then
        printf '%s' "$_is_tier" > "$_is_tier_file" 2>/dev/null || true
        _is_ib_payload=$(jq -n -c \
          --argjson pct_consumed "$_is_pct" \
          --argjson total_tokens "$_is_total" \
          --arg session_id "$session_id" \
          --argjson ts "$(date +%s)" \
          '{pct_consumed:$pct_consumed, total_tokens:$total_tokens, session_id:$session_id, ts:$ts}')
        _is_ib_file=$(interband_path "interstat" "budget" "$session_id" 2>/dev/null) || _is_ib_file=""
        if [[ -n "$_is_ib_file" ]]; then
          interband_write "$_is_ib_file" "interstat" "budget_alert" "$session_id" "$_is_ib_payload" 2>/dev/null || true
        fi
      fi
    fi
  fi
fi
```

**Step 2: Verify post-task.sh still works**

Run: `echo '{"session_id":"test-456","tool_input":{"subagent_type":"Explore","description":"test"},"tool_output":"result"}' | bash plugins/interstat/hooks/post-task.sh`
Expected: Exit 0. Check `~/.claude/interstat/metrics.db` has a new row.

Verify envelope if budget signal was emitted:

```bash
[[ -f ~/.interband/interstat/budget/test-456.json ]] && jq -e '(.version | startswith("1.")) and .namespace == "interstat" and .type == "budget_alert" and (.payload.pct_consumed | type == "number")' ~/.interband/interstat/budget/test-456.json && echo "Envelope valid" || echo "No budget signal (expected if INTERSTAT_TOKEN_BUDGET not set)"
```

**Step 3: Commit**

```bash
git -C plugins/interstat add hooks/post-task.sh && git -C plugins/interstat commit -m "feat(interstat): publish budget alerts to interband at threshold crossings"
```

---

### Task 3: Enrich interline Statusline with Pressure and Budget [DONE]

**Files:**
- Modify: `plugins/interline/scripts/statusline.sh:358-401` (add new layers before building status line)

**Step 1: Add pressure indicator layer**

In `plugins/interline/scripts/statusline.sh`, add a new layer after the context window display (after line 377, before `# --- Build status line ---`):

```bash
# --- Layer 4: Context pressure from intercheck interband signal ---
pressure_label=""
if _il_cfg_bool '.layers.pressure'; then
  if [ -n "$session_id" ]; then
    _il_pressure_file="$_il_interband_root/intercheck/pressure/${session_id}.json"
    if [ -f "$_il_pressure_file" ]; then
      _il_pressure_level=$(_il_interband_payload_field "$_il_pressure_file" "level")
      if [ -n "$_il_pressure_level" ] && [ "$_il_pressure_level" != "green" ]; then
        case "$_il_pressure_level" in
          yellow)  _il_pressure_color="${cfg_color_context_warn:-220}" ;;
          orange)  _il_pressure_color="208" ;;
          red)     _il_pressure_color="${cfg_color_context_critical:-196}" ;;
          *)       _il_pressure_color="245" ;;
        esac
        pressure_label="$(_il_color "$_il_pressure_color" "$_il_pressure_level")"
      fi
    fi
  fi
fi

# --- Layer 5: Budget alert from interstat interband signal ---
budget_label=""
if _il_cfg_bool '.layers.budget'; then
  if [ -n "$session_id" ]; then
    _il_budget_file="$_il_interband_root/interstat/budget/${session_id}.json"
    if [ -f "$_il_budget_file" ]; then
      _il_budget_pct=$(_il_interband_payload_field "$_il_budget_file" "pct_consumed")
      if [ -n "$_il_budget_pct" ]; then
        _il_budget_int="${_il_budget_pct%.*}"
        # Guard against non-numeric values (e.g., jq returning "null")
        case "$_il_budget_int" in ''|*[!0-9]*) _il_budget_int=0 ;; esac
        if [ "${_il_budget_int:-0}" -ge 80 ]; then
          _il_budget_color="${cfg_color_context_critical:-196}"
          budget_label="$(_il_color "$_il_budget_color" "${_il_budget_int}% budget")"
        elif [ "${_il_budget_int:-0}" -ge 50 ]; then
          _il_budget_color="${cfg_color_context_warn:-220}"
          budget_label="$(_il_color "$_il_budget_color" "${_il_budget_int}% budget")"
        fi
      fi
    fi
  fi
fi
```

**Step 2: Append new indicators to the status line**

Modify the status line build section (around lines 387-400). After the existing bead/phase/dispatch block, append the new indicators:

```bash
# Append ambient indicators (always visible, independent of dispatch/coord/bead)
if [ -n "$pressure_label" ]; then
  status_line="$status_line${sep}$pressure_label"
fi
if [ -n "$budget_label" ]; then
  status_line="$status_line${sep}$budget_label"
fi
```

Insert this before the final `echo -e "$status_line"`.

**Step 3: Test statusline with mock interband signals**

Create mock signals and verify rendering:

```bash
mkdir -p ~/.interband/intercheck/pressure ~/.interband/interstat/budget
echo '{"version":"1.0.0","namespace":"intercheck","type":"context_pressure","session_id":"test","timestamp":"2026-02-20T00:00:00Z","payload":{"level":"orange","pressure":95.5,"est_tokens":185000,"ts":1740000000}}' > ~/.interband/intercheck/pressure/test.json
echo '{"model":{"display_name":"Claude"},"workspace":{"project_dir":"/tmp"},"session_id":"test","context_window":{"used_percentage":45}}' | bash plugins/interline/scripts/statusline.sh
```

Expected: Status line includes "orange" in the output.

**Step 4: Clean up test signals**

```bash
rm -f ~/.interband/intercheck/pressure/test.json ~/.interband/interstat/budget/test.json
```

**Step 5: Commit**

```bash
git -C plugins/interline add scripts/statusline.sh
git -C plugins/interline commit -m "feat(interline): show context pressure and budget alerts from interband"
```

---

### Task 4: Interbase SDK Adoption — interline [DONE]

**Files:**
- Create: `plugins/interline/hooks/interbase-stub.sh` (copy from `sdk/interbase/templates/interbase-stub.sh`)
- Create: `plugins/interline/.claude-plugin/integration.json`
- Create: `plugins/interline/hooks/session-start.sh`
- Modify: `plugins/interline/.claude-plugin/plugin.json` (no changes needed, hooks auto-detected)

**Step 1: Copy interbase stub**

```bash
cp sdk/interbase/templates/interbase-stub.sh plugins/interline/hooks/interbase-stub.sh
```

**Step 2: Create integration.json**

Create `plugins/interline/.claude-plugin/integration.json`:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [
    "Workflow phase display from transcript analysis",
    "Git branch and model display",
    "Context window percentage"
  ],
  "integrated_features": [
    { "feature": "Context pressure indicator from intercheck", "requires": "intercheck" },
    { "feature": "Budget alert from interstat", "requires": "interstat" },
    { "feature": "Coordination state from interlock", "requires": "interlock" },
    { "feature": "Bead context from interphase", "requires": "interphase" }
  ],
  "companions": {
    "recommended": ["intercheck", "interphase"],
    "optional": ["interstat", "interlock"]
  }
}
```

**Step 3: Create session-start hook**

> **Review fix [L2]:** Added `set -euo pipefail` for consistency with all other hooks in the codebase.

Create `plugins/interline/hooks/session-start.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
# interline session-start hook — source interbase and nudge companions
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$HOOK_DIR/interbase-stub.sh"

ib_session_status
ib_nudge_companion "intercheck" "Adds context pressure indicator to your statusline"
```

**Step 4: Register the session-start hook**

> **Review fix [L2 from architecture]:** Check if `hooks.json` already exists before creating (matching Task 5's guard pattern).

Check if `plugins/interline/hooks/hooks.json` exists. If so, merge the SessionStart entry. If not, create it:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Step 5: Make session-start executable and test**

```bash
chmod +x plugins/interline/hooks/session-start.sh
bash plugins/interline/hooks/session-start.sh
```

Expected: No errors. In standalone mode, `ib_nudge_companion` is a no-op.

**Step 6: Commit**

```bash
git -C plugins/interline add hooks/interbase-stub.sh hooks/session-start.sh hooks/hooks.json .claude-plugin/integration.json
git -C plugins/interline commit -m "feat(interline): adopt interbase SDK with companion nudges"
```

---

### Task 5: Interbase SDK Adoption — intersynth [DONE]

**Files:**
- Create: `plugins/intersynth/hooks/interbase-stub.sh`
- Create: `plugins/intersynth/.claude-plugin/integration.json`
- Create: `plugins/intersynth/hooks/session-start.sh`

**Step 1: Copy interbase stub**

```bash
cp sdk/interbase/templates/interbase-stub.sh plugins/intersynth/hooks/interbase-stub.sh
```

**Step 2: Create integration.json**

Create `plugins/intersynth/.claude-plugin/integration.json`:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [
    "Multi-agent verdict aggregation and deduplication",
    "Compact summary generation from agent output"
  ],
  "integrated_features": [
    { "feature": "Auto-create beads from P0/P1 verdict findings", "requires": "beads" },
    { "feature": "Sprint-aware verdict linking", "requires": "interphase" }
  ],
  "companions": {
    "recommended": ["interflux"],
    "optional": ["interphase"]
  }
}
```

**Step 3: Create session-start hook**

Create `plugins/intersynth/hooks/session-start.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
# intersynth session-start hook — source interbase and nudge companions
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$HOOK_DIR/interbase-stub.sh"

ib_session_status
ib_nudge_companion "interflux" "Enables multi-agent review with verdict synthesis"
```

**Step 4: Register hook — check if hooks.json already exists**

Check `plugins/intersynth/hooks/hooks.json`. If it exists, add the SessionStart entry. If not, create it:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Step 5: Make executable and test**

```bash
chmod +x plugins/intersynth/hooks/session-start.sh
bash plugins/intersynth/hooks/session-start.sh
```

**Step 6: Commit**

```bash
git -C plugins/intersynth add hooks/interbase-stub.sh hooks/session-start.sh hooks/hooks.json .claude-plugin/integration.json
git -C plugins/intersynth commit -m "feat(intersynth): adopt interbase SDK with companion nudges"
```

---

### Task 6: Interbase SDK Adoption — intermem, intertest, internext, tool-time [DONE]

> **Review fixes applied:** [M3] Split into four independent sub-tasks (6a–6d) for per-plugin rollback and accurate progress tracking. [C4] intertest, internext, tool-time: create `integration.json` only (documentation artifacts); defer session-start hooks until a concrete integrated feature ships in a plan that uses them. intermem gets hooks because checkpoint synthesis (Task 10) is a concrete consumer. [L2] Added `set -euo pipefail` to session-start stubs. [L7] Collapsed multi-line loops to one-liners. [M3-note] Verify intermem plugin structure before SDK adoption (it may lack standard plugin layout).

---

#### Task 6a: Interbase SDK Adoption — intermem

**Prerequisites:** Verify `plugins/intermem/` has standard plugin structure (`.claude-plugin/plugin.json`, `hooks/` directory). If not, create the necessary directories first.

**Step 1: Copy interbase stub**

```bash
mkdir -p plugins/intermem/hooks && cp sdk/interbase/templates/interbase-stub.sh plugins/intermem/hooks/interbase-stub.sh
```

**Step 2: Create integration.json**

Create `plugins/intermem/.claude-plugin/integration.json`:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [
    "Auto-memory synthesis and promotion to reference docs",
    "Time-based decay and demotion of stale entries"
  ],
  "integrated_features": [
    { "feature": "Citation freshness from interwatch drift scores", "requires": "interwatch" },
    { "feature": "Smart checkpoint synthesis from intercheck pressure", "requires": "intercheck" }
  ],
  "companions": {
    "recommended": ["interwatch"],
    "optional": ["intercheck"]
  }
}
```

**Step 3: Create session-start hook** (intermem has a concrete consumer: Task 10 checkpoint synthesis)

```bash
#!/usr/bin/env bash
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOK_DIR/interbase-stub.sh"
ib_session_status
ib_nudge_companion "interwatch" "Enables citation freshness checking for promoted entries"
```

**Step 4: Register SessionStart hook**

Check if `plugins/intermem/hooks/hooks.json` exists. If so, merge. If not, create with standard SessionStart entry.

**Step 5: Test and commit**

```bash
chmod +x plugins/intermem/hooks/session-start.sh && bash plugins/intermem/hooks/session-start.sh && echo "intermem: OK" || echo "intermem: FAIL"
git -C plugins/intermem add hooks/interbase-stub.sh hooks/session-start.sh .claude-plugin/integration.json && [ -f plugins/intermem/hooks/hooks.json ] && git -C plugins/intermem add hooks/hooks.json; git -C plugins/intermem commit -m "feat(intermem): adopt interbase SDK with companion nudges"
```

---

#### Task 6b: Interbase SDK Adoption — intertest (integration.json only)

> No session-start hook — intertest has no concrete integrated feature shipping in this plan.

**Step 1: Create integration.json**

Create `plugins/intertest/.claude-plugin/integration.json`:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [
    "Systematic debugging discipline",
    "Test-driven development guidance",
    "Verification gates before completion claims"
  ],
  "integrated_features": [
    { "feature": "Syntax error stream from intercheck", "requires": "intercheck" }
  ],
  "companions": {
    "recommended": [],
    "optional": ["intercheck"]
  }
}
```

**Step 2: Commit**

```bash
git -C plugins/intertest add .claude-plugin/integration.json && git -C plugins/intertest commit -m "feat(intertest): add integration.json for ecosystem metadata"
```

---

#### Task 6c: Interbase SDK Adoption — internext (integration.json only)

> No session-start hook — internext has no concrete integrated feature shipping in this plan.

**Step 1: Create integration.json**

Create `plugins/internext/.claude-plugin/integration.json`:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [
    "Work prioritization with impact/effort/risk scoring",
    "Tradeoff-aware next-task recommendations"
  ],
  "integrated_features": [
    { "feature": "Historical effort calibration from interstat", "requires": "interstat" },
    { "feature": "Discovery confidence boost from interject", "requires": "interject" }
  ],
  "companions": {
    "recommended": [],
    "optional": ["interstat", "interject"]
  }
}
```

**Step 2: Commit**

```bash
git -C plugins/internext add .claude-plugin/integration.json && git -C plugins/internext commit -m "feat(internext): add integration.json for ecosystem metadata"
```

---

#### Task 6d: Interbase SDK Adoption — tool-time (integration.json only)

> No session-start hook — tool-time has no concrete integrated feature shipping in this plan.

**Step 1: Create integration.json**

Create `plugins/tool-time/.claude-plugin/integration.json`:

```json
{
  "ecosystem": "interverse",
  "interbase_min_version": "1.0.0",
  "ecosystem_only": false,
  "standalone_features": [
    "Tool usage event collection and analytics",
    "Usage pattern dashboards"
  ],
  "integrated_features": [
    { "feature": "Cross-reference with interstat token metrics", "requires": "interstat" }
  ],
  "companions": {
    "recommended": [],
    "optional": ["interstat"]
  }
}
```

**Step 2: Commit**

```bash
git -C plugins/tool-time add .claude-plugin/integration.json && git -C plugins/tool-time commit -m "feat(tool-time): add integration.json for ecosystem metadata"
```

---

### Task 7: Companion Plugin Dependency Graph [DONE]

**Files:**
- Create: `companion-graph.json` (at Interverse root)

**Step 1: Create companion-graph.json**

Create `/root/projects/Interverse/companion-graph.json`:

```json
{
  "$comment": "Machine-readable companion dependency graph for Interverse plugins. Edges describe 'from benefits when to is installed'. Consumed by /clavain:doctor.",
  "version": "1.0.0",
  "edges": [
    {
      "from": "interline",
      "to": "intercheck",
      "relationship": "enhances",
      "benefit": "Shows context pressure indicator in statusline"
    },
    {
      "from": "interline",
      "to": "interstat",
      "relationship": "enhances",
      "benefit": "Shows budget alert indicator in statusline"
    },
    {
      "from": "interline",
      "to": "interphase",
      "relationship": "enhances",
      "benefit": "Shows active bead context in statusline"
    },
    {
      "from": "interline",
      "to": "interlock",
      "relationship": "enhances",
      "benefit": "Shows multi-agent coordination state in statusline"
    },
    {
      "from": "interflux",
      "to": "intersynth",
      "relationship": "requires-for-feature",
      "benefit": "Verdict synthesis and deduplication after multi-agent review"
    },
    {
      "from": "interflux",
      "to": "interwatch",
      "relationship": "enhances",
      "benefit": "Auto-triggers review when document drift detected"
    },
    {
      "from": "interflux",
      "to": "interstat",
      "relationship": "enhances",
      "benefit": "Budget-aware agent triage (fewer agents at high token spend)"
    },
    {
      "from": "intermem",
      "to": "interwatch",
      "relationship": "enhances",
      "benefit": "Citation freshness checking for promoted memory entries"
    },
    {
      "from": "intermem",
      "to": "intercheck",
      "relationship": "enhances",
      "benefit": "Smart checkpoint synthesis at context pressure thresholds"
    },
    {
      "from": "internext",
      "to": "interstat",
      "relationship": "enhances",
      "benefit": "Historical token data calibrates effort estimates"
    },
    {
      "from": "internext",
      "to": "interject",
      "relationship": "enhances",
      "benefit": "Discovery confidence boosts priority scoring"
    },
    {
      "from": "intersynth",
      "to": "interflux",
      "relationship": "enhances",
      "benefit": "Enables multi-agent review verdict consumption"
    }
  ]
}
```

**Step 2: Validate the graph**

> **Review fix [L10]:** Validation now cross-checks edges against each plugin's `integration.json` companions declarations.

```bash
python3 -c "
import json, os, pathlib
g = json.load(open('companion-graph.json'))
plugins = set(os.listdir('plugins'))
errors = []
for e in g['edges']:
    if e['from'] not in plugins:
        errors.append(f\"Unknown plugin: {e['from']}\")
    if e['to'] not in plugins:
        errors.append(f\"Unknown plugin: {e['to']}\")

# Cross-validate: every companion in integration.json should appear in the graph
for p in plugins:
    ij = pathlib.Path(f'plugins/{p}/.claude-plugin/integration.json')
    if ij.exists():
        meta = json.load(open(ij))
        companions = meta.get('companions', {})
        for kind in ('recommended', 'optional'):
            for comp in companions.get(kind, []):
                if not any(e['from'] == p and e['to'] == comp for e in g['edges']):
                    errors.append(f'{p}: companion {comp} ({kind}) not in graph')

print(f\"{len(g['edges'])} edges, {len(errors)} errors\")
for err in errors:
    print(f'  ERROR: {err}')
"
```

Expected: `12 edges, 0 errors`

**Step 3: Commit**

```bash
git add companion-graph.json
git commit -m "feat: add companion plugin dependency graph"
```

---

### Task 8: Cost-Aware Review Depth — Always-On Budget Signal [DONE]

> **Review fixes applied:** [C1] Read `session_id` from stdin JSON (NOT `CLAUDE_SESSION_ID` env var — that doesn't exist). [M5] Source interband.sh and use `interband_read_payload` for envelope validation instead of raw jq. [L11] Append new block after existing lines, not "replace contents". [M9] Use `INTERMOD_LIB=/nonexistent` override for fallback testing (not destructive `mv`). Export via `CLAUDE_ENV_FILE` so subsequent hooks can see the value.

**Files:**
- Modify: `plugins/interflux/hooks/session-start.sh` (append budget-reading block)

**Prerequisites:** Verify `plugins/interflux/hooks/session-start.sh` current contents. Grep for existing `command -v ic`, `command -v bd`, or `ib_has_ic` patterns that need replacing with `ib_*` calls (PRD F4 requirement).

**Step 1: Append budget-reading block to interflux session-start**

After the existing lines (`source "$HOOK_DIR/interbase-stub.sh"` and `ib_session_status`), append:

```bash
# Read interstat budget signal if available (always-on, not sprint-only)
# CRITICAL: session_id comes from stdin JSON, NOT from env var
HOOK_INPUT=$(cat)   # must consume stdin before anything else
_if_session_id=$(printf '%s' "$HOOK_INPUT" | jq -r '.session_id // empty' 2>/dev/null)

_if_interband_root="${INTERBAND_ROOT:-${HOME}/.interband}"

# Source interband for envelope validation
_if_interband_lib=""
_if_repo_root="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
for _if_lib_candidate in \
    "${INTERBAND_LIB:-}" \
    "${HOOK_DIR}/../../../infra/interband/lib/interband.sh" \
    "${HOOK_DIR}/../../../interband/lib/interband.sh" \
    "${_if_repo_root}/../interband/lib/interband.sh" \
    "${HOME}/.local/share/interband/lib/interband.sh"; do
  [[ -n "$_if_lib_candidate" && -f "$_if_lib_candidate" ]] && _if_interband_lib="$_if_lib_candidate" && break
done

if [[ -n "$_if_session_id" && -z "${FLUX_BUDGET_REMAINING:-}" ]]; then
  _if_budget_file="${_if_interband_root}/interstat/budget/${_if_session_id}.json"
  if [[ -f "$_if_budget_file" ]]; then
    # Use interband_read_payload for envelope validation if available
    _if_pct=""
    if [[ -n "$_if_interband_lib" ]]; then
      source "$_if_interband_lib" || true
      _if_payload=$(interband_read_payload "$_if_budget_file" 2>/dev/null) || _if_payload=""
      if [[ -n "$_if_payload" ]]; then
        _if_pct=$(printf '%s' "$_if_payload" | jq -r '.pct_consumed // empty' 2>/dev/null)
      fi
    else
      # Fallback: raw jq if interband.sh not available
      _if_pct=$(jq -r '.payload.pct_consumed // empty' "$_if_budget_file" 2>/dev/null)
    fi

    if [[ -n "$_if_pct" ]]; then
      _if_pct_int="${_if_pct%.*}"
      [[ "$_if_pct_int" =~ ^[0-9]+$ ]] || _if_pct_int=0
      # Convert percentage consumed to remaining tokens estimate
      _if_budget="${INTERSTAT_TOKEN_BUDGET:-500000}"
      [[ "$_if_budget" =~ ^[0-9]+$ ]] || _if_budget=500000
      _if_remaining=$(awk "BEGIN{printf \"%d\", $_if_budget * (100 - $_if_pct) / 100}" 2>/dev/null || echo "")
      if [[ -n "$_if_remaining" && "$_if_remaining" -gt 0 && -n "${CLAUDE_ENV_FILE:-}" ]]; then
        echo "export FLUX_BUDGET_REMAINING=${_if_remaining}" >> "$CLAUDE_ENV_FILE"
      fi
    fi
  fi
fi
```

**Important:** The `HOOK_INPUT=$(cat)` line must be at the **top** of the file, before `source "$HOOK_DIR/interbase-stub.sh"`, since stdin can only be consumed once. Restructure the hook so stdin is consumed first:

```bash
#!/usr/bin/env bash
set -euo pipefail
# interflux session-start hook — source interbase, read budget signal, emit status
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_INPUT=$(cat)   # consume stdin first — session_id is here

source "$HOOK_DIR/interbase-stub.sh"
ib_session_status

# [budget-reading block from above, using $HOOK_INPUT for session_id]
```

**Step 2: Verify interflux session-start works — live mode**

```bash
echo '{"session_id":"test-789"}' | bash plugins/interflux/hooks/session-start.sh && echo "OK"
```

Expected: `OK`. No interband file exists so `FLUX_BUDGET_REMAINING` stays unset.

**Step 3: Verify fallback mode (interbase stub only, no live intermod)**

```bash
echo '{"session_id":"test-789"}' | INTERMOD_LIB=/nonexistent bash plugins/interflux/hooks/session-start.sh 2>&1
```

Expected: Exit 0. Stub functions used. No errors.

**Step 4: Run existing interflux tests**

```bash
bash plugins/interflux/tests/test-budget.sh
```

This is a required regression gate, not optional discovery.

**Step 5: Commit**

```bash
git -C plugins/interflux add hooks/session-start.sh && git -C plugins/interflux commit -m "feat(interflux): always-on budget signal from interstat interband"
```

---

### Task 9: Verdict-to-Bead Bridge (Opt-in) [DONE]

> **Review fixes applied:** [H4] Replace 30-char prefix string-match dedup with agent-name-keyed session map. [H4] Filter to open/in_progress beads only (closed beads don't block new ones). [L9] Guard jq against non-array `bd list` output.

**Files:**
- Modify: `plugins/intersynth/hooks/lib-verdict.sh` (add `verdict_auto_create_beads` function)

**Step 1: Read existing lib-verdict.sh**

Read `plugins/intersynth/hooks/lib-verdict.sh` to understand the current API.

**Step 2: Add verdict_auto_create_beads function**

Append to `plugins/intersynth/hooks/lib-verdict.sh`:

```bash
# Auto-create beads for critical verdict findings (opt-in via INTERSYNTH_AUTO_BEAD=true)
verdict_auto_create_beads() {
    [[ "${INTERSYNTH_AUTO_BEAD:-}" == "true" ]] || return 0
    command -v bd >/dev/null 2>&1 || return 0

    local verdicts_dir="${1:-${HOME}/.clavain/verdicts}"
    [[ -d "$verdicts_dir" ]] || return 0

    # Session-scoped dedup map: agent-name → bead-id
    # Uses agent name (filename without .json) as stable key, not summary text
    local session_id="${CLAUDE_SESSION_ID:-$$}"
    local bead_map="/tmp/intersynth-bead-map-${session_id}.json"
    [[ -f "$bead_map" ]] || echo '{}' > "$bead_map"

    local created=0
    for verdict_file in "$verdicts_dir"/*.json; do
        [[ -f "$verdict_file" ]] || continue

        local status agent summary agent_key
        status=$(jq -r '.status // ""' "$verdict_file" 2>/dev/null)
        [[ "$status" == "NEEDS_ATTENTION" ]] || continue

        agent=$(jq -r '.agent // "unknown"' "$verdict_file" 2>/dev/null)
        summary=$(jq -r '.summary // ""' "$verdict_file" 2>/dev/null)
        [[ -n "$summary" ]] || continue

        # Dedup key: agent name from filename (stable identifier)
        agent_key="$(basename "$verdict_file" .json)"

        # Check session map first (O(1), no bd call)
        local mapped_id
        mapped_id=$(jq -r --arg k "$agent_key" '.[$k] // empty' "$bead_map" 2>/dev/null)
        [[ -z "$mapped_id" ]] || continue

        # Fallback: check open beads with longer prefix (50 chars) and status filter
        local title="Review finding: ${summary:0:60}"
        local existing
        existing=$(bd list --status=open --json --quiet 2>/dev/null \
          | jq -r --arg prefix "${summary:0:50}" \
            'if type == "array" then [.[] | select(.title | tostring | contains($prefix))] | length else 0 end' \
          2>/dev/null || echo "0")
        [[ "$existing" -eq 0 ]] || continue

        # Create bead
        local new_id
        new_id=$(bd create --title="$title" --type=task --priority=1 --description="From $agent review. $summary" 2>&1 | grep -oE 'iv-[a-z0-9]+' || echo "")
        if [[ -n "$new_id" ]]; then
            # Record in session map to prevent duplicates on re-invocation
            local tmp_map
            tmp_map=$(mktemp "${bead_map}.XXXXXX") || continue
            jq --arg k "$agent_key" --arg v "$new_id" '. + {($k): $v}' "$bead_map" > "$tmp_map" 2>/dev/null && mv -f "$tmp_map" "$bead_map" || rm -f "$tmp_map"
            created=$((created + 1))
        fi
    done

    if [[ "$created" -gt 0 ]]; then
        echo "[intersynth] Auto-created $created beads from critical verdict findings" >&2
    fi
}
```

**Step 3: Test the function (dry run)**

```bash
source plugins/intersynth/hooks/lib-verdict.sh
INTERSYNTH_AUTO_BEAD=false verdict_auto_create_beads && echo "Opt-out works"
```

Expected: Returns immediately (opt-in guard).

**Step 4: Run existing intersynth tests**

```bash
bash plugins/intersynth/tests/test-verdict.sh 2>/dev/null || echo "No existing test suite"
```

**Step 5: Commit**

```bash
git -C plugins/intersynth add hooks/lib-verdict.sh && git -C plugins/intersynth commit -m "feat(intersynth): opt-in verdict-to-bead bridge with agent-name dedup"
```

---

### Task 10: Smart Checkpoint Triggers [DONE]

> **Review fixes applied:** [C2] interband.sh changes already in Task 1 — this task only modifies context-monitor.sh. [M7] Removed `python3` guard (code uses only bash/jq/stat). [M2] Removed hardcoded `/intermem:synthesize` — the interband signal is sufficient; consumers decide how to act. [L9] Removed unreliable `$(pwd)/.intermem` check — CWD not guaranteed to be project root. Checkpoint fires on pressure threshold alone. [H5] Atomic `mkdir` rate-limit instead of check-then-act `touch`. [L5] Added `interband_prune_channel`. Uses `_icm_` prefix (consistent with Task 1).
>
> **Dependency:** Requires Task 1's interband library sourcing block in context-monitor.sh. The `_icm_ib_lib` variable must be set by Task 1's code.

**Files:**
- Modify: `plugins/intercheck/hooks/context-monitor.sh` (at orange threshold)

**Step 1: Add checkpoint trigger at Orange threshold**

In `plugins/intercheck/hooks/context-monitor.sh`, modify the `orange` case (around line 89-91):

```bash
  orange)
    # Smart checkpoint: signal intermem via interband at orange pressure
    _icm_checkpoint_msg=""
    _icm_last_checkpoint="/tmp/intercheck-intermem-checkpoint-${SID}"
    # Atomic rate-limit: mkdir is POSIX-atomic on local filesystems
    _icm_cp_lock="/tmp/intercheck-cp-lock-${SID}"
    if [[ ! -f "$_icm_last_checkpoint" || $(( NOW - $(stat -c %Y "$_icm_last_checkpoint" 2>/dev/null || echo 0) )) -gt 900 ]]; then
      if mkdir "$_icm_cp_lock" 2>/dev/null; then
        touch "$_icm_last_checkpoint" 2>/dev/null || true
        rmdir "$_icm_cp_lock" 2>/dev/null || true
        # Signal intermem via interband (requires Task 1's interband sourcing)
        if [[ -n "${_icm_ib_lib:-}" ]]; then
          _icm_cp_payload=$(jq -n -c --argjson ts "$NOW" '{"trigger":"orange_pressure","ts":$ts}')
          _icm_cp_file=$(interband_path "intercheck" "checkpoint" "$SID" 2>/dev/null) || _icm_cp_file=""
          if [[ -n "$_icm_cp_file" ]]; then
            interband_write "$_icm_cp_file" "intercheck" "checkpoint_needed" "$SID" "$_icm_cp_payload" 2>/dev/null || true
            interband_prune_channel "intercheck" "checkpoint" 2>/dev/null || true
            _icm_checkpoint_msg=" Consider synthesizing session memory before continuing."
          fi
        fi
      fi
    fi
    jq -n --arg msg "Context pressure is high (pressure: $PRESSURE, ~${EST_TOKENS} tokens). Finish current work and commit. Avoid launching new subagents.${_icm_checkpoint_msg}" \
      '{"additionalContext": $msg}'
    ;;
```

**Step 2: Test the modified orange case**

```bash
# Create a fake state file at orange-level pressure
echo '{"calls":100,"last_call_ts":'$(date +%s)',"pressure":95,"heavy_calls":40,"est_tokens":185000,"syntax_errors":0,"format_runs":0}' > /tmp/intercheck-test-cp.json
echo '{"session_id":"test-cp","tool_name":"Read","tool_output":"x"}' | bash plugins/intercheck/hooks/context-monitor.sh
```

Expected: Output includes "Context pressure is high" message. If interband is available, check `~/.interband/intercheck/checkpoint/test-cp.json` was created.

**Step 3: Clean up test files**

```bash
rm -f /tmp/intercheck-test-cp.json /tmp/intercheck-intermem-checkpoint-test-cp /tmp/intercheck-cp-lock-test-cp ~/.interband/intercheck/checkpoint/test-cp.json
```

**Step 4: Commit**

```bash
git -C plugins/intercheck add hooks/context-monitor.sh && git -C plugins/intercheck commit -m "feat(intercheck): smart checkpoint triggers for intermem synthesis"
```
