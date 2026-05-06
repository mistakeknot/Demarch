---
date: 2026-05-06
session: 8ba2521d
topic: a4oj Phase 1 + canonical-witness shipped — take sylveste-a4oj.4 (MCP OAuth gating) next
beads: [sylveste-a4oj, sylveste-a4oj.1, sylveste-a4oj.2, sylveste-a4oj.3, sylveste-a4oj.5, sylveste-a4oj.7, sylveste-a4oj.8, sylveste-a4oj.4, sylveste-a4oj.6, sylveste-a4oj.13, sylveste-o8wo]
---

## Session Handoff — 2026-05-06 a4oj Phase 1 shipped, MCP OAuth gating next

### Directive

**Take `sylveste-a4oj.4` next.** It's the last open P2 from Phase 1 sequencing.

The bead's scope: workspace-aware `mcpProfile: dev` setting in `.claude/settings.json` that suppresses 20 deferred OAuth tools (Notion/Gmail/Calendar/Drive) which the deferred-tools listing carries every session for <5% per-session usage in dev workflow. Plus a sub-finding (M-03): trim the tldr-swinton instructions block (~600 tokens of marketing/cost-ladder text) to status-only.

Source findings: M-01, M-03 (`fd-mcp-server-hygiene`, Track A). Estimated savings: ~1kt/session combined. Difficulty: S.

Investigate first: how `.claude/settings.json` declares MCP servers (already has the `permissions.allow` block we patched in `sylveste-o8wo`, but the MCP-server enable/disable mechanism needs to be located). The mcpProfile concept may not exist yet — could be a new convention we're introducing, in which case the bead expands a bit.

### Dead Ends

