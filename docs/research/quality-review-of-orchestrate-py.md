# Quality Review: orchestrate.py and exec-manifest

**Scope:** `os/clavain/scripts/orchestrate.py`, `os/clavain/tests/structural/test_orchestrate.py`,
`os/clavain/schemas/exec-manifest.schema.json`, `os/clavain/schemas/exec-manifest.example.yaml`,
`os/clavain/skills/writing-plans/SKILL.md` (modified), `os/clavain/skills/executing-plans/SKILL.md` (modified).

**Language in scope:** Python. Checks applied: naming, file organisation, error handling, test coverage,
type annotations, docstring quality.

---

## Summary

The implementation is well-structured for a new orchestration primitive. The DAG logic (`graphlib`),
`DependencyDrivenScheduler`, and `dispatch_batch` ThreadPoolExecutor wiring are all sound. The
JSON schema and example YAML are clean. The tests cover the core algorithmic surface adequately.

Three issues require a fix before this is fully trustworthy. The rest are low-severity idiomatic
improvements and test gap callouts.

---

## Issues Requiring a Fix

### 1. `scheduler.is_active` is called as a property but needs to stay a property — the while loop is correct, but the `_resolve_all_sequential` path silently skips cycle detection (Medium)

`DependencyDrivenScheduler.is_active` is declared as `@property` and accessed as `scheduler.is_active`
(no call parentheses) at line 511. That is correct. This is not a bug.

However, `_resolve_all_sequential` at line 182 calls `TopologicalSorter.static_order()` directly
without first calling `.prepare()`. `static_order()` does not raise on a cyclic graph in Python's
stdlib — it will silently produce a partial or incorrect order. The cycle check in `validate_graph`
runs before `orchestrate()` dispatches, so in the main flow this is protected. But the function
itself is callable in isolation (and from tests) with no protection: any caller that invokes
`_resolve_all_sequential` on an unvalidated graph gets silent misbehaviour.

**Fix:** Add `.prepare()` + catch `CycleError` inside `_resolve_all_sequential`, or document
clearly that the caller must have already called `validate_graph`. The latter is acceptable given
the function is module-private, but the docstring should say so explicitly.

```python
def _resolve_all_sequential(graph: dict[str, set[str]]) -> list[list[str]]:
    """Each task in its own batch, topologically sorted.

    Caller must have already validated the graph via validate_graph().
    """
    ts = TopologicalSorter(graph)
    return [[tid] for tid in ts.static_order()]
```

---

### 2. `/tmp` temp files are never cleaned up (Medium — resource leak + collision risk)

`dispatch_task` writes three `/tmp` files per task:

```python
prompt_path  = f"/tmp/orchestrate-{run_id}-{task.id}-prompt.md"
output_path  = f"/tmp/orchestrate-{run_id}-{task.id}.md"
verdict_path = f"{output_path}.verdict"
```

None of these are removed after the run. For a long-running Clavain session that executes many
plans, this silently accumulates files. The `run_id` is 8 hex chars from `uuid4().hex[:8]`, which
makes cross-run collision unlikely but does not make within-run collision impossible if the same
`task.id` appears in two calls (already prevented by the duplicate-ID check, so this is fine for
the happy path).

The primary issue is the lack of cleanup. The files contain full Codex output and prompts, which
may include source code or credentials present in the project.

**Fix:** Use `tempfile.mkdtemp` for a run-scoped temp directory, and delete it at the end of
`orchestrate()` with `shutil.rmtree`, or use `tempfile.TemporaryDirectory` as a context manager.

