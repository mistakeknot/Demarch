import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit-roadmap-beads.sh"


def run_audit(tmp_path: Path, roadmap_text: str) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    docs = repo / "docs"
    bin_dir = tmp_path / "bin"
    scripts.mkdir(parents=True)
    docs.mkdir()
    bin_dir.mkdir()
    shutil.copy2(SCRIPT, scripts)
    (docs / "sylveste-roadmap.md").write_text(roadmap_text, encoding="utf-8")

    fake_bd = bin_dir / "bd"
    fake_bd.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "args = sys.argv[1:]\n"
        "if args[0] == 'show':\n"
        "    issue_id = args[1]\n"
        "    known = {\n"
        "        'sylveste-good': 'open',\n"
        "        'Sylveste-Good2': 'open',\n"
        "        'sylveste-6h7x': 'closed',\n"
        "        'Sylveste-4b5.2': 'closed',\n"
        "        'Sylveste-4b5.11': 'closed',\n"
        "    }\n"
        "    match = next((key for key in known if key.casefold() == issue_id.casefold()), None)\n"
        "    if match is None:\n"
        "        raise SystemExit(1)\n"
        "    print(json.dumps([{'id': match, 'status': known[match]}]))\n"
        "elif args[0] == 'list':\n"
        "    print(json.dumps([\n"
        "        {'id': 'sylveste-good', 'status': 'open'},\n"
        "        {'id': 'Sylveste-Good2', 'status': 'open'},\n"
        "        {'id': 'sylveste-orphan', 'status': 'open'}\n"
        "    ]))\n"
        "else:\n"
        "    raise SystemExit(2)\n",
        encoding="utf-8",
    )
    fake_bd.chmod(0o755)

    return subprocess.run(
        ["bash", str(scripts / "audit-roadmap-beads.sh"), "--json"],
        cwd=repo,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        check=False,
    )


def test_audit_supports_current_ids_and_beads_array_json(tmp_path: Path) -> None:
    result = run_audit(
        tmp_path,
        "# Roadmap\n\n- **`sylveste-good`** first\n- `Sylveste-Good2` second\n",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["roadmap_ids_total"] == 2
    assert payload["active_with_bead"] == 2
    assert payload["missing_beads"] == []
    assert payload["orphaned_open_beads"] == 1


def test_audit_handles_roadmap_without_issue_ids(tmp_path: Path) -> None:
    result = run_audit(tmp_path, "# Roadmap\n\nNo issue references yet.\n")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["roadmap_ids_total"] == 0
    assert payload["coverage_pct"] == 100


def test_audit_handles_mixed_case_recently_completed_ids(tmp_path: Path) -> None:
    result = run_audit(
        tmp_path,
        (
            "# Roadmap\n\n"
            "- `sylveste-good` active\n"
            "- `Sylveste-Good2` active\n"
            "- **Recently completed:** `sylveste-6h7x`, "
            "`Sylveste-4b5.2`, and `Sylveste-4b5.11`\n"
        ),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["roadmap_ids_total"] == 5
    assert payload["roadmap_ids_active"] == 2
    assert payload["roadmap_ids_completed"] == 3
    assert payload["unclosed_completed"] == []
