# PRD: Clavain Token-Efficiency Overhaul

**Bead:** iv-1zh2
**Date:** 2026-02-16
**Brainstorm:** `docs/brainstorms/2026-02-16-clavain-token-efficiency-synthesis-brainstorm.md`
**Research:** `docs/research/token-efficiency-agent-orchestration-2026.md`

## Problem

Clavain's multi-agent orchestration spends tokens inefficiently: all skills load at session start (~2K tokens), agent results flow as full text into orchestrator context, no model tier enforcement, no complexity-based dispatch, and no session resume capability. A typical sprint consumes 3-5x more tokens than necessary.

## Solution

Six features across four phases that reduce token overhead at every layer: baseline context (lazy loading), agent results (structured contracts + artifact handoffs), dispatch cost (model routing + complexity gating), and session resilience (checkpointing).

## Features

### F1: Agent Model Declarations + Output Contracts
**What:** Every agent .md declares its model tier and output contract so dispatch and result parsing are predictable.
**Acceptance criteria:**
- [ ] 100% of agent .md files have explicit `model:` frontmatter (haiku/sonnet/opus)
- [ ] Every agent .md includes an "Output Contract" section specifying structured format
- [ ] Contract schema documented in `using-clavain/references/agent-contracts.md`
- [ ] Contract validation logged (advisory, not enforced) when agents return non-conforming output
**Existing bead:** iv-1zh2.2 (model routing), iv-1zh2.6 (contracts) — combined for implementation efficiency

### F2: Lazy Skill Loading
**What:** Split using-clavain into a lightweight catalog (<500 tokens, always loaded) and full reference (loaded on-demand per skill invocation).
**Acceptance criteria:**
- [ ] SessionStart hook injects <500 tokens of Clavain context (currently ~2K)
- [ ] Catalog includes one-line descriptions + routing hints for each skill (not just names)
- [ ] Companion plugin availability stored in env var, not injected into context
- [ ] Full skill instructions load only when the skill is invoked
- [ ] Agent .md files not in context until dispatch time
- [ ] Total Clavain overhead per session <1K tokens at baseline
**Existing bead:** iv-1zh2.7

### F3: Verdict File Schema + Artifact Handoffs
**What:** Standardize how agents return results: structured verdict header (5-line, <200 tokens) plus full detail at a file path.
**Acceptance criteria:**
- [ ] Verdict schema defined: `TYPE, STATUS, MODEL, TOKENS_SPENT, FILES_CHANGED, FINDINGS_COUNT, SUMMARY, DETAIL_PATH`
- [ ] Flux-drive agents write findings to `.clavain/verdicts/fd-<agent>.json`
- [ ] Sprint/quality-gates read verdict headers, not raw agent output
- [ ] No agent result exceeds 500 tokens when injected into orchestrator context
- [ ] Verdict files cleaned at sprint start, persisted across session within a sprint
**Existing bead:** iv-1zh2.4

### F4: Sprint Orchestrator Verdict Consumption
**What:** Sprint workflow reads structured verdicts and routes on STATUS field, only drilling into DETAIL_PATH for NEEDS_ATTENTION findings.
**Acceptance criteria:**
- [ ] Sprint orchestrator parses verdict headers without reading full agent output
- [ ] CLEAN verdicts consume <50 tokens of orchestrator context
- [ ] NEEDS_ATTENTION verdicts trigger selective detail read (specific findings, not full file)
- [ ] Sprint summary reports per-agent STATUS + token cost
- [ ] `max_turns` set on all Task dispatches in sprint skills
**Existing bead:** iv-1zh2.1

