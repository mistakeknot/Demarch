# Event-Driven Advancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Make the intercore kernel the router for sprint phase transitions — `ic run advance` returns resolved actions so callers know what command to dispatch next.

**Architecture:** New `phase_actions` table (schema v14) with Go store in `internal/action/`. CLI surface via `ic run action` subcommands. Template variable resolution (`${artifact:*}`) at advance time in `cmd/ic/run.go`. Backward-compatible: no actions registered = no actions returned.

**Tech Stack:** Go 1.22, SQLite (modernc.org/sqlite), bash (lib-sprint.sh)

---

### Task 1: Schema — Add `phase_actions` table (v14 migration)

**Files:**
- Modify: `infra/intercore/internal/db/schema.sql` (append table DDL)
- Modify: `infra/intercore/internal/db/db.go:21-24` (bump version constants)

**Step 1: Add phase_actions DDL to schema.sql**

Append after the lane tables (line 274):

```sql
-- v14: phase actions (event-driven advancement)
CREATE TABLE IF NOT EXISTS phase_actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL REFERENCES runs(id),
    phase       TEXT NOT NULL,
    action_type TEXT NOT NULL DEFAULT 'command',
    command     TEXT NOT NULL,
    args        TEXT,
    mode        TEXT NOT NULL DEFAULT 'interactive',
    priority    INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    UNIQUE(run_id, phase, command)
);
CREATE INDEX IF NOT EXISTS idx_phase_actions_run ON phase_actions(run_id);
CREATE INDEX IF NOT EXISTS idx_phase_actions_phase ON phase_actions(run_id, phase);
```

**Step 2: Bump schema version constants in db.go**

In `db.go`, change:
```go
const (
    currentSchemaVersion = 14
    maxSchemaVersion     = 14
)
```

No migration stanza needed — `phase_actions` is a new table, so `CREATE TABLE IF NOT EXISTS` in the DDL handles both fresh installs and upgrades. The DDL is applied unconditionally during `Migrate()` (line 236).

**Step 3: Verify migration works**

Run: `cd infra/intercore && go build -o /tmp/ic-test ./cmd/ic && /tmp/ic-test init --db=/tmp/test-v14/.clavain/intercore.db`
Expected: exits 0, `PRAGMA user_version` returns 14.

Run: `cd infra/intercore && go test ./internal/db/ -v -run TestMigrate`
Expected: PASS (existing migration tests still pass with new version)

**Step 4: Commit**

```bash
cd infra/intercore && git add internal/db/schema.sql internal/db/db.go
git commit -m "feat(intercore): phase_actions table — schema v14 (iv-otvb)"
```

---

### Task 2: Store — Action CRUD in `internal/action/`

**Files:**
- Create: `infra/intercore/internal/action/action.go` (types)
- Create: `infra/intercore/internal/action/store.go` (CRUD)
- Create: `infra/intercore/internal/action/store_test.go` (unit tests)

**Step 1: Write the failing test**

Create `infra/intercore/internal/action/store_test.go`:

