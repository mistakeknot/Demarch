---
name: interlearn
description: "Cross-repo institutional knowledge index — indexes solution docs across the Interverse monorepo, enables unified search, and audits reflect coverage."
---
# Gemini Skill: interlearn

You have activated the interlearn capability.

## Base Instructions
# interlearn

Cross-repo institutional knowledge index for the Interverse monorepo.

## Overview

1 skill (3 sub-skills), 0 agents, 0 commands, 1 hook (SessionEnd). Companion plugin for interflux.

## Quick Commands

```bash
bash scripts/index-solutions.sh /root/projects/Interverse  # Rebuild index
python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))"  # Manifest check
jq . /root/projects/Interverse/docs/solutions/index.json  # Verify JSON index
wc -l /root/projects/Interverse/docs/solutions/INDEX.md  # Check line count
```

## Design Decisions (Do Not Re-Ask)

- Shell-only — no Python, no MCP server, no compiled binary
- Index lives at Interverse root `docs/solutions/` (not per-subrepo)
- No auto-commit — hook writes files, developer commits when ready
- 3-marker monorepo detection (`.beads/ + plugins/ + hub/`) in hook
- Handles frontmatter heterogeneity: `category` vs `problem_type`, `date_resolved`/`created` vs `date`


