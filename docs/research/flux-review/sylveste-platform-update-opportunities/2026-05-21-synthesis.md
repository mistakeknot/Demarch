---
artifact_type: review-synthesis
method: flux-review
target: "docs/research/flux-review/sylveste-platform-update-opportunities/2026-05-21-target-brief.md"
target_description: "Sylveste / Clavain / Intercore / Interverse platform update opportunities for Codex and Claude Code"
tracks: 4
track_a_agents: [adjacent-platform-architecture]
track_b_agents: [orthogonal-platform-engineering]
track_c_agents: [distant-systems-maintenance]
track_d_agents: [obsolete-assumption-hunter]
date: 2026-05-21
bead: sylveste-4u0v
---

# Sylveste Platform Update Opportunities

This was a compact four-track `/flux-review` pass against the current `zklw:/home/mk/projects/Sylveste` checkout, with tracks for adjacent platform architecture, orthogonal platform engineering, distant maintenance/control systems, and obsolete-assumption hunting. The pass did not run the full sixteen-agent Flux-review fan-out; it used four track-level reviewers to keep the review bounded while preserving the semantic-distance structure.

The highest-confidence pattern is not that Sylveste lacks ideas. It is that the platform has outgrown several early assumptions:

- Claude Code is no longer the only host surface; Codex needs native capability metadata rather than translated Claude prompts.
- Interverse is no longer a small plugin set; it needs portfolio tiers, generated inventory, and drift gates.
- Generated review agents are no longer a small scratch corpus; they need retention and pack-scoped loading.
- Multi-agent coordination cannot rely on shared-checkout tricks; worktrees and checkout freshness need to be platform primitives.
- Flux-review has become load-bearing enough to need scheduler-level cost, concurrency, and observability controls.

## Verification Caveat

Two tracks initially reported that the interlock worktree migration had not shipped because the nested `interverse/interlock` checkout still contained `GIT_INDEX_FILE` session-index code. Verification showed the nested checkout was one commit behind `origin/main`; `origin/main` contains `f1c79a2 Replace session index isolation with worktrees`. I fast-forwarded the nested checkout. The remaining finding is therefore not "the fix does not exist"; it is that a clean root checkout can mask stale nested plugin repos, and platform doctor/status needs to detect that before agents draw wrong conclusions or run stale hooks.

## Critical Findings

### 1. Codex Interflux Skill Wiring Is Stale

**Severity:** P1 / quick fix
**Convergence:** 3/4 tracks

The Codex installer still maps Interflux through older skill names and paths. Reviewers found `os/Clavain/scripts/install-codex-interverse.sh` referring to `interflux|skills/flux-engine|flux-drive`, while the current plugin has `interverse/interflux/skills/flux-drive/SKILL.md` and `skills/flux-review/SKILL.md`. Current commands delegate to `interflux:flux-engine` and `interflux:flux-review-engine`, but Codex install/link generation is not normalized around the current skill IDs.

**Impact:** Codex can miss or mis-link the core review skill. Claude Code mostly survives through slash command resolution, but the command-to-skill contract is harder to reason about.

**Recommendation:** Normalize Interflux skill IDs across `plugin.json`, command frontmatter, Codex installer mappings, and docs. Add a doctor assertion that every generated Codex link target exists.

**Follow-up Bead:** `Normalize interflux skill IDs across Claude manifest, commands, and Codex installer`

### 2. Interverse Inventory Has Outgrown Manual Manifest Discipline

**Severity:** P1
**Convergence:** 4/4 tracks

The ecosystem has roughly sixty live plugin manifests, plus many research fixture manifests. Tracks independently found manifest, marketplace, component-count, and docs drift:

- Some manifests declare fewer components than exist on disk.
- Some marketplace entries do not map cleanly to current Interverse manifests.
- Some plugins have zero or near-zero user-facing surface but still look like live marketplace/plugins.
- Interspect is described as cross-cutting infrastructure in public docs but its plugin manifest does not expose the commands/hooks its README claims.
- The hook-loading contract is contradictory: the plugin standard says not to declare hooks in `plugin.json`, while validation guidance elsewhere expects hook declaration.

**Impact:** Claude Code can silently miss commands, hooks, or agents. Codex wrapper generation inherits stale assumptions. Users cannot tell core plugins from optional, incubating, internal-only, or deprecated packages.

**Recommendation:** Treat plugin inventory as generated supply-chain metadata. Add a manifest ledger that classifies every plugin by surface type and lifecycle tier, validates disk paths, validates marketplace entries, and fails doctor/CI on drift.

