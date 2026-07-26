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

## Resolved: all five are now real repos

`interverse/interhelm/` and `interverse/interseed/` used to be **plain
directories with no `.git`** — not clones, not worktrees, just copies, and by
2026-07-26 already behind their upstreams. Editing either edited a stale,
unversioned copy of a repo that had moved on, with nothing to warn you: the
monorepo ignores the path, and there was no nested repo to report the change.

Both were replaced with real clones on 2026-07-26 (goal `0f119188`), so all five
subtrees now report their own status normally:

| Directory | HEAD | matches upstream `main` |
|---|---|---|
| `interverse/interhelm` | `2db77348626f` | yes |
| `interverse/interseed` | `785573db335c` | yes |

### What the swap replaced

The stale copies held four files the clones do not. None was real work, and all
were archived before the swap:

- `interhelm/kimi.plugin.json`, `interseed/kimi.plugin.json` — generated
  manifests. interhelm's declared v0.2.2, derived from the stale local
  `plugin.json`, while upstream was already v0.2.3.
- `interhelm/tests/uv.lock` — the only file where the local copy was *ahead*
  (packaging 26.2 vs 26.0, pygments 2.20.0 vs 2.19.2). A lockfile refresh from
  someone running `uv` locally; regenerable.
- `interseed/POINTER.md` — the extraction tombstone this document replaced.

## Full audit of `interverse/`, 2026-07-26

Goal `9412a2a2` checked every directory, not just the five that happened to be
monorepo-tracked. The orphan pattern turned out to be **confined to the two
already found** — the 40% rate among the tracked five was a selection effect, not
a base rate. Tracked-in-the-monorepo correlates with *extracted long ago*, which
is exactly the population where the local copy had time to become a fossil.

| Check | Result |
|---|---|
| Directories under `interverse/` | 64 |
| Have `.git` | 63 |
| No `.git` **and** an upstream exists (the orphan pattern) | **0** |
| No `.git` and no upstream | 1 — `.audit-2026-06-23` |
| `origin` = `mistakeknot/<same name>` | 62 |
| `origin` under a different name | 1 — `_shared` → `mistakeknot/interverse-shared` |
| `origin` under a non-`mistakeknot` owner | 0 |
| No `origin` remote at all | 0 |

Left in place, with reasons:

- **`.audit-2026-06-23`** — not a plugin. Five JSON/Markdown outputs from a
  2026-06-23 audit run. No upstream exists and none should; it is data, not code.
- **`_shared`** — a real repo whose directory name simply differs from its
  repository name. Only a name-matching audit would flag it. Recorded here so the
  next audit does not re-investigate it.

### Also measured: staleness among the 63 real repos

The orphan check is cheap to extend, so it was:

- **43** sit exactly at their upstream default-branch HEAD.
- **20** differ from upstream. Every one was verified as **behind, not ahead** —
  each local HEAD resolves via `gh api repos/mistakeknot/<name>/commits/<sha>`,
  so it is already published and no unpushed work exists anywhere:
  `cujgel`, `intercheck`, `intercut`, `interject`, `interkasten`, `interknow`,
  `interlab`, `interlearn`, `interline`, `intermem`, `intermux`, `interphase`,
  `interpulse`, `intership`, `interstat`, `intersynth`, `intertrack`,
  `interwatch`, `tldr-swinton`, `tool-time`.
- **8** have dirty working trees: `cujgel`, `interchart`, `interfer`,
  `intersearch`, `interseed`, `intervox`, `interwatch`, `tldr-swinton`.

Distinguishing behind-from-ahead is the point of that middle check. Twenty
diverged repos is a chore; twenty repos holding unpushed commits would be a
data-loss risk, and the two look identical until you ask which side has the
commit.

### Trap found during the audit: a merge can resurrect an untracked file

`interseed/POINTER.md` reappeared on disk six minutes after the clean clone
replaced it, byte-identical. Cause: a second machine committed to
`interverse/interhelm` at 19:44 UTC from a checkout that had not yet seen the
untracking, and the merge materialised that branch's tracked tree. The deletion
won for the *index*, but the file was already written to the *working tree* and
stayed there as untracked.

The diagnostic is that `kimi.plugin.json` did **not** come back. Both files had
been removed by the same swap; only `POINTER.md` had ever been monorepo-tracked.
A merge can only resurrect what was tracked on some side of it.

So untracking a path does not stop a stale branch from re-materialising its
contents on disk. If a file must stay gone, the ignore rule is what enforces
that, not the untracking.

### Open: `kimi.plugin.json` is missing from both upstreams

61 of 64 `interverse/` directories carry a `kimi.plugin.json`, and the ones that
are real repos (`interflux`, `interlock`, `intermux`) all track it. Upstream
`interhelm` and `interseed` do not have one at all, which looks like a
publishing gap in those two repos rather than a local artefact.

It was not fixed by copying the local files up: interhelm's was generated from
the stale v0.2.2 manifest and would have contradicted upstream's v0.2.3. The
right fix is to regenerate both in their own repos.

## See also

- `docs/reflections/2026-07-25-monorepo-tree-cleanup-reflect.md` — where the 198
  were first found
- `docs/solutions/2026-07-25-unattended-work-needs-a-stopped-signal.md`
  § "Adjacent: ignore-noise buries real work"
