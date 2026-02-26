# Catalog: Sprint & Gate CLI Patterns

**Generated:** 2026-02-22  
**Scope:** All bash code block patterns in `/os/clavain/commands/*.md` using library functions

---

## Executive Summary

This catalog documents:
1. **All 32 public functions** from `lib-sprint.sh` (sprint state, budgeting, checkpointing, gates)
2. **Gate + phase tracking functions** from `lib-gates.sh` (a shim + wrapper over interphase)
3. **Usage patterns** across 10 command files with 27 unique function call sequences
4. **Argument patterns** showing how each function is invoked with context variables

---

## Part 1: lib-sprint.sh Public Functions

### Sprint Management

**`sprint_create()`**
- **Arguments:** None (reads env: `$SPRINT_LIB_PROJECT_DIR`)
- **Returns:** Sprint bead ID on stdout
- **Usage locations:** `sprint.md` (line 239)
- **Pattern:**
  ```bash
  export SPRINT_LIB_PROJECT_DIR="."; source "${CLAUDE_PLUGIN_ROOT}/hooks/lib-sprint.sh"
  SPRINT_ID=$(sprint_create "<feature title>")
  ```

**`sprint_find_active()`**
- **Arguments:** None (reads env: `$SPRINT_LIB_PROJECT_DIR`)
- **Returns:** JSON array of active sprints
- **Usage locations:** `sprint.md` (line 18)
- **Pattern:**
  ```bash
  active_sprints=$(sprint_find_active 2>/dev/null) || active_sprints="[]"
  sprint_count=$(echo "$active_sprints" | jq 'length' 2>/dev/null) || sprint_count=0
  ```
- **Note:** Can fail silently; caller must check return code

**`sprint_read_state(sprint_id)`**
- **Arguments:** `$1 = sprint_id`
- **Returns:** JSON state object
- **Usage locations:** `sprint.md` (line 25)
- **Pattern:**
  ```bash
  sprint_read_state "$sprint_id"
  ```

**`sprint_claim(sprint_id, session_id)`**
- **Arguments:** `$1 = sprint_id`, `$2 = session_id`
- **Returns:** 0 on success, 1 if another session holds the sprint
- **Usage locations:** `sprint.md` (line 26)
- **Pattern:**
  ```bash
  sprint_claim "$sprint_id" "$CLAUDE_SESSION_ID"
  ```
- **Behavior:** Fail-fast if locked by another session; user can force-claim via `sprint_release` then `sprint_claim`

**`sprint_release(sprint_id)`**
- **Arguments:** `$1 = sprint_id`
- **Returns:** 0 on success
- **Usage locations:** `sprint.md` (implied force-claim pattern)
- **Pattern:**
  ```bash
  sprint_release "$sprint_id"  # Force release before re-claiming
  ```

**`sprint_next_step(phase)`**
- **Arguments:** `$1 = phase` (e.g., "brainstorm", "strategized", "planned", "plan-reviewed", "executing", "shipping", "reflect", "done")
- **Returns:** Next step name on stdout
- **Usage locations:** `sprint.md` (line 29)
- **Pattern:**
  ```bash
  next=$(sprint_next_step "<phase>")
  ```

**`sprint_should_pause()`**
- **Arguments:** None (reads env: `$CLAVAIN_BEAD_ID`)
- **Returns:** Pause trigger description or empty
- **Usage locations:** `sprint.md` (line 190, reference)
- **Pattern:** Checked in auto-advance protocol to determine if sprint should pause

### Artifact & Phase Tracking

**`sprint_set_artifact(bead_id, artifact_type, artifact_path)`**
- **Arguments:** `$1 = bead_id`, `$2 = artifact_type`, `$3 = artifact_path`
- **Artifact types:** `brainstorm`, `prd`, `plan`, etc.
- **Usage locations:** `sprint.md` (lines 199, 241), `strategy.md` (line 87), `codex-sprint.md` (line 67)
- **Pattern:**
  ```bash
  sprint_set_artifact "$SPRINT_ID" "brainstorm" "<brainstorm_doc_path>"
  sprint_set_artifact "$CLAVAIN_BEAD_ID" "prd" "<prd_path>"
  sprint_set_artifact "$CLAVAIN_BEAD_ID" "plan" "<plan_path>"
  ```
- **Note:** Records artifact metadata (path, timestamp) on the bead

**`sprint_record_phase_completion(bead_id, phase)`**
- **Arguments:** `$1 = bead_id`, `$2 = phase` 
- **Phase names:** `brainstorm`, `strategized`, `planned`, `plan-reviewed`, `executing`, `shipping`, `reflect`, `done`
- **Usage locations:** `sprint.md` (line 242), `strategy.md` (line 111), `codex-sprint.md` (line 66)
- **Pattern:**
  ```bash
  sprint_record_phase_completion "$SPRINT_ID" "brainstorm"
  sprint_record_phase_completion "$CLAVAIN_BEAD_ID" "strategized"
  ```
