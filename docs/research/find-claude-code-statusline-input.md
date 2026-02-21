# Claude Code Statusline JSON Input — Complete Field Reference

**Date:** 2026-02-20
**Purpose:** Document ALL fields available in the JSON object that Claude Code passes to custom statusline commands via stdin, plus changelog history and feature request pipeline.

---

## Full JSON Schema (as of v2.1.45)

Source: [Official Claude Code docs](https://code.claude.com/docs/en/statusline)

```json
{
  "cwd": "/current/working/directory",
  "session_id": "abc123...",
  "transcript_path": "/path/to/transcript.jsonl",
  "model": {
    "id": "claude-opus-4-6",
    "display_name": "Opus"
  },
  "workspace": {
    "current_dir": "/current/working/directory",
    "project_dir": "/original/project/directory",
    "added_dirs": ["/additional/dir/from/add-dir"]
  },
  "version": "1.0.80",
  "output_style": {
    "name": "default"
  },
  "cost": {
    "total_cost_usd": 0.01234,
    "total_duration_ms": 45000,
    "total_api_duration_ms": 2300,
    "total_lines_added": 156,
    "total_lines_removed": 23
  },
  "context_window": {
    "total_input_tokens": 15234,
    "total_output_tokens": 4521,
    "context_window_size": 200000,
    "used_percentage": 8,
    "remaining_percentage": 92,
    "current_usage": {
      "input_tokens": 8500,
      "output_tokens": 1200,
      "cache_creation_input_tokens": 5000,
      "cache_read_input_tokens": 2000
    }
  },
  "exceeds_200k_tokens": false,
  "vim": {
    "mode": "NORMAL"
  },
  "agent": {
    "name": "security-reviewer"
  }
}
```

---

## Field-by-Field Reference

### Root-Level Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `cwd` | string | No | Current working directory. Same value as `workspace.current_dir`; the latter is preferred. |
| `session_id` | string | No | Unique session identifier |
| `transcript_path` | string | No | Path to conversation transcript JSONL file |
| `version` | string | No | Claude Code version string |
| `exceeds_200k_tokens` | boolean | No | Whether the most recent API response's total tokens (input + cache + output) exceeds 200k. Fixed threshold regardless of actual context window size. |

### `model` Object

| Field | Type | Description |
|-------|------|-------------|
| `model.id` | string | Model identifier, e.g. `"claude-opus-4-6"` |
| `model.display_name` | string | Human-readable model name, e.g. `"Opus"` |

### `workspace` Object

| Field | Type | Description |
|-------|------|-------------|
| `workspace.current_dir` | string | Current working directory (preferred over `cwd`) |
| `workspace.project_dir` | string | Directory where Claude Code was launched. May differ from `current_dir` if working directory changes during session. |
| `workspace.added_dirs` | string[] | Directories added via `/add-dir` command. **Added in v2.1.45** (Feb 17, 2026). |

### `output_style` Object

| Field | Type | Description |
|-------|------|-------------|
| `output_style.name` | string | Name of current output style, e.g. `"default"` |

### `cost` Object

| Field | Type | Description |
|-------|------|-------------|
| `cost.total_cost_usd` | number | Total session cost in USD |
| `cost.total_duration_ms` | number | Total wall-clock time since session start, in milliseconds |
| `cost.total_api_duration_ms` | number | Total time spent waiting for API responses, in milliseconds |
| `cost.total_lines_added` | number | Lines of code added during session |
| `cost.total_lines_removed` | number | Lines of code removed during session |

### `context_window` Object

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `context_window.total_input_tokens` | number | No | Cumulative input tokens across entire session |
| `context_window.total_output_tokens` | number | No | Cumulative output tokens across entire session |
| `context_window.context_window_size` | number | No | Maximum context window size in tokens (200000 default, 1000000 for extended context) |
| `context_window.used_percentage` | number | **Yes** | Pre-calculated % of context window used. May be null early in session. |
| `context_window.remaining_percentage` | number | **Yes** | Pre-calculated % remaining. May be null early in session. |
| `context_window.current_usage` | object | **Yes** | Token counts from last API call. `null` before first API call. |

### `context_window.current_usage` Sub-Object

Only present after the first API call (null before that).

| Field | Type | Description |
|-------|------|-------------|
| `current_usage.input_tokens` | number | Input tokens in current context |
| `current_usage.output_tokens` | number | Output tokens generated |
| `current_usage.cache_creation_input_tokens` | number | Tokens written to cache |
| `current_usage.cache_read_input_tokens` | number | Tokens read from cache |

**Important:** `used_percentage` is calculated from input tokens only: `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. It does NOT include `output_tokens`.

### `vim` Object (Conditional)

**Not present in JSON** unless vim mode is enabled.

| Field | Type | Description |
|-------|------|-------------|
| `vim.mode` | string | Current vim mode: `"NORMAL"` or `"INSERT"` |

### `agent` Object (Conditional)

**Not present in JSON** unless running with `--agent` flag or agent settings configured.

| Field | Type | Description |
|-------|------|-------------|
| `agent.name` | string | Agent name, e.g. `"security-reviewer"` |

---

## What interline Currently Uses vs What's Available

### Currently used by interline (statusline.sh):
- `model.display_name` — model name display
- `workspace.project_dir` / `workspace.current_dir` — project name extraction
- `transcript_path` — transcript scanning for workflow phase detection
- `session_id` — sideband file lookup for bead/phase context

### Available but NOT used by interline:
- `cost.total_cost_usd` — session cost
- `cost.total_duration_ms` — session wall-clock time
- `cost.total_api_duration_ms` — API wait time
- `cost.total_lines_added` / `cost.total_lines_removed` — code churn
- `context_window.*` — all context window fields (usage %, token counts, current_usage)
- `exceeds_200k_tokens` — large context warning flag
- `version` — Claude Code version
- `output_style.name` — output style
- `vim.mode` — vim mode (when enabled)
- `agent.name` — agent name (when configured)
- `workspace.added_dirs` — directories added via `/add-dir`
- `cwd` — working directory (duplicate of workspace.current_dir)
- `model.id` — full model identifier

---

## Changelog History: Statusline Field Additions

| Version | Date | Change |
|---------|------|--------|
| v1.0.71 | ~Aug 2025 | Introduced customizable statusline via `/statusline` command. Initial fields: `model`, `workspace`, `cwd`, `session_id`, `transcript_path`, `version` |
| v1.0.85 | ~Sep 2025 | Added session cost info (`cost.*` fields) to statusline input |
| v1.0.112 | ~Oct 2025 | Statusline began displaying model identifier in transcript mode |
| v2.0.34 | ~Nov 2025 | Added `current_usage` field to statusline input for accurate context window % |
| v2.0.64-65 | ~Dec 11, 2025 | Added comprehensive context window information (`context_window.*` fields, `exceeds_200k_tokens`) |
| v2.1.6 | ~Jan 2026 | Added search functionality to `/config` and context window display fields |
| v2.1.45 | Feb 17, 2026 | Added `workspace.added_dirs` — directories from `/add-dir` |

### When Other Fields Were Added (exact version uncertain)
- `output_style.name` — present in official docs schema, version unknown
- `vim.mode` — present in official docs schema, likely added with vim mode feature
- `agent.name` — present in official docs schema, likely added with `--agent` flag feature

---

## Requested But NOT YET Implemented

These fields have been requested in GitHub issues but are NOT in the current JSON input:

### 1. Permission Mode ([#6227](https://github.com/anthropics/claude-code/issues/6227))
- **Status:** Closed as duplicate of #4719; related issues #16494 and #21516 marked COMPLETED (may have been added via hooks rather than statusline)
- **Proposed field:** `activePermissionMode` — string: `"default"` | `"acceptEdits"` | `"plan"` | `"bypassPermissions"`
- **Not in official docs** as a statusline field as of Feb 2026

### 2. Rate Limit Data ([#19385](https://github.com/anthropics/claude-code/issues/19385))
- **Status:** Open feature request
- **Proposed fields:**
  ```json
  {
    "rate_limits": {
      "session": {
        "used_percentage": 23,
        "resets_at": "2026-01-20T12:00:00Z",
        "resets_in_seconds": 14400
      },
      "weekly_all_models": {
        "used_percentage": 16,
        "resets_at": "2026-01-26T07:00:00Z"
      }
    }
  }
  ```
- Data exists in API response headers (`anthropic-ratelimit-unified-*`) but not exposed to statusline

### 3. Auto-Compact Threshold ([#12510](https://github.com/anthropics/claude-code/issues/12510))
- **Status:** Closed / implemented partially
- **Proposed field:** `context.auto_compact_threshold_percent`
- **Not in official docs** — the `used_percentage` and `remaining_percentage` were the fields that shipped

### 4. System Prompt / MCP Tool Token Counts
- Multiple issues requesting breakdown of what contributes to context usage (system prompt tokens, MCP tool definitions ~30-50k tokens, CLAUDE.md files)
- **Not implemented** — only aggregate token counts are available

---

## Behavioral Notes

### Update Triggers
- Script runs after each new assistant message
- Runs when permission mode changes
- Runs when vim mode toggles
- Debounced at 300ms (rapid changes batch together)
- If a new update triggers while script is still running, the in-flight execution is cancelled

### Null/Missing Field Handling
- `context_window.current_usage` — `null` before first API call
- `context_window.used_percentage` / `remaining_percentage` — may be `null` early in session
- `vim` object — entirely absent when vim mode is disabled
- `agent` object — entirely absent when not using `--agent` flag
- `workspace.added_dirs` — may be absent or empty array when no dirs added

### Output Format
- Only stdout is displayed (stderr is ignored for display)
- Multiple `echo`/`print` lines create multiple status rows
- ANSI escape codes supported for colors
- OSC 8 escape sequences supported for clickable links (terminal-dependent)
- Non-zero exit codes or empty output cause blank status line

### Performance
- Keep scripts fast — slow scripts block updates
- Cache expensive operations (git commands) to temp files with TTL
- Use stable cache filenames (NOT `$$` or PID-based — each invocation is a new process)

---

## Sources

- [Official Anthropic docs — Customize your status line](https://code.claude.com/docs/en/statusline)
- [GitHub issue #5404 — Original undocumented statusline discovery](https://github.com/anthropics/claude-code/issues/5404)
- [GitHub issue #12510 — Add context data to statusline JSON](https://github.com/anthropics/claude-code/issues/12510)
- [GitHub issue #6227 — Expose permission mode to statusline](https://github.com/anthropics/claude-code/issues/6227)
- [GitHub issue #19385 — Expose rate limit data in statusline](https://github.com/anthropics/claude-code/issues/19385)
- [GitHub issue #13783 — Bug: cumulative vs current tokens](https://github.com/anthropics/claude-code/issues/13783)
- [ClaudeLog changelog](https://claudelog.com/claude-code-changelog/)
- [PhotoStructure statusline guide](https://photostructure.com/coding/claude-code-statusline/)
- [Claude Code CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
