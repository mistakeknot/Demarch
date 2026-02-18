# Dispatch Infrastructure Analysis

Analysis of the existing dispatch infrastructure for Go dispatch module integration.

Date: 2026-02-18

## 1. State File Format and Path

### Path

```
/tmp/clavain-dispatch-$$.json
```

Where `$$` is the shell PID of the dispatch.sh process. This is a flat JSON file written atomically (temp + mv) throughout the lifetime of a dispatch run. It is cleaned up on EXIT/INT/TERM.

### JSON Schema (exact field names and types)

```json
{
  "name":     "<string>",   // label for tracking (from --name, default "codex")
  "workdir":  "<string>",   // working directory (from -C, default ".")
  "started":  <integer>,    // Unix timestamp when dispatch began (date +%s)
  "activity": "<string>",   // current activity string (see values below)
  "turns":    <integer>,    // count of turn.started JSONL events
  "commands": <integer>,    // count of completed command_execution item events
  "messages": <integer>     // count of completed agent_message item events
}
```

All integers are bare JSON numbers (not quoted strings). The `started` field is a Unix epoch integer.

### Activity String Values

These are the only values `activity` takes, set by the awk JSONL parser:

| Activity value     | Trigger                                          |
|--------------------|--------------------------------------------------|
| `"starting"`       | Initial state on dispatch launch                 |
| `"thinking"`       | On `turn.started` event; also after `turn.completed` |
| `"running command"` | On `item.started` where item type is `command_execution` |
| `"writing"`        | On `item.completed` where item type is `agent_message` |

### Write Mechanism

Atomic write via temp file + rename:

```bash
printf '{"name":"%s","workdir":"%s","started":%d,"activity":"%s","turns":%d,"commands":%d,"messages":%d}\n' \
  "$name" "$workdir" "$started" "$activity" "$turns" "$commands" "$messages" \
  > "$STATE_FILE.tmp" && mv -f "$STATE_FILE.tmp" "$STATE_FILE"
```

The awk parser also does this atomically:

```awk
tmp = sf ".tmp"
printf "{...}\n", ... > tmp
close(tmp)
system("mv " tmp " " sf)
```

### Interband Sideband (structured path)

When `INTERBAND_DISPATCH_FILE` is set and `interband_write` is available, the same payload is written via `interband_write "clavain" "dispatch" "$DISPATCH_SESSION_ID" "$payload_json"`. This is a preferred structured path alongside the legacy `/tmp/` file.

---

## 2. Verdict Sidecar Format

File: `${OUTPUT_FILE}.verdict` (e.g., `/tmp/codex-review.md.verdict`)

### Format (exact line structure)

```
--- VERDICT ---
STATUS: <status>
FILES: <n> changed
FINDINGS: <n> (P0: <n>, P1: <n>, P2: <n>)
SUMMARY: <one-line summary>
---
```

Line by line:
- Line 1: `--- VERDICT ---` (literal, no leading/trailing spaces)
- Line 2: `STATUS: ` followed by one of: `pass`, `warn`, `fail` (lowercase)
- Line 3: `FILES: ` followed by `<n> changed`
- Line 4: `FINDINGS: ` followed by `<n> (P0: <n>, P1: <n>, P2: <n>)`
- Line 5: `SUMMARY: ` followed by a single-line description
- Line 6: `---` (literal close delimiter)

### Extraction Logic

`_extract_verdict` checks the last 7 lines of the output file for a natural verdict block. If the first of those lines is exactly `--- VERDICT ---`, it writes them directly to the `.verdict` file.

If no natural verdict block is found, it synthesizes one:
- Looks for a `VERDICT:` line in the output via `grep -m1 "^VERDICT:"`
- Sets `status="warn"` if `NEEDS_ATTENTION` in verdict line, `status="pass"` if `CLEAN`, or `status="warn"` + "No verdict line in agent output." if empty
- Synthesizes full block with `FILES: 0 changed` and `FINDINGS: 0 (P0: 0, P1: 0, P2: 0)`

---

## 3. Summary File Format

File: `${OUTPUT_FILE}.summary` (e.g., `/tmp/codex-review.md.summary`)

### Format

```
Dispatch: <name>
Duration: <m>m <s>s
Turns: <n> | Commands: <n> | Messages: <n>
Tokens: <n> in / <n> out
```

Written by the awk `END` block using `systime()`. If awk fails to write it (short/failed runs), bash writes a fallback:

```
Dispatch: <name>
Duration: <m>m <s>s
```

---

## 4. JSONL Parser: Events Tracked

The awk parser in `_jsonl_parser` processes `codex exec --json` stdout. It extracts `"type"` from each JSONL line using a regex match. Non-JSON lines (starting with anything other than `{`) are skipped.

### Events and Their Handling

| JSONL `type` field     | Action                                                            |
|------------------------|-------------------------------------------------------------------|
| `turn.started`         | `turns++`, `activity = "thinking"`                                |
| `item.started`         | If `item.type == "command_execution"`: `activity = "running command"` |
| `item.completed`       | If `command_execution`: `cmds++` / If `agent_message`: `msgs++`, `activity = "writing"` |
| `turn.completed`       | Extracts `input_tokens` and `output_tokens`, `activity = "thinking"` |
| (any other type)       | Ignored (state file still updated on every line)                  |

State file is updated atomically on every valid JSON line, not just on matching events.

Token extraction uses gawk `match(line, /"input_tokens":([0-9]+)/, t)` capture groups — this is why gawk is required; mawk/nawk do not support three-argument `match()`.

---

## 5. Exit Code Handling

```bash
"${CMD[@]}" | _jsonl_parser ...
CODEX_EXIT="${PIPESTATUS[0]}"
exit "$CODEX_EXIT"
```

The dispatch script propagates the `codex exec` exit code exactly as-is via `PIPESTATUS[0]`. The awk parser's exit code is ignored. The `set -euo pipefail` at the top is in effect, but the pipe-to-parser construct is handled manually with `PIPESTATUS`.

Fallback (no gawk):

```bash
"${CMD[@]}"
# implicit exit with last command's exit code (pipefail handles this)
```

---

## 6. Go Store Pattern (from intercore)

### Constructor Pattern

Every store package follows this exact pattern:

```go
type Store struct {
    db *sql.DB
}

func New(db *sql.DB) *Store {
    return &Store{db: db}
}
```

No variadic options, no interface embedding. The `*sql.DB` is injected directly. The DB wrapper's `SqlDB()` method exposes `*sql.DB` to store constructors:

```go
store := sentinel.New(d.SqlDB())
store := state.New(d.SqlDB())
```

### Method Signatures

Methods take `context.Context` as first argument. Error wrapping uses `fmt.Errorf("operation: %w", err)` with `%w` for all wrapped errors:

```go
func (s *Store) Check(ctx context.Context, name, scopeID string, intervalSec int) (bool, error)
func (s *Store) Reset(ctx context.Context, name, scopeID string) error
func (s *Store) List(ctx context.Context) ([]Sentinel, error)
func (s *Store) Prune(ctx context.Context, olderThan time.Duration) (int64, error)

func (s *Store) Set(ctx context.Context, key, scopeID string, payload json.RawMessage, ttl time.Duration) error
func (s *Store) Get(ctx context.Context, key, scopeID string) (json.RawMessage, error)
func (s *Store) Delete(ctx context.Context, key, scopeID string) (bool, error)
func (s *Store) List(ctx context.Context, key string) ([]string, error)
func (s *Store) Prune(ctx context.Context) (int64, error)
```

### Error Wrapping Convention

```go
return false, fmt.Errorf("begin tx: %w", err)
return false, fmt.Errorf("sentinel check: %w", err)
return nil, fmt.Errorf("list scan: %w", err)
```

Format: `"<operation-name>: %w"`. Multi-hop: `"state set: begin: %w"`.

### Transaction Pattern

```go
tx, err := s.db.BeginTx(ctx, nil)
if err != nil {
    return false, fmt.Errorf("begin tx: %w", err)
}
defer tx.Rollback()

// ... work ...

if err := tx.Commit(); err != nil {
    return false, fmt.Errorf("commit: %w", err)
}
```

`defer tx.Rollback()` is always present after BeginTx. Rollback on a committed tx is a no-op.

### Sentinel-specific: RETURNING pattern

Because `modernc.org/sqlite` does not support CTE wrapping `UPDATE ... RETURNING`, the pattern used is:

```go
rows, err := tx.QueryContext(ctx, `UPDATE ... RETURNING 1`, ...)
if err != nil { return false, fmt.Errorf("sentinel check: %w", err) }
allowed := 0
for rows.Next() { allowed++ }
rows.Close()
if err := rows.Err(); err != nil { return false, fmt.Errorf("sentinel check rows: %w", err) }
```