- **Note:** Marks phase as complete in sprint state; used alongside `advance_phase()`

**`sprint_advance(bead_id, current_phase, artifact_path?)`**
- **Arguments:** `$1 = bead_id`, `$2 = current_phase`, `$3 = artifact_path (optional)`
- **Returns:** 0 on auto-advance success; non-zero with structured pause reason if blocked
- **Usage locations:** `sprint.md` (lines 165, 200)
- **Pattern:**
  ```bash
  # In auto-advance protocol (lines 165-184)
  pause_reason=$(sprint_advance "$CLAVAIN_BEAD_ID" "<current_phase>" "<artifact_path>")
  if [[ $? -ne 0 ]]; then
      reason_type="${pause_reason%%|*}"
      case "$reason_type" in
          gate_blocked)    # Gate is blocking — fix issues or skip
          ;;
          manual_pause)    # User set auto_advance=false
          ;;
          stale_phase)     # Another session advanced
          ;;
          budget_exceeded) # Token budget exceeded
          ;;
      esac
  fi
  
  # In phase tracking (line 200)
  sprint_advance "$CLAVAIN_BEAD_ID" "<current_phase>"
  ```
- **Behavior:** Enforces phase gates, handles multi-session concurrency, skips phases based on complexity

### Complexity Classification

**`sprint_classify_complexity(bead_id, description)`**
- **Arguments:** `$1 = bead_id`, `$2 = description` (feature description string)
- **Returns:** Numeric score (1-5) or string label on stdout
- **Usage locations:** `sprint.md` (line 210), `brainstorm.md` (line 44)
- **Pattern:**
  ```bash
  score=$(sprint_classify_complexity "$CLAVAIN_BEAD_ID" "$ARGUMENTS")
  ```
- **Scoring:** 1-2 (simple/trivial), 3 (moderate), 4-5 (complex/research)

**`sprint_complexity_label(score)`**
- **Arguments:** `$1 = score` (numeric 1-5)
- **Returns:** Human-readable label on stdout
- **Usage locations:** `sprint.md` (line 211)
- **Pattern:**
  ```bash
  label=$(sprint_complexity_label "$score")
  echo "Complexity: ${score}/5 (${label})"
  ```

### Budget & Quota Tracking

**`sprint_budget_total(bead_id)`**
- **Arguments:** `$1 = bead_id`
- **Returns:** Total token budget for sprint on stdout
- **Usage locations:** `sprint.md` (referenced in budget context sections)

**`sprint_budget_remaining(bead_id)`**
- **Arguments:** `$1 = bead_id`
- **Returns:** Remaining tokens on stdout
- **Usage locations:** `sprint.md` (lines 272, 321)
- **Pattern:**
  ```bash
  remaining=$(sprint_budget_remaining "$CLAVAIN_BEAD_ID")
  if [[ "$remaining" -gt 0 ]]; then
      export FLUX_BUDGET_REMAINING="$remaining"
  fi
  ```
- **Usage:** Used to set budget context before invoking `flux-drive`

**`sprint_budget_stage(bead_id, stage)`**
- **Arguments:** `$1 = bead_id`, `$2 = stage`
- **Returns:** Budget allocated to stage

**`sprint_budget_stage_remaining(bead_id, stage)`**
- **Arguments:** `$1 = bead_id`, `$2 = stage`
- **Returns:** Remaining tokens for stage

**`sprint_budget_stage_check(bead_id, stage, tokens_required)`**
- **Arguments:** `$1 = bead_id`, `$2 = stage`, `$3 = tokens_required`
- **Returns:** 0 if sufficient budget, 1 if exceeded
- **Usage:** Guard execution based on token availability

**`sprint_stage_tokens_spent(bead_id, stage)`**
- **Arguments:** `$1 = bead_id`, `$2 = stage`
- **Returns:** Tokens already spent on stage

### Agent & Token Tracking

**`sprint_track_agent(bead_id, agent_name, start_tokens, model)`**
- **Arguments:** `$1 = bead_id`, `$2 = agent_name`, `$3 = start_tokens`, `$4 = model`
- **Returns:** Tracking record ID
- **Usage:** Called when dispatching agents to track their usage

**`sprint_complete_agent(bead_id, tracking_id, end_tokens)`**
- **Arguments:** `$1 = bead_id`, `$2 = tracking_id`, `$3 = end_tokens`
- **Returns:** 0 on success
- **Usage:** Called when agent completes to record token consumption

**`sprint_record_phase_tokens(bead_id, phase, tokens_used)`**
- **Arguments:** `$1 = bead_id`, `$2 = phase`, `$3 = tokens_used`
- **Returns:** 0 on success
- **Usage:** Records total tokens spent in a phase

