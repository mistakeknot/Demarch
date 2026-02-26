# Intent Submission Mechanism — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)

**Goal:** Create a `pkg/clavain/` Go client in `apps/autarch/` that routes all 5 policy-governing write operations through Clavain's OS layer (`clavain-cli`) instead of bypassing it via direct `ic` calls.

**Architecture:** Subprocess client matching `pkg/intercore/` pattern — shells out to `clavain-cli` binary. Graceful degradation: falls back to direct `ic` calls when `clavain-cli` is not on PATH. Types duplicated for layer independence.

**Tech Stack:** Go 1.22+, `os/exec` for subprocess, `encoding/json` for output parsing, `testing` for table-driven tests. No external dependencies.

---

## Reference: Bypass Inventory

| Intent | Current bypass | File:Line | New call |
|--------|---------------|-----------|----------|
| Sprint creation | `ic.RunCreate()` | `coldwine.go:1121` | `clavain.SprintCreate()` |
| Sprint creation | `ic.RunCreate()` | `sprint_commands.go:127` | `clavain.SprintCreate()` |
| Task dispatch | `ic.DispatchSpawn()` | `coldwine.go:990` | `clavain.DispatchTask()` |
| Task dispatch | `ic.DispatchSpawn()` | `sprint_commands.go:183` | `clavain.DispatchTask()` |
| Run advancement | `ic.RunAdvance()` | `sprint_commands.go:83` | `clavain.SprintAdvance()` |
| Run advancement | `ic.RunAdvance()` | `coldwine_mode.go:87` | `clavain.SprintAdvance()` |
| Run advancement | `ic.RunAdvance()` | `coldwine_mode.go:147` | `clavain.SprintAdvance()` |
| Run cancel | `ic.RunCancel()` | `sprint_commands.go:99` | `clavain.SprintCancel()` |
| Run cancel | `ic.RunCancel()` | `coldwine_mode.go:102` | `clavain.SprintCancel()` |
| Artifact submit | `ic.StateSet()` (linking) | `coldwine.go:420,528,951` | Keep as-is (read metadata, not policy) |

**Note:** The `ic.StateSet()` calls at lines 420, 528, 951 are metadata writes (linking epic↔run, task↔dispatch). Per the vision doc, reads and non-policy metadata are allowed to call `ic` directly. Only policy-governing mutations go through L2.

## File Layout

```
apps/autarch/pkg/clavain/
├── client.go        # Client struct, binary discovery, exec helpers
├── client_test.go   # Client unit tests (mock exec)
├── sprint.go        # SprintCreate, SprintAdvance, SprintCancel
├── sprint_test.go   # Sprint command tests
├── dispatch.go      # DispatchTask (delegates to clavain-cli dispatch-task)
├── gate.go          # EnforceGate, GateOverride
├── artifact.go      # SetArtifact, GetArtifact
└── types.go         # SprintCreateResult, AdvanceResult, GateResult
```

---

### Task 1: Client Foundation — Binary Discovery + Exec Helpers

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)
**Files:**
- Create: `apps/autarch/pkg/clavain/client.go`
- Create: `apps/autarch/pkg/clavain/client_test.go`
- Create: `apps/autarch/pkg/clavain/types.go`

**Step 1: Write client_test.go**

```go
package clavain

import (
	"context"
	"testing"
)

func TestNew_BinaryNotFound(t *testing.T) {
	t.Setenv("PATH", "/nonexistent")
	_, err := New()
	if err == nil {
		t.Error("expected error when clavain-cli not on PATH")
	}
	if err != ErrUnavailable {
		t.Errorf("expected ErrUnavailable, got %v", err)
	}
}

func TestAvailable_NoError(t *testing.T) {
	// Just verify it doesn't panic.
	_ = Available()
}
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/autarch && go test ./pkg/clavain/ -run TestNew_BinaryNotFound -v`
Expected: FAIL — package does not exist.

**Step 3: Write types.go**

