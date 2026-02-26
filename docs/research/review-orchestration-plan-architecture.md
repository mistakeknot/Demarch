# Architecture Review: Interserve Orchestration Modes Plan

**Reviewed:** `docs/plans/2026-02-25-interserve-orchestration-modes.md`
**Manifest:** `docs/plans/2026-02-25-interserve-orchestration-modes.exec.yaml`
**Brainstorm:** `docs/brainstorms/2026-02-25-interserve-orchestration-modes.md`
**Date:** 2026-02-25
**Reviewer role:** Flux-drive Architecture & Design Reviewer

---

## Summary

The plan's core idea — a Python orchestrator that reads a machine-readable manifest and dispatches via the existing `dispatch.sh` — is architecturally sound. The language choice, the decision to keep `dispatch.sh` unmodified, and the separation of scheduling concern from execution concern are all correct calls. However there are three issues that should be resolved before execution begins: a manifest cross-stage dependency contradiction that will silently produce wrong schedules, a missing execution contract between the orchestrator and `dispatch.sh`, and a test placement that will fail on import. One lower-priority issue concerns the skill instruction style, and one schema detail warrants a quick fix.

---

## Components Touched

| Component | Role | Layer |
|-----------|------|-------|
| `os/clavain/scripts/orchestrate.py` | New scheduling engine | L2 script |
| `os/clavain/schemas/exec-manifest.schema.json` | New data contract | L2 schema |
| `os/clavain/schemas/exec-manifest.example.yaml` | Reference fixture | L2 schema |
| `os/clavain/skills/writing-plans/SKILL.md` | LLM instruction — manifest generation | L2 skill |
| `os/clavain/skills/executing-plans/SKILL.md` | LLM instruction — orchestrator invocation | L2 skill |
| `os/clavain/scripts/dispatch.sh` | Existing execution wrapper (unchanged) | L2 script |
| `os/clavain/tests/test_orchestrate.py` | New unit tests | test |

No L1 (Intercore/Intermute) or L3 (Autarch) components are touched. Dependency direction is correct: the new orchestrator calls down into `dispatch.sh`, not up into any plugin or kernel API.

---

## P0 Issues (Must Fix Before Execution)

### P0-1: Cross-Stage Dependency Semantics Are Contradicted in the Schema

**Location:** Plan Task 2, `build_graph()` description, and the schema `stages` definition.

The plan states:

> Cross-stage dependencies are implicit (all tasks in stage N depend on all tasks in stage N-1 completing, unless they have explicit `depends`).

But the schema defines `depends` as a list of task IDs with no restriction to the same stage. The example manifest in the brainstorm then uses `depends: [task-1]` on a task in stage-2 to express a cross-stage link:

```yaml
stages:
  - name: Foundation
    tasks:
      - id: task-1
        ...
  - name: Implementation
    tasks:
      - id: task-2
        depends: [task-1]   # cross-stage
```

This is contradictory. If `build_graph()` implements "stage barrier unless explicit depends", then `task-2` declaring `depends: [task-1]` means "depend on task-1 AND the stage barrier". That is redundant but harmless. However: for `task-3` in stage-2 that does NOT declare `depends: [task-1]`, the code would add a stage barrier dependency on ALL of stage-1, which also includes task-1. Both are fine.

The actual contradiction is more subtle: the plan says the stage barrier applies "unless they have explicit `depends`". Read literally, a task with ANY explicit `depends` loses the stage barrier. So if `task-2` has `depends: [task-1]`, it is removed from the stage barrier — fine, task-1 was the only prerequisite. But if `task-4` has `depends: [task-2, task-3]` (an intra-stage fan-in), does it ALSO get the stage barrier from stage-1? Under "unless explicit depends", no. If there were a task in stage-1 other than task-1 and task-3, task-4 would start without waiting for it, breaking the coarse ordering guarantee stages are supposed to provide.

The exec.yaml manifest shipped with this plan exposes this exact risk: task-3 in Integration stage has `depends: [task-2]`, but task-4 and task-5 also have cross-stage deps but no intra-stage barrier — in a `dependency-driven` run they could start before other Integration tasks resolve. The manifest is using `dependency-driven` mode with `max_parallel: 3`, so the scheduling confusion is live.

**Fix:** Choose one semantic and document it clearly in the plan:

Option A (recommended) — Stage barriers are additive. A task always depends on all tasks in all prior stages PLUS any explicit `depends`. The `unless` clause in the current plan description is removed. This is the safe, obvious interpretation.

Option B — Explicit `depends` fully replaces stage logic for that task. This needs a clear statement that a task with any explicit dep has opted out of automatic stage barriers.

