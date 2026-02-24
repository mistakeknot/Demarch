# Architecture Review: Pollard Hunter Resilience Plan (iv-xlpg)

**Plan file:** `/home/mk/projects/Demarch/docs/plans/2026-02-23-pollard-hunter-resilience.md`
**Reviewed:** 2026-02-23
**Reviewer:** fd-architecture

---

## Executive Summary

The plan is architecturally sound in its primary goal and mostly correct in its boundary decisions. Three issues require attention before implementation: a zero-value enum trap in `HunterStatus`, a behavioral contract break in `Success()`, and a redundant `ErrorMsg` field. One structural question about retry placement is worth considering but the plan's choice is defensible. The watcher change is the highest-value task and is correctly designed.

---

## 1. Boundaries and Coupling

### Retry in `hunters/` vs caller layer

The plan places `HuntWithRetry` in the `hunters/` package. This is the right decision.

The `hunters/` package already owns the `Hunter` interface and `HuntResult` type. Both callers (`cli/scan.go` and `api/scanner.go`) would need identical retry logic if it lived in each caller. Putting retry in `hunters/` creates one implementation tested once.

The function signature `HuntWithRetry(ctx, Hunter, HunterConfig, RetryConfig)` operates only on types already defined in the `hunters/` package. It introduces no new imports, no upward dependencies, and no coupling to `cli/` or `api/`. This is correct placement.

One concern: both callers use `hunters.DefaultRetryConfig()` directly with no way to override from configuration. If a specific hunter type (say, `agent-hunter` which spawns subprocesses) should never retry, callers have no hook to vary the config per hunter. This is acceptable for the initial implementation but is worth noting as a future seam — the `HunterConfig` struct or the registry is the natural place to carry per-hunter retry policy later.

### Dependency direction

All changes stay within `internal/pollard/`. No new cross-pillar imports. `cli/` and `api/` already import `hunters/`; adding the retry call does not change that dependency topology. `watch/` imports `api/` and continues to do so. No new couplings are introduced.

### Duplicate `CompetitorTarget` type

`api/scanner.go` already defines its own `CompetitorTarget` struct (lines 59-65) that mirrors `hunters.CompetitorTarget`. This duplication exists before the plan and is not made worse by it. It is outside scope of this plan but should be noted as existing debt.

### `failedHunters` slice locality (Task 3)

The plan introduces a `hunterSummary` local type and `failedHunters` slice in `cli/scan.go`. These are correctly scoped to the function. The plan's summary output references `len(hunterNames)` which is already in scope. This is clean.

---

## 2. Enum Design — Zero-Value Trap

**This is a must-fix.**

The plan defines:

```go
const (
    HunterStatusOK      HunterStatus = iota  // 0
    HunterStatusPartial                       // 1
    HunterStatusFailed                        // 2
    HunterStatusSkipped                       // 3
)
```

`HunterStatusOK` is assigned the zero value (0). The plan notes this is "backward compatible" because existing callers don't set `Status`, so it defaults to 0 = `HunterStatusOK`.

The backward compatibility reasoning is correct, but it creates a semantic trap: any `HuntResult` that is zero-initialized (including failure results the caller fails to populate, or test stubs that return `&HuntResult{}`) will silently report `Status == HunterStatusOK`. This is the opposite of a safe default. If code omits setting `Status`, the result reads as successful.

The safer iota ordering puts an explicit unknown/uninitialized state at zero:

```go
const (
    HunterStatusUnknown HunterStatus = iota  // 0 — zero value, not yet set
    HunterStatusOK                           // 1
    HunterStatusPartial                      // 2
    HunterStatusFailed                       // 3
    HunterStatusSkipped                      // 4
)
```

This means:
- A zero-initialized `HuntResult` has `Status == HunterStatusUnknown`, which is distinguishable from success.
- Callers that forgot to set `Status` are detectable.
- The plan's backward compatibility concern is addressed by updating all successful hunt completion paths to set `Status = HunterStatusOK`. There are exactly two: `cli/scan.go` (after the `Hunt` call succeeds) and `api/scanner.go` (after the `Hunt` call succeeds). Both are already being modified in Tasks 3 and 4.

The cost is two additional assignment lines in the success paths. The benefit is fail-safe behavior.

---

## 3. `Success()` Behavioral Contract Break

