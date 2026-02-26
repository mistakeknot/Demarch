# Brainstorm: Plugin Publishing Pipeline Overhaul

**Date:** 2026-02-25
**Status:** brainstorm-complete
**Scope:** Replace shell-based publish pipeline with Go-based `ic publish` in Intercore

---

## Problem Statement

The plugin publishing pipeline has accumulated significant technical debt:

- **Three divergent publish paths** (`interbump.sh`, `auto-publish.sh`, `/interpub:release`) with different behavior — the recommended skill path doesn't even update cache or `installed_plugins.json`
- **Up to 7 version locations** per plugin, all of which must agree: `plugin.json`, `pyproject.toml`, `package.json`, `agent-rig.json`, `marketplace.json`, `installed_plugins.json`, CC marketplace checkout
- **Silent drift** — 4 live version mismatches exist today, 30 orphaned cache dirs, 2 plugins missing from cache entirely
- **Fragile recovery** — mid-publish failures leave partially published state with manual recovery instructions
- **Auto-publish rewrites history** — `commit --amend` + `push --force-with-lease` on every auto-bump
- **Global 60s sentinel** — rapid successive plugin pushes silently skip the second one

Publishing 33 plugins should be boring and reliable. Instead, it's a source of recurring friction.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | `ic publish` subcommand in Intercore | Intercore already has Go infra, SQLite, CLI patterns. Publishing is a core platform operation. |
| Version source of truth | `plugin.json` only | Single source eliminates sync bugs entirely. Other files are derived artifacts. |
| Derived version files | Generated at publish time | Publish tool patches `package.json`, `pyproject.toml`, etc. as a build step. Not .gitignored — committed alongside. |
| State tracking | SQLite state machine | Track publish phases. On failure, detect incomplete publish and offer resume/rollback. Matches existing Intercore patterns. |
| Auto-publish | Keep but fix — hook calls `ic publish --auto` | Thin 5-line hook. Per-plugin sentinel. Never amend history. Never force-push. |
| Doctor | Comprehensive — drift, cache, wrappers | Detect and fix all categories of publishing health issues. |
| `/interpub:release` | Thin wrapper over `ic publish` | Skill becomes 10-line prompt. All logic in Go. |
| Overhaul approach | Revolutionary | Replace shell scripts with proper Go CLI tool. Clean break. |

---

## Architecture

### Component Layout

```
core/intercore/
  cmd/ic/
    main.go           (existing)
    publish.go         ← new subcommand router
  pkg/publish/
    engine.go          ← orchestrator: phase state machine
    version.go         ← version parsing, bumping, semver
    discovery.go       ← find plugin root, discover version files
    marketplace.go     ← marketplace.json read/write, dual-sync
    cache.go           ← cache rebuild, orphan cleanup, .git stripping
    installed.go       ← installed_plugins.json management
    doctor.go          ← drift detection, health checks, auto-repair
    hooks.go           ← pre/post-publish hook execution
    sentinel.go        ← per-plugin publish dedup (replaces global 60s)
    state.go           ← SQLite publish state persistence
    git.go             ← git operations (commit, push, status checks)
```

### CLI Surface

```
ic publish <version>           # bump to exact version + publish
ic publish --patch             # auto-increment patch
ic publish --minor             # auto-increment minor
ic publish --auto              # auto mode (for hooks): patch bump, no prompts
ic publish --auto --cwd <dir>  # auto mode with explicit working directory
ic publish --dry-run           # show what would happen

ic publish doctor              # detect all drift and health issues
ic publish doctor --fix        # auto-repair everything
ic publish doctor --json       # machine-readable output

ic publish clean               # prune orphaned cache dirs
ic publish clean --dry-run     # show what would be cleaned

ic publish init                # register new plugin in marketplace
ic publish init --name foo     # register with explicit name

ic publish status              # show publish state for current plugin
ic publish status --all        # show all 33 plugins' publish health
```

### Publish State Machine

