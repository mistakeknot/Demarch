# Correctness Review: Plugin Synergy Interop Implementation Plan
**Plan:** `/root/projects/Interverse/docs/plans/2026-02-20-plugin-synergy-interop.md`
**Reviewed:** 2026-02-20
**Reviewer:** Julik (Flux-drive Correctness Reviewer)

---

## Invariants Under Review

Before examining each finding, the invariants that must hold across all tasks:

1. **Atomic writes:** interband files must be written via temp+rename so readers never see a partial file.
2. **Session isolation:** interband files keyed on session_id must be per-session only. Pollution across sessions is a correctness violation.
3. **Hook idempotency:** PostToolUse hooks fire on every tool call. Any state they touch must survive concurrent or rapid repeated invocations without corruption.
4. **SQL injection barrier:** All dynamic values entering SQLite queries must be properly escaped, not relying on caller discipline.
5. **Reader resilience:** Any hook reading interband files must tolerate the file being empty, truncated (mid-write), or absent.
6. **Env var contract:** Hooks must only read env vars that Claude Code actually provides. Using phantom env vars causes silently wrong behavior (not an error — just a permanent no-op).
7. **Rate-limit atomicity:** Any "once per N minutes" guard must be atomic; two concurrent invocations must not both pass the guard.
8. **`source` re-entrancy:** `interband.sh` uses a load guard (`_INTERBAND_LOADED`). Re-sourcing from a hook that already loaded it is a no-op. This is safe only if the guard is correct.

---

## Finding 1 (CRITICAL): `CLAUDE_SESSION_ID` Does Not Exist as an Env Var

**Tasks affected:** Task 8 (interflux session-start).

**The bug:**

Task 8 proposes the following in `plugins/interflux/hooks/session-start.sh`:

```bash
_if_session_id="${CLAUDE_SESSION_ID:-}"
if [[ -n "$_if_session_id" && -z "${FLUX_BUDGET_REMAINING:-}" ]]; then
  _if_budget_file="${_if_interband_root}/interstat/budget/${_if_session_id}.json"
```

The plan assumes `CLAUDE_SESSION_ID` is an environment variable provided by Claude Code. It is not.

**Confirmed evidence:**

From `/root/projects/Interverse/services/intermute/docs/research/research-claude-code-hook-api.md`, line 438:

> `CLAUDE_SESSION_ID` -- **Does not exist as an env var.** The session ID is in the JSON stdin as `session_id`.

This is also consistent with how every other hook in the codebase reads it. `plugins/intercheck/hooks/context-monitor.sh` reads `SID=$(_ic_session_id "$INPUT")` from stdin JSON. `plugins/interlock/hooks/session-start.sh` reads `SESSION_ID=$(echo "$HOOK_INPUT" | jq -r '.session_id // empty')` from stdin JSON.

**Failure narrative:**

When the SessionStart hook fires, Claude Code passes a JSON blob on stdin. The hook reads the JSON into `HOOK_INPUT`, but the plan's code reads `CLAUDE_SESSION_ID` from the environment instead. That variable is unset. `_if_session_id` is empty. The `[[ -n "$_if_session_id" ]]` guard silently prevents the entire budget-read block from running. `FLUX_BUDGET_REMAINING` is never exported. The cost-aware review depth feature is dead on arrival, for every session, with no error or log of any kind.

The hook exits 0. The feature appears to work. It does not.

**Correct fix:**

The SessionStart hook must read the session_id from stdin JSON, the same way every other hook does. Also note that `FLUX_BUDGET_REMAINING` cannot survive across hook invocations as a raw env var unless it is exported via `CLAUDE_ENV_FILE` (which is only available at SessionStart). The corrected hook:

