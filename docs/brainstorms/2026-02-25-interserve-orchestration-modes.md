# Brainstorm: Interserve Orchestration Modes

**Date:** 2026-02-25
**Bead:** iv-mwoi7
**Status:** Complete

## Problem

The current interserve Codex agent dispatch is all-parallel only. Tasks within a batch run concurrently via parallel `dispatch.sh` calls; sequential dependencies are handled by Claude manually grouping tasks into batches. There is no dependency DAG, no conditional dispatch, and no way to express "run A, then when A finishes, fan out B+C+D in parallel."

This limits the system in several ways:
1. **Over-serialization** — Claude groups tasks into sequential batches conservatively, losing parallelism
2. **Over-parallelization** — When Claude groups aggressively, dependent tasks run before their prerequisites finish
3. **No formal dependency tracking** — Output routing between tasks is ad-hoc (Claude reads output files and pastes context)
4. **No validation** — Circular dependencies, missing prerequisites, and impossible schedules are only caught at runtime

## Current Architecture

```
/write-plan → markdown plan file
     ↓
/executing-plans → reads plan, classifies tasks (Codex vs Claude)
     ↓
/dispatching-parallel-agents → groups into batches (max 5)
     ↓
/interserve → writes prompt files, launches parallel dispatch.sh calls
     ↓
dispatch.sh → resolves tier, runs `codex exec`, extracts .verdict sidecar
     ↓
Claude reads verdict files → pass/warn/fail → retry once on failure
```

Key limitations:
- `dispatch.sh` blocks (synchronous) — no async completion notification
- No output routing between tasks — Claude manually reads and forwards
- Batch grouping is LLM-reasoned, not validated

## Decisions

### 1. Orchestration Model: Hybrid (stages + intra-stage dependencies)

Stages provide coarse ordering barriers. Within a stage, tasks can declare dependencies on other tasks in the same stage. Tasks with no unresolved dependencies run in parallel.

```
stage-1:
  task-1: "scaffold types"          # runs alone
stage-2:
  task-2: "implement API"           # starts immediately (depends on stage-1 barrier)
  task-3: "implement CLI"           # starts immediately
  task-4: "integration tests"       depends: [task-2, task-3]  # fan-in
```

**Why hybrid over pure DAG:** Stages give a simple mental model for straightforward plans (just group by stage). Intra-stage deps handle complex cases without forcing every plan to express a full DAG. Incremental adoption — plans without deps work as staged batches.

**Why hybrid over pure stages:** Pure stages over-serialize. If task-4 only depends on task-2 and task-3, it shouldn't wait for unrelated task-5 in the same stage to finish.

### 2. Plan Format: Separate execution manifest (.exec.yaml)

Plan markdown stays human/LLM-readable. A companion `.exec.yaml` file describes the execution DAG for the orchestrator.

```
docs/plans/2026-02-25-feature-x.md         # human plan
docs/plans/2026-02-25-feature-x.exec.yaml  # machine manifest
```

**Why separate file over markdown annotations:** Schema-validatable, no fragile HTML comment parsing, orchestrator never touches markdown. The "two files" concern is moot — `/write-plan` generates both atomically.

**Why separate file over YAML frontmatter:** No duplication between frontmatter and body. Clean separation of concerns — the plan is for reasoning, the manifest is for execution.

### 3. Orchestrator Language: Python

```python
# Core scheduling in ~10 lines via graphlib
from graphlib import TopologicalSorter
ts = TopologicalSorter(graph)
ts.prepare()
while ts.is_active():
    ready = ts.get_ready()
    dispatch_parallel(ready)
    for task in completed:
        ts.done(task)
```

**Why Python over bash:**
- `graphlib.TopologicalSorter` (stdlib, Python 3.9+) handles cycle detection, incremental ready-set, done-marking
- `concurrent.futures` for clean parallel dispatch with error propagation
- Proper data structures for DAG, output routing, retry logic
- Testable with standard pytest
- Already used in Clavain (interspect, interserve MCP, flux-drive)

