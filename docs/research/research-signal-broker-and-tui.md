# Autarch Signal Broker and Bigend/TUI Architecture Research

**Date**: 2026-02-20  
**Status**: Complete architectural analysis with vision-vs-reality gap identified

---

## Executive Summary

The autarch project contains a **functional signal broker** (pub/sub pattern) and event system, but they are **completely disconnected from the Bigend/TUI runtime**. The vision document claims embedded broker integration, but the actual codebase shows:

- ✓ Signal broker: Fully implemented in `pkg/signals/` with WebSocket server, pub/sub, backpressure
- ✓ Event storage: SQLite-backed event spine in `pkg/events/` with 20+ event types
- ✓ Intermute client: WebSocket events from Intermute service
- ✗ **Gap**: Bigend/TUI never subscribes to signals or broker
- ✗ **Gap**: No real-time signal injection into TUI
- ✗ **Gap**: Signal panel in Bigend is a stub (reads from file, never gets updates)

This document maps the full architecture and identifies the specific integration gaps.

---

## Part 1: Signal Broker Implementation

### Location & Structure

**Directory**: `/root/projects/Interverse/hub/autarch/pkg/signals/`

Key files:
- `signal.go` — Signal type definitions
- `broker.go` — Core pub/sub broker (64-item channel buffer per subscriber)
- `server.go` — HTTP + WebSocket wrapper
- `parse.go`, `parse_test.go` — Signal parsing utilities
- `agent_signal.go`, `ansi.go` — Utility functions

### Signal Types (Enum)

```go
type SignalType string

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

type Severity string

const (
    SeverityInfo     Severity = "info"
    SeverityWarning  Severity = "warning"
    SeverityCritical Severity = "critical"
)
```

### Signal Data Structure

```go
type Signal struct {
    ID            string     `json:"id"`
    Type          SignalType `json:"type"`
    Source        string     `json:"source"`              // "pollard", "gurgeh", "coldwine"
    SpecID        string     `json:"spec_id"`
    AffectedField string     `json:"affected_field"`     // dedup key
    Severity      Severity   `json:"severity"`
    Title         string     `json:"title"`
    Detail        string     `json:"detail"`
    CreatedAt     time.Time  `json:"created_at"`
    Dismissed     bool       `json:"dismissed"`
    DismissedAt   *time.Time `json:"dismissed_at,omitempty"`
}
```

### Broker Architecture

**In-process pub/sub** with typed subscriptions:

```go
type Broker struct {
    mu      sync.Mutex
    subs    map[*subscriber]struct{}
    Dropped atomic.Int64
}

type subscriber struct {
    ch    chan Signal              // 64-item buffer
    types map[SignalType]bool      // type filter (empty = all)
}
```

