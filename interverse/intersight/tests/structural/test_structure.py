"""Validate intersight plugin structure against Interverse conventions."""
import json
from pathlib import Path


REQUIRED_ROOT_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "PHILOSOPHY.md",
    "README.md",
    "LICENSE",
    ".gitignore",
]

REQUIRED_DIRS = [
    ".claude-plugin",
    "skills",
    "scripts",
    "scripts/extraction",
    "tests",
    "tests/structural",
]

EXTRACTION_SCRIPTS = [
    "parseRobotsTxt.js",
    "contentHash.js",
    "extractCSSCustomProperties.js",
    "extractColorTokens.js",
    "extractTypography.js",
    "extractSpacing.js",
    "extractShadowsAndBorders.js",
    "extractBreakpoints.js",
    "extractComponentInventory.js",
]


def test_required_root_files(plugin_root):
    """All canonical root files must exist."""
    for name in REQUIRED_ROOT_FILES:
        assert (plugin_root / name).exists(), f"Missing required file: {name}"


def test_required_directories(plugin_root):
    """All expected directories must exist."""
    for d in REQUIRED_DIRS:
        assert (plugin_root / d).is_dir(), f"Missing required directory: {d}"


def test_plugin_json_valid(plugin_json):
    """plugin.json must have required fields."""
    assert plugin_json["name"] == "intersight"
    assert "version" in plugin_json
    assert "description" in plugin_json
    assert "skills" in plugin_json
    assert isinstance(plugin_json["skills"], list)
    assert len(plugin_json["skills"]) >= 1


def test_plugin_json_skills_paths(plugin_root, plugin_json):
    """Every skill path in plugin.json must resolve to a directory with SKILL.md.

    Skills paths in plugin.json are relative to the plugin root (parent of .claude-plugin/),
    not relative to plugin.json itself.
    """
    for skill_path in plugin_json["skills"]:
        resolved = (plugin_root / skill_path).resolve()
        assert resolved.is_dir(), f"Skill path does not resolve to directory: {skill_path} -> {resolved}"
        assert (resolved / "SKILL.md").exists(), f"Missing SKILL.md in {resolved}"


def test_bump_version_exists_and_executable(plugin_root):
    """bump-version.sh must exist and be executable."""
    bv = plugin_root / "scripts" / "bump-version.sh"
    assert bv.exists(), "Missing scripts/bump-version.sh"
    import os
    assert os.access(bv, os.X_OK), "scripts/bump-version.sh is not executable"


def test_extraction_scripts_exist(scripts_dir):
    """All 9 extraction scripts must exist."""
    for name in EXTRACTION_SCRIPTS:
        assert (scripts_dir / name).exists(), f"Missing extraction script: {name}"


def test_extraction_scripts_are_iife(scripts_dir):
    """Each JS extraction script must be an IIFE that returns JSON."""
    for name in EXTRACTION_SCRIPTS:
        content = (scripts_dir / name).read_text()
        stripped = content.strip()
        assert stripped.startswith("(() =>") or stripped.startswith("(function"), \
            f"{name} must be an IIFE (start with '(() =>' or '(function')"
        assert "JSON.stringify" in content, \
            f"{name} must return JSON (contain 'JSON.stringify')"


def test_schema_json_valid(scripts_dir):
    """schema.json must be valid JSON with DTCG structure."""
    schema_path = scripts_dir / "schema.json"
    assert schema_path.exists(), "Missing scripts/extraction/schema.json"
    data = json.loads(schema_path.read_text())
    assert "$schema" in data or "$extensions" in data, \
        "schema.json must have $schema or $extensions"
