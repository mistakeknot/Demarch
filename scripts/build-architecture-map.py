#!/usr/bin/env python3
"""Build ARCHITECTURE.json + ARCHITECTURE.md for the interagency plugin ecosystem.

Scans Sylveste/interverse/*/ for plugin.json manifests and detects:
  - Declared dependencies (explicit `peerDependencies`)
  - Discovered dependencies (cross-plugin references found in skill bodies,
    command bodies, agent prompts, hook scripts)
  - Hook subscribers (which plugins register hooks for which events)
  - MCP server consumers (which plugins ship MCP servers)

Output:
  ARCHITECTURE.json — machine-readable graph
  ARCHITECTURE.md   — human-readable map with dependency diagrams
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

INTERVERSE = Path(__file__).resolve().parent.parent / "interverse"
OUT_DIR = Path(__file__).resolve().parent.parent
OUT_JSON = OUT_DIR / "ARCHITECTURE.json"
OUT_MD = OUT_DIR / "ARCHITECTURE.md"

# Regex for cross-plugin references in skill/command/agent bodies.
# Matches: interspect:foo, plugin_interflux_*, intersynth:synthesize-review,
# /interflux:flux-drive, etc.
REF_RE = re.compile(
    r"\b("
    r"clavain|interbrowse|intercache|intercept|interchart|intercheck|intercraft|"
    r"interdeep|interdeploy|interdev|interdoc|interfer|interfluence|interflux|"
    r"interform|interhelm|interject|interjawn|interkasten|interknow|interlab|"
    r"interlearn|interleave|interlens|interline|interlock|interlore|intermap|"
    r"intermem|intermix|intermonk|intermux|intername|internext|interpath|"
    r"interpeer|interphase|interplug|interpub|interpulse|interrank|interscribe|"
    r"intersearch|intersense|intership|intersight|interskill|interslack|"
    r"interspect|interstat|intersynth|intertest|intertrace|intertree|intertrust|"
    r"interwatch|tldr-swinton|tool-time|tuivision"
    r")\b"
)


def discover_plugins() -> list[Path]:
    """Find every directory under interverse/ that has .claude-plugin/plugin.json."""
    out = []
    for child in sorted(INTERVERSE.iterdir()):
        if child.is_dir() and (child / ".claude-plugin" / "plugin.json").exists():
            out.append(child)
    return out


def scan_plugin(plugin_dir: Path, all_names: set[str]) -> dict:
    """Extract metadata + discovered references for one plugin."""
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    name = manifest["name"]

    # Files to scan for cross-references (skill bodies, command bodies, agent
    # prompts, hook scripts). Skip our own self-references.
    scan_paths = [
        plugin_dir / "skills",
        plugin_dir / "commands",
        plugin_dir / "agents",
        plugin_dir / "hooks",
        plugin_dir / "scripts",
    ]
    refs: dict[str, int] = defaultdict(int)
    for p in scan_paths:
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in {".md", ".sh", ".py", ".js", ".ts"}:
                try:
                    text = f.read_text(errors="ignore")
                except (OSError, UnicodeError):
                    continue
                for match in REF_RE.finditer(text):
                    ref = match.group(1)
                    if ref != name and ref in all_names:
                        refs[ref] += 1

    return {
        "name": name,
        "version": manifest.get("version", "?"),
        "description": (manifest.get("description") or "")[:200],
        "skills": [s for s in manifest.get("skills", []) or []],
        "commands": [c for c in manifest.get("commands", []) or []],
        "agents": [a for a in manifest.get("agents", []) or []],
        "mcp_servers": list((manifest.get("mcpServers") or {}).keys()),
        "declared_peers": manifest.get("peerDependencies") or [],
        "discovered_refs": dict(sorted(refs.items(), key=lambda kv: -kv[1])),
    }


def build_graph(plugins: list[dict]) -> dict:
    """Compose graph + reverse index + missing-peer warnings."""
    by_name = {p["name"]: p for p in plugins}

    # Reverse index: who references each plugin?
    referenced_by: dict[str, set[str]] = defaultdict(set)
    for p in plugins:
        for ref in p["discovered_refs"]:
            referenced_by[ref].add(p["name"])

    # Detect mismatches: discovered references that aren't in declared peers
    # (filter to "strong" refs — count >= 3 — to avoid noise from passing
    # mentions like "see also interX").
    warnings = []
    for p in plugins:
        declared = set(p["declared_peers"])
        strong_refs = {n for n, c in p["discovered_refs"].items() if c >= 3}
        missing = strong_refs - declared - {p["name"]}
        if missing:
            warnings.append(
                {
                    "plugin": p["name"],
                    "missing_peers": sorted(missing),
                    "kind": "undeclared_strong_dependency",
                }
            )

    return {
        "version": 1,
        "generated_by": "Sylveste/scripts/build-architecture-map.py",
        "plugin_count": len(plugins),
        "plugins": {p["name"]: p for p in plugins},
        "referenced_by": {k: sorted(v) for k, v in referenced_by.items()},
        "warnings": warnings,
    }


def render_md(graph: dict) -> str:
    """Render the machine graph into a human-readable architecture document."""
    plugins = graph["plugins"]
    referenced_by = graph["referenced_by"]
    warnings = graph["warnings"]

    lines = [
        "# Interagency Plugin Architecture",
        "",
        "Auto-generated from `Sylveste/scripts/build-architecture-map.py`. ",
        "DO NOT EDIT BY HAND — rerun the script to regenerate.",
        "",
        f"**Plugins surveyed:** {graph['plugin_count']}",
        "",
        "## Most-referenced plugins (hub nodes)",
        "",
        "Plugins that many others depend on. Disabling these has wide blast radius.",
        "",
        "| Plugin | Referenced by | Top consumers |",
        "|---|---:|---|",
    ]
    top_referenced = sorted(referenced_by.items(), key=lambda kv: -len(kv[1]))[:15]
    for name, consumers in top_referenced:
        top3 = ", ".join(consumers[:3])
        more = f" + {len(consumers) - 3}" if len(consumers) > 3 else ""
        lines.append(f"| `{name}` | {len(consumers)} | {top3}{more} |")

    lines += [
        "",
        "## Plugins with most outbound dependencies (consumers)",
        "",
        "Plugins that pull from many others. Most likely to break when peers change.",
        "",
        "| Plugin | Outbound refs | Strong peers (count ≥ 3) |",
        "|---|---:|---|",
    ]
    by_outbound = sorted(
        plugins.values(), key=lambda p: -len(p["discovered_refs"])
    )[:15]
    for p in by_outbound:
        strong = [
            f"{n}({c})" for n, c in p["discovered_refs"].items() if c >= 3
        ][:5]
        lines.append(
            f"| `{p['name']}` | {len(p['discovered_refs'])} | "
            f"{', '.join(strong) if strong else '—'} |"
        )

    if warnings:
        lines += [
            "",
            "## Warnings — undeclared strong dependencies",
            "",
            "These plugins reference others 3+ times in their own code but don't ",
            "declare them in `peerDependencies`. Either declare the dependency or ",
            "remove the references.",
            "",
        ]
        for w in warnings:
            lines.append(
                f"- **{w['plugin']}** → missing: {', '.join(w['missing_peers'])}"
            )

    lines += [
        "",
        "## Per-plugin detail",
        "",
    ]
    for name in sorted(plugins):
        p = plugins[name]
        lines.append(f"### `{name}` (v{p['version']})")
        lines.append("")
        if p["description"]:
            lines.append(f"{p['description']}")
            lines.append("")
        if p["mcp_servers"]:
            lines.append(f"- MCP servers: {', '.join(p['mcp_servers'])}")
        if p["skills"]:
            lines.append(f"- Skills: {len(p['skills'])}")
        if p["commands"]:
            lines.append(f"- Commands: {len(p['commands'])}")
        if p["agents"]:
            lines.append(f"- Agents: {len(p['agents'])}")
        if p["declared_peers"]:
            lines.append(
                f"- Declared peers: {', '.join(p['declared_peers'])}"
            )
        if p["discovered_refs"]:
            top = ", ".join(
                f"{n}({c})" for n, c in list(p["discovered_refs"].items())[:6]
            )
            lines.append(f"- Discovered refs: {top}")
        consumers = referenced_by.get(name, [])
        if consumers:
            lines.append(
                f"- Referenced by: {', '.join(sorted(consumers)[:8])}"
                + (f" + {len(consumers) - 8}" if len(consumers) > 8 else "")
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    if not INTERVERSE.exists():
        print(f"interverse/ not found at {INTERVERSE}", file=sys.stderr)
        return 1

    plugin_dirs = discover_plugins()
    if not plugin_dirs:
        print("no plugins found", file=sys.stderr)
        return 1

    all_names = {p.name for p in plugin_dirs}
    plugins = [scan_plugin(p, all_names) for p in plugin_dirs]
    graph = build_graph(plugins)

    OUT_JSON.write_text(json.dumps(graph, indent=2) + "\n")
    OUT_MD.write_text(render_md(graph))

    print(f"wrote {OUT_JSON} ({len(plugins)} plugins)")
    print(f"wrote {OUT_MD}")
    print(f"warnings: {len(graph['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
