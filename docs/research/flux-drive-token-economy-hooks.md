# Flux-Drive Token Economy: Hooks Audit

**Date:** 2026-02-20
**Scope:** All Claude Code hooks across the Interverse monorepo
**Methodology:** Static analysis of hooks.json configs and hook scripts, estimating token cost from output character counts (1 token ~ 4 chars)

---

## Executive Summary

The Interverse ecosystem runs **12 plugins with hook registrations**, totaling **30+ individual hook bindings** across SessionStart, PreToolUse, PostToolUse, Stop, and SessionEnd events. The biggest token economy issue is not any single hook being oversized -- Clavain's session-start already has a 6000-char budget cap with priority-based shedding. The problems are:

1. **Cross-plugin accumulation**: SessionStart hooks from 7 plugins fire together, with no awareness of each other's output
2. **Unconditional per-call overhead**: Two hooks fire on EVERY tool call (`intercheck/context-monitor.sh` with no matcher, `tool-time/hook.sh` with `*` matcher) -- one of which injects context at pressure thresholds but both consume execution time
3. **Duplicate sprint detection**: `session-start.sh` runs sprint_brief_scan AND independently re-detects active sprints (lines 196-212), duplicating work already done inside sprint_brief_scan (lines 347-365)
4. **Silent hooks that still cost**: Several hooks read stdin, parse JSON, hit SQLite, but produce no output -- they still cost wall-clock time against hook timeouts

---

## P0: Critical Findings

### P0-1: intercheck/context-monitor.sh fires on EVERY PostToolUse with no matcher

**File:** `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json` (line 3-12)
**File:** `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh`

The hooks.json registration has no `matcher` field:
```json
"PostToolUse": [
  {
    "hooks": [{ "type": "command", "command": "...context-monitor.sh", "timeout": 5 }]
  }
]
```

This means it fires on **every single tool call** -- Read, Edit, Grep, Glob, Bash, Write, Task, WebSearch, WebFetch, etc. Each invocation:
- Reads stdin (JSON parse)
- Calls `jq` 3 times for field extraction
- Reads/writes a JSON state file via `_ic_read_state`/`_ic_write_state`
- Calls `python3` 2-3 times for float arithmetic (decay, pressure update, threshold check)
- Calls `date +%s`

Even when it produces no output (Green zone, the common case), it adds **~50-100ms wall-clock overhead per tool call**. Over a typical 80-call session, that is 4-8 seconds of cumulative hook latency. When it does output (Yellow/Orange/Red), the messages are 80-150 chars (~20-40 tokens each), which is fine -- the problem is the unconditional execution cost.

**Estimated cost:** 0 tokens (Green), 20-40 tokens (Yellow/Orange/Red) for output. But ~8s cumulative wall-clock time per session.

**Recommendation:** Add a matcher to limit to heavy tools only: `"matcher": "Read|Grep|Task|WebFetch|WebSearch|Bash"`. The pressure model already weights these tools higher (1.5 vs 1.0), so tracking only these captures ~90% of actual context growth while skipping the 60% of calls that are Edit/Write/Glob (which add minimal context).

### P0-2: tool-time/hook.sh fires on EVERY PreToolUse AND PostToolUse with `*` matcher

**File:** `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json`
**File:** `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh`

tool-time registers on **four events** (PreToolUse, PostToolUse, SessionStart, SessionEnd), all with `*` matcher. Every tool call triggers it twice (pre + post). Each invocation:
- Reads stdin (full hook JSON)
- Calls `jq` for 7-field extraction
- Reads/writes a sequence file
- For PostToolUse: additional `jq` call to check error patterns
- Writes a JSONL line to `events.jsonl`

The hook is well-designed for data collection (no output on Pre/Post/SessionStart, only SessionEnd runs summarize), but the **PreToolUse:Task** branch (lines 95-151) injects a prompt rewrite via `updatedInput` that adds ~600 chars (~150 tokens) of "MANDATORY FIRST STEP" instructions to every Task call detected as part of a multi-agent workflow.

**Estimated cost per session:**
- Silent calls: 0 tokens output, ~30-60ms per call x 2 (pre+post) = ~5-10s wall-clock over 80 calls
- Task prompt injection: ~150 tokens per multi-agent Task dispatch

