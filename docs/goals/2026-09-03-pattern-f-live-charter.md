# Pattern F live: refusals recorded, notes survive, new files gauged, plugin shipped

Ratified by mk on 2026-09-03 ("please execute the above /goal"; the pasted text is recorded verbatim in the condition file beside this charter). Successor to goal c60de386 (Pattern F hardening), which shipped the verdict register, the gauge gate, and the contracts but left them inert: the gate binds only after a Clavain publish, refusals leave no row, the interspect sanitizer drops any note carrying an injection-like phrase to an empty context, and the linter cannot see new-file blocks. Epic bead: Sylveste-yibw; children .12, .13, .14.

## Why

Four pilots of evidence say the offload shape works and that its second channel (the validator's BEYOND THE GAUGE) is where the cost is earned. None of that reaches a live session until the plugin ships, and two of the register's paths are lossy: a gate refusal is a verdict that is never written, and a validator note that happens to quote an injection phrase is written as nothing. Both new-file pilots of the last goal ran ungauged in the sense that mattered because `Create` blocks sit outside the linter's virtual tree.

## Scope

In:
- `hooks/gauge-gate-executor-spawn.sh` records every refusal as one evidence row (`--role gate --kind gate --verdict FAIL`, the reason as note) through `scripts/pattern-f-verdict.sh`, and prints the block decision whether or not the row lands (.12).
- `scripts/pattern-f-verdict.sh` pre-flights its context through the library's sanitizer and, on rejection, stores the note and criterion base64-encoded with a marker so the text survives byte-for-byte; `--list` decodes and emits one line per row whatever the note contains (.13 sanitizer half).
- `scripts/plan-gauge-lint.py` parses `Create \`path\` with:` blocks into the virtual tree (and attributes `.bats` paths) so GAUGE001 fires on a new-file plan whose verify contradicts its own content (.14).
- Clavain published from zklw and refreshed on this Mac, verified by content diff of the installed cache against Clavain main.
- One real plan (the contracts document catching up with the three changes above) run through `/execute-plan` in a fresh headless session started after the publish, with a seeded gauge defect so the live gate's refusal is demonstrated, then corrected and passed; every row read back from the register.
- Profiles per pilot in absolute terms (orchestrator context per turn, orchestrator dollars) with both shares for continuity.

Out: the meter trio, tests-on-commit, tripwires, effort tuning, share-gate changes, any interspect plugin change (the sanitizer stays as it is; the verdict script adapts to it).

## Gates

1. Quarantine is mk's ruling. Rows keep the 48h default; the journal states which rows calibration can see at close.
2. Absolute numbers reported per pilot; shares printed for continuity, never as the gate.
3. Executor pass rate 5/5 code-correct; a gauge defect counts against the plan author. The seeded defect in the live run is the orchestrating session's on purpose and is journaled as seeded.
4. No hand-typed verdict tables.

## Interpretations recorded at mint

- "stored intact": `pattern-f-verdict.sh --list` prints the note byte-for-byte; the row's context column may hold it encoded, with `note_enc` naming the encoding, so the register never carries the raw phrase into interspect's own readers.
- "never fails open": the refusal row is written before the decision is printed, inside a guard, so a missing register, a missing script, or a library error changes only stderr.
- "live session": a headless `claude -p` session started after the publish, so its hooks come from the refreshed plugin cache; the gate's refusal appears both as a blocked spawn in that session and as a gate row in the register.
- "through /execute-plan": the session invokes the `clavain:execute-plan` command with the plan path and follows the offload contracts it points at.

## Completion condition

See the condition file. Or stop after 12 turns.

## Close (2026-09-03)

DONE WHEN met: clavain 0.6.304 and 0.6.305 published from zklw and refreshed here, content-diffed identical to main; Sylveste-yibw.12 closed (25077ad, 6305a89, cacef81) and .14 closed (187ff9d, 6305a89); .13's sanitizer half closed in its notes, its quarantine half explicitly open for mk; the live session (pilot G on 0.6.304) had its first executor spawn refused by the gate with GAUGE001, the gate wrote its own register row, the orchestrator corrected one `Expected:` line, and the re-spawn committed be532a5 with a validator PASS, all journaled with profiles; the epic's children reflect what shipped and .15 holds the residual validator findings. GATE held: quarantine untouched; absolutes per pilot (orchestrator 56–121K per message, $2–12; whole runs $3–13) with shares for continuity (cost 47–88%, tokens 85–99%); 5 spawns, 4 commits, 1 live refusal on the seeded defect, code-correct 4/4; no transcribed verdicts. Turn budget overrun: about 40 tool-bearing turns against 12 stated, a third of them on a duplicate-instance incident of the orchestrating session's own making (journal, Confounds). Interpretations held as recorded at mint; one addition: the gate row carries no goal field, so per-goal register queries join it by session.

## Successor obligations

Sylveste-yibw.15 (Create grammar and verdict-script residuals; the `grep -r X .` scope gap; `--list` resilience to a redacted base64 payload); mk's quarantine ruling on .13; the interspect calibration side has never read a `pattern_f_verdict` row, so the register is written but not yet consumed; the launch discipline for headless pilots is now a memory note, not a script.
