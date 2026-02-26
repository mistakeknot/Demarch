# Interlearn Plugin Analysis — Documentation Gaps and Conventions

**Date:** 2026-02-23  
**Analyst:** Claude Code (read-only research)  
**Scope:** Interlearn plugin at `/home/mk/projects/Demarch/interverse/interlearn/`

---

## 1. What Interlearn Does

Interlearn is a **cross-repo institutional knowledge index** for the Interverse monorepo. It solves the problem: "We solved this before, but where did we document it?" by building a unified, searchable index of solution documentation scattered across 12+ repositories.

### Core Functionality

- **Index Building** (`/interlearn:index`): Scans all `docs/solutions/*.md` files across hub/, plugins/, services/, infra/, and root docs/. Parses YAML frontmatter (handles heterogeneous schemas: `category` vs `problem_type`, multiple date keys: `date`, `created`, `date_resolved`, `date_discovered`). Generates:
  - `docs/solutions/INDEX.md` — human-readable markdown, grouped by module
  - `docs/solutions/index.json` — machine-readable JSON, flat and by-module structures
  
- **Search** (`/interlearn:search <query>`): Two-phase lookup:
  - Phase 1: Structured search via index.json (title, tags, problem_type, module, path)
  - Phase 2: Full-text grep fallback if < 5 matches
  - Returns up to 10 results with summaries of top 3 matches
  
- **Audit** (`/interlearn:audit`): Checks whether closed beads have corresponding solution docs. Reports:
  - Total closed beads
  - Count with reflect artifacts
  - Count with solution docs
  - Coverage ratio
  - Knowledge gap beads (no reflect, no solution doc)

- **SessionEnd Hook**: Automatically refreshes the index when session ends (if in Interverse monorepo). Fire-and-forget, fail-open behavior.

### Architecture

- **1 skill** (3 sub-skills): `skills/interlearn/SKILL.md` with `/interlearn:index`, `/interlearn:search`, `/interlearn:audit` modes
- **1 hook** (SessionEnd): `hooks/session-end.sh` — background refresh trigger
- **1 indexer script**: `scripts/index-solutions.sh` — deterministic, repeatable index builder
- **0 agents, 0 commands, 0 MCP servers**
- **Shell-only implementation** — no Python, no daemon, no compiled binary

### Philosophy

- Path is canonical truth (filesystem grouping > frontmatter `module:`)
- No auto-commit — hooks write files, developers commit manually
- Fail-open behavior for hooks (never fail session teardown)
- Deterministic artifact generation (same input → identical output)
- Monorepo detection via 3 markers (`.beads/`, `plugins/`, `hub/`)

---

## 2. Existing Documentation

### Files Present

| File | Status | Purpose |
|------|--------|---------|
| `CLAUDE.md` | ✓ Present | Quick reference: overview, quick commands, design decisions (15 lines) |
| `README.md` | ✓ Present | User-facing introduction: what it is, how it works, getting started (69 lines) |
| `docs/interlearn-vision.md` | ✓ Present | Vision doc: core idea, current state, direction, design principles (35 lines) |
| `docs/interlearn-roadmap.md` | ✓ Present | Roadmap: now/next/later phases with bracketed task IDs (37 lines) |
| `docs/solutions/patterns/awk-sub-pattern-fallthrough-20260221.md` | ✓ Present | Example solution doc (internal learning, not indexed) |
| `.claude-plugin/plugin.json` | ✓ Present | Plugin manifest (version 0.1.0, 5 skills array) |
| `hooks/hooks.json` | ✓ Present | Hook registration (SessionEnd, 10s timeout) |
| `skills/interlearn/SKILL.md` | ✓ Present | Full skill definition with 3 sub-skills, principles, phase breakdown (74 lines) |
| `scripts/index-solutions.sh` | ✓ Present | Core indexer: frontmatter parsing, module derivation, JSON/MD generation (219 lines) |
| `scripts/bump-version.sh` | ✓ Present | Version bumping utility |
| `hooks/session-end.sh` | ✓ Present | SessionEnd hook handler (64 lines) |

### Documentation Quality Assessment

**Strong areas:**
- Vision and roadmap are clear and aligned
- SKILL.md is comprehensive with phase breakdown and principles
- Quick commands in CLAUDE.md are actionable
- Hook implementation is defensive (fail-open, guards, error handling)
- Frontmatter parsing handles heterogeneous schemas gracefully

