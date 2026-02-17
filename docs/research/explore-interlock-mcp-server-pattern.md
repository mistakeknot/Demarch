# Interlock Go MCP Server Pattern Analysis

**Date:** 2026-02-16  
**Purpose:** Document the complete Go MCP server pattern used by interlock-mcp for replication in interserve and other plugins.

## 1. Directory Structure

### Physical Layout
```
/root/projects/Interverse/plugins/interlock/
├── bin/
│   ├── interlock-mcp              # Built Go binary (9.4 MB)
│   └── launch-mcp.sh              # Auto-build launcher (705 bytes)
├── cmd/
│   └── interlock-mcp/
│       └── main.go                # Entry point
├── internal/
│   ├── client/
│   │   ├── client.go              # HTTP client for intermute API
│   │   └── client_test.go
│   └── tools/
│       └── tools.go               # MCP tool definitions (11 tools, 745 lines)
├── hooks/
│   ├── hooks.json                 # Hook bindings
│   ├── lib.sh
│   ├── pre-edit.sh
│   ├── session-start.sh
│   └── stop.sh
├── scripts/
│   ├── build.sh                   # Build script
│   └── ... (other support scripts)
├── .claude-plugin/
│   └── plugin.json                # Plugin manifest
├── go.mod                         # Go module definition
└── go.sum
```

### Key Insight
The binary is built during plugin installation via `launch-mcp.sh`, which runs `go build` on first invocation. This allows plugins to ship without pre-compiled binaries while still working immediately after `claude plugins install`.

---

## 2. Go Module Setup

### go.mod Configuration
```go
module github.com/mistakeknot/interlock

go 1.23.0

require github.com/mark3labs/mcp-go v0.43.2

// Dependencies include JSON schema, UUID, and YAML support
```

### Key Details
- **Language:** Go 1.23.0
- **MCP Library:** `github.com/mark3labs/mcp-go` v0.43.2 (core MCP server implementation)
- **Minimal Dependencies:** No logging framework, no database libraries, direct HTTP calls
- **HTTP Transport:** Standard `net/http` library (supports Unix socket and TCP)

---

## 3. MCP Server Initialization (main.go)

### Entry Point Pattern
```go
package main

import (
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	"github.com/mistakeknot/interlock/internal/client"
	"github.com/mistakeknot/interlock/internal/tools"
)

func main() {
	// 1. Initialize intermute client (HTTP or Unix socket)
	c := client.NewClient(
		client.WithSocketPath(os.Getenv("INTERMUTE_SOCKET")),
		client.WithBaseURL(os.Getenv("INTERMUTE_URL")),
		client.WithAgentID(getAgentID()),
		client.WithProject(getProject()),
		client.WithAgentName(getAgentName()),
	)

	// 2. Create MCP server instance
	s := server.NewMCPServer(
		"interlock",                     // Server name
		"0.1.0",                         // Version
		server.WithToolCapabilities(true), // Enable tool execution
	)

	// 3. Register all tools with the server
	tools.RegisterAll(s, c)

	// 4. Start stdio server (reads JSON-RPC on stdin, writes on stdout)
	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "interlock-mcp: %v\n", err)
		os.Exit(1)
	}
}
```

### Environment Detection
The server automatically detects agent identity from multiple sources (in priority order):
1. `INTERLOCK_AGENT_ID` — explicit override
2. `INTERMUTE_AGENT_ID` — from intermute service
3. `CLAUDE_SESSION_ID` — from Claude Code (fallback, truncated to 8 chars)
4. Hostname + PID — ultimate fallback

Similarly for project and agent name, with sensible defaults (hostname, PWD basename).

---

## 4. MCP Tool Registration Pattern

### Registration Function (tools.go excerpt)
```go
// RegisterAll registers all 11 MCP tools with the server
func RegisterAll(s *server.MCPServer, c *client.Client) {
	s.AddTools(
		reserveFiles(c),
		releaseFiles(c),
		releaseAll(c),
		checkConflicts(c),
		myReservations(c),
		sendMessage(c),
		fetchInbox(c),
		listAgents(c),
		requestRelease(c),
		negotiateRelease(c),
		respondToRelease(c),
	)
}
```

