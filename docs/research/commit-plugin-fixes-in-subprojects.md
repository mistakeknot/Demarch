# Commit plugin.json Fixes Across Interverse Subprojects

**Date:** 2026-02-23
**Task:** Remove redundant `hooks` declaration (and in interflux, `agentCapabilities`) from `.claude-plugin/plugin.json` across 14 Interverse subprojects.

## Background

Each Interverse plugin subproject has its own `.git` directory and is independently versioned. The `plugin.json` files contained a redundant `"hooks": "./hooks/hooks.json"` line that needed removal. In `interflux`, an additional unrecognized `agentCapabilities` key (84 lines) was also removed.

## Pre-Commit Analysis

All 14 targeted subprojects had `.claude-plugin/plugin.json` in their `git diff --name-only` output, confirming the changes were present. Several subprojects also had other unrelated modifications that were intentionally NOT staged or committed.

### Subprojects with only plugin.json changes:
- interline
- interject
- tool-time
- interlearn

### Subprojects with additional unstaged changes (left uncommitted):
- **interserve** — `cmd/interserve-mcp/main.go`, research docs
- **intersynth** — codex dispatch plan doc
- **interflux** — `.clavain/interspect/interspect.db`, research docs, skill files
- **intermem** — test files (`test_citations.py`, `test_scanner.py`)
- **interlock** — research/design docs
- **interfluence** — `.clavain/interspect/interspect.db`
- **interstat** — `uv.lock`
- **intermux** — Go source files (`models.go`, `watcher.go`)
- **intercheck** — `.clavain/interspect/interspect.db`
- **interkasten** — plan docs, test files, skill files

## Commit Results

All 14 commits succeeded. Each commit only staged `.claude-plugin/plugin.json` — no other files were included.

| Subproject | Commit Hash | Message | Lines Changed |
|---|---|---|---|
| interserve | `7a2d245` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| interline | `23838e2` | fix: remove redundant hooks declaration from plugin.json | -1 |
| intersynth | `9e40d45` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| interject | `2858344` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| tool-time | `99f2da8` | fix: remove redundant hooks declaration from plugin.json | -1 |
| intermem | `962afb2` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| interlock | `84f9507` | fix: remove redundant hooks declaration from plugin.json | -1 |
| interfluence | `feb0b25` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| interstat | `c9286fd` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| interlearn | `08c8986` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| intermux | `7c39057` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| intercheck | `9231ef8` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| interkasten | `7021568` | fix: remove redundant hooks declaration from plugin.json | +1 -2 |
| **interflux** | `55a2388` | fix: remove redundant hooks declaration and unrecognized agentCapabilities key | +1 -84 |

## Notes

- The `+1 -2` pattern (11 repos) means the hooks line was removed and an adjacent trailing comma was cleaned up.
- The `-1` pattern (3 repos: interline, tool-time, interlock) means only the hooks line was removed with no comma adjustment needed.
- interflux had the largest change at +1 -84, reflecting removal of the entire `agentCapabilities` object (83 lines) plus the hooks line.
- tool-time emitted a warning (`could not export to JSONL: exit status 1`) from a pre-commit hook but the commit still succeeded.
- No pushes to remote were performed. All changes are local only.
- All commit messages include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`.
