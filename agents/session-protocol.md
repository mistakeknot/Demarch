# Session Protocol

## Agent Quickstart

1. Read root `AGENTS.md` — you're doing it now.
2. Run `bd ready` to see available work.
3. Before editing any module, read its local `AGENTS.md` (or `CLAUDE.md` as fallback).
4. Verify which repo you're in: `git rev-parse --show-toplevel`.
5. When done: `bd close <id>`, commit, `bd sync`, push.

## Git Autosync

This repo has **git-autosync** enabled (`.git-autosync` marker). Claude Code hooks automatically:

- **On session start:** `git pull --rebase --autostash` to start with fresh code.
- **On every Edit/Write:** Debounce 3s, then `git add -A && git commit && git push`. Commits use `chore(sync):` prefix.

**What this means for you:**
- Your edits are pushed to origin within seconds — other agents (Mac or server) see them quickly.
- If push fails (concurrent edit from another agent), the hook auto-rebases and retries.
- `chore(sync):` commits are autosync noise — don't worry about them in git log.
- **You still must follow the Session Close Protocol** (beads, quality gates, intentional commit message, push). Autosync handles incremental safety; session close handles intentional milestones.
- Don't manually push after every small edit — autosync handles that. Save manual commits for meaningful checkpoints.

**Ship validated fixes without asking.** When a fix is validated (read back looks correct, tests pass), commit, push, and publish without pausing to confirm. Wasted round-trips cost more than the fix. Only ask before irreversible actions (publish, delete, merge, bead-close).

**Debugging heuristic:** Check the cheapest observable signals first — is the binary present? (`command -v <tool>`), is the cache stale? (clear and retry), is CWD correct? (`pwd`). Explore complex hypotheses only after ruling out simple causes.

## Instruction Loading Order

Use nearest, task-scoped instruction loading instead of reading every instruction file in the repo.

1. Read root `AGENTS.md` once at session start.
2. Before editing files in a module, read that module's local `AGENTS.md`.
3. If local `AGENTS.md` is missing, read that module's local `CLAUDE.md` as fallback.
4. For cross-module changes, repeat steps 2-3 for each touched module.
5. Resolve conflicts with this precedence: local `AGENTS.md` > local `CLAUDE.md` > root `AGENTS.md` > root `CLAUDE.md`.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File beads for remaining work** - `bd create` for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync              # compatibility sync step (0.50.x syncs, 0.51+ no-op)
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
- External contributors: push to your fork and open a PR instead

## Memory Provenance

> Full conventions: [`~/.claude/memory-conventions.md`](~/.claude/memory-conventions.md)

When writing auto-memory entries, include a source comment so future sessions can trace and verify:
```
# [date:YYYY-MM-DD] <one-line description of what was learned and why>
```
