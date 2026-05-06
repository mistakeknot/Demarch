---
artifact_type: brainstorm
bead: sylveste-3xl3.1
stage: discover
date: 2026-05-06
---

# flux-explore --teams: cross-domain debate mode

## What We're Building

A `--teams` flag for `/interflux:flux-explore` that opts into Claude Code's experimental agent-teams primitive (gated by `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, requires Claude Code v2.1.32+) so domain agents from maximally distant fields can directly challenge each other before the cross-domain isomorphism synthesis is written. Falls back to today's subagent path when the feature is unavailable.

The current flux-explore is **generative**, not investigative: each round launches a single Sonnet subagent that designs N agent specs (JSON), writes them to `.claude/agents/fd-*.md`, and a final synthesis subagent reads the accumulated specs (specifically the `expected_isomorphisms`, `source_domain`, and `distance_rationale` fields) and produces a brainstorm doc. The agents themselves never run during exploration — they're designed for later flux-drive review use.

Agent teams change this by letting agents from distant domains *talk*. The hypothesis: a synthesis written by a single agent reading specs is anchored on whatever the first pattern looks like; a synthesis distilled from a debate where domain agents actively challenge each other's framings surfaces structural overlaps that single-pass synthesis misses.

## Why This Approach

**Subagent path bottleneck.** Today's synthesis is one Sonnet reading N spec JSONs. It's effectively summary-of-summaries — anchored on the dominant analogy and biased toward surface similarity. Cross-domain *structural* isomorphism (the high-value finding) requires a second-pass critique that today's pipeline only fakes.

**Mesh topology buys something subagents can't simulate.** Subagents can't message each other; the only edges go back to the caller. Anchoring bias is structural — once one theory is in the synthesizer's context, follow-on reasoning is biased toward it. Direct inter-agent debate (the "competing hypotheses" pattern from the agent-teams docs) is the canonical fix.

**Cost-bounded experiment.** Linear-per-teammate token cost conflicts with the $2.93/landable baseline (see `feedback_long_term_quality_default.md`, cost preamble trim work in sylveste-ynh7). So `--teams` must be **opt-in** — never the default — and scoped to where mesh discourse buys something specific.

## Key Decisions

### 1. Scope of the team-mode change: synthesis only

`--teams` replaces **only Step 4 (Synthesis)** of flux-explore. Rounds 1..N (agent generation) remain identical: a single Sonnet subagent designs specs per round, generate-agents.py writes them. Teams enter at synthesis time when there are accumulated specs to debate from.

Why not put teams in every round? Round-time agent design is itself a generative single-shot task — debate doesn't help much when there's no shared evidence to converge on. Synthesis is where competing interpretations of the same evidence (the accumulated spec set) actually exist. Targeted application maximizes signal-per-token.

**Rejected:** "Target-mode" flux-explore (where agents actually review a real document during exploration and debate findings). Higher signal but much bigger scope — flux-explore today doesn't take a target document. Belongs in a follow-up bead if Approach 1 proves the value.

### 2. Teammate roles: ad-hoc debaters from spec metadata, not fd-\* reuse

The original bead description proposed reusing fd-\* agent files as teammate roles via subagent-definition handoff. On closer inspection, fd-\* agents are reviewer-shaped — their system prompts pull them toward "evaluate this code/doc" framing, not "argue from your domain perspective." Reusing them as teammates fights the agent's own prompt.

Instead: **spawn ad-hoc teammates with purpose-built debater prompts** seeded from each agent's spec JSON (`source_domain`, `focus`, `expected_isomorphisms`, `distance_rationale`). The spec JSON already has exactly the fields a debater prompt needs.

This keeps fd-\* agents pure reviewers (still used by flux-drive) and gives the synthesis-debate variant prompts written for the actual task.

**Trade-off accepted:** the bead's "no rewrite" claim weakens — we're not reusing definition files directly, but the spec JSON is the source of truth and the prompt is generated, so this is still automated, not hand-authored.

### 3. Team size: 5 teammates with split-role lead, max-distance clustering

**Revised post-review (P0 + Convergence 1 fix).** Split the lead role; flip the clustering rule.

