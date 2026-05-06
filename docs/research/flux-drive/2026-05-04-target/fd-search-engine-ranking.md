---
agent: fd-search-engine-ranking
discipline: search-engine-ranking
tier: orthogonal
target: /tmp/flux-drive-2026-05-04-target-1777878653.md
generated_at: 2026-05-04T21:00:00Z
---

### Findings Index
- P1 | SER-01 | "ml-routing-replacement" | Agent triage scores all 679+ agents via LLM without cheap candidate-gen
- P2 | SER-02 | "token-efficiency" | Skill routing has no retrieval stage — full ~8K-token skill listing in every turn
- P2 | SER-03 | "ml-routing-replacement" | CASS acted-on signal not fedback into agent tier scoring
- P2 | SER-04 | "ml-routing-replacement" | No freshness gate on tier scores — stale ranker problem
- P2 | SER-05 | "usability" | Position bias in alphabetical skill listing
- P3 | SER-06 | "ml-routing-replacement" | No negative-example mining from zero-finding agent runs

Verdict: needs-changes

### Summary

Sylveste's routing decisions (agent triage in flux-engine, skill routing in Claude Code harness) both skip the cheap candidate-generation stage that search engines use to gate expensive reranking. The full roster (679 Project Agents + 12 Plugin Agents) and full skill listing (~156 skills, ~8K tokens) are presented to the LLM every time. The project has embedding infrastructure (intersearch with nomic-embed-text-v1.5) and session intelligence (CASS) but neither feeds into routing. This is like running a Google search where every query goes straight to BERT cross-encoder reranking without BM25 candidate generation — works, but 10-100x more expensive than necessary.

The gap is especially sharp for agent triage: the SKILL.md scoring formula (`base_score + domain_boost + project_bonus + domain_agent + tier_bonus`) requires LLM judgment to compute `base_score` (0-3 scale: "3=core overlap, 2=adjacent, 1=tangential"). A BM25 or embedding retrieval step could generate a top-20 candidate set for ~200 tokens, then the LLM scores only those 20.

---

### Issues Found

#### SER-01: Agent triage evaluates ALL project agents via LLM (P1 — token-efficiency + ml-routing-replacement)

**Axis:** ml-routing-replacement / token-efficiency

**Search-engine discipline tie:** In Google's two-tower retrieval architecture, the query tower and document tower generate embeddings independently; cosine similarity over the full index (millions of docs) runs in <10ms. Only the top-k candidates go to the expensive BERT cross-encoder. Sylveste's flux-engine skips the tower phase entirely.

**Current state:**
- `interverse/interflux/skills/flux-drive/SKILL.md` Step 1.2b (lines 209-221) defines the scoring formula requiring LLM judgment for `base_score`.
- `.claude/agents/.index.yaml` shows 679 total Project Agents (281 generated, 215 stub, 181 used, 2 proven).
- Plus 12 Plugin Agents and 5 Cognitive Agents in `interverse/interflux/skills/flux-drive/references/agent-roster.md`.
- No pre-filter except heuristic file-type rules (Step 1.2a) that still leave dozens of candidates.

**Proposal:**
1. Add embedding index to agent `.md` files (they're already text — use intersearch's nomic-embed-text-v1.5).
2. At triage time, embed the document profile (summary + detected domains + languages) — ~100 tokens input.
3. Retrieve top-30 agents by cosine similarity in SQLite (intersearch already supports this).
4. LLM scoring phase only evaluates those 30 candidates.

**Estimated savings:**
- Current: ~679 × 50 tokens context + LLM reasoning = ~40K tokens/review for scoring alone.
- Proposed: 100-token embedding query + 30 × 50 = 1.6K tokens + rerank reasoning = ~5K tokens total.
- **Savings: ~35K tokens/review (~85% reduction in triage cost).**

**Difficulty:** M (multi-PR: embed agents, add retrieval query in SKILL.md Step 1.2, modify estimate-costs.sh)

**Risk:** Cold agents (tier=stub, never used) might be systematically ranked low by embeddings if their descriptions don't overlap with common review patterns. Mitigate: add tier bonus to embedding score (not just rerank).

---

#### SER-02: Skill routing has no retrieval stage — full skill listing every turn (P2 — token-efficiency)

**Axis:** token-efficiency

**Search-engine discipline tie:** Modern search engines use BM25 (tf-idf variant) to retrieve 1000 candidates from billions of documents, then LLM reranks top-k. Per `docs/research/2026-04-21-skill-listing-audit.md`, Sylveste lists ~156 skills with ~32K bytes (~8K tokens) in every system prompt.

