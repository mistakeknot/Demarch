# Disagreement → Resolution → Routing Signal Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Wire the T/T+1/T+2 loop: interflux detects disagreement, clavain:resolve captures resolution and emits a kernel event, interspect consumes it as evidence for routing overrides.

**Architecture:** Event-driven via intercore kernel. A new `review_events` table (same pattern as `interspect_events`) stores disagreement resolution events. Review events are queried via dedicated `ListReviewEvents` — NOT added to the unified UNION ALL stream (matching the interspect_events precedent). `ic events emit` CLI lets shell scripts emit events. Interspect's cursor consumer picks up events and converts to evidence records.

**Tech Stack:** Go 1.22, modernc.org/sqlite (pure Go, no CGO), bash/jq for shell integrations.

**Review findings incorporated:** fd-architecture and fd-correctness reviews identified 2 P0 and 4 P1 issues in the original plan. All addressed:
- P0: Review events kept out of UNION ALL (follow interspect_events pattern, avoids field loss)
- P0: `schema.sql` updated alongside migration block for fresh installs
- P1: `insertReplayInput` added to `AddReviewEvent` (per PRD requirement)
- P1: Undefined `RESOLVED_FINDINGS`/`DISMISSAL_REASONS` arrays replaced with findings.json iteration
- P1: `sinceInterspect` cursor bug fixed opportunistically
- P1: Emittable source validation tightened (only accept sources with emit routes)

---

### Task 1: Add `ReviewEvent` type and `SourceReview` constant

**Files:**
- Modify: `core/intercore/internal/event/event.go`

**Step 1: Add SourceReview constant and ReviewEvent struct**

Add `SourceReview` to the existing source constants block, and add the `ReviewEvent` struct after `InterspectEvent`:

```go
const (
	SourcePhase        = "phase"
	SourceDispatch     = "dispatch"
	SourceInterspect   = "interspect"
	SourceDiscovery    = "discovery"
	SourceCoordination = "coordination"
	SourceReview       = "review"
)

// ReviewEvent represents a disagreement resolution from flux-drive review.
type ReviewEvent struct {
	ID               int64     `json:"id"`
	RunID            string    `json:"run_id,omitempty"`
	FindingID        string    `json:"finding_id"`
	AgentsJSON       string    `json:"agents_json"`          // JSON map: agent_name → severity
	Resolution       string    `json:"resolution"`           // "accepted", "discarded", "deferred"
	DismissalReason  string    `json:"dismissal_reason,omitempty"` // "agent_wrong", "deprioritized", "already_fixed", "not_applicable"
	ChosenSeverity   string    `json:"chosen_severity"`
	Impact           string    `json:"impact"`               // "decision_changed", "severity_overridden"
	SessionID        string    `json:"session_id,omitempty"`
	ProjectDir       string    `json:"project_dir,omitempty"`
	Timestamp        time.Time `json:"timestamp"`
}
```

**Step 2: Verify existing tests still pass**

Run: `cd core/intercore && go build ./...`
Expected: PASS (no compilation errors)

**Step 3: Commit**

```bash
git add core/intercore/internal/event/event.go
git commit -m "feat(intercore): add ReviewEvent type and SourceReview constant"
```

---

### Task 2: Add `review_events` table via schema migration

**Files:**
- Modify: `core/intercore/internal/db/db.go` (bump `currentSchemaVersion` from 23 to 24, add migration block)
- Modify: `core/intercore/internal/db/schema.sql` (add table DDL for fresh installs — this is the `//go:embed` file that runs on `ic init`)
- Modify: `core/intercore/internal/db/migrations/020_baseline.sql` (add table DDL to Migrator baseline for reference)

**Step 1: Add review_events DDL to `schema.sql`**

Append to `schema.sql` (after `run_replay_inputs` table, at end of file):

```sql
-- v24: review events (disagreement resolution pipeline)
CREATE TABLE IF NOT EXISTS review_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id            TEXT,
    finding_id        TEXT NOT NULL,
    agents_json       TEXT NOT NULL,
    resolution        TEXT NOT NULL,
    dismissal_reason  TEXT,
    chosen_severity   TEXT NOT NULL,
    impact            TEXT NOT NULL,
    session_id        TEXT,
    project_dir       TEXT,
    created_at        INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_review_events_finding ON review_events(finding_id);
CREATE INDEX IF NOT EXISTS idx_review_events_created ON review_events(created_at);
```

**Step 2: Add the same DDL to `020_baseline.sql`**

Append the same DDL block to `020_baseline.sql` (after `interspect_events` table, for reference consistency).

**Step 3: Add migration block in db.go**

In `db.go`, bump `currentSchemaVersion` to 24 and `maxSchemaVersion` to 24. Add the migration block (following the existing pattern for conditional version checks):