```
                    ┌─────────────────────────────────────────┐
                    │           ic publish 0.3.0              │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 1: DISCOVERY                     │
                    │  - Find plugin root (.claude-plugin/)   │
                    │  - Read current version from plugin.json│
                    │  - Discover derived version files       │
                    │  - Locate marketplace(s)                │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 2: VALIDATION                    │
                    │  - Verify git worktree is clean         │
                    │  - Verify marketplace worktree is clean │
                    │  - Verify remotes are reachable         │
                    │  - Run plugin validator (if present)    │
                    │  - Run pre-publish hooks (post-bump.sh) │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 3: BUMP                          │
                    │  - Write new version to plugin.json     │
                    │  - Derive + patch: package.json,        │
                    │    pyproject.toml, agent-rig.json       │
                    │  - Verify all files match               │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 4: COMMIT_PLUGIN                 │
                    │  - git add changed files                │
                    │  - git commit "release: <name> v0.3.0"  │
                    │  - git pull --rebase (if needed)        │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 5: PUSH_PLUGIN                   │
                    │  - git push (never force, never amend)  │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 6: UPDATE_MARKETPLACE            │
                    │  - Update marketplace.json version      │
                    │  - git commit + push marketplace repo   │
                    │  - Sync CC marketplace checkout         │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 7: SYNC_LOCAL                    │
                    │  - Rebuild cache (without .git)         │
                    │  - Update installed_plugins.json        │
                    │  - Create version symlinks (if hooks)   │
                    │  - Clean up orphaned old versions       │
                    └──────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────────┐
                    │  Phase 8: DONE                          │
                    │  - Clear publish state                  │
                    │  - Run post-publish hooks               │
                    │  - Print summary                        │
                    └─────────────────────────────────────────┘
```

**Recovery behavior:** On re-run after failure, the tool reads the SQLite state, shows which phase failed, and offers:
- **Resume** — pick up from the failed phase
- **Rollback** — revert all completed phases (git revert, restore old version files)
- **Force** — discard state, start fresh

### Per-Plugin Sentinel (replacing global 60s)

```go
// sentinel.go
// Each plugin gets its own sentinel record in SQLite:
//   plugin_name TEXT, last_published_at DATETIME, version TEXT
//
// ic publish --auto checks:
//   1. Is there a sentinel for this specific plugin within TTL?
//   2. If yes, skip (exit 0). If no, proceed.
//   3. On successful publish, write sentinel.
//
// TTL: 30s (down from 60s, and per-plugin not global)
// This means you CAN publish interflux and then intermap 5s later.
```

### Doctor Checks

