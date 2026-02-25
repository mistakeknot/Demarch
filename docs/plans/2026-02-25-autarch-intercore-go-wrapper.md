# Plan: Go Wrapper for ic CLI (pkg/intercore/client.go)

**Bead:** iv-cl86n
**Sprint:** q9m1soaj
**Priority:** P0 — blocks 11 downstream beads
**Complexity:** 3/5 (moderate)

## Problem

Autarch (Go/L3) cannot talk to Intercore (L1). The bash layer has `lib-intercore.sh` with 41 wrapper functions; the Go layer has nothing. Every planned feature — sprint creation, dispatch monitoring, phase advancement, event streaming — is blocked on this.

## Design

### Package: `apps/autarch/pkg/intercore`

A Go client that shells out to the `ic` binary with `--json` and parses results. NOT a library binding — `ic` is the stable contract, same as `lib-intercore.sh` uses.

### Architecture Principles

1. **Mirror lib-intercore.sh** — same function surface, same fail-open philosophy
2. **Binary discovery + health check** — `exec.LookPath("ic")` then `ic health`
3. **Graceful degradation** — `ErrUnavailable` sentinel error when ic missing; callers decide policy
4. **Context-aware** — all methods take `context.Context` for cancellation
5. **`--json` everywhere** — positional flag before subcommand (memory: `ic --json run list`, NOT `ic run list --json`)
6. **No caching** — callers (views, data sources) own caching policy
7. **Streaming for events** — `events tail --follow` returns a channel of events
8. **Safe subprocess execution** — use `exec.CommandContext` with explicit arg list (no shell interpolation)

### Types (from observed `ic --json` output)

```go
// Run represents an Intercore sprint run.
type Run struct {
    ID            string   `json:"id"`
    Goal          string   `json:"goal"`
    Phase         string   `json:"phase"`
    Status        string   `json:"status"`          // "active", "cancelled", "done"
    ProjectDir    string   `json:"project_dir"`
    ScopeID       string   `json:"scope_id,omitempty"` // bead ID
    Complexity    int      `json:"complexity"`
    AutoAdvance   bool     `json:"auto_advance"`
    ForceFull     bool     `json:"force_full"`
    TokenBudget   int64    `json:"token_budget,omitempty"`
    BudgetWarnPct int      `json:"budget_warn_pct,omitempty"`
    Phases        []string `json:"phases,omitempty"`
    CreatedAt     int64    `json:"created_at"`       // unix timestamp
    UpdatedAt     int64    `json:"updated_at"`
}

// Dispatch represents an agent dispatch.
type Dispatch struct {
    ID        string `json:"id"`
    RunID     string `json:"run_id"`
    Type      string `json:"type"`
    Agent     string `json:"agent,omitempty"`
    Status    string `json:"status"`
    CreatedAt int64  `json:"created_at"`
    UpdatedAt int64  `json:"updated_at"`
}

// GateResult from ic gate check.
type GateResult struct {
    RunID     string        `json:"run_id"`
    FromPhase string        `json:"from_phase"`
    ToPhase   string        `json:"to_phase,omitempty"`
    Result    string        `json:"result"`   // "pass" or "fail"
    Tier      string        `json:"tier"`     // "soft", "hard", "none"
    Evidence  *GateEvidence `json:"evidence,omitempty"`
}

type GateEvidence struct {
    Conditions []GateCondition `json:"conditions"`
}

type GateCondition struct {
    Check  string `json:"check"`
    Phase  string `json:"phase,omitempty"`
    Result string `json:"result"`
    Count  int    `json:"count,omitempty"`
    Detail string `json:"detail,omitempty"`
}

// AdvanceResult from ic run advance.
type AdvanceResult struct {
    Advanced   bool   `json:"advanced"`
    FromPhase  string `json:"from_phase"`
    ToPhase    string `json:"to_phase"`
    GateResult string `json:"gate_result"` // "pass", "fail", "none"
    GateTier   string `json:"gate_tier"`
    Reason     string `json:"reason,omitempty"`
    EventType  string `json:"event_type"`
}

// Artifact from ic run artifact list.
type Artifact struct {
    RunID string `json:"run_id"`
    Phase string `json:"phase"`
    Path  string `json:"path"`
    Type  string `json:"type,omitempty"`
}

// Event from ic events tail.
type Event struct {
    ID        int64  `json:"id"`
    RunID     string `json:"run_id"`
    Source    string `json:"source"`
    Type      string `json:"type"`
    FromState string `json:"from_state,omitempty"`
    ToState   string `json:"to_state,omitempty"`
    Reason    string `json:"reason,omitempty"`
    Timestamp int64  `json:"timestamp"`
}
```

### Client Interface