### Test Pattern

Tests use a `setupTestDB(t *testing.T) *sql.DB` helper that:
- Creates a temp dir via `t.TempDir()`
- Opens SQLite at `filepath.Join(dir, "test.db")`
- Uses `db.SetMaxOpenConns(1)`
- Registers `t.Cleanup(func() { db.Close() })`
- Creates the needed table(s) inline (no schema embed — table DDL is in the test itself)

Subtests use `t.Run("name", func(t *testing.T) { db := setupTestDB(t); ... })` with a fresh DB per case.

### Package layout

```
internal/
  db/
    db.go       -- DB struct, Open, Migrate, Health, SchemaVersion
    db_test.go
    disk.go     -- checkDiskSpace helper
    schema.sql  -- embedded via //go:embed
  sentinel/
    sentinel.go -- Store struct + methods
    sentinel_test.go
  state/
    state.go    -- Store struct + methods + ValidatePayload
    state_test.go
cmd/ic/
  main.go       -- CLI dispatch, flag parsing, command routing
```

---

## 7. Migration Pattern for Adding v2 Tables

### Current State (schema v1)

```sql
-- schema.sql (v1)
CREATE TABLE IF NOT EXISTS state (...);
CREATE INDEX IF NOT EXISTS ...;
CREATE TABLE IF NOT EXISTS sentinels (...);
```

```go
const (
    currentSchemaVersion = 1
    maxSchemaVersion     = 1
)
```

### How to Add v2 Tables

The migration in `db.go` is version-gated by comparing `currentVersion` to `currentSchemaVersion`. The approach uses a single embedded `schema.sql` applied when version == 0. For v2, the pattern must be extended to handle incremental migrations.

**Step-by-step for v2:**

1. Add a new `schema_v2.sql` (or `migrations/002_dispatch.sql`) embedded alongside the existing `schema.sql`.

2. Bump constants:
   ```go
   const (
       currentSchemaVersion = 2
       maxSchemaVersion     = 2
   )
   ```

3. Extend `Migrate` to handle incremental steps:
   ```go
   if currentVersion < 1 {
       // apply schema.sql (v1 tables)
       if _, err := tx.ExecContext(ctx, schemaDDL); err != nil {
           return fmt.Errorf("migrate: apply v1: %w", err)
       }
   }
   if currentVersion < 2 {
       // apply v2 DDL (new tables/indexes)
       if _, err := tx.ExecContext(ctx, schemaV2DDL); err != nil {
           return fmt.Errorf("migrate: apply v2: %w", err)
       }
   }
   ```

4. Update `PRAGMA user_version` to `currentSchemaVersion` at the end of the transaction (already in the code as `fmt.Sprintf("PRAGMA user_version = %d", currentSchemaVersion)`).

**Key invariant:** The existing `_migrate_lock` table trick (using `CREATE TABLE IF NOT EXISTS _migrate_lock` to force an exclusive lock) is already in place. Do not change this pattern.

**Backup:** `Migrate` already creates a timestamped backup before applying any migration when `info.Size() > 0`. This continues to work with incremental steps.

### Example v2 Table for Dispatch Runs

For a dispatch run tracking table, following the established schema conventions:

```sql
-- schema_v2.sql additions
CREATE TABLE IF NOT EXISTS dispatch_runs (
    id          INTEGER PRIMARY KEY,
    scope_id    TEXT NOT NULL,
    name        TEXT NOT NULL,
    workdir     TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    exit_code   INTEGER,
    turns       INTEGER NOT NULL DEFAULT 0,
    commands    INTEGER NOT NULL DEFAULT 0,
    messages    INTEGER NOT NULL DEFAULT 0,
    in_tokens   INTEGER NOT NULL DEFAULT 0,
    out_tokens  INTEGER NOT NULL DEFAULT 0,
    activity    TEXT NOT NULL DEFAULT 'starting',
    created_at  INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_dispatch_scope ON dispatch_runs(scope_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_dispatch_started ON dispatch_runs(started_at DESC);
```

---

## 8. codex CLI Availability and Flags

### Binary Location

```
/usr/bin/codex
```

Available in PATH.

### `codex exec` Flags (complete)

```
codex exec [OPTIONS] [PROMPT]
```

