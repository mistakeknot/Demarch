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

## Staleness cleared, 2026-07-27

Goal `d4b1f7c2` acted on the 43 / 20 / 8 split above. Result: **63 at upstream
HEAD, 0 behind, 3 dirty.**

The `at-HEAD` and `behind` numbers held. The dirty count did not, and the
reason matters more than the number.

Within this one session: a weekly cron produced a fifth `interfer` benchmark
log; a sibling session committed and pushed in `interflux`, which briefly read
as *diverged* while it was in fact **ahead by one unpushed commit** — a
direction a name-and-SHA comparison cannot distinguish; a hook installer
dirtied three repos plus the monorepo, cleared, and dirtied them again; and
**`interchart`'s broken generator re-ran and reproduced the 6-node artefact
within minutes of it being discarded.**

That last one is the finding, not the churn. The 6-node output is
**deterministic, not a one-off** — so `interchart` cannot be held clean, and
the committed 244-node diagram is permanently one careless `git add` away from
being replaced by a stub. Raised to P1 as `Sylveste-afg`.

Final live reading: **63 at HEAD, 0 behind, 4 dirty** — `intersearch`
(`uv.lock`, left for its owner), `intervox` and `interflux` (hook installer),
and `interchart` (the reproducing generator). Two of those four are machinery
re-dirtying the tree on a schedule, which no amount of cleaning fixes.

Treat any estate-wide count as true only at the instant it was taken. A repo
whose *tooling* writes into tracked paths has no clean steady state to
converge to; that is a defect in the tooling, not a backlog of chores.

`git pull --ff-only` in all 20 behind repos: **19 fast-forwarded**, each verified
against `gh api repos/mistakeknot/<name>/commits/main`. The refusal to use a
plain `pull` is what made this safe — `--ff-only` aborts rather than merging, so
a repo secretly holding unpushed commits would have stopped instead of growing a
merge, and one that would have had local edits clobbered stopped too.

That is exactly what happened to the twentieth. `tldr-swinton` aborted with
"Your local changes to kimi.plugin.json would be overwritten by merge". Upstream
had 0.8.4 with extra `skills`/`commands` keys; the local uncommitted copy was a
stale 0.8.1 regeneration. Discarding the local file (archived first) let the pull
land, after which canonical and generated manifest agreed.

### The 8 dirty trees, resolved

Only 7 were still dirty — `interseed` came clean when the merge-resurrected
`POINTER.md` was archived. 29 entries, four different correct dispositions:

| Repo | Entry | Disposition |
|---|---|---|
| `cujgel`, `interchart` | `kimi.plugin.json` | Regenerated → **unchanged**; the worktree copies were already correct. Committed. |
| `interwatch` | `kimi.plugin.json` | Stale at 0.6.0 against canonical 0.6.1. Regenerated and committed. |
| `tldr-swinton` | `kimi.plugin.json` | Stale; discarded so the pull could land. |
| `interchart` | `docs/diagrams/ecosystem.html` | **Discarded** — a broken run (below). |
| `interfer` | 4 benchmark entries | Committed as result data; `.gitignore` covers `benchmarks/logs/` but not this directory. |
| `intervox` | 19 × `.beads/embeddeddolt/…` | Untracked + ignored (below). |
| `intersearch` | `uv.lock` | **Left in place** — see below. |

### Trap: "generated" does not imply "safe to commit"

`interchart/docs/diagrams/ecosystem.html` looked like an ordinary regenerated
artefact — same generator, newer timestamp. It described **6 nodes**. The
committed version described **244 nodes and 320 edges**. The Jul 25 run had
scanned almost nothing, and committing it would have replaced a good diagram
with a stub while looking like routine housekeeping.

A generated file is only safe to commit if the run that produced it succeeded.
Nothing in `git status` distinguishes a fresh regeneration from a failed one —
both are ` M`. The check that caught this was reading the artefact's own
self-reported scale, not its diff.

The likely cause is the nested-repo materialisation hazard documented in
`scripts/check-worktree-nested-repos.sh` (Jul 22): a root worktree materialises
almost none of the ~115 nested repos, so a scan run there sees an almost empty
estate and reports success. Tracked as `Sylveste-afg`.

### Root cause: `bd` ignores `dolt/`, the runtime creates `embeddeddolt/`

`intervox` was the only repo in the estate tracking its embedded Dolt database —
82 files, **66% of its 125 tracked files**, of live binary database state.

