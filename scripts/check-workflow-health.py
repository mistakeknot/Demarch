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

Exit 0 = every workflow in every repo can fire, and every repo answered.
Exit 1 = at least one is disabled or has never run.
Exit 2 = could not inspect, or could not inspect enough of the estate to speak
         for it — never confused with "all clear". That distinction was a claim
         this file made and did not keep until 2026-08-07; see the reachability
         floor at the bottom of main() for what it looked like when it broke.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

OWNER = "mistakeknot"


def gh_installed():
    """Whether the `gh` binary exists. Deliberately NOT whether it can answer.

    Named for what it actually establishes, because the difference is where the
    bug was: a present `gh` with a dead token satisfies this and answers nothing,
    and for a long time that combination reached the health surface as a pass.
    The reachability floor at the end of main() covers the other half.
    """
    return subprocess.run(["which", "gh"], capture_output=True).returncode == 0


def gh_json(path):
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def gh_raw(path):
    p = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.raw", path],
        capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def triggers(slug, path):
    """The event names a workflow declares, or None if they cannot be read.

    Takes an `owner/repo` slug, not a bare name — see origin_slug for why a
    directory name is not a safe stand-in for one.

    None rather than an empty set when the file cannot be fetched or parsed:
    "declares no triggers" and "I could not read its triggers" are different
    claims, and only the first would justify softening a verdict. Anything
    unreadable keeps the stricter reading.
    """
    txt = gh_raw(f"repos/{slug}/contents/{path}")
    if txt is None:
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        doc = yaml.safe_load(txt)
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    # YAML 1.1 reads a bare `on:` key as the boolean True, so a workflow's most
    # important line is the one most likely to be missed by a dict lookup.
    node = doc.get("on", doc.get(True))
    if isinstance(node, str):
        return {node}
    if isinstance(node, (list, dict)):
        return set(node)
    return None


def origin_slug(path: Path):
    """The `owner/repo` this checkout actually pushes to, or None.

    Read from the remote rather than assumed from the directory name, because on
    2026-08-07 three of the estate's directories disagreed with their remote:

        _shared    -> mistakeknot/interverse-shared
        lattice    -> mistakeknot/interweave
        intersite  -> mistakeknot/interverse-intersite

    The first two 404 under their directory name, so they were quietly skipped
    and reported as nothing at all. The third is the one that should worry you:
    `mistakeknot/intersite` EXISTS — a different repo, last pushed 2026-04-19 —
    while the checkout tracks `interverse-intersite`, pushed 2026-08-03. So this
    check was inspecting an abandoned repo and reporting the result as the health
    of the live one. Both happened to have zero workflows, which is luck, not
    correctness: a disabled secret-scan on the real repo would have been reported
    clean by looking somewhere else.

    An unreachable name announces itself. A wrong but answerable name does not.
    """
    p = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    url = p.stdout.strip()
    if url.endswith(".git"):
        url = url[:-4]
    # https://host/owner/repo and git@host:owner/repo both end in owner/repo.
    bits = url.replace(":", "/").rstrip("/").split("/")
    if len(bits) < 2 or not bits[-1] or not bits[-2]:
        return None
    return f"{bits[-2]}/{bits[-1]}"


