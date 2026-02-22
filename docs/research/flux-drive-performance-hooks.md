# Hook Performance Review — Interverse Monorepo

**Date:** 2026-02-20
**Scope:** All Claude Code hook bindings across 11 plugins (os/clavain + 10 companion plugins)
**Reviewer:** fd-performance (Flux-drive Performance Reviewer)

---

## Executive Summary

The hook ecosystem has grown to 37+ bindings across 11 plugins. For an interactive coding session, the following overhead is incurred on every tool call:

- **Every tool call (Pre + Post):** tool-time hook fires twice (`*` matcher, both Pre and PostToolUse). Each invocation: spawn bash, invoke jq twice, read/write a seq file, write a JSONL line. Estimated wall time: 30-60ms per tool call.
- **Every PostToolUse:** intercheck/context-monitor fires (no matcher = wildcard). Invokes `jq` three times, and `python3` twice for arithmetic, plus SQLite-like state file read/write. Estimated: 40-80ms per tool call.
- **Every Edit/Write:** four additional hooks fire (clavain: interserve-audit + catalog-reminder; intercheck: syntax-check + auto-format). For syntax-check this includes spawning `python3` or `go vet`. Auto-format may spawn `ruff`, `shfmt`, or `gofmt`. tldr-swinton: post-read-extract fires on every Read.

At a moderate session pace of 200 tool calls, the per-call overhead from these "always-on" hooks alone costs roughly 14-28 seconds of latency distributed across the session — not counting the heavy SessionStart path.

---

## 1. Always-On Hooks With No or Wildcard Matchers

### Finding 1.1: tool-time hook fires on EVERY Pre and PostToolUse (CRITICAL)

**File:** `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json`
**Hooks.json excerpt:**
```json
"PreToolUse":  [{ "matcher": "*", "hooks": [{ "command": "bash \"$CLAUDE_PLUGIN_ROOT/hooks/hook.sh\"" }] }],
"PostToolUse": [{ "matcher": "*", "hooks": [{ "command": "bash \"$CLAUDE_PLUGIN_ROOT/hooks/hook.sh\"" }] }]
```

**Script:** `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh`

This is the highest-frequency hook in the entire ecosystem. The `*` matcher means it fires on every single tool use, twice per tool call (pre and post). What the script does on every invocation:

1. `cat` stdin into memory
2. `jq` call to extract 7 fields in one pass (efficient)
3. File read + file write of a per-session sequence counter (`~/.claude/tool-time/.seq-{SESSION_ID}`)
4. For PostToolUse: a second `jq` call to detect errors
5. `jq -nc` to build the JSONL line
6. `echo >> events.jsonl` (append)

That is 3 external process invocations per tool call (jq, jq, jq). At 200 tool calls per session, this script runs 400 times, spawning 1200+ jq processes plus 400 bash subshells.

The seq counter pattern (read file, increment in bash, write file) has a TOCTOU race under concurrent sessions but more critically represents a file I/O round-trip on every single tool call.

Additionally, the PreToolUse branch does a `tail -c 5000000` on the transcript file for Task tools to detect multi-agent workflows. Reading 5MB from disk on every Task invocation to grep for keywords is expensive.

**Per-call cost estimate:** 30-60ms wall time on a warmed filesystem, more on cold or remote storage.

**Fix options:**
- If the goal is analytics only, make both hooks async (`"async": true`) so they do not block tool execution. The 5-second timeout already applies; making them async removes the sequential blocking entirely.
- The seq counter can be eliminated. The JSONL timestamp + session_id already provides ordering; seq adds nothing that cannot be reconstructed at analysis time.
- The multi-agent detection in PreToolUse (tail 5MB + grep) should move to a dedicated Task-only matcher instead of running inside the `*` Pre handler.

---

### Finding 1.2: intercheck/context-monitor fires on EVERY PostToolUse (CRITICAL)

**File:** `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json`
```json
"PostToolUse": [
  { "hooks": [{ "command": "${CLAUDE_PLUGIN_ROOT}/hooks/context-monitor.sh" }] },
  ...
]
```

The first binding in the PostToolUse array has **no matcher at all** — it fires on every tool call.

**Script:** `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh`

