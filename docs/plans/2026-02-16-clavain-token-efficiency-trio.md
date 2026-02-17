# Clavain Token Efficiency Trio — Implementation Plan
**Phase:** executing (as of 2026-02-16T23:44:03Z)

**Beads:** iv-ked1, iv-hyza, iv-kmyj
**PRD:** `docs/prds/2026-02-16-clavain-token-efficiency-trio.md`
**Date:** 2026-02-16

---

## F1: Skill Injection Budget Cap (iv-ked1)

**Effort:** 1-2 hours | **Risk:** Low | **Files:** 4

### Task 1.1: Add additionalContext cap to session-start.sh

**File:** `hub/clavain/hooks/session-start.sh`

At line 265, before the `cat <<EOF` output block, add a length check on the assembled `additionalContext` string. If it exceeds 6000 chars, truncate and append a notice.

Implementation:

1. After all context variables are assembled (line 262, after inflight detection), compute the full additionalContext string:
```bash
_full_context="You have Clavain.\n\n**Below is the full content of your 'clavain:using-clavain' skill - your introduction to using skills. For all other skills, use the 'Skill' tool:**\n\n${using_clavain_escaped}${companion_context}${conventions}${setup_hint}${upstream_warning}${sprint_context}${discovery_context}${sprint_resume_hint}${handoff_context}${inflight_context}"
```

2. Check length and truncate if needed:
```bash
ADDITIONAL_CONTEXT_CAP=6000
if [[ ${#_full_context} -gt $ADDITIONAL_CONTEXT_CAP ]]; then
    _full_context="${_full_context:0:$ADDITIONAL_CONTEXT_CAP}\\n\\n[Context truncated at ${ADDITIONAL_CONTEXT_CAP} chars. Run /clavain:using-clavain for full routing guide.]"
fi
```

3. Use `_full_context` in the heredoc output instead of inline concatenation.

**Verify:** `bash -n hooks/session-start.sh` (syntax check). Run a test session and check the additionalContext length isn't over 6K.

### Task 1.2: Add skill_check_budget() to lib.sh

**File:** `hub/clavain/hooks/lib.sh`

Add a function that checks all SKILL.md files under a given directory for size compliance:

```bash
# Check skill sizes against budget thresholds.
# Usage: skill_check_budget <skills_dir> [warn_threshold] [error_threshold]
# Output: lines of "PASS|WARN|ERROR skill-name size" to stdout
# Returns: 0 if all pass, 1 if any warn, 2 if any error
skill_check_budget() {
    local skills_dir="${1:?skills directory required}"
    local warn_at="${2:-16000}"
    local error_at="${3:-32000}"
    local max_severity=0

    for skill_md in "$skills_dir"/*/SKILL.md; do
        [[ -f "$skill_md" ]] || continue
        local skill_name
        skill_name=$(basename "$(dirname "$skill_md")")
        local size
        size=$(wc -c < "$skill_md")

        if [[ $size -gt $error_at ]]; then
            echo "ERROR $skill_name ${size} bytes (>${error_at})"
            [[ $max_severity -lt 2 ]] && max_severity=2
        elif [[ $size -gt $warn_at ]]; then
            echo "WARN $skill_name ${size} bytes (>${warn_at})"
            [[ $max_severity -lt 1 ]] && max_severity=1
        else
            echo "PASS $skill_name ${size} bytes"
        fi
    done
    return $max_severity
}
```

**Verify:** `bash -n hooks/lib.sh`. Test: `source hooks/lib.sh && skill_check_budget skills/`

### Task 1.3: Integrate budget check into /clavain:doctor

**File:** `hub/clavain/commands/doctor.md`

Add a new check section **"6. Skill Budget"** after the existing Plugin Version check (section 5):