```go
type Client struct {
    binPath string  // resolved ic binary path
    dbPath  string  // optional --db override
    timeout time.Duration
}

// Construction
func New(opts ...Option) (*Client, error)       // discovers ic, runs health check
func Available() bool                           // quick check without error

// Run operations
func (c *Client) RunCreate(ctx, project, goal string, opts ...RunOption) (string, error)
func (c *Client) RunStatus(ctx, runID string) (*Run, error)
func (c *Client) RunList(ctx context.Context, active bool) ([]Run, error)
func (c *Client) RunAdvance(ctx, runID string) (*AdvanceResult, error)
func (c *Client) RunCancel(ctx, runID string) error
func (c *Client) RunPhase(ctx, runID string) (string, error)
func (c *Client) RunCurrent(ctx, projectDir string) (string, error)
func (c *Client) RunSet(ctx, runID string, opts ...RunSetOption) error

// Dispatch operations
func (c *Client) DispatchSpawn(ctx, runID string, opts ...DispatchOption) (string, error)
func (c *Client) DispatchStatus(ctx, dispatchID string) (*Dispatch, error)
func (c *Client) DispatchList(ctx context.Context, active bool) ([]Dispatch, error)
func (c *Client) DispatchWait(ctx, dispatchID string, timeout time.Duration) error
func (c *Client) DispatchKill(ctx, dispatchID string) error

// Gate operations
func (c *Client) GateCheck(ctx, runID string) (*GateResult, error)
func (c *Client) GateOverride(ctx, runID, reason string) error

// Artifact operations
func (c *Client) ArtifactAdd(ctx, runID, phase, path string, artifactType string) error
func (c *Client) ArtifactList(ctx, runID string, phase string) ([]Artifact, error)

// State operations
func (c *Client) StateSet(ctx, key, scope, jsonValue string) error
func (c *Client) StateGet(ctx, key, scope string) (string, error)
func (c *Client) StateDelete(ctx, key, scope string) error

// Event streaming
func (c *Client) EventsTail(ctx, runID string, follow bool) (<-chan Event, error)

// Lock operations
func (c *Client) LockAcquire(ctx, name, scope string, timeout time.Duration) error
func (c *Client) LockRelease(ctx, name, scope string) error
```

## Tasks

### Task 1: Core client + binary discovery (file: `pkg/intercore/client.go`)
- `Client` struct with binPath, dbPath, timeout
- `New()` with `exec.LookPath` + `ic health` check
- `Available()` quick probe
- `ErrUnavailable` sentinel
- Internal `execJSON(ctx, args...)` helper: builds `exec.CommandContext` with explicit arg list (no shell), prepends `--json`, captures stdout/stderr
- Internal `execText(ctx, args...)` for commands returning plain text (e.g., RunCreate)
- Error handling: parse stderr for known patterns, wrap with context

### Task 2: Types (file: `pkg/intercore/types.go`)
- All JSON-mapped structs from the design section above
- Helper methods: `Run.IsActive()`, `GateResult.Passed()`, `AdvanceResult.Succeeded()`
- `Option` types for construction and method overrides

### Task 3: Run operations (file: `pkg/intercore/run.go`)
- RunCreate, RunStatus, RunList, RunAdvance, RunCancel, RunPhase, RunCurrent, RunSet
- Note: RunCreate returns plain text ID (not JSON) — use execText, not execJSON

### Task 4: Dispatch + Gate + Artifact + State operations (file: `pkg/intercore/operations.go`)
- All Dispatch*, Gate*, Artifact*, State*, Lock* methods
- All follow the same pattern: build args, exec.CommandContext with arg list, unmarshal JSON

### Task 5: Event streaming (file: `pkg/intercore/events.go`)
- EventsTail with `--follow` flag
- Line-delimited JSON reader on stdout pipe via exec.CommandContext
- Returns `<-chan Event` that closes when context cancelled or process exits
- Goroutine reads lines, decodes JSON, sends to channel

### Task 6: Tests (file: `pkg/intercore/client_test.go`)
- Test binary discovery (mock PATH)
- Test JSON parsing for each response type against real ic output samples
- Test ErrUnavailable propagation
- Test context cancellation
- Integration test (build tag `integration`) that calls real `ic` if available

## Verification

- `go build ./pkg/intercore/...` compiles
- `go test ./pkg/intercore/... -race` passes
- `go vet ./pkg/intercore/...` clean
- Integration: create a run, check status, advance, list artifacts, cancel — end-to-end

## Non-Goals

- No caching layer (callers own that)
- No TUI integration (that's iv-4hcuq and iv-8by7z)
- No Intermute sync (that's iv-cguwq)
- No DataSource interface implementation (separate concern)
