# Intercore Phase Chain and Gate Rules Research

**Date:** 2026-02-22  
**Status:** Complete  
**Source Files:**
- `/home/mk/projects/Demarch/core/intercore/internal/phase/phase.go` (phase constants, DefaultPhaseChain, phase validation)
- `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go` (gate rules, gate checks, evidence)
- `/home/mk/projects/Demarch/core/intercore/cmd/ic/run.go` (CLI phase handling)
- `/home/mk/projects/Demarch/os/clavain/hooks/lib-sprint.sh` (OS→kernel integration)
- `/home/mk/projects/Demarch/os/clavain/config/agency-spec.yaml` (spec-level gates)

---

## 1. DefaultPhaseChain — The Kernel's 9-Phase Lifecycle

**Location:** `/home/mk/projects/Demarch/core/intercore/internal/phase/phase.go:67`

### Phase Constants (defined at phase.go:10)
```go
const (
	PhaseBrainstorm         = "brainstorm"
	PhaseBrainstormReviewed = "brainstorm-reviewed"
	PhaseStrategized        = "strategized"
	PhasePlanned            = "planned"
	PhaseExecuting          = "executing"
	PhaseReview             = "review"
	PhasePolish             = "polish"
	PhaseReflect            = "reflect"
	PhaseDone               = "done"
)
```

### DefaultPhaseChain Definition (phase.go:67)
```go
// DefaultPhaseChain is the 9-phase Clavain lifecycle.
// Used when a run has no explicit phases column (NULL in DB).
var DefaultPhaseChain = []string{
	PhaseBrainstorm,           // 0: brainstorm
	PhaseBrainstormReviewed,   // 1: brainstorm-reviewed
	PhaseStrategized,          // 2: strategized
	PhasePlanned,              // 3: planned
	PhaseExecuting,            // 4: executing
	PhaseReview,               // 5: review
	PhasePolish,               // 6: polish
	PhaseReflect,              // 7: reflect
	PhaseDone,                 // 8: done
}
```

**Key Point:** This is the **canonical kernel phase chain**. Custom phase chains can be passed via `ic run create --phases='[...]'`, but they must follow strict validation rules (see below).

---

## 2. Gate Rules — Which Transitions Require Checks

**Location:** `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go:95-119`

### Gate Check Types (gate.go:13)
```go
const (
	CheckArtifactExists      = "artifact_exists"      // Counts artifacts for a phase
	CheckAgentsComplete      = "agents_complete"      // Verifies 0 active agents
	CheckVerdictExists       = "verdict_exists"       // Checks for passing dispatch verdict
	CheckChildrenAtPhase     = "children_at_phase"    // Portfolio run validation
	CheckUpstreamsAtPhase    = "upstreams_at_phase"   // Dependency validation
	CheckBudgetNotExceeded   = "budget_not_exceeded"  // Token budget checks
)
```

### Gate Rules Table (gate.go:95-119)
```go
var gateRules = map[[2]string][]gateRule{
	// brainstorm → brainstorm-reviewed: Must have brainstorm artifacts
	{PhaseBrainstorm, PhaseBrainstormReviewed}: {
		{check: CheckArtifactExists, phase: PhaseBrainstorm},
	},
	// brainstorm-reviewed → strategized: Must have brainstorm-reviewed artifacts
	{PhaseBrainstormReviewed, PhaseStrategized}: {
		{check: CheckArtifactExists, phase: PhaseBrainstormReviewed},
	},
	// strategized → planned: Must have strategized artifacts
	{PhaseStrategized, PhasePlanned}: {
		{check: CheckArtifactExists, phase: PhaseStrategized},
	},
	// planned → executing: Must have planned artifacts
	{PhasePlanned, PhaseExecuting}: {
		{check: CheckArtifactExists, phase: PhasePlanned},
	},
	// executing → review: All agents must complete (0 active agents)
	{PhaseExecuting, PhaseReview}: {
		{check: CheckAgentsComplete},
	},
	// review → polish: Must have passing verdict from dispatch
	{PhaseReview, PhasePolish}: {
		{check: CheckVerdictExists},
	},
	// polish → reflect: NO GATE (pass-through transition)
	// (No entry in map = no requirements)
	
	// reflect → done: Soft gate — must have reflect artifacts
	{PhaseReflect, PhaseDone}: {
		{check: CheckArtifactExists, phase: PhaseReflect},
	},
}
```

