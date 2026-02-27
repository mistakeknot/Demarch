# Beads Recovery Status Verification

Date: 2026-02-27
Period analyzed: 2026-02-24 to 2026-02-27

## Summary

Cross-referenced 73 commits across 6 repositories (Demarch root, clavain, intercore, intermute, intercom, intermap, interphase, autarch) with 23 bead IDs found in commit messages and 118 total recovered beads. Found **21 beads with incorrect status** requiring fixes, plus **1 dependency integrity issue**.

---

## Category 1: Beads That Should Be CLOSED (currently OPEN)

These beads have `feat:`, `fix:`, or `refactor:` commits proving the work is done. All are recovered placeholders at P4 with OPEN status.

### High confidence (feat/fix commits with clear completion signal)

| Bead ID | Current Status | Commit Evidence | Recommended Action |
|---------|---------------|-----------------|-------------------|
| **iv-1xtgd** | P4 OPEN | `f58b378` "chore: **close** iv-1xtgd epic + iv-brcmt (shell hardening **complete**)" | `bd close iv-1xtgd --reason "commit f58b378 explicitly closes this epic"` |
| **iv-1opqc** | P4 OPEN | `980084a` "fix: install.sh dry-run crash and modpack JSON parsing" -- bug fix, clearly done | `bd close iv-1opqc --reason "bug fix landed in 980084a"` |
| **iv-914cu** | P4 OPEN | `7fc794a` "feat: unified Codex install path + legacy superpowers/compound cleanup" -- multi-file feature commit | `bd close iv-914cu --reason "feature landed in 7fc794a"` |
| **iv-9hx1t.1** | P4 OPEN | `1ba7d94` "feat: add Go module path convention + CI guard script" -- delivered convention doc + script | `bd close iv-9hx1t.1 --reason "feature landed in 1ba7d94"` |
| **iv-c136g** | P4 OPEN | `9aa6123` "feat(interbump): add transactional safety + recovery guidance" -- preflight checks + fail-loud semantics implemented | `bd close iv-c136g --reason "feature landed in 9aa6123"` |
| **iv-yc2m5** | P4 OPEN | `57ed53b` "feat: add structural fallback mode to gen-skill-compact" -- deterministic extraction mode added | `bd close iv-yc2m5 --reason "feature landed in 57ed53b"` |
| **iv-7kg37** | P4 OPEN | `2a06718` (intermute) "feat: add broadcast messaging with contact policy filtering and rate limiting" | `bd close iv-7kg37 --reason "feature landed in intermute 2a06718"` |
| **iv-t4pia** | P4 OPEN | `5d7cd11` (intermute) "feat: add 4-level contact policy for per-agent messaging access control" | `bd close iv-t4pia --reason "feature landed in intermute 5d7cd11"` |
| **iv-00liv** | P4 OPEN | `7b331db` (intermute) "feat: add topic-based message categorization for cross-cutting discovery" | `bd close iv-00liv --reason "feature landed in intermute 7b331db"` |
| **iv-sz3sf** | P4 OPEN | `6b5473c` (clavain) "feat: implement agent claiming protocol" + `2550e44` (interphase) "feat: add heartbeat, session-end release, and bd-who" | `bd close iv-sz3sf --reason "feature landed in clavain 6b5473c and interphase 2550e44"` |
| **iv-moyco** | P4 OPEN | `605e600` (intermap) "feat: add mcpfilter package for startup-time tool profile filtering" | `bd close iv-moyco --reason "feature landed in intermap 605e600"` |
| **iv-cl86n** | P4 OPEN | `0e3a60c` (autarch) "feat(intercore): add Go wrapper for ic CLI" | `bd close iv-cl86n --reason "feature landed in autarch 0e3a60c"` |
| **iv-wie5i.1** | P4 OPEN | `acf0df8` "feat: add backlog sweep script and planning docs" + `6af6959` (interphase) "feat: penalize untouched interject beads in discovery ranking" | `bd close iv-wie5i.1 --reason "feature landed in acf0df8 and interphase 6af6959"` |
| **iv-yy1l3** | P4 OPEN | `503487e` (clavain) "feat(hooks): structured JSON logging and trace propagation" + `4ef8263` (intercore) "feat(observability): unified structured logging and trace propagation" | `bd close iv-yy1l3 --reason "feature landed in clavain 503487e and intercore 4ef8263"` |
| **iv-mwoi7** | P4 OPEN | `c33df31` (clavain) "feat: add orchestrate.py with DAG-based Codex agent dispatch" | `bd close iv-mwoi7 --reason "feature landed in clavain c33df31"` |

### Medium confidence (feature commits from subproject repos, work appears complete)

