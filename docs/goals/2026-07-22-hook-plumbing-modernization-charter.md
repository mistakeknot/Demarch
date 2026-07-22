---
artifact_type: goal-charter
bead: Sylveste-sqq
complexity: C2
---

# Goal Charter — Hook Plumbing Modernization (Goal A of parallel pair)

## Why (leverage)

The test-baseline goal (4aecb49d) spent a day fixing shell-quoting and
portability bugs in hook plumbing — a bug class Claude Code 2.1.139's
exec-form hooks (`args: string[]`, no shell) eliminate structurally.
`continueOnBlock` lets PostToolUse gate failures feed back for
self-correction instead of dead-ending. Bundled here because they share a
file lane: Sylveste-zlc's legacy `/tmp` sideband retirement and
Sylveste-23k's `CLAUDE_CODE_SESSION_ID` keying rewrite the same
interline/clavain-cli/interphase hook internals the exec-form migration
touches. Runs in PARALLEL with Goal B (a3a+1zu+hygiene, separate session)
under the partition mk confirmed 2026-07-22.

## Parallel-session coordination (binding)

- Both sessions run on the Mac (one shared Dolt — never split bead writes
  across machines mid-flight; bkrh lesson).
- This session owns the hook-plumbing lane: all plugin hook definitions
  (hooks.json / plugin hook configs), interline + clavain-cli sideband
  code, interphase hook libs. Reserve via interlock at session start.
- Goal B commits but does NOT publish plugins. This goal's final publish
  wave ships both sessions' changes: `git pull` before publishing, absolute
  `--cwd` paths only (Sylveste-1zu wart), canaries per publish.

## Scope

**In:**
- Inventory every hook entry across os/Clavain and interverse/* plugins:
  form (shell-string vs exec-form), convertibility, continueOnBlock fit.
- Convert all convertible entries to exec-form; each remaining shell-form
  entry gets a stated reason in the inventory.
- Apply continueOnBlock to PostToolUse gates where failure should feed back
  to the model (e.g. auto-publish gate failures).
- Sylveste-zlc: remove the legacy /tmp/clavain-bead sideband path from
  interline + clavain-cli after the keyed replacement is in place.
- Sylveste-23k: key the sideband envelope via CLAUDE_CODE_SESSION_ID in
  Bash subprocess env.
- Test suites green (interphase, Clavain, interline, interflux) on the Mac;
  zklw spot-verification after push.
- Final publish wave for all touched plugins (including Goal B's committed
  script fixes), release canaries passing.
- Close Sylveste-sqq, Sylveste-zlc, Sylveste-23k.

**Out:**
- Goal B's lane: a3a date-fallback scripts, intercore 1zu, epic hygiene.
- Hook semantic changes beyond invocation form and continueOnBlock.

## Completion condition (literal, for /goal)

The hook plumbing modernization is complete when ALL of the following are
surfaced in-session: (1) a committed hook inventory listing every hook
entry across os/Clavain and the interverse plugins with its invocation form,
where every convertible entry is converted to exec-form args and every
remaining shell-form entry carries a stated reason; (2) continueOnBlock
applied to the PostToolUse gates named in the inventory as feedback-worthy,
with diffs surfaced; (3) the legacy /tmp/clavain-bead sideband path removed
from interline and clavain-cli with the CLAUDE_CODE_SESSION_ID-keyed
replacement in place, surfaced by grep showing no remaining legacy-path
references outside changelogs and docs; (4) test suites for interphase,
Clavain, interline and interflux surfaced passing on the Mac with zero
failures, and a zklw run of the same suites surfaced passing after push;
(5) all touched plugins published via ic publish with absolute cwd paths
after a git pull that includes Goal B's commits, each release canary
surfaced passing; (6) beads Sylveste-sqq, Sylveste-zlc and Sylveste-23k
closed with the work cited, and bd export to .beads/issues.jsonl committed
and pushed with beads_jsonl_dolt_sync ok surfaced. Or stop after 70 turns
and surface an accounting of converted versus remaining hook entries and
any failing suites.

## Successor obligations

At close, propose a successor per Goal Cadence: remaining CC-digest
candidates (Sylveste-oqo intermux agents-json, Sylveste-nwv publish
tagging), or the next capability digest when the changelog watcher fires.

## Operational amendment (2026-07-22, pre-bind)

mk chose single-session execution with worktree isolation over the
two-session split. Goal B's code items (a3a scripts, 1zu Go+test) run in a
worktree-isolated executor agent (model: sonnet, explicit); ALL bd
operations, the nested os/Skaffen pull, branch merge and the single final
publish wave stay in the main checkout/session. B's publish-deferral clause
is superseded — one publish wave ships everything. Both goal entities
(ceb0f3a6, 48d16471) close from this session. The merged /goal condition is
the union of both charters' conditions with those adjustments.
