# Correctness Review: Signal Broker Wiring Plan
**Plan file:** `/root/projects/Interverse/hub/autarch/docs/plans/2026-02-20-signal-broker-wiring.md`
**Reviewer:** Julik (Flux-drive Correctness Reviewer)
**Date:** 2026-02-20

---

## Invariants That Must Hold

Before finding defects, establish what must be true at all times:

1. **I1 — Subscription lifetime matches goroutine lifetime.** Every `Subscription` created by `broker.Subscribe()` must be `Close()`d exactly once. Early close panics (send on closed channel). Late or missing close leaks the goroutine blocked on `sub.Chan()`.

2. **I2 — No blocking operation under the broker lock.** `broker.Publish()` holds `b.mu` for the full fan-out. No call under that lock may block indefinitely — no channel send, no I/O, no waiting on another lock.

3. **I3 — Dual-write atomicity.** `broker.Publish()` and `events.Store.Insert()` happen in the same logical operation. If one succeeds and the other fails, the system must not silently misrepresent the event history.

4. **I4 — waitBrokerSignal loop terminates cleanly on view teardown.** A goroutine blocked on `<-sub.Chan()` must not outlive the view that owns it, and must not consume signals from a subscription that belongs to a new lifecycle.

5. **I5 — Overlay subscription is single-instance.** Opening the overlay twice (toggle + toggle + toggle) must not create two concurrent goroutines consuming the same channel.

6. **I6 — Type-filter passthrough is well-defined.** The `signal.raised` passthrough case in `eventSignalMapping` sets `sigType = ""`. Using `""` as `signals.SignalType` must be intentional and handled everywhere that consumes signal types.

7. **I7 — Prefix-match is deterministic.** When an event type could match multiple prefixes, the signal type assigned must be consistent across runs.

---

## Finding 1 (CRITICAL): Blocking Channel Send Under Broker Mutex — Deadlock Vector

**Severity:** Deadlock; process-level stall affecting all broker subscribers.

### Location

`/root/projects/Interverse/hub/autarch/pkg/signals/broker.go`, `Publish()`, lines 44–65.

### The Code

```go
func (b *Broker) Publish(sig Signal) {
    b.mu.Lock()
    defer b.mu.Unlock()
    for sub := range b.subs {
        ...
        select {
        case sub.ch <- sig:       // fast path — non-blocking
        default:
            // Channel is full: evict oldest queued signal so newest wins.
            select {
            case <-sub.ch:        // drain one slot
                b.Dropped.Add(1)
            default:
            }
            sub.ch <- sig         // UNCONDITIONAL BLOCKING SEND — still holding b.mu
        }
    }
}
```

The last line `sub.ch <- sig` is an unconditional blocking send executed while `b.mu` is held. This is the exact condition for a deadlock:

### Concrete Failure Narrative

The channel capacity is 64. Suppose the TUI goroutine is slightly behind the WebSocket event rate.

```
T0: broker.Publish() is called. Channel has 64 items. Takes b.mu.Lock().
T1: Fast path select fails (full channel).
T2: Drain-one select succeeds: <-sub.ch drains 1 item. Channel now has 63.
    b.Dropped.Add(1).
T3: Between T2 and the send below, the TUI goroutine wakes and reads 2 more items.
    Channel now has 61 items.
    (This is fine; we proceed.)
T4: Alternative scenario: Between T2 and T4, five more Publish calls are queued
    on the WebSocket goroutine — but they cannot run because the first Publish
    still holds b.mu. So channel stays at 63.
T5: sub.ch <- sig executes. Channel goes to 64. Fine. Lock released.

— but in the pathological case —

T0: broker.Publish() is called. Channel has 64 items. Takes b.mu.Lock().
T1: Fast path select fails. Drain-one select is reached.
T2: The drain-one INNER select also hits default (this happens if the channel
    empties between the outer and inner selects — unlikely but possible under
    race detector scheduling, or if sub.Close() is racing).
T3: sub.ch <- sig is reached with channel still at 64.
T4: The unconditional send BLOCKS, holding b.mu.
T5: sub.Close() is called from Blur() in the TUI. Close() tries b.mu.Lock().
    DEADLOCK: Close() waits for Publish to release; Publish waits for the
    subscriber goroutine to drain; subscriber goroutine cannot drain because it
    is blocked trying to call sub.Close() (or has already exited).
```

