---
artifact_type: prd
bead: iv-wie5i
stage: design
---

# PRD: Discovery OS Integration

## Problem

Interject's scan output bypasses the kernel entirely — writing to its own SQLite and shelling out to `bd create` directly. The kernel's full discovery subsystem (E5) sits empty. Medium-tier discoveries auto-inflate the backlog to 430+ items. No feedback loop exists between "discovery promoted" and "discovery led to shipped code."

## Solution

Wire interject through the kernel discovery CLI (`ic discovery submit/promote`) so every discovery produces a durable kernel record with events, gates, and feedback. Gate bead creation by confidence tier: high-tier auto-creates P2 beads, medium-tier creates P4 beads labeled `pending_triage`, low-tier records only. Add a triage skill for batch review and a one-time backlog sweep.

## Features

### F1: Kernel Bridge in Scanner

**What:** After scoring a discovery, call `ic discovery submit` via subprocess to write a durable kernel record with score, source, and embedding.

**Acceptance criteria:**
- [ ] `scanner.py` calls `ic discovery submit` for every scored discovery (all tiers)
- [ ] Passes `--source`, `--source-id`, `--title`, `--score`, `--summary`, `--url` from discovery data
- [ ] Embedding written to temp file and passed as `--embedding=@<path>`; temp file cleaned up after call
- [ ] If `ic` is not available (command not found), logs a warning and continues (fail-soft during transition)
- [ ] Kernel dedup handles re-scans of same source+source_id automatically
- [ ] Discovery event (`discovery.submitted`) emitted by kernel on each submit
- [ ] Existing interject local DB write is unchanged (dual-write during transition)

### F2: Tier-Gated Bead Creation

**What:** Modify `OutputPipeline.process()` to create beads at different priorities based on confidence tier, with medium-tier beads labeled `pending_triage`.

**Acceptance criteria:**
- [ ] High tier (>= 0.8): `bd create` with P2, `[interject]` title prefix (unchanged behavior)
- [ ] Medium tier (0.5-0.8): `bd create` with P4, `[interject]` title prefix, `--label=pending_triage`
- [ ] Low tier (< 0.5): no bead created, no briefing doc (kernel record only from F1)
- [ ] High-tier still generates briefing doc + brainstorm doc (unchanged)
- [ ] Medium-tier still generates briefing doc (no brainstorm doc)
- [ ] Existing `_create_bead` method accepts priority as parameter instead of computing from tier

### F3: Kernel Promotion Link

**What:** After creating a bead, call `ic discovery promote` to link the kernel discovery record to the bead ID.

**Acceptance criteria:**
- [ ] `outputs.py` calls `ic discovery promote <discovery_id> --bead-id=<bead_id>` after successful `bd create`
- [ ] Promotion event (`discovery.promoted`) emitted by kernel
- [ ] Discovery ID passed from scanner through to output pipeline (new parameter in `process()`)
- [ ] If `ic discovery promote` fails, logs warning but does not fail the pipeline
- [ ] Promotion recorded in interject's local DB via existing `record_promotion()` (unchanged)

### F4: Triage Skill

**What:** New `/interject:triage` skill for batch review of `pending_triage` beads — promote (raise priority) or close.

**Acceptance criteria:**
- [ ] Skill at `interverse/interject/skills/triage/SKILL.md`
- [ ] Lists beads with `pending_triage` label via `bd list --label=pending_triage --status=open`
- [ ] Presents items in configurable batch size (default 5, max 20)
- [ ] For each item: shows title, source, score, URL, summary
- [ ] Actions: "Promote" (set priority to P2, remove `pending_triage` label), "Dismiss" (close bead with reason), "Skip"
- [ ] Calls `ic discovery feedback <id> --signal=promote` or `--signal=dismiss` for feedback loop
- [ ] Reports summary: N promoted, M dismissed, K skipped

### F5: Backlog Sweep Script

**What:** One-time script to defer or close stale beads, reducing backlog noise.

**Acceptance criteria:**
- [ ] Script at `scripts/backlog-sweep.sh`
- [ ] Dry-run mode by default; `--apply` to execute changes
- [ ] Identifies beads with `[interject]` title prefix, no phase state, and no activity for >30 days
- [ ] Candidate beads with P3+ priority: close with reason "stale-sweep"
- [ ] Candidate beads with P2 priority: defer only (never auto-close high-priority)
- [ ] P0/P1 beads are never touched
- [ ] Reports: count of candidates, deferred, closed, and skipped beads
- [ ] Logs every action for auditability

## Non-goals

- Sprint workflow integration (interphase plugin) — deferred to iv-zsio
- Ranking precision evaluation — deferred to iv-wie5i.2
- Migration of existing interject DB data to kernel (not needed; kernel accumulates from next scan forward)
- Cron/daemon for periodic triage
- TTL auto-archive rules (requires bd CLI changes)
- Removing interject's local DB (kept for scoring/learning; kernel-only storage is a future migration)

## Dependencies

- `ic` CLI available on PATH (intercore installed and built)
- Intercore schema v9+ (E5 discovery tables — already shipped)
- `bd` CLI for bead creation (existing dependency)
- Interject source adapters and scoring engine (existing, unchanged)

## Open Questions

None — all resolved in brainstorm (D1-D4).
