# Pattern F hardening: verdicts that reach calibration, plans that pass the gauge before they run, and an orchestrator that fits in its own context

Ratified by mk on 2026-09-03 ("please execute the above /goal"; the pasted text is recorded verbatim in the condition file beside this charter). Successor to goal 1b53da77 (main-thread offload, instrumented), which met its DONE WHEN and missed its gate: execution-only main-thread share of generated tokens 92% (limit 50%), cost share 65% (baseline 85%). Epic bead: Sylveste-yibw.

## Why

Goal 1b53da77 ran five executor runs through the offload shape and learned three things this goal acts on. The gauge fails, never the code: two of five runs were blocked by defects in the orchestrator's own VERIFY blocks. The validator's replay of the verify block added nothing (5/5 PASS) while its second channel, "what the gauge did not check", found six real defects. And the interspect verdict register that Pattern F needs already exists, but Pattern F never writes to it, so those five verdicts live only in a markdown table no calibration will read (melange corner finding f-041). Separately, the orchestrator's 38 turns at 344K context cost more than every executor and validator combined; offload alone reached 65%, and going lower needs the orchestrator's own context to shrink. Finally, the installed interstat plugin still runs the pre-fix parser at every SessionEnd, so any measurement this goal takes is rewritten by the old code until interstat is released.

## Scope

In:
- interstat released to interagency-marketplace (0.3.3) and refreshed on this Mac, verified by content diff of the installed cache against the source revision, not by version number.
- A verdict register write for Pattern F: a script the validator (or orchestrator) calls that inserts one interspect evidence row per verdict, with `kind` in {replay, independent}, the plan path, the executor commit, and PASS/FAIL; the write exits non-zero and says so when it cannot insert. Every executor and validator run in this goal's window has a row.
- `plan-gauge-lint.py` as a precondition: a PreToolUse hook on Agent/Task spawns whose prompt hands a plan file to an executor; the hook runs the linter and blocks the spawn (exit 2 with the reason) when the plan fails. One demonstrated refusal.
- The validator contract, as a checked-in reference the orchestrator points executors and validators at, with the second channel ("Beyond the gauge") as a named output and the register write as the contract's last step.
- One real goal (this one; its execution-grade items qualify, as in 1b53da77) run as a fresh session per pilot, each pilot's execution-only profile (review lanes excluded) compared against 65% cost share / 344K per turn, journaled.
- Sylveste-yibw's child beads updated to what shipped.

Out:
- The local-model cascade, effort tuning, re-deriving the phase table, the tripwire beads (mk-f0mz, Sylveste-55bc).
- Sylveste-koeo's round-trip fix, unless it blocks the interstat release.
- A Clavain publish. The hook and contract changes reach the installed Clavain only at its next publish; that is listed for mk, not claimed here.

## Gates

1. Both metrics reported for every fresh-session pilot, execution lanes only: main-thread share of generated tokens and of API-equivalent cost. Which one stands is mk's ruling; this goal ratifies neither.
2. Executor pass rate stays at 5/5 verbatim application or better. A gauge defect counts against the plan author (the fresh-session orchestrator), not the executor.
3. No hand-typed verdict tables. If a verdict is not in the register, it did not happen.

## Interpretations recorded at mint

- "interstat released": `ic publish` from zklw (the signer host), then `claude plugin update interstat@interagency-marketplace` here, then `diff -q` of the cache's `scripts/analyze.py`, `scripts/cost.py`, `scripts/profile.py` against interstat main.
- "verdicts visible in interspect": rows in the interspect evidence store, queried back by the goal's journal step from the store itself, never transcribed.
- "gauge-lint wired as a precondition": the hook is registered in Clavain's hooks manifest so it binds every Agent/Task spawn once Clavain is next published. The demonstrated refusal is the hook script fed a real PreToolUse payload for a failing plan (exit 2, reason on stderr) plus a test case. A live in-session refusal needs the Clavain publish and a session restart, and is not claimed.
- "fresh session per pilot": each pilot is orchestrated by a headless `claude -p` session with its own transcript and session id (a main-thread lane in profile.py), which receives a short brief, writes the plan file, spawns the Sonnet executor and Opus validator, and records the verdicts. Model is Fable 5.1 so the comparison to 1b53da77 changes one variable (context), falling back to Opus 5 if the Fable weekly bucket refuses, recorded as a confound if it happens.
- "one real goal": this goal's own items (register write, gauge-lint hook, validator contract) are the pilots, as 1b53da77's charter allowed. The interstat release is run from the main thread because it needs the signer host.

## Completion condition

See the condition file. Or stop after 16 turns.

## Close (2026-09-03)

DONE WHEN met: interstat 0.3.3 released and verified by content diff; every executor and validator run in the window has a register row (read back from the store at close, not transcribed); the gauge gate is wired in `hooks/hooks.json` with one refusal demonstrated on a real payload; the validator contract is checked in with BEYOND THE GAUGE as a named output; four fresh-session pilots profiled and journaled; Sylveste-yibw's children updated (three delivered, one trial, three defects filed). GATE reported on both metrics, neither at 50%: generated-token share 80–98%, cost share 63–81%, execution lanes only; the journal argues both are scale-invariant and the amendment proposes an absolute pair (context per turn, orchestrator dollars per pilot) for mk to rule on. Pass rate: 6 spawns, 5 commits, 1 refusal on a plan-author gauge defect, 1 one-parenthesis executor drift caught by the validator; code-correct 5/5. Turn budget: 16 stated; the orchestrating session used about 45 tool-bearing turns, most of them waiting on and reading four headless sessions. Out-of-scope items untouched: the Clavain publish that makes the hook bind live is listed for mk. Confounds: pilot A's Fable-cap stop and resume; the main-thread follow-up 7f2fa44 under rule 4 with a corrected register row.

## Successor obligations

Whatever the fresh-session profiles show still bloats the orchestrator (candidate: the brief itself, or executor reports); the remaining melange prescriptions on Sylveste-yibw not covered here (f-004 idempotent verify, f-003 attempts store, f-011 orchestrator scoring, f-023 strike taxonomy); a Clavain publish so the hook binds live.