```python
import shutil
import tempfile

# In orchestrate():
tmp_dir = tempfile.mkdtemp(prefix=f"orchestrate-{run_id}-")
try:
    # pass tmp_dir to dispatch_task instead of /tmp hard-coding
    ...
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

This also eliminates the `/tmp` hard-coding, which fails on Windows (not a current concern, but
good hygiene) and in sandboxed environments where `/tmp` may not be writable.

---

### 3. `dispatch_batch` rebuilds the full dependency graph on every batch call (Low-Medium — redundant work, potential inconsistency)

```python
# dispatch_batch, line 440
graph = build_graph(manifest)
```

`dispatch_batch` is called once per wave. Each call rebuilds the full graph from the manifest.
In the current code this is harmless because `manifest` is immutable, but it means:

- `O(tasks)` work is repeated every wave, needlessly.
- The graph used inside `dispatch_batch` for computing `dep_outputs` is a separate object from
  the one used by `DependencyDrivenScheduler` in `orchestrate()`. They will always be equal, but
  the duplication is a correctness trap: if the graph construction logic ever becomes mutable or
  stateful, the two copies will drift.

**Fix:** Accept `graph` as a parameter to `dispatch_batch`, passed in by `orchestrate()` which
already holds the authoritative graph.

```python
def dispatch_batch(
    task_ids: list[str],
    manifest: Manifest,
    graph: dict[str, set[str]],   # <-- added
    project_dir: str,
    ...
) -> dict[str, TaskResult]:
```

---

## Naming and Conventions

**Consistent with project vocabulary.** The `Task`, `TaskResult`, `Manifest` names are clear.
`_print_wave`, `_print_summary`, `_find_dispatch_sh`, `_resolve_*` all follow the established
`_private_helper` convention for module-internal functions. The `dispatch_task` / `dispatch_batch`
distinction (single vs batch) is clean.

**Minor: `dep` is used for two different types in the BFS loop.** In `mark_failed` (line 260)
and `_propagate_failure` (line 591), the loop variable `dep` iterates over dependent task IDs
(i.e., tasks that depend on the failed one), not dependency IDs. The name is backwards relative
to the graph direction being traversed. `dependent` would be clearer.

```python
# Current (confusing):
queue = list(self._dependents.get(task_id, set()))
while queue:
    dep = queue.pop()               # dep is actually a dependent, not a dep
    ...
    queue.extend(self._dependents.get(dep, set()))

# Better:
queue = list(self._dependents.get(task_id, set()))
while queue:
    dependent = queue.pop()
    ...
    queue.extend(self._dependents.get(dependent, set()))
```

This same issue appears identically in the standalone `_propagate_failure` function (line 591).
`DependencyDrivenScheduler.mark_failed` and `_propagate_failure` are duplicating the same BFS
logic — see the structural duplication note below.

---

## Python Idioms

### Unused import: `Iterator` from `typing`

```python
from typing import Iterator   # line 30 — never referenced in the file
```

`Iterator` is imported but not used anywhere. Remove it. The `from __future__ import annotations`
at line 18 is present, which is correct for the `str | None` syntax used throughout.

### `prior_stage_tasks` accumulates via plain union instead of `|=`

```python
# build_graph, line 143
prior_stage_tasks = prior_stage_tasks | set(current_stage_ids)
```

This creates a new set object every stage instead of mutating in place. Prefer `|=`:

```python
prior_stage_tasks |= set(current_stage_ids)
```

Minor, but consistent with how `deps |= prior_stage_tasks` is written two lines above.

### `_require_yaml()` calls `sys.exit(1)` directly instead of raising

`_require_yaml()` at line 78 calls `print(...); sys.exit(1)`. This is consistent with
the general pattern elsewhere in the file (`load_manifest`, `orchestrate`, `main` all use
`sys.exit`). The style is acceptable for a CLI script. However, `_require_yaml` is called from
`load_manifest`, which is a library-style function (it takes a path and returns a `Manifest`).
Library functions that call `sys.exit` are difficult to test — the `test_duplicate_task_id` test
already demonstrates the workaround needed (`with pytest.raises(SystemExit)`).

No change required for the current test surface, but future callers outside the CLI context
(e.g., if a web API ever wraps this) would be surprised by `sys.exit`. This is a low-severity
note, not a blocking issue.

### `build_prompt` constructs a `list` and `"\n".join(sections)` — correct idiom, but inconsistently applied

Some appended strings already have a trailing `\n` (e.g., `"## Context from dependencies\n"`,
`f"## Task: {task.title}\n"`), while others do not. The `"\n".join` then produces double-blank
lines in some places and single-blank lines in others. This inconsistency will silently produce
malformed prompts. Pick one convention: either strip trailing `\n` from appended strings and
rely on the `"\n".join` separator, or use `"\n\n".join` for paragraph separation. The
`textwrap.dedent` block at the end (line 348) also mixes a trailing newline implicitly.

---

## Error Handling

### `dispatch_task` swallows `TimeoutExpired` without logging stdout/stderr

```python
except subprocess.TimeoutExpired:
    return TaskResult(task_id=task.id, status="error", error="Timeout expired")
