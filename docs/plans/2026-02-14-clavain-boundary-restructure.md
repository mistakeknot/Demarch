# Plan: Clavain Boundary Restructure

**PRD:** `docs/prds/2026-02-14-clavain-boundary-restructure.md`

## Overview

Remove 4 alias commands and extract 5 domain-specific skills (plus 1 agent and 1 command) from Clavain into 4 new companion plugins + 1 existing plugin. Create interslack, interform, intercraft, interdev. Move finding-duplicate-functions to tldr-swinton.

**Clavain before:** 37 commands, 27 skills, 5 agents
**Clavain after:** 32 commands, 22 skills, 4 agents

## Tasks

### Task 1: Remove alias commands from Clavain

**Files to delete:**
- `hub/clavain/commands/lfg.md`
- `hub/clavain/commands/full-pipeline.md`
- `hub/clavain/commands/cross-review.md`
- `hub/clavain/commands/deep-review.md`

**Files to update:**
- `hub/clavain/.claude-plugin/plugin.json` — update `description` counts only (uses directory discovery, no arrays)
- `hub/clavain/agent-rig.json` — update description counts, update postInstall message (references `/lfg`)
- `hub/clavain/README.md` — update command count from 37 to 33 (we'll adjust further after skill moves)
- `hub/clavain/commands/help.md` — MUST remove aliases line (line 23: `> **Aliases:** /deep-review = ...`)

**Verification:** `ls commands/*.md | wc -l` should decrease by 4

### Task 2: Create `interslack` plugin

**New files:**
```
plugins/interslack/
  .claude-plugin/
    plugin.json
  skills/
    slack-messaging/
      SKILL.md       (moved from hub/clavain/skills/slack-messaging/SKILL.md)
      scripts/       (moved from hub/clavain/skills/slack-messaging/scripts/)
  CLAUDE.md
  .gitignore
```

**plugin.json template:**
```json
{
  "name": "interslack",
  "version": "0.1.0",
  "description": "Slack integration for Claude Code — send messages, read channels, test integrations.",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/interslack",
  "license": "MIT",
  "keywords": ["slack", "messaging", "integration", "communication"],
  "skills": ["./skills/slack-messaging"]
}
```

**Then:** Remove `skills/slack-messaging/` from Clavain. No plugin.json array update needed (directory discovery).

### Task 3: Create `interform` plugin

**New files:**
```
plugins/interform/
  .claude-plugin/
    plugin.json
  skills/
    distinctive-design/
      SKILL.md       (moved from hub/clavain/skills/distinctive-design/SKILL.md)
  CLAUDE.md
  .gitignore
```

**plugin.json:**
```json
{
  "name": "interform",
  "version": "0.1.0",
  "description": "Design patterns and visual quality for Claude Code — distinctive, production-grade interfaces.",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/interform",
  "license": "MIT",
  "keywords": ["design", "ui", "ux", "visual", "interface"],
  "skills": ["./skills/distinctive-design"]
}
```

**Then:** Remove `skills/distinctive-design/` from Clavain. No plugin.json array update needed (directory discovery).

### Task 4: Create `intercraft` plugin (largest extraction)

**New files:**
```
plugins/intercraft/
  .claude-plugin/
    plugin.json
  skills/
    agent-native-architecture/
      SKILL.md       (moved from hub/clavain/skills/agent-native-architecture/SKILL.md)
      references/    (moved — 14 reference documents)
  agents/
    review/
      agent-native-reviewer.md  (moved from hub/clavain/agents/review/agent-native-reviewer.md)
  commands/
    agent-native-audit.md       (moved from hub/clavain/commands/agent-native-audit.md)
  CLAUDE.md
  .gitignore
```

**plugin.json:**
```json
{
  "name": "intercraft",
  "version": "0.1.0",
  "description": "Agent-native architecture patterns — design, review, and audit for agent-first applications.",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/intercraft",
  "license": "MIT",
  "keywords": ["agent-native", "architecture", "mcp", "design-patterns", "agents"],
  "skills": ["./skills/agent-native-architecture"],
  "agents": ["./agents/review/agent-native-reviewer.md"],
  "commands": ["./commands/agent-native-audit.md"]
}
```

**Then:** Remove from Clavain: `skills/agent-native-architecture/`, `agents/review/agent-native-reviewer.md`, `commands/agent-native-audit.md`. No plugin.json array update needed (directory discovery).

**Special check:** Verify the agent-native-audit command doesn't reference `${CLAUDE_PLUGIN_ROOT}` paths that would break after extraction.

### Task 5: Create `interdev` plugin

**New files:**
```
plugins/interdev/
  .claude-plugin/
    plugin.json
  skills/
    mcp-cli/
      SKILL.md       (moved from hub/clavain/skills/mcp-cli/SKILL.md)
  CLAUDE.md
  .gitignore
```

**plugin.json:**
```json
{
  "name": "interdev",
  "version": "0.1.0",
  "description": "Developer tooling for Claude Code — MCP CLI interaction and tool discovery.",
  "author": { "name": "MK", "email": "mistakeknot@vibeguider.org" },
  "repository": "https://github.com/mistakeknot/interdev",
  "license": "MIT",
  "keywords": ["mcp", "cli", "developer-tools", "tool-discovery"],
  "skills": ["./skills/mcp-cli"]
}
```

**Then:** Remove `skills/mcp-cli/` from Clavain. No plugin.json array update needed (directory discovery).

### Task 6: Move `finding-duplicate-functions` to `tldr-swinton`

**Move files:**
```
hub/clavain/skills/finding-duplicate-functions/ → plugins/tldr-swinton/skills/finding-duplicate-functions/
```

This includes SKILL.md, scripts/ directory (5 scripts + extract-tokens directory).

**Update:**
- Check if `plugins/tldr-swinton/.claude-plugin/plugin.json` uses directory discovery or has a `skills` array. If array exists, add entry. If directory discovery, just moving files is enough.
- Clavain uses directory discovery — removing the directory is enough.

**Special check:** Verify scripts don't reference Clavain-specific paths or variables.

### Task 7: Cross-reference audit + Update Clavain metadata

**Step 0: Cross-reference audit (MUST run before updating metadata):**
```bash
# Find all references to deleted aliases
grep -rn "lfg\|full-pipeline\|cross-review\|deep-review" \
  hub/clavain/{commands,skills,agents,README.md,CLAUDE.md,agent-rig.json}

# Find all references to moved command
grep -rn "agent-native-audit" \
  hub/clavain/{commands,skills,agents,README.md,CLAUDE.md}

# Find all references to moved skills
grep -rn "slack-messaging\|distinctive-design\|agent-native-architecture\|finding-duplicate-functions\|mcp-cli" \
  hub/clavain/{commands,README.md,CLAUDE.md,agent-rig.json}
```
Fix ALL matches before proceeding.

After audit, update:

1. **`hub/clavain/.claude-plugin/plugin.json`:**
   - Update `description` counts: change "5 agents, 37 commands, 27 skills" to "4 agents, 32 commands, 22 skills"
   - Update companions list in description: add "interslack, interform, intercraft, interdev"
   - No array updates needed (Clavain uses directory discovery)

2. **`hub/clavain/agent-rig.json`:**
   - Update description counts
   - Add 4 new plugins to `recommended` array
   - Fix postInstall message (remove `/lfg` reference, use `/sprint`)

3. **`hub/clavain/README.md`:**
   - Update counts in opening paragraph
   - Update skill/command lists if present

4. **`hub/clavain/CLAUDE.md`:**
   - Update validation commands (skill count should be 22, commands 32, agents 4)
   - Update companion list

5. **`hub/clavain/commands/help.md`:**
   - Delete aliases line (line 23: `> **Aliases:** ...`)
   - Remove agent-native-audit from command table

### Task 8: Add new plugins to marketplace

Add 4 entries to `infra/marketplace/.claude-plugin/marketplace.json`:
- interslack, interform, intercraft, interdev

Each needs: name, source (GitHub URL), description, version, keywords, strict: true.

**Note:** GitHub repos don't exist yet. Create them or use placeholder URLs that get updated when repos are created.

### Task 9: Initialize git repos for new plugins

For each new plugin (interslack, interform, intercraft, interdev):
1. `cd plugins/<name> && git init`
2. Create `.gitignore`
3. Initial commit

### Task 10: Validate

**File count validation:**
- `ls hub/clavain/commands/*.md | wc -l` → 32
- `ls hub/clavain/skills/*/SKILL.md | wc -l` → 22
- `ls hub/clavain/agents/{review,workflow}/*.md | wc -l` → 4

**JSON validity:**
- `python3 -c "import json; json.load(open('hub/clavain/.claude-plugin/plugin.json'))"` → valid
- For each new plugin: `python3 -c "import json; json.load(open('plugins/<name>/.claude-plugin/plugin.json'))"` → valid

**Script syntax:**
- `bash -n` syntax check on any moved scripts

**Cross-reference integrity:**
- Verify NO dangling references to moved/deleted items remain in Clavain
- Verify moved skills/agents/commands exist in their new plugin directories
- Verify marketplace.json is valid JSON with all 4 new entries

## Parallelization

Tasks 2-6 (create new plugins + move files) are fully independent and can run in parallel.
Task 1 (remove aliases) is independent from 2-6.
Task 7 (update metadata) depends on all of 1-6.
Task 8 (marketplace) depends on 2-5 (needs plugin names/versions).
Task 9 (git init) depends on 2-5.
Task 10 (validate) depends on all others.

```
[1] ─────────────────────────────────────────┐
[2] interslack  ─────────────────────────────┤
[3] interform   ─────────────────────────────┤──→ [7] Update metadata ──→ [10] Validate
[4] intercraft  ─────────────────────────────┤──→ [8] Marketplace    ──┘
[5] interdev    ─────────────────────────────┤──→ [9] Git init       ──┘
[6] tldr-swinton ────────────────────────────┘
```

Tasks 1-6 in parallel, then 7-9 in parallel, then 10.