What it does on every invocation:
1. `jq -r '.tool_name'` — first jq call
2. `jq -r '.tool_output | length'` — second jq call (reads full tool output into memory)
3. `date +%s` — subprocess
4. Multiple `jq` reads from state file
5. **Two `python3` invocations** for floating-point arithmetic (pressure decay and pressure update):
   ```bash
   DECAY=$(python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))" ...)
   PRESSURE=$(python3 -c "print(round(max(0, $PRESSURE - $DECAY) + $WEIGHT, 2))" ...)
   ```
6. `jq -n` to write new state
7. **Two more `python3` invocations** for threshold comparisons:
   ```bash
   python3 -c "exit(0 if $PRESSURE > 120 else 1)"
   python3 -c "exit(0 if $PRESSURE > 90 else 1)"
   ```

That is 4 `python3` subprocess spawns and multiple `jq` spawns on **every tool call**. Python startup alone is 30-80ms per invocation. At 4 spawns per call and 200 calls per session, this is 800 Python process starts — potentially 24-64 seconds of Python startup overhead alone, none of which does meaningful computation. The actual math (a float multiply and a comparison) is trivially expressible in `awk` or bash arithmetic.

**Fix — replace all python3 arithmetic with awk or bash:**
```bash
# Replace python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))"
DECAY=$(awk "BEGIN{printf \"%.2f\", $ELAPSED / 600.0 * 0.5}")

# Replace python3 -c "exit(0 if $PRESSURE > 120 else 1)"
awk "BEGIN{exit ($PRESSURE > 120) ? 0 : 1}"
```

This eliminates all 4 Python spawns. The fix is low risk: pure arithmetic with no library dependencies.

The state file itself (JSON read/write via jq on every call) is a secondary concern but compound it with the Python overhead makes this the costliest per-call hook in the system.

---

### Finding 1.3: intercheck/context-monitor — O(N) string length on tool output

In `context-monitor.sh`:
```bash
OUTPUT_LEN=$(echo "$INPUT" | jq -r '.tool_output // "" | length' 2>/dev/null || echo 0)
```

This reads the full tool output JSON (potentially hundreds of KB for a Read or Grep result) into memory for a string length calculation. `jq`'s `| length` on a string is O(N) in character count. For a large Read (2000-line file), tool output may be 80-100KB; this is unavoidable in the current model but the `jq -r` step deserializes the full JSON before computing length. Using `wc -c` after `jq -r` would not improve it; the real fix is to cap the output before piping to jq if only length is needed.

---

## 2. SessionStart — Blocking Work on the Critical Context-Delivery Path

### Finding 2.1: clavain/session-start.sh — five find scans + two curl calls (HIGH)

**File:** `/root/projects/Interverse/os/clavain/hooks/session-start.sh`

This script is synchronous (despite `"async": true` in hooks.json — async applies to the OS scheduling, not whether Claude waits for context injection; context injection via stdout is always synchronous to the session start). The script runs the following before delivering `additionalContext`:

**Five `find` scans against the plugin cache directory:**
```bash
# _discover_interflux_plugin (lib.sh)
find "${HOME}/.claude/plugins/cache" -maxdepth 5 -path '*/interflux/*/.claude-plugin/plugin.json' ...

# _discover_interpath_plugin
find "${HOME}/.claude/plugins/cache" -maxdepth 5 -path '*/interpath/*/scripts/interpath.sh' ...

# _discover_interwatch_plugin
find "${HOME}/.claude/plugins/cache" -maxdepth 5 -path '*/interwatch/*/scripts/interwatch.sh' ...

# _discover_interlock_plugin
find "${HOME}/.claude/plugins/cache" -maxdepth 5 -path '*/interlock/*/scripts/interlock-register.sh' ...

# _discover_beads_plugin
find "${HOME}/.claude/plugins/cache" -maxdepth 5 -path '*/interphase/*/hooks/lib-gates.sh' ...
```

Each `find` with `-maxdepth 5` on a plugin cache with 30+ plugins traverses potentially thousands of inodes. With 5 separate find invocations, this represents significant disk I/O at every session start.

**Two network curl calls (sequential when Intermute is reachable):**
```bash
curl -sf --connect-timeout 1 --max-time 2 "${_intermute_url}/health"
curl -sf --connect-timeout 1 --max-time 2 "${_intermute_url}/api/agents?project=..."
```

When Intermute is reachable, a third conditional curl fires for reservations:
```bash
curl -sf --connect-timeout 1 --max-time 2 "${_intermute_url}/api/reservations?project=..."
```

