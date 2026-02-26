# Create Tier 2 Beads — Agent Dispatch

**Date:** 2026-02-25
**Parent Epic:** iv-ip4zr
**Tier 1 Dependency:** iv-cl86n (Go wrapper)

## Created Beads

| # | ID | Title | Type | Priority |
|---|-----|-------|------|----------|
| 1 | **iv-lkui7** | [autarch/coldwine] Dispatch task to agent via Intercore | feature | P1 |
| 2 | **iv-aw1ss** | [autarch/bigend] Structured dispatch monitoring via Intercore | feature | P1 |
| 3 | **iv-228zx** | [autarch] Dispatch result collection and task status sync | feature | P1 |

## Dependency Graph

```
iv-ip4zr (parent epic)
├── depends on iv-lkui7 (dispatch action)
├── depends on iv-aw1ss (monitoring)
└── depends on iv-228zx (result collection)

iv-lkui7 (dispatch action)
└── depends on iv-cl86n (Go wrapper)

iv-aw1ss (monitoring)
├── depends on iv-cl86n (Go wrapper)
└── depends on iv-lkui7 (dispatch action)

iv-228zx (result collection)
├── depends on iv-cl86n (Go wrapper)
└── depends on iv-lkui7 (dispatch action)
```

## Bead Descriptions

### Bead 1: iv-lkui7 — Coldwine Task Dispatch
Add a "Dispatch" action on Coldwine tasks that calls `ic dispatch spawn` (via Go wrapper), passing task context (title, description, epic ref). Captures dispatch ID and stores it on the task row. Shows confirmation with agent type selection. Updates task status to `in_progress` on successful dispatch.

### Bead 2: iv-aw1ss — Bigend Dispatch Monitoring
Augment Bigend's agent monitoring to poll `ic dispatch status` and `ic dispatch list` (via Go wrapper) instead of relying solely on tmux session listing. Show structured info: agent name, assigned task, phase, token usage, elapsed time. Correlate dispatch IDs with Coldwine tasks. Keep tmux view as supplementary detail.

### Bead 3: iv-228zx — Result Collection and Task Sync
When a dispatch completes (detected via polling or ic events stream), capture the result artifact and update the corresponding Coldwine task status (completed/failed). Store dispatch output summary. Trigger UI notification in Bigend. This closes the loop: task → dispatch → result → task update.

## Execution Order

1. **iv-cl86n** (Tier 1 Go wrapper) — must complete first
2. **iv-lkui7** (dispatch action) — unlocks beads 2 and 3
3. **iv-aw1ss** and **iv-228zx** — can be built in parallel after bead 1

## Summary

All 3 Tier 2 beads created, all dependencies wired (each depends on Go wrapper iv-cl86n, beads 2 and 3 depend on bead 1, all 3 are children of epic iv-ip4zr). The dependency graph ensures correct build order: wrapper first, then dispatch action, then monitoring and result collection in parallel.
