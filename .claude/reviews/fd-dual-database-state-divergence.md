# fd-dual-database-state-divergence -- Review Findings

## Summary

The Intercom dual-process system has a fundamental asymmetry: messages and chat metadata are dual-written (SQLite + Postgres outbox), but registered groups, tasks, sessions, and router state are written to SQLite only with no propagation to Postgres. When Rust's orchestrator is enabled (the production configuration), it reads exclusively from Postgres for groups, tasks, and sessions -- meaning any entity written only to SQLite is invisible to the orchestrator. The most critical gap is registered group propagation: the Node IPC `register_group` path and the Node `/model` command both call `setRegisteredGroup` in SQLite without any Postgres dual-write, leaving the Rust side operating on stale group state until intercomd is restarted and reloads from Postgres (which itself may be empty for that group).

## Findings

### [P0] register_group IPC writes to SQLite only -- Postgres never receives new groups

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/index.ts:67-89` (registerGroup function)
- **File**: `/home/mk/projects/Demarch/apps/intercom/src/db.ts:686-703` (setRegisteredGroup -- SQLite only)
- **File**: `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:400-431` (register_group IPC handler)
- **Issue**: When a container issues a `register_group` IPC command, Node calls `registerGroup()` -> `setRegisteredGroup()` which writes only to SQLite. There is no call to `dualWriteToPostgres('/groups/set', ...)`, no `writeToOutbox(...)` call, and no HTTP POST to intercomd's `/v1/db/groups/set` endpoint. The Rust daemon loads groups from Postgres at startup (main.rs:253-277) and caches them in `Arc<RwLock<Groups>>`. A newly registered group never enters the Rust in-memory map or Postgres until manual intervention.
- **Scenario**: The main group's container registers a new Telegram group via IPC. The group appears in SQLite immediately and Node's in-memory `registeredGroups` map. But the Rust orchestrator's `groups` map and Postgres `registered_groups` table remain empty for that JID. When a message arrives for the new group:
  1. The outbox drain stores the message in Postgres `messages`.
  2. `queue.enqueue_message_check()` fires.
  3. `process_group_messages()` looks up the JID in `groups.read().await` (line process_group.rs:98-104) and gets `None`.
  4. Returns `Ok(true)` -- silently skips the group. The message is never processed.
- **Fix**: After `setRegisteredGroup(jid, group)` in `registerGroup()` (index.ts:80), add a fire-and-forget `dualWriteToPostgres('/groups/set', { jid, name: group.name, folder: group.folder, trigger: group.trigger, added_at: group.added_at, container_config: group.containerConfig, requires_trigger: group.requiresTrigger, runtime: group.runtime, model: group.model })`. Also update the Rust in-memory `groups` map when the `/v1/db/groups/set` endpoint receives a write -- currently `db.rs:set_registered_group` only writes to Postgres, it does not update `AppState.groups`.

### [P0] Node /model command writes model/runtime to SQLite only -- Rust orchestrator uses stale model

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/index.ts:260-266` (handleModel)
- **Issue**: When Node handles a `/model` slash command, it updates `group.model` and `group.runtime`, calls `setRegisteredGroup(chatJid, group)` (SQLite only), and returns. There is no Postgres write. The Rust side's in-memory `groups` map and Postgres `registered_groups` table retain the old model/runtime values. `process_group_messages()` at process_group.rs:160 calls `resolve_runtime(&group)` using the stale Rust-side group, so the next container spawns with the old runtime.
- **Scenario**: User sends `/model gemini-3.1-pro` via WhatsApp. Node updates SQLite and its in-memory cache. But the Rust orchestrator still sees `claude` as the runtime. The next message triggers a Claude container instead of Gemini. The user sees the wrong model responding.
- **Fix**: Same as P0 above -- add `dualWriteToPostgres` call after `setRegisteredGroup`. Alternatively, route the Node `/model` command through the Rust `/v1/commands` endpoint (which already emits `SwitchModel` effects that update Rust in-memory + Postgres at main.rs:879-897). Note that Telegram commands already go through the Rust command endpoint via `onCommand` -> `handleCommand` in index.ts, but WhatsApp commands use the Node-local handler. This means model switches work correctly on Telegram (Rust handles it) but silently diverge on WhatsApp (Node handles it).

