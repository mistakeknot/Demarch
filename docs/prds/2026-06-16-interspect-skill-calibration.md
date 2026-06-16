---
artifact_type: prd
bead: Sylveste-skillcal
stage: design
---
# PRD: Interspect Skill Calibration — Extend the Routing Loop to Skills

## Problem

Sylveste already captures every Claude Code `Skill` invocation in
`~/.claude/audit.log` (per `docs/contracts/audit-log-schema.md`), and
`interspect` already has the closed-loop machinery — evidence → counting-rule
classification → propose → canary → promote/revert — for **flux-drive
agents**. But there is no skill-quality calibration anywhere in the platform:

- `tool-time` records frequency, no quality scoring or auto-apply.
- `interskill`, `interstat`, `intertrack`, `intercheck`, `interlearn`,
  `intermem` — none score skill quality and act on it.
- `interspect` itself is hard-scoped to `source_kind='agent'`.

The result: skill `description`/`when-to-use` text rots silently. A skill that
triggers too eagerly burns tokens; one that triggers too rarely costs
opportunity. Operators have no evidence-based signal — and no autonomous fix
loop — for either failure mode.

## Solution

Generalize `interspect` from `agent` to `{agent, skill}` by adding a new
evidence `source_kind='skill'`, four signal collectors, a per-skill goal
classifier, and a tune-overlay path. Reuse the existing canary, autonomy,
calibration writer, and routing-overrides contract. Auto-apply
`tighten_description` and `when-to-use` patches under canary; propose-only
for SKILL.md body rewrites and availability changes.

## Features

### F1: `source_kind='skill'` schema extension

**What:** Extend `evidence.source_kind` allowed values to include `skill`;
add `skill_goals` and `skill_signals` tables.

**Acceptance criteria:**
- [ ] `sqlite3 .clavain/interspect/interspect.db .schema` lists
  `skill_goals` and `skill_signals` tables with the schema in the
  implementation plan
- [ ] Existing `evidence` rows are unaffected (no migration of agent rows)
- [ ] Inserting `source_kind='skill'` rows passes the existing CHECK
  constraint
- [ ] `(invocation_id, signal_kind)` UNIQUE constraint dedups signal writes

### F2: Skill evidence ingestion from audit.log

**What:** `scripts/ingest-skill-audit.py` drains `~/.claude/audit.log` (and
rotated `.1.gz`) into the evidence store. Wired from PostToolUse +
SessionStart.

**Acceptance criteria:**
- [ ] Every `tool == "Skill"` row in audit.log lands as one `evidence` row
  with `source_kind='skill'`, `source=<skill-name>`, `verdict='neutral'`
- [ ] Watermark stored in `sessions.last_skill_audit_ts` — replays are
  idempotent
- [ ] `error` signal (from `exit_code`) is written inline with ingestion
- [ ] Backfill of 30 days completes in <60s on a 50MB audit.log

### F3: Four signal collectors

**What:** `scripts/signals/collect_{tokens,bead_close,no_redirect,error}.py`
write normalized `[0,1]` values into `skill_signals` per invocation.

**Acceptance criteria:**
- [ ] `tokens` joins per-session CASS analytics (`os/Alwe`) for marginal
  delta vs. counterfactual baseline (same project, ±7 days)
- [ ] `bead_close` reads `.beads/issues.jsonl` directly per the cloud-session
  pattern; 7-day window, pending invocations skipped
- [ ] `no_redirect` parses session JSONL for redirect markers in the next 5
  user turns
- [ ] `error` derives from `audit.log` `exit_code`
- [ ] All four are idempotent on `(invocation_id, signal_kind)`

### F4: Per-skill goal inference

**What:** `scripts/infer-skill-goals.py` classifies each registered skill
into `{speed, precision, completeness}` weights summing to 1, via one Haiku
call on SKILL.md.

**Acceptance criteria:**
- [ ] `~/.claude/plugins/*/skills/*/SKILL.md` and user `.claude/skills/`
  enumerated
- [ ] Content-hash short-circuit (`skill_md_hash`) — unchanged SKILL.md does
  not re-classify
- [ ] Few-shot examples in prompt: retrieval (speed), reasoning (precision),
  audit (completeness)
- [ ] After 20+ invocations, an EMA refinement pass blends inferred weights
  with observed signal mix; row's `classified_from` flips to `observed`

### F5: Weighted skill scoring

**What:** Extend `calibrate-audit.py` to compute per-skill composite scores
and write a `skills` block in `routing-calibration.json`.

**Acceptance criteria:**
- [ ] Skills with ≥10 invocations in trailing 30 days are scored
- [ ] Signal-to-goal mapping: `tokens→speed`, `error→precision`,
  `no_redirect→precision`, `bead_close→completeness`
- [ ] Recency-decay weighting matches the existing agent scorer
- [ ] `routing-calibration.json` has `skills` sibling to `agents`; snapshot
  history records skill drift

### F6: Tune overlays + canary + autonomy

**What:** Extend `/interspect:tune`, `/interspect:propose`,
`/interspect:approve`, `/interspect:revert`, `/interspect:status`,
`/interspect:effectiveness`, `/interspect:health` with `--source-kind=skill`.
Overlays write to `~/.claude/skill-overlays/<skill-name>.md` (mirroring the
agent-overlay precedent).

**Acceptance criteria:**
- [ ] `routing-overrides.json` accepts entries with `kind: "skill_tune"`,
  `skill: <name>`, `action: "tighten_description" | "when_to_use_add" |
  "skill_md_body_rewrite" | "availability"`, `patch`, `evidence_ids`,
  `state`
- [ ] Under `/interspect:enable-autonomy`, `tighten_description` and
  `when_to_use_add` auto-apply with canary monitoring; body rewrites and
  availability changes propose only
- [ ] Canary regression trigger: any signal regresses >20% AND composite >10%
  → auto-revert
- [ ] Reverted modification rows have `state='reverted'`

## Non-goals

- **Real-time signal collection.** `bead_close` and `no_redirect` are
  7-day-plus windowed signals — operators should expect lag between an
  overlay being applied and a calibration verdict. This is by design.
- **Skill discovery / installation.** Existing plugin/marketplace flows
  unchanged.
- **Re-writing skill bodies autonomously.** SKILL.md body rewrites are
  propose-only, even under autonomy.
- **Cross-project goal weight aggregation.** Goal weights remain per-project
  (per the existing `.clavain/interspect/` per-project DB convention).
- **Tool-time displacement.** tool-time continues to write `events.jsonl`
  for its community-comparison flows; interspect reads only
  `~/.claude/audit.log`. Boundary documented in interspect's AGENTS.md.

## Dependencies

- Existing `lib-interspect.sh` (schema migration, canary, autonomy gate,
  routing-overrides writer)
- Existing `routing-overrides.json` contract (`docs/contracts/routing-contract.md`) —
  extended additively with new `kind` value
- Existing audit-log v1 schema (`docs/contracts/audit-log-schema.md`) — no
  change needed; `tool: "Skill"` already captured per the contract's example
- `os/Alwe` CASS analytics for the `tokens` signal
- `.beads/issues.jsonl` for the `bead_close` signal

## Open Questions

- Should the per-skill goal-weight prior come from a curated list in the
  plugin instead of (or alongside) the Haiku classifier? Pro: deterministic,
  reviewable. Con: one more thing to keep current. **Tentative:** ship the
  classifier; revisit if drift exceeds 10% across reruns.
- How should overlays interact when a skill is namespaced via multiple
  plugin sources? **Tentative:** namespace overlays as
  `<plugin>:<skill>.md`, matching the audit-log `name` field convention.
