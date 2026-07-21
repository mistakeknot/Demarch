---
artifact_type: goal-charter
bead: Sylveste-0lt
complexity: 3
stage: goal-formed
---

# Goal Charter: Publish-Pipeline Hardening — Prune Safety + Loud Auto-Publish

## Why (leverage)

Publishing is daily infrastructure across ~57 plugins, and both target bugs
bit this session with fresh reproduction evidence:

- **Sylveste-0lt (P1):** during the clavain 0.6.278 publish, cache prune
  removed the ENTIRE clavain cache directory including the version it had
  just published — the plugin silently failed to load and every /clavain:*
  command went unknown. Root cause confirmed in code: `PruneStaleVersions`
  (`core/intercore/internal/publish/cache.go:156`) protects only
  `ReadInstalledVersion(pluginName)`; when that read returns empty, every
  cached version becomes a prune candidate.
- **Sylveste-dc9 (P2):** the PostToolUse auto-publish hook
  (`os/Clavain/hooks/auto-publish.sh`) is fully fail-open (`trap 'exit 0'
  ERR`, `|| true`); when the marketplace clone carries a dirty tracked
  `.clavain/interspect/interspect.db`, `GitPullRebase`
  (`internal/publish/engine.go:417`) refuses with exit 128 and the hook
  dies silently — publishes just don't happen.

Hardening this path de-risks every future release, including the
Sylveste-zlc soak gate that depends on clean release cycles.

Ceremony note: classifier said C4 — the blast-radius keyword bump again
("never delete the live version"), same heuristic that misfired on the
sideband cutover. mk ratified C3 override — second calibration data point
for the bump heuristic.

## Scope

**In:**
1. **Prune fail-closed + marketplace guard** (mk-ratified posture): in
   `PruneStaleVersions` and `PruneStaleVersionsAcrossMarketplaces`
   (`internal/publish/cache.go`), (a) skip pruning a plugin entirely when
   its installed version cannot be determined (empty read = no evidence =
   delete nothing), and (b) always protect the version the marketplace's
   `marketplace.json` currently points at, independent of installed-state.
   Regression test in `cache_test.go` reproducing the 0lt shape: empty
   installed version → zero deletions for that plugin; marketplace-pointed
   version never removed.
2. **Post-publish installPath assertion**: after `ic publish` completes,
   assert the `installed_plugins.json` installPath exists on disk; missing
   path = loud error in publish output.
3. **dc9 root-cause + loud hook** (mk-ratified shape — no auto-stash):
   untrack and gitignore the interspect telemetry DB files
   (`.clavain/interspect/interspect.db` + WAL/SHM) in the marketplace
   clone so instrumentation can never dirty it; change
   `auto-publish.sh` to surface `ic publish` failures as a visible
   message (systemMessage/additionalContext) instead of silent exit 0,
   with a regression test for the failure path.

**Out:**
- Auto-stash machinery in `ic publish` (mk declined — stashing tracked
  files during publish is riskier than the dirt it cleans).
- Broader publish-flow refactors; interspect telemetry storage redesign.
- Post-publish release canary (related existing bead sylveste-ao0q —
  orthogonal, not touched here).

## Acceptance criteria

1. Prune regression tests pass: with an empty installed-version read,
   prune removes nothing for that plugin; a version pointed at by
   `marketplace.json` is never removed. `go test ./internal/publish/`
   exits 0.
2. `ic publish` output shows the post-publish installPath assertion, and
   a missing installPath fails loudly.
3. The marketplace clone's interspect DB files are untracked and
   gitignored; a publish with local instrument dirt no longer blocks on
   `pull --rebase`.
4. `auto-publish.sh` emits a visible failure message when `ic publish`
   fails (regression-tested), instead of exiting 0 silently.
5. Work committed; Sylveste-0lt and Sylveste-dc9 closed with evidence.

## Completion condition (literal — handed to /goal)

Publish-pipeline hardening complete: PruneStaleVersions and
PruneStaleVersionsAcrossMarketplaces skip plugins whose installed version
is unreadable and never delete the version marketplace.json points at,
with regression tests reproducing the Sylveste-0lt failure shape; ic
publish asserts post-publish that the installed_plugins.json installPath
exists; the marketplace clone's interspect DB files are untracked and
gitignored; hooks/auto-publish.sh surfaces ic publish failures as a
visible message instead of silent exit 0, with a regression test; go test
./internal/publish/ passes with exit 0 shown in surfaced output; work
committed to core/intercore and os/Clavain (and the marketplace clone),
and beads Sylveste-0lt and Sylveste-dc9 closed with evidence. Or stop
after 30 turns.

## Successor obligations

None fixed at formation. Candidate at close: sylveste-ao0q (post-publish
plugin canary) is the natural next hardening layer — evaluate it against
the goal-close successor audit.
