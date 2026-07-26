# Plugins extracted out of `interverse/`

`.gitignore:9` ignores `interverse/`, because every plugin under it now lives in
its own repository. The monorepo is not the owner of any of them.

Historically the monorepo also *tracked* 198 files beneath that ignored path —
committed before the ignore rule landed, and therefore drifting silently against
the repos that own them. This document records what was measured before those
files were untracked, and the trap that survives the cleanup.

## Measured drift, 2026-07-25

Blob SHAs compared directly between the monorepo's `HEAD`, each nested repo's
`HEAD`, and (for the two with no local `.git`) the GitHub tree API.

| Subtree | Monorepo tracked | Local form | Upstream | Verdict |
|---|---|---|---|---|
| `interfer` | 128 | nested repo `fd5529f` | [interfer](https://github.com/mistakeknot/interfer) | 128/128 identical to nested `HEAD`; nested tracks 207, so the monorepo held a subset |
| `interhelm` | 29 | **plain dir, no `.git`** | [interhelm](https://github.com/mistakeknot/interhelm) | 27/29 identical; **behind on 2** — `plugin.json` v0.2.2 vs v0.2.3, `.gitignore` missing `.publish-approved`; upstream also has `tests/structural/helpers.py`, `tests/uv.lock` |
| `intersight` | 24 | nested repo `c5afaab` | [intersight](https://github.com/mistakeknot/intersight) | 24/24 identical to nested `HEAD` |
| `interseed` | 16 | **plain dir, no `.git`** | [interseed](https://github.com/mistakeknot/interseed) (private) | 15/15 identical; **behind on 4** — `.clavain/setup-verified`, `.gitignore`, `docs/brainstorms/2026-03-29-…-brainstorm.md`, `uv.lock`; `POINTER.md` is monorepo-only by design |
| `intership` | 1 | nested repo `9564ea9` | [intership](https://github.com/mistakeknot/intership) | 1/1 identical to nested `HEAD` |

The direction is consistent: the monorepo copy was **identical or behind in every
case**, never ahead. Across all 198 files the only monorepo-only content was
`interverse/interseed/POINTER.md` — the tombstone recording that interseed had
been extracted. This document replaces it, which is why it covers all five rather
than one.

## Status

The agreed disposition is to untrack all 198 from the monorepo index — no
"keep and stop ignoring" case exists, because every subtree has an owner
elsewhere. `git rm --cached` removes from the index only: files stay on disk,
stay reachable in this repo's history, and remain live in the five repositories
above.

Applied in `61e3e335`: `git ls-files interverse` went **198 → 0**, with the
on-disk file count unchanged and all three nested repos' status untouched
(`interfer` kept its 4 pre-existing dirty entries, which the monorepo never
tracked; `intersight` and `intership` stayed clean).

## Surviving trap: two of these have no local git presence

`interverse/interhelm/` and `interverse/interseed/` are **plain directories with
no `.git`**. They are not clones and not worktrees — just copies, now unversioned
locally and already behind their upstreams (interhelm was pushed 2026-07-23, two
days before this was measured).

Editing either directory therefore edits a stale, unversioned copy of a repo that
has moved on, with nothing to warn you: the monorepo ignores the path, and there
is no nested repo to report the change. Before working on either, clone the real
repository. Whether to replace or remove the orphan copies is a separate
decision, deliberately not taken here — the same call `POINTER.md` deferred.

The other three (`interfer`, `intersight`, `intership`) are real nested repos and
report their own status normally.

## See also

- `docs/reflections/2026-07-25-monorepo-tree-cleanup-reflect.md` — where the 198
  were first found
- `docs/solutions/2026-07-25-unattended-work-needs-a-stopped-signal.md`
  § "Adjacent: ignore-noise buries real work"
