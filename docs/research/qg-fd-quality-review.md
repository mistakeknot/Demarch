# QG Review: generate-agents.py + detect-domains.py simplification

**Date:** 2026-02-22
**Scope:** interflux plugin — generate-agents.py (NEW), detect-domains.py (MODIFIED), test_generate_agents.py (NEW), test_detect_domains.py (MODIFIED), flux-gen.md, SKILL.md, SKILL-compact.md

## Summary

The change adds a deterministic template engine (`generate-agents.py`) that extracts agent-file generation from the LLM orchestrator into a pure Python script, and simultaneously removes 250 lines of staleness-detection tiers from `detect-domains.py`. Both moves reduce complexity in the right direction. The test suite (23 new tests) covers modes, orphan detection, dry-run, and CLI exit codes.

Three production-relevant issues were found. The most structurally significant is a JSON schema mismatch between what `generate()` actually emits and what SKILL.md instructs the LLM to parse — the script uses four flat lists while the SKILL documents an `agents[].action` structure. The second is a file-descriptor lifecycle issue in `_atomic_write` that leaves `.tmp` orphans under some failure sequences. The third is that corrupt-cache parse failures are silently swallowed as `no_domains` in human-readable mode. Two P3 findings concern test isolation and the wall-clock timestamp breaking the "deterministic" invariant.

## Key Findings

1. **Schema mismatch (P2, QS-02):** `generate()` returns `{generated:[], skipped:[], orphaned:[], errors:[]}` but SKILL.md Step 1.0.4 documents `{status, agents:[{name, action}]}` as the parse target — the LLM will fail silently on the mismatch. SKILL.md must be updated to match the actual script output.

2. **`_atomic_write` fd leak path (P2, QS-01):** `os.close(fd)` inside the happy path + a second `os.close(fd)` in the exception handler leaves `.tmp` orphan files when `os.rename` fails after a successful close. The fix is to split `os.close` into a `finally` block separate from the rename+cleanup logic (pattern already used correctly in `detect-domains.py:write_cache`).

3. **Silent cache-corruption path (P2, QS-03):** A YAML parse error on a corrupt `flux-drive.yaml` returns `status: no_domains` with exit 1, but the `errors[]` entry is never printed in non-JSON mode — the operator sees "No domains detected" with no indication of the real cause.

## Findings File

Full findings written to: `/home/mk/projects/Demarch/interverse/interflux/.clavain/quality-gates/fd-quality.md`

Verdict: **needs-changes**

8 findings total: 3 P2, 5 P3. No P0/P1.
