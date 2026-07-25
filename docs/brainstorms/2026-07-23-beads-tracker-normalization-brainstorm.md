---
artifact_type: brainstorm
bead: none
stage: discover
---

# Beads Tracker Normalization (Clavain + zklw)

## What We're Building

A **phased, diagnostic-gated normalization** of the beads tracker landscape across both machines, plus the standing hygiene rules to keep it clean. This is a strategy/cleanup effort, not a feature — the output is a `/clavain:write-plan` covering staged execution where every destructive step gates on a preceding diagnostic.

Target end-state — a **hybrid topology**:
- **Per-repo standalone `.beads` as the default** — each project owns its DB, prefix = project name, git-syncable, no cross-repo contamination.
- **One real workspace/portfolio tracker** — a genuine repo (candidate: `~/projects/Sylveste`, or a dedicated `workspace` repo) that owns cross-cutting architecture beads. This gives the currently-phantom `mk-`/"workspace bead" lane a real home.

Immediate side-effect of Stage 1: the charter-vs-plain-goal routing bead (`Sylveste-rhw`, route `classifyComplexity` + a new spend signal into the `goal-form` fork) — currently filed into Sylveste as an **interim** home — migrates to the real workspace tracker.

## Why This Approach

The diagnosis (gathered live 2026-07-23) showed the mess is real but the **beads tooling supports a clean fix** — this is not a hand-edit-divergent-DBs nightmare:
- `bd rename-prefix` — fixes Sylveste/sylveste case-split, generic `bd`/`br` research dirs, mediumsetting double-prefix.
- `bd rename` — re-IDs a single issue *and rewrites all cross-references* (deps, notes, labels).
- `bd migrate issues` — moves issues between repos (de-contaminate agmodb; migrate shared-server groups to per-repo homes).
- `bd migrate sync` — sync.branch workflow for multi-clone setups (the durable answer to worktree duplicates).
- `dolt.auto-commit` policy — governs the export churn.

Phased-over-big-bang because the DBs are divergent and the destructive-git guard + beads-smuggling hazard make inline/aggressive edits risky. The user explicitly wanted full normalization **scoped as a plan first, not done inline.** Phased also front-loads value: Stage 1 unblocks the immediate need without waiting for the risky migration stages.

## Key Decisions

- **Topology = hybrid** (per-repo default + one real workspace tracker). Resolves the phantom `mk-` cleanly by making it a real tracker.
- **Shared-server data = investigate drift first.** zklw `~/projects/.beads` (shared Dolt server, `dolt.shared-server:true`, `no-git-ops:true`) shows 5 live beads but an 828-line jsonl export (777 shadow-work, 38 Revel, 12 books, 1 Interlacer). Diff shared-server vs each per-repo DB to learn what's unique server-side before choosing reconcile-and-migrate vs just-decommission. Data-driven, no blind deletion.
- **Phantom `mk-` refs = audit each ref first.** `mk-fx3`, `mk-1od`, "workspace bead mk-fx3" in global CLAUDE.md don't exist as live IDs (the literals appear only inside other beads' note/description fields, plus interstate design docs). Per-ref disposition: is the work done / stale / still-wanted → mint a real bead or drop to prose.
- **Churn is mostly cosmetic.** `.beads/.gitignore` already ignores `interactions.jsonl` (line 16) and `backup/` (line 56); the session-start "N uncommitted" warning is `dolt.auto-commit:on` rewriting ignored files — noise, not a data-integrity failure. Low priority; confirm the gitignore holds across all repos.
- **Sequencing = phased plan**, stages gate on diagnostics:
  1. **Stand up workspace tracker** + file the charter-routing bead (unblocks immediately).
  2. **Diagnostic** — diff shared-server 828 vs per-repo DBs; audit each `mk-` ref → disposition table.
  3. **Execute migrations** — `bd migrate issues` / `bd rename-prefix` per the diagnostic.
  4. **Decommission shared server** (if diagnostic clears it) + fix CLAUDE.md refs.
  5. **Dedupe worktrees** via `bd migrate sync` (shadow-work ×6, elf-revel-sessions).

## Open Questions

- **Workspace tracker home**: reuse `~/projects/Sylveste/.beads` (267 beads, `sylveste-` prefix — already the OS/Clavain/intercore code home) or a dedicated `~/projects/workspace` repo? Reusing Sylveste is simpler; a dedicated repo keeps portfolio beads from mixing with Sylveste-project beads.
- **Two-machine sync**: once per-repo is canonical, how do Clavain and zklw copies of the *same* repo's `.beads` stay consistent? `bd migrate sync` (sync.branch) is the candidate; needs validation against the git-only sync model (Mutagen retired).
- **Prefix casing convention**: lowercase-project (`sylveste`, `nartopo`) vs PascalCase (`Nartopo`, `Revel`)? Currently mixed. Pick one canonical rule for `rename-prefix` to apply uniformly.
- **Charter-routing bead scope** (the trigger for all this): confirm it's a `spend signal + classifyComplexity → goal-form fork` architecture task, and that it lands in the new workspace tracker once Stage 1 exists.
- **zklw-in-parallel**: all diagnostics must run on BOTH machines in parallel (saved as a standing preference this session) — the plan's diagnostic phase must not be Clavain-only.