```go
package action

import (
	"context"
	"database/sql"
	"testing"

	_ "modernc.org/sqlite"
)

func setupTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	if _, err := db.Exec("PRAGMA foreign_keys = ON"); err != nil {
		t.Fatal(err)
	}
	// Minimal schema: runs table (FK target) + phase_actions
	if _, err := db.Exec(`
		CREATE TABLE runs (
			id TEXT PRIMARY KEY,
			project_dir TEXT NOT NULL DEFAULT '.',
			goal TEXT NOT NULL DEFAULT '',
			status TEXT NOT NULL DEFAULT 'active',
			phase TEXT NOT NULL DEFAULT 'brainstorm',
			complexity INTEGER NOT NULL DEFAULT 3,
			force_full INTEGER NOT NULL DEFAULT 0,
			auto_advance INTEGER NOT NULL DEFAULT 1,
			created_at INTEGER NOT NULL DEFAULT 0,
			updated_at INTEGER NOT NULL DEFAULT 0
		);
		CREATE TABLE run_artifacts (
			id TEXT PRIMARY KEY,
			run_id TEXT NOT NULL REFERENCES runs(id),
			phase TEXT NOT NULL,
			path TEXT NOT NULL,
			type TEXT NOT NULL DEFAULT 'file',
			status TEXT NOT NULL DEFAULT 'active',
			created_at INTEGER NOT NULL DEFAULT 0
		);
		CREATE TABLE phase_actions (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id TEXT NOT NULL REFERENCES runs(id),
			phase TEXT NOT NULL,
			action_type TEXT NOT NULL DEFAULT 'command',
			command TEXT NOT NULL,
			args TEXT,
			mode TEXT NOT NULL DEFAULT 'interactive',
			priority INTEGER NOT NULL DEFAULT 0,
			created_at INTEGER NOT NULL DEFAULT 0,
			updated_at INTEGER NOT NULL DEFAULT 0,
			UNIQUE(run_id, phase, command)
		);
		INSERT INTO runs (id) VALUES ('test-run-1');
	`); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return db
}

func TestAddAndList(t *testing.T) {
	db := setupTestDB(t)
	s := New(db)
	ctx := context.Background()

	// Add two actions for same phase
	id1, err := s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/interflux:flux-drive", Args: strPtr(`["${artifact:plan}"]`), Mode: "interactive"})
	if err != nil {
		t.Fatal(err)
	}
	if id1 == 0 {
		t.Fatal("expected non-zero ID")
	}

	_, err = s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/clavain:interpeer", Mode: "both", Priority: 1})
	if err != nil {
		t.Fatal(err)
	}

	actions, err := s.ListForPhase(ctx, "test-run-1", "planned")
	if err != nil {
		t.Fatal(err)
	}
	if len(actions) != 2 {
		t.Fatalf("expected 2 actions, got %d", len(actions))
	}
	// Ordered by priority ASC
	if actions[0].Command != "/interflux:flux-drive" {
		t.Errorf("expected first action to be flux-drive, got %s", actions[0].Command)
	}
}

func TestAddDuplicate(t *testing.T) {
	db := setupTestDB(t)
	s := New(db)
	ctx := context.Background()

	_, err := s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/clavain:work"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/clavain:work"})
	if err == nil {
		t.Fatal("expected duplicate error")
	}
}

func TestUpdate(t *testing.T) {
	db := setupTestDB(t)
	s := New(db)
	ctx := context.Background()

	_, err := s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/interflux:flux-drive", Args: strPtr(`["old.md"]`)})
	if err != nil {
		t.Fatal(err)
	}

	err = s.Update(ctx, "test-run-1", "planned", "/interflux:flux-drive", &ActionUpdate{Args: strPtr(`["new.md"]`)})
	if err != nil {
		t.Fatal(err)
	}

	actions, err := s.ListForPhase(ctx, "test-run-1", "planned")
	if err != nil {
		t.Fatal(err)
	}
	if actions[0].Args == nil || *actions[0].Args != `["new.md"]` {
		t.Errorf("expected updated args, got %v", actions[0].Args)
	}
}

func TestDelete(t *testing.T) {
	db := setupTestDB(t)
	s := New(db)
	ctx := context.Background()

	_, err := s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/clavain:work"})
	if err != nil {
		t.Fatal(err)
	}

	err = s.Delete(ctx, "test-run-1", "planned", "/clavain:work")
	if err != nil {
		t.Fatal(err)
	}

	actions, err := s.ListForPhase(ctx, "test-run-1", "planned")
	if err != nil {
		t.Fatal(err)
	}
	if len(actions) != 0 {
		t.Fatalf("expected 0 actions after delete, got %d", len(actions))
	}
}

func TestListAll(t *testing.T) {
	db := setupTestDB(t)
	s := New(db)
	ctx := context.Background()

	s.Add(ctx, &Action{RunID: "test-run-1", Phase: "planned", Command: "/clavain:work"})
	s.Add(ctx, &Action{RunID: "test-run-1", Phase: "executing", Command: "/clavain:quality-gates"})

	actions, err := s.ListAll(ctx, "test-run-1")
	if err != nil {
		t.Fatal(err)
	}
	if len(actions) != 2 {
		t.Fatalf("expected 2 actions, got %d", len(actions))
	}
}

func TestAddBatch(t *testing.T) {
	db := setupTestDB(t)
	s := New(db)
	ctx := context.Background()

	batch := map[string]*Action{
		"planned":   {Command: "/interflux:flux-drive", Args: strPtr(`["${artifact:plan}"]`), Mode: "interactive"},
		"executing": {Command: "/clavain:quality-gates", Mode: "interactive"},
	}

	err := s.AddBatch(ctx, "test-run-1", batch)
	if err != nil {
		t.Fatal(err)
	}

	all, err := s.ListAll(ctx, "test-run-1")
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != 2 {
		t.Fatalf("expected 2 actions from batch, got %d", len(all))
	}
}

func TestResolveTemplateVars(t *testing.T) {
	db := setupTestDB(t)
	ctx := context.Background()

	// Add an artifact
	_, err := db.Exec(`INSERT INTO run_artifacts (id, run_id, phase, path, type, status) VALUES ('art1', 'test-run-1', 'planned', 'docs/plans/my-plan.md', 'plan', 'active')`)
	if err != nil {
		t.Fatal(err)
	}

	s := New(db)
	_, err = s.Add(ctx, &Action{RunID: "test-run-1", Phase: "plan-reviewed", Command: "/clavain:work", Args: strPtr(`["${artifact:plan}","${run_id}"]`)})
	if err != nil {
		t.Fatal(err)
	}

	actions, err := s.ListForPhaseResolved(ctx, "test-run-1", "plan-reviewed", ".")
	if err != nil {
		t.Fatal(err)
	}
	if len(actions) != 1 {
		t.Fatalf("expected 1 action, got %d", len(actions))
	}
	if actions[0].Args == nil || *actions[0].Args != `["docs/plans/my-plan.md","test-run-1"]` {
		t.Errorf("expected resolved args, got %v", *actions[0].Args)
	}
}

func strPtr(s string) *string { return &s }
```

**Step 2: Run test to verify it fails**

Run: `cd infra/intercore && go test ./internal/action/ -v`
Expected: FAIL — package doesn't exist yet

**Step 3: Write the types file**

Create `infra/intercore/internal/action/action.go`:

```go
package action

// Action represents a phase-triggered action for a run.
type Action struct {
	ID         int64
	RunID      string
	Phase      string
	ActionType string  // "command", "spawn", "hook"
	Command    string  // e.g., "/clavain:work", "/interflux:flux-drive"
	Args       *string // JSON array, may contain ${artifact:<type>} placeholders
	Mode       string  // "interactive", "autonomous", "both"
	Priority   int     // ordering when multiple actions per phase
	CreatedAt  int64
	UpdatedAt  int64
}

// ActionUpdate contains fields that can be updated on an existing action.
type ActionUpdate struct {
	Args     *string
	Mode     *string
	Priority *int
}
```