### Individual Tool Definition Pattern
```go
func reserveFiles(c *client.Client) server.ServerTool {
	return server.ServerTool{
		Tool: mcp.NewTool("reserve_files",
			// Parameter 1: array of strings
			mcp.WithArray("patterns",
				mcp.Description("Glob patterns for files to reserve"),
				mcp.Required(),
				mcp.WithStringItems(),
			),
			// Parameter 2: string
			mcp.WithString("reason",
				mcp.Description("Why you're reserving these files"),
				mcp.Required(),
			),
			// Parameter 3: optional number (TTL in minutes)
			mcp.WithNumber("ttl_minutes",
				mcp.Description("Reservation duration in minutes (default: 15)"),
			),
			// Parameter 4: optional boolean (exclusive mode)
			mcp.WithBoolean("exclusive",
				mcp.Description("Whether the reservation is exclusive (default: true)"),
			),
		),
		Handler: func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			// 1. Extract and validate arguments
			args := req.GetArguments()
			patterns := toStringSlice(args["patterns"])
			reason, _ := args["reason"].(string)
			ttl := intOr(args["ttl_minutes"], 15)
			exclusive := boolOr(args["exclusive"], true)

			if len(patterns) == 0 {
				return mcp.NewToolResultError("patterns is required"), nil
			}

			// 2. Call HTTP client method
			type result struct {
				Reservations []any    `json:"reservations"`
				Errors       []string `json:"errors,omitempty"`
			}
			var res result
			for _, p := range patterns {
				r, err := c.CreateReservation(ctx, p, reason, ttl, exclusive)
				if err != nil {
					res.Errors = append(res.Errors, fmt.Sprintf("%s: %v", p, err))
					continue
				}
				res.Reservations = append(res.Reservations, r)
				emitSignal("reserve", fmt.Sprintf("reserved %s", p))
			}

			// 3. Return JSON result
			return jsonResult(res)
		},
	}
}
```

### Helper Functions
- **`toStringSlice(v any)`** — converts JSON array to Go slice
- **`intOr(v any, def int)`** — extracts number with fallback
- **`boolOr(v any, def bool)`** — extracts boolean with fallback
- **`stringOr(v any, def string)`** — extracts string with fallback
- **`jsonResult(v any)`** — marshals response to JSON text result

### HTTP Client Pattern
The tools layer calls methods on `*client.Client`:
- `CreateReservation(ctx, pattern, reason, ttl, exclusive)` → POST /api/reservations
- `ListReservations(ctx, filters)` → GET /api/reservations?...
- `CheckConflicts(ctx, pattern)` → GET /api/conflicts?pattern=...
- `SendMessage(ctx, to, body)` → POST /api/messages
- `FetchInbox(ctx, cursor)` → GET /api/inbox?cursor=...
- etc.

---

## 5. Plugin Manifest (plugin.json)

### MCP Server Configuration
```json
{
  "name": "interlock",
  "version": "0.2.0",
  "description": "MCP server for intermute file reservation and agent coordination.",
  "mcpServers": {
    "interlock": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERMUTE_SOCKET": "/var/run/intermute.sock",
        "INTERMUTE_URL": "http://127.0.0.1:7338"
      }
    }
  }
}
```

### Key Points
- **Type:** `stdio` (Claude Code will invoke the command and communicate via JSON-RPC on stdin/stdout)
- **Command:** Points to `launch-mcp.sh` (not the binary directly, allowing auto-build)
- **Environment Variables:** Pre-populated with intermute connection details
  - `INTERMUTE_SOCKET`: Unix socket path (tried first)
  - `INTERMUTE_URL`: TCP fallback if socket unavailable

### No postInstall Hook Required
The `launch-mcp.sh` wrapper handles the first-run `go build`, eliminating the need for a postInstall hook and making the plugin work immediately after installation.

---

## 6. Launch Script (bin/launch-mcp.sh)

### Full Implementation
```bash
#!/usr/bin/env bash
# Launcher for interlock-mcp: auto-builds if binary is missing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="${SCRIPT_DIR}/interlock-mcp"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ ! -x "$BINARY" ]]; then
    # Check Go is available
    if ! command -v go &>/dev/null; then
        echo '{"error":"go not found — cannot build interlock-mcp. Install Go 1.23+ and restart."}' >&2
        exit 1
    fi
    # Auto-build on first run
    cd "$PROJECT_ROOT"
    go build -o "$BINARY" ./cmd/interlock-mcp/ 2>&1 >&2
fi

exec "$BINARY" "$@"
```

