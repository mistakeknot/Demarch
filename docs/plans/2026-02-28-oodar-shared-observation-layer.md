# OODAR Shared Observation Layer — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Build `ic situation snapshot` — a unified observation command that aggregates phase state, dispatch state, events, scheduler queue, and budget into a single JSON response, enabling every OODAR loop to observe the system in one call instead of five.

**Architecture:** New `internal/observation` package following the `internal/budget` multi-store aggregation pattern. A `Collector` struct holds interface references to phase, dispatch, event, and scheduler stores, and produces a `Snapshot` struct. CLI command `ic situation snapshot` wires it up. No new DB tables — read-only aggregation of existing data.

**Tech Stack:** Go 1.22, modernc.org/sqlite, standard library `testing`

**Source docs:**
- Brainstorm: `docs/brainstorms/2026-02-28-oodar-loops-brainstorm.md`
- Synthesis: `docs/research/oodar-flux-drive-synthesis.md`
- Intercore CLAUDE.md: `core/intercore/CLAUDE.md`

---

### Task 1: Create the Observation Package — Types and Interfaces

**Files:**
- Create: `core/intercore/internal/observation/observation.go`
- Test: `core/intercore/internal/observation/observation_test.go`

**Step 1: Write the failing test**

```go
// core/intercore/internal/observation/observation_test.go
package observation

import (
	"context"
	"testing"
	"time"
)

func TestCollectReturnsSnapshot(t *testing.T) {
	ctx := context.Background()
	c := NewCollector(nil, nil, nil, nil)
	snap, err := c.Collect(ctx, CollectOptions{})
	if err != nil {
		t.Fatalf("Collect: %v", err)
	}
	if snap == nil {
		t.Fatal("expected non-nil snapshot")
	}
	if snap.Timestamp.IsZero() {
		t.Error("expected non-zero timestamp")
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd core/intercore && go test ./internal/observation/ -run TestCollectReturnsSnapshot -v`
Expected: FAIL — package does not exist

**Step 3: Write the types and Collector stub**

