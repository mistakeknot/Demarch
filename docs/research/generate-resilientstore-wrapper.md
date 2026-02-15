# ResilientStore Wrapper Analysis

## Overview

Generated `/root/projects/Interverse/services/intermute/internal/storage/sqlite/resilient.go` -- a complete `ResilientStore` that wraps every method of `*Store` with `CircuitBreaker` + `RetryOnDBLock` for transient SQLite error resilience.

## Architecture

### Struct & Constructors

- `ResilientStore` holds `inner *Store` and `cb *CircuitBreaker`
- `NewResilient(inner)` -- default settings: threshold=5, resetTimeout=30s
- `NewResilientWithBreaker(inner, cb)` -- custom circuit breaker injection (for testing)

### Method Wrapping Pattern

Every method follows one of three patterns depending on return signature:

1. **`(T, error)`** -- 43 methods: declare `var result T`, assign inside double-nested closure (`cb.Execute` -> `RetryOnDBLock` -> inner call), return result+err
2. **`error` only** -- 14 methods: direct return of `cb.Execute(RetryOnDBLock(inner))`
3. **`(int, int, error)`** -- 1 method (`InboxCounts`): two named vars captured in closure

### Special Cases

- **`Close()`**: direct delegation, no CB/retry (closing a DB handle should not be retried)
- **`CheckConflicts()`**: full CB+retry (F4 sprint method, already implemented on `*Store`)
- **`SweepExpired()`**: full CB+retry (F3 sprint method, already implemented on `*Store`)
- **`CircuitBreakerState()`**: convenience accessor returning `cb.State().String()`

## Interface Satisfaction

Compile-time check ensures `ResilientStore` satisfies `storage.DomainStore`:

```go
var _ storage.DomainStore = (*ResilientStore)(nil)
```

`DomainStore` embeds `Store`, so this single check covers all 57 interface methods across both interfaces.

## Methods Wrapped (58 total)

### From `storage.Store` (15 methods)

| Method | Return Type | Pattern |
|--------|-------------|---------|
| `AppendEvent` | `(uint64, error)` | value+err |
| `InboxSince` | `([]core.Message, error)` | value+err |
| `ThreadMessages` | `([]core.Message, error)` | value+err |
| `ListThreads` | `([]storage.ThreadSummary, error)` | value+err |
| `RegisterAgent` | `(core.Agent, error)` | value+err |
| `Heartbeat` | `(core.Agent, error)` | value+err |
| `ListAgents` | `([]core.Agent, error)` | value+err |
| `MarkRead` | `error` | err-only |
| `MarkAck` | `error` | err-only |
| `RecipientStatus` | `(map[string]*core.RecipientStatus, error)` | value+err |
| `InboxCounts` | `(int, int, error)` | multi-value |
| `Reserve` | `(*core.Reservation, error)` | value+err |
| `GetReservation` | `(*core.Reservation, error)` | value+err |
| `ReleaseReservation` | `error` | err-only |
| `ActiveReservations` | `([]core.Reservation, error)` | value+err |
| `AgentReservations` | `([]core.Reservation, error)` | value+err |

### From `storage.DomainStore` (38 methods)

| Group | Methods | Count |
|-------|---------|-------|
| Spec CRUD | Create/Get/List/Update/Delete | 5 |
| Epic CRUD | Create/Get/List/Update/Delete | 5 |
| Story CRUD | Create/Get/List/Update/Delete | 5 |
| Task CRUD | Create/Get/List/Update/Delete | 5 |
| Insight | Create/Get/List/LinkToSpec/Delete | 5 |
| Session | Create/Get/List/Update/Delete | 5 |
| CUJ | Create/Get/List/Update/Delete + Link/Unlink/GetLinks | 8 |

### Concrete-only (not in interfaces, 3 methods)

| Method | Return Type | Wrapped? |
|--------|-------------|----------|
| `CheckConflicts` | `([]core.ConflictDetail, error)` | CB+retry |
| `SweepExpired` | `([]core.Reservation, error)` | CB+retry |
| `Close` | `error` | direct pass-through |

## Resilience Layers

```
Caller -> ResilientStore.Method()
          -> CircuitBreaker.Execute()     [fast-fail if open]
             -> RetryOnDBLock()           [7 retries, 50ms base, exp backoff, 25% jitter]
                -> Store.Method()         [actual SQLite operation]
```

- **CircuitBreaker**: 3-state (closed/open/half-open). Opens after 5 consecutive failures. Probes after 30s. Prevents thundering herd during extended outages.
- **RetryOnDBLock**: Only retries `"database is locked"` errors. Max 7 retries with exponential backoff (50ms, 100ms, 200ms, ..., 3200ms) + 25% jitter. Non-lock errors pass through immediately.

## Imports

```go
import (
    "context"
    "time"
    "github.com/mistakeknot/intermute/internal/core"
    "github.com/mistakeknot/intermute/internal/storage"
)
```

Uses `storage.Event` (type alias for `core.Event`) and `storage.ThreadSummary` for type references that are defined in the `storage` package.

## Verification

- **Compiles**: `go build ./...` -- clean, zero errors
- **Tests pass**: `go test ./internal/storage/sqlite/` -- all existing tests pass (0.805s)
- **Interface check**: compile-time `var _ storage.DomainStore = (*ResilientStore)(nil)` ensures complete coverage

## Design Notes

- The wrapper is purely mechanical -- no business logic changes, no additional error wrapping. This keeps the resilience layer transparent and debuggable.
- `Close()` is intentionally not wrapped with CB/retry because: (1) it's idempotent, (2) retrying a close on a locked DB is counterproductive, (3) the CB should not track close failures as "database health" signals.
- The `inner` field is `*Store` (concrete), not an interface, because the wrapper needs access to concrete-only methods (`CheckConflicts`, `SweepExpired`, `Close`).