When Intermute is **not** reachable, each curl blocks for up to 1 second (connect-timeout). Three curl calls × 1s connect timeout = up to 3 seconds of blocking on session start just for the health check to fail. On a first session after a reboot, with a cold plugin cache, the 5 find scans run before the curls, adding further latency.

**Additional work before context delivery:**
- `bd doctor --json` (beads health check, external subprocess)
- `python3` called inline for beads issue count parsing
- `pgrep -f "Xvfb :99"` (process scan)
- `git rev-parse --is-inside-work-tree` (subprocess)
- `stat` on versions file
- `source sprint-scan.sh` which triggers more work (see Finding 2.2)

**Fix for find scans:** Cache the result of companion discovery in a file (`~/.claude/tool-time/.companion-cache`) with a 1-hour TTL. On session start, read the cache file if it is fresh; run the finds only if stale or absent. The plugin set changes only on install/uninstall, not on session start.

```bash
CACHE_FILE="$HOME/.claude/clavain-companion-cache"
if [[ -f "$CACHE_FILE" ]] && [[ $(( $(date +%s) - $(stat -c %Y "$CACHE_FILE") )) -lt 3600 ]]; then
    source "$CACHE_FILE"
else
    # run finds, write results to CACHE_FILE
fi
```

**Fix for Intermute connection probing:** The connect-timeout should be reduced from 1s to 0.3s for the health check. If it fails, skip agent/reservation queries. This cuts the worst-case Intermute-offline penalty from 3s to ~0.9s.

---

### Finding 2.2: sprint_brief_scan — O(N) grep per plan file on every session start (MEDIUM)

**File:** `/root/projects/Interverse/os/clavain/hooks/sprint-scan.sh`

`sprint_brief_scan()` is called synchronously inside `session-start.sh`. It runs:

1. `sprint_check_coordination` — may trigger its own curl calls (but deduplicates using `_INTERMUTE_*_CACHE` vars if set — this is good)
2. A loop over all plan files in `docs/plans/*.md`:
   ```bash
   for file in "$plans_dir"/*.md; do
       total=$(grep -c '^\s*- \[[ x]\]' "$file" ...)
       checked=$(grep -c '^\s*- \[x\]' "$file" ...)
       stat -c %Y "$file"  # mtime check
   done
   ```
   This spawns 2 grep processes per plan file. In a project with 20 plan files, that is 40 grep subprocesses at every session start.

3. `sprint_count_orphaned_brainstorms` — iterates brainstorm files, runs `ls` + `grep -qi` per brainstorm.
4. `sprint_stale_beads` — calls `bd stale` (external subprocess).
5. Sources `lib-sprint.sh` and calls `sprint_find_active` which invokes `bd` again.

`session-start.sh` itself also sources `lib-sprint.sh` **again** after `sprint-scan.sh` already sourced it, then calls `sprint_find_active` **again** — a duplicate `bd` call and a duplicate `jq` pipeline.

**File:** `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 196-211)
```bash
source "${SCRIPT_DIR}/lib-sprint.sh" 2>/dev/null || true
if type sprint_find_active &>/dev/null; then
    ...
    active_sprints=$(sprint_find_active 2>/dev/null) || ...
    sprint_count=$(echo "$active_sprints" | jq 'length' ...) ...
```

And in `sprint-scan.sh`, `sprint_brief_scan()` also calls `sprint_find_active`. This means `sprint_find_active` (and the underlying `bd` call) runs twice per session start.

**Fix:** Extract active sprint discovery to a single call in `session-start.sh`, pass the result to `sprint_brief_scan` as a parameter rather than having both sites call it independently.

---

### Finding 2.3: interspect-session.sh — sqlite3 + `ic events tail` on every startup (MEDIUM)

**File:** `/root/projects/Interverse/os/clavain/hooks/interspect-session.sh`

Runs async alongside session-start but does significant work:
1. `sqlite3` — DB init check (runs migration SQL on every startup even when DB exists)
2. `ic events tail --all --consumer=interspect-consumer --limit=100` — external process
3. Per-event `jq` parsing in a while loop (up to 100 iterations)
4. Per-event `_interspect_insert_evidence` calls, each of which runs `git rev-parse --short HEAD`, `_interspect_project_name` (another git call), and `_interspect_next_seq` (another sqlite3 query)
5. `_interspect_check_canaries` — additional sqlite3 query + canary evaluation loop

The migration SQL that runs on every startup for the fast path:
```bash
if [[ -f "$_INTERSPECT_DB" ]]; then
    sqlite3 "$_INTERSPECT_DB" <<'MIGRATE'
