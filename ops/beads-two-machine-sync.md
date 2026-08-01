# Beads Two-Machine Sync — Verified State

> How bead state moves between Clavain (MacBook) and zklw (dedi), what differs
> between them, and which differences are deliberate. Companion to
> `publish-machine-roles.md`, which covers the *publish* role rather than beads.
>
> Verified end to end 2026-07-31 by observing hooks fire and beads arrive, not
> by confirming files were present. That distinction matters: this protocol had
> already failed once because a hook was installed at a path git ignores, which
> every file-presence check would have called healthy.

## The protocol

`.beads/issues.jsonl` is the git-tracked transport. Each machine keeps its own
Dolt database; the JSONL is how they reach each other.

| Direction | Mechanism | Trigger |
|---|---|---|
| Dolt → JSONL | export, then a dedicated commit | `post-commit` |
| JSONL → Dolt | `scripts/beads_safe_import.py` | `post-merge` |

Both machines set `core.hooksPath = <repo>/.beads/hooks`, so `.git/hooks/` is
**never executed**. Anything installed there is inert. Confirmed on both.
`core.hooksPath` is set by `bd hooks install`, not by us.

Both machines run **bd 1.1.2** against **schema v53**.

## One export mechanism, chosen

There are two things that could export the JSONL, and exactly one is enabled.

**`scripts/beads-auto-export.sh` (post-commit) is the live one.** It probes,
exports, and commits the result as its own commit.

**bd's built-in auto-export is off**, explicitly, in the tracked
`.beads/config.yaml`:

```yaml
export.auto: false
export.git-add: false
```

Why off, on the evidence rather than on preference:

- `export.auto` only *writes* the file. It never commits it, and only the
  committed copy is pushed — so on its own it strands a dirty `issues.jsonl` in
  the working tree indefinitely. Our post-commit path exports *and* commits,
  which is what a git-carried transport actually needs.
- `export.git-add` stages the export into whatever commit is forming, which
  widens `git commit -- <paths>` past the paths named. Observed on zklw: a
  one-path commit produced a two-file commit.

Verified after the change, on both machines: a pathspec commit contains exactly
the paths named, and the export arrives as a separate
`beads: sync export (automated)` commit.

### Why this was ever in doubt

Neither key had ever been *set*. Each machine inherited its bd version's
default, and the defaults disagree:

| bd version | `export.auto` | `export.git-add` |
|---|---|---|
| 1.0.0 | false | false |
| 1.0.2 | **true** | **true** |
| 1.1.x | false | false |

So zklw (1.0.2) exported on every write and Clavain (1.0.0) exported never, and
nobody had chosen either behaviour. That is the entire reason
`.beads/issues.jsonl` sat two days and 63 issues stale on one machine while the
other stayed perfectly current — the defect the previous three goals were
circling.

Setting both explicitly is the durable fix: the file is tracked, so both
machines read the same values whatever bd they run, and a future upstream
default flip cannot silently reintroduce either behaviour. It also fixed the
widening at bd 1.0.2, before either machine was upgraded.

## Upgrading bd

`bd` is one binary per machine serving **every** beads database on it (43 on
Clavain, 59 on zklw). bd 1.1.2 does **not** migrate an old database lazily — it
fails to open it (`column "started_at" could not be found`). So upgrading the
binary means migrating every database on that machine, not just this one.

The procedure that worked, per database:

```bash
# Pre-count must come from the OLD binary. The new one cannot open an
# unmigrated database at all, so "the new binary exported N" says nothing
# about what was there before.
( cd "$repo" && old-bd export --all -o pre.jsonl )
( cd "$repo" && BD_ALLOW_REMOTE_MIGRATE=1 bd migrate --yes )
( cd "$repo" && bd export --all -o post.jsonl )
# verify by comparing issue counts, not by the migrate exit code
```

`BD_ALLOW_REMOTE_MIGRATE=1` is required because bd refuses to migrate a
remote-backed database unattended: independent migration on two clones of a
*shared* remote forks the schema silently. That hazard does not apply between
Clavain and zklw — they do not share a Dolt remote and never `dolt pull` from
each other (see below) — so each migrates its own copy.

Result 2026-07-31: Sylveste went v23→v53 on Clavain and v32→v53 on zklw, with
3,804 issues + 1 memory preserved on each, ID sets identical.

