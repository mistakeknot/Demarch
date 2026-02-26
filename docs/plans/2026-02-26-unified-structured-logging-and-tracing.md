# Unified Structured Logging and Tracing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Replace ad-hoc fprintf/echo logging across L1 Kernel, L2 OS, and L3 Plugins with structured JSON logging (`log/slog` + bash helpers) and lightweight trace propagation (`IC_TRACE_ID`/`IC_SPAN_ID` env vars).

**Architecture:** Bottom-up rollout — L1 Intercore foundation first (observability package + slog migration + trace schema), then L2 Clavain bash helpers and hook wiring, then L3 plugin adoption guide. Environment variables propagate trace context across process boundaries; no OpenTelemetry SDK.

**Tech Stack:** Go `log/slog` (stdlib), bash JSON log helpers, SQLite migration v23, `crypto/rand` for span generation, `/dev/urandom` for bash span generation.

---

## Task 1: Observability Package — Foundation

**Bead:** iv-2dvdf
**Files:**
- Create: `internal/observability/observability.go`
- Create: `internal/observability/observability_test.go`

**Step 1: Write the test file**

```go
// internal/observability/observability_test.go
package observability

import (
	"bytes"
	"encoding/json"
	"log/slog"
	"os"
	"testing"
)

func TestTraceFromEnv_AllSet(t *testing.T) {
	t.Setenv("IC_TRACE_ID", "abcdef1234567890abcdef1234567890")
	t.Setenv("IC_SPAN_ID", "1234567890abcdef")
	t.Setenv("IC_PARENT_SPAN_ID", "fedcba0987654321")

	tc := TraceFromEnv()
	if tc.TraceID != "abcdef1234567890abcdef1234567890" {
		t.Errorf("TraceID = %q, want abcdef...", tc.TraceID)
	}
	if tc.SpanID != "1234567890abcdef" {
		t.Errorf("SpanID = %q, want 1234...", tc.SpanID)
	}
	if tc.ParentSpanID != "fedcba0987654321" {
		t.Errorf("ParentSpanID = %q, want fedcba...", tc.ParentSpanID)
	}
}

func TestTraceFromEnv_Empty(t *testing.T) {
	os.Unsetenv("IC_TRACE_ID")
	os.Unsetenv("IC_SPAN_ID")
	os.Unsetenv("IC_PARENT_SPAN_ID")

	tc := TraceFromEnv()
	if tc.TraceID != "" {
		t.Errorf("TraceID = %q, want empty", tc.TraceID)
	}
}

func TestGenerateTraceID(t *testing.T) {
	id := GenerateTraceID()
	if len(id) != 32 {
		t.Errorf("TraceID length = %d, want 32", len(id))
	}
	// Verify hex
	for _, c := range id {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			t.Errorf("TraceID contains non-hex char: %c", c)
		}
	}
}

func TestGenerateSpanID(t *testing.T) {
	id := GenerateSpanID()
	if len(id) != 16 {
		t.Errorf("SpanID length = %d, want 16", len(id))
	}
}

func TestNewHandler_InjectsTraceContext(t *testing.T) {
	t.Setenv("IC_TRACE_ID", "aaaa1111bbbb2222cccc3333dddd4444")
	t.Setenv("IC_SPAN_ID", "eeee5555ffff6666")

	var buf bytes.Buffer
	logger := slog.New(NewHandler(&buf, slog.LevelDebug))
	logger.Info("test message", "key", "value")

	var record map[string]any
	if err := json.Unmarshal(buf.Bytes(), &record); err != nil {
		t.Fatalf("unmarshal log: %v", err)
	}
	if record["trace_id"] != "aaaa1111bbbb2222cccc3333dddd4444" {
		t.Errorf("trace_id = %v, want aaaa...", record["trace_id"])
	}
	if record["span_id"] != "eeee5555ffff6666" {
		t.Errorf("span_id = %v, want eeee...", record["span_id"])
	}
	if record["key"] != "value" {
		t.Errorf("key = %v, want value", record["key"])
	}
}

func TestNewHandler_NoTraceContext(t *testing.T) {
	os.Unsetenv("IC_TRACE_ID")
	os.Unsetenv("IC_SPAN_ID")

	var buf bytes.Buffer
	logger := slog.New(NewHandler(&buf, slog.LevelDebug))
	logger.Info("test")

	var record map[string]any
	if err := json.Unmarshal(buf.Bytes(), &record); err != nil {
		t.Fatalf("unmarshal log: %v", err)
	}
	// trace_id should not be present when env var is unset
	if _, ok := record["trace_id"]; ok {
		t.Error("trace_id present when IC_TRACE_ID not set")
	}
}

func TestNewHandler_LevelFiltering(t *testing.T) {
	var buf bytes.Buffer
	logger := slog.New(NewHandler(&buf, slog.LevelWarn))
	logger.Info("should be filtered")
	if buf.Len() > 0 {
		t.Error("Info message should be filtered at Warn level")
	}
	logger.Warn("should appear")
	if buf.Len() == 0 {
		t.Error("Warn message should appear at Warn level")
	}
}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./internal/observability/`
Expected: FAIL — package does not exist

