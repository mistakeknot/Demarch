#!/usr/bin/env python3
"""
Replay missing bead placeholders from a commit-derived CSV manifest.

CSV columns:
  id,repo,commit,date,subject
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        capture_output=capture_output,
        check=False,
    )


def bead_exists(bead_id: str) -> bool:
    result = run_cmd(["bd", "show", bead_id], capture_output=True)
    return result.returncode == 0


def normalize_title(subject: str) -> str:
    title = f"[recovered] {subject.strip()}"
    if len(title) <= 220:
        return title
    return title[:217] + "..."


def build_description(manifest_path: str, repo: str, commit: str, date: str, subject: str) -> str:
    return (
        "Recovered placeholder bead created from git commit metadata after Beads data loss.\n\n"
        f"- Manifest source: {manifest_path}\n"
        f"- Repository: {repo}\n"
        f"- Commit: {commit}\n"
        f"- Commit date: {date}\n"
        f"- Commit subject: {subject}\n\n"
        "Original bead payload (status history, dependencies, description, labels, notes) "
        "was not recoverable from available Beads snapshots/backups."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay missing bead placeholders from commit manifest CSV."
    )
    parser.add_argument(
        "--csv",
        default="/tmp/beads-recovery-122264884/reconstructed-missing-beads-from-commits-2026-02-24_to_2026-02-28.csv",
        help="Path to manifest CSV (default: recovery output path).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without creating beads.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"error: CSV not found: {csv_path}", file=sys.stderr)
        return 2

    created = 0
    skipped = 0
    failed = 0

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"id", "repo", "commit", "date", "subject"}
        missing_columns = required - set(reader.fieldnames or [])
        if missing_columns:
            print(
                f"error: CSV missing columns: {', '.join(sorted(missing_columns))}",
                file=sys.stderr,
            )
            return 2

        for row in reader:
            bead_id = (row.get("id") or "").strip()
            repo = (row.get("repo") or "").strip()
            commit = (row.get("commit") or "").strip()
            date = (row.get("date") or "").strip()
            subject = (row.get("subject") or "").strip()

            if not bead_id:
                continue

            if bead_exists(bead_id):
                skipped += 1
                print(f"skip  {bead_id} (already exists)")
                continue

            title = normalize_title(subject if subject else f"Recovered placeholder for {bead_id}")
            description = build_description(str(csv_path), repo, commit, date, subject)

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
                description,
                "--labels",
                "recovered,placeholder",
            ]
            if commit:
                cmd.extend(["--external-ref", f"git:{commit}"])

            if args.dry_run:
                print(f"would {bead_id}: {' '.join(cmd)}")
                created += 1
                continue

            result = run_cmd(cmd, capture_output=True)
            if result.returncode != 0:
                failed += 1
                stderr = (result.stderr or "").strip()
                print(f"fail  {bead_id} :: {stderr}", file=sys.stderr)
                continue

            created += 1
            print(f"create {bead_id}")

    print(
        f"summary: created={created} skipped={skipped} failed={failed} "
        f"dry_run={str(args.dry_run).lower()}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
