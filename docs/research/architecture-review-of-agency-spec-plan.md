# Architecture Review: C1 Agency Specs — Declarative Per-Stage Config

**Date:** 2026-02-22
**Plan file:** `os/clavain/docs/plans/2026-02-22-c1-agency-specs.md`
**Brainstorm:** `os/clavain/docs/brainstorms/2026-02-22-c1-agency-specs-brainstorm.md`
**PRD:** `os/clavain/docs/prds/2026-02-22-c1-agency-specs.md`

---

## Summary Verdict

The plan is architecturally sound in its goal — making implicit sprint behavior declarative — and its backward-compatibility approach is well-considered. Three structural problems require resolution before implementation begins: a tool-choice contradiction that will cause runtime failures on day one, a gate authority ambiguity that will grow into a correctness liability as C2/C3 land, and a missing accounting primitive that makes the budget feature underdetermined. The companion declaration section is intentionally deferral-safe and that tradeoff is correctly documented.

---

## 1. Boundaries and Coupling

### 1.1 Schema Concern Separation — Mostly Clean, One Violation

The three-layer concern separation is correctly stated in the brainstorm: `agency-spec.yaml` declares what a stage needs (policy), `routing.yaml` resolves which concrete model satisfies that need (mechanism), and the kernel tracks state and gates (record). This division maps cleanly onto the existing Clavain OS / Kernel split documented in `clavain-vision.md`.

One violation: `budget.model_preference` in the stage spec attempts to express routing preference at the spec layer. The brainstorm's own resolution rule correctly demotes this to a hint ("routing.yaml has final authority"), but the schema still embeds an `enum [haiku, sonnet, opus, oracle, codex]` field in the stage spec. This creates a parallel routing surface that can diverge from `routing.yaml` without any validation catching the divergence. The Composer (C3) will eventually need to reconcile `stage.budget.model_preference` against `routing.yaml` phase resolution, and the precedence rule is documented only in prose, not enforced anywhere.

**Minimum fix:** Rename `model_preference` to `model_tier_hint` in the schema and add a comment noting that `routing.yaml` always wins. Alternatively, remove it entirely from C1 and let `routing.yaml` handle all model resolution — which it already does per phase. The field only has value when C3 is making budget-aware decisions, which is out of scope for C1.

### 1.2 Gate Authority — Active Correctness Risk

The plan's gate integration is the highest-risk boundary issue. The stated policy is "spec gates supplement, don't replace — if both exist, both must pass." The implementation in Task 3.1 contradicts this: `enforce_gate()` first checks `gates_json != "{}"` and if true, calls `_evaluate_spec_gates` and returns its result — `intercore_gate_check` is only reached in the else branch. This means when a spec gate is defined, the kernel gate check is bypassed, not supplemented.

Current `enforce_gate` in `lib-sprint.sh` (lines 503-511):
```bash
enforce_gate() {
    local bead_id="$1"
    local target_phase="$2"
    local artifact_path="${3:-}"
    local run_id
    run_id=$(_sprint_resolve_run_id "$bead_id") || return 0
    intercore_gate_check "$run_id"
}
```

The proposed replacement uses `if [[ "$gates_json" != "{}" ]]; then ... return $?; fi` with the kernel gate check as the else-branch fallback. This is not "both must pass" — it is "spec gates replace kernel gates when present." That behavior is incorrect by the plan's own stated policy, and it erodes the kernel's authority as the durable system of record.

The deeper structural issue: `intercore_gate_check` calls `ic gate check <run_id>` which evaluates gates registered in the kernel's SQLite DB. The spec defines gates as YAML. These are two separate gate registries with no synchronization. The plan does not specify whether spec gates should be written into the kernel at sprint-start (so `ic gate check` can evaluate them) or evaluated independently in bash alongside the kernel check.

The kernel gate model exists precisely to provide a crash-safe, auditable record of gate evidence. If spec gates run only in bash and bypass the kernel, gate outcomes become unobservable (not recorded in the event bus), non-auditable, and unavailable to Interspect for adaptive routing.

**Must-fix before implementation:** Choose one of two architecturally clean options:
- Option A (kernel-authoritative): At sprint start, translate spec gates into kernel gate registrations (`ic gate add <run_id> ...`). `enforce_gate` continues to call only `intercore_gate_check`. The spec is the source of truth at sprint-start, the kernel is the system of record during execution. This aligns with the vision doc's write-path contract ("companion plugins produce capability results but do not define gate rules — the OS does").
- Option B (dual evaluation): `enforce_gate` calls both `_evaluate_spec_gates` AND `intercore_gate_check`, requiring both to pass. Record spec gate outcomes as kernel events (not gate checks, but state entries) so they appear in the event bus.

