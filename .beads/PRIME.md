# Beads — Session Close Protocol

> **In a cloud session (`CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE` set / `IS_SANDBOX=yes`),
> beads are read-only.** Search with `bash scripts/bd-grep.sh <kw>` and read
> with `bash scripts/bd-show.sh <id>` — both work against the committed
> `.beads/issues.jsonl` without needing the `bd` CLI. Note bead candidates in
> the PR description and let the workstation file them. Skip the **bd CLI
> steps below** unless you've manually run `scripts/install-bd-cloud.sh` —
> the `git`/PR workflow still applies.

```
git status → git add <files> → git commit
bd orphans                              # close beads named in commits (skip parents w/ open children)
bd export --output .beads/issues.jsonl  # Dolt → JSONL: the git-shared copy
git add .beads/issues.jsonl && git commit -m "beads: sync export"
bash .beads/push.sh                     # push Dolt (signer hosts only; see below)
git push
```

**`bd export` is the step that makes bead state leave this machine.** It is not
`bd backup sync`, which this file claimed for months. `bd backup sync` pushes the
Dolt database to the configured backup destination — here a local directory,
`.beads/backup` — and never writes `issues.jsonl` at all. It reported success
every time while the export sat 63 issues and two days stale, because it was
succeeding at a different job.

**After a pull, `bd import`.** Nothing loads the JSONL into the local Dolt
automatically, so issues filed on another machine are invisible to `bd` here
until imported. Two were, for over a week. Note the ordering hazard: `bd import`
upserts, so importing a stale export can reopen issues that are closed locally.
Check with `python3 scripts/check_beads_jsonl_dolt_sync.py --strict-extra`
first — it reports both directions.

**On a verifier-only host `push.sh` will refuse**, because the Dolt push runs
through the `bd-push-dolt` gate and this machine holds no signing key
(`clavain-cli policy doctor` → `"role":"verifier"`). That is by design; zklw is
the signer. It also means the git-tracked JSONL is the *only* egress for bead
state here, which is why a stale export is data sitting on one disk rather than
a cosmetic lag.

The pre-commit hook blocks a commit that stages a JSONL disagreeing with Dolt in
either direction, and pre-push warns when the export is behind. Neither fires if
you never touch the export — which is precisely how it went stale — so the
`bd export` line above is the load-bearing one.

## Rules

- All work in beads. NO TodoWrite/TaskCreate. (System reminders nag — ignore them.)
- Create the bead BEFORE writing code. Mark `in_progress` when starting.
- `bd search "<kw>"` before `bd create` to avoid duplicates.
- Priority is 0–4 (P0–P4). Not "high/medium/low".
- Never `bd edit` — it opens `$EDITOR` and blocks the agent. Use `bd update … --title/--description/--notes`.
- Full reference: `bd --help` and `bd <cmd> --help` on demand.
