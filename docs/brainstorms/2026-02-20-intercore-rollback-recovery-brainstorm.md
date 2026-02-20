# [Intercore] E6: Rollback and Recovery — Three-Layer Revert
**Bead:** iv-0k8s
**Phase:** brainstorm (as of 2026-02-20T16:55:15Z)

**Date:** 2026-02-20
**Status:** Brainstorm complete
**Epic:** E6 in intercore autonomy ladder (P1)

## What We're Building

A rollback and recovery system for intercore that lets sprints rewind to earlier phases without losing history. Two layers in scope:

1. **Workflow state rollback** — Rewind a run's phase pointer backward in its phase chain, marking intervening transitions and artifacts as `rolled_back`. Active dispatches in rolled-back phases are marked cancelled. Gates re-evaluate on re-advance.

2. **Code rollback** — Query dispatch metadata to produce a structured report of which commits were produced by which dispatches in which phases. The kernel outputs data; the OS/human layer decides how to execute git reverts.

A third layer (discovery/backlog rollback — closing beads from bad signal sources) is deferred until E5 (Discovery) is built.

## Why This Approach

### The problem
Today, phase transitions are **forward-only**. If a sprint reaches `executing` and something goes wrong (bad plan, broken code, wrong approach), the only options are: cancel the entire run and start over, or manually hack state. There's no structured way to say "go back to `planned` and try again."

### The principle
**Rollback is not undo.** Rollback resets state to enable re-execution. It does not erase history. All events, dispatches, and artifacts from the rolled-back period are preserved with `rolled_back` status. This maintains the full audit trail — you can always see what happened and why it was rolled back.

### Why two layers
- **Workflow rollback** (Layer 1) solves the common case: sprint went sideways, rewind and retry.
- **Code rollback** (Layer 2) addresses the harder problem: code was committed from dispatches, now we need to know what to revert. The kernel stays git-agnostic — it provides the query, not the git commands.

## Key Decisions

### 1. Scope: Workflow + Code (defer discovery)
Discovery rollback depends on E5 which doesn't exist. No stubs — clean deferral.

### 2. Dispatch cancellation: Mark only
Set dispatch status to `cancelled` in DB. Don't signal PIDs. This follows intercore's "mechanism not policy" philosophy — the kernel records facts, the OS layer enforces behavior. Works for local processes, remote agents, or Codex alike.

### 3. Code rollback: Query only
`ic run rollback --layer=code` outputs structured JSON listing dispatch IDs, phases, commit SHAs, and file paths. The kernel doesn't generate git commands — it stays VCS-agnostic. Human or OS layer uses the data to construct revert sequences.

### 4. Gates re-evaluate after rollback
After rolling back to phase X, the next `advance` triggers normal gate checks. No grace period. This ensures quality controls aren't bypassed during recovery. The existing `ic gate override` escape hatch remains available.

### 5. Rollback is authoritative (no optimistic concurrency)
Normal `advance` uses `WHERE phase = ?` for concurrency safety. Rollback uses a direct UPDATE — it's an intentional, authoritative operation. If two sessions try to rollback simultaneously, last-writer-wins is acceptable (both intend to rollback).

### 6. No event/artifact deletion
Rolled-back events stay in `phase_events` with their original data. A new `rollback` event records the rewind. Artifacts get a `rolled_back` status but aren't deleted. Full history is always queryable.

## Architecture

### CLI Surface

```
ic run rollback <run_id> --to-phase=<phase> [--reason=<text>]
  → Rewinds run to target phase. Marks intervening artifacts/dispatches.
  → Returns: JSON with rolled_back_phases, cancelled_dispatches, marked_artifacts

ic run rollback <run_id> --layer=code [--phase=<phase>] [--format=json|text]
  → Queries dispatch metadata for code-producing dispatches.
  → Returns: JSON with dispatch_id, phase, commit_shas, file_paths
  → If --phase given, scopes to that phase only

ic run rollback <run_id> --dry-run --to-phase=<phase>
  → Shows what WOULD be rolled back without doing it
```

### Schema Changes (v8)

- `run_artifacts`: Add `status TEXT DEFAULT 'active'` column (values: `active`, `rolled_back`)
- `phase_events`: No schema change needed — `event_type` is TEXT, just add `rollback` as a new value
- Consider: `phase_events.rollback_target` column to record what phase the rollback targeted (or encode in `reason` JSON)

### Go Implementation

**New in `internal/phase/`:**
- `Rollback(ctx, runID, targetPhase, reason)` in machine.go — orchestrates the rollback
- `store.RollbackPhase(ctx, runID, targetPhase)` — direct UPDATE without optimistic concurrency
- `store.PhasesAfter(ctx, runID, phase)` — returns phases between target and current (for artifact/dispatch marking)

**New in `internal/dispatch/`:**
- `CancelByPhases(ctx, runID, phases)` — marks dispatches in specified phases as cancelled

**New in `internal/runtrack/`:**
- `MarkArtifactsRolledBack(ctx, runID, phases)` — sets artifact status
- `CancelAgentsByPhases(ctx, runID, phases)` — marks agents as failed

**New event type constants:**
- `EventRollback = "rollback"` — recorded in phase_events
- `EventDispatchCancelled = "dispatch_cancelled"` — recorded in dispatch_events

### Bash Wrapper

```bash
intercore_run_rollback() {
    local run_id="$1" target_phase="$2" reason="${3:-}"
    ic run rollback "$run_id" --to-phase="$target_phase" ${reason:+--reason="$reason"}
}

intercore_run_code_rollback() {
    local run_id="$1" phase="${2:-}"
    ic run rollback "$run_id" --layer=code ${phase:+--phase="$phase"} --format=json
}
```

### Clavain Integration

```bash
sprint_rollback() {
    local sprint_id="$1" target_phase="$2" reason="${3:-}"
    intercore_run_rollback "$sprint_id" "$target_phase" "$reason"
    # Update beads phase tracking
    phase_set "$sprint_id" "$target_phase" "Rolled back: $reason"
    # Clear checkpoint (force re-evaluation)
    checkpoint_clear
}
```

## Open Questions

1. **Should rollback emit an event bus notification?** — Probably yes, so `ic events tail` consumers (like auto-compound) can react to rollbacks.
2. **Max rollback depth?** — Can you roll back from `done` to `brainstorm`? Probably yes, since the run status would revert from `completed` to `active`. But this is unusual and worth flagging.
3. **Artifact content preservation** — Artifacts have `content_hash` but not the actual content. After code rollback, artifact files may no longer exist on disk. Is the metadata sufficient, or should we snapshot content?

## Original Intent (Full E6 Vision)

The complete E6 vision includes three layers. This brainstorm scopes to two:

| Layer | Trigger | E6 Scope |
|-------|---------|----------|
| Workflow state | Sprint goes sideways, need to retry from earlier phase | Yes |
| Code | Dispatches produced bad commits, need revert plan | Yes |
| Discovery/backlog | Bad signal source polluted the backlog | Deferred (needs E5) |

When E5 lands, discovery rollback should follow the same pattern: query metadata, propose changes, let human/OS execute.
