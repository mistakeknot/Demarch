---
target: docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md
bead: sylveste-s3z6.19.10
review_quality: balanced (2-agent focused)
review_date: 2026-05-06
agents: [fd-decisions, fd-systems]
---

# Synthesis — microrouter deferral PRD

## Verdict

**NEEDS_ATTENTION** — 1 P0 + 6 P1 + 2 P2. The PRD operationalizes the deferral well on structure (3 features, pinned thresholds, named state fields, D2 protocol) but exposes a meta-pattern: every signal-detection mechanism the PRD adds is **passive** (eval splits measure, check-ins inform, auto-revert depends on future sprints firing). None are active enforcement points. Combined with the thermometer-not-thermostat finding on the chosen mitigation, this PRD is closer to "documentation of intent" than "operational gate."

## P0 findings (1)

### P0.1 — fd-systems: heuristic-stratified eval is a thermometer, not a thermostat

The PRD pre-registers "heuristic-stratified eval split" as the **minimum required mitigation** for the brainstorm-review P0 (β's anchor is heuristic-controlled). But eval split is a *measurement* mechanism, not a *correction* mechanism. It will tell us "router underperforms on heuristic-hard cases" — and then what? The PRD gives no path to fix that without one of the three active mitigations (off-policy randomization, manual-override weighting, loss penalty for heuristic agreement).

**Implication:** The chosen mitigation closes the brainstorm-review P0 only in the diagnostic sense, not the corrective sense. If the strategy phase ships with eval-split-only, `.19.1` design phase MUST add an active mitigation, or the router will trivially clear "looks like heuristic on heuristic-easy cases" and fail on what we actually care about (heuristic-hard cases).

## P1 findings (6, deduped)

1. **D2-vs-mitigation conflation** (fd-decisions P1.1) — D2's headroom measurement happens against the live heuristic. If caveat-1 mitigations are not active during the 4-sprint accumulation, low headroom can mean "β is flawed" OR "β is under-mitigated." The PRD doesn't disambiguate.
2. **D2 checkpoint signal path is passive** (fd-systems P1.1) — D2 result publication has no active alert. If D2 returns "kill epic" at week 3, the next check-in is week ~6; result sits unread.
3. **Open Question #1 (auto-revert default) should be closed before launch** (fd-decisions P1.2) — auto-revert behavior affects whether D2 is a safety net or a hard gate. Leaving this open means the deferral doesn't have a defined failure mode.
4. **Sprint-counting OR-gate is gameable under deadline pressure** (fd-systems P1.2) — "4 weeks OR sufficient volume" lets whichever gate fires first end the deferral. If 4 weeks elapse with volume at 50/80 per cell, calendar pressure can close it early with weak data. Schelling trap by construction.
5. **Auto-revert depends on a future routing sprint** (fd-systems P1.3) — the chosen default "next routing sprint runs D2" is non-deterministic if no routing work lands after 2026-06-30. Could become an indefinite freeze.
6. **F3 check-in cadence has no enforcement teeth** (fd-decisions P1.3, fd-systems P1.5) — "surface in /clavain:status" is informational. Will be skipped under load. Recurring decision burden without enforcement = ceremonial.

## P2 findings (2)

1. **Numeric thresholds pinned but not defended** (fd-decisions P2.4) — 80/20/30%/5% read as Schelling points, not derivations. For audit trail, each should have a one-line rationale.
2. **F2 coordination addresses post-deadline path but not early kill-epic** (fd-decisions P2.5) — if D2 publishes early result, no defined publication / escalation path.

## Pattern recognition

The recurring shape across both reviews: **the PRD adds metadata, not enforcement**. The bead-state fields exist, but no hook reads them. The check-in cadence is named, but no system surfaces it. The auto-revert default is documented, but its activation is contingent on something else firing. None of these are wrong individually; collectively they create a "documented but inert" governance layer.

## Recommended next actions

Three reasonable paths:

**Path A — Patch PRD with active mechanisms:**
- Co-require one active mitigation alongside heuristic-stratified eval split (off-policy randomization is cheapest if `.19.5`/`.19.6` resolver is willing to randomize 5-10% of calls; manual-override weighting if telemetry exists).
- Replace OR-gate with AND-gate: "4 weeks AND sufficient volume" — locks the deadline against early closure with weak data.
- Close Open Question #1: pick auto-revert default explicitly (recommend "default to closing the epic" — most conservative if the operator goes silent).
- Add active D2 alert: hook into `bd state` daemon or cron to surface "D2 result published" notice within 24h.
- Add deadline-locked behavior: if no routing sprint runs by 2026-07-15, auto-create a routing-status bead.
- Add one-line rationale to each numeric threshold.

**Path B — Push P0 to `.19.1` design phase, accept other P1s as caveats:**
- Eval-split-only IS the right scope for deferral PRD. Active mitigations are training-pipeline concerns that belong in `.19.3` design (which `.19.1` plans). Document this scope decision explicitly.
- Add a strong note that `.19.1` MUST commit to ≥1 active mitigation before any LoRA run; eval split alone is necessary but not sufficient.
- Address the easier P1s (close OQ #1, switch OR→AND gate, add rationale to thresholds) but accept passive enforcement as a deliberate scope choice for v0 governance.

**Path C — Reopen the architecture decision:**
- If two rounds of review show β has structural circularity issues that mitigations only partially address, γ may genuinely be the better v0. γ's anchor is judges-across-families — no heuristic-controlled accumulation, no thermometer/thermostat issue.
- Cost of re-opening: this entire sprint's brainstorm + PRD work becomes a "we considered γ and rejected it twice" record. Not wasted; supports a stronger γ commitment if it's the right answer.

## Per-agent reports

- `fd-decisions.md` — 3 P1 + 2 P2; focus on operationalization completeness, threshold defensibility
- `fd-systems.md` — 1 P0 + 4 P1 + 2 P3; focus on feedback loops, signal paths, gameability
