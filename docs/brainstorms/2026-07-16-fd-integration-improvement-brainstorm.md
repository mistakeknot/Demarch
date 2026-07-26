---
artifact_type: brainstorm
bead: none
stage: discover
---

# Significantly Improve fd-integration (+ Agent Registry Extraction)

## What We're Building

Two tracks, one goal.

**Track 1 — fd-integration pilot (wire → ground → generalize):**

1. **Wire:** Add fd-integration to interflux's triage roster (`agent-roster.md` entry; `agent-roles.yaml` line already exists), make its output comply with the Findings Index contract (`- SEVERITY | ID | "Section" | Title` + `Verdict:` first block), and modernize the prompt to flux-gen v5 scaffolding: persona, `risk_addressed` frontmatter, severity examples, anti-overlap, "what NOT to flag" calibration, and a graceful-degradation clause matching its siblings ("if convention files absent, apply generic integration principles and note assumptions").
2. **Ground:** Fuse the agent with intertrace's three tracer libs (`lib/trace-{events,contracts,companion}.sh`) so findings are grep-verified, evidence-typed (verified/declared/missing confidence tiers), not LLM impressions. Eliminate the current split where the `/intertrace` skill and the agent do overlapping checks via disconnected codepaths.
3. **Generalize:** Hybrid substrate — federation path-discovery so any Sylveste-family repo resolves the hub docs (`~/projects/Sylveste/docs/companion-graph.json`, `contract-ownership.md`, currently the *only* copies; 0/61 plugin repos have their own), with code-inferred edges as fallback in repos outside the federation. No more silent 404 of the agent's "First Step (MANDATORY)".

**Track 2 — agent registry extraction:** A thin new interverse plugin owning reviewer-agent identity and dispatch eligibility as one source of truth — replacing the fragmentation across five files/four owners (interflux `agent-roster.md`, `.index.yaml`, `agent-roles.yaml`; intertrust's SQLite trust table; interspect's `routing-overrides.json`, all joining on bare name strings). interflux triage consumes it as sole roster source; fd-integration migrates from its hand entry to become the registry's first external registration.

## Why This Approach

Research (2026-07-16, repo-research agent over intertrace + interflux source) found fd-integration **cannot currently fire at all**: absent from the hand-maintained triage roster, non-compliant with the findings-index output contract, hard-dependent on evidence files that exist only at the monorepo root, and disconnected from its own tracer libraries. "Improve" therefore starts at "make it exist in the pipeline."

**Pilot-first, migrate-under** sequencing was chosen over registry-first because every downstream decision (trust calibration, severity tuning, prompt fixes) is starved without field evidence — fd-integration has zero dispatch history today. Hand-wiring costs one roster entry and starts the evidence clock immediately; the registry lands underneath it later and inherits a live external registrant as its migration test case. This matches the pilot-before-fanout doctrine and keeps every stage independently shippable.

**Registry as own track (not follow-up)** because the identity fragmentation is real and already caused this failure: fd-integration got a model-routing line but no roster entry, and nothing could notice the inconsistency. **Intercore was considered and rejected** as the registry home — it's runtime substrate (events, runs, publishing); agent metadata is a plugin-layer concern, and the ecosystem's own extraction precedent (intersense, intertrust) is thin single-responsibility interverse plugins.

## Key Decisions

*(1-4 from the 2026-07-16 dialogue; 5-10 refined 2026-07-17/18 after a flux-melange pass on this doc — synthesis at `docs/research/flux-melange/fd-integration-improvement-brainstorm/2026-07-17-synthesis.md`, 3 rounds, DRY halt, 19 upheld findings.)*

