# Correctness Review: Interserve Orchestration Modes

**Reviewed files:**
- `/home/mk/projects/Demarch/docs/plans/2026-02-25-interserve-orchestration-modes.md`
- `/home/mk/projects/Demarch/docs/plans/2026-02-25-interserve-orchestration-modes.exec.yaml`
- `/home/mk/projects/Demarch/os/clavain/scripts/dispatch.sh` (existing runtime; examined for interface contract)

**Reviewer:** Julik (fd-correctness)
**Date:** 2026-02-25

---

## Invariants

These must hold for the orchestrator to be correct:

1. **Dependency ordering invariant:** Task B may not begin until every task A where B depends on A has completed successfully.
2. **Stage barrier invariant:** In `manual-batching` mode, no task in stage N begins until all tasks in stage N-1 have completed.
3. **Failure isolation invariant:** If task A fails, every task that (directly or transitively) depends on A must be skipped, not dispatched with a fail-state context.
4. **Output fidelity invariant:** When task B receives dep_outputs from task A, those outputs must reflect A's actual completed state — not a stale, empty, or concurrent-write-in-progress state.
5. **Idempotent temp files invariant:** Prompt files written to `/tmp/` must not be shared or overwritten by concurrent orchestrator invocations.
6. **Parallelism safety invariant:** Tasks dispatched in the same batch must have no dependency relationship with each other.

---

## P0 Findings

### P0-1: Failure propagation gap — failed tasks not removed from pre-computed batches

**Location:** Plan section "Task 2, Step 1, component 7: orchestrate()"

**Description:**

The plan specifies that `resolve_execution_order()` pre-computes all execution batches upfront using `TopologicalSorter.get_ready()/done()` in a loop, then returns a static `list[list[task]]`. The main `orchestrate()` loop iterates over those batches:

```
load → validate → resolve order → for each batch: dispatch, collect, route outputs → summary
```

The problem: when a task in batch N fails, its dependent tasks appear in batches N+1, N+2, etc. — already placed there at planning time. The plan provides no mechanism to remove or skip those downstream tasks.

**Concrete failure narrative:**

Batch sequence for the manifest in dependency-driven mode:
```
Batch 0: [task-1]
Batch 1: [task-2]
Batch 2: [task-3, task-4, task-5]
Batch 3: [task-6]
```

1. Batch 0: task-1 completes. dep_outputs[task-1] = success result.
2. Batch 1: task-2 fails (dispatch.sh exits non-zero). dep_outputs[task-2] = fail result.
3. Batch 2: orchestrate() dispatches task-3, task-4, task-5 as scheduled. task-3 and task-5 both have `depends: [task-2]`.
4. `dispatch_task()` calls `summarize_output()` for task-2, which produces `Status: fail`.
5. task-3 and task-5 receive a prompt that says "Context from task-2: Status: fail" and execute against a codebase where `orchestrate.py` was never created.
6. task-3 and task-5 produce undefined behavior (may hallucinate code, may write garbage files, may exit non-zero themselves).
7. task-6 (tests) then runs against a partially broken codebase.

**Violated invariant:** Failure isolation invariant (invariant 3).

**Why this is a 3 AM incident:** The agent dispatched as task-3 has tool access to the filesystem. It will attempt to modify `orchestrate.py` which does not exist, potentially creating a corrupt or misguided version. If the summarization mentions "Status: fail" at all, the agent may attempt to work around the failure in unpredictable ways. The resulting codebase state after a 5-task partial failure is undefined.

**Minimal fix:**

The `orchestrate()` main loop must maintain a `skipped: set[str]` and after each batch, add any task whose result is `fail` along with all transitive dependents to `skipped`. Before dispatching each batch, filter out skipped tasks:

```python
failed_ids: set[str] = set()

for batch in batches:
    # Filter out tasks whose deps failed
    runnable = [t for t in batch if not (set(t.get('depends', [])) & failed_ids)]
    skipped = [t for t in batch if t not in runnable]
    for t in skipped:
        failed_ids.add(t['id'])
        results.append(TaskResult(t['id'], 'skip', None, None))

    batch_results = dispatch_batch(runnable, ...)
    for r in batch_results:
        if r.status != 'pass':
            failed_ids.add(r.task_id)
    results.extend(batch_results)
```

Alternatively, switch to a dynamic `get_ready()/done()` model where `done()` is only called for successful tasks. Failed tasks are never marked done, so `is_active()` eventually returns False and their dependents are naturally never scheduled.

