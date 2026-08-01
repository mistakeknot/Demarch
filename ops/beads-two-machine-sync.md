# Beads Two-Machine Sync — Verified State

> How bead state moves between Clavain (MacBook) and zklw (dedi), what differs
> between them, and which differences are deliberate. Companion to
> `publish-machine-roles.md`, which covers the *publish* role rather than beads.
>
> Verified end to end 2026-07-31 by observing hooks fire and beads arrive, not
> by confirming files were present. That distinction matters: this protocol had
> already failed once because a hook was installed at a path git ignores, which
> every file-presence check would have called healthy.

## The protocol

`.beads/issues.jsonl` is the git-tracked transport. Each machine keeps its own
Dolt database; the JSONL is how they reach each other.

| Direction | Mechanism | Trigger |
|---|---|---|
| Dolt → JSONL | export, then a dedicated commit | `post-commit` |
| JSONL → Dolt | `scripts/beads_safe_import.py` | `post-merge` |

Both machines set `core.hooksPath = <repo>/.beads/hooks`, so `.git/hooks/` is
**never executed**. Anything installed there is inert. Confirmed on both.

## Verified round trip

- `sylveste-vftd` filed on zklw → pushed → `git pull` on Clavain → visible in
  Clavain's `bd` with no manual import.
- Four Clavain-filed beads (`Sylveste-v4ub`, `-hdru`, `-9ohx`, `-8umf`) → pushed
  → `git pull` on zklw → present in zklw's Dolt with correct statuses.
- Drift checker clean on both machines afterward.

## Drift register

### Resolved

**`setsid` is Linux-only.** The post-commit Dolt auto-push block used it
unconditionally, so on macOS the subshell failed, `|| true` swallowed it, and
`.beads/push-hook.log` was never created — no output, no error, no trace. It now
falls back to a plain background job and always writes the log. Harmless in
effect (Clavain is verifier-only and cannot push Dolt regardless), but "does
nothing and leaves no evidence" is the wrong failure shape for a sync mechanism.

### Accepted, with reasons

**`bd` version differs: zklw 1.0.2, Clavain 1.0.0 (dev).** This is the root
cause of two things previously mistaken for bugs:

1. *The hook-shim version churn.* Each `bd` rewrites its own managed blocks in
   the tracked hook files to its own version string, so the two machines flip
   `# --- BEGIN BEADS INTEGRATION v1.0.2 ---` back and forth. Cosmetic today.
   It stops being cosmetic if the block contents ever diverge, not just the
   marker.

2. *The JSONL staleness that prompted all of this.* **bd 1.0.2 auto-exports
   during its own pre-commit**; bd 1.0.0 does not. zklw's export was never stale
   because bd was doing it; Clavain's rotted for two days because nothing was.

   Upgrading Clavain's `bd` would make `scripts/beads-auto-export.sh` largely
   redundant — but not obviously better. bd 1.0.2 stages the export **into the
   triggering commit**: a `git commit -- <one-path>` on zklw produced a
   two-file commit. Our post-commit path emits a separate commit and leaves the
   authored commit exactly as authored. Both were observed; the choice between
   them is a real one, not a workaround.

**The two mechanisms compose, but by construction rather than by luck.** On
zklw, bd exports in pre-commit, so by the time our post-commit script runs the
commit already contains `.beads/issues.jsonl` and the re-entrancy guard exits.
No double commit, no loop. That guard exists for our own recursion; it happens
to cover this too.

**Issue-ID prefix casing differs.** zklw creates `sylveste-vftd`; Clavain creates
`Sylveste-v4ub`. Both resolve, and the drift checker is case-sensitive but
compares whole IDs, so mixed casing is not a correctness problem — it is a
cosmetic tell of which machine filed a bead.

**Intercore schema differs: zklw 38, Clavain 39.** Within the range the gate
wrappers accept (36–39). Worth watching, not acting on.

**Push permissions differ, opposite to intuition.** Clavain pushes `main`
directly (the remote reports `Bypassed rule violations`); zklw is *rejected* by
branch protection and must use the `autosync/zklw` lane, wait for
`Generator and parity checkers`, then fast-forward. The signer is the machine
with fewer git privileges.

## The signer asymmetry is handled, not assumed

zklw is `role: signer`; Clavain is `role: verifier` with only
`.clavain/keys/authz-project.pub`. Same key fingerprint (`3d1c3001d533c5a9`).
So `.beads/push.sh` genuinely cannot work on Clavain, and the git-tracked JSONL
is the **only** egress for bead state there.

Checked whether anything quietly depends on that push succeeding:

- `.beads/push.sh` exits **1** when it refuses, with a message naming the
  reason. It does not fail open.
- `.beads/close-and-sync.sh` runs under `set -euo pipefail`, so it aborts on
  that exit rather than reporting a close as synced.

Both correct. The asymmetry is visible at every call site that could be misled
by it.