```go
// core/intercore/internal/observation/observation.go
package observation

import (
	"context"
	"time"

	"github.com/mistakeknot/intercore/internal/dispatch"
	"github.com/mistakeknot/intercore/internal/event"
	"github.com/mistakeknot/intercore/internal/phase"
)

// Snapshot is the unified observation of system state at a point in time.
type Snapshot struct {
	Timestamp  time.Time          `json:"timestamp"`
	Runs       []RunSummary       `json:"runs"`
	Dispatches DispatchSummary    `json:"dispatches"`
	Events     []event.Event      `json:"recent_events"`
	Queue      QueueSummary       `json:"queue"`
	Budget     *BudgetSummary     `json:"budget,omitempty"`
}

// RunSummary is a compact view of a run's phase state.
type RunSummary struct {
	ID         string  `json:"id"`
	Phase      string  `json:"phase"`
	Status     string  `json:"status"`
	ProjectDir string  `json:"project_dir"`
	Goal       string  `json:"goal"`
	CreatedAt  int64   `json:"created_at"`
}

// DispatchSummary aggregates active dispatch state.
type DispatchSummary struct {
	Active    int                 `json:"active"`
	Total     int                 `json:"total"`
	Agents    []AgentSummary      `json:"agents"`
}

// AgentSummary is a compact view of an active agent.
type AgentSummary struct {
	ID         string  `json:"id"`
	AgentType  string  `json:"agent_type"`
	Status     string  `json:"status"`
	Turns      int     `json:"turns"`
	InputTok   int     `json:"input_tokens"`
	OutputTok  int     `json:"output_tokens"`
	ScopeID    string  `json:"scope_id,omitempty"`
}

// QueueSummary shows scheduler state.
type QueueSummary struct {
	Pending   int `json:"pending"`
	Running   int `json:"running"`
	Retrying  int `json:"retrying"`
}

// BudgetSummary shows token budget state for a run.
type BudgetSummary struct {
	RunID     string `json:"run_id"`
	Budget    int64  `json:"budget"`
	Used      int64  `json:"used"`
	Remaining int64  `json:"remaining"`
}

// CollectOptions controls what the Collector gathers.
type CollectOptions struct {
	RunID      string // scope to a specific run (empty = all active)
	EventLimit int    // max recent events (default 20)
}

// PhaseQuerier is the subset of phase.Store needed by the Collector.
type PhaseQuerier interface {
	Get(ctx context.Context, id string) (*phase.Run, error)
	ListActive(ctx context.Context) ([]*phase.Run, error)
}

// DispatchQuerier is the subset of dispatch.Store needed by the Collector.
type DispatchQuerier interface {
	ListActive(ctx context.Context) ([]*dispatch.Dispatch, error)
	AggregateTokens(ctx context.Context, scopeID string) (*dispatch.TokenAggregation, error)
}

// EventQuerier is the subset of event.Store needed by the Collector.
type EventQuerier interface {
	ListAllEvents(ctx context.Context, sincePhaseID, sinceDispatchID, sinceDiscoveryID int64, limit int) ([]event.Event, error)
	ListEvents(ctx context.Context, runID string, sincePhaseID, sinceDispatchID, sinceDiscoveryID int64, limit int) ([]event.Event, error)
}

// SchedulerQuerier is the subset of scheduler.Store needed by the Collector.
type SchedulerQuerier interface {
	CountByStatus(ctx context.Context) (map[string]int, error)
}

// Collector aggregates data from multiple stores into a Snapshot.
type Collector struct {
	phases     PhaseQuerier
	dispatches DispatchQuerier
	events     EventQuerier
	scheduler  SchedulerQuerier
}

// NewCollector creates a Collector. Any store may be nil (that section is skipped).
func NewCollector(p PhaseQuerier, d DispatchQuerier, e EventQuerier, s SchedulerQuerier) *Collector {
	return &Collector{
		phases:     p,
		dispatches: d,
		events:     e,
		scheduler:  s,
	}
}

// Collect gathers a unified snapshot of system state.
func (c *Collector) Collect(ctx context.Context, opts CollectOptions) (*Snapshot, error) {
	if opts.EventLimit == 0 {
		opts.EventLimit = 20
	}

	snap := &Snapshot{
		Timestamp: time.Now().UTC(),
	}

	// Phase state
	if c.phases != nil {
		if opts.RunID != "" {
			run, err := c.phases.Get(ctx, opts.RunID)
			if err != nil {
				return nil, err
			}
			if run != nil {
				snap.Runs = []RunSummary{runToSummary(run)}
			}
		} else {
			runs, err := c.phases.ListActive(ctx)
			if err != nil {
				return nil, err
			}
			snap.Runs = make([]RunSummary, len(runs))
			for i, r := range runs {
				snap.Runs[i] = runToSummary(r)
			}
		}
	}

	// Dispatch state
	if c.dispatches != nil {
		active, err := c.dispatches.ListActive(ctx)
		if err != nil {
			return nil, err
		}
		agents := make([]AgentSummary, len(active))
		for i, d := range active {
			agents[i] = dispatchToSummary(d)
		}
		snap.Dispatches = DispatchSummary{
			Active: len(active),
			Agents: agents,
		}
	}

	// Recent events
	if c.events != nil {
		var evts []event.Event
		var err error
		if opts.RunID != "" {
			evts, err = c.events.ListEvents(ctx, opts.RunID, 0, 0, 0, opts.EventLimit)
		} else {
			evts, err = c.events.ListAllEvents(ctx, 0, 0, 0, opts.EventLimit)
		}
		if err != nil {
			return nil, err
		}
		snap.Events = evts
	}

	// Scheduler queue
	if c.scheduler != nil {
		counts, err := c.scheduler.CountByStatus(ctx)
		if err != nil {
			return nil, err
		}
		snap.Queue = QueueSummary{
			Pending:  counts["pending"],
			Running:  counts["running"],
			Retrying: counts["retrying"],
		}
	}

	// Budget (only if scoped to a run)
	if opts.RunID != "" && c.phases != nil && c.dispatches != nil {
		run, _ := c.phases.Get(ctx, opts.RunID)
		if run != nil && run.TokenBudget != nil && *run.TokenBudget > 0 {
			agg, err := c.dispatches.AggregateTokens(ctx, opts.RunID)
			if err != nil {
				return nil, err
			}
			used := agg.TotalIn + agg.TotalOut
			snap.Budget = &BudgetSummary{
				RunID:     opts.RunID,
				Budget:    *run.TokenBudget,
				Used:      used,
				Remaining: *run.TokenBudget - used,
			}
		}
	}

	return snap, nil
}

func runToSummary(r *phase.Run) RunSummary {
	return RunSummary{
		ID:         r.ID,
		Phase:      r.Phase,
		Status:     r.Status,
		ProjectDir: r.ProjectDir,
		Goal:       r.Goal,
		CreatedAt:  r.CreatedAt,
	}
}

func dispatchToSummary(d *dispatch.Dispatch) AgentSummary {
	s := AgentSummary{
		ID:        d.ID,
		AgentType: d.AgentType,
		Status:    d.Status,
		Turns:     d.Turns,
		InputTok:  d.InputTokens,
		OutputTok: d.OutputTokens,
	}
	if d.ScopeID != nil {
		s.ScopeID = *d.ScopeID
	}
	return s
}
```