---

### P0-2: Cross-stage implicit dependency paradox — explicit deps weaken ordering guarantee

**Location:** Plan section "Task 2, Step 1, component 2: build_graph()"

**Description:**

The plan specifies the cross-stage implicit dependency rule as:

> Cross-stage dependencies are implicit (all tasks in stage N depend on all tasks in stage N-1 completing, unless they have explicit `depends`).

The `unless they have explicit depends` clause is semantically inverted. It means:
- A task with **no explicit deps** in stage N receives the full stage-N-1 barrier (must wait for all of stage N-1).
- A task with **explicit deps** in stage N receives **no implicit barrier** (only its listed deps matter).

This produces the following paradox with the actual manifest:

```
Stage 1: [task-1, task-2]
Stage 2: [task-3 (deps:[task-2]), task-4 (deps:[task-1]), task-5 (deps:[task-2])]
```

Under the as-written rule:
- task-3: has explicit deps → skip implicit → depends only on task-2 (already in stage 1, correct)
- task-4: has explicit deps → skip implicit → depends **only on task-1**, NOT task-2
- task-5: has explicit deps → skip implicit → depends only on task-2

Result: **task-4 can start while task-2 is still running.** task-4 modifies `os/clavain/skills/writing-plans/SKILL.md`. task-2 is creating `os/clavain/scripts/orchestrate.py`. These files do not overlap, but:

1. The stage barrier promise (stage 2 starts only after stage 1 completes) is silently broken.
2. Any future manifest where a task-4-like entry needs to reference work from all of stage 1 will receive incomplete context. The `dep_outputs` dict will only contain task-1's output, not task-2's.
3. If task-2 fails after task-4 has already started, task-4 will have proceeded without knowing the dependency chain is broken.

**Violated invariants:** Stage barrier invariant (invariant 2), Dependency ordering invariant (invariant 1) for cross-stage partial dependencies.

**Concrete interleaving:**

```
t=0: orchestrate starts
t=1: batch [task-1] dispatched (no deps, correct)
t=2: task-1 completes -> dep_outputs[task-1] = result
t=3: batch [task-2, task-4] dispatched simultaneously
        (task-2: no-dep task in stage 1? No — wait, wrong scenario.
         Let me use the actual manifest.)
```

With the actual manifest and the as-written rule: task-2 has `depends: [task-1]` (explicit). task-4 has `depends: [task-1]` (explicit). Both are eligible to start as soon as task-1 completes. The stage barrier between "Schema & Core" and "Integration" is NOT enforced because all Integration tasks with explicit deps only list task-1, and the implicit rule is skipped for them.

```
t=0: Batch [task-1]
t=1: task-1 completes
t=2: Both task-2 (stage 1) and task-4 (stage 2) are "ready" per the graph
     -> stage barrier violated: Integration stage starts concurrently with remaining Schema & Core work
```

**Minimal fix:**

Change the rule to always **union** implicit cross-stage deps with explicit deps:

```python
def build_graph(manifest):
    graph = {}
    prev_stage_tasks = []
    for stage in manifest['stages']:
        for task in stage['tasks']:
            explicit = set(task.get('depends', []))
            # Always add stage barrier -- union, not replace
            implicit = set(prev_stage_tasks)
            graph[task['id']] = explicit | implicit
        prev_stage_tasks = [t['id'] for t in stage['tasks']]
    return graph
```

This correctly enforces both the stage barrier AND preserves explicit intra-stage ordering.

---

## P1 Findings

### P1-1: manual-batching mode ignores intra-stage explicit deps

**Location:** Plan section "Task 2, Step 1, component 4: resolve_execution_order(), manual-batching case"

**Description:**

The plan specifies `manual-batching`: "group by stage, run stages sequentially, tasks within stage in parallel."

This flattens all tasks within a stage into a single parallel batch, ignoring any explicit `depends` declarations between tasks in the same stage.

**Confirmed with actual manifest:**

Stage "Schema & Core" contains:
- task-1: `depends: []` (create JSON schema)
- task-2: `depends: [task-1]` (create orchestrate.py, which validates against the schema)

In `manual-batching` mode, task-1 and task-2 are dispatched simultaneously. task-2's verification step (`python3 orchestrate.py --validate example.yaml`) fails because the schema file does not exist yet — task-1 has not finished.

**Violated invariant:** Dependency ordering invariant (invariant 1) for intra-stage deps.