**Step 3: Write the implementation**

```go
// internal/observability/observability.go
package observability

import (
	"crypto/rand"
	"encoding/hex"
	"io"
	"log/slog"
	"os"
)

// TraceContext holds distributed trace identifiers propagated via environment.
type TraceContext struct {
	TraceID      string
	SpanID       string
	ParentSpanID string
}

// TraceFromEnv reads trace context from IC_TRACE_ID, IC_SPAN_ID, IC_PARENT_SPAN_ID.
func TraceFromEnv() TraceContext {
	return TraceContext{
		TraceID:      os.Getenv("IC_TRACE_ID"),
		SpanID:       os.Getenv("IC_SPAN_ID"),
		ParentSpanID: os.Getenv("IC_PARENT_SPAN_ID"),
	}
}

// GenerateTraceID returns a 32-char lowercase hex string (128-bit, OTel-compatible).
func GenerateTraceID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		panic("crypto/rand failed: " + err.Error())
	}
	return hex.EncodeToString(b)
}

// GenerateSpanID returns a 16-char lowercase hex string (64-bit, OTel-compatible).
func GenerateSpanID() string {
	b := make([]byte, 8)
	if _, err := rand.Read(b); err != nil {
		panic("crypto/rand failed: " + err.Error())
	}
	return hex.EncodeToString(b)
}

// ParseLevel maps a string to slog.Level. Returns slog.LevelWarn for unrecognized values.
func ParseLevel(s string) slog.Level {
	switch s {
	case "debug":
		return slog.LevelDebug
	case "info":
		return slog.LevelInfo
	case "warn", "warning":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelWarn
	}
}

// NewHandler returns a slog.JSONHandler that auto-injects trace context from env.
// Trace attributes are only added when IC_TRACE_ID is set.
func NewHandler(w io.Writer, level slog.Level) slog.Handler {
	opts := &slog.HandlerOptions{Level: level}
	base := slog.NewJSONHandler(w, opts)

	tc := TraceFromEnv()
	if tc.TraceID == "" {
		return base
	}

	attrs := []slog.Attr{
		slog.String("trace_id", tc.TraceID),
	}
	if tc.SpanID != "" {
		attrs = append(attrs, slog.String("span_id", tc.SpanID))
	}
	if tc.ParentSpanID != "" {
		attrs = append(attrs, slog.String("parent_span_id", tc.ParentSpanID))
	}

	// WithAttrs returns a new handler that prepends these attrs to every record
	return base.WithAttrs(attrs)
}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./internal/observability/`
Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add internal/observability/
git commit -m "feat(observability): add slog handler factory and trace context extraction"
```

---

## Task 2: slog Initialization in ic CLI

**Bead:** iv-g6gj4 (partial — this is the wiring task, Task 3 does the bulk migration)
**Files:**
- Modify: `cmd/ic/main.go` (flag parsing at lines 21-61, init at ~line 72)

**Step 1: Add slog import and level flag**

In `cmd/ic/main.go`, add to the var block (after line 25):
```go
var (
	flagDB      string
	flagTimeout time.Duration
	flagVerbose bool
	flagJSON    bool
	flagVV      bool // double-verbose for debug level
)
```

In the flag parsing loop (after the `--verbose` case at line 50), add:
```go
case arg == "-vv":
	flagVerbose = true
	flagVV = true
```

After the flag parsing loop ends (before `ctx := context.Background()`), add slog init:
```go
// Initialize structured logging
logLevel := slog.LevelWarn
if envLevel := os.Getenv("IC_LOG_LEVEL"); envLevel != "" {
	logLevel = observability.ParseLevel(envLevel)
} else if flagVV {
	logLevel = slog.LevelDebug
} else if flagVerbose {
	logLevel = slog.LevelInfo
}
slog.SetDefault(slog.New(observability.NewHandler(os.Stderr, logLevel)))
```

Add the import: `"github.com/mistakeknot/intercore/internal/observability"`

**Step 2: Build to verify compilation**

Run: `cd /home/mk/projects/Demarch/core/intercore && go build ./cmd/ic/`
Expected: Compiles without error

**Step 3: Run existing tests to verify no regression**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./cmd/ic/ ./internal/...`
Expected: All pass

