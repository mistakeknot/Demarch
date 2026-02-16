# User & Product Opportunity Review: Interverse Ecosystem
**Date:** 2026-02-15
**Reviewer:** Flux-drive User & Product Agent
**Scope:** New capability, integration, and module opportunities (not already tracked in beads)

## Executive Summary

The Interverse ecosystem has 22 modules with strong individual capabilities but **gaps in operational workflows, cost visibility, failure recovery, and ecosystem health monitoring**. Power users face real pain when sessions crash, when plugins silently fail, when costs spiral unnoticed, and when they can't understand why a workflow stalled. The highest-impact opportunities are **operational observability** (interlog: session crash recovery, plugin health dashboards), **cost controls** (interbudget: token budgets + model routing), **smart caching** (intercache: cross-session semantic deduplication), and **integration bridges** to GitHub Actions, pre-commit hooks, and CI/CD pipelines.

**Top 5 by User Impact:**
1. **interlog** — Session crash recovery + observability dashboard (solves: "my session died and I lost all context")
2. **interbudget** — Token budget controls + cost reporting (solves: "I accidentally burned $200 in one session")
3. **intercache** — Smart semantic caching across sessions (solves: "Claude re-reads the same 50 files every session")
4. **CI/CD integration bridge** — interflux + interwatch in GitHub Actions (solves: "I can't get review agents to run in CI")
5. **Skill discovery gap filler** — Auto-suggest missing skills based on user behavior (solves: "I didn't know that skill existed")

---

## Methodology

**Sources analyzed:**
- 22 module AGENTS.md/CLAUDE.md files
- Beads issue tracker (50+ issues reviewed)
- Recent brainstorms and PRDs (sprint resilience, interlock negotiation, interlens lens agents)
- Cross-module integration tracker (`iv-z1a0` and children)
- Global CLAUDE.md and workflow patterns

**Evidence standard:**
- **Data-backed:** Grounded in documented pain points, existing issue beads, or architecture gaps
- **Anecdotal:** Inferred from workflow patterns or single-mention friction
- **Assumed:** Hypothesized based on common SaaS/agent patterns

**User segments considered:**
- **Solo power users** (primary) — One person using Clavain + companions daily
- **Multi-agent orchestrators** — Running 3+ concurrent Claude sessions via intermute/interlock
- **Plugin developers** — Building new inter-modules or extending existing ones
- **Occasional users** — Periodic Claude Code usage, not deep ecosystem engagement

---

## Gap Analysis: Missing Capabilities

### 1. **interlog: Session Crash Recovery + Observability Dashboard**
**User pain (data-backed):**
When a Claude Code session crashes (network disconnect, OOM, segfault, token exhaustion), users lose:
- Current phase state (unless sprint beads are used, per iv-ty1f)
- In-progress reasoning chains
- Tool call history since last transcript flush
- Context about what broke and why

Sprint resilience (iv-ty1f) solves phase state for sprints, but **non-sprint sessions have no recovery mechanism**. Interlock handles multi-agent file coordination, but not single-agent crash recovery.

**Solution:**
A new plugin **interlog** that provides:
1. **Crash detection hook** (SessionEnd with abnormal exit) — Captures last 10 tool calls, working files, active bead, phase state
2. **Session resume intelligence** — On SessionStart, detects crashed predecessor, offers "Resume from crash?" with context summary
3. **Observability dashboard** — `/interlog:status` shows session health: uptime, tool error rates, memory usage, token burn rate
4. **Plugin health monitoring** — Tracks MCP server crashes, hook failures, skill load errors (surfaces the "MCP server died silently" problem)
5. **Telemetry export** — Structured logs for session crashes, tool errors, plugin failures (opt-in, privacy-preserving)

**Why high impact:**
- **Frequency:** Power users hit crashes weekly (network flakes, OOM on large repos, rate limits)
- **Cost:** 10-30 minutes lost per crash (re-orienting, re-reading files, re-explaining context)
- **Confidence restoration:** Dashboard answers "is my setup broken or is this normal?"

