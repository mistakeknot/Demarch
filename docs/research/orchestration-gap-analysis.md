# Orchestration Gap Analysis: Interverse Multi-Agent Ecosystem

**Agent:** fd-plugin-orchestration
**Date:** 2026-02-15
**Scope:** New orchestration gaps not already tracked in existing brainstorms, PRDs, plans, or beads

**Already tracked (excluded from this analysis):**
- Event bus / event contracts (iv-z1a1)
- Reservation negotiation protocol (iv-2vup, PRD exists)
- Sprint resilience / auto-advance (iv-ty1f, PRD exists)
- Interspect self-improvement system (full roadmap exists)
- Merge agent / conflict resolution (Phase 4 brainstorm exists)
- Cross-plugin dependencies (iv-z1a0 program with 7 children)
- Interlens flux agents (brainstorm exists)

---

## Gap 1: Agent Crash Recovery Protocol

### Current State

When a Claude Code session crashes mid-edit (context exhaustion, network drop, OOM kill, user closes terminal), the cleanup path has significant holes:

1. **Interlock Stop hook never fires.** The `stop.sh` hook (at `/root/projects/Interverse/plugins/interlock/hooks/stop.sh`) releases all reservations and cleans up per-session git index files. But Claude Code's Stop hook only fires on graceful stops. A crash means:
   - File reservations persist until TTL expiry (15 minutes per `pre-edit.sh` auto-reserve)
   - The per-session `GIT_INDEX_FILE` (`.git/index-$SESSION_ID`) is orphaned on disk
   - The agent registration in intermute persists with a stale `last_seen` timestamp
   - Temp files (`/tmp/interlock-agent-*.json`, `/tmp/interlock-connected-*`) linger

2. **Clavain session-handoff never fires.** The `session-handoff.sh` hook (at `/root/projects/Interverse/hub/clavain/hooks/session-handoff.sh`) only runs on Stop events. A crash means no `HANDOFF.md` is written, no beads are updated, and no in-flight agent manifest is recorded.

3. **Intermute sweeper handles reservations but not agents.** The sweeper (at `/root/projects/Interverse/services/intermute/internal/storage/sqlite/sweeper.go`) cleans up expired reservations with a heartbeat grace period (5 minutes, per `core.SessionStaleThreshold`). But the agent registration itself is never cleaned up -- the agents table accumulates stale entries. The `SessionStaleThreshold` in `/root/projects/Interverse/services/intermute/internal/core/domain.go` allows session_id reuse after 5 minutes, which is a partial mitigation, but stale agents still appear in `sprint_check_coordination()` output.

4. **Orphaned git index files accumulate.** The cleanup in `interlock-cleanup.sh` only runs per-session. There is a `find /tmp ... -mmin +60 -delete` for temp files, but `.git/index-*` files are never cleaned up by any scheduled process. Over time, a project can accumulate dozens of orphaned index files.

### Concrete Failure Scenario

Agent A is editing `internal/http/router.go` in an intermute sprint. Context exhaustion hits mid-edit. Agent A's session dies. Agent B starts 2 minutes later, runs `sprint_check_coordination()`, and sees Agent A as "online" with a reservation on `router.go`. Agent B's pre-edit hook blocks the edit. Agent B must wait 13 more minutes for TTL expiry, or the human must manually intervene.

### Proposed Solution: Crash Recovery Sidecar

A lightweight recovery mechanism with three components:

**Component 1: Heartbeat-based agent reaper in intermute.** Extend the existing sweeper (currently reservation-only) to also mark agents as `status=offline` when `last_seen` exceeds `SessionStaleThreshold`. The `sprint_check_coordination()` function in `sprint-scan.sh` already queries `/api/agents?project=...` -- it should filter by status or staleness. Reservations held by offline agents should be immediately eligible for takeover.

**Component 2: Periodic git index cleanup.** Add a cron job or a check in interlock's `session-start.sh` that scans `.git/index-*` files, cross-references them against active agents in intermute, and removes orphaned ones. The interlock SessionStart hook already queries `/api/agents` to get agent count -- adding a stale index cleanup there is minimal additional work.

