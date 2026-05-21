---
date: 2026-04-20
session: 9a4d062b
topic: axo3 sprint bootstrapped + dispatch fixes shipped
beads: [sylveste-mb3i, sylveste-aglf, sylveste-axo3, sylveste-0922]
---

## Session Handoff — 2026-04-20 Ockham Wave 2 sprint start + dispatch hardening shipped

### Directive
> Your job is to run Step 1 (Brainstorm) of sprint `sylveste-axo3` — "Ockham Wave 2 wiring: compose F3/F4/F5/F6/F7 into anomaly evaluator trigger path". Start by running `clavain-cli sprint-init sylveste-axo3` (will succeed cleanly now), confirm Tier 2 autonomy, then invoke `/clavain:brainstorm sylveste-axo3`. The bead is P0, claimed, complexity 3/5 (Tier 2 = pause after Step 4 plan review, auto-advance otherwise). Full 10-step sprint is queued.
- Beads:
  - `sylveste-axo3` — in_progress, claimed by this session (9a4d062b), ready for brainstorm
  - `sylveste-mb3i`, `sylveste-aglf` — CLOSED (shipped as clavain v0.6.243)
  - `sylveste-0922` — OPEN P3 follow-up: fix misleading "re-run to force" error in `core/intercore/internal/publish/engine.go:127`

- Fallback if not ready to brainstorm: the bead description is unusually detailed and pre-specifies the full compose pipeline (see `bd show sylveste-axo3`). Arguments could be made for jumping straight to `/clavain:write-plan` and treating the description as the brainstorm. The route skill classified it as brainstorm because `phase` state was unset.

### Dead Ends
- `ic publish --patch` retries after a stuck PublishState lock — the "re-run to force" error message is misleading; only `--auto` clears stale rows (captured in `docs/solutions/workflow-issues/ic-publish-stale-lock-and-approval-gate-System-20260420.md`, follow-up bead `sylveste-0922`)
- `ic publish --force` / `ic publish --patch --force` — no such flag exists
- Running `ic publish --auto` before stashing WIP — post-bump hooks (gen-rig-sync, agency-spec-helper) had mutated `cmd/clavain-cli/authz.go` and `config/routing.yaml` from an earlier failed publish, so the clean-worktree gate blocked repeatedly. Always stash first.
- `bd doctor --fix` did not untrack sensitive files automatically; had to run `git rm --cached` manually for `.beads/.beads-credential-key`, `.beads/.local_version`, `.beads/last-touched`, `.beads/backup/.backup-tmp-*`.
- `clavain-cli sprint-init` kept failing with "bd doctor found 1 error(s)" even after errors were cleared — it reads a stale sentinel at `/tmp/clavain-bd-corruption-$USER` written by session-start.sh. Fix: `rm /tmp/clavain-bd-corruption-$USER`.

### Context
- `os/` in the Sylveste monorepo is gitignored; `os/Clavain/` is a **sibling git repo**, not a submodule. Changes to dispatch.sh must be committed inside `os/Clavain/` and published via `ic publish --auto` with `.publish-approved` touch file.
- Publish sequence that actually works: `git stash push -u -m "pre-publish" && touch .publish-approved && ic publish --auto && git stash pop`
- `bash .beads/push.sh` hangs with "no tty available" in agent sessions unless `CLAVAIN_SPRINT_OR_WORK=1` is exported. Memory `feedback_auto_proceed_vetted_flow.md` documents the policy.
- clavain v0.6.243 dispatch.sh now: (1) captures codex stderr via `2> >(tee "$STDERR_FILE" >&2)` process substitution, (2) detects HTTP 4xx/5xx/429/ERROR-prefix/non-zero-exit/zero-output and overrides `.verdict` sidecar with STATUS=error|retry|warn (pre-error preserved as `.verdict.pre-error`), (3) runs `_preflight_toolchains` against project markers (go.mod, package.json, Cargo.toml, pyproject.toml, requirements.txt, Gemfile, pom.xml, build.gradle*) with `CLAVAIN_STRICT_PREFLIGHT=1` fail-fast and `CLAVAIN_PREFLIGHT_INJECT_PATH=1` injection.
- Test coverage added: `os/Clavain/tests/shell/dispatch_error_surfacing.bats` (10 tests) and `os/Clavain/tests/shell/dispatch_preflight.bats` (8 tests). Run with `cd os/Clavain && bats tests/shell/dispatch_*.bats`.
- Git worktree currently has user WIP unstashed: `config/routing.yaml` (gpt-5.4 dispatch default per memory) and `cmd/clavain-cli/authz.go` (authz v1.5 policy subcommands: init-key, sign, verify, rotate-key, quarantine). These are the user's work, not mine — do not commit them unprompted. They survived the publish via stash/pop.
- Sprint-init banner shown at end: complexity 3/5, Tier 2, pause-after-plan-review. No brainstorm artifact exists yet.
- Auraken Go migration epic `sylveste-benl` (P0, score 79) was passed over during route discovery because memory `project_auraken_hermes_pivot.md` notes benl.6-11 are mooted by the 2026-04-16 Hermes pivot. That epic deserves a review/close pass before being treated as executable again.
