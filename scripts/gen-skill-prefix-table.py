#!/usr/bin/env python3
"""Generate the skill-prefix routing table from installed plugin manifests.

Walks ~/.claude/plugins/cache/*/*/.claude-plugin/plugin.json (and the legacy
flat plugin.json layout), extracts each plugin's slash commands, and writes
a routing table to ~/.claude/skill-prefix-table.json.

The table is consumed by skill-prefix-router-hook.sh on UserPromptSubmit.
When a user prompt's first token matches a known slash command, the hook
emits a routing hint to skip Claude's skill-deliberation phase.

Output format:
    {
      "version": 1,
      "generated_at": "<iso>",
      "plugins": ["clavain", "interpath", ...],
      "commands": {
        "/clavain:work":     {"plugin": "clavain",     "command": "work",     "description": "..."},
        "/interpath:roadmap": {"plugin": "interpath", "command": "roadmap",  "description": "..."},
        ...
      },
      "global_commands": {
        "/loop":   {"plugin": null, "command": "loop",   "description": "..."},
        "/review": {"plugin": null, "command": "review", "description": "..."}
      }
    }

The generator is idempotent and side-effect-free (no live state mutation
beyond the output file). Safe to run from a SessionStart hook.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / "interagency-marketplace"
OUTPUT_PATH = Path.home() / ".claude" / "skill-prefix-table.json"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def parse_frontmatter(md_path: Path) -> dict[str, str]:
    """Extract simple key:value pairs from YAML frontmatter (no nested values)."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def discover_plugin_commands(plugin_root: Path) -> tuple[str, list[Path]] | None:
    """Return (plugin_name, [command_md_paths]) or None if no commands."""
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        manifest = plugin_root / "plugin.json"
    if not manifest.exists():
        return None
    try:
        meta = json.loads(manifest.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    name = meta.get("name")
    if not name:
        return None

    cmd_paths: list[Path] = []
    for cmd_ref in meta.get("commands", []) or []:
        rel = cmd_ref.lstrip("./")
        cmd_path = plugin_root / rel
        if cmd_path.exists():
            cmd_paths.append(cmd_path)
    if not cmd_paths:
        cmd_dir = plugin_root / "commands"
        if cmd_dir.is_dir():
            cmd_paths.extend(sorted(cmd_dir.glob("*.md")))
        cmd_dir2 = plugin_root / ".claude-plugin" / "commands"
        if cmd_dir2.is_dir():
            cmd_paths.extend(sorted(cmd_dir2.glob("*.md")))
    return name, cmd_paths


def latest_version(plugin_dir: Path) -> Path | None:
    """Return the highest-versioned subdir under <cache>/<plugin>/."""
    versions = [p for p in plugin_dir.iterdir() if p.is_dir()]
    if not versions:
        return None
    versions.sort(key=lambda p: p.name, reverse=True)
    return versions[0]


def build_table() -> dict:
    plugins: list[str] = []
    commands: dict[str, dict] = {}

    if CACHE_ROOT.is_dir():
        for plugin_dir in sorted(CACHE_ROOT.iterdir()):
            if not plugin_dir.is_dir():
                continue
            ver_dir = latest_version(plugin_dir)
            if ver_dir is None:
                continue
            result = discover_plugin_commands(ver_dir)
            if result is None:
                continue
            plugin_name, cmd_paths = result
            plugins.append(plugin_name)
            for cmd_md in cmd_paths:
                fm = parse_frontmatter(cmd_md)
                # The harness routes /<plugin>:<filestem>, not /<plugin>:<frontmatter-name>.
                # E.g. clavain/commands/status.md has `name: clavain-status` in frontmatter
                # but is invoked as `/clavain:status`. Always use the file stem.
                cmd_name = cmd_md.stem
                desc = fm.get("description", "")
                key = f"/{plugin_name}:{cmd_name}"
                commands[key] = {
                    "plugin": plugin_name,
                    "command": cmd_name,
                    "description": desc[:200],
                }

    return {
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z") or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "plugins": sorted(set(plugins)),
        "commands": commands,
        "global_commands": {},
    }


def main(argv: list[str]) -> int:
    # Cloud_default sessions have no plugin cache. Writing an empty table
    # there would mislead the per-prompt router into thinking it has up-to-
    # date "0 plugins" state. Skip cleanly when the cache is absent.
    if not CACHE_ROOT.is_dir():
        print(
            f"skill-prefix: no plugin cache at {CACHE_ROOT} — skipping "
            f"(cloud or pre-install state)"
        )
        return 0

    table = build_table()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
    print(
        f"Wrote {OUTPUT_PATH}: {len(table['plugins'])} plugins, "
        f"{len(table['commands'])} namespaced commands."
    )
    if "--print" in argv:
        for k in sorted(table["commands"]):
            v = table["commands"][k]
            print(f"  {k:50s} {v['description'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
