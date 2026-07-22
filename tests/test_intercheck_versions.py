from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


SCRIPT = Path(__file__).parents[1] / "scripts/intercheck-versions.sh"


def _write_marketplace(path: Path, version: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "plugins": [
                    {"name": "fixture-plugin", "version": version},
                ]
            }
        )
        + "\n"
    )


def test_explicit_marketplace_json_overrides_legacy_sibling(tmp_path: Path) -> None:
    plugin = tmp_path / "projects/fixture-plugin"
    plugin_json = plugin / ".claude-plugin/plugin.json"
    plugin_json.parent.mkdir(parents=True)
    plugin_json.write_text(
        json.dumps({"name": "fixture-plugin", "version": "1.2.3"}) + "\n"
    )
    (plugin / "pyproject.toml").write_text(
        '[project]\nname = "fixture-plugin"\nversion = "1.2.3"\n'
    )
    subprocess.run(["git", "init", "-q"], cwd=plugin, check=True)

    stale = tmp_path / "projects/interagency-marketplace/.claude-plugin/marketplace.json"
    canonical = tmp_path / "registered/.claude-plugin/marketplace.json"
    _write_marketplace(stale, "1.0.0")
    _write_marketplace(canonical, "1.2.3")
    environment = dict(os.environ)
    environment["INTERCHECK_MARKETPLACE_JSON"] = str(canonical)

    result = subprocess.run(
        [str(SCRIPT), "--verbose"],
        cwd=plugin,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "versions in sync: 1.2.3" in result.stdout
