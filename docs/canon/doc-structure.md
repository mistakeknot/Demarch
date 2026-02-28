# Documentation Structure Standard

How project documentation is organized, layered, and loaded across the Demarch ecosystem. This is the standard that interscribe enforces.

## The Boundary Rule

```
CLAUDE.md    → Claude Code ONLY: plugins, hooks, tool preferences, permissions
AGENTS.md    → Everything else: architecture, workflows, conventions, troubleshooting
  → docs/    → Deep reference files linked from AGENTS.md sections
```

**Any project knowledge in CLAUDE.md is a boundary violation.** CLAUDE.md is loaded on every session start — wasted tokens there cost on every interaction.

### What belongs where

| Content type | Correct location | Wrong location |
|-------------|-----------------|----------------|
| Plugin settings, hook config | CLAUDE.md | AGENTS.md |
| Tool preferences (Read vs cat) | CLAUDE.md | AGENTS.md |
| Permission notes | CLAUDE.md | AGENTS.md |
| Architecture, module structure | AGENTS.md | CLAUDE.md |
| Git workflow, branch strategy | AGENTS.md | CLAUDE.md |
| Build/test instructions | AGENTS.md | CLAUDE.md |
| Coding conventions | AGENTS.md | CLAUDE.md |
| Troubleshooting guides | AGENTS.md | CLAUDE.md |
| Detailed API reference | docs/ (linked from AGENTS.md) | AGENTS.md inline |
| Protocol specifications | docs/ (linked from AGENTS.md) | AGENTS.md inline |

## Progressive Disclosure

Three tiers, each loaded at different times:

| Tier | File | When loaded | Token budget |
|------|------|------------|-------------|
| **Entry point** | CLAUDE.md | Every session start (auto-loaded) | 30-60 lines (hard cap: 80) |
| **Reference** | AGENTS.md | On demand when agent needs project context | No hard cap; sections should stay under 100 lines |
| **Deep reference** | docs/*.md | On demand when agent reads a specific topic | No cap |

### When to extract to docs/

An AGENTS.md section should be extracted to a docs/ reference file when:
- It exceeds 100 lines
- It's a detailed specification, protocol, or API reference
- It's only needed for specific tasks (not general project understanding)

When extracting, keep a 3-5 line summary in AGENTS.md with a pointer link to the full document.

## Loading Hierarchy

Claude Code loads docs in this order (each level can override or extend the previous):

```
~/.claude/CLAUDE.md          (global — applies to all projects)
  → project/CLAUDE.md        (project-level)
    → project/subdir/CLAUDE.md  (subproject-level)

project/AGENTS.md            (loaded on demand)
  → project/subdir/AGENTS.md    (loaded on demand)
```

### Deduplication rules

- **Identical instruction at multiple levels** → keep at the highest common ancestor, remove from lower levels
- **Specialized instruction** (lower level adds detail) → keep both; the lower level refines the higher
- **Contradictory instructions** → flag for manual resolution; do not silently override

## Line Budgets

| File | Target | Warning | Hard cap | Action when exceeded |
|------|--------|---------|----------|---------------------|
| CLAUDE.md | 30-60 | 60 | 80 | Move project knowledge → AGENTS.md |
| AGENTS.md section | 50-80 | 80 | 100 | Extract → docs/ with pointer |
| MEMORY.md | 100-150 | 150 | 200 | Promote stable facts → AGENTS.md via intermem:synthesize |

## docs/canon/

Foundational docs that define project identity and standards. Every project in the ecosystem should have:

```
docs/canon/
├── doc-structure.md      # This file — how docs are organized (interscribe enforces this)
├── plugin-standard.md    # Structural quality bar for Interverse plugins
└── naming.md             # Naming conventions (currently at docs/guides/naming-conventions.md)
```

Root keeps: CLAUDE.md, AGENTS.md (operational, auto-loaded). PHILOSOPHY.md stays at project root (auto-loaded by interdoc's philosophy alignment protocol).

## Enforcement

**interscribe** audits and enforces this standard:
- `interscribe audit` — reports violations, scores health A-F
- `interscribe refactor` — automatically restructures docs to comply
- `interscribe consolidate` — deduplicates across the loading hierarchy

**interdoc** generates AGENTS.md content. **interscribe** restructures it. **interwatch** detects when docs drift from this standard. They are complementary, not overlapping.
