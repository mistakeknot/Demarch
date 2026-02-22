# Token Consumption Sources Analysis — Interverse Project

**Date:** 2026-02-18
**Scope:** Research-only. No code or files modified.
**Token estimation rule:** 4 chars ≈ 1 token (rough but consistent)

---

## Executive Summary

The single biggest lever for token savings is **subagent dispatch overhead in interflux/flux-drive**. A single full flux-drive run injects 148,728 bytes (~37,182 tokens) of agent system prompts — before any actual work or file reading occurs. The second biggest lever is the **interdoc SKILL.md**, which alone costs ~12,205 tokens whenever `/interdoc` is invoked.

Session startup overhead is **well-controlled** — capped at 6,000 chars — and is not the primary concern.

---

## Area 1: Session Startup Overhead

### What runs on every session start

Four hooks fire at session start:

| Hook | Location | What it does | Context injected |
|------|----------|-------------|-----------------|
| `session-start.sh` | `os/clavain/hooks/` | Injects using-clavain skill, sprint state, handoff context, companion alerts | Up to 6,000 chars |
| `session-start.sh` | `plugins/interlock/hooks/` | Registers agent with Intermute, sets up git index isolation | ~180 chars |
| `session-start.sh` | `plugins/interject/hooks/` | Checks inbox for high-relevance discoveries | 0–200 chars if items exist, else silent |
| `session-start.sh` | `plugins/intermux/hooks/` | Writes /tmp mapping file | 0 chars (no injection) |

### Clavain session-start context breakdown

The Clavain session-start hook assembles `additionalContext` with these components (in priority order, shed if over cap):

1. **Preamble + using-clavain SKILL.md** — 1,492 bytes (injected in full every session)
2. **Companion alerts** — variable (0–500 bytes: Intermute agent count, beads health)
3. **Conventions reminder** — ~180 bytes
4. **Setup hint** — ~80 bytes
5. **Upstream staleness warning** — ~120 bytes (if stale)
6. **Sprint context** — variable (0–500 bytes if active sprint scan returns data)
7. **Discovery context** — variable (0–100 bytes from interphase)
8. **Sprint resume hint** — variable (0–200 bytes if active sprint found)
9. **Handoff context** — capped at 40 lines from `.clavain/scratch/handoff-latest.md`
10. **In-flight agents** — variable (0–300 bytes)

**Hard cap:** `ADDITIONAL_CONTEXT_CAP=6000` chars (~1,500 tokens). Sections are shed whole (lowest priority first) when over cap.

### CLAUDE.md stack loaded per Clavain session

These are loaded automatically by Claude Code as persistent system prompt:

| File | Path | Bytes | Tokens |
|------|------|-------|--------|
| Global CLAUDE.md | `/home/mk/.claude/CLAUDE.md` | 13,001 | 3,250 |
| Root CLAUDE.md | `/root/CLAUDE.md` | 566 | 141 |
| Projects CLAUDE.md | `/root/projects/CLAUDE.md` | 167 | 42 |
| Interverse CLAUDE.md | `/root/projects/Interverse/CLAUDE.md` | 3,382 | 845 |
| Clavain CLAUDE.md | `/root/projects/Interverse/os/clavain/CLAUDE.md` | 3,349 | 837 |
| Session hook injection | (capped at 6,000 chars) | 6,000 | 1,500 |
| **Total baseline** | | **26,465** | **~6,616** |

**Assessment:** Session startup is efficient. The 6,000-char cap on hook injection is a good design. The global `CLAUDE.md` at 13,001 bytes (~3,250 tokens) is the largest single component of the static baseline.

---

## Area 2: Skill/Command System Prompts

Skills are loaded on-demand when the user invokes them (via the `Skill` tool). Commands are loaded when the user runs a `/command`. They are NOT pre-loaded into context.

### Clavain skills (15 skills, loaded only when invoked)

