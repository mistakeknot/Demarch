# Intercheck Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Create the `intercheck` plugin — code quality guards and session health monitoring via PostToolUse hooks.

**Architecture:** Pure hooks plugin with shared lib, session state in /tmp, and one status skill. Three hooks fire on PostToolUse: context-monitor (all tools), syntax-check (Edit/Write), auto-format (Edit/Write, after syntax-check passes).

**Tech Stack:** Bash hooks, jq for JSON state, language-specific checkers/formatters.

---

### Task 1: Scaffold plugin structure

**Files:**
- Create: `plugins/intercheck/.claude-plugin/plugin.json`
- Create: `plugins/intercheck/.claude-plugin/hooks.json`
- Create: `plugins/intercheck/CLAUDE.md`

**Step 1: Create plugin manifest**

```json
{
  "name": "intercheck",
  "version": "0.1.0",
  "description": "Code quality guards and session health monitoring",
  "author": "MK"
}
```

**Step 2: Create hooks.json skeleton**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/context-monitor.sh",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Edit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/syntax-check.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/auto-format.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Step 3: Create CLAUDE.md**

Minimal quick reference with hook descriptions and state file location.

**Step 4: Init git repo**

```bash
cd plugins/intercheck && git init && git add -A && git commit -m "feat: scaffold intercheck plugin"
```

---

### Task 2: Shared library (lib/intercheck-lib.sh)

**Files:**
- Create: `plugins/intercheck/lib/intercheck-lib.sh`

**Step 1: Write shared functions**

```bash
#!/usr/bin/env bash
# Shared library for intercheck hooks.
#
# Provides:
#   _ic_session_id     — extract session_id from stdin JSON
#   _ic_state_file     — path to session state file
#   _ic_read_state     — read state JSON (or default)
#   _ic_write_state    — write state JSON
#   _ic_detect_lang    — detect language from file extension
#   _ic_file_path      — extract file path from tool input JSON

[[ -n "${_LIB_INTERCHECK_LOADED:-}" ]] && return 0
_LIB_INTERCHECK_LOADED=1

_ic_session_id() {
  echo "$1" | jq -r '.session_id // empty' 2>/dev/null
}

_ic_state_file() {
  local sid="$1"
  echo "/tmp/intercheck-${sid}.json"
}

_ic_read_state() {
  local sf="$1"
  if [[ -f "$sf" ]]; then
    cat "$sf"
  else
    echo '{"calls":0,"last_call_ts":0,"pressure":0,"heavy_calls":0,"est_tokens":0,"syntax_errors":0,"format_runs":0}'
  fi
}

_ic_write_state() {
  local sf="$1" state="$2"
  echo "$state" > "$sf"
}

_ic_file_path() {
  local json="$1"
  echo "$json" | jq -r '.tool_input.file_path // .tool_input.command // empty' 2>/dev/null
}

_ic_detect_lang() {
  local fp="$1"
  case "$fp" in
    *.py)           echo "python" ;;
    *.sh|*.bash)    echo "shell" ;;
    *.json)         echo "json" ;;
    *.toml)         echo "toml" ;;
    *.yaml|*.yml)   echo "yaml" ;;
    *.go)           echo "go" ;;
    *.ts|*.tsx)     echo "typescript" ;;
    *.js|*.jsx)     echo "javascript" ;;
    *)              echo "unknown" ;;
  esac
}
```

**Step 2: Verify syntax**

```bash
bash -n lib/intercheck-lib.sh
```

---

### Task 3: Context monitor hook

**Files:**
- Create: `plugins/intercheck/hooks/context-monitor.sh`

**Step 1: Write the hook**

The hook:
1. Reads JSON from stdin
2. Extracts session_id, tool_name, and tool output length
3. Loads state from state file
4. Computes time decay: `elapsed = now - last_call_ts`, `decay = elapsed / 600 * 0.5` (0.5 per 10 min)
5. Adds call weight: 1.0 for normal calls, 1.5 for Read/Grep/Task
6. Estimates tokens: `output_len / 4` added to cumulative est_tokens
7. Computes pressure: `pressure = max(0, old_pressure - decay) + call_weight`
8. Writes updated state
9. Returns additionalContext JSON only when crossing a threshold

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/intercheck-lib.sh"

INPUT=$(cat)
SID=$(_ic_session_id "$INPUT")
[[ -z "$SID" ]] && exit 0

TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
OUTPUT_LEN=$(echo "$INPUT" | jq -r '.tool_output // "" | length' 2>/dev/null || echo 0)

SF=$(_ic_state_file "$SID")
STATE=$(_ic_read_state "$SF")