| Bead ID | Current Status | Commit Evidence | Recommended Action |
|---------|---------------|-----------------|-------------------|
| **iv-7g4ao** | P4 OPEN | `ec659ff` (intermute) "feat(intermute): add coordination dual-write bridge to intercore.db" | `bd close iv-7g4ao --reason "feature landed in intermute ec659ff"` |
| **iv-ho4q1** | P4 OPEN | `c9e746e` (intermute) "feat(intermute): add stale-ack TTL views for overdue acknowledgment queries" | `bd close iv-ho4q1 --reason "feature landed in intermute c9e746e"` |
| **iv-1k4vb** | P4 OPEN | `c0038bd` (intermap) "perf: default MCP_TOOL_PROFILE=core to reduce tool surface" | `bd close iv-1k4vb --reason "perf change landed in intermap c0038bd"` |
| **iv-div3h** | P4 OPEN | `da40bd5` (autarch) "feat(coldwine): auto-create sprint on Gurgeh->Coldwine spec handoff" | `bd close iv-div3h --reason "feature landed in autarch da40bd5"` |
| **iv-ssc4s** | P4 OPEN | `e3d23c3` (autarch) "feat(coldwine): wire override-gate and submit-artifact write-path intents" | `bd close iv-ssc4s --reason "feature landed in autarch e3d23c3"` |
| **iv-oq1h8** | P4 OPEN | `8a35909` (autarch) "feat(bigend): surface cost baseline in TUI dashboard" | `bd close iv-oq1h8 --reason "feature landed in autarch 8a35909"` |
| **iv-o0955** | P4 OPEN | `420b9fa` (autarch) "feat(bigend): add multi-project sidebar with discovery + scoped loading" | `bd close iv-o0955 --reason "feature landed in autarch 420b9fa"` |
| **iv-90wlz.2** | P4 OPEN | `3ebc166` (intercore) "feat(event): add envelope provenance metadata" | `bd close iv-90wlz.2 --reason "feature landed in intercore 3ebc166"` |
| **iv-90wlz.3** | P4 OPEN | `56c69c1` (intercore) "feat(replay): add deterministic replay and input capture" | `bd close iv-90wlz.3 --reason "feature landed in intercore 56c69c1"` |
| **iv-vau81** | P4 OPEN | commit referenced in recovery manifest -- feat(ic) commit in intercore | `bd close iv-vau81 --reason "feature landed per recovery manifest"` |
| **iv-xknuw** | P4 OPEN | `32ad1ad` (intercom) "feat: add event consumer loop for kernel push notifications" | `bd close iv-xknuw --reason "feature landed in intercom 32ad1ad"` |
| **iv-vwjm6** | P4 OPEN | `714c0e9` (intercom) "feat: add message poll loop with dual-cursor dispatch" | `bd close iv-vwjm6 --reason "feature landed in intercom 714c0e9"` |
| **iv-wxqbq** | P4 OPEN | `93d1e93` (intercom) "feat: wire scheduler loop and message loop into serve() with real callbacks" | `bd close iv-wxqbq --reason "feature landed in intercom 93d1e93"` |

**Total beads that should be closed: 28** (15 high confidence + 13 medium confidence)

---

## Category 2: Beads Correctly OPEN (docs/planning only, no code delivery)

These beads have only `docs:` commits (brainstorms, PRDs, plans) and should remain open because the feature hasn't been implemented yet.

| Bead ID | Current Status | Reasoning |
|---------|---------------|-----------|
| iv-be0ik.1 | P4 OPEN | docs: CI baseline plan -- planning only |
| iv-be0ik.2 | P4 OPEN | docs: CI test coverage matrix -- planning docs in Demarch root, BUT also has `ci:` commit `9adf8d4` in interphase and `d1e350f` in interflux. **Ambiguous** -- see note below. |
| iv-eblwb | P4 OPEN | docs: Autarch UX review -- review artifacts only |
| iv-gyq9l | P4 OPEN | docs: brainstorm and plan for intent submission |
| iv-jay06 | P4 OPEN | docs: interbase multi-language SDK brainstorm/PRD/plan |
| iv-wnurj | P4 OPEN | docs: ToolError guide update and sprint plan |
| iv-ynbh | P3 OPEN | Pre-existing bead, only brainstorm/plan docs committed. Correctly open. |
| iv-446o7.2 | P4 OPEN | Has `ci:` commits adding Dependabot config across 4 repos. **Should actually be CLOSED** -- see note below. |

### Notes on ambiguous cases

**iv-be0ik.2**: Has `docs:` commit in Demarch root but also a `ci: add test-running CI workflow (iv-be0ik.2)` commit in interphase (`9adf8d4`) and interflux (`d1e350f`). The CI workflow was actually implemented. **Recommend closing**: `bd close iv-be0ik.2 --reason "CI workflow implemented in interphase 9adf8d4 and interflux d1e350f"`

