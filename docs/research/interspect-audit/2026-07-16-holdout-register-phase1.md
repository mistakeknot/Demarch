# Holdout Register — Phase 1 (Sylveste-407)

Date: 2026-07-16
Bead: Sylveste-407
Pre-registration: `docs/research/2026-07-16-ecosystem-research-agenda.md`, top bet #1 (also `docs/research/2026-07-05-ecosystem-research-agenda.md`)

## Pre-registered experiment and kill rule

> Retroactively freeze a random 20% of existing interspect evidence events as holdout; recompute the currently-active routing overrides on the training split only; measure how many flip.
>
> **KILL RULE:** if evidence volume is too sparse to power the split (<~50 events per scored agent) OR <5% of overrides flip, park the primitive and set a volume tripwire to revisit at 2x current evidence.

## Verdict: PARKED

Both preconditions fail, and fail hard enough that the experiment cannot be run in any meaningful form:

1. **No scored agent anywhere has close to 50 scoring-eligible events.** The best case found (4 flux-drive review agents on the zklw home DB) has 2 sessions / 8 events each — 1/6th of the volume floor, and below the code's own hardcoded minimum of 3 sessions.
2. **There is nothing to flip.** `routing-overrides.json` — the file interspect's own design doc names as the cross-repo override contract — does not exist on either host. The `modifications` table (the DB-side record of applied overrides) is empty on every interspect.db found on both hosts. Zero active overrides means "flip count" is undefined, not zero-and-passing.

Both kill-rule branches are satisfied independently; this is not a marginal call.

## Substrate inventory

### What "the interspect DB" means turned out to be host- and directory-specific — there is no single canonical DB

Searching found `interspect.db` at 3 distinct locations on zklw with materially different schemas and content, plus ~60 more at per-subrepo `.clavain/interspect/` paths across both hosts (one per Sylveste subrepo + unrelated sibling projects — out of scope, each is a tiny independent instance). The three in-scope candidates:

| Location | Host | Rows (evidence) | Schema | Verdict |
|---|---|---|---|---|
| `~/projects/Sylveste/.clavain/interspect/interspect.db` | Mac | 244 | current (`source_kind`, skill_signals, skill_goals present) | **live, monorepo-scoped** |
| `~/.clavain/interspect/interspect.db` | zklw | 22 | current (matches Mac schema) | **live, cross-project global** (not Sylveste-scoped) |
| `~/projects/Sylveste/.clavain/interspect/interspect.db` | zklw | 1896 | older (no `source_kind`, no skill tables) | **stale snapshot, wrong subsystem** — see below |
| `~/projects/.clavain/interspect/interspect.db` | zklw | 12 | current | umbrella-level, negligible volume |

The zklw path that name-matches the orchestrator's brief (`~/projects/Sylveste/.clavain/interspect/interspect.db`, 1896 rows, "most likely accumulates evidence THERE") is a **false lead**: its evidence is 1126 `kernel-phase` + 743 `decomposition_outcome` events — intercore kernel/decomposition telemetry, a different subsystem entirely, not agent-routing evidence. Its schema predates `source_kind` and lacks `skill_signals`/`skill_goals`, and its last write was 2026-06-20 — three weeks stale relative to the Mac DB's `interspect.db-wal` activity through 2026-07-16. It has zero rows in `modifications`; it does hold 20 `verdict_outcome` rows, but none are scoreable (1 session/agent, and the pre-`source_kind` schema means the scoring query cannot execute against it at all). Ruled out.

The genuinely live, Sylveste-scoped substrate is the **Mac DB** (244 events, sessions through 2026-06-27, DB mtime 2026-07-16) plus the **zklw home DB** (`~/.clavain/interspect/interspect.db`, cross-project — 22 rows, of which some are Sylveste sessions). Both were copied to `/Users/sma/.claude/jobs/7b16ec73/tmp/lane-a/{mac,zklw-home}/interspect.db` before querying (SHA-256 recorded below for provenance). No `routing-calibration.json`, `calibration-history/`, or `routing-overrides.json` exists anywhere on either host. One home-level artifact exists: `~/.clavain/interspect/calibrated-thresholds.json` on zklw (single agent `fd-safety`, `sample_count: 3`, dated 2026-04-04) — a legacy/different-schema artifact, not the current `_interspect_write_routing_calibration` output format (schema_version 2).

```
sha256  mac/interspect.db:       5fb1daa2094b8945d7db2b60ff8f961d860986bf498cbe032e199a44158926f0
sha256  zklw-home/interspect.db: 7c92f4edfa60b589be38dcbb78a3553ab7113c2784a93224b47e16baa5138418
```

### Mac (`~/projects/Sylveste/.clavain/interspect/interspect.db`) — 244 evidence events, 51 sessions (2026-03-26 → 2026-06-27)

Event kinds:

| event | count |
|---|---|
| `skill_invocation` | 204 |
| `coordination.acquired` | 36 |
| (blank/other) | 4 |

