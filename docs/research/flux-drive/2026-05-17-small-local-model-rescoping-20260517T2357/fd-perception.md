---
title: Perception Review — Small-Local-Model Rescoping
date: 2026-05-17
reviewer: fd-perception-reviewer
bead: Sylveste-s10 (pre-review)
---

# Perception Review — Small-Local-Model Rescoping

## Summary

The brainstorm constructs a MAP of 5 candidate workloads from session memory + recent handoffs, then applies a strict kill rule to all but two. However, the TERRITORY — actual workload distribution in `~/.claude/interstat/metrics.db`, closed-bead corpus, and 1000-commit git history — is never consulted. The author explicitly acknowledges this ("the actual workload distribution is in interstat/metrics.db and bead/git logs") but doesn't execute the lookup. This creates two concrete risks: (a) invisible high-volume workloads that don't appear in session memory are excluded from measurement; (b) recency bias over the past 2 weeks distorts priority, obscuring longer-term patterns that might change the kill-vs-measure verdict. The brainstorm's reasoning is sound *within its source-limited frame*, but the frame itself is the blind spot.

## Findings

### [P1] FINDING: Recency-biased workload sampling (session memory only, not dispatch logs)

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 122–124 (Open questions #2)

**Perceptual lens**: Map-territory confusion + Information-source diversity

**Issue**: The 5 candidates (lens-triage, Explore dispatch, bd classification, commit-msg scoring, flux-review pre-filter) all derive from session memory, handoffs, and 2 visible beads. None of these sources weight by FREQUENCY of occurrence in the workload. For example:
- Candidate B (Explore dispatch) is anchored to Sylveste-9ve, which the author notes stopped firing 2026-04-21 — but without consulting dispatch logs, the author doesn't know if Explore was high-volume before it stopped (would justify cost-saving focus) or low-traffic (would argue for other priorities).
- Candidate E (flux-review pre-filter) is deemed "latency-attractive, recall-risky" (line 96) without measuring actual flux-drive dispatch frequency or latency distribution (P50 / P95 / P99).
- Lens-triage (Candidate A) is marked "kill" because the k8c corpus is "tiny (11 runs)"; but how many lens-finding runs are dispatched per week globally across all agents? If it's 100+/week, the opportunity cost shifts.

**Evidence the author missed**: 
- `~/.claude/interstat/metrics.db` contains `dispatch_outcomes` with `agent_name`, `timestamp`, `finding_count`, `verdict` per agent-document pair. SQL query to reveal: `SELECT agent_name, COUNT(*) as dispatch_count FROM dispatch_outcomes WHERE timestamp >= '2026-04-01' AND agent_name LIKE 'fd-%' GROUP BY agent_name ORDER BY dispatch_count DESC LIMIT 20`. This shows which flux-drive agents (including lens-finding, skill-dispatch, etc.) are actually firing and at what frequency.
- Git commit history since 2026-04-01 shows `feat(skill-router)`, `feat(bead-tooling)`, `feat(.claude)` changes — suggesting recent work on slash-resolution and bead-tooling. A `git log --since=2026-04-01 --format=%B | grep -i "skill\|bead\|duplicate\|classify\|score" | wc -l` would show velocity of effort on exactly these workloads.
- Interspect evidence DB (mentioned in line 92 as ground truth for E) also contains historical dispatch patterns. Query to reveal: dispatch rate of flux-review over the past 90 days, broken by month, to detect trend (growing / declining / flat).

**Recommendation**: Before finalizing the kill rule, run `sqlite3 ~/.claude/interstat/metrics.db "SELECT agent_name, COUNT(*) as n, MAX(timestamp) as latest FROM dispatch_outcomes WHERE timestamp >= '2026-04-01' GROUP BY agent_name ORDER BY n DESC;"` and cross-reference against the 5 candidates. If any candidate maps to an agent in the top-10 dispatch list, escalate to measurement regardless of corpus-size / verticality concerns. Conversely, if Explore (candidate B) shows 0 dispatches in April, that could justify moving it further down or merging its measurement into 9ve diagnostic work.

---

### [P2] FINDING: False certainty on heuristic-vs-specialist tradeoff at 89.6% baseline

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 12, 30–34, 98–107

**Perceptual lens**: Signal-noise separation + Temporal discounting + Paradigm-shift exposure

**Issue**: The brainstorm opens with "The microrouter close showed heuristics are very strong" (line 30). The 89.6% measurement on `core-builtin-general` is treated as a fixed, generalizable signal. But:

1. **One measurement on one workload at one time is not a universal truth.** Sylveste-zge measured routing correctness on the `core-builtin-general` workload (routing-drift CI gate). But routing-drift measures a narrow decision boundary (does this agent belong in this category?), not *coverage across all routing scenarios*. The 89.6% is a LEADING INDICATOR of heuristic fitness for *that* workload; it doesn't predict heuristic performance on lens-triage, skill discovery, or bead-classification.

2. **The brainstorm doesn't distinguish between "heuristic beats SLM on routing" and "heuristic beats SLM on all triage tasks."** These are different claims. Line 96 on E (flux-review pre-filter) admits the measurement *didn't happen yet* — "worth measuring but not the strongest candidate." But the kill rule assumes the measurement has already proven heuristics win, when it hasn't.

3. **Paradigm-shift exposure:** The 5 candidates all assume the choice space is {heuristic, sub-10B specialist, cloud Haiku, prompt-eng}. Missing from this choice space:
   - **Multi-stage cascades**: heuristic → BM25 sketch → embedding lookup → small LLM → cloud Opus, each stage with an abstain clause. This is cheaper than full-SLM and could outperform heuristic on hard cases without the latency cost of always calling cloud.
   - **DSPy-style prompt programs**: Deterministic structure (not learned weights) applied at prompt time to recover some of the gains of fine-tuning without the inference cost.
   - **Retrieval-augmented heuristics**: Use BM25 / semantic search over the bead corpus or closed-dupe set to *augment* rule coverage, not replace it with SLM.

**Evidence the author missed**:
- The microrouter close doc itself (mentioned in handoff, not read in this brainstorm) likely contains caveats on generalizability. Check `docs/research/microrouter-phase1/baseline-2026-05-17-zge-trigger-check.txt` for which workloads were included in the 89.6% measurement.
- Git history shows `feat(skill-router)` (commit 1c1026a0) landed a "deterministic slash-command prefix router" in Phase 2. If this outperformed an SLM baseline, that's evidence that the paradigm-choice space is wider than the brainstorm assumes.

**Recommendation**: 
1. Explicitly list the *scope* of the 89.6% signal: "89.6% correctness on routing-drift (agent-role consistency check) does not imply 89.6% correctness on [lens-triage / bead-duplicate-detection / flux-review-dispatch]. These require independent measurement."
2. For the two promoted candidates (C′ and E), explicitly design Phase-1 measurement to test whether heuristic + prompt-engineering can match or beat the learned approach, rather than comparing SLM to cloud Opus only.
3. Sketch one cascade alternative (e.g., "BM25 keyword-match → embedding cosine-sim → small 4B classifier" for duplicate detection) and evaluate against the pure-embedding candidate (C′).

---

### [P3] FINDING: Survivorship bias — workloads that survived into session memory are the 5 visible ones

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 36–108

**Perceptual lens**: Survivorship bias + Change blindness

**Issue**: The 5 candidates exist because they were:
- Mentioned in recent handoffs (Sylveste-9ve, k8c.1, k8c.2, Sylveste-zge)
- Open beads at session start (visible in `bd list`)
- Or recently discussed in code review / commit messages

Workloads that don't survive into session memory are invisible:
- A closed bead that was repeatedly re-opened and re-closed (suggests a chronic decision problem that might benefit from SLM automation)
- A task that's run *informally* without creating beads (e.g., "I grep the codebase by hand instead of using Explore")
- A new workload that emerged in the past 2 weeks but hasn't yet been named or tracked in an open bead

**Evidence the author missed**:
- `~/.claude/projects/-Users-sma-projects-Sylveste/memory/` contains auto-memory from prior sessions. The MEMORY.md file lists recurring patterns: `feedback_read_papers_first`, `feedback_measure_inputs_not_outputs`, `feedback_read_tensor_shapes_before_papers`. These are workloads (review-task calibration, measurement design, model checkpoint inspection) that recur across sessions. Do any of these have high enough dispatch volume to justify a local SLM?
- `bd list --status closed` over the past 90 days, filtered by who created the bead (if creator is the user), shows what decisions the user actually made repeatedly. A pattern like "created 5 beads named *-calibrat*" would reveal a calibration workload the brainstorm doesn't mention.
- Git log author-filtered (`git log --author='mistakeknot' --since='2026-04-01' --format=%B`) shows what the user actually *committed* work on. If 20% of commits are model-porting diffs and 5% are documentation, that's a signal about relative effort allocation.

**Recommendation**: Before Phase-1 measurement, run a quick survivorship-bias audit: (1) scan `~/.claude/projects/.../memory/` for recurring decision patterns not in the 5 candidates; (2) run `bd list --status closed --since 2026-03-01 | grep -iE 'calibrat|review|triage|classify'` to find closed beads whose names suggest automation potential; (3) extract top-5 commit message prefixes by frequency (`git log --format=%B | grep -oP '^[a-z]+\(' | sort | uniq -c | sort -rn`) to correlate workload surface area. Any emerging workload (not in the top 5 but showing growth trend) should be escalated to "defer until measurement" instead of "kill."

---

### [P2] FINDING: Duplicate-detection (C′) escapes the "small-local-model" frame via embedding redirect

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 71–72, 105, 113

**Perceptual lens**: Reification + Paradigm-shift exposure

**Issue**: Candidate C′ is promoted because it's framed as an "embedding model, not generative" (line 72). This sidesteps the original question ("is there a narrow task class where a sub-10B *generative* local specialist would win?") by redefining the solution space.

Two concerns:
1. **Is this honest?** If the user's intent was specifically to explore sub-10B LMs for autonomous decision-making, embedding models are a different category (no inference per-se, just retrieval + similarity). The brainstorm risks promoting a solution that doesn't actually answer the opening question, which could waste Phase-1 measurement time on an escape hatch.
2. **Adjacency to existing infrastructure.** Sylveste already has Interspect (evidence-tracking, finding-storage) and likely has pre-computed embeddings or access to embedding APIs. Is C′ (new embedding model) a duplicate of existing capability? Line 71 claims "ground truth is clean" but doesn't cite whether bead embeddings are already computed and what vector DB (if any) is live.

**Evidence the author missed**:
- Check if Interspect or intertrust already index closed beads by embedding. If yes, Phase-1 for C′ might be as simple as querying the existing index with a new threshold, not training a new model.
- Review `docs/AGENTS.md` (project instructions) to confirm whether embedding-based duplicate detection is in scope for "small-local-model" framing, or whether the user's intent was generative SLM only.
- If an embedding model was already selected (BGE-small / all-MiniLM-L6 mentioned in line 113), check `huggingface` download history: has the user already ported this model to local quantized form? If yes, Phase-1 is trivial (re-rank existing closed-dupe set). If no, there's hidden work.

**Recommendation**: Reframe C′ explicitly: "C′ is a retrieval-based solution, not a generative SLM, and should be measured separately from the 'generative sub-10B specialist' question. If the user wants specifically generative models, C′ doesn't answer that question and should be deferred or moved to a companion bead on retrieval-augmented tasks."

---

### [P2] FINDING: Flux-review pre-filter (E) cost-benefit is inverted; latency savings are the unstated crux

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 87–96, 115

**Perceptual lens**: Signal-noise separation + Temporal discounting + Change blindness

**Issue**: Candidate E is promoted to "measure" status on latency grounds (line 94), with cost explicitly dismissed as "negligible" (~$5/month). But:

1. **The latency claim is unvalidated.** Line 115 recommends "train a tiny classifier (could even be logistic regression on TF-IDF + agent embedding)" without knowing if that classifier is sub-200ms p50 locally. If TF-IDF vectorization + cosine-sim on 10+ agents takes >100ms, the latency win vanishes.

2. **Recall risk is understated.** Line 95 sets a "recall floor must be ~99%." This is a 1% false-negative rate on finding discovery. If flux-drive runs ~10×/week and each run dispatches ~8 agents, that's ~80 agent-document pairs/week. A 1% false-negative rate means ~1 real finding per 100 weeks is silently filtered. Over a year, that's ~0.5 findings missed — seemingly acceptable. But what if flux-drive usage grows 5× (as suggested in the handoff — V4 spike is driving new model-validation work)? Then 5 findings/year are missed, which changes the risk calculus.

3. **Change blindness on dispatch mix.** The Interspect evidence DB's dispatch outcomes reflect the *current* agent registry. But the handoff mentions new plugins (interhelm, intertrace, intertest) recently landed. If the flux-drive agent roster is expanding, the overlap between candidate pre-filter logic and new agents is unknown. Pre-filter trained on today's agents might fail on next month's agents.

**Evidence the author missed**:
- Measure actual latency of the proposed classifier candidate. If it's locally sub-100ms, latency is credible. If >200ms, it doesn't solve the latency problem and becomes a cost-reduction argument (which is already dismissed as "negligible").
- Predict 90-day flux-drive dispatch growth using interstat: `SELECT DATE_TRUNC('week', timestamp) as week, COUNT(*) as dispatches FROM dispatch_outcomes WHERE agent_name LIKE 'fd-%' GROUP BY week ORDER BY week;` If trend is flat, 1% false-negative is acceptable. If growing, escalate recall floor to 99.5% or higher.
- Check the interflux agent registry (`docs/agents/**/*.md` mentioned in handoff line 38) to count current flux-drive agents and predict next quarter's roster growth. If >30% agents are expected to change, pre-filter model-fit risk rises.

**Recommendation**: Reframe E measurement design: (1) benchmark latency of the proposed classifier (TF-IDF + LR) locally before committing to measurement; (2) compute the false-negative cost curve over 1 year assuming 0%, 5%, 10%, 50% dispatch growth; (3) if false-negative cost is >$50/year at any growth scenario, escalate recall floor from 99% to 99.5% and re-estimate measurement load.

---

### [P1] FINDING: Missing cross-reference to intertrust + Interspect overlap on E (dispatch triage)

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 87–96

**Perceptual lens**: Map of competitors + Paradigm-shift exposure

**Issue**: Candidate E (flux-review agent pre-filter) is framed as a standalone cost/latency optimization. But the handoff context (line 39) mentions intertrust (trust scores) is live. Sylveste's perceptual architecture includes:
- **intertrust**: assigns trust scores to agents based on prior performance
- **Interspect**: logs dispatch outcomes and finding quality
- **Proposed E**: train a classifier on dispatch outcomes to predict "substantive findings"

Are E and intertrust solving the same problem? For example, if intertrust already scores agents on "likelihood of finding findings" (or equivalently, "likelihood of finding zero findings"), then E might be reinventing intertrust for flux-drive specifically. Or, if intertrust uses *trust scores* (a single scalar per agent) and E uses *content-based prediction* (agent description + document excerpt), they're complementary. But the brainstorm never checks.

**Evidence the author missed**:
- Read the intertrust docs or recent commits to understand what intertrust currently predicts. If it includes "dispatch-success probability," E is a duplicate. If not, E is complementary.
- Check whether Interspect evidence DB is *already used* by intertrust for score updates. If yes, Interspect is the shared ground truth. If no, E might create a second source of ground truth (dispatch outcomes), creating maintenance burden.
- Query interlock or interflux to see if dispatch routing *already uses* intertrust scores. If yes, E might be second-guessing intertrust. If no, E is a new use case.

**Recommendation**: Before Phase-1 measurement for E, add a short discovery task: "How does E differ from intertrust? Are they compatible, competing, or complementary?" Diagram the existing decision flow (intertrust score → dispatch decision → Interspect outcome log) and show where E injects a new decision point. If E *replaces* a stage of the flow, flag it as a redesign, not a pure optimization. If E *augments* the flow, quantify the added latency.

---

### [P3] FINDING: Open questions #1 and #3 are legit sensemaking blind spots, not rhetorical questions

**Location**: `docs/brainstorms/2026-05-17-small-local-model-rescoping.md`, lines 121, 123

**Perceptual lens**: Narrative fallacy + Reification

**Issue**: The brainstorm lists three "open questions for review" but treats them as rhetorical. 
- Question #1 ("Is the kill rule too strict?") is answered preemptively: "Counterargument: the microrouter cluster was killed precisely because we didn't apply a strict-enough threshold up front." This deflects the question instead of investigating it.
- Question #3 ("Is the embedding-not-generative escape hatch honest?") is tagged with a disclaimer but allowed to stand: "If the user's intent was specifically generative SLM, this candidate doesn't count." But then C′ is still promoted to measurement.

These aren't rhetorical questions — they're real tensions in the argument that the review process should resolve, not note and move on.

**Recommendation**: Elevate open questions #1 and #3 to explicit reviewer tasks. For #1, the reviewer should check: does the microrouter kill-rule data actually support a strict threshold, or is it a sunk-cost rationalization? For #3, the reviewer should confirm with the user: are C′ retrieval-based candidates in scope for the "small-local-model" bead, or should they be deferred to a separate bead on retrieval augmentation?

---

## Workload candidates the brainstorm may have missed

For each, cite the evidence basis (NOT speculation):

1. **Bead-corpus analysis / categorization workload**: Git history shows `feat(bead-tooling)` (line 59d9ce9a) and `bd-create-checked wrapper with TF-IDF dup detection` (line 59d9ce9a). This suggests bead-metadata automation is a known pain point. Frequency basis: check `bd list --status closed --since 2026-04-01 --format='%(title)' | grep -iE 'category|class|type|tier' | wc -l` to count how many recent closed beads explicitly mention metadata-assignment work.

2. **Agent-routing / skill-dispatch triage**: Git shows `feat(skill-router)` (line 1c1026a0) landed a "deterministic slash-command prefix router" recently. If this outperformed an SLM baseline, there may be a hidden lesson about heuristic-vs-learned on *dispatch* specifically. Frequency basis: query interstat for `skill_dispatch` or `router_decision` agent dispatches over past 30 days.

3. **Model checkpoint validation / parity verification**: The user's session history (handoff line 32–38) shows deep work on DeepSeek V4 tensor-map, FP4/FP8 dequantization, and parity checks. This workload (verify that a ported model matches upstream) recurs across model-porting projects. Frequency basis: check `git log --format=%B | grep -iE 'parity|checkpoint|tensor-map|dequant' | wc -l` for the past 2 months to estimate recurrence.

4. **Dispatch outcome labeling / quality scoring**: Interspect evidence DB requires human judgment to label dispatch findings as "substantive" vs "false positive." If this labeling is done manually per session, it's a recurring triage workload. Frequency basis: check Interspect schema for `verified_by` or `human_label` fields; query recent updates to estimate labeling throughput.

5. **Paradigm-detection in long-running experiments**: The user runs multi-week spikes (V4 spike is Day-3 of a multi-day arc). Detecting *when assumptions change mid-spike* (e.g., "the bottleneck shifted from memory to compute") requires reading outputs, logs, and prior assumptions. This is a perception task (not automation). Frequency basis: check how many times a spike bead was reopened or an assumption was amended mid-spike.

---

## Sources the brainstorm should consult before promotion

Ranked by impact:

1. **`~/.claude/interstat/metrics.db` (dispatch frequency database)**
   - Reveals true workload frequency distribution (not session-memory sample)
   - Already cited in brainstorm (line 122) but not consulted
   - Query: dispatch counts per agent per week for past 8 weeks

2. **Closed-bead corpus metadata (`~/.beads/issues.jsonl` + Dolt backup)**
   - Shows which workloads the user has repeatedly created beads for
   - Reveals survivorship-bias blind spots
   - Query: bead creation frequency by title pattern / P-tier / type

3. **Git log analysis (past 90 days, author-filtered)**
   - Shows actual work distribution (not hand-curated candidate list)
   - Reveals effort allocation and skill/tool velocity
   - Query: `git log --author='mistakeknot' --format=%B --since='2026-02-17'` grouped by keyword (model, bead, skill, routing, etc.)

4. **`~/.claude/projects/.../memory/` (auto-memory from prior sessions)**
   - Documents recurring decision patterns and lessons learned
   - Captures what recurs across sessions (survivorship bias blind spot)
   - Scan for patterns like "feedback_calibrate", "feedback_measure_*", "learned_lesson_*"

5. **Interspect evidence DB (dispatch outcomes + finding quality)**
   - Ground truth for candidate E (flux-review pre-filter)
   - Also reveals dispatch patterns by agent and outcome type
   - Query: `SELECT agent_name, AVG(finding_count) as avg_findings, COUNT(*) as dispatch_count FROM evidence_table WHERE timestamp >= '2026-03-17' GROUP BY agent_name ORDER BY dispatch_count DESC`

6. **Recent git commits in model-porting / validation paths** (e.g., interfer, flash-moe)
   - Reveals if tensor-validation / parity-checking workload has grown
   - May justify a new candidate (model-validation triage)
   - Check: `git log --since='2026-04-01' -- interfer/ flash-moe/ | grep -iE 'checkpoint|parity|validation' | wc -l`

---

## Final Notes for Reviewer

- **Do not block promotion based on these findings.** The brainstorm's reasoning is sound within its source-limited frame. These findings are about expanding the frame, not discrediting it.
- **The kill rule *might* be appropriate.** But it should be applied *after* consulting the territory, not before. The current kill rule operates on a sample of the population (session-memory candidates), not the full population (all Sylveste workloads).
- **Candidates C′ (embedding) and E (pre-filter) are reasonable Phase-1 targets** given current information. But Phase-1 measurement should explicitly include a heuristic / prompt-engineering arm, and should measure against ground truth from interstat, not just the brainstorm's hypothesis.
- **Candidate B (Explore dispatch) is marked "defer"** but the diagnosis precondition (Sylveste-9ve close) is outstanding (see handoff, fallback-work section). This is correct sequencing; don't unblock B until 9ve is diagnosed.
- **C′ reframing (embedding ≠ generative SLM) is a legitimate tension.** Reviewer should confirm with user whether retrieval-based candidates are in scope, or should go to a companion "retrieval-augmented triage" bead.
