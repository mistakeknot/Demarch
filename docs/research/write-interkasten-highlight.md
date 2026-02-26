# interkasten Module Highlight Analysis

**Module:** interkasten (interverse/interkasten)
**Version:** 0.4.4
**Open Beads:** 12
**Created:** 2026-02-23

---

## Executive Summary

Interkasten (v0.4.4) is a mature bidirectional Notion sync plugin for Claude Code that bridges project documentation and Notion workspaces. It exposes 21 MCP tools covering project CRUD, bidirectional sync with three-way merge conflict resolution, file scanning, signal gathering, and beads issue tracking. The architecture is agent-native: tools return raw signals and expose CRUD operations, while Claude Code skills handle intelligence and decision-making. The system uses a WAL protocol for crash recovery, circuit breakers for API resilience, and SHA-256 content hashing for change detection.

---

## Feature Completeness (v0.4.0 → v0.4.4)

### Core Capabilities ✓
- **Bidirectional sync:** Push (local → Notion) and pull (Notion → local) with 60-second polling
- **Conflict resolution:** Three-way merge via `node-diff3` with configurable strategies (three-way-merge default, local-wins fallback, notion-wins, conflict-file)
- **Project hierarchy:** `.beads` markers define parentage; parent-child stored as FK; `.git` is detection-only
- **Notion integration:** 21 MCP tools, @notionhq/client v5, data source model, soft-delete with 30-day retention
- **Beads issue sync:** Diff-based snapshot tracking; syncs beads state to per-project Notion Issues database
- **Crash recovery:** WAL protocol (pending → target_written → committed → delete) survives mid-sync failures
- **Resilience:** Circuit breaker pattern (closed → open after 10 failures → half-open → closed)
- **Key docs:** Auto-refresh key doc URL columns in Notion (Product, Tool, Inactive tiers)
- **Skills:** layout (interactive discovery), onboard (classification + sync), doctor (diagnostics)
- **Testing:** 130 tests (121 unit, 9 integration); 100% coverage of sync engine, WAL, merge, entity CRUD

### Recent Fixes & Polish (0.4.0 → 0.4.4)
- Notion API upgrade: v2 → v5 (data source model, improved type safety)
- Process memory detection: `.rss()` function call (not property)
- Notion-to-md version compat: returns `{ parent: string }` (was direct string in older versions)
- Drizzle ORM nullable column: `lt()` needs `!` assertion for proper type inference
- Bootstrap robustness: `start-mcp.sh` detects missing `node_modules` and runs `npm install` automatically