**Publish flow**:
1. Lock broker
2. For each subscriber:
   - Check type filter (if set, skip if type doesn't match)
   - Try to send on subscriber's channel
   - If full (evict-oldest-on-full backpressure): drop oldest, send newest
3. Unlock

**Subscribe flow**:
1. Create subscriber with optional type filter
2. Return Subscription wrapper with `Chan()` and `Close()` methods
3. Can `Stream(ctx, out)` to redirect to another channel

### WebSocket Server

**Listen address**: `127.0.0.1:8092` (local-only by default)

**Routes**:
- `GET /health` — JSON `{"status": "ok"}`
- `POST /api/signals` — Publish a signal (JSON body)
- `GET /ws?types=competitor_shipped,spec_health_low` — WebSocket stream (optional type filter)

**Server startup** (`internal/signals/cli/serve.go`):
```go
func ServeCmd() *cobra.Command {
    cmd := &cobra.Command{
        RunE: func(cmd *cobra.Command, args []string) error {
            srv := signals.NewServer(nil)
            return srv.ListenAndServe(addr)
        },
    }
    cmd.Flags().StringVar(&addr, "addr", "127.0.0.1:8092", "HTTP bind address")
    return cmd
}
```

**Invoked by**: `signals` CLI command (separate binary)  
**NOT invoked by**: autarch/bigend/tui commands

### Current Status per Vision

From `docs/autarch-vision.md` lines 202-215:

> **Status**: This architecture exists in Autarch's current codebase (the signal broker pattern is proven in Bigend and Coldwine). It has not yet been connected to Intercore's event bus — that integration is part of the Bigend migration.

**Verdict**: Half true. The broker exists and is proven. But it's **never started** by Bigend/TUI and **never receives signals** from anywhere.

---

## Part 2: Event Storage System

### Location & Structure

**Directory**: `/root/projects/Interverse/hub/autarch/pkg/events/`

Key files:
- `types.go` — Event type definitions + filter builder
- `store.go` — SQLite backend at `~/.autarch/events.db`
- `writer.go` — Write interface
- `reader.go` — Query interface
- `intermute_bridge.go` — Bridge from Intermute events to local store
- `reconcile.go` — Dedup and merge logic

### Event Types

```go
const (
    // Initiative events
    EventInitiativeCreated EventType = "initiative_created"
    EventInitiativeUpdated EventType = "initiative_updated"
    
    // Epic events
    EventEpicCreated EventType = "epic_created"
    EventEpicUpdated EventType = "epic_updated"
    
    // Signal events ← IMPORTANT
    EventSignalRaised    EventType = "signal_raised"
    EventSignalDismissed EventType = "signal_dismissed"
    // ... 18+ more types
)
```

### Event Storage Schema

SQLite table (inferred from code):
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_type TEXT,
    entity_type TEXT,
    entity_id TEXT,
    source_tool TEXT,
    payload BLOB,           -- JSON
    project_path TEXT,
    created_at TIMESTAMP
);
```

### Event Query Filter

```go
type EventFilter struct {
    EventTypes  []EventType
    EntityTypes []EntityType
    EntityIDs   []string
    SourceTools []SourceTool
    Since       *time.Time
    Until       *time.Time
    Limit       int
    Offset      int
}
```

Example usage:
```go
store.Query(
    NewEventFilter().
        WithEventTypes(EventSignalRaised).
        WithLimit(100)
)
```

### Who Writes Events?

**Nobody in current codebase** — writers are not implemented. The schema exists but there's no code path that calls `store.Write()`.

### Who Reads Events?

**Only Bigend/TUI signals overlay** (`internal/tui/signals_overlay.go` line 271):
```go
store, err := events.OpenStore("")
evs, err := store.Query(events.NewEventFilter().WithLimit(100))
```

This reads on-demand when user opens the overlay (Ctrl+S), not continuously.

---

## Part 3: Bigend/TUI Current Architecture

### TUI Bootstrap (`cmd/autarch/main.go`)

Bigend TUI is **deprecated** (line 360):
```go
func runBigendTUI(agg *aggregator.Aggregator) error {
    // Deprecation warning for standalone TUI
    fmt.Fprintln(os.Stderr, "\033[33m⚠ Deprecation warning: bigend --tui is deprecated.\033[0m")
    fmt.Fprintln(os.Stderr, "  Use: autarch tui --tool=bigend")
    
    m := bigendTui.New(agg, buildInfoString())
    p := tea.NewProgram(m, tea.WithAltScreen())
    _, err := p.Run()
    return err
}
```

Modern flow: `autarch tui` command launches unified TUI with Intermute manager.

### Aggregator Initialization (`internal/bigend/aggregator/aggregator.go`)

**Current data sources**:
1. **Discovery scanner**: Finds projects on disk
2. **TMux client**: Lists sessions and detects state
3. **State detector**: Pattern/repetition/activity/LLM-based status
4. **MCP manager**: Component health
5. **Intermute client**: WebSocket to Intermute service (optional, line 140-145)

**WebSocket connection to Intermute** (lines 170-212):
```go
func (a *Aggregator) ConnectWebSocket(ctx context.Context) error {
    if a.intermuteClient == nil {
        return fmt.Errorf("intermute client not available")
    }
    
    // Subscribes to 20+ event types:
    eventTypes := []string{
        "spec.created", "spec.updated", ..., "message.sent", ...
    }
    
    a.intermuteClient.On("*", func(evt intermute.Event) {
        a.handleIntermuteEvent(evt)
    })
    
    return a.intermuteClient.Subscribe(a.wsCtx, eventTypes...)
}
```

**But**: `ConnectWebSocket()` is **never called** in the codebase. Signal signals are never subscribed.

### Bigend TUI Model (`internal/bigend/tui/model.go`)

- Dashboard, Sessions, Agents tabs
- Runs pane (F6) showing Intercore kernel data
- Signal panel (line 16-17): Stub only
- No WebSocket consumer for broker or Intermute events

### Signal Panel (`internal/bigend/tui/signals.go`)

```go
type SignalPanel struct {
    signals []signals.Signal
}

