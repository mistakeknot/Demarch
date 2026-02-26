# Beads Subtask Creation for Epic iv-pxid

**Date:** 2026-02-22
**Epic:** iv-pxid (Interverse plugin validation)

## Summary

Created 6 subtasks under epic `iv-pxid` and wired 3 dependency relationships so that the validator script (task 1) blocks downstream work.

## Tasks Created

| ID | Title | Type | Priority |
|---|---|---|---|
| iv-pxid.1 | Create validate-plugin.sh structural validator | task | P1 |
| iv-pxid.2 | Wire validate-plugin.sh into interbump.sh as pre-publish gate | task | P2 |
| iv-pxid.3 | Fix 14 plugins with undeclared hooks in plugin.json | bug | P1 |
| iv-pxid.4 | Fix 7 plugins with undeclared skills/commands | bug | P1 |
| iv-pxid.5 | Fix 3 version mismatches + hardcoded API key | bug | P2 |
| iv-pxid.6 | Add cache cleanup tooling to prune stale plugin versions | task | P3 |

## Dependencies Added

- **iv-pxid.2** (wire into interbump) depends on **iv-pxid.1** (create validator)
- **iv-pxid.3** (fix undeclared hooks) depends on **iv-pxid.1** (create validator)
- **iv-pxid.4** (fix undeclared skills/commands) depends on **iv-pxid.1** (create validator)

Tasks 5 and 6 have no dependencies — they can proceed independently.

## Execution Notes

- The `bd create` command does not have an `--epic` flag. Used `--parent=iv-pxid` to attach subtasks as children of the epic.
- Used `--silent` flag to capture only the bead ID from each create command.
- Dependencies use the `blocks` relationship type (default for `bd dep add`).
- A non-fatal warning `beads.role not configured` appeared on the first create; subsequent calls suppressed it via `tail -1`.

## Dependency Graph

```
iv-pxid (epic)
├── iv-pxid.1  Create validator         ← MUST complete first
│   ├── iv-pxid.2  Wire into interbump  (blocked by .1)
│   ├── iv-pxid.3  Fix 14 hooks         (blocked by .1)
│   └── iv-pxid.4  Fix 7 features       (blocked by .1)
├── iv-pxid.5  Fix version mismatches   (independent)
└── iv-pxid.6  Cache cleanup            (independent)
```

## All Bead IDs

```
iv-pxid.1
iv-pxid.2
iv-pxid.3
iv-pxid.4
iv-pxid.5
iv-pxid.6
```