Even without the Close() scenario, a single slow subscriber can hold the broker lock indefinitely, starving all other subscribers and blocking every new Publish call.

**The `go test -race` test (`TestPublishOverflow`) does not catch this** because it publishes 65 signals sequentially to a single subscriber channel and then drains. It never has the lock held while the channel is blocked.

### Fix

Replace the unconditional blocking send with a second non-blocking select:

```go
select {
case sub.ch <- sig:
default:
    // Channel still full after eviction attempt — count the drop and move on.
    b.Dropped.Add(1)
}
```

Full corrected evict path:

```go
select {
case sub.ch <- sig:
default:
    select {
    case <-sub.ch:
        b.Dropped.Add(1)
    default:
    }
    select {
    case sub.ch <- sig:
    default:
        // Truly lost; the subscriber cannot keep up.
        b.Dropped.Add(1)
    }
}
```

The broker lock is never held across a blocking channel operation. Backpressure is absorbed by dropping with a counter, not by blocking the publisher.

---

## Finding 2 (HIGH): Goroutine Leak — Re-Subscribe Without Closing Prior Subscription

**Severity:** Goroutine accumulation; signals consumed by orphaned goroutines, never delivered to TUI.

### Location

Plan Task 5 (`SignalsView.Init()`) and Task 6 (`SignalsOverlay.Toggle()` — opening branch).

### The Proposed Code

```go
func (v *SignalsView) Init() tea.Cmd {
    cmds := []tea.Cmd{
        v.loadData(),
        v.connectIntermute(),
    }
    if v.broker != nil {
        v.brokerSub = v.broker.Subscribe(nil)   // creates new sub, overwrites field
        cmds = append(cmds, v.waitBrokerSignal())
    }
    return tea.Batch(cmds...)
}
```

If `Init()` is called again on an already-initialized view (which Bubble Tea does when the program re-starts the model, or when window resize triggers re-initialization in some app configurations), the old `v.brokerSub` is overwritten without closing it. The goroutine from the previous `waitBrokerSignal()` is now blocked on a channel that nobody will ever `Close()`. It leaks until process exit.

### Failure Narrative

```
T0: App initializes. Init() → brokerSub = sub1. G1 spawned, blocked on sub1.Chan().
T1: App re-initializes (resize, tab nav, or re-mount). Init() called again.
    brokerSub = sub2 (sub1 silently orphaned).
    G2 spawned, blocked on sub2.Chan().
T2: G1 is still alive. The broker fan-out now sends to both sub1 and sub2.
T3: G1 receives a signal, delivers brokerSignalMsg. Update() re-arms on brokerSub
    (which is now sub2). G1 is now chasing sub2's messages, but G2 is also
    chasing sub2's messages.
T4: One signal from the broker is consumed by G1, which re-arms on sub2 — spawning G3.
    G2 also fires, spawning G4. The subscription goroutine count doubles per re-init.
T5: sub1 is never closed. The broker's b.subs map grows by one orphaned entry per
    re-init. Dropped counter counts drops against sub1 forever.
```

This same bug applies to `SignalsOverlay.Toggle()` if called twice rapidly before the first subscription has been consumed.

### Fix

Guard both `Init()` and the overlay's open path:

```go
func (v *SignalsView) Init() tea.Cmd {
    // Close any pre-existing subscription before creating a new lifecycle.
    if v.brokerSub != nil {
        v.brokerSub.Close()
        v.brokerSub = nil
    }
    cmds := []tea.Cmd{v.loadData(), v.connectIntermute()}
    if v.broker != nil {
        v.brokerSub = v.broker.Subscribe(nil)
        cmds = append(cmds, v.waitBrokerSignal())
    }
    return tea.Batch(cmds...)
}
```

And in `SignalsOverlay.Toggle()` opening branch:

```go
if o.visible {
    o.loaded = false
    cmds := []tea.Cmd{o.loadData()}
    if o.broker != nil {
        if o.brokerSub != nil {       // guard before subscribing
            o.brokerSub.Close()
        }
        o.brokerSub = o.broker.Subscribe(nil)
        cmds = append(cmds, o.waitBrokerOverlaySignal())
    }
    return tea.Batch(cmds...)
}
```

---

## Finding 3 (HIGH): Stale Subscription Capture in `waitBrokerSignal` Closures — Signal Loss and Double-Consumer Race

**Severity:** Signals delivered to wrong goroutine; Update() re-arms on a different subscription than the goroutine currently blocked; eventual two-goroutine race on the same channel.

