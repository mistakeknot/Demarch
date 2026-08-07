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
| `publish-drift` — does the published artifact contain the committed source | launchd | systemd timer | daily 09:15 |
| `settings-history` — did the settings snapshot actually record | launchd | (watchdog) | daily 09:15 |
| `autosync-repair` — commit and push what the marker promised | — | **systemd timer** | daily 08:45 |
| settings.json history | SessionStart + daily | **continuous, 10s poll** | see below |

## Could not look is not nothing found

Every check here answers three questions, not two: is it right, is it wrong, and
**could I tell**. The third is a real answer and it has its own exit code — `3`,
the same one `rig-peer-agreement.py` reserved and for the same stated reason:
"I have no peer" and "my peer and I disagree" are opposite statements and must
not share a code.

The rule exists because the estate kept violating it. On 2026-08-01 a sweep of
every check found eight sites where a dependency failing produced a GREEN
verdict:

- `marketplace-divergence` decided by `grep -q 'clones disagree'` and never read
  ic's exit status, so a missing clone, an erroring ic, or a reworded message all
  reported "clones agree". Measured, not assumed: from `$HOME` — the vantage the
  check deliberately uses — `ic publish doctor` ends with "across 0 plugins" and
  exits 1, while the same command inside the tree says "across 62".
- `enablement-drift` decided by `grep -q 'DRIFT'`, and the guard prints ZERO
  BYTES on a clean run. So "no drift" and "the guard did not run" were
  byte-identical — and the guard returns 1 for exactly the could-not-look cases,
  the first of which is the four-month outage this whole page exists for.
- `rig-autosync-check.sh` counted an unreadable repo as clean, an uncomputable
  ahead-count as pushed, a failed `find` as "no autosync repos here", and dropped
  every autosync-marked WORKTREE out of the population (`.git` is a file there,
  not a directory).
- `report-rig-health.py` — the last mile — skipped any status file that would not
  parse, so a check could classify its own failure perfectly and still vanish.

Each now returns 0 / 1 / 3, and `rig-health-check.sh` maps 3 to `warn`.

**Deliberately still fail-open, with reasons**, so the list is a decision and not
an oversight:

- Hook-payload `jq -r … 2>/dev/null` parses across ~10 hooks. A hook that cannot
  parse its own stdin has nothing to say; exiting quietly is the correct answer,
  not a withheld one.
- `guard-tests`, `settings-reference`, `intercore-tests`, `ic-provenance` already
  read exit status directly, and a dependency failure there reaches `fail`.
- `settings-history` is not in `EXPECTED`: zklw runs a continuous watchdog
  instead of the scheduled snapshot, so a missing status file there is correct
  rather than a finding. Staleness detection still applies once a file exists.

**How to verify one**, and the only way that counts: break the dependency for
real and force a run under the actual scheduler. Reading the code is not proof.
`RIG_IC_BIN`, `RIG_INTERCORE_DIR`, `RIG_MARKETPLACE_CLONES`, `RIG_GUARD_HOOK`
and `RIG_AUTOSYNC_ROOT` exist so the failure paths can be staged without
vandalising the real estate; the suites in `dotfiles/common/.claude/hooks/tests/`
run the REAL scripts against those overrides, never a copy of the logic.

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
| `rig-job-finding.sh` | *what did it do to each of its targets?* |
| `rig-job-outcomes.py` | *did everything scheduled produce an outcome at all?* |

What **is** redundant is wrapping systemd and launchd jobs in receipts. Both
already store the result durably until the next run. **Where the outcome
survives, read it; where it evaporates, capture it.** Receipts are therefore
used for cron and nothing else — on this estate, three lines.

### An exit code is not evidence of work (2026-08-07)

The middle row above was added after the wrapper's premise turned out to be
incomplete. It was written on the strength of a measurement — `claude -p` is
honest, it exits 1 on an authentication failure — and the conclusion drawn was
that the exit code existed and cron merely threw it away. Both halves were true
and the inference was too narrow.

`tierA-review` started at 02:47, spawned a background subagent onto a 2191-line
diff across 16 files in `jawnbase`, hit the print-mode background-wait ceiling at
600s, was terminated mid-review, and **exited 0 in 673 seconds**. It filed
nothing. Its last words were *"I'll … wait for the background review agent to
finish."* Every layer of the surface read pass.

The night before, the same job hit a quota wall, exited 1, and every layer
correctly said so. **The estate was catching the honest failure and missing the
dishonest success** — the worse of the two, because a job that reports success
while doing nothing decays for exactly as long as nobody checks.

`rig-job-outcomes.py` had already named this in its own docstring: *"a job that
does nothing exits 0 and writes nothing, and both readings come back clean."*
The mechanism to prevent it existed. `tierA-review` was **exempt** from it,
declared `none` on the reasoning that a night with zero changed repos writes
nothing — which is right for `plan-burndown`, whose empty-queue path genuinely
leaves no trace, and wrong for a sweep over a *known list*: "no commits" is a
finding about a repo the job did look at. The exemption was granted by schedule
adjacency rather than by shape.

So the job now emits one declared row per target, and the receipt is
`findings <max-age-hours> <count|any>`:

```
# exactly one COVERAGE row per target — this is what the count counts
rig-job-finding.sh tierA-review covered     jawnbase "12 commits, 0 P0/P1"
rig-job-finding.sh tierA-review no-change   jawnfit  "last commit 2026-07-29"
rig-job-finding.sh tierA-review unreachable ravenous "not present on this host"

# then zero or more FINDINGS, which are news and are not coverage
rig-job-finding.sh tierA-review finding     jawnbase "P0: …" --ref jawnbase#mk-abc1
```

Three things follow from the vocabulary, and each closes a separate hole:

- **The count and the age live in one declaration.** A freshness bound alone is
  satisfied by a single row, so a sweep that reported on one repo of seven and
  died would read as fresh *and* complete. Two declarations could be half-written;
  one cannot. More targets than declared is a finding too — a count that no longer
  matches the job's list has stopped being able to detect the partial sweep it
  exists for. What is counted is **distinct subjects of coverage rows**, not rows:
  a repo with three defects filed against it is one repo looked at, and a defect
  filed about a repo that was never reviewed must not fill that repo's slot.
- **`unreachable` is not `no-change`.** A repo with nothing new and a repo nobody
  can see produce the same silence and mean opposite things. `autosigil` and
  `ravenous` are named in the AUTO-TIERA prompt, exist on Clavain, and do not
  exist on zklw where the sweep runs — reported for two months as *"directory not
  found (confirmed via filesystem search)"*, a machine-local answer to a
  fleet-wide question. `ravenous` had a live tmux session and active work. An
  undeclared unreachable target is a finding; a declared one is a note carrying
  its own end condition.
- **A `finding` never changes the exit code, and must name where it was filed.**
  The defect is news about some *other* repo; routing it through the failure
  ladder would make a working review read as a broken job. `--ref` is mandatory
  because the surface points at the durable record rather than becoming one — a
  health check that accumulated findings would be a permanently red line, which
  is the failure this whole program was written against.

Runs are grouped by an id `rig-job-receipt.sh` exports and the emitter records,
never by clock proximity: three rows from a killed run plus four from the next
one are two half-sweeps, and a time-window reader would report seven.

Found while auditing this, and unrelated to the new kind: `check_receipt` has
always returned `None` for a receipt it could not parse, and the caller ignored
it — so a **malformed** declaration fell through to `ok` and the job read as
passing. Now NO VERDICT, like a job that declares no receipt at all. Declared
unreadably is no better evidence of work than not declared.

### A log written by a redirect is not a receipt (2026-08-07)

The same day, two of the three cron automations were still exempt, and the
argument for one of them was careful and wrong on an interesting axis.

`interwatch-drift` was declared `file 200 <log>`, justified like this: it is a
`claude -p` run whose output is redirected to that log, and `claude -p` emits its
analysis whether or not it finds drift, so there is no completion path that
writes nothing — *the log is written by the work rather than by the wrapper*.

Every sentence of that is true, and the axis is wrong. The property that matters
is not **written by the work vs. by the wrapper**, it is **distinguishes
work-done from work-attempted**. A `>> log 2>&1` redirect fails that: the
process writes to it while dying exactly as readily as while succeeding.
Measured on the run that proved it — `tierA-review` started 02:47:01, ran 673s,
reviewed nothing, exited 0, and its log's mtime is **02:58:14**, the dead run's
end to the second. A `file` receipt would have read fresh, and passing.

`plan-burndown` was `none` on the reasoning that an empty plan queue leaves
nothing behind. The measurement under that was sound (its interspect row really
is absent on the empty-queue path, so *that* receipt would have failed a healthy
job) but the conclusion did not follow: "I looked, and there was nothing" is a
finding about a queue it did look at, which is the same sentence written one
paragraph away about `tierA-review`'s repos. Its own contract says *"Never
process a second bead"*, so the honest count is exactly **1** — not `any`.

`interwatch-drift` gets `any` instead, because it **discovers** its targets
(23 repos on the last scan). A count nobody can state in advance cannot be
checked against one, and inventing a number would be declaring a fact. That
leaves a real gap — `any` catches a run that emitted nothing, not a sweep that
covered 9 of 23 and died — and the gap is named in the config rather than
papered over, because closing it would mean letting the job declare its own
denominator, which is a job grading its own exam.

### A declaration must not judge the runs that predate it

Adding a receipt to a weekly job makes it red until that job next runs.
Declared on a Friday, `interwatch-drift` next fires on Monday: three days of a
red line whose only available action is *wait*. That is this whole program's
purpose inverted — a surface that cries wolf teaches its reader to scroll past
it, and the reader it teaches is the one who scrolls past a real failure next
month. The tempting alternative, leaving the receipt off until convenient, keeps
the hole open for exactly as long as closing it is inconvenient.

So a declaration can carry a start date, and until the job's next run it is a
**note**, not a verdict:

```
interwatch-drift findings 200 any
interwatch-drift receipt-from 2026-08-07 the first scan under this receipt is Monday 2026-08-10
```

What stops it being an off switch is that the grace period is not a number
anyone chooses: it is **the receipt's own max-age**, already declared one line
above for a different purpose. 200 hours after that date with still no
qualifying run, the declaration has outlived the freshness it demands of its own
job and is reported as a failure. A post-dated receipt buys exactly one window,
and buying a second means widening the bound the check then holds you to.

A start date with no stated reason, or one that cannot be read as a date, is
refused rather than honoured — if a malformed exemption cost nothing, the way to
silence a check would be to misspell its date.

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

## Backups: proven restorable, and the one that was not running at all

Everything above asks whether a job RAN. This asks whether its output is worth
anything. The answer, on 2026-07-29, was mostly yes and once catastrophically no.

### The one that was not running

Clavain's Synology backup logged `Synology not mounted, skipping` and exited **0**
— 22,063 times between 2026-03-26 and 2026-07-29. launchd recorded success;
`rig-job-outcomes.py` read the exit code, found the unit classified `verified`,
and passed it (**mk-7vej**).

No care with exit codes could have caught this. **The job did not fail.** It
correctly declined to run and correctly said so. The false claim was never made
by anyone: that a backup existed. That is why `rig-backup-freshness.py` reads the
repository rather than the process — `restic snapshots` is a receipt the backup
itself wrote and dated, and it outlives the run that made it.

An earlier note in this program said the Synology copy kept succeeding while B2
was locked. That was wrong, and it was inferred from exit 0.

> **Corrected 2026-07-29 (same day, later).** The paragraph above used to say the
> backup "last completed 2026-03-30", that it had been absent "for a third of a
> year", and that one of two faults was a `wrong password or no key found`
> credential problem. **All three were wrong**, and the way they were wrong is
> worse than the facts they got wrong.
>
> The repository holds **361 snapshots ending 2026-07-08** — three weeks stale,
> not four months. `restic check` passes on all 361. The 2026-03-30 date is the
> last *success line in the log*, and it stops there because the script ran under
> `set -e`: on 2026-04-15 and 2026-07-08 `restic backup` wrote its snapshot, the
> following `restic forget` hit a stale lock, and the script died before printing
> its completion line. **A successful backup was recorded as a failure, and then
> the absence of the success line was read as an absence of backups.**
>
> And `wrong password or no key found` was never a credential problem. The log
> shows what actually happened, two lines earlier:
>
> ```
> List(key) returned error, retrying after 670ms: fdopendir …/keys: operation timed out
> List(key) returned error, retrying after 2.08s:  fdopendir …/keys: operation timed out
> List(key) operation successful after 2 retries
> Fatal: wrong password or no key found
> ```
>
> The SMB mount stalled listing `keys/`, restic retried, the retry "succeeded"
> with an empty listing, and restic then truthfully reported finding no key. The
> repository opens on the first try with the configured password. **restic reports
> a stalled network filesystem as a credential error**, and that message sent this
> program to file a key-reconciliation task against a repository whose key was
> never in question.
>
> The through-line is uncomfortable and exact: this section exists to argue that
> only the repository can answer "does a backup exist", and it was written from
> the log.

