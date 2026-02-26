# Plan: Broadcast Messaging (iv-7kg37)

**Bead:** iv-7kg37
**Complexity:** 2/5 (simple)
**Dependencies:** iv-t4pia (contact policies) ✅, iv-00liv (topic messages) ✅, iv-bg0a0 (adopt patterns) ✅

## Goal

Add a `broadcast_message` capability: send a message to all agents in a project, filtered by contact policies, tagged with a topic, and rate-limited to prevent storms.

## Design Decisions

1. **Server-side fan-out** — new `POST /api/broadcast` endpoint resolves recipients via `ListAgents`, excludes sender, feeds the full `To` list through existing `filterByPolicy`. No client-side agent enumeration needed.
2. **Reuse `handleSendMessage` internals** — broadcast shares the same policy filtering, event append, and SSE notification path. Extract the send-after-validation logic into a shared helper.
3. **Rate limiting via in-memory token bucket on Service** — simple `sync.Mutex`-guarded counter per (project, sender) pair, resets every minute. No new schema. Returns HTTP 429 with `Retry-After` header.
4. **Topic required on broadcast** — broadcasts without a topic are rejected (400). This ensures discoverability via `TopicMessages`.

## Tasks

### Task 1: Add `handleBroadcast` HTTP handler

**File:** `core/intermute/internal/http/handlers_messages.go`

Add request/response types:
```go
type broadcastRequest struct {
    From    string `json:"from"`
    Project string `json:"project"`
    Topic   string `json:"topic"`
    Body    string `json:"body"`
    Subject string `json:"subject,omitempty"`
}

type broadcastResponse struct {
    MessageID  string   `json:"message_id"`
    Cursor     uint64   `json:"cursor"`
    Delivered  int      `json:"delivered"`
    Denied     []string `json:"denied,omitempty"`
}
```

Handler logic:
1. Validate: `from`, `project`, `topic`, `body` all required (400 if missing)
2. Auth: same API key project scoping as `handleSendMessage`
3. Call `s.store.ListAgents(ctx, project, nil)` to get all project agents
4. Build `To` list: all agent IDs except `req.From` (sender excludes self)
5. If `To` is empty → return 200 with `delivered: 0` (no other agents)
6. Check rate limit: `s.checkBroadcastRate(project, req.From)` → 429 if exceeded
7. Run `s.filterByPolicy(ctx, project, req.From, "", toList)` (empty threadID — no thread exception for broadcast)
8. If all denied → 403 with `policyDeniedResponse`
9. Build `core.Message` with `To: allowedTo`, append event, SSE broadcast per recipient
10. Return `broadcastResponse` with `delivered: len(allowedTo)`

### Task 2: Rate limiter on Service

**File:** `core/intermute/internal/http/service.go`

Add a minimal per-sender rate limiter:
```go
type broadcastLimiter struct {
    mu      sync.Mutex
    buckets map[string]*bucket // key: "project:sender"
}

type bucket struct {
    count   int
    resetAt time.Time
}
```

- `checkBroadcastRate(project, sender string) bool` — returns true if rate exceeded
- Limit: 10 broadcasts per minute per sender per project
- On first call or after reset window: initialize count=1, resetAt=now+60s
- On subsequent calls: if `time.Now().After(resetAt)`, reset; else increment and check `count > 10`
- Lazy cleanup: no background goroutine — stale entries evicted on next check

Add `limiter *broadcastLimiter` field to `Service`, initialized in `NewService`.

### Task 3: Register broadcast route

**File:** `core/intermute/internal/http/router.go` and `router_domain.go`

Add `mux.Handle("/api/broadcast", wrap(svc.handleBroadcast))` to both router constructors.

### Task 4: Client `BroadcastMessage` method

**File:** `interverse/interlock/internal/client/client.go`

```go
type BroadcastOptions struct {
    Subject string
}

type BroadcastResult struct {
    MessageID string   `json:"message_id"`
    Delivered int      `json:"delivered"`
    Denied    []string `json:"denied,omitempty"`
}

func (c *Client) BroadcastMessage(ctx context.Context, topic, body string, opts BroadcastOptions) (*BroadcastResult, error) {
    payload := map[string]any{
        "project": c.project,
        "from":    c.agentID,
        "topic":   topic,
        "body":    body,
    }
    if opts.Subject != "" {
        payload["subject"] = opts.Subject
    }
    var result BroadcastResult
    err := c.doJSON(ctx, "POST", "/api/broadcast", payload, &result)
    return &result, err
}
```

### Task 5: MCP `broadcast_message` tool

**File:** `interverse/interlock/internal/tools/tools.go`

New tool registration:
- Name: `broadcast_message`
- Params: `topic` (required), `body` (required), `subject` (optional)
- Handler: calls `c.BroadcastMessage(ctx, topic, body, opts)`
- Response: JSON with `message_id`, `delivered`, `denied`
- Add to `RegisterAll` (16 tools total)

### Task 6: Tests

**File:** `core/intermute/internal/storage/sqlite/broadcast_test.go`

Tests using `newRaceStore` + `sendTestMessage` helpers:
1. `TestBroadcast_SendAndReceive` — register 3 agents, broadcast from agent-1, verify agents 2 & 3 receive via inbox
2. `TestBroadcast_PolicyFiltering` — agent with `block_all` excluded, agent with `contacts_only` excluded (sender not in contacts), `open` agent receives
3. `TestBroadcast_SelfExclusion` — sender not in own To list
4. `TestBroadcast_TopicRequired` — empty topic returns 400

HTTP-level tests are preferred but the project pattern uses store-level tests. We'll test the handler directly since broadcast logic lives there.

**File:** `core/intermute/internal/http/broadcast_test.go`

Use `httptest.NewServer` with the router to test:
1. Full broadcast flow (register agents → broadcast → check inboxes)
2. Rate limiting (11th broadcast in <60s returns 429)
3. Topic requirement validation
4. Auth/project scoping

## Acceptance Criteria

- [x] `broadcast_message` MCP tool sends to all agents in a project
- [x] Respects contact policies: block_all excluded, contacts_only excluded unless sender in contacts
- [x] Broadcast messages tagged with a topic for discoverability
- [x] Rate limiting prevents broadcast storms (10/min/sender/project)

## Files Changed

| File | Change |
|------|--------|
| `core/intermute/internal/http/handlers_messages.go` | `handleBroadcast` handler + types |
| `core/intermute/internal/http/service.go` | `broadcastLimiter` + rate check |
| `core/intermute/internal/http/router.go` | Route registration |
| `core/intermute/internal/http/router_domain.go` | Route registration |
| `core/intermute/internal/http/broadcast_test.go` | HTTP-level broadcast tests |
| `interverse/interlock/internal/client/client.go` | `BroadcastMessage` method |
| `interverse/interlock/internal/tools/tools.go` | `broadcast_message` tool (16 total) |
