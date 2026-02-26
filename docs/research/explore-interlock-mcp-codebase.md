# Interlock MCP Server Codebase Exploration

**Date:** 2026-02-23  
**Repository:** `/home/mk/projects/Demarch/interverse/interlock/`  
**Purpose:** Understanding Go MCP server structure, tool registration patterns, negotiation protocol, and client architecture.

---

## 1. Go MCP Server Structure

### Entry Point: `cmd/interlock-mcp/main.go`

**Key components:**
- Creates intermute client with environment-based configuration (socket path, URL, agent ID, project, agent name)
- Initializes MCP server using `mark3labs/mcp-go v0.43.2` library
- Registers all tools via `tools.RegisterAll(s, c)` — single function call that wires up all 11 tools
- Serves over stdio: `server.ServeStdio(s)`

**Agent identification hierarchy:**
1. `INTERLOCK_AGENT_ID` env var
2. `INTERMUTE_AGENT_ID` env var
3. `CLAUDE_SESSION_ID` env var (prefixed with "claude-")
4. Fallback: `hostname-pid`

**Project identification:**
1. `INTERLOCK_PROJECT` env var
2. `INTERMUTE_SOCKET` env var
3. Current working directory basename (fallback)

**File locations:**
- Entry point: `/home/mk/projects/Demarch/interverse/interlock/cmd/interlock-mcp/main.go`
- Client package: `/home/mk/projects/Demarch/interverse/interlock/internal/client/`
- Tools package: `/home/mk/projects/Demarch/interverse/interlock/internal/tools/`

---

## 2. Tool Registration Pattern

### `RegisterAll` Function Signature

**Location:** `/home/mk/projects/Demarch/interverse/interlock/internal/tools/tools.go:27-42`

