# Interserve Orchestration Modes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Add a Python orchestrator that reads execution manifests (.exec.yaml) and dispatches Codex agents with proper dependency ordering — supporting all-parallel, all-sequential, dependency-driven, and manual-batching modes.

**Architecture:** New Python script `os/clavain/scripts/orchestrate.py` reads `.exec.yaml` manifests, uses `graphlib.TopologicalSorter` to resolve task dependencies, and dispatches via existing `dispatch.sh`. Skills updated to generate manifests and invoke the orchestrator.

**Tech Stack:** Python 3.9+ (graphlib, concurrent.futures, PyYAML), existing dispatch.sh, YAML execution manifests.

---

## Task 1: Execution Manifest Schema

**Files:**
- Create: `os/clavain/schemas/exec-manifest.schema.json`
- Create: `os/clavain/schemas/exec-manifest.example.yaml`

**Step 1: Write the JSON Schema**

Create `os/clavain/schemas/exec-manifest.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Execution Manifest",
  "description": "Machine-readable execution plan for orchestrate.py",
  "type": "object",
  "required": ["version", "mode", "stages"],
  "properties": {
    "version": { "const": 1 },
    "mode": {
      "enum": ["all-parallel", "all-sequential", "dependency-driven", "manual-batching"]
    },
    "tier": {
      "enum": ["fast", "deep"],
      "default": "deep"
    },
    "max_parallel": {
      "type": "integer", "minimum": 1, "maximum": 10, "default": 5
    },
    "timeout_per_task": {
      "type": "integer", "minimum": 30, "maximum": 1800, "default": 300
    },
    "stages": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["name", "tasks"],
        "properties": {
          "name": { "type": "string" },
          "tasks": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["id", "title"],
              "properties": {
                "id": { "type": "string", "pattern": "^task-[0-9]+$" },
                "title": { "type": "string" },
                "files": { "type": "array", "items": { "type": "string" } },
                "depends": { "type": "array", "items": { "type": "string" } },
                "tier": { "enum": ["fast", "deep"] },
                "prompt_hint": { "type": "string" }
              }
            }
          }
        }
      }
    }
  }
}
```

**Step 2: Write an example manifest**

Create `os/clavain/schemas/exec-manifest.example.yaml` showing a realistic 4-task plan with stages and intra-stage dependencies.

**Step 3: Verify schema parses**

Run: `python3 -c "import json; json.load(open('os/clavain/schemas/exec-manifest.schema.json'))"`
Expected: No error

---

## Task 2: Python Orchestrator — Core Scheduling Engine

**Files:**
- Create: `os/clavain/scripts/orchestrate.py`

This is the core of the feature. The orchestrator:
1. Reads `.exec.yaml` manifest
2. Validates the DAG (cycle detection, missing dependencies)
3. Resolves execution order based on mode
4. Dispatches tasks via `dispatch.sh` with proper parallelism
5. Waits for completion and collects results
6. Routes outputs from completed tasks to dependents
7. Reports summary (pass/fail/skip per task)

**Step 1: Write the orchestrator**

Create `os/clavain/scripts/orchestrate.py`:

```python
#!/usr/bin/env python3
"""orchestrate.py — DAG-based Codex agent dispatch.

Reads an execution manifest (.exec.yaml) and dispatches tasks via dispatch.sh
with proper dependency ordering.

Usage:
    python3 orchestrate.py <manifest.exec.yaml> [--plan <plan.md>] [--project-dir <dir>]
    python3 orchestrate.py --validate <manifest.exec.yaml>
    python3 orchestrate.py --dry-run <manifest.exec.yaml>
"""
```

Core components:

