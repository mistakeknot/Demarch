# Claude Code Statusline Feature — Documentation Research

**Date:** 2026-02-20
**Source:** Context7 — `/websites/code_claude` library (code.claude.com/docs/en/statusline)
**Library resolved from:** `@anthropic-ai/claude-code` -> `/anthropics/claude-code` (778 snippets, High reputation, score 80.6)
**Secondary source used:** `/websites/code_claude` (1674 snippets, High reputation, score 65.5) — this had the statusline-specific docs

---

## Configuration

The statusline is configured in `~/.claude/settings.json` (user-level) or project settings:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh",
    "padding": 2
  }
}
```

- **type**: `"command"` — tells Claude Code to run an external command
- **command**: path to script or inline shell command
- **padding**: optional integer, adds vertical padding around the status line

The status line updates automatically on the next interaction after configuration.

---

## How Input is Delivered

Claude Code sends a JSON object to the script's **stdin**. The script reads it (e.g., `input=$(cat)`) and writes its output to stdout.

---

## Full JSON Schema — Fields Passed via stdin

### Model Information

| Field | Type | Description |
|-------|------|-------------|
| `model.id` | string | Identifier for the current model |
| `model.display_name` | string | Display name for the current model |

### Workspace Information

| Field | Type | Description |
|-------|------|-------------|
| `cwd` | string | Current working directory |
| `workspace.current_dir` | string | Current working directory (preferred over `cwd`) |
| `workspace.project_dir` | string | Directory where Claude Code was launched |

### Cost Information

| Field | Type | Description |
|-------|------|-------------|
| `cost.total_cost_usd` | float | Total session cost in USD |
| `cost.total_duration_ms` | integer | Total wall-clock time since session start in milliseconds |
| `cost.total_api_duration_ms` | integer | Total time spent waiting for API responses in milliseconds |
| `cost.total_lines_added` | integer | Total lines of code added |
| `cost.total_lines_removed` | integer | Total lines of code removed |

### Context Window Information

| Field | Type | Description |
|-------|------|-------------|
| `context_window.total_input_tokens` | integer | Cumulative input token count |
| `context_window.total_output_tokens` | integer | Cumulative output token count |
| `context_window.context_window_size` | integer | Maximum context window size in tokens (default 200000, extended 1000000) |
| `context_window.used_percentage` | float | Percentage of context window used |
| `context_window.remaining_percentage` | float | Percentage of context window remaining |
| `context_window.current_usage` | object | Token counts from the last API call |
| `exceeds_200k_tokens` | boolean | Whether the last API response exceeded 200k tokens |

### Session Information

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `transcript_path` | string | Path to the conversation transcript file |
| `version` | string | Claude Code version |

---

## Example JSON Input (Reconstructed from Documentation)

```json
{
  "model": {
    "id": "claude-opus-4-6",
    "display_name": "Claude Opus 4.6"
  },
  "cwd": "/root/projects/Interverse",
  "workspace": {
    "current_dir": "/root/projects/Interverse",
    "project_dir": "/root/projects/Interverse"
  },
  "cost": {
    "total_cost_usd": 1.23,
    "total_duration_ms": 120000,
    "total_api_duration_ms": 45000,
    "total_lines_added": 150,
    "total_lines_removed": 30
  },
  "context_window": {
    "total_input_tokens": 50000,
    "total_output_tokens": 12000,
    "context_window_size": 200000,
    "used_percentage": 31.0,
    "remaining_percentage": 69.0,
    "current_usage": {}
  },
  "exceeds_200k_tokens": false,
  "session_id": "abc123",
  "transcript_path": "/home/user/.claude/projects/.../transcript.txt",
  "version": "2.1.39"
}
```

---

## Example Scripts from Documentation

### Inline jq command (minimal)

```json
{
  "statusLine": {
    "type": "command",
    "command": "jq -r '\"[\\(.model.display_name)] \\(.context_window.used_percentage // 0)% context\"'"
  }
}
```

### Bash script (full)

```bash
#!/bin/bash
# Read JSON data that Claude Code sends to stdin
input=$(cat)

# Extract fields using jq
MODEL=$(echo "$input" | jq -r '.model.display_name')
DIR=$(echo "$input" | jq -r '.workspace.current_dir')
# The "// 0" provides a fallback if the field is null
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)

# Output the status line - ${DIR##*/} extracts just the folder name
echo "[$MODEL] ${DIR##*/} | ${PCT}% context"
```

---

## Key Observations

1. **`cwd` vs `workspace.current_dir`**: Both exist; docs say `workspace.current_dir` is "preferred".
2. **Null safety**: Fields like `used_percentage` can be null — use jq's `// 0` fallback pattern.
3. **`context_window.current_usage`**: Documented as "object" with "token counts from the last API call" but no sub-field details provided. Likely contains `input_tokens` and `output_tokens` for the most recent call.
4. **`exceeds_200k_tokens`**: A top-level boolean, not nested under `context_window`.
5. **Cost fields include code metrics**: `total_lines_added` and `total_lines_removed` are under `cost`, not a separate category.
6. **No turn/message count**: There is no field for conversation turn count or message count.
7. **No tool usage data**: No fields about which tools have been used or tool call counts.
8. **Padding config**: The `padding` setting in the config controls vertical spacing, not part of the JSON input.
