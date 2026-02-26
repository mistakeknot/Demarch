# Task 1 Analysis: generate-agents.py and Tests

## Summary

Created `interverse/interflux/scripts/generate-agents.py` (template engine for domain-specific review agents) and `interverse/interflux/tests/structural/test_generate_agents.py` (23 tests). All 23 tests pass. The single pre-existing failure in `test_agents.py::test_agent_count` (hardcoded 13 vs actual 17 agents) is unrelated.

## Files Created

1. **`/home/mk/projects/Demarch/interverse/interflux/scripts/generate-agents.py`** — Core template engine (executable, ~350 lines)
2. **`/home/mk/projects/Demarch/interverse/interflux/tests/structural/test_generate_agents.py`** — Test suite (23 tests, ~340 lines)

## Script Architecture

### Constants and Configuration

- `FLUX_GEN_VERSION = 4` — current template format version
- `CORE_AGENTS` — frozenset of 7 core agent names to skip during parsing
- `DOMAIN_DOC_TYPES` — hardcoded map of 11 domains to their documentation types for the First Step section
- `PLUGIN_ROOT` / `DOMAINS_DIR` — paths resolved relative to the script's location

### Functions Implemented

1. **`parse_agent_specs(profile_path, domain)`**
   - Regex-based extraction of `## Agent Specifications` section
   - Splits on `### fd-*` subsection headers
   - Extracts Focus, Persona, Decision lens, Key review areas, Success criteria hints
   - Skips any agent whose name is in `CORE_AGENTS`
   - Returns list of spec dicts

2. **`render_agent(spec)`**
   - Produces full markdown with YAML frontmatter (`generated_by: flux-gen`, `domain`, `generated_at`, `flux_gen_version: 4`)
   - Template matches flux-gen.md Step 4 format exactly
   - Persona fallback: `"You are a {domain} {focus} specialist — methodical, specific, and grounded in project reality."`
   - Decision lens fallback: `"Prioritize findings by real-world impact on {domain} projects. Flag issues that would cause failures in production before style concerns."`
   - `_short_title()` helper derives section titles from review area bullets

3. **`check_existing_agents(agents_dir)`**
   - Scans `fd-*.md` files, parses YAML frontmatter
   - Only returns agents with `generated_by: flux-gen`

4. **`generate(project, mode, dry_run)`**
   - Reads `.claude/flux-drive.yaml` for domain list
   - Three modes: `skip-existing`, `regenerate-stale` (version < FLUX_GEN_VERSION), `force`
   - Orphan detection: agents whose domain is not in detected domains
   - Returns structured report dict with status, generated, skipped, orphaned, errors

5. **`_atomic_write(path, content)`**
   - tempfile + os.rename pattern matching detect-domains.py convention

6. **CLI (`main()`)**
   - `--mode` (skip-existing|regenerate-stale|force), `--json`, `--dry-run`
   - Exit codes: 0 (ok), 1 (no domains), 2 (error)

### Design Decisions

- **Regex parsing** rather than a markdown library — keeps dependencies minimal (only pyyaml needed), matching the detect-domains.py pattern
- **Atomic writes** using the same tempfile+rename pattern as detect-domains.py
- **Monkeypatch `DOMAINS_DIR`** in tests rather than subprocess env manipulation — cleaner for unit tests of `generate()`. CLI tests use real domain profiles (game-simulation) since subprocess can't easily patch module-level constants.
- **`_domain_display_name()`** uses `.replace("-", " ").title()` — simple and consistent

## Test Coverage

### TestParseAgentSpecs (3 tests)
- `test_extracts_agent_from_profile` — 2 agents from mock profile, all fields verified
- `test_skips_core_agent_injections` — fd-architecture, fd-safety skipped
- `test_no_agent_specs_section` — bare profile returns empty list

### TestRenderAgent (7 tests)
- `test_renders_frontmatter` — YAML frontmatter with correct keys and version
- `test_persona_fallback` — None persona generates domain-based fallback
- `test_decision_lens_fallback` — None decision_lens generates fallback
- `test_review_areas_rendered` — numbered sections with content
- `test_success_hints_appended` — hints added to Success Criteria
- `test_what_not_to_flag_section` — anti-overlap section references core agents
- `test_title_format` — correct `# name — Domain Display Domain Reviewer`

### TestGenerate (7 tests)
- `test_no_domains_returns_no_domains` — no cache -> status: no_domains
- `test_skip_existing_mode` — existing agents preserved, new ones generated
- `test_regenerate_stale_mode` — old version regenerated, current version skipped
- `test_dry_run_writes_nothing` — reports but no file writes
- `test_orphan_detection` — agents for removed domains in orphaned list
- `test_force_mode_overwrites` — current-version agents regenerated
- `test_empty_cache_domains` — empty domains list -> no_domains

### TestCheckExistingAgents (2 tests)
- `test_finds_flux_gen_agents` — only flux-gen agents returned
- `test_nonexistent_dir` — empty dict for missing directory

### TestCLIIntegration (4 tests)
- `test_cli_json_output` — valid JSON with status and generated keys
- `test_cli_no_cache_exits_1` — exit code 1 without cache
- `test_cli_dry_run_creates_no_files` — no files written with --dry-run
- `test_cli_invalid_path_exits_2` — exit code 2 for bad path

## Test Results

```
23 passed in 0.43s
```

Full suite (130 of 131 passed — the 1 failure is pre-existing `test_agent_count` expecting 13 agents but repo has 17).

## Key Findings

1. **Template version bump**: The task spec says `flux_gen_version: 4` while flux-gen.md Step 4 template shows version 3. The script implements version 4 as specified in the task requirements.

2. **Mock profile strategy**: Tests use synthetic profiles with known content rather than real domain profiles. This makes tests deterministic and independent of profile evolution. CLI integration tests use the real `game-simulation` domain profile for end-to-end validation.

3. **Pre-existing test failure**: `test_agents.py::test_agent_count` fails (expected 13, found 17). This is unrelated — it counts plugin agents in `interverse/interflux/agents/`, not generated agents in `.claude/agents/`. Should be updated separately.

4. **Import pattern**: Follows the exact same `importlib.util.spec_from_file_location` pattern as `test_detect_domains.py` for importing hyphenated script names.
