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
- `gen-catalog.py` — generator script that writes to a fixed output path

`scan-fleet.sh` is a generator/maintenance script, not a pipeline component. The placement is correct.

One concern: the plan says scan-fleet.sh outputs to stdout or uses `--in-place`. The existing scripts/ pattern (gen-catalog.py) writes to a fixed path. Consider making the output path an argument rather than `--in-place` to keep consistent with the scripts/ convention and avoid accidental overwrites during development.

### lib-fleet.sh in os/clavain/scripts/

Correct placement. lib-routing.sh is the established pattern for sourced YAML query libraries. lib-fleet.sh should follow the exact same file-finding contract (script-relative, then CLAVAIN_SOURCE_DIR, then plugin cache) — the plan already calls this out. The `_FLEET_LOADED` guard mirrors `_ROUTING_LOADED`.

One boundary note: lib-fleet.sh introduces a second YAML config dependency alongside lib-routing.sh. The config-finding logic is duplicated across both libraries. This is acceptable at two files but if a third config library appears (C3 Composer may introduce one), extract the path-resolution logic to a shared `lib-config.sh`. Flag as a follow-up comment in lib-fleet.sh pointing to lib-routing.sh as the pattern source.

---

## 3. Integration Points with agency-spec.yaml

### Capability Join Model

The companions block in agency-spec.yaml declares plugin-level capability bundles. The fleet registry declares individual agent capabilities. Both use the same capability strings — the direct join works. But the Composer needs to understand that satisfying a stage requirement means selecting agents whose union of capabilities covers the required set, not necessarily a single agent covering all of them. Document this join logic in a comment block in fleet-registry.yaml (analogous to the routing.yaml header explaining resolution order).

### Role Resolution Gap

The agency-spec stages/ship and stages/design both reference `role: fd-architecture` directly. The fleet registry uses agent IDs as the key. These happen to match for the interflux review agents. But the clavain-local roles (`brainstorm-facilitator`, `strategist`, `plan-writer`, `implementer`, etc.) do not correspond to any agent ID in the proposed seed data or any existing agent file. These are abstract roles the Composer must resolve to concrete agents. The fleet schema must support this — which is why the `roles` field omission identified in section 1 matters. Confirm explicitly: are role labels in agency-spec always equal to agent IDs in the fleet registry? If yes, document it. If no, a mapping table or `roles` field is required.

### Capability String Consistency Enforcement

The plan says to "cross-reference capabilities against agency-spec.yaml companion declarations" as an F1 task. This cross-reference must produce a definitive closed list and that list must be enforced in the JSON schema as an enum. Without schema enforcement, capability string drift will silently break C3 matching. The plan currently treats this as a documentation exercise; it should produce a schema constraint.

---

## 4. Merge Semantics in scan-fleet.sh

### Generated vs. Curated Split — One Correctness Problem

The plan assigns `description` to the generated (overwritten) side. This is incorrect.

The agent frontmatter description is authored for Claude Code's Task tool `description` parameter — it is optimized for Claude to decide whether to invoke the agent. Looking at actual agent files:
- `fd-architecture.md`: description is a 300+ character string with inline example tags
- `data-migration-expert.md`: description is short and purpose-oriented
- `best-practices-researcher.md`: description is short and clear

Overwriting the curated description on every scan-fleet run will embed example content into what should be a clean catalog summary field. The catalog description and the Task tool description serve different readers (Composer logic vs. Claude Code Task invocation).

Fix: move `description` to the curated list. Treat the frontmatter description as a seed default written on first discovery and preserved thereafter, not overwritten on every scan.

### Category Assignment for Flat-Layout Agents

The script derives `category` from the agent directory path (`agents/review/` → `review`). This works for interflux and clavain agents where the layout is `category/agent-name.md`. But .claude/agents/ has a flat layout with no category subdirectory. The plan does not address this case. Either exclude .claude/agents from auto-categorization (require manual category for local agents) or document the fallback heuristic.

### subagent_type Generation for Local Agents

The `plugin-name:category:agent-name` format is reliable for interverse plugins. For .claude/agents local agents, Claude Code uses just the agent name as the subagent_type (not a namespaced path). This is another place where local agents need special-case handling in scan-fleet.sh. Document the rule or guard against it in the implementation.

### yq Merge Implementation Note

yq v4 supports this merge pattern via `load()` and selective merge expressions. The implementation should guard against two distinct cases: cold-start (agent does not yet exist in registry) and warm-merge (agent exists with curated fields). The plan describes the behavior correctly but does not specify the yq expression. Ensure the implementation handles the case where a curated field is present but empty (e.g., `capabilities: []` should be preserved as empty, not overwritten).

---

## 5. Execution Order

### Practical Order is Correct