### Location

Plan Task 5, `waitBrokerSignal()`:

```go
func (v *SignalsView) waitBrokerSignal() tea.Cmd {
    if v.brokerSub == nil {
        return nil
    }
    return func() tea.Msg {
        sig, ok := <-v.brokerSub.Chan()   // reads v.brokerSub at EXECUTION time
        if !ok {
            return nil
        }
        return brokerSignalMsg{signal: sig}
    }
}
```

The closure reads `v.brokerSub` at the time the `tea.Cmd` is *executed* by Bubble Tea's runtime, not at the time `waitBrokerSignal()` is *called*. If `v.brokerSub` has been replaced (by a re-init or by the overlay toggle sequence), the goroutine will read from the new subscription while another goroutine (from the new Init) also reads from the new subscription.

### Failure Narrative

```
T0: Init() → brokerSub = sub1. Cmd1 = waitBrokerSignal(). G1 spawned.
    G1 is queued by Bubble Tea's runtime but not yet executing.
T1: Blur() called → sub1.Close(), brokerSub = nil.
T2: Focus() → Init() again → brokerSub = sub2. Cmd2 = waitBrokerSignal().
    G2 spawned. G2 is now blocking on sub2.Chan().
T3: G1 finally starts executing. It reads v.brokerSub at this point → sub2.
    Now G1 and G2 are BOTH blocking on sub2.Chan().
T4: Broker publishes signal S. sub2 receives it. One of G1 or G2 wakes.
    Say G1 wakes. G1 delivers brokerSignalMsg to Update().
    Update() calls waitBrokerSignal() → G3 spawned on sub2.Chan().
    Now G2 and G3 are both on sub2.Chan(). G2 is permanent orphan noise.
T5: Every subsequent signal is consumed by one goroutine; the other is starved.
    Every Update() arms a new goroutine. Goroutine count grows unboundedly.
```

### Fix

Capture the subscription by value at call time:

```go
func (v *SignalsView) waitBrokerSignal() tea.Cmd {
    sub := v.brokerSub  // capture current sub at construction time, not execution time
    if sub == nil {
        return nil
    }
    return func() tea.Msg {
        sig, ok := <-sub.Chan()  // uses captured sub, immune to field reassignment
        if !ok {
            return nil
        }
        return brokerSignalMsg{signal: sig}
    }
}
```

And in `Update()`, only re-arm if the captured subscription is still the current one:

```go
case brokerSignalMsg:
    v.signals = append([]signals.Signal{msg.signal}, v.signals...)
    v.selected = clamp(v.selected, 0, v.currentListLen()-1)
    // Only re-arm if the subscription is still active (not replaced by a re-init).
    if v.brokerSub != nil {
        return v, v.waitBrokerSignal()
    }
    return v, nil
```

The identical fix must be applied to `waitBrokerOverlaySignal()` in the overlay.

---

## Finding 4 (HIGH): Dual-Write Failure is Logged at Debug Level — Silent History Divergence

**Severity:** Events appear in-memory (delivered to TUI subscribers) but not persisted; on next startup the event history is silently incomplete.

### Location

Plan Task 4, `handleIntermuteEvent` extension:

```go
if sig, ok := intermuteEventToSignal(aggEvt); ok {
    a.broker.Publish(sig)         // broadcasts to all in-memory subscribers

    if a.eventsStore != nil {
        payload, _ := json.Marshal(sig)    // error silently discarded
        storeEvt := &events.Event{...}
        if err := a.eventsStore.Insert(storeEvt); err != nil {
            slog.Debug("failed to persist signal to events store", "error", err)
            // ← at Debug level; invisible in production logs
        }
    }
}
```

Two independent defects:

**Defect A:** `json.Marshal` error is swallowed with `_`. If `sig` contains a value that fails JSON marshaling (a custom type added later, or a non-UTF8 string), `payload` is `nil`. `storeEvt.Payload = nil` is inserted into SQLite. Reads that try to `json.Unmarshal(evt.Payload, &sig)` will fail, producing a fallback signal with missing fields. The `loadData()` in `SignalsView` does handle this fallback, but the root cause is invisible.

**Defect B:** The insert failure is logged at `slog.Debug`. In a production deployment where `slog` level is `Info` or higher, a disk-full, locked-DB, or schema-mismatch failure produces zero observable output. Subscribers received the signal; SQLite did not record it. On the next app start, the event is gone. This is an active correctness violation: the TUI showed it, the history denies it.

