---
name: interdoc
description: "Recursive AGENTS.md generator with integrated GPT 5.2 Pro critique, CLAUDE.md harmonization, incremental updates, diff previews, and smart monorepo scoping. Cross-AI compatible."
---
# Gemini Skill: interdoc

You have activated the interdoc capability.

## Base Instructions
# AGENTS.md

> Cross-AI documentation for interdoc. Works with Claude Code, Codex CLI, and other AI coding tools.

## Overview

**interdoc** is a Claude Code plugin that generates and maintains AGENTS.md documentation using parallel subagents. It analyzes project structure, spawns agents per directory, and consolidates into coherent documentation.

**Why AGENTS.md?** Claude Code reads both AGENTS.md and CLAUDE.md, but AGENTS.md is the cross-AI standard that also works with Codex CLI and other AI coding tools.

**Plugin Type:** Claude Code skill plugin
**Plugin Namespace:** `interdoc` (from interagency-marketplace)
**Current Version:** 5.0.0

## Repository Structure

```
/ 
├── .claude/
│   └── agents/
│       └── interdocumentarian.md  # Claude subagent for AGENTS.md authoring
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata and version (source of truth)
├── .codex/
│   └── INSTALL.md            # Codex CLI install instructions
├── hooks/
│   ├── check-updates.sh     # Hook script (disabled by default)
│   └── check-commit.sh      # Hook script (disabled by default)
│   ├── git/
│   │   ├── post-commit       # Advisory commit hook
│   │   └── install-post-commit.sh
│   └── tools/
│       └── interdoc-audit.sh  # Coverage + lint helper
├── scripts/
│   ├── drift-fix.sh       # Structural auto-fix (renames, deletions, link fixes)
│   ├── bump-version.sh    # Version management
│   ├── check-versions.sh  # Version consistency checker
│   └── interdoc-generator.sh
├── skills/
│   └── interdoc/
│       └── SKILL.md         # Main skill definition
├── docs/
│   ├── plans/               # Design documents
│   └── TEST_PLAN.md         # Test cases from splinterpeer analysis
├── tests/
│   ├── fixtures/
│   │   └── setup-test-repo.sh  # Test repo scaffolding
│   ├── test-drift-fix-*.sh     # drift-fix.sh test suite
│   └── run-all.sh              # Test runner
├── README.md                # User-facing documentation
├── CLAUDE.md                # Claude-specific settings only
└── AGENTS.md                # This file - cross-AI documentation
```

## The Skill

| Skill | Trigger | Use Case |
|-------|---------|----------|
| `interdoc` | Natural language (hooks disabled by default) | Generate/update AGENTS.md documentation |

**Discovery:** In Claude Code, ask “List all available Skills” to see interdoc, or run `/interdoc`.

**Advisory hook (optional):** Run `./hooks/git/install-post-commit.sh` to enable a non-blocking reminder after commits.

**Optional modes:** Use phrases like "change-set update", "doc coverage", or "doc lint" to trigger specialized behaviors.

> **Note:** This is a Claude Code plugin skill, invoked via natural language (e.g., "generate documentation for this project"). It is NOT a slash command.

## Key Features

- **Parallel subagents**: Spawns agents per directory for fast analysis
- **Incremental updates**: Appends new content, preserves existing documentation
- **CLAUDE.md harmonization**: Migrates docs from CLAUDE.md → AGENTS.md
- **Unified diff previews**: Shows actual diffs before applying
- **Dry run + cached apply**: Preview changes and apply last preview without re-analysis
- **Structural auto-fix**: Deterministic rename/deletion/link fixes without LLM tokens (`/interdoc fix`)
- **JSON schema output**: Subagents return structured JSON with sentinel markers
- **Git-aware**: Uses commit messages and diffs for update context
- **Scalability guardrails**: Concurrency limits, batch processing for large repos
- **Claude subagent option**: Specialized subagent for high-quality AGENTS.md content

## Hooks (Disabled by Default)

Hooks are not enabled by default. Manual invocation is the standard flow.

## Development

### This is Documentation-Driven

There is **no source code** to build or test. The "implementation" is the skill documentation and shell scripts.

**To modify behavior:**
- Edit `skills/interdoc/SKILL.md` to change workflows
- Edit `hooks/*.sh` to change trigger logic
- Update `README.md` for user-facing documentation
- Update `.claude-plugin/plugin.json` for metadata/version changes

### Testing Changes

1. Make changes to SKILL.md or hook files
2. Commit and push to GitHub
3. Run `claude plugin update interdoc@interagency-marketplace` to refresh local cache
4. Trigger the skill to verify behavior

