import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# The generator lives in interpath; scripts/sync-roadmap-json.sh is a shim.
# These tests point at the real implementation on purpose. They already
# asserted every behaviour the plugin copy lacked — deferred rendering, a Z
# suffix on generated_at, populated blocked_by, a backlog file existing at all
# — but they only ever ran against the monorepo fork, so the copy that was
# actually wrong was the one no test could see. Aiming them here is what makes
# them a drift guard rather than a description of one branch of a fork.
GENERATOR = ROOT / "interverse" / "interpath" / "scripts" / "sync-roadmap-json.sh"
SCRIPT = ROOT / "interverse" / "interpath" / "scripts" / "render_backlog.py"
SHIM = ROOT / "scripts" / "sync-roadmap-json.sh"


def run_renderer(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    source = tmp_path / "roadmap.json"
    output = tmp_path / "backlog.md"
    source.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(source), str(output)],
        capture_output=True,
        text=True,
        check=False,
    )


def roadmap_payload() -> dict:
    return {
        "project": "sylveste",
        "generated_at": "2026-07-10T12:34:56+00:00",
        "roadmap": {
            "now": [
                {
                    "module": "sylveste",
                    "id": "sylveste-p1",
                    "title": "Strategic gate",
                    "priority": "P1",
                    "status": "open",
                }
            ],
            "next": [
                {
                    "module": "intercore",
                    "id": "sylveste-b",
                    "title": "Blocked kernel work",
                    "priority": "P2",
                    "status": "blocked",
                },
                {
                    "module": "clavain",
                    "id": "Sylveste-A",
                    "title": "Active installer repair",
                    "priority": "P2",
                    "status": "in_progress",
                },
            ],
            "later": [
                {
                    "module": "interlab",
                    "id": "sylveste-c",
                    "title": "Deferred benchmark",
                    "priority": "P3",
                    "status": "deferred",
                },
                {
                    "module": "sylveste",
                    "id": "sylveste-d",
                    "title": "Someday cleanup",
                    "priority": "P4",
                    "status": "open",
                },
            ],
        },
    }


def test_renders_live_p2_through_p4_grouped_by_priority_and_module(tmp_path: Path) -> None:
    result = run_renderer(tmp_path, roadmap_payload())

    assert result.returncode == 0, result.stderr
    rendered = (tmp_path / "backlog.md").read_text(encoding="utf-8")
    assert "**Last synced:** 2026-07-10" in rendered
    assert "## P2 - Next" in rendered
    assert "### clavain" in rendered
    assert "- **Sylveste-A** Active installer repair _(in progress)_" in rendered
    assert "### intercore" in rendered
    assert "- **sylveste-b** Blocked kernel work _(blocked)_" in rendered
    assert "## P3 - Later" in rendered
    assert "- **sylveste-c** Deferred benchmark _(deferred)_" in rendered
    assert "## P4 - Someday" in rendered
    assert "- **sylveste-d** Someday cleanup" in rendered
    assert "sylveste-p1" not in rendered
    assert rendered.index("### clavain") < rendered.index("### intercore")
    assert all(line == line.rstrip() for line in rendered.splitlines())


def test_rejects_duplicate_issue_ids_across_phases(tmp_path: Path) -> None:
    payload = roadmap_payload()
    payload["roadmap"]["later"].append(
        {
            "module": "other",
            "id": "SYLVESTE-A",
            "title": "Duplicate",
            "priority": "P3",
            "status": "open",
        }
    )

    result = run_renderer(tmp_path, payload)

    assert result.returncode != 0
    assert "duplicate issue id: SYLVESTE-A" in result.stderr
    assert not (tmp_path / "backlog.md").exists()


def test_roadmap_sync_regenerates_backlog_with_machine_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SHIM, scripts)

    # The fake repo mirrors the real layout: shim in scripts/, generator and
    # renderer in interverse/interpath/scripts/. Exercising the shim end to end
    # is the point — it is the delegation, not either file alone, that broke
    # when the two copies drifted.
    plugin_scripts = repo / "interverse" / "interpath" / "scripts"
    plugin_scripts.mkdir(parents=True)
    shutil.copy2(GENERATOR, plugin_scripts)
    shutil.copy2(SCRIPT, plugin_scripts)

    manifest = repo / "interverse" / "demo" / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"name":"demo","version":"1.0.0"}\n', encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_bd = bin_dir / "bd"
    fake_bd.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps([{\n"
        "  'id': 'sylveste-sync',\n"
        "  'title': '[demo] Generated backlog item',\n"
        "  'status': 'open',\n"
        "  'priority': 2,\n"
        "  'labels': [],\n"
        "  'dependency_count': 0\n"
        "}, {\n"
        "  'id': 'sylveste-deferred',\n"
        "  'title': '[demo] Deferred backlog item',\n"
        "  'status': 'deferred',\n"
        "  'priority': 3,\n"
        "  'labels': [],\n"
        "  'dependency_count': 0\n"
        "}, {\n"
        "  'id': 'sylveste-blocked',\n"
        "  'title': '[demo] Blocked backlog item',\n"
        "  'status': 'open',\n"
        "  'priority': 2,\n"
        "  'labels': [],\n"
        "  'dependency_count': 1,\n"
        "  'dependencies': [{\n"
        "    'issue_id': 'sylveste-blocked',\n"
        "    'depends_on_id': 'sylveste-prereq',\n"
        "    'type': 'blocks'\n"
        "  }]\n"
        "}]))\n",
        encoding="utf-8",
    )
    fake_bd.chmod(0o755)

    roadmap = repo / "docs" / "roadmap.json"
    backlog = repo / "docs" / "backlog.md"
    roadmap.parent.mkdir(parents=True)
    result = subprocess.run(
        ["bash", str(scripts / "sync-roadmap-json.sh"), str(roadmap), str(backlog)],
        cwd=repo,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert roadmap.exists()
    assert backlog.exists()
    rendered = backlog.read_text(encoding="utf-8")
    assert "- **sylveste-sync** Generated backlog item" in rendered
    assert "- **sylveste-deferred** Deferred backlog item _(deferred)_" in rendered
    machine = json.loads(roadmap.read_text(encoding="utf-8"))
    assert machine["generated_at"].endswith("Z")
    blocked = next(item for item in machine["roadmap"]["next"] if item["id"] == "sylveste-blocked")
    assert blocked["status"] == "blocked"
    assert blocked["blocked_by"] == ["sylveste-prereq"]