```bash
#!/usr/bin/env bash
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_INPUT=$(cat)   # must consume stdin before anything else

source "$HOOK_DIR/interbase-stub.sh"
ib_session_status

_if_interband_root="${INTERBAND_ROOT:-${HOME}/.interband}"
_if_session_id=$(printf '%s' "$HOOK_INPUT" | jq -r '.session_id // empty' 2>/dev/null)
if [[ -n "$_if_session_id" ]]; then
  _if_budget_file="${_if_interband_root}/interstat/budget/${_if_session_id}.json"
  if [[ -f "$_if_budget_file" ]]; then
    _if_pct=$(jq -r '.payload.pct_consumed // empty' "$_if_budget_file" 2>/dev/null)
    if [[ -n "$_if_pct" ]]; then
      _if_pct_int="${_if_pct%.*}"
      _if_budget="${INTERSTAT_TOKEN_BUDGET:-500000}"
      _if_remaining=$(awk "BEGIN{printf \"%d\", $_if_budget * (100 - $_if_pct) / 100}" 2>/dev/null || echo "")
      if [[ -n "$_if_remaining" && "$_if_remaining" -gt 0 && -n "${CLAUDE_ENV_FILE:-}" ]]; then
        echo "export FLUX_BUDGET_REMAINING=${_if_remaining}" >> "$CLAUDE_ENV_FILE"
      fi
    fi
  fi
fi
```

The export-via-CLAUDE_ENV_FILE approach is required if `FLUX_BUDGET_REMAINING` needs to be visible to subsequent hook invocations in the same session. Without it, the variable is local to the SessionStart hook process and lost immediately.

---

## Finding 2 (HIGH): SQL Injection via String Interpolation in Task 2

**Task affected:** Task 2 (interstat budget alert emission).

**The bug:**

The plan adds the following query to `post-task.sh`:

```bash
_is_total=$(sqlite3 "$DB_PATH" "PRAGMA busy_timeout=5000; SELECT COALESCE(SUM(result_length / 4), 0) FROM agent_runs WHERE session_id='$(printf "%s" "$session_id" | sed "s/'/''/g")';" 2>/dev/null || echo "0")
```

The escaping technique is `sed "s/'/''/g"` — replacing each single quote with two single quotes (SQLite standard literal-escaping). This is the same pattern already used in the existing INSERT block in `post-task.sh` (lines 53–58), so it is at least internally consistent.

However, the approach has two correctness problems.

**Problem A: `set -euo pipefail` and non-numeric awk output cause hook termination.**

The value `_is_pct` is produced by awk:

```bash
_is_pct=$(awk "BEGIN{printf \"%.1f\", ($_is_total / $_is_budget) * 100}" 2>/dev/null || echo "0")
_is_pct_int="${_is_pct%.*}"
if [[ "$_is_pct_int" -ge 50 ]]; then
```

If `_is_total` returns something unexpected (empty string from sqlite3 error), awk receives `( / )` which is a division-by-zero or parse error, emits nothing, and the `|| echo "0"` fallback sets `_is_pct` to `"0"`. That part is safe.

But if `_is_total` is `0` and `_is_budget` is also `0` (user set `INTERSTAT_TOKEN_BUDGET=0`), awk performs a division-by-zero and outputs `inf` or exits with error. The `|| echo "0"` covers the exit error, but `_is_pct` becomes `"0"`. `_is_pct_int` becomes `"0"`. The comparison `[[ "0" -ge 50 ]]` evaluates correctly to false. This path is safe, but fragile.

The real risk: if `_is_pct_int` ends up as a non-numeric string (e.g., `"inf"` from an awk implementation that does not error on division by zero but outputs `inf`), then `[[ "inf" -ge 50 ]]` causes a bash integer comparison error. Under `set -euo pipefail`, this exits the hook non-zero. Claude Code surfaces a hook failure to the user. The fix is a numeric guard:

```bash
[[ "${_is_pct_int:-0}" =~ ^[0-9]+$ ]] || _is_pct_int=0
```

**Problem B: The inline SELECT is inconsistent with the heredoc INSERT above it.**

The existing INSERT uses a heredoc (lines 42–61), which is the correct pattern for multi-value SQL with dynamic interpolation. The new SELECT uses a single-quoted inline string, which is harder to read and easier to misquote. Use a heredoc for consistency and safety:

```bash
_is_total=$(sqlite3 "$DB_PATH" <<SQL
PRAGMA busy_timeout=5000;
SELECT COALESCE(SUM(result_length / 4), 0)
FROM agent_runs
WHERE session_id='$(printf "%s" "$session_id" | sed "s/'/''/g")';
SQL
) || _is_total=0
```

