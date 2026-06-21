# Beads Dolt↔JSONL sync guard (advisory)

- **Date:** 2026-06-20
- **Status:** Proposal + working prototype (NOT installed). Research artifact.
- **Author:** session research task (a67c894c)
- **Prototype:** `/Users/sma/.claude/jobs/a67c894c/tmp/beads-sync-guard.sh`
  (move into `scripts/` on install — see "Install").

---

## 1. The hazard

beads (`bd`) stores live issue state in a **Dolt database** under
`.beads/dolt/Sylveste`. The git-tracked, portable export is
**`.beads/issues.jsonl`** (one JSON object per line, produced by `bd export`).

The two are **not automatically reconciled on pull.** After a `git pull` that
updates `issues.jsonl`, the local Dolt DB is *not* re-imported. Until someone
runs `bd import`, every `bd search` / `bd show` / `bd list` / `bd count`
silently returns **stale** results against the old Dolt working set. There is
no warning — the staleness is invisible.

### Today's evidence (2026-06-20)

After a pull, the local Dolt DB held **1406** issues while
`.beads/issues.jsonl` had **3489** lines — a **~2000-issue gap**. An epic
`sylveste-owjn` present in the JSONL was **invisible to `bd`** until
`bd import` was run. The after-the-fact fix is `bd import`; nothing *warned*
that the DB was stale beforehand. (At the time this doc was written, the repo
had already been repaired: both sides read **3564**.)

### Why this is dangerous, not just annoying

Priority-driven automation (`/route`, `/work`, `bd ready`, dup-checks, the
SessionStart `bd stats` orientation line) all read the Dolt side. A stale DB
makes that automation **silently operate on a 2-month-old worldview** — it
can re-create issues that already exist, miss ready work, or "lose" whole
epics, with no error surfaced.

---

## 2. What already exists (and why it doesn't cover this)

The repo is not starting from zero. Relevant existing pieces:

| File | What it does | Gap vs this hazard |
| --- | --- | --- |
| `.git/hooks/post-merge` → `bd hooks run post-merge` | beads-managed git hook fires after every merge/pull | beads' own post-merge handler does **not** run `bd import` (verified: pull left the 2000-issue gap in place). It is the natural host but currently a no-op for this. |
| `.claude/settings.json` SessionStart | runs `session-freshness-gate.sh`, then `heal-dolt.sh`, then `bd stats \| head -1` | `bd stats` *reads* the (possibly stale) Dolt count; it never compares to the JSONL, so it reports the stale number as if authoritative. |
| `scripts/check_beads_jsonl_dolt_sync.py` | set-diff of JSONL issue IDs vs `bd sql "select id from issues"`; exits 1 on mismatch | **Right detector, wrong remedy + wrong polarity for pull-staleness.** When JSONL IDs are missing from Dolt (exactly the post-pull case) it prints *"Run `bd export`"* — the opposite of the correct `bd import`. It is also heavier (full ID set diff) and built as a blocking check, not an advisory SessionStart line. |
| `scripts/lib-cloud-guard.sh` / `lib_cloud_guard.py` | canonical cloud/sandbox detection (env vars only) | reusable; the new guard mirrors its detection. |
| `.beads/heal-dolt.sh` | repairs a down/corrupt Dolt server | orthogonal — handles *Dolt unavailable*, not *Dolt stale-but-up*. |

**Net:** the detection primitive exists but is mis-prescribed and mis-shaped
for the pull-staleness case. This proposal adds a small, correctly-polarized,
advisory guard rather than reworking the heavier ID-diff script.

---

## 3. Design

**Compare two cheap counts and warn on divergence.**

- **Dolt side:** `bd count` (no filters) → total rows in the Dolt `issues`
  table. Verified to return a clean integer (`3564`) and to match
  `bd sql "select count(*) from issues"`.
- **JSONL side:** issue-line count of `.beads/issues.jsonl` = total lines −
  blank lines − **memory lines** (`"_type":"memory"`).
- If `|jsonl_issues − dolt_issues| > tolerance` (default `0`), print a
  one-line advisory on **stderr** and **exit 0** (never block).
  - **JSONL ahead** (the post-pull case) → *"run `bd import`"*.
  - **Dolt ahead** (unexported local edits) → *"run `bd backup sync`"*.

### Properties

- **Cheap.** The grep/`wc` side is ~4 ms. The whole cost is `bd count`'s own
  process startup + Dolt connect, measured here at **~1.1 s wall**
  (0.37 s user + 0.32 s system; the remainder is `bd` binary startup, *not*
  the query). A hard timeout (`BEADS_SYNC_GUARD_TIMEOUT`, default 3 s) caps
  the worst case so a wedged Dolt server can never hang a SessionStart.
  *Caveat:* on this machine `bd count` alone is ~1.1 s, marginally over the
  "<1 s" target — the cost is fixed `bd` startup latency, identical to the
  `bd stats` line the SessionStart hook already pays. See §6 for a faster
  `bd sql` variant if the budget is hard.