```go
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

### Tool Definition Pattern (Example: `reserveFiles`)

**Location:** Lines 46-98

**Structure:**
```go
func reserveFiles(c *client.Client) server.ServerTool {
	return server.ServerTool{
		Tool: mcp.NewTool("reserve_files",
			mcp.WithDescription("..."),
			mcp.WithArray("patterns",
				mcp.Description("Glob patterns for files to reserve (e.g. 'src/router.go', 'internal/http/*.go')"),
				mcp.Required(),
				mcp.WithStringItems(),
			),
			mcp.WithString("reason",
				mcp.Description("Why you're reserving these files"),
				mcp.Required(),
			),
			mcp.WithNumber("ttl_minutes",
				mcp.Description("Reservation duration in minutes (default: 15)"),
			),
			mcp.WithBoolean("exclusive",
				mcp.Description("Whether the reservation is exclusive (default: true)"),
			),
		),
		Handler: func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			// Extract arguments
			args := req.GetArguments()
			patterns := toStringSlice(args["patterns"])
			reason, _ := args["reason"].(string)
			ttl := intOr(args["ttl_minutes"], 15)
			exclusive := boolOr(args["exclusive"], true)

			// Validation
			if len(patterns) == 0 {
				return mcp.NewToolResultError("patterns is required"), nil
			}

			// Call client method
			r, err := c.CreateReservation(ctx, p, reason, ttl, exclusive)
			
			// Return result
			return jsonResult(res)
		},
	}
}
```

**Pattern characteristics:**
- Each tool function takes `*client.Client` and returns `server.ServerTool`
- Tool definition uses fluent MCP builder API (`mcp.NewTool`, `WithString`, `WithArray`, etc.)
- Handler is a closure over the client
- Arguments extracted via type assertion with fallback helpers: `toStringSlice()`, `intOr()`, `boolOr()`, `stringOr()`
- Results serialized via `jsonResult()` helper (JSON marshaling + mcp.NewToolResultText)
- Error responses use `mcp.NewToolResultError()` for validation + API errors

---

## 3. All 11 Tools & Schemas

### Reservation Tools (3)

#### 1. `reserve_files`
- **Purpose:** Reserve one or more file patterns
- **Parameters:**
  - `patterns` (array of strings, required): glob patterns
  - `reason` (string, required): reservation reason
  - `ttl_minutes` (number, optional): duration (default 15)
  - `exclusive` (boolean, optional): exclusive lock (default true)
- **Response:** `{ reservations: [], errors: []string }`
- **Handler:** Creates reservation via `c.CreateReservation()` per pattern, collects errors
- **Signal:** Emits "reserve" signal on success (fire-and-forget)

#### 2. `release_files`
- **Purpose:** Release specific reservations by ID
- **Parameters:**
  - `reservation_ids` (array of strings, required): IDs to release
- **Response:** `{ released: []string, errors: []any }`
- **Handler:** Deletes reservation via `c.DeleteReservation()` per ID
- **Signal:** Emits "release" signal

#### 3. `release_all`
- **Purpose:** Release all active reservations for current agent
- **Parameters:** None
- **Response:** `{ released_count: int }`
- **Handler:** Calls `c.ListReservations(agent=current, project=current)`, deletes all active

### Conflict & Listing Tools (2)

#### 4. `check_conflicts`
- **Purpose:** Dry-run conflict check (no reservation created)
- **Parameters:**
  - `patterns` (array of strings, required): patterns to check
- **Response:** `{ conflicts: []any, clear: []string }`
- **Handler:** Calls `c.CheckConflicts()` per pattern, returns conflicts or clear status

#### 5. `my_reservations`
- **Purpose:** List current agent's active reservations
- **Parameters:** None
- **Response:** `[]client.Reservation` (JSON serialized)
- **Handler:** Calls `c.ListReservations(agent=current, project=current)`

### Messaging Tools (3)

#### 6. `send_message`
- **Purpose:** Send direct message to another agent
- **Parameters:**
  - `to` (string, required): recipient agent ID or name
  - `body` (string, required): message body
- **Response:** `{ sent: true, to: string }`
- **Handler:** Calls `c.SendMessage(to, body)`
- **Signal:** Emits "message" signal

#### 7. `fetch_inbox`
- **Purpose:** Fetch inbox messages + check for negotiation timeouts
- **Parameters:**
  - `cursor` (string, optional): pagination cursor
- **Response:** 
  ```json
  {
    "messages": [],
    "next_cursor": "string",
    "negotiation_timeout_error": "error string (optional)",
    "negotiation_timeouts": [NegotiationTimeout] (optional)
  }
  ```
- **Handler:** Calls `c.FetchInbox(cursor)` + `c.CheckExpiredNegotiations()`
- **Signal:** Emits "message" signal if messages > 0

#### 8. `list_agents`
- **Purpose:** List agents, optionally filtered by capability tag
- **Parameters:**
  - `capability` (string, optional): capability tag or comma-separated OR list
- **Response:** `[]client.Agent` (JSON)
- **Handler:** Calls `c.ListAgents()` or `c.DiscoverAgents(capabilities)` if filter provided

### Negotiation Tools (3)

#### 9. `request_release` [DEPRECATED]
- **Purpose:** Legacy release request (use negotiate_release instead)
- **Parameters:**
  - `agent_name` (string, required): target agent
  - `pattern` (string, required): file pattern
  - `reason` (string, required): release reason
- **Response:** `{ sent: true, to: string, type: "release-request" }`
- **Handler:** Marshals JSON message with `type: "release-request"`, calls `c.SendMessage()`
- **Message format:**
  ```json
  {
    "type": "release-request",
    "pattern": "string",
    "reason": "string",
    "requester": "agent_name"
  }
  ```

#### 10. `negotiate_release`
- **Purpose:** Request file release with urgency + optional blocking wait
- **Parameters:**
  - `agent_name` (string, required): target agent name/ID
  - `file` (string, required): file pattern
  - `reason` (string, required): why file is needed
  - `urgency` (string, optional): "normal" or "urgent" (default "normal")
  - `wait_seconds` (number, optional): blocking wait timeout (0 = no wait)
- **Response (no wait):** `{ status: "pending", thread_id: string, to: string, urgency: string }`
- **Response (with wait):** 
  - On `release-ack`: `{ status: "released", thread_id, released_by, reason }`
  - On `release-defer`: `{ status: "deferred", thread_id, eta_minutes, reason }`
  - On timeout: `{ status: "timeout", thread_id, waited: seconds }`
- **Handler algorithm:**
  1. Validate parameters
  2. `c.CheckConflicts(file)` to verify agent holds reservation
  3. Generate random `thread_id` via `generateNegotiateID()` (UUID-like format)
  4. Marshal release-request message:
     ```json
     {
       "type": "release-request",
       "file": "string",
       "reason": "string",
       "requester": "agent_name",
       "urgency": "normal|urgent",
       "thread_id": "string"
     }
     ```
  5. Call `c.SendMessageFull()` with thread_id, subject, importance (urgent→urgent, else normal), ack_required (urgent→true)
  6. If `wait_seconds > 0`:
     - Poll negotiation thread every 2 seconds until timeout or response
     - Call `pollNegotiationThread()` which fetches thread and scans for release-ack/release-defer messages
     - Return status as soon as response detected
     - Max 3 consecutive poll errors before failing
- **Timeout constants:** `NormalTimeoutMinutes=10`, `UrgentTimeoutMinutes=5`, `NegotiationPollInterval=2s`

#### 11. `respond_to_release`
- **Purpose:** Respond to release negotiation (release now or defer with ETA)
- **Parameters:**
  - `thread_id` (string, required): negotiation thread ID
  - `requester` (string, required): requester agent ID
  - `action` (string, required): "release" or "defer"
  - `file` (string, required): file pattern being negotiated
  - `eta_minutes` (number, optional): for defer only, max 60 (clamped)
  - `reason` (string, optional): defer reason
- **Response (release):** `{ action: "release", thread_id, file, released: int }`
- **Response (defer):** `{ action: "defer", thread_id, file, eta_minutes, reason }`
- **Handler algorithm:**
  1. Validate parameters
  2. If action="release":
     - Call `c.ReleaseByPattern(agent_id=current, pattern=file)` to release matching reservations
     - Marshal and send release-ack message:
       ```json
       {
         "type": "release-ack",
         "file": "string",
         "released": true,
         "released_by": "agent_name",
         "released_cnt": int
       }
       ```
     - Return released count
  3. If action="defer":
     - Clamp eta_minutes to [0, 60]
     - Marshal and send release-defer message:
       ```json
       {
         "type": "release-defer",
         "file": "string",
         "eta_minutes": int,
         "reason": "string",
         "released": false
       }
       ```
     - Return defer details
  4. Both send via `c.SendMessageFull()` with thread_id and subject matching action type

---

## 4. Release Response Protocol (iv-1aug)

### Message Types in Thread

All negotiation messages use JSON-structured body with `type` field:

#### `release-request` (from negotiate_release)
```json
{
  "type": "release-request",
  "file": "pattern/glob",
  "reason": "why needed",
  "requester": "agent_name",
  "urgency": "normal|urgent",
  "thread_id": "uuid-like-string"
}
```
- Subject: "release-request"
- Importance: "urgent" if urgency="urgent", else "normal"
- AckRequired: true if urgency="urgent"

#### `release-ack` (from respond_to_release action=release)
```json
{
  "type": "release-ack",
  "file": "pattern/glob",
  "released": true,
  "released_by": "agent_name",
  "released_cnt": int
}
```
- Subject: "release-ack"
- Indicates holder has released matching reservations

#### `release-defer` (from respond_to_release action=defer)
```json
{
  "type": "release-defer",
  "file": "pattern/glob",
  "eta_minutes": int,
  "reason": "why deferring",
  "released": false
}
```
- Subject: "release-defer"
- Indicates holder cannot release yet, includes ETA

### Polling & Detection (`pollNegotiationThread`)

**Location:** `/home/mk/projects/Demarch/interverse/interlock/internal/tools/tools.go:703-733`

**Algorithm:**
1. Fetch all messages in thread via `c.FetchThread(thread_id)`
2. Iterate messages in reverse (newest first)
3. For each message:
   - Try to extract message type from `msg.Body` JSON's `type` field
   - Fall back to `msg.Subject` if JSON parsing fails
   - Return on first match:
     - `"release-ack"` → status="released", payload with released_by and reason
     - `"release-defer"` → status="deferred", payload with eta_minutes and reason
4. Return empty string if no terminal message found (polling continues)

**Return signature:**
```go
func pollNegotiationThread(ctx context.Context, c *client.Client, threadID string) (status string, payload map[string]any, error error)
```

---

## 5. Intermute Client (`internal/client/client.go`)

### Client Initialization

**Constructor:** `NewClient(opts ...Option)`
- Default: HTTP to `http://127.0.0.1:7338` with 10s timeout
- Unix socket support: `WithSocketPath(path)` option
- TCP fallback: `WithBaseURL(url)` option
- Agent metadata: `WithAgentID()`, `WithProject()`, `WithAgentName()`

