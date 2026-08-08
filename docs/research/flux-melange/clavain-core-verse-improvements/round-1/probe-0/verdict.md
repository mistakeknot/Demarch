# Verdict — probe-0: f-029 (stale snapshot fleet) vs f-014 (legit install cache)

## Verdict: PARTIAL — f-029's substance holds; f-014's frame is correct about intent but wrong about coverage

The ~/.codex git clones **are** the designed install location for the Codex
harness (f-014's frame is correct): `install-codex-interverse.sh` deliberately
clones interverse plugins under `~/.codex` and links `~/.agents/skills/*` into
those clones. But the fleet is **not** functioning as a maintained install
cache — it is a partially frozen one (f-029's substance is confirmed):
44 of 47 links resolve to snapshot clones whose freshness is uneven and, for
non-default-profile plugins, frozen since 2026-03-24. Agents reading
`~/.agents/skills` get a mix of live canonical trees and months-old apocrypha,
including a deprecated skill the canonical plugin no longer ships.

## Evidence

1. **Link layer targets** (`ls -la ~/.agents/skills`): 47 links. Three point at
   canonical Sylveste working trees — `clavain -> Sylveste/os/Clavain/skills`,
   `alwe -> Sylveste/os/Alwe/skills/alwe`, `zaka -> Sylveste/os/Zaka/skills/zaka`
   (all relinked Jul 10–22). The other 44 point at `~/.codex/<plugin>/skills/...`
   (created Mar 24).

2. **Intended design** (`Sylveste/os/Clavain/scripts/install-codex-interverse.sh`):
   clones plugins into `$CLONE_ROOT` (default `~/.codex`), refreshes existing
   clones with `git pull --ff-only` (line 905), and installs the skill links.
   So snapshots-as-install-target is by design — f-014 is right that the clones
   are legitimate. `install-kimi.sh` only manages the single `clavain` link and
   points it at the canonical tree; it does not touch the other 44.

3. **Refresh machinery is broken/absent**:
   - `ensure_repo` pulls only plugins in the *active* agent-rig profile
     (`interverse_recommended_plugins` → default profile). Result on disk:
     default-profile clones (interdoc, interlock, interphase, intertest) fetched
     Jul 15 2026; non-default clones (interflux = review profile, interlab =
     ops profile) frozen at Mar 24 2026 (`FETCH_HEAD` mtimes).
   - `codex-auto-refresh.sh` (the only script that would pull everything via a
     full reinstall) has **never run**: no crontab entry, no LaunchAgent, and
     its log `~/.local/share/clavain/codex-refresh.log` does not exist.
   - Even the "fresh" default-profile snapshots lag: `~/.codex/interdoc` HEAD
     2026-06-22 vs canonical `Sylveste/interverse/interdoc` HEAD 2026-07-22.

4. **flux-research is live-routed apocrypha**: canonical
   `Sylveste/interverse/interflux/skills/` ships only `flux-engine`,
   `flux-melange-engine`, `flux-review-engine` (HEAD 2026-08-03). Upstream
   deprecated flux-research (merged into `flux-drive mode=research`, per
   interflux docs) and later renamed skill dirs to match SKILL.md `name:`
   fields. The frozen `~/.codex/interflux` snapshot (HEAD 2026-03-24) still
   ships `flux-drive` + `flux-research`, and both are invocable through
   `~/.agents/skills` — Kimi Code's native skill scan loads them (flux-research
   appears in the live skill roster, marked DEPRECATED only because the stale
   copy says so).

5. **Drift-checker coverage** (`check-install-updates.sh`): light/default mode
   checks only `~/.codex/clavain` drift; companion-repo drift requires `--full`.
   f-014's claim that the drift-checker "covers" the snapshot fleet holds only
   for the clavain clone — the interflux freeze raises no routine warning.

## What exactly is broken (the PARTIAL decomposition)

- NOT broken: the routing design (links → `~/.codex` clones is intended for Codex).
- Broken: (a) refresh only covers the active profile, starving review/ops/
  research/docs/observability plugins; (b) no scheduler ever runs the
  auto-refresh; (c) drift notification hides companion staleness behind `--full`;
  (d) deprecated skills remain invocable because nothing prunes links whose
  skill was removed upstream; (e) three links bypass the snapshot model entirely
  and point at canonical trees — two freshness semantics in one directory,
  undocumented.

## New findings (improvement opportunities)

1. **N1 (P2)**: Make `install-codex-interverse.sh update` refresh *all* cloned
   plugins present under `~/.codex`, not just the active profile's — presence on
   disk is a better refresh set than profile membership.
2. **N2 (P2)**: Schedule `codex-auto-refresh.sh` (LaunchAgent) or delete it;
   dead automation is worse than none because docs imply freshness.
3. **N3 (P2)**: Promote companion-repo drift into the default (light) mode of
   `check-install-updates.sh`, or have the SessionStart hook run `--full` on a
   TTL — a 4.5-month-stale interflux should page at session start.
4. **N4 (P1)**: Add link pruning to the installer: after pulling a clone, remove
   `~/.agents/skills` links whose target skill dir no longer exists upstream
   (would have removed flux-research when canonical dropped it).
5. **N5 (P3)**: Pick one routing model and document it in AGENTS.md — either all
   links → canonical Sylveste working trees (like clavain/alwe/zaka) or all →
   refreshed snapshots; the current split-brain is invisible to agents.

## REMEDIATION

REMEDIATION: Amend the review-target docs (the fd-lifecycle-drift/f-014 writeup
and any AGENTS.md/install docs implying the ~/.codex fleet is drift-checked and
current) to state that only the active agent-rig profile is refreshed, that
companion drift is reported solely in `--full` mode, and that non-default-profile
clones on this machine are frozen as of 2026-03-24.