CREATE TABLE IF NOT EXISTS blacklist ...
CREATE INDEX IF NOT EXISTS ...
CREATE TABLE IF NOT EXISTS canary_samples ...
MIGRATE
    sqlite3 "$_INTERSPECT_DB" "ALTER TABLE sessions ADD COLUMN run_id TEXT;" 2>/dev/null || true
    ...
fi
```

This opens sqlite3 twice per startup (migration + ALTER) even when the schema is already current. A schema version pragma (`PRAGMA user_version`) would allow skipping migration on the fast path.

Because interspect-session runs async, it does not block context delivery. However, the ic events cursor registration check adds another `ic` invocation:
```bash
if ! ic events cursor list 2>/dev/null | grep -q 'interspect-consumer'; then
    ic events cursor register interspect-consumer --durable 2>/dev/null || true
fi
```

This runs `ic events cursor list` (subprocess + DB query) on every session start just to check whether a cursor exists. Since the cursor is persistent and stable, it changes only on first run. This check should be skipped with a local sentinel file after first registration.

---

### Finding 2.4: interkasten/setup.sh — 30-second timeout at SessionStart (LOW-MEDIUM)

**File:** `/root/projects/Interverse/plugins/interkasten/hooks/hooks.json`
```json
"SessionStart": [
  { "matcher": "", "hooks": [
    { "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/setup.sh\"", "timeout": 30 },
    { "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/session-status.sh\"", "timeout": 5 }
  ]}
]
```

The `setup.sh` hook has a 30-second timeout. If the interkasten MCP server is starting or the Notion API is slow, this blocks session initialization for up to 30 seconds before Claude Code delivers context. `setup.sh` was not readable in this review but the 30-second budget signals a blocking network operation (Notion API health check or MCP server startup) on the critical path.

The `""` matcher is equivalent to a wildcard — it fires on every session event type (startup, resume, clear, compact). A setup operation that might take 30 seconds should not re-run on compact or clear events where the MCP server is already running.

---

## 3. Per-Edit-Call Overhead

### Finding 3.1: intercheck — three hooks fire on every Edit/Write (MEDIUM)

For every Edit or Write tool call, the following hooks fire sequentially:
1. `context-monitor.sh` (wildcard, always fires) — 4 python3 spawns as noted above
2. `syntax-check.sh` (matcher: Edit|Write|NotebookEdit) — spawns `python3`, `bash -n`, `go vet`, or `node --check`
3. `auto-format.sh` (matcher: Edit|Write|NotebookEdit) — may spawn `ruff`, `shfmt`, `gofmt`, `jq`, or `npx`

Plus from clavain:
4. `interserve-audit.sh` (matcher: Edit|Write|MultiEdit|NotebookEdit) — lightweight file check, fast
5. `catalog-reminder.sh` (matcher: Edit|Write|MultiEdit) — runs sentinel check + jq

That is 5 hooks per Edit, potentially spawning 6-8 external processes (python3 ×4 in context-monitor, python3 ×1 in syntax-check, formatter ×1). For a session with 50 edits, this is 400 process spawns from context-monitor's python3 calls alone.

**Fix for syntax-check.sh:** The `python3 -m py_compile` call spawns a full Python interpreter to parse one file. For shell scripts, `bash -n` is fast. For JSON, `jq . "$FP" > /dev/null` avoids Python startup entirely. Python-based checks (py_compile, tomllib, yaml) should be batched or replaced with lighter-weight alternatives where possible.

---

### Finding 3.2: clavain/bead-agent-bind.sh — curl to Intermute on every bd claim (LOW)

**File:** `/root/projects/Interverse/os/clavain/hooks/bead-agent-bind.sh`

When an agent claims a bead (PostToolUse:Bash matching `bd update --status=in_progress` or `bd claim`), this script:
1. Calls `bd show "$ISSUE_ID" --json` to read existing metadata
2. If a different agent is bound, calls `curl` to check if that agent is online
3. If online, sends another `curl POST` to notify the other agent

The two curl calls fire on what could be a frequent path (any `bd update --status=in_progress`). The guard `[[ -n "${INTERMUTE_AGENT_ID:-}" ]] || exit 0` is a fast path if coordination is not active, which is good. But when active in a multi-agent session with many bead operations, each `bd claim` incurs two network round-trips.

This is acceptable overhead for the use case (bead conflict detection is important when agents actually overlap), but the `bd show` call on every claim — even when no conflict exists — adds one extra subprocess unconditionally.

**Fix:** Move the `bd show` call after confirming intermute has a different agent registered, not before.

---

## 4. Redundant External Calls

### Finding 4.1: `sprint_find_active` called twice at session start (MEDIUM)

As noted in Finding 2.2, `sprint_find_active` (which calls `bd`) is invoked twice:
- Once inside `sprint_brief_scan` (called from `session-start.sh` line 176)
- Once directly in `session-start.sh` lines 201-212

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` lines 176, 201
- `/root/projects/Interverse/os/clavain/hooks/sprint-scan.sh` line 354

