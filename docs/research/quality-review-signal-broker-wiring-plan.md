# Quality Review: Signal Broker Wiring Plan
**Plan file:** `/root/projects/Interverse/hub/autarch/docs/plans/2026-02-20-signal-broker-wiring.md`
**Date:** 2026-02-20
**Reviewer:** Flux-drive Quality & Style Reviewer

---

## Summary

The plan is well-structured: it follows a strict red-green-commit TDD loop across eight tasks, the architecture rationale is sound (push over poll), and the Bubble Tea message pattern used is idiomatic for this codebase. Nine findings were identified. Two are correctness blockers that must be fixed before implementation begins; the remainder are design, naming, and test hygiene concerns.

---

## Findings

### 1. BLOCKER — Subscription leak: Init() does not guard against a pre-existing subscription

**Location:** Task 5, `SignalsView.Init()` implementation; Task 6, `SignalsOverlay.Toggle()` subscribe block.

**Problem:** The plan's `Init()` code subscribes whenever `broker != nil`:

```go
if v.broker != nil {
    v.brokerSub = v.broker.Subscribe(nil)
    cmds = append(cmds, v.waitBrokerSignal())
}
```

`Init()` is called by Bubble Tea at model initialization but can also be called again if the parent rebuilds the model. If `Init()` is called while `v.brokerSub` is already set from a previous call, the old subscription is overwritten without being closed. The goroutine spawned by `waitBrokerSignal()` from the first call is now blocked on a channel that is never closed and never drained — a goroutine leak. The broker still holds a reference to the old subscriber, so signals will be delivered into a buffered channel that is never read (eventually causing drop counter inflation).

The same pattern appears in `SignalsOverlay.Toggle()` in Task 6, which does include a `brokerSub == nil` guard, so that instance is correctly written. The Task 5 path does not include the guard.

**Fix:** Add the nil guard in `Init()`:

```go
if v.broker != nil && v.brokerSub == nil {
    v.brokerDone = make(chan struct{})
    v.brokerSub = v.broker.Subscribe(nil)
    cmds = append(cmds, v.waitBrokerSignal())
}
```

And in `Blur()`, close `brokerDone` before closing `brokerSub` so the parked goroutine exits cleanly before the channel is closed:

```go
func (v *SignalsView) Blur() {
    if v.brokerDone != nil {
        close(v.brokerDone)
        v.brokerDone = nil
    }
    if v.brokerSub != nil {
        v.brokerSub.Close()
        v.brokerSub = nil
    }
}
```

In `waitBrokerSignal`, select on both the signal channel and the done channel:

```go
func (v *SignalsView) waitBrokerSignal() tea.Cmd {
    if v.brokerSub == nil {
        return nil
    }
    sub := v.brokerSub
    done := v.brokerDone
    return func() tea.Msg {
        select {
        case sig, ok := <-sub.Chan():
            if !ok {
                return nil
            }
            return brokerSignalMsg{signal: sig}
        case <-done:
            return nil
        }
    }
}
```

This prevents the goroutine from outliving the subscription lifecycle and eliminates the channel-close race.

---

### 2. BLOCKER — json.Marshal error silently discarded before store insert (Task 4)

**Location:** Task 4, `handleIntermuteEvent` extension block.

**Problem:** The plan writes:

```go
payload, _ := json.Marshal(sig)
```

The `_` discard means a marshal failure produces a `nil` payload. The subsequent `store.Insert` call will write a row with null payload. When `loadData()` reads that row back, the `json.Unmarshal(evt.Payload, &sig)` call will fail, falling through to the minimal fallback signal reconstruction — which silently loses all signal data. The store write failure is logged at `slog.Debug`, but the marshal failure (the earlier and more actionable error) is not logged at all.

`json.Marshal` on the current `signals.Signal` struct (only primitive fields and `time.Time`) will not fail in practice today, but the discard pattern is inconsistent with the project's error handling discipline and will be a debugging trap if the struct ever gains a non-serialisable field.

**Fix:**

```go
payload, err := json.Marshal(sig)
if err != nil {
    slog.Debug("failed to marshal signal for persistence",
        "signal_id", sig.ID, "error", err)
} else {
    storeEvt := &events.Event{
        EventType:  events.EventSignalRaised,
        EntityType: events.EntitySignal,
        EntityID:   sig.ID,
        SourceTool: events.SourceTool(sig.Source),
        Payload:    payload,
        CreatedAt:  sig.CreatedAt,
    }
    if err := a.eventsStore.Insert(storeEvt); err != nil {
        slog.Debug("failed to persist signal to events store", "error", err)
    }
}
```

---

### 3. Naming — `intermuteEventToSignal` takes `aggregator.Event`, not `intermute.Event`

**Location:** `signal_convert.go`, the conversion function.

**Problem:** The function name `intermuteEventToSignal` implies it accepts a `pkg/intermute.Event` as input. It does not. The `Event` type in `package aggregator` is the local aggregator event, already converted from `intermute.Event` at lines 249-255 of `aggregator.go`. The name causes a reader to expect a different function signature than is actually present.

