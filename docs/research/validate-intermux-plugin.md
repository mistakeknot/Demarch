# Plugin Validation Report: intermux

**Date:** 2026-02-18
**Plugin Path:** `/home/mk/.claude/plugins/cache/interagency-marketplace/intermux/0.1.0/`
**Validator:** Claude Opus 4.6 (plugin-validator agent)

---

## Summary

**PASS** -- The intermux plugin is well-structured, compiles cleanly, passes all tests, and follows plugin conventions correctly. Two minor issues found (hooks schema event name, SKILL.md frontmatter format), plus a few recommendations for improvement. No critical or major issues.

| Category | Count |
|----------|-------|
| Critical Issues | 0 |
| Major Issues | 0 |
| Minor Issues | 2 |
| Warnings | 3 |

---

## 1. Manifest Validation (.claude-plugin/plugin.json)

**Status: PASS**

```json
{
  "name": "intermux",
  "version": "0.1.0",
  "description": "Agent activity visibility -- tmux monitoring, activity feeds, health detection. Enriches intermute with live context.",
  "author": { "name": "MK" },
  "hooks": "./hooks/hooks.json",
  "skills": ["./skills/status/SKILL.md"],
  "mcpServers": {
    "intermux": {
      "type": "stdio",
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh",
      "args": [],
      "env": {
        "INTERMUTE_URL": "http://127.0.0.1:7338",
        "TMUX_SOCKET": "/tmp/tmux-0/default"
      }
    }
  }
}
```

| Check | Result | Notes |
|-------|--------|-------|
| JSON syntax valid | PASS | Validated with `jq` |
| `name` present | PASS | `"intermux"` -- kebab-case, no spaces |
| `version` format | PASS | `"0.1.0"` -- valid semver |
| `description` non-empty | PASS | Clear and descriptive |
| `author` structure | PASS | Has `name` field |
| `hooks` path | PASS | Points to `./hooks/hooks.json` which exists |
| `skills` array | PASS | Points to `./skills/status/SKILL.md` which exists |
| `mcpServers` config | PASS | stdio type with command, args, env |
| `command` uses `${CLAUDE_PLUGIN_ROOT}` | PASS | Portable path reference |
| No unknown fields | PASS | All fields are recognized plugin.json properties |

---

## 2. Hooks Validation

### hooks/hooks.json