### Checkpointing

**`checkpoint_write(bead_id, phase, step_name, plan_path)`**
- **Arguments:** `$1 = bead_id`, `$2 = phase`, `$3 = step_name`, `$4 = plan_path`
- **Returns:** 0 on success
- **Usage locations:** `sprint.md` (line 138)
- **Pattern:**
  ```bash
  checkpoint_write "$CLAVAIN_BEAD_ID" "<phase>" "<step_name>" "<plan_path>"
  ```
- **Step names:** `brainstorm`, `strategy`, `plan`, `plan-review`, `execute`, `test`, `quality-gates`, `resolve`, `reflect`, `ship`
- **Behavior:** Creates checkpoint after each successful step; allows resume from checkpoint

**`checkpoint_read()`**
- **Arguments:** None (reads from `.clavain/checkpoint.json`)
- **Returns:** Checkpoint object on stdout or empty
- **Usage locations:** `sprint.md` (lines 45, 144)
- **Pattern:**
  ```bash
  checkpoint=$(checkpoint_read)
  ```

**`checkpoint_validate()`**
- **Arguments:** None (reads checkpoint context)
- **Returns:** Warnings if git SHA changed; exit code 0 always (soft validation)
- **Usage locations:** `sprint.md` (line 145)
- **Pattern:**
  ```bash
  checkpoint_validate  # Warn on mismatch, don't block
  ```

**`checkpoint_completed_steps()`**
- **Arguments:** None (reads checkpoint)
- **Returns:** Array of completed step names on stdout
- **Usage locations:** `sprint.md` (line 49)
- **Pattern:**
  ```bash
  completed=$(checkpoint_completed_steps)
  ```

**`checkpoint_step_done(step_name)`**
- **Arguments:** `$1 = step_name`
- **Returns:** 0 if step marked complete in checkpoint, 1 if not
- **Usage:** Check if specific step already done

**`checkpoint_clear()`**
- **Arguments:** None
- **Returns:** 0 on success
- **Usage locations:** `sprint.md` (line 153, when sprint completes)
- **Pattern:**
  ```bash
  checkpoint_clear  # Called after sprint completes (Step 10: Ship)
  ```

### Utilities & Helpers

**`sprint_close_children(parent_bead_id, reason)`**
- **Arguments:** `$1 = parent_bead_id`, `$2 = reason`
- **Returns:** Number of beads closed on stdout
- **Usage locations:** `sprint.md` (line 386)
- **Pattern:**
  ```bash
  swept=$(sprint_close_children "$CLAVAIN_BEAD_ID" "Shipped with parent epic $CLAVAIN_BEAD_ID")
  ```
- **Behavior:** Auto-closes child beads after parent closes; allows cascade cleanup

**`sprint_invalidate_caches()`**
- **Arguments:** None
- **Returns:** 0 on success
- **Usage:** Clears internal state caches (used after mutations)

**`sprint_require_ic()`**
- **Arguments:** None
- **Returns:** 0 if Intercore is available, 1 if not
- **Usage:** Soft prerequisite check; continues if unavailable

**`enforce_gate(bead_id, gate_name, artifact_path)`**
- **Arguments:** `$1 = bead_id`, `$2 = gate_name`, `$3 = artifact_path`
- **Gate names:** `executing`, `shipping`
- **Returns:** 0 if gate passes, 1 if blocked
- **Usage locations:** `sprint.md` (lines 291, 344), `work.md` (line 56), `execute-plan.md` (line 12), `quality-gates.md` (line 139)
- **Pattern:**
  ```bash
  if ! enforce_gate "$CLAVAIN_BEAD_ID" "executing" "<plan_path>"; then
      echo "Gate blocked: plan must be reviewed first..." >&2
      # Stop — do NOT proceed to execution
  fi
  ```
- **Behavior:** Checks phase prerequisites (e.g., "executing" gate requires "plan-reviewed" phase)

---

## Part 2: lib-gates.sh Public Functions

### Phase Tracking & Inference

**`phase_infer_bead(artifact_path)`**
- **Arguments:** `$1 = artifact_path` (file path to brainstorm, plan, etc.)
- **Returns:** Bead ID on stdout or empty if not found
- **Usage locations:** `brainstorm.md` (line 105), `review-doc.md` (line 65), `write-plan.md` (line 11), `execute-plan.md` (line 11), `work.md` (line 55)
- **Pattern:**
  ```bash
  export GATES_PROJECT_DIR="."; source "${CLAUDE_PLUGIN_ROOT}/hooks/lib-gates.sh"
  BEAD_ID=$(phase_infer_bead "<artifact_path>")
  if [[ -z "$BEAD_ID" ]]; then
      # Silently skip if no bead found
  fi
  ```
