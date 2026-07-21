---
artifact_type: research
bead: Sylveste-ytm
stage: triage
goal: 8555c86c
---

# Interverse Test-Baseline Triage — Root-Cause Map

Fresh runs 2026-07-21 (this Mac, "Clavain" machine), goal 8555c86c.
Raw outputs: session scratchpad `interphase-full.txt`, `clavain-full.txt`.

## Fresh failure counts (surfaced in-session)

| Suite | Failing / total |
|---|---|
| interphase `bats tests/shell/` | **132 / 152** |
| Clavain bats (tier 2) | **167 / 654** |
| Clavain structural pytest (tier 1) | **1 / 783** |
| interline structural | **2 / 12** |
| interflux structural | **3 / 238** |
| **Total** | **305 failures** |

## Headline

**≥90% of the rot is macOS-vs-Linux platform drift, concentrated in two
root causes.** The suites (and some production hook code) were authored
against zklw (Linux); this Mac lacks the bats helper libraries, `flock(1)`,
and GNU sed semantics. Two clusters are **live production bugs on macOS**,
not just test rot — the same class as the interline `stat -c` bug fixed in
0.2.16 (Sylveste-rfs). A contributing factor: the Clavain runner prints
"Tiers 1+2 passed" unconditionally (cluster H), so red runs read as green
unless you check the exit code.

## Clusters

### A — bats-assert/bats-support unresolvable on macOS — ~256 failures (84%)
`tests/shell/test_helper.bash` (both interphase and Clavain) searches only
`/usr/lib/node_modules` and `/usr/local/lib/node_modules` (Clavain also
`tests/node_modules`). This Mac's npm root is `~/.npm-global/lib/node_modules`
and the libs are not installed anywhere, so the load silently skips and every
`assert_*`/`refute_*` is `command not found`. Counts: interphase ~124,
Clavain ~132.
**Disposition: fix now.** Install the libs (vendor into `tests/node_modules`
or `npm i -g`) AND extend both helpers' search paths with `$(npm root -g)`
and the Homebrew lib path. **Effort: S** — two helper files, one install.
Unblocks 84% of all failures; re-run everything after this first.

### B — `flock(1)` does not exist on macOS — ~23 failures + production impact
Production code hard-depends on Linux flock:
- interspect `hooks/lib-interspect.sh` `_interspect_flock_git` wraps ALL
  overlay/override/canary write paths → ~20 Clavain
  `test_interspect_routing.bats` failures, and **on macOS the production
  writes themselves fail** (overlays, routing overrides, revert, canary
  status).
- interflux `scripts/flux-dispatch.sh` + `flux-backoff.sh` fd-204 locking →
  3 backpressure failures. **Resolves Sylveste-9cs: not a semaphore
  regression — platform dependency** (manual repro: `flock: command not
  found`, exit 127).
**Disposition: fix.** Portable lock helper (mkdir-lock fallback, or a
documented `brew install flock` dependency + guard); shared between the two
codebases if practical. **Effort: M** — concurrency-sensitive, two repos.
Beads: Sylveste-9cs (interflux side) + new production-bug bead (interspect
side, filed by this triage).

### C — GNU `sed -i` in interphase production code — 4 failures + production bug
`hooks/lib-gates.sh` has 3 `sed -i "s|…"` sites (e.g. :573). BSD sed
requires an extension argument, so on macOS `_gate_write_artifact_phase`
**silently never writes/updates `**Phase:**` artifact headers** (failures
masked by `|| true`). Same class as the interline stat bug.
**Disposition: fix now** (portable `sed -i.bak … && rm`, or perl -pi), plus
an ecosystem-wide audit for `sed -i `, `stat -c`, `date -d` GNU-isms.
**Effort: S.** Bead filed by this triage.

### D — PATH="/nonexistent" simulation rot — 2 failures
interphase `discovery.bats`/`brief_scan` nuke PATH to simulate missing
`bd`, but `lib-discovery.sh` now runs `dirname` at source time, so the
source fails before the behavior under test.
**Disposition: rewrite** the two tests to stub `bd` instead of destroying
PATH. **Effort: XS.**

### E — interline structural manifest drift — 2 failures
`test_scripts_count` expects 4 scripts, repo has 6 (bump-version.sh,
lib-lane.sh, validate-gitleaks-waivers.sh added); `test_scripts_executable`
flags `lib-lane.sh` missing its executable bit.
**Disposition: fix now** (update count; chmod or exempt sourced libs).
**Effort: XS.**

### F — Clavain individual stragglers — ~12 failures
Ran their assertions (no assert-lib involvement) and failed on behavior:
`audit: enforce mode` (test-side GNU `sed -i` — fold into C's audit),
doctor pair in `test_codex_interverse_installer.bats` (status≠0, cause not
yet isolated), `sprint_claim` TTL takeover, `sprint_invalidate_caches`,
safety-floor sonnet routing, runtime-evidence canaries ×2, artifact
hard-gate, budget advance.
**Disposition: isolate individually** during execution, AFTER cluster A
lands (some may be A/B side effects; the remainder are candidate real
drift). **Effort: M** (unknowns).

### G — fresh convention violation (this session, 2026-07-20) — 1 failure
Clavain structural `test_hook_entry_points_have_set_euo_pipefail`:
`hooks/release-canary-check.sh` (shipped 0.6.282) uses `set -uo pipefail`,
convention requires `set -euo pipefail` (compatible with its fail-open ERR
trap). **Disposition: fix now** — one line, rides the next release.
**Effort: XS.**

### H — runner reports success while failing — invisible-rot mechanism
`os/Clavain/tests/run-tests.sh` default path prints "Tiers 1+2 passed."
unconditionally; only the exit code (`exit $FAILED`) is honest.
**Disposition: fix now** — guard the message on `$FAILED`. **Effort: XS.**

## Recommended execution order

1. **A** (S) — install + repath bats libs → immediately re-run all suites
   for a true residual baseline.
2. **C + E + G + H** (S+XS×3) — quick wins, including the sed production
   bug and the lying runner.
3. **B** (M) — portable locking; closes Sylveste-9cs and the interspect
   production bug.
4. **D** (XS) — rewrite the two PATH-sim tests.
5. **F** (M) — isolate the ~12 stragglers against a now-green background;
   real regressions get fixes, retired-behavior tests get the pre-granted
   rewrite/delete authority (mk-ratified, charter
   `docs/goals/2026-07-20-test-baseline-triage-charter.md`).
6. Verify on zklw — portability fixes must keep Linux green too.

Estimate: steps 1–2 one session; step 3 one focused session; steps 4–5
half a session.