```go
// v23 → v24: review events (disagreement resolution pipeline)
if currentVersion >= 20 && currentVersion < 24 {
    v24Stmts := []string{
        `CREATE TABLE IF NOT EXISTS review_events (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id            TEXT,
            finding_id        TEXT NOT NULL,
            agents_json       TEXT NOT NULL,
            resolution        TEXT NOT NULL,
            dismissal_reason  TEXT,
            chosen_severity   TEXT NOT NULL,
            impact            TEXT NOT NULL,
            session_id        TEXT,
            project_dir       TEXT,
            created_at        INTEGER NOT NULL DEFAULT (unixepoch())
        )`,
        `CREATE INDEX IF NOT EXISTS idx_review_events_finding ON review_events(finding_id)`,
        `CREATE INDEX IF NOT EXISTS idx_review_events_created ON review_events(created_at)`,
    }
    for _, stmt := range v24Stmts {
        if _, err := tx.ExecContext(ctx, stmt); err != nil {
            return fmt.Errorf("migrate v23→v24: %w", err)
        }
    }
}
```

Note: The guard `currentVersion >= 20` ensures this only runs on databases that already have the baseline schema (v20+). Fresh installs get the table from `schema.sql` via `CREATE TABLE IF NOT EXISTS`.

**Step 4: Run tests to verify migration**

Run: `cd core/intercore && go test ./internal/db/ -v -run TestMigrate`
Expected: PASS

**Step 5: Commit**

```bash
git add core/intercore/internal/db/db.go core/intercore/internal/db/schema.sql core/intercore/internal/db/migrations/020_baseline.sql
git commit -m "feat(intercore): add review_events table (schema v24)"
```

---

### Task 3: Add `AddReviewEvent`, `ListReviewEvents`, and `MaxReviewEventID` to event store

**Files:**
- Modify: `core/intercore/internal/event/store.go`
- Modify: `core/intercore/internal/event/store_test.go`
- Modify: `core/intercore/internal/event/replay_capture.go` (add `reviewReplayPayload`)

**Step 1: Write the failing test**

Add to `store_test.go`:

```go
func TestAddReviewEvent(t *testing.T) {
	store, _ := setupTestStore(t)
	ctx := context.Background()

	id, err := store.AddReviewEvent(ctx, "run001", "AR-001", `{"fd-architecture":"P1","fd-quality":"P2"}`, "discarded", "agent_wrong", "P2", "decision_changed", "sess-abc", "/tmp/project")
	if err != nil {
		t.Fatalf("AddReviewEvent: %v", err)
	}
	if id < 1 {
		t.Errorf("expected id >= 1, got %d", id)
	}

	events, err := store.ListReviewEvents(ctx, 0, 100)
	if err != nil {
		t.Fatalf("ListReviewEvents: %v", err)
	}
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}

	e := events[0]
	if e.FindingID != "AR-001" {
		t.Errorf("FindingID = %q, want %q", e.FindingID, "AR-001")
	}
	if e.AgentsJSON != `{"fd-architecture":"P1","fd-quality":"P2"}` {
		t.Errorf("AgentsJSON mismatch")
	}
	if e.Resolution != "discarded" {
		t.Errorf("Resolution = %q, want %q", e.Resolution, "discarded")
	}
	if e.DismissalReason != "agent_wrong" {
		t.Errorf("DismissalReason = %q, want %q", e.DismissalReason, "agent_wrong")
	}
	if e.ChosenSeverity != "P2" {
		t.Errorf("ChosenSeverity = %q, want %q", e.ChosenSeverity, "P2")
	}
	if e.Impact != "decision_changed" {
		t.Errorf("Impact = %q, want %q", e.Impact, "decision_changed")
	}
}

func TestAddReviewEvent_OptionalFields(t *testing.T) {
	store, _ := setupTestStore(t)
	ctx := context.Background()

	id, err := store.AddReviewEvent(ctx, "", "AR-002", `{"fd-safety":"P0"}`, "accepted", "", "P0", "severity_overridden", "", "")
	if err != nil {
		t.Fatalf("AddReviewEvent: %v", err)
	}
	if id < 1 {
		t.Errorf("expected id >= 1, got %d", id)
	}

	events, err := store.ListReviewEvents(ctx, 0, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}
	if events[0].RunID != "" {
		t.Errorf("RunID should be empty, got %q", events[0].RunID)
	}
	if events[0].DismissalReason != "" {
		t.Errorf("DismissalReason should be empty, got %q", events[0].DismissalReason)
	}
}

func TestListReviewEvents_SinceCursor(t *testing.T) {
	store, _ := setupTestStore(t)
	ctx := context.Background()

	store.AddReviewEvent(ctx, "", "F-1", `{}`, "accepted", "", "P1", "decision_changed", "", "")
	store.AddReviewEvent(ctx, "", "F-2", `{}`, "discarded", "agent_wrong", "P2", "decision_changed", "", "")
	store.AddReviewEvent(ctx, "", "F-3", `{}`, "accepted", "", "P0", "severity_overridden", "", "")

	all, err := store.ListReviewEvents(ctx, 0, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Fatalf("expected 3, got %d", len(all))
	}

	filtered, err := store.ListReviewEvents(ctx, all[0].ID, 100)
	if err != nil {
		t.Fatal(err)
	}
	if len(filtered) != 2 {
		t.Errorf("expected 2 after cursor, got %d", len(filtered))
	}
}

func TestMaxReviewEventID(t *testing.T) {
	store, _ := setupTestStore(t)
	ctx := context.Background()

	store.AddReviewEvent(ctx, "", "F-1", `{}`, "accepted", "", "P1", "decision_changed", "", "")

	maxID, err := store.MaxReviewEventID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if maxID < 1 {
		t.Errorf("expected maxID >= 1, got %d", maxID)
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd core/intercore && go test ./internal/event/ -v -run TestAddReviewEvent`
Expected: FAIL — `AddReviewEvent` not defined

