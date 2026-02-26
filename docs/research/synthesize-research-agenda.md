# Monorepo Research Agenda — Thematic Synthesis

**Generated:** 2026-02-23
**Source:** 29 brainstorms/plans + existing research items
**Scope:** Q1 2026 roadmap thematic grouping

---

## Thematic Bullets (10-15 bullets, grouped)

### Kernel & Core Infrastructure

- **Intercore E-Series Completion** — Implement E3 (hook migration to kernel), E5 (discovery pipeline), E6 (rollback/recovery), E8 (portfolio orchestration) to establish kernel as the unified runtime for all phase/discovery/dispatch/portfolio state.

- **Event-Driven Advancement** — Wire phase transitions through event-emitting action system: `ic run advance` returns resolved next-command(s) via `phase_actions` table so callers dispatch without script logic.

- **Schema & Durability** — Extend intercore schema (v14+) with lanes, phase actions, and feedback signals; add comprehensive migration tests to prevent silent schema corruption.

### Sprint Workflow Hardening

- **Multi-Session File Coordination** — Implement git-index-per-session + flock-serialized commits (GIT_INDEX_FILE), mandatory file reservations on edit (blocking hook + auto-reserve), and session registration in sprint flow.

- **Sprint Resilience & Resume** — Make sprint state fully kernel-driven via `ic run` (no beads fallback), cache run ID at claim, add session-start sprint detection for zero-setup resume on restarts.

- **Cost-Aware Execution** — Make token spend a first-class resource: sprint budget parameter + budget-aware phase-advance checks + sprint remaining-budget visibility in flux-drive triage.

### Cognitive & Review Systems

- **Flux-Drive Lens Integration** — Migrate Interlens into Interverse as `plugins/interlens/`, create fd-systems cognitive agent, add triage pre-filter to exclude cognitive agents from diff inputs.

- **Flux-Drive Document Slicing** — Build interserve Go MCP server that classifies document sections per agent domain using Codex spark; generate per-agent temp files; reduce token consumption 50-70%.

- **Progressive Review Findings** — Surface flux-drive findings incrementally during review (not only at synthesis) so operators act on high-confidence items early.

### Plugin Ecosystem Integration

- **Dual-Mode Plugin Architecture** — Ship interbase.sh SDK + integration.json schema + companion nudge protocol; migrate interflux as reference implementation so plugins work as both CLI and MCP.

- **Agent Capability Discovery** — Wire end-to-end: agents advertise capabilities at registration (`.config/clavain/capabilities-*.json`), intermute filters by capability, consumers query via `ic agent list --capability=`.

- **Plugin Synergy & Interop** — Connect Interverse plugins via interband signals (atomic JSON files), statusline enrichment, interbase SDK adoption, cross-plugin data bridges (interstat, intercheck, intermem).

### Work Organization & Prioritization

- **Thematic Work Lanes** — Add lanes as first-class kernel entity (auto-discover from `bd label lane:*`), integrate with sprint/discovery filtering, implement lane-scoped Pollard hunters with starvation-weighted scheduling.

- **Portfolio Orchestration & Scheduling** — Implement E8 for multi-project coordination: portfolio lanes, dependency scheduling, rollback policy, portfolio-level advance gates.

- **Structured Reflection & Learning** — Integrate reflect phase gate into sprint workflow, wire kernel-native reflect to Clavain OS, capture learning artifacts durably (not in beads).

### Developer Tools & Observability

- **Token-Efficient Skill Loading** — Generate compact SKILL.md files (60-80 lines) for interwatch, interpath, flux-drive; pre-compute watchable signals via interwatch-scan.py; reduce LLM context overhead.

- **Agent Capability Stubs & Discovery** — Extend registration scripts to read capability files, expose capabilities via intermute HTTP + MCP, enable dynamic agent discovery in sprint assignment.

- **Intercore CLI Observability** — Add comprehensive `ic` status/health/debug commands; expose kernel state via statusline; add rollback metadata queries for code layer inspection.

### Integration & Expansion

- **Gemini CLI Adapter** — Build integration for `gemini` model in Intercom NanoClaw runtime; wire runner registration, model announcement, cost tracking.

- **Autarch Dashboard & Status Tools** — Implement TUI status dashboard with kernel data sources; add phase/artifact/budget visualization; implement file-fallback for degraded-state rendering.

- **Plugin Publishing & Validation Gates** — Add validation gates for plugin publishing: capability declarations, integration.json schema compliance, MCP server health checks.