**Recommendation:**
1. Move the Task prompt injection to a **separate hook registration** with `"matcher": "Task"` instead of embedding it in the catch-all hook. This avoids the overhead of transcript scanning (5MB `tail -c`) on non-Task calls.
2. Consider splitting the analytics logger into Pre-only and Post-only registrations -- PreToolUse doesn't need error extraction, PostToolUse doesn't need the Task injection check.

---

## P1: High-Priority Findings

### P1-1: Duplicate sprint detection in clavain/session-start.sh

**File:** `/root/projects/Interverse/hub/clavain/hooks/session-start.sh` (lines 173-212)

The hook does sprint awareness in **two places**:
1. Lines 173-180: `source sprint-scan.sh` then `sprint_brief_scan()` -- which internally calls `sprint_find_active()` and generates a sprint resume hint (lines 347-365 of sprint-scan.sh)
2. Lines 196-212: Independently sources `lib-sprint.sh`, calls `sprint_find_active()` again, and builds `sprint_resume_hint`

Both produce nearly identical output ("Active sprint: {id} -- {title} (phase: {phase}, next: {step})"). The second block (lines 196-212) was likely added before sprint_brief_scan was updated to include sprint detection.

**Estimated waste:** ~100 tokens of duplicate context + ~200ms of redundant `bd`/`jq` calls.

**Recommendation:** Remove lines 196-212 entirely. The sprint_brief_scan output already includes the active sprint hint.

### P1-2: SessionStart accumulation across 7 plugins

When all plugins are active, these SessionStart hooks fire simultaneously:

| Plugin | Hook | Estimated Output (chars) | Estimated Tokens |
|--------|------|--------------------------|------------------|
| clavain | session-start.sh | 2000-6000 (budget-capped) | 500-1500 |
| clavain | interspect-session.sh | 0-200 (only on canary alert) | 0-50 |
| interlock | session-start.sh | ~300 | ~75 |
| interkasten | session-status.sh | ~80-150 | ~20-40 |
| interject | session-start.sh | 0-300 (only with discoveries) | 0-75 |
| intermux | session-start.sh | 0 (writes file, no JSON output) | 0 |
| interflux | session-start.sh | 0 (stub mode: no-op) | 0 |
| tool-time | hook.sh | 0 (SessionStart: silent) | 0 |

**Worst-case total:** ~6000 (clavain) + 300 (interlock) + 150 (interkasten) + 300 (interject) + 200 (interspect canary) = **~6950 chars = ~1740 tokens**

**Typical case:** ~3500 (clavain, most sections shed) + 300 (interlock) + 80 (interkasten) = **~3880 chars = ~970 tokens**

The clavain session-start already has a 6000-char cap, which is responsible. But it has **no awareness of the ~600+ chars injected by other plugins**. The effective total can exceed 7000 chars.

**Recommendation:** Consider a cross-plugin budget. Since clavain is the hub, its 6000-char cap should account for known companion injections (~800 chars) and reduce its own cap to 5200.

### P1-3: Handoff context can inject up to 40 lines uncapped

**File:** `/root/projects/Interverse/hub/clavain/hooks/session-start.sh` (lines 217-233)

The handoff file is read with `head -40`, which at ~80 chars/line is up to 3200 chars (~800 tokens). While the budget shedding system (lines 295-314) drops handoff_context when over budget, it only sheds at the _section_ level. If using_clavain_content (1492 bytes) + companion_context is small, the 3200-char handoff survives, consuming a large portion of the 6000-char budget.

**Recommendation:** Reduce `head -40` to `head -20` (the handoff instructions already say "10-20 lines"). Or cap handoff_content at 1500 chars (~375 tokens) with truncation.

### P1-4: interlock/pre-edit.sh does expensive inbox checks on every Edit

**File:** `/root/projects/Interverse/plugins/interlock/hooks/pre-edit.sh`

This hook fires on every `Edit` tool call. It performs:
1. Inbox check for commit notifications (lines 24-63): `curl` to intermute, `jq` parsing, potential `git pull --rebase`
2. Inbox check for release-request messages (lines 66-107): another `curl` + `jq` parsing
3. Reservation conflict check (line 120): shell script invocation with `curl`
4. Auto-reserve (lines 168-178): `curl POST`

The inbox checks use a 30-second throttle via flag files (`-mmin -0.5`), but the throttle is per-session -- on session start, both inbox checks fire on the very first Edit, adding 2-4 `curl` calls + `jq` processing.

When output IS produced, it injects advisory context:
- Pull notification: ~80 chars (~20 tokens)
- Release request advisory: variable, ~200-400 chars per request (~50-100 tokens)
- Block decision for conflict: ~200 chars (~50 tokens)

