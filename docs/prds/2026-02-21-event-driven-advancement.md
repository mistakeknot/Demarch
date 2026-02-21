# PRD: Event-Driven Advancement

**Bead:** iv-r9j2
**Sprint:** iv-lype
**Brainstorm:** [docs/brainstorms/2026-02-21-event-driven-advancement-brainstorm.md](../brainstorms/2026-02-21-event-driven-advancement-brainstorm.md)

## Problem

Sprint phase routing lives in a bash case statement (`sprint_next_step()`) that's invisible to the kernel, can't be inspected at runtime, can't be overridden mid-sprint, and doesn't support autonomous dispatch. The kernel emits phase events but doesn't know what should happen next.

## Solution

Add a `phase_actions` table to intercore that maps phases to commands with template arguments. `ic run advance` resolves templates (e.g., `${artifact:plan}`) and returns actions in its JSON output. Sprint skill reads actions instead of consulting a bash case statement. Hook handler can auto-dispatch for autonomous runs.

## Features

### F1: Schema + Store — `phase_actions` table
**What:** Add `phase_actions` table to intercore schema and Go CRUD store.
**Acceptance criteria:**
- [ ] `phase_actions` table created via schema migration (v14)
- [ ] `ActionStore` in new `internal/action/` package with Add, List, Update, Delete, ListForPhase methods
- [ ] Foreign key on `run_id` referencing `runs(id)`
- [ ] UNIQUE constraint on `(run_id, phase, command)` prevents duplicate registrations
- [ ] Integration test: CRUD round-trip passes

### F2: CLI — `ic run action` subcommands
**What:** CLI surface for managing phase actions.
**Acceptance criteria:**
- [ ] `ic run action add <run_id> --phase=<p> --command=<c> [--args=<json>] [--mode=<m>] [--type=<t>]`
- [ ] `ic run action list <run_id> [--phase=<p>] [--json]`
- [ ] `ic run action update <run_id> --phase=<p> --command=<c> [--args=<json>] [--mode=<m>]`
- [ ] `ic run action delete <run_id> --phase=<p> --command=<c>`
- [ ] `--actions=<json>` flag on `ic run create` for batch registration at create time
- [ ] Integration tests: add/list/update/delete pass; create-with-actions pass

### F3: Resolution — template variables in `ic run advance`
**What:** `ic run advance` resolves `${artifact:<type>}` placeholders from `run_artifacts` and includes resolved actions in JSON output.
**Acceptance criteria:**
- [ ] `ic run advance` output includes `"actions": [...]` array when phase_actions exist for `to_phase`
- [ ] `${artifact:<type>}` resolves from `run_artifacts` WHERE `run_id=? AND type=?`, using most recent match
- [ ] `${run_id}` and `${project_dir}` resolve to current values
- [ ] Unresolvable placeholders are left as-is (caller detects and surfaces)
- [ ] Actions are filtered by mode when `--mode=interactive|autonomous` flag is passed
- [ ] No actions = no `"actions"` key in output (backward compatible)
- [ ] PhaseEventCallback event payload includes resolved actions
- [ ] Unit test: resolution with all variable types
- [ ] Integration test: advance with actions returns resolved JSON

### F4: Bash integration — sprint skill consumes kernel actions
**What:** `sprint_advance()` reads actions from kernel instead of `sprint_next_step()` case statement. Fallback to `sprint_next_step()` when no kernel actions exist.
**Acceptance criteria:**
- [ ] `sprint_advance()` parses `actions` array from `ic run advance` result
- [ ] Returns first action's command to caller (sprint SKILL.md dispatches it)
- [ ] Falls back to `sprint_next_step()` when no actions returned (backward compat during migration)
- [ ] `sprint_create()` registers default action template via `--actions` flag
- [ ] New bash wrapper: `intercore_run_action_add()`, `intercore_run_action_list()`
- [ ] End-to-end: sprint create → advance → action returned matches expected command

## Non-goals

- Hook-based autonomous dispatch (Phase 3, future sprint)
- General-purpose workflow DSL
- Action execution tracking / completion recording (Phase 2)
- Retiring SpawnHandler (it continues to work alongside phase_actions)

## Dependencies

- Intercore schema v13 (current) — migration to v14 is additive-only
- `run_artifacts` table (exists since schema v4) — used for `${artifact:*}` resolution
- `lib-sprint.sh` (current) — modified, not replaced

## Open Questions

None — all resolved in brainstorm.
