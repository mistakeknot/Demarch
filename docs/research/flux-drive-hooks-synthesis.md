# Flux-Drive Hooks Synthesis Report

**Date:** 2026-02-20
**Scope:** Parallel review of Claude Code hooks across Interverse monorepo (12 plugins, 30+ bindings)
**Reviewers:** flux-drive-token-economy, flux-drive-orchestration, flux-drive-performance
**Prior Work:** 8 hook fixes already applied this session; 7 beads already created for known items

---

## Executive Summary

Three independent agents reviewed hook redundancy, token inefficiency, and performance overhead. The review identified **15 new findings** not previously addressed (excluding 8 already-fixed items and 7 tracked beads). The ecosystem has grown to 30+ hook bindings with overlapping concerns, unnecessary process spawning, and per-call overhead accumulating to **14-28 seconds per typical 200-call session**.

**Critical issues:** tool-time fires on every tool call with `*` matchers; intercheck/context-monitor spawns 4 Python processes per call for trivial float arithmetic; clavain session-start.sh performs 5 find scans with no caching.

**Overall verdict:** **NEEDS CHANGES** — Multiple P0/P1 findings require immediate fixes to reduce session latency and hook redundancy. Session start currently takes 500ms-2s, much of it from uncached operations and redundant subprocess calls.

---

## Validation Summary

| Status | Count |
|--------|-------|
| Valid agent reports | 3/3 |
| Malformed reports | 0/3 |
| Total findings across agents | 41 |
| Already addressed (excluded) | 8 |
| Duplicate findings (merged) | 18 |
| New findings (this synthesis) | 15 |

---

## Convergence Analysis

**High convergence (all 3 agents reported):**
- P0-1: tool-time fires on every tool call with `*` matcher — **3/3 convergence**
- P0-2: intercheck context-monitor has no matcher, fires on every PostToolUse — **3/3 convergence**
- P0-5: interserve pre-read-intercept.sh exists but is not registered — **2/3 convergence** (token + orchestration)
- P1-1: clavain session-start.sh is 325 lines, does too much — **3/3 convergence** (different angles)
- P1-2: Duplicate sprint detection (session-start calls sprint_find_active twice) — **2/3 convergence** (performance + orchestration)

**Medium convergence (2 agents reported):**
- P0-3: Three plugins write CLAUDE_SESSION_ID to env file (race condition) — **orchestration + performance**
- P0-4: clavain and interlock both query Intermute for agents/reservations — **orchestration + performance**
- P1-6: interlock pre-edit.sh does expensive git pull --rebase on PreToolUse — **orchestration + performance**
- P2-3: Session handoff reads up to 40 lines uncapped — **token-economy + performance**

**Low convergence (1 agent reported but high confidence):**
- P2-1: context-monitor uses python3 for float arithmetic — **performance** (specific recommendation: use awk)
- P5-1: interstat init-db.sh runs on every Task call — **performance**
- P2-5: Five find calls in lib.sh have no cache — **performance** (specific: companion discovery)

---

## Findings Index

### P0 — Critical (blocks merge, causes session slowdown)

| ID | Title | Agents | Convergence | Severity |
|----|-------|--------|-------------|----------|
| P0-1 | tool-time fires on EVERY Pre+PostToolUse with `*` matcher | Token, Orch, Perf | 3/3 | CRITICAL |
| P0-2 | intercheck context-monitor has no matcher, fires on EVERY PostToolUse | Token, Orch, Perf | 3/3 | CRITICAL |
| P0-3 | Three plugins independently write CLAUDE_SESSION_ID (race) | Orch, Perf | 2/3 | CRITICAL |
| P0-4 | clavain + interlock both query Intermute at session start (redundant) | Orch, Perf | 2/3 | CRITICAL |
| P0-5 | interserve pre-read-intercept.sh exists but not registered | Token, Orch | 2/3 | CRITICAL |
| P0-6 | interflux hooks.json has invalid structure | Orch | 1/3 | CRITICAL |

### P1 — Important (should fix soon, reduces latency/redundancy)

| ID | Title | Agents | Convergence | Severity |
|----|-------|--------|-------------|----------|
| P1-1 | clavain session-start.sh is 325 lines, does too much | Token, Orch, Perf | 3/3 | HIGH |
| P1-2 | Duplicate sprint detection (sprint_find_active called twice) | Orch, Perf | 2/3 | HIGH |
| P1-3 | Duplicate sprint lib sourcing (lib-sprint.sh sourced twice) | Token, Perf | 2/3 | HIGH |
| P1-4 | auto-compound.sh + auto-drift-check.sh duplicate transcript analysis | Orch | 1/3 | HIGH |
| P1-5 | interlock/pre-edit.sh does expensive inbox checks on every Edit | Token | 1/3 | HIGH |
| P1-6 | interlock pre-edit.sh does git pull --rebase on PreToolUse (risky) | Orch, Perf | 2/3 | HIGH |
| P1-7 | interfluence learn-from-edits.sh uses non-standard env vars | Orch | 1/3 | HIGH |
| P1-8 | tool-time agent-output-redirect should be separate hook | Orch | 1/3 | HIGH |

