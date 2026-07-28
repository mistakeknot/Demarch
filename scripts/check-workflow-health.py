#!/usr/bin/env python3
"""Report workflows that exist but cannot fire.

GitHub disables a workflow with a `schedule:` trigger after 60 days of
repository inactivity, and a disabled workflow does not run on push either. On
2026-07-28 this had silently switched off `secret-scan.yml` — the check standing
between a leaked credential and GitHub — on **17 of 36** plugin repos. Every one
showed a clean history of 100 successful runs and then simply stopped.

That is the same defect as a workflow whose inputs do not exist on a runner: it
is present, correct, reviewed, and not actually checking anything. The only
difference is that the platform turned this one off rather than the repo layout.

Also flags workflows that have never produced a single run — one that has never
executed is indistinguishable from one that is broken.

Exit 0 = every workflow can fire.
Exit 1 = at least one is disabled or has never run.
Exit 2 = could not inspect (no gh, no auth) — never confused with "all clear".
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

OWNER = "mistakeknot"


def gh_json(path):
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def estate_repos(root: Path):
    names = []
    clav = root / "os" / "Clavain"
    if (clav / ".git").is_dir():
        names.append("Clavain")
    iv = root / "interverse"
    if iv.is_dir():
        names += sorted(c.name for c in iv.iterdir() if (c / ".git").is_dir())
    names.append("Sylveste")
    return names


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path.home() / "projects" / "Sylveste"))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--require-repos", type=int, default=0,
                    help="fail if fewer than N repos were inspected (vacuity guard)")
    args = ap.parse_args(argv)

    if subprocess.run(["which", "gh"], capture_output=True).returncode != 0:
        print("check-workflow-health: gh not available — cannot inspect", file=sys.stderr)
        return 2

    repos = estate_repos(Path(args.root))
    if len(repos) < args.require_repos:
        print(f"check-workflow-health: inspected {len(repos)} repos, expected "
              f">= {args.require_repos}. Refusing to report health on a partial "
              f"checkout.", file=sys.stderr)
        return 2

    disabled, never = [], []
    inspected = 0
    for repo in repos:
        data = gh_json(f"repos/{OWNER}/{repo}/actions/workflows")
        if data is None:
            continue
        inspected += 1
        for w in data.get("workflows", []):
            name = w.get("path", "").split("/")[-1]
            # GitHub-generated entries are not ours to police.
            if not name.endswith((".yml", ".yaml")):
                continue
            state = w.get("state", "?")
            if state != "active":
                disabled.append((repo, name, state))
                continue
            runs = gh_json(f"repos/{OWNER}/{repo}/actions/workflows/{w['id']}/runs?per_page=1")
            if runs is not None and runs.get("total_count", 0) == 0:
                never.append((repo, name))

    if not args.quiet:
        for repo, name, state in sorted(disabled):
            print(f"DISABLED  {repo:16} {name:30} state={state}")
        for repo, name in sorted(never):
            print(f"NEVER-RAN {repo:16} {name:30} (never validated)")

    print(f"{inspected} repo(s) inspected: {len(disabled)} disabled, "
          f"{len(never)} never ran")
    if disabled:
        print("  re-enable: gh api --method PUT "
              "repos/mistakeknot/<repo>/actions/workflows/<id>/enable")
    return 1 if (disabled or never) else 0


if __name__ == "__main__":
    sys.exit(main())
