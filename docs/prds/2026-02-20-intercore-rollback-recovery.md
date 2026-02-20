# PRD: Intercore Rollback and Recovery (E6)
**Bead:** iv-9ofb
**Brainstorm:** docs/brainstorms/2026-02-20-intercore-rollback-recovery-brainstorm.md

## Problem

Intercore phase transitions are forward-only. When a sprint goes wrong mid-execution, the only options are cancelling the entire run or manually hacking database state. There's no structured way to rewind a run to an earlier phase and retry.

## Solution

Add a `rollback` subcommand to `ic run` that rewinds a run's phase pointer backward in its chain, marks intervening artifacts and dispatches as `rolled_back`, and preserves the full audit trail. Additionally, provide a code rollback query that reports which commits were produced by which dispatches, enabling the OS/human layer to construct git revert sequences.

## Features

### F1: Schema Migration (v7 → v8)
**What:** Add `status` column to `run_artifacts` table and bump schema to v8.
**Acceptance criteria:**
- [ ] `run_artifacts` has `status TEXT DEFAULT 'active'` column
- [ ] `db.Migrate()` handles v7→v8 upgrade idempotently (duplicate column guard)
- [ ] Schema version constant updated to 8
- [ ] Existing artifacts default to `active` status
- [ ] `ic health` reports schema v8

### F2: Workflow State Rollback
**What:** `ic run rollback <id> --to-phase=<phase>` rewinds a run's phase to a prior position in its chain, recording a `rollback` event.
**Acceptance criteria:**
- [ ] Validates target phase exists in run's chain and is behind current phase
- [ ] Updates `runs.phase` to target phase via direct UPDATE (no optimistic concurrency)
- [ ] Records `rollback` event in `phase_events` with from_phase, to_phase, and reason
- [ ] If run status was `completed`, reverts to `active`
- [ ] Returns JSON: `{rolled_back_phases: [...], from_phase, to_phase}`
- [ ] Rejects rollback on cancelled/failed runs
- [ ] Event bus notification emitted for rollback

### F3: Dispatch and Artifact Marking
**What:** When rolling back, mark dispatches and artifacts in rolled-back phases as cancelled/rolled_back.
**Acceptance criteria:**
- [ ] Dispatches in rolled-back phases set to `cancelled` status
- [ ] Dispatch cancellation events recorded in `dispatch_events`
- [ ] Agents in rolled-back phases set to `failed` status
- [ ] Artifacts in rolled-back phases set to `rolled_back` status
- [ ] Rollback JSON response includes `cancelled_dispatches` and `marked_artifacts` counts
- [ ] Already-completed dispatches are also marked (rollback is retroactive)

### F4: Code Rollback Query
**What:** `ic run rollback <id> --layer=code` queries dispatch metadata to report which commits were produced by which dispatches in which phases.
**Acceptance criteria:**
- [ ] Returns JSON array of `{dispatch_id, phase, name, commit_shas, file_paths}`
- [ ] `commit_shas` sourced from artifact `content_hash` fields (or empty if not recorded)
- [ ] `file_paths` sourced from artifact `path` fields
- [ ] Optional `--phase=<phase>` flag scopes query to single phase
- [ ] Optional `--format=text` for human-readable output
- [ ] Works independently of workflow rollback (query-only, no state mutation)

### F5: Dry-Run Mode
**What:** `ic run rollback <id> --dry-run --to-phase=<phase>` shows what would be rolled back without mutating state.
**Acceptance criteria:**
- [ ] Same validation as real rollback (phase exists, is behind current)
- [ ] Returns same JSON structure as real rollback
- [ ] No database writes occur
- [ ] Clearly labeled as dry-run in output

## Non-goals

- **Discovery/backlog rollback** — Deferred until E5 (Discovery) is built
- **Git command generation** — Kernel outputs data, doesn't generate revert commands
- **PID signaling** — Dispatches are marked cancelled, not actively killed
- **Rollback undo** — No "undo the rollback" — just advance forward again
- **Automatic rollback triggers** — Rollback is always explicit (human or OS layer initiates)

## Dependencies

- Intercore schema v7 (current) — migration builds on this
- `internal/phase/machine.go` — existing Advance() pattern to mirror
- `internal/dispatch/store.go` — existing dispatch status management
- `internal/runtrack/store.go` — existing artifact/agent management
- `internal/event/` — event bus for rollback notifications

## Open Questions

1. **Event bus notification format** — Should rollback events use the same `Event` struct with a new `Source` value, or extend the struct?
2. **Completed run rollback** — Rolling back a `completed` run to `active` is unusual. Should we warn or require `--force`?
3. **Artifact content** — Artifacts track `content_hash` but not commit SHAs directly. For F4, should we add a `git_sha` column, or is `content_hash` + `path` sufficient for the OS layer to correlate?
