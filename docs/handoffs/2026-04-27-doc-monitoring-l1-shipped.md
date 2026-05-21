---
date: 2026-04-27
session: 01af7532
topic: doc-monitoring L1 shipped
beads: [sylveste-wdf2, sylveste-wdf2.1, sylveste-wdf2.2, sylveste-wdf2.3, sylveste-wdf2.4]
---

## Session Handoff — 2026-04-27 doc-monitoring L1 shipped

### Directive
> Your job is to design and implement L2 of the doc-monitoring automation epic (sylveste-wdf2.2): a PreToolUse hook that surfaces drift on doc access, with auto-fire on Certain confidence (24h cooldown, daily budget cap, no-op refresh detection). Start by reading sylveste-wdf2 and sylveste-wdf2.2 for the deferred decisions and ship constraints, then `cat .interwatch/drift.json` to see real drift state being maintained by the L1 hook. L1 is shipped; you can build on real-world drift signals.
- Beads: sylveste-wdf2 (P2 epic, OPEN); sylveste-wdf2.1 (P2, CLOSED — L1 shipped); sylveste-wdf2.2 (P2, OPEN — your target); sylveste-wdf2.3 (P3, OPEN — L3+L4 schedule routines, depends on L2); sylveste-wdf2.4 (P4, deferred — L5 substrate-independent replay)
- Plugin shipped: interwatch@0.4.2 (marketplace + CC marketplace cache synced)
- Hook live on Sylveste at `.beads/hooks/post-commit` and `.beads/hooks/post-merge`. Verify by `stat -c '%y' /home/mk/projects/Sylveste/.interwatch/drift.json` after any commit — should refresh within 2s.

### Dead Ends
- `&` + `disown` for backgrounding hook scan — git SIGHUPs its process group on exit, killing the scan before it completes. Fixed with `setsid bash hook-runner.sh`.
- Installing hooks to `.git/hooks/` — Sylveste has `core.hooksPath=.beads/hooks` (bd-managed). Git ignores `.git/hooks/` entirely. Installer must read `git config --get core.hooksPath`.
- Hardcoded `/home/mk/...` path in hook body — `.beads/hooks/` is tracked in git, would leak machine paths to other developers. Use runtime resolver (`$INTERWATCH_HOOK_RUNNER` → repo-relative → plugin cache → silent skip).
- Synthetic tmpdir round-trip tests — passed all four hook bug classes by accident (empty watchables config ran fast enough to evade the SIGHUP race; tmpdir doesn't have `core.hooksPath` set; tmpdir hooks aren't tracked). Real-commit-on-real-config repo is the only environment that surfaces all four.
- `ic publish 0.4.X` after manual plugin.json bump — fails with "already at target version". Workaround: `ic publish doctor --fix` syncs marketplace AND CC marketplace cache.

### Context
- L1 contract: pure-Python `interwatch-scan.py --save-state` runs in setsid'd background, ~0.3s on Sylveste, never blocks commit. Errors land in `.interwatch/hook.log` (currently empty — clean runs). Downstream layers compose through `.interwatch/drift.json`.
- Decision summary on epic: hybrid trigger model decomposed by cost class — cheap signals event-driven (L1 git hook, shipped), expensive refresh on-access (L2) OR scheduled floor (L3), audit monthly (L4), substrate-independent replay deferred (L5). Auto-fire on Certain confidence; High surfaces note only.
- Goodhart guardrails for L2 (must implement before auto-fire ships): no-op refresh detection (skip `--record-refresh` if generator output semantically identical, decay weights instead); 24h cooldown per doc; per-day auto-refresh budget cap (default 5, configurable in `.interwatch/project.yaml`).
- Three test-environment classes are now needed: synthetic round-trip (catches symbol bugs), real-commit tmpdir (catches logic bugs around exit codes), real-commit on real-config repo (catches subprocess-lifecycle and distribution bugs). See `~/.claude/projects/-home-mk-projects-Sylveste/memory/universal-gotchas.md` 2026-04-27 entries.
- Substrate-independence finding from yesterday's flux-review (`docs/brainstorms/2026-04-26-flux-explore-sylveste-flywheel.md`) reframes test design at unit-test scale — same evaluator + same conditions produce false confidence. L5 (sylveste-wdf2.4) extends this principle to monitor-validation; design with that direction in mind.
- Concurrent-agent gotcha hit during ship: peer-coexistence work (`sylveste-4ct0`) committed during my close-bead commit, causing `cannot lock ref 'HEAD'`. Both agents share Dolt — the close persisted because the other agent's commit picked up my JSONL update. Watch for this when multiple sessions are active.
- Key paths: `interverse/interwatch/scripts/{install-git-hooks,uninstall-git-hooks,hook-runner,interwatch-scan.py}.sh`; `interverse/interwatch/commands/install-hooks.md`; `.beads/hooks/{post-commit,post-merge}` (committed, portable body); `.interwatch/{drift,last-scan}.json` (gitignored except watchables.yaml).