**Component 3: Session-start crash detection.** The Clavain `session-start.sh` hook already calls `sprint_check_coordination()`. Extend it to detect signs of a previous crash: (a) stale `.git/index-*` files with no matching active session, (b) in-progress beads with `last_updated` older than the session stale threshold, (c) orphaned temp files. When detected, inject an `additionalContext` warning: "Detected crash artifacts from a previous session. Cleaning up stale reservations and index files."

**Effort estimate:** ~2 days. Most logic already exists; it just needs to be wired into crash scenarios instead of only graceful shutdowns.

---

## Gap 2: Intermediate Result Sharing Between Agents

### Current State

Agents currently share results only through two mechanisms:

1. **File system.** Agent A writes a file (e.g., `docs/research/fd-architecture.md`), Agent B reads it later. This works for final outputs but not for intermediate findings.

2. **Intermute messages.** Agents can send messages via the intermute messaging API. However, there is no protocol for structured intermediate results. Messages are free-text with optional threading. The only structured message types are `commit:<hash>` (from postcommit hook) and `release-request` / `release_ack` / `release_defer` (from reservation negotiation).

### What's Missing

Consider the flux-drive review workflow: 7 review agents (fd-architecture, fd-safety, fd-correctness, fd-quality, fd-user-product, fd-performance, fd-game-design) analyze the same artifact in parallel. Each produces a standalone report. The synthesis phase combines them. But:

- **No cross-agent signaling during analysis.** If fd-safety discovers a critical vulnerability, fd-architecture could use that finding to evaluate whether the architecture even supports the required security boundary. Currently, each agent works in isolation and the synthesis phase catches contradictions after the fact.

- **No shared workspace for incremental findings.** The interject integration sweep brainstorm (at `/root/projects/Interverse/docs/brainstorms/2026-02-15-interject-integration-sweep-brainstorm.md`) mentions "two agents independently researching a topic" as a known waste signal. But there is no mechanism for agents to publish partial findings that other agents can query.

- **No structured finding format.** Agent outputs are unstructured markdown. The flux-drive spec defines a scoring protocol, but intermediate findings (before the full report) have no schema.

### Concrete Failure Scenario

During a flux-drive review of a new PRD, fd-correctness discovers that a proposed API endpoint already exists with incompatible semantics. fd-architecture, running in parallel, proposes an integration that depends on that endpoint. The synthesis phase flags the contradiction, but both agents already consumed their full token budget. If fd-correctness could have broadcast a "blocking finding" mid-analysis, fd-architecture would have adjusted its recommendation.

### Proposed Solution: Structured Finding Sideband via Intermute

**Protocol:** Define a new message type `finding:<severity>` with a structured JSON body:
```json
{
  "type": "finding",
  "severity": "blocking|important|informational",
  "agent": "fd-correctness",
  "category": "api-conflict",
  "summary": "POST /api/agents endpoint already exists with incompatible session_id semantics",
  "file_refs": ["internal/http/handlers_agents.go:34"],
  "thread_id": "<review-thread-id>"
}
```

**Consumption:** Agents that opt into the finding sideband would check for peer findings at defined checkpoints (e.g., before writing their final report). The flux-drive synthesis phase already reads all agent outputs -- it would additionally read the finding thread for early-termination decisions.

**Implementation path:** This builds on existing intermute threading. The finding message type is a convention (like `commit:<hash>`), not a new server feature. The main work is in the flux-drive skill (adding checkpoint logic to agents) and a `fetch_peer_findings` helper in the interflux MCP server.

**Effort estimate:** ~3 days. Mostly agent prompt changes and one new MCP tool.

---

## Gap 3: Pipeline Orchestration Across Plugins

### Current State

Clavain's 3-layer routing (Stage -> Domain -> Concern) maps user intent to individual skills, commands, and agents. But there is no mechanism for composing multi-step workflows that cross plugin boundaries as a single orchestrated pipeline.

Current cross-plugin workflows are implicit and procedural:
- `/sprint` manually calls brainstorm -> strategy -> plan -> execute -> review -> ship, each as a separate skill invocation
- `/flux-drive` dispatches agents in parallel, then synthesizes, but this is hardcoded in the skill prompt
- `/review` calls flux-drive, which calls individual agents -- each step is a prompt instruction, not a declared pipeline

