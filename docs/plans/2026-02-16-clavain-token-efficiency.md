# Clavain Token-Efficiency Overhaul — Implementation Plan

**Bead:** iv-1zh2
**Phase:** executing (as of 2026-02-16T18:46:39Z)
**PRD:** `docs/prds/2026-02-16-clavain-token-efficiency.md`
**Date:** 2026-02-16

---

## F2: Lazy Skill Loading (iv-1zh2.7)

**Effort:** 1-2 hours | **Risk:** Low | **Files:** 3

### Task 2.1: Create compact catalog

**File:** `hub/clavain/skills/using-clavain/SKILL.md`

Replace the current 49-line SKILL.md with a compact catalog (~25 lines, <500 tokens) that contains:
1. The "Quick Router" table (14 rows, ~300 tokens) — this IS the discoverability surface
2. The routing heuristic (3-step: detect stage → detect domain → invoke skill)
3. A one-liner: "For full routing tables: `using-clavain/references/routing-tables.md`"

Remove from always-loaded context:
- The "Red Flag" section (10 lines) — move to `references/skill-discipline.md`
- The Codex CLI install instructions — move to `references/codex-setup.md`

### Task 2.2: Trim SessionStart context injection

**File:** `hub/clavain/hooks/session-start.sh`

Currently the hook injects using-clavain content + companion discovery results + handoff context + sprint scan. Changes:
1. Companion discovery: store results in `CLAVAIN_COMPANIONS` env var (comma-separated list of detected companions), NOT in additionalContext. Skills that need companion info read the env var.
2. Sprint scan: keep as-is (it's useful context and already capped)
3. Handoff retrieval: keep as-is (capped at 40 lines, often empty)
4. In-flight agent detection: keep as-is (security-relevant)

Net effect: ~500 tokens removed from additionalContext (companion discovery paragraphs).

### Task 2.3: Verify token reduction

Run a session with the changes and check `/context` output. Clavain overhead should drop from ~2K to ~1K tokens.

**AC verification:**
- [ ] SessionStart injects <500 tokens of Clavain-specific context
- [ ] Catalog includes one-line descriptions + routing hints
- [ ] Companion availability in env var
- [ ] Full reference materials load on demand

---

## F3: Verdict File Schema + Artifact Handoffs (iv-1zh2.4)

**Effort:** 2-3 hours | **Risk:** Low | **Files:** 4-5

### Task 3.1: Define verdict schema

**File:** `hub/clavain/skills/using-clavain/references/agent-contracts.md` (new)

Define the universal verdict format:

```
TYPE: verdict | implementation
STATUS: CLEAN | NEEDS_ATTENTION | BLOCKED | ERROR
MODEL: haiku | sonnet | opus | codex
TOKENS_SPENT: <number>
FILES_CHANGED: [file1.go, file2.go]
FINDINGS_COUNT: <number>
SUMMARY: <one-line summary>
DETAIL_PATH: <path to full output>
```

Include examples for each TYPE and STATUS combination. Document the `.clavain/verdicts/` directory convention.

### Task 3.2: Create verdict writer utility

**File:** `hub/clavain/hooks/lib-verdict.sh` (new, ~40 lines)

Bash functions for agents to call:
- `verdict_init()` — create `.clavain/verdicts/` if missing, add to `.gitignore`
- `verdict_write <agent-name> <status> <summary> <detail-path>` — writes JSON to `.clavain/verdicts/<agent-name>.json`
- `verdict_read <agent-name>` — reads and outputs the structured header
- `verdict_clean()` — remove all verdict files (called at sprint start)

### Task 3.3: Update flux-drive agent prompts

**Files:** Core fd-* agents live in `plugins/interflux/agents/review/fd-*.md`. Clavain has generated domain agents in `hub/clavain/.claude/agents/fd-*.md`. Update both locations.

Add to each agent's instructions:
```
## Output Contract
After your analysis, output a structured verdict header:
TYPE: verdict
STATUS: CLEAN | NEEDS_ATTENTION
...
Then write your full analysis to the DETAIL_PATH.
```

Note: This only applies to Clavain's copy of fd-* agents. The interflux originals are modified separately (or Clavain overrides take precedence).

### Task 3.4: Add .clavain/verdicts/ to .gitignore

**File:** `hub/clavain/.gitignore`

Add `.clavain/verdicts/` entry.

**AC verification:**
- [ ] Verdict schema documented
- [ ] lib-verdict.sh passes `bash -n` syntax check
- [ ] .clavain/verdicts/ git-ignored
- [ ] At least one agent .md has Output Contract section

---

## F1: Agent Model Declarations + Output Contracts (iv-1zh2.6 + iv-1zh2.2)

**Effort:** 1-2 hours | **Risk:** Low | **Files:** 4 agent .md files + reference doc

### Task 1.1: Add model declarations to all agents

**Files:**
- `hub/clavain/agents/review/plan-reviewer.md` — already has `model: sonnet` ✓
- `hub/clavain/agents/review/data-migration-expert.md` — already has `model: sonnet` ✓
- `hub/clavain/agents/workflow/bug-reproduction-validator.md` — already has `model: sonnet` ✓
- `hub/clavain/agents/workflow/pr-comment-resolver.md` — already has `model: sonnet` ✓

All 4 agents already declare model. Task: verify each uses the right tier:
- plan-reviewer: sonnet (correct — review task)
- data-migration-expert: sonnet (correct — review task)
- bug-reproduction-validator: sonnet (correct — investigation + code execution)
- pr-comment-resolver: sonnet (correct — code changes)

### Task 1.2: Add Output Contract sections to all agents

**Files:** Same 4 agent .md files

Add to each agent's .md:

For review agents (plan-reviewer, data-migration-expert):
```
## Output Contract
TYPE: verdict
STATUS: CLEAN | NEEDS_ATTENTION
MODEL: sonnet
TOKENS_SPENT: (estimated)
FILES_CHANGED: []
FINDINGS_COUNT: <n>
SUMMARY: <one-line>
DETAIL_PATH: .clavain/verdicts/<agent-name>.md
```

For workflow agents (bug-reproduction-validator, pr-comment-resolver):
```
## Output Contract
TYPE: implementation
STATUS: COMPLETE | PARTIAL | FAILED
MODEL: sonnet
TOKENS_SPENT: (estimated)
FILES_CHANGED: [<files>]
FINDINGS_COUNT: 0
SUMMARY: <one-line>
DETAIL_PATH: .clavain/verdicts/<agent-name>.md
```

### Task 1.3: Document contract schema in reference

Already done in Task 3.1 — this task just links to it from the agent .md files.

**AC verification:**
- [ ] 100% of agents have model: declaration (already true)
- [ ] 100% of agents have Output Contract section
- [ ] Contracts reference the verdict schema from F3

---

## F4: Sprint Orchestrator Verdict Consumption (iv-1zh2.1)

**Effort:** 3-4 hours | **Risk:** Medium | **Files:** 3-4 sprint-related skills

### Task 4.1: Extract verdict parsing library

**File:** `hub/clavain/hooks/lib-verdict.sh` (extend from Task 3.2)

Add functions:
- `verdict_parse_all()` — reads all `.clavain/verdicts/*.json`, outputs a summary table (STATUS, AGENT, SUMMARY — one line per agent)
- `verdict_count_by_status()` — returns counts per STATUS (e.g., "3 CLEAN, 1 NEEDS_ATTENTION")
- `verdict_get_attention()` — returns only NEEDS_ATTENTION verdicts with their DETAIL_PATHs

### Task 4.2: Update sprint command to use verdicts

**File:** `hub/clavain/commands/sprint.md` (NOT skills/sprint/SKILL.md — sprint is a command)

After quality-gates dispatches review agents, instead of reading raw agent output:
1. Call `verdict_parse_all` to get the summary table
2. If all CLEAN: proceed to next step (one-line summary in context)
3. If any NEEDS_ATTENTION: read only those agents' DETAIL_PATHs for specific findings
4. Report per-agent STATUS in sprint summary

### Task 4.3: Add max_turns to Task dispatches

**Files:** All skills that dispatch via Task tool

Audit and add `max_turns` to every Task dispatch:
- Explore agents: `max_turns: 10`
- Review agents: `max_turns: 15`
- Implementation agents: `max_turns: 30`
- Research agents: `max_turns: 20`

### Task 4.4: Sprint summary with token tracking

**File:** `hub/clavain/commands/sprint.md`

Add a summary section at sprint completion:
```
Sprint Summary:
- Steps completed: 7/9
- Agents dispatched: 6
- Verdicts: 4 CLEAN, 2 NEEDS_ATTENTION
- Estimated tokens: 45,200
```

Token tracking is estimated (from verdict TOKENS_SPENT fields), not measured. Precise measurement is iv-8m38's job.

**AC verification:**
- [ ] Sprint reads verdict headers, not raw output
- [ ] CLEAN verdicts < 50 tokens in context
- [ ] max_turns set on all dispatches
- [ ] Sprint summary includes per-agent STATUS

---

## F5: Complexity Classifier + Phase Skipping (iv-1zh2.3)

**Effort:** 3-4 hours | **Risk:** Medium | **Files:** 2-3

### Task 5.1: Extend existing complexity classifier

**File:** `hub/clavain/hooks/lib-sprint.sh` (extend `sprint_classify_complexity` at line 541)

`sprint_classify_complexity` already exists and returns "simple"/"medium"/"complex". Extend it to:
1. Add a file_count parameter (currently only uses description word count)
2. Map to 1-5 integer scale: simple→1-2, medium→3, complex→4-5
3. Add keyword detection for research tasks (→5) and trivial tasks (→1)
4. Keep the existing `bd state` override mechanism
5. Return integer (not string) for programmatic use

The existing heuristic uses word count + ambiguity/simplicity signals. Add:
- File count thresholds (0-1→lower, 10+→higher)
- Research keywords: "explore", "investigate", "research", "brainstorm" → bump to 5
- Trivial keywords: "rename", "format", "typo", "bump" → floor at 1

### Task 5.2: Add phase skipping to sprint

**File:** `hub/clavain/commands/sprint.md`

Before Step 1 (brainstorm), run complexity classifier. Add to sprint skill:

```
## Pre-Step: Complexity Assessment
Run complexity_classify on the task. Display the score to the user:
"Complexity: 3/5 (moderate) — running standard sprint workflow"

Score-based routing:
- 1-2: Skip to Step 3 (write-plan), skip flux-drive review, use Sonnet-only agents
- 3: Standard workflow, all steps
- 4-5: Full workflow with Opus orchestration

The user can override with `--skip-to <step>` or `--complexity <1-5>`.
```

### Task 5.3: Scale flux-drive agent count

**File:** Quality-gates skill or flux-drive dispatch

When dispatching flux-drive agents, use complexity score:
- Score 1-2: 2 agents (fd-quality + fd-correctness)
- Score 3: 4 agents (+ fd-architecture + fd-safety)
- Score 4-5: full roster (all available fd-* agents)

**AC verification:**
- [ ] Complexity classifier returns 1-5 from heuristic
- [ ] Sprint displays score and explains routing
- [ ] Score 1-2 skips brainstorm + strategy
- [ ] Flux-drive agent count scales with score
- [ ] `--skip-to` override works

---

## F6: Session Checkpointing + Sprint Resume (iv-1zh2.5)

**Effort:** 3-4 hours | **Risk:** Medium | **Files:** 3-4

### Task 6.1: Define checkpoint schema

**File:** `hub/clavain/hooks/lib-sprint.sh` (extend)

```bash
# checkpoint_write <bead_id> <phase> <step_name> <plan_path>
checkpoint_write() {
    local bead="$1" phase="$2" step="$3" plan_path="$4"
    local git_sha=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    local checkpoint=".clavain/checkpoint.json"

    # Read existing checkpoint or create new
    # Append step to completed_steps array
    # Update phase, git_sha, timestamp
    # Write atomically (temp + mv)
}

# checkpoint_read
# Returns: JSON checkpoint or empty
checkpoint_read() {
    local checkpoint=".clavain/checkpoint.json"
    [ -f "$checkpoint" ] && cat "$checkpoint"
}

# checkpoint_validate
# Returns: 0 if git SHA matches, 1 if mismatch (with warning)
checkpoint_validate() {
    local saved_sha=$(checkpoint_read | jq -r '.git_sha // ""')
    local current_sha=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    if [ "$saved_sha" != "$current_sha" ] && [ "$saved_sha" != "unknown" ]; then
        echo "WARNING: Code changed since checkpoint (was $saved_sha, now $current_sha)"
        return 1
    fi
    return 0
}
```

### Task 6.2: Add checkpoint writes to sprint skill

**File:** `hub/clavain/commands/sprint.md`

After each step completes, call checkpoint_write. The sprint skill instructions should include:

```
After each step completes successfully:
1. Source lib-sprint.sh
2. Call checkpoint_write with current bead, phase, step name, and plan path
3. Continue to next step
```

### Task 6.3: Add --resume to sprint

**File:** `hub/clavain/commands/sprint.md`

At the top of sprint skill, before Step 1:

```
## Resume Check
If invoked with --resume:
1. Read checkpoint with checkpoint_read
2. Validate git SHA with checkpoint_validate (warn on mismatch, don't block)
3. Display: "Resuming from step <n>. Completed: [step1, step2, ...]"
4. Skip to the first incomplete step
5. Load agent verdicts from .clavain/verdicts/ if present

If invoked with --from-step <n>:
1. Skip directly to step <n> regardless of checkpoint
```

### Task 6.4: Add .clavain/checkpoint.json to .gitignore

**File:** `hub/clavain/.gitignore`

Add `.clavain/checkpoint.json` entry (may already be covered by the verdicts addition in F3).

**AC verification:**
- [ ] Checkpoint written after each sprint step
- [ ] --resume reads checkpoint and skips completed steps
- [ ] Git SHA mismatch warns but doesn't block
- [ ] --from-step overrides checkpoint
- [ ] Checkpoint is human-readable JSON

---

## Implementation Summary

| Feature | Bead | Effort | Files Changed | Depends On |
|---------|------|--------|---------------|------------|
| F2: Lazy loading | iv-1zh2.7 | 1-2h | 2 | — |
| F3: Verdict schema | iv-1zh2.4 | 2-3h | 4-5 | F2 |
| F1: Model + contracts | iv-1zh2.6, iv-1zh2.2 | 1-2h | 5 | F3 |
| F4: Verdict consumption | iv-1zh2.1 | 3-4h | 3-4 | F1 |
| F5: Complexity classifier | iv-1zh2.3 | 3-4h | 2-3 | F4 |
| F6: Checkpointing | iv-1zh2.5 | 3-4h | 3-4 | F4 |

**Total:** ~14-19 hours across 4 phases. F5 and F6 can be parallelized (both depend on F4, not each other).

## Test Strategy

Each feature has its own verification checklist. Additionally:
- `bash -n` syntax check on all modified .sh files
- Manual sprint run after F4 to validate end-to-end verdict flow
- `/context` check after F2 to validate token reduction
- Sprint with `--resume` after F6 to validate checkpointing

## Plan Review Findings (addressed)

| # | Source | Finding | Resolution |
|---|--------|---------|------------|
| P1-1 | Architecture | Sprint is a command, not a skill | Fixed: all refs now point to `commands/sprint.md` |
| P1-2 | Architecture | `sprint_classify_complexity` already exists | Fixed: F5 extends existing function, doesn't create new |
| P1-3 | Architecture | Flux-drive agents in interflux, not clavain | Fixed: both locations documented |
| P2-1 | Quality | Sprint is 288+ lines — extract verdict library | Addressed: lib-verdict.sh is a separate file |
| P2-2 | User-Product | Complexity score should be transparent | Added: sprint displays score and explains routing |
| P2-3 | Quality | Edge cases for missing verdict files | lib-verdict functions handle missing files gracefully |
| P2-4 | Performance | Verdict I/O latency | Acceptable: JSON writes are <5ms each, total <50ms for 10 agents |
