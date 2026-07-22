# Kimi Code Host Guide

How to run Sylveste (Clavain + Interverse) on [Kimi Code CLI](https://www.kimi.com/code/docs/en/), alongside the existing Claude Code, Codex, and Gemini hosts.

## What works where

| Capability | How it maps to Kimi Code |
|------------|--------------------------|
| Instructions (`AGENTS.md`) | Native. Kimi reads `AGENTS.md` at project and user level — Sylveste's AGENTS.md-first session protocol works unchanged. |
| Skills (`skills/*/SKILL.md`) | Native format. Symlinked into `~/.agents/skills/`, which Kimi scans automatically. |
| Slash commands (`commands/*.md`) | Native via Kimi plugins (`/<plugin>:<command>` namespacing, same convention as Claude). |
| MCP servers (19 plugins) | Translated into Kimi's `mcpServers` schema (same shape as Claude's; `${CLAUDE_PLUGIN_ROOT}` resolved to real paths). |
| Hooks | Kimi's hook protocol is Claude-compatible (stdin JSON, exit 0/2, `hookSpecificOutput`). `scripts/kimi-hook-bridge.sh` supplies the `CLAUDE_*` env contract so existing hook scripts run unmodified. |
| Custom subagents (`agents/*.md`) | **Not supported.** Kimi has three built-in subagent types (`coder`, `explore`, `plan`) and no custom agent definitions. Use skills + `Agent` dispatch instead. |

## Install

```bash
# From a Sylveste checkout:
bash os/Clavain/scripts/install-kimi.sh install

# Verify:
bash os/Clavain/scripts/install-kimi.sh doctor
```

The installer:

1. Symlinks `~/.agents/skills/clavain` → the Clavain `skills/` directory.
2. Runs `scripts/gen-kimi-manifests.py` to (re)generate `kimi.plugin.json` manifests.
3. Merges Clavain's MCP servers (context7, qmd) into `~/.kimi-code/mcp.json`.
4. Writes a managed hooks block into `~/.kimi-code/config.toml` (markers `# BEGIN/END CLAVAIN KIMI HOOKS`) — **unless the clavain plugin is installed and enabled** in Kimi's plugin manager, in which case the block is removed/skipped (the plugin's `kimi.plugin.json` already carries the full hook set; a config block would double-fire every hook).
5. Writes a managed tool-map block into `~/.kimi-code/AGENTS.md` (markers `<!-- BEGIN/END CLAVAIN KIMI TOOL MAP -->`).

All user-config writes are backup-first and idempotent. Paths are overridable via `KIMI_CODE_HOME` and `AGENTS_SKILLS_DIR`.

Other subcommands: `update`, `uninstall`, `doctor [--json]`.

The top-level `install.sh` runs this automatically when `command -v kimi` succeeds (and removes the integration on `--uninstall`).

## Dogfooding in this repo

The Sylveste checkout itself ships a project-level `.kimi-code/mcp.json` that wires the intermap, intermux, and interlock MCP servers via git-relative launcher paths, so Kimi Code sessions working *on* Sylveste get those tools without any install step. (interserve is skipped — it has no launcher in this checkout.)

## Tool-name deltas

Kimi's tool set is nearly identical to Claude Code's. The tool-map block covers the deltas:

- `MultiEdit` → `Edit`
- `TodoWrite` → `TodoList`
- `Task` → `Agent` (built-in subagent types only)
- `Read`, `Write`, `Bash`, `Grep`, `Glob`, `Skill`, `AskUserQuestion` — same names, same roles

## Regenerating plugin manifests

`kimi.plugin.json` files are generated artifacts; `.claude-plugin/plugin.json` remains the source of truth.

```bash
python3 scripts/gen-kimi-manifests.py          # regenerate all
python3 scripts/gen-kimi-manifests.py --check  # CI check: fail if stale
```

Translation rules: `skills`/`commands` directories are referenced as `./`-relative paths; stdio MCP commands have `${CLAUDE_PLUGIN_ROOT}` rewritten to `./`; hooks are flattened to Kimi's `{event, matcher, command, timeout}` schema with `${KIMI_PLUGIN_ROOT}` substituted and Claude-only tool names (`MultiEdit`, `TodoWrite`, `Task`) remapped; `agents` definitions are dropped (Kimi has no equivalent).

## Plugin route (recommended for full functionality)

Installing Clavain as a real Kimi plugin (`/plugins install /path/to/Sylveste/os/Clavain` in the TUI) enables everything the generated manifest carries — the full 16-hook set, 58 `/clavain:*` slash commands, and the `using-clavain` session-start skill. The symlink + `mcp.json` route alone does **not** register slash commands.

Caveats of the plugin route:

- Kimi copies the plugin into `~/.kimi-code/plugins/managed/clavain/`; later edits to the source checkout have no effect until you reinstall (`/plugins remove clavain`, then install again).
- Plugins are per-user only (no project-level install scope yet).
- `install-kimi.sh` detects an enabled clavain plugin and skips its config.toml hooks block, so the two routes can coexist without hooks double-firing.

## Known gaps

- **Custom subagent definitions** (Clavain's 6 agents, interflux's 17, `fd-*` fleets) do not load in Kimi. Their instructions can be ported as skills if needed.
- **`session-start.sh`** depends on `CLAUDE_ENV_FILE`, which has no Kimi equivalent; env-export behavior degrades gracefully (the rest of the script's logic runs).