### [P1] SwitchModel effect updates Rust in-memory + Postgres but not SQLite

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/main.rs:879-897` (apply_command_effects SwitchModel)
- **Issue**: When the Rust command handler processes a `/model` switch via the `SwitchModel` effect, it updates the in-memory `groups` map and persists to Postgres via `pool.set_registered_group()`. But it never notifies Node to update SQLite. The Telegram bridge's `route_ingress()` reads `registered_groups` from SQLite (telegram.rs:214), so it will use stale runtime/model values for trigger checking and runtime resolution on the Telegram ingress path.
- **Scenario**: User switches model via Telegram `/model gemini`. Rust updates its in-memory map + Postgres. Next Telegram message arrives, `route_ingress()` opens SQLite (telegram.rs:659-666), queries `registered_groups` (telegram.rs:802-846), and reads the old runtime. The ingress response reports the old model/runtime in `TelegramIngressResponse`. Node logs a parity warning but the message is still processed -- however, the parity data may cause confusion in routing decisions.
- **Fix**: After persisting to Postgres in `apply_command_effects`, also call back to Node's host callback server with the updated group state, or add a periodic sync from Postgres -> SQLite for the `registered_groups` table.

### [P1] Telegram ingress reads groups from SQLite, not Postgres -- stale routing decisions

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/telegram.rs:209-273` (route_ingress)
- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/telegram.rs:659-666` (open_sqlite)
- **Issue**: `TelegramBridge::route_ingress()` opens the SQLite database directly via `rusqlite::Connection` (not the Postgres pool) and queries `registered_groups` from there. This means the Telegram routing path depends on SQLite being the source of truth for group registration, while the orchestration path depends on Postgres. If a group is registered via the Rust `/v1/db/groups/set` endpoint (e.g., via legacy migration or future API), it will exist in Postgres but not SQLite, causing `route_ingress` to reject incoming messages as `unregistered_group`.
- **Scenario**: After a Postgres-only migration, a group exists in Postgres `registered_groups` but not in SQLite. The Rust orchestrator recognizes the group in its in-memory map. But when a Telegram message arrives, `route_ingress` queries SQLite, finds no row, and returns `accepted: false` with reason `unregistered_group`. The message is dropped at the Telegram channel layer before it ever reaches the outbox.
- **Fix**: Modify `route_ingress` to query from the Rust in-memory `groups` map (or Postgres) instead of SQLite. This requires passing the `groups` state into `TelegramBridge` or changing the method signature. Alternatively, maintain SQLite as a read-through cache that is populated from Postgres on startup.

### [P1] Tasks created via Node IPC are SQLite-only -- Rust scheduler cannot see them

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:303-314` (schedule_task handler)
- **File**: `/home/mk/projects/Demarch/apps/intercom/src/db.ts:464-483` (createTask -- SQLite only)
- **Issue**: When a container creates a scheduled task via IPC `schedule_task`, Node writes it to SQLite's `scheduled_tasks` table. There is no dual-write to Postgres. The Rust scheduler (`scheduler.rs`) reads due tasks from Postgres via `pool.claim_due_tasks()`. Tasks created through Node IPC are invisible to the Rust scheduler.
- **Scenario**: A container in the main group schedules a daily report via IPC. The task is stored in SQLite. The Rust scheduler polls `claim_due_tasks()` from Postgres and never finds the task. The daily report never fires.
- **Fix**: After `createTask()` in `ipc.ts`, add `dualWriteToPostgres('/tasks', {...})` to propagate the task to Postgres. Alternatively, route task creation through the Rust `/v1/db/tasks` endpoint.

