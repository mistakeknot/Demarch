---
artifact_type: prd
bead: sylveste-3xl3.1
stage: design
date: 2026-05-06
brainstorm: docs/brainstorms/2026-05-06-flux-explore-teams-brainstorm.md
review_synthesis: docs/research/flux-review/flux-explore-teams-brainstorm/2026-05-06-synthesis.md
---

# PRD: flux-explore --teams (Synthesis-Debate Mode)

## Problem

Today's `/interflux:flux-explore` synthesis is a single Sonnet subagent that reads accumulated agent specs (JSON) and writes a cross-domain isomorphism brainstorm. It is summary-of-summaries — anchored on whatever pattern the synthesizer encounters first, biased toward surface similarity over structural isomorphism. Cross-domain isomorphism — the high-value finding flux-explore was built to surface — is the work the synthesis step is *least* equipped to do, because anchoring is structural and a single-agent reading order produces it.

## Solution

Add a `--teams` flag that opts into Claude Code's experimental agent-teams primitive (gated by `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, requires v2.1.32+) for the synthesis step only. Replace the single-Sonnet synthesis with a 5-teammate debate (orchestrator-lead + author + 3 domain debaters + 1 questioner) running a 2-round blind-commit-then-reply protocol, with refuse-to-commit fallback and audit-traceable transcript. Round generation untouched. Falls back to existing single-Sonnet path when feature unavailable, when runtime spawn fails, or when clusters cannot be reconciled.

## Features

### F1: Pre-implementation primitive probes

**What:** Three small probes (~15 min each) that verify Claude Code agent-teams primitive contracts before any production code lands. These directly answer review-flagged P0/P1 risks.

**Acceptance criteria:**
- [ ] Mailbox topology probe documented + executed: spawn 3-teammate test team; observe whether peer posts are visible without lead intervention. Result recorded as `mesh` or `star` in `docs/research/flux-explore-teams-probes/2026-05-06-mailbox.md`.
- [ ] TaskCompleted authority probe documented + executed: read v2.1.32+ docs and (if ambiguous) test whether the hook can veto future task creation. Result recorded as `pre-veto` / `post-only` / `unknown` in `docs/research/flux-explore-teams-probes/2026-05-06-task-completed.md`.
- [ ] Cost attribution probe documented + executed: with a known parent+child Claude Code session pair, confirm whether `interstat session-cost --session=<parent>` returns aggregated child cost. Result recorded as `aggregated` / `lead-only` / `unknown` in `docs/research/flux-explore-teams-probes/2026-05-06-cost-attribution.md`.
- [ ] If any probe surfaces blocking finding (mailbox is star, TaskCompleted is post-only AND prompt-cap is unenforceable, cost cannot be attributed): pause sprint, surface for design adjustment, do NOT implement.

### F2: --teams flag detection, version gate, runtime fallback

**What:** Bash-level gate that decides whether `--teams` mode is available, robust to semver build suffixes and runtime spawn errors. Falls through to single-Sonnet synthesis path when unavailable. Writes frontmatter signals so post-run analysis distinguishes degradation paths.