The duplicate call produces no harm (idempotent read), but it is a wasted subprocess. The `bd` CLI may itself hit a SQLite database, making this a redundant disk read.

**Fix:** Pass the sprint scan result from `sprint_brief_scan` back via a variable, or call `sprint_find_active` once and pass the result to both.

---

### Finding 4.2: `git rev-parse` called many times in a single session-start (MEDIUM)

The following functions each invoke `git rev-parse` independently during session start:

- `_discover_interlock_plugin` prerequisite: `git rev-parse --is-inside-work-tree`
- `_intermute_project = basename "$(git rev-parse --show-toplevel 2>/dev/null)"`
- `_interspect_db_path`: `git rev-parse --show-toplevel`
- `_interspect_project_name`: `git rev-parse --show-toplevel`
- `_interspect_consume_kernel_events`: `git rev-parse --show-toplevel` (via `_interspect_db_path`)
- `sprint-scan.sh` / `lib-sprint.sh`: multiple `git rev-parse` calls for coordination check

Conservatively, `git rev-parse --show-toplevel` is called 5+ times during a single session start. While `git rev-parse` is fast for local repos (~5ms), 5 calls add ~25ms and more importantly spawn 5 subshells. This is a low-severity issue individually but compounds with the other overhead.

**Fix:** Export `_GIT_TOPLEVEL` once at the top of session-start.sh and use the variable throughout.

---

### Finding 4.3: lib-interspect.sh — `_interspect_db_path` called redundantly (LOW)

`_interspect_db_path` calls `git rev-parse --show-toplevel` each time. It is called from `_interspect_ensure_db`, `_interspect_next_seq`, `_interspect_insert_evidence`, and `_interspect_is_routing_eligible`. In `interspect-session.sh`, for a batch of 100 events, `_interspect_insert_evidence` is called up to 100 times, each triggering a `git rev-parse`.

The global `_INTERSPECT_DB` is set by `_interspect_ensure_db`, but not all callers go through `ensure_db` before calling functions that recompute the path.

**Fix:** Set `_INTERSPECT_DB` once during initialization and use it as the canonical path throughout. The current code partially does this but falls back to re-calling `_interspect_db_path` when `_INTERSPECT_DB` is unset.

---

## 5. Operations That Could Be Cached or Deferred

### Finding 5.1: interstat/post-task.sh — runs `init-db.sh` on every Task tool call (MEDIUM)

**File:** `/root/projects/Interverse/plugins/interstat/hooks/post-task.sh`

```bash
bash "$INIT_DB_SCRIPT" >/dev/null 2>&1 || true
```

`init-db.sh` is called unconditionally on every Task tool use. If a session spawns 20 subagents, init-db runs 20 times. The script creates the SQLite database and schema if it does not exist — but once the DB exists, this is pure overhead (a bash spawn + sqlite3 process + DDL queries that are no-ops).

**Fix:** Check for DB existence before calling init-db:
```bash
[[ -f "$DB_PATH" ]] || bash "$INIT_DB_SCRIPT" >/dev/null 2>&1 || true
```

This reduces the overhead from O(N Task calls) to O(1) per session.

---

### Finding 5.2: tldr-swinton/post-read-extract.sh — wc -l and md5sum on every Read (LOW-MEDIUM)

**File:** `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`

Fires after every Read tool call. On the hot path:
1. `jq` to extract file path
2. `wc -l` to count lines
3. `md5sum` of the file path string (for the per-file flag)

