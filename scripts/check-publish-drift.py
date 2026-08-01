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

Where the source comes from
---------------------------
A verdict of "undetermined" is the failure mode that quietly kills a check like
this: three plugins reported "no local repo" on Clavain simply because they were
never cloned there, and an audit that abstains on 3 of 67 trains you to read a
green result as "mostly green". So the source is resolved in two tiers:

  1. A LOCAL checkout, when one exists. Preferred, and not merely for speed — only
     a working tree can show a bump that was published but never committed, or
     commits that exist locally and have not been pushed. Those are real drift and
     a remote can never see them.
  2. Otherwise the repo named by the marketplace entry's own `source.url`, fetched
     into a bare mirror cache. Every entry carries one, so no plugin needs to be
     checked out on a machine for that machine to judge it.

This also means the two machines no longer need their verdicts reconciled: either
can determine all 67 on its own. Where they legitimately disagree, the machine
holding unpushed commits is the one telling the truth, and its verdict is the
stricter one.

Exit codes: 0 clean, 1 drift found, 2 could not determine (use --strict to fail on 2).
"""
from __future__ import annotations

import argparse
import json
import os
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
DEFAULT_CACHE = Path(os.environ.get("PUBLISH_DRIFT_CACHE", Path.home() / ".cache/publish-drift"))

# A mirror fetch that hangs is worse than one that fails: this runs on a timer, and
# a wedged git-over-https blocks every later check in the same run.
NET_TIMEOUT = 120


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


def marketplace_entries(marketplace: Path) -> dict[str, dict]:
    data = json.load(open(marketplace))
    plugins = data.get("plugins") or []
    if isinstance(plugins, dict):
        plugins = [dict(v, name=k) for k, v in plugins.items()]
    return {p["name"]: p for p in plugins if p.get("name")}


def source_url(entry: dict) -> str:
    """The git URL a marketplace entry points at, if it points at one.

    `source` is either a bare string or an object; only the url/git forms name a
    repository we can mirror. Anything else (a local path source, say) is not
    fetchable and stays undetermined rather than being guessed at.
    """
    src = entry.get("source")
    if isinstance(src, str):
        return src if src.endswith(".git") or src.startswith("http") else ""
    if isinstance(src, dict):
        url = src.get("url") or src.get("repo") or ""
        return url if isinstance(url, str) else ""
    return ""


def mirror(name: str, url: str, cache: Path, offline: bool) -> Path | None:
    """Bare mirror of a plugin's published source, refreshed in place.

    Bare on purpose: this only ever reads history, and a mirror of 67 repos with
    working trees would cost disk for nothing. `git ls-tree` replaces every
    filesystem existence check below so the same audit runs against either shape.
    """
    dest = cache / f"{name}.git"
    if dest.is_dir():
        if offline:
            return dest
        # Refresh; a failed fetch leaves the previous mirror intact and usable,
        # so a network blip degrades the answer's freshness rather than losing it.
        git(dest, "fetch", "--prune", "--quiet", "origin", "+refs/heads/*:refs/heads/*",
            timeout=NET_TIMEOUT)
        return dest
    if offline:
        return None
    cache.mkdir(parents=True, exist_ok=True)
    try:
        # URL comes from the marketplace manifest: passed as its own argv entry,
        # never interpolated into a shell string.
        r = subprocess.run(
            ["git", "clone", "--bare", "--quiet", url, str(dest)],
            capture_output=True, text=True, timeout=NET_TIMEOUT,
        )
    except Exception:
        return None
    return dest if r.returncode == 0 and dest.is_dir() else None


def resolve_tip(repo: Path) -> str:
    for ref in ("origin/main", "origin/master", "refs/heads/main", "refs/heads/master"):
        if git(repo, "rev-parse", "--verify", "-q", ref):
            return ref
    return "HEAD"


def tree_entries(repo: Path, tip: str) -> set[str]:
    """Top-level names present in the tree at `tip`.

    Replaces `(repo / p).exists()`: a bare mirror has no working tree, and even in
    a checkout the question is what the COMMIT contains, not what happens to be
    lying in the directory.
    """
    out = git(repo, "ls-tree", "--name-only", tip)
    return {line.strip().rstrip("/") for line in out.splitlines() if line.strip()}


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


def audit(repo: Path, published: str, bare: bool = False) -> dict:
    tip = resolve_tip(repo)

    bump = find_bump(repo, tip, published)
    if not bump:
        # No commit anywhere in tip's history sets this version. If the working
        # tree nonetheless shows it, the bump was published and never committed.
        #
        # This ordering matters. Asking the working tree FIRST reported a
        # phantom uncommitted bump on any checkout parked on a feature branch:
        # os/Clavain sits on executor-routing-adoption, 16 commits behind
        # origin/main, so its plugin.json legitimately lags. The bump was
        # committed — just not on the branch this machine happens to have out.
        # Consulting history first tells those two apart.
        if not bare and manifest_version(repo) == published:
            return {
                "status": "uncommitted-bump",
                "detail": f"working tree {published}, no commit in {tip} sets it — "
                          f"published without committing the bump",
            }
        return {"status": "undetermined", "detail": f"no commit sets plugin.json to {published}"}

    present = tree_entries(repo, tip)
    paths = [p for p in SHIPPED_SURFACE if p in present]
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
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE,
                    help="bare-mirror cache for plugins with no local checkout")
    ap.add_argument("--offline", action="store_true",
                    help="never touch the network; use existing mirrors only")
    ap.add_argument("--no-mirror", action="store_true",
                    help="local checkouts only (restores pre-mirror behaviour)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    roots = args.root or [Path.home() / "projects/Sylveste", Path.home() / "projects"]
    if not args.marketplace.is_file():
        print(f"marketplace manifest not found: {args.marketplace}", file=sys.stderr)
        return 2

    repos = discover_repos(roots)
    entries = marketplace_entries(args.marketplace)
    results = {}
    for name, entry in sorted(entries.items()):
        if args.plugin and name not in args.plugin:
            continue
        version = entry.get("version")
        if not version:
            continue

        repo = repos.get(name)
        if repo:
            r = audit(repo, version)
            r["source"] = "local"
        elif args.no_mirror:
            r = {"status": "undetermined", "detail": "no local repo", "source": "-"}
        else:
            url = source_url(entry)
            if not url:
                r = {"status": "undetermined",
                     "detail": "no local repo and no fetchable source in the marketplace entry",
                     "source": "-"}
            else:
                m = mirror(name, url, args.cache_dir, args.offline)
                if not m:
                    r = {"status": "undetermined",
                         "detail": f"no local repo; could not mirror {url}", "source": "-"}
                else:
                    r = audit(m, version, bare=True)
                    r["source"] = "mirror"
        r["published"] = version
        results[name] = r

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        drift = {k: v for k, v in results.items() if v["status"] == "drift"}
        uncommitted = {k: v for k, v in results.items() if v["status"] == "uncommitted-bump"}
        undet = {k: v for k, v in results.items() if v["status"] == "undetermined"}
        clean = [k for k, v in results.items() if v["status"] == "clean"]
        mirrored = sum(1 for v in results.values() if v.get("source") == "mirror")

        print(f"{len(results)} published plugins: {len(clean)} clean, {len(drift)} drifted, "
              f"{len(uncommitted)} uncommitted bump, {len(undet)} undetermined"
              f"  ({mirrored} judged from a source mirror)\n")
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
