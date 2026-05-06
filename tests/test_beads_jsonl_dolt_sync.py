from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_beads_jsonl_dolt_sync as check


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def test_diff_issue_ids_reports_jsonl_ids_missing_from_dolt() -> None:
    diff = check.diff_issue_ids(
        jsonl_ids={"sylveste-s3z6.19.1", "sylveste-s3z6.19.2", "Sylveste-jm4"},
        dolt_ids={"sylveste-s3z6.19.1", "Sylveste-jm4"},
    )

    assert diff.missing_in_dolt == ["sylveste-s3z6.19.2"]
    assert diff.extra_in_dolt == []
    assert diff.ok is False


def test_cli_fails_when_tracked_jsonl_contains_ids_absent_from_dolt(tmp_path: Path, capsys) -> None:
    repo = tmp_path
    beads_dir = repo / ".beads"
    beads_dir.mkdir()
    write_jsonl(
        beads_dir / "issues.jsonl",
        [
            {"id": "sylveste-s3z6.19.1", "title": "present"},
            {"id": "sylveste-s3z6.19.2", "title": "jsonl only"},
            {"id": "Sylveste-jm4", "title": "present mixed case"},
        ],
    )
    fake_bd = tmp_path / "bd"
    fake_bd.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "assert sys.argv[1:3] == ['sql', 'select id from issues']\n"
        "print('id')\n"
        "print('---------------------')\n"
        "print('sylveste-s3z6.19.1')\n"
        "print('Sylveste-jm4')\n",
        encoding="utf-8",
    )
    fake_bd.chmod(0o755)
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{tmp_path}:{old_path}"
    try:
        exit_code = check.main(["--repo", str(repo)])
    finally:
        os.environ["PATH"] = old_path

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "missing_in_dolt=1" in out
    assert "sylveste-s3z6.19.2" in out


def test_pre_commit_hook_checks_staged_issues_jsonl_blob() -> None:
    hook = (ROOT / ".beads" / "hooks" / "pre-commit").read_text(encoding="utf-8")

    assert "git show :'.beads/issues.jsonl'" in hook
    assert "--issues-jsonl \"$_beads_jsonl_staged\"" in hook


def test_cli_passes_when_tracked_jsonl_and_dolt_issue_ids_match(tmp_path: Path, capsys) -> None:
    repo = tmp_path
    beads_dir = repo / ".beads"
    beads_dir.mkdir()
    write_jsonl(
        beads_dir / "issues.jsonl",
        [
            {"id": "sylveste-o2fr", "title": "gate"},
            {"id": "Sylveste-906", "title": "mixed case safety finding"},
        ],
    )
    fake_bd = tmp_path / "bd"
    fake_bd.write_text(
        "#!/usr/bin/env python3\n"
        "print('id')\n"
        "print('---------------------')\n"
        "print('sylveste-o2fr')\n"
        "print('Sylveste-906')\n",
        encoding="utf-8",
    )
    fake_bd.chmod(0o755)
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{tmp_path}:{old_path}"
    try:
        exit_code = check.main(["--repo", str(repo)])
    finally:
        os.environ["PATH"] = old_path

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "beads_jsonl_dolt_sync ok" in out
    assert "jsonl_count=2" in out
