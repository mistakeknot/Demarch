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


def test_load_jsonl_issue_ids_accepts_exported_memory_records(tmp_path: Path) -> None:
    issues_jsonl = tmp_path / "issues.jsonl"
    write_jsonl(
        issues_jsonl,
        [
            {"id": "sylveste-o2fr", "title": "gate"},
            {"_type": "memory", "key": "routing-note", "value": "Prefer live evidence."},
        ],
    )

    assert check.load_jsonl_issue_ids(issues_jsonl) == {"sylveste-o2fr"}


def test_load_jsonl_issue_ids_rejects_malformed_memory_records(tmp_path: Path) -> None:
    issues_jsonl = tmp_path / "issues.jsonl"
    write_jsonl(issues_jsonl, [{"_type": "memory", "key": "routing-note"}])

    try:
        check.load_jsonl_issue_ids(issues_jsonl)
    except ValueError as exc:
        assert "invalid memory record" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("malformed memory record was accepted")


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
    # Both directions, not one. Without --strict-extra the guard passes a JSONL
    # that is behind Dolt, which is how the export sat 63 issues stale while the
    # hook reported success on every commit.
    assert "--strict-extra" in hook


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


# ─── content staleness (not just membership) ──────────────────────────


def test_normalize_strips_zone_before_touching_the_separator() -> None:
    """"UTC" contains a T.

    Normalizing the date/time separator first turns " +0000 UTC" into
    " +0000 U C", the suffix strip then misses, and every Dolt timestamp
    compares as older than every JSONL one — silently disabling the staleness
    detection this function exists to enable.
    """
    assert check.normalize_ts("2026-07-31T15:57:07Z") == check.normalize_ts(
        "2026-07-31 15:57:07 +0000 UTC"
    )
    assert check.normalize_ts("") == ""


def test_normalize_matches_the_safe_import_implementation() -> None:
    """Two scripts compare these timestamps; they must agree exactly.

    If they drift, the export trigger and the import filter disagree about
    which side is newer, and the disagreement is invisible until data moves the
    wrong way.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "beads_safe_import", ROOT / "scripts" / "beads_safe_import.py"
    )
    assert spec and spec.loader
    sfi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sfi)

    for sample in (
        "2026-07-31T15:57:07Z",
        "2026-07-31 15:57:07 +0000 UTC",
        "2026-08-01 02:14:40 UTC",
        "",
    ):
        assert check.normalize_ts(sample) == sfi.normalize_ts(sample), sample


def test_jsonl_max_updated_ignores_memory_rows(tmp_path: Path) -> None:
    p = tmp_path / "issues.jsonl"
    write_jsonl(
        p,
        [
            {"id": "a", "updated_at": "2026-07-01T00:00:00Z"},
            {"_type": "memory", "key": "k", "value": "v"},
            {"id": "b", "updated_at": "2026-07-05T00:00:00Z"},
        ],
    )
    assert check.load_jsonl_max_updated(p) == "2026-07-05 00:00:00"


def test_a_close_is_detectable_even_though_the_id_set_is_unchanged(tmp_path: Path) -> None:
    """The gap that motivated the high-water mark.

    Closing a bead changes its status, not the id set — so a membership-only
    check reports "in sync" while the committed export still says `open`.
    Observed in production before this was added.
    """
    before = tmp_path / "before.jsonl"
    write_jsonl(before, [{"id": "a", "status": "open", "updated_at": "2026-07-01T00:00:00Z"}])

    ids_before = check.load_jsonl_issue_ids(before)
    ids_after = {"a"}  # the close does not change membership
    diff = check.diff_issue_ids(jsonl_ids=ids_before, dolt_ids=ids_after)
    assert not diff.missing_in_dolt and not diff.extra_in_dolt, "membership is identical"

    # Only the timestamp reveals it.
    assert check.normalize_ts("2026-07-02 00:00:00 +0000 UTC") > check.load_jsonl_max_updated(before)