def estate_repos(root: Path):
    """Yield (label, slug) for every checkout in the estate.

    A checkout whose slug cannot be resolved yields slug None rather than being
    dropped, so it surfaces as unreachable instead of vanishing. Nothing here is
    allowed to leave the list silently — that is the whole lesson of this file.
    """
    found = []
    clav = root / "os" / "Clavain"
    if (clav / ".git").is_dir():
        found.append((clav.name, origin_slug(clav)))
    iv = root / "interverse"
    if iv.is_dir():
        for c in sorted(iv.iterdir()):
            if (c / ".git").is_dir():
                found.append((c.name, origin_slug(c)))
    found.append((root.name, origin_slug(root) or f"{OWNER}/Sylveste"))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path.home() / "projects" / "Sylveste"))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--require-repos", type=int, default=0,
                    help="fail if fewer than N repos were inspected (vacuity guard)")
    args = ap.parse_args(argv)

    if not gh_installed():
        print("check-workflow-health: gh not available — cannot inspect", file=sys.stderr)
        return 2

    repos = estate_repos(Path(args.root))
    # Two floors, against two different denominators, because two different
    # things can go wrong. This one is the checkout: a partial clone has fewer
    # repos on disk than the estate really has. The one after the loop is
    # reachability, and it is the load-bearing one — see there.
    if len(repos) < args.require_repos:
        print(f"check-workflow-health: found {len(repos)} repo(s) on disk, "
              f"expected >= {args.require_repos}. Refusing to report health on "
              f"a partial checkout.", file=sys.stderr)
        return 2

    disabled, never, manual, unreachable = [], [], [], []
    inspected = 0
    for label, slug in repos:
        # The label is what it is called on disk; the slug is what it is on
        # GitHub. Reporting the label alone is what hid the case where they
        # differ, so a differing pair is printed as both.
        repo = f"{label} ({slug})" if slug and slug.split("/")[-1] != label else label
        if slug is None:
            unreachable.append(f"{label} (no origin remote)")
            continue
        data = gh_json(f"repos/{slug}/actions/workflows")
        if data is None:
            # Was a bare `continue` until 2026-08-07, and that was the whole bug:
            # a repo the API could not answer for left no trace at all. See the
            # reachability floor below for what it cost.
            unreachable.append(repo)
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
            runs = gh_json(f"repos/{slug}/actions/workflows/{w['id']}/runs?per_page=1")
            if runs is not None and runs.get("total_count", 0) == 0:
                # A workflow_dispatch-only workflow has no automatic trigger, so
                # "never ran" means nobody has needed it yet -- not that anything
                # is wrong. cxdb-release.yml is a manual cross-compile release
                # build, and counting it as a fault made this check report a
                # failure every day for a workflow behaving exactly as designed.
                #
                # Still reported, because unvalidated is a real thing to know
                # about a release path. Just not a failure.
                ev = triggers(slug, w.get("path", ""))
                if ev is not None and ev <= {"workflow_dispatch"}:
                    manual.append((repo, name))
                else:
                    never.append((repo, name))

    if not args.quiet:
        for repo, name, state in sorted(disabled):
            print(f"DISABLED  {repo:24} {name:30} state={state}")
        for repo, name in sorted(never):
            print(f"NEVER-RAN {repo:24} {name:30} (never validated)")
        for repo, name in sorted(manual):
            print(f"MANUAL    {repo:24} {name:30} "
                  f"(workflow_dispatch only; never dispatched)")
        # Capped, because this is the one list that can be the whole estate: a
        # dead token makes every repo unreachable at once, and 73 identical lines
        # bury the summary that says what happened. The others cannot run away
        # like that — a disabled workflow is news precisely because it is rare.
        # The count below is the fact; the names are only the sample.
        for repo in sorted(unreachable)[:8]:
            print(f"UNREACHED {repo:24} {'':30} (the API would not answer for it)")
        if len(unreachable) > 8:
            print(f"UNREACHED ... and {len(unreachable) - 8} more")

    tail = f", {len(manual)} manual-only never dispatched" if manual else ""
    if unreachable:
        tail += f", {len(unreachable)} unreachable"
    # "N of M" rather than "N", because the gap between them is the fact a reader
    # most needs and the one the old wording had no room to say.
    print(f"{inspected} of {len(repos)} repo(s) inspected: {len(disabled)} "
          f"disabled, {len(never)} never ran{tail}")
    if disabled:
        print("  re-enable: gh api --method PUT "
              "repos/<owner>/<repo>/actions/workflows/<id>/enable")

    # THE FLOOR THAT MATTERS APPLIES TO WHAT WAS INSPECTED, NOT TO WHAT WAS ON
    # DISK. Until 2026-08-07 `--require-repos` was tested only against the
    # directory listing, and the loop that followed skipped every repo the API
    # would not answer for. So a `gh` that was installed and on PATH but could
    # not authenticate — an expired token, a revoked scope, a rate limit, a
    # network flap — produced this, measured with a planted `gh` that exits 1:
    #
    #     0 repo(s) inspected: 0 disabled, 0 never ran
    #     exit 0
    #
    # A clean pass, on the health surface, from a run that inspected nothing. The
    # vacuity guard was pointed at the one number that could not go wrong: the
    # repos were all still on disk. The docstring above promises exit 2 for "no
    # gh, no auth", and the `which gh` probe at the top of main() delivered only
    # the first half — a binary being present says nothing about whether it can
    # answer.
    if inspected < args.require_repos:
        print(f"check-workflow-health: reached {inspected} of {len(repos)} "
              f"repo(s), expected >= {args.require_repos}. A verdict on this "
              f"few is not a verdict on the estate.", file=sys.stderr)
        return 2

    # A finding stands on its own. A disabled workflow is disabled whether or not
    # some other repo answered, so partial coverage does not soften it.
    if disabled or never:
        return 1

    # Nothing wrong in the repos that answered is not the same claim as nothing
    # wrong in the estate, and exit 0 here would make the second claim. If this
    # proves to flap on transient API failures, the fix is a retry around
    # gh_json — not a softer verdict, which would restore exactly the bug above.
    if unreachable:
        shown = sorted(unreachable)[:8]
        more = f" (+{len(unreachable) - 8} more)" if len(unreachable) > 8 else ""
        print(f"check-workflow-health: {len(unreachable)} repo(s) could not be "
              f"reached, so this run cannot speak for the whole estate: "
              f"{', '.join(shown)}{more}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
