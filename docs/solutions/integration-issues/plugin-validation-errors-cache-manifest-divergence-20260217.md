---
module: System
date: 2026-02-17
problem_type: integration_issue
component: tooling
symptoms:
  - "interflux Plugin 1 error — missing skills/commands/agents in plugin.json manifest"
  - "interject Plugin 2 errors — stale hooks.json format in cache"
  - "interkasten Plugin 4 errors — missing skills/ directory in cache + invalid Setup hook event"
  - "interserve Plugin 1 error — unresolved"
root_cause: incomplete_setup
resolution_type: config_change
severity: high
tags: [claude-code, plugin, cache-divergence, hooks-format, manifest, orphaned-at, hook-event-types]
---

# Plugin Validation Errors: Cache/Manifest Divergence (4 Plugins)

## Problem

Four plugins showed errors in Claude Code's `/plugin` output despite their MCP servers connecting successfully. Each error had a distinct root cause related to cache staleness, manifest incompleteness, or invalid hook configuration.

## Environment

- Module: Interverse monorepo (interflux, interject, interkasten, interserve)
- Claude Code: latest (Feb 2026)
- Plugin cache: `/home/mk/.claude/plugins/cache/interagency-marketplace/`
- Date: 2026-02-17

## Symptoms

| Plugin | Error Count | MCP Status |
|--------|-------------|------------|
| interflux | 1 | qmd + exa connected |
| interject | 2 | interject connected |
| interkasten | 4 | (no MCP declared) |
| interserve | 1 | interserve connected |

All MCP servers were healthy — errors were at the plugin manifest/hooks/skills level.

## Investigation

### Phase 1: Evidence Gathering

Systematically compared **source repos** vs **plugin cache** for each plugin:

1. Read `plugin.json` from source AND cache
2. Read `hooks/hooks.json` from source AND cache
3. Verified all declared skill/command/agent files exist in cache
4. Checked for `.orphaned_at` markers
5. Compared `installed_plugins.json` versions against cache directory names

### Phase 2: Root Causes Found

**interflux (1 error):** `plugin.json` had no `"skills"`, `"commands"`, or `"agents"` arrays, despite description text claiming "17 agents, 3 commands, 2 skills". Claude Code validates manifest declarations against described capabilities.

**interject (2 errors):** Cache at v0.1.4 had **stale `hooks.json`** using the wrong format (flat array with `"type"` field). The source repo had already been fixed to use the correct event-key object format, but the cache was cloned from an older commit at the same version number. Additionally, an `.orphaned_at` marker in the old v0.1.2 cache dir.

**interkasten (4 errors):** Cache at v0.4.0 was **missing the entire `skills/` directory** — 3 declared skill files not found (3 errors). The `hooks.json` used `"Setup"` as a hook event type, which is **not a valid Claude Code hook event** (1 error). Valid events: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `SessionEnd`.

**interserve (1 error):** All files, formats, and binaries structurally correct. Root cause not determined with certainty. Possible causes: hardcoded absolute path in `INTERSERVE_DISPATCH_PATH` env var, or a validation edge case in hook registration.

## Solution

### Fix 1: interflux — Declare Manifest Arrays

Added `skills`, `commands`, and `agents` arrays to `.claude-plugin/plugin.json`:

```json
"skills": [
  "./skills/flux-drive",
  "./skills/flux-research"
],
"commands": [
  "./commands/flux-drive.md",
  "./commands/flux-research.md",
  "./commands/flux-gen.md"
],
"agents": [
  "./agents/review/fd-architecture.md",
  // ... 12 review + 5 research + 1 reference = 18 entries
]
```

Committed, pushed. Interbump auto-bumped to v0.2.13. New cache cloned with fix.

### Fix 2: interject — Update Stale Cache

Source already had correct `hooks.json`. Copied corrected version directly to cache:

```json
// Cache had (WRONG):
{ "hooks": [{ "type": "SessionStart", "script": "..." }] }

// Replaced with (CORRECT — matches source):
{ "hooks": { "SessionStart": [{ "matcher": "", "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh" }] }] } }
```

### Fix 3: interkasten — Copy Skills + Fix Hook Event

1. Copied `skills/` directory from source to cache (3 SKILL.md files)
2. Replaced invalid `"Setup"` hook event with `"SessionStart"`, merging `setup.sh` into the SessionStart array (runs first with 30s timeout, already idempotent):

```json
// Before (WRONG — "Setup" not a valid event):
{ "Setup": [{ "hooks": [{ "command": "setup.sh", "timeout": 30 }] }],
  "SessionStart": [{ "hooks": [{ "command": "session-status.sh" }] }] }

// After (setup.sh merged into SessionStart):
{ "SessionStart": [{ "hooks": [
    { "command": "setup.sh", "timeout": 30 },
    { "command": "session-status.sh", "timeout": 5 }
  ] }] }
```

Committed, pushed. Interbump auto-bumped to v0.4.1. Copied fix to cache.

### Bonus: Mass Orphan Cleanup

Removed 29 `.orphaned_at` markers across all marketplace plugin cache dirs (stale markers from old versions).

```bash
find ~/.claude/plugins/cache/interagency-marketplace \
  -maxdepth 4 -name ".orphaned_at" \
  -not -path "*/temp_git_*" -delete
```

## Why This Works

**Cache divergence pattern:** `claude plugins install` does a shallow `git clone` at the commit matching the marketplace version tag. If the plugin author pushes fixes without bumping the version number, or if the clone is incomplete (missing directories due to shallow clone or sparse checkout), the cache becomes permanently stale. The `gitCommitSha` in `installed_plugins.json` is frozen at install time.

**Three independent failure modes:**

1. **Manifest omission** (interflux): `plugin.json` must explicitly declare all capabilities — Claude Code doesn't discover skills/agents/commands by convention alone; it validates declared vs described.

2. **Cache staleness** (interject): Source repo was fixed but cache retained the pre-fix commit. Same version number, different content. The `gitCommitSha` field doesn't trigger re-cloning.

3. **Invalid hook events** (interkasten): Claude Code silently ignores unknown hook event types. `"Setup"` was never valid — the 14 valid events are: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `SessionEnd`.

## Prevention

- **Always bump version** when fixing any plugin file (hooks, skills, manifest). Use `scripts/bump-version.sh <version>` or `/interpub:release`. Same version + different content = permanent cache divergence.
- **Validate hook event types** against the 14-event allowlist before committing hooks.json. Invalid events are silently ignored — no error at source, only at plugin load time.
- **Declare all capabilities** in `plugin.json` manifest. If the description mentions "N agents, M skills", the manifest must have matching arrays.
- **Periodic cache audit**: Compare `gitCommitSha` in `installed_plugins.json` against each source repo's HEAD. Drift means cache is stale.
- **Test with fresh clone**: After any hooks/manifest change, delete the cache dir and reinstall to verify the plugin loads cleanly from scratch.

## Diagnostic Quick Reference

When `/plugin` shows errors but MCP shows "connected":

1. **Read cache `plugin.json`** — are all skills/commands/agents declared?
2. **Compare cache `hooks.json` vs source** — format drift? (event-key objects, not arrays)
3. **Verify skill files exist in cache** — `ls cache/<version>/skills/*/SKILL.md`
4. **Check hook event names** — are they in the 14-event allowlist?
5. **Check `.orphaned_at` markers** — `find cache/ -name ".orphaned_at"`

## Related Issues

- [plugin-loading-failures-interverse-20260215.md](plugin-loading-failures-interverse-20260215.md) — Previous round of plugin failures (same patterns: hooks format, orphaned markers, missing binaries)
