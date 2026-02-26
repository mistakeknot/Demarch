# Replace `hub/clavain` with `os/clavain` — Analysis

**Date:** 2026-02-22
**Scope:** All files in `/home/mk/projects/Demarch`

## Summary

Replaced all `hub/clavain` references with `os/clavain` across the Demarch monorepo. This reflects the directory restructuring where Clavain moved from `hub/clavain` to `os/clavain`.

## Replacement Statistics

- **Total occurrences replaced:** ~1,620 (1,596 in md/json/log files + ~24 in sh/ts/go/js/py files)
- **Total files modified:** 99 files across 12 git repositories
- **Remaining occurrences:** 0 in source files; residual references exist only in binary/generated artifacts (see below)

### By Repository

| Repository | Files Changed |
|---|---|
| Demarch (root) | 91 files (md/json/log/sh) |
| os/clavain | 54 files |
| core/intercore | 53 files |
| interverse/interflux | 8 files |
| interverse/interserve | 4 files |
| interverse/interkasten | 3 files |
| interverse/interchart | 3 files |
| interverse/intermux | 2 files |
| interverse/intermem | 2 files |
| interverse/interlock | 2 files |
| interverse/intersynth | 1 file |
| interverse/interpath | 1 file |

Note: Files in subprojects appear in both the root Demarch diff and their own subproject git diff.

## Two Patterns Handled

### 1. Absolute paths (`/root/projects/Interverse/hub/clavain`)

These appeared in 11 files, primarily in:
- Plan documents referencing old Interverse layout
- interserve plugin.json (`INTERSERVE_DISPATCH_PATH`)
- interflux review research docs (file references)
- interkasten hierarchy plan (project paths)

These were converted to relative `os/clavain` paths where they appeared in documentation. In compiled Go code (`interserve/cmd/interserve-mcp/main.go`), the absolute path was updated to `/root/projects/Interverse/os/clavain/scripts/dispatch.sh` — this is a runtime dispatch path and needs to remain absolute.

### 2. Relative paths (`hub/clavain/...`)

The bulk of replacements — straightforward `hub/clavain` to `os/clavain` across all file types:
- `.md` (documentation, research, plans, PRDs, brainstorms, solutions, skills, commands, agents)
- `.json` (roadmap, solutions index, scan data, beads exports, settings, plugin manifests)
- `.log` (audit logs, learnings)
- `.sh` (shell scripts — migrate-sprints, lib-intercore, test-integration)
- `.ts` (interkasten hierarchy tests)
- `.go` (interserve main, intercore dispatch spawn, intermux watcher/models)
- `.js` (interchart scanner)
- `.py` (intermem test fixtures)

## Files NOT Modified (Intentionally)

The following contain `hub/clavain` references but were intentionally left unchanged:

| File Type | Reason |
|---|---|
| `.db` (SQLite databases) | Binary format; cannot sed-replace safely |
| `.jsonl` (beads issues) | Historical/immutable issue tracker records |
| `__pycache__/*.pyc` | Compiled Python bytecache; will regenerate |
| `.dolt/noms/*` | Dolt version control internal binary data |
| `bin/interserve-mcp` | Compiled Go binary; will regenerate on rebuild |
| `.intermem/stability.jsonl` | intermem state data |

These will naturally resolve through:
- Rebuilding Go/Python binaries
- Normal beads issue lifecycle (new issues use correct paths)
- `.pyc` cache invalidation on next import

## Verification

```
$ grep -r 'hub/clavain' --include='*.md' --include='*.json' --include='*.log' --include='*.sh' --include='*.py' --include='*.ts' --include='*.js' --include='*.go' . | wc -l
0
```

Zero remaining references in any source file format.

## Post-Replacement Count

```
$ grep -r 'os/clavain' --include='*.md' --include='*.json' --include='*.log' . | wc -l
1767
```

All references now consistently use `os/clavain`.