Option A is strongly preferred because it keeps the kernel as the single gate authority and makes spec gates observable without adding a second gate evaluation path. Option B adds two gate code paths that must stay in sync — exactly the class of parallel architecture the review principles flag as a smell.

### 1.3 `sprint_stage_tokens_spent` — Missing Primitive

Task 3.2 introduces `sprint_stage_budget_remaining()` which calls `sprint_stage_tokens_spent()`. This function does not exist anywhere in `lib-sprint.sh`. The existing token tracking infrastructure uses `sprint_record_phase_tokens()` which stores per-phase token data in `intercore_state_get("phase_tokens", run_id)` as a JSON blob keyed by phase name, not by macro-stage.

To implement `sprint_stage_tokens_spent(sprint_id, stage)`, the function must:
1. Know which phases belong to the stage (requires the spec or a hardcoded map)
2. Sum the token records for those phases from the `phase_tokens` state key

This is a non-trivial dependency that the plan leaves implicit. The budget feature cannot ship without this primitive. It is not mentioned in the testing strategy or the risk table.

**Minimum fix:** Add `sprint_stage_tokens_spent()` to Task 3.2 with explicit implementation, reading from `phase_tokens` state and summing by phase-to-stage mapping. Document that the accuracy depends on `sprint_record_phase_tokens` having been called at each phase completion (it is called at line 647, but only if `ic` is available).

---

## 2. Pattern Analysis

### 2.1 Tool Choice Contradiction — Runtime Failure on Day One

The PRD (line 89) explicitly resolves the YAML parser question: "Decision: use `yq`." The plan ignores this decision and designs the entire loader library around `python3 + PyYAML` with a `agency-spec-helper.py` script.

This matters concretely: `yq` is not installed on this server (verified). The PRD's stated basis for the decision ("yq is installed on this server") is factually wrong. The plan's approach (Python + PyYAML) is correct for this environment — PyYAML and jsonschema are both available. But the PRD and plan are in direct contradiction, which means any agent implementing from either document in isolation will produce a different result.

The PRD needs to be updated to reflect the actual decision: Python + PyYAML, not yq. Until that correction is made, the PRD is the wrong source of truth for implementers.

### 2.2 Python Helper in a Bash Codebase — Acceptable, With Scope Discipline

The Python helper approach follows the precedent established by the existing Python sync rewrite at `os/clavain/docs/plans/2026-02-12-python-sync-rewrite.md` and the interstat sqlite queries already in `lib-sprint.sh`. Python is used where bash cannot cleanly handle the task (YAML parsing, schema validation). This is the right call.

The concern is scope creep in the helper script. The plan specifies three subcommands (`load`, `validate`, `query`) and a 150-line cap. The `query` subcommand is redundant: if `agency_load_spec` caches JSON in `_AGENCY_SPEC_JSON`, all subsequent queries use `jq` directly in bash — there is no need to shell out to Python again for a dotted-path extraction. Python-to-bash-to-Python-again for every field read would be the worst of both worlds.

**Minimum fix:** Drop the `query` subcommand entirely. The helper handles only `load` (YAML→JSON) and `validate` (schema check). All field extraction uses `jq` on the cached `_AGENCY_SPEC_JSON` variable. This reduces the Python footprint to exactly its justified use case and eliminates redundant subprocess spawning for reads.

### 2.3 Cache Invalidation Scope

`_AGENCY_SPEC_JSON` cached in a bash variable is correct for single-session use. The `agency_invalidate_cache` function is mentioned but not designed. The only scenario requiring invalidation mid-session is if a project override is written during a sprint (unlikely but possible with project-level spec editing). If invalidation is omitted or broken, a stale spec silently governs the session. The risk is low but the failure mode (wrong gates, wrong budgets) is high impact.

The cache should use the spec file's modification time as a validity key, checked on each `agency_load_spec` call. This is a single `stat` call and avoids silent staleness.

### 2.4 Capability Vocabulary — Intentional Ambiguity is Acceptable for C1

The open question about capability vocabulary (free-form strings vs. enum) is correctly deferred. The brainstorm notes the tradeoff accurately: enum is more validatable but harder to extend; free-form strings let the vocabulary emerge from usage. The plan's position — start free-form, add enum validation when vocabulary stabilizes — matches how `routing.yaml`'s category vocabulary evolved (it started with four categories and the schema now has a known set). This is the right call for C1 and does not create downstream debt as long as C2 declares a vocabulary stabilization gate.