Within the aggregator package the prefix `intermute` on a function name should be reserved for functions that directly handle `pkg/intermute` types (of which there are none currently but several in the pipeline, for example `handleIntermuteEvent`).

**Fix:** Rename to `eventToSignal`. It is unexported, its input type is unambiguous from the signature, and the shorter name passes the 5-second recognition test.

---

### 4. Test design — Integration tests mixed into unit-level `signal_convert_test.go`

**Location:** Tasks 3 and 4 append to `signal_convert_test.go`.

**Problem:** `signal_convert_test.go` is created in Task 2 to test the pure, package-level function `intermuteEventToSignal`. Tasks 3 and 4 add `TestHandleIntermuteEventPublishesToBroker`, `TestHandleIntermuteEventSkipsUnmapped`, and `TestPublishedSignalWrittenToStore` to the same file. These are integration-level tests that instantiate an `Aggregator`, not tests of the conversion helper.

The existing test file split in this package is intentional: `aggregator_websocket_test.go` for WebSocket behavior, `aggregator_actions_test.go` for action behavior. Mixing aggregator behavior tests into a file named for the conversion function violates that convention and makes the test suite harder to navigate.

**Fix:** Create `aggregator_broker_test.go` for all tests that instantiate `Aggregator` and exercise broker-related behavior. Keep `signal_convert_test.go` containing only `TestConvertIntermuteEvent_*` tests for the pure function.

---

### 5. Logic — Prefix match over unsorted map is non-deterministic

**Location:** `signal_convert.go`, the prefix-match fallback loop.

**Problem:** The plan implements a prefix-match loop over `eventSignalMapping`:

```go
for prefix, st := range eventSignalMapping {
    if strings.HasPrefix(evt.Type, prefix) {
        sigType = st
        found = true
        break
    }
}
```

Map iteration in Go is randomized. Today there is only one entry per prefix family (`"task.blocked"`, `"run.failed"`, `"run.waiting"`, `"spec.revised"`) so there is no collision. But if a second `"task."` entry is added — for example `"task.failed"` — then an event type like `"task.failed.timeout"` may match either `"task.blocked"` or `"task.failed"` depending on iteration order. This is a latent correctness bug.

Additionally, the exact-match check at the top of the function already handles the listed types correctly. The prefix loop is only needed for sub-types not in the map (e.g., `"task.blocked.timeout"`). There are currently no known sub-types in the Intermute event namespace based on the subscribed event list in `ConnectWebSocket`. The prefix loop is speculative complexity.

**Fix (minimal):** Remove the prefix-match loop and use exact match only until a concrete sub-type requirement is identified. Document the intent:

```go
// intermuteEventToSignal converts an aggregator Event to a signals.Signal.
// Only events with an exact match in eventSignalMapping are converted.
// Unmapped event types return false.
func eventToSignal(evt Event) (signals.Signal, bool) {
    sigType, found := eventSignalMapping[evt.Type]
    if !found {
        return signals.Signal{}, false
    }
    // ... rest of conversion
}
```

If prefix matching is genuinely needed in the future, use a sorted slice of prefixes (longest first) rather than a map to ensure determinism.

---

### 6. Test coverage gap — Double Init() / subscription leak not tested

**Location:** Task 5 test plan, `signals_broker_test.go`.

**Problem:** The plan tests nil-broker fallback and single happy-path broker delivery. It does not test the case where `Init()` is called twice (or `Focus()` is called after `Blur()` while a broker is set). Without this test, the subscription-leak bug identified in Finding 1 would not be caught by the test suite.

**Fix:** Add a test:

```go
func TestSignalsView_InitTwiceNoLeak(t *testing.T) {
    broker := signals.NewBroker()
    v := NewSignalsView(nil)
    v.SetBroker(broker)

    // First Init
    v.Init()
    // Simulate blur (cleanup)
    v.Blur()

    // Second Init should not create a second subscription
    v.Init()

    // Publish one signal
    broker.Publish(signals.Signal{ID: "LEAK-001", Type: signals.SignalTaskBlocked})

    // Exactly one message should arrive
    v2, _ := v.Update(brokerSignalMsg{signal: signals.Signal{ID: "LEAK-001", Type: signals.SignalTaskBlocked}})
    sv := v2.(*SignalsView)
    if len(sv.signals) != 1 {
        t.Fatalf("expected 1 signal, got %d (possible duplicate subscription)", len(sv.signals))
    }
}
```

---

### 7. Design — Two structurally identical broker message types across packages

**Location:** Task 5 (`brokerSignalMsg` in `views`) and Task 6 (`brokerOverlaySignalMsg` in `tui`).

**Problem:** Both types are:

```go
type brokerSignalMsg struct {
    signal signals.Signal
}
```

They differ only in name. The duplication exists because Go type switches dispatch on concrete type, so a shared type would require a common import. The `pkg/signals` package is already imported by both `views` and `tui`, making it the natural home for a shared message type.

**Preferred fix:** Add to `pkg/signals`:

```go
// BrokerMsg wraps a Signal for Bubble Tea command delivery.
// Use as a tea.Msg to deliver pushed signals to TUI components.
type BrokerMsg struct {
    Signal Signal
}
```