### Gate Check Implementations (gate.go:170-240)

#### CheckArtifactExists
```go
case CheckArtifactExists:
	if rt == nil {
		cond.Result = GateFail
		cond.Detail = "no runtrack querier provided"
		allPass = false
		break
	}
	count, qerr := rt.CountArtifacts(ctx, run.ID, rule.phase)
	if qerr != nil {
		return "", "", nil, fmt.Errorf("gate check: %w", qerr)
	}
	cond.Count = &count
	if count > 0 {
		cond.Result = GatePass
	} else {
		cond.Result = GateFail
		cond.Detail = fmt.Sprintf("no artifacts found for phase %q", rule.phase)
		allPass = false
	}
```
**Logic:** Calls `runtrack.CountArtifacts(ctx, runID, phase)`. Pass if count > 0. Count is returned in evidence.

#### CheckAgentsComplete
```go
case CheckAgentsComplete:
	if rt == nil {
		cond.Result = GateFail
		cond.Detail = "no runtrack querier provided"
		allPass = false
		break
	}
	count, qerr := rt.CountActiveAgents(ctx, run.ID)
	if qerr != nil {
		return "", "", nil, fmt.Errorf("gate check: %w", qerr)
	}
	cond.Count = &count
	if count == 0 {
		cond.Result = GatePass
	} else {
		cond.Result = GateFail
		cond.Detail = fmt.Sprintf("%d agents still active", count)
		allPass = false
	}
```
**Logic:** Calls `runtrack.CountActiveAgents(ctx, runID)`. Pass if count == 0 (all agents finished). Fail detail shows how many agents remain.

#### CheckVerdictExists
```go
case CheckVerdictExists:
	if vq == nil {
		cond.Result = GateFail
		cond.Detail = "no verdict querier provided"
		allPass = false
		break
	}
	scopeID := ""
	if run.ScopeID != nil {
		scopeID = *run.ScopeID
	}
	has, qerr := vq.HasVerdict(ctx, scopeID)
	if qerr != nil {
		return "", "", nil, fmt.Errorf("gate check: %w", qerr)
	}
	if has {
		cond.Result = GatePass
	} else {
		cond.Result = GateFail
		cond.Detail = "no passing verdict found"
		allPass = false
	}
```
**Logic:** Calls `dispatch.HasVerdict(ctx, scopeID)` where scopeID is the run's ScopeID. Pass if a verdict exists, fail with "no passing verdict found" otherwise.

---

## 3. How the OS Passes Phase Chain to Kernel

**Location:** `/home/mk/projects/Demarch/os/clavain/hooks/lib-sprint.sh:134-145`

### Sprint Create → IC Run Create Call
```bash
# Create ic run (required — this is the state backend)
local phases_json='["brainstorm","brainstorm-reviewed","strategized","planned","plan-reviewed","executing","shipping","reflect","done"]'
local complexity="${2:-3}"
local token_budget
token_budget=$(_sprint_default_budget "$complexity")

# Default phase actions for kernel-driven routing (matches sprint_next_step fallback table)
# Keys = phase where you ARE, values = command to run at that phase
# Args is a string containing a JSON array (ic CLI expects *string, not raw array)
local default_actions='{"brainstorm":{"command":"/clavain:strategy","mode":"interactive"},"strategized":{"command":"/clavain:write-plan","mode":"interactive"},"planned":{"command":"/interflux:flux-drive","args":"[\"${artifact:plan}\"]","mode":"interactive"},"plan-reviewed":{"command":"/clavain:work","args":"[\"${artifact:plan}\"]","mode":"both"},"executing":{"command":"/clavain:quality-gates","mode":"interactive"},"shipping":{"command":"/clavain:reflect","mode":"interactive"}}'

local run_id
run_id=$(intercore_run_create "$(pwd)" "$title" "$phases_json" "$scope_id" "$complexity" "$token_budget" "$default_actions") || run_id=""
```

