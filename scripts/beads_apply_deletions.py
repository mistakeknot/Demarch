#!/usr/bin/env python3
"""Apply intentional bead deletions recorded by the other machine.

`bd import` is upsert-only: it creates and updates, never deletes. So a bead
deleted on one machine survives on the other, and the moment that machine
exports, the bead is written back into the shared JSONL and imported home
again. The deletion undoes itself, silently. Demonstrated in both directions
before this existed.

Absence from the JSONL cannot be the deletion signal. A file is missing a bead
for several reasons that are not deletion — a filtered export (`bd export`
omits infra beads by default), a bead created locally and not yet exported, a
truncated write. Treating absence as intent would delete live work.

So the intent is recorded explicitly, in `.beads/deletions.jsonl`: append-only,
git-tracked, one JSON object per line, written by `scripts/beads-confirm-
deletion.sh` at the moment a human confirms the deletion was deliberate. This
file is the *only* thing that authorises removing a bead here.

  {"id": "sylveste-abc", "deleted_at": "2026-08-01T05:00:00Z",
   "actor": "mk", "machine": "zklw", "note": "sync probe"}

Run AFTER the import, never before: the import would otherwise re-create
whatever this just removed.

Two beads are refused rather than deleted, and both say so out loud:

  * the local bead is NEWER than the deletion record — someone worked it here
    after the other machine gave up on it. Deleting would discard that work.
    Same last-writer-wins doctrine the import guard uses, and the same reason:
    a silent revert is worse than a visible conflict.
  * the ledger line does not parse. A deletion that fails to apply because a
    line was quietly skipped is exactly the failure this file exists to end.

Usage:
  beads_apply_deletions.py               # apply
  beads_apply_deletions.py --dry-run     # report what would be deleted
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_ts(value: str) -> datetime | None:
    """RFC3339 -> aware datetime. Both sides of the comparison come from bd."""
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_ledger(path: Path) -> tuple[list[dict], list[tuple[int, str]]]:
    """Return (entries, malformed) — malformed lines are reported, not ignored."""
    entries: list[dict] = []
    malformed: list[tuple[int, str]] = []
    with path.open(encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
            except ValueError:
                malformed.append((lineno, line[:80]))
                continue
            if not isinstance(row, dict) or not isinstance(row.get("id"), str):
                malformed.append((lineno, line[:80]))
                continue
            entries.append(row)
    return entries, malformed


def local_state(repo: Path, bd: str, issue_id: str) -> dict | None:
    """The local row, or None if this bead does not exist here.

    Deliberately `bd show --json` and not `bd sql`: the latter does not exist in
    embedded mode, which is what a fresh `bd init` produces. A deletion path
    that only works in server mode would be inert exactly where it is least
    expected to be.
    """
    result = subprocess.run(
        [bd, "show", issue_id, "--json"], cwd=repo, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        return None
    payload = result.stdout[result.stdout.find("[") :] if "[" in result.stdout else ""
    try:
        rows = json.loads(payload)
    except ValueError:
        return None
    if isinstance(rows, list) and rows:
        return rows[0]
    return rows if isinstance(rows, dict) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--ledger", type=Path, default=None)
    ap.add_argument("--bd-command", default="bd")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    ledger = args.ledger or (repo / ".beads" / "deletions.jsonl")
    if not ledger.exists():
        return 0
    bd = shutil.which(args.bd_command) if "/" not in args.bd_command else args.bd_command
    if bd is None:
        return 0  # cloud session; nothing to delete from

    entries, malformed = read_ledger(ledger)
    for lineno, text in malformed:
        print(
            f"beads: deletions.jsonl line {lineno} is not a usable record, so a "
            f"deletion may not have been applied: {text}",
            file=sys.stderr,
        )
    if not entries:
        return 2 if malformed else 0

    deleted: list[str] = []
    refused: list[tuple[str, str, str]] = []
    for row in entries:
        issue_id = row["id"]
        current = local_state(repo, bd, issue_id)
        if current is None:
            continue  # already gone here; the ledger replays harmlessly

        deleted_at = parse_ts(row.get("deleted_at") or "")
        updated_at = parse_ts(current.get("updated_at") or "")
        if deleted_at and updated_at and updated_at > deleted_at:
            refused.append((issue_id, current.get("updated_at", ""), row.get("deleted_at", "")))
            continue

        if args.dry_run:
            deleted.append(issue_id)
            continue
        result = subprocess.run(
            [bd, "delete", issue_id, "--force"], cwd=repo, text=True, capture_output=True, check=False
        )
        if result.returncode != 0:
            print(
                f"beads: could not delete {issue_id}: "
                f"{(result.stderr or result.stdout).strip().splitlines()[:1]}",
                file=sys.stderr,
            )
            continue
        deleted.append(issue_id)

    for issue_id, local_ts, del_ts in refused:
        print(
            f"beads: NOT deleting {issue_id} — it was changed here at {local_ts}, "
            f"after the deletion was recorded at {del_ts}.",
            file=sys.stderr,
        )
        print(
            "       Someone worked this bead after the other machine dropped it. "
            "Resolve by hand: keep it, or delete it here with "
            "scripts/beads-confirm-deletion.sh",
            file=sys.stderr,
        )

    if deleted and (not args.quiet or args.dry_run):
        verb = "would delete" if args.dry_run else "deleted"
        print(f"beads_apply_deletions {verb}={len(deleted)}: {' '.join(deleted[:10])}")

    return 2 if malformed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
