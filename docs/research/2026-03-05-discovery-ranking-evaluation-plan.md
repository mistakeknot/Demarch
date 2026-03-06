---
artifact_type: research
bead: iv-wie5i.2
stage: discover
---

# Discovery Ranking Evaluation Plan

**Bead:** iv-wie5i.2
**Date:** 2026-03-05
**Status:** Evaluation framework — ready to execute once discovery data accumulates

## Context

The interject→kernel bridge just shipped (iv-wie5i). Every scan now writes to both interject's local DB and the kernel via `ic discovery submit`. Bead creation is tier-gated: high (>= 0.8) → P2 bead, medium (0.5-0.8) → P4 bead with `pending_triage`, low (< 0.5) → kernel record only.

**Current state:** Both databases are empty (0 discoveries, 0 promotions, 0 feedback signals). The evaluation framework is designed *before* data exists so that measurement is baked in from the first scan, not bolted on after habits form.

## 1. Gold-Set Sampling

### Purpose
A manually-rated reference set to measure precision and recall of the automated scoring.

### Method

1. **Collect 100 discoveries** across the first 3-5 scans (mix of sources: arxiv, github, hackernews, exa).
2. **Human rating** (by project owner): Rate each discovery 1-5 on relevance to Demarch:
   - **5** — Directly applicable, would adopt/build immediately
   - **4** — Strong relevance, worth a brainstorm
   - **3** — Interesting but not actionable this quarter
   - **2** — Tangentially related, low signal
   - **1** — Noise, no relevance
3. **Storage:** `docs/research/gold-set/` directory with one YAML file per batch:
   ```yaml
   # gold-set-batch-001.yaml
   rated_at: 2026-03-10
   rater: mk
   items:
     - id: ij-github-example-1
       title: "..."
       source: github
       auto_score: 0.82
       auto_tier: high
       human_rating: 4
       notes: "Good MCP pattern, worth investigating"
   ```
4. **Refresh cadence:** Re-rate a 20-item sample every 2 weeks to detect profile drift.

### Gold-Set Size Justification

100 items provides ~95% confidence intervals of ±10% on precision/recall estimates. For a pre-1.0 system, this is sufficient to detect gross miscalibration without requiring a massive labeling effort. Scale to 200+ only if initial results show borderline precision.

## 2. Precision and Recall Metrics

### Definitions

Given the tier-gated system, precision and recall are measured at two thresholds:

**High-tier gate (auto-promote to P2 bead):**
- **Precision@high:** Of items scored >= 0.8 (auto-promoted), what fraction did the human rate 4-5?
- **Recall@high:** Of items the human rated 4-5, what fraction scored >= 0.8?

**Medium-tier gate (P4 bead, pending_triage):**
- **Precision@medium:** Of items scored 0.5-0.8 (auto-triaged), what fraction did the human rate 3+?
- **Recall@medium:** Of items the human rated 3+, what fraction scored >= 0.5?

### Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Precision@high | >= 0.7 | 70% of auto-promoted items should be genuinely useful. Higher is better but 100% means thresholds are too conservative. |
| Recall@high | >= 0.5 | Missing half the good items is acceptable if the other half surfaces via medium-tier triage. |
| Precision@medium | >= 0.5 | Medium tier is a triage queue, not auto-action. 50% precision is tolerable. |
| Recall@medium | >= 0.8 | Combined with high, this means 80%+ of relevant items enter the pipeline somewhere. |
| False positive rate (low tier) | <= 0.1 | At most 10% of items scored < 0.5 should have been rated 3+ by human. |

### Computation Script

