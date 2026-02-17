# Clavain Token-Efficiency Synthesis Brainstorm

**Bead:** iv-1zh2
**Phase:** brainstorm (as of 2026-02-16T18:03:16Z)
**Date:** 2026-02-16
**Input:** Research doc `docs/research/token-efficiency-agent-orchestration-2026.md` + Clavain codebase analysis
**Goal:** Implementation-ready directions for each of 7 token-efficiency patterns, grounded in Clavain's actual architecture

---

## Finding 1: Lead-Orchestrator + Specialized Worker Roles

### What We Know
- AgentCoder: 3 lean agents (56.9K tokens) beat MetaGPT's 5 agents (138.2K) — 59% reduction
- MASAI: 5 modular sub-agents at <$2/issue on SWE-bench
- Clavain already does this partially: Opus orchestrates, Sonnet reviews, Haiku explores

### Current State in Clavain
- Sprint skill (`/sprint`) acts as orchestrator but doesn't enforce role boundaries
- Flux-drive triage selects from fd-* agents but the orchestrator (Claude) still sees all intermediate output
- Subagent results flow back into the parent context — no garbage collection

### Implementation Direction
**The orchestrator should never see raw code.** It should see only:
1. Structured verdicts from workers (CLEAN/NEEDS_ATTENTION + file list)
2. Dependency signals (what blocks what)
3. Budget consumption (tokens spent / remaining)

**Concrete changes:**
- Add `output_format: verdict` to all agent .md frontmatter — agents that return free-text get their output summarized before injecting into orchestrator context
- Sprint skill should dispatch via Task tool with `max_turns` limits — currently unbounded
- Background agents (`run_in_background: true`) should be default for any agent that doesn't need follow-up questions

### Acceptance Criteria
- [ ] Orchestrator context growth is O(n) in number of agents, not O(n*m) in agent output size
- [ ] Each worker agent has a declared max output format (verdict, diff, summary)
- [ ] Sprint workflow tracks tokens-per-step and can report total cost at completion

### Risks & Anti-Patterns
- **Over-summarization**: Workers compress away the actionable detail. Fix: verdicts include file:line references, not just "found issues"
- **Lost context on retry**: If a worker fails and needs retry, the orchestrator can't provide context it never saw. Fix: workers write full output to temp files, orchestrator gets summary + file path
- **Single point of failure**: Orchestrator crash loses all coordination. Fix: beads track which workers completed (already partially done via bead-agent-bind)

### Metrics
- Total orchestrator context consumed per sprint (before vs after)
- Number of re-dispatches caused by insufficient verdicts

---

## Finding 2: Cross-Model Specialization and Task Routing

### What We Know
- myclaude: 4 backends (Codex, Claude, Gemini, OpenCode) with cost arbitrage
- claude-router: Dynamic Haiku/Sonnet/Opus by query complexity
- Clavain interserve: Claude for orchestration, Codex for implementation (89% cost reduction on code gen)
- Amazon Bedrock: ~30% savings via automatic Sonnet/Haiku routing

### Current State in Clavain
- Agent .md files declare `model: sonnet` but only 2 agents use it — most inherit default
- Interserve toggle is binary (on/off), not complexity-aware
- No Gemini/Grok routing — only Claude + Codex
- Model routing skill (`/model-routing`) toggles between "economy" and "quality" presets

### Implementation Direction
**Three-tier routing with explicit cost signals:**

| Tier | Model | Use When | Token Cost |
|------|-------|----------|------------|
| Explore | Haiku | File search, grep, codebase navigation | ~$0.001/task |
| Review | Sonnet | Code review, plan review, quality checks | ~$0.01/task |
| Orchestrate | Opus | Sprint coordination, complex decisions | ~$0.05/task |
| Implement | Codex | Source code generation, refactoring | ~$0.005/task |

**Concrete changes:**
- Every agent .md MUST declare `model:` in frontmatter — no implicit defaults
- `dispatching-parallel-agents` skill should auto-select tier based on agent type (explore → haiku, review → sonnet)
- Interserve dispatch should accept complexity hints: `--tier fast` (spark) vs `--tier deep` (codex full)
- Add `estimated_cost` to agent dispatch logs for post-hoc analysis

