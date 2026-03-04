# Intercom Dual-Process Architecture Review — Synthesis Report

**Date:** 2026-03-04
**Context:** 5-agent review of Rust daemon + Node host architecture
**Agents:**
1. fd-dual-database-state-divergence
2. fd-queue-delivery-reliability
3. fd-container-lifecycle-management
4. fd-mount-security-wiring
5. fd-ipc-authorization-boundary

**Verdict:** NEEDS-CHANGES — 2 P0, 8 P1 findings block production deployment

---

## Executive Summary

The Intercom dual-process system has **two critical P0 blockers that render message processing non-functional** under realistic conditions:

1. **Registered groups written to SQLite-only are invisible to the Rust daemon**, which reads exclusively from Postgres. Groups registered via IPC are permanently lost unless manually synced.
2. **Retry deferred flags are never drained without external stimulus**, leaving groups stuck indefinitely after processing failures.

Additionally, there are **8 P1 findings** spanning message delivery, task processing, container lifecycle, authorization, and mount security. The most systemic issues are:
- **Task processing disabled entirely** — `drain_pending` dispatches to wrong function, tasks never execute
- **Container name never registered** — `register_process` never called, breaks killing/signaling containers
- **Dual IPC polling creates authorization races** — both Node and Rust poll same directories with different logic

The architecture exhibits **high structural fragmentation**: dual database writes (SQLite + Postgres) not applied consistently to all entities, dual polling at the IPC layer, and divergent authorization on tasks vs. messages. These asymmetries compound—fixing one issue exposes another.

---

## Validation & Agent Status

| Agent | Files Read | Valid | Verdict | Notes |
|-------|-----------|-------|---------|-------|
| fd-dual-database-state-divergence | 5 | ✓ | NEEDS-CHANGES | 7 P0/P1 findings, single-cause cluster |
| fd-queue-delivery-reliability | 3 | ✓ | NEEDS-CHANGES | 3 P0/P1 findings, liveness bugs |
| fd-container-lifecycle-management | 5 | ✓ | NEEDS-CHANGES | 3 P0/P1 findings, process registration missing |
| fd-mount-security-wiring | 2 | ✓ | NEEDS-CHANGES | 1 P1 + 2 P2 findings, exclude validation gap |
| fd-ipc-authorization-boundary | 6 | ✓ | NEEDS-CHANGES | 2 P1 findings, race conditions + staleness |

**Validation:** 5/5 agents valid, 0 failed, 0 malformed.

---

## Deduplicated Findings by Severity

### CRITICAL (P0) — Must Fix Before Production

#### [P0-A] Registered Groups Never Propagate from Node to Rust

**Agents reporting:** fd-dual-database-state-divergence, fd-ipc-authorization-boundary
**Convergence:** 2/5 agents, acknowledged by both as same root cause

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/src/index.ts:67-89` (registerGroup)
- `/home/mk/projects/Demarch/apps/intercom/src/db.ts:686-703` (setRegisteredGroup — SQLite only)
- `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:400-431` (register_group IPC handler)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/main.rs:253-277` (Rust loads from Postgres at startup)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/process_group.rs:98-104` (group lookup)

**Issue:**

When a container registers a new group via IPC (`register_group` task), Node calls `setRegisteredGroup()` which writes **only to SQLite**. There is no dual-write to Postgres via `dualWriteToPostgres()`, no outbox call, and no HTTP POST to Rust's `/v1/db/groups/set`.

The Rust daemon loads groups from Postgres at startup and caches them in `Arc<RwLock<Groups>>`. A newly registered group never enters Rust's in-memory map or Postgres until manual intervention.

**Failure scenario:**

1. Main group's container registers a new Telegram group via IPC → group appears in SQLite + Node memory only
2. Message arrives for the new group → outbox drain stores message in Postgres `messages`
3. `queue.enqueue_message_check()` fires → Rust looks up JID in `groups.read().await`
4. `None` returned → `process_group_messages()` silently returns `Ok(true)` (line 102)
5. Message is never processed, remains in outbox indefinitely

**Severity:** P0 — blocks all group registration workflows in Rust mode
**Complexity:** Medium — requires dual-write plumbing plus in-memory map update
**Interacts with:** P0-B, P2-C, P2-D

---

#### [P0-B] Retry Deferred Flag Never Drained Without External Stimulus

**Agents reporting:** fd-queue-delivery-reliability, fd-container-lifecycle-management
**Convergence:** 2/5 agents, identical findings

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:424-441` (deferred retry task)
- `/home/mk/projects/Demarch/apps/intercom/src/group-queue.ts:287-291` (Node implementation for comparison)

