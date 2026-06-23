---
title: Small-local-model (sub-10B) rescoping after microrouter close
date: 2026-05-17
bead: Sylveste-s10
status: brainstorm (pre-review)
---

# Small-local-model rescoping after microrouter close

## Frame

The microrouter/SLM/routing cluster wound down 2026-05-17 with zero open beads. The 2026-05-09 .19 LoRA epic was cancelled; the 2026-05-17 Sylveste-zge measurement closed MOOT after the post-0zy `core-builtin-general` agreement hit 89.6% — above the 85% trigger that would have justified a successor learned router.

The 2026-05-17 handoff is explicit: any future learned-routing question needs a fresh scoping bead written against then-current workload. This doc is the scoping artifact for Sylveste-s10.

**Question.** Is there a narrow task class in the Sylveste workload where a sub-10B local specialist (fine-tuned or zero-shot) would beat the current heuristic + cloud-tier routing by enough margin to justify the inference path?

**Hardware context.** M5 Max 128GB. Concurrent with large-MoE work (flash-moe Qwen 35B–122B). A "small local model" here means **sub-10B params**, ideally sub-4B so it can run alongside large-MoE without VRAM contention. Latency budget: sub-200ms p50 for routing/triage decisions; sub-2s p50 for lens-style judgements.

## What "small local model" rules out

- **Reviving the .19 LoRA epic.** Killed deliberately; the workload (general routing across all agent roles) was wrong for a specialist.
- **General-purpose chat / code generation.** Large-MoE track owns this (Qwen 35B/122B, DeepSeek V4 port).
- **Replacing cloud Opus/Sonnet for hard tasks.** Quality gap too large at sub-10B.

## What it might unlock

A sub-10B specialist competes against three baselines, not one:

1. **Heuristic** (regex, lookup tables, deterministic rules). The microrouter close showed heuristics are very strong when the task is narrow and the rules are auditable.
2. **Cloud Haiku** ($0.80/M input, $4/M output, ~300ms latency, no fine-tuning on this corpus).
3. **Prompt engineering on existing cloud tier.** Often dominates fine-tuning if the corpus is small or the task is well-described in natural language.

A specialist wins only when the task has **enough structured ground-truth in the corpus** AND **the baselines are visibly weak** AND **latency/cost matters enough**.

## Candidate workloads (5)

### A. Lens-finding triage / k8c quality lens

**Workload.** k8c shipped flux-local at dogfood-quality using Qwen 35B. CALIBRATION.md shows 8/11 lens runs usable, quality lens specifically loops/self-affirms in 2/11 runs. Followup k8c.1 proposes temperature/prompt fixes; k8c.2 proposes Opus A/B for gate-quality.

**Specialist hypothesis.** A 3B–7B fine-tuned on the lens corpus (~11 calibrated runs, 8 substantive findings, 4 declined-cosmetic) could give faster, more deterministic findings than Qwen 35B while avoiding Opus cost.

**Reality check.**
- Corpus is **tiny** (11 runs). Fine-tuning likely overfits.
- Quality issue is *looping* — that's a decoding-discipline problem, not a model-capacity problem. Smaller models loop *more*, not less.
- Cost angle: flux-local runs are infrequent. Even 100% Opus replacement saves ~$10/month at current dispatch rate.
- **Verdict: likely no.** Heuristic + prompt fix (k8c.1) is the right path. Re-evaluate only if dispatch rate grows 10×.

### B. Explore-subagent dispatch resurrection

**Workload.** Sylveste-9ve: Explore subagent dispatches in `~/.claude/interstat/metrics.db` stopped 2026-04-21 (n=132 in April, now zero). Cause unknown — could be workflow shift (direct grep/Read replaced Explore) or instrumentation regression.

**Specialist hypothesis.** If the cause is *cost* (Explore is a Sonnet/Opus dispatch with non-trivial latency), a sub-10B local "should-I-Explore?" classifier could make Explore cheap enough to fire again.

**Reality check.**
- We don't yet know whether the cause is cost — it might be workflow drift or instrumentation. **Diagnosis precedes design.** Sylveste-9ve must close first.
- Even if cost is the cause, the decision is binary (Explore vs direct read). A regex on prompt keywords might suffice.
- **Verdict: dependent on Sylveste-9ve. Defer.**

### C. bd bead title/description classification

**Workload.** Every `bd create` involves a P-tier (P0–P4), a type (bug/feature/task/epic/chore/decision), and an implicit duplicate-check. Currently P-tier is human-judged on each create; type defaults to `task`; duplicate-check is `bd search "<kw>"` keyword match (used inconsistently).

**Specialist hypothesis.** A sub-4B fine-tuned on the closed-bead corpus (1000s of beads with hand-set P-tier and type) classifies a new bead's P-tier and type from title+description, and flags likely duplicates via embedding similarity. Latency < 200ms locally.

