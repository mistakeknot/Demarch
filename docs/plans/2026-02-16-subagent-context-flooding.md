# Plan: Subagent Context Flooding Fix
**Bead:** iv-24qk
**Phase:** executing (as of 2026-02-17T00:15:34Z)

## Overview

Wire the existing `lib-verdict.sh` infrastructure into all multi-subagent processes, add file-based output to commands that currently return results inline (quality-gates, review), and create the `intersynth` plugin to provide dedicated synthesis subagents that keep agent prose entirely out of the host context.

**Expanded scope:** Created `intersynth` plugin with `synthesize-review` and `synthesize-research` agents. All 4 processes now delegate synthesis to intersynth instead of reading agent files directly.

## Tasks

### Task 1: Update quality-gates.md to use file-based output
**File:** `hub/clavain/commands/quality-gates.md`
**Changes:**
1. Add OUTPUT_DIR definition: `.clavain/quality-gates/` (cleaned at start of each run, gitignored)
2. Phase 3 (Gather Context): Write diff to `/tmp/qg-diff-{TS}.txt` (already partially done)
3. Phase 4 (Run Agents): Update agent prompt template to include the file-based output contract:
   - Write ALL findings to `{OUTPUT_DIR}/{agent-name}.md`
   - Do NOT return findings in response text
   - Follow the Findings Index format (SEVERITY | ID | Section | Title, then Verdict line)
4. Phase 4 (continued): Add polling for `.md` file completion (like flux-drive Step 2.3)
5. Phase 5 (Synthesize): Read only Findings Index from each file (first ~30 lines), NOT full TaskOutput
6. Phase 5 (continued): After reading each index, call `verdict_write()` with agent status + summary
7. Add verdict summary table to the report output
**Dependencies:** None
**Risk:** Low — follows established flux-drive pattern

### Task 2: Update review.md to use file-based output
**File:** `hub/clavain/commands/review.md`
**Changes:**
1. Add OUTPUT_DIR definition: `.clavain/reviews/{target}/` where target is PR number, branch, or "current"
2. Phase 2: Update agent prompts to write findings to `{OUTPUT_DIR}/{agent-name}.md` with the output contract
3. Phase 2: Add `.md` file polling for completion monitoring
4. Phase 4 (Synthesis): Read Findings Indexes instead of raw TaskOutput
5. Phase 4: Call `verdict_write()` per agent
6. Update the report format to include verdict summaries
**Dependencies:** None (can be done in parallel with Task 1)
**Risk:** Low

### Task 3: Update flux-drive synthesize.md to use verdict integration
**File:** `plugins/interflux/skills/flux-drive/phases/synthesize.md`
**Changes:**
1. Step 3.2: Enforce the existing instruction "read Findings Index first (~30 lines)" by making it the PRIMARY collection method, not a suggestion
2. Step 3.2: After reading each agent's index, call `verdict_write()`:
   ```bash
   source "${CLAUDE_PLUGIN_ROOT}/../../../hub/clavain/hooks/lib-verdict.sh"
   verdict_write "{agent-name}" "verdict" "{status}" "{model}" "{1-line summary}"
   ```
   Note: The orchestrator agent calls this — agents themselves don't call verdict_write
3. Step 3.2: Add explicit instruction: "Only read full prose body for agents with NEEDS_ATTENTION status or when resolving conflicts between agents"
4. Step 3.5 (Report): Add verdict summary table using `verdict_parse_all()` output format
**Dependencies:** None
**Risk:** Low — reinforces existing behavior

### Task 4: Update flux-research SKILL.md to use verdict integration
**File:** `plugins/interflux/skills/flux-research/SKILL.md`
**Changes:**
1. Phase 3 Step 3.1: Change "Read all .md files" to "Read Sources and Findings headers from each .md file (first ~40 lines)"
2. Step 3.1: After reading each agent's headers, call `verdict_write()` with type "research" and status based on findings quality
3. Step 3.2: When merging, only read full prose for high-confidence findings that need cross-referencing
4. Add verdict summary to the output report
**Dependencies:** None
**Risk:** Low

### Task 5: Add .clavain gitignore entries
**File:** `.gitignore` at project roots where quality-gates/reviews run
**Changes:**
1. Ensure `.clavain/quality-gates/` is gitignored
2. Ensure `.clavain/reviews/` is gitignored
3. `.clavain/verdicts/` is already handled by `verdict_init()` but verify
**Dependencies:** None
**Risk:** None

## Execution Order

Tasks 1-4 are independent and can be executed in parallel. Task 5 is trivial and can be done alongside any task.

## Verification

After all tasks:
1. Read each modified file and verify the output contract is present
2. Verify verdict_write calls reference the correct lib-verdict.sh path
3. Check that no process reads full agent prose by default (only Findings Index)
4. Verify gitignore entries exist

## Testing

These are skill/command files (markdown instructions for Claude Code agents). They cannot be unit-tested — verification is by review and by running the commands in a session.
