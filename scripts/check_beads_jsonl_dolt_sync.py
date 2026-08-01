#!/usr/bin/env python3
"""Fail when tracked Beads JSONL contains issues missing from live Dolt.

This is a repository-local guard for the failure mode where `.beads/issues.jsonl`
contains Bead IDs that the live `bd`/Dolt authority cannot see, making
priority-based automation silently incomplete.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IssueIdDiff:
    jsonl_count: int
    dolt_count: int
    missing_in_dolt: list[str]
    extra_in_dolt: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_in_dolt


def load_jsonl_issue_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - argparse-facing guard
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if row.get("_type") == "memory":
                memory_key = row.get("key")
                memory_value = row.get("value")
                if (
                    not isinstance(memory_key, str)
                    or not memory_key
                    or not isinstance(memory_value, str)
                ):
                    raise ValueError(f"{path}:{line_number}: invalid memory record")
                continue
            issue_id = row.get("id")
            if not isinstance(issue_id, str) or not issue_id:
                raise ValueError(f"{path}:{line_number}: missing string id")
            ids.add(issue_id)
    return ids


def normalize_ts(value: str) -> str:
    """Reduce Dolt's and the JSONL's timestamp renderings to one comparable form.

    Dolt prints `2026-07-31 15:57:07 +0000 UTC`; the JSONL carries
    `2026-07-31T15:57:07Z`.

    Strip the zone suffix BEFORE normalizing the date/time separator: "UTC"
    contains a T, so doing it the other way rewrites " +0000 UTC" into
    " +0000 U C" and the suffix stops matching — which makes every Dolt
    timestamp compare as older and hides exactly the staleness this detects.
    """
    if not value:
        return ""
    v = value.strip()
    for suffix in (" +0000 UTC", " UTC", "+00:00", "Z"):
        if v.endswith(suffix):
            v = v[: -len(suffix)]
            break
    return v.replace("T", " ").strip()


def load_jsonl_max_updated(path: Path) -> str:
    """Latest updated_at in the export.

    Issue IDs alone cannot detect a close: closing a bead changes its status,
    not the set of ids. Comparing high-water marks catches content changes that
    leave membership identical, which is the common case — most bead activity
    is closing something that already exists.
    """
    newest = ""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("_type") == "memory":
                continue
            ts = normalize_ts(row.get("updated_at") or "")
            if ts > newest:
                newest = ts
    return newest


def load_dolt_max_updated(repo: Path, bd_command: str = "bd") -> str:
    resolved = shutil.which(bd_command) if "/" not in bd_command else bd_command
    if resolved is None:
        return ""
    result = subprocess.run(
        [resolved, "sql", "select max(updated_at) from issues"],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        return ""
    newest = ""
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line or set(line) <= {"-", "+"} or line.startswith("("):
            continue
        if "max(" in line.lower():
            continue
        ts = normalize_ts(line.split("|")[0])
        if ts and ts[0].isdigit() and ts > newest:
            newest = ts
    return newest


def parse_bd_sql_issue_ids(output: str) -> set[str]:
    ids: set[str] = set()
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line == "id" or set(line) <= {"-"}:
            continue
        if line.startswith("(") and line.endswith("rows)"):
            continue
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not cells or cells[0] == "id":
                continue
            issue_id = cells[0]
        else:
            issue_id = line.split()[0]
        if issue_id:
            ids.add(issue_id)
    return ids


def load_dolt_issue_ids(repo: Path, bd_command: str = "bd") -> set[str]:
    resolved = shutil.which(bd_command) if "/" not in bd_command else bd_command
    if resolved is None:
        raise RuntimeError(f"bd command not found on PATH: {bd_command}")
    result = subprocess.run(
        [resolved, "sql", "select id from issues"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "bd sql failed")
    return parse_bd_sql_issue_ids(result.stdout)


def diff_issue_ids(jsonl_ids: set[str], dolt_ids: set[str]) -> IssueIdDiff:
    return IssueIdDiff(
        jsonl_count=len(jsonl_ids),
        dolt_count=len(dolt_ids),
        missing_in_dolt=sorted(jsonl_ids - dolt_ids),
        extra_in_dolt=sorted(dolt_ids - jsonl_ids),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate that tracked .beads/issues.jsonl issue IDs exist in live Dolt."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument(
        "--issues-jsonl",
        type=Path,
        default=None,
        help="path to issues.jsonl; default: <repo>/.beads/issues.jsonl",
    )
    parser.add_argument("--bd-command", default="bd", help="bd executable to run")
    parser.add_argument(
        "--strict-extra",
        action="store_true",
        help="also fail when Dolt has issue IDs absent from the tracked JSONL export",
    )
    parser.add_argument("--show", type=int, default=25, help="max mismatched IDs to print per class")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the diff as JSON so callers can branch on direction, not just exit code",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # Cloud-guard: this script asks Dolt for issue ids and compares to JSONL.
    # In cloud there is no Dolt, and we treat JSONL as the source of truth,
    # so the comparison is meaningless. Skip cleanly with exit 0.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from lib_cloud_guard import cloud_session, cloud_log_skip, workstation_log_missing_bd
    except ImportError:
        cloud_session = lambda: False  # type: ignore
        cloud_log_skip = lambda op="op": None  # type: ignore
        workstation_log_missing_bd = lambda op="op": None  # type: ignore
    if cloud_session():
        cloud_log_skip("check_beads_jsonl_dolt_sync")
        return 0
    if shutil.which("bd") is None:
        workstation_log_missing_bd("check_beads_jsonl_dolt_sync")
        return 0

    args = build_parser().parse_args(argv)
    repo = args.repo.resolve()
    issues_jsonl = args.issues_jsonl or (repo / ".beads" / "issues.jsonl")
    try:
        jsonl_ids = load_jsonl_issue_ids(issues_jsonl)
        dolt_ids = load_dolt_issue_ids(repo, args.bd_command)
    except Exception as exc:
        print(f"beads_jsonl_dolt_sync error: {exc}", file=sys.stderr)
        return 2

    diff = diff_issue_ids(jsonl_ids=jsonl_ids, dolt_ids=dolt_ids)

    # The two directions need different responses, and an exit code cannot carry
    # that. Dolt-ahead is fixed by exporting; JSONL-ahead must NEVER trigger an
    # export, because exporting would delete the issues the JSONL uniquely holds
    # — which is exactly how sylveste-j7vl came within one command of being lost.
    if args.json:
        # Membership alone misses the commonest change of all: closing a bead
        # alters its status, not the id set. Compare high-water marks too, or a
        # session that only closes issues exports nothing and the committed
        # JSONL keeps saying "open".
        jsonl_ts = load_jsonl_max_updated(issues_jsonl)
        dolt_ts = load_dolt_max_updated(repo, args.bd_command)
        content_stale = bool(dolt_ts and dolt_ts > jsonl_ts)
        print(json.dumps({
            "jsonl_count": diff.jsonl_count,
            "dolt_count": diff.dolt_count,
            "missing_in_dolt": diff.missing_in_dolt,
            "extra_in_dolt": diff.extra_in_dolt,
            "jsonl_max_updated": jsonl_ts,
            "dolt_max_updated": dolt_ts,
            "content_stale": content_stale,
            "safe_to_export": not diff.missing_in_dolt,
            "export_needed": bool(diff.extra_in_dolt) or content_stale,
        }))
        return 1 if (diff.missing_in_dolt or (args.strict_extra and diff.extra_in_dolt)) else 0

    print(
        "beads_jsonl_dolt_sync "
        f"jsonl_count={diff.jsonl_count} dolt_count={diff.dolt_count} "
        f"missing_in_dolt={len(diff.missing_in_dolt)} extra_in_dolt={len(diff.extra_in_dolt)}"
    )
    if diff.missing_in_dolt:
        print("JSONL issue IDs absent from live Dolt:")
        for issue_id in diff.missing_in_dolt[: args.show]:
            print(f"  - {issue_id}")
        if len(diff.missing_in_dolt) > args.show:
            print(f"  ... {len(diff.missing_in_dolt) - args.show} more")
    if diff.extra_in_dolt and args.strict_extra:
        print("Dolt issue IDs absent from tracked JSONL:")
        for issue_id in diff.extra_in_dolt[: args.show]:
            print(f"  - {issue_id}")
        if len(diff.extra_in_dolt) > args.show:
            print(f"  ... {len(diff.extra_in_dolt) - args.show} more")

    if diff.missing_in_dolt or (args.strict_extra and diff.extra_in_dolt):
        print("Run `bd export --output .beads/issues.jsonl` only after the Dolt authority contains the same issue IDs.")
        return 1
    print("beads_jsonl_dolt_sync ok")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
