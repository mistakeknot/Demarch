# clavain-cli Go Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Bash clavain-cli dispatcher + lib-sprint.sh (1,360 lines, 40 functions, 62 jq calls) with a Go binary that implements all 28 sprint commands with type-safe arithmetic, table-driven tests, and identical JSON output.

**Architecture:** New Go module at `os/clavain/cmd/clavain-cli/` with flat package structure. The binary calls `ic` and `bd` via subprocess (preserving L1/L2 boundary). Types are duplicated from `apps/autarch/pkg/intercore/types.go` for layer independence. Plain `os.Args` dispatch (no cobra) matching the current case-statement pattern.

**Tech Stack:** Go 1.22+, `os/exec` for subprocess, `encoding/json` for I/O, `testing` for table-driven tests. No external dependencies.

---

## Reference: Current Bash → Go Command Mapping

| Bash function | CLI command | Go file |
|---------------|-------------|---------|
| `sprint_create()` | `sprint-create` | `sprint.go` |
| `sprint_find_active()` | `sprint-find-active` | `sprint.go` |
| `sprint_read_state()` | `sprint-read-state` | `sprint.go` |
| `sprint_budget_remaining()` | `sprint-budget-remaining` | `budget.go` |
| `sprint_budget_total()` | `budget-total` | `budget.go` |
| `sprint_budget_stage()` | `sprint-budget-stage` | `budget.go` |
| `sprint_budget_stage_remaining()` | `sprint-budget-stage-remaining` | `budget.go` |
| `sprint_budget_stage_check()` | `sprint-budget-stage-check` | `budget.go` |
| `sprint_stage_tokens_spent()` | `sprint-stage-tokens-spent` | `budget.go` |
| `sprint_record_phase_tokens()` | `sprint-record-phase-tokens` | `budget.go` |
| `sprint_advance()` | `sprint-advance` | `phase.go` |
| `sprint_next_step()` | `sprint-next-step` | `phase.go` |
| `sprint_should_pause()` | `sprint-should-pause` | `phase.go` |
| `enforce_gate()` | `enforce-gate` | `phase.go` |
| `sprint_set_artifact()` | `set-artifact` | `phase.go` |
| `sprint_record_phase_completion()` | `record-phase` | `phase.go` |
| `advance_phase()` | `advance-phase` | `phase.go` |
| `checkpoint_write()` | `checkpoint-write` | `checkpoint.go` |
| `checkpoint_read()` | `checkpoint-read` | `checkpoint.go` |
| `checkpoint_validate()` | `checkpoint-validate` | `checkpoint.go` |
| `checkpoint_clear()` | `checkpoint-clear` | `checkpoint.go` |
| `checkpoint_completed_steps()` | `checkpoint-completed-steps` | `checkpoint.go` |
| `checkpoint_step_done()` | `checkpoint-step-done` | `checkpoint.go` |
| `sprint_claim()` | `sprint-claim` | `claim.go` |
| `sprint_release()` | `sprint-release` | `claim.go` |
| `bead_claim()` | `bead-claim` | `claim.go` |
| `bead_release()` | `bead-release` | `claim.go` |
| `sprint_classify_complexity()` | `classify-complexity` | `complexity.go` |
| `sprint_complexity_label()` | `complexity-label` | `complexity.go` |
| `sprint_close_children()` | `close-children` | `children.go` |
| `sprint_close_parent_if_done()` | `close-parent-if-done` | `children.go` |
| `sprint_track_agent()` | `sprint-track-agent` | `sprint.go` |
| `sprint_complete_agent()` | `sprint-complete-agent` | `sprint.go` |
| `sprint_invalidate_caches()` | `sprint-invalidate-caches` | `sprint.go` |
| `phase_infer_bead()` | `infer-bead` | `phase.go` |
| (new) | `get-artifact` | `phase.go` |
| (new) | `infer-action` | `phase.go` |

## File Layout

```
os/clavain/cmd/clavain-cli/
├── main.go           # Dispatcher (os.Args case switch)
├── exec.go           # Subprocess helpers (runIC, runBD, runGit)
├── exec_test.go      # Subprocess helper tests
├── types.go          # Duplicated types (Run, BudgetResult, GateResult, etc.)
├── sprint.go         # Sprint CRUD + agent tracking + cache invalidation
├── sprint_test.go    # Sprint CRUD tests
├── budget.go         # Budget math engine (all 7 budget commands)
├── budget_test.go    # Table-driven budget math tests
├── phase.go          # Phase transitions, gates, artifacts, actions
├── phase_test.go     # Phase transition + gate tests
├── checkpoint.go     # Checkpoint read/write/validate/clear
├── checkpoint_test.go # Checkpoint tests
├── claim.go          # Sprint + bead claiming
├── claim_test.go     # Claiming tests
├── complexity.go     # Complexity classification + labels
├── complexity_test.go # Complexity heuristic tests
├── children.go       # Close children/parent
├── children_test.go  # Children management tests
└── go.mod            # Module: github.com/mistakeknot/clavain-cli
```

---

### Task 1: Go Module + Subprocess Helpers + Dispatcher Shell

**Bead:** iv-sevis (F1)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Create: `os/clavain/cmd/clavain-cli/go.mod`
- Create: `os/clavain/cmd/clavain-cli/main.go`
- Create: `os/clavain/cmd/clavain-cli/exec.go`
- Create: `os/clavain/cmd/clavain-cli/exec_test.go`
- Create: `os/clavain/cmd/clavain-cli/types.go`

**Step 1: Initialize Go module**

```bash
mkdir -p os/clavain/cmd/clavain-cli
cd os/clavain/cmd/clavain-cli
go mod init github.com/mistakeknot/clavain-cli
```

**Step 2: Write subprocess helpers and types**

`exec.go` — subprocess wrappers for `ic` and `bd`:

```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

// icBin caches the resolved path to the ic binary.
var icBin string

// findIC locates the ic binary on PATH. Returns error if not found.
func findIC() (string, error) {
	if icBin != "" {
		return icBin, nil
	}
	path, err := exec.LookPath("ic")
	if err != nil {
		path, err = exec.LookPath("intercore")
		if err != nil {
			return "", fmt.Errorf("ic binary not found on PATH")
		}
	}
	icBin = path
	return icBin, nil
}

// runIC executes ic with the given args and returns stdout.
// Pass --json as first arg for JSON mode.
func runIC(args ...string) ([]byte, error) {
	bin, err := findIC()
	if err != nil {
		return nil, err
	}
	cmd := exec.Command(bin, args...)
	cmd.Stderr = os.Stderr
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("ic %s: %w", strings.Join(args, " "), err)
	}
	return bytes.TrimSpace(out), nil
}

// runICJSON executes ic --json <args> and unmarshals the result into dst.
func runICJSON(dst any, args ...string) error {
	fullArgs := append([]string{"--json"}, args...)
	out, err := runIC(fullArgs...)
	if err != nil {
		return err
	}
	return json.Unmarshal(out, dst)
}

// runBD executes bd with the given args and returns stdout.
func runBD(args ...string) ([]byte, error) {
	path, err := exec.LookPath("bd")
	if err != nil {
		return nil, fmt.Errorf("bd binary not found on PATH")
	}
	cmd := exec.Command(path, args...)
	cmd.Stderr = os.Stderr
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("bd %s: %w", strings.Join(args, " "), err)
	}
	return bytes.TrimSpace(out), nil
}

// runGit executes git with the given args and returns stdout.
func runGit(args ...string) ([]byte, error) {
	cmd := exec.Command("git", args...)
	cmd.Stderr = os.Stderr
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("git %s: %w", strings.Join(args, " "), err)
	}
	return bytes.TrimSpace(out), nil
}

// bdAvailable returns true if bd is on PATH.
func bdAvailable() bool {
	_, err := exec.LookPath("bd")
	return err == nil
}

// icAvailable returns true if ic is on PATH and healthy.
func icAvailable() bool {
	bin, err := findIC()
	if err != nil {
		return false
	}
	cmd := exec.Command(bin, "health")
	return cmd.Run() == nil
}
```

`types.go` — duplicated from `apps/autarch/pkg/intercore/types.go` for L2 independence:

```go
package main

// Run represents an Intercore sprint run.
type Run struct {
	ID            string   `json:"id"`
	Goal          string   `json:"goal"`
	Phase         string   `json:"phase"`
	Status        string   `json:"status"`
	ProjectDir    string   `json:"project_dir"`
	ScopeID       string   `json:"scope_id,omitempty"`
	Complexity    int      `json:"complexity"`
	AutoAdvance   bool     `json:"auto_advance"`
	ForceFull     bool     `json:"force_full"`
	TokenBudget   int64    `json:"token_budget,omitempty"`
	BudgetWarnPct int      `json:"budget_warn_pct,omitempty"`
	Phases        []string `json:"phases,omitempty"`
	CreatedAt     int64    `json:"created_at"`
	UpdatedAt     int64    `json:"updated_at"`
}

// BudgetResult from ic run budget.
type BudgetResult struct {
	RunID       string `json:"run_id"`
	TokenBudget int64  `json:"token_budget"`
	TokensUsed  int64  `json:"tokens_used"`
	Exceeded    bool   `json:"exceeded"`
	WarnPct     int    `json:"warn_pct,omitempty"`
}

// GateResult from ic gate check.
type GateResult struct {
	RunID     string        `json:"run_id"`
	FromPhase string        `json:"from_phase"`
	ToPhase   string        `json:"to_phase,omitempty"`
	Result    string        `json:"result"`
	Tier      string        `json:"tier"`
	Evidence  *GateEvidence `json:"evidence,omitempty"`
}

// Passed returns true if the gate check passed.
func (g GateResult) Passed() bool { return g.Result == "pass" }

// GateEvidence contains the individual condition checks.
type GateEvidence struct {
	Conditions []GateCondition `json:"conditions"`
}

// GateCondition is a single gate condition check result.
type GateCondition struct {
	Check  string `json:"check"`
	Phase  string `json:"phase,omitempty"`
	Result string `json:"result"`
	Count  int    `json:"count,omitempty"`
	Detail string `json:"detail,omitempty"`
}

// AdvanceResult from ic run advance.
type AdvanceResult struct {
	Advanced             bool     `json:"advanced"`
	FromPhase            string   `json:"from_phase"`
	ToPhase              string   `json:"to_phase"`
	GateResult           string   `json:"gate_result"`
	GateTier             string   `json:"gate_tier"`
	Reason               string   `json:"reason,omitempty"`
	EventType            string   `json:"event_type"`
	ActiveAgentCount     int      `json:"active_agent_count,omitempty"`
	NextGateRequirements []string `json:"next_gate_requirements,omitempty"`
}

// Artifact from ic run artifact list.
type Artifact struct {
	ID    string `json:"id,omitempty"`
	RunID string `json:"run_id"`
	Phase string `json:"phase"`
	Path  string `json:"path"`
	Type  string `json:"type,omitempty"`
}

// TokenAgg from ic run tokens.
type TokenAgg struct {
	InputTokens  int64 `json:"input_tokens"`
	OutputTokens int64 `json:"output_tokens"`
}

// RunAgent from ic run agent list.
type RunAgent struct {
	ID        string `json:"id"`
	RunID     string `json:"run_id"`
	AgentType string `json:"agent_type"`
	Name      string `json:"name,omitempty"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at,omitempty"`
}

// SprintState is the JSON output of sprint-read-state.
type SprintState struct {
	ID            string            `json:"id"`
	Phase         string            `json:"phase"`
	Artifacts     map[string]string `json:"artifacts"`
	History       map[string]string `json:"history"`
	Complexity    string            `json:"complexity"`
	AutoAdvance   string            `json:"auto_advance"`
	ActiveSession string            `json:"active_session"`
	TokenBudget   int64             `json:"token_budget"`
	TokensSpent   int64             `json:"tokens_spent"`
}

// ActiveSprint is one entry in the sprint-find-active result.
type ActiveSprint struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Phase string `json:"phase"`
	RunID string `json:"run_id"`
}