For files under 300 lines (the majority of Read calls in practice), the hook exits after `wc -l`. The `wc -l` requires reading the file's inode but is fast. The `md5sum` runs even when the hook will skip (it runs before the early exit). This is a minor efficiency issue — the file hash should only be computed if the 300-line check passes.

**Fix:** Move the md5sum call to after the `LINE_COUNT` check:
```bash
if [ "$LINE_COUNT" -lt 300 ]; then exit 0; fi
# ... then compute hash
FILE_HASH=$(echo -n "$FILE" | md5sum | cut -d' ' -f1)
```

Also, `python3` is spawned for JSON encoding of the final output even when the hook would not produce output. The `python3` call should only run when `EXTRACT_OUTPUT` is non-empty (it already does, the flow is correct here — this is a minor note).

---

### Finding 5.3: lib.sh companion discovery — no caching between session starts (MEDIUM)

**File:** `/root/projects/Interverse/os/clavain/hooks/lib.sh`

All five `_discover_*_plugin` functions run `find` against the plugin cache every time they are called, with no caching. They check `INTERFLUX_ROOT`, `INTERLOCK_ROOT` etc. as env vars first (good), but in a typical session where these env vars are not pre-set, all five find scans run every SessionStart.

The plugin cache changes only when `/plugin install` or `/plugin uninstall` runs. Between those events, the results are stable. A file-based cache with a 24-hour TTL would eliminate all five finds on every subsequent session start.

**Current guard:** env var check
**Proposed guard:** env var → cache file (24h TTL) → find (updates cache)

---

### Finding 5.4: interlock/pre-edit.sh — curl on every Edit when INTERLOCK_AUTO_RELEASE=1 (LOW)

**File:** `/root/projects/Interverse/plugins/interlock/hooks/pre-edit.sh`

The inbox check uses a 30-second cache (`-mmin -0.5` = 30 seconds). This is reasonable. The conflict check via `interlock-check.sh` fires unconditionally for every Edit when `INTERMUTE_AGENT_ID` is set. In a session with 100 edits across 10 files, this is 100 HTTP requests to intermute.

The intermute calls are bounded by the 30s throttle for inbox checks, but the reservation conflict check (`interlock-check.sh`) has no throttle — it hits the HTTP API on every single Edit call. For multi-agent sessions with high edit frequency (e.g., a batch formatting run), this could generate 50-100 HTTP requests in a short window.

**Fix:** Consider a 5-second cache on the reservation conflict response for a given file path, since reservation state is unlikely to change within 5 seconds.

---

## 6. Architectural Observations

### Finding 6.1: Stop hook anti-cascade via sentinel — correct but adds one sentinel check per Stop hook

The three Stop hooks (session-handoff, auto-compound, auto-drift-check) all use a shared sentinel via `intercore_check_or_die`. The sentinel correctly prevents re-entrant firing when a Stop hook itself triggers a Stop event. This is well-designed.

The cost: each Stop hook calls `intercore_available` (which runs `ic health` on first call) plus the sentinel check. With 3 Stop hooks and a fallback to temp files, the overhead is acceptable at low frequency. Stop events are rare.

### Finding 6.2: auto-compound.sh — transcript scan with tail (acceptable)

`tail -80` on a potentially large transcript file is fast (seeks from end). The subsequent `grep -iq` calls are in-memory string operations on the 80-line slice. This is efficient. No issue.

### Finding 6.3: interfluence/learn-from-edits.sh — not reviewed (out of scope for this pass)

The interfluence hook fires only on Edit (matched), which limits its blast radius. A full review of its contents would require reading the script, but its bounded matcher means it cannot be a wildcard overhead source.

---

## Priority Summary

