# Rig Self-Checks

> What runs on its own, where, how often, and how long before you hear about it.
> Companions: `plugin-enablement-policy.md`, `publish-machine-roles.md`.

A check nobody invokes is a check that exits 0. `guard-enabled-plugins.sh`
protected nothing for four months (`mk-1wj0`) while looking healthy in the
SessionStart list, and its test suite existed the whole time — nothing ran it.
This page exists so that never depends on someone remembering.

## What is automatic

| Check | Clavain | zklw | Cadence |
|---|---|---|---|
| `guard-tests` — the 13-test guard suite | launchd | systemd timer | daily 09:15 |
| `settings-reference` — does a reference actually resolve | launchd | systemd timer | daily 09:15 |
| `marketplace-divergence` — do the clones agree | launchd | systemd timer | daily 09:15 |
| `intercore-tests` — `go test ./...` for the suite gating `ic` | launchd | systemd timer | daily 09:15 |
| `ic-provenance` — does the deployed binary match the source | launchd | systemd timer | daily 09:15 |
| `advertisement-budget` — what enabled plugins cost in context | launchd | systemd timer | daily 09:15 |
| `instrument-freshness` — are the usage instruments still recording | launchd | systemd timer | daily 09:15 |
| settings.json history | SessionStart + daily | **continuous, 10s poll** | see below |

Expected steady state, so a drift is auditable against something:

```
Clavain   guard-tests pass   settings-reference pass   marketplace-divergence pass
          intercore-tests PASS    ic-provenance pass    advertisement-budget WARN
zklw      guard-tests pass   settings-reference pass   marketplace-divergence pass
          intercore-tests PASS    ic-provenance pass    advertisement-budget WARN
```

zklw's budget check found a real problem on its first run — 52,537 against a
30,000 ceiling, because the enablement policy had only ever been applied to the
Mac. Resolved the same day to **29,360** (`mk-zysa`); see
`plugin-enablement-policy.md`. Both machines now sit in the warn band with ~500
chars of headroom, under **one rig-wide ceiling** — the reasoning for not giving
the dev server its own number is recorded beside the constant in
`rig-budget-eval.py`.

**If either machine reports `intercore-tests = skip`, that machine's build marker went missing.**

Runner: `~/.local/bin/rig-health-check.sh` → writes one JSON status file per check
to `~/.claude/health/`. Exits non-zero if any check failed, so the scheduler's own
state agrees with the status files.

Schedulers:

```
Clavain   ~/Library/LaunchAgents/com.arouth.rig-health.plist   (RunAtLoad + 09:15 daily)
zklw      ~/.config/systemd/user/rig-health.timer              (09:15 daily, Persistent)
zklw      ~/.config/systemd/user/settings-watchdog.service     (continuous)
```

A separate LaunchAgent from `com.arouth.claude-plugin-cleanup` on purpose: cleanup
is weekly, these want daily, and a failing check must not be able to stop cache
pruning or vice versa.

## The Go test suite runs on both machines — reversed 2026-07-27

`intercore-tests` runs on **Clavain and zklw**. It used to run only on Clavain,
and the reasoning recorded here for that was wrong on the facts.

The claim was "zklw has no Go and cannot get one without root that mk does not
have." Neither half held. A root-owned **go1.23.8 had been sitting at
`/usr/local/go` since March 2025**, absent from `PATH` in both login and
non-interactive shells and therefore invisible to `command -v go`. And a
user-local install needs no root at all: `~/.local/go` holds **go1.26.4**, chosen
to match Clavain's toolchain exactly so an artifact built on either machine is
comparable to the other.

The supporting argument was also weaker than it read. "Clavain compiles both
artifacts, so testing where the binary is produced is full coverage" is true
about *compilation* and says nothing about *execution* — the section admitted as
much two paragraphs later and then let the conclusion stand anyway. **Nothing
ran the linux binary on linux.** That is now covered: zklw's first scheduled run
reported `40 package(s) ok`.