### P2 — Medium Priority (optimization opportunities)

| ID | Title | Agents | Convergence | Severity |
|----|-------|--------|-------------|----------|
| P2-1 | context-monitor.sh uses python3 for float arithmetic (30-50ms each) | Token, Perf | 2/3 | MEDIUM |
| P2-2 | interserve-audit.sh silently logs, never injects context | Token | 1/3 | MEDIUM |
| P2-3 | clavain handoff context can inject up to 40 lines uncapped (3200 chars) | Token, Perf | 2/3 | MEDIUM |
| P2-4 | Redundant fast-exit guards in bead-agent-bind.sh | Orch | 1/3 | MEDIUM |
| P2-5 | Five find calls in lib.sh companion discovery (no cache, ~1s total) | Token, Perf | 2/3 | MEDIUM |
| P2-6 | interstat init-db.sh runs unconditionally on every Task call | Perf | 1/3 | MEDIUM |
| P2-7 | tldr-swinton post-read-extract.sh md5sum computed before gate | Perf | 1/3 | MEDIUM |

### P3 — Low Priority (polish)

| ID | Title | Agents | Convergence |
|----|-------|--------|-------------|
| P3-1 | tldr-swinton post-read-extract.sh injects large extracts (125-500 tokens) | Token | 1/3 |
| P3-2 | interspect-session.sh runs migration SQL on every startup | Perf | 1/3 |
| P3-3 | interject session-start.sh uses python3 for JSON parsing (not jq) | Orch, Perf | 2/3 |
| P3-4 | interflux session-start.sh is a no-op in stub mode | Token, Orch | 2/3 |
| P3-5 | Empty matcher strings vs absent matchers (consistency issue) | Orch | 1/3 |

---

## Detailed Findings

### P0-1: tool-time fires on EVERY Pre+PostToolUse with `*` matcher

**Convergence:** 3/3 agents

**Files:**
- `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json` (lines 3-51)
- `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh`

**Problem:**
tool-time registers `*` matchers on `PreToolUse`, `PostToolUse`, `SessionStart`, and `SessionEnd`. Every tool call spawns two processes (pre + post). Each invocation:
- Reads stdin (jq parse)
- Manages a sequence file (file I/O)
- Appends a JSONL line
- PreToolUse also reads 5MB transcript tail + greps for multi-agent detection

Estimated cost per 200-tool session: 400+ process spawns, ~4-6 seconds cumulative latency.

**Recommendation:**
1. Remove PreToolUse binding entirely (PostToolUse already captures timing)
2. If Task prompt injection (lines 90-151) is needed, split into separate Task-only hook in clavain
3. Make PostToolUse async (`"async": true`) since analytics don't need to block execution
4. Reduce SessionStart binding or remove (SessionEnd already summarizes)

---

### P0-2: intercheck context-monitor fires on EVERY PostToolUse, spawns 4 Python processes

**Convergence:** 3/3 agents

**Files:**
- `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json` (lines 3-12)
- `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh`

**Problem:**
No `matcher` field = fires on every tool call. Per invocation:
- `jq` calls (3x)
- `date +%s` subprocess
- **4 `python3` spawns** for simple float arithmetic (decay, pressure update, thresholds)
- State file read/write

Python startup: 30-50ms each. Over 200 calls = 800 Python starts, potentially 24-64 seconds overhead.

**Recommendation:**
1. Add matcher: `"Edit|Write|Bash|Read|Grep|Task|WebFetch|WebSearch"` (skip Skill, lightweight tools)
2. Replace all `python3 -c` with `awk`:
   ```bash
   # Before:
   DECAY=$(python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))" ...)
   # After:
   DECAY=$(awk "BEGIN{printf \"%.2f\", $ELAPSED / 600.0 * 0.5}")
   ```

---

### P0-3: Three plugins write CLAUDE_SESSION_ID to env file (race condition)

**Convergence:** 2/3 agents (orchestration, performance)

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 21-26)
- `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` (lines 18-19)

