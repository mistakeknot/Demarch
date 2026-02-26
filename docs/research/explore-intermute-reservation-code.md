# Intermute File Reservation System — Code Exploration

**Date:** 2026-02-25  
**Codebase:** `/home/mk/projects/Demarch/core/intermute/`  
**Focus:** SQLite storage layer, HTTP handlers, system initialization, schema, and glob pattern overlap logic

---

## 1. Entry Point & Initialization

### main.go — Storage & Sweeper Setup

**File:** `/home/mk/projects/Demarch/core/intermute/cmd/intermute/main.go`

- **Store initialization (line 53):**
  ```go
  store, err := sqlite.New(dbPath)
  ```
  - Opens SQLite database at `dbPath` (default: `intermute.db`)
  - Applies schema via `applySchema(db)` immediately after opening
  - Wraps store with circuit breaker + retry resilience (line 59):
    ```go
    resilient := sqlite.NewResilient(store)
    ```

- **Sweeper setup (lines 79-81):**
  ```go
  sweeper := sqlite.NewSweeper(store, hub, 60*time.Second, 5*time.Minute)
  sweeper.Start(context.Background())
  ```
  - Interval: 60 seconds
  - Grace period (heartbeat): 5 minutes
  - Started before HTTP router initialization

- **HTTP service & router (lines 83-84):**
  ```go
  svc := httpapi.NewDomainService(resilient).WithBroadcaster(hub)
  router := httpapi.NewDomainRouter(svc, hub.Handler(), auth.Middleware(keyring))
  ```
  - Service receives resilient store + WebSocket broadcaster
  - Router includes auth middleware

- **Graceful shutdown (lines 96-114):**
  1. Sweeper stopped first
  2. HTTP requests drained (5s timeout)
  3. Database closed (WAL checkpointed)

---

## 2. go.mod Dependencies

**File:** `/home/mk/projects/Demarch/core/intermute/go.mod`

```
go 1.24
toolchain go1.24.12

require (
  github.com/google/uuid v1.6.0        (for generating IDs)
  github.com/spf13/cobra v1.10.2       (CLI)
  gopkg.in/yaml.v3 v3.0.1              (YAML support)
  modernc.org/sqlite v1.29.0           (SQLite driver — pure Go, no CGO)
  nhooyr.io/websocket v1.8.7           (WebSocket)
)
```

**SQLite Driver:** Pure Go implementation (`modernc.org/sqlite`)

---

## 3. Database Schema — file_reservations Table

**File:** `/home/mk/projects/Demarch/core/intermute/internal/storage/sqlite/schema.sql`  
**Lines:** 55–69

```sql
CREATE TABLE IF NOT EXISTS file_reservations (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  project TEXT NOT NULL,
  path_pattern TEXT NOT NULL,
  exclusive INTEGER NOT NULL DEFAULT 1,
  reason TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  released_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_reservations_project 
  ON file_reservations(project);
CREATE INDEX IF NOT EXISTS idx_reservations_agent 
  ON file_reservations(agent_id);
CREATE INDEX IF NOT EXISTS idx_reservations_active 
  ON file_reservations(project, expires_at) 
  WHERE released_at IS NULL;
```

### Key Design Decisions

1. **Composite natural key:** `id` is UUID-based (not project+id composite)
2. **Active filter:** `WHERE released_at IS NULL AND expires_at > now()`
3. **Exclusive flag:** 0 = shared, 1 = exclusive (default)
4. **Timestamps:** RFC3339Nano format (UTC)
5. **ReleasedAt:** NULL = unreleased; set on explicit release or sweep

---

## 4. Core Domain Models

**File:** `/home/mk/projects/Demarch/core/intermute/internal/core/models.go`

### Reservation Struct (lines 79–96)

```go
type Reservation struct {
  ID          string        // UUID
  AgentID     string        // Agent holding the lock
  Project     string        // Project scope
  PathPattern string        // Glob pattern (e.g., "pkg/events/*.go")
  Exclusive   bool          // true = exclusive, false = shared
  Reason      string        // Why the reservation was made
  TTL         time.Duration // Time-to-live (only used when creating)
  CreatedAt   time.Time
  ExpiresAt   time.Time
  ReleasedAt  *time.Time    // nil = unreleased
}

// IsActive returns true if reservation is still valid
func (r *Reservation) IsActive() bool {
  return r.ReleasedAt == nil && time.Now().Before(r.ExpiresAt)
}
```

### ConflictDetail Struct (lines 98–106)

