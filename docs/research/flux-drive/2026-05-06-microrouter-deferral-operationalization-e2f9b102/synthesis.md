---
target: docs/plans/2026-05-06-microrouter-deferral-operationalization.md
bead: sylveste-s3z6.19.10
review_quality: balanced
review_date: 2026-05-06
agents: [fd-correctness, fd-safety, fd-quality]
---

# Synthesis — microrouter deferral operationalization plan

## Verdict

**NEEDS_ATTENTION — 3 P0s, ~5 P1s, several P2/P3.** The plan has correctness and safety bugs in the hook script that would make F3's enforcement entirely inert from day one. Two of the P0s also expose a structural mismatch: F3's "active enforcement with teeth" design assumed SessionStart hooks can block sessions; they can't. The third P0 violates CLAUDE.md's explicit rule that closing an epic requires human confirmation.

## P0 findings (3)

### P0.1 — Hook script crashes silently on first run (fd-correctness, fd-quality)

The state-read pattern `bd state $BEAD field 2>/dev/null | grep -v "no .* state set" | head -1` exits with code 1 when the field is unset (grep filters everything, returns 1; pipefail propagates; command substitution under `set -e` aborts). Verified empirically against the actual `bd` binary. Result: script crashes at the first `bd state` read on a field that's not yet populated (e.g., `d2_result` is never set by any task in this plan). The hook wrapper `|| true` masks the crash from Claude Code, so sessions continue normally — but **all governance logic never runs**. F3 is documentation, not enforcement.

**Minimal fix:** append `|| VAR=""` to each of the 5 state reads in T7's script.

### P0.2 — BLOCKING mechanism is structurally inert (fd-quality, fd-safety)

Two compounding issues:
1. T8 wraps the hook in `|| true`. Even if the script exits 2, the wrapper exits 0 — Claude Code never sees BLOCKING.
2. SessionStart hooks are documented as non-blocking (`"Can block? No"` per Claude Code plugin docs). Only UserPromptSubmit can actually block a session.

The "14-day BLOCKING escalation" + "deadline BLOCKING" language in the PRD/plan describes a mechanism that doesn't exist. The hook can only nag via stderr; it cannot prevent /sprint or /work from running.

**Two fix paths:**
- **Restructure**: move the hook to UserPromptSubmit (actually blocks), modify the script to emit on user prompt rather than session start. Adds scope.
- **Downgrade**: drop BLOCKING/exit-2 language from PRD and plan; the hook is advisory; /clavain:route surfacing is the actual enforcement (operator can't proceed past route without addressing the deferral state).

### P0.3 — Auto-close-epic violates CLAUDE.md and corrupts state (fd-correctness, fd-safety)

CLAUDE.md explicitly says auto-proceed on bead-close is allowed only when **none** of these apply: "(a) bead has open children, (b) closing an epic, (c) acceptance criteria reference unobserved work, (d) user explicitly held the close." The plan auto-closes `sylveste-s3z6.19` (an epic) on deadline pass — violates rule (b) directly.

Worse: the `.19` epic has 4+ open P0/P1 children. `bd close sylveste-s3z6.19` fails without `--force` due to open-children gate. The script wraps it in `2>/dev/null || true`, swallowing the failure, then sets `phase=done` on `.19.10`. Result: epic stays OPEN, but `phase=done` makes the hook exit early on subsequent runs — permanently masking the deadline-exceeded state.

**Fix:** remove `bd close` from the hook entirely. Replace with: set a `deadline_exceeded=true` state field on `.19.10`; `/clavain:route` surfaces it as forced re-entry; human runs the close (or extends, or re-decides). Aligns with CLAUDE.md.

## P1 findings (5)

1. **T3/T4/T5/T9 double-append on retry** (fd-correctness P1.1) — sed-extract-and-append pattern includes previously-appended text on second run; verify checks are presence-only so doubled content passes silently. Fix: date-prefix guard.
2. **T12 verify is inverted** (fd-correctness P1.3, fd-quality P1-D) — `git status --short | grep -E "^[AM]"` exits 0 on FAILED commit, 1 on SUCCESS. Backwards.
3. **T2 silently drops existing `.19.2` notes** (fd-correctness P2.1) — heredoc replace, no read-existing step. Loses the 2026-05-04 inference-path + privacy-audit + scheduling-constraint notes. Fix: use append pattern like T3/T4/T5.
4. **Naming convention violation** (fd-quality P1-A) — `deferral-check.sh` should be `check-deferral.sh` per scripts/ majority verb-noun convention.
5. **Trust boundary** (fd-safety P1) — `.claude/settings.json` is committed; the deferral hook is per-operator metadata. Should live in `.claude/settings.local.json` (gitignored) instead.

## P2 findings

- Hook timeout=5 may be insufficient for Dolt startup if a check-in lands during a Dolt cold start (fd-safety)
- `decision_authority_backup=arouth1` (same as primary) — placeholder; harmless until extended (fd-correctness P3.1)
- `phase=executed` on F3 (sylveste-ngft) is set at sprint close on 2026-05-06 but the hook's first real test (check-in date 2026-05-20) hasn't occurred yet — F3 acceptance is asserted on observation that hasn't happened (fd-correctness P3.2)
- Hook format inconsistency (escape style) vs existing `.claude/settings.json` entries (fd-quality P1-B/C)

## Recommended next actions

The P0s require either:

**Path A — Minimal fixes, accept advisory-only enforcement:**
- Fix P0.1 (5 `|| VAR=""` appends)
- Drop BLOCKING/exit-2 language from PRD + plan; hook is advisory + /clavain:route surfacing is the enforcement (P0.2)
- Remove `bd close` from hook; replace with `deadline_exceeded` state field + /clavain:route surfacing (P0.3)
- Fix P1.1 (date-prefix guards), P1.2 (T12 verify), P1.3 (T2 append pattern)
- Apply P1.4 (rename to `check-deferral.sh`) and P1.5 (move to `.claude/settings.local.json`)

This keeps scope contained. Eval-split-only-style fix: address what's broken minimally; don't redesign.

**Path B — Restructure F3 for real enforcement:**
- Move hook to UserPromptSubmit (can actually block)
- Modify script to emit on prompt, not session start
- Re-design escalation to UserPromptSubmit semantics
- All P0/P1 fixes from Path A still required

Adds scope; arguably the right answer if the deferral truly needs hard enforcement. But fd-safety's CLAUDE.md observation argues that destructive enforcement (auto-close-epic) was never the right model anyway — surfacing + manual decision is correct.

**Path C — Reduce F3 scope: drop the hook entirely:**
- Keep T6 state fields (deferral_check_in / deferral_deadline / etc.)
- Drop T7 (script) and T8 (hook wiring)
- Add a manual /clavain:status enhancement (separate bead) that reads deferral state and surfaces it
- Most aligned with CLAUDE.md "human in the loop for destructive ops"

Lightest weight; honest about what hooks can/cannot do.

## Per-agent reports

- `fd-correctness.md` — 1 P0 + 3 P1 + 3 P2/P3
- `fd-safety.md` — 2 P0 + ≥2 P1 (Dolt concurrency, TZ, timeout)
- `fd-quality.md` — 2 P0 + 4 P1 (naming, hook format, timeout, T12 verify) + minor
