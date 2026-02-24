# Plan: Intercore SandboxSpec Schema on Dispatches
**Bead:** iv-rjz3

## Goal

Add structured sandbox specification columns to dispatch records so the kernel stores what sandbox policy was **requested** at spawn time and what policy was **effective** at completion. The kernel stores contracts and records compliance — enforcement is by dispatch drivers.

## Scope

**Tier 1 only** (per bead description):
- Tool allowlists
- Working directory isolation
- Filesystem access mode
- Resource limits (max turns, max commands — advisory)

**Explicitly out of scope:** Container image, mounts, network policy (Tier 2, future).

## Design

### New Columns

Two JSON TEXT columns on the `dispatches` table:

| Column | Type | Set At | Mutable? |
|--------|------|--------|----------|
| `sandbox_spec` | TEXT (JSON) | Spawn | No (immutable after creation) |
| `sandbox_effective` | TEXT (JSON) | Completion | No (set once at terminal status) |

**`sandbox_spec`** — the requested sandbox contract:
```json
{
  "tools_allowed": ["Read", "Grep", "Glob", "Bash"],
  "tools_denied": [],
  "working_dir": "/home/mk/projects/Demarch",
  "access_mode": "workspace-write",
  "max_turns": 50,
  "max_commands": 200
}
```

**`sandbox_effective`** — what actually happened (recorded at completion):
```json
{
  "tools_used": ["Read", "Grep", "Bash"],
  "access_mode": "workspace-write",
  "turns_used": 23,
  "commands_used": 47,
  "violations": []
}
```

All fields are optional (omit = unconstrained). The existing `sandbox` column (simple string like `"workspace-write"`) is preserved for backward compatibility — `sandbox_spec.access_mode` supersedes it when present.

### Why JSON, not individual columns?

The SandboxSpec is a **nested contract** — tool lists are arrays, violations are arrays of objects. Normalizing these into separate columns or tables would be over-engineering for a v1 that stores contracts for audit. JSON columns in SQLite are well-supported and match the existing pattern (e.g., `gate_rules TEXT` on runs).

## Changes

### 1. Schema migration (v17 → v18)

**File:** `internal/db/db.go`

Add migration block:
```go
// v17 → v18: sandbox specification columns
if currentVersion >= 2 && currentVersion < 18 {
    v18Stmts := []string{
        "ALTER TABLE dispatches ADD COLUMN sandbox_spec TEXT",
        "ALTER TABLE dispatches ADD COLUMN sandbox_effective TEXT",
    }
    for _, stmt := range v18Stmts {
        if _, err := tx.ExecContext(ctx, stmt); err != nil {
            if !isDuplicateColumnError(err) {
                return fmt.Errorf("migrate v17→v18: %w", err)
            }
        }
    }
}
```

Update `currentSchemaVersion` and `maxSchemaVersion` from 17 → 18.

**File:** `internal/db/schema.sql`

Add columns after `sandbox`:
```sql
sandbox_spec     TEXT,
sandbox_effective TEXT,
```

### 2. Dispatch struct + column list

**File:** `internal/dispatch/dispatch.go`

Add to `Dispatch` struct:
```go
SandboxSpec      *string  // JSON: requested sandbox contract
SandboxEffective *string  // JSON: effective sandbox at completion
```

Update `dispatchCols` to include the two new columns.

Update both `scanDispatch` / `scanDispatches` to scan the new nullable columns.

Add `"sandbox_effective"` to `allowedUpdateCols` (set at completion). `sandbox_spec` is NOT in the update allowlist — it's set only at creation.

### 3. SpawnOptions + Create

**File:** `internal/dispatch/spawn.go`

Add to `SpawnOptions`:
```go
SandboxSpec string // optional: JSON sandbox specification
```

**File:** `internal/dispatch/dispatch.go` (Create function)

Include `sandbox_spec` in the INSERT columns, reading from `d.SandboxSpec`.

### 4. CLI: `ic dispatch spawn --sandbox-spec=`

**File:** `cmd/ic/dispatch.go`

Add flag parsing:
```go
case strings.HasPrefix(args[i], "--sandbox-spec="):
    opts.SandboxSpec = strings.TrimPrefix(args[i], "--sandbox-spec=")
```

The value is a JSON string (or `@file.json` for file-based input — stretch goal, not v1).

### 5. CLI: `ic dispatch status` output

**File:** `cmd/ic/dispatch.go`

**`dispatchToMap()`:** Use `json.RawMessage` to embed sandbox JSON as nested objects (not double-escaped strings):
```go
if d.SandboxSpec != nil {
    m["sandbox_spec"] = json.RawMessage(*d.SandboxSpec)
}
if d.SandboxEffective != nil {
    m["sandbox_effective"] = json.RawMessage(*d.SandboxEffective)
}
```

**`printDispatch()`:** Add human-readable display of sandbox spec/effective (if non-nil) after the existing sandbox line.

### 6. Tests

**File:** `internal/dispatch/dispatch_test.go` (or new `sandbox_test.go`)

- Test: spawn with `sandbox_spec` → verify stored correctly
- Test: spawn without `sandbox_spec` → verify NULL (backward compat)
- Test: update `sandbox_effective` at completion → verify stored
- Test: attempt to update `sandbox_spec` via UpdateStatus → verify rejected (not in allowedUpdateCols)
- Test: migration from v17 → v18 adds columns idempotently

**File:** `test-integration.sh`

- Add integration test: spawn with `--sandbox-spec='{"tools_allowed":["Read"]}'`, complete, verify `ic dispatch status --json` shows both fields.

## Task Breakdown

| # | Task | Effort |
|---|------|--------|
| 1 | Schema migration (db.go + schema.sql) | 10 min |
| 2 | Dispatch struct + column list + scan | 15 min |
| 3 | SpawnOptions + Create INSERT | 10 min |
| 4 | allowedUpdateCols for sandbox_effective | 5 min |
| 5 | CLI --sandbox-spec flag | 5 min |
| 6 | CLI status --json output | 5 min |
| 7 | Unit tests | 15 min |
| 8 | Integration test | 10 min |

## Risks

- **JSON validation:** v1 does NOT validate the JSON structure — the kernel stores whatever the caller provides. Validation is a future concern (when drivers start enforcing).
- **Backward compat:** Existing dispatches get NULL for both new columns. All scan code uses nullable types. The existing `sandbox` string column is unchanged.