---

## 3. Simplicity and YAGNI

### 3.1 Companion Declarations as C1 Scope — Risk of Speculative Encoding

F6 (companion capability declarations) adds significant YAML to `agency-spec.yaml` for 8 companions, each with multi-level capability maps (`kernel`, `filesystem`, `external`, `coordination` sub-keys) and per-agent specialization/cost profiles. The brainstorm correctly identifies this as seed data for C2's fleet registry.

The structural problem is that the spec becomes the authoritative source for companion capabilities that companions themselves do not self-declare. When a companion changes (new agent added, MCP capability removed, cost profile updated), the central spec must be manually updated — and there is no mechanism to detect drift. The brainstorm acknowledges this and defers self-declaration to C2. That is the correct decision, but it means the C1 companion declarations are best-effort documentation, not enforceable contracts.

The risk is that the companion declarations will drift from reality immediately (companion capabilities change frequently), creating a spec that is wrong for C2 before C2 ships. This is the same class of problem the "bulk audit bead anti-pattern" in project MEMORY.md documents: encoding observations of current state as durable facts that are immediately stale.

**Recommendation:** Scope F6 narrowly for C1. Declare only the `provides` array (abstract capabilities a companion offers, e.g., `multi_perspective`, `cross_ai_review`) — not the per-agent kernel/filesystem/coordination specifics. The abstract capability vocabulary is stable; the implementation details are not. C2 enriches the declarations with actual implementation detail via self-declaration protocol. This reduces F6's YAML surface by roughly 70% and eliminates the drift-prone detail layer.

### 3.2 `agent_spec.condition` — Premature Extensibility

The `condition` field in agent specs uses free-form expressions like `"complexity >= 4"` and `"project.domain == 'game'"`. There is no evaluator for these expressions defined anywhere in the plan. The plan does not specify what parses them, what context variables are available, or how errors are handled. These expressions cannot be enforced until C3 (Composer) ships — C3 is the component that makes routing decisions at agent dispatch time.

For C1, these conditions are inert strings stored in YAML that no code reads. Adding them to the schema now is speculative extensibility that increases schema complexity without any current consumer. The MEMORY.md documents this exact anti-pattern: "check that new abstractions are used by more than one real caller before blessing extraction."

**Minimum fix:** Remove `condition` from `agent_spec` in C1. Re-add it in C3 when the Composer defines the evaluation model. The schema can accept `condition` as an optional unvalidated string in C1 if preserving the YAML syntax is desired, but the JSON Schema should mark it as intentionally unvalidated with a comment noting C3 dependency.

### 3.3 Budget Shares Sum Validation — Missing Edge Case

The plan validates that budget shares sum to 100% and warns/normalizes if off. The normalization behavior is unspecified: does it scale proportionally, truncate, or error? The plan says "warn and normalize" but the implementation in Task 3.2 does not handle the normalization path — `sprint_stage_budget()` takes the share as-is without normalizing against the actual total. If shares sum to 110%, the allocations will collectively exceed the run budget, making `sprint_stage_budget_remaining()` unreliable.

The simplest fix: normalize at load time in the Python helper. If shares sum to S where S != 100, scale each share by 100/S. Log the original vs. normalized values. This keeps the budget arithmetic in `lib-sprint.sh` simple (assumes shares always sum to 100 post-load).

---

## 4. Missing Schema Fields for C2/C3

The following fields are absent from the C1 schema and will create migration work when C2/C3 land:

**C2 (Fleet Registry) will need:**
- `companions.<name>.version` — to track which plugin version a capability declaration describes. Without versioning, C2 cannot tell if a declaration is stale relative to the installed plugin.
- `companions.<name>.health_check` — a command or endpoint C2 can use to verify the companion is actually available. The registry tracks availability, not just declarations.
- `companions.<name>.provides[].quality_signal` — C2's purpose is to track what companions *actually deliver* vs. what they *claim*. Without a quality signal reference, C2 has no hook to correlate spec claims with outcomes.

**C3 (Composer) will need:**
- `stages.<name>.agents[].priority` — when the Composer selects from the optional agent list, it needs a priority ordering when budget is constrained. The current schema has `required` and `optional` arrays but no intra-array priority.
- `stages.<name>.agents[].min_count` and `max_count` as separate integers rather than the `count: "N-M"` string pattern. The string pattern is harder to validate and requires string parsing in C3. Using two integer fields (`min_count`, `max_count`) is consistent with how JSON Schema validates numeric ranges and is cleaner for the Composer's budget allocation math.
- `stages.<name>.timeout_tokens` — a hard ceiling on stage token use (distinct from `budget.share` which is advisory). C3 needs to know when to forcibly advance past a stage that is consuming too much, separate from the soft budget warning.