### Key API Methods

#### File Reservation
- `CreateReservation(ctx, pattern, reason, ttlMinutes, exclusive)` → `*Reservation, error`
- `DeleteReservation(ctx, id)` → `error`
- `ListReservations(ctx, filters)` → `[]Reservation, error`
- `CheckConflicts(ctx, pattern)` → `[]ConflictDetail, error`
- `ReleaseByPattern(ctx, agentID, pattern)` → `int, error` (count released)

#### Messaging
- `SendMessage(ctx, to, body)` → `error`
- `SendMessageFull(ctx, to, body, MessageOptions)` → `error`
  - MessageOptions: ThreadID, Subject, Importance, AckRequired
- `FetchInbox(ctx, cursor)` → `[]Message, nextCursor, error`
- `FetchThread(ctx, threadID)` → `[]Message, error`
  - Fallback: if endpoint 404, pages through inbox and filters by thread_id

#### Agent Discovery
- `ListAgents(ctx)` → `[]Agent, error`
- `DiscoverAgents(ctx, capabilities)` → `[]Agent, error` (OR matching on tags)
- `RegisterAgent(ctx)` → `*Agent, error`

#### Negotiation Timeout Checks
- `CheckExpiredNegotiations(ctx)` → `[]NegotiationTimeout, error`
  - Advisory only: does NOT force-release
  - Identifies release-request messages that exceed timeout thresholds
  - Returns timeout info only if:
    - Message is `type: "release-request"`
    - Age exceeds `NormalTimeoutMinutes` (10) or `UrgentTimeoutMinutes` (5)
    - Thread has no `release-ack` response
  - Exported constants: `NormalTimeoutMinutes=10`, `UrgentTimeoutMinutes=5`, `NegotiationPollInterval=2*time.Second`

