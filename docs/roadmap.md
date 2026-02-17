# Interverse Roadmap

**Modules:** 30 | **Open beads (root tracker):** 348 | **Blocked (root tracker):** 27 | **Last updated:** 2026-02-17
**Structure:** [`CLAUDE.md`](../CLAUDE.md)
**Machine output:** [`docs/roadmap.json`](roadmap.json)

---

## Ecosystem Snapshot

| Module | Location | Version | Status | Roadmap | Open Beads (context) |
|--------|----------|---------|--------|---------|----------------------|
| clavain | hub/clavain | 0.6.30 | active | yes | 0 (372 closed, local archive) |
| intercheck | plugins/intercheck | 0.1.2 | active | yes | n/a (tracked in root .beads) |
| intercraft | plugins/intercraft | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| interdev | plugins/interdev | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| interdoc | plugins/interdoc | 5.1.1 | active | yes | 0 (1 closed, local archive) |
| interfluence | plugins/interfluence | 0.1.3 | active | yes | 0 (0 closed, local archive) |
| interflux | plugins/interflux | 0.2.13 | active | yes | n/a (tracked in root .beads) |
| interform | plugins/interform | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| interject | plugins/interject | 0.1.4 | active | yes | n/a (tracked in root .beads) |
| interkasten | plugins/interkasten | 0.4.1 | active | yes | 0 (59 closed, local archive) |
| interlens | plugins/interlens | 2.2.2 | active | yes | n/a (tracked in root .beads) |
| interline | plugins/interline | 0.2.4 | active | yes | n/a (tracked in root .beads) |
| interlock | plugins/interlock | 0.2.0 | active | yes | n/a (tracked in root .beads) |
| intermap | plugins/intermap | 0.1.0 | early | no | n/a |
| intermux | plugins/intermux | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| internext | plugins/internext | 0.1.2 | active | yes | n/a (tracked in root .beads) |
| interpath | plugins/interpath | 0.2.0 | active | yes | n/a (tracked in root .beads) |
| interphase | plugins/interphase | 0.3.2 | active | yes | n/a (tracked in root .beads) |
| interpub | plugins/interpub | 0.1.2 | active | yes | n/a (tracked in root .beads) |
| intersearch | plugins/intersearch | 0.1.1 | active | yes | n/a (tracked in root .beads) |
| interserve | plugins/interserve | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| interslack | plugins/interslack | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| interstat | plugins/interstat | 0.1.0 | active | yes | n/a (tracked in root .beads) |
| intersynth | plugins/intersynth | 0.1.0 | early | no | n/a |
| interwatch | plugins/interwatch | 0.1.2 | active | yes | n/a (tracked in root .beads) |
| tldr-swinton | plugins/tldr-swinton | 0.7.12 | active | yes | 7 open, 6 blocked (117 closed, local archive) |
| tool-time | plugins/tool-time | 0.3.2 | active | yes | 0 (4 closed, local archive) |
| tuivision | plugins/tuivision | 0.1.4 | active | yes | n/a (tracked in root .beads) |
| intermute | services/intermute | — | active | yes | 0 (29 closed, local archive) |
| interverse | root | — | active | yes | 348 open (27 blocked, root tracker) |

**Legend:** active = recent commits or active tracker items; early = manifest exists but roadmap maturity is limited. `n/a` means there is no module-local `.beads` database.

---

## Roadmap

### Now (P0-P1)

- [interverse] **iv-hoqj** Interband — sideband protocol library for cross-plugin file contracts
- [interverse] **iv-0681** Crash recovery + error aggregation for multi-agent sessions
- [interspect] **iv-vrc4** Overlay system (Type 1) (unblocks iv-ynbh)
- [interspect] **iv-ukct** `/interspect:revert` command (its prerequisites iv-cylo and iv-jo3i are complete)
- [interstat] **iv-dyyy** F0: plugin scaffold + SQLite schema

