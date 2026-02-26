# Brainstorm: Native Automated Coordination in Kernel

**Bead:** iv-otd4l
**Phase:** brainstorm (as of 2026-02-25T21:35:56Z)
**Date:** 2026-02-25
**Status:** Brainstorm complete

## What We're Building

A unified coordination subsystem in Intercore (`ic coordination`) that consolidates file reservations, named locks, and dispatch write-sets into a single `coordination_locks` table in the kernel SQLite database. This replaces the current fragmented architecture where:

- **Intercore** has filesystem-only `mkdir` locks (no DB, no TTL, PID-liveness stale detection)
- **Intermute** has HTTP-based file reservations (own SQLite, `BeginTx` without `BEGIN IMMEDIATE`)
- **Dispatch write-sets** are tracked in a separate `dispatch_intents` table

After this work, Intercore becomes the single coordination authority. Intermute delegates reservation storage to the shared DB. Interlock becomes a thin MCP bridge calling `ic` instead of Intermute HTTP.

## Why This Approach

### Problem

Multi-agent coordination in Demarch has 3 known TOCTOU bugs and 8 documented architectural seams:

1. **Reserve() transaction isolation** — Intermute's `Reserve()` uses default `BeginTx` (not `BEGIN IMMEDIATE`). Under concurrent HTTP requests without `MaxOpenConns(1)`, two agents can both pass the conflict check and both insert.
2. **Advisory dispatch limits** — `global_max_dispatches` checked without a lock; concurrent spawns exceed limits.
3. **Incomplete crash recovery** — Stop hook only fires on graceful stops. Crash = 15-min stale reservations + orphaned agent registrations.
4. **No reservation transfer** on session handoff (context exhaustion).
5. **Non-Clavain agents have no coordination** — raw Codex dispatches bypass all Interlock enforcement.
6. **Filesystem locks are fragile** — PID-based stale detection fails across reboots, no TTL, no audit trail.

### Why unified in Intercore (not fix-in-place)

- **Single writer via `MaxOpenConns(1)`** — Intercore already enforces this. Eliminates the TOCTOU root cause.
- **Same DB as dispatches/runs** — coordination checks can join against dispatch state (who owns this file? what run is it part of?).
- **CLI-accessible** — any agent can `ic coordination reserve` regardless of whether it has MCP tools or HTTP access.
- **Event bus integration** — coordination events flow through the existing `ic events` system for monitoring and replay.
- **Crash recovery via sweeper** — Intercore already has sentinel TTL cleanup; extend to coordination locks.

### Why NOT a new daemon or gRPC

- Same-machine guarantee (all Demarch agents run on one host) means shared SQLite is lowest-latency.
- No new process to manage, no new protocol to maintain.
- SQLite WAL mode handles concurrent readers + single writer efficiently.

## Key Decisions

### D1: Single `coordination_locks` table

One table with a `type` discriminator column handles all three coordination primitives:

```sql
CREATE TABLE coordination_locks (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL,     -- 'file_reservation' | 'named_lock' | 'write_set'
    owner        TEXT NOT NULL,     -- agent_id or PID:host
    scope        TEXT NOT NULL,     -- project dir or run_id
    pattern      TEXT NOT NULL,     -- glob pattern or lock name
    exclusive    BOOLEAN NOT NULL DEFAULT 1,
    reason       TEXT,
    ttl_seconds  INTEGER,
    created_at   INTEGER NOT NULL,
    expires_at   INTEGER,           -- NULL = no expiry (named locks)
    released_at  INTEGER,           -- NULL = active
    dispatch_id  TEXT,              -- NULL for non-dispatch locks
    run_id       TEXT               -- NULL for non-run locks
);

CREATE INDEX idx_coord_active ON coordination_locks(scope, type)
    WHERE released_at IS NULL;
CREATE INDEX idx_coord_owner ON coordination_locks(owner)
    WHERE released_at IS NULL;
CREATE INDEX idx_coord_expires ON coordination_locks(expires_at)
    WHERE released_at IS NULL AND expires_at IS NOT NULL;
```

**Conflict detection:** Single code path using glob overlap logic (`filepath.Match` or equivalent) for all types. `exclusive=true` conflicts with any overlapping active lock. `exclusive=false` (shared) conflicts only with exclusive locks.

**Why single table:** One acquire/release/check/sweep code path. Coordination events are uniform. Dashboard queries don't need UNION across tables.

### D2: Shared SQLite DB (Intermute reads Intercore DB directly)