The heredoc boundary prevents shell interpretation of the query body (except for the explicit `$(...)` expansion, which is intentional).

---

## Finding 3 (HIGH): `_ic_write_state` Is Not Atomic — Race Condition on State File

**Tasks affected:** Task 1 (intercheck interband write) and Task 10 (checkpoint trigger).

**The pre-existing bug:**

`_ic_write_state` in `/root/projects/Interverse/plugins/intercheck/lib/intercheck-lib.sh`:

```bash
_ic_write_state() {
  local sf="$1" state="$2"
  echo "$state" > "$sf"
}
```

This is a direct truncate-and-write, not atomic. Two concurrent PostToolUse invocations with the same session_id will race on this file.

**Race narrative (two concurrent tool calls):**

1. Hook A reads the state file: `calls=10, pressure=5.3`.
2. Hook B reads the state file at the same time: `calls=10, pressure=5.3`.
3. Hook A computes new state: `calls=11, pressure=6.0`. Begins `echo "$state" > "$sf"`.
4. Hook B computes new state: `calls=11, pressure=6.3`. Also begins `echo "$state" > "$sf"`.
5. The kernel interleaves the writes. The file ends up with either A's or B's state. Either way, one tool call's contribution is silently lost. In the pathological case — where the kernel flushes A's partial write, then B's partial write — the state file ends up as corrupted JSON, and the next hook invocation reads default state (call count resets to 0, pressure resets to 0).

The plan does not introduce this bug — it already exists — but the plan's additions in Task 1 and Task 10 both depend on the state written by `_ic_write_state` being correct. If the state is wrong, the interband signal publishes a wrong pressure level, and the checkpoint trigger fires based on wrong data.

**Task 10 checkpoint rate-limit has its own race:**

```bash
if [[ -d "$_ic_intermem_dir" ]] && [[ ! -f "$_ic_last_checkpoint" || $(( NOW - $(stat -c %Y "$_ic_last_checkpoint" 2>/dev/null || echo 0) )) -gt 900 ]]; then
  touch "$_ic_last_checkpoint" 2>/dev/null || true
```

This is check-then-act: check file absent or old, then write. Two concurrent invocations both at orange level both pass the check (file absent) and both `touch` the file, emitting two interband checkpoint signals within the same window. The rate-limit invariant is violated.

**Recommended fixes:**

For `_ic_write_state`, use atomic write:

```bash
_ic_write_state() {
  local sf="$1" state="$2"
  local tmp
  tmp=$(mktemp "${sf}.XXXXXX") || return 1
  printf '%s\n' "$state" > "$tmp" && mv -f "$tmp" "$sf"
}
```

This does not eliminate the read-modify-write race on the counter itself (only a lock would), but it eliminates partial-write JSON corruption. For a monitoring signal where occasional lost increments are acceptable, this is the appropriate minimum fix.

For the checkpoint rate-limit, use `mkdir` as an atomic lock (POSIX guarantee on local filesystems):

```bash
_ic_cp_lock="/tmp/intercheck-cp-lock-${SID}"
if mkdir "$_ic_cp_lock" 2>/dev/null; then
  touch "$_ic_last_checkpoint" 2>/dev/null || true
  rmdir "$_ic_cp_lock" 2>/dev/null || true
  # ... emit signal
fi
```

If the directory already exists, the second invocation fails silently and skips emission.

---

## Finding 4 (HIGH): `source "$_ic_interband_lib"` Load Guard Conflict — Wrong Version Loaded Silently

**Tasks affected:** Task 1 (intercheck), Task 2 (interstat).

**The bug:**

The plan sources `interband.sh` inside PostToolUse hooks using a path-discovery loop. `interband.sh` has a load guard:

```bash
[[ -n "${_INTERBAND_LOADED:-}" ]] && return 0
_INTERBAND_LOADED=1
```

This prevents double-loading. It is correct when there is one canonical source path. The problem arises when two hooks in the same shell process source `interband.sh` from different paths.

**Concrete failure scenario:**

