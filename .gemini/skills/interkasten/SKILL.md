---
name: interkasten
description: "Living bridge between your projects folder and Notion — bidirectional sync with adaptive AI documentation and pagent workflow automation"
---
# Gemini Skill: interkasten

You have activated the interkasten capability.

## Base Instructions
# interkasten — Agent Instructions

Claude Code plugin + MCP server for bidirectional Notion sync with adaptive AI documentation.

**Version:** 0.4.0
**Repository:** `github.com/mistakeknot/interkasten`
**Monorepo location:** `plugins/interkasten/` in Interverse

## Quick Start

```bash
cd server && npm install && npm run build
npm test          # 130 tests (121 unit + 9 integration)
node dist/index.js  # MCP server on stdio
```

Integration tests require `INTERKASTEN_TEST_TOKEN` env var (Notion API token for test workspace).

## Architecture

```
interkasten/
├── .claude-plugin/plugin.json  # Claude Code plugin manifest (v0.4.0)
├── server/
│   ├── package.json            # Node >=20, ESM, vitest
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts            # MCP entry point, startup sequence
│       ├── config/
│       │   ├── schema.ts       # Zod config schema
│       │   ├── defaults.ts     # Default config values
│       │   └── loader.ts       # YAML config loader (~/.interkasten/config.yaml)
│       ├── store/
│       │   ├── db.ts           # SQLite via better-sqlite3 + drizzle-orm
│       │   ├── schema.ts       # 5 tables: entity_map, base_content, sync_log, sync_wal, beads_snapshot
│       │   ├── entities.ts     # Entity CRUD, conflict tracking, soft-delete
│       │   ├── wal.ts          # WAL state machine: pending → target_written → committed → delete
│       │   └── sync-log.ts     # Append-only operation log
│       ├── sync/
│       │   ├── engine.ts       # Core sync engine (push, pull, merge orchestration)
│       │   ├── watcher.ts      # Chokidar file watcher for local changes
│       │   ├── queue.ts        # Sync operation queue with dedup
│       │   ├── translator.ts   # Markdown ↔ Notion block conversion
│       │   ├── notion-client.ts # Notion API wrapper with circuit breaker
│       │   ├── notion-poller.ts # 60s polling for Notion-side changes
│       │   ├── merge.ts        # Three-way merge via node-diff3
│       │   ├── beads-sync.ts   # Beads ↔ Notion issue sync (diff-based, snapshot tracking)
│       │   ├── linked-refs.ts  # T2 summary cards for linked references
│       │   ├── entity-map.ts   # Entity registration, lookup, hierarchy helpers
│       │   ├── key-docs.ts     # Key doc URL columns in Notion
│       │   └── triage.ts       # Legacy tier classification (prefer gather_signals)
│       └── daemon/
│           ├── context.ts      # Shared DaemonContext (db, config, notion, engine)
│           └── tools/
│               ├── health.ts   # Liveness probe
│               ├── config.ts   # Config get/set
│               ├── version.ts  # Version info
│               ├── init.ts     # Setup wizard + project discovery
│               ├── projects.ts # Project CRUD
│               ├── sync.ts     # Sync trigger + status + log
│               ├── issues.ts   # Beads ↔ Notion issue listing
│               ├── signals.ts  # Raw filesystem/git signals + file scanning
│               ├── hierarchy.ts # Scan preview, parent/tags CRUD, database properties
│               └── triage.ts   # Legacy tier tool
├── skills/
│   ├── layout/SKILL.md         # Interactive project discovery + hierarchy registration
│   ├── onboard/SKILL.md        # Classification, doc generation, drift baselines, sync
│   └── doctor/SKILL.md         # Self-diagnosis: config, token, MCP, database, sync health
├── commands/
│   ├── onboard.md              # /interkasten:onboard
│   └── doctor.md               # /interkasten:interkasten-doctor
├── hooks/
│   ├── hooks.json              # Hook registry (Setup, SessionStart, Stop)
│   ├── setup.sh                # Auto-build MCP server on install
│   ├── session-status.sh       # Print project count, pending WAL, conflicts
│   └── session-end-warn.sh     # Warn about pending sync operations
├── scripts/
│   └── start-mcp.sh            # Bootstrap: npm install if needed, then start
└── docs/
    ├── brainstorms/
    ├── plans/
    └── prds/
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `@modelcontextprotocol/sdk` | MCP server framework |
| `@notionhq/client` v5 | Notion API (data source model) |
| `@tryfabric/martian` | Markdown → Notion blocks |
| `notion-to-md` | Notion blocks → markdown |
| `better-sqlite3` | SQLite (native addon, can't bundle) |
| `drizzle-orm` | Type-safe ORM over SQLite |
| `node-diff3` | Three-way merge algorithm |
| `diff-match-patch-es` | Patch generation for conflict files |
| `chokidar` | Filesystem watching |
| `p-queue` | Concurrency-limited sync queue |
| `yaml` | Config file parsing |
| `zod` | Schema validation |

## Database Schema (5 tables)

### entity_map
Maps local filesystem entities to Notion page IDs. Each row = one synced entity.

| Column | Type | Description |
|--------|------|-------------|
| `local_path` | text, unique | Filesystem path |
| `notion_id` | text, unique | Notion page/database ID |
| `entity_type` | text | `project`, `doc`, `ref`, `issue` |
| `tier` | text | `T1` (full sync) or `T2` (summary card) |
| `doc_tier` | text | `Product`, `Tool`, `Inactive` (project-level triage) |
| `parent_id` | integer FK | Self-referential hierarchy (null = top-level) |
| `tags` | text | JSON array of tag strings |
| `last_local_hash` | text | SHA-256 of local content |
| `last_notion_hash` | text | SHA-256 of Notion content |
| `last_notion_ver` | text | Notion `last_edited_time` (polling fast-path) |
| `base_content_id` | integer FK | → base_content (merge ancestor) |
| `conflict_*` | various | Conflict tracking (detected_at, local/notion content IDs) |
| `deleted` / `deleted_at` | boolean/text | Soft-delete (30-day retention) |

### base_content
Content-addressed store for three-way merge base snapshots.

### sync_log
Append-only operation log. Operations: `push`, `pull`, `merge`, `conflict`, `error`. Directions: `local_to_notion`, `notion_to_local`.

### sync_wal
Write-ahead log for crash recovery. States: `pending` → `target_written` → `committed` → `rolled_back`.

### beads_snapshot
Snapshot of beads issue state for diff-based sync. Tracks last-known state to detect changes.

## MCP Tools (21 registered)

### Infrastructure (4 tools)
| Tool | Description |
|------|-------------|
| `interkasten_health` | Liveness probe: uptime, SQLite, Notion, circuit breaker, WAL |
| `interkasten_config_get` | Read config (full or by key path) |
| `interkasten_config_set` | Update config value |
| `interkasten_version` | Daemon + schema version |

### Project Management (7 tools)
| Tool | Description |
|------|-------------|
| `interkasten_init` | First-time setup: validate token, create/find database |
| `interkasten_list_projects` | List projects with hierarchy, tags, key doc status |
| `interkasten_get_project` | Project detail: docs, parent, children, tags |
| `interkasten_register_project` | Register project with agent-specified Notion properties |
| `interkasten_unregister_project` | Stop tracking (soft-delete, preserves Notion pages) |
| `interkasten_refresh_key_docs` | Update key doc URL columns in Notion |
| `interkasten_add_database_property` | Add property to Projects database (idempotent) |

### Hierarchy & Signals (5 tools)
| Tool | Description |
|------|-------------|
| `interkasten_scan_preview` | Non-destructive tree discovery with signals (writes nothing) |
| `interkasten_gather_signals` | Raw filesystem/git signals for a project |
| `interkasten_scan_files` | Scan project for files matching a pattern |
| `interkasten_set_project_parent` | Set/change project parent (with Notion relation) |
| `interkasten_set_project_tags` | Set tags (with Notion multi-select) |

### Sync Operations (5 tools)
| Tool | Description |
|------|-------------|
| `interkasten_sync` | Trigger sync: push, pull, or both directions |
| `interkasten_sync_status` | Pending ops, errors, circuit breaker state |
| `interkasten_sync_log` | Query sync history |
| `interkasten_conflicts` | List unresolved merge conflicts with content previews |
| `interkasten_list_issues` | List synced beads issues with Notion page IDs |

### Legacy (1 tool)
| Tool | Description |
|------|-------------|
| `interkasten_triage` | Hardcoded tier classification (prefer `gather_signals`) |

## Key Design Patterns

### Agent-Native Design
Tools expose raw signals and CRUD operations. Intelligence lives in Claude Code skills:
- **No hardcoded classification** — `gather_signals` returns LOC, commits, markers; agent proposes tiers
- **No hardcoded tag vocabulary** — `set_project_tags` accepts any strings
- **No cascade logic** — `unregister_project` handles one entity; agent orchestrates
- **No auto-file-selection** — `scan_files` lists files; agent + user pick what to sync

### Bidirectional Sync (v0.4.0)
- **Push**: local file change → chokidar detects → queue → translate to Notion blocks → API write
- **Pull**: NotionPoller (60s, configurable) → content hash check → translate to markdown → write local file
- **Merge**: when both sides changed since base, three-way merge via `node-diff3`
- **Conflict strategies**: `three-way-merge` (default), `local-wins`, `notion-wins`, `conflict-file`
- **Roundtrip normalization**: after push, pull-back content stored as base (prevents phantom conflicts)

### WAL Protocol (crash recovery)
Every sync operation follows: `pending` → `target_written` → `committed` → delete WAL entry. If process crashes mid-sync, WAL entries survive and are replayed on restart.

### Circuit Breaker
Notion API errors tracked; after N consecutive failures, circuit opens (stops API calls). Half-open after cooldown allows a probe request. Prevents cascading failures.

### Content Hashing
SHA-256 of normalized markdown. Used for change detection (skip no-op syncs) and base content dedup.

### Soft-Delete Safety
Unregistered entities marked `deleted=true` with 30-day retention before GC. Aligned with Notion's trash retention period.

### Beads Issue Sync
Diff-based: snapshot current beads state, compare against last-known state, sync deltas to Notion Issues database per project. Uses `execFileSync` (not `execSync`) to prevent shell injection.

### Hierarchy
- `.beads` is the hierarchy marker — nearest ancestor with `.beads` = parent
- `.git` is a project detection marker only (doesn't imply parentage)
- Symlinks deduplicated via `realpathSync()`
- Parent-child stored as `parent_id` FK in `entity_map`

### Path Validation (security)
All pull operations validate: `resolve(path) + startsWith(projectDir + "/")`. Notion page titles with path traversal sequences (`..`, absolute paths) are rejected and logged.

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| `layout` | `/interkasten:layout` | Interactive project discovery, hierarchy, and registration |
| `onboard` | `/interkasten:onboard` | Classification, doc generation, drift baselines, sync |
| `doctor` | `/interkasten:interkasten-doctor` | Self-diagnosis: config, token, MCP, database, sync health |

## Hooks

| Event | Script | Description |
|-------|--------|-------------|
| `Setup` | `setup.sh` | Auto-build MCP server (`npm install && npm run build`) on plugin install |
| `SessionStart` | `session-status.sh` | Print project count, pending WAL entries, unresolved conflicts |
| `Stop` | `session-end-warn.sh` | Warn if pending sync operations exist |

## Testing

```bash
cd server && npm test                    # 121 unit tests
INTERKASTEN_TEST_TOKEN=ntn_... npm test  # + 9 integration tests
```

Test structure mirrors source:
- `tests/config/` — config loader tests
- `tests/store/` — entity CRUD, WAL state machine tests
- `tests/sync/` — translator, merge, beads-sync, triage, hierarchy, poller, engine, linked-refs, soft-delete, key-docs
- `tests/integration/` — end-to-end Notion API tests (skipped without token)

## Configuration

`~/.interkasten/config.yaml` — key settings:

| Key | Default | Description |
|-----|---------|-------------|
| `projects_dir` | `/root/projects` | Root directory to scan for projects |
| `sync.poll_interval` | `60` | Notion polling interval (seconds) |
| `sync.conflict_strategy` | `three-way-merge` | Merge conflict fallback |
| `project_detection.markers` | `[".beads", ".git"]` | Files that indicate a project |
| `project_detection.max_depth` | `4` | Max scan depth |

## Environment

```bash
export INTERKASTEN_NOTION_TOKEN="ntn_..."  # Required for Notion sync
export INTERKASTEN_TEST_TOKEN="ntn_..."    # For integration tests (can be same token)
```

## Common Tasks

### Register a new project
```
1. interkasten_scan_preview → see discovered projects
2. interkasten_register_project → register with Notion
3. interkasten_set_project_parent → place in hierarchy
4. interkasten_set_project_tags → classify
5. interkasten_sync(direction: "push") → initial sync
```

### Debug sync issues
```
1. interkasten_health → check SQLite, Notion, circuit breaker
2. interkasten_sync_status → pending ops, errors
3. interkasten_sync_log → recent operations
4. interkasten_conflicts → unresolved merge conflicts
```

### Diagnose configuration
Run `/interkasten:interkasten-doctor` — checks config file, Notion token, MCP server connectivity, database schema, and sync health.

## Gotchas

- `process.memoryUsage.rss()` not `.rss` — it's a function in newer Node
- `notion-to-md` returns `{ parent: string }` in newer versions, not just string
- Zod from MCP SDK peer dep is sufficient — no need for separate install
- `drizzle-orm` `lt()` on nullable column needs `!` assertion
- `better-sqlite3` is a native addon — can't be bundled with esbuild
- Bootstrap approach: `start-mcp.sh` runs `npm install` if `node_modules` missing

## Operational Notes

### Build Process
- Bootstrap script approach (not esbuild) — `tsc` only, `start-mcp.sh` handles `npm install`
- SQLite via better-sqlite3 + drizzle-orm (native addon, can't bundle)

### WAL Protocol Detail
- States: pending → target_written → committed → delete
- **Every write path** must participate — not just the clean pull path
- Conflict resolution, error recovery, and cleanup paths need WAL too
- WAL entry lifetime = first mutation → last side effect (push to Notion)
- See `docs/guides/data-integrity-patterns.md` for the full pattern

### Sync Design
- Circuit breaker: closed → open (10 failures) → half-open → closed
- Content hashing: SHA-256 of normalized markdown
- Roundtrip base: after push, pull-back content stored as merge base
- Queue dedup: by (side, entityKey), latest operation wins

### Triage System
- Doc tiers: Product (5 docs) / Tool (2 docs) / Inactive (none)
- Signals: LOC, hasBeads, isPlugin, mdCount, hasManifest, lastCommitDays, commitCount, hasReadme, hasSrc
- `doc_tier` column on entity_map (separate from `tier` which is T1/T2 sync priority)

### Status (as of v0.4.0)
- Phases 0-3 complete (scaffold, foundation, push sync, bidirectional sync)
- 21 MCP tools, 130 tests, 3 skills, 2 hooks
- @notionhq/client upgraded from v2 to v5 (data source model)
- All 59 local beads closed (35 were flux-drive findings)
- Next candidates: webhook receiver (P2, deferred to v0.5.x), interphase context integration (P2)

## Session Completion

> See `/root/projects/Interverse/AGENTS.md` for session completion protocol.