```

When a dispatch times out, `subprocess.run` with `capture_output=True` has already captured
partial stdout/stderr. The `TimeoutExpired` exception carries `.stdout` and `.stderr` attributes.
Discarding them makes post-mortem debugging impossible: the operator sees "Timeout expired" with
no context about what the Codex agent was doing.

**Fix:**

```python
except subprocess.TimeoutExpired as e:
    partial = (e.stderr or b"").decode(errors="replace")[-500:]
    return TaskResult(
        task_id=task.id,
        status="error",
        error=f"Timeout expired. Last stderr: {partial}",
    )
```

### `Exception` catch in `dispatch_task` and `dispatch_batch` loses the traceback type

Both catch sites at line 404 and line 462 do `error=str(e)`. `str(e)` for many exception types
(including `FileNotFoundError` when `dispatch.sh` is missing, or `PermissionError`) gives a
message without the exception class name, making log output ambiguous:

```
error="[Errno 2] No such file or directory: '/path/to/dispatch.sh'"
```

vs

```
error="FileNotFoundError: [Errno 2] No such file or directory: '/path/to/dispatch.sh'"
```

**Fix:** Use `f"{type(e).__name__}: {e}"` in both catch sites.

### `_propagate_failure` is structurally duplicated with `DependencyDrivenScheduler.mark_failed`

Both functions implement BFS over a reverse dependency graph to mark transitive dependents as
skipped. The only difference is that `_propagate_failure` writes to `completed: dict[str, TaskResult]`
directly (for static batch modes), while `mark_failed` accumulates `self._skip_set` (for the
dynamic scheduler). This duplication means a future bug fix would need to be applied in two places.

Acceptable for now given the small codebase, but worth a `# NOTE: mirrors DependencyDrivenScheduler.mark_failed`
comment on `_propagate_failure` so the next contributor knows to keep them in sync.

---

## Type Annotations

Overall the annotations are good. The `str | None` union syntax (enabled by `from __future__ import annotations`)
is used consistently. A few gaps:

**`_make_manifest` in the test file has no type annotations** on its helper function, which is
fine since it is a test utility, but the project has `pyright-lsp` available and the
`requires-python = ">=3.12"` in `pyproject.toml` means full Python 3.12 typing is available.
The production code's annotations are complete enough for type-checking.

**`dispatch_batch` has `# type: ignore[arg-type]` comments at lines 525 and 565** at the call
site in `orchestrate`:

```python
dispatch_batch(
    ready, manifest, project_dir, plan_path,
    completed, dispatch_sh, run_id,  # type: ignore[arg-type]
)
```

The suppression is hiding a real type issue: `dispatch_sh` is `str | None` at the call site (the
`None` case is guarded by `sys.exit` three lines above, but pyright cannot see through that control
flow). This would be eliminated by restructuring: either widen `dispatch_batch`'s `dispatch_sh`
parameter to `str | None` and assert internally, or narrow the type with a `TypeGuard` at the
check point, or simply raise `AssertionError` after the exit (which pyright understands as
unreachable). The `type: ignore` is an acceptable short-term patch but should not be left
permanently.

---

## Docstring Quality

The module docstring (lines 2-16) is excellent: it lists all four modes, shows usage examples,
and is accurate. The function-level docstrings are brief but accurate. No misleading docstrings
found.

One gap: `build_graph` documents the stage-barrier semantics in its docstring, but there is no
docstring on `validate_graph` explaining what the return value contract is (empty list = valid,
non-empty = errors). The current docstring says "Returns a list of error strings (empty = valid)"
which is fine, but it does not mention that the function does NOT raise — callers that expect an
exception will be surprised. Adding "Does not raise; caller must check the returned list" would
help.

---

## Test Coverage Gaps

The 26 tests cover the happy-path algorithmic surface well. The following gaps are worth noting
for the risk level of this code:

### Missing: no test for `dispatch_task` / `dispatch_batch` (subprocess boundary)