**Acceptance criteria:**
- [ ] `--teams` flag parsed in flux-explore command's Step 0.
- [ ] Detection helper returns `teams_available=true` only when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` AND `claude --version` parses ≥ 2.1.32 via `sort -V` (handles `2.1.32+build.5`).
- [ ] Runtime team-spawn failure caught; flux-explore writes `teams_fallback: runtime_failure` to synthesis frontmatter and continues with subagent path.
- [ ] Frontmatter signals: exactly one of `teams_used: true | teams_fallback: detection | teams_fallback: runtime_failure | teams_fallback: divergent_clusters` written every run that requested `--teams`.
- [ ] When `--teams` not requested: code path is byte-identical to today's flux-explore (no regression on existing users).

### F3: Max-distance cluster algorithm + 5-role team spawn (with split lead)

**What:** Partition accumulated specs into clusters that *maximize* across-cluster distance (not minimize within-cluster variance), and spawn a 5-teammate team with split orchestrator/author roles plus a dedicated questioner.

**Acceptance criteria:**
- [ ] Clustering function takes N spec JSONs (N ≥ 9) and returns 3 clusters via farthest-point sampling on `source_domain` embeddings (or k-means with max-min centroid distance objective).
- [ ] Plan-time audit fails the run with `teams_fallback: divergent_clusters` if minimum pairwise centroid distance is below configurable threshold (start permissive, tighten on calibration).
- [ ] Unbalanced spec counts handled: if any cluster < 3 specs, rebalance; if rebalance impossible, drop to 4 teammates (lead + author + 2 debaters) with logged degradation.
- [ ] Team spawn produces 5 named teammates: orchestrator (mailbox routing + turn enforcement only, NO synthesis-write tools); author (writes synthesis from transcript); 3 domain debaters (one per cluster); 1 questioner (no candidates, only challenges).
- [ ] Each debater's spawn prompt cites `source_domain`, `expected_isomorphisms`, and `distance_rationale` from its assigned cluster's specs.

### F4: Debate protocol (blind R1, replies-first R2, refuse-to-commit, transcript persistence)

**What:** Round structure that prevents anchoring leak from synthesizer to first-poster, enforces challenge-reply discipline, and produces audit-traceable output. Round cap is enforced primarily at the prompt level (verified hook authority becomes a backup).

**Acceptance criteria:**
- [ ] Round 1 — blind: orchestrator gates mailbox visibility; each debater posts before reading peers. Each post must include one named falsifiable claim of form "Domain-X-pattern P maps to Domain-Y-pattern Q via mechanism M, falsified by observation O."
- [ ] Round 1.5 — challenge: mailbox opens; pre-assigned round-robin challenges issued (A→B, B→C, C→A); questioner challenges all three.
- [ ] Round 2 — replies first: each debater responds to every Round-1 challenge directed at it before proposing new combinations. TaskCompleted (or prompt enforcement, depending on probe outcome) gates round closure on every challenge having a reply or being explicitly orphaned.
- [ ] Round cap enforced: orchestrator refuses to spawn Round 3+ tasks. If TaskCompleted hook can veto, use it as belt-and-braces; otherwise prompt-level cap is canonical.
- [ ] Refuse-to-commit fallback: if no isomorphism mechanism cited by ≥2 debaters at end of Round 2, author writes "no fix; clusters incompatible" stub and falls back to subagent synthesis tagged with divergence reason. Frontmatter records `teams_fallback: divergent_clusters`.
- [ ] Full debate transcript persisted to `docs/research/flux-explore-debates/{slug}/transcript.md` BEFORE author writes synthesis. Synthesis frontmatter links to transcript path.

### F5: Multi-isomorphism synthesis output + cost attribution

**What:** Synthesis acceptance criteria upgrade — name ≥3 distinct isomorphisms with two-domain support, mandatory unresolved-tensions section. Cost capture aggregates per-teammate session, not lead-only.

**Acceptance criteria:**
- [ ] Synthesis doc contains ≥3 distinct named isomorphisms, each citing the two specific source domains and the structural mechanism that transfers. Single-isomorphism synthesis fails the acceptance check.
- [ ] Synthesis doc has a mandatory "Unresolved tensions" section (empty section is acceptable; absent section fails).
- [ ] Cost capture: per-teammate session IDs collected at spawn time; total cost summed across all 5 sessions (or via parent-aggregation if the cost-attribution probe confirmed it works).
- [ ] If any teammate cost cannot be attributed at synthesis-write time: write `synthesis_cost_usd: incomplete` and `cost_attribution_gap: <reason>` to frontmatter — never write a misleadingly small number.
- [ ] Pre-flight cost preview printed before team spawn: estimated cost = teammate_count × estimated_per_session × expected_rounds. User opting into `--teams` sees the ~4× baseline burn warning before the run.

### F6: A/B benchmark harness vs subagent synthesis path

**What:** Per-run comparison of teams synthesis against subagent synthesis on the *same spec set*, scored by a reviewer-agent rubric. This is how acceptance #2 ("synthesis demonstrably surfaces overlaps subagent path misses") gets measured.

**Acceptance criteria:**
- [ ] Optional `--benchmark` flag runs both paths sequentially: subagent synthesis first, then teams synthesis, on the same accumulated specs.
- [ ] Reviewer agent (Sonnet, separate session) scores both synthesis docs on: (a) number of distinct cross-domain isomorphisms named, (b) number with two-domain support cited, (c) presence + content of unresolved-tensions section.
- [ ] Comparison report written to `docs/research/flux-explore-teams-benchmarks/{slug}/{YYYY-MM-DD}-comparison.md` with scores, token counts (per-teammate aggregated for teams), and verdict.
- [ ] At least one benchmark run executed during this sprint on a real prior flux-explore spec set; results captured as the empirical signal for whether `--teams` is worth the cost.

## Non-goals

- Approach 2 (target-mode review-debate where agents review a real document) — separate bead `sylveste-3xl3.7`, blocked by 3xl3.1.
- Approach 3 (full team-driven exploration across all rounds) — separate bead `sylveste-3xl3.8`, blocked by 3xl3.7.
- Reusing `fd-*` agent definition files as teammate roles directly — explicitly rejected in brainstorm Decision #2; debater prompts are generated from spec JSON.
- Plan-approval mode for teammates — irrelevant since debaters don't write code.
- TeammateIdle hook as primary cap mechanism — relegated to third-line guard.
- Changing Round 1..N agent generation in flux-explore — only Step 4 (synthesis) is touched.

## Dependencies

- Claude Code v2.1.32+ at runtime (gracefully degraded fallback handles older versions).
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` environment opt-in.
- `interstat session-cost` capability (probed in F1; influences F5 implementation).
- Existing `generate-agents.py` spec → `.md` pipeline (untouched).
- Existing `flux-engine` skill (untouched; this PRD only changes the synthesis stage of `/interflux:flux-explore`).

## Open Questions

1. **A/B benchmark target choice:** which prior flux-explore output do we use for the F6 comparison run? Defer to plan; pick a recent run where the existing synthesis was thin.
2. **Cluster-distance threshold value:** start permissive (e.g., centroid distance ≥ 0.3 cosine on simple bag-of-words embeddings); calibrate after a few real runs. Defer to plan.
3. **/sprint resume mid-debate:** if /resume hits during Round 2, in-process teammates are gone. Transcript-as-integrity (F4 transcript persistence before synthesis) bounds the loss to "Round 2 turns not yet flushed to transcript." Document as known limit; revisit if observed.

## Success Metrics (Epic DoD)

- Probe verdicts recorded (F1 done) before any production code lands.
- `--teams` mode runs end-to-end on a benchmark spec set without exceeding 4× per-run subagent baseline cost.
- F6 comparison report shows measurable lift (more isomorphisms named with two-domain support OR unresolved-tensions surfaced that subagent path missed) on at least one benchmark target.
- All seven P0/P1 review findings closed via the corresponding feature implementation.