### Data Structures

**Reservation:**
```go
type Reservation struct {
	ID          string // ID
	AgentID     string
	Project     string
	PathPattern string
	Exclusive   bool
	Reason      string
	ExpiresAt   string // RFC3339 timestamp
	IsActive    bool
}
```

**Message:**
```go
type Message struct {
	ID          string
	MessageID   string
	From        string
	To          []string
	Body        string
	ThreadID    string
	Subject     string
	Importance  string
	AckRequired bool
	Timestamp   string // RFC3339
	CreatedAt   string // RFC3339
	Read        bool
}
```

**ConflictDetail:**
```go
type ConflictDetail struct {
	ReservationID string
	AgentID       string
	HeldBy        string
	Pattern       string
	Reason        string
	ExpiresAt     string
}
```

**Agent:**
```go
type Agent struct {
	AgentID      string
	Name         string
	Project      string
	Capabilities []string
	Status       string
	LastSeen     string
}
```

### HTTP Request Pattern

**All requests:**
- Method: GET/POST/DELETE as appropriate
- Base URL from client config (default `http://127.0.0.1:7338`)
- Header: `Content-Type: application/json` (POST/PATCH)
- Header: `X-Agent-ID: {agentID}` (custom)
- Timeout: 10 seconds

**Status code handling:**
- 409 Conflict → parse as `ConflictError{ Conflicts: []ConflictDetail }`
- 4xx/5xx → parse as `IntermuteError{ Code, Message, RetryAfter }`
- 2xx → parse response JSON into `out` parameter if provided

