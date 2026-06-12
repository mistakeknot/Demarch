# Sylveste Roadmap

**Modules:** `find apps os core interverse sdk -maxdepth 2 -name .git -printf '%h\n' 2>/dev/null | wc -l` | **Beads:** `bd stats` | **Last updated:** 2026-03-27
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json) — auto-generated superset of roadmap-placed items only (fewer than `bd stats` totals, which track all beads).

---

## Now — Frontier Priorities

**P1: Skaffen competitive gap closure** (Sylveste-6i0, epic, 22 open subtasks). The largest active epic. Closing feature gaps identified in the coding-agent feature matrix — hooks, compaction, skills, subagents, sandbox, image support, web search, plan mode, and more. 1/23 subtasks shipped so far. Brainstorms and plans landed for most critical gaps (hook system, skills system, subagent system, sandbox, image support, web search, plan mode, per-project config).

**P1: SWE-bench pass rate** (Sylveste-ynh Phase 1 + Sylveste-9lx Phase 2). Two epics targeting +15-20% (quick wins: grep context lines, glob fixes, tail-preserving truncation, py_compile validation, fault hypothesis prompting) and +10-15% (test-driven feedback loop, empty-diff detection, aggregate diff review). pyenv per-cell Python selection (Sylveste-sdk0) also open.

**P1: Infrastructure + bugs.**
- **iv-ho3** StrongDM Factory Substrate — validation-first infra for Clavain. In progress. Blocks iv-296 → iv-g36hy → iv-3ov (the measurement chain).
- **iv-v5ayb** go.mod replace directive breaks interlock/intermap in plugin cache. Quick fix: publish interbase/go as Go module.
- **iv-28vf9** Compaction recovery protocol for SessionStart hook.
- **iv-6376** Kernel E9: Autarch Phase 2 — Pollard + Gurgeh migration.

Note: iv-83du3 (Intercom message delivery reliability) shipped — outbox, LISTEN/NOTIFY, UDS, SQLite retirement all complete.

**P1: Measurement hardening chain.** The path to making the north-star metric canonical:
- iv-ho3 (in progress) → iv-296 (CXDB integration) → iv-g36hy (sprint execution recording) → iv-3ov (evidence pipeline wiring)

**P1: Hyperspace AGI adoption** (Sylveste-a42, epic). Three themes from Hyperspace research: close Skaffen's feedback loop (quality signals, compound phase), consolidate observability, enable autonomous plugin improvement via interlab mutation campaigns.

**P2: Adaptive routing (the flywheel).**
- **iv-5ztam** Interspect adaptive routing epic — evidence-driven agent selection. 10+ subtasks including counterfactual shadow evaluation, rate limiter, meta-learning loop.
- **iv-jgdct** Apply complexity-aware routing across all subagents. B2 infrastructure is fully built but has zero production callers — needs signal collection + injection at dispatch points (flux-drive, quality-gates). Staged rollout plan: shadow first, enforce later.
- **Sylveste-g4ja** Interspect-interrank wiring. Override consumption (Gap 1) shipped — lib-routing.sh now reads `.claude/routing-overrides.json`. Gaps 2-5 (interrank at decision time, calibration validation, routing decision feedback, override TTL) remain open.
- **Sylveste-g3a** Interspect calibration pipeline — fix broken verdict recording in quality-gates, upgrade calibration schema to v2 with source weighting and phase awareness.

**Recently completed (since last update):**
- **iv-awny7** Intercom Rust/Postgres cutover — ALL 6 SUBTASKS CLOSED. Group registration, scheduled tasks, SQLite removal, command plane unification, Node scaffolding removal, architecture docs. Former P0 epic, done.
- **iv-iq14t** Intent contract hardening — quality gate follow-ups (closed)
- **iv-godia** Routing decision capture as replayable kernel facts (closed)
- **iv-fo0rx** Canonical landed-change entity and north-star denominator (closed)
- **iv-30zy3** Durable session-bead-run attribution ledger in interstat (closed)
- **iv-544dn** Interspect event validity and outcome attribution research (closed)
- **iv-ojik9** Apps → OS → Kernel intent contract research (closed)
- **Sylveste-g4ja** Override consumption (Gap 1) — lib-routing.sh reads interspect overrides (closed)
- **Sylveste-pgl** Context monitor hook — inject context % warnings (closed)
- **iv-83du3** Intercom message delivery reliability — outbox, LISTEN/NOTIFY, UDS IPC, SQLite retirement (closed)
- **iv-craui** interkasten self-referential FK fix (closed)
- **iv-q8ge7** BeadID/SessionID validation before subprocess arg passing (closed)
- **interlab v0.4.0** Mutation store with SQLite-backed provenance tracking, 3 new MCP tools (mutation_record, mutation_query, mutation_genealogy), /autoresearch integration, interflux self-review pilot campaign
- **interlab v0.4.1** Multi-plugin quality scanner — scan all interverse plugins by PQS, generate campaign specs for /autoresearch-multi
- **interlab v0.4.2** Delta sharing via interlock — broadcast mutations and aggregate results so parallel sessions discover and build on each other's approaches

