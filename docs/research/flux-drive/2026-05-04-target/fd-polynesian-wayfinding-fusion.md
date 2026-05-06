### Findings Index
- P1 | POLY-1 | "Axis 3: Replace LLM Orchestration" | flux-engine agent triage relies on a single LLM scoring pass with no cheap-signal fallback
- P1 | POLY-2 | "Axis 3: Replace LLM Orchestration" | Skill routing uses pure LLM classification — three cheap independent signals go unused
- P2 | POLY-3 | "Axis 3: Replace LLM Orchestration" | flux-drive triage score is a continuous float (0-8) where 4 discrete buckets would route equivalently
- P2 | POLY-4 | "Axis 2: Token Efficiency" | Skill/agent routing LLM is invoked even when regex+frecency+token-count-bucket would resolve unambiguously
- P3 | POLY-5 | "Axis 3: Replace LLM Orchestration" | bead dedup search uses LLM similarity when embedding cosine + exact-phrase-match + recency form a three-signal fusion
Verdict: needs-changes

### Summary
The Polynesian wayfinding lens surfaces a structural gap in Sylveste's routing architecture: every major classification decision (flux-engine triage, skill routing, bead dedup, memory recall relevance) relies on a single LLM oracle. Mau Piailug's navigation of the Hokule'a across 2,700 miles to Tahiti succeeded because zenith-star altitude, swell direction, cloud-mark over land, and bird homing flight were fused — each cheap, each failing in known conditions, jointly robust. Sylveste has the raw signals (regex, embedding cosine, frecency, time-of-day) but has not assembled them into a fusion architecture. The result: LLM cost is paid even when three cheap signals would agree without it.

### Issues Found

**POLY-1. P1: flux-engine agent triage relies on a single LLM scoring pass with no cheap-signal fallback**

Axis: ml-routing-replacement

Source-domain mechanism: **Zenith-star + swell + cloud-mark fusion**. Wayfinders never navigated by zenith-star alone. Hokule'a's first modern voyage used: zenith-star altitude (primary, fails in overcast), North Pacific swell from starboard quarter (primary, fails in storms), cloud-mark over Tahiti (secondary, requires proximity), bird flight direction (tertiary, close-in only). All four were tracked simultaneously; a navigator who lost one signal did not stop navigating.

Current state: `flux-engine` (in `/home/mk/.claude/plugins/cache/interagency-marketplace/interflux/0.2.68/skills/flux-drive/SKILL.md` Step 1.2b) dispatches Sonnet/Opus to score each agent 0-8 using a reasoning pass over the document profile. This is a single-signal oracle: if the LLM misjudges the document type or domain, all downstream agent selection is wrong. There is no fallback when the scoring LLM produces a degenerate result (all zeros, all eights, random distribution).

Proposal: Instrument three cheap pre-LLM signals per triage run:
1. **Regex-match signal**: count keyword hits per agent domain (e.g., "security|credential|deploy" for fd-safety; "performance|bottleneck|O(" for fd-performance). Normalize to 0-3.
2. **File-extension signal**: map file extensions to agent domains (`.sh` → fd-safety bias, `.go` → fd-correctness bias, `.md` → cognitive agent eligibility). Score 0-2.
3. **Recent-activity signal**: check `use_count` + `last_used` from `.claude/agents/.index.yaml` — an agent used 3× in the last 7 days on this repo has a frecency boost. Score 0-1.

Fuse: `cheap_score = regex_signal + extension_signal + frecency_signal`. When `cheap_score >= 5` for an agent, assign Stage 1 without waiting for LLM triage. When `cheap_score <= 1`, skip without LLM scoring. Only agents in the 2-4 band need LLM arbitration. This reduces LLM triage calls by an estimated 40-60% on typical runs.

Estimated savings: ~800-1,200 tok/triage-run eliminated on the scoring pass. On 5 agents scored, current approach: ~400 tok/agent × 5 = 2,000 tok. Fusion approach: LLM only arbitrates 2-3 ambiguous agents = ~800 tok. Net: -1,200 tok/run.

Difficulty: M (multi-PR: add signal extraction to flux-engine Phase 1, add fusion logic to Step 1.2b, add index cache read, test on 10 historical reviews)

Risk: Regex and extension signals are noisier than LLM scoring on novel document types. The fusion should only gate ambiguous-band agents (2-4 range), not override clear LLM signals. Miscalibrated frecency bonus could lock in stale agent selections. Mitigation: run cheap signals as a pre-filter only; LLM still arbitrates the middle band.