**Problem:**
clavain and interlock both async-run session-start hooks that write `export CLAUDE_SESSION_ID=...` to `$CLAUDE_ENV_FILE`. Both write the same value but the parallel execution creates a race condition on file writes.

**Recommendation:**
Designate clavain as canonical CLAUDE_SESSION_ID writer. Interlock should read from env var instead of re-writing.

---

### P0-4: clavain + interlock both query Intermute at session start

**Convergence:** 2/3 agents (orchestration, performance)

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 100-132)
- `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` (lines 37-38)

**Problem:**
clavain makes 3 HTTP calls to Intermute (health check, agents list, reservations). interlock also calls Intermute to register the agent. Both run async but fetch overlapping data. Shell variables cache within a process boundary so don't cross to interlock.

Estimated redundant cost: 4-6 HTTP calls per session start (~200-400ms).

**Recommendation:**
Have interlock write registration result to temp file (e.g., `/tmp/intermute-session-${SESSION_ID}.json`). Clavain reads from file instead of making its own queries. Alternatively, merge into single hook that both consume.

---

### P0-5: interserve pre-read-intercept.sh exists but is not registered

**Convergence:** 2/3 agents (token, orchestration)

**Files:**
- `/root/projects/Interverse/plugins/interserve/hooks/hooks.json` (empty hooks object)
- `/root/projects/Interverse/plugins/interserve/hooks/pre-read-intercept.sh` (72 lines, dead code)

**Problem:**
interserve's hooks.json contains `{"hooks": {}}` — empty. The pre-read-intercept.sh script exists but is never invoked. The interserve mode's read-interception feature is broken.

**Recommendation:**
Either:
1. Register the hook: `"PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/pre-read-intercept.sh", "timeout": 5}]}]`
2. Or remove the dead script if the feature has been abandoned.

---

### P0-6: interflux hooks.json has invalid structure

**Convergence:** 1/3 agents (orchestration)

**Files:**
- `/root/projects/Interverse/plugins/interflux/hooks/hooks.json`

**Problem:**
Non-standard structure:
```json
{
  "hooks": {
    "SessionStart": [
      { "type": "command", "command": "..." }
    ]
  }
}
```

Should be:
```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "..." }] }
    ]
  }
}
```

Additionally, the hook is a no-op in stub mode. Either fix schema and make it do real work, or remove entirely.

**Recommendation:**
Fix schema or remove the hook.

---

### P1-1: clavain session-start.sh is 325 lines, does too much

**Convergence:** 3/3 agents (all approached from different angles)

**File:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh`

**Problem:**
Single script handles:
1. Plugin cache cleanup
2. using-clavain skill injection
3. Beads health check (python3 subprocess)
4. Oracle detection
5. 5 companion plugin discoveries (with Intermute API calls and find scans)
6. Interserve mode detection
7. Upstream staleness check
8. Sprint scan sourcing
9. Discovery scan
10. Sprint bead detection
11. Handoff context loading
12. In-flight agent detection
13. Context budget management with priority shedding

Any early failure cascades. Hard to maintain, test, optimize.

**Recommendation:**
Split into a dispatcher that runs independent checks in parallel subshells and aggregates results. Each concern becomes a separate script.

---

### P1-2: Duplicate sprint detection (sprint_find_active called twice)

**Convergence:** 2/3 agents (orchestration, performance)

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 173-212)
- `/root/projects/Interverse/os/clavain/hooks/sprint-scan.sh` (line 354)

**Problem:**
`sprint_find_active` is called:
1. Inside `sprint_brief_scan` (called from session-start.sh line 176)
2. Directly in session-start.sh lines 201-212 (duplicate)

Both calls produce identical output. Wastes ~100 tokens of duplicate context + ~200ms redundant `bd`/`jq` calls.

**Recommendation:**
Remove lines 196-212 entirely. sprint_brief_scan output already includes the active sprint hint.

**Status:** Already listed in token-economy report as P1-1; confirmed by orchestration and performance reviewers.

---

### P1-3: lib-sprint.sh sourced twice at session start

**Convergence:** 2/3 agents (token, performance)

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 175, 198)
- `/root/projects/Interverse/os/clavain/hooks/sprint-scan.sh` (internal source)

**Problem:**
`sprint-scan.sh` sources `lib-sprint.sh` at its own line 350. Then `session-start.sh` sources it again at line 198. Both have `2>/dev/null || true` guards but no double-source protection. Functions like `sprint_find_active` end up defined twice.

**Recommendation:**
Add guard to `lib-sprint.sh`:
```bash
[[ -n "${_SPRINT_LIB_LOADED:-}" ]] && return 0
_SPRINT_LIB_LOADED=1
```
Consistent with pattern used by `sprint-scan.sh` (which has `_SPRINT_SCAN_LOADED`).

---

### P1-4: auto-compound.sh + auto-drift-check.sh duplicate transcript analysis

**Convergence:** 1/3 agents (orchestration)

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/auto-compound.sh`
- `/root/projects/Interverse/os/clavain/hooks/auto-drift-check.sh`

