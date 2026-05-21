---
artifact_type: review-synthesis
method: flux-review
target: /home/mk/projects/Sylveste/interverse/interflux
target_description: interflux plugin (multi-agent review + research engine, 17 agents, 7 commands, 1 skill, 2 MCP servers, 338 code files, ~60 MB)
tracks: 3
track_a_agents: [fd-cc-plugin-architect, fd-multi-agent-orchestration, fd-python-cli-ecosystem, fd-mcp-integration, fd-hook-lifecycle]
track_b_agents: [fd-academic-publishing, fd-release-engineering, fd-doc-review-platform, fd-standards-editing]
track_c_agents: [fd-monastic-scriptoria, fd-tidal-harmonic-analysis, fd-ikebana-negative-space, fd-lost-wax-casting]
date: 2026-04-17
models:
  track_a_design: opus
  track_a_review: opus
  track_b_design: sonnet
  track_b_review: sonnet
  track_c_design: opus
  track_c_review: sonnet
  synthesis: opus
refusals: []
---

# Interflux — Multi-Track Flux-Review Synthesis

## Execution Summary

- **Tracks run:** 3 (adjacent, orthogonal, distant). No tracks refused.
- **Agents applied as perspectives:** 13 total (5 + 4 + 4). None produced the synthetic Usage Policy refusal; the v0.2.59 safety fixes (Apply-the-perspective-of framing, common-preamble strategic-verb removal) held.
- **Models:** Opus for Track A review + Track C design + synthesis (per `--quality=balanced`); Sonnet for Track B review + Track C review + routine designs. No fallback triggered.
- **Findings output:** `2026-04-17-track-a-adjacent.md`, `2026-04-17-track-b-orthogonal.md`, `2026-04-17-track-c-distant.md` in this directory.

## Critical Findings (P0/P1)

### P0 — Architectural

**CF-1: PostToolUse hook fires unbounded on every Edit/Write** (Track A, A-P0-1)
The `hooks/hooks.json` PostToolUse matchers for `Edit` and `Write` have no path-scope. `check-compact-drift.sh` runs on every file edit in any project the user works in. Fix: scope matcher to `${CLAUDE_PLUGIN_ROOT}/**` or move the check to `PreCompact`.

**CF-2: MCP servers exit code 0 on missing API key, looking healthy while broken** (Track A, A-P0-2)
`openrouter-dispatch/index.ts` lines 5-9 (and `scripts/launch-exa.sh` same pattern). Claude Code's MCP manager cannot distinguish "missing config" from "working" — calls silently fail. Fix: exit 78 (EX_CONFIG), not 0.

### P1 — Cross-Plugin Coupling

**CF-3: Cross-plugin library discovery via `find ~/.claude/plugins/cache`** (Track A, A-P1-3)
Every sourced lib (clavain's `lib-routing.sh`, interserve templates, interspect's `lib-trust.sh`) resolves via path-globbing a cache directory. Three silent-failure modes: version skew, non-deterministic `head -1`, stale unpublished caches. Fix: an `intercore` manifest discovery with `api_version`, or explicit plugin dependencies.

**CF-4: Openrouter rate-limit and spend-ceiling are per-process, lost across invocations** (Track A, A-P1-5)
State in `tokenBucket` and `cumulativeSpendUsd` is in-memory. 10 sequential flux-review runs can each burn the full rate and the full $1 ceiling independently. Fix: persist state to `~/.config/interflux/openrouter-state.json` with flock, matching the pattern `findings-helper.sh` already uses.

### P1 — Editorial / Release Discipline

**CF-5: Findings have no provenance block** (Track B, B-P1-1)
Finding files are keyed by agent name but carry no `{model_id × agent_version × template_version × reviewed_at × project_commit}` tuple. Contested findings cannot be reproduced. Fix: mandatory provenance frontmatter on every agent output.

**CF-6: `model-registry.yaml.lock` is 0 bytes — fake lockfile semantics** (Track B, B-P1-3)
The `.lock` suffix implies package-manager semantics that don't exist. Either populate with resolved models + pricing snapshots or delete. Fake lockfiles are a release-engineering footgun.

**CF-7: Reaction-round aggregate metrics mix severity bands** (Track C, C-P1-2)
Gini and novelty are computed across the whole findings set. A P0 Gini pathology (overlapping real bugs) is different from a P3 Gini pathology (one reviewer is chatty). Fix: decompose fixative signals per severity band, per domain axis — the tidal harmonic pattern.

### P1 — Concurrent-Write Safety

**CF-8: No burnout verification between agent `.md` writes and synthesis reads** (Track C, C-P2-4)
`.md.partial → .md` rename can race a synthesis read. The skill acknowledges the risk; the mitigation (timestamped OUTPUT_DIR) is partial. Fix: checksum agent outputs twice with a wait, reject files whose hash changes.

## Cross-Track Convergence (Highest-Confidence Signal)

### Convergence 3/3 — Silent failure as architecture

Tracks A, B, and C all independently surfaced the problem of **undetected failure modes that look like success**:
- Track A (fd-mcp-integration): MCP servers exit 0 on missing keys; hooks never report the drift check's own failures.
- Track B (fd-release-engineering): the `.lock` file is empty but carries lockfile semantics; cold-start canary has no time-box.
- Track C (fd-lost-wax-casting, fd-monastic-scriptoria): no burnout-verify, no signature-mark, no quire-mismatch detection.

**This is the project's dominant structural weakness.** Every pipeline has a "silent OK" path that makes real failures indistinguishable from success. The convergence across distant reasoning paths confirms this is not a surface issue but an architectural pattern.

