# Hardcoded Logic in Interkasten Tools — Analysis

This document identifies decision logic and hardcoded rules in Interkasten's MCP tools that belong in the agent layer, not in the tool layer. The principle: **tools should gather signals and return raw data; agents should decide what to do with it.**

---

## Critical Findings

### 1. **Triage Classification Rules (triage.ts)**

**The Problem:**
`classifyProject()` contains hardcoded thresholds that make tier assignments:
- `LOC >= 1000` → "Product" (line 89)
- `.beads exists && commitCount >= 10` → "Product" (line 92)
- `mdCount >= 5 && hasManifest && hasSrc` → "Product" (line 95)
- `lastCommitDays > 180 && commitCount < 5` → "Inactive" (line 77-82)
- `loc === 0 && mdCount < 2` → "Inactive" (line 84)

**Why This Is Wrong:**
- A project with 999 LOC is arbitrarily different from 1001 LOC, but the tool treats them as different tiers
- Different teams have different definitions of "Product" vs "Tool"
- The rules conflict: a .beads repo + recent commits might be Inactive in some contexts, Product in others
- The tool bakes in ordinal decision-making ("first-match wins") that could be configurable

**What the Agent Should Do:**
- Call `interkasten_gather_signals(project_path)` — returns raw TriageSignals
- Receive: `{ loc, hasBeads, commitCount, mdCount, lastCommitDays, ... }`
- Agent decides: "This is Product because..." (reasoning layer)
- Agent calls `interkasten_set_tier(project, tier, rationale)` explicitly

**How to Fix:**
1. Split `triageProject()` → `gatherSignals()` (already exists) + `classifyProject()` should not be called by tools
2. New tool: `interkasten_gather_signals(project)` — returns signals only
3. Remove `classifyProject()` from tool entry points; agent is responsible


---

### 2. **Required Docs Table (triage.ts, key-docs.ts)**

**The Problem:**
Line 38-42 (triage.ts) and line 13 (key-docs.ts) hardcode the 5 "key docs" and what each tier requires:

```typescript
export const TIER_DOC_REQUIREMENTS: Record<DocTier, readonly string[]> = {
  Product: ["Vision", "PRD", "Roadmap", "AGENTS.md", "CLAUDE.md"],
  Tool: ["AGENTS.md", "CLAUDE.md"],
  Inactive: [],
};

export const KEY_DOC_TYPES = ["Vision", "PRD", "Roadmap", "AGENTS.md", "CLAUDE.md"]
```

**Why This Is Wrong:**
- What if a team uses `.md` convention for "Roadmap" but calls it "Milestones.md"?
- Some teams might want "Architecture" as required, not "Vision"
- Some teams don't need PRD (research projects, libraries)
- The list is baked into database schema — changing it means migration

**What the Agent Should Do:**
- Call `interkasten_find_docs_matching(pattern, project)` — e.g., `find_docs_matching("roadmap|milestones|timeline", project)`
- Agent decides which docs are "required" based on project needs
- Agent passes requirements explicitly: `categorizeKeyDocs(docs, required_list)`

**How to Fix:**
1. Keep KEY_DOC_TYPES as constant (internal use only)
2. New tool: `interkasten_find_docs_by_pattern(project, pattern_list)` — searches by regexes, not hardcoded names
3. `categorizeKeyDocs()` should accept `required: string[]` as parameter, not look it up by tier
4. Agent is responsible for: "For Product tier, I require these docs: [...]"


---

### 3. **Doc Finding Heuristics (key-docs.ts)**

**The Problem:**
Lines 38-76 contain implicit rules for finding docs:
- Looks for AGENTS.md / CLAUDE.md only at root level (lines 40-42)
- Searches Vision/PRD/Roadmap in both root and `docs/` directory (lines 46-50)
- Uses prefix matching: `PRD-MVP.md` matches "prd" (line 69)
- Case-insensitive but exact prefix-based (line 64)