**Step 4: Commit**

```bash
git add cmd/ic/main.go
git commit -m "feat(ic): initialize slog with observability handler and level flags"
```

---

## Task 3: Migrate Event Handlers to slog

**Bead:** iv-g6gj4 (continued)
**Files:**
- Modify: `internal/event/handler_log.go` (29 lines — full rewrite)
- Modify: `internal/event/handler_hook.go` (73 lines — replace logw with logger)
- Modify: `internal/event/handler_spawn.go` (57 lines — replace logw with logger)
- Modify: `internal/portfolio/relay.go` (lines 28-59 — struct field + constructor)
- Modify: `internal/sentinel/sentinel.go` (line 74 — single fprintf)
- Modify: `cmd/ic/run.go` (lines 452, 464, 536, 1038-1039 — update handler construction)

**Step 1: Migrate handler_log.go**

Replace the entire file content with:
```go
package event

import (
	"context"
	"log/slog"
)

// NewLogHandler returns a handler that logs structured event lines.
// If logger is nil, logging is suppressed (equivalent to the old quiet=true).
func NewLogHandler(logger *slog.Logger) Handler {
	return func(ctx context.Context, e Event) error {
		if logger == nil {
			return nil
		}
		attrs := []slog.Attr{
			slog.String("source", e.Source),
			slog.String("type", e.Type),
			slog.String("run_id", e.RunID),
			slog.String("from", e.FromState),
			slog.String("to", e.ToState),
		}
		if e.Reason != "" {
			attrs = append(attrs, slog.String("reason", e.Reason))
		}
		logger.LogAttrs(ctx, slog.LevelInfo, "event", attrs...)
		return nil
	}
}
```

**Step 2: Migrate handler_hook.go**

Replace the `logw io.Writer` parameter with `logger *slog.Logger`:
```go
func NewHookHandler(projectDir string, logger *slog.Logger) Handler {
```

Remove the `if logw == nil { logw = os.Stderr }` block. Replace the `fmt.Fprintf(logw, ...)` at line 65 with:
```go
if logger != nil {
	logger.WarnContext(hookCtx, "hook failed",
		"hook", hookName,
		"error", err.Error(),
		"stderr", stderr.String(),
	)
}
```

Remove unused imports: `"fmt"`, `"io"`.

**Step 3: Migrate handler_spawn.go**

Replace the `logw io.Writer` parameter with `logger *slog.Logger`:
```go
func NewSpawnHandler(querier AgentQuerier, spawner AgentSpawner, logger *slog.Logger) Handler {
```

Remove the `if logw == nil { logw = os.Stderr }` block. Replace the two `fmt.Fprintf(logw, ...)` calls with:
```go
// Line ~49 (failure):
if logger != nil {
	logger.WarnContext(ctx, "auto-spawn failed", "agent_id", id, "error", err)
}

// Line ~52 (success):
if logger != nil {
	logger.InfoContext(ctx, "auto-spawn started", "agent_id", id)
}
```

**Step 4: Migrate relay.go struct field**

In `internal/portfolio/relay.go`, change the struct field (line 36):
```go
logger *slog.Logger  // was: logw io.Writer
```

Update constructor `NewRelay` (line 52):
```go
logger: slog.Default(),  // was: logw: os.Stderr
```

Rename `SetLogWriter` to `SetLogger`:
```go
func (r *Relay) SetLogger(l *slog.Logger) {
	r.logger = l
}
```

Replace all 6 `fmt.Fprintf(r.logw, ...)` calls with slog equivalents:
- Line 76: `r.logger.Warn("relay poll error", "error", err)`
- Line 125: `r.logger.Warn("relay skip project", "project", child.ProjectDir, "error", err)`
- Line 134: `r.logger.Warn("relay query events failed", "project", child.ProjectDir, "error", err)`
- Line 143: `r.logger.Warn("relay events failed", "project", child.ProjectDir, "error", err)`
- Line 158: `r.logger.Warn("relay write dispatch count", "error", err)`
- Line 188: `r.logger.Info("relay event", "project", projectDir, "type", eventType, "from", evt.FromPhase, "to", evt.ToPhase)`

**Step 5: Migrate sentinel.go**

Add `logger *slog.Logger` field to `Store` struct and constructor. Replace line 74:
```go
slog.WarnContext(ctx, "sentinel auto-prune failed", "error", err)
```

**Step 6: Update call sites in cmd/ic/run.go**

Line 452 — update `NewLogHandler`:
```go
// Old: notifier.Subscribe("log", event.NewLogHandler(os.Stderr, !flagVerbose))
var eventLogger *slog.Logger
if flagVerbose {
	eventLogger = slog.Default()
}
notifier.Subscribe("log", event.NewLogHandler(eventLogger))
```