```markdown
### 6. Skill Budget

```bash
# Check skill sizes (sourcing lib.sh for the function)
SCRIPT_DIR="$(find ~/.claude/plugins/cache -path '*/clavain/*/hooks/lib.sh' 2>/dev/null | head -1)"
if [[ -n "$SCRIPT_DIR" ]]; then
    source "$SCRIPT_DIR"
    SKILLS_DIR="$(dirname "$SCRIPT_DIR")/../skills"
    budget_output=$(skill_check_budget "$SKILLS_DIR" 16000 32000 2>/dev/null)
    budget_exit=$?
    warns=$(echo "$budget_output" | grep -c "^WARN" || true)
    errors=$(echo "$budget_output" | grep -c "^ERROR" || true)
    if [[ $errors -gt 0 ]]; then
        echo "skill budget: ERROR ($errors skills over 32K)"
        echo "$budget_output" | grep "^ERROR"
    elif [[ $warns -gt 0 ]]; then
        echo "skill budget: WARN ($warns skills over 16K)"
        echo "$budget_output" | grep "^WARN"
    else
        echo "skill budget: PASS (all skills under 16K)"
    fi
fi
```

Add to the output table: `skill budget  [PASS|WARN: N over 16K|ERROR: N over 32K]`

Add to recommendations: `skill budget WARN/ERROR → "Trim skills over 16K chars by moving verbose sections to references/ subdirectory"`

**Verify:** Run `/clavain:doctor` and confirm the new check appears in output.

### Task 1.4: Trim writing-skills SKILL.md to under 16K

**File:** `hub/clavain/skills/writing-skills/SKILL.md` (currently 18,646 bytes)

Need to remove ~3K bytes. Move these sections to new reference files:

1. **Move "Claude Search Optimization (CSO)" section (lines 140-287)** → `skills/writing-skills/references/claude-search-optimization.md`
   - This is 148 lines of detailed guidance on descriptions, keywords, naming, token efficiency
   - Replace in SKILL.md with: `## Claude Search Optimization\n\nSee `references/claude-search-optimization.md` for CSO techniques: rich descriptions, keyword coverage, naming conventions, and token efficiency patterns.`

2. **Move "Bulletproofing Discipline Skills" section (lines 406-415)** → can be folded into the existing reference material or kept inline (only 10 lines, not worth splitting)

3. **Move "Anti-Patterns" section (lines 427-447)** → fold into the CSO reference since it's about skill quality

Target: SKILL.md under 12K after trim (comfortable margin).

**Verify:** `wc -c skills/writing-skills/SKILL.md` → should be <16000. Run `skill_check_budget skills/` → should show PASS for writing-skills.

---

## F2: Summary-Mode Output Extraction (iv-hyza)

**Effort:** 2-3 hours | **Risk:** Low | **Files:** 4

### Task 2.1: Add verdict header specification to shared-contracts.md

**File:** `plugins/interflux/skills/flux-drive/phases/shared-contracts.md`

Add a new section **"Verdict Header"** after the existing "Output Format: Findings Index" section:

```markdown
## Verdict Header (Universal)

All agents (flux-drive reviewers and Codex dispatches) append a verdict header as the **last block** of their output. This enables the orchestrator to read only the tail of the file for a structured summary.

### Format

```
--- VERDICT ---
STATUS: pass|fail|warn|error
FILES: N changed
FINDINGS: N (P0: n, P1: n, P2: n)
SUMMARY: <1-2 sentence verdict>
---
```

### Rules

- The header is the last 7 lines of the output file (including the `---` delimiters)
- For flux-drive agents: STATUS maps from Verdict line (safe→pass, needs-changes→warn, risky→fail, error→error)
- For Codex agents: STATUS is CLEAN→pass, NEEDS_ATTENTION→warn, error→error
- FILES count: number of files modified by the agent (0 for review-only agents)
- FINDINGS count: total findings from the Findings Index (0 if no issues)
- SUMMARY: 1-2 sentences, no line breaks

### Extraction

The orchestrator extracts the verdict with `tail -7` on the output file. This avoids reading the full prose body into context.

For flux-drive reviews, the orchestrator reads:
- Findings Index (first ~30 lines via `head`)
- Verdict Header (last 7 lines via `tail`)
- Total: ~37 lines per agent regardless of prose length
```

**Verify:** Review the contract for completeness. No code to test — this is a specification.

### Task 2.2: Add verdict extraction to dispatch.sh

**File:** `hub/clavain/scripts/dispatch.sh`

After the Codex exec completes (line 604 success path, line 608 fallback path), extract the verdict header from the output file and write a `.verdict` sidecar:

1. Add a function after `_jsonl_parser()` (around line 586):
```bash
# Extract verdict header from agent output and write .verdict sidecar.
# The verdict is the last block delimited by "--- VERDICT ---" ... "---".
# If no verdict block found, synthesize one from the output's last lines.
_extract_verdict() {
    local output_file="$1"
    [[ -z "$output_file" || ! -f "$output_file" ]] && return 0

    local verdict_file="${output_file}.verdict"

    # Try to extract existing verdict block (last 7 lines)
    local last_lines
    last_lines=$(tail -7 "$output_file" 2>/dev/null) || return 0

    if echo "$last_lines" | head -1 | grep -q "^--- VERDICT ---$"; then
        echo "$last_lines" > "$verdict_file"
        return 0
    fi

    # No verdict block — synthesize from output
    # Check for VERDICT: CLEAN/NEEDS_ATTENTION pattern (interserve convention)
    local verdict_line
    verdict_line=$(grep -m1 "^VERDICT:" "$output_file" 2>/dev/null) || verdict_line=""

    local status="pass"
    local summary="No structured verdict found."
    if [[ "$verdict_line" == *"NEEDS_ATTENTION"* ]]; then
        status="warn"
        summary="${verdict_line#VERDICT: }"
    elif [[ "$verdict_line" == *"CLEAN"* ]]; then
        status="pass"
        summary="Agent reports clean completion."
    elif [[ -z "$verdict_line" ]]; then
        status="warn"
        summary="No verdict line in agent output."
    fi

    # Count files changed (look for FILES_CHANGED: pattern)
    local files_count=0
    local files_line
    files_line=$(grep -m1 "^FILES_CHANGED:" "$output_file" 2>/dev/null) || files_line=""
    if [[ -n "$files_line" ]]; then
        files_count=$(echo "$files_line" | tr ',' '\n' | wc -l | tr -d ' ')
    fi

    cat > "$verdict_file" <<VERDICT
--- VERDICT ---
STATUS: $status
FILES: $files_count changed
FINDINGS: 0 (P0: 0, P1: 0, P2: 0)
SUMMARY: $summary
---
VERDICT
}
```

2. Call `_extract_verdict "$OUTPUT"` after codex exec completes (both the gawk and fallback paths).

**Verify:** `bash -n scripts/dispatch.sh`. Test with a dry run + mock output file.

### Task 2.3: Update executing-plans to use verdict-first reading

**File:** `hub/clavain/skills/executing-plans/SKILL.md`

In Step 2A (Codex Dispatch), update the verification step (currently "Read each agent's output and verify"):

Replace the instruction at line 52 with:
```markdown
   - Read each agent's `.verdict` file first (7 lines — structured summary)
   - If STATUS is `pass`: trust the verdict, report success, move on
   - If STATUS is `warn` or `fail`: read the full output file for details, diagnose, retry or escalate
   - If no `.verdict` file: fall back to reading the full output
```

**Verify:** Read the updated SKILL.md and confirm the instructions are clear.

### Task 2.4: Update interserve skill for verdict-first reading

**File:** `hub/clavain/skills/interserve/SKILL.md`

In Step 3 "Read Verdict" (line 120-124), update to reference the `.verdict` sidecar:

Replace with:
```markdown
### Step 3: Read Verdict

Read the `.verdict` sidecar file (7 lines):
```bash
cat "/tmp/codex-result-*.md.verdict"
```

- `STATUS: pass` → report success, trust self-verification
- `STATUS: warn` + `SUMMARY: NEEDS_ATTENTION...` → read full output for details, retry once with tighter prompt
- `STATUS: error` or no `.verdict` file → fall back to reading full output file
- No verdict / garbled → fall back to Split mode or edit directly

**When to read full output (override verdict):**
- First dispatch in a new session (establish trust)
- Changes to critical paths (auth, data integrity, billing)
- STATUS: warn or fail
```

**Verify:** Read the updated SKILL.md for clarity.

---

## F3: Conditional Phase Skipping (iv-kmyj)

**Effort:** 3-4 hours | **Risk:** Medium | **Files:** 2

### Task 3.1: Add sprint_phase_whitelist() to lib-sprint.sh

**File:** `hub/clavain/hooks/lib-sprint.sh`

