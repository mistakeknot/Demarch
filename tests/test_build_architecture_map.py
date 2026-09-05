"""Tests for the architecture-map checker.

These guard the CHECKER, not the estate. The monorepo gitignores interverse/,
so a cloud checkout has no plugins to inspect; every test here builds a
synthetic estate under tmp_path. The vacuity tests are the important ones —
they prove the checker refuses to report on a tree it cannot see, which is the
failure mode that makes a green check meaningless.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build-architecture-map.py"
OK, DRIFT, CANNOT_ASSESS = 0, 1, 2


def run(root, *args):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def make_plugin(root, name, *, peers=None, refs=None, ref_count=3):
    """Create a plugin that references `refs` ref_count times each."""
    d = root / "interverse" / name
    (d / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (d / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": name, "version": "0.1.0", "description": f"{name} test plugin",
        "peerDependencies": peers or [],
    }))
    (d / "skills").mkdir(exist_ok=True)
    body = "\n".join(f"see {r}" for r in (refs or []) for _ in range(ref_count))
    (d / "skills" / "s.md").write_text(body or "no refs\n")
    return d


@pytest.fixture
def estate(tmp_path):
    """Two plugins; interflux references interspect 3x without declaring it."""
    make_plugin(tmp_path, "interflux", refs=["interspect"])
    make_plugin(tmp_path, "interspect")
    return tmp_path


def baseline(root, entries):
    (root / "ARCHITECTURE.baseline.json").write_text(json.dumps({
        "version": 1, "entries": entries}))


# --- vacuity: the checker must refuse to report on what it cannot see -------

def test_empty_root_cannot_assess(tmp_path):
    """No interverse/ at all. Exit 2, never 0 — nothing was compared."""
    code, out = run(tmp_path, "--check")
    assert code == CANNOT_ASSESS, out
    assert "inspected 0 plugins" in out
    assert "this is not a pass" in out


def test_require_plugins_floor_cannot_assess(estate):
    """A partial estate is not a small estate. Below the floor, refuse."""
    code, out = run(estate, "--check", "--require-plugins", "60")
    assert code == CANNOT_ASSESS, out
    assert "below the --require-plugins floor" in out


def test_floor_satisfied_reports_normally(estate):
    run(estate)  # generate
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "test", "owner": "test"}])
    code, out = run(estate, "--check", "--require-plugins", "2")
    assert code == OK, out


# --- drift ------------------------------------------------------------------

def test_generate_then_check_is_clean(estate):
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "test", "owner": "test"}])
    assert run(estate)[0] == OK
    assert (estate / "ARCHITECTURE.json").is_file()
    assert (estate / "ARCHITECTURE.md").is_file()
    code, out = run(estate, "--check", "--require-plugins", "2")
    assert code == OK, out


def test_missing_map_is_drift(estate):
    code, out = run(estate, "--check")
    assert code == DRIFT, out
    assert "ARCHITECTURE.json is missing" in out


def test_stale_map_is_drift(estate):
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "test", "owner": "test"}])
    run(estate)
    make_plugin(estate, "interlab")  # estate changed, map did not
    code, out = run(estate, "--check")
    assert code == DRIFT, out
    assert "is stale" in out


# --- baseline ---------------------------------------------------------------

def test_unbaselined_violation_is_drift(estate):
    run(estate)
    baseline(estate, [])
    code, out = run(estate, "--check")
    assert code == DRIFT, out
    assert "interflux references interspect" in out


def test_baselined_violation_is_silent(estate):
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "pre-existing", "owner": "someone"}])
    run(estate)
    code, out = run(estate, "--check")
    assert code == OK, out
    assert "all baselined" in out


def test_new_peer_on_baselined_plugin_is_not_covered(estate):
    """The waiver is per (plugin, peer) pair, not per plugin.

    interflux is already waived for interspect. Adding a second undeclared
    peer must NOT ride in under that waiver — otherwise a baselined plugin
    becomes a permanent blind spot that grows without anyone granting it.
    """
    make_plugin(estate, "interlab")
    make_plugin(estate, "interflux", refs=["interspect", "interlab"])
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "pre-existing", "owner": "someone"}])
    run(estate)
    code, out = run(estate, "--check")
    assert code == DRIFT, out
    assert "interflux references interlab" in out
    assert "interflux references interspect" not in out


def test_declaring_the_peer_clears_the_violation(estate):
    make_plugin(estate, "interflux", peers=["interspect"], refs=["interspect"])
    run(estate)
    baseline(estate, [])
    code, out = run(estate, "--check")
    assert code == OK, out


def test_stale_waiver_is_reported_but_not_drift(estate):
    """A fixed violation is the outcome the waiver was for, not a failure."""
    make_plugin(estate, "interflux", peers=["interspect"], refs=["interspect"])
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "pre-existing", "owner": "someone"}])
    run(estate)
    code, out = run(estate, "--check")
    assert code == OK, out
    assert "no longer needed" in out


# --- the baseline file is evidence, so it must be readable and signed -------

def test_unreadable_baseline_cannot_assess(estate):
    """A broken waiver file is not an empty one.

    Reading it as "nothing waived" would flag every pre-existing violation as
    new, and that noise is how a check gets ignored.
    """
    run(estate)
    (estate / "ARCHITECTURE.baseline.json").write_text("{not json")
    code, out = run(estate, "--check")
    assert code == CANNOT_ASSESS, out
    assert "baseline unreadable" in out


def test_unsigned_baseline_entry_cannot_assess(estate):
    run(estate)
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"]}])
    code, out = run(estate, "--check")
    assert code == CANNOT_ASSESS, out
    assert "lacks a reason or an owner" in out


def test_json_report_shape(estate):
    baseline(estate, [{"plugin": "interflux", "missing_peers": ["interspect"],
                       "reason": "test", "owner": "test"}])
    run(estate)
    code, out = run(estate, "--check", "--json")
    assert code == OK, out
    doc = json.loads(out)
    assert doc["status"] == "ok"
    assert doc["plugins_inspected"] == 2
    assert doc["new_violations"] == []


# --- the committed baseline is the real one, not a fixture ------------------

def test_committed_baseline_is_well_formed():
    """Every entry in the shipped waiver file carries a reason and an owner."""
    path = Path(__file__).resolve().parent.parent / "ARCHITECTURE.baseline.json"
    doc = json.loads(path.read_text())
    assert doc["entries"], "the shipped baseline is empty"
    for e in doc["entries"]:
        assert e["plugin"] and e["missing_peers"], e
        assert e["reason"] and e["owner"], f"unsigned waiver: {e['plugin']}"


def test_committed_baseline_covers_the_committed_map():
    """The waiver file and ARCHITECTURE.json agree on what exists today.

    If this fails, one of the two was regenerated without the other and the
    gate would fire on violations that were already known.
    """
    root = Path(__file__).resolve().parent.parent
    graph = json.loads((root / "ARCHITECTURE.json").read_text())
    doc = json.loads((root / "ARCHITECTURE.baseline.json").read_text())
    in_map = {(w["plugin"], p) for w in graph["warnings"] for p in w["missing_peers"]}
    waived = {(e["plugin"], p) for e in doc["entries"] for p in e["missing_peers"]}
    assert in_map == waived, (
        f"unwaived: {sorted(in_map - waived)}; stale: {sorted(waived - in_map)}")


def test_broken_baseline_does_not_block_regeneration(estate):
    """Regenerating is how you fix drift; a bad waiver file must not trap you.

    Generate mode writes the map and warns. Only --check, which issues a
    verdict, refuses.
    """
    (estate / "ARCHITECTURE.baseline.json").write_text("{not json")
    code, out = run(estate)
    assert code == OK, out
    assert (estate / "ARCHITECTURE.json").is_file()
    assert "warning" in out and "baseline unreadable" in out


def test_stale_artifacts_field_excludes_violations(estate):
    """The JSON report's stale_artifacts must not absorb violation messages."""
    run(estate)
    baseline(estate, [])
    code, out = run(estate, "--check", "--json")
    assert code == DRIFT, out
    doc = json.loads(out)
    assert doc["stale_artifacts"] == []
    assert doc["new_violations"] == [["interflux", "interspect"]]
