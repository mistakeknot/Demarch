# Interverse Plugin Decomposition Design

**Date:** 2026-02-25
**Status:** Approved
**Scope:** 6 source plugins → 12 resulting plugins + 2 library upgrades

## Motivation

Three drivers, weighted equally:
1. **Adoption flexibility** — users install only what they need
2. **Token/context efficiency** — smaller plugins = less surface loaded per session
3. **Development velocity** — separate concerns evolve at independent rates

## Naming Strategy

The largest/most essential piece of each split keeps the original name. Extracted concerns get new names. No meta-packages — clean break with backward-compatible deprecation notices.

## Shared Code Strategy

Extracted plugins share code through the **interbase SDK** (existing shared integration SDK for dual-mode plugins). No per-split shared libraries, no copy-and-diverge.

## Decomposition Map

| Source | Keeps name as | Extracted to | Strategy |
|--------|--------------|-------------|----------|
| interflux | interflux (unified review+research pipeline) | intersense, interknow | Unify flux-drive/flux-research first, then extract |
| interkasten | interkasten (sync engine + entity map) | intertree | Core keeps name, doctor stays as thin redirect |
| interdev | interdev (mcp-cli + CC reference) | interskill, interplug | Core becomes lean reference |
| intercheck | intercheck (syntax-check + auto-format) | interpulse | Static guards keep name |
| intercache | intercache (blob store + session tracking) | Embeddings → intersearch | Not a new plugin — intersearch absorbs |
| interpath | interpath (all 7 artifact types) | — | No split — leave intact |

**Net new plugins:** 6 (intersense, interknow, intertree, interskill, interplug, interpulse)
**Library upgrades:** 2 (intersearch gains embedding persistence + nomic model, interbase gains shared utilities)
**Retired concerns:** 1 (flux-research as separate skill — merged into flux-drive)

---

## Detailed Splits

### 1. interflux — Unify + Extract

#### Pre-work: Unify flux-drive and flux-research

flux-drive and flux-research follow the same structural pattern (detect → score → dispatch → synthesize). The differences are tuning knobs, not separate architectures. Merge into a single pipeline with a `mode` parameter.

- **Review mode:** Staged launch, AgentDropout, peer findings, content slicing, knowledge compounding
- **Research mode:** Single-stage launch, no dropout, no peer findings, no slicing, research synthesis template

Two slash commands remain as thin entry points into the unified engine.

#### interflux (keeps name) — Unified multi-agent orchestration pipeline

- **Owns:** Single `flux-drive` skill with `mode` parameter (review | research)
- **Agents:** All 17 (12 review + 5 research). Mode determines which pool is scored.
- **Commands:** `/flux-drive` (review), `/flux-research` (shim → flux-drive research mode), `/flux-gen` (agent generation), `/fetch-findings`
- **MCP servers:** exa only (qmd moves to interknow)
- **Config retained:** `agent-roles.yaml`, `budget.yaml`
- **Dependencies:** intersense (domain detection), interknow (knowledge read/write), intersynth (synthesis)

#### intersense (new) — Project domain detection + content hashing

- **Migrated from interflux:** `detect-domains.py`, `content-hash.py`, `config/flux-drive/domains/` (renamed to `config/domains/`), domain `index.yaml`
- **Interface:** Python scripts callable from any plugin. Writes `.claude/intersense.yaml` (renamed from `.claude/flux-drive.yaml`)
- **No MCP server, no skills, no hooks** — pure library/script plugin
- **Consumers:** interflux, interknow, potentially intertest, interpath

#### interknow (new) — Durable knowledge compounding

- **Migrated from interflux:** qmd MCP server, `config/flux-drive/knowledge/` → `config/knowledge/`, background compounding agent, temporal decay logic
- **MCP server:** qmd (relocated from interflux)
- **Skills:** `/interknow:compound` (explicit knowledge write), `/interknow:recall` (query knowledge for a topic)
- **Hooks:** Optional SessionStart hook reporting knowledge stats
- **Dependencies:** intersense (domain tagging), intersearch (embedding queries for knowledge recall)

#### Config directory migration

```
interflux/config/flux-drive/
  domains/        → intersense/config/domains/
  knowledge/      → interknow/config/knowledge/
  agent-roles.yaml  → stays in interflux
  budget.yaml       → stays in interflux
```

---

### 2. interkasten — Extract hierarchy

#### interkasten (keeps name) — Notion sync engine

- **Owns:** MCP server with sync-related tools (~15 of 21): `interkasten_sync`, `_status`, `_log`, `_conflicts`, `_health`, `_version`, `_config_get/set`, `_init`, `_list/get/register/unregister_project`, `_refresh_key_docs`, `_add_database_property`, `_list_issues`
- **Owns:** All `store/` (SQLite tables), all `sync/` modules (engine, watcher, queue, notion-client, poller, translator, merge, beads-sync, entity-map, key-docs, linked-refs, triage)
- **Skills:** `/interkasten:onboard` (orchestrates sync setup), `/interkasten:doctor` (thin redirect to `/clavain:doctor --scope notion`)
- **Hooks:** All 3 (setup.sh, session-status.sh, session-end-warn.sh)

