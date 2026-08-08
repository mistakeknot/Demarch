#!/usr/bin/env python3
"""Inventory of how every repo's beads export relates to a beads database.

DELIBERATELY NOT A `rig-` CHECK, AND THIS IS THE POINT

Everything else in .local/bin named `rig-*` honours the estate's contract: exit 0
clean, 1 findings, 2 could-not-assess, wired into rig-health-check.sh, red means
act. This tool does not, because a standing check needs a signal with both
COVERAGE (it can judge most repos) and PRECISION (what it flags is real), and on
2026-08-05 four candidate signals were measured on 78 `.beads` directories on
Clavain and 94 on zklw. All four failed one or the other:

  1. Declared issue-prefix vs the export's ids.
     Only 8 of 78 .beads/config.yaml files declare `issue-prefix` (10 of 94 on
     zklw). 87% unjudgeable -- which is the exact defect this was meant to fix:
     the predecessor sweep reported cannot-assess for 30 of 50 directories.

  2. "Is there a database inside this repo?"
     34 of 78 track an export with no local database. But that is the ordinary
     shape of a research clone that carries an upstream `issues.jsonl`, and an
     export run IN such a repo does not write foreign data -- it fails with "no
     beads database found" (measured in research/frankentui, which has no
     database even though ~/projects/Sylveste above it does: bd does not walk up
     past the repo). So these are structural facts, not defects, and a check that
     is red on 34 repos every day is a check nobody reads.

  3. "Does one export carry more than one prefix family?" (declaration-free, so
     full coverage.) Fires on 10 of 43 readable exports, and all ten are benign:
     research clones inherit the upstream project's `bd-*` ids alongside their
     own prefix. research/ntm carries bd+br+ntm; mediumsetting carries
     beads+mediumsetting. Full coverage, no precision.

  4. The export against the LIVE database, which is the question that actually
     matters. Needs `bd` per repo: a Dolt server spawned per database, lock
     contention across ~90 directories, and it does not even complete -- Nartopo
     and mediumsetting both fail to open with "pending schema migrations alter
     pre-existing dirty tables" (upstream gastownhall/beads#4566).

So there is no cheap standing check here, and inventing one out of signal 1 or 2
would have shipped either 87% silence or 34 standing false alarms. What protects
the fleet instead is the pair that needs no per-repo knowledge at all:
cloud/pre-commit-beads-no-loss.py refuses any commit that drops ids, and
guard-bd-export-pinned.py refuses an unpinned `bd export -o`.

This file remains because the four measurements above are worth being able to
redo, and because "what is the binding shape of this fleet" is a real question
with a determinate answer. It is an inventory, so it reports and exits 0.

EXIT.  0 inventory produced / 2 the root could not be read.

There is no exit 1: this tool has no findings, by construction. A number in the
summary is not an alarm, and pretending otherwise is how a check earns being
ignored.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PREFIX_RE = re.compile(r"^\s*issue-prefix\s*:\s*[\"']?([^\"'\s#]+)", re.M)
# `embeddeddolt` is the DEFAULT layout; `dolt` is what `dolt.shared-server: false`
# produces. Sylveste is the only repo here with the latter, and a marker list
# derived from Sylveste alone reported 40 healthy repos as having no database.
# `bd where` is no help either: it prints `database: .../.beads/dolt` in repos
# whose database is actually `.beads/embeddeddolt` -- the path it would use, not
# the one that exists.
DB_MARKERS = ("dolt", "embeddeddolt", "beads.db", "issues.db")
SKIP_DIRS = {"node_modules", "target", ".venv", "venv", "dist", "build",
             ".mypy_cache", ".pytest_cache", "__pycache__", "backup"}
MAXDEPTH = 5
TIMEOUT = 20


def git(args: list[str], cwd: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, errors="replace", timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return 99, ""
    return r.returncode, r.stdout.rstrip("\n")


def has_database(beads: Path) -> bool:
    if any((beads / m).exists() for m in DB_MARKERS):
        return True
    try:
        return any(p.suffix == ".db" for p in beads.iterdir())
    except OSError:
        return False


def find_beads_dirs(root: Path) -> list[Path]:
    out: list[Path] = []
    base = len(root.parts)
    for dirpath, dirnames, _ in os.walk(root):
        d = Path(dirpath)
        if len(d.parts) - base >= MAXDEPTH:
            dirnames[:] = []
            continue
        dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
        if d.name == ".beads":
            dirnames[:] = []
            out.append(d)
    return sorted(out)


def classify(beads: Path) -> dict:
    repo_guess = str(beads.parent)
    rc, top = git(["rev-parse", "--show-toplevel"], repo_guess)
    if rc != 0 or not top:
        return {"dir": repo_guess, "state": "not-a-repo"}
    top = top.strip()

    export = beads / "issues.jsonl"
    rc, _ = git(["ls-files", "--error-unmatch",
                 os.path.relpath(export, top)], top)
    tracked = rc == 0
    has_db = has_database(beads)
    if not tracked:
        return {"dir": repo_guess, "repo": top, "state": "no-tracked-export",
                "has_db": has_db}

    try:
        text = export.read_text(errors="replace")
    except OSError as exc:
        return {"dir": repo_guess, "repo": top, "state": "unreadable",
                "why": str(exc), "has_db": has_db}

    counts: collections.Counter[str] = collections.Counter()
    bad = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(d, dict) and d.get("id"):
            counts[str(d["id"]).split("-")[0]] += 1
    if bad and not counts:
        return {"dir": repo_guess, "repo": top, "state": "unparseable",
                "why": f"{bad} bad line(s), no readable ids", "has_db": has_db}

    prefix = None
    cfg = beads / "config.yaml"
    if cfg.is_file():
        try:
            m = PREFIX_RE.search(cfg.read_text(errors="replace"))
            prefix = m.group(1) if m else None
        except OSError:
            pass

    families: collections.Counter[str] = collections.Counter()
    for p, n in counts.items():
        families[p.lower()] += n

    # Case-insensitive on purpose: Sylveste declares `sylveste` and legitimately
    # carries 339 `Sylveste-*` ids next to 3490 `sylveste-*` ones.
    mismatch = None
    if prefix:
        foreign = {k: v for k, v in families.items() if k != prefix.lower()}
        mismatch = foreign or None

    return {"dir": repo_guess, "repo": top, "state": "tracked-export",
            "ids": sum(counts.values()), "families": dict(families),
            "declared": prefix, "mismatch": mismatch, "has_db": has_db}


def main() -> int:
    # __doc__ is None under `python -OO`, so don't dereference it blind.
    ap = argparse.ArgumentParser(
        description=(__doc__ or "beads binding inventory").splitlines()[0])
    ap.add_argument("--root", default=str(Path.home() / "projects"))
    ap.add_argument("--verbose", action="store_true",
                    help="list every directory, not just the notable ones")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"beads-binding-inventory: CANNOT READ root {root}", file=sys.stderr)
        return 2

    rows = [classify(b) for b in find_beads_dirs(root)]
    home = str(Path.home())
    rel = lambda p: p.replace(home, "~")

    tracked = [r for r in rows if r["state"] == "tracked-export"]
    unreadable = [r for r in rows if r["state"] in ("unreadable", "unparseable")]
    declared = [r for r in tracked if r["declared"]]
    mismatched = [r for r in tracked if r.get("mismatch")]
    nodb = [r for r in tracked if not r["has_db"]]
    multi = [r for r in tracked if len(r["families"]) > 1]

    print(f"beads binding inventory on {os.uname().nodename} ({rel(str(root))})")
    print(f"  .beads directories          {len(rows)}")
    print(f"  tracked exports             {len(tracked)}")
    print(f"  ...with a database here     {len(tracked) - len(nodb)}")
    print(f"  ...without one             {len(nodb)}   (normal for a research "
          f"clone; an export run there fails rather than writing foreign data)")
    print(f"  ...declaring issue-prefix   {len(declared)}   "
          f"({100*len(declared)//max(len(tracked),1)}% -- the coverage ceiling "
          f"for any prefix-based check)")
    print(f"  ...prefix DISAGREES         {len(mismatched)}")
    print(f"  ...multiple prefix families {len(multi)}   (benign: clones inherit "
          f"upstream ids)")
    print(f"  unreadable / unparseable    {len(unreadable)}")

    if mismatched:
        print("\n  exports whose ids disagree with their declared prefix:")
        for r in sorted(mismatched, key=lambda x: -x["ids"]):
            print(f"    {rel(r['dir'])}: declares '{r['declared']}', "
                  f"carries {r['mismatch']}")
    if unreadable:
        print("\n  could not read:")
        for r in unreadable:
            print(f"    {rel(r['dir'])}: {r.get('why', r['state'])}")
    if args.verbose:
        print("\n  every tracked export:")
        for r in sorted(tracked, key=lambda x: -x["ids"]):
            db = "db" if r["has_db"] else "--"
            print(f"    {r['ids']:>5}  {db}  {str(r['declared'] or '-'):<12} "
                  f"{sorted(r['families'])}  {rel(r['dir'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