Line 464 — update `NewHookHandler`:
```go
// Old: notifier.Subscribe("hook", event.NewHookHandler(run.ProjectDir, os.Stderr))
notifier.Subscribe("hook", event.NewHookHandler(run.ProjectDir, slog.Default()))
```

Line 536 — update `NewSpawnHandler`:
```go
// Old: notifier.Subscribe("spawn", event.NewSpawnHandler(rtStore, spawner, os.Stderr))
notifier.Subscribe("spawn", event.NewSpawnHandler(rtStore, spawner, slog.Default()))
```

Lines 1038-1039 — same pattern for rollback path.

Also update `cmd/ic/portfolio.go` lines 228-238 to use `slog.Info`/`slog.Error`.

**Step 7: Build and test**

Run: `cd /home/mk/projects/Demarch/core/intercore && go build ./cmd/ic/ && go test -race ./internal/event/ ./internal/portfolio/ ./internal/sentinel/ ./cmd/ic/`
Expected: All pass

**Step 8: Commit**

```bash
git add internal/event/ internal/portfolio/ internal/sentinel/ cmd/ic/run.go cmd/ic/portfolio.go
git commit -m "refactor(event): migrate handlers from io.Writer to slog.Logger"
```

---

## Task 4: Migrate cmd/ic Subcommands to slog

**Bead:** iv-g6gj4 (continued)
**Files:**
- Modify: All 17 `cmd/ic/*.go` files

**Migration pattern for all files:**

The ~576 `fmt.Fprintf(os.Stderr, "ic: <cmd>: %v\n", err)` calls fall into 3 categories:

1. **Error exits** — `fmt.Fprintf(os.Stderr, "ic: cost: %v\n", err); os.Exit(1)` → `slog.Error("<cmd> failed", "error", err); os.Exit(1)`
2. **Status/info messages** — `fmt.Fprintf(os.Stderr, "[event] ...\n", ...)` → `slog.Info(...)` or `slog.Debug(...)`
3. **Usage/help text** — `fmt.Fprintf(os.Stderr, "Usage: ic ...\n")` → keep as `fmt.Fprintf(os.Stderr, ...)` (usage text is not logging)

**Step 1: Migrate files in priority order**

Process each file. For each `fmt.Fprintf(os.Stderr, "ic: ...)`:
- Error pattern → `slog.Error("description", "error", err)`
- Status/bracket pattern → `slog.Info("description", key, val, ...)`
- Usage strings → leave unchanged

Files to migrate (descending by call count):
1. `run.go` (152 calls) — largest, most important
2. `main.go` (57 calls) — CLI entry, some pre-slog init calls must stay as fprintf
3. `discovery.go` (54 calls)
4. `lane.go` (47 calls)
5. `dispatch.go` (47 calls)
6. `portfolio.go` (30 calls)
7. `scheduler_cmd.go` (29 calls)
8. `agency.go` (27 calls)
9. `events.go` (22 calls)
10. `gate.go` (21 calls)
11. `cost.go` (19 calls)
12. `publish.go` (17 calls)
13. `action.go` (17 calls)
14. `coordination.go` (16 calls)
15. `lock.go` (15 calls)
16. `interspect.go` (13 calls)
17. `config.go` (12 calls)

**IMPORTANT:** In `main.go`, the flag parsing errors (lines 46-47) run BEFORE slog is initialized. These 2-3 calls must remain as `fmt.Fprintf(os.Stderr, ...)`.

**Step 2: Build and test after each batch of 3-4 files**

Run: `cd /home/mk/projects/Demarch/core/intercore && go build ./cmd/ic/ && go test -race ./...`

**Step 3: Commit per batch**

```bash
git commit -m "refactor(ic): migrate <batch> subcommands to slog"
```

Aim for 4-5 commits covering all 17 files.

---

## Task 5: Trace Schema Migration (v23)

**Bead:** iv-0kn9y
**Files:**
- Create: `internal/db/migrations/023_audit_trace_id.sql`
- Modify: `internal/audit/audit.go` (Entry struct, INSERT, Query, VerifyIntegrity)
- Create or modify: `internal/db/migrator_test.go` (add v23 test)

**Step 1: Write the migration file**

```sql
-- v23: add trace_id to audit_log for cross-layer trace correlation
ALTER TABLE audit_log ADD COLUMN trace_id TEXT NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_audit_log_trace ON audit_log(trace_id) WHERE trace_id != '';
```

**Step 2: Write migration test**