---

## 6. Reservation System Data Model

### Reservation Lifecycle

1. **Create:** `POST /api/reservations`
   - Request: `{ agent_id, project, path_pattern, exclusive, reason, ttl_minutes? }`
   - Response: `Reservation{ ID, AgentID, Project, PathPattern, Exclusive, Reason, ExpiresAt, IsActive }`

2. **List:** `GET /api/reservations?agent=X&project=Y`
   - Query params: `agent`, `project` (optional filters)
   - Response: `{ reservations: []Reservation }`

3. **Check Conflicts:** `GET /api/reservations/check?project=Y&pattern=P&exclusive=true`
   - Query params: `project`, `pattern`, `exclusive`
   - Response: `{ conflicts: []ConflictDetail }` (or 404 fallback to client-side check)

4. **Release (Delete):** `DELETE /api/reservations/{id}`
   - No response body

### Conflict Detection

- Exclusive reservations block other exclusive or any reservations on overlapping patterns
- Overlap check: `PatternsOverlap(existing, candidate)` (simple prefix/glob check)
  ```go
  func PatternsOverlap(existing, candidate string) bool {
      e := strings.TrimSuffix(existing, "*")
      c := strings.TrimSuffix(candidate, "*")
      return strings.HasPrefix(e, c) || strings.HasPrefix(c, e)
  }
  ```
- 409 response triggers `ConflictError` with full conflict details

---

## 7. Plugin Configuration & Deployment

### Plugin Manifest (`.claude-plugin/plugin.json`)

**Location:** `/home/mk/projects/Demarch/interverse/interlock/.claude-plugin/plugin.json`

```json
{
  "name": "interlock",
  "version": "0.2.2",
  "description": "MCP server for intermute file reservation and agent coordination...",
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
  },
  "skills": [
    "./skills/conflict-recovery",
    "./skills/coordination-protocol"
  ],
  "commands": [
    "./commands/join.md",
    "./commands/leave.md",
    "./commands/setup.md",
    "./commands/status.md"
  ]
}
```

### Build & Launch

**Build:**
```bash
bash scripts/build.sh
```

**Launch script:** `bin/launch-mcp.sh` (stdio wrapper)

**Intermute connection:**
- Unix socket preferred: `${INTERMUTE_SOCKET}` env var
- TCP fallback: `${INTERMUTE_URL}` (default `http://127.0.0.1:7338`)
- Agent metadata from environment or derived from session context

---

## 8. Implementation Pattern Summary

### For Adding a New Tool

**Template:**
```go
func myNewTool(c *client.Client) server.ServerTool {
	return server.ServerTool{
		Tool: mcp.NewTool("my_tool_name",
			mcp.WithDescription("Brief description of what this tool does."),
			// Parameters
			mcp.WithString("required_param",
				mcp.Description("Description of this parameter"),
				mcp.Required(),
			),
			mcp.WithNumber("optional_param",
				mcp.Description("Optional parameter"),
				// No mcp.Required() — optional by default
			),
		),
		Handler: func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			// Extract and convert arguments
			args := req.GetArguments()
			reqParam, _ := args["required_param"].(string)
			optParam := intOr(args["optional_param"], 0)

			// Validation
			if reqParam == "" {
				return mcp.NewToolResultError("required_param is required"), nil
			}

			// Call client method
			result, err := c.SomeMethod(ctx, reqParam, optParam)
			if err != nil {
				return mcp.NewToolResultError(fmt.Sprintf("operation failed: %v", err)), nil
			}

			// Emit signal (optional)
			emitSignal("tool_name", fmt.Sprintf("did something with %s", reqParam))

			// Return result
			return jsonResult(result)
		},
	}
}
```

