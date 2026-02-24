---
module: interflux
date: 2026-02-24
problem_type: integration_issue
component: tooling
symptoms:
  - "Plugin install fails on new machine — MCP servers cannot start"
  - "hooks exist on disk but never loaded by Claude Code (missing hooks key)"
  - "qmd: command not found — external binary not installed"
  - "EXA_API_KEY not set — exa-mcp-server starts but cannot function"
root_cause: incomplete_setup
resolution_type: tooling_addition
severity: high
tags: [claude-code, plugin, mcp, launcher, graceful-degradation, hooks, install]
---

# Troubleshooting: Plugin Install Failure on New Machine — Undeclared Hooks + Missing MCP Prerequisites

## Problem
The interflux plugin (multi-agent review engine) fails to install/load correctly on a new computer. Three independent issues compound: hooks are never loaded because the manifest doesn't declare them, and both MCP servers fail because their external dependencies (qmd binary, npx + EXA_API_KEY) aren't present on a fresh machine.

## Environment
- Module: interflux (Claude Code plugin, v0.2.22)
- Affected Component: Plugin manifest (plugin.json), MCP server initialization
- Date: 2026-02-24

## Symptoms
- Plugin installs without error but hooks don't fire (session-start, write-capabilities)
- `qmd mcp` fails with "command not found" — binary installed via bun, not present on new machine
- `exa-mcp-server` either fails (no npx/Node.js) or starts but errors on every call (no EXA_API_KEY)
- Plugin appears "loaded" but is missing hooks and MCP tools

## What Didn't Work

**Direct binary reference in plugin.json:**
- `"command": "qmd"` assumes `qmd` is on PATH. On a new machine it's not — installed at `~/.bun/bin/qmd` via `bun install -g qmd`. Claude Code has no `postInstall` hook to install it automatically.

**Direct npx invocation for exa:**
- `"command": "npx", "args": ["-y", "exa-mcp-server"]` works when Node.js is installed, but silently breaks when `EXA_API_KEY` is unset (MCP starts but every tool call fails). No pre-flight check.

## Solution

### Fix 1: Declare hooks in plugin.json

The `hooks/` directory existed with a valid `hooks.json`, but `plugin.json` had no `"hooks"` field. Claude Code never loaded them.

```json
// Before (WRONG — hooks on disk but undeclared):
{
  "skills": ["./skills/flux-drive", "./skills/flux-research"],
  "commands": ["./commands/flux-drive.md", ...]
  // No hooks key — hooks silently ignored
}

// After (CORRECT):
{
  "skills": ["./skills/flux-drive", "./skills/flux-research"],
  "hooks": "./hooks/hooks.json",
  "commands": ["./commands/flux-drive.md", ...]
}
```

### Fix 2: Launcher script for qmd MCP server

Created `scripts/launch-qmd.sh` — checks if `qmd` exists before starting, exits cleanly with helpful message if not:

```bash
#!/usr/bin/env bash
set -euo pipefail

if ! command -v qmd &>/dev/null; then
    echo "qmd not found — install with: bun install -g qmd" >&2
    echo "interflux will work without qmd but semantic doc search will be unavailable." >&2
    exit 0  # Clean exit — don't make Claude Code retry
fi

exec qmd "$@"
```

Updated plugin.json:
```json
// Before:
"command": "qmd"

// After:
"command": "${CLAUDE_PLUGIN_ROOT}/scripts/launch-qmd.sh"
```

### Fix 3: Launcher script for exa MCP server

Created `scripts/launch-exa.sh` — checks for both npx and EXA_API_KEY:

```bash
#!/usr/bin/env bash
set -euo pipefail

if ! command -v npx &>/dev/null; then
    echo "npx not found — install Node.js to use the Exa search MCP server." >&2
    exit 0
fi

if [[ -z "${EXA_API_KEY:-}" ]]; then
    echo "EXA_API_KEY not set — Exa search MCP server disabled." >&2
    exit 0
fi

exec npx -y exa-mcp-server "$@"
```

## Why This Works

1. **Undeclared hooks**: Claude Code reads the `"hooks"` field in `plugin.json` to find `hooks.json`. Without it, hooks.json is invisible to the plugin loader — no error, no warning, hooks simply don't exist from Claude Code's perspective. This is the same bug class found in 14 plugins during the publishing audit (iv-pxid).

2. **`exit 0` for graceful degradation**: A non-zero exit from an MCP launcher causes Claude Code to show errors and potentially retry. Exiting 0 with stderr messages lets the plugin load successfully — the optional MCP server is simply absent. The plugin's core functionality (review agents, skills, commands) works fine without either MCP server.

3. **Launcher script as indirection layer**: The existing ecosystem pattern (from `critical-patterns.md`) uses launcher scripts for compiled binaries that self-build. This adapts the pattern for external dependencies: instead of building, the launcher **checks availability** and fails gracefully. Same principle — the MCP `"command"` field points to a tracked script, not a potentially-missing binary.

4. **`exec` for zero overhead**: The `exec` call replaces the shell process with the actual server. No wrapper overhead after the prerequisite check passes.

## Prevention

- **Always declare hooks in plugin.json** when a `hooks/` directory exists. The publishing validator (iv-pxid) will catch this going forward.
- **Never reference bare external binaries in MCP server declarations.** Always use a launcher script that checks availability.
- **Use `exit 0` (not `exit 1`) for optional MCP servers.** Non-zero exits produce user-visible errors in Claude Code.
- **Check ALL prerequisites, not just the binary.** The exa launcher checks both `npx` and `EXA_API_KEY` because the server technically starts without the key but fails on every tool call.
- **Pattern template for external-dep launchers:**
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  if ! command -v <tool> &>/dev/null; then
      echo "<tool> not found — install with: <install-cmd>" >&2
      echo "<plugin> will work without <tool> but <feature> will be unavailable." >&2
      exit 0
  fi
  # Optional: check env vars, config files, service health
  exec <tool> "$@"
  ```

## Related Issues
- See also: [plugin-loading-failures-interverse-20260215.md](plugin-loading-failures-interverse-20260215.md) — the original 4-plugin debugging session that discovered the undeclared hooks bug class
- See also: [../workflow-issues/auto-build-launcher-go-mcp-plugins-20260215.md](../workflow-issues/auto-build-launcher-go-mcp-plugins-20260215.md) — the compiled-binary launcher pattern (builds from source); this doc extends the pattern to external dependencies (checks availability instead of building)
- See also: [../../solutions/patterns/critical-patterns.md](../patterns/critical-patterns.md) — Required Reading entry #1 documents the launcher pattern
