"""Coverage for the self-contained Kimi version-parity check.

This is the check that can actually run in a plugin repo's CI and in the
pre-commit hook, because it needs nothing but the two JSON files already in the
repo. gen-kimi-manifests.py --check is stronger but needs the generator, which
lives in the monorepo — and the monorepo gitignores every plugin, so neither
side can check the other in CI.

The vacuity tests matter most. A checker that reports success after inspecting
zero plugins is the exact failure this whole line of work keeps finding, and the
monorepo is a checkout where that happens by default.
"""

import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_kimi_version_parity",
    Path(__file__).resolve().parents[1] / "scripts" / "check-kimi-version-parity.py",
)
parity = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(parity)


def _plugin(root: Path, canonical: str, generated: str | None):
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": root.name, "version": canonical}) + "\n"
    )
    if generated is not None:
        (root / "kimi.plugin.json").write_text(
            json.dumps({"name": root.name, "version": generated}) + "\n"
        )
    return root


def test_in_parity_passes(tmp_path):
    _plugin(tmp_path, "1.2.3", "1.2.3")
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 0


def test_bump_without_regeneration_fails(tmp_path):
    """The failure mode that drifted 21 of 62 manifests."""
    _plugin(tmp_path, "1.2.4", "1.2.3")
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1


def test_missing_generated_manifest_fails(tmp_path):
    _plugin(tmp_path, "1.2.3", None)
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1


def test_nothing_inspected_is_a_failure_not_a_pass(tmp_path):
    """A plugin-less checkout must not report success.

    Without --require-plugins the run is informational and exits 0; with it,
    finding nothing is a hard error. CI must always pass the flag.
    """
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 2
    assert parity.main(["--root", str(tmp_path)]) == 0


def test_estate_mode_walks_interverse_and_clavain(tmp_path):
    _plugin(tmp_path / "os" / "Clavain", "0.1.0", "0.1.0")
    _plugin(tmp_path / "interverse" / "alpha", "2.0.0", "2.0.0")
    _plugin(tmp_path / "interverse" / "beta", "3.0.0", "3.0.0")

    assert parity.main(["--estate", str(tmp_path), "--require-plugins", "3"]) == 0
    # One drifts -> the whole estate check fails.
    _plugin(tmp_path / "interverse" / "beta", "3.0.1", "3.0.0")
    assert parity.main(["--estate", str(tmp_path), "--require-plugins", "3"]) == 1


def test_estate_mode_vacuity(tmp_path):
    """An empty estate — the shape of a monorepo cloud checkout."""
    (tmp_path / "interverse").mkdir()
    (tmp_path / "os").mkdir()
    assert parity.main(["--estate", str(tmp_path), "--require-plugins", "60"]) == 2


def test_unreadable_manifest_does_not_silently_pass(tmp_path):
    _plugin(tmp_path, "1.0.0", "1.0.0")
    (tmp_path / "kimi.plugin.json").write_text("{ not json\n")
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1


def test_BOTH_manifests_unreadable_does_not_pass(tmp_path):
    """One corrupt manifest was already covered. Two was the hole.

    The check compares `got != want`, and read_version turns an unparseable file
    into a `<unreadable: ...>` marker built from the exception text. Two files
    that are broken the same way raise the same exception, so their markers are
    equal, so the comparison succeeds — on a plugin whose manifests could not be
    parsed at all. Measured before the fix: three plugins with empty manifests
    reported `parity ok: 3 plugin(s)` and exit 0.

    The test above stops one step short of this because it corrupts only the
    generated side, leaving the canonical side readable and the two markers
    unequal. That is why it passed throughout.
    """
    _plugin(tmp_path, "1.0.0", "1.0.0")
    (tmp_path / ".claude-plugin" / "plugin.json").write_text("")
    (tmp_path / "kimi.plugin.json").write_text("")
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1


def test_no_version_key_in_either_manifest_does_not_pass(tmp_path):
    """None == None is not parity; it is the absence of the thing being checked."""
    (tmp_path / ".claude-plugin").mkdir(parents=True)
    (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"name": "x"}\n')
    (tmp_path / "kimi.plugin.json").write_text('{"name": "x"}\n')
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1