1. **`load_manifest(path)`** — Parse YAML, validate against schema (warn but don't fail if jsonschema not installed), return typed dict.

2. **`build_graph(manifest)`** — Build `{task_id: set(dependency_ids)}` from stages. **Stage barriers are additive:** every task implicitly depends on ALL tasks from ALL prior stages, PLUS any explicit `depends` entries. Explicit `depends` never removes the stage barrier — it only adds intra-stage edges. Return the graph dict.

3. **`validate_graph(graph, manifest)`** — Check for cycles via `TopologicalSorter`, missing dependency references, self-dependencies. Print errors and exit 1 on failure.

4. **`resolve_execution_order(graph, mode, manifest)`** — Based on mode. For `dependency-driven`, this function does NOT pre-compute static batches — it returns a generator/iterator that yields ready tasks dynamically using `TopologicalSorter`:
   - `all-parallel`: ignore deps, return all tasks as one batch
   - `all-sequential`: return each task as its own batch in topological order
   - `dependency-driven`: use `TopologicalSorter.get_ready()` / `.done()` loop for maximum parallelism — the caller drives the loop, marking tasks done as they complete, and requesting the next ready set
   - `manual-batching`: group by stage, run stages sequentially. **Within a stage, respect intra-stage `depends`** — use TopologicalSorter on the intra-stage subgraph so dependent tasks within a stage are properly ordered

5. **`dispatch_task(task, manifest, project_dir, plan_path, dep_outputs)`** — Write prompt file, enriching with dependency context from `dep_outputs`. Call `dispatch.sh` via `subprocess.run()` (blocking — one thread per task in the pool). Return `TaskResult(task_id, status, output_path, verdict_path)`.

   **Dispatch contract with `dispatch.sh`:**
   - Generate a unique run ID per orchestrator invocation: `run_id = uuid4().hex[:8]`
   - Output path: `/tmp/orchestrate-{run_id}-{task_id}.md` (avoids collision across concurrent runs)
   - Required flags: `-C <project_dir>`, `-o <output_path>`, `--tier <task.tier or manifest.tier>`, `--prompt-file <prompt_path>`, `-s workspace-write`
   - When interserve mode is active: add `CLAVAIN_DISPATCH_PROFILE=interserve` env var
   - Verdict sidecar: `dispatch.sh` always writes `<output_path>.verdict` (even on failure, it synthesizes one). Read status from verdict, NOT from process exit code. Exit code 1 can mean "completed with issues" (verdict: warn), not just "crashed".
   - The orchestrator always uses `--prompt-file` with plain-text prompts. It does NOT use `dispatch.sh`'s `--template` flag. These are mutually exclusive dispatch paths.

6. **`dispatch_batch(tasks, ...)`** — Use `concurrent.futures.ThreadPoolExecutor` to dispatch tasks in parallel (up to `max_parallel`). **Collect ALL results even if some fail:** use `as_completed()` iterator with individual `try/except` per future, not a list comprehension that stops on first exception. Failed tasks are recorded with error status, not dropped.

7. **`orchestrate(manifest_path, plan_path, project_dir, dry_run)`** — Main loop using dynamic scheduling:
   ```
   load → validate → for dependency-driven: TopologicalSorter loop (get_ready → dispatch_batch → mark done → get_ready...)
   ```
   **Failure propagation:** When a task fails, all tasks that transitively depend on it are marked `skipped` (not dispatched). The orchestrator computes the transitive closure of dependents and removes them from the ready set. This prevents dispatching tasks whose prerequisites failed.

8. **`main()`** — argparse CLI: `<manifest>`, `--plan`, `--project-dir`, `--validate`, `--dry-run`, `--mode` (override manifest mode).

**Step 2: Make executable**

Run: `chmod +x os/clavain/scripts/orchestrate.py`

**Step 3: Verify basic execution**

Run: `python3 os/clavain/scripts/orchestrate.py --validate os/clavain/schemas/exec-manifest.example.yaml`
Expected: "Manifest valid: 4 tasks, 0 cycles, mode: dependency-driven"

Run: `python3 os/clavain/scripts/orchestrate.py --dry-run os/clavain/schemas/exec-manifest.example.yaml`
Expected: Prints execution plan (batches with task IDs) without dispatching

---

## Task 3: Output Routing Between Dependent Tasks

**Files:**
- Modify: `os/clavain/scripts/orchestrate.py` (the dispatch_task and prompt generation functions)

**Step 1: Implement output summarization**

Add a `summarize_output(output_path, verdict_path, max_lines=200)` function that:
1. Reads the `.verdict` sidecar if it exists (7 lines — STATUS, FILES_CHANGED, etc.)
2. Reads the first `max_lines` of the full output file
3. Returns a structured summary string:
   ```
   ## Context from task-2: "Implement API"
   **Status:** pass
   **Files changed:** pkg/api/handler.go, pkg/api/routes.go
   **Summary:** [first 5 lines of output or verdict summary]
   ```

**Step 2: Enrich dependent task prompts**

In `dispatch_task()`, when `dep_outputs` is non-empty:
1. For each dependency, call `summarize_output()` to get its summary
2. Prepend a `## Context from dependencies` section to the task's prompt file
3. Include the summaries so the downstream agent knows what was built

**Note:** The orchestrator always constructs plain-text prompts with `--prompt-file`. It does NOT use `dispatch.sh`'s `--template` flag (which uses KEY: section format with `{{PLACEHOLDERS}}`). These are mutually exclusive dispatch paths. If a task prompt starts with `KEY:` sections, it was not generated by the orchestrator.

**Step 3: Test with dry-run**

Run: `python3 os/clavain/scripts/orchestrate.py --dry-run os/clavain/schemas/exec-manifest.example.yaml`
Expected: Dry-run output shows which tasks would receive dependency context and from which predecessors

---

## Task 4: Update `/write-plan` to Generate Manifests

**Files:**
- Modify: `os/clavain/skills/writing-plans/SKILL.md`

**Step 1: Add manifest generation instructions**

After the "Save plans to" section, add instructions for generating the companion `.exec.yaml`:

After saving the plan markdown, also generate a companion execution manifest at `docs/plans/YYYY-MM-DD-<feature-name>.exec.yaml`.

The manifest should:
1. Set `version: 1`
2. Choose `mode` based on plan analysis:
   - 3+ independent tasks with clear boundaries → `dependency-driven`
   - All tasks share state or files → `all-sequential`
   - Simple independent tasks, no deps → `all-parallel`
3. Group tasks into stages (natural groupings from the plan)
4. Declare `depends` for tasks that need output from earlier tasks
5. List `files` for each task (from the plan's "Files:" sections)
6. Set `tier: deep` by default (override to `fast` for verification-only tasks)

**Step 2: Add manifest template to the skill**

Include a YAML template that the skill can follow when generating manifests.

**Step 3: Update execution handoff**

Update the AskUserQuestion in "Execution Handoff" to mention the manifest:
- If `.exec.yaml` was generated, include it in the execution recommendation
- Add a fourth option: "Orchestrated Delegation (Recommended)" when a manifest exists with dependency-driven mode

---

## Task 5: Update `/executing-plans` to Invoke Orchestrator

**Files:**
- Modify: `os/clavain/skills/executing-plans/SKILL.md`

**Step 1: Add manifest detection**

In Step 2 (Check Execution Mode), add a third check before the interserve/direct mode split:

Check whether a `.exec.yaml` manifest exists alongside the plan file (replace the `.md` extension with `.exec.yaml`). If it exists, use Orchestrated Mode. This check takes priority over both interserve flag and direct mode.

**Step 2: Add Step 2C: Orchestrated Execution**

When `ORCHESTRATED_MODE` is detected:

1. Validate the manifest: `python3 "$ORCHESTRATE" --validate "$MANIFEST"`
2. Show the execution plan: `python3 "$ORCHESTRATE" --dry-run "$MANIFEST"`
3. Ask for approval via AskUserQuestion
4. Execute: `python3 "$ORCHESTRATE" "$MANIFEST" --plan "$PLAN_PATH" --project-dir "$(pwd)"`
5. Read the orchestrator's summary output
6. If any tasks failed: offer retry, manual execution, or skip
7. Proceed to Step 3 (Report) as normal

**Step 3: Update the skill's fallback chain**

```
ORCHESTRATED_MODE (manifest exists) → invoke orchestrate.py
  ↓ (no manifest)
INTERSERVE_ACTIVE (flag exists) → current parallel dispatch via interserve skill
  ↓ (no flag)
DIRECT_MODE → current direct execution
```

**Step 4: Verify backward compatibility**

Existing plans without `.exec.yaml` must continue to work exactly as before — the manifest check is additive, not breaking.

---

## Task 6: Tests

**Files:**
- Create: `os/clavain/tests/structural/test_orchestrate.py`

**Step 1: Write unit tests for the orchestrator**

```python
import pytest
from orchestrate import load_manifest, build_graph, validate_graph, resolve_execution_order

class TestBuildGraph:
    def test_simple_linear(self): ...      # task-1 → task-2 → task-3
    def test_fan_out(self): ...            # task-1 → [task-2, task-3]
    def test_fan_in(self): ...             # [task-2, task-3] → task-4
    def test_diamond(self): ...            # task-1 → [task-2, task-3] → task-4
    def test_cross_stage_implicit(self): ...  # stage barrier creates implicit deps

class TestValidateGraph:
    def test_valid_graph(self): ...
    def test_cycle_detected(self): ...
    def test_missing_dependency(self): ...
    def test_self_dependency(self): ...

class TestResolveExecutionOrder:
    def test_all_parallel_ignores_deps(self): ...
    def test_all_sequential_one_per_batch(self): ...
    def test_dependency_driven_max_parallelism(self): ...
    def test_manual_batching_groups_by_stage(self): ...

class TestOutputRouting:
    def test_summarize_with_verdict(self): ...
    def test_summarize_without_verdict(self): ...
    def test_prompt_enrichment(self): ...
```

**Step 2: Run tests**

Run: `cd os/clavain/tests && uv run pytest structural/test_orchestrate.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add os/clavain/schemas/ os/clavain/scripts/orchestrate.py os/clavain/tests/structural/test_orchestrate.py
git add os/clavain/skills/writing-plans/SKILL.md os/clavain/skills/executing-plans/SKILL.md
git commit -m "feat: add orchestrate.py with DAG-based Codex dispatch and execution manifests"
```