NOW=$(date +%s)
LAST_TS=$(echo "$STATE" | jq -r '.last_call_ts // 0')
CALLS=$(echo "$STATE" | jq -r '.calls // 0')
PRESSURE=$(echo "$STATE" | jq -r '.pressure // 0')
HEAVY=$(echo "$STATE" | jq -r '.heavy_calls // 0')
EST_TOKENS=$(echo "$STATE" | jq -r '.est_tokens // 0')

# Time decay
if [[ "$LAST_TS" -gt 0 ]]; then
  ELAPSED=$((NOW - LAST_TS))
  DECAY=$(python3 -c "print(round($ELAPSED / 600.0 * 0.5, 2))" 2>/dev/null || echo "0")
else
  DECAY=0
fi

# Call weight
WEIGHT=1.0
case "$TOOL" in
  Read|Grep|Task|WebFetch|WebSearch) WEIGHT=1.5; HEAVY=$((HEAVY + 1)) ;;
esac

# Token estimate
NEW_TOKENS=$(python3 -c "print(int($OUTPUT_LEN / 4))" 2>/dev/null || echo 0)
EST_TOKENS=$((EST_TOKENS + NEW_TOKENS))

# Pressure update
PRESSURE=$(python3 -c "print(round(max(0, $PRESSURE - $DECAY) + $WEIGHT, 2))" 2>/dev/null || echo "$PRESSURE")
CALLS=$((CALLS + 1))

# Write state
NEW_STATE=$(jq -n \
  --argjson calls "$CALLS" \
  --argjson ts "$NOW" \
  --argjson pressure "$PRESSURE" \
  --argjson heavy "$HEAVY" \
  --argjson tokens "$EST_TOKENS" \
  --argjson errors "$(echo "$STATE" | jq '.syntax_errors // 0')" \
  --argjson formats "$(echo "$STATE" | jq '.format_runs // 0')" \
  '{calls:$calls, last_call_ts:$ts, pressure:$pressure, heavy_calls:$heavy, est_tokens:$tokens, syntax_errors:$errors, format_runs:$formats}')
_ic_write_state "$SF" "$NEW_STATE"

# Threshold check — output additionalContext only on crossing
MSG=""
if (( EST_TOKENS > 200000 )) || python3 -c "exit(0 if $PRESSURE > 120 else 1)" 2>/dev/null; then
  # Red — auto-checkpoint
  CHECKPOINT="/tmp/intercheck-checkpoint-${SID}.md"
  echo "# Session Checkpoint (auto-generated)" > "$CHECKPOINT"
  echo "Session: $SID" >> "$CHECKPOINT"
  echo "Pressure: $PRESSURE | Tokens: ~${EST_TOKENS}" >> "$CHECKPOINT"
  echo "Tool calls: $CALLS ($HEAVY heavy)" >> "$CHECKPOINT"
  echo "Time: $(date -Iseconds)" >> "$CHECKPOINT"
  MSG="Context is near exhaustion (pressure: $PRESSURE, ~${EST_TOKENS} tokens). Checkpoint written to $CHECKPOINT. Commit your work and wrap up NOW."
elif (( EST_TOKENS > 180000 )) || python3 -c "exit(0 if $PRESSURE > 90 else 1)" 2>/dev/null; then
  MSG="Context pressure is high (pressure: $PRESSURE, ~${EST_TOKENS} tokens). Finish current work and commit. Avoid launching new subagents."
elif (( EST_TOKENS > 150000 )) || python3 -c "exit(0 if $PRESSURE > 60 else 1)" 2>/dev/null; then
  MSG="Context pressure is moderate (pressure: $PRESSURE, ~${EST_TOKENS} tokens). Consider wrapping up current task before starting new ones."
fi

if [[ -n "$MSG" ]]; then
  jq -n --arg msg "$MSG" '{"additionalContext": $msg}'
