# Implementation Plan: Interverse Plugin Decomposition

**Date:** 2026-02-25
**Design:** [2026-02-25-interverse-plugin-decomposition-design.md](2026-02-25-interverse-plugin-decomposition-design.md)
**Scope:** 6 source plugins → 12 resulting plugins + 2 library upgrades
**Estimated tasks:** 38

### Progress

- [x] Phase 0 — Prerequisites (5/5 tasks) — committed
- [x] Phase 1 — Leaf Extractions (15/15 tasks) — committed
- [x] Phase 2 — Infrastructure Extractions (6/6 tasks) — committed
- [x] Phase 3 — Dependent Extractions (5/5 tasks) — committed
- [x] Phase 4 — Rewire Consumers + Cleanup (7/7 tasks) — all committed and validated

**New plugins created:** interpulse, interskill, interplug, intertree, intersense, interknow
**Plugins modified:** interflux, intercheck, interdev, interkasten, interbase, intercache, intersearch

**Notes:**
- intertree MCP tool handlers remain in interkasten (require DaemonContext). Pure functions extracted. Full migration deferred to Phase 4.
- interdev reduced from 5 skills to 2 (mcp-cli, working-with-claude-code)
- intercheck reduced to code quality only (syntax + format); pressure tracking moved to interpulse
- intersense created for domain detection; interflux scripts replaced with delegation stubs
- intersearch upgraded to v0.2.0 with MCP server + persistent embedding store (nomic-embed-text-v1.5)
- intercache reduced to 8 tools (embedding_index/embedding_query moved to intersearch)

---

## Phase 0 — Prerequisites (no new plugins)

These fix existing bugs and prepare the unified pipeline before any extraction begins.

### Task 0.1: Fix intercheck undeclared hooks bug

**What:** Add `"hooks": "./hooks/hooks.json"` to `interverse/intercheck/.claude-plugin/plugin.json`.

**Files:**
- Edit: `interverse/intercheck/.claude-plugin/plugin.json`

**Acceptance:**
- `jq '.hooks' interverse/intercheck/.claude-plugin/plugin.json` returns `"./hooks/hooks.json"`
- Plugin validation passes: `jq -e '.name and .skills and .hooks' plugin.json`

---

### Task 0.2: Add launcher script to intercache

**What:** Create `scripts/launch-intercache.sh` following critical-patterns convention. Checks `uv` availability, exits 0 gracefully if missing. Update `plugin.json` to use launcher.

**Files:**
- Create: `interverse/intercache/scripts/launch-intercache.sh`
- Edit: `interverse/intercache/.claude-plugin/plugin.json` — change mcpServers.intercache.command to use launcher

**Acceptance:**
- `bash interverse/intercache/scripts/launch-intercache.sh --check` exits 0 on this machine
- `plugin.json` mcpServers.intercache.command references `launch-intercache.sh`
- Without `uv`: script exits 0 silently (graceful degradation)

---

### Task 0.3: Unify flux-drive and flux-research — add mode parameter to SKILL.md

**What:** Modify `flux-drive/SKILL.md` to accept a `mode` parameter (review | research). In review mode, all existing phases activate. In research mode: single-stage launch, no AgentDropout, no peer findings, no content slicing, research synthesis template. Default mode is `review`.

**Files:**
- Edit: `interverse/interflux/skills/flux-drive/SKILL.md` — add mode handling at top of triage phase
- Edit: `interverse/interflux/skills/flux-drive/SKILL-compact.md` — same mode handling
- Edit: `interverse/interflux/skills/flux-drive/phases/launch.md` — skip staging/dropout when mode=research
- Edit: `interverse/interflux/skills/flux-drive/phases/synthesize.md` — select synthesis template by mode

**Acceptance:**
- SKILL.md documents `mode` parameter in frontmatter or argument description
- `mode=research` skips: staged launch (Step 2.2a–2.2c), AgentDropout (Step 2.2a.5), peer findings, content slicing
- `mode=research` uses research agent pool for scoring (5 agents) instead of review pool (12 agents)
- `mode=review` behaves identically to current flux-drive