### If a migration refuses with "dirty tables"

```
pending schema migrations alter pre-existing dirty tables: config
```

Upstream [#4566](https://github.com/gastownhall/beads/issues/4566) (closed):
"dirty working set deadlocks schema migration — `bd dolt commit` can't clear it
because it also triggers init schema". The remedy bd prints is therefore the one
thing that cannot work: the command told to clean the working set re-dirties it
on startup. Commit the working set with the `dolt` CLI instead, bypassing bd
entirely:

```bash
cd <dolt data dir>          # .beads/dolt, or ~/.beads/shared-server/dolt
dolt sql -q "use <db>; call dolt_add('.'); call dolt_commit('-m', 'commit working set before schema migration');"
```

Then re-run the migration. This cleared all 8 affected databases on Clavain.

### Databases that need `bd bootstrap`, not migration

16 databases (3 on Clavain, 13 on zklw) have a `.beads/` directory but no local
database — they report `bd where` / `bd bootstrap` hints rather than a schema
error. **These were already broken before the upgrade**, verified by running the
old binary against them. They are not migration casualties. Recovering one means
`bd bootstrap` to re-clone from its remote, which *replaces* local data, so it is
a per-project decision rather than a batch operation. Tracked as `sylveste-esjb`.

```
Clavain (3): jawncloud  phosphene  underground-beets
zklw   (13): agents  FLUXrig  garden-salon  intervox  intrdrm  oodacademy
             prodspecs  productrecs  shadow-work  spellswords  tropescraper
             wi2c  zahro
```

Note `shadow-work` appears here for zklw but migrated cleanly on Clavain — the
two machines do not have the same set of working databases, so this list is
per-machine rather than a property of the repo.

## The trap that cost the most

`.beads/metadata.json` carries a `dolt_server_port` field that bd 1.1.2 warns
is deprecated "(can cause cross-project data leakage)". It is a real hazard, not
a style note.

Copying a `.beads/` directory elsewhere to experiment on it does **not** isolate
it. Deleting `.beads/dolt-server.port` is not enough: bd falls back to
`dolt_server_port` in `metadata.json` and connects to the *original* machine's
live server. A "sandbox" migration run this way applied 30 schema migrations to
the production database instead of the copy.

To actually isolate a copy, remove the port from `metadata.json` too — or copy
neither file and let bd start its own server.

## Drift register

### Resolved

**bd version.** Was 1.0.0 (Clavain) vs 1.0.2 (zklw); both now 1.1.2. This was
the root of the hook-shim churn — each bd rewrites its managed blocks to its own
version string, so the two machines flipped
`# --- BEGIN BEADS INTEGRATION v1.0.x ---` back and forth. Verified fixed by
observation: after pulling the other machine's hooks, `bd hooks install --force`
on zklw produced an empty diff. Both machines now generate byte-identical hook
content. `bd hooks install` only rewrites between its own markers — the SYLVESTE
blocks in those files survive it, checked against a backup.

**Dolt schema.** Was v23 (Clavain) vs v32 (zklw); both now v53. Worth noting
that a 9-version schema divergence went unnoticed for months without breaking
anything, which is a genuine point in favour of a schema-tolerant JSONL
transport over Dolt-level replication.

**`setsid` is Linux-only.** The post-commit Dolt auto-push block used it
unconditionally, so on macOS the subshell failed, `|| true` swallowed it, and
`.beads/push-hook.log` was never created — no output, no error, no trace. It now
falls back to a plain background job and always writes the log.

**Push privileges.** Previously Clavain pushed `main` directly (the remote
reported `Bypassed rule violations`) while zklw was rejected. `enforce_admins`
is now **true** on `main`, so both machines take the same route: push to
`autosync/<machine>`, wait for `Generator and parity checkers`, then
fast-forward `main`. The asymmetry recorded here previously no longer exists.

### Accepted, with reasons

**Issue-ID prefix casing differs.** zklw creates `sylveste-vftd`; Clavain
creates `Sylveste-v4ub`. Both resolve, and the drift checker compares whole IDs,
so mixed casing is cosmetic — a tell of which machine filed a bead.

**Dolt remotes differ, and are not shared.** zklw's is
`file:///home/mk/projects/Sylveste/.beads/remote/Sylveste` (a directory on zklw);
Clavain's is `git+https://github.com/mistakeknot/Sylveste.git`. Neither is a
cross-machine channel. This is why the two machines can migrate schema
independently without the fork hazard bd warns about — and why the git-tracked
JSONL is the only thing actually carrying beads between them.

**Dolt mode differs per project, not per machine.** Sylveste runs a managed
per-project sql-server; other projects (cujgel, and most of the smaller ones)
run embedded. `bd sql` is *not supported in embedded mode*, so
`check_beads_jsonl_dolt_sync.py` and `beads_safe_import.py` only work in
server mode. Fine here; a trap if these scripts are ever reused elsewhere.

**`.beads/embeddeddolt` on Clavain is dead.** 42M, last written 2026-04-07, zero
files touched since. The live server's cwd is `.beads/dolt`. Left in place
rather than deleted, but it is not the database and should not be mistaken for
one.

## The signer asymmetry is handled, not assumed

zklw is `role: signer`; Clavain is `role: verifier` with only
`.clavain/keys/authz-project.pub`. Same key fingerprint (`3d1c3001d533c5a9`).
So `.beads/push.sh` genuinely cannot work on Clavain, and the git-tracked JSONL
is the **only** egress for bead state there.

Checked whether anything quietly depends on that push succeeding:

- `.beads/push.sh` exits **1** when it refuses, with a message naming the
  reason. It does not fail open.
- `.beads/close-and-sync.sh` runs under `set -euo pipefail`, so it aborts on
  that exit rather than reporting a close as synced.

Both correct. The asymmetry is visible at every call site that could be misled
by it.

## Limitations

**A failing probe is loud, not silent.** `beads-auto-export.sh` decides whether
to export by running the same checker that guards commits. If that checker
cannot run, the script now says so on stderr and names the fix, instead of
skipping quietly. It previously conflated "bd absent (cloud session)" with "the
probe ran and failed" — and the second went silent for a while today when a
schema mismatch broke `bd sql`, which is the exact failure shape this whole
mechanism was built to replace.

Note the branch keys on *"did it produce a verdict"*, not on the exit code: the
checker is also the pre-commit guard, so it exits non-zero precisely when it
finds drift, which is when an export is wanted.

**Deletions do not propagate. Close beads; do not delete them.**

`beads_safe_import.py` applies records that are absent locally or newer — it
never deletes, because absence in an incoming export is ambiguous: either
"deleted there" or "not created there yet".

Observed: a probe bead filed on zklw, deleted on Clavain, survived in zklw's
Dolt and was re-exported — a push from zklw would have resurrected it. Deleting
it on both machines was the only clean fix.

bd 1.1.2 understands `tombstone` rows on import, so this is now *fixable* rather
than inherent. It is not fixed: nothing in our path emits tombstones yet.

**Expect merge conflicts on `.beads/issues.jsonl` when both machines export.**

It is a ~3,800-line generated file and both ends rewrite it, so git conflicts on
it are routine rather than exceptional. Do not hand-resolve the hunks. Dolt is
the authority; the file is a projection:

```bash
git show MERGE_HEAD:.beads/issues.jsonl > .beads/issues.jsonl   # take incoming
git add .beads/issues.jsonl && git commit --no-edit             # finish merge
python3 scripts/beads_safe_import.py                            # theirs -> local Dolt
bd export --output .beads/issues.jsonl                          # union back out
```

Taking the incoming side first is deliberate: the import is additive, so nothing
local is lost by adopting the other machine's file and then re-exporting the
union. Resolving the other way round would drop whatever the incoming export
uniquely held.

## Known-redundant, not yet retired

bd 1.1.2's own `bd import` now enforces the same rule `beads_safe_import.py`
was written for — "updated_at is strictly newer; older rows are skipped; rows
with the same updated_at keep every local column" — and enforces it *inside the
transaction* rather than as a pre-filter, with `--allow-stale` as the deliberate
override.

That makes our importer a candidate for retirement, on better terms than it
currently offers. It is left in place because swapping the import half is a
change to the mechanism that protects against silent reversion, and deserves
its own verification against real two-machine data rather than a footnote in an
export-side goal.
