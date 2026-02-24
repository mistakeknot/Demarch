# Demarch Conventions

Canonical documentation paths are strict. Do not introduce compatibility aliases or fallback filenames.

## Module Repos (apps/, os/, core/, interverse/, sdk/)

- Roadmap: `docs/roadmap.md` (auto-generated from beads via `scripts/generate-module-roadmaps.sh`)
- Vision: `docs/<repo>-vision.md`
- PRD: `docs/PRD.md`
- Optional machine roadmap feed: `docs/roadmap.json`

Examples:
- `interverse/interlock/docs/roadmap.md` (auto-generated)
- `core/intermute/docs/intermute-vision.md`
- `os/clavain/docs/PRD.md`

## Demarch Root (monorepo root docs/)

- Human roadmap: `docs/demarch-roadmap.md`
- Machine roadmap feed (canonical for tooling): `docs/roadmap.json`
- Vision: `docs/demarch-vision.md`
- Root-level PRDs: `docs/prds/*.md` (no single root `docs/PRD.md`)

## Enforcement Rules

- Module roadmaps are auto-generated — do not hand-edit `docs/roadmap.md` in modules.
- Do not use `docs/vision.md` as an active artifact path.
- New docs, commands, scripts, and prompts must reference canonical paths only.
- Existing non-canonical files must be migrated to canonical filenames.