---

### Task 0.4: Update flux-research command to shim into flux-drive

**What:** Replace `flux-research/SKILL.md` content with a thin redirect that invokes flux-drive with `mode=research`. Update the command file.

**Files:**
- Edit: `interverse/interflux/commands/flux-research.md` — invoke flux-drive skill with mode=research
- Remove skill registration: Edit `interverse/interflux/.claude-plugin/plugin.json` — remove `flux-research` from skills array (keep as command only)
- Keep: `interverse/interflux/skills/flux-research/SKILL.md` — mark deprecated, redirect to flux-drive

**Acceptance:**
- `/flux-research` command invokes flux-drive in research mode
- `plugin.json` skills array contains only `flux-drive`
- Old `flux-research` SKILL.md has deprecation notice

---

### Task 0.5: Merge research agent scoring into flux-drive triage

**What:** The flux-drive triage phase (Step 1.2) currently only scores review agents. Add research agent pool with a query-type affinity table (from flux-research SKILL.md) that activates when `mode=research`.

**Files:**
- Edit: `interverse/interflux/skills/flux-drive/SKILL.md` — add research scoring table in triage section
- Edit: `interverse/interflux/skills/flux-drive/SKILL-compact.md` — same

**Acceptance:**
- In `mode=research`: triage scores 5 research agents using affinity table (3=primary, 2=secondary, 0=skip)
- In `mode=review`: triage scores 12 review agents using existing formula (unchanged)
- Domain bonus +1 for research agents when Research Directives exist

---

## Phase 1 — Leaf Extractions

All 4 extractions in this phase are independent and can be executed in parallel.

### Task 1.1: Scaffold interpulse plugin

**What:** Create the interpulse plugin directory with standard plugin structure.

**Files:**
- Create: `interverse/interpulse/.claude-plugin/plugin.json`
- Create: `interverse/interpulse/CLAUDE.md`
- Create: `interverse/interpulse/AGENTS.md`
- Create: `interverse/interpulse/README.md`

**Acceptance:**
- `jq '.name' plugin.json` = `"interpulse"`
- Version `0.1.0`
- Description: "Session context monitoring — pressure tracking, token estimation, threshold warnings"

---

### Task 1.2: Move context-monitor.sh to interpulse

**What:** Copy `context-monitor.sh` from intercheck to interpulse. Rename state file prefix from `intercheck` to `interpulse`. Extract session-state functions from `intercheck-lib.sh` into interpulse's own lib.

**Files:**
- Create: `interverse/interpulse/hooks/hooks.json` — PostToolUse on `Edit|Write|Bash|Task|NotebookEdit|MultiEdit`
- Create: `interverse/interpulse/hooks/context-monitor.sh` — adapted from intercheck version
- Create: `interverse/interpulse/lib/interpulse-lib.sh` — `_ip_session_id`, `_ip_state_file`, `_ip_read_state`, `_ip_write_state`
- Edit: `interverse/interpulse/.claude-plugin/plugin.json` — add `"hooks": "./hooks/hooks.json"`

**Acceptance:**
- `context-monitor.sh` sources `interpulse-lib.sh` (not intercheck-lib.sh)
- State file path: `/tmp/interpulse-${SESSION_ID}.json`
- State schema: `{calls, last_call_ts, pressure, heavy_calls, est_tokens}` (no syntax_errors, format_runs)
- Interband publishing intact (optional dep on interband.sh)

---

### Task 1.3: Create interpulse status skill

**What:** Create `/interpulse:status` skill showing pressure gauge, token estimate, session age.

**Files:**
- Create: `interverse/interpulse/skills/status/SKILL.md`

**Acceptance:**
- Reads `/tmp/interpulse-${SESSION_ID}.json`
- Renders pressure bar (16-char), level (Green/Yellow/Orange/Red), token estimate, session age, recommendation
- Matches existing intercheck status behavior for pressure-related fields

