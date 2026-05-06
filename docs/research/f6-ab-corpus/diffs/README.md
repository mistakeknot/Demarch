# Diff snapshots — audit fallback

This directory is for materialised diff snapshots used as the audit fallback
when the harness cannot reproduce a diff via `git show <sha>`.

The default reproduction path is `git show <sha>` against the monorepo HEAD.
Snapshots are added here only when:

- the source commit risks mutation (rebase, force-push) before F6b ships, or
- the diff was synthesised (e.g., a fixture that does not correspond to a
  monorepo commit), or
- the corpus is being moved to a different host where the source SHA does not
  resolve.

When `manifest.jsonl` row for a diff has `diff_snapshot_path: "diffs/<id>.diff"`
and that file exists, the harness prefers the snapshot over `git show`. When
no `diff_snapshot_path` is set or the file is absent, the harness falls back to
`git show <sha>`.

V1 of the corpus does **not** materialise snapshots — every diff is reproducible
from its SHA against the locked baseline `f72d3cfd`. Add a snapshot here if a
SHA goes missing.
