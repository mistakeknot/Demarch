# PRD: Native Automated Coordination in Kernel

**Bead:** iv-otd4l

## Problem

Multi-agent coordination in Demarch is fragmented across three layers (Intercore filesystem locks, Intermute HTTP reservations, Interlock MCP tools) with 3 known TOCTOU bugs, incomplete crash recovery, and no coordination path for non-Clavain agents. The primary correctness risk — Intermute's `Reserve()` using default transaction isolation without `MaxOpenConns(1)` — means two agents can simultaneously pass the conflict check and both acquire the same file.

## Solution

A unified `coordination_locks` table in Intercore's SQLite database, accessed via `ic coordination` CLI commands. All coordination primitives (file reservations, named locks, dispatch write-sets) share one schema, one conflict detection path, and one sweep/cleanup lifecycle. Intermute delegates reservation storage to this table via shared DB access. Interlock becomes a thin MCP bridge to `ic`. Migration is incremental with dual-write.

## Features

### F1: `coordination_locks` Table and `ic coordination` CLI

**What:** New SQLite table and CLI subcommands that provide the core acquire/release/check/list/sweep operations with `BEGIN IMMEDIATE` transaction isolation.

**Acceptance criteria:**
- [ ] `coordination_locks` table created via Intercore migration (schema per brainstorm D1)
- [ ] `ic coordination reserve --owner=<agent> --scope=<project> --pattern=<glob> [--exclusive] [--ttl=<seconds>] [--reason=<text>] [--type=file_reservation|named_lock|write_set] [--dispatch=<id>] [--run=<id>]` acquires a lock
- [ ] `ic coordination release <id>` marks `released_at` on a specific lock
- [ ] `ic coordination release --owner=<agent> --scope=<project>` releases all locks for an agent in a scope
- [ ] `ic coordination check --scope=<project> --pattern=<glob> [--exclude-owner=<agent>]` returns conflicting active locks (exit 0 = clear, exit 1 = conflict)
- [ ] `ic coordination list [--scope=<project>] [--owner=<agent>] [--type=<type>] [--active]` lists locks with JSON output
- [ ] `ic coordination sweep [--older-than=<duration>]` releases expired locks and stale owner locks
- [ ] All write transactions use `BEGIN IMMEDIATE`
- [ ] Glob overlap conflict detection uses `filepath.Match`-compatible algorithm (copied from Intermute's `glob.PatternsOverlap`)
- [ ] `--json` flag works on all commands (positional, before subcommand)
- [ ] Existing `ic lock` commands continue to work (filesystem locks unchanged)

### F2: Event Bus Integration

**What:** Coordination state changes emit events through Intercore's existing event bus for monitoring, audit, and downstream consumption.

**Acceptance criteria:**
- [ ] `coordination.acquired` event emitted on successful reserve (includes lock ID, owner, pattern, type)
- [ ] `coordination.released` event emitted on explicit release
- [ ] `coordination.expired` event emitted when sweep releases an expired lock
- [ ] `coordination.conflict` event emitted when reserve is blocked by existing lock (includes blocker info)
- [ ] `coordination.transferred` event emitted on reservation transfer
- [ ] Events include `scope` field for project-scoped filtering
- [ ] Events visible via `ic events tail <run_id>` and `ic events tail --all`
- [ ] Events use the existing `run_events` table (scoped to run_id when available, global otherwise)

### F3: Crash Recovery Sweeper

**What:** Extend Intercore's background sweep to automatically clean up coordination locks from crashed agents.

**Acceptance criteria:**
- [ ] `ic coordination sweep` checks TTL expiry (`expires_at < now AND released_at IS NULL`)
- [ ] For `named_lock` type: checks owner PID liveness via `syscall.Kill(pid, 0)` — `ESRCH` = stale
- [ ] For `file_reservation` type: checks agent heartbeat staleness (last_seen older than 2× TTL)
- [ ] Sweep runs as part of `ic coordination reserve` (inline, same as sentinel auto-prune pattern)
- [ ] Sweep emits `coordination.expired` events for each cleaned lock
- [ ] `ic coordination sweep --dry-run` shows what would be cleaned without acting
- [ ] Agent heartbeat staleness requires reading Intermute's agent registry (shared DB or HTTP fallback)

### F4: Reservation Transfer

**What:** Atomic command to reassign all active reservations from one agent to another during session handoff.

**Acceptance criteria:**
- [ ] `ic coordination transfer --from=<agent> --to=<agent> --scope=<project>` atomically updates `owner` on all active locks
- [ ] Transfer is a single transaction (all-or-nothing)
- [ ] `coordination.transferred` event emitted per transferred lock
- [ ] Transfer fails if `--to` agent already has conflicting exclusive locks in the same scope
- [ ] `--force` flag skips the conflict check (for emergency handoffs)
- [ ] Transfer works for all lock types (file_reservation, named_lock, write_set)

### F5: Intermute Dual-Write Bridge

**What:** Intermute writes reservation operations to both its own `file_reservations` table AND the new `coordination_locks` table, enabling shadow comparison before cutover.

**Acceptance criteria:**
- [ ] Intermute opens `intercore.db` (discovered via walk-up from project dir, same as `ic`)
- [ ] `Reserve()` writes to both `file_reservations` (existing) and `coordination_locks` (new) in separate transactions
- [ ] `Release()` marks released in both tables
- [ ] `CheckConflict()` reads from `file_reservations` (existing, authoritative during dual-write)
- [ ] `MaxOpenConns(1)` enforced on the Intercore DB connection
- [ ] Mismatch detection: periodic comparison of active locks between both tables, logged as warning
- [ ] Dual-write is controlled by a config flag (`coordination_dual_write: true`) so it can be toggled
- [ ] Intermute's reservation HTTP endpoints continue to work unchanged during dual-write

### F6: Interlock MCP Bridge to `ic`

**What:** Interlock's MCP tools and hooks call `ic coordination` instead of Intermute HTTP for reservation operations.

**Acceptance criteria:**
- [ ] `reserve_files` MCP tool calls `ic coordination reserve` instead of `POST /api/reservations`
- [ ] `release_files` MCP tool calls `ic coordination release` instead of `DELETE /api/reservations/{id}`
- [ ] `check_conflicts` MCP tool calls `ic coordination check` instead of `POST /api/reservations/check`
- [ ] `my_reservations` MCP tool calls `ic coordination list --owner=<agent>` instead of `GET /api/reservations`
- [ ] `pre-edit.sh` hook calls `ic coordination check` and `ic coordination reserve` instead of `interlock-check.sh`
- [ ] `interlock-precommit-hook` calls `ic coordination check` instead of querying Intermute HTTP
- [ ] Negotiation tools (`negotiate_release`, `respond_to_release`) remain on Intermute (messaging concern)
- [ ] Join-flag gating still works (`intermute-joined` check before `ic` calls)
- [ ] Graceful fallback: if `ic` is not found, fall back to Intermute HTTP (fail-open)

### F7: Cleanup — Remove Legacy Reservation Storage

**What:** Remove Intermute's `file_reservations` table, the dual-write bridge, and the filesystem lock directory.

**Acceptance criteria:**
- [ ] Intermute migration removes `file_reservations` table
- [ ] `Reserve()`, `Release()`, `CheckConflict()` methods removed from Intermute's SQLite store
- [ ] Intermute's reservation HTTP endpoints proxy to `coordination_locks` table (read-only)
- [ ] Dual-write config flag and code removed
- [ ] `/tmp/intercore/locks/` directory no longer created by `ic lock`
- [ ] `ic lock acquire/release` reimplemented on top of `coordination_locks` (type=named_lock)
- [ ] `sprint_claim()` in `lib-sprint.sh` uses `ic coordination reserve` instead of `intercore_lock`
- [ ] All existing tests pass with the new storage backend
- [ ] Backward compatibility: `ic lock` commands still work (thin wrapper over `ic coordination`)

## Non-Goals

- Distributed/multi-machine coordination (same-machine guarantee holds)
- Replacing Intermute's messaging system (only reservations move)
- Building the full GKST architecture (SnapshotRef, read-set capture, merge queue)
- Contact policies (iv-t4pia) — orthogonal to reservation storage
- Migrating the release negotiation protocol (stays in Intermute as messaging)

## Dependencies

- Intercore's existing SQLite migration system (`PRAGMA user_version`)
- Intercore's event bus (`run_events` table, `ic events` CLI)
- Intermute's `glob.PatternsOverlap()` algorithm (will be copied, not imported)
- Intermute's agent registry (for heartbeat staleness checks in F3)

## Open Questions

1. **Glob overlap algorithm:** Copy from Intermute or extract to shared `pkg/glob` package? Copying is simpler but creates drift risk.
2. **Dispatch write-set migration timing:** Should existing `dispatch_intents` rows be migrated to `coordination_locks` as part of F1, or is that a separate cleanup after F7?
3. **MaxOpenConns(1) enforcement:** Should we add a startup check that detects if another process has the DB open with a different connection limit?
4. **Filesystem lock removal (F7):** Can we remove `/tmp/intercore/locks/` immediately after F1 proves coordination_locks works for named locks, or must we wait for the full F7 cleanup?