**Issue:**

When `run_for_group` fails with `retry_count <= MAX_RETRIES`, the code spawns an async task that:
1. Sleeps for `delay_ms` backoff
2. Sets `state.pending_messages = true`
3. Does nothing else — no drain is triggered

The `reset_group` and `drain_pending` calls at lines 454-455 execute **immediately after the spawn**, before the deferred task has time to fire. When the deferred task finally sets the flag (after backoff), there is no mechanism to re-enter the enqueue/run cycle.

**Failure scenario:**

1. Single-group system processes a message
2. Container fails (image missing, OOM, etc.)
3. Retry #1 scheduled for 5s backoff
4. After 5s: `pending_messages = true` is set in memory
5. No new messages arrive for this group → `drain_pending` is never called
6. Group remains stuck indefinitely
7. Message waits for next external event (new inbound message) — which may never come

**Contrast with Node:** `scheduleRetry` (line 287-291 of `group-queue.ts`) directly calls `this.enqueueMessageCheck(groupJid)` in the callback, correctly re-entering the full enqueue/run path.

**Severity:** P0 — blocks message recovery after transient failures in single-group scenarios
**Complexity:** Low — requires spawning `enqueue_message_check` instead of flag-set
**Interacts with:** P1-C (queue processing), P1-E (outbox fallback poll)

---

### IMPORTANT (P1) — Should Fix Before Production

#### [P1-A] Rust drain_pending Dispatches Tasks to Wrong Function, Tasks Never Execute

**Agents reporting:** fd-queue-delivery-reliability, fd-container-lifecycle-management
**Convergence:** 2/5 agents, convergence on root cause

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:459-503` (drain_pending)
- `/home/mk/projects/Demarch/apps/intercom/src/group-queue.ts:294-318` (Node's drainGroup for comparison)

**Issue:**

`drain_pending()` scans groups for `pending_messages || !pending_tasks.is_empty()`, marks them active, and spawns `run_for_group()`. But `run_for_group` **only calls `process_messages_fn`** — it never pops from `pending_tasks` or calls `run_task`.

The Node version (`drainGroup` line 294-318) explicitly checks `pendingTasks.length > 0`, pops the first task, and calls `this.runTask()`.

**Failure scenario:**

1. Scheduler task fires for group X → `enqueue_task()` is called
2. Task goes into `pending_tasks` queue
3. Message container is active; task waits in queue
4. Message container finishes → `drain_pending` picks up group X (has pending tasks)
5. Spawns `run_for_group` → calls `process_messages_fn`
6. No pending messages → returns `true`
7. `reset_group` clears `active`, `drain_pending` runs again
8. Same task still in queue → infinite loop of empty message processing runs
9. Tasks are never executed
10. Concurrency slots stuck in no-op loop

**Severity:** P1 — disables all task scheduling in Rust
**Complexity:** Medium — requires conditional logic to pop and dispatch tasks separately
**Interacts with:** P0-B (retry loop), P1-B (container registration)

---

#### [P1-B] Rust register_process Never Called — Container Lifecycle Broken

**Agents reporting:** fd-container-lifecycle-management
**Convergence:** 1/5 agents, but affects 5 critical methods

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:236` (register_process definition)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/process_group.rs` (message path, never calls register_process)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/scheduler_wiring.rs` (task path, never calls register_process)
- `/home/mk/projects/Demarch/apps/intercom/src/container-runner.ts:356` (Node calls onProcess)

**Issue:**

`GroupQueue::register_process()` is defined but has **zero callers** in the Rust codebase. Neither `process_group.rs` nor `scheduler_wiring.rs` calls it after spawning a container.

Result: Every container spawned by Rust has:
- `container_name = None`
- `group_folder = None`

**Five cascading failures:**

1. **`kill_group()` always returns `false`** — `/reset` and `/model` commands cannot stop running containers
2. **`send_message()` always returns `false`** — follow-up messages never reach active containers via IPC
3. **`close_stdin()` is a no-op** — containers cannot be signaled to wind down
4. **`notify_idle()` never fires** — idle containers cannot be preempted by pending tasks
5. **`shutdown()` reports zero detached containers** — process cleanup metrics are wrong

