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

# Whose repositories are OURS. A marketplace entry sourced anywhere else is a
# VENDORED third-party upstream, and commits in it are not our unshipped work.
#
# Why this is a class and not a special case for one plugin
# ---------------------------------------------------------
# `drift` means "code we committed has not been published", and its remedy is
# "run the publish wave". Both halves are wrong for a vendored upstream. The
# commits are not ours to ship — as of 2026-08-14 canongraph's local clone was
# 234 commits behind github.com/jvattimo1/canongraph, authored 204 by jvattimo
# and 30 by satkinson and ZERO by us — so "closed by publishing" would mean
# shipping unreviewed third-party code on the strength of a monitoring line.
#
# It was also making the two machines disagree, which is the part that proves
# this is structural. Resolution prefers a LOCAL checkout, and for our own repos
# that preference is right (only a working tree shows an uncommitted bump or an
# unpushed commit). For a vendored upstream it inverts: the verdict then tracks
# how recently THIS machine pulled somebody else's repo. Measured the same day,
# from identical committed code:
#
#     Clavain   source=local (clone 234 commits stale)   status=clean
#     zklw      source=mirror (no local clone)           status=drift, 38 commits
#
# The module docstring claims "either can determine all 67 on its own". That was
# true only for repos we write to. So vendored entries resolve from the MIRROR
# even when a local clone exists: the question "has upstream moved past what we
# published" is a question about upstream, and only the mirror answers it the
# same way on both hosts.
DEFAULT_OWN_ORGS = ("mistakeknot",)

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


def source_org(url: str) -> str:
    """The owning org/user of a git forge URL, or "" if it names none.

    Handles the https and scp-like ssh forms; anything else returns "" and is
    treated as OURS rather than vendored. That default is deliberate: calling
    something vendored downgrades it out of the failing set, so an unparseable
    URL must never be able to silence a real drift by accident.
    """
    if not url:
        return ""
    u = url.strip()
    for scheme in ("https://", "http://", "ssh://", "git://"):
        if u.startswith(scheme):
            u = u[len(scheme):]
            break
    else:
        if "@" in u and ":" in u:          # git@github.com:org/repo.git
            u = u.split("@", 1)[1].replace(":", "/", 1)
    if "@" in u.split("/", 1)[0]:          # strip creds in host position
        u = u.split("@", 1)[1]
    parts = [p for p in u.split("/") if p]
    return parts[1] if len(parts) >= 3 else ""