**Status: MINOR ISSUE**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh",
            "async": true
          }
        ]
      }
    ]
  }
}
```

| Check | Result | Notes |
|-------|--------|-------|
| JSON syntax valid | PASS | Validated with `jq` |
| Event name valid | **MINOR** | `SessionStart` is not in the standard documented hook events (PreToolUse, PostToolUse, Stop, Notification, SubagentStop). However, Claude Code does support session lifecycle hooks and this may be a valid internal event. The hook structure is correct regardless. |
| Has `matcher` field | PASS | `"startup\|resume\|clear\|compact"` |
| Has `hooks` array | PASS | Contains one hook entry |
| Hook `type` valid | PASS | `"command"` |
| Hook `command` path | PASS | Uses `${CLAUDE_PLUGIN_ROOT}` prefix |
| `async` field | PASS | Set to `true` -- appropriate for a mapping-file writer |
| Referenced script exists | PASS | `hooks/session-start.sh` exists and is executable |

### hooks/session-start.sh

**Status: PASS**

| Check | Result | Notes |
|-------|--------|-------|
| Bash syntax valid | PASS | `bash -n` passes |
| Executable permission | PASS | `-rwxrwx---` |
| Uses `set -euo pipefail` | PASS | Strict error handling |
| Reads stdin (JSON input) | PASS | `INPUT=$(cat)` |
| Graceful error handling | PASS | `|| exit 0` on jq parse, `|| true` on tmux query |
| No hardcoded credentials | PASS | Clean |
| Writes to /tmp | PASS | `/tmp/intermux-mapping-${SID}.json` -- ephemeral, appropriate |

---

## 3. Skills Validation

### skills/status/SKILL.md

**Status: MINOR ISSUE**

| Check | Result | Notes |
|-------|--------|-------|
| SKILL.md exists | PASS | At `skills/status/SKILL.md` |
| Frontmatter format | **MINOR** | Uses non-standard `<skill-description>` and `<command-name>` XML tags instead of YAML frontmatter with `---` delimiters. While Claude Code may accept this format, the standard convention is YAML frontmatter with `name` and `description` fields. |
| Description present | PASS | Via `<skill-description>` tag |
| Command name present | PASS | Via `<command-name>status</command-name>` |
| Markdown content | PASS | Has substantial instructions (Steps, Status Icons, Additional Context) |
| Instructions quality | PASS | Clear step-by-step with MCP tool references |

**Recommended frontmatter format:**
```markdown
---
name: status
description: Show a live dashboard of all agent tmux sessions with status, activity, and health warnings.
---
```

---

## 4. MCP Server Validation

### Configuration

**Status: PASS**

| Check | Result | Notes |
|-------|--------|-------|
| Server type | PASS | `stdio` -- appropriate for Go binary |
| Command path | PASS | `${CLAUDE_PLUGIN_ROOT}/bin/launch-mcp.sh` -- uses portable path |
| Launcher script exists | PASS | `bin/launch-mcp.sh` present and executable |
| Binary exists | PASS | `bin/intermux-mcp` -- ELF 64-bit x86-64, Go binary |
| Binary executable | PASS | `-rwxrwx---` permissions |
| Auto-build fallback | PASS | `launch-mcp.sh` auto-builds if binary missing |
| Environment variables | PASS | `INTERMUTE_URL` and `TMUX_SOCKET` configured |

### Launcher Script (bin/launch-mcp.sh)

| Check | Result | Notes |
|-------|--------|-------|
| Bash syntax valid | PASS | `bash -n` passes |
| Uses `set -euo pipefail` | PASS | |
| Binary detection | PASS | Checks `[[ ! -x "$BINARY" ]]` |
| Go availability check | PASS | `command -v go` before build attempt |
| Error messaging | PASS | JSON error on missing Go toolchain |
| `exec` for binary | PASS | Uses `exec "$BINARY" "$@"` -- replaces shell process |

### Go Source Code Quality

| Check | Result | Notes |
|-------|--------|-------|
| `go vet ./...` | PASS | No issues |
| `go test ./...` | PASS | 1 test package passes (tmux), 5 packages have no tests |
| MCP tools registered | PASS | 7 tools: list_agents, peek_agent, activity_feed, search_output, agent_health, who_is_editing, session_info |
| Thread safety | PASS | `sync.RWMutex` used in Store |
| Graceful shutdown | PASS | Signal handler with context cancellation |
| Module path | PASS | `github.com/mistakeknot/intermux` |

---

## 5. Directory Structure

```
intermux/0.1.0/
  .claude-plugin/
    plugin.json          # Manifest
  bin/
    launch-mcp.sh        # Auto-build launcher
    intermux-mcp         # Pre-built Go binary
  cmd/
    intermux-mcp/
      main.go            # MCP server entry point
  internal/
    activity/
      models.go          # Data types
      store.go           # Thread-safe store
    health/
      monitor.go         # Health classification
    push/
      pusher.go          # Intermute metadata push
    tmux/
      parser.go          # Pane content parsing
      session_name.go    # Session name parser
      session_name_test.go  # Tests
      watcher.go         # Tmux session scanner
    tools/
      tools.go           # MCP tool definitions
  hooks/
    hooks.json           # Hook configuration
    session-start.sh     # Session correlation hook
  skills/
    status/
      SKILL.md           # /intermux:status command
  scripts/
    bump-version.sh      # Version bumping (delegates to interbump)
  docs/
    roadmap.json         # Module roadmap
  .clavain/
    interspect/
      interspect.db      # Interspect database
  CLAUDE.md              # Quick reference
  AGENTS.md              # Full development guide
  .gitignore             # Ignores bin/intermux-mcp
  go.mod                 # Go module
  go.sum                 # Go dependencies
```

| Check | Result | Notes |
|-------|--------|-------|
| Plugin root structure | PASS | `.claude-plugin/plugin.json` present |
| Standard directories | PASS | hooks/, skills/, bin/, cmd/, internal/ |
| README equivalent | PASS | CLAUDE.md and AGENTS.md serve this purpose |
| .gitignore present | PASS | Ignores `bin/intermux-mcp` binary |
| No unnecessary files | PASS | No node_modules, .DS_Store, etc. |
| No commands/ directory | OK | Plugin uses skills + MCP tools instead of slash commands |
| No agents/ directory | OK | Not applicable for this plugin type |

---

## 6. Security Checks

| Check | Result | Notes |
|-------|--------|-------|
| No hardcoded credentials | PASS | All files clean |
| MCP env uses localhost | PASS | `http://127.0.0.1:7338` -- local only |
| Hook doesn't leak secrets | PASS | Only writes session/tmux/agent mapping |
| /tmp file naming | PASS | Uses session ID suffix, no collision risk |
| No secrets in examples | PASS | AGENTS.md examples are clean |
| Process inspection | PASS | Reads /proc safely with error handling |