- **Advisory.** Every exit path returns `0`. The signal is the stderr line,
  not the exit status. It cannot block a pull, commit, or session start.
- **Accurate / low false-positive.** Count-vs-count with `bd count` and the
  JSONL counting like-for-like (memories excluded). The only states that fire
  are genuine divergence. Tolerance is configurable for noisy environments.

### Counting like-for-like (memory records)

`bd export` writes persistent memories (`bd remember`) into the same JSONL as
`"_type":"memory"` lines, but `bd count` counts only the `issues` table.
Counting raw JSONL lines would therefore over-count by the number of memories
and produce a false "JSONL ahead" alarm. The guard subtracts memory lines
before comparing. (Note: in the *current* Sylveste export there are **0**
memory records — `_type` does not appear at all — but the guard handles them
because `bd import --help` documents the round-trip and a future
`bd remember` would introduce them.)

### Cloud / sandbox handling

In a Claude Code cloud/sandbox session (`IS_SANDBOX=yes` or
`CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default`), beads are **read-only**
and the JSONL *is* the source of truth (per `CLAUDE.md` "Cloud Sessions").
There is no live Dolt to compare against, so the comparison is meaningless.
The guard detects this with env vars only (mirroring `lib-cloud-guard.sh`;
never `which bd`, so a workstation with a broken PATH is not misdiagnosed) and
**exits 0 silently**. Likewise, if `bd` is absent, `issues.jsonl` is missing,
or `bd count` fails / times out / returns non-numeric output, the guard stays
silent — for an advisory check, false silence is preferable to a false alarm
(Dolt-down is already handled by `heal-dolt.sh`).

---

## 4. Where it hooks in — **recommendation: SessionStart**

**Primary location: the existing `.claude/settings.json` SessionStart hook,
appended after the current `heal-dolt` + `bd stats` command.**

Rationale (one paragraph): the failure mode is *"I query `bd` and silently get
stale answers,"* and the moment that matters is when an agent or human
**starts working** — which is exactly SessionStart, and is already where the
repo pays for a `bd`-process-startup orientation line (`bd stats | head -1`).
Co-locating the guard there adds the JSONL comparison that `bd stats` is
missing, reuses an already-budgeted `bd` invocation window, and surfaces the
warning in the same place the human reads orientation output. A git
`post-merge` hook is the *theoretically* tighter trigger (it fires at the
exact pull that creates the drift), but beads already owns `post-merge` via
`bd hooks run post-merge`, that handler is the thing that *should* have
imported and didn't, and editing the beads-managed block risks being clobbered
on the next `bd` upgrade — so post-merge is the right place for an eventual
*auto-`bd import`* fix, not for this advisory. SessionStart also catches drift
introduced by `dolt`-level resets, container swaps, and crashes that no git
hook sees. (Secondary/optional: also wire it into `pre-commit` so a stale DB
is caught before an agent commits a JSONL written from a stale export — but
SessionStart alone covers the observed hazard.)

---

## 5. Prototype

Full script: `/Users/sma/.claude/jobs/a67c894c/tmp/beads-sync-guard.sh`
(7.1 KB, POSIX-ish bash). Core logic:

1. Resolve repo root (`PROJECT_DIR` / git toplevel / `$PWD`).
2. Cloud/sandbox → exit 0 silently.
3. `bd` missing or JSONL missing → exit 0 silently.
4. `jsonl_issues = lines − blanks − memory-lines`.
5. `dolt_issues = bd count` under a hard timeout (`timeout`/`gtimeout`, with a
   portable background-and-kill fallback). Non-numeric/failed/timed-out → exit 0.
6. If `|drift| > tolerance` → print the directional advisory; always exit 0.

Env overrides: `BEADS_SYNC_GUARD_TOLERANCE` (default 0),
`BEADS_SYNC_GUARD_TIMEOUT` (default 3 s), `BEADS_JSONL`, `PROJECT_DIR`.

### Test results (run 2026-06-20 against the live repo, Dolt=JSONL=3564)

| # | Scenario | Expected | Result |
| --- | --- | --- | --- |
| 1 | Synced DB (3564 == 3564) | silent, exit 0 | **PASS** (no output) |
| 2 | JSONL ahead (5647 vs 3564, +2083) | fire, `bd import` | **PASS** — `STALE local DB … run 'bd import'` |
| 3 | JSONL behind (1406 vs 3564, −2158) | fire, `bd backup sync` | **PASS** — `JSONL behind Dolt … run 'bd backup sync'` |
| 4 | 3564 issues + 10 `"_type":"memory"` (3574 lines) | silent (memories excluded) | **PASS** (no output) |
| 5 | `IS_SANDBOX=yes` with drift | silent skip | **PASS** |
| 5b | `CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE=cloud_default` with drift | silent skip | **PASS** |
| 6 | `bd` not on PATH, with drift | silent, exit 0 (no false alarm) | **PASS** |
| 7 | 3-issue gap, `BEADS_SYNC_GUARD_TOLERANCE=5` | silent (within tolerance) | **PASS** |

