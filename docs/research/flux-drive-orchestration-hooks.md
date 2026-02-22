# Flux-Drive Orchestration Hooks Review

**Date:** 2026-02-20
**Scope:** All Claude Code hooks across the Interverse monorepo (12 plugins, 33 registered hooks, 34 scripts)
**Reviewer:** Claude Opus 4.6

---

## Executive Summary

The Interverse hook ecosystem has grown organically across 12 plugins into 33 registered hook bindings executing 34 distinct scripts. The review identified **6 P0 findings** (immediate action needed), **8 P1 findings** (should fix soon), **5 P2 findings** (improvement opportunities), and **3 P3 findings** (minor polish). The most critical issues are:

1. **tool-time fires on every single tool call** with `*` matchers across 4 event types -- the highest-cost hook in the ecosystem
2. **intercheck context-monitor has no matcher** and fires on every PostToolUse, spawning python3 for float arithmetic each time
3. **Three plugins independently write CLAUDE_SESSION_ID** to the env file on SessionStart
4. **Two hooks (interserve-audit.sh and intercheck syntax-check.sh) fire on overlapping Edit/Write matchers** and both inspect file paths
5. **Clavain and interlock both query Intermute for agent/reservation data** at session start
6. **interserve pre-read-intercept.sh exists but is not registered** in any hooks.json

---

## Hook Firing Matrix

### SessionStart Hooks

| Plugin | Script | Matcher | Async | Timeout | Notes |
|--------|--------|---------|-------|---------|-------|
| clavain | session-start.sh | `startup\|resume\|clear\|compact` | yes | - | Heavy: 325 lines, companion discovery, Intermute queries, sprint scan, beads health |
| clavain | interspect-session.sh | `startup\|resume\|clear\|compact` | yes | - | SQLite insert, ic run lookup, canary check |
| interlock | session-start.sh | `startup\|resume\|clear\|compact` | yes | - | Intermute registration, git index isolation, writes CLAUDE_SESSION_ID |
| intermux | session-start.sh | `startup\|resume\|clear\|compact` | yes | - | Writes tmux-agent mapping file |
| interject | session-start.sh | `""` (empty = all) | no | - | SQLite query for high-relevance discoveries |
| interkasten | setup.sh | `""` (empty = all) | no | 30 | npm install + tsc build (first-time only) |
| interkasten | session-status.sh | `""` (empty = all) | no | 5 | SQLite queries for project count, WAL, conflicts |
| tool-time | hook.sh | `*` | no | 5 | JSONL event logging |
| interflux | session-start.sh | none | no | - | Sources interbase, calls ib_session_status (no-op in stub mode) |

**Total SessionStart hooks: 9** (all fire on every session start)

### PreToolUse Hooks

| Plugin | Script | Matcher | Timeout | Notes |
|--------|--------|---------|---------|-------|
| interlock | pre-edit.sh | `Edit` | 5 | Conflict check + auto-reserve via Intermute API |
| tldr-swinton | pre-serena-edit.sh | `mcp__plugin_serena_serena__replace_symbol_body` | 8 | Caller analysis before Serena edits |
| tldr-swinton | pre-serena-edit.sh | `mcp__plugin_serena_serena__rename_symbol` | 8 | Caller analysis before Serena renames |
| tool-time | hook.sh | `*` | 5 | JSONL event logging |

**Total PreToolUse hooks: 4** (tool-time fires on EVERY tool call)

### PostToolUse Hooks

| Plugin | Script | Matcher | Timeout | Notes |
|--------|--------|---------|---------|-------|
| **intercheck** | **context-monitor.sh** | **NONE** | **5** | **Fires on EVERY tool call -- no matcher** |
| intercheck | syntax-check.sh | `Edit\|Write\|NotebookEdit` | 5 | Language-specific syntax validation |
| intercheck | auto-format.sh | `Edit\|Write\|NotebookEdit` | 10 | Language-specific formatting |
| clavain | interserve-audit.sh | `Edit\|Write\|MultiEdit\|NotebookEdit` | 5 | Interserve mode violation logging |
| clavain | catalog-reminder.sh | `Edit\|Write\|MultiEdit` | 5 | Catalog regen reminder |
| clavain | auto-publish.sh | `Bash` | 15 | Auto-publish on git push |
| clavain | bead-agent-bind.sh | `Bash` | 5 | Bind agent identity on bd claim |
| clavain | interspect-evidence.sh | `Task` | 5 | Record agent dispatch in SQLite |
| interfluence | learn-from-edits.sh | `Edit` | 5 | Log edit diffs for voice learning |
| interstat | post-task.sh | `Task` | 10 | Record agent run in SQLite |
| tldr-swinton | post-read-extract.sh | `Read` | 8 | Auto-inject compact extract for large files |
| tool-time | hook.sh | `*` | 5 | JSONL event logging |