The practical order (F1 → F3 → F2 → F4) is preferred. The query library is simpler to build and test against static fixture data, and it serves as the contract validator for the registry format. Developing scan-fleet.sh before lib-fleet.sh would mean testing the generator's output with ad hoc yq queries rather than the actual consumer API.

### Internal F1 Ordering

F1 task 3 says "cross-reference capabilities against agency-spec.yaml companion declarations." This should produce the closed capability enum that goes into the JSON schema. The capability audit must complete before the schema is finalized. Reorder F1 tasks: capability audit first, then schema, then hand-author seed data. The plan implies the current order is schema-first, which would require a schema revision after the audit.

### F2 Binding Dependency

scan-fleet.sh's merge logic requires an existing fleet-registry.yaml to preserve curated fields. The more binding F2 dependency is on the seeded registry (full F1 output), not just the schema. The execution diagram should note this.

### Missing Integration Smoke Test

The plan jumps from F3 (lib-fleet.sh written) directly to F4 (bats tests). F4 uses 5-agent fixtures. There is no step that verifies lib-fleet.sh works against the real fleet-registry.yaml with all 31 agents before writing the fixture tests. Add a step between F3 and F4: run each lib-fleet query against the real seeded registry and verify counts match expected. This catches YAML encoding issues in agent descriptions (particularly the long interflux frontmatter strings) that 5-agent fixtures will not surface.

---

## Findings by Priority

### Must Address Before Implementation

**M1. Add `roles` field to the agent schema.**
agency-spec.yaml references agents by role labels (`brainstorm-facilitator`, `strategist`, `implementer`, etc.) that do not all match agent IDs. Without `roles`, the Composer cannot close the match loop for abstract roles. Smallest fix: add `roles: []` to the agent entry schema. Document that for concrete agents (fd-architecture), the role equals the agent ID; for abstract roles, they must be declared explicitly.

**M2. Move `description` from generated to curated in merge semantics.**
The frontmatter description is optimized for Claude Code Task invocation (300+ chars, embedded examples). Overwriting the curated catalog description on every scan run will degrade catalog quality and embed non-catalog content. Treat description as a seed default: written on first discovery, preserved thereafter.

**M3. Add `runtime` block to agent schema for invocation path.**
The Composer needs to know whether to use subagent_type (Claude Code Task), a command, or Codex dispatch. Add a structured `runtime` block: `mode`, `subagent_type` (when mode=subagent), and Codex dispatch support flag.

### Should Address in This Sprint

**S1. Add capability string enum to fleet-registry.schema.json.**
Capability strings must be drawn from the closed set in agency-spec.yaml companions.provides. Derive this enum during the F1 capability audit task and enforce it in the schema.

**S2. Document local-agent special cases in scan-fleet.sh.**
.claude/agents/ has flat layout and local-only scope. Either skip with `--include-local` flag requirement, or document how category and subagent_type are assigned. Add `local` to the `source` field enum.

**S3. Add integration smoke test between F3 and F4.**
Run lib-fleet queries against the real seeded fleet-registry.yaml (31 agents) before writing bats tests. Catches YAML encoding issues invisible in 5-agent fixtures.

**S4. Reorder F1 tasks internally.**
Capability audit must complete before schema finalization. Current implied order (schema first, audit third) would require a schema revision. Correct order: capability audit, then schema, then seed data authoring.

### Optional Improvements

**O1. Add `stage_affinity` list to agent schema.**
`category: workflow` is too coarse for stage-aware dispatch. A `stage_affinity: [discover, design]` list enables future Composer filtering without breaking existing category queries.

**O2. Change scan-fleet.sh output to path argument rather than `--in-place`.**
Matches the existing scripts/ convention (gen-catalog.py uses a fixed output path) and avoids accidental overwrite during development.

**O3. Document the two-level capability model in a header comment in fleet-registry.yaml.**
Mirrors routing.yaml's resolution-order documentation. Explains the join: companions declare capability bundles; individual agents declare capability granularity; Composer joins on capability strings.

---

## What the Plan Gets Right

The plan correctly scopes C2 to data layer only — no Composer logic, no runtime service, no health checks. The yq adoption is appropriate and overdue. The lib-fleet.sh public API is clean and covers the query operations C3 will need. The fixture strategy (5 agents covering all edge cases) is proportionate. The non-goals section is explicit and correct — cold_start_tokens as static estimates rather than runtime measurements is the right call for a static catalog.

The three-file config layout (routing.yaml, agency-spec.yaml, fleet-registry.yaml) forms a coherent read-only data layer that the Composer can query without side effects. The module placement decisions are all correct. This is the right architecture for the build-vs-consume boundary between C2 and C3.

The lib-routing.sh pattern (config-finding via script-relative, env override, plugin cache; guard variable; thin yq wrappers) is the right template for lib-fleet.sh. Reusing it keeps the library interface consistent with what sprint pipeline scripts already expect.
