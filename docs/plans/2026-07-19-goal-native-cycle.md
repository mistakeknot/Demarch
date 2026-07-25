---
artifact_type: plan
bead: Sylveste-ym0
stage: design
---
# Goal-Native Cycle Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** Sylveste-ym0
**Goal:** Ship the first-class intercore Goal entity with the melange-ratified terminal-gate machinery (fenced lease, per-step close, condition linter, successor auditor), the GoalNativeChain, and the Clavain-side formation/migration surfaces — per `docs/brainstorms/2026-07-18-goal-native-cycle-brainstorm.md` KD 1–15.

**Architecture:** New `goals` table + `internal/goal` package in intercore (SQLite, migration 039), surfaced as an `ic goal` CLI noun; close concurrency via a DB-backed lease with a monotonic `fence_gen` checked on every terminal write (KD 8); gates and chain extend the existing switch/const patterns (KD 9/10). Clavain consumes via clavain-cli verbs (`goal-mint`), the formation ritual command, hook updates, and an interband sideband write that unblocks interphase retirement (KD 11).

**Tech Stack:** Go 1.25 (`modernc.org/sqlite` — `SetMaxOpenConns(1)`, no CTE-wrapped `UPDATE...RETURNING`; use direct `UPDATE ... RETURNING`/row-count), hand-rolled CLI dispatch (no cobra), bash hooks + bats, command `.md` prose files.

**Prior Learnings:** `docs/solutions/patterns/critical-patterns.md` §2 (hooks.json event-type keys) applies only if new hook files are added — this plan modifies existing hooks in place. intercore CLAUDE.md constraints encoded in tasks: `PRAGMA user_version` migrations, TTL computed in Go not SQL, exit codes 0/1/2/3.

**Repos:** `core/intercore` (tasks 1–8, 13–14) and `os/Clavain` (tasks 9–12) — both independent git repos nested in the Sylveste monorepo; commit in the repo you edited.

---

## Must-Haves

**Truths** (observable behaviors):
- `ic goal create` mints a durable goal with a lint-validated completion condition; invalid conditions are refused (exit 3) unless `--force`.
- Two concurrent close attempts on one goal: exactly one acquires the close lease; the loser gets a nonzero exit; a stale-fence writer cannot stamp close steps (race test proves it under `-race`).
- A goal closes only when all four terminal steps (`verified`, `reflected`, `compounded`, `successor_proposed`) are stamped; crash mid-sequence leaves resumable per-step state.
- `ic goal audit --json` reports three defect classes: closed-without-successor, dormant (no attached-run advance within threshold), stuck-closing (lease expired mid-close).
- `ic run create --goal-id=X` attaches a run; any successful phase advance on it touches `goals.last_run_advanced_at`.
- Runs created with the GoalNativeChain advance `goal-formed → planned` only when the charter artifact exists; runs with NULL phases still resolve to the untouched DefaultChain.
- `clavain-cli goal-mint` lints, creates the goal, optionally binds a bead, and prints ready-to-paste `/goal` text.
- The Stop-hook goal-cadence tier fires on audit defects (entity-backed), not only on prose regex; all ic calls fail open.

**Artifacts** (files with specific exports):
- `core/intercore/internal/db/migrations/039_goals.sql` — `goals` table + `runs.goal_id`
- `core/intercore/internal/goal/goal.go` exports `Goal`, `Store`, `New`, `ErrLeaseHeld`, `ErrStaleFence`, `ErrCloseIncomplete`
- `core/intercore/internal/goal/lint.go` exports `LintCondition`, `Problem`
- `core/intercore/internal/goal/audit.go` exports `Audit`, `Defect`
- `core/intercore/cmd/ic/goal.go` exports `cmdGoal` (registered in `main.go`)
- `core/intercore/pkg/phase/phase.go` exports `GoalFormed`, `GoalNativeChain`
- `os/Clavain/cmd/clavain-cli/goal.go` exports `cmdGoalMint`
- `os/Clavain/commands/goal-form.md` — the formation ritual command

**Key Links** (breakage cascades):
- Every terminal-sequence write goes through `fence_gen` equality — `StampStep`/`FinishClose` WHERE clauses are the single-writer guarantee.
- `internal/phase/store.go UpdatePhase` → `goals.last_run_advanced_at` touch → `Audit` dormancy math — if the touch is dropped, dormancy audit false-positives every active goal.
- `ic goal lint-condition` ← `ic goal create` refusal ← `clavain-cli goal-mint` — the tier-independent gate (KD 9) exists only if create refuses by default.
- `cmdSprintAdvance` interband write must produce the exact envelope `interline/scripts/statusline.sh` reads, or interphase retirement (KD 11) breaks the statusline.

---

## Stage A — Goal entity foundation (intercore)

### Task 1: Migration 039 — goals table + runs.goal_id

**Files:**
- Create: `core/intercore/internal/db/migrations/039_goals.sql`
- Test: `core/intercore/internal/db/migrator_test.go` (existing file — add one case only if a migration-count assertion exists; otherwise no test change)

**Step 1: Write the migration** (pattern: `038_agency_events.sql` — additive, idempotent, `IF NOT EXISTS`; the migrator tolerates duplicate-column errors):

```sql
CREATE TABLE IF NOT EXISTS goals (
    id                     TEXT NOT NULL PRIMARY KEY,
    project_dir            TEXT NOT NULL,
    title                  TEXT NOT NULL,
    charter_path           TEXT,
    condition_text         TEXT NOT NULL DEFAULT '',
    status                 TEXT NOT NULL DEFAULT 'open',
    complexity             INTEGER NOT NULL DEFAULT 3,
    fence_gen              INTEGER NOT NULL DEFAULT 0,
    closing_run_id         TEXT,
    lease_owner            TEXT,
    lease_expires_at       INTEGER,
    verified_at            INTEGER,
    reflected_at           INTEGER,
    compounded_at          INTEGER,
    successor_proposed_at  INTEGER,
    successor_ref          TEXT,
    last_run_advanced_at   INTEGER,
    bead_id                TEXT,
    created_at             INTEGER NOT NULL DEFAULT (unixepoch()),
    updated_at             INTEGER NOT NULL DEFAULT (unixepoch()),
    amended_at             INTEGER,
    closed_at              INTEGER
);
CREATE INDEX IF NOT EXISTS idx_goals_live ON goals(status) WHERE status IN ('open','closing');
CREATE INDEX IF NOT EXISTS idx_goals_project ON goals(project_dir, status);
ALTER TABLE runs ADD COLUMN goal_id TEXT;
CREATE INDEX IF NOT EXISTS idx_runs_goal ON runs(goal_id) WHERE goal_id IS NOT NULL;
```

Status vocabulary: `open | closing | closed | abandoned`. All timestamps unix seconds (INTEGER), matching `runs`.

**Step 2: Verify migration applies**
Run: `cd core/intercore && go test ./internal/db/ -run TestMigrat -v`
Expected: PASS (migrator picks up 039 automatically via `go:embed migrations/*.sql`)

**Step 3: Commit**
```bash
cd core/intercore
git add internal/db/migrations/039_goals.sql
git commit -m "feat(goal): migration 039 — goals table + runs.goal_id (Sylveste goal-native cycle, KD 1/3/8)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/db/ 2>&1 | tail -1`
  expect: exit 0
- run: `grep -c "IF NOT EXISTS" /Users/sma/projects/Sylveste/core/intercore/internal/db/migrations/039_goals.sql`
  expect: contains "4"
</verify>

### Task 2: internal/goal package — Goal struct + Store CRUD

**Files:**
- Create: `core/intercore/internal/goal/goal.go`
- Test: `core/intercore/internal/goal/goal_test.go`

**Step 1: Write the failing test** (mirror `internal/phase/store_test.go` conventions — `t.TempDir()` DB, `db.Open` + `Migrate`, manual assertions):

```go
package goal

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/mistakeknot/intercore/internal/db"
)

func setupTestStore(t *testing.T) *Store {
	t.Helper()
	dir := t.TempDir()
	d, err := db.Open(filepath.Join(dir, "test.db"), 100*time.Millisecond)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { d.Close() })
	if err := d.Migrate(context.Background()); err != nil {
		t.Fatalf("Migrate: %v", err)
	}
	return New(d.SqlDB())
}

func TestStore_CreateAndGet(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()
	g := &Goal{ProjectDir: "/tmp/test", Title: "Ship widget", ConditionText: "go test ./... exits 0", Complexity: 3}
	id, err := s.Create(ctx, g)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if len(id) != 8 {
		t.Errorf("ID length = %d, want 8", len(id))
	}
	got, err := s.Get(ctx, id)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Status != "open" || got.Title != "Ship widget" || got.FenceGen != 0 {
		t.Errorf("got %+v", got)
	}
}

func TestStore_ListOpenByProject(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()
	_, _ = s.Create(ctx, &Goal{ProjectDir: "/a", Title: "one", ConditionText: "x exits 0"})
	_, _ = s.Create(ctx, &Goal{ProjectDir: "/b", Title: "two", ConditionText: "y exits 0"})
	got, err := s.List(ctx, "/a", "open")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 1 || got[0].Title != "one" {
		t.Errorf("List = %+v", got)
	}
}
```

**Step 2: Run to confirm failure**
Run: `cd core/intercore && go test ./internal/goal/ -v`
Expected: FAIL (package does not exist / undefined: New)

**Step 3: Write the implementation** — `internal/goal/goal.go`:

```go
// Package goal implements the first-class Goal entity: a durable unit of
// intent that contains runs, carries a machine-evaluable completion
// condition, and closes through a fenced, per-step terminal sequence.
// Design: docs/brainstorms/2026-07-18-goal-native-cycle-brainstorm.md KD 1/3/8.
package goal

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"errors"
	"fmt"
)

var (
	ErrNotFound        = errors.New("goal: not found")
	ErrLeaseHeld       = errors.New("goal: close lease held by another owner")
	ErrStaleFence      = errors.New("goal: stale fence — lease was broken and reacquired")
	ErrCloseIncomplete = errors.New("goal: terminal steps incomplete")
)

// Goal is one row of the goals table. Timestamps are unix seconds.
type Goal struct {
	ID                  string
	ProjectDir          string
	Title               string
	CharterPath         *string
	ConditionText       string
	Status              string
	Complexity          int
	FenceGen            int64
	ClosingRunID        *string
	LeaseOwner          *string
	LeaseExpiresAt      *int64
	VerifiedAt          *int64
	ReflectedAt         *int64
	CompoundedAt        *int64
	SuccessorProposedAt *int64
	SuccessorRef        *string
	LastRunAdvancedAt   *int64
	BeadID              *string
	CreatedAt           int64
	UpdatedAt           int64
	AmendedAt           *int64
	ClosedAt            *int64
}

type Store struct{ db *sql.DB }

func New(db *sql.DB) *Store { return &Store{db: db} }

func newID() (string, error) {
	var b [4]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(b[:]), nil
}

const goalCols = `id, project_dir, title, charter_path, condition_text, status,
	complexity, fence_gen, closing_run_id, lease_owner, lease_expires_at,
	verified_at, reflected_at, compounded_at, successor_proposed_at,
	successor_ref, last_run_advanced_at, bead_id, created_at, updated_at,
	amended_at, closed_at`

func scanGoal(row interface{ Scan(...any) error }) (*Goal, error) {
	var g Goal
	err := row.Scan(&g.ID, &g.ProjectDir, &g.Title, &g.CharterPath,
		&g.ConditionText, &g.Status, &g.Complexity, &g.FenceGen,
		&g.ClosingRunID, &g.LeaseOwner, &g.LeaseExpiresAt, &g.VerifiedAt,
		&g.ReflectedAt, &g.CompoundedAt, &g.SuccessorProposedAt,
		&g.SuccessorRef, &g.LastRunAdvancedAt, &g.BeadID, &g.CreatedAt,
		&g.UpdatedAt, &g.AmendedAt, &g.ClosedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &g, nil
}

func (s *Store) Create(ctx context.Context, g *Goal) (string, error) {
	id, err := newID()
	if err != nil {
		return "", fmt.Errorf("goal create: %w", err)
	}
	if g.Complexity == 0 {
		g.Complexity = 3
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO goals
		(id, project_dir, title, charter_path, condition_text, complexity, bead_id)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		id, g.ProjectDir, g.Title, g.CharterPath, g.ConditionText, g.Complexity, g.BeadID)
	if err != nil {
		return "", fmt.Errorf("goal create: %w", err)
	}
	return id, nil
}

func (s *Store) Get(ctx context.Context, id string) (*Goal, error) {
	return scanGoal(s.db.QueryRowContext(ctx,
		`SELECT `+goalCols+` FROM goals WHERE id = ?`, id))
}

// List returns goals for a project (empty projectDir = all projects),
// filtered by status (empty = any).
func (s *Store) List(ctx context.Context, projectDir, status string) ([]*Goal, error) {
	q := `SELECT ` + goalCols + ` FROM goals WHERE 1=1`
	var args []any
	if projectDir != "" {
		q += ` AND project_dir = ?`
		args = append(args, projectDir)
	}
	if status != "" {
		q += ` AND status = ?`
		args = append(args, status)
	}
	q += ` ORDER BY created_at DESC`
	rows, err := s.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*Goal
	for rows.Next() {
		g, err := scanGoal(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, g)
	}
	return out, rows.Err()
}
```

**Step 4: Run tests to confirm pass**
Run: `cd core/intercore && go test ./internal/goal/ -v`
Expected: PASS (2 tests)

**Step 5: Commit**
```bash
cd core/intercore
git add internal/goal/goal.go internal/goal/goal_test.go
git commit -m "feat(goal): internal/goal package — Goal entity store CRUD"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 3: Fenced close lease + per-step terminal sequence

**Files:**
- Modify: `core/intercore/internal/goal/goal.go` (append)
- Test: `core/intercore/internal/goal/close_test.go`

The single-writer guarantee (KD 8): `AcquireClose` CAS-transitions `open→closing` (or breaks an expired lease) and bumps `fence_gen`; every subsequent terminal write carries the fence and fails with `ErrStaleFence` if the lease was rebroken. TTL is computed in Go (`nowUnix + ttlSec`), never `unixepoch()` arithmetic in SQL (intercore CLAUDE.md). No CTE wrapping — direct `UPDATE ... RETURNING` with scan.

**Step 1: Write the failing test** — `close_test.go`:

```go
package goal

import (
	"context"
	"errors"
	"testing"
	"time"
)

