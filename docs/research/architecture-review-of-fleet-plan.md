# Architecture Review: C2 Agent Fleet Registry
## Plan: os/clavain/docs/plans/2026-02-22-c2-fleet-registry.md

**Date:** 2026-02-22
**Reviewer:** fd-architecture (Flux-drive Architecture & Design)
**Sprint:** iv-i1i3
**Track position:** C2 of C1 → C2 → C3 chain (agency-spec → fleet-registry → Composer)

---

## Summary

The plan is structurally sound for its stated purpose: building a static YAML catalog that the C3 Composer can query. The module placement is correct, the library API is well-scoped, and the yq adoption is the right call given B1 already established hand-rolled parsing as technical debt worth addressing. Three issues require attention before implementation begins. Several smaller schema gaps will block C3 if not resolved now, since retrofitting the schema after the registry is hand-authored for 31 agents is costly.

---

## 1. Schema Design — Completeness for C3 Composer Consumption

### What C3 Will Need

agency-spec.yaml describes what each stage *requires*:
- `requires.capabilities` — capability strings that must be provided (e.g., `domain_review`, `multi_perspective`)
- `agents[].role` — abstract role labels (e.g., `fd-architecture`, `brainstorm-facilitator`, `strategist`)
- `agents[].model_tier` — the tier the Composer should target
- Stage-level `condition` fields on optional agents (e.g., `has_security_surface`)

For the Composer to perform a match-spec-to-agent operation, it needs to answer at minimum: "Which agents provide capability X at model tier Y?" and "Can this agent fulfill role Z?"

### Missing Fields in the Proposed Schema

**1. `roles` list is absent.**

