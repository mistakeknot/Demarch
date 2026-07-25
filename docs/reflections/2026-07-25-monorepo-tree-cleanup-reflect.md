---
artifact_type: reflection
goal: 959fb6bc
stage: reflect
date: 2026-07-25
project: Sylveste
---

# Reflection: monorepo tree cleanup (goal 959fb6bc)

A C2 hygiene goal appended to the `be6423c3 → 31686951` line, taken on because
`git status` in the monorepo had become unreadable and was blocking the close
ceremony for `31686951`.

## What shipped

Five commits on `Sylveste` (`d633a1c9`, `753a6a63`, `9cfb9135`, `8d9881b2`,
`d41b643d`) and one on `os/Alwe` (`e73694b`). `.gitignore` gained `.DS_Store`,
`**/.DS_Store`, `__pycache__/`, `*.py[cod]`, `*.jsonl.lock`. Exactly one file was
deleted — a zero-byte `peer-findings.jsonl.lock` from Jun 20 — after explicit
approval, per the goal's condition 3.

## Learning 1: an unreadable `git status` is a defect, not untidiness

The tree held **52 uncommitted files**, the oldest seven weeks stale, including
charters for three goals that had *since closed* (`fa0b2a9d`, `a69d0dec`,
`40830a1b`), four brainstorms, a plan with its criteria seal, and two
flux-melange research runs. None of it was in flight in a sibling session — it
was simply invisible, buried under 23 `__pycache__` entries and a tracked
`.DS_Store` that reported modified forever and could never be cleaned.

The signal existed the whole time. It was drowned, which is operationally
identical to being absent — the same failure shape this whole line of work has
been chasing, one layer out from the code.

**Carry forward:** noise in a status channel is a defect in that channel. Fix it
when noticed, not when it finally blocks something.

## Learning 2: `git commit -- <pathspec>` cannot express a staged deletion

`git rm --cached .DS_Store` followed by `git commit -m … -- .gitignore .DS_Store`
silently **re-added** the file: `d633a1c9` shows `Bin 10244 -> 10244 bytes` where
a deletion was intended. The pathspec form commits the *working-tree* state of
those paths, overriding what was staged for them.

The pathspec habit remains correct — it is what stops a sibling session's staged
work being swept into an unrelated commit — but it has this one blind spot. When
untracking a file that stays on disk: stage the removal, verify nothing else is
staged, then commit the index with **no pathspec**.

## Learning 3: the confirming check was itself misleading

`git check-ignore -v .DS_Store` exited 1 against a rule that plainly matched,
which read as a `check-ignore` quirk. It was not: **`check-ignore` skips tracked
files unless given `--no-index`**, so the exit code was correctly reporting that
the untracking had failed. Two confusing behaviours stacked to make a real bug
look cosmetic.

**Carry forward:** when a verification disagrees with a change that "obviously"
worked, the verification is the more likely truth-teller. Chase the discrepancy
before explaining it away.

## Residual

`interverse/` is in `.gitignore:9`, yet the monorepo still tracks **198 files**
beneath it — committed before the ignore rule landed, now drifting against the
nested repos that own them. The one file touched here
(`interverse/intersight/README.md`) was already committed upstream as `c5afaab`;
the monorepo held a stale duplicate, so a file was simultaneously current and
three days stale depending on which repo you read. Syncing that one file to reach
a clean tree was correct; untangling the other 197 is its own work and was
deliberately not attempted.

## See also

- `docs/solutions/2026-07-25-unattended-work-needs-a-stopped-signal.md`
  (§ "Adjacent: ignore-noise buries real work")
- `os/Alwe/docs/reflection-31686951.md`
