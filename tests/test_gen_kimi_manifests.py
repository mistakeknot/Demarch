"""Coverage for gen-kimi-manifests.py's asset-directory resolution.

The generator probed only <plugin>/skills and <plugin>/commands, so any plugin
keeping its assets elsewhere had them silently dropped from the generated Kimi
manifest. Two plugins do: tldr-swinton (4 skills, 6 commands) and interpub
(1 command), both under .claude-plugin/. Nothing reported it — an omitted
optional key is indistinguishable from a plugin that has none, which is why
tldr-swinton's upstream manifest had been hand-corrected and then read as
"diverged from the generator" rather than "the generator is wrong".
"""

import importlib.util
import json
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "gen_kimi_manifests",
    Path(__file__).resolve().parents[1] / "scripts" / "gen-kimi-manifests.py",
)
gen = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gen)


@pytest.fixture
def report():
    return {"notes": [], "errors": []}


def _skill(root: Path, rel: str):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("# skill\n")
    return d


def test_declared_non_default_skills_dir_is_emitted(tmp_path, report):
    """The tldr-swinton shape: individual skills under .claude-plugin/skills/."""
    _skill(tmp_path, ".claude-plugin/skills/alpha")
    _skill(tmp_path, ".claude-plugin/skills/beta")
    manifest = {
        "skills": ["./.claude-plugin/skills/alpha", "./.claude-plugin/skills/beta"]
    }

    assert gen.resolve_asset_dir(tmp_path, manifest, "skills", report) == (
        "./.claude-plugin/skills/"
    )


def test_declared_non_default_commands_dir_is_emitted(tmp_path, report):
    """The interpub shape: a command .md under .claude-plugin/commands/."""
    d = tmp_path / ".claude-plugin" / "commands"
    d.mkdir(parents=True)
    (d / "release.md").write_text("# release\n")
    manifest = {"commands": ["./.claude-plugin/commands/release.md"]}

    assert gen.resolve_asset_dir(tmp_path, manifest, "commands", report) == (
        "./.claude-plugin/commands/"
    )


def test_leading_dot_in_dirname_survives(tmp_path, report):
    """Regression: lstrip("./") strips a CHARACTER SET, not a prefix.

    It turned "./.claude-plugin/skills" into "claude-plugin/skills", eating the
    leading dot and resolving to a path that does not exist — so the fix
    silently did nothing and reported "declared directory does not exist".
    """
    _skill(tmp_path, ".claude-plugin/skills/alpha")
    manifest = {"skills": ["./.claude-plugin/skills/alpha"]}

    got = gen.resolve_asset_dir(tmp_path, manifest, "skills", report)
    assert got == "./.claude-plugin/skills/"
    assert "claude-plugin" not in (got or "").replace(".claude-plugin", "")


def test_single_skill_directly_in_skills_dir_emits_nothing(tmp_path, report):
    """The intermap shape: skills/SKILL.md, not skills/<name>/SKILL.md.

    The declared entry resolves to the plugin root, and emitting "././" would
    point Kimi at the whole plugin. The convention probe rejects this layout,
    and the declared path must not override that.
    """
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "SKILL.md").write_text("# skill\n")
    manifest = {"skills": ["./skills"]}

    assert gen.resolve_asset_dir(tmp_path, manifest, "skills", report) is None


def test_conventional_layout_still_uses_the_probe(tmp_path, report):
    """A declaration pointing at the default dir must not change the answer.

    This function exists only to stop NON-default locations being dropped;
    anything broader would silently alter the manifests already correct.
    """
    _skill(tmp_path, "skills/alpha")

    declared = gen.resolve_asset_dir(tmp_path, {"skills": ["./skills/alpha"]}, "skills", report)
    undeclared = gen.resolve_asset_dir(tmp_path, {}, "skills", report)
    assert declared == undeclared == "./skills/"


def test_paths_spanning_several_dirs_are_omitted_with_a_note(tmp_path, report):
    """Kimi accepts one directory; an arbitrary pick would look authoritative."""
    _skill(tmp_path, "here/alpha")
    _skill(tmp_path, "there/beta")
    manifest = {"skills": ["./here/alpha", "./there/beta"]}

    assert gen.resolve_asset_dir(tmp_path, manifest, "skills", report) is None
    assert any("span" in n for n in report["notes"])


def test_declared_directory_that_does_not_exist_is_reported(tmp_path, report):
    manifest = {"commands": ["./nowhere/cmd.md"]}

    assert gen.resolve_asset_dir(tmp_path, manifest, "commands", report) is None
    assert any("does not exist" in n for n in report["notes"])


def test_no_declaration_and_no_directory_emits_nothing(tmp_path, report):
    assert gen.resolve_asset_dir(tmp_path, {}, "skills", report) is None
    assert gen.resolve_asset_dir(tmp_path, {}, "commands", report) is None


def test_skills_dir_with_no_skill_subdirs_emits_nothing(tmp_path, report):
    """Preserves the pre-existing convention test: a collection needs members."""
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "notes.md").write_text("not a skill\n")

    assert gen.resolve_asset_dir(tmp_path, {}, "skills", report) is None


def test_real_estate_has_no_manifest_pointing_at_the_plugin_root(tmp_path):
    """Guard against re-introducing the "././" bug across the live estate."""
    root = Path(__file__).resolve().parents[1]
    bad = []
    for manifest_path in sorted(root.glob("interverse/*/kimi.plugin.json")):
        data = json.loads(manifest_path.read_text())
        for key in ("skills", "commands"):
            value = data.get(key)
            if value and value.strip("./") in ("", "."):
                bad.append(f"{manifest_path.parent.name}:{key}={value}")
    assert not bad, f"manifests pointing at the plugin root: {bad}"
