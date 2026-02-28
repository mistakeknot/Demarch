#!/bin/bash
# scripts/gen-gemini-skills.sh
# Generates Gemini CLI SKILL.md files from Clavain/Interverse phase docs.
# This implements Progressive Disclosure to save tokens.

set -e

# Ensure we are at the project root
PROJECT_ROOT=$(git rev-parse --show-toplevel)
cd "$PROJECT_ROOT"

SKILLS_DIR=".gemini/generated-skills"
mkdir -p "$SKILLS_DIR"

echo "Generating Gemini Skills from Clavain and Interverse drivers..."

# Find all modules with an AGENTS.md or CLAUDE.md
find os interverse -maxdepth 2 -type d | while read module_dir; do
    plugin_name=$(basename "$module_dir")
    
    # Check if this module has agent instructions
    agent_doc="$module_dir/AGENTS.md"
    if [ ! -f "$agent_doc" ]; then
        agent_doc="$module_dir/CLAUDE.md"
        if [ ! -f "$agent_doc" ]; then
            continue
        fi
    fi
    
    echo "Processing $plugin_name..."
    
    skill_dir="$SKILLS_DIR/$plugin_name"
    mkdir -p "$skill_dir"
    skill_file="$skill_dir/SKILL.md"
    
    # Try to extract a brief description from the plugin.json or just use a default
    plugin_json="$module_dir/.claude-plugin/plugin.json"
    description="Interverse driver capability: $plugin_name"
    if [ -f "$plugin_json" ]; then
        desc_extract=$(jq -r '.description // empty' "$plugin_json" 2>/dev/null)
        if [ ! -z "$desc_extract" ]; then
            description="$desc_extract"
        fi
    fi
    
    # Start writing the Gemini SKILL.md with YAML frontmatter
    cat <<EOF > "$skill_file"
---
name: $plugin_name
description: "$description"
---
# Gemini Skill: $plugin_name

You have activated the $plugin_name capability.

EOF
    
    # Append the main agent instructions
    echo "## Base Instructions" >> "$skill_file"
    cat "$agent_doc" >> "$skill_file"
    echo -e "
" >> "$skill_file"
    
    # Append phase docs if they exist
    if [ -d "$module_dir/phases" ]; then
        echo "## Phase Documentation" >> "$skill_file"
        for phase_file in "$module_dir/phases"/*.md; do
            echo "### Phase: $(basename "$phase_file" .md)" >> "$skill_file"
            cat "$phase_file" >> "$skill_file"
            echo -e "
" >> "$skill_file"
        done
    fi

    # Append reference docs if they exist
    if [ -d "$module_dir/references" ]; then
        echo "## Reference Documentation" >> "$skill_file"
        for ref_file in "$module_dir/references"/*.md; do
            echo "### Reference: $(basename "$ref_file" .md)" >> "$skill_file"
            cat "$ref_file" >> "$skill_file"
            echo -e "
" >> "$skill_file"
        done
    fi
    
    echo "✓ Generated $skill_file"
done

echo "All Gemini Skills generated successfully."