```go
type ConflictDetail struct {
  ReservationID string    `json:"reservation_id"`
  AgentID       string    `json:"agent_id"`
  AgentName     string    `json:"held_by"`  // Agent name (from agents table)
  Pattern       string    `json:"pattern"`
  Reason        string    `json:"reason,omitempty"`
  ExpiresAt     time.Time `json:"expires_at"`
}
```

---

## 5. HTTP Handlers — Reservations API

**File:** `/home/mk/projects/Demarch/core/intermute/internal/http/handlers_reservations.go`

### ReservationStore Interface (lines 60–68)

```go
type ReservationStore interface {
  Reserve(ctx context.Context, r core.Reservation) (*core.Reservation, error)
  GetReservation(ctx context.Context, id string) (*core.Reservation, error)
  ReleaseReservation(ctx context.Context, id, agentID string) error
  ActiveReservations(ctx context.Context, project string) ([]core.Reservation, error)
  AgentReservations(ctx context.Context, agentID string) ([]core.Reservation, error)
  CheckConflicts(ctx context.Context, project, pathPattern string, exclusive bool) ([]core.ConflictDetail, error)
}
```

### HTTP Endpoints

- **POST /api/reservations** — Create new reservation with conflict checking
- **GET /api/reservations?project=P[&agent=A]** — List active reservations
- **GET /api/reservations/check?project=P&pattern=GLOB[&exclusive=true]** — Dry-run conflict check
- **DELETE /api/reservations/{id}** — Release reservation by ID

### Key Handler Signatures

- `createReservation()` (lines 96–148) — Default TTL: 30 minutes, returns 409 Conflict if overlaps
- `releaseReservation()` (lines 211–235) — Verifies agent ownership, atomic update
- `checkConflicts()` (lines 184–209) — Dry-run only, no side effects

---

## 6. SQLite Storage — Reservation Methods

**File:** `/home/mk/projects/Demarch/core/intermute/internal/storage/sqlite/sqlite.go`

### Reserve() (lines 1328–1432)

```go
func (s *Store) Reserve(_ context.Context, r core.Reservation) (*core.Reservation, error)
```

**Flow:**
1. Generate UUID if missing, set CreatedAt, defaults TTL to 30min
2. Validate pattern complexity (max 50 tokens, 10 wildcards)
3. Validate pattern syntax via `glob.PatternsOverlap()` with itself
4. Begin transaction
5. Query active reservations excluding self (WHERE project=P, released_at IS NULL, expires_at>now)
6. For each active: skip if both shared, check `glob.PatternsOverlap(newPattern, existing)`
7. If conflicts: return ConflictError with details
8. INSERT new reservation, COMMIT
9. Return hydrated reservation

**Key:** Shared-shared overlaps allowed; any exclusive lock blocks overlap

### ReleaseReservation() (lines 1468–1482)

```go
func (s *Store) ReleaseReservation(_ context.Context, id, agentID string) error
```

- **UPDATE file_reservations SET released_at = NOW() WHERE id=? AND agent_id=? AND released_at IS NULL**
- Atomic two-part check: owner verification + idempotence guard
- Returns ErrNotFound if no rows affected

### ActiveReservations() (lines 1485–1500)

- Query: WHERE project=P, released_at IS NULL, expires_at>now
- Ordered by created_at DESC

### AgentReservations() (lines 1502–1517)

- Query: WHERE agent_id=A (no expiration filter)
- Returns all agent's reservations including expired

### CheckConflicts() (lines 1586–1631)

- Dry-run conflict detection
- Queries all active reservations, checks overlap
- Joins agents table for agent name in ConflictDetail

### SweepExpired() (lines 1639–1657)

```go
func (s *Store) SweepExpired(_ context.Context, expiredBefore, heartbeatAfter time.Time) ([]core.Reservation, error)
```

- DELETE expired reservations from inactive agents
- Preserves reservations from agents with recent heartbeats (grace period: 5min default)

---

## 7. HTTP Router

**File:** `/home/mk/projects/Demarch/core/intermute/internal/http/router.go`

```go
func NewRouter(svc *Service, wsHandler http.Handler, mw func(http.Handler) http.Handler) http.Handler
```

**Routes:**
- Line 22: `POST /api/reservations` + `GET /api/reservations`
- Line 23: `GET /api/reservations/check`
- Line 24: `DELETE /api/reservations/{id}`

All routes protected by auth middleware.

---

## 8. Background Sweeper

**File:** `/home/mk/projects/Demarch/core/intermute/internal/storage/sqlite/sweeper.go`

### Sweeper Struct (lines 18–25)