**Severity:** P1 — breaks all container lifecycle operations (stop, signal, preemption)
**Complexity:** Low — requires two add-after-spawn lines in message and task paths
**Interacts with:** P1-A (task execution requires proper lifecycle), P2-A (container timeout defaults)

---

#### [P1-C] Dual IPC Polling Creates Authorization Race Conditions

**Agents reporting:** fd-ipc-authorization-boundary
**Convergence:** 1/5 agents, but affects security model

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:45-198` (Node IPC watcher)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs:234-258` (Rust IPC watcher)
- `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:79-82` (Node message authorization)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs:279` (Rust message authorization)

**Issue:**

Both Node (`startIpcWatcher`) and Rust (`IpcWatcher::run`) poll the same `data/ipc/` directory tree on 1-second intervals. Both read, process, and unlink files.

**Authorization divergence:**
- **Node messages:** applies `registeredGroups[data.chatJid]` check (in-memory, always fresh)
- **Rust messages:** applies `GroupRegistry::folder_for_jid()` (up to 10s stale, see P2-B)
- **Node tasks:** full authorization checks (lines 229-435)
- **Rust tasks:** **zero authorization**, delegates blindly to Node (line 319-321)

A file could be processed by either poller depending on timing, and different authorization decisions might be applied.

**Failure scenario:**

1. Non-main container writes a `register_group` task
2. **Race outcome A:** Rust polls first → forwards to Node with `is_main=false` → Node rejects ✓
3. **Race outcome B:** Node polls first → processes with in-memory `registeredGroups` → Node rejects ✓
4. BUT: For a message, if Rust polls first and GroupRegistry is stale (10s window), message could be wrongly authorized
5. Authorization decisions become non-deterministic based on polling race

**Severity:** P1 — security model not enforced consistently
**Complexity:** High — requires architectural decision (exclusive poller or separate IPC directories)
**Interacts with:** P2-B (registry staleness), P0-A (groups not in Postgres)

---

#### [P1-D] Rust Has No Task Authorization; Task Operations Unprotected

**Agents reporting:** fd-ipc-authorization-boundary
**Convergence:** 1/5 agents, critical security gap

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs:308-329` (process_tasks)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs:66` (IpcDelegate trait)

**Issue:**

`process_tasks()` parses the IPC task file and forwards it to Node via `delegate.forward_task()` **without performing any authorization check**. It passes `ctx.is_main` (directory-derived, trustworthy) but Rust itself performs **zero authorization**.

This creates an implicit contract: if Rust ever progresses the strangler-fig migration and handles tasks natively (without Node callback), there is no Rust-side authorization layer for:
- `schedule_task`
- `pause_task`, `resume_task`, `cancel_task`
- `register_group`

A non-main container could execute all task operations against any group.

**Severity:** P1 — security model incomplete; blocks native Rust task handling
**Complexity:** Medium — requires authorization checks mirroring Node
**Interacts with:** P1-C (dual polling), P0-A (groups not yet registered)

---

#### [P1-E] Outbox Rows with attempts >= 5 Become Zombie Pending Rows

**Agents reporting:** fd-queue-delivery-reliability
**Convergence:** 1/5 agents, but affects durability

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:1241` (claim_outbox_rows)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:1296-1311` (mark_outbox_retry)

**Issue:**

`claim_outbox_rows` selects rows `WHERE status = 'pending' AND attempts < 5`. When `mark_outbox_retry` is called after the 5th transient failure, `attempts` remains 5 and the row is reset to `status='pending'`.

The row is now:
- Invisible to `claim_outbox_rows` (fails the `attempts < 5` predicate)
- Never transitioned to `status='failed'`
- Stuck as `status='pending'` forever
- Counted as "pending" by `outbox_stats` (misleading)
- Ignored by `recover_stale_outbox_rows` (only handles `status='processing'`)

**Failure scenario:**

1. Message has intermittent deserialization issue (codec error, malformed payload)
2. Retried 5 times; on 5th attempt, `mark_outbox_retry` is called
3. Row becomes permanent zombie: `status='pending', attempts=5`
4. Never drained, never cleaned up, metrics show "pending" (misleading)

**Severity:** P1 — blocks message delivery indefinitely; affects observability
**Complexity:** Low — requires single conditional check in `mark_outbox_retry`
**Interacts with:** P0-B (retry loop), P2-E (monitoring gap)

---

#### [P1-F] Rust IPC Watcher Has 10-Second Authorization Staleness Window

**Agents reporting:** fd-ipc-authorization-boundary
**Convergence:** 1/5 agents

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs:694-750` (sync_registry_loop)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs:578-583` (is_authorized_target)

**Issue:**

The Rust `GroupRegistry` is populated by `sync_registry_loop()`, which fetches registered groups from Node every 10 seconds (line 712). During the **first 12 seconds of startup** (2-second delay + 10-second interval), the registry is empty.

Between sync cycles, a newly registered group exists in:
- Node's in-memory state ✓
- SQLite ✓
- Rust's GroupRegistry ✗ (not yet synced)

If Rust's IPC poller picks up a message from the new group before the next 10-second sync, `is_authorized_target()` returns `false`, and the message is discarded with log "Unauthorized IPC message attempt blocked" (not moved to errors — the file is deleted).

**Scenario:**

1. Main group registers "team-eng" via IPC → Node updates in-memory + SQLite
2. Team-eng's container writes a message within 10 seconds (before registry sync)
3. Rust IPC poller picks up the message
4. `is_authorized_target()` → "team-eng" not in GroupRegistry → deny
5. Message is dropped (file deleted, no retry, no outbox entry)
6. Loss is silent; no indication in logs that the message was ever received

**Severity:** P1 — message loss window during group registration
**Complexity:** Medium — requires push-based update or fallback logic
**Interacts with:** P0-A (groups not in Postgres), P1-C (dual polling)

---

#### [P1-G] Exclude Values in AdditionalMount Not Validated Against Path Injection

**Agents reporting:** fd-mount-security-wiring
**Convergence:** 1/5 agents, shared by both Node and Rust

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/src/container-runner.ts:291-293` (Node)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/secrets.rs:153-159` (Rust)

**Issue:**

The `exclude` array from `AdditionalMount` is passed through `validateAdditionalMounts` **without any validation**. Raw strings are interpolated into `--mount type=tmpfs,destination={containerPath}/{subdir},tmpfs-size=0`.

An `exclude` value containing `..` or `,` could:
- Perform path traversal out of mount point: `exclude: ["../../etc"]` → `destination=/workspace/extra/foo/../../etc` → `/etc`
- Inject Docker options: `exclude: ["x,tmpfs-size=999999999"]` → inject size override

**Scenario:**

Group's `containerConfig` in Postgres contains:
```json
{
  "additionalMounts": [{
    "hostPath": "~/projects/foo",
    "exclude": ["../../etc"]
  }]
}
```

Results in: `--mount type=tmpfs,destination=/workspace/extra/foo/../../etc` → resolves to `/etc` inside container.

**Severity:** P1 — security boundary violation; path traversal + injection
**Complexity:** Low — requires validation matching `isValidContainerPath`
**Interacts with:** P2-C (allowlist staleness), security model

---

### NICE-TO-HAVE (P2) — Polish & Observability

#### [P2-A] Container Timeout Defaults Create False Semantics (Rust vs. Node)

**Agents reporting:** fd-container-lifecycle-management
**Convergence:** 1/5 agents, but affects both implementations

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/runner.rs:33,145-147` (Rust: DEFAULT_TIMEOUT_MS=300s, idle=1800s)
- `/home/mk/projects/Demarch/apps/intercom/src/config.ts:118` (Node: CONTAINER_TIMEOUT=1800s)