### Design Rationale
1. **No Pre-compiled Binaries:** Keeps git repo small, avoids cross-platform compilation issues
2. **Build on First Run:** Happens transparently during plugin installation
3. **JSON Error Output:** If Go is missing, returns valid JSON error (Claude Code can parse it)
4. **Exec Pattern:** Final `exec` ensures the binary becomes the process (PID 1 for stdio server)

---

## 7. dispatch.sh Script in hub/clavain

### Location & Purpose
```
/root/projects/Interverse/hub/clavain/scripts/dispatch.sh
```

Wrapper around `codex exec` with sensible defaults for multi-agent dispatch. Not directly related to the MCP server pattern, but shows how agents invoke external tools.

### Usage Signature
```bash
bash dispatch.sh [OPTIONS] "prompt"
bash dispatch.sh [OPTIONS] --prompt-file <file>
```

### Key Flags
- `-C, --cd <DIR>` — Working directory (required for `--inject-docs`)
- `-o, --output-last-message <FILE>` — Output file (supports `{name}` substitution)
- `-s, --sandbox <MODE>` — Sandbox: `read-only` | `workspace-write` | `danger-full-access`
- `-m, --model <MODEL>` — Override model
- `--tier <fast|deep>` — Resolve model from `config/dispatch/tiers.yaml`
- `--inject-docs[=SCOPE]` — Prepend CLAUDE.md and/or AGENTS.md to prompt
- `--name <LABEL>` — Label for tracking (used in `{name}` substitution)
- `--dry-run` — Print the codex command without executing

### Key Features
1. **Tier Resolution:** Maps `fast`/`deep` to models from YAML config
2. **Template Assembly:** Parses task description sections and substitutes into template
3. **JSONL Parsing:** Streams codex output through `awk` for live statusline updates
4. **State File:** Writes `/tmp/clavain-dispatch-$$.json` for visibility in statusline

### Not Related to MCP Servers
The `dispatch.sh` script is a Codex wrapper, not an MCP server. It's included in this analysis because the user asked for it, but it's orthogonal to the Go MCP pattern.

---

## 8. tiers.yaml Configuration

### Location
```
/root/projects/Interverse/hub/clavain/config/dispatch/tiers.yaml
```

### Contents
```yaml
tiers:
  fast:
    model: gpt-5.3-codex-spark
    description: Scoped read-only tasks, exploration, verification, quick reviews
  fast-clavain:
    model: gpt-5.3-codex-spark-xhigh
    description: Clavain interserve-mode default for read-only/administrative tasks
  deep:
    model: gpt-5.3-codex
    description: Generative tasks, implementation, complex reasoning, debates
  deep-clavain:
    model: gpt-5.3-codex-xhigh
    description: Clavain interserve-mode high-complexity/research/flux-drive dispatch

fallback:
  fast: deep        # fast falls back to deep tier's model
  fast-clavain: deep-clavain
  deep-clavain: deep
```

### Usage Pattern
The `dispatch.sh` script reads this file and maps tier names to model strings at runtime. This decouples dispatch calls from model names — when new models ship, only the YAML needs updating.

### Clavain Interserve Mode
When `/root/projects/Interverse/.claude/interserve-toggle.flag` exists, `dispatch.sh` remaps:
- `fast` → `fast-clavain` (cheaper, higher concurrency)
- `deep` → `deep-clavain` (higher compute budget, more resilient)

---

## 9. Complete Replication Checklist for Interserve

### Phase 1: Go Module Setup
- [ ] Create `go.mod` with `github.com/mistakeknot/interserve` and Go 1.23.0
- [ ] Add dependency: `github.com/mark3labs/mcp-go v0.43.2`
- [ ] Create `go.sum` (run `go mod tidy`)

### Phase 2: Directory Structure
- [ ] Create `cmd/interserve-mcp/main.go` (copy pattern from interlock)
- [ ] Create `internal/client/client.go` (adapt from interlock if talking to a service, or remove if stateless)
- [ ] Create `internal/tools/tools.go` (define your 5-15 MCP tools)
- [ ] Create `bin/launch-mcp.sh` (copy exactly from interlock)

### Phase 3: Tool Implementation
- [ ] Define each tool with `mcp.NewTool(...)` + parameter builders
- [ ] Implement Handler functions with proper type assertions
- [ ] Use helper functions: `toStringSlice()`, `intOr()`, `boolOr()`, `stringOr()`, `jsonResult()`
- [ ] Call downstream services via HTTP client methods

