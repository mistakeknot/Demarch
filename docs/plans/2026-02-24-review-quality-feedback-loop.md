# Review Quality Feedback Loop Plan

**Bead:** iv-6dqrj
**Phase:** executing (as of 2026-02-25T06:51:56Z)
**Brainstorm:** docs/brainstorms/2026-02-24-review-quality-feedback-loop-brainstorm.md

## Task 1: Add `interspect-verdict` hook ID to allowlist
- [x] In `hooks/lib-interspect.sh`, add `interspect-verdict` to `_interspect_validate_hook_id()` case statement (line ~2203)

## Task 2: Create `interspect-verdict.sh` PostToolUse hook
- [x] Create `hooks/interspect-verdict.sh` — PostToolUse hook that fires on Task tool
- [x] Filter: only process when `tool_input.subagent_type` contains `intersynth:synthesize-review`
- [x] Parse `tool_input.prompt` to extract OUTPUT_DIR path (the directory containing verdict files)
- [x] Fall back to `.clavain/verdicts/` if OUTPUT_DIR not parseable
- [x] Read each `.json` verdict file in the verdicts directory
- [x] For each verdict, insert a `verdict_recorded` evidence event with context JSON:
  ```json
  {
    "verdict_status": "CLEAN|NEEDS_ATTENTION",
    "finding_count": 3,
    "agent": "fd-architecture",
    "detail_path": ".clavain/quality-gates/fd-architecture.md"
  }
  ```
- [x] Use `_interspect_insert_evidence` with source=agent name, event=`verdict_recorded`, hook_id=`interspect-verdict`
- [x] Fail-open (exit 0 always), 5s timeout

## Task 3: Register hook in hooks.json
- [x] Add second PostToolUse entry to `hooks/hooks.json` matching `Task` tool
- [x] Command: `${CLAUDE_PLUGIN_ROOT}/hooks/interspect-verdict.sh`
- [x] Timeout: 5 seconds

## Task 4: Add `_interspect_get_agent_quality_scores()` query function
- [x] In `hooks/lib-interspect.sh`, add function after `_interspect_get_overlay_eligible()` (~line 669)
- [x] Query: aggregate `verdict_recorded` events per agent from evidence table
- [x] Compute quality score (0-100) based on:
  - `finding_density` = avg finding_count across verdict_recorded events
  - `attention_rate` = pct of verdicts with NEEDS_ATTENTION status
- [x] Output: `agent|verdict_count|avg_findings|attention_rate_pct`
- [x] Used by `/interspect` status command to display agent performance

## Task 5: Update CLAUDE.md
- [x] Add `interspect-verdict.sh` to Quick Commands syntax check list
- [x] Note the new `verdict_recorded` event type in evidence docs

## Task 6: Test and commit
- [x] Run `bash -n` syntax checks on all modified files
- [ ] Commit with conventional format