### Invariant Conflict

This violates I3 (dual-write atomicity). Since broker and SQLite cannot participate in a single transaction, the plan must document the chosen failure mode explicitly. The minimum fix is:

1. Escalate to `slog.Warn` with signal ID, signal type, and the error.
2. Handle the marshal error explicitly:

```go
payload, err := json.Marshal(sig)
if err != nil {
    slog.Warn("failed to marshal signal for persistence; broker delivery unaffected",
        "signal_id", sig.ID, "signal_type", sig.Type, "error", err)
} else if a.eventsStore != nil {
    storeEvt := &events.Event{
        EventType:  events.EventSignalRaised,
        EntityType: events.EntityType("signal"),
        EntityID:   sig.ID,
        SourceTool: events.SourceTool(sig.Source),
        Payload:    payload,
        CreatedAt:  sig.CreatedAt,
    }
    if err := a.eventsStore.Insert(storeEvt); err != nil {
        slog.Warn("failed to persist signal to events store; in-memory delivery succeeded",
            "signal_id", sig.ID, "error", err)
    }
}
```

The architecture decision — broker-first or store-first — is out of scope for this plan, but must be documented in an ADR.

---

## Finding 5 (MEDIUM): SQLite Write on WebSocket Goroutine — WS Read Loop Stall

**Severity:** Event delivery stall under disk pressure; Intermute connection timeout risk.

### Location

Plan Task 4: `handleIntermuteEvent` is called directly from the WebSocket callback registered in `ConnectWebSocket`:

```go
a.intermuteClient.On("*", func(evt intermute.Event) {
    a.handleIntermuteEvent(evt)    // synchronous call on WS goroutine
})
```

With Task 4's changes, `handleIntermuteEvent` now synchronously calls `a.eventsStore.Insert()` — a SQLite write that involves I/O and potentially WAL locking. SQLite write latency in contended or low-memory scenarios can reach 10s+ seconds (the default busy_timeout for the events store is unknown). During that time, the WebSocket read goroutine is blocked and cannot process incoming frames. Intermute will either buffer (if it has unlimited buffering) or consider the client stalled and time out the connection.

### Fix

Move the store write to a goroutine:

```go
if sig, ok := intermuteEventToSignal(aggEvt); ok {
    a.broker.Publish(sig)

    if a.eventsStore != nil {
        go func(s signals.Signal) {
            payload, err := json.Marshal(s)
            if err != nil {
                slog.Warn("signal marshal failed", "signal_id", s.ID, "error", err)
                return
            }
            storeEvt := &events.Event{
                EventType:  events.EventSignalRaised,
                EntityType: events.EntityType("signal"),
                EntityID:   s.ID,
                SourceTool: events.SourceTool(s.Source),
                Payload:    payload,
                CreatedAt:  s.CreatedAt,
            }
            if err := a.eventsStore.Insert(storeEvt); err != nil {
                slog.Warn("signal persistence failed", "signal_id", s.ID, "error", err)
            }
        }(sig)
    }
}
```

Trade-off: this increases the temporal gap between the broker publish and the store write, making the dual-write even less synchronous. This is acceptable given that SQLite is a fallback/history path, not the primary delivery mechanism. The decision must be documented.

---

## Finding 6 (MEDIUM): Prefix-Match in `intermuteEventToSignal` is Non-Deterministic

**Severity:** Wrong signal type assigned non-deterministically when event type matches multiple prefixes; flaky signal filtering.

### Location

Plan Task 2, `signal_convert.go`:

```go
var eventSignalMapping = map[string]signals.SignalType{
    "task.blocked":  signals.SignalTaskBlocked,
    "run.failed":    signals.SignalExecutionDrift,
    "run.waiting":   signals.SignalExecutionDrift,
    "spec.revised":  signals.SignalSpecHealthLow,
    "signal.raised": "",
}

func intermuteEventToSignal(evt Event) (signals.Signal, bool) {
    sigType, found := eventSignalMapping[evt.Type]  // exact match first
    if !found {
        for prefix, st := range eventSignalMapping {  // map range = random order
            if strings.HasPrefix(evt.Type, prefix) {
                sigType = st
                found = true
                break  // first random match wins
            }
        }
    }
    ...
}
```

