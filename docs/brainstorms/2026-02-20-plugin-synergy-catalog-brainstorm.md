# Plugin Synergy Catalog: Low-Hanging Interop Opportunities
**Bead:** iv-vlg4

**Date:** 2026-02-20
**Type:** Brainstorm — comprehensive catalog
**Scope:** Integration improvements + emergent features across all Interverse plugins

## What We're Exploring

The Interverse has 31 plugins, 1 hub (Clavain), 1 service (intermute), and 1 SDK (interbase). They coordinate through three layers: **interband** (real-time file signals), **beads** (persistent issue state), and **verdicts** (review output). Many plugins solve adjacent problems independently. This brainstorm catalogs every integration gap and emergent opportunity, organized by theme.

## Why Now

The ecosystem has reached critical mass — enough plugins exist that cross-cutting synergies outweigh new plugin development. Several plugins duplicate staleness detection, analytics are collected but never consumed, and interbase adoption is minimal despite being purpose-built for ecosystem integration.

---

## Category 1: Feedback Loops (Data Collected but Never Consumed)

### 1.1 intercheck context pressure → interline statusline

**Gap:** intercheck tracks context pressure (Green/Yellow/Orange/Red thresholds at 60/90/120 tool calls) and stores it at `/tmp/intercheck-${SESSION_ID}.json`. interline renders the statusline but has no idea about context pressure.

**Opportunity:** intercheck writes pressure level to interband (`intercheck/pressure`). interline reads it and shows a colored indicator (green dot, yellow warning, red alert) in the statusline.

**Effort:** Small — intercheck already has the data, interline already reads interband channels.

**Impact:** High — users get ambient awareness of context burn rate without running `/intercheck:status`.

### 1.2 interstat token spend → model routing decisions

**Gap:** interstat tracks cumulative token consumption per sprint in SQLite (`~/.claude/interstat/metrics.db`). Clavain's model routing (`/clavain:model-routing`) switches between economy and quality modes. These don't talk to each other.

**Opportunity:** When interstat detects a sprint approaching its token budget (e.g., 80% consumed), emit an interband signal. Clavain's subagent dispatcher reads it and auto-downgrades to economy routing for remaining work. Override with `--quality` flag.

**Effort:** Medium — needs interband write in interstat, read in Clavain dispatch.

**Impact:** Medium — prevents budget blowouts on long sprints.

### 1.3 tool-time analytics → intelligent tool selection

**Gap:** tool-time collects tool usage events (`~/.claude/tool-time/events.jsonl`) with timing data. No plugin uses this to inform behavior.

**Opportunity:** tool-time exposes a summary function (or interband channel) with "slow tools" data. Plugins that dispatch subagents (interflux, intersynth) could prefer faster tool patterns. For example, if Serena MCP calls are consistently 5x slower than Read/Grep, flux-drive agents could get a hint to prefer native tools.

**Effort:** Medium — needs aggregation logic in tool-time, consumption in flux-drive agent prompts.

**Impact:** Low-Medium — marginal speed improvement, but compounds across many agent dispatches.

### 1.4 intercheck syntax errors → intertest regression signal

**Gap:** intercheck's syntax-check hook validates Python/Shell/Go/JS after every Edit/Write and tracks error count. intertest provides TDD and debugging disciplines but doesn't know about syntax failures.

**Opportunity:** When intercheck detects repeated syntax errors in the same file (≥3 in a session), signal intertest to suggest switching to TDD mode for that file. Ambient nudge, not enforcement.

**Effort:** Small — intercheck already counts errors, just needs interband write + intertest PostToolUse read.

**Impact:** Low — nice-to-have behavioral nudge.

### 1.5 interstat sprint metrics → internext work prioritization

**Gap:** internext scores work items on impact/effort/risk but has no data about actual historical effort. interstat has per-sprint token consumption.

**Opportunity:** internext reads interstat historical data to calibrate effort estimates. "Similar past sprints used X tokens" becomes a data-backed effort signal instead of pure heuristic.

