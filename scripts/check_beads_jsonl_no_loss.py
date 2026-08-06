#!/usr/bin/env python3
"""Refuse a commit whose .beads/issues.jsonl drops issue ids that HEAD has.

WHY THIS EXISTS, AND WHY THE EXISTING GUARD IS NOT ENOUGH

check_beads_jsonl_dolt_sync.py compares the staged export against the live Dolt
database in both directions. That is the right check for drift, and on
2026-08-04 it would have caught the incident below. But it can only ever be as
right as Dolt is: it answers "does the file match the database?", never "did this
commit throw away issues that were here a moment ago?". If the database bd
resolved is not the one this file belongs to, both sides of that comparison can
be wrong together and agree.

THE INCIDENT

`bd export -o .beads/issues.jsonl` was run from ~/projects (the parent workspace
directory) rather than from ~/projects/Sylveste. bd resolved correctly for the
directory it was in -- ~/.beads/embeddeddolt, 458 issues, every id `mk-*` -- and
`-o` wrote that database's contents over Sylveste's tracked export, taking it
from 3822 lines to 458 and dropping every Sylveste issue. Exit code 0.

Nothing about that is a bd bug: `-o` is a path, and bd was asked to write there.
The hazard is that the output path carries no relationship to the source
database, and the cwd that selects the database is invisible in the command.
`-o .beads/issues.jsonl` looks identical whether you are in the right directory
or one level up.

WHAT THIS CHECKS

Set difference on ids only, staged vs HEAD. Cheap, has no opinion about content,
and cannot be fooled by a wrong database -- a foreign export drops *every* id and
fails loudly.

Deliberate removals are still possible:
  * ids recorded in .beads/deletions.jsonl are expected to disappear
  * BEADS_ALLOW_JSONL_SHRINK=1 overrides for a genuine prune, and says so

Exit 0 nothing lost / 1 ids would be lost / 2 could not tell.

Exit 2 matters as much as 1. A guard that cannot read one of its two inputs must
not pass the commit: "I could not compare" and "nothing was lost" are the same
silence, and it is the silence this repo keeps getting bitten by.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


def ids_from_text(text: str, label: str) -> set[str]:
    out: set[str] = set()
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} line {n} is not JSON: {exc}") from exc
        i = d.get("id")
        if i:
            out.add(i)
    return out


def git_show(ref_path: str) -> str | None:
    """Content at a git ref, or None when the path does not exist there."""
    r = subprocess.run(["git", "show", ref_path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged-file", required=True,
                    help="path to the staged content, already extracted")
    ap.add_argument("--path", default=".beads/issues.jsonl")
    args = ap.parse_args()

    head = git_show(f"HEAD:{args.path}")
    if head is None:
        # No previous version: a first commit of the export cannot lose anything.
        print(f"beads-no-loss: {args.path} is new in this commit — nothing to lose")
        return 0

    try:
        with open(args.staged_file, errors="replace") as fh:
            staged_text = fh.read()
    except OSError as exc:
        print(f"beads-no-loss: CANNOT ASSESS — unreadable staged content: {exc}",
              file=sys.stderr)
        return 2

    try:
        head_ids = ids_from_text(head, "HEAD")
        staged_ids = ids_from_text(staged_text, "staged")
    except ValueError as exc:
        print(f"beads-no-loss: CANNOT ASSESS — {exc}", file=sys.stderr)
        return 2

    if not head_ids:
        print(f"beads-no-loss: CANNOT ASSESS — HEAD:{args.path} parsed to zero "
              f"ids, so 'nothing lost' would be meaningless", file=sys.stderr)
        return 2

    lost = head_ids - staged_ids
    if not lost:
        gained = len(staged_ids - head_ids)
        print(f"beads-no-loss: ok — {len(head_ids)} ids kept"
              + (f", {gained} added" if gained else ""))
        return 0

    # Deliberate deletions are recorded; honour them.
    deleted: set[str] = set()
    for src in (".beads/deletions.jsonl",):
        if not os.path.isfile(src):
            continue
        try:
            with open(src, errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    i = d.get("id") or d.get("issue_id")
                    if i:
                        deleted.add(i)
        except OSError:
            pass

    unexplained = lost - deleted
    if not unexplained:
        print(f"beads-no-loss: ok — {len(lost)} id(s) dropped, all recorded in "
              f".beads/deletions.jsonl")
        return 0

    if os.environ.get("BEADS_ALLOW_JSONL_SHRINK") == "1":
        print(f"beads-no-loss: OVERRIDDEN — {len(unexplained)} id(s) dropped with "
              f"BEADS_ALLOW_JSONL_SHRINK=1", file=sys.stderr)
        return 0

    sample = sorted(unexplained)[:8]
    pct = 100.0 * len(unexplained) / len(head_ids)
    print(f"""
beads-no-loss: REFUSING — this commit drops {len(unexplained)} of {len(head_ids)}
issue ids ({pct:.0f}%) from {args.path}, and they are not in .beads/deletions.jsonl.

  HEAD has   {len(head_ids)} ids
  staged has {len(staged_ids)} ids
  lost e.g.  {', '.join(sample)}{' ...' if len(unexplained) > len(sample) else ''}

The usual cause is `bd export -o {args.path}` run from the WRONG DIRECTORY. bd
picks its database from the current working directory, so running it one level up
(~/projects rather than ~/projects/Sylveste) exports a different project's
database over this file and still exits 0. Check `cd`, then `bd info` -- it prints
the database it resolved -- and export again.

If the removal is deliberate, record the ids in .beads/deletions.jsonl or set
BEADS_ALLOW_JSONL_SHRINK=1 for this commit.
""".strip(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
