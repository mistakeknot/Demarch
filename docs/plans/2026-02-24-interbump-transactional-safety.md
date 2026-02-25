# Plan: Interbump Transactional Safety

**Bead:** iv-c136g
**Phase:** executing (as of 2026-02-25T05:25:27Z)
**Date:** 2026-02-24
**Complexity:** 2/5 (simple)

## Problem

`scripts/interbump.sh` updates version files across two independent git repos (plugin + marketplace) with sequential pushes. Several failure modes can leave inconsistent published state:

1. No preflight checks — script starts mutating files before verifying clean worktrees or reachable remotes
2. `git pull --rebase 2>/dev/null || true` silently swallows rebase conflicts
3. Plugin pushed before marketplace — if marketplace push fails, plugin version is published but marketplace still points to old version
4. No recovery guidance — partial failures leave operator guessing what to undo
5. Script reaches "Done!" even if git operations partially failed (push errors not checked)

## Tasks

### Task 1: Add preflight validation phase
- [x] Before any file mutations, verify:
  - Both worktrees are clean (`git -C $dir diff --quiet && git -C $dir diff --cached --quiet`)
  - Both remotes are reachable (`git -C $dir ls-remote --exit-code origin HEAD`)
  - Required tools present (jq, git, sed)
- [x] Fail fast with clear error message if any check fails

### Task 2: Make git operations fail-loud with phase tracking
- [x] Replace `git pull --rebase 2>/dev/null || true` with explicit error handling
- [x] Track which phase completed: `PHASE_PLUGIN_COMMITTED`, `PHASE_PLUGIN_PUSHED`, `PHASE_MARKETPLACE_COMMITTED`, `PHASE_MARKETPLACE_PUSHED`
- [x] On any git failure, emit recovery instructions based on which phases completed
- [x] Use `set -e` behavior (already set) but add trap for cleanup messaging

### Task 3: Add recovery guidance on failure
- [x] Add `trap` handler that detects which phase failed and prints:
  - What succeeded (which repos were committed/pushed)
  - What failed (the specific operation)
  - Exact commands to recover (e.g., `git -C <path> reset HEAD~1` to undo a commit that wasn't pushed)
- [x] Ensure exit code is non-zero on any partial failure

### Task 4: Guard marketplace push on plugin push success
- [x] Only commit+push marketplace if plugin commit+push fully succeeded
- [x] Add explicit `|| { recovery_message; exit 1; }` after each git push
- [x] Move "Done!" message inside a final success gate that checks all phases completed

## Files to Change

- `scripts/interbump.sh` — all changes in this single file

## Patterns to Follow

- Existing phase-tracking pattern: the script already has distinct sections marked with comments (`# --- Git: plugin repo ---`, `# --- Git: marketplace repo ---`)
- Existing color/echo pattern for status output
- `set -euo pipefail` already set — leverage it, don't fight it

## Out of Scope

- Actual two-phase commit protocol (overkill for local git repos)
- Automated rollback (too risky — guided manual rollback is safer)
- Test harness for interbump (separate bead)
