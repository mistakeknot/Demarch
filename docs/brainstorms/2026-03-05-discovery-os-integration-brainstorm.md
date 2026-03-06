---
artifact_type: brainstorm
bead: iv-wie5i
stage: discover
---

# Discovery OS Integration — Close the Research-to-Backlog Loop

**Date:** 2026-03-05
**Bead:** iv-wie5i (P0 epic)

## What We're Building

Wire interject's scan output through the kernel discovery subsystem (`ic discovery`) so that every discovery produces a durable kernel record with events, gates, and feedback — then gate bead creation by confidence tier so only high-signal items auto-create high-priority beads.

The kernel already has the full discovery CRUD (E5, shipped in iv-fra3): submit, score, promote, dismiss, feedback, decay, dedup, embedding search, events. Interject already has source adapters, scoring, and an output pipeline. The gap is the integration seam — interject writes to its own SQLite and shells out to `bd create` directly, bypassing the kernel entirely.

## Why This Approach

Three forces converge:

1. **Backlog inflation.** Interject auto-creates beads for all medium+high discoveries. The backlog hit 430 items. Medium-tier items are noise masquerading as work.

2. **Invisible discovery.** Without kernel records, Interspect can't observe discovery patterns, Clavain can't route based on discovery confidence, and no feedback loop exists between "discovery promoted" and "discovery led to shipped code."

3. **Dual-store divergence.** Maintaining parallel state in interject's SQLite and the kernel's discovery tables would create two sources of truth that inevitably diverge. Better to commit to kernel-native integration.

## Key Decisions

### D1: Kernel-native plugin tier (new philosophy)

**Decision:** Interject becomes a kernel-native plugin — it MAY require intercore as a hard dependency.

**Rationale:** The standalone degradation principle from PHILOSOPHY.md doesn't serve plugins whose entire value proposition IS kernel integration. Forcing interject to maintain a local fallback store would create divergent state that's worse than the dependency. A new "kernel-native" tier in the philosophy codifies this exception with clear criteria.

**Affected plugins:** interject, interspect, interphase. All other Interverse plugins remain standalone-capable.

### D2: Subprocess ic CLI integration

**Decision:** Interject calls `ic discovery submit` via subprocess, same pattern as existing `bd create` calls.

**Rationale:** Zero new dependencies. The ic CLI handles dedup, events, gates atomically. ~50ms overhead per call is acceptable for batch scan workflows. Embedding data passes via `--embedding=@tempfile`. Error handling is string parsing but the interface is stable.

### D3: Beads-first with pending_triage label

**Decision:** Medium-tier discoveries still create beads, but at P4 with a `pending_triage` label. High-tier creates beads at P2 (same as today). The `/interject:triage` skill promotes (raises priority) or closes pending beads.

**Rationale:** Single tracking system — everything is a bead. The effective backlog stays clean because P4+`pending_triage` items rank at the bottom of discovery scoring and don't appear in `bd ready` by default. No need to teach consumers about two different stores.

**Alternative rejected:** Triage-first (medium-tier skips bead creation, only lives in kernel until promoted). Cleaner for backlog count, but fragments tracking across two systems.

### D4: Kernel record for all tiers

**Decision:** Every scored discovery (including low-tier) gets an `ic discovery submit` call. Only medium+ create beads.

**Rationale:** The kernel discovery table is the durable record for the feedback loop. Low-tier items need to be recorded so that threshold calibration, interest profile learning, and decay work correctly. The kernel table is designed for this volume.

## Integration Flow (Target)

```
Scanner scores discovery
    |
    v
ic discovery submit --source=X --source-id=Y --title=T --score=S --embedding=@file
    |
    +-- Kernel: dedup check, event emitted, record created
    |
    v
Tier routing:
    high (>= 0.8)  --> bd create (P2) + briefing doc + brainstorm doc
    medium (0.5-0.8) --> bd create (P4, label:pending_triage) + briefing doc
    low (< 0.5)     --> kernel record only (no bead, no doc)
    |
    v
After bead creation:
    ic discovery promote <id> --bead-id=<bid>
    (links kernel record to bead, emits promotion event)
```

## Scope

### In scope
- `scanner.py`: Add `ic discovery submit` call after scoring (dual-write to local DB + kernel)
- `outputs.py`: Modify `process()` to implement tier-gated bead creation (P4+pending_triage for medium)
- `outputs.py`: Add `ic discovery promote` call after bead creation
- `/interject:triage` skill: Batch review of pending_triage beads (promote/dismiss)
- `scripts/backlog-sweep.sh`: One-time sweep of stale beads (dry-run by default)
- `PHILOSOPHY.md`: Add kernel-native plugin tier
- `interject/CLAUDE.md`: Document kernel-native status

### Out of scope (deferred)
- Interphase plugin (sprint workflow integration) — iv-zsio
- Ranking precision evaluation — iv-wie5i.2
- Cron/daemon for periodic triage
- Migration of existing interject DB data to kernel
- TTL auto-archive rules

## Open Questions

- **Embedding temp file lifecycle:** Should scanner clean up temp files immediately, or batch-clean at scan end? (Implementation detail — decide during planning.)
- **Triage batch size:** The original PRD proposed 5-10 items per batch in the triage skill. Is that right, or should it be configurable? (Probably configurable with sensible default.)
- **Backlog sweep thresholds:** 30-day staleness for defer, P3+ for close. These need validation against actual backlog data before running.