This was found while fixing `mk-cg3z`, where the same missing toolchain made
zklw structurally unable to publish. One environment gap, two symptoms, and the
documentation asserted it was unfixable in both places.

Which machines are builders is marked by **tracked dotfiles artifacts**:

```
dotfiles/macos/.config/intercore/build-machine   →  ~/.config/intercore/build-machine
dotfiles/server/.config/intercore/build-machine  →  ~/.config/intercore/build-machine
```

Keying off `command -v go` instead would mean a machine that loses its toolchain
silently downgrades to `skip` and the check disappears — the exact vanishing-check
shape this whole effort exists to prevent. The marker inverts it: a **designated**
machine with no Go fails loudly; an undesignated machine skips quietly. Tracking
the marker in git means losing it shows up as a visible change rather than a
permanent silent skip.

### The timer saw a narrower PATH than you do

zklw's `rig-health.service` inherited systemd's user `PATH`, which does **not**
include `~/.local/bin`. Every tool installed there — `ic`, `go`, the `rig-*`
helpers — was invisible to the scheduled run while working perfectly when you
ran the same script by hand. The script had been absorbing this one binary at a
time, probing `${HOME}/.local/bin/ic` before falling back to `command -v ic`.
That works and hides the cause; the next tool added pays it again.

The service now sets `PATH` explicitly. Prefer that over another absolute-path
probe: a check that behaves differently under the scheduler than in your shell
is untrustworthy in both places.

## The advertisement budget, and why the ceiling is shaped this way

Every other check here watches **machinery**. None watched the number the
context-engineering program exists to hold — and it drifted **28,246 → 29,496 in
two days** without a word. The cause was `cujgel`: enabled while uninstalled
(genuinely free), then installed (1,250 chars). **Enablement and cost are
separated in time**, so watching `settings.json` was never going to catch it.
Only measuring does.

The instrument is checked in:

```
Sylveste/ops/scripts/advertisement-budget.py       # --json for tooling
dotfiles/common/.local/bin/rig-budget-eval.py      # ceiling + delta
```

It previously existed **only in a session scratchpad**, which is how three
baselines (34,141 / 46,416 / 36,837) were published and later retired as wrong.
An ad-hoc measurement gets re-derived slightly differently each time and two runs
cannot be diffed.

### Thresholds

| | | |
|---|---|---|
| `> 30,000` | **fail** | the number the program was run against — the contract |
| `>= 28,500` | **warn** | under ~5% headroom |
| jump `>= 250` in one run | **warn** | ~one added command description; self-clears |
| otherwise | pass | delta still reported in the summary |

**Why not a ratchet.** Failing on any increase over the last recorded value was
the alternative. It fires on every legitimate addition, so each deliberate plugin
enable would need an "accept the new baseline" gesture — and a check that must be
routinely dismissed is a check that gets dismissed when it matters. This rig
already had one alarm nobody could act on for four months. Unactionable alarms are
worse than none.

So: ceiling for the contract, warn band for early notice, per-plugin delta on
**every** run for attribution — including at pass, because "what moved" is useful
even when nothing is wrong. The one useful half of the ratchet is kept as the
single-run jump.

### The rig currently sits in the warn band, deliberately

29,496 with 504 chars of headroom. **The band was not widened to make that
green.** Calibrating a threshold to whatever you happen to measure is how a check
becomes decorative. The warn is true: the next plugin enabled at typical size
breaches the ceiling.

Known reclamation if headroom is wanted: Clavain's `plan-reviewer`, 887 chars
(`mk-hpkv`). `cujgel` was assessed and **kept** — at ~156 chars per entry it has
no `<example>` bloat and no demotable wrappers, so the only lever is removing
functionality. See `plugin-enablement-policy.md`.

### Baseline state

```
~/.claude/health/state/budget-previous.json     # per-plugin totals, for the delta
```

A subdirectory on purpose: the reporter globs `~/.claude/health/*.json`
non-recursively, so state files here cannot be mistaken for check results.

## Instrument freshness — an instrument reporting zero looks like an idle rig

