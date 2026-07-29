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
| `guard-tests` — **every** suite in `hooks/tests/` (31 tests, 3 suites) | launchd | systemd timer | daily 09:15 |
| `settings-reference` — does a reference actually resolve | launchd | systemd timer | daily 09:15 |
| `marketplace-divergence` — do the clones agree | launchd | systemd timer | daily 09:15 |
| `intercore-tests` — `go test ./...` for the suite gating `ic` | launchd | systemd timer | daily 09:15 |
| `ic-provenance` — does the deployed binary match the source | launchd | systemd timer | daily 09:15 |
| `advertisement-budget` — what enabled plugins cost in context | launchd | systemd timer | daily 09:15 |
| `instrument-freshness` — are the usage instruments still recording | launchd | systemd timer | daily 09:15 |
| `enablement-drift` — do live settings still match the approved reference | launchd | systemd timer | daily 09:15 |
| `autosync-health` — are opted-in repos actually being synced | launchd | systemd timer | daily 09:15 |
| `hook-liveness` — are the registered hooks actually firing | launchd | systemd timer | daily 09:15 |
| `peer-agreement` — do this machine and its peers agree on what must match | launchd | systemd timer | daily 09:15 |
| `autosync-repair` — commit and push what the marker promised | — | **systemd timer** | daily 08:45 |
| settings.json history | SessionStart + daily | **continuous, 10s poll** | see below |

Expected steady state, so a drift is auditable against something:

```
Clavain   guard-tests pass   settings-reference pass   marketplace-divergence pass
          intercore-tests PASS    ic-provenance pass    advertisement-budget WARN
          peer-agreement PASS
zklw      guard-tests pass   settings-reference pass   marketplace-divergence pass
          intercore-tests PASS    ic-provenance pass    advertisement-budget WARN
          peer-agreement PASS
```

Both machines run `peer-agreement`, and that is the point: each compares the
other independently, so a divergence is seen twice rather than depending on one
machine's scheduler being alive.

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

## `job-outcomes` — the schedulers were never watched

Added 2026-07-28. Every check above watches the rig. Nothing watched the things
that *run* the rig, and they had been failing in the open.

What the first run found, all of it previously silent:

| Machine | Finding |
|---|---|
| **Clavain** | **Both off-site B2 backups dead since 2026-07-25** — a stale restic lock from a dead PID, failing every 4 hours. The local Synology copy kept succeeding, so the backup story looked fine. Unlocked; B2 now completes (`mk-elhy`). |
| zklw | `canongraph-backup` exit 1, `jawnverse-pg-backup` timeout, `remontoire` exit 1, `caddy-routes` 203/EXEC **since 2026-07-13** (`mk-ud80`) |
| zklw | 3 nightly Claude Code automations failing for 14 days |

### The evidence was never missing

This is the part worth keeping. Nothing here was hidden:

- `claude -p` **exits 1** on an authentication failure — measured, not assumed
- `~/.config/restic/backup-b2.sh` **exits 11** — and restic's own error names the
  fix, `the unlock command can be used to remove stale locks`
- systemd recorded `Result=exit-code` for every failed unit
- launchd recorded `LastExitStatus` for every failed agent

Every one of those commands was honest. **What did not exist was a channel.**
That crontab has no `MAILTO`, so a non-zero exit has nowhere to go;
`systemctl --user list-units --failed` and `launchctl list` hold the answers and
nothing reads them; the logs are opened when you are already suspicious, which is
the one time you do not need them.

So the fix is not "make the jobs honest". They were. It is to read what they
already say.

### Receipts and the check are not redundant — the argument

The tempting simplification is that per-job receipts make an external reader
unnecessary. They do not:

> **A receipt cannot report its own absence.**

Disable a timer, delete a crontab line, or leave the machine asleep and no
receipt is written — which is indistinguishable from "not due yet" unless
something independently knows what was *supposed* to run. So the two cover
different failures:

| | answers |
|---|---|
| `rig-job-receipt.sh` | *did this run succeed?* — where the outcome would evaporate |
| `rig-job-outcomes.py` | *did everything scheduled produce an outcome at all?* |

What **is** redundant is wrapping systemd and launchd jobs in receipts. Both
already store the result durably until the next run. **Where the outcome
survives, read it; where it evaporates, capture it.** Receipts are therefore
used for cron and nothing else — on this estate, three lines.

### Every job declares what non-zero means

A naive alert on `--failed` would fire forever on two units that are working
perfectly: `rig-health` exits non-zero whenever any check fails (that is its
contract, so the scheduler agrees with the status files) and
`git-autosync-repair` exits non-zero when a repo needs a human. Alerting on
those teaches the reader to ignore the one list that matters.