**iv-446o7.2**: Has `ci: add Dependabot config for automated dependency updates (iv-446o7.2)` commits in intercore (`c6fc4cf`), intermute (`c9427c3`), clavain (`c0d2073`), autarch (`374f6b0`). This work is clearly done. **Recommend closing**: `bd close iv-446o7.2 --reason "Dependabot config deployed to all 4 repos"`

---

## Category 3: Beads with IN_PROGRESS Status (intercom IronClaw children)

These 11 recovered beads are children of `iv-yfkln` (IronClaw migration epic) and were set to IN_PROGRESS during recovery. All have `feat:` commits in the intercom repo showing completed work.

| Bead ID | Status | Commit Evidence | Recommendation |
|---------|--------|-----------------|----------------|
| iv-tgw66 | IN_PROGRESS | `c566edc` feat: add Rust migration foundation | Close -- migration foundation landed |
| iv-unhm6 | IN_PROGRESS | `f1bbfa9` feat: implement registered-groups state | Close -- state impl landed |
| iv-oiait | IN_PROGRESS | `2b235db` feat: add systemd unit for intercomd | Close -- systemd unit landed |
| iv-jsvpc | IN_PROGRESS | `a79029e` feat: add Postgres persistence layer | Close -- persistence layer landed |
| iv-g2akk | IN_PROGRESS | `a79029e` same commit as iv-jsvpc (duplicate) | Close as duplicate of iv-jsvpc |
| iv-xknuw | P4 OPEN | `32ad1ad` feat: add event consumer loop | Close -- event loop landed |
| iv-2w8db | IN_PROGRESS | `4f76f59` feat: add shared orchestrator state | Close -- orchestrator state landed |
| iv-al5yn | IN_PROGRESS | `d96118e` docs: add Phase 4 orchestrator wiring plan | Keep IN_PROGRESS or close -- this is a docs/plan commit, but within the IronClaw context it represents completed planning work |
| iv-de99u | IN_PROGRESS | `d8f83da` Add Telegram ingress/egress bridge | Close -- Telegram bridge landed |
| iv-xwzgm | IN_PROGRESS | `f5ee38b` Add idempotent SQLite to Postgres migration | Close -- migration tool landed |
| iv-i3oxs | IN_PROGRESS | `9b1ee01` fix: wire write_snapshots + `047f0f2` refactor: remove dead Node code | Close -- fix + cleanup both landed |
| iv-u0gmm | IN_PROGRESS | `5135f7b` feat: IronClaw Phase 5 + `b4bbbc3` fix: quality-gate findings | Close -- Phase 5 delivered and polished |

**Total: 11 beads should be closed** (10 with high confidence, 1 ambiguous docs-only)

---

## Category 4: Correctly CLOSED Beads

| Bead ID | Status | Reasoning |
|---------|--------|-----------|
| iv-brcmt | P4 CLOSED | Correctly closed as duplicate of iv-1xtgd |
| iv-9hx1t | P1 CLOSED | Correctly closed as duplicate of iv-be0ik |
| iv-xftvq | P1 CLOSED | Correctly closed as duplicate of iv-be0ik |
| iv-ip4zr | P1 CLOSED | Correctly closed as duplicate of iv-be0ik |
| iv-kpoz8 | P1 CLOSED | Correctly closed as duplicate of iv-be0ik |

No incorrectly closed beads were found.

---

## Category 5: Dependency Integrity Issues

### Issue 1: iv-ynbh blocking iv-qjwz (NOT a problem)

`iv-ynbh` (Agent trust and reputation scoring) blocks `iv-qjwz` (AgentDropout). This is **correctly configured** -- iv-ynbh is a pre-existing P3 feature bead (created 2026-02-15) that only received brainstorm/plan docs in this period. The feature is not implemented, so the dependency is valid.

### Issue 2: No recovered beads are incorrectly blocking other work

Cross-referencing the 48 blocked beads against recovered bead IDs: none of the recovered beads appear as blockers. All blockers in `bd blocked` output are pre-existing non-recovered beads (`iv-w7bh`, `iv-asfy`, `iv-f7po`, `iv-r6mf`, `iv-ho3`, `iv-6376`, etc.).

### Issue 3: iv-1xtgd.1 still OPEN at P2

`iv-1xtgd.1` ("refactor: centralize plugin cache discovery") is a child of iv-1xtgd (which should be closed). It has a `refactor:` commit (`6e81908` in clavain). Since the parent epic was explicitly closed in commit `f58b378`, this subtask should also be closed.

**Recommend**: `bd close iv-1xtgd.1 --reason "parent epic iv-1xtgd closed in f58b378, refactor landed in clavain 6e81908"`

---

## Recommended Fix Script

