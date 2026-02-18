# PRD: intercore — Unified State Database

**Bead:** iv-ieh7

## Problem

The Clavain hook infrastructure communicates through ~15 scattered temp files in `/tmp/`, each with its own naming convention, TTL logic, and cleanup strategy. This causes TOCTOU race conditions in throttle guards, makes cross-session state invisible, and requires every new hook to invent its own state management pattern.

## Solution

A Go CLI (`ic`) backed by a single SQLite WAL database (`intercore.db`) that provides atomic state operations and throttle guards callable from bash hooks. Lives at `plugins/intercore/` as a Claude Code plugin.

## Features

### F1: Go CLI Scaffold and Schema

**What:** Create the `plugins/intercore/` project with Go module, SQLite schema, auto-migration, and the `ic` CLI entry point.

**Acceptance criteria:**
- [ ] `go build ./cmd/ic` produces a working binary
- [ ] Running `ic init` creates `intercore.db` with all tables (state, sentinels, runs, agents, artifacts, phase_gates) and schema version tracking
- [ ] Schema migrations run automatically on first use and on version bumps
- [ ] WAL mode enabled by default with a configurable `busy_timeout` (default 5s)
- [ ] `ic version` prints version and schema version

### F2: State Operations

**What:** CRUD operations for structured state (key/scope/payload), replacing JSON temp files and interband sideband entries.

**Acceptance criteria:**
- [ ] `ic state set <key> <scope_id> '<json>'` upserts a state row (scope_type inferred or specified with `--scope`)
- [ ] `ic state set` supports `--ttl=<duration>` to set `expires_at`
- [ ] `ic state get <key> <scope_id>` returns the payload JSON (exit 0) or empty (exit 1)
- [ ] `ic state list <key>` lists all scope_ids for a given key
- [ ] `ic state prune` deletes expired rows, returns count deleted
- [ ] Write rate limiting: `ic state set` with `--debounce` skips write if payload unchanged and last write was < 250ms ago
- [ ] Output is plain text by default, `--json` flag for structured output

### F3: Sentinel Operations

**What:** Atomic claim-if-eligible throttle checks, replacing touch-file + `find -mmin` guards.

**Acceptance criteria:**
- [ ] `ic sentinel check <name> <scope_id> --interval=<seconds>` returns "allowed" (exit 0) or "throttled" (exit 1) in a single atomic transaction
- [ ] When `--interval=0`, sentinel fires exactly once per scope_id (once-per-session guard)
- [ ] Concurrent calls from different sessions correctly serialize — only one wins
- [ ] `ic sentinel reset <name> <scope_id>` clears a sentinel (for testing/recovery)
- [ ] `ic sentinel list` shows all active sentinels with last_fired timestamps
- [ ] `ic sentinel prune --older-than=<duration>` cleans up stale sentinels

### F4: Run Tracking

**What:** Tables and CLI commands for tracking orchestration runs, agents, artifacts, and phase gates — enabling queries like "what phase is this run in?" and "which agents are active?"

**Acceptance criteria:**
- [ ] `ic run create --project=<path> --goal=<text> [--bead=<id>] [--session=<id>]` creates a run, returns its ID
- [ ] `ic run phase <run_id> <phase>` updates the phase, records in phase_gates
- [ ] `ic run status <run_id>` shows run details including agents and artifacts
- [ ] `ic agent add <run_id> --type=<type> [--name=<n>] [--pid=<p>]` registers an agent
- [ ] `ic agent update <agent_id> --status=<s>` updates agent status
- [ ] `ic artifact add <run_id> --phase=<p> --path=<path> --type=<t>` registers an artifact
- [ ] `ic run list [--status=<s>] [--project=<p>]` lists runs with filtering
- [ ] `ic run current` returns the active run for the current session/project (most recent active run)

### F5: Bash Integration Library

**What:** A thin `lib-intercore.sh` bash library that wraps `ic` commands for use in existing hooks, providing drop-in replacements for current temp file operations.

