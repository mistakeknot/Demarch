#!/usr/bin/env python3
"""Fail when kimi.plugin.json's version has fallen behind its source manifest.

Why this exists separately from gen-kimi-manifests.py --check
------------------------------------------------------------
`--check` is the strong check: it regenerates and byte-compares. But it needs
the generator, which lives in the Sylveste monorepo, and the plugins live in 62
separate repos. Neither side can see the other in CI:

  * a monorepo checkout has no plugins — os/, core/ and interverse/ are
    gitignored, so `--check` there inspects nothing and passes vacuously;
  * a plugin repo checkout has no generator.

So the enforceable check in a plugin repo's own CI has to be self-contained.
This is that check. It needs nothing but the two JSON files already in the repo.

It is deliberately narrower than `--check`. It catches the one failure mode that
actually recurs — a version bump in .claude-plugin/plugin.json that did not
re-run the generator, which is how 21 of 62 manifests drifted — and it cannot
catch a description edit or a hook change. A narrow check that runs everywhere
beats a thorough one that runs nowhere; run `--check` too wherever the plugins
are materialised.

Usage
-----
    scripts/check-kimi-version-parity.py                  # this repo (cwd)
    scripts/check-kimi-version-parity.py --root .         # same
    scripts/check-kimi-version-parity.py --estate ~/projects/Sylveste
    scripts/check-kimi-version-parity.py --require-plugins 1

Exit codes: 0 in parity, 1 drift found, 2 nothing inspected.
"""

import argparse
import json
import sys
from pathlib import Path

CANONICAL = Path(".claude-plugin") / "plugin.json"
GENERATED = Path("kimi.plugin.json")


def read_version(path):
    try:
        return json.loads(path.read_text()).get("version")
    except (OSError, json.JSONDecodeError) as exc:
        return f"<unreadable: {exc}>"


def plugin_roots(root, estate):
    """Yield plugin roots. A single repo yields itself; an estate walks it."""
    if estate:
        clavain = estate / "os" / "Clavain"
        if (clavain / CANONICAL).is_file():
            yield clavain
        interverse = estate / "interverse"
        if interverse.is_dir():
            for child in sorted(interverse.iterdir()):
                if child.is_dir() and (child / CANONICAL).is_file():
                    yield child
        return
    if (root / CANONICAL).is_file():
        yield root


def behind_remote(plugin: Path) -> int:
    """How many commits this checkout is behind its remote-tracking branch.

    Parity is a property of what is in git, not of what happens to be on one
    machine's disk. A checkout that has not pulled will show kimi.plugin.json as
    absent even though it was committed — which is exactly what happened when
    this check first ran on zklw: 58 of 65 "out of parity", every one of them a
    stale working copy rather than real drift.

    A check that reports 58 false alarms gets ignored, so a stale repo must say
    "I cannot assess this" instead of "this is broken". No fetch: a read-only
    check must not mutate the repo it inspects, so this uses whatever
    remote-tracking ref is already there. Returns 0 when it cannot tell.
    """
    import subprocess

    r = subprocess.run(
        ["git", "-C", str(plugin), "rev-list", "--count", "HEAD..@{upstream}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return 0
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="a single plugin repo (default cwd)")
    ap.add_argument("--estate", help="walk os/Clavain + interverse/* under this root")
    ap.add_argument("--require-plugins", type=int, default=0, metavar="N",
                    help="fail if fewer than N plugins were inspected")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    estate = Path(args.estate).resolve() if args.estate else None

    inspected = 0
    drift = []
    unassessable = []
    for plugin in plugin_roots(root, estate):
        inspected += 1
        canonical = plugin / CANONICAL
        generated = plugin / GENERATED
        want = read_version(canonical)

        if not generated.is_file():
            behind = behind_remote(plugin)
            if behind:
                unassessable.append((plugin.name, behind))
            else:
                drift.append((plugin.name, want, None,
                              "kimi.plugin.json is missing"))
            continue
        got = read_version(generated)
        if got != want:
            drift.append((plugin.name, want, got,
                          "version bumped without regenerating"))

    for name, want, got, why in drift:
        print(f"DRIFT  {name}: {why} "
              f"(plugin.json={want} kimi.plugin.json={got})", file=sys.stderr)

    for name, behind in unassessable:
        print(f"STALE  {name}: {behind} commit(s) behind its remote — parity "
              f"cannot be judged from this checkout", file=sys.stderr)

    # A checkout too stale to judge is not a pass. Report it as could-not-run
    # rather than letting an unpulled machine either cry wolf or look healthy.
    if unassessable and len(unassessable) > len(drift):
        print(f"\nCANNOT ASSESS: {len(unassessable)} of {inspected} plugin(s) are "
              f"behind their remotes. Pull them, then re-run — this checkout is "
              f"not a valid basis for a parity verdict.", file=sys.stderr)
        return 2

    if args.require_plugins and inspected < args.require_plugins:
        print(f"FAIL: inspected {inspected} plugin(s), required at least "
              f"{args.require_plugins}. Nothing was checked — a pass here would "
              f"be meaningless.\n  root: {estate or root}", file=sys.stderr)
        return 2

    if drift:
        print(f"\n{len(drift)} of {inspected} plugin(s) out of parity. "
              f"Regenerate with the monorepo's scripts/gen-kimi-manifests.py, "
              f"then commit kimi.plugin.json alongside the version bump.",
              file=sys.stderr)
        return 1

    print(f"parity ok: {inspected} plugin(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