The `build_graph()` implementation spec must then match the chosen semantic exactly. Without this fix, two implementors reading the plan will write different schedulers.

---

### P0-2: The Execution Contract with `dispatch.sh` Is Underspecified

**Location:** Plan Task 2, `dispatch_task()` description.

The plan says `dispatch_task()` calls `dispatch.sh` via `subprocess.run()` and returns a `TaskResult(task_id, status, output_path, verdict_path)`. It does not specify:

1. **The exact `dispatch.sh` invocation flags.** `dispatch.sh` requires `-o <output_file>` to write output and generate the `.verdict` sidecar. Without `-o`, no output file exists and `verdict_path` is undefined. The orchestrator must pass `-o /tmp/orchestrate-<task_id>-<timestamp>.md` and derive `verdict_path` from that by appending `.verdict`. This is implicit knowledge that an implementor reading only the plan will miss.

2. **How `subprocess.run()` is used.** The plan says `concurrent.futures.ThreadPoolExecutor` for parallelism. `dispatch.sh` calls `codex exec` which itself is a long-running subprocess. If `subprocess.run()` is used (blocking), then a single thread per task is occupied for the full execution duration — that is correct with a thread pool but must be explicit. If `subprocess.Popen()` is used instead (non-blocking), the thread pool logic changes. The plan leaves this ambiguous.

3. **`dispatch.sh` exit code semantics.** `dispatch.sh` exits with the exit code of `codex exec`. A non-zero exit does not guarantee the output file was written — it may be partial. `_extract_verdict()` in dispatch.sh writes a synthesized `.verdict` sidecar even on failure, so `verdict_path` will exist. The `TaskResult.status` field must be derived from the verdict sidecar, not from the process exit code alone, because a Codex exit code of 1 can mean "completed but found issues" (status: warn) rather than "crashed".

4. **Output file naming collision.** Multiple concurrent tasks writing to `/tmp/orchestrate-<task_id>.md` are safe only if task IDs are unique within a run. The schema enforces `"pattern": "^task-[0-9]+$"`, which is unique within a manifest but not across concurrent orchestrator invocations. If two orchestrator runs happen simultaneously (possible in multi-agent scenarios), task-1 from run A and task-1 from run B collide. The plan should add a run-ID prefix or use `tempfile.mktemp`.

**Fix before execution:** Add a "Dispatch Contract" subsection to Task 2 that specifies the exact `dispatch.sh` flags, the output naming scheme (including collision avoidance), the `subprocess.run()` vs `Popen` choice, and the exit-code / verdict-sidecar interpretation. This is a two-paragraph addition that prevents a P0 integration bug.

---

## P1 Issues (Should Fix Before Execution)

### P1-1: Test Placement Conflicts With Existing Test Runner Configuration

**Location:** Plan Task 6, `os/clavain/tests/test_orchestrate.py`.

The existing `pyproject.toml` at `os/clavain/tests/pyproject.toml` configures pytest:

```toml
[tool.pytest.ini_options]
testpaths = ["structural"]
pythonpath = ["structural", "../scripts"]
```

`testpaths = ["structural"]` means `uv run pytest` (or `python3 -m pytest`) invoked from `tests/` will only discover `structural/`. A file placed at `tests/test_orchestrate.py` will not be discovered by the default test run.

The plan's Task 6 Step 2 says:

```bash
cd os/clavain && python3 -m pytest tests/test_orchestrate.py -v
```

This explicit path invocation will work, but it bypasses the project's test runner convention. More importantly, the import line:

```python
from orchestrate import load_manifest, build_graph, validate_graph, resolve_execution_order
```

This import works only if `../scripts` is on `sys.path`. The `pythonpath` entry in `pyproject.toml` adds `../scripts` relative to `tests/`, so it would resolve to `os/clavain/scripts` — which is correct. However this only applies when pytest is invoked from `tests/` with that `pyproject.toml`. When invoked as `python3 -m pytest tests/test_orchestrate.py` from `os/clavain/`, the `pythonpath` in `tests/pyproject.toml` may or may not apply depending on how pytest locates its config.

The clean fix is one of:
- Place the test at `os/clavain/tests/structural/test_orchestrate.py` (matches existing convention, auto-discovered).
- OR add `"."` to `testpaths` in `pyproject.toml` — but this would discover all files at the top level of `tests/`, potentially mixing unit tests with structural tests in the run output.

The recommended fix: place the test in `tests/structural/test_orchestrate.py`. The existing `pythonpath = ["structural", "../scripts"]` already exposes `../scripts`, so `from orchestrate import ...` will resolve correctly.

---