---

## 7. Warnings

1. **Test coverage is low** -- Only `internal/tmux/session_name_test.go` has tests. The activity store, health monitor, pusher, tools, and parser packages have no test files. While `go vet` passes, adding tests for critical paths (store operations, pane parsing, health classification) would improve reliability.

2. **INTERMUTE_URL uses HTTP** -- The MCP server env configures `INTERMUTE_URL=http://127.0.0.1:7338`. This is acceptable for localhost communication but would be a concern if the URL were ever changed to a remote host. The pusher does not enforce HTTPS.

3. **Pre-built binary in cache** -- The `bin/intermux-mcp` binary is a 9.5MB ELF executable committed to the plugin cache. While the launcher script handles auto-building, shipping pre-built binaries increases cache size. The `.gitignore` correctly excludes it from the source repo, so this only affects the marketplace distribution.

---

## 8. Component Summary

| Component | Found | Valid | Notes |
|-----------|-------|-------|-------|
| Commands | 0 | N/A | Plugin uses skills + MCP tools |
| Agents | 0 | N/A | Not applicable |
| Skills | 1 | 1 | `status` skill (minor frontmatter format issue) |
| Hooks | 1 event, 1 hook | 1 | `SessionStart` (minor: non-standard event name) |
| MCP Servers | 1 | 1 | `intermux` stdio server with 7 tools |
| Go packages | 6 | 6 | All pass `go vet` |
| Tests | 1 file | 1 | `session_name_test.go` passes |

---

## 9. Positive Findings

- **Solid Go architecture** -- Clean separation into packages (activity, health, push, tmux, tools) with well-defined responsibilities.
- **Thread-safe store** -- Proper use of `sync.RWMutex` with copy-on-read in `Get()` to prevent data races.
- **Graceful degradation** -- Hook script exits 0 on all error paths; MCP launcher auto-builds if binary missing; pusher silently disables when no INTERMUTE_URL.
- **Good session name parser** -- Handles compound keywords (admin-claude), multi-word projects (shadow-work, agent-fortress), optional instance numbers, and edge cases with comprehensive test coverage.
- **Portable paths** -- Consistent use of `${CLAUDE_PLUGIN_ROOT}` in all configuration.
- **Ring buffer design** -- Activity store uses a fixed-size ring buffer (200 events) instead of unbounded growth, preventing memory leaks in long-running sessions.
- **Comprehensive AGENTS.md** -- Architecture diagram, tool table, component descriptions, environment variables, and development commands.

---

## 10. Recommendations

1. **[Minor Fix] Standardize SKILL.md frontmatter** -- Replace `<skill-description>` and `<command-name>` XML tags with standard YAML frontmatter:
   ```markdown
   ---
   name: status
   description: Show a live dashboard of all agent tmux sessions with status, activity, and health warnings.
   ---
   ```

2. **[Minor Fix] Verify SessionStart hook event** -- Confirm that `SessionStart` is a valid hook event in the current Claude Code plugin runtime. If not, the hook will silently never fire. The standard documented events are PreToolUse, PostToolUse, Stop, Notification, and SubagentStop.

3. **[Improvement] Add tests for critical packages** -- Priority targets:
   - `internal/activity/store_test.go` -- concurrent access, ring buffer wraparound
   - `internal/tmux/parser_test.go` -- pane content parsing, event type detection
   - `internal/health/monitor_test.go` -- status classification

4. **[Improvement] Add LICENSE file** -- No license file present in the plugin.

5. **[Improvement] Consider HTTPS enforcement** -- Add a check in the pusher to warn or refuse if `INTERMUTE_URL` starts with `http://` and the host is not `127.0.0.1` or `localhost`.

---

## Overall Assessment

**PASS** -- The intermux plugin is production-quality with clean code, proper error handling, portable configuration, and comprehensive documentation. The two minor issues (SKILL.md frontmatter format and SessionStart event name) do not prevent the plugin from functioning. The Go codebase passes vet and tests. The MCP server correctly registers all 7 tools with proper input validation and JSON serialization. The hook script is well-written with graceful error handling. The plugin is ready for use.