1. `syntax-check.sh` fires first (PostToolUse on a Write call) and discovers the installed version of interband at `~/.local/share/interband/lib/interband.sh` (version N from the marketplace). It sources it. `_INTERBAND_LOADED=1` is set.
2. `context-monitor.sh` fires second and discovers the dev-tree version at `${SCRIPT_DIR}/../../../infra/interband/lib/interband.sh` (version N+1, with the new `intercheck:context_pressure` case in `interband_validate_payload`). It tries to source it. The guard fires. The source is a no-op. The loaded functions are still from version N.
3. `interband_validate_payload` is called for type `context_pressure`. The installed version N does not have that case. The wildcard catch-all in the `case` statement passes (the plan adds validation, so unknown types pass forward-compat). The validate function returns 0. The signal is written.

Wait — that means the signal IS written? Let me recheck: the existing `interband_validate_payload` function (seen in `infra/interband/lib/interband.sh`) uses a `case` statement with known types explicitly listed. Unknown types fall through with no explicit return 1. The function returns 0 (the default after a case with no match). So in this scenario the forward-compat actually holds and the write succeeds.

**But the scenario reverses dangerously in the opposite direction:** If the dev-tree version is loaded first (because `context-monitor.sh` fires before `syntax-check.sh`), and a consumer elsewhere loads the installed version, the guard prevents the installed version from loading. The installed version's functions are replaced by the dev-tree versions for that process. This is acceptable in dev, but it becomes a silent version mismatch in production if the installed and source versions diverge.

**The real concern:** The discovery order (dev-tree path checked first) means that on a developer machine, hooks always load the dev-tree version of interband, even in production plugin testing contexts. Any breakage in the dev-tree version silently affects all hooks that source interband, not just the ones being developed. A syntax error in the dev-tree interband.sh causes `source` to fail, and under `set -euo pipefail`, the hook exits non-zero, causing a hook error visible to the user.

**Recommended fix:**

Add `|| true` to the source call in both Task 1 and Task 2:

```bash
source "$_ic_interband_lib" || true
```

This converts a source failure into silent degradation rather than hook crash. Additionally, document in the plan that the discovery order (dev-tree before installed) is intentional for development only, and that production deployments use only the installed path.

---

## Finding 5 (HIGH): `bd list --json --quiet` Dedup via grep — Collision-Prone and Unfiltered

**Task affected:** Task 9 (verdict-to-bead bridge).

**The plan adds:**

```bash
existing=$(bd list --json --quiet 2>/dev/null | jq -r ".[].title" 2>/dev/null | grep -Fc "${summary:0:30}" || echo "0")
[[ "$existing" -eq 0 ]] || continue
```

**Correctness problems:**

**Problem A: 30-character prefix collisions are common in review findings.**

"Missing error handling in function X" and "Missing error handling in function Y" share the same first 30 characters. The second bead is silently dropped. In a typical multi-agent review of a 10-file Go service, at least 2–3 findings will share a prefix this short.

**Problem B: No status filter — closed beads block new ones.**

`bd list --json --quiet` returns all beads regardless of status. A bead closed six months ago with a matching title prefix permanently blocks creation of a new, valid, current finding. The dedup should only consider open or in-progress beads.

**Problem C: Scale performance.**

`bd list` without filters returns the full bead list. On a project with thousands of beads, this is slow (potentially hundreds of milliseconds per call). The plan calls it once per verdict file in a loop. Ten verdict files means ten serial full-table scans of the bead database, blocking hook completion. Under `set -euo pipefail`, if `bd list` exits non-zero (lock timeout, DB error), the `|| echo "0"` fallback saves the hook but the dedup is disabled for that invocation — and auto-bead may create duplicates.

**Problem D: `grep -Fc` semantics are fragile.**

`grep -Fc` counts lines matching the fixed string. `jq -r ".[].title"` outputs one title per line. The count is "1 if any bead matches", which happens to be the correct behavior here — but only because jq's output is one-line-per-entry. If a title contains a literal newline (possible in some bead storage implementations), jq may output two lines for one bead, making `grep -c` return 2 when one bead matches. Then `[[ 2 -eq 0 ]]` is false, the check passes — correct outcome, wrong semantics. The code works by accident of data format.

**Recommended fix:**

Single jq invocation with status filter:

```bash
existing=$(bd list --status=open --json --quiet 2>/dev/null \
  | jq -r --arg prefix "${summary:0:50}" \
    '[.[] | select(.title | startswith($prefix) or contains($prefix))] | length' \
  2>/dev/null || echo "0")
```