def test_an_empty_version_string_is_not_a_version(tmp_path):
    _plugin(tmp_path, "", "")
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1


def test_an_unreadable_generated_manifest_is_not_called_a_stale_bump(tmp_path, capsys):
    """The exit code is 1 either way here, so the REASON is the whole test.

    A mutation that checks only the canonical side survived every exit-code
    assertion in this file, because an unreadable generated manifest also fails
    the plain `got != want` comparison and lands on exit 1 regardless. What it
    loses is the diagnosis: it tells you the version was bumped without
    regenerating, which sends you to run the generator on a file that cannot be
    parsed. Wrong instruction, confidently given.
    """
    _plugin(tmp_path, "1.0.0", "1.0.0")
    (tmp_path / "kimi.plugin.json").write_text("{ not json\n")
    assert parity.main(["--root", str(tmp_path), "--require-plugins", "1"]) == 1
    err = capsys.readouterr().err
    assert "no readable version to compare" in err
    assert "version bumped without regenerating" not in err


@pytest.mark.parametrize("required", [1, 60])
def test_live_estate_is_in_parity(required):
    """The real estate, which this session brought to 0 drift."""
    root = Path(__file__).resolve().parents[1]
    if not (root / "interverse").is_dir():
        pytest.skip("interverse/ not materialised in this checkout")
    assert parity.main(["--estate", str(root), "--require-plugins", str(required)]) == 0


# ---------------------------------------------------------------------------
# The freshness guard: how old the evidence is, and whether it may be used to
# accuse a plugin of drift.
#
# WHY THESE EXIST
#
# behind_remote() shipped with no test at all, and both of its defects were the
# kind a test written from the docstring would have caught:
#
#   1. It was CALLED ONLY when kimi.plugin.json was missing. The far more common
#      shape — the file present, its version behind a bumped plugin.json because
#      the checkout has not pulled the regeneration — never reached the guard.
#      That is the interlore case on 2026-08-07: fixed on the remote on 08-03,
#      reported as drift on Clavain, clean on zklw, and read at the time as a
#      coverage gap between the machines.
#
#   2. It compared against @{upstream} WITHOUT FETCHING, and returned the plain
#      integer 0 for "level with the remote", for "no upstream", and for "git
#      failed". On a clone that last fetched five weeks ago the comparison is
#      between two local pointers and the remote is not consulted at all.
#      Measured: 55 of 70 Clavain checkouts reported "0 behind" on fetch data
#      older than seven days, twelve having never fetched; zklw had 65 of 66
#      within the week. Same integer from both machines.
#
# These build real git repositories rather than monkeypatching, because the bug
# was in what git was actually asked and when.
# ---------------------------------------------------------------------------

def _run(*args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True,
                   capture_output=True, text=True)


def _repo(path: Path, canonical: str, generated: str | None):
    """A plugin repo with an origin it tracks, and one commit on both sides."""
    path.parent.mkdir(parents=True, exist_ok=True)
    origin = path.parent / (path.name + ".origin.git")
    _run("git", "init", "--quiet", "--bare", "-b", "main", str(origin),
         cwd=path.parent)
    path.mkdir(parents=True, exist_ok=True)
    _run("git", "init", "--quiet", "-b", "main", ".", cwd=path)
    _run("git", "config", "user.email", "t@example.invalid", cwd=path)
    _run("git", "config", "user.name", "t", cwd=path)
    _run("git", "config", "commit.gpgsign", "false", cwd=path)
    _plugin(path, canonical, generated)
    _run("git", "add", "-A", cwd=path)
    _run("git", "commit", "--quiet", "-m", "init", cwd=path)
    _run("git", "remote", "add", "origin", str(origin), cwd=path)
    _run("git", "push", "--quiet", "-u", "origin", "main", cwd=path)
    return path


def _fetch_age(path: Path, days: float | None):
    """Set, or erase, this repo's record of when it last contacted its remote."""
    common = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-common-dir"],
        capture_output=True, text=True, check=True).stdout.strip()
    p = Path(common)
    if not p.is_absolute():
        p = path / p
    head = p / "FETCH_HEAD"
    if days is None:
        head.unlink(missing_ok=True)
        return
    head.touch()
    when = time.time() - days * 86400
    os.utime(head, (when, when))