Today's mapping has no overlapping prefixes, so the non-determinism is latent. But the code explicitly documents prefix matching as a feature. As soon as a `"run."` catch-all prefix or a more specific `"task.blocked.timeout"` entry is added, event types that match two prefixes will be assigned different `SignalType` values on different runs. This is a test-order-sensitive bug waiting to be shipped.

### Fix

Use an ordered slice, not a map, for prefix lookups:

```go
// exactSignalMapping is checked first for full type name matches.
var exactSignalMapping = map[string]signals.SignalType{
    "signal.raised": "",  // passthrough — see intermuteEventToSignal
}

// prefixSignalMapping is checked in order; first match wins.
var prefixSignalMapping = []struct {
    prefix  string
    sigType signals.SignalType
}{
    {"task.blocked", signals.SignalTaskBlocked},
    {"run.failed",   signals.SignalExecutionDrift},
    {"run.waiting",  signals.SignalExecutionDrift},
    {"spec.revised", signals.SignalSpecHealthLow},
}
```

This makes priority explicit and testable.

---

## Finding 7 (MEDIUM): `TestSignalsView_BrokerPush` Does Not Exercise the Subscription Goroutine

**Severity:** False test confidence; goroutine leak and double-subscribe bugs from Findings 2 and 3 are not caught by this test.

### Location

Plan Task 5, `signals_broker_test.go`:

```go
func TestSignalsView_BrokerPush(t *testing.T) {
    broker := signals.NewBroker()
    v := NewSignalsView(nil)
    v.SetBroker(broker)

    cmd := v.Init()
    if cmd == nil {
        t.Fatal("expected Init to return a command")
    }

    want := signals.Signal{...}
    broker.Publish(want)

    // The subscription goroutine should produce a brokerSignalMsg
    // We can't easily test the full Bubble Tea loop, but we can test
    // that the view handles the message correctly
    v2, _ := v.Update(brokerSignalMsg{signal: want})
    ...
}
```

The comment is honest but the test is misleading. `Init()` returns a `tea.Cmd` (a function). Bubble Tea would run that function in a goroutine and deliver the result as a `tea.Msg`. The test does not run the command. `broker.Publish(want)` publishes to a subscription channel that nobody is reading in this test. The `brokerSignalMsg` is manually injected into `Update()`.

This test verifies only that `Update()` handles `brokerSignalMsg{...}` correctly — not that the subscription goroutine delivers signals, not that cleanup is correct on `Blur()`, not that double-init does not leak.

### Required Additional Test

```go
func TestSignalsView_WaitBrokerSignal_Delivers(t *testing.T) {
    broker := signals.NewBroker()
    v := NewSignalsView(nil)
    v.SetBroker(broker)

    // Manually create subscription as Init() would.
    sub := broker.Subscribe(nil)
    v.brokerSub = sub

    // Get the wait command.
    cmd := v.waitBrokerSignal()

    // Run the command in background (simulates Bubble Tea runtime).
    msgCh := make(chan tea.Msg, 1)
    go func() { msgCh <- cmd() }()

    // Publish a signal.
    want := signals.Signal{ID: "TEST-001", Type: signals.SignalTaskBlocked}
    broker.Publish(want)

    select {
    case msg := <-msgCh:
        got, ok := msg.(brokerSignalMsg)
        if !ok {
            t.Fatalf("expected brokerSignalMsg, got %T", msg)
        }
        if got.signal.ID != "TEST-001" {
            t.Fatalf("unexpected signal ID: %q", got.signal.ID)
        }
    case <-time.After(2 * time.Second):
        t.Fatal("timeout: signal not delivered")
    }
}

func TestSignalsView_Blur_ClosesSubscription(t *testing.T) {
    broker := signals.NewBroker()
    v := NewSignalsView(nil)
    v.SetBroker(broker)
    v.brokerSub = broker.Subscribe(nil)

    v.Blur()

    if v.brokerSub != nil {
        t.Fatal("expected brokerSub to be nil after Blur()")
    }
    // Broker should have no remaining subscribers.
    // (Requires a method or test-only accessor; or verify by checking Dropped after Publish)
}
```

---

## Finding 8 (LOW): `TestHandleIntermuteEventSkipsUnmapped` Uses 100ms Sleep

**Severity:** Flaky under high load or race detector; correct behavior is testable synchronously.

### Location

Plan Task 3:

```go
select {
case sig := <-sub.Chan():
    t.Fatalf("expected no signal for unmapped event, got %+v", sig)
case <-time.After(100 * time.Millisecond):
    // Expected — no signal published
}
```