---

## Preserved Existing Research Items

> These items remain active; integrate findings into implementation:

- Evaluate safe approval flows for phase gates over chat (spans: sprint workflow, reflect phase, phase gates)
- Define thin integration boundaries with Clavain intents and Intercore event consumption (spans: plugin synergy, intercore events, sprint handover)
- Determine high-signal message summaries that reduce operator noise (spans: progressive review findings, statusline, phase advancement)
- Evaluate graph readability metrics for large-node scenarios (spans: portfolio orchestration, lane visualization)
- Determine the right thresholding strategy for overlap domains (spans: lane membership, agent capability, discovery scoring)
- Explore compact diff artifacts suitable for PR review (spans: flux-drive slicing, progressive findings, token efficiency)
- Evaluate ranking heuristics against real incident-resolution tasks (spans: discovery pipeline, work prioritization)
- Identify lightweight scoring signals for "reused successfully" outcomes (spans: agent discovery, plugin synergy)
- Define a stable schema for cross-tool consumption of index outputs (spans: TLDR symbol index, discovery pipeline, portfolio data)

---

## Cross-Cutting Themes

### Execution Sequencing

1. **Kernel Foundation (Weeks 1-2):** E3 hook cutover, schema v14+ migrations, event-driven advancement framework
2. **Sprint Hardening (Weeks 2-3):** Multi-session coordination, resilience, cost-awareness
3. **Cognitive Layer (Weeks 3-4):** Interlens migration, document slicing, progressive findings
4. **Ecosystem Glue (Weeks 4-5):** Dual-mode SDK, capability discovery, plugin synergy
5. **Organization & Tools (Weeks 5-6):** Lanes, portfolio, reflection, token efficiency, dashboards

### Risk Mitigations

- **Git Index Corruption:** Local `flock` prevents concurrent `git add`, session-specific `GIT_INDEX_FILE` eliminates shared state
- **Plugin Namespace Collision:** Use `_INTERBASE_` prefix for centralized library, `_ib_` for functions, validate loading guards
- **Discovery Drift:** Pre-compute signals via interwatch-scan.py (not dynamic evaluation), store confidence tiers durably
- **Token Budget Overruns:** Phase-advance checks against `ic run budget`, sprint-level enforcement, progressive token reporting
- **Phase Deadlock:** Event-driven advancement with explicit action routing prevents implicit state machines

### Open Questions

1. **Capability Discovery Staging:** Should agents register capabilities at startup (startup cost) or on-demand (query latency)?
2. **Portfolio Rollback Scope:** When rolling back a portfolio lane, should it also rewind dependent lanes in other projects?
3. **Reflect Phase Customization:** Does each lane get its own reflect policy, or is reflection standardized across portfolio?
4. **Lane Membership Dynamics:** Should lanes auto-expand/contract based on issue labels, or require manual scope management?

---

## Dependencies & Blockers

- **Prerequisite:** `sdk/interbase/templates/interbase-stub.sh` fix (set `_INTERBASE_LOADED=1` unconditionally before live source)
- **Prerequisite:** `sdk/interbase/lib/interbase.sh` fix (`_ib_nudge_is_dismissed` jq-absent fallback returns 0)
- **Blocker:** All E3 tasks require intercore wrapper functions in `lib-intercore.sh` (Task 0 in sprint-handover plan)
- **Blocker:** Dual-mode SDK must ship before plugin migration (Task 1 of dual-mode-plugin-architecture)

---

## Metrics & Success Criteria

- **Kernel:** Beads→kernel migration complete; no remaining beads-fallback code in Clavain
- **Sprint:** Multi-session test passes with concurrent edits to same repo; session resume under 5s
- **Cognitive:** Flux-drive document slicing reduces per-agent context by >60%
- **Ecosystem:** All interverse plugins adopt interbase SDK; capability discovery queries <100ms
- **Organization:** Lanes fully integrated; portfolio orchestration handles 50+ project dependencies
- **Efficiency:** Skill loading token cost <2% of full SKILL.md; token budget enforcement prevents >10% budget overruns

---

## Related Documentation

- **PRDs:** `docs/prds/2026-02-*` (29 files, one per plan/brainstorm)
- **Research:** `docs/research/` (existing findings, architecture reviews, correctness reviews)
- **Brainstorms:** Listed above — archive after plan extraction
- **Kernel Contract:** `core/intercore/docs/` + `infra/intercore/docs/` (E-series specs, schema docs)