**Minimal fix:**

Within each stage, apply `TopologicalSorter` to the intra-stage subgraph to determine intra-stage sub-batches, then dispatch sub-batches sequentially within the stage:

```python
def resolve_manual_batching(stages, graph):
    batches = []
    for stage in stages:
        stage_task_ids = {t['id'] for t in stage['tasks']}
        # Build intra-stage subgraph
        intra_graph = {
            tid: graph[tid] & stage_task_ids
            for tid in stage_task_ids
        }
        ts = TopologicalSorter(intra_graph)
        ts.prepare()
        while ts.is_active():
            ready = ts.get_ready()
            if ready:
                batches.append([t for t in stage['tasks'] if t['id'] in ready])
                ts.done(*ready)
    return batches
```

---

### P1-2: ThreadPoolExecutor result loss on first exception

**Location:** Plan section "Task 2, Step 1, component 6: dispatch_batch()"

**Description:**

The plan specifies using `concurrent.futures.ThreadPoolExecutor` to dispatch tasks, then "collect results." The natural implementation pattern is:

```python
futures = [executor.submit(dispatch_task, task, ...) for task in tasks]
results = [f.result() for f in futures]
```

`[f.result() for f in futures]` is a list comprehension that calls `.result()` in order. The first future that raises an exception (e.g., `subprocess.TimeoutExpired` from a timed-out dispatch.sh call, or any unhandled exception in `dispatch_task`) propagates out of the comprehension, and **all remaining futures' results are discarded**.

**Concrete failure narrative:**

Batch: [task-3, task-4, task-5] in parallel with max_parallel=3.

1. task-3 times out at t+300s. `subprocess.run(timeout=300)` raises `subprocess.TimeoutExpired` inside its thread.
2. The future for task-3 stores the exception.
3. Main thread executes `[f.result() for f in futures]`. `futures[0]` might be task-3. `f.result()` re-raises `TimeoutExpired`.
4. task-4 and task-5 have completed successfully — their results are in their futures — but are never retrieved.
5. orchestrate() crashes or propagates the exception, treating the entire batch as failed.
6. task-6 (which only depends on task-2 and task-3) may be skipped even though task-4 and task-5 (which it does NOT depend on) are what failed.

**Violated invariant:** Output fidelity invariant (invariant 4) — results from successful tasks are lost.

**Minimal fix:**

Use `as_completed()` with per-future exception handling:

```python
from concurrent.futures import as_completed

results = []
future_to_task = {executor.submit(dispatch_task, task, ...): task for task in tasks}
for future in as_completed(future_to_task):
    task = future_to_task[future]
    try:
        result = future.result()
    except subprocess.TimeoutExpired:
        result = TaskResult(task['id'], 'timeout', None, None)
    except Exception as e:
        result = TaskResult(task['id'], 'error', None, None)
    results.append(result)
return results
```

This ensures all task results (pass, fail, timeout) are collected before returning.

---

### P1-3: resolve_execution_order / dependency-driven mode contradiction

**Location:** Plan section "Task 2, Step 1, component 4: resolve_execution_order()"

**Description:**

The plan describes two contradictory behaviors for `dependency-driven` mode:

1. `resolve_execution_order(graph, mode)` returns batches (a `list[list[task]]` — pre-computed, static).
2. `dependency-driven`: "use `TopologicalSorter.get_ready()` loop for maximum parallelism."

Maximum parallelism from `TopologicalSorter` requires a **dynamic** scheduling protocol: call `get_ready()` to get currently-eligible tasks, dispatch them, wait for completion, call `done()` to unblock successors, call `get_ready()` again. The sorter's state must be maintained across dispatch iterations.

If instead `resolve_execution_order()` pre-computes all batches upfront by running `get_ready()/done()` in a loop that assumes all tasks succeed, the result is a static list of waves. This loses two properties:

- **Runtime adaptability:** If tasks take different amounts of time, tasks in later waves cannot start until the slowest task in the current wave finishes. True dynamic scheduling would unblock each task the moment all its specific deps complete.
- **Failure propagation:** As noted in P0-1, pre-computed batches cannot exclude failed tasks' dependents.

The plan's `orchestrate()` description confirms the static model: "for each batch: dispatch, collect, route outputs." There is no `done()` call described in the main loop.

