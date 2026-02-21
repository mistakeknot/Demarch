# Architecture Review: Signal Broker Wiring Plan
**Plan file:** `/root/projects/Interverse/hub/autarch/docs/plans/2026-02-20-signal-broker-wiring.md`
**Review date:** 2026-02-20
**Reviewer:** Flux-drive Architecture & Design Reviewer

---

## Codebase Context

This review is grounded in the actual autarch source. Key files read:

- `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go` — 948 lines; `Aggregator` struct, `handleIntermuteEvent`, `dispatchEvent`
- `/root/projects/Interverse/hub/autarch/pkg/signals/broker.go` — `Broker`, `Subscription`, `Subscribe`, `Publish`, `ServeWS`
- `/root/projects/Interverse/hub/autarch/pkg/signals/signal.go` — `Signal`, `SignalType`, `Severity` types
- `/root/projects/Interverse/hub/autarch/pkg/events/types.go` — `EventType`, `EntityType`, `EntitySignal`, `EventSignalRaised`
- `/root/projects/Interverse/hub/autarch/internal/tui/views/signals.go` — `SignalsView`, existing Intermute wiring, `loadData`
- `/root/projects/Interverse/hub/autarch/internal/tui/signals_overlay.go` — `SignalsOverlay`, `Toggle`, `loadData`
- `/root/projects/Interverse/hub/autarch/internal/tui/unified_app.go` (grep) — `signalsOverlay *SignalsOverlay` field, `NewSignalsOverlay()` constructor
- `/root/projects/Interverse/hub/autarch/cmd/autarch/main.go` (grep) — `runBigendTUI`, `bigendTui.New(agg, ...)`, `NewUnifiedApp`

---

## Executive Summary

The plan is directionally correct. The boundary chosen (broker lives inside `Aggregator`; TUI components subscribe) is the right separation. Tasks 1 through 4 covering the aggregator side are clean and low risk. Three structural issues affect Tasks 4 through 7 and need resolution before implementation: (1) the unified TUI path in Task 7 creates a broker that no one publishes to, (2) the `SetEventsStore` setter pattern breaks `Aggregator`'s established construction discipline and opens a race window, and (3) the `intermuteEventToSignal` mapping table uses randomized map iteration for prefix matching, which is non-deterministic. Additionally, the `signal.raised` passthrough produces a zero `SignalType` that no subscriber can filter for, and `inferSeverity` is a string-heuristic that will diverge from intent as new event types are added. The remainder of the plan is implementable as written.

---

## 1. Boundaries and Coupling

### 1.1 Broker ownership is correct

The aggregator already owns the Intermute WebSocket lifecycle (`ConnectWebSocket`, `DisconnectWebSocket`, `handleIntermuteEvent`). Embedding `*signals.Broker` as a peer field alongside `intermuteClient` follows the same ownership model. There is no layer violation: `pkg/signals` is a shared package (`pkg/`), and `internal/bigend/aggregator` depending on it is the expected direction. The `Broker()` getter returning the raw `*signals.Broker` pointer is also correct — callers subscribe through the broker's own `Subscribe` API, which is stable and intentionally public.

### 1.2 Must fix — unified TUI path creates a broker that no one publishes to

Task 7 Option A creates `signalBroker := signals.NewBroker()` in `main.go` and passes it to the overlay via `app.SetSignalBroker(signalBroker)`. That broker never receives any events because:

- The unified TUI path connects to Intermute via `autarch.Client` (HTTP), not via the `Aggregator`.
- The `Aggregator`'s `handleIntermuteEvent` — where the plan inserts `broker.Publish(sig)` in Task 3 — is never called in this path.
- The standalone broker created in Option A is an inert object with no publisher.

This means the overlay broker subscription would sit permanently empty in the primary user-facing path, while SQLite polling would silently continue. The broker injection provides the appearance of push delivery while delivering nothing.

The AGENTS.md confirms: "4 dashboard tabs: Bigend(0), Gurgeh(1), Coldwine(2), Pollard(3) — Signals is an overlay (`/sig`), not a tab." The unified TUI creates `NewSignalsOverlay()` directly in `NewUnifiedApp()` (confirmed by grep). `SignalsView` is not a dashboard tab in the unified path and is not passed through the factory.

Smallest viable fix: in the unified TUI startup path, do not create or inject a broker at all. Let the nil-broker fallback preserve existing SQLite polling behavior. Reserve broker injection for paths that own a live `Aggregator` — i.e., the deprecated standalone Bigend TUI path (`runBigendTUI`), where `agg.Broker()` can be passed directly to the TUI model.

