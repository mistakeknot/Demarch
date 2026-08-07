# Verdict — Compact-Drift Guard Adjudication (f-008 × f-122)

Date: 2026-08-06 · Adjudicator: flux-melange PROBE-DISAGREEMENT probe-0

## Which parts hold

**f-122 holds in full.** A root-level guard exists: `scripts/test-compact-freshness.sh`
(registry duplicated in `scripts/gen-skill-compact.sh:27-42`). Its 14-entry hardcoded
registry contains 3 phantom entries verified against git history:

- `interverse/interflux/skills/flux-drive` — the compact was *deliberately* deleted in
  interflux@d2a1ded ("consolidate SKILL.md + SKILL-compact.md"), a documented canonization
  whose stated reason was that the dual-file design silently dropped Phase 2.5
  reaction-round orchestration. The guard demanding this file directly contradicts that
  decision. (The dir was later renamed `flux-engine` in 18d393e, which accidentally
  re-created a compact — see below.)
- `os/clavain/skills/interserve` — renamed `interserve-engine` (clavain@6b352a9).
- `os/clavain/skills/brainstorming` — no git history at that path in os/clavain; pure phantom.

**f-008's EXISTENCE-claim fails, its EFFECT-claim stands.** A guard does exist and even
lists 8 Clavain skills — so "no guard exists for Clavain" is factually wrong. But the guard
is (1) broken (phantom entries → always red), (2) wired to nothing (no CI workflow at root
or in Clavain, no pre-commit invocation), and (3) incomplete (7 live pairs uncovered).
Meanwhile interflux's own per-plugin hook — the one f-008 credited as the only guard — was
deleted in d2a1ded and resurrected unregistered (inert) via b5f537c. Net effect: no
functioning drift protection anywhere, exactly f-008's operational point.

## Current drift (measured 2026-08-06)

**15/15 Clavain compact pairs fail the guard's own freshness check** (round-2 said 13/15):
9 genuine source-hash drifts + 6 pairs missing `.skill-compact-manifest.json` entirely.
Oldest drift: 126 days (using-tmux-for-interactive-commands, lane, galiana, file-todos).
All 4 non-Clavain registry entries with existing dirs (doc-watch, artifact-gen, dialectic,
flux-engine) also fail. The compact fleet is 0% fresh.

## Recommended guard design: option (b) — canonize to single SKILL.md

Choose **(b)**: delete the compacts, manifests, and the guard, following interflux's own
d2a1ded pattern (single SKILL.md with a `## Quick Reference` section at top). Three
sentences of trade-off: the dual-file model has already failed operationally — 0% freshness
across 19 pairs, up to 126 days stale — and d2a1ded proved a stale compact is worse than
none because it silently routes sessions around current behavior (the Phase 2.5 incident),
so the token savings (~measured in the sylveste-ynh7 plan) are being paid for with
incorrect agent behavior. Option (a) (fix registry + CI) perpetuates a structurally
fragile design: a root-level hardcoded registry cannot survive per-plugin renames, and
hash-equality freshness flags every typo fix as drift, training maintainers to ignore it.
Option (c) (generate at install time) is the acceptable fallback *if* token savings are
re-measured and shown to matter after canonization, since generated-at-install artifacts
cannot drift from their source; but it adds install-time LLM/structural tooling complexity
that the Quick-Reference pattern gets for free.

## Where the guard should live

If (b) is adopted the guard dies with the compacts — that is the point. For any residual
dual-file plugins, enforcement must live **per-plugin** (each plugin's own test suite, run
by that plugin's CI, e.g. Clavain's `test.yml`), never as a root-level hardcoded registry:
every failure mode observed here (3 phantoms, 7 uncovered pairs) traces to the registry
living far from the renames it couldn't track. Per-plugin discovery (glob `skills/*/SKILL-compact.md`)
with no central list is the only configuration that cannot go stale in this way.

## Follow-up hazards noted

- interflux@18d393e accidentally re-created `flux-engine/SKILL-compact.md` (310 lines)
  during the rename, contradicting d2a1ded; it has no SKILL.md preamble and is itself stale.
  Canonization there needs completing, not just in Clavain.
- `interverse/interflux/hooks/check-compact-drift.sh` is tracked on main but unregistered
  in hooks.json — delete it or register it; inert scaffolding invites the next f-008.

## REMEDIATION

REMEDIATION: Adopt option (b) — canonize all 19 SKILL.md/SKILL-compact.md pairs to single SKILL.md files with a `## Quick Reference` section (pattern: interflux@d2a1ded); delete `scripts/test-compact-freshness.sh`, `scripts/gen-skill-compact.sh`, all `SKILL-compact.md` + `.skill-compact-manifest.json` files, and interflux's unregistered `hooks/check-compact-drift.sh`; complete the half-done flux-engine canonization (remove the 18d393e-re-created compact); if token savings later prove necessary, regenerate compacts at install time (option c) with per-plugin glob-discovered checks in each plugin's own CI — never a root registry.
