# Pollard Hunter Resilience Implementation Plan
**Phase:** executing (as of 2026-02-23T21:19:13Z)

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Make individual hunter failures non-fatal across all Pollard execution paths, with per-hunter error status and configurable retry.

**Architecture:** Both the CLI scan loop (`cli/scan.go`) and the API scanner (`api/scanner.go`) already `continue` past individual hunter errors. The watch path delegates to `Scanner.Scan()` which also continues. The gaps are: (1) no retry on transient failures, (2) no structured per-hunter error status in `HuntResult`, (3) the CLI scan loop prints errors but doesn't summarize them, and (4) the watcher's `RunOnce` treats scanner errors as fatal. We add retry at the call site, a `HunterStatus` enum for structured error reporting, and a summary table at the end of scan output.

**Tech Stack:** Go, `internal/pollard/hunters`, `internal/pollard/cli`, `internal/pollard/api`, `internal/pollard/watch`

---

### Task 1: Add HunterStatus enum and per-hunter status to HuntResult

**Files:**
- Modify: `apps/autarch/internal/pollard/hunters/hunter.go:88-109` (HuntResult struct)

**Step 1: Add HunterStatus type**

Add after the `PipelineOptions` struct (before `HuntResult`):

```go
// HunterStatus represents the outcome of a hunt operation.
type HunterStatus int

const (
	HunterStatusOK HunterStatus = iota
	HunterStatusPartial  // Some results, some errors
	HunterStatusFailed   // No results, error occurred
	HunterStatusSkipped  // Not run (e.g., not in registry)
)

func (s HunterStatus) String() string {
	switch s {
	case HunterStatusOK:
		return "ok"
	case HunterStatusPartial:
		return "partial"
	case HunterStatusFailed:
		return "failed"
	case HunterStatusSkipped:
		return "skipped"
	default:
		return "unknown"
	}
}
```

**Step 2: Add Status and ErrorMsg fields to HuntResult**

Add to the `HuntResult` struct:

```go
Status   HunterStatus
ErrorMsg string // Human-readable error summary (empty if OK)
```

**Step 3: Keep Success() unchanged — it stays error-based**

Do NOT change `Success()`. The existing `len(r.Errors) == 0` check is the correct contract — all 12+ hunters populate `Errors` but never set `Status`. Changing this would silently break DB run recording via `CompleteRun`.

`Success()` remains as-is. The new `Status` field is informational for callers that want structured reporting (CLI summary, API responses).

**Step 4: Build and verify**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./internal/pollard/...`
Expected: builds without errors (existing callers don't set Status, so it defaults to 0 = HunterStatusOK, which is backward compatible)

**Step 5: Commit**

```bash
git add internal/pollard/hunters/hunter.go
git commit -m "feat(pollard): add HunterStatus enum for structured error reporting"
```

---

### Task 2: Add retry helper for transient hunter failures

**Files:**
- Create: `apps/autarch/internal/pollard/hunters/retry.go`
- Create: `apps/autarch/internal/pollard/hunters/retry_test.go`

**Step 1: Write the retry helper**

Create `apps/autarch/internal/pollard/hunters/retry.go`:

```go
package hunters

import (
	"context"
	"errors"
	"fmt"
	"net"
	"strings"
	"time"
)

// RetryConfig controls retry behavior for a hunter.
type RetryConfig struct {
	MaxAttempts int           // Total attempts (1 = no retry)
	Backoff     time.Duration // Base delay between retries (doubled each attempt)
}

// DefaultRetryConfig returns a sensible default: 2 attempts with 1s backoff.
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{MaxAttempts: 2, Backoff: 1 * time.Second}
}

// HuntWithRetry executes a hunter with retry on transient failures.
// Returns the result from the first successful attempt, or the last error.
func HuntWithRetry(ctx context.Context, h Hunter, cfg HunterConfig, rc RetryConfig) (*HuntResult, error) {
	if rc.MaxAttempts < 1 {
		rc.MaxAttempts = 1
	}

	var lastErr error
	for attempt := 1; attempt <= rc.MaxAttempts; attempt++ {
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		result, err := h.Hunt(ctx, cfg)
		if err == nil {
			return result, nil
		}

		lastErr = err
		if !isTransient(err) {
			return nil, err
		}

		if attempt < rc.MaxAttempts {
			delay := rc.Backoff * time.Duration(1<<(attempt-1))
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(delay):
			}
		}
	}

	return nil, fmt.Errorf("after %d attempts: %w", rc.MaxAttempts, lastErr)
}

// isTransient returns true for errors that may succeed on retry.
func isTransient(err error) bool {
	if err == nil {
		return false
	}

	// Network errors — only transient ones (timeout, temporary)
	var netErr net.Error
	if errors.As(err, &netErr) {
		return netErr.Timeout()
	}

	// Common transient HTTP status messages in error strings
	msg := strings.ToLower(err.Error())
	for _, s := range []string{"rate limit", "429", "503", "timeout", "temporary"} {
		if strings.Contains(msg, s) {
			return true
		}
	}

	return false
}
```

**Step 2: Write tests**

Create `apps/autarch/internal/pollard/hunters/retry_test.go`:

```go
package hunters