zklw recorded **no usage data for 13 days** and nothing said so. `audit.log` held
25 lines from 2026-07-14; tool-time's `events.jsonl` stopped the same day;
`stats.json` regenerated daily reporting `total_events: 0`. Everything looked
installed and healthy.

The cost was not abstract. Thirteen plugin-enablement decisions on that machine
had to be made as **capability calls with no evidence**, because the evidence had
silently stopped existing (`plugin-enablement-policy.md`).

### Mechanism: the CLI has been logged out since 2026-07-14

```
2026-07-14 03:01   last tool-time event recorded
2026-07-14 16:24   ~/.claude/.credentials.json last written
        ...        no authenticated CLI session since
```

`claude -p` on zklw returns **`Not logged in · Please run /login`**. The hook
wiring is fine — that same aborted run shows Claude Code invoking tool-time's
`SessionEnd` hook (`Hook cancelled`), which proves plugin hooks are resolved and
called. There have simply been no authenticated CLI sessions to call them in.

Same shape as the autosync GitHub-token expiry: an expired credential silently
freezes a subsystem that goes on looking installed.

### Settled 2026-07-27: no Claude Code session runs on zklw at all

The open question was whether zklw's *remote* sessions run hooks. They do not —
and the reason is more fundamental than a hook-loading difference.

| Evidence | Finding |
|---|---|
| `ps` for `share/claude/versions` or `bin/claude` | **No Claude Code runtime process exists on zklw** |
| `strings` on `remote/srv/*/server` | **Zero** matches for `hook_event_name`, `SessionStart`, `PostToolUse` |
| Size of that binary | 6.3 MB, against the CLI's 251 MB |
| Its parent process | `tailscaled be-child ssh` — spawned per connection |
| tuivision MCP processes | Orphans (`ppid 1`) left by dead sessions; newest was spawned by this diagnosis's own aborted `claude -p` |

`~/.claude/remote/srv/*/server` is a **bridge**, not a session runtime. It gives a
Claude Code session running *on the client* access to zklw's filesystem and
shell. Hooks are executed by the session runtime, which is not on zklw.

**Consequence, stated plainly: every hook in zklw's `settings.json` is dead for
the work actually done there.** That includes `guard-enabled-plugins.sh`,
`git-autosync-pull.sh`, `canongraph-recall.py`, and `report-rig-health.py`
itself. zklw's checks were writing status files that nothing read — the same
failure this program exists to eliminate, one level up: not a check that never
runs, but a check that runs and reports into a void.

Fixed by reporting zklw's findings on the Mac — see "Peer reporting" below.

An earlier draft claimed the SessionStart hook "has never fired on zklw" because
the settings-history holds zero `session-start` commits. **That inference was
unsound and is retracted** — `settings-history-snapshot.sh` only commits when
settings.json actually *changed*, so a no-change session leaves no trace either
way. The conclusion happens to be right; the reasoning was not, and the
difference matters. `hook-heartbeat.sh` now exists precisely so this question has
an unconditional answer next time.

## Every Claude Code hook on zklw is inert — the full count

Chasing four named hooks turned up the real number. Nothing on zklw runs Claude
Code hooks, so **73 hook entries are registered there and none of them fire**:

| Source | Entries | Notes |
|---|---|---|
| `settings.json` (after pruning) | 7 | see the per-hook table below |
| Plugin-provided `hooks.json` | **66** across 24 enabled plugins | never audited before |

The plugin half was the surprise. Among them: `interlock` (4 hooks — multi-session
file reservation, which four-plus concurrent sessions are supposed to make
mandatory), `security-guidance` (9), `clavain` (17), `interspect` (3, whose whole
value is that its hooks "run continuously"), `tool-time` (5), `interwatch`,
`intertrack`.

**This has a budget consequence.** zklw pays advertisement for plugins whose value
is largely or wholly hook-delivered, and gets none of it. `interspect` at 668
chars is the clearest case. The enablement calls in
`plugin-enablement-policy.md` were made without knowing this and should be
revisited against it.