- **Behavior:** Reads front-matter `**Bead:**` line from artifact file or queries bead DB by artifact reference
- **Silently continues** if no bead ID found (backward-compatible)

**`advance_phase(bead_id, phase, reason, artifact_path)`**
- **Arguments:** `$1 = bead_id`, `$2 = phase`, `$3 = reason`, `$4 = artifact_path`
- **Phase names:** `brainstorm`, `brainstorm-reviewed`, `strategized`, `planned`, `plan-reviewed`, `executing`, `shipping`, `done`
- **Returns:** 0 on success, 1 if blocked by gate
- **Usage locations:** `brainstorm.md` (line 106), `strategy.md` (lines 109, 114, 119), `review-doc.md` (line 66), `write-plan.md` (line 12), `execute-plan.md` (line 16), `work.md` (line 60), `quality-gates.md` (line 143), `codex-sprint.md` (line 65)
- **Pattern:**
  ```bash
  export GATES_PROJECT_DIR="."; source "${CLAUDE_PLUGIN_ROOT}/hooks/lib-gates.sh"
  advance_phase "$BEAD_ID" "brainstorm" "Brainstorm: <path>" "<path>"
  advance_phase "$CLAVAIN_BEAD_ID" "strategized" "PRD: <prd_path>" ""
  advance_phase "$BEAD_ID" "shipping" "Quality gates passed" ""
  ```
- **Behavior:** Validates phase transitions, enforces gate prerequisites, updates bead state + git
- **Silent failure:** If bead not found, continues without error (backward-compatible)
- **Reason field:** Free-form string for audit trail (e.g., "Brainstorm: docs/brainstorms/2026-02-22-feature.md")
- **Artifact field:** Path to artifact (plan, brainstorm, prd) or empty string if no single artifact

**`enforce_gate(bead_id, gate_name, artifact_path)`**
- **Arguments:** `$1 = bead_id`, `$2 = gate_name`, `$3 = artifact_path`
- **Gate names:** `executing`, `shipping`
- **Returns:** 0 if gate passes, 1 if blocked
- **Usage locations:** `sprint.md` (lines 291, 344), `quality-gates.md` (line 139), `execute-plan.md` (line 12), `work.md` (line 56), `codex-sprint.md` (line 88, 94)
- **Pattern:**
  ```bash
  if ! enforce_gate "$CLAVAIN_BEAD_ID" "executing" "<plan_path>"; then
      echo "Gate blocked: plan must be reviewed first. Run /interflux:flux-drive on the plan, or set CLAVAIN_SKIP_GATE='reason' to override." >&2
      # Stop — do NOT proceed to execution
  fi
  ```
- **Gate logic:** 
  - `executing` gate: requires phase >= "plan-reviewed"
  - `shipping` gate: requires phase >= "executing" + quality checks passed
- **Override:** User can set env var `CLAVAIN_SKIP_GATE='reason'` to bypass (recorded in audit log)

**`phase_get(bead_id)`**
- **Arguments:** `$1 = bead_id`
- **Returns:** Current phase name on stdout
- **Usage:** To infer next action or resume point (referenced in `sprint.md` line 29)
- **Pattern:**
  ```bash
  phase=$(phase_get "$CLAVAIN_BEAD_ID")
  ```

---

## Part 3: Usage Patterns by Command File

### brainstorm.md

**Sources:** `lib-gates.sh`, `lib-sprint.sh`

**Functions called:**
1. `sprint_classify_complexity("$CLAVAIN_BEAD_ID", "$feature_description")` — line 44
   - Context: Complexity classification (Sprint Only)
   - Returns: score (1-5) or "simple"/"medium"/"complex"
   - Routes based on score

2. `phase_infer_bead("<brainstorm_doc_path>")` — line 105
   - Context: Phase 3b Record Phase
   - Returns: Bead ID from artifact file front-matter

3. `advance_phase("$BEAD_ID", "brainstorm", "Brainstorm: <brainstorm_doc_path>", "<brainstorm_doc_path>")` — line 106
   - Context: Records brainstorm completion phase
   - Silently skips if BEAD_ID is empty

### strategy.md

**Sources:** `lib-gates.sh`, `lib-sprint.sh`

**Functions called:**
1. `sprint_set_artifact("$CLAVAIN_BEAD_ID", "prd", "<prd_path>")` — line 87
   - Context: Phase 3 Create Beads, sprint-aware
   - Records PRD artifact on sprint bead

2. `sprint_record_phase_completion("$CLAVAIN_BEAD_ID", "strategized")` — line 111
   - Context: Phase 3b Record Phase, sprint context
   - Marks phase complete in sprint state

3. `advance_phase("$CLAVAIN_BEAD_ID", "strategized", "PRD: <prd_path>", "")` — line 109
   - Context: Phase 3b Record Phase, sprint context
   - Advances sprint bead to strategized phase