Add to `internal/db/migrator_test.go`:
```go
func TestMigrator_V22Upgrade(t *testing.T) {
	// Create DB at v22, run migrator, verify trace_id column exists
	db := openTestDB(t)
	setVersion(t, db, 22)
	// Apply baseline (creates all tables at v22 schema)
	applyBaseline(t, db)
	setVersion(t, db, 22) // override baseline's MaxVersion

	m := NewMigrator(&DB{db: db})
	applied, err := m.Run(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if applied != 1 {
		t.Errorf("applied = %d, want 1", applied)
	}

	// Verify column exists
	var traceID string
	err = db.QueryRow("SELECT trace_id FROM audit_log LIMIT 0").Scan(&traceID)
	// Should not error (column exists), even if no rows
	if err != nil && err != sql.ErrNoRows {
		t.Errorf("trace_id column missing: %v", err)
	}
}
```

**Step 3: Run migration test**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race -v ./internal/db/ -run TestMigrator`
Expected: All pass including new v23 test

**Step 4: Update audit.go Entry struct**

Add `TraceID` field to the `Entry` struct (around line 55-66):
```go
type Entry struct {
	// existing fields...
	TraceID     string // NEW: trace correlation ID from IC_TRACE_ID env
}
```

**Step 5: Update audit.go INSERT**

At line ~167, update the INSERT statement:
```sql
INSERT INTO audit_log (session_id, event_type, actor, target, payload, metadata, prev_hash, checksum, sequence_num, trace_id, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

Add `entry.TraceID` to the args. **Do NOT include trace_id in computeChecksum** — keep the hash chain backward-compatible.

**Step 6: Update Query SELECT and VerifyIntegrity SELECT**

Add `trace_id` to the SELECT column list in both `Query()` (line ~274) and `VerifyIntegrity()` (line ~207). Add `&entry.TraceID` to `rows.Scan()`.

**Step 7: Populate trace_id from environment in Logger.Log()**

At the top of `Logger.Log()`, if `entry.TraceID` is empty, read from env:
```go
if entry.TraceID == "" {
	entry.TraceID = os.Getenv("IC_TRACE_ID")
}
```

**Step 8: Test**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./internal/audit/ ./internal/db/`
Expected: All pass

**Step 9: Commit**

```bash
git add internal/db/migrations/023_audit_trace_id.sql internal/audit/ internal/db/migrator_test.go
git commit -m "feat(audit): add trace_id column and env-based population (migration v23)"
```

---

## Task 6: Wire Trace Context into EventEnvelope

**Bead:** iv-0kn9y (continued)
**Files:**
- Modify: `internal/event/store.go` (lines 343-400 — defaultDispatchEnvelope, defaultCoordinationEnvelope)
- Modify: `internal/phase/event_envelope.go` (lines 20-40 — defaultPhaseEnvelopeJSON)

**Step 1: Update defaultDispatchEnvelope in store.go**

At the start of `defaultDispatchEnvelope` (line 343), read env vars:
```go
func (s *Store) defaultDispatchEnvelope(ctx context.Context, dispatchID, runID, fromStatus, toStatus string) *EventEnvelope {
	// Read propagated trace context from environment
	envTraceID := os.Getenv("IC_TRACE_ID")
	envSpanID := os.Getenv("IC_SPAN_ID")
	envParentSpanID := os.Getenv("IC_PARENT_SPAN_ID")

	traceID := envTraceID
	if traceID == "" {
		traceID = runID
		if traceID == "" {
			traceID = dispatchID
		}
	}
	// ... rest of function, using traceID ...

	envelope := &EventEnvelope{
		// ... existing fields ...
		TraceID:      traceID,
		SpanID:       envSpanID, // use env if set, otherwise generate
		ParentSpanID: envParentSpanID,
	}
	if envelope.SpanID == "" {
		envelope.SpanID = fmt.Sprintf("dispatch:%s:%d", dispatchID, time.Now().UnixNano())
	}
```

**Step 2: Update defaultCoordinationEnvelope in store.go**

Same pattern — read `IC_TRACE_ID`/`IC_SPAN_ID` from env, prefer env over synthetic defaults.

**Step 3: Update defaultPhaseEnvelopeJSON in phase/event_envelope.go**

Read env vars at the top:
```go
func defaultPhaseEnvelopeJSON(runID, eventType, fromPhase, toPhase string) *string {
	envTraceID := os.Getenv("IC_TRACE_ID")
	envSpanID := os.Getenv("IC_SPAN_ID")

	traceID := envTraceID
	if traceID == "" {
		traceID = runID
	}
	spanID := envSpanID
	if spanID == "" {
		spanID = fmt.Sprintf("phase:%s:%d", eventType, time.Now().UnixNano())
	}

	envelope := phaseEventEnvelope{
		TraceID:  traceID,
		SpanID:   spanID,
		// ... rest unchanged ...
	}
```

**Step 4: Test**

Run: `cd /home/mk/projects/Demarch/core/intercore && go test -race ./internal/event/ ./internal/phase/`
Expected: All pass

**Step 5: Commit**

```bash
git add internal/event/store.go internal/phase/event_envelope.go
git commit -m "feat(event): populate EventEnvelope trace context from IC_TRACE_ID env"
```

---

## Task 7: Bash Log Helpers (lib-log.sh)

**Bead:** iv-9993w
**Files:**
- Create: `os/clavain/hooks/lib-log.sh`
- Modify: `os/clavain/hooks/lib.sh` (add source line)

**Step 1: Write lib-log.sh**

```bash
#!/usr/bin/env bash
# lib-log.sh — Structured JSON logging for Clavain hooks and plugins.
# Source this file to get log_debug, log_info, log_warn, log_error.
# Output: JSON lines to stderr.
# Env vars:
#   IC_LOG_LEVEL      — debug|info|warn|error (default: info)
#   IC_TRACE_ID       — trace correlation ID
#   IC_SPAN_ID        — span ID for this operation
#   IC_LOG_COMPONENT  — component name (default: basename of caller)

[[ -n "${_LIB_LOG_LOADED:-}" ]] && return 0
_LIB_LOG_LOADED=1

_LOG_COMPONENT="${IC_LOG_COMPONENT:-$(basename "${BASH_SOURCE[1]:-unknown}" .sh)}"

# Level integers: debug=0, info=1, warn=2, error=3
_log_level_int() {
    case "${1:-info}" in
        debug) echo 0 ;;
        info)  echo 1 ;;
        warn)  echo 2 ;;
        error) echo 3 ;;
        *)     echo 1 ;;
    esac
}

