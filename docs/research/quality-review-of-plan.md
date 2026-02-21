# Quality Review: Plugin Synergy Interop Implementation Plan

**Reviewed:** 2026-02-20
**Plan file:** `docs/plans/2026-02-20-plugin-synergy-interop.md`
**Scope:** Bash conventions, error handling, interband sourcing, hook timeout budgets, shell quoting, test approach.

---

## Summary

The plan is architecturally coherent and the interband write pattern is correct at a high level. However there are six concrete issues requiring fixes before implementation: one safety-critical SQL injection risk, one incomplete interband sourcing pattern, two naming inconsistencies, one silent threshold mismatch, and test coverage that would miss a broken `interband_write` call. One timeout concern is a real risk at the orange hook. Issues are ordered by severity.

---

## Finding 1 — CRITICAL: SQL Injection in Task 2 (`post-task.sh`)

**Location:** Task 2, Step 2 — `_is_total` query

```bash
# Plan code (unsafe):
_is_total=$(sqlite3 "$DB_PATH" "PRAGMA busy_timeout=5000; SELECT COALESCE(SUM(result_length / 4), 0) FROM agent_runs WHERE session_id='$(printf "%s" "$session_id" | sed "s/'/''/g")';" 2>/dev/null || echo "0")
```

The existing `post-task.sh` (lines 42–61) passes SQL to sqlite3 via a heredoc, with each value escaped via `sed "s/'/''/g"`. The plan departs from this pattern by constructing the SQL string inline with command substitution inside double quotes. Even with the sed escape applied, embedding shell expansions inside a double-quoted SQL string argument is fragile and harder to audit.

**Fix:** Use the heredoc pattern that already exists in `post-task.sh`:

```bash
_is_total=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
PRAGMA busy_timeout=5000;
SELECT COALESCE(SUM(result_length / 4), 0)
FROM agent_runs
WHERE session_id='$(printf "%s" "$session_id" | sed "s/'/''/g")';
SQL
)
```

This is still string-interpolated (sqlite3 has no bind parameters in heredoc mode), but it matches the project's established escaping pattern and is auditable by grep. The SQL is also more readable without the inline quoting gymnastics.

---

## Finding 2 — HIGH: Interband Sourcing Pattern Is Incomplete vs. Established Convention

**Location:** Task 1, Step 3 (`context-monitor.sh`); Task 2, Step 2 (`post-task.sh`)

The plan's candidate search loop in Task 1:

```bash
for _ic_lib_candidate in \
    "${SCRIPT_DIR}/../../../infra/interband/lib/interband.sh" \
    "${HOME}/.local/share/interband/lib/interband.sh"; do
  [[ -f "$_ic_lib_candidate" ]] && _ic_interband_lib="$_ic_lib_candidate" && break
done
```

The established pattern from `plugins/interphase/hooks/lib-gates.sh` (`_gate_load_interband`, lines 27–43) has five candidates and a different ordering:

```bash
for candidate in \
    "${INTERBAND_LIB:-}" \
    "${_GATES_SCRIPT_DIR}/../../../infra/interband/lib/interband.sh" \
    "${_GATES_SCRIPT_DIR}/../../../interband/lib/interband.sh" \
    "${repo_root}/../interband/lib/interband.sh" \
    "${HOME}/.local/share/interband/lib/interband.sh"
```

Three specific gaps in the plan's version:

1. **`${INTERBAND_LIB:-}` is absent.** This is the first candidate in the established pattern and allows a test harness or caller to inject a custom path. Omitting it makes the new code untestable in isolation and diverges from every other interband consumer in the codebase.

2. **Only one relative path is tried.** The interphase pattern tries both `infra/interband` and bare `interband` paths, covering both monorepo and standalone install layouts. The plan only covers the monorepo path.

3. **`${repo_root}` via `git rev-parse` is absent.** The fourth candidate in the established pattern provides a cross-directory fallback.

In Task 2 (`post-task.sh`), the sourcing uses a `cd && pwd` trick to canonicalize the path — that is correct — but the same three missing candidates apply.

**Fix:** Adopt the five-candidate pattern from `lib-gates.sh` verbatim in both Task 1 and Task 2. Add `${INTERBAND_LIB:-}` as the first candidate.

