# Verify Docs Reference Valid Beads

> Created: 2026-02-27 | Task: Cross-reference bead IDs in documentation against beads database

## Summary

Scanned all markdown files in `docs/brainstorms/`, `docs/plans/`, `docs/roadmaps/`, `docs/guides/`, `docs/research/`, `docs/solutions/`, `docs/prds/`, and `docs/demarch-roadmap.md`, plus `docs/roadmap.json`, for bead ID references (pattern `iv-XXXXX` or `iv-XXXXX.N`).

| Metric | Count |
|--------|-------|
| Total unique bead IDs found in docs | 501 |
| Template/test/example IDs excluded | 18 |
| Genuine IDs checked against DB | 483 |
| Found in beads database | 444 |
| **Confirmed missing from database** | **39** |
| — Missing subtasks (parent exists) | 15 |
| — Missing top-level beads | 24 |

**Overall health: 91.9% of doc-referenced beads exist in the database.**

## Excluded Template/Example IDs (18)

These are documentation examples, test fixtures, or hypothetical scenarios — not real beads:

`iv-abc`, `iv-abc1`, `iv-abc12`, `iv-def`, `iv-ghi`, `iv-foo`, `iv-test`, `iv-test1`, `iv-test2`, `iv-test3`, `iv-test123`, `iv-block`, `iv-force`, `iv-scout`, `iv-xxx`, `iv-123`, `iv-sp1k`, `iv-xesrg`

## Missing Beads: Subtasks (15)

These subtasks are referenced in docs but missing from the database. Their parent beads DO exist.

### iv-eblwb.1 through iv-eblwb.12 (12 subtasks)

- **Parent:** iv-eblwb (exists — "[recovered] docs: add flux-gen UX review agents and specs")
- **Referenced in:** `docs/research/create-p2-beads-12-items.md`
- **Nature:** 12 planned P2 subtasks for Autarch/flux-gen UX improvements. The research doc defines them but they were never created as beads.
- **Subtask titles (from doc):**
  - .1 — Messages Route Only to Active View
  - .2 — (and 10 more similar Autarch UX features/bugs)

### iv-npvnv.1, iv-npvnv.2 (2 subtasks)

- **Parent:** iv-npvnv (exists — "[recovered-doc] Stricter Schema Validation for the Kernel Interface")
- **Referenced in:** `docs/brainstorms/2026-02-26-kernel-schema-validation-brainstorm.md`
- **Nature:** Two proposed subtasks from the brainstorm:
  - .1 (P0) — API contract snapshots + CI gate
  - .2 (P1) — Versioned migration framework

### iv-446o7.1 (1 subtask)

- **Parent:** iv-446o7 (exists — iv-446o7.2 exists as a recovered bead)
- **Referenced in:** `docs/guides/secret-scanning-baseline.md`, `docs/research/verify-commits-reference-valid-beads.md`
- **Nature:** Secret-scan remediation sub-task. Commit `33b491c` references "Closes: iv-446o7.1" but the bead was never created. Sibling iv-446o7.2 was recovered.

## Missing Beads: Top-Level (24)

### From unified-structured-logging-and-tracing plan (6 beads)

| ID | Context |
|----|---------|
| iv-0kn9y | Referenced as task bead in plan (Task 4/5 area) |
| iv-9993w | Referenced as task bead in plan (Task 6 area) |
| iv-cv9yi | Referenced as task bead in plan (Task 8 area) |
| iv-g6gj4 | Wiring task bead, referenced multiple times across Tasks 2-4 |
| iv-ifsxm | Referenced as task bead in plan (Task 7 area) |
| iv-5zoaq | Sprint ID for unified logging epic (parent: iv-yy1l3). Referenced in PRD, brainstorm, and commit `ab5b549` |

**Source:** `docs/plans/2026-02-26-unified-structured-logging-and-tracing.md`, `docs/prds/2026-02-26-unified-structured-logging-and-tracing.md`

### From clavain-cli-go-migration plan (4 beads)

| ID | Context |
|----|---------|
| iv-5b6wu | Feature F3 bead |
| iv-88dwi | Feature F4 bead |
| iv-udul3 | Feature F2 bead |
| iv-uunsq | Feature F5 bead |

**Source:** `docs/plans/2026-02-25-clavain-cli-go-migration.md`