So the meaning is declared beside the job. systemd units and crontabs take `#`
comments and plists take XML comments, so in every case it lives in the unit
itself rather than a side table that drifts away from it:

```
# rig-outcome: verified
#   restic backup to B2; a non-zero exit means no backup was taken
```

| Class | Meaning | Behaviour |
|---|---|---|
| `verified` | the work did not happen | **fail** |
| `finding` | the job ran fine and has something to say | named, never alerted |
| `ignore` | the outcome genuinely does not matter | silent, but stated |

An **unclassified** scheduled job is a failure of this check, not a skip.
"Nobody has decided what this job's failure means" is exactly the state that
produced the fourteen days, and it has to cost something to leave it there. It
proved itself immediately: three `estate-*` units created the same afternoon
were flagged within minutes of being written.

### Two Clavain agents want unloading, not classifying

`com.sma.mount-slse-projects` pings `100.97.18.105` — the retired slse address,
decommissioned 2026-04-29 — and exits 68 forever. `com.sma.zklw-reboot-once` is a
one-shot kdump reboot scheduled for 2026-05-02, still loaded on a daily 03:00
interval. Both are classified `ignore` **only to stop the noise**; the reasoning
recorded in each plist says plainly that the correct fix is to unload them, which
is a human decision rather than a classification.

## `hook-liveness` — registration is not evidence

Added 2026-07-28. Every other check here watches something a hook *does*. None
watched whether the hooks run at all, and on zklw they had not since 2026-07-14.

The check reads `settings.json` for what is registered, then looks for records
the hooks themselves wrote, per event, and separates four answers that must never
merge:

| Answer | Meaning | Status |
|---|---|---|
| `alive` | the event fired inside 24h; its hooks were invoked | pass |
| `untriggered` | the event's trigger never occurred — no session started, or no tool ran | pass |
| `dead` | the trigger *did* occur and the event left no record | **fail** |
| `unobservable` | no registered hook on that event writes a dated record, so nothing can be concluded | **warn, never pass** |

Evidence is per-event because Claude Code invokes *every* hook registered for an
event: one heartbeat line for `SessionStart` proves all four SessionStart hooks
were invoked. It proves **invocation, not success** — a hook that runs and fails
silently still looks alive from here, and proving each hook's effect is that
hook's own job.

The evidence map lives in `rig_session_evidence.py`. Adding a hook to it is the
cheap way to make its event observable; registering `hook-heartbeat.sh` on more
events is the expensive way, because on `PostToolUse` that is an interpreter
spawned on every single tool call to learn what `audit.log` already records.

### The loud case names the cause, not the symptom

On zklw the check reports:

```
11 session(s) started in the last 1.0d and all 11 failed authentication --
every tool-triggered hook (PostToolUse, PreToolUse) is dead until
`claude /login` is run on this machine
```

not "PostToolUse is dead". An operator told the latter goes and reads PostToolUse
hooks, all seven of which are fine. Naming the cause is the difference between a
check that finds a bug and a check that starts a search.

### Blind spots on Clavain, stated rather than hidden

`PreToolUse`, `Stop` and `PreCompact` are `unobservable` on the Mac — no hook
registered on them writes a dated record. Left that way deliberately: observing
`PreToolUse` costs a write on every tool call, forever, to watch three guards.
`PreCompact` is excluded from the dead/triggered logic entirely, because "overdue"
is not definable for an event that fires unpredictably, and treating a rare event
as overdue manufactures failures. They stay named in every run's summary.

Full per-hook disposition on both machines:
`dotfiles/common/.claude/hooks/README.md`.

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

### RETRACTED 2026-07-28: "no Claude Code session runs on zklw at all"

**This section was wrong, and it was load-bearing.** It is kept rather than
deleted because three later decisions were built on it and none of them make
sense without seeing the mistake.

zklw runs roughly **11 Claude Code sessions a day**. There are 281 session
transcripts under `~/.claude/projects/`. Every one since 2026-07-14 07:13 dies at
`authentication_failed` — 179 of the 281 — because the CLI is logged out
(`mk-q6bl`). SessionStart hooks fire on every one of them, correctly, and have
throughout. What is dead is `PreToolUse` and `PostToolUse`, and only because the
session ends before its first tool call.