**Step 3: Add `reviewReplayPayload` to `replay_capture.go`**

```go
func reviewReplayPayload(findingID, agentsJSON, resolution, dismissalReason, chosenSeverity, impact string) string {
	out := map[string]interface{}{
		"finding_id":      findingID,
		"agents_json":     agentsJSON,
		"resolution":      resolution,
		"chosen_severity": chosenSeverity,
		"impact":          impact,
	}
	if dismissalReason != "" {
		out["dismissal_reason"] = dismissalReason
	}
	b, err := json.Marshal(out)
	if err != nil {
		return "{}"
	}
	return string(b)
}
```

**Step 4: Implement `AddReviewEvent`, `ListReviewEvents`, and `MaxReviewEventID`**

Add to `store.go` (follow the `AddInterspectEvent` pattern, but add replay input like dispatch/coordination):

```go
// AddReviewEvent records a disagreement resolution event.
func (s *Store) AddReviewEvent(ctx context.Context, runID, findingID, agentsJSON, resolution, dismissalReason, chosenSeverity, impact, sessionID, projectDir string) (int64, error) {
	result, err := s.db.ExecContext(ctx, `
		INSERT INTO review_events (run_id, finding_id, agents_json, resolution, dismissal_reason, chosen_severity, impact, session_id, project_dir)
		VALUES (NULLIF(?, ''), ?, ?, ?, NULLIF(?, ''), ?, ?, NULLIF(?, ''), NULLIF(?, ''))`,
		runID, findingID, agentsJSON, resolution, dismissalReason, chosenSeverity, impact, sessionID, projectDir,
	)
	if err != nil {
		return 0, fmt.Errorf("add review event: %w", err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		return 0, err
	}

	// Create replay input (consistent with dispatch/coordination pattern, per PRD F1)
	if runID != "" {
		payload := reviewReplayPayload(findingID, agentsJSON, resolution, dismissalReason, chosenSeverity, impact)
		_ = insertReplayInput(ctx, s.db.ExecContext, runID, "review_event", findingID, payload, "", SourceReview, &id)
	}

	return id, nil
}

// ListReviewEvents returns review events since a cursor position.
func (s *Store) ListReviewEvents(ctx context.Context, since int64, limit int) ([]ReviewEvent, error) {
	if limit <= 0 {
		limit = 1000
	}

	rows, err := s.db.QueryContext(ctx, `
		SELECT id, COALESCE(run_id, '') AS run_id, finding_id, agents_json, resolution,
			COALESCE(dismissal_reason, '') AS dismissal_reason, chosen_severity, impact,
			COALESCE(session_id, '') AS session_id,
			COALESCE(project_dir, '') AS project_dir,
			created_at
		FROM review_events
		WHERE id > ?
		ORDER BY created_at ASC, id ASC
		LIMIT ?`,
		since, limit,
	)
	if err != nil {
		return nil, fmt.Errorf("list review events: %w", err)
	}
	defer rows.Close()

	var events []ReviewEvent
	for rows.Next() {
		var e ReviewEvent
		var ts int64
		if err := rows.Scan(&e.ID, &e.RunID, &e.FindingID, &e.AgentsJSON, &e.Resolution,
			&e.DismissalReason, &e.ChosenSeverity, &e.Impact,
			&e.SessionID, &e.ProjectDir, &ts); err != nil {
			return nil, fmt.Errorf("scan review event: %w", err)
		}
		e.Timestamp = time.Unix(ts, 0)
		events = append(events, e)
	}
	return events, rows.Err()
}

// MaxReviewEventID returns the highest review_events.id (for cursor init).
func (s *Store) MaxReviewEventID(ctx context.Context) (int64, error) {
	var id sql.NullInt64
	err := s.db.QueryRowContext(ctx, "SELECT MAX(id) FROM review_events").Scan(&id)
	if err != nil {
		return 0, err
	}
	if !id.Valid {
		return 0, nil
	}
	return id.Int64, nil
}
```

**Step 5: Run tests to verify they pass**