1. **Scope: staged all-three** — wire, ground, generalize — plus registry extraction, gates inside one goal.
2. **Substrate: hybrid** — hub path-discovery for federation repos + code-inference fallback elsewhere. Rejected: per-repo declaration files (61-repo maintenance tax, drift burden), inference-only (loses declared-intent checks), hub-only (leaves non-federation repos with prose review).
3. **Registry home: new thin interverse plugin, not intercore, not deeper into interflux.** Owns **identity + dispatch eligibility + model routing** (the two interflux files that actually drifted, unified); lifecycle tiers, trust, and exclusions stay with their current owners (flux-agent, intertrust, interspect) as registry consumers. Registration is declarative (manifest scanned from *enabled* plugins, so staleness self-resolves).
4. **Sequencing: pilot-first, migrate-under.** Roster path deliberately changes twice (hand entry now, registry swap later); accepted cost for evidence velocity.
5. **Tracer invocation (melange-ratified):** agent-invoked via a shared `trace-diff` entry script that accepts a **caller-resolved file list** (bead-scoped `/intertrace`, diff-scoped agent) and emits one typed-evidence doc, with a per-review-run cache so N agents on one diff don't re-scan. The script's signature is designed for **Composer injection (`launch.md` Step 2.0.4) as a committed second step** — a call-site swap, not a "revisit if" condition (melange f-002/f-015/f-019: the revisit trigger fires inside this plan, and the Composer seam already exists). **Single tracer codepath is a stage-2 acceptance criterion**, not an open question (f-018).
6. **Federation discovery (melange-verified P0):** precedence chain — explicit override (env/config, unifying the `/intertrace` skill's currently-unassigned `$MONOREPO_ROOT`) → ancestor walk that looks for the **hub docs themselves** (`docs/companion-graph.json` at an ancestor), walking **past `.git` boundaries** — git-toplevel can never be the mechanism (verified: it returns intertrace's own root; f-007/f-009) → explicit "outside federation" state that triggers inference fallback, never a silent 404. Result cached with staleness check (intersense's cache pattern — its only valid role here; it is not a root-discovery precedent, f-008).
7. **Inference noise control:** provenance (`declared`/`inferred`) and evidence-confidence are **separate stored fields** — never overloaded into the P0-P3 severity slot (f-010/f-013 caught the label-space collision with intertrace's evidence-strength tiers). Inference-only findings cap at **P2**; ≥2-signal corroboration gate for reporting an inferred edge; bulk low-confidence gaps aggregate into one summary finding; exclusions live in a "What NOT to Flag" prompt section. Rationale: intertrust scores the agent, not the evidence tier — the ceiling stops fallback noise from eroding trust in the agent's declared-evidence findings.
8. **Identity continuity is a pre-pilot gate (melange convergence spine):** decide the identity-key carry-forward (bare-string continuity vs. alias table vs. migration backfill for `trust_feedback.agent` and routing-override keys) **before the pilot writes its first trust row** — otherwise the migrate-under swap orphans the very evidence the pilot exists to gather (f-004/f-006/f-012).
9. **Wire step adds a roster taxonomy category, not just a row:** fd-integration is a third agent class (plugin-shipped external reviewer) that the Project-vs-interflux-Plugin taxonomy has no slot for; `plugin.json`'s `agents` array is itself an identity-truth source the fragmentation count must include (f-001/f-005).
10. **Success criteria:** fd-integration dispatched on ≥5 cross-module diffs with findings parsing into synthesis; trust rows accumulating with ≥60% accept after ~20 findings; interflux consumes registry as sole roster source (`agent-roster.md` deleted or generated); a **registry corroboration lint** reconciling the registry against each consumer's live view (f-014 — "the cure must not relocate the single point of failure"); stage-3 demo of grounded review inside an individual plugin repo + graceful, explicitly-labeled inference fallback in a non-Sylveste repo.

## Open Questions

*(Refined 2026-07-18. Resolved into Key Decisions above: tracer invocation path (→ KD 5), federation discovery (→ KD 6), noise control (→ KD 7), single tracer codepath (→ KD 5, now an acceptance criterion), registry boundary (→ KD 3).)*

- **Build-fresh vs. extend `flux-agent.py`:** the melange's highest-novelty finding (f-022/f-024) — `flux-agent.py` is a *live* registrar already implementing registry verbs (`promote`/`prune`/`record`) over project-local `fd-*.md`, i.e. a fourth bare-string identity scheme the fragmentation count missed. But it only globs `.claude/agents/` and never sees plugin-shipped agents, so extending it is a scope-widening, not a free lunch. The registry plan must answer build-vs-extend against this live tool, not against inert config. Name for the new plugin (if built fresh) still TBD.
- **Registration manifest shape:** `plugin.json`'s existing `agents` array (already an identity source — f-005) vs. a dedicated reviewers manifest carrying registry fields (`risk_addressed`, domains, `min_model`) the plugin.json schema lacks.
- **Identity-key carry-forward mechanism** (the KD-8 gate's *choice*): bare-string continuity vs. alias table vs. migration backfill. Lightest viable answer is bare-string continuity (registry key == today's name string) — verify it against interspect's override keys before committing.
- **Project-key canonicalization (f-021):** `trust_feedback` keys on `(agent, project=basename(git-toplevel))`, uncanonicalized — two repos sharing a basename silently pool trust history. Fix scope: registry track, intertrust itself, or both?
- **Unscored alternative shapes (explicit deferral):** MCP tool surface, hook-time capture (intertrace ships an empty `hooks.json` stub), and evidence-as-a-service were flagged by the melange as *unscored, not beaten*. Deliberately deferred — revisit only if the Composer-injection step (KD 5) hits friction.
- **Fusion gap from the melange run itself:** the run attempted zero lens fusions; the two hottest clusters (federation-discovery, flux-agent-registrar) never got a DEEPEN pass. If the plan stage wants implementation-grade detail on either, a targeted `/flux-melange --weights=risk-hunt` re-run on the plan doc is the tool.