**How the wrong conclusion was reached, since the method is the lesson:** the
evidence below is a `ps` snapshot. zklw's sessions are launched by systemd
timers, live about two seconds, and fail. Sampling `ps` between them finds
nothing and looks exactly like a machine that runs no sessions at all. A
point-in-time probe was used to prove a claim about all time — which is the same
error as reading an instrument's silence as proof of idleness, one level up.
`hook-heartbeat.sh` and `rig-hook-liveness.py` now answer this from records
rather than from a snapshot.

Corrected disposition of everything below: see
`dotfiles/common/.claude/hooks/README.md`, which is beside the scripts.

The original evidence and reasoning, as recorded on 2026-07-27:

| Evidence | Finding (as claimed then) |
|---|---|
| `ps` for `share/claude/versions` or `bin/claude` | ~~No Claude Code runtime process exists on zklw~~ — a snapshot between short-lived scheduled runs |
| `strings` on `remote/srv/*/server` | **Zero** matches for `hook_event_name`, `SessionStart`, `PostToolUse` |
| Size of that binary | 6.3 MB, against the CLI's 251 MB |
| Its parent process | `tailscaled be-child ssh` — spawned per connection |
| tuivision MCP processes | Orphans (`ppid 1`) left by dead sessions; newest was spawned by this diagnosis's own aborted `claude -p` |

`~/.claude/remote/srv/*/server` is a **bridge**, not a session runtime. It gives a
Claude Code session running *on the client* access to zklw's filesystem and
shell. Hooks are executed by the session runtime, which is not on zklw.

~~**Consequence, stated plainly: every hook in zklw's `settings.json` is dead for
the work actually done there.**~~ **False.** `guard-enabled-plugins.sh`,
`git-autosync-pull.sh`, `canongraph-recall.py` and `report-rig-health.py` are all
SessionStart hooks and all of them fire, many times a day.

What survives of this paragraph is the *second* half, and it is still true and
still the reason peer reporting exists: zklw's sessions are **headless**, so
everything those hooks print goes into a transcript with no human attached. A
hook that fires into a void and a hook that never fires are different faults with
the same symptom, and conflating them cost fourteen days.

Fixed by reporting zklw's findings on the Mac — see "Peer reporting" below.

An earlier draft claimed the SessionStart hook "has never fired on zklw" because
the settings-history holds zero `session-start` commits. **That inference was
unsound and is retracted** — `settings-history-snapshot.sh` only commits when
settings.json actually *changed*, so a no-change session leaves no trace either
way. The conclusion happens to be right; the reasoning was not, and the
difference matters. `hook-heartbeat.sh` now exists precisely so this question has
an unconditional answer next time.

## ~~Every Claude Code hook on zklw is inert~~ — the full count, re-read

**Corrected 2026-07-28.** The count is right; the verdict on it is not. 73 hook
entries are registered on zklw. They are not all inert — the SessionStart ones
fire on every scheduled session, which is about eleven times a day. Only the
tool-triggered ones are dead, and only because the session dies at
authentication first.

| Source | Entries | Notes |
|---|---|---|
| `settings.json` (after pruning) | 7 | see the per-hook table below |
| Plugin-provided `hooks.json` | **66** across 24 enabled plugins | never audited before |

The plugin half was the surprise. Among them: `interlock` (4 hooks — multi-session
file reservation, which four-plus concurrent sessions are supposed to make
mandatory), `security-guidance` (9), `clavain` (17), `interspect` (3, whose whole
value is that its hooks "run continuously"), `tool-time` (5), `interwatch`,
`intertrack`.

~~**This has a budget consequence.** zklw pays advertisement for plugins whose
value is largely or wholly hook-delivered, and gets none of it.~~ **Overstated.**
Plugin SessionStart hooks fire like any other. What zklw loses is the
tool-triggered half — which for `interspect` and `tool-time`, whose value really
is per-tool-call, is most of it. The enablement calls in
`plugin-enablement-policy.md` should still be revisited, but against "the
PostToolUse half is dead until authentication is restored", not against "none of
it runs".

**Git hooks are unaffected** and still work. `install-server.sh` fans a
`pre-commit` scanner out to every `.git-autosync` repo; those fire on `git
commit`, which really does happen on zklw. Only *Claude Code* hooks are dead. The
distinction matters — the secret scanner still protects that machine.

### Per-hook disposition, zklw

Revised 2026-07-28. "Fires?" is measured, not inferred — `rig-hook-liveness.py`
reads records the hooks themselves wrote.

