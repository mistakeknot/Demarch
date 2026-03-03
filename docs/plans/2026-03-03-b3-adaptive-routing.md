# Plan: B3 Adaptive Routing — Interspect Outcomes Drive Agent Selection

**Bead:** iv-i198
**PRD:** docs/prds/2026-03-03-b3-adaptive-routing.md

## Review Findings Incorporated

Flux-drive plan review (4 agents: correctness, integration, architecture, safety) identified 10 P0/P1 issues. All addressed below:

1. **DB path priority reordered** — `$CLAUDE_PROJECT_DIR` first, git root second, CWD-with-guard third (was: git root first, which resolves to plugin repo root from hook context)
2. **Division by zero guarded** — agents with `total_findings=0` excluded from recommendations
3. **`acted_on`/`dismissed` removed from schema** — verdict files don't have these fields; use `findings_count > 0` as signal instead
4. **Fast-path bypass documented** — `ic route model` skips bash implementation; shadow logging only fires in bash fallback path (Go extension is follow-up)
5. **Atomic writes** — `tmp.$$ + mv` for calibration file
6. **Safety floor applied during calibration output** — file contains floor-clamped recommendations, not raw scores
7. **`interspect-verdict.sh` dropped** — call `_interspect_record_verdict` as a function from call site, not through intermediate script
8. **lib-verdict.sh stays pure** — interspect fan-out moved to quality-gates call site
9. **Rollback procedure documented** — delete calibration file to disable
10. **reflect.md uses `_discover_interspect_plugin()`** — not fragile relative path

## Implementation

### Part 1: Fix PostToolUse evidence pipeline (F1)

**File:** `interverse/interspect/hooks/interspect-evidence.sh`

- [x] Add diagnostic: before `_interspect_ensure_db`, log CWD and resolved DB path to stderr when `INTERSPECT_DEBUG=1`

**File:** `interverse/interspect/hooks/lib-interspect.sh` (~line 33, `_interspect_db_path`)

- [x] Rewrite `_interspect_db_path()` with corrected priority:
  1. Prefer `$CLAUDE_PROJECT_DIR` if set (Claude Code sets this for the active project)
  2. Fall back to `git rev-parse --show-toplevel`
  3. Fall back to CWD **only if** `.clavain/interspect/` already exists there (existence guard)
  4. Return 1 if no valid root found (callers already handle failure)
- [x] Add diagnostic log to `_interspect_db_path()`: log which fallback branch was taken when `INTERSPECT_DEBUG=1`
- [ ] Test: dispatch an Agent subagent from Demarch root, verify `agent_dispatch` event appears in `.clavain/interspect/interspect.db`

### Part 2: Wire verdict outcomes into evidence (F2)

**File:** `interverse/interspect/hooks/lib-interspect.sh`

- [x] Add `interspect-verdict` to `_interspect_validate_hook_id()` allowlist (MUST be same commit as `_interspect_record_verdict`)
- [x] Add new function `_interspect_record_verdict(session_id, agent_name, status, findings_count, model_used)` that:
  - Calls `_interspect_ensure_db` first (sets `_INTERSPECT_DB` for consistent path resolution)
  - Normalizes `agent_name` via `_interspect_normalize_agent_name()`
  - Builds context JSON: `{status, findings_count, model_used}`
  - Calls `_interspect_insert_evidence` with event=`verdict_outcome`, hook_id=`interspect-verdict`
  - Note: `acted_on`/`dismissed` removed — verdict files don't have this data

**~~File: `interverse/interspect/hooks/interspect-verdict.sh`~~** — DROPPED (architecture review: unnecessary intermediate script; call `_interspect_record_verdict` directly as a function)

**File:** `os/clavain/commands/quality-gates.md` (or the hook that calls `verdict_parse_all`)

- [x] After `verdict_parse_all` + verdict consumption, add interspect fan-out at the **call site** (not inside lib-verdict.sh):
  ```bash
  # Record verdict outcomes to interspect (fail-open)
  if source "$CLAVAIN_ROOT/hooks/lib.sh" 2>/dev/null; then
      interspect_root=$(_discover_interspect_plugin 2>/dev/null) || interspect_root=""
      if [[ -n "$interspect_root" ]]; then
          source "${interspect_root}/hooks/lib-interspect.sh"
          for verdict_file in .clavain/verdicts/*.json; do
              agent=$(basename "$verdict_file" .json)
              status=$(jq -r '.status // "UNKNOWN"' "$verdict_file")
              findings=$(jq -r '.findings_count // 0' "$verdict_file")
              model=$(jq -r '.model // "unknown"' "$verdict_file")
              _interspect_record_verdict "$SESSION_ID" "$agent" "$status" "$findings" "$model" 2>/dev/null || true
          done
      fi
  fi
  ```