**Estimated per-call cost:** After first call, mostly fast-path (flag check + one curl for reservation). But the release-request parsing (lines 66-107) is expensive when active.

**Recommendation:** The 30s throttle is reasonable. Consider making release-request inbox checks opt-in only when `INTERLOCK_AUTO_RELEASE=1` is set -- this is already the case (line 66). No change needed, but document that this feature flag should default to off.

---

## P2: Medium-Priority Findings

### P2-1: context-monitor.sh uses python3 for float arithmetic

**File:** `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh` (lines 36, 50, 67-73)

Three `python3 -c` invocations per call for simple arithmetic:
```bash
DECAY=$(python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))")
PRESSURE=$(python3 -c "print(round(max(0, $PRESSURE - $DECAY) + $WEIGHT, 2))")
python3 -c "exit(0 if $PRESSURE > 120 else 1)"
```

Python startup is ~30-50ms each. Total: ~100-150ms per tool call just for arithmetic.

**Recommendation:** Replace with `awk` or `bc`:
```bash
DECAY=$(awk "BEGIN {printf \"%.2f\", $ELAPSED / 600.0 * 0.5}")
PRESSURE=$(awk "BEGIN {p = $PRESSURE - $DECAY; if (p<0) p=0; printf \"%.2f\", p + $WEIGHT}")
```
`awk` startup is ~1ms vs python3's ~30ms.

### P2-2: interserve-audit.sh silently logs but never injects context (by design, but note the bug)

**File:** `/root/projects/Interverse/hub/clavain/hooks/interserve-audit.sh`

This hook fires on `Edit|Write|MultiEdit|NotebookEdit` and only writes to a log file. It produces NO additionalContext output, which means violations are logged but the agent never learns about them. The task description says "NO output, bug."

**Token cost:** 0 (no output ever produced).

**Recommendation:** Either add additionalContext output for violations (so the agent can self-correct) or remove the hook and rely solely on the PreToolUse interserve/pre-read-intercept.sh for enforcement.

### P2-3: tldr-swinton post-read-extract.sh injects potentially large extract output

**File:** `/root/projects/Interverse/plugins/tldr-swinton/.claude-plugin/hooks/post-read-extract.sh`

Fires on every `Read` tool call for code files >300 lines. The compact extract output can be 500-2000 chars depending on file complexity. Per-file flagging prevents duplicates within a session.

**Estimated cost:** 125-500 tokens per unique large file read. In a session reading 10 large files, that is 1250-5000 tokens of injected context.

**Recommendation:** The per-file flagging is good. Consider adding a session-wide budget cap: stop injecting after N total extractions (e.g., 5 files) to prevent accumulation in Read-heavy sessions.

### P2-4: Sprint scan in session-start.sh sources lib-sprint.sh twice

**File:** `/root/projects/Interverse/hub/clavain/hooks/session-start.sh` (lines 175, 198)

`lib-sprint.sh` is sourced at line 198. But `sprint-scan.sh` (sourced at line 175) also sources `lib-sprint.sh` at its own line 350. Both have `2>/dev/null || true` guards but no double-source protection. The script ends up defining `sprint_find_active` and other functions twice.

**Recommendation:** Add a guard to `lib-sprint.sh` (`[[ -n "${_SPRINT_LIB_LOADED:-}" ]] && return 0`), consistent with the pattern used by `sprint-scan.sh` (which has `_SPRINT_SCAN_LOADED`).

### P2-5: Five `find` calls in lib.sh companion discovery (~200ms each)

**File:** `/root/projects/Interverse/hub/clavain/hooks/lib.sh` (lines 13, 32, 52, 70, 89)

Five `_discover_*_plugin` functions each run `find ~/.claude/plugins/cache -maxdepth 5`. On a system with many plugin versions cached, these can be slow (~200ms each). All five run during SessionStart.

**Estimated cost:** ~1s wall-clock time for companion discovery. No token output, but adds to hook latency.

**Recommendation:** Cache results in a temp file keyed on plugin cache directory mtime. If cache is fresh (<60s), skip the `find` calls.

---

## P3: Low-Priority / Informational

### P3-1: interflux session-start.sh is a no-op (stub mode)

**File:** `/root/projects/Interverse/plugins/interflux/hooks/session-start.sh`
**File:** `/root/projects/Interverse/plugins/interflux/hooks/interbase-stub.sh`