### intercore_run_create Wrapper Function (lib-intercore.sh:236-245)
```bash
# intercore_run_create — Create a new ic run.
# Args: $1=project_dir, $2=goal, $3=phases_json, $4=scope_id (optional),
#       $5=complexity (optional, default 3), $6=token_budget (optional),
#       $7=actions_json (optional, e.g. '{"planned":{"command":"/clavain:work","mode":"interactive"}}')
# Prints: run ID to stdout
# Returns: 0 on success, 1 on failure
intercore_run_create() {
    local project="$1" goal="$2" phases_json="$3" scope_id="${4:-}" complexity="${5:-3}" token_budget="${6:-}" actions_json="${7:-}"
    if ! intercore_available; then return 1; fi
    local args=(run create --project="$project" --goal="$goal" --complexity="$complexity")
    [[ -n "$phases_json" ]] && args+=(--phases="$phases_json")
    [[ -n "$scope_id" ]] && args+=(--scope-id="$scope_id")
    [[ -n "$token_budget" ]] && args+=(--token-budget="$token_budget")
    [[ -n "$actions_json" ]] && args+=(--actions="$actions_json")
    "$INTERCORE_BIN" "${args[@]}" ${INTERCORE_DB:+--db="$INTERCORE_DB"} 2>/dev/null
}
```

### Actual IC CLI Invocation (cmd/ic/run.go:96-97)
```go
case strings.HasPrefix(args[i], "--phases="):
	phasesJSON = strings.TrimPrefix(args[i], "--phases=")
```

**Execution Flow:**
1. OS calls `sprint_create(title, complexity)`
2. `sprint_create()` constructs a phases JSON array (see below)
3. Calls `intercore_run_create $(pwd) "$title" "$phases_json" ...`
4. `intercore_run_create()` builds an arg array with `--phases="$phases_json"`
5. Invokes: `ic run create --project=... --goal=... --phases='["brainstorm",...,"done"]' ...`
6. IC CLI parses the JSON string and validates it with `ParsePhaseChain()`

---

## 4. The "plan-reviewed" Phase — OS Custom Phase Not in Kernel

**CRITICAL DISCOVERY:** The OS passes a 9-phase chain that includes **`plan-reviewed`**, but the kernel's DefaultPhaseChain only has 9 phases: **brainstorm** → **brainstorm-reviewed** → **strategized** → **planned** → **executing** → **review** → **polish** → **reflect** → **done**.

### OS Phase Chain (lib-sprint.sh:134)
```json
["brainstorm","brainstorm-reviewed","strategized","planned","plan-reviewed","executing","shipping","reflect","done"]
```

### Kernel DefaultPhaseChain (phase.go:67)
```go
[]string{
	"brainstorm",
	"brainstorm-reviewed",
	"strategized",
	"planned",
	"executing",           // OS skips directly from "planned" to "executing"
	"review",              // Kernel expects this, but OS doesn't include it
	"polish",              // Kernel expects this, but OS doesn't include it
	"reflect",
	"done",
}
```

### Phase Mapping Mismatch
| Step | Kernel Phase | OS Phase |
|------|--------------|----------|
| 0 | brainstorm | brainstorm |
| 1 | brainstorm-reviewed | brainstorm-reviewed |
| 2 | strategized | strategized |
| 3 | planned | planned |
| 4 | executing | **plan-reviewed** (custom) |
| 5 | review | executing |
| 6 | polish | **shipping** (custom) |
| 7 | reflect | reflect |
| 8 | done | done |

### OS Custom Phases
- **`plan-reviewed`** (index 4 in OS chain)
  - Mapped in `agency-spec.yaml` with gate `plan_reviewed` of type `artifact_reviewed`
  - Has phase actions: `{"plan-reviewed":{"command":"/clavain:work","args":"[\"${artifact:plan}\"]","mode":"both"}}`
  - See agency-spec.yaml lines 57, 76-78, 132
  
- **`shipping`** (index 6 in OS chain)
  - Replaces kernel's "review" + "polish" phases
  - Has phase actions: `{"shipping":{"command":"/clavain:reflect","mode":"interactive"}}`

### How This Works
The kernel's `ParsePhaseChain()` function (phase.go:79-102) accepts **any** phase name that matches `[a-zA-Z0-9_-]+`. It does NOT validate against the constants. This means:

1. OS can pass custom phase names like `"plan-reviewed"` and `"shipping"`
2. Kernel stores them as-is in the run's `phases` column
3. When OS calls `ic run advance`, the kernel uses the **run's custom phases** for transitions (via `ChainNextPhase()`)
4. Gate rules are looked up by (from, to) tuples in the `gateRules` map
5. If a custom transition like `(planned, plan-reviewed)` isn't in the map, **no gate applies** (pass-through)

---

## 5. Phase Validation Rules

**Location:** `/home/mk/projects/Demarch/core/intercore/internal/phase/phase.go:79-102`

```go
// ParsePhaseChain parses and validates a JSON phase chain.
// Returns error if: not valid JSON array, fewer than 2 phases, or contains duplicates.
func ParsePhaseChain(jsonStr string) ([]string, error) {
	if jsonStr == "" {
		return nil, fmt.Errorf("parse phase chain: empty string")
	}
	var chain []string
	if err := json.Unmarshal([]byte(jsonStr), &chain); err != nil {
		return nil, fmt.Errorf("parse phase chain: %w", err)
	}
	if len(chain) < 2 {
		return nil, fmt.Errorf("parse phase chain: need at least 2 phases, got %d", len(chain))
	}
	seen := make(map[string]bool, len(chain))
	for _, p := range chain {
		if p == "" || !isValidPhaseName(p) {
			return nil, fmt.Errorf("parse phase chain: invalid phase name %q (must match [a-zA-Z0-9_-]+)", p)
		}
		if seen[p] {
			return nil, fmt.Errorf("parse phase chain: duplicate phase %q", p)
		}
		seen[p] = true
	}
	return chain, nil
}
```

### Validation Constraints
1. Must be valid JSON array
2. Must have at least 2 phases
3. Each phase name must match `[a-zA-Z0-9_-]+` (lowercase, digits, hyphens, underscores)
4. No duplicate phase names
5. **No validation against phase constants** — custom phases are allowed

---

## 6. GateRulesInfo() — Display Function

**Location:** `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go:400-443`

This function returns gate rules in order for display (e.g., `ic gate rules`):

```go
// GateRulesInfo returns a list of all gate rules for display purposes.
func GateRulesInfo() []struct {
	From   string
	To     string
	Checks []struct {
		Check string
		Phase string
	}
} {
	var rules []struct {
		From   string
		To     string
		Checks []struct {
			Check string
			Phase string
		}
	}

	// Iterate in phase order for deterministic output
	for i := 0; i < len(DefaultPhaseChain)-1; i++ {
		from := DefaultPhaseChain[i]
		to := DefaultPhaseChain[i+1]
		gr, ok := gateRules[[2]string{from, to}]
		if !ok {
			continue
		}
		entry := struct {
			From   string
			To     string
			Checks []struct {
				Check string
				Phase string
			}
		}{From: from, To: to}
		for _, r := range gr {
			entry.Checks = append(entry.Checks, struct {
				Check string
				Phase string
			}{Check: r.check, Phase: r.phase})
		}
		rules = append(rules, entry)
	}
	return rules
}
```

**Output Order:** Iterates through DefaultPhaseChain, looks up rules for consecutive transitions, returns only transitions with gates. **Note:** This only reports gates for the kernel's DefaultPhaseChain, not custom phase chains.

---

## 7. Gate Evaluation Logic

**Location:** `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go:121-365`

### Public Entry Point (gate.go:365-397)
```go
// EvaluateGate performs a dry-run gate check for the next transition.
// This is the public entry point used by `ic gate check`.
func EvaluateGate(ctx context.Context, store *Store, runID string, cfg GateConfig, rt RuntrackQuerier, vq VerdictQuerier, pq PortfolioQuerier, dq DepQuerier, bq BudgetQuerier) (*GateCheckResult, error) {
	run, err := store.Get(ctx, runID)
	if err != nil {
		return nil, err
	}

	// Determine next phase
	toPhase, err := ChainNextPhase(run.Phases, run.Phase)
	if err != nil {
		return nil, fmt.Errorf("evaluate gate: %w", err)
	}

	// Evaluate gate for the transition
	result, tier, evidence, err := evaluateGate(ctx, run, cfg, run.Phase, toPhase, rt, vq, pq, dq, bq)
	if err != nil {
		return nil, fmt.Errorf("evaluate gate: %w", err)
	}

	return &GateCheckResult{
		RunID:     runID,
		FromPhase: run.Phase,
		ToPhase:   toPhase,
		Result:    result,
		Tier:      tier,
		Evidence:  evidence,
	}, nil
}
```