func (p *SignalPanel) SetSignals(sigs []signals.Signal) {
    p.signals = sigs
}

func (p *SignalPanel) Render(width int) string {
    active := p.activeSignals()
    if len(active) == 0 {
        return "  No active signals"
    }
    var lines []string
    lines = append(lines, fmt.Sprintf("  ⚡ %d active signal(s)", len(active)))
    // ... render icons + titles
    return strings.Join(lines, "\n")
}
```

**Status**: Render function exists but `SetSignals()` is **never called** by TUI update loop.

### Signals Overlay (`internal/tui/signals_overlay.go`)

Modern unified TUI has a signals overlay (Ctrl+S):

```go
type SignalsOverlay struct {
    visible  bool
    signals  []signals.Signal
    events   []*events.Event
    selected int
    category int // 0=signals, 1=events
}

// Load data on open (line 269-323)
func (o *SignalsOverlay) loadData() tea.Cmd {
    return func() tea.Msg {
        store, err := events.OpenStore("")
        evs, err := store.Query(events.NewEventFilter().WithLimit(100))
        // ... parse signals from events
        return signalsOverlayLoadedMsg{signals: sigs, events: other}
    }
}
```

**Status**: On-demand file read, not real-time streaming. No broker connection.

---

## Part 4: Intermute Service Integration

### Intermute Client (`pkg/intermute/client.go`)

Autarch has a **local copy** of Intermute client code (26KB):
- Dials Intermute WebSocket on startup
- Subscribes to event types
- Triggers callbacks on events

**Invoked by**: Aggregator (only if `ConnectWebSocket()` called, which it isn't)

### Types Synchronized

From `pkg/intermute/types.go`:
- Spec, Epic, Story, Task (status enums)
- Message, MessageAttachment, MessageThread
- Insight, CUJ, Session, Agent
- Agent inbox counts, messaging

### Bridge to Local Events (`pkg/events/intermute_bridge.go`)

Unmapped. There's a file but no active code path writes Intermute events to local store.

---

## Part 5: Kernel/Intercore Integration

### KernelState Aggregation (`internal/bigend/aggregator/kernel.go`)

Aggregator fetches Intercore data:
```go
type KernelState struct {
    Runs       map[string][]icdata.Run
    Dispatches map[string][]icdata.Dispatch
    Events     map[string][]icdata.Event
    Metrics    KernelMetrics
}
```

**Fetched data**:
- Active runs per project
- Dispatch status + token counts
- Recent events (50 max, first 3 seconds)
- Aggregate metrics

**Used by**: Bigend dashboard (Runs pane, F6), kernel state metrics

**Not connected to signals**: Kernel events never trigger signal creation.

---

## Part 6: Vision-Reality Gap Analysis

### What Vision Claims (lines 202-215)

1. **Signal broker is embedded**: "An embedded goroutine within the Autarch app process"
   - ✓ Broker code exists
   - ✗ Never started
   - ✗ Never fed data

2. **In-process pub/sub with typed subscriptions**
   - ✓ Implemented in `Broker.Subscribe()` + type filter map
   - ✗ No subscribers exist

3. **WebSocket streaming to TUI and web consumers**
   - ✓ Server supports it (`/ws` endpoint)
   - ✗ TUI never connects to it

4. **Backpressure handling (evict-oldest-on-full)**
   - ✓ Implemented (line 56-62 in broker.go)
   - ✗ Never tested in practice

5. **Durable event log source of truth**
   - ✓ SQLite schema defined
   - ✗ Never written to
   - ✓ Overlay reads from it (file-based, on-demand)

6. **Broker is rendering optimization, not replacement for event bus**
   - ✓ Correct philosophy
   - ✗ Never implemented

### What's Actually Built

| Component | Exists? | Integrated? | Status |
|-----------|---------|-------------|--------|
| Signal types (8 enums) | ✓ | N/A | Complete |
| Broker pub/sub | ✓ | ✗ | Never instantiated |
| HTTP/WS server | ✓ | ✗ | Standalone CLI only |
| Event store schema | ✓ | ✗ | Created but empty |
| Event types (20+) | ✓ | Partial | Only signal_raised exists |
| Intermute client | ✓ | ✗ | Connected to agg, not used |
| Signal panel render | ✓ | ✗ | Stub, no data fed |
| Signals overlay (Ctrl+S) | ✓ | ✓ | Works (file-based, on-demand) |

---

## Part 7: Data Flow Diagrams

### Current Reality

```
┌─────────────────────────────────────────────────────────┐
│ autarch tui                                             │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Unified TUI (Bubble Tea)                          │  │
│ │                                                     │  │
│ │ ┌──────────────┐  ┌────────────────┐              │  │
│ │ │ Bigend View  │  │ Signals Overlay│              │  │
│ │ ├──────────────┤  └────────────────┘              │  │
│ │ │ - Dashboard  │      (Ctrl+S)                    │  │
│ │ │ - Sessions   │      ┌────────────────┐          │  │
│ │ │ - Agents     │      │ On open:       │          │  │
│ │ │ - Signal!!!  │      │ - OpenStore()  │          │  │
│ │ └──────────────┘      │ - Query()      │          │  │
│ │                       │ - Parse JSON   │          │  │
│ │                       └────────────────┘          │  │
│ │                          ↓                         │  │
│ │                       ~/.autarch/                 │  │
│ │                       events.db                   │  │
│ │                       (empty!)                    │  │
│ └────────────────────────────────────────────────────┘  │
│                                                         │
│ Internals:                                              │
│ - Intermute manager (spawns server on 7338)           │
│ - Aggregator (reads discovery, tmux, agg state)       │
│ - NO signal broker instantiation                      │
│ - NO Intermute WebSocket subscription                 │
│ - NO event write path                                 │
└─────────────────────────────────────────────────────────┘
```

### Vision Claims

```
┌──────────────────────────────────────────────────────────┐
│ autarch tui                                              │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Unified TUI + Embedded Signal Broker                │ │
│ │                                                       │ │
│ │ ┌─────────────┐  ┌────────────┐  ┌──────────────┐  │ │
│ │ │ Bigend View │  │ Signal     │  │ Broker       │  │ │
│ │ │ - Dashboard │  │ Panel      │  │ Subscriptions│  │ │
│ │ │ - Sessions  │  │ (live!)    │  │ (typed)      │  │ │
│ │ │ - Agents    │  │            │  │              │  │ │
│ │ │ - Signals   │◄─┤ (updates   │◄─┤ signal_type │  │ │
│ │ │ (live!)     │  │ via WS)    │  │ filter       │  │ │
│ │ └─────────────┘  └────────────┘  │              │  │ │
│ │                                   │ pub/sub fan │  │ │
│ │                                   └──────────────┘  │ │
│ │                                        ▲            │ │
│ └────────────────────────────────────────┼────────────┘ │
│                                          │              │
│                                   (embedded)             │
│                                   (ephemeral)            │
│                                   (feeds from             │
│                                    kernel                 │
│                                    cursor log)            │
└──────────────────────────────────────────────────────────┘
```

---

## Part 8: Current Startup Pathways

### Unified TUI (`autarch tui`)

File: `cmd/autarch/main.go:99-238`

```
1. tuiCmd() registers command
2. RunE handler:
   a. Check setup (auto-run if needed)
   b. Create Intermute manager (spawns server on :7338)
   c. Create Autarch client (connects to manager)
   d. Create UnifiedApp (generic TUI container)
   e. Wire dashboard views (Bigend, Gurgeh, Coldwine, Pollard)
   f. Run tui.Run(client, app, opts)