_LOG_THRESHOLD=$(_log_level_int "${IC_LOG_LEVEL:-info}")

# Core log function. Usage: _log_emit LEVEL "message" [key=value ...]
_log_emit() {
    local level="$1" msg="$2"
    shift 2

    local level_int
    level_int=$(_log_level_int "$level")
    if (( level_int < _LOG_THRESHOLD )); then
        return 0
    fi

    # Build JSON with jq for safety (no injection from msg or extra fields)
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S" 2>/dev/null)

    local extra_args=()
    extra_args+=(--arg level "$level" --arg msg "$msg" --arg ts "$ts" --arg component "$_LOG_COMPONENT")

    if [[ -n "${IC_TRACE_ID:-}" ]]; then
        extra_args+=(--arg trace_id "$IC_TRACE_ID")
    fi
    if [[ -n "${IC_SPAN_ID:-}" ]]; then
        extra_args+=(--arg span_id "$IC_SPAN_ID")
    fi

    # Build extra key=value pairs
    local kv_expr=""
    local idx=0
    for pair in "$@"; do
        local key="${pair%%=*}"
        local val="${pair#*=}"
        extra_args+=(--arg "kv_${idx}" "$key" --arg "vv_${idx}" "$val")
        kv_expr="${kv_expr} | .[\$kv_${idx}] = \$vv_${idx}"
        idx=$((idx + 1))
    done

    local jq_filter='{level: $level, msg: $msg, ts: $ts, component: $component}'
    if [[ -n "${IC_TRACE_ID:-}" ]]; then
        jq_filter="${jq_filter} | .trace_id = \$trace_id"
    fi
    if [[ -n "${IC_SPAN_ID:-}" ]]; then
        jq_filter="${jq_filter} | .span_id = \$span_id"
    fi
    jq_filter="${jq_filter}${kv_expr}"

    jq -nc "${extra_args[@]}" "$jq_filter" >&2
}

log_debug() { _log_emit debug "$@"; }
log_info()  { _log_emit info "$@"; }
log_warn()  { _log_emit warn "$@"; }
log_error() { _log_emit error "$@"; }

# Generate a 32-char hex trace ID
generate_trace_id() {
    od -An -tx1 -N16 /dev/urandom 2>/dev/null | tr -d ' \n' || printf '%032x' "$$$(date +%s%N)"
}

# Generate a 16-char hex span ID
generate_span_id() {
    od -An -tx1 -N8 /dev/urandom 2>/dev/null | tr -d ' \n' || printf '%016x' "$$$(date +%s%N)"
}
```

**Step 2: Source from lib.sh**

At the top of `os/clavain/hooks/lib.sh` (after any existing guard), add:
```bash
# Structured logging — available to all hooks
source "${BASH_SOURCE[0]%/*}/lib-log.sh" 2>/dev/null || true
```

**Step 3: Test manually**

```bash
cd /home/mk/projects/Demarch/os/clavain/hooks
source lib-log.sh
log_info "test message" key=value
# Expected on stderr: {"level":"info","msg":"test message","ts":"2026-02-26T...","component":"bash","key":"value"}

