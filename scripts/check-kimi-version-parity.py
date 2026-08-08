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
    scripts/check-kimi-version-parity.py --estate ~/projects/Sylveste \
        --max-fetch-age-days 7

Exit codes: 0 in parity, 1 drift found, 2 could not assess — nothing inspected,
below the --require-plugins floor, or a finding that only a stale checkout
supports. Exit 2 is never a claim that something is wrong; it is the refusal to
make one.

In --estate mode the local clones stand in for what is in git, so their freshness
is checked before any of them is used to accuse a plugin of drift. In --root mode
the checkout IS the subject and no freshness rule applies. See remote_evidence().
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

CANONICAL = Path(".claude-plugin") / "plugin.json"
GENERATED = Path("kimi.plugin.json")


def read_version(path):
    try:
        return json.loads(path.read_text()).get("version")
    except (OSError, json.JSONDecodeError) as exc:
        return f"<unreadable: {exc}>"


def usable(version) -> bool:
    """Whether a value read by read_version can carry a parity verdict.

    A NON-VERSION IS NOT A MATCHING VERSION. The comparison this file is built
    on is `got != want`, and equality is the wrong test the moment both sides
    can be absent: two manifests that each lack a `version` key both read None,
    None equals None, and the pair is declared in parity on the strength of a
    field neither of them has. Two manifests that are both unreadable are worse,
    because they fail identically — two empty files produce the same
    JSONDecodeError text, so their `<unreadable: ...>` markers match and the
    check reports parity for a plugin whose manifests it could not even parse.

    Measured 2026-08-07 on a synthetic estate: three plugins with empty
    manifests, `parity ok: 3 plugin(s)`, exit 0. The equality held. It just was
    not about anything.
    """
    return (isinstance(version, str) and bool(version)
            and not version.startswith("<unreadable"))


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


class Evidence(NamedTuple):
    """Whether this checkout is a sound basis for accusing a plugin of drift.

    `trustworthy` is the only field the verdict consults. The rest are carried so
    the report can say WHY, because "cannot assess" without a reason is the kind
    of output people learn to scroll past.
    """

    trustworthy: bool
    reason: str  # empty when trustworthy
    behind: int | None  # per the cached remote-tracking ref; None = unresolved
    fetch_age_days: float | None  # None = never fetched since clone


def _git(plugin: Path, *args):
    return subprocess.run(["git", "-C", str(plugin), *args],
                          capture_output=True, text=True)


def last_fetch_age_days(plugin: Path):
    """Days since this repo last contacted its remote, or None if it never has.

    FETCH_HEAD is rewritten by every fetch and pull and by nothing else, which
    makes its mtime the only local record of when the remote-tracking refs were
    last checked against the remote. Its absence means this clone has never
    fetched.

    The one way this under-reports: `git fetch --no-write-fetch-head` skips the
    file. Nothing in the estate passes that flag, and the failure is in the safe
    direction — a repo that fetched would be reported as stale, costing a false
    "cannot assess" rather than a false accusation.
    """
    r = _git(plugin, "rev-parse", "--git-common-dir")
    if r.returncode != 0:
        return None
    common = Path(r.stdout.strip())
    if not common.is_absolute():
        common = plugin / common
    head = common / "FETCH_HEAD"
    if not head.exists():
        return None
    return (time.time() - head.stat().st_mtime) / 86400.0