**Why Python over MCP extension:** Orchestration is a batch operation, not a long-lived stateful service. A script invoked by skills is simpler than adding state management to the interserve MCP server.

### 4. Execution Modes (all four)

| Mode | Behavior | When to use |
|------|----------|-------------|
| `all-parallel` | All tasks dispatched simultaneously | Fully independent tasks (current default) |
| `all-sequential` | Tasks run one at a time in plan order | Complex interdependencies, shared state |
| `dependency-driven` | Automatic scheduling from declared deps | Most plans — maximum parallelism with correctness |
| `manual-batching` | Claude groups into explicit batches | Fallback when deps are hard to express |

The orchestrator supports all four. `/write-plan` sets the default mode in the manifest. Claude can override at dispatch time.

### 5. Architecture: Skills invoke orchestrator

```
/write-plan → generates plan.md + plan.exec.yaml
     ↓
/executing-plans → validates manifest, calls orchestrate.py
     ↓
orchestrate.py → reads .exec.yaml, builds DAG, dispatches via dispatch.sh
     ↓
dispatch.sh → unchanged (runs codex exec, extracts verdict)
     ↓
orchestrate.py → routes outputs between dependent tasks, reports status
     ↓
Claude reads orchestrator summary → handles failures, proceeds
```

Skills handle *what* to build (reasoning). Python handles *when* to dispatch (scheduling).

## Execution Manifest Schema

```yaml
# .exec.yaml schema
version: 1
mode: dependency-driven          # all-parallel | all-sequential | dependency-driven | manual-batching
tier: sonnet                     # default codex model tier
max_parallel: 5                  # concurrency limit
timeout_per_task: 300            # seconds

stages:
  - name: Foundation
    tasks:
      - id: task-1
        title: "Scaffold types"
        prompt_file: null        # orchestrator generates from plan
        files: [pkg/types.go]    # file reservations (interlock)
        depends: []
        tier: null               # inherit from top-level

  - name: Implementation
    tasks:
      - id: task-2
        title: "Implement API"
        files: [pkg/api/handler.go]
        depends: [task-1]        # cross-stage dep (implicit via stage barrier)
      - id: task-3
        title: "Implement CLI"
        files: [cmd/cli/main.go]
        depends: [task-1]
      - id: task-4
        title: "Integration tests"
        files: [tests/integration_test.go]
        depends: [task-2, task-3]  # intra-stage fan-in
        tier: opus                 # override for complex task
```

## Output Routing

When task-4 depends on task-2 and task-3, the orchestrator:
1. Waits for task-2 and task-3 to complete
2. Reads their output/verdict files
3. Appends a `## Context from dependencies` section to task-4's prompt
4. Dispatches task-4 with the enriched prompt

This replaces Claude's manual "read output, paste into next prompt" pattern.

## Scope

### In scope (this sprint)
- Execution manifest schema (`.exec.yaml`)
- Python orchestrator (`os/clavain/bin/orchestrate.py`)
- Manifest generation in `/write-plan` skill
- Updated `/executing-plans` skill to invoke orchestrator
- All four execution modes
- Output routing between dependent tasks
- Basic status reporting (task started/completed/failed)

### Out of scope (future)
- Interlock file reservation integration (auto-reserve files per task)
- Live TUI progress display in Autarch
- Retry policies per task
- Conditional tasks (skip if dependency output matches pattern)
- Cross-plan dependencies (task in plan A depends on task in plan B)

## Risks

1. **dispatch.sh is synchronous** — orchestrator must run dispatches in background processes and poll for completion. Mitigation: `concurrent.futures.ProcessPoolExecutor` with subprocess calls.
2. **Output routing quality** — dependency context may be too large or too noisy for downstream tasks. Mitigation: summarize outputs (first 200 lines + verdict) rather than forwarding raw output.
3. **Plan format migration** — existing plans without `.exec.yaml` must still work. Mitigation: orchestrator falls back to all-parallel when no manifest exists.
