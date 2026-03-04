# Critical Patterns

Patterns that bite every session. Each learned from a production failure.

**1. hooks.json format** — Event types are **object keys** (`"SessionStart": [...]`), NOT array elements with `"type"` field. Wrong format silently ignored.

**2. Compiled MCP servers need launcher scripts** — `plugin.json` must point to `bin/launch-mcp.sh` (tracked), not the binary (gitignored). No `postInstall` hook exists.

**3. `.orphaned_at` markers block plugin loading** — After version bumps or cache manipulation: `find ~/.claude/plugins/cache -maxdepth 4 -name ".orphaned_at" -not -path "*/temp_git_*" -delete`

**4. Valid hook events (14 total)** — `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `SessionEnd`. Invalid events silently ignored.

**5. jq null-slice** — `null[:10]` is a runtime error (exit 5), NOT null. Fix: `(.field // [])[:10]`. Shell functions returning JSON must return `{}`, never `""`.

**6. Billing tokens != effective context** — Cache hits are free for billing but consume context. Decision gates about context limits MUST use `input + cache_read + cache_creation`, never `input + output`.