**Step 4: Run test to verify it passes**

Run: `cd core/intercore && go test ./internal/observation/ -run TestCollectReturnsSnapshot -v`
Expected: PASS

**Step 5: Commit**

```bash
cd core/intercore
git add internal/observation/observation.go internal/observation/observation_test.go
git commit -m "feat(intercore): add observation package with Collector and Snapshot types

OODAR shared observation layer — types, interfaces, and Collect()
aggregator following the budget.Checker multi-store pattern."
```

---

### Task 2: Add SchedulerStore.CountByStatus Method

The scheduler store needs a new method to count jobs by status for the queue summary. The existing `List` method returns full job objects which is wasteful for counts.

**Files:**
- Modify: `core/intercore/internal/scheduler/store.go`
- Test: `core/intercore/internal/scheduler/store_test.go` (create if needed)

**Step 1: Write the failing test**

```go
// Append to existing test file or create new
func TestCountByStatus(t *testing.T) {
	store := testStore(t) // use existing helper pattern
	ctx := context.Background()

	counts, err := store.CountByStatus(ctx)
	if err != nil {
		t.Fatalf("CountByStatus: %v", err)
	}
	if counts == nil {
		t.Fatal("expected non-nil map")
	}
	// Empty DB should return zero counts
	if counts["pending"] != 0 {
		t.Errorf("expected 0 pending, got %d", counts["pending"])
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd core/intercore && go test ./internal/scheduler/ -run TestCountByStatus -v`
Expected: FAIL — `CountByStatus` method not found

**Step 3: Add CountByStatus to store.go**

