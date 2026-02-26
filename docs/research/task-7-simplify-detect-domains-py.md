# Task 7: Simplify detect-domains.py to Heuristic Fallback Only

## Summary

Removed all staleness detection code from `interverse/interflux/scripts/detect-domains.py`, retaining only the heuristic domain detection logic. This script now serves exclusively as a fallback for when LLM-based domain detection (Haiku subagent in flux-drive SKILL.md) is unavailable.

## Changes Made

### `interverse/interflux/scripts/detect-domains.py`

**Removed functions (staleness detection):**
- `compute_structural_hash()` — computed SHA-256 hash of structural files for cache invalidation
- `_parse_iso_datetime()` — helper for staleness tier checks
- `_check_stale_tier1()` — structural hash comparison (<100ms)
- `_check_stale_tier2()` — git log check (<500ms)
- `_check_stale_tier3()` — mtime fallback for non-git projects
- `check_stale()` — orchestrator for the 3-tier staleness check

**Removed constants:**
- `STRUCTURAL_FILES` — set of 12 build-system file names (package.json, Cargo.toml, etc.)
- `STRUCTURAL_EXTENSIONS` — set of 4 file extensions (.gd, .tscn, .unity, .uproject)

**Removed imports:**
- `hashlib` — only used by `compute_structural_hash()`
- `subprocess` — only used by `_check_stale_tier2()` for git log checks

**Removed CLI flags:**
- `--check-stale` — triggered staleness check mode (exit 0=fresh, 3=stale, 4=none)
- `--dry-run` — diagnostic output for `--check-stale` mode

**Updated `write_cache()`:**
- Removed `structural_hash` parameter — no longer computes or stores structural hashes in cache

**Updated `main()`:**
- Removed the `--check-stale` mode branch that called `check_stale()`
- Removed `compute_structural_hash()` call before `write_cache()`
- Simplified `write_cache()` call (no structural_hash kwarg)

**Updated docstring:**
- Removed exit codes 3 (stale) and 4 (no cache) — these were only for `--check-stale` mode
- Simplified exit code descriptions

**Added header comment:**
```python
# This script is the heuristic fallback for domain detection.
# Primary detection uses LLM-based classification (Haiku subagent in flux-drive SKILL.md).
# This script runs when the LLM is unavailable (offline, API error, timeout).
```

### `interverse/interflux/tests/structural/test_detect_domains.py`

**Removed test classes:**
- `TestStructuralHash` (6 tests) — tested `compute_structural_hash()` determinism, file sensitivity, format
- `TestStalenessCheck` (5 tests) — tested `check_stale()` with various cache states

**Removed imports:**
- `time` — only used by `TestStructuralHash.test_hash_stable_with_same_content`
- `STRUCTURAL_FILES` — removed constant
- `check_stale` — removed function
- `compute_structural_hash` — removed function

**Updated tests in `TestCacheV1`:**
- Replaced `test_write_includes_structural_hash` and `test_write_without_structural_hash` with a single `test_write_no_structural_hash` that asserts structural_hash is NOT present
- Updated class docstring

## What Was Preserved

All core detection logic remains intact:
- `DomainSpec` class
- `load_index()`, `gather_directories()`, `gather_files()`, `gather_frameworks()`, `gather_keywords()`
- `score_domain()`, `detect()`
- `read_cache()`, `write_cache()` (simplified)
- Signal weights: `W_DIR`, `W_FILE`, `W_FRAMEWORK`, `W_KEYWORD`
- `SOURCE_EXTENSIONS`
- CLI with `--json`, `--no-cache`, `--index-yaml`, `--cache-path` flags
- All dependency parsers: package.json, Cargo.toml, go.mod, pyproject.toml, requirements.txt

## Test Results

**detect-domains tests:** 36 passed in 0.54s (was 47 tests — 11 removed)
**generate-agents tests:** 23 passed in 0.39s (unchanged, no impact)

## Line Count Reduction

- `detect-domains.py`: 713 lines -> 457 lines (256 lines removed, ~36% reduction)
- `test_detect_domains.py`: 435 lines -> 318 lines (117 lines removed, ~27% reduction)

## Architecture Impact

The staleness detection responsibility has moved from this Python script to content hashing in the SKILL.md flow (LLM-based detection). This script is now a pure signal-scoring heuristic with no side-channel checks (no git, no subprocess, no file hashing). This makes it faster, simpler, and free of external dependencies beyond the filesystem and PyYAML.