Both `views` and `tui` packages handle `signals.BrokerMsg` in their Update switches. This eliminates the redundant types without creating import cycles, aligns with how `pkg/events.Subscription` is already shared, and makes it easier to add future broker consumers (e.g., a status bar indicator) without inventing yet another identical type.

This is not a blocker — the duplicated private types work correctly — but it simplifies the conceptual surface.

---

### 8. Task 7 is underspecified and defers discovery to implementation time

**Location:** Task 7, "Wire Broker Through App Startup".

**Problem:** Task 7 presents two options (A and B) without committing to either, and includes notes like "Check: Is SignalsView currently a tab in the unified TUI?" and "Check `internal/bigend/tui/` to see if it already has a signals component." These are pre-implementation discoveries deferred to the implementing agent, creating ambiguity mid-task.

The plan should specify the answer before implementation. Reading `cmd/autarch/main.go` and `internal/tui/unified_app.go` takes seconds and resolves the question definitively.

**Recommendation:** Add a pre-Task 7 discovery step: read `cmd/autarch/main.go:229-238` and `internal/tui/unified_app.go`, document findings, commit to one option (A or B), and strike the other. The implementing agent should not discover architecture mid-implementation.

---

### 9. Minor — `signal.raised` passthrough mapping produces an empty `SignalType`

**Location:** `signal_convert.go`, `eventSignalMapping`:

```go
"signal.raised": "", // passthrough — use event metadata
```

**Problem:** The function then conditionally handles the empty string:

```go
if sigType == "" {
    sig.Type = signals.SignalType(evt.Type)
}
```

This produces a `Signal` whose type is the raw string `"signal.raised"` — not any of the defined `signals.SignalType` constants. If any subscriber filters on a known `SignalType`, this passthrough signal will be routed to no-filter subscribers only. That may be the intent, but it is undocumented.

More practically: a `Signal` reaching the events store with `type = "signal.raised"` will be loaded back and passed to `filteredSignals()` in `SignalsView`, which compares `string(sig.Type)` against `signalTypeFilters`. The type `"signal.raised"` is not in that filter list, so it will only appear under the "all" filter and never be accessible via type filtering. This is a subtle UX gap.

**Fix:** Either define `SignalReraised SignalType = "signal_reraised"` in `pkg/signals/signal.go` and use it for passthrough, or document explicitly that signal.raised events are stored with a dynamic type and cannot be type-filtered. If the passthrough case is not yet needed (no Intermute `signal.raised` events are being subscribed to in `ConnectWebSocket`), remove the entry from the map entirely.

---

## Summary Table

| # | Severity | Area | Issue |
|---|----------|------|-------|
| 1 | Blocker | Concurrency | Init() can create duplicate subscriptions; goroutine/channel leak on re-focus |
| 2 | Blocker | Error handling | json.Marshal error silently discarded before store insert |
| 3 | Naming | Identifier | `intermuteEventToSignal` takes `aggregator.Event`, not `intermute.Event` — rename to `eventToSignal` |
| 4 | Test design | File layout | Aggregator integration tests mixed into `signal_convert_test.go`; should be `aggregator_broker_test.go` |
| 5 | Correctness | Logic | Prefix match over unsorted map is non-deterministic; will collide if mapping grows |
| 6 | Test gap | Coverage | No test for Init() called twice (double subscription / leak scenario) |
| 7 | Design | Type reuse | `brokerSignalMsg` and `brokerOverlaySignalMsg` are identical; `signals.BrokerMsg` would be shared |
| 8 | Plan quality | Completeness | Task 7 defers key discovery to implementation time; commit to one option upfront |
| 9 | Minor | Semantics | `signal.raised` passthrough produces a non-constant SignalType invisible to type filters |

---

## Positive Observations

- The TDD loop is correctly structured throughout: failing test first, minimal implementation, passing test, commit. Each task is a single atomic unit of work.
- `brokerSignalMsg` as an unexported type is the correct Bubble Tea pattern — it scopes message routing to the view package and prevents external packages from accidentally injecting broker messages.
- The nil-broker fallback (SQLite polling continues unchanged) is tested in both Task 5 and Task 6. This is important: broker delivery must degrade gracefully when no broker is configured.
- `slog.Debug` for store write failures is the appropriate severity for a non-fatal persistence failure on a push path. The plan is consistent with existing usage in `aggregator.go`.
- `Subscription.Close()` in `pkg/signals/broker.go` is nil-safe (checks `s == nil || s.broker == nil || s.sub == nil`), so calling it on a nil subscription from `Blur()` will not panic — a nice defensive property the plan implicitly relies on.
- The `time.After(2 * time.Second)` timeout pattern in channel-receive tests matches the project's existing convention in `pkg/signals/broker_test.go:recvSignal`.
- The end-to-end integration test in Task 8 tests the full path (Intermute event to aggregator to broker to subscriber), which provides higher confidence than the per-task unit tests alone.
- The `SourceTool` cast `events.SourceTool(sig.Source)` in the dual-write block is correct — `SourceTool` is a `contract.SourceTool` alias, so a string cast is safe here.
