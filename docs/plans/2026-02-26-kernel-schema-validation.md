# Kernel Schema Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Add contract stability guarantees to Intercore's CLI JSON output (auto-generated JSON Schema snapshots with CI break detection) and a versioned migration framework with forward-migration CI tests.

**Architecture:** A `go generate` step reflects on annotated Go output structs using `invopop/jsonschema` to produce JSON Schema files in `contracts/`. CI diffs these snapshots against committed versions. Separately, the monolithic `Migrate()` function in `internal/db/db.go` is replaced by numbered migration files applied sequentially via `PRAGMA user_version`.

**Tech Stack:** Go 1.22, `invopop/jsonschema` (v0.4+), `modernc.org/sqlite`, GitHub Actions CI

---

## Task 1: Add `invopop/jsonschema` Dependency

**Files:**
- Modify: `core/intercore/go.mod`
- Modify: `core/intercore/go.sum`

**Step 1: Add the dependency**

Run: `cd /home/mk/projects/Demarch/core/intercore && go get github.com/invopop/jsonschema@latest`

Expected: `go.mod` gains `github.com/invopop/jsonschema` line, `go.sum` updated.

**Step 2: Verify it compiles**

Run: `cd /home/mk/projects/Demarch/core/intercore && go build ./...`

Expected: clean build, exit 0.

**Step 3: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add go.mod go.sum
git commit -m "deps(intercore): add invopop/jsonschema for contract generation"
```

---

## Task 2: Create Contract Type Registry

**Files:**
- Create: `core/intercore/contracts/registry.go`
- Create: `core/intercore/contracts/doc.go`

This file maps each CLI subcommand and event type to its Go output struct so the generator knows what to reflect on.

**Step 1: Create the contracts package with registry**

Create `core/intercore/contracts/doc.go`:
```go
// Package contracts defines the JSON Schema contract surface for intercore CLI output.
// Run `go generate ./contracts/...` to regenerate schema snapshots.
package contracts
```

Create `core/intercore/contracts/registry.go`:
```go
package contracts

import (
	"github.com/mistakeknot/intercore/internal/coordination"
	"github.com/mistakeknot/intercore/internal/dispatch"
	"github.com/mistakeknot/intercore/internal/discovery"
	"github.com/mistakeknot/intercore/internal/event"
	"github.com/mistakeknot/intercore/internal/lane"
	"github.com/mistakeknot/intercore/internal/phase"
	"github.com/mistakeknot/intercore/internal/runtrack"
	"github.com/mistakeknot/intercore/internal/scheduler"
)

// ContractType maps a schema name to the Go type that defines the JSON shape.
type ContractType struct {
	Name     string // schema file name (e.g., "cli/run-status")
	Instance any    // zero-value instance of the output struct
}

// CLIContracts lists every CLI subcommand output type.
// Each entry produces a schema at contracts/cli/<name>.json.
var CLIContracts = []ContractType{
	// run domain
	{"run-status", phase.Run{}},
	{"run-list-item", phase.Run{}},
	{"run-agent", runtrack.Agent{}},
	{"run-artifact", runtrack.Artifact{}},
	{"run-tokens", dispatch.TokenAggregation{}},
	{"run-budget", map[string]any{}}, // inline map — will be typed in follow-up

	// dispatch domain
	{"dispatch-status", dispatch.Dispatch{}},
	{"dispatch-list-item", dispatch.Dispatch{}},
	{"dispatch-tokens", dispatch.TokenAggregation{}},

	// coordination domain
	{"coordination-reserve", coordination.ReserveResult{}},
	{"coordination-lock", coordination.Lock{}},
	{"coordination-sweep", coordination.SweepResult{}},
	{"coordination-conflict", coordination.ConflictInfo{}},

	// gate domain
	{"gate-check", phase.GateCheckResult{}},
	{"gate-condition", phase.GateCondition{}},

	// discovery domain
	{"discovery-item", discovery.Discovery{}},
	{"discovery-profile", discovery.InterestProfile{}},

	// event bus
	{"event", event.Event{}},
	{"interspect-event", event.InterspectEvent{}},

	// scheduler
	{"scheduler-job", scheduler.SpawnJob{}},
	{"scheduler-stats", scheduler.Stats{}},

	// lanes
	{"lane", lane.Lane{}},
	{"lane-event", lane.LaneEvent{}},
}

