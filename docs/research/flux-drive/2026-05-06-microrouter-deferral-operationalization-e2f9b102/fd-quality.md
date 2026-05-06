# fd-quality findings — microrouter deferral operationalization plan

Reviewed against: `session-freshness-gate.sh`, `.claude/settings.json` (live), git log, scripts/ naming corpus.

---

## P0 findings

### P0-A: `grep -v "no .* state set" | head -1` kills the script under `pipefail` when no state is set

In `deferral-check.sh` lines for `CHECK_IN`, `DEADLINE`, `AUTO_REVERT`, `D2_RESULT`, `PHASE`:

```bash
CHECK_IN=$(bd state "$BEAD" deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1)
```

Under `set -euo pipefail`, when `bd state` returns `"no deferral_check_in state set"` (the normal cold-start case), `grep -v` finds zero passing lines and exits 1. `pipefail` propagates that non-zero exit code out of the pipeline. In bash, **a command substitution in an assignment does NOT mask the exit code of the pipeline inside it** — the assignment itself exits 1, which triggers `errexit`. Confirmed empirically: the script exits 1 with no output on first run before state is set.

Fix: append `|| true` to each state-read pipeline, or use a `|| :` guard:
```bash
CHECK_IN=$(bd state "$BEAD" deferral_check_in 2>/dev/null | grep -v "no .* state set" | head -1 || true)
```
This is exactly the fix that `|| true` would provide; confirmed it produces an empty string safely. All five state-read lines need this.

### P0-B: T8 hook wrapper swallows `exit 2` — BLOCKING behavior is silently disabled

The hook command in T8 is:
```
bash -c "cd \"$PROJECT_DIR\" && bash scripts/deferral-check.sh 2>&1 || true"
```

The `|| true` at the end means the hook always exits 0 regardless of whether `deferral-check.sh` exits 2. The BLOCKING path (`exit 2`) becomes indistinguishable from a notice — it prints a stderr message but the hook runner sees a clean exit. If Claude Code or the hook orchestrator uses the hook exit code to enforce blocking, this defeats the entire F3 acceptance criterion "if 14 days pass, hook auto-promotes to BLOCKING status."

Fix: remove `|| true` from the wrapper. The script already has graceful fallback for `bd unavailable` (`command -v bd || exit 0`) and `date` failures (`|| exit 0`). Non-zero exit should propagate for the blocking case.

---

## P1 findings

### P1-A: Script naming is `noun-verb` — project corpus is majority `verb-noun`

The proposed name `deferral-check.sh` is `noun-verb`. Surveying all 27 `.sh` files in `scripts/`:
- `verb-noun` (dominant, ~19 scripts): `audit-roadmap-beads`, `backfill-secret-scan`, `check-go-module-paths`, `check-rig-drift`, `clean-plugin-cache`, `consolidate-module-docs`, `generate-module-roadmaps`, `gen-gemini-commands`, `install-index-hooks`, `register-mcp`, `sync-research-index`, `sync-roadmap-json`, `sync-secret-scan-baseline`, `test-compact-freshness`, `validate-plugin`, etc.
- `noun-noun` (minor, ~2): `gemini-hook-bridge`, `skill-prefix-router-hook`
- `noun-adjective-noun` (one-off): `session-freshness-gate`

Proposed name `deferral-check.sh` uses none of these patterns and inverts the dominant order. Rename to `check-deferral.sh` to match the majority convention.

### P1-B: T8 hook command quoting style is inconsistent with existing convention

Existing `settings.json` hook commands use bash single-quoted strings for the inner `bash -c` argument:
```json
"command": "bash -c 'cd \"$PROJECT_DIR\" && bash scripts/session-freshness-gate.sh ...'"
```

T8's jq filter produces:
```json
"command": "bash -c \"cd \\\"$PROJECT_DIR\\\" && bash scripts/deferral-check.sh 2>&1 || true\""
```

Both resolve to the same runtime string, but the output is the double-quote style with nested escapes. The entry is readable in `jq` output but inconsistent with how all three existing `SessionStart` entries are formatted in the live file. The install step should produce single-quote style to stay consistent.

### P1-C: T8 introduces `"timeout": 5` — no existing hook entry uses this field

All three existing `SessionStart` hook objects have exactly two keys: `"type"` and `"command"`. The T8-generated entry adds `"timeout": 5`. If this is a valid field in Claude Code's hook schema it should be applied consistently; if it is not a recognized field it is silently ignored but creates a divergence that will confuse future readers comparing entries.

The plan does not justify adding `timeout` here while leaving the three existing entries without it, including `session-freshness-gate.sh` which does Dolt health checks and could equally benefit from a timeout.

Either drop `"timeout"` to match convention, or add a note that this is intentional and update the existing entries.

### P1-D: T12 verify block tests for staged files after commit — will always fail

```bash
- run: `git status --short | grep -E "^[AM]"`
  expect: exit 0
```

After a successful `git commit`, no files are staged. `git status --short` shows nothing matching `^[AM]` and `grep` exits 1. The verify block's `expect: exit 0` is wrong. This verify check does not test anything useful post-commit. Replace with a check that confirms the commit message contains the expected subject, e.g.:
```bash
- run: `git log -1 --format="%s" | grep -q "feat(microrouter)"`
  expect: exit 0
```

