# Verdict — fd-canonization-safety (probe 3, round 2)

## What the intersection revealed

The parent contradiction — consolidation says merge the duplicates; contract engineering says the divergence may be the de-facto contract — turned out to be *load-bearing reality* in all five review areas, not a thought experiment. Three structural patterns recurred:

1. **The guard is blinder than the drift.** Every duplicate pair had a reconciliation mechanism, and every mechanism watched the wrong signal: the lib-intercore sync test points at a deleted path and compares only a version string that is identical across 266 diff lines; the gitleaks sync greps a marker that the (falsely completed) migration left stale on 37/47 copies; the SKILL-compact freshness guard checks source hashes in a hand-maintained registry that includes a deliberately deleted file and two phantom skills. Contract analysis alone rates each guard "adequate" (a check exists); consolidation alone rates each fleet "merged" (hashes/counts match somewhere). Only the fused lens sees that the guards certify the wrong invariant.

2. **The executed copy is not the edited copy.** For lib-intercore.sh, all 9 runtime hooks execute the Clavain copy while humans treat the core copy as the source template. For SKILL pairs, agents execute SKILL-compact.md (the directive says "load it instead") while humans edit SKILL.md — 13/15 Clavain pairs drifted, up to 126 days. Canonizing "the wrong twin" is not hypothetical: the naive merge target is in both cases the copy no consumer runs.

3. **"Informational" text has behavioral consumers via hashes.** The ~60 PHILOSOPHY doctrine blocks are parsed by no gate, but their file content feeds session-freshness-gate.sh's exit-code contract, so a consolidation sweep changes session-start behavior fleet-wide.

## Safe-canonization verdict for lib-intercore.sh

**Canonical copy: os/Clavain/hooks/lib-intercore.sh** — it is the only copy any runtime consumer executes, and its semantics (post-E3-cutover: no legacy temp-file fallback, fail-open sentinels, error-propagating state ops, 5 extra run_* wrappers) are what every hook's call sites are written against. The core/intercore copy is an archive of pre-cutover semantics kept alive only by its own test suite.

Safe path, in order:
1. **Contract test first**: pin per-function failure semantics of the Clavain copy (exit codes for `intercore_sentinel_check_or_legacy`, `intercore_state_set/get`, `intercore_check_or_die` under ic-absent, ic-erroring, ic-throttled) in Clavain's bats suite — today nothing observes these (f-001/f-078's underlying gap).
2. **Fix the guard before using it**: repoint test-integration.sh:1383 from `../../hub/clavain/...` to `../../os/Clavain/hooks/lib-intercore.sh`, and compare content hash, not just `INTERCORE_WRAPPER_VERSION` — the current version-only compare passes over 266 diff lines.
3. **Bump to 1.2.0 on canonization** and make the machine stamp the single version witness (delete or regenerate the "Version: 0.1.0 (source: infra/...)" provenance comment).
4. **Demote the core copy to a consumer**: delete core/intercore/lib-intercore.sh and have test-integration.sh source the canonical file via the fixed relative path; if the legacy temp-file fallback is still wanted for migration support, extract it under an explicit `intercore_sentinel_check_legacy` name rather than letting it ride the shared wrapper name with a different arity (4-arg vs 3-arg signature clash).
5. Do NOT semantic-union the two copies: their divergences point in opposite directions per function (sentinels vs state ops), so a union silently re-introduces the temp-file fallback the E3 cutover deliberately removed.

## Top 2 findings

1. **P1 — double-blind twin guard** (test-integration.sh:1383 + both lib-intercore.sh:9): identical 1.1.0 stamps, 266 diff lines, guard path dead since the hub/clavain→os/Clavain move, and the executed/edited copies are inverted — wholesale canonizing the repo's nominal "source" (core) would flip failure direction in all 9 Clavain hooks.
2. **P2 — gitleaks re-attachment needs a hash allowlist, not a marker grep** (sync-secret-scan-baseline.sh:55,82-99): the marker is simultaneously provenance stamp and overwrite-protection key; the migration plan's "[x] 45 files" is false for 37, and the only re-attachment rule that preserves the protection contract is matching deployed files against historical template hashes (today provably marker-line-only drift) rather than grepping both markers.

## REMEDIATION

File a bead for the P1 twin canonization following the 5-step path above (contract test → guard fix → 1.2.0 bump → core-copy demotion → no semantic union); a second bead for the gitleaks hash-allowlist re-attachment mechanism in sync-secret-scan-baseline.sh; a third, cheap bead to fix the test-compact-freshness.sh KNOWN_SKILLS registry (drop flux-drive/interserve/brainstorming phantoms, add the 6 unmanifested Clavain pairs) since the guard currently trains operators to ignore it.