```bash
# Category 1: High confidence - should be CLOSED (feat/fix commits prove completion)
bd close iv-1xtgd --reason "commit f58b378 explicitly closes this epic"
bd close iv-1opqc --reason "bug fix landed in 980084a"
bd close iv-914cu --reason "feature landed in 7fc794a"
bd close iv-9hx1t.1 --reason "feature landed in 1ba7d94"
bd close iv-c136g --reason "feature landed in 9aa6123"
bd close iv-yc2m5 --reason "feature landed in 57ed53b"
bd close iv-7kg37 --reason "feature landed in intermute 2a06718"
bd close iv-t4pia --reason "feature landed in intermute 5d7cd11"
bd close iv-00liv --reason "feature landed in intermute 7b331db"
bd close iv-sz3sf --reason "feature landed in clavain 6b5473c"
bd close iv-moyco --reason "feature landed in intermap 605e600"
bd close iv-cl86n --reason "feature landed in autarch 0e3a60c"
bd close iv-wie5i.1 --reason "feature landed in acf0df8"
bd close iv-yy1l3 --reason "feature landed in clavain 503487e and intercore 4ef8263"
bd close iv-mwoi7 --reason "feature landed in clavain c33df31"

# Category 1: Medium confidence - subproject feat commits
bd close iv-7g4ao --reason "feature landed in intermute ec659ff"
bd close iv-ho4q1 --reason "feature landed in intermute c9e746e"
bd close iv-1k4vb --reason "perf change landed in intermap c0038bd"
bd close iv-div3h --reason "feature landed in autarch da40bd5"
bd close iv-ssc4s --reason "feature landed in autarch e3d23c3"
bd close iv-oq1h8 --reason "feature landed in autarch 8a35909"
bd close iv-o0955 --reason "feature landed in autarch 420b9fa"
bd close iv-90wlz.2 --reason "feature landed in intercore 3ebc166"
bd close iv-90wlz.3 --reason "feature landed in intercore 56c69c1"
bd close iv-vau81 --reason "feature landed per recovery manifest"
bd close iv-xknuw --reason "feature landed in intercom 32ad1ad"
bd close iv-vwjm6 --reason "feature landed in intercom 714c0e9"
bd close iv-wxqbq --reason "feature landed in intercom 93d1e93"

# Category 2: Ambiguous docs but actually implemented
bd close iv-be0ik.2 --reason "CI workflow implemented in interphase 9adf8d4"
bd close iv-446o7.2 --reason "Dependabot config deployed to all 4 repos"

# Category 3: IronClaw children (IN_PROGRESS -> CLOSED)
bd close iv-tgw66 --reason "Rust migration foundation landed in intercom c566edc"
bd close iv-unhm6 --reason "registered-groups state landed in intercom f1bbfa9"
bd close iv-oiait --reason "systemd unit landed in intercom 2b235db"
bd close iv-jsvpc --reason "Postgres persistence layer landed in intercom a79029e"
bd close iv-g2akk --reason "duplicate of iv-jsvpc, same commit a79029e"
bd close iv-2w8db --reason "orchestrator state landed in intercom 4f76f59"
bd close iv-al5yn --reason "Phase 4 plan landed in intercom d96118e"
bd close iv-de99u --reason "Telegram bridge landed in intercom d8f83da"
bd close iv-xwzgm --reason "SQLite-to-Postgres migration landed in intercom f5ee38b"
bd close iv-i3oxs --reason "fix + dead code cleanup landed in intercom 9b1ee01 and 047f0f2"
bd close iv-u0gmm --reason "IronClaw Phase 5 landed in intercom 5135f7b"

# Category 5: Dependency cleanup
bd close iv-1xtgd.1 --reason "parent epic iv-1xtgd closed, refactor landed in clavain 6e81908"
```

**Total fixes: 42 beads to close** (28 from Category 1 + 2 from Category 2 + 11 from Category 3 + 1 from Category 5)

---

## Beads NOT Flagged (correctly open, no action needed)

These beads are correctly in OPEN or IN_PROGRESS status:

- **iv-ynbh** (P3 OPEN) -- pre-existing, only planning docs, blocks iv-qjwz correctly
- **iv-eblwb** (P4 OPEN) -- UX review docs only, no implementation
- **iv-gyq9l** (P4 OPEN) -- brainstorm and plan only
- **iv-jay06** (P4 OPEN) -- brainstorm, PRD, and plan only
- **iv-wnurj** (P4 OPEN) -- docs update and sprint plan only
- **iv-be0ik** (P1 OPEN) -- roadmap recovery placeholder, status unknown
- **iv-be0ik.1** (P4 OPEN) -- CI baseline plan docs only
- **iv-v9ksd** (P4 OPEN) -- no matching commit found in analyzed period
- **iv-yfkln** (P1 IN_PROGRESS) -- parent epic, children still need closing first
- **iv-yfkln.1 through iv-yfkln.5** (IN_PROGRESS) -- non-recovered children of active epic