```

**Signal broker**: Not instantiated. Not started.

### Bigend Web (`autarch bigend`)

File: `cmd/autarch/main.go:251-443`

```
1. bigendCmd() registers command
2. RunE handler:
   a. Load config
   b. Create discovery scanner
   c. Create aggregator
   d. Create web server
   e. Spawn refresh ticker loop
   f. ListenAndServe()
```

**Signal broker**: Not instantiated. Not started.

**Intermute registration** (line 279):
```go
if stop, err := intermute.RegisterTool(registerCtx, "bigend"); err != nil {
    slog.Warn("intermute registration failed", "error", err)
}
```
This registers Bigend as a tool in the Intermute service, but doesn't connect Bigend to Intermute's event stream.

### Bigend TUI (deprecated, `autarch bigend --tui`)

File: `cmd/autarch/main.go:358-369`

```
1. Shows deprecation warning
2. Creates aggregator
3. Calls bigendTui.New(agg, buildInfo)
4. Runs Bubble Tea program
```

**Signal broker**: Not instantiated. Not started.

---

## Part 9: Missing Integration Points

### 1. Signal Broker Lifecycle

**Needed**:
```go
// In autarch tui / bigend initialization
signalBroker := signals.NewBroker()
signalServer := signals.NewServer(signalBroker)