| Skill | File | Bytes | Tokens |
|-------|------|-------|--------|
| engineering-docs | `os/clavain/skills/engineering-docs/SKILL.md` | 11,968 | 2,992 |
| subagent-driven-development | `os/clavain/skills/subagent-driven-development/SKILL.md` | 10,044 | 2,511 |
| dispatching-parallel-agents | `os/clavain/skills/dispatching-parallel-agents/SKILL.md` | 8,444 | 2,111 |
| interserve | `os/clavain/skills/interserve/SKILL.md` | 7,923 | 1,981 |
| file-todos | `os/clavain/skills/file-todos/SKILL.md` | 7,626 | 1,907 |
| writing-plans | `os/clavain/skills/writing-plans/SKILL.md` | 6,378 | 1,595 |
| upstream-sync | `os/clavain/skills/upstream-sync/SKILL.md` | 6,049 | 1,512 |
| code-review-discipline | `os/clavain/skills/code-review-discipline/SKILL.md` | 5,485 | 1,371 |
| using-tmux-for-interactive-commands | `os/clavain/skills/using-tmux-for-interactive-commands/SKILL.md` | 5,074 | 1,269 |
| landing-a-change | `os/clavain/skills/landing-a-change/SKILL.md` | 4,557 | 1,139 |
| executing-plans | `os/clavain/skills/executing-plans/SKILL.md` | 4,428 | 1,107 |
| refactor-safely | `os/clavain/skills/refactor-safely/SKILL.md` | 3,826 | 957 |
| galiana | `os/clavain/skills/galiana/SKILL.md` | 3,727 | 932 |
| brainstorming | `os/clavain/skills/brainstorming/SKILL.md` | 2,488 | 622 |
| using-clavain | `os/clavain/skills/using-clavain/SKILL.md` | 1,492 | 373 |
| **Total (all 15)** | | **129,885** | **~32,471** |

Note: `using-clavain` is injected at session start (small at 1,492 bytes). The other 14 are on-demand.

### Clavain commands (52 commands, loaded when user runs /command)

| Command | Bytes | Tokens |
|---------|-------|--------|
| sprint.md | 18,560 | 4,640 |
| setup.md | 9,907 | 2,477 |
| doctor.md | 9,586 | 2,397 |
| interspect-status.md | 8,942 | 2,236 |
| work.md | 8,608 | 2,152 |
| triage.md | 7,763 | 1,941 |
| interspect-propose.md | 7,374 | 1,844 |
| quality-gates.md | 6,287 | 1,572 |
| brainstorm.md | 5,631 | 1,408 |
| review.md | 4,573 | 1,143 |
| (42 more smaller commands) | ~94,755 | ~23,689 |
| **Total (all 52)** | **180,986** | **~45,247** |

### Plugin skills (40 skills across all plugins, loaded when invoked)

| Skill | File | Bytes | Tokens |
|-------|------|-------|--------|
| interdoc | `plugins/interdoc/skills/interdoc/SKILL.md` | 48,821 | **12,205** |
| flux-drive | `plugins/interflux/skills/flux-drive/SKILL.md` | 25,617 | 6,404 |
| agent-native-architecture | `plugins/intercraft/skills/agent-native-architecture/SKILL.md` | 23,253 | 5,813 |
| writing-skills | `plugins/interdev/skills/writing-skills/SKILL.md` | 12,618 | 3,155 |
| interpeer | `plugins/interpeer/skills/interpeer/SKILL.md` | 12,477 | 3,119 |
| flux-research | `plugins/interflux/skills/flux-research/SKILL.md` | 9,964 | 2,491 |
| systematic-debugging | `plugins/intertest/skills/systematic-debugging/SKILL.md` | 9,872 | 2,468 |
| test-driven-development | `plugins/intertest/skills/test-driven-development/SKILL.md` | 9,867 | 2,467 |
| mcp-cli | `plugins/interdev/skills/mcp-cli/SKILL.md` | 9,237 | 2,309 |
| developing-claude-code-plugins | `plugins/interdev/skills/developing-claude-code-plugins/SKILL.md` | 8,807 | 2,202 |
| create-agent-skills | `plugins/interdev/skills/create-agent-skills/SKILL.md` | 8,736 | 2,184 |
| beads-workflow | `plugins/interphase/skills/beads-workflow/SKILL.md` | 7,962 | 1,991 |
| tool-time | `plugins/tool-time/skills/tool-time/SKILL.md` | 7,780 | 1,945 |
| layout | `plugins/interkasten/skills/layout/SKILL.md` | 7,532 | 1,883 |
| (26 more smaller skills) | ~100,837 | ~25,209 |
| **Total (all 40 plugin skills)** | **281,180** | **~70,295** |

