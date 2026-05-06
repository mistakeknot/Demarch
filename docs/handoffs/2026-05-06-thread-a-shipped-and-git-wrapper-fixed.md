---
date: 2026-05-06
session: 478f131e
topic: thread A complete, git wrapper fixed, lattice v0c.{1,5,6,7} shipped
beads: [sylveste-8jx0, sylveste-qow6, sylveste-0usg, sylveste-t0sz, sylveste-xt0y, sylveste-9s3t, sylveste-rqmx, sylveste-itsc, sylveste-go0q, sylveste-dsbl]
---

## Session Handoff — 2026-05-06 thread A complete + lattice v0c.{1,5,6,7} shipped

### Directive

> Your job is to either (a) tackle one of the remaining lattice v0c items — **v0c.4 periodic re-harvest hook** is the smallest, **v0c.2 MCP tool granularity** is the most useful (needs `tools/list` introspection), **v0c.3 Service entity type** captures long-running daemons (intermux, intermap-mcp, interop) — or (b) pick from the P0 queue (`bd list --status open --priority 0` shows ~15 epics; Track B6 routing / Auraken→Hermes pivot / Mythos launch readiness are warm). The Thread A + lattice v0c.{1,5,6,7} cluster is fully closed.

If picking v0c.4 first (smallest):
- Need a way to keep the lattice fresh against the live tree without a manual rerun.
- Options: a SessionStart hook in the lattice plugin, a post-commit hook in the monorepo, or a daemon mode for `architecture_report.py`.
- File a new bead `lattice v0c.4: periodic re-harvest hook`.

If picking v0c.2 (highest signal): tool-level MCP resolution requires booting each MCP server briefly to call `tools/list`. Cache the result per-session with the server binary's mtime as cache key. Connector site: `interverse/lattice/src/lattice/connectors/_arch_consumers.py` (current `_resolve_reference` resolves only to mcp_server, drops the tool name).

Open beads (priority order):
- **sylveste-dsbl** (P1, open) — F3 meta-tracker. Now functions as parking lot for per-consumer DDL metadata that surfaces during F4 (`sylveste-t2cs`); not directly actionable until F4 work resumes. Leave open.
- 15 P0 epics from other tracks. None were in this handoff's Thread A scope.

Closed today (10 beads): sylveste-{8jx0 cycle, qow6 collision triage, 0usg v0c.6, 9s3t interblog verdict, itsc git wrapper, t0sz intership rename, rqmx v0c.7 unclassified_reason, xt0y v0c.5 file_contract, go0q v0c.1 unqualified slash}.

Live lattice scan (`cd interverse/lattice && uv run python scripts/architecture_report.py --contracts --leverage`) after the v0c shipments:
- `cross_plugin_collisions`: 4 → 3 (research+scan cross-domain accept, status self-resolves)
- `unclassified plugins`: 1 — `architecture:plugin/interblog — non_pillar_app` (intentional)
- `file_contracts`: 13 detected, canonical `.interwatch/drift.json` (interwatch writes, interpath reads)
- `consumes` edges: 114 → 137 (+23 from v0c.1 + v0c.6 stem fallback combined)
- Top inbound: `/clavain:clavain-status` 3, `/interwatch:watch` 3, `/clavain:brainstorm` 2, plus a long tail at 2

### Dead Ends

- **v0c.1's "5-10x consume edge growth" prediction overconfident** — actual lift +20% (114 → 137). Most plugin doc bare `/X` mentions are markdown anchors, code paths, or filtered by the `(?![:/])` lookahead; the hard no-guessing rule on ambiguity also drops some. Conservative outcome is the right one — false-positive consumes would distort the leverage signal more than missing edges hurt. Don't chase the original prediction; the current rate is correct.
- **v0c.6 silently broke 9 consume edges** — making the contract identity the frontmatter `name:` field meant prose like `/clavain:status` (file-stem form, used in 5 docs) stopped resolving against contracts now stored as `clavain-status`. Fixed in v0c.1's commit by adding a `command_path`/`skill_dir` suffix-match fallback. Lesson: any change to identity semantics needs a back-compat lookup path until prose catches up.
- **`Crosswalk.list_entities`** — does not exist. Use `crosswalk.get(canonical_id)` for direct lookup, or `CrossPluginCollisionsTemplate().execute(query_context)` for aggregate queries. The existing v0b1 tests use `crosswalk.get(...)` — match that style for new connector tests.
- **`env -u VAR command builtin`** — silently broken on this system. `env(1)` cannot exec a shell builtin. Use `( unset VAR; command builtin "$@" )` subshell. Fixed in interlock 0.2.14 (`mistakeknot/interlock` `44a51dd`); regression test asserts on the subshell form.
- **`git reset --mixed HEAD`** to repair lattice's stale index — failed because HEAD's tree object itself was missing in `.git/objects`. Use `rm .git/index && git read-tree HEAD` instead. After interlock 0.2.14 the corruption no longer recurs.
- **First `rm .git/index && git read-tree HEAD` for lattice (under broken wrapper)** — actually CORRUPTED the monorepo session index because the broken wrapper redirected the inner `read-tree` to write lattice's tree into the *monorepo's* `.git/index-<sid>`. Repeating the same operation now (with the fixed wrapper) is safe.
- **Redefining `git()` in the current shell to bypass the broken wrapper** — works for the *current* shell, but every Bash tool invocation starts a fresh `bash -c` that re-sources `$CLAUDE_ENV_FILE`, restoring the broken function. Patch the live session-env file directly: `/home/mk/.claude/session-env/<sid>/sessionstart-hook-NN.sh`.
- **`git add <explicit-files>` is NOT sufficient defense against bundle damage** — concurrent agents' staged deletions/modifications carry through pre-commit hooks. Twice this session I bundled their work (`baf79406` and `4145f54c`); recovery commits were `15f9d3fa` and `031c83b6`. Defensive practice: `git diff --cached --name-only` before EVERY commit, verify the staged set matches the intended set. Use `git reset HEAD` first if `git status` shows mixed `M`/`D`/`A` from someone else's bundled rebase, then stage explicit paths.
- **Updating findings doc with interblog Resolution section** — landed once, then a concurrent agent reverted it (system reminder framed as intentional user/linter modification). Verdict captured durably in the bead trail (`sylveste-9s3t` close note) and in the architecture report's `unclassified_reason: non_pillar_app` annotation. Don't re-add the doc section without checking with the user.
- **Inferring file_contract reads/writes from verb proximity** — designed but not implemented. Direct heuristic ("plugin X writes `.X/<file>`, others read it") is more reliable, simpler, and catches the canonical case cleanly.