def is_vendored(url: str, own_orgs: tuple[str, ...]) -> bool:
    org = source_org(url)
    return bool(org) and org.lower() not in {o.lower() for o in own_orgs}


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
    ap.add_argument("--own-org", action="append", default=None,
                    help="git forge org whose repos are ours, not vendored "
                         f"(repeatable; default: {', '.join(DEFAULT_OWN_ORGS)})")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    roots = args.root or [Path.home() / "projects/Sylveste", Path.home() / "projects"]
    if not args.marketplace.is_file():
        print(f"marketplace manifest not found: {args.marketplace}", file=sys.stderr)
        return 2

    repos = discover_repos(roots)
    own_orgs = tuple(args.own_org) if args.own_org else DEFAULT_OWN_ORGS
    entries = marketplace_entries(args.marketplace)
    results: dict[str, dict] = {}
    r: dict
    for name, entry in sorted(entries.items()):
        if args.plugin and name not in args.plugin:
            continue
        version = entry.get("version")
        if not version:
            continue

        url = source_url(entry)
        vendored = is_vendored(url, own_orgs)

        # A vendored entry skips its local clone even when one exists. Locality
        # is preferred for OUR repos because only a working tree shows an
        # uncommitted bump or an unpushed commit; for somebody else's repo it
        # answers "how recently did I pull" instead of "where is upstream", and
        # that is what made the two machines disagree.
        repo = None if vendored else repos.get(name)
        local = repos.get(name)
        if repo:
            r = audit(repo, version)
            r["source"] = "local"
        elif args.no_mirror and vendored and local:
            # --no-mirror restores pre-mirror behaviour, so a vendored entry has
            # nowhere to go but the stale clone. It says so in the source field
            # rather than reporting like a mirror verdict.
            r = audit(local, version)
            r["source"] = "local (vendored, --no-mirror: may be stale)"
        elif args.no_mirror:
            r = {"status": "undetermined", "detail": "no local repo", "source": "-"}
        elif not url:
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

        if vendored:
            r["vendored"] = True
            r["upstream"] = url
            # Reclassified, not silenced: it keeps its count, age and commit
            # subjects, and is listed by name with its upstream URL. The only
            # thing that changes is which question it is evidence for.
            if r["status"] == "drift":
                r["status"] = "vendored-behind"
        r["published"] = version
        results[name] = r

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        drift = {k: v for k, v in results.items() if v["status"] == "drift"}
        vendored_behind = {k: v for k, v in results.items() if v["status"] == "vendored-behind"}
        uncommitted = {k: v for k, v in results.items() if v["status"] == "uncommitted-bump"}
        undet = {k: v for k, v in results.items() if v["status"] == "undetermined"}
        clean = [k for k, v in results.items() if v["status"] == "clean"]
        mirrored = sum(1 for v in results.values() if v.get("source") == "mirror")
        n_vendored = sum(1 for v in results.values() if v.get("vendored"))

        print(f"{len(results)} published plugins: {len(clean)} clean, {len(drift)} drifted, "
              f"{len(uncommitted)} uncommitted bump, {len(undet)} undetermined"
              f"  ({mirrored} judged from a source mirror, {n_vendored} vendored)\n")
        if drift:
            print(f"{'plugin':<16} {'published':<10} {'unshipped':>9} {'oldest':>7}  commits")
            print("-" * 100)
            for name, r in sorted(drift.items(), key=lambda kv: -kv[1]["count"]):
                print(f"{name:<16} {r['published']:<10} {r['count']:>9} {r['age']:>7}  {r['detail']}")
            # SAY WHICH KIND OF RED THIS IS.
            #
            # Drift is closed by publishing, and publishing is not something a
            # scheduled run can do: `ic publish --auto` refuses a plugin an
            # agent has touched, and the wave runs from the signer machine
            # (zklw) with CLAVAIN_AUTHZ_PROJECT_ROOT pinned. So this check will
            # report the same plugins, in the same words, every day until a
            # human runs it -- and a line that is red every morning is one
            # people stop reading, which is the failure the response budget
            # exists to catch.
            #
            # It stays a failure: published-behind-source is a real divergence
            # between what the marketplace advertises and what the repo holds.
            # It just names who can close it and how, so the reader is not left
            # to infer that from a count of unshipped commits.
            print("\n  Closed by publishing, which is a human action: run the wave "
                  "from the signer machine (zklw), regenerating manifests from the "
                  "MONOREPO ROOT first, then `ic publish <exact-version>` per plugin. "
                  "`ic publish --auto` will refuse any plugin an agent has modified.")
        if vendored_behind:
            # A DIFFERENT QUESTION, NOT A QUIETER ANSWER.
            #
            # These are listed by name, with their upstream and their real
            # commit count, precisely so the reclassification is visible. The
            # failure mode of a downgrade is that it reads as "handled"; the
            # failure mode of leaving them in `drifted` was worse, because the
            # remedy printed above -- run the publish wave -- would have shipped
            # third-party code nobody here reviewed.
            print("\nVendored upstreams behind their published version. These are NOT "
                  "unshipped work of ours:")
            for name, r in sorted(vendored_behind.items(), key=lambda kv: -kv[1]["count"]):
                print(f"  {name:<16} {r['published']:<10} {r['count']:>4} commits  "
                      f"{r['age']:>5}  {r.get('upstream', '')}")
            print("  Closed by a vendoring DECISION, not a publish: review the upstream "
                  "range, then either re-pin the marketplace entry at a reviewed commit "
                  "or take the update deliberately. Judged from the mirror on every "
                  "machine, so both hosts agree regardless of who has a local clone.")
        for label, group in (("Published without committing the bump", uncommitted),
                             ("Undetermined", undet)):
            if group:
                print(f"\n{label}:")
                for name, r in sorted(group.items()):
                    print(f"  {name:<16} {r['published']:<10} {r['detail']}")

    # `vendored-behind` is deliberately absent from this tuple. It is reported in
    # full above but does not fail the check, because the check's failure means
    # "somebody here must publish" and no publish closes an upstream we do not
    # write to. Leaving it in would have made publish-drift red every morning for
    # a reason nobody on this side could act on -- which is how a check stops
    # being read, and would have taken the four real drifts down with it.
    if any(v["status"] in ("drift", "uncommitted-bump") for v in results.values()):
        return 1
    if args.strict and any(v["status"] == "undetermined" for v in results.values()):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
