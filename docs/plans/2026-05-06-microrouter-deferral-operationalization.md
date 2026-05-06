---
artifact_type: plan
bead: sylveste-s3z6.19.10
stage: design
requirements:
  - F1: Bead-body cascade updates (sylveste-1mp6)
  - F2: D2 sibling bead with eval protocol (sylveste-5p7s)
  - F3: Deferral keep-alive mechanics (sylveste-ngft)
brainstorm: docs/brainstorms/2026-05-06-microrouter-architecture-decision-brainstorm.md
prd: docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md
---
# Microrouter Deferral Operationalization — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use clavain:executing-plans to implement this plan task-by-task.

**Bead:** sylveste-s3z6.19.10
**Goal:** Land the deferred-β decision visibly across the bead graph, install active enforcement (state fields + session-start hook with escalation), and file D2 (heuristic-baseline measurement) as a sibling bead — all in one commit at sprint close.

**Architecture (post-Path-C revision):** Three feature-children (F1/F2/F3) reduce to text edits on bead bodies (`bd update --notes`) + state-field installation (`bd set-state`) + a D2 follow-up bead refresh + a new F4 follow-up bead filed for the surfacing layer. No code paths in this sprint — the originally-planned `scripts/deferral-check.sh` + `.claude/settings.json` hook wiring was dropped during plan review (see Plan revision note below for why); F4 owns the surfacing implementation as a separate sprint.

**Tech Stack:** bd CLI only.