import (
	"context"
	"errors"
	"net"
	"testing"
	"time"
)

type fakeHunter struct {
	name     string
	calls    int
	failN    int   // Fail first N calls
	err      error // Error to return on failure
}

func (f *fakeHunter) Name() string { return f.name }

func (f *fakeHunter) Hunt(ctx context.Context, _ HunterConfig) (*HuntResult, error) {
	f.calls++
	if ctx.Err() != nil {
		return nil, ctx.Err()
	}
	if f.calls <= f.failN {
		return nil, f.err
	}
	return &HuntResult{HunterName: f.name, SourcesCollected: 1}, nil
}

func TestHuntWithRetry_SucceedsFirstAttempt(t *testing.T) {
	h := &fakeHunter{name: "test"}
	result, err := HuntWithRetry(context.Background(), h, HunterConfig{}, DefaultRetryConfig())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if h.calls != 1 {
		t.Errorf("expected 1 call, got %d", h.calls)
	}
	if result.SourcesCollected != 1 {
		t.Errorf("expected 1 source, got %d", result.SourcesCollected)
	}
}

func TestHuntWithRetry_RetriesTransient(t *testing.T) {
	h := &fakeHunter{name: "test", failN: 1, err: &net.DNSError{IsTimeout: true}}
	result, err := HuntWithRetry(context.Background(), h, HunterConfig{}, RetryConfig{MaxAttempts: 2, Backoff: time.Millisecond})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if h.calls != 2 {
		t.Errorf("expected 2 calls, got %d", h.calls)
	}
	if result.SourcesCollected != 1 {
		t.Errorf("expected 1 source, got %d", result.SourcesCollected)
	}
}

func TestHuntWithRetry_NoRetryOnNonTransient(t *testing.T) {
	h := &fakeHunter{name: "test", failN: 10, err: errors.New("invalid config")}
	_, err := HuntWithRetry(context.Background(), h, HunterConfig{}, RetryConfig{MaxAttempts: 3, Backoff: time.Millisecond})
	if err == nil {
		t.Fatal("expected error")
	}
	if h.calls != 1 {
		t.Errorf("expected 1 call (no retry), got %d", h.calls)
	}
}

func TestHuntWithRetry_ExhaustsAttempts(t *testing.T) {
	h := &fakeHunter{name: "test", failN: 10, err: &net.DNSError{IsTimeout: true}}
	_, err := HuntWithRetry(context.Background(), h, HunterConfig{}, RetryConfig{MaxAttempts: 2, Backoff: time.Millisecond})
	if err == nil {
		t.Fatal("expected error")
	}
	if h.calls != 2 {
		t.Errorf("expected 2 calls, got %d", h.calls)
	}
}

func TestHuntWithRetry_RespectsContextCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	h := &fakeHunter{name: "test", failN: 10, err: &net.DNSError{IsTimeout: true}}
	_, err := HuntWithRetry(ctx, h, HunterConfig{}, RetryConfig{MaxAttempts: 3, Backoff: time.Millisecond})
	if !errors.Is(err, context.Canceled) {
		t.Errorf("expected context.Canceled, got %v", err)
	}
}

func TestIsTransient(t *testing.T) {
	tests := []struct {
		err       error
		transient bool
	}{
		{nil, false},
		{errors.New("invalid config"), false},
		{errors.New("rate limit exceeded"), true},
		{errors.New("HTTP 429 Too Many Requests"), true},
		{errors.New("HTTP 503 Service Unavailable"), true},
		{&net.DNSError{IsTimeout: true}, true},
	}
	for _, tt := range tests {
		if got := isTransient(tt.err); got != tt.transient {
			t.Errorf("isTransient(%v) = %v, want %v", tt.err, got, tt.transient)
		}
	}
}
```

**Step 3: Run tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/pollard/hunters/ -run TestHuntWithRetry -v -race`
Expected: all pass

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/pollard/hunters/ -run TestIsTransient -v -race`
Expected: all pass

**Step 4: Commit**

```bash
git add internal/pollard/hunters/retry.go internal/pollard/hunters/retry_test.go
git commit -m "feat(pollard): add retry helper for transient hunter failures

HuntWithRetry retries on network errors, rate limits, and timeouts
with exponential backoff. Non-transient errors fail immediately."
```

---

### Task 3: Wire retry into CLI scan loop and add summary table

**Files:**
- Modify: `apps/autarch/internal/pollard/cli/scan.go:171-250` (hunter execution loop)

**Step 1: Use HuntWithRetry in the scan loop**

Replace the direct `hunter.Hunt(ctx, hCfg)` call (line 227) with:

```go
result, err := hunters.HuntWithRetry(ctx, hunter, hCfg, hunters.DefaultRetryConfig())
```

**Step 2: Set HunterStatus on result**

After a successful hunt, set `result.Status` based on whether it had partial errors:

```go
if err != nil {
	fmt.Printf("  Error: %v\n", err)
	if runID > 0 {
		db.CompleteRun(runID, false, 0, 0, err.Error())
	}
	// Track failed hunter for summary
	failedHunters = append(failedHunters, hunterSummary{name: name, status: hunters.HunterStatusFailed, err: err})
	continue
}

