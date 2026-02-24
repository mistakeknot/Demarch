# Quality Review: Pollard Hunter Resilience Plan (iv-xlpg)

**Plan file:** `docs/plans/2026-02-23-pollard-hunter-resilience.md`
**Date:** 2026-02-23
**Reviewer:** fd-quality (Flux-drive Quality & Style Reviewer)
**Scope:** Go — `internal/pollard/hunters/`, `internal/pollard/cli/`, `internal/pollard/api/`, `internal/pollard/watch/`

---

## Executive Summary

The plan is well-structured and the code it proposes is largely idiomatic Go. Three issues require attention before implementation: a semantic gap in `Success()` after the `HunterStatus` migration, a context-cancellation edge case in the retry loop, and a missing test case for the context-cancelled-before-first-attempt scenario. Everything else is sound or is a deliberate, acceptable trade-off.

---

## Finding 1 — BLOCKER: `Success()` semantics break after migration

**File:** `apps/autarch/internal/pollard/hunters/hunter.go`
**Task:** Task 1, Step 3

### Current code (before plan)
```go
func (r *HuntResult) Success() bool {
    return len(r.Errors) == 0
}
```

### Proposed replacement
```go
func (r *HuntResult) Success() bool {
    return r.Status == HunterStatusOK
}
```

### Problem

The plan makes `Success()` depend entirely on `Status`, but existing callers that create a `HuntResult` without ever setting `Status` will get `Status == 0 == HunterStatusOK` — which looks fine by backward compatibility. However, `api/scanner.go` also directly appends hunter errors into `result.Errors` (line 222: `result.Errors = append(result.Errors, huntResult.Errors...)`), and the run-completion path (lines 209-215) checks `huntResult.Success()` to decide what to pass to `db.CompleteRun`. After the migration, a hunt that returns `len(Errors) > 0` but `Status == HunterStatusOK` (because nobody set it to `HunterStatusPartial`) will be recorded in the DB as successful.

The plan does set `result.Status = hunters.HunterStatusPartial` in the CLI path (Task 3, Step 2) but only in `scan.go`, not in the `api/scanner.go` success path (Task 4 only handles the error path). The DB completion call in `api/scanner.go` (lines 209-215) continues to use `huntResult.Success()` — after the plan's changes that call will return `true` even when `Errors` is non-empty because `Status` was never set to `HunterStatusPartial` by the API path.

### Fix

Either:

a) Keep `Success()` checking `len(r.Errors) == 0` (its current semantics) and add a separate `IsOK() bool { return r.Status == HunterStatusOK }` for code that needs status-based checks, OR

b) Add a `result.Status = hunters.HunterStatusPartial` assignment to the post-hunt block in `api/scanner.go` (after the successful hunt, before recording completion):

```go
// In api/scanner.go, after "Execute the hunt" and before DB completion
if len(huntResult.Errors) > 0 {
    huntResult.Status = hunters.HunterStatusPartial
}
```

Option (b) is simpler and keeps the migration self-consistent, but it requires the plan to explicitly add this to Task 4.

---

## Finding 2 — BUG: Context cancelled before first attempt is not handled

**File:** `apps/autarch/internal/pollard/hunters/retry.go` (proposed)
**Function:** `HuntWithRetry`

### The gap

The retry loop calls `h.Hunt(ctx, cfg)` on the first iteration without checking whether `ctx` is already cancelled. If `ctx` is cancelled before the first attempt, `h.Hunt` will still be called (the hunter implementation is responsible for checking ctx internally, which not all hunters may do promptly). The test `TestHuntWithRetry_RespectsContextCancellation` pre-cancels the context before calling `HuntWithRetry` — this test will only pass reliably if the fakeHunter's `Hunt` checks the context, which the proposed `fakeHunter` does not do.

Looking at the proposed `fakeHunter`:
```go
func (f *fakeHunter) Hunt(_ context.Context, _ HunterConfig) (*HuntResult, error) {
    f.calls++
    if f.calls <= f.failN {
        return nil, f.err
    }
    return &HuntResult{...}, nil
}
```

The context is discarded (`_`). With `failN: 10` and a pre-cancelled context, the test expects `context.Canceled` to be returned — but the fakeHunter will return `f.err` (`&net.DNSError{IsTimeout: true}`) on each call, so the loop will exhaust attempts and return a wrapped `DNSError`, not `context.Canceled`.

### Fix

Add a context check at the top of the loop body, before calling `h.Hunt`:

```go
for attempt := 1; attempt <= rc.MaxAttempts; attempt++ {
    if ctx.Err() != nil {
        return nil, ctx.Err()
    }
    result, err := h.Hunt(ctx, cfg)
    ...
```

And update `fakeHunter` to check the context:

```go
func (f *fakeHunter) Hunt(ctx context.Context, _ HunterConfig) (*HuntResult, error) {
    if ctx.Err() != nil {
        return nil, ctx.Err()
    }
    f.calls++
    if f.calls <= f.failN {
        return nil, f.err
    }
    return &HuntResult{HunterName: f.name, SourcesCollected: 1}, nil
}
```

This makes the context-cancellation test deterministic and documents the expected contract for `Hunter.Hunt` implementations.

---

## Finding 3 — MINOR: `isTransient` string-matching approach is acceptable but incomplete

**File:** `apps/autarch/internal/pollard/hunters/retry.go` (proposed)

### Assessment

The plan uses `errors.As(err, &netErr)` for `net.Error` (correct typed-interface approach) and falls back to string matching for HTTP status codes. This is a reasonable pragmatic choice given that hunter errors do not currently use a typed HTTP error type.

The string matching `strings.Contains(msg, "timeout")` will incorrectly classify some non-retryable timeouts as transient — for example, a timeout caused by a misconfigured URL (permanent DNS failure) would match the same pattern as a transient network blip. However, since `net.Error` with `IsTimeout: true` is already caught by the `errors.As` check first, the string match is only a fallback for raw HTTP client errors that embed timeout text. This is acceptable.

One gap: `net.Error` with `IsTemporary: true` is explicitly designed for transient errors, but the plan never checks it separately. `errors.As(err, &netErr)` catches all `net.Error` values and returns `true`, including permanent ones like `net.DNSError{IsNotFound: true}`. A DNS "not found" is not transient.

### Recommendation

Tighten the `net.Error` check:

```go
var netErr net.Error
if errors.As(err, &netErr) {
    return netErr.Timeout() || netErr.Temporary()
}
```

This excludes permanent network errors (hostname not found, connection refused) while retaining retries for timeouts and explicitly temporary errors. Note: `Temporary()` is deprecated in Go 1.18+ but still reliable for `net.DNSError` and `net.OpError`.

The `TestIsTransient` table does not cover:
- `&net.DNSError{IsNotFound: true}` — should return `false` after the fix
- `context.DeadlineExceeded` — currently returns `false` (correct — the caller handles this separately via `select`), but worth documenting in the test

---

## Finding 4 — OBSERVATION: `HunterStatus.String()` and `fmt.Stringer` compliance

**File:** `apps/autarch/internal/pollard/hunters/hunter.go` (proposed)

The plan implements `String() string` on `HunterStatus`. This satisfies the `fmt.Stringer` interface, which means `fmt.Printf("%s", status)` and `fmt.Printf("%v", status)` will both call this method. This is correct and idiomatic.

The 5-second naming rule check: `HunterStatusOK`, `HunterStatusPartial`, `HunterStatusFailed`, `HunterStatusSkipped` — all clear. The type prefix on each constant is standard Go convention for untyped-safe iota enums when the type might appear alongside other int-based types.

One minor note: the `default: return "unknown"` branch is good defensive practice for forward compatibility (if a new constant is added but `String()` is not updated, it silently degrades rather than panicking). No change needed.

---

## Finding 5 — OBSERVATION: `fakeHunter` pointer receiver and mutation safety

**File:** `apps/autarch/internal/pollard/hunters/retry_test.go` (proposed)

The `fakeHunter` uses a pointer receiver on `Hunt` (`f *fakeHunter`) to mutate `f.calls`. The test creates `h := &fakeHunter{...}` and passes it directly. This is correct — since `fakeHunter` implements `Hunter` via a pointer receiver, passing `h` (already a pointer) satisfies the interface.

The concern about concurrency safety is not applicable here. `HuntWithRetry` is a sequential loop — it calls `h.Hunt` and waits for the result before proceeding. There is no goroutine spawning in the proposed implementation. The `fakeHunter.calls` counter is mutated only from the single goroutine running `HuntWithRetry`. No mutex is needed.

The CLAUDE.md memory note about Bubble Tea's threading model (Model.Update and View on the same goroutine) is specific to TUI components and does not apply here.

---

## Finding 6 — OBSERVATION: `hunterSummary` local type in `scan.go`

**Task:** Task 3, Step 3

The plan defines `hunterSummary` as a local type inside the `RunE` closure:

```go
type hunterSummary struct {
    name   string
    status hunters.HunterStatus
    err    error
}
```