Run: `cd core/intercore && go test ./internal/event/ -v -run "TestAddReviewEvent|TestListReviewEvents|TestMaxReviewEventID"`
Expected: PASS

**Step 6: Commit**

```bash
git add core/intercore/internal/event/store.go core/intercore/internal/event/store_test.go core/intercore/internal/event/replay_capture.go
git commit -m "feat(intercore): add AddReviewEvent, ListReviewEvents, MaxReviewEventID with replay input"
```

---

### Task 4: Update cursor tracking for review events + fix interspect cursor bug

**Files:**
- Modify: `core/intercore/cmd/ic/events.go` (add `sinceReview` cursor field, `--since-review` flag, fix `sinceInterspect` advancement)

**Important:** Review events are NOT added to the UNION ALL queries (`ListEvents`/`ListAllEvents`). They follow the same pattern as `interspect_events` — consumed via dedicated `ListReviewEvents` query. The cursor still needs to track the review high-water mark for consumers that use named cursors.

**Step 1: Add `--since-review` flag to `cmdEventsTail`**

In the flag parsing loop, add after `--since-discovery=`:

```go
case strings.HasPrefix(args[i], "--since-review="):
    val := strings.TrimPrefix(args[i], "--since-review=")
    n, err := strconv.ParseInt(val, 10, 64)
    if err != nil {
        slog.Error("events tail: invalid --since-review", "value", val)
        return 3
    }
    sinceReview = n
```

Declare `sinceReview int64` alongside the other cursor variables (line 37).

**Step 2: Update `loadCursor` to return review field**

Change the return type and cursor struct:

```go
func loadCursor(ctx context.Context, store *state.Store, consumer, scope string) (phase, dispatch, interspect, discovery, review int64) {
    key := consumer
    if scope != "" {
        key = consumer + ":" + scope
    }
    payload, err := store.Get(ctx, "cursor", key)
    if err != nil {
        return 0, 0, 0, 0, 0
    }

    var cursor struct {
        Phase      int64 `json:"phase"`
        Dispatch   int64 `json:"dispatch"`
        Interspect int64 `json:"interspect"`
        Discovery  int64 `json:"discovery"`
        Review     int64 `json:"review"`
    }
    if err := json.Unmarshal(payload, &cursor); err != nil {
        return 0, 0, 0, 0, 0
    }
    return cursor.Phase, cursor.Dispatch, cursor.Interspect, cursor.Discovery, cursor.Review
}
```

Note: Old cursor JSON without "review" field will unmarshal to `review=0`, which is the correct default (replay from beginning).

**Step 3: Update `saveCursor` to include review field**

```go
func saveCursor(ctx context.Context, store *state.Store, consumer, scope string, phaseID, dispatchID, interspectID, discoveryID, reviewID int64) {
    key := consumer
    if scope != "" {
        key = consumer + ":" + scope
    }
    payload := fmt.Sprintf(`{"phase":%d,"dispatch":%d,"interspect":%d,"discovery":%d,"review":%d}`, phaseID, dispatchID, interspectID, discoveryID, reviewID)
    ttl := cursorTTL(ctx, store, key)
    if err := store.Set(ctx, "cursor", key, json.RawMessage(payload), ttl); err != nil {
        slog.Debug("event: saveCursor", "cursor", key, "error", err)
    }
}
```

**Step 4: Update caller in `cmdEventsTail`**

Update the `loadCursor` call (line 117) to receive the review cursor:
```go
sincePhase, sinceDispatch, sinceInterspect, sinceDiscovery, sinceReview = loadCursor(ctx, stStore, consumer, runID)
```

Update the `saveCursor` call (line 157) to pass review:
```go
saveCursor(ctx, stStore, consumer, runID, sincePhase, sinceDispatch, sinceInterspect, sinceDiscovery, sinceReview)
```

**Step 5: Update `cmdEventsCursorRegister` default payload**

Change the default payload (line 280):
```go
payload := `{"phase":0,"dispatch":0,"interspect":0,"discovery":0,"review":0}`
```

**Step 6: Build and verify**

Run: `cd core/intercore && go build ./cmd/ic`
Expected: PASS

Run: `cd core/intercore && go test ./... -count=1`
Expected: PASS

**Step 7: Commit**

```bash
git add core/intercore/cmd/ic/events.go
git commit -m "feat(intercore): add review cursor field + update cursor tracking"
```

---

### Task 5: Add `ic events emit` CLI subcommand

**Files:**
- Modify: `core/intercore/cmd/ic/events.go`

**Step 1: Add `emit` case to `cmdEvents` switch**

```go
func cmdEvents(ctx context.Context, args []string) int {
	if len(args) == 0 {
		slog.Error("events: missing subcommand", "expected", "tail, cursor, emit")
		return 3
	}

	switch args[0] {
	case "tail":
		return cmdEventsTail(ctx, args[1:])
	case "cursor":
		return cmdEventsCursor(ctx, args[1:])
	case "emit":
		return cmdEventsEmit(ctx, args[1:])
	default:
		slog.Error("events: unknown subcommand", "subcommand", args[0])
		return 3
	}
}
```