### Internal Gate Evaluation (gate.go:121-340)
The `evaluateGate()` function:
1. Fetches the rule for (run.Phase, toPhase) from the `gateRules` map
2. If no rule exists, result is `GateNone` (no gate to check)
3. For each rule, evaluates the check (artifact_exists, agents_complete, verdict_exists, etc.)
4. Collects evidence for each condition
5. All checks must pass for the gate to pass
6. Returns (result, tier, evidence, error)

---

## 8. Summary Table — All Gates in Kernel DefaultPhaseChain

| From | To | Gate Check | Details |
|------|-----|-----------|---------|
| brainstorm | brainstorm-reviewed | CheckArtifactExists | Must have brainstorm artifacts |
| brainstorm-reviewed | strategized | CheckArtifactExists | Must have brainstorm-reviewed artifacts |
| strategized | planned | CheckArtifactExists | Must have strategized artifacts |
| planned | executing | CheckArtifactExists | Must have planned artifacts |
| executing | review | CheckAgentsComplete | All agents must complete (count == 0) |
| review | polish | CheckVerdictExists | Must have passing verdict from dispatch |
| polish | reflect | (none) | Pass-through, no gate |
| reflect | done | CheckArtifactExists | Must have reflect artifacts |

---

## 9. Key Findings

1. **DefaultPhaseChain is kernel-local:** Defined in `phase.go` as the standard 9-phase lifecycle. Custom chains override it.

2. **Phase names are not validated:** The kernel accepts any phase name matching `[a-zA-Z0-9_-]+`. The OS leverages this to define custom phases like `plan-reviewed` and `shipping`.

3. **Gates are transition-based:** Defined by (from, to) tuples. If a transition isn't in `gateRules`, it has no gate (pass-through).

4. **OS-Kernel Phase Mismatch:** 
   - OS passes 9 phases: `[..., planned, plan-reviewed, executing, shipping, reflect, done]`
   - Kernel has 9 phases: `[..., planned, executing, review, polish, reflect, done]`
   - Custom phases like `plan-reviewed` and `shipping` are stored as-is and respected by the kernel's phase machinery.

5. **No "plan-reviewed" in kernel code:** The phase exists purely at the OS/spec level. The kernel phase.go has no constant for it.

6. **Gate checks are pluggable:** The evaluateGate() function accepts querier interfaces (RuntrackQuerier, VerdictQuerier, PortfolioQuerier, DepQuerier, BudgetQuerier). Tests can stub these.

7. **GateRulesInfo() is informational:** Only returns rules for the kernel's DefaultPhaseChain, not custom chains. Useful for documentation but doesn't affect runtime behavior.

---

## 10. References

- **Kernel Phase Constants:** `/home/mk/projects/Demarch/core/intercore/internal/phase/phase.go` lines 10-19
- **DefaultPhaseChain:** `/home/mk/projects/Demarch/core/intercore/internal/phase/phase.go` line 67
- **Gate Rules Map:** `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go` lines 95-119
- **Gate Check Constants:** `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go` lines 13-19
- **Gate Evaluation:** `/home/mk/projects/Demarch/core/intercore/internal/phase/gate.go` lines 121-365
- **OS Phase Chain:** `/home/mk/projects/Demarch/os/clavain/hooks/lib-sprint.sh` line 134
- **intercore_run_create Wrapper:** `/home/mk/projects/Demarch/os/clavain/hooks/lib-intercore.sh` lines 236-245
- **IC CLI --phases parsing:** `/home/mk/projects/Demarch/core/intercore/cmd/ic/run.go` lines 96-97
- **Phase Chain Parsing:** `/home/mk/projects/Demarch/core/intercore/internal/phase/phase.go` lines 79-102