| Hook | Event | Fires? | Disposition |
|---|---|---|---|
| `guard-enabled-plugins.sh` | SessionStart | yes | **Keep.** Protective function still belongs on the timer as `enablement-drift`, because the hook's output is headless — but it is not inert. |
| `git-autosync-pull.sh` | SessionStart | yes | **Keep.** Has been working the whole time. |
| `report-rig-health.py` | SessionStart | yes | **Keep.** Fires; findings travel to the Mac by peer reporting because nobody reads a headless transcript. |
| `hook-heartbeat.sh` | SessionStart | yes | **Keep.** The evidence channel that settled all of this. |
| `git-autosync.sh` | PostToolUse | **no** | **Keep.** Dead for want of authentication, not of a trigger. |
| `log-tool-invocation.sh` | PostToolUse | **no** | **Keep.** Its deadness *is* the audit.log outage. Matcher here is `Skill\|Agent`, narrower than the Mac's. |
| `warn-agent-model-unset.sh` | PreToolUse | **no** | **Keep.** Previously kept as "harmless". Stronger than that: zklw's scheduled jobs spawn agents, so once auth returns it advises more spawns than the Mac does. |

### Two registrations were removed on the false premise

`git-sync-check.sh` (SessionStart) and `git-uncommitted-nudge.sh` (Stop) were
removed and replaced by the scheduled `autosync-health` check. **That still
stands** — an advisory nudge printed into a headless transcript helps nobody, and
the reasoning holds independently of whether sessions run.

`canongraph-recall.py` (SessionStart) and `canongraph-run-bridge.py` (Stop) were
removed with the reason "there is no session here to inject into" and "no session
to end". **Both reasons were false.** There are eleven sessions a day and they do
end. These two are doing real agent work when authenticated — the
`agmodb-production-runner` plan-backlog burn-down among them — so recall and the
run bridge would have applied to exactly the sessions that most needed them.

Not restored in this pass, deliberately:

- It changes nothing until authentication is restored on zklw.
- Editing `settings.json` requires re-adopting the settings reference or
  `enablement-drift` reports drift the next morning; that is a separate
  deliberate act, not a side effect of a documentation fix.
- Whether headless burn-in jobs *should* write into CanonGraph is mk's call, not
  a correction to be smuggled in under a retraction.

Carried as a decision in the handoff, alongside `claude /login`.
| `report-rig-health.py` | SessionStart | **Kept.** Rescued by peer reporting. |
| `hook-heartbeat.sh` | SessionStart | **Kept.** The instrument that answers "did a hook fire here". |

No files were deleted anywhere. Four *registrations* were removed from zklw's
`settings.json` only; every script remains on disk and in dotfiles, and all of
them are still live on the Mac.

## Autosync on zklw — detected, then repaired

`git-autosync` is **entirely hook-driven** — a PostToolUse hook commits and
pushes on edit, a SessionStart hook pulls. There is **no systemd machinery behind
it**, so on zklw it did nothing.

Measured 2026-07-27: 93 repos carry a `.git-autosync` marker; **14 held
uncommitted work and 3 were unpushed.** Eleven have ever recorded activity, the
most recent stopping 2026-07-22. This is why uncommitted work sat in `Sylveste`
until a human noticed earlier that week.

`git-autosync-repair.sh` now runs on a **systemd timer** at 08:45, half an hour
before the health check, so `autosync-health` reports the state *after* repair.
A timer and not a hook: that is the entire lesson of the outage. First run took
it to **5 dirty, 4 unpushed** — the rest correctly refused.

### Why an allowlist, not "commit everything except…"

Decided with mk after triaging what was actually sitting there, because the
working tree answered the question. It contained:

- **`.beads/.beads-credential-key`** — 32 bytes, mode `0600`, **not gitignored**
- **`.beads/hooks/pre-commit`** — a *type change*: the tracked regular file had
  been replaced by a symlink to `~/projects/dotfiles/cloud/pre-commit.sh`, a
  path that exists only on that machine

A `git add -A` would have pushed a secret to GitHub and broken a hook in every
other checkout. **Neither would have appeared on a denylist written before
seeing them.** A denylist is only as good as the last surprise.

So the repairer commits `uv.lock`, `.beads/issues.jsonl`, `.git-autosync`, and
`docs/diagrams/*.html` — and reports everything else. Hand-authored work is
never touched: `core/agent-rig` has held a deliberate 8-line migration since
2026-07-10, and a tool that swept that into "chore: autosync" would be eating
the work it exists to protect.

### It refuses rather than guesses

Rebase, merge, cherry-pick or bisect in progress · detached HEAD · unresolved
conflicts · a non-empty index · unreachable remote · no upstream · no remote at
all · any type change even on an allowed path · **a branch that has genuinely
diverged**, because rebase-vs-merge is an editorial choice about history that a
script does not get to make.

