# Goal Charter — The structural regulator contract

**Bead:** unminted (cloud session, beads read-only — mint at workstation before /goal)
**Complexity:** C3
**Date:** 2026-08-23
**Source:** daniloc.xyz thread 2026-08-22 (`3mtofpi2pxc2y`) on Conant–Ashby regulators for agent-written code, plus the estate audit in this session.

## Title

Establish the structural-model contract — one versioned schema, two producers, enforcement where the plugins actually exist — so that a model of the codebase's cross-file structure becomes a gate input rather than a stale report. Explicitly *not* the module carve-out: that is the successor, earned by evidence.

## Why (leverage)

Conant and Ashby: every good regulator of a system must be a model of that system. Sylveste has excellent regulators of the **factory** — intercore's witness spine, Clavain's phase gates, interspect's routing calibration — and no regulator of the **artifact**. The pieces that aim at the artifact exist (`intermap`'s call graphs, `scripts/build-architecture-map.py`'s reference graph, `intertrace`'s consumer edges) but are advisory, unscheduled, and outside the enforcement path. The result is the failure mode the theorem predicts: the map has drifted from the territory it models, and nobody was notified.

The cheapest correct first move is not a new pillar. It is to **freeze the contract** — what a structural fact is, what a violation is, what a consumer may rely on — and prove it against two independent producers and one non-Claude consumer. If the contract survives that, the module carve-out is justified by evidence rather than by architecture taste. If it does not, we have lost one sprint instead of a pillar.

## Research findings (grounding — completed pre-charter)

- **The map is stale and unenforced.** `ARCHITECTURE.json` was last regenerated 2026-07-31 (23 days). `AGENTS.md` claims 66 plugin manifests; the map says 61. No workflow in `.github/workflows/` regenerates it. `scripts/build-architecture-map.py` has no `--check` mode — `main()` writes files unconditionally.
- **The map already detects real structural violations.** `ARCHITECTURE.md` lists 23 plugins with undeclared strong dependencies (3+ references, no `peerDependencies` entry). This is exactly a cross-file structural regulator, currently emitting into a document nobody gates on.
- **A detector without an actuator rots.** `sylveste-txrs` and `sylveste-mxns` (interwatch drift: `agents-md`, `claude-md`, `readme-md`, roadmap, intercore/interflux AGENTS.md) are both still `open`. Any new detector must ship with an action path or it joins them.
- **CI cannot enforce this, and must not pretend to.** `.gitignore:7-9` ignores `os/`, `core/`, `interverse/` — a fresh `actions/checkout` contains none of the plugins. `kimi-manifest-drift.yml` documents this trap in detail: running a generator there "would inspect zero plugins, report zero stale manifests and exit 0 — a green check that looked at nothing," and records that `interverse-inventory.yml` gated real steps behind `[ -d interverse ]` and silently skipped them on every run. Estate enforcement lives in the **pre-commit hook**, where the monorepo is materialised. CI guards the *checkers*.
- **The estate has an exit-code vocabulary for this.** `gen-kimi-manifests.py --check --require-plugins 60` → 0 clean, 1 drift, 2 cannot-verify (vacuity guard). `gen-autonomy-position.py` uses the same, and CI asserts exit 2 on a source-less tree. Reuse it; do not invent one.
- **Plugins cannot carry a platform promise.** `docs/contracts/v1-stability-contract.md` §3 excludes Interverse plugins from v1.0: "Plugin API is stable; plugin behavior is not a platform promise." Layer 1 (frozen to v2.0) covers event stream format and kernel data model. A verdict that can fail a gate belongs on the Layer-1 side of that line.
- **The estate's anti-divergence mechanism is interbase.** `docs/plans/2026-02-25-interverse-plugin-decomposition-design.md`: extracted plugins share code through the interbase SDK — "No per-split shared libraries, no copy-and-diverge."
- **Ockham is the positioning precedent.** `docs/brainstorms/2026-04-03-ockham-vision-brainstorm.md:187` — "Not an audit log. Interspect owns the evidence trail. Ockham writes to interspect, never maintains its own audit store." And: "Not a quality arbiter. Quality gates are Clavain's domain."
- **intermap is MCP-only today.** `cmd/intermap-mcp/main.go` is the sole entry point (9 tools, 6 Go packages + 67 Python tests passing per `docs/plans/2026-03-01-intermap-audit-close.md`). A headless CLI is new work, not a rename.

## Scope

### In