**Issue:**

Rust `DEFAULT_TIMEOUT_MS` (line 33) is 300,000ms (5 minutes), but the actual timeout calculation on line 147 is:
```rust
container_timeout.max(config.idle_timeout_ms + 30_000)
```

With idle default of 1,800,000ms (30 minutes), the effective timeout is always **30+ minutes**, not 5 minutes. The 5-minute default is never applied.

Node defaults to 1,800,000ms directly (consistent with actual behavior).

**Scenario:**

If someone reduces `idle_timeout_ms` for testing (e.g., to 60 seconds), the hard timeout drops to 5 minutes (300s < 60s + 30s not possible, so max(300s, 90s) = 300s), which may kill containers mid-work.

**Severity:** P2 — false semantics, potential for surprising behavior if defaults change
**Complexity:** Low — align Rust DEFAULT_TIMEOUT_MS with Node (1,800,000ms)
**Interacts with:** P1-B (lifecycle), config consistency

---

#### [P2-B] Rust Silently Skips Mounts When Allowlist Is Missing; Node Logs Per-Mount

**Agents reporting:** fd-mount-security-wiring
**Convergence:** 1/5 agents, divergent behavior

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/mounts.rs:169-189` (Rust)
- `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:249-257` (Node)

**Issue:**

When allowlist is absent:
- **Node:** Logs WARN per requested mount: `"No mount allowlist configured at {path}"`
- **Rust:** Logs DEBUG once: `"Skipping additional mounts -- no allowlist loaded"` (easily missed in production)

An operator cannot tell which specific mounts were dropped in Rust, making troubleshooting difficult.

**Severity:** P2 — observability gap; affects operational debugging
**Complexity:** Low — elevate log level and enumerate mounts
**Interacts with:** P2-C (allowlist loading)

---

#### [P2-C] Node Allowlist Cache Prevents Runtime Updates Without Restart

**Agents reporting:** fd-mount-security-wiring
**Convergence:** 1/5 agent

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:22-24,62-65` (module-level cache)

