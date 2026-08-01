# Beads — Session Close Protocol

> **In a cloud session (`CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE` set / `IS_SANDBOX=yes`),
> beads are read-only.** Search with `bash scripts/bd-grep.sh <kw>` and read
> with `bash scripts/bd-show.sh <id>` — both work against the committed
> `.beads/issues.jsonl` without needing the `bd` CLI. Note bead candidates in
> the PR description and let the workstation file them. Skip the **bd CLI
> steps below** unless you've manually run `scripts/install-bd-cloud.sh` —
> the `git`/PR workflow still applies.

```
git status → git add <files> → git commit    # the export follows automatically
bd orphans                                   # close beads named in commits
git push
```

**The export is automatic now.** A post-commit hook runs
`scripts/beads-auto-export.sh`, which refreshes `.beads/issues.jsonl` from Dolt
and commits it *on its own*, as `beads: sync export (automated)`. Your commits
are untouched — it never stages the export into a commit you authored, because
doing that widens `git commit -- <paths>` beyond the paths you named.

It costs ~0.3s per commit (a probe) and ~3s only when beads actually changed.
`BEADS_NO_AUTO_EXPORT=1` opts out for one command.

**A pull imports automatically too**, via post-merge →
`scripts/beads_safe_import.py`. That is deliberately not `bd import`: a plain
import upserts every record, so an export written on another machine at an
earlier moment reverts anything changed here since — a bead you closed reopens,
silently. The safe importer applies only records that are absent locally or
genuinely newer.

**When automation stops and asks you.** If issues exist in the JSONL but not in
Dolt, the auto-export refuses, because exporting would delete them. Two very
different situations look identical from here, so it asks:

  - another machine's work, pulled but not imported → `python3 scripts/beads_safe_import.py`
  - something you deleted on purpose → `bd export --output .beads/issues.jsonl`

**What `bd backup sync` is.** Not this. It pushes the Dolt database to its
configured backup destination — here a local directory, `.beads/backup` — and
never writes `issues.jsonl`. This file claimed otherwise for months, and
reported success the whole time the export sat two days and 63 issues stale.

**On a verifier-only host `push.sh` will refuse**, because the Dolt push runs
through the `bd-push-dolt` gate and this machine holds no signing key
(`clavain-cli policy doctor` → `"role":"verifier"`). That is by design; zklw is
the signer. It also means the git-tracked JSONL is the *only* egress for bead
state here — which is why the export being automatic matters rather than being
a tidiness nicety.

Backstops, if the automation is bypassed: pre-commit blocks a commit staging a
JSONL that disagrees with Dolt in either direction, and pre-push warns when the
*committed* export is behind. Both should now be silent in normal operation.

## Rules

- All work in beads. NO TodoWrite/TaskCreate. (System reminders nag — ignore them.)
- Create the bead BEFORE writing code. Mark `in_progress` when starting.
- `bd search "<kw>"` before `bd create` to avoid duplicates.
- Priority is 0–4 (P0–P4). Not "high/medium/low".
- Never `bd edit` — it opens `$EDITOR` and blocks the agent. Use `bd update … --title/--description/--notes`.
- Full reference: `bd --help` and `bd <cmd> --help` on demand.