**Step 4: Write the store**

Create `infra/intercore/internal/action/store.go`:

```go
package action

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"
)

var (
	ErrNotFound  = errors.New("action not found")
	ErrDuplicate = errors.New("duplicate action for run/phase/command")
)

var templateVarRE = regexp.MustCompile(`\$\{artifact:([^}]+)\}`)
var runIDVarRE = regexp.MustCompile(`\$\{run_id\}`)
var projectDirVarRE = regexp.MustCompile(`\$\{project_dir\}`)

// Store provides phase action CRUD operations.
type Store struct {
	db *sql.DB
}

// New creates an action store.
func New(db *sql.DB) *Store {
	return &Store{db: db}
}

// Add inserts a new phase action. Returns the auto-increment ID.
func (s *Store) Add(ctx context.Context, a *Action) (int64, error) {
	if a.ActionType == "" {
		a.ActionType = "command"
	}
	if a.Mode == "" {
		a.Mode = "interactive"
	}
	now := time.Now().Unix()
	result, err := s.db.ExecContext(ctx, `
		INSERT INTO phase_actions (run_id, phase, action_type, command, args, mode, priority, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		a.RunID, a.Phase, a.ActionType, a.Command, a.Args, a.Mode, a.Priority, now, now,
	)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE constraint") {
			return 0, ErrDuplicate
		}
		if strings.Contains(err.Error(), "FOREIGN KEY constraint") {
			return 0, fmt.Errorf("run not found: %s", a.RunID)
		}
		return 0, fmt.Errorf("action add: %w", err)
	}
	return result.LastInsertId()
}

