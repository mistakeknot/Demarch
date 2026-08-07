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
