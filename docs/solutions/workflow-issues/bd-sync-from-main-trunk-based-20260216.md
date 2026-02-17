---
module: System
date: 2026-02-16
problem_type: workflow_issue
component: beads
symptoms:
  - "bd sync --from-main: Error: no git remote configured"
  - "bd sync works but bd sync --from-main fails"
  - "Session handoff hook blocked by sync error"
root_cause: wrong_flag
resolution_type: workflow_fix
severity: medium
tags: [beads, bd, sync, trunk-based, git, workflow]
---

# `bd sync --from-main` Fails on Trunk-Based Repos

## Problem

The session handoff protocol (clavain's session-handoff.sh) instructs Claude to run `bd sync --from-main`, which consistently fails with:

```
Error: no git remote configured
```

This happens even though `git remote -v` shows a properly configured `origin` remote.

## Root Cause

`--from-main` is designed for **ephemeral branch** workflows — when you're on a feature branch and need to pull beads state from main. It requires a `sync.branch` config and performs git operations against a dedicated sync branch.

In **trunk-based** workflows (committing directly to main), `--from-main` is the wrong flag. The error "no git remote configured" is misleading — it means beads can't find the sync-branch infrastructure, not that git has no remote.

## Solution

Use `bd sync` (no flags) for trunk-based workflows:

```bash
# Trunk-based (our workflow): just export DB → JSONL
bd sync

# Ephemeral branches: pull beads state from main
bd sync --from-main  # Only for feature branches
```

`bd sync` without flags exports the database to `issues.jsonl`, which is all that's needed before committing on main.

## Session Handoff Fix

The handoff protocol in MEMORY.md and clavain's session-handoff skill should use:

```bash
bd sync           # NOT: bd sync --from-main
```

## Beads Sync Modes Reference

| Command | Use Case | What It Does |
|---------|----------|-------------|
| `bd sync` | Trunk-based (main branch) | Export DB → JSONL |
| `bd sync --import` | After `git pull` | Import JSONL → DB |
| `bd sync --from-main` | Ephemeral branches | Pull beads from main branch |
| `bd sync --full` | Legacy full sync | Pull → merge → export → commit → push |

## Cross-References

- Beads docs: `bd sync --help`
- Session handoff hook: clavain `hooks/session-handoff.sh`