### Phase 4: Plugin Manifest
- [ ] Create `.claude-plugin/plugin.json` with:
  - `mcpServers.interserve.type = "stdio"`
  - `mcpServers.interserve.command = "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh"`
  - `mcpServers.interserve.env` with any necessary connection details

### Phase 5: Build & Test
- [ ] Run `go build -o bin/interserve-mcp ./cmd/interserve-mcp/`
- [ ] Test locally: `INTERMUTE_SOCKET=/var/run/intermute.sock bin/interserve-mcp`
- [ ] Install plugin: `claude plugins install <path-or-repo>`
- [ ] Verify tools appear in Claude Code with `@` menu

### Phase 6: Hooks & Documentation (Optional)
- [ ] Create `hooks/hooks.json` if you need SessionStart/SessionEnd hooks
- [ ] Add bash hook scripts if needed
- [ ] Document in `CLAUDE.md` and `AGENTS.md`

---

## 10. Technical Patterns & Gotchas

### Stdio Server Essentials
1. **No Logging to Stdout:** The MCP server writes JSON-RPC on stdout; any other output breaks the protocol
2. **Stderr is Safe:** Use `fmt.Fprintf(os.Stderr, ...)` for debug logs
3. **Exit Codes:** Return 1 on fatal error, 0 on success
4. **Context Handling:** Each tool handler receives a `context.Context` (honor cancellation)

### Tool Result Formats
- **Success:** `mcp.NewToolResultText(jsonString)` or `mcp.NewToolResultJSON(value)`
- **Error:** `mcp.NewToolResultError(message)` — still returns exit code 0 (error is in JSON response)

### HTTP Client Pattern
- Use `net/http.Client` with 10-second timeout
- Support Unix socket via custom `DialContext`
- Support TCP fallback (default: `127.0.0.1:PORT`)
- Use environment variables for connection details (socket path, base URL)

### Argument Type Coercion
JSON-RPC always sends numbers as `float64` and booleans as `bool`. The helper functions handle casting:
```go
intOr(args["ttl_minutes"], 15)  // float64 → int with fallback
boolOr(args["exclusive"], true) // bool with fallback
```

### Environment Detection Fallback Chain
Implement graceful degradation:
1. Explicit env var (`INTERSERVE_AGENT_ID`)
2. Service-provided var (`INTERMUTE_AGENT_ID`)
3. Session ID from Claude Code (`CLAUDE_SESSION_ID`)
4. Hostname + PID as last resort

---

## 11. Critical Design Decision Summary

| Decision | Rationale |
|----------|-----------|
| **Language: Go** | Fast startup, single binary, no runtime deps |
| **MCP Library: mark3labs/mcp-go** | Minimal, focused, handles JSON-RPC protocol details |
| **Stdio Transport** | Simple, works over SSH/Mosh, no socket/port management |
| **Launch Script Instead of Binary** | Smaller repo, build on first run, transparent to user |
| **HTTP Client for Downstream** | Standard library only, Unix socket + TCP, flexible |
| **No Logging Framework** | Stderr is sufficient for dev, keep binary small |
| **Tool Registration in RegisterAll()** | Explicit, auditable, easy to reorder/deprecate |
| **Context-Aware Handlers** | Cancellation support, no goroutine leaks |

---

## 12. Files to Copy As-Is for Interserve

```
✓ bin/launch-mcp.sh              (exact copy, just change version number)
✓ helpers in tools.go            (toStringSlice, intOr, boolOr, stringOr, jsonResult)
✓ main.go structure              (adapt env var names, keep pattern)
✓ client option builders          (WithSocketPath, WithBaseURL, WithAgentID, etc.)
```

---

## References

**Interlock Plugin Root:** `/root/projects/Interverse/plugins/interlock/`

**Key Files:**
- `go.mod` — Module definition
- `cmd/interlock-mcp/main.go` — Entry point (120 lines)
- `internal/tools/tools.go` — 11 tool definitions (745 lines)
- `internal/client/client.go` — HTTP client (300+ lines)
- `bin/launch-mcp.sh` — Auto-build launcher (23 lines)
- `.claude-plugin/plugin.json` — MCP server config

**Related Documentation:**
- `/root/projects/Interverse/hub/clavain/scripts/dispatch.sh` — Multi-agent dispatch wrapper (610 lines)
- `/root/projects/Interverse/hub/clavain/config/dispatch/tiers.yaml` — Model tier config

