---
date: 2026-05-06
session: 478f131e
topic: thread A shipped + git wrapper root cause fixed
beads: [sylveste-8jx0, sylveste-qow6, sylveste-0usg, sylveste-t0sz, sylveste-xt0y, sylveste-9s3t, sylveste-rqmx, sylveste-itsc]
---

## Session Handoff — 2026-05-06 thread A shipped + git wrapper fixed

### Directive

> Your job is to act on the open lattice follow-ups. Pick **sylveste-t0sz** first (smallest, dissolves another of the 4 real collisions). Verify with `cd interverse/lattice && uv run python scripts/architecture_report.py --contracts 2>&1 | grep -A6 cross_plugin_collisions` — `setup` should drop after intership rename + lattice rescan.

Open beads (priority order):
- **sylveste-t0sz** (P3, open) — rename `intership:setup` → `intership:customize`. Single nested repo at `interverse/intership/`. Update `commands/setup.md` filename + frontmatter `name:`, bump version, push.
- **sylveste-xt0y** (P3, open) — lattice v0c.5: `FileContract` entity type (would dissolve interpath ↔ interwatch cycle in the lattice's view).
- **sylveste-rqmx** (P3, open) — lattice v0c.7: emit `unclassified_reason` from `_pillar_for_path` (currently returns silent `None`).
- **sylveste-dsbl** (F3, open per prior handoff) — scope already rewritten in notes.

Closed this session: sylveste-8jx0 (cycle resolution), sylveste-qow6 (collision triage), sylveste-0usg (lattice v0c.6 shipped), sylveste-9s3t (interblog non-pillar verdict), sylveste-itsc (git wrapper root-cause fix shipped).

Live lattice scan after v0c.6: 12 reported collisions → 4 real (research, scan, setup, status). research/scan are cross-domain accept; status self-resolves on next interscout cleanup; setup is t0sz.

### Dead Ends

- **`git reset --mixed HEAD` to repair lattice's stale index** — failed because HEAD's tree object itself was missing in `.git/objects`. Used `rm .git/index && git read-tree HEAD` instead.
- **First `rm .git/index && git read-tree HEAD` for lattice** — actually CORRUPTED the monorepo session index because the broken wrapper redirected the inner `read-tree` to write lattice's tree into the *monorepo's* `.git/index-<sid>`. Repeating the same operation now (with the fixed wrapper) is safe and is the right recovery path.
- **Redefining `git()` in the current shell to bypass the broken wrapper** — works for the *current* shell, but every Bash tool invocation starts a fresh `bash -c` that re-sources `$CLAUDE_ENV_FILE`, restoring the broken function. Had to patch the live session-env file directly.
- **Trying to commit interpath AGENTS.md without first rebuilding `.git/index`** — failed with `error: invalid object 100644 88c25b9d… for '.claude-plugin/plugin.json'`. Earlier index rebuild had partially failed under the broken wrapper. Re-running `rm .git/index && git read-tree HEAD` after the wrapper fix produced a clean index.
- **`env -u VAR command builtin`** — silently broken on this system. `env(1)` cannot exec a shell builtin. Use `( unset VAR; command builtin "$@" )` subshell instead.

### Context

- **Root cause for ALL "fatal: unable to read <hash>" corruption** in nested git repos was interlock's per-session git wrapper. Two latent bugs: (1) cwd-only path check missed nested .git/, so nested-repo `git status` discovered nested `.git/objects` but used the monorepo's session `GIT_INDEX_FILE`; (2) `env -u GIT_INDEX_FILE command git` was broken from day one but rarely hit because the else-branch only triggers outside the project root. Fix shipped in interlock 0.2.14 (`mistakeknot/interlock` HEAD). Live session env patched in place — no restart needed.

- **Smoking gun**: interpath and interwatch reported the SAME missing hash (`48adab42…`) because that hash was a tree in the monorepo's session index, not theirs. Two independent repos can't share a missing hash by accident.

- **Lattice repo path**: `interverse/lattice/` is its own git repo → `mistakeknot/interweave`. Same pattern for `interverse/{interpath,interwatch,interlock}/` → respective `mistakeknot/<name>`. Nested commits don't show in monorepo `git status`.

- **Live wrapper file**: `/home/mk/.claude/session-env/478f131e-4b80-427b-b5d7-fb4e79675375/sessionstart-hook-11.sh` — patched. Source: `interverse/interlock/hooks/session-start.sh`. Cache: `/home/mk/.claude/plugins/cache/interagency-marketplace/interlock/0.2.12/hooks/session-start.sh` — also patched.

- **interblog verdict** (sylveste-9s3t): non-pillar L3 app by design. The 6-pillar model is platform-shaped (Autarch is the *discipline* app, not a generic L3 bucket). Do NOT add a 7th pillar; the gap is intentional.

- **interpath ↔ interwatch verdict** (sylveste-8jx0): intentional sensor/generator pattern over `.interwatch/drift.json` published file contract. Both AGENTS.md files now carry "Architectural cycle (intentional)" notes — pushed in `mistakeknot/{interpath,interwatch}`.

- **bd flush gotcha**: `bd backup sync` does NOT flush local JSONL (it's for cloud Dolt backup). Use `bd export > .beads/issues.jsonl` before commits. Auto-flush every ~5 min, but force manual export before push cycles.

- **Concurrent agent activity throughout session** — F5/F6a sprint commits landed concurrently (b313acf0, 769cfc6b, 15f9d3fa, 42c69328, c107a7da, eeaee21a). Stage explicit paths only; check `git log -- <path>` after commit to verify the right ref.

- **Session index repair recipe** (if it happens again before everyone's session restarts on 0.2.14): `GIT_INDEX_FILE=/home/mk/projects/Sylveste/.git/index-<sid> command git -C /home/mk/projects/Sylveste read-tree HEAD`. For nested repos: `cd <nested>; rm .git/index; git read-tree HEAD`.

- **Triage doc**: `docs/research/2026-05-06-collision-triage.md` (verdicts on the 4 real collisions; references sylveste-0usg/t0sz).