The hook sources `interbase-stub.sh` and calls `ib_session_status`, which is a no-op in stub mode (line 30: `ib_session_status() { return 0; }`). When the live interbase is present at `~/.intermod/`, it sources the live version instead.

**Token cost:** 0 (stub), unknown (live).

**Recommendation:** None -- this is well-designed graceful degradation. But the live `interbase.sh` should be audited separately if it produces output.

### P3-2: intermux session-start.sh is silent (file write only)

**File:** `/root/projects/Interverse/plugins/intermux/hooks/session-start.sh`

Writes a JSON mapping file to `/tmp/intermux-mapping-*.json`. Produces no stdout output.

**Token cost:** 0.

### P3-3: interstat post-task.sh is silent (SQLite write only)

**File:** `/root/projects/Interverse/plugins/interstat/hooks/post-task.sh`

Fires on `Task` PostToolUse. Writes to SQLite, no stdout. On SQLite failure, writes to JSONL fallback. Still no stdout.

**Token cost:** 0.

### P3-4: interfluence learn-from-edits.sh is silent (log write only)

**File:** `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh`

Fires on `Edit` PostToolUse. Writes diff to `learnings-raw.log`. No stdout.

**Token cost:** 0.

### P3-5: interspect hooks are silent (except canary alerts)

- `interspect-session.sh` (SessionStart): Silent unless canary alerts exist (~200 chars).
- `interspect-evidence.sh` (PostToolUse:Task): Silent always.
- `interspect-session-end.sh` (Stop): Silent always.

**Token cost:** 0 typical, ~50 tokens rare canary case.

### P3-6: interserve hooks.json is empty

**File:** `/root/projects/Interverse/plugins/interserve/hooks/hooks.json`