**Effort:** Medium — needs interstat query API and internext integration.

**Impact:** Medium — better prioritization decisions over time.

---

## Category 2: Staleness Detection Unification

### 2.1 Unified staleness service (decided: unified approach)

**Gap:** Three plugins detect staleness independently:
- **interwatch** — document drift scoring (content hash comparison, git log analysis)
- **intermem** — memory entry decay (time-based confidence penalty, stale_streak counter)
- **interdoc** — AGENTS.md drift (structural comparison, drift-fix scripts)

Each has its own hashing, scoring, and threshold logic. They don't share signals.

**Opportunity:** Create a shared staleness library (could live in interbase or as a new `lib/staleness.sh`) that provides:
- `staleness_score(filepath)` — unified 0-100 freshness score
- `staleness_notify(filepath, score)` — write to interband `staleness/changed`
- `staleness_subscribe(callback)` — react to freshness changes

Each plugin keeps its domain-specific decay model but delegates core scoring to the shared library.

**Effort:** Large — design the API, migrate three plugins.

**Impact:** High — eliminates three independent implementations, enables new consumers.

### 2.2 interwatch drift → intermem confidence penalty

**Gap:** When interwatch detects a document has drifted (low freshness score), intermem doesn't know. Memory entries citing that document continue at full confidence.

**Opportunity:** interwatch writes drift events to interband. intermem's decay pipeline reads them and applies a confidence penalty to entries citing drifted documents.

**Effort:** Small — point bridge, doesn't require unified service.

**Impact:** Medium — prevents promoting stale knowledge that cites outdated docs.

### 2.3 interdoc AGENTS.md drift → interwatch monitoring

**Gap:** interdoc generates AGENTS.md files and has drift-fix scripts. interwatch monitors document freshness. They don't coordinate — interwatch might flag an AGENTS.md as stale while interdoc's drift-fix could auto-repair it.

**Opportunity:** Register interdoc-managed files with interwatch as "auto-repairable". When interwatch detects drift, it checks if interdoc can fix it before alerting the user.

**Effort:** Small — interwatch needs a "repairable" flag per watched file.

**Impact:** Low — reduces false-positive drift alerts.

---

## Category 3: interbase SDK Adoption

### 3.1 Current state

Only **interflux** has adopted interbase (stub + integration.json). The SDK provides:
- `ib_has_companion(name)` — check if a companion plugin is installed
- `ib_nudge_companion(companion, benefit)` — suggest missing plugins (max 2/session)
- `ib_phase_set(bead, phase)` — set bead phase (no-op without bd)
- `ib_in_ecosystem()` — detect Interverse vs standalone mode

### 3.2 High-value adoption targets

Plugins that would benefit most from interbase:

| Plugin | Why | Effort |
|--------|-----|--------|
| **interline** | Could nudge "install intercheck for pressure display" | Small |
| **intersynth** | Could check for interflux before synthesis, nudge if missing | Small |
| **intermem** | Could nudge "install interwatch for citation freshness" | Small |
| **intertest** | Could check for intercheck companion, share syntax data | Small |
| **internext** | Could nudge "install interstat for effort calibration" | Small |
| **tool-time** | Could check for interstat, share metrics | Small |

### 3.3 Batch adoption pattern

Each adoption follows the same 3-step pattern:
1. Copy `templates/interbase-stub.sh` into plugin's `hooks/`
2. Create `.claude-plugin/integration.json`
3. Add `source interbase-stub.sh` to session-start hook

This is highly parallelizable — 6 plugins could be adopted in one sprint.

---

## Category 4: Data Flow Bridges (Point-to-Point)

### 4.1 interflux verdict findings → beads auto-creation

**Gap:** After flux-drive review, verdict files sit in `.clavain/verdicts/`. P0/P1 findings require manual bead creation.

**Opportunity:** intersynth's synthesis step could auto-create beads for P0/P1 findings that aren't addressed in the current sprint. Uses `bd create` with verdict metadata.