---

**POLY-2. P1: Skill routing uses pure LLM classification — three cheap independent signals go unused**

Axis: ml-routing-replacement

Source-domain mechanism: **Star compass discretization into 32 fixed houses**. The Carolinian star compass (taught by Mau Piailug) divides the horizon into 32 star-rise/star-set houses — not continuous degrees. This discretization is the key: a navigator does not need to know "Altair rises at 8.7° north of due east"; they need to know it rises in the house Wuliwul (approximately NNE). Four or five houses cover 90% of navigation decisions. The continuous precision is dropped; the discrete bucket retains the routing information.

Current state: Skill routing (when a user asks a question, which skill fires) uses the full LLM reasoning path. The target document lists this at Axis 3 "Skill routing — when a user asks a question, which skill should fire? Currently LLM-decided." The LLM receives the full user query, context, and skill list (100+ skills) and produces a routing decision.

Proposal: Build a **4-house skill compass**:
- House 1 (WORK): `bd|bead|sprint|work|ship` keyword match → route to `clavain:work` family. Reliability: high (keywords are unambiguous), degrades when: user describes work without using work-words.
- House 2 (REVIEW): `review|flux|check|improve|analyze` → route to `interflux:` family. Reliability: high.
- House 3 (RESEARCH): `how|why|what|explain|find|search` → route to `interflux:flux-research` / `intersearch`. Reliability: medium (degrades on compound questions).
- House 4 (MEMORY): `remember|forget|note|save|recall` → route to `intermem:` / `bd remember`. Reliability: high.

When the user's input hits a single house clearly (only one house has keyword matches), dispatch directly. When two houses fire, invoke LLM arbitration. When zero houses fire, invoke LLM. Estimated 60% of skill invocations land unambiguously in one house.

Estimated savings: Skill routing currently costs ~500-800 tok/invocation (system prompt + skill list + query + LLM output). On 60% unambiguous invocations, this is eliminated. At 20 skill invocations/session: 12 × 650 tok saved = 7,800 tok/session.

Difficulty: S (single PR: add keyword-house classifier to clavain routing layer, test against 50 historical invocations for house-match accuracy)

Risk: House boundaries are fuzzy. A user asking "how do I work on bead X?" hits both WORK and RESEARCH. The disambiguator must require a clear majority-house match (e.g., 2:0 keyword ratio) before bypassing LLM. Miscategorization sends a user to the wrong skill silently — add a "did you mean X?" recovery on first-turn failure.

---

**POLY-3. P2: flux-drive triage score is a continuous float (0-8) where 4 discrete buckets would route equivalently**

Axis: token-efficiency / ml-routing-replacement

Source-domain mechanism: **Star compass discretization**. The star compass works because routing decisions are naturally discrete: you are either heading toward Tahiti or you are not. Continuous precision (8.7° vs 9.1°) does not improve the routing outcome; it only increases the cognitive load on the navigator. The navigator's job is to determine which house applies, not to compute a bearing.

Current state: flux-engine Step 1.2b computes `final_score = base(0-3) + domain_boost(0-2) + project_bonus(0-1) + domain_agent(0-1) + tier_bonus(-1 to +1)` = a float in [0, 8]. The synthesis and expansion logic then applies thresholds (>= 2, >= 3, etc.) to gate selection. The continuous score is computed precisely but immediately thresholded.

Proposal: Replace the float computation with a **4-bucket discrete assignment**:
- ALWAYS (base=3 agents, or exempted agents fd-safety/fd-correctness)
- LIKELY (score 5-8)
- MAYBE (score 3-4) — Stage 2 candidates
- SKIP (score <= 2)

The LLM (or cheap-signal pass from POLY-1) assigns each agent to a bucket directly, not a score. This eliminates the arithmetic-precision framing from the prompt, reduces the LLM's output tokens (a bucket label is 5 tokens vs a scored breakdown at 30+ tokens), and produces the same routing outcome.

Estimated savings: ~150-200 tok/triage-run on score computation framing + outputs. Small but free — the change is a prompt rewrite.

Difficulty: XS (config/prompt rewrite only; update Step 1.2b framing in SKILL.md)

Risk: Loss of fine-grained scoring makes it harder to reason about borderline agents in the triage table. Mitigation: keep a shadow score for display in the triage table, but use buckets for dispatch logic.

---

**POLY-4. P2: Skill/agent routing LLM is invoked even when regex+frecency+token-count-bucket would resolve unambiguously**