**Fix direction:** Interflux needs a first-class `VerificationStep` primitive that every phase passes through. Not a try/except. An explicit contract: "this step emits one of {VERIFIED, FAILED_VERIFICATION, UNVERIFIABLE}. UNVERIFIABLE is not a success." The silent-failure fixes from prior Phase 1 work address individual instances; this is the underlying pattern.

### Convergence 2/3 — Provenance and identity

Tracks A and B both flagged provenance gaps:
- Track A (plugin descriptor counts that drift from filesystem reality).
- Track B (findings lack reviewer-of-record metadata; tier transitions have no changelog; fixture edits invalidate baselines silently).

**Fix direction:** Every artifact interflux produces (finding, knowledge entry, tier promotion, fixture edit, model-registry update) needs a **content-addressed provenance block**. This is the release-engineering missing primitive.

### Convergence 2/3 — Single-number aggregates hide multi-modal signal

Tracks B and C both flagged the aggregate-metric problem:
- Track B: fixtures get one `qualified_baseline`, but different fixtures test different competences.
- Track C: Gini/novelty aggregated across severities mix P0 pathology and P3 noise.

**Fix direction:** Replace aggregates with vectors. Per-fixture baselines (not a single average). Per-severity-band discourse health. Per-agent-domain specific scores rather than one triage score.

## Track-Specific Unique Insights

### Track A (Adjacent) unique

- **A-P2-9: flux-review command is 551 lines and should be a skill, not a command.** The other commands are 9-96 lines. This structural misfit is invisible without Claude Code plugin-authorship expertise.
- **A-P2-10: Progressive enhancements have no adoption telemetry.** The qmd/lib-routing/lib-interspect skip paths might be dead — no way to tell.

### Track B (Orthogonal) unique — Highest Surprise Value

- **B-P2-5: "Discourse" naming collides with Discourse-the-forum.** A Gerrit/Review Board user reading the plugin listing will misread the system as forum integration. This is invisible from within the Sylveste vocabulary and is exactly the kind of finding parallel-discipline tracks exist to surface.
- **B-P2-8: No "reflexive review" COI declaration.** When interflux reviews itself (as this campaign is doing!), there's no structural warning. Academic publishing solved this; code review hasn't.
- **B-P1-2: No errata/retraction path for withdrawn findings.** `/interspect:correction` is feedback, not formal retraction tied to a stable finding ID.

### Track C (Distant) unique — Mechanism-Level Isomorphisms

- **C-P1-3 (mikomi): The prompt template incentivizes filling P3 even when empty.** A one-sentence prompt change would authorize "no P3 findings" as positive signal — fixing an issue invisible from within plugin-architecture or release-engineering vocabularies.
- **C-P2-6 (correctorium): Knowledge compounding is self-reviewing.** The finding agent also canonicalizes the pattern — a well-known failure mode in medieval scribal transmission. Fix: compound only after N independent reviews confirm.
- **C-P1-1 (signature marks): Concurrent runs can cross-contaminate OUTPUT_DIR.** The skill itself acknowledges this via timestamp suffixing, but the fix is incomplete; a quire-mark per agent output would be a deterministic defense.

## Top 5 Architectural Recommendations

1. **Establish a `VerificationStep` contract across all phases.** Every phase transition returns one of {VERIFIED, FAILED_VERIFICATION, UNVERIFIABLE} with emitted evidence. Makes the "silent OK" class of failures (CF-1, CF-2, CF-8) a category error rather than individual bugs. (Convergence 3/3.)

2. **Add provenance frontmatter to every artifact interflux writes.** Findings, knowledge entries, tier transitions, fixture changes, registry updates. `{agent_version_hash, model_id, model_api_version, template_version, project_commit, timestamp, run_uuid}`. Solves CF-5 and enables the errata/retraction path (B-P1-2) and the quire-mark pattern (C-P1-1). (Convergence 2/3 + high-value unique.)

3. **Scope the PostToolUse hook and fix MCP exit codes.** Two independent but simple changes that together eliminate the largest class of invisible-cost problems (CF-1 + CF-2). Both are under 20 lines of change. Highest ratio of impact to effort.

4. **Refactor `commands/flux-review.md` into `skills/flux-review/`** and remove Composer dead code in one atomic pass. 551 lines of command is wrong shape for Claude Code's plugin model, and partial Composer removal leaves ghost conditionals worse than full removal (A-P1-4, A-P2-9).

5. **Decompose aggregate fixative metrics into per-severity, per-domain vectors.** (CF-7.) Then use the vectors to drive per-band synthesis decisions. This is the tidal-harmonic insight and is the most concrete improvement to the reaction-round architecture. Applies as well to FluxBench per-fixture baselines.

## Semantic-Distance Value Assessment

Did the outer tracks contribute insights qualitatively different from the inner track?

**Yes, clearly.** Track B supplied the provenance / errata / COI / naming-collision findings that the plugin-architecture lens could not reach — those require an outside-the-vocabulary reader. Track C supplied three mechanism-specific findings (mikomi, correctorium, signature-mark) that name implementation paths Track A would never propose. The convergence across all three tracks on "silent failure as architecture" was the highest-confidence signal and is the most important finding — it would not have been visible from Track A alone, because from inside Claude Code plugin expertise each silent-OK case reads as a local bug, not an architectural pattern.

The garden-salon finding that each distance tier produces qualitatively different insights holds here: adjacent gave architectural debt, orthogonal gave editorial discipline, distant gave mechanism-level implementation patterns.