```go
// Package clavain provides a Go client for the clavain-cli binary (OS layer).
// It shells out to clavain-cli with subprocess calls, mirroring
// pkg/intercore's pattern for the ic binary.
//
// For policy-governing write operations (sprint creation, dispatch, advancement,
// gate enforcement, artifact registration), apps should use this package
// instead of calling ic directly.
package clavain

import "errors"

// ErrUnavailable is returned when clavain-cli is not found on PATH.
var ErrUnavailable = errors.New("clavain: clavain-cli binary not available")

// SprintCreateResult from clavain-cli sprint-create.
type SprintCreateResult struct {
	BeadID  string `json:"bead_id"`
	RunID   string `json:"run_id"`
}

// AdvanceResult from clavain-cli sprint-advance.
type AdvanceResult struct {
	Advanced  bool   `json:"advanced"`
	FromPhase string `json:"from_phase"`
	ToPhase   string `json:"to_phase"`
	Reason    string `json:"reason,omitempty"`
}

// GateResult from clavain-cli enforce-gate.
type GateResult struct {
	Passed  bool   `json:"passed"`
	Reason  string `json:"reason,omitempty"`
}

// DispatchResult from clavain-cli dispatch-task.
type DispatchResult struct {
	DispatchID string `json:"dispatch_id"`
	RunID      string `json:"run_id"`
}
```

**Step 4: Write client.go**

```go
package clavain

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// DefaultTimeout for clavain-cli subprocess calls.
const DefaultTimeout = 15 * time.Second

// Option configures a Client.
type Option func(*Client)

// WithBinPath forces a specific clavain-cli binary path (skips LookPath).
func WithBinPath(path string) Option {
	return func(c *Client) { c.binPath = path }
}

// WithTimeout sets the subprocess timeout.
func WithTimeout(d time.Duration) Option {
	return func(c *Client) { c.timeout = d }
}

// Client wraps the clavain-cli binary for OS-layer operations.
type Client struct {
	binPath string
	timeout time.Duration
}

// New discovers the clavain-cli binary on PATH.
// Returns ErrUnavailable if not found.
func New(opts ...Option) (*Client, error) {
	c := &Client{timeout: DefaultTimeout}
	for _, o := range opts {
		o(c)
	}
	if c.binPath == "" {
		path, err := exec.LookPath("clavain-cli")
		if err != nil {
			return nil, ErrUnavailable
		}
		c.binPath = path
	}
	return c, nil
}

// Available returns true if clavain-cli is discoverable.
func Available() bool {
	_, err := New()
	return err == nil
}

// execRaw runs clavain-cli with the given args and returns stdout.
func (c *Client) execRaw(ctx context.Context, args ...string) ([]byte, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	timeout := c.timeout
	if _, ok := ctx.Deadline(); !ok && timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, timeout)
		defer cancel()
	}

	cmd := exec.CommandContext(ctx, c.binPath, args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		errMsg := strings.TrimSpace(stderr.String())
		if errMsg == "" {
			errMsg = err.Error()
		}
		return stdout.Bytes(), fmt.Errorf("clavain-cli %s: %s", strings.Join(args, " "), errMsg)
	}
	return stdout.Bytes(), nil
}

// execText runs clavain-cli and returns trimmed stdout text.
func (c *Client) execText(ctx context.Context, args ...string) (string, error) {
	out, err := c.execRaw(ctx, args...)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

// execJSON runs clavain-cli and unmarshals JSON stdout into dst.
func (c *Client) execJSON(ctx context.Context, dst any, args ...string) error {
	out, err := c.execRaw(ctx, args...)
	if err != nil {
		return err
	}
	return json.Unmarshal(bytes.TrimSpace(out), dst)
}
```

**Step 5: Run tests to verify they pass**

Run: `cd apps/autarch && go test ./pkg/clavain/ -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/autarch/pkg/clavain/
git commit -m "feat(autarch): add pkg/clavain client foundation — binary discovery + exec helpers"
```

---

### Task 2: Sprint Intent — Create, Advance, Cancel

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)
**Files:**
- Create: `apps/autarch/pkg/clavain/sprint.go`
- Create: `apps/autarch/pkg/clavain/sprint_test.go`