**Effort:** Medium — needs verdict-to-bead mapping logic, dedup against existing beads.

**Impact:** Medium — eliminates manual triage for critical findings.

### 4.2 interject discoveries → internext scoring

**Gap:** interject scans arXiv, HN, GitHub for relevant capabilities and creates beads. internext scores work items for prioritization. They don't talk.

**Opportunity:** internext factors in interject's recommendation confidence when scoring discovery-originated beads. High-confidence discoveries (strong match to learned profile) get a priority boost.

**Effort:** Small — internext reads bead metadata that interject already writes.

**Impact:** Low-Medium — better discovery-to-action pipeline.

### 4.3 interlock coordination state → interline statusline

**Gap:** interlock manages multi-agent file reservations. interline shows dispatch state. When multiple agents are coordinating, the statusline doesn't reflect coordination status.

**Opportunity:** interlock already writes to interband (`interlock/coordination`). interline could read this and show "2 agents coordinating" or "file conflict" in the statusline.

**Effort:** Small — interline already reads interband, just needs a new channel reader.

**Impact:** Medium — ambient awareness of multi-agent coordination state.

### 4.4 intermux agent activity → interstat token accounting

**Gap:** intermux monitors tmux sessions and agent activity. interstat tracks token consumption. When agents run in tmux sessions, their token spend isn't attributed.

**Opportunity:** intermux provides session-to-agent mapping. interstat uses this to attribute token spend to specific agent dispatches rather than just "the session."

**Effort:** Medium — needs intermux query + interstat attribution logic.

**Impact:** Low — better accounting, useful for cost analysis but not critical.

### 4.5 tldr-swinton context → interflux agent prompts

**Gap:** tldr-swinton provides token-efficient code context (function signatures, call graphs, semantic search). interflux's review agents use Read/Grep to understand code.

**Opportunity:** interflux review agents could use tldr-swinton's MCP tools (`find`, `context`, `extract`) to get structured code context instead of raw file reads. More precise, fewer tokens.

**Effort:** Medium — needs agent prompt modifications + MCP tool availability check.

**Impact:** Medium — potentially significant token savings in code review workflows.

### 4.6 interfluence voice profile → interpath artifact generation

**Gap:** interfluence maintains a voice profile for consistent writing style. interpath generates artifacts (roadmaps, PRDs, vision docs) in a generic voice.

**Opportunity:** interpath checks for interfluence voice profile and applies it when generating artifacts. Documents come out sounding like the user wrote them.

**Effort:** Small — interpath already has a template system, just needs profile injection.

**Impact:** Low-Medium — nice polish for generated docs.

---

## Category 5: Emergent Features (New Capabilities from Combining Data)

### 5.1 Session health dashboard (intercheck + interstat + tool-time + interline)

**Emergent from:** All four analytics plugins contributing to a unified view.

**Concept:** interline's statusline shows a single health indicator computed from: context pressure (intercheck), token spend rate (interstat), and tool efficiency (tool-time). Click/expand shows full dashboard.

**Effort:** Medium — aggregation logic + interline rendering.

**Impact:** High — ambient session intelligence.

### 5.2 Smart checkpoint triggers (intercheck + intermem + beads)

**Emergent from:** Context pressure + memory synthesis + bead state.

**Concept:** When intercheck hits Orange pressure AND there are unsaved learnings in auto-memory, trigger intermem synthesis before context compaction. Ensures knowledge isn't lost to context window limits.

**Effort:** Medium — needs interband coordination between intercheck and intermem.

**Impact:** High — prevents knowledge loss during long sessions.

### 5.3 Cost-aware review depth (interstat + interflux)

**Emergent from:** Token budget tracking + multi-agent review.

**Concept:** interflux's flux-drive already has agent triage. If interstat reports budget pressure, flux-drive reduces agent count or switches to compact review mode. Already partially supported via `FLUX_BUDGET_REMAINING` env var — just needs tighter integration.

**Effort:** Small — env var bridge already exists, just needs to be always-on instead of sprint-only.

