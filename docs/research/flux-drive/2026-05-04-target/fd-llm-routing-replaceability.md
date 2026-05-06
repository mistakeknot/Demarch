### Findings Index
- P1 | R-01 | "Routing: flux-engine agent triage scoring is LLM work that could be embedding similarity + small classifier" | Today every flux-drive run scores N agents via LLM reasoning; embedding cosine + tier_bonus arithmetic could replace the base+domain_boost computation
- P1 | R-02 | "Routing: skill router pays LLM cost on every turn to reach 'no skill applicable'" | Most user turns don't trigger a skill but the LLM evaluates triggers each turn; regex/embedding pre-filter could short-circuit
- P2 | R-03 | "Routing: bead deduplication on bd create depends on user-discipline 'bd search first'" | Embedding-based dedup gate on title+description is a one-time index per bead, near-zero marginal cost
- P2 | R-04 | "Routing: memory recall (which topic_file is relevant) is implicit LLM reasoning over MEMORY.md index" | Cosine similarity over topic-file titles + first-paragraph would pre-rank top-k for the LLM
- P2 | R-05 | "Routing: voice-fidelity scoring in interfluence:compare uses LLM judgment" | Stylometric features (sentence length distribution, em-dash density, contrastive-reframe regex hits) yield a deterministic score
- P3 | R-06 | "Routing: PR theme classification in /pr-triage is single-shot LLM call per PR" | A keyword-based classifier on PR title + changed paths handles 80% of triage cases

Verdict: needs-changes

## Summary

Five replacements pay for themselves in token-cost-displaced. Ranked by leverage:

1. **R-01 flux-engine triage** — every flux-drive run scores agents via LLM. The scoring formula (`base + domain_boost + project_bonus + tier_bonus`) is already deterministic *if you have* a base relevance score; today the LLM computes that base. Embedding cosine over (target text, agent persona) replaces it. Highest volume + most-mechanical step.
2. **R-02 skill routing** — short-circuiting "no skill applicable" turns avoids the per-turn LLM eval cost across every conversation.
3. **R-03 bead dedup** — solves a workflow-discipline problem (users skip `bd search`) with a deterministic gate.
4. **R-04 memory recall** — embeddings over topic-file titles pre-rank for the LLM.
5. **R-05 voice fidelity** — stylometric features replace LLM-as-judge.

Intercept's distillation pattern (Haiku → log → xgboost) provides the template for R-01/R-02 if simple cosine doesn't reach the precision floor. Training data for all five exists in cass session logs already.

## Issues Found

### R-01 (P1) — flux-engine agent triage: LLM scoring of agent relevance is the highest-volume routing call in the system

**Axis:** ml-routing-replacement
**Current state:** `/home/mk/.claude/plugins/cache/interagency-marketplace/interflux/0.2.68/skills/flux-drive/SKILL.md` Step 1.2b defines: `final_score = base_score(0-3) + domain_boost(0-2) + project_bonus(0-1) + domain_agent(0-1) + tier_bonus(-1 to +1)`. The arithmetic is deterministic, but the *base_score* — "core overlap" / "adjacent" / "tangential" / "excluded" — is LLM judgment. Every flux-drive invocation re-runs this judgment for every agent in the roster (Project Agents + Plugin Agents = 20-50 agents per run). For a typical run with 30 agents at ~150 tok of LLM reasoning per agent decision = 4.5kt of LLM-routing cost per /flux-drive.

**Input vector for ML replacement:**
- target_embedding: 768-dim sentence embedding of (review-target title + first ~500 tokens of content)
- agent_embedding: 768-dim sentence embedding of (agent.md system prompt task-context paragraph)
- domain_match_features: binary vector over project domains (game-simulation, web-api, ...)
- file_pattern_match: binary indicator for diff inputs

**Output:** base_score in {0, 1, 2, 3} (4-class classification) OR continuous relevance ∈ [0,1] thresholded at 0.4/0.6/0.8.

**Precision floor:** Per agent calibration P1: "agent-selection accuracy of an embedding-based router is within 2%" — so target ≥ 0.95 of LLM judgment, measured against a held-out set of 50 historical /flux-drive runs.

**LLM-cost displaced:** ~4.5kt/run × ~10-20 /flux-drive runs/week = 45-90kt/week. At Sonnet input pricing, ~$0.15-0.30/week. Not huge in dollars — but per-user across the platform and recurring forever, this is the dominant routing cost.