Two of those were found by *forcing* them, not by reading code:

- `ls-remote --exit-code origin HEAD` exits 2 when nothing **matches**, which
  includes a perfectly reachable remote whose HEAD is an unborn branch. The
  repairer called that "unreachable".
- A repo with **no upstream** was counted as *clean*, because `ahead` cannot be
  computed without a tracking branch. Work that had never left the machine,
  reported as nothing to do — the exact failure the tool exists for, hiding
  inside the tool.

### Sync before committing

The first real run committed onto branches that were already **behind**, because
the *pull* half of autosync had not fired here either and local refs were up to
**59 commits** stale. Behind + a new local commit = diverged, and no
fast-forward fixes that afterwards: every commit succeeded and nine pushes were
rejected non-fast-forward.

It now fetches first and fast-forwards with `--ff-only`, which cannot conflict
and cannot invent a commit. Only repos with something to send are fetched —
fetching all 93 daily would take on merge risk for no benefit on a machine that
reads nothing.

### The marker population: audited, and kept whole

The suspicion was that 122 markers on a machine that never honoured them meant
the set had sprawled. It had not:

| | |
|---|---|
| markers | **93**, not the ~122 the docs claimed — and 93 at *every* search depth |
| with a remote **and** an upstream | **93 of 93** — the promise is keepable |
| no remote / no upstream / archived / dead >180d | **0 / 0 / 0 / 0** |

The population was never the problem. Shrinking it would have removed the
promise instead of keeping it, and made the rig quieter without making it
truer. The reasoning lives in `git-autosync-repair.sh`, beside the code that
reads the marker.

One correction the audit forced: autosync **has** run here. Eleven repos hold a
`.git/autosync.log`, the most recent from 2026-07-22. "Ran rarely, then
stopped" is accurate; "never fired" is not.

### The repairer is watched the same way a check is

It writes its own `autosync-repair` status file on its **own** timer, so if it
stops running the file ages out and the reporter says STALE — the identical
mechanism that catches a dead check. No fixer for the fixer.

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
                        ...and PUSHES ~/.claude/health/facts.json to zklw