**Impact:** Medium — prevents review agents from blowing the budget.

### 5.4 Cross-session knowledge graph (interkasten + intermem + interlens)

**Emergent from:** Notion sync + memory promotion + cognitive lenses.

**Concept:** intermem graduates facts to AGENTS.md. interkasten syncs to Notion. interlens provides cognitive analysis frameworks. Combined: a knowledge graph that tracks how understanding evolves across sessions, with Notion as the durable store.

**Effort:** Large — significant integration work.

**Impact:** Medium — long-term knowledge management improvement.

### 5.5 Automated plugin health report (intercheck + tool-time + interstat)

**Emergent from:** Syntax checking + tool usage patterns + token metrics.

**Concept:** Weekly automated report: which plugins' hooks are slow, which skills are unused, which MCP servers have high latency. Surfaces plugin maintenance needs.

**Effort:** Medium — aggregation + report generation.

**Impact:** Medium — helps maintain ecosystem health.

---

## Category 6: Coordination Protocol Improvements

### 6.1 interband channel registry

**Gap:** Plugins write to ad-hoc interband channels. No central registry of channel names, schemas, or retention policies. A new plugin has to grep the codebase to discover available channels.

**Opportunity:** A `channels.json` manifest in interband root listing all registered channels with schema, producer, consumers, and retention policy.

**Effort:** Small — documentation + validation script.

**Impact:** Medium — enables safe new integrations.

### 6.2 Hook execution ordering

**Gap:** Multiple plugins register PostToolUse hooks. Execution order is undefined. If intercheck's syntax-check runs after interflux's review, they may conflict.

**Opportunity:** Document expected execution order. Investigate if Claude Code supports hook priority/ordering.

**Effort:** Small — mostly documentation + testing.

**Impact:** Low — prevents subtle ordering bugs.

### 6.3 Companion plugin dependency graph

**Gap:** No machine-readable graph of which plugins enhance which others. interbase's `ib_nudge_companion` is per-plugin but there's no ecosystem-wide view.

**Opportunity:** A `companion-graph.json` at the Interverse root listing edges like `interflux -> intersynth (uses verdict synthesis)`, `intercheck -> interline (pressure display)`. Enables `/clavain:doctor` to report "you have interflux but not intersynth — synthesis won't work."

**Effort:** Small — static file + doctor integration.

**Impact:** Medium — better install guidance and health checks.

---

## Key Decisions

1. **Unified staleness service** over shared-signal loose coupling — invest in a proper shared library
2. **Comprehensive catalog** over top-3 deep-dive — capture everything now, prioritize during strategy
3. **Integration + emergent features** — don't limit to just wiring, also capture new capabilities
4. **Both advisory signals and soft automation** to be explored during planning — no premature commitment

## Priority Matrix (Effort vs Impact)

### Quick Wins (Small effort, High/Medium impact)
- 1.1 intercheck pressure → interline statusline
- 4.3 interlock coordination → interline statusline
- 5.3 Cost-aware review depth (env var already exists)
- 6.3 Companion plugin dependency graph
- 3.2 Batch interbase adoption (6 plugins)

### Strategic Investments (Medium effort, High impact)
- 5.1 Session health dashboard
- 5.2 Smart checkpoint triggers
- 1.2 interstat → model routing
- 2.1 Unified staleness service

### Nice-to-Haves (captured for future reference)
- 1.3 tool-time → tool selection hints
- 4.4 intermux → interstat attribution
- 4.6 interfluence → interpath voice
- 5.4 Cross-session knowledge graph
- 6.2 Hook execution ordering docs

## Open Questions

1. Should the unified staleness service live in interbase (SDK) or as a standalone library?
2. Should interband channel writes be fire-and-forget or have delivery confirmation?
3. How do we handle circular dependencies (e.g., intercheck nudges intertest, intertest nudges intercheck)?
4. What's the testing strategy for cross-plugin integration? Currently each plugin tests in isolation.