### The four faults, established by forcing each one

There was never one fault, or two. Diagnosing it properly on 2026-07-29 found
four, each with a measured cost:

| # | fault | cost | why it was invisible |
|---|---|---|---|
| 1 | **Nothing mounted the share.** The mount only ever existed because a human had connected in Finder. `/Volumes` is root-owned, so a user LaunchAgent *cannot* create `/Volumes/Jarmusch`; `/etc/auto_smb` exists but `/etc/auto_master` never references it, so autofs was never involved. | 22,063 skipped runs | exit 0 every time |
| 2 | **`[ -d /Volumes/Jarmusch ]` tests a directory, not a mount.** A leftover empty mountpoint passed the guard. | 2,987 failures on 2026-04-17 alone | the guard reported "mounted" |
| 3 | **Two stale restic locks.** The lock named PID 8942 on this same host; after a reboot that PID was reused by a live process, so restic could not judge the lock stale and refused to proceed. | 262 failed runs, 2026-04-03 → 2026-07-08 | `restic forget` failing, under `set -e`, looked like the whole job failing |
| 4 | **`set -e` converted a good backup into a reported failure.** See the correction above. | the entire false diagnosis | the log stopped saying "complete" |

Faults 1, 2 and 4 were each found by **forcing a run under launchd** rather than
reasoning about the script, and forcing it turned up two more problems that no
amount of reading would have:

- **`/usr/local/bin/python3` is a dangling symlink** to a Python 3.11 framework
  removed in 2023. It precedes `/usr/bin` on the job's `PATH`, so anything under
  this agent calling `python3` silently produced nothing. The first rewrite of
  the mount helper used `python3` to URL-encode the password and failed on
  exactly this. It now percent-encodes in bash, with `LC_ALL=C` so the loop
  iterates bytes.
- **`mount_smbfs` lives in `/sbin`**, which the plist's
  `PATH=/usr/local/bin:/usr/bin:/bin` omits entirely — so the mount would have
  failed next even with a working `python3`.
- Incidentally, `/usr/local/bin/restic` is **0.18.1 built for darwin/amd64** and
  has been running under Rosetta; `/opt/homebrew/bin` has 0.19.0 arm64. Both
  support `--retry-lock`, so this cost speed rather than correctness.

The mount now belongs to the backup script: it mounts `//mistakenot@jarmusch/Jarmusch`
at `~/mnt/jarmusch` (under `$HOME`, where an unprivileged agent may create a
mountpoint), reading the password from the login keychain at runtime so no new
secret goes to disk. **Verified working from launchd**, not from a shell — the
agent mounted the share itself with no GUI session involved.

An on-demand mount was chosen over wiring up autofs. autofs needs root, would
keep the password in a root-readable plaintext map, and fails by presenting a
silently empty directory — which is the exact quiet failure this whole section
exists to end. The script's mount can fail loudly, and does: it exits **1** when
`jarmusch:445` answers but the mount does not.

### Restores actually performed, 2026-07-29

Not "the backup completed". Restored, then opened.

| repository | restored | verified how |
|---|---|---|
| `rclone:b2:sma-mac-backup` (85 snapshots, from 2026-03-26) | `install-macos.sh` from snapshot `21b7153a` | sha256 identical to live; `bash -n` parses |
| `b2:jawnverse-pgbackups` tag `jawnverse-pg` | 18 dumps, 26.8 MiB, snapshot `847d1687` | `pg_restore --list` → 63 TOC entries, `dbname: jawnbase`, format CUSTOM |
| `b2:jawnverse-pgbackups` tag `canongraph` | `log.sqlite`, `topology.yaml`, `profile.json` | `PRAGMA integrity_check` → ok; 765 event_log rows, 316 entities, 335 relationships, 40 documents; YAML and JSON parse |
| `b2:ethics-gradient-backup/mac` (rclone mirror) | one session `.jsonl` | bytes identical; valid JSONL |
| `~/mnt/jarmusch/Backups/mac-restic` (361 snapshots, 2026-03-26 → 2026-07-08) | 22.9 MiB Olympus RAW `P5270011.ORF` + a shell script, snapshot `f6a8b7bc` | sha256 identical to live and `cmp` clean on both; `sips` decodes the RAW at 5184×3888 and renders a JPEG; `restic check` clean on all 361 snapshots |

**The restore constraint nobody had written down:** the Postgres dumps are
`--format=custom` written by **PG17** tooling inside the `jawnverse-postgres`
container. zklw's host `pg_restore` is 16.14 and rejects them outright with
`unsupported version (1.16) in file header`. They are not corrupt — they load
correctly *with PG17*. But restoring onto a fresh machine with a distro Postgres
will fail, and that dependency existed only in the container image and a unit
comment.

It is now written down where someone restoring onto a bare machine would actually
look: **[`ops/backup-restore-runbook.md`](backup-restore-runbook.md)**, which
carries the verified procedure for every destination here, both misleading error
messages (`wrong password or no key found`, `unsupported version (1.16)`) with
their real causes, and the key-escrow warning at the top where it cannot be
missed.

### Two defects the fix itself introduced

Both were found by watching the repaired job run rather than declaring it fixed,
and both would have been invisible to the test suite.

**Adding paths to an invocation orphans restic's parent snapshot.** restic selects
a parent by matching host + *path set*, and with a parent it skips every file whose
inode/size/mtime are unchanged — which is how the 2026-07-08 run reported 308,536
files unmodified without reading them. Appending `~/.config/restic` and `~/scripts`
to the existing invocation meant no snapshot matched, so restic silently fell back
to reading and chunking all 203 GB: **52 minutes to cover a third of `~/projects`,
0% CPU, blocked in uninterruptible I/O, holding the repository lock throughout.** A
five-minute timer cannot own a run that takes hours and restarts from nothing on
every laptop sleep. The same edit was in the B2 script, where the next 4-hourly run
would have done that re-read across the internet.

Fixed by splitting each destination into two invocations — the large tree keeps its
three original paths and its parent chain, the config tree gets its own. **The tags
matter as much as the split:** two snapshots in one repository means an untagged
freshness entry would let a two-second config snapshot answer "fresh" for a 203 GB
backup that had stopped. That is exactly the masking the tag field was added to
prevent for zklw, and the fix for the original bug would have reintroduced it.

**The freshness check aged every snapshot by the machine's UTC offset.** restic
stamps snapshots in local time *with* an offset (`2026-07-30T11:00:06.416999-07:00`);
the check took `[:19]` and declared the result UTC. Zero error on a UTC server,
seven hours on Clavain — invisibly correct wherever it was most likely to be
tested. At cadence 24h the 72h limit absorbed it, but at `mac-b2`'s cadence 4h the
limit is 12h, so **a backup taken six hours ago computed as thirteen: a false STALE
alarm on the one backup of this machine that has never stopped.** Teaching a reader
that the report cries wolf is worse than not having the check.

The suite could not have caught it — the fake `restic` emitted naive UTC, so every
test agreed with the bug. The fake now emits offset-bearing stamps, and two
regression tests pin the offset explicitly so they fail on any machine rather than
only in a zone that exposes it. Both directions are tested because they fail
differently: west of UTC manufactures staleness and is merely loud, east of UTC
hides staleness and is silent. Verified by reintroducing the old parser — both fail,
and only those two.

### Retention: believed versus measured

| repository | policy says | actually holds |
|---|---|---|
| Clavain → B2 | hourly 24, daily 7, weekly 4, monthly 6 | 85 snapshots, 2026-03-26 → today ✓ |
| Clavain → Synology | same, every 5 min | **361 snapshots, 2026-03-26 → 2026-07-08**; `restic check` clean on all 361 |
| zklw → B2 (both tags) | daily 7, weekly 4, **no monthly tier at all** | 9 snapshots/tag — `jawnverse-pg` **17.3d**, `canongraph` **15.1d** |
| Clavain → B2 rclone mirror | *believed*: none, `rclone sync` keeps no history | **30 days**, from a B2 lifecycle rule (`daysFromHidingToDeleting: 30`); 250 of 438 listed entries are old versions |

Two surprises in opposite directions, and one correction to how the first was
originally described.

**zklw's window was recorded as "17 days, not the ~28 the policy implies".** The
policy framing was wrong: `--keep-daily 7 --keep-weekly 4` has a ceiling of about
five weeks, and 7 dailies + 2 weeklies = the 9 snapshots actually present, so the
policy was doing exactly what it said. The real defect was the one the arithmetic
hid — **there was no monthly tier on either unit**, so maximum recoverable depth
was capped at roughly five weeks no matter how long the repo lived. A corruption
noticed six weeks later was unrecoverable by design, and nothing said so.

Fixed 2026-07-29: `--keep-monthly 12` added to both `jawnverse-pg-backup.sh` and
`canongraph-backup.sh`. The cost is negligible and was measured rather than
assumed — the entire repository is **34.4 MiB** stored (41.3 MiB uncompressed,
1.20× ratio), so twelve monthlies of deduplicating ~10 MiB dumps cost single-digit
megabytes. **Clavain deliberately stays at `--keep-monthly 6`**: its repositories
hold 203 GB including the RAW photo library, where each retained monthly is
genuinely expensive. Retention depth is priced per repository rather than set once
and copied.

**The rclone mirror** — which looks like a pure mirror with no history — has a
month of version history that no script referenced or asserted. Delete that
lifecycle rule and the safety net vanishes silently, with nothing local changing.
That is now a `lifecycle` line in `backup-repos.conf` and
`rig-backup-freshness.py` reads the rule from the bucket on every run: a window
that shrinks below the 30 days the config depends on is a **finding**, and a rule
it cannot read is a **no-verdict**, never a pass. Depending on it deliberately was
chosen over migrating the mirror to restic — it carries agent transcripts, which
are valuable but reconstructible, and a 30-day undelete window fits data whose
real risk is an accidental local deletion noticed within the month. Asserting an
assumption costs one API call; migrating it costs a rewrite.

The `jawnverse-pg` history is also missing **2026-07-28**: the 48-hour orphaned
restic lock is visible as a hole in the backup record.

### The gap that no freshness check can see: the key has one copy

Auditing the backup set turned up something worse than a missing second location,
because a second location would not have helped.

`restic` covers `~/projects`, `~/Downloads` and `~/Pictures/Photo Archive`. The
rclone mirror covers `~/.claude/projects` and `~/.codex`. **Nothing covered
`~/.config/restic`** — which is where the three backup scripts, both env files,
and `PASSWORD.txt` live. It is in no backup set and no git repository.

A search of that directory, `~/scripts` and the dotfiles repo found **exactly
three copies of the restic repository password**, all three inside
`~/.config/restic`, on the machine being backed up. 1Password holds the *SMB*
credential (as `Synology NAS`, confirmed by hash against the keychain item) but
**no item contains the repository password**.

So: if Clavain's SSD fails, both restic repositories — 203 GB including the photo
library — become permanently undecryptable ciphertext. Both copies survive. The
off-site copy survives. Neither can ever be opened again. **This is a 3-2-1
strategy defeated at the key rather than at the copy.**

`~/.config/restic` and `~/scripts` were added to both repositories, and the
scripts are now tracked in dotfiles, which fixes the availability of the
*scripts*. It does **not** fix the key, and cannot: storing the password inside
the repositories it decrypts is circular. Escrowing it off the machine needs an
out-of-band store, so it is item 1 on the manual list below rather than something
this session could close.

### Decision: restore verification is a dated drill, not a nightly job

Argued, because the goal that prompted this warned against defaulting to more
machinery — and a nightly restore test nobody reads would be this program's
defect in its purest form.

Split the question by what actually changes:

- **Does a recent backup exist?** Changes constantly, and is cheap to ask.
  `rig-backup-freshness.py` asks it **daily**, per repository and per tag.
- **Is a backup restorable?** Changes rarely, and is expensive to ask — egress,
  disk, and a container round trip. Nightly would spend real money to re-answer
  a question whose answer only moves when the tooling does.

So restore verification is **dated, and re-run on triggers** rather than on a
clock. The triggers are the things that can invalidate it:

1. a Postgres major version change on either the container or the host
2. a restic major version change (Clavain is on 0.19.0, zklw on 0.16.4 — they
   already differ, which is itself worth watching)
3. a new repository, or a change of storage backend or credentials
4. any restore that fails, which resets the clock for that repository