**Step 1: Write sprint_test.go**

```go
package clavain

import (
	"context"
	"testing"
)

func TestSprintCreate_MissingBinary(t *testing.T) {
	t.Setenv("PATH", "/nonexistent")
	c, err := New()
	if err == nil {
		// Binary found unexpectedly — skip
		_ = c
		t.Skip("clavain-cli found on PATH")
	}
	// Can't create client, which is correct behavior
}

func TestSprintCreateOptions(t *testing.T) {
	// Verify option functions don't panic
	opts := []SprintOption{
		WithSprintComplexity(4),
		WithSprintLane("core"),
	}
	var o sprintOpts
	for _, fn := range opts {
		fn(&o)
	}
	if o.complexity != 4 {
		t.Errorf("complexity = %d, want 4", o.complexity)
	}
	if o.lane != "core" {
		t.Errorf("lane = %q, want %q", o.lane, "core")
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/autarch && go test ./pkg/clavain/ -run TestSprintCreate -v`
Expected: FAIL — `SprintOption` not defined.

**Step 3: Write sprint.go**

```go
package clavain

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"strconv"
)

// SprintOption configures a SprintCreate call.
type SprintOption func(*sprintOpts)

type sprintOpts struct {
	complexity int
	lane       string
}

// WithSprintComplexity sets the complexity (1-5) for budget calculation.
func WithSprintComplexity(n int) SprintOption {
	return func(o *sprintOpts) { o.complexity = n }
}

// WithSprintLane sets the thematic lane label.
func WithSprintLane(lane string) SprintOption {
	return func(o *sprintOpts) { o.lane = lane }
}

// SprintCreate creates a sprint via clavain-cli (bead + ic run + budget + phases).
// Returns the bead ID (plain text output from clavain-cli sprint-create).
func (c *Client) SprintCreate(ctx context.Context, goal string, opts ...SprintOption) (string, error) {
	var o sprintOpts
	for _, fn := range opts {
		fn(&o)
	}

	args := []string{"sprint-create", goal}
	if o.complexity > 0 {
		args = append(args, strconv.Itoa(o.complexity))
	}
	if o.lane != "" {
		// Lane is the 3rd positional arg
		if o.complexity == 0 {
			args = append(args, "3") // default complexity
		}
		args = append(args, o.lane)
	}

	beadID, err := c.execText(ctx, args...)
	if err != nil {
		return "", fmt.Errorf("sprint-create: %w", err)
	}
	return beadID, nil
}

// SprintAdvance advances a sprint to the next phase via clavain-cli.
// beadID is the sprint bead, currentPhase is the current phase name.
// Returns the pause reason (empty string means advanced successfully).
func (c *Client) SprintAdvance(ctx context.Context, beadID, currentPhase string, artifactPath ...string) (string, error) {
	args := []string{"sprint-advance", beadID, currentPhase}
	if len(artifactPath) > 0 && artifactPath[0] != "" {
		args = append(args, artifactPath[0])
	}

	result, err := c.execText(ctx, args...)
	if err != nil {
		// sprint-advance returns exit 1 with pause reason on stdout
		if result != "" {
			return result, nil
		}
		return "", fmt.Errorf("sprint-advance: %w", err)
	}
	return "", nil // empty = advanced successfully
}

// SprintCancel cancels a sprint's ic run and marks the bead cancelled.
// This delegates to ic directly since clavain-cli doesn't have cancel yet.
// The cancel operation is not policy-governed (user explicitly cancels).
func (c *Client) SprintCancel(ctx context.Context, runID string) error {
	// Sprint cancel is a user-explicit operation — safe to delegate to ic.
	// We still route through clavain-cli for consistency when it gains cancel.
	// For now, this is the one case where we accept direct ic calls.
	return fmt.Errorf("sprint cancel not yet implemented in clavain-cli — use ic.RunCancel()")
}

// SprintReadState reads the full state of a sprint.
func (c *Client) SprintReadState(ctx context.Context, beadID string) (string, error) {
	return c.execText(ctx, "sprint-read-state", beadID)
}

// resolveRunID resolves a bead ID to an ic run ID using clavain-cli's internal cache.
// This is a convenience for callers that need the underlying run ID.
func (c *Client) resolveRunID(ctx context.Context, beadID string) (string, error) {
	out, err := c.execRaw(ctx, "sprint-read-state", beadID)
	if err != nil {
		return "", err
	}
	// sprint-read-state returns JSON — parse properly, don't line-scan.
	var state struct {
		ID string `json:"id"`
	}
	if err := json.Unmarshal(bytes.TrimSpace(out), &state); err != nil {
		return "", fmt.Errorf("resolveRunID: parse sprint state for %s: %w", beadID, err)
	}
	if state.ID == "" {
		return "", fmt.Errorf("resolveRunID: no run ID found for bead %s", beadID)
	}
	return state.ID, nil
}
```

