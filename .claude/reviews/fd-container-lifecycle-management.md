# fd-container-lifecycle-management -- Review Findings

## Summary

The Rust `GroupQueue` has a critical port omission: `register_process()` is defined but never called by either `process_group.rs` or `scheduler_wiring.rs`, leaving `container_name` and `group_folder` permanently `None` on all group states. This breaks `kill_group`, `send_message`, `close_stdin`, and idle preemption via `notify_idle`. Additionally, `drain_pending` in Rust always dispatches to `run_for_group` (message path) and never pops or executes pending tasks, causing an infinite dispatch loop when tasks are queued behind an active message container. The Node-side code is structurally sound due to `finally` blocks guaranteeing `reset_group` semantics.

## Findings

### [P0] Rust register_process never called -- container_name and group_folder always None

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:236`
- **Issue**: `GroupQueue::register_process()` is defined at line 236 but has zero callers in the entire Rust codebase. Neither `process_group.rs` (the message path) nor `scheduler_wiring.rs` (the task path) calls it after spawning a container. The Node-side equivalent is called from `index.ts` via the `onProcess` callback: `queue.registerProcess(chatJid, proc, containerName, group.folder)`.
- **Scenario**: Every container spawned by the Rust orchestrator has `GroupState.container_name = None` and `GroupState.group_folder = None`. This causes five cascading failures:
  1. `kill_group()` (line 313) always returns `false` -- `/reset` and `/model` commands cannot stop running containers
  2. `send_message()` (line 269) always returns `false` -- follow-up messages never reach active containers via IPC
  3. `close_stdin()` (line 291) is a no-op -- containers cannot be signaled to wind down
  4. `notify_idle()` (line 251) never writes close sentinels -- idle containers cannot be preempted by pending tasks
  5. `shutdown()` (line 353) reports zero detached containers since it checks `container_name.is_some()`
- **Fix**: In `process_group.rs::process_group_messages()`, the container name is deterministic (built from `container_name()` in `mounts.rs`). Register it before calling `run_container_agent`:
  ```rust
  let name = container_name(&group.folder);
  queue.register_process(&chat_jid, &name, Some(&group.folder)).await;
  let result = run_container_agent(...).await;
  ```
  Apply the same pattern in `scheduler_wiring.rs::run_scheduled_task()`.

### [P0] Rust drain_pending dispatches tasks to run_for_group instead of run_task -- tasks never execute

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:459`
- **Issue**: `drain_pending()` (line 459) collects groups with `pending_tasks` but dispatches them all to `run_for_group` (line 500), which calls `process_messages_fn` (the message processing path). It never pops tasks from `pending_tasks` or calls `run_task`. The Node-side `drainGroup()` (group-queue.ts:294) correctly checks `pendingTasks.length > 0`, shifts the first task, and calls `this.runTask()`.
- **Scenario**: A scheduled task enqueues while a message container is active. When the message container finishes, `drain_pending` sees `pending_tasks` is non-empty, sets `active=true` and `is_task_container=true`, then spawns `run_for_group`. This calls `process_messages_fn`, which finds no messages and returns `true`. Then `reset_group` clears `active`, `drain_pending` runs again, sees tasks still pending (never popped), sets `active=true` again -- infinite loop of empty message processing runs until the process is killed or max retries are hit.
- **Fix**: Rewrite `drain_pending` to match Node's `drainGroup` logic. When a group has `pending_tasks`, pop the front task and call `run_task` instead of `run_for_group`:
  ```rust
  if has_tasks {
      if let Some(task) = state.pending_tasks.pop_front() {
          state.active = true;
          state.is_task_container = true;
          inner.active_count += 1;
          let queue_clone = queue.clone();
          tokio::spawn(async move {
              run_task(queue_clone, jid, task).await;
          });
          continue;
      }
  }
  ```