### P1-2: The `--prompt-file` Mechanism Bypasses `dispatch.sh` Template Assembly

**Location:** Plan Task 2, `dispatch_task()` and Task 3, output routing.

The plan writes a prompt to a temp file and passes it via `--prompt-file`. This is correct. However `dispatch.sh` has a `--template` flag for assembling structured prompts from KEY: section templates. The orchestrator's dependency context injection (Task 3) prepends a `## Context from dependencies` section to the prompt file before calling `dispatch.sh`. This means the orchestrator is doing template assembly work in Python that `dispatch.sh` already supports structurally — but with a different mechanism.

This is not a bug, but it creates two parallel prompt-assembly systems: the `--template` mechanism in `dispatch.sh` and the Python-side prefix injection in the orchestrator. If downstream agents generate plans that use the `--template` flag convention (KEY: sections with `{{PLACEHOLDERS}}`), the orchestrator's prefix injection would interfere by adding free-form markdown before a structured template prompt. The two systems are additive-incompatible.

**Fix:** Add an explicit note in Task 3 that `dispatch_task()` must check whether the prompt content is a template-format prompt (starts with `KEY:` sections) and, if so, inject dependency context using a KEY: section (e.g., `CONTEXT:`) rather than a raw markdown prefix. Alternatively, document that `orchestrate.py` always constructs plain-text prompts and never uses the `--template` flag — and that these two dispatch paths remain mutually exclusive.

---

## Lower Priority Issues

### L1: Skill Instruction Style — Bash Pseudocode in SKILL.md Is Misleading

**Location:** Plan Task 5, Step 1.

The plan adds this to `executing-plans/SKILL.md`:

```bash
PLAN_PATH="$1"  # the plan file
MANIFEST="${PLAN_PATH%.md}.exec.yaml"
if [ -f "$MANIFEST" ]; then
    echo "ORCHESTRATED_MODE"
fi
```

Skills are LLM instructions, not shell scripts. The agent reading this skill never runs this code — it reads the logic and then performs the check itself using Bash tool calls. The pseudocode convention exists in the existing skill already (the existing Step 2 check uses the same pattern), so this is consistent with the current style. However it creates a subtle hazard: the "PLAN_PATH=$1" convention implies the skill receives a positional argument, which it does not. The agent must infer the plan path from context. This is not a new problem introduced by this plan, but the new Step adds another instance.

The improvement would be to write the Step 1 check as plain English: "Check whether a `.exec.yaml` manifest exists alongside the plan file (replace `.md` extension with `.exec.yaml`). If it exists, use Orchestrated Mode." The existing pseudocode in the skill is a legacy style; the new step should not deepen the pattern.

This is worth a quick edit but is not a blocker.

---

### L2: Schema — `tier` Field Uses Different Vocabulary Than `dispatch.sh`

**Location:** Schema, `tier` enum: `["fast", "deep"]`.

`dispatch.sh` accepts `--tier fast|deep`. The schema matches. But the brainstorm example shows `tier: sonnet` and `tier: opus` — which are model-name values, not tier names. The schema rejects these (`enum: ["fast", "deep"]` only). The brainstorm's example YAML is therefore invalid against the schema.

This is a documentation inconsistency rather than a code defect, but it will confuse the implementing agent. The plan's schema definition (fast/deep) is correct. The brainstorm's model-name examples (sonnet/opus) are wrong. A quick note in Task 1 that model names are not valid tier values (they go in `--model` override, not `--tier`) prevents the implementor from adding a third path.

---

### L3: `max_parallel` Maximum of 10 May Conflict With Resource Limits

**Location:** Schema, `max_parallel: { minimum: 1, maximum: 10 }`.

The existing interserve skill caps parallel dispatch at 5 agents per batch: "Max 5 agents per batch (to avoid overwhelming resources)". The schema allows up to 10. The orchestrator will honor whatever value the manifest declares. A manifest with `max_parallel: 8` will dispatch 8 concurrent `codex exec` processes — each of which runs a full AI agent with its own context window and compute allocation.

This is a policy question rather than a correctness issue. But it should be documented: either align the schema maximum with the existing 5-agent guideline, or document that the orchestrator permits higher concurrency than the manual skill recommends and that users should understand the resource implications.

The current manifest uses `max_parallel: 3`, which is conservative and fine.

---

## Pattern Analysis

### What the Plan Gets Right

**Unchanged dispatch.sh.** The plan explicitly keeps `dispatch.sh` unmodified. This is the correct call. `dispatch.sh` is 711 lines with JSONL streaming, interband sideband, verdict extraction, and state management. Touching it for this feature would be scope creep and integration risk.