`handleIntermuteEvent` is called directly (not in a goroutine) in this test. `broker.Publish` is synchronous. After `handleIntermuteEvent` returns, the channel state is already final: either a signal is there or it is not. A 100ms wait is both wasteful and non-deterministic under `go test -race`, which can multiply scheduling delays by 2–20x.

### Fix

```go
select {
case sig := <-sub.Chan():
    t.Fatalf("expected no signal for unmapped event, got %+v", sig)
default:
    // Correct: no signal in channel immediately after synchronous call
}
```

---

## Finding 9 (LOW): `signal.raised` Passthrough Creates Untyped `SignalType` Value

**Severity:** Type-switch exhaustiveness gap; downstream consumers silently miss passthrough signals.

### Location

`signal_convert.go`:

```go
if sigType == "" {
    sig.Type = signals.SignalType(evt.Type) // arbitrary string cast to SignalType
}
```

Any type-switch that handles known `SignalType` constants will fall through to `default` for passthrough signals. The `filteredSignals()` in `SignalsView` filters by `signalTypeFilters`, which lists only named constants. Passthrough signals with dynamic types are never shown in any filter category except "all". This may be intentional, but it is undocumented.

The `signalTypeFilters` slice in `signals.go` does not include `SignalTaskBlocked` despite the plan adding it to the mapping, which means `task.blocked` signals will appear in "all" but not in any named filter. That is likely an oversight in the existing filter list that this plan does not fix.

### Fix Options

- Define a `SignalPassthrough signals.SignalType = "passthrough"` sentinel for all passthrough events.
- Or: Document explicitly that passthrough signals only appear under "all" filter.
- And: Add `SignalTaskBlocked` to `signalTypeFilters` in `signals.go`.

---

## Summary Table

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | CRITICAL | `broker.go:Publish()` | Unconditional blocking send under mutex — deadlock if subscriber is slow or being closed |
| 2 | HIGH | Task 5 `Init()`, Task 6 `Toggle()` | Re-subscribe without closing prior sub → goroutine leak, orphaned subscriber in broker |
| 3 | HIGH | Task 5 `waitBrokerSignal`, Task 6 `waitBrokerOverlaySignal` | Closure reads `sub` field at execution time, not call time → two goroutines on same channel, signal loss |
| 4 | HIGH | Task 4 dual-write | Store failure logged at `Debug`; `json.Marshal` error discarded → silent history divergence |
| 5 | MEDIUM | Task 4 `handleIntermuteEvent` | SQLite `Insert()` on WebSocket goroutine → WS read loop stall under disk pressure |
| 6 | MEDIUM | Task 2 `signal_convert.go` | Map range for prefix match → non-deterministic signal type on overlapping prefixes |
| 7 | MEDIUM | Task 5 test | `TestSignalsView_BrokerPush` does not run the subscription goroutine; Findings 2/3 invisible |
| 8 | LOW | Task 3 test | 100ms sleep assertion; synchronous call allows immediate `default:` check |
| 9 | LOW | Task 2 passthrough | Arbitrary string cast to `SignalType`; `SignalTaskBlocked` absent from `signalTypeFilters` |

---

## Minimum Required Changes Before Implementation Starts

**These must be addressed before any code is written:**

1. **Fix Finding 1 in `broker.go`** — replace the unconditional blocking send with a non-blocking fallback select. This is in existing production code and affects all current users of the broker, not just the new wiring.

2. **Fix Finding 3 (closure capture)** in both `waitBrokerSignal` and `waitBrokerOverlaySignal` — `sub := v.brokerSub` at call time, not field access at execution time. This is a one-line change per function that prevents the double-consumer race.

3. **Add pre-existing subscription guard in Init() and Toggle() (Finding 2)** — close any non-nil `brokerSub` before creating a new one.

4. **Escalate store failure logging to `slog.Warn` and handle marshal error explicitly (Finding 4)** — the `_` discard and `slog.Debug` are active correctness hazards in production.

**These should be addressed before merging:**

5. **Move SQLite insert off the WebSocket goroutine (Finding 5)** — one goroutine spawn; keeps the WS read loop non-blocking.

6. **Replace map-based prefix match with ordered slice (Finding 6)** — prevents future non-determinism as the mapping grows.

7. **Add goroutine-exercising tests for the wait commands (Finding 7)** — without these, the concurrency bugs from Findings 2 and 3 will not be detected by the test suite.