### Acceptance Criteria
- [ ] 100% of agent .md files have explicit `model:` declaration
- [ ] Explore agents (codebase search, file listing) always use Haiku
- [ ] Dispatch logs include model tier and estimated token cost
- [ ] No Opus tokens spent on tasks that could use Sonnet

### Risks & Anti-Patterns
- **Haiku for complex reasoning**: Haiku hallucinate more on architectural questions. Fix: routing heuristic based on task type, not just prompt length
- **Model lock-in**: Hardcoding model names breaks when new models ship. Fix: use tiers (explore/review/orchestrate), not model names, in skills
- **Cost measurement gap**: Can't validate savings without baseline. Fix: interstat must be running (iv-dyyy dependency)

### Metrics
- Cost per sprint broken down by model tier
- Quality regression rate when downtiering (Opus → Sonnet, Sonnet → Haiku)

---

## Finding 3: Complexity-Based Dispatch and Resource Rules

### What We Know
- myclaude: Conditional phase skipping when score >= 8/10
- claude-flow: 3-tier complexity routing (WASM → Haiku → Opus)
- AgentCoder: Non-LLM executor for test runs — zero model cost
- SoA: Auto-scales agent count by problem complexity

### Current State in Clavain
- Sprint workflow always runs all 9 steps — no skipping
- Flux-drive triage selects agents but doesn't scale count by document complexity
- No complexity scoring — every task gets the same resource allocation
- Some operations (formatting, file moves) go through LLM unnecessarily

### Implementation Direction
**Complexity classifier at dispatch time:**

```
Input: task description + file count + change scope
Output: complexity score 1-5
Rules:
  1 (trivial): Single file, < 50 lines, formatting/rename → bash script, no LLM
  2 (simple): 1-3 files, clear spec → Haiku agent, max_turns=5
  3 (moderate): 3-10 files, some ambiguity → Sonnet agent, max_turns=15
  4 (complex): 10+ files, architectural → Opus agent, max_turns=30
  5 (research): Unknown scope, exploration → Opus + parallel Haiku explorers
```

**Concrete changes:**
- Sprint skill: skip brainstorm/strategy for complexity 1-2 tasks (direct to plan → execute)
- Flux-drive: scale agent count — complexity 1-2 gets 2 agents, 3-4 gets 4-6, 5 gets full roster
- Add `--skip-to <step>` flag to sprint for explicit phase skipping
- Non-LLM operations: file renames, formatting, dependency bumps → bash scripts via a "mechanical tasks" dispatcher

### Acceptance Criteria
- [ ] Complexity classifier exists and runs before first dispatch
- [ ] Trivial tasks (rename, format) complete without any LLM call
- [ ] Sprint skips brainstorm+strategy for complexity <= 2
- [ ] Flux-drive agent count correlates with document complexity

### Risks & Anti-Patterns
- **Misclassification**: A "simple" task turns out complex mid-execution. Fix: complexity can be revised upward mid-task, never downward
- **Skip too aggressively**: Skipping brainstorm on a task that needed it. Fix: classifier is conservative — defaults to moderate
- **Metric gaming**: Optimizing for low complexity scores rather than actual simplicity. Fix: track rework rate per complexity bucket

### Metrics
- Tasks completed per complexity bucket
- Token spend per complexity bucket
- Rework rate (tasks that needed re-dispatch at higher complexity)

---

## Finding 4: Artifact-First Handoffs Rather Than Full Transcripts

### What We Know
- File indirection: 70% context savings (Clavain production — prompt files in /tmp/)
- Codex CLI: File-based state passing between agents
- cco: Git worktree isolation — agents communicate via committed files, not shared context
- DeepCode: Blueprint distillation — compress source docs into high-signal plans

### Current State in Clavain
- Prompt files written to /tmp/ for subagent dispatch — already saves 70%
- But agent RESULTS still flow back as full text into orchestrator context
- Brainstorm → strategy → plan pipeline passes full documents, not summaries
- Flux-drive agents return full review text — no structured handoff format

### Implementation Direction
**Every handoff should be a file reference, not inline content.**

