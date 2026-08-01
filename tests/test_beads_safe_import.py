"""Guard the import direction of the beads JSONL <-> Dolt round trip.

The failure this prevents is silent and destructive: `bd import` upserts every
record, so importing an export written on another machine at an earlier moment
reverts anything changed here since. A bead closed on this machine reopens,
with no error and nothing in the output to notice.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "beads_safe_import",
    Path(__file__).resolve().parents[1] / "scripts" / "beads_safe_import.py",
)
assert _SPEC and _SPEC.loader
sfi = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sfi)


def rec(issue_id: str, updated: str, status: str = "open") -> dict:
    return {"id": issue_id, "updated_at": updated, "status": status}


# ─── timestamp normalization ──────────────────────────────────────────


def test_normalize_reconciles_dolt_and_jsonl_renderings():
    """Dolt and the JSONL print the same instant differently.

    Without this, every incoming record compares as newer than every local one
    (because "2026-07-31T..." > "2026-07-31 ..."), which would make the whole
    filter a no-op and restore the exact upsert hazard it exists to prevent.
    """
    assert sfi.normalize_ts("2026-07-31T15:57:07Z") == sfi.normalize_ts(
        "2026-07-31 15:57:07 +0000 UTC"
    )


def test_normalize_is_total_on_empty_input():
    assert sfi.normalize_ts("") == ""
    assert sfi.normalize_ts("   ") == ""


# ─── the hazard ───────────────────────────────────────────────────────


def test_stale_incoming_does_not_reopen_a_locally_closed_bead():
    """The regression that motivated this script."""
    records = [rec("Sylveste-a", "2026-07-29T10:00:00Z", status="open")]
    lines = ['{"id":"Sylveste-a","status":"open"}']
    local = {"Sylveste-a": "2026-07-31 12:00:00 +0000 UTC"}  # closed here, later

    apply_lines, new_ids, updated_ids, skipped = sfi.classify(records, lines, local)

    assert apply_lines == [], "a stale record must never be applied"
    assert not new_ids and not updated_ids
    assert [s[0] for s in skipped] == ["Sylveste-a"]


def test_absent_locally_is_imported():
    """The whole point: another machine's issues are invisible to bd until imported."""
    records = [rec("Sylveste-remote", "2026-07-29T10:00:00Z")]
    lines = ['{"id":"Sylveste-remote"}']
    apply_lines, new_ids, updated_ids, _ = sfi.classify(records, lines, local={})
    assert apply_lines == lines
    assert new_ids == ["Sylveste-remote"]
    assert updated_ids == []


def test_genuinely_newer_incoming_is_applied():
    records = [rec("Sylveste-b", "2026-08-01T09:00:00Z")]
    lines = ['{"id":"Sylveste-b"}']
    local = {"Sylveste-b": "2026-07-31 12:00:00 +0000 UTC"}
    apply_lines, new_ids, updated_ids, _ = sfi.classify(records, lines, local)
    assert apply_lines == lines
    assert updated_ids == ["Sylveste-b"] and new_ids == []


def test_identical_timestamps_are_skipped():
    # No basis to prefer either side, and nothing to gain by rewriting.
    records = [rec("Sylveste-c", "2026-07-31T12:00:00Z")]
    lines = ['{"id":"Sylveste-c"}']
    local = {"Sylveste-c": "2026-07-31 12:00:00 +0000 UTC"}
    apply_lines, _, _, skipped = sfi.classify(records, lines, local)
    assert apply_lines == []
    assert [s[0] for s in skipped] == ["Sylveste-c"]


def test_mixed_batch_applies_only_the_safe_records():
    """A real pull is a mix; the filter must be per-record, not all-or-nothing."""
    records = [
        rec("new-1", "2026-07-29T10:00:00Z"),
        rec("stale-1", "2026-07-29T10:00:00Z", status="open"),
        rec("fresh-1", "2026-08-02T10:00:00Z"),
    ]
    lines = ['{"id":"new-1"}', '{"id":"stale-1"}', '{"id":"fresh-1"}']
    local = {
        "stale-1": "2026-07-31 12:00:00 +0000 UTC",
        "fresh-1": "2026-07-31 12:00:00 +0000 UTC",
    }
    apply_lines, new_ids, updated_ids, skipped = sfi.classify(records, lines, local)
    assert new_ids == ["new-1"]
    assert updated_ids == ["fresh-1"]
    assert [s[0] for s in skipped] == ["stale-1"]
    assert '{"id":"stale-1"}' not in apply_lines


def test_raw_line_is_preserved_verbatim():
    """Records are re-emitted as the original text, not re-serialized.

    Re-serializing would silently drop any field this script does not model,
    turning an import into a lossy rewrite of another machine's data.
    """
    line = '{"id":"x","updated_at":"2026-08-01T00:00:00Z","unmodeled_field":{"a":1}}'
    apply_lines, _, _, _ = sfi.classify(
        [{"id": "x", "updated_at": "2026-08-01T00:00:00Z"}], [line], local={}
    )
    assert apply_lines == [line]


def test_memory_records_are_not_treated_as_issues(tmp_path: Path):
    p = tmp_path / "issues.jsonl"
    p.write_text(
        '{"_type":"memory","key":"k","value":"v"}\n{"id":"Sylveste-z","updated_at":"2026-08-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    records, lines = sfi.load_jsonl(p)
    assert [r["id"] for r in records] == ["Sylveste-z"]
    assert len(lines) == 1
