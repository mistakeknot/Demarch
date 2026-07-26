---
artifact_type: solution
goal: 31686951
stage: compound
category: observability
tags: [scheduling, launchd, staleness, alarm-thresholds, health-checks, omitempty, git-hygiene]
---

# Anything unattended needs a signal that says it stopped

Third entry in the line from
[`2026-07-24-cli-dependency-as-optional-accelerator.md`](2026-07-24-cli-dependency-as-optional-accelerator.md).
Solved 2026-07-25 under goals `31686951` and `959fb6bc` in `os/Alwe` and the
Sylveste monorepo.

## The trap: a fallback that is only incidentally fresh

Two prior goals built a local index and made every capability fall back to it.
Nothing kept the index current — it was fresh only because someone had been
refreshing it by hand while working. The fallback was real in a demo and
theoretical in practice.

Worse, the obvious fix (add a cron job) is the weaker half. **A scheduled job
that silently stops looks exactly like one that is working:** queries keep
succeeding, just against progressively older data. That is the same defect the
whole line of work started from — a repair deferred forever with nothing
reporting that it never happened — reproduced one layer up.

```go
// Ship these together, always.
LocalStale                 bool  `json:"local_stale,omitempty"`
LocalAgeSeconds            int64 `json:"local_age_seconds"`  // NOT omitempty; see below
LocalStaleThresholdSeconds int   `json:"local_stale_threshold_seconds,omitempty"`
```

**Rule:** when you add something that runs unattended, add the signal that says
it stopped. The question is not "does this work?" but "if this quietly died, what
would tell me?"

## Pattern: alarm thresholds have two failure modes

Set the staleness window to **2× the schedule interval**, not 1×.

- Too loose misses the fault.
- Too tight fires on ordinary scheduling jitter — and an alarm that fires
  routinely is one the operator learns to ignore. That reproduces silence by a
  different route: the signal is present, technically correct, and useless.

At 300s scheduling and a 600s window, one missed run is tolerated and a dead
indexer surfaces within ten minutes. Distinguish *never ran* from *ran too long
ago*, because the remedies differ:

```go
if cov.LastIndexedUnix == 0 {
    return "local catalog has never been indexed — run `alwe index`"
}
return fmt.Sprintf("last refreshed %ds ago, past its %ds window — the indexer "+
    "may be stopped or wedged; run `alwe index`", age, threshold)
```

Note the mirror-image mistake to avoid: the CLI this work backstops uses a 300s
staleness threshold against indexing cadences far longer than that, which is
exactly why its health check exits non-zero most of the time and why we stopped
trusting it. Having criticised that, making the same error inverted would have
been careless.

## Pattern: measure before choosing an interval, and record it where it is changed

Five warm runs over 9,647 files: **~80ms** for a full no-op scan, **~83ms per
changed file**, 6.71s to clear an 80-file backlog. At ~2.7 changed files/minute a
300s run costs ~1.2s — a **0.4% duty cycle**.

Put the derivation in the scheduler definition itself, not only in a commit
message:

```xml
<!-- StartInterval 300s is measured, not assumed: a warm run costs ~80ms when
     nothing changed and ~83ms per changed file over 9,647 files. At ~2.7
     changed files/min a 300s run touches ~13 files for ~1.2s — 0.4% duty
     cycle. Re-measure before changing this. -->
<key>StartInterval</key><integer>300</integer>
<key>Nice</key><integer>5</integer>
<key>LowPriorityIO</key><true/>
```

The next person to touch the interval then sees the numbers instead of
re-deriving them. This is the second time in this line of work that measuring
*changed* a decision rather than confirming it.

## Trap: a meaningful zero must never be `omitempty`

`local_age_seconds` was `omitempty`, so a catalog refreshed seconds ago
serialised as `null` — the **healthiest** possible state, rendered
indistinguishably from "not computed".

Tests were green because they asserted on struct fields, not the serialised form.
The fix included a test that marshals and inspects the JSON:

```go
b, _ := json.Marshal(h)
var decoded map[string]any
json.Unmarshal(b, &decoded)
v, present := decoded["local_age_seconds"]
if !present || v == nil { t.Fatal("age 0 must render as 0, not null") }
```

**Rule:** for any numeric field, ask what its zero means. If zero is a real
answer, `omitempty` is a bug. Assert on serialised output, not just structs.

## Adjacent: ignore-noise buries real work

The same session found 52 uncommitted files in a monorepo — three charters for
goals that had since *closed*, four brainstorms, a plan with its criteria seal,
two research runs — the oldest seven weeks stale. They had been invisible because
`git status` was unreadable: 23 `__pycache__` files plus a `.DS_Store` that was
**tracked**, so it reported modified forever and could never be cleaned.

```bash
git rm --cached .DS_Store        # untrack; leave on disk
printf '.DS_Store\n**/.DS_Store\n__pycache__/\n*.py[cod]\n*.jsonl.lock\n' >> .gitignore
git check-ignore -v .DS_Store   # only reports once untracked — check-ignore skips the index
```

Two things worth knowing:

- `git check-ignore` **ignores tracked files by default**, so it reports nothing
  for a tracked-but-ignored path until you untrack it (or pass `--no-index`).
  Verifying an ignore rule against a tracked file will mislead you.
- Untracking a whole ignored subtree can be much larger than it looks. Here
  `interverse/` was in `.gitignore` yet the monorepo still tracked **198 files**
  beneath it, committed before the rule landed and now drifting against the
  nested repos that own them. Syncing one file to get a clean tree was correct;
  untangling 198 is separate work and should be named as such rather than
  quietly attempted.

**Rule:** treat an unreadable `git status` as a defect in its own right. It is
not cosmetic — it is what let seven weeks of work go unnoticed.

## See also

- `os/Alwe/docs/reflection-31686951.md`
- `os/Alwe/ops/com.arouth.alwe-index.plist`
- Predecessors: `2026-07-24-cli-dependency-as-optional-accelerator.md`,
  `2026-07-25-degrading-a-cli-dependency-to-optional.md`