### [P1] Task mutations (pause/resume/cancel) via Node IPC are SQLite-only

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/ipc.ts:322-374` (pause_task, resume_task, cancel_task handlers)
- **File**: `/home/mk/projects/Demarch/apps/intercom/src/db.ts:506-551` (updateTask, deleteTask -- SQLite only)
- **Issue**: Task status changes (pause, resume, cancel) via Node IPC write only to SQLite. The Rust scheduler reads from Postgres and will continue executing tasks that Node believes are paused or deleted.
- **Scenario**: User pauses a task via IPC. SQLite marks it `paused`. Postgres still shows `active`. Rust scheduler picks it up and runs it. User sees the "paused" task executing.
- **Fix**: Mirror task mutations to Postgres via `dualWriteToPostgres` or route through Rust endpoints.

### [P2] Outbox payload schema only supports 'message' and 'chat_metadata' -- no path for group/task/session entities

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/pg-writer.ts:57-60` (writeToOutbox type signature)
- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/outbox.rs:117-174` (drain loop match arms)
- **Issue**: The outbox type signature restricts `payloadType` to `'message' | 'chat_metadata'`. The drain loop in Rust has a hard match on `"message"` and `"chat_metadata"`, treating all other types as permanent failures. Even if a new payload type like `"registered_group"` were added to the Node side, the Rust drain would reject it with `"permanent: unknown payload_type"` and mark it as failed.
- **Scenario**: A developer adds `writeToOutbox(jid, 'registered_group', payload)` to fix the registration gap. The Rust drain encounters the row, hits the `other` match arm at outbox.rs:170, marks it failed, and logs an error. The group never reaches Postgres.
- **Fix**: Extend both the TypeScript type and the Rust drain loop to support additional entity types (`registered_group`, `task`, `session`) before adding outbox writes for those entities. Alternatively, use the existing HTTP dual-write path (`dualWriteToPostgres`) for non-message entities since they are low-volume and do not need the durability guarantees of the outbox.

### [P2] Session writes from Node are SQLite-only -- Rust and Node session state can diverge

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/db.ts:621-625` (setSession -- SQLite only)
- **File**: `/home/mk/projects/Demarch/apps/intercom/src/index.ts:128-151` (clearGroupSession -- SQLite only)
- **Issue**: When Node stores or clears a session, it writes to SQLite only. The Rust side maintains its own session state in `Arc<RwLock<Sessions>>` loaded from Postgres at startup, and persists session updates to Postgres (process_group.rs:273-276). If Node clears a session (e.g., on `/reset` via WhatsApp), Postgres and Rust's in-memory cache retain the old session ID.
- **Scenario**: WhatsApp user sends `/reset`. Node clears the session from SQLite and in-memory. But Rust still has the old session ID. The next message processed by the Rust orchestrator passes the stale session ID to the container, which resumes the old conversation instead of starting fresh.
- **Fix**: The Rust `/v1/commands` endpoint already handles `ClearSession` effect (main.rs:867-876) which clears both in-memory and Postgres. Ensure WhatsApp commands are routed through the Rust command endpoint rather than handled locally in Node. Alternatively, add `dualWriteToPostgres` for session operations.

### [P2] Rust /v1/db/groups/set endpoint does not update in-memory groups map

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/db.rs:524-536` (set_registered_group HTTP handler)
- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/main.rs:494` (db_routes use Option<PgPool> state, not AppState)
- **Issue**: The DB routes nest uses `Option<PgPool>` as state, not the full `AppState`. When Node calls `/v1/db/groups/set` (which it currently does not, but would if the P0 fix is applied), the handler writes to Postgres but does NOT update `AppState.groups` in-memory. The Rust orchestrator continues using its cached group data until restart.
- **Scenario**: Fix for P0 is applied -- Node calls `/v1/db/groups/set` after registration. Postgres is updated. But the Rust in-memory `groups` map still does not contain the new group. Messages for the group are still silently skipped by `process_group_messages()`.
- **Fix**: Either (a) change the DB routes to use `AppState` and update `groups` on set, or (b) add a dedicated `/v1/groups/register` endpoint on the `AppState` router that both persists to Postgres AND updates the in-memory map, or (c) implement a periodic group refresh from Postgres into the in-memory map.

### [P3] Schema parity is correct -- both databases have all columns

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/db.ts:105-150` (SQLite schema + migrations)
- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:348-358` (Postgres schema)
- **Issue**: No schema drift detected. Both databases define `container_config`, `requires_trigger`, `runtime`, and `model` columns in their respective `registered_groups` tables. SQLite uses `ALTER TABLE` migrations for backward compatibility; Postgres uses `CREATE TABLE IF NOT EXISTS` with the full schema. Column types differ as expected (TEXT vs JSONB for container_config, INTEGER vs BOOLEAN for requires_trigger) but the semantic mapping is correct. This is NOT a finding -- included for completeness.

### [P3] container_config is read correctly by both paths when present

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/process_group.rs:181-185` (container_config deserialization)
- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:1483` (container_config from Postgres JSONB)
- **Issue**: The Rust orchestrator correctly reads `container_config` from the `RegisteredGroup` struct (stored as JSONB in Postgres) and deserializes it into `ContainerConfig` for mount validation. The data type mapping works. However, this is academic: due to the P0 finding above, `container_config` set during group registration via Node IPC never reaches Postgres, so the Rust orchestrator always sees `None` for IPC-registered groups. The container runs without additional mounts or custom timeouts.
- **Scenario**: Main group registers a project group with `containerConfig: { additionalMounts: [{ hostPath: "/home/mk/projects/Foo", readonly: false }] }`. SQLite stores it. Rust orchestrator reads from Postgres, finds `container_config = NULL`. Container spawns without the mount. The agent cannot access the project directory.
- **Fix**: Resolves automatically once the P0 registration dual-write is fixed.