| Check | Detect | Fix |
|-------|--------|-----|
| Version drift: plugin.json vs marketplace.json | Compare all 33 | Update marketplace to match plugin.json (source of truth) |
| Version drift: installed_plugins.json vs marketplace.json | Compare all 33 | Update installed_plugins.json to match marketplace |
| CC marketplace desync | Diff `core/marketplace/` vs `~/.claude/plugins/marketplaces/` | Copy + commit + push CC checkout |
| Orphaned cache dirs | Scan for `.orphaned_at` markers | Delete orphaned dirs |
| Missing cache entries | Cross-ref installed_plugins.json paths | Rebuild from plugin source |
| `.git` dirs in cache | Scan cache for `.git/` | `rm -rf` the `.git` dirs |
| Cache version mismatch | plugin.json inside cache dir vs dir name | Rebuild cache entry |
| Missing bump-version.sh | Scan interverse/*/ for missing wrappers | Generate standard wrapper |
| Stale publish state | Check for incomplete publishes | Offer resume/rollback |
| Pre-publish hooks | Check for undeclared hooks on disk | Warn (don't auto-fix — needs human review) |
| plugin.json schema | Required fields, unrecognized keys, author format | Report violations, auto-fix where safe (replaces validate-plugin.sh) |
| Unregistered plugins | Plugin dirs not in marketplace.json | Suggest `ic publish init` |

### Auto-Publish Hook (Simplified)

```bash
#!/usr/bin/env bash
# PostToolUse: auto-publish on successful git push
[[ "$TOOL_NAME" == "Bash" ]] || exit 0
[[ "$EXIT_CODE" == "0" ]] || exit 0
[[ "$TOOL_INPUT" =~ git\ push ]] || exit 0

# ic publish --auto handles:
# - plugin detection (is CWD a plugin?)
# - per-plugin sentinel (dedup)
# - patch bump if needed
# - full publish pipeline
# - never amends, never force-pushes
ic publish --auto --cwd "$CWD" 2>/dev/null
exit 0
```

**What changes from current auto-publish.sh (213 lines → 8 lines):**
- No more inline marketplace discovery logic
- No more inline version bumping with sed/jq
- No more `git commit --amend --no-edit`
- No more `git push --force-with-lease`
- No more global sentinel — per-plugin, managed by Go
- No more silent swallowing of errors — Go tool logs to stderr

### `/interpub:release` Skill (Simplified)

```markdown
# /interpub:release <version>

Run `ic publish <version>` in the current plugin directory.

If the `ic` binary is not found, tell the user to install Intercore:
  `bash /home/mk/projects/Demarch/core/intercore/install.sh`

After publish succeeds, remind:
- Restart Claude Code sessions to pick up the new version
- Run `ic publish doctor` periodically to check ecosystem health
```

---

## Migration Plan

### Phase 1: Build `ic publish` core (no breaking changes)

1. Implement `pkg/publish/` with all subpackages
2. Wire into `cmd/ic/publish.go`
3. Write tests against a fixture marketplace + plugin
4. Ship — coexists with interbump.sh, both work

### Phase 2: Wire auto-publish hook

1. Replace `os/clavain/hooks/auto-publish.sh` with thin wrapper
2. Test rapid successive publishes (sentinel)
3. Verify no more history rewriting

### Phase 3: Wire `/interpub:release` skill

1. Replace skill with thin wrapper
2. Update CLAUDE.md / AGENTS.md references

### Phase 4: Run doctor, fix existing drift

1. `ic publish doctor --fix` across all 33 plugins
2. Clean orphaned cache (30 dirs)
3. Strip .git from cache (58 entries)
4. Sync all version drifts

### Phase 5: Deprecate shell scripts

1. Add deprecation warning to `interbump.sh` pointing to `ic publish`
2. Add deprecation warning to `auto-publish.sh`
3. Remove after 2 weeks of `ic publish` stability

### Phase 6: Reduce version file locations

1. Audit which tools actually read `package.json`/`pyproject.toml` versions at runtime
2. For those that don't: stop committing version to those files
3. For those that do: migrate to read from `plugin.json`
4. End state: `plugin.json` is the only hand-edited version file

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Go binary not available on fresh installs | `ic publish` checks for binary, `/interpub:release` skill falls back to interbump.sh during migration |
| SQLite state corruption | Publish state is advisory — `--force` flag bypasses state and starts fresh |
| Marketplace push failures (network) | State machine remembers phase, auto-resume on next run |
| Plugin-specific post-bump hooks break | Run hooks in same phase as today, capture stderr, fail loud |
| Cache rebuild races with running sessions | Version symlinks preserve old version paths until next session restart |

---

## Success Metrics

- **Zero version drifts** — `ic publish doctor` reports clean across all 33 plugins
- **Single publish path** — all publishes go through `ic publish` (direct, hook, or skill)
- **< 5s publish time** — Go binary vs shell script overhead
- **Automatic recovery** — no manual intervention needed for mid-publish failures
- **No history rewriting** — auto-publish never amends or force-pushes

---

## Resolved Questions

1. **`ic publish init`** — Yes. Handle initial marketplace registration for new plugins. One command from "plugin exists" to "plugin is published".
2. **Doctor absorbs schema validation** — Yes. Doctor becomes the single health check, absorbing what `validate-plugin.sh` does today. One tool to rule them all.

## Open Questions

1. Should cache rebuild use hard links instead of copies to save disk space?
2. Should `ic publish --auto` emit a structured event to Intercore's event bus for observability?