**ML-cost:** Embedding generation: ~50ms/agent at first-time index, then cached by `.claude/agents/.index.yaml` (already exists per Step 1.2b). Inference: cosine similarity is microseconds. Retraining is rare — only when agent roster changes.

**Failure scenario:** Today's LLM scoring is invisible cost — no per-run breakdown shows "your agent triage burned 4.5kt." The ynh7-style preamble work has been measuring static preamble; this dynamic per-run cost has never been measured.

**Proposal:** Implement a `flux-agent score-relevance --target <file> --agents <list>` command that returns the score vector deterministically using cached agent embeddings. Wire into `phases/launch.md` Step 1.2b as the *base_score* source. Keep LLM-scoring as fallback for ties or when the embedding score lands in the 0.5-0.7 ambiguous band.

**Difficulty:** S (sentence-transformers model + sqlite cache + 200 lines of Python).
**Risk:** Medium. If the embedding model underperforms on agent-specialty distinctions (e.g., fd-prompt-cache-economics vs fd-context-budget-orchestration), low-quality routing degrades review quality. Mitigation: ensemble with LLM scoring during a 2-week shadow phase, measure agreement rate.

### R-02 (P1) — Skill routing: per-turn LLM evaluation of skill triggers

**Axis:** ml-routing-replacement
**Current state:** Every user turn, the harness presents the skill listing (~150 entries) to the LLM, which decides whether to invoke a Skill or proceed without one. Most turns don't trigger a skill — yet the LLM still walks the trigger list. The cost is two-fold: (a) the listing in the preamble (covered by fd-context-budget-orchestration B-02), and (b) the LLM's per-turn inference cost over that listing.

**Input vector for ML replacement:**
- user_prompt_embedding (768-dim of last user turn)
- recent_tool_history (one-hot over the last 5 tools used)
- skill_keyword_matches (binary vector over skill TRIGGER keywords — extractable from current descriptions)

**Output:** `top_k_skills` (k=3) with relevance scores; if all scores < threshold, emit `no_skill`.

**Precision floor:** ≥ 0.90 recall on "skill should fire" cases (false-negative rate must be low; missed skills are user-invisible cost). False-positive rate can be moderate (extra skill listing surfaced to LLM is cheap).

**LLM-cost displaced:** Per agent calibration P2: "Skill routing burns 200-500 LLM tokens per turn just to decide 'no skill needed'." At ~50 turns/session × 100 sessions/week = 5000 turns × ~300 tok = 1.5Mt/week of routing inference. Conservative.

**ML-cost:** Local embedding + cosine over 150-entry skill index. <10ms inference, sub-cent operational cost.

**Failure scenario:** Skill router today is invisible per-turn LLM cost. If R-02 ships, the harness can short-circuit `no_skill` turns *before* the LLM sees the skill listing — saving the listing tokens too (compounds with fd-context-budget-orchestration B-02).

**Proposal:** Implement a router-classifier in the Claude Code harness layer (likely pluggable via hook). Two-stage:
- Stage 1: regex over user_prompt against skill TRIGGER keywords. If single high-confidence match, route.
- Stage 2: embedding cosine over remaining candidates. If top-1 > 0.7, route. Otherwise emit `no_skill` and skip the LLM eval.

**Difficulty:** M (requires harness-layer integration; Claude Code may need to expose a routing-hook seam).
**Risk:** Medium-high. Pre-LLM gating of skill invocation could miss rare-but-correct skill matches. Mitigation: log all `no_skill` decisions and periodically (offline) compare against LLM-judgment to detect drift.

### R-03 (P2) — Bead deduplication: embedding-based fuzzy dedup gate on bd create

**Axis:** ml-routing-replacement
**Current state:** AGENTS.md and `bd prime` instruct: "`bd search "<kw>" before bd create to avoid duplicates`." This is workflow discipline — the LLM (the agent) decides when to search and what keywords. In practice, agents skip bd search under time pressure or with novel-feeling beads, leading to duplicates. The user's `feedback_proactive_bead_creation.md` and the duplicate-bead bookkeeping pattern (visible in MEMORY.md project Active Brainstorms list) suggests this is a real recurring problem.

**Input vector for ML replacement:**
- new_bead_embedding (768-dim of title + description, computed at `bd create` time)
- index of existing beads' embeddings (precomputed, refreshed on bead-edit)

