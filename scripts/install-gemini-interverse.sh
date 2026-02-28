#!/usr/bin/env bash
# Install Clavain + Interverse skills for Gemini CLI.
# Generates Gemini skills from project markdown docs and links them globally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ACTION="install"
if [[ $# -gt 0 && "${1#-}" == "$1" ]]; then
  ACTION="$1"
  shift
fi

if ! command -v gemini &>/dev/null; then
    echo "Error: Gemini CLI (gemini) not found on PATH."
    echo "Install with: npm install -g @google/gemini-cli"
    exit 1
fi

case "$ACTION" in
    install)
        echo "Generating Gemini CLI skills..."
        bash "$SCRIPT_DIR/gen-gemini-skills.sh"
        
        echo "Linking skills to Gemini global scope..."
        cd "$PROJECT_ROOT"
        gemini skills link .gemini/generated-skills --scope user --consent
        
        echo "Successfully installed Gemini CLI skills!"
        ;;
    uninstall)
        echo "Unlinking Gemini CLI skills..."
        # Gemini does not have a bulk unlink yet, but we can iterate over the generated skills
        for skill_dir in "$PROJECT_ROOT/.gemini/generated-skills"/*; do
            if [ -d "$skill_dir" ]; then
                skill_name=$(basename "$skill_dir")
                echo "Unlinking $skill_name..."
                gemini skills uninstall "$skill_name" --scope user || true
            fi
        done
        echo "Successfully uninstalled Gemini CLI skills!"
        ;;
    *)
        echo "Usage: $0 [install|uninstall]"
        exit 1
        ;;
esac