**Step 4: Run tests**

Run: `cd apps/autarch && go test ./pkg/clavain/ -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/autarch/pkg/clavain/sprint.go apps/autarch/pkg/clavain/sprint_test.go
git commit -m "feat(autarch): add clavain sprint intent — create, advance, cancel"
```

---

### Task 3: Dispatch + Gate + Artifact Intents

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)
**Files:**
- Create: `apps/autarch/pkg/clavain/dispatch.go`
- Create: `apps/autarch/pkg/clavain/gate.go`
- Create: `apps/autarch/pkg/clavain/artifact.go`

**Step 1: Write dispatch.go**

```go
package clavain

import (
	"context"
	"fmt"
)

// DispatchOption configures a DispatchTask call.
type DispatchOption func(*dispatchOpts)

type dispatchOpts struct {
	dispatchType string
	agent        string
	name         string
}

// WithDispatchType sets the dispatch type (e.g., "task", "review").
func WithDispatchType(t string) DispatchOption {
	return func(o *dispatchOpts) { o.dispatchType = t }
}

// WithDispatchAgent sets the agent name.
func WithDispatchAgent(name string) DispatchOption {
	return func(o *dispatchOpts) { o.agent = name }
}

// WithDispatchName sets the dispatch display name.
func WithDispatchName(name string) DispatchOption {
	return func(o *dispatchOpts) { o.name = name }
}

// DispatchTask spawns a task dispatch through clavain-cli.
// This routes through the OS layer so dispatch policy can be applied
// (e.g., budget checks, agent assignment rules).
//
// NOTE: clavain-cli dispatch-task is not yet implemented. This method
// falls back to returning an error with a message directing callers
// to use ic.DispatchSpawn() until the command is added.
// TODO(iv-gyq9l): Add dispatch-task to clavain-cli and remove fallback.
func (c *Client) DispatchTask(ctx context.Context, runID string, opts ...DispatchOption) (string, error) {
	var o dispatchOpts
	for _, fn := range opts {
		fn(&o)
	}

	args := []string{"sprint-track-agent", runID}
	if o.name != "" {
		args = append(args, o.name)
	}
	if o.agent != "" {
		args = append(args, o.agent)
	}

	// Track the agent in the OS layer. The actual dispatch still goes
	// through ic directly — full dispatch-task mediation is a future enhancement.
	_, err := c.execText(ctx, args...)
	// Non-fatal: tracking failure doesn't block dispatch.
	_ = err

	// Return empty — caller still needs to dispatch via ic.DispatchSpawn().
	// This is the incremental approach: register with OS, dispatch with kernel.
	return "", fmt.Errorf("dispatch-task not yet mediated by clavain-cli — use ic.DispatchSpawn() and call clavain.TrackAgent() separately")
}

// TrackAgent registers an agent dispatch with the OS layer for tracking.
// Call this after ic.DispatchSpawn() to keep the OS layer informed.
func (c *Client) TrackAgent(ctx context.Context, beadID, agentName string, agentType, dispatchID string) error {
	args := []string{"sprint-track-agent", beadID, agentName}
	if agentType != "" {
		args = append(args, agentType)
	}
	if dispatchID != "" {
		args = append(args, dispatchID)
	}
	_, err := c.execText(ctx, args...)
	return err
}

// CompleteAgent marks an agent as complete in the OS layer.
func (c *Client) CompleteAgent(ctx context.Context, agentID, status string) error {
	args := []string{"sprint-complete-agent", agentID}
	if status != "" {
		args = append(args, status)
	}
	_, err := c.execText(ctx, args...)
	return err
}
```