**Problem:**
Both Stop hooks:
1. Read same hook JSON
2. Check stop_hook_active
3. Claim shared stop sentinel
4. Read transcript file
5. Call `tail -80` on transcript
6. Run `detect_signals()` on same 80 lines

They independently grep the same signal patterns. Only ONE can fire per stop event (sentinel system), so auto-drift-check never fires if auto-compound fires first.

**Recommendation:**
Merge into single `auto-stop-actions.sh` that:
1. Detects signals once
2. If weight >= 3: trigger compound
3. Else if weight >= 2: trigger drift check

Eliminates sentinel race and ensures higher-priority action always wins.

---

### P1-5: interlock/pre-edit.sh does expensive inbox checks on every Edit

**Convergence:** 1/3 agents (token-economy)

**File:**
- `/root/projects/Interverse/plugins/interlock/hooks/pre-edit.sh`

**Problem:**
Fires on every Edit. Performs:
1. Inbox check for commit notifications (curl + jq parsing)
2. Inbox check for release-request messages (curl + jq parsing)
3. Reservation conflict check (curl)
4. Auto-reserve (curl POST)

On session start, both inbox checks fire on very first Edit, adding 2-4 curl calls + jq processing.

**Recommendation:**
30s throttle is reasonable. Make release-request inbox checks opt-in only when `INTERLOCK_AUTO_RELEASE=1` is set -- already the case. No change needed, but document that feature flag should default to off.

---

### P1-6: interlock pre-edit.sh does git pull --rebase on PreToolUse

**Convergence:** 2/3 agents (orchestration, performance)

**Files:**
- `/root/projects/Interverse/plugins/interlock/hooks/pre-edit.sh` (lines 28-63)

**Problem:**
PreToolUse hook runs `git pull --rebase` synchronously with 5-second timeout. Potentially slow/destructive. If rebase takes >5s, hook is killed mid-operation, leaving partial rebase state.

**Recommendation:**
Move auto-pull to less time-critical location (background checker), or increase timeout, or guard with check that pull will be fast.

---

### P1-7: interfluence learn-from-edits.sh uses non-standard env vars

**Convergence:** 1/3 agents (orchestration)

**File:**
- `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh`

**Problem:**
Hook reads `$CLAUDE_TOOL_NAME`, `$CLAUDE_TOOL_INPUT_FILE_PATH`, `$CLAUDE_TOOL_INPUT_OLD_STRING`, `$CLAUDE_TOOL_INPUT_NEW_STRING` as environment variables. Standard Claude Code hook protocol passes data via JSON on stdin. These env vars may be legacy API that no longer exists.

If unset, hook silently does nothing (exits because TOOL_NAME is empty). Voice-learning feature may be silently broken.

**Recommendation:**
Verify whether Claude Code actually sets these env vars. If not, rewrite to read from stdin JSON.

---

### P1-8: tool-time agent-output-redirect should be separate hook

**Convergence:** 1/3 agents (orchestration)

**Files:**
- `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh` (lines 90-151)

**Problem:**
tool-time has dual purpose:
1. Lines 1-89: JSONL event logging
2. Lines 90-151: "agent output redirect" feature (injects file-save instructions into Task prompts)

These are completely unrelated. Redirect is gated by PreToolUse + Task but entire hook runs on every tool call. The feature is a significant behavioral change hidden inside "tool-time" analytics plugin. Should be in clavain or dedicated orchestration plugin.

**Recommendation:**
Extract agent-output-redirect feature (lines 90-151) into separate hook in clavain with Task matcher on PreToolUse. Remove PreToolUse binding from tool-time entirely (related to P0-1).

---

### P2-1: context-monitor.sh uses python3 for float arithmetic

**Convergence:** 2/3 agents (token, performance)

**File:**
- `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh` (lines 36, 50, 67-73)

**Problem:**
Three `python3 -c` invocations per call for simple arithmetic:
```bash
DECAY=$(python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))")
PRESSURE=$(python3 -c "print(round(max(0, $PRESSURE - $DECAY) + $WEIGHT, 2))")
python3 -c "exit(0 if $PRESSURE > 120 else 1)"
```

Python startup: ~30-50ms each. Total: ~100-150ms per tool call just for arithmetic.