Add after the `sprint_complexity_label()` function (line 688), before the Checkpointing section:

```bash
# ─── Phase Skipping ──────────────────────────────────────────────

# Return the list of required phases for a given complexity tier.
# Phases not in this list should be skipped by the sprint orchestrator.
# Output: space-separated phase names (whitelist)
sprint_phase_whitelist() {
    local complexity="${1:-3}"
    case "$complexity" in
        1) echo "planned executing shipping done" ;;
        2) echo "planned plan-reviewed executing shipping done" ;;
        3|4|5) echo "brainstorm brainstorm-reviewed strategized planned plan-reviewed executing shipping done" ;;
        *) echo "brainstorm brainstorm-reviewed strategized planned plan-reviewed executing shipping done" ;;
    esac
}

# Check if a phase should be skipped for the given complexity tier.
# Returns 0 if phase should be SKIPPED, 1 if it should be executed.
# (Convention: 0 = skip, 1 = execute — mnemonic: 0 = "yes, skip")
sprint_should_skip() {
    local phase="${1:?phase required}"
    local complexity="${2:-3}"

    local whitelist
    whitelist=$(sprint_phase_whitelist "$complexity")

    # Check if phase is in whitelist
    case " $whitelist " in
        *" $phase "*) return 1 ;;  # In whitelist → don't skip
        *) return 0 ;;             # Not in whitelist → skip
    esac
}

# Find the next non-skipped phase from current_phase for the given complexity.
# Walks the transition table, skipping phases not in the whitelist.
# Output: the next phase that IS in the whitelist (or "done" if none remain)
sprint_next_required_phase() {
    local current_phase="${1:?current phase required}"
    local complexity="${2:-3}"

    local phase="$current_phase"
    local next_phase

    # Walk forward through the transition table until we find a whitelisted phase
    while true; do
        next_phase=$(_sprint_transition_table "$phase")
        [[ -z "$next_phase" || "$next_phase" == "$phase" ]] && { echo "done"; return 0; }

        if ! sprint_should_skip "$next_phase" "$complexity"; then
            # Phase is in whitelist — this is the next required phase
            echo "$next_phase"
            return 0
        fi

        # Phase should be skipped — keep walking
        phase="$next_phase"
    done
}
```

**Verify:** `bash -n hooks/lib-sprint.sh`. Test the functions:
```bash
source hooks/lib-sprint.sh
sprint_phase_whitelist 1        # → "planned executing shipping done"
sprint_should_skip "brainstorm" 1 && echo "skip" || echo "execute"  # → "skip"
sprint_should_skip "planned" 1 && echo "skip" || echo "execute"     # → "execute"
sprint_next_required_phase "brainstorm" 1  # → "planned"
sprint_next_required_phase "brainstorm" 3  # → "brainstorm-reviewed"
```

### Task 3.2: Modify sprint_advance() to support phase skipping

**File:** `hub/clavain/hooks/lib-sprint.sh`

In `sprint_advance()` (line 471), after computing `next_phase` from the transition table (line 479), add a complexity check that may jump further ahead:

After line 480 (`[[ -z "$next_phase" || "$next_phase" == "$current_phase" ]] && return 1`), add:

```bash
    # Phase skipping: check if next_phase should be skipped for this complexity
    local complexity
    complexity=$(bd state "$sprint_id" complexity 2>/dev/null) || complexity="3"
    [[ -z "$complexity" || "$complexity" == "null" ]] && complexity="3"

    # Check force_full_chain override
    local force_full
    force_full=$(bd state "$sprint_id" force_full_chain 2>/dev/null) || force_full="false"

    if [[ "$force_full" != "true" ]] && sprint_should_skip "$next_phase" "$complexity"; then
        # Skip to the next required phase
        next_phase=$(sprint_next_required_phase "$current_phase" "$complexity")
        [[ -z "$next_phase" ]] && next_phase="done"
        echo "Phase: skipping to $next_phase (complexity $complexity)" >&2
    fi
```

This integrates cleanly because `sprint_advance()` already does the phase transition — we're just changing *which* phase it transitions to.

**Verify:** `bash -n hooks/lib-sprint.sh`. The function should still pass syntax check and the existing lock/stale-phase logic is untouched.