Intermute opens `intercore.db` for coordination operations instead of maintaining its own `file_reservations` table. Both processes must use `MaxOpenConns(1)` on the shared DB.

**Same-machine guarantee:** Intercore and Intermute always run on the same host. No network hop needed.

**WAL mode:** Already configured by Intercore. Concurrent readers (Intermute serving GET /api/reservations) don't block the single writer.

### D3: Incremental migration with dual-write

Four phases, each independently shippable:

1. **Phase 1: Add `ic coordination` commands** — `reserve`, `release`, `check`, `list`, `sweep`. New table in intercore.db. Filesystem locks (`/tmp/intercore/locks/`) remain for backward compat.
2. **Phase 2: Dual-write** — Intermute writes to both its own `file_reservations` AND the new `coordination_locks` table. Reads still come from Intermute's table. Enables shadow comparison.
3. **Phase 3: Switch readers** — Interlock hooks call `ic coordination check` instead of Intermute HTTP. Intermute's reservation GET endpoints read from `coordination_locks`. Intermute writes stop going to old table.
4. **Phase 4: Cleanup** — Remove Intermute's `file_reservations` table, `Reserve()`/`Release()` methods, and the old filesystem lock directory.

### D4: Interlock becomes thin MCP bridge to `ic`

Interlock's MCP tools (`reserve_files`, `release_files`, `check_conflicts`, etc.) shell out to `ic coordination` instead of calling Intermute HTTP. Hooks (`pre-edit.sh`, `interlock-check.sh`) call `ic` directly.

Benefits: Agents without MCP (raw Codex dispatches) can `ic coordination reserve` from their prompt. Unifies the coordination interface.

### D5: `BEGIN IMMEDIATE` for all coordination writes

All write transactions in the coordination subsystem use `BEGIN IMMEDIATE` to acquire the write lock immediately, preventing the TOCTOU window where two transactions both read "no conflict" then both write.

Combined with `MaxOpenConns(1)`, this provides true serializability.

### D6: Event bus integration

Coordination state changes emit events:

- `coordination.acquired` — lock/reservation created
- `coordination.released` — explicit release
- `coordination.expired` — TTL-based sweep
- `coordination.conflict` — acquire attempt blocked by existing lock
- `coordination.transferred` — reservation transferred between sessions

Events enable: Bigend monitoring, Interspect evidence collection, audit trails, portfolio-level coordination visibility.

### D7: Crash recovery via sweeper

Background sweep (extending existing sentinel cleanup) checks:
- Expired TTLs → mark `released_at`, emit `coordination.expired`
- Owner liveness (for `named_lock` type) → `syscall.Kill(pid, 0)` check
- Agent heartbeat staleness → if agent hasn't heartbeated in 2× TTL, release its locks

This fixes the crash recovery gap where Stop hooks don't fire.

### D8: Reservation transfer for session handoff

New command: `ic coordination transfer --from=<agent> --to=<agent> --scope=<project>`

Atomically reassigns all active reservations from one agent to another. Used during session handoff (context exhaustion) to maintain file ownership continuity.

## Open Questions

1. **Glob overlap algorithm:** Should we use Intermute's existing `glob.PatternsOverlap()` (Go, tested) or reimplement in Intercore? Importing Intermute as a Go dependency would create L1↔L1 coupling. Probably copy the algorithm.
2. **Negotiation protocol:** Intermute has the release negotiation protocol (request→ack/defer→force). Does this move to Intercore too, or stay in Intermute as a messaging concern?
3. **Dispatch write-set migration:** The existing `dispatch_intents` table tracks git-level write-sets. Should these become `type=write_set` coordination_locks, or remain separate since they have different semantics (post-hoc conflict detection vs pre-hoc reservation)?
4. **MaxOpenConns(1) enforcement across processes:** How to guarantee both Intercore CLI and Intermute service honor the single-writer constraint? SQLite's `PRAGMA busy_timeout` provides implicit serialization, but a misconfigured process could still corrupt WAL.
5. **Filesystem lock removal timeline:** The `/tmp/intercore/locks/` directory is used by `sprint_claim()` in lib-sprint.sh. When can we remove it? After Phase 1 proves coordination_locks works for named locks?

## Non-Goals

- Distributed/multi-machine coordination (same-machine guarantee holds)
- Replacing Intermute's messaging system (only reservations move)
- Building the full GKST architecture (SnapshotRef, read-set capture, merge queue) — that's a separate epic
- Contact policies (iv-t4pia) — orthogonal to reservation storage
