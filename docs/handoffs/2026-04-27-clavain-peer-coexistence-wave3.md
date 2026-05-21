---
date: 2026-04-27
session: 9d62dc8c
topic: clavain peer-coexistence Wave 3 handoff
beads:
  - sylveste-4ct0  # epic, in_progress, sprint=true, phase=executing
  - sylveste-am1d  # F5 closed (AGENTS.md softening)
  - sylveste-gg3e  # F1 closed (agent-rig.json reclassification)
  - sylveste-3tm8  # F2 open — modpack-install.sh (NEXT)
  - sylveste-w9ys  # F3 open — bridge skills
  - sylveste-0i24  # F4 open — /clavain:peers viewer
  - sylveste-k3f7  # F6 open — telemetry hook
  - sylveste-fj1w  # B′ follow-up (P3, gated on F6 telemetry)
  - sylveste-yofd  # C′ follow-up (P4, gated on B′)
---

## Session Handoff — 2026-04-27 Clavain peer-coexistence (mid-sprint, Waves 3–5 pending)

### Directive
> Your job is to finish Sprint sylveste-4ct0 from Wave 3. Start by reading `/home/mk/projects/Sylveste/docs/plans/2026-04-27-clavain-peer-coexistence-A.md` Tasks 3, 4, 6, 5, 8 (in that order — F2 first, then F3+F6 parallel-able, then F4 once F2 lands, then verify). Verify each task with `bash /home/mk/projects/Sylveste/os/Clavain/scripts/test-peer-coexistence.sh` (currently F1.* PASS, F2-F6 FAIL — that's expected RED state). When all tests PASS, run sprint Steps 6 (Test & Verify), 7 (Quality Gates), 8 (Resolve), 9 (Reflect), 10 (Ship) per `/clavain:sprint` preamble. Push both repos at end (Sylveste root + os/Clavain) and publish Clavain plugin per `os/Clavain/AGENTS.md` Release workflow.

- **Highest-risk remaining task**: F2 (sylveste-3tm8) — `os/Clavain/scripts/modpack-install.sh` has 6 named edit sites (plan Task 3 Step 1). Use the F2 acceptance tests in the harness as exit criteria.
- **F4 dep**: task-5 needs both task-2 (F1, done) AND task-3 (F2) — manifest enforces this. Don't start F4 until F2's `--category=peers` works.
- **Beads in progress to claim**: `bd update sylveste-3tm8 --status in_progress` before starting F2.
- **Pre-launch project**: per memory, no live-user risk on reversible ops; auto-proceed allowed for low-risk steps in vetted sprint flow.

### Dead Ends
- Initial scope was C′ (full rig manager: profiles, lockfile, per-skill priorities, peers.yaml registry, `clavain rig` CLI; 1.5–2 weeks). Brainstorm review (1 P0, 7 P1, 3/3 reviewer convergence) showed the multi-rig assumption was unevidenced and 6 of 8 C′ pieces weren't load-bearing. Down-scoped to A (~1–2 days). Mod-manager patterns (MO2/LOOT/Vortex/Wabbajack/Paradox/Irony) preserved as design references in B′/C′ follow-up beads.
- Original plan had per-task harness writes (tasks 3/5/6 each appending) → fixed to single-owner (task-1 writes complete harness) after plan review caught Wave 3 write contention.
- Original F2 design used `--apply` flag → dropped after PRD review showed it inverts the existing dry-run-by-default contract. Now `process_peers()` is just report-only; `process_category("hard_conflicts")` keeps existing semantics.
- Initial F1 commit landed and immediately got broken by Clavain's pre-commit hook `scripts/gen-rig-sync.py` which still read `plugins.conflicts` (now null) and emptied the disable-conflicts blocks in setup.md/doctor.md. Fixed in commit `c230e23`. **5th** downstream consumer that PRD/plan review missed.

### Context
- `/home/mk/projects/Sylveste/os/Clavain` is its own git repo (`git@github.com:mistakeknot/Clavain.git`) — Sylveste root has `os/` gitignored. Implementation commits land in Clavain repo; only `AGENTS.md` softening + planning artifacts are in Sylveste root. **Cd-aware bd**: `bd close` from `os/Clavain` fails (no .beads context) — always run beads commands from Sylveste root.
- Clavain has a pre-commit hook (`scripts/gen-rig-sync.py`) that auto-regenerates `setup.md` and `doctor.md` marker sections from `agent-rig.json`. ANY `agent-rig.json` schema change must update the generator first. The pre-commit hook also runs even when target files aren't staged (it auto-stages regenerated content under `Executed-By: 9d62dc8c` footer in commit message — that's normal).
- Test harness at `/home/mk/projects/Sylveste/os/Clavain/scripts/test-peer-coexistence.sh` is the single source of truth for acceptance. F1.1–F1.6 currently PASS; F2–F6 FAIL by design (RED state, expected before implementation).
- Sprint phase tracking is degraded: `enforce-gate: skipped — no ic run for bead` on every advance-phase. Not a blocker — beads state is canonical, IC run integration would just give richer kernel telemetry.
- 4 unpushed commits: 1 in Sylveste root (planning artifacts + AGENTS.md), 3 in os/Clavain (harness, F1, gen-rig-sync fix). Push only after sprint Step 10.
- Brainstorm/PRD/plan/review artifacts under `docs/brainstorms/`, `docs/prds/`, `docs/plans/`, `docs/research/flux-drive/2026-04-27-clavain-peer-coexistence-*/`. SYNTHESIS.md is the headline review for brainstorm; fd-architecture.md exists for both prd/ and plan/ subdirs.
- F4's `/clavain:peers` is **Claude Code only** per PRD revision; Codex parity is explicit non-goal. F1 dropped GSD marketplace identifier confirmation — using `gsd-plugin@jnuyens` as placeholder; first user report can correct.
- F6 hook registers in `os/Clavain/hooks/hooks.json` (NOT `plugin.json`) under existing SessionStart `startup|resume|clear|compact` matcher. Plan review caught this before implementation.