fi
```

**Step 2: Verify syntax**

```bash
bash -n hooks/context-monitor.sh
```

---

### Task 4: Syntax check hook

**Files:**
- Create: `plugins/intercheck/hooks/syntax-check.sh`

**Step 1: Write the hook**

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/intercheck-lib.sh"

INPUT=$(cat)
SID=$(_ic_session_id "$INPUT")
FP=$(_ic_file_path "$INPUT")
[[ -z "$FP" || ! -f "$FP" ]] && exit 0

LANG=$(_ic_detect_lang "$FP")
ERR=""

case "$LANG" in
  python)
    ERR=$(python3 -m py_compile "$FP" 2>&1) || true
    ;;
  shell)
    ERR=$(bash -n "$FP" 2>&1) || true
    ;;
  json)
    ERR=$(python3 -c "import json; json.load(open('$FP'))" 2>&1) || true
    ;;
  toml)
    ERR=$(python3 -c "import tomllib; tomllib.load(open('$FP','rb'))" 2>&1) || true
    ;;
  yaml)
    ERR=$(python3 -c "import yaml; yaml.safe_load(open('$FP'))" 2>&1) || true
    ;;
  go)
    command -v go &>/dev/null && ERR=$(go vet "$FP" 2>&1) || true
    ;;
  typescript|javascript)
    command -v node &>/dev/null && ERR=$(node --check "$FP" 2>&1) || true
    ;;
  *)
    exit 0
    ;;
esac

if [[ -n "$ERR" ]]; then
  # Increment syntax_errors in state
  if [[ -n "$SID" ]]; then
    SF=$(_ic_state_file "$SID")
    STATE=$(_ic_read_state "$SF")
    NEW_STATE=$(echo "$STATE" | jq '.syntax_errors = (.syntax_errors + 1)')
    _ic_write_state "$SF" "$NEW_STATE"
  fi
  # Truncate error to 200 chars
  ERR_SHORT="${ERR:0:200}"
  jq -n --arg msg "Syntax error in $FP: $ERR_SHORT" '{"additionalContext": $msg}'
fi
```

**Step 2: Verify syntax**

```bash
bash -n hooks/syntax-check.sh
```

---

### Task 5: Auto-format hook

**Files:**
- Create: `plugins/intercheck/hooks/auto-format.sh`

**Step 1: Write the hook**

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/lib/intercheck-lib.sh"

INPUT=$(cat)
SID=$(_ic_session_id "$INPUT")
FP=$(_ic_file_path "$INPUT")
[[ -z "$FP" || ! -f "$FP" ]] && exit 0

LANG=$(_ic_detect_lang "$FP")
FORMATTED=false

case "$LANG" in
  python)
    command -v ruff &>/dev/null && ruff format --quiet "$FP" 2>/dev/null && FORMATTED=true
    ;;
  shell)
    command -v shfmt &>/dev/null && shfmt -w "$FP" 2>/dev/null && FORMATTED=true
    ;;
  go)
    command -v gofmt &>/dev/null && gofmt -w "$FP" 2>/dev/null && FORMATTED=true
    ;;
  json)
    if command -v jq &>/dev/null && jq . "$FP" > "${FP}.tmp" 2>/dev/null; then
      mv "${FP}.tmp" "$FP" && FORMATTED=true
    else
      rm -f "${FP}.tmp"
    fi
    ;;
  typescript|javascript)
    if command -v npx &>/dev/null && [[ -d "$(dirname "$FP")/node_modules" || -d "./node_modules" ]]; then
      npx prettier --write "$FP" 2>/dev/null && FORMATTED=true
    fi
    ;;
esac

# Track format count in state (silent — no output)
if [[ "$FORMATTED" == "true" && -n "$SID" ]]; then
  SF=$(_ic_state_file "$SID")
  STATE=$(_ic_read_state "$SF")
  NEW_STATE=$(echo "$STATE" | jq '.format_runs = (.format_runs + 1)')
  _ic_write_state "$SF" "$NEW_STATE"
fi
```

**Step 2: Verify syntax**

```bash
bash -n hooks/auto-format.sh
```

---

### Task 6: Status skill

**Files:**
- Create: `plugins/intercheck/skills/status/SKILL.md`

**Step 1: Write the skill**

The skill reads the session state file and displays a health dashboard. Include instructions for Claude to read the state file and format the output as a table.

---

### Task 7: Integration test and commit

**Step 1: Verify all hook syntax**

```bash
cd plugins/intercheck
bash -n hooks/context-monitor.sh
bash -n hooks/syntax-check.sh
bash -n hooks/auto-format.sh
bash -n lib/intercheck-lib.sh
```

**Step 2: Test with mock input**

```bash
echo '{"session_id":"test-123","tool_name":"Edit","tool_input":{"file_path":"/tmp/test.py"},"tool_output":"x = 1"}' | bash hooks/context-monitor.sh
echo '{"session_id":"test-123","tool_name":"Edit","tool_input":{"file_path":"/tmp/test.py"}}' | bash hooks/syntax-check.sh
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: intercheck plugin — context monitor, syntax check, auto-format"
```

**Step 4: Add to Interverse CLAUDE.md**

Add `intercheck/` to the structure listing.

**Step 5: Push**

```bash
git push
```
