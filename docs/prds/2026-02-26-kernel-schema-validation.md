# PRD: Stricter Schema Validation for the Kernel Interface

**Bead:** iv-npvnv
**Date:** 2026-02-26

## Problem

Intercore's 16 CLI subcommands output JSON defined only by Go struct tags, consumed by 3 pillar layers (Clavain bash, Autarch Go, Interspect). Any field rename, type change, or removal silently breaks downstream consumers with no detection until runtime. SQLite schema evolution uses ad-hoc `CREATE TABLE IF NOT EXISTS` with no migration testing or rollback story.

## Solution

Add contract stability guarantees at two levels: (1) auto-generated JSON Schema snapshots with CI-enforced break detection for all CLI output, and (2) a versioned migration framework with forward-migration CI tests for SQLite schema evolution.

## Features

### F1: JSON Schema Generator from Go Structs

**What:** Build a `go generate` step that reflects on annotated Go output structs and produces JSON Schema files in `contracts/cli/` and `contracts/events/`.

**Acceptance criteria:**
- [ ] Go generator produces valid JSON Schema (draft 2020-12) from annotated output structs
- [ ] All 16 CLI subcommand output types have generated schemas
- [ ] Event payload types have per-type schemas (not union)
- [ ] Generator is invoked via `go generate ./contracts/...`
- [ ] Generated schemas include field descriptions from struct comments
- [ ] Nullable fields (pointers, omitempty) correctly represented

### F2: Contract Snapshot CI Gate

**What:** CI step that runs `go generate`, diffs against committed snapshots, and blocks merges with unauthorized schema changes.

**Acceptance criteria:**
- [ ] CI runs `go generate ./contracts/...` and `git diff --exit-code contracts/`
- [ ] Unauthorized schema diffs fail the CI check
- [ ] `contracts/overrides/YYYY-MM-DD-<desc>.md` override files bypass the gate for that cycle
- [ ] Clear error message explains which schemas changed and how to proceed
- [ ] Override files document migration notes for consumers

### F3: Contract Ownership Matrix

**What:** Documentation mapping each contract surface to its owner, consumers, and versioning policy.

**Acceptance criteria:**
- [ ] Matrix exists at `docs/contract-ownership.md`
- [ ] Every CLI subcommand listed with owner and consumer repos
- [ ] Every event type listed with owner and consumer repos
- [ ] Versioning policy defined (semver rules for what constitutes breaking)
- [ ] Linked from root CLAUDE.md and AGENTS.md

### F4: Migration Runner + Versioned Migration Files

**What:** Replace the monolithic `schema.sql` with numbered migration files and a runner that applies them sequentially based on `PRAGMA user_version`.

**Acceptance criteria:**
- [ ] Migration files live in `core/intercore/internal/storage/migrations/`
- [ ] Baseline migration (v20) captures current schema as `020_baseline.sql`
- [ ] Migration runner reads `PRAGMA user_version`, applies pending migrations in order
- [ ] Each migration runs in a transaction with `user_version` set on success
- [ ] Existing databases at v16-v20 upgrade correctly (additive migrations preserved)
- [ ] New databases start from `020_baseline.sql`

### F5: Forward-Migration CI Tests

**What:** CI tests that verify migrations apply cleanly from empty DB and from oldest supported version (v16).

**Acceptance criteria:**
- [ ] Test: empty DB → apply all migrations → verify final schema matches expectation
- [ ] Test: v16 DB → apply migrations 017-020 → verify schema matches
- [ ] Test: v20 DB → no migrations needed → verify idempotent
- [ ] Final schema shape verified against `sqlite_master` snapshot
- [ ] Migration failures produce actionable error messages

## Non-goals

- Runtime schema validation (validating CLI inputs before processing)
- Protobuf/gRPC migration
- Automated rollback (down) migrations
- Cross-repo CI integration (Autarch/Clavain consuming Intercore schemas)
- SDK type generation from schemas
- Event payload versioning (separate from CLI output versioning)

## Dependencies

- `invopop/jsonschema` Go library (or equivalent) for schema generation — needs evaluation
- Intercore's existing output structs must be identifiable (may need struct tags or registration)
- CI infrastructure (GitHub Actions) for the gate step

## Open Questions

1. **Schema generator library** — `invopop/jsonschema` is the leading candidate (popular, struct-tag based). Need to verify nullable/omitempty handling before committing.
2. **Baseline extraction** — Start fresh from v20 baseline, or extract historical migrations? Baseline is simpler and v16 compat can use the existing `schema.sql` path.
3. **Consumer notification** — When `CONTRACT-BREAK` overrides merge, notification is manual for now. Automated cross-repo PRs are future work.