---

## Finding 3 — MEDIUM: `_ic_` Prefix Collision with Intercheck Library Namespace

**Location:** Task 1, Step 3 (`context-monitor.sh`)

The existing `context-monitor.sh` sources `intercheck-lib.sh`, which defines the public functions `_ic_session_id`, `_ic_state_file`, `_ic_read_state`, and `_ic_write_state`. The plan introduces new script-local temporaries that reuse the same `_ic_` prefix:

```bash
_ic_interband_root="..."
_ic_interband_lib=""
_ic_lib_candidate
_ic_pressure_level
_ic_ib_payload
_ic_ib_file
```

Because these are top-level script variables (not inside a function), they share the same namespace as the `_ic_*` library functions. A future addition to `intercheck-lib.sh` named `_ic_ib_file` or `_ic_pressure_level` would silently overwrite the plan's variables.

The comparison point: `lib-gates.sh` uses `_gate_` for its own internal helpers and keeps local variables inside function scope. Because the new code is not inside a function, a more specific prefix is necessary.

**Fix:** Rename the interband-specific temporaries within `context-monitor.sh` to `_icm_` (context-monitor locals) or `_ib_` (interband-specific group):

```bash
_icm_ib_root=...
_icm_ib_lib=""
_icm_ib_candidate
_icm_pressure_level
_icm_ib_payload
_icm_ib_file
```

Tasks 2, 3, and 8 use `_is_`, `_il_`, and `_if_` respectively — these match established codebase prefixes (`_il_` is used throughout `statusline.sh`) and do not collide with any existing library namespace, so no fix is needed for those tasks.

---

## Finding 4 — MEDIUM: Task 2 Threshold Crossing Comment Does Not Match Implementation

**Location:** Task 2, Step 2 (`post-task.sh`)

```bash
# Only emit at threshold crossings: 50%, 80%, 95%
if [[ "$_is_pct_int" -ge 50 ]]; then
  _is_ib_payload=$(jq -n -c ...)
  ...
  interband_write ...
fi
```

The comment says "only emit at threshold crossings" but the implementation emits (overwrites the interband file) on every PostToolUse:Task event where the session is above 50%. There is no stored last-emitted tier — the file is rewritten unconditionally on every qualifying event.

This matters because PostToolUse:Task fires on every agent Task call, which can be frequent. The plan's own efficiency rationale is undermined.

**Fix:** Either remove the "threshold crossing" comment to accurately describe the actual behavior (emit every event above 50%), or add last-threshold tracking. A lightweight approach: store `_is_last_tier` in a `/tmp` file keyed on `$session_id` and only write to interband when the bucket (50/80/95) changes:

```bash
_is_tier="low"
[[ "$_is_pct_int" -ge 95 ]] && _is_tier="critical"
[[ "$_is_pct_int" -ge 80 && "$_is_tier" != "critical" ]] && _is_tier="high"
[[ "$_is_pct_int" -ge 50 && "$_is_tier" == "low" ]] && _is_tier="medium"

_is_tier_file="/tmp/interstat-budget-tier-${session_id}"
_is_last_tier=$(cat "$_is_tier_file" 2>/dev/null || echo "")
if [[ "$_is_tier" != "$_is_last_tier" ]]; then
    printf '%s' "$_is_tier" > "$_is_tier_file" 2>/dev/null || true
    interband_write ...
fi
```

---

## Finding 5 — MEDIUM: Task 8 Reads Interband Envelope Without Validation

**Location:** Task 8, Step 1 (`interflux/hooks/session-start.sh`)

```bash
_if_pct=$(jq -r '.payload.pct_consumed // empty' "$_if_budget_file" 2>/dev/null)
```

This is a raw jq read that bypasses `interband_validate_envelope_file`. The established pattern for reading interband data is either `_il_interband_payload_field` (in `statusline.sh`) or `interband_read_payload` (in `interband.sh`), both of which first call `interband_validate_envelope_file` to verify the version prefix starts with `"1."` and all required fields are present.

