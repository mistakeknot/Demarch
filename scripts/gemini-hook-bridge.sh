#!/bin/bash
# scripts/gemini-hook-bridge.sh
# Adapter for running Claude Code hooks in Gemini CLI.
# Gemini expects JSON on stdin and a JSON decision on stdout.
# Usage: ./scripts/gemini-hook-bridge.sh path/to/hook-script.sh

if [ -z "$1" ]; then
    echo '{"decision": "deny", "reason": "Adapter error: No hook script provided."}'
    exit 0
fi

SCRIPT_PATH="$1"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "{"decision": "deny", "reason": "Adapter error: Script $SCRIPT_PATH not found."}"
    exit 0
fi

if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH"
fi

# Set up Claude Code specific environment variables
export CLAUDE_PLUGIN_ROOT=$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)
export CLAUDE_PROJECT_DIR="${GEMINI_PROJECT_DIR:-$(pwd)}"

# Read the JSON event from Gemini CLI (stdin)
EVENT_JSON=$(cat)

# Extract tool name or command if it's a Tool or Bash event to emulate Claude's arguments if necessary.
# Often Claude passes $1 as tool name. We can try to extract it.
TOOL_NAME=$(echo "$EVENT_JSON" | jq -r '.tool_name // .command // ""')

# Execute the Claude Code hook.
# We route stdout to stderr because Gemini CLI ONLY accepts the final JSON on stdout.
# Any other stdout output will cause a parsing error in Gemini CLI.
set +e
echo "$EVENT_JSON" | "$SCRIPT_PATH" "$TOOL_NAME" 1>&2
EXIT_CODE=$?
set -e

# Return the exact JSON required by Gemini CLI
if [ $EXIT_CODE -eq 0 ]; then
    echo '{"decision": "allow"}'
else
    echo "{"decision": "deny", "reason": "Original hook script exited with code $EXIT_CODE."}"
fi
