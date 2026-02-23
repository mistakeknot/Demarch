# PRD: Plugin Publishing Structural Validation
**Bead:** iv-pxid
**Date:** 2026-02-22
**Status:** Draft

## Problem

The plugin publishing pipeline (`interbump.sh`) validates version numbers but not plugin structure. This allowed 14 plugins to ship with hooks that Claude Code never loads, 7 plugins to ship with zero declared features despite having skills/commands on disk, and 3 plugins to drift out of version sync. One plugin ships a hardcoded API key.

## Solution

### Feature 1: validate-plugin.sh (iv-pxid.1)

Standalone bash script in `scripts/` that validates plugin structure. Must run in <1s, no Claude Code dependency.

**Checks:**
- **Undeclared hooks**: `hooks/hooks.json` exists on disk → must be declared in plugin.json. Hard error.
- **Undeclared skills**: `skills/*/SKILL.md` exists on disk → must be in `skills` array. Hard error.
- **Undeclared commands**: `commands/*.md` exists on disk → must be in `commands` array. Hard error.
- **Undeclared agents**: `agents/*.md` exists on disk → must be in `agents` array. Hard error.
- **hooks.json structure**: Must have top-level `"hooks"` key, not empty `{}`.
- **Secret scanning**: Env blocks in plugin.json must not contain literal UUIDs/keys (regex check).
- **Declared files exist**: Every path in plugin.json must resolve to a real file.

**Interface:**
```bash
scripts/validate-plugin.sh [plugin-dir]  # defaults to .
# Exit 0 = valid, Exit 1 = errors found (prints each error to stderr)
```

### Feature 2: interbump.sh integration (iv-pxid.2)

Add pre-publish gate call to `validate-plugin.sh` in interbump.sh. Runs before any version writes.
- `--skip-validation` flag for emergencies.

### Feature 3: Fix 14 undeclared hooks (iv-pxid.3)

For each of: intercheck, interfluence, interflux, interject, interkasten, interlearn, interline, interlock, intermem, intermux, interserve, interstat, tool-time:
- Add `"hooks": "./hooks/hooks.json"` to plugin.json
- Bump version via interbump
- Push both repos

### Feature 4: Fix 7 zero-feature plugins (iv-pxid.4)

For each plugin, add missing declarations to plugin.json:
- **interline**: 1 command (statusline-setup.md), hooks
- **interpath**: 1 skill (artifact-gen), 6 commands (changelog, prd, propagate, roadmap, status, vision)
- **interphase**: 1 skill (beads-workflow)
- **interwatch**: 1 skill (doc-watch), 3 commands (refresh, status, watch)
- **tool-time**: 2 skills (tool-time, tool-time-codex), hooks
- **tuivision**: 1 skill (tui-test)
- **interlock**: 2 skills (coordination-protocol, conflict-recovery) — already has MCP declared

Bump version and push for each.

### Feature 5: Fix version drift + security (iv-pxid.5)

- **interflux**: bump marketplace to 0.2.20
- **interlock**: bump marketplace to 0.2.2
- **interkasten**: bump plugin.json to 0.4.4
- **interject**: replace hardcoded EXA_API_KEY with `${EXA_API_KEY}` env var reference

### Feature 6: Cache cleanup (iv-pxid.6)

Script or interbump flag to prune all but latest version directory per plugin in `~/.claude/plugins/cache/interagency-marketplace/`.

## Execution Order

1. validate-plugin.sh (unblocks everything)
2. Fix undeclared hooks (14 plugins) — can parallelize
3. Fix zero-feature plugins (7 plugins) — can parallelize with #2
4. Wire validator into interbump
5. Fix version drift + security
6. Cache cleanup

## Success Criteria

- `validate-plugin.sh` passes for all 33 plugins after fixes
- interbump refuses to publish an invalid plugin
- All hooks/skills/commands load in Claude Code after session restart