A corrupted, truncated, or stale file from a different schema version would silently yield an empty or wrong `_if_pct`. Because this feeds a computed `FLUX_BUDGET_REMAINING` export that influences agent dispatch behavior, silent corruption is a real risk.

**Fix:** Use `interband_read_payload` after sourcing `interband.sh`, then extract the field from the validated payload:

```bash
source "$_if_interband_lib"
_if_payload=$(interband_read_payload "$_if_budget_file" 2>/dev/null) || _if_payload=""
if [[ -n "$_if_payload" ]]; then
    _if_pct=$(printf '%s' "$_if_payload" | jq -r '.pct_consumed // empty' 2>/dev/null)
    ...
fi
```

This requires sourcing `interband.sh` first, which Task 8 does not currently do. The plan should add the same `for _if_lib_candidate in ...` sourcing block used in Tasks 1 and 2 (and fixed per Finding 2).

---

## Finding 6 — MEDIUM: `INTERSTAT_TOKEN_BUDGET` Not Guarded for Non-Integer Values

**Location:** Task 2, Step 2 (`post-task.sh`)

```bash
_is_budget="${INTERSTAT_TOKEN_BUDGET:-0}"
if [[ "$_is_budget" -gt 0 && "$_is_total" -gt 0 ]]; then
```

`[[ "$_is_budget" -gt 0 ]]` performs integer comparison. `post-task.sh` opens with `set -euo pipefail`. If `INTERSTAT_TOKEN_BUDGET` is set to a non-integer value (e.g., `"500k"`, `""` with no default taking effect, or a typo), Bash throws `integer expression expected` and the hook exits non-zero, failing silently (PostToolUse hooks that exit non-zero are logged but not fatal).

The same guard issue applies to `_is_total` if `sqlite3` outputs non-numeric content (the `|| echo "0"` fallback handles the failure case, but not a partially-numeric output).

**Fix:**

```bash
_is_budget="${INTERSTAT_TOKEN_BUDGET:-0}"
[[ "$_is_budget" =~ ^[0-9]+$ ]] || _is_budget=0
_is_total=...
[[ "$_is_total" =~ ^[0-9]+$ ]] || _is_total=0
```

---

## Finding 7 — LOW: Interband Prune Not Called After Write (Inconsistency with `lib-gates.sh`)

**Location:** Tasks 1 and 10 (`context-monitor.sh`)

`lib-gates.sh` `_gate_update_statusline` (lines 504–513) calls `interband_prune_channel` after every `interband_write`. The plan's new writes to `intercheck:pressure` and `intercheck:checkpoint` channels never call `interband_prune_channel`. For a 3600s retention and 64-file cap, the channel will accumulate up to 64 files before natural expiry — across many sessions this can grow. The cap prevents unbounded growth, but inconsistency with the established pattern will confuse future maintainers.

**Fix (minor):** Add after each `interband_write` call:

```bash
interband_prune_channel "intercheck" "pressure" 2>/dev/null || true
```

The prune is throttled internally by `INTERBAND_PRUNE_INTERVAL_SECS` (default 300s) so calling it on every PostToolUse event is cheap.

---

## Finding 8 — LOW: Cumulative jq Calls May Approach Timeout Budget at Orange Level (Task 10)

**Location:** Task 10, Step 1 (`context-monitor.sh` orange case)

The base `context-monitor.sh` already calls jq 7–8 times per PostToolUse event (state read, threshold arithmetic, output generation). Task 1 adds 2 more jq calls (payload build, plus `interband_write` calls jq internally twice: validate + write). Task 10 adds a further 2 jq calls at the orange threshold (checkpoint payload build + `interband_write`).

At orange level, the hook now has approximately 13–14 jq invocations per PostToolUse event. Each jq invocation on a loaded system takes 30–80ms. At the high end, this approaches 1.1 seconds on top of other hook overhead. The current timeout in intercheck's hooks.json was not shown in the source files reviewed — if it is 5s, there is headroom; if it is 2s, this is a real risk.

**Recommendation:** Confirm the timeout value in intercheck's hooks.json. If headroom is tight, consolidate the pressure signal write and checkpoint signal write into a single code block that decides at the end whether one or both signals need emitting, rather than two independent code paths each calling `interband_write`. Also consider making the checkpoint signal write async (`&`) with an immediate `disown`, since the checkpoint is advisory and the orange output does not depend on it succeeding synchronously.

