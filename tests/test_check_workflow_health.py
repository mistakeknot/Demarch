"""Coverage for the estate workflow-health check.

This file did not exist until 2026-08-07, and the check had been running weekly
on zklw for a month without one. What it was missing is the reason it is here.

check-workflow-health had a vacuity guard, `--require-repos`, and the guard was
pointed at the wrong denominator: `len(repos)`, the directories on disk. The loop
underneath it skipped any repo the GitHub API would not answer for, and nothing
counted those skips. So a `gh` that was installed and on PATH but could not
authenticate produced a clean pass over nothing:

    0 repo(s) inspected: 0 disabled, 0 never ran
    exit 0

Measured with a planted `gh` on PATH that exits 1 for every call. The repos were
all still on disk, so the only number the guard could see was the one number that
could not go wrong.

Fixing that surfaced the second bug immediately, which is the better one: repo
names were assumed from directory names, and three of the estate's directories
disagree with their remote. Two of those 404 and had been silently skipped for as
long as the check existed. The third resolved to a REAL BUT DIFFERENT repo, so
the check had been reporting an abandoned repo's health as the live one's.

The tests below therefore care much more about verdicts than about formatting.
Every exit code this check can return has a test that makes it happen, and — the
part that matters — makes it happen for its own reason: a run that reached
nothing must not be able to borrow exit 0 from a run that reached everything and
found it healthy.
"""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_workflow_health",
    Path(__file__).resolve().parents[1] / "scripts" / "check-workflow-health.py",
)
wfh = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(wfh)

REPOS = [f"r{i:02d}" for i in range(1, 41)]
PAIRS = [(r, f"mistakeknot/{r}") for r in REPOS]

# Captured before the autouse fixture below replaces it, for the one test that
# is about estate_repos itself rather than about what main() does with it.
REAL_ESTATE_REPOS = wfh.estate_repos


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """No test here touches the network or the disk layout."""
    monkeypatch.setattr(wfh, "gh_installed", lambda: True)
    monkeypatch.setattr(wfh, "estate_repos", lambda root: list(PAIRS))


def _api(monkeypatch, unreachable=(), disabled=(), never=(), manual=()):
    """Install a gh_json that answers for every repo except the named ones."""
    def fn(path):
        repo = path.split("/")[2]          # repos/<owner>/<repo>/...
        if repo in unreachable:
            return None
        if "/runs" in path:
            return {"total_count": 0 if repo in (set(never) | set(manual)) else 3}
        state = "disabled_inactivity" if repo in disabled else "active"
        return {"workflows": [{"path": ".github/workflows/ci.yml",
                               "id": 1, "state": state}]}
    monkeypatch.setattr(wfh, "gh_json", fn)
    monkeypatch.setattr(
        wfh, "triggers",
        lambda slug, path: ({"workflow_dispatch"}
                            if slug.split("/")[-1] in manual else {"push"}))


def test_a_healthy_estate_passes(monkeypatch):
    _api(monkeypatch)
    assert wfh.main(["--require-repos", "30"]) == 0


def test_a_disabled_workflow_is_a_finding(monkeypatch):
    """The failure this check was written for: GitHub switched off secret-scan
    on 17 of 36 plugin repos after 60 days of inactivity."""
    _api(monkeypatch, disabled={"r07"})
    assert wfh.main(["--require-repos", "30"]) == 1


def test_a_workflow_that_never_ran_is_a_finding(monkeypatch):
    _api(monkeypatch, never={"r07"})
    assert wfh.main(["--require-repos", "30"]) == 1


def test_a_manual_only_workflow_is_reported_but_is_not_a_finding(monkeypatch):
    """Sylveste#62. A workflow_dispatch-only workflow has no trigger that could
    have fired, so `never ran` describes it accurately and accuses it wrongly."""
    _api(monkeypatch, manual={"r07"})
    assert wfh.main(["--require-repos", "30"]) == 0


