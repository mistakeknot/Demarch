#!/usr/bin/env bash
# scripts/kimi-hook-bridge.sh
# Adapter for running Claude Code hooks in Kimi Code CLI.
#
# Kimi's hook protocol already matches Claude's: event JSON on stdin
# (hook_event_name, session_id, cwd, tool_name, tool_input), exit 0 = allow,
# exit 2 = block, and hookSpecificOutput JSON / appended context on stdout.
# So unlike the Gemini bridge, this adapter only normalizes the environment
# and forwards stdin/stdout/exit-code untouched.
#
# Usage: ./scripts/kimi-hook-bridge.sh path/to/hook-script.sh

if [ -z "${1:-}" ]; then
    echo "kimi-hook-bridge: adapter error: no hook script provided (failing open)" >&2
    exit 0
fi

SCRIPT_PATH="$1"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "kimi-hook-bridge: adapter error: script not found: $SCRIPT_PATH (failing open)" >&2
    exit 0
fi

if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH" 2>/dev/null || true
fi

# Set up Claude Code environment variables so Claude-format hook scripts run
# unmodified. Prefer KIMI_PLUGIN_ROOT when the host sets it; otherwise derive
# the plugin root as the parent of the hook script's directory
# (<plugin-root>/hooks/<script>.sh).
export CLAUDE_PLUGIN_ROOT="${KIMI_PLUGIN_ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)}"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# stdin is inherited (Kimi's payload shape already matches Claude's), stdout
# passes through untouched, and exec propagates the script's exit code
# (0 = allow, 2 = block) exactly as the Claude hook emits it.
exec "$SCRIPT_PATH"
