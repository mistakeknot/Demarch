---
target: docs/plans/2026-05-06-microrouter-deferral-operationalization.md
bead: sylveste-s3z6.19.10
review_type: correctness
reviewer: Julik (flux-drive correctness)
review_date: 2026-05-06
---

# fd-correctness findings — microrouter deferral operationalization plan

## Invariants under review

These must hold for the plan to be correct:

1. Every `bd update --notes` call either replaces notes deliberately or appends without duplication on retry.
2. `scripts/deferral-check.sh` exits 0 when no action is due, exits 2 when blocking, and never exits 1 unexpectedly.
3. T7 verify `bash scripts/deferral-check.sh` confirms the script is operational before wiring it into the hook.
4. The auto-close path in the script produces the described effect (epic actually closes).
5. T12 verify blocks detect commit failure, not success.
6. T6 partial failures leave no inconsistent state that corrupts downstream logic.

---

## P0 findings

### P0.1 — `scripts/deferral-check.sh`: all five `bd state` reads crash the script under `set -euo pipefail` when the field is unset

**What the script does:**

```bash
CHECK_IN=$(bd state "$BEAD" deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1)
```

**What actually happens when the field is unset:**

`bd state` exits 0 and prints `(no deferral_check_in state set)`. The `grep -v "no .* state set"` pattern matches that line (grep is a substring search; the parens don't protect the match), produces no output, and exits 1. With `set -o pipefail`, the pipeline exit code is 1. Command substitution `$(...)` propagates a non-zero exit to the enclosing `set -e` context, which aborts the script.

Tested against actual bd on this system:

```
$ set -euo pipefail
$ CHECK_IN=$(bd state sylveste-s3z6.19.10 deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1)
$ echo $?   # never reached
# exit 1
```

**Every session start before T6 completes:** crashes on the first read (`CHECK_IN`). After T6 sets the five deferral fields, the script advances past `CHECK_IN`/`DEADLINE`/`AUTO_REVERT` but crashes at `D2_RESULT` — which is never set by any task in this plan. `PHASE` would also crash if `d2_result` happened to succeed; in practice `phase` is already set to `planned` so it would survive, but `d2_result` does not.

**Consequence for T7 verify:**

The plan's T7 Step 3 verify runs `bash scripts/deferral-check.sh` and expects exit 0. It gets exit 1. The verify block fails. If the executor trusts the verify block to confirm the script is working, this is a false negative that blocks the sprint close.

**Consequence for hook behavior:**

The hook command wraps the script in `|| true`, so sessions are not hard-blocked. But all logic in the script — D2 kill-epic notice, deadline check, check-in nag — silently never runs. The governance layer installed by F3 is inert from the moment it is installed.

**Minimal fix:** append `|| VAR=""` to each assignment:

```bash
CHECK_IN=$(bd state "$BEAD" deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1) || CHECK_IN=""
DEADLINE=$(bd state "$BEAD" deferral_deadline 2>/dev/null | grep -v "no .* state set" | head -1) || DEADLINE=""
AUTO_REVERT=$(bd state "$BEAD" auto_revert_action 2>/dev/null | grep -v "no .* state set" | head -1) || AUTO_REVERT=""
D2_RESULT=$(bd state "$BEAD" d2_result 2>/dev/null | grep -v "no .* state set" | head -1) || D2_RESULT=""
PHASE=$(bd state "$BEAD" phase 2>/dev/null | grep -v "no .* state set" | head -1) || PHASE=""
```

The `|| VAR=""` form is transparent: it handles the pipeline-exit-1 case explicitly instead of masking it. Each variable defaults to empty, and all the downstream `[[ -n "$VAR" ]]` guards already handle the empty case correctly.

---

## P1 findings

### P1.1 — T3/T4/T5/T9 double-append on retry (no idempotency guard)

Tasks 3, 4, 5, and 9 append to existing notes using this pattern:

```bash
bd update BEAD --notes "$(bd show BEAD | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')

2026-05-06: NEW TEXT HERE"
```

The sed extraction reads the current NOTES section from the live bead. After the first successful run, the current NOTES section already contains `"2026-05-06: NEW TEXT HERE"`. If the task is retried (e.g., the verify failed for an unrelated reason, or the executor re-ran the block), the extraction captures the already-appended text, and the new text is appended again. Result: the datestamped note appears twice verbatim.

This does not corrupt data irreversibly (bd notes are text, not machine-parsed state), but it does degrade the readability of the bead body and makes the "run idempotently" property of the plan false.

No verify block in T3/T4/T5/T9 checks for duplication — all checks are presence-only (`grep -q "some text"`). A doubled entry still passes all verify checks.

**Minimal fix:** add a guard before each append call:

```bash
bd show BEAD | grep -q "2026-05-06 closing note:" || bd update BEAD --notes "$(...)..."
```

The timestamp prefix is unique enough per task to serve as an idempotency key. T1 and T2 (straight heredoc replacements) are already idempotent by construction.

### P1.2 — `bd close sylveste-s3z6.19` in the auto-close path fails silently with open children

The script's deadline-exceeded block:

```bash
bd close sylveste-s3z6.19 --reason "deferral deadline ($DEADLINE) exceeded; auto-close per sylveste-s3z6.19.10" 2>/dev/null || true
bd set-state "$BEAD" phase=done 2>/dev/null || true
exit 2
```

`bd close` on an epic with open children returns exit 1 and prints `cannot close epic sylveste-s3z6.19: 22 open child issue(s); close children first or use --force to override`. The `2>/dev/null || true` swallows both the error message and the failure. The script then sets `phase=done` and exits 2.

The operator sees `[microrouter] BLOCKING: deferral_deadline (2026-06-30) exceeded; auto-closing .19 epic` in the stderr output and may reasonably conclude the epic was closed. It was not. The `.19` epic remains open with all 22+ children intact. The `phase=done` on `.19.10` prevents this branch from firing again (the `[[ "$PHASE" == "done" ]]` guard at the top), so the auto-close never retries.

**Concrete interleaving that causes the misleading state:**

1. 2026-07-01, session starts.
2. Hook fires. Deadline has passed. `AUTO_REVERT == "auto-close-epic"`.
3. Script prints "BLOCKING: deferral_deadline exceeded; auto-closing .19 epic."
4. `bd close sylveste-s3z6.19` fails (22 open children). Suppressed.
5. `bd set-state sylveste-s3z6.19.10 phase=done` succeeds.
6. Hook exits 2. Session prints the BLOCKING message.
7. Operator reads "auto-closing .19 epic" and moves on, believing the epic closed.
8. `.19` is still open. Future `bd list` or `bd ready` shows `.19` children as available work.

**Minimal fix:** remove `|| true` from the `bd close` call so failure surfaces. Add an explicit check after the call and change the message to reflect actual outcome:

```bash
if bd close sylveste-s3z6.19 --reason "..." 2>&1; then
  echo "[microrouter] BLOCKING: .19 epic auto-closed per deadline." >&2
  bd set-state "$BEAD" phase=done 2>/dev/null || true
else
  echo "[microrouter] BLOCKING: deferral_deadline exceeded. Epic has open children — manual close required. Run: bd close --force sylveste-s3z6.19" >&2
fi
exit 2
```

### P1.3 — T12 verify block is inverted: it asserts staged files exist AFTER the commit

T12 Step 4 verify:

```bash
- run: `git status --short | grep -E "^[AM]"`
  expect: exit 0
```

This runs after `git commit`. After a successful commit, the working tree is clean: `git status --short` produces no `A` or `M` lines. `grep -E "^[AM]"` finds nothing and exits 1. The verify check fails on a successful commit.

Conversely, if the commit failed (e.g., pre-commit hook rejected it), the files would still be staged, `grep` would find them, and the verify would return exit 0 — incorrectly signaling success.

The check is completely inverted. The only useful verify for commit success is checking `git log -1` for the expected commit message, which is already in the Step 4 verify. The `git status --short | grep -E "^[AM]"` check should be removed or moved to Step 2 (before the commit, to confirm files are staged before committing).

---

## P2 findings

### P2.1 — T2 silently drops 904 characters of existing `.19.2` notes from 2026-05-04

T2 uses a straight heredoc replacement:

```bash
bd update sylveste-s3z6.19.2 --notes "$(cat <<'EOF'
2026-05-06: Reframed for deferred-β...
EOF
)"
```

`.19.2` currently has a NOTES section with 904 characters of notes accumulated on 2026-05-04, including:
- The β/α decision input (coverage report MUST report whether ≥2K usable pass@1 examples extracted)
- Inference path details (Claude Max OAuth, ChatGPT Pro OAuth, $50 API-billing safety floor)
- Privacy audit field specification (`judge_backend` per label record)
- Scheduling constraint (off-hours, ≤30% peak rate)

T2 has no Step 1 read-current-notes step and does not attempt to preserve these notes. The replacement silently discards them.

T1 (`.19.1`) is safe because `.19.1` currently has no NOTES section. The intent for T1/T2 appears to be replacement rather than append, but T2's notes contain non-trivial carry-forward decisions that T2's new text does not supersede. The correct behavior for T2 is append (same as T3/T4/T5), not replace.

### P2.2 — `date -d ""` on Linux returns today's epoch, masking empty DEADLINE

In the script:

```bash
TODAY_EPOCH=$(date -d "$TODAY" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$TODAY" +%s 2>/dev/null) || exit 0
```

On Linux, `date -d ""` (empty string) does not fail — it returns the current date's epoch. If `TODAY` were ever empty (e.g., `date +%Y-%m-%d` failed), `TODAY_EPOCH` would be silently set to a valid timestamp rather than triggering `|| exit 0`.

The `date -d "$DEADLINE"` call inside the deadline block has the same property: if `DEADLINE` somehow contains an empty string that slips past the `[[ -n "$DEADLINE" ]]` guard (not possible given current logic, but fragile), it would parse as today's epoch and the `TODAY_EPOCH -gt DEADLINE_EPOCH` comparison would be false. This is a latent edge case rather than an active bug.

**Note:** the `[[ -n "$DEADLINE" ]]` guard does correctly prevent the deadline block from executing when `DEADLINE` is empty, so this is not a live bug in the current script. The risk is introduced if the guard is ever removed or the variable assignment pattern is changed.

### P2.3 — T8 idempotency check does not detect hook added with different command prefix

The idempotency guard:

```bash
if ! jq -e '.hooks.SessionStart[]?.hooks[]?.command | select(test("deferral-check.sh"))' .claude/settings.json >/dev/null 2>&1; then
```

`test("deferral-check.sh")` is a substring match. It correctly detects the hook if the command contains `deferral-check.sh` in any form (absolute path, relative path, `./scripts/deferral-check.sh`, etc.). This is safe for the standard case.

The gap: if the hook was previously added with a different script name or aliased path that doesn't contain the literal string `deferral-check.sh`, the idempotency check would miss it and add a duplicate entry. Given that this script does not yet exist in the repo, this is a future-state concern rather than an active bug.

---

## P3 findings

### P3.1 — `bd state` `decision_authority_primary` and `decision_authority_backup` set to the same value without comment

T6 sets both `decision_authority_primary=arouth1` and `decision_authority_backup=arouth1`. The PRD acknowledges this explicitly ("single-operator project; backup defaults to primary"). This is not an error but it is worth noting that the hook script never reads these fields — they are present as human-readable metadata only. If the script is later extended to contact the backup authority on BLOCKING escalation, the identical values would send the same notification twice.

### P3.2 — T10 marks F3 child (`sylveste-ngft`) `phase=executed` before verifying hook actually fires

T10 sets `phase=executed` on `sylveste-ngft` (F3 keep-alive mechanics) after T6 (state fields) and T7-T8 (hook installation). The F3 acceptance criteria include:

> the check-in is NOT just informational. At each `deferral_check_in` date: (a) session-start hook surfaces "deferral check-in due" + a 1-line action prompt

This is unverifiable at T10 because the hook fires on a future date (2026-05-20). Marking `phase=executed` before the hook has ever fired on a real check-in date means the bead is closed based on "script is installed and runs without error at non-due date," not "hook surfaces notice when check-in is due."

Given P0.1 (the hook crashes before reaching check-in logic), `phase=executed` for `sylveste-ngft` would be set before the hook's core behavior has been verified at all.

---

## Verdict

NEEDS_ATTENTION — P0.1 makes the hook inert on every session start (script crashes silently before any governance logic runs); P1.2 makes the auto-close path emit a misleading success message while the epic remains open; P1.3 makes T12's verify block confirm failure as success. The three fixes are small (append `|| VAR=""` to five lines, rewrite one `if` block around `bd close`, remove one inverted grep check from T12), but without P0.1 fixed, the entire F3 feature is a no-op.