def test_an_estate_that_answers_for_nothing_is_not_a_pass(monkeypatch):
    """THE BUG. Before the fix this returned 0 and said `0 repo(s) inspected`."""
    _api(monkeypatch, unreachable=set(REPOS))
    assert wfh.main(["--require-repos", "30"]) == 2


def test_reaching_fewer_repos_than_the_floor_is_not_a_pass(monkeypatch):
    """29 of 40 with the floor at 30 — the boundary, from the failing side."""
    _api(monkeypatch, unreachable=set(REPOS[:11]))
    assert wfh.main(["--require-repos", "30"]) == 2


def test_partial_coverage_above_the_floor_still_cannot_claim_the_estate(monkeypatch):
    """30 of 40 clears the floor and is still not a verdict on 40.

    Nothing wrong in the repos that answered is a different claim from nothing
    wrong in the estate, and exit 0 makes the second one.
    """
    _api(monkeypatch, unreachable=set(REPOS[:10]))
    assert wfh.main(["--require-repos", "30"]) == 2


def test_the_floor_outranks_a_finding_when_coverage_collapses(monkeypatch):
    """15 of 40 with a disabled workflow among them is still exit 2, not 1.

    This is the ONLY test that can tell the two floors apart, and it exists
    because a mutation proved the others could not. Every other scenario has
    `unreachable` non-empty, and the unreachable check returns 2 as well — so
    swapping the floor back to `len(repos)`, which IS the original bug, left the
    whole suite green. Here the mutation changes the answer: with the floor on
    the directory listing, 40 >= 30 passes, the finding is reported, and exit 1
    claims a verdict drawn from a third of the estate.

    Order matters and this pins it: a finding you cannot situate is not a
    verdict. 25 unreachable repos might hold twenty more of the same.
    """
    _api(monkeypatch, unreachable=set(REPOS[:25]), disabled={"r30"})
    assert wfh.main(["--require-repos", "30"]) == 2


def test_one_unresolvable_checkout_is_enough_to_withhold_a_verdict(monkeypatch):
    """40 healthy repos plus a single orphan is not an all-clear.

    Also written because a mutation survived: the earlier orphan test put the
    floor exactly at the repo count, so dropping the orphan failed the floor
    instead of failing the thing under test. Here coverage clears the floor
    easily, so the orphan is the only reason the verdict is withheld.
    """
    monkeypatch.setattr(wfh, "estate_repos",
                        lambda root: PAIRS + [("orphan", None)])
    _api(monkeypatch)
    assert wfh.main(["--require-repos", "30"]) == 2


def test_a_finding_stands_despite_partial_coverage(monkeypatch):
    """A disabled workflow is disabled whether or not some other repo answered.

    This is the one case where partial coverage must NOT win: downgrading a real
    finding to `could not assess` because an unrelated repo timed out would hide
    the thing the check exists to find.
    """
    _api(monkeypatch, unreachable=set(REPOS[:5]), disabled={"r09"})
    assert wfh.main(["--require-repos", "30"]) == 1


def test_no_gh_binary_is_could_not_run(monkeypatch):
    monkeypatch.setattr(wfh, "gh_installed", lambda: False)
    assert wfh.main(["--require-repos", "30"]) == 2


def test_a_partial_checkout_is_refused_before_any_api_call(monkeypatch):
    """The other floor, against the other denominator: too few repos on disk."""
    monkeypatch.setattr(wfh, "estate_repos", lambda root: PAIRS[:2])

    def explode(path):
        raise AssertionError("must not call the API on a partial checkout")

    monkeypatch.setattr(wfh, "gh_json", explode)
    assert wfh.main(["--require-repos", "30"]) == 2


def test_a_checkout_with_no_resolvable_remote_is_unreachable_not_absent(monkeypatch):
    """Slug None must surface, not vanish.

    Dropping it from the list would put the check straight back into the state
    this file exists to document: a repo that is neither inspected nor counted
    against the coverage it claims.
    """
    monkeypatch.setattr(wfh, "estate_repos",
                        lambda root: PAIRS[:39] + [("orphan", None)])
    _api(monkeypatch)
    assert wfh.main(["--require-repos", "40"]) == 2


