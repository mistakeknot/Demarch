---
artifact_type: goal-charter
bead: Sylveste-ytm
complexity: 4
stage: goal-formed
---

# Goal Charter: Interverse Test-Baseline Execution — Green the Four Suites per the Triage Map

## Why (leverage)

The triage goal (8555c86c) mapped 305 failures across four suites to 8
clusters and proved ≥90% is macOS-vs-Linux platform drift — including two
live production bugs on this Mac (interspect flock writes, interphase
sed -i Phase headers) and a runner that reports success unconditionally.
Report: `docs/research/2026-07-20-interverse-test-baseline-triage.md`
(commit aaf33e55). Until the baselines are green, no exit code in the
interverse is trustworthy and every regression claim pays a stash-proof
tax. This goal spends the map.

**Interview decisions (2026-07-21, all recommended-option):**
1. Success bar = **full green + zklw**: 0 failures on this Mac, straggler
   quarantines allowed only with a surfaced bead each, zklw re-verified
   green after the portability fixes.
2. Lock design = **hybrid**: use `flock` when the binary exists (zklw
   keeps byte-identical semantics — zero Linux risk), portable
   mkdir-based lock fallback where it doesn't; same helper pattern in
   both interspect and interflux; no new dependencies.
3. Ceremony = **melange skipped, ratified directly**: the triage goal was
   the stress-test; this charter projects an mk-ratified map.

**Pre-granted authority (carried from the triage charter, mk-ratified):**
stale tests asserting deliberately retired behavior may be rewritten to
current behavior or deleted outright, rationale in the commit message.

## Scope

**In (execution order from the report):**
1. **Cluster A** — install bats-support/bats-assert (vendor into
   `tests/node_modules` or `npm i -g`) AND extend both interphase and
   Clavain `tests/shell/test_helper.bash` search paths with
   `$(npm root -g)` and the Homebrew lib path. Immediately re-run all
   suites for the true residual baseline (~256 of 305 expected cleared).
2. **Quick wins C + E + G + H** — portable `sed -i` in interphase
   `hooks/lib-gates.sh` (Sylveste-sne, production bug) plus a GNU-ism
   audit (`sed -i `, `stat -c`, `date -d`) across the ecosystem; interline
   script count + executable bit; `hooks/release-canary-check.sh`
   `set -euo pipefail`; `run-tests.sh` success message guarded on
   `$FAILED`.
3. **Cluster B** — hybrid lock helper (flock-if-present, mkdir fallback)
   replacing bare `flock` in interspect `hooks/lib-interspect.sh` and
   interflux `scripts/flux-dispatch.sh` + `flux-backoff.sh`. Closes
   Sylveste-60q and Sylveste-9cs.
4. **Cluster D** — rewrite the 2 PATH="/nonexistent" tests to stub `bd`.
5. **Cluster F** — isolate the ~12 Clavain stragglers against the now-
   green background: real regressions get fixes; retired-behavior tests
   get the pre-granted rewrite/delete authority; anything genuinely deep
   gets quarantine + its own bead, surfaced.
6. **zklw verification** — run the touched suites on zklw over ssh;
   portability fixes must keep Linux green.
7. Changed plugins released per the always-publish-after-push rule (the
   release-canary machinery from goal 8f0a88b6 covers each publish).

**Out:**
- Any feature work beyond test/portability fixes; the goal-native cycle
  redesign; the Claude Code changelog watcher (deferred, sequenced after
  this goal).
- Rewriting lock SEMANTICS beyond portability (no redesign of what gets
  serialized).

## Acceptance criteria

1. All four suites (interphase bats, Clavain runner tiers 1+2, interline
   structural, interflux structural) shown with 0 failures on this Mac in
   surfaced output — OR any residual failure explicitly quarantined with
   a bead ID surfaced per test.
2. Production-bug beads Sylveste-sne, Sylveste-60q, Sylveste-9cs closed.
3. Hybrid lock helper landed in both interspect and interflux; Linux path
   still uses real flock.
4. zklw verification surfaced: touched suites green on zklw.
5. run-tests.sh no longer prints success on failure.
6. Work committed and pushed across affected repos; changed plugins
   published; Sylveste-ytm closed.

## Completion condition (literal — handed to /goal)

Interverse test-baseline execution complete per the triage map (docs/research/2026-07-20-interverse-test-baseline-triage.md): all four suites (interphase bats, Clavain test runner, interline structural, interflux structural) re-run with per-suite counts shown in surfaced output, each at 0 failures on this Mac except tests explicitly quarantined with a bead ID surfaced per quarantine; beads Sylveste-sne, Sylveste-60q, and Sylveste-9cs closed with bd close output surfaced; the hybrid lock helper (flock when present, mkdir fallback) landed in both interspect and interflux; zklw verification surfaced showing the touched suites green on Linux; work committed and pushed across affected repos and bead Sylveste-ytm closed with output surfaced. Or stop after 60 turns.

## Successor obligations

Propose a successor at close per Goal Cadence. Leading candidates at
formation time: the Claude Code changelog watcher (drafted, deferred
behind this goal) and Sylveste-zlc (drop legacy /tmp sideband path,
soak-gated on one clean release).