**Output:** top-3 nearest existing beads + cosine score. If top-1 > 0.85 → block create + show user; 0.7-0.85 → warn + ask; < 0.7 → allow.

**Precision floor:** ≥ 0.95 precision on "is duplicate" (false-positives block legitimate new beads — high friction). Recall can be moderate (missed duplicates are recoverable post-hoc via `/clavain:resolve` or manual cleanup).

**LLM-cost displaced:** Each `bd search` call before `bd create` costs the agent ~200-500 tok of LLM reasoning to formulate keywords + parse results. At 10-30 bd creates/week × 300 tok = 3-9kt/week. Plus the cleanup cost of post-hoc dedup work, which is harder to quantify but high in friction.

**ML-cost:** Embedding gen + cosine over (likely <5000) bead corpus. <100ms.

**Failure scenario:** Duplicate beads accumulate; user runs periodic `/clavain:resolve` cleanup. Search-before-create discipline is the LLM's job and slips under load.

**Proposal:** Add a `bd create --check-dup` mode (default on) that runs the embedding lookup, prints top-3 candidates above threshold 0.7, and asks user `proceed/merge/abort`. Embeddings stored in `.beads/dolt/embeddings.parquet` or alongside the existing dolt schema.

**Difficulty:** S (one new bd command; sentence-transformers model already a Python install).
**Risk:** Low. Default-on is mild friction; can disable with `--no-check-dup` flag.

### R-04 (P2) — Memory recall: which topic_file is relevant to the question

**Axis:** ml-routing-replacement
**Current state:** When agents reference MEMORY.md topic files (`project_meadowsyn.md`, `feedback_no_rhythm_reset.md`, etc.), the agent reads the index in MEMORY.md and decides which file to open. This is an LLM call per question against the topic-file titles + 1-line descriptions.

**Input vector for ML replacement:**
- question_embedding (current user prompt)
- topic_file_index (precomputed: each topic file → embedding of title + first ~200 tok)

**Output:** top-k topic files with cosine scores. Surface top-3 to the agent as a routing hint.

**Precision floor:** ≥ 0.85 recall on "relevant topic file present" — the LLM still gets to read the surfaced files, so false-positives are cheap. False-negatives (missing a relevant file) silently degrade quality.

**LLM-cost displaced:** Less direct than R-01/R-02. Today the cost is "agent reads MEMORY.md index ≈ 1.2kt every time it consults memory." Embedding-based pre-filter would let agent ask `memory_recall("question") → 3 relevant files` and skip the index read. Per session × multiple memory consultations, ~500-2kt/session.

**ML-cost:** Embedding store at `.claude/projects/.../memory/embeddings.parquet`. Refresh on memory file edit. Lookup ~10ms.

**Failure scenario:** Agent reads full MEMORY.md index repeatedly across the session because the index lives in inline preamble, not as a queryable surface.

**Proposal:** Add `intermem:recall <query>` skill that returns top-k topic files via embedding cosine. Document in MEMORY.md as the canonical lookup mechanism. Combine with fd-context-budget-orchestration B-01 (memory shrink) — once Active Projects moves to beads, the topic-file lookup is the canonical recall path.

**Difficulty:** S (intermem skill addition + embedding index).
**Risk:** Low.

### R-05 (P2) — Voice-fidelity scoring in interfluence:compare uses LLM judgment

**Axis:** ml-routing-replacement
**Current state:** `/home/mk/projects/Sylveste/interverse/interfluence/skills/compare/` (skill exists per directory listing) — interfluence:compare uses LLM judgment to score whether output matches the user's voice profile. This is a per-invocation LLM call, today costing ~500-1kt per compare.

The user's voice memory anchors (`feedback_voice_calibration_intersite.md`, `feedback_no_rhythm_reset.md`, `feedback_voice_fidelity_requires_ground_truth.md`) name *specific stylometric markers*: triads vs pairs, em-dash density, contrastive reframes, "one's" usage, sentence-length rhythm. These are extractable features.

**Input vector for ML replacement:**
- sentence_length_distribution (mean, p50, p90)
- em_dash_density (em-dashes per 100 tokens)
- contrastive_reframe_count (regex: `not X — Y` or `not X but Y`)
- triad_count vs pair_count (n-gram pattern)
- "one's" frequency
- ai_phrase_count (regex over the AI-tell list from interfluence corpus)