**Gaps:**
- No `AGENTS.md` (comprehensive development guide) — **CRITICAL MISSING**
- No `docs/roadmap.json` (machine-readable roadmap) — **MISSING**
- No test/validation instructions
- No troubleshooting section in CLAUDE.md
- No example workflow or gotchas

---

## 3. What's Missing

### 3.1 AGENTS.md (Critical)

Interlearn lacks a comprehensive development guide. By convention, all Interverse plugins should have `AGENTS.md` that covers:

- **Architecture overview** (skills, hooks, scripts, state)
- **Component conventions** (skill layout, frontmatter, phase files)
- **Dependency declarations** (external tools: jq, awk, bash, bd CLI)
- **Testing strategy** (structural tests, integration tests, validation commands)
- **Development workflow** (edit, test, bump version, publish)
- **Validation checklist** (manifest check, syntax check, dependency verification)
- **Common gotchas** (frontmatter edge cases, monorepo detection, hook fail-open semantics)

**Reference examples:**
- `interwatch/AGENTS.md` — doc freshness monitoring (skill, commands, hooks structure)
- `interject/AGENTS.md` — discovery engine (MCP server, dependencies, testing)

**Key sections needed for interlearn:**
1. Plugin overview: 1 skill (3 modes), 1 hook, shell-only
2. Frontmatter schema tolerance (how heterogeneous keys are handled)
3. Index artifacts: INDEX.md (markdown) and index.json (format + example)
4. Hook fail-open guarantees and monorepo detection logic
5. Indexer script: scanning logic, exclusion patterns, module derivation
6. Testing: validate JSON, syntax check scripts, verify index.json format
7. Common issues: stale index, missing frontmatter fields, monorepo detection failure

---

### 3.2 docs/roadmap.json (Important)

Interlearn lacks machine-readable roadmap. By convention, Interverse plugins publish `docs/roadmap.json` for consumption by interpath and planning tools.

**Format reference** (from `interject/docs/roadmap.json`):

```json
{
  "module_summary": "Brief description of module purpose",
  "roadmap": {
    "now": [
      {"id": "UNIQUE-ID", "title": "Task title", "priority": "P1"}
    ],
    "next": [
      {"id": "UNIQUE-ID", "title": "Task title", "priority": "P2"}
    ],
    "later": []
  }
}
```

**For interlearn** (derived from `docs/interlearn-roadmap.md`):

```json
{
  "module_summary": "Cross-repo institutional knowledge index — indexes solution docs, enables unified search, audits reflect coverage",
  "roadmap": {
    "now": [
      {"id": "interlearn-now-doc-baseline", "title": "Establish canonical product artifacts for module roadmap and vision", "priority": "P1"},
      {"id": "interlearn-now-index-reliability", "title": "Harden indexing robustness for inconsistent frontmatter and malformed markdown", "priority": "P1"},
      {"id": "interlearn-now-audit-signal", "title": "Improve audit signal quality so reflect coverage gaps are high-confidence", "priority": "P1"}
    ],
    "next": [
      {"id": "interlearn-next-query-quality", "title": "Improve search ranking quality for practical debugging and implementation queries", "priority": "P2"},
      {"id": "interlearn-next-taxonomy", "title": "Refine metadata taxonomy across category, tags, and module attribution fields", "priority": "P2"},
      {"id": "interlearn-next-workflow-integration", "title": "Integrate stronger with review and planning workflows for proactive knowledge surfacing", "priority": "P2"}
    ],
    "later": [
      {"id": "interlearn-later-feedback-loop", "title": "Add feedback loops for low-value hits to iteratively improve ranking behavior", "priority": "P3"},
      {"id": "interlearn-later-impact-metrics", "title": "Track reuse impact metrics across modules and sprint cycles", "priority": "P3"},
      {"id": "interlearn-later-context-packaging", "title": "Package compact context bundles for downstream agents and tooling", "priority": "P3"}
    ]
  }
}
```

---

## 4. Interverse Plugin Conventions (Reference)

### Directory Structure (Standard)