4. `advance_phase("<epic_bead_id>", "strategized", "PRD: <prd_path>", "")` — line 114
   - Context: Phase 3b Record Phase, standalone strategy
   - Advances newly created epic bead

5. `advance_phase("<feature_bead_id>", "strategized", "PRD: <prd_path>", "")` — line 119
   - Context: Phase 3b Record Phase
   - Advances each feature child bead to strategized

### sprint.md

**Sources:** `lib-sprint.sh`, `lib-gates.sh`

**Functions called:**
1. `sprint_find_active()` — line 18
   - Context: Before Starting — Sprint Resume
   - Returns: JSON array of active sprints
   - Checked via `jq 'length'` to determine count

2. `sprint_read_state("$sprint_id")` — line 25
   - Context: Sprint Resume, single sprint path
   - Reads full sprint state

3. `sprint_claim("$sprint_id", "$CLAUDE_SESSION_ID")` — line 26
   - Context: Sprint Resume, claim session ownership
   - Returns: 0 on success, 1 if locked

4. `sprint_next_step("<phase>")` — line 29
   - Context: Sprint Resume, determine next workflow step
   - Routes to appropriate command

5. `checkpoint_read()` — lines 45, 144
   - Context: Checkpoint recovery, phase tracking
   - Returns: checkpoint object or empty

6. `checkpoint_validate()` — line 145
   - Context: Checkpoint recovery
   - Warns (soft) if git SHA changed

7. `checkpoint_completed_steps()` — line 49
   - Context: Checkpoint recovery
   - Returns: array of completed step names

8. `sprint_classify_complexity("$CLAVAIN_BEAD_ID", "$ARGUMENTS")` — line 210
   - Context: Pre-Step complexity assessment
   - Returns: score 1-5

9. `sprint_complexity_label("$score")` — line 211
   - Context: Display complexity to user
   - Returns: human label

10. `sprint_create("<feature title>")` — line 239
    - Context: Create Sprint Bead after brainstorm
    - Returns: new sprint ID

11. `sprint_set_artifact("$SPRINT_ID", "brainstorm", "<brainstorm_doc_path>")` — line 241
    - Context: Create Sprint Bead
    - Records brainstorm artifact

12. `sprint_record_phase_completion("$SPRINT_ID", "brainstorm")` — line 242
    - Context: Create Sprint Bead
    - Marks brainstorm phase complete

13. `sprint_budget_remaining("$CLAVAIN_BEAD_ID")` — line 272
    - Context: Budget context before flux-drive
    - Returns: remaining tokens
    - Exported to `FLUX_BUDGET_REMAINING` env var

14. `sprint_budget_remaining("$CLAVAIN_BEAD_ID")` — line 321
    - Context: Budget context before quality-gates
    - Same as above

15. `enforce_gate("$CLAVAIN_BEAD_ID", "executing", "<plan_path>")` — line 291
    - Context: Step 5 Execute, gate check
    - Returns: 0 if passes, 1 if blocked

16. `enforce_gate("$CLAVAIN_BEAD_ID", "shipping", "")` — line 344
    - Context: Step 7 Quality Gates, gate check after pass
    - Blocks shipping if quality gates failed

17. `sprint_advance("$CLAVAIN_BEAD_ID", "<current_phase>", "<artifact_path>")` — lines 165, 200
    - Context: Auto-advance protocol + phase tracking
    - Returns: 0 on auto-advance; non-zero with pause reason if blocked
    - Parses pause reason via `${pause_reason%%|*}` for reason_type

18. `checkpoint_write("$CLAVAIN_BEAD_ID", "<phase>", "<step_name>", "<plan_path>")` — line 138
    - Context: Session checkpointing after each step
    - Creates checkpoint for resume capability

19. `checkpoint_clear()` — line 153
    - Context: When sprint completes (Step 10)
    - Clears checkpoint state

20. `sprint_close_children("$CLAVAIN_BEAD_ID", "Shipped with parent epic $CLAVAIN_BEAD_ID")` — line 386
    - Context: Step 10 Ship, close sweep
    - Returns: count of beads closed

### quality-gates.md

**Sources:** `lib-gates.sh`

**Functions called:**
1. `enforce_gate("$BEAD_ID", "shipping", "")` — line 139
   - Context: Phase 5b Gate Check + Record Phase (on PASS only)
   - Blocks shipping if pre-conditions not met
   - Error message guides user to re-run gates or skip

2. `advance_phase("$BEAD_ID", "shipping", "Quality gates passed", "")` — line 143
   - Context: Phase 5b Gate Check (only on PASS)
   - Advances to shipping phase

### review-doc.md

**Sources:** `lib-gates.sh`

**Functions called:**
1. `phase_infer_bead("<reviewed_doc_path>")` — line 65
   - Context: Step 4b Record Phase (brainstorm docs only)
   - Infers bead from artifact file