**Reality check.**
- **Corpus exists and is large.** All closed beads in Dolt + JSONL backup.
- **Ground truth is noisy.** P-tier is human-set and inconsistent (P3 vs P4 is often a coin flip; P0 vs P1 too).
- **Specialist value: marginal.** A heuristic ("contains 'security'/'data loss' → P0; contains 'cleanup'/'cosmetic' → P4") would cover the strong-signal cases. The hard cases are hard *because* they require judgement no model trained on noisy labels will improve on.
- Duplicate detection via embedding similarity is the **strongest candidate within this bucket** — embeddings can be 100M params, ground truth is clean (which beads were closed as duplicates), and the failure mode is annoying-but-fixable.
- **Verdict: weak for P-tier/type; potentially strong for duplicate detection (embedding model, not generative).**

### D. Commit-message style/quality scoring

**Workload.** Pre-commit hook gate. Score each commit message against project conventions (Conventional Commits prefix, subject length, body present for non-trivial changes, references to beads when applicable).

**Specialist hypothesis.** A sub-4B classifier scores conformance and suggests fixes; latency must be sub-500ms to not annoy.

**Reality check.**
- **A regex covers >90% of this.** Conventional Commits prefix is a regex. Subject length is a count. Bead references are a regex.
- **The hard cases are content-semantic** ("does this commit message actually describe the change?") which a sub-4B cannot judge without reading the diff, which blows the latency budget.
- **Verdict: no. Regex pre-commit hook is the right tool.**

### E. Flux-review agent triage pre-filter

**Workload.** `/flux-drive` matches agents from a registry against a target document via keyword triage. The current triage is permissive — many agents that match get dispatched and return "no findings" (false-positive dispatches). Each dispatch is a cloud LLM call (~$0.01–$0.10).

**Specialist hypothesis.** A sub-4B classifier reads (agent description, document excerpt) and predicts "will return substantive findings (Y/N)". Pre-filter cuts dispatch count by 30–50% while preserving recall of substantive findings.

**Reality check.**
- **Ground truth exists.** Interspect evidence DB has dispatch outcomes (`finding_count`, `verdict` per dispatch).
- **Dispatch rate matters.** If flux-drive runs ~10×/week with ~8 agents each = 80 dispatches/week. 30% reduction = 24 dispatches/week saved × $0.05 avg = ~$5/month. **Cost savings are negligible.**
- **Latency angle stronger.** Each dispatch is 30–120s wall time; cutting 30% would visibly speed up flux-drive runs.
- **Risk: false negatives are expensive.** Pre-filter that hides a real finding is worse than redundant dispatches. Recall floor must be ~99%.
- **Verdict: latency-attractive, recall-risky. Worth measuring but not the strongest candidate.**

## Ranking

| Candidate | Workload exists? | Ground truth clean? | Specialist beats heuristic? | Specialist beats prompt-eng? | Net |
|-----------|------------------|---------------------|------------------------------|-------------------------------|-----|
| A. Lens triage | yes (small) | partial | no (corpus too small) | no | **kill** |
| B. Explore dispatch | maybe | unknown | unknown | unknown | **defer (depends on 9ve)** |
| C. bd P-tier/type | yes | noisy | weak | weak | **kill** |
| C′. bd dup detection (embedding) | yes | clean | yes | yes | **PROMOTE** |
| D. Commit-msg scoring | yes | regex-covered | no | n/a | **kill** |
| E. Flux-review pre-filter | yes | clean | maybe | maybe (latency-driven) | **measure** |

## Recommendation

**Two candidates merit Phase-1 measurement beads. The rest close MOOT under the kill rule.**

1. **C′. bd duplicate-detection embedding model.** Smallest, cleanest win. ~100M-param sentence-embedding model (BGE-small / all-MiniLM-L6) over closed-bead corpus; cosine-similarity threshold for "likely duplicate." This is *not* generative inference — it's a retrieval problem. The microrouter close doesn't apply. Phase-1 measurement: precision/recall against the existing closed-as-duplicate set.

2. **E. Flux-review agent triage pre-filter.** Latency win, not cost win. Phase-1 measurement: train a tiny classifier (could even be logistic regression on TF-IDF + agent embedding) on Interspect dispatch outcomes; measure recall at the threshold where 30% of dispatches are filtered. Kill if recall < 95% at that threshold.

3. **B. Sylveste-9ve closes first.** If Explore dormancy is a cost problem, escalate B to a measurement bead then. Otherwise it stays dormant.

## Open questions for review

1. **Is the kill rule too strict?** ">50% probability of >20% improvement" might rule out worthwhile-but-uncertain bets. Counterargument: the microrouter cluster was killed precisely because we didn't apply a strict-enough threshold up front.
2. **Am I missing workload candidates?** This list was generated from session memory + the handoff. The actual workload distribution is in interstat/metrics.db and the bead/git logs.
3. **Is the embedding-not-generative escape hatch (C′) honest?** It sidesteps the "small-local-model" framing by saying "actually we want retrieval." If the user's intent was specifically generative SLM, this candidate doesn't count.
4. **Phase-1 measurement design.** For C′ specifically, what's the right test set? Random sample of 50 closed-as-duplicate pairs + 50 unrelated pairs is small; closed-as-dup pairs themselves may be undersampled (many duplicates may have been silently merged without the "duplicate" tag).