// Checkpoint is the JSON checkpoint format stored in ic state.
type Checkpoint struct {
	Bead           string   `json:"bead,omitempty"`
	Phase          string   `json:"phase,omitempty"`
	PlanPath       string   `json:"plan_path,omitempty"`
	GitSHA         string   `json:"git_sha,omitempty"`
	UpdatedAt      string   `json:"updated_at,omitempty"`
	CompletedSteps []string `json:"completed_steps,omitempty"`
	KeyDecisions   []string `json:"key_decisions,omitempty"`
}
```

**Step 3: Write the main dispatcher**

`main.go`:

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		printHelp()
		os.Exit(0)
	}

	cmd := os.Args[1]
	args := os.Args[2:]

	var err error
	switch cmd {
	// Sprint CRUD
	case "sprint-create":
		err = cmdSprintCreate(args)
	case "sprint-find-active":
		err = cmdSprintFindActive(args)
	case "sprint-read-state":
		err = cmdSprintReadState(args)

	// Budget
	case "sprint-budget-remaining":
		err = cmdBudgetRemaining(args)
	case "budget-total":
		err = cmdBudgetTotal(args)
	case "sprint-budget-stage":
		err = cmdBudgetStage(args)
	case "sprint-budget-stage-remaining":
		err = cmdBudgetStageRemaining(args)
	case "sprint-budget-stage-check":
		err = cmdBudgetStageCheck(args)
	case "sprint-stage-tokens-spent":
		err = cmdStageTokensSpent(args)
	case "sprint-record-phase-tokens":
		err = cmdRecordPhaseTokens(args)

	// Phase transitions
	case "sprint-advance":
		err = cmdSprintAdvance(args)
	case "sprint-next-step":
		err = cmdSprintNextStep(args)
	case "sprint-should-pause":
		err = cmdSprintShouldPause(args)
	case "enforce-gate":
		err = cmdEnforceGate(args)
	case "advance-phase":
		err = cmdAdvancePhase(args)
	case "record-phase":
		err = cmdRecordPhase(args)
	case "set-artifact":
		err = cmdSetArtifact(args)
	case "get-artifact":
		err = cmdGetArtifact(args)
	case "infer-action":
		err = cmdInferAction(args)
	case "infer-bead":
		err = cmdInferBead(args)

	// Checkpoints
	case "checkpoint-write":
		err = cmdCheckpointWrite(args)
	case "checkpoint-read":
		err = cmdCheckpointRead(args)
	case "checkpoint-validate":
		err = cmdCheckpointValidate(args)
	case "checkpoint-clear":
		err = cmdCheckpointClear(args)
	case "checkpoint-completed-steps":
		err = cmdCheckpointCompletedSteps(args)
	case "checkpoint-step-done":
		err = cmdCheckpointStepDone(args)

	// Claiming
	case "sprint-claim":
		err = cmdSprintClaim(args)
	case "sprint-release":
		err = cmdSprintRelease(args)
	case "bead-claim":
		err = cmdBeadClaim(args)
	case "bead-release":
		err = cmdBeadRelease(args)

	// Complexity
	case "classify-complexity":
		err = cmdClassifyComplexity(args)
	case "complexity-label":
		err = cmdComplexityLabel(args)

	// Children
	case "close-children":
		err = cmdCloseChildren(args)
	case "close-parent-if-done":
		err = cmdCloseParentIfDone(args)

	// Agent tracking
	case "sprint-track-agent":
		err = cmdSprintTrackAgent(args)
	case "sprint-complete-agent":
		err = cmdSprintCompleteAgent(args)
	case "sprint-invalidate-caches":
		err = cmdSprintInvalidateCaches(args)

	case "help", "--help", "-h":
		printHelp()

	default:
		fmt.Fprintf(os.Stderr, "clavain-cli: unknown command '%s'\n", cmd)
		fmt.Fprintf(os.Stderr, "Run 'clavain-cli help' for usage.\n")
		os.Exit(1)
	}

	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func printHelp() {
	fmt.Print(`Usage: clavain-cli <command> [args...]

Gate / Phase:
  advance-phase       <bead_id> <phase> <reason> <artifact_path>
  enforce-gate        <bead_id> <target_phase> <artifact_path>
  infer-bead          <artifact_path>

Sprint State:
  set-artifact        <bead_id> <type> <path>
  record-phase        <bead_id> <phase>
  sprint-advance      <bead_id> <current_phase> [artifact_path]
  sprint-find-active
  sprint-create       <title>
  sprint-claim        <bead_id> <session_id>
  sprint-release      <bead_id>
  sprint-read-state   <bead_id>
  sprint-next-step    <phase>
  sprint-budget-remaining <bead_id>

Budget:
  budget-total            <bead_id>
  sprint-budget-stage     <bead_id> <stage>
  sprint-budget-stage-remaining <bead_id> <stage>
  sprint-budget-stage-check     <bead_id> <stage>
  sprint-stage-tokens-spent     <bead_id> <stage>
  sprint-record-phase-tokens    <bead_id> <phase>

Complexity:
  classify-complexity <bead_id> <description>
  complexity-label    <score>

Children:
  close-children           <bead_id> <reason>
  close-parent-if-done     <bead_id> [reason]

Bead Claiming:
  bead-claim              <bead_id> [session_id]
  bead-release            <bead_id>

Checkpoints:
  checkpoint-write    <bead_id> <phase> <step> <plan_path>
  checkpoint-read
  checkpoint-validate
  checkpoint-clear
  checkpoint-completed-steps
  checkpoint-step-done <step_name>

Agent Tracking:
  sprint-track-agent     <bead_id> <agent_name> [agent_type] [dispatch_id]
  sprint-complete-agent  <agent_id> [status]
  sprint-invalidate-caches
`)
}
```

**Step 4: Write stub functions for all commands**

Create `sprint.go`, `budget.go`, `phase.go`, `checkpoint.go`, `claim.go`, `complexity.go`, `children.go` with stub functions that return `fmt.Errorf("not implemented")`. This ensures the binary compiles and dispatches correctly from day one.

Example `sprint.go`:

```go
package main

import "fmt"

func cmdSprintCreate(args []string) error      { return fmt.Errorf("not implemented") }
func cmdSprintFindActive(args []string) error   { return fmt.Errorf("not implemented") }
func cmdSprintReadState(args []string) error    { return fmt.Errorf("not implemented") }
func cmdSprintTrackAgent(args []string) error   { return fmt.Errorf("not implemented") }
func cmdSprintCompleteAgent(args []string) error { return fmt.Errorf("not implemented") }
func cmdSprintInvalidateCaches(args []string) error { return fmt.Errorf("not implemented") }
```