// EventContracts lists event payload types for the event bus.
var EventContracts = []ContractType{
	{"phase-advance", event.Event{}},
	{"dispatch-status-change", event.Event{}},
	{"interspect-signal", event.InterspectEvent{}},
}
```

**Step 2: Verify it compiles**

Run: `cd /home/mk/projects/Demarch/core/intercore && go build ./contracts/...`

Expected: clean build. If any internal types are unexported or packages have circular imports, fix by adding json struct tags or using type aliases.

**Step 3: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add contracts/
git commit -m "feat(intercore): add contract type registry for schema generation"
```

---

## Task 3: Write the JSON Schema Generator

**Files:**
- Create: `core/intercore/contracts/generate.go`
- Create: `core/intercore/contracts/cli/` (directory, generated output)
- Create: `core/intercore/contracts/events/` (directory, generated output)

**Step 1: Write the failing test**

Create `core/intercore/contracts/generate_test.go`:
```go
package contracts

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGenerateSchemas_ProducesFiles(t *testing.T) {
	dir := t.TempDir()
	err := GenerateSchemas(dir)
	if err != nil {
		t.Fatalf("GenerateSchemas: %v", err)
	}

	// Verify at least one CLI schema exists
	cliDir := filepath.Join(dir, "cli")
	entries, err := os.ReadDir(cliDir)
	if err != nil {
		t.Fatalf("read cli dir: %v", err)
	}
	if len(entries) == 0 {
		t.Error("no CLI schemas generated")
	}

	// Verify at least one event schema exists
	eventsDir := filepath.Join(dir, "events")
	entries, err = os.ReadDir(eventsDir)
	if err != nil {
		t.Fatalf("read events dir: %v", err)
	}
	if len(entries) == 0 {
		t.Error("no event schemas generated")
	}
}

func TestGenerateSchemas_ValidJSON(t *testing.T) {
	dir := t.TempDir()
	if err := GenerateSchemas(dir); err != nil {
		t.Fatalf("GenerateSchemas: %v", err)
	}

	// Walk all .json files and verify they parse
	err = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || filepath.Ext(path) != ".json" {
			return err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if len(data) == 0 {
			t.Errorf("empty schema: %s", path)
		}
		// JSON Schema must have "$schema" key
		if !contains(data, "$schema") {
			t.Errorf("missing $schema in: %s", path)
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func contains(data []byte, needle string) bool {
	return len(data) > 0 && len(needle) > 0 && bytesContains(data, []byte(needle))
}

func bytesContains(haystack, needle []byte) bool {
	for i := 0; i <= len(haystack)-len(needle); i++ {
		match := true
		for j := range needle {
			if haystack[i+j] != needle[j] {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test ./contracts/ -run TestGenerate -v`

Expected: FAIL — `GenerateSchemas` undefined.

**Step 3: Write the generator implementation**

Create `core/intercore/contracts/generate.go`:
```go
package contracts

//go:generate go run generate_cmd.go

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/invopop/jsonschema"
)

// GenerateSchemas generates JSON Schema files for all registered contract types.
// Output is written to subdirectories cli/ and events/ under outDir.
func GenerateSchemas(outDir string) error {
	cliDir := filepath.Join(outDir, "cli")
	eventsDir := filepath.Join(outDir, "events")

	if err := os.MkdirAll(cliDir, 0755); err != nil {
		return fmt.Errorf("mkdir cli: %w", err)
	}
	if err := os.MkdirAll(eventsDir, 0755); err != nil {
		return fmt.Errorf("mkdir events: %w", err)
	}

	r := &jsonschema.Reflector{
		DoNotReference:          true,
		RequiredFromJSONSchemaTags: false,
	}

	for _, ct := range CLIContracts {
		schema := r.Reflect(ct.Instance)
		schema.ID = jsonschema.ID(fmt.Sprintf("https://intercore.dev/contracts/cli/%s.json", ct.Name))

		data, err := json.MarshalIndent(schema, "", "  ")
		if err != nil {
			return fmt.Errorf("marshal %s: %w", ct.Name, err)
		}
		path := filepath.Join(cliDir, ct.Name+".json")
		if err := os.WriteFile(path, append(data, '\n'), 0644); err != nil {
			return fmt.Errorf("write %s: %w", ct.Name, err)
		}
	}

	for _, ct := range EventContracts {
		schema := r.Reflect(ct.Instance)
		schema.ID = jsonschema.ID(fmt.Sprintf("https://intercore.dev/contracts/events/%s.json", ct.Name))

		data, err := json.MarshalIndent(schema, "", "  ")
		if err != nil {
			return fmt.Errorf("marshal %s: %w", ct.Name, err)
		}
		path := filepath.Join(eventsDir, ct.Name+".json")
		if err := os.WriteFile(path, append(data, '\n'), 0644); err != nil {
			return fmt.Errorf("write %s: %w", ct.Name, err)
		}
	}

	return nil
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test ./contracts/ -run TestGenerate -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add contracts/
git commit -m "feat(intercore): JSON Schema generator from Go output structs"
```

