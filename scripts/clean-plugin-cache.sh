#!/bin/bash
#
# clean-plugin-cache — remove stale plugin version directories from Claude Code cache.
#
# Keeps only the latest version per plugin. Symlinks are always removed.
#
# Usage:
#   clean-plugin-cache.sh [--dry-run]

set -euo pipefail

if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run]"
            echo "  Removes stale plugin version directories from Claude Code cache."
            echo "  Keeps only the latest semver per plugin."
            exit 0
            ;;
    esac
done

CACHE_DIR="$HOME/.claude/plugins/cache/interagency-marketplace"

if [ ! -d "$CACHE_DIR" ]; then
    echo -e "${RED}Cache directory not found: $CACHE_DIR${NC}" >&2
    exit 1
fi

total_removed=0
total_kept=0
bytes_freed=0

for plugin_dir in "$CACHE_DIR"/*/; do
    [ -d "$plugin_dir" ] || continue
    plugin_name=$(basename "$plugin_dir")

    # Collect real directories (not symlinks), sort by semver descending
    versions=()
    while IFS= read -r v; do
        versions+=("$v")
    done < <(
        for d in "$plugin_dir"*/; do
            [ -d "$d" ] || continue
            [ -L "${d%/}" ] && continue  # skip symlinks
            basename "$d"
        done | sort -t. -k1,1n -k2,2n -k3,3n | tac
    )

    # Remove symlinks unconditionally
    for d in "$plugin_dir"*/; do
        [ -L "${d%/}" ] || continue
        if $DRY_RUN; then
            echo -e "  ${YELLOW}[dry-run]${NC} rm symlink $plugin_name/$(basename "$d")"
        else
            rm -f "${d%/}"
        fi
        total_removed=$((total_removed + 1))
    done

    # Keep first (latest), remove rest
    kept=false
    for v in "${versions[@]}"; do
        if ! $kept; then
            kept=true
            total_kept=$((total_kept + 1))
            continue
        fi
        dir_size=$(du -sb "$plugin_dir$v" 2>/dev/null | cut -f1 || echo 0)
        bytes_freed=$((bytes_freed + dir_size))
        if $DRY_RUN; then
            echo -e "  ${YELLOW}[dry-run]${NC} rm -rf $plugin_name/$v ($(numfmt --to=iec "$dir_size" 2>/dev/null || echo "${dir_size}B"))"
        else
            rm -rf "$plugin_dir$v"
        fi
        total_removed=$((total_removed + 1))
    done
done

freed_human=$(numfmt --to=iec "$bytes_freed" 2>/dev/null || echo "${bytes_freed} bytes")

echo ""
if $DRY_RUN; then
    echo -e "${YELLOW}Dry run complete.${NC} Would remove $total_removed dirs, keep $total_kept, free ~$freed_human."
else
    echo -e "${GREEN}Done.${NC} Removed $total_removed dirs, kept $total_kept, freed ~$freed_human."
fi