---

## Finding 9 — LOW: Task 9 `verdict_auto_create_beads` — jq Pipeline Not Guarded Against Non-Array

**Location:** Task 9, Step 2 (`lib-verdict.sh`)

```bash
existing=$(bd list --json --quiet 2>/dev/null | jq -r ".[].title" 2>/dev/null | grep -Fc "${summary:0:30}" || echo "0")
```

`jq -r ".[].title"` will emit a type error and exit non-zero if `bd list --json` outputs a non-array (e.g., `null`, an error object, or empty input). The `2>/dev/null` suppresses the error message, and `grep -Fc ...` then receives no input and returns 0 (no matches), making `existing=0`. Because the code then proceeds to create a bead when `existing -eq 0`, a `bd list` failure silently looks like "no existing bead," potentially creating duplicates.

**Fix:**

```bash
existing=$(bd list --json --quiet 2>/dev/null | jq -r 'if type == "array" then .[].title else empty end' 2>/dev/null | grep -Fc "${summary:0:30}" || echo "0")
```

The `if type == "array"` guard causes jq to emit nothing (not an error) when the input is not an array.

---

## Finding 10 — LOW: Session-Start Hook Stubs Missing `set -euo pipefail` (Tasks 4, 5, 6)

**Location:** `plugins/interline/hooks/session-start.sh`, `plugins/intersynth/hooks/session-start.sh`, and the four plugins in Task 6

```bash
#!/usr/bin/env bash
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOK_DIR/interbase-stub.sh"
ib_session_status
```

Every existing hook in the codebase inspected during this review opens with `set -euo pipefail`: `interlock/hooks/session-start.sh` line 2, `interstat/hooks/post-task.sh` line 2, `intercheck/hooks/context-monitor.sh` line 10. The plan's session-start stubs for Tasks 4, 5, and 6 all omit strict mode.

**Fix:** Add `set -euo pipefail` immediately after the shebang in all six session-start stubs. Since `interbase-stub.sh` is designed to be fail-open (its internal commands use `|| true`), enabling strict mode in the caller is safe and consistent.

---

## Finding 11 — LOW: Test Approach Does Not Validate Interband Envelope Structure

**Location:** Tasks 1, 2, 3, 8, 9 — "Verify" steps

The plan's verification steps are manual `echo '...' | bash ...` invocations that check file existence:

```bash
# Task 1 Step 4:
# Check ~/.interband/intercheck/pressure/test-123.json was created.
```

A broken `interband_validate_payload` case (e.g., a typo in the jq expression that causes it to always return 1) would cause `interband_write` to return 1 silently, and the file would not be written. The verification step would then say "file does not exist" — which does catch this case. Good.

However, if `interband_write` succeeds but the payload is malformed (e.g., the jq expression in `interband_validate_payload` passes but with wrong structure due to a new bug), the file is created but contains a wrong schema. The plan's test only checks file existence, not envelope validity.

**Fix:** Add an envelope validation step to each task's verify block:

```bash
# Task 1 verify addition:
jq -e '
    (.version | startswith("1.")) and
    .namespace == "intercheck" and
    .type == "context_pressure" and
    (.payload.level | type == "string") and
    (.payload.pressure | type == "number") and
    (.payload.est_tokens | type == "number")
' ~/.interband/intercheck/pressure/test-123.json && echo "Envelope valid" || echo "FAIL: invalid envelope"
```

This validates the round-trip through `interband_validate_payload` and `interband_write`, not just file creation.

---

## Finding 12 — LOW: Task 6 Multi-Line `for` Loop in Commit Step (Operational Hygiene)

**Location:** Task 6, Step 6

```bash
for p in intermem intertest internext tool-time; do
  git -C "plugins/$p" add hooks/interbase-stub.sh hooks/session-start.sh .claude-plugin/integration.json
  [ -f "plugins/$p/hooks/hooks.json" ] && git -C "plugins/$p" add hooks/hooks.json
  git -C "plugins/$p" commit -m "feat($p): adopt interbase SDK with companion nudges"
done
```