| # | Finding | Plugin | Severity | Type |
|---|---------|--------|----------|------|
| 1.1 | tool-time `*` matcher fires on every Pre+PostToolUse; not async | tool-time | CRITICAL | Per-call overhead |
| 1.2 | context-monitor spawns 4 python3 processes per tool call for float arithmetic | intercheck | CRITICAL | Per-call overhead |
| 2.1 | session-start: 5 find scans + up to 3 curl calls, no caching | clavain | HIGH | SessionStart latency |
| 2.2 | sprint_find_active called twice; 2 grep/plan file in brief_scan | clavain | MEDIUM | SessionStart latency |
| 2.3 | interspect-session: migration SQL + cursor check + ic events tail every startup | clavain | MEDIUM | SessionStart latency |
| 3.1 | 5 hooks fire per Edit; syntax-check spawns python3 per edit | intercheck/clavain | MEDIUM | Per-edit overhead |
| 4.1 | sprint_find_active / bd called twice at session start | clavain | MEDIUM | Redundant calls |
| 4.2 | git rev-parse called 5+ times during single session start | clavain | MEDIUM | Redundant calls |
| 5.1 | interstat init-db.sh runs on every Task call | interstat | MEDIUM | Cacheable init |
| 2.4 | interkasten setup.sh has 30s timeout at SessionStart | interkasten | LOW-MEDIUM | SessionStart latency |
| 5.2 | tldr-swinton md5sum computed before line count gate | tldr-swinton | LOW | Per-call waste |
| 4.3 | _interspect_db_path / git rev-parse called per-event in batch | clavain | LOW | Redundant calls |
| 5.3 | companion discovery: 5 find scans with no persistent cache | clavain | MEDIUM | Cacheable discovery |
| 5.4 | interlock conflict check hits HTTP API on every Edit | interlock | LOW | Throttle gap |

---

## Recommended Fixes — Ordered by Impact

**Fix 1 (CRITICAL): Make tool-time hook async.**
In `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json`, add `"async": true` to both PreToolUse and PostToolUse hooks. The analytics logging does not need to block tool execution. The multi-agent Task detection in PreToolUse cannot be async (it needs to modify input), so split it into a separate Task-only hook. This is the highest ROI change in the codebase.

**Fix 2 (CRITICAL): Replace python3 arithmetic in context-monitor.sh with awk.**
In `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh`, replace all 4 `python3 -c` invocations with `awk` or bash `(( ))` arithmetic. Example:
```bash
# Before:
DECAY=$(python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))" 2>/dev/null || echo "0")
# After:
DECAY=$(awk "BEGIN{printf \"%.2f\", $ELAPSED / 600.0 * 0.5}")
```
Eliminates ~24-64 seconds of cumulative Python startup per 200-call session.

**Fix 3 (HIGH): Cache companion plugin discovery in session-start.sh.**
Write discovered plugin roots to `~/.claude/clavain-companion-cache.sh` with a 1-hour mtime TTL. Source the cache on session start if fresh; otherwise run finds and update the cache. Eliminates 5 find scans per session start.

**Fix 4 (MEDIUM): Deduplicate sprint_find_active calls in session-start.sh.**
Call `sprint_find_active` once at the top of `session-start.sh`, store the result, and pass it to `sprint_brief_scan`. Remove the second call at lines 201-212. Saves one `bd` invocation per session start.

**Fix 5 (MEDIUM): Add schema version guard to interspect-session.sh.**
Add a `PRAGMA user_version` check before running migration SQL. Register the interspect cursor with a local sentinel file to avoid running `ic events cursor list` on every session start.

**Fix 6 (MEDIUM): Guard interstat's init-db.sh with a DB existence check.**
In `/root/projects/Interverse/plugins/interstat/hooks/post-task.sh`, change:
```bash
bash "$INIT_DB_SCRIPT" >/dev/null 2>&1 || true
```
to:
```bash
[[ -f "$DB_PATH" ]] || bash "$INIT_DB_SCRIPT" >/dev/null 2>&1 || true
```

**Fix 7 (LOW): Reorder md5sum after line count gate in post-read-extract.sh.**
Move `FILE_HASH` computation to after the 300-line check in `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`.

---

## Measurement Recommendations

The following would validate or falsify the severity estimates above:

1. **tool-time overhead:** Add `date +%s%N` timing around the hook in a test session. Compare session duration with and without `"async": true` on a 200-call session.

2. **context-monitor python3 cost:** Run `time python3 -c "print(1)"` on this server. If startup is under 10ms, the impact is lower than estimated; if 50ms+, the impact is higher.

3. **SessionStart latency:** Add timing to session-start.sh with `date +%s%N` before and after the find scans and curl calls. Log to `/tmp/session-start-timing.log`. Run three sessions and compare.

4. **intercheck formatting cost:** The auto-format hook is a 10-second timeout. Use `strace -e execve -c` during an editing session to count subprocess spawns attributable to intercheck.

All estimates above are based on code reading. Actual measurements may shift severity ratings significantly in either direction depending on filesystem cache warmth and network conditions.