```go
// CountByStatus returns a map of status -> count for all jobs.
func (s *Store) CountByStatus(ctx context.Context) (map[string]int, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT status, COUNT(*) FROM scheduler_jobs GROUP BY status`)
	if err != nil {
		return nil, fmt.Errorf("count by status: %w", err)
	}
	defer rows.Close()

	counts := make(map[string]int)
	for rows.Next() {
		var status string
		var count int
		if err := rows.Scan(&status, &count); err != nil {
			return nil, fmt.Errorf("count by status scan: %w", err)
		}
		counts[status] = count
	}
	return counts, rows.Err()
}
```

**Step 4: Run test to verify it passes**

Run: `cd core/intercore && go test ./internal/scheduler/ -run TestCountByStatus -v`
Expected: PASS

**Step 5: Commit**

```bash
cd core/intercore
git add internal/scheduler/store.go internal/scheduler/store_test.go
git commit -m "feat(intercore): add SchedulerStore.CountByStatus for observation layer"
```

---

### Task 3: Integration Test — Collector With Real SQLite

Test the Collector against a real database with seed data, verifying the full aggregation pipeline.

**Files:**
- Modify: `core/intercore/internal/observation/observation_test.go`

**Step 1: Write the integration test**

```go
func testCollector(t *testing.T) (*Collector, *db.DB) {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "test.db")
	d, err := db.Open(path, 100*time.Millisecond)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { d.Close() })
	if err := d.Migrate(context.Background()); err != nil {
		t.Fatalf("Migrate: %v", err)
	}

	pStore := phase.New(d.SqlDB())
	dStore := dispatch.New(d.SqlDB(), nil)
	eStore := event.NewStore(d.SqlDB())
	sStore := scheduler.NewStore(d.SqlDB())

	return NewCollector(pStore, dStore, eStore, sStore), d
}

func TestCollectIntegration(t *testing.T) {
	c, d := testCollector(t)
	ctx := context.Background()

	// Seed a run
	pStore := phase.New(d.SqlDB())
	_, err := pStore.Create(ctx, &phase.CreateParams{
		ProjectDir: "/tmp/test-project",
		Goal:       "test run",
	})
	if err != nil {
		t.Fatalf("Create run: %v", err)
	}

	snap, err := c.Collect(ctx, CollectOptions{})
	if err != nil {
		t.Fatalf("Collect: %v", err)
	}

	if len(snap.Runs) != 1 {
		t.Errorf("expected 1 run, got %d", len(snap.Runs))
	}
	if snap.Runs[0].Phase != phase.PhaseBrainstorm {
		t.Errorf("expected phase %s, got %s", phase.PhaseBrainstorm, snap.Runs[0].Phase)
	}
	if snap.Runs[0].Goal != "test run" {
		t.Errorf("expected goal 'test run', got %q", snap.Runs[0].Goal)
	}
}

func TestCollectWithRunScope(t *testing.T) {
	c, d := testCollector(t)
	ctx := context.Background()

	pStore := phase.New(d.SqlDB())
	run, _ := pStore.Create(ctx, &phase.CreateParams{
		ProjectDir: "/tmp/test-project",
		Goal:       "scoped test",
	})

	snap, err := c.Collect(ctx, CollectOptions{RunID: run.ID})
	if err != nil {
		t.Fatalf("Collect: %v", err)
	}

	if len(snap.Runs) != 1 {
		t.Errorf("expected 1 run, got %d", len(snap.Runs))
	}
	if snap.Runs[0].ID != run.ID {
		t.Errorf("expected run %s, got %s", run.ID, snap.Runs[0].ID)
	}
}

func TestCollectNilStoresGraceful(t *testing.T) {
	c := NewCollector(nil, nil, nil, nil)
	ctx := context.Background()

	snap, err := c.Collect(ctx, CollectOptions{})
	if err != nil {
		t.Fatalf("Collect with nil stores: %v", err)
	}
	if snap == nil {
		t.Fatal("expected non-nil snapshot even with nil stores")
	}
	if len(snap.Runs) != 0 {
		t.Errorf("expected 0 runs, got %d", len(snap.Runs))
	}
}
```

**Step 2: Run tests**

Run: `cd core/intercore && go test ./internal/observation/ -v`
Expected: PASS — all 4 tests (unit + 3 integration)

**Step 3: Commit**

```bash
cd core/intercore
git add internal/observation/observation_test.go
git commit -m "test(intercore): integration tests for observation Collector"
```

---

### Task 4: CLI Command — `ic situation snapshot`

**Files:**
- Create: `core/intercore/cmd/ic/situation.go`
- Modify: `core/intercore/cmd/ic/main.go:134` (add switch case)

**Step 1: Create the CLI command**

```go
// core/intercore/cmd/ic/situation.go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"

	"github.com/mistakeknot/intercore/internal/dispatch"
	"github.com/mistakeknot/intercore/internal/event"
	"github.com/mistakeknot/intercore/internal/observation"
	"github.com/mistakeknot/intercore/internal/phase"
	"github.com/mistakeknot/intercore/internal/scheduler"
)