### What's Missing

1. **No declarative pipeline definition.** If a user wants "brainstorm -> peer review -> plan -> execute with parallel lint+test -> ship", they must describe this procedurally. There is no way to define a reusable pipeline template.

2. **No pipeline state machine.** The sprint resilience PRD (iv-ty1f) addresses phase tracking for the sprint workflow specifically, but the solution is sprint-scoped. Other multi-step workflows (e.g., "research a topic, create a design doc, get review, file implementation beads") have no state tracking.

3. **No conditional routing.** The 3-layer routing table is static. There is no "if review score < 7, loop back to plan" logic except as prose instructions in skill prompts.

4. **No pipeline observability.** tool-time tracks tool usage at the individual tool level, and galiana tracks signal weights for auto-compound. But there is no way to answer "how long did step 3 of my 7-step workflow take?" or "which step typically fails?"

### Concrete Failure Scenario

A user runs `/sprint "add OAuth support"`. The brainstorm phase takes 4 minutes. Strategy creates 3 feature beads. Plan creates a detailed implementation plan. Execute starts... and context exhaustion hits. The next session resumes the sprint (sprint resilience fixes this), but it re-executes the plan phase because there's no checkpoint of "plan was complete, execute was at step 2 of 5." The user watches 3 minutes of redundant plan re-generation.

### Proposed Solution: Lightweight Pipeline Registry

Rather than a heavy workflow engine, extend the existing beads+phase infrastructure:

**Component 1: Pipeline templates in `.clavain/pipelines/`.** YAML files defining ordered steps with conditions:
```yaml
name: full-sprint
steps:
  - skill: brainstorming
    output: docs/brainstorms/{slug}-brainstorm.md
    checkpoint: brainstorm_complete
  - skill: writing-plans
    output: docs/plans/{slug}.md
    checkpoint: plan_complete
    retry_on: review_score < 7
  - skill: executing-plans
    checkpoint: execute_complete
    parallel_gates: [lint, test]
  - skill: flux-drive
    checkpoint: review_complete
```

**Component 2: Pipeline state on beads.** The sprint resilience PRD already proposes `bd set-state <sprint> phase=X`. Extend this to store checkpoint completion: `bd set-state <sprint> checkpoint=plan_complete`. Any session can resume from the last completed checkpoint.

**Component 3: Pipeline progress in interline.** The sprint resilience PRD already proposes `[sprint: <id> | <phase> -> <next>]` in the statusline. Pipeline templates would feed this automatically.

**Why this is different from sprint resilience:** Sprint resilience (iv-ty1f) solves the specific `/sprint` workflow with hardcoded phases. Pipeline orchestration generalizes this to any multi-step workflow. The sprint implementation could become the first pipeline template, validating the pattern.

**Effort estimate:** ~5 days for the template parser and bead integration. Sprint resilience (iv-ty1f) should ship first as the concrete implementation; pipeline generalization follows.

---

## Gap 4: Agent Capability Discovery

### Current State

Agent capabilities are statically declared in two places:
1. **Clavain routing table** (in `skills/using-clavain/SKILL.md`): A markdown table mapping Stage x Domain x Concern to skills, commands, and agents. Injected on every SessionStart.
2. **Intermute agent registration**: Agents register with a `capabilities[]` array (defined in `internal/core/models.go`). However, this field is populated with an empty array by `interlock-register.sh` -- no agent actually declares capabilities.

### What's Missing

1. **No runtime capability query.** When Clavain dispatches a task to an agent, it relies on the static routing table. If a new agent is added to a companion plugin, the routing table must be manually updated. There is no `GET /api/agents?capability=code-review&language=go` query.

2. **No capability negotiation.** The flux-drive triage phase selects agents based on content detection (language, framework, domain). But agent selection is hardcoded in the triage scoring algorithm. If a custom agent is installed (e.g., a domain-specific security reviewer), there is no mechanism for it to advertise "I can review Go code for SQL injection" and be discovered by flux-drive.