**Follow-up Beads:**

- `Generate Interverse inventory from manifests and fail drift in doctor/CI`
- `Define Interverse plugin surface tiers and install profile packs`
- `Spec and test canonical hook loading contract`

### 3. Plugin Installation Is Too Monolithic For Codex And Claude Code

**Severity:** P1
**Convergence:** 3/4 tracks

Default install/recommendation paths still behave as if "more Interverse" is usually better. That was reasonable when the ecosystem was small. It is now wrong. The repo includes many plugin types: core workflow plugins, review/research tools, docs tools, observability tools, MCP-only services, internal substrate packages, archived experiments, and research fixtures.

**Impact:** Claude Code pays discovery, hook, and MCP costs for capabilities that may not apply. Codex pays additional prompt-wrapper and symlink complexity, and has no native way to avoid Claude-only surfaces.

**Recommendation:** Define install packs: `core`, `review`, `docs`, `research`, `ops`, `observability`, `mcp`, `incubating`, `internal`, `deprecated`. Make Codex install use a smaller default pack and require explicit opt-in for MCP-heavy or Claude-only surfaces.

**Follow-up Bead:** `Introduce Interverse core, review, docs, ops, research, and observability profile packs`

### 4. Generated Review Agents Need Retention, Indexing, And Active Packs

**Severity:** P1
**Convergence:** 3/4 tracks

The root `.claude/agents` corpus is now platform state, not scratch output. Reviewers counted hundreds of generated `fd-*` agents, a multi-megabyte corpus, a stale `.index.yaml`, many stub-tier agents, and mixed generator versions. Prior review artifacts also call out generated-agent lifecycle gaps.

**Impact:** Claude Code and Flux triage pay for stale one-shot expertise. Codex should not inherit a large always-on generated-agent identity corpus. The recall benefit of rare lenses is real, but it should be retrieved, not eagerly loaded.

**Recommendation:** Introduce active packs backed by an indexed agent registry. Load proven/core agents by default, retrieve generated/stub agents by target hash/domain/frequency, and prune or archive stale generated agents with evidence-preserving tombstones.

**Follow-up Bead:** `Implement generated-agent retention, pack-scoped loading, and stale index refresh`

### 5. Worktree Isolation Must Become A Platform Primitive, Not A Local Fix

**Severity:** P1
**Convergence:** 4/4 tracks, adjusted after verification

The recent interlock fix does exist upstream, but the permanent nested `interverse/interlock` checkout was behind and therefore still contained stale isolated-index hook code until refreshed. This revealed a larger boundary problem: root-level cleanliness does not prove nested plugin repos are current, and multi-agent safety depends on which nested hook implementation is actually installed.

**Impact:** Both Claude Code and Codex can operate from stale coordination assumptions. A root checkout can look clean while a nested plugin runs an older, unsafe hook. This is especially dangerous for coordination, authz, publish, and hook plugins.

**Recommendation:** Add nested checkout freshness to Sylveste doctor/status. For multi-agent work, make worktree-based isolation the canonical platform primitive, with shared-checkout reservations as a coordination aid rather than filesystem isolation. Document and test the rollout across Clavain, Interlock, Intermute, and Codex install paths.

**Follow-up Beads:**

- `Add nested plugin checkout freshness gate to Sylveste doctor`
- `Make worktree-first coordination canonical across Clavain, Codex, and Intercore`

### 6. Clavain SessionStart And Hook Surfaces Need A Health Budget

**Severity:** P1
**Convergence:** 2/4 tracks

Clavain's SessionStart hook is large and does many things: setup checks, cache rewrites, Beads health, service queries, context injection, state recording, and cleanup. Interverse adds many more hooks, each with its own fail-open behavior.

**Impact:** Claude Code startup/resume gets slower and less predictable. Codex parity suffers because hook behavior is implicit and not cleanly represented in capability metadata. Hidden mutation in startup hooks also complicates debugging.

**Recommendation:** Split SessionStart into a cached read model plus explicit repair commands. Add a hook health ledger tracking latency, exit status, mutation category, and injected context bytes. Make hook budget regressions visible in doctor and publish checks.

**Follow-up Bead:** `Refactor Clavain SessionStart into cached read model plus hook health ledger`

### 7. Flux-review Needs Cost, Concurrency, And Read-only/Remote Modes

**Severity:** P1/P2
**Convergence:** 3/4 tracks

