---
name: intermux
description: "Agent activity visibility -- tmux monitoring, activity feeds, health detection. Enriches intermute with live context."
---
# Gemini Skill: intermux

You have activated the intermux capability.

## Base Instructions
# Intermux — Agent Activity Visibility

## What This Is

Intermux is a persistent Go MCP server that gives agents visibility into what other agents are doing. It continuously monitors tmux sessions, detects agent status, and enriches intermute with live activity metadata.

## Architecture

```
Claude Code Agents (in tmux sessions)
         │ MCP tools
         ▼
┌─────────────────────────────┐
│     intermux (Go MCP)       │
│  • tmux watcher goroutine   │
│  • health monitor goroutine │
│  • metadata pusher goroutine│
│  • in-memory activity store │
└──────────┬──────────────────┘
           │ PATCH /api/agents/{id}/metadata
           ▼
┌─────────────────────────────┐
│  intermute (coordination)   │
└─────────────────────────────┘
```

## MCP Tools (7)

| Tool | Description |
|------|-------------|
| `list_agents` | All detected agent sessions with status |
| `peek_agent` | Detailed view: pane content, process info, activity record |
| `activity_feed` | Chronological events filtered by time/session/type |
| `search_output` | Search pane content across all agents |
| `agent_health` | Health report with warnings for stuck/crashed agents |
| `who_is_editing` | Check if any agent is editing files matching a pattern |
| `session_info` | Raw tmux session info |

## Key Components

### Tmux Watcher (`internal/tmux/`)
- Scans tmux sessions every 10 seconds
- Filters for sessions matching "claude" or "codex" in name
- Captures pane content and extracts signals (active, idle, error patterns)
- Detects CWD via `/proc/<pid>/cwd`, git branch from `.git/HEAD`

### Activity Store (`internal/activity/`)
- In-memory `map[string]*AgentActivity` keyed by tmux session
- Ring buffer of 200 `ActivityEvent`s
- Thread-safe via `sync.RWMutex`

### Health Monitor (`internal/health/`)
- Runs every 30 seconds
- Classifies: active, idle, stuck (>5min no change), crashed (PID gone)
- Triggers status change callbacks

### Metadata Pusher (`internal/push/`)
- Pushes to intermute PATCH `/api/agents/{id}/metadata` every 30 seconds
- Requires agent correlation (tmux session → intermute agent ID)
- Free heartbeat with every metadata push

### Agent Correlation
- SessionStart hook writes `/tmp/intermux-mapping-<session_id>.json`
- Maps `{tmux_session, agent_id}` for the pusher
- Watcher goroutine checks for new mapping files every 15 seconds

## Development

```bash
# Build
go build -o bin/intermux-mcp ./cmd/intermux-mcp/

# Run standalone (for testing)
INTERMUTE_URL=http://127.0.0.1:7338 ./bin/intermux-mcp

# Install as plugin
claude plugins install /root/projects/Interverse/plugins/intermux

# Validate structure
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"
bash -n hooks/*.sh
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INTERMUTE_URL` | `http://127.0.0.1:7338` | Intermute API base URL |
| `INTERMUTE_AGENT_ID` | (none) | Agent ID from interlock registration |
| `TMUX` | (none) | Set by tmux — used to detect current session |


