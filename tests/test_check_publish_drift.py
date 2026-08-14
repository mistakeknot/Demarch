"""Coverage for publish-drift's vendored-upstream class.

Why this file exists
--------------------
`vendored-behind` is a DOWNGRADE: it takes a plugin out of the set that fails the
check. That makes misclassification the expensive direction — calling something
vendored when it is ours would silence real unshipped work, and it would do so
while the summary line still looked healthy. So the parsing that decides
ownership is unit-tested against every URL form the marketplace actually carries,
and the fail-safe (an unparseable URL is OURS, never vendored) is asserted rather
than assumed.

The end-to-end pair is the load-bearing test. It reproduces the bug the class was
built for: on 2026-08-14 canongraph read `clean` on Clavain from a local clone 234
commits stale, and `drift, 38 commits` on zklw from the source mirror — the same
committed code, two hosts, two verdicts. Here one fixture is audited twice,
differing only in whether its org counts as ours, and the two verdicts must
differ: `clean` from the local clone when it is ours, `vendored-behind` from the
mirror when it is not. If vendored resolution ever silently fell back to a local
checkout, that second assertion is what notices.

No network: `mirror()` clones by URL and a filesystem path is a valid git URL, so
the mirror path exercised here is the real one.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_publish_drift",
    Path(__file__).resolve().parents[1] / "scripts" / "check-publish-drift.py",
)
assert _SPEC and _SPEC.loader
pd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pd)


# --------------------------------------------------------------------------
# ownership parsing
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url,org",
    [
        ("https://github.com/mistakeknot/interpath.git", "mistakeknot"),
        ("https://github.com/jvattimo1/canongraph.git", "jvattimo1"),
        ("http://github.com/gensysven/interjawn", "gensysven"),
        ("git@github.com:mistakeknot/clavain.git", "mistakeknot"),
        ("ssh://git@github.com/jvattimo1/canongraph.git", "jvattimo1"),
        ("git://github.com/someone/thing.git", "someone"),
        ("https://user:token@github.com/mistakeknot/x.git", "mistakeknot"),
        # Names no org: too few path components to place one.
        ("https://example.com/onlyrepo", ""),
        ("", ""),
        ("not a url", ""),
    ],
)
def test_source_org_parses_every_form_the_marketplace_carries(url, org):
    assert pd.source_org(url) == org


def test_is_vendored_is_case_insensitive_on_the_org():
    # Forge orgs are not case-sensitive, and a marketplace entry written
    # "MistakeKnot" must not read as somebody else's repository.
    assert not pd.is_vendored("https://github.com/MistakeKnot/x.git", ("mistakeknot",))
    assert not pd.is_vendored("https://github.com/mistakeknot/x.git", ("MistakeKnot",))


def test_an_unparseable_source_is_ours_not_vendored():
    """The fail-safe, asserted.

    Vendored is the lenient verdict, so a URL nobody can parse must fall on the
    strict side. The opposite default would let a malformed marketplace entry
    downgrade a real drift to a line nobody has to act on.
    """
    for url in ("", "not a url", "https://example.com/onlyrepo"):
        assert pd.is_vendored(url, ("mistakeknot",)) is False


def test_own_org_list_is_honoured_beyond_the_default():
    assert pd.is_vendored("https://github.com/acme/x.git", ("mistakeknot",))
    assert not pd.is_vendored("https://github.com/acme/x.git", ("mistakeknot", "acme"))


# --------------------------------------------------------------------------
# end to end
# --------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(repo),
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


def _init(repo: Path) -> None:
    # --initial-branch pinned, and the global config neutralised above: a fixture
    # that reads host git config cannot diverge between hosts. resolve_tip only
    # looks for main/master, so an inherited default would decide whether this
    # test can see history at all.
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main", str(repo)],
                   check=True, capture_output=True)


def _write(repo: Path, rel: str, body: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _manifest(repo: Path, name: str, version: str) -> None:
    _write(repo, ".claude-plugin/plugin.json",
           json.dumps({"name": name, "version": version}) + "\n")


@pytest.fixture
def fixture(tmp_path):
    """A plugin whose UPSTREAM is two shipped-surface commits past the published
    bump, and whose LOCAL checkout sits exactly at it and is clean."""
    published = "1.0.0"

    upstream_work = tmp_path / "up-work"
    _init(upstream_work)
    _manifest(upstream_work, "foo", published)
    _write(upstream_work, "hooks/run.sh", "one\n")
    _git(upstream_work, "add", "-A")
    _git(upstream_work, "commit", "-qm", "bump to 1.0.0")
    for n in ("two", "three"):
        _write(upstream_work, "hooks/run.sh", n + "\n")
        _git(upstream_work, "add", "-A")
        _git(upstream_work, "commit", "-qm", f"upstream change {n}")

    bare = tmp_path / "up.git"
    subprocess.run(["git", "clone", "--bare", "--quiet",
                    str(upstream_work), str(bare)], check=True, capture_output=True)

    # An independent repo at the published version, not a clone reset backwards:
    # nothing here needs the two histories to share SHAs, and this keeps the
    # fixture free of any history-rewriting verb.
    root = tmp_path / "local"
    local = root / "foo"
    _init(local)
    _manifest(local, "foo", published)
    _write(local, "hooks/run.sh", "one\n")
    _git(local, "add", "-A")
    _git(local, "commit", "-qm", "bump to 1.0.0")

    marketplace = tmp_path / "marketplace.json"
    marketplace.write_text(json.dumps({
        "plugins": [{"name": "foo", "version": published,
                     "source": {"url": str(bare)}}]
    }))
    return {"marketplace": marketplace, "root": root, "cache": tmp_path / "cache",
             "url": str(bare), "published": published}


def _run(fixture, own_org, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "check-publish-drift.py",
        "--marketplace", str(fixture["marketplace"]),
        "--root", str(fixture["root"]),
        "--cache-dir", str(fixture["cache"]),
        "--own-org", own_org,
        "--json",
    ])
    rc = pd.main()
    return rc, json.loads(capsys.readouterr().out)["foo"]


def test_ours_is_audited_from_the_local_checkout_and_is_clean(fixture, monkeypatch, capsys):
    # The org derived from the fixture's own URL, declared ours. Derived rather
    # than hardcoded because the path depends on the tmpdir.
    ours = pd.source_org(fixture["url"])
    assert ours, "fixture URL must yield an org for this test to mean anything"
    rc, r = _run(fixture, ours, monkeypatch, capsys)
    assert r["source"] == "local"
    assert r["status"] == "clean"
    assert not r.get("vendored")
    assert rc == 0


def test_vendored_is_audited_from_the_mirror_and_reports_behind(fixture, monkeypatch, capsys):
    """The same fixture, the same committed code, one bit changed.

    This is the cross-machine bug as a unit test: a clean local checkout is
    present and must NOT be what answers. If vendored resolution ever fell back
    to it, `source` would read "local" and `status` "clean" — exactly the pair
    Clavain reported for canongraph while zklw reported drift.
    """
    _rc, r = _run(fixture, "somebody-else", monkeypatch, capsys)
    assert r["vendored"] is True
    assert r["source"] == "mirror", "a stale local clone must not answer for an upstream we do not write to"
    assert r["status"] == "vendored-behind"
    assert r["count"] == 2
    assert r["upstream"] == fixture["url"]


def test_vendored_behind_does_not_fail_the_check(fixture, monkeypatch, capsys):
    """It is reported in full, and it does not turn the check red.

    No publish closes an upstream we do not write to, so failing on it would make
    publish-drift red every morning for a reason nobody here can act on — and
    take the real drifts down with it.
    """
    rc, r = _run(fixture, "somebody-else", monkeypatch, capsys)
    assert r["status"] == "vendored-behind"
    assert rc == 0


def test_a_real_drift_still_fails_alongside_a_vendored_one(fixture, monkeypatch, capsys):
    """The downgrade must not be contagious.

    A vendored entry going quiet is only correct if an OWN entry in the same run
    still fails. Otherwise the change traded four true positives for one.
    """
    # Add a second plugin, ours, drifted: its local checkout is behind its own
    # committed source, which is what `drift` means.
    root = fixture["root"]
    mine = root / "bar"
    _init(mine)
    _manifest(mine, "bar", "2.0.0")
    _write(mine, "hooks/run.sh", "one\n")
    _git(mine, "add", "-A")
    _git(mine, "commit", "-qm", "bump to 2.0.0")
    _write(mine, "hooks/run.sh", "two\n")
    _git(mine, "add", "-A")
    _git(mine, "commit", "-qm", "unshipped change")

    mp = json.loads(fixture["marketplace"].read_text())
    mp["plugins"].append({"name": "bar", "version": "2.0.0",
                          "source": {"url": "https://github.com/mistakeknot/bar.git"}})
    fixture["marketplace"].write_text(json.dumps(mp))

    monkeypatch.setattr(sys, "argv", [
        "check-publish-drift.py",
        "--marketplace", str(fixture["marketplace"]),
        "--root", str(root),
        "--cache-dir", str(fixture["cache"]),
        "--own-org", "mistakeknot",
        "--json",
    ])
    rc = pd.main()
    out = json.loads(capsys.readouterr().out)

    assert out["foo"]["status"] == "vendored-behind"
    assert out["bar"]["status"] == "drift"
    assert rc == 1, "a vendored downgrade must not suppress a real drift in the same run"