### Context

- **Root cause for nested-repo "fatal: unable to read <hash>" corruption**: interlock's per-session git wrapper had a cwd-only path check that missed nested `.git/`. Nested-repo `git status` discovered the nested repo's object store but used the monorepo's session `GIT_INDEX_FILE`. Fixed in interlock 0.2.14 with walk-up nested-repo detection. Live session env patched in place at `/home/mk/.claude/session-env/<sid>/sessionstart-hook-NN.sh`.

- **Smoking gun**: interpath and interwatch reported the SAME missing hash (`48adab42…`) because that hash was a tree in the *monorepo's* session index. Two independent repos can't share a missing hash by accident.

- **Repair recipe** (for any session still on broken wrapper):
  - Monorepo: `GIT_INDEX_FILE=/home/mk/projects/Sylveste/.git/index-<sid> command git -C /home/mk/projects/Sylveste read-tree HEAD`
  - Nested: `cd <nested>; rm .git/index; git read-tree HEAD`

- **Nested repo paths and their remotes**:
  - `interverse/lattice/` → `mistakeknot/interweave`
  - `interverse/interpath/` → `mistakeknot/interpath`
  - `interverse/interwatch/` → `mistakeknot/interwatch`
  - `interverse/interlock/` → `mistakeknot/interlock`
  - `interverse/intership/` → `mistakeknot/intership`
  Nested commits don't show in monorepo `git status`. Push each separately.

- **Lattice circular_dependencies template walks `consumes` edges only** — it does NOT walk the new `writes`/`reads` edges file_contracts use. So file_contracts don't introduce new cycles. The interpath ↔ interwatch consumes cycle in the leverage report is from prose cross-references in their AGENTS.md docs (intentional, sensor/generator pattern). The drift.json relationship is dissolved structurally by v0c.5 file_contracts on a separate axis. Both representations are correct facets of the same architectural reality.

- **interpath ↔ interwatch verdict** (sylveste-8jx0): intentional sensor/generator pattern over `.interwatch/drift.json` published file contract. After v0c.5 the file contract is a first-class entity (writer=interwatch, reader=interpath).

- **interblog verdict** (sylveste-9s3t): non-pillar L3 app by design. Architecture report annotates as `unclassified_reason: non_pillar_app`. Do NOT add a 7th pillar.

- **Collision triage verdicts** (`docs/research/2026-05-06-collision-triage.md`):
  - `/research`, `/scan` — accept as cross-domain verb sharing
  - `/status` — self-resolving via existing `interscout` deprecation
  - `/setup` — DONE (intership renamed to `/intership:customize`, mistakeknot/intership 0.3.3)

- **v0c.1 unqualified slash resolution precedence** (committed in `mistakeknot/interweave` `8895015`):
  1. Same plugin (a plugin's `/foo` is unambiguous)
  2. clavain (workflow frontend, owns most platform-wide commands)
  3. Unique cross-plugin match
  4. Ambiguous → unresolved (no guessing). Plugin's `unresolved_consumes` property collects these for finding-aid review.

- **`bd backup sync` ≠ JSONL flush**. Use `bd export > .beads/issues.jsonl` before commits.

- **`docs/handoffs/latest.md` symlink thrashes under concurrent agents** — each session's `/clavain:handoff` points it at their own handoff. Reading the handoff file directly is more reliable than following the symlink.

- **Concurrent agent activity throughout session** — F5/F6a/3xl3 sprint commits landed concurrently. Defensive pattern: `git reset HEAD` before staging, then `git add <explicit-paths>`, then `git diff --cached --name-only` to verify before commit.

- **Heuristic-detected file_contracts in live monorepo**: `.clavain/interspect/{confidence.json, delegation-calibration.json, interspect.db, overlays/, protected-paths.json, routing-calibration.json}` (clavain owner), `.clavain/verdicts/` (clavain), `.interlore/proposals.yaml` (interlore), `.interspect/interspect.db` (interspect), `.interwatch/{drift.json, project.yaml, watchables.yaml, scan.sh}` (interwatch).
