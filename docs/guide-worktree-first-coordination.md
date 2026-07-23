# Worktree-first coordination — the canonical contract

**Status:** canonical (sylveste-n2ma, 2026-07-22). This is the single source of
truth for when Sylveste work runs in a git worktree, how the native Claude Code
worktree primitive relates to Sylveste's coordination layer, and how the two
known sharp edges (beads-from-worktrees, nested repos) are handled.

Grounded against live Claude Code docs (code.claude.com/docs/en/worktrees and
/subagents, fetched 2026-07-22). Version floors cited inline; verify a flag
exists for your installed CC version before relying on it.

## 0. The one-sentence contract

**Native Claude Code worktrees isolate file edits; interlock coordinates agents
that share a tree; mutating fan-outs default to worktree isolation *per nested
repo*, and root-repo operations that touch nested repos run against the main
checkout.**

## 1. Two layers, not two choices

The retirement verdict (`docs/research/2026-07-22-git-index-file-retirement-verdict.md`)
established that Sylveste's bespoke `GIT_INDEX_FILE` per-session-index machinery
is gone. What replaced it is **two complementary layers**, not one mechanism:

| Layer | Owner | Job | Mechanism |
|-------|-------|-----|-----------|
| **Isolation** | Claude Code (native) | Keep parallel *file edits* from colliding | `git worktree` — separate working dir + branch, shared `.git` |
| **Coordination** | interlock | Let agents that *share* one tree not clobber each other | file reservations + serialized commit lock (shared-filesystem mode, 0.2.16+) |

They are orthogonal. Isolation prevents collisions by giving each agent its own
files; coordination prevents collisions when agents deliberately share files.
interlock **no longer creates worktrees** (`interlock/hooks/session-start.sh:22`,
since 0.2.16 — see `interlock/docs/shared-fs-coordination.md`); use native
worktrees for isolation and interlock for the shared-tree case.

## 2. When a worktree is REQUIRED

- **Mutating agent / workflow fan-outs.** Any `Agent`/`Workflow` spawn that edits
  files in parallel with siblings uses `isolation: "worktree"` (Agent tool param,
  or `isolation: worktree` in a custom subagent's frontmatter). The worktree
  branches from the default branch by default and auto-cleans if the agent makes
  no changes. This is AGENTS.md doctrine, not a per-task decision.
- **Parallel sprint/work tasks.** Two tasks that could touch the same files run
  in separate worktrees (`claude --worktree <name>`), one branch each.

## 3. When a worktree is NOT used

- **Single-writer sessions** editing one tree — no isolation needed.
- **Agents that must SHARE a tree** (deliberately coordinated work) — use
  interlock reservations, not worktrees.
- **Root-repo operations that span nested repos** (publish waves, cross-repo
  sweeps) — see §5; these run against the main checkout.

## 4. Base branch and env files (native config)

- **`worktree.baseRef`** in `settings.json`: `"fresh"` (default — branch from the
  remote default branch, clean tree) or `"head"` (branch from current local HEAD,
  carrying unpushed work). Use `"head"` when isolating subagents that must operate
  on in-progress work. It cannot be set to a branch name; use `git worktree add`
  directly for that.
- **`.worktreeinclude`** at repo root (`.gitignore` syntax): copies **gitignored
  files** (e.g. `.env`, `.claude/settings.local.json`) into every new worktree.
  It copies files only — **it does NOT carry nested git repositories** (§5).
- Add `.claude/worktrees/` to `.gitignore` so worktree contents don't show as
  untracked in the main checkout.

**Retire bespoke worktree machinery.** `core/intermute/scripts/worktree-setup.sh`
hand-rolls `git worktree add` plus manual copies of `settings.local.json` and
`scripts/` — precisely what `worktree.baseRef` + `.worktreeinclude` now do
natively. It is a layer atop the native primitive and is slated for retirement or
reduction to a thin wrapper; new work must use the native flags, not this script.

## 5. Sharp edge — nested repos (per-repo worktrees)

`interverse/` is gitignored in the root repo; interhelm/interlock/interflux and
most inter* dirs, plus `os/Skaffen` and `core/interweave`, are **independent
nested git repos with their own remotes**. A worktree "checks out only tracked
files" and cannot materialize a nested repo; `.worktreeinclude` can't carry one
either (it copies gitignored *files*, not repos). A root-repo worktree therefore
materializes almost none of the plugins.

**Contract rule:** worktree isolation is **per nested repo**, not root.

- To mutate a nested plugin in isolation, create a worktree **of that nested
  repo**, not of the Sylveste root.
- **Root-repo operations that touch nested repos** (an `ic publish` wave,
  cross-repo sweeps) run against the **main checkout**, never a root worktree —
  the nested repos are absent from a root worktree.
- A doctor check (`§7`) detects a root-repo worktree and warns which nested repos
  are absent, so this fails loud instead of silently publishing nothing.

This rule is the direct lesson of the 2026-07-22 publish wave, where interhelm
(dual-tracked) and intercut (absent on the signer host) blocked 2 of 23
publishes (Sylveste-cpd).

## 6. Sharp edge — beads from a worktree

Beads writes go through a Dolt server whose port/state lives in the **main
checkout's** `.clavain/`. A fresh worktree has no `.clavain/`, so a naive `bd
close` from a worktree can't find the store.

**Contract rule:** `bd` resolves the main-checkout Dolt state automatically when
run from a worktree (implemented under this goal, element 3) — mutating bd
commands work transparently from any worktree, with concurrent-writer safety on
the shared Dolt server. Until a given host ships that resolution, the fallback is
read-only beads from worktrees (`bd-grep`/`bd-show` against committed
`.beads/issues.jsonl`) with mutations run from the main checkout.

## 7. Doctor checks (the contract, enforced)

- **root-worktree nested-repo absence** — if the session runs in a root-repo
  worktree, warn and list the nested repos not present (so publish/sweep ops
  don't silently no-op).
- **bd-from-worktree resolution** — verify a mutating bd command from a worktree
  reaches the main-checkout Dolt (green once element 3 lands).

## 8. Autosync lane discipline

Worktree branches (`worktree-<name>`, `work/<name>`) are **never**
autosync-pushed to `main`. Autosync operates on the main checkout's lane
branches only (see the dual-machine lane model). A worktree merges to main by
deliberate action, not by the autosync timer.

## Consumers referencing this contract

- **Clavain conventions** — `os/Clavain/AGENTS.md` (Topic Guides + Conventions)
- **Codex integration** — `os/Clavain/agents/codex-integration.md`
- **Interlock coordination** — `interverse/interlock/docs/shared-fs-coordination.md`
- **Intermute scripts** — `core/intermute/AGENTS.md` (and worktree-setup.sh retirement, §4)
- **Intercore** — `core/intercore/AGENTS.md`