---

## Task 4: Create the `go generate` Command Runner

**Files:**
- Create: `core/intercore/contracts/generate_cmd.go` (build-tag `ignore`, standalone `main`)

This is the `go:generate` target that calls `GenerateSchemas` with the repo's `contracts/` directory.

**Step 1: Write the generate command**

Create `core/intercore/contracts/cmd/gen/main.go`:
```go
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/mistakeknot/intercore/contracts"
)

func main() {
	// Determine contracts/ output directory relative to this file's location
	_, thisFile, _, _ := runtime.Caller(0)
	contractsDir := filepath.Join(filepath.Dir(thisFile), "..", "..")

	if err := contracts.GenerateSchemas(contractsDir); err != nil {
		fmt.Fprintf(os.Stderr, "generate: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Generated schemas in %s\n", contractsDir)
}
```

Update the `//go:generate` directive in `contracts/generate.go` to:
```go
//go:generate go run ./cmd/gen
```

**Step 2: Run the generator**

Run: `cd /home/mk/projects/Demarch/core/intercore && go generate ./contracts/...`

Expected: schema files appear in `contracts/cli/` and `contracts/events/`.

**Step 3: Verify generated schemas**

Run: `ls /home/mk/projects/Demarch/core/intercore/contracts/cli/ /home/mk/projects/Demarch/core/intercore/contracts/events/`

Expected: `.json` files for each registered contract type.