if len(result.Errors) > 0 {
	result.Status = hunters.HunterStatusPartial
}
```

**Step 3: Add summary table at end of scan**

After the hunter loop, add a summary:

```go
// Print summary
if len(failedHunters) > 0 {
	fmt.Printf("\n--- Hunter Summary ---\n")
	for _, h := range failedHunters {
		fmt.Printf("  %s: %s (%v)\n", h.name, h.status, h.err)
	}
	fmt.Printf("\n%d/%d hunters completed successfully\n", len(hunterNames)-len(failedHunters), len(hunterNames))
}
```

Define `hunterSummary` as a local type before the loop:

```go
type hunterSummary struct {
	name   string
	status hunters.HunterStatus
	err    error
}
var failedHunters []hunterSummary
```

**Step 4: Build check**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/pollard/`
Expected: builds without errors

**Step 5: Commit**

```bash
git add internal/pollard/cli/scan.go
git commit -m "feat(pollard): wire retry into CLI scan loop with summary table

Hunters retry once on transient errors (network, rate limit, timeout).
Failed hunters show in summary table at end of scan output."
```

---

### Task 4: Wire retry into API Scanner.Scan and set HunterStatus

**Files:**
- Modify: `apps/autarch/internal/pollard/api/scanner.go:198-206` (hunt execution)

**Step 1: Replace direct hunt call with retry**

Replace line 199:
```go
huntResult, err := hunter.Hunt(ctx, hCfg)
```

With:
```go
huntResult, err := hunters.HuntWithRetry(ctx, hunter, hCfg, hunters.DefaultRetryConfig())
```

**Step 2: Set status on failed results**

When a hunter fails, create a `HuntResult` with status instead of just appending an error:

```go
if err != nil {
	failedResult := &hunters.HuntResult{
		HunterName: name,
		Status:     hunters.HunterStatusFailed,
		ErrorMsg:   err.Error(),
		Errors:     []error{err},
	}
	result.HunterResults[name] = failedResult
	result.Errors = append(result.Errors, fmt.Errorf("hunter %s failed: %w", name, err))
	if runID > 0 {
		s.db.CompleteRun(runID, false, 0, 0, err.Error())
	}
	continue
}
```

**Step 2b: Set HunterStatusPartial on success path with errors**

After the error-handling block, when a hunt succeeds but has partial errors:

```go
if len(huntResult.Errors) > 0 {
	huntResult.Status = hunters.HunterStatusPartial
	huntResult.ErrorMsg = huntResult.Errors[0].Error()
}
```

This ensures `Scanner.Scan()` always returns per-hunter results even for failures, so the watcher can report partial results.

**Step 3: Build check**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./internal/pollard/...`
Expected: builds without errors

**Step 4: Commit**

```bash
git add internal/pollard/api/scanner.go
git commit -m "feat(pollard): wire retry into Scanner.Scan, always populate HunterResults

Failed hunters now appear in HunterResults with HunterStatusFailed.
Watch path gets partial results instead of just errors."
```

---

### Task 5: Make watcher resilient to scanner errors

**Files:**
- Modify: `apps/autarch/internal/pollard/watch/watcher.go:50-91` (RunOnce)

**Step 1: Handle partial scan results in RunOnce**

The current code returns early on scanner error. Change it to use partial results:

Replace lines 57-63:
```go
// Run scan
result, err := w.scanner.Scan(ctx, api.ScanOptions{
	Hunters: hunters,
})
if err != nil {
	return nil, fmt.Errorf("watch scan: %w", err)
}
```

With:
```go
// Run scan — partial results are usable even when some hunters fail.
// Note: Scanner.Scan() currently always returns nil error (it puts errors
// into result.Errors), but we guard against future changes.
result, err := w.scanner.Scan(ctx, api.ScanOptions{
	Hunters: hunters,
})
if ctx.Err() != nil {
	return nil, fmt.Errorf("watch scan: %w", ctx.Err())
}
if err != nil {
	fmt.Fprintf(os.Stderr, "watch scan partial failure: %v\n", err)
}
if result == nil {
	result = &api.ScanResult{HunterResults: make(map[string]*hunters.HuntResult)}
}
```

**Step 2: Build check**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./internal/pollard/...`
Expected: builds without errors

**Step 3: Run existing watch tests**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/pollard/watch/ -v -race`
Expected: pass (existing tests should still work)

**Step 4: Commit**

```bash
git add internal/pollard/watch/watcher.go
git commit -m "feat(pollard): make watcher resilient to partial scanner failures

Context cancellation is still fatal. Other errors are logged and
the watcher continues with partial results."
```

---

### Task 6: Final integration test

**Files:**
- Test: all modified files

**Step 1: Build all pollard binaries**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go build ./cmd/pollard/`
Expected: builds without errors

**Step 2: Run full pollard test suite**

Run: `cd /home/mk/projects/Demarch/apps/autarch && go test ./internal/pollard/... -race -count=1 -timeout=60s`
Expected: all pass

**Step 3: Commit if fixups needed**

Only if Step 2 revealed issues.