#### intertree (new) — Project hierarchy + layout management

- **Migrated tools (renamed):**
  - `interkasten_scan_preview` → `intertree_scan`
  - `interkasten_set_project_parent` → `intertree_set_parent`
  - `interkasten_set_project_tags` → `intertree_set_tags`
  - `interkasten_gather_signals` → `intertree_signals`
  - `interkasten_scan_files` → `intertree_scan_files`
- **Migrated code:** `discoverProjects()` (currently in `init.ts`, used by `hierarchy.ts`)
- **Skills:** `/intertree:layout` (renamed from `/interkasten:layout`)
- **No hooks** — layout is on-demand only
- **Dependencies:** Reads/writes interkasten's entity_map table via interbase SDK (shared SQLite access)

#### Coupling point: entity_map table

The entity_map table serves dual purposes: sync state (hashes, WAL, conflicts) and hierarchy (parent_id, tags, doc_tier). Column ownership:

| Owner | Columns |
|-------|---------|
| interkasten | local_hash, remote_hash, conflict_*, wal_ref, sync_status |
| intertree | parent_id, tags, doc_tier, hierarchy metadata |
| Shared (read by both) | entity_key, entity_type, local_path, notion_id |

Access mediated by interbase SDK module for `~/.interkasten/state.db`.

---

### 3. interdev — Extract skill + plugin authoring

#### interdev (keeps name) — Lean developer reference

- **Retains:** `mcp-cli` skill (MCP CLI interaction) + `working-with-claude-code` skill (37 reference docs, self-updating scraper)
- **Purpose:** Runtime tool discovery and official docs lookup
- **No hooks, no MCP, no commands**

#### interskill (new) — Consolidated skill authoring

- **Merges:** `create-agent-skills` + `writing-skills` into one unified skill
- **XML tension resolved:** Markdown headings (not XML) is authoritative. `core-principles.md` updated to match.
- **Structure:**
  - Spec phase: frontmatter fields, invocation control, `$ARGUMENTS`, subagent execution
  - Quality phase: TDD pressure testing, rationalization tables, CSO
  - Templates: `router-skill.md`, `simple-skill.md`
  - Workflows: 9 consolidated workflow files
  - References: ~15 deduplicated (down from ~25 across both source skills)
- **Skills:** `/interskill:create` (unified workflow), `/interskill:audit` (verify existing skill)
- **No hooks, no MCP**

#### interplug (new) — Plugin development lifecycle

- **Migrated from interdev:** `developing-claude-code-plugins` skill + 4 reference files
- **Skills:** `/interplug:create` (guided plugin creation), `/interplug:validate` (structure check), `/interplug:troubleshoot`
- **Dependencies:** Optionally references interskill for skill-authoring within plugin creation
- **No hooks, no MCP**

---

### 4. intercheck — Extract session monitor

#### intercheck (keeps name) — Static code quality guards

- **Retains:** `syntax-check.sh`, `auto-format.sh`
- **Hooks:** PostToolUse on `Edit|Write|NotebookEdit`
- **Shared lib:** Keeps `_ic_file_path`, `_ic_detect_lang` from `lib/intercheck-lib.sh`
- **State:** Own counter file at `/tmp/intercheck-${SESSION_ID}.json` (just `syntax_errors`, `format_runs`)
- **Skills:** `/intercheck:status` (syntax error count + format run count)
- **Bug fix:** Declares `"hooks": "./hooks/hooks.json"` in plugin.json (currently missing)

#### interpulse (new) — Session context monitoring

- **Migrated:** `context-monitor.sh`, session state functions from intercheck-lib
- **Hooks:** PostToolUse on `Edit|Write|Bash|Task|NotebookEdit|MultiEdit`
- **State:** Owns `/tmp/interpulse-${SESSION_ID}.json` (pressure, tokens, calls, heavy_calls, last_call_ts)
- **Skills:** `/interpulse:status` (full pressure gauge, token estimate, session age, recommendations)
- **Dependencies:** interband (optional, for statusline publishing to interline)

#### State file decoupling

Before: One shared `/tmp/intercheck-${SID}.json` with all fields, race condition risk on concurrent writes.
After: Two independent files, no cross-read needed:
- `/tmp/intercheck-${SID}.json` — `{syntax_errors, format_runs}`
- `/tmp/interpulse-${SID}.json` — `{pressure, tokens, calls, heavy_calls, last_call_ts}`

---

### 5. intercache + intersearch — Embedding consolidation

#### intercache (keeps name) — Blob store + session tracking