- [x] Guard: entire block wrapped in `|| true`, never blocks sprint
- [x] lib-verdict.sh remains unchanged (pure data-access library)

### Part 3: Agent scoring + calibration command (F3)

**File:** `interverse/interspect/commands/calibrate.md`

- [x] New command `/interspect:calibrate` that:
  1. Queries evidence DB with CASE-based name normalization at query time (same pattern as `_interspect_get_classified_patterns`):
     ```sql
     SELECT
       CASE
         WHEN source LIKE 'interflux:review:fd-%' THEN SUBSTR(source, 19)
         WHEN source LIKE 'interflux:fd-%' THEN SUBSTR(source, 11)
         ELSE source
       END as agent,
       event, context
     FROM evidence
     WHERE event IN ('agent_dispatch', 'verdict_outcome', 'override', 'disagreement_override')
     ```
  2. Groups by normalized agent name
  3. Computes per-agent: `hit_rate`, `evidence_sessions`, `confidence`
     - **Division by zero guard:** agents with `SUM(findings_count) = 0` get `reason="insufficient_findings"`, no recommendation, excluded from routing changes
     - Use `NULLIF` in SQL: `CAST(SUM(findings_count_nonzero) AS REAL) / NULLIF(SUM(total_findings), 0)`
  4. Applies recommendation logic (see PRD) with **safety floor applied at output time** — recommendations in the calibration file are already floor-clamped
  5. Writes `.clavain/interspect/routing-calibration.json` via atomic `tmp.$$ + mv`:
     ```bash
     local tmpfile="${calibration_path}.tmp.$$"
     jq '.' <<< "$calibration_json" > "$tmpfile"
     jq -e '.' "$tmpfile" >/dev/null 2>&1 || { rm -f "$tmpfile"; return 1; }
     mv "$tmpfile" "$calibration_path"
     ```
  6. Displays summary table: `Agent | Sessions | Hit Rate | Current | Recommended`

**File:** `interverse/interspect/hooks/lib-interspect.sh`

- [x] Add `_interspect_compute_agent_scores()` — read-only DB access (note: mutates global confidence cache as a side effect via `_interspect_load_confidence`)
- [x] Add `_interspect_write_routing_calibration()` — writes calibration file atomically using `tmp.$$ + mv`
- [x] Calibration file keys always in `fd-<name>` format (validate before writing)

### Part 4: lib-routing reads calibration — shadow mode (F4)

**File:** `os/clavain/scripts/lib-routing.sh`

- [x] Add `_routing_read_calibration()`:
  - Reads `.clavain/interspect/routing-calibration.json`
  - Validates: valid JSON, `schema_version == 1`, `agents` is an object
  - Validates model names: reject any `recommended_model` not in `haiku|sonnet|opus`
  - Returns empty map on any failure (file absent, malformed, unknown schema version)
  - **Not cached in `_ROUTING_CACHE_POPULATED`** — read fresh each call (small file, avoids stale calibration after reflect)
- [x] In `routing_resolve_model` bash path: after per-agent override check, before phase-specific category:
  - Read calibration
  - If agent has a recommendation with confidence ≥ 0.7 and ≥ 3 sessions:
    - Shadow mode (default): log `[interspect-shadow] fd-X: base=sonnet, calibrated=haiku` to stderr
    - Enforce mode (opt-in via `calibration.mode` in routing.yaml or `INTERSPECT_ROUTING_MODE` env override): assign to `$result` (DO NOT `echo + return` — must fall through to safety floor block)
  - **CRITICAL: calibration assigns to `$result` and falls through to existing safety floor at end of function. No early return.**

**Known limitation (this sprint):** When `ic route model` (Go router) is available and `CLAVAIN_RUN_ID` is not set, `routing_resolve_model` returns from the fast path before reaching the bash calibration layer. Shadow logging only fires in the bash fallback path. Extending the Go router for calibration is a follow-up.

**File:** `os/clavain/config/routing.yaml`

- [x] Add `calibration:` section:
  ```yaml
  calibration:
    mode: shadow  # shadow (default) | enforce
    # Env override: INTERSPECT_ROUTING_MODE=enforce
  ```
- [x] Update resolution order comment to include the calibration layer

### Part 5: Trigger in reflect phase (F5)

**File:** `os/clavain/commands/reflect.md`

- [x] After `calibrate-phase-costs` call (step 6), add calibration trigger using proper discovery:
  ```bash
  # Calibrate agent routing from evidence
  if source "${CLAUDE_PLUGIN_ROOT}/hooks/lib.sh" 2>/dev/null; then
      interspect_root=$(_discover_interspect_plugin 2>/dev/null) || interspect_root=""
      if [[ -n "$interspect_root" ]]; then
          source "${interspect_root}/hooks/lib-interspect.sh"
          _interspect_write_routing_calibration 2>/dev/null || true
      fi
  fi
  ```
