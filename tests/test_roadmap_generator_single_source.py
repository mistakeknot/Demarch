"""The roadmap generator has exactly one implementation, and it is interpath's.

Two copies of sync-roadmap-json.sh existed for four months and diverged in four
ways at once: the plugin copy counted all 18 deferred beads as open work
(481 -> 499), hardcoded blocked_by to [] and dropped 127 dependency edges,
emitted a timestamp that is malformed on macOS because %:z is a GNU date
extension, and produced no backlog.md at all.

None of that was invisible for lack of tests. tests/test_render_backlog.py had
asserted every one of those behaviours since July. It just only ever ran the
monorepo copy, so the implementation that was wrong was the one no test could
reach. These tests exist to make a re-fork fail rather than drift.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHIM = ROOT / "scripts" / "sync-roadmap-json.sh"
GENERATOR = ROOT / "interverse" / "interpath" / "scripts" / "sync-roadmap-json.sh"
RENDERER = ROOT / "interverse" / "interpath" / "scripts" / "render_backlog.py"

# Two beads, chosen to exercise the divergences that actually happened:
# one deferred (silently counted as open by the old plugin copy) and one with a
# real dependency edge (dropped entirely by its hardcoded blocked_by: []).
FAKE_BD = """#!/usr/bin/env python3
import json
print(json.dumps([
  {'id': 'demo-open',     'title': '[demo] Open item',     'status': 'open',
   'priority': 2, 'labels': [], 'dependency_count': 0},
  {'id': 'demo-deferred', 'title': '[demo] Deferred item', 'status': 'deferred',
   'priority': 2, 'labels': [], 'dependency_count': 0},
  {'id': 'demo-blocked',  'title': '[demo] Blocked item',  'status': 'open',
   'priority': 2, 'labels': [], 'dependency_count': 1,
   'dependencies': [{'issue_id': 'demo-blocked',
                     'depends_on_id': 'demo-prereq', 'type': 'blocks'}]},
]))
"""


def _fake_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal project laid out like the monorepo, plus a stubbed bd."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(SHIM, repo / "scripts")

    plugin_scripts = repo / "interverse" / "interpath" / "scripts"
    plugin_scripts.mkdir(parents=True)
    shutil.copy2(GENERATOR, plugin_scripts)
    shutil.copy2(RENDERER, plugin_scripts)

    manifest = repo / "interverse" / "demo" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"name":"demo","version":"1.0.0"}\n', encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_bd = bin_dir / "bd"
    fake_bd.write_text(FAKE_BD, encoding="utf-8")
    fake_bd.chmod(0o755)

    (repo / "docs").mkdir()
    return repo, bin_dir


def _run(script: Path, repo: Path, bin_dir: Path, tag: str) -> dict:
    roadmap = repo / "docs" / f"{tag}-roadmap.json"
    backlog = repo / "docs" / f"{tag}-backlog.md"
    result = subprocess.run(
        ["bash", str(script), str(roadmap), str(backlog)],
        cwd=repo,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
             "ROADMAP_PROJECT": "demo"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return {
        "roadmap": json.loads(roadmap.read_text(encoding="utf-8")),
        "backlog": backlog.read_text(encoding="utf-8"),
    }


def test_the_shim_and_the_generator_produce_the_same_output(tmp_path: Path) -> None:
    """Run both paths and diff. Reading the two files is not evidence.

    This is the check that would have caught the fork: the two implementations
    were textually similar enough to look interchangeable and behaved
    differently on real tracker data.
    """
    repo, bin_dir = _fake_repo(tmp_path)

    via_shim = _run(repo / "scripts" / "sync-roadmap-json.sh", repo, bin_dir, "shim")
    direct = _run(
        repo / "interverse" / "interpath" / "scripts" / "sync-roadmap-json.sh",
        repo, bin_dir, "direct",
    )

    # generated_at is the one field that legitimately differs between runs.
    shim_roadmap = dict(via_shim["roadmap"])
    direct_roadmap = dict(direct["roadmap"])
    shim_roadmap.pop("generated_at", None)
    direct_roadmap.pop("generated_at", None)

    assert shim_roadmap == direct_roadmap
    assert via_shim["backlog"] == direct["backlog"]


def test_generated_at_is_parseable_on_this_platform(tmp_path: Path) -> None:
    """%:z is GNU-only; BSD date passes ':z' through literally.

    The result parses on Linux and not on macOS, so the roadmap reads as
    undated on one machine and fresh on the other, and downstream ranking
    silently withdraws it. Asserting the suffix is not enough — assert it
    actually parses.
    """
    from datetime import datetime

    repo, bin_dir = _fake_repo(tmp_path)
    out = _run(repo / "scripts" / "sync-roadmap-json.sh", repo, bin_dir, "stamp")

    stamp = out["roadmap"]["generated_at"]
    assert stamp.endswith("Z"), f"expected a UTC Z suffix, got {stamp!r}"
    datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def test_deferred_beads_are_not_counted_as_open_work(tmp_path: Path) -> None:
    """The 481 -> 499 inflation, as a unit."""
    repo, bin_dir = _fake_repo(tmp_path)
    out = _run(repo / "scripts" / "sync-roadmap-json.sh", repo, bin_dir, "deferred")

    items = [
        item
        for phase in ("now", "next", "later")
        for item in out["roadmap"]["roadmap"].get(phase, [])
    ]
    deferred = [i for i in items if i["id"] == "demo-deferred"]
    assert deferred, "the deferred bead vanished from the roadmap entirely"
    assert deferred[0]["status"] == "deferred"
    assert "_(deferred)_" in out["backlog"]


def test_dependency_edges_survive(tmp_path: Path) -> None:
    """blocked_by: [] dropped 127 edges on the real tracker."""
    repo, bin_dir = _fake_repo(tmp_path)
    out = _run(repo / "scripts" / "sync-roadmap-json.sh", repo, bin_dir, "edges")

    items = [
        item
        for phase in ("now", "next", "later")
        for item in out["roadmap"]["roadmap"].get(phase, [])
    ]
    blocked = next(i for i in items if i["id"] == "demo-blocked")
    assert blocked["status"] == "blocked"
    assert blocked["blocked_by"] == ["demo-prereq"]


def test_the_monorepo_keeps_no_second_copy_of_the_generator() -> None:
    """A re-fork must fail here rather than surface months later as drift.

    Checked against tracked files: interpath is a nested checkout, so its own
    files are not in this repo's index, and anything matching these names that
    IS tracked here is by definition a second copy.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    renderers = [p for p in tracked if Path(p).name == "render_backlog.py"]
    assert renderers == [], f"renderer duplicated in the monorepo: {renderers}"

    generators = [p for p in tracked if Path(p).name == "sync-roadmap-json.sh"]
    assert generators == ["scripts/sync-roadmap-json.sh"], (
        f"expected only the shim to be tracked here, found: {generators}"
    )


def test_the_shim_delegates_instead_of_reimplementing() -> None:
    """The shim may set defaults and exec. It may not generate."""
    body = SHIM.read_text(encoding="utf-8")
    code = [
        line for line in body.splitlines() if not line.lstrip().startswith("#")
    ]
    joined = "\n".join(code)

    assert "interverse/interpath/scripts/sync-roadmap-json.sh" in joined
    assert "exec bash" in joined

    # Generation markers. Their presence means logic came back into the shim.
    for marker in ("bd list", "collect_items_from_beads", "jq -s", "add_module"):
        assert marker not in joined, (
            f"{marker!r} is generation logic and belongs in interpath, not the shim"
        )