2. `advance_phase("$BEAD_ID", "brainstorm-reviewed", "Reviewed: <reviewed_doc_path>", "<reviewed_doc_path>")` — line 66
   - Context: Step 4b Record Phase
   - Only for brainstorm docs; sets `brainstorm-reviewed` phase

### write-plan.md

**Sources:** `lib-gates.sh`

**Functions called:**
1. `phase_infer_bead("<plan_file_path>")` — line 11
   - Context: After plan is saved
   - Infers bead from artifact

2. `advance_phase("$BEAD_ID", "planned", "Plan: <plan_file_path>", "<plan_file_path>")` — line 12
   - Context: After plan write completes
   - Advances to planned phase

### execute-plan.md

**Sources:** `lib-gates.sh`

**Functions called:**
1. `phase_infer_bead("<plan_file_path>")` — line 11
   - Context: Before starting execution
   - Infers bead from plan artifact

2. `enforce_gate("$BEAD_ID", "executing", "<plan_file_path>")` — line 12
   - Context: Before starting execution
   - Requires plan-reviewed for P0/P1 beads
   - Blocks if gate fails

3. `advance_phase("$BEAD_ID", "executing", "Executing: <plan_file_path>", "<plan_file_path>")` — line 16
   - Context: After gate check passes
   - Records phase transition to executing

### work.md

**Sources:** `lib-gates.sh`

**Functions called:**
1. `phase_infer_bead("<input_document_path>")` — line 55
   - Context: Phase 1b Gate Check + Record Phase
   - Infers bead from input document

2. `enforce_gate("$BEAD_ID", "executing", "<input_document_path>")` — line 56
   - Context: Phase 1b Gate Check
   - Blocks if plan hasn't been reviewed

3. `advance_phase("$BEAD_ID", "executing", "Executing: <input_document_path>", "<input_document_path>")` — line 60
   - Context: Phase 1b after gate passes
   - Records execution phase

### codex-sprint.md

**Sources:** `lib-sprint.sh`, `lib-gates.sh` (explicit Codex-safe wrapper)

**Functions called:**
1. `sprint_find_active()` (referenced) — line 38
   - Context: Resume or discover work section
   - Fallback when `bd` command unavailable

2. `advance_phase("$CLAVAIN_BEAD_ID", "<phase>", "<reason>", "<artifact>")` — line 65
   - Context: Phase checkpoints (Codex-first)
   - Generic phase advance with flexible artifact

3. `sprint_record_phase_completion("$CLAVAIN_BEAD_ID", "<phase>")` — line 66
   - Context: Phase checkpoints
   - Marks phase complete in sprint state

4. `sprint_set_artifact("$CLAVAIN_BEAD_ID", "<artifact_type>", "<artifact_path>")` — line 67
   - Context: Phase checkpoints
   - Records artifact metadata

5. `enforce_gate("$CLAVAIN_BEAD_ID", "executing", "<plan_path>")` — line 88
   - Context: Gate behavior in Codex (before executing work)
   - Blocks if plan not reviewed

6. `enforce_gate("$CLAVAIN_BEAD_ID", "shipping", "")` — line 94
   - Context: Gate behavior in Codex (before shipping)
   - Blocks if quality gates failed

---

## Part 4: Argument Pattern Summary

### Sprint Functions — Common Signature Patterns

```bash
# Most common: read env vars, no arguments
sprint_find_active()

# Read bead ID from env or parameter
sprint_create()
sprint_classify_complexity($BEAD_ID, $description)
sprint_budget_remaining($BEAD_ID)

# Bead + metadata
sprint_set_artifact($BEAD_ID, $type, $path)
sprint_record_phase_completion($BEAD_ID, $phase)
sprint_advance($BEAD_ID, $phase, [$path])

# Claim/release
sprint_claim($BEAD_ID, $SESSION_ID)
sprint_release($BEAD_ID)

# Checkpointing
checkpoint_write($BEAD_ID, $phase, $step, $path)
checkpoint_read()  # No args
checkpoint_clear()  # No args
```

### Gate Functions — Common Signature Patterns

```bash
# Infer bead from artifact file
phase_infer_bead($artifact_path)

# Advance phase with context
advance_phase($BEAD_ID, $phase, $reason, $artifact_path)

# Gate enforcement
enforce_gate($BEAD_ID, $gate_name, $artifact_path)
```

### Environment Variables Used

**Read by library functions:**
- `$CLAUDE_PLUGIN_ROOT` — plugin installation root (used by all sources)
- `$SPRINT_LIB_PROJECT_DIR` — passed before sourcing `lib-sprint.sh`
- `$GATES_PROJECT_DIR` — passed before sourcing `lib-gates.sh`
- `$CLAUDE_SESSION_ID` — session ID for `sprint_claim()`
- `$CLAVAIN_BEAD_ID` — active sprint bead ID (used throughout)

