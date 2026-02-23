# Plan: Plugin Publishing Structural Validation
**Bead:** iv-pxid
**Phase:** planned (as of 2026-02-23T07:26:44Z)
**Date:** 2026-02-22

## Scope Update

Re-audit of source repos (not cached versions) shows most feature declaration issues are **already fixed**. Remaining work:

1. **validate-plugin.sh** — prevent regressions (interbump already has the gate wired at line 109-118)
2. **interject version mismatch** — marketplace=0.1.6, source=0.1.7
3. **Cache cleanup script**
4. **Close already-done subtasks** (iv-pxid.3, iv-pxid.4, iv-pxid.5 are largely resolved)

## Tasks

### Task 1: Create validate-plugin.sh [iv-pxid.1]
**File:** `scripts/validate-plugin.sh`
**Time:** ~30 min

Checks (all hard errors):
1. **Undeclared hooks** — `hooks/hooks.json` exists → `"hooks"` key must exist in plugin.json
2. **Undeclared skills** — `skills/*/SKILL.md` on disk → must appear in `"skills"` array
3. **Undeclared commands** — `commands/*.md` on disk → must appear in `"commands"` array
4. **Undeclared agents** — `agents/*.md` on disk → must appear in `"agents"` array
5. **hooks.json structure** — must have `"hooks"` top-level key
6. **Secret scanning** — env blocks must not contain literal UUID patterns
7. **Declared files exist** — every path in plugin.json must resolve to a real file

Interface:
```bash
scripts/validate-plugin.sh [plugin-dir]  # defaults to .
# Exit 0 = valid, Exit 1 = errors
# --quiet flag for CI (suppress passing checks)
```

Run against all 33 plugins as a smoke test after creating.

### Task 2: Fix interject marketplace version [iv-pxid.5]
**Time:** ~2 min

Bump interject in marketplace.json from 0.1.6 to 0.1.7, commit, push.

### Task 3: Cache cleanup script [iv-pxid.6]
**File:** `scripts/clean-plugin-cache.sh`
**Time:** ~10 min

For each plugin in `~/.claude/plugins/cache/interagency-marketplace/`:
- Keep only the latest version directory (highest semver)
- Delete all others
- Report what was cleaned

### Task 4: Close resolved subtasks
**Time:** ~2 min

- Close iv-pxid.2 (interbump gate already wired at line 109-118)
- Close iv-pxid.3 (all 14 hooks already declared in source)
- Close iv-pxid.4 (all 7 zero-feature plugins already fixed in source)
- Update iv-pxid.5 notes (only interject marketplace bump remains)

## Execution Order

1 → 2 → 3 → 4 (sequential, each is fast)

## Success Criteria

- `validate-plugin.sh` passes for all 33 plugins
- No version mismatches between source and marketplace
- Cache contains only latest version per plugin