Mac    session start -> reported as "zklw:<check>"
```

Peers are listed in `~/.config/intercore/health-peers`. The fetch runs in the
**scheduled job, never in the SessionStart hook**, so session startup never waits
on ssh.

An unreachable peer writes an explicit marker rather than going quiet: otherwise
a lost peer looks exactly like a healthy one once its files age out. Peer
staleness is judged like local staleness, which also covers the fetch itself
dying.

**One direction of ssh, two observers.** The Mac has no inbound sshd, so zklw
cannot open the connection. It does not need to: the same visit that collects
zklw's statuses also deposits the Mac's `facts.json` at
`~/.claude/health/peers/Clavain/.facts.json`, which is where zklw's own agreement
check reads it. Both machines run the comparison independently and zklw's verdict
comes home in the next fetch.

An earlier note here said symmetry was pointless because zklw would report to
nobody. That stopped being true the moment peer reporting existed — a verdict
zklw reaches does arrive. The real constraint is just the missing sshd.

> Also worth recording: the settings-history could not date this outage, contrary
> to expectation. Its 347 commits stop at **2026-04-24** and resume 2026-07-26 —
> the watchdog was itself dead for three months before being repaired. A history
> with a hole in it is not a witness for the period inside the hole.

## Collecting from a peer is not comparing against it — `peer-agreement`

Nine statuses arrived from zklw every day and **not one was compared against the
Mac's**. Every check answered "is this machine healthy", none answered "do these
two machines agree", and three divergences had already happened by 2026-07-27,
each found by accident:

- Both machines build `ic` from their own clone, and `ic-provenance` compares
  each binary against its **own** clone. Two machines can sit at different
  commits with both reporting pass.
- Publishing clavain 0.6.292 from zklw hit a rebase conflict because zklw's
  marketplace clone was stale for interflux; taking the local side would have
  rolled interflux **backwards**. `ic publish doctor` detects clone divergence
  only *within* one machine.
- Both machines run go1.26.4 and the release verifier pins the manifest's
  `go_version`, so an upgrade on one makes digests unreproducible on the other,
  silently, until a publish fails (`mk-wuwp`).

### What is compared

| Fact | Why it must match |
|---|---|
| `go_toolchain` | The `go` that will build the next release. `bin/release-manifest.json` pins `go_version` and the verifier asserts each binary's embedded version equals it exactly. |
| `intercore_commit` | The source both machines build `ic` from. `ic-provenance` only asks "current with **my** clone", so a machine that is behind passes while shipping an older binary than its peer. |
| `ic_commit` | The deployed binary's own stamp. Identical clones plus one machine that forgot to rebuild is a real state, and only this catches it. |
| `marketplace_plugin_versions` | The name→version map, **not the git SHA**. SHAs disagree constantly and harmlessly while a clone waits to pull; versions disagreeing is what causes damage. |

### What is deliberately NOT compared

This half matters as much. A wall of expected errors teaches you to skip the
output, which is exactly how the four-month guard outage (`mk-1wj0`) survived.

| Fact | Why comparing it would be wrong |
|---|---|
| advertisement budget | Differs **by design** — different enablement sets. 28,452 vs 29,360 is the policy working. |
| enabled plugin set | Differs **by design**, same reason. The enablement policy is per-machine. |
| plugin source repo HEADs | Clavain is the *verifier* role; its checkouts trail the marketplace and that is the documented steady state. Comparing them rebuilds the 21-error wall `publish-machine-roles.md` removed. |
| installed plugin versions | The Mac runs plugins; zklw starts no sessions, so its installed set is meaningless. |
| intercore DB schema | Per-machine database, migrated on first use. Different versions between migrations are correct. |
| the Go that built `ic` | `ic` is not digest-verified by anything, so its build toolchain carries no downstream contract. Only the toolchain that builds *release artifacts* matters. |

The reasoning lives in `rig-facts.py` beside each collector, so the code and this
table cannot drift apart.

### Exit codes, again

`1` diverged · `2` no peer configured · `3` cannot compare (stale or missing
facts). "I have no peer" and "we disagree" are opposite statements and must not
share a code — the same discipline as the release verifier's reserved exit 3.
Stale peer facts produce a **warn**, never a fail: comparing three-day-old values
would yield confident findings about a machine's past.

Divergence is a **failure**, not a warning, because every fact here has a
demonstrated failure mode that does not self-heal. A warning would be right for
something the next scheduled run repairs by itself; nothing here does.

## The reporter was the one thing nothing watched

The audit that came with `peer-agreement` asked whether peer reporting had the
guard's shape. Most of it does not: a peer that stops running ages out to STALE,
an unreachable peer writes a marker, a dead fetch shows up as aging files, and a
dead scheduler shows up because the reporter still runs at session start.

One gap was real. **The SessionStart reporter is the only channel from this
system to a human, and nothing watched the channel.** Unregister the hook and
every check still passes, every status file still updates, and the findings
simply stop arriving.

The reporter now appends to `~/.claude/health/reporter-heartbeat.jsonl`, and
`instrument-freshness` treats it as an instrument like `audit.log` — read from
the timestamp *inside* the last record, and only meaningful where sessions
actually start (zklw correctly reports it "not present").

**This does not close the gap, and pretending otherwise would be the same
mistake.** A hook cannot announce its own absence through itself; the detector
runs on the scheduler, but its finding is delivered by… the reporter. What the
heartbeat buys is that the gap becomes **measurable and dated**: the first
session after a reporter outage says how long it lasted, instead of the outage
being invisible in both directions. Closing it properly needs an out-of-band
channel — a push notification, a peer that alarms on the Mac's silence — and
that is not built. The honest statement is that this is a *bootstrap floor*, not
a covered case.

### Corrected 2026-07-29 — the peer alarm IS built. Delivery is what is not.

The paragraph above says a peer that alarms on the Mac's silence "is not built".
That was wrong, and the goal that asked for a decision here assumed the same
thing. All three failure modes were **forced** rather than reasoned about, using
`RIG_HEALTH_DIR` and `RIG_FACTS_STALE_AFTER` against sandbox copies, so no live
state was touched:

| forced condition | what actually happens |
|---|---|
| Mac's status files aged 8 days (laptop shut) | reporter: `12 stale`, each line naming *"the check itself stopped running"* |
| agent unloaded, files frozen 2 days | reporter: `12 stale`, same |
| status files absent entirely | reporter: `12 never ran` + `PEER zklw configured but no status files fetched yet` |
| Clavain's facts on zklw aged past threshold | `rig-peer-agreement.py` returns **3** → `write_status warn` → surfaces in the report |

So the reporting path does **not** fail in the way that looks healthy. It fails
loudly, in two places independently, and each half fires under forcing.

The correct distinction is **detection versus delivery**. Detection is redundant
already: the Mac notices its own scheduler died, and zklw notices the Mac stopped
depositing facts, and neither needs the other to reach that conclusion. What is
genuinely single-pointed is *delivery* — every one of those findings reaches mk
only when a human opens a session. On the Mac that happens constantly. On zklw
the SessionStart reporter runs inside roughly eleven headless timer sessions a
day that **no human ever reads**, so zklw's warning about a silent Mac is
computed, written, and left sitting there.

### The decision: accepted single point of failure, because it is not single

Rejecting the two alternatives, with reasons rather than by default:

**Redundancy — already present, nothing to build.** The audit's own premise was
that zklw "could evaluate the Mac's freshness as easily as the Mac evaluates its
own". It already does, via `peer-agreement`, and the exit-3 path proves it. What
was actually missing was not a second observer but two durability defects in the
scheduler's own definition, both fixed 2026-07-29 and both invisible until
looked at: the plist was invalid XML that `plutil` accepts and `plistlib`
rejects, and its `rig-outcome` classification existed **only in the generated
copy**, so the next `install-macos.sh` run would have regenerated the live plist
without it and `rig-job-outcomes.py` would have called the scheduler
UNCLASSIFIED. A self-inflicted version of the same silence.

**Dead-man's switch — rejected.** It is the most-machinery answer, and it buys
delivery at the cost of crying wolf: a switch that fires when nothing is heard
fires every time a laptop is closed over a weekend. The failure it guards
against is already detected twice; adding a third detector that pages is
solving the wrong half. If out-of-band delivery is ever wanted, the honest
version is a push notification triggered by an existing finding, not a new
observer.

**Topology is not backwards.** zklw being canonical and always-on argues for it
being the *witness*, which it already is. It does not argue for moving the
aggregation there, because aggregation exists to be read and zklw has no human
reader. The Mac is the display precisely because that is where mk looks. The
current shape — always-on machine computes an independent verdict, laptop
aggregates and displays — is right, and the residual risk is bounded and
nameable:

> If the Mac is closed for a week **and** nobody opens a session on zklw, zklw's
> warning is written and unread. Nothing is lost; the first Mac session surfaces
> every stale check with its age. The cost of the outage is delay, not silence.

That is accepted, and it is written down here so that accepting it stays a
decision rather than an oversight.

### The check: relative, not a plain age threshold

"Fail if the instrument is older than N days" is wrong twice over. An idle
machine trips it for behaving correctly, and a busy machine that stopped
recording passes for N days — exactly the window that hid this.

So the check compares each instrument against **independent proof that sessions
ran at all**. ~~Claude Code rewrites `~/.claude.json` as it works.~~

**Corrected 2026-07-28 — that proof was not proof.** Claude Code rewrites
`~/.claude.json` and `settings.json` at session **start**, before the first tool
call and before authentication. Every zklw session since 2026-07-14 started,
refreshed both markers, and died at `authentication_failed`. So the check saw a
fresh marker beside a silent instrument and announced

```
sessions active 28m ago but audit-log recorded nothing in over 2.0d
```

— a definite verdict against a healthy instrument, every day for fourteen days.
The same defect family this program has been correcting all week, in a third
costume: not *stale vs cannot-check* this time but its neighbour, **did not
happen vs could not have happened**.

The authority is now the **session transcripts**, which record what a session
did rather than that it existed. A session that reached a tool call is proof that
recording was possible; one that died before it proves only that Claude Code
started. Three outcomes are counted separately — productive, blocked at
authentication, started-and-did-nothing — and only the first licenses a verdict.

Two consequences:

- **Exit 3 is now distinct from exit 1.** Exit 1 means an instrument that should
  have recorded did not; exit 3 means no session got far enough for the question
  to have an answer. Exit 3 reports as `warn`, and
  `test-rig-instrument-freshness.sh` fails if the two ever return the same code.
- **Instruments are judged only against their own trigger.** `audit.log` is
  written by a hook registered `Skill|Agent` on zklw and
  `Skill|Agent|Bash|Read|Edit|Write|NotebookEdit` on the Mac, so the same file
  means different things on the two machines. A week of Bash work legitimately
  leaves zklw's copy empty. The matcher is read from `settings.json`, never
  hardcoded, so re-scoping a hook re-scopes the check that judges it.

A stale marker still means the machine was idle, and the check still stays quiet.

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

Re-verified 2026-07-28 across nine cases, including the two the original set
could not express: sessions dying at authentication (exit 3, not 1), and a fresh
activity marker with no session transcript behind it — a watchdog or backup
touching `settings.json` is enough, and under the old logic that counted as proof
sessions ran. The collapse was then **forced** in an isolated copy by setting
`EXIT_NO_VERDICT = 1`; the suite failed with `both returned 1 -- the states have
collapsed`, which is the regression it exists to catch.

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
- **Restoring authentication on zklw** — `claude /login`, interactive, and the
  single unblock for the largest outage in this document. Until it is done, every
  `PreToolUse` and `PostToolUse` hook on that machine stays dead, autosync cannot
  commit, `audit.log` cannot record, and ~11 scheduled agent sessions a day
  continue to start, fail, and report success at the timer level (`mk-q6bl`).
- **Deciding whether `canongraph-recall.py` and `canongraph-run-bridge.py` go
  back on zklw.** Both were unregistered on the false premise that no session
  exists there to recall into or to end. Restoring them also means re-adopting
  the settings reference so `enablement-drift` does not report drift the next
  morning (`mk-7c70`).
- **Autosync on zklw.** The `autosync-repair` timer now commits the allowlisted
  cases and refuses the rest; `autosync-health` detects what remains. The
  hook-driven half returns on its own once authentication is restored — the timer
  stays regardless, because sessions have now demonstrably stopped once.
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

## The estate checks are on timers — cadence per check, not a uniform daily

Three checks written between 2026-07-26 and 07-28 ran only when a human
remembered to run them. That is the same shape as the guard outage this whole
document exists because of, so they are now scheduled. Units are tracked in
`dotfiles/server/.config/systemd/user/`; each `.timer` carries its cadence
argument inline.

| Check | Cadence | Why that cadence |
|---|---|---|
| `estate-lane-status` | daily | Lanes move per-edit, but the actionable condition is "frozen > 7 days", so the fact changes on a scale of days. Daily gives seven observations before the flag matters. |
| `estate-kimi-parity` | daily | Parity breaks on publish, a few times a week. Drift reached 21 of 62 manifests the last time nothing watched. |
| `estate-workflow-health` | weekly | Watches GitHub's 60-day auto-disable fuse. Weekly gives ~8 observations before it burns; daily would mean ~64 API calls against a fact that cannot change in a day. |
| `git-autosync-promote` | hourly | A green lane should not wait a day to reach main. Declared interval 2h so one skipped run does not read as stale. |

`rig-report.sh <name> <interval> <cmd...>` runs a check and records the verdict,
mapping the exit-code dialect all of these already speak:

| Exit | Meaning | Recorded as |
|---|---|---|
| 0 | ran, found nothing | `pass` |
| 1 | ran, found something | `fail` |
| **2** | **could not run** | `fail`, summarised `could not run — …` |

Exit 2 is the reason the wrapper exists. A check that cannot run must never look
like one that ran and was happy — that conflation is how a secret scanner GitHub
had switched off still showed 100 green runs.

### Expectations are host-scoped, and asserted from the peer side

`report-rig-health.py` treats a missing status file as a finding, because
deleting a scheduler must not delete its alarm. These four timers exist only on
zklw, so asserting them globally would print a permanent false alarm on the Mac —
hence `EXPECTED_BY_HOST`.

The assertion also runs on the **peer** path, which is where the visibility
actually is. zklw's own SessionStart reporter is not a channel to rely on: every
session there has died at `authentication_failed` before its first tool call since
2026-07-14. So the Mac asserts what zklw owes and reports `NEVER` for anything it
has not seen — a timer that was never installed cannot report its own absence.

### What the first unattended runs found

Each of the three found something real on its first firing, which is the argument
for having scheduled them:

- `estate-lane-status` — `apps/Khouri` frozen **109 days**.
- `estate-workflow-health` — 0 disabled, confirming the 17 re-enables held.
- `estate-kimi-parity` — **58 of 65 "out of parity", every one a false alarm.**

That last one mattered most. Parity is a property of what is in git, and zklw's
plugin repos had not pulled the `kimi.plugin.json` commits, so the file was absent
from that disk while present in the repo — the Mac reported 62 ok on the same
estate. 58 false alarms is worse than no check; it is the cry-wolf failure from
the other direction. A repo behind its remote is now `STALE` rather than `DRIFT`,
and when staleness dominates the check exits 2 rather than guessing. It now
reports `CANNOT ASSESS: 30 of 65 plugin(s) are behind their remotes`.

**Known limitation.** These timers read the checker scripts out of zklw's
monorepo working tree, so a blocked pull disables them. That is not theoretical:
`.beads/hooks/pre-commit` has been a typechange there since 2026-07-27, holding
the checkout 27 commits behind, and the two scripts had to be materialised with a
targeted `git checkout origin/main -- <paths>` to run at all. The surface reported
it correctly (`could not run — No such file or directory`), which is the system
working; the typechange still needs a human.