**Acceptance criteria:**
- [ ] `intercore_state_set <key> <scope_id> <json>` wraps `ic state set` with error handling (returns 0 on failure, never blocks)
- [ ] `intercore_state_get <key> <scope_id>` wraps `ic state get`, returns payload or empty string
- [ ] `intercore_sentinel_check <name> <scope_id> <interval>` wraps `ic sentinel check`, returns 0 (allowed) or 1 (throttled)
- [ ] `intercore_available()` returns 0 if `ic` binary is on PATH, 1 otherwise
- [ ] All functions follow the "fail-safe by convention" pattern — errors return 0, never block workflow
- [ ] Library auto-discovers `ic` binary location (PATH or `~/.claude/plugins/cache/*/intercore/*/bin/ic`)

### F6: Mutex Consolidation

**What:** Reorganize existing `mkdir`-based mutex locks under a unified `/tmp/intercore/locks/` namespace with owner metadata.

**Acceptance criteria:**
- [ ] All mutex locks created under `/tmp/intercore/locks/<category>/<id>/`
- [ ] Lock directories contain an `owner` file with PID, session_id, and created_at
- [ ] `ic lock list` shows all active locks with owner info
- [ ] `ic lock stale [--max-age=<duration>]` lists locks older than threshold whose PID is dead
- [ ] `ic lock clean [--max-age=<duration>]` removes stale locks (dead PID + age exceeded)
- [ ] Bash helper `intercore_lock <category> <id>` and `intercore_unlock <category> <id>` in lib-intercore.sh

### F7: Backward Compatibility and Migration

**What:** Dual-write mode that writes to both intercore DB and legacy temp files, allowing consumers (interline, interband) to migrate at their own pace.

**Acceptance criteria:**
- [ ] `ic` supports `--legacy-compat` flag (or `INTERCORE_LEGACY_COMPAT=1` env var) that triggers dual-write
- [ ] In dual-write mode, `ic state set dispatch` also writes `/tmp/clavain-dispatch-$$.json`
- [ ] In dual-write mode, `ic state set bead_phase` also writes `/tmp/clavain-bead-${SID}.json` and `~/.interband/interphase/bead/${SID}.json`
- [ ] In dual-write mode, `ic sentinel check stop` also touches `/tmp/clavain-stop-${SID}`
- [ ] Legacy compat can be toggled per-key via config, not just globally
- [ ] Migration script that reads existing temp files/interband entries and imports them into intercore

## Non-goals

- **Replacing beads (bd)** — beads remains the authoritative issue tracker and permanent phase store. intercore handles ephemeral/session state.
- **Replacing interband entirely** — interband may evolve into a view layer that reads from intercore, but that's a separate decision.
- **DB-backed mutexes** — filesystem `mkdir` locks stay. intercore only consolidates their namespace and adds introspection.
- **Telemetry migration** — `~/.clavain/telemetry.jsonl` stays as append-only flat file.
- **MCP server** — intercore is a CLI first. MCP exposure (if ever needed) is a future feature.
- **Multi-machine distribution** — intercore is local-only, single-machine. No replication, no remote access.

## Dependencies

- Go 1.21+ (already available on server)
- SQLite driver: `modernc.org/sqlite` (pure Go, no CGO) or `github.com/mattn/go-sqlite3` (CGO, faster)
- Existing hook infrastructure (`lib.sh`, `lib-gates.sh`, `lib-sprint.sh`) for integration points
- `bd` CLI patterns for CLI design reference

## Open Questions

1. **DB file location** — `.clavain/intercore.db` (project-relative) or `~/.intercore/intercore.db` (global)? Project-relative matches beads but means one DB per project. Global means cross-project queries are possible but session isolation is harder.
2. **interband relationship** — Does intercore subsume interband, or does interband become a read-through cache/view?
3. **autopub.lock** — Mutex or throttle? Need to check implementation to classify correctly.
4. **CGO vs pure Go SQLite** — `mattn/go-sqlite3` is faster but requires CGO. `modernc.org/sqlite` is pure Go, easier to cross-compile. Performance difference likely negligible for this workload.
