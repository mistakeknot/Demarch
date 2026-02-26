# Interdoc Analysis: Intermute AGENTS.md Refresh

**Date:** 2026-02-25
**Source:** `/home/mk/projects/Demarch/core/intermute/AGENTS.md` (299 lines)
**Target:** Same file, refreshed

## Scope of Analysis

Read and cross-referenced the following source files against the existing AGENTS.md:
- `go.mod` -- module path, Go version, dependencies
- `cmd/intermute/main.go` -- CLI commands, flags, server wiring
- `internal/http/router.go` and `router_domain.go` -- all route registrations
- `internal/http/handlers_agents.go` -- agent CRUD + metadata + contact policy endpoints
- `internal/http/handlers_messages.go` -- messaging, inbox counts, stale acks, topics, broadcast
- `internal/http/handlers_threads.go` -- thread listing and thread messages
- `internal/http/handlers_reservations.go` -- file reservation CRUD + conflict check
- `internal/http/handlers_domain.go` -- domain entity CRUD (DomainService)
- `internal/http/handlers_health.go` -- /health endpoint
- `internal/http/service.go` -- Service struct, broadcast rate limiter
- `internal/core/models.go` -- Message, Agent, Event, Reservation, RecipientStatus, StaleAck, ConflictDetail types
- `internal/core/domain.go` -- Domain entity types (Spec, Epic, Story, Task, Insight, Session, CUJ), ContactPolicy, sentinel errors
- `internal/storage/storage.go` -- Store interface (59 methods)
- `internal/storage/domain.go` -- DomainStore interface extending Store
- `internal/storage/sqlite/schema.sql` -- all 16 tables
- `internal/storage/sqlite/sqlite.go` -- Store implementation, query logger
- `internal/storage/sqlite/resilient.go` -- ResilientStore wrapper
- `internal/storage/sqlite/circuitbreaker.go` -- circuit breaker
- `internal/storage/sqlite/sweeper.go` -- expired reservation sweeper
- `internal/storage/sqlite/coordination_bridge.go` -- Intercore dual-write bridge
- `internal/storage/sqlite/querylog.go` -- slow query logger
- `internal/glob/overlap.go` -- NFA glob overlap detection
- `internal/server/server.go` -- HTTP + Unix socket dual-listen server
- `pkg/embedded/server.go` -- embeddable server (New, NewWithAuth)
- `client/client.go` -- Go SDK client
- `client/domain.go` -- domain entity client methods
- `client/websocket.go` -- WebSocket subscription client

## Findings: Gaps in Current AGENTS.md

### 1. Missing API Endpoints (NOT documented)

**Agent endpoints -- new since last review:**
- `PATCH /api/agents/{id}/metadata` -- merge metadata keys (PATCH semantics)
- `GET /api/agents/{id}/policy` -- get contact policy
- `POST /api/agents/{id}/policy` -- set contact policy
- `GET /api/agents?capability=...` -- filter by capability (comma-separated)

**Messaging endpoints -- new since last review:**
- `POST /api/broadcast` -- broadcast to all project agents (rate-limited: 10/min/sender)
- `GET /api/inbox/{agent}/counts` -- inbox total/unread counts
- `GET /api/inbox/{agent}/stale-acks` -- ack-required messages past TTL
- `GET /api/topics/{project}/{topic}` -- topic-based cross-cutting message discovery

**Infrastructure endpoints -- undocumented:**
- `GET /health` -- health check (unauthenticated, only on DomainRouter)

**Domain endpoints -- CUJ not documented:**
- `GET/POST /api/cujs` -- list/create CUJs
- `GET/PUT/DELETE /api/cujs/{id}` -- CUJ CRUD

**Reservation endpoints -- incomplete:**
- `GET /api/reservations/check?project=...&pattern=...&exclusive=...` -- conflict check (was missing from the documented endpoint list)

### 2. Missing Data Model Fields

**Message now has:**
- `CC`, `BCC` (carbon copy, blind carbon copy)
- `Subject` (message subject line)
- `Topic` (cross-cutting discovery, lowercased at write time)
- `Metadata` (map[string]string)
- `Attachments` ([]Attachment with Name, Path)
- `Importance` (string)
- `AckRequired` (bool)
- `Status` (string)

**Agent now has:**
- `ContactPolicy` (open, auto, contacts_only, block_all)

**New types not documented:**
- `RecipientStatus` -- per-recipient read/ack tracking
- `StaleAck` -- unacked messages past TTL
- `Reservation` -- file lock with TTL, exclusive/shared
- `ConflictDetail` / `ConflictError` -- reservation conflict reporting
- `CriticalUserJourney` (CUJ) -- full entity with steps, persona, priority
- `CUJStep` -- step in a CUJ
- `CUJFeatureLink` -- many-to-many CUJ-feature association
- `DomainEvent` -- event sourcing wrapper for domain changes
- `ContactPolicy` -- enum (open, auto, contacts_only, block_all)

### 3. Missing Infrastructure

**Coordination Bridge:**
- `internal/storage/sqlite/coordination_bridge.go` -- dual-write to Intercore's `coordination_locks` table
- Enabled via `--coordination-dual-write` flag on `serve` command
- Auto-discovers Intercore DB or uses `--intercore-db` path

