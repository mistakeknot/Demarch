# Demarch — Agent Development Guide

Open-source autonomous software development agency platform (Intercore, Clavain, Interverse, Autarch, Interspect).

## Quick Reference

```bash
bd ready                                  # See available work
git rev-parse --show-toplevel             # Verify which repo you're in
cd interverse/<name> && uv run pytest tests/structural/ -v  # Plugin tests
cd core/intercore && go test ./...        # Kernel tests
ic publish --patch                        # Publish plugin (Go CLI)
scripts/bump-version.sh <ver>             # Publish plugin (shell)
bd close <id> && bd sync && git push      # Complete work
```

## Topic Guides

| Topic | File | Covers |
|-------|------|--------|
| Architecture | [agents/architecture.md](agents/architecture.md) | Overview, glossary, directory layout, dependency chains, compatibility |
| Session Protocol | [agents/session-protocol.md](agents/session-protocol.md) | Agent quickstart, git autosync, instruction loading order, landing the plane, memory provenance |
| Design Doctrine | [agents/design-doctrine.md](agents/design-doctrine.md) | Philosophy filters, anti-patterns, brainstorming/planning guidelines |
| Development Workflow | [agents/development-workflow.md](agents/development-workflow.md) | Running/testing by module type, publishing, cross-repo changes |
| Plugin Publishing | [agents/plugin-publishing.md](agents/plugin-publishing.md) | Publish gate, version bumping (interbump), ecosystem diagram |
| Beads Workflow | [agents/beads-workflow.md](agents/beads-workflow.md) | Bead tracking, label taxonomy, recovery scripts, roadmap |
| Critical Patterns | [agents/critical-patterns.md](agents/critical-patterns.md) | Six must-know patterns from production failures |
| Prerequisites | [agents/prerequisites.md](agents/prerequisites.md) | Required tools, secrets, Go module path convention |
| Operational Guides | [agents/operational-guides.md](agents/operational-guides.md) | Guide index, prior solutions search, operational notes |

## Session Close Protocol

1. File beads for remaining work (`bd create`)
2. Run quality gates (tests, linters, builds)
3. Close/update beads (`bd close <id>`)
4. **Push** — `git pull --rebase && bd sync && git push`
5. Verify `git status` shows "up to date with origin"

Work is NOT complete until `git push` succeeds. See [agents/session-protocol.md](agents/session-protocol.md) for full details.

<!-- bv-agent-instructions-v1: beads commands and workflow covered in agents/beads-workflow.md -->

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