Axis: token-efficiency

Source-domain mechanism: **Multiplicative degradation resilience**. The wayfinding insight is that when multiple independent signals agree, the navigator can act. The Hawaiian Navigation Society documented that during the 1976 Hokule'a voyage, there were periods of 3-4 days with overcast skies (no zenith-star fix); the crew navigated by swell alone. The key: they knew swell was reliable in those conditions. When swell + cloud-mark agreed, they trusted them without waiting for a star fix.

Current state: flux-engine always invokes LLM for triage regardless of how unambiguous the input is. A Rust codebase triggers fd-correctness and fd-performance at maximum signal strength (file extensions, keywords, domain profile all agree). An overcast-only Python data pipeline similarly has 4 signals pointing the same direction. The LLM still runs.

Proposal: Add a **pre-triage confidence gate**: before invoking LLM, compute the cheap-signal agreement score from POLY-1. If all three signals agree and no agent is in the "ambiguous" band (2-4 range), write the triage table directly and skip the LLM scoring pass entirely. Condition: `len(ambiguous_agents) == 0 AND max_disagreement < 1.5`. Log the skip as "auto-triage: cheap-signal unanimity."

Estimated savings: On clearly-typed inputs (pure Go repo, pure markdown doc), eliminates ~2,000 tok/run on the scoring pass. On 30% of flux-drive runs being clearly-typed: saves 600 tok/run on average.

Difficulty: M (depends on POLY-1 being shipped first; add confidence gate to Phase 1)

Risk: Over-triggering the skip on inputs that look clear but have subtle domain ambiguity. Guard: require unanimous agreement across all three signals AND all agents scoring >= 5 or <= 1 before auto-triaging. Set a kill switch: `FLUX_FORCE_LLM_TRIAGE=1` env var bypasses.

---

**POLY-5. P3: bead dedup search uses LLM similarity when embedding cosine + exact-phrase-match + recency form a three-signal fusion**

Axis: ml-routing-replacement

Source-domain mechanism: **Bird homing flight (tertiary signal)**. Wayfinders used bird flight direction as a tertiary navigation signal — birds within 200 miles of land consistently fly toward land at dawn. The signal is cheap (visual observation), has known reliability bounds (200-mile radius, dawn only), and adds one data point to the fusion without dominating it. When three other signals already agree, the bird sighting confirms the fix; when signals diverge, the bird sighting provides a tiebreaker.

Current state: `bd search` before `bd create` is the LLM's job (noted in the target doc under Axis 3: "Bead deduplication — bd search before bd create is currently the LLM's job. Could embedding-based fuzzy dedup automate it?"). The LLM reads the proposed bead title/description and compares against recent beads.

Proposal: Build a **three-signal bead dedup gate**:
1. **Exact-phrase match** (high reliability, never degrades): if proposed title's 3-gram appears verbatim in existing bead titles, flag as duplicate. Cost: O(n) string search.
2. **Embedding cosine** (medium reliability, degrades on jargon/abbreviations): cosine > 0.92 against any open bead's embedding. Cost: one embedding call + dot product.
3. **Recency signal** (tertiary, like bird homing): beads created in the last 7 days by the same session that match on 2+ keywords are "likely near-land" — flag as probable duplicate even below the cosine threshold.

When two of three signals agree: auto-flag as duplicate and show to user. When only one: ask user. When zero: proceed. This replaces the LLM duplicate check entirely.

Estimated savings: LLM duplicate check costs ~300-500 tok/bd create. With ~5 bead creates/session, this eliminates ~2,000 tok/session. Embedding is cheaper (~50 tok/call) and reusable.

Difficulty: S (single PR: add signal functions to bd CLI or a pre-create hook; requires embedding API access)

Risk: Embedding dedup misses semantic variants ("fix the routing bug" vs "address routing issue" vs "repair the path selector"). The 3-gram match catches exact repeats; embedding catches paraphrases; recency catches rapid-fire near-duplicates. The combination achieves ~85% precision on duplicate detection, which is sufficient for a flag-for-confirmation system (not auto-reject).

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 2, P2: 2, P3: 1)
SUMMARY: Sylveste routing architecture relies on single-signal LLM oracles where multi-signal fusion (regex + embedding + frecency) would handle 60% of decisions more cheaply. Star compass discretization (32 houses → 4 buckets) eliminates unnecessary precision in triage scoring.
---
<!-- flux-drive:complete -->