IC_LOG_LEVEL=warn log_info "should not appear"
# Expected: no output (info < warn)

IC_LOG_LEVEL=warn log_warn "should appear"
# Expected: JSON line on stderr

echo "trace: $(generate_trace_id) span: $(generate_span_id)"
# Expected: 32-char hex and 16-char hex
```

**Step 4: Commit**

```bash
git add os/clavain/hooks/lib-log.sh os/clavain/hooks/lib.sh
git commit -m "feat(clavain): add lib-log.sh structured JSON logging helpers"
```

---

## Task 8: Clavain Trace Propagation

**Bead:** iv-ifsxm
**Files:**
- Modify: `os/clavain/hooks/session-start.sh` (lines 19-25 — generate IC_TRACE_ID)
- Modify: `os/clavain/hooks/lib-intercore.sh` (lines 16-17 — accept IC_TRACE_ID from env)
- Modify: `os/clavain/hooks/lib-sprint.sh` (lines 34, 906, 910, 955 — use log_* + propagate trace)
- Modify: `os/clavain/hooks/session-handoff.sh` (line 35 area — log trace context)

**Step 1: Generate IC_TRACE_ID in session-start.sh**

After line 24 (where `CLAUDE_SESSION_ID` is exported), add:
```bash
# Generate trace context for this session
_trace_id=$(generate_trace_id)
_span_id=$(generate_span_id)
echo "export IC_TRACE_ID=${_trace_id}" >> "$CLAUDE_ENV_FILE"
echo "export IC_SPAN_ID=${_span_id}" >> "$CLAUDE_ENV_FILE"
log_info "session started" session_id="$_session_id" trace_id="$_trace_id"
```

This requires lib-log.sh to be sourced before this point. Since `lib.sh` is sourced at line 16 and lib.sh now sources lib-log.sh, `generate_trace_id` and `log_info` are available.

**Step 2: Accept trace context in lib-intercore.sh**

After line 16 (`INTERCORE_BIN=""`), add documentation comment:
```bash
# Trace context: IC_TRACE_ID and IC_SPAN_ID are inherited from the environment.
# They are set by session-start.sh and flow through to all ic CLI calls
# via process environment inheritance. The ic binary reads them directly from env.
```

No code change needed — the ic binary (after Task 2) reads `IC_TRACE_ID` from env automatically. The bash env vars are inherited by child processes without explicit passing.

**Step 3: Migrate key lib-sprint.sh logging**

Replace line 34:
```bash
# Old: echo "Sprint requires intercore..." >&2
log_error "Sprint requires intercore (ic). Run install.sh or /clavain:setup"
```

Replace lines 906, 910 (direct `$INTERCORE_BIN` calls — these already inherit `IC_TRACE_ID` from env):
```bash
# No change needed — env vars are inherited. But add logging:
log_debug "budget check" run_id="$run_id"
"$INTERCORE_BIN" run budget "$run_id" 2>/dev/null
```

Replace line 955:
```bash
# Old: echo "Phase: $from_phase → $to_phase (auto-advancing)" >&2
log_info "phase advancing" from="$from_phase" to="$to_phase" run_id="$run_id"
```

**Step 4: Add trace logging to session-handoff.sh**

After line 35 (`SESSION_ID=...`), add:
```bash
log_info "session handoff" session_id="${SESSION_ID:0:8}" trace_id="${IC_TRACE_ID:-unset}"
```

**Step 5: Test end-to-end**

Start a Claude Code session, verify:
1. `echo $IC_TRACE_ID` shows a 32-char hex value
2. `echo $IC_SPAN_ID` shows a 16-char hex value
3. `ic events tail --all` shows trace_id in envelope JSON

**Step 6: Commit**

```bash
git add os/clavain/hooks/session-start.sh os/clavain/hooks/lib-intercore.sh os/clavain/hooks/lib-sprint.sh os/clavain/hooks/session-handoff.sh
git commit -m "feat(clavain): propagate IC_TRACE_ID/IC_SPAN_ID through hook lifecycle"
```

---

## Task 9: Plugin Adoption Guide and Python Formatter

**Bead:** iv-cv9yi
**Files:**
- Create: `docs/guide-plugin-logging.md`
- Create: `interverse/interbase/python/interlogger.py` (or similar shared location)
- Modify: 1 Go plugin MCP as reference (e.g., `interverse/intermap/cmd/intermap-mcp/main.go`)
- Modify: 1 Python plugin as reference (e.g., `interverse/intersearch/server.py` or `interverse/intermap/python/intermap/__init__.py`)

**Step 1: Write the plugin logging guide**

Create `docs/guide-plugin-logging.md` documenting:
- The structured logging convention for Go (`log/slog` + `observability.NewHandler`)
- The structured logging convention for bash (`source lib-log.sh`)
- The structured logging convention for Python (JSON formatter reading `IC_TRACE_ID`)
- How trace context flows through environment variables
- How to test trace correlation with `ic events tail`

**Step 2: Write Python JSON formatter**

```python
# interlogger.py — Structured JSON logging for Demarch Python plugins
import json
import logging
import os
import sys
from datetime import datetime, timezone


