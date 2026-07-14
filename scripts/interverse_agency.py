#!/usr/bin/env python3
"""Install and diagnose first-class Interverse agencies from agency manifests."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scripts import interverse_inventory
except ImportError:
    import interverse_inventory  # type: ignore[no-redef]


class AgencyError(RuntimeError):
    pass


def load_agency(root: Path | str, name: str) -> tuple[Path, dict[str, Any]]:
    root_path = Path(root).resolve()
    ledger = interverse_inventory.build_inventory(root_path)
    matches = [entry for entry in ledger["agencies"] if entry["name"] == name]
    if not matches:
        available = ", ".join(entry["name"] for entry in ledger["agencies"]) or "none"
        raise AgencyError(f"unknown agency {name!r}; available: {available}")
    if len(matches) != 1:
        raise AgencyError(f"agency name {name!r} is declared more than once")
    entry = matches[0]
    if entry["drift"]["status"] == "fail":
        details = "; ".join(item["message"] for item in entry["drift"]["high"])
        raise AgencyError(f"agency {name!r} manifest is invalid: {details}")
    agency_root = (root_path / entry["path"]).resolve()
    try:
        agency_root.relative_to(root_path)
    except ValueError as exc:
        raise AgencyError(f"agency {name!r} path escapes the Sylveste root") from exc
    return agency_root, entry


def require_supported(entry: dict[str, Any]) -> None:
    if entry["platform"]["supported"]:
        return
    supported = ", ".join(entry["install"]["supported_os"])
    raise AgencyError(
        f"agency {entry['name']!r} is unsupported on {entry['platform']['current']}; supported platforms: {supported}"
    )


def manifest_command(agency_root: Path, script: str, args: list[str]) -> list[str]:
    script_path = (agency_root / script).resolve()
    try:
        script_path.relative_to(agency_root)
    except ValueError as exc:
        raise AgencyError("agency installer path escapes its repository") from exc
    if not script_path.is_file():
        raise AgencyError(f"agency installer is missing: {script_path}")
    return ["bash", str(script_path), *args]


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


def install_agency(
    root: Path | str,
    name: str,
    *,
    dry_run: bool = False,
    extra_args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    agency_root, entry = load_agency(root, name)
    require_supported(entry)
    args = list(entry["install"]["default_args"])
    args.extend(extra_args or [])
    if dry_run and "--dry-run" not in args:
        args.append("--dry-run")
    command = manifest_command(agency_root, entry["install"]["script"], args)
    result = run_command(command, cwd=agency_root, env=env)
    payload = {
        "agency": name,
        "status": "ok" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "command": command,
        "dry_run": dry_run,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    return payload, result


def resolve_runtime_binary(entry: dict[str, Any], env: dict[str, str]) -> Path | None:
    binary_name = entry["runtime"]["binary"]
    home_candidate = Path(env["HOME"]) / ".local" / "bin" / binary_name
    if home_candidate.is_file() and os.access(home_candidate, os.X_OK):
        return home_candidate
    path_candidate = shutil.which(binary_name, path=env.get("PATH"))
    return Path(path_candidate) if path_candidate else None


def doctor_agency(
    root: Path | str,
    name: str,
    *,
    env: dict[str, str] | None = None,
) -> tuple[dict[str, Any], int]:
    agency_root, entry = load_agency(root, name)
    active_env = dict(os.environ if env is None else env)
    active_env.setdefault("HOME", str(Path.home()))
    checks: dict[str, bool | None] = {"manifest": True, "installer": False, "runtime": False}
    payload: dict[str, Any] = {
        "agency": name,
        "platform": entry["platform"],
        "checks": checks,
    }

    check_command = manifest_command(agency_root, entry["install"]["script"], entry["install"]["check_args"])
    check_result = run_command(check_command, cwd=agency_root, env=active_env)
    checks["installer"] = check_result.returncode == 0
    payload["installer"] = {
        "command": check_command,
        "exit_code": check_result.returncode,
        "stdout": check_result.stdout.strip(),
        "stderr": check_result.stderr.strip(),
    }
    if check_result.returncode != 0:
        payload["status"] = "failed"
        return payload, 1

    if not entry["platform"]["supported"]:
        checks["runtime"] = None
        payload["status"] = "unsupported"
        return payload, 0

    binary = resolve_runtime_binary(entry, active_env)
    if binary is None:
        payload["status"] = "not_installed"
        payload["runtime"] = {"binary": entry["runtime"]["binary"], "found": False}
        return payload, 1

    runtime_command = [str(binary), *entry["runtime"]["doctor_args"]]
    runtime_result = run_command(runtime_command, cwd=agency_root, env=active_env)
    checks["runtime"] = runtime_result.returncode == 0
    payload["runtime"] = {
        "binary": str(binary),
        "found": True,
        "command": runtime_command,
        "exit_code": runtime_result.returncode,
        "stdout": runtime_result.stdout.strip(),
        "stderr": runtime_result.stderr.strip(),
    }
    payload["status"] = "ok" if runtime_result.returncode == 0 else "failed"
    return payload, 0 if runtime_result.returncode == 0 else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.environ.get("SYLVESTE_ROOT", "."))
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="explicitly install one agency")
    install.add_argument("name")
    install.add_argument("--dry-run", action="store_true")
    install.add_argument(
        "--arg",
        action="append",
        default=[],
        help="additional argument passed to the agency installer",
    )

    doctor = subparsers.add_parser("doctor", help="validate one agency and its installed runtime")
    doctor.add_argument("name")

    subparsers.add_parser("list", help="list discovered agency manifests")
    return parser.parse_args(argv)


def print_payload(payload: dict[str, Any], *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"{payload['agency']}: {payload['status']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    try:
        if args.command == "list":
            ledger = interverse_inventory.build_inventory(args.root)
            payload = {"agencies": ledger["agencies"], "count": len(ledger["agencies"])}
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                for entry in ledger["agencies"]:
                    support = (
                        "supported"
                        if entry["platform"]["supported"]
                        else f"unsupported on {entry['platform']['current']}"
                    )
                    print(f"{entry['name']}\t{entry['class']}\t{support}\t{entry['path']}")
            return 0
        if args.command == "install":
            payload, result = install_agency(
                args.root,
                args.name,
                dry_run=args.dry_run,
                extra_args=args.arg,
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                if result.stdout:
                    print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="", file=sys.stderr)
            return 0 if result.returncode == 0 else 1
        payload, exit_code = doctor_agency(args.root, args.name)
        print_payload(payload, json_mode=args.json)
        return exit_code
    except (AgencyError, OSError, json.JSONDecodeError) as exc:
        print(f"interverse_agency: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
