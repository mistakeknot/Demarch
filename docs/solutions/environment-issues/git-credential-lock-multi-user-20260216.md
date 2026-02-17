---
module: System
date: 2026-02-16
problem_type: environment_issue
component: git
symptoms:
  - "fatal: unable to get credential storage lock in 1000 ms: Permission denied"
  - "temp_git_* directories accumulating in plugin cache"
  - ".orphaned_at markers appearing after failed plugin installs"
  - "claude plugins install fails silently"
root_cause: credential_file_lock
resolution_type: config_change
severity: high
tags: [git, credentials, multi-user, claude-user, permissions, ACL, plugin-install]
---

# Git Credential Store Lock Failure in Multi-User Setup

## Problem

When running Claude Code as `claude-user` (a non-root user whose dotfiles are symlinked to `/root/`), all git operations requiring authentication fail with:

```
fatal: unable to get credential storage lock in 1000 ms: Permission denied
```

This causes cascading failures: `claude plugins install` can't clone repos, leaving `temp_git_*` debris and `.orphaned_at` markers in the plugin cache. Plugins silently fail to install.

## Environment

- Root user owns all config files, claude-user accesses them via symlinks
- `/home/claude-user/.git-credentials` → `/root/.git-credentials`
- `/home/claude-user/.gitconfig` → `/root/.gitconfig`
- POSIX ACLs grant claude-user `rw` on `.git-credentials`

## Root Cause

Git's credential store creates a lock file (`git-credentials.lock`) using `O_CREAT|O_EXCL` in the **same directory** as the credentials file. When credentials live at `/root/.git-credentials`, the lock file must be created in `/root/`.

Even though claude-user has ACL access to the credentials file itself, creating a **new file** in `/root/` requires write permission on the directory. The `/root/` directory is `701` (owner rwx, group none, other execute-only), so claude-user can traverse it but cannot create files in it.

ACLs on `/root/` don't help because git's atomic `O_CREAT|O_EXCL` bypasses directory-level ACL inheritance for the lock creation step.

## What Didn't Work

- **ACLs on the credentials file**: Claude-user can read/write the file, but can't create the `.lock` sibling
- **Default ACLs on `/root/`**: Lock file creation still fails
- **Group permissions on `/root/`**: Would compromise root's home directory security

## Solution

Move the credentials file to a directory where claude-user has full write access (including file creation for locks):

```bash
# 1. Copy credentials to .claude/ (which has default ACLs for claude-user)
cp /root/.git-credentials /root/.claude/git-credentials
chmod 660 /root/.claude/git-credentials
setfacl -m u:claude-user:rw /root/.claude/git-credentials

# 2. Update gitconfig to use the new path
# In /root/.gitconfig, change:
#   [credential]
#       helper = store
# To:
#   [credential]
#       helper = store --file /root/.claude/git-credentials
```

The `/root/.claude/` directory already has default ACLs granting `claude-user:rwx`, so the lock file (`git-credentials.lock`) will be created with proper permissions automatically.

## Why This Works

1. `/root/.claude/` has `default:user:claude-user:rwx` ACL → new files inherit write access
2. Git creates `git-credentials.lock` in the same dir as the credentials file
3. Lock creation in `/root/.claude/` succeeds because claude-user can create files there
4. The symlink chain (`/home/claude-user/.gitconfig` → `/root/.gitconfig`) still works — gitconfig just points to a different credential file path

## Verification

```bash
# As claude-user, test credential access:
su -s /bin/bash -c 'HOME=/home/claude-user git credential-store \
  --file /root/.claude/git-credentials get <<EOF
protocol=https
host=github.com
EOF' claude-user
# Should output username and password

# Test a clone:
su -s /bin/bash -c 'HOME=/home/claude-user git ls-remote https://github.com/USER/REPO.git HEAD' claude-user
# Should output SHA without "credential lock" error
```

## Cleanup After Fix

```bash
# Remove accumulated temp_git_* from failed installs
rm -rf ~/.claude/plugins/cache/temp_git_*

# Remove .orphaned_at markers from current plugin versions
find ~/.claude/plugins/cache -maxdepth 4 -name ".orphaned_at" -not -path "*/temp_git_*"
# Selectively remove markers for plugins you want to re-enable

# Old credential file can be removed (optional)
# rm /root/.git-credentials
```

## Cross-References

- `docs/solutions/integration-issues/plugin-loading-failures-interverse-20260215.md` — related plugin loading failures
- `docs/solutions/patterns/critical-patterns.md` — compiled MCP server launcher pattern
- MEMORY.md: "Plugin Cache & Loading" section