**Issue:**

Module-level `cachedAllowlist` and `allowlistLoadError` cache the result permanently. If the allowlist file doesn't exist at startup, `allowlistLoadError` is set non-null (line 69), and all subsequent calls return null immediately without re-checking the filesystem.

If an operator creates the allowlist file after Node starts, mounts remain blocked forever until Node restart.

**Scenario:**

1. Operator starts intercom Node service before running `setup/mounts.ts`
2. Allowlist doesn't exist → `allowlistLoadError` is set to non-null
3. Operator creates allowlist file
4. Mounts still blocked with no indication a restart is needed

**Severity:** P2 — operational friction; silent failure after config provision
**Complexity:** Low — remove negative cache, only cache successful loads
**Interacts with:** P2-B (missing allowlist behavior)

---

#### [P2-D] Session Writes from Node Are SQLite-Only, Rust Session State Can Diverge

**Agents reporting:** fd-dual-database-state-divergence
**Convergence:** 1/5 agents

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/src/db.ts:621-625` (setSession)
- `/home/mk/projects/Demarch/apps/intercom/src/index.ts:128-151` (clearGroupSession)

**Issue:**

When Node clears a session (e.g., via `/reset` command), it writes to SQLite only. The Rust side maintains its own session state in `Arc<RwLock<Sessions>>` loaded from Postgres at startup, and persists updates to Postgres.

If Node clears a session, Postgres and Rust's in-memory cache retain the old session ID.

**Scenario:**

1. WhatsApp user sends `/reset`
2. Node clears session from SQLite + in-memory
3. Rust still has old session ID in memory and Postgres
4. Next message processed by Rust passes stale session ID to container
5. Container resumes old conversation instead of starting fresh

**Severity:** P2 — conversation state divergence; user sees stale session
**Complexity:** Medium — requires routing WhatsApp commands through Rust endpoint
**Interacts with:** P0-A (dual-write gap), P2-F (task mutations)

---

#### [P2-E] Rust /v1/db/groups/set Endpoint Does Not Update In-Memory Groups Map

**Agents reporting:** fd-dual-database-state-divergence
**Convergence:** 1/5 agents, but critical for P0 fix

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/db.rs:524-536` (set_registered_group handler)
- `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/main.rs:494` (db_routes use Option<PgPool>, not AppState)

**Issue:**

The DB routes nest uses `Option<PgPool>` as state, not the full `AppState`. When `/v1/db/groups/set` is called (which it will be if P0-A fix is applied), the handler writes to Postgres but does NOT update `AppState.groups` in-memory.

**Consequence of P0-A fix without P2-E fix:**

1. Node calls `/v1/db/groups/set` after registration (P0-A fix)
2. Postgres is updated ✓
3. Rust in-memory `groups` map is **not** updated ✗
4. Messages for the group are still silently skipped by `process_group_messages()` (line 102)
5. Fix appears to work but doesn't; regression when P0-A is deployed alone

