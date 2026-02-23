---
name: interverse-ops
description: Operations skill for Gemini CLI replacing Claude Code slash commands. Handles plugin publishing, version bumping, and bead syncing.
---
# Interverse Operations Skill

This skill replaces Claude Code's slash commands (e.g., `/interpub:release`, `/interpath:roadmap`) with direct execution of the underlying bash scripts for Gemini CLI.

When the user asks to perform an operations task, do not attempt to invoke a slash command. Use the `run_shell_command` tool to execute the appropriate script below.

## Publishing and Version Bumping
Instead of `/interpub:release <version>`, use the bump script directly.
Ensure you are in the correct module directory before executing:

```bash
cd interverse/interflux
scripts/bump-version.sh <version>
```

To perform a dry run:
```bash
scripts/bump-version.sh <version> --dry-run
```

**Note:** Both methods call the same underlying engine (`scripts/interbump.sh`). Do not hand-edit version files or marketplace versions for normal releases.

## Ecosystem Diagram
After any change that adds, removes, or renames a plugin, skill, agent, MCP server, or hook, regenerate the live ecosystem diagram.
Instead of any Claude command, use:

```bash
bash interverse/interchart/scripts/regenerate-and-deploy.sh
```

## Beads Tracking
Never run the interactive `bv` TUI command, as it blocks the automated terminal. Stick strictly to the `bd` CLI:
- List open issues: `bd list --status=open`
- Check ready work: `bd ready`
- Create a bead: `bd create --title="[module] Description" --description="..."`
- Close a bead: `bd close <id>`
- Sync beads before pushing: `bd sync`

## Roadmap Generation
Instead of `/interpath:roadmap` or `/interpath:propagate`, run the sync script:

```bash
scripts/sync-roadmap-json.sh
```