def _advance_remote(path: Path):
    """Put a commit on the origin that `path` has not seen, and let it notice."""
    origin = path.parent / (path.name + ".origin.git")
    other = path.parent / (path.name + ".other")
    _run("git", "clone", "--quiet", str(origin), str(other), cwd=path.parent)
    _run("git", "config", "user.email", "t@example.invalid", cwd=other)
    _run("git", "config", "user.name", "t", cwd=other)
    _run("git", "config", "commit.gpgsign", "false", cwd=other)
    (other / "NOTE").write_text("moved on\n")
    _run("git", "add", "-A", cwd=other)
    _run("git", "commit", "--quiet", "-m", "remote moves", cwd=other)
    _run("git", "push", "--quiet", "origin", "main", cwd=other)
    _run("git", "fetch", "--quiet", "origin", cwd=path)


def _estate(root: Path):
    """--estate walks os/Clavain and interverse/*; give it one real plugin."""
    (root / "interverse").mkdir(parents=True, exist_ok=True)
    return root / "interverse" / "alpha"


# --- blind spot 1: the guard was wired to the wrong branch -----------------

def test_a_present_but_stale_manifest_is_not_called_drift(tmp_path, capsys):
    """THE INTERLORE SHAPE, and the one the shipped guard could not see.

    kimi.plugin.json is present and its version trails a bumped plugin.json.
    That is what a stale checkout looks like after someone else regenerated and
    pushed — and it is also what real drift looks like, which is the whole reason
    the freshness of the checkout has to decide between them.

    The shipped code consulted the remote only under `if not generated.is_file()`,
    so this path reached `got != want` and reported DRIFT without ever asking
    whether this clone was entitled to an opinion.
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _advance_remote(plugin)  # now genuinely behind its remote

    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 2
    err = capsys.readouterr().err
    assert "STALE" in err
    assert "behind its remote" in err
    # The accusation it withheld is named, not merely withheld.
    assert "version bumped without regenerating" in err
    assert "DRIFT" not in err


def test_a_missing_manifest_on_a_stale_checkout_is_still_guarded(tmp_path):
    """The one branch that was wired correctly. It must stay wired."""
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.3", None)
    _advance_remote(plugin)
    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 2


def test_an_unreadable_manifest_on_a_stale_checkout_is_not_convicted(tmp_path):
    """A deliberate change of position, recorded because the old one was argued.

    The previous comment routed unreadable manifests to DRIFT on the grounds that
    a corrupt file "travels with the repo, and pulling will not fix it". That is
    true of a file corrupt on the remote and false of one corrupt only here — a
    truncated checkout, an interrupted write, a file the remote has since
    repaired. The check cannot tell those apart without looking at the remote,
    and looking is exactly what a stale clone cannot do. So the rule is now
    uniform: no accusation of any kind rests on evidence this checkout cannot
    stand behind.
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.0.0", "1.0.0")
    (plugin / "kimi.plugin.json").write_text("{ not json\n")
    _advance_remote(plugin)
    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 2


# --- blind spot 2: "0 behind" from a ref nobody refreshed ------------------

def test_zero_behind_from_a_month_old_ref_is_not_evidence(tmp_path, capsys):
    """The defect that made 2026-08-07 unreadable.

    Nothing here fetches, so `HEAD..@{upstream}` compares two local pointers.
    This repo is level with the remote-tracking ref it happens to hold, and that
    ref was last refreshed 35 days ago — the measured age of interdoc, interdeep,
    interfluence and 41 others on Clavain. The old code returned 0 and the caller
    read 0 as "up to date".
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _fetch_age(plugin, 35.0)

    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 2
    err = capsys.readouterr().err
    assert "STALE" in err
    assert "35d ago" in err


def test_never_fetched_is_not_the_same_as_up_to_date(tmp_path, capsys):
    """Twelve Clavain checkouts have no FETCH_HEAD at all."""
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _fetch_age(plugin, None)

    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 2
    assert "never fetched" in capsys.readouterr().err


def test_a_fresh_checkout_still_convicts(tmp_path, capsys):
    """THE TEST THAT STOPS THE FIX FROM BEING A MUTE BUTTON.

    Every assertion above turns a finding into a refusal, and a guard that
    refuses unconditionally would satisfy all of them while reporting nothing
    ever again. Same drift, same code path, a clone that fetched an hour ago:
    exit 1, DRIFT, no STALE.
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _fetch_age(plugin, 1.0 / 24)

    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 1
    err = capsys.readouterr().err
    assert "DRIFT" in err
    assert "STALE" not in err