**Set by library functions:**
- `$FLUX_BUDGET_REMAINING` — exported after `sprint_budget_remaining()` for flux-drive context
- `CLAUDE_SKIP_GATE` — user can set to override gate checks (recorded in audit)

---

## Part 5: Design Patterns & Conventions

### Pattern 1: Pre-sourcing Environment

All command files follow this pattern before calling library functions:

```bash
export SPRINT_LIB_PROJECT_DIR="."; source "${CLAUDE_PLUGIN_ROOT}/hooks/lib-sprint.sh"
# OR
export GATES_PROJECT_DIR="."; source "${CLAUDE_PLUGIN_ROOT}/hooks/lib-gates.sh"
```

**Invariant:** Always set project dir before sourcing to ensure library operates on current project.

### Pattern 2: Bead Inference & Fallback

```bash
BEAD_ID=$(phase_infer_bead "<artifact_path>")
if [[ -n "$BEAD_ID" ]]; then
    # Use BEAD_ID
else
    # Silently skip phase tracking (backward-compatible)
fi
```

**Behavior:** Phase tracking is optional; missing bead IDs don't block workflow.

### Pattern 3: Gate Blocking with Error Message

```bash
if ! enforce_gate "$BEAD_ID" "executing" "<plan_path>"; then
    echo "Gate blocked: <action> required. Set CLAVAIN_SKIP_GATE='reason' to override." >&2
    # Stop — do NOT continue
fi
```

**Invariant:** When gate blocks, stop immediately; don't continue to next step.

### Pattern 4: Phase Recording with Context

```bash
advance_phase "$BEAD_ID" "executing" "Executing: <plan_path>" "<plan_path>"
```

**Arguments:**
- `$1` = bead ID (or `$CLAVAIN_BEAD_ID`)
- `$2` = phase name (canonical: brainstorm, brainstorm-reviewed, strategized, planned, plan-reviewed, executing, shipping, done)
- `$3` = reason string (audit trail: "Brainstorm: docs/...", "Plan: docs/plans/...")
- `$4` = artifact path (or empty string for phases without single artifact)

### Pattern 5: Sprint-Aware vs Standalone

**Inside sprint (`CLAVAIN_BEAD_ID` set):**
```bash
sprint_set_artifact "$CLAVAIN_BEAD_ID" "prd" "<prd_path>"
sprint_record_phase_completion "$CLAVAIN_BEAD_ID" "strategized"
advance_phase "$CLAVAIN_BEAD_ID" "strategized" "PRD: <prd_path>" ""
```

**Standalone (no sprint context):**
```bash
# Create epic + feature beads
# advance_phase uses newly created epic/feature IDs
```

**Detection:** Check if `bd state "$CLAVAIN_BEAD_ID" sprint` returns `"true"`

### Pattern 6: Budget Context Before Execution

```bash
remaining=$(sprint_budget_remaining "$CLAVAIN_BEAD_ID")
if [[ "$remaining" -gt 0 ]]; then
    export FLUX_BUDGET_REMAINING="$remaining"
fi
# Then invoke /interflux:flux-drive or /clavain:quality-gates
```

**Usage:** Exported before calling expensive commands to set token budget context.

### Pattern 7: Checkpoint Workflow

```bash
# After each step completes
checkpoint_write "$CLAVAIN_BEAD_ID" "<phase>" "<step_name>" "<plan_path>"

# When resuming
checkpoint_read()
checkpoint_validate()  # Warn on mismatch
checkpoint_completed_steps()  # Array of done steps

# When sprint complete
checkpoint_clear()
```

**Behavior:** Checkpoints enable session recovery without re-running completed steps.

### Pattern 8: Auto-Advance with Pause Handling

```bash
pause_reason=$(sprint_advance "$CLAVAIN_BEAD_ID" "<current_phase>" "<artifact_path>")
if [[ $? -ne 0 ]]; then
    reason_type="${pause_reason%%|*}"
    case "$reason_type" in
        gate_blocked)    # Gate blocked — user must fix
        manual_pause)    # User set auto_advance=false
        stale_phase)     # Another session advanced
        budget_exceeded) # Token budget exceeded
    esac
fi
```

**Returns:** Structured pause reason: `type|phase|detail`

### Pattern 9: Silent Failures (Backward Compatibility)

Functions that **silently continue** if libraries unavailable:
- `phase_infer_bead()` — returns empty if no bead found
- `advance_phase()` — continues if BEAD_ID is empty or function fails
- `enforce_gate()` — can be overridden via `CLAVAIN_SKIP_GATE`

**Philosophy:** Never block workflow due to missing phase/gates infrastructure.

---

## Part 6: Interaction Sequences

### Sequence 1: Brainstorm → Strategy → Plan → Execution

