#!/usr/bin/env python3
"""Generate Kimi Code CLI plugin manifests (kimi.plugin.json) from Claude Code
plugin manifests (.claude-plugin/plugin.json) for Clavain and every Interverse
plugin.

Stdlib-only. Usage:

    scripts/gen-kimi-manifests.py [--root <repo-root>] [--check] [--json]
                                  [--plugin <name>...]

Default: write kimi.plugin.json into each plugin root (next to .claude-plugin/).
--check: write nothing; exit non-zero if any generated manifest is missing or
differs from what would be generated.
--json: machine-readable report instead of the human summary.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Hook events Kimi Code supports (from official docs).
KIMI_HOOK_EVENTS = {
    "UserPromptSubmit", "PreToolUse", "Stop", "PostToolUse",
    "PostToolUseFailure", "PermissionRequest", "PermissionResult",
    "SessionStart", "SessionEnd", "SubagentStart", "SubagentStop",
    "StopFailure", "Interrupt", "PreCompact", "PostCompact", "Notification",
}

# SessionStart matchers Kimi understands.
KIMI_SESSION_MATCHERS = {"startup", "resume", "exit"}

# Claude tool names with no Kimi equivalent: drop from alternations; if a
# matcher consists solely of dropped names it falls back to "Edit".
_DROPPED_TOOLS = {"MultiEdit", "NotebookEdit"}

# Claude tool name -> Kimi tool name.
_RENAMED_TOOLS = {"TodoWrite": "TodoList", "Task": "Agent"}

NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def sanitize_name(name):
    """Lowercase and coerce to Kimi's [a-z0-9][a-z0-9_-]{0,63} regex."""
    n = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-_")
    if not n or not n[0].isalnum():
        n = "p" + n
    return n[:64]


def normalize_author(author):
    """Claude author may be a string or an object; normalize to string."""
    if isinstance(author, dict):
        author = author.get("name") or ""
    if not isinstance(author, str):
        return None
    return author or None


def map_tool_matcher(matcher):
    """Translate a Claude PreToolUse/PostToolUse tool matcher to Kimi tools."""
    tokens = matcher.split("|")
    out = []
    for tok in tokens:
        if tok in _DROPPED_TOOLS:
            continue
        out.append(_RENAMED_TOOLS.get(tok, tok))
    if not out:
        return "Edit"
    # De-duplicate while preserving order (e.g. Task|Agent -> Agent).
    seen = set()
    deduped = []
    for tok in out:
        if tok not in seen:
            seen.add(tok)
            deduped.append(tok)
    return "|".join(deduped)


def map_matcher(event, matcher):
    """Map a Claude hook matcher to a Kimi matcher (or None to omit it)."""
    if not matcher:
        return None
    if event in ("SessionStart", "SessionEnd"):
        tokens = [t for t in matcher.split("|") if t in KIMI_SESSION_MATCHERS]
        return "|".join(tokens) if tokens else None
    if event in ("PreToolUse", "PostToolUse", "PostToolUseFailure",
                 "PermissionRequest", "PermissionResult"):
        return map_tool_matcher(matcher)
    return matcher


def rewrite_root_var(command):
    """Replace Claude plugin-root env refs with Kimi ones."""
    return command.replace("${CLAUDE_PLUGIN_ROOT}", "${KIMI_PLUGIN_ROOT}") \
                  .replace("$CLAUDE_PLUGIN_ROOT", "$KIMI_PLUGIN_ROOT")


def rewrite_root_var_deep(value):
    """Recursively rewrite plugin-root refs in args/env structures."""
    if isinstance(value, str):
        return rewrite_root_var(value)
    if isinstance(value, list):
        return [rewrite_root_var_deep(v) for v in value]
    if isinstance(value, dict):
        return {k: rewrite_root_var_deep(v) for k, v in value.items()}
    return value