def test_the_threshold_is_the_thing_being_tested(tmp_path):
    """Same repo, same drift; only --max-fetch-age-days moves."""
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _fetch_age(plugin, 10.0)

    assert parity.main(["--estate", str(root), "--require-plugins", "1",
                        "--max-fetch-age-days", "7"]) == 2
    assert parity.main(["--estate", str(root), "--require-plugins", "1",
                        "--max-fetch-age-days", "30"]) == 1


# --- the guard must not disable the check where it is enforced -------------

def test_root_mode_convicts_on_a_detached_head(tmp_path, capsys):
    """CI's shape, and the reason the guard is estate-only.

    A plugin repo's CI checks out a detached HEAD, where @{upstream} does not
    resolve. If "cannot resolve upstream" meant "cannot judge" everywhere, the
    pre-commit hook and every plugin CI would go quiet — exiting 0 forever while
    inspecting a tree it had decided not to have an opinion about. In --root mode
    the checkout is the subject, not a stand-in for one, so it is judged.
    """
    plugin = _repo(tmp_path / "solo", "1.2.4", "1.2.3")
    sha = subprocess.run(["git", "-C", str(plugin), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    _run("git", "checkout", "--quiet", "--detach", sha, cwd=plugin)
    _fetch_age(plugin, None)

    assert parity.main(["--root", str(plugin), "--require-plugins", "1"]) == 1
    assert "DRIFT" in capsys.readouterr().err


def test_a_directory_that_is_not_a_repo_is_judged_on_its_files(tmp_path):
    """No git, no remote, nothing that could be stale — so decide."""
    root = tmp_path / "estate"
    _plugin(_estate(root), "1.2.4", "1.2.3")
    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 1


# --- reporting the staleness rather than assuming it -----------------------

def test_a_pass_says_how_old_the_evidence_behind_it_is(tmp_path, capsys):
    """A green run on unrefreshed clones must not read like a green run.

    The manifests agree, so there is no accusation to withhold and the verdict
    stays 0 — a stale clone produces a coverage limit here, not a false charge.
    But the run rests on data nobody refreshed, and the summary line is what
    rig-report.sh publishes to the health record, so that is where it has to be
    said. On Clavain this is 55 of 70.
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.3", "1.2.3")
    _fetch_age(plugin, 40.0)

    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 0
    out = capsys.readouterr().out
    assert "parity ok: 1 plugin(s)" in out
    assert "1 of 1 judged on remote data this checkout cannot vouch for" in out
    # The clause names all three states it covers. Measured on Clavain, this
    # count was 65: 44 stale fetches, 12 never fetched, 9 known-behind and 1 with
    # no upstream. An earlier version of this line attributed all 65 to fetch
    # age, which was false for ten of them.
    assert "behind, or no upstream" in out


def test_a_fresh_pass_claims_nothing_extra(tmp_path, capsys):
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.3", "1.2.3")
    _fetch_age(plugin, 0.5)

    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("parity ok: 1 plugin(s)")


def test_every_exit_path_leaves_a_summary_on_stdout(tmp_path, capsys):
    """rig-report.sh publishes `tail -1` of stdout as the health summary.

    Before this, only the exit-0 path printed to stdout, so a run that found
    drift or refused to judge handed the health record whatever happened to be
    there. estate-drift lost its verdict to exactly this and published a sentence
    about bead housekeeping instead.
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _fetch_age(plugin, 0.1)
    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 1
    assert "out of parity" in capsys.readouterr().out.strip().splitlines()[-1]

    _fetch_age(plugin, 90.0)
    assert parity.main(["--estate", str(root), "--require-plugins", "1"]) == 2
    assert "unassessable" in capsys.readouterr().out.strip().splitlines()[-1]

    assert parity.main(["--estate", str(root), "--require-plugins", "99"]) == 2
    assert "below the floor" in capsys.readouterr().out.strip().splitlines()[-1]


def test_the_floor_outranks_a_refusal_to_judge(tmp_path, capsys):
    """Both return 2; which reason is printed is the point.

    When one plugin was found where sixty were required, the useful sentence is
    that coverage collapsed — not that the single plugin found was too stale to
    judge. check-workflow-health.py orders these the same way.
    """
    root = tmp_path / "estate"
    plugin = _repo(_estate(root), "1.2.4", "1.2.3")
    _fetch_age(plugin, 90.0)
    assert parity.main(["--estate", str(root), "--require-plugins", "60"]) == 2
    err = capsys.readouterr().err
    assert "required at least 60" in err
    assert "CANNOT ASSESS" not in err


def test_a_confirmed_finding_is_not_buried_by_a_majority_of_gaps(tmp_path, capsys):
    """One drift that is certain, two plugins nobody can judge.

    Written this way round on purpose. The obvious version of this test — two
    convictable and one stale — cannot tell the old rule from the new one: the
    old `len(unassessable) > len(drift)` is false at 1 > 2, so it falls through
    to the same exit 1 the new code reaches directly, and the assertion passes
    against both. It looks like coverage and is not.

    Inverting the ratio is what separates them. At 2 > 1 the old rule returned 2,
    CANNOT ASSESS, and the confirmed finding vanished behind a caveat about
    OTHER plugins — a plugin proven out of parity, on a checkout fresh enough to
    prove it, downgraded to "could not tell" by the arithmetic of its neighbours.
    Now the finding is reported and the gaps are reported alongside it.
    """
    root = tmp_path / "estate"
    fresh = _repo(root / "interverse" / "a", "1.0.1", "1.0.0")
    stale_b = _repo(root / "interverse" / "b", "2.0.1", "2.0.0")
    stale_c = _repo(root / "interverse" / "c", "3.0.1", "3.0.0")
    _fetch_age(fresh, 0.1)
    _fetch_age(stale_b, 99.0)
    _fetch_age(stale_c, 99.0)

    assert parity.main(["--estate", str(root), "--require-plugins", "3"]) == 1
    err = capsys.readouterr().err
    assert "DRIFT  a" in err
    # Neither gap is silently absorbed into the finding.
    assert "STALE  b" in err
    assert "STALE  c" in err


# --- remote_evidence() as a unit -------------------------------------------

def test_evidence_separates_cannot_tell_from_up_to_date(tmp_path):
    """The conflation that started all of this.

    behind_remote() returned the int 0 for both. These are the two states, and
    they must not compare equal.
    """
    level = _repo(tmp_path / "level", "1.0.0", "1.0.0")
    _fetch_age(level, 0.1)
    good = parity.remote_evidence(level, 7.0)
    assert good.trustworthy and good.behind == 0

    orphan = _repo(tmp_path / "orphan", "1.0.0", "1.0.0")
    _run("git", "checkout", "--quiet", "-b", "local-only", cwd=orphan)
    blind = parity.remote_evidence(orphan, 7.0)
    assert not blind.trustworthy
    assert blind.behind is None
    assert "remote-tracking" in blind.reason


def test_evidence_reports_the_age_it_used(tmp_path):
    plugin = _repo(tmp_path / "aged", "1.0.0", "1.0.0")
    _fetch_age(plugin, 12.0)
    ev = parity.remote_evidence(plugin, 7.0)
    assert not ev.trustworthy
    assert ev.fetch_age_days is not None
    assert 11.9 < ev.fetch_age_days < 12.1


def test_a_worktree_reads_the_common_dir_for_its_fetch_record(tmp_path):
    """FETCH_HEAD lives in the common dir, not the worktree's own .git file.

    Sylveste's own estate work runs from `bd worktree` checkouts, so resolving
    this wrongly would report every worktree as never-fetched — a whole machine
    turned unassessable by a path bug.
    """
    plugin = _repo(tmp_path / "main-wt", "1.0.0", "1.0.0")
    _fetch_age(plugin, 0.1)
    wt = tmp_path / "linked-wt"
    _run("git", "worktree", "add", "--quiet", str(wt), "-b", "wt", cwd=plugin)
    age = parity.last_fetch_age_days(wt)
    assert age is not None and age < 1.0