**Step 2: Implement `cmdEventsEmit`**

```go
func cmdEventsEmit(ctx context.Context, args []string) int {
	var source, eventType, contextJSON, runID, sessionID, projectDir string

	for i := 0; i < len(args); i++ {
		switch {
		case strings.HasPrefix(args[i], "--source="):
			source = strings.TrimPrefix(args[i], "--source=")
		case strings.HasPrefix(args[i], "--type="):
			eventType = strings.TrimPrefix(args[i], "--type=")
		case strings.HasPrefix(args[i], "--context="):
			contextJSON = strings.TrimPrefix(args[i], "--context=")
		case strings.HasPrefix(args[i], "--run="):
			runID = strings.TrimPrefix(args[i], "--run=")
		case strings.HasPrefix(args[i], "--session="):
			sessionID = strings.TrimPrefix(args[i], "--session=")
		case strings.HasPrefix(args[i], "--project="):
			projectDir = strings.TrimPrefix(args[i], "--project=")
		default:
			slog.Error("events emit: unknown flag", "value", args[i])
			return 3
		}
	}

	if source == "" {
		slog.Error("events emit: --source is required")
		return 3
	}
	if eventType == "" {
		slog.Error("events emit: --type is required")
		return 3
	}

	// Validate context JSON if provided
	if contextJSON != "" {
		if !json.Valid([]byte(contextJSON)) {
			slog.Error("events emit: --context must be valid JSON")
			return 3
		}
	}

	// Default session/project from env
	if sessionID == "" {
		sessionID = os.Getenv("CLAUDE_SESSION_ID")
	}
	if projectDir == "" {
		projectDir, _ = os.Getwd()
	}

	d, err := openDB()
	if err != nil {
		slog.Error("events emit failed", "error", err)
		return 2
	}
	defer d.Close()

	evStore := event.NewStore(d.SqlDB())

	// Route to the appropriate store method based on source.
	// Only sources with emit support are accepted — validates both
	// that the source is known AND that it has an emit handler.
	switch source {
	case event.SourceReview:
		var payload struct {
			FindingID       string            `json:"finding_id"`
			Agents          map[string]string `json:"agents"`
			Resolution      string            `json:"resolution"`
			DismissalReason string            `json:"dismissal_reason"`
			ChosenSeverity  string            `json:"chosen_severity"`
			Impact          string            `json:"impact"`
		}
		if err := json.Unmarshal([]byte(contextJSON), &payload); err != nil {
			slog.Error("events emit: failed to parse review context", "error", err)
			return 3
		}
		if payload.FindingID == "" || payload.Resolution == "" || payload.ChosenSeverity == "" || payload.Impact == "" {
			slog.Error("events emit: review context requires finding_id, resolution, chosen_severity, impact")
			return 3
		}
		agentsJSON, _ := json.Marshal(payload.Agents)
		id, err := evStore.AddReviewEvent(ctx, runID, payload.FindingID, string(agentsJSON), payload.Resolution, payload.DismissalReason, payload.ChosenSeverity, payload.Impact, sessionID, projectDir)
		if err != nil {
			slog.Error("events emit failed", "error", err)
			return 2
		}
		fmt.Printf("%d\n", id)

	case event.SourceInterspect:
		var payload struct {
			AgentName      string `json:"agent_name"`
			OverrideReason string `json:"override_reason"`
		}
		if contextJSON != "" {
			json.Unmarshal([]byte(contextJSON), &payload)
		}
		if payload.AgentName == "" {
			slog.Error("events emit: interspect context requires agent_name")
			return 3
		}
		id, err := evStore.AddInterspectEvent(ctx, runID, payload.AgentName, eventType, payload.OverrideReason, contextJSON, sessionID, projectDir)
		if err != nil {
			slog.Error("events emit failed", "error", err)
			return 2
		}
		fmt.Printf("%d\n", id)

	default:
		slog.Error("events emit: source not supported for emit", "source", source, "emittable", "review, interspect")
		return 3
	}

	return 0
}
```

Note: The validation switch only accepts sources with emit handlers (`review`, `interspect`). This avoids the confusing UX where `--source=phase` passes a "known source" check but then fails at routing.

**Step 3: Build and run smoke test**

Run: `cd core/intercore && go build -o ic ./cmd/ic`
Expected: PASS

Run: `cd core/intercore && ./ic events emit --source=review --type=disagreement_resolved --context='{"finding_id":"AR-001","agents":{"fd-architecture":"P1","fd-quality":"P2"},"resolution":"discarded","dismissal_reason":"agent_wrong","chosen_severity":"P2","impact":"decision_changed"}'`
Expected: Prints an event ID (integer)

**Step 4: Commit**