---

### Task 1.4: Remove context-monitor from intercheck

**What:** Remove context-monitor.sh from intercheck. Update hooks.json to only declare syntax-check and auto-format. Simplify intercheck-lib.sh to remove session state functions. Update intercheck's state file to only track `{syntax_errors, format_runs}`.

**Files:**
- Delete: `interverse/intercheck/hooks/context-monitor.sh`
- Edit: `interverse/intercheck/hooks/hooks.json` — remove context-monitor matcher group
- Edit: `interverse/intercheck/lib/intercheck-lib.sh` — remove `_ic_session_id`, `_ic_read_state`, `_ic_write_state`, `_ic_state_file`; keep `_ic_file_path`, `_ic_detect_lang`
- Edit: `interverse/intercheck/hooks/syntax-check.sh` — write to simple counter file `{syntax_errors, format_runs}` instead of full state
- Edit: `interverse/intercheck/hooks/auto-format.sh` — same counter file update
- Edit: `interverse/intercheck/skills/status/SKILL.md` — show only syntax errors + format runs (no pressure)

**Acceptance:**
- `intercheck/hooks/hooks.json` has only one PostToolUse matcher group (Edit|Write|NotebookEdit)
- `context-monitor.sh` no longer exists in intercheck
- syntax-check.sh and auto-format.sh write `/tmp/intercheck-${SID}.json` with `{syntax_errors, format_runs}` only
- No interband dependency in intercheck

---

### Task 1.5: Scaffold interskill plugin

**What:** Create interskill plugin with standard structure.

**Files:**
- Create: `interverse/interskill/.claude-plugin/plugin.json`
- Create: `interverse/interskill/CLAUDE.md`
- Create: `interverse/interskill/AGENTS.md`
- Create: `interverse/interskill/README.md`

**Acceptance:**
- `jq '.name' plugin.json` = `"interskill"`
- Version `0.1.0`
- Skills: `create`, `audit`

---

### Task 1.6: Consolidate skill-authoring into interskill

**What:** Merge `create-agent-skills` and `writing-skills` from interdev into one unified skill in interskill. Resolve XML tension (markdown headings is authoritative). Deduplicate references.

**Files:**
- Create: `interverse/interskill/skills/create/SKILL.md` — unified workflow (spec phase + quality phase)
- Create: `interverse/interskill/skills/create/references/` — deduplicated from both source skills (~15 files)
- Create: `interverse/interskill/skills/create/templates/` — `router-skill.md`, `simple-skill.md`
- Create: `interverse/interskill/skills/create/workflows/` — consolidated 9 workflow files
- Create: `interverse/interskill/skills/audit/SKILL.md` — skill verification workflow

**Acceptance:**
- Unified SKILL.md covers: frontmatter fields, invocation control, `$ARGUMENTS`, subagent execution, TDD pressure testing, rationalization tables, CSO
- No XML tag recommendations anywhere — markdown headings only
- `core-principles.md` reference updated to match markdown convention
- Templates and workflow files present and internally consistent

---

### Task 1.7: Remove skill-authoring skills from interdev

**What:** Remove `create-agent-skills` and `writing-skills` skills from interdev. Update plugin.json.

**Files:**
- Edit: `interverse/interdev/.claude-plugin/plugin.json` — remove `create-agent-skills` and `writing-skills` from skills array
- Keep source directories with deprecation notice (or delete if preferred)

**Acceptance:**
- `plugin.json` skills array: `["./skills/mcp-cli", "./skills/working-with-claude-code", "./skills/developing-claude-code-plugins"]`
- interdev CLAUDE.md updated to reflect 3 skills

---

### Task 1.8: Scaffold interplug plugin

**What:** Create interplug plugin with standard structure.

