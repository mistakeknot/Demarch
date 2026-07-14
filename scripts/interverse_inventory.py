#!/usr/bin/env python3
"""Generate an Interverse plugin inventory and classify drift.

The inventory is intentionally stdlib-only so it can run in doctor, publish,
and GitHub Actions contexts before project dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

COMPONENT_ORDER = ("skills", "commands", "agents", "hooks", "mcpServers", "lspServers")
DECLARED_PATH_KEYS = ("skills", "commands", "agents")
INTERAGENCY_MARKETPLACE = "interagency-marketplace"
AGENCY_SCHEMA_VERSION = "interverse.agency/v1"
PROFILE_TAXONOMY: dict[str, str] = {
    "default": "Small daily-use pack for fast Claude Code and Codex startup.",
    "core": "Workflow, coordination, test discipline, and local code-context essentials.",
    "review": "Multi-agent review, synthesis, integration tracing, and model-ranking tools.",
    "docs": "Repository documentation, product artifacts, doc freshness, and memory graduation.",
    "research": "Deep research, knowledge compounding, dialectic reasoning, and search tools.",
    "ops": "Runtime operator workflows, status surfaces, Slack, diagnostics, and experiment loops.",
    "observability": "Context pressure, feature metrics, project maps, profiling, and dashboards.",
    "plugin-dev": "Plugin, skill, MCP, and agent-native development workflows.",
    "design": "Distinctive interface design and UI/UX analysis workflows.",
    "mcp": "MCP-heavy services that should be opt-in for startup and context performance.",
    "incubating": "Experimental or narrow plugins that are not part of the default surface.",
    "internal": "Internal-only implementation support, hidden from ordinary user-facing packs.",
    "deprecated": "Retired or archived plugins, excluded from install packs.",
    "all": "Every non-internal, non-deprecated first-party plugin in this inventory.",
}
DEFAULT_PROFILE_PLUGINS = {
    "clavain",
    "intercheck",
    "interdev",
    "interdoc",
    "interlock",
    "internext",
    "interpeer",
    "interphase",
    "intertest",
    "tldr-swinton",
    "tool-time",
}
PROFILE_NAME_OVERRIDES = {
    "clavain": "core",
    "intercheck": "core",
    "interdev": "core",
    "interdoc": "core",
    "interlock": "core",
    "internext": "core",
    "interpeer": "core",
    "interphase": "core",
    "intertest": "core",
    "tldr-swinton": "core",
    "tool-time": "core",
    "interflux": "review",
    "interrank": "review",
    "intersynth": "review",
    "intertrace": "review",
    "intermem": "docs",
    "interpath": "docs",
    "interscribe": "docs",
    "intertree": "docs",
    "interwatch": "docs",
    "interdeep": "research",
    "interknow": "research",
    "interlearn": "research",
    "intermonk": "research",
    "intersearch": "research",
    "interhelm": "ops",
    "interlab": "ops",
    "interline": "ops",
    "intermux": "ops",
    "interslack": "ops",
    "interpulse": "observability",
    "interspect": "observability",
    "interstat": "observability",
    "intertrack": "observability",
    "interchart": "observability",
    "intercraft": "plugin-dev",
    "interplug": "plugin-dev",
    "interpub": "plugin-dev",
    "interskill": "plugin-dev",
    "interform": "design",
    "intersight": "design",
    "intercache": "mcp",
    "interject": "mcp",
    "interlens": "mcp",
    "tuivision": "mcp",
}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def split_source(source: str) -> tuple[str, str]:
    if "@" not in source:
        return source, ""
    name, marketplace = source.split("@", 1)
    return name, marketplace


def default_rig_path(root: Path) -> Path:
    candidates = (
        root / "os" / "Clavain" / "agent-rig.json",
        root / "os" / "clavain" / "agent-rig.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def default_marketplace_path(root: Path) -> Path:
    repo_local = root / "core" / "marketplace" / ".claude-plugin" / "marketplace.json"
    if repo_local.exists():
        return repo_local
    return Path.home() / ".claude" / "plugins" / "marketplaces" / INTERAGENCY_MARKETPLACE / ".claude-plugin" / "marketplace.json"


def discover_plugin_roots(root: Path) -> list[Path]:
    roots: list[Path] = []
    interverse = root / "interverse"
    if interverse.is_dir():
        for manifest in sorted(interverse.glob("*/.claude-plugin/plugin.json")):
            roots.append(manifest.parents[1])

    clavain = root / "os" / "Clavain" / ".claude-plugin" / "plugin.json"
    if clavain.exists():
        roots.append(clavain.parents[1])

    return roots


def discover_agency_roots(root: Path) -> list[Path]:
    agencies = root / "os"
    if not agencies.is_dir():
        return []
    return [manifest.parent for manifest in sorted(agencies.glob("*/agency.json"))]


def current_platform() -> str:
    return {
        "Darwin": "darwin",
        "Linux": "linux",
        "Windows": "windows",
    }.get(platform.system(), platform.system().lower())


def rig_source(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return str(payload.get("source", ""))
    return ""


def load_rig_entries(rig_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    if not rig_path.exists():
        return {}, [
            {
                "code": "missing_rig",
                "severity": "high",
                "path": rig_path.as_posix(),
                "message": "agent-rig.json is missing",
            }
        ]

    data = read_json(rig_path)
    plugins = data.get("plugins", {}) if isinstance(data, dict) else {}
    entries: dict[str, dict[str, Any]] = {}

    def add_entry(tier: str, payload: Any, *, profile: str | None = None) -> None:
        source = rig_source(payload)
        name, marketplace = split_source(source)
        if not name or marketplace != INTERAGENCY_MARKETPLACE:
            return
        entry = entries.setdefault(
            name,
            {
                "name": name,
                "source": source,
                "tier": tier,
                "description": str(payload.get("description", "")) if isinstance(payload, dict) else "",
                "profiles": [],
            },
        )
        if profile and profile not in entry["profiles"]:
            entry["profiles"].append(profile)

    if isinstance(plugins, dict):
        core = plugins.get("core")
        if isinstance(core, dict):
            add_entry("core", core)
        for tier, value in plugins.items():
            if isinstance(value, list):
                for payload in value:
                    if isinstance(payload, (dict, str)):
                        add_entry(str(tier), payload)
        profiles = plugins.get("profiles")
        if isinstance(profiles, dict):
            for profile_name, value in profiles.items():
                if not isinstance(value, list):
                    continue
                for payload in value:
                    add_entry("profile", payload, profile=str(profile_name))
        for entry in entries.values():
            entry["profiles"] = sorted(entry.get("profiles", []))

    return entries, []


def load_marketplace_entries(marketplace_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    if not marketplace_path.exists():
        return {}, [
            {
                "code": "missing_marketplace",
                "severity": "warning",
                "path": marketplace_path.as_posix(),
                "message": "marketplace.json is missing; marketplace presence could not be checked",
            }
        ]

    data = read_json(marketplace_path)
    entries: dict[str, dict[str, Any]] = {}
    for payload in data.get("plugins", []) if isinstance(data, dict) else []:
        if not isinstance(payload, dict):
            continue
        name = payload.get("name")
        if isinstance(name, str) and name:
            entries[name] = payload
    return entries, []


def list_field(manifest: dict[str, Any], key: str, high: list[dict[str, str]]) -> list[str]:
    value = manifest.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        high.append(
            {
                "code": f"invalid_{key}_type",
                "severity": "high",
                "path": f".claude-plugin/plugin.json:{key}",
                "message": f"plugin.json field '{key}' must be an array of paths",
            }
        )
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            result.append(item)
        else:
            high.append(
                {
                    "code": f"invalid_{key}_entry",
                    "severity": "high",
                    "path": f".claude-plugin/plugin.json:{key}",
                    "message": f"plugin.json field '{key}' contains a non-string path",
                }
            )
    return result


def declared_rel(entry: str, plugin_root: Path) -> tuple[str, Path, str | None]:
    if os.path.isabs(entry):
        return entry, Path(entry), "declared paths must be relative to the plugin root"
    stripped = entry[2:] if entry.startswith("./") else entry
    resolved = (plugin_root / stripped).resolve()
    try:
        resolved.relative_to(plugin_root.resolve())
    except ValueError:
        return stripped, resolved, "declared path escapes the plugin root"
    return stripped, resolved, None


def high_path_issue(code: str, component: str, entry: str, plugin_root: Path, message: str) -> dict[str, str]:
    stripped, resolved, path_error = declared_rel(entry, plugin_root)
    return {
        "code": code,
        "severity": "high",
        "component": component,
        "path": stripped,
        "absolute_path": resolved.as_posix(),
        "message": path_error or message,
    }


def validate_declared_paths(plugin_root: Path, manifest: dict[str, Any]) -> tuple[dict[str, int], list[dict[str, str]]]:
    declared_counts = {key: 0 for key in COMPONENT_ORDER}
    high: list[dict[str, str]] = []

    for key in DECLARED_PATH_KEYS:
        entries = list_field(manifest, key, high)
        declared_counts[key] = len(entries)
        for entry in entries:
            stripped, resolved, path_error = declared_rel(entry, plugin_root)
            if path_error:
                high.append(high_path_issue(f"{key}_path_escapes_root", key, entry, plugin_root, path_error))
                continue
            if key == "skills":
                if not resolved.exists():
                    high.append(high_path_issue("missing_declared_path", key, entry, plugin_root, f"declared {key} path does not exist"))
                elif not resolved.is_dir():
                    high.append(high_path_issue("invalid_declared_path_type", key, entry, plugin_root, "declared skill path must be a directory"))
            else:
                if not resolved.exists():
                    high.append(high_path_issue("missing_declared_path", key, entry, plugin_root, f"declared {key} path does not exist"))
                elif not resolved.is_file():
                    high.append(high_path_issue("invalid_declared_path_type", key, entry, plugin_root, f"declared {key} path must be a file"))

    hooks = manifest.get("hooks")
    if isinstance(hooks, str):
        declared_counts["hooks"] = 1
        stripped, resolved, path_error = declared_rel(hooks, plugin_root)
        if path_error:
            high.append(high_path_issue("hooks_path_escapes_root", "hooks", hooks, plugin_root, path_error))
        elif not resolved.is_file():
            high.append(high_path_issue("missing_declared_path", "hooks", hooks, plugin_root, "declared hooks path does not exist"))
        elif stripped == "hooks/hooks.json":
            high.append(
                {
                    "code": "redundant_standard_hooks_declaration",
                    "severity": "high",
                    "component": "hooks",
                    "path": stripped,
                    "absolute_path": resolved.as_posix(),
                    "message": "hooks/hooks.json is auto-loaded and should not be declared in plugin.json",
                }
            )
    elif isinstance(hooks, list):
        declared_counts["hooks"] = len(hooks)
        for entry in hooks:
            if not isinstance(entry, str):
                high.append(
                    {
                        "code": "invalid_hooks_entry",
                        "severity": "high",
                        "component": "hooks",
                        "path": ".claude-plugin/plugin.json:hooks",
                        "message": "hooks entries must be path strings",
                    }
                )
                continue
            stripped, resolved, path_error = declared_rel(entry, plugin_root)
            if path_error:
                high.append(high_path_issue("hooks_path_escapes_root", "hooks", entry, plugin_root, path_error))
            elif not resolved.is_file():
                high.append(high_path_issue("missing_declared_path", "hooks", entry, plugin_root, "declared hooks path does not exist"))
    elif hooks is not None:
        high.append(
            {
                "code": "invalid_hooks_type",
                "severity": "high",
                "component": "hooks",
                "path": ".claude-plugin/plugin.json:hooks",
                "message": "plugin.json field 'hooks' must be a path string or array of paths",
            }
        )

    for key in ("mcpServers", "lspServers"):
        value = manifest.get(key)
        if value is None:
            declared_counts[key] = 0
        elif isinstance(value, dict):
            declared_counts[key] = len(value)
        else:
            high.append(
                {
                    "code": f"invalid_{key}_type",
                    "severity": "high",
                    "component": key,
                    "path": f".claude-plugin/plugin.json:{key}",
                    "message": f"plugin.json field '{key}' must be an object keyed by server name",
                }
            )

    return declared_counts, high


def disk_components(plugin_root: Path) -> tuple[dict[str, int], dict[str, list[str]]]:
    paths = {key: [] for key in COMPONENT_ORDER}

    skills_dir = plugin_root / "skills"
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            paths["skills"].append(relpath(skill_md.parent, plugin_root))
        for flat_skill in sorted(skills_dir.glob("*.md")):
            paths["skills"].append(relpath(flat_skill, plugin_root))

    commands_dir = plugin_root / "commands"
    if commands_dir.is_dir():
        for command in sorted(commands_dir.rglob("*.md")):
            paths["commands"].append(relpath(command, plugin_root))

    agents_dir = plugin_root / "agents"
    if agents_dir.is_dir():
        for agent in sorted(agents_dir.rglob("*.md")):
            paths["agents"].append(relpath(agent, plugin_root))

    for hook_path in (plugin_root / "hooks" / "hooks.json", plugin_root / ".claude-plugin" / "hooks" / "hooks.json"):
        if hook_path.is_file():
            paths["hooks"].append(relpath(hook_path, plugin_root))

    return {key: len(paths[key]) for key in COMPONENT_ORDER}, paths


def is_declared(rel: str, declarations: list[str], plugin_root: Path) -> bool:
    for entry in declarations:
        stripped, resolved, path_error = declared_rel(entry, plugin_root)
        if path_error:
            continue
        if rel == stripped:
            return True
        if resolved.is_dir() and rel.startswith(stripped.rstrip("/") + "/"):
            return True
    return False


def undeclared_disk_warnings(plugin_root: Path, manifest: dict[str, Any], disk_paths: dict[str, list[str]]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for key in DECLARED_PATH_KEYS:
        if key not in manifest:
            continue
        declarations = list_field(manifest, key, [])
        for rel in disk_paths[key]:
            if not is_declared(rel, declarations, plugin_root):
                warnings.append(
                    {
                        "code": "undeclared_disk_component",
                        "severity": "warning",
                        "component": key,
                        "path": rel,
                        "message": f"{key} component exists on disk but is not declared in plugin.json",
                    }
                )

    if "hooks" not in manifest and disk_paths["hooks"]:
        for rel in disk_paths["hooks"]:
            warnings.append(
                {
                    "code": "undeclared_hooks",
                    "severity": "warning",
                    "component": "hooks",
                    "path": rel,
                    "message": "hooks file exists on disk but is not declared in plugin.json; standard hooks may be auto-loaded",
                }
            )
    return warnings


def plugin_surface_types(declared_counts: dict[str, int], disk_counts: dict[str, int]) -> list[str]:
    return [key for key in COMPONENT_ORDER if declared_counts.get(key, 0) > 0 or disk_counts.get(key, 0) > 0]


def text_blob(name: str, manifest: dict[str, Any], rig_entry: dict[str, Any] | None) -> str:
    values: list[str] = [name, str(manifest.get("description", ""))]
    keywords = manifest.get("keywords")
    if isinstance(keywords, list):
        values.extend(str(item) for item in keywords)
    if rig_entry:
        values.append(str(rig_entry.get("description", "")))
    return " ".join(values).lower()


def infer_primary_profile(
    name: str,
    manifest: dict[str, Any],
    surface_types: list[str],
    rig_entry: dict[str, Any] | None,
    plugin_root: Path,
) -> str:
    blob = text_blob(name, manifest, rig_entry)
    if (plugin_root / "ARCHIVED.md").exists() or any(term in blob for term in ("deprecated", "archived", "retired")):
        return "deprecated"
    if any(term in blob for term in ("internal-only", "internal only", "private implementation")):
        return "internal"
    if name in PROFILE_NAME_OVERRIDES:
        return PROFILE_NAME_OVERRIDES[name]
    if surface_types == ["mcpServers"] or ("mcpServers" in surface_types and not set(surface_types) & {"skills", "commands", "agents"}):
        return "mcp"

    keyword_profiles = (
        ("review", ("review", "synthesis", "verdict", "trace", "benchmark", "rank")),
        ("docs", ("document", "documentation", "artifact", "memory", "handoff", "watch")),
        ("research", ("research", "knowledge", "search", "dialectic", "learn")),
        ("ops", ("statusline", "slack", "diagnostic", "deploy", "runtime", "operator", "tmux")),
        ("observability", ("metric", "pressure", "profile", "dashboard", "telemetry", "map")),
        ("plugin-dev", ("plugin", "skill", "mcp cli", "agent-native", "publishing")),
        ("design", ("design", "ui", "ux", "interface", "visual")),
    )
    for profile, terms in keyword_profiles:
        if any(term in blob for term in terms):
            return profile
    return "incubating"


def plugin_profile(
    name: str,
    manifest: dict[str, Any],
    surface_types: list[str],
    rig_entry: dict[str, Any] | None,
    plugin_root: Path,
) -> dict[str, Any]:
    primary = infer_primary_profile(name, manifest, surface_types, rig_entry, plugin_root)
    packs = set(rig_entry.get("profiles", [])) if rig_entry else set()
    if primary not in {"internal", "deprecated"}:
        packs.add(primary)
    if name in DEFAULT_PROFILE_PLUGINS and primary not in {"internal", "deprecated"}:
        packs.add("default")
    packs.discard("all")

    if primary == "deprecated":
        visibility = "deprecated"
    elif primary == "internal":
        visibility = "internal"
    elif "default" in packs:
        visibility = "default"
    else:
        visibility = "optional"

    pack_order = ["core", "default", "review", "docs", "research", "ops", "observability", "plugin-dev", "design", "mcp", "incubating"]
    return {
        "primary": primary,
        "visibility": visibility,
        "packs": [pack for pack in pack_order if pack in packs] + sorted(packs - set(pack_order)),
    }


def analyze_plugin(
    root: Path,
    plugin_root: Path,
    rig_entries: dict[str, dict[str, Any]],
    marketplace_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    high: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    try:
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError("plugin.json top-level value is not an object")
    except Exception as exc:  # noqa: BLE001 - doctor output should report any parse failure
        name = plugin_root.name
        high.append(
            {
                "code": "invalid_manifest",
                "severity": "high",
                "path": relpath(manifest_path, root),
                "message": f"plugin.json could not be parsed: {exc}",
            }
        )
        manifest = {}
    else:
        name = str(manifest.get("name") or plugin_root.name)
        if not manifest.get("name"):
            high.append(
                {
                    "code": "missing_manifest_name",
                    "severity": "high",
                    "path": relpath(manifest_path, root),
                    "message": "plugin.json is missing required field 'name'",
                }
            )
        elif name != plugin_root.name:
            warnings.append(
                {
                    "code": "manifest_name_path_mismatch",
                    "severity": "warning",
                    "path": relpath(manifest_path, root),
                    "message": f"manifest name '{name}' differs from directory '{plugin_root.name}'",
                }
            )

    declared_counts, path_high = validate_declared_paths(plugin_root, manifest)
    high.extend(path_high)
    disk_counts, disk_paths = disk_components(plugin_root)
    warnings.extend(undeclared_disk_warnings(plugin_root, manifest, disk_paths))

    marketplace_entry = marketplace_entries.get(name)
    rig_entry = rig_entries.get(name)

    if marketplace_entry is None:
        warnings.append(
            {
                "code": "plugin_not_in_marketplace",
                "severity": "warning",
                "path": "core/marketplace/.claude-plugin/marketplace.json",
                "message": "local plugin is not registered in the Interagency marketplace",
            }
        )
    elif manifest.get("version") and marketplace_entry.get("version") and manifest["version"] != marketplace_entry["version"]:
        warnings.append(
            {
                "code": "marketplace_version_mismatch",
                "severity": "warning",
                "path": "core/marketplace/.claude-plugin/marketplace.json",
                "message": f"plugin.json version {manifest['version']} differs from marketplace version {marketplace_entry['version']}",
            }
        )

    if marketplace_entry is not None and rig_entry is None:
        warnings.append(
            {
                "code": "marketplace_plugin_not_in_rig",
                "severity": "warning",
                "path": "os/Clavain/agent-rig.json",
                "message": "marketplace plugin is not listed in Clavain agent-rig.json",
            }
        )

    surface_types = plugin_surface_types(declared_counts, disk_counts)
    profile = plugin_profile(name, manifest, surface_types, rig_entry, plugin_root)
    status = "fail" if high else "warn" if warnings else "ok"
    return {
        "name": name,
        "path": relpath(plugin_root, root),
        "manifest_path": relpath(manifest_path, root),
        "version": manifest.get("version", ""),
        "description": manifest.get("description", ""),
        "rig": {
            "present": rig_entry is not None,
            "tier": rig_entry.get("tier") if rig_entry else None,
            "source": rig_entry.get("source") if rig_entry else None,
        },
        "marketplace": {
            "present": marketplace_entry is not None,
            "version": marketplace_entry.get("version") if marketplace_entry else None,
        },
        "profile": profile,
        "surface_types": surface_types,
        "components": {
            "declared": declared_counts,
            "disk": disk_counts,
        },
        "component_paths": disk_paths,
        "drift": {
            "status": status,
            "high": high,
            "warnings": warnings,
        },
    }


def agency_string_list(
    value: Any,
    *,
    field: str,
    high: list[dict[str, str]],
    required: bool = True,
) -> list[str]:
    if not isinstance(value, list) or (required and not value):
        high.append(
            {
                "code": "invalid_agency_manifest_field",
                "severity": "high",
                "path": f"agency.json:{field}",
                "message": f"agency manifest field '{field}' must be a non-empty array of strings",
            }
        )
        return []
    if not all(isinstance(item, str) and item for item in value):
        high.append(
            {
                "code": "invalid_agency_manifest_field",
                "severity": "high",
                "path": f"agency.json:{field}",
                "message": f"agency manifest field '{field}' must contain only non-empty strings",
            }
        )
        return []
    return list(value)


def agency_required_string(manifest: dict[str, Any], key: str, high: list[dict[str, str]]) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        high.append(
            {
                "code": "invalid_agency_manifest_field",
                "severity": "high",
                "path": f"agency.json:{key}",
                "message": f"agency manifest field '{key}' must be a non-empty string",
            }
        )
        return ""
    return value


def analyze_agency(root: Path, agency_root: Path) -> dict[str, Any]:
    manifest_path = agency_root / "agency.json"
    high: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    try:
        manifest = read_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError("agency.json top-level value is not an object")
    except Exception as exc:  # noqa: BLE001 - doctor output must retain parse failures
        manifest = {}
        high.append(
            {
                "code": "invalid_agency_manifest",
                "severity": "high",
                "path": relpath(manifest_path, root),
                "message": f"agency.json could not be parsed: {exc}",
            }
        )

    name = agency_required_string(manifest, "name", high)
    for key in ("display_name", "description", "version", "layer", "class", "repository"):
        agency_required_string(manifest, key, high)
    if manifest.get("schema_version") != AGENCY_SCHEMA_VERSION:
        high.append(
            {
                "code": "invalid_agency_schema_version",
                "severity": "high",
                "path": relpath(manifest_path, root),
                "message": f"schema_version must be {AGENCY_SCHEMA_VERSION!r}",
            }
        )
    if manifest.get("kind") != "agency":
        high.append(
            {
                "code": "invalid_agency_kind",
                "severity": "high",
                "path": relpath(manifest_path, root),
                "message": "kind must be 'agency'",
            }
        )

    schema_entry = manifest.get("$schema")
    if not isinstance(schema_entry, str) or not schema_entry:
        high.append(
            {
                "code": "missing_agency_schema",
                "severity": "high",
                "path": relpath(manifest_path, root),
                "message": "$schema must name a repository-local schema",
            }
        )
    else:
        stripped, schema_path, schema_error = declared_rel(schema_entry, agency_root)
        if schema_error or not schema_path.is_file():
            high.append(
                {
                    "code": "missing_agency_schema",
                    "severity": "high",
                    "path": stripped,
                    "message": schema_error or "declared agency schema does not exist",
                }
            )

    install = manifest.get("install") if isinstance(manifest.get("install"), dict) else {}
    install_script = install.get("script")
    if not isinstance(install_script, str) or not install_script:
        high.append(
            {
                "code": "missing_agency_install_script",
                "severity": "high",
                "path": "agency.json:install.script",
                "message": "install.script must name a repository-local installer",
            }
        )
        install_script = ""
    else:
        stripped, script_path, script_error = declared_rel(install_script, agency_root)
        if script_error or not script_path.is_file():
            high.append(
                {
                    "code": "missing_agency_install_script",
                    "severity": "high",
                    "path": stripped,
                    "message": script_error or "declared agency installer does not exist",
                }
            )
    check_args = agency_string_list(install.get("check_args"), field="install.check_args", high=high)
    default_args = agency_string_list(
        install.get("default_args"),
        field="install.default_args",
        high=high,
        required=False,
    )
    supported_os = agency_string_list(install.get("supported_os"), field="install.supported_os", high=high)

    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    runtime_binary = runtime.get("binary")
    if not isinstance(runtime_binary, str) or not runtime_binary:
        high.append(
            {
                "code": "invalid_agency_runtime",
                "severity": "high",
                "path": "agency.json:runtime.binary",
                "message": "runtime.binary must be a non-empty command name",
            }
        )
        runtime_binary = ""
    doctor_args = agency_string_list(runtime.get("doctor_args"), field="runtime.doctor_args", high=high)
    status_args = agency_string_list(runtime.get("status_args"), field="runtime.status_args", high=high)

    agency_string_list(manifest.get("capabilities"), field="capabilities", high=high)
    agency_string_list(manifest.get("contracts"), field="contracts", high=high)
    authority = manifest.get("authority") if isinstance(manifest.get("authority"), dict) else {}
    for key in ("may", "requires_approval", "never"):
        agency_string_list(authority.get(key), field=f"authority.{key}", high=high)

    status = "fail" if high else "warn" if warnings else "ok"
    platform_name = current_platform()
    return {
        "kind": "agency",
        "name": name or agency_root.name.lower(),
        "display_name": manifest.get("display_name", agency_root.name),
        "description": manifest.get("description", ""),
        "version": manifest.get("version", ""),
        "layer": manifest.get("layer", ""),
        "class": manifest.get("class", ""),
        "path": relpath(agency_root, root),
        "manifest_path": relpath(manifest_path, root),
        "install": {
            "script": install_script,
            "check_args": check_args,
            "default_args": default_args,
            "supported_os": supported_os,
        },
        "runtime": {
            "binary": runtime_binary,
            "doctor_args": doctor_args,
            "status_args": status_args,
            "service_manager": runtime.get("service_manager", ""),
            "service": runtime.get("service", ""),
            "timer": runtime.get("timer", ""),
        },
        "platform": {
            "current": platform_name,
            "supported": platform_name in supported_os,
        },
        "drift": {
            "status": status,
            "high": high,
            "warnings": warnings,
        },
    }


def profile_summary(plugins: list[dict[str, Any]]) -> dict[str, Any]:
    packs: dict[str, list[str]] = {name: [] for name in PROFILE_TAXONOMY}
    for plugin in plugins:
        profile = plugin.get("profile", {})
        name = plugin["name"]
        for pack in profile.get("packs", []):
            packs.setdefault(pack, []).append(name)
        if profile.get("visibility") not in {"internal", "deprecated"}:
            packs["all"].append(name)

    return {
        "taxonomy": {name: PROFILE_TAXONOMY[name] for name in PROFILE_TAXONOMY},
        "packs": {name: sorted(set(values)) for name, values in packs.items()},
    }


def build_inventory(
    root: Path | str,
    *,
    rig_path: Path | str | None = None,
    marketplace_path: Path | str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    resolved_rig = Path(rig_path).resolve() if rig_path is not None else default_rig_path(root_path).resolve()
    resolved_marketplace = (
        Path(marketplace_path).resolve() if marketplace_path is not None else default_marketplace_path(root_path).resolve()
    )

    rig_entries, rig_global_drift = load_rig_entries(resolved_rig)
    marketplace_entries, marketplace_global_drift = load_marketplace_entries(resolved_marketplace)

    plugins = [
        analyze_plugin(root_path, plugin_root, rig_entries, marketplace_entries)
        for plugin_root in discover_plugin_roots(root_path)
    ]
    plugins.sort(key=lambda plugin: plugin["name"])
    plugin_names = {plugin["name"] for plugin in plugins}
    agencies = [analyze_agency(root_path, agency_root) for agency_root in discover_agency_roots(root_path)]
    agencies.sort(key=lambda agency: agency["name"])

    orphaned_rig = [
        {
            "name": entry["name"],
            "source": entry["source"],
            "tier": entry["tier"],
            "severity": "high",
            "message": "agent-rig.json references a first-party plugin that is missing from interverse/",
        }
        for entry in sorted(rig_entries.values(), key=lambda item: item["name"])
        if entry["name"] not in plugin_names
    ]
    orphaned_marketplace = [
        {
            "name": name,
            "version": str(entry.get("version", "")),
            "severity": "warning",
            "message": "marketplace.json references a plugin not present in this checkout inventory",
        }
        for name, entry in sorted(marketplace_entries.items())
        if name not in plugin_names
    ]

    plugin_high = sum(len(plugin["drift"]["high"]) for plugin in plugins)
    plugin_warnings = sum(len(plugin["drift"]["warnings"]) for plugin in plugins)
    agency_high = sum(len(agency["drift"]["high"]) for agency in agencies)
    agency_warnings = sum(len(agency["drift"]["warnings"]) for agency in agencies)
    global_high = sum(1 for item in rig_global_drift + marketplace_global_drift if item["severity"] == "high")
    global_warnings = sum(1 for item in rig_global_drift + marketplace_global_drift if item["severity"] == "warning")
    high_drift_count = plugin_high + agency_high + len(orphaned_rig) + global_high
    warning_drift_count = plugin_warnings + agency_warnings + len(orphaned_marketplace) + global_warnings

    ok_count = sum(1 for plugin in plugins if plugin["drift"]["status"] == "ok")
    warn_count = sum(1 for plugin in plugins if plugin["drift"]["status"] == "warn")
    failing_plugin_count = sum(1 for plugin in plugins if plugin["drift"]["status"] == "fail")
    agency_ok_count = sum(1 for agency in agencies if agency["drift"]["status"] == "ok")
    agency_warn_count = sum(1 for agency in agencies if agency["drift"]["status"] == "warn")
    failing_agency_count = sum(1 for agency in agencies if agency["drift"]["status"] == "fail")

    return {
        "root": root_path.as_posix(),
        "rig": {
            "path": resolved_rig.as_posix(),
            "first_party_count": len(rig_entries),
        },
        "marketplace": {
            "path": resolved_marketplace.as_posix(),
            "first_party_count": len(marketplace_entries),
        },
        "summary": {
            "plugin_count": len(plugins),
            "agency_count": len(agencies),
            "ok_count": ok_count,
            "warn_count": warn_count,
            "failing_plugin_count": failing_plugin_count,
            "agency_ok_count": agency_ok_count,
            "agency_warn_count": agency_warn_count,
            "failing_agency_count": failing_agency_count,
            "fail_count": high_drift_count,
            "high_drift_count": high_drift_count,
            "warning_drift_count": warning_drift_count,
        },
        "global_drift": rig_global_drift + marketplace_global_drift,
        "orphaned": {
            "rig": orphaned_rig,
            "marketplace": orphaned_marketplace,
        },
        "profiles": profile_summary(plugins),
        "plugins": plugins,
        "agencies": agencies,
    }


def print_human(ledger: dict[str, Any], *, verbose: bool = False) -> None:
    summary = ledger["summary"]
    print("Interverse Inventory Doctor")
    print(f"Root: {ledger['root']}")
    print(f"Plugins: {summary['plugin_count']} ok={summary['ok_count']} warn={summary['warn_count']} fail={summary['failing_plugin_count']}")
    print(
        f"Agencies: {summary['agency_count']} ok={summary['agency_ok_count']} "
        f"warn={summary['agency_warn_count']} fail={summary['failing_agency_count']}"
    )
    print(f"High drift: {summary['high_drift_count']}  Warning drift: {summary['warning_drift_count']}")
    print(f"Rig: {ledger['rig']['path']} ({ledger['rig']['first_party_count']} first-party entries)")
    print(f"Marketplace: {ledger['marketplace']['path']} ({ledger['marketplace']['first_party_count']} entries)")

    for item in ledger["global_drift"]:
        print(f"[{item['severity'].upper()}] {item['code']}: {item['message']} ({item['path']})")

    for item in ledger["orphaned"]["rig"]:
        print(f"[HIGH] orphaned_rig_plugin: {item['source']} ({item['message']})")

    if verbose:
        for item in ledger["orphaned"]["marketplace"]:
            print(f"[WARNING] orphaned_marketplace_plugin: {item['name']} ({item['message']})")

    for plugin in ledger["plugins"]:
        drift = plugin["drift"]
        if drift["status"] == "ok" and not verbose:
            continue
        print(f"\n{plugin['name']} [{drift['status']}] {plugin['path']}")
        print(
            "  surfaces="
            + (",".join(plugin["surface_types"]) or "none")
            + f" rig={plugin['rig']['tier'] or 'none'} marketplace={plugin['marketplace']['present']}"
            + f" profile={plugin['profile']['primary']} visibility={plugin['profile']['visibility']}"
        )
        for item in drift["high"]:
            print(f"  [HIGH] {item['code']}: {item['message']} ({item.get('path', '')})")
        if verbose or drift["status"] == "warn":
            for item in drift["warnings"]:
                print(f"  [WARNING] {item['code']}: {item['message']} ({item.get('path', '')})")

    for agency in ledger["agencies"]:
        drift = agency["drift"]
        if drift["status"] == "ok" and not verbose:
            continue
        support = "supported" if agency["platform"]["supported"] else f"unsupported on {agency['platform']['current']}"
        print(f"\n{agency['name']} [agency:{drift['status']}] {agency['path']}")
        print(f"  class={agency['class']} layer={agency['layer']} platform={support}")
        for item in drift["high"]:
            print(f"  [HIGH] {item['code']}: {item['message']} ({item.get('path', '')})")
        if verbose or drift["status"] == "warn":
            for item in drift["warnings"]:
                print(f"  [WARNING] {item['code']}: {item['message']} ({item.get('path', '')})")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.environ.get("SYLVESTE_ROOT", "."))
    parser.add_argument("--rig", default=os.environ.get("INTERVERSE_INVENTORY_RIG"))
    parser.add_argument("--marketplace", default=os.environ.get("INTERVERSE_INVENTORY_MARKETPLACE"))
    parser.add_argument("--json", action="store_true", help="print the full inventory ledger as JSON")
    parser.add_argument("--check", action="store_true", help="exit nonzero when high-severity drift is present")
    parser.add_argument("--verbose", "-v", action="store_true", help="include warning-level plugin details in human output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    try:
        ledger = build_inventory(args.root, rig_path=args.rig, marketplace_path=args.marketplace)
    except json.JSONDecodeError as exc:
        print(f"interverse_inventory: invalid JSON: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"interverse_inventory: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(ledger, indent=2, sort_keys=True))
    else:
        print_human(ledger, verbose=args.verbose)

    if args.check and ledger["summary"]["high_drift_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
