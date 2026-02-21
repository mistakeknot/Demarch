# Wave 1 Classification Summary: Interverse Root Solution Docs

**Reviewed:** 16 docs | **Date:** 2026-02-21

## Coverage Assessment

10 of 16 docs are already well-covered by existing guides and memory. The four consolidated guides (`plugin-troubleshooting.md`, `shell-and-tooling-patterns.md`, `multi-agent-coordination.md`, `data-integrity-patterns.md`) referenced in MEMORY.md do an excellent job absorbing the detailed solution docs.

## Action Items (6 docs need work)

1. **CLAUDE.md update** (1 doc): `critical-patterns.md` is a "required reading" file with no discoverable path from CLAUDE.md. Add a pointer in Interverse CLAUDE.md so it is surfaced every session.

2. **MEMORY.md additions** (4 docs): Four lessons are not yet in MEMORY.md or any guide:
   - `argparse-parents-subparser-default-overwrite` -- Python CLI gotcha, cross-cutting
   - `cas-spawn-link-orphan-cleanup` -- CAS+orphan pattern for create-then-link operations
   - `intercore-schema-upgrade-deployment` -- binary rebuild required before `ic init`
   - `token-accounting-billing-vs-context` -- billing tokens vs effective context (630x gap)

3. **Prune candidates** (2 docs): Both plugin-loading incident reports (Feb 15 and Feb 17) are fully superseded by `plugin-troubleshooting.md` guide + `critical-patterns.md`. They can be kept as historical record but add no net-new knowledge.

## Cross-Cutting Patterns

8 of 16 docs contain lessons applicable beyond the Interverse root (argparse, CAS, guard fallthrough, set -e, synthesis, token accounting, WAL, jq null safety). These are the most valuable docs -- their patterns recur across projects.

## TOCTOU doc (Feb 21) note

The newest doc (`toctou-gate-check-cas-dispatch`) overlaps with existing MEMORY.md entries on TOCTOU and terminal status exhaustiveness, but adds the specific tx-scoped querier wrapper pattern and the "CAS alone is insufficient for terminal states" insight. Worth a memory update.