**Verdict:** The plan specifies a static pre-computed model but calls it "dynamic." The implementation will be correct in success cases (static batching gives the same order as dynamic when all tasks succeed) but incorrect for failure handling and suboptimal for runtime parallelism (e.g., if task-3 finishes in 10s but task-4 takes 290s, task-5's successors wait for task-4 even if they only depend on task-3).

**Recommended fix:** Either:

A. Commit to static pre-computed batches and document that limitation. Failure propagation must be handled by the batch filter (P0-1 fix). This is simpler to implement and dry-run.

B. Move the `TopologicalSorter` state into `orchestrate()` and drive it dynamically:
```python
ts = TopologicalSorter(graph)
ts.prepare()
while ts.is_active():
    ready_ids = ts.get_ready()
    tasks_to_run = [task_by_id[tid] for tid in ready_ids if tid not in failed_ids]
    results = dispatch_batch(tasks_to_run, ...)
    for r in results:
        if r.status == 'pass':
            ts.done(r.task_id)
        else:
            failed_ids.add(r.task_id)
            # Do NOT call ts.done() -- leaves dependents blocked
```

Option B is architecturally correct but requires that dry-run simulate the dynamic loop rather than call `resolve_execution_order()`.

---

### P1-4: Temp file path collision between concurrent orchestrator invocations

**Location:** Plan section "Task 2, Step 1, component 5: dispatch_task()"

**Description:**

The plan specifies writing prompt files to `/tmp/orchestrate-<task_id>.md`. Task IDs follow the pattern `^task-[0-9]+$`, so the paths are `/tmp/orchestrate-task-1.md`, `/tmp/orchestrate-task-2.md`, etc.

If two orchestrator invocations run concurrently (e.g., two engineers running the tool simultaneously, or a CI system and a human both running it, or a retry invocation that overlaps with a slow-running first invocation), both will write to the same file paths.

**Concrete failure narrative:**

1. Engineer A runs `orchestrate.py manifest-foo.exec.yaml`. orchestrate() for project Foo starts writing `/tmp/orchestrate-task-1.md` with Foo's task-1 prompt.
2. Engineer B runs `orchestrate.py manifest-bar.exec.yaml` 100ms later. orchestrate() for project Bar writes `/tmp/orchestrate-task-1.md` with Bar's task-1 prompt, overwriting Foo's.
3. Foo's dispatch_task for task-1 calls `dispatch.sh --prompt-file /tmp/orchestrate-task-1.md`. It reads Bar's prompt. Codex is dispatched with Bar's task against Foo's codebase.
4. Both files are silently wrong. No error is produced.

**Violated invariant:** Idempotent temp files invariant (invariant 5).

Secondary issue: if `dispatch_task()` does not use `try/finally` to clean up the temp file, failed runs leave stale `/tmp/orchestrate-task-N.md` files. A subsequent run with the same PID (after reboot or process recycling) could in theory read a stale file if the write step fails partway through, but this is an edge case compared to the concurrent collision.

**Minimal fix:**

Include the process ID and a run ID (UUID or timestamp) in the temp file name:

```python
import os, uuid
run_id = uuid.uuid4().hex[:8]
prompt_path = f"/tmp/orchestrate-{os.getpid()}-{run_id}-{task['id']}.md"
```

And clean up in `dispatch_task()`:

```python
try:
    prompt_path.write_text(prompt_content)
    result = subprocess.run(["bash", dispatch_sh, "--prompt-file", str(prompt_path), ...])
finally:
    prompt_path.unlink(missing_ok=True)
```

---

## P2 Findings

### P2-1: Manifest task-6 missing task-4 and task-5 as dependencies

**Location:** `docs/plans/2026-02-25-interserve-orchestration-modes.exec.yaml`, task-6 entry

**Description:**

task-6 is described as "Tests for orchestrate.py" and lists `files: [os/clavain/tests/test_orchestrate.py]`. Its `depends` is `[task-2, task-3]`.

task-4 updates `os/clavain/skills/writing-plans/SKILL.md` and task-5 updates `os/clavain/skills/executing-plans/SKILL.md`. These files are not tested by task-6's tests (which cover the Python orchestrator). So the concurrency is not a file conflict.

However, the manifest's execution order for `dependency-driven` mode with the correct implicit deps produces:

```
Batch 0: [task-1]
Batch 1: [task-2]
Batch 2: [task-3, task-4, task-5]  -- all unblocked after task-2
Batch 3: [task-6]  -- unblocked after task-3 (and task-2)
```

task-6 can start as soon as task-3 is done, while task-4 and task-5 may still be running. The test suite in task-6 tests the orchestrator. The skill files (task-4, task-5) are not exercised by the tests. This is not a data corruption risk with these specific tasks, but it signals a conceptual gap: if task-6 is intended to verify the full integration, it should depend on ALL integration tasks. As the manifest stands, the tests can pass while task-4 or task-5 are still in-flight or have failed.

**Recommended fix in manifest:**

```yaml
- id: task-6
  title: "Tests for orchestrate.py"
  files:
    - os/clavain/tests/test_orchestrate.py
  depends: [task-2, task-3, task-4, task-5]
```

---

### P2-2: all-sequential mode order may not match plan document order

**Location:** Plan section "Task 2, Step 1, component 4: resolve_execution_order(), all-sequential case"

**Description:**

`all-sequential` mode returns "each task as its own batch in topological order." The plan does not specify which topological order — `static_order()` returns a valid topological ordering but the specific sequence depends on the order nodes were inserted into the `TopologicalSorter` (Python dict ordering, which is insertion-order in 3.7+).

The plan document lists tasks as task-1, task-2, task-3, task-4, task-5, task-6. A user expecting tasks to execute in that order in `all-sequential` mode may be surprised if the topological sort produces a different valid ordering (e.g., task-1, task-2, task-4, task-3, task-5, task-6). This is valid topologically but confusing to the operator.

For `all-sequential`, correctness is maintained (any topological order is valid). This is a UX/observability issue rather than a data corruption risk. The fix is to document that the ordering is topological (not document order) and/or to prefer document order when breaking topological ties.

---

## Summary Table

| ID   | Severity | Title                                                    | Violated Invariant        |
|------|----------|----------------------------------------------------------|---------------------------|
| P0-1 | P0       | Failure propagation gap: failed deps dispatched anyway   | Failure isolation (3)     |
| P0-2 | P0       | Explicit deps weaken cross-stage barrier                 | Stage barrier (2), Dep ordering (1) |
| P1-1 | P1       | manual-batching ignores intra-stage explicit deps        | Dep ordering (1)          |
| P1-2 | P1       | ThreadPoolExecutor drops results on first exception      | Output fidelity (4)       |
| P1-3 | P1       | resolve_execution_order / dependency-driven contradiction| Dep ordering (1)          |
| P1-4 | P1       | /tmp prompt file collision under concurrent invocations  | Idempotent temp files (5) |
| P2-1 | P2       | Manifest task-6 missing task-4, task-5 deps              | (partial ordering gap)    |
| P2-2 | P2       | all-sequential order not deterministic relative to plan  | (UX/observability only)   |

---

## Recommended Fix Order

1. **P0-2 first (build_graph fix):** Change cross-stage implicit dep rule from "skip if explicit" to "always union." This is a one-line change in `build_graph()` and the correct foundation for everything else. Without this, the DAG itself is wrong.

2. **P0-1 next (failure propagation):** Add `failed_ids` set to `orchestrate()` main loop. Filter each batch against failed and transitively-blocked task IDs before dispatch.

3. **P1-3 / P1-1 together (scheduling model):** Decide on static vs dynamic scheduling. If static, document the limitation. If dynamic, move the `TopologicalSorter` state into `orchestrate()`. Fix `manual-batching` to apply intra-stage topo sort regardless.

4. **P1-2 (ThreadPoolExecutor):** Switch to `as_completed()` with per-future exception handling.

5. **P1-4 (temp files):** Add PID + run UUID to temp file names. Add `try/finally` cleanup in `dispatch_task()`.

6. **P2-1 (manifest deps):** Add `task-4` and `task-5` to task-6's `depends` list.

---

## Notes on TopologicalSorter API Usage

The plan uses `graphlib.TopologicalSorter` correctly for cycle detection: `ts.prepare()` raises `graphlib.CycleError` when cycles exist. This is the right API. The concern is not with how the API is used but with when it is used (pre-compute vs runtime) and what graph it operates on (as described in P0-2 and P1-3).

One additional note: `TopologicalSorter.add(node, *predecessors)` is the lower-level API for building incrementally, while the constructor accepts a dict. The plan uses the dict constructor (`TopologicalSorter(graph)`) which is fine. The dict must map `node -> set_of_predecessors`, not `node -> set_of_successors`. The plan's `build_graph()` description says it returns `{task_id: set(dependency_ids)}` which is the predecessor format — correct for the constructor.