---

## P2 findings

### P2-A: T3/T4/T5 note-append `sed` extraction produces leading blank line when notes are empty

The pattern:
```bash
bd update <bead> --notes "$(bd show <bead> | sed -n '/^NOTES$/,/^LABELS:/p' | sed '1d;$d')

2026-05-06 appended text"
```

If `bd show` output has no `NOTES` section (bead has no prior notes), the `sed` pipeline outputs nothing, leaving `--notes` receiving a value that starts with a bare newline before the appended text. The resulting notes body has an unwanted leading blank line. Minor cosmetic issue; no data loss. Fix: strip leading newlines from the sed output or use a conditional.

### P2-B: T3 note-append reads notes via `sed -n '/^NOTES$/,/^LABELS:/p'` — fragile if schema changes

Tasks 3, 4, and 5 extract existing notes from `bd show` output using a regex range over `^NOTES$` and `^LABELS:`. If the `bd show` format changes (e.g., `LABELS` moves above `NOTES`, or the section separator changes), the extraction silently produces empty string and the update becomes a replacement rather than an append. No guard checks whether extraction succeeded before writing.

The plan's Prior Learnings note references `multi-step-cli-init-rollback-clavain-20260215.md` for T6 but does not apply the same caution here. A `--append` flag on `bd update` (if it exists in the CLI) would be safer; if not, at least confirm extraction returned non-empty before proceeding.

### P2-C: Final verification block is almost entirely redundant with task-level `<verify>` blocks

The "Final verification" section re-checks:
- `.19.1 deferred-β` — already in T1 `<verify>`
- `.19.8 shelved per sylveste-s3z6.19.10` — already in T3 `<verify>`
- `.19.9 critical-path P0` — already in T4 `<verify>`
- `test -x scripts/deferral-check.sh` — already in T7 `<verify>`

The two genuinely independent checks in the final block are: (a) `bash scripts/deferral-check.sh` run against real post-T6 state (T7 verify also runs the script but against state that may not have the T6 fields set yet, depending on execution order), and (b) the `jq -e '.hooks.SessionStart[].hooks[].command | select(test("deferral-check.sh"))'` check which uses a different expression than T8's verify. Both are worth keeping. The four redundant checks could be replaced with a note "see task-level verify blocks" to reduce noise.

### P2-D: T7 Step 1 label ("Write the failing test first") is misleading

Step 1 is titled "Write the failing test first" (TDD language) but immediately says "Skip a separate test file; the verify block at end runs the script with current state." This creates a false affordance — an executor reading the step heading will pause expecting to write a test. The step should be retitled "No separate test file needed — verify block at end covers this" or dropped entirely.

### P2-E: T9 verify checks for `"d2_result="` but the appended content writes `d2_result=<verdict>` as prose, not a state-field assignment

```bash
- run: `bd show sylveste-5p7s | grep -q "d2_result="`
  expect: exit 0
```

The note text in T9 includes the string `d2_result=<verdict>` as an example command in prose. The grep will match that prose occurrence. The verify is technically correct (the string will be present) but it conflates "the notes contain an example of the command" with "the field is actually set." The state field `d2_result` is only set at D2 result publication time (by the D2 runner), not by T9. No action needed beyond clarifying the verify description.

---

## P3 findings

### P3-A: PRD F2 acceptance criterion says "new bead sylveste-s3z6.19.12" — plan treats 5p7s as pre-existing

The PRD says "New bead created: `sylveste-s3z6.19.12` (or next available index under `.19`)." The plan's Task 9 is titled "Refresh F2 (sylveste-5p7s) bead body" and treats 5p7s as already existing (it does — confirmed via `bd show`). The plan's Architecture section says "D2 follow-up bead refresh." The bead exists with parent `.19.10` (not `.19` directly). Neither document explicitly acknowledges that the PRD AC was satisfied by pre-creation. A one-line note in T9 ("5p7s was pre-created as the F2 bead during brainstorm; this task is a refresh, not a create") would close the apparent mismatch.

### P3-B: T7 synthetic test uses `✓`/`✗` emoji in echo output

```bash
echo "$output" | grep -q "escalating to BLOCK at 14d" && echo "✓ 7d nag works" || echo "✗ 7d nag broken: $output"
```

The project convention (CLAUDE.md, AGENTS.md) avoids emojis in files unless explicitly requested. The final verify block also uses `✓`. These are in bash test snippets inside the plan document (not in the script itself), so the impact is cosmetic, but they are inconsistent with the no-emoji convention.

### P3-C: T6 `decision_authority_backup=arouth1` is identical to primary — no comment in plan

The plan sets `decision_authority_backup=arouth1` with no inline comment. The PRD explains "single-operator project; backup defaults to primary but field is explicit." Without that explanation in the plan's step, an executor might flag this as a copy-paste error. Add a brief inline comment, e.g. `# single-operator project; backup intentionally mirrors primary`.

---

## Verdict

NEEDS_ATTENTION — Two P0 blockers: `grep -v | head -1` exits 1 under `pipefail` on cold-start (kills the script before it does anything), and the `|| true` wrapper in T8's hook command silently swallows the BLOCKING exit code, making F3's escalation enforcement inert.
