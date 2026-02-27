#!/usr/bin/env python3
"""
Create placeholder beads for IDs referenced in roadmap docs but missing in Beads.

Scope:
- docs/roadmap.json
- any readable **/*roadmap*.md file in repo
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ID_RE = re.compile(r"iv-[a-z0-9]+(?:\.[0-9]+)*", re.IGNORECASE)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def bead_exists(bead_id: str) -> bool:
    q = f"select count(*) as c from issues where id = '{bead_id}'"
    result = run(["bd", "sql", "--json", q])
    if result.returncode != 0:
        return False
    try:
        rows = json.loads(result.stdout or "[]")
        if not rows:
            return False
        return int(rows[0].get("c", 0)) > 0
    except Exception:
        return False


def find_roadmap_files(repo_root: Path) -> list[Path]:
    files = sorted(p for p in repo_root.glob("**/*roadmap*.md") if ".git/" not in p.as_posix())
    json_path = repo_root / "docs" / "roadmap.json"
    if json_path.exists():
        files.append(json_path)
    return files


def collect_missing_ids(repo_root: Path) -> tuple[set[str], dict[str, list[str]], list[str]]:
    files = find_roadmap_files(repo_root)
    ids_to_sources: dict[str, list[str]] = defaultdict(list)
    unreadable: list[str] = []

    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            unreadable.append(rel)
            continue
        for bead_id in {m.group(0).lower() for m in ID_RE.finditer(text)}:
            ids_to_sources[bead_id].append(rel)

    referenced = set(ids_to_sources.keys())
    missing = {bead_id for bead_id in referenced if not bead_exists(bead_id)}
    return missing, ids_to_sources, unreadable


def make_title(bead_id: str, sources: list[str]) -> str:
    primary = sources[0] if sources else "roadmap"
    return f"[roadmap-recovery] Missing roadmap bead {bead_id} ({primary})"


def make_description(bead_id: str, sources: list[str]) -> str:
    source_lines = "\n".join(f"- {s}" for s in sorted(set(sources)))
    return (
        "Recovered placeholder bead created because this ID appears in roadmap docs but is "
        "missing from the active Beads database.\n\n"
        f"Bead ID: {bead_id}\n"
        "Sources:\n"
        f"{source_lines}"
    )


def create_placeholder(bead_id: str, sources: list[str], dry_run: bool) -> tuple[bool, str]:
    title = make_title(bead_id, sources)
    desc = make_description(bead_id, sources)
    cmd = [
        "bd",
        "create",
        "--id",
        bead_id,
        "--type",
        "task",
        "--priority",
        "2",
        "--title",
        title,
        "--description",
        desc,
        "--labels",
        "recovered,placeholder,roadmap-missing",
    ]
    if dry_run:
        return True, f"would_create {bead_id}"
    result = run(cmd)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "").strip()
    return True, f"created {bead_id}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create missing roadmap beads.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    repo_root = Path.cwd()
    missing, ids_to_sources, unreadable = collect_missing_ids(repo_root)

    created = 0
    skipped = 0
    failed = 0

    for bead_id in sorted(missing):
        # Skip obvious template placeholders in artifact docs.
        if bead_id in {"iv-aaaa", "iv-bbbb", "iv-xxxx"}:
            skipped += 1
            print(f"skip_template {bead_id}")
            continue
        ok, msg = create_placeholder(bead_id, ids_to_sources.get(bead_id, []), args.dry_run)
        if ok:
            created += 1
            print(msg)
        else:
            failed += 1
            print(f"error {bead_id}: {msg}", file=sys.stderr)

    print(
        "summary:",
        f"missing_detected={len(missing)}",
        f"created={created}",
        f"skipped={skipped}",
        f"failed={failed}",
        f"unreadable_files={len(unreadable)}",
        f"dry_run={str(args.dry_run).lower()}",
    )
    if unreadable:
        print("unreadable:")
        for p in unreadable:
            print(p)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