### Integration Points
- **Beads:** Bidirectional issue sync via `bd` CLI (execFileSync, no shell injection)
- **Zod validation:** Config schema loading from `~/.interkasten/config.yaml`
- **Chokidar:** Filesystem watching for local change detection
- **p-queue:** Concurrency-limited sync operation queue with dedup (by side + entity key)
- **Martian:** Markdown → Notion block translation
- **better-sqlite3:** Native SQLite adapter (can't be bundled, bootstrap approach used)

---

## Architecture Highlights

### Agent-Native Design
Rather than embed decision logic in the MCP server, interkasten exposes primitives and intelligence moves to Claude Code skills:

1. **gather_signals** returns raw filesystem metrics (LOC, commit count, doc count, last commit days)
2. **scan_files** lists files; agent + user pick what to sync
3. **set_project_tags** accepts any strings (no hardcoded vocabulary)
4. **set_project_parent** places in hierarchy; agent orchestrates cascades
5. Skills layer reads signals and makes classification, tagging, and sync decisions

This separates concerns: MCP = data + CRUD, skills = reasoning.

### Sync Engine
```
Local Changes → chokidar → queue (dedup) → translate → Notion API write
Notion Changes → NotionPoller (60s) → hash check → translate → local file write
Both Changed → node-diff3 merge (base + local + notion) → conflict file if needed
```

Content hashing (SHA-256 of normalized markdown) detects no-ops and speeds polling. Roundtrip base: after push, pull content back and store as base (prevents phantom conflicts).

### Conflict Resolution
Three-way merge with `node-diff3`:
- **Best case:** automatic merge succeeds → sync completes
- **Conflict case:** generates diff-match-patch conflict file → `interkasten_conflicts` tool lists for agent review
- **Strategies:** three-way-merge (intelligent, fails gracefully) → local-wins (pragmatic fallback) → notion-wins (remote-trusting) → conflict-file (human review)

### WAL Protocol (Crash Recovery)
Every sync operation records: `pending` → `target_written` (side effect done) → `committed` (logged) → delete entry.

If process crashes mid-sync:
1. WAL entries survive on disk
2. On restart, replay pending operations
3. Half-completed operations roll back via `rolled_back` state

Applies to all write paths: clean syncs, error recovery, conflict resolution.

### Database Schema (5 Tables)
- **entity_map:** Filesystem ↔ Notion mappings, hierarchy (parent_id FK), tags (JSON), conflict tracking, soft-delete
- **base_content:** Content-addressed store for three-way merge bases (SHA-256 addresses)
- **sync_log:** Append-only operation log (push/pull/merge/conflict/error + direction)
- **sync_wal:** Write-ahead log for crash recovery (state machine)
- **beads_snapshot:** Last-known beads state for diff-based issue sync

### Security & Validation
- Path validation on all pull operations: `resolve(path) + startsWith(projectDir + "/")`
- Notion titles with path traversal (`..`, absolute paths) rejected and logged
- No shell injection in beads sync: `execFileSync` (not `execSync`)
- Soft-delete retention: 30 days (aligned with Notion trash)

---

## Open Beads (12) & Known Issues

Based on AGENTS.md "Status (as of v0.4.0)":
- **35 beads closed** (59 total reduced)
- 35 were flux-drive findings (architectural discoveries via distributed cognition)
- Primary work streams completed: scaffold (Phase 0), foundation (Phase 1), push sync (Phase 2), bidirectional sync (Phase 3)

**Next candidates (deferred to v0.5.x):**
1. Webhook receiver (P2) — real-time Notion change detection (vs. 60s polling)
2. Interphase context integration (P2) — phase tracking in workflow automation
3. Soft-delete GC tuning (P3) — configurable retention windows
4. Conflict strategy auto-selection (P3) — learn from user resolutions
5. Multi-workspace support (P3) — handle multiple Notion tokens
6. Beads snapshot incremental updates (P3) — more efficient for large issue sets
7. Markdown dialect preservation (P3) — front matter, code fence languages
8. Linked references summary cards (T2 enhancement) — richer connection visibility
9. Performance profiling (P3) — memory / sync duration benchmarks
10. Integration tests expansion (P3) — cover more edge cases
11. Documentation polish (P3) — user guide for conflict resolution workflow
12. CLI tool for offline mode (P3) — fallback when Notion unreachable

---

## Quality & Testing

### Test Coverage
- **121 unit tests:** Config, store (entity CRUD, WAL state), sync (translator, merge, beads-sync, triage, hierarchy, poller, engine, linked-refs, soft-delete, key-docs)
- **9 integration tests:** End-to-end Notion API (skipped without `INTERKASTEN_TEST_TOKEN`)
- Test structure mirrors source organization for maintainability

### Known Gotchas (Embedded in Code)
1. **Node.js API:** `process.memoryUsage.rss()` is a function, not property (newer Node versions)
2. **Notion-to-md:** Returns `{ parent: string }` in v3+, was direct string in v2
3. **Zod:** MCP SDK peer dep sufficient; no separate install needed
4. **Drizzle ORM:** `lt()` on nullable columns requires `!` assertion
5. **Better-sqlite3:** Native addon, can't be bundled with esbuild (bootstrap approach used)
6. **Plugin reload:** Session restart required after plugin updates (hooks/skills load at session start)

### Operational Robustness
- Circuit breaker: 10 consecutive failures → open, half-open probe after cooldown
- Graceful degradation: If Notion unreachable, local changes queue and retry
- WAL replay: Automatic on daemon restart, no manual recovery needed
- Soft-delete GC: Entries older than 30 days eligible for cleanup (manual via admin tools)

---

## Skills & Commands

| Skill | Description |
|-------|-------------|
| **layout** | `/interkasten:layout` — Interactive project discovery, hierarchy visualization, and registration |
| **onboard** | `/interkasten:onboard` — Classification (Product/Tool/Inactive), doc generation, drift baselines, initial sync |
| **doctor** | `/interkasten:interkasten-doctor` — Self-diagnosis: config file, Notion token, MCP server, database schema, sync health |

Hooks:
- **SessionStart:** Brief status (project count, pending WAL, unresolved conflicts)
- **Stop:** Warn if pending sync operations exist

---

## Roadmap Positioning

### Within Interverse
Interkasten is a **documentation infrastructure plugin** (tier 1 platform):
- Sits alongside **interdoc** (AGENTS.md generator) and **interwatch** (doc freshness)
- Powers **interphase** workflow automation (doc phases, gates)
- Feeds **interlearn** (institutional knowledge indexing)
- Depends on **intercore** + **intermute** for coordinated multi-agent workflows

### Maturity Assessment
- **v0.4.4 = Production-Ready MVP** with full bidirectional sync, crash recovery, and conflict resolution
- **Completeness:** Core use case (doc sync + hierarchy) is 100% implemented
- **Quality:** 130 tests, 5-table schema, WAL protocol, circuit breaker, soft-delete
- **Integration:** 21 MCP tools, 3 skills, 2 hooks, beads issue sync, Notion v5 data source model
- **Next Phase:** Webhooks (real-time), workflow automation (interphase), performance profiling

### Competitive Advantages
1. **Three-way merge** (not just last-write-wins) — preserves intentional edits from both sides
2. **Agent-native design** — skills layer owns classification, no hardcoded logic in daemon
3. **Crash recovery via WAL** — survives mid-sync failures without manual intervention
4. **Soft-delete retention** — aligns with Notion trash, prevents accidental data loss
5. **Beads integration** — issues sync bidirectionally, not just docs
6. **Signal gathering** — exposes raw metrics (LOC, commits, doc count) for agent reasoning

---

## Deployment & Operations

### Bootstrap & Installation
```bash
/plugin install interkasten
# → hooks.json wires Setup hook
# → setup.sh runs: npm install && npm run build
# → start-mcp.sh invoked on session start
```

### Environment
```bash
export INTERKASTEN_NOTION_TOKEN="ntn_..."  # Required for Notion sync
export INTERKASTEN_TEST_TOKEN="ntn_..."    # For integration tests (can be same)
```

### Configuration
```yaml
# ~/.interkasten/config.yaml
projects_dir: /root/projects
sync:
  poll_interval: 60  # seconds
  conflict_strategy: three-way-merge
project_detection:
  markers: [".beads", ".git"]
  max_depth: 4
```

### Health Monitoring
- `interkasten_health` → uptime, SQLite status, Notion connectivity, circuit breaker state, WAL entries
- `interkasten_sync_status` → pending ops, error counts, circuit breaker open/closed
- `interkasten_sync_log` → query recent operations by type (push/pull/merge/conflict/error) or time window

---

## Summary for Roadmap

**interkasten (v0.4.4)** is a mature bidirectional Notion sync plugin providing 21 MCP tools, three-way merge conflict resolution, crash recovery via WAL protocol, and agent-native architecture where skills own decision logic. It serves as the documentation infrastructure backbone for the Interverse ecosystem, integrating with beads issue tracking and supporting hierarchical project organization with tagging. With 130 tests, full async sync, circuit breaker resilience, and soft-delete safety, it's production-ready for multi-project knowledge management workflows.

---

## Key Metrics for Roadmap Card

- **Stability:** v0.4.4 stable, all Phase 0-3 complete
- **Test coverage:** 130 tests (121 unit, 9 integration)
- **MCP tools:** 21 (infrastructure, project, hierarchy, sync, legacy)
- **Skills:** 3 (layout, onboard, doctor)
- **Hooks:** 2 (SessionStart status, Stop warning)
- **Database tables:** 5 (entity_map, base_content, sync_log, sync_wal, beads_snapshot)
- **Sync strategies:** 4 (three-way-merge, local-wins, notion-wins, conflict-file)
- **Open beads:** 12 (webhook receiver, interphase integration, performance profiling, etc.)