**Python for scheduling, bash for execution.** `graphlib.TopologicalSorter` is exactly the right tool for this — 10 lines to get cycle detection, incremental ready-set, and done-marking. The plan correctly identifies that Bash cannot express this cleanly. The boundary is well-drawn: Python does scheduling, `dispatch.sh` does execution.

**Separate `.exec.yaml` file.** Keeping the machine manifest separate from the human plan markdown is correct. It avoids fragile HTML comment parsing, allows schema validation, and keeps `dispatch.sh`'s `--prompt-file` interface clean. The concern about "two files" is addressed in the brainstorm and the answer (atomic generation by `/write-plan`) is sound.

**Fallback chain is additive.** The plan adds ORCHESTRATED_MODE as a new first check before the existing INTERSERVE_ACTIVE / DIRECT_MODE split. Existing plans without `.exec.yaml` are unaffected. This is the minimum viable integration point.

**Test class structure is complete.** The `TestBuildGraph`, `TestValidateGraph`, `TestResolveExecutionOrder`, and `TestOutputRouting` classes cover the four independently testable concerns. This is a good decomposition.

### Potential Anti-Pattern: God Function Risk in `orchestrate()`

The main `orchestrate()` function as described does: load, validate, resolve order, dispatch batches, collect results, route outputs, report summary. That is six distinct responsibilities in one function. For a single-file script this is acceptable, but if the orchestrator grows (retry policies, interlock reservation, conditional tasks from the "out of scope" list), the function will become hard to test.

The plan should clarify that `orchestrate()` is a thin coordinator that calls the other named functions — not that it inlines their logic. The named functions (`load_manifest`, `build_graph`, `validate_graph`, etc.) are already the right decomposition. As long as `orchestrate()` calls them as black boxes rather than inlining their implementation, this is fine. No change needed now, but worth flagging for the implementor.

---

## Manifest Self-Review (The `.exec.yaml` for This Plan)

The submitted manifest `docs/plans/2026-02-25-interserve-orchestration-modes.exec.yaml` is reviewed here because it will be consumed by the orchestrator it creates, making it a self-referential test case.

**Issue:** task-3 (`Output routing`) and task-5 (`Update /executing-plans`) both list `os/clavain/scripts/orchestrate.py` as their target file, and task-3 depends on task-2, while task-5 depends on task-2. In `dependency-driven` mode with `max_parallel: 3`, task-3 and task-5 could run concurrently after task-2 completes. Task-3 modifies `orchestrate.py` (adds `summarize_output`, changes `dispatch_task`). Task-5 modifies `skills/executing-plans/SKILL.md` — no overlap there. However task-3 and task-6 both list `orchestrate.py` modifications, and task-6 depends on `[task-2, task-3]`. That sequencing is correct.

The only file conflict is that task-3 and task-2 both target `os/clavain/scripts/orchestrate.py`. Task-3 depends on task-2, so they are sequential — no conflict.

**Cross-stage dependency semantics (connects to P0-1):** Under `dependency-driven` mode, the stage barrier between "Schema & Core" and "Integration" must be enforced. task-4 (`/write-plan update`) has `depends: [task-1]` (cross-stage). If the implementor uses the "explicit depends removes stage barrier" interpretation, task-4 would wait only for task-1 and could start before task-2 finishes — which is safe since they touch different files (`SKILL.md` vs `orchestrate.py`). Under the "stage barrier is additive" interpretation, task-4 would wait for both task-1 AND task-2 before starting. Both are functionally correct for this specific manifest, but illustrate why the P0-1 semantic must be resolved: a different manifest could be broken by either interpretation.

---

## Required Changes Before Execution

| Priority | Change | Location |
|----------|--------|----------|
| P0-1 | Resolve cross-stage dependency semantic: additive barrier vs opt-out. Document chosen behavior in `build_graph()` spec. | Plan Task 2 |
| P0-2 | Add Dispatch Contract subsection: exact `dispatch.sh` flags, output file naming (with run-ID prefix), `subprocess.run` vs `Popen`, and exit-code/verdict interpretation. | Plan Task 2 |
| P1-1 | Move test to `tests/structural/test_orchestrate.py` to match existing test runner configuration and ensure auto-discovery. | Plan Task 6 |
| P1-2 | Document that prompt prefix injection and `--template` flag are mutually exclusive dispatch paths. | Plan Task 3 |

The P0 issues are specification gaps that will cause implementors to make different choices. The P1 issues are integration mismatches with existing infrastructure that will surface as test runner confusion or subtle dispatch incompatibilities. All four are low-effort fixes to the plan document — none require architecture changes.