**Why This Is Wrong:**
- Why only root + docs/? Some projects use docs/guides/ or docs/specifications/
- Case-insensitive but prefix-based is arbitrary — what if someone names it "product_roadmap.md"?
- AGENTS.md / CLAUDE.md root-only assumption breaks if someone moves them to docs/
- No way for agent to provide custom search paths or patterns

**What the Agent Should Do:**
- Call `interkasten_scan_for_files(project, file_patterns)` — returns all matches
- Agent specifies patterns: `["AGENTS.md", "CLAUDE.md", "*roadmap*.md", "*vision*.md"]`
- Agent decides which match to use (e.g., if multiple roadmaps exist, pick the one in docs/)
- Agent provides the path explicitly to `updateProjectKeyDocs()`

**How to Fix:**
1. Rename `findKeyDoc()` → `findKeyDocsByPattern()` with explicit pattern parameter
2. Remove special cases for AGENTS.md / CLAUDE.md — treat all the same
3. Return all matches, not first match
4. New tool: `interkasten_search_files(project, patterns)` — agent calls this
5. Agent logic handles tie-breaking (multiple matches)


---

### 4. **Notion Database Schema Baked Into Tools (init.ts)**

**The Problem:**
Lines 140-163 define the entire Projects database schema:
- Status options: ["Active", "Archived", "Syncing"] (hardcoded colors)
- Doc Tier options: ["Product", "Tool", "Inactive"]
- Health Score format: `percent`
- Key doc columns: 5 URL fields

Lines 183-195 define Research Inbox schema:
- Status options: ["New", "Processing", "Classified", "Done"]

**Why This Is Wrong:**
- Tool decides what the Notion schema should be
- If agent wants to change status values (e.g., add "Paused"), tool needs code change
- Notion schema becomes implicit — no way to version it or query it
- Multi-workspace setups can't have different schemas

**What the Agent Should Do:**
- Call `interkasten_describe_schema()` — returns current schema definition
- Agent decides: "I want to add a 'Description' field" or "Change status colors"
- Agent calls `interkasten_ensure_schema(expected_schema, auto_fix=true)`
- Tool compares actual vs expected, reports diffs, applies if requested

**How to Fix:**
1. Move schema definitions to config.yaml or a separate schema.json file
2. `init` tool should load schema from config, not hardcode
3. New tool: `interkasten_get_schema()` — returns current schema from Notion
4. New tool: `interkasten_sync_schema(schema_object)` — agent-driven schema updates
5. Track schema version in config to enable migrations


---

### 5. **Auto-Cascading Behaviors (init.ts, projects.ts)**

**The Problem:**
init.ts automatically creates placeholder Notion pages for docs:
- Lines 284-298: loops through first 20 markdown files, creates a Notion page for each
- Hardcoded limit: `slice(0, 20)` (line 285)
- Assumes all .md files should be synced

projects.ts automatically sets Status when registering:
- Line 221: always sets Status to "Active"
- No option to set to "Archived" or "Syncing"

**Why This Is Wrong:**
- Agent has no control over which files get synced
- 20 is arbitrary — large projects will silently skip 50 docs
- Register tool can't express intent: "Register this as archived because it's a template"

**What the Agent Should Do:**
- Call `interkasten_discover_files(project)` — returns all markdown files with metadata
- Agent decides: "I want to sync [specific files]"
- Agent calls `interkasten_sync_files(file_list)` explicitly
- When registering, agent specifies status: `register_project(path, status="Active")`

**How to Fix:**
1. Remove auto-creation logic from init; make it opt-in
2. New tool: `interkasten_list_candidate_files(project)` — returns all .md files with metadata
3. Modify `interkasten_register_project` to accept `status` parameter (default: "Active")
4. `init` should report candidates to agent, ask before syncing
5. Agent decides scope of sync, not tool


---

### 6. **Confirmation Flow & Status Defaults (init.ts, projects.ts)**