Contains `{"hooks": {}}` -- no hook registrations. The pre-read-intercept.sh is registered through a DIFFERENT mechanism (likely Clavain or another plugin's hooks.json). Wait -- checking the hooks.json list, interserve has an empty hooks.json. The pre-read-intercept.sh must be registered elsewhere or via the plugin.json directly.

**Recommendation:** Verify that pre-read-intercept.sh is actually registered. If the interserve plugin.json declares hooks at a non-standard path, that path should be documented.

### P3-7: interkasten setup.sh runs at SessionStart with 30s timeout

**File:** `/root/projects/Interverse/plugins/interkasten/hooks/hooks.json` (line 9)

The setup hook has a 30-second timeout, which is the highest of any hook. If the Notion API is slow, this could delay session start significantly. However, it runs before session-status.sh and is presumably for one-time setup.

**Recommendation:** Ensure setup.sh exits quickly when already set up (should be a no-op on repeat runs).

---

## Summary Table: All Hooks with Token Cost

### SessionStart Hooks (fire once per session)

| Plugin | Hook Script | Output? | Est. Tokens | Notes |
|--------|------------|---------|-------------|-------|
| clavain | session-start.sh | Yes (additionalContext) | 500-1500 | Budget-capped at 6000 chars; priority shedding |
| clavain | interspect-session.sh | Rare (canary alert) | 0-50 | Only fires when canary is in alert state |
| interlock | session-start.sh | Yes (additionalContext) | ~75 | Agent registration + coordination summary |
| interkasten | setup.sh | No | 0 | Side-effect only (setup) |
| interkasten | session-status.sh | Yes (additionalContext) | 20-40 | Brief one-line status |
| interject | session-start.sh | Conditional | 0-75 | Only if high-relevance discoveries exist |
| intermux | session-start.sh | No | 0 | Writes mapping file only |
| interflux | session-start.sh | No (stub) | 0 | No-op in stub mode |
| tool-time | hook.sh | No | 0 | Silent on SessionStart |

**SessionStart total:** ~600-1740 tokens worst case, ~600-1000 typical.

### PreToolUse Hooks (fire before tool execution)

| Plugin | Hook Script | Matcher | Output? | Est. Tokens/Call | Notes |
|--------|------------|---------|---------|------------------|-------|
| interlock | pre-edit.sh | Edit | Conditional | 0-100 | Block on conflict, advisory on inbox |
| interserve | pre-read-intercept.sh | Read (?) | Conditional | 0-50 | Block on large code files |
| tldr-swinton | pre-serena-edit.sh | Serena edits | Conditional | 50-200 | Caller analysis before refactoring |
| tool-time | hook.sh | `*` (all) | Conditional | 0-150 | Silent unless Task + multi-agent detected |

### PostToolUse Hooks (fire after tool execution)

| Plugin | Hook Script | Matcher | Output? | Est. Tokens/Call | Notes |
|--------|------------|---------|---------|------------------|-------|
| intercheck | context-monitor.sh | **None (all)** | Conditional | 0-40 | **P0: fires every call** |
| intercheck | syntax-check.sh | Edit/Write/NB | Conditional | 0-80 | Only on syntax error |
| intercheck | auto-format.sh | Edit/Write/NB | No | 0 | Silent always |
| clavain | interserve-audit.sh | Edit/Write/ME | No | 0 | Logs only, no output (bug?) |
| clavain | auto-publish.sh | Bash | Conditional | 0-50 | Only on git push in plugin repos |
| clavain | bead-agent-bind.sh | Bash | Conditional | 0-30 | Only on bd update/claim with agent conflict |
| clavain | catalog-reminder.sh | Edit/Write/ME | Conditional | ~25 | Once per session, on component file change |
| clavain | interspect-evidence.sh | Task | No | 0 | Silent always (SQLite write) |
| interfluence | learn-from-edits.sh | Edit | No | 0 | Silent always (log write) |
| tldr-swinton | post-read-extract.sh | Read | Conditional | 0-500 | Per-file, on code files >300 lines |
| interstat | post-task.sh | Task | No | 0 | Silent always (SQLite write) |
| tool-time | hook.sh | `*` (all) | No | 0 | Silent on PostToolUse (JSONL write) |

### Stop Hooks (fire when session is about to end)

| Plugin | Hook Script | Output? | Est. Tokens | Notes |
|--------|------------|---------|-------------|-------|
| clavain | session-handoff.sh | Conditional (block) | 0-300 | Blocks if uncommitted work detected |
| clavain | auto-compound.sh | Conditional (block) | 0-200 | Blocks if compoundable signals detected |
| clavain | auto-drift-check.sh | Conditional (block) | 0-150 | Blocks if shipped-work signals detected |
| clavain | interspect-session-end.sh | No | 0 | Silent (SQLite write) |
| interlock | stop.sh | Unknown | Unknown | Not reviewed in detail |
| interkasten | session-end-warn.sh | Unknown | Unknown | Not reviewed in detail |

### SessionEnd Hooks (fire after session ends)

| Plugin | Hook Script | Output? | Notes |
|--------|------------|---------|-------|
| clavain | dotfiles-sync.sh | No | Async, no context impact |
| clavain | session-end-handoff.sh | No | Async, no context impact |
| interstat | session-end.sh | No | Runs summarize.py + upload.py |
| tool-time | hook.sh | No | Runs summarize.py + upload.py |

---

## Per-Session Token Budget Estimate

Assuming a typical 80-tool-call session with 10 file reads, 20 edits, and 2 Task dispatches:

| Source | Tokens |
|--------|--------|
| SessionStart (all plugins) | ~1000 |
| context-monitor warnings (if Yellow+) | ~40 |
| syntax-check errors (2 errors) | ~160 |
| tldrs extract injections (5 files) | ~1500 |
| interlock pre-edit advisories | ~50 |
| catalog-reminder (once) | ~25 |
| tool-time Task injection (2 Tasks) | ~300 |
| Stop hook block reasons | ~300 |
| **Total injected by hooks** | **~3375** |

This is within practical limits (~200k token context window) but represents a non-trivial baseline. In a heavy multi-agent session with many file reads, the tldrs extracts alone could reach 5000+ tokens.

---

## Prioritized Recommendations

1. **P0: Add matcher to intercheck/context-monitor.sh** -- reduce from every-call to heavy-call-only
2. **P0: Split tool-time/hook.sh Task injection** into a separate matcher-specific hook
3. **P1: Remove duplicate sprint detection** in clavain/session-start.sh (lines 196-212)
4. **P1: Reduce clavain session-start budget cap** from 6000 to 5200 to account for companion injections
5. **P1: Reduce handoff read** from 40 lines to 20 lines
6. **P2: Replace python3 arithmetic** with awk in context-monitor.sh
7. **P2: Add session-wide cap to tldrs extracts** (max 5 files per session)
8. **P2: Cache companion discovery results** in lib.sh
9. **P2: Add double-source guard** to lib-sprint.sh
10. **P3: Add additionalContext output** to interserve-audit.sh for violations, or remove hook