```
plugin-name/
  .claude-plugin/
    plugin.json          # Plugin manifest
    integration.json     # (Optional) Integration config
  CLAUDE.md              # Quick reference (≤50 lines)
  AGENTS.md              # Full development guide (required)
  README.md              # User-facing intro
  docs/
    <name>-vision.md     # Vision document
    <name>-roadmap.md    # Markdown roadmap
    roadmap.json         # Machine-readable roadmap
    solutions/           # Solution docs (internal learning)
  skills/
    <skill-name>/
      SKILL.md           # Skill definition with frontmatter
      phases/            # (If complex) Phase breakdown
      references/        # (If needed) Reference materials
  commands/              # (If applicable)
    <cmd-name>.md
  hooks/
    hooks.json           # Hook registration
    <hook-handler>.sh    # Hook scripts
  scripts/
    bump-version.sh      # Version bumping
    <utility>.sh         # Other utilities
  tests/
    structural/          # (Recommended) Plugin structure validation
      test_structure.py
      test_skills.py
```

### CLAUDE.md Convention

Keep ≤50 lines. Include:
- 1-line description
- Overview (count: skills, hooks, agents, commands, servers)
- Quick commands (validation, testing, manifest check)
- Design decisions (don't re-ask these)

Example:
```markdown
# interlearn

Cross-repo institutional knowledge index for the Interverse monorepo.

## Overview

1 skill (3 sub-skills), 0 agents, 0 commands, 1 hook (SessionEnd). Companion plugin for interflux.

## Quick Commands

bash scripts/index-solutions.sh /root/projects/Interverse  # Rebuild index
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"  # Manifest check
jq . /root/projects/Interverse/docs/solutions/index.json  # Verify JSON index

## Design Decisions (Do Not Re-Ask)

- Shell-only — no Python, no MCP server, no compiled binary
- Index lives at Interverse root `docs/solutions/` (not per-subrepo)
- No auto-commit — hook writes files, developer commits when ready
- 3-marker monorepo detection (`.beads/ + plugins/ + hub/`) in hook
- Handles frontmatter heterogeneity: `category` vs `problem_type`, `date_resolved`/`created` vs `date`
```

### AGENTS.md Convention

Full development guide, typically 50-150 lines. Include:
- Architecture overview (components, layers, state)
- Component conventions (skill layout, hook structure, script patterns)
- Dependencies (external tools, libraries)
- Testing strategy (validation, integration tests)
- Development workflow (edit → test → bump → publish)
- Common gotchas (edge cases, failure modes)

---

## 5. Summary: Critical Gaps and Action Items

### Critical Gaps

1. **AGENTS.md missing** — No comprehensive development guide. Required for:
   - Documenting skill/hook/script architecture
   - Testing and validation procedures
   - Development workflow and version bumping
   - Common gotchas and troubleshooting

2. **roadmap.json missing** — No machine-readable roadmap for planning/interpath integration. Should convert `docs/interlearn-roadmap.md` to JSON format per convention.

### Documentation Status Matrix

| Item | Status | Notes |
|------|--------|-------|
| CLAUDE.md | ✓ | Good quality, quick reference |
| README.md | ✓ | User-focused, clear |
| Vision doc | ✓ | Clear direction |
| Markdown roadmap | ✓ | Detailed (now/next/later) |
| **AGENTS.md** | **✗ CRITICAL** | Missing dev guide |
| **roadmap.json** | **✗ MISSING** | Breaking integration |
| Plugin manifest | ✓ | Valid plugin.json |
| Skill definition | ✓ | Comprehensive SKILL.md |
| Hooks | ✓ | Defensive, fail-open |
| Scripts | ✓ | Well-commented |

### Quality Assessment

**Strengths:**
- Clear, actionable vision and roadmap
- Shell implementation is robust (fail-open semantics, monorepo detection)
- Frontmatter parsing handles schema heterogeneity gracefully
- Hook design prioritizes session stability over index freshness
- SKILL.md is well-structured with explicit phase breakdown

**Weaknesses:**
- Missing developer guide (AGENTS.md) — no testing section, no gotchas documented
- No machine-readable roadmap (roadmap.json) — breaks interpath integration
- Limited validation documentation
- No examples of index.json structure
- No troubleshooting guidance

---

## Conclusion

Interlearn is a well-architected, shell-first plugin with clear vision and solid implementation. It follows Interverse patterns for skills and hooks but is missing two critical documentation artifacts: **AGENTS.md** (development guide) and **roadmap.json** (machine-readable roadmap). These are standard for all Interverse plugins and necessary for cross-plugin integration, planning visibility, and developer onboarding.

**Next steps:** Create AGENTS.md and roadmap.json following Interverse conventions shown in section 4.
