# Research iv-36ul: Interfluence learn-from-edits.sh Hook API Analysis

**Date:** 2026-02-20  
**Concern:** The learn-from-edits.sh hook reads `CLAUDE_TOOL_NAME`, `CLAUDE_TOOL_INPUT_FILE_PATH`, etc. as environment variables. This may be a legacy API that no longer exists in current Claude Code.

**Verdict:** ✓ **BUG CONFIRMED** — The env var API is **completely broken**. Claude Code's official hook protocol (v2.1.44+) delivers **all input via stdin JSON only**. There are NO environment variables set like `CLAUDE_TOOL_NAME`, `CLAUDE_TOOL_INPUT_FILE_PATH`, `CLAUDE_TOOL_INPUT_OLD_STRING`, `CLAUDE_TOOL_INPUT_NEW_STRING`.

---

## Executive Summary

1. **interfluence hook uses a non-existent API** — expects env vars that Claude Code never sets
2. **Official hook API is stdin JSON only** — documented in `/root/projects/Interverse/services/intermute/docs/research/research-claude-code-hook-api.md` (researched 2026-02-14)
3. **All Clavain hooks follow the correct pattern** — read from stdin via `INPUT=$(cat)`, then parse with `jq`
4. **The hook currently runs silently and does nothing** — env vars are empty, the log file is never written

---

## Detailed Evidence

### 1. interfluence Hook Implementation (BROKEN)

**File:** `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh`

```bash
# Lines 13-16: Reads non-existent environment variables
TOOL_NAME="$CLAUDE_TOOL_NAME"                          # ← Does not exist
FILE_PATH="$CLAUDE_TOOL_INPUT_FILE_PATH"              # ← Does not exist
OLD_STRING="$CLAUDE_TOOL_INPUT_OLD_STRING"            # ← Does not exist
NEW_STRING="$CLAUDE_TOOL_INPUT_NEW_STRING"            # ← Does not exist
```

The hook is configured as PostToolUse on Edit:

**File:** `/root/projects/Interverse/plugins/interfluence/hooks/hooks.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/learn-from-edits.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Result:** When an Edit tool is used:
- Hook runs with empty env vars: `TOOL_NAME=""`, `FILE_PATH=""`, `OLD_STRING=""`, `NEW_STRING=""`
- Line 19 check fails: `[ "" != "Edit" ]` is false, so hook exits 0
- Learnings are never logged

---

### 2. Official Claude Code Hook API (stdin JSON)

**Source:** `/root/projects/Interverse/services/intermute/docs/research/research-claude-code-hook-api.md` (researched 2026-02-14 from official Claude Code docs)

**Key finding — Section "Environment Variables", Lines 425-439:**

```markdown
### NOT set by Claude Code

- `CLAUDE_SESSION_ID` -- **Does not exist as an env var.** The session ID is in the JSON stdin as `session_id`.
- The session ID, transcript path, CWD, etc. are all passed via **stdin JSON**, not environment variables.

### Using CLAUDE_ENV_FILE (SessionStart only)

Write `export` statements to persist environment variables...
```

**All hook input is delivered via stdin as JSON.** For PostToolUse specifically (Lines 202-233):

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "permission_mode": "default",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "file content"
  },
  "tool_response": {
    "filePath": "/path/to/file.txt",
    "success": true
  },
  "tool_use_id": "toolu_01ABC123..."
}
```

**No environment variables are set by Claude Code for hook data.** The only env var available is:
- `CLAUDE_PROJECT_DIR` — project root directory
- `CLAUDE_PLUGIN_ROOT` — plugin's root directory (for plugin hooks)

---

### 3. Ecosystem Comparison: How Other Hooks Do It Correctly

All PostToolUse hooks in Clavain follow the **stdin JSON** pattern. Examples:

#### Hook 1: `auto-drift-check.sh` (PostToolUse on Stop event)

**File:** `/root/projects/Interverse/os/clavain/hooks/auto-drift-check.sh`, Lines 14-30

```bash
# Input: Hook JSON on stdin (session_id, transcript_path, stop_hook_active)
# Line 27: Read hook input
INPUT=$(cat)

# Line 30: Extract from JSON
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
```

**Pattern:** `INPUT=$(cat)` then `jq -r '.field'`

---

#### Hook 2: `interserve-audit.sh` (PostToolUse on Edit|Write|NotebookEdit)

**File:** `/root/projects/Interverse/os/clavain/hooks/interserve-audit.sh`, Lines 4-18

```bash
# Line 13: Read hook input
payload="$(cat || true)"
[[ -n "$payload" ]] || exit 0

# Line 16-17: Extract from JSON
file_path="$(jq -r '(.tool_input.file_path // .tool_input.notebook_path // empty)' \
  <<<"$payload" 2>/dev/null || true)"
```

**Pattern:** Read stdin into variable, parse with `jq -r '.tool_input.file_path'`

---

#### Hook 3: `catalog-reminder.sh` (PostToolUse on Edit|Write|MultiEdit)

**File:** `/root/projects/Interverse/os/clavain/hooks/catalog-reminder.sh`, Lines 6-8

