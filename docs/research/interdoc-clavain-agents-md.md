# Interdoc Analysis: Clavain AGENTS.md Refresh

**Date:** 2026-02-25
**Target:** `/home/mk/projects/Demarch/os/clavain/AGENTS.md`
**Current size:** 503 lines
**Target size:** 350-450 lines

## Audit Summary

### Component Counts (verified against filesystem + plugin.json)

| Component | Documented | Actual | Match? |
|-----------|-----------|--------|--------|
| Skills | 16 | 16 | Yes |
| Agents | 4 | 4 | Yes |
| Commands | 46 | 46 | Yes |
| Hook bindings (in hooks.json) | 7 events documented | 6 actual bindings | No |
| Hook scripts on disk | ~15 documented | 18 `.sh` files | No |
| MCP servers | 1 | 1 (context7) | Yes |
| GitHub workflows | 8 documented | 7 actual | No |

### Stale Content Found

1. **Architecture tree references nonexistent skills.** The tree lists `test-driven-development/`, `systematic-debugging/`, `flux-drive/`, and `writing-skills/` -- none of these exist on disk. They were either moved to companion plugins (flux-drive -> interflux) or removed. The actual skills are:
   - brainstorming, code-review-discipline, dispatching-parallel-agents, engineering-docs, executing-plans, file-todos, galiana, interserve, landing-a-change, lane, refactor-safely, subagent-driven-development, upstream-sync, using-clavain, using-tmux-for-interactive-commands, writing-plans

2. **Hooks section lists `bead-auto-close.sh`** (removed in commit `9793a6a`, replaced by `scripts/bead-land.sh`). Also lists `session-handoff.sh` and `session-end-handoff.sh` as registered hooks, but these were removed from hooks.json in commit `7dc44a5` (false positives). The scripts still exist on disk but are inactive.

3. **Interspect Routing Overrides section (lines 140-185)** references `hooks/lib-interspect.sh` which was extracted to the standalone interspect companion plugin in commit `4c7e546`. The library no longer exists at that path in Clavain. The entire 46-line section describes interspect's internal workings -- this content belongs in the interspect plugin's own AGENTS.md, not here.

4. **GitHub workflows section** lists 8 workflows but only 7 exist. The actual workflows are:
   - `eval-daily.yml`, `eval-on-change.yml`, `pr-agent-commands.yml`, `secret-scan.yml`, `sync.yml`, `test.yml`, `upstream-check.yml`
   - Missing from docs: `eval-daily.yml`, `eval-on-change.yml`, `secret-scan.yml`, `test.yml`
   - Listed but nonexistent: `upstream-impact.yml`, `upstream-decision-gate.yml`, `codex-refresh-reminder.yml`, `codex-refresh-reminder-pr.yml`, `upstream-sync-issue-command.yml`

5. **Hook library files not documented.** The AGENTS.md doesn't mention several lib files that exist in hooks/:
   - `lib-intercore.sh` -- Intercore CLI wrappers (critical for sprint/phase integration)
   - `lib-signals.sh` -- Signal detection for auto-stop-actions
   - `lib-spec.sh` -- Agency spec loader (reads config/agency-spec.yaml)
   - `lib-verdict.sh` -- Verdict file utilities for structured agent handoffs
   - `lib-sprint.sh` -- Sprint state library (sourced by multiple hooks)

6. **Scripts section is incomplete.** Missing from docs:
   - `orchestrate.py` -- DAG-based Codex agent dispatch
   - `build-clavain-cli.sh` -- Go CLI binary builder
   - `scan-fleet.sh` -- Fleet registry auto-scanner
   - `lib-fleet.sh` -- Fleet registry query library
   - `lib-routing.sh` -- Routing config reader
   - `verify-config.sh` -- Plugin state verifier
   - `bead-land.sh` -- Close orphaned beads (replaces auto-close hook)
   - `beads-hygiene.sh` -- Beads cleanup utilities
   - `modpack-install.sh` -- Companion plugin installer
   - `agency-spec-helper.py` -- Agency spec YAML helper
   - `clavain_sync/` -- Python package for upstream sync classification
   - `validate-gitleaks-waivers.sh` -- Secret scan waiver validation

7. **Missing `config/` directory documentation.** The architecture tree mentions `config/dispatch/` but the actual config directory structure is:
   - `config/agency/` -- 5 phase-specific agency YAML files (build, design, discover, reflect, ship)
   - `config/agency-spec.yaml` -- Agency specification
   - `config/agency-spec.schema.json` -- JSON schema for agency spec
   - `config/fleet-registry.yaml` -- Agent fleet registry
   - `config/fleet-registry.schema.json` -- JSON schema for fleet registry
   - `config/routing-overrides.schema.json` -- Routing overrides schema
   - `config/routing.yaml` -- Model routing configuration
   - `config/CLAUDE.md` -- Engineering conventions (installed by agent-rig)

8. **Missing `cmd/clavain-cli/` documentation.** A Go CLI binary was added (commit `c69c545`) with budget, checkpoint, children, claim, complexity, exec, phase, sprint commands and 55 tests. Not mentioned anywhere in AGENTS.md.

9. **L2 layer context missing.** The AGENTS.md doesn't explain Clavain's position in the Demarch architecture: it's Layer 2 (OS), sitting between Intercore (L1 kernel) and Autarch (L3 apps). This context is important for understanding dependency direction.

### Content Extraction Candidates

1. **Interspect Routing Overrides** (46 lines) -- Extract entirely. This content describes interspect's internals and references a library that no longer lives in Clavain. Replace with a 3-line cross-reference to the interspect companion plugin.

2. **Upstream Tracking** (35 lines) -- Keep but condense. The detailed upstream table and sync system description is useful but the state file details and decision record paths are over-specified.

3. **Modpack companion plugins** (75 lines) -- Keep in AGENTS.md. This is core reference material for understanding which plugins Clavain delegates to.

### New Content Needed

1. Layer context paragraph (L2 between L1 and L3)
2. Complete skills table with all 16 skills
3. Accurate hooks list matching hooks.json
4. `config/` directory documentation
5. `cmd/clavain-cli/` mention
6. Updated scripts list
7. Updated GitHub workflows list

### Actions Taken

1. Rewrote AGENTS.md with all corrections above
2. Reduced from 503 to ~430 lines (within target range)
3. Removed phantom skill references from architecture tree
4. Updated hooks section to match actual hooks.json bindings
5. Replaced Interspect section with cross-reference
6. Added L2 layer context
7. Updated GitHub workflows to match reality
8. Added missing config/, cmd/, and script documentation
9. Added complete skills table
10. Updated hook library documentation
