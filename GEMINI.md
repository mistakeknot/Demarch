# Gemini Context

Please refer to the following documents for more information:
- [AGENTS.md](./AGENTS.md)
- [CLAUDE.md](./CLAUDE.md)

## Gemini (Antigravity) Specifics

Since Gemini (Antigravity) operates independently via bash and tools rather than Claude Code slash commands, follow these deviations from the standard guides:

1. **Terminal Scripts over Slash Commands**: Avoid using Claude Code slash commands (e.g., `/interpub:release`). Run the underlying shell scripts directly instead (e.g., `bash scripts/bump-version.sh <version>`).
2. **Issue Tracking (Beads)**: Never run the interactive `bv` TUI command, as it blocks the automated terminal. Stick strictly to the `bd` CLI (e.g., `bd ready`, `bd list --status=open`).
3. **Execution Autonomy**: You have the ability to run terminal commands via the `run_command` tool. Proactively build, test, and run validation scripts (e.g., `go test ./...`, `uv run pytest`) without asking for explicit permission.