**Files:**
- Create: `interverse/interplug/.claude-plugin/plugin.json`
- Create: `interverse/interplug/CLAUDE.md`
- Create: `interverse/interplug/AGENTS.md`
- Create: `interverse/interplug/README.md`

**Acceptance:**
- `jq '.name' plugin.json` = `"interplug"`
- Version `0.1.0`
- Skills: `create`, `validate`, `troubleshoot`

---

### Task 1.9: Move plugin dev skill to interplug

**What:** Move `developing-claude-code-plugins` skill from interdev to interplug. Create validate and troubleshoot skills.

**Files:**
- Create: `interverse/interplug/skills/create/SKILL.md` — adapted from interdev's `developing-claude-code-plugins`
- Create: `interverse/interplug/skills/create/references/` — `plugin-structure.md`, `common-patterns.md`, `polyglot-hooks.md`, `troubleshooting.md`
- Create: `interverse/interplug/skills/validate/SKILL.md` — plugin structure validation
- Create: `interverse/interplug/skills/troubleshoot/SKILL.md` — plugin debugging guide

**Acceptance:**
- `/interplug:create` covers full plugin lifecycle (plan → create → test → release)
- `/interplug:validate` checks plugin.json schema, hooks declaration, skill structure
- `/interplug:troubleshoot` covers common failure modes
- Optional reference to interskill for skill-authoring within plugin creation

---

### Task 1.10: Remove plugin dev skill from interdev

**What:** Remove `developing-claude-code-plugins` from interdev. Update plugin.json.

**Files:**
- Edit: `interverse/interdev/.claude-plugin/plugin.json` — remove from skills array
- Keep source directory with deprecation notice (or delete)

**Acceptance:**
- `plugin.json` skills array: `["./skills/mcp-cli", "./skills/working-with-claude-code"]`
- interdev CLAUDE.md updated to reflect 2 skills

---

### Task 1.11: Scaffold intertree plugin

