# docs/research/ gitignore tracking decision (Sylveste-aso)

Date: 2026-06-22
Status: Draft — documents the de-facto decision and one residual fix
Bead: Sylveste-aso ("Umbrella gitignore: docs/research/*/ rule is leaky for nested content")

## TL;DR

The bead's stated problem — "the `docs/research/*/` rule only matches top-level
subdirectories, so nested content (`docs/research/flux-drive/X/Y.md`) gets through" —
**rests on a false premise about git semantics.** The rule is not leaky. The 12 flux
review dirs that got committed in the 2026-04-19 sweep were committed *on purpose* by
explicit negation rules, not by accident through a leaky pattern.

A decision among the bead's three options has effectively already been made in tree:
**option (a) applied selectively** — flux-* review trees are tracked, generic research
dirs stay ignored. The only genuine residual is a small over-inclusion edge (flux
`INPUT/` scratch dirs are committable), which is the opposite of the bead's framing.

## Evidence

### The pattern is NOT leaky (git ignores dirs transitively)

`.gitignore:84` is `docs/research/*/`. Tested against a deeply nested path:

```
$ git check-ignore -v docs/research/foo/bar/baz.md
.gitignore:84:docs/research/*/   docs/research/foo/bar/baz.md     # IGNORED
```

Once git matches and ignores a directory (`foo/`), every file beneath it is excluded.
There is no "top-level only" defect. The bead's core technical claim is incorrect.

### Why flux dirs actually got committed: negation rules, not leakage

`.gitignore:84-90` (current):

```
docs/research/*/
!docs/research/dialectics/
!docs/research/flux-drive/
!docs/research/flux-research/
!docs/research/flux-review/
!docs/research/f1-cypher-benchmark/
!docs/research/f6-ab-corpus/
```

The `!docs/research/flux-drive/` etc. negations were added 2026-04-01 in commit
`ecba688a` ("chore: resolve beads merge conflicts"). They deliberately re-include
those trees. The 2026-04-19 sweep commit `f9e8ae50` committed 15 flux-drive session
dirs precisely because those negations made them trackable.

Commit `41cfd152` (also cited) committed content under `docs/flux-drive/` and
`docs/flux-review/` — paths with **no `docs/research/` prefix at all**, never matched
by any research rule. Commit `de72314a` placed content under `docs/research-notes/`
specifically *because* `docs/research/` is ignored — confirming contributors
understood the rule works.

### Current tracked state (the de-facto decision)

- 1138 files tracked under `docs/research/`, including 85 flux-drive session dirs.
- Generic research dirs remain ignored: `docs/research/microrouter-phase1/` shows as
  `!!` (ignored) in `git status --ignored`.

This is the bead's **option (a)** ("accept that review outputs are now tracked"),
narrowed to the flux-* trees rather than applied globally.

### The genuine residual (opposite of the bead's framing)

Because the negations re-include the *entire* flux-* trees, review scratch input
dirs are committable:

```
$ git check-ignore -v docs/research/flux-drive/INPUT/
# (no output) — NOT IGNORED, fully committable
```

At session start, `docs/research/flux-drive/INPUT/`, `INPUT-20260501T2239/`, and
several `*-20260517T2357/` session dirs are untracked-and-committable. The bead's
option (c) ("keep large artifact outputs ignored, commit only synthesis/summary
markdown") was **not** implemented — all flux content (SYNTHESIS.md + per-agent
fd-*.md + raw INPUT scratch) is tracked indiscriminately.

## Decision

Ratify **option (a), selective**: flux-* review trees are intentionally tracked;
generic `docs/research/<x>/` stays ignored. This matches what is already in tree and
what flux runs produce every session. No change to the core rule.

### Residual fix (small, optional)

If raw flux INPUT scratch should not enter history, add after line 90:

```
# Flux review scratch inputs — re-ignore inside the tracked flux trees
docs/research/flux-drive/INPUT/
docs/research/flux-drive/INPUT-*/
docs/research/*/INPUT/
docs/research/*/INPUT-*/
```

This is a cleanliness nicety, not the bug the bead described. If the team prefers
full reproducibility (keep INPUT/ for audit), skip it and the de-facto decision
stands as-is with no code change.

## Recommendation for the bead

Close as substantially resolved. The leaky-nesting bug does not exist; the tracking
decision (option a, selective) is already made and in tree. The only open item is the
minor INPUT-scratch over-inclusion above — file as a tiny chore if desired, but it
does not block closing Sylveste-aso, whose premise is invalid.