**Total PostToolUse hooks: 12** (2 fire on every tool call: context-monitor, tool-time)

### Stop Hooks

| Plugin | Script | Matcher | Timeout | Notes |
|--------|--------|---------|---------|-------|
| clavain | session-handoff.sh | none | 5 | Block: write HANDOFF.md if dirty tree |
| clavain | auto-compound.sh | none | 5 | Block: trigger /compound on signal detection |
| clavain | auto-drift-check.sh | none | 5 | Block: trigger /interwatch:watch on signals |
| clavain | interspect-session-end.sh | none | 5 | SQLite update + canary evaluation |
| interlock | stop.sh | none | 10 | Release all reservations |
| interkasten | session-end-warn.sh | `""` | 5 | Warn about pending WAL ops |

**Total Stop hooks: 6** (all fire)

### SessionEnd Hooks

| Plugin | Script | Matcher | Timeout | Notes |
|--------|--------|---------|---------|-------|
| clavain | dotfiles-sync.sh | none | - (async) | Push dotfiles to GitHub |
| clavain | session-end-handoff.sh | none | - (async) | Backup handoff if Stop didn't fire |
| interstat | session-end.sh | none | 15 | JSONL parse + token backfill |
| tool-time | hook.sh | `*` | 10 | JSONL summarize + upload |

**Total SessionEnd hooks: 4**

### Setup Hooks

| Plugin | Script | Matcher | Timeout | Notes |
|--------|--------|---------|---------|-------|
| tldr-swinton | setup.sh | none | 10 | Cache warming |

### Grand Total: 36 hook invocations across 6 event types

---

## Findings

### P0 -- Critical (fix immediately)

#### P0-1: tool-time fires on ALL 4 event types with `*` matcher

**Files:**
- `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json` (lines 3-51)
- `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh`

**Problem:** tool-time registers `*` matchers on `PreToolUse`, `PostToolUse`, `SessionStart`, and `SessionEnd`. This means **every single tool call** spawns two processes for tool-time (pre + post), plus one each at session start/end. For a typical session with 200 tool calls, that is 400+ process spawns just for event logging. Each spawn reads stdin, runs jq, manages a sequence file, and appends a JSONL line.

**Cost:** ~10ms per invocation x 400+ calls = ~4 seconds of cumulative latency per session. More importantly, the PreToolUse hook adds latency to every user-facing tool call.

**Recommendation:**
- Remove the `PreToolUse` binding entirely. PostToolUse already captures the tool name, timing can be reconstructed from timestamps.
- If PreToolUse is needed for the agent-output-redirect feature (lines 94-151), split that into a separate hook with a `Task` matcher -- it only activates on Task calls anyway.
- Change the `SessionStart` matcher from `*` to a specific matcher or remove it (the SessionEnd handler already summarizes).

---

#### P0-2: intercheck context-monitor has no matcher -- fires on every PostToolUse

**Files:**
- `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json` (lines 3-12)
- `/root/projects/Interverse/plugins/intercheck/hooks/context-monitor.sh`

**Problem:** The context-monitor hook has no `matcher` field in its hooks.json entry. This means it fires on every PostToolUse event, regardless of tool type. Every invocation:
1. Reads stdin (jq parse)
2. Reads/writes a state file (JSON parse + write)
3. Spawns python3 TWICE for float arithmetic (time decay + pressure update, lines 36 and 50)
4. Conditionally spawns python3 again for threshold comparison (lines 67-72)

That is 2-4 python3 invocations per tool call, purely for context tracking that produces no output 95%+ of the time (only outputs at yellow/orange/red thresholds).

**Cost:** ~30-50ms per tool call (jq + 2-3 python3 spawns). Over 200 calls = 6-10 seconds.

**Recommendation:**
- Add a matcher to skip tools that barely contribute to context pressure. At minimum, exclude `Skill` and lightweight tools.
- Replace python3 float arithmetic with bash integer arithmetic (multiply by 100 to avoid floats: pressure 6000 instead of 60.00).
- Consider sampling: only update state every Nth call and extrapolate.

