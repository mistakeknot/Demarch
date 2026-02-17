# Clavain Token Efficiency Trio — PRD

**Beads:** iv-ked1, iv-hyza, iv-kmyj
**Date:** 2026-02-16
**Brainstorm:** `docs/brainstorms/2026-02-16-clavain-token-efficiency-trio-brainstorm.md`

## Goal

Reduce Clavain's per-session token overhead by 30-50% for simple-to-moderate tasks through three independent, compounding improvements: skill budget enforcement, structured agent output extraction, and complexity-based phase skipping.

## Success Criteria

| Metric | Baseline | Target |
|--------|----------|--------|
| SessionStart additionalContext | 2-5KB | <6KB hard cap |
| Largest skill SKILL.md | 18.6KB (writing-skills) | <16KB per skill |
| Agent result tokens in orchestrator context | 2-10K per agent | <500 per agent (header only) |
| Sprint phases for complexity 1-2 tasks | 8 phases | 3-4 phases |
| Wall clock for trivial sprint | ~15 min | <5 min |

## Features

### F1: Skill Injection Budget Cap (iv-ked1)

**Decision:** Hybrid approach — runtime cap on SessionStart + authoring-time lint on skill sizes.

**Budget thresholds:**
- Per-skill SKILL.md: **16K chars warn, 32K chars error** at lint time
- SessionStart `additionalContext`: **6K chars hard cap** (truncate with overflow message)
- Skills exceeding 16K must split into entry point + `references/` directory

**Resolved questions:**
- Cap at 16K chars (matching myclaude). writing-skills (18.6KB) must be trimmed — move sections to references/.
- SessionStart and per-skill are separate budgets. SessionStart is already compact (~2-5KB); the 6K cap is a safety net, not an active constraint.

**Deliverables:**
1. `additionalContext` truncation in session-start.sh with overflow message
2. `skill_check_budget()` function in lib.sh — called by `/clavain:doctor`
3. Trim writing-skills SKILL.md to <16K (move verbose sections to references/)
4. Document budget convention in AGENTS.md

### F2: Summary-Mode Output Extraction (iv-hyza)

**Decision:** Universal verdict header contract for all agent results + dispatch.sh post-processing.

**Verdict header format:**
```
--- VERDICT ---
STATUS: pass|fail|warn|error
FILES: N changed
FINDINGS: N (P0: n, P1: n, P2: n)
SUMMARY: <1-2 sentence verdict>
---
```

The verdict header is the **last block** in agent output (not the first) so it can be extracted with `tail` without reading the full file. Full prose body stays in the output file for on-demand reading.

**Reading contract:**
- Orchestrator reads only the verdict header (last 7 lines) from each agent output file
- Full file content is never read into orchestrator context unless explicit debug request
- For flux-drive: Findings Index (first ~30 lines) + verdict header (last ~7 lines) = ~37 lines total per agent
- For Codex dispatch: verdict header (last ~7 lines) only

**Resolved questions:**
- No confidence score in v1. Keep the header minimal — 5 fields only.
- Verdict header is appended (not replaces) existing output format. No breaking change.

**Deliverables:**
1. Verdict header specification documented in shared-contracts.md
2. dispatch.sh: extract verdict header from output file, write to `{output}.verdict`
3. executing-plans/SKILL.md: read `.verdict` files instead of full output
4. interserve/SKILL.md: update result reading to use verdict-first pattern

### F3: Conditional Phase Skipping (iv-kmyj)

**Decision:** Phase whitelist per complexity tier + user confirmation at skip points. Opt-out by default (skipping is ON; user can force full chain).

**Phase whitelists:**

| Complexity | Label | Required Phases | Skipped |
|-----------|-------|----------------|---------|
| 1 | trivial | planned → executing → shipping → done | brainstorm, strategy, plan-review |
| 2 | simple | planned → plan-reviewed → executing → shipping → done | brainstorm, strategy |
| 3 | moderate | brainstorm → strategized → planned → plan-reviewed → executing → shipping → done | none |
| 4 | complex | full chain | none |
| 5 | research | full chain | none |

**Key design choices:**
- Complexity 1 still requires a plan (even a 3-line plan) — no direct brainstorm-to-execute path
- Complexity 2 keeps plan review (flux-drive) as a safety net
- Skipping is opt-out: sprint auto-skips unless user passes `--full-chain` or bead has `force_full_chain=true`
- Mid-sprint complexity change: re-evaluate at each skip point. If user adds scope, complexity may bump up and restore skipped phases for the remainder.

**User confirmation flow:**
When complexity 1-2 is detected, sprint shows:
```
Complexity: 2 (simple) — skipping brainstorm and strategy phases.
[Continue with plan] [Force full chain] [Override complexity]
```

**Resolved questions:**
- Opt-out (skipping enabled by default). Power users who want full chain can override.
- No mid-sprint re-evaluation in v1 — complexity is set at sprint start and locked. Re-evaluation is a v2 feature.

**Deliverables:**
1. `sprint_phase_whitelist()` function in lib-sprint.sh
2. `sprint_should_skip()` function — checks current phase against whitelist
3. Integration into sprint skill: check whitelist before each phase command
4. `--full-chain` flag support in sprint invocation
5. User confirmation dialog via AskUserQuestion

## Architecture

```
Session Start                        Sprint Workflow
─────────────                        ───────────────
session-start.sh                     /clavain:sprint
  │                                    │
  ├─ Load using-clavain (370 tok)      ├─ Classify complexity (1-5)
  ├─ Companion alerts (200-500)        ├─ Get phase whitelist for tier
  ├─ Sprint/discovery context          ├─ For each phase:
  ├─ Handoff context (0-2K)            │   ├─ Is phase in whitelist? → Execute
  ├─ [NEW] Cap at 6K total ◄───────   │   ├─ Not in whitelist? → Skip
  └─ Output additionalContext          │   └─ Skip → advance_phase() to next
                                       │
Skill Invocation                     Agent Results
────────────────                     ─────────────
Skill tool → loads SKILL.md          dispatch.sh / Task tool
  │                                    │
  ├─ [NEW] Size < 16K? ✓              ├─ Agent writes full output to file
  ├─ Size 16-32K? ⚠ warn              ├─ [NEW] Append verdict header (last 7 lines)
  └─ Size > 32K? ✗ error              ├─ [NEW] Extract .verdict file
                                       └─ Orchestrator reads .verdict only
```

## Non-Goals

- **No changes to Claude Code's Skill tool** — Clavain can't modify built-in tool behavior. Budget enforcement is at authoring and injection time only.
- **No LLM-based complexity classification** — the heuristic classifier is fast and free. An LLM call to classify complexity would cost tokens to save tokens.
- **No sprint-level token budgets** — that's iv-8m38 (token budget controls). This PRD only addresses per-session workflow efficiency.
- **No changes to flux-drive's internal synthesis** — the Findings Index contract stays as-is. We add the verdict header as supplementary.

## Implementation Order

F1 → F2 → F3 (ordered by independence and risk)

- **F1 (budget cap)** has no dependencies, is pure defense, and prevents future problems
- **F2 (verdict header)** builds on F1's convention (compact output) and establishes the contract F3 relies on
- **F3 (phase skipping)** is the most complex and benefits from F1+F2 being in place (cheaper phases to skip)

Each feature is independently shippable — completing F1 alone is valuable.
