# Research: Dolt Lock Management Best Practices for Multi-Process Environments

**Date:** 2026-02-26
**Status:** Complete
**Purpose:** Understand Dolt's locking mechanisms, failure modes, and best practices for concurrent multi-process/multi-agent access.

---

## Table of Contents

1. [Noms Storage Layer and the LOCK File](#1-noms-storage-layer-and-the-lock-file)
2. [What Happens When a Dolt Process Is Killed](#2-what-happens-when-a-dolt-process-is-killed)
3. [Multi-Process Access Patterns](#3-multi-process-access-patterns)
4. [Dolt Server Mode (dolt sql-server)](#4-dolt-server-mode-dolt-sql-server)
5. [Lock Timeout and Stale Lock Configuration](#5-lock-timeout-and-stale-lock-configuration)
6. [Beads Project: Real-World Lock Contention Case Study](#6-beads-project-real-world-lock-contention-case-study)
7. [Critical Data Loss Bug (v1.78.5 - v1.80.2)](#7-critical-data-loss-bug-v1785---v1802)
8. [Recommendations Summary](#8-recommendations-summary)

---

## 1. Noms Storage Layer and the LOCK File

### Architecture Overview

Dolt's storage engine descends from the defunct **Noms** project. The core data lives in `.dolt/noms/`, which uses a content-addressed storage engine based on **Prolly Trees** to enable SQL performance with Git-like versioning.

The `.dolt/noms/` directory contains:

- **`manifest`** — Lists which table files exist, their storage format, lock hash, root hash, GC generation, and references to each tablefile with chunk counts.
- **`LOCK`** — A 0-byte file used as a **filesystem advisory lock** (`flock(2)`) to coordinate exclusive access to the database. Appears in both `noms/` and `oldgen/` directories.
- **`vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv`** (the "chunk journal") — All database writes go here first. Named after binary all-1s hash. On garbage collection, journal contents are compacted into permanent table files.
- **`journal.idx`** — Index file for faster lookups within the chunk journal.
- **Table files** (`*.tf`) — Permanent storage for compacted chunks.

### How the LOCK File Works

The LOCK file uses **POSIX advisory file locking** (`flock(2)`):

1. A process opens `.dolt/noms/LOCK` and acquires an **exclusive flock**.
2. While held, no other process can acquire the same lock.
3. When the process closes the file descriptor (or exits), the kernel **automatically releases the flock**.

This is fundamentally different from a "lockfile exists = locked" approach. The lock is held by the kernel on behalf of a file descriptor, not by the file's existence on disk.

**Key implication:** The LOCK file's *existence* on disk does not mean the database is locked. What matters is whether any process holds an active `flock()` on it. The file persists between uses as a stable target for the flock syscall.

### Journal Manifest Lock

The journal file has its own lock mechanism (the "journal manifest lock") that coordinates writes to the chunk journal. In embedded mode, this lock is held while the database is open for writes. The `nbs.ErrDatabaseLocked` error is returned when a second process attempts to acquire this lock and fails.

---

## 2. What Happens When a Dolt Process Is Killed

### Normal Termination (SIGTERM)

When `dolt sql-server` receives SIGTERM (the default `kill` signal), it performs graceful shutdown:
- Completes in-flight queries
- Flushes pending journal writes
- Closes the journal manifest lock
- Releases the flock on `.dolt/noms/LOCK`

The systemd unit file for Dolt specifies `KillSignal=SIGTERM` and `SendSIGKILL=no` to ensure graceful shutdown.

### Forced Termination (SIGKILL / crash / power loss)

When a process is killed forcefully:

1. **The flock is automatically released** — POSIX `flock(2)` locks are held by file descriptors, not files. When a process dies, the kernel closes all its file descriptors, which releases all flocks. **There is no orphaned lock problem with flock-based locking.**

2. **The LOCK file persists on disk** — This is expected and harmless. The file is just a target for the flock syscall; its existence does not indicate a lock is held.

3. **The journal file may be incomplete** — If the process was mid-write to the chunk journal, the journal may contain partially written records. Dolt handles this by truncating the journal to the last successfully loaded record on next startup (when loading in read-write mode).

4. **No database corruption** — The content-addressed storage model means partial writes to the journal don't corrupt existing data. The journal is append-only, and incomplete trailing records are discarded on recovery.

### The `.dolt/lock` File (Application-Level)

Some tools (notably Beads) use a separate application-level lock file at `.dolt/lock` (distinct from `.dolt/noms/LOCK`). **This** file can become orphaned if the process crashes, because it's a simple "file exists = locked" mechanism, not a kernel flock. Tools that use this pattern need their own stale-lock cleanup.

---

## 3. Multi-Process Access Patterns

### Pattern 1: Embedded Mode (Single-Writer)

```
Process A ──── embedded Dolt driver ──── .dolt/noms/ (exclusive flock)
Process B ──── embedded Dolt driver ──── BLOCKED (ErrDatabaseLocked)
```

In embedded mode, each process opens the database directly via the filesystem. The journal manifest lock enforces **single-writer exclusivity**. A second process attempting to open the same database gets `nbs.ErrDatabaseLocked`.

**When to use:** Single-process tools, CLI scripts that run sequentially, development environments.

**Risks:**
- Only one process can write at a time
- No built-in queuing — second process fails immediately (unless driver retry is configured)
- Read-only mode (`dolt sql -r csv -q ...`) still opens the database and historically caused issues (see Section 7)

### Pattern 2: Server Mode (Multi-Writer via SQL Protocol)

```
Process A ──── MySQL wire protocol ──── dolt sql-server ──── .dolt/noms/ (exclusive flock)
Process B ──── MySQL wire protocol ────────────┘
Process C ──── MySQL wire protocol ────────────┘
```

In server mode, a single `dolt sql-server` process holds the exclusive flock. All client processes connect via the MySQL wire protocol (port 3306 by default). The server handles concurrent access internally.

**When to use:** Multi-agent environments, production deployments, any scenario with concurrent writes.

**Advantages:**
- Handles concurrent connections natively (default `max_connections: 1000`)
- Session-level isolation — each connection has its own HEAD and working state
- No filesystem lock contention between clients
- Standard database connection pooling and retry patterns apply

### Pattern 3: Embedded Mode with Driver Retry (Cooperative Single-Writer)

```
Process A ──── embedded driver (holds lock) ──── .dolt/noms/
Process B ──── embedded driver (retrying with exponential backoff) ────┘
                  └── eventually acquires lock when A releases
```

The Dolt Go embedded driver (`github.com/dolthub/driver`) supports `Config.BackOff` for exponential backoff retry when the database is locked.

**When to use:** Light concurrency (2-3 processes), tools that need occasional write access but can tolerate delays.

**Configuration example:**
```go
import "github.com/dolthub/driver"

cfg := driver.Config{
    // ... standard config ...
    BackOff: &backoff.ExponentialBackOff{
        MaxElapsedTime: 30 * time.Second,
    },
}
connector, err := driver.NewConnector(cfg)
db := sql.OpenDB(connector)
```

---

## 4. Dolt Server Mode (dolt sql-server)

### Session Isolation Model

Each server connection maintains independent state through session variables:

- `@@<dbname>_head` — The HEAD commit for the session
- `@@<dbname>_working` — Current working state hash

Changes made in one session are invisible to other sessions until explicitly committed and merged. This prevents write stomping but requires explicit coordination for shared state.

### Concurrency Characteristics

| Setting | Default | Description |
|---------|---------|-------------|
| `max_connections` | 1000 | Simultaneous client connections |
| `back_log` | 50 | Blocked connections waiting in queue |
| `max_connections_timeout_millis` | 60000 | How long blocked connections wait |
| `read_timeout_millis` | 28800000 | Read operation timeout (8 hours) |
| `write_timeout_millis` | 28800000 | Write operation timeout (8 hours) |

### Write Throughput

Dolt can handle approximately **300 writes per second**, though this varies with database size, update size, and replication settings. This is sufficient for most development tool and agent coordination use cases, but not for high-volume OLTP workloads.

### Branch-Based Isolation for Agents

With `autocommit: false`, each agent session can:
1. Create a session-specific branch
2. Make modifications in isolation
3. Merge changes back to the main branch
4. Use `GET_LOCK`/`RELEASE_LOCK` for coordinating shared metadata (e.g., `dolt_branches`)

### MCP Integration (v1.58.7+)

Dolt sql-server can start an MCP HTTP server alongside the SQL server, providing AI agents direct access via the Model Context Protocol. Agent operations are isolated to branches, preventing production impact.

### systemd Deployment

Recommended systemd unit file:

```ini
[Unit]
Description=Dolt SQL Server
After=network.target

[Service]
User=dolt
Group=dolt
WorkingDirectory=/var/lib/doltdb/databases
ExecStart=/usr/local/bin/dolt sql-server
KillSignal=SIGTERM
SendSIGKILL=no
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Key: `SendSIGKILL=no` ensures graceful shutdown with journal flush.

### Garbage Collection Caveat

Running `CALL dolt_gc()` **breaks all open connections** to the running server. In-flight queries on those connections may fail and must be retried. Schedule GC during low-activity windows.

---

## 5. Lock Timeout and Stale Lock Configuration

### What Dolt Exposes

Dolt's server configuration **does not expose explicit lock timeout or stale lock detection settings**. The locking behavior is handled at lower levels:

1. **flock-based locking** — The kernel manages lock lifetime. No timeout needed because locks are released on process exit.

2. **Embedded driver retry** — `Config.BackOff` on the Go embedded driver controls retry behavior. This is application-level, not a Dolt server setting.

3. **`DisableSingletonCache`** (embedded mode) — Added in Dolt PR #10363. When enabled, each `Open()` constructs a fresh store instead of reusing a cached singleton. This prevents stale lock references but increases overhead. Primarily for embedded/driver use cases where multiple opens/closes happen in one process.

4. **Fail-fast on journal lock** — Also from PR #10363. Instead of blocking indefinitely on the journal manifest lock, immediately returns `nbs.ErrDatabaseLocked`, allowing the caller to implement their own retry strategy.

### What Dolt Does NOT Expose

- No configurable lock timeout duration at the server level
- No built-in stale lock detection or cleanup mechanism
- No lock priority or fairness settings
- No lock-wait queue visibility

### The Flock Advantage

Because Dolt uses POSIX `flock(2)` (not lockfiles), stale lock detection is **not needed**. The kernel automatically releases locks when processes die. The only scenario where manual intervention is needed is with application-level lockfiles (like Beads' `.dolt/lock`), which are separate from Dolt's own locking.

---

## 6. Beads Project: Real-World Lock Contention Case Study

The [Beads project](https://github.com/steveyegge/beads) (steveyegge/beads) — a memory system for coding agents — has been through a complete arc of Dolt lock management approaches, making it an excellent case study.

### Phase 1: Manual Lock Cleanup (PR #1260) — Problematic

The initial approach in Beads involved:
- Detecting stale lock files by checking age (>5 second threshold)
- Manually deleting `.beads/dolt/.dolt/lock` files
- Application-level retry loops around database operations

**Problems encountered:**
- **Race conditions** — Deleting a LOCK file that another process legitimately holds can corrupt the database
- **Arbitrary thresholds** — The 5-second age heuristic was too fragile for production use
- **Duplicated logic** — Retry should be in the driver, not the application
- **Path bugs** — Relative path handling caused path doubling (`.beads/dolt/.beads/dolt`)

### Phase 2: Driver-Level Retry (Issue #1401) — Better

The improved approach (documented in [issue #1401](https://github.com/steveyegge/beads/issues/1401)):
- Removed all manual lock file cleanup
- Configured `embedded.Config.BackOff` with exponential backoff (30s max)
- Proper connector lifecycle: store `*embedded.Connector`, explicitly `Close()` on shutdown
- Unit-of-work pattern: `withEmbeddedDolt()` helper ensuring fresh connectors per operation
- `filepath.Abs()` for path normalization before passing to driver
- `context.Background()` for initial connectivity checks

### Phase 3: Server Mode Only (v0.56.0) — Best

As of Beads v0.56.0 (2026-02-23), embedded mode was **entirely removed**:
- All database access goes through `dolt sql-server`
- Users run `bd dolt start` or configure a systemd service
- Multi-agent scenarios "just work" via standard MySQL connections
- Lock contention is eliminated entirely at the application level

### Phase 4: Lock Health Diagnostics (v0.55.0+)

Beads added proactive health checks:
- `bd doctor` detects and reports `dolt-access.lock` and `noms LOCK` issues
- Uses **flock probes** (actual `flock()` attempts) rather than checking file existence
- Surfaces lock errors with actionable guidance instead of silent empty results

### Key Lessons from Beads

1. **Never manually delete LOCK files** — They use flock, not existence-based locking. Deleting them is at best useless and at worst dangerous.
2. **Never implement application-level retry for lock contention** — Use the driver's built-in backoff.
3. **For multi-agent scenarios, just use server mode** — It eliminates the entire class of problems.
4. **Use flock probes for diagnostics** — Test whether a lock is held by attempting to acquire it, not by checking file metadata.

---

## 7. Critical Data Loss Bug (v1.78.5 - v1.80.2)

### The Bug

In Dolt versions 1.78.5 through 1.80.2, a data loss bug existed when **multiple dolt processes accessed the same database simultaneously**.

**Root cause:** Since v1.78.5, Dolt truncated the journal file to the last successfully loaded record on database load. This is correct when the CLI is the **exclusive writer**. However, Dolt also loads databases in **read-only mode** (e.g., `dolt sql -r csv -q ...`), and the bug caused truncation to occur even in read-only mode.

**Failure scenario:**
1. `dolt sql-server` is running and actively writing to the journal
2. A read-only CLI command (`dolt sql -r csv -q ...`) opens the same database
3. The read-only process truncates the journal to its last known good record
4. The server continues writing at its previous journal offset
5. The gap between truncation point and write offset is zero-filled by the OS
6. Later reads of the corrupted journal region produce checksum errors or load failures

### The Fix

- Fixed in v1.81.0: Journal truncation now only occurs when loading in **read-write mode**
- Read-only loads leave the journal file unmodified

### Relevance

This bug demonstrates that even "read-only" Dolt operations can be dangerous when a server is running. The safest architecture is to route **all** access (read and write) through `dolt sql-server`, never mixing CLI and server access to the same database.

---

## 8. Recommendations Summary

### For Multi-Agent / Multi-Process Environments

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| Multiple agents writing concurrently | **`dolt sql-server`** | Handles all locking internally; standard MySQL connections |
| Single agent, occasional CLI access | **Embedded mode** with driver retry | Simpler deployment; driver handles lock contention |
| CI/CD pipelines (sequential) | **CLI mode** | No concurrency; each step completes before next starts |
| Mixed read/write workloads | **`dolt sql-server` only** | Avoids the v1.78-v1.80 journal truncation class of bugs |

### Deployment Best Practices

1. **Use server mode for production** — Run `dolt sql-server` as a systemd service with `SendSIGKILL=no` for graceful shutdown.

2. **Never mix CLI and server access** — If a server is running, all access (including reads) should go through the SQL protocol. Direct CLI access to a server-managed database risks journal corruption.

3. **Never manually delete LOCK files** — Dolt uses kernel-level flock, not existence-based locking. The file persisting on disk is normal. If you suspect a stuck lock, verify the holding process with `fuser .dolt/noms/LOCK` or `lsof .dolt/noms/LOCK`.

4. **Use flock probes for health checks** — Test lock status by attempting a non-blocking `flock()`, not by checking file age or existence.

5. **Configure driver backoff for embedded mode** — If you must use embedded mode with potential concurrency, configure `Config.BackOff` with exponential backoff (30s max recommended).

6. **Manage connector lifecycle** — In embedded mode, explicitly `Close()` connectors to release the journal manifest lock. Use unit-of-work patterns (`withEmbeddedDolt()`) for operations that need the database briefly.

7. **Schedule GC carefully** — `CALL dolt_gc()` breaks all connections. Schedule during maintenance windows.

8. **Keep Dolt updated** — The v1.78-v1.80 journal truncation bug demonstrates that storage-layer bugs happen. Stay current.

### Anti-Patterns to Avoid

- **Manual LOCK file deletion** — Race condition risk; the file is a flock target, not a lockfile
- **Application-level retry loops** — Duplicates driver functionality; use `Config.BackOff` instead
- **Stale lock detection by file age** — Meaningless for flock-based locks; check with `flock()` probe
- **Mixing CLI reads with running server** — Risk of journal truncation (fixed in v1.81+ but indicates a class of issues)
- **`SIGKILL` for server shutdown** — Bypasses journal flush; use `SIGTERM` with graceful shutdown

---

## Sources

### DoltHub Official
- [Anatomy of a Dolt Database](https://dolthub.awsdev.ld-corp.com/blog/2024-10-28-dolt-anatomy/) — Storage layer architecture, journal file, LOCK files
- [dolt sql-server Concurrency](https://www.dolthub.com/blog/2021-03-12-dolt-sql-server-concurrency/) — Session isolation, concurrent connections
- [Dolt Server Configuration](https://docs.dolthub.com/sql-reference/server/configuration) — max_connections, timeouts
- [Application Server Installation](https://docs.dolthub.com/introduction/installation/application-server) — systemd setup
- [Dolt Releases](https://github.com/dolthub/dolt/releases) — v1.81 journal fix, embedded lock contention fixes (PR #10363)
- [Announcing Dolt SQL Server MCP](https://www.dolthub.com/blog/2025-09-09-announcing-dolt-sql-server-mcp/) — AI agent integration
- [Embedding Dolt in Go](https://www.dolthub.com/blog/2022-07-25-embedded/) — Embedded driver basics
- [Dolt Go Driver](https://github.com/dolthub/driver) — Config.BackOff, connector API

### Beads (steveyegge/beads) — Lock Contention Case Study
- [Issue #1401: Replace manual lock cleanup with driver-level retry](https://github.com/steveyegge/beads/issues/1401) — Comprehensive analysis of lock handling approaches
- [TROUBLESHOOTING.md](https://github.com/steveyegge/beads/blob/main/docs/TROUBLESHOOTING.md) — Lock file locations, embedded vs server mode
- [CHANGELOG.md](https://github.com/steveyegge/beads/blob/main/CHANGELOG.md) — v0.56.0 removal of embedded mode, lock diagnostics evolution