The Flux-review engine is now short and skill-driven, but its architecture still assumes it can generate specs, create agents, and write artifacts. The engine supports 10/13/16-agent modes with high token estimates. Prior May 4 work already identified concurrency caps, content-addressed caching, embedding triage, and stall rescue as wins.

**Impact:** Claude Code can spend large review budgets unpredictably. Codex cannot safely run the full engine against remote/protected targets without a manual adaptation. Read-only reviews are valuable but not first-class.

**Recommendation:** Add an ephemeral read-only mode for remote/protected targets. Move fan-out policy toward a scheduler contract with explicit concurrency, budget, cache key, retry, partial-results, and timeout semantics. Keep cross-track convergence as the core quality signal, but make cost behavior observable.

**Follow-up Beads:**

- `Add flux-review ephemeral read-only mode for remote targets`
- `Instrument and cap flux-review cost pipeline`

### 8. Interflux Depends On Intersynth Without A Formal Contract

**Severity:** P1
**Convergence:** 2/4 tracks plus prior interflux roadmap research

Interflux delegates synthesis to Intersynth and tells the host not to read individual agent outputs itself. That is the right direction for context hygiene, but the inter-plugin contract is under-specified. The Intersynth plugin exposes agents rather than a stable skill/command contract, and Interflux does not declare a versioned dependency contract.

**Impact:** A standalone Interflux install can appear valid while synthesis behavior is missing or drifted. Codex translation has no clean way to know the dependency is required.

**Recommendation:** Define the synthesis interface: inputs, output schema, error behavior, version range, fallback mode, and conformance tests.

**Follow-up Bead:** `Define and enforce the interflux-intersynth synthesis contract`

### 9. Evidence And Telemetry Boundaries Are Blurry

**Severity:** P2/P1 depending on scope
**Convergence:** 2/4 tracks

Interspect is described as a pillar/cross-cutting evidence system, but packaging and docs do not expose a coherent boundary. Related measurement concerns are split across Interspect, Interstat, Intertrack, Interpulse, Intercheck, Tool-time, Interrank, Clavain calibration files, and Intercore events.

**Impact:** Routing, trust, cost, and calibration decisions cannot rely on one authoritative flight recorder. Codex and Claude Code both need durable, comparable evidence to improve their own routing and workflow choices.

**Recommendation:** Define the evidence-plane boundary. Decide what belongs in Intercore as append-only kernel facts, what belongs in Interspect as analysis/profiling, and what plugin-local telemetry may remain local. Then repackage Interspect to match that boundary.

**Follow-up Bead:** `Repackage Interspect and consolidate evidence telemetry boundaries`

### 10. Workspace Verification Needs A Root-level Affected-module Runner

**Severity:** P2
**Convergence:** 1/4, but high practical leverage

The monorepo contains many Python, Go, and Node subprojects but no root task graph or affected-module runner. Agents currently rediscover verification commands per module.

**Impact:** Claude Code and Codex waste time running too much or too little verification. This also weakens publish and plugin drift gates because there is no single entrypoint for "test what changed".

**Recommendation:** Add a root-level affected-module runner that maps changed paths to test/build/lint commands, with module ownership and known slow tests encoded as data.

**Follow-up Bead:** `Add Sylveste affected-module build and test runner`

## Cross-track Convergence

### Strongest Convergence: Inventory, Install, And Drift

All tracks surfaced the same underlying issue: Interverse needs generated inventory and lifecycle metadata. The adjacent track framed it as plugin/manifest drift. Orthogonal framed it as package ecosystem supply-chain metadata. Distant framed it as maintenance ledger and canonical witness failure. The obsolete-assumption track framed it as a stale "one scaffold fits every plugin" assumption.

**Combined recommendation:** make plugin inventory generated and tiered before doing large public-surface or installer work.

### Strongest Quick Win: Codex Interflux Skill Mapping

Three tracks independently noticed stale `flux-engine` / `flux-research` assumptions against the current `flux-drive` / `flux-review` skill layout. This is a small fix with direct Codex impact.

**Combined recommendation:** do this first, with doctor assertions.

### Most Important Safety Finding: Checkout Freshness And Worktree-first Coordination

All tracks flagged worktree/index coordination. Verification refined the diagnosis: the upstream fix existed, but the nested checkout was stale. That makes the platform problem more general. Sylveste needs freshness gates for nested repos and a canonical worktree-first model across host agents.

**Combined recommendation:** detect stale nested repos in doctor/status, and keep moving shared-checkout behavior out of the critical path.

### Highest Cost Opportunity: Generated Agents And Flux-review Fan-out