3. **No installed-plugin awareness.** Clavain's modpack system lists companion plugins, but there is no runtime query for "which companion plugins are actually installed and active?" The `_discover_*_plugin()` functions in `lib.sh` search the filesystem, but they are not exposed as a queryable registry.

4. **Intermute `capabilities` field is unused.** The agent registration (`interlock-register.sh`) sends `{id, name, project, session_id}` with no capabilities. The database schema supports it (`capabilities_json` column), but nothing populates or queries it.

### Concrete Failure Scenario

A user installs the `intercraft` companion plugin (which adds `agent-native-reviewer`). They run `/flux-drive` on a design document. The triage phase selects the standard 7 review agents but misses `agent-native-reviewer` because it is not in interflux's agent roster. The user must manually invoke `/intercraft:agent-native-review` separately. If `agent-native-reviewer` had registered its capability (`design-review`, `agent-architecture`), flux-drive's triage could have auto-included it.

### Proposed Solution: Capability Registry Protocol

**Step 1: Populate capabilities on registration.** Modify `interlock-register.sh` to read a `.claude-plugin/capabilities.json` file (or extract from `plugin.json` metadata) and include it in the agent registration payload. Intermute already stores this in `capabilities_json`.

**Step 2: Add capability query to intermute.** Extend `GET /api/agents` with `?capability=<tag>` filter. The storage layer already indexes by `capabilities_json`; add a WHERE clause.

**Step 3: Add discovery MCP tool to interlock.** A new `discover_agents` tool that queries intermute for agents with specific capabilities. This replaces hardcoded agent lists in flux-drive triage.

**Step 4: Capability advertisement in companion plugins.** Each companion plugin declares its agent capabilities in its plugin manifest. Clavain's SessionStart hook aggregates these into the routing context.

**Effort estimate:** ~3 days. The data model exists; the gap is purely in population and querying.

---

## Gap 5: Agent Error Aggregation and Surfacing

### Current State

Agent errors are currently surfaced through several disconnected channels:

1. **Hook stderr goes to Claude Code debug log.** All hook scripts use `set -euo pipefail` with `|| exit 0` guards (fail-open). Errors are silently swallowed. The interlock pre-edit hook emits a one-time `additionalContext` warning when intermute becomes unreachable, but other errors (jq parse failures, SQLite write errors, network timeouts) are invisible.

2. **Subagent errors are in JSONL files.** When a Task-dispatched agent fails, the error appears in the agent's `.jsonl` output file. The parent session sees the error in the Task tool response, but there is no aggregation across sessions or agents.

3. **Interspect evidence collection records dispatch events but not failures.** The `interspect-evidence.sh` hook (at `/root/projects/Interverse/hub/clavain/hooks/interspect-evidence.sh`) records `agent_dispatch` events but does not record agent failures or error patterns.

4. **tool-time tracks tool usage but not error rates.** The `summarize.py` script counts tool calls and edit-without-read violations, but does not track tool failure rates, timeout rates, or hook error rates.

### What's Missing

- **No "agent X has failed 3 times in the last hour" alert.** If fd-safety consistently times out on large files, the human never knows unless they check each review report manually.
- **No hook health dashboard.** If the interspect evidence hook starts failing due to a SQLite corruption, the failure is silent. Evidence simply stops being collected.
- **No error correlation.** If intermute goes down, multiple hooks fail simultaneously (interlock registration, sprint-scan coordination check, pre-edit reservation check). The human sees fragmented warnings from different hooks, not a unified "intermute is down, N hooks degraded."

### Concrete Failure Scenario

The intermute SQLite database hits disk full. The sweeper starts logging errors (`sweeper: disk I/O error`), but these go to intermute's stdout/stderr (systemd journal). Interlock hooks fail silently (curl timeouts, `|| exit 0`). Sprint-scan shows "No active coordination (Intermute offline or no agents)." The human sees the "no agents" message but doesn't realize it is caused by disk full -- it could also mean no other sessions are running. Meanwhile, file reservations are not being enforced, and two agents silently start editing the same file.

### Proposed Solution: Health Sideband with Escalation