### Task 3.3: Add complexity classification and skip confirmation to sprint skill

The sprint skill is loaded via `/clavain:sprint` — it's the SKILL.md content embedded in the sprint command. The sprint command is at `hub/clavain/commands/sprint.md`.

**File:** `hub/clavain/commands/sprint.md`

In the sprint command's Step 1 (Brainstorm), **before** invoking `/clavain:brainstorm`, add complexity classification and skip logic:

Find the section that begins with "## Step 1: Brainstorm" and add before the brainstorm invocation:

```markdown
### Pre-Flight: Complexity Classification

Before starting the workflow, classify the task complexity:

```bash
export SPRINT_LIB_PROJECT_DIR="."
source "$(find ~/.claude/plugins/cache -path '*/clavain/*/hooks/lib-sprint.sh' 2>/dev/null | head -1)"
COMPLEXITY=$(sprint_classify_complexity "" "<the feature description from arguments>" 0)
COMPLEXITY_LABEL=$(sprint_complexity_label "$COMPLEXITY")
echo "Complexity: $COMPLEXITY ($COMPLEXITY_LABEL)"
```

If complexity is 1-2, present skip options via AskUserQuestion:

```yaml
AskUserQuestion:
  question: "Complexity {COMPLEXITY} ({LABEL}) detected. Skip early phases?"
  options:
    - label: "Skip to plan (Recommended)"
      description: "Skip brainstorm and strategy — go straight to writing a plan"
    - label: "Full workflow"
      description: "Run all phases including brainstorm and strategy"
    - label: "Override complexity"
      description: "Set a different complexity level"
```

Based on response:
- **Skip to plan**: Set `force_full_chain=false` on the bead and jump to Step 3 (Write Plan)
- **Full workflow**: Set `force_full_chain=true` on the bead and proceed normally from Step 1
- **Override complexity**: Ask for complexity 1-5, set on bead, re-evaluate

Store the complexity on the bead for sprint_advance() to use:
```bash
bd set-state "$CLAVAIN_BEAD_ID" "complexity=$COMPLEXITY" 2>/dev/null || true
```
```

**Verify:** Read the updated sprint.md and walk through the logic mentally for complexity 1, 2, and 3 tasks.

### Task 3.4: Test the full phase skipping flow

**Verification steps:**

1. Create a test bead with complexity 1:
```bash
bd create --title="Test: trivial rename task" --type=task --priority=3
bd set-state <id> complexity=1
```

2. Source lib-sprint.sh and verify:
```bash
sprint_phase_whitelist 1                          # → planned executing shipping done
sprint_should_skip "brainstorm" 1 && echo "SKIP"  # → SKIP
sprint_should_skip "strategized" 1 && echo "SKIP"  # → SKIP
sprint_should_skip "planned" 1 && echo "SKIP" || echo "KEEP"  # → KEEP
sprint_next_required_phase "brainstorm" 1          # → planned
```

3. Verify sprint_advance() skips correctly:
```bash
bd set-state <id> phase=brainstorm
sprint_advance <id> brainstorm
# Should log "Phase: skipping to planned (complexity 1)"
bd state <id> phase  # → planned
```

---

## Execution Order

1. **F1 Tasks 1.1-1.4** (Skill Budget Cap) — independent, no risk to other features
2. **F2 Tasks 2.1-2.4** (Verdict Header) — builds on F1's conventions
3. **F3 Tasks 3.1-3.4** (Phase Skipping) — most complex, benefits from F1+F2

Each feature is independently shippable. F1 can be committed and tested before starting F2.

## Acceptance Criteria

- [ ] `bash -n` passes for all modified shell scripts
- [ ] `/clavain:doctor` shows "skill budget: PASS" (no skills over 16K)
- [ ] SessionStart additionalContext is under 6K chars (verified in test session)
- [ ] dispatch.sh produces `.verdict` sidecar files after Codex runs
- [ ] executing-plans skill references verdict-first reading
- [ ] `sprint_phase_whitelist 1` returns abbreviated phase list
- [ ] `sprint_advance` skips phases for complexity 1-2 beads
- [ ] Sprint workflow presents skip confirmation for complexity 1-2 tasks
- [ ] `--full-chain` or `force_full_chain=true` overrides skipping