**Git hooks are unaffected** and still work. `install-server.sh` fans a
`pre-commit` scanner out to every `.git-autosync` repo; those fire on `git
commit`, which really does happen on zklw. Only *Claude Code* hooks are dead. The
distinction matters — the secret scanner still protects that machine.

### Per-hook disposition, zklw

| Hook | Event | Disposition |
|---|---|---|
| `guard-enabled-plugins.sh` | SessionStart | **Relocated** to the timer as `enablement-drift`. Registration kept: inert here, correct if CLI sessions resume. |
| `git-sync-check.sh` | SessionStart | **Registration removed.** Replaced by scheduled `autosync-health`. |
| `git-uncommitted-nudge.sh` | Stop | **Registration removed.** Same replacement. |
| `canongraph-recall.py` | SessionStart | **Registration removed.** Injects recalled context into a session prompt; there is no session here to inject into. |
| `canongraph-run-bridge.py` | Stop | **Registration removed.** Fires at session end; no session to end. |
| `git-autosync.sh` | PostToolUse | **Kept.** Autosync has no replacement; removing this discards the only wiring that exists. |
| `git-autosync-pull.sh` | SessionStart | **Kept**, same reason. |
| `log-tool-invocation.sh` | PostToolUse | **Kept.** Writes `audit.log`; per-tool-call work no timer can do. Its deadness *is* the audit.log outage. |
| `warn-agent-model-unset.sh` | PreToolUse | **Kept.** Harmless, correct if CLI resumes. |
| `report-rig-health.py` | SessionStart | **Kept.** Rescued by peer reporting. |
| `hook-heartbeat.sh` | SessionStart | **Kept.** The instrument that answers "did a hook fire here". |

No files were deleted anywhere. Four *registrations* were removed from zklw's
`settings.json` only; every script remains on disk and in dotfiles, and all of
them are still live on the Mac.

## Autosync on zklw is not running

`git-autosync` is **entirely hook-driven** — a PostToolUse hook commits and
pushes on edit, a SessionStart hook pulls. There is **no systemd machinery behind
it**, so on zklw it does nothing.

Measured 2026-07-27: 93 repos carry a `.git-autosync` marker; **14 hold
uncommitted work and 3 are unpushed.** Only 8 have ever recorded activity, most
stopping in June. This is why uncommitted work sat in `Sylveste` until a human
noticed earlier that week.

`autosync-health` now reports it. It needs **no staleness threshold**, which is
the point: uncommitted work on a dev machine is normal, but uncommitted work in a
repo that explicitly opted into auto-committing is a broken promise by
definition. The marker is the promise.

**Detection only — deliberately.** Committing and pushing unattended on a shared
server is a consequential change, not a default to restore quietly. The check
names the repos; whether a timer should push on mk's behalf is mk's call.

## Peer reporting — zklw's findings surface on the Mac

```
zklw   systemd timer -> checks run -> ~/.claude/health/*.json
Mac    daily job     -> rig-health-fetch-peers.sh -> ~/.claude/health/peers/zklw/
Mac    session start -> reported as "zklw:<check>"
```

Peers are listed in `~/.config/intercore/health-peers`. The fetch runs in the
**scheduled job, never in the SessionStart hook**, so session startup never waits
on ssh.

An unreachable peer writes an explicit marker rather than going quiet: otherwise
a lost peer looks exactly like a healthy one once its files age out. Peer
staleness is judged like local staleness, which also covers the fetch itself
dying.

Deliberately one-directional. Making it symmetric would have zklw fetching the
Mac's status and reporting it to nobody, for the reason above.

> Also worth recording: the settings-history could not date this outage, contrary
> to expectation. Its 347 commits stop at **2026-04-24** and resume 2026-07-26 —
> the watchdog was itself dead for three months before being repaired. A history
> with a hole in it is not a witness for the period inside the hole.

### The check: relative, not a plain age threshold

"Fail if the instrument is older than N days" is wrong twice over. An idle
machine trips it for behaving correctly, and a busy machine that stopped
recording passes for N days — exactly the window that hid this.