// AddBatch inserts multiple phase actions for a run in a single transaction.
// The map key is the phase name.
func (s *Store) AddBatch(ctx context.Context, runID string, actions map[string]*Action) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("action batch: begin: %w", err)
	}
	defer tx.Rollback()

	now := time.Now().Unix()
	for phase, a := range actions {
		actionType := a.ActionType
		if actionType == "" {
			actionType = "command"
		}
		mode := a.Mode
		if mode == "" {
			mode = "interactive"
		}
		_, err := tx.ExecContext(ctx, `
			INSERT INTO phase_actions (run_id, phase, action_type, command, args, mode, priority, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			runID, phase, actionType, a.Command, a.Args, mode, a.Priority, now, now,
		)
		if err != nil {
			if strings.Contains(err.Error(), "UNIQUE constraint") {
				return fmt.Errorf("duplicate action for phase %s: %s", phase, a.Command)
			}
			return fmt.Errorf("action batch insert %s: %w", phase, err)
		}
	}
	return tx.Commit()
}

// ListForPhase returns actions for a run+phase, ordered by priority ASC.
func (s *Store) ListForPhase(ctx context.Context, runID, phase string) ([]*Action, error) {
	rows, err := s.db.QueryContext(ctx, `
		SELECT id, run_id, phase, action_type, command, args, mode, priority, created_at, updated_at
		FROM phase_actions WHERE run_id = ? AND phase = ? ORDER BY priority ASC, id ASC`,
		runID, phase,
	)
	if err != nil {
		return nil, fmt.Errorf("action list: %w", err)
	}
	defer rows.Close()
	return scanActions(rows)
}

// ListForPhaseResolved returns actions with template variables resolved.
func (s *Store) ListForPhaseResolved(ctx context.Context, runID, phase, projectDir string) ([]*Action, error) {
	actions, err := s.ListForPhase(ctx, runID, phase)
	if err != nil {
		return nil, err
	}
	for _, a := range actions {
		if a.Args != nil {
			resolved := s.resolveTemplateVars(ctx, runID, projectDir, *a.Args)
			a.Args = &resolved
		}
	}
	return actions, nil
}

// ListAll returns all actions for a run, ordered by phase then priority.
func (s *Store) ListAll(ctx context.Context, runID string) ([]*Action, error) {
	rows, err := s.db.QueryContext(ctx, `
		SELECT id, run_id, phase, action_type, command, args, mode, priority, created_at, updated_at
		FROM phase_actions WHERE run_id = ? ORDER BY phase ASC, priority ASC, id ASC`,
		runID,
	)
	if err != nil {
		return nil, fmt.Errorf("action list all: %w", err)
	}
	defer rows.Close()
	return scanActions(rows)
}

// Update modifies an existing action identified by (run_id, phase, command).
func (s *Store) Update(ctx context.Context, runID, phase, command string, upd *ActionUpdate) error {
	var sets []string
	var args []interface{}
	now := time.Now().Unix()

	if upd.Args != nil {
		sets = append(sets, "args = ?")
		args = append(args, *upd.Args)
	}
	if upd.Mode != nil {
		sets = append(sets, "mode = ?")
		args = append(args, *upd.Mode)
	}
	if upd.Priority != nil {
		sets = append(sets, "priority = ?")
		args = append(args, *upd.Priority)
	}
	if len(sets) == 0 {
		return nil // nothing to update
	}

	sets = append(sets, "updated_at = ?")
	args = append(args, now, runID, phase, command)

	query := fmt.Sprintf("UPDATE phase_actions SET %s WHERE run_id = ? AND phase = ? AND command = ?",
		strings.Join(sets, ", "))
	result, err := s.db.ExecContext(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("action update: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// Delete removes an action identified by (run_id, phase, command).
func (s *Store) Delete(ctx context.Context, runID, phase, command string) error {
	result, err := s.db.ExecContext(ctx,
		"DELETE FROM phase_actions WHERE run_id = ? AND phase = ? AND command = ?",
		runID, phase, command,
	)
	if err != nil {
		return fmt.Errorf("action delete: %w", err)
	}
	n, _ := result.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// resolveTemplateVars replaces ${artifact:<type>}, ${run_id}, ${project_dir} in a string.
func (s *Store) resolveTemplateVars(ctx context.Context, runID, projectDir, input string) string {
	// Resolve ${artifact:<type>} — looks up run_artifacts by type
	result := templateVarRE.ReplaceAllStringFunc(input, func(match string) string {
		sub := templateVarRE.FindStringSubmatch(match)
		if len(sub) < 2 {
			return match
		}
		artType := sub[1]
		var path string
		err := s.db.QueryRowContext(ctx,
			`SELECT path FROM run_artifacts WHERE run_id = ? AND type = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1`,
			runID, artType,
		).Scan(&path)
		if err != nil {
			return match // leave unresolved
		}
		return path
	})

	// Resolve ${run_id}
	result = runIDVarRE.ReplaceAllString(result, runID)

	// Resolve ${project_dir}
	result = projectDirVarRE.ReplaceAllString(result, projectDir)

	return result
}

func scanActions(rows *sql.Rows) ([]*Action, error) {
	var actions []*Action
	for rows.Next() {
		a := &Action{}
		var args sql.NullString
		if err := rows.Scan(
			&a.ID, &a.RunID, &a.Phase, &a.ActionType, &a.Command,
			&args, &a.Mode, &a.Priority, &a.CreatedAt, &a.UpdatedAt,
		); err != nil {
			return nil, fmt.Errorf("action scan: %w", err)
		}
		if args.Valid {
			a.Args = &args.String
		}
		actions = append(actions, a)
	}
	return actions, rows.Err()
}
```

**Step 5: Run tests to verify they pass**

Run: `cd infra/intercore && go test ./internal/action/ -v`
Expected: All 7 tests PASS

**Step 6: Commit**

```bash
cd infra/intercore && git add internal/action/
git commit -m "feat(intercore): action store — CRUD + template resolution (iv-otvb)"
```

---

### Task 3: CLI — `ic run action` subcommands

**Files:**
- Create: `infra/intercore/cmd/ic/action.go`
- Modify: `infra/intercore/cmd/ic/run.go:30-64` (add "action" case to cmdRun switch)
- Modify: `infra/intercore/cmd/ic/run.go:67-68` (add `--actions` flag to cmdRunCreate)

**Step 1: Create action.go with add/list/update/delete subcommands**

Create `infra/intercore/cmd/ic/action.go`:

```go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/mistakeknot/interverse/infra/intercore/internal/action"
)

func cmdRunAction(ctx context.Context, args []string) int {
	if len(args) == 0 {
		fmt.Fprintf(os.Stderr, "ic: run action: missing subcommand (add, list, update, delete)\n")
		return 3
	}

	switch args[0] {
	case "add":
		return cmdRunActionAdd(ctx, args[1:])
	case "list":
		return cmdRunActionList(ctx, args[1:])
	case "update":
		return cmdRunActionUpdate(ctx, args[1:])
	case "delete":
		return cmdRunActionDelete(ctx, args[1:])
	default:
		fmt.Fprintf(os.Stderr, "ic: run action: unknown subcommand: %s\n", args[0])
		return 3
	}
}

func cmdRunActionAdd(ctx context.Context, args []string) int {
	var runID, phase, command, argsJSON, mode, actionType string
	priority := 0

	var positional []string
	for _, arg := range args {
		switch {
		case strings.HasPrefix(arg, "--phase="):
			phase = strings.TrimPrefix(arg, "--phase=")
		case strings.HasPrefix(arg, "--command="):
			command = strings.TrimPrefix(arg, "--command=")
		case strings.HasPrefix(arg, "--args="):
			argsJSON = strings.TrimPrefix(arg, "--args=")
		case strings.HasPrefix(arg, "--mode="):
			mode = strings.TrimPrefix(arg, "--mode=")
		case strings.HasPrefix(arg, "--type="):
			actionType = strings.TrimPrefix(arg, "--type=")
		case strings.HasPrefix(arg, "--priority="):
			fmt.Sscanf(strings.TrimPrefix(arg, "--priority="), "%d", &priority)
		default:
			positional = append(positional, arg)
		}
	}

	if len(positional) < 1 {
		fmt.Fprintf(os.Stderr, "ic: run action add: usage: ic run action add <run_id> --phase=<p> --command=<c>\n")
		return 3
	}
	runID = positional[0]

	if phase == "" || command == "" {
		fmt.Fprintf(os.Stderr, "ic: run action add: --phase and --command are required\n")
		return 3
	}

	d, err := openDB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action add: %v\n", err)
		return 2
	}
	defer d.Close()

	s := action.New(d.SqlDB())
	a := &action.Action{
		RunID:      runID,
		Phase:      phase,
		ActionType: actionType,
		Command:    command,
		Mode:       mode,
		Priority:   priority,
	}
	if argsJSON != "" {
		a.Args = &argsJSON
	}

	id, err := s.Add(ctx, a)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action add: %v\n", err)
		if err == action.ErrDuplicate {
			return 1
		}
		return 2
	}

	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(map[string]interface{}{"id": id})
	} else {
		fmt.Printf("Added action %d: %s → %s\n", id, phase, command)
	}
	return 0
}

func cmdRunActionList(ctx context.Context, args []string) int {
	var phase string
	var positional []string

	for _, arg := range args {
		switch {
		case strings.HasPrefix(arg, "--phase="):
			phase = strings.TrimPrefix(arg, "--phase=")
		default:
			positional = append(positional, arg)
		}
	}

	if len(positional) < 1 {
		fmt.Fprintf(os.Stderr, "ic: run action list: usage: ic run action list <run_id> [--phase=<p>]\n")
		return 3
	}
	runID := positional[0]

	d, err := openDB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action list: %v\n", err)
		return 2
	}
	defer d.Close()

	s := action.New(d.SqlDB())

	var actions []*action.Action
	if phase != "" {
		actions, err = s.ListForPhase(ctx, runID, phase)
	} else {
		actions, err = s.ListAll(ctx, runID)
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action list: %v\n", err)
		return 2
	}

	if flagJSON {
		items := make([]map[string]interface{}, len(actions))
		for i, a := range actions {
			items[i] = actionToMap(a)
		}
		json.NewEncoder(os.Stdout).Encode(items)
	} else {
		if len(actions) == 0 {
			fmt.Println("No actions registered.")
			return 0
		}
		for _, a := range actions {
			argsStr := ""
			if a.Args != nil {
				argsStr = " " + *a.Args
			}
			fmt.Printf("  %s → %s%s  [%s, priority=%d]\n", a.Phase, a.Command, argsStr, a.Mode, a.Priority)
		}
	}
	return 0
}

func cmdRunActionUpdate(ctx context.Context, args []string) int {
	var runID, phase, command, argsJSON, mode string
	priority := -1

	var positional []string
	for _, arg := range args {
		switch {
		case strings.HasPrefix(arg, "--phase="):
			phase = strings.TrimPrefix(arg, "--phase=")
		case strings.HasPrefix(arg, "--command="):
			command = strings.TrimPrefix(arg, "--command=")
		case strings.HasPrefix(arg, "--args="):
			argsJSON = strings.TrimPrefix(arg, "--args=")
		case strings.HasPrefix(arg, "--mode="):
			mode = strings.TrimPrefix(arg, "--mode=")
		case strings.HasPrefix(arg, "--priority="):
			fmt.Sscanf(strings.TrimPrefix(arg, "--priority="), "%d", &priority)
		default:
			positional = append(positional, arg)
		}
	}

	if len(positional) < 1 || phase == "" || command == "" {
		fmt.Fprintf(os.Stderr, "ic: run action update: usage: ic run action update <run_id> --phase=<p> --command=<c> [--args=...] [--mode=...]\n")
		return 3
	}
	runID = positional[0]

	d, err := openDB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action update: %v\n", err)
		return 2
	}
	defer d.Close()

	s := action.New(d.SqlDB())
	upd := &action.ActionUpdate{}
	if argsJSON != "" {
		upd.Args = &argsJSON
	}
	if mode != "" {
		upd.Mode = &mode
	}
	if priority >= 0 {
		upd.Priority = &priority
	}

	if err := s.Update(ctx, runID, phase, command, upd); err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action update: %v\n", err)
		if err == action.ErrNotFound {
			return 1
		}
		return 2
	}

	fmt.Printf("Updated: %s → %s\n", phase, command)
	return 0
}

func cmdRunActionDelete(ctx context.Context, args []string) int {
	var phase, command string
	var positional []string

	for _, arg := range args {
		switch {
		case strings.HasPrefix(arg, "--phase="):
			phase = strings.TrimPrefix(arg, "--phase=")
		case strings.HasPrefix(arg, "--command="):
			command = strings.TrimPrefix(arg, "--command=")
		default:
			positional = append(positional, arg)
		}
	}

	if len(positional) < 1 || phase == "" || command == "" {
		fmt.Fprintf(os.Stderr, "ic: run action delete: usage: ic run action delete <run_id> --phase=<p> --command=<c>\n")
		return 3
	}
	runID := positional[0]

	d, err := openDB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action delete: %v\n", err)
		return 2
	}
	defer d.Close()

	s := action.New(d.SqlDB())
	if err := s.Delete(ctx, runID, phase, command); err != nil {
		fmt.Fprintf(os.Stderr, "ic: run action delete: %v\n", err)
		if err == action.ErrNotFound {
			return 1
		}
		return 2
	}

	fmt.Printf("Deleted: %s → %s\n", phase, command)
	return 0
}

func actionToMap(a *action.Action) map[string]interface{} {
	m := map[string]interface{}{
		"id":          a.ID,
		"run_id":      a.RunID,
		"phase":       a.Phase,
		"action_type": a.ActionType,
		"command":     a.Command,
		"mode":        a.Mode,
		"priority":    a.Priority,
	}
	if a.Args != nil {
		// Parse args as JSON array for structured output
		var parsed interface{}
		if err := json.Unmarshal([]byte(*a.Args), &parsed); err == nil {
			m["args"] = parsed
		} else {
			m["args"] = *a.Args
		}
	}
	return m
}
```

**Step 2: Add "action" case to cmdRun switch in run.go**

In `infra/intercore/cmd/ic/run.go`, add after the "artifact" case (around line 57):

```go
	case "action":
		return cmdRunAction(ctx, args[1:])
```

**Step 3: Add `--actions` flag to cmdRunCreate**

In `cmdRunCreate`, add a new variable alongside the existing flag vars (around line 68):

```go
var actionsJSON string
```

Add the flag parsing case in the `for` loop:

```go
case strings.HasPrefix(args[i], "--actions="):
    actionsJSON = strings.TrimPrefix(args[i], "--actions=")
```

After run creation succeeds (after the run ID is printed), add batch action registration:

```go
// Register phase actions if --actions provided
if actionsJSON != "" {
    var actionMap map[string]struct {
        Command string  `json:"command"`
        Args    *string `json:"args,omitempty"`
        Mode    string  `json:"mode,omitempty"`
        Type    string  `json:"type,omitempty"`
    }
    if err := json.Unmarshal([]byte(actionsJSON), &actionMap); err != nil {
        fmt.Fprintf(os.Stderr, "ic: run create: invalid --actions JSON: %v\n", err)
        return 2
    }
    aStore := action.New(d.SqlDB())
    batch := make(map[string]*action.Action, len(actionMap))
    for phase, spec := range actionMap {
        a := &action.Action{
            Command:    spec.Command,
            ActionType: spec.Type,
            Mode:       spec.Mode,
            Args:       spec.Args,
        }
        batch[phase] = a
    }
    if err := aStore.AddBatch(ctx, id, batch); err != nil {
        fmt.Fprintf(os.Stderr, "ic: run create: register actions: %v\n", err)
        return 2
    }
}
```

Add the import for the action package at the top of run.go:

```go
"github.com/mistakeknot/interverse/infra/intercore/internal/action"
```

**Step 4: Build and verify**

Run: `cd infra/intercore && go build ./cmd/ic`
Expected: builds without errors

**Step 5: Commit**

```bash
cd infra/intercore && git add cmd/ic/action.go cmd/ic/run.go
git commit -m "feat(intercore): ic run action CLI — add/list/update/delete (iv-qjm3)"
```

---

### Task 4: Resolution — Wire actions into `ic run advance` output

**Files:**
- Modify: `infra/intercore/cmd/ic/run.go:500-517` (add actions to advance JSON output)

**Step 1: After advance succeeds, resolve and include actions**

In `cmdRunAdvance`, after the `result` is obtained (around line 500), add action resolution before the JSON output block:

```go
// Resolve phase actions for the target phase
var resolvedActions []*action.Action
if result.Advanced {
    aStore := action.New(d.SqlDB())
    resolvedActions, _ = aStore.ListForPhaseResolved(ctx, id, result.ToPhase, run.ProjectDir)
}
```

Modify the JSON output block (lines 501-510) to include actions:

```go
if flagJSON {
    out := map[string]interface{}{
        "from_phase":  result.FromPhase,
        "to_phase":    result.ToPhase,
        "event_type":  result.EventType,
        "gate_result": result.GateResult,
        "gate_tier":   result.GateTier,
        "advanced":    result.Advanced,
        "reason":      result.Reason,
    }
    if len(resolvedActions) > 0 {
        actionMaps := make([]map[string]interface{}, len(resolvedActions))
        for i, a := range resolvedActions {
            actionMaps[i] = actionToMap(a)
        }
        out["actions"] = actionMaps
    }
    json.NewEncoder(os.Stdout).Encode(out)
}
```

Update the text output to also show actions:

```go
} else {
    if result.Advanced {
        fmt.Printf("%s → %s\n", result.FromPhase, result.ToPhase)
        for _, a := range resolvedActions {
            argsStr := ""
            if a.Args != nil {
                argsStr = " " + *a.Args
            }
            fmt.Printf("  action: %s%s [%s]\n", a.Command, argsStr, a.Mode)
        }
    } else {
        fmt.Printf("%s (blocked: %s)\n", result.FromPhase, result.EventType)
    }
}
```

Ensure the `action` import is present (added in Task 3).

**Step 2: Build and verify**

Run: `cd infra/intercore && go build ./cmd/ic`
Expected: builds without errors

**Step 3: Commit**

```bash
cd infra/intercore && git add cmd/ic/run.go
git commit -m "feat(intercore): ic run advance returns resolved actions (iv-z5pc)"
```

---

### Task 5: Integration tests — end-to-end action lifecycle

**Files:**
- Modify: `infra/intercore/test-integration.sh` (append action test section)

**Step 1: Add integration test section**

Append to `test-integration.sh` before the final summary:

```bash
echo "=== Phase Actions ==="
# Create a run to test actions against
ACTION_RUN=$(ic run create --project="$TEST_DIR" --goal="Test actions" --db="$TEST_DB" --json | jq -r '.id')
[[ -n "$ACTION_RUN" ]] || fail "action: create run"
pass "action: run created ($ACTION_RUN)"

# Add actions individually
ic run action add "$ACTION_RUN" --phase=planned --command=/interflux:flux-drive --args='["${artifact:plan}"]' --mode=interactive --db="$TEST_DB" >/dev/null
pass "action: add planned"

ic run action add "$ACTION_RUN" --phase=executing --command=/clavain:quality-gates --mode=interactive --db="$TEST_DB" >/dev/null
pass "action: add executing"

# List all actions
action_count=$(ic run action list "$ACTION_RUN" --json --db="$TEST_DB" | jq 'length')
[[ "$action_count" == "2" ]] || fail "action: list expected 2, got $action_count"
pass "action: list all ($action_count)"

# List by phase
phase_count=$(ic run action list "$ACTION_RUN" --phase=planned --json --db="$TEST_DB" | jq 'length')
[[ "$phase_count" == "1" ]] || fail "action: list by phase expected 1, got $phase_count"
pass "action: list by phase"

# Update action
ic run action update "$ACTION_RUN" --phase=planned --command=/interflux:flux-drive --args='["new-plan.md"]' --db="$TEST_DB" >/dev/null
updated_args=$(ic run action list "$ACTION_RUN" --phase=planned --json --db="$TEST_DB" | jq -r '.[0].args[0]')
[[ "$updated_args" == "new-plan.md" ]] || fail "action: update expected new-plan.md, got $updated_args"
pass "action: update"

# Delete action
ic run action delete "$ACTION_RUN" --phase=executing --command=/clavain:quality-gates --db="$TEST_DB" >/dev/null
remaining=$(ic run action list "$ACTION_RUN" --json --db="$TEST_DB" | jq 'length')
[[ "$remaining" == "1" ]] || fail "action: delete expected 1 remaining, got $remaining"
pass "action: delete"

# Create with --actions flag (batch registration)
BATCH_RUN=$(ic run create --project="$TEST_DIR" --goal="Test batch" --actions='{"planned":{"command":"/clavain:work","args":["${artifact:plan}"],"mode":"both"},"executing":{"command":"/clavain:quality-gates"}}' --db="$TEST_DB" --json | jq -r '.id')
[[ -n "$BATCH_RUN" ]] || fail "action: batch run create"
batch_count=$(ic run action list "$BATCH_RUN" --json --db="$TEST_DB" | jq 'length')
[[ "$batch_count" == "2" ]] || fail "action: batch expected 2, got $batch_count"
pass "action: create with --actions ($batch_count)"

# Advance with actions — verify actions appear in output
# First register an artifact so ${artifact:plan} resolves
ic run artifact add "$BATCH_RUN" --phase=brainstorm --path=docs/plans/test-plan.md --type=plan --db="$TEST_DB" >/dev/null
advance_output=$(ic run advance "$BATCH_RUN" --json --db="$TEST_DB")
advanced=$(echo "$advance_output" | jq -r '.advanced')
[[ "$advanced" == "true" ]] || fail "action: advance expected true, got $advanced"
has_actions=$(echo "$advance_output" | jq 'has("actions")')
[[ "$has_actions" == "true" ]] || fail "action: advance output missing actions"
resolved_command=$(echo "$advance_output" | jq -r '.actions[0].command')
[[ "$resolved_command" == "/clavain:work" ]] || fail "action: expected /clavain:work, got $resolved_command"
# Check template resolution (${artifact:plan} → docs/plans/test-plan.md)
resolved_arg=$(echo "$advance_output" | jq -r '.actions[0].args[0]')
[[ "$resolved_arg" == "docs/plans/test-plan.md" ]] || fail "action: expected resolved artifact path, got $resolved_arg"
pass "action: advance with resolved actions"

echo "  Phase actions tests passed"
```

**Step 2: Run integration tests**

Run: `cd infra/intercore && bash test-integration.sh`
Expected: All tests PASS including new "Phase Actions" section

**Step 3: Commit**

```bash
cd infra/intercore && git add test-integration.sh
git commit -m "test(intercore): integration tests for phase actions lifecycle (iv-z5pc)"
```

---

### Task 6: Bash integration — sprint skill consumes kernel actions

**Files:**
- Modify: `hub/clavain/hooks/lib-intercore.sh` (add action wrappers)
- Modify: `hub/clavain/hooks/lib-sprint.sh:547-610` (modify sprint_advance to read actions)
- Modify: `hub/clavain/hooks/lib-sprint.sh:512-526` (modify sprint_next_step to read from kernel)

**Step 1: Add bash wrappers to lib-intercore.sh**

Add to `hub/clavain/hooks/lib-intercore.sh`:

```bash
# ─── Phase Action Wrappers ────────────────────────────────────────

intercore_run_action_add() {
    local run_id="$1" phase="$2" command="$3"
    local args="${4:-}" mode="${5:-interactive}"
    local flags=("--phase=$phase" "--command=$command" "--mode=$mode" "--json")
    [[ -n "$args" ]] && flags+=("--args=$args")
    "$INTERCORE_BIN" run action add "$run_id" "${flags[@]}" 2>/dev/null
}

intercore_run_action_list() {
    local run_id="$1" phase="${2:-}"
    local flags=("--json")
    [[ -n "$phase" ]] && flags+=("--phase=$phase")
    "$INTERCORE_BIN" run action list "$run_id" "${flags[@]}" 2>/dev/null
}
```

**Step 2: Modify sprint_advance to parse actions from advance result**

In `hub/clavain/hooks/lib-sprint.sh`, modify `sprint_advance()` (line 547+). After the successful advance path (line 602-609), add action extraction:

After `to_phase=$(echo "$result" | jq -r '.to_phase // ""' 2>/dev/null) || to_phase=""`:

```bash
    # Extract kernel actions (if present)
    local actions_json
    actions_json=$(echo "$result" | jq -c '.actions // []' 2>/dev/null) || actions_json="[]"
    local action_count
    action_count=$(echo "$actions_json" | jq 'length' 2>/dev/null) || action_count=0

    sprint_invalidate_caches
    sprint_record_phase_tokens "$sprint_id" "$current_phase" 2>/dev/null || true

    # Return action info if kernel provided actions
    if [[ "$action_count" -gt 0 ]]; then
        local first_command first_args
        first_command=$(echo "$actions_json" | jq -r '.[0].command // ""' 2>/dev/null) || first_command=""
        first_args=$(echo "$actions_json" | jq -c '.[0].args // []' 2>/dev/null) || first_args="[]"
        echo "Phase: $from_phase → $to_phase (auto-advancing) [action: $first_command]" >&2
        # Output structured action info on stdout for caller
        echo "$actions_json"
    else
        echo "Phase: $from_phase → $to_phase (auto-advancing)" >&2
    fi
    return 0
```

**Step 3: Modify sprint_next_step to query kernel first**

In `hub/clavain/hooks/lib-sprint.sh`, modify `sprint_next_step()` (line 512). Add kernel lookup before the case statement fallback:

```bash
sprint_next_step() {
    local phase="$1"
    local sprint_id="${2:-${CLAVAIN_BEAD_ID:-}}"

    # Try kernel-backed actions first
    if [[ -n "$sprint_id" ]]; then
        local run_id
        run_id=$(_sprint_resolve_run_id "$sprint_id" 2>/dev/null) || run_id=""
        if [[ -n "$run_id" ]]; then
            local action_command
            action_command=$(intercore_run_action_list "$run_id" "$phase" 2>/dev/null | jq -r '.[0].command // ""' 2>/dev/null) || action_command=""
            if [[ -n "$action_command" ]]; then
                echo "$action_command"
                return 0
            fi
        fi
    fi

    # Fallback: static routing table
    case "$phase" in
        brainstorm)          echo "strategy" ;;
        brainstorm-reviewed) echo "strategy" ;;
        strategized)         echo "write-plan" ;;
        planned)             echo "flux-drive" ;;
        plan-reviewed)       echo "work" ;;
        executing)           echo "quality-gates" ;;
        shipping)            echo "reflect" ;;
        reflect)             echo "done" ;;
        done)                echo "done" ;;
        *)                   echo "brainstorm" ;;
    esac
}
```

**Step 4: Verify bash syntax**

Run: `bash -n hub/clavain/hooks/lib-sprint.sh && bash -n hub/clavain/hooks/lib-intercore.sh && echo "OK"`
Expected: OK (no syntax errors)

**Step 5: Commit**

```bash
cd hub/clavain && git add hooks/lib-intercore.sh hooks/lib-sprint.sh
git commit -m "feat(clavain): sprint skill consumes kernel actions with fallback (iv-pipe)"
```

---

### Task 7: Documentation — Update AGENTS.md and roadmap

**Files:**
- Modify: `infra/intercore/AGENTS.md` (add Phase Actions section, update CLI reference)
- Modify: `infra/intercore/CLAUDE.md` (add action quick reference)
- Modify: `infra/intercore/docs/roadmap.md` (mark A3 as partially shipped, note kernel-side done)

**Step 1: Add Phase Actions section to AGENTS.md**

After the "Run Tracking Module" section, add:

```markdown
## Phase Actions Module

The phase actions module (schema v14) enables event-driven advancement. Phase actions map phases to commands that should be dispatched when that phase is reached. Template variables (`${artifact:<type>}`, `${run_id}`, `${project_dir}`) are resolved at advance time.

### Table

- `phase_actions` — maps phase transitions to dispatchable commands (FK: `run_id → runs.id`)

### Action Types

- `command` — a slash command (e.g., `/clavain:work`, `/interflux:flux-drive`)
- `spawn` — trigger agent spawn
- `hook` — execute a shell hook

### Modes

- `interactive` — consumed by sprint skill (human in loop)
- `autonomous` — consumed by on-phase-advance hook (no human)
- `both` — consumed by either path

### Template Resolution

At `ic run advance` time, args containing template variables are resolved:
- `${artifact:<type>}` → latest active artifact path from `run_artifacts` WHERE `type=<type>`
- `${run_id}` → current run ID
- `${project_dir}` → project directory from runs table
- Unresolvable variables are left as-is (caller detects)

### Bash Wrappers (lib-intercore.sh)

\`\`\`bash
intercore_run_action_add <run_id> <phase> <command> [args] [mode]
intercore_run_action_list <run_id> [phase]
\`\`\`
```

**Step 2: Add to CLAUDE.md quick reference**

Add after the "Run Quick Reference" section:

```markdown
## Action Quick Reference

\`\`\`bash
ic run action add <run_id> --phase=<p> --command=<c> [--args=<json>] [--mode=<m>]
ic run action list <run_id> [--phase=<p>] [--json]
ic run action update <run_id> --phase=<p> --command=<c> [--args=...] [--mode=...]
ic run action delete <run_id> --phase=<p> --command=<c>

# Batch registration at run create
ic run create --project=. --goal="..." --actions='{"planned":{"command":"/clavain:work"}}'

# Advance now returns actions
ic run advance <run_id> --json
# → {"advanced": true, ..., "actions": [{"command": "/clavain:work", "args": ["plan.md"]}]}
\`\`\`
```

**Step 3: Update roadmap**

In `infra/intercore/docs/roadmap.md`, add entry to Shipped Epics:

```markdown
### Event-Driven Advancement — Phase 1 (P2) — SHIPPED
**What:** Kernel-side phase→action routing with template resolution.
**Bead:** iv-r9j2
**Phase:** planned (as of 2026-02-21T16:58:10Z)
**Shipped:** `phase_actions` table (schema v14), `ic run action` CLI (add/list/update/delete), `--actions` flag on `ic run create` for batch registration, template variable resolution (`${artifact:*}`, `${run_id}`, `${project_dir}`) in `ic run advance` output, `sprint_advance()` reads kernel actions with `sprint_next_step()` fallback.
```

**Step 4: Commit**

```bash
cd infra/intercore && git add AGENTS.md CLAUDE.md docs/roadmap.md
git commit -m "docs(intercore): phase actions module — AGENTS.md, CLAUDE.md, roadmap (iv-r9j2)"
```