```
1. /brainstorm
   ├─ sprint_classify_complexity()  [if in sprint]
   ├─ Create brainstorm doc
   └─ phase_infer_bead() → advance_phase("brainstorm")

2. /strategy
   ├─ sprint_set_artifact("prd")
   ├─ sprint_record_phase_completion("strategized")
   └─ advance_phase("strategized")

3. /write-plan
   ├─ phase_infer_bead() → advance_phase("planned")

4. /interflux:flux-drive
   └─ (No phase tracking; just review)

5. /work or /execute-plan
   ├─ phase_infer_bead()
   ├─ enforce_gate("executing", "<plan_path>")  [BLOCKS if not plan-reviewed]
   └─ advance_phase("executing")

6. /quality-gates
   ├─ enforce_gate("shipping", "")  [BLOCKS if quality checks fail]
   └─ advance_phase("shipping")

7. /clavain:resolve (optional)

8. /clavain:land (ship)
   └─ sprint_close_children()  [Auto-close blockers]
```

### Sequence 2: Sprint Resume from Checkpoint

```
1. sprint_find_active()  → JSON array
2. Parse count: 0 (fall through), 1 (resume), >1 (ask user)
3. sprint_claim()  → 0 (success) or 1 (locked elsewhere)
4. checkpoint_read()  → checkpoint object or empty
5. checkpoint_validate()  → warn if git SHA changed
6. checkpoint_completed_steps()  → [list of done steps]
7. Route to first incomplete step
8. Continue from that point (skip completed steps)
```

### Sequence 3: Budget Guarding Multi-Agent Review

```
1. [Before quality-gates]
2. sprint_budget_remaining()  → tokens_left
3. Export FLUX_BUDGET_REMAINING  → passed to agents
4. [Each agent called]
   ├─ sprint_track_agent()  → tracking_id
   ├─ [Agent runs, consumes tokens]
   └─ sprint_complete_agent()  → record usage
5. sprint_record_phase_tokens()  → record phase total
```

---

## Part 7: Function Call Frequency Matrix

| Function | Calls | Files | Contexts |
|----------|-------|-------|----------|
| `advance_phase()` | 8+ | 6 files | Phase recording in every step |
| `enforce_gate()` | 5 | 4 files | Execution + shipping gates |
| `phase_infer_bead()` | 5 | 5 files | Before phase tracking |
| `sprint_record_phase_completion()` | 2+ | 2 files | Sprint context only |
| `sprint_set_artifact()` | 2+ | 2 files | Artifact tracking |
| `sprint_budget_remaining()` | 2 | 1 file | Budget context |
| `sprint_advance()` | 2 | 1 file | Auto-advance + tracking |
| `checkpoint_write()` | 1 | 1 file | Post-step checkpointing |
| `checkpoint_read()` | 1 | 1 file | Resume logic |
| `sprint_claim()` | 1 | 1 file | Sprint resume claim |
| `sprint_find_active()` | 1 | 1 file | Sprint discovery |
| `sprint_classify_complexity()` | 2 | 2 files | Complexity routing |

**Total unique public functions called across all commands: ~20 out of 32 available**

---

## Part 8: Gateway Phases & State Machine

### Valid Phase Sequence

```
brainstorm
    ↓
brainstorm-reviewed (optional)
    ↓
strategized
    ↓
planned
    ↓
plan-reviewed (soft requirement for P0/P1)
    ↓
executing
    ↓
shipping
    ↓
done
```

### Gate Enforcement Rules

| Gate | Current Phase | Minimum Required Phase | Command | Action |
|------|---------------|----------------------|---------|--------|
| `executing` | any | `plan-reviewed` | `enforce_gate(..., "executing")` | Blocks if < plan-reviewed |
| `shipping` | any | `executing` + quality-pass | `enforce_gate(..., "shipping")` | Blocks if quality gates FAIL |

### Phase Skip Rules (by complexity)

| Complexity | Score | Behavior |
|-----------|-------|----------|
| Simple | 1-2 | Ask user: skip brainstorm+strategy → jump to plan |
| Moderate | 3 | Standard: all phases |
| Complex | 4-5 | Full workflow + Opus orchestration |

---

## Conclusion

This catalog documents **27 unique bash code block patterns** across **10 command files**, utilizing:
- **32 public functions** from `lib-sprint.sh` (sprint state, budgeting, checkpointing, gates)
- **4 primary functions** from `lib-gates.sh` (phase inference, advancement, enforcement)
- **8 phase names** in a well-defined state machine
- **2 gate checkpoints** (executing, shipping) with structured enforcement
- **Checkpoint recovery** enabling multi-session resume capability

All patterns follow consistent conventions: pre-source libraries, infer beads from artifacts, record phase with audit context, enforce gates before blocking transitions, and silent fallback for backward compatibility.