The May 4 synthesis already identified token savings from routing prefilters, content-addressed caching, and concurrency caps. This review adds a structural target: the generated-agent corpus and Flux-review fan-out should be retrieved and scheduled, not eagerly loaded and free-running.

**Combined recommendation:** agent registry active packs plus Flux-review scheduler controls.

## Track-specific Insights

### Track A: Adjacent Platform Architecture

Track A emphasized concrete developer-tooling risks: stale Codex link overrides, generated-agent corpus growth, manifest drift, and preamble budget regression gates. Its most useful extra point was that token budget work should move from one-off optimization reports into publish/doctor gates.

### Track B: Orthogonal Platform Engineering

Track B emphasized platform supply-chain discipline: profile-based install packs, root-level affected-module testing, idempotent publishing, MCP optional/config-error semantics, and component inventory generation. Its strongest new point was treating MCP launcher exit behavior as a contract, not shell-script trivia.

### Track C: Distant Systems Maintenance

Track C emphasized ledgers and flight recorders: measurement-grade event streams, routing decision receipts, hook health budgets, knowledge lifecycle registries, and cache maintenance. Its useful reframing was that Sylveste has many signals but not enough authoritative evidence boundaries.

### Track D: Obsolete-assumption Hunter

Track D found stale assumptions: Codex as translated Claude, one plugin scaffold for all plugin types, Interspect as pillar vs package mismatch, generated review agents as permanent context, and Interflux/Intersynth as an implicit dependency. It also surfaced the important distinction between shipped fixes and stale nested checkouts.

## Recommended Execution Order

1. **Repair Codex Interflux skill mapping.** Small, high-confidence, directly improves Codex.
2. **Add plugin inventory/drift gate.** Creates the data needed for the next steps.
3. **Define plugin tiers and install packs.** Reduces load for both hosts and clarifies marketplace posture.
4. **Add nested checkout freshness gate.** Prevents another "root clean but nested stale" incident.
5. **Retain and pack-scope generated agents.** Reduces discovery/routing cost without losing rare-lens value.
6. **Add Flux-review cost/read-only controls.** Makes the review engine safer and cheaper.
7. **Formalize Interflux/Intersynth contract.** Stabilizes the most important review dependency.
8. **Refactor hook health and SessionStart.** Makes startup behavior observable and budgeted.
9. **Repackage evidence/telemetry boundaries.** Harder, but important for v0.7+ autonomy claims.
10. **Add affected-module runner.** Improves everyday verification and publish safety.

## Follow-up Beads Filed

| Bead | Priority | Title |
|---|---:|---|
| `sylveste-wkjf` | P0 | Normalize interflux skill IDs across Claude manifest, commands, and Codex installer |
| `sylveste-b4ch` | P1 | Generate Interverse inventory from manifests and fail drift in doctor/CI |
| `sylveste-i0sa` | P1 | Define Interverse plugin surface tiers and install profile packs |
| `sylveste-7zw2` | P1 | Implement generated-agent retention, pack-scoped loading, and stale index refresh |
| `sylveste-x1rf` | P1 | Add nested plugin checkout freshness gate to Sylveste doctor |
| `sylveste-n2ma` | P1 | Make worktree-first coordination canonical across Clavain, Codex, and Intercore |
| `sylveste-z55b` | P1 | Refactor Clavain SessionStart into cached read model plus hook health ledger |
| `sylveste-2o0s` | P1 | Add flux-review ephemeral read-only mode and cost controls |
| `sylveste-te7b` | P1 | Define and enforce the interflux-intersynth synthesis contract |
| `sylveste-gd3q` | P2 | Repackage Interspect and consolidate evidence telemetry boundaries |
| `sylveste-6zhe` | P2 | Add Sylveste affected-module build and test runner |

## Synthesis Assessment

Sylveste is strong because it has already built many of the right pieces: Beads, Intercore, Clavain, Interverse, Interspect, Flux-review, generated agents, and cost instrumentation. The performance problem is now second-order: too many pieces are loaded, discovered, or trusted as if the ecosystem were still small.

The single highest-leverage change is a generated platform inventory with lifecycle tiers and drift gates. It unlocks smaller Codex installs, cleaner Claude discovery, safer marketplace publishing, stale-plugin detection, and better public/private boundary discipline.

The surprising finding was the interlock verification twist: the worktree fix was real, but the permanent nested checkout was behind. That is exactly the class of failure Sylveste should prevent: the evidence exists, but the current working surface is stale enough for agents to act on the wrong reality.