func cmdSituation(ctx context.Context, args []string) int {
	if len(args) == 0 {
		slog.Error("situation: missing subcommand", "expected", "snapshot")
		return 3
	}
	switch args[0] {
	case "snapshot":
		return cmdSituationSnapshot(ctx, args[1:])
	default:
		slog.Error("situation: unknown subcommand", "subcommand", args[0])
		return 3
	}
}

func cmdSituationSnapshot(ctx context.Context, args []string) int {
	var runID string
	var eventLimit int = 20

	for i := 0; i < len(args); i++ {
		arg := args[i]
		switch {
		case strings.HasPrefix(arg, "--run="):
			runID = strings.TrimPrefix(arg, "--run=")
		case arg == "--run" && i+1 < len(args):
			i++
			runID = args[i]
		case strings.HasPrefix(arg, "--events="):
			n, err := strconv.Atoi(strings.TrimPrefix(arg, "--events="))
			if err != nil {
				slog.Error("situation snapshot: invalid --events", "value", args[i])
				return 3
			}
			eventLimit = n
		default:
			// First positional arg is runID for convenience
			if runID == "" {
				runID = arg
			}
		}
	}

	d, err := openDB()
	if err != nil {
		slog.Error("situation snapshot: open db", "error", err)
		return 2
	}
	defer d.Close()

	pStore := phase.New(d.SqlDB())
	dStore := dispatch.New(d.SqlDB(), nil)
	eStore := event.NewStore(d.SqlDB())
	sStore := scheduler.NewStore(d.SqlDB())

	collector := observation.NewCollector(pStore, dStore, eStore, sStore)

	snap, err := collector.Collect(ctx, observation.CollectOptions{
		RunID:      runID,
		EventLimit: eventLimit,
	})
	if err != nil {
		slog.Error("situation snapshot", "error", err)
		return 2
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(snap); err != nil {
		slog.Error("situation snapshot: encode", "error", err)
		return 2
	}
	return 0
}
```

**Step 2: Register in main.go**

Add the following case to the switch block in `main.go` at line 134, before `default:`:

```go
	case "situation":
		exitCode = cmdSituation(ctx, subArgs)
```

**Step 3: Build and verify**

Run: `cd core/intercore && go build -o ic ./cmd/ic && ./ic situation snapshot`
Expected: JSON output with empty/default values (no active runs in test DB)

**Step 4: Run all tests to check nothing broke**

Run: `cd core/intercore && go test ./... -count=1`
Expected: All PASS

**Step 5: Commit**

```bash
cd core/intercore
git add cmd/ic/situation.go cmd/ic/main.go
git commit -m "feat(intercore): add 'ic situation snapshot' CLI command

Unified observation layer for OODAR loops — aggregates phase state,
dispatch state, events, scheduler queue, and budget into single JSON."
```

---

### Task 5: Integration Test — CLI End-to-End

Verify the full CLI command works with the integration test harness.

**Files:**
- Modify: `core/intercore/test-integration.sh` (add situation snapshot test case)

**Step 1: Add test case to integration script**

Append after existing test cases in `test-integration.sh`:

```bash
# --- situation snapshot ---
echo "=== situation snapshot (empty) ==="
$IC situation snapshot --json 2>/dev/null
assert_exit 0

echo "=== situation snapshot (with run) ==="
RUN_ID=$($IC run create --project="$TMPDIR/test-proj" --goal="integration test" 2>/dev/null | grep -oP 'id=\K[^ ]+')
SNAP=$($IC situation snapshot --run="$RUN_ID" 2>/dev/null)
echo "$SNAP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d['runs'])==1, f'expected 1 run, got {len(d[\"runs\"])}'; print('  situation snapshot: OK')"
assert_exit 0
```

**Step 2: Run integration tests**

Run: `cd core/intercore && bash test-integration.sh`
Expected: All tests PASS including new situation snapshot cases

**Step 3: Commit**

```bash
cd core/intercore
git add test-integration.sh
git commit -m "test(intercore): integration test for ic situation snapshot"
```

---

### Task 6: Add printUsage Entry and AGENTS.md Documentation

**Files:**
- Modify: `core/intercore/cmd/ic/main.go` (printUsage function)
- Modify: `core/intercore/AGENTS.md` (CLI reference section)

**Step 1: Add situation to printUsage**

Find the `printUsage()` function in main.go and add the `situation` command to the command list in alphabetical position.

**Step 2: Add to AGENTS.md CLI reference**

Add under the CLI commands section:

```markdown
### `ic situation`

Unified observation layer for OODAR loops.

- `ic situation snapshot` — JSON snapshot of all active runs, dispatches, events, queue depth
- `ic situation snapshot --run=<id>` — scoped to a specific run (includes budget)
- `ic situation snapshot --events=50` — control event history depth (default: 20)
```

**Step 3: Commit**

```bash
cd core/intercore
git add cmd/ic/main.go AGENTS.md
git commit -m "docs(intercore): add ic situation to usage and AGENTS.md"
```

---

### Task 7: Update PHILOSOPHY.md with OODAR Vocabulary

Label the existing flywheel as OODAR to establish shared vocabulary across the project.

**Files:**
- Modify: `PHILOSOPHY.md` (root)

**Step 1: Add OODAR section**

After the "The Core Bet" section (line ~27), add:

```markdown
### The OODAR Lens

The flywheel (authority → actions → evidence → authority) is an instance of **OODAR** — Observe, Orient, Decide, Act, Reflect — operating at nested timescales:

- **Per-turn:** Agent observes tool results, orients on context, decides next action, acts, and reflects via signal scoring.
- **Per-sprint:** Phase gates observe artifacts, orient on sprint state, decide phase transitions, advance phases, and reflect at sprint end.
- **Cross-session:** Interspect observes evidence, orients via pattern classification, decides routing proposals, acts via override application, and reflects via canary monitoring.

OODAR extends Boyd's OODA loop with an explicit **Reflect** phase because AI agents don't implicitly learn from experience — learning must be captured as durable evidence that earns authority.

Situation assessments are prompt aids, not ground truth. Always verify recent evidence against cached assessments.
```

**Step 2: Commit**

```bash
git add PHILOSOPHY.md
git commit -m "docs: add OODAR vocabulary to PHILOSOPHY.md

Labels the existing flywheel as OODAR operating at nested timescales.
Establishes shared vocabulary for observation layer work."
```

---

## Task Dependency Graph

```
Task 1 (types + interfaces) ──┐
                               ├──→ Task 3 (integration tests) ──→ Task 4 (CLI) ──→ Task 5 (CLI e2e)
Task 2 (CountByStatus) ───────┘                                                  ↘
                                                                                   Task 6 (docs)
Task 7 (PHILOSOPHY.md) ── independent, can run in parallel with anything
```

## Success Criteria

1. `ic situation snapshot` returns valid JSON in <50ms on a DB with 10 active runs and 50 dispatches
2. All existing tests continue to pass (`go test ./...`)
3. Integration test validates round-trip: create run → snapshot → verify run appears
4. Nil stores degrade gracefully (no panics, empty sections)
5. Budget summary only appears when `--run` is specified and budget is set