- **`sylveste-a4oj.6` (stall-rescue in flux-watch.sh) was implemented end-to-end this session, then reverted in the working tree before commit.** All 4 test scenarios passed (control / both stall / .partial in progress / real arrival mid-wait), but the changes to `scripts/flux-watch.sh`, `skills/flux-drive/phases/launch.md`, and `skills/flux-drive/phases/shared-contracts.md` were unwound between my edits and a follow-up turn. Bead is reopened (status=open). The implementation design is sound; if the next session retries, the same approach should work — main risk to ask about is *why* the revert happened (lint? scope conflict? different agent's parallel edit?). See bead notes for the full design.

- **`docs/roadmap-v1.md` is NOT an orphan interpath witness** despite its suspicious filename. It's a hand-curated v1.0 release-goals planning doc with a track-A/B/C version-gate model, last touched 2026-04-27 by "Refresh autonomy roadmap audit state". The `sylveste-a4oj.7` rule explicitly exempts hand-curated parallel docs; do not archive it.

- **interpath's existing canonical-path convention uses `${module}-{vision,roadmap}.md`**, not `vision.md` / `roadmap.md` as SCRIP-2 originally proposed. The convention was already correct — the gap was the SKILL prose saying "Write to the appropriate location" which let agents drift to dated variants. Don't try to renormalize to `docs/vision.md` — that would break existing references.

- **Subagent Write-permission patterns** for `.claude/flux-gen-specs/**` and `.claude/agents/**` need explicit absolute-path forms (`Write(//home/mk/projects/Sylveste/.claude/flux-gen-specs/**)`) — the relative + glob patterns failed for subagents in practice. Bead `sylveste-o8wo` (P2) tracks the open question of *why*. Worth investigating upstream when there's bandwidth.

### Context

**Phase 1 of `sylveste-a4oj` is fully closed.** Closed beads: `.1` (MEMORY.md restructure), `.2` (content-address OUTPUT_DIR), `.3` (MAX_CONCURRENT=6 cap), `.5` (`/loop` 240s default), `.7` (canonical-witness designation), `.8` (SessionStart dirty-bit cache lib + gate). Plus the permission-fix sub-bead `sylveste-o8wo` shipped.

**Open under the epic:**
- `sylveste-a4oj.4` — MCP OAuth tool gating (P2, S, ~1kt/session) ← **directive**
- `sylveste-a4oj.6` — Stall-rescue (P2, S, reverted; reopened)
- `sylveste-a4oj.9` — Phase 2 bundle (P2, multi-finding)
- `sylveste-a4oj.10` — Phase 3 bundle (P3, infrastructure-class)
- `sylveste-a4oj.11` — Rule/Marginalia split for feedback files (P2, M, deferred from `.1`)
- `sylveste-a4oj.12` — Memory depth-tiered archiving (P3, M, deferred from `.1`)
- `sylveste-a4oj.13` — Wire `session-freshness-gate.sh` into SessionStart hooks (P2, S, deferred from `.8` for explicit user opt-in)

**Commits this session:**
- Sylveste monorepo: `ca999e9e` (subagent Write permissions, `o8wo`), `6c1bd1f3` (freshness lib + session gate + gen-skill-compact refactor, `.8`), `3b39f6a5` (multi-axis flux-review synthesis, `a4oj`)
- Interflux: `350deb6` (concurrency cap + run-isolation alignment, `.{2,3}`)
- Interpath: `8130049` (canonical-witness rule for artifact-gen, `.7`)

**New artifacts on disk (committed):**
- `docs/research/flux-review/sylveste-improvements-multi-axis/2026-05-04-synthesis.md` (329 lines) — the canonical synthesis driving Phase 1
- `docs/research/flux-drive/2026-05-04-target/` — 16 per-agent finding files + summary
- `scripts/lib-freshness.sh` (sourceable manifest pattern lib)
- `scripts/session-freshness-gate.sh` (SessionStart wrapper, opt-in via `a4oj.13`)
- `interverse/interflux/skills/flux-drive/phases/{launch.md, expansion.md}` updated with concurrency cap
- `interverse/interflux/skills/flux-review/phases/track-dispatch.md` updated with track-level cap
- `interverse/interpath/skills/artifact-gen/{SKILL.md, SKILL-compact.md, phases/{roadmap.md, vision.md}}` updated with canonical-witness rule

**User-memory writes (NOT in git):**
- `~/.claude/projects/-home-mk-projects-Sylveste/memory/MEMORY.md` — restructured stable→churn order (was 132 lines, now 128 after a4oj.5 entry). Active Projects + Active Brainstorms collapsed into single Project Index near the bottom.
- `~/.claude/projects/-home-mk-projects-Sylveste/memory/feedback_loop_interval_240s.md` — the rule for `/loop` 4m default + ScheduleWakeup never-300s guidance (`a4oj.5`).

**Permissions / settings:**
- Project `.claude/settings.json` now has explicit absolute-path Write allow rules for `.claude/{agents,flux-gen-specs}/**` and `docs/research/flux-{drive,research,review}/**`. Verified working via Haiku test subagent.
- `.gitignore` adds `.claude/session-state.json` (auto-generated by the freshness gate) and `!docs/research/flux-review/` (un-ignore for future syntheses).

**Process notes worth carrying forward:**
- The pre-commit hook (`bd prime` from PreCompact) auto-syncs `.beads/issues.jsonl` and can sweep adjacent untracked files into commits unintentionally. Stage deliberately; expect 1-2 extra files per commit from the hook.
- Concurrent-session activity (other agents editing other files) means `git push` may report "Everything up-to-date" because someone else's auto-push beat yours. Verify with `git log origin/main..HEAD` to see if commits are actually behind.
- The interflux + interpath repos are nested git repositories inside the Sylveste monorepo. `git status` from monorepo root won't show their drift; `cd` into the subrepo to see and commit.
- `bd backup sync` (the protocol's pre-push step) currently exits with help text — its Dolt destination at `/Users/sma/...` is misconfigured (macOS path on Linux box). The `.beads/push.sh` path via `bd-push-dolt` gate works fine; sync isn't strictly required.