**Current state:**
- Skill descriptions in YAML frontmatter of each `SKILL.md` file (lines like `description: "..."` in `docs/canon/plugin-standard.md:71`).
- `scripts/perf/extract-trigger-vocab.py:4` notes: "The Claude Code harness indexes skill matches against the `description:` field."
- Full listing included in system-reminder every turn regardless of user message content.

**Proposal:**
1. Use intersearch to embed all skill descriptions (one-time index, ~156 vectors).
2. At turn start, embed user message → retrieve top-10 skills by cosine similarity.
3. Only include those 10 skill descriptions in system prompt (~500 bytes × 10 = ~5K bytes = ~1.3K tokens).
4. Add fallback: if user explicitly types `/plugin:skill`, bypass retrieval and include that skill.

**Estimated savings:**
- Current: ~8K tokens/turn for skill listing alone.
- Proposed: ~1.3K tokens/turn + 200-token embedding overhead = ~1.5K tokens.
- **Savings: ~6.5K tokens/turn (~80% reduction).**
- Over 10 turns: 65K tokens saved — significant for cost-per-session.

**Difficulty:** L (new infra: embedding index for skills, retrieval hook in Claude Code harness or via MCP tool)

**Risk:** Recall loss — if embedding doesn't surface the right skill, user has to type `/plugin:skill` explicitly. Mitigate: use hybrid retrieval (BM25 + embedding) and keep top-3 "most-used-this-session" skills always included.

---

#### SER-03: CASS acted-on signal not fed back into tier scoring (P2 — ml-routing-replacement)

**Axis:** ml-routing-replacement

**Search-engine discipline tie:** Click-through rate (CTR) is ground truth for search ranking. "Acted-on" (user implements a finding, closes a bead referencing it) is Sylveste's analog. CASS tracks sessions (`cass analytics`), and finding-outcome data exists in bead closes, but no pipeline connects them.

**Current state:**
- `interverse/interflux/scripts/flux-agent.py` (lines 597-645) implements `cmd_record()` which updates `use_count` and `last_used` on agent files.
- But `use_count` is "times launched," not "times findings were useful."
- `docs/brainstorms/2026-03-03-b3-adaptive-routing-brainstorm.md:76-77` mentions `hit_rate = (findings acted on) / (total findings)` but it's not implemented.
- CASS has `cass analytics tokens/tools/models --json` but no acted-on-finding tracking.

**Proposal:**
1. Add `finding_acted_on` event type to interspect/CASS pipeline (when a bead is closed referencing a flux-drive finding).
2. Store per-agent hit rate: `acted_on_count / total_findings_count`.
3. Incorporate hit rate into tier bonus: `tier_bonus = tier_base + hit_rate_bonus`.
4. Weekly recompute via cron hook (like FluxBench challenger evaluation).

**Estimated savings:**
- Token savings: indirect — better tier routing means fewer wasted agent runs (each saved agent = ~40K tokens).
- Quality gain: agents with low hit rate get demoted; proven agents with high hit rate get priority.

**Difficulty:** M (multi-PR: interspect event type, CASS integration, flux-agent.py update, weekly cron)

**Risk:** Sparse signal for low-frequency agents. Mitigate: minimum 10 findings before hit rate affects tier; use Wilson confidence interval for small samples (standard in CTR).

---

#### SER-04: No freshness gate on tier scores — stale ranker problem (P2 — ml-routing-replacement)

**Axis:** ml-routing-replacement

**Search-engine discipline tie:** LambdaMART rankers need periodic retraining as document distributions shift. Sylveste's tier scores (`stub→generated→used→proven`) are computed once and decay only via STALE_DAYS=90 pruning, not recomputation.