---

#### P0-3: Three plugins independently write CLAUDE_SESSION_ID to env file

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 21-26)
- `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` (lines 18-19)
- (intercheck reads session_id from hook JSON directly, but the env var is written twice)

**Problem:** Both clavain and interlock session-start hooks write `export CLAUDE_SESSION_ID=...` to `$CLAUDE_ENV_FILE`. Since both run async, there is a race condition where the second write might overwrite the first (although both write the same value, it is wasteful disk I/O and creates append ordering issues if CLAUDE_ENV_FILE has other content).

**Recommendation:** Designate one canonical plugin (clavain, since it always loads) as the CLAUDE_SESSION_ID exporter. Interlock should read it from the env var instead of re-writing it.

---

#### P0-4: Clavain and interlock both query Intermute for agents/reservations at session start

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh` (lines 100-132)
- `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` (lines 37-38, delegates to interlock-register.sh)

**Problem:** Clavain's session-start.sh makes 3 HTTP calls to Intermute (health check, agents list, reservations list) and caches them in shell variables. Interlock's session-start.sh also calls Intermute to register the agent (which returns agent count). These run in parallel (both are async) but fetch overlapping data. The clavain hook even caches `_INTERMUTE_AGENTS_CACHE` and `_INTERMUTE_RESERVATIONS_CACHE`, but these shell variables are not shared across process boundaries -- they only exist within clavain's session-start.sh process.

**Cost:** 4-6 redundant HTTP calls to Intermute per session start (~200-400ms total depending on network).

**Recommendation:**
- Have interlock write the Intermute registration result to a well-known temp file (e.g., `/tmp/intermute-session-${SESSION_ID}.json`).
- Have clavain read from that file instead of making its own Intermute queries.
- Alternatively, merge the Intermute queries into a single hook that both consume.

---

#### P0-5: interserve pre-read-intercept.sh exists but is not registered

**Files:**
- `/root/projects/Interverse/plugins/interserve/hooks/hooks.json` (empty hooks object)
- `/root/projects/Interverse/plugins/interserve/hooks/pre-read-intercept.sh` (72 lines of dead code)

**Problem:** The interserve `hooks.json` has an empty hooks object (`"hooks": {}`). The `pre-read-intercept.sh` script exists but is never invoked. This script is supposed to intercept large file reads when interserve mode is ON and suggest codex_query instead. Without it registered, the interserve mode's read-interception feature is completely broken.

**Recommendation:** Either:
- Register the hook: `"PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/pre-read-intercept.sh", "timeout": 5}]}]`
- Or remove the dead script if the feature has been abandoned.

---

#### P0-6: interflux hooks.json has invalid structure

**Files:**
- `/root/projects/Interverse/plugins/interflux/hooks/hooks.json`

**Problem:** The hooks.json for interflux has a non-standard structure:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
      }
    ]
  }
}
```

The `SessionStart` array contains a command object directly, not wrapped in a `{"hooks": [...]}` group. Per the Claude Code plugin schema, each event should contain an array of groups, where each group has a `hooks` array. This may cause the hook to silently not fire, or work depending on Claude Code's schema tolerance.

Furthermore, `session-start.sh` sources `interbase-stub.sh` which calls `ib_session_status()` -- a no-op in stub mode. This hook does nothing in practice.

**Recommendation:** Either fix the schema to match the standard format and make ib_session_status() do useful work, or remove the hook entirely since it is a no-op.

---

### P1 -- Important (fix soon)

#### P1-1: Clavain session-start.sh is 325 lines and does too much

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-start.sh`

**Problem:** This single script handles:
1. Plugin cache cleanup (lines 32-48)
2. using-clavain skill injection (lines 50-53)
3. Beads health check with python3 (lines 64-75)
4. Oracle detection (line 78-80)
5. 5 companion plugin discoveries (lines 83-133) with Intermute API calls
6. Interserve mode detection (lines 136-140)
7. Upstream staleness check (lines 159-171)
8. Sprint scan sourcing (lines 174-180)
9. Discovery scan (lines 185-193)
10. Sprint bead detection (lines 196-212)
11. Handoff context loading (lines 218-233)
12. In-flight agent detection (lines 238-285)
13. Context budget management with priority shedding (lines 287-315)

Any failure in an early section could cascade. The script is hard to maintain, test, or optimize because all concerns are interleaved.

**Recommendation:** Split into a dispatcher that runs independent checks in parallel subshells and aggregates results. Each concern becomes a separate script that can be tested and timed independently.

---

#### P1-2: Two hooks fire on Edit/Write/NotebookEdit with overlapping path inspection

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/interserve-audit.sh` (matcher: `Edit|Write|MultiEdit|NotebookEdit`)
- `/root/projects/Interverse/plugins/intercheck/hooks/syntax-check.sh` (matcher: `Edit|Write|NotebookEdit`)