So the check compares each instrument against **independent proof that sessions
ran at all**: Claude Code rewrites `~/.claude.json` as it works. A fresh marker
plus a silent instrument means sessions ran and recorded nothing. A stale marker
means the machine was idle, and the check stays quiet.

Freshness is read from the timestamp **inside the last record**, never from
mtime. During this diagnosis a manual hook probe appended one line and the file's
mtime jumped from 13 days stale to fresh while the instrument was still dead. Any
diagnostic poke, backup tool, or editor would launder the signal the same way.

| Threshold | Value | Why |
|---|---|---|
| Activity window | 24h | Older marker ⇒ idle ⇒ silence is correct |
| Instrument silence | 48h | A session records within seconds of its first tool call, so any working day produces records. Two days absorbs a light weekend, a session that opened and did nothing, and clock skew — while catching a real outage on **day two instead of day thirteen**. |

Verified by forcing all seven branches: recording, the 13-day outage, idle
machine stays quiet, **mtime laundering still fails**, undateable record, missing
activity marker, and one-of-two instruments dead.

## `skip` is a third status, and it cannot hide a dead check

A `skip` says the runner ran and decided this check does not apply here. A
*missing* status file says the runner never ran. Those were previously
indistinguishable, so both new checks stay in the reporter's `EXPECTED` list.

Staleness still outranks `skip`: a skip that stops being refreshed is reported as
STALE like anything else. Skips print only alongside other findings, so a healthy
machine stays silent.

## ic build provenance

`ic version` used to print a compile-time constant and the **local database**
schema version. Two machines could report identical output while running binaries
built from different commits. Reading `schema: v36` vs `v38` as a build
difference produced a wrong diagnosis once; it describes the database, not the
binary, and the output now labels it as such.

```
$ ic version
ic 0.3.5
commit: cd0197f812e6
commit time: 2026-07-26T16:30:23Z (vcs)
target: darwin/arm64 go1.26.4
schema: v39 (local database)
```

Provenance comes from `-ldflags` if a build script sets them, otherwise from Go's
own VCS stamping. The fallback is the load-bearing half — requiring a build script
to remember ldflags means the stamp goes missing exactly when someone builds in a
hurry. `ic --json version` emits the same machine-readably, which is what the
check consumes; grepping prose is how checks quietly start matching nothing.

**Why lag is a failure here but only informational for plugin installs:** a
trailing plugin install self-heals the next time Claude Code restarts. Nothing
ever rebuilds `ic`. Lag is permanent until a human acts.

Rebuild and redeploy:

```bash
cd ~/projects/Sylveste/core/intercore
go build -o ~/.local/bin/ic ./cmd/ic                      # Clavain
GOOS=linux GOARCH=amd64 go build -o /tmp/ic-linux ./cmd/ic
scp /tmp/ic-linux zklw:~/.local/bin/ic.new
ssh zklw 'chmod +x ~/.local/bin/ic.new && mv ~/.local/bin/ic.new ~/.local/bin/ic'
```

The tree must be **clean** when you build, or the stamp reads `-dirty` and
`ic-provenance` fails — correctly, since a dirty binary matches no commit.

## `doctor`'s per-plugin findings: informational by direction

Seven `installed=X marketplace=Y` findings stood open on zklw, making
`ic publish doctor` exit non-zero on a healthy machine. The decision (`mk-fkfr`)
is **not** to watch them, and it is encoded in `checkInstalledDrift` rather than
left as standing noise:

- **installed BEHIND marketplace → `info`.** This is the normal steady state
  between a publish and the next Claude Code restart. It self-heals with no human
  action. A check that cries wolf during normal operation gets ignored, which is a
  slower way of not running it.
- **installed AHEAD of marketplace → `error`.** Cannot arise from any normal
  path; a cache holding a version the marketplace never published does not
  self-heal.

Two tests in `internal/publish/installed_drift_test.go` pin the asymmetry,
including one asserting a trailing-only machine comes back clean. Restoring a
blanket `error` severity fails them with the reason attached.