### F5: Complexity Classifier + Phase Skipping
**What:** Heuristic complexity scorer (1-5) that determines model tier, agent count, and sprint phase requirements before first dispatch.
**Acceptance criteria:**
- [ ] Complexity classifier runs before first dispatch, scores 1-5 based on file count + change scope + task type
- [ ] Score 1-2: sprint skips brainstorm + strategy, uses Haiku/Sonnet only
- [ ] Score 3: standard sprint, Sonnet agents
- [ ] Score 4-5: full sprint, Opus orchestration, full agent roster
- [ ] Flux-drive scales agent count: score 1-2 → 2 agents, 3-4 → 4-6, 5 → full roster
- [ ] `--skip-to <step>` flag added to sprint for explicit phase override
- [ ] Complexity can be revised upward mid-task, never downward
- [ ] Sprint displays complexity score and explains phase skipping decisions to the user
**Existing bead:** iv-1zh2.3

### F6: Session Checkpointing + Sprint Resume
**What:** Sprint writes checkpoint after each step, enabling resume from any point without re-running prior steps.
**Acceptance criteria:**
- [ ] Checkpoint written to `.clavain/checkpoint.json` after each sprint step
- [ ] Checkpoint includes: bead, phase, completed_steps, key_decisions, agent_verdicts, tokens_spent, git_sha
- [ ] `/sprint --resume` reads checkpoint, validates git SHA matches HEAD, skips completed steps
- [ ] `--from-step <n>` overrides checkpoint for forced re-run
- [ ] Agent verdicts persist across session boundaries (not just /tmp/)
- [ ] Checkpoint is human-readable JSON, git-ignored
**Existing bead:** iv-1zh2.5

## Non-goals

- **Compression/summarization**: LLMLingua and gist tokens break prompt caching. Not worth the tradeoff for Clavain's stable prompt patterns.
- **Third-party model routing**: No Gemini/Grok/OpenCode backends. Codex is the only non-Claude backend.
- **Auto-scaling agent count at runtime**: SoA-style dynamic agent spawning adds complexity without clear benefit for Clavain's structured workflows.
- **Token budget enforcement (hard limits)**: That's iv-8m38, a separate feature. This PRD provides the measurement infrastructure it needs.
- **LLM-assisted complexity classification**: Pure heuristic only. Using an LLM to classify complexity contradicts the goal of saving tokens.

## Dependencies

| Dependency | Status | Impact |
|-----------|--------|--------|
| Agent .md frontmatter format | Stable | F1 adds new fields |
| using-clavain skill structure | Stable | F2 restructures it |
| lib-gates.sh phase tracking | Stable | F6 extends it |
| Flux-drive fd-* agents | In interflux plugin | F1, F3 need agent .md edits |
| Sprint skill | In Clavain | F4, F5, F6 modify it |

## Implementation Order

```
F2 (lazy loading) → F3 (verdict schema) → F1 (contracts) → F4 (verdict consumption) → F5 (complexity) → F6 (checkpointing)
```

F2 first because it has the smallest blast radius and immediate savings. F3 defines the verdict schema before F1 references it in agent contracts. F4 consumes what F3 defines. F5 and F6 are additive on top.

## Open Questions

1. **Contract enforcement timing**: Advisory now, enforced after 2 weeks of data? Or enforced from day one with a grace period?
2. **Verdict file location**: `.clavain/verdicts/` (persistent, git-ignored) vs `/tmp/` (ephemeral). PRD assumes `.clavain/verdicts/`.
3. **Checkpoint git SHA validation**: Strict (refuse resume on mismatch) or warn (resume with warning)? PRD assumes warn.
4. ~~**Complexity classifier**: Pure heuristic or LLM-assisted for ambiguous cases?~~ **Resolved:** Pure heuristic only (moved to non-goals).

## Estimated Savings

| Layer | Feature | Expected Reduction |
|-------|---------|-------------------|
| Baseline context | F2 (lazy loading) | 75-88% of startup overhead |
| Agent results | F3 + F4 (verdicts) | 80% of orchestrator context from agents |
| Dispatch cost | F1 + F5 (routing + complexity) | 3-5x on routed tasks |
| Wasted work | F6 (checkpointing) | 30-50% on resumed sessions |

Note: these are NOT additive — they overlap at different layers.
