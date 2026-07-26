# Goal Charter — Worktree-first coordination, canonical

**Bead:** sylveste-n2ma (P1) · folds Sylveste-4b5.4 · pilots Sylveste-cpd
**Complexity:** C3
**Date:** 2026-07-22
**Predecessor:** parallel-pair goals ceb0f3a6 (hook-plumbing) + 48d16471 (small-fix bundle) — both name n2ma as successor; their worktree-executor run and the publish wave are this goal's evidence.

## Title
Make worktree-first coordination canonical across Clavain, Codex, and Intercore — confirm the native primitive has replaced the bespoke machinery, write the contract, and solve the two sharp edges that actually block worktree use.

## Why (leverage)
The 2026-07-22 publish wave paid the nesting tax three times: interhelm was dual-tracked (root-monorepo dir *and* a divergent independent repo on zklw), intercut was absent on zklw entirely, and root-repo worktrees were found to materialize almost none of the interverse plugins. mk reversed a prior anti-worktree stance the same day ("it's clear you are able to use them very well now") and re-elevated n2ma P2→P1. Worktrees are now the default isolation mechanism, but the platform has no canonical contract for *when they're required*, *how beads work from them*, or *how nested repos are handled* — so every worktree task rediscovers the same edges. This goal writes the contract once and removes the two blockers that make worktrees unsafe today.

## Research findings (grounding — completed pre-charter)
- **Bespoke `GIT_INDEX_FILE` wrapper is already retired.** No executable use remains across os/ interverse/ core/ (only historical docs + two tests); `interverse/interlock/tests/structural/test_structure.py` (lines 337/351/352) already *asserts its absence*. The replace-vs-layer audit 4b5.4 demanded resolves to **already replaced** — this goal confirms and documents it rather than removing code.
- **CC native worktree config surface fully exists and is documented** (grounded at code.claude.com/docs/en/worktrees + /subagents, 2026-07-22):
  - `isolation: worktree` — subagent frontmatter field for permanent per-agent isolation; branches from default branch, auto-cleanup on no-change (v2.1.203 working-dir check; v2.1.210 covers linked-worktree main checkout).
  - `worktree.baseRef` in settings.json — `"fresh"` (default, remote default branch) vs `"head"` (current HEAD, for in-progress work).
  - `.worktreeinclude` at project root — `.gitignore` syntax, copies **gitignored files** (`.env` etc.) into every worktree. **Does NOT copy nested git repos.**
  - Cleanup sweep gated by `cleanupPeriodDays`; `git worktree lock` during runs.
- **Nested-repo hazard is doc-confirmed.** Worktrees "check out only tracked files" and share the main `.git`. Nested independent repos (interhelm, intercut, os/Skaffen, core/interweave) are gitignored/untracked in the parent → absent from worktrees, and `.worktreeinclude` can't carry them.

## Scope

### In
1. **Confirm-and-document the retirement** (fast): a written verdict that the native primitive replaced the bespoke `GIT_INDEX_FILE` machinery, citing the absent executable use + the interlock regression test.
2. **The canonical worktree-first contract** — one authored doc, agreed to (linked/referenced) across Clavain conventions, Codex install paths, Interlock (coordination layer), Intermute scripts, and Intercore docs. Covers: when a worktree is required (mutating agent/workflow fan-outs, sprint/work per-task isolation), `baseRef` fresh-vs-head guidance, `.worktreeinclude` for env files, and autosync lane discipline (worktree branches never autosync-push main).
3. **Sharp edge 1 — bd worktree-aware** (mk chose the ambitious option): make `bd` resolve the Dolt port/state from the main checkout automatically so mutating bd commands work transparently from any worktree, with concurrent-writer safety on the shared Dolt server addressed (documented locking/serialization or a stated contention bound).
4. **Sharp edge 2 — nested repos, per-repo worktrees** (encodes the 2026-07-22 lesson): contract rule that worktree isolation is **per nested repo**, not root; root-repo operations touching nested repos (publish, cross-repo sweeps) run against the main checkout; a doctor check detects a root worktree and warns which nested repos are absent.
5. **Doctor checks** covering the contract: (a) bd-write-from-worktree resolves correctly, (b) root-worktree nested-repo-absence warning. Verify exact CC flag names exist before pinning any doctor assertion (they do — see research).
6. **Pilot: resolve Sylveste-cpd** — unblock interhelm (resolve dual-tracking) and intercut (present on zklw) using the contract, as the concrete proof.

### Out
- Retiring code that's already gone (the wrapper) — this is confirm-only.
- Conductor/3kol N-parallel consumer wiring — orthogonal, stays its own bead.
- Rewriting interlock's coordination layer — preserved as the complementary layer, referenced not rebuilt.
- Publishing plugins beyond what the cpd pilot requires.

## Acceptance criteria
1. Retirement verdict written and cited (absent executable use + interlock regression test).
2. Canonical contract doc exists and is referenced from Clavain, Codex, Interlock, Intermute, and Intercore docs.
3. bd works from a worktree: a mutating bd command run from a worktree resolves the main-checkout Dolt and succeeds, with concurrency handling stated; a test covers it.
4. Nested-repo rule + doctor checks land; the root-worktree warning fires in a test/demo.
5. Sylveste-cpd resolved: interhelm and intercut publishable, or their blockers concretely cleared with the path recorded.
6. All commits pushed; bd export committed with `beads_jsonl_dolt_sync ok`.

## Completion condition (LITERAL — handed to /goal verbatim)
The worktree-first canonicalization is complete when ALL of the following are surfaced in-session: (1) a written retirement verdict is committed stating the bespoke GIT_INDEX_FILE machinery is already replaced by the native CC worktree primitive, citing both the absence of executable GIT_INDEX_FILE use and the interlock regression test that asserts it; (2) a canonical worktree-first contract document is committed and is referenced from Clavain, Codex, Interlock, Intermute, and Intercore docs, with the cross-references surfaced by grep; (3) bd resolves the main-checkout Dolt state when run from a git worktree so a mutating bd command from a worktree succeeds, with a test covering it surfaced passing and the concurrent-writer handling stated; (4) the per-nested-repo rule and its doctor checks are committed, and a test or demo surfaces the root-worktree nested-repo-absence warning firing; (5) Sylveste-cpd is resolved — interhelm and intercut are either published or their blockers concretely cleared with the resolution path recorded and the bead closed citing it; (6) all commits pushed and bd export to .beads/issues.jsonl committed and pushed with beads_jsonl_dolt_sync ok surfaced. Or stop after 80 turns and surface an accounting of the contract sections written, the sharp edges solved versus outstanding, and the cpd pilot state.

## Successor obligations
On completion, propose a successor: most likely Conductor/3kol (the N-parallel worktree consumer this contract enables) or the zklw Go-toolchain uplift (Sylveste-6f7) that unblocks canary-registering ic and Clavain-from-zklw. Keep candidates in-project.