- **Retains:** 8 of 10 MCP tools: `cache_lookup`, `cache_store`, `cache_invalidate`, `cache_warm`, `cache_stats`, `cache_purge`, `session_track`, `session_diff`
- **Loses:** `embedding_index`, `embedding_query` → move to intersearch
- **Bug fix:** Add `launch-intercache.sh` launcher per critical-patterns convention

#### intersearch (library → library + MCP) — Shared embedding infrastructure

- **Gains from intercache:** Embedding persistence (`embeddings.py` adapted), `embedding_index` and `embedding_query` as MCP tools
- **Model consolidation:** `all-MiniLM-L6-v2` (384d) → `nomic-embed-text-v1.5` (768d)
- **Matryoshka support:** nomic model supports truncation to 384d/256d/128d for speed-sensitive consumers
- **Retains:** `EmbeddingClient`, `ExaClient`
- **Consumers:** interject, interflux (via interknow), intercache (delegates embedding calls)
- **Migration:** Existing 384d embeddings invalidated on model switch; reindex on first use

---

### 6. interpath — No split

interpath's 7 artifact types share a discovery phase, are coupled by the monorepo/propagate pipeline, and orchestrated by the `all.md` command. The phase files are well-isolated internally. Leave intact.

---

## Dependency Graph

```
                    ┌─────────────┐
                    │  interbase  │  (shared SDK)
                    └──────┬──────┘
           ┌───────────────┼───────────────┬──────────────┐
           │               │               │              │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼─────┐ ┌─────▼──────┐
    │ intersense  │ │ intersearch │ │ interkasten│ │  interband │
    │(domain det.)│ │(embed+exa)  │ │  (sync)    │ │ (sideband) │
    └──────┬──────┘ └──────┬──────┘ └──────┬─────┘ └─────┬──────┘
           │        ┌──────┘               │              │
    ┌──────▼──────┐ │              ┌───────▼──────┐ ┌─────▼──────┐
    │  interknow  │◄┘              │  intertree   │ │ interpulse │
    │(knowledge)  │                │ (hierarchy)  │ │(session mon)│
    └──────┬──────┘                └──────────────┘ └────────────┘
           │
    ┌──────▼──────┐
    │  interflux  │──────► intersynth (synthesis)
    │  (unified   │──────► interpeer  (cross-AI)
    │   pipeline) │
    └─────────────┘

    Independent (no new deps):
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ intercheck  │  │  interskill │  │  interplug  │  │   interdev  │
    │(static guard)│  │(skill auth) │  │(plugin dev) │  │  (ref docs) │
    └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

## Execution Phases

### Phase 0 — Prerequisites (no new plugins)

1. Fix intercheck's undeclared hooks bug in plugin.json
2. Add launcher script to intercache
3. Unify flux-drive and flux-research into single pipeline with `mode` parameter

### Phase 1 — Leaf extractions (parallelizable)

All independent, can execute simultaneously:
- Extract **interpulse** from intercheck
- Extract **interskill** from interdev (merge + consolidate)
- Extract **interplug** from interdev
- Extract **intertree** from interkasten

### Phase 2 — Infrastructure extractions

- Extract **intersense** from interflux
- Upgrade **intersearch** with embedding persistence + nomic-embed-text-v1.5

### Phase 3 — Dependent extractions

- Extract **interknow** from interflux (depends on intersense + intersearch)

### Phase 4 — Rewire consumers

- Update interflux to depend on intersense + interknow
- Update intercache to remove embedding tools
- Update interkasten to expose entity_map access via interbase for intertree

## Risk Assessment

| Split | Risk | Mitigation |
|-------|------|-----------|
| intertree ↔ interkasten | **High** — shared SQLite table | interbase SDK mediates; well-defined column ownership |
| interflux → intersense | **Low** — pure script extraction |
| interflux → interknow | **Medium** — qmd MCP relocation | Update all knowledge read/write paths |
| intercache → intersearch | **Medium** — model change invalidates embeddings | Drop + reindex on first use |
| intercheck → interpulse | **Low** — state file rename, clean separation |
| interdev → interskill/interplug | **Low** — skills-only, no runtime state |

## Original Intent (Deferred Items)

The following items from the original analysis were evaluated and deferred:

- **interpath split** (planning vs tracking artifacts) — deferred because shared discovery phase and monorepo pipeline make splitting costly for little benefit. Revisit if interpath exceeds 10 artifact types.
- **interkasten-doctor as separate plugin** — deferred because the doctor skill is already a thin redirect to `/clavain:doctor --scope notion`. No value in a separate plugin for a one-line redirect.
- **Three-way interflux split** (review + research + knowledge) — superseded by the unify-first decision. Review and research are modes of one pipeline, not separate architectures.
- **interdev → interauthor** (single extraction for all meta-authoring) — rejected in favor of interskill + interplug because skill authoring and plugin development serve different audiences at different stages.