**Notable outlier:** `interdoc/SKILL.md` at 48,821 bytes is 2x larger than the next biggest skill. It contains extensive inline reference documentation that could be split into on-demand reference files.

---

## Area 3: Subagent Dispatch Overhead

This is the highest-impact token source. When an orchestration command (like `/clavain:sprint` or `/interflux:flux-drive`) dispatches subagents, each subagent gets its full system prompt injected as the `system` field in the Task tool call.

### Interflux flux-drive agents (17 agents total)

When a full `flux-drive` run is triggered, it dispatches up to 17 agents in parallel:

**Review agents (12):**

| Agent | File | Bytes | Tokens |
|-------|------|-------|--------|
| fd-perception | `agents/review/fd-perception.md` | 9,852 | 2,463 |
| fd-systems | `agents/review/fd-systems.md` | 9,589 | 2,397 |
| fd-resilience | `agents/review/fd-resilience.md` | 9,564 | 2,391 |
| fd-decisions | `agents/review/fd-decisions.md` | 9,540 | 2,385 |
| fd-people | `agents/review/fd-people.md` | 9,535 | 2,384 |
| fd-game-design | `agents/review/fd-game-design.md` | 6,040 | 1,510 |
| fd-architecture | `agents/review/fd-architecture.md` | 5,914 | 1,479 |
| fd-correctness | `agents/review/fd-correctness.md` | 5,765 | 1,441 |
| fd-user-product | `agents/review/fd-user-product.md` | 5,540 | 1,385 |
| fd-safety | `agents/review/fd-safety.md` | 5,504 | 1,376 |
| fd-quality | `agents/review/fd-quality.md` | 5,407 | 1,352 |
| fd-performance | `agents/review/fd-performance.md` | 5,324 | 1,331 |

**Research agents (5):**

| Agent | File | Bytes | Tokens |
|-------|------|-------|--------|
| learnings-researcher | `agents/research/learnings-researcher.md` | 10,919 | 2,730 |
| best-practices-researcher | `agents/research/best-practices-researcher.md` | 7,850 | 1,963 |
| framework-docs-researcher | `agents/research/framework-docs-researcher.md` | 6,716 | 1,679 |
| repo-research-analyst | `agents/research/repo-research-analyst.md` | 5,941 | 1,485 |
| git-history-analyzer | `agents/research/git-history-analyzer.md` | 4,111 | 1,028 |

**Interflux agent system prompt subtotal: 123,111 bytes = ~30,778 tokens**

Plus the flux-drive SKILL.md (25,617 bytes = ~6,404 tokens) loaded into the orchestrating context.

**Total flux-drive invocation system prompt cost: 148,728 bytes = ~37,182 tokens** — before any code files are read.

Note: Each spawned subagent also inherits its own copy of the CLAUDE.md stack and session context, multiplying the base overhead.

### Interkasten agents (6 agents)

| Agent | File | Bytes | Tokens |
|-------|------|-------|--------|
| fd-pipeline-operations | `.claude/agents/fd-pipeline-operations.md` | 5,205 | 1,301 |
| fd-prompt-engineering | `.claude/agents/fd-prompt-engineering.md` | 5,066 | 1,267 |
| fd-plugin-structure | `.claude/agents/fd-plugin-structure.md` | 4,845 | 1,211 |
| fd-data-integrity | `.claude/agents/fd-data-integrity.md` | 4,694 | 1,174 |
| fd-api-surface | `.claude/agents/fd-api-surface.md` | 4,631 | 1,158 |
| fd-consumer-experience | `.claude/agents/fd-consumer-experience.md` | 4,626 | 1,157 |
| **Total** | | **29,067** | **~7,267** |

### Intersynth agents (2 agents)

