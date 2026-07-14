from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import interverse_agency as agency_cli


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def platform_key() -> str:
    return {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}.get(
        platform.system(), platform.system().lower()
    )


def write_agency(root: Path, name: str, supported_os: list[str]) -> Path:
    agency_root = root / "os" / name.title()
    write_json(agency_root / "schemas" / "agency-v1.json", {"type": "object"})
    write_json(
        agency_root / "agency.json",
        {
            "$schema": "./schemas/agency-v1.json",
            "schema_version": "interverse.agency/v1",
            "kind": "agency",
            "name": name,
            "display_name": name.title(),
            "description": "test agency",
            "version": "1.0.0",
            "layer": "L2",
            "class": "portfolio",
            "repository": f"https://example.invalid/{name}",
            "install": {
                "script": "scripts/install.sh",
                "check_args": ["--check"],
                "default_args": ["--no-enable"],
                "supported_os": supported_os,
            },
            "runtime": {
                "binary": name,
                "doctor_args": ["doctor", "--json"],
                "status_args": ["status", "--json"],
                "service_manager": "systemd-user",
                "service": f"{name}.service",
                "timer": f"{name}.timer",
            },
            "capabilities": ["portfolio.observe"],
            "authority": {
                "may": ["evidence.read"],
                "requires_approval": ["experiment.execute"],
                "never": ["git.push", "git.merge", "deployment.deploy", "release.publish"],
            },
            "contracts": [f"{name}.cycle/v1"],
        },
    )
    installer = agency_root / "scripts" / "install.sh"
    installer.parent.mkdir(parents=True, exist_ok=True)
    installer.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' \"$HOME\" > \"$AGENCY_TRACE_HOME\"\n"
        "printf '%s\\n' \"$@\" > \"$AGENCY_TRACE_ARGS\"\n"
        "printf 'delegated\\n'\n",
        encoding="utf-8",
    )
    return agency_root


def test_shared_installer_delegates_explicit_agency_with_temporary_home(tmp_path: Path) -> None:
    write_agency(tmp_path, "alpha", [platform_key()])
    home = tmp_path / "home"
    home.mkdir()
    trace_home = tmp_path / "trace-home"
    trace_args = tmp_path / "trace-args"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "SYLVESTE_ROOT": str(tmp_path),
            "AGENCY_TRACE_HOME": str(trace_home),
            "AGENCY_TRACE_ARGS": str(trace_args),
        }
    )

    result = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--agency=alpha"],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert trace_home.read_text(encoding="utf-8").strip() == str(home)
    assert trace_args.read_text(encoding="utf-8").splitlines() == ["--no-enable"]


def test_install_reports_unsupported_platform_clearly(tmp_path: Path, capsys) -> None:
    write_agency(tmp_path, "alpha", ["definitely-not-this-platform"])

    exit_code = agency_cli.main(["--root", str(tmp_path), "install", "alpha"])

    assert exit_code == 2
    stderr = capsys.readouterr().err
    assert f"unsupported on {platform_key()}" in stderr
    assert "definitely-not-this-platform" in stderr


def test_install_json_is_one_document(tmp_path: Path, monkeypatch, capsys) -> None:
    write_agency(tmp_path, "alpha", [platform_key()])
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AGENCY_TRACE_HOME", str(tmp_path / "trace-home"))
    monkeypatch.setenv("AGENCY_TRACE_ARGS", str(tmp_path / "trace-args"))

    exit_code = agency_cli.main(["--root", str(tmp_path), "--json", "install", "alpha"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["stdout"] == "delegated"


def test_doctor_reports_not_installed_in_clean_home(tmp_path: Path, monkeypatch, capsys) -> None:
    write_agency(tmp_path, "alpha", [platform_key()])
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AGENCY_TRACE_HOME", str(tmp_path / "trace-home"))
    monkeypatch.setenv("AGENCY_TRACE_ARGS", str(tmp_path / "trace-args"))

    exit_code = agency_cli.main(["--root", str(tmp_path), "--json", "doctor", "alpha"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "not_installed"
    assert payload["checks"]["manifest"] is True
    assert payload["checks"]["installer"] is True
    assert payload["checks"]["runtime"] is False


def test_doctor_runs_installed_runtime_doctor(tmp_path: Path, monkeypatch, capsys) -> None:
    write_agency(tmp_path, "alpha", [platform_key()])
    home = tmp_path / "home"
    binary = home / ".local" / "bin" / "alpha"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/usr/bin/env bash\nprintf '{\"status\":\"ok\"}\\n'\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AGENCY_TRACE_HOME", str(tmp_path / "trace-home"))
    monkeypatch.setenv("AGENCY_TRACE_ARGS", str(tmp_path / "trace-args"))

    exit_code = agency_cli.main(["--root", str(tmp_path), "--json", "doctor", "alpha"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["checks"] == {"manifest": True, "installer": True, "runtime": True}