**What:** Create intertree plugin as a TypeScript MCP server plugin (mirrors interkasten's server pattern).

**Files:**
- Create: `interverse/intertree/.claude-plugin/plugin.json`
- Create: `interverse/intertree/CLAUDE.md`
- Create: `interverse/intertree/AGENTS.md`
- Create: `interverse/intertree/README.md`
- Create: `interverse/intertree/scripts/launch-mcp.sh`

**Acceptance:**
- `jq '.name' plugin.json` = `"intertree"`
- Version `0.1.0`
- MCP server declared with launcher script
- Skills: `layout`

---

### Task 1.12: Extract discoverProjects to intertree

**What:** Move `discoverProjects()` function from interkasten's `init.ts` to intertree. This is a pure filesystem tree walker with no sync dependencies.

**Files:**
- Create: `interverse/intertree/server/src/discovery.ts` — contains `discoverProjects()` and supporting types
- Edit: `interverse/interkasten/server/src/daemon/tools/init.ts` — import `discoverProjects` from intertree (or inline a thin wrapper that calls intertree's MCP tool)

**Acceptance:**
- `discoverProjects()` lives in intertree
- interkasten's `init.ts` still works (calls intertree_scan or maintains local copy with deprecation)
- No functional regression in `/interkasten:onboard`

---

### Task 1.13: Extract hierarchy tools to intertree MCP server

**What:** Move the 5 hierarchy-related MCP tool handlers from interkasten to intertree's MCP server. Rename tool prefixes.

**Files:**
- Create: `interverse/intertree/server/src/tools/scan.ts` — `intertree_scan` (from `interkasten_scan_preview`)
- Create: `interverse/intertree/server/src/tools/hierarchy.ts` — `intertree_set_parent`, `intertree_set_tags` (from interkasten equivalents)
- Create: `interverse/intertree/server/src/tools/signals.ts` — `intertree_signals`, `intertree_scan_files` (from interkasten equivalents)
- Edit: `interverse/interkasten/server/src/daemon/tools/hierarchy.ts` — remove migrated handlers
- Edit: `interverse/interkasten/server/src/daemon/tools/signals.ts` — remove migrated handlers

**Acceptance:**
- intertree MCP server registers 5 tools: `intertree_scan`, `intertree_set_parent`, `intertree_set_tags`, `intertree_signals`, `intertree_scan_files`
- interkasten no longer registers the 5 migrated tools
- intertree connects to `~/.interkasten/state.db` for entity_map access (via interbase SDK or direct SQLite)

---

### Task 1.14: Move layout skill to intertree

**What:** Move the layout skill from interkasten to intertree. Update tool references.

**Files:**
- Create: `interverse/intertree/skills/layout/SKILL.md` — adapted from interkasten's layout skill, tool names updated to `intertree_*`
- Edit: `interverse/interkasten/.claude-plugin/plugin.json` — remove `layout` from skills array
- Edit: `interverse/interkasten/CLAUDE.md` — remove layout skill reference

**Acceptance:**
- `/intertree:layout` works end-to-end (scan → hierarchy review → classification → register)
- `/interkasten:layout` no longer exists
- interkasten plugin.json lists 2 skills: `onboard`, `doctor`

---

### Task 1.15: Add interbase SDK module for shared SQLite access

**What:** Add a TypeScript or shell module to interbase that provides mediated access to `~/.interkasten/state.db`. This is the contract between interkasten and intertree.

**Files:**
- Create: `sdk/interbase/ts/kasten-store.ts` — exports functions for reading/writing hierarchy columns (parent_id, tags, doc_tier) on entity_map
- Or: Create: `sdk/interbase/lib/interkasten-db.sh` — shell helper for SQLite queries on entity_map hierarchy columns

**Acceptance:**
- intertree uses interbase SDK to access entity_map (not direct SQLite imports from interkasten)
- Column ownership documented: interkasten owns sync columns, intertree owns hierarchy columns
- Read access to shared columns (entity_key, entity_type, local_path, notion_id) available to both

---

## Phase 2 — Infrastructure Extractions

### Task 2.1: Scaffold intersense plugin

**What:** Create intersense plugin directory.

**Files:**
- Create: `interverse/intersense/.claude-plugin/plugin.json`
- Create: `interverse/intersense/CLAUDE.md`
- Create: `interverse/intersense/AGENTS.md`
- Create: `interverse/intersense/README.md`

**Acceptance:**
- `jq '.name' plugin.json` = `"intersense"`
- Version `0.1.0`
- No skills, no hooks, no MCP — scripts-only plugin

---

### Task 2.2: Move domain detection scripts to intersense

**What:** Move `detect-domains.py`, `content-hash.py`, and domain profiles from interflux to intersense.

**Files:**
- Move: `interverse/interflux/scripts/detect-domains.py` → `interverse/intersense/scripts/detect-domains.py`
- Move: `interverse/interflux/scripts/content-hash.py` → `interverse/intersense/scripts/content-hash.py`
- Move: `interverse/interflux/config/flux-drive/domains/` → `interverse/intersense/config/domains/`
- Edit: `interverse/intersense/scripts/detect-domains.py` — update output path from `.claude/flux-drive.yaml` to `.claude/intersense.yaml`
- Edit: `interverse/intersense/scripts/content-hash.py` — no changes expected (path-agnostic)

**Acceptance:**
- `python3 interverse/intersense/scripts/detect-domains.py /path/to/project` writes `.claude/intersense.yaml`
- All 11 domain profiles present in `intersense/config/domains/`
- `index.yaml` references correct relative paths

---

### Task 2.3: Update interflux to use intersense

**What:** Update all interflux references to domain detection to call intersense scripts instead of local copies.

**Files:**
- Edit: `interverse/interflux/skills/flux-drive/SKILL.md` — Step 1.0.1 calls intersense scripts
- Edit: `interverse/interflux/skills/flux-drive/SKILL-compact.md` — same
- Edit: `interverse/interflux/scripts/generate-agents.py` — read domain profiles from intersense path
- Edit: `interverse/interflux/scripts/update-domain-profiles.py` — point to intersense config
- Leave stubs: `interverse/interflux/scripts/detect-domains.py` → thin wrapper calling intersense version
- Leave stubs: `interverse/interflux/scripts/content-hash.py` → thin wrapper calling intersense version

**Acceptance:**
- flux-drive triage reads `.claude/intersense.yaml` (not `.claude/flux-drive.yaml`)
- `generate-agents.py` reads domain profiles from intersense
- Backward compat: stub scripts in interflux delegate to intersense
- Full flux-drive review still works end-to-end

---

### Task 2.4: Upgrade intersearch with embedding persistence

**What:** Add embedding persistence (SQLite) and nomic-embed-text-v1.5 model to intersearch. Add MCP server capability.

**Files:**
- Edit: `interverse/intersearch/src/intersearch/embeddings.py` — switch model from `all-MiniLM-L6-v2` to `nomic-ai/nomic-embed-text-v1.5` (768d)
- Create: `interverse/intersearch/src/intersearch/store.py` — SQLite embedding store (adapted from intercache's `embeddings.py`)
- Create: `interverse/intersearch/src/intersearch/server.py` — MCP server with `embedding_index` and `embedding_query` tools
- Edit: `interverse/intersearch/pyproject.toml` — add `mcp`, `einops` dependencies; update `sentence-transformers` for nomic support
- Create: `interverse/intersearch/.claude-plugin/plugin.json` — register as plugin with MCP server
- Create: `interverse/intersearch/scripts/launch-intersearch.sh` — launcher script

**Acceptance:**
- `EmbeddingClient.embed("test")` returns 768d vector (not 384d)
- SQLite store persists embeddings with model version tracking
- `embedding_index` and `embedding_query` MCP tools work
- Auto-invalidation when model version changes (reindex on first use)
- Launcher script exits 0 gracefully if dependencies missing

---

### Task 2.5: Remove embedding tools from intercache

**What:** Remove `embedding_index` and `embedding_query` from intercache MCP server.

**Files:**
- Edit: `interverse/intercache/src/intercache/server.py` — remove embedding tool registrations
- Delete or deprecate: `interverse/intercache/src/intercache/embeddings.py`
- Edit: `interverse/intercache/pyproject.toml` — remove `sentence-transformers`, `einops` from deps (if no other consumer)

**Acceptance:**
- intercache MCP server registers 8 tools (was 10)
- `embedding_index` and `embedding_query` no longer available via intercache
- intercache has no dependency on sentence-transformers

---

### Task 2.6: Update intercache consumers to use intersearch for embeddings

**What:** Any code that called intercache's `embedding_index`/`embedding_query` must now call intersearch.

**Files:**
- Search for all references to `intercache` + `embedding` across the monorepo
- Update MCP tool calls to target `intersearch` server instead of `intercache`

**Acceptance:**
- No remaining references to intercache embedding tools
- All embedding consumers use intersearch MCP server

---

## Phase 3 — Dependent Extractions

### Task 3.1: Scaffold interknow plugin

**What:** Create interknow plugin directory with MCP server.

**Files:**
- Create: `interverse/interknow/.claude-plugin/plugin.json`
- Create: `interverse/interknow/CLAUDE.md`
- Create: `interverse/interknow/AGENTS.md`
- Create: `interverse/interknow/README.md`
- Create: `interverse/interknow/scripts/launch-qmd.sh` — relocated from interflux

**Acceptance:**
- `jq '.name' plugin.json` = `"interknow"`
- Version `0.1.0`
- MCP server: qmd (via launcher)
- Skills: `compound`, `recall`

---

### Task 3.2: Move knowledge directory and qmd MCP to interknow

**What:** Move knowledge compounding infrastructure from interflux to interknow.

**Files:**
- Move: `interverse/interflux/config/flux-drive/knowledge/` → `interverse/interknow/config/knowledge/`
- Move: `interverse/interflux/scripts/launch-qmd.sh` → `interverse/interknow/scripts/launch-qmd.sh`
- Edit: `interverse/interflux/.claude-plugin/plugin.json` — remove qmd from mcpServers
- Edit: `interverse/interknow/.claude-plugin/plugin.json` — add qmd MCP server

**Acceptance:**
- interknow serves qmd MCP tools
- interflux no longer declares qmd MCP server
- Knowledge entries accessible via interknow's qmd

---

### Task 3.3: Create interknow skills

**What:** Create `/interknow:compound` and `/interknow:recall` skills.

**Files:**
- Create: `interverse/interknow/skills/compound/SKILL.md` — explicit knowledge write workflow (extracted from flux-drive synthesize phase's silent compounding)
- Create: `interverse/interknow/skills/recall/SKILL.md` — query knowledge for a topic with domain-aware filtering

**Acceptance:**
- `/interknow:compound` writes a knowledge entry with provenance, domain tag (via intersense), temporal metadata
- `/interknow:recall` searches qmd with query, returns top-K entries with source attribution
- Both skills work independently of interflux

---

### Task 3.4: Create interknow SessionStart hook

**What:** Optional hook that reports knowledge stats at session start.

**Files:**
- Create: `interverse/interknow/hooks/hooks.json`
- Create: `interverse/interknow/hooks/session-start.sh` — counts knowledge entries, reports via additionalContext

**Acceptance:**
- Hook outputs `{"additionalContext": "interknow: N knowledge entries across M domains"}`
- Graceful degradation if qmd not running (skips silently)

---

### Task 3.5: Update interflux to use interknow for knowledge operations

**What:** Update flux-drive skill to delegate knowledge read/write to interknow instead of local qmd/knowledge paths.

**Files:**
- Edit: `interverse/interflux/skills/flux-drive/phases/launch.md` — Step 2.1 reads knowledge via interknow's qmd MCP (tool name change if any)
- Edit: `interverse/interflux/skills/flux-drive/phases/synthesize.md` — silent compounding delegates to `/interknow:compound` or interknow's write tools
- Leave stub: `interverse/interflux/scripts/launch-qmd.sh` → error message redirecting to interknow

**Acceptance:**
- flux-drive review still injects knowledge context per agent (unchanged behavior)
- Knowledge compounding in synthesis phase writes to interknow's store
- No functional regression in end-to-end flux-drive review

---

## Phase 4 — Rewire Consumers + Cleanup

### Task 4.1: Update interflux plugin.json dependencies

**What:** Document interflux's new dependencies on intersense and interknow in plugin.json or integration.json.

**Files:**
- Edit: `interverse/interflux/.claude-plugin/plugin.json` — update description, verify skills/commands/agents lists
- Edit: `interverse/interflux/.claude-plugin/integration.json` — declare intersense, interknow as ecosystem dependencies
- Edit: `interverse/interflux/CLAUDE.md` — update component counts and dependency list

**Acceptance:**
- integration.json lists intersense and interknow as dependencies
- CLAUDE.md accurately reflects: 1 skill, 4 commands, 17 agents, 1 MCP server (exa only)

---

### Task 4.2: Update interkasten for intertree separation

**What:** Clean up interkasten after hierarchy extraction. Ensure no dangling references.

**Files:**
- Edit: `interverse/interkasten/.claude-plugin/plugin.json` — remove layout skill, update description
- Edit: `interverse/interkasten/CLAUDE.md` — remove hierarchy references, document intertree dependency
- Edit: `interverse/interkasten/AGENTS.md` — update tool inventory

**Acceptance:**
- plugin.json lists 2 skills (onboard, doctor), ~15 MCP tools (not 21)
- No references to scan_preview, set_project_parent, set_project_tags, gather_signals, scan_files
- CLAUDE.md mentions intertree as companion for hierarchy operations

---

### Task 4.3: Update interdev for lean reference state

**What:** Final cleanup of interdev after both extractions.

**Files:**
- Edit: `interverse/interdev/.claude-plugin/plugin.json` — 2 skills only
- Edit: `interverse/interdev/CLAUDE.md` — update to reflect lean reference role
- Edit: `interverse/interdev/AGENTS.md` — update

**Acceptance:**
- plugin.json: 2 skills (mcp-cli, working-with-claude-code)
- CLAUDE.md mentions interskill and interplug as companions
- No remaining references to create-agent-skills or writing-skills or developing-claude-code-plugins

---

### Task 4.4: Update root CLAUDE.md plugin registry

**What:** Add new plugins to the Demarch monorepo CLAUDE.md structure section.

**Files:**
- Edit: `/home/mk/projects/Demarch/CLAUDE.md` — add intersense, interknow, intertree, interskill, interplug, interpulse to the interverse listing

**Acceptance:**
- All 6 new plugins listed with one-line descriptions
- Alphabetical order maintained

---

### Task 4.5: Register new plugins in marketplace

**What:** Add all 6 new plugins to the interagency marketplace.

**Files:**
- Edit: `core/marketplace/marketplace.json` — add entries for intersense, interknow, intertree, interskill, interplug, interpulse
- Run: `/interpub:release 0.1.0` for each new plugin (or batch via interbump)

**Acceptance:**
- All 6 plugins appear in `marketplace.json`
- Each has version `0.1.0`
- Each is installable via `claude plugins install`

---

### Task 4.6: Bump versions on modified source plugins

**What:** Bump versions on all 4 source plugins that were modified (interflux, interkasten, interdev, intercheck, intercache).

**Files:**
- Run version bumps via interbump for:
  - interflux: minor bump (unified pipeline + extracted concerns)
  - interkasten: minor bump (hierarchy tools removed)
  - interdev: minor bump (3 skills removed)
  - intercheck: minor bump (context-monitor removed, hooks bug fixed)
  - intercache: patch bump (embeddings removed, launcher added)

**Acceptance:**
- Each bumped plugin has consistent version across plugin.json, marketplace.json, installed_plugins.json
- Changelog entries in each plugin's docs

---

### Task 4.7: End-to-end validation

**What:** Verify all decomposed plugins work correctly in a fresh session.

**Validation checklist:**
1. `/flux-drive` review mode works (interflux → intersense → interknow → intersynth)
2. `/flux-research` invokes flux-drive in research mode
3. `/flux-gen` generates agents using intersense domain profiles
4. `/intertree:layout` scans and manages project hierarchy
5. `/interkasten:onboard` still works without hierarchy tools
6. `/interskill:create` walks through unified skill authoring
7. `/interplug:create` walks through plugin creation
8. `/intercheck:status` shows syntax errors + format runs only
9. `/interpulse:status` shows pressure gauge + token estimate
10. `/interknow:compound` writes a knowledge entry
11. `/interknow:recall` retrieves knowledge entries
12. intercache blob store works without embedding tools
13. intersearch embedding_index + embedding_query work with nomic model

**Acceptance:**
- All 13 checks pass
- No error output from any hook
- No undeclared hooks remaining

---

## Summary

| Phase | Tasks | Parallelizable | Key risk |
|-------|-------|---------------|----------|
| 0 — Prerequisites | 5 | Partially (0.1-0.2 parallel, 0.3-0.5 sequential) | flux-drive/research unification complexity |
| 1 — Leaf extractions | 10 | Yes (4 extraction streams) | intertree ↔ interkasten shared SQLite |
| 2 — Infrastructure | 6 | Partially (2.1-2.3 parallel with 2.4-2.6) | Model change invalidates embeddings |
| 3 — Dependent | 5 | Sequential (interknow depends on intersense + intersearch) | qmd MCP relocation |
| 4 — Rewire + cleanup | 7 | Mostly parallel | Marketplace registration ordering |
| **Total** | **38** | | |