**This is a must-fix.**

The plan changes `Success()` from:

```go
func (r *HuntResult) Success() bool {
    return len(r.Errors) == 0
}
```

to:

```go
func (r *HuntResult) Success() bool {
    return r.Status == HunterStatusOK
}
```

The problem: `HunterStatusOK` is the zero value. All existing `HuntResult` values where callers did not set `Status` will return `true` from `Success()` regardless of `r.Errors`. The behavioral change looks neutral on the surface but is actually a silent divergence.

More importantly, the existing callers in `cli/scan.go` (line 237) and `api/scanner.go` (line 209) call `result.Success()` to determine the `success` boolean they pass to `db.CompleteRun`. After the change, if the caller returns a result with errors but forgets to set `Status = HunterStatusPartial`, `Success()` returns true, and the DB records a successful run. This is worse than the current behavior.

The fix depends on which enum ordering is chosen:

- If `HunterStatusOK` stays at zero: do not change `Success()`. Keep it as `len(r.Errors) == 0`. The `Status` field adds structured reporting without replacing the existing error-based success check.
- If `HunterStatusUnknown` is zero: change `Success()` as proposed, but explicitly set `Status` on all result paths (Tasks 3 and 4 already do this for failure; the success paths need `Status = HunterStatusOK` added).

The cleaner approach is to keep both signals consistent: set `Status` explicitly and keep `Success()` checking `Status`. This requires the `HunterStatusUnknown` zero-value ordering. The plan's current combination of `HunterStatusOK` at zero plus changing `Success()` to check `Status` is internally consistent only by accident — it works because the zero value happens to mean OK. But it fails to provide the invariant that an unset `Status` is distinguishable.

---

## 4. Redundant `ErrorMsg` Field

**Minor structural issue.**

The plan adds two fields to `HuntResult`:

```go
Status   HunterStatus
ErrorMsg string // Human-readable error summary (empty if OK)
```

`HuntResult.Errors` already exists as `[]error`. The new `ErrorMsg` duplicates information that can be derived from `Errors`. Task 4 populates both:

```go
failedResult := &hunters.HuntResult{
    HunterName: name,
    Status:     hunters.HunterStatusFailed,
    ErrorMsg:   err.Error(),
    Errors:     []error{err},
}
```

`err.Error()` is stored twice: once in `ErrorMsg` and once in `Errors[0]`. Callers that want a string already call `huntResult.Errors[0].Error()` (existing pattern in `api/scanner.go` line 212). Adding `ErrorMsg` as a separate field creates two sources of truth for the same data.

The simpler design: keep only `Errors []error` for machine use, and derive strings from it at display time. If a single-string summary is needed at the struct level, a method `func (r *HuntResult) ErrorSummary() string` returning `errors.Join` or the first error message is cleaner than a persisted field.

If `ErrorMsg` is kept for simplicity, at minimum it should not be populated separately — it should be derived on access via a method, not stored alongside `Errors`.

---

## 5. `isTransient` String-Matching Approach

**Low severity, worth noting.**

The `isTransient` function in `retry.go` uses substring matching on error strings for HTTP status codes:

```go
for _, s := range []string{"rate limit", "429", "503", "timeout", "temporary"} {
    if strings.Contains(msg, s) {
        return true
    }
}
```

String-matching error messages is fragile: it depends on how downstream hunters format their errors. The substring `"429"` would match any error containing the digit sequence 429 (e.g., a file path, a port number, a metric value).

The `net.Error` interface check above it is the correct pattern. The string fallback is pragmatic given that hunters likely return wrapped HTTP errors as plain strings. The plan's approach is acceptable as a first pass, but the comment should note it is a heuristic, not a contract.

The `"timeout"` substring also matches `context.DeadlineExceeded` wrappings in some Go HTTP clients. Whether that is desirable (context timeouts should retry) or not (context cancellation should not retry) depends on usage. The plan correctly handles `ctx.Done()` separately in the retry loop, so a context deadline error will be caught before the transient check. This is fine.

---

## 6. Watcher Change (Task 5)

The change to `RunOnce` is the most impactful part of the plan and is correctly designed.

The current behavior returns the error immediately, aborting the watch cycle and losing any partial results `Scanner.Scan` had accumulated. The plan separates two distinct cases:

1. `ctx.Err() != nil` — truly fatal, propagate.
2. Other errors — log to stderr, continue with partial results.

This matches the existing `Run()` behavior (lines 104-106 in `watcher.go`), which already swallows `RunOnce` errors by logging them to stderr. The change makes `RunOnce` itself resilient so `Run()` receives a valid result even when some hunters fail.

One issue in Task 5's proposed code:

```go
if result == nil {
    result = &api.ScanResult{HunterResults: make(map[string]*hunters.HuntResult)}
}
```

Looking at `api/scanner.go` `Scan()` (lines 120-226), `Scan` always initializes `result` before entering the loop and returns it unconditionally (`return result, nil`). The only way `result` is `nil` after calling `Scan` is if `Scan` itself panics or returns `nil, err`. Given the current implementation, `Scan` never returns `nil` for the result pointer. The nil guard is therefore dead code.

It is harmless defensively, but it misleads readers into thinking `Scan` can return `(nil, err)`. If the nil guard is kept for defensive programming, a comment should explain the invariant.

---

## 7. YAGNI Check

**`HunterStatusSkipped`** is defined in the enum but no task in the plan sets it. The plan describes it as "not in registry" but the CLI already handles that with `fmt.Printf("Warning: hunter %q not found in registry, skipping\n", name)` and `continue`. The skip path does not produce a `HuntResult` at all, so `HunterStatusSkipped` has no concrete consumer in this plan.

This is a speculative value. It should either be removed from the initial implementation (add it when there is a real consumer) or added only if Task 3 is extended to create a `HuntResult` for skipped hunters and include them in the summary table. Currently, skipped hunters are not counted in `len(hunterNames)` used in the summary denominator, so the summary percentage would be wrong if skipped hunters were mixed with failed ones.

**`RetryConfig` as a struct** is appropriate despite having only two fields — `MaxAttempts` and `Backoff`. The function signature `HuntWithRetry(ctx, Hunter, HunterConfig, RetryConfig)` is cleaner than a variadic options approach for two explicit fields. No concern here.

**`DefaultRetryConfig()`** returning 2 attempts with 1s backoff means scans that hit transient failures will add up to 1 second of latency per affected hunter. For a 12-hunter scan, worst case is 12 extra seconds. This is acceptable but worth documenting in the function's godoc so callers understand the latency budget implication.

---

## 8. Pattern Alignment

The plan follows existing patterns in the codebase:

- Uses `fmt.Errorf("...: %w", err)` for wrapping (consistent with the rest of the file).
- `fakeHunter` in tests implements the `Hunter` interface — correct test isolation.
- Tests use table-driven format for `TestIsTransient` — consistent with Go idiom.
- The `hunterSummary` local type in `cli/scan.go` follows the pattern of small anonymous structs used elsewhere in the codebase for iteration state.

The plan does not introduce any new external dependencies. `net`, `errors`, `strings`, `time`, `context`, `fmt` are all already in use in `hunters/`.

---

## Summary: Required Changes Before Implementation

### Must-fix

1. **Enum zero-value ordering** (Task 1): Move `HunterStatusOK` off zero. Use `HunterStatusUnknown = iota` as the zero value. Update Tasks 3 and 4 to explicitly set `Status = HunterStatusOK` on successful hunt paths.

2. **`Success()` contract** (Task 1): Either (a) keep `Success()` as `len(r.Errors) == 0` and treat `Status` as additive reporting, or (b) change to `Status == HunterStatusOK` only after ensuring all success paths explicitly set `Status`. Do not combine the zero-value-as-OK assumption with the Status-based `Success()` check — it works by coincidence, not design.

### Should-fix

3. **Remove `ErrorMsg` field** (Task 1 and 4): The field duplicates `Errors[0].Error()`. Replace with a `ErrorSummary() string` method or simply derive strings from `Errors` at display time.

4. **Remove `HunterStatusSkipped`** (Task 1): No consumer exists in this plan. Add it when a concrete use case requires it (e.g., summary table includes skipped hunters).

### Low priority

5. **Nil guard comment** (Task 5): Document why the `result == nil` guard exists, or remove it if it is truly dead given `Scan`'s invariants.

6. **Per-hunter retry config** (Task 2): Note in `DefaultRetryConfig` godoc that per-hunter retry overrides are a future extension point, and that the function adds up to 1s latency per hunter on transient failures.
