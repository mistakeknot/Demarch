# Plugin Publishing Pipeline: Structural Validation
**Bead:** iv-pxid
**Phase:** brainstorm (as of 2026-02-23T04:20:23Z)
**Date:** 2026-02-22

## What We're Building

A structural validator (`validate-plugin.sh`) that catches undeclared plugin features before publishing, plus mass fixes for the 21+ affected plugins and integration into the existing `interbump.sh` pipeline.

## Why This Approach

An ecosystem audit found that 14 plugins have hooks on disk that Claude Code never loads (missing `hooks` key in plugin.json), and 7 plugins declare zero features despite having skills/commands on disk. The root cause is that `interbump.sh` only validates version numbers — it never checks whether on-disk features are properly declared.

The intersynth v0.1.3 bug (hooks shipped but never loaded) is the canonical example: hooks were re-added to disk in a commit but the plugin.json `hooks` key was not restored. Nothing in the pipeline caught this.

## Key Decisions

1. **Error on undeclared features** — If hooks/skills/commands exist on disk but aren't in plugin.json, validation fails. No warn-only mode. This prevents the 14-plugin bug class from recurring.

2. **Integrate into interbump.sh** — Run validation as a pre-publish gate. Add `--skip-validation` flag for emergencies only.

3. **Script, not agent** — `validate-plugin.sh` is a standalone bash script in `scripts/`, not a plugin agent. It must be fast (< 1s) and work without Claude Code running.

4. **Leverage existing infrastructure** — `intercheck-versions.sh` already handles version sync. The new script handles structural checks only (no version duplication). `interpub:release` Phase 2 already has an optional `plugin-validator` slot.

## Scope

### In Scope
- `validate-plugin.sh`: detect undeclared hooks, skills, commands, agents; detect hardcoded secrets in env blocks; validate hooks.json structure
- Wire into `interbump.sh` as pre-publish gate
- Fix all 14 plugins with undeclared hooks
- Fix all 7 zero-feature plugins (add missing declarations)
- Fix 3 version mismatches (interflux, interlock, interkasten)
- Fix 1 hardcoded API key (interject)
- Cache cleanup script for stale version directories

### Out of Scope
- CI/CD integration (future)
- Automated plugin.json generation from disk contents
- Plugin dependency resolution

## Affected Plugins

**Undeclared hooks (14):** intercheck, interfluence, interflux, interject, interkasten, interlearn, interline, interlock, intermem, intermux, interserve, interstat, tool-time

**Undeclared skills/commands (7):** interline, interpath, interphase, interwatch, tool-time, tuivision, interlock

**Version drift (3):** interflux (0.2.20 vs marketplace 0.2.19), interlock (0.2.2 vs 0.2.1), interkasten (0.4.3 vs marketplace 0.4.4)

**Security (1):** interject hardcoded EXA_API_KEY

## Open Questions

None — requirements are clear from the audit.

## References

- Full audit: `interverse/intersynth/docs/research/audit-plugin-version-mismatches.md`
- Existing scripts: `scripts/interbump.sh`, `scripts/intercheck-versions.sh`
- Plugin schema docs: `docs/research/validate-plugin-json-schemas.md`
- Critical patterns: `docs/solutions/patterns/critical-patterns.md`
