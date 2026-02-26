# PRD: Interserve Orchestration Modes

**Date:** 2026-02-25
**Bead:** iv-mwoi7
**Source:** [Brainstorm](../brainstorms/2026-02-25-interserve-orchestration-modes.md)

## Problem Statement

Interserve's Codex agent dispatch only supports all-parallel execution. This forces Claude to manually batch tasks sequentially (losing parallelism) or dispatch everything at once (risking dependency violations). There is no formal dependency tracking, no output routing between tasks, and no validation of execution order.

## Solution

A Python-based orchestrator that reads a structured execution manifest (`.exec.yaml`) and dispatches Codex agents according to a hybrid stage + dependency model. Four execution modes (all-parallel, all-sequential, dependency-driven, manual-batching) cover the full spectrum from simple to complex plans.

## Features

### F1: Execution Manifest Schema
Define the `.exec.yaml` format: version, mode, stages, tasks with dependencies, tier overrides, concurrency limits. Schema must be backward-compatible (plans without manifests default to all-parallel).

### F2: Python Orchestrator (`orchestrate.py`)
Core scheduling engine using `graphlib.TopologicalSorter`. Reads manifest, builds DAG, dispatches ready tasks via `dispatch.sh`, waits for completion, routes outputs to dependents. Supports all four execution modes.

### F3: Output Routing
When a task depends on completed tasks, the orchestrator enriches its prompt with summarized outputs from dependencies. Replaces Claude's manual "read output, paste context" pattern.

### F4: `/write-plan` Manifest Generation
Update the writing-plans skill to generate `.exec.yaml` alongside the markdown plan. Task IDs, dependencies, file lists, and tier overrides are derived from the plan structure.

### F5: `/executing-plans` Orchestrator Integration
Update the executing-plans skill to detect `.exec.yaml` and invoke `orchestrate.py` instead of manual dispatch. Falls back to current behavior when no manifest exists.

## Success Criteria

- Plans with declared dependencies execute in correct order
- Independent tasks within a stage run in parallel
- Fan-in works: task waits for all dependencies before starting
- Output from completed tasks is available to dependent tasks
- Existing plans without `.exec.yaml` continue to work (all-parallel)
- Cycle detection rejects invalid dependency graphs
- All four modes work: all-parallel, all-sequential, dependency-driven, manual-batching

## Non-Goals

- Interlock file reservation integration (future)
- Live TUI progress in Autarch (future)
- Per-task retry policies (future)
- Conditional task execution (future)