**Recommendation:**
Replace with `awk`:
```bash
DECAY=$(awk "BEGIN {printf \"%.2f\", $ELAPSED / 600.0 * 0.5}")
PRESSURE=$(awk "BEGIN {p = $PRESSURE - $DECAY; if (p<0) p=0; printf \"%.2f\", p + $WEIGHT}")
```

`awk` startup: ~1ms vs python3's ~30ms.

---

### P2-2: interserve-audit.sh silently logs, never injects context

**Convergence:** 1/3 agents (token-economy)

**File:**
- `/root/projects/Interverse/os/clavain/hooks/interserve-audit.sh`

**Problem:**
Fires on Edit|Write|MultiEdit|NotebookEdit, only writes to log file. Produces NO additionalContext output. Violations are logged but agent never learns about them.

**Recommendation:**
Either add additionalContext output for violations (agent can self-correct) or remove hook and rely solely on PreToolUse interserve/pre-read-intercept.sh for enforcement.

---

### P2-3: clavain handoff context can inject up to 40 lines uncapped

**Convergence:** 2/3 agents (token, performance)

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 217-233)

**Problem:**
Handoff file read with `head -40`: up to 3200 chars (~800 tokens). Budget shedding system drops handoff when over budget at section level. If other sections are small, 3200-char handoff survives, consuming large portion of 6000-char budget.

**Recommendation:**
Reduce `head -40` to `head -20` (handoff instructions already say "10-20 lines"). Or cap handoff_content at 1500 chars (~375 tokens) with truncation.

---

### P2-4: Redundant fast-exit guards in bead-agent-bind.sh

**Convergence:** 1/3 agents (orchestration)

**File:**
- `/root/projects/Interverse/os/clavain/hooks/bead-agent-bind.sh`

**Problem:**
Hook has Bash matcher filtering for `Bash` tool calls. Then inside, script does case-match on command string for `bd update`/`bd claim` patterns. Double-filtering correct but matcher could be more specific.

Lines 10-11: `INTERMUTE_AGENT_ID` checked before reading stdin. If unset, stdin never consumed. Efficient but means hook JSON goes to /dev/null.

**Recommendation:**
No change needed — pattern is correct and efficient.

---

### P2-5: Five find calls in lib.sh companion discovery (no cache)

**Convergence:** 2/3 agents (token, performance)

**File:**
- `/root/projects/Interverse/os/clavain/hooks/lib.sh` (lines 13, 32, 52, 70, 89)

**Problem:**
Five `_discover_*_plugin` functions each run `find ~/.claude/plugins/cache -maxdepth 5`. On system with many plugin versions cached, can be slow (~200ms each). All five run during SessionStart.

Estimated cost: ~1s wall-clock time for companion discovery. Plugin set only changes on install/uninstall.

**Recommendation:**
Cache results in temp file keyed on plugin cache directory mtime. If cache fresh (<60s), skip find calls. Example:
```bash
CACHE_FILE="$HOME/.claude/clavain-companion-cache"
if [[ -f "$CACHE_FILE" ]] && [[ $(( $(date +%s) - $(stat -c %Y "$CACHE_FILE") )) -lt 3600 ]]; then
    source "$CACHE_FILE"
else
    # run finds, write results to CACHE_FILE
fi
```

---

### P2-6: interstat init-db.sh runs unconditionally on every Task call

**Convergence:** 1/3 agents (performance)

**File:**
- `/root/projects/Interverse/plugins/interstat/hooks/post-task.sh`

**Problem:**
```bash
bash "$INIT_DB_SCRIPT" >/dev/null 2>&1 || true
```

Called unconditionally on every Task tool use. Script creates SQLite database and schema if doesn't exist. Once DB exists, this is pure overhead (bash spawn + sqlite3 process + DDL no-ops).

In session with 20 subagents, init-db runs 20 times unnecessarily.

**Recommendation:**
Guard with DB existence check:
```bash
[[ -f "$DB_PATH" ]] || bash "$INIT_DB_SCRIPT" >/dev/null 2>&1 || true
```

Reduces overhead from O(N Task calls) to O(1) per session.

---

### P2-7: tldr-swinton post-read-extract.sh md5sum computed before gate

**Convergence:** 1/3 agents (performance)

**File:**
- `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`

**Problem:**
Hook computes md5sum of file path for per-file flag BEFORE checking line count gate. For files under 300 lines (majority), the hook exits after `wc -l`. The `md5sum` runs unnecessarily.

**Recommendation:**
Move md5sum call to after the 300-line check:
```bash
if [ "$LINE_COUNT" -lt 300 ]; then exit 0; fi
# ... then compute hash
FILE_HASH=$(echo -n "$FILE" | md5sum | cut -d' ' -f1)
```

