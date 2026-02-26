# Task Complexity Classification: Orchestration Command Template Standards

**Date:** 2026-02-23
**Scope:** Classify the task to route either `/sprint` (full lifecycle) or `/work` (fast execution)
**Input Task ID:** iv-fy2n
**Source:** wshobson/agents full-stack-feature pattern

---

## Task Summary

**Title:** Create a shared template/convention for all multi-step orchestration commands in Clavain

**Description:** Establish explicit behavioral rules for multi-step command execution:
1. Execute steps in order, no skipping
2. Write output files per step, read from files not context
3. Stop at checkpoints for user approval
4. Halt on failure and present error
5. Use only local agents
6. Never enter plan mode autonomously

**Apply to:** sprint, execute-plan, work, and similar commands
**Source Pattern:** wshobson/agents full-stack-feature pattern

**Metadata:**
- Has plan: No
- Has brainstorm: No
- Has PRD: No
- Complexity score: 3/5 (moderate)
- Priority: P3
- Type: task
- Bead phase: none
- Child bead count: 0

---

## Complexity Analysis

### Scope Assessment

**What already exists in Clavain:**
- **Command system:** `/work` (fast execution), `/execute-plan` (batch with checkpoints), `/sprint` (full lifecycle), `/sprint-status`, `/compound` (knowledge synthesis)
- **Architecture:** 54 commands, 16 skills, 3-layer routing (Stage → Domain → Concern), hooks for phase tracking, integration with interphase for gates
- **Patterns identified:** `/work` follows "task → execute → quality → ship" with TodoWrite tracking; `/execute-plan` has explicit checkpoints between batches; both enforce gate checks
- **Command files read:** `/work.md` (exec workflow), `/sprint-status.md` (workflow health), `/execute-plan.md` (batch execution)

**Scope of new work:**
- Document standardized template/convention applicable across all multi-step commands
- Specify 6 behavioral rules (ordered execution, file I/O, checkpoint logic, failure handling, agent scope, autonomy guards)
- Create canonical reference that can be applied to `/sprint`, `/execute-plan`, `/work`, and future multi-step commands
- This is architectural/policy work, not a code change

**Existing patterns that align:**
- `/work` already implements rules 1, 2, 4 (execute in order, file-based state, halt on test failure)
- `/execute-plan` implements rule 3 (checkpoints between batches)
- Phase tracking hooks (session-start, phase-gates, lib-gates) partially implement checkpoint logic
- No systematic enforcement of rules 5 & 6 (local agents only, never autonomous plan mode)

### Complexity Factors

**Factors increasing complexity (toward /sprint):**
1. **Cross-cutting concern** — affects 4+ existing commands + all future ones
2. **Pattern extraction required** — need to find where rules overlap vs. diverge across commands
3. **No existing spec to reference** — rules are inferred from behavior, not documented
4. **Potential ambiguity** — "never enter plan mode autonomously" requires definition of what "plan mode" means in context (brainstorm? strategy? write-plan skill?)
5. **Integration points uncertain** — unclear how rules interact with existing hooks (gates, phase tracking, discovery shims)

**Factors decreasing complexity (toward /work):**
1. **Clear requirements** — 6 explicit behavioral rules provided
2. **Existing patterns** — can extract from current `/work` and `/execute-plan` implementations
3. **No code changes needed** — purely documentation/convention work
4. **Single module** — all changes in Clavain, no cross-module dependencies
5. **Known scope** — template + convention docs, not a full feature build

### Routing Decision

**Complexity score breakdown:**
- **Scope clarity:** 75/100 (rules clear, integration points unclear → slight ambiguity)
- **Pattern leverage:** 65/100 (can extract from `/work` and `/execute-plan`, but need synthesis)
- **Single module:** 90/100 (purely Clavain work)
- **Risk profile:** 55/100 (low risk if documentation-only, higher if implies hook changes)

**Weighted average:** ~71/100 = **Moderate (3/5)**, on the boundary between `/work` and `/sprint`

### Why Not `/work`?

`/work` assumes a clear, executable plan exists. Here:
- **No plan exists** — the task is to CREATE a template/convention, not execute against one
- **Strategy needed** — need to determine which existing patterns to formalize vs. which are unique to each command
- **Potential ambiguity** — "never enter plan mode autonomously" requires clarification before proceeding

### Why Not Full `/sprint`?

`/sprint` is for new features, ambiguous scope, research-needed, security-sensitive, cross-cutting changes with **high complexity (4-5)**. Here:
- **Not a full feature** — this is design + documentation
- **Complexity only 3/5** — within fast-execution range once strategy is clear
- **Single module** — no cross-module research burden
- **Lower priority (P3)** — not urgent

### Optimal Routing: `/work` with Light Brainstorm

This task should use **`/work` with a brief strategy phase** (not full `/sprint`):

1. **Quick strategy:** (5-10 min)
   - Read existing `/work` and `/execute-plan` command definitions
   - Identify where rules 1-6 are already implemented vs. missing
   - Clarify what "plan mode autonomously" means (brainstorm? strategy? write-plan skill?)
   - Determine if changes to hooks are needed or just documentation

2. **Execute:** (30-45 min)
   - Create template/convention doc with 6 rules + rationale
   - Audit `/sprint`, `/execute-plan`, `/work` against template
   - Apply conventions to each command (inline comments or separate guide)
   - Create reference checklist for future commands

3. **Quality:** (10 min)
   - Verify all 4 target commands align with template
   - Check for conflicts with existing hooks
   - Get user approval before shipping

---

## Recommendation

**Routing:** `/work`
**Confidence:** 0.75
**Reason:** Moderate complexity (3/5), clear requirements, extractable patterns from existing commands, single module, low risk — all fit `/work` criteria; require brief strategy phase to clarify scope before execution.

---

## Key Findings for Router

1. **Existing patterns are strong:** Clavain already implements 4 of 6 rules (`/work` has ordered execution, file I/O, failure halting; `/execute-plan` has checkpoints). Template work is synthesis, not invention.

2. **Ambiguity on "plan mode autonomously":** Needs clarification — does this mean don't call `/brainstorm` skill automatically? Don't call `/write-plan` skill? The rules reference needs this definition.

3. **Hook integration unclear:** Rules 3 (checkpoints) and 5-6 (local agents, autonomy guards) may require changes to `lib-gates.sh`, `lib-discovery.sh`, or interspect routing. A quick audit is needed before committing to execution.

4. **Template → policy document:** Output should be a shared convention file (e.g., `docs/conventions/orchestration-command-rules.md`) that all commands cite, with inline examples from `/work`, `/execute-plan`, `/sprint`.

5. **Priority P3 fits `/work`:** Not urgent, doesn't block other work, can be done in one session, doesn't require multi-session planning.

---

## Next Steps (Post-Routing)

If routing to `/work`:

1. **Strategy (5 min):** Read `/work.md` and `/execute-plan.md` for patterns; define "plan mode autonomously"
2. **Create template doc** with 6 rules + examples
3. **Audit 4 commands** against template
4. **Commit to Clavain** with reference in each command's "See also" section

If `brainstorm` phase reveals new blockers (e.g., hook changes needed):
- Escalate to `/sprint` for full architecture review
- Create dependent beads for hook refactor if required