def test_a_repo_is_inspected_under_its_slug_not_its_directory_name(monkeypatch):
    """`interverse/intersite` pushes to `mistakeknot/interverse-intersite`.

    `mistakeknot/intersite` also exists — a different, abandoned repo — so an
    inspection keyed on the directory name got a confident answer about the
    wrong subject. The assertion is on the URL, because the failure mode here
    produces a perfectly healthy-looking verdict.
    """
    asked = []

    def fn(path):
        asked.append(path)
        return {"workflows": []}

    monkeypatch.setattr(wfh, "gh_json", fn)
    monkeypatch.setattr(wfh, "estate_repos",
                        lambda root: [("intersite", "mistakeknot/interverse-intersite")])
    wfh.main([])
    assert asked == ["repos/mistakeknot/interverse-intersite/actions/workflows"]
    assert not any("repos/mistakeknot/intersite/" in p for p in asked)


def test_a_differing_slug_is_shown_alongside_the_directory_name(monkeypatch, capsys):
    """Because the reader cannot check what the reader cannot see."""
    monkeypatch.setattr(
        wfh, "estate_repos",
        lambda root: [("lattice", "mistakeknot/interweave")])
    monkeypatch.setattr(wfh, "gh_json", lambda path: None)
    wfh.main([])
    assert "lattice (mistakeknot/interweave)" in capsys.readouterr().out


@pytest.mark.parametrize("url,want", [
    ("https://github.com/mistakeknot/interweave.git", "mistakeknot/interweave"),
    ("https://github.com/mistakeknot/interweave", "mistakeknot/interweave"),
    ("git@github.com:mistakeknot/interweave.git", "mistakeknot/interweave"),
    ("ssh://git@github.com/mistakeknot/interweave.git", "mistakeknot/interweave"),
])
def test_origin_slug_parses_the_url_forms_git_actually_emits(monkeypatch, url, want):
    class R:
        returncode = 0
        stdout = url + "\n"

    monkeypatch.setattr(wfh.subprocess, "run", lambda *a, **k: R())
    assert wfh.origin_slug(Path("/nowhere")) == want


def test_a_relative_root_still_yields_a_named_repo(monkeypatch, tmp_path):
    """Path(".").name is the empty string, and `--root .` is an ordinary call.

    Unresolved, the monorepo's own entry printed with a blank label — which
    reads as a formatting glitch rather than as the missing name it is.
    """
    monkeypatch.setattr(wfh, "origin_slug", lambda p: "mistakeknot/Sylveste")
    monkeypatch.chdir(tmp_path)
    labels = [label for label, _ in REAL_ESTATE_REPOS(Path("."))]
    assert labels == [tmp_path.resolve().name]
    assert "" not in labels


def test_origin_slug_is_none_when_git_cannot_answer(monkeypatch):
    class R:
        returncode = 128
        stdout = ""

    monkeypatch.setattr(wfh.subprocess, "run", lambda *a, **k: R())
    assert wfh.origin_slug(Path("/nowhere")) is None


def test_the_summary_says_how_many_of_how_many(monkeypatch, capsys):
    """The gap between reached and expected is the fact a reader most needs.

    The old wording had no room to say it: `0 repo(s) inspected` reads as a
    complete sentence about a healthy estate if you are skimming.
    """
    _api(monkeypatch, unreachable=set(REPOS[:10]))
    wfh.main(["--require-repos", "30"])
    assert "30 of 40 repo(s) inspected" in capsys.readouterr().out


def test_the_unreachable_list_is_capped(monkeypatch, capsys):
    """A dead token makes every repo unreachable at once, and 40 identical lines
    bury the summary that explains why."""
    _api(monkeypatch, unreachable=set(REPOS))
    wfh.main(["--require-repos", "30"])
    out = capsys.readouterr().out
    assert out.count("UNREACHED") <= 9          # 8 names plus the elision line
    assert "and 32 more" in out