(Same pattern for all other files.)

**Step 5: Write exec_test.go**

```go
package main

import "testing"

func TestFindIC_NotOnPath(t *testing.T) {
	// Save and clear icBin cache
	old := icBin
	icBin = ""
	defer func() { icBin = old }()

	// With a clean PATH that doesn't have ic, findIC should fail
	t.Setenv("PATH", "/nonexistent")
	_, err := findIC()
	if err == nil {
		t.Error("expected error when ic not on PATH")
	}
}

func TestBDAvailable(t *testing.T) {
	// Just verify it doesn't panic
	_ = bdAvailable()
}

func TestICAvailable(t *testing.T) {
	// Just verify it doesn't panic
	_ = icAvailable()
}
```

**Step 6: Build and verify**

Run: `cd os/clavain/cmd/clavain-cli && go build -o /dev/null .`
Expected: Compiles with no errors.

Run: `cd os/clavain/cmd/clavain-cli && go test -race ./...`
Expected: PASS

**Step 7: Verify help output**

Run: `cd os/clavain/cmd/clavain-cli && go run . help`
Expected: Same help text as current Bash clavain-cli.

Run: `cd os/clavain/cmd/clavain-cli && go run . nonexistent-cmd`
Expected: `clavain-cli: unknown command 'nonexistent-cmd'` on stderr, exit 1.

**Step 8: Commit**

```bash
git add os/clavain/cmd/clavain-cli/
git commit -m "feat(clavain-cli): Go binary scaffold with dispatcher and subprocess helpers"
```

---

### Task 2: Sprint CRUD Commands

**Bead:** iv-sevis (F1)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/sprint.go`
- Create: `os/clavain/cmd/clavain-cli/sprint_test.go`

**Step 1: Write tests for resolveRunID**

```go
package main

import "testing"

func TestResolveRunID_Empty(t *testing.T) {
	_, err := resolveRunID("")
	if err == nil {
		t.Error("expected error for empty bead ID")
	}
}

