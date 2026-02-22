# Research: Current Model Routing in Clavain Hub

**Date:** 2026-02-20  
**Focus:** Comprehensive inventory of current model routing implementation, configuration, and skill infrastructure

---

## Executive Summary

Clavain's model routing has **three independent systems**:
1. **Dispatch tier system** (dispatch.sh + config/dispatch/tiers.yaml) — for Codex CLI agents
2. **Subagent model frontmatter** (agents/*.md `model:` YAML field) — for Claude subagents
3. **Interspect routing overrides** (.claude/routing-overrides.json) — for agent exclusions based on evidence

The first two are **production-ready** but **static** (no complexity-aware or outcome-driven selection). The third is **evidence-collection** only — no routing changes applied yet. Track B in the roadmap covers evolution from static → complexity-aware → adaptive routing.

---

## 1. Dispatch Tier System (Codex CLI Agents)

### Location
- **Config:** `/root/projects/Interverse/os/clavain/config/dispatch/tiers.yaml`
- **Implementation:** `/root/projects/Interverse/os/clavain/scripts/dispatch.sh` (lines 161-259)
- **Skill:** `skills/interserve/SKILL.md`

### Current Tiers
```yaml
tiers:
  fast:
    model: gpt-5.3-codex-spark
    description: Scoped read-only tasks, exploration, verification, quick reviews
  
  fast-clavain:
    model: gpt-5.3-codex-spark-xhigh
    description: Clavain interserve-mode default for read-only/administrative tasks
  
  deep:
    model: gpt-5.3-codex
    description: Generative tasks, implementation, complex reasoning, debates
  
  deep-clavain:
    model: gpt-5.3-codex-xhigh
    description: Clavain interserve-mode high-complexity/research/flux-drive dispatch

fallback:
  fast: deep        # fast falls back to deep tier's model
  fast-clavain: deep-clavain
  deep-clavain: deep
```

### Resolution Logic (dispatch.sh)
- **Flag:** `--tier fast|deep` or `--tier fast-clavain|deep-clavain`
- **Priority:** Interserve mode remaps `fast` → `fast-clavain` and `deep` → `deep-clavain` if `.claude/clodex-toggle.flag` file exists
- **YAML parsing:** Hand-rolled line-by-line parser (lines 207-247 of dispatch.sh) — finds tier block under `tiers:`, reads `model:` value
- **Fallback:** If requested tier not found, falls back to `fallback` mapping (e.g., `fast` → `deep` if Spark unavailable)
- **Override:** `-m/--model` flag bypasses tier system entirely (mutually exclusive with `--tier`)

### Environment Variables
- `CLAVAIN_INTERSERVE_MODE` — Set to `true` if `.claude/clodex-toggle.flag` exists (controls tier remapping)
- `CLAVAIN_DISPATCH_PROFILE` — Can be `interserve|clavain|xhigh|codex` to trigger x-high tier remapping
- `CLAVAIN_SOURCE_DIR` / `CLAVAIN_DIR` — Optional overrides for locating tiers.yaml

### Invocation Pattern (Skill: interserve)
```bash
# Resolve tier from config, then dispatch
CLAVAIN_DISPATCH_PROFILE=interserve bash "$DISPATCH" \
  --prompt-file "$TASK_FILE" \
  -C "$PROJECT_DIR" \
  -o "/tmp/codex-result-{name}.md" \
  -s workspace-write \
  --tier deep
```

### Interserve Mode Toggle
- **File:** `/root/projects/Interverse/os/clavain/scripts/clodex-toggle.sh`
- **Flag file:** `.claude/clodex-toggle.flag` in project root
- **Effect:** When present, dispatch remaps models:
  - `fast` → `gpt-5.3-codex-spark-xhigh`
  - `deep` → `gpt-5.3-codex-xhigh`
  - Routes source code changes through Codex to preserve Claude token budget

---

## 2. Subagent Model Frontmatter

### Location
- **Research agents:** `agents/research/*.md` (in interflux companion: 5 agents)
- **Review agents (Clavain):** `agents/review/*.md` (2 agents: plan-reviewer, data-migration-expert)
- **Review agents (interflux):** 7 fd-* agents in `plugins/interflux/agents/`
- **Workflow agents:** `agents/workflow/*.md` (2 agents: pr-comment-resolver, bug-reproduction-validator)

### YAML Frontmatter Format
```yaml
---
name: some-agent
description: What this agent does
model: inherit|haiku|sonnet|opus
---
```

### Current Model Configuration (from `/clavain:model-routing` command)
**Economy mode** (default, optimized for cost):
- Research (5): `haiku` — Grep, read, summarize
- Review (9): `sonnet` — Structured analysis with good judgment
- Workflow (2): `sonnet` — Code changes need reliable execution

**Quality mode** (maximum reasoning):
- All agents: `model: inherit` (uses parent session's model, typically Opus)

### Toggle Command
```
/clavain:model-routing [economy|quality|status]
```
- `economy` — Sets research→haiku, review→sonnet, workflow→sonnet (saves ~5x on research, ~3x on review)
- `quality` — Sets all to `inherit` (maximum reasoning)
- `status` — Reports current model for all agents

### Cost Rationale
- **Haiku:** Fast, cheap, good for read-only exploration
- **Sonnet:** Balanced cost/quality for analysis and code execution
- **Opus:** High reasoning for critical reviews and complex architectural decisions
- **Economy savings:** ~5x on research, ~3x on review vs. quality mode

---

## 3. Interspect Routing Overrides (Evidence-Driven)

### Location
- **Library:** `hooks/lib-interspect.sh` (lines 418-809)
- **Evidence hooks:** `hooks/interspect-evidence.sh` (records agent dispatch outcomes)
- **Overrides file:** `.claude/routing-overrides.json`

### Purpose
Learn which agents are consistently irrelevant for a project by monitoring user corrections, then propose permanent routing overrides when evidence reaches threshold (≥80% "agent_wrong" corrections).

### Data Structure
```json
{
  "version": 1,
  "overrides": [
    {
      "agent": "fd-game-design",
      "action": "exclude",
      "reason": "Go backend project, no game simulation",
      "evidence_ids": [],
      "created": "2026-02-15T00:00:00Z",
      "created_by": "human",
      "canary_enabled": true,
      "canary_started": "2026-02-15T00:00:00Z"
    }
  ]
}
```

### Commands (in AGENTS.md)
- `/interspect:propose` — Batch proposals for routing-eligible patterns
- `/interspect:revert <agent>` — Remove an override
- `/interspect:unblock <agent>` — Remove from blacklist, allow re-proposal
- `/interspect:status` — Show overrides, canaries, and modifications

### Evidence Collection Flow
1. `interspect-evidence.sh` (PostToolUse hook) records agent dispatch outcomes
2. `interspect-session.sh` (SessionStart hook) initializes session tracking
3. User submits correction via `/interspect:correction <agent> <description>` when agent produces irrelevant findings
4. SQLite evidence store accumulates corrections (evidence_ids, agent, project, correction_type, timestamp)
5. Threshold met (≥80% "agent_wrong" corrections) → eligible for override proposal

### Canary Monitoring
After applying an override, Interspect monitors for 14 days or 20 uses. If the override causes problems, run `/interspect:revert` to undo.

### SQL Helpers (lib-interspect.sh)
- `_interspect_sql_escape()` — Safe SQL string escaping
- `_interspect_is_routing_eligible()` — Threshold + blacklist check
- `_interspect_read_routing_overrides()` — Read overrides file
- `_interspect_apply_routing_override()` — Full apply+commit+canary flow
- `_interspect_validate_overrides_path()` — Path traversal protection

### Current Status
- **Evidence collection:** Active (hooks wired)
- **Override proposals:** No proposals applied yet (threshold not reached for any agent on any project)
- **Cross-cutting agents:** fd-architecture, fd-quality, fd-safety, fd-correctness show warnings when excluded (provide structural/security coverage)

---

## 4. Model Selection for Different Phases/Agents

### Phase → Model Mapping (from routing-tables.md)

| Phase | Primary Skills | Key Agents | Typical Model |
|-------|----------------|-----------|---------------|
| **Explore** | brainstorming | repo-research-analyst, best-practices-researcher | Haiku (research) |
| **Plan** | writing-plans | plan-reviewer, fd-architecture | Sonnet (review) |
| **Review (docs)** | flux-drive | fd-architecture/safety/correctness/quality/performance/user-product (triage varies) | Sonnet→Opus (adaptive triage) |
| **Execute** | executing-plans, interserve | (no fixed agents; dispatch via `/interserve`) | Deep tier (gpt-5.3-codex) |
| **Debug** | systematic-debugging | bug-reproduction-validator, git-history-analyzer | Sonnet (analysis) |
| **Review (code)** | code-review-discipline | (fd-* agents, adaptive triage) | Sonnet→Opus |
| **Ship** | landing-a-change | fd-safety | Opus (critical) |

### Explicit Model Overrides
Individual agents can be overridden via Task tool:
```
Task(fd-architecture, model="opus"): "Review this architecture..."
```

---

## 5. Roadmap: Track B (Model Routing Evolution)

### Current Status (as of roadmap.md, 2026-02-20)

**Track B: Model Routing** — Build multi-model routing from static → adaptive

| Step | What | Bead | Status | Depends On |
|------|------|------|--------|------------|
| **B1** | **Static routing table** — phase→model mapping declared in config, applied at dispatch | `iv-dd9q` | Open (P2) | — |
| **B2** | **Complexity-aware routing** — task complexity drives model selection within phases. Design with zero-cost abstraction (disabled = static path). See pi_agent_rust lessons §3. | `iv-k8xn` | Open (P2) | B1 |
| **B3** | **Adaptive routing** — Interspect outcome data drives model/agent selection | `iv-i198` | Open (P3) | B2, Interspect (iv-thp7) |

### B2 Design Notes (from brainstorms/2026-02-19-pi-agent-rust-lessons-brainstorm.md §3)
- **Zero-cost abstraction:** When disabled, no overhead vs. static path
- **Shadow mode:** Safe rollout — observe complexity-aware decisions without acting on them
- **Complexity inputs:** Token count, reasoning requirements, cross-file scope, user intent clarity

### Related Beads
- `iv-pbmc` — Cost-aware agent scheduling with token budgets (P1, **done**)
- `iv-thp7` — Level 3 Adapt — Interspect kernel event integration (P2, open)

---

## 6. Configuration Files

### tiers.yaml Structure
- **Top-level section:** `tiers:`
- **Tier blocks:** `fast:`, `fast-clavain:`, `deep:`, `deep-clavain:`
- **Fields per tier:** `model:` (required), `description:` (optional)
- **Fallback section:** `fallback:` — tier→tier mappings for graceful degradation
- **Parser:** Line-by-line regex (not YAML library) — robust but requires exact indent

### agent-rig.json (example agent configuration)
- Agents specify `model:` in frontmatter
- Default: `inherit` (use parent session model) or explicit: `haiku`, `sonnet`, `opus`
- Overridden at dispatch time via Task tool or model-routing command

---

## 7. Existing `/clavain:model-routing` Skill

### Location
`/root/projects/Interverse/os/clavain/commands/model-routing.md`

### Capabilities
1. **Status report** — Lists all agents with current model tier
2. **Economy mode** — Sets smart defaults (haiku/sonnet mix)
3. **Quality mode** — Sets all to `inherit` (Opus)

### Implementation
Uses `sed -i` to edit frontmatter `model:` lines in `agents/*/md` files.

### Gap
No integration with:
- Token budget tracking (exists in lib-sprint.sh but not consulted by model-routing command)
- Complexity-aware model selection (B2 feature, not yet implemented)
- Dispatch tier system (works on agent frontmatter, not dispatch config/tiers.yaml)

---

## 8. Token Budget Tracking (lib-sprint.sh)

### Location
`/root/projects/Interverse/os/clavain/hooks/lib-sprint.sh`, lines 86-97

### Default Budgets by Complexity Tier
```bash
_sprint_default_budget() {
    local complexity="${1:-3}"
    case "$complexity" in
        1) echo "50000" ;;      # Trivial task
        2) echo "100000" ;;     # Simple task
        3) echo "250000" ;;     # Medium task (default)
        4) echo "500000" ;;     # Complex task
        5|*) echo "1000000" ;;  # Very complex task
    esac
}
```

### Relationship to Model Routing
- Sprint complexity tier is set during `/sprint create` or determined by word-count heuristic
- Budget is used to track token spend, NOT to drive model selection (that's B2 feature)
- Current system: Budget is advisory (tracked, monitored), not binding

### Complexity Classification (lib-sprint.sh, lines 719+)
- Word-count tier is starting point
- Adjusted by signals (TODO: unclear what signals currently apply)

---

## 9. Implementation Gaps (Track B)

### B1: Static Routing Table
- **Status:** Partial (dispatch tiers exist, but not formally documented as "static routing table")
- **Missing:** Declarative per-phase model assignment, applied uniformly across dispatch and subagent invocation

### B2: Complexity-Aware Routing
- **Status:** Not started (bead `iv-k8xn` open)
- **Design needed:**
  - Complexity detection (input: task description, file list, test suite)
  - Model selection logic (complexity → tier mapping)
  - Zero-cost abstraction for safe rollout
  - Shadow mode for observation before action

### B3: Adaptive Routing
- **Status:** Not started (bead `iv-i198` open)
- **Depends on:** B2 (complexity-aware), Interspect (iv-thp7)
- **Concept:** Outcome data (corrections, quality signals, token spend) drives model selection over time

---

## 10. Multi-Agent Review Routing (flux-drive)

### Location
`/plugins/interflux/` (companion plugin)

### Agents
7 core review agents (fd-*):
- `fd-architecture` — Boundaries, coupling, module design
- `fd-safety` — Security, credentials, trust boundaries
- `fd-correctness` — Data integrity, concurrency, async
- `fd-quality` — Naming, conventions, language idioms
- `fd-user-product` — User flows, UX, product reasoning
- `fd-performance` — Performance, bottlenecks, scaling
- `fd-game-design` — Game balance, pacing, emergent behavior

5 research agents:
- `best-practices-researcher`
- `framework-docs-researcher`
- `git-history-analyzer`
- `learnings-researcher`
- `repo-research-analyst`

### Triage Logic
- Auto-detects project docs (CLAUDE.md/AGENTS.md) for codebase context
- Scores each agent for relevance
- Dynamically selects 4-12 agents per task (adaptive count)
- Applied via `/interflux:flux-drive` command

### Model Selection
- Each agent specifies `model:` in frontmatter
- All currently use `inherit` (parent session model) or explicit tier
- No complexity-aware selection within flux-drive (candidate for B2 feature)

---

## 11. Key Files Summary

| File | Purpose | Current Status |
|------|---------|-----------------|
| `config/dispatch/tiers.yaml` | Tier→model mapping for Codex dispatch | Active, used by dispatch.sh |
| `scripts/dispatch.sh` | Codex CLI wrapper with tier resolution | Active, production |
| `skills/interserve/SKILL.md` | Skill doc for dispatch usage | Active |
| `commands/model-routing.md` | Toggle economy/quality modes for subagents | Active |
| `agents/*/md` | Subagent model frontmatter | Static, no dynamic routing |
| `hooks/lib-interspect.sh` | Evidence-driven routing override logic | Active (evidence only, no overrides applied) |
| `hooks/lib-sprint.sh` | Token budget tracking by complexity tier | Active (advisory only) |
| `.claude/routing-overrides.json` | Persistent routing exclusions | Exists, no entries yet |
| `docs/roadmap.md` | Track A/B/C convergence plan | Track B open (P2) |

---

## 12. Relevant Brainstorms and Research

### pi_agent_rust Lessons (brainstorms/2026-02-19-pi-agent-rust-lessons-brainstorm.md)
- **§2: Agency specs** — Declarative per-stage config (Track C1 related)
- **§3: Complexity-aware routing** — Zero-cost abstraction design (Track B2 reference)

### Vision and Design Decisions (docs/clavain-vision.md)
- Three-layer architecture: Kernel (Intercore) → OS (Clavain) → Drivers (companion plugins)
- Model routing is an OS concern (not kernel primitive, not driver decision)

---

## 13. Limitations and Open Questions

### Current System Limitations
1. **No complexity awareness** — All tasks in a phase use same model tier (B2 required to fix)
2. **Manual mode toggle** — Economy/quality is all-or-nothing per session (B2/B3 required for per-task selection)
3. **No outcome feedback** — Token budgets tracked but not used to select models (B3 required)
4. **Dispatch ≠ Subagent routing** — Two separate systems (dispatch tiers vs. agent frontmatter); no unified configuration
5. **Interspect data not acted on** — Evidence collected but no routing changes applied (awaiting threshold or manual review)

### Research Questions (from roadmap.md Research Agenda)
- **Multi-model composition theory** — Principled framework for which model to use when
- **Agent measurement & analytics** — What metrics predict human override? Token waste signals?
- **Multi-agent failure taxonomy** — How do hallucination cascades and model mismatch propagate?
- **Fleet topology optimization** — How many agents per phase? Which combinations produce best outcomes?

---

## Conclusion

Clavain has **three functional but static routing systems**:
1. **Dispatch tiers** (Codex CLI) — Config-driven, well-tested, no complexity awareness
2. **Agent frontmatter** (Claude subagents) — Manual toggle only (economy/quality)
3. **Interspect overrides** (agent exclusions) — Evidence collection active, no reversals applied yet

All three are designed for **static or manual** operation. Track B in the roadmap (bead `iv-k8xn`, P2) covers evolution to **complexity-aware** routing, and Track B3 (bead `iv-i198`, P3) covers **adaptive** routing driven by Interspect outcome data.

The infrastructure is ready for B2 implementation — token budgets exist, complexity classification exists (heuristic only), and the dispatch system can be extended to consult complexity before selecting a tier.
