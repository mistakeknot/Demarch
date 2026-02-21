# Wave 1: Autarch Solution Docs Classification Summary

Reviewed 14 solution docs from `hub/autarch/docs/solutions/`. None of the lessons are currently present in autarch's CLAUDE.md, AGENTS.md, or root MEMORY.md.

## Action Breakdown

- **claude_md (6 docs):** The most impactful category. Six docs contain rules that should be enforced on every session: pointer escape / deep-copy concurrency pattern, ANSI-aware string ops, Bubble Tea message routing (never swallow child messages), WindowSizeMsg chrome subtraction, dimension mismatch prevention, and reproduce-before-planning workflow discipline.
- **agents_md (4 docs):** Phase ordering rationale, chat-first TUI design principles, Oracle review patterns (phase constants, focus routing, error observability), and shell focus state as source of truth for key/mouse routing.
- **none (2 docs):** Spec propagation consistency and PRD blank generation are well-contained bug fixes with no broader lesson needing propagation.
- **prune (1 doc):** "Preserve Original Intent" duplicates an existing global skill and workflow-patterns.md entry.
- **memory (1 doc):** Import-cycle adapter pattern from arbiter-spec-sprint is a Go architectural lesson worth recording.

## Top Findings

1. **Autarch CLAUDE.md is underutilized.** It has zero TUI rules or concurrency guidelines despite 5 UI bug docs and a major concurrency fix. Six high-value rules should be added.
2. **9 of 14 docs are cross-cutting** -- their lessons apply beyond autarch (to any Bubble Tea TUI, any Go concurrent state, any agent workflow). Consider propagating the strongest to root MEMORY.md.
3. **The over-planning anti-pattern** (doc 14) is a workflow discipline issue that should be in CLAUDE.md to prevent recurrence by any agent working in this repo.
4. **No overlap found** between these 14 docs and existing MEMORY.md entries, which focus on Clavain/intercore/shell patterns rather than TUI or Go concurrency.
