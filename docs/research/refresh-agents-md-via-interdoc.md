# AGENTS.md Refresh — interdoc:interdoc Run Report

**Date:** 2026-02-27
**Trigger:** 9 new files added since last AGENTS.md update (4 research reports, 4 recovery scripts, 1 label backfill script)
**Result:** AGENTS.md updated and committed (commit `05ecc2c`)

---

## What Changed

### New commits since last AGENTS.md update

Two significant commits landed:

| Commit | Title |
|--------|-------|
| `6176ece` | fix(beads): verify and close 44 recovered beads with commit evidence |
| `384579f` | feat(beads): add module and theme label taxonomy with 4,336-label backfill |

### New files (9 total)

**Research reports (4):**
- `docs/research/check-beads-with-wrong-status.md` — audit of beads with incorrect status flags
- `docs/research/verify-commits-reference-valid-beads.md` — cross-check commit messages vs bead database
- `docs/research/verify-docs-reference-valid-beads.md` — cross-check doc references vs bead database
- `docs/research/verify-recovered-beads-quality.md` — quality audit of 139 recovered beads

**Recovery scripts (4):**
- `scripts/replay-missing-beads-from-commit-manifest.py` — recreate beads from a CSV of git commit metadata
- `scripts/replay-missing-roadmap-beads.py` — create placeholders for IDs referenced in roadmap docs
- `scripts/map_brainstorms_plans_to_beads.py` — map brainstorm/plan docs to beads via `**Bead:** ...` declarations
- `scripts/backfill-bead-labels.py` — apply module and theme label taxonomy to existing beads

**Label backfill script is also a recovery script; counted in the 4 above.**
(Total: 4 research + 4 scripts = 8 new files, plus the `.beads/issues.jsonl` mutations = 9 touched files)

---

## AGENTS.md Sections Updated

### Added: "Label Taxonomy" subsection under "Bead Tracking"

Documents the two-dimensional label system introduced by `backfill-bead-labels.py`:

- **36 module labels** (`mod:<name>`) — one per pillar/subproject
- **12 theme labels** (`theme:<name>`) — type of work (tech-debt, performance, security, ux, observability, dx, infra, docs, testing, architecture, coordination, research)

Labels are inferred heuristically from `[module]` bracket prefixes in titles and keyword patterns in title+description. The script is idempotent and additive.

### Added: "Bead Recovery Scripts" subsection under "Bead Tracking"

Documents all four recovery scripts in a reference table with a brief purpose description for each. Recovered beads are tagged `recovered, placeholder` for traceability. Links to `docs/research/verify-recovered-beads-quality.md` for the audit report.

---

## Sections Not Changed

All existing sections were reviewed and found accurate:

- **Agent Quickstart / Instruction Loading Order** — no changes needed
- **Glossary** — no new terms required
- **Directory Layout** — no new modules added
- **Key Dependency Chains** — no new plugin dependencies
- **Roadmap** — subsection unchanged (roadmap tooling unchanged)
- **Go Module Path Convention** — unchanged
- **Prerequisites** — unchanged (no new tools required)
- **Development Workflow** — unchanged
- **Publishing / Plugin Dev Gate** — unchanged
- **Version Bumping (interbump)** — unchanged
- **Operational Guides table** — unchanged (beads-0.51-upgrade-plan.md still current; it was already updated to reflect bd 0.56.1 in a prior commit)
- **Critical Patterns** — unchanged
- **Compatibility / Landing the Plane / Operational Notes** — unchanged

---

## Key Findings

1. **Label taxonomy is a new permanent capability** — 36 mod: + 12 theme: labels, covering 76% of 2,300 beads (1,746 labeled). The backfill script is idempotent and can be re-run after adding new beads.

2. **Four recovery scripts are now available** — previously there was no documented process for reconstructing beads after data loss. These scripts cover three recovery vectors: git commit manifests, roadmap documents, and brainstorm/plan markdown files.

3. **The 2026-02-27 recovery successfully closed 44 beads** — 42 confirmed complete by commit evidence + 2 missing beads created and immediately closed. 39 plan-defined IDs remain unmaterialized (future work, not lost data).

---

## Commit Details

```
commit 05ecc2c
docs: refresh AGENTS.md after beads recovery and label taxonomy

Adds two new subsections to the Bead Tracking section:
- Label Taxonomy: two-dimensional mod:/theme: label system with all
  36 module labels and 12 theme labels; references backfill-bead-labels.py
- Bead Recovery Scripts: table of 4 recovery scripts (replay from
  commit manifest, replay from roadmap, map brainstorms/plans, backfill
  labels) with a link to the 2026-02-27 audit report.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

1 file changed, 40 insertions(+), 1 deletion(-)