```bash
git add core/intercore/cmd/ic/events.go
git commit -m "feat(intercore): add ic events emit CLI subcommand"
```

---

### Task 6: Add integration test for emit → tail roundtrip

**Files:**
- Modify: `core/intercore/test-integration.sh` (add test case)

**Step 1: Find integration test file**

Run: `head -20 core/intercore/test-integration.sh`
Understand the test structure and conventions.

**Step 2: Add roundtrip test**

Add a new test case following the existing pattern. Since review events are NOT in the UNION ALL, the test verifies emit returns monotonically increasing IDs and validates error handling:

```bash
# Test: events emit roundtrip
echo "=== Test: events emit roundtrip ==="
EVENT_ID=$(./ic events emit --source=review --type=disagreement_resolved \
    --context='{"finding_id":"IT-001","agents":{"fd-arch":"P1","fd-quality":"P2"},"resolution":"discarded","dismissal_reason":"agent_wrong","chosen_severity":"P2","impact":"decision_changed"}' \
    --session=test-sess --project=/tmp/test)

if [ -z "$EVENT_ID" ]; then
    echo "FAIL: emit returned no event ID"
    exit 1
fi

# Second emit should get higher ID
EVENT_ID2=$(./ic events emit --source=review --type=disagreement_resolved \
    --context='{"finding_id":"IT-002","agents":{"fd-safety":"P0"},"resolution":"accepted","chosen_severity":"P0","impact":"severity_overridden"}' \
    --session=test-sess --project=/tmp/test)

if [ "$EVENT_ID2" -le "$EVENT_ID" ]; then
    echo "FAIL: second event ID ($EVENT_ID2) not greater than first ($EVENT_ID)"
    exit 1
fi
echo "PASS: events emit roundtrip (IDs: $EVENT_ID, $EVENT_ID2)"

# Test: emit with invalid JSON should fail
if ./ic events emit --source=review --type=test --context='not-json' 2>/dev/null; then
    echo "FAIL: emit accepted invalid JSON"
    exit 1
fi
echo "PASS: emit rejects invalid JSON"

# Test: emit with unsupported source should fail
if ./ic events emit --source=phase --type=test --context='{}' 2>/dev/null; then
    echo "FAIL: emit accepted unsupported source"
    exit 1
fi
echo "PASS: emit rejects unsupported source"
```

**Step 3: Run integration test**

Run: `cd core/intercore && bash test-integration.sh`
Expected: PASS

**Step 4: Commit**

```bash
git add core/intercore/test-integration.sh
git commit -m "test(intercore): add events emit roundtrip integration test"
```

---

### Task 7: Extend clavain:resolve to emit disagreement events

**Files:**
- Modify: `os/clavain/commands/resolve.md`

**Step 1: Add Step 5b after existing Step 5 (trust feedback)**

After the existing trust feedback block (Step 5, ends around line 100), add a new step. This step iterates `findings.json` directly (same pattern as Step 5) instead of relying on undefined tracking arrays:

````markdown
### 5b. Emit Disagreement Events

After recording trust feedback, check each resolved finding for `severity_conflict`. When the resolution changes a decision, emit a kernel event.

**Impact gate:** Only emit when:
- The finding had `severity_conflict` (agents disagreed on severity)
- AND either: (a) the finding was discarded despite having P0 or P1 severity from at least one agent, or (b) the finding was accepted with a severity different from the majority rating

```bash
if [[ -f "$FINDINGS_JSON" ]] && command -v ic &>/dev/null; then
    SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

    # Process each finding that has severity_conflict
    # Uses the same findings.json iteration as Step 5 (trust feedback)
    jq -c '.findings[] | select(.severity_conflict != null)' "$FINDINGS_JSON" 2>/dev/null | while IFS= read -r finding; do
        [[ -z "$finding" ]] && continue

        FINDING_ID=$(echo "$finding" | jq -r '.id // empty')
        SEVERITY=$(echo "$finding" | jq -r '.severity // empty')
        AGENTS_MAP=$(echo "$finding" | jq -c '.severity_conflict // {}')

        # Determine outcome: check if finding was addressed in the resolve session
        # Same logic as Step 5 — the .resolution field is set during Step 3
        OUTCOME=$(echo "$finding" | jq -r '.resolution // empty')
        [[ -z "$OUTCOME" ]] && continue

        # Check if any agent rated this P0 or P1
        HAS_HIGH_SEVERITY=$(echo "$AGENTS_MAP" | jq 'to_entries | map(select(.value == "P0" or .value == "P1")) | length > 0')

        # Impact gate
        IMPACT=""
        DISMISSAL_REASON=""
        if [[ "$OUTCOME" == "discarded" && "$HAS_HIGH_SEVERITY" == "true" ]]; then
            IMPACT="decision_changed"
            DISMISSAL_REASON=$(echo "$finding" | jq -r '.dismissal_reason // "agent_wrong"')
        elif [[ "$OUTCOME" == "accepted" ]]; then
            SEVERITY_MISMATCH=$(echo "$AGENTS_MAP" | jq --arg sev "$SEVERITY" 'to_entries | map(select(.value != $sev)) | length > 0')
            if [[ "$SEVERITY_MISMATCH" == "true" ]]; then
                IMPACT="severity_overridden"
            fi
        fi

        # Only emit if impact gate passed
        if [[ -n "$IMPACT" ]]; then
            CONTEXT=$(jq -n \
                --arg finding_id "$FINDING_ID" \
                --argjson agents "$AGENTS_MAP" \
                --arg resolution "$OUTCOME" \
                --arg dismissal_reason "$DISMISSAL_REASON" \
                --arg chosen_severity "$SEVERITY" \
                --arg impact "$IMPACT" \
                '{finding_id:$finding_id,agents:$agents,resolution:$resolution,dismissal_reason:$dismissal_reason,chosen_severity:$chosen_severity,impact:$impact}')

            ic events emit \
                --source=review \
                --type=disagreement_resolved \
                --session="$SESSION_ID" \
                --project="$PROJECT_ROOT" \
                --context="$CONTEXT" 2>/dev/null || true
        fi
    done
fi
```