Use a longer prefix (50 characters) to reduce collision risk, and filter to open status only. If `bd` does not support `--status=open` filtering, apply it in jq: `select(.status == "open" or .status == "in_progress")`. This is a single jq invocation replacing the jq-pipe-grep chain, and it does not accidentally match on closed beads.

---

## Finding 6 (MEDIUM): Task 10 — `python3` Guard Protects Code That Uses No Python

**Task affected:** Task 10 (smart checkpoint triggers).

**The bug:**

```bash
if command -v python3 >/dev/null 2>&1; then
  _ic_intermem_dir="$(pwd)/.intermem"
  _ic_last_checkpoint="/tmp/intercheck-intermem-checkpoint-${SID}"
  if [[ -d "$_ic_intermem_dir" ]] && [[ ! -f "$_ic_last_checkpoint" || $(( NOW - $(stat -c %Y "$_ic_last_checkpoint" 2>/dev/null || echo 0) )) -gt 900 ]]; then
    touch "$_ic_last_checkpoint" 2>/dev/null || true
    ...
  fi
fi
```

The entire checkpoint block is gated on `command -v python3`. The code inside uses only bash builtins, `stat`, `touch`, `jq`, and `interband_write` — no Python at all. On any environment where Python 3 is absent (minimal containers, stripped CI images), the checkpoint signal is permanently disabled with no error or explanation.

This appears to be a copy-paste error from a draft that planned to call a Python helper for the intermem check.

**Fix:** Remove the `python3` guard entirely. The correct guard is the one already inside the block: `[[ -d "$_ic_intermem_dir" ]]`.

---

## Finding 7 (MEDIUM): Task 10 — Checkpoint Trigger Has Undocumented Dependency on Task 1

**Task affected:** Task 10 (smart checkpoint triggers).

**The bug:**

Task 10's code inside the `orange` case references `_ic_interband_lib`:

```bash
if [[ -n "${_ic_interband_lib:-}" ]]; then
  ...interband_path...
  ...interband_write...
fi
```

This variable is defined and the library is sourced in the interband discovery block added by Task 1. Task 10 silently does nothing if Task 1 is not applied. An implementer who applies Task 10 without Task 1 gets a permanently inert checkpoint trigger with no error.

The plan's task ordering (Tasks 1–10) implies sequential application, but the dependency is not documented. If tasks are cherry-picked or applied out of order during incremental development, the silent no-op is a trap.