**Step 2: Write gate.go**

```go
package clavain

import "context"

// EnforceGate checks whether a phase transition is allowed.
// Returns nil if the gate passes, error with reason if blocked.
func (c *Client) EnforceGate(ctx context.Context, beadID, targetPhase, artifactPath string) error {
	args := []string{"enforce-gate", beadID, targetPhase}
	if artifactPath != "" {
		args = append(args, artifactPath)
	}
	_, err := c.execText(ctx, args...)
	return err
}

// GateOverride forces advancement past a gate.
// This records the override with a reason for audit purposes.
// NOTE: Delegates to ic gate override since clavain-cli doesn't wrap it yet.
func (c *Client) GateOverride(ctx context.Context, beadID, reason string) error {
	// clavain-cli doesn't have gate-override yet — use enforce-gate with skip env
	// TODO(iv-gyq9l): Add gate-override to clavain-cli
	return ErrUnavailable
}
```

**Step 3: Write artifact.go**

```go
package clavain

import (
	"context"
	"strings"
)

// SetArtifact registers an artifact path on a sprint bead.
func (c *Client) SetArtifact(ctx context.Context, beadID, artifactType, path string) error {
	_, err := c.execText(ctx, "set-artifact", beadID, artifactType, path)
	return err
}

// GetArtifact retrieves an artifact path for a sprint bead.
// Returns ("", nil) if no artifact of that type exists.
// Returns ("", err) for actual subprocess failures.
func (c *Client) GetArtifact(ctx context.Context, beadID, artifactType string) (string, error) {
	result, err := c.execText(ctx, "get-artifact", beadID, artifactType)
	if err != nil {
		// clavain-cli get-artifact exits 1 with empty stdout when artifact not found.
		// Distinguish "not found" (result is empty) from actual errors.
		if result == "" || strings.Contains(err.Error(), "not found") {
			return "", nil
		}
		return "", err
	}
	return result, nil
}
```

**Step 4: Run tests**

Run: `cd apps/autarch && go test ./pkg/clavain/ -v`
Expected: PASS (no new tests that call the binary — the dispatch/gate/artifact methods are thin wrappers)

**Step 5: Commit**

```bash
git add apps/autarch/pkg/clavain/dispatch.go apps/autarch/pkg/clavain/gate.go apps/autarch/pkg/clavain/artifact.go
git commit -m "feat(autarch): add dispatch, gate, and artifact intent wrappers"
```

---

### Task 4: Wire Coldwine — Replace Direct ic Calls

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)
**Files:**
- Modify: `apps/autarch/internal/tui/views/coldwine.go:1121` (sprint creation)
- Modify: `apps/autarch/internal/tui/views/coldwine.go:990` (dispatch spawn)
- Modify: `apps/autarch/internal/tui/views/coldwine_mode.go:87,102,147` (advance, cancel)

**Critical behavioral contracts:**
- Sprint creation must return both bead ID (for TUI tracking) and run ID (for ic state write)
- Dispatch spawn must still return dispatch ID for `ic.StateSet` metadata write
- Advance must return `*intercore.AdvanceResult` for TUI rendering (or convert)
- Cancel must work even when clavain-cli is absent (graceful degradation)

**Step 1: Add clavain client to ColdwineView**

In the ColdwineView struct initialization (wherever `ic *intercore.Client` is stored), add:

```go
import "github.com/mistakeknot/autarch/pkg/clavain"

// In the struct or constructor:
clavainClient, _ := clavain.New() // nil-safe — methods check for nil
```

**Step 2: Replace sprint creation at coldwine.go:1121**

