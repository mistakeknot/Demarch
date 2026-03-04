**Bead:** iv-r6u9q

# Plan: Promote Go Redaction Library & Wire Persistence Paths

## Goal

Make the existing Go redaction library (currently `internal/` in intercore) available to autarch, add missing Hermes-specific patterns, and wire redaction into all event persistence INSERT paths that currently skip it.

## Prior Context

- **Existing library**: `core/intercore/internal/redaction/` — 784 LOC, 28 patterns, 17 categories
- **Already integrated**: `internal/audit/audit.go` auto-redacts all payloads before INSERT
- **Not integrated**: 8 INSERT paths across `event/store.go` and autarch's `events/store.go`
- **Reference**: fd-security-patterns review, Hermes `redact.py` (research/hermes_agent/agent/)

## Tasks

### 1. Promote redaction package from internal/ to pkg/
- [x] Move `core/intercore/internal/redaction/` → `core/intercore/pkg/redaction/`
- [x] Update import in `core/intercore/internal/audit/audit.go`: `internal/redaction` → `pkg/redaction`
- [x] Update any other internal imports (grep for `internal/redaction`)
- [x] Run `go test ./...` in intercore to verify

### 2. Add intercore replace directive to autarch
- [x] Add `replace github.com/mistakeknot/intercore => ../../core/intercore` to `apps/autarch/go.mod`
- [x] Add `github.com/mistakeknot/intercore` to autarch's `require` block (version doesn't matter with replace)
- [x] Run `go mod tidy` in autarch
- [x] Verify autarch still builds: `go build ./cmd/...`

### 3. Add missing Hermes patterns
- [x] Add to `patterns.go` in the promoted package:
  - `CategoryTelegramToken` — `(\d{8,}):[-A-Za-z0-9_]{30,}` (priority 90)
  - `CategoryPerplexityKey` — `pplx-[A-Za-z0-9]{10,}` (priority 100)
  - `CategoryFalKey` — `fal_[A-Za-z0-9_-]{10,}` (priority 100)
  - `CategoryFirecrawlKey` — `fc-[A-Za-z0-9]{10,}` (priority 100)
  - `CategoryBrowserBaseKey` — `bb_live_[A-Za-z0-9_-]{10,}` (priority 100)
  - `CategoryCodexToken` — `gAAAA[A-Za-z0-9_=-]{20,}` (priority 100)
- [x] Add corresponding `Category` constants to `types.go`
- [x] Add tests for each new pattern

### 4. Wire redaction into intercore event store
- [x] In `core/intercore/internal/event/store.go`:
  - Add `redaction` import
  - Add a `RedactionConfig` field to `Store` struct (or accept as param)
  - Apply `redaction.Redact()` to string fields before INSERT in:
    - `AddDispatchEvent()` — redact `reason`, `envelopeJSON`
    - `AddCoordinationEvent()` — redact `reason`, `envelopeJSON`
    - `insertReplayInput()` — redact `payload` (via early redaction in callers)
    - `AddInterspectEvent()` — redact `overrideReason`, `contextJSON`
    - `AddReviewEvent()` — redact `agentsJSON`, `resolution`, `dismissalReason`, `impact`
- [x] Run `go test ./...` in intercore

### 5. Wire redaction into autarch event store
- [x] In `apps/autarch/pkg/events/store.go`:
  - Add `redaction` import from intercore's `pkg/redaction`
  - Add a `RedactionConfig` field to `Store` struct
  - Apply `redaction.Redact()` to `Payload` ([]byte → string → redact → []byte) in `Append()`
- [x] In `apps/autarch/pkg/events/reconcile_store.go`:
  - Apply redaction to `reason` and `details` in `LogConflict()`
- [x] Run `go test ./...` in autarch

### 6. Final verification
- [x] Run intercore tests with race detector: `go test -race ./...`
- [x] Run autarch tests: `go test ./...`
- [x] Build both: `go build ./cmd/...` in both directories