func TestDefaultBudget(t *testing.T) {
	tests := []struct {
		complexity int
		want       int64
	}{
		{1, 50000},
		{2, 100000},
		{3, 250000},
		{4, 500000},
		{5, 1000000},
		{0, 1000000},  // default
		{99, 1000000}, // default
	}
	for _, tt := range tests {
		got := defaultBudget(tt.complexity)
		if got != tt.want {
			t.Errorf("defaultBudget(%d) = %d, want %d", tt.complexity, got, tt.want)
		}
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd os/clavain/cmd/clavain-cli && go test -run TestDefaultBudget -v`
Expected: FAIL — `resolveRunID` and `defaultBudget` not defined.

**Step 3: Implement sprint.go**

Replace stubs with full implementations matching the Bash functions. Key functions:

- `resolveRunID(beadID string) (string, error)` — calls `bd state <beadID> ic_run_id`, caches result
- `defaultBudget(complexity int) int64` — switch on complexity tier
- `cmdSprintCreate(args)` — creates bd epic + ic run, links them, loads agency specs
- `cmdSprintFindActive(args)` — calls `ic --json run list --active`, enriches with bd titles
- `cmdSprintReadState(args)` — calls `ic --json run status`, `ic run artifact list`, `ic run events`, assembles SprintState JSON
- `cmdSprintTrackAgent(args)` — calls `ic run agent add`
- `cmdSprintCompleteAgent(args)` — calls `ic run agent update`
- `cmdSprintInvalidateCaches(args)` — calls `ic state delete-all discovery_brief`

**Critical behavioral contracts (must match Bash exactly):**
- `sprint-create` outputs the bead ID (not run ID) on stdout as plain text
- `sprint-find-active` outputs `[]` (not error) when ic unavailable
- `sprint-read-state` outputs `{}` (not error) for unknown bead IDs
- All functions are fail-safe (return 0 / empty) except `sprint-claim` which returns 1 on conflict

**Step 4: Run tests to verify they pass**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -v`
Expected: PASS

**Step 5: Commit**

```bash
git add os/clavain/cmd/clavain-cli/sprint.go os/clavain/cmd/clavain-cli/sprint_test.go
git commit -m "feat(clavain-cli): implement Sprint CRUD commands (create, find-active, read-state)"
```

---

### Task 3: Budget Math Engine

**Bead:** iv-udul3 (F2)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/budget.go`
- Create: `os/clavain/cmd/clavain-cli/budget_test.go`

**Step 1: Write table-driven budget math tests**

```go
package main

import "testing"

func TestPhaseCostEstimate(t *testing.T) {
	tests := []struct {
		phase string
		want  int64
	}{
		{"brainstorm", 30000},
		{"brainstorm-reviewed", 15000},
		{"strategized", 25000},
		{"planned", 35000},
		{"plan-reviewed", 50000},
		{"executing", 150000},
		{"shipping", 100000},
		{"reflect", 10000},
		{"done", 5000},
		{"unknown", 30000},
		{"", 30000},
	}
	for _, tt := range tests {
		got := phaseCostEstimate(tt.phase)
		if got != tt.want {
			t.Errorf("phaseCostEstimate(%q) = %d, want %d", tt.phase, got, tt.want)
		}
	}
}

func TestPhaseToStage(t *testing.T) {
	tests := []struct {
		phase string
		want  string
	}{
		{"brainstorm", "discover"},
		{"brainstorm-reviewed", "design"},
		{"strategized", "design"},
		{"planned", "design"},
		{"plan-reviewed", "design"},
		{"executing", "build"},
		{"shipping", "ship"},
		{"reflect", "reflect"},
		{"done", "done"},
		{"garbage", "unknown"},
	}
	for _, tt := range tests {
		got := phaseToStage(tt.phase)
		if got != tt.want {
			t.Errorf("phaseToStage(%q) = %q, want %q", tt.phase, got, tt.want)
		}
	}
}

func TestBudgetRemaining(t *testing.T) {
	tests := []struct {
		budget int64
		spent  int64
		want   int64
	}{
		{250000, 100000, 150000},
		{250000, 250000, 0},
		{250000, 300000, 0}, // clamped to 0
		{0, 0, 0},
		{0, 100, 0},
	}
	for _, tt := range tests {
		got := budgetRemaining(tt.budget, tt.spent)
		if got != tt.want {
			t.Errorf("budgetRemaining(%d, %d) = %d, want %d", tt.budget, tt.spent, got, tt.want)
		}
	}
}

func TestStageAllocation(t *testing.T) {
	tests := []struct {
		total     int64
		sharePct  int
		minTokens int64
		want      int64
	}{
		{250000, 20, 1000, 50000},   // 20% of 250k
		{250000, 50, 1000, 125000},  // 50% of 250k
		{10000, 20, 5000, 5000},     // min_tokens floor
		{0, 20, 1000, 1000},         // zero budget → min_tokens
	}
	for _, tt := range tests {
		got := stageAllocation(tt.total, tt.sharePct, tt.minTokens)
		if got != tt.want {
			t.Errorf("stageAllocation(%d, %d, %d) = %d, want %d",
				tt.total, tt.sharePct, tt.minTokens, got, tt.want)
		}
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd os/clavain/cmd/clavain-cli && go test -run TestBudget -v`
Expected: FAIL — functions not defined.

**Step 3: Implement budget.go**

Key pure functions (no subprocess calls — testable in isolation):

```go
package main

// phaseCostEstimate returns the estimated billing tokens for a phase.
func phaseCostEstimate(phase string) int64 {
	switch phase {
	case "brainstorm":          return 30000
	case "brainstorm-reviewed": return 15000
	case "strategized":         return 25000
	case "planned":             return 35000
	case "plan-reviewed":       return 50000
	case "executing":           return 150000
	case "shipping":            return 100000
	case "reflect":             return 10000
	case "done":                return 5000
	default:                    return 30000
	}
}

// phaseToStage maps sprint phases to macro-stage names.
func phaseToStage(phase string) string {
	switch phase {
	case "brainstorm":
		return "discover"
	case "brainstorm-reviewed", "strategized", "planned", "plan-reviewed":
		return "design"
	case "executing":
		return "build"
	case "shipping":
		return "ship"
	case "reflect":
		return "reflect"
	case "done":
		return "done"
	default:
		return "unknown"
	}
}

// budgetRemaining computes remaining tokens, clamped to >= 0.
func budgetRemaining(budget, spent int64) int64 {
	rem := budget - spent
	if rem < 0 {
		return 0
	}
	return rem
}

// stageAllocation computes the allocated budget for a stage.
func stageAllocation(totalBudget int64, sharePct int, minTokens int64) int64 {
	alloc := totalBudget * int64(sharePct) / 100
	if alloc < minTokens {
		return minTokens
	}
	return alloc
}
```

Then implement the 7 `cmd*` functions that wire these pure functions to subprocess calls (ic run budget, ic state get/set, ic run tokens).

**Critical behavioral contracts:**
- `sprint-budget-remaining` outputs `"0"` (not error) for unknown beads
- `sprint-budget-stage-check` exits 1 (not 0) when exceeded, with `budget_exceeded|<stage>|stage budget depleted` on stderr
- Budget math uses `int64` — never float64

**Step 4: Run tests to verify they pass**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -v`
Expected: PASS

**Step 5: Commit**

```bash
git add os/clavain/cmd/clavain-cli/budget.go os/clavain/cmd/clavain-cli/budget_test.go
git commit -m "feat(clavain-cli): type-safe budget math engine with table-driven tests"
```

---

### Task 4: Phase Transitions + Gate Enforcement

**Bead:** iv-5b6wu (F3)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/phase.go`
- Create: `os/clavain/cmd/clavain-cli/phase_test.go`

**Step 1: Write phase transition tests**

```go
package main

import "testing"

func TestSprintNextStep(t *testing.T) {
	tests := []struct {
		phase string
		want  string
	}{
		{"brainstorm", "strategy"},
		{"brainstorm-reviewed", "strategy"},
		{"strategized", "write-plan"},
		{"planned", "flux-drive"},
		{"plan-reviewed", "work"},
		{"executing", "quality-gates"},
		{"shipping", "reflect"},
		{"reflect", "done"},
		{"done", "done"},
		{"unknown", "brainstorm"},
		{"", "brainstorm"},
	}
	for _, tt := range tests {
		got := nextStep(tt.phase)
		if got != tt.want {
			t.Errorf("nextStep(%q) = %q, want %q", tt.phase, got, tt.want)
		}
	}
}

// Phases is the canonical 9-phase sequence.
func TestPhaseSequence(t *testing.T) {
	phases := []string{
		"brainstorm", "brainstorm-reviewed", "strategized",
		"planned", "plan-reviewed", "executing",
		"shipping", "reflect", "done",
	}
	if len(phases) != 9 {
		t.Fatalf("expected 9 phases, got %d", len(phases))
	}
	// Each phase except "done" must map to a next step
	for _, p := range phases[:8] {
		step := nextStep(p)
		if step == "" {
			t.Errorf("nextStep(%q) returned empty", p)
		}
	}
}
```

**Step 2: Run tests to verify they fail**

Run: `cd os/clavain/cmd/clavain-cli && go test -run TestSprintNextStep -v`
Expected: FAIL

**Step 3: Implement phase.go**

Key functions:
- `nextStep(phase string) string` — static phase→step mapping (fallback table from Bash)
- `cmdSprintNextStep(args)` — first tries kernel action list (ic run action list), then fallback
- `cmdSprintAdvance(args)` — budget check → ic run advance → handle result (advanced/blocked/paused/stale)
- `cmdSprintShouldPause(args)` — gate check, returns structured trigger
- `cmdEnforceGate(args)` — ic gate check + CLAVAIN_SKIP_GATE env var + agency spec gates
- `cmdSetArtifact(args)` — ic run artifact add
- `cmdGetArtifact(args)` — ic run artifact list, filter by type
- `cmdRecordPhase(args)` — invalidate caches
- `cmdAdvancePhase(args)` — advance-phase (legacy gate command)
- `cmdInferAction(args)` — determine next action from sprint state
- `cmdInferBead(args)` — extract bead ID from artifact file frontmatter

**Critical behavioral contracts:**
- `sprint-advance` returns structured pause reasons: `budget_exceeded|<phase>|<detail>`, `gate_blocked|<phase>|<detail>`, `manual_pause|<phase>|auto_advance=false`, `stale_phase|<phase>|<detail>`
- `enforce-gate` respects `CLAVAIN_SKIP_GATE` env var — if set, log the skip reason to stderr and return 0
- `sprint-next-step` returns the step NAME not the command (e.g., "strategy" not "/clavain:strategy")
- All gate enforcement is fail-safe: if ic is unavailable, gates pass (fail-open)

**Step 4: Run tests**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -v`
Expected: PASS

**Step 5: Commit**

```bash
git add os/clavain/cmd/clavain-cli/phase.go os/clavain/cmd/clavain-cli/phase_test.go
git commit -m "feat(clavain-cli): phase transitions, gate enforcement, and artifact tracking"
```

---

### Task 5: Checkpoints

**Bead:** iv-88dwi (F4)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/checkpoint.go`
- Create: `os/clavain/cmd/clavain-cli/checkpoint_test.go`

**Step 1: Write checkpoint tests**

```go
package main

import (
	"encoding/json"
	"testing"
)

func TestCheckpointMarshalRoundTrip(t *testing.T) {
	ckpt := Checkpoint{
		Bead:           "iv-abc",
		Phase:          "planned",
		PlanPath:       "docs/plans/test.md",
		GitSHA:         "abc123",
		UpdatedAt:      "2026-02-25T00:00:00Z",
		CompletedSteps: []string{"brainstorm", "strategy", "plan"},
	}
	data, err := json.Marshal(ckpt)
	if err != nil {
		t.Fatal(err)
	}
	var got Checkpoint
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatal(err)
	}
	if got.Bead != ckpt.Bead {
		t.Errorf("Bead = %q, want %q", got.Bead, ckpt.Bead)
	}
	if len(got.CompletedSteps) != 3 {
		t.Errorf("CompletedSteps len = %d, want 3", len(got.CompletedSteps))
	}
}

func TestCheckpointAddStep_Dedup(t *testing.T) {
	ckpt := Checkpoint{CompletedSteps: []string{"brainstorm"}}
	ckpt = addCompletedStep(ckpt, "brainstorm") // duplicate
	ckpt = addCompletedStep(ckpt, "strategy")
	if len(ckpt.CompletedSteps) != 2 {
		t.Errorf("expected 2 steps after dedup, got %d: %v", len(ckpt.CompletedSteps), ckpt.CompletedSteps)
	}
}
```

**Step 2: Implement checkpoint.go**

Key functions:
- `addCompletedStep(ckpt Checkpoint, step string) Checkpoint` — deduplicated append
- `cmdCheckpointWrite(args)` — reads existing from ic state, merges new step, writes back
- `cmdCheckpointRead(args)` — reads from ic state, falls back to current run
- `cmdCheckpointValidate(args)` — compares git SHA, warns on mismatch (exit 0)
- `cmdCheckpointClear(args)` — removes legacy `.clavain/checkpoint.json` file
- `cmdCheckpointCompletedSteps(args)` — outputs JSON array
- `cmdCheckpointStepDone(args)` — exits 0 if step in list, 1 if not

**Critical:** Checkpoints are stored in ic state (NOT file-based anymore in the current Bash implementation). The Bash `checkpoint_write` calls `intercore_state_set "checkpoint" "$run_id"`. The Go version must match.

**Step 3: Run tests**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -v`
Expected: PASS

**Step 4: Commit**

```bash
git add os/clavain/cmd/clavain-cli/checkpoint.go os/clavain/cmd/clavain-cli/checkpoint_test.go
git commit -m "feat(clavain-cli): checkpoint management (write, read, validate, clear)"
```

---

### Task 6: Sprint + Bead Claiming

**Bead:** iv-88dwi (F4)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/claim.go`
- Create: `os/clavain/cmd/clavain-cli/claim_test.go`

**Step 1: Write claiming tests**

```go
package main

import "testing"

func TestClaimStaleness_Fresh(t *testing.T) {
	// A claim from 30 minutes ago should block
	if isClaimStale(30 * 60) {
		t.Error("30min claim should not be stale")
	}
}

func TestClaimStaleness_Old(t *testing.T) {
	// A claim from 3 hours ago should be stale (threshold: 2h = 7200s)
	if !isClaimStale(3 * 60 * 60) {
		t.Error("3h claim should be stale")
	}
}

func TestClaimStaleness_Boundary(t *testing.T) {
	// Exactly at threshold
	if isClaimStale(7200) {
		t.Error("exactly 2h should not be stale (< check, not <=)")
	}
}
```

**Step 2: Implement claim.go**

Key functions:
- `isClaimStale(ageSeconds int64) bool` — returns true if > 7200s (matching Bash)
- `cmdSprintClaim(args)` — ic lock acquire → check agents → register session → ic lock release → bead_claim
- `cmdSprintRelease(args)` — bead_release → mark session agents completed
- `cmdBeadClaim(args)` — advisory lock via bd set-state claimed_by/claimed_at
- `cmdBeadRelease(args)` — clear bd set-state claimed_by/claimed_at

**Critical behavioral contract:**
- `sprint-claim` returns exit 1 if another active session holds the sprint (< 60 min age for sprint, < 2h for bead)
- `sprint-claim` returns exit 0 if claimed by the same session ID (idempotent)
- `sprint-claim` auto-expires stale sessions (> 60 min) and force-claims

**Step 3: Run tests**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -v`
Expected: PASS

**Step 4: Commit**

```bash
git add os/clavain/cmd/clavain-cli/claim.go os/clavain/cmd/clavain-cli/claim_test.go
git commit -m "feat(clavain-cli): sprint and bead claiming with stale session detection"
```

---

### Task 7: Complexity Classification

**Bead:** iv-uunsq (F5)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/complexity.go`
- Create: `os/clavain/cmd/clavain-cli/complexity_test.go`

**Step 1: Write complexity classification tests**

```go
package main

import "testing"

func TestClassifyComplexity(t *testing.T) {
	tests := []struct {
		desc string
		want int
	}{
		{"", 3},                                                    // empty → default
		{"fix", 3},                                                 // too short (<5 words) → default
		{"rename the variable to something better", 1},             // trivial keyword + short
		{"explore the architecture and investigate tradeoffs for the new system", 5}, // research
		{"add a button to the form", 2},                            // short, simple
		{"implement the authentication system with OAuth2 integration, rate limiting, and session management for multiple providers", 4}, // long
	}
	for _, tt := range tests {
		got := classifyComplexity(tt.desc)
		if got != tt.want {
			t.Errorf("classifyComplexity(%q) = %d, want %d", tt.desc, got, tt.want)
		}
	}
}

func TestComplexityLabel(t *testing.T) {
	tests := []struct {
		score int
		want  string
	}{
		{1, "trivial"},
		{2, "simple"},
		{3, "moderate"},
		{4, "complex"},
		{5, "research"},
		{0, "moderate"},  // out of range → default
		{99, "moderate"}, // out of range → default
	}
	for _, tt := range tests {
		got := complexityLabel(tt.score)
		if got != tt.want {
			t.Errorf("complexityLabel(%d) = %q, want %q", tt.score, got, tt.want)
		}
	}
}
```

**Step 2: Implement complexity.go**

Port the Bash heuristics to Go:
- `classifyComplexity(desc string) int` — word count tiers, trivial/research/ambiguity/simplicity signals
- `complexityLabel(score int) string` — score to label mapping
- `cmdClassifyComplexity(args)` — checks ic/bd for manual override first, then falls back to heuristic
- `cmdComplexityLabel(args)` — simple mapping

**Step 3: Run tests**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -run TestClassify -v`
Expected: PASS

**Step 4: Commit**

```bash
git add os/clavain/cmd/clavain-cli/complexity.go os/clavain/cmd/clavain-cli/complexity_test.go
git commit -m "feat(clavain-cli): complexity classification heuristics ported from Bash"
```

---

### Task 8: Children Management

**Bead:** iv-uunsq (F5)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/cmd/clavain-cli/children.go`
- Create: `os/clavain/cmd/clavain-cli/children_test.go`

**Step 1: Implement children.go**

- `cmdCloseChildren(args)` — `bd show <epic_id>`, parse BLOCKS section for open children, `bd close` each, then call `cmdCloseParentIfDone`
- `cmdCloseParentIfDone(args)` — `bd show <bead_id>`, parse PARENT section, check if all children closed, close parent if so

**Parsing bd show output:** The Go implementation parses bd's structured text output (same as Bash awk/grep). This is fragile but matches the current contract. Alternative: if `bd show --json` is available, use that instead.

```go
// parseBlockedIDs extracts open bead IDs from the BLOCKS section of bd show output.
func parseBlockedIDs(bdShowOutput string) []string { ... }

// parseParentID extracts the parent bead ID from the PARENT section of bd show output.
func parseParentID(bdShowOutput string) string { ... }

// countOpenChildren counts ↳ ○ and ↳ ◐ lines in the CHILDREN section.
func countOpenChildren(bdShowOutput string) int { ... }
```

**Step 2: Write tests for parsing helpers**

```go
func TestParseBlockedIDs(t *testing.T) {
	output := `BLOCKS
  ← ○ iv-abc: Some open task
  ← ✓ iv-def: Some closed task
  ← ○ iv-ghi: Another open one

CHILDREN`
	ids := parseBlockedIDs(output)
	if len(ids) != 2 {
		t.Errorf("expected 2 open blocked IDs, got %d: %v", len(ids), ids)
	}
}
```

**Step 3: Run tests**

Run: `cd os/clavain/cmd/clavain-cli && go test -race -v`
Expected: PASS

**Step 4: Commit**

```bash
git add os/clavain/cmd/clavain-cli/children.go os/clavain/cmd/clavain-cli/children_test.go
git commit -m "feat(clavain-cli): close-children and close-parent-if-done with bd output parsing"
```

---

### Task 9: Integration Test Harness

**Bead:** iv-uunsq (F5)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Create: `os/clavain/tests/shell/test_go_cli_compat.bats`

**Step 1: Write BATS integration tests comparing Go vs Bash output**

```bash
#!/usr/bin/env bats
# Integration tests: verify Go clavain-cli produces identical output to Bash version.
# Requires: ic binary built, bd available, temp DB per test.

setup() {
    export TMPDIR="$(mktemp -d)"
    export IC_DB="$TMPDIR/ic.db"
    ic init --db "$IC_DB" 2>/dev/null || true

    GO_CLI="$(cd "$BATS_TEST_DIRNAME/../../cmd/clavain-cli" && go build -o "$TMPDIR/clavain-cli-go" . && echo "$TMPDIR/clavain-cli-go")"
    BASH_CLI="$BATS_TEST_DIRNAME/../../bin/clavain-cli"
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "help output matches" {
    go_help=$("$GO_CLI" help 2>&1)
    bash_help=$("$BASH_CLI" help 2>&1)
    # Compare first 10 lines (structure match, not byte-identical)
    [ "$(echo "$go_help" | head -1)" = "$(echo "$bash_help" | head -1)" ]
}

@test "unknown command exits 1" {
    run "$GO_CLI" nonexistent-cmd
    [ "$status" -eq 1 ]
    [[ "$output" == *"unknown command"* ]]
}

@test "complexity-label matches" {
    for score in 1 2 3 4 5; do
        go_out=$("$GO_CLI" complexity-label "$score")
        bash_out=$("$BASH_CLI" complexity-label "$score")
        [ "$go_out" = "$bash_out" ]
    done
}

@test "sprint-next-step matches all phases" {
    for phase in brainstorm brainstorm-reviewed strategized planned plan-reviewed executing shipping reflect done; do
        go_out=$("$GO_CLI" sprint-next-step "$phase")
        bash_out=$("$BASH_CLI" sprint-next-step "$phase")
        [ "$go_out" = "$bash_out" ]
    done
}

@test "sprint-find-active returns JSON array when no sprints" {
    go_out=$("$GO_CLI" sprint-find-active 2>/dev/null)
    [ "$go_out" = "[]" ]
}
```

**Step 2: Run integration tests**

Run: `cd os/clavain && bats tests/shell/test_go_cli_compat.bats`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add os/clavain/tests/shell/test_go_cli_compat.bats
git commit -m "test(clavain-cli): BATS integration tests for Go/Bash output compatibility"
```

---

### Task 10: Bash Shim + Plugin Build Integration

**Bead:** iv-uunsq (F5)
**Phase:** planned (as of 2026-02-26T00:40:25Z)
**Files:**
- Modify: `os/clavain/bin/clavain-cli` (replace with thin shim)
- Modify: `os/clavain/plugin.json` (if it has a build step section)
- Create: `os/clavain/scripts/build-clavain-cli.sh`

**Step 1: Write the build script**

```bash
#!/usr/bin/env bash
# Build the Go clavain-cli binary. Called by plugin.json build step.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/../cmd/clavain-cli"
OUT_DIR="$SCRIPT_DIR/../bin"

if ! command -v go &>/dev/null; then
    echo "clavain-cli: Go not found — using Bash fallback" >&2
    exit 0
fi

echo "Building clavain-cli Go binary..." >&2
go build -C "$SRC_DIR" -mod=readonly -o "$OUT_DIR/clavain-cli-go" .
echo "clavain-cli-go built at $OUT_DIR/clavain-cli-go" >&2
```

**Step 2: Write the thin Bash shim**

Replace `os/clavain/bin/clavain-cli` with:

```bash
#!/usr/bin/env bash
# clavain-cli — thin shim. Delegates to Go binary if available, falls back to Bash.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GO_BIN="$SCRIPT_DIR/clavain-cli-go"

# Try Go binary first
if [[ -x "$GO_BIN" ]]; then
    exec "$GO_BIN" "$@"
fi

# Auto-build if Go is available
if command -v go &>/dev/null && [[ -d "$SCRIPT_DIR/../cmd/clavain-cli" ]]; then
    if go build -C "$SCRIPT_DIR/../cmd/clavain-cli" -mod=readonly -o "$GO_BIN" . 2>/dev/null; then
        exec "$GO_BIN" "$@"
    fi
fi

# Fall back to Bash implementation
HOOKS_DIR="$(dirname "$SCRIPT_DIR")/hooks"
export SPRINT_LIB_PROJECT_DIR="${SPRINT_LIB_PROJECT_DIR:-.}"
export GATES_PROJECT_DIR="${GATES_PROJECT_DIR:-.}"
source "${HOOKS_DIR}/lib-sprint.sh"
source "${HOOKS_DIR}/lib-gates.sh"

case "${1:-help}" in
    advance-phase)       shift; advance_phase "$@" ;;
    enforce-gate)        shift; enforce_gate "$@" ;;
    infer-bead)          shift; phase_infer_bead "$@" ;;
    set-artifact)        shift; sprint_set_artifact "$@" ;;
    record-phase)        shift; sprint_record_phase_completion "$@" ;;
    sprint-advance)      shift; sprint_advance "$@" ;;
    sprint-find-active)  shift; sprint_find_active "$@" ;;
    sprint-create)       shift; sprint_create "$@" ;;
    sprint-claim)        shift; sprint_claim "$@" ;;
    sprint-release)      shift; sprint_release "$@" ;;
    sprint-read-state)   shift; sprint_read_state "$@" ;;
    sprint-next-step)    shift; sprint_next_step "$@" ;;
    sprint-budget-remaining) shift; sprint_budget_remaining "$@" ;;
    classify-complexity) shift; sprint_classify_complexity "$@" ;;
    complexity-label)    shift; sprint_complexity_label "$@" ;;
    close-children)      shift; sprint_close_children "$@" ;;
    close-parent-if-done) shift; sprint_close_parent_if_done "$@" ;;
    bead-claim)          shift; bead_claim "$@" ;;
    bead-release)        shift; bead_release "$@" ;;
    checkpoint-write)    shift; checkpoint_write "$@" ;;
    checkpoint-read)     shift; checkpoint_read "$@" ;;
    checkpoint-validate) shift; checkpoint_validate "$@" ;;
    checkpoint-clear)    shift; checkpoint_clear "$@" ;;
    help|--help|-h)
        if [[ -x "$GO_BIN" ]]; then "$GO_BIN" help; else cat <<'HELP'
Usage: clavain-cli <command> [args...] (Bash fallback mode)
Run with Go binary for full command list.
HELP
        fi
        ;;
    *)
        echo "clavain-cli: unknown command '${1}'" >&2
        echo "Run 'clavain-cli help' for usage." >&2
        exit 1
        ;;
esac
```

**Step 3: Verify shim works**

Run: `os/clavain/bin/clavain-cli help`
Expected: Go binary help (if built) or Bash fallback help.

Run: `os/clavain/bin/clavain-cli complexity-label 3`
Expected: `moderate`

**Step 4: Measure latency improvement**

```bash
# Bash path (force fallback by temporarily moving Go binary)
time for i in $(seq 20); do os/clavain/bin/clavain-cli complexity-label 3 >/dev/null; done

# Go path
time for i in $(seq 20); do os/clavain/bin/clavain-cli-go complexity-label 3 >/dev/null; done
```

Document results in a comment on the PR.

**Step 5: Commit**

```bash
git add os/clavain/bin/clavain-cli os/clavain/scripts/build-clavain-cli.sh
git commit -m "feat(clavain-cli): thin Bash shim with Go binary auto-build fallback"
```

---

## Dependency Graph

```
Task 1 (scaffold)
  ├─→ Task 2 (Sprint CRUD)
  ├─→ Task 3 (budget math)
  ├─→ Task 4 (phase transitions)
  ├─→ Task 5 (checkpoints)
  ├─→ Task 6 (claiming)
  └─→ Task 7 (complexity)

Task 4 ─→ Task 8 (children, uses phaseToStage)

Tasks 2-8 ─→ Task 9 (integration tests)
Tasks 2-8 ─→ Task 10 (shim + build)
```

Tasks 2-7 are **independent** once Task 1 is complete. They can be executed in parallel.
Tasks 9-10 depend on all commands being implemented.