**Silent fail-open:** The `2>/dev/null || true` ensures resolve never fails due to event emission. Same pattern as trust feedback.
````

**Step 2: Verify the resolve command still parses correctly**

```bash
head -5 os/clavain/commands/resolve.md  # Should show frontmatter
```

**Step 3: Commit**

```bash
git add os/clavain/commands/resolve.md
git commit -m "feat(clavain): emit disagreement_resolved events in resolve Step 5b"
```

---

### Task 8: Add `_interspect_process_disagreement_event` to interspect

**Files:**
- Modify: `interverse/interspect/hooks/lib-interspect.sh`

**Important:** The consumer queries review events directly via `ListReviewEvents` — NOT through the UNION ALL stream. This ensures all review event fields (`chosen_severity`, `impact`, `dismissal_reason`) are preserved with full fidelity.

**Step 1: Add `_interspect_process_disagreement_event`**

Add after `_interspect_consume_kernel_events` (around line 2057):

```bash
# Process a disagreement_resolved event from the kernel review_events table.
# Converts event payload to evidence records for each overridden agent.
# Args: $1=event_json (full ReviewEvent JSON from ListReviewEvents — all fields preserved)
_interspect_process_disagreement_event() {
    local event_json="$1"

    local finding_id resolution chosen_severity impact agents_json dismissal_reason session_id
    finding_id=$(echo "$event_json" | jq -r '.finding_id // empty') || return 0
    resolution=$(echo "$event_json" | jq -r '.resolution // empty') || return 0
    chosen_severity=$(echo "$event_json" | jq -r '.chosen_severity // empty') || return 0
    impact=$(echo "$event_json" | jq -r '.impact // empty') || return 0
    agents_json=$(echo "$event_json" | jq -r '.agents_json // "{}"') || return 0
    dismissal_reason=$(echo "$event_json" | jq -r '.dismissal_reason // empty') || return 0
    session_id=$(echo "$event_json" | jq -r '.session_id // "unknown"') || return 0

    [[ -z "$finding_id" || -z "$resolution" || -z "$chosen_severity" ]] && return 0

    # Map dismissal_reason to override_reason for evidence
    local override_reason=""
    case "$dismissal_reason" in
        agent_wrong)        override_reason="agent_wrong" ;;
        deprioritized)      override_reason="deprioritized" ;;
        already_fixed)      override_reason="stale_finding" ;;
        not_applicable)     override_reason="agent_wrong" ;;
        "")
            if [[ "$resolution" == "accepted" && "$impact" == "severity_overridden" ]]; then
                override_reason="severity_miscalibrated"
            fi
            ;;
    esac

    # For each agent whose severity differs from chosen, insert evidence
    local agent_entries
    agent_entries=$(echo "$agents_json" | jq -c 'to_entries[]' 2>/dev/null) || return 0

    while IFS= read -r entry; do
        [[ -z "$entry" ]] && continue
        local agent_name agent_severity
        agent_name=$(echo "$entry" | jq -r '.key')
        agent_severity=$(echo "$entry" | jq -r '.value')

        # Only create evidence for agents whose severity was overridden
        [[ "$agent_severity" == "$chosen_severity" ]] && continue

        local context
        context=$(jq -n \
            --arg finding_id "$finding_id" \
            --arg agent_severity "$agent_severity" \
            --arg chosen_severity "$chosen_severity" \
            --arg resolution "$resolution" \
            --arg impact "$impact" \
            --arg dismissal_reason "$dismissal_reason" \
            '{finding_id:$finding_id,agent_severity:$agent_severity,chosen_severity:$chosen_severity,resolution:$resolution,impact:$impact,dismissal_reason:$dismissal_reason}')

        _interspect_insert_evidence \
            "$session_id" "$agent_name" "disagreement_override" \
            "$override_reason" "$context" "interspect-disagreement" \
            2>/dev/null || true
    done <<< "$agent_entries"
}
```

