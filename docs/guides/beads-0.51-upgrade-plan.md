# Beads 0.51+ Upgrade Status (Completed)

## Status

The migration from SQLite-era Beads to modern Dolt-based Beads is complete.

This guide is now the post-migration reference, not a pending plan.

## Current state (verified 2026-02-27)

- CLI version: `bd 0.56.1` (latest at verification time)
- Storage/backend: Dolt
- Sync mode: `dolt-native` (`bd config get sync.mode`)
- Active tracker: Demarch root `.beads/` (module-level `.beads/` are archival/read-only)
- `bd sync` behavior: deprecated compatibility no-op

## Operational rules after migration

1. Do not use removed/obsolete sync flags:
- `bd sync --from-main` (obsolete)
- `bd sync --status` (obsolete)

2. Treat `bd sync` as compatibility-only:
- It no longer performs legacy git sync behavior.
- Keep it only where workflow/docs expect a compatibility step.

3. Use explicit commands for data movement:
- Export/import: `bd export`, `bd import`
- Dolt remote operations: `bd dolt pull`, `bd dolt push`

4. Use normal git commands for code pushes:
- `git pull --rebase`
- `git push`

## Validation commands

Use these checks when auditing a clone or after upgrades:

```bash
bd --version
bd config get sync.mode
bd doctor --json
bd sync --help
```

Expected indicators:
- CLI is `0.51+` (currently `0.56.1`)
- `sync.mode` is `dolt-native`
- `bd doctor` reports Dolt storage and healthy schema
- `bd sync --help` states deprecated/no-op behavior

## Historical note

Older references to `bd 0.50.3`, SQLite backend, and migration rollout steps are retained in commit history only. They should not be treated as current operational guidance.
