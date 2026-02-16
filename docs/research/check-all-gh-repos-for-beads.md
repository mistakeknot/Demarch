# Beads JSONL Audit Across GitHub Repos

**Date:** 2026-02-14  
**Owner:** mistakeknot  
**Method:** `gh api repos/OWNER/REPO/contents/.beads/issues.jsonl`

## Summary

Checked 34 repos for `.beads/issues.jsonl` files. **3 repos have beads with actual content**, 1 has an empty file, and 30 have no beads file at all.

## Repos With Beads Content

| Repo | File Size (bytes) | Line Count | Status |
|------|-------------------|------------|--------|
| **Typhon** | 88,143 | 78 | Largest beads file |
| **agent-rig** | 17,076 | 10 | Medium |
| **interbench** | 6,505 | 9 | Small |
| **Undersketch** | 0 | 0 | Empty file (exists but no content) |

## Repos Without Beads (No `.beads/issues.jsonl`)

These 30 repos returned 404 — no `.beads/issues.jsonl` file exists:

1. Agaroham
2. Autarch
3. Derkhan
4. Horza
5. Interlens
6. Mawhrin
7. Ong-Back
8. Ong-Lots
9. XULFbot
10. afterthem
11. agmodb
12. auracoil
13. beadmaster
14. conductor-poc
15. dotfiles
16. dragonflux
17. jawncloud
18. mcp-musicbox
19. ong-lots-dataset
20. pattern-royale
21. projectmerlin
22. setupol
23. spiderthem
24. tasm
25. tempo-conductor
26. tldr-bench-datasets
27. tldrs-vhs
28. tronbombadil
29. viberary
30. wikifeedia

## Previously Known Repos (Skipped)

These 15 repos were excluded from this check as they were already known:

- Clavain, interdoc, interfluence, interflux, interkasten, interline, intermute, interpath, interphase, interpub, interwatch, tldr-swinton, tuivision, tool-time, interagency-marketplace

## Notes

- **Typhon** has the largest beads file by far (88KB, 78 issues), suggesting significant issue tracking activity.
- **Undersketch** has the `.beads/` directory structure initialized but the `issues.jsonl` file is empty (0 bytes).
- The vast majority of repos (30/34 = 88%) have no beads tracking at all.
- Line counts were verified using both the base64 contents API and the raw content API to ensure accuracy.
