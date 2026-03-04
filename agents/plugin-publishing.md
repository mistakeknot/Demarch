# Plugin Dev/Publish Gate

Applies to work in `os/clavain/` and `interverse/*`.

Before claiming a plugin release is complete:

1. Run module-appropriate checks from **Running and testing by module type** (see [development-workflow.md](development-workflow.md)).
2. Publish only via supported entrypoints:
   - Claude Code: `/interpub:release <version>`
   - Terminal (from plugin root): `scripts/bump-version.sh <version>`
   - Optional preflight: `scripts/bump-version.sh <version> --dry-run`
3. Do not hand-edit version files or marketplace versions for normal releases; `scripts/interbump.sh` is the source of truth.
4. Release is complete only when both pushes succeed:
   - plugin repo push
   - `core/marketplace` push
5. If the plugin includes hooks, preserve the post-bump/cache-bridge behavior from `interbump` (do not bypass with ad-hoc scripts).
6. After publish, restart Claude Code sessions so the new plugin version is picked up.

## Ecosystem Diagram (interchart)

After any change that adds, removes, or renames a plugin, skill, agent, MCP server, or hook, regenerate the live ecosystem diagram:

```bash
bash interverse/interchart/scripts/regenerate-and-deploy.sh  # from repo root
```

This scans the monorepo, rebuilds the HTML, and pushes to GitHub Pages. No manual intervention needed — just run the command as a final step.

## Version Bumping (interbump)

All plugins and Clavain share a single version bump engine at `scripts/interbump.sh`. Each module's `scripts/bump-version.sh` is a thin wrapper that delegates to it.

### How it works

1. Reads plugin name and current version from `.claude-plugin/plugin.json` via **jq**
2. Auto-discovers version files: `plugin.json` (always), plus `pyproject.toml`, `package.json`, `server/package.json`, `agent-rig.json`, `docs/PRD.md` if they exist
3. Finds marketplace by walking up from plugin root looking for `core/marketplace/` (monorepo layout), falling back to `../interagency-marketplace` (legacy sibling checkout)
4. Runs `scripts/post-bump.sh` if present (runs after version file edits but before git commit)
5. Updates all version files (jq for JSON, sed for toml/md)
6. Updates marketplace.json via `jq '(.plugins[] | select(.name == $name)).version = $ver'`
7. Git add + commit + `pull --rebase` + push (both plugin and marketplace repos)
8. Creates cache symlinks in `~/.claude/plugins/cache/` so running Claude Code sessions' plugin Stop hooks (which reference the old version path) continue to resolve after the version directory is renamed

### Post-bump hooks

Modules with extra work needed between version edits and git commit use `scripts/post-bump.sh`:

| Module | Post-bump action |
|--------|-----------------|
| `os/clavain/` | Runs `gen-catalog.py` to refresh skill/agent/command counts |
| `interverse/tldr-swinton/` | Reinstalls CLI via `uv tool install`, checks interbench sync |

### Adding a new plugin

1. Create `scripts/bump-version.sh` (copy any existing 5-line wrapper)
2. Ensure `.claude-plugin/plugin.json` has `name` and `version` fields
3. Add an entry to `core/marketplace/.claude-plugin/marketplace.json`
4. If the plugin needs pre-commit work, add `scripts/post-bump.sh`
