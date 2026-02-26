# Research: content-hash.py Helper Script

## Task

Create a Python script for computing deterministic SHA-256 content hashes from a project's key files, used by flux-drive to detect domain detection cache staleness.

## Files Created

- **Script**: `/home/mk/projects/Demarch/interverse/interflux/scripts/content-hash.py`
- **Tests**: `/home/mk/projects/Demarch/interverse/interflux/tests/structural/test_content_hash.py`

## Design Decisions

### File Discovery Strategy

The script discovers files in three categories, applied in order:

1. **README** -- checks `README.md`, `README.rst`, `README.txt`, `README` in priority order; includes only the first match.
2. **Build files** -- checks `package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `build.gradle`, `pom.xml`, `Makefile`, `CMakeLists.txt` in the project root.
3. **Key source files** -- scans `src/` and `lib/` directories (recursively), identifies the most common file extension among candidates, then takes the first 3 files (sorted by relative path) of that extension. Falls back to scanning the project root non-recursively if `src/`/`lib/` don't exist.

All discovered files are deduplicated by resolved path and sorted lexicographically by relative path for determinism.

### Hash Format

Files are concatenated with null-byte separators in this format:

```
<relative_path_1>\0<content_1>\0<relative_path_2>\0<content_2>...
```

The first file's pair has no leading separator. Each subsequent file is preceded by a single `\0` separator before its `<relative_path>\0<content>` pair. This ensures that the hash changes when files are renamed (path is part of the hash) or reordered (though ordering is deterministic).

Output format: `sha256:<64_hex_chars>`

### Binary File Detection

Two heuristics:
- **Size check**: files > 1MB are skipped.
- **Null byte check**: if the first 512 bytes of a file contain a `\x00` byte, it's treated as binary.

This is conservative -- it may skip valid UTF-16 encoded text files, but that's acceptable for the use case (project key files are overwhelmingly UTF-8).

### Exit Code Design

Follows the same convention as `generate-agents.py` and `detect-domains.py`:
- **0**: success (hash computed, or `--check` matched)
- **1**: no result (no hashable files found, or `--check` mismatched)
- **2**: fatal error (invalid path, I/O error, etc.)

### CLI Modes

1. **Default** (`content-hash.py <project_root>`): prints `sha256:<hex>` to stdout.
2. **JSON** (`--json`): prints `{"hash": "sha256:<hex>", "files": ["README.md", ...]}`.
3. **Check** (`--check <hash>`): compares computed hash against provided hash. Exit 0 if match, 1 if mismatch.
4. **Check + JSON** (`--check <hash> --json`): outputs `{"match": true/false, "hash": ..., "files": ...}` with appropriate exit code.

### Code Style Alignment

Matched existing patterns from the interflux scripts directory:
- `from __future__ import annotations` at top
- Same atomic write pattern (tempfile + rename) -- not needed for this script since it doesn't write files, but the code structure, docstrings, imports, and `main()` -> `SystemExit` pattern all match `generate-agents.py`.
- Same `argparse` conventions: `--json` stored as `json_output`, `type=Path` for project root.
- Same `if __name__ == "__main__"` exception-catching pattern.

## Test Coverage

25 tests across 6 test classes:

### TestComputeHash (4 tests)
- `test_hash_with_readme_and_build` -- verifies hash format (`sha256:` + 64 hex chars)
- `test_determinism` -- same files produce same hash across multiple calls
- `test_different_content_different_hash` -- different README content produces different hashes
- `test_file_order_is_deterministic` -- files are sorted by relative path

### TestDiscoverFiles (8 tests)
- `test_finds_readme_md` -- discovers README.md
- `test_finds_readme_rst` -- discovers README.rst when .md absent
- `test_finds_build_files` -- discovers package.json, Makefile
- `test_finds_source_files_from_src` -- finds up to 3 source files from src/
- `test_source_files_pick_dominant_extension` -- picks most common extension (3 .py vs 1 .go = picks .py)
- `test_empty_project` -- empty project returns no files
- `test_skips_binary_files` -- files with null bytes in first 512 bytes are skipped
- `test_skips_large_binary_files` -- files over 1MB are skipped
- `test_fallback_to_root_for_source` -- scans project root when src/lib absent

### TestJsonOutput (2 tests)
- `test_json_flag` -- valid JSON with hash and files keys
- `test_plain_output` -- default output is just hash string

### TestCheckMode (4 tests)
- `test_check_match` -- correct hash exits 0
- `test_check_mismatch` -- wrong hash exits 1
- `test_check_json_match` -- JSON output with match: true
- `test_check_json_mismatch` -- JSON output with match: false, expected/actual

### TestEdgeCases (6 tests)
- `test_missing_project_root` -- nonexistent path exits 2
- `test_empty_project_exits_1` -- no hashable files exits 1
- `test_empty_project_json` -- empty project JSON includes error key
- `test_only_binary_files` -- all-binary project exits 1
- `test_readme_priority_order` -- README.md preferred over README.rst
- `test_no_duplicates` -- no duplicate file paths in output

### Import Pattern
Tests use the same `importlib.util.spec_from_file_location` pattern as `test_generate_agents.py` to import the hyphenated script name. CLI integration tests use `subprocess.run` for exit code verification.

## Test Results

All 25 tests pass:

```
============================= 25 passed in 0.69s ==============================
```

## Integration Notes

This script is designed to be called from flux-drive's domain detection workflow. The typical flow:

1. **On first run**: `content-hash.py <project> --json` computes and returns the hash. The caller stores `hash` in `.claude/flux-drive.yaml`.
2. **On subsequent runs**: `content-hash.py <project> --check <stored_hash>` quickly determines if the project has changed. Exit 0 means cache is fresh; exit 1 means re-detection needed.

The hash covers README, build system, and dominant source files -- the same signals that flux-drive's domain detection examines. This means the hash changes precisely when domain detection results might change.
