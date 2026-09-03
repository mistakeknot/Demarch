# Goal c60de386 — pilot journal (Pattern F hardening)

Successor to goal 1b53da77. Orchestrating session aa2bb078 (Fable 5.1) runs the release and the bookkeeping; each pilot is orchestrated by its own fresh headless session (`claude -p --model fable --session-id <id>`) that receives the contract block plus a brief, writes the plan, lints it, spawns a Sonnet executor and an Opus validator, and records verdicts with the register script. Pilot session ids are the lane keys for `interstat/scripts/profile.py --session <id>`.

## Release (main thread, needs the signer host)

interstat 0.3.3 published from zklw (`ic publish 0.3.3`; canary + post-release probe green; bump commit 72bc2c9 on interstat main). Mac refreshed (`claude plugin marketplace update`, `claude plugin update interstat@interagency-marketplace`); the cached `scripts/analyze.py`, `scripts/cost.py`, `scripts/profile.py`, `skills/cost/SKILL.md` are byte-identical to interstat origin/main. Running sessions keep executing 0.3.2 until restarted.

## Pilots

| Pilot | Work | Session | Executor commit | Validator | Gauge defects (plan author's) | Beyond the gauge | Register rows |
|---|---|---|---|---|---|---|---|
| A | `scripts/pattern-f-verdict.sh` + bats: one interspect evidence row per verdict, kind replay/independent, read-back or non-zero | 39c8935e | 5f49c43 (strike 1) | PASS (strike 1); re-ran all 5 VERIFY steps, files byte-identical to the plan | none | 8 bullets, 5 registered as independent FAIL rows: `_interspect_sanitize` returns empty on injection-like phrases ("ignore previous", "system:") so the library inserts context='' with rc 0 and the script exits 4; default `--db` fallback untested and anchored on the script's repo, so a plugin-cache install exits 3; rows carry the library's 48h `quarantine_until`, so interspect's calibration queries cannot see them for two days; `--list` is not safely parseable when a note carries a tab or newline; no supersede semantics and second-resolution ordering. Not registered (gauge-design observations): the live-register VERIFY line passes vacuously on an empty register; nothing calls the script yet; `--commit` is shape-checked only | 7 (all rc 0; sqlite count 7) |
| B | `hooks/gauge-gate-executor-spawn.sh` + hooks.json PreToolUse `Task\|Agent` + bats: plan-gauge-lint blocks executor spawns whose plan fails | 2f8dafde | 102d0d0 (strike 1) | PASS (strike 1); all 7 VERIFY lines re-run (gate bats 5/5, hooks_json bats 6/6, pytest 12 passed, shellcheck clean) | none | 10 bullets, 7 registered: a gate refusal is recorded nowhere (no evidence row, unlike every other Pattern F verdict); the marker match is `^`-anchored so an indented or backticked marker slips through, and there is no converse check; jq missing on PATH allows silently; linter notes are discarded on the allow path so a degraded dry run ("old_string did not match") reads as clean; `REPO:` is prompt-controlled with a PWD fallback; nothing tests that the harness still honors the legacy `{decision:block}` shape; the missing-linter / rc>=2 / no-GAUGE-line branches are untested. Not registered: the 30s timeout is a silent-allow path; the unanchored matcher also fires on TaskStop (harmless); no in-repo emitter carries the marker yet (pilot C wires the contract). Orchestrator reported two linter facts: that `--repo-root` must precede the plan path (wrong: pilot D's validator and a direct test showed either order works; the hook comment and amendment that repeated it were corrected in 827f7da), and that the linter has no new-file grammar, so `Create` blocks sit outside the gauge (right, Sylveste-yibw.14) | 9 (first batch rc 127: zsh did not word-split an unquoted command string; the one permitted retry wrote the rest, rc 0) |
| C | `skills/executing-plans/references/pattern-f-contracts.md` + pointers from the skill and `/execute-plan`: executor and validator prompts, BEYOND THE GAUGE as a named output, register write as the last step | d758b3e9 | d0f6c51 (strike 2) | PASS (strike 1); all 7 VERIFY lines re-run at the commit | one, the plan author's: the brief said two structural tests fail at HEAD, but a third (`test_hook_entry_points_have_set_euo_pipefail`) fails since pilot B's hook landed with `set -uo pipefail` on the orchestrating session's own instruction; the executor stopped without committing, the orchestrator added the deselect, re-linted, re-spawned once | 6 bullets, 5 registered: **executor drift**, the committed file moves one parenthesis on line 45 against the plan's block while the report claimed verbatim (confirmed by diff from the main thread); the `/execute-plan` pointer is a bare repo-relative path where sibling commands use `${CLAUDE_PLUGIN_ROOT}`; the doc overstates what the linter reads (it ignores Preconditions, Commit, the trailer, and new-file blocks); the register's default path is stated under the wrong root; line 17 carries backslash-escaped backticks inside code spans. Not registered: no structural test pins the doc's cited paths. All five go to pilot D | 7 (all rc 0) |
| D | fix-forward: hook gains `set -euo pipefail` with guards so allow/block behavior is unchanged; contract doc corrected (paren, backticks, gauge scope, register path); `/execute-plan` pointer uses `${CLAUDE_PLUGIN_ROOT}` | 0f950073 | a5acc3b (strike 1) | PASS (strike 1); all 13 VERIFY lines re-run, commit touches exactly the 3 paths; structural 898 passed | none (orchestrator noted the linter without `--repo-root` reports every old_string as not found and still exits 0, so it re-ran with the flag) | 6 registered: the `findings=$(printf \| awk)` line was the one pipeline left unguarded under `set -e` (theoretical: awk exits 0 with no match, reproduced blocking correctly, guarded anyway in 7f2fa44); the doc's "ignores Preconditions and Commit" wording overstates, the linter has no section awareness at all; the linter's path regex allowlists extensions so a `.bats` edit target inherits the previous file's path; line 17 lost its copyable literal; the `${CLAUDE_PLUGIN_ROOT}` pointer sits in prose where nothing expands it; the hook's comment about `--repo-root` ordering is false. Doc wording items carried to Sylveste-yibw.14's note | 8 (all rc 0) |
| main | rule-4 follow-up: `\|\| true` on the findings pipeline | aa2bb078 | 7f2fa44 | none (main thread; bats 5/5, refusal blocks) | one, the orchestrator's own: a sed with `\|` as delimiter failed on the `\|\|` in its replacement, the commit was empty, and a PASS row had already been written against a5acc3b; corrected by an independent FAIL row naming the superseding commit, then the real PASS row | n/a | 3 (1 premature, 1 correction, 1 real) |

Executor runs this goal: 6 spawns, 5 commits, 1 refusal on a plan-author gauge defect (counts against the orchestrating session's brief), 1 executor drift (one parenthesis, text, caught by the validator's diff). Verbatim application 4/5 on committed runs; code-correct 5/5.

## Close-out

Register read back at close (`sqlite3 ... where event='pattern_f_verdict' group by session, role, kind`): 39c8935e 1/1/5, 2f8dafde 1/1/7, d758b3e9 1/1/5, 0f950073 1/1/6 (executor replay / validator replay / validator independent), plus aa2bb078 2 replay + 1 independent for the main-thread follow-up. Every executor and validator run in the window has a row; no verdict in this journal exists only here.

Gate report, both metrics, execution lanes only: main-thread share of generated tokens 93 / 98 / 80 / 92 %, of cost 81 / 75 / 64 / 63 % (A/B/C/D). Neither reached 50%; both are scale-invariant and neither moved with the thing that changed. What changed: orchestrator context per turn 344K → 71–82K, orchestrator cost per pilot about $3.8 → $3 while carrying the whole loop in a fresh session. The amendment in `commands/model-routing.md` proposes replacing the share gates with an absolute pair (context per turn, orchestrator dollars per pilot) for mk to rule on.

## Confounds

- Pilot A's first attempt stopped at turn 8 with "You've reached your Fable limit" (this account's Fable weekly bucket was at 96% before the goal). mk switched accounts (`/login`); the pilot was resumed in the same session id on Fable. Both attempts count in the 39c8935e lane; the resume re-sent the session's context once more than a clean run would have.

## Token profile (execution lanes only; melange/review workflows excluded)

Filled from `profile.py --session <id>` after each pilot. Comparison point from goal 1b53da77: main-thread share of API-equivalent cost 65%, share of generated tokens 92%, orchestrator context 344K per turn over 38 turns, $19 main + $10 executors/validators = $29 for five executor runs.

| Pilot | lane | msgs | output | cache read | ctx/msg | $ equiv |
|---|---|---|---|---|---|---|
| A | main (Fable 5.1; 8 turns before the limit + 5 after resume) | 12 | 40K | 0.8M | 80K | 4 |
| A | executor (Sonnet 5) | 13 | 9K | 0.7M | 57K | 0.5 |
| A | validator (Opus 5) | 11 | 14K | 0.5M | 53K | 1 |

| B | main (Fable 5.1) | 10 | 40K | 0.7M | 80K | 3 |
| B | executor (Sonnet 5) | 12 | 4K | 0.6M | 52K | 0.5 |
| B | validator (Opus 5) | 14 | 8K | 0.7M | 56K | 1 |

Pilot B shares, execution lanes only: cost **75%**, generated tokens **98%**; whole run $4.

| C | main (Fable 5.1) | 16 | 40K | 1.2M | 82K | 3 |
| C | executor (Sonnet 5, two spawns) | 33 | 10K | 1.7M | 56K | 1 |
| C | validator (Opus 5) | 22 | 8K | 1.2M | 59K | 1 |

Pilot C shares, execution lanes only: cost **64%**, generated tokens **80%**; whole run $5 including the second executor spawn.

| D | main (Fable 5.1) | 14 | 30K | 0.9M | 71K | 3 |
| D | executor (Sonnet 5) | 20 | 4K | 1.1M | 56K | 0.5 |
| D | validator (Opus 5) | 23 | 7K | 1.4M | 66K | 1 |

Pilot D shares, execution lanes only: cost **63%**, generated tokens **92%**; whole run $5.

Demonstrated refusal (main thread, real PreToolUse payload naming the linter's GAUGE001 fixture plan; the hook run from the committed tree with `CLAUDE_PLUGIN_ROOT` set):

```
{"decision":"block","reason":"pattern-f gauge gate: plan-gauge-lint refused .../fixture/bad.md: GAUGE001  line 20: verify expects no output, but the plan's own emitted text matches"}
```

The same payload naming the clean fixture plan printed nothing and exited 0.

Pilot A shares, execution lanes only: cost **81%**, generated tokens **93%**. Both shares are higher than 1b53da77's, and the absolute cost of the run is a fifth of one 1b53da77 pilot: $5 for a plan, an executor, a validator, and seven register rows, against roughly $6 per pilot before. The share metric is scale-invariant, so shrinking the orchestrator from 344K to 80K per turn cut the main lane's cost by an order of magnitude and moved the share the wrong way, because the executor and validator lanes shrank too. Read with the absolute column or not at all.

## Verdict register

Read back from the live register, never transcribed: `bash scripts/pattern-f-verdict.sh --list` (all rows) at close.