func mkGoal(t *testing.T, s *Store) string {
	t.Helper()
	id, err := s.Create(context.Background(),
		&Goal{ProjectDir: "/tmp/t", Title: "g", ConditionText: "tests exit 0"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	return id
}

func TestAcquireClose_ExclusiveAndFenced(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()
	id := mkGoal(t, s)

	f1, err := s.AcquireClose(ctx, id, "run-A", "sessionA", 3600)
	if err != nil {
		t.Fatalf("first acquire: %v", err)
	}
	if f1 != 1 {
		t.Errorf("fence = %d, want 1", f1)
	}
	if _, err := s.AcquireClose(ctx, id, "run-B", "sessionB", 3600); !errors.Is(err, ErrLeaseHeld) {
		t.Errorf("second acquire err = %v, want ErrLeaseHeld", err)
	}
}

func TestAcquireClose_BreaksExpiredLease_StaleFenceRejected(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()
	id := mkGoal(t, s)

	f1, err := s.AcquireClose(ctx, id, "run-A", "sessionA", 0) // expires immediately
	if err != nil {
		t.Fatalf("acquire: %v", err)
	}
	time.Sleep(1100 * time.Millisecond) // ensure now > lease_expires_at (second resolution)
	f2, err := s.AcquireClose(ctx, id, "run-B", "sessionB", 3600)
	if err != nil {
		t.Fatalf("break-stale acquire: %v", err)
	}
	if f2 != f1+1 {
		t.Errorf("fence after break = %d, want %d", f2, f1+1)
	}
	// old holder's fence is now stale
	if err := s.StampStep(ctx, id, "verified", f1); !errors.Is(err, ErrStaleFence) {
		t.Errorf("stale stamp err = %v, want ErrStaleFence", err)
	}
	// new holder stamps fine
	if err := s.StampStep(ctx, id, "verified", f2); err != nil {
		t.Errorf("fresh stamp: %v", err)
	}
}

func TestFinishClose_RequiresAllSteps(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()
	id := mkGoal(t, s)
	f, _ := s.AcquireClose(ctx, id, "run-A", "sessionA", 3600)

	if err := s.FinishClose(ctx, id, f); !errors.Is(err, ErrCloseIncomplete) {
		t.Fatalf("premature finish err = %v, want ErrCloseIncomplete", err)
	}
	for _, step := range []string{"verified", "reflected", "compounded", "successor_proposed"} {
		if err := s.StampStep(ctx, id, step, f); err != nil {
			t.Fatalf("stamp %s: %v", step, err)
		}
	}
	if err := s.FinishClose(ctx, id, f); err != nil {
		t.Fatalf("finish: %v", err)
	}
	g, _ := s.Get(ctx, id)
	if g.Status != "closed" || g.ClosedAt == nil {
		t.Errorf("after close: %+v", g)
	}
}

func TestStampStep_UnknownStepRejected(t *testing.T) {
	s := setupTestStore(t)
	id := mkGoal(t, s)
	f, _ := s.AcquireClose(context.Background(), id, "r", "o", 3600)
	if err := s.StampStep(context.Background(), id, "bogus", f); err == nil {
		t.Error("bogus step accepted")
	}
}
```

**Step 2: Run to confirm failure**
Run: `cd core/intercore && go test ./internal/goal/ -run 'Acquire|Finish|Stamp' -v`
Expected: FAIL (undefined: AcquireClose)

**Step 3: Append the implementation** to `goal.go`:

```go
// stepCols whitelists terminal-step names to columns — never interpolate
// caller input into SQL identifiers.
var stepCols = map[string]string{
	"verified":           "verified_at",
	"reflected":          "reflected_at",
	"compounded":         "compounded_at",
	"successor_proposed": "successor_proposed_at",
}

// AcquireClose transitions open→closing (or breaks an expired closing lease)
// and returns the new fence generation. ttlSec sizes the lease to the close
// sequence's real multi-LLM-call latency — callers should renew between
// steps rather than passing a huge TTL.
func (s *Store) AcquireClose(ctx context.Context, id, runID, owner string, ttlSec int64) (int64, error) {
	now := nowUnix()
	var fence int64
	err := s.db.QueryRowContext(ctx, `UPDATE goals
		SET status = 'closing', closing_run_id = ?, lease_owner = ?,
		    lease_expires_at = ?, fence_gen = fence_gen + 1, updated_at = ?
		WHERE id = ?
		  AND (status = 'open'
		       OR (status = 'closing' AND lease_expires_at IS NOT NULL AND lease_expires_at < ?))
		RETURNING fence_gen`,
		runID, owner, now+ttlSec, now, id, now).Scan(&fence)
	if errors.Is(err, sql.ErrNoRows) {
		if _, gerr := s.Get(ctx, id); errors.Is(gerr, ErrNotFound) {
			return 0, ErrNotFound
		}
		return 0, ErrLeaseHeld
	}
	if err != nil {
		return 0, fmt.Errorf("goal acquire-close: %w", err)
	}
	return fence, nil
}

// RenewLease extends the lease under the current fence.
func (s *Store) RenewLease(ctx context.Context, id string, fence, ttlSec int64) error {
	now := nowUnix()
	res, err := s.db.ExecContext(ctx, `UPDATE goals
		SET lease_expires_at = ?, updated_at = ?
		WHERE id = ? AND fence_gen = ? AND status = 'closing'`,
		now+ttlSec, now, id, fence)
	if err != nil {
		return fmt.Errorf("goal renew: %w", err)
	}
	return staleUnlessOneRow(res)
}

// StampStep records one terminal step under the fence.
func (s *Store) StampStep(ctx context.Context, id, step string, fence int64) error {
	col, ok := stepCols[step]
	if !ok {
		return fmt.Errorf("goal stamp: unknown step %q", step)
	}
	now := nowUnix()
	res, err := s.db.ExecContext(ctx, `UPDATE goals
		SET `+col+` = ?, updated_at = ?
		WHERE id = ? AND fence_gen = ? AND status = 'closing'`,
		now, now, id, fence)
	if err != nil {
		return fmt.Errorf("goal stamp %s: %w", step, err)
	}
	return staleUnlessOneRow(res)
}

// FinishClose completes the goal iff every step is stamped, under the fence.
func (s *Store) FinishClose(ctx context.Context, id string, fence int64) error {
	now := nowUnix()
	res, err := s.db.ExecContext(ctx, `UPDATE goals
		SET status = 'closed', closed_at = ?, updated_at = ?,
		    lease_owner = NULL, lease_expires_at = NULL
		WHERE id = ? AND fence_gen = ? AND status = 'closing'
		  AND verified_at IS NOT NULL AND reflected_at IS NOT NULL
		  AND compounded_at IS NOT NULL AND successor_proposed_at IS NOT NULL`,
		now, now, id, fence)
	if err != nil {
		return fmt.Errorf("goal finish-close: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 1 {
		return nil
	}
	// Distinguish stale fence from incomplete steps for the caller.
	g, gerr := s.Get(ctx, id)
	if gerr != nil {
		return gerr
	}
	if g.Status == "closing" && g.FenceGen == fence {
		return ErrCloseIncomplete
	}
	return ErrStaleFence
}

// ReleaseLease abandons a close attempt (goal returns to open) under the fence.
func (s *Store) ReleaseLease(ctx context.Context, id string, fence int64) error {
	res, err := s.db.ExecContext(ctx, `UPDATE goals
		SET status = 'open', lease_owner = NULL, lease_expires_at = NULL,
		    closing_run_id = NULL, updated_at = ?
		WHERE id = ? AND fence_gen = ? AND status = 'closing'`,
		nowUnix(), id, fence)
	if err != nil {
		return fmt.Errorf("goal release: %w", err)
	}
	return staleUnlessOneRow(res)
}

func staleUnlessOneRow(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n != 1 {
		return ErrStaleFence
	}
	return nil
}
```

Also add near the top of `goal.go` (TTL in Go per intercore CLAUDE.md; a var so tests could stub it later):

```go
import "time"
var nowUnix = func() int64 { return time.Now().Unix() }
```

**Step 4: Run tests to confirm pass**
Run: `cd core/intercore && go test ./internal/goal/ -v`
Expected: PASS (all)

**Step 5: Commit**
```bash
cd core/intercore
git add internal/goal/goal.go internal/goal/close_test.go
git commit -m "feat(goal): fenced close lease + per-step terminal sequence (KD 8)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ 2>&1 | tail -1`
  expect: exit 0
- run: `grep -c "fence_gen = ?" /Users/sma/projects/Sylveste/core/intercore/internal/goal/goal.go`
  expect: contains "4"
</verify>

### Task 4: Condition linter (tier-independent gate, KD 9)

**Files:**
- Create: `core/intercore/internal/goal/lint.go`
- Test: `core/intercore/internal/goal/lint_test.go`

Purely mechanical checks against the /goal built-in evaluator's contract: ≤4000 chars, non-empty, and at least one *demonstrable predicate* (something the Haiku evaluator can judge from surfaced output). Subjective-only wording is an error; missing turn-bound is a warning.

**Step 1: Write the failing test** — `lint_test.go`:

```go
package goal

import (
	"strings"
	"testing"
)

func TestLintCondition(t *testing.T) {
	cases := []struct {
		name     string
		text     string
		wantErrs int
		wantWarn bool
	}{
		{"good with bound", "all Go tests exit 0 and bead mk-1 closed, or stop after 20 turns", 0, false},
		{"good no bound", "`go test ./...` exits 0 and git status is clean", 0, true},
		{"empty", "", 1, false},
		{"too long", strings.Repeat("x", 4001), 1, false},
		{"subjective only", "the code is good and the feature feels polished", 1, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			probs := LintCondition(tc.text)
			errs, warns := 0, 0
			for _, p := range probs {
				if p.Severity == "error" {
					errs++
				} else {
					warns++
				}
			}
			if errs != tc.wantErrs {
				t.Errorf("errors = %d (%v), want %d", errs, probs, tc.wantErrs)
			}
			if tc.wantWarn && warns == 0 {
				t.Errorf("expected a warning, got %v", probs)
			}
		})
	}
}
```

**Step 2: Run to confirm failure**
Run: `cd core/intercore && go test ./internal/goal/ -run Lint -v`
Expected: FAIL (undefined: LintCondition)

**Step 3: Write the implementation** — `lint.go`:

```go
package goal

import (
	"fmt"
	"regexp"
)

// Problem is one lint finding on a /goal completion-condition string.
type Problem struct {
	Severity string `json:"severity"` // "error" | "warning"
	Message  string `json:"message"`
}

// MaxConditionLen is the /goal built-in's condition limit.
const MaxConditionLen = 4000

// demonstrable matches predicates the /goal evaluator can judge from
// surfaced conversation output (commands, exit codes, artifact states).
// Deliberately mechanical — no model judgment (capability-routing doctrine).
var demonstrable = regexp.MustCompile(`(?i)` +
	`exit(s)?\s+(code\s+)?0|` +
	"`[^`]+`|" +
	`tests?\s+(pass|green)|` +
	`git status|` +
	`\b(bd|bead)\b.*\bclose|` +
	`\b(HTTP|http)\s*2\d\d\b|` +
	`file .*exist|` +
	`committed|pushed|published|deployed|merged|` +
	`stop after \d+ turns`)

var turnBound = regexp.MustCompile(`(?i)stop after \d+ turns`)

// LintCondition validates a condition string against the /goal built-in's
// contract: length, non-emptiness, demonstrability, and a bounded-runtime
// recommendation. Errors block minting (unless forced); warnings inform.
func LintCondition(text string) []Problem {
	var probs []Problem
	if len(text) == 0 {
		return []Problem{{Severity: "error", Message: "condition is empty"}}
	}
	if len(text) > MaxConditionLen {
		probs = append(probs, Problem{Severity: "error", Message: fmt.Sprintf(
			"condition is %d chars; the /goal built-in caps at %d", len(text), MaxConditionLen)})
	}
	if !demonstrable.MatchString(text) {
		probs = append(probs, Problem{Severity: "error", Message: "no demonstrable predicate " +
			"(the evaluator only judges surfaced output — reference a command, exit code, " +
			"artifact state, or bead close; not subjective quality)"})
	}
	if !turnBound.MatchString(text) {
		probs = append(probs, Problem{Severity: "warning", Message: "no runtime bound — " +
			"consider appending 'or stop after N turns'"})
	}
	return probs
}
```

**Step 4: Run tests to confirm pass**
Run: `cd core/intercore && go test ./internal/goal/ -run Lint -v`
Expected: PASS

**Step 5: Commit**
```bash
cd core/intercore
git add internal/goal/lint.go internal/goal/lint_test.go
git commit -m "feat(goal): completion-condition linter against the /goal evaluator contract (KD 9)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ -run Lint 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 5: Successor auditor + dormancy sweep (KD 8, f-016/f-030/f-031)

**Files:**
- Create: `core/intercore/internal/goal/audit.go`
- Test: `core/intercore/internal/goal/audit_test.go`

Three defect classes, one query pass: `closed_without_successor` (closed but `successor_ref` NULL — belt-and-braces beyond FinishClose's stamp requirement, catches legacy/manual rows), `dormant` (open/closing with no attached-run advance within threshold), `stuck_closing` (closing with an expired lease).

**Step 1: Write the failing test** — `audit_test.go`:

```go
package goal

import (
	"context"
	"testing"
)

func TestAudit_ThreeDefectClasses(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()

	// dormant: open, last advance far in the past
	dormantID := mkGoal(t, s)
	if _, err := s.db.ExecContext(ctx,
		`UPDATE goals SET last_run_advanced_at = 1000 WHERE id = ?`, dormantID); err != nil {
		t.Fatal(err)
	}

	// stuck_closing: lease expired mid-close
	stuckID := mkGoal(t, s)
	if _, err := s.AcquireClose(ctx, stuckID, "r", "o", 0); err != nil {
		t.Fatal(err)
	}

	// closed_without_successor: closed but successor_ref NULL (legacy/manual row)
	orphanID := mkGoal(t, s)
	if _, err := s.db.ExecContext(ctx,
		`UPDATE goals SET status = 'closed', closed_at = 2000 WHERE id = ?`, orphanID); err != nil {
		t.Fatal(err)
	}

	// healthy: open and recently advanced
	healthyID := mkGoal(t, s)
	if err := s.TouchRunAdvance(ctx, healthyID); err != nil {
		t.Fatal(err)
	}

	defects, err := s.Audit(ctx, "", 3600)
	if err != nil {
		t.Fatalf("Audit: %v", err)
	}
	byID := map[string]string{}
	for _, d := range defects {
		byID[d.GoalID] = d.Kind
	}
	if byID[dormantID] != "dormant" {
		t.Errorf("dormant: got %q", byID[dormantID])
	}
	if byID[stuckID] != "stuck_closing" {
		t.Errorf("stuck: got %q", byID[stuckID])
	}
	if byID[orphanID] != "closed_without_successor" {
		t.Errorf("orphan: got %q", byID[orphanID])
	}
	if _, ok := byID[healthyID]; ok {
		t.Errorf("healthy goal flagged: %v", defects)
	}
}
```

**Step 2: Run to confirm failure**
Run: `cd core/intercore && go test ./internal/goal/ -run Audit -v`
Expected: FAIL (undefined: Audit / TouchRunAdvance)

**Step 3: Write the implementation** — `audit.go`:

```go
package goal

import (
	"context"
	"fmt"
)

// Defect is one audit finding — the standing successor-proposal auditor
// (the melange's argmax finding f-016: the obligation must not live only
// inside the dying session's own turn).
type Defect struct {
	GoalID string `json:"goal_id"`
	Title  string `json:"title"`
	Kind   string `json:"kind"` // closed_without_successor | dormant | stuck_closing
	Detail string `json:"detail"`
}

// TouchRunAdvance updates dormancy state; called on any attached run's
// successful phase advance (f-031 — drift detection is one comparison).
func (s *Store) TouchRunAdvance(ctx context.Context, id string) error {
	_, err := s.db.ExecContext(ctx,
		`UPDATE goals SET last_run_advanced_at = ?, updated_at = ? WHERE id = ?`,
		nowUnix(), nowUnix(), id)
	return err
}

// Audit sweeps goals for the three defect classes. dormantAfterSec bounds
// how long an open goal may go without any attached-run advance.
// projectDir empty = all projects.
func (s *Store) Audit(ctx context.Context, projectDir string, dormantAfterSec int64) ([]Defect, error) {
	now := nowUnix()
	q := `SELECT id, title, status, lease_expires_at, successor_ref,
	             COALESCE(last_run_advanced_at, created_at) AS last_activity
	      FROM goals WHERE status IN ('open', 'closing', 'closed')`
	var args []any
	if projectDir != "" {
		q += ` AND project_dir = ?`
		args = append(args, projectDir)
	}
	rows, err := s.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var defects []Defect
	for rows.Next() {
		var id, title, status string
		var leaseExp *int64
		var successor *string
		var lastActivity int64
		if err := rows.Scan(&id, &title, &status, &leaseExp, &successor, &lastActivity); err != nil {
			return nil, err
		}
		switch status {
		case "closed":
			if successor == nil {
				defects = append(defects, Defect{GoalID: id, Title: title,
					Kind: "closed_without_successor",
					Detail: "goal closed with no successor_ref recorded"})
			}
		case "closing":
			if leaseExp != nil && *leaseExp < now {
				defects = append(defects, Defect{GoalID: id, Title: title,
					Kind: "stuck_closing",
					Detail: fmt.Sprintf("close lease expired %ds ago", now-*leaseExp)})
			}
		case "open":
			if now-lastActivity > dormantAfterSec {
				defects = append(defects, Defect{GoalID: id, Title: title,
					Kind: "dormant",
					Detail: fmt.Sprintf("no attached-run advance for %ds", now-lastActivity)})
			}
		}
	}
	return defects, rows.Err()
}

// SetSuccessor records the successor proposal target (bead id, goal id, or
// free-text ref) — the durable record the auditor checks for.
func (s *Store) SetSuccessor(ctx context.Context, id, ref string) error {
	_, err := s.db.ExecContext(ctx,
		`UPDATE goals SET successor_ref = ?, updated_at = ? WHERE id = ?`,
		ref, nowUnix(), id)
	return err
}
```

**Step 4: Run tests to confirm pass**
Run: `cd core/intercore && go test ./internal/goal/ -v`
Expected: PASS (all)

**Step 5: Commit**
```bash
cd core/intercore
git add internal/goal/audit.go internal/goal/audit_test.go
git commit -m "feat(goal): successor auditor + dormancy sweep (f-016/f-030/f-031)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ -run Audit 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 6: `ic goal` CLI noun

**Files:**
- Create: `core/intercore/cmd/ic/goal.go`
- Modify: `core/intercore/cmd/ic/main.go` (one switch case + usage line)
- Test: covered by integration task 14 (CLI files in cmd/ic have no unit tests by convention — verified against `run.go`)

**Step 1: Write `cmd/ic/goal.go`** (mirror `run.go` dispatch + `run_create.go` flag/output conventions; exit codes 0/2/3, check-style 1 for lint/audit findings):

```go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"

	"github.com/mistakeknot/intercore/internal/cli"
	"github.com/mistakeknot/intercore/internal/goal"
)

func cmdGoal(ctx context.Context, args []string) int {
	if len(args) == 0 {
		slog.Error("goal: missing subcommand",
			"expected", "create, show, list, close, audit, lint-condition, successor")
		return 3
	}
	switch args[0] {
	case "create":
		return cmdGoalCreate(ctx, args[1:])
	case "show":
		return cmdGoalShow(ctx, args[1:])
	case "list":
		return cmdGoalList(ctx, args[1:])
	case "close":
		return cmdGoalClose(ctx, args[1:])
	case "audit":
		return cmdGoalAudit(ctx, args[1:])
	case "lint-condition":
		return cmdGoalLint(args[1:])
	case "successor":
		return cmdGoalSuccessor(ctx, args[1:])
	default:
		slog.Error("goal: unknown subcommand", "got", args[0])
		return 3
	}
}

func goalStore() (*goal.Store, func(), int) {
	d, err := openDB()
	if err != nil {
		slog.Error("goal: open db failed", "error", err)
		return nil, nil, 2
	}
	return goal.New(d.SqlDB()), func() { d.Close() }, 0
}

func cmdGoalCreate(ctx context.Context, args []string) int {
	f := cli.ParseFlags(args)
	title := f.String("title", "")
	project := f.String("project", "")
	condition := f.String("condition", "")
	conditionFile := f.String("condition-file", "")
	charter := f.String("charter", "")
	beadID := f.String("bead", "")
	force := f.Bool("force")
	complexity, err := f.Int("complexity", 3)
	if err != nil || complexity < 1 || complexity > 5 {
		slog.Error("goal create: invalid complexity")
		return 3
	}
	if title == "" || project == "" {
		slog.Error("goal create: --title and --project are required")
		return 3
	}
	if conditionFile != "" {
		b, rerr := os.ReadFile(conditionFile)
		if rerr != nil {
			slog.Error("goal create: read condition file", "error", rerr)
			return 2
		}
		condition = string(b)
	}
	// Tier-independent gate (KD 9): refuse error-level lint findings.
	probs := goal.LintCondition(condition)
	hasErr := false
	for _, p := range probs {
		fmt.Fprintf(os.Stderr, "lint %s: %s\n", p.Severity, p.Message)
		if p.Severity == "error" {
			hasErr = true
		}
	}
	if hasErr && !force {
		slog.Error("goal create: condition failed lint (use --force to override)")
		return 3
	}
	store, closeDB, rc := goalStore()
	if rc != 0 {
		return rc
	}
	defer closeDB()
	g := &goal.Goal{ProjectDir: project, Title: title, ConditionText: condition, Complexity: complexity}
	if charter != "" {
		g.CharterPath = &charter
	}
	if beadID != "" {
		g.BeadID = &beadID
	}
	id, err := store.Create(ctx, g)
	if err != nil {
		slog.Error("goal create failed", "error", err)
		return 2
	}
	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(map[string]any{"id": id, "status": "open"})
	} else {
		fmt.Println(id)
	}
	return 0
}

func cmdGoalShow(ctx context.Context, args []string) int {
	if len(args) == 0 {
		slog.Error("goal show: missing id")
		return 3
	}
	store, closeDB, rc := goalStore()
	if rc != 0 {
		return rc
	}
	defer closeDB()
	g, err := store.Get(ctx, args[0])
	if err != nil {
		slog.Error("goal show failed", "error", err)
		return 2
	}
	json.NewEncoder(os.Stdout).Encode(g)
	return 0
}

func cmdGoalList(ctx context.Context, args []string) int {
	f := cli.ParseFlags(args)
	store, closeDB, rc := goalStore()
	if rc != 0 {
		return rc
	}
	defer closeDB()
	goals, err := store.List(ctx, f.String("project", ""), f.String("status", ""))
	if err != nil {
		slog.Error("goal list failed", "error", err)
		return 2
	}
	if flagJSON {
		json.NewEncoder(os.Stdout).Encode(goals)
		return 0
	}
	for _, g := range goals {
		fmt.Printf("%s\t%s\t%s\n", g.ID, g.Status, g.Title)
	}
	return 0
}

// close subcommands: begin | step | finish | release
func cmdGoalClose(ctx context.Context, args []string) int {
	if len(args) < 2 {
		slog.Error("goal close: usage: close <begin|step|finish|release> <goal-id> [flags]")
		return 3
	}
	verb, id := args[0], args[1]
	f := cli.ParseFlags(args[2:])
	store, closeDB, rc := goalStore()
	if rc != 0 {
		return rc
	}
	defer closeDB()
	switch verb {
	case "begin":
		ttl, err := f.Int("ttl", 1800)
		if err != nil {
			slog.Error("goal close begin: invalid --ttl")
			return 3
		}
		fence, err := store.AcquireClose(ctx, id, f.String("run", ""), f.String("owner", ""), int64(ttl))
		if err != nil {
			slog.Error("goal close begin failed", "error", err)
			return 2
		}
		json.NewEncoder(os.Stdout).Encode(map[string]any{"fence": fence})
		return 0
	case "step":
		fence, err := f.Int("fence", 0)
		if err != nil || fence == 0 {
			slog.Error("goal close step: --fence required")
			return 3
		}
		if err := store.StampStep(ctx, id, f.String("name", ""), int64(fence)); err != nil {
			slog.Error("goal close step failed", "error", err)
			return 2
		}
		return 0
	case "finish":
		fence, err := f.Int("fence", 0)
		if err != nil || fence == 0 {
			slog.Error("goal close finish: --fence required")
			return 3
		}
		if err := store.FinishClose(ctx, id, int64(fence)); err != nil {
			slog.Error("goal close finish failed", "error", err)
			return 2
		}
		return 0
	case "release":
		fence, err := f.Int("fence", 0)
		if err != nil || fence == 0 {
			slog.Error("goal close release: --fence required")
			return 3
		}
		if err := store.ReleaseLease(ctx, id, int64(fence)); err != nil {
			slog.Error("goal close release failed", "error", err)
			return 2
		}
		return 0
	default:
		slog.Error("goal close: unknown verb", "got", verb)
		return 3
	}
}

func cmdGoalAudit(ctx context.Context, args []string) int {
	f := cli.ParseFlags(args)
	dormant, err := f.Int("dormant-after", 604800) // 7 days
	if err != nil {
		slog.Error("goal audit: invalid --dormant-after")
		return 3
	}
	store, closeDB, rc := goalStore()
	if rc != 0 {
		return rc
	}
	defer closeDB()
	defects, err := store.Audit(ctx, f.String("project", ""), int64(dormant))
	if err != nil {
		slog.Error("goal audit failed", "error", err)
		return 2
	}
	json.NewEncoder(os.Stdout).Encode(defects)
	if len(defects) > 0 {
		return 1 // check-style: findings present
	}
	return 0
}

func cmdGoalLint(args []string) int {
	f := cli.ParseFlags(args)
	text := f.String("text", "")
	file := f.String("file", "")
	if file != "" {
		b, err := os.ReadFile(file)
		if err != nil {
			slog.Error("goal lint-condition: read file", "error", err)
			return 2
		}
		text = string(b)
	}
	probs := goal.LintCondition(text)
	json.NewEncoder(os.Stdout).Encode(probs)
	for _, p := range probs {
		if p.Severity == "error" {
			return 1
		}
	}
	return 0
}

func cmdGoalSuccessor(ctx context.Context, args []string) int {
	if len(args) < 1 {
		slog.Error("goal successor: usage: successor <goal-id> --ref=<bead-or-goal-or-text>")
		return 3
	}
	f := cli.ParseFlags(args[1:])
	ref := f.String("ref", "")
	if ref == "" {
		slog.Error("goal successor: --ref required")
		return 3
	}
	store, closeDB, rc := goalStore()
	if rc != 0 {
		return rc
	}
	defer closeDB()
	if err := store.SetSuccessor(ctx, args[0], ref); err != nil {
		slog.Error("goal successor failed", "error", err)
		return 2
	}
	return 0
}
```

**Step 2: Register in `main.go`** — add to the subcommand switch (alongside `case "run":`):

```go
	case "goal":
		exitCode = cmdGoal(ctx, subArgs)
```

and one line to the usage/help output: `goal      Goal entity: create, show, list, close, audit, lint-condition, successor`.

**Step 3: Build + smoke**
Run: `cd core/intercore && go build -o ic ./cmd/ic && ./ic goal lint-condition --text="go test ./... exits 0, or stop after 10 turns"`
Expected: `[]` on stdout… wait, warnings serialize too — expected output: JSON array (possibly `null`), exit 0.

**Step 4: Commit**
```bash
cd core/intercore
git add cmd/ic/goal.go cmd/ic/main.go
git commit -m "feat(goal): ic goal CLI noun — create/show/list/close/audit/lint-condition/successor"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go build -o /tmp/ic-verify ./cmd/ic && /tmp/ic-verify goal lint-condition --text="tests pass, or stop after 5 turns"; echo "exit=$?"`
  expect: contains "exit=0"
- run: `cd /Users/sma/projects/Sylveste/core/intercore && /tmp/ic-verify goal lint-condition --text="make it feel nice"; echo "exit=$?"`
  expect: contains "exit=1"
</verify>

### Task 7: Run attach — `--goal-id` + advance touch

**Files:**
- Modify: `core/intercore/internal/phase/phase.go` (Run struct: add `GoalID *string`)
- Modify: `core/intercore/internal/phase/store.go` (`Create` insert + scan columns; `UpdatePhase` touch)
- Modify: `core/intercore/cmd/ic/run_create.go` (`--goal-id` flag)
- Test: `core/intercore/internal/phase/store_test.go` (add cases)

**Step 1: Write the failing test** (append to `store_test.go`):

```go
func TestStore_RunGoalAttachAndTouch(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()
	// create a goal row directly (goals table exists via migration)
	if _, err := store.db.ExecContext(ctx,
		`INSERT INTO goals (id, project_dir, title) VALUES ('gtest123', '/tmp', 'g')`); err != nil {
		t.Fatal(err)
	}
	gid := "gtest123"
	run := &Run{ProjectDir: "/tmp/test", Goal: "labeled", Complexity: 3, AutoAdvance: true, GoalID: &gid}
	id, err := store.Create(ctx, run)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	got, _ := store.Get(ctx, id)
	if got.GoalID == nil || *got.GoalID != gid {
		t.Fatalf("GoalID not persisted: %+v", got)
	}
	if err := store.UpdatePhase(ctx, id, "brainstorm", "brainstorm-reviewed"); err != nil {
		t.Fatalf("UpdatePhase: %v", err)
	}
	var touched *int64
	if err := store.db.QueryRowContext(ctx,
		`SELECT last_run_advanced_at FROM goals WHERE id = ?`, gid).Scan(&touched); err != nil {
		t.Fatal(err)
	}
	if touched == nil {
		t.Error("last_run_advanced_at not touched by UpdatePhase")
	}
}
```

Note: if `store.db` is unexported differently (check the struct field name in `store.go:New`), use the same field the existing tests use for raw SQL — if none do, add the queries via a tiny exported test helper or query through `d.SqlDB()` captured in `setupTestStore`. Follow whichever pattern `store_test.go` already uses for direct SQL; do not invent a new one.

**Step 2: Run to confirm failure**
Run: `cd core/intercore && go test ./internal/phase/ -run GoalAttach -v`
Expected: FAIL (unknown field GoalID)

**Step 3: Implement** —
1. `phase.go` Run struct: add `GoalID *string` after `ParentRunID`.
2. `store.go Create`: add `goal_id` to the INSERT column list + value.
3. `store.go` row scanning (`Get`/`List`/scan helper): add `goal_id` to SELECT lists + `&r.GoalID` to Scan calls — locate every `SELECT` that enumerates run columns (`grep -n "parent_run_id" internal/phase/store.go` finds them all; add `goal_id` wherever `parent_run_id` appears).
4. `store.go UpdatePhase`: after the successful phase UPDATE, best-effort touch:

```go
	// Goal dormancy touch (f-031): any attached run's advance counts as
	// goal activity. Best-effort — never fail the advance over it.
	_, _ = s.db.ExecContext(ctx, `UPDATE goals
		SET last_run_advanced_at = unixepoch(), updated_at = unixepoch()
		WHERE id = (SELECT goal_id FROM runs WHERE id = ? AND goal_id IS NOT NULL)`, id)
```

(Plain-integer `unixepoch()` write is fine here — the TTL-in-Go rule targets TTL *arithmetic*, not timestamp stamps; this matches `DEFAULT (unixepoch())` usage across the schema.)
5. `run_create.go`: parse `goalID := f.String("goal-id", "")`; if non-empty set `run.GoalID = &goalID`.

**Step 4: Run tests**
Run: `cd core/intercore && go test ./internal/phase/ ./internal/goal/ -v 2>&1 | tail -5`
Expected: PASS (all — existing run tests must stay green; the scan-column additions are the risk point)

**Step 5: Commit**
```bash
cd core/intercore
git add internal/phase/phase.go internal/phase/store.go cmd/ic/run_create.go internal/phase/store_test.go
git commit -m "feat(goal): runs attach to goals (--goal-id); phase advance touches goal dormancy state (KD 3, f-031)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/phase/ 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 8: GoalNativeChain + goal-formed gate (KD 5/10)

**Files:**
- Modify: `core/intercore/pkg/phase/phase.go` (constants + chain)
- Modify: `core/intercore/internal/phase/phase.go` (re-export)
- Modify: `core/intercore/internal/phase/gate.go` (gateRules entry)
- Test: `core/intercore/internal/phase/gate_test.go` (add case following existing gate test pattern)

**Step 1: `pkg/phase/phase.go`** — append (DefaultChain UNTOUCHED, per f-004):

```go
// GoalFormed is the goal-native chain's head phase: the formation ritual
// has produced a ratified charter (the phase artifact) and minted the Goal
// entity. It absorbs Brainstorm/BrainstormReviewed/Strategized for
// goal-scale work (brainstorm KD 5) — DefaultChain is untouched; in-flight
// nil-Phases runs keep resolving to the legacy chain.
const GoalFormed = "goal-formed"

// GoalNativeChain is the goal-native lifecycle. Runs opt in via an explicit
// phases array stamped at creation (ic run create --phases=...) — never by
// editing DefaultChain.
var GoalNativeChain = []string{
	GoalFormed,
	Planned,
	Executing,
	Review,
	Polish,
	Reflect,
	Done,
}
```

**Step 2: `internal/phase/phase.go`** — add re-exports next to the existing `PhaseBrainstorm` aliases:

```go
const PhaseGoalFormed = exported.GoalFormed

var GoalNativePhaseChain = exported.GoalNativeChain
```

**Step 3: `internal/phase/gate.go`** — add to the `gateRules` map (charter is the goal-formed artifact):

```go
	{PhaseGoalFormed, PhasePlanned}: {
		{check: CheckArtifactExists, phase: PhaseGoalFormed},
	},
```

**Step 4: Test** — append to `gate_test.go`, following the file's existing table/setup pattern (find the existing `{PhaseBrainstorm, PhaseBrainstormReviewed}` artifact-gate test and clone it): create a run with `Phases: phase.GoalNativePhaseChain`, assert advance `goal-formed → planned` FAILS without a goal-formed artifact and PASSES once one is registered (same artifact-registration helper the sibling test uses).

**Step 5: Run tests**
Run: `cd core/intercore && go test ./internal/phase/ ./pkg/... -v 2>&1 | tail -5`
Expected: PASS

**Step 6: Commit**
```bash
cd core/intercore
git add pkg/phase/phase.go internal/phase/phase.go internal/phase/gate.go internal/phase/gate_test.go
git commit -m "feat(goal): GoalNativeChain + goal-formed artifact gate; DefaultChain untouched (KD 5/10)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./... 2>&1 | tail -1`
  expect: exit 0
- run: `cd /Users/sma/projects/Sylveste/core/intercore && git diff HEAD~1 -- pkg/phase/phase.go | grep -c "^-var DefaultChain\|^-\tBrainstorm"`
  expect: contains "0"
</verify>

---

## Stage C — Clavain surfaces

### Task 9: clavain-cli — `goal-mint` verb + blast-radius complexity bump

**Files:**
- Create: `os/Clavain/cmd/clavain-cli/goal.go`
- Modify: `os/Clavain/cmd/clavain-cli/main.go` (switch case + help line)
- Modify: `os/Clavain/cmd/clavain-cli/complexity.go` (blast-radius signals, f-009)
- Test: `os/Clavain/cmd/clavain-cli/goal_test.go`, extend `complexity_test.go`

**Step 1: Write failing tests.** `goal_test.go`:

```go
package main

import (
	"strings"
	"testing"
)

func TestFormatGoalPaste(t *testing.T) {
	out := formatGoalPaste("g1a2b3c4", "all tests exit 0, or stop after 20 turns")
	if !strings.Contains(out, "/goal all tests exit 0, or stop after 20 turns") {
		t.Errorf("missing paste line: %q", out)
	}
	if !strings.Contains(out, "g1a2b3c4") {
		t.Errorf("missing goal id: %q", out)
	}
}
```

Extend `complexity_test.go` (mirror an existing classify test case's calling convention exactly — find the test that exercises the ambiguity bump and clone it):

```go
func TestClassify_BlastRadiusBump(t *testing.T) {
	base := classifyText("update the widget list rendering")
	risky := classifyText("update the widget list and migrate the prod auth table")
	if risky <= base {
		t.Errorf("blast-radius text scored %d, want > %d", risky, base)
	}
}
```

(`classifyText` stands for whatever scoring entry point `complexity_test.go` already calls — use the existing test file's helper, do not invent a new export.)

**Step 2: Run to confirm failure**
Run: `cd os/Clavain/cmd/clavain-cli && go test ./... -run 'GoalPaste|BlastRadius' -v`
Expected: FAIL

**Step 3: Implement.** `complexity.go` — add below `ambiguitySignals` (mirroring its map+list pattern):

```go
// blastRadiusSignals bump complexity +1 when ANY is found (f-009).
// Rarer, stronger signals than ambiguitySignals, hence threshold 1 not >2.
var blastRadiusSignals = map[string]bool{
	"delete": true, "migrate": true, "migration": true, "drop": true,
	"auth": true, "prod": true, "production": true,
	"irreversible": true, "destructive": true,
}
```

and in the scoring function, immediately after the ambiguity bump (`complexity.go:96-98`):

```go
	if countMatchesInText(lowered, blastRadiusSignalsList) > 0 {
		score++
	}
```

(derive `blastRadiusSignalsList` the same way `ambiguitySignalsList` is derived from its map — copy the existing pattern.)

`goal.go`:

```go
package main

import (
	"fmt"
	"os"
	"strings"
)

// formatGoalPaste renders the mint result: durable entity id + the exact
// /goal invocation the user pastes to bind a session to it.
func formatGoalPaste(goalID, condition string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Goal minted: %s\n", goalID)
	fmt.Fprintf(&b, "Ready to paste:\n\n  /goal %s\n", condition)
	return b.String()
}

// cmdGoalMint lints, mints the intercore Goal entity, optionally binds a
// bead, and prints the /goal paste text (brainstorm KD 2/7).
// Usage: goal-mint <title> --project=<dir> --condition-file=<path>
//        [--charter=<path>] [--complexity=N] [--bead=<id>]
func cmdGoalMint(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("usage: goal-mint <title> --project=<dir> --condition-file=<path> [--charter=] [--complexity=] [--bead=]")
	}
	title := args[0]
	flags := parseKVFlags(args[1:]) // use the file-local flag helper the other verbs use; if none exists, parse --k=v pairs inline
	project := flags["project"]
	conditionFile := flags["condition-file"]
	if project == "" || conditionFile == "" {
		return fmt.Errorf("goal-mint: --project and --condition-file are required")
	}
	condBytes, err := os.ReadFile(conditionFile)
	if err != nil {
		return fmt.Errorf("goal-mint: read condition: %w", err)
	}
	condition := strings.TrimSpace(string(condBytes))

	createArgs := []string{"goal", "create", "--title=" + title, "--project=" + project,
		"--condition-file=" + conditionFile}
	if v := flags["charter"]; v != "" {
		createArgs = append(createArgs, "--charter="+v)
	}
	if v := flags["complexity"]; v != "" {
		createArgs = append(createArgs, "--complexity="+v)
	}
	if v := flags["bead"]; v != "" {
		createArgs = append(createArgs, "--bead="+v)
	}
	var res struct {
		ID string `json:"id"`
	}
	if err := runICJSON(&res, createArgs...); err != nil {
		return fmt.Errorf("goal-mint: ic goal create: %w", err)
	}
	if beadID := flags["bead"]; beadID != "" && bdAvailable() {
		if _, err := runBD("state", beadID, "ic_goal_id", res.ID); err != nil {
			fmt.Fprintf(os.Stderr, "goal-mint: bead bind failed (non-fatal): %v\n", err)
		}
	}
	fmt.Print(formatGoalPaste(res.ID, condition))
	return nil
}
```

(If no `parseKVFlags` helper exists in the package, write a 10-line one in `goal.go` that splits `--k=v` args into a map — check `grep -n "func parse" cmd/clavain-cli/*.go` first and reuse anything present.)

`main.go` switch: `case "goal-mint": err = cmdGoalMint(args)` + help line under an appropriate section.

**Step 4: Run tests**
Run: `cd os/Clavain/cmd/clavain-cli && go test ./... 2>&1 | tail -3`
Expected: PASS (all — existing complexity expectations must stay green; if a fixture text accidentally contains a blast keyword, adjust the new keyword list, not the fixture)

**Step 5: Commit**
```bash
cd os/Clavain
git add cmd/clavain-cli/goal.go cmd/clavain-cli/goal_test.go cmd/clavain-cli/main.go cmd/clavain-cli/complexity.go cmd/clavain-cli/complexity_test.go
git commit -m "feat(goal): goal-mint verb + blast-radius complexity bump (KD 7/14, f-009)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/os/Clavain/cmd/clavain-cli && go test ./... 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 10: Formation ritual command + route/next-goal wiring (KD 2/6/7)

**Files:**
- Create: `os/Clavain/commands/goal-form.md`
- Modify: `os/Clavain/commands/route.md` (goal-shaped branch)
- Modify: `os/Clavain/commands/next-goal.md` (audit step + draft-charter framing)

**Step 1: Write `commands/goal-form.md`:**

```markdown
---
name: goal-form
description: "Collaborative goal-formation ritual: research-first inter-elicitation → charter → stakes-routed review → mint (ic goal) → /goal handoff"
argument-hint: "[goal description or bead id]"
---

# Goal Formation Ritual

Form the best possible goal by maximizing comparative advantage: the USER
holds intent, stakes, taste, and go/no-go; YOU hold research breadth, prior
art, repo state, and candidate enumeration. The ritual front-loads
collaboration where errors compound — /goal is a work-until-done loop, so
goal quality is the highest-leverage variable in the cycle.

## Step 1 — Research first (never ask what you can derive)

Before any question: `bd ready` + `bd show` on candidate beads, repo state,
`ic goal list --project="$PWD" --status=open` (existing goals), and
`ic goal audit --project="$PWD"` (defects that may deserve the next goal).
For seeded candidates (from /clavain:next-goal), the seed bead's description
is ONE MORE RESEARCH INPUT — run the full pass anyway (KD 13).

## Step 2 — Stakes classification

`clavain-cli classify-complexity "" "<description>"` → C1–C5 routes ceremony:
- **C1:** ONE confirming AskUserQuestion, then draft the charter directly.
- **C2–C3:** short interview (2-4 single questions), charter, lint, mint.
- **C4–C5:** full interview + flux-melange review of the charter before
  ratification (`/flux-melange <charter> --goal="stress-test this goal
  charter: scope, condition judgeability, risks, alternatives"`).

## Step 3 — Interview (single-question AskUserQuestion, one at a time)

Ask ONLY genuine user-authority questions: intent, success definition,
scope appetite, risk tolerance, tradeoffs. Progression: purpose →
constraints → success criteria → edge cases. Recommended option FIRST.
Anchoring instrumentation (KD 13): after each question, record
(first-listed option, chosen option) via
`clavain-cli interspect-evidence goal-form-anchor "<first>" "<chosen>"`
if the verb exists; otherwise skip silently.

## Step 4 — Charter

Write `docs/goals/YYYY-MM-DD-<slug>-charter.md`: Title · Why (leverage) ·
Scope (in/out) · Acceptance criteria · **Completion condition** (the
LITERAL string handed to /goal — never a paraphrase; write it so the
evaluator can judge it from surfaced output: commands, exit codes, bead
closes; bound it with "or stop after N turns") · Successor obligations.

## Step 5 — Lint + mint

`ic goal lint-condition --file=<condition-extract>` — fix errors (the
tier-independent gate; C1 goals get this too). Then:
`clavain-cli goal-mint "<title>" --project="$PWD" --condition-file=<path>
--charter=<charter-path> --complexity=<N> [--bead=<id>]`
Bead binding is stakes-scaled (KD 3): epic for C4/C5, task bead or none
for C1.

## Step 6 — Handoff

Print the goal-mint paste block verbatim and STOP. The user invokes /goal —
session binding is theirs, not yours.
```

**Step 2: `route.md`** — add a goal-shaped branch where the command classifies input (locate the bead-ID-regex branch; add alongside):

```markdown
- **Goal-scale input** (mentions "goal", spans multiple work items, or names an
  outcome rather than a task): route to `/clavain:goal-form` — the formation
  ritual owns charter + mint + /goal handoff. Do not start ordinary
  implementation for goal-scale asks.
```

**Step 3: `next-goal.md`** — two edits:
1. In Step 1 (gather candidates), append: `Also run \`ic goal audit --project="$PWD"\` (fail-open if ic missing) — audit defects (dormant goals, stuck closes, missing successors) are candidate material and MUST be surfaced ahead of new work (f-030).`
2. In Step 4 (emit block), append: `Frame each candidate as a DRAFT CHARTER seed: the recommendation's /goal text must be lint-clean (\`ic goal lint-condition\`) and the block should note that /clavain:goal-form turns a candidate into a ratified charter (KD 7).`

**Step 4: Commit**
```bash
cd os/Clavain
git add commands/goal-form.md commands/route.md commands/next-goal.md
git commit -m "feat(goal): formation ritual command + route/next-goal goal-native wiring (KD 2/6/7)"
```

<verify>
- run: `test -f /Users/sma/projects/Sylveste/os/Clavain/commands/goal-form.md && grep -c "lint-condition" /Users/sma/projects/Sylveste/os/Clavain/commands/goal-form.md`
  expect: exit 0
- run: `grep -c "goal-form" /Users/sma/projects/Sylveste/os/Clavain/commands/route.md /Users/sma/projects/Sylveste/os/Clavain/commands/next-goal.md | grep -cv ":0"`
  expect: contains "2"
</verify>

### Task 11: Entity-backed goal-cadence hook (f-016/f-020)

**Files:**
- Create: `os/Clavain/hooks/lib-goal-audit.sh`
- Modify: `os/Clavain/hooks/auto-stop-actions.sh` (source + branch after the existing goal-cadence tier, ~line 146)
- Test: `os/Clavain/tests/shell/goal_audit.bats`

**Step 1: Write the failing bats test** — `tests/shell/goal_audit.bats`:

```bash
#!/usr/bin/env bats
# Tests for hooks/lib-goal-audit.sh

setup() {
    load test_helper
    source "$HOOKS_DIR/lib-goal-audit.sh"
    STUB_DIR="$(mktemp -d)"
    export PATH="$STUB_DIR:$PATH"
}

teardown() {
    rm -rf "$STUB_DIR"
}

make_ic_stub() {
    # $1 = audit stdout, $2 = audit exit code
    cat > "$STUB_DIR/ic" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "health" ]]; then exit 0; fi
if [[ "\$1" == "sentinel" ]]; then exit 0; fi
if [[ "\$1" == "goal" && "\$2" == "audit" ]]; then echo '$1'; exit $2; fi
exit 0
EOF
    chmod +x "$STUB_DIR/ic"
}

@test "goal_audit_reason: empty when no defects" {
    make_ic_stub "[]" 0
    run goal_audit_reason "test-session"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "goal_audit_reason: fires on defects" {
    make_ic_stub '[{"goal_id":"g1","kind":"dormant"}]' 1
    run goal_audit_reason "test-session"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Goal audit"* ]]
}

@test "goal_audit_reason: fail-open when ic absent" {
    export INTERCORE_BIN=""
    export PATH="/usr/bin:/bin"
    run goal_audit_reason "test-session"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}
```

**Step 2: Run to confirm failure**
Run: `cd os/Clavain && bats tests/shell/goal_audit.bats`
Expected: FAIL (lib-goal-audit.sh not found)

**Step 3: Write `hooks/lib-goal-audit.sh`:**

```bash
#!/usr/bin/env bash
# lib-goal-audit.sh — entity-backed goal-cadence check (f-016/f-030).
# The standing auditor: fires on ic goal audit defects, independent of the
# goal-completed prose signal. Everything fails open (lib-intercore.sh idiom).

# Callers must have sourced lib-intercore.sh first.

# goal_audit_reason <session_id>
# Prints a Stop-hook REASON string when audit defects exist; empty otherwise.
# Always returns 0 (fail-open).
goal_audit_reason() {
    local session_id="$1"
    if ! type intercore_available >/dev/null 2>&1 || ! intercore_available; then
        return 0
    fi
    if ! intercore_sentinel_check_or_legacy "goal_audit_throttle" "$session_id" 3600; then
        return 0
    fi
    local defects
    defects=$("$INTERCORE_BIN" goal audit --project="$PWD" --dormant-after=604800 2>/dev/null) || true
    if [[ -n "$defects" && "$defects" != "[]" && "$defects" != "null" ]]; then
        printf 'Goal audit: this project has goal defects (dormant, stuck-closing, or closed-without-successor). Run `ic goal audit --project="%s"` and surface each defect to the user with a proposed action (resume, abandon-with-reason, or propose successor).' "$PWD"
    fi
    return 0
}
```

**Step 4: Wire into `auto-stop-actions.sh`** — near the other `source` lines add `source "$SCRIPT_DIR/lib-goal-audit.sh"` (match the file's existing source idiom), and immediately after the existing goal-cadence tier block:

```bash
# Entity-backed goal audit (f-016): the standing auditor, independent of
# prose signals. Only consulted when no higher tier fired.
if [[ -z "$REASON" ]] && [[ ! -f ".claude/clavain.no-goalcadence" ]]; then
    AUDIT_REASON=$(goal_audit_reason "$SESSION_ID")
    if [[ -n "$AUDIT_REASON" ]]; then
        REASON="$AUDIT_REASON"
    fi
fi
```

**Step 5: Run tests**
Run: `cd os/Clavain && bats tests/shell/goal_audit.bats && bats tests/shell/lib_signals.bats`
Expected: PASS (new + existing)

**Step 6: Commit**
```bash
cd os/Clavain
git add hooks/lib-goal-audit.sh hooks/auto-stop-actions.sh tests/shell/goal_audit.bats
git commit -m "feat(goal): entity-backed goal-cadence audit in Stop hook, fail-open (f-016/f-030)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/os/Clavain && bats tests/shell/goal_audit.bats 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 12: Interband sideband parity from sprint-advance (KD 11)

**Files:**
- Create: `os/Clavain/cmd/clavain-cli/sideband.go`
- Modify: `os/Clavain/cmd/clavain-cli/phase.go` (`cmdSprintAdvance` success path)
- Test: `os/Clavain/cmd/clavain-cli/sideband_test.go`

The goal-native authority writes the SAME envelope interphase writes today (`~/.interband/interphase/bead/${session_id}.json` + legacy `/tmp/clavain-bead-${session_id}.json`), so `interline/scripts/statusline.sh` keeps working and interphase's writer becomes redundant — the retirement precondition.

**Step 1: Write the failing test** — `sideband_test.go`:

```go
package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestWriteBeadSideband_EnvelopeShape(t *testing.T) {
	root := t.TempDir()
	t.Setenv("INTERBAND_ROOT", root)
	if err := writeBeadSideband("sess-1", "bead-9", "executing", "advanced"); err != nil {
		t.Fatalf("writeBeadSideband: %v", err)
	}
	b, err := os.ReadFile(filepath.Join(root, "interphase", "bead", "sess-1.json"))
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	var env struct {
		Version   string `json:"version"`
		Namespace string `json:"namespace"`
		Type      string `json:"type"`
		SessionID string `json:"session_id"`
		Timestamp string `json:"timestamp"`
		Payload   struct {
			ID     string `json:"id"`
			Phase  string `json:"phase"`
			Reason string `json:"reason"`
			Ts     int64  `json:"ts"`
		} `json:"payload"`
	}
	if err := json.Unmarshal(b, &env); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if env.Namespace != "interphase" || env.Type != "bead_phase" || env.SessionID != "sess-1" {
		t.Errorf("envelope: %+v", env)
	}
	if env.Payload.ID != "bead-9" || env.Payload.Phase != "executing" || env.Payload.Ts == 0 {
		t.Errorf("payload: %+v", env.Payload)
	}
}

func TestWriteBeadSideband_NoSessionIsNoop(t *testing.T) {
	if err := writeBeadSideband("", "b", "p", ""); err != nil {
		t.Errorf("empty session should no-op, got %v", err)
	}
}
```

**Step 2: Run to confirm failure** — `cd os/Clavain/cmd/clavain-cli && go test -run Sideband -v` → FAIL.

**Step 3: Write `sideband.go`:**

```go
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// writeBeadSideband mirrors interphase's _gate_update_statusline envelope
// (interband protocol 1.0.0) so the statusline keeps working as interphase
// retires (brainstorm KD 11). Both writes are atomic tmp+rename,
// best-effort at call sites.
func writeBeadSideband(sessionID, beadID, phase, reason string) error {
	if sessionID == "" {
		return nil
	}
	now := time.Now()
	payload := map[string]any{"id": beadID, "phase": phase, "reason": reason, "ts": now.Unix()}
	env := map[string]any{
		"version":    "1.0.0",
		"namespace":  "interphase",
		"type":       "bead_phase",
		"session_id": sessionID,
		"timestamp":  now.UTC().Format("2006-01-02T15:04:05Z"),
		"payload":    payload,
	}
	envBytes, err := json.Marshal(env)
	if err != nil {
		return err
	}
	root := os.Getenv("INTERBAND_ROOT")
	if root == "" {
		home, herr := os.UserHomeDir()
		if herr != nil {
			return herr
		}
		root = filepath.Join(home, ".interband")
	}
	dir := filepath.Join(root, "interphase", "bead")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	if err := atomicWrite(filepath.Join(dir, sessionID+".json"), envBytes); err != nil {
		return err
	}
	// Legacy fallback path interline still reads.
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	return atomicWrite(filepath.Join(os.TempDir(), "clavain-bead-"+sessionID+".json"), payloadBytes)
}

func atomicWrite(path string, data []byte) error {
	tmp := fmt.Sprintf("%s.tmp.%d", path, os.Getpid())
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}
```

**Step 4: Call from `cmdSprintAdvance`** — in the success path (after the transition is printed), add:

```go
	// Sideband parity (KD 11): keep the statusline current without interphase.
	if sid := os.Getenv("CLAUDE_SESSION_ID"); sid != "" {
		_ = writeBeadSideband(sid, beadID, result.ToPhase, "sprint-advance")
	}
```

(`result.ToPhase` — use whatever field `AdvanceResult` actually exposes for the new phase; check the struct in `phase.go` and use its real name.)

**Step 5: Run tests + file the interline companion bead**
Run: `cd os/Clavain/cmd/clavain-cli && go test ./... 2>&1 | tail -1` → PASS.
Then (from the Sylveste root):
```bash
bd create --title="interline: interphase sideband writer redundancy — cutover checklist for interphase retirement" \
  --description="clavain-cli sprint-advance now writes the interphase/bead interband envelope (goal-native plan task 12, KD 11). interline keeps reading the same paths. Cutover: verify dual-writer parity in live sessions, then retire interphase's _gate_update_statusline writer and its hooks; interline needs no change unless the envelope moves namespaces." \
  --type=task --priority=2
```

**Step 6: Commit**
```bash
cd os/Clavain
git add cmd/clavain-cli/sideband.go cmd/clavain-cli/sideband_test.go cmd/clavain-cli/phase.go
git commit -m "feat(goal): interband bead sideband from sprint-advance — interphase retirement parity (KD 11)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/os/Clavain/cmd/clavain-cli && go test -run Sideband ./... 2>&1 | tail -1`
  expect: exit 0
</verify>

---

## Stage E — Validation

### Task 13: Two-session race test (melange caveat: demonstrate, don't just read)

**Files:**
- Create: `core/intercore/internal/goal/race_test.go`

**Step 1: Write the test:**

```go
package goal

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
)

// TestAcquireClose_TwoSessionRace demonstrates the double-witness prevention
// the melange flagged as source-read-only (f-001/f-025): N concurrent
// sessions race to close one goal; exactly one may hold the lease.
// Run with -race.
func TestAcquireClose_TwoSessionRace(t *testing.T) {
	s := setupTestStore(t)
	ctx := context.Background()
	id := mkGoal(t, s)

	const n = 16
	var wins, held int64
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			_, err := s.AcquireClose(ctx, id, "run", "owner", 3600)
			switch {
			case err == nil:
				atomic.AddInt64(&wins, 1)
			case errors.Is(err, ErrLeaseHeld):
				atomic.AddInt64(&held, 1)
			default:
				t.Errorf("unexpected error: %v", err)
			}
		}(i)
	}
	wg.Wait()
	if wins != 1 {
		t.Errorf("winners = %d, want exactly 1 (held=%d)", wins, held)
	}
	if wins+held != n {
		t.Errorf("wins+held = %d, want %d", wins+held, n)
	}
}
```

**Step 2: Run under the race detector**
Run: `cd core/intercore && go test -race ./internal/goal/ -run TwoSessionRace -v`
Expected: PASS, no race reports

**Step 3: Commit**
```bash
cd core/intercore
git add internal/goal/race_test.go
git commit -m "test(goal): two-session close race — exclusive lease demonstrated under -race (f-025)"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test -race ./internal/goal/ -run TwoSessionRace 2>&1 | tail -1`
  expect: exit 0
</verify>

### Task 14: E2E lifecycle test

**Files:**
- Create: `core/intercore/internal/goal/e2e_test.go` (package `goal_test` — imports both goal and phase)

**Step 1: Write the test:**

```go
package goal_test

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/mistakeknot/intercore/internal/db"
	"github.com/mistakeknot/intercore/internal/goal"
	"github.com/mistakeknot/intercore/internal/phase"
)

// TestGoalLifecycleE2E: mint → lint → run attach → advance (dormancy touch)
// → audit clean → fenced close sequence → successor → audit clean.
func TestGoalLifecycleE2E(t *testing.T) {
	ctx := context.Background()
	d, err := db.Open(filepath.Join(t.TempDir(), "e2e.db"), 100*time.Millisecond)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { d.Close() })
	if err := d.Migrate(ctx); err != nil {
		t.Fatal(err)
	}
	gs := goal.New(d.SqlDB())
	ps := phase.New(d.SqlDB())

	cond := "`go test ./...` exits 0, or stop after 20 turns"
	if probs := goal.LintCondition(cond); len(probs) != 0 {
		t.Fatalf("condition should lint clean: %v", probs)
	}
	gid, err := gs.Create(ctx, &goal.Goal{ProjectDir: "/tmp/p", Title: "e2e", ConditionText: cond})
	if err != nil {
		t.Fatal(err)
	}

	rid, err := ps.Create(ctx, &phase.Run{ProjectDir: "/tmp/p", Goal: "e2e", Complexity: 2,
		AutoAdvance: true, GoalID: &gid})
	if err != nil {
		t.Fatal(err)
	}
	if err := ps.UpdatePhase(ctx, rid, "brainstorm", "brainstorm-reviewed"); err != nil {
		t.Fatal(err)
	}

	if defects, _ := gs.Audit(ctx, "/tmp/p", 3600); len(defects) != 0 {
		t.Fatalf("healthy goal audited dirty: %v", defects)
	}

	fence, err := gs.AcquireClose(ctx, gid, rid, "e2e-session", 3600)
	if err != nil {
		t.Fatal(err)
	}
	for _, step := range []string{"verified", "reflected", "compounded", "successor_proposed"} {
		if err := gs.StampStep(ctx, gid, step, fence); err != nil {
			t.Fatalf("stamp %s: %v", step, err)
		}
	}
	if err := gs.SetSuccessor(ctx, gid, "bead:next-1"); err != nil {
		t.Fatal(err)
	}
	if err := gs.FinishClose(ctx, gid, fence); err != nil {
		t.Fatal(err)
	}
	if defects, _ := gs.Audit(ctx, "/tmp/p", 3600); len(defects) != 0 {
		t.Fatalf("closed-with-successor audited dirty: %v", defects)
	}
}
```

**Step 2: Run**
Run: `cd core/intercore && go test ./internal/goal/ -run E2E -v`
Expected: PASS

**Step 3: Commit**
```bash
cd core/intercore
git add internal/goal/e2e_test.go
git commit -m "test(goal): full lifecycle E2E — mint to audited-clean close"
```

<verify>
- run: `cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ -run E2E 2>&1 | tail -1`
  expect: exit 0
</verify>

---

## Explicitly Deferred (do not build)

- `ic goal amend` verb — amendments re-ratify through the ritual for now; `amended_at` column ships unused (KD 12 note).
- The `CheckGoalConditionValid` gate-check type (f-014) — mint-time refusal covers the tier-independent gate in v1; the GateCondition wiring (querier threading through every EvaluateGate caller) lands with the first per-run goal-gate consumer.
- interphase writer removal — gated on the interline companion bead's live parity verification (task 12 files it).
- lbkd/3kol subsume/supersede verdicts — strategy Phase 0.5 hard gate, not plan work.
- Any daemon/cron for the auditor — `ic goal audit` is one-shot by design; scheduling belongs to zklw cron or the Stop-hook cadence (task 11), matching intercore's no-daemon architecture.

## Acceptance Criteria

1. Full intercore suite green, including the new goal package.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test ./...
   ```
2. Exclusive fenced close demonstrated under the race detector.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test -race ./internal/goal/ -run 'TwoSessionRace|Acquire|Finish'
   ```
3. Condition lint gates minting: valid conditions exit 0, undemonstrable ones exit 1.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go build -o /tmp/ic-ac ./cmd/ic && /tmp/ic-ac goal lint-condition --text="tests pass, or stop after 5 turns" && ! /tmp/ic-ac goal lint-condition --text="make it feel nice"
   ```
4. DefaultChain untouched: legacy 9-phase chain still resolves for nil-Phases runs.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/phase/ -run 'Chain|Resolve' && grep -A11 "var DefaultChain" pkg/phase/phase.go | grep -q Strategized
   ```
5. clavain-cli suite green with goal-mint + blast-radius bump.
   ```check
   cd /Users/sma/projects/Sylveste/os/Clavain/cmd/clavain-cli && go test ./...
   ```
6. Entity-backed cadence hook is tested and fail-open.
   ```check
   cd /Users/sma/projects/Sylveste/os/Clavain && bats tests/shell/goal_audit.bats
   ```
7. Sideband envelope matches the interline reader contract.
   ```check
   cd /Users/sma/projects/Sylveste/os/Clavain/cmd/clavain-cli && go test -run Sideband ./...
   ```
8. Ritual + wiring docs exist and reference each other.
   ```check
   grep -q "lint-condition" /Users/sma/projects/Sylveste/os/Clavain/commands/goal-form.md && grep -q "goal-form" /Users/sma/projects/Sylveste/os/Clavain/commands/route.md && grep -q "goal audit" /Users/sma/projects/Sylveste/os/Clavain/commands/next-goal.md
   ```
9. E2E lifecycle green.
   ```check
   cd /Users/sma/projects/Sylveste/core/intercore && go test ./internal/goal/ -run E2E
   ```