Reproduce test 2 (the headline hazard):

```sh
cp .beads/issues.jsonl /tmp/ahead.jsonl
for i in $(seq 1 2083); do
  printf '{"id":"sylveste-fakedrift%04d","title":"pulled but not imported"}\n' "$i" >> /tmp/ahead.jsonl
done
BEADS_JSONL=/tmp/ahead.jsonl bash scripts/beads-sync-guard.sh
# → beads: STALE local DB — JSONL has 5647 issues, Dolt has 3564 (2083 not yet imported).
#   beads: run 'bd import' to load the pulled issues (bd search/show are stale until you do).
```

---

## 6. False-positive analysis

- **Memory records:** excluded by construction (test 4). Zero in the current
  export, but handled for future `bd remember` use.
- **Infra beads:** `bd export` excludes infra (agents/rigs/roles/messages)
  *and* `bd count` counts the `issues` table, which likewise excludes them.
  Both sides exclude the same population, so they net out. Verified: both = 3564.
  *Risk:* if `bd count`'s population and `bd export`'s default population ever
  diverge (e.g., a future `bd` that counts gates), a constant offset would
  appear. Mitigation: `BEADS_SYNC_GUARD_TOLERANCE` absorbs a small constant
  offset; if a persistent non-zero baseline shows up, switch the JSONL side to
  `bd export | wc -l` (identical population by definition) — see below.
- **Transient mid-sync state:** `bd backup sync` runs every 5 min and rewrites
  the JSONL; a fire during that ~sub-second window self-clears next session.
  Advisory + exit-0 means no harm.
- **Dolt down / slow:** `bd count` fails or times out → silent (not a false
  positive; `heal-dolt.sh` owns that path).
- **`bd` absent / cloud:** silent by design.

**Tighter (but slower) variant.** To make both sides count *exactly* the same
population, replace `bd count` with comparing `bd export | wc -l` against the
committed JSONL line count — but that re-serializes every issue (much heavier)
and is unnecessary given the verified population match. For a *faster* Dolt
side, `bd sql "select count(*) from issues"` is available, though it carries
the same `bd`-startup latency as `bd count`. The existing
`check_beads_jsonl_dolt_sync.py` is the precise-but-heavy ID-set option if an
exact reconciliation (not just a count) is ever wanted.

---

## 7. Install (manual — do this to enable; NOT done by this proposal)

1. **Move the prototype into the repo:**
   ```sh
   cp /Users/sma/.claude/jobs/a67c894c/tmp/beads-sync-guard.sh \
      scripts/beads-sync-guard.sh
   chmod +x scripts/beads-sync-guard.sh
   ```

2. **Wire it into SessionStart.** Edit `.claude/settings.json`. The current
   SessionStart `command` is (line ~18):
   ```sh
   bash -c 'cd "$PROJECT_DIR" && bash scripts/session-freshness-gate.sh && exit 0; [ -f .beads/heal-dolt.sh ] && bash .beads/heal-dolt.sh .beads 2>&1 || true; bd stats 2>/dev/null | head -1 || echo "beads: Dolt unavailable, JSONL backup is source of truth"'
   ```
   Append the guard after the `bd stats` line (it self-skips when fresh
   because the `session-freshness-gate.sh && exit 0` short-circuit runs
   first on unchanged state):
   ```sh
   bash -c 'cd "$PROJECT_DIR" && bash scripts/session-freshness-gate.sh && exit 0; [ -f .beads/heal-dolt.sh ] && bash .beads/heal-dolt.sh .beads 2>&1 || true; bd stats 2>/dev/null | head -1 || echo "beads: Dolt unavailable, JSONL backup is source of truth"; bash scripts/beads-sync-guard.sh'
   ```
   The guard prints to stderr only on drift and always exits 0, so it never
   changes the hook's success/failure behavior.

3. **(Optional) also guard pre-commit.** Add `bash scripts/beads-sync-guard.sh`
   to a project pre-commit step if you want stale-export protection before an
   agent commits.

4. **Verify** with the test-2 reproduction in §5 (induce drift, confirm it
   fires; confirm it is silent on a synced repo).

### Future work (out of scope here)

The *real* fix is to make a pull actually re-import. File a bead to add
`bd import` (idempotent upsert) to the beads `post-merge` handler — or, if the
beads-managed block can't be touched, to the interwatch-managed prelude in
`.beads/hooks/post-merge`. This advisory guard is the cheap interim warning
until that lands.