**Problem:** Both hooks fire on every Edit/Write/NotebookEdit. Both extract the file path from the same JSON input. interserve-audit.sh checks if the file is a code file and logs violations; syntax-check.sh checks the file extension to determine language. They independently parse the hook JSON, extract file_path, and inspect the file extension.

**Cost:** Two separate jq + file inspection processes for every edit. Both exit quickly for most files (interserve exits if toggle flag is off; syntax-check exits for unsupported languages), but the process spawn overhead remains.

**Recommendation:** If interserve mode is rarely active, the interserve-audit hook could be merged into syntax-check (which always runs) as a pre-check. Or, add an early guard in interserve-audit that checks the toggle flag before reading stdin.

---

#### P1-3: Clavain auto-compound and auto-drift-check duplicate transcript analysis

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/auto-compound.sh`
- `/root/projects/Interverse/os/clavain/hooks/auto-drift-check.sh`

**Problem:** Both Stop hooks:
1. Read the same hook JSON from stdin
2. Check `stop_hook_active`
3. Parse `session_id`
4. Claim the shared stop sentinel
5. Read the transcript file
6. Call `tail -80` on the transcript
7. Source and run `lib-signals.sh:detect_signals()`

They independently grep the same 80 lines of transcript for the same signal patterns. The only difference is the threshold (weight >= 3 for compound, >= 2 for drift) and the action (compound vs drift check).

However, they use a **shared stop sentinel** (`INTERCORE_STOP_DEDUP_SENTINEL`), which means only ONE of them can fire per stop event. This is by design (the sentinel system ensures only one Stop hook blocks). But it means auto-drift-check will never fire if auto-compound fires first, and vice versa. The order depends on Claude Code's hook execution order within the Stop array.

**Cost:** Duplicated transcript parsing (grep runs), though the sentinel prevents both from blocking simultaneously.

**Recommendation:** Merge into a single `auto-stop-actions.sh` that:
1. Detects signals once
2. If weight >= 3: trigger compound
3. Else if weight >= 2: trigger drift check
4. This eliminates the sentinel race and ensures the higher-priority action always wins.

---

#### P1-4: interspect-evidence.sh and interstat post-task.sh both fire on PostToolUse:Task

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/interspect-evidence.sh` (matcher: `Task`)
- `/root/projects/Interverse/plugins/interstat/hooks/interstat/hooks/post-task.sh` (matcher: `Task`)

**Problem:** Both hooks fire on every Task tool call. Both extract `session_id`, `subagent_type`, and `description` from the same JSON input. Both write to SQLite databases (interspect DB and interstat metrics DB respectively). They independently parse the same hook JSON.

**Distinction:** They serve different purposes (interspect is evidence/analysis, interstat is efficiency benchmarking) and write to different databases. The data overlap is high -- both record "which agent was dispatched with what description."

**Cost:** Two jq parses + two SQLite writes per Task call. Agent dispatch is relatively infrequent (typically 5-20 per session), so the absolute cost is low.

**Recommendation:** Low urgency. If consolidation is desired, create a shared "agent dispatch recorder" that writes to both databases in a single script. But given the different ownership (clavain vs interstat plugin), keeping them separate may be easier to maintain.

---