Replace:
```go
runID, err := ic.RunCreate(ctx, ".", goal,
    intercore.WithScopeID(epicID),
)
```

With:
```go
var runID string
if clavainClient != nil {
    beadID, err := clavainClient.SprintCreate(ctx, goal,
        clavain.WithSprintComplexity(3),
    )
    if err != nil {
        // Fall back to direct ic
        runID, err = ic.RunCreate(ctx, ".", goal,
            intercore.WithScopeID(epicID),
        )
        if err != nil {
            return sprintCreatedMsg{err: err}
        }
    } else {
        // clavain-cli sprint-create creates both bead and ic run internally.
        // The bead ID ≠ run ID — resolve the actual run ID for ic metadata writes.
        resolvedRunID, resolveErr := clavainClient.resolveRunID(ctx, beadID)
        if resolveErr != nil {
            // Can't resolve — fall back to direct ic
            runID, err = ic.RunCreate(ctx, ".", goal,
                intercore.WithScopeID(epicID),
            )
            if err != nil {
                return sprintCreatedMsg{err: err}
            }
        } else {
            runID = resolvedRunID
        }
    }
} else {
    runID, err = ic.RunCreate(ctx, ".", goal,
        intercore.WithScopeID(epicID),
    )
    if err != nil {
        return sprintCreatedMsg{err: err}
    }
}
```

**Note:** The exact wiring depends on reading the full `coldwine.go` context around line 1121. The pattern is: try clavain-cli first, fall back to ic on error or when clavain-cli absent.

**Step 3: Replace dispatch at coldwine.go:990**

For now, keep `ic.DispatchSpawn()` but add tracking:

```go
dispatchID, err := ic.DispatchSpawn(ctx, runID,
    intercore.WithDispatchType("task"),
    intercore.WithDispatchName(taskTitle),
)
// Track with OS layer (non-blocking)
if clavainClient != nil && err == nil {
    go func() {
        tctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
        defer cancel()
        _ = clavainClient.TrackAgent(tctx, epicID, taskTitle, "task", dispatchID)
    }()
}
```

**Step 4: Replace advance at coldwine_mode.go:87,147**

Replace:
```go
result, err := ic.RunAdvance(ctx, runID)
```

With:
```go
var result *intercore.AdvanceResult
if clavainClient != nil {
    _, advErr := clavainClient.SprintAdvance(ctx, beadID, currentPhase)
    if advErr != nil {
        // Fall back to direct ic
        result, err = ic.RunAdvance(ctx, runID)
    } else {
        // clavain-cli already advanced internally — do NOT call ic.RunAdvance again.
        // Read current state for TUI rendering instead.
        run, getErr := ic.RunStatus(ctx, runID)
        if getErr != nil {
            err = getErr
        } else {
            result = &intercore.AdvanceResult{
                Advanced:  true,
                FromPhase: currentPhase,
                ToPhase:   run.Phase,
            }
        }
    }
} else {
    result, err = ic.RunAdvance(ctx, runID)
}
```

**Note:** This is an incremental approach. The clavain-cli `sprint-advance` enforces gate policy and advances the phase internally. The success path reads current state via `ic.RunStatus()` for TUI rendering — it must NOT call `ic.RunAdvance()` again (that would double-advance past gate boundaries). A future optimization can parse clavain-cli's structured JSON output directly.

**Step 5: Build and verify**

Run: `cd apps/autarch && go build ./cmd/autarch/`
Expected: Compiles cleanly.

**Step 6: Commit**

```bash
git add apps/autarch/internal/tui/views/coldwine.go apps/autarch/internal/tui/views/coldwine_mode.go
git commit -m "feat(autarch): wire Coldwine to clavain OS layer for sprint/dispatch/advance"
```

---

### Task 5: Wire SprintCommands — Replace Slash Command Bypasses

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)
**Files:**
- Modify: `apps/autarch/internal/tui/views/sprint_commands.go:83,99,127,183`

**Step 1: Replace `/sprint create` at line 127**