### [P1] Rust run_for_group has no panic guard -- active=true stuck permanently on panic

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:386`
- **Issue**: `run_for_group()` calls `process_messages_fn` (line 398) and then runs `reset_group` (line 454). If the process function panics, the tokio task terminates without reaching `reset_group`. The group is left with `active=true` permanently, blocking all future messages for that group and consuming a concurrency slot. The Node equivalent uses `try/finally` (group-queue.ts:222-241) which guarantees cleanup.
- **Scenario**: A bug or unexpected data in message formatting causes a panic in `process_group_messages` (e.g., `.unwrap()` on a `None`). The group JID is permanently stuck: `active=true`, `active_count` never decremented. All future messages for that group queue up in `pending_messages` but never execute. The concurrency slot is permanently lost.
- **Fix**: Wrap the process_fn call with `tokio::task::spawn` + `JoinHandle` and match on the result, or use `std::panic::AssertUnwindSafe` + `FutureExt::catch_unwind`:
  ```rust
  let success = if let Some(ref f) = process_fn {
      match std::panic::AssertUnwindSafe(f(group_jid.clone()))
          .catch_unwind()
          .await
      {
          Ok(result) => result,
          Err(_) => {
              error!(group_jid = group_jid.as_str(), "process_messages_fn panicked");
              false
          }
      }
  } else { false };
  ```
  The same fix should be applied to `run_task` (line 513).

### [P1] Rust retry path sets pending_messages but never triggers drain

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/queue.rs:434`
- **Issue**: When a message processing failure triggers a retry (line 424-441), the spawned task sleeps for the backoff delay, then sets `state.pending_messages = true`. But it does nothing else -- no drain is triggered. The group sits with `active=false` and `pending_messages=true` until an external event (new incoming message, or another group finishing) happens to call `drain_pending`. The Node equivalent (group-queue.ts:287) calls `this.enqueueMessageCheck(groupJid)` which immediately triggers `runForGroup`.
- **Scenario**: A single-group system processes a message, fails, and schedules a retry. After the backoff delay, `pending_messages` is set to `true`. Since no other groups are running, `drain_pending` never executes. The retry is effectively lost until the next incoming message arrives (which could be hours or never for a low-traffic group).
- **Fix**: After setting `pending_messages = true`, trigger a drain by spawning `run_for_group` if the group is not active and a concurrency slot is available. Or more simply, make the retry task call an equivalent of `enqueue_message_check` which handles the full activate-and-spawn logic.

### [P2] Container timeout defaults to 5 minutes (Rust) when container_config is absent

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/runner.rs:33` and `:145`
- **Issue**: When `container_config` is `None` (the known dual-database bug where `container_config` is only set in SQLite, not Postgres), `DEFAULT_TIMEOUT_MS` is 300,000ms (5 minutes). However, the `idle_timeout_ms` default is 1,800,000ms (30 minutes). The grace-period calculation on line 147 (`container_timeout.max(config.idle_timeout_ms + 30_000)`) forces the actual timeout to 1,830,000ms (30.5 minutes). This means the "5-minute default" is never effective -- the idle grace period always dominates.
- **Scenario**: This is actually safe by accident -- the grace period ensures containers survive long enough for idle timeout to work. However, the default semantics are confusing: `DEFAULT_TIMEOUT_MS` (line 33) suggests a 5-minute hard kill, but the actual timeout is always 30+ minutes. If someone reduces `idle_timeout_ms` (e.g., to 60 seconds for testing), the hard timeout drops to 5 minutes, which may kill containers mid-work. The Node side defaults `CONTAINER_TIMEOUT` to 1,800,000ms (30 minutes) from `config.ts:118`, which is 6x larger.
- **Fix**: Align the Rust `DEFAULT_TIMEOUT_MS` with the Node `CONTAINER_TIMEOUT` (1,800,000ms), or read it from the shared `intercom.toml` config. The current value creates a false sense of a 5-minute timeout that never applies.

### [P2] Node timeout path: stopContainer uses shell string via exec instead of execFile

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/container-runner.ts:459`
- **Issue**: `stopContainer(containerName)` returns a shell command string (`docker stop ${name}`), which is then passed to `exec()` (not `execFile`). The `containerName` is constructed from `group.folder` (line 320-321) with regex replacement of non-alphanumeric characters, but `exec` invokes a shell which interprets metacharacters. The `group-queue.ts:195` already uses the safer `execFileSync` pattern for the same operation.
- **Fix**: Use `execFile` instead of `exec` to avoid shell interpretation, matching `group-queue.ts`:
  ```typescript
  execFile(CONTAINER_RUNTIME_BIN, ['stop', containerName], { timeout: 15000 }, (err) => {
  ```

### [P3] Rust cleanup_orphans does not exclude intercom-postgres

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/runner.rs:673`
- **Issue**: The Rust `cleanup_orphans()` stops all containers matching `name=intercom-` without the `CLEANUP_EXCLUDE` set that the Node side uses (container-runtime.ts:64) to protect `intercom-postgres`. If this function were ever called at Rust daemon startup (matching the Node pattern), it would kill the Postgres infrastructure container.
- **Scenario**: Currently safe because the function is never called (dead code). But if someone wires it into the Rust startup path, the Postgres container would be stopped, breaking all persistence.
- **Fix**: Add the exclusion filter: `names.filter(|n| *n != "intercom-postgres")`, and add a `#[allow(dead_code)]` annotation or remove the function if it is intentionally unused.

### [P3] Node onProcess callback invoked synchronously before stdin write -- confirmed safe

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/container-runner.ts:356`
- **Issue**: `onProcess(container, containerName)` is called at line 356 before `container.stdin.write()` at line 365. If the container exits immediately after spawn (before stdin write), the `close` event fires and resolves the promise.
- **Scenario**: No actual bug. The `finally` block in `runForGroup` (group-queue.ts:234) always resets the group state after the `processMessagesFn` promise resolves (which includes the `runContainerAgent` promise resolving via the `close` event). The ordering is correct: `onProcess` -> container exits -> `close` event resolves promise -> `runForGroup`'s `finally` resets state.
- **Fix**: No fix needed. Documenting as reviewed-and-confirmed-safe.
