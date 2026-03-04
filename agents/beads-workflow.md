# Beads Workflow

## Bead Tracking

All work is tracked at the **Demarch root level** using the monorepo `.beads/` database. Module-level `.beads/` databases are read-only archives of historical closed beads.

- Create beads from the Demarch root: `cd /root/projects/Demarch && bd create --title="[module] Description" ...`
- Use `[module]` prefix in bead titles to identify the relevant module (e.g., `[interlock]`, `[interflux]`, `[clavain]`)
- Filter by module: `bd list --status=open | grep -i interlock`
- Cross-module beads use multiple prefixes: `[interlock/intermute]`

## Label Taxonomy

Beads use a two-dimensional label system. Backfill/apply with `scripts/backfill-bead-labels.py`.

**Module labels** (`mod:<name>`) — which pillar/subproject the bead belongs to:
```bash
# Generate current list:
(echo "mod:clavain mod:demarch mod:autarch mod:intercom mod:interspect mod:tldrs"; \
 ls -d interverse/inter* core/inter* sdk/inter* 2>/dev/null | xargs -I{} basename {} | sed 's/^/mod:/') \
 | tr ' ' '\n' | sort | paste -d'  ' - - - - -
```

**Theme labels** (`theme:<name>`) — what kind of work:
```
theme:tech-debt  theme:performance  theme:security  theme:ux
theme:observability  theme:dx  theme:infra  theme:docs
theme:testing  theme:architecture  theme:coordination  theme:research
```

Labels are inferred from `[module]` bracket prefixes in titles and keyword patterns in title+description. The backfill script is idempotent and additive — it never removes existing labels.

## Bead Recovery Scripts

After data loss events, use these scripts to reconstruct missing beads:

| Script | Purpose |
|--------|---------|
| `scripts/replay-missing-beads-from-commit-manifest.py` | Recreate beads from a CSV of git commits where bead IDs appeared in commit messages but were missing from the database |
| `scripts/replay-missing-roadmap-beads.py` | Create placeholder beads for IDs referenced in `docs/roadmap.json` and `*roadmap*.md` files but absent from the database |
| `scripts/map_brainstorms_plans_to_beads.py` | Map `docs/brainstorms/` and `docs/plans/` markdown files to bead IDs via `**Bead:** ...` declarations; creates placeholder beads for unmatched docs |
| `scripts/backfill-bead-labels.py` | Apply module and theme label taxonomy to existing beads using heuristic detection (idempotent) |

Recovered beads are tagged `recovered, placeholder` so they are distinguishable from original data. See `docs/research/verify-recovered-beads-quality.md` for the audit report from the 2026-02-27 recovery.

## Roadmap

The platform roadmap is at [`docs/demarch-roadmap.md`](../docs/demarch-roadmap.md) with machine-readable canonical output in [`docs/roadmap.json`](../docs/roadmap.json). Regenerate both with `/interpath:roadmap` from the Demarch root. Auto-generate module-level roadmaps from beads with `scripts/generate-module-roadmaps.sh` or `/interpath:propagate`.

`scripts/sync-roadmap-json.sh` generates the canonical JSON rollup from the root roadmap and beads data. `scripts/generate-module-roadmaps.sh` auto-generates per-module `docs/roadmap.md` files from beads state.