Three handoff types:
1. **Plan handoff**: Write plan to `docs/plans/`, pass path to executor — ALREADY DONE
2. **Verdict handoff**: Agent writes `{ verdict, files_changed, findings[] }` to `/tmp/verdict-<agent>.json`, orchestrator reads only the summary field
3. **State handoff**: Session-end hook writes `{ completed_steps, remaining_steps, key_decisions }` to `.clavain/session-state.json` for resume

**Concrete changes:**
- All flux-drive agents should write findings to `/tmp/fd-<agent>-findings.json` with structured schema
- Sprint orchestrator reads verdict files, not raw agent output
- Add `--artifact-path` to agent dispatch — agents write output there instead of returning it
- Session handoff skill already exists (`session-handoff.sh`) — extend it with structured state

### Acceptance Criteria
- [ ] No agent result exceeds 500 tokens when injected into orchestrator context
- [ ] Every agent handoff includes a file path to full output for drill-down
- [ ] Session resume loads structured state, not conversation replay
- [ ] Verdict schema is standardized across all agent types

### Risks & Anti-Patterns
- **File proliferation**: Hundreds of temp files per sprint. Fix: cleanup hook at session end
- **Stale artifacts**: Agent writes file, orchestrator reads stale version. Fix: atomic writes (write to .tmp, rename)
- **Lost nuance**: Structured verdicts lose the "why" behind findings. Fix: verdicts include `reasoning_path` field (file ref to full chain-of-thought)

### Metrics
- Orchestrator context consumed per agent handoff (target: < 500 tokens)
- Session resume time (structured state vs conversation replay)

---

## Finding 5: Context Compaction and Resumable State

### What We Know
- Anthropic SDK: ~85% compaction, quality 3.56/5
- Factory.ai anchored: 98.6% compaction, quality 3.70/5
- Prompt caching: 90% cost reduction for cached tokens, but compression breaks cache
- "Tokens per task, not tokens per request" — aggressive compression forces re-fetching

### Current State in Clavain
- Claude Code auto-compacts at context limits — Clavain doesn't control this
- No session state persistence between sessions (except beads)
- Sprint can't resume from step 5 without re-running steps 1-4
- Flux-drive re-dispatches all agents on retry — no incremental review

### Implementation Direction
**Session checkpointing, not compression.**

Instead of trying to compress the conversation, checkpoint the state:

```json
// .clavain/checkpoint.json
{
  "bead": "iv-1zh2",
  "phase": "executing",
  "completed_steps": ["brainstorm", "strategy", "plan", "plan-review"],
  "plan_path": "docs/plans/2026-02-16-token-efficiency.md",
  "key_decisions": [
    "Using tier-based routing instead of model names",
    "Complexity classifier before dispatch"
  ],
  "agent_verdicts": {
    "fd-architecture": { "status": "CLEAN", "path": "/tmp/fd-arch.json" },
    "fd-quality": { "status": "NEEDS_ATTENTION", "findings": 2 }
  },
  "tokens_spent": 45200,
  "context_at_checkpoint": "28%"
}
```

**Concrete changes:**
- Sprint skill writes checkpoint after each step completes
- `/sprint --resume` reads checkpoint and skips completed steps
- Agent verdicts are persisted (not just in /tmp/) so retry doesn't re-dispatch clean agents
- Phase tracking (lib-gates.sh) already exists — extend it with structured state

### Acceptance Criteria
- [ ] Sprint can resume from any step without re-running prior steps
- [ ] Agent verdicts persist across session boundaries
- [ ] Checkpoint file is human-readable and git-friendly
- [ ] No information loss on resume — key decisions are preserved

### Risks & Anti-Patterns
- **Stale checkpoints**: Checkpoint from yesterday doesn't reflect code changes since then. Fix: checkpoint includes git SHA, resume validates HEAD matches
- **Checkpoint bloat**: Every step adds state, checkpoint grows unbounded. Fix: cap at 5 key_decisions, rotate agent_verdicts
- **False resume**: Checkpoint says step 3 done, but step 3 output was wrong. Fix: checkpoint is advisory — user can force re-run with `--from-step 3`

### Metrics
- Session resume success rate (resume works without rework)
- Tokens saved per resume vs full re-run