Zero tests exercise the subprocess dispatch path. The entire bottom half of the system
(prompt file writing, `dispatch.sh` invocation, verdict file parsing, `ThreadPoolExecutor`
wiring) is untested. This is a significant gap for a production CLI because:

- The verdict file parsing (STATUS: prefix stripping) can silently return `"error"` if
  the sidecar file has unexpected formatting.
- The fallback from verdict file to `returncode == 0` is untested.
- The `TimeoutExpired` path is untested.

Recommended: add tests with `unittest.mock.patch("subprocess.run")` that exercise the verdict
parsing, the timeout path, and the returncode fallback path. These are unit tests that do not
require a real `dispatch.sh`.

```python
from unittest.mock import patch, MagicMock

def test_dispatch_task_reads_verdict_status(tmp_path):
    task = Task(id="task-1", title="T", stage="S1")
    manifest = _make_manifest([{"name": "S1", "tasks": [{"id": "task-1", "title": "T"}]}])
    verdict = tmp_path / "out.md.verdict"

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result):
        # Write the verdict sidecar that dispatch_task reads
        verdict.write_text("STATUS: warn\n")
        # ... (needs tmp_dir restructuring to control verdict_path)
```

### Missing: `test_load_manifest` does not test missing required fields

The `test_duplicate_task_id` test is good. But there is no test for:
- Missing `id` or `title` fields (would raise `KeyError` from `t["id"]`, not a clean error)
- Non-YAML content (would raise from `yaml.safe_load`)
- Empty `stages` list (would produce a valid manifest with zero tasks — the JSON schema
  requires `minItems: 1` but `load_manifest` does not enforce this)

The schema has `"minItems": 1` on `stages`, but `load_manifest` never calls a schema validator.
A manifest with `stages: []` passes `load_manifest` and produces a `Manifest` with zero tasks,
which then produces an empty graph, which passes `validate_graph`, and `orchestrate` prints
"Orchestrating 0 tasks" and exits cleanly. This is arguably correct behaviour, but it should
be an explicit test.

### Missing: `test_load_manifest` skips on missing example file silently

```python
if not os.path.exists(example):
    pytest.skip("Example manifest not found")
```

The example file now exists at `schemas/exec-manifest.example.yaml`. The `pytest.skip` guard
is dead for current checkouts but will silently skip if someone moves or renames the file
without updating the test. Since this is a regression guard (the test verifies the example
is parseable and has correct task counts), it should use `assert os.path.exists(example)` or
build the path via `Path(__file__).parents[2]` to make the traversal explicit and auditable.

### Missing: `_propagate_failure` (static mode) not tested for transitive depth > 1

`TestDependencyDrivenScheduler` has `test_diamond_failure_propagation` which covers transitive
skips in the dynamic scheduler. But `_propagate_failure` (used in the static `all-parallel`,
`all-sequential`, `manual-batching` modes) has no direct test. If the BFS logic in
`_propagate_failure` differs from the scheduler's BFS (and currently they are equivalent but
separately implemented), a regression in one would not be caught.

### Missing: `_print_summary` "failed" count calculation

`_print_summary` at line 642 calculates:
```python
failed = total - passed
```

This conflates "warn", "error", and "skipped" all into a single "Failed/Skipped" bucket. The
label "Failed/Skipped" in the output is accurate, but the logic also double-counts `pass (dry-run)`:

```python
passed = len(by_status.get("pass", []) + by_status.get("pass (dry-run)", []))
```

`"warn"` results are not counted as passed, so a run where all tasks return `"warn"` would
report `Passed: 0, Failed/Skipped: N` even though every task completed successfully. Given
that the main dispatch loop at line 529 treats `"warn"` identically to `"pass"` (calls
`mark_done`), the summary should count `"warn"` as passed too. This is a correctness issue
in the reporting (not execution), but it will confuse operators.

**Fix:**

```python
passed = sum(
    len(v) for k, v in by_status.items()
    if k in ("pass", "warn", "pass (dry-run)")
)
```

---

## Schema Quality

`exec-manifest.schema.json` is well-formed and accurate. Two observations:

1. The `id` field pattern `"^task-[0-9]+$"` enforces a rigid naming convention. This is fine
   for the common case but the `build_graph` and scheduler code make no assumptions about the
   ID format — they treat IDs as opaque strings. Locking the schema to `task-N` prevents
   natural-language IDs (`"scaffold-types"`) that would make manifests more readable. Consider
   relaxing to `"^[a-z][a-z0-9-]+$"` (kebab-case) or removing the pattern constraint entirely.

2. The schema marks `version` as `{ "const": 1 }` but `load_manifest` reads it with
   `raw.get("version", 1)` — a missing `version` field is silently accepted. The schema would
   reject a manifest without `version` (it is in `required`), but `load_manifest` accepts it.
   This is a minor consistency gap between schema validation and programmatic loading. Since
   `--validate` invokes `load_manifest` + `validate_graph` (not jsonschema), a manifest without
   a `version` field passes `--validate`. Document this or add a programmatic version check.

---

## Skills Integration (writing-plans / executing-plans)

The new skill sections are clear and correctly describe the manifest format. Two notes:

1. `writing-plans/SKILL.md` says: "If the plan has <3 tasks or all tasks are tightly coupled,
   skip the manifest". The threshold `<3` is arbitrary and undocumented. A plan with 2 parallelisable
   tasks benefits from orchestration as much as a plan with 3. Consider changing the guidance to
   "If all tasks are tightly coupled and none can run in parallel, skip the manifest" without a
   hard count threshold.

2. `executing-plans/SKILL.md` instructs the agent to locate the orchestrator via:
   ```bash
   ORCHESTRATE=$(find ~/.claude/plugins/cache -name "orchestrate.py" | head -1)
   ```
   This is a `find` command in a skill, which the project AGENTS.md explicitly cautions against
   in favour of known paths. The canonical path is `os/clavain/scripts/orchestrate.py` relative
   to the Clavain plugin root, which `_find_dispatch_sh()` models correctly. The skill instruction
   should reference `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate.py` instead of a cache `find`.
   (This is a skill documentation issue, not a code bug, but it will produce fragile agent
   behaviour if the cache layout changes.)

---

## File Organisation

The new files are placed correctly:
- `scripts/orchestrate.py` — alongside `dispatch.sh` and other scripts. Correct.
- `tests/structural/test_orchestrate.py` — consistent with all other structural tests. Correct.
- `schemas/` — new directory, reasonable location for schema artefacts. Consistent with how
  `config/dispatch/` holds configuration artefacts.

No concerns.

---

## Prioritised Finding List

| Priority | Finding | Location |
|----------|---------|---------|
| Medium | `/tmp` files never cleaned up; prompts may contain credentials | `dispatch_task` lines 367-369 |
| Medium | `_resolve_all_sequential` has no cycle guard; docstring should say caller must validate | line 180 |
| Medium | `_print_summary` undercounts passed: `"warn"` status not treated as pass in summary | line 641 |
| Low-Medium | `dispatch_batch` rebuilds graph on every call; graph should be passed as parameter | line 440 |
| Low | `TimeoutExpired` discards captured partial stdout/stderr | line 400-403 |
| Low | `Exception` catch uses `str(e)` without class name; loses type context | lines 404-407, 462-464 |
| Low | `dep` variable name is backwards (iterating dependents, not deps) | `mark_failed`, `_propagate_failure` |
| Low | Unused `Iterator` import from `typing` | line 30 |
| Low | `prior_stage_tasks = prior_stage_tasks | set(...)` should be `|=` | line 143 |
| Low | `type: ignore[arg-type]` suppresses a real narrowing gap | lines 525, 565 |
| Low | `build_prompt` inconsistent trailing `\n` on appended strings produces irregular spacing | lines 316-354 |
| Test gap | No tests for subprocess boundary: verdict parsing, timeout, returncode fallback | `dispatch_task` |
| Test gap | No tests for `_propagate_failure` (static mode) with depth > 1 | `_propagate_failure` |
| Test gap | `_print_summary` "warn" miscounting not caught by tests | `_print_summary` |
| Test gap | `test_load_example_manifest` uses `pytest.skip` instead of hard assertion | line 416 |
| Schema | `"^task-[0-9]+$"` pattern unnecessarily rigid; code treats IDs as opaque strings | schema line 55 |
| Skill doc | `executing-plans` uses `find` to locate orchestrator instead of plugin-root path | SKILL.md Step 2C |