### From native-kernel-coordination plan (4 beads)

| ID | Context |
|----|---------|
| iv-gibz3 | Task bead |
| iv-nu9kx | Task bead |
| iv-qaoly | Task bead |
| iv-sg04f | Task bead |

**Source:** `docs/plans/2026-02-25-native-kernel-coordination.md`

### From create-6-autarch-self-hosting-beads research (5 beads)

| ID | Context |
|----|---------|
| iv-62f6e | P1 — [autarch] Kernel visibility: read Intercore DB in Bigend |
| iv-77a0w | P2 — [autarch] Implement stubbed TUI commands (New Spec, New Epic, etc.) |
| iv-fsuaj | P3 — [autarch] Interspect dashboard: surface profiler data in TUI |
| iv-mj16n | P3 — [autarch] Sprint context: project Clavain state into TUI |
| iv-vtcwi | P2 — [autarch] Intent submission: Coldwine write path to Clavain/Intercore |

**Source:** `docs/research/create-6-autarch-self-hosting-beads.md`

### From adopt-mcp-agent-mail-patterns plan (3 beads)

| ID | Context |
|----|---------|
| iv-osph4 | Decision bead: sender identity decision |
| iv-upzm9 | Decision bead (already resolved per plan text) |
| iv-x46ly | Decision bead (already resolved per plan text) |

**Source:** `docs/plans/2026-02-24-adopt-mcp-agent-mail-patterns.md`, `docs/brainstorms/2026-02-24-adopt-mcp-agent-mail-patterns-brainstorm.md`

### From context-file-audit research (2 beads)

| ID | Context |
|----|---------|
| iv-0q6zu | P3 experiment design bead |
| iv-7mk87 | Bead for the audit itself |

**Source:** `docs/research/context-file-audit.md`

## Analysis by Category

### Plan-defined beads never created (17)

The largest category. These are bead IDs that plan documents reference as task/feature identifiers, but the beads were never actually created in the database. This is typical of plans that define future work items inline — the plan author assigned IDs but never ran `bd create`.

Affected plans:
- `2026-02-26-unified-structured-logging-and-tracing` (6 beads)
- `2026-02-25-clavain-cli-go-migration` (4 beads)
- `2026-02-25-native-kernel-coordination` (4 beads)
- `2026-02-24-adopt-mcp-agent-mail-patterns` (3 beads)

### Research-proposed beads never created (7)

Research docs that proposed new beads with specific IDs, but the beads were never materialized:
- `create-6-autarch-self-hosting-beads.md` (5 beads)
- `context-file-audit.md` (2 beads)

### Subtasks never materialized (15)

Parent beads exist but their documented subtasks don't:
- iv-eblwb subtasks (12) — from `create-p2-beads-12-items.md`
- iv-npvnv subtasks (2) — from kernel schema validation brainstorm
- iv-446o7.1 (1) — secret-scan remediation (sibling .2 was recovered)

## Recommendations

1. **Unified logging plan beads (6):** These should be created if the sprint is still active. The plan references them as concrete task assignments.

2. **Clavain Go migration beads (4):** Same — create if the migration is proceeding.

3. **Native kernel coordination beads (4):** Same pattern.

4. **Autarch self-hosting beads (5):** The research doc explicitly intended these to be created. They represent a well-defined dependency tree.

5. **iv-eblwb subtasks (12):** The research doc `create-p2-beads-12-items.md` was likely a plan to create these. They should be materialized.

6. **MCP agent-mail decision beads (3):** The plan says these are "already resolved" — they may have been decided informally without beads. Could be skipped or created as closed.

7. **iv-446o7.1:** Should be created as closed (the commit that closes it exists: `33b491c`).

8. **iv-npvnv subtasks (2):** These come from a brainstorm and represent proposed work. Create if the kernel validation sprint proceeds.

## Methodology

1. Extracted all `iv-[a-z0-9]{3,}` patterns (with optional `.N` suffix) from docs using grep
2. Combined results from markdown files and `roadmap.json` (46 additional IDs, all overlapping)
3. Excluded 18 template/test/example IDs
4. Verified each ID against `bd show <id>` using exit code (not string matching, to avoid false negatives)
5. For false-positive "missing" results in first pass, re-verified with exit code check (corrected 14 false negatives)
6. Mapped each missing ID to its source document(s) for context