---

## Next — Strategic Themes (P2)

5 themes defining the medium-term direction. Full item inventory: [backlog.md](backlog.md).

1. **Skaffen Sovereign Agent** — Go-native coding agent with OODARC loop, masaq TUI, MCP client, intercore bridge, model routing. The second runtime alongside Clavain. Brainstorms and plans cover v0.1 completion, agent loop separation, quality signals (cross-session compound learning), scoped sessions, and competitive feature parity. See [Skaffen brainstorms](brainstorms/) from 2026-03-10 through 2026-03-14.

2. **Adaptive Routing (Track B2→B3)** — Complexity-aware routing activation (B2 infrastructure exists, callers needed), interspect calibration pipeline fixes, evidence-driven agent selection. The learning loop that makes the system cheaper and better over time.

3. **Autonomous Improvement Loop** — interlab mutation store (shipped), meta-improvement campaigns (interflux self-review pilot planned), intermix cross-repo matrix evaluation harness (planned, Sylveste-ome7), multi-plugin quality scanning (shipped). The infrastructure for agents improving themselves.

4. **Measurement Hardening** — Make the north-star metric canonical. The measurement chain unblocks the evidence pipeline that adaptive routing needs.

5. **Developer Experience & Tooling** — Intermap code mapping, interlock coordination, Autarch TUI migration, plugin ecosystem maturity, masaq component library refinements (breadcrumb, viewport, markdown improvements in progress).

---

## Later — Horizon (P3)

Longer-term directions, not yet scoped into specific items. Full inventory: [backlog.md](backlog.md).