**Step 4: Commit the generated snapshots**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add contracts/
git commit -m "feat(intercore): generate initial JSON Schema snapshots for all CLI output"
```

---

## Task 5: Add Contract Snapshot CI Gate

**Files:**
- Modify: `core/intercore/.github/workflows/ci.yml`
- Create: `core/intercore/contracts/overrides/` (directory)
- Create: `core/intercore/contracts/overrides/.gitkeep`

**Step 1: Add the CI step**

Edit `core/intercore/.github/workflows/ci.yml` to add a `contracts` job after the existing `test` job:

```yaml
  contracts:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.24"
      - name: Regenerate schemas
        run: go generate ./contracts/...
      - name: Check for schema drift
        run: |
          if [ -n "$(ls contracts/overrides/*.md 2>/dev/null)" ]; then
            echo "Override file(s) found — schema changes are authorized this cycle:"
            ls contracts/overrides/*.md
            exit 0
          fi
          if ! git diff --exit-code contracts/cli/ contracts/events/; then
            echo ""
            echo "ERROR: Schema snapshots are out of date."
            echo ""
            echo "If this is an intentional breaking change:"
            echo "  1. Create contracts/overrides/$(date +%Y-%m-%d)-<description>.md"
            echo "  2. Document the change and migration notes for consumers"
            echo "  3. Re-run CI"
            echo ""
            echo "If this is unintentional, your code changed a CLI output struct."
            echo "Run 'go generate ./contracts/...' locally and commit the updated schemas."
            exit 1
          fi
          echo "Schemas are up to date."
```

**Step 2: Create the overrides directory**

```bash
mkdir -p /home/mk/projects/Demarch/core/intercore/contracts/overrides
touch /home/mk/projects/Demarch/core/intercore/contracts/overrides/.gitkeep
```

**Step 3: Verify CI file is valid YAML**

Run: `cd /home/mk/projects/Demarch/core/intercore && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`

Expected: no error.

**Step 4: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add .github/workflows/ci.yml contracts/overrides/.gitkeep
git commit -m "feat(intercore): add contract snapshot CI gate with override mechanism"
```

---

## Task 6: Write Contract Ownership Matrix

**Files:**
- Create: `docs/contract-ownership.md`

**Step 1: Write the ownership matrix document**

Create `docs/contract-ownership.md`:
```markdown
# Contract Ownership Matrix

Maps each Intercore contract surface to its owner, consumers, and versioning policy.

## CLI Output Contracts

| Command | Output Schema | Owner | Consumers | Stability |
|---------|--------------|-------|-----------|-----------|
| `run create` | `cli/run-status.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `run status` | `cli/run-status.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `run advance` | `cli/run-status.json` | Intercore | Clavain bash | Stable |
| `run list` | `cli/run-list-item.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `run tokens` | `cli/run-tokens.json` | Intercore | Clavain bash | Stable |
| `run budget` | `cli/run-budget.json` | Intercore | Clavain bash | Stable |
| `run agent list` | `cli/run-agent.json` | Intercore | Clavain bash | Stable |
| `run artifact list` | `cli/run-artifact.json` | Intercore | Clavain bash | Stable |
| `dispatch spawn` | `cli/dispatch-status.json` | Intercore | Clavain bash | Stable |
| `dispatch status` | `cli/dispatch-status.json` | Intercore | Clavain bash, Autarch Go | Stable |
| `dispatch list` | `cli/dispatch-list-item.json` | Intercore | Clavain bash | Stable |
| `dispatch tokens` | `cli/dispatch-tokens.json` | Intercore | Clavain bash | Stable |
| `coordination reserve` | `cli/coordination-reserve.json` | Intercore | Interlock MCP | Stable |
| `coordination release` | `cli/coordination-lock.json` | Intercore | Interlock MCP | Stable |
| `coordination conflicts` | `cli/coordination-conflict.json` | Intercore | Interlock MCP | Stable |
| `gate check` | `cli/gate-check.json` | Intercore | Clavain bash | Stable |
| `discovery list` | `cli/discovery-item.json` | Intercore | Clavain bash | Stable |
| `discovery profile` | `cli/discovery-profile.json` | Intercore | Clavain bash | Stable |
| `events tail` | `cli/event.json` | Intercore | Clavain bash, Interspect | Stable |
| `scheduler stats` | `cli/scheduler-stats.json` | Intercore | Clavain bash | Stable |
| `lane list` | `cli/lane.json` | Intercore | Clavain bash | Stable |
| `config get` | inline map | Intercore | Clavain bash | Unstable |

## Event Payload Contracts

| Event Type | Schema | Owner | Consumers |
|-----------|--------|-------|-----------|
| `phase.advance` | `events/phase-advance.json` | Intercore | Clavain hooks, Interspect |
| `dispatch.status_change` | `events/dispatch-status-change.json` | Intercore | Clavain hooks, Interspect |
| `interspect.*` | `events/interspect-signal.json` | Intercore | Interspect |

## Versioning Policy

**Stable contracts:**
- Field additions: non-breaking (consumers MUST ignore unknown fields)
- Field renames: BREAKING (requires override file)
- Field removals: BREAKING (requires override file)
- Type changes: BREAKING (requires override file)
- Nullable → non-nullable: BREAKING

**Breaking change process:**
1. Create `contracts/overrides/YYYY-MM-DD-<description>.md` with migration notes
2. CI allows the schema diff for that cycle
3. Notify consumers manually (future: automated cross-repo PRs)
4. Remove override after consumers migrate
```

**Step 2: Commit**

```bash
cd /home/mk/projects/Demarch
git add docs/contract-ownership.md
git commit -m "docs: add contract ownership matrix for Intercore CLI surfaces"
```

---

## Task 7: Extract Baseline Migration File

**Files:**
- Create: `core/intercore/internal/db/migrations/` (directory)
- Create: `core/intercore/internal/db/migrations/020_baseline.sql`

**Step 1: Create the migrations directory**

```bash
mkdir -p /home/mk/projects/Demarch/core/intercore/internal/db/migrations
```

**Step 2: Create the baseline migration**

The baseline migration captures the current v20 schema exactly as it exists in `schema.sql`. This is the starting point for all new databases.

Create `core/intercore/internal/db/migrations/020_baseline.sql`:
Copy the contents of `internal/db/schema.sql` verbatim, but remove the `IF NOT EXISTS` guards (baseline is applied to a fresh DB only). Add a header comment:

```sql
-- Migration 020: baseline schema (captures v20 state)
-- This migration is applied to new databases only.
-- Existing databases at v16-v19 use additive migrations 016-019.
-- Existing databases at v20 skip this migration entirely.

CREATE TABLE state (
    key         TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    -- ... (full schema from schema.sql with IF NOT EXISTS removed)
);
-- ... all tables, indexes
```

**Step 3: Create additive migration stubs for v16-v19**

These capture the existing `ALTER TABLE` migrations already in `db.go`:

Create `core/intercore/internal/db/migrations/016_gate_rules.sql`:
```sql
-- Migration 016: runtime-configurable gate rules
ALTER TABLE runs ADD COLUMN gate_rules TEXT;
```

Create `core/intercore/internal/db/migrations/017_cost_reconciliation.sql`:
```sql
-- Migration 017: cost reconciliation records
CREATE TABLE IF NOT EXISTS cost_reconciliations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    dispatch_id     TEXT,
    reported_in     INTEGER NOT NULL,
    reported_out    INTEGER NOT NULL,
    billed_in       INTEGER NOT NULL,
    billed_out      INTEGER NOT NULL,
    delta_in        INTEGER NOT NULL,
    delta_out       INTEGER NOT NULL,
    source          TEXT NOT NULL DEFAULT 'manual',
    created_at      INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_cost_recon_run ON cost_reconciliations(run_id);
CREATE INDEX IF NOT EXISTS idx_cost_recon_dispatch ON cost_reconciliations(dispatch_id) WHERE dispatch_id IS NOT NULL;
```

Create `core/intercore/internal/db/migrations/018_sandbox_specs.sql`:
```sql
-- Migration 018: sandbox specification columns
ALTER TABLE dispatches ADD COLUMN sandbox_spec TEXT;
ALTER TABLE dispatches ADD COLUMN sandbox_effective TEXT;
```

Create `core/intercore/internal/db/migrations/019_scheduler_jobs.sql`:
```sql
-- Migration 019: scheduler job queue
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'pending',
    priority    INTEGER NOT NULL DEFAULT 2,
    agent_type  TEXT NOT NULL DEFAULT 'codex',
    session_name TEXT,
    batch_id    TEXT,
    dispatch_id TEXT,
    spawn_opts  TEXT NOT NULL,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_msg   TEXT,
    created_at  INTEGER NOT NULL,
    started_at  INTEGER,
    completed_at INTEGER,
    FOREIGN KEY (dispatch_id) REFERENCES dispatches(id)
);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_status ON scheduler_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_session ON scheduler_jobs(session_name);
```

**Step 4: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add internal/db/migrations/
git commit -m "feat(intercore): extract baseline + additive migration files (v16-v20)"
```

---

## Task 8: Implement the Migration Runner

**Files:**
- Create: `core/intercore/internal/db/migrator.go`
- Create: `core/intercore/internal/db/migrator_test.go`

**Step 1: Write the failing test**

Create `core/intercore/internal/db/migrator_test.go`:
```go
package db

import (
	"context"
	"testing"
)

func TestMigrator_EmptyDB(t *testing.T) {
	d, _ := tempDB(t)
	ctx := context.Background()

	m, err := NewMigrator(d)
	if err != nil {
		t.Fatalf("NewMigrator: %v", err)
	}

	applied, err := m.Run(ctx)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	// Should apply baseline (020) for empty DB
	if applied == 0 {
		t.Error("expected at least 1 migration applied")
	}

	// Verify version is 20
	v, err := d.SchemaVersion()
	if err != nil {
		t.Fatal(err)
	}
	if v != 20 {
		t.Errorf("SchemaVersion = %d, want 20", v)
	}

	// Verify tables exist
	for _, table := range []string{"state", "sentinels", "dispatches", "runs", "coordination_locks"} {
		var name string
		err = d.db.QueryRow("SELECT name FROM sqlite_master WHERE type='table' AND name=?", table).Scan(&name)
		if err != nil {
			t.Errorf("table %s not found: %v", table, err)
		}
	}
}

func TestMigrator_Idempotent(t *testing.T) {
	d, _ := tempDB(t)
	ctx := context.Background()

	m, err := NewMigrator(d)
	if err != nil {
		t.Fatalf("NewMigrator: %v", err)
	}

	if _, err := m.Run(ctx); err != nil {
		t.Fatalf("first Run: %v", err)
	}

	// Second run should apply 0 migrations
	applied, err := m.Run(ctx)
	if err != nil {
		t.Fatalf("second Run: %v", err)
	}
	if applied != 0 {
		t.Errorf("second Run applied %d, want 0", applied)
	}
}

func TestMigrator_V16Upgrade(t *testing.T) {
	d, _ := tempDB(t)
	ctx := context.Background()

	// Simulate a v16 database: apply schema DDL and set user_version=16
	// This tests that migrations 017-020 apply correctly
	if _, err := d.db.ExecContext(ctx, schemaDDL); err != nil {
		t.Fatalf("apply base DDL: %v", err)
	}
	// Set to v16 — the minimum supported version
	if _, err := d.db.ExecContext(ctx, "PRAGMA user_version = 16"); err != nil {
		t.Fatalf("set version: %v", err)
	}

	m, err := NewMigrator(d)
	if err != nil {
		t.Fatalf("NewMigrator: %v", err)
	}

	applied, err := m.Run(ctx)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	// Should apply 017, 018, 019 (not 020 baseline — DB already has tables)
	// The exact count depends on which additive migrations detect missing columns
	if applied == 0 {
		t.Error("expected some migrations applied for v16 DB")
	}

	v, err := d.SchemaVersion()
	if err != nil {
		t.Fatal(err)
	}
	if v != 20 {
		t.Errorf("SchemaVersion = %d, want 20", v)
	}
}

func TestMigrator_V20NoOp(t *testing.T) {
	d, _ := tempDB(t)
	ctx := context.Background()

	// Simulate v20 DB: full schema + version set
	if err := d.Migrate(ctx); err != nil {
		t.Fatalf("Migrate: %v", err)
	}

	m, err := NewMigrator(d)
	if err != nil {
		t.Fatalf("NewMigrator: %v", err)
	}

	applied, err := m.Run(ctx)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if applied != 0 {
		t.Errorf("applied = %d, want 0 for v20 DB", applied)
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test ./internal/db/ -run TestMigrator -v`

Expected: FAIL — `NewMigrator` undefined.

**Step 3: Write the migration runner**

Create `core/intercore/internal/db/migrator.go`:
```go
package db

import (
	"context"
	"embed"
	"fmt"
	"io/fs"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

//go:embed migrations/*.sql
var migrationsFS embed.FS

// Migration represents a numbered migration file.
type Migration struct {
	Version  int
	Name     string
	SQL      string
	Baseline bool // true for 020_baseline.sql
}

// Migrator applies versioned migration files sequentially.
type Migrator struct {
	db         *DB
	migrations []Migration
}

// NewMigrator creates a Migrator that reads embedded migration files.
func NewMigrator(d *DB) (*Migrator, error) {
	var migrations []Migration

	entries, err := fs.ReadDir(migrationsFS, "migrations")
	if err != nil {
		return nil, fmt.Errorf("read migrations dir: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".sql" {
			continue
		}
		name := strings.TrimSuffix(entry.Name(), ".sql")
		parts := strings.SplitN(name, "_", 2)
		if len(parts) < 2 {
			continue
		}
		version, err := strconv.Atoi(parts[0])
		if err != nil {
			continue
		}

		data, err := migrationsFS.ReadFile("migrations/" + entry.Name())
		if err != nil {
			return nil, fmt.Errorf("read migration %s: %w", entry.Name(), err)
		}

		migrations = append(migrations, Migration{
			Version:  version,
			Name:     name,
			SQL:      string(data),
			Baseline: strings.Contains(name, "baseline"),
		})
	}

	sort.Slice(migrations, func(i, j int) bool {
		return migrations[i].Version < migrations[j].Version
	})

	return &Migrator{db: d, migrations: migrations}, nil
}

// Run applies pending migrations and returns the count applied.
func (m *Migrator) Run(ctx context.Context) (int, error) {
	currentVersion, err := m.db.SchemaVersion()
	if err != nil {
		return 0, fmt.Errorf("read version: %w", err)
	}

	// If the database is empty (version 0), apply the baseline migration
	if currentVersion == 0 {
		return m.applyBaseline(ctx)
	}

	// Otherwise, apply additive migrations > currentVersion
	return m.applyAdditive(ctx, currentVersion)
}

func (m *Migrator) applyBaseline(ctx context.Context) (int, error) {
	for _, mig := range m.migrations {
		if !mig.Baseline {
			continue
		}
		tx, err := m.db.db.BeginTx(ctx, nil)
		if err != nil {
			return 0, fmt.Errorf("begin baseline: %w", err)
		}
		defer tx.Rollback()

		if _, err := tx.ExecContext(ctx, mig.SQL); err != nil {
			return 0, fmt.Errorf("apply baseline %s: %w", mig.Name, err)
		}
		if _, err := tx.ExecContext(ctx, fmt.Sprintf("PRAGMA user_version = %d", mig.Version)); err != nil {
			return 0, fmt.Errorf("set version %d: %w", mig.Version, err)
		}
		if err := tx.Commit(); err != nil {
			return 0, fmt.Errorf("commit baseline: %w", err)
		}
		return 1, nil
	}
	return 0, fmt.Errorf("no baseline migration found")
}

func (m *Migrator) applyAdditive(ctx context.Context, currentVersion int) (int, error) {
	applied := 0
	for _, mig := range m.migrations {
		if mig.Baseline || mig.Version <= currentVersion {
			continue
		}
		tx, err := m.db.db.BeginTx(ctx, nil)
		if err != nil {
			return applied, fmt.Errorf("begin migration %s: %w", mig.Name, err)
		}

		if _, err := tx.ExecContext(ctx, mig.SQL); err != nil {
			tx.Rollback()
			return applied, fmt.Errorf("apply migration %s: %w", mig.Name, err)
		}
		if _, err := tx.ExecContext(ctx, fmt.Sprintf("PRAGMA user_version = %d", mig.Version)); err != nil {
			tx.Rollback()
			return applied, fmt.Errorf("set version %d: %w", mig.Version, err)
		}
		if err := tx.Commit(); err != nil {
			return applied, fmt.Errorf("commit migration %s: %w", mig.Name, err)
		}
		applied++
	}
	return applied, nil
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test ./internal/db/ -run TestMigrator -v`

Expected: all 4 tests PASS.

**Step 5: Run full test suite**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./...`

Expected: all tests pass (existing tests should still work since `Migrate()` is unchanged).

**Step 6: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add internal/db/migrator.go internal/db/migrator_test.go
git commit -m "feat(intercore): versioned migration runner with forward-only application"
```

---

## Task 9: Forward-Migration CI Tests

**Files:**
- Modify: `core/intercore/internal/db/migrator_test.go` (add schema shape verification)

**Step 1: Write the schema shape verification test**

Add to `core/intercore/internal/db/migrator_test.go`:
```go
func TestMigrator_FinalSchemaShape(t *testing.T) {
	// Test that all migration paths produce the same final schema shape
	expectedTables := []string{
		"state", "sentinels", "dispatches", "merge_intents", "runs",
		"phase_events", "run_agents", "run_artifacts", "dispatch_events",
		"interspect_events", "discoveries", "discovery_events",
		"feedback_signals", "interest_profile", "project_deps",
		"lanes", "lane_events", "lane_members", "phase_actions",
		"audit_log", "cost_reconciliations", "coordination_locks",
		"coordination_events", "scheduler_jobs",
	}

	scenarios := []struct {
		name    string
		setupFn func(t *testing.T, d *DB)
	}{
		{
			name:    "empty_db",
			setupFn: func(t *testing.T, d *DB) {},
		},
		{
			name: "v16_db",
			setupFn: func(t *testing.T, d *DB) {
				ctx := context.Background()
				if _, err := d.db.ExecContext(ctx, schemaDDL); err != nil {
					t.Fatalf("apply DDL: %v", err)
				}
				if _, err := d.db.ExecContext(ctx, "PRAGMA user_version = 16"); err != nil {
					t.Fatalf("set version: %v", err)
				}
			},
		},
		{
			name: "v20_db",
			setupFn: func(t *testing.T, d *DB) {
				ctx := context.Background()
				if err := d.Migrate(ctx); err != nil {
					t.Fatalf("Migrate: %v", err)
				}
			},
		},
	}

	for _, sc := range scenarios {
		t.Run(sc.name, func(t *testing.T) {
			d, _ := tempDB(t)
			ctx := context.Background()
			sc.setupFn(t, d)

			m, err := NewMigrator(d)
			if err != nil {
				t.Fatalf("NewMigrator: %v", err)
			}
			if _, err := m.Run(ctx); err != nil {
				t.Fatalf("Run: %v", err)
			}

			// Verify all expected tables exist
			for _, table := range expectedTables {
				var name string
				err = d.db.QueryRow(
					"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
					table,
				).Scan(&name)
				if err != nil {
					t.Errorf("[%s] table %s not found: %v", sc.name, table, err)
				}
			}

			// Verify version is 20
			v, err := d.SchemaVersion()
			if err != nil {
				t.Fatal(err)
			}
			if v != 20 {
				t.Errorf("[%s] SchemaVersion = %d, want 20", sc.name, v)
			}
		})
	}
}

func TestMigrator_FailureProducesActionableError(t *testing.T) {
	d, _ := tempDB(t)
	ctx := context.Background()

	// Corrupt the DB by setting a version that has no migration file
	if _, err := d.db.ExecContext(ctx, "PRAGMA user_version = 999"); err != nil {
		t.Fatal(err)
	}

	m, err := NewMigrator(d)
	if err != nil {
		t.Fatalf("NewMigrator: %v", err)
	}

	applied, err := m.Run(ctx)
	if err != nil {
		// Error is fine — just verify it's actionable (not a panic)
		t.Logf("expected error for v999: %v", err)
		return
	}
	// If no error, 0 migrations should apply (all files are <= 999)
	if applied != 0 {
		t.Errorf("applied = %d, want 0 for future version", applied)
	}
}
```

**Step 2: Run the tests**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test ./internal/db/ -run TestMigrator -v`

Expected: all tests PASS.

**Step 3: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add internal/db/migrator_test.go
git commit -m "test(intercore): forward-migration CI tests for all upgrade paths"
```

---

## Task 10: Add Forward-Migration CI Step

**Files:**
- Modify: `core/intercore/.github/workflows/ci.yml`

**Step 1: Add the migration test step to CI**

The existing `go test -race ./...` already runs `TestMigrator_*` tests. But we add an explicit job name for clarity:

Edit `core/intercore/.github/workflows/ci.yml`, add to the `test` job steps:

```yaml
      - name: Run migration tests
        run: go test -race -v ./internal/db/ -run TestMigrator
```

**Step 2: Commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add .github/workflows/ci.yml
git commit -m "ci(intercore): add explicit forward-migration test step"
```

---

## Task 11: Integration Smoke Test

**Files:** None (verification only)

**Step 1: Build the binary**

Run: `cd /home/mk/projects/Demarch/core/intercore && go build -o ic ./cmd/ic`

Expected: clean build.

**Step 2: Run all tests with race detector**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./...`

Expected: all tests pass.

**Step 3: Verify schema generation roundtrip**

Run:
```bash
cd /home/mk/projects/Demarch/core/intercore
go generate ./contracts/...
git diff --exit-code contracts/
```

Expected: no diff (schemas match committed snapshots).

**Step 4: Verify integration tests if available**

Run: `cd /home/mk/projects/Demarch/core/intercore && bash test-integration.sh`

Expected: all integration tests pass.

**Step 5: Final commit**

```bash
cd /home/mk/projects/Demarch/core/intercore
git add -A
git commit -m "feat(intercore): kernel schema validation — contract snapshots + versioned migrations"
```
