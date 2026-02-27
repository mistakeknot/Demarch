# Verify Commits Reference Valid Beads

**Date:** 2026-02-27
**Scope:** Git commits from 2026-02-24 to 2026-02-27 in Demarch monorepo
**Purpose:** Verify that all bead IDs referenced in git commit messages exist in the beads database (`.beads/issues.jsonl`)

## Summary

- **Total commits in range:** 87
- **Commits referencing bead IDs (subject line):** 23
- **Commits without bead IDs:** 64
- **Unique bead IDs in subject lines:** 23
- **Additional bead IDs in commit bodies:** 9 (32 total unique)
- **Beads found (recovered):** 22
- **Beads found (original):** 1
- **Beads found (recovered-doc):** 5
- **Beads found (roadmap-recovery):** 1
- **Beads found (recovered, closed as duplicate):** 1
- **MISSING from database:** 2

## Missing Beads (GAPS)

These bead IDs appear in commit messages but have **no corresponding entry** in the beads database:

| Bead ID | Commit | Context |
|---------|--------|---------|
| `iv-5zoaq` | `ab5b549` docs: add unified logging brainstorm, PRD, plan, and plugin adoption guide | Commit body: "Sprint iv-5zoaq artifacts for iv-yy1l3". Appears to be a sprint/sub-task ID for the unified logging epic (iv-yy1l3). |
| `iv-446o7.1` | `33b491c` docs: complete secret-scan remediation for all 4 repos | Commit body: "Closes: iv-446o7.1". Sub-task .1 of iv-446o7; note that iv-446o7.2 exists as a recovered bead but .1 does not. |

## Full Bead Verification Table

### Beads from Commit Subject Lines (23 IDs)

| Bead ID | Status | Type | Commit(s) | Title |
|---------|--------|------|-----------|-------|
| `iv-00liv` | RECOVERED | task/P4 | `d195758` | feat: add topic-based message categorization for cross-cutting discovery |
| `iv-1opqc` | RECOVERED | task/P4 | `980084a` | fix: install.sh dry-run crash and modpack JSON parsing |
| `iv-1xtgd` | RECOVERED | task/P4 | `f58b378` | chore: close iv-1xtgd epic + iv-brcmt (shell hardening complete) |
| `iv-446o7.2` | RECOVERED | task/P4 | `dadd1a4` | ci: add Dependabot config for automated dependency updates |
| `iv-7kg37` | RECOVERED | task/P4 | `0fad00e` | feat: add broadcast messaging with contact policy filtering and rate limiting |
| `iv-914cu` | RECOVERED | task/P4 | `7fc794a` | feat: unified Codex install path + legacy superpowers/compound cleanup |
| `iv-9hx1t.1` | RECOVERED | task/P4 | `1ba7d94` | refactor: align module path to github.com/mistakeknot/intercore |
| `iv-be0ik.1` | RECOVERED | task/P4 | `26a15c9`, `d8b3344` | docs: add CI baseline plan for Go repos |
| `iv-be0ik.2` | RECOVERED | task/P4 | `1d9f322` | ci: add test-running CI workflow |
| `iv-brcmt` | RECOVERED (CLOSED) | task/P4 | `f58b378` | Closed as duplicate of iv-1xtgd (safe dedupe pass) |
| `iv-c136g` | RECOVERED | task/P4 | `9aa6123`, `d8b3344` | feat(interbump): add transactional safety + recovery guidance |
| `iv-cl86n` | RECOVERED | task/P4 | `cf39586` | feat(intercore): add Go wrapper for ic CLI |
| `iv-eblwb` | RECOVERED | task/P4 | `d90efce` | docs: add flux-gen UX review agents and specs |
| `iv-gyq9l` | RECOVERED | task/P4 | `fd8d07f` | docs: brainstorm and plan for intent submission mechanism |
| `iv-jay06` | RECOVERED | task/P4 | `94ab91b` | docs: add interbase multi-language SDK brainstorm, PRD, and plan |
| `iv-moyco` | RECOVERED | task/P4 | `6edc389` | feat: add mcpfilter package for startup-time tool profile filtering |
| `iv-mwoi7` | RECOVERED | task/P4 | `4c3915e` | feat: add orchestrate.py with DAG-based Codex agent dispatch |
| `iv-sz3sf` | RECOVERED | task/P4 | `5b8a7e2` | feat: implement agent claiming protocol |
| `iv-t4pia` | RECOVERED | task/P4 | `41d6089` | feat: add 4-level contact policy for per-agent messaging access control |
| `iv-wie5i.1` | RECOVERED | task/P4 | `acf0df8` | feat: penalize untouched interject beads in discovery ranking |
| `iv-wnurj` | RECOVERED | task/P4 | `fffcd50` | docs: update ToolError guide with middleware adoption and add sprint plan |
| `iv-yc2m5` | RECOVERED | task/P4 | `57ed53b` | feat: add structural fallback mode to gen-skill-compact |
| `iv-ynbh` | ORIGINAL | feature/P3 | `383da6e` | Agent trust and reputation scoring via interspect |