This is acceptable Go. Local types inside function bodies are valid and keep the type close to its single use site. The concern is whether this type will be needed in multiple places later. Looking at the architecture, the summary table is CLI-only output — it will not be needed in `api/scanner.go` (which stores structured results in `HunterResults` map) or in `watch/watcher.go`. Keeping it local is the right scope.

However, placing the type declaration and `var failedHunters []hunterSummary` inside the `RunE` closure (which is already ~200 lines) will make the closure harder to read. The plan should explicitly note where in the closure body these declarations should appear — before the hunter loop is the right place, consistent with Go's "declare before use" idiom.

---

## Finding 7 — OBSERVATION: Task 5 watcher nil-result guard is defensive but correct

**Task:** Task 5, Step 1

The plan adds:
```go
if result == nil {
    result = &api.ScanResult{HunterResults: make(map[string]*hunters.HuntResult)}
}
```

After examining `api/scanner.go`'s `Scan()` method (lines 120-226): it initializes `result` at the top of the function and always returns a non-nil `result` even when errors occur. The `result == nil` guard in the watcher is therefore unreachable with the current implementation. This is fine defensive code — the guard documents the assumption and protects against future changes to `Scan()` that might return `nil, err`.

No change needed, but a comment like `// Scan initializes result, but guard against future changes` would make the intent clear.

---

## Finding 8 — MINOR: Error wrapping consistency in Task 4

**File:** `apps/autarch/internal/pollard/api/scanner.go` (proposed change)

The plan proposes wrapping the failed-hunter error in `HunterResults`:
```go
result.Errors = append(result.Errors, fmt.Errorf("hunter %s failed: %w", name, err))
```

This matches the existing pattern in `scanner.go` line 201:
```go
result.Errors = append(result.Errors, fmt.Errorf("hunter %s failed: %w", name, err))
```

The `%w` wrapping is consistent with the project's error-handling convention visible throughout the codebase (`fmt.Errorf("failed to load config: %w", err)` etc.). Good.

Note that `ErrorMsg: err.Error()` on the `failedResult` struct (the new `HuntResult`) stores a string copy of the error, not the error itself. This is intentional for the API response layer (it will be JSON-serialized) but loses the ability to `errors.Is/As` against the original error. This is an acceptable trade-off since `HuntResult.Errors []error` still holds the original.

---

## Test Coverage Assessment

| Test | Coverage | Gap |
|------|----------|-----|
| `TestHuntWithRetry_SucceedsFirstAttempt` | Normal path | None |
| `TestHuntWithRetry_RetriesTransient` | Transient retry | None |
| `TestHuntWithRetry_NoRetryOnNonTransient` | Non-transient early exit | None |
| `TestHuntWithRetry_ExhaustsAttempts` | All retries fail | None |
| `TestHuntWithRetry_RespectsContextCancellation` | Ctx cancelled | Broken — see Finding 2 |
| `TestIsTransient` | Transient detection | Missing `IsNotFound` negative case |

Missing test: `MaxAttempts: 0` should behave as `MaxAttempts: 1` (the plan clamps it). A test asserting this zero-value behavior would document the contract.

---

## Naming and Conventions Check

All new identifiers align with project vocabulary and Go conventions:

- `RetryConfig`, `DefaultRetryConfig` — clear, follows project style
- `HuntWithRetry` — verb-noun, exported, self-describing (passes 5-second rule)
- `isTransient` — unexported predicate, correct casing
- `HunterStatus`, `HunterStatusOK` etc. — type-prefixed enum, standard Go
- `hunterSummary` — lowercase local type, appropriate for its scope

No new dependencies are introduced. `net`, `errors`, `strings`, `time` are all standard library.

---

## Summary of Required Changes Before Implementation

| Priority | Finding | Action |
|----------|---------|--------|
| BLOCKER | Finding 1: `Success()` semantic gap | Add `Status = HunterStatusPartial` to API scanner's success path (Task 4), or keep `Success()` as `len(Errors)==0` |
| BUG | Finding 2: Pre-cancelled context reaches `h.Hunt` | Add `ctx.Err() != nil` guard at top of loop body; update `fakeHunter` to check context |
| MINOR | Finding 3: `net.Error` catches non-retryable DNS errors | Tighten to `netErr.Timeout() \|\| netErr.Temporary()` |
| MINOR | Finding 3: Missing test cases for `isTransient` | Add `IsNotFound: true` negative case and `context.DeadlineExceeded` documented case |
| NOTE | Finding 7: Nil guard comment | Optional — add inline comment explaining the guard |
