---
artifact_type: goal-charter
bead: Sylveste-ktz
complexity: C3
---

# Goal Charter — Small-Fix + Hygiene Bundle (Goal B of parallel pair)

## Why (leverage)

The standing successor of goals 4aecb49d and 7b585d72, expanded with the
grooming sweep's hygiene tail. Every item is self-contained,
execution-grade, and low-collision — bundled per mk's bundling preference,
run in PARALLEL with Goal A (hook plumbing, separate session) under the
partition mk confirmed 2026-07-22. Written for a weaker executor: exact
sites, complete steps, machine-checkable acceptance.

## Parallel-session coordination (binding)

- Both sessions run on the Mac (one shared Dolt; never split bead writes
  across machines mid-flight).
- This session owns: interlock hooks/pre-edit.sh, interflux
  scripts/discover-models.sh, interkasten scripts/start-mcp.sh, intercore
  publish code, and the named bead operations. Reserve via interlock.
- **This session does NOT run ic publish for plugins.** Goal A ships the
  publish wave covering these commits. Close beads on commit + green
  tests, noting publish deferred to Goal A.

## Scope (exact sites)

**In:**
1. **Sylveste-a3a — BSD date fallbacks** at the three remaining `date -d`
   sites: `interverse/interlock/hooks/pre-edit.sh:222`,
   `interverse/interflux/scripts/discover-models.sh:45`,
   `interverse/interkasten/scripts/start-mcp.sh:58`. Use the proven
   helper pattern from `interverse/interphase/hooks/lib-discovery.sh`
   `_discovery_iso_to_epoch()`: GNU `date -d` first, then normalize
   (`${ts%%.*}`, strip `+00:00`/`Z`) + `date -j -u -f
   "%Y-%m-%dT%H:%M:%S"` fallback. `bash -n` each file; run each script's
   test if one exists.
2. **Sylveste-1zu — ic publish --cwd hard-error**: in core/intercore,
   a `--cwd` pointing at a nonexistent path must exit non-zero with a
   clear error instead of silently falling back to process cwd. Add a Go
   test covering the nonexistent-relative-path case (the interpulse
   triple-publish scenario). `go test ./...` green.
3. **Hygiene tail**: close epics `sylveste-09h` and `sylveste-uais`
   (100% children complete per sweep memo; user pre-authorized via this
   charter); `bd update sylveste-18a --title` to a descriptive title
   (currently literally "epic"); `git -C os/Skaffen pull --ff-only`
   (checkout stale behind origin/main).

**Out:**
- Goal A's lane: hook definitions, sideband code, plugin publishes.
- Anything not listed above.

## Completion condition (literal, for /goal)

The small-fix and hygiene bundle is complete when ALL of the following are
surfaced in-session: (1) BSD date fallbacks landed at
interverse/interlock/hooks/pre-edit.sh, interverse/interflux/scripts/
discover-models.sh and interverse/interkasten/scripts/start-mcp.sh using
the lib-discovery helper pattern, with diffs surfaced, bash -n clean for
all three files, and Sylveste-a3a closed citing the commits; (2) ic publish
with a nonexistent --cwd path exiting non-zero with a clear error, a Go
test covering the case, go test output surfaced green, and Sylveste-1zu
closed citing the commit; (3) epics sylveste-09h and sylveste-uais closed
citing the sweep memo, sylveste-18a retitled via bd update with the new
title surfaced, and a git pull --ff-only of os/Skaffen surfaced bringing
it current with origin/main; (4) an explicit statement surfaced that no
ic publish was run for plugins in this session, publishes deferred to the
hook-plumbing goal; (5) all commits pushed and bd export to
.beads/issues.jsonl committed and pushed with beads_jsonl_dolt_sync ok
surfaced. Or stop after 40 turns and surface an accounting of completed
versus outstanding items.

## Successor obligations

At close, propose a successor per Goal Cadence — likely nothing standalone:
this bundle clears the known small-debt tail; fold any residue into Goal
A's close or the next digest cycle.
