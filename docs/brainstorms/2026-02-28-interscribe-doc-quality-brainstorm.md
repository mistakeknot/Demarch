# Interscribe: Documentation Quality & Progressive Disclosure

**Date:** 2026-02-28
**Status:** Brainstorm
**Module:** interverse/interscribe (new)

## Problem Statement

CLAUDE.md and AGENTS.md files are monolithic accumulators. They grow every time something is learned but never get restructured. Project knowledge leaks into CLAUDE.md (which should be Claude Code config only). Duplicate instructions appear across the loading hierarchy. No tool enforces the boundary between tool config and project knowledge, or applies progressive disclosure to project docs.

The existing tooling is strong at **generation and capture** but has no coverage for **restructuring**:
- interdoc generates AGENTS.md from code (bottom-up)
- interwatch detects drift and triggers regeneration
- intermem:synthesize promotes memory → docs
- /review-doc does single-pass quality scoring
- /distill applies progressive disclosure to skills (SKILL.md → SKILL-compact.md)

**Gap:** Nothing restructures, modularizes, or enforces boundaries on CLAUDE.md/AGENTS.md.

## Design Decisions

### Boundary Rule (The Core Insight)

```
CLAUDE.md    → Claude Code only: plugins, hooks, tool preferences, permissions
AGENTS.md    → Everything else: architecture, workflows, conventions, standards
  → docs/    → Deep reference files linked from AGENTS.md sections
```

Any project knowledge in CLAUDE.md is a violation. Interscribe detects and moves it.

### Architecture
- **Skill-only plugin** — no compiled MCP server. Analysis done by LLM reading files + shell scripts for metrics.
- **General-purpose from day 1** — designed for any project's CLAUDE.md/AGENTS.md, not Demarch-specific.
- **Fully automatic** by default — applies all changes, user reviews via git diff. Trust the tool.

### Standards Location
- The doc-structure standard (pointer-doc convention, token budgets, boundary rules) lives in `docs/canon/doc-structure.md` in each project.
- `docs/canon/` holds PHILOSOPHY.md + standards. Operational docs (CLAUDE.md, AGENTS.md) stay at root.
- Interscribe reads and enforces the standard; it doesn't own the file location.

## Three Modes

### 1. Audit — "How healthy are these docs?"

Input: Project root (or specific files)
Output: Report with scores and actionable findings

Checks:
- **Boundary violations**: Project knowledge in CLAUDE.md (should be in AGENTS.md)
- **Token budget**: How much context do these docs consume at session start?
- **Duplication**: Same instruction in multiple files across the hierarchy
- **Staleness**: References to deleted files, renamed modules, old patterns
- **Depth violations**: AGENTS.md sections that are too deep (should be pointer → docs/)
- **Missing pointers**: Large AGENTS.md sections without deep reference docs

### 2. Refactor — "Restructure these docs"

Input: Project root (or specific files)
Output: Modified files (fully automatic, reviewable via git diff)

Actions:
- Move project knowledge from CLAUDE.md → AGENTS.md
- Extract deep AGENTS.md sections → docs/ reference files with backlinks
- Add pointer links where content was extracted
- Remove duplicates (keep canonical location, add pointer from others)
- Fix broken internal links
- Enforce line budgets (CLAUDE.md: ~30-60 lines, AGENTS.md sections: reasonable)

### 3. Consolidate — "Deduplicate across hierarchy"

Input: Multiple docs in a loading hierarchy (global → project → subproject)
Output: Deduplication report + moves

Checks:
- Same instruction at multiple levels → keep at highest common ancestor
- Contradictions between levels → flag for resolution
- Subproject docs that repeat project-level conventions → remove, add pointer

## Integration Points

| Tool | Relationship |
|------|-------------|
| interdoc | Interscribe refactors what interdoc generates. interdoc generates AGENTS.md from code; interscribe restructures it for optimal consumption. |
| interwatch | Interwatch could trigger interscribe:audit when docs grow past thresholds. New signal type: "structural drift." |
| /review-doc | Review-doc scores content quality. Interscribe scores structural quality. Complementary, not overlapping. |
| /distill | Distill handles SKILL.md progressive disclosure. Interscribe handles CLAUDE.md/AGENTS.md progressive disclosure. Same pattern, different targets. |
| docs/canon/doc-structure.md | Interscribe enforces this standard. The standard is the source of truth; interscribe is the enforcement tool. |

## docs/canon/ Convention

Applies to all repos in the ecosystem:

```
docs/canon/
├── PHILOSOPHY.md      # Design bets and tradeoffs (moved from root)
├── doc-structure.md   # Pointer-doc standard, token budgets, boundary rules (NEW)
└── naming.md          # Naming conventions (moved from docs/guides/)
```

Root keeps: CLAUDE.md, AGENTS.md (operational, auto-loaded).

## Plugin Structure

```
interverse/interscribe/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── interscribe/
│       └── SKILL.md          # Main skill (audit, refactor, consolidate modes)
├── scripts/
│   ├── audit-docs.sh         # Token counting, boundary checking
│   └── find-duplicates.sh    # Cross-file duplication detection
├── CLAUDE.md
├── AGENTS.md
└── README.md
```

## Open Questions

1. Should interscribe also handle MEMORY.md optimization (it has a 200-line soft cap)?
2. Should `docs/canon/` migration be an interscribe mode, or a separate one-time script?
3. How does interscribe interact with `.codex/AGENTS.md` (Codex CLI's equivalent)?

## Alignment

**Philosophy alignment:** Interscribe directly serves "Documentation is agent memory" (PHILOSOPHY.md §Receipts Close Loops). Better-structured docs → better agent decisions → faster flywheel.

**Conflict/Risk:** Fully automatic mode means interscribe can make mistakes that silently degrade doc quality. Mitigated by git-reviewable changes and the trust ladder (can dial back to conservative later).