**Then add to `RegisterAll()`:**
```go
func RegisterAll(s *server.MCPServer, c *client.Client) {
	s.AddTools(
		// ... existing tools ...
		myNewTool(c),
	)
}
```

### Key Patterns

1. **Argument extraction:** Use type assertions with fallbacks: `intOr()`, `boolOr()`, `stringOr()`, `toStringSlice()`
2. **Error handling:** Return error responses via `mcp.NewToolResultError()` for validation; return API errors as tool result text (JSON)
3. **JSON serialization:** Always use `jsonResult()` helper to marshal and wrap in mcp.NewToolResultText
4. **Idempotency:** Operations on reservations are idempotent (204 on already-deleted, etc.)
5. **Signals:** Emit fire-and-forget signals via `emitSignal(eventType, text)` for UI feedback
6. **Thread safety:** No shared state — each tool invocation is independent closure over client

### MCP Library Usage (`github.com/mark3labs/mcp-go`)

- `mcp.NewTool(name, ...options)` — create tool definition
- `mcp.WithString()`, `WithNumber()`, `WithBoolean()`, `WithArray()` — parameter builders
- `mcp.Required()` — mark param as required
- `mcp.WithStringItems()` — set array element type
- `mcp.WithDescription()` — param description
- `mcp.NewToolResultError(msg)` — error response
- `mcp.NewToolResultText(msg)` — text response (JSON for structured results)
- `server.MCPServer.AddTools(tools...)` — register tools
- `server.ServeStdio(s)` — start server on stdio

---

## 9. Test Coverage & Files

**Location:** `/home/mk/projects/Demarch/interverse/interlock/`

| Path | Purpose |
|------|---------|
| `cmd/interlock-mcp/main.go` | Entry point, agent ID/project detection |
| `internal/client/client.go` | HTTP client for intermute API |
| `internal/client/client_test.go` | Client unit tests |
| `internal/tools/tools.go` | All 11 tool definitions + helpers |
| `.claude-plugin/plugin.json` | Plugin manifest & MCP server config |
| `AGENTS.md` | Development guide |
| `CLAUDE.md` | Quick reference |

---

## 10. Key Takeaways for New Tool Development

1. **Registration is decoupled:** Each tool is a function that returns `server.ServerTool`. Add new tool functions and register in `RegisterAll()`.

2. **Arguments are untyped:** All MCP arguments come as `map[string]any`. Use helper functions for safe type conversion.

3. **Errors have dual channels:**
   - Validation errors: `mcp.NewToolResultError()` — short-circuits the response
   - API errors: Include in JSON result body for structured error reporting

4. **Negotiation is message-based:** Threading is built on intermute's messaging infrastructure. Tools send JSON-structured messages and poll thread for responses. Message type detection is flexible (JSON body `type` field or message `Subject`).

5. **Thread IDs are generated client-side:** `generateNegotiateID()` creates UUIDs or fallback format. Passed to `SendMessageFull()` to establish thread association.

6. **Timeout escalation is advisory:** `CheckExpiredNegotiations()` reports timeout-eligible negotiations but does not force-release. Holder sees advisory context on next edit (via hook) and can decide to respond.

7. **Pattern overlap is prefix-based:** Simple glob-aware overlap check for conflict detection. No full glob matching.

8. **Intermute client handles API versioning:** Falls back to client-side conflict checking if `/api/reservations/check` is not available (older intermute versions).

---

**End of Analysis**