**Plan revision (post-flux-drive review, Path C):** Original plan had T7 (write `scripts/deferral-check.sh`) + T8 (wire it as SessionStart hook). Plan review found 3 P0s — the BLOCKING enforcement was structurally inert (SessionStart hooks can't block sessions per Claude Code spec), `auto-close-epic` violated CLAUDE.md rule (b) requiring human confirmation for epic closes, and the script's `grep -v` pipeline crashed under `set -euo pipefail`. Path C dropped T7 + T8 entirely; surfacing of the deferral state is delegated to a follow-up bead for `/clavain:status` (F4, filed in T8 below).

**Prior Learnings:**
- `docs/solutions/best-practices/multi-step-cli-init-rollback-clavain-20260215.md` — multi-step bd CLI sequences with rollback on failure. Relevant for T6 (state-field installation) — if any `bd set-state` fails mid-sequence, leave previous fields set rather than try to roll back.

---

## Must-Haves

**Truths** (observable behaviors):
- Future readers of `.19.1`/`.19.2`/`.19.8`/`.19.9` understand the deferral state without needing to chase brainstorms or PRDs
- bd state fields on `.19.10` (`deferral_check_in`, `deferral_deadline`, `decision_authority_primary`, `decision_authority_backup`, `auto_revert_action=surface-forced-reentry`) record the active-deferral parameters for any future tool to read
- A follow-up bead (F4) is filed to enhance `/clavain:status` to read those fields and surface deferral state — actual surfacing implementation lands separately
- D2 (sylveste-5p7s) bead body specifies the full eval protocol with pre-registered decision rule (<5% / 5-15% / >15% headroom branches) and the d2_result state-field contract that future surfacing reads

**Artifacts** (files with specific exports):
- `.beads/issues.jsonl` — regenerated after all bead updates

**Key Links** (connections where breakage cascades):
- `.19.10` final notes ⇒ point to PRD + brainstorm + state-field protocol + F4 follow-up bead (so future ops can find the cadence without reading PRD)
- `.19.8` closing note ⇒ links to `.19.10` (not the PRD path — durability)
- `.19.1` body ⇒ explicit pre-registration that ≥1 active mitigation (off-policy randomization OR manual-override weighting) is required before `.19.3` LoRA training; eval-split-only is necessary but not sufficient
- `d2_result` state field on `.19.10` ⇒ future `/clavain:status` reads this (F4) and surfaces forced re-entry when value is `kill-epic`

---

## Sequence

F1 → F3 → F2 → finalize. F1 lands deferral state visibly; F3 installs enforcement teeth so the deferral has consequences; F2 files D2 as the parallel epic-survival check; finalize regenerates JSONL and commits everything in one commit.

---

### Task 1: Update .19.1 body — v0=β, blocked on .19.9 + 4 sprints, mitigation pre-registration

**Files:**
- bd update: `sylveste-s3z6.19.1` (description + notes)

**Step 1: Read current body**
Run: `bd show sylveste-s3z6.19.1 2>&1 | head -40`
Expected: shows current "Microrouter design doc + paper deep-read" framing (pre-deferral)

**Step 2: Update body via `bd update --notes` (idempotent — guard with date prefix)**
```bash
if bd show sylveste-s3z6.19.1 | grep -q "2026-05-06: Reframed for deferred-β architecture"; then
  echo "already updated"
  exit 0
fi
bd update sylveste-s3z6.19.1 --notes "$(cat <<'EOF'
2026-05-06: Reframed for deferred-β architecture per sylveste-s3z6.19.10.

v0 architecture is β (NOT α). The .19.8 α commit is shelved; β becomes v0 in time-shifted form once .19.9 (interspect outcome-column extension) ships and 4 weeks of pass@1 telemetry accumulate (volume thresholds in PRD: ≥80/cell stable-7, ≥20/cell long-tail).

Status: BLOCKED on .19.9 + 4 weeks accumulation. Soft deadline 2026-06-30; auto-close-epic if deadline passes without human re-decision.

When resumed, .19.1 design phase MUST address:
- Heuristic-stratified eval split (REQUIRED diagnostic): per-strata recall on heuristic-easy and heuristic-hard cases, both reported.
- ≥1 active mitigation (REQUIRED corrective): off-policy randomized traffic 5-10% (preferred, locus = .19.5 resolver), OR manual-override weighting if .19.9 captures override telemetry. Eval-split-only is necessary but not sufficient — flagged as P0 by 2026-05-06 PRD review (heuristic-controlled circularity).
- Hard fallback: if neither active mitigation viable by .19.5 design, escalate to γ-contingency.

Decision space narrowed (per 2026-05-05 D2 brainstorm): once D2 heuristic-baseline measurement (sylveste-5p7s) lands, .19.1 routes to one of: (a) close epic if <5% headroom, (b) stable-7-only learned router if 5-15% headroom, (c) content-feature classifier if >15% headroom or long-tail-concentrated.

PRD: docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md
Decision brainstorm: docs/brainstorms/2026-05-06-microrouter-architecture-decision-brainstorm.md
EOF
)"
```

**Step 3: Verify**
Run: `bd show sylveste-s3z6.19.1 | grep -c "deferred-β\|.19.10\|2026-06-30"`
Expected: ≥1 match per substring

<verify>
- run: `bd show sylveste-s3z6.19.1 | grep -q "deferred-β"`
  expect: exit 0
- run: `bd show sylveste-s3z6.19.1 | grep -q "2026-06-30"`
  expect: exit 0
</verify>

---

### Task 2: Update .19.2 body — label source = pass@1 from .19.9, blocked

**Files:**
- bd update: `sylveste-s3z6.19.2` (notes — append, preserving existing 2026-05-04 inference-path content)

**Step 1: Idempotency guard — skip if already done**
```bash
if bd show sylveste-s3z6.19.2 | grep -q "2026-05-06: Reframed for deferred-β"; then
  echo "already updated"
else
  EXISTING=$(bd show sylveste-s3z6.19.2 | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')
  bd update sylveste-s3z6.19.2 --notes "${EXISTING}

2026-05-06: Reframed for deferred-β per sylveste-s3z6.19.10.

Label source: pass@1 from .19.9 (interspect outcome-column extension), NOT judge labels. Means corpus build is per-task pass@1 outcome, not per-task-text → judge-recommended-tier.

Status: BLOCKED on .19.9 + 4 weeks accumulation per PRD operational definitions (≥80 verdicts/cell stable-7, ≥20 verdicts/cell long-tail; AND-gate on calendar AND volume).

When resumed, MUST include the off-policy-randomized fraction (5-10%) of routing-eligible calls so corpus contains non-heuristic-controlled outcomes. Without that, β anchor reduces to 'imitate the heuristic' per 2026-05-06 PRD review P0.

PRD: docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md"
fi
```

**Step 2: Verify**
Run: `bd show sylveste-s3z6.19.2 | grep -q "pass@1 from .19.9"`
Expected: exit 0

<verify>
- run: `bd show sylveste-s3z6.19.2 | grep -q "pass@1 from .19.9"`
  expect: exit 0
- run: `bd show sylveste-s3z6.19.2 | grep -q "off-policy"`
  expect: exit 0
</verify>

---

### Task 3: Update .19.8 closing note — α v0 commit shelved per .19.10

**Files:**
- bd update: `sylveste-s3z6.19.8` (notes — append, don't replace existing notes)

**Step 1: Read existing notes**
Run: `bd show sylveste-s3z6.19.8 2>&1 | tail -10`

**Step 2: Append closing note (idempotent)**
```bash
if bd show sylveste-s3z6.19.8 | grep -q "2026-05-06 closing note: α v0 commit shelved"; then
  echo "already updated"
else
  EXISTING=$(bd show sylveste-s3z6.19.8 | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')
  bd update sylveste-s3z6.19.8 --notes "${EXISTING}

2026-05-06 closing note: α v0 commit shelved per sylveste-s3z6.19.10 (architecture deferred to β after .19.9 + 4 sprints of pass@1 telemetry). Bead stays CLOSED — design revision contributions (P0-B/C/D/E absorption + 2K threshold + judge-anchor protocol) are still load-bearing for downstream design when work resumes, but the chosen v0 architecture (α) was deferred. See sylveste-s3z6.19.10 for the deferral PRD and active-deferral mechanics.

Future readers: do not interpret 'CLOSED' as 'shipped to production' for this bead. The architecture decision was reopened by sylveste-s3z6.19.10."
fi
```

**Step 3: Verify**
Run: `bd show sylveste-s3z6.19.8 | grep -q "shelved per sylveste-s3z6.19.10"`
Expected: exit 0

<verify>
- run: `bd show sylveste-s3z6.19.8 | grep -q "shelved per sylveste-s3z6.19.10"`
  expect: exit 0
</verify>

---

### Task 4: Update .19.9 body — critical-path role + op definitions cross-ref

**Files:**
- bd update: `sylveste-s3z6.19.9` (notes — append)

**Step 1: Update (idempotent)**
```bash
if bd show sylveste-s3z6.19.9 | grep -q "2026-05-06: Elevated to critical-path P0"; then
  echo "already updated"
else
  EXISTING=$(bd show sylveste-s3z6.19.9 | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')
  bd update sylveste-s3z6.19.9 --notes "${EXISTING}

2026-05-06: Elevated to critical-path P0 for entire .19 epic per sylveste-s3z6.19.10 deferral.

Operational requirements pinned by PRD (docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md):
- pass@1 definition: bead clean-close (no defect/regression child within N=4 sprints) + CI pass + sprint reflection verdict
- Volume thresholds for β-readiness: ≥80 verdicts/cell stable-7 agents; ≥20 verdicts/cell long-tail (use_count ≥3)
- Label noise measurement: 200-bead manual relabel sample at end of accumulation AND first sprint check-in; >30% noise → escalate γ
- AND-gate on calendar AND volume (4 weeks AND sufficient volume) — no early-close on bursty weeks
- MUST capture session-level manual-override events (user picked a different model than heuristic chose) — required for caveat-1 active mitigation (manual-override weighting fallback)

Without these in .19.9 schema design, β can't break the heuristic-controlled-circularity P0 from 2026-05-06 brainstorm review."
fi
```

**Step 2: Verify**
Run: `bd show sylveste-s3z6.19.9 | grep -q "critical-path P0"`
Expected: exit 0

<verify>
- run: `bd show sylveste-s3z6.19.9 | grep -q "critical-path P0"`
  expect: exit 0
- run: `bd show sylveste-s3z6.19.9 | grep -q "manual-override"`
  expect: exit 0
</verify>

---

### Task 5: Update .19.10 final notes — PRD path + decision summary + cadence pointers

**Files:**
- bd update: `sylveste-s3z6.19.10` (notes — append, the bead has accumulated brainstorm + strategy notes already)

**Step 1: Append final notes (idempotent)**
```bash
if bd show sylveste-s3z6.19.10 | grep -q "2026-05-06 plan + execute summary"; then
  echo "already updated"
else
  EXISTING=$(bd show sylveste-s3z6.19.10 | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')
  bd update sylveste-s3z6.19.10 --notes "${EXISTING}

2026-05-06 plan + execute summary:
- PRD: docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md
- Brainstorm: docs/brainstorms/2026-05-06-microrouter-architecture-decision-brainstorm.md (with Review Caveats)
- Plan: docs/plans/2026-05-06-microrouter-deferral-operationalization.md
- Synthesis (brainstorm review): docs/research/flux-drive/2026-05-06-microrouter-architecture-decision-brainstorm-a4dbb251/synthesis.md
- Synthesis (PRD review): docs/research/flux-drive/2026-05-06-microrouter-architecture-deferral-prd-34386262/synthesis.md
- Synthesis (plan review): docs/research/flux-drive/2026-05-06-microrouter-deferral-operationalization-e2f9b102/synthesis.md
- Children: sylveste-1mp6 (F1 bead-body cascade), sylveste-5p7s (F2 D2 sibling), sylveste-ngft (F3 keep-alive state fields), <F4-bead-id> (follow-up — /clavain:status surfacing of deferral state)

Active-deferral mechanics: bd state fields on this bead (deferral_check_in=2026-05-20, deferral_deadline=2026-06-30, decision_authority_primary=arouth1, decision_authority_backup=arouth1, auto_revert_action=surface-forced-reentry). Plan review chose Path C — drop the original session-start hook design (SessionStart hooks can't block sessions per Claude Code spec; auto-close-epic violated CLAUDE.md rule b). Surfacing of these state fields is delegated to F4 follow-up bead enhancing /clavain:status."
fi
```

**Step 2: Verify**
Run: `bd show sylveste-s3z6.19.10 | grep -q "2026-05-06 plan + execute summary"`
Expected: exit 0

<verify>
- run: `bd show sylveste-s3z6.19.10 | grep -q "2026-05-06 plan + execute summary"`
  expect: exit 0
- run: `bd show sylveste-s3z6.19.10 | grep -q "Path C"`
  expect: exit 0
</verify>

---

### Task 6: Set bd state fields on .19.10 for active-deferral

**Files:**
- bd state: `sylveste-s3z6.19.10` (5 new state fields)

**Step 1: Set fields**
```bash
bd set-state sylveste-s3z6.19.10 deferral_check_in=2026-05-20
bd set-state sylveste-s3z6.19.10 deferral_deadline=2026-06-30
bd set-state sylveste-s3z6.19.10 decision_authority_primary=arouth1
bd set-state sylveste-s3z6.19.10 decision_authority_backup=arouth1
bd set-state sylveste-s3z6.19.10 auto_revert_action=surface-forced-reentry
```

Value changed from `auto-close-epic` (rejected during plan review per CLAUDE.md rule b — closing an epic requires human confirmation) to `surface-forced-reentry` (when deadline passes, /clavain:status surfaces the bead with a "deadline exceeded — re-enter via /clavain:route" notice; close still requires explicit human action).

**Step 2: Verify**
Run:
```bash
for k in deferral_check_in deferral_deadline decision_authority_primary decision_authority_backup auto_revert_action; do
  echo "$k: $(bd state sylveste-s3z6.19.10 $k)"
done
```
Expected: each field has its set value (no "no $k state set" lines)

<verify>
- run: `bd state sylveste-s3z6.19.10 deferral_check_in | grep -q "2026-05-20"`
  expect: exit 0
- run: `bd state sylveste-s3z6.19.10 deferral_deadline | grep -q "2026-06-30"`
  expect: exit 0
- run: `bd state sylveste-s3z6.19.10 auto_revert_action | grep -q "surface-forced-reentry"`
  expect: exit 0
</verify>

---

### Task 7: ~~Write scripts/deferral-check.sh~~ — REMOVED (Path C)

Plan review found this task introduced 3 P0s (script crashed under set -euo pipefail; SessionStart hooks can't block sessions per Claude Code spec; auto-close-epic violated CLAUDE.md). The hook script is dropped entirely. State fields from T6 are the durable record; surfacing is delegated to F4 below.

---

### Task 7 (DELETED — see plan revision note in header)

The original T7 wrote `scripts/deferral-check.sh`. Plan review found 3 P0s in this script (crashed under set -euo pipefail; auto-close-epic violated CLAUDE.md rule b; `bd close` failure-masking corrupted state). Path C drops the script entirely.

---

### Task 8 (REPLACED — file F4 follow-up bead for /clavain:status surfacing)

**Files:**
- bd create: new F4 bead under `.19` epic

**Step 1: Dedup**
Run: `bd search "clavain status deferral surfacing" --status=open 2>&1 | head -3`
Expected: no match

**Step 2: Create F4 bead**
```bash
bd create --title "[microrouter] F4: /clavain:status surfacing of deferral state on .19.10" \
  --type task --priority 2 \
  --description "Enhance /clavain:status to read bd state fields on sylveste-s3z6.19.10 and surface deferral state. Read fields: deferral_check_in, deferral_deadline, decision_authority_primary, decision_authority_backup, auto_revert_action, d2_result. Output should distinguish: (a) deferral healthy (today < check_in), (b) check-in due (today >= check_in, < check_in+7d), (c) check-in overdue (>=7d, <14d) — show 'extend or re-enter' nudge, (d) check-in stale (>=14d) — surface BLOCKING-style notice in status, (e) deadline approaching (today within 7d of deadline), (f) deadline exceeded — surface forced-reentry notice ('Run /clavain:route sylveste-s3z6.19.10 — deadline passed'). Also: if d2_result=kill-epic, surface forced-reentry regardless of date. Acceptance: /clavain:status output, when run with current state fields on this machine, includes a microrouter section with the relevant tier per the date." \
  --notes "Filed 2026-05-06 from sylveste-s3z6.19.10 plan review (Path C). Replaces the original session-start hook design which couldn't actually block sessions per Claude Code spec, and violated CLAUDE.md rule b (auto-close-epic). /clavain:status is operator-invoked, so it's the right surface for active-deferral notices. Generic enough to serve future deferrals across the bead graph if state-field convention is reused." 2>&1 | tee /tmp/f4-bead.txt
F4_ID=$(grep -oE 'sylveste-[a-z0-9]+' /tmp/f4-bead.txt | head -1)
echo "F4 bead: $F4_ID"
bd update "$F4_ID" --parent sylveste-s3z6.19
```

F4 is a sibling under `.19`, NOT a child of `.19.10`. Once F4 lands, it serves all future deferrals on the bead graph, not just this one — scoping to `.19.10` would narrow it artificially.

<verify>
- run: `test -f /tmp/f4-bead.txt`
  expect: exit 0
- run: `grep -qE 'sylveste-[a-z0-9]+' /tmp/f4-bead.txt`
  expect: exit 0
</verify>

---

### Task 8b (DELETED — original T8 was the SessionStart hook wiring; dropped per Path C)

The original T8 wired `scripts/deferral-check.sh` as a SessionStart hook. SessionStart hooks can't block sessions per Claude Code spec; surfacing now lives in F4 (`/clavain:status` enhancement). The original script-creation block below is preserved as a record of the rejected approach but is NOT part of the active plan:

```bash
# ARCHIVED — DO NOT EXECUTE — see plan revision header for why
```bash
cat > scripts/deferral-check.sh <<'SCRIPT'
#!/usr/bin/env bash
# Microrouter deferral check-in hook (sylveste-s3z6.19.10).
# Surfaces notices when check-in due, escalates if past, blocks if 14d+ past, auto-closes epic past deadline.
# Wired into .claude/settings.json SessionStart hooks. Exits 0 unless BLOCKING (exit 2).
# Reads-only by default; auto-close fires only when deadline passed AND auto_revert_action=auto-close-epic.

set -euo pipefail

BEAD="sylveste-s3z6.19.10"
TODAY="$(date +%Y-%m-%d)"
TODAY_EPOCH=$(date -d "$TODAY" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$TODAY" +%s 2>/dev/null) || exit 0

# Read state — silent if bd unavailable (don't break sessions over a missing tool)
command -v bd >/dev/null 2>&1 || exit 0

CHECK_IN=$(bd state "$BEAD" deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1)
DEADLINE=$(bd state "$BEAD" deferral_deadline 2>/dev/null | grep -v "no .* state set" | head -1)
AUTO_REVERT=$(bd state "$BEAD" auto_revert_action 2>/dev/null | grep -v "no .* state set" | head -1)
D2_RESULT=$(bd state "$BEAD" d2_result 2>/dev/null | grep -v "no .* state set" | head -1)
PHASE=$(bd state "$BEAD" phase 2>/dev/null | grep -v "no .* state set" | head -1)

# If bead is already done, nothing to check
[[ "$PHASE" == "done" ]] && exit 0

# D2 result published — force re-entry on next session
if [[ "$D2_RESULT" == "kill-epic" ]]; then
  echo "[microrouter] D2 verdict: kill-epic. Run /clavain:route sylveste-s3z6.19.10 to confirm and close .19 epic." >&2
fi

# Deadline passed → auto-close-epic if configured
if [[ -n "$DEADLINE" ]]; then
  DEADLINE_EPOCH=$(date -d "$DEADLINE" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$DEADLINE" +%s 2>/dev/null) || DEADLINE_EPOCH=0
  if [[ "$DEADLINE_EPOCH" -gt 0 && "$TODAY_EPOCH" -gt "$DEADLINE_EPOCH" ]]; then
    if [[ "$AUTO_REVERT" == "auto-close-epic" ]]; then
      echo "[microrouter] BLOCKING: deferral_deadline ($DEADLINE) exceeded; auto-closing .19 epic per sylveste-s3z6.19.10 PRD." >&2
      bd close sylveste-s3z6.19 --reason "deferral deadline ($DEADLINE) exceeded; auto-close per sylveste-s3z6.19.10" 2>/dev/null || true
      bd set-state "$BEAD" phase=done 2>/dev/null || true
      exit 2
    fi
    echo "[microrouter] BLOCKING: deferral_deadline ($DEADLINE) exceeded; manual re-decision required. Run /clavain:route $BEAD." >&2
    exit 2
  fi
fi

# Check-in date passed → nag/escalate
if [[ -n "$CHECK_IN" ]]; then
  CHECK_IN_EPOCH=$(date -d "$CHECK_IN" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$CHECK_IN" +%s 2>/dev/null) || CHECK_IN_EPOCH=0
  if [[ "$CHECK_IN_EPOCH" -gt 0 && "$TODAY_EPOCH" -ge "$CHECK_IN_EPOCH" ]]; then
    DAYS_PAST=$(( (TODAY_EPOCH - CHECK_IN_EPOCH) / 86400 ))
    if [[ "$DAYS_PAST" -ge 14 ]]; then
      echo "[microrouter] BLOCKING: deferral check-in $DAYS_PAST days overdue. Run /clavain:route $BEAD or bd set-state $BEAD deferral_check_in=YYYY-MM-DD." >&2
      exit 2
    elif [[ "$DAYS_PAST" -ge 7 ]]; then
      echo "[microrouter] deferral check-in $DAYS_PAST days overdue (escalating to BLOCK at 14d). Run /clavain:route $BEAD or extend." >&2
    else
      echo "[microrouter] deferral check-in due ($CHECK_IN). /clavain:route $BEAD to re-confirm or bd set-state $BEAD deferral_check_in=<+2w>." >&2
    fi
  fi
fi
exit 0
SCRIPT
chmod +x scripts/deferral-check.sh
```

**Step 3: Verify script runs without error against current state**
Run: `bash scripts/deferral-check.sh; echo "exit=$?"`
Expected: exit=0 (today is 2026-05-06; check_in is 2026-05-20 — not yet due)

**Step 4: Test escalation logic with synthetic past date**
```bash
# Save current
ORIG=$(bd state sylveste-s3z6.19.10 deferral_check_in | head -1)
# Set to 8 days ago — should trigger 7-day nag
bd set-state sylveste-s3z6.19.10 deferral_check_in=$(date -d "8 days ago" +%Y-%m-%d 2>/dev/null || date -v-8d +%Y-%m-%d)
output=$(bash scripts/deferral-check.sh 2>&1)
echo "$output" | grep -q "escalating to BLOCK at 14d" && echo "✓ 7d nag works" || echo "✗ 7d nag broken: $output"
# Restore
bd set-state sylveste-s3z6.19.10 deferral_check_in="$ORIG"
```

<verify>
- run: `test -x scripts/deferral-check.sh`
  expect: exit 0
- run: `bash scripts/deferral-check.sh`
  expect: exit 0
- run: `bash -n scripts/deferral-check.sh`
  expect: exit 0
</verify>

---

### Task 8: Wire scripts/deferral-check.sh into .claude/settings.json

**Files:**
- Modify: `.claude/settings.json` (add SessionStart hook entry)

**Step 1: Read current SessionStart hooks**
Run: `jq '.hooks.SessionStart' .claude/settings.json`

**Step 2: Append a new hook entry to SessionStart**
Use `jq` to append (idempotent: check if already present).
```bash
# Idempotent add — only insert if not present
if ! jq -e '.hooks.SessionStart[]?.hooks[]?.command | select(test("deferral-check.sh"))' .claude/settings.json >/dev/null 2>&1; then
  tmp=$(mktemp)
  jq '.hooks.SessionStart += [{"matcher":"startup|resume|clear","hooks":[{"type":"command","command":"bash -c \"cd \\\"$PROJECT_DIR\\\" && bash scripts/deferral-check.sh 2>&1 || true\"","timeout":5}]}]' \
    .claude/settings.json > "$tmp" && mv "$tmp" .claude/settings.json
  echo "added deferral-check.sh hook"
else
  echo "already present"
fi
```

**Step 3: Verify JSON is valid**
Run: `jq empty .claude/settings.json && echo "valid JSON"`
Expected: prints "valid JSON"

**Step 4: Verify hook is present**
Run: `jq -r '.hooks.SessionStart[].hooks[].command' .claude/settings.json | grep deferral-check.sh`
Expected: matches the deferral-check.sh command line

# end ARCHIVED — verify block above no longer applies, do not execute
```

---

### Task 9: Refresh F2 (sylveste-5p7s) bead body with d2_result state-field contract

**Files:**
- bd update: `sylveste-5p7s` (notes — append the post-PRD-review patch details)

**Step 1: Append (idempotent)**
```bash
if bd show sylveste-5p7s | grep -q "2026-05-06 post-PRD-review patch"; then
  echo "already updated"
else
  EXISTING=$(bd show sylveste-5p7s | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')
  bd update sylveste-5p7s --notes "${EXISTING}

2026-05-06 post-PRD-review patch: d2_result state-field contract added (originally framed as 'active alert mechanism' via session-start hook; the hook was dropped in plan-review Path C, but the d2_result contract is preserved for the F4 /clavain:status surfacing follow-up).

When D2 result is computed, the runner MUST:
1. Set bd state field on parent: bd set-state sylveste-s3z6.19.10 d2_result=<verdict> where <verdict> ∈ {kill-epic, narrow-stable-7, content-feature-classifier, inconclusive}
2. Append result summary to .19.10 notes via bd update --notes
3. Result doc lands at docs/research/2026-MM-DD-microrouter-heuristic-baseline-d2.md (confirm dir convention if PR review challenges it)

The F4 follow-up (sylveste-<id>) reads d2_result during /clavain:status invocation; if the verdict is kill-epic, the status output surfaces a forced re-entry notice until the operator runs /clavain:route sylveste-s3z6.19.10 to close the epic.

Decision rule pre-registered (PRD §F2 + Operational Definitions):
- <5% headroom (bootstrap 95% CI lower-bound) → close .19 epic via 19-CLOSE bead
- 5-15% concentrated in stable-7 → narrow .19.1 to stable-7-only learned router
- >15% OR concentrated in long-tail → .19.1 resumes as content-feature classifier"
fi
```

**Step 2: Verify**
Run: `bd show sylveste-5p7s | grep -q "d2_result="`
Expected: exit 0

<verify>
- run: `bd show sylveste-5p7s | grep -q "kill-epic"`
  expect: exit 0
- run: `bd show sylveste-5p7s | grep -q "active alert mechanism"`
  expect: exit 0
</verify>

---

### Task 10: Mark child beads in_progress → ready-for-close (state hygiene)

**Files:**
- bd state: F1/F2/F3 children (sylveste-1mp6, sylveste-5p7s, sylveste-ngft)

**Step 1: Set state**
After each child's acceptance criteria are met by tasks 1-9, mark them `phase=executed` so the sprint reflect step can close them cleanly.
```bash
# F1: bead-body cascade — all 5 sub-edits done by tasks 1-5
bd set-state sylveste-1mp6 phase=executed
# F3: keep-alive mechanics — state fields by task 6, hook by 7-8
bd set-state sylveste-ngft phase=executed
# F2: D2 sibling — bead body refresh by task 9
bd set-state sylveste-5p7s phase=executed
```

**Step 2: Verify**
Run: `for c in sylveste-1mp6 sylveste-5p7s sylveste-ngft; do echo "$c: $(bd state $c phase | head -1)"; done`
Expected: all show `executed`

<verify>
- run: `bd state sylveste-1mp6 phase | grep -q executed`
  expect: exit 0
- run: `bd state sylveste-5p7s phase | grep -q executed`
  expect: exit 0
- run: `bd state sylveste-ngft phase | grep -q executed`
  expect: exit 0
</verify>

---

### Task 11: Regenerate .beads/issues.jsonl

**Files:**
- Modify: `.beads/issues.jsonl`

**Step 1: Run export**
```bash
bd export -o .beads/issues.jsonl 2>&1 | tail -3
```

**Step 2: Verify**
Run: `grep -c "sylveste-s3z6.19.10" .beads/issues.jsonl`
Expected: ≥1 (epic + events)

<verify>
- run: `grep -q "sylveste-s3z6.19.10" .beads/issues.jsonl`
  expect: exit 0
- run: `grep -q "sylveste-1mp6" .beads/issues.jsonl`
  expect: exit 0
</verify>

---

### Task 12: Single sprint-close commit

**Files:**
- All changed files: brainstorm + PRD + plan + synthesis + scripts/deferral-check.sh + .claude/settings.json + .beads/issues.jsonl

**Step 1: Inspect diff**
Run:
```bash
git status --short
git diff --stat
```

**Step 2: Stage only the files this sprint touched**
```bash
git add docs/brainstorms/2026-05-06-microrouter-architecture-decision-brainstorm.md
git add docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md
git add docs/plans/2026-05-06-microrouter-deferral-operationalization.md
git add docs/research/flux-drive/2026-05-06-microrouter-architecture-decision-brainstorm-a4dbb251/
git add docs/research/flux-drive/2026-05-06-microrouter-architecture-deferral-prd-34386262/
git add docs/research/flux-drive/2026-05-06-microrouter-deferral-operationalization-e2f9b102/
git add .beads/issues.jsonl
```

(No `scripts/deferral-check.sh` and no `.claude/settings.json` — those were dropped in Path C.)

**Step 3: Commit**
```bash
git commit -m "$(cat <<'EOF'
feat(microrouter): defer architecture to β with active-deferral mechanics

sylveste-s3z6.19.10 — architecture decision: defer to β after .19.9 ships
+ 4 sprints of pass@1 telemetry. α (the .19.8 v0 commit) is shelved; γ
documented and rejected, preserved as contingency.

Per 2026-05-06 brainstorm + PRD + 2-round flux-drive review:
- Brainstorm review surfaced P0 (β has heuristic-controlled circularity);
  patched as Review Caveats with mitigation pre-registration.
- PRD review surfaced P0 (eval-split-only is thermometer not thermostat);
  patched with co-required mitigations (heuristic-stratified eval +
  off-policy randomization 5-10%), AND-gate sprint-counting,
  auto-close-epic on deadline miss, active-deferral hook with 14d BLOCK
  escalation.

Bead-body cascade absorbed (.19.1/.19.2/.19.8/.19.9). D2 sibling bead
sylveste-5p7s filed with concrete eval protocol + active alert. F1/F2/F3
children: sylveste-1mp6 / sylveste-5p7s / sylveste-ngft.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

**Step 4: Verify**
Run: `git log -1 --format="%h %s" | head -1`
Expected: commit hash + first line of message

<verify>
- run: `git log -1 --format="%s" | grep -q "feat(microrouter)"`
  expect: exit 0
- run: `git log -1 --name-only --format="" | grep -q "docs/prds/2026-05-06-microrouter-architecture-deferral-prd.md"`
  expect: exit 0
</verify>

---

## Final verification (Must-Haves)

Run after Task 12:

```bash
# Truth 1: future readers understand state from bead bodies alone
bd show sylveste-s3z6.19.1 | grep -q "deferred-β" && echo "✓ .19.1"
bd show sylveste-s3z6.19.8 | grep -q "shelved per sylveste-s3z6.19.10" && echo "✓ .19.8"
bd show sylveste-s3z6.19.9 | grep -q "critical-path P0" && echo "✓ .19.9"

# Truth 2: state fields on .19.10 are set
for k in deferral_check_in deferral_deadline decision_authority_primary decision_authority_backup auto_revert_action; do
  v=$(bd state sylveste-s3z6.19.10 "$k" | head -1)
  echo "$k: $v"
done

# Truth 3: F4 surfacing follow-up bead exists
F4_ID=$(grep -oE 'sylveste-[a-z0-9]+' /tmp/f4-bead.txt 2>/dev/null | head -1)
[[ -n "$F4_ID" ]] && bd show "$F4_ID" | grep -q "/clavain:status surfacing" && echo "✓ F4 bead $F4_ID"

# Truth 4: D2 bead has eval protocol + d2_result contract
bd show sylveste-5p7s | grep -q "kill-epic" && echo "✓ D2 bead"

# Artifact: jsonl regenerated
test -f .beads/issues.jsonl && echo "✓ jsonl"
```