"Dated" only differs from "forgotten" if the date is written down, so it is: the
table above carries what was proven, where, and when. Re-drill when a trigger
fires, or annually, whichever comes first.

### Stale locks: `--retry-lock` for contention, detection for orphans

Full reasoning is written into `canongraph-backup.service` and
`jawnverse-pg-backup.service`, beside the units. In short: `--retry-lock 15m` was
adopted (both units write one repository ~28 minutes apart, so contention is
real), auto-unlock was **rejected** because its safety rests on a single-writer
assumption that nothing enforces and being wrong damages the repository, and
orphans are handled by detection now that `backup-freshness` escalates them
within three days. That last part is only defensible *because* the problem is now
visible; detection-only would have been the wrong answer a week ago.

## What is still manual

- **Escrowing the restic repository password off Clavain.** The highest-severity
  item in this document. Three copies exist, all in `~/.config/restic` on the
  machine being backed up, and no 1Password item holds it (verified by hash
  2026-07-29 — the *SMB* credential is there, the repository password is not). If
  that SSD fails, 203 GB across both repositories survives as ciphertext nobody
  can open. Adding the directory to the backups does **not** fix this; storing the
  key inside the repositories it decrypts is circular. Fixing it means writing
  into a credential store, which is mk's to do:
  `op document create ~/.config/restic/PASSWORD.txt --title "restic repository password (Clavain)" --vault Private`
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

**Known limitation, resolved 2026-07-29.** These timers used to read their
checker scripts out of zklw's monorepo working tree, so a blocked pull disabled
them. That was not theoretical: `.beads/hooks/pre-commit` was a typechange there
from 2026-07-27, holding the checkout 30 commits behind, and both scripts had to
be materialised with a targeted `git checkout origin/main -- <paths>` to run at
all. The surface reported it correctly (`could not run — No such file or
directory`), which is the system working, but a check that correctly reports
being unable to run is still not checking anything.

The fix is `estate-check.sh`, which resolves the checker from a bare mirror of
`origin/main`, fetched every run. `--estate` still points at the real checkout,
because inspecting what is on disk is the check's job; only the script's own
provenance moved.

**The generalisation is worth more than the fix.** The defect was distributing a
monitor through the channel it is meant to watch. A monitor that goes dark for
the same reason its subject goes dark is not a monitor. The blockage was also
self-sustaining: the dirty entry blocked the pull that would deliver the commit
that removed the reason for the dirty entry. The fix — `9485e7e0`, which inverted
the shared hook from *symlinked over the tracked file* to *called by it* — had
been sitting on `main` since 2026-07-27, unable to reach the one machine that
needed it, because of the thing it fixed.

Demonstrated against a tree deliberately built at `8ac44c62`, the commit zklw was
stuck on, where neither checker exists:

| Form | Result |
|---|---|
| `python3 <stale-tree>/scripts/check-workflow-health.py` | exit 2 — could not run |
| `estate-check.sh Sylveste scripts/check-workflow-health.py` | exit 1 — ran, `66 repo(s) inspected: 0 disabled, 1 never ran` |

**Tracked is not deployed.** Cleaning this up exposed a second layer. The timer
units and their helper scripts were tracked in dotfiles, which is what the
previous goal claimed — but on zklw `~/.config/systemd/user/estate-*` and most of
`~/.local/bin/rig-*` were **hand-made copies**, not symlinks into the checkout.
A copy does not go stale so much as never update at all, which is strictly worse
than a stale pull, and it is invisible: the repo looks authoritative and the
machine ignores it. Every entry whose content was byte-identical to its dotfiles
twin is now a symlink, so a dotfiles pull is the single deployment path. Two
exceptions were flagged here and both were closed the same day — see **The
deployment contract** below, which generalises the finding into a check.

**Parity now returns a real verdict, and it disagrees with the Mac.** With the 25
behind-remote plugin checkouts pulled current, `estate-kimi-parity` exits 1 with
`9 of 65 plugin(s) out of parity` — a finding, not `CANNOT ASSESS`, and not the
58 false alarms staleness was producing. The Mac reports `parity ok: 62`.

Both are accurate. Seven of the nine drifting plugins — `interboxd`,
`interbrowse`, `intercept`, `interdeploy`, `interscout`, `interstate`, `lattice` —
**do not exist on the Mac**, and two more (`interseed`, `intersite`) are not
enumerated by its discovery. The machines were scanning different sets, so the
numbers were never in conflict.

This inverts the previous goal's reading, which treated the Mac as the
trustworthy side. With staleness removed, **zklw is the better basis for this
check because it holds more of the estate**. Agreeing with the other machine is
not the same as being correct: two checks over different input sets can both be
right and still disagree, and the one reporting fewer problems is the one to
distrust first.

## The deployment contract, 2026-07-29

"Tracked in dotfiles" and "deployed on this machine" are different properties.
Three goals in a row verified the first and assumed the second, and each time the
assumption was false somewhere. The generalisation is now a check:
`dotfiles/common/.local/bin/rig-dotfiles-deployed.py`, wired in as Check 12 of
`rig-health-check.sh`, so it runs on both machines with no timer of its own.

**Root cause, not symptom.** `install-server.sh` declared **21** paths and *none*
of `common/.local/bin` or the `estate-*` units. Nothing ever linked them, so a
hand-made copy was the only way they could exist — the previous goal's fix was
correct and the next reprovision would have silently discarded it. Declarations
now stand at 57 on the server and 61 on the Mac.

`link()` prints `skip: (not in dotfiles)` and **returns 0**, so a declaration
naming a path that is not in the repo is a silent no-deploy. That is how
`~/.codex/AGENTS.md` — 17KB that both `CLAUDE.md` files call canonical — sat
untracked from the `common/macos/server` reorg (`3a1769e`) until today, outside
restic's `~/projects`-and-`~/Downloads` scope, one `rm` from gone.

### Four legitimate modes, because demanding symlinks everywhere is wrong

| Mode | Where | Why not a symlink |
|---|---|---|
| `symlink` | the default | — |
| `generated` | `Library/LaunchAgents/*.plist` | launchd expands neither `~` nor env vars in `ProgramArguments`; the installer sed-substitutes `$HOME`, so the deployed file *must* differ from the template |
| `copy-sync` | `~/.claude/settings.json` | the app rewrites it with write-temp-then-rename, and rename *replaces* a symlink (observed 2026-07-26) |
| `resolved-from-checkout` | `rig-health-check.sh`'s ten helpers | it tries `~/projects/dotfiles/...` before `~/.local/bin/...`, so those helpers need no `$HOME` copy at all |

That last one is why "must exist under `$HOME`" is a property of the **consumer**,
not the file. A systemd unit invokes an absolute path and has no fallback; a
shell script can try two. The check derives the required set by scanning tracked
units for `%h/.local/bin/<name>` references rather than assuming.

### Most of the work was in *not* reporting things

The first run produced 74 findings; 47 were noise — the other machine's package,
the generated plists, hook unit tests, and above all the checkout-resolved
helpers. Suppressing those was worth more than finding the 27, for the reason
this document keeps rediscovering: the 58-false-alarm parity run and
`Sylveste-84by`'s three phantom rebases were both ignored, not fixed.

| | before | after |
|---|---|---|
| Clavain | 15 findings | **0** — `pass` |
| zklw | 42 findings | **4** — `warn` |

### Cadence, argued

It rides the existing daily `rig-health` pass rather than taking its own timer,
because a separate timer would give the check its own independent way to go dark
— exactly how the `estate-*` units failed. Daily rather than weekly because the
drift-introducing event is a *new path* appearing, and new paths landed on **17 of
the last 90 days (19%, 106 files)** in bursts of consecutive days; a weekly
interval would present a picture up to seven days stale during precisely the
bursts when drift is created.

### The exit mapping is inverted on purpose

| Exit | Recorded as | Why |
|---|---|---|
| 0 | `pass` | — |
| 1 | `warn` | deployment drift is latent and actionable, not an outage; it has usually been true for weeks |
| 2 | `fail` | **an inability to assess is worse than a finding here**, because being unable to see deployment state is the condition under which this defect class survived three goals |

Silence is the failure mode, so silence gets the loudest status. Verified all
three ways: `pass` on Clavain, `warn` with 4 findings on zklw, and `fail —
deployment check not found` against an isolated `HOME`.

### Ownership is not inferable from location

A reverse-direction scan looks for live files that no repo tracks — the
`estate-drift` class, which was enabled, running weekly, filing beads, with its
script in `~/bin`, a directory that is not even a git checkout. That is now
tracked, and its `ExecStart` moved to `%h/.local/bin` so it sits somewhere the
installer manages.

The scan is **informational, never a finding**, because the first version walked
`~/.local/bin` and `~/bin` too and reported **151** paths on zklw. Every
`pip --user` console script has a shebang, and ~50 systemd units belong to the
project repos that deploy them. A project's binary installed into `~/.local/bin`
is indistinguishable from a home-level ops script, so the list is surfaced for a
human to read and never allowed to turn the check red over `ollama.service`.

### What remains, deliberately

> **Superseded on 2026-07-31** — see *Config or app state* and *The zklw half* below.
> All four zklw findings named here are resolved: zklw went from 14 findings to 0
> after `install-server.sh` ran to completion. `.codex/skills` is excluded outright.

Four paths on zklw stay unresolved and are the reason it reports `warn`:
`~/.codex/skills`, `~/.codex/superpowers`, `~/projects/docs`, and
`~/.codex/AGENTS.md`. The first three are **app-managed runtime state**, and the
two machines show opposite halves of one mistake — zklw's are divergent copies
(50 live files vs 8 tracked for `skills`), while the Mac's symlink works and lets
Codex write *through* it into the checkout, leaving the repo permanently dirty
with generated `imagegen`, `plugin-creator` and `review-agent` trees. That belongs
in the `copy-sync` category or excluded outright, not symlinked (`Sylveste-xv9s`).
`AGENTS.md` differs between the machines and needs a content merge before either
copy is replaced (`Sylveste-hddm`).

## Config or app state: the ownership rule, 2026-07-30

The previous goal established that *tracked* and *deployed* are different
properties. This one found the question underneath it, which the deployment
check never asked: **should this path be tracked at all?**

A symlink is a two-way street. Checking that config flows repo → machine says
nothing about app state flowing machine → repo through the same link. `xv9s`
recorded that as untidiness — "leaves the repo permanently dirty with generated
content". It was worse than that. Codex had *deleted two tracked files* through
the link and re-added them under new names, and nothing commits or reverts the
dotfiles checkout on the Mac, so the deletions sat there waiting for the next
person who runs a broad `git add -A` to commit an app's decisions as authored
work.

**The rule: if an app writes a path, dotfiles may not symlink it.** The test is
not what the file contains or where it lives, but who writes it — and the
evidence is usually a timestamp. After a Codex rebuild all 54 files under
`~/.codex/skills/.system` carry one identical mtime. One rebuild ran *during*
this session's measurement: a tracked `LICENSE.txt` vanished and returned inside
three minutes, which briefly made a present file look like an orphan and sent
one classification pass down the wrong path.

"Excluded" then has to mean the app stops writing into the checkout, not that git
stops mentioning it. A `.gitignore` entry would have left Codex rebuilding a
tree inside a shared repo where a `git add -f` or a tooling change reintroduces
it. `~/.codex/skills` is a real directory now and the declaration is gone.

### Two mechanisms, and a tree that was partitioned rather than duplicated

The repo carried **two deployment mechanisms at once**. `848b445` (2026-03-28)
renamed `common/X → X` for yadm, whose repo at `~/.local/share/yadm/repo.git`
had `core.worktree = $HOME`. `4b15241` a month later brought `common/` back —
but only **21 of 405 paths**. The symlink mechanism then won in practice: 70
commits touched `common/` against 7 touching root.

The first framing — "389 stale duplicates, recoverable from history" — was
wrong, and it was wrong in the direction that would have destroyed something.
Path-level dedup said 384 files were unique; only comparing the *shapes* of the
two trees showed why. superpowers' payload half (35 skills, hooks, commands,
lib) lives in `common/` and deploys; its `LICENSE`, 42 tests and 7 docs stayed
at root and do not. **Zero shared paths.** They are not two versions of one
thing, they are one thing cut in half. Retiring the root half would have left
vendored third-party code deployed with neither a license nor a test suite.

The correction generalises into a rule for deleting from a config repo: **an
orphan that is live in `$HOME` gets preserved, never deleted.** Ten of the files
in the retirement list were live regular files with no `common/` twin, including
every reference doc `~/.claude/CLAUDE.md` names by title. Tracked only in the
tree being retired, they were deployed by nothing and — being outside restic's
`~/projects` + `~/Downloads` scope — backed up by nothing either. Deleting them
would have reproduced exactly the defect the previous goal had just fixed for
`.codex/AGENTS.md`. They were preserved into `common/` and declared, because
tracking without a declaration is what made the tree invisible in the first
place.

