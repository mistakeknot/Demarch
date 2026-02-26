# Plan: Window Identity for Agent Session Persistence (iv-uk7c3)

**Bead:** iv-uk7c3
**Complexity:** 3/5 (moderate)
**Brainstorm:** `docs/brainstorms/2026-02-25-window-identity-brainstorm.md`

## Goal

Add persistent window identity so agents maintain stable IDs across session restarts. Reservations, inbox, and contacts survive because the agent_id doesn't change.

## Tasks

### Task 1: Window identity model + Store interface

**Files:** `core/intermute/internal/core/models.go`, `core/intermute/internal/storage/storage.go`

Add `WindowIdentity` struct to models:
```go
type WindowIdentity struct {
    ID           string
    Project      string
    WindowUUID   string
    AgentID      string
    DisplayName  string
    CreatedAt    time.Time
    LastActiveAt time.Time
    ExpiresAt    *time.Time
}
```

Add to Store interface:
```go
UpsertWindowIdentity(ctx context.Context, wi WindowIdentity) (*WindowIdentity, error)
ListWindowIdentities(ctx context.Context, project string) ([]WindowIdentity, error)
ExpireWindowIdentity(ctx context.Context, project, windowUUID string) error
LookupWindowIdentity(ctx context.Context, project, windowUUID string) (*WindowIdentity, error)
```

Add InMemory stubs.

### Task 2: SQLite schema + implementation

**Files:** `core/intermute/internal/storage/sqlite/schema.sql`, `core/intermute/internal/storage/sqlite/sqlite.go`

Migration: `migrateWindowIdentities` — creates table + unique index on `(project, window_uuid)`.

```sql
CREATE TABLE IF NOT EXISTS window_identities (
  id TEXT PRIMARY KEY,
  project TEXT NOT NULL,
  window_uuid TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_active_at TEXT NOT NULL,
  expires_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_window_project
  ON window_identities(project, window_uuid);
```

Implement:
- `UpsertWindowIdentity` — INSERT OR UPDATE on (project, window_uuid), touch last_active_at
- `ListWindowIdentities` — SELECT WHERE project=? AND (expires_at IS NULL OR expires_at > datetime('now'))
- `ExpireWindowIdentity` — UPDATE SET expires_at = datetime('now') WHERE project=? AND window_uuid=?
- `LookupWindowIdentity` — SELECT WHERE project=? AND window_uuid=? AND not expired

Add ResilientStore wrappers.

### Task 3: HTTP handlers + routes

**Files:** `core/intermute/internal/http/handlers_windows.go` (new), `core/intermute/internal/http/router.go`, `core/intermute/internal/http/router_domain.go`

New handler file:
- `POST /api/windows` — upsert window identity, returns full record
- `GET /api/windows?project=X` — list non-expired for project
- `DELETE /api/windows/{id}` — expire by window UUID (soft delete)

Request/response types:
```go
type upsertWindowRequest struct {
    Project     string `json:"project"`
    WindowUUID  string `json:"window_uuid"`
    AgentID     string `json:"agent_id"`
    DisplayName string `json:"display_name"`
}
type windowResponse struct {
    ID           string  `json:"id"`
    Project      string  `json:"project"`
    WindowUUID   string  `json:"window_uuid"`
    AgentID      string  `json:"agent_id"`
    DisplayName  string  `json:"display_name"`
    CreatedAt    string  `json:"created_at"`
    LastActiveAt string  `json:"last_active_at"`
    ExpiresAt    *string `json:"expires_at,omitempty"`
}
```

### Task 4: Interlock client methods

**File:** `interverse/interlock/internal/client/client.go`

```go
type WindowIdentity struct {
    ID           string  `json:"id"`
    Project      string  `json:"project"`
    WindowUUID   string  `json:"window_uuid"`
    AgentID      string  `json:"agent_id"`
    DisplayName  string  `json:"display_name"`
    CreatedAt    string  `json:"created_at"`
    LastActiveAt string  `json:"last_active_at"`
    ExpiresAt    *string `json:"expires_at,omitempty"`
}

func (c *Client) UpsertWindow(ctx, windowUUID, agentID, displayName string) (*WindowIdentity, error)
func (c *Client) ListWindows(ctx context.Context) ([]WindowIdentity, error)
func (c *Client) LookupWindow(ctx context.Context, windowUUID string) (*WindowIdentity, error)
func (c *Client) ExpireWindow(ctx context.Context, windowUUID string) error
```

### Task 5: MCP tools (3 new → 20 total)

**File:** `interverse/interlock/internal/tools/tools.go`

- `list_window_identities` — list active windows for the project
- `rename_window` — update display_name for a window_uuid (upsert with new name)
- `expire_window` — soft-delete a window identity

### Task 6: Registration script integration

**File:** `interverse/interlock/scripts/interlock-register.sh`

Before registering with intermute:
1. Resolve window UUID: `INTERLOCK_WINDOW_ID` > SHA1-UUID from `TMUX_PANE` > empty
2. If window UUID exists: `GET /api/windows?project=X` → lookup by window_uuid
3. If found: reuse `agent_id` and `display_name` as the registration identity
4. If not found: register normally, then `POST /api/windows` to create the mapping
5. Export `INTERLOCK_WINDOW_ID` to env file for subsequent hooks

### Task 7: Tests

**File:** `core/intermute/internal/http/handlers_windows_test.go` (new)

- `TestWindowUpsert_CreateAndLookup` — create, verify fields, lookup by UUID
- `TestWindowUpsert_TouchOnReuse` — upsert same UUID twice, verify last_active_at updated
- `TestWindowExpire` — expire, verify not returned in list
- `TestWindowList_ProjectScoped` — windows from different projects don't mix

## Acceptance Criteria

- [x] window_identities table mapping tmux window UUIDs to persistent agent names
- [x] TTL-based lifecycle (expires_at) prevents orphan accumulation
- [x] On session start, agent looks up existing identity by window UUID
- [x] Reservations and coordination state preserved across session restarts
- [x] Cleanup via expire_window MCP tool

## Files Changed

| File | Change |
|------|--------|
| `core/intermute/internal/core/models.go` | `WindowIdentity` struct |
| `core/intermute/internal/storage/storage.go` | 4 new Store methods + InMemory stubs |
| `core/intermute/internal/storage/sqlite/schema.sql` | `window_identities` table |
| `core/intermute/internal/storage/sqlite/sqlite.go` | Migration + 4 implementations |
| `core/intermute/internal/storage/sqlite/resilient.go` | 4 ResilientStore wrappers |
| `core/intermute/internal/http/handlers_windows.go` | NEW — 3 HTTP handlers |
| `core/intermute/internal/http/router.go` | Route registration |
| `core/intermute/internal/http/router_domain.go` | Route registration |
| `core/intermute/internal/http/handlers_windows_test.go` | NEW — 4 tests |
| `interverse/interlock/internal/client/client.go` | 4 client methods |
| `interverse/interlock/internal/tools/tools.go` | 3 MCP tools (20 total) |
| `interverse/interlock/scripts/interlock-register.sh` | Window UUID resolution |