Per the project's `CLAUDE.md` global instructions, multi-line `for`/`while` loops in Bash tool calls cause each line to become a separate invalid permission entry in `.claude/settings.local.json`. When the implementer runs this step, `do`, `done`, and the `git -C ...` lines become individual entries.

**Fix:** Collapse to a one-liner:

```bash
for p in intermem intertest internext tool-time; do git -C "plugins/$p" add hooks/interbase-stub.sh hooks/session-start.sh .claude-plugin/integration.json && git -C "plugins/$p" commit -m "feat($p): adopt interbase SDK with companion nudges"; done
```

The same applies to the Step 5 `chmod`/`bash` loop.

---

## Finding 13 — NOTE: `stat -c %Y` Is Linux-Only (Consistent with Codebase)

**Location:** Task 10, Step 1 (`context-monitor.sh`)

```bash
$(( NOW - $(stat -c %Y "$_ic_last_checkpoint" 2>/dev/null || echo 0) ))
```

`stat -c %Y` is GNU coreutils. `interband.sh` also uses `stat -c %Y` (lines 125 and 135), so this is consistent with the existing codebase posture. The project targets Linux only (confirmed by server environment). No change required — note for any future portability work.

---

## Summary Table

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | CRITICAL | Task 2, post-task.sh | Inline shell expansion in SQL string; use heredoc pattern from existing code |
| 2 | HIGH | Tasks 1, 2 | Interband sourcing missing `${INTERBAND_LIB:-}` first candidate and 3 fallbacks |
| 3 | MEDIUM | Task 1, context-monitor.sh | `_ic_` prefix collides with intercheck library namespace |
| 4 | MEDIUM | Task 2, post-task.sh | Threshold crossing comment does not match implementation (writes every event above 50%) |
| 5 | MEDIUM | Task 8, interflux/session-start.sh | Raw jq read bypasses `interband_validate_envelope_file` |
| 6 | MEDIUM | Task 2, post-task.sh | `INTERSTAT_TOKEN_BUDGET` not guarded against non-integer values |
| 7 | LOW | Tasks 1, 10, context-monitor.sh | `interband_prune_channel` not called after write (inconsistency with lib-gates.sh) |
| 8 | LOW | Task 10, context-monitor.sh | Cumulative jq calls at orange level may approach timeout budget |
| 9 | LOW | Task 9, lib-verdict.sh | `jq -r ".[].title"` not guarded against non-array bd output |
| 10 | LOW | Tasks 4, 5, 6, session-start stubs | Missing `set -euo pipefail` in all six new session-start hooks |
| 11 | LOW | All tasks, verify steps | Manual tests check file existence but not envelope structure validity |
| 12 | LOW | Task 6, Step 5/6 | Multi-line for loops will create invalid settings.local.json permission entries |
| 13 | NOTE | Task 10 | `stat -c %Y` is Linux-only (consistent with codebase, note for portability) |

## Priority Order for Fixes Before Implementation

1. **(CRITICAL)** Replace inline SQL string construction in Task 2 with the heredoc pattern from the existing `post-task.sh`.
2. **(HIGH)** Add `${INTERBAND_LIB:-}` as the first candidate in both Task 1 and Task 2 interband sourcing loops, and add the three missing fallback paths from `lib-gates.sh`.
3. **(MEDIUM)** Rename `_ic_` temporaries in Task 1 to `_icm_` to avoid library namespace collision.
4. **(MEDIUM)** Fix Task 2 threshold crossing: either update the comment or add tier-change tracking.
5. **(MEDIUM)** Task 8: source `interband.sh` and use `interband_read_payload` instead of raw jq.
6. **(MEDIUM)** Add `[[ "$_is_budget" =~ ^[0-9]+$ ]] || _is_budget=0` guard in Task 2.
7. **(LOW)** Add `set -euo pipefail` to all six session-start stubs (Tasks 4, 5, 6).
8. **(LOW)** Collapse multi-line for loops in Task 6 Steps 5 and 6 to one-liners.
9. **(LOW)** Add envelope validation to each task's verify block.
10. **(LOW)** Add `interband_prune_channel` calls after each `interband_write` in Tasks 1 and 10.