This was not carelessness in one repo. `bd` ships a `.beads/.gitignore` whose
first rule is `dolt/`, but the directory its runtime creates is
`embeddeddolt/`, which that rule never matches. Protection therefore depends on
a repo carrying an extra repo-level line. `intervoice` has one; `intervox`, its
successor, does not. Estate exposure is narrow — two repos have an
`embeddeddolt/` directory on disk and only one tracked it.

Fixed by `git rm --cached -r .beads/embeddeddolt` plus the missing
`.gitignore` line. On-disk file count stayed at 101 and the database still
reads; only the index changed. `git check-ignore` confirms the rule matches —
which it could not report while the files were still tracked.

### Left dirty, with reasons

- **`intersearch/uv.lock`** — +23 packages (`mcp`, `pydantic`, `cryptography`,
  `einops`…) with `pyproject.toml` **unchanged**. A resolution somebody
  produced locally, regenerable from `pyproject.toml`, and not obviously
  anyone's intended commit. Left for its owner.
- **`intervox`** and **`interflux`** — two entries each, created at
  `09:45:26` on 2026-07-27 by a machine-wide hook installer, not by this work.
- **The monorepo itself** — the same sweep typechanged `.beads/hooks/pre-commit`
  and left a `.bak` beside it. Two entries, same origin.

### Trap: a tracked hooks directory turns hook installs into commits

A hook installer symlinked `pre-commit` to
`/Users/sma/projects/dotfiles/cloud/pre-commit.sh` in roughly 130 repos under
`~/projects`. In almost all of them it landed in `.git/hooks/`, which git never
tracks — so it was invisible and harmless by construction.

It surfaced in exactly the repos whose `core.hooksPath` points into a **tracked**
directory:

| Repo | tracked hooks dir | `core.hooksPath` | went dirty |
|---|---|---|---|
| `interflux` | `.githooks` (1 file) | `.githooks` | **yes** |
| `intervox` | `.beads/hooks` (5 files) | `…/.beads/hooks` | **yes** |
| `cujgel` | `.beads/hooks` (5 files) | unset | no |
| `intermix` | `.beads/hooks` (5 files) | unset | no |

Tracking hook files is fine. Pointing `core.hooksPath` at the tracked copy is
what converts every hook installation into a pending commit — and here the
pending content is a symlink to an absolute path outside the repo, which would
break in every other clone. `intervoice` avoids this by ignoring
`.beads/hooks/`; `intervox` does not, so its five hook files remain exposed.

Neither was committed. Both are left for a decision — bead `Sylveste-0wt`.

### Open: `kimi.plugin.json` is missing from both upstreams

61 of 64 `interverse/` directories carry a `kimi.plugin.json`, and the ones that
are real repos (`interflux`, `interlock`, `intermux`) all track it. Upstream
`interhelm` and `interseed` do not have one at all, which looks like a
publishing gap in those two repos rather than a local artefact.

It was not fixed by copying the local files up: interhelm's was generated from
the stale v0.2.2 manifest and would have contradicted upstream's v0.2.3. The
right fix is to regenerate both in their own repos.

**Confirmed by the tool, 2026-07-27.** There is a generator —
`scripts/gen-kimi-manifests.py`, with a `--check` mode that writes nothing. It
reports across 62 plugins:

```
tally: {'ok': 39, 'differs': 21, 'missing': 2}
missing: interhelm interseed
```

The two missing are exactly the two named above, so "regenerate in their own
repos" was the right call and is now a measurement rather than an inference.

The 21 that differ are the same defect one step earlier. Five repos sampled
before and after their fast-forward each had `plugin.json` and
`kimi.plugin.json` **in sync at the old commit and out of sync at upstream
HEAD** — every one of those upstream commits bumped the version without
re-running the generator. The pull imported an inconsistency that already
existed upstream; it did not create it. Regeneration is not wired into the
release path.

Fixing one repo at a time does not converge: `--check` read 21 differs before
this session's work and 21 after. `interwatch` was fixed and removed from the
list, and `tldr-swinton` — whose fast-forward brought in a hand-edited upstream
manifest carrying `skills`/`commands` keys the generator does not emit — took
its place. The count holds level because bumps land at least as fast as manual
fixes. This needs one estate-wide pass plus a release-path hook, not repo-by-repo
attention. Tracked as `Sylveste-646`.

## See also

- `docs/reflections/2026-07-25-monorepo-tree-cleanup-reflect.md` — where the 198
  were first found
- `docs/solutions/2026-07-25-unattended-work-needs-a-stopped-signal.md`
  § "Adjacent: ignore-noise buries real work"