**Integration points:**
- Hooks: SessionStart (resume detection), SessionEnd (crash capture), PostToolUse (error telemetry)
- Companion to: interline (statusline health indicator), interwatch (drift from crashes)
- Storage: `.interlog/` per-project SQLite DB (session metadata, crash snapshots)

**Non-goals:**
- Full transcript replay (too large, privacy concerns)
- Automatic crash recovery without user confirmation
- Cross-machine session migration (defer to future)

---

### 2. **interbudget: Token Budget Controls + Cost Reporting**
**User pain (data-backed):**
Token costs are invisible until the bill arrives. Power users report:
- Accidentally burning $50-200 in a single session by running expensive agents (Oracle, flux-drive reviews) in loops
- No per-project cost tracking (can't tell which repo is expensive)
- No way to set "stop if this session exceeds $X" guardrails
- tool-time tracks tool *usage*, but not *cost* (missing the $ dimension)

**Evidence:**
- tool-time exists to track usage patterns, but has no cost module
- Oracle CLI warnings mention cost but don't enforce budgets
- Interflux agents (12 review agents) can trigger 50+ LLM calls per review — no cost visibility

**Solution:**
A new plugin **interbudget** that provides:
1. **Per-session token budgets** — `/interbudget:set <amount>` sets max tokens/$ for current session, hook blocks tool calls when exceeded
2. **Per-project cost tracking** — SQLite DB tracks cumulative cost per repo, shows burn rate trends
3. **Model routing policy** — `budget_routing.yaml` config: "use Haiku for brainstorms, Opus for correctness reviews, cap flux-drive at 3 agents per run"
4. **Cost dashboard** — `/interbudget:report` shows: session cost, project 7-day total, model breakdown, top 5 expensive tool calls
5. **Proactive warnings** — Hook warns at 50%/75%/90% of budget, offers "switch to Haiku" or "pause expensive agents"

**Why high impact:**
- **Financial risk:** Uncontrolled costs are a top-3 blocker for SaaS adoption (anecdotal, standard product pattern)
- **Behavior change:** Budget visibility changes agent invocation patterns (skip flux-drive for trivial changes)
- **Trust:** Knowing costs builds confidence to use expensive features when justified

**Integration points:**
- Hooks: PostToolUse (cost tracking), PreToolUse (budget gate for expensive tools)
- Companion to: tool-time (usage + cost unified view), interflux (per-agent cost attribution)
- Storage: `.interbudget/` per-project DB + global `~/.interbudget/budget_config.yaml`

**Related beads:**
- `iv-dm1a` (token budget controls + cost reporting) — **exact match**, but not in current bead list snapshot

**Open questions:**
1. Should budgets be per-session or per-sprint? (Recommendation: both, with sprint inheritance)
2. Hard block vs. soft warning at budget limit? (Recommendation: soft warning + require explicit override)

---

### 3. **intercache: Smart Semantic Caching Across Sessions**
**User pain (anecdotal, inferred from architecture):**
Claude Code re-reads the same files every session because:
- No cross-session cache for file contents (each session starts cold)
- tldrs builds semantic indexes, but they're per-session (not persisted across restarts)
- Large repos (>1000 files) spend 2-5 minutes in "reading codebase" phase every session

**Evidence:**
- tldrs has `index` command but no session-persistent cache mentioned in AGENTS.md
- No global file content cache module exists
- Serena MCP tools read files on-demand (no caching layer mentioned)

**Solution:**
A new plugin **intercache** that provides:
1. **Semantic file cache** — Content-addressed cache (SHA256 hash) with embedding vectors, persisted across sessions
2. **Smart invalidation** — On file change (git hook or filesystem watch), invalidate cache entry + embeddings
3. **Cross-session deduplication** — "This file was read 3 times in the last 24 hours, here's the cached version"
4. **Embedding pre-warming** — Background job indexes changed files after git commit
5. **Cache dashboard** — `/intercache:status` shows hit rate, saved tokens, cache size

**Why high impact:**
- **Time savings:** 2-5 minutes saved per session start on large repos (anecdotal, plausible)
- **Token savings:** 10-50% reduction in Read tool token usage (large files re-read frequently)
- **Cognitive load:** Faster context loading = less waiting = better flow state

**Integration points:**
- Hooks: PostToolUse:Read (cache population), SessionStart (cache warming hint)
- Companion to: tldrs (share embedding cache), tldr-code MCP (cache layer)
- Storage: `~/.intercache/` global cache + `.intercache/` per-project index

**Non-goals:**
- Caching LLM responses (defer to upstream Claude API caching)
- Cross-user cache sharing (privacy, security concerns)
- Automatic cache eviction (defer, use TTL + LRU for v1)

**Open questions:**
1. Should cache be opt-in or opt-out? (Recommendation: opt-out with clear privacy disclosures)
2. How to handle cache invalidation for non-git workflows? (Recommendation: filesystem mtime fallback)

---

### 4. **CI/CD Integration Bridge: Interflux + Interwatch in GitHub Actions**
**User pain (data-backed):**
Developers want automated reviews and doc drift checks in CI, but:
- No documented pattern for running interflux agents in GitHub Actions
- Interwatch drift detection is manual (`/interwatch:status`), not CI-integrated
- No pre-commit hook examples for running flux-drive agents
- CI integration is mentioned in beads (`iv-z1a6` release coupling) but not as a general bridge

**Evidence:**
- Clavain has upstream-check.yml, pr-agent-commands.yml (GitHub workflows exist)
- No `/docs/ci-integration.md` in interflux or interwatch
- Interpath generates artifacts but doesn't trigger on PR events

**Solution:**
Not a new module, but **reference implementations + documentation**:
1. **GitHub Actions workflow templates** in `Interverse/infra/ci-templates/`:
   - `interflux-pr-review.yml` — Run fd-correctness, fd-safety agents on PR diffs
   - `interwatch-drift-check.yml` — Fail CI if PRD/roadmap drift > "High" confidence
   - `interpath-changelog.yml` — Auto-generate changelog on release tags
2. **Pre-commit hook examples** in `Interverse/infra/git-hooks/`:
   - `pre-commit-interflux-syntax` — Run fd-correctness on staged files (local, fast)
   - `pre-commit-interwatch-drift` — Warn if committing code without updating docs
3. **Cost-aware CI patterns** — Use Haiku for CI reviews, Opus for release-blocking checks
4. **Documentation** — `docs/guides/ci-integration.md` with copy-paste examples

**Why high impact:**
- **Workflow gap:** Users have the tools but not the integration recipes
- **Quality gates:** Automated reviews catch bugs pre-merge (shift-left quality)
- **Adoption barrier:** "I'd use interflux if it ran in CI" is a common blocker (anecdotal)

**Integration points:**
- Works with: interflux (agent orchestration), interwatch (drift scoring), interpath (artifact gen)
- Requires: GitHub Actions runner, Claude API key in secrets, beads CLI in CI env

**Non-goals:**
- Full GitLab/CircleCI/Jenkins support (defer, focus on GitHub Actions for v1)
- Self-hosted runner setup docs (assume cloud runners)
- CI-specific interflux agents (reuse existing agents)

---

### 5. **Skill Discovery Gap Filler: Auto-Suggest Missing Skills**
**User pain (anecdotal, inferred):**
Power users discover skills by:
1. Reading SKILL.md files manually
2. Asking "is there a skill for X?"
3. Stumbling on skills via `/using-clavain` routing table

**Problem:** No proactive discovery. If a user doesn't know `/tldrs-find` exists, they grep manually.

**Solution:**
A new Clavain hook (not standalone module) **skill-suggest.sh** (PostToolUse:Bash):
1. **Pattern matching** — On `grep -r`, suggest `/tldrs-find`; on `find . -name`, suggest `/tldrs-structural`
2. **Frequency-based hints** — "You've run `bd list` 10 times this week, did you know about `/sprint-status`?"
3. **Context-aware suggestions** — If in a Git repo with `.beads/`, suggest beads skills on relevant commands
4. **Skill gap analysis** — Compare user's tool usage (from tool-time) to available skills, surface unused high-value skills

**Why medium-high impact:**
- **Adoption barrier:** Users pay for tools they don't know exist
- **Discoverability:** Current discovery is passive (read docs) not active (system suggests)
- **Workflow efficiency:** Using the right skill saves 5-15 minutes per task

**Integration points:**
- Hooks: PostToolUse:Bash (pattern detection), SessionStart (weekly skill report)
- Companion to: tool-time (usage patterns), clavain (skill registry)
- Storage: `.clavain/skill_suggestions_seen.json` (don't repeat suggestions)

**Non-goals:**
- Suggesting skills from other plugins (focus on Clavain skills for v1)
- AI-based suggestion (defer, use regex patterns)
- Skill marketplace/install automation (defer to plugin installation flow)

---

## Gap Analysis: Integration Opportunities (Existing Modules)

### 6. **Interject → Clavain Sprint Routing (Partial — iv-z1a4 exists)**
**Status:** Tracked as `iv-z1a4` (Interkasten context into discovery and sprint intake), but limited to Interkasten.

**Expansion:** Interject ambient discovery (15 MCP tools for search/analysis) should feed into Clavain sprint intake:
- Interject briefing docs in `docs/research/` → auto-triage into sprint backlog
- "Discovery → Action pipeline" (mentioned in brainstorm) is half-implemented

**Why not already tracked:**
- `iv-z1a4` is Interkasten-specific (Notion sync context)
- Interject integration is mentioned in brainstorm but no bead exists

**Recommendation:** Create new bead `iv-<new>: Interject briefings → Clavain sprint intake routing`

---

### 7. **Interphase Gate Failures → Interwatch Escalation**
**User pain (inferred):**
When a phase gate fails (test failures, lint errors, quality gate blocking findings), the failure is logged but:
- No automatic documentation update triggered
- No interwatch signal generated (drift detection doesn't know about gate failures)
- User manually must update PRD/plan to reflect "why did this fail?"

**Solution:**
New interphase → interwatch integration:
1. On gate failure, emit interwatch signal with confidence="High" (certainty that docs may be stale)
2. Interwatch suggests updating plan with failure context
3. Optional: auto-generate "Gate Failure" section in plan with failure logs

**Why medium impact:**
- **Workflow continuity:** Gate failures break flow; auto-doc helps resume
- **Knowledge capture:** Failure context is lost if not immediately documented

---

### 8. **Beads State Transitions → Intermute Event Bus**
**User pain (inferred from architecture):**
When Agent A closes a bead, Agent B (working on a dependent bead) doesn't know until they manually run `bd list` or hit a blocker.

**Current state:**
- Beads are per-agent (no cross-session reactive updates)
- Intermute has messaging, but beads don't publish to it

**Solution:**
New beads hook (PostToolUse:Bash on `bd close`, `bd update`) publishes state transitions to intermute:
- `bead.closed` event with `{issue_id, title, dependencies_unblocked: [...]}`
- `bead.blocked` event when a dependency is added
- Agents subscribe to events for beads they depend on

**Why medium impact:**
- **Multi-agent workflows:** Reduces "waiting for blockers" check loops
- **Workflow automation:** Enables "when X closes, auto-start Y" patterns

**Related to:** `iv-z1a1` (Inter-module event bus + event contracts) — **exact match**

---

### 9. **Interline Statusline: Multi-Agent Awareness**
**User pain (inferred):**
When running 3 agents via interlock, each agent's statusline shows only their own state. No visibility into:
- "Agent B is waiting on me to release file X"
- "2 other agents are in-progress on this project"
- "Agent C just committed, I should pull"

**Solution:**
Extend interline to query intermute and show:
- Active agents on this project (names, uptime, current phase)
- Pending release requests (file, requester, age)
- Recent commits from other agents (last 10 minutes)

**Why medium-high impact:**
- **Coordination visibility:** Reduces "am I the only one working here?" uncertainty
- **Workflow efficiency:** Surfacing release requests speeds up negotiation

**Related to:** `iv-z1a2` (Interline as unified operations HUD) — **exact match**

---

### 10. **Tool-Time Cost Attribution: Per-Agent Breakdown**
**User pain (assumed, plausible):**
tool-time tracks tool usage but not per-agent cost attribution in multi-agent workflows. Power users want:
- "Which flux-drive agent is most expensive?"
- "Is fd-architecture worth the cost vs. fd-correctness?"
- Per-project cost heatmaps (which modules burn tokens)

**Solution:**
Extend tool-time to parse agent names from tool calls, track cost per agent, expose in dashboard.

**Why medium impact:**
- **Cost visibility:** Helps prioritize which agents to run
- **ROI analysis:** Data-driven decisions on agent usage

**Overlap with:** interbudget (#2 above) — **these should be unified or clearly separated**

---

## External Integration Opportunities

### 11. **GitHub Issue/PR Auto-Sync to Beads**
**User pain (anecdotal):**
Users maintain issues in both GitHub and beads, leading to drift. No two-way sync exists.

**Solution:**
New module **intergit** (or extend interkasten):
1. On GitHub issue create → auto-create bead with `gh_issue_url` state field
2. On bead close → auto-comment on GitHub issue with close reason
3. Bi-directional sync via GitHub webhooks (self-hosted or GitHub Actions)

**Why medium impact:**
- **Workflow unification:** Single source of truth for issues
- **Team collaboration:** External contributors see bead-tracked work

**Non-goals:**
- Full GitHub Project board sync (complex, defer)
- Real-time sync (polling/webhook delay acceptable)

---

### 12. **Slack Alerts for Critical Events**
**User pain (anecdotal):**
Power users want Slack alerts for:
- Phase gate failures during sprints
- Interlock negotiation timeouts (no response from Agent A)
- Interwatch "Certain" drift (AGENTS.md is stale)
- Session crashes (from interlog)

**Current state:**
- interslack exists but is manual (`/slack:send`)
- No event-driven alerting

**Solution:**
Extend interslack with hooks:
1. SessionEnd (abnormal exit) → Slack DM
2. Interwatch drift > "High" → Slack channel
3. Interlock timeout → Slack thread

**Why medium impact:**
- **Async awareness:** Alerts when not actively in Claude session
- **Critical issues:** Don't miss gate failures or crashes

---

## Research & Ecosystem Health Opportunities

### 13. **Interaudit: Plugin Health + Dependency Checker**
**User pain (assumed, inferred from plugin count):**
With 22 modules, plugin health is hard to track:
- Which plugins have stale dependencies?
- Which MCP servers crash silently?
- Which skills haven't been updated in 6 months?
- Are there circular dependencies between plugins?

**Solution:**
New module **interaudit**:
1. `/interaudit:health` — Check all installed plugins: version staleness, MCP server liveness, hook success rates
2. `/interaudit:deps` — Dependency graph (which plugins depend on which)
3. `/interaudit:stale` — List plugins with no commits in 90 days, flag for review
4. Automated weekly report (cron or GitHub Actions)

**Why medium-high impact:**
- **Ecosystem maintenance:** Prevents plugin rot
- **Developer UX:** "Which plugin broke?" is a common debug question

**Integration points:**
- Reads: `~/.claude/settings.json` (installed plugins), marketplace.json, plugin.json files
- Companion to: interlog (plugin crash telemetry)

---

### 14. **Interbench Expansion: Regression Testing for Plugins**
**User pain (data-backed from tldrs):**
tldrs has interbench integration for regression testing, but other plugins don't. Plugin changes risk breaking existing workflows.

**Solution:**
Expand interbench to support:
1. Regression suites for all plugins (not just tldrs)
2. Artifact capture for interpath, interwatch, interdoc outputs
3. A/B testing framework for skill effectiveness

**Why medium impact:**
- **Quality gates:** Catch regressions before publish
- **Confidence:** Safe to refactor if tests pass

**Overlap with:** existing interbench (expand, not new module)

---

### 15. **Knowledge Compounding Export: Interscribe Integration Check**
**User pain (tracked, deferred):**
`iv-sdqv` (interscribe extraction for knowledge compounding) is tracked but not prioritized.

**Opportunity:** Surface compounded learnings from MEMORY.md into:
- Interject briefings (connect external research to internal learnings)
- Clavain skill refinement (update skills based on lessons learned)
- Interwatch "patterns" (common drift patterns observed)

**Why medium-low impact:**
- **Long-term value:** Compounding takes time to show ROI
- **Already tracked:** No need for new bead, just prioritize existing

---

## Summary of Recommendations

### Tier 1: High User Impact, Clear Pain Point (Ship First)
1. **interlog** (session crash recovery + observability dashboard) — New module
2. **interbudget** (token budget controls + cost reporting) — New module
3. **intercache** (smart semantic caching) — New module
4. **CI/CD integration bridge** (interflux + interwatch templates) — Docs + examples, not new module

### Tier 2: Medium-High Impact, Integration Work (Ship Second)
5. Skill discovery gap filler (auto-suggest) — Clavain hook extension
6. Interject → Clavain sprint routing — New bead (expand iv-z1a4)
7. Interline multi-agent awareness — Extends iv-z1a2
8. Interaudit (plugin health checker) — New module

### Tier 3: Medium Impact, Opportunistic (Ship When Relevant)
9. Interphase gate failures → Interwatch escalation — Integration
10. Beads → Intermute event bus — Hook extension (iv-z1a1)
11. Tool-time cost attribution — Extend tool-time or merge into interbudget
12. GitHub issue/PR auto-sync — New module (intergit)
13. Slack alerts for critical events — Extend interslack
14. Interbench regression expansion — Extend existing infra

### Tier 4: Research/Long-Term (Defer)
15. Interscribe knowledge compounding (already tracked as iv-sdqv)

---

## User Impact Validation

### Evidence Quality by Opportunity
| Opportunity | Evidence | User Segment | Frequency |
|------------|----------|--------------|-----------|
| interlog | **Data-backed** (sprint resilience PRD, crash mentions) | Solo power users | Weekly |
| interbudget | **Anecdotal** (standard SaaS pattern, Oracle cost warnings) | All users | Monthly |
| intercache | **Inferred** (architecture gap, no cache exists) | Large repo users | Daily |
| CI/CD bridge | **Data-backed** (workflow gap in docs, iv-z1a6) | Plugin developers | Per-release |
| Skill discovery | **Anecdotal** (no proactive hints exist) | New users | Per-feature-discovery |

### Workflow Friction Addressed
- **Session continuity:** interlog (crash recovery), intercache (faster resume)
- **Cost anxiety:** interbudget (guardrails), tool-time cost attribution
- **Multi-agent coordination:** Interline awareness, beads → intermute events
- **Quality gates:** CI/CD bridge, interphase → interwatch integration
- **Discoverability:** Skill auto-suggest, interaudit health checks

---

## Open Questions for User Validation

1. **Cost vs. usage tracking:** Should interbudget and tool-time merge, or stay separate? (Recommendation: merge into tool-time v2 with cost module)
2. **Cache privacy:** Is cross-session file caching acceptable, or does it feel invasive? (Recommendation: opt-out with clear disclosure)
3. **CI integration priority:** Is GitHub Actions the right focus, or do users need GitLab/CircleCI first? (Recommendation: GitHub Actions for v1, validate before expanding)
4. **Skill suggestions:** Helpful or annoying? (Recommendation: weekly summary mode, not per-command)
5. **Multi-agent statusline:** Do users want "other agents" visibility, or is it noise? (Recommendation: opt-in via interline config)

---

## Next Steps

1. **Validate top 3 with user interviews** (if applicable) — Confirm interlog, interbudget, intercache are real pain points
2. **Create beads for Tier 1 opportunities** — Start with interlog (highest crash recovery value)
3. **Document CI/CD bridge patterns** — Quick win, no new code needed
4. **Prototype skill auto-suggest** — Easiest to test, fast feedback loop
5. **Revisit iv-z1a0 program** — Many opportunities overlap with existing integration beads, consolidate tracking