The consequence to accept: if a machine's Claude Code stopped reinstalling
entirely, nothing here would say so. That is a real gap, traded for a check that
is believed when it does fire.

## How you hear about it

`report-rig-health.py`, a SessionStart hook on both machines, reads
`~/.claude/health/` and prints to stderr — which Claude Code surfaces. It is
**silent when everything passes**, so output always means something.

It reports three conditions, and the third is the point:

- **FAIL** — a check ran and found a problem.
- **NEVER** — no status file at all; the scheduled job has not run here.
- **WARN** — a real finding that is not yet a breach (the budget inside its
  headroom band). It prints, so it cannot be missed by accident, but it does not
  claim something is broken. Keeping WARN and FAIL apart is what lets FAIL stay
  believable.
- **STALE** — a status file older than twice its interval. *A check reporting
  "fail" is working as designed; a check whose status has stopped being updated
  has itself died.* That is exactly what happened to the guard, so a stale `pass`
  is reported as loudly as a failure.

Deleting the whole health directory produces three findings, not silence.

## Detection latency

| Event | Detected within | Then surfaced |
|---|---|---|
| Guard tests break | 24h | next session start |
| Settings reference stops resolving | 24h | next session start |
| Marketplace clones diverge | 24h | next session start |
| An intercore test starts failing | 24h (Clavain only) | next session start |
| Deployed `ic` falls behind intercore HEAD | 24h | next session start |
| `ic` deployed from a dirty or unstamped build | 24h | next session start |
| Advertisement budget crosses 30,000 | 24h | next session start |
| Budget enters the 28,500 warn band | 24h | next session start |
| A plugin's advertised cost changes at all | 24h | named in the delta |
| A usage instrument stops recording while sessions run | 48h + 24h | next session start |
| Live settings drift from the approved reference | 24h | next session start (zklw: via the Mac) |
| An autosync repo stops being auto-committed | 24h | next session start (zklw: via the Mac) |
| settings.json changes, **zklw** | ~10s | in the git history immediately |
| settings.json changes, **Clavain** | next session start, or 24h | recorded, not alerted |
| **A check stops running** | 48h (2× interval) | next session start |

Both new checks inherit the same 24h cadence and the same 48h stale threshold;
nothing about them runs on a different clock.

Caveats that are real, not theoretical:

- **launchd does not fire while the Mac is asleep.** A closed laptop defers the
  09:15 run until wake. `RunAtLoad` covers boot/login. This is why the stale
  threshold is 2× rather than 1×: a laptop shut for a weekend would otherwise
  cry wolf every Monday.
- zklw adds `RandomizedDelaySec=300`, so the real fire time is 09:15–09:20.
- zklw's timer is `Persistent=true`: a run missed while the box was down fires
  after boot instead of being skipped. A skipped run and a healthy day must not
  look alike.
- Both survive logout/reboot: launchd agents are per-user and load at login;
  zklw has `Linger=yes`, so user units run without an active session.

## The marketplace check runs from outside the tree

`rig-health-check.sh` runs `ic publish doctor` with `cwd=$HOME`, deliberately.

`ic publish` resolves the marketplace by walking up from cwd: inside the Sylveste
tree it finds `core/marketplace`, outside it finds the Claude Code checkout. The
old doctor check opened with `if absMarket == absCCPath { return }` — true
precisely when run from outside — so it disabled itself in the one directory where
divergence gets created. That vantage point is therefore the one worth automating.

## The watchdog decision

**Decision: run it, on zklw, in polling mode.** (`mk-1wj0` follow-through.)

It had been installed at `~/.local/bin/settings-watchdog.sh` since March and never
running. The reason was not neglect: **`inotify-tools` is not installed on zklw**,
installing it needs root that mk does not have, and the script required
`inotifywait` at startup — so it exited 1 and nothing said so. Requiring a tool
absent on both machines is the same silent-no-op shape as the dead reference path.

