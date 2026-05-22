#!/usr/bin/env python3
"""Generate the Interverse plugin inventory ledger with drift status.

Reads every interverse/<plugin>/.claude-plugin/plugin.json plus the
canonical marketplace (core/marketplace/.claude-plugin/marketplace.json),
walks each plugin's component directories on disk, and emits a JSON
ledger to .interwatch/interverse-inventory.json.

Each plugin entry records:
- name, version, description
- surface_type (heuristic classification: workflow | review | docs |
  observability | mcp-only | research | deprecated | unclassified)
- in_marketplace (bool)
- components: per-type (skills/commands/agents/hooks/mcpServers)
  declared_count, ondisk_count, missing_paths
- drift_status (none | minor | major)
- drift_reasons (list of human-readable strings)

Exit codes:
  0 — no major drift
  1 — major drift detected (paths declared in manifest that don't exist
      on disk, or manifest parse errors)

The marketplace dimension and minor under-declarations DO NOT cause a
non-zero exit by themselves. CI/publish gates can require zero major
drift; the inventory file itself is the report for review.

Anchored by sylveste-b4ch. File contract: .interwatch/interverse-
inventory.json (writer: this script; reader: doctor + CI publish gate).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERVERSE = ROOT / "interverse"
MARKETPLACE_JSON = ROOT / "core" / "marketplace" / ".claude-plugin" / "marketplace.json"
OUTPUT = ROOT / ".interwatch" / "interverse-inventory.json"

COMPONENT_DIRS = {
    "skills": "skills",
    "commands": "commands",
    "agents": "agents",
    "hooks": "hooks",
    "mcpServers": "mcp-servers",
}


def load_marketplace() -> set[str]:
    if not MARKETPLACE_JSON.exists():
        return set()
    try:
        data = json.loads(MARKETPLACE_JSON.read_text())
    except json.JSONDecodeError:
        return set()
    return {p.get("name") for p in data.get("plugins", []) if isinstance(p, dict) and p.get("name")}


def declared_paths(manifest: dict, ctype: str) -> list[str]:
    raw = manifest.get(ctype, [])
    if not isinstance(raw, list):
        return []
    out = []
    for d in raw:
        if isinstance(d, str):
            out.append(d.removeprefix("./"))
        elif isinstance(d, dict) and isinstance(d.get("path"), str):
            out.append(d["path"].removeprefix("./"))
    return out


def _component_dirs(plugin_dir: Path, ctype: str) -> list[Path]:
    """Return the candidate on-disk directories for a component type.

    Plugins use either <plugin>/<ctype>/ or <plugin>/.claude-plugin/<ctype>/.
    Both layouts are present in Sylveste; the inventory treats them as
    equivalent and counts whichever exists (preferring both if present).
    """
    name = COMPONENT_DIRS[ctype]
    candidates = [plugin_dir / name, plugin_dir / ".claude-plugin" / name]
    return [c for c in candidates if c.exists() and c.is_dir()]


def count_ondisk(plugin_dir: Path, ctype: str) -> int:
    total = 0
    for cdir in _component_dirs(plugin_dir, ctype):
        if ctype == "skills":
            total += sum(1 for p in cdir.iterdir() if p.is_dir() and (p / "SKILL.md").exists())
        elif ctype in ("commands", "agents"):
            total += sum(1 for _ in cdir.rglob("*.md"))
        elif ctype == "hooks":
            total += sum(1 for p in cdir.rglob("*") if p.is_file() and p.suffix in (".sh", ".json"))
        elif ctype == "mcpServers":
            total += sum(1 for p in cdir.iterdir() if p.is_dir())
    return total


def classify_surface(name: str, keywords: set[str], components: dict[str, dict], description: str) -> str:
    desc_lc = (description or "").lower()
    # Explicit signals first
    if "deprecated" in keywords or "archive" in keywords or "archived" in keywords:
        return "deprecated"
    if "experiment" in keywords or "spike" in keywords or "research-only" in keywords:
        return "research"
    # MCP-only: ships MCP servers, no user-facing commands/skills
    mcp_count = components.get("mcpServers", {}).get("ondisk_count", 0)
    cmd_count = components.get("commands", {}).get("ondisk_count", 0)
    skill_count = components.get("skills", {}).get("ondisk_count", 0)
    if mcp_count > 0 and cmd_count == 0 and skill_count == 0:
        return "mcp-only"
    # Keyword-based primary classification
    if {"review", "multi-agent", "flux-drive"} & keywords:
        return "review"
    if {"docs", "documentation", "docgen", "doc-watch"} & keywords:
        return "docs"
    if {"observability", "evidence", "profiler", "metrics", "monitoring", "telemetry"} & keywords:
        return "observability"
    if {"research"} & keywords:
        return "research"
    # Default: assume workflow if it ships commands or skills
    if cmd_count > 0 or skill_count > 0:
        return "workflow"
    # No declared user-facing surface and not MCP-only
    return "unclassified"


def analyze_plugin(plugin_dir: Path, marketplace_names: set[str]) -> dict:
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return {
            "name": plugin_dir.name,
            "drift_status": "major",
            "drift_reasons": ["manifest_missing"],
        }

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return {
            "name": plugin_dir.name,
            "drift_status": "major",
            "drift_reasons": [f"manifest_parse_error: {e}"],
        }

    name = manifest.get("name") or plugin_dir.name
    version = manifest.get("version", "")
    description = manifest.get("description", "") or ""
    keywords = {str(k).lower() for k in manifest.get("keywords", []) if isinstance(k, (str, int))}

    drift_reasons: list[str] = []
    components: dict[str, dict] = {}

    for ctype in COMPONENT_DIRS:
        decl = declared_paths(manifest, ctype)
        ondisk = count_ondisk(plugin_dir, ctype)

        missing: list[str] = []
        for p in decl:
            if not (plugin_dir / p).exists():
                missing.append(p)
        if missing:
            drift_reasons.append(f"declared_{ctype}_missing_on_disk: {missing}")

        # Under-declaration: ondisk components exist but manifest declares none.
        # Surface this as minor for components Claude/Codex needs at load time.
        if not decl and ondisk > 0 and ctype in ("skills", "commands"):
            drift_reasons.append(f"manifest_under_declares_{ctype}: {ondisk} on disk, 0 declared")

        components[ctype] = {
            "declared_count": len(decl),
            "ondisk_count": ondisk,
            "missing_paths": missing,
        }

    in_marketplace = name in marketplace_names
    if not in_marketplace:
        drift_reasons.append("missing_from_marketplace")

    surface_type = classify_surface(name, keywords, components, description)

    drift_status = "none"
    if any(("missing_on_disk" in r or "parse_error" in r or "manifest_missing" in r) for r in drift_reasons):
        drift_status = "major"
    elif drift_reasons:
        drift_status = "minor"

    return {
        "name": name,
        "directory": plugin_dir.name,
        "version": version,
        "description": (description[:200] + "…") if len(description) > 200 else description,
        "surface_type": surface_type,
        "in_marketplace": in_marketplace,
        "components": components,
        "drift_status": drift_status,
        "drift_reasons": drift_reasons,
    }


def main() -> int:
    marketplace_names = load_marketplace()
    plugins = []
    for plugin_dir in sorted(INTERVERSE.iterdir()):
        if not plugin_dir.is_dir():
            continue
        if plugin_dir.name.startswith("."):
            continue
        # Archived plugin: ARCHIVED.md present, no .claude-plugin/. Surface it
        # so the ledger doesn't silently lose archived state.
        if not (plugin_dir / ".claude-plugin").exists():
            if (plugin_dir / "ARCHIVED.md").exists():
                plugins.append({
                    "name": plugin_dir.name,
                    "directory": plugin_dir.name,
                    "version": "",
                    "description": "(archived)",
                    "surface_type": "deprecated",
                    "in_marketplace": plugin_dir.name in marketplace_names,
                    "components": {},
                    "drift_status": "minor" if plugin_dir.name in marketplace_names else "none",
                    "drift_reasons": (
                        ["archived_but_in_marketplace"]
                        if plugin_dir.name in marketplace_names
                        else []
                    ),
                })
            # Otherwise: directory exists but isn't a Claude plugin (Go-only
            # project, scratch area, etc.). Skip silently.
            continue
        plugins.append(analyze_plugin(plugin_dir, marketplace_names))

    summary = {
        "major": sum(1 for p in plugins if p.get("drift_status") == "major"),
        "minor": sum(1 for p in plugins if p.get("drift_status") == "minor"),
        "none": sum(1 for p in plugins if p.get("drift_status") == "none"),
    }
    surface_breakdown: dict[str, int] = {}
    for p in plugins:
        s = p.get("surface_type", "unclassified")
        surface_breakdown[s] = surface_breakdown.get(s, 0) + 1

    marketplace_only = sorted(marketplace_names - {p["name"] for p in plugins})

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_plugins_on_disk": len(plugins),
        "total_plugins_in_marketplace": len(marketplace_names),
        "marketplace_only_plugins": marketplace_only,
        "drift_summary": summary,
        "surface_breakdown": surface_breakdown,
        "plugins": plugins,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")

    print(
        f"Interverse inventory written to {OUTPUT.relative_to(ROOT)}: "
        f"{len(plugins)} plugins on disk, {len(marketplace_names)} in marketplace. "
        f"Drift — major: {summary['major']}, minor: {summary['minor']}, none: {summary['none']}.",
        file=sys.stderr,
    )

    if summary["major"] > 0:
        majors = [p["name"] for p in plugins if p.get("drift_status") == "major"]
        print(f"Major drift in: {majors}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