**Recently completed (removed from active queue):** iv-7o7n, iv-j7uy, iv-8m38, iv-cylo, iv-d72t, iv-zrmk, iv-5m8j, iv-tifk, iv-ked1, iv-hyza, iv-kmyj, iv-1zh2, iv-1zh2.1 through iv-1zh2.7.

### Next (P2)

**Token Efficiency & Cost Optimization**
- [interflux] **iv-qjwz** AgentDropout — dynamic redundancy elimination (blocked by iv-ynbh)
- [interflux] **iv-905u** Intermediate result sharing between parallel agents
- [interverse] **iv-xuec** Security threat model for token optimization techniques
- [interverse] **iv-dthn** Research: inter-layer feedback loops and optimization thresholds

**Interstat Benchmarking Pipeline**
- [interstat] **iv-qi8j** F1: PostToolUse:Task hook — real-time event capture (blocked by iv-dyyy)
- [interstat] **iv-lgfi** F2: Conversation JSONL parser — token backfill (blocked by iv-dyyy)
- [interstat] **iv-dkg8** F3: Report — analysis queries + decision gate (blocked by iv-dyyy, iv-lgfi)
- [interstat] **iv-bazo** F4: Status — collection progress (blocked by iv-dyyy, iv-lgfi)

**Interspect Routing Overrides**
- [interspect] **iv-r6mf** F1: `routing-overrides.json` schema + flux-drive reader
- [interspect] **iv-8fgu** F2: Routing-eligible pattern detection + propose flow (blocked by iv-r6mf)
- [interspect] **iv-gkj9** F3: Apply override + canary + git commit (blocked by iv-8fgu)
- [interspect] **iv-2o6c** F4: Status display + revert for routing overrides (blocked by iv-gkj9)
- [interspect] **iv-6liz** F5: Manual routing override support (blocked by iv-r6mf)

**Interlock Negotiation**
- [interlock] **iv-1aug** F1: Release Response Protocol — `release_ack` / `release_defer` (Phase 4a prerequisite is complete)
- [interlock] **iv-5ijt** F3: Structured `negotiate_release` MCP tool (blocked by iv-1aug)
- [interlock] **iv-6u3s** F4: Sprint Scan release visibility (blocked by iv-1aug)
- [interlock] **iv-2jtj** F5: Escalation timeout for unresponsive agents (blocked by iv-5ijt)

**Cross-Module Integration**
- [interverse] **iv-z1a0** Cross-module integration opportunity program (parent tracker)
- [interverse] **iv-z1a1** Inter-module event bus + event contracts (blocked by iv-z1a0)
- [interverse] **iv-z1a2** Interline as unified operations HUD (blocked by iv-z1a0)
- [interverse] **iv-z1a4** Interkasten context into discovery and sprint intake (blocked by iv-z1a0)
- [interverse] **iv-ev4o** Agent capability discovery via intermute registration
- [interverse] **iv-umvq** Health aggregation service (interstatus) for ecosystem-wide health visibility

**Shared Libraries**
- [interverse] **iv-lwsf** Shared HTTP client library (interhttp) for Go + bash
- [interverse] **iv-tkc6** Shared bash hook library (interlace) for clavain/interphase/interlock
- [interverse] **iv-jmua** Shared SQLite library (intersqlite) for six modules

**Orchestration & Dispatch**
- [clavain] **iv-zyym** Evaluate Claude Hub for event-driven GitHub agent dispatch
- [clavain] **iv-wrae** Evaluate Container Use (Dagger) for sandboxed agent dispatch
- [clavain] **iv-quk4** Hierarchical dispatch — meta-agent for N-agent fan-out
- [interverse] **iv-p4qq** Smart semantic caching across sessions (intercache)
- [interverse] **iv-friz** CI/CD integration bridge — GitHub Actions templates

**Research Experiments (P2 exploratory)**
- [interflux] **iv-qznx** Multi-framework interoperability benchmark and scoring harness
- [intermute] **iv-jc4j** Heterogeneous collaboration and routing experiments inspired by SC-MAS/Dr. MAS
- [interflux] **iv-wz3j** Role-aware latent memory safety and lifecycle experiments (blocked by iv-jc4j)
- [interstat] **iv-v81k** Repository-aware benchmark expansion for SWE coding tasks (blocked by iv-qznx)