**Component 1: Hook health counters.** Each hook script writes success/failure counters to a shared state file (e.g., `/tmp/clavain-hook-health-${SESSION_ID}.json`). Format:
```json
{
  "pre-edit": {"success": 47, "fail": 0, "last_fail": null},
  "sprint-scan": {"success": 12, "fail": 3, "last_fail": "2026-02-15T10:23:00Z", "last_error": "intermute unreachable"},
  "interspect-evidence": {"success": 8, "fail": 2, "last_fail": "2026-02-15T10:24:00Z", "last_error": "sqlite3: disk I/O error"}
}
```

**Component 2: Session-start health check.** The Clavain SessionStart hook reads the health file from the previous session (if available) and injects a summary: "Hook health: 2 hooks degraded (sprint-scan: intermute unreachable, interspect-evidence: sqlite error)."

**Component 3: Error correlation rules.** A small set of rules that detect correlated failures: "if sprint-scan AND pre-edit AND interlock-register all fail within 60 seconds, root cause is likely intermute down." This replaces 3 separate warnings with one actionable message.

**Component 4: Escalation to interline statusline.** When hook failure rate exceeds a threshold (e.g., >3 failures in 5 minutes), write a warning to the interline state file: `{"layer": "health", "status": "degraded", "detail": "intermute down"}`. This shows in the statusline as a persistent warning until the issue resolves.

**Effort estimate:** ~3 days. The health counters are trivial (append to JSON file). Correlation rules are a simple pattern match. Interline integration uses the existing state file protocol.

---

## Gap 6: Cost-Aware Scheduling

### Current State

There is no token budget tracking or cost-aware scheduling anywhere in the Interverse ecosystem:

1. **Galiana tracks signal weights** (in `lib-galiana.sh`) for deciding when to trigger auto-compound. These weights are heuristic (commit=1, debug-resolution=2) and unrelated to token cost.

2. **tool-time tracks tool usage counts** but not token consumption. The dashboard shows "Edit calls per session" but not "tokens consumed per session" or "tokens consumed per agent."

3. **Flux-drive dispatches all selected agents in parallel** with no budget awareness. A flux-drive review with 7 agents on a large codebase consumes 7x the tokens of a single agent. There is no mechanism to say "I have a 500K token budget for this review; skip the lowest-priority agents if we'd exceed it."

4. **The fd-token-economy review agent** (at `/root/projects/Interverse/.claude/agents/fd-token-economy.md`) reviews whether context costs are within budget, but it is a review agent that runs as part of flux-drive -- it adds to the cost rather than controlling it.

5. **Claude Code exposes cost information** in `~/.claude/projects/{cwd}/sessions/{session_id}/session.jsonl` (token counts per message). But no Interverse component reads this.

### What's Missing