```bash
# Line 6: Read hook input
INPUT="$(cat)"

# Line 8: Extract from JSON
FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.edits[0].file_path // empty' 2>/dev/null)" || true
```

**Pattern:** Same — stdin JSON, not env vars.

---

#### Hook 4: `bead-agent-bind.sh` (PostToolUse on Bash)

**File:** `/root/projects/Interverse/os/clavain/hooks/bead-agent-bind.sh`, Lines 15-18

```bash
# Line 15: Read hook input
INPUT=$(cat)

# Line 18: Extract from JSON
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
```

**Pattern:** Consistent — all Clavain hooks read stdin, never env vars for hook data.

---

#### Hook 5: `auto-publish.sh` (PostToolUse on Bash)

**File:** `/root/projects/Interverse/os/clavain/hooks/auto-publish.sh`, Lines 25-34

```bash
# Line 27: Read hook input
local payload
payload="$(cat || true)"
[[ -n "$payload" ]] || exit 0

# Line 32-33: Extract from JSON
local cmd cwd
cmd="$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null || true)"
cwd="$(jq -r '.cwd // empty' <<<"$payload" 2>/dev/null || true)"
```

**Pattern:** Identical — stdin JSON via heredoc syntax `<<<"$payload"`

---

## Summary of Correct API Usage

| Hook | Event | File Path Reading | Edit String Reading |
|------|-------|-------------------|---------------------|
| `auto-drift-check.sh` | Stop | `jq '.cwd'` | N/A |
| `interserve-audit.sh` | PostToolUse | `jq '.tool_input.file_path'` | N/A |
| `catalog-reminder.sh` | PostToolUse | `jq '.tool_input.file_path'` | N/A |
| `bead-agent-bind.sh` | PostToolUse | N/A | `jq '.tool_input.command'` |
| `auto-publish.sh` | PostToolUse | `jq '.cwd'` | `jq '.tool_input.command'` |
| **learn-from-edits.sh** | **PostToolUse** | **`$CLAUDE_TOOL_INPUT_FILE_PATH`** (empty) | **`$CLAUDE_TOOL_INPUT_OLD_STRING`** (empty) |

interfluence is the **only hook in the ecosystem using the broken env var pattern**.

---

## Impact Assessment

**Severity:** Medium

- **User impact:** Voice profile learning hook silently fails. Edit diffs are never logged.
- **Error visibility:** None — hook exits 0, Claude Code sees nothing wrong.
- **Silent failure:** Users enabling `/interfluence refine` will see empty `learnings-raw.log` and believe the feature is not working.

---

## Fix Required

Change `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh` to use the correct stdin JSON API:

### Current (Broken) — Lines 13-16:
```bash
TOOL_NAME="$CLAUDE_TOOL_NAME"
FILE_PATH="$CLAUDE_TOOL_INPUT_FILE_PATH"
OLD_STRING="$CLAUDE_TOOL_INPUT_OLD_STRING"
NEW_STRING="$CLAUDE_TOOL_INPUT_NEW_STRING"
```

### Correct (Fixed):
```bash
# Read hook input from stdin
INPUT=$(cat)

# Extract fields from JSON
TOOL_NAME="$(echo "$INPUT" | jq -r '.tool_name // empty')"
FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')"

# For Edit tool, old_string and new_string are in tool_input
OLD_STRING="$(echo "$INPUT" | jq -r '.tool_input.old_string // empty')"
NEW_STRING="$(echo "$INPUT" | jq -r '.tool_input.new_string // empty')"
```

### Additional Validation Needed:
1. Test that `$TOOL_NAME` is `"Edit"` (uppercase)
2. Test that `$FILE_PATH` matches the actual file being edited
3. Verify `learnings-raw.log` is created and receives entries
4. Test with a real Edit tool call in Claude Code

---

## Documentation References

- Official hook API: `code.claude.com/docs/en/hooks` (researched in detail at `/root/projects/Interverse/services/intermute/docs/research/research-claude-code-hook-api.md`)
- PostToolUse spec: Lines 202-233 of hook API research
- Edit tool input schema: Line 119-125 of hook API research
- All Clavain PostToolUse hooks: `/root/projects/Interverse/os/clavain/hooks/*.sh`

---

## Files Involved

| File | Lines | Issue |
|------|-------|-------|
| `/root/projects/Interverse/plugins/interfluence/hooks/learn-from-edits.sh` | 13-16 | Broken env var reads |
| `/root/projects/Interverse/plugins/interfluence/hooks/hooks.json` | 1-16 | Hook configuration (correct) |
| `/root/projects/Interverse/plugins/interfluence/AGENTS.md` | 68-76 | Documents hook behavior (needs update) |
| `/root/projects/Interverse/plugins/interfluence/CLAUDE.md` | (no hooks section) | Missing validation note |

---

## Next Steps

1. Fix `learn-from-edits.sh` to read stdin JSON
2. Add integration test: trigger an Edit, verify `learnings-raw.log` receives entry
3. Update interfluence AGENTS.md to note the fix + add example of correct hook pattern
4. Verify `/interfluence refine` can read and process the learned edits
