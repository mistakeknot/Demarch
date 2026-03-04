# fd-queue-delivery-reliability -- Review Findings

## Summary

The Rust queue retry path has a critical liveness bug: after a processing failure, the deferred retry task sets `pending_messages=true` in memory but nothing triggers `drain_pending` to consume it, leaving the group stuck until an external event (new inbound message) arrives. Additionally, `drain_pending` only spawns `run_for_group` (message processing) -- it never pops or executes queued tasks from `pending_tasks`, causing tasks that hit the concurrency limit to spin in an infinite no-op loop. The outbox layer has a zombie-row problem where rows with `attempts >= 5` remain as `status='pending'` forever, unreachable by the claim query and never escalated to `status='failed'`.

## Findings

### [P0] Rust retry deferred flag is never drained without external stimulus

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:424-441`
- **Issue**: When `run_for_group` fails and `retry_count <= MAX_RETRIES`, it spawns a deferred async task that sleeps for `delay_ms` then sets `state.pending_messages = true`. However, `reset_group` and `drain_pending` execute immediately after the spawn (lines 454-455), BEFORE the deferred task fires. When the deferred task finally fires, it only sets the flag -- nobody calls `drain_pending` or `enqueue_message_check` afterward. The flag sits inert until an unrelated event (new inbound message, outbox row for that group) happens to trigger processing.
- **Scenario**: Group receives a message. Container spawns and fails (e.g., image missing). Retry #1 is deferred for 5 seconds. After 5s, `pending_messages=true` is set. No new messages arrive. The group is stuck indefinitely -- the retry never fires. In outbox mode, the 30-second fallback poll claims outbox rows but does NOT scan in-memory `pending_messages` flags.
- **Contrast**: Node's `scheduleRetry` (line 287-291 of `group-queue.ts`) calls `this.enqueueMessageCheck(groupJid)` directly in the setTimeout callback, which correctly re-enters the full enqueue/run path.
- **Fix**: Replace the deferred flag-set with an actual `enqueue_message_check` call. Change the spawned task to call `GroupQueue::enqueue_message_check` instead of directly setting the flag:
  ```rust
  let queue_handle = queue_handle.clone(); // Arc<GroupQueue>
  tokio::spawn(async move {
      tokio::time::sleep(Duration::from_millis(delay_ms)).await;
      queue_handle.enqueue_message_check(&jid_clone).await;
  });
  ```
  This requires `run_for_group` to receive an `Arc<GroupQueue>` handle (or a self-referencing closure) rather than only the raw `Arc<Mutex<Inner>>`. Alternatively, add a minimal helper that acquires the lock, sets the flag, and calls `drain_pending` inline.

### [P0] Rust drain_pending never executes queued tasks

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:459-503`
- **Issue**: `drain_pending` scans all groups for `pending_messages || !pending_tasks.is_empty()`, marks them active, and spawns `run_for_group`. But `run_for_group` only calls `process_messages_fn` -- it never pops from `pending_tasks` or calls `run_task`. When `process_messages_fn` finds no messages in Postgres (because the group had a task, not a message), it returns `Ok(true)`. Then `run_for_group` calls `reset_group` + `drain_pending` again. The pending tasks are still in the deque, so the cycle repeats: an infinite loop of empty `run_for_group` calls for that group, each consuming a concurrency slot momentarily.
- **Scenario**: Two containers are running (at max_concurrent=2). A scheduler task fires for group X and calls `enqueue_task`. The task goes into `pending_tasks` and group X is added to `waiting_groups`. When a slot frees up, `drain_pending` picks up group X and spawns `run_for_group`. The process_messages_fn finds no pending messages and returns true. `drain_pending` runs again, sees the task still queued, loops. Tasks are never executed.
- **Contrast**: Node's `drainGroup` (line 294-318 of `group-queue.ts`) explicitly checks `pendingTasks` first, pops the first task, and calls `runTask`.
- **Fix**: `drain_pending` must differentiate between task-only groups and message groups. For groups with pending tasks, pop the first task and spawn `run_task(queue, jid, task)` instead of `run_for_group`. Example:
  ```rust
  if has_tasks {
      let task = state.pending_tasks.pop_front().unwrap();
      to_spawn_tasks.push((jid.clone(), task));
  } else {
      to_spawn_messages.push(jid.clone());
  }
  ```