- **Orchestrator-lead** (Sonnet): mailbox routing, turn enforcement, round-cap enforcement only. NO synthesis-writing tools. Pure coordinator.
- **Author** (Sonnet): writes the synthesis from the persisted debate transcript at the end. Does not participate in rounds. Receives the transcript as input, not a running summary.
- **3 domain debaters** (Sonnet): each carries one cluster of accumulated agents.
- **1 questioner** (Sonnet): no candidates of their own; only challenges. Forces challenge coverage.

**Clustering rule (P0 fix):** partition specs to **maximize across-cluster distance**, not minimize within-cluster variance. Use farthest-point sampling for cluster seeds, or k-means with a max-min-distance objective on `source_domain` embeddings. Plan-time audit: fail the run if any two cluster centroids are below a minimum distance threshold. This is the original celestial-navigation insight — three sights too close together produce a tight-looking cocked hat that cannot detect bias from current.

Why split lead: chair-plus-author replays single-Sonnet anchoring at the synthesis-write step (Convergence rank 1, 4 independent agents flagged). Whatever the lead's read of the debate is *becomes* the synthesis with no peer check on the lead's framing. Splitting orchestration from authoring is the highest-leverage single change in the review.

Why questioner role: without explicit asymmetric roles (Noh's shite/waki/tsure/jiutai grammar), four debaters all default to assertion mode and no one is structurally tasked with drawing out objections.

### 4. Debate structure: blind R1 commitments, replies-first R2, refuse-to-commit fallback

**Revised post-review** to fix anchoring leak (P1), missing commitments (P1), missing reply discipline (P1), missing escape hatch (Convergence 2).

**Round 1 — blind commitment:** each debater posts BEFORE reading peers (orchestrator gates mailbox visibility until each debater has posted). Each post must include one **named, falsifiable** isomorphism claim of the form "Domain-X-pattern P maps to Domain-Y-pattern Q via mechanism M, falsified by observation O." No hedges. The questioner does not post candidates; only reads the round at the end.

**Round 1.5 — challenge issuance:** mailbox visibility opens; each debater reads peers; questioner issues challenges to each debater (round-robin pre-assigned: debater A → B's claim, B → C's claim, C → A's claim, plus questioner challenges all three).

**Round 2 — reply-first:** each debater **responds to each challenge first** (sed contra style), then optionally proposes new combinations. Orchestrator gates TaskCompleted on every Round-1 challenge having a Round-2 reply or being explicitly listed as orphaned.

**Round cap enforcement (revised):** TaskCompleted hook authority is **not assumed** — the cap is enforced primarily inside the orchestrator's prompt (hard turn-counter, refuse-to-spawn rule) with TeammateIdle as backup. TaskCompleted is used if the v2.1.32+ contract supports pre-creation veto (verified at probe time), otherwise the prompt-level cap is canonical.

**Refuse-to-commit fallback:** if Round-2 candidates from clusters cannot be reconciled — quantified as no isomorphism mechanism cited by ≥2 debaters — the author writes "no fix; clusters incompatible" and falls back to subagent synthesis tagged with the divergence reason. This is a higher-quality failure mode than forcing synthesis from divergent material.

**Plan-approval mode** is irrelevant (no code writes happen).

### 5. Fallback path: detect both flag and version, plus runtime failure

**Revised post-review (P0/P1: semver fragility, runtime launch failure).**

Detection in Step 4:
```bash
teams_available=false
if [[ "${CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS:-0}" == "1" ]]; then
    claude_version=$(claude --version 2>/dev/null | awk '{print $NF}')
    # robust semver compare via sort -V — handles build suffixes
    if [[ "$(printf '2.1.32\n%s\n' "$claude_version" | sort -V | head -1)" == "2.1.32" ]]; then
        teams_available=true
    fi
fi
```

When `--teams` requested but `teams_available=false`: emit a clear notice and fall through to single-Sonnet synthesis path.

**Runtime failure handling (P1):** wrap the team launch in error handling. If the team-spawn API returns an error after detection passes, log `teams_runtime_failure: <reason>` to the brainstorm frontmatter and fall through to subagent path. Do not abort flux-explore mid-synthesis.

**Frontmatter signals:** every flux-explore run that requested `--teams` writes one of `teams_used: true | teams_fallback: detection | teams_fallback: runtime_failure | teams_fallback: divergent_clusters` to its synthesis frontmatter, so post-run analysis can distinguish degradation paths.

### 6. Cost measurement: per-teammate session aggregation, not lead-only

**Revised post-review (P1: ~3-4× cost understatement risk).** Each teammate runs in its own session. interstat captures per-session costs; "before/after the synthesis stage" measurement on the parent session likely captures only the lead's tokens.

**Pre-flight verification probe (REQUIRED before implementation):** confirm `interstat session-cost` aggregates child sessions via parent linkage. If yes, frontmatter `synthesis_cost_usd` reads parent-aggregated cost. If no, capture per-teammate session IDs at spawn time and sum explicitly.

**Sentinel rule:** if any teammate's cost cannot be attributed at synthesis-write time, write `synthesis_cost_usd: incomplete` (not a misleading small number) and `cost_attribution_gap: <reason>` so post-run rollups don't average against a broken signal.

**Pre-flight cost preview:** before spawning the team, print estimated cost (rough teammate × baseline-per-Sonnet-call × expected-rounds) so user opting into `--teams` gets warned about the ~4× baseline burn.

**Baseline comparison:** measure subagent path baseline *on the same spec set in the same run* (run subagent synthesis once, then teams synthesis), compare per-run, not per-corpus-average — so the comparison is informative not cherry-picked.

### 7. Pre-implementation probes (REQUIRED, ~15 min each)

**Added post-review (Synthesis Assessment recommendation).** Three probes must complete before any code lands; each directly answers a P0/P1 finding:

1. **Mailbox topology probe** — spawn a 3-teammate ad-hoc team, have one post a message, observe whether peers see it without the lead intervening. If star-shaped (lead relays everything), the mesh argument is invalid and the design degrades to "lead transcribes a relay" — redesign needed.
2. **TaskCompleted authority probe** — read v2.1.32+ docs/changelog or test whether TaskCompleted hook can veto future task creation. Decides whether the round cap is hook-enforced or prompt-enforced.
3. **Cost attribution probe** — run a known parent+child Claude Code session pair, check whether `interstat session-cost --session=<parent>` returns aggregated child cost or lead-only cost.

If any probe fails or surfaces unexpected behavior, the design needs adjustment, not the implementation. Probes are a hard gate before plan-write.

### 8. Synthesis output: multiple isomorphisms with two-domain support

**Added post-review (bell-foundry insight).** Acceptance criteria upgrade: "synthesis names ≥3 distinct cross-domain isomorphisms, each with two-domain support cited" rather than "synthesis is written." A well-tuned bell holds multiple modes simultaneously; a single-tone synthesis is the failure mode the brainstorm was trying to avoid.

The reviewer rubric for A/B against subagent path scores on:
- (a) number of distinct cross-domain isomorphisms named
- (b) number with two-domain support cited
- (c) presence of unresolved-tensions section (mandatory; empty section is acceptable)

### 9. Debate transcript: persisted as integrity requirement

**Promoted from Open Q to Decision (kiva insight).** Persist the full debate transcript to `docs/research/flux-explore-debates/{slug}/transcript.md` as a synthesis-integrity requirement, not a nice-to-have. Frontmatter of the synthesis doc links to transcript path. This converts the synthesis from "trust the author's read of the debate" to "audit-traceable from transcript." Author writes from the persisted transcript file, not from in-context running summary — so /resume doesn't lose Round-2 insights.

### 10. Spec-JSON-grounded debate (auctoritates)

**Added post-review (disputatio insight).** Debater prompts must require citing specific spec JSON fields by name — e.g., "debater B's cluster's `expected_isomorphism` field claims X — your reply must engage X by name." This makes the spec accumulation load-bearing in the debate (not just team-seeding metadata) and constrains hand-waving.

## Open Questions

1. **A/B benchmark target choice.** What target do we run subagent vs teams synthesis on for the comparison? Probably a recent flux-explore output where the synthesis was thin. Defer to plan time.

2. **Cluster-distance threshold value.** What's the actual minimum cluster centroid distance below which the run fails the audit? Will need calibration on a few real spec sets — defer to plan time, start permissive and tighten.

3. **Resume semantics under /sprint.** Docs note `/resume` does not restore in-process teammates. The transcript-as-integrity decision (#9) makes this less painful — the author can re-run from the persisted transcript without the team — but if /resume hits mid-debate, Round-2 insights not yet posted are lost. Plan should document this as a known limit.

4. **TeammateIdle hook necessity.** With prompt-level cap (Decision #4 revised) plus TaskCompleted as backup, TeammateIdle becomes a third-line guard. Probably not needed for v0; revisit if cap leakage observed.

## Approaches Considered

**Approach 1 (RECOMMENDED): Synthesis-debate, ad-hoc debater roles, 4-teammate fixed size, 2-round capped.**
Smallest meaningful change. Replaces only the synthesis step. Keeps round generation untouched. Bounded cost. Direct A/B against current synthesis path on the same accumulated spec JSONs. Lowest risk; clearest measurement story.

**Approach 2: Target-mode flux-explore with review-debate.**
Flux-explore gains a target document parameter; agents actually review the target through their domain lens; debate happens over real findings. Higher signal but much bigger scope (changes flux-explore's whole shape, not just Step 4). Better as a follow-up if Approach 1 proves the value.

**Approach 3: Full team-driven exploration (rounds + synthesis).**
Each round runs as a team that designs + critiques the next round's domain selection; teammates carry across rounds. Maximally agent-team-shaped but maximum scope and cost; coordination overhead likely exceeds benefit per the docs' warning. Defer indefinitely.

**Lead recommendation:** Approach 1.

## Review Findings Applied (2026-05-06)

This brainstorm was reviewed via flux-review (2 tracks: 5 adjacent + 5 distant agents) — synthesis at `docs/research/flux-review/flux-explore-teams-brainstorm/2026-05-06-synthesis.md`. The review surfaced **1 P0 + 7 P1** findings; all incorporated above. The cross-track convergence detection ranked these as the top issues (independent agents flagging the same underlying flaw):

| Rank | Score | Finding | Decision changed |
|------|-------|---------|------------------|
| 1 | 4 | Lead is chair-plus-author; replays single-Sonnet anchoring at synthesis-write | Decision #3 — split into orchestrator + author |
| 2 | 3 | 2-round cap justified by cost not quality; treated as timer not commitment budget | Decision #4 — refuse-to-commit fallback added |
| 3 | 3 | Round-2 prompt loses challenge-reply discipline | Decision #4 — replies-first rule added |
| 4 | 2 | Cost measurement misses 3 of 4 teammate sessions | Decision #6 — per-teammate aggregation + sentinel |
| 5 | 2 | Synthesis must surface unresolved tensions | Decision #4 + #8 — mandatory unresolved-tensions section |
| 6 | 2 | Cluster choice can re-introduce anchoring (P0) | Decision #3 — flipped to max-distance clustering |

**Empirical signal:** the P0 (cluster-by-similarity collapses triangulation) was caught **only** by the distant track (`fd-celestial-navigation-fix`). No adjacent specialist flagged it. Six of the eight P0/P1 findings come from or were independently flagged by the distant track. This is recursive evidence for the brainstorm's own thesis — cross-domain debate finds bugs in the framing that adjacent specialists read as sensible engineering.

The brainstorm v2 (this revision) is materially different from v1: split lead role, max-distance clustering, blind R1 commitments, replies-first R2, refuse-to-commit fallback, per-teammate cost aggregation, three pre-implementation probes, transcript-as-integrity, multi-isomorphism acceptance criteria, spec-JSON-grounded debate. v1 → v2 changes were all driven by review findings, not new additions.

## Sequencing Decision (2026-05-06)

User selected: **do all three approaches, one after another**. Sequenced as separate beads under the same epic (sylveste-3xl3) with explicit `blocks` dependencies:

1. **sylveste-3xl3.1** — Approach 1 (synthesis-debate). Current sprint. Proves the core hypothesis on smallest possible scope. Outcome (A/B vs subagent path, cost measurement) gates whether Approach 2 is worth the larger rework.
2. **sylveste-3xl3.7** (new) — Approach 2 (target-mode review-debate). Blocked by 3xl3.1. Only kicks off if Approach 1 demonstrates measurable cross-domain isomorphism quality lift.
3. **sylveste-3xl3.8** (new) — Approach 3 (full team-driven exploration). Blocked by 3xl3.7. Furthest-reaching scope; requires evidence from both prior approaches before committing.

Why sequenced rather than parallel: each approach builds on the last, the agent-teams primitive is experimental (can change under us), and the cost ceiling means we want measured evidence at each stage before scaling commitment. Skipping straight to Approach 3 would burn tokens on coordination patterns we haven't validated at smaller scale.