1. **The contract** — a versioned JSON Schema for structural facts and structural violations, authored in `sdk/interbase`, semver'd independently of every consumer, with `schema_version` stamped in each emitted document.
2. **Two producers, one schema** — `scripts/build-architecture-map.py` (plugin-graph scale) and `intermap` (intra-project scale) both emit conforming documents. Two independent producers is the actual test of whether this contract is module-worthy; a schema with one producer is a data format, not a contract.
3. **Checker mode with a vacuity guard** — `--check` on both producers, exit 0/1/2 per the estate vocabulary, `--require-plugins N` so an empty tree fails loudly instead of reporting clean.
4. **Enforcement in the pre-commit hook**, installed by the existing idempotent, non-destructive installer pattern (must leave the beads-managed block intact).
5. **CI guards the checkers, not the estate** — unit tests for resolution logic plus a test proving the vacuity guard exits 2 on a plugin-less root. The workflow states in its own comments where real enforcement lives.
6. **Baseline + waiver file** for the 23 pre-existing undeclared-dep violations, each with a reason and an owner. New violations are never auto-baselined.
7. **Violations emit as intercore events** (`source: structural`), so interspect can profile them and the calibration loop can close. No private store.
8. **interphase gate in shadow mode** — reads violations, reports, never blocks. Promotion to blocking is out of scope and gated on the metrics below.
9. **Reconcile 61 vs 66** as the first real drift caught, with `ARCHITECTURE.json` regenerated and committed.

### Out

- **The module carve-out and its name.** This charter deliberately does not create a pillar. See Successor obligations.
- **Renaming or relocating `intermap`.** It stays an Interverse plugin and becomes a producer.
- **Blocking enforcement.** The gate is report-only for the full evaluation window, no exceptions.
- **New semantic analysis.** Use intermap's existing AST/tree-sitter capability; adding call-graph depth is a separate goal.
- **Multi-host wiring** (Codex/Gemini/Kimi/Skaffen consumers).
- **Retiring `ARCHITECTURE.md` rendering.** The human-readable map stays as-is.

## Requirements

| ID | Requirement |
|----|-------------|
| R1 | Structural-fact and structural-violation schemas exist in `sdk/interbase`, versioned, with `schema_version` in every emitted document and a validator callable from Bash, Go, and Python. |
| R2 | `scripts/build-architecture-map.py` emits schema-conforming output and gains `--check` (0 clean / 1 drift / 2 cannot-verify) and `--require-plugins N`. |
| R3 | `intermap` gains a headless CLI entry point that emits schema-conforming output with no MCP server and no Claude session, sharing the exit-code vocabulary. |
| R4 | A single validator accepts both producers' output; a conformance test runs both and asserts schema validity. |
| R5 | The pre-commit hook runs the checker on a materialised monorepo, fails the commit on new violations, and is installed idempotently without clobbering the beads block. |
| R6 | CI tests the checker and asserts exit 2 on a plugin-less root; CI never regenerates the map and says so in the workflow. |
| R7 | A baseline file records the 23 existing violations with reason and owner; the checker distinguishes baselined from new; nothing is auto-baselined. |
| R8 | Each new violation emits an intercore event; no violation history is persisted outside the intercore event stream. |
| R9 | An interphase gate reads violations and reports them in shadow mode; a test proves it cannot block. |
| R10 | `ARCHITECTURE.json` is regenerated, the 61-vs-66 discrepancy is resolved, and `AGENTS.md` and the map agree. |

## Acceptance criteria

1. R1–R4: both producers emit documents that pass one shared validator; conformance test green.
2. R2/R3: `--check` returns 1 on seeded drift and 2 on an empty tree, proven by tests for both producers.
3. R5: a commit introducing a new undeclared strong dependency is refused by the hook on a materialised checkout; the beads block survives three installer runs.
4. R6: the CI job passes, contains no estate-scanning step, and its summary names the pre-commit hook as the real enforcement point.
5. R7: the baseline file exists with 23 entries, each with reason and owner; a new violation is reported while baselined ones are silent.
6. R8: a seeded violation appears in `ic` events with `source: structural`; a grep proves no other persistence path was added.
7. R9: the interphase gate surfaces violations in a shadow-mode run and a test asserts a non-blocking exit.
8. R10: `ARCHITECTURE.json` regenerated; plugin count agrees with `AGENTS.md`; both committed.
9. All commits pushed; bd export committed with `beads_jsonl_dolt_sync ok`.

## Metrics

Evaluation window: **30 days** from first pre-commit hook install. Interim review at day 14; go/no-go on the successor at day 30.

### Success metrics — what proves the regulator is real

| ID | Metric | Target | Baseline | Source |
|----|--------|--------|----------|--------|
| S1 | Structural index staleness | ≤ 1 commit, median, over 14 days | 23 days as of 2026-08-23 | `git log -1 --format=%ct ARCHITECTURE.json` vs HEAD, sampled daily |
| S2 | Real drift caught before main | ≥ 1 commit refused by the hook for a genuine new violation | 0 (no gate exists) | pre-commit logs / refused-commit record |
| S3 | Violation → action rate | ≥ 50% of new violations fixed, waived, or baselined-with-reason within 14 days | ~0% (interwatch drift beads open, unactioned) | intercore `structural` events vs bead/waiver state |
| S4 | Precision | ≥ 80% of a 20-violation human-adjudicated sample judged real | unmeasured | manual adjudication at day 30 |
| S5 | Non-Claude consumers | ≥ 2 (pre-commit hook, CI checker) consuming the schema with no session | 0 | inspection |

### Guardrail metrics — what must not degrade