---

## Finding 6: Structured Return Formats and Strict Contracts

### What We Know
- JSON Whisperer (RFC 6902): 31% token reduction vs full regeneration
- TOON: 30-90% token reduction
- Codex dispatch: VERDICT: CLEAN/NEEDS_ATTENTION format
- OpenAI apply_patch: Model specifically trained on patch format

### Current State in Clavain
- Interserve agents return `VERDICT: CLEAN | NEEDS_ATTENTION` + `FILES_CHANGED: [list]` — good
- Flux-drive fd-* agents return free-text reviews — no structure contract
- Plan-reviewer returns prose with sections — semi-structured
- Bug-reproduction-validator has the best structure: Status, Steps, Findings, Root Cause, Evidence

### Implementation Direction
**Universal agent contract:**

Every agent returns exactly one of:
```
TYPE: verdict
---
STATUS: CLEAN | NEEDS_ATTENTION | BLOCKED | ERROR
FILES_CHANGED: [file1.go, file2.go]
FINDINGS_COUNT: 3
SUMMARY: One-line summary of what was found
DETAIL_PATH: /tmp/agent-detail-<id>.md
```

Or for implementation agents:
```
TYPE: implementation
---
STATUS: COMPLETE | PARTIAL | FAILED
FILES_CHANGED: [file1.go, file2.go]
TESTS_PASSING: true | false
SUMMARY: One-line summary of what was implemented
DETAIL_PATH: /tmp/agent-detail-<id>.md
```

**Concrete changes:**
- Add "Output Contract" section to every agent .md — template provided in `using-clavain/references/`
- Sprint orchestrator ONLY parses the structured header — full detail stays in DETAIL_PATH
- Flux-drive synthesizer reads structured headers for triage, only reads detail files for P0/P1 findings
- Validation: if an agent returns output that doesn't match contract, log a warning (don't crash)

### Acceptance Criteria
- [ ] Every agent .md includes an Output Contract section
- [ ] Orchestrator parses structured headers without reading full output
- [ ] Contract violations are logged and reported in sprint summary
- [ ] At least 80% token reduction in orchestrator context from agent results

### Risks & Anti-Patterns
- **Overly rigid contracts**: Agent can't express nuance. Fix: contracts are for orchestrator consumption; full detail always available at DETAIL_PATH
- **Contract drift**: Agent .md says one thing, agent output says another. Fix: validation hook checks contract compliance
- **Lowest common denominator**: Forcing all agents into same format loses agent-specific value. Fix: TYPE field allows multiple contract variants

### Metrics
- Contract compliance rate across agents
- Orchestrator context consumed from agent results (before vs after)

---

## Finding 7: Lazy Skill Loading and Policy Minimization

### What We Know
- task-orchestrator: 88% baseline context reduction via lazy loading
- code-mode-toon: Skills loaded only when task type matches
- Claude Code ToolSearch: MCP tools loaded on-demand, not at session start
- myclaude: 16K char skill injection budget cap
- Schema pruning: 15x cost reduction (RestMCP)

### Current State in Clavain
- SessionStart hook injects companion plugin discovery (~2K tokens) regardless of task
- 23 skills declared in plugin.json — all available at session start (skill descriptions in context)
- Model routing, interlock, intermute context injected even when not needed
- using-clavain skill provides routing tables — ~1K tokens of always-present context

### Implementation Direction
**Two-phase skill loading:**

Phase 1 (always loaded, < 500 tokens):
- Skill catalog: name + one-line description for each skill
- Quick reference: how to invoke `/clavain:<name>`
- Routing hint: "For code review use /review, for planning use /sprint"

Phase 2 (loaded on demand, when skill is invoked):
- Full skill instructions (SKILL.md content)
- Reference materials (routing tables, dispatch patterns)
- Agent definitions (only when dispatching that agent)