**The Problem:**
init.ts doesn't ask for confirmation before creating databases:
- Lines 135-166: silently creates 3 databases
- No agent input on structure, naming, or placement
- Saves init manifest but doesn't surface it to agent for review

projects.ts registers new projects with silent assumptions:
- Line 273: assumes "Active" status is always correct
- Line 302-304: silently marks projects as "Archived" when unregistering

**Why This Is Wrong:**
- Agent can't see or question the created schema before it's written to Notion
- No transaction/rollback model for multi-step init
- Unregistering has side effects (marks as Archived) that agent might not intend

**What the Agent Should Do:**
- Call `interkasten_plan_init()` — returns what will be created without doing it
- Agent reviews: "Create 3 databases in this page?"
- Agent calls `interkasten_apply_init()` — now it actually creates
- Unregister includes explicit parameter: `unregister_project(path, action="delete"|"archive"|"orphan")`

**How to Fix:**
1. Split init into dry-run + apply phases
2. init tool returns plan: `{ databases: [...], schema: {...}, location: "..." }`
3. Agent reviews and calls init again with `apply=true`
4. Unregister tool: `unregister_project(path, action="soft_delete"|"orphan")` — agent decides
5. No silent cascading deletes


---

### 7. **Key Doc Sync Workflow Baked In (projects.ts, onboard skill)**

**The Problem:**
`interkasten_refresh_key_docs` automatically:
- Lines 356-371: optionally adds columns to database if `add_columns=true`
- Lines 397-401: automatically updates Notion for all projects
- Returns simplified summary; doesn't expose raw key doc data

onboard skill prescribes exact phases and order:
- Phase 1: Triage all (no per-project control)
- Phase 2: Generate docs in fixed order (Vision → PRD → Roadmap → AGENTS.md → CLAUDE.md)
- Phase 3: Establish drift baselines (assumes interwatch is available)

**Why This Is Wrong:**
- Tool decides when to add columns; agent can't preview what will be added
- No option to refresh only key docs, skip others
- Skill assumes all projects follow same workflow
- No escape hatch if a project's workflow is different

**What the Agent Should Do:**
- Call `interkasten_refresh_key_docs(project, patterns, dry_run=true)` — see what will update
- Agent reviews changes before applying
- Agent decides per-project workflow, not follows skill template
- Skill is a suggested pattern, not mandatory sequence

**How to Fix:**
1. Add `dry_run` parameter to refresh_key_docs
2. Return detailed diff: `{ updated: [], skipped: [], errors: [] }` with specifics
3. Refactor onboard skill into modular sub-tasks:
   - `onboard:triage-all` (returns tier distribution)
   - `onboard:generate-product-docs` (agent controls which)
   - `onboard:generate-tool-docs` (agent controls which)
   - `onboard:establish-drift-watch` (optional, opt-in)
4. Skill calls tools with explicit parameters, agent reviews output at each step


---

### 8. **Hardcoded File Scan Patterns (init.ts, key-docs.ts)**

**The Problem:**
`SKIP_DIRS` hardcoded (triage.ts line 33-36):
```typescript
const SKIP_DIRS = new Set([
  "node_modules", "dist", ".git", "__pycache__", "target",
  "build", ".next", "venv", ".venv", "vendor",
]);
```

`CODE_EXTENSIONS` hardcoded (triage.ts line 29-31):
```typescript
const CODE_EXTENSIONS = new Set([
  ".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go",
]);
```

`discoverProjects` uses hardcoded markers from config (init.ts line 259) but doesn't expose what was matched.

**Why This Is Wrong:**
- LOC count excludes C++, Java, Ruby — what if project uses those?
- Skips `.ruby/` or `.venv-python3.11/` but they're in SKIP_DIRS?
- If project has `.beads/` it signals "Product", but tool decides this
- No introspection: agent can't ask "which files did you count?"

