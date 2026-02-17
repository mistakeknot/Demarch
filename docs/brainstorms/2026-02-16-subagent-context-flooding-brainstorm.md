# Subagent Context Flooding Fix
**Bead:** iv-24qk
**Phase:** brainstorm (as of 2026-02-17T00:10:34Z)

## What We're Building

A consistent "write-behind" protocol for all multi-subagent dispatch processes (flux-drive, flux-research, quality-gates, review, brainstorm) so that agent results are persisted to disk and only summaries enter the main agent's context window.

## Why This Matters

When flux-drive dispatches 6-8 reviewer agents and each returns 3-5K tokens of review prose, the orchestrator loses ~30K tokens of context capacity reading their output. Quality-gates and review are worse — they return agent results inline through TaskOutput, meaning the full prose enters the main conversation. This causes:

1. **Context exhaustion** — sprint workflows that chain brainstorm → strategy → plan → execute → quality-gates can exhaust context before shipping
2. **Lost coherence** — when context compresses, the main agent loses track of earlier phases
3. **Redundant content** — agent results are already written to files (in flux-drive/research) but then also read fully into context

## Current State (Problem Analysis)

| Process | Background dispatch? | File output? | Context flooding? | Root cause |
|---------|---------------------|-------------|-------------------|------------|
| flux-drive | Yes | Yes (.md files) | Yes | Synthesis reads ALL agent files fully |
| flux-research | Yes | Yes (.md files) | Yes | Synthesis reads ALL agent files fully |
| quality-gates | Yes | No | **Severe** | Agent results come back via TaskOutput inline |
| review | Yes | No | **Severe** | Agent results come back via TaskOutput inline |
| brainstorm | Partial (1 agent) | No | Mild | repo-research-analyst returns inline |

## Existing Infrastructure (Unused)

`lib-verdict.sh` (128 lines) provides a complete verdict file system:
- `verdict_write()` — structured JSON with status, summary, detail path, token count
- `verdict_parse_all()` — summary table (STATUS, AGENT, SUMMARY)
- `verdict_count_by_status()` — "3 CLEAN, 1 NEEDS_ATTENTION"
- `verdict_get_attention()` — only agents needing human review
- `verdict_total_tokens()` — total token cost

**This infrastructure is never called by any skill or command.** Wiring it in is the core of this fix.

## Proposed Solution

### Pattern: Structured Verdict Protocol

Every multi-subagent dispatch follows this contract:

1. **Dispatch**: Launch agents with `run_in_background: true` (already done in most cases)
2. **Agent output**: Agents write full findings to files (already done in flux-drive/research; add to quality-gates/review)
3. **Verdict write**: After agent completes, call `verdict_write()` with a 1-line summary + status
4. **Orchestrator reads verdicts**: Use `verdict_parse_all()` to get the summary table (~5 tokens per agent)
5. **Selective drill-down**: Only `verdict_get_attention()` agents' detail files get read

### Changes Per Process

**flux-drive (SKILL.md synthesis phase)**:
- Phase 3 Step 3.2: Read Findings Index only (first ~30 lines per file) — ALREADY SPECIFIED but not enforced
- Add: After reading index, call `verdict_write()` with agent name, status (from verdict line), and 1-line summary
- Change: Instead of reading full prose, use verdict summaries. Only read full prose for conflicts or NEEDS_ATTENTION agents

**flux-research (SKILL.md synthesis phase)**:
- Step 3.1: Same pattern — read Sources + Findings headers, write verdict, selective drill-down

**quality-gates (command)**:
- Add: Write diff to temp file (already partially done)
- Add: Tell agents to write findings to `{OUTPUT_DIR}/{agent-name}.md` instead of returning inline
- Add: Use polling for `.md` file completion (same as flux-drive)
- Add: Call `verdict_write()` per agent after completion
- Phase 5 synthesis: Read verdicts, not raw output

**review (command)**:
- Same changes as quality-gates
- Add: OUTPUT_DIR pattern for review output files

**brainstorm (command)**:
- Phase 1.1: repo-research-analyst already returns concise output (~500 tokens). Lower priority for optimization.

### Prompt Contract for Agents

All agent prompts get a standard output section:

```markdown
## Output Contract

Write ALL findings to `{OUTPUT_DIR}/{agent-name}.md`.
Do NOT return findings in your response text.
Your response text should be a single line: "Findings written to {OUTPUT_DIR}/{agent-name}.md"

File structure:
### Findings Index
- SEVERITY | ID | "Section" | Title
Verdict: safe|needs-changes|risky

### Summary
[3-5 lines]

### Issues Found
[detailed findings]
```

This contract already exists in flux-drive's `shared-contracts.md` and launch phase. It needs to be extended to quality-gates and review.

## Key Decisions

1. **Verdict files are ephemeral** — cleaned at sprint start, not committed to git
2. **Findings Index is the context-efficient summary** — ~30 lines per agent instead of ~3K
3. **Full prose stays on disk** — available for `/clavain:resolve` and human review
4. **lib-verdict.sh is the single source of truth** — all processes use the same verdict infrastructure
5. **Backward compatible** — processes that don't use the verdict system continue to work (verdict functions are additive)

## Scope

### In Scope
- Wire `lib-verdict.sh` into flux-drive synthesis
- Wire `lib-verdict.sh` into flux-research synthesis
- Add file-based output to quality-gates (currently inline)
- Add file-based output to review (currently inline)
- Enforce Findings Index-first reading pattern in synthesis phases
- Add OUTPUT_DIR patterns to quality-gates and review commands

### Out of Scope
- Changing agent dispatch (already background in most cases)
- Modifying individual agent behaviors (they already follow the contract when told to)
- Token budgeting (handled by existing budget.yaml system)
- Interserve/Codex dispatch (separate mechanism)

## Open Questions

None — the solution is well-constrained by existing infrastructure.

## Estimated Impact

- **Context savings**: ~20-40K tokens per quality-gates invocation, ~15-25K per flux-drive synthesis
- **Sprint endurance**: Sprint workflows should reach Step 9 (Ship) without context exhaustion
- **No behavioral change**: Same findings, same quality — just stored on disk instead of in context
