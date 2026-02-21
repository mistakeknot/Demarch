# Create 4 Feature Beads — Phase Actions Pipeline

**Date**: 2026-02-21
**Task**: Create four feature beads for the intercore phase actions pipeline.

## Summary

All four feature beads were created successfully from `/root/projects/Interverse`. Each targets a layer of the phase actions feature — from schema through CLI to resolution and bash integration.

## Bead Creation Results

### F1: Schema + Store — phase_actions table (v14 migration)
- **Bead ID**: `iv-otvb`
- **Priority**: P2
- **Status**: open
- **Description**: Add phase_actions table to intercore schema and Go CRUD ActionStore in internal/action/ package. FK on run_id, UNIQUE on (run_id, phase, command). Integration test for CRUD round-trip.

### F2: CLI — ic run action subcommands (add/list/update/delete)
- **Bead ID**: `iv-qjm3`
- **Priority**: P2
- **Status**: open
- **Description**: CLI surface for managing phase actions. ic run action add/list/update/delete. --actions flag on ic run create for batch registration. Integration tests.

### F3: Resolution — template variables in ic run advance output
- **Bead ID**: `iv-z5pc`
- **Priority**: P2
- **Status**: open
- **Description**: ic run advance resolves ${artifact:<type>} from run_artifacts, includes resolved actions array in JSON output. PhaseEventCallback event payload includes actions. Mode filtering. Backward compatible (no actions = no key).

### F4: Bash integration — sprint skill consumes kernel actions
- **Bead ID**: `iv-pipe`
- **Priority**: P2
- **Status**: open
- **Description**: sprint_advance() reads actions from kernel instead of sprint_next_step() case statement. Fallback when no actions. sprint_create() registers default actions via --actions flag. New bash wrappers.

## All Bead IDs

| Bead | ID |
|------|------|
| F1 | iv-otvb |
| F2 | iv-qjm3 |
| F3 | iv-z5pc |
| F4 | iv-pipe |

## Notes

- All beads created with `--type=feature --priority=2` as specified.
- Warning about `beads.role` not configured appeared on each command — this is cosmetic and does not affect bead creation.
- The four beads form a dependency chain: F1 (schema) -> F2 (CLI) -> F3 (resolution) -> F4 (bash integration). Dependencies were not explicitly linked in this operation.