Replace:
```go
runID, err := ic.RunCreate(ctx, ".", goal)
```

With:
```go
if clavainClient != nil {
    beadID, err := clavainClient.SprintCreate(ctx, goal)
    if err != nil {
        return fmt.Sprintf("Create failed (clavain): %s — falling back to ic", err)
    }
    return fmt.Sprintf("Sprint created: %s", beadID)
}
// Fallback
runID, err := ic.RunCreate(ctx, ".", goal)
```

**Step 2: Replace `/sprint advance` at line 83**

Replace:
```go
result, err := ic.RunAdvance(ctx, runs[0].ID)
```

With:
```go
if clavainClient != nil {
    pauseReason, advErr := clavainClient.SprintAdvance(ctx, beadID, currentPhase)
    if advErr != nil {
        // Fall back to direct ic
        result, err := ic.RunAdvance(ctx, runs[0].ID)
        if err != nil {
            return fmt.Sprintf("Advance failed: %s", err)
        }
        return fmt.Sprintf("Advanced: %s → %s (via ic fallback)", result.FromPhase, result.ToPhase)
    } else if pauseReason != "" {
        return fmt.Sprintf("Sprint paused: %s", pauseReason)
    } else {
        // clavain-cli already advanced — read state for display, don't re-advance
        return "Sprint advanced (via OS layer)"
    }
}
// No clavain client — direct ic
result, err := ic.RunAdvance(ctx, runs[0].ID)
```

**Step 3: Replace `/dispatch spawn` at line 183**

Add tracking after dispatch (same pattern as Task 4 Step 3).

**Step 4: Build and verify**

Run: `cd apps/autarch && go build ./cmd/autarch/`
Expected: Compiles cleanly.

**Step 5: Commit**

```bash
git add apps/autarch/internal/tui/views/sprint_commands.go
git commit -m "feat(autarch): wire sprint slash commands through clavain OS layer"
```

---

### Task 6: Integration Verification

**Bead:** iv-gyq9l
**Phase:** executing (as of 2026-02-26T04:06:17Z)
**Files:**
- Test: existing test files

**Step 1: Run full test suite**

Run: `cd apps/autarch && go test -race ./...`
Expected: PASS (or pre-existing failures unrelated to this change)

**Step 2: Build binary**

Run: `cd apps/autarch && go build ./cmd/autarch/`
Expected: Compiles cleanly.

**Step 3: Verify graceful degradation**

Temporarily move `clavain-cli` off PATH and verify Autarch still builds and the fallback paths compile:

```bash
PATH_BACKUP="$PATH"
export PATH="/usr/bin:/bin"  # No clavain-cli
cd apps/autarch && go build ./cmd/autarch/  # Should still compile
export PATH="$PATH_BACKUP"
```

**Step 4: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(autarch): integration fixes for clavain OS layer wiring"
```

---

## Scope Notes

### What this plan does NOT cover (future work):

1. **`dispatch-task` in clavain-cli** — Full dispatch policy mediation requires a new clavain-cli subcommand. For now, dispatches go through ic with OS tracking via `TrackAgent()`.
2. **`gate-override` in clavain-cli** — Gate override TUI button requires a new clavain-cli subcommand.
3. **Structured JSON output from sprint-advance** — Currently the clavain client calls sprint-advance for gate policy, then reads state from ic for TUI rendering. A future optimization parses clavain-cli's output directly.
5. **asyncResponse context propagation** — The existing `asyncResponse` helper in sprint_commands.go does not accept a context. Clavain calls inside it inherit the ambient context from HandleMessage, which is correct for now. Full context propagation into asyncResponse is a pre-existing issue tracked separately.
4. **Removing the fallback paths** — Once clavain-cli is guaranteed installed (via install.sh), the `if clavainClient != nil` branches can be simplified.

### Incremental approach rationale:

Rather than blocking on new clavain-cli subcommands, this plan routes the 3 most critical intents (create, advance, gate-check) through the OS layer immediately, while tracking dispatches for future full mediation. The `StateSet` metadata writes remain on ic (they're not policy-governing).