The agency-spec uses role labels (`brainstorm-facilitator`, `strategist`, `plan-writer`, `implementer`, `reflector`, `synthesis`, `parallel-worker`, `test-runner`) as the primary dispatch keys. The fleet schema has no `roles` field — only `capabilities`. For agents that fill a named role (the 4 clavain workflow agents, intersynth's synthesis agent), `capabilities` alone does not give the Composer enough to match the spec's `role:` field.

The C3 Composer will need to do one of:
- Match by role string directly, or
- Resolve roles through a capabilities indirection (every role maps to a capability set)

Neither resolution path is established in this plan. The schema needs either a `roles: []` list on each agent entry, or the agency-spec needs to be updated to express roles as capability bundles rather than labels. The first option (add `roles` to the fleet schema) is smaller and keeps C3 work self-contained.

**2. `category` enum is undertight for non-review, non-research agents.**

The proposed enum is `review | research | workflow | synthesis`. The agency-spec contains roles that do not cleanly fit: `brainstorm-facilitator` (discover stage), `strategist` and `plan-writer` (design stage), `implementer` and `parallel-worker` (build stage), `test-runner` (build stage), `reflector` (reflect stage). These are workflow agents but "workflow" is a catch-all that will produce useless results from `fleet_by_category workflow`. If the Composer ever needs to narrow by stage affinity, the category field cannot help.

Two options: expand the enum with stage-affinity categories, or add a separate `stage_affinity: []` field. A `stage_affinity` list is lower risk because it is additive and does not break existing category queries.

**3. `dispatch_tier` (Codex dispatch) is absent.**

routing.yaml has two independent routing namespaces: `subagents` (Claude Code Task tool, using haiku/sonnet/opus) and `dispatch` (Codex CLI, using fast/deep tier names). The proposed schema only models `models.preferred` and `models.supported` using the subagent tier vocabulary. There is no field for whether an agent can be invoked via Codex dispatch and if so, which tier.

The build.yaml per-stage config already references `/clavain:work` with `mode: both`, meaning agents can run in both Claude Code subagent mode and Codex dispatch mode. If the Composer needs to assign work to a Codex worker, it cannot use the fleet registry to determine dispatch tier compatibility. Add an optional `dispatch: { tier: fast | deep, supported: bool }` block.

**4. `invocation_path` / `subagent_type` format is underspecified.**

The plan defines `subagent_type: interflux:review:fd-architecture` as the Claude Code Task tool type. However, the clavain-local agents (data-migration-expert, plan-reviewer, etc.) and the .claude/agents project-local agents use a different invocation path. There is no field for whether the agent is available as a subagent_type string, a local agent slug, or must be invoked via a slash command. Without this, the Composer cannot construct the correct Task tool call.

Add a `runtime` block:
```yaml
runtime:
  mode: subagent       # subagent | command | codex
  subagent_type: interflux:review:fd-architecture   # when mode=subagent
  command: /interflux:flux-drive   # when mode=command (future)
```

**5. `condition` support is absent.**

agency-spec optional agents carry a `condition` field (`has_security_surface`, `has_performance_surface`). The fleet registry has no way to declare which conditions an agent is eligible to fulfill. Without this, the Composer cannot answer "given condition X is true, which agents are candidates?" This is a C3 scope concern but the schema field belongs in C2. Add an optional `conditions: []` list.

### What the Schema Gets Right

- `capabilities` list using the exact strings from `requires.capabilities` in agency-spec is correct — this is the direct join key the Composer needs
- `cold_start_tokens` per agent is the right granularity for budget-aware dispatch
- `models.preferred / models.supported` correctly reflects that agents have a tier preference but can run cheaper
- `tags: []` free-form field is a reasonable escape hatch for future filtering

---

## 2. Module Boundaries

### fleet-registry.yaml in os/clavain/config/

This placement is correct. The existing config/ directory already contains:
- `routing.yaml` — model routing policy (owns "how to pick a model")
- `agency-spec.yaml` — stage requirements (owns "what each stage needs")
- `agency/*.yaml` — per-stage dispatch configs (owns "how each stage runs")

`fleet-registry.yaml` owns "what agents exist and what they can do" — a peer concern to routing, not a child of it. Placing it at `config/fleet-registry.yaml` puts the three catalog files (routing, spec, fleet) at the same level, which matches their peer relationship.

One boundary concern: the .claude/agents/ project-local agents are scoped to a specific project's session. They are not part of the Clavain plugin distribution. Including them in the fleet registry creates an implicit assumption that .claude/agents/ always contains those entries. For portability, the scan-fleet.sh should optionally include project-local agents (behind a flag like `--include-local`), and the seed data should clearly mark their `source` as `local` rather than a plugin name. The plan already uses a `source` field — ensure `local` is in the allowed enum.

### scan-fleet.sh in os/clavain/scripts/

The scripts/ directory already contains:
- `lib-routing.sh` — library sourced by pipeline (matches the proposed lib-fleet.sh pattern)
- `dispatch.sh`, `debate.sh` — operational scripts

`scan-fleet.sh` is a generator/maintenance script, not a pipeline component. It is analogous to `gen-catalog.py` which already lives in scripts/. The placement is correct.

One concern: the plan says scan-fleet.sh outputs to stdout or uses `--in-place`. The existing scripts/ pattern does not use `--in-place` flags — gen-catalog.py writes to a fixed path. Consider making the output path an argument rather than `--in-place` to keep consistent with the scripts/ convention and avoid accidental overwrites during development.

### lib-fleet.sh in os/clavain/scripts/

Correct placement. lib-routing.sh is the established pattern for sourced YAML query libraries. lib-fleet.sh should follow the exact same file-finding contract (script-relative, then CLAVAIN_SOURCE_DIR, then plugin cache) — the plan already calls this out. The `_FLEET_LOADED` guard mirrors `_ROUTING_LOADED`.

One boundary concern: lib-fleet.sh introduces a second YAML config dependency alongside lib-routing.sh. Any script that needs both must source both. This is fine for now, but the config-finding logic (`_routing_find_config` vs the analogous `_fleet_find_config`) is duplicated. The duplication is acceptable at this scale (two files), but if a third config library appears (C3 Composer may introduce one), the config-finding pattern should be extracted to a shared `lib-config.sh`. Flag this as a follow-up, not a blocker.

---

## 3. Integration Points with agency-spec.yaml

### What agency-spec.yaml Declares That the Fleet Must Answer

The companion section of agency-spec.yaml uses a different abstraction level than the proposed agent entries. The companions block declares plugin-level capability bundles:

```yaml
companions:
  interflux:
    provides: [multi_perspective, artifact_generation, domain_review]
```

The fleet registry declares individual agent capabilities. The C3 Composer will need to query the fleet to find agents, but the agency-spec's `requires.capabilities` are matched against the companion's `provides`, not against individual agent capabilities.

This creates a two-level capability model:
- Level 1 (agency-spec): companion provides [multi_perspective, domain_review]
- Level 2 (fleet registry): fd-architecture provides [domain_review, multi_perspective]

These are the same capability strings, which is good — the direct join works. But the Composer needs to understand that satisfying a stage requirement means selecting agents whose union of capabilities covers the required set, not necessarily a single agent covering all of them. The fleet schema's `fleet_check_coverage` function in the proposed API is the right primitive for this, but the plan does not document the join logic between spec requirements and fleet capabilities. This should be documented in a comment block in fleet-registry.yaml (analogous to the routing.yaml header comment explaining resolution order).

### Role Resolution Gap

The agency-spec stages/ship and stages/design both reference `role: fd-architecture` directly (not just as a capability). The fleet registry uses agent IDs as the key (`fd-architecture:`) but the plan does not confirm that agent IDs and role labels are the same namespace. Confirm explicitly: are role labels in agency-spec always equal to agent IDs in the fleet registry? If yes, document it. If no, a mapping table is required.

Looking at the data: the clavain-local roles (`brainstorm-facilitator`, `strategist`, `plan-writer`, `implementer`, etc.) do not correspond to any agent ID in the proposed seed data or any existing agent file. These are abstract roles that the Composer will need to resolve to concrete agents. This is a C3 concern, but the fleet schema needs to support it — which is why the `roles` field omission identified above matters.

### Capability String Consistency

The capabilities proposed in the schema example (`domain_review`, `multi_perspective`) match the strings in agency-spec.yaml exactly. This is correct. However, the plan does not mention any validation step that cross-checks fleet registry capability strings against the known set in agency-spec. The F1 task list says "cross-reference capabilities against agency-spec.yaml companion declarations" — this needs to produce a definitive closed list of capability strings and enforce it in the JSON schema. Without this, capability string drift will silently break C3 matching.

Concrete fix: the fleet-registry.schema.json should enumerate the allowed capability values (sourced from the companions.provides sets in agency-spec.yaml). This turns a documentation cross-reference into a schema validation.

---

## 4. Merge Semantics in scan-fleet.sh

### The Generated vs. Curated Split

The plan defines:
- Generated fields (overwritten): `source`, `category`, `subagent_type`, `description`
- Curated fields (preserved): `capabilities`, `models`, `cold_start_tokens`, `tags`

This split has one correctness problem and one ambiguity.

**Correctness problem: `description` as generated.**

The agent frontmatter `description` field is not identical to a suitable fleet catalog description. Looking at the actual agent files:
- fd-architecture.md: description is a long multi-sentence string with examples inline (one-line field with embedded Example tags, 300+ characters)
- data-migration-expert.md: description is short and clear ("Validates data migrations...")
- best-practices-researcher.md: description is short and clear

The frontmatter description is authored for Claude Code's Task tool `description` parameter — it is optimized for Claude to decide whether to invoke the agent, not for human-readable catalog display or for the Composer's agent selection logic. Overwriting the curated `description` in fleet-registry.yaml with the raw frontmatter text will make the fleet catalog harder to read and may embed example content into what should be a clean summary field.

Recommendation: treat `description` as curated, not generated. scan-fleet.sh should use frontmatter description only when no curated description exists (i.e., treat it as a default/seed, not an overwrite). Alternatively, introduce a separate `frontmatter_description` field for the raw agent .md description and a separate curated `description` field for the fleet catalog. The simpler fix is to move description to the curated list.

**Ambiguity: `category` as generated.**

The script is supposed to derive `category` by scanning the agent's directory path (`agents/review/`, `agents/research/`, `agents/workflow/`). This works for interflux and clavain-local agents where the directory structure is `category/agent-name.md`. But .claude/agents/ has a flat layout with no category subdirectory. The scan logic would need a fallback for flat directories. The plan does not address this case. Either exclude .claude/agents from auto-categorization (require manual category for local agents) or document the fallback.

**`subagent_type` generation is reliable.**

The proposed format `plugin-name:category:agent-name` can be assembled from the directory path and plugin.json manifest without ambiguity for interverse plugins. For clavain-local agents, the format would be `clavain:review:data-migration-expert` — this is correct. For .claude/agents local agents, subagent_type in Claude Code uses just the agent name. This is another place where local agents need special-case handling.

**Merge implementation using yq.**

The plan describes merging as "load existing registry, overlay discovered agents, preserve curated fields." The yq v4 operation for this is a two-step: first load the existing registry into a temp map, then for each discovered agent, use `yq e 'select(.agents.<id>)` to check existence and conditionally merge. yq v4 supports this via the `load()` function and selective merge expressions. The plan does not spell out the yq expression, which is fine for a plan document, but the implementation should guard against the case where the existing registry is missing an agent entirely (cold start) vs. where it exists with curated fields.

---

## 5. Execution Order

### Stated Order

The plan offers two orderings:
- Dependency-correct: F1 → F2 and F1 → F3 → F4
- Practical: F1 → F3 → F2 → F4

The practical order (get lib-fleet working before scan-fleet) is correct and preferred. The query library is simpler to build and test against static fixture data, and it serves as the contract validator for the registry format. Developing scan-fleet.sh before lib-fleet.sh would mean testing the generator's output with ad hoc yq queries rather than the actual consumer API.

### A Missing Dependency

F1 task 3 says "cross-reference capabilities against agency-spec.yaml companion declarations." This should produce a closed capability enum that goes into the JSON schema (fleet-registry.schema.json). That enum is an input to F1 itself — the schema can't be complete until this cross-reference is done. The task list implies this is the last F1 task, but the schema should not be finalized before the capability audit is complete. Reorder F1 tasks internally: capability audit first, then schema, then hand-author seed data.

### F2 Depends on the Curated Registry, Not Just the Schema

scan-fleet.sh's merge logic requires an existing fleet-registry.yaml to preserve curated fields. This means F2 actually depends on F1 completing the full seed data (not just the schema). The plan states F2 needs the schema, which is true, but the more binding dependency is on the seeded registry. This is fine operationally since F1 produces both, but the execution order diagram should note this.

### No Integration Smoke Test Before F4

The plan goes from F3 (lib-fleet.sh written) to F4 (tests for all). There is no step that verifies lib-fleet.sh works against the real fleet-registry.yaml with all 31 agents before writing tests. Given that test fixtures use only 5 agents, a gap could exist where all bats tests pass but queries against the actual full registry fail due to schema quirks or encoding issues in agent descriptions. Add a step between F3 and F4: run each lib-fleet query against the real fleet-registry.yaml seed data and verify the counts match the expected 31+ agents.

---

## Findings by Priority

### Must Address Before Implementation

**M1. Add `roles` field to the agent schema.**
agency-spec.yaml references agents by role labels that do not all match agent IDs. Without roles, the Composer cannot close the match loop for abstract roles (strategist, implementer, brainstorm-facilitator). Smallest fix: add `roles: []` to the agent entry schema. Document that for concrete agents (fd-architecture), role equals agent ID; for abstract roles, they must be declared explicitly.

**M2. Move `description` from generated to curated in merge semantics.**
The frontmatter description is optimized for Claude Code Task invocation, not for catalog readability or Composer selection. Overwriting the curated description on every scan-fleet run will degrade catalog quality. Treat description as a seed default (written on first discovery, preserved thereafter).

**M3. Add `runtime` block to agent schema for invocation path.**
The Composer needs to know whether to use subagent_type, a command, or Codex dispatch. The current schema conflates `subagent_type` with the full invocation model. Add a structured `runtime` block that covers mode (subagent/command/codex), the subagent_type string when mode is subagent, and whether Codex dispatch is supported.

### Should Address in This Sprint

**S1. Add capability string enum to fleet-registry.schema.json.**
Capability strings in the fleet must be drawn from the closed set defined in agency-spec.yaml companions.provides. Without schema enforcement, silent drift will break C3 matching. Derive the enum during the F1 capability audit task.

**S2. Document the local-agent special cases for scan-fleet.sh.**
.claude/agents/ has a flat layout and local-only scope. The scan logic must either skip local agents by default (requiring --include-local flag) or document how it assigns category and subagent_type for flat-layout agents. Source should be `local` in the allowed enum.

**S3. Add integration smoke test between F3 and F4.**
Run lib-fleet queries against the real seeded fleet-registry.yaml before writing bats fixture tests. This catches encoding and schema issues that 5-agent fixtures will not surface.

### Optional Improvements

**O1. Add `stage_affinity` list to agent schema.**
`category: workflow` is too coarse for stage-aware dispatch. A `stage_affinity: [discover, design]` list enables future Composer filtering without breaking existing category queries.

**O2. Extract config-finding logic to shared lib-config.sh when a third config library appears.**
Two config libraries (lib-routing, lib-fleet) with identical path-resolution code is acceptable. Three would justify extraction. Flag as a follow-up with a comment in lib-fleet.sh pointing back to lib-routing.sh as the pattern source.

**O3. Capability audit comment in fleet-registry.yaml header.**
Add a header comment (mirroring routing.yaml's resolution-order documentation) that explains the two-level capability model: companions provide capability bundles; individual agents declare capability granularity; the Composer joins on capability strings.

---

## What the Plan Gets Right

The plan correctly scopes C2 to data layer only — no Composer logic, no runtime service, no health checks. The yq adoption is appropriate and overdue given lib-routing.sh's hand-rolled parser is 680 lines. The lib-fleet.sh public API is clean and covers the query operations C3 will need. The fixture strategy (5 agents covering all edge cases) is proportionate. The non-goals section is explicit and correct — cold_start_tokens as static estimates rather than runtime measurements is the right call for a static catalog.

The three-file config layout (routing.yaml, agency-spec.yaml, fleet-registry.yaml) forms a coherent read-only data layer that the Composer can query without side effects. This is the right architecture for the build-vs-consume boundary between C2 and C3.