| Agent | File | Bytes | Tokens |
|-------|------|-------|--------|
| synthesize-review | `agents/synthesize-review.md` | 5,632 | 1,408 |
| synthesize-research | `agents/synthesize-research.md` | 3,715 | 929 |
| **Total** | | **9,347** | **~2,337** |

### Other agents

- intercraft: `agent-native-reviewer.md` = 8,466 bytes (~2,117 tokens)
- interdoc: `interdocumentarian.md` = 6,241 bytes (~1,560 tokens)
- interfluence: `voice-analyzer.md` = 4,973 bytes (~1,243 tokens)
- tldr-swinton: 6 agents totaling 10,452 bytes (~2,613 tokens)

---

## Area 4: AGENTS.md and CLAUDE.md Sizes

These are loaded by Claude Code automatically when you `cd` into a project directory. AGENTS.md is also loaded when agents work in that directory.

### AGENTS.md files (non-vendor)

| File | Bytes | Tokens |
|------|-------|--------|
| `os/clavain/AGENTS.md` | 25,624 | 6,406 |
| `plugins/tldr-swinton/AGENTS.md` | 25,497 | 6,374 |
| `AGENTS.md` (root Interverse) | 23,833 | 5,958 |
| `infra/intercore/AGENTS.md` | 20,614 | 5,154 |
| `plugins/interkasten/AGENTS.md` | 15,815 | 3,954 |
| `plugins/interflux/AGENTS.md` | 13,206 | 3,302 |
| `services/intermute/AGENTS.md` | 11,464 | 2,866 |
| `plugins/interfluence/AGENTS.md` | 9,770 | 2,443 |
| `plugins/interdoc/AGENTS.md` | 8,901 | 2,225 |
| `infra/agent-rig/AGENTS.md` | 7,214 | 1,804 |
| `plugins/tuivision/AGENTS.md` | 6,100 | 1,525 |
| `plugins/interserve/AGENTS.md` | 5,525 | 1,381 |
| (26 more, all 1,000–4,198 bytes) | ~45,656 | ~11,414 |
| **Total (38 non-vendor files)** | **~218,853** | **~54,713** |

### CLAUDE.md files (non-vendor)

| File | Bytes | Tokens |
|------|-------|--------|
| `os/clavain/CLAUDE.md` | 3,349 | 837 |
| `plugins/interkasten/CLAUDE.md` | 5,719 | 1,430 |
| `plugins/tldr-swinton/CLAUDE.md` | 4,118 | 1,030 |
| `plugins/intermem/CLAUDE.md` | 5,175 | 1,294 |
| `infra/intercore/CLAUDE.md` | 3,796 | 949 |
| `plugins/interline/CLAUDE.md` | 3,899 | 975 |
| (others, all <3,500 bytes) | ~77,256 | ~19,314 |
| **Total (39 files, excluding vendor)** | **~108,478** | **~27,120** |

**Key insight:** AGENTS.md and CLAUDE.md files are loaded hierarchically. A session in `plugins/interflux/` loads the root Interverse CLAUDE.md (3,382), the interflux CLAUDE.md (2,353), and the global CLAUDE.md (13,001) — totaling ~4,680 tokens in static documentation before any work.

---

## Ranked Summary: Token Impact by Category

| Rank | Category | Scenario | Bytes | Est. Tokens | Notes |
|------|----------|----------|-------|-------------|-------|
| 1 | **Subagent dispatch — interflux flux-drive** | Single full run | 148,728 | **~37,182** | 17 agents × 7,242 avg bytes each. Repeats every review invocation. |
| 2 | **Skill/command system prompts (all)** | Full catalog available | 411,166 (skills+cmds) | **~102,792** | Not all loaded at once — per-invocation cost; interdoc alone is 12,205 tokens. |
| 3 | **AGENTS.md files (all projects)** | Monorepo-wide | 218,853 | **~54,713** | Loaded per-subdirectory; 4–6 files loaded per typical session (~10,000–30,000 tokens). |
| 4 | **Session startup (Clavain hook)** | Per session | 26,465 | **~6,616** | Well-controlled; hard cap at 6,000 chars for dynamic content. |
| 5 | **Interdoc SKILL.md alone** | Per `/interdoc` invocation | 48,821 | **~12,205** | Outlier — 2x the size of the next largest single skill. |
| 6 | **Global CLAUDE.md** | Every session | 13,001 | **~3,250** | Loaded in all sessions; contains tooling reference + behavioral rules. |