`source_kind`: `skill` = 204, `agent` = 40. **Zero rows** have `event IN ('agent_dispatch','verdict_outcome','override','disagreement_override')` — the exact event set `_interspect_compute_agent_scores` (in `interverse/interspect/hooks/lib-interspect.sh:3609-3627`) requires for agent-routing scoring. The agent-routing lane has literally nothing to score on this host.

`modifications` table: empty (0 rows).

Top skill_invocation sources by distinct-session count (the skill-calibration lane, `score-skills.py`, default `--min-invocations 10`):

| source (skill) | invocations | distinct sessions |
|---|---|---|
| `interflux:flux-engine` | 42 | 7 |
| `deep-research` | 27 | 6 |
| `interflux:flux-melange-engine` | 11 | 5 |
| `interflux:flux-review-engine` | 10 | 8 |
| `interflux:flux-review` | 10 | 8 |
| all others | ≤7 each | ≤4 each |

Only 2 of ~40 skills clear the `min-invocations=10` bar, and even those sit at 6-7 sessions — nowhere near a volume that supports a stable 80/20 split (an 80% training slice of 7 sessions is 5-6 sessions; removing 1-2 for holdout is not a meaningful freeze, it's noise).

### zklw home (`~/.clavain/interspect/interspect.db`, cross-project) — 22 evidence events, 39 sessions

This is the only DB found anywhere with `verdict_outcome` events (the agent-scoring lane's real signal):

| agent (source) | verdict_outcome events | sessions |
|---|---|---|
| `architecture` | 2 | 2 (`b9d8fa49…`, `eea1cf39…`) |
| `correctness` | 2 | 2 (same two sessions) |
| `game-design` | 2 | 2 (same two sessions) |
| `quality` | 2 | 2 (same two sessions) |

All 8 events fall into just 2 sessions, dated 2026-03-16 and 2026-07-06 — a single flux-drive review run each, four months apart. `_interspect_compute_agent_scores` requires `len(sessions) >= min_sessions` (hardcoded `_INTERSPECT_CALIBRATION_MIN_SESSIONS=3`, `lib-interspect.sh:3482`) before it will score an agent at all; every agent here sits at 2/3. None would even appear in `_interspect_compute_agent_scores`'s output today, let alone reach the 50-event volume floor from the pre-registration. `modifications`: empty.

### zklw `~/projects/Sylveste/.clavain/interspect/interspect.db` (1896 rows) and `~/projects/.clavain/interspect/interspect.db` (12 rows)

Ruled out as described above (wrong subsystem / negligible volume respectively). The zklw Sylveste-scoped DB holds 20 unscoreable `verdict_outcome` rows (see above); otherwise neither has scoreable agent-routing events, and both have empty `modifications`.

## Kill-rule arithmetic

Precondition for running the experiment: **at least one host** where scored agents have ≥~50 evidence events each **AND** at least one active override/calibration artifact exists to test flips against.

| Check | Result |
|---|---|
| Any host with ≥50 scoring-eligible events for any single agent | **No.** Best case: 4 agents × 8 events / 2 sessions each (zklw home DB) — 16% of the floor, and below the code's own 3-session minimum |
| Any active routing override or calibration artifact anywhere | **No.** `routing-overrides.json` absent on both hosts; `modifications` table empty in every DB found; no `routing-calibration.json`/`calibration-history/` exists; the one calibration-shaped file found (zklw `~/.clavain/interspect/calibrated-thresholds.json`) is a stale, differently-schemed artifact from 2026-04-04 with `sample_count: 3` for a single agent — not a routing override, and itself below today's code's minimums |

Both branches of the kill rule are independently true: evidence volume is far too sparse to power any split, and there are zero active overrides to measure flips against — "flip %" is not computable, not zero. **Zero active overrides means there is nothing to flip yet.** Recommendation: PARK per the pre-registered rule, with a volume tripwire (below).

## Volume tripwire

Current per-lane volume and the 2x threshold that should trigger a revisit:

| Lane | Host | Current volume | 2x threshold | Where to check |
|---|---|---|---|---|
| Agent-routing (`verdict_outcome` etc.) | Mac (`~/projects/Sylveste/.clavain/interspect/interspect.db`) | 0 events | 0 → any nonzero is already a state change worth re-checking | `sqlite3 interspect.db "SELECT event, COUNT(*) FROM evidence WHERE event IN ('agent_dispatch','verdict_outcome','override','disagreement_override') GROUP BY event;"` |
| Agent-routing (`verdict_outcome`) | zklw (`~/.clavain/interspect/interspect.db`) | 8 events / 4 agents (2 sessions each) | 16 events / 4+ sessions per agent — **still short of both the code's `min_sessions=3` and the pre-reg's ~50-event floor**; real trigger is reaching ≥50 events for the *best-populated* agent | same query against `ssh zklw '~/.clavain/interspect/interspect.db'` |
| Skill-calibration (`skill_invocation`) | Mac | best case 42 events / 7 sessions (`interflux:flux-engine`) | 84 events / 14 sessions | `sqlite3 interspect.db "SELECT source, COUNT(*), COUNT(DISTINCT session_id) FROM evidence WHERE event='skill_invocation' GROUP BY source ORDER BY 2 DESC;"` |
| Active overrides to test flips against | Both | 0 (`routing-overrides.json` absent; `modifications` empty everywhere) | first nonzero override written by `_interspect_write_routing_calibration` / `interspect-approve` | `test -f .clavain/interspect/routing-calibration.json` and `.claude/routing-overrides.json`; `sqlite3 interspect.db "SELECT COUNT(*) FROM modifications WHERE status='applied';"` |

Re-run this Phase-1 spike when **either** (a) any single agent's `verdict_outcome`/`agent_dispatch` count reaches ~50 on any host, **or** (b) `routing-overrides.json` or a non-empty `modifications` table first appears — whichever comes first. Given current growth (Mac went 0→244 events over ~3 months but 0 of them scoring-eligible; zklw's 4-agent cluster added exactly 1 new session in 4 months), the override-artifact trigger is more likely to fire first than the volume trigger, and firing on it alone would still leave the experiment underpowered per the volume clause — both conditions likely need to be watched, not just the first to flip.

## What would make this runnable

1. **Agent-routing lane needs `verdict_outcome`/`agent_dispatch` events to actually accumulate.** Right now flux-drive-style review runs (`architecture`, `correctness`, `game-design`, `quality`, `fd-*`) are the only source of these events, and they're rare (2 sessions in 4 months on zklw, zero on Mac). Whatever pipeline should be emitting `verdict_outcome` per flux-drive dispatch isn't firing on the Mac host at all — worth checking whether flux-drive runs on Mac are recording to a different DB, not recording at all, or genuinely aren't happening there.
2. **`routing-overrides.json` needs to exist before there's anything to test a holdout split against.** Since `_interspect_write_routing_calibration` requires `min_sessions=3` per agent and none currently qualify, no calibration file has ever been written, so `/interspect calibrate` → `/interspect-approve` has never had output to promote into an override. This is upstream of the holdout question: the loop hasn't calibrated even once yet, on either host, in the current schema.
3. **Once (1) and (2) both hold**, the actual experiment is mechanically simple and does not need reimplementation: `_interspect_compute_agent_scores` in `interverse/interspect/hooks/lib-interspect.sh:3500` is a self-contained Python block invoked from bash; the holdout harness would (a) copy the DB to scratch, (b) seeded-random-sample 20% of `evidence` rows into a `holdout` marker or a separate excluded table, (c) call `_interspect_write_routing_calibration` against the 80% remainder, (d) diff `recommended_model` per agent against the full-data run. No reimplementation of the scoring math is needed or advisable — the risk in a from-scratch reimplementation is silently drifting from the production scoring logic, which is the one thing this experiment must not do.
4. **Skill-calibration lane (`score-skills.py`) is closer to runnable** than the agent lane — `interflux:flux-engine` (42 invocations/7 sessions) and `deep-research` (27/6) are the least-sparse signals found anywhere, but neither is written into an active overlay/override artifact today (`~/.claude/skill-overlays/` is empty on both hosts), so the same "nothing to flip against" problem applies. If a skill-calibration holdout is wanted as an alternative Phase-1 lane, `interflux:flux-engine` is the best-populated candidate but still well under a defensible 80/20 split (7 sessions total).

## Surprises

- The zklw path that best-matched the orchestrator's naming guess (`~/projects/Sylveste/.clavain/interspect/interspect.db`) was the largest DB found (1896 rows) but turned out to be the wrong subsystem (intercore kernel/decomposition telemetry, stale schema, last write 2026-06-20) — a volume red herring that would have produced a fabricated-looking "high volume" result if not schema-checked against `_interspect_compute_agent_scores`'s actual event filter.
- The live agent-routing signal (`verdict_outcome`) exists in exactly one place across both hosts — the zklw *cross-project* home DB (`~/.clavain/interspect/`), not the Sylveste-monorepo-scoped DB on either host — and even there it's two flux-drive runs four months apart.
- Despite `docs/research/2026-07-16-ecosystem-research-agenda.md` stating "ioe7 has since gone live — interspect now recalibrates routing on agent-produced evidence," no calibration file (`routing-calibration.json`) or override (`routing-overrides.json`) exists anywhere as of this audit. If ioe7's loop is live, it is not yet writing calibration artifacts under the current schema/thresholds — worth flagging back to whoever authored that agenda line, since it's a factual claim this audit could not corroborate on-disk.


---

*Corrections applied 2026-07-16 after independent opus validation: Mac session count 51 (not 52); the false-lead zklw DB holds 20 `verdict_outcome` rows, none scoreable (not zero). Validation also strengthened the verdict: all zklw-home `verdict_outcome` rows carry `findings_count=0`/`status=NULL`, independently failing the scorer's `total_findings > 0` gate — the PARK is over-determined.*