### Additional Beads from Commit Bodies (9 IDs)

| Bead ID | Status | Recovery Type | Title |
|---------|--------|---------------|-------|
| `iv-3wmf2` | EXISTS | recovered-doc | Intermap Python Sidecar |
| `iv-446o7.1` | **MISSING** | -- | Secret-scan remediation sub-task (referenced in "Closes: iv-446o7.1") |
| `iv-5zoaq` | **MISSING** | -- | Unified logging sprint ID (referenced as "Sprint iv-5zoaq artifacts") |
| `iv-6dqrj` | EXISTS | recovered-doc | Review Quality Feedback Loop |
| `iv-b7ecy` | EXISTS | recovered-doc | ic Binary in Install Path |
| `iv-bg0a0` | EXISTS | recovered-doc | Adopt mcp_agent_mail Patterns |
| `iv-dxsow` | EXISTS | recovered-doc | Search Surface Documentation Plan |
| `iv-gkory` | EXISTS | roadmap-recovery | Missing roadmap bead (sdk/interbase/docs/roadmap.md) |
| `iv-npvnv` | EXISTS | recovered-doc | Stricter Schema Validation for the Kernel Interface |
| `iv-yy1l3` | EXISTS | recovered | feat(observability): unified structured logging and trace propagation |

## Recovery Quality Assessment

### All recovered beads share these characteristics:
- **Created date:** 2026-02-27 (recovery date, not original creation)
- **Owner:** mistakeknot (generic recovery owner)
- **Priority:** P4 (default placeholder priority)
- **Description:** "Recovered placeholder bead created from git commit metadata after Beads data loss"
- **External link:** Git commit SHA linking back to the originating commit

### The one original bead (`iv-ynbh`) differs:
- **Created:** 2026-02-15 (pre-dates the loss window)
- **Owner:** mk (actual owner)
- **Priority:** P3 (manually triaged)
- **Description:** Full context with problem statement, solution outline, and references
- **Type:** feature (not generic task)

This contrast highlights the information loss in recovered beads: original priority, owner, type, creation date, and detailed descriptions are all lost.

## Recommendations

1. **Create beads for the 2 missing IDs:**
   - `iv-5zoaq` -- Sprint task for unified logging (iv-yy1l3). Context: commit `ab5b549`.
   - `iv-446o7.1` -- Secret-scan remediation sub-task, sibling of iv-446o7.2. Context: commit `33b491c`. Should likely be marked CLOSED since the commit says "Closes: iv-446o7.1".

2. **Audit recovered bead metadata:** The 22 recovered beads all have P4/task/OPEN status. Some (like `iv-1xtgd` "shell hardening complete" and `iv-brcmt`) should be CLOSED based on commit context. Consider a pass to update status from commit semantics.

3. **64 commits lack bead IDs entirely.** Many are chore/docs/fix commits that may not need tracking, but some (`feat(security): add secret-scanning baseline rollout toolkit`, `docs: implementation plan for Interverse plugin decomposition (38 tasks)`) represent significant work without bead linkage.
