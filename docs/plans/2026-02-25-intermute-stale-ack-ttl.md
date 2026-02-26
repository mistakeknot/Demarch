# Plan: Stale-Ack TTL Views (iv-ho4q1)

**Bead:** iv-ho4q1
**Complexity:** 2/5 (simple — mostly pre-implemented)

## Goal

Expose stale acknowledgment queries through the interlock MCP tool layer. The intermute storage, HTTP handler, and tests are already implemented.

## Pre-existing Implementation (already done)

- `core.StaleAck` struct in `models.go`
- `InboxStaleAcks(ctx, project, agentID, ttlSeconds, limit)` in Store interface
- SQLite query joining `message_recipients` + `messages` with TTL filter
- ResilientStore wrapper
- InMemory stub
- `GET /api/inbox/{agent}/stale-acks?project=X&ttl_seconds=N&limit=M` HTTP handler
- `staleAcksResponse` and `staleAckItem` types
- 2 HTTP-level tests passing

## Remaining Tasks

### Task 1: Client `FetchStaleAcks` method

**File:** `interverse/interlock/internal/client/client.go`

```go
type StaleAckItem struct {
    ID         string `json:"id"`
    ThreadID   string `json:"thread_id"`
    From       string `json:"from"`
    Subject    string `json:"subject"`
    Topic      string `json:"topic"`
    Body       string `json:"body"`
    Importance string `json:"importance"`
    Kind       string `json:"kind"`
    AgeSeconds int    `json:"age_seconds"`
    Read       bool   `json:"read"`
    CreatedAt  string `json:"created_at"`
}

func (c *Client) FetchStaleAcks(ctx, ttlSeconds, limit int) ([]StaleAckItem, error)
```

### Task 2: MCP `fetch_stale_acks` tool

**File:** `interverse/interlock/internal/tools/tools.go`

- Name: `fetch_stale_acks`
- Params: `ttl_seconds` (required, int), `limit` (optional, int)
- Handler: calls `c.FetchStaleAcks(ctx, ttl, limit)`
- Add to `RegisterAll` (17 tools total)

## Files Changed

| File | Change |
|------|--------|
| `interverse/interlock/internal/client/client.go` | `StaleAckItem` type + `FetchStaleAcks` method |
| `interverse/interlock/internal/tools/tools.go` | `fetch_stale_acks` tool (17 total) |