#### P1-5: session-handoff.sh checks git status, session-end-handoff.sh also checks git status

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/session-handoff.sh` (Stop hook, lines 55-60)
- `/root/projects/Interverse/os/clavain/hooks/session-end-handoff.sh` (SessionEnd hook, lines 59-63)

**Problem:** Both hooks check `git status --porcelain` / `git diff --stat` to detect uncommitted changes. session-end-handoff.sh is a safety net that only runs if session-handoff.sh didn't fire. However, the sentinel detection (lines 28-42 of session-end-handoff.sh) is complex and has multiple fallback paths (temp file check, IC sentinel check, sentinel reset). This belt-and-suspenders pattern adds code complexity.

**Recommendation:** The pattern is intentionally redundant (safety net), so the duplication is acceptable. However, simplify the sentinel detection: just check the temp file. If it exists, Stop ran. If not, run the backup. The IC sentinel path adds complexity for minimal benefit.

---

#### P1-6: interlock pre-edit.sh does git pull --rebase on inbox commit notifications

**Files:**
- `/root/projects/Interverse/plugins/interlock/hooks/pre-edit.sh` (lines 28-63)

**Problem:** This PreToolUse hook (which fires before every Edit call in multi-agent mode) checks the Intermute inbox for commit notifications and auto-pulls. `git pull --rebase` is a potentially slow and destructive operation (it can cause rebase conflicts) happening synchronously in a PreToolUse hook with a 5-second timeout. If the rebase takes longer than 5 seconds, the hook is killed mid-operation.

**Risk:** Partial rebase state left behind if hook times out. The hook does abort on conflict (line 46), but timeout kills bypass the abort.

**Recommendation:** Move the auto-pull to a less time-critical location (e.g., a dedicated background checker), or increase the timeout, or guard with a check that the pull will be fast (e.g., only pull if `git fetch --dry-run` shows changes).

---

#### P1-7: interfluence learn-from-edits.sh uses non-standard env vars

**Files:**
- `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh`

**Problem:** This hook reads `$CLAUDE_TOOL_NAME`, `$CLAUDE_TOOL_INPUT_FILE_PATH`, `$CLAUDE_TOOL_INPUT_OLD_STRING`, and `$CLAUDE_TOOL_INPUT_NEW_STRING` as environment variables (lines 13-16). However, the standard Claude Code hook protocol passes data via JSON on stdin, not env vars. These env vars may be a legacy API that no longer exists or may be set by a specific Claude Code version.

If these env vars are not set, the hook silently does nothing (exits at line 19 because TOOL_NAME is empty). This means the entire voice-learning feature may be silently broken.

**Recommendation:** Verify whether Claude Code actually sets these env vars. If not, rewrite to read from stdin JSON like all other hooks.

---

#### P1-8: tool-time hook.sh agent-output-redirect should be a separate hook

**Files:**
- `/root/projects/Interverse/plugins/tool-time/hooks/hook.sh` (lines 90-151)

**Problem:** The tool-time event logger has a dual purpose: lines 1-89 do JSONL event logging, lines 90-151 implement an "agent output redirect" feature that injects file-save instructions into Task agent prompts. These are completely unrelated features sharing a single script. The redirect feature is gated by `PreToolUse` + `Task` but the entire hook runs on every tool call.

The redirect modifies `updatedInput` to rewrite agent prompts -- this is a significant behavioral change hidden inside a "tool-time" analytics plugin. It should be in clavain or a dedicated orchestration plugin.

**Recommendation:** Extract the agent-output-redirect feature (lines 90-151) into a separate hook in clavain with a `Task` matcher on `PreToolUse`. Remove the PreToolUse binding from tool-time entirely (see P0-1).

---

### P2 -- Improvement Opportunities

#### P2-1: Redundant fast-exit guards in bead-agent-bind.sh

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/bead-agent-bind.sh`