// Spawn in background
go signalServer.ListenAndServe("127.0.0.1:8092")
```

**Current**: Doesn't exist.

### 2. Feed Events to Broker

**Needed**: A source that publishes signals:
```go
// When Pollard detects competitor move
broker.Publish(signals.Signal{
    Type:    signals.SignalCompetitorShipped,
    Source:  "pollard",
    SpecID:  spec.ID,
    Severity: signals.SeverityWarning,
    Title:   "Competitor shipped feature X",
    ...
})
```

**Current**: No code path calls `broker.Publish()`.

### 3. TUI Subscribes to Broker

**Needed**:
```go
// In Bigend TUI model
subscription := broker.Subscribe([]signals.SignalType{
    signals.SignalCompetitorShipped,
    signals.SignalAssumptionDecayed,
    // ... filter types
})

// In update loop
case sig := <-subscription.Chan():
    // Update signal panel
    m.signals = append(m.signals, sig)
```

**Current**: No subscription. No channel listen.

### 4. Write Events to Store

**Needed**:
```go
// When signal is created or dismissed
store.Write(&events.Event{
    EventType:  events.EventSignalRaised,
    EntityType: events.EntitySignal,
    EntityID:   signal.ID,
    SourceTool: events.SourcePollard,
    Payload:    marshalJSON(signal),
    CreatedAt:  time.Now(),
})
```

**Current**: Store exists but never written to.

### 5. Intermute → Broker Feed

**Needed**:
```go
// When Intermute sends an event
a.intermuteClient.On("*", func(evt intermute.Event) {
    // Convert to signal?
    sig := intermute.EventToSignal(evt)
    
    // Publish to broker
    broker.Publish(sig)
    
    // Write to event store
    store.Write(...)
})
```

**Current**: Event handler exists but is empty (line 246-250):
```go
func (a *Aggregator) handleIntermuteEvent(evt intermute.Event) {
    aggEvt := Event{
        // ... stub
    }
}
```

---

## Part 10: File Paths & Locations

### Core Broker Code

- `/root/projects/Interverse/hub/autarch/pkg/signals/signal.go` — Type definitions
- `/root/projects/Interverse/hub/autarch/pkg/signals/broker.go` — Pub/sub logic
- `/root/projects/Interverse/hub/autarch/pkg/signals/server.go` — HTTP/WS server
- `/root/projects/Interverse/hub/autarch/internal/signals/cli/serve.go` — Standalone CLI

### Event System

- `/root/projects/Interverse/hub/autarch/pkg/events/types.go` — Event & filter types
- `/root/projects/Interverse/hub/autarch/pkg/events/store.go` — SQLite backend
- `/root/projects/Interverse/hub/autarch/pkg/events/writer.go` — Write interface
- `/root/projects/Interverse/hub/autarch/pkg/events/intermute_bridge.go` — Bridge (unmapped)

### Bigend/TUI

- `/root/projects/Interverse/hub/autarch/internal/bigend/tui/model.go` — Main model (1100+ lines)
- `/root/projects/Interverse/hub/autarch/internal/bigend/tui/signals.go` — Signal panel stub
- `/root/projects/Interverse/hub/autarch/internal/tui/signals_overlay.go` — Overlay (file-based)
- `/root/projects/Interverse/hub/autarch/internal/bigend/aggregator/aggregator.go` — Data aggregator (600+ lines)

### Startup

- `/root/projects/Interverse/hub/autarch/cmd/autarch/main.go` — CLI entry point (570 lines)
- `/root/projects/Interverse/hub/autarch/cmd/signals/main.go` — Signals standalone CLI

### Vision Doc

- `/root/projects/Interverse/hub/autarch/docs/autarch-vision.md` — Lines 200-216 (signal architecture)

---

## Part 11: Recommendations for Implementation

### Phase 1: Broker Activation

1. **Instantiate broker** in TUI/Bigend initialization
2. **Start server** on loopback (non-blocking)
3. **Graceful shutdown** on context cancel

### Phase 2: Event Publish

1. **Identify signal sources**: Pollard (competitor detection), Gurgeh (spec health), Coldwine (task blockers)
2. **Create signal payload** at detection point
3. **Call `broker.Publish()`** with signal

### Phase 3: TUI Consumption

1. **Subscribe in model** on startup
2. **Listen in update loop** (non-blocking select)
3. **Render in signal panel** + update metrics

### Phase 4: Event Store

1. **Write to store** alongside broker publish (atomic or best-effort)
2. **Intermute bridge** → local store sync
3. **Signals overlay** can then use store as "recent history"

### Phase 5: Intermute Integration

1. **Implement `handleIntermuteEvent()`** to convert Intermute events → signals
2. **Publish converted signals** to broker
3. **Handle edge cases** (duplicate detection, type mapping)

---

## Conclusion

The autarch codebase has **all the building blocks** for real-time signal delivery:

- ✓ Signal types and schema
- ✓ Broker pub/sub mechanism
- ✓ WebSocket server capability
- ✓ Event store infrastructure
- ✓ Intermute integration framework

But they are **completely disconnected**. The signal broker exists in a vacuum — never started, never fed data, never consumed by TUI. The vision is sound; the execution is incomplete.

**Gap severity**: Medium. The architecture is correct; it just needs to be wired up. No fundamental redesign needed.

**Implementation complexity**: Low-to-medium. Five discrete phases, each with clear responsibilities.

---

## Appendix: Key Line References

| Component | File | Lines | Note |
|-----------|------|-------|------|
| Signal types | `pkg/signals/signal.go` | 8-44 | 8 signal types + 3 severity levels |
| Broker | `pkg/signals/broker.go` | 13-65 | Core pub/sub, evict-oldest backpressure |
| Server routes | `pkg/signals/server.go` | 50-54 | `/health`, `/ws`, `/api/signals` |
| Bigend agg init | `cmd/autarch/main.go` | 304 | `agg := aggregator.New()` (never starts broker) |
| Intermute ignore | `cmd/autarch/main.go` | 279-283 | Registers tool but never calls `ConnectWebSocket()` |
| Signal panel | `internal/bigend/tui/signals.go` | 16-57 | Render stub, `SetSignals()` never called |
| Overlay file read | `internal/tui/signals_overlay.go` | 269-323 | On-demand query, not real-time |
| Intermute event | `internal/bigend/aggregator/aggregator.go` | 246-250 | Empty handler stub |
| Vision | `docs/autarch-vision.md` | 202-215 | Claims broker is "connected" (it's not) |
