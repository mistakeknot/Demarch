# Intercore Rollback and Recovery (E6) Implementation Plan
**Phase:** executing (as of 2026-02-20T17:31:01Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Add `ic run rollback` with workflow state rollback (phase rewind + dispatch/artifact marking) and code rollback query to intercore.

**Architecture:** New `Rollback()` function in the phase machine mirrors `Advance()` but goes backward. Schema v8 adds `status` column to `run_artifacts`. The rollback CLI subcommand supports `--to-phase` for workflow rewind, `--layer=code` for commit metadata query, and `--dry-run` for preview. Dispatch/artifact marking happens in the same transaction as the phase rewind.

**Tech Stack:** Go 1.22, SQLite (modernc.org/sqlite), standard `testing` package, bash wrapper.

**PRD:** docs/prds/2026-02-20-intercore-rollback-recovery.md
**Beads:** iv-atki (F1), iv-bld6 (F2), iv-vlvn (F3), iv-d5we (F4), iv-rp3m (F5)

---

## Task 1: Schema Migration v7 → v8 (F1: iv-atki)

**Files:**
- Modify: `infra/intercore/internal/db/db.go:21-24` (version constants)
- Modify: `infra/intercore/internal/db/db.go:136-154` (migration function)
- Modify: `infra/intercore/internal/db/schema.sql:105-116` (run_artifacts table)
- Test: `infra/intercore/internal/db/db_test.go`

**Step 1: Write the failing test**

Add to `infra/intercore/internal/db/db_test.go`:

```go
func TestMigrateV7ToV8_ArtifactStatus(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test.db")

	// Create a v7 database
	d, err := Open(path, 100*time.Millisecond)
	if err != nil {
		t.Fatal(err)
	}
	if err := d.Migrate(context.Background()); err != nil {
		t.Fatal(err)
	}
	d.Close()

	// Verify we're at v8 after migration
	d2, err := Open(path, 100*time.Millisecond)
	if err != nil {
		t.Fatal(err)
	}
	defer d2.Close()

	v, err := d2.SchemaVersion()
	if err != nil {
		t.Fatal(err)
	}
	if v != 8 {
		t.Fatalf("expected schema version 8, got %d", v)
	}

	// Verify status column exists on run_artifacts with default 'active'
	var colDefault sql.NullString
	err = d2.SqlDB().QueryRow(
		"SELECT dflt_value FROM pragma_table_info('run_artifacts') WHERE name='status'",
	).Scan(&colDefault)
	if err != nil {
		t.Fatalf("status column not found on run_artifacts: %v", err)
	}
	if !colDefault.Valid || colDefault.String != "'active'" {
		t.Fatalf("expected default 'active', got %v", colDefault)
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/db/ -run TestMigrateV7ToV8 -v`
Expected: FAIL — schema version is still 7, no `status` column.

**Step 3: Update schema version constants**

In `infra/intercore/internal/db/db.go`, change lines 21-24:

```go
const (
	currentSchemaVersion = 8
	maxSchemaVersion     = 8
)
```

**Step 4: Add status column to schema.sql**

In `infra/intercore/internal/db/schema.sql`, update the `run_artifacts` table (after `dispatch_id TEXT` line, around line 112):

Add `status TEXT NOT NULL DEFAULT 'active',` between `dispatch_id` and `created_at`.

The full table should be:
```sql
CREATE TABLE IF NOT EXISTS run_artifacts (
    id          TEXT NOT NULL PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES runs(id),
    phase       TEXT NOT NULL,
    path        TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'file',
    content_hash TEXT,
    dispatch_id TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  INTEGER NOT NULL DEFAULT (unixepoch())
);
```

**Step 5: Add v7→v8 migration**

In `infra/intercore/internal/db/db.go`, inside `Migrate()`, after the v5→v6 block (after line 153), add:

```go
	// v7 → v8: add status column to run_artifacts
	if currentVersion >= 7 {
		v8Stmts := []string{
			"ALTER TABLE run_artifacts ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
		}
		for _, stmt := range v8Stmts {
			if _, err := tx.ExecContext(ctx, stmt); err != nil {
				if !isDuplicateColumnError(err) {
					return fmt.Errorf("migrate v7→v8: %w", err)
				}
			}
		}
	}
```

**Step 6: Run test to verify it passes**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/db/ -run TestMigrateV7ToV8 -v`
Expected: PASS

**Step 7: Run all existing tests to verify no regressions**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/db/ -v`
Expected: All PASS

**Step 8: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add internal/db/db.go internal/db/schema.sql internal/db/db_test.go
git commit -m "feat(db): schema v8 — add status column to run_artifacts"
```

---

## Task 2: Rollback Event Type and Error Constants (F2: iv-bld6)

**Files:**
- Modify: `infra/intercore/internal/phase/phase.go:30-38` (event constants)
- Modify: `infra/intercore/internal/phase/errors.go` (new error)

**Step 1: Add rollback event type constant**

In `infra/intercore/internal/phase/phase.go`, add to the event type constants block (after `EventSet` on line 37):

```go
	EventRollback = "rollback"
```

**Step 2: Add rollback error sentinel**

In `infra/intercore/internal/phase/errors.go`, add after `ErrTerminalPhase`:

```go
	ErrInvalidRollback = errors.New("cannot roll back: target phase is not behind current phase")
```

**Step 3: Add ChainPhaseIndex helper**

In `infra/intercore/internal/phase/phase.go`, after the `ChainContains` function (after line 155):

```go
// ChainPhaseIndex returns the index of phase in chain, or -1 if not found.
func ChainPhaseIndex(chain []string, p string) int {
	for i, cp := range chain {
		if cp == p {
			return i
		}
	}
	return -1
}

// ChainPhasesBetween returns the phases strictly between from and to (exclusive on both ends).
// Returns nil if from is not before to in the chain.
func ChainPhasesBetween(chain []string, from, to string) []string {
	fromIdx := ChainPhaseIndex(chain, from)
	toIdx := ChainPhaseIndex(chain, to)
	if fromIdx < 0 || toIdx < 0 || fromIdx >= toIdx {
		return nil
	}
	// Phases from fromIdx+1 to toIdx (exclusive of from, inclusive of to — we want the phases that get rolled back)
	// Actually: we want phases after target up to and including current, because those are the ones being rolled back
	result := make([]string, 0, toIdx-fromIdx)
	for i := fromIdx + 1; i <= toIdx; i++ {
		result = append(result, chain[i])
	}
	return result
}
```

**Step 4: Write tests for new chain helpers**

In `infra/intercore/internal/phase/phase_test.go`, add:

```go
func TestChainPhaseIndex(t *testing.T) {
	chain := []string{"a", "b", "c", "d"}
	tests := []struct {
		phase string
		want  int
	}{
		{"a", 0}, {"b", 1}, {"d", 3}, {"x", -1},
	}
	for _, tt := range tests {
		if got := ChainPhaseIndex(chain, tt.phase); got != tt.want {
			t.Errorf("ChainPhaseIndex(%q) = %d, want %d", tt.phase, got, tt.want)
		}
	}
}

func TestChainPhasesBetween(t *testing.T) {
	chain := []string{"a", "b", "c", "d", "e"}
	tests := []struct {
		from, to string
		want     []string
	}{
		{"a", "d", []string{"b", "c", "d"}},
		{"b", "d", []string{"c", "d"}},
		{"a", "b", []string{"b"}},
		{"d", "a", nil}, // backward = nil
		{"a", "a", nil}, // same = nil
		{"x", "d", nil}, // not found = nil
	}
	for _, tt := range tests {
		got := ChainPhasesBetween(chain, tt.from, tt.to)
		if len(got) != len(tt.want) {
			t.Errorf("ChainPhasesBetween(%q, %q) = %v, want %v", tt.from, tt.to, got, tt.want)
			continue
		}
		for i := range got {
			if got[i] != tt.want[i] {
				t.Errorf("ChainPhasesBetween(%q, %q)[%d] = %q, want %q", tt.from, tt.to, i, got[i], tt.want[i])
			}
		}
	}
}
```

**Step 5: Run tests**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -run "TestChainPhase" -v`
Expected: PASS

**Step 6: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add internal/phase/phase.go internal/phase/errors.go internal/phase/phase_test.go
git commit -m "feat(phase): add rollback event type, error, and chain helper functions"
```

---

## Task 3: Store-Level Rollback Methods (F2: iv-bld6)

**Files:**
- Modify: `infra/intercore/internal/phase/store.go` (new methods)
- Test: `infra/intercore/internal/phase/store_test.go`

**Step 1: Write the failing test for RollbackPhase**

Add to `infra/intercore/internal/phase/store_test.go`:

```go
func TestRollbackPhase(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	// Create a run and advance it twice: brainstorm → brainstorm-reviewed → strategized
	id, err := store.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test rollback"})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.UpdatePhase(ctx, id, "brainstorm", "brainstorm-reviewed"); err != nil {
		t.Fatal(err)
	}
	if err := store.UpdatePhase(ctx, id, "brainstorm-reviewed", "strategized"); err != nil {
		t.Fatal(err)
	}

	// Rollback to brainstorm
	err = store.RollbackPhase(ctx, id, "strategized", "brainstorm")
	if err != nil {
		t.Fatalf("RollbackPhase failed: %v", err)
	}

	// Verify phase is now brainstorm
	run, err := store.Get(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != "brainstorm" {
		t.Fatalf("expected phase brainstorm, got %s", run.Phase)
	}
}

func TestRollbackPhase_NotBehind(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	id, err := store.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}

	// Try to roll back to a phase ahead of current — should fail
	err = store.RollbackPhase(ctx, id, "brainstorm", "strategized")
	if err == nil {
		t.Fatal("expected error for forward rollback")
	}
}

