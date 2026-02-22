# Demarch Conventions

Canonical documentation paths are strict. Do not introduce compatibility aliases or fallback filenames.

## Module Repos (apps/, os/, core/, interverse/, sdk/)

- Roadmap: `docs/<repo>-roadmap.md`
- Vision: `docs/<repo>-vision.md`
- PRD: `docs/PRD.md`
- Optional machine roadmap feed: `docs/roadmap.json`

Examples:
- `interverse/interlock/docs/interlock-roadmap.md`
- `core/intermute/docs/intermute-vision.md`
- `os/clavain/docs/PRD.md`

## Interverse Root (monorepo root docs/)

- Human roadmap: `docs/interverse-roadmap.md`
- Machine roadmap feed (canonical for tooling): `docs/roadmap.json`
- Vision: `docs/interverse-vision.md`
- Root-level PRDs: `docs/prds/*.md` (no single root `docs/PRD.md`)

## Enforcement Rules

- Do not use `docs/roadmap.md` or `docs/vision.md` as active artifact paths.
- New docs, commands, scripts, and prompts must reference canonical paths only.
- Existing non-canonical files must be migrated to canonical filenames.