- **Kernel library bindings** — Native client bindings for intercore (blocked by intent router)
- **Continuous dispatch** — Daemon mode for always-on agent orchestration
- **Workspace isolation** — Git worktree per task for parallel safe execution
- **Runtime budget enforcement** — Real-time token budget checks mid-execution
- **Intercom Go rewrite** — Port Rust daemon to Go + Skaffen integration (Sylveste-mvy)
- **Mycroft fleet orchestrator** — Multi-agent fleet coordination (brainstorm complete)
- **Evaluation infrastructure** — intermix harness (planned), model-capability sensitivity benchmarks, verifier context patterns
- **Exploration-exploitation strategy** — Skaffen Orient phase (Sylveste-e0t)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads (context) |
|--------|----------|---------|--------|---------|----------------------|
| agent-rig | core/agent-rig | 0.1.0 | early | no | n/a |
| autarch | apps/autarch | 0.1.0 | active | yes | n/a |
| clavain | os/clavain | 0.6.236 | active | yes | n/a |
| interblog | apps/interblog | 0.1.3 | early | no | n/a |
| interband | core/interband | — | planned | no | n/a |
| interbench | core/interbench | — | planned | no | n/a |
| intercache | interverse/intercache | 0.2.0 | early | no | n/a |
| interchart | interverse/interchart | 0.1.8 | early | no | n/a |
| intercheck | interverse/intercheck | 0.2.2 | active | yes | 4 |
| intercom | apps/intercom | 1.1.0 | active | shipped | n/a |
| intercore | core/intercore | — | active | yes | n/a |
| intercraft | interverse/intercraft | 0.1.2 | active | yes | 4 |
| interdeep | interverse/interdeep | 0.1.6 | early | no | n/a |
| interdev | interverse/interdev | 0.2.0 | active | yes | 4 |
| interdoc | interverse/interdoc | 5.2.1 | active | yes | 4 |
| interfer | interverse/interfer | 0.1.0 | early | no | n/a |
| interfluence | interverse/interfluence | 0.2.10 | active | yes | 4 |
| interflux | interverse/interflux | 0.2.52 | active | yes | n/a |
| interform | interverse/interform | 0.1.0 | active | yes | 4 |
| interhelm | interverse/interhelm | 0.2.0 | active | yes | n/a |
| interject | interverse/interject | 0.1.14 | active | yes | 4 |
| interkasten | interverse/interkasten | 0.4.25 | active | no | n/a |
| interknow | interverse/interknow | 0.1.5 | early | no | n/a |
| interlab | interverse/interlab | 0.4.6 | active | yes | n/a |
| interlearn | interverse/interlearn | 0.1.0 | active | yes | 8 |
| interleave | interverse/interleave | 0.1.2 | early | no | n/a |
| interlens | interverse/interlens | 2.2.4 | active | yes | 4 |
| interline | interverse/interline | 0.2.13 | active | yes | 4 |
| interlock | interverse/interlock | 0.2.10 | active | yes | n/a |
| interlore | interverse/interlore | 0.1.0 | early | no | n/a |
| intermap | interverse/intermap | 0.1.6 | active | yes | 7 |
| intermem | interverse/intermem | 0.2.4 | active | yes | n/a |
| intermix | interverse/intermix | 0.1.11 | active | no | n/a |
| intermonk | interverse/intermonk | 0.1.1 | early | no | n/a |
| intermute | core/intermute | — | active | yes | n/a |
| intermux | interverse/intermux | 0.1.5 | active | yes | 4 |
| intername | interverse/intername | 0.1.2 | early | no | n/a |
| internext | interverse/internext | 0.1.5 | active | yes | 4 |
| interpath | interverse/interpath | 0.3.2 | active | yes | 4 |
| interpeer | interverse/interpeer | 0.1.0 | early | no | n/a |
| interphase | interverse/interphase | 0.3.17 | active | yes | 4 |
| interplug | interverse/interplug | 0.1.5 | early | no | n/a |
| interpub | interverse/interpub | 0.1.8 | active | yes | 4 |
| interpulse | interverse/interpulse | 0.1.5 | early | no | n/a |
| interrank | interverse/interrank | 0.3.0 | active | no | n/a |
| interscribe | interverse/interscribe | 0.1.1 | early | no | n/a |
| intersearch | interverse/intersearch | 0.2.1 | active | yes | 4 |
| ~~intersense~~ | ~~interverse/intersense~~ | — | archived | — | — |
| intership | interverse/intership | 0.3.1 | early | no | n/a |
| intersight | interverse/intersight | 0.1.5 | early | no | n/a |
| interskill | interverse/interskill | 0.1.3 | early | no | n/a |
| interslack | interverse/interslack | 0.1.0 | active | yes | 4 |
| interspect | interverse/interspect | 0.1.18 | active | [vision](./interspect-vision.md) | n/a |
| interstat | interverse/interstat | 0.2.27 | active | yes | 4 |
| intersynth | interverse/intersynth | 0.1.9 | early | no | n/a |
| intertest | interverse/intertest | 0.1.2 | early | no | n/a |
| intertrace | interverse/intertrace | 0.1.2 | early | no | n/a |
| intertrack | interverse/intertrack | 0.1.4 | active | yes | n/a |
| intertree | interverse/intertree | 0.1.2 | early | no | n/a |
| intertrust | interverse/intertrust | 0.1.3 | early | no | n/a |
| interverse | root | — | active | yes | n/a |
| interwatch | interverse/interwatch | 0.3.3 | active | yes | 5 |
| marketplace | core/marketplace | — | active | yes | n/a |
| skaffen | os/skaffen | — | active | yes | n/a |
| tldr-swinton | interverse/tldr-swinton | 0.7.17 | active | yes | n/a |
| tool-time | interverse/tool-time | 0.3.10 | active | yes | n/a |
| tuivision | interverse/tuivision | 0.2.0 | active | yes | 4 |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Keeping Current

```
# Regenerate this roadmap JSON from current repo state
scripts/sync-roadmap-json.sh docs/roadmap.json

# Regenerate via interpath command flow (Claude Code)
/interpath:roadmap    (from Interverse root)

# Propagate items to subrepo roadmaps
/interpath:propagate  (from Interverse root)
```

---

**Moved to separate files:** Module highlights → [sylveste-reference.md](sylveste-reference.md). Research agenda, cross-module dependencies, modules without roadmaps → [backlog.md](backlog.md).