def translate_hooks(hooks_path, report):
    """Flatten Claude hooks/hooks.json into Kimi's flat hook array."""
    if not hooks_path.is_file():
        return []
    try:
        data = json.loads(hooks_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        report["errors"].append(f"hooks: unreadable {hooks_path}: {exc}")
        return []
    flat = []
    for event, entries in (data.get("hooks") or {}).items():
        if event not in KIMI_HOOK_EVENTS:
            count = sum(len(e.get("hooks") or []) for e in entries)
            report["dropped_hooks"] += count
            report["notes"].append(
                f"dropped {count} hook(s) for unsupported event {event!r}")
            continue
        for entry in entries:
            matcher = map_matcher(event, entry.get("matcher"))
            for hook in entry.get("hooks") or []:
                if hook.get("type", "command") != "command":
                    report["dropped_hooks"] += 1
                    report["notes"].append(
                        f"dropped non-command hook on {event}")
                    continue
                item = {"event": event}
                if matcher:
                    item["matcher"] = matcher
                item["command"] = rewrite_root_var(hook.get("command", ""))
                timeout = hook.get("timeout")
                if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
                    item["timeout"] = max(1, min(600, int(timeout)))
                flat.append(item)
                report["hooks_ported"] += 1
    return flat


def translate_mcp_servers(servers, report):
    """Translate Claude mcpServers to the Kimi schema."""
    out = {}
    for name, srv in (servers or {}).items():
        if not isinstance(srv, dict):
            report["notes"].append(f"skipped malformed MCP server {name!r}")
            continue
        entry = {}
        if "url" in srv:  # HTTP transport
            entry["url"] = srv["url"]
            if isinstance(srv.get("headers"), dict):
                entry["headers"] = srv["headers"]
        else:  # stdio transport
            command = srv.get("command", "")
            if command.startswith("${CLAUDE_PLUGIN_ROOT}"):
                command = "." + command[len("${CLAUDE_PLUGIN_ROOT}"):]
                if not command.startswith("./"):
                    command = "./" + command.lstrip("/")
            entry["command"] = command
            if srv.get("args"):
                entry["args"] = rewrite_root_var_deep(srv["args"])
            if isinstance(srv.get("env"), dict) and srv["env"]:
                entry["env"] = rewrite_root_var_deep(srv["env"])
            cwd = srv.get("cwd")
            if isinstance(cwd, str):
                if cwd.startswith("${CLAUDE_PLUGIN_ROOT}"):
                    cwd = "." + cwd[len("${CLAUDE_PLUGIN_ROOT}"):]
                if not cwd.startswith("./"):
                    cwd = "./" + cwd.lstrip("/") if cwd != "." else "./"
                entry["cwd"] = cwd
        out[name] = entry
        report["mcp_ported"] += 1
    return out


def count_agents(plugin_dir, manifest):
    """Count agent definitions dropped (Kimi has no custom subagent format)."""
    agents = manifest.get("agents")
    if isinstance(agents, list):
        return len(agents)
    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        return sum(1 for _ in agents_dir.rglob("*.md"))
    return 0


def resolve_asset_dir(plugin_dir, manifest, key, report):
    """Return the Kimi directory reference for "skills" or "commands", or None.

    Kimi wants a single directory; Claude's manifest may either say nothing (and
    rely on the conventional <plugin>/<key>/ location) or declare explicit
    paths, which need not live there.

    This used to probe <plugin>/<key>/ only. Two plugins keep their assets under
    .claude-plugin/ instead — tldr-swinton (4 skills, 6 commands) and interpub
    (1 command) — so the generated manifests silently omitted them and Kimi saw
    no skills or commands at all for those plugins. Nothing reported it: a
    missing optional key looks exactly like a plugin that has none.

    Declared paths win, because the manifest is the authority on where a
    plugin's assets are. The directory probe stays as the fallback for the
    common case of a plugin that declares nothing.
    """
    declared = manifest.get(key)
    if declared:
        paths = declared if isinstance(declared, list) else [declared]
        parents = set()
        for raw in paths:
            # removeprefix, not lstrip: lstrip("./") strips a CHARACTER SET, so
            # "./.claude-plugin/skills" would lose the leading dot of the
            # directory name and resolve to a path that does not exist.
            rel = str(raw)
            while rel.startswith("./"):
                rel = rel[2:]
            if not rel:
                continue
            # A declared entry is normally one asset — an individual skill
            # directory, or a single command .md — so the reference Kimi wants
            # is its container. But a manifest may also declare the collection
            # directory itself. Discriminator: a skill directory holds SKILL.md,
            # the collection directory that holds skill directories does not.
            candidate = plugin_dir / rel
            if candidate.is_dir() and not (candidate / "SKILL.md").is_file():
                parent = candidate           # already the collection directory
            else:
                parent = candidate.parent    # an individual skill or command
            try:
                parents.add(parent.relative_to(plugin_dir).as_posix())
            except ValueError:
                report["notes"].append(
                    f"{key}: declared path {raw!r} escapes the plugin root; ignored"
                )
        if len(parents) == 1:
            only = parents.pop()
            # "." means the declared entry sits directly in the plugin root —
            # e.g. intermap declares ./skills and keeps a single skills/SKILL.md
            # rather than skills/<name>/SKILL.md. Emitting "././" would point
            # Kimi at the plugin root. Defer to the probe below, which applies
            # the convention test and correctly emits nothing for that layout.
            #
            # Likewise when the declaration resolves to the conventional
            # directory: the probe already handles it, and this function exists
            # only to stop assets in NON-default locations being dropped. Any
            # broader change would silently alter the 39 manifests that are
            # already correct.
            if only not in (".", key):
                if (plugin_dir / only).is_dir():
                    return f"./{only}/"
                report["notes"].append(
                    f"{key}: declared directory {only!r} does not exist on disk"
                )
                return None
        elif len(parents) > 1:
            # Kimi takes one directory. Emitting an arbitrary pick would be
            # worse than emitting nothing, because it would look authoritative.
            report["notes"].append(
                f"{key}: declared paths span {len(parents)} directories "
                f"({', '.join(sorted(parents))}); Kimi accepts one, so omitted"
            )
            return None

    fallback = plugin_dir / key
    if key == "skills":
        if fallback.is_dir() and any(p.is_dir() for p in fallback.iterdir()):
            return "./skills/"
        return None
    if fallback.is_dir():
        return "./commands/"
    return None


def translate_plugin(plugin_dir):
    """Build the Kimi manifest for one plugin root.

    Returns (manifest_dict, report_dict).
    """
    report = {"dropped_agents": 0, "dropped_hooks": 0, "hooks_ported": 0,
              "mcp_ported": 0, "notes": [], "errors": []}
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())

    kimi = {}
    kimi["name"] = sanitize_name(manifest.get("name") or plugin_dir.name)
    if not NAME_RE.fullmatch(kimi["name"]):
        report["errors"].append(f"name {kimi['name']!r} fails Kimi regex")
    for field in ("version", "description", "license", "keywords", "homepage"):
        if manifest.get(field):
            kimi[field] = manifest[field]
    author = normalize_author(manifest.get("author"))
    if author:
        kimi["author"] = author

    description = manifest.get("description") or ""
    interface = {"displayName": kimi["name"]}
    if description:
        short = description if len(description) <= 120 \
            else description[:117].rstrip() + "..."
        interface["shortDescription"] = short
    kimi["interface"] = interface

    skills_dir = plugin_dir / "skills"
    skills_ref = resolve_asset_dir(plugin_dir, manifest, "skills", report)
    if skills_ref:
        kimi["skills"] = skills_ref
    commands_ref = resolve_asset_dir(plugin_dir, manifest, "commands", report)
    if commands_ref:
        kimi["commands"] = commands_ref

    report["dropped_agents"] = count_agents(plugin_dir, manifest)

    # Clavain core rig only: load the orientation skill at session start.
    if kimi["name"] == "clavain" \
            and (skills_dir / "using-clavain").is_dir():
        kimi["sessionStart"] = {"skill": "using-clavain"}

    mcp = translate_mcp_servers(manifest.get("mcpServers"), report)
    if mcp:
        kimi["mcpServers"] = mcp

    hooks = translate_hooks(plugin_dir / "hooks" / "hooks.json", report)
    if hooks:
        kimi["hooks"] = hooks

    return kimi, report