**Current state:**
- `interverse/interflux/scripts/flux-agent.py:47-49` defines STALE_DAYS=90, PROVEN_MIN_USES=3, PROVEN_MIN_LINES=150.
- `_classify_initial_tier()` (lines 168-182) is called at scan time, not periodically.
- `.index.yaml` shows `generated_at: '2026-04-26T06:30:58'` — index rebuilt manually, not on schedule.
- If agent quality drifts (someone improves an agent's prompt), tier doesn't update until next `flux-agent index`.

**Proposal:**
1. Add `stale_after` field to `.index.yaml` (default: 7 days since last recompute).
2. SessionStart hook checks index freshness; if stale, runs `flux-agent index --rebuild` in background.
3. Consider adding quality signal to tier: `proven` requires not just use_count≥3 but also hit_rate≥0.3 (per SER-03).

**Estimated savings:**
- Token savings: indirect — stale tiers route to wrong agents, wasting budget.
- Risk reduction: prevents over-reliance on once-good agents that have drifted.

**Difficulty:** S (single PR: add freshness check to session-start.sh, add stale_after to index)

**Risk:** Background rebuild during session might race with triage read. Mitigate: atomic write (already done in `_atomic_write()`); triage reads existing index, next session sees fresh.

---

#### SER-05: Position bias in alphabetical skill listing (P2 — usability)

**Axis:** usability

**Search-engine discipline tie:** Position bias is a well-documented phenomenon in search ranking (users click top results regardless of relevance). LLMs exhibit similar bias toward earlier-listed options in prompts. Skills listed alphabetically give `auth`, `browse`, `campaign` higher implicit priority than `validate`, `work`.

**Current state:**
- `docs/research/2026-04-21-skill-listing-audit.md` shows skills listed by plugin, sorted alphabetically.
- System-reminder block lists skills in deterministic order every turn.
- No shuffling, no position rotation, no recency weighting.

**Proposal:**
1. Sort skills by recent-use frequency (most-used-this-session first), then by plugin last-used (frecency).
2. Alternatively: implement retrieval (SER-02) and return results in relevance order, not alphabetical.
3. For debugging: add `--skill-order=alpha|frecency|random` flag to session config.

**Estimated savings:**
- Token savings: none directly.
- UX improvement: skills the user actually wants are more likely to be selected by the LLM on first try.

**Difficulty:** S (single PR: sort logic in skill-listing generator)

**Risk:** Randomization makes debugging harder. Mitigate: log skill order to session metadata; use deterministic seed from session ID for reproducibility.

---

#### SER-06: No negative-example mining from zero-finding agent runs (P3 — ml-routing-replacement)

**Axis:** ml-routing-replacement

**Search-engine discipline tie:** Negative examples (queries that retrieved a document but user didn't click) are crucial for training rankers. When a triaged agent produces zero findings, that's a labeled negative: "this agent was irrelevant for this document type." Sylveste doesn't capture this.

**Current state:**
- `flux-agent.py cmd_record()` only records agents that were launched.
- Zero-finding runs don't decrement use_count or add a negative signal.
- AgentDropout (`config/flux-drive/budget.yaml:50-58`) prunes redundant agents at dispatch time, but doesn't learn from post-dispatch outcomes.

**Proposal:**
1. After synthesis, log `{agent, document_type, finding_count}` to a JSONL.
2. Agents with consistently low finding counts for a document type get a domain-specific penalty.
3. Feed into embedding training: negative pairs = (document_profile, zero-finding_agent).

**Estimated savings:**
- Token savings: agents with low expected yield get filtered earlier (via domain penalty), saving ~40K tokens each.
- Over 100 reviews with 2 wasted agents each: 8M tokens saved.

**Difficulty:** M (multi-PR: logging, domain-penalty computation, optional embedding fine-tune)

**Risk:** Some agents (fd-safety, fd-correctness) correctly produce zero findings when code is safe — penalizing them would be wrong. Mitigate: exempt safety-critical agents (already in `exempt_agents` list); only penalize agents not in that list.

---

### Improvements

1. **Adopt two-stage retrieval for agent triage** — Use intersearch embeddings as the candidate-gen layer; LLM scoring only for top-k. This is the single highest-impact change. Reference: Google's BERT cross-encoder reranking is only applied to BM25 top-1000.

2. **Implement CTR analog via interspect events** — Track `finding_acted_on` signal to close the feedback loop. Without ground truth, the routing model can't improve.

3. **Add freshness gating to tier index** — Weekly automatic recompute prevents tier drift. Model: FluxBench's weekly evaluation cadence (`fyo3.10`).

4. **Hybrid retrieval for skill routing** — BM25 (keyword match on skill description) + embedding (semantic match on user message). Return top-10 instead of all 156. Use the same infrastructure as agent triage.

5. **Position-debiased skill ordering** — Sort by frecency (recent use × frequency) instead of alphabetical. Log order for debugging.

6. **Learning-to-rank pipeline** — Longer term: collect (document_profile, agent, finding_count, acted_on) tuples; train LambdaMART or XGBoost ranker to replace LLM scoring for triage. This is the Intercept pattern applied to agent routing.

<!-- flux-drive:complete -->
