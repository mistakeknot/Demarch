"""docs/roadmap.json is hand-regenerated; this is what stops it rotting silently.

The tracked roadmap is on no automatic path. The com.arouth.sylveste-roadmap
LaunchAgent writes ~/.cache/clavain/, so docs/roadmap.json only moves when a
human runs the generator. It went 26 days without one and drifted to 62 items
against a live 499 -- and because the fork that produced it also miscounted,
it was not merely stale but wrong: 0 deferred where there were 18, and 1
dependency edge where there were 127.

Age is read from the payload's own generated_at, never from file mtime. A
fresh clone rewrites every mtime, so an mtime check would pass in CI exactly
when it matters least.
"""

import datetime
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "roadmap.json"
BACKLOG = ROOT / "docs" / "backlog.md"

# Matches the stale_after_days the next-goal helper already applies to the
# cached copy, so the two artifacts do not disagree about what "fresh" means.
DEFAULT_MAX_AGE_DAYS = 7
MAX_AGE_DAYS = int(os.environ.get("ROADMAP_MAX_AGE_DAYS", DEFAULT_MAX_AGE_DAYS))

REGENERATE = "bash scripts/sync-roadmap-json.sh"


def _load() -> dict:
    assert ROADMAP.exists(), f"{ROADMAP} is missing. Regenerate: {REGENERATE}"
    return json.loads(ROADMAP.read_text(encoding="utf-8"))


def test_generated_at_is_parseable_utc() -> None:
    """A timestamp that does not parse is the fork's signature failure.

    The pre-defork generator used `date -u +%S%:z`. `%:z` is a GNU extension:
    it yields +00:00 under coreutils and passes through literally under BSD,
    so macOS emitted `...36:z`, which is not ISO 8601 at all. Asserting the
    string merely ends in "Z" would not have caught it either -- this parses.
    """
    raw = _load().get("generated_at")
    assert isinstance(raw, str) and raw, f"generated_at is missing. Regenerate: {REGENERATE}"
    try:
        stamp = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - the failure message is the point
        pytest.fail(f"generated_at {raw!r} is not ISO 8601 ({exc}). Regenerate: {REGENERATE}")
    assert stamp.tzinfo is not None, f"generated_at {raw!r} has no timezone. Regenerate: {REGENERATE}"


def test_roadmap_is_not_stale() -> None:
    raw = _load()["generated_at"]
    stamp = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    age = datetime.datetime.now(datetime.timezone.utc) - stamp
    assert age.days < MAX_AGE_DAYS, (
        f"docs/roadmap.json is {age.days}d old (limit {MAX_AGE_DAYS}d), generated {raw}.\n"
        f"Regenerate both artifacts from the repo root: {REGENERATE}\n"
        f"This must run where interverse/interpath is checked out -- the shim "
        f"delegates there and refuses from a bare worktree."
    )


def test_backlog_accompanies_roadmap() -> None:
    """The fork generated no backlog at all; a roadmap without one is the tell."""
    assert BACKLOG.exists(), f"{BACKLOG} is missing. Regenerate: {REGENERATE}"
    assert BACKLOG.stat().st_size > 0, f"{BACKLOG} is empty. Regenerate: {REGENERATE}"


def test_counts_are_self_consistent() -> None:
    """open_beads must exclude deferred, which is exactly what the fork got wrong.

    Staleness is not the only way this file goes bad. The forked generator
    produced a perfectly fresh roadmap that counted all 18 deferred beads as
    open work, so a pure age check would have called it healthy.
    """
    doc = _load()
    roadmap = doc.get("roadmap") or {}
    items = [
        entry
        for phase in ("now", "next", "later")
        for entry in (roadmap.get(phase) or [])
        if isinstance(entry, dict)
    ]
    assert items, f"roadmap has no items. Regenerate: {REGENERATE}"

    deferred = {e["id"] for e in items if e.get("status") == "deferred" and e.get("id")}
    live = {e["id"] for e in items if e.get("status") != "deferred" and e.get("id")}

    assert doc.get("open_beads") == len(live), (
        f"open_beads={doc.get('open_beads')} but {len(live)} non-deferred items "
        f"({len(deferred)} deferred). The pre-defork generator had no deferred "
        f"branch and counted them as open. Regenerate: {REGENERATE}"
    )