func TestRollbackPhase_CompletedRun(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	id, err := store.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}
	// Advance to done and mark completed
	if err := store.UpdatePhase(ctx, id, "brainstorm", "done"); err != nil {
		t.Fatal(err)
	}
	if err := store.UpdateStatus(ctx, id, phase.StatusCompleted); err != nil {
		t.Fatal(err)
	}

	// Rollback should revert status to active
	err = store.RollbackPhase(ctx, id, "done", "brainstorm")
	if err != nil {
		t.Fatalf("RollbackPhase on completed run failed: %v", err)
	}

	run, err := store.Get(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	if run.Status != phase.StatusActive {
		t.Fatalf("expected status active, got %s", run.Status)
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -run "TestRollbackPhase" -v`
Expected: FAIL — `RollbackPhase` method doesn't exist.

**Step 3: Implement RollbackPhase**

Add to `infra/intercore/internal/phase/store.go`, after `UpdateSettings()` (after line 222):

```go
// RollbackPhase rewinds a run's phase pointer backward. Unlike UpdatePhase,
// this uses a direct UPDATE (no optimistic concurrency) because rollback is
// an authoritative operation. If the run is in a terminal status (completed),
// it reverts to active.
func (s *Store) RollbackPhase(ctx context.Context, id, currentPhase, targetPhase string) error {
	run, err := s.Get(ctx, id)
	if err != nil {
		return err
	}

	// Reject cancelled/failed runs (but allow completed — rollback reverts it)
	if run.Status == StatusCancelled || run.Status == StatusFailed {
		return ErrTerminalRun
	}

	chain := ResolveChain(run)

	// Validate both phases exist in chain
	if !ChainContains(chain, targetPhase) {
		return fmt.Errorf("rollback: target phase %q not in chain", targetPhase)
	}
	if !ChainContains(chain, currentPhase) {
		return fmt.Errorf("rollback: current phase %q not in chain", currentPhase)
	}

	// Validate target is behind current
	targetIdx := ChainPhaseIndex(chain, targetPhase)
	currentIdx := ChainPhaseIndex(chain, currentPhase)
	if targetIdx >= currentIdx {
		return ErrInvalidRollback
	}

	now := time.Now().Unix()
	result, err := s.db.ExecContext(ctx, `
		UPDATE runs SET phase = ?, status = 'active', updated_at = ?, completed_at = NULL
		WHERE id = ?`,
		targetPhase, now, id,
	)
	if err != nil {
		return fmt.Errorf("rollback phase: %w", err)
	}
	n, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("rollback phase: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -run "TestRollbackPhase" -v`
Expected: PASS

**Step 5: Run full phase test suite**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add internal/phase/store.go internal/phase/store_test.go
git commit -m "feat(phase): add RollbackPhase store method with backward transition"
```

---

## Task 4: Rollback Machine Function (F2: iv-bld6)

**Files:**
- Modify: `infra/intercore/internal/phase/machine.go` (new Rollback function)
- Test: `infra/intercore/internal/phase/machine_test.go`

**Step 1: Write the failing test**

Add to `infra/intercore/internal/phase/machine_test.go`:

```go
func TestRollback_Basic(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	id, err := store.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test rollback"})
	if err != nil {
		t.Fatal(err)
	}
	// Advance to strategized
	if err := store.UpdatePhase(ctx, id, "brainstorm", "brainstorm-reviewed"); err != nil {
		t.Fatal(err)
	}
	if err := store.UpdatePhase(ctx, id, "brainstorm-reviewed", "strategized"); err != nil {
		t.Fatal(err)
	}

	var callbackCalled bool
	callback := func(runID, eventType, fromPhase, toPhase, reason string) {
		callbackCalled = true
		if eventType != phase.EventRollback {
			t.Errorf("callback event type = %q, want %q", eventType, phase.EventRollback)
		}
	}

	result, err := phase.Rollback(ctx, store, id, "brainstorm", "test reason", callback)
	if err != nil {
		t.Fatalf("Rollback failed: %v", err)
	}

	if result.FromPhase != "strategized" {
		t.Errorf("FromPhase = %q, want %q", result.FromPhase, "strategized")
	}
	if result.ToPhase != "brainstorm" {
		t.Errorf("ToPhase = %q, want %q", result.ToPhase, "brainstorm")
	}
	if !callbackCalled {
		t.Error("callback was not called")
	}

	// Verify the run's phase was updated
	run, err := store.Get(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	if run.Phase != "brainstorm" {
		t.Errorf("run.Phase = %q, want %q", run.Phase, "brainstorm")
	}

	// Verify rollback event was recorded
	events, err := store.Events(ctx, id)
	if err != nil {
		t.Fatal(err)
	}
	var found bool
	for _, e := range events {
		if e.EventType == phase.EventRollback {
			found = true
			if e.FromPhase != "strategized" || e.ToPhase != "brainstorm" {
				t.Errorf("rollback event: from=%q to=%q, want from=strategized to=brainstorm", e.FromPhase, e.ToPhase)
			}
		}
	}
	if !found {
		t.Error("no rollback event found in audit trail")
	}
}

func TestRollback_TerminalRun(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	id, err := store.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.UpdateStatus(ctx, id, phase.StatusCancelled); err != nil {
		t.Fatal(err)
	}

	_, err = phase.Rollback(ctx, store, id, "brainstorm", "test", nil)
	if err == nil {
		t.Fatal("expected error for cancelled run rollback")
	}
}

func TestRollback_RolledBackPhases(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	id, err := store.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.UpdatePhase(ctx, id, "brainstorm", "brainstorm-reviewed"); err != nil {
		t.Fatal(err)
	}
	if err := store.UpdatePhase(ctx, id, "brainstorm-reviewed", "strategized"); err != nil {
		t.Fatal(err)
	}
	if err := store.UpdatePhase(ctx, id, "strategized", "planned"); err != nil {
		t.Fatal(err)
	}

	result, err := phase.Rollback(ctx, store, id, "brainstorm", "test", nil)
	if err != nil {
		t.Fatal(err)
	}

	// Should report 3 rolled-back phases: brainstorm-reviewed, strategized, planned
	if len(result.RolledBackPhases) != 3 {
		t.Fatalf("RolledBackPhases = %v, want 3 phases", result.RolledBackPhases)
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -run "TestRollback_" -v`
Expected: FAIL — `Rollback` function doesn't exist.

**Step 3: Implement Rollback function**

Add to `infra/intercore/internal/phase/machine.go`, after the `Advance` function:

```go
// RollbackResult describes what happened during a rollback.
type RollbackResult struct {
	FromPhase        string   // phase before rollback
	ToPhase          string   // target phase (now current)
	RolledBackPhases []string // phases between target and from (inclusive of from)
	Reason           string
}

// Rollback rewinds a run to a prior phase in its chain.
//
// Unlike Advance, rollback:
//   - Goes backward (target must be behind current)
//   - Uses a direct UPDATE (no optimistic concurrency — rollback is authoritative)
//   - Reverts completed runs back to active
//   - Records a rollback event in the audit trail
//   - Returns the list of phases that were rolled back
//
// Rollback does NOT delete events or artifacts — those are marked separately
// by the caller (see runtrack.MarkArtifactsRolledBack).
func Rollback(ctx context.Context, store *Store, runID, targetPhase, reason string, callback PhaseEventCallback) (*RollbackResult, error) {
	run, err := store.Get(ctx, runID)
	if err != nil {
		return nil, err
	}

	// Reject cancelled/failed runs (completed is OK — rollback reverts it)
	if run.Status == StatusCancelled || run.Status == StatusFailed {
		return nil, ErrTerminalRun
	}

	chain := ResolveChain(run)
	fromPhase := run.Phase

	// Compute phases that will be rolled back
	rolledBack := ChainPhasesBetween(chain, targetPhase, fromPhase)
	if rolledBack == nil {
		return nil, ErrInvalidRollback
	}

	// Perform the phase rewind
	if err := store.RollbackPhase(ctx, runID, fromPhase, targetPhase); err != nil {
		return nil, fmt.Errorf("rollback: %w", err)
	}

	// Record rollback event
	if err := store.AddEvent(ctx, &PhaseEvent{
		RunID:     runID,
		FromPhase: fromPhase,
		ToPhase:   targetPhase,
		EventType: EventRollback,
		Reason:    strPtrOrNil(reason),
	}); err != nil {
		return nil, fmt.Errorf("rollback: record event: %w", err)
	}

	// Fire callback
	if callback != nil {
		callback(runID, EventRollback, fromPhase, targetPhase, reason)
	}

	return &RollbackResult{
		FromPhase:        fromPhase,
		ToPhase:          targetPhase,
		RolledBackPhases: rolledBack,
		Reason:           reason,
	}, nil
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -run "TestRollback_" -v`
Expected: PASS

**Step 5: Run full phase test suite**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/phase/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add internal/phase/machine.go internal/phase/machine_test.go
git commit -m "feat(phase): add Rollback machine function with event recording"
```

---

## Task 5: Dispatch and Artifact Marking (F3: iv-vlvn)

**Files:**
- Modify: `infra/intercore/internal/runtrack/store.go` (new methods)
- Modify: `infra/intercore/internal/dispatch/dispatch.go` (new method)
- Test: `infra/intercore/internal/runtrack/store_test.go`
- Test: `infra/intercore/internal/dispatch/dispatch_test.go`

**Step 1: Write the failing test for MarkArtifactsRolledBack**

Add to `infra/intercore/internal/runtrack/store_test.go`:

```go
func TestMarkArtifactsRolledBack(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	// Create a run (need phase store for the FK)
	pStore := phase.New(store.DB())
	runID, err := pStore.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}

	// Add artifacts in two phases
	_, err = store.AddArtifact(ctx, &runtrack.Artifact{RunID: runID, Phase: "brainstorm", Path: "/tmp/a.md", Type: "file"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = store.AddArtifact(ctx, &runtrack.Artifact{RunID: runID, Phase: "strategized", Path: "/tmp/b.md", Type: "file"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = store.AddArtifact(ctx, &runtrack.Artifact{RunID: runID, Phase: "planned", Path: "/tmp/c.md", Type: "file"})
	if err != nil {
		t.Fatal(err)
	}

	// Mark strategized and planned as rolled back
	count, err := store.MarkArtifactsRolledBack(ctx, runID, []string{"strategized", "planned"})
	if err != nil {
		t.Fatal(err)
	}
	if count != 2 {
		t.Fatalf("MarkArtifactsRolledBack count = %d, want 2", count)
	}

	// Verify brainstorm artifact is still active
	arts, err := store.ListArtifacts(ctx, runID, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, a := range arts {
		if a.Phase == "brainstorm" && a.Status != nil && *a.Status != "active" {
			t.Errorf("brainstorm artifact status = %v, want active", *a.Status)
		}
	}
}
```

**Note:** The `Artifact` struct needs a `Status` field. Add `Status *string` to `infra/intercore/internal/runtrack/runtrack.go` after `CreatedAt int64` in the `Artifact` struct. Also update `ListArtifacts` scan to include the new column.

**Step 2: Write the failing test for CancelAgentsByPhases**

Add to `infra/intercore/internal/runtrack/store_test.go`:

```go
func TestCancelAgentsByPhases(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	pStore := phase.New(store.DB())
	runID, err := pStore.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}

	// We can't directly set the phase on agents, so we just add agents and cancel all
	// (the phase filtering is done via dispatch lookup in the real implementation)
	agentID, err := store.AddAgent(ctx, &runtrack.Agent{RunID: runID, AgentType: "claude", Status: "active"})
	if err != nil {
		t.Fatal(err)
	}

	count, err := store.FailAgentsByRun(ctx, runID)
	if err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("FailAgentsByRun count = %d, want 1", count)
	}

	agents, err := store.ListAgents(ctx, runID)
	if err != nil {
		t.Fatal(err)
	}
	for _, a := range agents {
		if a.ID == agentID && a.Status != runtrack.StatusFailed {
			t.Errorf("agent status = %q, want failed", a.Status)
		}
	}
}
```

**Step 3: Run tests to verify they fail**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/runtrack/ -run "TestMarkArtifacts|TestCancelAgents" -v`
Expected: FAIL — methods don't exist.

**Step 4: Add Status field to Artifact struct**

In `infra/intercore/internal/runtrack/runtrack.go`, update the `Artifact` struct:

```go
type Artifact struct {
	ID          string
	RunID       string
	Phase       string
	Path        string
	Type        string
	ContentHash *string
	DispatchID  *string
	Status      *string
	CreatedAt   int64
}
```

**Step 5: Update ListArtifacts scan to include status**

In `infra/intercore/internal/runtrack/store.go`, update `ListArtifacts()` queries and scan to include status:

Change the SELECT queries to:
```sql
SELECT id, run_id, phase, path, type, content_hash, dispatch_id, status, created_at
FROM run_artifacts ...
```

Update the scan to include status:
```go
var (
	contentHash sql.NullString
	dispatchID  sql.NullString
	status      sql.NullString
)
if err := rows.Scan(
	&a.ID, &a.RunID, &a.Phase, &a.Path, &a.Type,
	&contentHash, &dispatchID, &status, &a.CreatedAt,
); err != nil {
```
And after scan: `a.Status = nullStr(status)`

**Step 6: Implement MarkArtifactsRolledBack**

Add to `infra/intercore/internal/runtrack/store.go`, after `ListArtifacts()`:

```go
// MarkArtifactsRolledBack sets status='rolled_back' on all artifacts in the given phases.
// Returns the number of artifacts marked.
func (s *Store) MarkArtifactsRolledBack(ctx context.Context, runID string, phases []string) (int64, error) {
	if len(phases) == 0 {
		return 0, nil
	}

	// Build placeholder list
	placeholders := make([]string, len(phases))
	args := make([]interface{}, 0, len(phases)+1)
	args = append(args, runID)
	for i, p := range phases {
		placeholders[i] = "?"
		args = append(args, p)
	}

	query := fmt.Sprintf(
		"UPDATE run_artifacts SET status = 'rolled_back' WHERE run_id = ? AND phase IN (%s)",
		strings.Join(placeholders, ", "),
	)
	result, err := s.db.ExecContext(ctx, query, args...)
	if err != nil {
		return 0, fmt.Errorf("mark artifacts rolled back: %w", err)
	}
	return result.RowsAffected()
}
```

**Step 7: Implement FailAgentsByRun**

Add to `infra/intercore/internal/runtrack/store.go`:

```go
// FailAgentsByRun sets status='failed' on all active agents for a run.
// Returns the number of agents updated.
func (s *Store) FailAgentsByRun(ctx context.Context, runID string) (int64, error) {
	now := time.Now().Unix()
	result, err := s.db.ExecContext(ctx,
		"UPDATE run_agents SET status = ?, updated_at = ? WHERE run_id = ? AND status = ?",
		StatusFailed, now, runID, StatusActive,
	)
	if err != nil {
		return 0, fmt.Errorf("fail agents by run: %w", err)
	}
	return result.RowsAffected()
}
```

**Step 8: Implement CancelDispatchesByPhases**

Add to `infra/intercore/internal/dispatch/dispatch.go`, after existing methods:

```go
// CancelByRunAndPhases marks dispatches as cancelled for a run in the given phases.
// Dispatches are scoped by run via scope_id = run_id.
// Returns the number of dispatches cancelled.
func (s *Store) CancelByRunAndPhases(ctx context.Context, runID string, phases []string) (int64, error) {
	if len(phases) == 0 {
		return 0, nil
	}

	// Dispatches don't have a phase column — they're linked via run_artifacts.dispatch_id.
	// But dispatches DO have scope_id = run_id. For rollback, we cancel ALL non-terminal
	// dispatches for the run. The phase-level marking is done on artifacts, not dispatches.
	// This is safe because rollback rewinds the entire run to a prior phase.
	now := time.Now().Unix()
	result, err := s.db.ExecContext(ctx, `
		UPDATE dispatches SET status = ?, completed_at = ?
		WHERE scope_id = ? AND status NOT IN ('completed', 'failed', 'cancelled', 'timeout')`,
		StatusCancelled, now, runID,
	)
	if err != nil {
		return 0, fmt.Errorf("cancel dispatches for rollback: %w", err)
	}
	n, err := result.RowsAffected()
	if err != nil {
		return 0, fmt.Errorf("cancel dispatches for rollback: %w", err)
	}

	// Record cancellation events (fire-and-forget via event recorder)
	// We don't have individual dispatch IDs here — the event recorder handles
	// per-dispatch events at the UpdateStatus level. For bulk cancellation,
	// we skip individual event recording to avoid N queries.

	return n, nil
}
```

**Step 9: Run tests**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/runtrack/ -run "TestMarkArtifacts|TestCancelAgents|TestFailAgents" -v`
Expected: PASS

**Step 10: Run full test suite**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./... -v`
Expected: All PASS

**Step 11: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add internal/runtrack/runtrack.go internal/runtrack/store.go internal/runtrack/store_test.go internal/dispatch/dispatch.go
git commit -m "feat(runtrack,dispatch): add artifact marking and dispatch cancellation for rollback"
```

---

## Task 6: CLI — ic run rollback (F2+F3: iv-bld6, iv-vlvn)

**Files:**
- Modify: `infra/intercore/cmd/ic/run.go` (new subcommand dispatch + handler)

**Step 1: Add rollback to subcommand dispatch**

In `infra/intercore/cmd/ic/run.go`, in the `cmdRun` switch statement (around line 29-61), add after the `cancel` case:

```go
	case "rollback":
		return cmdRunRollback(ctx, args[1:])
```

Also update the usage string on line 25 to include `rollback`.

**Step 2: Implement cmdRunRollback**

Add to `infra/intercore/cmd/ic/run.go` (after `cmdRunCancel`, around line 609):

```go
func cmdRunRollback(ctx context.Context, args []string) int {
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "ic: run rollback: usage: ic run rollback <id> --to-phase=<phase> [--reason=<text>] [--dry-run]\n")
		fmt.Fprintf(os.Stderr, "       ic run rollback <id> --layer=code [--phase=<phase>] [--format=json|text]\n")
		return 3
	}

	runID := args[0]
	var toPhase, reason, layer, filterPhase, format string
	dryRun := false

	for i := 1; i < len(args); i++ {
		switch {
		case strings.HasPrefix(args[i], "--to-phase="):
			toPhase = strings.TrimPrefix(args[i], "--to-phase=")
		case strings.HasPrefix(args[i], "--reason="):
			reason = strings.TrimPrefix(args[i], "--reason=")
		case strings.HasPrefix(args[i], "--layer="):
			layer = strings.TrimPrefix(args[i], "--layer=")
		case strings.HasPrefix(args[i], "--phase="):
			filterPhase = strings.TrimPrefix(args[i], "--phase=")
		case strings.HasPrefix(args[i], "--format="):
			format = strings.TrimPrefix(args[i], "--format=")
		case args[i] == "--dry-run":
			dryRun = true
		}
	}

	// Route: --layer=code → code rollback query
	if layer == "code" {
		return cmdRunRollbackCode(ctx, runID, filterPhase, format)
	}

	// Route: --to-phase → workflow rollback
	if toPhase == "" {
		fmt.Fprintf(os.Stderr, "ic: run rollback: --to-phase or --layer required\n")
		return 3
	}

	return cmdRunRollbackWorkflow(ctx, runID, toPhase, reason, dryRun)
}

func cmdRunRollbackWorkflow(ctx context.Context, runID, toPhase, reason string, dryRun bool) int {
	d, err := openDB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback: %v\n", err)
		return 2
	}
	defer d.Close()

	pStore := phase.New(d.SqlDB())
	rtStore := runtrack.New(d.SqlDB())
	dStore := dispatch.New(d.SqlDB(), nil)
	evStore := event.NewStore(d.SqlDB())

	// Get current state for dry-run and validation
	run, err := pStore.Get(ctx, runID)
	if err != nil {
		if err == phase.ErrNotFound {
			fmt.Fprintf(os.Stderr, "ic: run rollback: not found: %s\n", runID)
			return 1
		}
		fmt.Fprintf(os.Stderr, "ic: run rollback: %v\n", err)
		return 2
	}

	chain := phase.ResolveChain(run)
	rolledBackPhases := phase.ChainPhasesBetween(chain, toPhase, run.Phase)
	if rolledBackPhases == nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback: target phase %q is not behind current phase %q\n", toPhase, run.Phase)
		return 1
	}

	if dryRun {
		output := map[string]interface{}{
			"dry_run":            true,
			"from_phase":        run.Phase,
			"to_phase":          toPhase,
			"rolled_back_phases": rolledBackPhases,
		}
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(output)
		return 0
	}

	// Set up event notifier for bus notifications
	notifier := event.NewNotifier()
	notifier.Subscribe("log", event.NewLogHandler(os.Stderr, !flagVerbose))

	callback := func(runID, eventType, fromPhase, toPhase, cbReason string) {
		notifier.Notify(event.Event{
			RunID:   runID,
			Source:  event.SourcePhase,
			Type:    eventType,
			FromState: fromPhase,
			ToState:   toPhase,
			Reason:  cbReason,
		})
	}

	// Perform workflow rollback
	result, err := phase.Rollback(ctx, pStore, runID, toPhase, reason, callback)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback: %v\n", err)
		if err == phase.ErrTerminalRun {
			return 1
		}
		return 2
	}

	// Mark artifacts as rolled back
	markedArtifacts, err := rtStore.MarkArtifactsRolledBack(ctx, runID, result.RolledBackPhases)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback: warning: artifact marking failed: %v\n", err)
	}

	// Cancel active dispatches
	cancelledDispatches, err := dStore.CancelByRunAndPhases(ctx, runID, result.RolledBackPhases)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback: warning: dispatch cancellation failed: %v\n", err)
	}

	// Fail active agents
	failedAgents, err := rtStore.FailAgentsByRun(ctx, runID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback: warning: agent cancellation failed: %v\n", err)
	}

	// Record dispatch cancellation event in event bus
	if cancelledDispatches > 0 {
		evStore.AddDispatchEvent(ctx, "", runID, "", dispatch.StatusCancelled, "rollback", reason)
	}

	// Output JSON
	output := map[string]interface{}{
		"from_phase":            result.FromPhase,
		"to_phase":              result.ToPhase,
		"rolled_back_phases":    result.RolledBackPhases,
		"reason":                result.Reason,
		"cancelled_dispatches":  cancelledDispatches,
		"marked_artifacts":      markedArtifacts,
		"failed_agents":         failedAgents,
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	enc.Encode(output)

	return 0
}
```

**Step 3: Build and test manually**

Run: `cd /root/projects/Interverse/infra/intercore && go build -o ic ./cmd/ic && echo "build OK"`
Expected: Build succeeds.

**Step 4: Run full test suite**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./... -v`
Expected: All PASS

**Step 5: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add cmd/ic/run.go
git commit -m "feat(cli): add ic run rollback --to-phase for workflow state rollback"
```

---

## Task 7: CLI — Code Rollback Query (F4: iv-d5we)

**Files:**
- Modify: `infra/intercore/cmd/ic/run.go` (add cmdRunRollbackCode)
- Modify: `infra/intercore/internal/runtrack/store.go` (new query method)
- Test: `infra/intercore/internal/runtrack/store_test.go`

**Step 1: Write the failing test for artifact code query**

Add to `infra/intercore/internal/runtrack/store_test.go`:

```go
func TestListArtifactsWithDispatches(t *testing.T) {
	store := setupTestStore(t)
	ctx := context.Background()

	pStore := phase.New(store.DB())
	runID, err := pStore.Create(ctx, &phase.Run{ProjectDir: "/tmp/test", Goal: "test"})
	if err != nil {
		t.Fatal(err)
	}

	dispatchID := "dispatch-1"
	_, err = store.AddArtifact(ctx, &runtrack.Artifact{
		RunID:      runID,
		Phase:      "executing",
		Path:       "src/main.go",
		Type:       "file",
		DispatchID: &dispatchID,
	})
	if err != nil {
		t.Fatal(err)
	}

	results, err := store.ListArtifactsForCodeRollback(ctx, runID, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].DispatchID == nil || *results[0].DispatchID != dispatchID {
		t.Error("dispatch ID not returned")
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/runtrack/ -run "TestListArtifactsWithDispatches" -v`
Expected: FAIL — method doesn't exist.

**Step 3: Implement ListArtifactsForCodeRollback**

Add to `infra/intercore/internal/runtrack/store.go`:

```go
// CodeRollbackEntry represents a dispatch-artifact pair for code rollback queries.
type CodeRollbackEntry struct {
	DispatchID   *string `json:"dispatch_id"`
	DispatchName *string `json:"dispatch_name"`
	Phase        string  `json:"phase"`
	Path         string  `json:"path"`
	ContentHash  *string `json:"content_hash"`
	Type         string  `json:"type"`
}

// ListArtifactsForCodeRollback returns artifacts joined with dispatch metadata
// for generating code rollback reports. Optionally filtered by phase.
func (s *Store) ListArtifactsForCodeRollback(ctx context.Context, runID string, phase *string) ([]*CodeRollbackEntry, error) {
	var query string
	var args []interface{}

	if phase != nil {
		query = `
			SELECT a.dispatch_id, d.name, a.phase, a.path, a.content_hash, a.type
			FROM run_artifacts a
			LEFT JOIN dispatches d ON a.dispatch_id = d.id
			WHERE a.run_id = ? AND a.phase = ?
			ORDER BY a.phase, a.created_at ASC`
		args = []interface{}{runID, *phase}
	} else {
		query = `
			SELECT a.dispatch_id, d.name, a.phase, a.path, a.content_hash, a.type
			FROM run_artifacts a
			LEFT JOIN dispatches d ON a.dispatch_id = d.id
			WHERE a.run_id = ?
			ORDER BY a.phase, a.created_at ASC`
		args = []interface{}{runID}
	}

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("code rollback query: %w", err)
	}
	defer rows.Close()

	var entries []*CodeRollbackEntry
	for rows.Next() {
		e := &CodeRollbackEntry{}
		var dispatchID, dispatchName, contentHash sql.NullString
		if err := rows.Scan(&dispatchID, &dispatchName, &e.Phase, &e.Path, &contentHash, &e.Type); err != nil {
			return nil, fmt.Errorf("code rollback scan: %w", err)
		}
		e.DispatchID = nullStr(dispatchID)
		e.DispatchName = nullStr(dispatchName)
		e.ContentHash = nullStr(contentHash)
		entries = append(entries, e)
	}
	return entries, rows.Err()
}
```

**Step 4: Implement cmdRunRollbackCode**

Add to `infra/intercore/cmd/ic/run.go`:

```go
func cmdRunRollbackCode(ctx context.Context, runID, filterPhase, format string) int {
	d, err := openDB()
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback --layer=code: %v\n", err)
		return 2
	}
	defer d.Close()

	pStore := phase.New(d.SqlDB())
	rtStore := runtrack.New(d.SqlDB())

	// Verify run exists
	_, err = pStore.Get(ctx, runID)
	if err != nil {
		if err == phase.ErrNotFound {
			fmt.Fprintf(os.Stderr, "ic: run rollback: not found: %s\n", runID)
			return 1
		}
		fmt.Fprintf(os.Stderr, "ic: run rollback: %v\n", err)
		return 2
	}

	var phaseFilter *string
	if filterPhase != "" {
		phaseFilter = &filterPhase
	}

	entries, err := rtStore.ListArtifactsForCodeRollback(ctx, runID, phaseFilter)
	if err != nil {
		fmt.Fprintf(os.Stderr, "ic: run rollback --layer=code: %v\n", err)
		return 2
	}

	if format == "text" {
		for _, e := range entries {
			dispatchName := "<unknown>"
			if e.DispatchName != nil {
				dispatchName = *e.DispatchName
			}
			hash := "<none>"
			if e.ContentHash != nil {
				hash = (*e.ContentHash)[:12] + "..."
			}
			fmt.Printf("%-20s %-20s %-40s %s\n", e.Phase, dispatchName, e.Path, hash)
		}
		return 0
	}

	// Default JSON output
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	enc.Encode(entries)
	return 0
}
```

**Step 5: Run tests**

Run: `cd /root/projects/Interverse/infra/intercore && go test ./internal/runtrack/ -run "TestListArtifactsWithDispatches" -v`
Expected: PASS

**Step 6: Build**

Run: `cd /root/projects/Interverse/infra/intercore && go build -o ic ./cmd/ic && echo "build OK"`
Expected: Build succeeds.

**Step 7: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add cmd/ic/run.go internal/runtrack/store.go internal/runtrack/store_test.go
git commit -m "feat(cli): add ic run rollback --layer=code for commit metadata query"
```

---

## Task 8: Integration Tests (all features)

**Files:**
- Modify: `infra/intercore/test-integration.sh`

**Step 1: Add rollback integration tests**

Append to `infra/intercore/test-integration.sh`, before the cleanup section:

```bash
# --- Rollback tests ---

echo "=== Rollback: workflow state ==="

# Create a run, advance a few times, then rollback
ROLL_ID=$(./ic run create --project=. --goal="test rollback" | grep -oP '"id":\s*"\K[^"]+')

./ic run advance "$ROLL_ID" --disable-gates >/dev/null  # brainstorm → brainstorm-reviewed
./ic run advance "$ROLL_ID" --disable-gates >/dev/null  # brainstorm-reviewed → strategized
./ic run advance "$ROLL_ID" --disable-gates >/dev/null  # strategized → planned

# Verify current phase
PHASE=$(./ic run phase "$ROLL_ID")
assert_eq "$PHASE" "planned" "phase before rollback"

# Dry-run first
DRY=$(./ic run rollback "$ROLL_ID" --to-phase=brainstorm --dry-run)
echo "$DRY" | jq -e '.dry_run == true' >/dev/null || fail "dry-run should be true"
echo "$DRY" | jq -e '.rolled_back_phases | length == 3' >/dev/null || fail "dry-run should show 3 rolled-back phases"

# Actual rollback
RESULT=$(./ic run rollback "$ROLL_ID" --to-phase=brainstorm --reason="test rollback")
echo "$RESULT" | jq -e '.from_phase == "planned"' >/dev/null || fail "from_phase should be planned"
echo "$RESULT" | jq -e '.to_phase == "brainstorm"' >/dev/null || fail "to_phase should be brainstorm"

# Verify phase is now brainstorm
PHASE=$(./ic run phase "$ROLL_ID")
assert_eq "$PHASE" "brainstorm" "phase after rollback"

# Verify run is still active (not completed)
STATUS=$(./ic run status "$ROLL_ID" --json | jq -r '.status')
assert_eq "$STATUS" "active" "status after rollback"

# Verify rollback event in audit trail
./ic run events "$ROLL_ID" | jq -e 'map(select(.event_type == "rollback")) | length > 0' >/dev/null || fail "rollback event should be in audit trail"

echo "=== Rollback: code query ==="

# Add an artifact then query
./ic run artifact add "$ROLL_ID" --phase=brainstorm --path=/tmp/test-artifact.md
CODE_RESULT=$(./ic run rollback "$ROLL_ID" --layer=code)
echo "$CODE_RESULT" | jq -e 'length > 0' >/dev/null || fail "code rollback should return artifacts"

echo "=== Rollback: completed run ==="

# Create and complete a run
COMP_ID=$(./ic run create --project=. --goal="test completed rollback" | grep -oP '"id":\s*"\K[^"]+')
# Fast-track to done
for i in $(seq 8); do
    ./ic run advance "$COMP_ID" --disable-gates >/dev/null 2>&1 || true
done
STATUS=$(./ic run status "$COMP_ID" --json | jq -r '.status')
assert_eq "$STATUS" "completed" "run should be completed"

# Rollback completed run
RESULT=$(./ic run rollback "$COMP_ID" --to-phase=brainstorm --reason="re-evaluate")
echo "$RESULT" | jq -e '.to_phase == "brainstorm"' >/dev/null || fail "completed run rollback to_phase"

STATUS=$(./ic run status "$COMP_ID" --json | jq -r '.status')
assert_eq "$STATUS" "active" "completed run should be active after rollback"

echo "=== Rollback: cancelled run (should fail) ==="
CANC_ID=$(./ic run create --project=. --goal="test cancelled" | grep -oP '"id":\s*"\K[^"]+')
./ic run cancel "$CANC_ID" >/dev/null
ROLL_RC=0
./ic run rollback "$CANC_ID" --to-phase=brainstorm 2>/dev/null || ROLL_RC=$?
[ "$ROLL_RC" -ne 0 ] || fail "rollback on cancelled run should fail"

echo "All rollback tests passed."
```

**Step 2: Run integration tests**

Run: `cd /root/projects/Interverse/infra/intercore && bash test-integration.sh`
Expected: All tests pass including new rollback tests.

**Step 3: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add test-integration.sh
git commit -m "test: add rollback integration tests"
```

---

## Task 9: Bash Wrapper (F2: iv-bld6)

**Files:**
- Modify: `infra/intercore/lib-intercore.sh`

**Step 1: Add rollback wrapper functions**

In `infra/intercore/lib-intercore.sh`, after the `intercore_run_budget()` function (around line 457), add:

```bash
# --- E6: Rollback wrappers ---

# intercore_run_rollback — Roll back a run to a prior phase.
# Args: $1=run_id, $2=target_phase, $3=reason (optional)
# Prints: JSON with from_phase, to_phase, rolled_back_phases, cancelled_dispatches, marked_artifacts
# Returns: 0=success, 1=failure (not found, invalid target, terminal)
intercore_run_rollback() {
    local run_id="$1" target_phase="$2" reason="${3:-}"
    if ! intercore_available; then return 1; fi
    local args=(run rollback "$run_id" --to-phase="$target_phase")
    [[ -n "$reason" ]] && args+=(--reason="$reason")
    "$INTERCORE_BIN" "${args[@]}" ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}

# intercore_run_rollback_dry — Preview what a rollback would do.
# Args: $1=run_id, $2=target_phase
# Prints: JSON with dry_run=true, from_phase, to_phase, rolled_back_phases
# Returns: 0=success, 1=invalid
intercore_run_rollback_dry() {
    local run_id="$1" target_phase="$2"
    if ! intercore_available; then return 1; fi
    "$INTERCORE_BIN" run rollback "$run_id" --to-phase="$target_phase" --dry-run \
        ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}

# intercore_run_code_rollback — Query dispatch metadata for code rollback.
# Args: $1=run_id, $2=phase (optional, filters to single phase)
# Prints: JSON array of {dispatch_id, dispatch_name, phase, path, content_hash, type}
# Returns: 0=success, 1=failure
intercore_run_code_rollback() {
    local run_id="$1" filter_phase="${2:-}"
    if ! intercore_available; then return 1; fi
    local args=(run rollback "$run_id" --layer=code)
    [[ -n "$filter_phase" ]] && args+=(--phase="$filter_phase")
    "$INTERCORE_BIN" "${args[@]}" ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}
```

**Step 2: Bump wrapper version**

Update the version string at the top of lib-intercore.sh:

```bash
INTERCORE_WRAPPER_VERSION="0.7.0"
```

**Step 3: Commit**

```bash
cd /root/projects/Interverse/infra/intercore
git add lib-intercore.sh
git commit -m "feat(wrapper): add rollback bash wrappers (v0.7.0)"
```

---

## Task 10: Sync Wrapper to Clavain + Update CLAUDE.md

**Files:**
- Modify: `os/clavain/hooks/lib-intercore.sh` (copy from intercore)
- Modify: `infra/intercore/CLAUDE.md` (add rollback quick ref)

**Step 1: Copy updated wrapper to Clavain**

```bash
cp /root/projects/Interverse/infra/intercore/lib-intercore.sh \
   os/clavain/hooks/lib-intercore.sh
```

**Step 2: Update CLAUDE.md with rollback quick reference**

Add to `infra/intercore/CLAUDE.md`, after the "Run Quick Reference" section:

```markdown
## Rollback Quick Reference

```bash
# Workflow rollback — rewind to a prior phase
ic run rollback <id> --to-phase=<phase> --reason="why"
ic run rollback <id> --to-phase=<phase> --dry-run    # Preview only

# Code rollback — query dispatch/artifact metadata
ic run rollback <id> --layer=code                     # All phases
ic run rollback <id> --layer=code --phase=executing   # Single phase
ic run rollback <id> --layer=code --format=text       # Human-readable
```
```

**Step 3: Commit intercore changes**

```bash
cd /root/projects/Interverse/infra/intercore
git add CLAUDE.md
git commit -m "docs: add rollback quick reference to CLAUDE.md"
```

**Step 4: Commit Clavain wrapper sync**

```bash
cd os/clavain
git add hooks/lib-intercore.sh
git commit -m "sync: lib-intercore.sh v0.7.0 (rollback wrappers)"
```

---

## Dependency Graph

```
Task 1 (Schema v8)  ──→  Task 3 (Store methods) ──→  Task 4 (Machine fn) ──→  Task 6 (CLI workflow)
                                                                                     ↓
Task 2 (Constants)  ──→  Task 3                                              Task 8 (Integration)
                                                                                     ↓
                          Task 5 (Dispatch/artifact) ──→ Task 6              Task 9 (Bash wrapper)
                                                                                     ↓
                          Task 7 (Code rollback) ──────→ Task 6              Task 10 (Sync + docs)
```

**Parallelizable groups:**
- Group A: Tasks 1, 2 (independent foundation work)
- Group B: Tasks 3, 5, 7 (store methods — all independent once constants exist)
- Group C: Task 4 (depends on Task 3)
- Group D: Task 6 (depends on Tasks 4, 5, 7)
- Group E: Tasks 8, 9, 10 (sequential, depends on Task 6)