If the goal is to deliver real-time signals to the overlay in the unified TUI, that requires either routing events from `autarch.Client` through a local broker (a separate design, not in scope), or accepting that the unified TUI path continues polling.

### 1.3 Must fix — `SetEventsStore` breaks construction consistency and opens a race window

Every dependency in `Aggregator` is injected at construction time via `New()`. The plan introduces `SetEventsStore(*events.Store)` as a post-construction setter. This breaks the pattern established by all seven existing fields (`scanner`, `tmuxClient`, `stateDetector`, `intermuteClient`, `mcpManager`, `resolver`, `cfg`).

Practical consequence: `handleIntermuteEvent` calls `broker.Publish(sig)` and immediately checks `a.eventsStore != nil` in the same synchronous path. `ConnectWebSocket` starts the event listener; if `SetEventsStore` is called after `ConnectWebSocket`, there is a window where events arrive and are published to the broker but not persisted to the store. The store write is a secondary concern here, but the setter anti-pattern is worth fixing regardless.

Smallest viable fix: accept `*events.Store` as an optional parameter to `New()`. Passing `nil` preserves existing behavior (no dual-write). This eliminates the construction inconsistency and the race window.

```go
func New(scanner *discovery.Scanner, cfg *config.Config, store *events.Store) *Aggregator {
    // ...
    return &Aggregator{
        // existing fields...
        eventsStore: store, // nil = no dual-write
    }
}
```

Call sites that do not need dual-write pass `nil`. Call sites that do pass an opened store. This matches how every other optional dependency in the codebase is handled.

### 1.4 Observe — `SignalsView` has three delivery mechanisms after Task 5

`views/signals.go` currently calls `connectIntermute()`, which creates its own `intermute.Client`, connects it, and routes all events through `intermuteEvents` channel → `waitIntermuteEvent()` → `intermuteEventMsg` → full `loadData()` poll. After Task 5, `SignalsView` will have:

1. Poll SQLite on `Init` and `Focus` (initial load)
2. Broker subscription for live push of individual signals
3. Its own live Intermute WebSocket connection that triggers full SQLite reload on any event

