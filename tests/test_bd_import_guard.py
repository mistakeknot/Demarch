"""Guard the import direction of the beads JSONL <-> Dolt round trip.

The failure this prevents is silent and destructive: an import that upserts
every record reverts anything changed here since the incoming export was
written. A bead closed on this machine reopens, with no error and nothing in
the output to notice.

`scripts/beads_safe_import.py` used to enforce that, because `bd import` did
not. bd 1.1.2 does, so the script is gone and this file tests the property
where it now lives — in bd. That means these tests can fail on a bd upgrade
without a line of this repo changing, which is the point: the guarantee is
load-bearing and it is no longer ours.

Deliberately run against a real bd database rather than a stub. A stub would
assert what we believe bd does, which is exactly the belief under test — the
tombstone support this repo planned around turned out to have been removed
three releases earlier, and no amount of stubbing would have caught that.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("bd") is None, reason="bd not installed")


def bd(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bd", *args], cwd=repo, text=True, capture_output=True, check=False
    )


@pytest.fixture(scope="module")
def repo(tmp_path_factory) -> Path:
    """A throwaway bd database.

    Its own directory, never a copy of a real .beads — copying one carries
    metadata.json, which names a database, and the copy then writes to the
    original. That mistake once applied 30 schema migrations to production.
    """
    path = tmp_path_factory.mktemp("bdguard")
    subprocess.run(["git", "init", "-q", "."], cwd=path, check=True)
    result = bd(path, "init", "--prefix", "guardprobe")
    if result.returncode != 0:
        pytest.skip(f"bd init failed: {result.stderr.strip()[:200]}")
    return path


@pytest.fixture
def closed_bead(repo: Path) -> tuple[Path, str, dict]:
    """A bead that is CLOSED here — the local state a stale import would revert."""
    created = bd(repo, "create", "closed here", "-p", "3", "--json")
    issue_id = json.loads(created.stdout)["id"]
    bd(repo, "close", issue_id)
    exported = bd(repo, "export", "-o", "current.jsonl")
    assert exported.returncode == 0, exported.stderr
    rows = [
        json.loads(line)
        for line in (repo / "current.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    row = next(r for r in rows if r.get("id") == issue_id)
    assert row["status"] == "closed"
    return repo, issue_id, row


def status_of(repo: Path, issue_id: str) -> str:
    shown = bd(repo, "show", issue_id, "--json")
    assert shown.returncode == 0, shown.stderr
    payload = json.loads(shown.stdout[shown.stdout.find("[") :])
    return payload[0]["status"]


def reopened(row: dict, updated_at: str) -> dict:
    """The other machine's view: same bead, still open.

    closed_at has to go. bd rejects a non-closed issue carrying one, and the
    rejection aborts the whole file — which looks exactly like a stale row
    being skipped unless you read the error.
    """
    variant = dict(row, status="open", updated_at=updated_at)
    variant.pop("closed_at", None)
    return variant


def import_rows(repo: Path, name: str, rows: list[dict]) -> subprocess.CompletedProcess:
    path = repo / name
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return bd(repo, "import", str(path))


def test_stale_incoming_does_not_reopen_a_locally_closed_bead(closed_bead):
    """The regression that motivated all of this."""
    repo, issue_id, row = closed_bead
    bd(repo, "update", issue_id, "--status", "closed")

    import_rows(repo, "stale.jsonl", [reopened(row, "2020-01-01T00:00:00Z")])

    assert status_of(repo, issue_id) == "closed"


def test_equal_timestamps_keep_the_local_row(closed_bead):
    """updated_at has second granularity, so a tie is two distinct writes.

    Neither side can claim to be later, and reverting on a coin flip is the
    hazard. bd resolves it toward local.
    """
    repo, issue_id, row = closed_bead
    bd(repo, "update", issue_id, "--status", "closed")

    import_rows(repo, "tie.jsonl", [reopened(row, row["updated_at"])])

    assert status_of(repo, issue_id) == "closed"


def test_genuinely_newer_incoming_is_applied(closed_bead):
    """Without this the two tests above are vacuous.

    An import that refuses everything passes them both while breaking the sync
    entirely — which is the whole point of the mechanism, not a side effect.
    """
    repo, issue_id, row = closed_bead
    bd(repo, "update", issue_id, "--status", "closed")

    result = import_rows(repo, "newer.jsonl", [reopened(row, "2099-01-01T00:00:00Z")])

    assert result.returncode == 0, result.stderr
    assert status_of(repo, issue_id) == "open"


def test_absent_issues_are_created(closed_bead):
    """The other half of non-vacuity: unseen beads must actually arrive."""
    repo, _, row = closed_bead
    fresh_id = "guardprobe-fromelsewhere"
    incoming = reopened(dict(row, id=fresh_id, title="from another machine"), "2026-06-01T00:00:00Z")

    result = import_rows(repo, "absent.jsonl", [incoming])

    assert result.returncode == 0, result.stderr
    assert status_of(repo, fresh_id) == "open"