```go
type Sweeper struct {
  store    *Store
  bus      Broadcaster    // WebSocket hub
  interval time.Duration  // 60s default
  grace    time.Duration  // 5min heartbeat grace
  cancel   context.CancelFunc
  done     chan struct{}
}
```

### Start() → runSweep() (lines 38–96)

1. Startup sweep with 5min backstop
2. Periodic sweeps every 60s
3. For each sweep: calls SweepExpired, broadcasts EventReservationExpired to WebSocket hub

---

## 9. Glob Pattern Overlap Logic

**File:** `/home/mk/projects/Demarch/core/intermute/internal/glob/overlap.go`

### ValidateComplexity() (lines 42–66)

- Enforces limits: MaxTokens = 50, MaxWildcards = 10
- Parses segments and counts tokens

### PatternsOverlap() (lines 68–90)

```go
func PatternsOverlap(a, b string) (bool, error)
```

- Normalizes to forward slashes, splits on `/`
- **Patterns must have same depth** or returns false
- For each segment pair calls `segmentPatternsOverlap()`

### segmentPatternsOverlap() (lines 92–149)

**NFA-based state exploration:**

1. Parse both segments into tokens (literal, any, star, class)
2. State machine: `state{i, j}` = positions in A and B
3. Epsilon closure on tokenStar
4. BFS: check if token ranges overlap at each state
5. Accept if reach `(len(A), len(B))` state

**Examples:**
- `pkg/api/*.go` overlaps `pkg/api/users.go` ✓
- `pkg/api/*.go` does NOT overlap `pkg/service/*.go` ✗

### Token Types

- tokenLiteral: single rune
- tokenAny: `?` — one non-separator rune
- tokenStar: `*` — zero or more non-separators
- tokenClass: `[abc]` or `[^abc]` — character set

---

## 10. Conflict Resolution Rules

### Overlap Decision Tree (Reserve() lines 1388–1390)

```go
if !r.Exclusive && existingExcl == 0 {
  continue  // shared-shared always allowed
}
overlap, err := glob.PatternsOverlap(r.PathPattern, existingPattern)
```

| New | Existing | Pattern Match | Allowed? |
|-----|----------|---------------|----------|
| Shared | Shared | Yes | ✓ |
| Shared | Exclusive | Yes | ✗ Conflict |
| Exclusive | Shared | Yes | ✗ Conflict |
| Exclusive | Exclusive | Yes | ✗ Conflict |

---

## 11. Time-to-Live & Expiration

- **Default TTL:** 30 minutes
- **ExpiresAt:** Set at creation: `now + TTL`
- **Active Check:** `released_at IS NULL AND expires_at > NOW()`
- **Sweep Grace:** 5 minutes (inactive agents have their reservations auto-deleted)

---

## 12. Multi-Tenancy & Authorization

- **Project Scoping:** All queries include `WHERE project = ?`
- **Agent Ownership:** Release requires agent_id match
- **HTTP Auth:** API keys tied to project (403 Forbidden if mismatch)

---

## 13. Error Handling

### Core Errors

- **ErrNotFound:** Entity not found
- **ConflictError:** Pattern overlaps with active reservations

### HTTP Status Mapping

- 201 Created — Success
- 200 OK — Released successfully
- 400 Bad Request — Validation error
- 403 Forbidden — Wrong agent
- 404 Not Found — Not found
- 409 Conflict — Pattern overlap detected
- 500 Internal Server Error — DB error

---

## 14. Indexes

```sql
idx_reservations_project ON file_reservations(project)
idx_reservations_agent ON file_reservations(agent_id)
idx_reservations_active ON file_reservations(project, expires_at) WHERE released_at IS NULL
```

- Active query uses composite partial index
- Agent lookups use single-column index

---

## 15. WebSocket Broadcasting

- **Hub:** Centralized gateway (internal/ws/gateway.go)
- **Event Type:** "reservation.expired"
- **Payload:** Project, reservation ID, agent ID, path pattern
- **Subscribers:** All clients on `/ws/agents/` receive events

---

## Summary

Intermute's file reservation system is a **multi-tenant, transactional lock service** with:

1. **Optimistic conflict detection** via glob pattern overlap analysis
2. **Exclusive and shared lock modes** (UNIX RWLock semantics)
3. **TTL-based auto-expiration** with 5-minute grace period
4. **Real-time WebSocket notifications**
5. **Atomic transactions** for all state mutations
6. **RFC3339Nano timestamps** for reliability
7. **Project-scoped multi-tenancy** with agent ownership verification

**Critical Path:** glob.PatternsOverlap() must validate same path depth and mutual rune range compatibility across all segments.
