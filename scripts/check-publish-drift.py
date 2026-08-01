#!/usr/bin/env python3
"""Report plugins whose PUBLISHED artifact does not contain their COMMITTED source.

Why this exists
---------------
`ic publish status` compares plugin.json / marketplace / installed VERSION NUMBERS.
When they agree it prints a clean, reassuring table — and that table is silent about
the only thing that matters: whether the published artifact actually contains the
code that is committed.

On 2026-07-27 clavain was published as 0.6.293. On 2026-07-30 a hook fix landed,
without touching the version file. For three days `ic publish status` read

    plugin.json:  0.6.293
    marketplace:  0.6.293
    installed:    0.6.293

while the fix had never shipped. The plugin cache compounds it: a directory named
`clavain/0.6.293/` is labelled with a version, not hashed on content, so a stale
artifact looks current at every layer a human would think to check.

The invariant this checks
-------------------------
For each published plugin, let B be the commit that set plugin.json to the
published version. Nothing on the plugin's shipped surface may change in B..tip.
Any commit there is code that is committed but not shipped.

It also catches the adjacent failure: `ic publish <version>` syncs the marketplace
but does NOT commit the plugin repo, so the version bump can sit uncommitted in the
working tree while the marketplace already advertises it. Then no bump commit
exists at all, and a naive check silently finds nothing to compare.

Exit codes: 0 clean, 1 drift found, 2 could not determine (use --strict to fail on 2).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Directories that constitute a plugin's shipped, behavioural surface. Changes to
# docs/, tests/, .github/ do not alter what the plugin does when it runs, and
# treating them as drift would make the check cry wolf until it is ignored.
SHIPPED_SURFACE = ("hooks", "skills", "commands", "agents", "lib", "scripts", "mcp", "src", "bin")

DEFAULT_MARKETPLACE = (
    Path.home() / ".claude/plugins/marketplaces/interagency-marketplace/.claude-plugin/marketplace.json"
)


def git(repo: Path, *args: str, timeout: int = 30) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout
        )
        return out.stdout.strip()
    except Exception:
        return ""


def discover_repos(roots: list[Path]) -> dict[str, Path]:
    """Map plugin name -> repo dir by reading each .claude-plugin/plugin.json.

    Names come from manifests on disk and are never interpolated into a shell;
    every git call below passes them as separate argv entries.
    """
    repos: dict[str, Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for depth in ("*/.claude-plugin/plugin.json", "*/*/.claude-plugin/plugin.json"):
            for manifest in root.glob(depth):
                try:
                    name = json.load(open(manifest)).get("name")
                except Exception:
                    continue
                if name:
                    repos.setdefault(name, manifest.parent.parent)
    return repos


def published_versions(marketplace: Path) -> dict[str, str | None]:
    data = json.load(open(marketplace))
    plugins = data.get("plugins") or []
    if isinstance(plugins, dict):
        plugins = [dict(v, name=k) for k, v in plugins.items()]
    return {p["name"]: p.get("version") for p in plugins if p.get("name")}


def manifest_version(repo: Path, ref: str | None = None) -> str | None:
    rel = ".claude-plugin/plugin.json"
    try:
        raw = git(repo, "show", f"{ref}:{rel}") if ref else (repo / rel).read_text()
        return json.loads(raw).get("version")
    except Exception:
        return None


def find_bump(repo: Path, tip: str, version: str) -> str:
    """Commit that introduced this version into plugin.json.

    Pickaxe first; fall back to the last commit touching the manifest, which is
    correct whenever the manifest is only ever edited by a bump.
    """
    out = git(repo, "log", tip, "--format=%H", "-S", f'"version": "{version}"',
              "--", ".claude-plugin/plugin.json")
    if out:
        return out.splitlines()[-1].strip()
    if manifest_version(repo, tip) == version:
        out = git(repo, "log", tip, "-1", "--format=%H", "--", ".claude-plugin/plugin.json")
        return out.strip()
    return ""


def audit(repo: Path, published: str) -> dict:
    tip = "origin/main" if git(repo, "rev-parse", "--verify", "-q", "origin/main") else "HEAD"

    if manifest_version(repo) == published and manifest_version(repo, tip) != published:
        return {
            "status": "uncommitted-bump",
            "detail": f"working tree {published}, {tip} {manifest_version(repo, tip)} — "
                      f"published without committing the bump",
        }

    bump = find_bump(repo, tip, published)
    if not bump:
        return {"status": "undetermined", "detail": f"no commit sets plugin.json to {published}"}

    paths = [p for p in SHIPPED_SURFACE if (repo / p).exists()]
    if not paths:
        return {"status": "clean", "detail": "no shipped surface"}

    log = git(repo, "log", "--format=%H%x09%aI%x09%s", f"{bump}..{tip}", "--", *paths)
    commits = [line.split("\t", 2) for line in log.splitlines() if line.strip()]
    if not commits:
        return {"status": "clean", "detail": ""}

    oldest = min(c[1] for c in commits)
    try:
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(oldest)).days
        age = f"{days}d"
    except Exception:
        age = oldest[:10]
    return {
        "status": "drift",
        "count": len(commits),
        "age": age,
        "detail": "; ".join(c[2][:60] for c in commits[:3]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marketplace", type=Path, default=DEFAULT_MARKETPLACE)
    ap.add_argument("--root", type=Path, action="append", default=None,
                    help="repo root to scan (repeatable)")
    ap.add_argument("--plugin", action="append", default=None, help="limit to these plugins")
    ap.add_argument("--strict", action="store_true", help="treat undetermined as failure")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    roots = args.root or [Path.home() / "projects/Sylveste", Path.home() / "projects"]
    if not args.marketplace.is_file():
        print(f"marketplace manifest not found: {args.marketplace}", file=sys.stderr)
        return 2

    repos = discover_repos(roots)
    results = {}
    for name, version in sorted(published_versions(args.marketplace).items()):
        if args.plugin and name not in args.plugin:
            continue
        if not version:
            continue
        repo = repos.get(name)
        results[name] = ({"status": "undetermined", "detail": "no local repo"}
                         if not repo else audit(repo, version))
        results[name]["published"] = version

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        drift = {k: v for k, v in results.items() if v["status"] == "drift"}
        uncommitted = {k: v for k, v in results.items() if v["status"] == "uncommitted-bump"}
        undet = {k: v for k, v in results.items() if v["status"] == "undetermined"}
        clean = [k for k, v in results.items() if v["status"] == "clean"]

        print(f"{len(results)} published plugins: {len(clean)} clean, {len(drift)} drifted, "
              f"{len(uncommitted)} uncommitted bump, {len(undet)} undetermined\n")
        if drift:
            print(f"{'plugin':<16} {'published':<10} {'unshipped':>9} {'oldest':>7}  commits")
            print("-" * 100)
            for name, r in sorted(drift.items(), key=lambda kv: -kv[1]["count"]):
                print(f"{name:<16} {r['published']:<10} {r['count']:>9} {r['age']:>7}  {r['detail']}")
        for label, group in (("Published without committing the bump", uncommitted),
                             ("Undetermined", undet)):
            if group:
                print(f"\n{label}:")
                for name, r in sorted(group.items()):
                    print(f"  {name:<16} {r['published']:<10} {r['detail']}")

    if any(v["status"] in ("drift", "uncommitted-bump") for v in results.values()):
        return 1
    if args.strict and any(v["status"] == "undetermined" for v in results.values()):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
