# Stricter Schema Validation for the Kernel Interface

**Bead:** iv-npvnv
**Date:** 2026-02-26
**Status:** Brainstorm

## What We're Building

A contract stability layer for Intercore's CLI boundary that prevents accidental breaking changes from propagating across pillars. Two workstreams:

1. **API contract snapshots + CI gate** (iv-npvnv.1, P0) — Auto-generate JSON Schema from Go structs, snapshot in-repo, diff in CI to catch breaking changes before merge.
2. **Versioned migration framework** (iv-npvnv.2, P1) — Replace ad-hoc `CREATE TABLE IF NOT EXISTS` with numbered migration files and forward-migration CI tests.

## Why This Approach

### The Problem

Intercore has 16 CLI subcommands with `--json` output, consumed by 3 different layers:
- **Clavain bash wrappers** (`lib-intercore.sh`, `lib-sprint.sh`) — parse JSON via `jq`
- **Autarch Go clients** (`pkg/intercore/`, `pkg/clavain/`) — unmarshal into typed structs
- **Interspect profiler** — reads event tables directly

Today, JSON output shapes are defined implicitly by Go struct tags. There's no versioning, no schema validation, and no break detection. A field rename in Intercore silently breaks Clavain's bash parsing and Autarch's Go deserialization.

For migrations: Intercore is at SQLite schema v20 with additive migrations and a version check at open time (rejects future versions). Forward-compatible from v16+, but there's no rollback story, no migration test coverage, and each service has its own ad-hoc pattern.

### Chosen Approach

**JSON Schema snapshots auto-generated from Go structs.** This is the lightest-weight option that provides real contract guarantees:
- No new serialization format (stays JSON)
- No new toolchain dependency (Protobuf, CUE, TypeSpec)
- Schemas stay in sync with Go types automatically
- CI diffs catch any structural change before merge
- Golden-file testing was rejected (too brittle to ordering/whitespace)
- Protobufs were rejected (too heavy — would require rewriting all serialization)

**Versioned migration files with forward-only CI tests.** Numbered SQL files (`001_init.sql`, `002_add_lanes.sql`) applied sequentially. Rollback strategy is restore-from-backup (not automated down-migrations). This matches standard Go project conventions and avoids the complexity of bidirectional migrations.

## Key Decisions

1. **Technology: JSON Schema** — Auto-generated from Go output structs, snapshotted in `contracts/` directory. Not hand-maintained (avoids drift) and not recorded from CLI output (avoids flaky CI).

2. **Surface scope: All 16 CLI subcommands** — Full coverage, not just critical-path commands. Every `--json` output shape gets a schema snapshot.

3. **Migration approach: Versioned forward-only** — Numbered migration files, sequential application, forward-tested in CI. No automated rollback — rollback is "restore from backup." Standard Go pattern.

4. **Break detection: CI gate** — Schema diff in CI blocks unauthorized breaking changes. Intentional breaks require explicit annotation (e.g., `// CONTRACT-BREAK: <reason>` or a dedicated override file).

## Contract Surface Inventory

### CLI Commands (all have `--json` mode)

| Domain | Commands | Consumers |
|--------|----------|-----------|
| Runs | `run create`, `run advance`, `run status`, `run list`, `run budget` | Clavain bash, Autarch Go |
| State | `state get`, `state set`, `state sentinel-check` | Clavain bash |
| Dispatch | `dispatch`, `dispatch tokens` | Clavain bash |
| Events | `event emit`, `event query` | Clavain bash, Interspect |
| Coordination | `coordination reserve`, `coordination release`, `coordination conflicts` | Interlock MCP |
| Config | `config get` | Clavain bash |
| Agency | `agency specs`, `agency models` | Clavain bash |
| Discovery | `discovery scan` | Clavain bash |
| Portfolio | `portfolio list`, `portfolio deps` | Clavain bash |
| Scheduler | `scheduler next` | Clavain bash |

### Event Payloads

Events written to `events` table with JSON payload. Types include:
- `phase.advanced`, `gate.checked`, `run.created`, `run.completed`
- `budget.exceeded`, `dispatch.started`, `dispatch.completed`
- `coordination.reserved`, `coordination.released`

### SQLite Schema (v20)

16 tables across 3 concerns:
- **Core**: `runs`, `run_state`, `events`, `gate_rules`, `artifacts`, `agents`
- **Coordination**: `coordination_locks`, `coordination_events`
- **Domain**: `lanes`, `portfolio_*`, `scheduler_*`

## Schema Generation Design

```
Go structs (source of truth)
    ↓ [go generate / build step]
contracts/<command>.schema.json (snapshots)
    ↓ [CI diff]
PASS/FAIL → block merge on unauthorized diff
```

### Generation Flow

1. Tag or annotate output structs as "contract types" (e.g., `RunStatus`, `EventPayload`)
2. Use a Go schema generator (jsonschema lib or custom reflection) to produce JSON Schema
3. Write schemas to `contracts/cli/<command>.json` and `contracts/events/<type>.json`
4. CI step: `go generate ./contracts/...` → `git diff --exit-code contracts/`
5. If diff detected without `CONTRACT-BREAK` annotation → CI fails

### Breaking Change Override

For intentional breaks:
- Add `contracts/overrides/YYYY-MM-DD-<description>.md` with migration notes
- CI reads overrides dir and allows the diff for that cycle
- Override files are cleaned up after consumers migrate

## Migration Framework Design

```
core/intercore/internal/storage/migrations/
    001_init.sql
    002_add_metadata.sql
    ...
    020_coordination_locks.sql
```

### Migration Runner

- Read `PRAGMA user_version` to get current version
- Apply all migrations with version > current sequentially
- Each migration runs in a transaction
- Set `PRAGMA user_version = <new_version>` after each successful migration
- Forward-only: no down migrations (rollback = restore backup)

### CI Testing

- Test applies all migrations from scratch (empty DB → current)
- Test applies migrations from v16 (oldest supported) → current
- Verify final schema matches expected shape via `sqlite_master` snapshot

## Open Questions

1. **Schema generator library** — Which Go JSON Schema generator to use? Options: `invopop/jsonschema` (popular, struct-tag based), `santhosh-tekuri/jsonschema` (validator only), custom reflection. Need to evaluate struct tag support and nullable handling.

2. **Event payload schemas** — Events have a polymorphic `data` field. Should we generate a schema per event type, or a union schema? Per-type is cleaner but more files.

3. **Existing migration extraction** — Current schema is in one big `schema.sql` with `CREATE TABLE IF NOT EXISTS`. Should we extract historical migrations (001 through 020) or just start fresh from v20 with a single `baseline.sql`?

4. **Consumer notification** — When a `CONTRACT-BREAK` override is merged, how do we notify consumer repos (Clavain, Autarch) that they need to update? Manual? GitHub issue? Automated PR?

## Scope Boundaries

**In scope:**
- JSON Schema generation from Go structs
- Schema snapshot CI gate for all 16 CLI commands
- Event payload schema snapshots
- Versioned migration files for Intercore SQLite
- Forward-migration CI tests
- Contract ownership matrix in docs

**Out of scope (future work):**
- Runtime schema validation (validating input before processing)
- Protobuf/gRPC migration
- Automated rollback migrations
- Cross-repo CI integration (Autarch/Clavain CI consuming Intercore schemas)
- SDK type generation from schemas
