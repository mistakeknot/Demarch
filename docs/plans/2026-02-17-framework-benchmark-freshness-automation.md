# Framework and Benchmark Freshness Automation — Implementation Plan
**Bead:** iv-wrtg
**Phase:** planned (as of 2026-02-17T00:00:00Z)

## Goal
Implement an automated signal pipeline to detect meaningful updates in frameworks and benchmarks and create review work quickly.

### Task 1: Source polling
- Add pollers in `interwatch` for framework release tags and benchmark/arXiv search terms.
- Normalize update events (framework, paper, version, significance signal).

### Task 2: Impact scoring
- Add scoring weights for API breaks, benchmark claims, and major performance updates.
- Tag outputs as low/medium/high priority review.

### Task 3: Bead synthesis
- Auto-create review tasks with link evidence and suggested action owners.
- Set default priority mapping: high impact -> P1, medium -> P2/P3.

### Task 4: Dashboard and notifications
- Add weekly freshness digest command in `interwatch`.
- Add stale counter and last-success timestamp metrics.

### Task 5: Governance
- Add explicit approval gate before auto-closing review tasks.
- Add runbook step for triage in `interphase`.
