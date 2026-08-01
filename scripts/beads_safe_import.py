#!/usr/bin/env python3
"""Import issues from the tracked JSONL into local Dolt without losing local state.

`bd import` upserts every record in the file. After a pull that is exactly wrong:
the incoming export was written on another machine at some earlier moment, so it
carries that machine's view of issues this machine has since changed. Importing
it wholesale reverts them — an issue closed here reopens because the export
predates the close.

This filters to the records that are safe to apply:

  * absent locally      -> import (this is the whole point; another machine's
                           issues are invisible to `bd` here until imported)
  * incoming is newer   -> import (a real update from the other machine)
  * incoming is older   -> SKIP (the local row is the more recent writer)
  * timestamps equal    -> skip; nothing to gain, and no basis to prefer either

Last-writer-wins on updated_at. Crude, but the two machines work on largely
disjoint issues, and the failure it prevents (silent reversion) is worse than
the one it permits (a genuinely concurrent edit resolving to one side).

Usage:
  beads_safe_import.py                 # apply
  beads_safe_import.py --dry-run       # report what would be applied
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    """Return (issue records, raw lines) preserving original line text.

    The raw line is kept so an imported record is byte-identical to what was
    committed — re-serializing risks dropping fields this script does not model.
    """
    records: list[dict] = []
    lines: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("_type") == "memory":
                continue
            if not isinstance(row.get("id"), str):
                continue
            records.append(row)
            lines.append(line)
    return records, lines


def load_local(repo: Path, bd_command: str = "bd") -> dict[str, str]:
    """Map local issue id -> updated_at, straight from Dolt."""
    resolved = shutil.which(bd_command) if "/" not in bd_command else bd_command
    if resolved is None:
        raise RuntimeError(f"bd not found on PATH: {bd_command}")
    result = subprocess.run(
        [resolved, "sql", "select id, updated_at from issues"],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "bd sql failed")
    out: dict[str, str] = {}
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line or set(line) <= {"-", "+"} or line.startswith("("):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 2 and cells[0] and cells[0] != "id":
            out[cells[0]] = cells[1]
    return out


def normalize_ts(value: str) -> str:
    """Reduce the two timestamp renderings to one comparable form.

    Dolt prints `2026-07-31 15:57:07 +0000 UTC`; the JSONL carries
    `2026-07-31T15:57:07Z`. Comparing them raw makes every incoming record look
    newer, which would defeat the entire point of this script.

    Strip the zone suffix BEFORE touching the date/time separator: "UTC"
    contains a T, so normalizing the separator first rewrites " +0000 UTC" to
    " +0000 U C" and the suffix no longer matches. That inverted the filter into
    the plain upsert it exists to replace, and is why the ordering has a test.
    """
    if not value:
        return ""
    v = value.strip()
    for suffix in (" +0000 UTC", " UTC", "+00:00", "Z"):
        if v.endswith(suffix):
            v = v[: -len(suffix)]
            break
    return v.replace("T", " ").strip()


def classify(records: list[dict], lines: list[str], local: dict[str, str]):
    """Split incoming records into (to_apply_lines, new_ids, updated_ids, skipped)."""
    apply_lines: list[str] = []
    new_ids: list[str] = []
    updated_ids: list[str] = []
    skipped: list[tuple[str, str, str]] = []
    for row, line in zip(records, lines):
        issue_id = row["id"]
        incoming = normalize_ts(row.get("updated_at") or "")
        if issue_id not in local:
            apply_lines.append(line)
            new_ids.append(issue_id)
            continue
        current = normalize_ts(local[issue_id])
        if incoming > current:
            apply_lines.append(line)
            updated_ids.append(issue_id)
        else:
            skipped.append((issue_id, incoming, current))
    return apply_lines, new_ids, updated_ids, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--issues-jsonl", type=Path, default=None)
    ap.add_argument("--bd-command", default="bd")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    path = args.issues_jsonl or (repo / ".beads" / "issues.jsonl")
    if not path.exists():
        return 0
    if shutil.which(args.bd_command) is None and "/" not in args.bd_command:
        return 0

    try:
        records, lines = load_jsonl(path)
        local = load_local(repo, args.bd_command)
    except Exception as exc:
        print(f"beads_safe_import error: {exc}", file=sys.stderr)
        return 2

    apply_lines, new_ids, updated_ids, skipped = classify(records, lines, local)

    if not args.quiet or args.dry_run:
        print(
            f"beads_safe_import incoming={len(records)} local={len(local)} "
            f"new={len(new_ids)} updated={len(updated_ids)} skipped_older={len(skipped)}"
        )
        for issue_id in new_ids[:10]:
            print(f"  + {issue_id}")
        if len(new_ids) > 10:
            print(f"  ... {len(new_ids) - 10} more new")

    if not apply_lines:
        return 0
    if args.dry_run:
        return 0

    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        tmp.write("\n".join(apply_lines) + "\n")
        tmp_path = tmp.name
    try:
        resolved = shutil.which(args.bd_command) or args.bd_command
        result = subprocess.run(
            [resolved, "import", tmp_path], cwd=repo, text=True, capture_output=True, check=False
        )
        if result.returncode != 0:
            print(result.stderr.strip() or "bd import failed", file=sys.stderr)
            return 1
        if not args.quiet:
            print(result.stdout.strip())
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