```python
# scripts/eval-ranking-precision.py
# Input: gold-set YAML files
# Output: precision/recall at each threshold, confusion matrix

import yaml
from pathlib import Path

def evaluate(gold_dir: str = "docs/research/gold-set/"):
    items = []
    for f in Path(gold_dir).glob("gold-set-batch-*.yaml"):
        batch = yaml.safe_load(f.read_text())
        items.extend(batch.get("items", []))

    if not items:
        print("No gold-set data yet. Run scans and rate items first.")
        return

    # Compute metrics at each threshold
    for threshold_name, score_min, score_max, human_min in [
        ("high", 0.8, 1.0, 4),
        ("medium", 0.5, 0.8, 3),
    ]:
        predicted_positive = [i for i in items if score_min <= i["auto_score"] < score_max or (score_max == 1.0 and i["auto_score"] >= score_min)]
        actually_positive = [i for i in items if i["human_rating"] >= human_min]

        tp = len([i for i in predicted_positive if i["human_rating"] >= human_min])
        fp = len(predicted_positive) - tp
        fn = len([i for i in actually_positive if not (score_min <= i["auto_score"] < score_max or (score_max == 1.0 and i["auto_score"] >= score_min))])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        print(f"{threshold_name}: precision={precision:.2f} recall={recall:.2f} (TP={tp} FP={fp} FN={fn})")
```

## 3. Source-Trust Adaptation

### Current Mechanism

`engine.py` already has `update_source_weights_from_feedback()` which adjusts source weights based on promotion→shipped conversion rates. Source weights multiply the base cosine similarity score.

### Evaluation Questions

1. **Source reliability variance:** Do sources differ meaningfully in signal quality? Hypothesis: arxiv and github have higher precision than hackernews (more noise). Measure precision@high per source.

2. **Weight convergence:** After N scans, do source weights stabilize or oscillate? Track weights over time in a log file.

3. **Cold-start problem:** New sources start at weight 1.0. Is this too generous? Too conservative? Compare precision of first 10 discoveries from a new source vs established sources.

### Measurement

Add a source-weight audit to the scan completion flow:

```python
# In scanner.py, after adapt_thresholds():
profile = self.db.get_profile()
source_weights = profile.get("source_weights", {})
logger.info("Source weights after scan: %s", source_weights)
```

Track per-source metrics in gold-set evaluation:

```
Source breakdown:
  arxiv:      precision@high=0.80, recall@high=0.60, weight=1.15
  github:     precision@high=0.75, recall@high=0.55, weight=1.10
  hackernews: precision@high=0.40, recall@high=0.70, weight=0.85
```

### Recommended Trust Rules

| Signal | Weight adjustment | Bounds |
|--------|-------------------|--------|
| Promoted discovery shipped | source_weight += 0.05 * priority_weight | max 2.0 |
| Promoted discovery abandoned | source_weight -= 0.02 | min 0.3 |
| Dismissed at triage | source_weight -= 0.01 | min 0.3 |
| No action after 30 days | No adjustment (staleness is not signal about source quality) | — |

These rules already exist in `engine.py:learn_promotion()` and `learn_dismissal()`. The evaluation should verify the adjustment magnitudes are reasonable (not too aggressive, not too timid).

## 4. Dedup Quality Assessment

### Current Mechanism

- **Interject local:** Exact dedup by `disc_id` (format: `ij-{source}-{source_id[:30]}`). Prevents same source item from being re-scanned.
- **Kernel:** Optional semantic dedup via `--dedup-threshold` (cosine similarity). TOCTOU-vulnerable across concurrent submits but mitigated by `UNIQUE(source, source_id)` constraint.

### Evaluation Questions

1. **Exact dedup coverage:** What fraction of re-scanned items are caught by `disc_id` dedup? Should be ~100% for same-source items.

2. **Cross-source duplicates:** Same paper on arxiv and semantic_scholar, same repo on github and hackernews. These aren't caught by exact dedup. How prevalent are they?

3. **Semantic dedup threshold:** What cosine similarity threshold catches cross-source duplicates without false-merging distinct items?

### Measurement

After 100+ discoveries accumulate:

```sql
-- Find potential cross-source duplicates
-- (requires embedding similarity, run in Python)
SELECT a.id, b.id, a.source, b.source, a.title, b.title
FROM discoveries a, discoveries b
WHERE a.source != b.source
  AND a.id < b.id
  AND cosine_similarity(a.embedding, b.embedding) > 0.85
```

### Recommended Dedup Checks

1. **Always enable `--dedup-threshold=0.9` on kernel submit.** High threshold catches near-exact duplicates without false merges.
2. **Log dedup events.** When `ic discovery submit` returns an existing ID (dedup hit), log it for monitoring.
3. **Cross-source dedup audit:** Monthly script that finds high-similarity pairs across sources. Manual review to calibrate threshold.

## 5. Recommended Thresholds

### Current Defaults

| Threshold | Default | Source |
|-----------|---------|--------|
| High | 0.8 | `engine.py:39` |
| Medium | 0.5 | `engine.py:40` |
| Low | 0.2 | `engine.py:41` |
| Discard | < 0.2 | `engine.py:146` (implicit) |

### Adaptive Mechanism

`adapt_thresholds()` adjusts thresholds based on promotion rate:
- Promotion rate > 30% → lower thresholds by 0.02 (surface more)
- Promotion rate < 10% → raise thresholds by 0.02 (reduce noise)
- Bounds: high ∈ [0.6, 0.95], medium ∈ [0.3, 0.7]

### Evaluation Procedure

1. **Weeks 1-2 (cold start):** Run with defaults. Collect gold-set. Do NOT adjust thresholds yet.
2. **Week 3:** Run `eval-ranking-precision.py` against gold-set. Check precision/recall at current thresholds.
3. **Adjust if needed:**
   - If precision@high < 0.5 → raise high threshold by 0.05 (too much noise auto-promoting)
   - If recall@high+medium combined < 0.6 → lower medium threshold by 0.05 (missing too much)
   - If false positive rate at low tier > 0.15 → raise low threshold by 0.05
4. **Weeks 4+:** Enable `adapt_thresholds()` (currently only runs after each scan). Monitor for oscillation. If thresholds oscillate by > 0.1 between scans, add a damping factor.

### Recommended Starting Thresholds

Keep the current defaults (0.8/0.5/0.2). They're reasonable for a system with no data. The evaluation framework above will tell us when to adjust.

**Key insight:** The tier-gated output pipeline (shipped in iv-wie5i) provides a natural safety net. Even if thresholds are miscalibrated:
- False positives at high tier → create P2 beads that get triaged eventually
- False positives at medium tier → create P4 pending_triage beads that `/interject:triage` handles
- False negatives → worst case, a relevant discovery sits as a kernel record that can be found via `ic discovery search`

The system is **safe to run with defaults** — evaluation calibrates for *efficiency*, not safety.

## 6. Implementation Checklist

- [ ] Run first interject scan: `uv run interject-scan` (populates both DBs)
- [ ] After 3-5 scans (~50-100 discoveries): Create first gold-set batch
- [ ] Run `eval-ranking-precision.py` against gold-set
- [ ] Review source-weight logs for per-source precision
- [ ] Run cross-source dedup audit
- [ ] Adjust thresholds if metrics are outside targets
- [ ] Enable `--dedup-threshold=0.9` on kernel submit (update `_submit_to_kernel` in outputs.py)
- [ ] Schedule bi-weekly gold-set refresh (20-item sample)

## 7. Success Criteria

The evaluation framework is successful when:

1. **Gold-set exists** with >= 100 rated items across >= 3 sources
2. **Precision@high >= 0.7** (auto-promoted items are genuinely useful)
3. **Combined recall >= 0.8** (80%+ of relevant items enter the pipeline)
4. **Source weights are non-uniform** (the system has learned that sources differ)
5. **Dedup catches >= 95%** of re-scanned items (zero cross-source dedup is acceptable initially)
6. **Thresholds are stable** (not oscillating by > 0.1 between scans)