def render(manifest):
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def discover_plugins(root):
    """Yield plugin root dirs: os/Clavain plus every interverse/* with a
    Claude manifest."""
    clavain = root / "os" / "Clavain"
    if (clavain / ".claude-plugin" / "plugin.json").is_file():
        yield clavain
    interverse = root / "interverse"
    if interverse.is_dir():
        for child in sorted(interverse.iterdir()):
            if child.is_dir() and \
                    (child / ".claude-plugin" / "plugin.json").is_file():
                yield child


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Kimi plugin manifests from Claude manifests.")
    parser.add_argument("--root", default=".",
                        help="repo root containing os/ and interverse/")
    parser.add_argument("--check", action="store_true",
                        help="verify manifests are up to date; write nothing")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable report")
    parser.add_argument("--plugin", action="append", default=[],
                        help="restrict to named plugin(s); repeatable")
    parser.add_argument("--require-plugins", type=int, default=0, metavar="N",
                        help="fail if fewer than N plugins were inspected; use "
                             "in CI so a checkout with no plugins cannot pass "
                             "vacuously")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    wanted = set(args.plugin)
    results = []
    stale = 0

    for plugin_dir in discover_plugins(root):
        entry = {"plugin": plugin_dir.name,
                 "path": str(plugin_dir.relative_to(root))}
        try:
            manifest, report = translate_plugin(plugin_dir)
        except (OSError, json.JSONDecodeError) as exc:
            entry.update(status="error", errors=[str(exc)])
            results.append(entry)
            continue
        if wanted and manifest["name"] not in wanted \
                and plugin_dir.name not in wanted:
            continue
        entry.update(report)
        entry["errors"] = report["errors"]
        target = plugin_dir / "kimi.plugin.json"
        text = render(manifest)
        if args.check:
            if not target.is_file():
                entry["status"] = "missing"
                stale += 1
            elif target.read_text() != text:
                entry["status"] = "differs"
                stale += 1
            else:
                entry["status"] = "ok"
        else:
            if target.is_file() and target.read_text() == text:
                entry["status"] = "unchanged"
            else:
                target.write_text(text)
                entry["status"] = "written"
        results.append(entry)

    totals = {
        "plugins": len(results),
        "errors": sum(1 for r in results if r.get("errors")),
        "hooks_ported": sum(r.get("hooks_ported", 0) for r in results),
        "dropped_hooks": sum(r.get("dropped_hooks", 0) for r in results),
        "dropped_agents": sum(r.get("dropped_agents", 0) for r in results),
        "mcp_ported": sum(r.get("mcp_ported", 0) for r in results),
    }

    if args.json:
        print(json.dumps({"root": str(root), "check": args.check,
                          "totals": totals, "plugins": results}, indent=2))
    else:
        mode = "check" if args.check else "generate"
        for r in results:
            line = f"{r['status']:>9}  {r['plugin']}"
            extras = []
            if r.get("hooks_ported"):
                extras.append(f"{r['hooks_ported']} hooks")
            if r.get("dropped_hooks"):
                extras.append(f"{r['dropped_hooks']} hooks dropped")
            if r.get("mcp_ported"):
                extras.append(f"{r['mcp_ported']} MCP")
            if r.get("dropped_agents"):
                extras.append(f"{r['dropped_agents']} agents dropped")
            if extras:
                line += f"  ({', '.join(extras)})"
            print(line)
            for note in r.get("notes", []):
                print(f"           note: {note}")
            for err in r.get("errors", []):
                print(f"           ERROR: {err}")
        print(f"\n{mode}: {totals['plugins']} plugins, "
              f"{totals['hooks_ported']} hooks ported "
              f"({totals['dropped_hooks']} dropped), "
              f"{totals['mcp_ported']} MCP servers ported, "
              f"{totals['dropped_agents']} agents dropped, "
              f"{totals['errors']} plugin(s) with errors")
        if args.check:
            print(f"check: {stale} manifest(s) missing or stale")

    # A vacuous run is the failure mode this whole check exists to prevent.
    #
    # The Sylveste monorepo .gitignore's os/, core/ and interverse/, so a fresh
    # `actions/checkout` contains none of the 62 plugins. `--check` there finds
    # nothing to compare, reports zero stale manifests, and exits 0 — a green
    # check that inspected nothing. That is not hypothetical: the existing
    # interverse-inventory workflow gates its real steps behind `[ -d interverse ]`
    # and has therefore been silently skipping them on every cloud run.
    #
    # Callers that expect plugins must say so, and get a hard failure rather than
    # false reassurance when they are absent.
    if args.require_plugins and totals["plugins"] < args.require_plugins:
        print(
            f"FAIL: inspected {totals['plugins']} plugin(s), "
            f"required at least {args.require_plugins}.\n"
            f"  root: {root}\n"
            f"  This checkout has no plugins to check. In the Sylveste monorepo "
            f"that is expected —\n"
            f"  os/, core/ and interverse/ are gitignored and every plugin lives "
            f"in its own repo, so a\n"
            f"  cloud checkout cannot see them. Run this where the plugins are "
            f"materialised, or run\n"
            f"  the per-repo version-parity check instead "
            f"(scripts/check-kimi-version-parity.py).",
            file=sys.stderr,
        )
        return 2

    failed = totals["errors"] or (stale if args.check else 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