**Fix:** Either include a self-contained interband discovery block in Task 10 (duplicating Task 1's discovery, acceptable given the scope), or add an explicit warning in the plan: "Task 10 requires Task 1's interband library sourcing to be applied to context-monitor.sh first."

---

## Finding 8 (MEDIUM): Task 2 — `source "$_is_interband_lib"` Has No Error Guard Under `set -euo pipefail`

**Task affected:** Task 2 (interstat budget signal).

**The bug:**

`post-task.sh` runs under `set -euo pipefail`. The plan adds:

```bash
if [[ -n "$_is_interband_lib" ]]; then
  source "$_is_interband_lib"
  ...
fi
```

If `source` fails (the file exists when checked with `-f` but becomes unreadable or contains a syntax error by the time `source` runs), bash exits non-zero. Under `set -e`, this terminates the hook process. Claude Code surfaces a hook error to the user, and the already-written SQLite metric row is orphaned (the write succeeded; only the interband signal is lost).

The `2>/dev/null || true` defensive pattern used on `interband_write` is correct. The `source` call needs the same treatment:

```bash
source "$_is_interband_lib" || true
```

This converts a broken library source into silent degradation (no interband signal) rather than a user-visible hook error.

---

## Finding 9 (LOW): Task 1 — `_ic_interband_root` Variable Is Dead Code

**Task affected:** Task 1 (intercheck interband write).

**The plan defines:**

```bash
_ic_interband_root="${INTERBAND_ROOT:-${HOME}/.interband}"
```

But the interband path is obtained via `interband_path "intercheck" "pressure" "$SID"`, which calls `interband_root()` internally. `_ic_interband_root` is never referenced. This is dead code. It confuses readers into thinking the variable feeds into the path computation, and it will accumulate as dead weight if the hook grows.

**Fix:** Remove the line.

---

## Finding 10 (LOW): Task 3 — Non-Numeric `_il_budget_int` Causes Arithmetic Warning

**Task affected:** Task 3 (interline statusline enrichment).

**The plan adds:**

```bash
_il_budget_int="${_il_budget_pct%.*}"
if [ "${_il_budget_int:-0}" -ge 80 ]; then
```

If `_il_budget_pct` is the string `null` (leaked from a malformed payload where jq returns `"null"` instead of empty), `${_il_budget_pct%.*}` strips nothing (no `.` in `null`), yielding `_il_budget_int="null"`. Then `[ "null" -ge 80 ]` causes bash to emit `bash: [: null: integer expression expected` to stderr. The statusline script runs as `#!/bin/bash` without `set -e`, so execution continues, the comparison evaluates to false, and no label is shown — which is the correct degraded behavior. But the stderr warning appears on the user's terminal as a garbled status line artifact.

**Fix:**

```bash
[[ "${_il_budget_int}" =~ ^[0-9]+$ ]] || _il_budget_int=0
```

Insert this after the `_il_budget_int` assignment, before the comparison.

---

## Summary Table

| # | Finding | Task | Severity | Invariant Violated |
|---|---------|------|----------|-------------------|
| 1 | `CLAUDE_SESSION_ID` is not an env var — feature permanently disabled | Task 8 | CRITICAL | Env var contract |
| 2 | SQL `set -e` risk from non-numeric awk output; inconsistent pattern vs INSERT | Task 2 | HIGH | Hook idempotency |
| 3 | `_ic_write_state` not atomic; checkpoint rate-limit check-then-act racy | Task 1, 10 | HIGH | Atomic writes; Rate-limit atomicity |
| 4 | `source` of interband.sh may silently load wrong version due to load guard | Task 1, 2 | HIGH | Hook idempotency |
| 5 | `bd list` dedup via grep — short prefix collisions, no status filter, scale risk | Task 9 | HIGH | Session isolation |
| 6 | `python3` guard wraps code that uses no Python — disables feature on minimal envs | Task 10 | MEDIUM | — |
| 7 | Task 10 checkpoint trigger silently inert if Task 1 not applied | Task 10 | MEDIUM | — |
| 8 | `source "$_is_interband_lib"` has no `|| true` under `set -euo pipefail` | Task 2 | MEDIUM | Hook idempotency |
| 9 | Dead variable `_ic_interband_root` in Task 1 | Task 1 | LOW | — |
| 10 | `_il_budget_int` non-numeric string causes arithmetic warning on stderr | Task 3 | LOW | Reader resilience |

---

## Priority Order for Implementation

1. **Fix Finding 1 before implementing Task 8.** The feature is completely inert without reading session_id from stdin JSON. Also decide whether `FLUX_BUDGET_REMAINING` is exported via `CLAUDE_ENV_FILE` or passed via interband for subsequent hooks.

2. **Fix Finding 5 before enabling auto-bead creation in Task 9.** The `bd list` dedup as written will silently suppress valid beads when summaries share a 30-character prefix, and will permanently block re-creation of findings that were previously closed.

3. **Fix Finding 2 (numeric guard on `_is_pct_int`) before merging Task 2.** A hook exit under `set -euo pipefail` corrupts nothing, but it surfaces an error to the user and disrupts the session.

4. **Add `|| true` to `source` calls (Finding 4, Finding 8)** as a one-line change in both Task 1 and Task 2 before committing either.

5. **Remove the `python3` guard (Finding 6)** — trivial one-line fix that unblocks the checkpoint trigger on minimal environments.

6. **Document or eliminate the Task 10 → Task 1 dependency (Finding 7).**

7. **Low-severity fixes (Findings 9, 10)** can be batched with the first commit that touches their respective files.

The state file atomicity issue (Finding 3) is a pre-existing bug in intercheck-lib.sh. The plan does not introduce it, but Task 1 and Task 10 amplify its impact by publishing signals based on potentially corrupted state. Filing it as a separate bead is appropriate; fixing it before landing Task 1 is ideal.