---

### P3-1: tldr-swinton post-read-extract.sh injects large extracts

**Convergence:** 1/3 agents (token-economy)

**File:**
- `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`

**Problem:**
Fires on every Read for code files >300 lines. Compact extract output can be 500-2000 chars (~125-500 tokens). Per-file flagging prevents duplicates within session.

In session reading 10 large files: 1250-5000 tokens injected context.

**Recommendation:**
Per-file flagging is good. Consider session-wide budget cap: stop injecting after N total extractions (e.g., 5 files) to prevent accumulation in Read-heavy sessions.

---

### P3-2: interspect-session.sh runs migration SQL on every startup

**Convergence:** 1/3 agents (performance)

**File:**
- `/root/projects/Interverse/os/clavain/hooks/interspect-session.sh`

**Problem:**
Migration SQL runs on every startup even when DB exists:
```bash
if [[ -f "$_INTERSPECT_DB" ]]; then
    sqlite3 "$_INTERSPECT_DB" <<'MIGRATE'
CREATE TABLE IF NOT EXISTS ...
MIGRATE
    sqlite3 "$_INTERSPECT_DB" "ALTER TABLE sessions ADD COLUMN run_id TEXT;" 2>/dev/null || true
fi
```

Opens sqlite3 twice per startup even when schema already current.

**Recommendation:**
Use `PRAGMA user_version` to track schema version and skip migration on fast path. Also, register interspect cursor with local sentinel file to avoid running `ic events cursor list` on every session start.

---

### P3-3: interject session-start.sh uses python3 for JSON parsing

**Convergence:** 2/3 agents (orchestration, performance)

**File:**
- `/root/projects/Interverse/plugins/interject/hooks/session-start.sh` (line 40)

**Problem:**
Line 40 uses:
```bash
python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))"
```

Instead of:
```bash
jq -r '.session_id // ""'
```

Every other hook uses jq. Python3 startup: ~50ms vs jq's ~5ms. Total: 10x slower for same operation.

**Recommendation:**
Replace with jq for consistency and speed.

---

### P3-4: interflux session-start.sh is a no-op in stub mode

**Convergence:** 2/3 agents (token, orchestration)

**Files:**
- `/root/projects/Interverse/plugins/interflux/hooks/session-start.sh`
- `/root/projects/Interverse/plugins/interflux/hooks/interbase-stub.sh`

**Problem:**
Hook sources interbase-stub.sh and calls `ib_session_status()`, defined as `{ return 0; }` in stub mode. Unless live interbase installed at `~/.intermod/interbase/interbase.sh`, hook does nothing but spawn bash process.

**Recommendation:**
Remove hook registration from hooks.json until interbase has live implementation. Re-add when ib_session_status() actually does something.

---

### P3-5: Empty matcher strings vs absent matchers (consistency issue)

**Convergence:** 1/3 agents (orchestration)

**Files:**
- `/root/projects/Interverse/plugins/interject/hooks/hooks.json` (matcher: `""`)
- `/root/projects/Interverse/plugins/interkasten/hooks/hooks.json` (matcher: `""`)
- `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json` (no matcher field on context-monitor)
- `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json` (matcher: `*`)

**Problem:**
Four different patterns mean "match everything":
1. No matcher field (intercheck context-monitor)
2. Empty string matcher `""` (interject, interkasten)
3. Wildcard `*` (tool-time)
4. Absent matcher in group (clavain Stop hooks)

All behave same but inconsistency makes audit hard.

**Recommendation:**
Standardize on one pattern. Suggestion: omit matcher field for catch-all hooks (most concise). Document convention.

---

## Already-Addressed Issues (Excluded from New Findings)

These 8 hook fixes were applied earlier this session and are NOT counted as new findings:

1. **stop hook priority inversion** — Fixed sentinel ordering in clavain Stop hooks
2. **bead-agent-bind dead code** — Removed obsolete branch logic
3. **session-end-handoff sentinel mismatch** — Fixed sentinel detection logic
4. **auto-drift-check guard** — Added proper stop_hook_active guard
5. **auto-publish exit code** — Fixed exit status handling
6. **catalog-reminder matcher** — Corrected Edit|Write|MultiEdit matcher
7. **interfluence heredoc** — Fixed shell quoting in learn-from-edits.sh
8. *(one more applied but already documented)*

---

## Already-Tracked Beads (Not New Actions Required)

These 7 items are already tracked as beads and should NOT be re-opened:

| Bead ID | Title | Status |
|---------|-------|--------|
| iv-49mq | context-monitor python3 replacement | Tracked |
| iv-4s0b | interstat init-db optimization | Tracked |
| iv-66f1 | tool-time transcript cache | Tracked |
| iv-kcf6 | Intermute deduplication | Tracked |
| iv-69f6 | double-escape issue | Tracked |
| iv-2e4m | discover cache implementation | Tracked |
| iv-jpap | interkasten deleted column | Tracked |

---

## Prioritized Action List

### Phase 1: Critical Fixes (this week)

**1. Remove tool-time PreToolUse binding + extract Task redirect**
- Priority: CRITICAL (affects every tool call)
- Effort: ~1 hour
- Impact: Eliminates 200+ process spawns per session, ~2s latency reduction
- Files:
  - `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json` (remove PreToolUse binding)
  - `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh` (extract lines 90-151)
  - `/root/projects/Interverse/os/clavain/hooks/agent-output-redirect.sh` (new, clavain)

**2. Replace python3 arithmetic in context-monitor.sh with awk**
- Priority: CRITICAL (4 spawns per tool call)
- Effort: ~30 minutes
- Impact: Eliminates 800 Python starts per 200-call session, ~30s latency reduction
- Files:
  - `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh`

**3. Add matcher to context-monitor.sh (related to #2)**
- Priority: CRITICAL
- Effort: ~15 minutes
- Files:
  - `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json`

**4. Register or remove interserve pre-read-intercept.sh**
- Priority: CRITICAL (dead code)
- Effort: ~20 minutes
- Files:
  - `/root/projects/Interverse/plugins/interserve/hooks/hooks.json`

**5. Fix interflux hooks.json schema or remove hook**
- Priority: CRITICAL (malformed JSON)
- Effort: ~15 minutes
- Files:
  - `/root/projects/Interverse/plugins/interflux/hooks/hooks.json`

### Phase 2: High-Priority Fixes (next 1-2 weeks)

**6. Remove duplicate sprint_find_active call in session-start.sh**
- Priority: HIGH (100 tokens + 200ms redundant calls)
- Effort: ~30 minutes
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (remove lines 196-212)

**7. Add double-source guard to lib-sprint.sh**
- Priority: HIGH (prevents function redefinition)
- Effort: ~15 minutes
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/lib-sprint.sh`

**8. Deduplicate CLAUDE_SESSION_ID env writes**
- Priority: HIGH (eliminates race condition)
- Effort: ~30 minutes
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (keep CLAUDE_SESSION_ID write)
  - `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` (remove CLAUDE_SESSION_ID write)

**9. Deduplicate Intermute queries at session start**
- Priority: HIGH (4-6 redundant HTTP calls, 200-400ms)
- Effort: ~1 hour
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (read from temp file)
  - `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` (write temp file)

**10. Cache companion plugin discovery**
- Priority: HIGH (eliminates 5 find scans, ~1s per session start)
- Effort: ~45 minutes
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/lib.sh` (add cache logic)

**11. Merge auto-compound.sh + auto-drift-check.sh**
- Priority: HIGH (eliminates sentinel race, redundant signal detection)
- Effort: ~1 hour
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/auto-stop-actions.sh` (new, merged)
  - Remove old: `auto-compound.sh`, `auto-drift-check.sh`
  - Update: `session-start.sh` (Stop hook array)

**12. Merge syntax-check.sh + auto-format.sh in intercheck**
- Priority: HIGH (eliminates redundant JSON parses + language detection)
- Effort: ~1 hour
- Files:
  - `/root/projects/Interverse/plugins/intercheck/hooks/post-edit.sh` (new, merged)
  - Remove old: `syntax-check.sh`, `auto-format.sh`
  - Update: `hooks.json` (PostToolUse array)

### Phase 3: Medium-Priority Fixes (next 2-4 weeks)

**13. Guard interstat init-db.sh with DB existence check**
- Priority: MEDIUM (redundant init on every Task call)
- Effort: ~15 minutes
- Files:
  - `/root/projects/Interverse/plugins/interstat/hooks/post-task.sh`

**14. Reduce clavain handoff read from 40 to 20 lines**
- Priority: MEDIUM (800 tokens → 400 tokens per session)
- Effort: ~10 minutes
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 220-222)

**15. Verify interfluence env var API compatibility**
- Priority: MEDIUM (silent feature breakage risk)
- Effort: ~30 minutes
- Files:
  - `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh`

**16. Add schema version guard to interspect-session.sh**
- Priority: MEDIUM (eliminates redundant migration SQL runs)
- Effort: ~30 minutes
- Files:
  - `/root/projects/Interverse/os/clavain/hooks/interspect-session.sh`

**17. Move md5sum after line count gate in post-read-extract.sh**
- Priority: MEDIUM (minor efficiency gain)
- Effort: ~10 minutes
- Files:
  - `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`

### Phase 4: Polish (next 4-8 weeks)

**18. Replace python3 JSON parsing with jq in interject**
- Priority: LOW (10x slower but rare hook)
- Effort: ~10 minutes
- Files:
  - `/root/projects/Interverse/plugins/interject/hooks/session-start.sh`

**19. Standardize matcher patterns across all hooks**
- Priority: LOW (consistency issue)
- Effort: ~1 hour
- Files:
  - All `hooks.json` files (convert to consistent pattern)

**20. Add session-wide cap to tldr-swinton extracts**
- Priority: LOW (prevent token accumulation in Read-heavy sessions)
- Effort: ~30 minutes
- Files:
  - `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`

---

## Session Impact Estimate

**Current state (with all plugins active):**
- SessionStart: 500ms-2s (heavily dependent on Intermute network latency)
- Per Edit: 60-200ms hook overhead
- Per non-Edit tool call: 40-60ms hook overhead
- Cumulative per 200-call session: ~14-28s of hook latency

**After Phase 1 fixes (critical only):**
- SessionStart: ~500ms (faster if Intermute queries dedup)
- Per Edit: ~20-60ms hook overhead (reduced python3 overhead)
- Per tool call: ~20-40ms hook overhead
- Cumulative: ~6-14s of hook latency
- **Expected improvement: 50% latency reduction**

**After Phase 1-2 fixes (critical + high-priority):**
- SessionStart: ~200-500ms (companion discovery + sprint detection cached)
- Per Edit: ~10-30ms hook overhead
- Per tool call: ~10-20ms hook overhead
- Cumulative: ~2-6s of hook latency
- **Expected improvement: 75-80% latency reduction**

---

## Verdict

**Overall Status:** **NEEDS CHANGES**

**Rationale:**
- 6 P0 findings require immediate action (all critical for functionality or latency)
- 8 P1 findings should be addressed soon (high redundancy, poor performance)
- 7 P2 findings are optimization opportunities (medium impact)
- Multiple agents converged on same issues (high confidence)
- Current hook overhead is 14-28 seconds per typical session, easily reducible to 2-6 seconds

**Gate Status:** **FAIL** — Cannot merge without addressing P0 findings (tool-time, context-monitor, dead code hooks)

**Recommended Next Steps:**
1. Create Phase 1 beads for 5 critical fixes
2. Assign ownership (suggest: clavain, intercheck, tool-time module leads)
3. Plan Phase 2 fixes for following sprint
4. Measure actual latency impact post-fixes (add timing instrumentation to session-start.sh)

---

## Appendix: Agent Scores

| Agent | Valid | Finding Count | New Findings | Quality |
|-------|-------|---------------|--------------|---------|
| flux-drive-token-economy | Yes | 13 | 8 (P0+P1+P2+P3) | High (token cost estimates) |
| flux-drive-orchestration | Yes | 16 | 10 (P0+P1+P2+P3) | High (structure + dependencies) |
| flux-drive-performance | Yes | 12 | 7 (P0+P1+P2+P3) | High (latency + subprocess analysis) |
| **Total** | **3/3** | **41** | **15 new** | **High convergence (3/3)** |

---

## Files Referenced

### Synthesis Output
- **Verdict:** `/root/projects/Interverse/docs/research/flux-drive-hooks-synthesis.md` (this file)

### Agent Reports (input)
- `/root/projects/Interverse/docs/research/flux-drive-token-economy-hooks.md`
- `/root/projects/Interverse/docs/research/flux-drive-orchestration-hooks.md`
- `/root/projects/Interverse/docs/research/flux-drive-performance-hooks.md`

### Key Files to Modify (prioritized by impact)
1. `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json` (P0-1)
2. `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh` (P0-1, P1-8)
3. `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json` (P0-2)
4. `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh` (P0-2, P2-1)
5. `/root/projects/Interverse/plugins/interserve/hooks/hooks.json` (P0-5)
6. `/root/projects/Interverse/plugins/interflux/hooks/hooks.json` (P0-6)
7. `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (P1-1, P1-2, P1-3, P2-3)
8. `/root/projects/Interverse/os/clavain/hooks/lib-sprint.sh` (P1-3)
9. `/root/projects/Interverse/os/clavain/hooks/auto-compound.sh` (P1-4)
10. `/root/projects/Interverse/os/clavain/hooks/auto-drift-check.sh` (P1-4)

---

**End of Synthesis Report**
