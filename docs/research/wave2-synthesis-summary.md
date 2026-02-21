# Wave 2 Synthesis: Solution Doc Triage

74 solution docs reviewed by 4 agents. 30 actionable, 22 already covered, 8 prune candidates, 22 fine as-is.

## Highest-Impact Actions (P0)

1. **`~/.claude/CLAUDE.md` Oracle section** -- add `--write-output <path>` and `--timeout` rules. Current docs say `--wait` but omit these, causing silent output loss in browser mode.
2. **`hub/autarch/CLAUDE.md`** -- add Go concurrency rule (never return pointers to mutable state; use `Clone()` + `-race` flag) and Bubble Tea message routing rule (never swallow child messages in parent `Update()`).
3. **`docs/guides/data-integrity-patterns.md`** -- add silent `_ = json.Marshal/Unmarshal` rule (fail hard on writes, log+continue on reads, grep for `_ = json.` as CI check).
4. **MEMORY.md** -- add Bash tool background mode corruption warning (`run_in_background: true` corrupts multi-flag args; use foreground with timeout instead).

## Bulk Additions

- **MEMORY.md gets 15 new entries**: 8 plugin lifecycle lessons, 3 intercore patterns, 2 monorepo/workflow patterns, 1 Python gotcha, 1 Go architecture pattern.
- **`hub/autarch/CLAUDE.md` gets 6 rules**: concurrency, Bubble Tea routing, ANSI string ops, layout sizing, and reproduce-before-planning workflow.
- **`hub/autarch/AGENTS.md` gets 4 sections**: TUI design principles, Oracle review patterns, input routing, spec phase ordering.

## Guide Updates (4 files)

| Guide | New Sections |
|-------|-------------|
| `plugin-troubleshooting.md` | Ghost plugin entries from renames |
| `shell-and-tooling-patterns.md` | awk `sub()` $0 mutation, beads daemon stale startlock |
| `multi-agent-coordination.md` | Advisory-only enforcement pattern, post-parallel quality gates |
| `data-integrity-patterns.md` | Silent JSON errors in Go |

## Prune Candidates (8 docs)

- **Delete** (2): `disable-model-invocation-blocks-skill-tool` (superseded by broader LFG pipeline doc), `preserve-original-intent` (duplicates global skill).
- **Keep as historical** (6): B1 config resolution, settings heredoc bloat, two plugin incident reports, E8 portfolio, E9 dependency scheduling. All fully propagated to guides/MEMORY.md but useful as incident records.

## Cross-Cutting Themes (highest value)

1. **Plugin lifecycle gaps** (8 docs) -- cache, session registry, marketplace sync, ghost entries. Systemic platform limitation, not one-off bugs.
2. **TOCTOU/CAS patterns** (3 docs) -- tx-wrapped gates, CAS spawn-link-orphan, advisory-only observers. Three distinct patterns for the same class of bug.
3. **Bubble Tea TUI rules** (6 docs) -- message routing, layout sizing, ANSI ops, focus state. Form a coherent rule set for autarch CLAUDE.md.
4. **LLM output reliability** (2 docs) -- provenance tracking prevents compounding echoes; unified diffs catch cross-cutting schema bugs.
5. **Silent failure patterns** (2 docs) -- discarded JSON errors and guard fallthrough. Both need fail-closed discipline.
6. **Go concurrency safety** (2 docs) -- Clone() for cross-goroutine types, import-cycle adapters. Apply to any Go project.

## Execution Order

1. P0 items first (4 changes, prevents data loss / silent failures)
2. MEMORY.md bulk (15 entries, prevents re-investigation)
3. autarch CLAUDE.md (6 rules, prevents TUI/concurrency bug recurrence)
4. Guide updates (4 files, improves discoverability)
5. autarch AGENTS.md + clavain AGENTS.md (5 sections, documentation quality)
6. Prune 2 superseded docs
