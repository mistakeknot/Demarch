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

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

# Exit codes, matching scripts/gen-kimi-manifests.py and
# scripts/check-kimi-version-parity.py:
#   0  the map on disk agrees with the estate
#   1  drift — the map is stale, or a new structural violation appeared
#   2  cannot assess — nothing was inspected, or the count fell below the
#      --require-plugins floor. Exit 2 is never a claim that something is
#      wrong; it is the refusal to make one.
OK, DRIFT, CANNOT_ASSESS = 0, 1, 2


def paths_for(root: Path) -> tuple[Path, Path, Path, Path]:
    """Resolve the four paths this script reads and writes, under one root."""
    return (root / "interverse",
            root / "ARCHITECTURE.json",
            root / "ARCHITECTURE.md",
            root / "ARCHITECTURE.baseline.json")

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


def discover_plugins(interverse: Path) -> list[Path]:
    """Find every directory under interverse/ that has .claude-plugin/plugin.json."""
    out = []
    if not interverse.is_dir():
        return out
    for child in sorted(interverse.iterdir()):
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


def violation_pairs(graph: dict) -> set[tuple[str, str]]:
    """Flatten warnings into (plugin, missing_peer) pairs.

    Pairs, not per-plugin entries, because a plugin already carrying a
    baselined violation can acquire a NEW undeclared peer. Comparing whole
    warning entries would let that second peer ride in silently under the
    first one's waiver — the baseline would grow scope without anyone
    deciding to grant it.
    """
    return {
        (w["plugin"], peer)
        for w in graph.get("warnings", [])
        for peer in w.get("missing_peers", [])
    }


def load_baseline(path: Path) -> tuple[set[tuple[str, str]], str | None]:
    """Read the waiver file. Returns (pairs, error) — never raises.

    A baseline that cannot be read is NOT an empty baseline. Treating an
    unreadable or malformed file as "nothing is waived" would flag all 23
    pre-existing violations as new on the first parse error, and the noise
    would train everyone to ignore the check. The caller turns the error into
    exit 2 (cannot assess) rather than exit 1 (drift).
    """
    if not path.is_file():
        return set(), None
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return set(), f"baseline unreadable at {path}: {exc}"
    entries = doc.get("entries")
    if not isinstance(entries, list):
        return set(), f"baseline at {path} has no 'entries' list"
    pairs = set()
    for e in entries:
        plugin, peers = e.get("plugin"), e.get("missing_peers")
        if not isinstance(plugin, str) or not isinstance(peers, list):
            return set(), f"baseline entry is malformed: {e!r}"
        if not e.get("reason") or not e.get("owner"):
            return set(), (f"baseline entry for {plugin} lacks a reason or an "
                           f"owner; a waiver nobody signed is not a waiver")
        pairs.update((plugin, peer) for peer in peers)
    return pairs, None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify the interagency plugin architecture map.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT),
                        help="repo root containing interverse/ (default: the "
                             "Sylveste checkout this script lives in)")
    parser.add_argument("--check", action="store_true",
                        help="verify the committed map matches the estate and "
                             "no unbaselined violation exists; write nothing")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable report")
    parser.add_argument("--require-plugins", type=int, default=0, metavar="N",
                        help="refuse to report (exit 2) if fewer than N "
                             "plugins were inspected; use in any automated "
                             "caller so a checkout without interverse/ cannot "
                             "pass vacuously")
    parser.add_argument("--baseline", default=None,
                        help="path to the waiver file for pre-existing "
                             "violations (default: ARCHITECTURE.baseline.json "
                             "beside the map)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    interverse, out_json, out_md, default_baseline = paths_for(root)
    baseline_path = Path(args.baseline) if args.baseline else default_baseline

    report: dict = {"root": str(root), "checked": args.check}

    def emit(status: str, code: int, message: str, **extra) -> int:
        report.update(status=status, message=message, **extra)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(message, file=sys.stderr if code else sys.stdout)
        return code

    plugin_dirs = discover_plugins(interverse)
    report["plugins_inspected"] = len(plugin_dirs)

    # Vacuity guard, before any verdict. A checkout that gitignores interverse/
    # inspects zero plugins; without this it would find zero drift and report
    # success having looked at nothing.
    if not plugin_dirs:
        return emit("cannot_assess", CANNOT_ASSESS,
                    f"inspected 0 plugins: no plugin manifests under "
                    f"{interverse}. Nothing was compared, so no verdict is "
                    f"available — this is not a pass.")
    if len(plugin_dirs) < args.require_plugins:
        return emit("cannot_assess", CANNOT_ASSESS,
                    f"inspected {len(plugin_dirs)} plugin(s), below the "
                    f"--require-plugins floor of {args.require_plugins}; "
                    f"refusing to report on a partial estate.")

    all_names = {p.name for p in plugin_dirs}
    graph = build_graph([scan_plugin(p, all_names) for p in plugin_dirs])
    md = render_md(graph)
    json_text = json.dumps(graph, indent=2) + "\n"

    baselined, baseline_error = load_baseline(baseline_path)
    if baseline_error and args.check:
        # Only a VERDICT needs a readable baseline. Regeneration must stay
        # possible with a broken waiver file, since regenerating is how you
        # fix the drift that a broken baseline would otherwise trap you in.
        return emit("cannot_assess", CANNOT_ASSESS, baseline_error)

    found = violation_pairs(graph)
    new_violations = sorted(found - baselined)
    stale_waivers = sorted(baselined - found)
    report.update(plugin_count=graph["plugin_count"],
                  violations=len(found),
                  baselined=len(baselined),
                  new_violations=[list(v) for v in new_violations],
                  stale_waivers=[list(v) for v in stale_waivers])

    if not args.check:
        out_json.write_text(json_text)
        out_md.write_text(md)
        warn = f" [warning: {baseline_error}]" if baseline_error else ""
        return emit("written", OK,
                    f"wrote {out_json} and {out_md} "
                    f"({graph['plugin_count']} plugins, {len(found)} "
                    f"violation(s), {len(new_violations)} unbaselined)" + warn,
                    baseline_error=baseline_error)

    problems = []
    for path, want in ((out_json, json_text), (out_md, md)):
        if not path.is_file():
            problems.append(f"{path.name} is missing")
        elif path.read_text() != want:
            problems.append(f"{path.name} is stale — regenerate it")
    report["stale_artifacts"] = list(problems)  # copy: problems grows below

    for plugin, peer in new_violations:
        problems.append(
            f"{plugin} references {peer} 3+ times without declaring it in "
            f"peerDependencies, and it is not in {baseline_path.name}")

    if problems:
        return emit("drift", DRIFT,
                    "structural drift:\n  - " + "\n  - ".join(problems))

    note = ""
    if stale_waivers:
        # Not drift: a waived violation that got fixed is the outcome the
        # waiver was for. Say so, so the baseline can be pruned deliberately.
        note = (f" ({len(stale_waivers)} baseline entr"
                f"{'y' if len(stale_waivers) == 1 else 'ies'} no longer "
                f"needed: {', '.join(f'{a}->{b}' for a, b in stale_waivers)})")
    return emit("ok", OK,
                f"map matches the estate: {graph['plugin_count']} plugins, "
                f"{len(found)} violation(s), all baselined{note}")


if __name__ == "__main__":
    raise SystemExit(main())