It now prefers `inotifywait` and falls back to polling size+mtime every 10s. One
stat per interval is free. What is genuinely lost: a change made *and reverted*
between polls is invisible.

This history is not decoration. zklw's 340+ snapshots are the only reason the
2026-07-24 `enabledPlugins` drift could be reconstructed at all — mtimes alone
could not say who changed what.

**Clavain runs no watchdog daemon.** macOS has no `inotifywait`, and a persistent
poller on a laptop is not worth the battery. Instead the SessionStart hook takes a
snapshot, so a change made during session N is captured at the start of session
N+1, plus the daily scheduled run. Say it plainly: **on Clavain, a settings change
made and reverted within one session is not recorded.** zklw catches that; Clavain
does not.

```
~/.claude/settings-history/     # git repo, one commit per observed change
git -C ~/.claude/settings-history log --oneline
```

## What is still manual

- **Acting on findings.** The reporter tells you; nothing self-heals. That is
  deliberate — `--approve` and `--fix` stay human-triggered, and `ic` is never
  rebuilt automatically.
- **Rebuilding and redeploying `ic`** when `ic-provenance` reports lag. The check
  names the gap; closing it is a human step (command above).
- **Testing the linux binary on linux.** Clavain cross-compiles it and tests the
  source; nothing exercises the artifact on its target OS.
- **`ic publish doctor`'s remaining per-plugin categories.** Clone divergence is
  automated and installed-drift is now classified; anything else doctor reports
  is only seen when a human runs it.
- **Re-copying systemd units after a dotfiles change** — see below.
- **Autosync on zklw.** It is hook-driven with no systemd replacement, so it does
  not run. `autosync-health` now *detects* the damage; nothing repairs it.
  Committing and pushing unattended on a shared server is a decision, not a
  default — see below.
- **Reclaiming budget headroom.** The check reports the number and names what
  moved; deciding what to demote, slim, or disable stays a human call.
- **Catching a cost increase faster than daily.** A plugin installed mid-session
  bills immediately but is not measured until the next scheduled run.

The daily run now takes **roughly two minutes on Clavain** (it was seconds).
`go test ./...` is ~13s interactively but ~100s under launchd's scheduling
priority. That is well inside a daily budget, but it is no longer instant.

## Runbook

```bash
# Run every check now (~2 min: the Go suite dominates)
rig-health-check.sh ; echo "exit=$?"

# Force a failure without touching the real repo, binary, or health files
RIG_HEALTH_DIR=/tmp/h RIG_INTERCORE_DIR=/path/to/throwaway/clone rig-health-check.sh
RIG_HEALTH_DIR=/tmp/h RIG_IC_BIN=/path/to/other/ic rig-health-check.sh

# See what a new session would say
python3 ~/.claude/hooks/report-rig-health.py </dev/null

# Current status, machine-readable
cat ~/.claude/health/*.json

# zklw: reinstall/refresh the systemd units after editing them in dotfiles
bash ~/projects/dotfiles/server/.local/bin/install-rig-health-units.sh --enable

# Clavain: reload the LaunchAgent after editing the plist
launchctl unload ~/Library/LaunchAgents/com.arouth.rig-health.plist
launchctl load   ~/Library/LaunchAgents/com.arouth.rig-health.plist
launchctl kickstart -k gui/$(id -u)/com.arouth.rig-health   # run it now
```

**systemd units are copied, not symlinked.** `systemctl --user disable` deletes a
unit file that is itself a symlink — `settings-watchdog.service` vanished that way
mid-setup. Copies can drift from the dotfiles checkout, which is what
`install-rig-health-units.sh` is for: re-run it after any unit edit.

## Related

- `mk-1wj0` — the four-month guard outage this all descends from
- `mk-963o` — marketplace clone divergence
- `mk-ldnb` — publish machine roles
- `mk-fkfr` — the un-automated surfaces this page closed
- dotfiles `902cef3`, `fbb8e6b`, `47ba9eb`, `55b2fb1`, `c518309`, `01b6b79`, `845ad06`
- intercore `cd0197f` — build stamp + drift classification
