---
artifact_type: goal-charter
bead: sylveste-ao0q
complexity: 2
stage: goal-formed
---

# Goal Charter: Post-Publish Plugin Canary — Release Health Probe + Rollback Verb

## Why (leverage)

Successor to goal f16e8021 (publish-pipeline hardening, its recorded
successor ref). That goal made publish *unable to destroy* installed state;
this one makes every release *prove health*. The Sylveste-0lt incident had
two failure surfaces the current flow still only half-covers:

1. **Publish-time state** — now partially covered by the installPath
   assertion, but nothing validates the published artifact itself (schema,
   hook declarations, cache entry integrity). `ic publish doctor` owns 9
   reusable checks (`internal/publish/doctor.go`) that never run at
   publish time.
2. **Next-session load** — the 0lt symptom was the plugin silently failing
   to appear at session start. Nothing watches that surface at all.

interspect precedent: canary machinery exists for routing/skill
modifications (20-use windows, alert thresholds). Releases need the
release-shaped variant — immediate probe + single next-session load check —
not a multi-session window (a release either loads or it doesn't).
interpub is a thin wrapper; all publish logic lives in
`core/intercore/internal/publish/` (Go), so that is the canary's home,
with a session-side hook for the load check.

Classifier: C2 (no override needed — C2/C3 route the same ceremony).

## Scope

**In (mk-ratified shapes: publish-time + session-start probe; loud alert
with human-triggered rollback verb, no auto-rollback):**
1. **Publish-time probe**: after the installPath assertion, `ic publish`
   runs doctor-grade checks scoped to the just-published plugin (plugin
   schema validation, hook declaration correctness, cache entry presence,
   installed/marketplace pointer agreement) and fails loud on any error.
2. **Canary record**: each publish registers a pending release canary
   (plugin, new version, retained prior version, timestamp). Storage
   shape is implementation's call (state file or interspect DB table).
3. **Session-start check**: a hook verifies pending canaries against the
   session's actual plugin-load state — marks the canary passed, or emits
   a loud alert containing the ready-to-run rollback command.
4. **`ic publish rollback <plugin>`**: repoints marketplace.json,
   installed_plugins.json, and cache to the retained prior version (which
   the f16e8021 prune guarantees survives); refuses cleanly when no prior
   version is retained.
5. Tests: probe trip on a synthetic broken publish, canary lifecycle,
   rollback restore + clean refusal, stubbed session-start check.

**Out:**
- Auto-rollback (mk declined — publishes are outward-facing; auto-revert
  can fight a concurrent intentional publish).
- Multi-session canary windows / thresholds (routing-style machinery).
- interspect routing/skill canary refactors.
- The next-session live pass as an in-goal criterion (unobservable within
  the working session — registration is the live evidence; the check
  logic is proven in a stubbed harness).

## Acceptance criteria

1. `go test ./internal/publish/` passes with the new probe, canary, and
   rollback tests; exit 0.
2. A synthetic broken publish trips the probe with a loud error naming
   the failing check.
3. `ic publish rollback` restores prior-version state in a test harness
   and refuses cleanly with no retained prior version.
4. The session-start canary check passes/alerts correctly in a stubbed
   test and is wired into hook registration.
5. A real publish registers a canary record (shown in output).
6. Work committed; sylveste-ao0q closed with evidence.

## Completion condition (literal — handed to /goal)

Post-publish canary complete: ic publish runs a post-release health probe
(plugin schema, hook declarations, cache entry, installed/marketplace
pointer agreement) on the just-published plugin and fails loud on probe
errors; each publish registers a release canary record carrying the
retained prior version; a session-start check marks the canary passed when
the plugin loaded and emits a loud alert containing a ready-to-run ic
publish rollback command when it did not, proven by a stubbed harness
test; ic publish rollback restores the prior version across
marketplace.json, installed_plugins.json, and cache and refuses cleanly
when no prior version is retained; go test ./internal/publish/ passes with
exit 0 shown in surfaced output and the hook-side tests pass; a real
publish registers a canary record shown in surfaced output; work committed
and bead sylveste-ao0q closed with evidence. Or stop after 35 turns.

## Successor obligations

None fixed at formation. Candidates at close: the auto-rollback question
revisits once the manual verb has soak evidence; Sylveste-zlc (legacy
sideband removal) unlocks after this release cycle soaks cleanly.