The broker push (Task 5) adds a `signals.Signal` directly to `v.signals`. The Intermute path reloads everything from SQLite, which may or may not include the same signal (depending on Task 4's dual-write). The result is a potential duplicate: the broker delivers a signal, then the Intermute reload re-fetches it from SQLite and appends it to `v.signals` again.

This is not a must-fix for correctness — the existing code has this redundancy already (polling + live Intermute) — but it creates the observable behavior of a signal appearing twice in the list. If the broker path is reliable, the Intermute connection in `SignalsView` becomes unnecessary: the aggregator's `handleIntermuteEvent` already processes Intermute events, drives the broker, and (via Task 4) writes to the store. `SignalsView` duplicating that connection is redundant. The path to clean removal of `connectIntermute()` from `SignalsView` opens once the broker is proven reliable.

---

## 2. Pattern Analysis

### 2.1 Must fix — `intermuteEventToSignal` prefix matching is order-dependent

The implementation in Task 2 uses `map[string]signals.SignalType` for both the mapping table and the prefix fallback loop:

```go
var eventSignalMapping = map[string]signals.SignalType{
    "task.blocked":  signals.SignalTaskBlocked,
    "run.failed":    signals.SignalExecutionDrift,
    "run.waiting":   signals.SignalExecutionDrift,
    "spec.revised":  signals.SignalSpecHealthLow,
    "signal.raised": "", // passthrough
}

for prefix, st := range eventSignalMapping {
    if strings.HasPrefix(evt.Type, prefix) {
        ...
    }
}
```

Map iteration order in Go is randomized per the language spec. If two entries could both be prefixes of the same event type (e.g., a future `"task.blocked.external"` event would match both `"task.blocked"` and a hypothetical `"task."` entry), the result is non-deterministic. In the current table this does not cause a bug because all keys are exact strings, but treating exact-match keys as prefix patterns in a range loop is misleading and fragile.

The deeper issue: an event type `"task.blocked.external"` would fail the exact-match check, then enter the prefix loop where it would find `"task.blocked"` — but only if the loop happens to iterate that entry before any other entry that is also a prefix. This is a latent ordering bug.

Smallest fix: use a sorted slice of prefix patterns for the prefix-match step instead of ranging over a map:

```go
var eventPrefixMapping = []struct {
    prefix string
    sigType signals.SignalType
}{
    {"task.blocked", signals.SignalTaskBlocked},
    {"run.failed",   signals.SignalExecutionDrift},
    // ...
}
```

Or document explicitly that all keys in `eventSignalMapping` are complete event type strings (not patterns) and remove the prefix-loop entirely, returning false for any unrecognized event subtype. This is the simpler approach given the current mapping covers only five exact types.

### 2.2 Must fix — `signal.raised` passthrough produces an undefined `SignalType`

The mapping for `"signal.raised"` is the empty string `""`, and the implementation handles this with:

```go
if sigType == "" {
    sig.Type = signals.SignalType(evt.Type)
}
```

This publishes a signal whose `Type` is the string `"signal.raised"`. Looking at the defined constants in `pkg/signals/signal.go`:

```go
const (
    SignalCompetitorShipped    SignalType = "competitor_shipped"
    SignalResearchInvalidation SignalType = "research_invalidation"
    SignalAssumptionDecayed    SignalType = "assumption_decayed"
    SignalHypothesisStale      SignalType = "hypothesis_stale"
    SignalSpecHealthLow        SignalType = "spec_health_low"
    SignalExecutionDrift       SignalType = "execution_drift"
    SignalVisionDrift          SignalType = "vision_drift"
    SignalTaskBlocked          SignalType = "task_blocked"
)
```

`"signal.raised"` is not a defined constant. Subscribers filtering by `[]SignalType{signals.SignalTaskBlocked}` will not receive it. Subscribers with no filter will receive a signal with a type that no render code in `signals_overlay.go` or `views/signals.go` can display meaningfully (neither file has a case for `"signal.raised"` — they use the `sig.Type` value as a display string but no categorization logic handles it). The `signalTypeFilters` array in `views/signals.go` also does not include this type, so it would fall into the "all" bucket only.

If Intermute `signal.raised` events carry a nested signal type in `evt.Data`, extract it. If they carry a pre-formed `signals.Signal` in their payload, deserialize it rather than constructing one. If neither, map `"signal.raised"` to the closest defined type (`SignalExecutionDrift` is the most generic) and remove the passthrough special case.

### 2.3 `inferSeverity` is a string-contains heuristic

```go
func inferSeverity(eventType string) signals.Severity {
    if strings.Contains(eventType, "failed") || strings.Contains(eventType, "blocked") {
        return signals.SeverityWarning
    }
    return signals.SeverityInfo
}
```

This will misclassify any future event type that contains "blocked" but represents resolution (e.g., `"task.unblocked"` also contains "blocked"). Severity should be a property of the signal type, not inferred from the event type string.

Smallest fix: add a `severity signals.Severity` field to each mapping entry:

```go
var eventSignalMapping = []struct {
    eventType string
    sigType   signals.SignalType
    severity  signals.Severity
}{
    {"task.blocked", signals.SignalTaskBlocked,   signals.SeverityWarning},
    {"run.failed",   signals.SignalExecutionDrift, signals.SeverityWarning},
    {"run.waiting",  signals.SignalExecutionDrift, signals.SeverityInfo},
    {"spec.revised", signals.SignalSpecHealthLow,  signals.SeverityInfo},
}
```

This eliminates `inferSeverity` entirely and makes each mapping's intent explicit.

### 2.4 `clamp` / `clampOverlay` — existing duplication, plan does not worsen it

`internal/tui/views/signals.go` defines `clamp()` and `internal/tui/signals_overlay.go` defines `clampOverlay()`. These are functionally identical. The plan references both correctly within their respective files. No new duplication is introduced. The pre-existing duplication is acceptable given the package boundary, but is noted so any future refactor knows to consolidate into one shared unexported function in `internal/tui/`.

---

## 3. Simplicity and YAGNI

### 3.1 Task 4 (dual-write) may be premature

The existing `SignalsView.loadData()` already reads `EventSignalRaised` records from the events store and reconstructs `signals.Signal` from their JSON payload. The dual-write in Task 4 writes the broker-published signal back to the store so this polling path continues to work.

This only matters for the SQLite polling fallback. If the broker is working correctly, the polling path is not needed for live delivery. The dual-write adds a JSON marshal plus SQLite write on every signal for the benefit of a fallback path that the broker makes unnecessary.

The existing Pollard, Gurgeh, and Coldwine tool emitters already write to the events store independently. The Intermute-sourced signals that `handleIntermuteEvent` handles may not need to be independently persisted if the Intermute server already records them on its side. There is no concrete case in the plan of a user scenario where the dual-write matters in ways the existing emitters do not already cover.

This is not a must-fix — the dual-write is not architecturally harmful and the code is clean — but it adds code to `handleIntermuteEvent` that serves a speculative fallback rather than the stated goal of push delivery.

### 3.2 Task 7 dead code — `SignalsView` factory wiring is unused

The Task 7 commentary raises: "Check: Is SignalsView currently a tab in the unified TUI? If not, only the overlay needs wiring."

This is now answered by the actual codebase. `SignalsView` is confirmed not a dashboard tab (AGENTS.md: "4 dashboard tabs: Bigend(0), Gurgeh(1), Coldwine(2), Pollard(3) — Signals is an overlay"). The factory modification block in Task 7 creates an `sv` variable via `views.NewSignalsView(c)` that is never added to the returned `[]tui.View` slice. This is dead code that will not compile (Go will reject an unused variable assignment if `sv` is assigned but not used) and should be removed entirely.

Active work in Task 7 is only: add `SetSignalBroker` on `UnifiedApp`, which passes the broker to `signalsOverlay`. Remove the factory snippet.

### 3.3 Task 3 test has a 2-second timeout for synchronous behavior

```go
case <-time.After(2 * time.Second):
    t.Fatal("timed out waiting for signal from broker")
```

`handleIntermuteEvent` is synchronous: it calls `broker.Publish(sig)` which writes to a buffered channel (`make(chan Signal, 64)`). The signal is available in `sub.Chan()` immediately after `handleIntermuteEvent` returns. A 2-second timeout is unnecessary — 100ms (matching the "no signal" assertion below it) is sufficient and avoids test suite slowdown when the negative case is reached first. Use the same timeout for both assertions.

### 3.4 Task 5 `Blur()` is the wrong lifecycle for subscription cleanup

The plan adds `brokerSub.Close()` in `Blur()` of `SignalsView`. In the Autarch TUI, `Blur()` is called when a view loses focus — not when it is destroyed. A user switching from the Signals tab to the Bigend tab would call `Blur()`, closing the subscription. On switching back, `Focus()` is called (which currently only calls `loadData()`, not `Init()`). The subscription would not be re-created unless `Init()` is explicitly called again.

The correct place for subscription cleanup is either: (a) a `Close()` or `Destroy()` lifecycle method if one exists, or (b) tracking the subscription in `Init()` and not closing it in `Blur()`. If the intent is to pause push delivery when the view is not focused, close and re-subscribe in `Focus()` rather than `Blur()`. The current plan only handles the close half.

Check whether the `tui.View` interface in this codebase defines a teardown method. If not, keep the subscription alive across focus changes and only close it if the view is explicitly unmounted.

---

## Priority Ordering

### Must fix before implementing

**M1.** Do not create a standalone broker in the unified TUI path (Task 7 Option A). The broker has no publisher in that path. Use nil-broker fallback (existing SQLite polling) for the unified TUI. Inject `agg.Broker()` only in `runBigendTUI` where the aggregator exists. (Section 1.2)

**M2.** Inject `*events.Store` at `New()` time rather than via `SetEventsStore`. The setter creates a race window between `ConnectWebSocket` start and store assignment, and breaks the established constructor-injection pattern for all other dependencies. (Section 1.3)

**M3.** Replace the `signal.raised` passthrough with a real mapping or explicit handling. Publishing a signal with `SignalType("signal.raised")` produces an undefined type that no subscriber can filter and no render code labels. (Section 2.2)

### Fix during implementation

**F1.** Replace the `map[string]SignalType` prefix-loop with a slice of explicit entries to eliminate non-deterministic map iteration. While no current entries collide, the pattern is incorrect and fragile. (Section 2.1)

**F2.** Replace `inferSeverity` with severity declared per mapping entry. The string-contains heuristic will produce wrong results as event types grow. (Section 2.3)

**F3.** Remove the dead factory code in Task 7 (`views.NewSignalsView(c)` that is never used). The compiled Go will reject it as an unused variable; the plan must be trimmed. (Section 3.2)

**F4.** Resolve the `Blur()`-closes-subscription lifecycle issue. Either close and re-open in `Focus()`, or keep the subscription alive across focus changes. (Section 3.4)

### Optional cleanup

**O1.** Reduce the Task 3 broker test timeout from 2 seconds to 100ms. (Section 3.3)

**O2.** Remove `connectIntermute()` from `SignalsView` once the broker path is proven. Three delivery mechanisms for one view is unnecessary complexity. (Section 1.4)

**O3.** Evaluate whether Task 4 dual-write is needed given existing tool emitters already write to the events store. Defer if no concrete fallback scenario requires it. (Section 3.1)