The stale yadm repo was moved to `~/.dotfiles-backup-yadm-20260730` rather than
deleted. Nothing automated invoked it — no launchd job, no cron entry, no shell
alias — so it was latent rather than urgent. But a worktree pointed at `$HOME`,
four months behind, with an empty index, is not a thing to leave loaded.

### The legacy tree was not inert: it was competing for authority

`.claude/CLAUDE.md` at the repo root is loaded as **project instructions** for
the dotfiles repo. Both it and the current `common/.claude/CLAUDE.md` arrived in
one session's context — 81 lines each, **zero shared non-empty lines**. Two
generations of the same document, both claiming to be the global rules. Likewise
two tracked `settings.json` (12,791 B from May, 22,902 B from July), and a
`host.md##h.sleeper-service` alternate for a machine decommissioned on
2026-04-29.

### Three more places the check was silent

Each is the vacuity failure at a finer grain than the run-level guard was built
for. That guard asked *"is the inventory empty?"* It could not ask *"did entries
fall out of a non-empty one?"*

1. **`home_target()` returned `None` and the loop moved on.** Anything outside
   `common/macos/server/bin` was dropped — **426 of 636 tracked files, 67%** —
   contributing nothing and raising nothing. The 389-file legacy tree sat inside
   that hole for four months. `None` now means two different things and only one
   may be silent: *the other machine's package* is a correct skip; *no rule can
   ever map this into `$HOME`* is a path tracked in the permanent belief that it
   is deployed, and is a finding unless `UNMANAGED` names a reason.
2. **`HOME_FIRST_OK` matched only dotted names and `Library`.** So
   `common/projects/*` — declared in both installers and live as symlinks the
   whole time — had never been deployment-checked at all. Nine paths, invisible
   because the mapping quietly refused them. This one surfaced *because* making
   case 1 loud turned it into visible false positives.
3. **The check stat'ed the link, never the directory behind it.**
   `common/.codex/skills` passed every run while holding 46 untracked files and
   two tracked deletions. `LINKED-DIR-WRITTEN` now reports untracked or deleted
   content inside a declared directory link — the one question a resolving
   symlink cannot answer.

Blind spot 2 then taught a second lesson about how it was fixed. Adding
`projects` to the allowed list fixed that case and left the bug: within the hour
a sibling committed `macos/scripts/backup-to-b2.sh` — declared at
`install-macos.sh:161`, live as a symlink at `~/scripts/`, invoked by a
LaunchAgent — and the check called it undeployable, because `scripts` was not on
the list either. A list of blessed directory names is the wrong shape. The
installers already state which `$HOME` directories they target in every
declaration they parse, so the set is now read from them. The useful part is the
timing: that rule would have cost a false finding every time a new `$HOME`
directory was adopted, and cry-wolf is the failure mode this whole surface exists
to prevent.

Clavain went from 15 findings at the start of the previous goal, to 0, to **20
once the silent skips became loud**, to 0 again once each was either given a
reason or fixed. The middle number is the honest one: it is what the machine had
been carrying all along.

### `1oci`: when comparing the machines is the wrong question

`ARCHITECTURE.json` and `docs/diagrams/ecosystem.html` are tracked and generated
by scanning the local checkout, and the two machines see genuinely different
estates — 62 vs 65 plugins, 81 vs 131 commands, 249 vs 253 nodes. Each
overwrites the other forever and **neither is wrong**. No drift check, freshness
check, or machine-to-machine comparison can resolve that, because there is no
missing input to find: the inputs differ legitimately.

So `rig-generated-inputs.py` asks the only locally answerable question — *did
this run see every input the artefact was built from?* A manifest records the
expected input set; a run seeing fewer is `INCOMPLETE` and must not overwrite,
and a run seeing more means the manifest is stale and should be refreshed
deliberately. "The machines differ" becomes "this run was detectably
incomplete".

The manifest was seeded from Clavain's 61 plugins, which has a consequence worth
stating plainly: once zklw refreshes it from the larger estate, **Clavain will
correctly report `INCOMPLETE`** and should stop regenerating those two files.
That is the mechanism working, not a regression.

### What remains

- **zklw was unreachable all day.** Tailscale SSH demanded interactive
  re-authentication, so the zklw column of the inventory, `hddm`'s `AGENTS.md`
  content merge, the zklw firing, and the manifest refresh from the canonical
  estate are all outstanding. Nothing was guessed in its absence.
- **`.codex/superpowers` (58 files) was deliberately kept.** It holds the
  license and tests for code deployed from `common/`. Whether dotfiles should
  vendor it at all versus pin an upstream ref is a separate question.
- **`.claude/CLAUDE.md` is the last file of the retired tree.** A sibling session
  held uncommitted edits in it and interlock's daemon was down, so it could not
  be reserved against and was carved out rather than clobbered.
- **`.clavain/` state stays tracked**, including a 260 KB SQLite database whose
  `-shm`/`-wal` sidecars are untracked and unignored. That was a deliberate call:
  the A:L3 streak is meant to accumulate across both hosts, and git is currently
  how it travels. It is also the most likely first casualty of lane-based
  two-machine sync.

## The zklw half, 2026-07-31

zklw's baseline before anything changed: **14 findings across 3 classes**, 67
declarations, 54 deployed. After running `install-server.sh` to completion:
**0 findings, 67 of 67 deployed as declared.**

The eight `COPY` findings split cleanly once their content was actually
compared, which is the step that decides whether converting a copy to a symlink
is lossless:

| path | verdict |
|---|---|
| 4 × `.claude/*.md` reference docs, `.codex/infrastructure.md` | **byte-identical** — lossless |
| `projects/docs` | live entirely stale — repo newer on every file |
| `.codex/superpowers` | **0 files in common** — see below |
| `.codex/AGENTS.md` | genuine merge (`Sylveste-hddm`) |

Five of eight needed no decision at all. Both machines had hand-copied the *same*
content into `$HOME` and tracked it nowhere an installer could see — the defect
was never that the copies disagreed, it was that nothing deployed them.

`projects/docs` looked like it held unique content: one file, `ethics-gradient.md`,
existed only on zklw. It turned out to be the superseded predecessor of `zklw.md` —
same 455 lines, identical heading sets, 19 bytes apart from the machine-rename
substitutions. `keybindings.md` differed only because zklw's copy still said
`ethics-gradient` where the repo says `zklw`. Nothing was lost.

### zklw had the wrong half of superpowers deployed

`~/.codex/superpowers` on zklw contained `agents/`, `docs/`, `LICENSE`,
`README.md`, `RELEASE-NOTES.md`, `tests/` — and **no `skills/`, `commands/`,
`hooks/`, or `.claude-plugin/`**. Zero files in common with the repo's payload.
It was the *scaffolding* half: the same partition found on the Mac a day
earlier, except here it was the half that got deployed. superpowers had
therefore been non-functional on zklw for as long as that copy existed. The
installer run replaced it with the payload; 14 skills are present now.

This is the sharpest argument yet for checking deployment rather than tracking.
Nothing was missing, nothing was stale, no check was red — the directory existed,
was populated, and had plausible contents. Only comparing it against what the
installer *claims* to deploy showed that the machine had the wrong thing.

### The installers had been aborting before their last step for five months

Running `install-server.sh` to completion — required in order to deploy the
files preserved the day before — exposed `$DOTFILES/common/bin/fix-claude-paths.sh`,
a path that has never existed in this repo. Wrong in **both** installers since
2026-02-28.