**Output:** voice_fidelity_score ∈ [0,1] + per-feature breakdown for actionable feedback.

**Precision floor:** ≥ 0.85 correlation with user's hand-graded scores on a held-out set. The user's `feedback_voice_fidelity_requires_ground_truth.md` directly cautions against surface-pattern claims without ground truth — so the classifier MUST be evaluated against user-graded examples, not LLM-judged.

**LLM-cost displaced:** ~500-1kt per compare × invocation frequency (low — interfluence is craft mode, not session-default). Modest aggregate.

**ML-cost:** Pure regex + counting + Python statistics. No embedding model required.

**Failure scenario:** LLM compare today gives prose feedback ("your sentence rhythm is good but the dash density is high") that's actionable. A pure-stylometric score loses prose feedback. Mitigation: hybrid — emit deterministic score + LLM prose only when score < threshold (saves cost on already-good outputs).

**Proposal:** Implement `interfluence:compare-fast` as a deterministic stylometric scorer. Keep `interfluence:compare` (LLM) as the fallback for low-scoring outputs needing prose feedback. Document the stylometric feature list in interfluence's voice-profile schema.

**Difficulty:** S (Python script + regex library + sentence-tokenizer).
**Risk:** Low. The user has already named the load-bearing markers in feedback memory.

### R-06 (P3) — PR theme classification in /pr-triage

**Axis:** ml-routing-replacement
**Current state:** `/clavain:pr-triage` skill description: "Triage all open PRs — batch by theme, review with parallel agents, generate report, walk through decisions." Theme assignment is LLM work over PR title + body + changed-files list.

**Input vector for ML replacement:**
- pr_title_keywords (regex over common themes: docs, fix, feat, refactor, test, chore)
- changed_paths (top-level dir of each changed file → theme weight)
- pr_size (small/medium/large)

**Output:** theme label (e.g., docs / infra / feature / fix / refactor) + confidence.

**Precision floor:** ≥ 0.80 for top-1 theme match. Multi-theme PRs are inherently ambiguous; the classifier returning top-2 with confidences is acceptable.

**LLM-cost displaced:** ~100-300 tok per PR × N PRs in queue. Modest.

**ML-cost:** Trivial — title-keyword regex + path-prefix dict.

**Failure scenario:** Today's LLM theme classification mostly works because it's high-context. The displacement opportunity is small in absolute tokens but reduces the "warm-up" cost of starting `/pr-triage`.

**Proposal:** Implement as a regex+lookup pre-classifier in `/pr-triage`. Surface theme as an LLM hint, not as a hard route — the LLM still reviews each PR.

**Difficulty:** XS.
**Risk:** None.

## Improvements

1. **Cass log distillation pipeline (Intercept template):** Adopt the same Haiku → log → distill pattern that Intercept uses. For R-01 (agent triage) and R-02 (skill router), capture LLM decisions in cass logs, distill periodically into xgboost/embedding-classifier checkpoints. Stand up `scripts/distill-router.sh` as a scheduled job.
2. **Routing replaceability scorecard:** Add `intermux:agents` or `interspect:interspect-effectiveness` reports that quantify "LLM-routing cost displaced this week" so the win shows up alongside the ynh7-style preamble savings.
3. **Embedding-cache infrastructure:** Sylveste already has `.claude/agents/.index.yaml` (per Step 1.2b tier_bonus lookup). Generalize this into `.claude/embeddings/` with separate stores for {agents, skills, beads, topic-files}. One refresh discipline, used by R-01 through R-04.
4. **Precision-floor monitoring:** Each replaced LLM-route emits a "would the LLM have agreed?" canary at 1% sample rate. Drift detection prevents silent quality regression.

<!-- flux-drive:complete -->

--- VERDICT ---
STATUS: warn
FILES: 0 changed
FINDINGS: 6 (P0: 0, P1: 2, P2: 3, P3: 1)
SUMMARY: Five replaceable LLM-routing decisions identified. Top two: flux-engine agent triage (~4.5kt/run × 10-20 runs/week = 45-90kt/week) and skill routing (~1.5Mt/week of per-turn 'no-skill' inference). Bead dedup, memory recall, and voice fidelity are smaller wins with cleaner deterministic features. Intercept's Haiku→log→xgboost template applies directly.
---