| Flag | Short | Description |
|------|-------|-------------|
| `--config <key=value>` | `-c` | Override config.toml value (TOML-parsed, dotted path) |
| `--enable <FEATURE>` | | Enable a feature flag |
| `--disable <FEATURE>` | | Disable a feature flag |
| `--image <FILE>...` | `-i` | Attach image(s) to prompt |
| `--model <MODEL>` | `-m` | Model override |
| `--oss` | | Use open-source provider |
| `--local-provider <OSS_PROVIDER>` | | lmstudio or ollama |
| `--sandbox <MODE>` | `-s` | `read-only`, `workspace-write`, `danger-full-access` |
| `--profile <CONFIG_PROFILE>` | `-p` | Config profile from config.toml |
| `--full-auto` | | Sets `-a on-request --sandbox workspace-write` |
| `--dangerously-bypass-approvals-and-sandbox` | | Skip all confirmations + sandboxing |
| `--cd <DIR>` | `-C` | Working directory root for the agent |
| `--skip-git-repo-check` | | Allow outside a git repo |
| `--add-dir <DIR>` | | Additional writable directory |
| `--ephemeral` | | No session persistence to disk |
| `--output-schema <FILE>` | | JSON Schema for final response shape |
| `--color <COLOR>` | | `always`, `never`, `auto` (default: `auto`) |
| `--json` | | Emit JSONL events to stdout |
| `--output-last-message <FILE>` | `-o` | File to write agent's last message |
| `--help` | `-h` | Help |
| `--version` | `-V` | Print version |

`codex exec` also has two subcommands:
- `codex exec resume` — resume previous session (`--last` flag or explicit session ID)
- `codex exec review` — run a code review against the current repository

The JSONL stream from `--json` emits events with top-level `"type"` field. The types tracked by dispatch.sh are: `turn.started`, `turn.completed`, `item.started`, `item.completed`. Token counts are on `turn.completed` as `"input_tokens"` and `"output_tokens"`. Command/message item types are on `"item"` sub-object as `"type":"command_execution"` and `"type":"agent_message"`.

---

## 9. Legacy Key Mapping (from intercore compat table)

The `legacyPatterns` map in `main.go` documents all legacy temp file patterns that intercore tracks. Relevant for dispatch integration:

| intercore key      | Legacy temp file pattern                    |
|--------------------|---------------------------------------------|
| `dispatch`         | `/tmp/clavain-dispatch-*.json`              |
| `stop`             | `/tmp/clavain-stop-*`                       |
| `compound_throttle` | `/tmp/clavain-compound-last-*`             |
| `drift_throttle`   | `/tmp/clavain-drift-last-*`                 |
| `handoff`          | `/tmp/clavain-handoff-*`                    |
| `autopub`          | `/tmp/clavain-autopub*.lock`                |
| `catalog_remind`   | `/tmp/clavain-catalog-remind-*.lock`        |
| `discovery_brief`  | `/tmp/clavain-discovery-brief-*.cache`      |

The `dispatch` key uses scope_id derived from the PID (the `$$` in the file name pattern).

---

## 10. Summary of Key Integration Points

For a Go dispatch module integrating with this infrastructure:

1. **State file**: Read `/tmp/clavain-dispatch-$$.json` to pick up live dispatch status. Fields: `name`, `workdir`, `started` (Unix int), `activity` (string), `turns`, `commands`, `messages` (all ints).

2. **Verdict sidecar**: Read `<output>.verdict`. Always 6 lines. Starts with `--- VERDICT ---`, ends with `---`. Fields: STATUS, FILES, FINDINGS, SUMMARY.

3. **Summary sidecar**: Read `<output>.summary`. 2-4 lines. First line is `Dispatch: <name>`.

4. **Go Store pattern**: `New(db *sql.DB) *Store`. Context-first methods. `fmt.Errorf("op: %w", err)` wrapping. Always `defer tx.Rollback()` after `BeginTx`.

5. **Schema v2**: Bump `currentSchemaVersion`/`maxSchemaVersion` to 2, embed new DDL, add incremental migration branch `if currentVersion < 2 { ... }`.

6. **codex exec flags**: Use `-s workspace-write -C <dir> -o <output> --json` for dispatch runs. `--json` is required for JSONL event streaming.

7. **PIPESTATUS**: Go equivalent: capture subprocess exit code directly; awk/parser pipe exit code is irrelevant.