**Step 2: Add `_interspect_consume_review_events` consumer function**

This polls review events via their dedicated query path (not the UNION ALL), using `ic state` for cursor persistence:

```bash
# Consume review events from kernel and convert to interspect evidence.
# Uses ic state for cursor persistence (separate from the event cursor system,
# since review events are not in the UNION ALL stream).
_interspect_consume_review_events() {
    command -v ic &>/dev/null || return 0

    local cursor_key="interspect-disagreement-review-cursor"
    local since_review
    since_review=$(ic state get "$cursor_key" "" 2>/dev/null) || since_review="0"
    [[ -z "$since_review" ]] && since_review="0"

    # Query review events directly via Go store (JSON, one per line)
    # This uses ListReviewEvents which returns full ReviewEvent with all fields
    local events_output
    events_output=$(ic events review --since="$since_review" --limit=100 2>/dev/null) || return 0

    [[ -z "$events_output" ]] && return 0

    local max_id="$since_review"
    while IFS= read -r event_line; do
        [[ -z "$event_line" ]] && continue

        _interspect_process_disagreement_event "$event_line" || true

        local event_id
        event_id=$(echo "$event_line" | jq -r '.id // 0') || continue
        if [[ "$event_id" -gt "$max_id" ]]; then
            max_id="$event_id"
        fi
    done <<< "$events_output"

    # Persist cursor
    if [[ "$max_id" != "$since_review" ]]; then
        ic state set "$cursor_key" "$max_id" "" 2>/dev/null || true
    fi
}
```

**Step 3: Wire into `_interspect_consume_kernel_events`**

At the end of `_interspect_consume_kernel_events`, add:

```bash
    # Poll review events via separate query (not in UNION ALL)
    _interspect_consume_review_events || true
```

**Step 4: Add `ic events review` subcommand to events.go**

This is a thin wrapper around `ListReviewEvents`. Add to `cmdEvents` switch:

```go
case "review":
    return cmdEventsReview(ctx, args[1:])
```

Implement:

```go
func cmdEventsReview(ctx context.Context, args []string) int {
    var since int64
    limit := 100

    for i := 0; i < len(args); i++ {
        switch {
        case strings.HasPrefix(args[i], "--since="):
            val := strings.TrimPrefix(args[i], "--since=")
            n, err := strconv.ParseInt(val, 10, 64)
            if err != nil {
                slog.Error("events review: invalid --since", "value", val)
                return 3
            }
            since = n
        case strings.HasPrefix(args[i], "--limit="):
            val := strings.TrimPrefix(args[i], "--limit=")
            n, err := strconv.Atoi(val)
            if err != nil {
                slog.Error("events review: invalid --limit", "value", val)
                return 3
            }
            limit = n
        default:
            slog.Error("events review: unknown flag", "value", args[i])
            return 3
        }
    }

    d, err := openDB()
    if err != nil {
        slog.Error("events review failed", "error", err)
        return 2
    }
    defer d.Close()

    evStore := event.NewStore(d.SqlDB())
    events, err := evStore.ListReviewEvents(ctx, since, limit)
    if err != nil {
        slog.Error("events review failed", "error", err)
        return 2
    }

    enc := json.NewEncoder(os.Stdout)
    for _, e := range events {
        if err := enc.Encode(e); err != nil {
            slog.Error("events review: write failed", "error", err)
            return 2
        }
    }
    return 0
}
```

**Step 5: Verify bash syntax**

Run: `bash -n interverse/interspect/hooks/lib-interspect.sh`
Expected: No output (valid syntax)

**Step 6: Build and verify**

Run: `cd core/intercore && go build ./cmd/ic`
Expected: PASS

**Step 7: Commit**

```bash
git add interverse/interspect/hooks/lib-interspect.sh core/intercore/cmd/ic/events.go
git commit -m "feat(interspect): add disagreement event consumer + evidence insertion"
```

---

### Task 9: Run full test suite and verify end-to-end

**Files:** None new (verification only)

**Step 1: Run intercore unit tests**

Run: `cd core/intercore && go test ./... -count=1`
Expected: All PASS

**Step 2: Run intercore integration tests**

Run: `cd core/intercore && bash test-integration.sh`
Expected: All PASS (including new emit roundtrip test)

**Step 3: Verify bash syntax for all modified shell files**

Run: `bash -n interverse/interspect/hooks/lib-interspect.sh && echo "OK"`
Expected: OK

**Step 4: Build final ic binary**

Run: `cd core/intercore && go build -o ic ./cmd/ic && echo "Build OK"`
Expected: Build OK

**Step 5: Commit (if any fixes needed)**

Only commit if fixes were needed during verification. Otherwise, no commit needed.
