---
artifact_type: brainstorm
bead: sylveste-g939
stage: discover
parent_epic: sylveste-b1ha
parent_prd: docs/prds/2026-04-21-persona-lens-ontology.md
predecessor: docs/research/f6-measurement-preregistration.md
created: 2026-05-06
---

# F6b Execution Brainstorm — flux-drive Triage Backend Swap + A/B + Ship Decision

## Why a brainstorm at all?

F6a's pre-reg defines **what** F6b measures (review-coverage-per-diff, secondaries, thresholds, anti-patterns) but is silent on **how** F6b implements the two backends, runs the comparison, and handles the second-labeler pass. This brainstorm closes those gaps before `/clavain:write-plan` decomposes the work.

Out of scope: any change to the pre-reg (frozen at commit `d6cf80a8`), the corpus (frozen with V1 labels), or the harness contract (frozen at F6a).

## What We're Building

Four implementation tracks under sylveste-g939:

1. **LegacyBackend** — subprocess wrapper around `/interflux:flux-drive` that runs the real triage + dispatch and returns a `BackendResult`.
2. **OntologyBackend** — new lattice template (`SelectPersonaeForTaskTemplate`) + a thin `OntologyBackend.triage` that calls the template, then dispatches selected agents through the same per-agent pipeline as legacy.
3. **A/B execution** — pilot-3 → user checkpoint → full corpus replay (legacy then ontology), per pre-reg §Analysis plan.
4. **Second-labeler pass + ship decision** — Codex auto-relabels 5 of the 12 discriminating diffs; if disagreement <30% the F6b decision binds; ship/abandon/redesign per pre-reg threshold matrix.

## Why This Approach

### Track 1 — LegacyBackend = subprocess wrap with cache

**Decision:** invoke `claude --plugin-dir interverse/interflux /interflux:flux-drive <diff_path> --output-dir <cache>/<diff_id>` as a subprocess, parse the produced `findings/*.md` + per-agent dispatch list, compute `wall_time_sec` from elapsed time and `cost_usd` from `estimate-costs.sh`. Cache results on disk keyed by `(diff_id, baseline_sha, flux-drive-version)` so re-runs are free.

**Why:**
- The pre-reg's primary metric (review-coverage-per-diff with 60% token-overlap) requires *real* finding text. Extracting only the triage scoring without dispatch (rejected option) produces empty Findings → coverage = 0 → metric is meaningless.
- Subprocess wrap exercises the actual production flux-drive — no risk of behavioural drift between "what we measured" and "what users get".
- Cache addresses the runtime/OAuth-burn concern: pilot-3 + cache means full run only pays the cost once. Re-runs (debugging, decision-memo regeneration) are free.

**Trade-off:** wall-time is bounded by the slowest agent's turn × 30 diffs. Could be hours. Mitigated by `--max-parallel` if flux-drive supports it; otherwise sequential is acceptable since cache makes it a one-time cost.

**Auth path:** Claude Max OAuth (per user feedback memory `feedback_claude_max_preference.md`). Marginal $ = 0. Operational bound is the 5-hour OAuth rate-limit window.

### Track 2 — OntologyBackend = new lattice template + thin wrapper

**Decision:** Add `SelectPersonaeForTaskTemplate` to `interverse/lattice/src/lattice/templates/`. Inputs: `diff_text`, `changed_paths`, optional `keywords`. Output: ranked list of agent names (the 12 fd-agents) with scores. `OntologyBackend.triage` calls the template to choose agents, then dispatches those agents through the same per-agent pipeline LegacyBackend uses (so finding generation is identical — only triage differs).

**Why:**
- PRD §F6b acceptance criterion (post-ERRATA) explicitly says "lattice's named templates (e.g., a new `select_personae_for_task` template)". G5 (canonical query authority) requires the agent-selection logic live as a registered template, not as ad-hoc code in OntologyBackend.
- Reusing legacy's dispatch pipeline isolates the variable: the only difference between backends is **which agents are dispatched**. Findings, costing, and wall-time all flow through identical code paths post-triage.
- Composing existing templates (rejected option) is brittle: lattice's `ChangeImpactForContractTemplate` returns impacted contracts, but agent-relevance scoring isn't a contract concept — would require ad-hoc post-processing in the backend, violating G5 in spirit.

**Trade-off:** F6b scope grows to "build a lattice template" + "integrate it". The template needs Persona entities ingested via F4 (sylveste-t2cs, closed) — verify ingestion is real before assuming it's queryable. If ingestion is broken, Track 2 stalls until F4 is repaired.

**Risk to surface:** the 12 fd-agents must be queryable as Persona entities in lattice's SQLite. F4 closed but ingestion correctness wasn't sampled at F6a sign-off. **First action in F6b: verify lattice has the 12 fd-Personas + their domain/discipline relationships before writing the template.**

### Track 3 — A/B execution = pilot-3 → checkpoint → full

**Decision:** Run pilot-3 (3 representative diffs spanning small/medium/large complexity) through each backend. Surface to user: extrapolated wall-time, OAuth burn estimate, USD-equivalent cost. AskUserQuestion before committing to the full 30-diff replay. Then run legacy first (full), then ontology (full), per pre-reg §Analysis-plan ordering.

