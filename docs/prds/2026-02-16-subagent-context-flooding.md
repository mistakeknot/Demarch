# PRD: Subagent Context Flooding Fix
**Bead:** iv-24qk

## Problem Statement

Multi-subagent dispatch commands (flux-drive, flux-research, quality-gates, review) return full agent output into the main context window, consuming 20-40K tokens. Sprint workflows that chain multiple phases exhaust context before reaching the shipping step.

## Users

Claude Code agents running sprint workflows, flux-drive reviews, quality-gates, and code reviews.

## Success Criteria

1. Quality-gates and review write agent findings to files instead of returning inline
2. Flux-drive synthesis reads Findings Indexes (30 lines) instead of full prose (3K lines) per agent
3. All processes call `verdict_write()` after agent completion for structured handoff
4. Sprint workflows can complete all 9 steps without context exhaustion
5. No behavioral change — same findings quality, just stored on disk

## Features

### F1: Quality-Gates File Output (P0)
Quality-gates currently receives agent results via TaskOutput inline. Change to:
- Define OUTPUT_DIR: `.clavain/quality-gates/{timestamp}/`
- Agent prompts tell agents to write to `{OUTPUT_DIR}/{agent-name}.md`
- Synthesis reads verdict summaries instead of raw TaskOutput
- Files: `hub/clavain/commands/quality-gates.md`

### F2: Review File Output (P0)
Same pattern as quality-gates but for the review command:
- Define OUTPUT_DIR: `.clavain/reviews/{pr-number or branch}/`
- Agent prompts include file-based output contract
- Synthesis reads from files
- Files: `hub/clavain/commands/review.md`

### F3: Flux-Drive Verdict Integration (P1)
Flux-drive already writes to files but reads everything fully in synthesis:
- After reading each agent's Findings Index, call `verdict_write()` with status + summary
- Synthesis uses `verdict_parse_all()` for the summary table
- Only drill down to full prose for NEEDS_ATTENTION or conflict resolution
- Files: `plugins/interflux/skills/flux-drive/phases/synthesize.md`

### F4: Flux-Research Verdict Integration (P1)
Same as F3 but for research:
- After reading each agent's Sources/Findings headers, call `verdict_write()`
- Synthesis uses verdict summaries
- Files: `plugins/interflux/skills/flux-research/SKILL.md`

### F5: Shared Output Contract (P1)
Extract the common "write to file, not inline" prompt section into a reusable reference:
- Create `hub/clavain/docs/output-contract.md` or equivalent
- Quality-gates, review, flux-drive, flux-research all reference it
- Ensures consistency across all multi-agent processes

## Non-Goals

- Changing agent dispatch mechanisms (already background)
- Modifying individual agent behaviors
- Token budgeting (handled by budget.yaml)
- Interserve/Codex dispatch

## Risks

- **Low**: Agents may not follow the file output contract perfectly. Mitigation: existing flux-drive agents already follow this contract successfully.
- **Low**: Verdict files accumulate on disk. Mitigation: `verdict_clean()` at sprint start, `.clavain/verdicts/` is gitignored.