### Later (P3)

- [interspect] **iv-ynbh** Agent trust and reputation scoring via interspect (blocked by iv-vrc4)
- [interverse] **iv-6i37** Blueprint distillation: channel optimization for sprint intake
- [interwatch] **iv-wrtg** Framework and benchmark freshness automation pipeline

---

## Module Highlights

### clavain (hub/clavain)
v0.6.30. Hub orchestrator for brainstorm-to-ship workflows. Current focus: runtime resilience, analytics-driven routing controls, and dispatch quality.

### interflux (plugins/interflux)
v0.2.13. Multi-agent review and research engine. Current focus: token efficiency, stronger review contracts, and operational reliability.

### interkasten (plugins/interkasten)
v0.4.1. Bidirectional Notion sync and documentation automation. Current focus: linked references, pull-sync reliability, and tracker sync refinement.

### interlock (plugins/interlock)
v0.2.0. Multi-agent file coordination and reservation control. Phase 4a (`iv-d72t`) is complete; next work is release negotiation and escalation controls.

### tldr-swinton (plugins/tldr-swinton)
v0.7.12. Token-efficient code context and semantic retrieval. Current focus is MCP hardening and eval integration.

### tool-time (plugins/tool-time)
v0.3.2. Tool usage analytics with public observability surface at `tool-time.org`.

### intermute (services/intermute)
Active MVP-to-RC maturity. Core APIs, WebSocket delivery, and reservation primitives are operational. Current focus: hardening and diagnostics.

---

## Research Agenda

- **Flux-Drive Document Slicing** — Core rollout complete (`iv-7o7n`, `iv-j7uy`, `iv-zrmk`, `iv-5m8j`, `iv-tifk` closed). Follow-on optimization work remains.
- **Interstat Token Benchmarking** — Ongoing implementation of evidence capture and analysis pipeline (`iv-dyyy`, `iv-qi8j`, `iv-lgfi`, `iv-dkg8`, `iv-bazo`).
- **Sprint Resilience Phase 2** — Autonomy layer for sprint workflow recovery after context exhaustion.
- **Interspect Routing Overrides** — Detect patterns, propose overrides, canary-test, and revert safely.
- **Interlock Reservation Negotiation** — Release negotiation protocol and escalation model after Phase 4a completion.
- **Interlens Flux Agents** — Cognitive augmentation lenses as flux-drive review agents.
- **Token-Efficient Skill Loading** — Foundational brainstorm series closed; follow-on work should be tracked with new implementation beads.
- **Clavain Boundary Restructure** — Continuing extraction of capabilities into companion plugins.
- **Cross-Module Integration Sweep** — Systematic identification of shared patterns across 22+ modules.
- **Interject Integration Sweep** — Ambient discovery engine integration with current research workflows.
- **Intercheck Code Quality Guards** — Syntax validation, formatting safeguards, and session health monitoring.
- **Open Source + Research Watch (2026-02-17)** — Working watchlist for framework/paper deltas. Verify versions at execution time before making roadmap commitments.

---

## Cross-Module Dependencies

Major dependency chains spanning multiple modules:

- **Document slicing chain** (completed): iv-7o7n → iv-j7uy → iv-zrmk → iv-5m8j → iv-tifk are closed.
- **Interlock negotiation chain** (active): iv-1aug → iv-5ijt → iv-2jtj, with iv-6u3s in parallel once iv-1aug lands. Phase 4a prerequisite iv-d72t is closed.
- **Interspect routing chain** (active): iv-r6mf → iv-8fgu → iv-gkj9 → iv-2o6c, plus iv-6liz after iv-r6mf.
- **Trust/dropout chain** (active): iv-vrc4 → iv-ynbh → iv-qjwz.
- **Integration program** (active): iv-z1a0 blocks iv-z1a1, iv-z1a2, and iv-z1a4.

---

## Modules Without Roadmaps

- `plugins/intermap`
- `plugins/intersynth`

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
