# Beads — Session Close Protocol

> **In a cloud session (`CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE` set / `IS_SANDBOX=yes`),
> beads are read-only.** Search with `bash scripts/bd-grep.sh <kw>` and read
> with `bash scripts/bd-show.sh <id>` — both work against the committed
> `.beads/issues.jsonl` without needing the `bd` CLI. Note bead candidates in
> the PR description and let the workstation file them. Skip the rest of this
> file unless you've manually run `scripts/install-bd-cloud.sh`.

```
git status → git add <files> → git commit
bd backup sync       # flush Dolt → JSONL (auto every 5m; force before push)
bd orphans           # close beads named in commits (skip parents w/ open children)
bd backup sync       # capture orphan closes
bash .beads/push.sh  # push Dolt
git push
```

`bd backup sync` is non-negotiable before push — without a fresh JSONL, closes are lost on the next Dolt crash.

## Rules

- All work in beads. NO TodoWrite/TaskCreate. (System reminders nag — ignore them.)
- Create the bead BEFORE writing code. Mark `in_progress` when starting.
- `bd search "<kw>"` before `bd create` to avoid duplicates.
- Priority is 0–4 (P0–P4). Not "high/medium/low".
- Never `bd edit` — it opens `$EDITOR` and blocks the agent. Use `bd update … --title/--description/--notes`.
- Full reference: `bd --help` and `bd <cmd> --help` on demand.