**Problem:** The hook has a Bash matcher filtering for `Bash` tool calls. Then inside the script, it does a case-match on the command string for `bd update`/`bd claim` patterns (lines 22-28). This double-filtering is correct but the matcher could be more specific (though Claude Code matchers don't support command-level filtering, so the script-level check is necessary).

The real issue is lines 10-11: `INTERMUTE_AGENT_ID` is checked before reading stdin. If the env var is unset (no multi-agent coordination), stdin is never consumed. This is efficient but means the hook JSON goes to /dev/null, which is fine since bash hooks don't block on unconsumed stdin.

**Recommendation:** No change needed -- the pattern is correct and efficient.

---

#### P2-2: intercheck syntax-check and auto-format share file detection logic

**Files:**
- `/root/projects/Interverse/plugins/intercheck/hooks/syntax-check.sh`
- `/root/projects/Interverse/plugins/intercheck/hooks/auto-format.sh`

**Problem:** Both hooks source `intercheck-lib.sh`, call `_ic_session_id()`, `_ic_file_path()`, and `_ic_detect_lang()`. They run sequentially (syntax-check first, auto-format second per the hooks.json ordering) and independently parse the same JSON input.

**Recommendation:** Merge into a single `post-edit.sh` that does syntax check, then format, sharing the parsed input and detected language. This saves one JSON parse + one language detection per edit. Both are already within intercheck, so ownership is clear.

---

#### P2-3: Catalog-reminder uses `intercore_check_or_die` for one-per-session behavior

**Files:**
- `/root/projects/Interverse/os/clavain/hooks/catalog-reminder.sh`

**Problem:** catalog-reminder.sh sources lib-intercore.sh and uses sentinel logic just to ensure it fires once per session. It matches on `Edit|Write|MultiEdit` (every edit) to check if a "component file" was modified. The matcher cannot be narrowed further because Claude Code matchers operate on tool names, not file paths.

**Recommendation:** Acceptable pattern. The sentinel ensures only one reminder per session. No change needed.

---

#### P2-4: Multiple SessionStart hooks could share parsed JSON

**Problem:** 9 hooks fire on SessionStart. Each independently reads stdin and parses JSON. Since hooks run in separate processes, stdin is cloned for each. But each still spawns its own jq process.

**Recommendation:** Low priority. SessionStart happens once per session, so 9 jq processes is ~100ms total. Not worth optimizing unless session start latency becomes a problem.

---

#### P2-5: interkasten setup.sh runs npm install on every plugin install/update

**Files:**
- `/root/projects/Interverse/plugins/interkasten/hooks/setup.sh`

**Problem:** The Setup hook runs `npm install` and `npx tsc` if `node_modules` or `dist/index.js` is missing. This is correct behavior for a Setup hook (runs once on install/update). However, the 30-second timeout is tight for npm install on a cold cache.

**Recommendation:** Add `--cache /tmp/npm-cache` to the npm install command for faster reinstalls (matching the pattern used by interfluence's build command per CLAUDE.md).

---

### P3 -- Minor Polish

#### P3-1: interject session-start.sh uses python3 for JSON parsing instead of jq

**Files:**
- `/root/projects/Interverse/plugins/interject/hooks/session-start.sh` (line 40)

**Problem:** Line 40 uses `python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))"` instead of `jq -r '.session_id // ""'`. Every other hook uses jq. Python3 startup is ~50ms vs jq's ~5ms.

**Recommendation:** Replace with jq for consistency and speed.

---

#### P3-2: interflux session-start.sh is a no-op

**Files:**
- `/root/projects/Interverse/plugins/interflux/hooks/session-start.sh`
- `/root/projects/Interverse/plugins/interflux/hooks/interbase-stub.sh`

**Problem:** The hook sources interbase-stub.sh and calls `ib_session_status()` which is defined as `{ return 0; }` in stub mode. Unless the live interbase is installed at `~/.intermod/interbase/interbase.sh`, this hook does nothing but spawn a bash process.

**Recommendation:** Remove the hook registration from hooks.json until interbase has a live implementation. The hook can be re-added when ib_session_status() actually does something.

---

#### P3-3: Empty matcher strings vs absent matchers have unclear semantics

**Files:**
- `/root/projects/Interverse/plugins/interject/hooks/hooks.json` (matcher: `""`)
- `/root/projects/Interverse/plugins/interkasten/hooks/hooks.json` (matcher: `""`)
- `/root/projects/Interverse/plugins/intercheck/hooks/hooks.json` (no matcher field on context-monitor)
- `/root/projects/Interverse/plugins/tool-time/hooks/hooks.json` (matcher: `*`)

**Problem:** Four different patterns are used to mean "match everything":
1. No matcher field (intercheck context-monitor)
2. Empty string matcher `""` (interject, interkasten)
3. Wildcard `*` (tool-time)
4. Absent matcher in group (clavain Stop hooks)

All behave the same (match everything), but the inconsistency makes it hard to audit which hooks are intentionally catch-all vs accidentally missing a matcher.

**Recommendation:** Standardize on one pattern. Suggestion: omit the matcher field for catch-all hooks (most concise), and document this convention.

---

## Merge/Remove Candidates

| Action | Candidate | Target | Rationale | Savings |
|--------|-----------|--------|-----------|---------|
| **REMOVE** | tool-time PreToolUse binding | - | Event logging doesn't need pre-call data; the agent-redirect should move to clavain | ~200 process spawns/session |
| **REMOVE** | interflux SessionStart hook | - | No-op in stub mode | 1 process spawn/session |
| **REMOVE** | interserve pre-read-intercept.sh | - (or register it) | Dead code, never invoked | Clarity |
| **MERGE** | auto-compound.sh + auto-drift-check.sh | auto-stop-actions.sh | Same signal detection, shared sentinel race | 1 fewer process spawn, eliminates sentinel race |
| **MERGE** | syntax-check.sh + auto-format.sh | post-edit.sh (intercheck) | Same input parsing, same language detection | 1 fewer process spawn per edit |
| **EXTRACT** | tool-time hook.sh agent-redirect (lines 90-151) | clavain PreToolUse:Task hook | Feature misplaced in analytics plugin | Clarity, correct ownership |
| **NARROW** | intercheck context-monitor matcher | `Edit\|Write\|Bash\|Read\|Grep\|Task\|WebFetch\|WebSearch` | Skip Skill, NotebookEdit, Glob and other lightweight tools | ~20% fewer firings |
| **NARROW** | tool-time SessionStart matcher | specific or remove | SessionEnd already captures session data | 1 fewer process spawn |
| **DEDUPLICATE** | CLAUDE_SESSION_ID env writes | clavain only | interlock should read, not write | Remove race condition |
| **DEDUPLICATE** | Intermute queries at session start | shared temp file | clavain and interlock both query Intermute | 2-3 fewer HTTP calls |

---

## Hook Dependency Chain (Implicit Ordering)

The following implicit dependencies exist between hooks from different plugins:

1. **interlock session-start.sh** writes `INTERMUTE_AGENT_ID` to `CLAUDE_ENV_FILE` -> **interlock pre-edit.sh** reads it -> **clavain bead-agent-bind.sh** reads it
   - Risk: If interlock session-start runs AFTER clavain session-start (both async), clavain's Intermute queries may run before interlock registers the agent.
   - Mitigation: Clavain makes its own Intermute queries independently.

2. **clavain session-handoff.sh** (Stop) writes sentinel -> **clavain session-end-handoff.sh** (SessionEnd) checks sentinel
   - Safe: Stop hooks always run before SessionEnd hooks.

3. **clavain auto-compound.sh** and **auto-drift-check.sh** share the stop sentinel
   - Risk: First to claim wins; order is undefined within the Stop hooks array. Currently the hooks.json lists: session-handoff, auto-compound, auto-drift-check, interspect-session-end. Session-handoff releases the sentinel if no signals; auto-compound claims it next.
   - Actual behavior: session-handoff claims first, then releases if clean. auto-compound claims second. auto-drift-check claims third. Only one of compound/drift can block per stop.

4. **intermux session-start.sh** reads `INTERMUTE_AGENT_ID` from env -> depends on **interlock session-start.sh** having set it
   - Risk: Both are async SessionStart hooks with no ordering guarantee.
   - Mitigation: intermux writes empty string for agent_id if not set; updates later are not attempted.

---

## Cost Summary

**Per tool call (worst case, all plugins active):**
- PreToolUse: tool-time (5ms) + interlock pre-edit if Edit (variable, up to 5s with git pull)
- PostToolUse: intercheck context-monitor (30-50ms) + tool-time (5ms) + syntax-check if Edit (10-50ms) + auto-format if Edit (10-100ms) + interserve-audit if Edit (5ms) + interfluence if Edit (5ms)

**Estimated latency per Edit call: ~60-200ms in hook overhead**
**Estimated latency per non-Edit call: ~40-60ms in hook overhead** (context-monitor + tool-time pre+post)

**Per session start: 9 hooks, ~500ms-2s** (dominated by Intermute HTTP calls and npm install check)
**Per session stop: 6 hooks, ~50-200ms** (dominated by transcript analysis and Intermute cleanup)

---

## Recommendations Priority Order

1. **P0-1:** Split tool-time hook: remove PreToolUse binding, extract agent-redirect to clavain
2. **P0-2:** Add matcher to context-monitor, replace python3 with bash integer math
3. **P0-5:** Register or remove interserve pre-read-intercept.sh
4. **P0-6:** Fix interflux hooks.json schema or remove no-op hook
5. **P1-3:** Merge auto-compound + auto-drift-check into single Stop hook
6. **P0-3/P0-4:** Deduplicate SESSION_ID writes and Intermute queries
7. **P1-2:** Merge syntax-check + auto-format within intercheck
8. **P1-7:** Verify interfluence hook env var API compatibility
9. **P1-8:** Extract agent-redirect from tool-time to clavain
10. **P1-6:** Move git pull --rebase out of PreToolUse critical path
