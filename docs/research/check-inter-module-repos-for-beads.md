# Beads Issues Check Across Inter-Module Repos

**Date:** 2026-02-14  
**Owner:** mistakeknot  
**Method:** Checked `.beads/issues.jsonl` via GitHub API for each repo

## Summary

- **15 repos checked**
- **2 repos** have `.beads/issues.jsonl` with actual content (Clavain, interkasten)
- **1 repo** has the file but it is empty (interfluence)
- **12 repos** do not have the file at all
- **77 open issues** total across all repos (all in Clavain)

## Results by Repo

| Repo | File Exists | Size (bytes) | Total Issues | Open | Closed |
|------|:-----------:|:------------:|:------------:|:----:|:------:|
| **Clavain** | Yes | 259,246 | 357 | 77 | 280 |
| **interkasten** | Yes | 39,244 | 43 | 0 | 43 |
| **interfluence** | Yes | 0 | 0 | 0 | 0 |
| interdoc | No | - | - | - | - |
| interflux | No | - | - | - | - |
| interline | No | - | - | - | - |
| intermute | No | - | - | - | - |
| interpath | No | - | - | - | - |
| interphase | No | - | - | - | - |
| interpub | No | - | - | - | - |
| interwatch | No | - | - | - | - |
| tldr-swinton | No | - | - | - | - |
| tuivision | No | - | - | - | - |
| tool-time | No | - | - | - | - |
| interagency-marketplace | No | - | - | - | - |

## Detailed Findings

### Clavain (259 KB, 357 issues)
- **Open: 77** — the only repo with outstanding open beads issues
- **Closed: 280** — significant history of resolved issues
- This is by far the most active beads user across all checked repos

### interkasten (39 KB, 43 issues)
- **Open: 0** — all issues resolved
- **Closed: 43** — moderate usage, all cleaned up

### interfluence (0 bytes)
- File exists in the `.beads/` directory but is empty (0 bytes)
- Beads was initialized but never used, or was cleared out

### Repos Without `.beads/issues.jsonl` (12 repos)
The following repos returned 404 for `.beads/issues.jsonl`, meaning either:
- The `.beads/` directory does not exist in the repo, or
- The directory exists but `issues.jsonl` is not present, or
- The repo itself does not exist (unlikely given the owner is confirmed)

Repos: interdoc, interflux, interline, intermute, interpath, interphase, interpub, interwatch, tldr-swinton, tuivision, tool-time, interagency-marketplace

## Key Takeaways

1. **Clavain is the priority** — 77 open beads issues need attention or triage
2. **interkasten is clean** — all 43 issues closed, no action needed
3. **12 of 15 repos have no beads tracking** — if beads should be standard across inter-modules, these repos need initialization
4. **interfluence** has an empty issues file — may need cleanup or initialization