The 2026-06-09 fix noted in `install-macos.sh` ("paths were wrong as
`common/bin/`, which silently skipped these links") corrected the `link()` calls
and missed this one, because the two failures do not look alike: `link()` prints
`skip:` and returns 0, while a direct invocation under `set -e` **aborts**.

So everything after that line never ran on either machine: the pre-commit
dispatcher install and its fan-out to every `.git-autosync` repo — the estate's
secret scanner, whose own comment records that every credential ever found in
this repo's history arrived by auto-sync. Both machines have it anyway, because
someone installed it by hand. A reprovisioned machine would have had none of it,
and the installer would have reported success right up to the point it died.

With the path corrected, `install-server.sh` exits 0 and its own verification
runs: `rejected-credential=87 DID-NOT-REJECT=0 unverified=0`.

### `1oci`: neither estate is a superset

The manifest was refreshed from zklw (64 plugins to Clavain's 61) and zklw is
now the estate of record for `ARCHITECTURE.json` and `docs/diagrams/ecosystem.html`.
Clavain correctly reports `INCOMPLETE` with the six missing plugins named and
should stop regenerating them.

The measurement was sharper than the bead: zklw has 6 plugins Clavain lacks
**and Clavain has 5 that zklw lacks**. Neither is a superset, so no comparison
between the machines could ever have decided which artefact was right — only
"did this run see everything the manifest records" has an answer.

### `iqfu`: the second copy was the older design, not a variant

`macos/.claude/hooks/git-autosync.sh` was not a Mac-specific variant of the
shared hook. It was the design the shared hook replaced. Its `LANE GUARD`
required `HEAD` to be an `autosync/*` branch — precisely the alternative
`common/` documents as rejected on 2026-06-30, citing jawnfit: 24 commits, 26
days, never merged, master frozen at the fork. macos/ was last touched
2026-07-02; the rejection was written down on 2026-07-27, twenty-five days
later.

The bead's other claims did not survive checking either. It recorded that the
Mac copy lacked the staged-secret guard; both copies had a complete one, added
to both by `1b1dca8` on the same day. Only `autosync-disabled` and
refuse-where-push-impossible were genuinely `common`-only.

Since `common/` already parameterises by `AUTOSYNC_LANE`, unification was
adoption rather than a merge. One caveat had to be handled: FLUXrig, the Mac's
single `.git-autosync` repo, sits on `main` with an empty marker. The old guard
refused it outright; the surviving hook treats an empty marker as "push the
checked-out branch", so adopting it unchanged would have **started** auto-pushing
`main`. It was given `LANE=1`, so `HEAD` stays on `main` and commits go to
`refs/heads/autosync/clavain`. A deliberate deviation from "no behaviour change",
taken because the alternative was a regression.

### What this half found that the surface could not

Three of the four discoveries here were invisible to every existing check, in
the same way: **something existed, looked populated, and was wrong.** The
superpowers directory had files. The installers ran and printed success. The
`AGENTS.md` on each machine read as authoritative. A check that asks "is it
there?" cannot see any of it; only "is it what the installer says it should be"
can.

The exception is `Sylveste-0dk3`, found the same day and filed separately:
`guard-zklw-destructive-git.sh` is present on zklw and **registered nowhere**, so
the destructive-command guard is not running on the machine that executes with
`--dangerously-skip-permissions`. The Mac wires it and zklw does not. It is worth
recording *why* `rig-hook-liveness` cannot catch that: it reports whether hooks
**fire**, and a hook that was never registered produces no failure, no error, and
no silence distinguishable from a quiet day. The guard does still intercept
zklw-targeted commands issued from a Mac session — that was demonstrated
accidentally when it blocked a `git stash list` in an `ssh zklw` command during
this work — so the exposure is sessions running *on* zklw, not every path to it.

## Registration was mistaken for protection, 2026-08-03

The previous section closed by recording `Sylveste-0dk3` as "present on zklw and
registered nowhere". Both halves of that need correcting, and the correction is
worse than the bead.

**The bead was right when filed, and had gone stale by the time it was worked.**
Three dated backups of zklw's `settings.json` — Jul 26, Jul 27 16:43, Jul 27
17:01 — each carry zero references to the guard and exactly one `PreToolUse`
hook, which is precisely what the 07-31 measurement reported. By 08-03 the live
file registered it. Nothing accounts for the change: neither installer deploys
`settings.json` (both decline it deliberately, because Claude Code replaces it
with write-temp-then-rename, which replaces a symlink rather than following it),
and the only sync path for that file runs **live → repo** (`sync-dotfiles.sh:94`),
which is the wrong direction to have installed anything. The likeliest agent is a
tool-using session on zklw at 08-02 20:28–20:36 local, which is when both the
file and `~/.claude/audit.log` were last written. So the registration arrived by
a path nothing declares and nothing can reproduce, and it can leave the same way.

**Registration turned out not to be the thing that mattered.** The host matcher
required the command to contain `ssh … zklw`:

```bash
if ! echo "$COMMAND" | grep -qE 'ssh\s+(-[^ ]+\s+)*(zklw|slse)|ssh\s+(-[^ ]+\s+)*mk@'; then
  exit 0  # Not targeting the dev server, allow
fi
```

That is true of every destructive command issued **from** the Mac and of none
issued in a session already running **on** zklw. Measured on zklw before the fix
by feeding `PreToolUse` JSON to the hook on stdin:

| probe (as a zklw session would issue it) | before | after |
|---|---|---|
| `git reset --hard HEAD~1` | **rc=0 allowed** | rc=2 blocked |
| `git clean -fd` | **rc=0 allowed** | rc=2 blocked |
| `git stash` | **rc=0 allowed** | rc=2 blocked |
| `git checkout -- <path>` | **rc=0 allowed** | rc=2 blocked |
| `ssh zklw '… reset --hard'` | rc=2 blocked | rc=2 blocked |
| `git status --porcelain` | rc=0 allowed | rc=0 allowed |

So the guard was present, deployed, byte-identical to the repo, registered in
`settings.json`, and blocking nothing that a session on that machine would ever
issue. Every level of inspection short of executing it agreed it was fine.

Its own name is part of how it hid. Finding a file called
`guard-zklw-destructive-git` wired **on zklw** reads as confirmation. It was
written from the Mac's vantage point, where "targeting zklw" necessarily implies
an `ssh` prefix, and the name records the target rather than the vantage point.

The fix keys on whether *this host* is the dev server, by hostname (`zklw|slse`)
or by an explicit `$HOME/.claude/guard-destructive-git-local` opt-in — two ways
because the hostname has already changed once (`slse` → `zklw`) and a rename must
not silently downgrade a guard. Mac behaviour is unchanged and verified
unchanged. Refusal advice is now mode-dependent: "use scp/rsync instead" is
correct for a Mac session reaching in and meaningless for a session already on
the box, which has nowhere to copy from — and zklw has no human to reinterpret
it. The guard also answers `--mode` now, so which of the two modes a host is in
can be **asked** rather than discovered by issuing something destructive.

### The check that could not have caught it, and the one that now can

`rig-hook-liveness.py` compares the hooks `settings.json` **registers** against
evidence they ran. It starts from the registration list, so an unregistered hook
is outside its domain by construction — it cannot report what it never enumerates.

`rig-hook-wiring.py` asks the complementary question: what is present here and
registered nowhere? Its first firing found two on each machine, neither planted:

| finding | why it matters |
|---|---|
| `bd-ensure-server.sh` | tracked, edited as recently as Aug 1, named in no settings file and nowhere in the repo. Its own header says it exists "to prevent silent empty results" — a script written against silent failure, silently not running. |
| `rtk-rewrite.sh` | a `PreToolUse:Bash` hook that rewrites commands before execution, registered nowhere, while `common/.claude/hooks/.rtk-hook.sha256` is still tracked beside it. |

Cry-wolf was the failure mode to design against. Most files under a hooks
directory are not meant to be registered: helpers called by another hook, sourced
libraries, tests, and scripts a scheduler or plugin manifest runs. A naive
"absent from `settings.json`" check manufactures a finding for each, and a check
that cries wolf is how the real one hides. So an unregistered script is a finding
only when **nothing** on the machine names it — no other hook, no settings
command, no launchd plist or systemd unit, no plugin manifest, no shell rc. All
derived, no blessed-name list: that mistake was made once already in
`rig-dotfiles-deployed.py` and had to be replaced within the hour, because an
allow-list produces a false finding for every hook adopted after it is written.

Exit contract matches the deployment check — 0 clean, 1 findings, 2 cannot
assess — and 2 is not a milder 1. All three were demonstrated, plus the vacuity
case: an **empty** hooks directory returns 2, not a quiet 0.

What it does not claim is efficacy. The guard above would have passed this check
on 08-03 while still blocking nothing. Wiring and effect are separate questions
and want separate instruments.

### `Sylveste-tozs`: the right binary was already there

zklw emitted policy `schema: 1` against a gate requiring `>= 2`, so every gate
wrapper on the signer host aborted as "malformed policy". No build was needed:
`os/Clavain/bin/clavain-cli-go-linux-amd64` on zklw already emitted schema 2 with
`delegation`, as did the `bin/clavain-cli` wrapper the Mac symlinks to. The fault
was that `~/.local/bin/clavain-cli` on zklw was an 18 MB **copy** of the Jul 27
schema-1 binary, shadowing the wrapper. Replacing the copy with a symlink — the
arrangement the Mac already had — moved it to schema 2.

That is the third instance in three days of the same shape: the correct artifact
present, and a stale copy in front of it. The estate keeps differing in *how* a
thing is attached rather than *whether* it is there — `~/.claude/hooks` is a
symlink into the repo on zklw and a real directory of copies on the Mac;
`settings.json` is copy-synced live → repo on both; `clavain-cli` was a symlink
on one and a copy on the other. Each asymmetry is invisible to a check that asks
only whether the file exists.

> **Wrong, corrected below** (§ *Attachment mode is a contract*, 2026-08-03): the
> Mac's `~/.claude/hooks` is a real directory of **per-file symlinks**, not of
> copies. The reading that it held copies is what made the near-miss recorded in
> `dcaca30` look like a deployment-staleness risk, when the real defect ran the
> other way and was already live. The general claim in this paragraph — that the
> estate differs in *how* things attach — held up; this instance of it was wrong.

The message was fixed separately, and the misdirection was real: three unrelated
failures all printed "malformed policy (rc=3)" — a CLI that printed no JSON, one
too old for the schema, and a response missing fields. Only the word "malformed"
was ever accurate, and "policy" named the one thing not at fault. Each now
reports itself with the observed number against the required one.

**The workaround does not retire, and the bead's guess was wrong.** `Sylveste-tozs`
supposed that the standing "use `ic publish --auto --cwd=<abs>`, not the gate
wrapper" practice was this same root cause worked around rather than diagnosed.
It is not. That practice was learned 2026-07-22, eight days *before* the
`schema >= 2` requirement landed (`673ecf1`, 2026-07-30), and its cause is a
separate bug still present on `main`: `ic-publish-patch.sh` ends in
`ic publish --patch "$PLUGIN_DIR" "$@"`, where the positional directory parses as
an exact version. A plausible shared cause is not a shared cause; dating the two
was what separated them.

### Left undone, deliberately

- `rig-hook-wiring.py` is **tracked but declared in neither installer**, and not
  wired into `rig-health-check.sh`. Both installers and that surface belong to a
  live sibling session mid-rewrite of their exit contract. This is the same
  tracked-but-undeclared class as `Sylveste-y6rl`, accepted knowingly here rather
  than fought over a file two sessions are editing.
- The `bd-push-dolt` push on zklw now reaches its **intended** refusal —
  "requires confirmation; no tty available" — instead of "malformed policy". The
  remaining step is interactive by design and was not bypassed.
- A `PreToolUse` refusal captured inside a real session **on** zklw is still
  missing. Direct invocation of the live hook on that host is proven, and the
  harness there demonstrably runs hooks from that settings file, but launching a
  session with `--dangerously-skip-permissions` was correctly refused from here.

## Attachment mode is a contract, 2026-08-03

`Sylveste-iqfu` was closed by unifying one hook out of `macos/`, on the reading
that the four names still tracked in both trees were benign and the risk was a
future asymmetric edit. Three of the four were already divergent on the morning
this was written — by 24, 28 and 81 lines. Each machine had been running a
different version of the same hook for weeks.

| hook | `common/` → zklw | `macos/` → Mac | what it actually was |
|---|---|---|---|
| `guard-zklw-destructive-git.sh` | 115 L | 115 L, same sha | identical; duplication latent only |
| `git-autosync-pull.sh` | 79 L | 103 L, **+ lane guard** | `macos/` newer — and adopting it breaks zklw |
| `git-sync-check.sh` | 111 L, **+ deference, + stdin echo** | 139 L, **+ fetch-staleness note** | both newer, **neither a superset** |
| `git-uncommitted-nudge.sh` | 76 L, **+ deference, + stdin echo** | 157 L, **+ timeout contract** | both newer, **neither a superset** |

**"Unify to the newer copy" had no referent.** `macos/` was newer in all three
divergent cases, which inverts what `iqfu` had trained everyone to expect — but
`common/` was not simply older. It carried autosync deference and the stdin echo
that `macos/` lacked. Picking a winner would have dropped working behaviour
whichever way it went: either the deference that suppresses nagging across 93
marked repos, or the latency contract that was fixing 120 of 1545 timing-out
`Stop` events. Each file is now a union, and no host branch was needed —
nothing in either copy was actually OS-specific.

### The one place a ruling was needed, not a merge

`macos/`'s lane guard skipped the auto-pull unless `HEAD` matched `autosync/*`,
unconditionally. The lane model was decided 2026-06-30 and never wired, and the
measurement says so: on zklw **92 of 93** repos carrying a `.git-autosync` marker
are on `main` or `master`, exactly **one** is on a lane, and this Mac has no
`autosync/*` branch anywhere. Shipping that copy to both machines would have
disabled auto-pull on 92 of 93 repos on the canonical machine — and auto-pull is
the only half of autosync still working there, the `PostToolUse` push half having
been dead since 2026-07-14.

> **CORRECTED 2026-08-04 — the guard described below was removed, and two claims
> in this section do not hold.** It probed for a *local* `refs/heads/autosync/*`
> while the writer creates the lane on the remote, so it was inert by coincidence
> rather than conditional by design; and the design doc it cites decides the
> opposite of what the guard did (HEAD stays on `main` precisely so this pull
> reconciles the machines). `LANE=1` is also 7 repos, not one — "exactly one is on
> a lane" counted repos whose HEAD *is* a lane branch. Separately, "the push half
> having been dead since 2026-07-14" was true when written and is no longer: two
> repos pushed successfully on 07-29 and 07-30. See "Deference is a claim, and it
> needs a check" below.

The guard is now conditional on the lane model actually being in use — either
`AUTOSYNC_LANE` is set, or the repo genuinely has a lane branch — which preserves
the decision without shipping its unwired half. Both directions were demonstrated
on a fixture: a marked repo on `main` pulls, and the same repo skips with the lane
reason logged once an `autosync/*` branch exists.

### The channel that could have caused it with nobody editing a hook

The Mac's `~/.claude/hooks` is a real directory of **per-file symlinks** into a
per-OS tree; `install-macos.sh` links each hook individually and iterates
`common/` before `macos/`, so `macos/` won by last-write. zklw's is a **whole-
directory** symlink into `common/`. Neither is a directory of copies.

`sync-dotfiles.sh` then copied `~/.claude/hooks/*.sh` into `common/` with `cp -p`
— and `cp` **dereferences** a symlink, while `[ -f ]` **follows** one, so a
symlink to a regular file passes the only test that stood between the loop and
the copy. The loop therefore wrote `macos/` bytes into `common/` under the
`common/` name: a silent cross-tree overwrite, in the direction of the tree that
deploys to zklw, needing no hook edit at all — just a sync run. That is how the
92-of-93 breakage could have arrived on its own.

Proven in a sandbox rather than reasoned about: a `common/` file holding
`COMMON-VERSION-fixed` came back holding `MACOS-VERSION-stale`. Measured on the
real machine: **17 of 17** live hooks are symlinks, 13 into `common/` where the
copy was a file onto itself and `cp`'s complaint was swallowed by `|| true`, and
4 into `macos/` which were the live hazard. So the loop's entire current effect on
this Mac was either a no-op or the bug; it had not preserved a local hook in a
long time, because there are none left to preserve. Fixed by skipping symlinks —
a symlink into the repo is already tracked and has nothing local to preserve,
which is precisely the case the loop should never have been copying.

### Two of my own claims, corrected

`dcaca30` recorded that "a live → repo sync propagated my change" into `macos/`.
It cannot have. **No sync path writes `macos/` at all** — `sync-dotfiles.sh`
mentions that tree nowhere, and its only hook destination is `common/`. The
`macos/` copy changed because the Mac's live hook *is* the `macos/` file, so
writing the live hook wrote the repo directly. Not luck, and not a sync.

The near-miss in that note was real but backwards. It read as: the repo would
have held a fixed `common/` and a stale `macos/`, and a later `install-macos.sh`
run would have reverted the Mac. In fact the installer creates **symlinks**, so it
reverts no content; and the Mac's live guard was *already* the stale `macos/` copy
at that moment. The exposure was immediate, not deferred — and the actual danger
was the sync overwriting the **fixed `common/` copy** with the stale `macos/` one,
which would have un-fixed the machine the guard was fixed for.

### The check, and its own success path

`rig-hook-duplication.py` reports names tracked in more than one tree and whether
the copies agree, alongside which tree the live hook resolves into. A sibling to
`rig-hook-wiring.py`, not an extension: wiring asks about this machine's
`settings.json`, duplication asks about the repo's trees, and a duplicated hook is
not an unwired one — folding them together would make a non-zero exit ambiguous.

Its first firing named the three divergent pairs on both machines, with the
`runs here` column correctly differing (`macos/` on the Mac, `common/` on zklw),
which is the divergence stated as a fact about behaviour rather than about bytes.

It got two things wrong that only running it could reveal:

- It called zklw's arrangement a **copy**. A file inside a symlinked *parent* is
  an ordinary regular file, so `is_symlink()` on the file alone cannot tell a copy
  from a live link. A copy is frozen at copy time; a link is the tree's own bytes.
  Reporting the second as the first tells a reader their repo edit will not reach
  the machine when it already has — the very mental model the check exists to
  correct. It now names the mode: per-file symlink, file inside a symlinked
  directory, hardlink, or independent copy, and for a genuine copy it compares
  bytes and reports drift.
- After unification it returned **2, cannot-assess**, because only one tree held
  hooks. So it went red at the exact moment the defect was eliminated. The rule it
  was built on is right — an empty input set must not read as clean — but vacuity
  is about whether the check managed to **look**, not how few things it found.
  Zero trees is a failed discovery and stays a 2. One tree holding 21 readable
  hooks is a complete measurement with a definite answer, and is now a 0 that says
  *structurally impossible*, not merely *absent today*.

The second was invisible to every earlier firing, because all of them ran against
two trees and never took that branch. **A check's success path is also a path, and
this one had never been executed.**

### What unifying revealed downstream

Removing the four emptied `macos/.claude/hooks` entirely — they were the whole
Mac-specific hook layer. The layering mechanism in `install-macos.sh` survives for
a hook that genuinely needs it; there just is not one today.

`test-git-sync-hooks.sh` had **declined to assert** autosync deference, on the
explicit grounds that the two copies disagreed and asserting either would cement
one answer. That abstention was correct then and expired with the ruling, so it is
a real assertion now — in both directions, because "silent for a marked repo"
also passes for a hook that is silent about everything. Verified it can fail:
with the single deference line stripped from a copy, the new check goes red and
names the nudge it should not have emitted.

### Left undone, deliberately

- Neither `rig-hook-wiring.py` nor `rig-hook-duplication.py` is **declared in
  either installer** or wired into `rig-health-check.sh`. Those files belong to
  live sibling sessions mid-rewrite of their exit contract (`sylveste-2fhj`).
- **Autosync deference on zklw is silence on behalf of a half-running system.**
  The push half has been dead since 2026-07-14, so deferring for 93 marked repos
  suppresses a warning nothing else is covering. Pre-existing on that machine;
  unifying the files did not change it, and changing it is a separate decision
  from unifying them. Filed rather than folded in.
  > **RESOLVED 2026-08-04 (`Sylveste-kser`), and the diagnosis was wrong twice.**
  > The push half is dormant, not dead — it pushed on 07-29 and 07-30. And
  > "nothing else is covering" is false: a daily repair timer keeps all 93 repos
  > current, which is why exposure measured 0. The thing worth gating on was
  > therefore never the push hook. Deference is now gated on per-repo freshness
  > from any mechanism.
- `git-autosync-pull.sh` releases the lock from its `EXIT` trap even on the
  path where it never acquired one, so a session that gave up waiting would
  `rmdir` the lock the holder was using. Present in both former copies, so
  unification doubled its blast radius rather than creating it. Guarded with a
  `HELD_LOCK` flag in passing; the wider audit of that lock is filed.
- The stale `macos/.claude/hooks` comments in `rig-health-check.sh` and
  `rig-dotfiles-deployed.py` are now inaccurate. Both are owned by another
  session and were left alone; their code handles the missing directory
  correctly (`isdir()` guard), so nothing is broken, only mis-commented.

## Deference is a claim, and it needs a check, 2026-08-04

Goal: "Make autosync trustworthy on the machine that runs unattended."
`Sylveste-k0pq` (P1, closed), `Sylveste-kser` (closed). dotfiles `3c5b5b6`,
`0739f7c`.

Two advisory hooks went silent for any repo carrying a `.git-autosync` marker,
on the stated grounds that "the autosync system already pulls on start and
pushes on edit". That sentence is a claim about a subsystem, and nothing checked
it. What the measurement found is worse than the bead predicted, and in a
different place.

### Gate on the mechanism doing the work, not the one named in the comment

Across zklw's 93 marked repos: 9 have ever recorded a successful push, 81 have
no `.git/autosync.log` at all, the median last successful push is 22.1 days old
— and **0 of 93 currently hold unpushed commits or dirty files**.

That last number is the interesting one. Deference has never been visibly
harmful because something *is* keeping those repos current. It is not the push
hook. It is `git-autosync-repair.sh` on a daily timer — a different subsystem
from the one the deference comment names. The bead's own proposed fix ("gate
deference on the push half being alive") would therefore have measured the wrong
thing and still reported healthy. Ratified instead: gate on freshness from *any*
mechanism, per repo, on direct per-repo evidence.

The rule generalises past this case. When code defers to a subsystem, the
subsystem it actually depends on is the one that would have to fail for the
deference to hurt — not the one the comment credits. Those are different
questions and only the first is worth gating on.

### A failing scheduled job, overwritten by a healthier manual run

The repair timer has exited 1 on **all 11 of its recorded runs since
2026-07-28**, with a refusal count trending up (16 → 9 → 6 → 4 → 4 → 5 → 13 →
13). The stored `~/.claude/health/autosync-repair.json` read `pass` throughout,
because a later manual invocation overwrote the scheduled failure — the file is
last-writer-wins with no notion that the *scheduled* run is the authoritative
one. A dashboard that any ad-hoc run can turn green is not a dashboard.

Worse, which 13 repos need a human is **not recoverable from the record**. The
script writes its detail to stderr, the unit routes stderr to the journal, there
are no drop-ins overriding that (checked, per the drop-in rule above) — and the
journal for that run holds only the summary line. So the refusals exist as a
count and nowhere as a list. That is the "an empty result is not a zero" failure
one level up: not a wrong number, but a number with no retrievable referent.
Filed rather than guessed at.

### Inert by coincidence is not safe

A lane guard shipped in `e17a9d0` skipped auto-pull when "the lane model looked
live" and HEAD was not an `autosync/*` branch. It probed liveness by looking for
a local `refs/heads/autosync/*`. The writer pushes
`HEAD:refs/heads/autosync/<machine>`, which appears locally as
`refs/remotes/origin/autosync/*` — a different namespace. So for all 7 `LANE=1`
repos the probe answered "not live", the pull happened, and the guard was
harmless. Two independent coincidences had to hold: the wrong namespace, and no
`LANE=1` repo happening to carry a local lane branch. One `git branch
autosync/zklw` would have removed the second.

**"Currently returns the right answer" and "implements the right rule" are
different properties, and only the second survives a new repo.** This is the
same shape as the registered-but-inert guard from `0dk3`: everything short of
executing the specific path agreed it was fine.

The conclusion was independently wrong too. `dual-machine-sync.md`, in the
revision that supersedes the 2026-06-30 design, decides "HEAD stays on `main`.
The lane is a push destination, not a checkout", *because* that makes the
session-start `pull --rebase origin main` the cross-machine reconciliation
point. The guard came from the `macos/` copy, which encoded the "HEAD *is* the
lane" model that doc explicitly rejected. Preserving a rejected design behind a
conditional and calling it respect for a decision is how the rejection gets
un-made — the previous session's own note that the `macos/` copy "was the design
this one replaced" was the warning, and it went unread one file over.

### Age is evidence about a lock, not about its holder

`Sylveste-k0pq`. Both autosync hooks shared `.git/autosync.lockdir`, installed
`trap release_lock EXIT` *before* acquiring, and released unconditionally — so a
process that waited out its timeout freed the lock the holder was using. The
push hook's timeout path was `exit 0` *inside* `acquire_lock`, making "give up on
the lock" and "steal the lock" the same statement. Both also broke any lock older
than 60s with no liveness check, so two processes could each declare the other's
lock stale.

`mkdir` was never the problem and stays. What was missing is an owner record and
a liveness test, in one sourced implementation rather than a copy per hook — a
mutex with two independently-editable halves is a mutex only until someone edits
one half, which is the twice-tracked-hook defect in the one place where
disagreement means two writers running `add`/`commit`/`push` in one repo.

Two refinements that only came out of running it:

- **"Alive" and "cannot determine" must be different states.** The first draft
  had two states plus an absolute ceiling to prevent deadlock, and its own test
  caught that the ceiling then applied to a *verifiably running* owner —
  reintroducing the age-only defect on a 900s fuse instead of a 60s one. Four
  states now: verified alive (never broken, at any age), verified dead, no owner
  record (breakable — nothing will ever be shown to hold it), cannot determine
  (breakable only past the ceiling).
- **Every tie goes to waiting**, because the costs are asymmetric: a false "dead"
  gives two concurrent writers, a false "alive" gives one skipped sync that the
  repair timer picks up.

### Resolve a library from the file, not from the invocation path

Both hooks are reached as `~/.claude/hooks/*.sh` on both machines, by different
attachment modes — per-file symlink on Clavain, file inside a symlinked
directory on zklw (see "Attachment mode is a contract" above). Following
`BASH_SOURCE` through symlinks to the real file lands next to the library in the
repo under either mode, so the shared library needs **no new deployment step**.
Verified by firing both hooks through the deployed path on Clavain, where
`lib-autosync-lock.sh` is *absent* from `~/.claude/hooks` and resolution reaches
it anyway. Where it cannot be found, both hooks fail closed and log the path
they looked at.

### Four ways a check lied to itself, all caught by fixtures

The Clavain sweep reports "2 current, exit 0" — one branch of four. Every defect
below was found by fixtures that forced the other three, not by the sweep:

1. **`.strip()` on column-encoded output.** `git()` returned
   `r.stdout.strip()`, and `git status --porcelain` encodes state in the first
   two *columns*: `" M uv.lock"` parsed as `"v.lock"`. The first dirty path of
   every repo lost a character, so an allowlisted path silently read as
   unallowlisted and a repo the repair timer handles fine reported as holding
   work nothing would sync. `rstrip("\n")`, never `strip()`, on anything
   positional.
2. **The weakest fact vetoing the strongest.** `classify()` demanded the
   ahead-count before reading the log, so a repo with a *recent successful push*
   returned cannot-assess purely because it had no upstream — the evidence
   proving the mechanism works was never read. Consult evidence before letting
   an unrelated failure decide. "No upstream" remains a finding; it is no longer
   a short circuit.
3. **`ahead = None`, never `0`.** A repo whose ahead-count cannot be computed has
   not been shown to have nothing unpushed. Collapsing that to 0 is the
   `|| echo 0` mistake with a different spelling.
4. **A test that cannot fail measures nothing.** The 15-case lock proof was run
   against the *pre-fix* semantics to confirm it discriminates; it fails there on
   the k0pq case and the missing owner record. Two of its own assertions were
   also wrong at first: `grep -c` prints `0` *and* exits 1, so `|| echo 0`
   emitted `"0\n0"`; and `verdict | grep -q` under `set -o pipefail` reports the
   pipeline as failed, because `grep -q` exits on first match and SIGPIPEs the
   upstream `head`. Both are fallbacks firing on the wrong condition — the same
   class as the `| tail -3` that hid an entire beads step in `iqfu`.

### Corrections to the record

- **"The push half has been dead since 2026-07-14" was true when written and is
  now stale**, not fabricated — the logout outage documented earlier in this file
  was real. But two repos pushed successfully on 07-29 and 07-30, in a `-> main`
  log format that only exists in code from 07-27, so it recovered at least five
  days before the claim was last repeated. It is *dormant*: it fires when a
  session edits a file, and few do on that machine. A dated claim about a live
  system needs re-measuring before it is restated, not just a citation.
  Corrected in three hook headers and in `CLAUDE.md`; also still asserted by
  `mk-q6bl`.
- **`mk-q6bl` does not reproduce.** Recent zklw sessions reach 59, 42 and 2 tool
  calls with no authentication errors, so "every scheduled session fails auth
  before its first tool call" no longer holds. Left open pending a check of
  whether the *scheduled* path specifically still fails.
- **`LANE=1` is 7 repos, not 1.** The earlier "exactly one is on a lane" counted
  repos whose HEAD *is* an `autosync/*` branch (jawnfit alone). The marker flag
  and the checked-out branch are different questions, and under the current
  design a lane repo is *expected* to sit on main.
- **Gated deference is currently a no-op on zklw's fleet**, because all 93 repos
  are genuinely current. Said plainly rather than presented as a fix with visible
  effect: it changes what happens the next time something is outstanding, not
  what is reported today.

### What `git-autosync-repair.sh` covers, and what it does not

Running: yes, daily 08:45 UTC via `git-autosync-repair.timer`, confirmed in the
journal. There is a second timer, `git-autosync-promote.timer`, hourly, which
fast-forwards `main` to a green lane tip and was not previously recorded here.

Covers: fetches all 93; `--ff-only` merges a repo that is merely behind; commits
only the explicit allowlist (`uv.lock`, `.beads/issues.jsonl`, `.git-autosync`,
`docs/diagrams/*.html`); pushes; and refuses — to a human — on rebase/merge/
cherry-pick/bisect in progress, detached HEAD, conflicts, anything already
staged, any path off the allowlist, divergence, a missing remote or upstream, and
an unreachable remote.

Does not cover: hand-authored source changes, deliberately. Nor does it surface
its own refusals anywhere durable, which is the finding above.

## A correct tool can still be a data-loss hazard, 2026-08-05

Goal: "Make beads writes provably land, and stop export from being able to
destroy the file." `sylveste-vqlu` (P0, corrected, **closed 2026-08-05**).

> **SUPERSEDED, 2026-08-05.** Every path named in this section has moved. The
> check is now `dotfiles/cloud/pre-commit-beads-no-loss.py`, reached by the shared
> dispatcher in 110 of 110 tracked-export repos; Sylveste's
> `scripts/check_beads_jsonl_no_loss.py` and its test suite were deleted with mk's
> approval. See "One guard, 110 repos, and four rejected checks" below — including
> the defect the deleted copy turned out to have.

`bd export -o .beads/issues.jsonl` rewrote a tracked 3822-line export down to 458
rows of a different project's issues, and exited 0. The section below is mostly
about how I then mis-diagnosed it.

### The mechanism: cwd is invisible in the command line

bd picks its database from the current working directory. Run from
`~/projects/Sylveste` it resolves `~/projects/Sylveste/.beads/dolt` — 3829 issues,
all `sylveste-*`. Run from `~/projects`, the parent workspace directory, it
resolves `~/.beads/embeddeddolt` — 458 issues, all `mk-*`. **Both are correct.**
The export ran from the parent after the tool shell had been reset there, and
`-o` pointed at the child repo's tracked file.

Nothing here is a bd bug, which is why the bead stays open on a narrower claim:
`-o` accepts any path, and nothing ties the output file to the database it came
from. `-o .beads/issues.jsonl` reads identically whether you are in the repo or
one level above it, and only one of those is right. A command whose correctness
depends on invisible ambient state will eventually be run in the wrong ambient
state.

### Three wrong conclusions, filed at P0 before being checked

Worth recording in full, because the diagnosis cost more than the incident.

1. **"bd resolves the wrong database from this directory."** False. I measured
   once, in a shell whose cwd I had not verified, and attributed the result to
   the tool. `bd info` prints the database it resolved and would have answered
   this immediately. **Before attributing a failure to a tool, re-run the exact
   command with the ambient state made explicit** — cwd first, because it is the
   one input that never appears in the command.
2. **"Four bead writes were misrouted."** False. They landed in the correct
   database. zklw showed them absent because each machine has its own Dolt DB
   (`dolt.shared-server: false`) and they exchange state through
   `.beads/issues.jsonl` in git — absence on the other machine before the export
   travels is the *designed* state. I read normal sync latency as a data-integrity
   incident and re-filed two beads on the canonical machine to "fix" it, creating
   the only real corruption in the episode: two duplicate open P1/P2 records.
   Closed as duplicates with mk's ruling rather than deleted, so the history says
   so (`Sylveste-p4fc`, `Sylveste-cgov`).
3. **"A read-back through the same client proves nothing."** Stated as the lesson
   of the day. It is true in general and did not apply: the read-back was
   correct, the writes were fine. A real principle invoked about the wrong
   failure is still a wrong explanation, and it is more durable than a plain
   mistake because it sounds like insight.

The pattern across all three: an unexpected observation, one plausible
mechanism, no attempt to falsify it, and a P0 in a shared tracker within the
hour. Severity is not a substitute for a second measurement — and filing fast
made the wrong claim the most visible artifact of the whole goal.

### Check what already guards the path before adding a guard

`.beads/hooks/pre-commit` already ran `check_beads_jsonl_dolt_sync.py
--strict-extra`, comparing the staged export against live Dolt in both
directions. With 458 rows staged against 3829 in Dolt, **it would have refused
the commit.** The truncation was never going to land. I did not look before
building a second guard.

The new check is still worth having, but for a strictly narrower reason than the
one I would have claimed: the drift guard can only be as right as Dolt is. If the
resolved database is not the one the file belongs to, both sides of that
comparison are wrong *together* and agree. `check_beads_jsonl_no_loss.py`
compares staged against `HEAD` instead, so a foreign export fails on set
difference no matter what any database says.

Design points worth keeping:

- **No tolerance band.** Dropping one id refuses, same as dropping all of them.
  A percentage threshold is an invitation to lose a few quietly.
- **Deliberate removal stays possible, and legible**: ids recorded in
  `.beads/deletions.jsonl`, or `BEADS_ALLOW_JSONL_SHRINK=1` for a prune.
- **Cannot-assess blocks too.** Unparseable staged content, an unreadable file, or
  a `HEAD` that parses to zero ids all exit 2 and stop the commit. "I could not
  compare" and "nothing was lost" are the same silence, and it is the silence
  this repo keeps getting bitten by.
- 12 test cases in `scripts/tests/`, including a replay of the real incident and
  an end-to-end commit that is actually blocked with `HEAD` intact.

### The fleet was never corrupted

Measured on both machines: **no repo has a database whose ids are disjoint from
its committed JSONL.** Clavain 0 prefix mismatches, zklw 0. The one thing the
sweep did surface: 10 directories on Clavain and 4 on zklw resolve a database
*outside* themselves — all empty `.conductor/*` worktree dirs inheriting their
parent repo's DB. Harmless today because the files hold no ids, and the same shape
as the incident.

That sweep is not shipped as a standing check. It reports cannot-assess for 30 of
50 directories on Clavain, almost all of them repos with no beads database at all,
and a check that cannot classify 60% of its input is noise pretending to be
coverage. Filed instead of shipped — the honest version needs "no database here"
as a distinct verdict from "could not tell".

> **STILL NOT SHIPPED, 2026-08-05, and now for a measured reason.** Splitting "no
> database" from "could not tell" was necessary but not sufficient: four candidate
> signals were measured on 78 directories on Clavain and 94 on zklw, and every one
> failed either coverage or precision. Recorded in
> `Sylveste/scripts/beads-binding-inventory.py`, which is deliberately
> not a `rig-` check. Also: the claim above that 14 directories "resolve a database
> outside themselves" was wrong — bd does not walk up past the repo. Measured in
> `Sylveste/research/frankentui`, which resolves *no* database even though
> `~/projects/Sylveste` above it has one.

### The guard is repo-local, and that is a gap

`check_beads_jsonl_no_loss.py` protects Sylveste only. Every other repo with a
tracked `issues.jsonl` has no equivalent, and the parent-directory export is
exactly as easy there. The durable fix belongs in bd, in a shared hook, or in a
wrapper that refuses `-o` outside the resolved database's repo.

> **RESOLVED, 2026-08-05**, and the guess about where was half wrong. A shared
> hook was right; a wrapper was not — see the next section. The count was also
> understated: not "every other repo", but 110 tracked exports across the two
> machines, of which exactly one was protected.

## One guard, 110 repos, and four rejected checks, 2026-08-05

Goal: "Close the export hazard everywhere, not just in Sylveste." `sylveste-vqlu`
(closed), `Sylveste-g40g` (P1, filed), `Sylveste-tfvr` (P2, filed),
`Sylveste-lsh8` (P3, filed). `dotfiles/cloud/pre-commit-beads-no-loss.py`,
`dotfiles/common/.claude/hooks/guard-bd-export-pinned.py`,
`Sylveste/scripts/beads-binding-inventory.py`.

The previous section left a guard that protected one repo. Making it protect all
of them turned out to be the easy part; the instructive part was how many times
the fleet's actual shape contradicted the shape inferred from Sylveste.

### Measure the attachment surface before choosing where to attach

110 tracked `.beads/issues.jsonl` files: 49 on Clavain, 61 on zklw. Exactly one
was guarded. The question "where does a shared guard go" looked like it needed a
design; it needed a measurement, and the measurement answered it outright.

**109 of 110 already reach one file** — `dotfiles/cloud/pre-commit.sh` — by two
routes: 33 repos symlink `.git/hooks/pre-commit` at it, and 15 call it by path
from a tracked `.beads/hooks/pre-commit`. So one `run_check` line covered the
fleet with **zero per-repo edits and no change to any bd-managed marker block**,
which was the gate mk held: a guard placed inside a `BEGIN/END BEADS INTEGRATION`
block is a guard with an expiry date, because the installer rewrites it.

The 110th was `Sylveste/apps/auraken`, `git init`-ed hours earlier and holding
nothing but `*.sample` hooks while 62 tracked ids sat unguarded. Installed as a
call-by-path hook, **not** a symlink — see the hazard below. Verified by planting
a foreign export in a throwaway `GIT_INDEX_FILE` so the live repo's index was
never written; it refused, and `git status` was byte-identical before and after.

### A check whose subject is "the wrong path was used" must not take a path as input

The deleted Sylveste copy accepted a pre-extracted file plus a `--path` that
defaulted to `.beads/issues.jsonl`, and the hook passed both. Sylveste tracks
**two** exports. Staging the nested one —
`research/gsv-portfolio-39/.beads/issues.jsonl` — made the hook extract and
compare the *root* path: a clean comparison of a file nobody had touched,
reported as `ok — 500 ids kept`, exit 0.

Proven rather than asserted, before deleting the old file: the same nested fixture
returns rc=0 from the old implementation and rc=1 from the new one. The
replacement takes no arguments, finds its own paths from
`git diff --cached --name-status`, and iterates every export the commit actually
stages. The path it reads and the path it reports are the same variable.

Corollary that generalises: a guard against a class of mistake must not be
configurable in the dimension the mistake occurs in.

### Refuse at source, but weigh the blast radius of where you put the refusal

mk's condition asked for a decision between a PATH wrapper on `bd`, an upstream
change, or both. **Not doing the wrapper**, and the reason is reach rather than
difficulty: `bd` is invoked by the pre-commit hooks of 110 repos, by
`bd hooks run pre-commit` *from inside* those hooks, by SessionStart hooks, and by
autosync timers on both machines. A wrapper that mis-parses one argument stops
committing everywhere. That is a strictly worse failure than the single incident
it would prevent.

The same refusal placed on the PreToolUse Bash matcher sees only tool-issued
commands, so a bug in it cannot reach a timer or a hook. The rule is decidable
from the command text alone — a file-writing `bd export` must pin its database
with `-C`, `--db`, or `--directory` — with no cwd inference and no shell
emulation, because a guard with its own ambient-state dependency is the bug
wearing a badge. It converts a command whose correctness depends on where you are
standing into one that states its own source: the difference between a convention
and a mechanism is that the mechanism makes the convention the only way through.

Deliberately **fail-open**: any parse failure allows the command. A guard that
blocks every Bash call because its own input surprised it is worse than a missed
unpinned export, and the commit-time check is the layer that actually prevents
data loss. 27 assertions, most of them false-positive cases — `export FOO=1 && bd
list`, `echo bd export -o x`, `grep -rn "bd export -o" docs/`.

### Four signals, none shippable: when the honest deliverable is a measurement

The charter allowed "ship the DB-binding sweep properly **or say plainly that you
are not." Not shipping it, having measured why:

| signal | coverage | precision |
|---|---|---|
| declared `issue-prefix` vs export ids | 7 of 48 repos (14%) | perfect (0 findings) |
| is there a database inside the repo? | full | 34 standing false alarms |
| more than one prefix family in one export | full | 10 of 43 false positives |
| export vs the live database | full | does not complete |

Each rejection was a fact about the fleet that Sylveste could not have told me:

1. **Almost nothing declares a prefix.** 7 of 48 on Clavain, 9 of 59 on zklw. A
   prefix check reproduces the 87%-silence defect it was meant to fix.
2. **"No local database" is the normal shape of a research clone**, not a defect —
   and an export run in such a repo *fails* with "no beads database found" rather
   than writing foreign data, because bd does not walk up past the repo. A check
   red on 34 repos daily is a check nobody reads.
3. **Multiple prefix families are benign**: clones inherit the upstream project's
   `bd-*` ids alongside their own. `research/ntm` carries `bd`+`br`+`ntm`.
4. **The real question needs `bd` per repo**, which spawns a Dolt server per
   database — and does not finish: Nartopo and mediumsetting both fail to open
   with pending schema migrations on dirty tables (`gastownhall/beads#4566`,
   filed as `Sylveste-tfvr`). Found only because I went looking for ground truth
   instead of trusting the filesystem.

Three separate times the design came from Sylveste and the fleet contradicted it.
Sylveste is the *least* representative repo here: hand-tuned config,
`dolt.shared-server: false`, its own `dolt/` directory where everything else has
`embeddeddolt`. That last one silently classified 40 healthy repos as having no
database, because the marker list was derived from the one repo that is different.

**The rule: when a check must generalise across a fleet, derive its inputs from
the fleet. The repo you are standing in is a sample of size one, and if it is the
one you have been tuning, it is the worst available sample.**

The residue is worth keeping, so it shipped as an inventory — exit 0, no findings
by construction, and its docstring carries the table above. A number in a summary
is not an alarm, and dressing one up as a check is how a check earns being
ignored.

It lives in `Sylveste/scripts/` rather than `dotfiles/common/.local/bin/` beside
its siblings, and the detour is itself worth recording.
`cloud/pre-commit-config-invariants.sh` refused the commit: *"a tracked file in a
deploying tree that nothing names is in git and on no machine."* Correct, and the
two sanctioned remedies — a link line in `install-macos.sh` / `install-server.sh`,
or a `NOT_DEPLOYED` entry with a reason in `rig-dotfiles-deployed.py` — all land in
files a live sibling session had committed to 40 minutes earlier. Overriding with
`SKIP_CONFIG_INVARIANTS=1` was available and wrong: the guard had correctly
identified that I was about to track a file that would exist nowhere. Moving the
file was the honest third option, and the tool sweeps `~/projects` from either
repo.

### Verify the external name, not the one the binary says

The `bd` binary's own strings give `github.com/steveyegge/beads`. That path
redirects; the canonical repo is `gastownhall/beads`. One `gh repo view` before
writing it into an artifact, and the drafted report goes to the right place.

### Two of my own suites were not being run at all

Found while checking whether my new suite would be counted, after a sibling
session fixed one of mine (dotfiles `41c96be`): `rig-health-check.sh` sums the
estate total with `grep -oE 'passed: [0-9]+ *  *failed: [0-9]+'`, so a suite
ending "15 passed, 0 failed" reads correctly to a human and matches nothing.

Worse for `test-rig-autosync-freshness.sh`: I had put it in
`common/.local/bin/tests/`, a directory I created for it, containing only it —
and `rig-health-check.sh` globs exactly **one** tests directory,
`common/.claude/hooks/tests/`. Fifteen assertions sat unrun for a day in a
directory read by nothing. Moved, resolution fixed to the house three-candidate
pattern, tally corrected; they now run daily.

The estate *does* report untallied suites — the UNTALLIED guard prints a count of
them. It never names them, and a count without names is not actionable, which is
exactly why the loop stayed open long enough for me to add to it. My own sweep for
others was a rough probe and should not be read as an audit: it had false
negatives (suites using `$PASS`/`$FAIL` rather than `$pass`/`$fail`) and one false
positive (it matched an earlier `echo` line, not the final conforming `printf`).

### The hazard one level up, filed not fixed

Adding the beads check to `cloud/pre-commit.sh` made that file the enforcement
point for data integrity across 110 repos as well as for secret scanning. 33 of
those repos reach it through a **symlink**, and `bd hooks install` appends to the
hook it finds — through the link, into the shared file. husky replaces its target
outright. Either way the damage reaches all 110, and it has happened once already
(`mk-cbz5`, 2026-07-27), which is why 15 repos already call the dispatcher by path
instead.

Filed as `Sylveste-g40g` (P1) on mk's ruling rather than fixed here: converting 33
hooks is not what this charter asked for. The remedy is to change the install
shape in `cloud/install-hooks.sh`, which already verifies each repo by planting a
credential in a throwaway index — with the ordering care that whatever converts
them must not itself write through the links it is replacing.

> **RESOLVED, and the number was wrong by an order of magnitude.** Not 33 links but
> **389**, across the two machines. See "The unit of a hazard is not the unit you
> happen to be counting" below: 33 was Clavain's tracked-export repos only, and
> repos were never the right unit in the first place.

## The unit of a hazard is not the unit you happen to be counting, 2026-08-06

`Sylveste-g40g` was chartered as "convert the 33 symlinks". Three of those five
words were wrong.

**Not 33.** That figure came from the previous goal's scan, which had been scoped
to repos carrying a tracked `.beads/issues.jsonl` on Clavain. The estate-wide
count is 206 on Clavain and 183 on zklw.

**Not "the symlinks", as though repos held them.** 416 repos read those 389 files.
A worktree has no hooks directory: `git rev-parse --git-path hooks` resolves
through the **common** dir, so every worktree reads its parent's hook. One file in
`shadow-work/.husky/` is read by nine checkouts — the repo, two sibling clones and
six `.claude/worktrees/`.

That single fact dissolved the charter's own gate. It had asked which
`.claude/worktrees/*` and `elf-revel-sessions/*` snapshots were disposable enough
to delete rather than convert, and whether `shadow-work-f2` and
`shadow-work-spike-wf` pointing at another repo's `.husky` needed separate
handling. The answer to all of it is that they own nothing: converting the parent
converts every reader, and **nothing needed deleting**. A question that looks like
a judgement call is sometimes just a measurement not yet taken.

It was also a live bug in the check. Its dedupe keyed on the path **string**, and
git returns `/private/var/...` for a worktree where `os.path.join` produces
`/var/...`, so one shared file counted twice. Keyed on the realpath of the
**directory** now — realpath of the *file* would follow the very symlink under
inspection and collapse the whole estate to a count of one.

### The row of the table that was false

`rig-hook-integrity.py` existed to prevent recurrence of `mk-cbz5` and carried a
table of which hook directories a tool regenerates:

| location | owner it claimed | regenerated | true? |
|---|---|---|---|
| `.husky/_/pre-commit` | husky | yes | yes |
| `.beads/hooks/pre-commit` | beads | yes | yes |
| `.husky/pre-commit` | user | no | yes |
| **`.git/hooks/pre-commit`** | **git** | **no** | **NO** |

205 of Clavain's 206 links and 180 of zklw's 183 sat in that last row. So the check
reported *"none in a regenerated directory"* and passed, over an estate where a
single `bd hooks install` in any repo would have edited the file all of them share.

Falsified by measurement, not by argument. `bd hooks install --help` states its
default target **is** `.git/hooks/`, and a decoy probe against bd 1.1.2 — a symlink
at `.git/hooks/pre-commit` pointing at a sentinel file, in a throwaway repo —
modified the sentinel and left the link intact, in all three modes (`default`,
`--force`, `--chain`). 84 of the 389 links were in a repo with such a tool already
installed; the other 305 were defended by nobody having run `bd init` there yet.

`.git/hooks` is not git's private directory. It is the **default target of every
hook installer there is**, which makes it the most exposed location in the table
rather than the one that needed no entry.

### Two more blind spots, and one that would have arrived with the fix

Links were probed at four paths **relative to each repo**. Three on zklw lived in
an absolute `core.hooksPath` target outside their repo and were invisible — see
the phantom tree below.

And the liveness guard was `linked == 0 → NO VERDICT`. True only while linking was
how repos reached the dispatcher. The remedy for the hazard is to stop linking, so
a fully converted, fully healthy estate would have answered *"nothing was
verified"* on the very run that proved the repair worked. It asks about **reach**
now, satisfied by a link, a copy or a call-by-path shim alike. **A check whose
liveness guard is written in terms of the defect cannot survive the defect being
fixed.**

### The phantom tree, and what it was hiding

`~/projects/Demarch/` on zklw: a real directory, not a symlink, not a git repo,
created 05:24 on 2026-07-27 and containing nothing but empty scaffolding and three
hook symlinks. `install-hooks.sh` documents this failure as the thing its guard
prevents — a repo carrying another machine's absolute `core.hooksPath`, where
`mkdir -p` builds a hooks tree nothing reads. The guard only rejects paths
**outside `$HOME`**, and `/home/mk/projects/Demarch/...` is inside it, so the tree
got built.

Three Sylveste subrepos pointed at it. They looked protected, and were — through a
directory nobody owned. What that concealed is the part worth keeping: each of the
three **already had its own bd-generated `.beads/hooks/pre-commit`**, and the
absolute `core.hooksPath` had been overriding it since 27 July. Their own beads
hooks had not run in ten days, and nothing said so.

Repointing them at their own (now **relative**) `.beads/hooks` restored those hooks
and immediately cost the three their secret scan, because a bd hook does not call
the dispatcher. `rig-hook-integrity` named all three and reported the coverage drop
— 245 → 242 — within minutes of my causing it. **The check earned its keep by
catching the person changing it.**

And then two true counts disagreed. With the tree orphaned, the check reported
*"0 symlink(s) remain"* while `find ~/projects -name pre-commit -type l -lname
'*cloud/pre-commit.sh'` reported 3. Both were correct: the check enumerates links
reachable **from a repo**, so orphaning the tree removed those links from its view
without removing them from the disk. **A check that walks repos cannot see a hazard
that has stopped belonging to one** — and "nothing points at it" is a weaker
property than "it does not exist", because one `git init` restores the pointer. The
three were converted directly with the same generator; `find` now returns 0 on both
machines. The installer could not do it, and was right not to: its ownership guard
refused because `~/projects` is itself a git repo on zklw and owns that path.

### A permanent skip is a permanent hole

The installer's response to a repo-provided hook was to skip and print that a human
should wire the dispatcher in. That ending only works if someone is that human.
Nobody was, so three repos that **commit unattended** went unscanned, and the daily
check would have named the same three every day — which is how a check earns being
ignored.

It now **augments**: the call is prepended, above the tool's block, outside bd's
markers, which bd documents it preserves across installs. The tool's block is
untouched. Narrow to `.beads/hooks` on purpose — that file is a generated artifact,
where `shadow-work/.husky/pre-commit` is a hand-written repo gate and still a
human's to wire. Prepended rather than appended because the block below can exit 0
early, and a scan placed after it does not run on the commits that take that path.

### Proving the ordering rather than asserting it

Every write in the sweep happens on a path that may still be a symlink at the one
shared file, and `> "$hook"` on such a path truncates the **target**. The first
repair of the 2026-07-27 incident did exactly that while reporting the repo FIXED.

So `install-hooks.sh` hashes the dispatcher before and after every run and fails
loudly if it changed, because *"the code unlinks first"* is a claim about the code.
`write_hook()` unlinks first **and** refuses if the path survives the unlink; the
suite's mutation test found those are two independent protections, since deleting
the unlink alone did not clobber — the refusal branch caught it.

Hook content is generated by one function rather than written per repo, because
hand-writing it had already drifted three ways for the same three lines
(`|| exit 1` without `"$@"` in two repos, `"$@" || exit $?` in the installer).

A separate `convert` mode rewrites only what is already wired. Under `SELECT=all`,
plain `install` would also have added hooks to third-party checkouts and vendored
eval corpora — a change in **coverage**, which is a different decision with
different arguments behind it, and afterwards nothing could have said which repos
the change actually touched.

### Two tests that were passing for the wrong reason

Five assertions in `test-rig-hook-integrity.sh` failed against the corrected table
and were right to: their fixtures built healthy repos out of symlinks. Two of them
had never tested anything.

- The **tracked-hook** test ran fixtures outside `$HOME`, where the installer's own
  guard skips every repo. It asserted that an untouched file was untouched by a
  sweep that never reached it. It now also asserts the sweep *reported* the skip.
- The **broken-link** test moved the dispatcher aside, which makes the check fail
  one step earlier — "the dispatcher is unreadable" — and return before the link
  scan runs. It asserted only `rc == 1`, so it passed without ever exercising a
  broken link. It now plants a link whose target is absent and asserts the wording.

**An assertion on an exit code alone cannot tell which of several findings produced
it.** Both of these passed for years on the strength of a number that many
different failures can produce.

### The rule

A file shared by N consumers must not be writable through any one consumer's
tooling. The supported shape is a real file that calls the shared file by path:
a rewrite then costs one repo its checks, loudly and locally, instead of costing
every repo its checks, silently.

Measured after, on both machines: **0 symlinks remain**, 521 repos rejected a
planted credential through a throwaway index (276 Clavain, 245 zklw), **0 did
not**, 93/93 unattended repos on zklw scan, and every pushable repo on both
machines meets its stated floor of zero. `ushas` was fixed in passing and was a
coverage gap rather than a shape one — it had bd's `post-*` and `pre-push` hooks
and no `pre-commit` at all, and had been failing Clavain's floor since 01:00 that
day.