### [P1] Outbox rows with attempts >= 5 become zombie 'pending' rows

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:1241`
- **Issue**: `claim_outbox_rows` selects rows `WHERE status = 'pending' AND attempts < 5`. When `mark_outbox_retry` resets a row to `status='pending'` after the 5th transient failure, `attempts` remains 5. The row is now invisible to the claim query (fails the `attempts < 5` predicate) but is never transitioned to `status='failed'`. It stays as `status='pending'` forever. `outbox_stats` counts it as "pending" (misleading), `recover_stale_outbox_rows` ignores it (only handles `status='processing'`), and `cleanup_outbox` only deletes `status='delivered'` rows.
- **Scenario**: A message has a deserialization issue that's intermittent (e.g., a codec error during Postgres store). It gets retried 5 times. On the 5th retry, `mark_outbox_retry` is called. The row is now permanently stuck: reported as pending but never processed.
- **Fix**: After the claim query increments attempts to 5 and the row fails again, `mark_outbox_retry` should check if `attempts >= 5` and call `mark_outbox_failed` instead. Or add a periodic sweep:
  ```sql
  UPDATE message_outbox SET status = 'failed', last_error = 'max attempts exceeded'
  WHERE status = 'pending' AND attempts >= 5
  ```

### [P2] Rust queue retry resets retry_count after MAX_RETRIES but pending messages remain unprocessed in Postgres

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:442-451`
- **Issue**: When `retry_count > MAX_RETRIES`, the code resets `retry_count = 0` and logs "dropping (will retry on next incoming message)". This is acceptable as a circuit breaker. However, in outbox mode, the original outbox row was already marked `delivered` (line 128 of outbox.rs) before `process_messages_fn` was called. The message IS stored in the messages table but the cursor was rolled back (process_group.rs line 357-361). If no new message ever arrives for this group, the unprocessed messages sit in Postgres indefinitely. In legacy poll mode, `poll_once` would eventually re-discover them, but in outbox mode, the only discovery path is a new outbox row for the same chat_jid.
- **Scenario**: A group's container repeatedly fails (bad image, OOM, etc.). After 6 attempts (1 initial + 5 retries), the queue gives up. The messages are stored in Postgres (cursor rolled back). No new messages arrive for hours/days. The messages are never processed.
- **Fix**: After max retries, enqueue the group for delayed re-check at a longer interval (e.g., 10 minutes), or have the outbox drain periodic sweep check for groups with unprocessed messages beyond their cursor.

### [P2] Node GroupQueue shutdown does not cancel pending retry setTimeout timers

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/group-queue.ts:287-291`
- **Issue**: `scheduleRetry` creates `setTimeout` callbacks but does not store the timer IDs. The `shutdown` method sets `shuttingDown=true` but cannot cancel in-flight timers. The guard `if (!this.shuttingDown)` prevents new enqueues, but the setTimeout callback still fires and executes the guard check -- this is a minor resource leak, not a message loss. However, if `process.exit(0)` at line 342 of `index.ts` runs before all timers fire, pending retries are silently discarded. This is by design (containers are detached, not killed), but worth noting.
- **Scenario**: Group is in retry backoff (e.g., 80-second delay for retry #5). Shutdown signal arrives. `process.exit(0)` runs 10 seconds later. The retry timer fires but the process is already dead. The pending messages are silently dropped. On restart, they would be recovered by `recover_pending_messages` in legacy mode or `recover_stale_outbox_rows` in outbox mode, so this is a graceful-degradation path, not a hard loss.
- **Fix**: Store timer IDs and clear them on shutdown, or accept this as documented behavior. The existing recovery mechanisms handle the restart case.

### [P2] Outbox mark_outbox_retry does not fire NOTIFY -- retried rows wait up to 30 seconds

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercom-core/src/persistence.rs:1296-1311`
- **Issue**: `mark_outbox_retry` resets a row to `status='pending'` via UPDATE, but the Postgres trigger `trg_outbox_notify` only fires on INSERT. The LISTEN loop won't see the retried row. The row waits for the 30-second `DRAIN_FALLBACK_INTERVAL` poll to be re-claimed. This adds up to 30 seconds of latency per retry.
- **Scenario**: Transient Postgres error during `store_message` call. Row goes back to 'pending'. User waits up to 30 extra seconds for their message to be processed. Over 5 retries, this can accumulate to 2.5 minutes of unnecessary delay.
- **Fix**: After `mark_outbox_retry`, explicitly execute `NOTIFY intercom_outbox` in the same connection, or send a signal to `drain_tx` from the outbox drain loop when it encounters a retry.

### [P3] drain_pending HashMap iteration order is non-deterministic

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:469-474`
- **Issue**: The `candidates` vector is built by iterating `inner.groups` (a `HashMap`), which has no guaranteed order. When multiple groups have pending work and `max_concurrent` slots are limited, which groups get served is arbitrary. The Node version maintains a `waitingGroups` array that preserves FIFO order. The Rust version has `waiting_groups` but `drain_pending` iterates ALL groups from the HashMap, not from the ordered waiting list.
- **Scenario**: Groups A, B, and C all have pending messages. Only 1 slot is free. Due to HashMap iteration order, C might get served before A even though A has been waiting longest. This is a fairness issue, not a correctness issue.
- **Fix**: Iterate `inner.waiting_groups` (the ordered deque) instead of `inner.groups` when selecting candidates. Fall back to scanning `groups` only for the just-finished group (which may not be in `waiting_groups`).
