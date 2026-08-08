# Round 4 / Probe 2 — Verdict: upstreams.json semantics (f-028 × f-083 × f-090)

**Status: RESOLVED.** This is the run's last live disagreement.

## What upstreams.json's contract is today

It is three things fused into one file, and the disagreement exists because the
three have decayed at different rates:

1. **Distribution manifest** (the `fileMap`): upstream source path → local
   destination. Written by humans, read by both sync engines, `pull-upstreams.sh`,
   `upstream-check.sh`, `upstream-impact-report.py`, and the `sync.yml` clone step.
2. **Mutable sync state** (`lastSyncedCommit`): written atomically by the engines
   (`clavain_sync/state.py`, jq in the bash engine) after each successful sync.
3. **Sync policy** (`syncConfig`): protectedFiles, namespaceReplacements,
   contentBlocklist — all live and enforced — plus `deletedLocally`, which is
   enforced by readers but **written by no one**.

It is not a mirror catalog (nothing asserts the local tree matches it) and it is
not pure residue (26/65 entries still drive real syncs). It is a distribution
manifest whose negative half — the part that records what should *stop* being
distributed — was never implemented.

## Residual truth of f-028 (precise)

- **Survives:** catalog staleness. Re-verified on disk this round: **39 of 65
  fileMap targets do not exist locally.** Worse than plain deletion, several
  targets were *relocated* — `systematic-debugging`, `test-driven-development`,
  `verification-before-completion` now live under `interverse/intertest/skills/`,
  the oracle references under the standalone interpeer repo — while
  `os/Clavain/upstreams.json` still declares Clavain paths as their sync targets.
- **Refuted (stays refuted):** the resurrection mechanism. Both engines guard with
  `SKIP:not-present-locally` (`sync-upstreams.sh:315`, `clavain_sync/classify.py:61`);
  running the sync does not re-materialize deleted files.
- **Newly stated this round:** the guard is *presence-based, not intent-based*.
  It protects against resurrection only as an incidental side effect of the file
  being absent. If any stale path is recreated for an unrelated reason, the
  mapping re-engages and the weekly automation AUTO-overwrites the file with
  upstream content. The designed intent channel (`deletedLocally`) exists in both
  readers but has no writer — the catalog is append-only by construction.

## The real defects, ranked by blast radius

1. **P1 — The deprecated engine is the live automation.** `sync.yml` (weekly
   cron) calls `scripts/sync-upstreams.sh --auto --no-ai` directly, bypassing
   `pull-upstreams.sh --sync`, which defaults to the Python successor. Every
   weekly sync PR is produced by self-declared-deprecated code; the tested
   successor (`clavain_sync`, atomic state writes, structural test suite) sits
   unused by CI. Any divergence between the two engines' classification semantics
   lands in automated PRs undetected. (f-090)
2. **P1 — Deletion-amnesia: the catalog cannot shrink.** Upstream deletions fall
   out of the diff window as `lastSyncedCommit` advances; local deletions and
   relocations are never recorded (`deletedLocally: []` forever); no code removes
   a fileMap entry. 39 fossil entries accumulate noise, false provenance, and the
   latent-overwrite risk above. (f-028 residual, f-083)
3. **P2 — SKIP-category desensitization.** ~39 fossil SKIP lines per run train
   reviewers to ignore the category that also carries protected/deleted signals.

## Ruling: option (i) — prune upstreams.json and give it a shrink mechanism

Option (ii) is a non-entity: the successor engine deliberately reuses
`upstreams.json` (PRD 2026-02-12: "Keep upstreams.json schema unchanged"); there
is no successor manifest to replace it with. Option (iii) would kill
`upstream-check.sh`, the impact report, and the `sync.yml` clone step for no
gain — 26/65 entries still do real work. The file's contract is sound; its
negative half is unimplemented.

### Migration in 3 steps

1. **Prune and repoint (one PR).** For each of the 39 dead entries: if the target
   was relocated (superpowers skills → `interverse/intertest`, oracle refs →
   interpeer repo), delete the entry from `os/Clavain/upstreams.json` and record
   the mapping in the *new owning repo's* sync config; if the target was truly
   removed, move the path into `syncConfig.deletedLocally` so the guard becomes
   intent-based rather than incidental.
2. **Add the shrink mechanism to `clavain_sync`.** Two rules, both proposing
   changes inside the existing weekly sync PR (never silent): (a) an entry
   classified `SKIP:not-present-locally` for N=3 consecutive runs is moved to
   `deletedLocally` with a report line; (b) an upstream source path present at
   `lastSyncedCommit` but gone at the new HEAD produces a *local deletion
   proposal* in the PR, closing the deletion-propagation hole. Add structural
   tests mirroring the existing `test_state.py`/`test_config.py` suite.
3. **Switch CI to the successor and retire the bash engine.** Change `sync.yml`'s
   run step to `python3 -m clavain_sync sync --auto --no-ai` (or
   `pull-upstreams.sh --sync`), let one clean weekly cycle validate parity, then
   delete `scripts/sync-upstreams.sh` rather than leaving a deprecated second
   engine on disk.

REMEDIATION: Prune the 39 dead fileMap entries from os/Clavain/upstreams.json (repoint relocated skills to their interverse owners' sync configs, demote true deletions into deletedLocally), teach clavain_sync a shrink rule (chronically-skipped entries → deletedLocally; upstream deletions → local deletion proposals in the sync PR), and switch .github/workflows/sync.yml from the deprecated sync-upstreams.sh to `python3 -m clavain_sync`, deleting the bash engine after one clean cycle.

## Appendix — the 39 dead fileMap targets (disk-verified 2026-08-06)

- oracle (12): all `skills/interpeer/references/oracle-docs/*` + `oracle-reference.md` targets — relocated to the standalone interpeer repo
- superpowers (11): `skills/systematic-debugging/*` (4), `skills/test-driven-development/*` (2), `skills/verification-before-completion/SKILL.md`, `skills/writing-skills/*` (4) — mostly relocated to `interverse/intertest/skills/`
- superpowers-dev (6): `skills/developing-claude-code-plugins/*` (5), `skills/working-with-claude-code/*` (1 + glob)
- compound-engineering (9): `skills/create-agent-skills/*` (1 + 3 globs), `agents/research/*` (5)
- globs with zero matches counted as dead: 4 (superpowers-dev references, create-agent-skills references/templates/workflows)