**Resilience layer:**
- `ResilientStore` wraps every Store method with circuit breaker + retry
- `CircuitBreaker` (threshold=5, resetTimeout=30s)
- `RetryOnDBLock` for transient SQLite errors
- `queryLogger` logs slow queries (>100ms threshold)

**Sweeper:**
- Background goroutine cleaning expired reservations from inactive agents
- 60s interval, 5min heartbeat grace period
- Emits `reservation.expired` events via broadcaster

**Server:**
- Dual-listen: HTTP + optional Unix domain socket (`--socket` flag)
- Config: `server.Config{Addr, SocketPath, Handler}`

**Glob overlap detection:**
- `internal/glob/` -- NFA-based glob pattern overlap detection
- Used for file reservation conflict checking
- DoS guard: max 50 tokens, max 10 wildcards per pattern

### 4. Missing CLI Flags

`intermute serve` now supports:
- `--host` (default: 127.0.0.1)
- `--port` (default: 7338)
- `--db` (default: intermute.db)
- `--socket` (Unix domain socket path) -- NEW
- `--coordination-dual-write` (mirror to Intercore) -- NEW
- `--intercore-db` (path to intercore.db) -- NEW

### 5. Stale Content

**Router Gap section (lines 262-266):**
- States `NewRouter` includes `/api/reservations` but `NewDomainRouter` does NOT include reservations. This is STALE. Looking at `router_domain.go`, `NewDomainRouter` DOES include `/api/reservations`, `/api/reservations/check`, and `/api/reservations/` routes. Both routers now have reservations.

**Test count:**
- AGENTS.md says "111 test functions" -- actual count is 158 test functions.
- Coverage percentages likely outdated.

**Downstream Dependencies:**
- Path `/root/projects/Autarch` is stale. The monorepo path is `/home/mk/projects/Demarch/apps/autarch`.

**Multi-Session Coordination:**
- References `scripts/worktree-setup.sh` and `scripts/worktree-teardown.sh` -- these exist, but section feels procedural and belongs more in CLAUDE.md (which already covers it).

**Auracoil section:**
- Review metadata from 2026-02-07 / commit 2e9e98e. Significant features have been added since.
- The corrections listed are all now incorporated. Section is stale as a whole.

**Directory Structure:**
- Missing `internal/glob/` package
- Missing `internal/server/` entry (only mentioned as reference)
- `internal/storage/` description says "Store interface with InMemory implementation" but the InMemory is in storage.go, SQLite in sqlite/. More importantly, missing: `resilient.go`, `circuitbreaker.go`, `sweeper.go`, `coordination_bridge.go`, `querylog.go`, `retry.go`

**Database Design:**
- Missing tables: `message_recipients`, `file_reservations`, `agent_contacts`, `cujs`, `cuj_feature_links`
- Events table description is accurate but incomplete (missing newer event types)

### 6. Contact Policy System (entirely undocumented)

Four policy levels:
- `open` -- accept from anyone (default)
- `auto` -- auto-allow agents with overlapping file reservations
- `contacts_only` -- explicit whitelist only
- `block_all` -- reject everything

Policy enforcement on message send:
- All recipients (to, cc, bcc) filtered by policy
- Thread participant exception (not for block_all)
- Reservation overlap exception (for auto policy)
- If ALL recipients denied, returns 403 with `policy_denied` error
- Partial delivery: allowed recipients get the message, denied list returned

Agent contacts:
- `AddContact`, `RemoveContact`, `ListContacts`, `IsContact` in Store interface
- `agent_contacts` table with composite PK

### 7. Session Management

- `SessionStaleThreshold = 5 minutes` -- after this, session_id can be reused
- `ErrActiveSessionConflict` -- returned when session_id is in use by active agent
- Registration with duplicate session_id updates existing agent if stale

### 8. Optimistic Locking

- Domain entities use `version` field for optimistic locking
- `ErrConcurrentModification` sentinel error

## Summary of Changes for Rewrite

1. **Add L1 layer context** in overview
2. **Update directory structure** with glob/, server/, new sqlite files
3. **Complete API endpoint list** (broadcast, topics, inbox counts, stale-acks, agent metadata/policy, health, CUJ)
4. **Update data model** with all current fields (CC, BCC, Subject, Topic, Importance, AckRequired, ContactPolicy)
5. **Add CUJ entity** to domain types
6. **Document contact policy system**
7. **Document resilience layer** (circuit breaker, retry, ResilientStore)
8. **Document coordination bridge** (dual-write to Intercore)
9. **Document sweeper** (expired reservation cleanup)
10. **Fix stale router gap** (both routers now include reservations)
11. **Update test count** (158 functions)
12. **Fix downstream dependency path** (`/home/mk/projects/Demarch/apps/autarch`)
13. **Add new CLI flags** (--socket, --coordination-dual-write, --intercore-db)
14. **Remove stale Auracoil section** (outdated review metadata)
15. **Update database table list** (16 tables total)
16. **Add key files** for new components
