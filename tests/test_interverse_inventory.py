from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import interverse_inventory as inventory


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_plugin(
    root: Path,
    name: str,
    manifest: dict[str, object],
    *,
    skill_names: list[str] | None = None,
    command_names: list[str] | None = None,
    agent_names: list[str] | None = None,
) -> Path:
    plugin_root = root / "interverse" / name
    write_json(
        plugin_root / ".claude-plugin" / "plugin.json",
        {"name": name, "version": "1.0.0", **manifest},
    )
    for skill_name in skill_names or []:
        skill_dir = plugin_root / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
    for command_name in command_names or []:
        command_path = plugin_root / "commands" / f"{command_name}.md"
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text(f"# {command_name}\n", encoding="utf-8")
    for agent_name in agent_names or []:
        agent_path = plugin_root / "agents" / f"{agent_name}.md"
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_path.write_text(f"# {agent_name}\n", encoding="utf-8")
    return plugin_root


def write_rig(root: Path, *sources: tuple[str, str]) -> Path:
    sections: dict[str, list[dict[str, str]]] = {
        "required": [],
        "recommended": [],
        "optional": [],
    }
    for tier, source in sources:
        sections[tier].append({"source": source, "description": f"{source} plugin"})
    path = root / "os" / "Clavain" / "agent-rig.json"
    write_json(path, {"plugins": sections})
    return path


def write_marketplace(root: Path, *names: str) -> Path:
    path = root / "core" / "marketplace" / ".claude-plugin" / "marketplace.json"
    write_json(
        path,
        {
            "name": "interagency-marketplace",
            "plugins": [
                {"name": name, "version": "1.0.0", "source": {"source": "url", "url": f"https://example.invalid/{name}.git"}}
                for name in names
            ],
        },
    )
    return path


def test_inventory_lists_plugins_component_counts_and_presence(tmp_path: Path) -> None:
    write_plugin(
        tmp_path,
        "alpha",
        {
            "skills": ["./skills/review"],
            "commands": ["./commands/run.md"],
            "agents": ["./agents/auditor.md"],
            "mcpServers": {"alpha": {"type": "stdio", "command": "./bin/alpha"}},
        },
        skill_names=["review"],
        command_names=["run"],
        agent_names=["auditor"],
    )
    rig_path = write_rig(tmp_path, ("recommended", "alpha@interagency-marketplace"))
    marketplace_path = write_marketplace(tmp_path, "alpha")

    ledger = inventory.build_inventory(tmp_path, rig_path=rig_path, marketplace_path=marketplace_path)

    assert ledger["summary"]["plugin_count"] == 1
    assert ledger["summary"]["fail_count"] == 0
    alpha = ledger["plugins"][0]
    assert alpha["name"] == "alpha"
    assert alpha["rig"]["tier"] == "recommended"
    assert alpha["marketplace"]["present"] is True
    assert alpha["surface_types"] == ["skills", "commands", "agents", "mcpServers"]
    assert alpha["components"]["declared"] == {
        "skills": 1,
        "commands": 1,
        "agents": 1,
        "hooks": 0,
        "mcpServers": 1,
        "lspServers": 0,
    }
    assert alpha["components"]["disk"]["skills"] == 1
    assert alpha["components"]["disk"]["commands"] == 1
    assert alpha["components"]["disk"]["agents"] == 1
    assert alpha["drift"]["status"] == "ok"


def test_inventory_flags_missing_declared_paths_and_orphaned_rig_as_high_drift(tmp_path: Path) -> None:
    write_plugin(
        tmp_path,
        "beta",
        {
            "skills": ["./skills/present"],
            "commands": ["./commands/missing.md"],
        },
        skill_names=["present"],
    )
    rig_path = write_rig(
        tmp_path,
        ("recommended", "beta@interagency-marketplace"),
        ("optional", "ghost@interagency-marketplace"),
    )
    marketplace_path = write_marketplace(tmp_path, "beta")

    ledger = inventory.build_inventory(tmp_path, rig_path=rig_path, marketplace_path=marketplace_path)

    beta = next(plugin for plugin in ledger["plugins"] if plugin["name"] == "beta")
    assert ledger["summary"]["fail_count"] == 2
    assert beta["drift"]["status"] == "fail"
    assert any("commands/missing.md" in item["path"] for item in beta["drift"]["high"])
    assert ledger["orphaned"]["rig"] == [
        {
            "name": "ghost",
            "source": "ghost@interagency-marketplace",
            "tier": "optional",
            "severity": "high",
            "message": "agent-rig.json references a first-party plugin that is missing from interverse/",
        }
    ]


def test_unmarketed_local_plugin_warns_without_failing_check(tmp_path: Path) -> None:
    write_plugin(tmp_path, "gamma", {}, skill_names=["local"])
    rig_path = write_rig(tmp_path)
    marketplace_path = write_marketplace(tmp_path)

    ledger = inventory.build_inventory(tmp_path, rig_path=rig_path, marketplace_path=marketplace_path)

    gamma = ledger["plugins"][0]
    assert ledger["summary"]["fail_count"] == 0
    assert gamma["drift"]["status"] == "warn"
    assert gamma["marketplace"]["present"] is False
    assert any(item["code"] == "plugin_not_in_marketplace" for item in gamma["drift"]["warnings"])


def test_cli_json_check_returns_nonzero_only_for_high_drift(tmp_path: Path, capsys) -> None:
    write_plugin(tmp_path, "beta", {"commands": ["./commands/missing.md"]})
    rig_path = write_rig(tmp_path, ("recommended", "beta@interagency-marketplace"))
    marketplace_path = write_marketplace(tmp_path, "beta")

    exit_code = inventory.main(
        [
            "--root",
            str(tmp_path),
            "--rig",
            str(rig_path),
            "--marketplace",
            str(marketplace_path),
            "--json",
            "--check",
        ]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["fail_count"] == 1
    assert payload["summary"]["high_drift_count"] == 1


def test_check_rig_drift_wrapper_uses_case_sensitive_repo_rig_path(tmp_path: Path) -> None:
    write_plugin(tmp_path, "alpha", {}, skill_names=["review"])
    rig_path = write_rig(tmp_path, ("recommended", "alpha@interagency-marketplace"))
    marketplace_path = write_marketplace(tmp_path, "alpha")

    env = os.environ.copy()
    env.update(
        {
            "SYLVESTE_ROOT": str(tmp_path),
            "INTERVERSE_INVENTORY_RIG": str(rig_path),
            "INTERVERSE_INVENTORY_MARKETPLACE": str(marketplace_path),
        }
    )

    result = subprocess.run(
        [str(ROOT / "scripts" / "check-rig-drift.sh"), "--json"],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["rig"]["path"].endswith("os/Clavain/agent-rig.json")
    assert payload["summary"]["plugin_count"] == 1


def test_publish_path_runs_inventory_gate_before_version_updates() -> None:
    script = (ROOT / "scripts" / "interbump.sh").read_text(encoding="utf-8")

    assert "Interverse inventory drift gate" in script
    assert "check-rig-drift.sh" in script
    assert script.index("Interverse inventory drift gate") < script.index('phase "update-files"')