See `docs/TEST_PLAN.md` for comprehensive test cases.

## Version Management

**Version is declared in `.claude-plugin/plugin.json` (root level).**

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Bug fix, docs clarification | Patch | 4.3.0 → 4.3.1 |
| New feature, workflow change | Minor | 4.3.0 → 4.4.0 |
| Breaking change | Major | 4.3.0 → 5.0.0 |

### Bump Version

After committing skill changes:

```bash
# 1. Edit plugin.json and increment version
# 2. Commit and push
git add .claude-plugin/plugin.json
git commit -m "Bump version to X.Y.Z"
git push
```

### Update the Marketplace

The plugin is distributed via `interagency-marketplace`. After pushing version changes:

1. Edit `~/interagency-marketplace/.claude-plugin/marketplace.json`
2. Update the `interdoc` entry version
3. Commit and push
4. Refresh local cache:
   ```bash
   claude plugin marketplace update interagency-marketplace
   claude plugin update interdoc@interagency-marketplace
   ```

## Commit Workflow

1. Edit the relevant files (SKILL.md, hooks, etc.)
2. Commit with descriptive message
3. **Bump version in plugin.json**
4. Commit version bump
5. Push both commits
6. **Update ~/interagency-marketplace** with new version
7. Push marketplace changes

## GPT Review Phase

After generation/update, interdoc sends AGENTS.md to GPT 5.2 Pro via Oracle for independent critique.

### How It Works

1. Pre-flight check verifies Oracle session
2. Gathers evidence (git changes, commit messages, detected languages)
3. Sends AGENTS.md + source files to GPT with critic prompt
4. Parses structured JSON suggestions
5. Classifies by significance:
   - **Non-controversial** (auto-applied): low severity, additive suggestions
   - **Significant** (user-prompted): high severity, corrections, 3+ suggestions

### Oracle Dependencies

- Oracle CLI installed (`npm i -g @steipete/oracle`)
- Active ChatGPT session (X11 stack: Xvfb on :99, Chrome)
- Environment: `DISPLAY=:99 CHROME_PATH=/usr/local/bin/google-chrome-wrapper`

### Helper Scripts

- `hooks/tools/oracle-review.sh` — Sends AGENTS.md to GPT for critique
- `hooks/tools/sanitize-review.sh` — Strips code fences, citation artifacts
- `hooks/tools/secret-scan.sh` — Filters dangerous files before Oracle upload

### Troubleshooting

- **Oracle session expired:** Run `oracle-login` via NoVNC, complete Cloudflare check
- **X11 not running:** Check `pgrep -f "Xvfb :99"`, restart if needed
- **Review skipped:** Normal if Oracle unavailable — generation still works

<quick_reference>

## Command Quick Reference

| Trigger | Mode | Scope |
|---------|------|-------|
| "generate AGENTS.md" | Generation | Full project |
| "update AGENTS.md" | Update | Changed directories |
| "change-set update" | Update | Git diff only |
| "doc coverage" | Report | Coverage stats |
| "lint AGENTS.md" / "doc lint" | Lint | Style warnings |
| "fix stale references" / "interdoc fix" | Fix | Structural only (no LLM) |
| "dry run" | Any + Preview | No writes |

</quick_reference>

## Recent Changes (January 2026)

### v4.4.3 - Phase 1 Roadmap: Coverage + Lint + Change-Set
- Added change-set update mode, coverage report, and style lint triggers
- Added optional local audit script (coverage + lint)

### v4.4.0 - Disable Hooks by Default
- Removed auto-loaded hooks to avoid Claude Code hook validation errors
- Manual invocation is the default workflow

### v4.3.3 - Dry Run + Preview Cache
- Added dry-run mode with summary + diff preview
- Added "apply last preview" cache (HEAD-validated)

### v4.3.2 - Claude Subagent + Codex Install
- Added interdocumentarian Claude subagent for directory docs
- Added Codex CLI install instructions

### v4.3.0 - Splinterpeer Robustness Improvements
- Rewrote hooks with repo-root handling and HEAD-tracking
- Added JSON schema with sentinel markers for subagent output
- Added deterministic CLAUDE.md heading allowlist
- Added scalability guardrails (concurrency limits, batching)
- Fixed find commands for filename safety
- Added comprehensive test plan

### v4.2.0 - CLAUDE.md Harmonization
- Initial CLAUDE.md → AGENTS.md migration feature

### v4.1.0 - Improved Verification and UX
- Better subagent verification before consolidation
- Individual file review option

---

*Last updated: 2026-01-18*