**Why:**
- Pre-reg requires baseline-before-ontology + immutable-baseline-after-ontology-begins. Pilot-3 doesn't violate this — it's a runtime estimate, not a measurement run. Pilot-3 results are discarded and not used in the decision memo.
- Wall-time and OAuth burn are unknown a priori — pilot-3 is the only honest way to estimate.
- USD-equivalent cost-per-finding is still recorded in full run for the pre-reg's secondary-metric comparison; OAuth path means the *actual spend* is $0, but the *metric value* is computed against API-normalised pricing for fair comparison.

**Trade-off:** ~10 min of pilot-3 overhead before the real run begins. Acceptable.

### Track 4 — Second labeler = Codex (gpt-5.5) auto-relabel

**Decision:** Dispatch Codex (gpt-5.5 via Clavain Codex) on 5 randomly-sampled diffs from the 12-diff discriminating subset. Codex re-labels using the same `_schema.json` + label format. Compare against V1 labels: per-diff agreement on `expected_agents` (Jaccard) and `expected_findings_themes` (set match after canonicalisation). If aggregate disagreement <30%, F6b decision binds. If ≥30%, escalate to user (memory `feedback_voice_calibration_intersite.md` precedent: model triangulation has limits) and trigger pre-reg's "corpus rebuild" branch.

**Why:**
- Pre-reg explicitly requires this before F6b ships (§Robustness).
- Codex auto-dispatch is the lowest-friction option that satisfies the pre-reg's "second labeler" requirement.
- gpt-5.5 is a different model family (per memory `feedback_codex_model_gpt54.md`, gpt-5.5 is current default). Claude-vs-Codex disagreement is the cheapest reasonable triangulation.
- 5/12 random sample matches pre-reg verbatim — no improvisation on sampling rule.

**Trade-off:** Same systematic biases (both LLMs trained on similar code corpora) may mean low disagreement is *not* strong evidence of label correctness. The pre-reg accepts this caveat — the 5-diff bar is a *floor*, not a guarantee.

**Risk:** if Codex disagreement is high (≥30%), the decision pauses pending user manual relabel. That's the pre-reg's intended escalation path.

## Key Decisions

1. **Backends share the dispatch pipeline; only triage differs.** Both `LegacyBackend.triage` and `OntologyBackend.triage` call the same per-agent dispatch helper; they differ only in *which agents* the helper is called for. Isolates the experimental variable.

2. **Cache is content-addressed by (diff_id, baseline_sha, backend_version).** Backend-version key means a flux-drive update or a lattice-template change automatically invalidates cache for affected diffs. Replay-cheap.

3. **Pilot-3 runs but is discarded.** Pilot results inform user decision; they are NOT recorded in `f6-baseline-results.jsonl` or `f6-ontology-results.jsonl`. Those files are immutable per pre-reg.

4. **Lattice ingestion verification is gate zero.** First F6b code change is a one-shot script that queries lattice for the 12 fd-Personas and their domain/discipline relationships. If anything is missing, Track 2 stalls and F4 reopens before Track 2 can proceed.

5. **Auth path = Claude Max OAuth.** Tracked via `CLAUDE_AUTH=oauth` env var or absence of API-key env vars. The harness logs the auth path in `BackendResult.backend_metadata['auth_path']` for traceability.

6. **Second-labeler dispatch happens after pilot-3, before the full run.** This ordering means: if disagreement is high, we escalate before spending OAuth burn on a 30-diff run that might invalidate the corpus. Saves a wasted 30-diff replay.

7. **Decision memo (`docs/research/f6-ab-decision.md`) references pre-reg at SHA `d6cf80a8` AND F6a sign-off note in sylveste-2n8i.** Memo is the immutable artefact that binds the ship/abandon/redesign outcome.

## Open Questions

1. **Does flux-drive support a non-interactive subprocess invocation that skips the AskUserQuestion confirmation gate?** Need to check `--interactive` flag handling and whether the default path auto-proceeds. (SKILL.md skim suggests yes — `INTERACTIVE = false` by default.) Validate in pilot-3.

2. **Is lattice's template registry hot-reloadable?** If `SelectPersonaeForTaskTemplate` is added to `_register_builtins()` and the lattice package isn't reloaded, the harness may not see it. Validate by importing fresh in the harness's OntologyBackend.

3. **Does `estimate-costs.sh` work for OAuth runs?** Memory `Quick Reference` notes cost-query.sh reads from `core/intercore/config/costs.yaml` dynamically; verify it computes USD-equivalent for OAuth, not zero.

4. **What does flux-drive emit when slicing fires (large diff)?** Two of the 30 diffs are "large" (≥1000 lines). Pre-reg doesn't address whether sliced diffs change the contract; verify in pilot-3 by selecting at least one large diff for the pilot.

5. **Should the SelectPersonaeForTaskTemplate be unit-tested against synthetic Persona fixtures, or against the real lattice DB?** Lattice's existing template tests use real fixtures (per `interverse/lattice/CLAUDE.md`'s test command). F6b should follow precedent.

## Next Step

`/clavain:write-plan` decomposes these four tracks into bite-sized tasks. Plan should include:
- Track 1 → Track 4 ordering (the four tracks above are largely sequential: lattice verification → template + LegacyBackend in parallel → OntologyBackend → pilot-3 → full run → second labeler → decision memo)
- Explicit gate before full run: pilot-3 results + user checkpoint
- Explicit gate before decision memo: second-labeler disagreement check
- Explicit gate before bead-close: pre-reg artefact SHA list (pre-reg + baseline-results + baseline-metrics + ontology-results + ontology-metrics + decision-memo) recorded in sylveste-g939 close-reason
