---
artifact_type: review-target-brief
method: flux-review
target: Sylveste / Clavain / Intercore / Interverse plugin ecosystem
date: 2026-05-21
bead: sylveste-4u0v
---

# Sylveste Platform Update Opportunities — Target Brief

## Review Intent

Identify the highest-leverage opportunities to significantly update and improve Sylveste, Clavain, Intercore, the core pillars, and the Interverse plugin ecosystem for performance in both Codex and Claude Code.

This review should prioritize architecture, obsolete assumptions, old plugin/skill/command approaches, and changes that reduce recurring agent cost or improve reliability. The output should be actionable: a short ranked set of major opportunities plus follow-up Beads.

## Current Snapshot

- Root Sylveste checkout on `zklw` is clean on `main` after cleanup, aside from the active Bead update for this work and one generated Clavain calibration artifact.
- Root README presents Sylveste as an agency platform with six pillars: Intercore, Clavain, Skaffen, Interverse, Autarch, and Interspect.
- Interverse currently contains roughly sixty plugin directories. Many are mature plugins with skills/hooks/commands; several are shell or MCP wrappers with no user-facing skill or command surface.
- The canonical plugin bar is `docs/canon/plugin-standard.md`.
- `/flux-review` is now a short slash command delegating to the `interflux:flux-review-engine` skill. The engine describes 2-4 semantic-distance tracks and cross-track synthesis.
- Existing May 4 multi-axis review (`docs/research/flux-review/sylveste-improvements-multi-axis/2026-05-04-synthesis.md`) already identified token-efficiency and routing wins: content-addressed caching, SessionStart dirty-bit cache, skill-router prefilter, embedding-based agent triage, concurrency caps, stall rescue, Bead dedup, and plugin prefix disambiguation.
- Existing interflux roadmap research found a spec/implementation gap, missing intersynth integration contract, weak flux-review observability, generated-agent lifecycle drift, compact-skill drift risk, and plugin manifest maintenance churn.
- A recent shipped interlock change replaced per-session isolated Git indexes with real worktrees after the root checkout hit a dirty/divergent state. Treat this as evidence that shared-checkout coordination assumptions need upgrading across the platform.
- Relevant open Beads include interflux pre-launch readiness, longitudinal cost calibration, automatic calibration loops, Hermes provider strategy, and v6 trust/evidence mechanisms.

## Review Questions

1. Which older architecture, plugins, skills, commands, or workflows should be replaced, consolidated, or demoted?
2. What would most improve Codex performance: fewer loaded instructions, better skill discovery, tool mapping, local/remote coordination, or different plugin packaging?
3. What would most improve Claude Code performance: slash command ergonomics, hook cost, subagent fan-out, plugin manifests, MCP hygiene, or skill/command architecture?
4. Which Interverse plugins should be core platform, optional packs, incubating experiments, deprecated, or internal-only?
5. Which platform boundaries are unclear today: Sylveste vs Clavain, Intercore vs Interspect, Interverse vs Clavain, Autarch vs OS, public vs private surface?
6. Which review/agent-generation approaches from earlier Interverse versions are now stale because Claude Code, Codex, or the local tooling has changed?
7. What short sequence of Beads should be filed next to convert this review into execution?

## Output Expectations

For each recommendation:

- Name the opportunity.
- Explain why it is high leverage.
- Cite concrete current artifacts or observed repo state when possible.
- State expected impact on Codex, Claude Code, or both.
- State likely effort and risk.
- Suggest a follow-up Bead title if action is needed.