**Concrete changes:**
- Split using-clavain skill into `catalog.md` (phase 1, < 500 tokens) and `reference/` (phase 2)
- SessionStart hook injects ONLY the catalog, not full companion discovery results
- Companion plugin availability stored in env var, not context — checked when needed
- Skill injection budget: hard cap at 8K tokens per skill invocation (half of myclaude's 16K — Clavain skills are tighter)
- Agent .md files loaded ONLY when dispatched via Task tool — not pre-loaded

### Acceptance Criteria
- [ ] SessionStart injects < 500 tokens of Clavain context (currently ~2K)
- [ ] Skill invocation loads full instructions on-demand
- [ ] Agent definitions not in context until dispatch time
- [ ] Total skill context per session < 8K tokens (excluding the task-specific skill)

### Risks & Anti-Patterns
- **Cold start delay**: First skill invocation is slower because instructions load on-demand. Fix: acceptable tradeoff — savings compound across the session
- **Missing context**: Agent doesn't know about a skill it should recommend. Fix: catalog always present with one-liners — enough for routing
- **Split maintenance**: Catalog and full skill drift apart. Fix: catalog auto-generated from skill frontmatter

### Metrics
- SessionStart token injection (before vs after)
- Total Clavain context overhead per session
- Skill invocation latency (first use vs subsequent)

---

## Cross-Cutting Dependencies

```
Finding 7 (lazy loading) ──→ reduces baseline, makes everything cheaper
Finding 3 (complexity)   ──→ determines how many of the others to apply
Finding 2 (model routing) ──→ multiplies savings from findings 1, 4, 6
Finding 1 (orchestrator)  ──→ requires findings 4 + 6 for structured handoffs
Finding 6 (contracts)     ──→ enables finding 4 (artifact handoffs)
Finding 4 (artifacts)     ──→ enables finding 5 (checkpointing)
Finding 5 (checkpoints)   ──→ independent but benefits from all others
```

**Recommended implementation order:**
1. Finding 7 (lazy loading) — smallest change, immediate savings, no dependencies
2. Finding 6 (contracts) — standardizes agent output, enables later findings
3. Finding 2 (model routing) — declare tiers in all agent .md files
4. Finding 4 (artifact handoffs) — uses contracts from finding 6
5. Finding 1 (orchestrator roles) — uses handoffs from finding 4
6. Finding 3 (complexity dispatch) — can be added incrementally
7. Finding 5 (checkpointing) — benefits from all above, adds session resilience

**Total estimated savings (non-additive, overlapping):**
- Baseline context: 75-88% reduction (finding 7)
- Per-agent result overhead: 80% reduction (findings 4 + 6)
- Cost per sprint: 3-5x reduction (finding 2)
- Wasted work: 30-50% reduction (findings 3 + 5)

---

## Implementation Phases

### Phase A: Quick Wins (1-2 days, no architectural changes)
- Declare `model:` in all agent .md files (finding 2)
- Add Output Contract section to flux-drive agents (finding 6)
- Split using-clavain into catalog + reference (finding 7)
- Add `max_turns` to all Task dispatches in skills (finding 1)

### Phase B: Structured Handoffs (2-3 days)
- Verdict file schema and writer utility (finding 4)
- Sprint orchestrator reads verdicts, not raw output (finding 1 + 4)
- Agent contract validation logging (finding 6)

### Phase C: Smart Dispatch (3-5 days)
- Complexity classifier (finding 3)
- Sprint phase skipping based on complexity (finding 3)
- Tier-based cost tracking in dispatch logs (finding 2)

### Phase D: Session Resilience (2-3 days)
- Checkpoint schema and writer (finding 5)
- Sprint resume from checkpoint (finding 5)
- Agent verdict persistence across sessions (finding 4 + 5)

---

## Open Questions

1. **Should contracts be enforced or advisory?** Enforced = break on violation, advisory = log and continue. Recommendation: advisory initially, enforce after 2 weeks of data.
2. **Where do verdict files live?** `/tmp/` (ephemeral) vs `.clavain/verdicts/` (persistent). Recommendation: `.clavain/verdicts/` with git-ignore, cleaned at sprint start.
3. **How to handle model routing for third-party agents?** Flux-drive agents from interflux declare their own models. Should Clavain override? Recommendation: no — respect agent's declared tier.
4. **Complexity classifier: LLM or heuristic?** LLM adds tokens to classify. Recommendation: heuristic based on file count, change scope, and task type keywords. Save LLM for ambiguous cases.
