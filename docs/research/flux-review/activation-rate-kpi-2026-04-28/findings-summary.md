---
artifact_type: review-findings-summary
target: docs/brainstorms/2026-04-28-activation-rate-kpi-brainstorm.md
bead: sylveste-8r5h
date: 2026-04-29
tracks: 1 (focused, 3 lenses)
agents: [fd-systems, fd-decisions, fd-correctness]
status: resolved
---

# Brainstorm Review — Findings Summary (Resolved)

**Initial severity counts:** 2 P0 · 6 P1 · 7 P2 · 4 P3
**Resolution status (2026-04-29):** All P0 + P1 folded into refined design via second-round design questions.

## P0 — must-fix (resolved)

1. **`SourceActivation` doesn't exist; emit silently fails.** → New `subsystem_events`
   table + `SourceSubsystem` source. Sequencing: kernel surface ships before any
   subsystem adopts the helper (Phase 1 §1).

2. **Cursor-advance race + missing dedup key.** → `BEGIN EXCLUSIVE` around
   read-process-write triple; `source_event_id` column with `INSERT OR IGNORE`.
   Captured in Key Decision #6.

## P1 — significant changes (resolved)

3. **Emit-without-integration gaming loop.** → "Wired" = ≥3 distinct sessions
   in 14d (Key Decision #1). Single-emit alone does not pass.

4. **Closed feedback loop undefined.** → v1 report-only + owner notifications;
   v2 soft-block (`--ack-low-activation`) after baseline calibration. Key
   Decision #7.

5. **Survivorship bias in 25th-percentile threshold.** → Baseline computed over
   `(activated + unactivated)` with unactivated as separate counter. Key
   Decision #11.

6. **Passive-first spike skipped.** → Phase 0 is a 1-week spike against
   `iv-zsio` / `iv-godia` / `iv-2s7k7` with explicit ≥2/3 success criterion.
   If passive wins, explicit emit is deferred indefinitely.

7. **`first_merge_ts` wrong on renames.** → `git log --follow --diff-filter=AR`
   plus stored commit hash. Key Decision #10.

8. **Session sentinel not durable.** → `ic state set` keyed on
   `(subsystem, session_id)` with TTL. Key Decision #5.

## Convergent themes (cross-lens)

- **Meta-recursive failure risk** — the KPI itself was exposed to its target
  pattern. fd-correctness located the code paths; fd-systems framed it as
  a gaming loop; fd-decisions framed it as survivorship bias.
- **Closed feedback loop** — flagged independently by fd-systems and
  fd-decisions; resolved with v1/v2 split.
- **Reversibility** — fd-decisions surfaced the "validate passive first"
  starter option; folded in as Phase 0.

## Net effect

Recommendation shifted from "Approach A direct" to **"Approach A gated by a
1-week Phase 0 passive spike."** All architecture-level concerns are now in
the brainstorm Key Decisions; remaining P2/P3 are plan-level checklists.
