# Architecture Review: interflux flux-gen LLM Detection Refactor

**Date:** 2026-02-22
**Diff analyzed:** /tmp/qg-diff-1771785677.txt
**Primary output:** /home/mk/projects/Demarch/interverse/interflux/.clavain/quality-gates/fd-architecture.md

---

## Scope

Six changed files in the interflux Claude Code plugin:
- `scripts/generate-agents.py` (NEW, ~566 LOC) — deterministic agent template engine
- `scripts/detect-domains.py` (MODIFIED) — stripped to heuristic fallback only; ~200 LOC removed (staleness tiers, structural hash)
- `commands/flux-gen.md` (MODIFIED) — delegates generation to generate-agents.py script
- `skills/flux-drive/SKILL.md` (MODIFIED) — adds LLM-based detection as primary path, heuristic as fallback
- `skills/flux-drive/SKILL-compact.md` (MODIFIED) — matching compact version
- `tests/structural/test_generate_agents.py` (NEW, 23 tests)
- `tests/structural/test_detect_domains.py` (MODIFIED) — staleness tests removed

---

## Key Findings

**Verdict: safe — 3 P2, 2 P3 issues, none blocking.**

### P2 Issues

1. **Cache format version fork (A1):** detect-domains.py still writes `cache_version: 1`; SKILL.md directs LLM to write `cache_version: 2`. Neither reader (detect-domains.py `read_cache()` nor generate-agents.py) gates on version. The `content_hash` absence is used to detect stale v1 caches, which works for now, but the ambiguity accumulates as the schema evolves. Fix: align CACHE_VERSION constant to 2 in detect-domains.py, add version guard in generate-agents.py.

2. **content_hash computed in-prose (A2):** Staleness detection now relies on a `content_hash` that SKILL.md instructs the LLM to compute by hashing "README + build file + 2-3 key source files." This is non-deterministic — different LLM runs may pick different files. The removed `compute_structural_hash()` function was deterministic and tested. The hash is load-bearing for cache freshness. Fix: add a `--content-hash` subcommand or utility function in generate-agents.py that scripts can call for both write and validation, removing the in-prose computation.

3. **AGENTS.md stale after change (A3):** `scripts/detect-domains.py` description in AGENTS.md still reads "Domain profile scoring (deterministic)"; generate-agents.py is not listed; test count is outdated; agent count differs between CLAUDE.md and AGENTS.md. These affect automated validation checks that use component counts as guards.

### P3 Issues

4. **DOMAIN_DOC_TYPES duplication (A4):** generate-agents.py embeds a 11-entry dict encoding domain-to-doc-type mappings. Same knowledge exists (partially) in domain profile markdown files. A third update site will silently drift from the profiles.

5. **Fragile subprocess test (A5):** CLI integration test falls back to the live game-simulation profile because it cannot inject DOMAINS_DIR into a subprocess, documented by an inline comment. Fragile against profile restructuring. Prefer Python API tests or a `--domains-dir` CLI flag.

---

## Architectural Assessment

The change correctly reduces the component surface. Removing three-tier staleness (~200 LOC of git/hash/mtime logic) in favor of an LLM-read hash is proportionate to the shift in primary detection path. generate-agents.py is a clean extraction of the template engine from flux-gen.md prose — its scope is narrow, its interface is stable (exit codes + JSON report), and its test coverage is proportionate. The LLM-as-primary pattern is consistent with how flux-drive already uses Haiku subagents. The two P2 issues (version fork and in-prose hash) are the ones most likely to surface as subtle bugs in production.