- [x] Uses `_discover_interspect_plugin()` — handles cache lookup, env override, and fallback properly

### Part 6: Tests

- [x] Test `_interspect_db_path` fallback resolution:
  - `$CLAUDE_PROJECT_DIR` set → uses it regardless of git root
  - No `$CLAUDE_PROJECT_DIR`, in git repo → uses git root
  - No git root, CWD has `.clavain/interspect/` → uses CWD
  - No git root, CWD has no `.clavain/interspect/` → returns 1
- [x] Test `_interspect_record_verdict` inserts correct event type with normalized agent name
- [x] Test `_interspect_compute_agent_scores` with synthetic evidence data:
  - Agents with `findings_count=0` excluded (no recommendation)
  - Division by zero does not crash
  - Safety floor clamped in output
- [x] Test scoring logic: high hit_rate keeps tier, low hit_rate demotes, safety floor prevents below-sonnet in calibration output
- [x] Test `_routing_read_calibration`:
  - No file → empty map
  - Valid file → correct map
  - Malformed JSON → empty map
  - Unknown schema version → empty map
  - Invalid model name → rejected
- [x] Test `routing_resolve_model` with calibration: verify calibrated model goes through safety floor (no early return bypass)
- [x] Run existing interspect + clavain test suites — no regression

## Key Design Decisions

1. **Shadow mode first** — All calibrated routing logs what would change but doesn't act. Enforce mode opt-in via `routing.yaml` `calibration.mode` or `INTERSPECT_ROUTING_MODE` env override.
2. **Separate calibration file** — `routing-calibration.json` in `.clavain/interspect/`, not in `.claude/routing-overrides.json` (different concern: model tier vs binary exclusion).
3. **≥3 sessions threshold** — Matches cost calibration pattern. Prevents single-sprint outliers from affecting routing.
4. **Safety floors enforced at calibration output AND at routing resolution** — Calibration file contains floor-clamped recommendations. Safety floor in `routing_resolve_model` is a second defense.
5. **Fail-open everywhere** — Every interspect integration is guarded by plugin discovery and silent on failure.
6. **No intermediate scripts** — `interspect-verdict.sh` dropped; verdict recording is a library function call from the quality-gates call site.
7. **lib-verdict.sh stays pure** — No cross-plugin calls inside the verdict library. Fan-out happens at call sites.
8. **Atomic writes** — `tmp.$$ + mv` for calibration file to prevent torn reads.
9. **Fresh calibration reads** — `_routing_read_calibration()` reads the file per-call, not cached in `_ROUTING_CACHE_POPULATED`, to avoid stale data after reflect writes.

## Rollback Procedure

| Scenario | Fix |
|----------|-----|
| Shadow mode shows unexpected recommendations | Delete `.clavain/interspect/routing-calibration.json` |
| Enforce mode producing wrong routing | Unset `INTERSPECT_ROUTING_MODE` env AND/OR set `calibration.mode: shadow` in routing.yaml |
| Evidence pipeline writing to wrong DB | Verify `$CLAUDE_PROJECT_DIR` is set correctly; check `INTERSPECT_DEBUG=1` logs |
| Need to fully disable | Delete calibration file + revert lib-routing.sh changes. No DB migration needed — `verdict_outcome` rows are additive. |

## Verification

1. `bash -n interverse/interspect/hooks/interspect-evidence.sh` — syntax OK
2. `bash -n interverse/interspect/hooks/lib-interspect.sh` — syntax OK
3. `bash -n os/clavain/scripts/lib-routing.sh` — syntax OK
4. Dispatch an Agent subagent → check evidence DB for `agent_dispatch` event
5. Existing test suites pass (interspect bats, clavain bats, lib-routing tests)
6. `/interspect:calibrate` with synthetic data → produces valid JSON with floor-clamped recommendations

## Files Modified

| File | Change |
|------|--------|
| `interverse/interspect/hooks/lib-interspect.sh` | DB path priority fix, verdict recording function, scoring function, calibration writer (atomic), hook_id allowlist |
| `interverse/interspect/hooks/interspect-evidence.sh` | Debug logging for DB path resolution |
| `interverse/interspect/commands/calibrate.md` | New: calibrate command |
| `os/clavain/commands/quality-gates.md` | Wire verdict outcomes to interspect at call site |
| `os/clavain/scripts/lib-routing.sh` | Read routing calibration, shadow mode, model validation |
| `os/clavain/config/routing.yaml` | Add `calibration:` section, update resolution order comment |
| `os/clavain/commands/reflect.md` | Add calibration trigger via `_discover_interspect_plugin()` |
| `os/clavain/tests/shell/test_b3_calibration.bats` | New: 31 tests covering B3 calibration pipeline end-to-end |