| ID | Guardrail | Threshold | Rationale |
|----|-----------|-----------|-----------|
| G1 | Added pre-commit wall-clock | ≤ 2s p95 | The beads auto-export budget is ~0.3s probe / ~3s on change; a structural check must stay in that family or it gets bypassed. |
| G2 | Merges blocked by the structural gate | exactly 0 during the window | The gate is shadow-mode. A single block means it is miswired, not that it is working. |
| G3 | Violation rows outside intercore events | 0 | Ockham's rule: never maintain a private audit store. |
| G4 | intermap MCP output size | ≤ +10% vs today | Context efficiency is a stated Interverse plugin criterion; the regulator must not tax every session. |
| G5 | Layer-1 contract changes | 0 | `ic` CLI, `plugin.json`, hook contract, event field names stay frozen. The new schema is additive. |
| G6 | Pre-existing CI jobs | all still green | kimi-manifest-drift and the other four workflows are untouched. |

### Kill metrics — when to stop, and what stopping means

| ID | Trigger | Action |
|----|---------|--------|
| K1 | Precision < 50% on the day-30 sample | **Kill.** An inaccurate regulator is worse than none — it trains everyone to ignore it. Revert the hook, keep the schema as a draft, do not carve the module. |
| K2 | Violation → action rate < 20% at day 30 | **Demote.** It is a detector with no actuator, i.e. interwatch's failure repeated. Convert to on-demand-only; do not gate; do not promote. |
| K3 | Schema breaking changes > 2 in the window | **Stop the successor.** The contract is not ready to be frozen; a Layer-1 promise cannot be made on it yet. Continue as a plugin-local format. |
| K4 | Hook bypass rate (`--no-verify` / opt-out env) > 10% of commits, or p95 > 5s | **Kill the enforcement path.** The regulator is being routed around, which is worse than absent because it looks enforced. Redesign before retrying. |
| K5 | The vacuity guard ever exits 0 on an empty tree | **Hard stop, immediately.** A checker that reports success having read nothing is the specific defect `kimi-manifest-drift.yml` was built to prevent. Not a window metric — halt and fix. |

## Completion condition (LITERAL — handed to /goal verbatim)

The structural regulator contract is complete when ALL of the following are surfaced in-session: (1) structural-fact and structural-violation JSON Schemas are committed in sdk/interbase with a schema_version field and a validator, and a conformance test is surfaced passing that validates output from BOTH scripts/build-architecture-map.py and the intermap headless CLI against that one validator; (2) both producers support --check with exit 0 clean, 1 drift, 2 cannot-verify, and tests are surfaced proving exit 1 on seeded drift and exit 2 on an empty tree for each; (3) the intermap headless entry point emits conforming output with no MCP server running and no Claude session, surfaced by a direct shell invocation; (4) the pre-commit hook runs the checker, refuses a commit that introduces a new undeclared strong dependency on a materialised checkout, and three consecutive installer runs leave the beads-managed block intact and exactly one structural block present, all surfaced; (5) a CI workflow is committed that tests the checkers, asserts exit 2 on a plugin-less root, contains no step that scans the estate, and states in its summary that the pre-commit hook is the real enforcement point; (6) a baseline file with all 23 pre-existing undeclared-dependency violations is committed, each entry carrying a reason and an owner, and a demonstration is surfaced showing a new violation reported while baselined ones stay silent; (7) a seeded violation is surfaced appearing in ic events with source structural, and a grep is surfaced proving no violation persistence path exists outside the intercore event stream; (8) an interphase gate surfaces violations in a shadow-mode run and a test is surfaced asserting it exits non-blocking; (9) ARCHITECTURE.json is regenerated and committed, and the plugin count agrees with AGENTS.md with the discrepancy resolution recorded; (10) all commits pushed and the bd export committed and pushed with beads_jsonl_dolt_sync ok surfaced. Or stop after 80 turns and surface an accounting of which requirements landed, which producers conform, whether the hook enforces, and the measured baseline for S1 and S3.

## Successor obligations

On completion, do **not** automatically carve the module. Propose the successor only if the day-30 review clears K1–K4 and meets S3 and S4. If it does, the successor is: name and extract the L2 structural governor as a headless peer to Ockham (`os/`), moving the schema to it, leaving `intermap` as the agent-facing reader and Clavain as the sole enforcement authority, with the Ockham-style "what it is NOT" boundary doc written first. If the review does not clear, the successor is instead a rescoping goal that records which of the four claims failed and whether the contract survives as a plugin-local format.

## Open questions for review

1. **Schema home.** `sdk/interbase` is the documented anti-divergence mechanism, but it is an SDK, not a contract registry. Alternative: keep the schema inside intermap for this window and move it on promotion — cheaper, but then the second producer imports from a plugin, which is the coupling interbase exists to prevent.
2. **Shadow-mode duration.** 30 days is proposed. Shorter gets to enforcement sooner; longer gives S3/S4 more samples. The estate has no precedent value here — interwatch's graduated report-only→auto-refresh ladder is the closest analogue.
3. **Two producers now, or one?** Including `intermap` doubles the work but is the only real test of the contract. Dropping it makes this a one-sprint hygiene goal that proves nothing about module-worthiness.
4. **G4 measurement.** No current instrument measures per-plugin MCP output size; interstat measures sessions. This guardrail may need a cheap manual baseline instead.
