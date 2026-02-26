# Context File Audit — CLAUDE.md & AGENTS.md

> Based on [arxiv.org/abs/2602.11988](https://arxiv.org/abs/2602.11988) ("Evaluating AGENTS.md", Gloaguen et al. 2026)
> Created: 2026-02-26 | Bead: iv-7mk87

## Paper's Key Findings

1. Context files **increase cost by +20%** and **reduce task success by 0.5–2%** for LLM-generated files
2. **Codebase overviews** are the primary offender — encourage broad exploration without accelerating file discovery
3. **Tool instructions** (specific commands, tools to use) DO work — 1.6× adoption when mentioned
4. **Constraints** (naming rules, security boundaries) were NOT measured by the paper
5. Context files help in **doc-poor repos** (+2.7%) but hurt in well-documented ones

## Classification Categories

| Category | Paper Verdict | Keep? | Rationale |
|----------|--------------|-------|-----------|
| **Constraint** | Not measured | **YES** | Naming conventions, security rules, design decisions — model would get these wrong without them |
| **Tool instruction** | Helps (1.6×) | **YES** | Build commands, test commands, publish workflows |
| **Codebase overview** | Hurts (-2%) | **TRIM** | Directory trees, component descriptions — agents have Glob/Grep/tldr-swinton |
| **Historical context** | Not measured | **MOVE** | Design rationale, past decisions — useful but may induce over-exploration |
| **Redundant content** | Hurts most | **REMOVE** | Content duplicated across CLAUDE.md, AGENTS.md, README.md, MEMORY.md |

---

## Inventory Summary

| Layer | CLAUDE.md files | AGENTS.md files | Total words |
|-------|----------------|-----------------|-------------|
| Global (`~/.claude/`) | 1 (1,068w) | 1 (1,680w) | 2,748 |
| Root (Demarch/) | 1 (826w) | 1 (3,119w) | 3,945 |
| Subprojects | 56 | 50 | ~66,000 |
| Auto-memory | — | — | 3,288 |
| **Total** | **58** | **52** | **~76,000** |

The paper's average developer context file was **641 words**. Our root AGENTS.md alone is 5× that.

---

## Root CLAUDE.md (826 words) — Audit

| Lines | Section | Category | Verdict | Words |
|-------|---------|----------|---------|-------|
| 1–3 | Title + description | Overview | KEEP (2 lines) | 16 |
| 5–65 | **Structure (directory tree)** | **CODEBASE OVERVIEW** | **TRIM — largest offender** | 370 |
| 67–73 | Naming Convention | Constraint | KEEP | 68 |
| 75–81 | Git Workflow | Constraint | KEEP | 47 |
| 83–87 | Working in Subprojects | Tool instruction | KEEP | 31 |
| 89–97 | Plugin Publish Policy | Tool instruction | KEEP | 63 |
| 99–101 | Critical Patterns | Tool instruction | KEEP | 21 |
| 103–105 | Plugin Design Principle | Constraint | KEEP | 32 |
| 107–112 | Security: AGENTS.md Trust Boundary | Constraint | KEEP | 60 |
| 114–119 | Security: Memory Provenance | Constraint | KEEP | 25 |
| 121–127 | Design Decisions (Do Not Re-Ask) | Constraint | KEEP | 55 |

### Findings

**45% of the root CLAUDE.md is a directory tree listing 50+ items.** This is exactly the type of content the paper identifies as the worst offender — it encourages agents to explore broadly rather than search narrowly. The agent has Glob, Grep, intermap, and tldr-swinton for navigation. The tree provides zero information the agent couldn't get from `ls` in 1 second.

**Recommendation:** Replace the 60-line directory tree with a 3-line pointer:
```
## Structure
5 pillars: os/clavain/ (OS), interverse/ (42 plugins), core/ (kernel), apps/ (TUIs), sdk/ (shared).
Each subproject has its own CLAUDE.md and AGENTS.md. Use Glob/Grep to navigate.
```

Savings: ~350 words, ~44% of file.

---

## Root AGENTS.md (3,119 words) — Audit

| Lines | Section | Category | Verdict | Words |
|-------|---------|----------|---------|-------|
| 1–5 | Overview | Overview | KEEP (compact) | 85 |
| 7–14 | Agent Quickstart | Tool instruction | KEEP | 50 |
| 16–24 | Instruction Loading Order | Constraint | KEEP — important | 65 |
| 26–37 | Glossary | Overview | KEEP (defines jargon) | 105 |
| 39–99 | **Directory Layout (table)** | **CODEBASE OVERVIEW** | **TRIM — 50-row table** | 625 |
| 101–142 | **Module Relationships** | **CODEBASE OVERVIEW** | **TRIM — 40-line ASCII graph** | 310 |
| 144–158 | Bead Tracking + Roadmap | Tool instruction | KEEP | 110 |
| 159–165 | Naming Convention | Constraint | KEEP (duplicates CLAUDE.md) | 50 |
| 166–173 | Go Module Path Convention | Constraint | KEEP | 65 |
| 174–191 | Prerequisites | Tool instruction | KEEP | 115 |
| 192–256 | Development Workflow | Tool instruction | KEEP | 340 |
| 257–283 | Plugin Dev/Publish Gate | Constraint | KEEP | 175 |
| 284–338 | Cross-repo + Version Bumping | Tool instruction | KEEP | 285 |
| 340–356 | Critical Patterns | Constraint | KEEP — learned from failures | 165 |
| 358–387 | Compatibility + Landing the Plane | Constraint + Tool instruction | KEEP | 205 |
| 389–392 | Operational Notes reference | Pointer | KEEP | 18 |

### Findings

**30% of root AGENTS.md is codebase overview** (Directory Layout table + Module Relationships graph = ~935 words). This is the exact content type the paper says hurts performance.

The Directory Layout table (50 rows) duplicates information that:
- Is already in the CLAUDE.md directory tree (so double-loaded)
- Can be discovered by `ls -la` or Glob
- Is available in each subproject's own CLAUDE.md

The Module Relationships graph is more useful (dependency info isn't discoverable via Glob), but could be condensed.

**Naming Convention** appears in both CLAUDE.md and AGENTS.md — redundant.

**Landing the Plane** also appears in Clavain AGENTS.md — redundant for work within Clavain.

**Recommendations:**
1. Remove Directory Layout table (save ~625 words). Replace with: "See each module's CLAUDE.md. Use `ls apps/ core/ interverse/ os/ sdk/` for directory overview."
2. Condense Module Relationships to key dependency chains only (~5 lines instead of 40)
3. Remove duplicate Naming Convention (it's in CLAUDE.md, which is always loaded)
4. Total savings: ~700-900 words, ~25% of file

---

## Global ~/.claude/CLAUDE.md (1,068 words) — Audit

| Section | Category | Verdict |
|---------|----------|---------|
| Documentation Structure | Meta | KEEP (7 lines) |
| Project Documentation Requirements | Constraint | KEEP |
| Git Workflow | Constraint | KEEP |
| Tool Usage Preferences | Constraint | KEEP |
| Collaborative Brainstorming | Constraint | KEEP |
| Oracle | Tool instruction | KEEP |
| Continuous Learning → Project Memory | Constraint | KEEP |
| Persistent Task Tracking | Constraint | KEEP |
| Claude Code Plugin Development | Tool instruction | KEEP (pointers, not content) |
| Settings Hygiene | Constraint | KEEP — prevents real bugs |
| Workflow Patterns | Pointer | KEEP |
| Running as claude-user | Conditional | KEEP |

**Verdict: Clean.** The global CLAUDE.md is 100% constraints and tool instructions. No codebase overview content. Well-structured.

---

## Subproject CLAUDE.md — Pattern Analysis (8 sampled)

### Well-structured (constraint-heavy, minimal overview):
- **Clavain** (262w): Pure constraints + quick commands. No directory tree. A+
- **interflux** (289w): Design decisions + quick commands. No directory tree. A+
- **intermap** (293w): Architecture + tool table + build commands. Compact. A
- **interpulse** (94w): Pure description + usage. Ideal. A+
- **intership** (72w): Pure function description. Ideal. A+
- **intertree** (113w): Clean overview + decisions. A

### Needs trimming (overview-heavy):
- **intercore** (1,197w): **54% is CLI quick reference** that duplicates the AGENTS.md command listing. The 8 "Quick Reference" sections (~650 words) repeat what's in the AGENTS.md. Remove from CLAUDE.md, keep only in AGENTS.md.
- **interkasten** (754w): **Architecture tree + 21-row MCP tool table** = overview. The tool table is useful but better suited for AGENTS.md. CLAUDE.md should have just build commands + design decisions.
- **autarch** (757w): **Key Paths table + Workflow Discipline** are valuable constraints. But Quick Commands section is large (200w). Acceptable.
- **interbase** (424w): SDK documentation (Go SDK, Python SDK details) is overview content better in AGENTS.md.
- **tldr-swinton** (452w): Plugin structure tree + publishing runbook. Structure tree is overview; runbook is tool instruction (keep).

---

## Subproject AGENTS.md — Pattern Analysis (3 sampled)

### Intercore AGENTS.md (2,864 words)
- Excellent comprehensive reference. CLI command tables are the RIGHT place for this content.
- Architecture tree (lines 17–61) is overview but valuable — developers need to understand 20+ internal packages.
- The full CLI command listing is tool instruction — KEEP.
- **Issue:** 100% duplicated in CLAUDE.md's quick reference sections. Fix: strip CLAUDE.md, keep AGENTS.md as single source.

### Clavain AGENTS.md (3,003 words)
- Architecture tree (lines 42–134) = **450 words of directory listing**. This is overview content.
- Component conventions (lines 175–236) = **constraint** content. KEEP.
- Modpack tables (lines 316–377) = **tool instruction** (which plugins to install). KEEP.
- Landing the Plane (lines 419–444) = duplicated from root AGENTS.md. REMOVE.
- **Recommendation:** Compress architecture tree to top-level only (~10 lines instead of 90).

### Autarch AGENTS.md (2,176 words)
- Architecture section (lines 50–89) with directory tree = overview. Could compress.
- Shared packages table (lines 91–118) = 28-row table. Useful but discoverable.
- Integration diagram (lines 249–270) = overview. Unique info (data flow) but verbose.
- Arbiter Spec Sprint (lines 296–334) = tool instruction. KEEP.
- **Most overhead is in package tables** that `go doc` or tldrs can provide.

---

## Auto-Memory MEMORY.md (3,288 words, 246 lines)

**Over the 200-line limit.** Only first 200 lines are loaded, so 46 lines of content are silently truncated.

Content breakdown:
- **Autarch patterns** (~150 lines): Detailed architecture notes, Bubble Tea gotchas, build workarounds
- **Intercore patterns** (~40 lines): Coordination, publish subsystem, seam tests
- **Interspect/Clavain bash** (~20 lines): Accumulation patterns, flock protocol
- **Shell portability** (~15 lines): Portable regex, Go build safety
- **Interverse conventions** (~10 lines): Plugin patterns
- **Intercom** (~10 lines): Container rebuild rules

**70% of MEMORY.md is Autarch-specific.** This is classic "exploration noise" — when working on interflux or interkasten, 150 lines of Bubble Tea threading model notes are pure noise.

**Recommendation:** Extract to topic files immediately:
- `autarch-learnings.md` (already referenced but apparently not fully extracted)
- `intercore-learnings.md`
- Keep MEMORY.md as a 50-line index with links

---

## Redundancy Map

Content that appears in multiple files:

| Content | Appears In | Fix |
|---------|-----------|-----|
| Directory tree / structure | Root CLAUDE.md, Root AGENTS.md | Keep in AGENTS.md only (condensed) |
| Naming convention | Root CLAUDE.md, Root AGENTS.md | Keep in CLAUDE.md only |
| Landing the Plane | Root AGENTS.md, Clavain AGENTS.md | Keep in root AGENTS.md only |
| Plugin publish workflow | Root CLAUDE.md, Root AGENTS.md, Clavain AGENTS.md, each plugin CLAUDE.md | Root CLAUDE.md is authoritative; others should point there |
| Design decisions | Root CLAUDE.md, Root AGENTS.md (partially) | Keep in CLAUDE.md only |
| CLI command reference | Intercore CLAUDE.md, Intercore AGENTS.md | Keep in AGENTS.md only |
| MCP tool listing | Interkasten CLAUDE.md, Interkasten AGENTS.md | Keep in AGENTS.md, reference from CLAUDE.md |

---

## Scoring: Impact vs Effort

| Change | Words Saved | Risk | Effort |
|--------|-------------|------|--------|
| **Remove root CLAUDE.md directory tree** | ~350 | Low — agents have navigation tools | 5 min |
| **Remove root AGENTS.md directory layout table** | ~625 | Low — each module has its own docs | 10 min |
| **Condense root AGENTS.md module relationships** | ~250 | Medium — dependency info has value | 15 min |
| **Strip Intercore CLAUDE.md CLI duplication** | ~650 | Low — content stays in AGENTS.md | 10 min |
| **Compress Clavain AGENTS.md architecture tree** | ~350 | Low — top-level structure is enough | 10 min |
| **Fix MEMORY.md overflow** | ~0 (reorganize) | Low — data moves, not deleted | 20 min |
| **Remove cross-file redundancies** | ~200 | Low — keep single source | 15 min |
| **TOTAL** | **~2,425** | | ~85 min |

**Estimated token savings per session:** ~2,425 words ≈ ~3,200 tokens of context no longer processed on every turn. At our usage volume, this compounds significantly.

---

## Recommendations (Prioritized)

### P0 — Do Now (high impact, low risk)
1. **Remove the 60-line directory tree from root CLAUDE.md.** Replace with 3-line summary.
2. **Remove the 50-row directory layout table from root AGENTS.md.** Replace with pointer to `ls` and module docs.
3. **Fix MEMORY.md overflow** — extract Autarch content to topic file.

### P1 — Do Soon (moderate impact)
4. Condense Module Relationships graph in root AGENTS.md to 5 key dependency chains.
5. Strip CLI quick reference duplication from Intercore CLAUDE.md.
6. Compress Clavain AGENTS.md architecture tree to top-level only.

### P2 — Do When Touching These Files
7. Remove Landing the Plane duplication from Clavain AGENTS.md.
8. Remove Naming Convention duplication from root AGENTS.md.
9. Move MCP tool table from interkasten CLAUDE.md to AGENTS.md only.

### P3 — Experiment (design bead iv-0q6zu)
10. Run controlled experiment with 5 tasks to measure actual cost/quality impact.
