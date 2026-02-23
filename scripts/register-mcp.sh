#!/bin/bash
# scripts/register-mcp.sh
# Registers all Interverse MCP servers with Gemini CLI.
# This configures Gemini to use the existing `launch-mcp.sh` entry points.

set -e

# Ensure we are at the project root
PROJECT_ROOT=$(git rev-parse --show-toplevel)
cd "$PROJECT_ROOT"

echo "Scanning for MCP servers to register with Gemini CLI..."

# Find all launch-mcp.sh scripts
for launch_script in $(find interverse -name "launch-mcp.sh" -type f); do
    # Extract the plugin directory and name
    plugin_dir=$(dirname $(dirname "$launch_script"))
    plugin_name=$(basename "$plugin_dir")
    
    echo "Registering $plugin_name..."
    
    # We use gemini mcp add to register the server in the project scope (.gemini/settings.json)
    # The server is executed via bash with the script path.
    gemini mcp add --scope project "$plugin_name" bash "$PROJECT_ROOT/$launch_script"
    
    echo "✓ $plugin_name registered."
done

echo "All Interverse MCP servers registered successfully."