**What the Agent Should Do:**
- Call `interkasten_analyze_project(path, config?)` — returns all signals with source files
- Response includes: `{ loc: 2000, loc_by_lang: { ts: 1200, js: 800 }, files_scanned: [...], dirs_skipped: [...] }`
- Agent can verify: "You counted LOC from X files in these dirs" — see the work
- Agent provides custom config: `{ skip_dirs: [...], code_extensions: [...] }`

**How to Fix:**
1. Refactor `gatherSignals` to return source information
2. Add `signals_with_debug` tool that shows which files contributed to each signal
3. Accept `config_override` parameter in triage tool
4. Return a "signals_detail" field: `{ loc: 2000, files: [{path, lang, lines}, ...] }`


---

### 9. **Required Docs Presentation (projects.ts, onboard skill)**

**The Problem:**
`categorizeKeyDocs` splits results into 3 buckets (required_missing, required_present, optional):
- Lines 170-198 (key-docs.ts) — categorizes based on tier
- Line 46 (projects.ts) — displays the 3-category breakdown

Tool assumes these categories are meaningful to agent, but doesn't explain the reasoning.

**Why This Is Wrong:**
- Agent sees "required_missing: [Vision, PRD]" but doesn't know why
- No way to override: "I know Vision is missing but I don't want to generate it"
- Categorization is implicit in tier; agent can't audit the logic

**What the Agent Should Do:**
- Call `interkasten_categorize_docs(docs, tier, rules?)` — agent can override rules
- Response includes reasoning: `{ type: "Vision", category: "required", reason: "Product tier requires Vision" }`
- Agent can say: "Show me all docs, categorize by my custom rules instead"
- Agent decides what to generate based on gaps + priority, not just "required"

**How to Fix:**
1. `categorizeKeyDocs` should return reasoning for each categorization
2. Accept `tier` + `custom_requirements` parameter
3. Return: `{ requiredMissing: [...], requiredPresent: [...], optional: [...], reasoning: { Vision: "..." } }`
4. Onboard skill uses this reasoning for logging, but agent can override


---

## Summary of Tool Refactoring Principles

| Current | Should Be |
|---------|-----------|
| Tool triages & decides tier | Tool gathers signals; agent decides tier |
| Tool defines required docs by tier | Tool finds docs; agent specifies requirements |
| Tool auto-creates Notion schema | Tool proposes schema; agent approves |
| Tool limits markdown scans to 20 files | Tool returns all candidates; agent selects |
| Tool sets Status to "Active" by default | Tool accepts status parameter; agent decides |
| Tool auto-adds database columns | Tool shows what would be added (dry-run); agent approves |
| Tool prescribes onboard workflow | Tool provides sub-tasks; agent composes workflow |
| Tool hides which files contributed to LOC | Tool returns file-level detail; agent audits |

---

## Implementation Priority

1. **High** (blocks agent control):
   - Split triage into signal-gathering + decision
   - Make doc requirements agent-driven, not tier-driven
   - Add dry-run modes to mutation tools

2. **Medium** (improves transparency):
   - Return source info for all signals
   - Document why decisions are made
   - Accept agent-provided configuration

3. **Low** (nice to have):
   - Custom doc patterns
   - Detailed file-level debug info
   - Schema version tracking

---

## References

- `/root/projects/Interverse/plugins/interkasten/server/src/sync/triage.ts` — Lines 72-101 (classification logic)
- `/root/projects/Interverse/plugins/interkasten/server/src/sync/key-docs.ts` — Lines 13, 38-76, 170-198
- `/root/projects/Interverse/plugins/interkasten/server/src/daemon/tools/init.ts` — Lines 140-298, 397-418
- `/root/projects/Interverse/plugins/interkasten/server/src/daemon/tools/projects.ts` — Lines 40-60, 200-225
- `/root/projects/Interverse/plugins/interkasten/skills/onboard/SKILL.md` — Lines 15-46