---

## The Single Biggest Lever: Interflux Subagent System Prompts

**~37,182 tokens per flux-drive run** — and this is just the system prompt overhead. Each of the 17 agents also reads files, generates output, and the synthesizer collects all results. The actual per-run cost is 2–4x this figure including conversation turns.

The five most-expensive agents are: `fd-perception` (2,463 tokens), `fd-systems` (2,397), `fd-resilience` (2,391), `fd-decisions` (2,385), and `fd-people` (2,384). These five together account for 11,020 tokens — almost 30% of the total agent system prompt budget.

**What drives the cost:** Each agent file contains:
1. A detailed behavioral identity section (~1,500 chars)
2. Lengthy task description and output format (~2,000 chars)
3. Domain-specific knowledge and pattern examples (~3,000–6,000 chars)

### Top optimization opportunities

**Opportunity 1 — Interflux agent system prompt compression (~37,182 tokens → target ~15,000)**
The review agents share significant structural boilerplate. A shared "base review agent" could hold the common behavioral rules, with each specialist agent containing only the domain-specific content. Estimated savings: 40–60%.

**Opportunity 2 — Interdoc SKILL.md refactor (~12,205 tokens → target ~3,000)**
At 48,821 bytes, `interdoc/SKILL.md` is 2x the next-largest skill. Much of it is inline reference documentation (generation mode, update mode, harmonization rules, output schema). These are already referenced as separate files in `./references/` but may be duplicated or over-included inline. Splitting to true lazy-loading references could save ~9,000 tokens per `/interdoc` invocation.

**Opportunity 3 — Global CLAUDE.md triage (~3,250 tokens / session)**
The global `~/.claude/CLAUDE.md` (13,001 bytes) is loaded in every session. It contains tooling reference material that could live in `~/.codex/AGENTS.md` instead (which Claude Code does not auto-load). Trimming 50% would save ~1,600 tokens per session — small per session but compounds across many sessions/subagents.

**Opportunity 4 — AGENTS.md size control**
The top-5 AGENTS.md files (`clavain/`, `tldr-swinton/`, `Interverse/`, `intercore/`, `interkasten/`) average 22,278 bytes (~5,570 tokens) each. When subagents work in these directories, this becomes base overhead for every agent turn. Audit for content that belongs in reference files instead.

---

## File Inventory (Key Files Referenced)

| File | Path | Bytes | Tokens |
|------|------|-------|--------|
| flux-drive SKILL.md | `/root/projects/Interverse/plugins/interflux/skills/flux-drive/SKILL.md` | 25,617 | 6,404 |
| interdoc SKILL.md | `/root/projects/Interverse/plugins/interdoc/skills/interdoc/SKILL.md` | 48,821 | 12,205 |
| quality-gates.md | `/root/projects/Interverse/os/clavain/commands/quality-gates.md` | 6,287 | 1,572 |
| review.md | `/root/projects/Interverse/os/clavain/commands/review.md` | 4,573 | 1,143 |
| sprint.md (largest command) | `/root/projects/Interverse/os/clavain/commands/sprint.md` | 18,560 | 4,640 |
| clavain session-start.sh | `/root/projects/Interverse/os/clavain/hooks/session-start.sh` | 16,225 | (script, not injected) |
| Global CLAUDE.md | `/home/mk/.claude/CLAUDE.md` | 13,001 | 3,250 |
| Clavain AGENTS.md | `/root/projects/Interverse/os/clavain/AGENTS.md` | 25,624 | 6,406 |
| Interverse AGENTS.md | `/root/projects/Interverse/AGENTS.md` | 23,833 | 5,958 |
| fd-perception.md (largest agent) | `/root/projects/Interverse/plugins/interflux/agents/review/fd-perception.md` | 9,852 | 2,463 |
| interflux agents total | `/root/projects/Interverse/plugins/interflux/agents/` | 123,111 | 30,778 |