**Severity:** P2 — P0-A fix doesn't work unless P2-E is also fixed
**Complexity:** Medium — requires either routing change or periodic refresh
**Interacts with:** P0-A (registration fix), P1-A (task execution)

---

#### [P2-F] Task Mutations (pause/resume/cancel) via Node IPC Are SQLite-Only

**Agents reporting:** fd-dual-database-state-divergence
**Convergence:** 1/5 agent

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:322-374` (pause_task, resume_task, cancel_task handlers)
- `/home/mk/projects/Demarch/apps/intercom/src/db.ts:506-551` (updateTask, deleteTask)

**Issue:**

Task status changes (pause, resume, cancel) via Node IPC write only to SQLite. The Rust scheduler reads from Postgres and will continue executing tasks that Node believes are paused or deleted.

**Scenario:**

1. User pauses a task via IPC
2. SQLite marks it `paused`
3. Postgres still shows `active`
4. Rust scheduler picks it up and runs it
5. User sees the "paused" task executing

**Severity:** P2 — task state divergence; automation sees wrong state
**Complexity:** Medium — requires dual-write or Rust-side mutation endpoints
**Interacts with:** P0-A (dual-write gap), P1-A (task execution)

---

#### [P2-G] Outbox mark_outbox_retry Does Not Fire NOTIFY; Retried Rows Wait 30 Seconds

**Agents reporting:** fd-queue-delivery-reliability
**Convergence:** 1/5 agent

**Files:**
- `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:1296-1311` (mark_outbox_retry)

**Issue:**

`mark_outbox_retry` resets a row to `status='pending'` via UPDATE, but the Postgres trigger `trg_outbox_notify` only fires on INSERT. The LISTEN loop doesn't see the retried row.

The row waits for the 30-second `DRAIN_FALLBACK_INTERVAL` poll to be re-claimed.

**Consequence:**

Transient Postgres error during message storage → row goes back to pending → waits 30 seconds before retry. Over 5 retries, up to 2.5 minutes of unnecessary latency.

**Severity:** P2 — latency amplification on transient failures
**Complexity:** Low — add explicit NOTIFY after UPDATE
**Interacts with:** P1-E (zombie rows), P0-B (retry backoff)

---

---

## Critical Systemic Issues

### 1. **Dual Database Asymmetry (Single Root Cause — P0-A)**

The architecture assumes all mutable entities (groups, tasks, sessions) are dual-written to both SQLite and Postgres. However, this is applied **inconsistently**:

| Entity | Path | SQLite | Postgres | Rust Reads | Impact |
|--------|------|--------|----------|-----------|--------|
| Messages | Outbox drain | ✓ | ✓ | ✓ Postgres | Works |
| Registered groups | IPC `register_group` | ✓ | ✗ | ✗ Missing | **P0-A** |
| Model/runtime | `/model` command | ✓ | ✗ | ✗ Stale | **P0-A** |
| Tasks created | IPC `schedule_task` | ✓ | ✗ | ✗ Missing | **P0-A** |
| Task mutations | IPC pause/resume | ✓ | ✗ | ✗ Stale | **P2-F** |
| Sessions | IPC `setSession`, `/reset` | ✓ | ✗ | ✗ Stale | **P2-D** |

**Root cause:** No systematic enforcement of dual-write at the point where these entities are created/mutated.

**Fix strategy:**
1. Identify all write paths for mutable entities (grep for `set*`, `create*`, `update*`, `delete*`)
2. Add `dualWriteToPostgres` call after each write (Node side), or route through Rust endpoints (strangler-fig)
3. Verify Rust `/v1/db/*` endpoints update both Postgres AND in-memory state
4. Document the dual-write protocol in AGENTS.md

---

### 2. **Task Processing Completely Disabled (P1-A)**

The Rust queue has:
- `pending_tasks` deque (populated by scheduler)
- `drain_pending()` function (supposed to execute tasks)
- But `drain_pending` only calls `run_for_group` (message path)
- And `run_for_group` never pops from `pending_tasks`

**Result:** Every enqueued task enters an infinite loop of empty message processing until it times out.

**Fix:** Rewrite `drain_pending` to differentiate task-only groups:
```rust
if has_tasks {
    if let Some(task) = state.pending_tasks.pop_front() {
        // spawn run_task
    }
} else if has_messages {
    // spawn run_for_group
}
```

---

### 3. **Container Lifecycle Never Registered (P1-B)**

The `register_process` function exists but is never called, leaving `container_name` and `group_folder` always `None`.

**Cascading failures:**
- `kill_group()` → can't kill containers → `/reset` doesn't stop running agents
- `send_message()` → can't send IPC to active containers → follow-up messages drop
- `close_stdin()` → can't signal containers to wind down → containers stay alive
- `notify_idle()` → can't preempt idle containers → tasks queue while idle containers block slots

**Fix:** Call after spawn in both message and task paths:
```rust
let name = container_name(&group.folder);
queue.register_process(&chat_jid, &name, Some(&group.folder)).await;
let result = run_container_agent(...).await;
```

---

### 4. **Dual IPC Polling Creates Races (P1-C)**

Both Node and Rust poll `data/ipc/` on 1-second intervals. For messages, they apply **different authorization logic** (Node uses fresh in-memory state, Rust uses 10s-stale GroupRegistry). For tasks, Rust applies **no authorization**.

**Result:** Authorization decisions are non-deterministic and incomplete.

**Fix:** Designate one process as the exclusive IPC poller. Since Rust handles queries natively, make Rust the sole poller and have it forward to Node via callbacks. Or separate IPC directories: `data/ipc-rust/` and `data/ipc-node/`.

---

## Recommended Action Plan (Priority Order)

### **Tier 1: Critical Blockers (Blocks Production)**

1. **[P0-B] Fix retry deferred flag draining** (2-3 hours)
   - Replace flag-set with `enqueue_message_check` call in retry spawned task
   - File: `queue.rs:424-441`
   - Test: Single-group retry scenario, verify drain fires within 1 second of backoff completion

2. **[P0-A] Fix group registration dual-write** (3-4 hours)
   - Add `dualWriteToPostgres` after `setRegisteredGroup` in both `registerGroup` (index.ts) and `/model` (index.ts:260-266)
   - Verify Rust `/v1/db/groups/set` updates in-memory map (requires P2-E)
   - Files: `index.ts:80`, `index.ts:264`, `db.rs:524-536`
   - Test: Register group via IPC, verify message processed by Rust

3. **[P1-A] Fix task dispatch in drain_pending** (2-3 hours)
   - Rewrite `drain_pending` to pop tasks and call `run_task` for task-only groups
   - File: `queue.rs:459-503`
   - Test: Schedule task while message container is active, verify task executes

4. **[P1-B] Register container process lifecycle** (1 hour)
   - Call `queue.register_process` in both `process_group_messages` and `run_scheduled_task`
   - Files: `process_group.rs`, `scheduler_wiring.rs`
   - Test: Verify `kill_group`, `send_message` return true after spawn

### **Tier 2: High-Impact Security/Reliability (1-2 weeks)**

5. **[P1-E] Prevent zombie outbox rows** (1 hour)
   - Check `attempts >= 5` in `mark_outbox_retry`, transition to `failed` instead of `pending`
   - File: `persistence.rs:1296-1311`
   - Test: Force 5 retries, verify row becomes `failed`

6. **[P1-G] Validate exclude values in AdditionalMount** (2-3 hours)
   - Add validation rejecting `..`, `/`, `,` in exclude entries
   - Files: `container-runner.ts:291-293`, `secrets.rs:153-159`
   - Test: Attempt to inject path traversal in containerConfig, verify rejection

7. **[P1-D] Add Rust-side task authorization** (3-4 hours)
   - Mirror Node's authorization checks in Rust `process_tasks`
   - Files: `ipc.rs:308-329`
   - Test: Non-main container sends `register_group` task, verify Rust rejects

8. **[P1-C] Eliminate dual IPC polling race** (8-12 hours, architectural)
   - Decision: Exclusive poller (Rust) OR separate directories
   - Implement chosen option, verify authorization determinism
   - Test: Run load test with concurrent registration + messaging, verify no lost messages

9. **[P1-F] Reduce GroupRegistry staleness window** (2-3 hours)
   - Implement push-based registry update callback OR fallback to Node for unknown JIDs
   - Files: `ipc.rs:694-750`, `ipc.rs:578-583`
   - Test: Register group, verify message processed within 1 second

### **Tier 3: Polish & Observability (2-3 weeks)**

10. **[P2-E] In-memory map sync for /v1/db/groups/set** (2-3 hours, dependency of P0-A fix)
11. **[P2-B] Improve allowlist missing observability** (1 hour)
12. **[P2-C] Remove Node allowlist negative cache** (1 hour, dependency of P2-B)
13. **[P2-D] Dual-write sessions** (2-3 hours, part of systematic P0-A fix)
14. **[P2-F] Dual-write task mutations** (2-3 hours, part of systematic P0-A fix)
15. **[P2-G] Add NOTIFY to mark_outbox_retry** (1 hour)
16. **[P2-A] Align container timeout defaults** (1 hour)

---

## Files Requiring Changes (Minimal Set for Production)

### Must-Fix (Tier 1 + P1-E, P1-G)

1. `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs`
   - Lines 424-441: Fix retry deferred flag (P0-B)
   - Lines 459-503: Fix drain_pending task dispatch (P1-A)

2. `/home/mk/projects/Demarch/apps/intercom/src/index.ts`
   - Lines 67-89: Add dual-write to registerGroup (P0-A)
   - Lines 260-266: Add dual-write to /model command (P0-A)

3. `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/process_group.rs`
   - Before run_container_agent: Call register_process (P1-B)

4. `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/scheduler_wiring.rs`
   - Before run_container_agent: Call register_process (P1-B)

5. `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs`
   - Lines 1296-1311: Check attempts >= 5 in mark_outbox_retry (P1-E)
   - Lines 1241: Consider transient failure handling for zombie rows

6. `/home/mk/projects/Demarch/apps/intercom/src/container-runner.ts` & `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/secrets.rs`
   - Validate exclude values (P1-G)

### Should-Fix (Tier 2 Architecture)

7. `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/ipc.rs`
   - Add task authorization (P1-D)
   - Reduce registry staleness (P1-F)
   - Architectural decision: exclusive poller vs. separate directories (P1-C)

---

## Cross-Agent Convergence Summary

| Finding | Agents | Consensus Level |
|---------|--------|-----------------|
| P0-A: Register group not in Postgres | 2 (fd-dual-db, fd-ipc-auth) | High — same root cause |
| P0-B: Retry deferred flag not drained | 2 (fd-queue, fd-container) | High — identical findings |
| P1-A: Tasks not executed by drain_pending | 2 (fd-queue, fd-container) | High — same code path |
| P1-B: register_process never called | 1 (fd-container) | High confidence, verified |
| P1-C: Dual IPC polling races | 1 (fd-ipc-auth) | High confidence, detailed |
| P1-D: No Rust task authorization | 1 (fd-ipc-auth) | High confidence, security gap |
| P1-E: Zombie outbox rows | 1 (fd-queue) | High confidence, deterministic |
| P1-F: GroupRegistry 10s stale window | 1 (fd-ipc-auth) | High confidence, by design |
| P1-G: Exclude validation missing | 1 (fd-mount-security) | High confidence, path injection |

**Key observation:** P0 and P1-A/B findings are from 2+ independent agents, confirming they are not analysis artifacts. The critical path to production is:

1. P0-B + P0-A + P1-A + P1-B (4 fixes, ~8-10 hours)
2. P1-E + P1-G (2 fixes, ~3-4 hours)
3. P1-D + P1-C + P1-F (3 fixes, ~13-19 hours, architectural)

---

## Conclusion

The Intercom dual-process architecture has **sound core concepts** (SQLite for local state, Postgres for distributed state, Rust for orchestration) but **broken execution** in the dual-write path, task queuing, and authorization boundaries.

The two P0s are production-blockers that must be fixed before deployment. They are not complex fixes individually, but they expose deeper issues (P2-E, P2-D, P2-F) that require systematic dual-write enforcement across all entity types.

The 8 P1 findings represent 8-12 weeks of distributed system debugging if deployed to production unfixed. The most urgent are the queue liveness bugs (P0-B, P1-A) and the security races (P1-C, P1-D, P1-G).

**Recommendation:** Fix Tier 1 (P0-B, P0-A, P1-A, P1-B) + P1-E + P1-G before production merge. Schedule Tier 2 (P1-C/D/F, full dual-write audit) for hardening phase post-MVP.