- **No per-sprint token budget.** A `/sprint` invocation may consume anywhere from 50K to 2M tokens depending on complexity, number of review rounds, and agent dispatch. The user has no visibility into projected or actual cost until they check the Anthropic dashboard.
- **No agent prioritization by cost-effectiveness.** If fd-performance consistently produces low-value findings for a project (e.g., a CLI tool where performance doesn't matter), there is no signal to deprioritize it in future reviews.
- **No cost-benefit signal for interspect.** Interspect aims to learn from agent effectiveness, but "effectiveness" is currently measured only by override/correction rate. Adding "cost per useful finding" would dramatically improve agent selection.

### Concrete Failure Scenario

A user runs `/sprint "add pagination to API"` on a small feature. The sprint runs brainstorm (20K tokens), strategy (15K tokens), plan (25K tokens), and then launches flux-drive with 7 agents (7 x 80K = 560K tokens). Total: 620K tokens for a feature that could have been reviewed by 2-3 agents for 200K tokens. The user is surprised by the bill. If the sprint had a budget parameter (`/sprint --budget 200K "add pagination"`) that informed agent selection, the cost could be controlled.

### Proposed Solution: Token Ledger with Budget Gating

**Component 1: Session token counter.** A lightweight hook (PostToolUse) that reads the session JSONL's last entry for input/output token counts and maintains a running total in `/tmp/clavain-tokens-${SESSION_ID}.json`. This is read-only on the session file -- no modification.

**Component 2: Sprint budget parameter.** Extend the sprint bead state to include `token_budget` and `tokens_spent`. The auto-advance engine (from sprint resilience PRD) checks `tokens_spent < token_budget` before each phase transition. If the budget is exhausted, pause and ask the user whether to continue.

**Component 3: Flux-drive cost-aware triage.** The triage scoring algorithm already ranks agents. Add a "budget remaining" input: if only 100K tokens remain, dispatch only the top-3 agents instead of all 7. This is a soft cap -- the user can override.

**Component 4: Cost-effectiveness signal to interspect.** After each review, compute `useful_findings / tokens_consumed` for each agent. Feed this into the interspect evidence store. Over time, interspect can learn "fd-performance produces 0.1 useful findings per 10K tokens in this project" and suggest deprioritization.

**Effort estimate:** ~5 days. The token counter is straightforward. Sprint budget integration depends on sprint resilience (iv-ty1f) shipping first. Flux-drive triage modification is ~1 day.

---

## Gap 7: Agent Trust and Reputation

### Current State

Agent quality is tracked in two nascent systems:

1. **Interspect evidence store** records agent dispatch events and correction signals. The counting-rule confidence gate (Phase 2) computes thresholds for pattern detection. But this is about detecting failure patterns, not building a positive trust score.

2. **Galiana experiment framework** evaluates agent configurations against golden test cases. But this is offline evaluation (batch mode), not runtime trust tracking.

3. **Flux-drive scoring** assigns numerical scores to review findings (1-10 severity, 1-3 confidence). But these scores are per-finding, not per-agent. There is no "fd-safety has a 0.85 precision on this project" metric.

### What's Missing

- **No agent precision/recall tracking.** When a human overrides an agent's finding (dismisses it as false positive), this is recorded by interspect. But there is no aggregation into "fd-quality has a 30% false positive rate on Python projects."
- **No agent reliability score for dispatch decisions.** When flux-drive selects agents for a review, it uses static triage scoring (language detection, domain detection). It does not factor in "this agent performed poorly on the last 5 reviews in this project."
- **No reputation decay.** An agent that was accurate 6 months ago but has drifted (due to prompt changes, model updates, or project evolution) still has the same implicit trust level.
- **No cross-project reputation.** If fd-correctness is consistently excellent across 10 projects, that signal does not propagate. Each project's interspect data is isolated.

### Concrete Failure Scenario

fd-game-design was originally created for a game project. It is included in the default flux-drive agent roster. When reviewing a CLI tool's PRD, it consistently produces irrelevant findings about "player experience" and "engagement loops." The human dismisses these findings every time. After 20 reviews, the human is frustrated but fd-game-design is still dispatched on every review because there is no mechanism to reduce its priority for non-game projects.

### Proposed Solution: Lightweight Trust Scores via Interspect

This is best implemented as an extension to the interspect roadmap (Phase 3: Autonomy), not a standalone feature:

**Extension 1: Finding-level feedback.** When the synthesis phase of flux-drive processes agent outputs, track which findings are included in the final synthesis (accepted) vs. discarded. Write `finding_accepted` / `finding_discarded` events to interspect evidence.

**Extension 2: Agent precision metric.** Compute `accepted_findings / total_findings` per agent per project. Store as a running average in the interspect canary table (which already has per-agent metrics).

**Extension 3: Trust-weighted triage.** Feed the precision metric into flux-drive triage scoring. An agent with 0.3 precision on this project gets its triage score multiplied by 0.5, making it less likely to be dispatched. An agent with 0.9 precision gets a 1.2 multiplier.

**Extension 4: Cross-project aggregation.** Add a global interspect summary that aggregates metrics across projects: `SELECT agent, AVG(precision) FROM canary GROUP BY agent`. This provides a baseline trust score for new projects where the agent has no local track record.

**Effort estimate:** ~4 days, but dependent on interspect Phase 2 (overlay system) shipping first. The finding-level feedback requires flux-drive synthesis changes. The trust-weighted triage is a simple multiplier in the existing scoring algorithm.

---

## Priority Ranking

| Gap | Impact | Effort | Dependencies | Priority |
|-----|--------|--------|--------------|----------|
| **1. Crash Recovery** | High -- directly causes agent downtime and human intervention | 2 days | None | **P1** |
| **5. Error Aggregation** | High -- silent failures erode trust in the entire system | 3 days | None | **P1** |
| **4. Capability Discovery** | Medium -- blocks dynamic agent ecosystem growth | 3 days | None | **P2** |
| **2. Intermediate Results** | Medium -- reduces review quality and wastes tokens | 3 days | None | **P2** |
| **6. Cost-Aware Scheduling** | Medium -- no cost control on expensive operations | 5 days | Sprint resilience (iv-ty1f) | **P2** |
| **3. Pipeline Orchestration** | Medium -- enables reusable workflows but sprint resilience covers the main case | 5 days | Sprint resilience (iv-ty1f) | **P3** |
| **7. Agent Trust** | Low priority now -- interspect Phase 2 must ship first | 4 days | Interspect Phase 2 (iv-vrc4+) | **P3** |

### Recommended sequencing

1. **Crash Recovery + Error Aggregation** (P1, parallel, ~3 days total) -- these are reliability gaps that affect daily operations
2. **Capability Discovery** (P2, ~3 days) -- unblocks dynamic plugin ecosystem
3. **Intermediate Results** (P2, ~3 days) -- improves flux-drive review quality
4. **Cost-Aware Scheduling** (P2, after sprint resilience ships)
5. **Pipeline Orchestration** (P3, after sprint resilience ships)
6. **Agent Trust** (P3, after interspect Phase 2 ships)

---

## Key Files Referenced

| File | Role |
|------|------|
| `/root/projects/Interverse/plugins/interlock/hooks/stop.sh` | Graceful reservation release (never fires on crash) |
| `/root/projects/Interverse/plugins/interlock/hooks/session-start.sh` | Agent registration + git index isolation |
| `/root/projects/Interverse/plugins/interlock/hooks/pre-edit.sh` | Reservation check + auto-reserve + inbox polling |
| `/root/projects/Interverse/plugins/interlock/scripts/interlock-cleanup.sh` | Reservation release + temp file cleanup |
| `/root/projects/Interverse/plugins/interlock/scripts/interlock-register.sh` | Agent registration (capabilities field unused) |
| `/root/projects/Interverse/plugins/interlock/hooks/lib.sh` | Intermute curl wrappers, path helpers |
| `/root/projects/Interverse/hub/clavain/hooks/session-handoff.sh` | Crash-affected: handoff file generation |
| `/root/projects/Interverse/hub/clavain/hooks/sprint-scan.sh` | Coordination check (shows stale agents as online) |
| `/root/projects/Interverse/hub/clavain/hooks/auto-compound.sh` | Signal-based knowledge compounding |
| `/root/projects/Interverse/hub/clavain/hooks/lib.sh` | Plugin discovery, in-flight agent detection |
| `/root/projects/Interverse/hub/clavain/hooks/interspect-evidence.sh` | Agent dispatch tracking (no failure tracking) |
| `/root/projects/Interverse/hub/clavain/hooks/hooks.json` | Hook registration manifest |
| `/root/projects/Interverse/services/intermute/internal/storage/sqlite/sweeper.go` | Reservation sweeper (no agent reaping) |
| `/root/projects/Interverse/services/intermute/internal/core/domain.go` | SessionStaleThreshold (5 minutes) |
| `/root/projects/Interverse/services/intermute/internal/core/models.go` | Agent model with unused capabilities field |
| `/root/projects/Interverse/plugins/interflux/CLAUDE.md` | Flux-drive agent roster (static, not discoverable) |
| `/root/projects/Interverse/plugins/tool-time/CLAUDE.md` | Usage analytics (no cost tracking) |
| `/root/projects/Interverse/hub/clavain/galiana/lib-galiana.sh` | Signal weight tracking for auto-compound |
| `/root/projects/Interverse/docs/product/interspect-roadmap.md` | Interspect phases (trust metrics not yet planned) |