def remote_evidence(plugin: Path, max_fetch_age_days: float) -> Evidence:
    """Can a drift finding from this checkout be believed?

    Parity is a property of what is in git, not of what happens to be on one
    machine's disk. A checkout that has not pulled shows kimi.plugin.json as
    absent, or shows an old one beside a bumped plugin.json, even though the pair
    was committed in agreement — which is what happened when this check first ran
    on zklw: 58 of 65 "out of parity", every one of them a stale working copy
    rather than real drift.

    THE FUNCTION THIS REPLACES ANSWERED A DIFFERENT QUESTION THAN IT WAS ASKED.
    It returned an int, and returned 0 both for "this checkout is level with its
    remote" and for "I could not find out" — no upstream configured, rev-list
    failed, unparseable output. Those are opposite states and the caller could
    not tell them apart, so `if behind:` read a failure to look as evidence of
    nothing to see.

    Worse, the number it did return was computed against the remote-tracking ref
    already on disk, and nothing here refreshes that ref. On a clone that last
    fetched five weeks ago, `HEAD..@{upstream}` is a comparison between two local
    pointers: it reports 0 with complete confidence and the remote is not
    involved. Measured 2026-08-07: 55 of 70 Clavain plugin checkouts reported
    "0 behind" from fetch data older than seven days, twelve of which had never
    fetched at all, while zklw — whose autosync keeps its checkouts current — had
    65 of 66 within the week. Both machines got the same integer out of this
    function. Only one of them had measured anything.

    That is why 2026-08-07 looked like a coverage gap between the machines and
    was not one. interlore was fixed on the remote on 08-03; Clavain had not
    fetched; the guard that exists to catch precisely that reported 0.

    NO FETCH, DELIBERATELY. A read-only check must not mutate the repos it
    inspects — an unattended timer that fetches 70 repos changes their state,
    can race a session mid-rebase, and turns a checker into a sync tool. So the
    staleness is REPORTED rather than resolved: this returns how old the evidence
    is and lets the caller refuse to convict on it. Freshening the estate is
    autosync's job, and on the machine where it runs, this returns trustworthy.
    """
    if _git(plugin, "rev-parse", "--git-dir").returncode != 0:
        # Not a git checkout at all. There is no remote for it to be behind and
        # no ref that could be stale, so the files on disk are the whole of the
        # available truth and judging them is correct.
        return Evidence(True, "", None, None)

    age = last_fetch_age_days(plugin)

    r = _git(plugin, "rev-list", "--count", "HEAD..@{upstream}")
    if r.returncode != 0:
        return Evidence(False, "no remote-tracking branch to compare against",
                        None, age)
    try:
        behind = int(r.stdout.strip())
    except ValueError:
        return Evidence(False, "could not read a commit count from git",
                        None, age)

    if behind:
        return Evidence(False, f"{behind} commit(s) behind its remote", behind, age)
    if age is None:
        return Evidence(False, "never fetched since clone, so '0 behind' compares "
                               "two local refs", behind, age)
    if age > max_fetch_age_days:
        return Evidence(False, f"last fetched {age:.0f}d ago, so '0 behind' is "
                               f"that old too", behind, age)
    return Evidence(True, "", behind, age)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="a single plugin repo (default cwd)")
    ap.add_argument("--estate", help="walk os/Clavain + interverse/* under this root")
    ap.add_argument("--require-plugins", type=int, default=0, metavar="N",
                    help="fail if fewer than N plugins were inspected")
    ap.add_argument("--max-fetch-age-days", type=float, default=7.0, metavar="D",
                    help="estate mode: a checkout that has not fetched within D "
                         "days cannot support a drift finding (default 7)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    estate = Path(args.estate).resolve() if args.estate else None

    # THE FRESHNESS GUARD IS AN ESTATE-MODE RULE ONLY, and the distinction is
    # load-bearing rather than cautious. The two modes ask different questions of
    # the same files:
    #
    #   --root  is a plugin repo checking ITSELF, in its own CI and pre-commit
    #           hook. That tree is the subject, not a proxy for one, so its
    #           agreement with a remote is beside the point. CI also checks out a
    #           detached HEAD, where `@{upstream}` does not resolve at all — so a
    #           guard that treats "no upstream" as "cannot judge" would turn the
    #           enforced check off precisely where it is enforced, and the check
    #           would go on exiting 0 while catching nothing.
    #
    #   --estate walks 70 local clones as STAND-INS for what is in git. There the
    #           age of the stand-in is the whole question.
    check_freshness = estate is not None
    trusted = Evidence(True, "", None, None)

    inspected = 0
    drift = []
    unassessable = []
    unproven = 0  # in parity here, on evidence too old to prove it anywhere else
    for plugin in plugin_roots(root, estate):
        inspected += 1
        canonical = plugin / CANONICAL
        generated = plugin / GENERATED
        want = read_version(canonical)

        # Decide WHAT the finding is first, and only then whether this checkout
        # is entitled to make it. The version that shipped asked those two
        # questions in the wrong order: it consulted the remote only on the
        # missing-file branch, so a present-but-stale kimi.plugin.json beside a
        # bumped plugin.json — the interlore shape, and by far the most common
        # one — was accused without the guard ever being called.
        if not generated.is_file():
            finding = (want, None, "kimi.plugin.json is missing")
        else:
            got = read_version(generated)
            if not usable(want) or not usable(got):
                finding = (want, got, "no readable version to compare")
            elif got != want:
                finding = (want, got, "version bumped without regenerating")
            else:
                finding = None

        ev = remote_evidence(plugin, args.max_fetch_age_days) if check_freshness \
            else trusted

        if finding is None:
            # A clean pair proves parity HERE. On a checkout that has not fetched
            # it proves nothing about the repo, because the bump may be sitting
            # unpulled. That is a limit on coverage rather than a false
            # accusation, so it does not move the verdict — but it is counted and
            # said out loud, because a pass whose basis is a month old should not
            # read identically to one taken this morning.
            if not ev.trustworthy:
                unproven += 1
            continue

        if ev.trustworthy:
            drift.append((plugin.name, *finding))
        else:
            unassessable.append((plugin.name, ev.reason, finding[2]))

    for name, want, got, why in drift:
        print(f"DRIFT  {name}: {why} "
              f"(plugin.json={want} kimi.plugin.json={got})", file=sys.stderr)

    for name, reason, suppressed in unassessable:
        # Name the accusation that was withheld, not just the fact of withholding
        # it. "STALE foo: 3 commits behind" told a reader nothing about whether
        # pulling would reveal a real problem or a non-event.
        print(f"STALE  {name}: would have reported '{suppressed}', but this "
              f"checkout cannot support it — {reason}", file=sys.stderr)

    # How old the evidence is, stated rather than assumed. This is the half of
    # the fix that is not a verdict change: on a machine whose clones do not
    # fetch, most of a green run rests on data nobody refreshed, and the run
    # should say so instead of reading exactly like a run on a current checkout.
    # Say what the count is a count OF. The first version of this line read
    # "N judged from fetch data older than 7d", which was true of most of the 65
    # it reported on Clavain and false of ten: nine clones that had fetched
    # recently enough to know they were behind, and one with no upstream at all.
    # Those cannot support a verdict either, but not for that reason, and a
    # summary that names one cause for three states is the kind of true-sounding
    # sentence this check exists to stop shipping.
    staleness = ""
    if unproven:
        staleness = (f"; {unproven} of {inspected} judged on remote data this "
                     f"checkout cannot vouch for (fetch older than "
                     f"{args.max_fetch_age_days:g}d, behind, or no upstream)")

    # THE FLOOR OUTRANKS EVERYTHING BELOW IT. Moved above the could-not-assess
    # branch to match check-workflow-health.py, which learned it the hard way:
    # when coverage has collapsed, the most informative thing to say is that it
    # collapsed. Both paths already returned 2, so this changes which reason gets
    # printed, not which verdict is reached.
    if args.require_plugins and inspected < args.require_plugins:
        print(f"FAIL: inspected {inspected} plugin(s), required at least "
              f"{args.require_plugins}. Nothing was checked — a pass here would "
              f"be meaningless.\n  root: {estate or root}", file=sys.stderr)
        print(f"parity: {inspected} plugin(s) inspected, below the floor of "
              f"{args.require_plugins}")
        return 2

    if drift:
        print(f"\n{len(drift)} of {inspected} plugin(s) out of parity. "
              f"Regenerate with the monorepo's scripts/gen-kimi-manifests.py, "
              f"then commit kimi.plugin.json alongside the version bump.",
              file=sys.stderr)
        print(f"parity: {len(drift)} of {inspected} plugin(s) out of "
              f"parity{staleness}")
        return 1

    # A finding this checkout is too stale to stand behind is not a pass and not
    # a finding. The old rule fired only when the stale count OUTNUMBERED the
    # drift count, which let a single unassessable plugin be rounded away by two
    # real ones — the one plugin nobody could judge is exactly the one worth
    # saying out loud.
    if unassessable:
        print(f"\nCANNOT ASSESS: {len(unassessable)} of {inspected} plugin(s) had "
              f"a parity finding this checkout is too stale to stand behind. Pull "
              f"them, then re-run.", file=sys.stderr)
        print(f"parity unassessable: {len(unassessable)} of {inspected} "
              f"plugin(s) too stale to judge{staleness}")
        return 2

    print(f"parity ok: {inspected} plugin(s){staleness}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
