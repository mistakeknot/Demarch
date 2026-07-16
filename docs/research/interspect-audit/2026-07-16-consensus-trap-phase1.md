# Consensus-trap breaker — Phase 1 (Sylveste-4b5.1)

Date: 2026-07-16
Bead: Sylveste-4b5.1 (parent: Sylveste-4b5)
Pre-registration: agenda top bet #2 — extend calibrate-audit.py + canary machinery to log
agreement-rate and output-diversity across the last N calibration cycles; plot agreement-rate
trend against independent defect-escape-rate.

**Scope note:** the BREAKER (auto-firing circuit) is hard-blocked on `sylveste-9lp.37`
(frozen external holdout register) landing first, per the bead's own acceptance criteria. This
report does not build the breaker. It (a) measures the retrospective trend if data allows, and
(b) extends the metrics *emission* in `interverse/interspect/scripts/calibrate-audit.py` so
future cycles are measurable.

**Related, same-day, same-directory:** `2026-07-16-holdout-register-phase1.md` (Sylveste-407,
the pre-registered spike for the *other* half of this dependency pair) independently audited the
same substrate in more depth for a different question (holdout-split feasibility). Its substrate
inventory is treated as authoritative here rather than re-derived; this report cites it rather
than duplicating the host/schema archaeology. Where this report's own recon (done before reading
that report) reached the same conclusion independently, both are noted.

## KILL RULE (as pre-registered)

> If agreement-rate is flat (no upward trend) across ≥5 cycles AND defect-escape-rate is
> stable, the loop is not collapsing — record the baseline constants and demote to a standing
> monitor; do not build the breaker.

## Verdict: NOT EVALUABLE — retrospective trend is unpowered (0 cycles on every host)

A "calibration cycle" is one invocation of `_interspect_write_routing_calibration`
(`hooks/lib-interspect.sh:3677`), which writes `routing-calibration.json` and archives a
timestamped snapshot to `.clavain/interspect/calibration-history/`. That directory does not
exist, and `routing-calibration.json` does not exist, on **any** host checked:

| Host | Path | `routing-calibration.json` | `calibration-history/` | Cycles |
|---|---|---|---|---|
| Mac | `~/projects/Sylveste/.clavain/interspect/` | absent | absent | **0** |
| zklw | `~/projects/Sylveste/.clavain/interspect/` | absent | absent | **0** (also wrong subsystem — see below) |
| zklw | `~/.clavain/interspect/` (cross-project home DB) | absent | absent | **0** |

Zero cycles on every host means the retrospective kill-rule evaluation (which needs ≥5 cycles)
is not powered by a wide margin — not "close," not "borderline." This absence is itself the
finding, and it is the strongest possible argument for doing the metrics-emission work now: the
instrumentation needs to exist *before* the first cycle lands, or the first several cycles go
unmeasured too.

Per DO item 1's own framing: this is recorded as the finding rather than forced into a false
positive/negative reading.

## Why zero cycles, not "not enough evidence"

`_interspect_compute_agent_scores` only requires `min_sessions=3` per agent
(`_INTERSPECT_CALIBRATION_MIN_SESSIONS=3`, `lib-interspect.sh:3482`) to score an agent at all —
a low bar that Mac's evidence (40 agent-sourced rows, various sources) could plausibly clear for
at least one agent. That `routing-calibration.json` still doesn't exist on Mac suggests
`_interspect_write_routing_calibration` has never actually run there (e.g. the SessionEnd hook
that calls `write-routing-calibration.sh` isn't firing, isn't wired for this repo, or every past
run hit one of its early-return conditions) — not solely that the evidence floor isn't met. This
matches Sylveste-407's surprise #3: despite the ecosystem-research-agenda claiming "ioe7 has
gone live — interspect now recalibrates routing on agent-produced evidence," no calibration
artifact exists anywhere. Worth a separate ticket to check why the writer isn't firing; out of
scope for this Phase-1 (which is about instrumenting the *trend*, not fixing the *writer*).

## Substrate actually checked (this report's own pass, cross-checked against Sylveste-407)

Three interspect.db instances hold live Sylveste-relevant agent/skill evidence:

| DB | Host | Schema | Evidence rows | Sessions | `verdict_outcome` rows | Notes |
|---|---|---|---|---|---|---|
| `~/projects/Sylveste/.clavain/interspect/interspect.db` | Mac | current (`source_kind`, skill_signals present) | 244 | 52 | **0** | Live, monorepo-scoped. All rows within 90 days. |
| `~/.clavain/interspect/interspect.db` | zklw | current | 22 | 39 | **8** (4 agents × 2 each) | Cross-project home DB — the only place `verdict_outcome` exists at all. Sessions span 2026-03-16 → 2026-07-06 (18 rows fall in the trailing 90 days). |
| `~/projects/Sylveste/.clavain/interspect/interspect.db` | zklw | older (no `source_kind`, no skill tables) | 1896 | — | 0 | **Wrong subsystem** — confirmed independently in this pass (743 `decomposition_outcome` + 1126 `kernel-phase` events, matching Sylveste-407's 743/427/410/289 breakdown) and by Sylveste-407 directly. This is intercore kernel/decomposition telemetry, not agent-routing evidence. Excluded. |

`override_reason` is empty on every evidence row, on every host, with no exceptions found.
`modifications` table is empty everywhere (0 applied overrides anywhere, confirming Sylveste-407
independently). No `routing-overrides.json` exists on either host.

## Metric definitions (derived from the actual schema)

All three are implemented in `compute_consensus_trend_point()` in
`interverse/interspect/scripts/calibrate-audit.py`, over a rolling `--window-days` (default 90,
matching the drift-audit window) against `evidence`/`skill_signals` in `interspect.db`:

1. **`agreement_rate`** — `1 - (agent-sourced evidence rows with non-empty override_reason /
   total agent-sourced evidence rows)` in the window. Intended proxy for verifier-vs-generator
   agreement (share of agent output accepted without a recorded override). **Limitation:**
   `override_reason` is unpopulated fleet-wide (0 non-empty rows found anywhere), so this metric
   is currently a constant 1.0 wherever `evidence` rows with `source_kind='agent'` exist, and
   `None` (undefined) where they don't. It is not yet measuring real disagreement — it is
   measuring the *absence* of an override-recording pathway. This is documented in-code and
   here rather than silently reported as a real 1.0 "perfect agreement" reading.

2. **`output_diversity`** — mean(distinct `evidence.source` values per session) / (distinct
   `source` values across the whole window), in the window. 1.0 = every session touches every
   source seen (no per-session specialization / maximal apparent diversity by this proxy); lower
   = sessions cluster on fewer sources relative to the whole population. **Limitation:** this
   inspects *which tool/skill/agent emitted the evidence*, not the semantic content of what was
   produced — it is a proxy for behavioral variety, not output-content diversity. A generator
   that always calls the same 3 skills but produces textually varied output would still register
   as low diversity here.

3. **`defect_escape_rate`** — `1 - avg(skill_signals.value)` where `signal_kind='error'`, in the
   window. `skill_signals.value` is stored as a goodness score in [0,1] (1.0 = clean; confirmed
   against `_interspect_select_skill_action`'s `1 - value` deficit convention in
   `lib-interspect.sh:5230-5271`, and against raw rows: `value=1.0, raw_value=0.0` for all
   sampled `error` rows). **Limitation:** this is a skill-invocation error rate, not a verified
   *downstream* defect count — nothing in the current schema distinguishes "defect found by the
   loop itself" from "defect discovered later, independently, after the loop approved." It is
   the closest available proxy, not the target concept.

## Baselines (point-in-time, this run)

| Host / DB | Window | `agreement_rate` | `output_diversity` | `defect_escape_rate` | `evidence_n` |
|---|---|---|---|---|---|
| Mac | 90d (= full history; all 244 rows are recent) | 1.000 | 0.057 | 0.000 | 244 |
| zklw home (cross-project) | 90d | 1.000 | 0.160 | n/a (no `skill_signals` matching in window) | 18 |
| zklw home (cross-project) | 365d (full history) | 1.000 | 0.182 | n/a | 22 |

`defect_escape_rate` on the zklw home DB is `None`/n/a: that DB has 0 `skill_signals` rows with
`signal_kind='error'` in either window (its evidence is dominated by `verdict_outcome` and
`tool_*` events, not `skill_invocation`). Only the Mac DB currently has enough `skill_signals`
volume (531 rows total, 204 of kind `error`) to populate this metric.

Since these are single point-in-time reads (n=1 "cycle" per host, informal — not written by
`_interspect_write_routing_calibration`), **no trend exists to plot yet.** These numbers are
recorded as the pre-instrumentation baseline, not as evidence of stability or drift.

## Kill-rule status

**Not evaluable.** 0 cycles < 5 required, on every host. Per the pre-registration's own
framing, this is not "the loop passed the kill rule" (which would require observing flatness
across ≥5 real cycles) — it is "there is no trend to evaluate the kill rule against yet."
Re-evaluate once `.clavain/interspect/calibration-history/` accumulates ≥5 snapshots on any one
host (each `_interspect_write_routing_calibration` run appends one), which per DO item 3 will
now also each append one `consensus-trend.jsonl` line via the extended `calibrate-audit.py`.

Recommendation: **do not build the breaker** — not because the loop was measured and found
non-collapsing, but because there is nothing yet for a breaker to watch. This is consistent with
the bead's own hard-block on `sylveste-9lp.37` (the holdout register), which independently
gates the breaker. Both gates point the same direction: instrument now, decide later.

## Changes made (additive, `interverse/interspect/scripts/calibrate-audit.py`)

Extended `calibrate-audit.py` to compute and emit the three metrics above on every run, on top
of its existing drift-audit behavior, which is unchanged:

- `compute_consensus_trend_point(db_path, now, window_days)` — new function; queries
  `interspect.db` directly via stdlib `sqlite3` (no new dependency) and returns
  `{cycle_ts, agreement_rate, output_diversity, defect_escape_rate, evidence_n}`.
- `append_consensus_trend(calibration_dir, point)` — appends one JSON line to
  `.clavain/interspect/consensus-trend.jsonl` (created on first write).
- `render_consensus_trend_section(...)` — new markdown section, inserted into the existing
  report between "Per-agent drift" and "Methodology."
- The consensus-trend point is computed **before** the existing early-return-if-no-calibration
  check, so metrics emission happens on every run regardless of whether
  `routing-calibration.json` exists yet — this is deliberate: the whole point is to start
  accumulating trend data *before* the loop has calibrated even once, since Phase-1 found it
  never has.
- New `--dry-run-safe` flag: computes and prints the trend point as JSON, writes nothing to
  disk (no JSONL append, no report). Used for the test run below.
- No changes to existing drift-audit logic, arguments, exit codes, or report sections/wording
  (verified: `git stash` diff shows only additions to the file; pre-existing structural test
  failures — a stale hardcoded command count and one non-executable `.sh` file — are unrelated
  and reproduce identically on the pre-change file).

### Test run (scratch copy, real `.clavain` untouched)

```
$ mkdir -p /tmp/interspect-scratch/testrepo/.clavain/interspect
$ cp ~/projects/Sylveste/.clavain/interspect/interspect.db /tmp/interspect-scratch/testrepo/.clavain/interspect/
$ cd /tmp/interspect-scratch/testrepo
$ python3 .../scripts/calibrate-audit.py --dry-run-safe --repo-root=. --window-days=90
{
  "agreement_rate": 1.0,
  "cycle_ts": "2026-07-16T14:20:15.702059+00:00",
  "defect_escape_rate": 0.0,
  "evidence_n": 244,
  "output_diversity": 0.05691056910569106
}
$ echo $?
0
$ ls .clavain/interspect/         # no consensus-trend.jsonl written
interspect.db
```

Also verified the non-dry-run path against the same scratch copy: with no
`routing-calibration.json` present, the script still exits 1 with the pre-existing "run
/interspect:calibrate first" message (unchanged behavior) **and** still appends the trend point
to `consensus-trend.jsonl` (new behavior, by design — metrics emission is independent of
calibration bootstrap state). With a synthetic `routing-calibration.json` added, the full
markdown report renders with the new "Consensus-trend" section correctly populated. Real
`~/projects/Sylveste/.clavain/interspect/` was confirmed untouched throughout (checked file
listing and mtimes before/after).

## Next steps (not this bead)

- Investigate why `_interspect_write_routing_calibration` has never completed successfully on
  either host despite `ioe7` being marked closed/live — likely candidate: SessionEnd hook wiring.
  Worth a bead; this Phase-1 doesn't fix it, only notes the gap (matches Sylveste-407's surprise
  #3, filed independently).
- Once `sylveste-9lp.37` lands and calibration cycles start accumulating, re-run this
  measurement against `.clavain/interspect/consensus-trend.jsonl` with ≥5 rows to actually
  evaluate the kill rule.
- `agreement_rate` as defined is inert until something populates `override_reason` on agent
  evidence with real accept/reject signal — flagging this as a schema gap, not fixing it here
  (out of scope: extending evidence emission at the override-recording call site was not part of
  this bead's DO list).
