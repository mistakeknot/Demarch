# Research: SystemPrompt Code Orchestrator

**Date:** 2026-02-15
**Source:** [systempromptio/systemprompt-code-orchestrator](https://github.com/systempromptio/systemprompt-code-orchestrator)
**License:** MIT | **Stars:** 139 | **Language:** TypeScript | **Created:** 2025-06-27

---

## Executive Summary

SystemPrompt Code Orchestrator is an MCP (Model Context Protocol) server that turns a developer workstation into a remotely-accessible AI coding assistant. It orchestrates Claude Code CLI (and theoretically Gemini CLI) sessions through a Docker-containerized MCP server that communicates with a host-side daemon over TCP. The project is early-stage (v0.01), single-founder, and emphasizes mobile/voice-first workflows via a companion iOS/Android app.

**Key architectural insight:** It does NOT implement multi-agent coordination between peers. It is a single-task-at-a-time orchestrator that spawns one Claude Code CLI process per task, monitors it via streaming events, and exposes task state as MCP resources. There is no task decomposition, no agent-to-agent communication, and no token-efficiency optimization.

---

## 1. Architecture

### High-Level Topology

```
MCP Client (Mobile App / Desktop / Inspector)
    |
    v  (HTTP + MCP Protocol)
Docker Container
    ├── Express.js HTTP Server (port 3000)
    ├── MCP Handler (protocol endpoints at /mcp)
    ├── TaskStore (in-memory Map + JSON file persistence)
    ├── AgentManager (singleton, session lifecycle)
    └── ClaudeCodeService (singleton, query execution)
            |
            v  (TCP socket, port 9876)
Host Bridge Daemon (runs on host machine)
    ├── Receives JSON commands over TCP
    ├── Spawns Claude Code CLI processes
    ├── Streams stdout/stderr back as JSON lines
    └── Reports process lifecycle (pid, exit code)
            |
            v
Claude Code CLI (--dangerously-skip-permissions, --max-turns 5)
    └── Executes on host with full filesystem access
```

### Component Breakdown

#### MCP Server (`src/server.ts`)
- Express.js HTTP server with CORS, listening on `0.0.0.0:3000`
- Routes: `/mcp` (MCP protocol), `/health`, `/` (metadata)
- MCP transport is Streamable HTTP (not SSE, not stdio)
- No authentication on MCP endpoints

#### Host Bridge Daemon (`daemon/src/host-bridge-daemon.ts`)
- Standalone TCP server running on the host machine (port 9876 by default)
- Receives JSON messages: `{ tool: "claude", command: "...", workingDirectory: "...", env: {...} }`
- Spawns Claude Code CLI via shell: `claude -p --output-format json --dangerously-skip-permissions --max-turns 5 "prompt"`
- Streams responses as newline-delimited JSON: `{ type: "stream"|"pid"|"error"|"complete", data?: ..., exitCode?: ... }`
- Manages process lifecycle, graceful shutdown, and PID tracking
- Path mapping: Docker `/workspace` <-> host `HOST_FILE_ROOT`

#### Docker Architecture (`docker-compose.yml`)
- Single container: `mcp-server`
- Mounts host workspace at `/workspace:rw` for file operations
- Mounts `.claude.json` for authentication
- Persistent volume `coding-agent-state` for task data at `/data/state`
- Communicates with daemon via `host.docker.internal:9876`

### Execution Modes

The `ClaudeCodeService` supports two modes:

1. **Host Proxy Mode** (default): When `ANTHROPIC_API_KEY` is not set, routes queries through the Host Bridge Daemon to the host's Claude CLI installation. This is the primary mode.

2. **SDK Mode**: When `ANTHROPIC_API_KEY` is available, uses `@anthropic-ai/claude-code` SDK directly from within the Docker container. Uses the `query()` function with streaming message iteration.

---

## 2. Agent Manager

### Class: `AgentManager` (`src/services/agent-manager/agent-manager.ts`)

Singleton that manages all AI agent sessions. Currently only supports Claude, but designed for extensibility.

**Key components:**
- **SessionStore** (`session-store.ts`): In-memory `Map<string, AgentSession>` with lookup by session ID, service ID, or type
- **ClaudeSessionManager** (`claude-session-manager.ts`): Handles Claude-specific session creation, command execution, and cleanup
- **TaskLogger** (`task-logger.ts`): Writes structured logs to the TaskStore for each session action

**AgentSession structure:**
```typescript
interface AgentSession {
  id: string;                    // Unique session identifier
  type: AgentType;              // 'claude' (currently only option)
  serviceSessionId: string;      // Underlying ClaudeCodeService session ID
  status: AgentState;           // initializing | ready | busy | idle | error | completed | cancelled
  projectPath: string;          // Working directory
  taskId?: string;              // Associated task
  mcpSessionId?: string;        // MCP correlation ID
  created_at: string;
  last_activity: string;
  output_buffer: string[];
  error_buffer: string[];
}
```

**Session lifecycle:**
1. `startClaudeSession(config)` -- creates session in store, spawns via ClaudeSessionManager
2. `sendCommand(sessionId, command)` -- validates state, sets status to `busy`, routes to ClaudeSessionManager
3. `endSession(sessionId)` -- terminates underlying service, cleans up store

**Events emitted:**
- `session:created` -- `{ sessionId, type }`
- `session:ready` -- `sessionId` (when service session becomes active)
- `task:progress` -- `{ taskId, event, data }` (forwarded from ClaudeCodeService)

---

## 3. Task Management

### Class: `TaskStore` (`src/services/task-store.ts`)

Singleton in-memory task store backed by filesystem persistence.

**Storage model:**
- In-memory: `Map<string, Task>`
- On disk: `./coding-agent-state/tasks/<task_id>.json` (one file per task)
- Global state: `./coding-agent-state/state.json` (includes all tasks + metrics)
- Auto-save every 30 seconds + on every create/update

**Task structure:**
```typescript
interface Task {
  id: TaskId;                   // Branded string type (e.g., "task_1720000000000")
  description: string;          // Max 255 chars (truncated from title)
  status: TaskStatus;           // pending | in_progress | waiting | completed | failed | cancelled
  tool: AITool;                 // Always "CLAUDECODE"
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  assigned_to?: string;         // Agent session ID
  error?: string;
  result?: {
    output: string;
    success: boolean;
    error?: string;
    data?: any;
  };
  logs: TaskLogEntry[];         // Structured log entries
  toolInvocations?: ToolInvocation[];
  toolUsageSummary?: ToolUsageSummary;
  claudeMetrics?: ClaudeMetrics;  // Token usage, cost, duration
  filesAffected?: Array<{path, operation, timestamp}>;
  commandsExecuted?: Array<{command, exitCode, duration, timestamp}>;
}
```

**Task status lifecycle:**
```
pending --> in_progress --> waiting --> completed
                       \-> failed
                       \-> cancelled
```

The `waiting` state means Claude finished but the session is still active for follow-up instructions via `update_task`.

**MCP resource integration:**
- Tasks exposed as MCP resources with URI scheme `task://<task_id>`
- On every task change, `sendResourcesUpdatedNotification()` pushes MCP `notifications/resources/updated` to subscribed clients
- On task creation/deletion, `sendResourcesListChangedNotification()` pushes `notifications/resources/list_changed`

### Task Creation Flow (`src/handlers/tools/create-task.ts`)

When `create_task` MCP tool is called:

1. Validate input (title + instructions required)
2. Tool is hardcoded to `"CLAUDECODE"` -- the `tool` field in the MCP schema was removed; it always uses Claude
3. Create task in TaskStore (status: `pending`)
4. Update status to `in_progress`
5. Start agent session via `agentOperations.startAgentForTask()`
6. Assign session ID to task (`assigned_to`)
7. **Fire-and-forget** `executeInitialInstructions()` -- runs asynchronously
8. Return immediately with `{ task_id, session_id, status: "in_progress" }`

The async `executeInitialInstructions()` function:
1. Sets up progress handlers
2. Calls `agentOperations.executeInstructions(sessionId, instructions)`
3. Logs execution time and result
4. On success: updates task to `waiting` with result
5. On failure: updates task to `failed` with error

---

## 4. Token Efficiency

**Finding: There are NO token efficiency optimizations in this project.**

Specific analysis:

- **No prompt compression or caching**: Each task sends the full instruction text to Claude Code CLI as a single prompt string. No prompt summarization, no context windowing, no differential prompting.

- **No multi-turn context management**: Claude Code CLI is invoked with `--max-turns 5` (hardcoded in the daemon), meaning each task gets at most 5 turns. But there is no attempt to reduce tokens within those turns.

- **No shared context between tasks**: Each task spawns an entirely new Claude Code CLI process. There is no session resumption, no context sharing, and no memory between tasks.

- **Token tracking (observability only)**: The system does track token usage in `ClaudeMetrics`:
  ```typescript
  usage: {
    inputTokens: number;
    outputTokens: number;
    cacheCreationTokens: number;
    cacheReadTokens: number;
    totalTokens: number;
  };
  cost: number;  // USD
  ```
  This data is extracted from Claude Code's JSON output (`parsedResult.usage`) and stored in the task's `result.data` metadata. But it is purely for reporting -- it does not influence future behavior.

- **No system prompt optimization**: The `customSystemPrompt` option exists but is passed through directly to Claude Code SDK. No compression, templating, or token-aware truncation.

- **Performance optimizations (non-token)**: The README mentions streaming output, lazy resource loading, connection pooling, and efficient state persistence. These are I/O optimizations, not token optimizations.

---

## 5. Task Decomposition

**Finding: There is NO task decomposition.**

The orchestrator operates on a **one task = one Claude Code CLI invocation** model:

- The `create_task` tool takes `title` and `instructions` as flat strings
- These are passed directly to Claude Code CLI as a single prompt
- The `ProcessTask` type includes `parentTaskId` and `type` fields (`query`, `code_generation`, `code_review`, etc.), suggesting planned support for task hierarchies, but these are **never used** in the current codebase
- No tool breaks work into subtasks, no task dependency graph, no work breakdown structure
- The `update_task` tool allows sending follow-up instructions to an existing session, but this is manual human intervention, not automated decomposition

The README's "Future Roadmap" explicitly lists **"Multi-Agent Orchestration"** as a planned feature, confirming it does not exist yet.

---

## 6. Coordination / Event System

### Event Architecture

The system uses Node.js `EventEmitter` throughout, with typed event interfaces:

**Three event layers:**

1. **ClaudeCodeService events** (lowest level):
   - `session:created`, `session:ready`, `session:terminated`
   - `task:progress` -- stream data parsed into progress events
   - `stream:data` -- raw streaming output from Claude
   - `claude:event` -- structured events parsed from Claude output

2. **AgentManager events** (middle level):
   - `session:created`, `session:ready`
   - `task:progress` (forwarded from ClaudeCodeService)

3. **TaskStore events** (highest level):
   - `task:created`, `task:updated`, `task:deleted`
   - `task:log` (new log entry added)
   - `task:progress` (elapsed time update)

### Claude Event Parser (`src/services/claude-code/event-parser.ts`)

Parses Claude Code CLI stdout/stderr into structured `ClaudeEvent` objects:

**Event types:**
- `process:start` / `process:end` -- process lifecycle with PID, exit code, duration
- `tool:start` / `tool:end` -- tool invocation tracking (Bash, Read, Write, Edit)
- `message` -- assistant thinking/explanation
- `stream` -- raw output data
- `error` -- error messages
- `result` -- JSON result with cost/usage/duration

**Detection uses regex patterns:**
```typescript
bashCommand: /^\$ (.+)$/
readFile: /^(?:Reading|Opening) file:\s*(.+)$/i
writeFile: /^(?:Writing|Creating|Saving) (?:to )?file:\s*(.+)$/i
editFile: /^(?:Editing|Modifying|Updating) file:\s*(.+)$/i
toolCall: /^(?:Running|Executing|Calling|Using)(?: the)? (\w+)/i
error: /^(?:Error|Failed|Exception|Warning):\s*(.+)$/i
jsonResult: /^\{.*"type"\s*:\s*"result".*\}$/
```

**Important limitation:** The event parser operates on text pattern matching of Claude's stdout, not structured event data. This is inherently fragile -- if Claude's output format changes, event parsing breaks silently.

### MCP Notifications

Task state changes propagate to MCP clients via the MCP SDK's notification system:
- `notifications/resources/updated` -- when a specific task resource changes
- `notifications/resources/list_changed` -- when tasks are created/deleted

This enables real-time monitoring without polling.

### Push Notifications

Firebase Cloud Messaging (FCM) integration sends mobile push notifications when tasks complete. Configured via `PUSH_TOKEN` environment variable.

### Agent-to-Agent Coordination

**There is none.** Each task runs in isolation. There is no:
- Inter-agent communication
- Shared memory/state between agents
- Conflict resolution
- File locking
- Work distribution
- Agent negotiation

---

## 7. Claude Code Integration Details

### How Claude Code CLI is Invoked

From the Host Bridge Daemon:
```bash
claude -p --output-format json --dangerously-skip-permissions --max-turns 5 "the prompt"
```

Flags:
- `-p` -- pipe mode (non-interactive, read from stdin/args)
- `--output-format json` -- structured JSON output
- `--dangerously-skip-permissions` -- skip all permission prompts
- `--max-turns 5` -- limit to 5 agentic turns (hardcoded in daemon)

The prompt is the raw instruction text from the `create_task` call.

### SDK Mode Alternative

When `ANTHROPIC_API_KEY` is set, uses `@anthropic-ai/claude-code` SDK:
```typescript
for await (const message of query({ prompt, abortController, options })) {
  messages.push(message);
  session.outputBuffer.push(message);
}
```

Supports `maxTurns`, `model`, `allowedTools`, and `customSystemPrompt` options.

### Session Isolation

Each task gets its own:
- Claude Code CLI process (host proxy mode) or SDK query session (SDK mode)
- Session ID in the AgentManager
- Session ID in the ClaudeCodeService
- Separate output/error/stream buffers
- Own entry in the TaskStore

There is NO session resumption. The `--resume` flag is not used. Each task is a completely fresh Claude conversation.

### Result Parsing

Claude Code's JSON output is parsed for:
- `result` -- the text response
- `is_error` -- success/failure
- `duration_ms` / `duration_api_ms` -- timing
- `num_turns` -- how many turns were used
- `session_id` -- Claude's internal session ID
- `total_cost_usd` -- cost
- `usage` -- `{ input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens }`

All of this metadata is logged to the task as a `CLAUDE_RESULT` log entry.

---

## 8. MCP Tools Provided

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_task` | Create + immediately start a Claude Code task | `title`, `instructions` |
| `update_task` | Send follow-up instructions to running task | `process` (session ID), `instructions` |
| `end_task` | Complete and cleanup a task | `task_id`, `status` |
| `report_task` | Generate task report | `task_ids[]`, `format` |
| `check_status` | Verify agent availability | `test_sessions`, `verbose` |
| `update_stats` | Get system statistics | `include_tasks` |
| `clean_state` | Cleanup old tasks | `keep_recent`, `dry_run` |
| `get_prompt` | Get a pre-built prompt template | template name + variables |

### Pre-Built Prompt Templates

- Bug fixing (bug_description, error_logs)
- React components (component_name, features)
- Unit testing (target_files, framework, coverage_target)
- Reddit post (content type specific)

---

## 9. Comparison to Interverse/Interlock

| Feature | SystemPrompt Orchestrator | Interlock (Interverse) |
|---------|--------------------------|----------------------|
| **Multi-agent coordination** | None (roadmap item) | Full (reservation, negotiation, conflict resolution) |
| **Task decomposition** | None | Clavain sprint system |
| **Token efficiency** | None (tracking only) | Compact skill loading, context windowing |
| **Agent communication** | None | Intermute broadcast, reservation protocol |
| **File locking** | None | Exclusive/shared reservations with TTL |
| **Architecture** | Docker + TCP daemon | Claude Code hooks + MCP server |
| **Claude integration** | CLI spawn per task | Native SDK + session management |
| **Session model** | Fresh process per task | Persistent sessions with resumption |
| **State persistence** | JSON files | SQLite (intermute) + JSON |
| **MCP server** | Yes (HTTP transport) | Yes (interlock, interject, tldr-swinton) |
| **Mobile access** | Yes (companion app) | No |
| **Remote access** | Cloudflare tunnels | Tailscale |

### Key Takeaways for Interverse

1. **MCP resource subscription pattern** is well-implemented -- the `listChanged` + `resources/updated` notification flow is clean and could inform interlock's MCP resource design.

2. **Event parsing from CLI output** is fragile. Interverse's approach of using hooks and structured JSON (not regex on stdout) is more robust.

3. **The task-as-MCP-resource model** (URI scheme `task://<id>`) is a good pattern for exposing work units to MCP clients. Could inform how Clavain exposes sprints/beads.

4. **No useful patterns for token efficiency** -- the project doesn't attempt it. Interverse's compact skill loading and context windowing remain differentiated.

5. **The Docker-daemon bridge pattern** is interesting for remote access but adds complexity. Interverse's direct hook integration is simpler for local multi-agent scenarios.

---

## 10. Sources

- [GitHub Repository](https://github.com/systempromptio/systemprompt-code-orchestrator)
- [Glama MCP Server Listing](https://glama.ai/mcp/servers/@systempromptio/systemprompt-code-orchestrator)
- [PulseMCP Listing](https://www.pulsemcp.com/servers/systemprompt-code-orchestrator)
- [SystemPrompt.io Website](https://systemprompt.io)
- [SystemPrompt Core (Rust framework)](https://github.com/systempromptio/systemprompt-core)
- [Skywork Analysis](https://skywork.ai/skypage/en/systemprompt-code-orchestrator-ai-engineers-guide/1977612134614364160)