**C5 (Self-Building) will need:**
- `stages.<name>.can_propose_changes: boolean` — whether Interspect is permitted to propose spec changes for this stage. Without this, C5 has no way to know which parts of the spec are frozen policy vs. adaptable configuration.

None of these require implementation in C1. They do require that the schema is designed to accept them without breaking changes — meaning the `companions.<name>` object and `stages.<name>.agents` arrays should be defined with `additionalProperties: true` (or equivalently, not set to `false`) so C2/C3 can add fields via additive schema extension without breaking C1 validation.

The current plan does not mention `additionalProperties` settings in the JSON Schema design. This is a small authorship detail but gets expensive to fix after the schema is deployed and projects have written override specs against it.

---

## 5. Companion Capability Declaration vs. Self-Declaration Goal

The brainstorm acknowledges the tension directly (Open Question 4) and makes the right call: central declaration in C1, self-declaration protocol added in C2. This is architecturally defensible because:

1. The clavain-vision.md write-path contract specifies "companion plugins produce capability results but do not define gate rules or create runs." Self-declaration of capabilities is a capability claim, not a gate rule — so it does not violate the write-path contract for companions to self-declare.
2. Central declaration in C1 creates a forcing function: the spec must be written, which surfaces capability gaps and naming inconsistencies before C2 has to process them.

However, the central declaration approach creates a coupling that the plan underweights: `agency-spec.yaml` becomes a dependency for Interverse plugin authors who want their companion recognized. Today, a new companion plugin can be installed and used without touching any Clavain core files. With central declaration, adding a companion to the agency requires a Clavain PR. This is a coordination burden that grows with the companion count.

The brainstorm's proposed migration path (central now, self-declaration in C2) is sound, but C1 should establish the self-declaration schema format for companions even if the mechanism is not yet wired. Specifically: the companion entry in `agency-spec.yaml` should have a `source: "central"` vs. `source: "self-declared"` field. This makes the migration in C2 an additive change (flip source, wire the loader) rather than a schema redesign.

---

## Priority Summary

**Must fix before implementation begins:**

1. **Gate authority ambiguity** (`os/clavain/docs/plans/2026-02-22-c1-agency-specs.md`, Task 3.1): Choose Option A (translate spec gates to kernel gate registrations at sprint-start) or Option B (dual evaluation with both paths required to pass). The current plan implements neither — it implements spec-replaces-kernel, which contradicts the stated policy.

2. **PRD/plan tool contradiction** (`os/clavain/docs/prds/2026-02-22-c1-agency-specs.md`, Open Questions section): Update the PRD to reflect the actual decision: Python + PyYAML, not yq. yq is not installed on this server. The plan's Python approach is correct; the PRD's decision record is wrong.

3. **`sprint_stage_tokens_spent` missing** (Task 3.2): Add this function explicitly to the plan with implementation detail. Budget remaining calculation is broken without it. It requires summing `phase_tokens` state entries grouped by stage, which in turn requires the phase-to-stage mapping from `_phase_to_stage()`.

**Should fix before implementation:**

4. **`budget.model_preference` scope** (Task 1.1 schema): Rename to `model_tier_hint` and document explicitly that `routing.yaml` always takes precedence. Or remove from C1 entirely since no C1 consumer uses it.

5. **Drop `query` subcommand from Python helper** (Task 2.2): Use `jq` directly on `_AGENCY_SPEC_JSON` for all field extraction. Eliminating the redundant Python subprocess for reads keeps the helper minimal and avoids per-call spawn overhead.

6. **Narrow F6 companion declarations** (Task 3.3): Declare only `provides` (abstract capabilities) in C1. Defer per-agent kernel/filesystem capability detail to C2 self-declaration. Reduces drift surface from day one.

**Track for C2/C3 planning:**

7. **Schema `additionalProperties` setting**: Set to `true` on `companions.<name>` and `stages.<name>.agents[]` entries so C2/C3 can add fields without breaking C1 validation.

8. **Add `companions.<name>.source` field**: Set to `"central"` in C1. C2 flips to `"self-declared"` as part of its self-declaration wiring. Makes the C1→C2 migration additive.

9. **Replace `count: "N-M"` string with `min_count`/`max_count` integers**: Cleaner for JSON Schema validation and C3 budget math.

10. **Remove `agent_spec.condition`**: Inert in C1 and C2, only meaningful in C3. Add back in C3 sprint with the Composer's evaluation model defined.
