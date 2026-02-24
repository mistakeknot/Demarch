# Correctness Review: iv-xlpg Pollard Hunter Resilience Plan
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-23
**Plan:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-pollard-hunter-resilience.md`

---

## Invariants Under Review

Before listing findings, the correctness invariants the plan must preserve:

1. **I1 — Success() semantic:** `HuntResult.Success()` currently returns `true` iff `len(r.Errors) == 0`. Every call site (`cli/scan.go:237`, `cli/apply.go:186`, `cli/research.go:129`, `api/scanner.go:209`) relies on this exact semantic.
2. **I2 — Zero-value safety:** `HuntResult` instances are created directly by every hunter (12+ implementations) via `result := &HuntResult{...}`. Adding new fields must not change the meaning of existing results.
3. **I3 — HunterStatus name uniqueness:** The `hunters` package must not shadow an existing type name visible to the package or its importers.
4. **I4 — Scanner.Scan partial-result contract:** `Scanner.Scan` currently returns `(result, nil)` always (errors go into `result.Errors`); callers that receive `(result, non-nil-err)` are not currently written.
5. **I5 — Context cancellation propagation:** A cancelled context must abort in-flight retries promptly; sleeping past context cancellation is a production stall.
6. **I6 — Overflow safety:** Exponential backoff computations must not produce negative delays or overflow.
7. **I7 — Nil result guard:** `HuntWithRetry` may return `(nil, err)`. Every call site that dereferences the result without a nil check will panic.

---

## Finding 1 — CRITICAL: HunterStatus Name Collision with research.HunterStatus

**Severity:** Build-breaking / namespace corruption

**Location:** Plan Task 1; source truth at `apps/autarch/internal/pollard/research/run.go:31`

**Finding:**
The `research` sub-package already defines a type named `HunterStatus`:

```go
// apps/autarch/internal/pollard/research/run.go:30-48
// HunterStatus tracks the state of a single hunter within a run.
type HunterStatus struct {
    Name       string
    Status     Status
    StartedAt  time.Time
    FinishedAt time.Time
    Findings   int
    Error      string
}
```

The plan proposes adding `hunters.HunterStatus` (an `int` enum) to `apps/autarch/internal/pollard/hunters/hunter.go`. While these are in different packages and will not cause a build error by themselves, the name collision creates a direct hazard:

- Any file that imports both `hunters` and `research` — such as `api/orchestrator.go` and `api/scanner.go` which import both — will have two `HunterStatus` types in scope, requiring fully-qualified references everywhere. The plan does not account for this.
- `research/coordinator.go:379` exports `GetHunterStatuses() map[string]HunterStatus` (returning `research.HunterStatus`). The plan's `hunters.HunterStatus` will conflict in documentation, grep results, and any future unification attempt.

**Concrete collision scenario:**
`api/scanner.go` already imports `hunters`. If it later imports `research` for coordinator use, the code `var s HunterStatus` becomes ambiguous to the reader and the linter flags it as a shadowing issue.

**Required fix:** Rename the new enum. Candidates: `HuntOutcome`, `HuntStatusCode`, or `ResultStatus`. Do not introduce a second `HunterStatus` into this package family.

---

## Finding 2 — CRITICAL: Success() Semantic Break — Silent Regression on All Existing Call Sites

**Severity:** Data integrity regression at `api/scanner.go`, `cli/apply.go`, `cli/research.go`

**Location:** Plan Task 1, Step 3; source truth at `hunter.go:107-109`

**Current implementation:**
```go
// hunter.go:107-109
func (r *HuntResult) Success() bool {
    return len(r.Errors) == 0
}
```

**Plan's proposed replacement:**
```go
func (r *HuntResult) Success() bool {
    return r.Status == HunterStatusOK
}
```

**The invariant break:**
The plan claims this is backward-compatible because `Status` zero-value is `HunterStatusOK` (iota = 0). This is correct for `HuntResult` instances that are _returned by new code that sets Status_. But it is wrong for:

1. **Existing hunters that set `result.Errors` but never set `result.Status`.** All 12+ hunter implementations (github.go, hackernews.go, arxiv.go, competitor.go, openalex.go, pubmed.go, usda.go, legal.go, economics.go, wiki.go, custom.go, agent.go, context7.go) create `HuntResult` via literal initialization and append to `.Errors` on failure. Under the new `Success()`, they will report `Success() == true` even when `len(r.Errors) > 0`, because `Status` is still zero (`HunterStatusOK`).

2. **Effect at api/scanner.go:209-215:**
```go
success := huntResult.Success()   // now always true (Status=0) for old hunters
errMsg := ""
if !success && len(huntResult.Errors) > 0 {
    errMsg = huntResult.Errors[0].Error()
}
if runID > 0 {
    s.db.CompleteRun(runID, success, ...)  // records false positives as "success"
}
```
Every partial-failure hunt will be recorded in the DB as successful. This silently corrupts the run history.

3. **Effect at cli/apply.go:186 and cli/research.go:129:** Same false-positive success reporting.

**The correct approach:** Either (a) keep `Success()` as `len(r.Errors) == 0` and treat `Status` as a supplementary field computed from it, or (b) update all hunter implementations to set `Status` as part of this plan. The plan does neither.

**Minimal fix:** Do not change `Success()`. Instead, derive `Status` from `Errors` at the boundary where it is needed:
```go
func (r *HuntResult) DeriveStatus() HunterStatus {
    if len(r.Errors) == 0 {
        return HunterStatusOK
    }
    if r.SourcesCollected > 0 {
        return HunterStatusPartial
    }
    return HunterStatusFailed
}
```
Call this at the call sites that need a `Status` value rather than making `Success()` dependent on callers setting a field they have no obligation to set.

---

## Finding 3 — HIGH: Backoff Overflow on High MaxAttempts

**Severity:** Runtime panic or extreme stall (depends on Go runtime behavior)

**Location:** Plan Task 2, Step 1; `retry.go` proposed code, line 136

**Proposed code:**
```go
delay := rc.Backoff * time.Duration(1<<(attempt-1))
```

**The failure:**
`1 << (attempt-1)` is an untyped int shift. In Go, `time.Duration` is `int64`. When `attempt` reaches 64 or higher, `1 << 63` overflows to the minimum negative `int64` value (`-9223372036854775808`). Multiplying a positive `time.Duration` by a negative multiplier produces a negative duration. `time.After(negative_duration)` fires immediately (equivalent to `time.After(0)`). The retry loop then burns through all remaining attempts with zero delay, which defeats the entire backoff purpose.

For `MaxAttempts: 2` (the plan's default) this never triggers. But `RetryConfig` is a public exported struct. Any caller that passes `MaxAttempts: 64` or higher hits this path. The fix is a cap:

```go
shift := attempt - 1
if shift > 30 {
    shift = 30  // cap at ~12 days; prevents int64 overflow
}
delay := rc.Backoff * time.Duration(1<<shift)
```

A separate cap on maximum delay (e.g., 30 seconds) is also recommended for operational safety, but the overflow cap is required for correctness.

---

## Finding 4 — HIGH: Context Cancellation Race in Retry Sleep

**Severity:** Stall under cancellation (production wake-at-3am if hunting loops run in watch mode)

**Location:** Plan Task 2, `retry.go`, lines 136-142

**Proposed code:**
```go
if attempt < rc.MaxAttempts {
    delay := rc.Backoff * time.Duration(1<<(attempt-1))
    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    case <-time.After(delay):
    }
}
```

This is structurally correct for the sleep itself. However, there is a race between the `h.Hunt(ctx, cfg)` call and the `select` on `ctx.Done()`: `Hunt` is passed `ctx` directly, so if the context is already cancelled before `Hunt` is called, `Hunt` should return `ctx.Err()` immediately. But `isTransient` will then be called on `context.Canceled` or `context.DeadlineExceeded`.

**The isTransient function:**
```go
func isTransient(err error) bool {
    var netErr net.Error
    if errors.As(err, &netErr) {
        return true
    }
    msg := strings.ToLower(err.Error())
    for _, s := range []string{"rate limit", "429", "503", "timeout", "temporary"} {
        if strings.Contains(msg, s) {
            return true
        }
    }
    return false
}
```

`context.DeadlineExceeded.Error()` returns `"context deadline exceeded"`. This does not match "timeout". However, `context.DeadlineExceeded` implements `net.Error` with `Timeout() bool { return true }` and `Temporary() bool { return false }` in some Go versions, and in the standard library it does _not_ implement `net.Error`. Verify: the standard `context.DeadlineExceeded` does NOT satisfy `net.Error` (it is `*deadlineExceededError` which does not have `Timeout()`/`Temporary()` in the `net.Error` sense in current Go). So it falls through to string matching, and "context deadline exceeded" does not contain "timeout" as a substring — it contains "deadline", not "timeout". Therefore `isTransient` returns `false` for `context.DeadlineExceeded`, and the retry aborts immediately, which is correct.

`context.Canceled.Error()` = `"context canceled"` — also does not match any transient string. Correct.

**But**: a hunter that wraps context cancellation in a network error (e.g., `fmt.Errorf("HTTP GET: %w", netErr)` where `netErr.Timeout()` is true because it was cancelled mid-flight) will return `isTransient == true`. The retry loop will then attempt to sleep, and the `select` on `ctx.Done()` will fire immediately because the context is already cancelled. This is actually handled correctly by the sleep select. The race here is a minor one — but it does mean that a cancelled-context hunt attempt still counts against `MaxAttempts` rather than aborting immediately before the sleep.

**The real race** is that `HuntWithRetry` does not check `ctx.Err()` before calling `h.Hunt(ctx, cfg)`. On the first iteration this is fine (Hunt itself will check). But if a transient failure happens and the context is cancelled during `h.Hunt`, the sleep select will catch it. The missing guard is before the `h.Hunt` call on subsequent attempts:

```go
for attempt := 1; attempt <= rc.MaxAttempts; attempt++ {
    // MISSING: if ctx.Err() != nil { return nil, ctx.Err() }
    result, err := h.Hunt(ctx, cfg)
    ...
}
```

Without this check, a cancelled context still dispatches into `h.Hunt` on every retry. Well-written hunters return immediately on cancelled context, so this is low severity in practice, but it is incorrect protocol.

**Fix:** Add `if ctx.Err() != nil { return nil, ctx.Err() }` at the top of the loop body.

---

## Finding 5 — HIGH: isTransient String Matching is Fragile and Unbounded

**Severity:** Silent incorrect retry behavior (either retrying non-retriable errors or not retrying retriable ones)

**Location:** Plan Task 2, `retry.go:160-168`

**The proposed detection:**
```go
msg := strings.ToLower(err.Error())
for _, s := range []string{"rate limit", "429", "503", "timeout", "temporary"} {
    if strings.Contains(msg, s) {
        return true
    }
}
```

**Problems:**

1. **"temporary" matches too broadly.** Any error message that happens to contain the word "temporary" — including business logic errors like "temporary file conflict during YAML merge" or "this is a temporary stub implementation" — will be retried. This is a footgun for future error messages from hunters.

2. **"503" matches too broadly.** An HTTP 503 from GitHub or HackerNews is transient. But an error like "configuration step 503 failed" or a local filesystem error with a path containing "503" would also match. The correct approach is to define sentinel error types.

3. **"timeout" substring:** `context.DeadlineExceeded.Error()` = `"context deadline exceeded"`. The word "timeout" does not appear, so deadline-exceeded is not retried (correct). But `net.OpError` with `Timeout() == true` will already be caught by the `errors.As(err, &netErr)` branch. The "timeout" string check is redundant with the `net.Error` branch for the standard cases and only adds fragility for non-standard cases.

4. **No match for "connection reset"** or `"EOF"` — both are common transient network errors in HTTP/1.1 long-lived connections that hunters use for API calls.

**Required fix:** Define a typed error interface or sentinel:
```go
type RetriableError interface {
    error
    IsRetriable() bool
}
```
Have hunters (or HTTP middleware) wrap retriable errors in this type. Fall back to `net.Error.Timeout()` as a catch-all. Remove the string-matching branch entirely. If string matching must remain for the short term, remove "temporary" and "503" from the list.

---

## Finding 6 — HIGH: Nil Result Dereference Risk at Every HuntWithRetry Call Site

**Severity:** Panic in watch path under specific error conditions

**Location:** Plan Tasks 3, 4, 5; `HuntWithRetry` return contract

**The contract:**
`HuntWithRetry` returns `(nil, err)` in two cases:
- Non-transient error: `return nil, err` (line 133)
- Exhausted attempts: `return nil, fmt.Errorf("after %d attempts: %w", ...)` (line 145)

**Task 3 (cli/scan.go) — safe as proposed:**
The error branch calls `continue`, so nil result is never dereferenced. This path is fine.

**Task 4 (api/scanner.go) — safe as proposed:**
The plan creates a `failedResult` explicitly on error, so nil is never stored. This path is fine.

**Task 5 (watch/watcher.go) — the nil guard is present but incomplete:**
The plan adds:
```go
if result == nil {
    result = &api.ScanResult{HunterResults: make(map[string]*hunters.HuntResult)}
}
```

But this guard is for the `ScanResult`, not for individual `HuntResult` entries within it. In `watcher.go`, after the plan's Task 4 change, `result.HunterResults[name]` will contain a `*hunters.HuntResult` with `Status: HunterStatusFailed` for failed hunters — so the nil guard on individual entries is handled at the Task 4 layer.

**However**, there is still a nil risk: the watcher's `diffSnapshots` function (line 77) accesses `result.OutputFiles` and `result.TotalSources`. With the plan's guard, these will be zero/nil-slice on full failure, which is safe. The gap is `result.HunterResults` iteration if `diffSnapshots` or `emitSignals` iterates over it and dereferences entries — not visible without reading those functions, but worth flagging as an audit point.

**Required action:** Read `diffSnapshots` and `emitSignals` to verify they nil-check before dereferencing `*HuntResult` entries. The plan does not do this verification.

---

## Finding 7 — MEDIUM: Scanner.Scan Context Cancellation Semantic Inconsistency After Plan

**Severity:** Watcher gets wrong error on context cancellation

**Location:** Task 5 (`watch/watcher.go:61-63`) interacting with `scanner.go:137-142`

**Current Scanner.Scan context handling:**
```go
// scanner.go:136-142
for _, name := range hunterNames {
    select {
    case <-ctx.Done():
        result.Errors = append(result.Errors, ctx.Err())
        return result, nil   // <-- returns nil error even on cancellation
    default:
    }
```

`Scanner.Scan` returns `(result, nil)` even when the context is cancelled — it puts the `ctx.Err()` into `result.Errors` instead of returning it as the function error.

**The plan's watcher fix:**
```go
if err != nil {
    if ctx.Err() != nil {
        return nil, fmt.Errorf("watch scan: %w", err)
    }
    // Other errors: log and continue
}
```

But `Scanner.Scan` never returns `(result, non-nil-err)` under any current code path — it always returns `nil` as the error. The `err != nil` branch in the watcher will never be entered. The entire `ctx.Err()` check in the watcher is dead code.

After the plan's Task 4, `Scanner.Scan` still returns `(result, nil)` — the plan does not change that function signature behavior. So the watcher's resilience fix does nothing for context cancellation: when a context is cancelled, `Scanner.Scan` returns `(result, nil)`, the watcher sees `err == nil`, falls through to snapshot/diff processing, and processes a partial result with `ctx.Err()` buried in `result.Errors` — which is incorrect behavior for a cancelled watch cycle.

**The watcher fix needs to also check `result.Errors` for context errors:**
```go
result, err := w.scanner.Scan(ctx, api.ScanOptions{Hunters: hunters})
if ctx.Err() != nil {
    return nil, fmt.Errorf("watch scan cancelled: %w", ctx.Err())
}
// err is always nil per current Scanner.Scan contract, but check anyway
if err != nil {
    fmt.Fprintf(os.Stderr, "watch scan error: %v\n", err)
}
```

---

## Finding 8 — MEDIUM: hunterNames Length Used in Summary Table May Include Zero-value Sentinel

**Severity:** Off-by-one in "N/M hunters completed" summary

**Location:** Plan Task 3, Step 3; `cli/scan.go` proposed changes

**Proposed summary:**
```go
fmt.Printf("\n%d/%d hunters completed successfully\n",
    len(hunterNames)-len(failedHunters), len(hunterNames))
```

`hunterNames` is the original list from the plan. In the actual scan loop (observed in the source), when `--hunter` is not specified, `hunterNames` is built from `cfg.EnabledHunters()`. When a hunter is not found in the registry, the loop logs a warning and `continue`s. That hunter is neither in `failedHunters` nor in the success count. The denominator `len(hunterNames)` includes not-found hunters, making the success count `len(hunterNames) - len(failedHunters)` larger than the actual number of hunters that ran successfully.

Example: 5 configured hunters, 1 not found in registry, 1 failed. The output would say "3/5 completed successfully" when in fact only 3 of 4 actually-attempted hunters completed.

**Fix:** Track `attemptedCount` (incremented after the registry lookup succeeds) and use that as the denominator.

---

## Finding 9 — LOW: TestHuntWithRetry_RespectsContextCancellation Has a Race

**Severity:** Test flakiness under load (low severity but worth noting)

**Location:** Plan Task 2, `retry_test.go:254-262`

**Proposed test:**
```go
func TestHuntWithRetry_RespectsContextCancellation(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    cancel()
    h := &fakeHunter{name: "test", failN: 10, err: &net.DNSError{IsTimeout: true}}
    _, err := HuntWithRetry(ctx, h, HunterConfig{}, RetryConfig{MaxAttempts: 3, Backoff: time.Millisecond})
    if !errors.Is(err, context.Canceled) {
        t.Errorf("expected context.Canceled, got %v", err)
    }
}
```

The test pre-cancels the context, then calls `HuntWithRetry`. `fakeHunter.Hunt` does not check `ctx.Done()` (it is a mock). Therefore `h.Hunt(ctx, cfg)` will succeed on attempt 1 (calls == 1 which is <= failN=10, returns the error). Then `isTransient` returns true, and the sleep `select` fires `ctx.Done()` immediately because context is already cancelled. `ctx.Err()` = `context.Canceled`, test passes.

But this test does _not_ test what happens when the context is cancelled mid-flight during an actual `Hunt` call — it only tests cancellation during the backoff sleep. The actual production race (Hunt blocked on network I/O, context cancelled, Hunt returns context error wrapped in net.Error, isTransient returns true, retry attempts sleep) is not covered.

**Recommendation:** Add a test where `fakeHunter.Hunt` blocks on a channel that is released only after the context is cancelled, verifying that `HuntWithRetry` terminates promptly.

---

## Finding 10 — LOW: fakeHunter in retry_test.go Does Not Implement Full Hunter Interface

**Severity:** Test compilation risk depending on Hunter interface evolution

**Location:** Plan Task 2, `retry_test.go`

The `Hunter` interface requires both `Name() string` and `Hunt(ctx, cfg)`. The proposed `fakeHunter` implements both. This is fine at the current interface definition. However, the `fakeHunter` is defined in the `hunters` package (internal test), not as a test helper exported from a `hunters/testutil` sub-package. If the interface gains a new method, all internal tests break. This is standard Go practice (internal tests do break on interface changes) and low severity, but the plan should note this is an in-package test.

---

## Summary Table

| # | Finding | Severity | Blocks Ship? |
|---|---------|----------|-------------|
| 1 | `HunterStatus` name collision with `research.HunterStatus` | Critical | Yes — namespace confusion, maintenance hazard |
| 2 | `Success()` semantic break — all hunters return false-positive success | Critical | Yes — corrupts run history DB |
| 3 | Backoff overflow at high MaxAttempts | High | No (default is 2), but exported API is a time bomb |
| 4 | Missing ctx check before Hunt call on retry iterations | High | Low probability in practice |
| 5 | `isTransient` "temporary" and "503" match too broadly | High | Causes incorrect retries |
| 6 | Nil result dereference risk — diffSnapshots/emitSignals not verified | High | Audit gap |
| 7 | Watcher ctx-cancellation check is dead code — Scanner never returns non-nil error | Medium | Resilience fix doesn't work as intended |
| 8 | Summary table denominator includes not-found hunters (off-by-one) | Medium | UX only |
| 9 | Context cancellation test doesn't cover mid-Hunt cancellation race | Low | Test gap |
| 10 | fakeHunter not in testutil package | Low | Maintenance only |

---

## Required Changes Before Implementation

### Must fix (blocks correctness):

1. **Rename `HunterStatus` in the `hunters` package** to `HuntOutcome` or `ResultCode` to avoid collision with `research.HunterStatus`.

2. **Do not change `Success()`.** Keep it as `len(r.Errors) == 0`. Add a new `DeriveStatus() HuntOutcome` method that computes the enum from existing fields, so hunters don't need to be updated.

3. **Cap backoff shift** at 30 before computing `1<<shift` in `HuntWithRetry`.

4. **Add `if ctx.Err() != nil { return nil, ctx.Err() }` at the top of the retry loop body** (before calling Hunt).

5. **Fix the watcher context cancellation guard**: check `ctx.Err()` directly rather than `err != nil`, since `Scanner.Scan` never returns a non-nil error.

### Should fix (high quality bar):

6. Replace string-based `isTransient` with a `RetriableError` interface, or at minimum remove "temporary" and "503" from the string match list.

7. Audit `diffSnapshots` and `emitSignals` for nil `*HuntResult` dereference before completing Task 5.

8. Fix the summary table denominator to count `attemptedHunters` not `len(hunterNames)`.
