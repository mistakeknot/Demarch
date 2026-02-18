---
title: "intercore Schema Upgrade + Binary Deployment Pattern"
category: patterns
severity: medium
date: 2026-02-18
tags: [intercore, sqlite, migration, deployment, go-embed]
related_issues: [iv-a20e]
---

# intercore Schema Upgrade + Binary Deployment Pattern

## Problem

When adding new tables to intercore's SQLite schema (e.g., v2→v3 adding `runs` + `phase_events`), the live installed binary doesn't automatically pick up changes. The schema DDL is embedded in the Go binary via `//go:embed schema.sql`, so:

1. The old binary can't create new tables (it doesn't know about them)
2. Running `ic init` with the old binary sets `PRAGMA user_version` to the old version
3. The live DB at `.clavain/intercore.db` stays at the old schema

## Investigation Steps

1. `ic version` showed `schema: v2` — binary was stale
2. `which ic` → `/home/mk/.local/bin/ic` → symlink to `/home/mk/go/bin/ic`
3. Binary timestamp predated the commit adding v3 schema

## Solution: 3-Step Deployment Sequence

```bash
# 1. Rebuild binary from source (schema.sql is //go:embed'd)
cd /root/projects/Interverse/infra/intercore
go build -o /home/mk/go/bin/ic ./cmd/ic

# 2. Migrate live DB (creates timestamped backup automatically)
cd /root/projects/Interverse
ic init   # → "initialized .clavain/intercore.db (schema v3)"

# 3. Verify
ic version   # schema: v3
ic health    # ok
```

## Why This Works

The migration strategy is **additive-only** using `CREATE TABLE IF NOT EXISTS`:

- All tables use `IF NOT EXISTS`, so re-applying the full DDL on an existing DB safely creates only new tables
- `PRAGMA user_version` is bumped inside the same transaction as the DDL
- `Migrate()` creates a timestamped backup before any migration attempt
- `Open()` allows older schemas (only rejects versions **above** `maxSchemaVersion`)

This means:
- v2 databases work fine with the v3 binary (existing commands keep working)
- New features (`ic run`) just won't work until `ic init` runs the migration
- The backup at `intercore.db.backup-YYYYMMDD-HHMMSS` provides rollback

## Key Gotcha

**The schema version constant and DDL travel together in the binary.** If you bump `currentSchemaVersion` in `db.go` and add tables to `schema.sql`, you MUST rebuild the installed binary before running `ic init`. Running `ic init` with the old binary is a no-op (it thinks it's already at the current version).

## When This Pattern Applies

Every time intercore gains new tables or modifies the schema:
- v1→v2: Added `dispatches` table
- v2→v3: Added `runs` + `phase_events` tables
- Future: Any additive schema change follows the same 3-step sequence

## Limitation

This pattern **breaks** for destructive schema changes (ALTER TABLE, column renames, data migrations). Those would need conditional migration blocks inside `Migrate()` keyed on the current `user_version`. All intercore migrations so far have been purely additive.