class InterFormatter(logging.Formatter):
    """JSON formatter that includes IC_TRACE_ID from environment."""

    def format(self, record):
        entry = {
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "component": record.name,
        }
        trace_id = os.environ.get("IC_TRACE_ID")
        if trace_id:
            entry["trace_id"] = trace_id
        span_id = os.environ.get("IC_SPAN_ID")
        if span_id:
            entry["span_id"] = span_id
        if record.exc_info and record.exc_info[0]:
            entry["error"] = str(record.exc_info[1])
        return json.dumps(entry)


def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """Configure structured JSON logging for a plugin component."""
    logger = logging.getLogger(name)
    env_level = os.environ.get("IC_LOG_LEVEL", level).upper()
    logger.setLevel(getattr(logging, env_level, logging.INFO))

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(InterFormatter())
    logger.addHandler(handler)
    return logger
```

**Step 3: Migrate intermap Go MCP as reference**

In `interverse/intermap/cmd/intermap-mcp/main.go`, add after imports:
```go
import "github.com/mistakeknot/intercore/internal/observability"
```

In `main()`, before the MCP server starts:
```go
slog.SetDefault(slog.New(observability.NewHandler(os.Stderr, observability.ParseLevel(os.Getenv("IC_LOG_LEVEL")))))
```

Replace the `fmt.Fprintf(os.Stderr, "intermap-mcp: %v\n", err)` with `slog.Error("intermap-mcp failed", "error", err)`.

**Note:** Intermap's go.mod needs to import intercore — this may require a `replace` directive or using the observability package as a copied minimal file. If import is not feasible, copy the 3 key functions (`NewHandler`, `ParseLevel`, `TraceFromEnv`) into a local `internal/log/` package.

**Step 4: Migrate intersearch Python as reference**

In `interverse/intersearch/server.py`, replace:
```python
import logging
logger = logging.getLogger(__name__)
```
with:
```python
from interlogger import setup_logging
logger = setup_logging("intersearch")
```

**Step 5: Commit**

```bash
git add docs/guide-plugin-logging.md interverse/
git commit -m "docs(plugins): add structured logging guide and reference migrations"
```

---

## Task 10: CI Verification

**Files:**
- Modify: `core/intercore/.github/workflows/ci.yml` (add migration v23 test)

**Step 1: Verify the existing migration test step covers v23**

The CI already has:
```yaml
- name: Run migration tests
  run: go test -race -v ./internal/db/ -run TestMigrator
```

Since Task 5 added `TestMigrator_V22Upgrade`, this is automatically covered. No CI change needed unless we want explicit v23 naming.

**Step 2: Run full test suite**

```bash
cd /home/mk/projects/Demarch/core/intercore
go build ./...
go vet ./...
go test -race ./...
```

Expected: All pass including new observability, audit, migration tests.

**Step 3: Verify contracts are up to date**

```bash
cd /home/mk/projects/Demarch/core/intercore
go generate ./contracts/...
git diff --exit-code contracts/
```

If audit.Entry struct changed, contracts may need regeneration. If schemas drift, create override doc: `contracts/overrides/2026-02-26-audit-trace-id.md`.

**Step 4: Commit if needed**

```bash
git add .github/workflows/ci.yml contracts/
git commit -m "ci: verify migration v23 and updated contracts"
```

---

## Dependency Graph

```
Task 1 (observability pkg) ──┬──→ Task 2 (slog init in main.go)
                              │      └──→ Task 3 (event handler migration)
                              │             └──→ Task 4 (cmd/ic subcommand migration)
                              └──→ Task 5 (trace schema v23) ──→ Task 6 (EventEnvelope wiring)

Task 7 (lib-log.sh) ──→ Task 8 (Clavain trace propagation)

Task 9 (plugin guide) depends on Tasks 1 + 7

Task 10 (CI) depends on all prior tasks
```

**Parallelism:** Tasks 1-6 (Go) and Tasks 7-8 (bash) are independent tracks. Task 9 depends on both. Task 10 is final verification.
