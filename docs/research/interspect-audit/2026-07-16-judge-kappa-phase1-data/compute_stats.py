#!/usr/bin/env python3
"""
Compute intra-judge kappa (test-retest) statistics for the Sylveste-06i.1
LLM-judge reliability audit. Pure-Python (no numpy/scipy dependency).

Inputs: round1.jsonl, round2.jsonl, round3.jsonl — each 30 lines of
  {"item_number": int, "severity": "CRITICAL|HIGH|MEDIUM|LOW", "verdict": "CONFIRM|REJECT"}

Outputs: prints Fleiss' kappa (severity, 4-category), Cohen's kappa pairwise
  (severity), percent exact agreement, verdict agreement rate, plus
  bootstrap 95% CIs, and writes a raw combined JSONL audit trail.
"""
import json
import random
import statistics
import sys
from collections import Counter, defaultdict

LANE_DIR = "/Users/sma/.claude/jobs/7b16ec73/tmp/lane-c"
CATEGORIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
N_ITEMS = 30
N_ROUNDS = 3


def load_round(path):
    rows = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rows[d["item_number"]] = d
    return rows


def fleiss_kappa(category_counts_per_item, categories):
    """category_counts_per_item: list of dicts {category: count} per item, n raters per item constant."""
    n_items = len(category_counts_per_item)
    n_raters = sum(category_counts_per_item[0].values())
    # P_i for each item: agreement proportion among raters on that item
    P_i = []
    cat_totals = {c: 0 for c in categories}
    for counts in category_counts_per_item:
        n = sum(counts.values())
        s = sum(v * (v - 1) for v in counts.values())
        P_i.append(s / (n * (n - 1))) if n > 1 else P_i.append(1.0)
        for c in categories:
            cat_totals[c] += counts.get(c, 0)
    P_bar = sum(P_i) / n_items
    total = n_items * n_raters
    p_j = {c: cat_totals[c] / total for c in categories}
    P_e = sum(p * p for p in p_j.values())
    if P_e == 1.0:
        return 1.0, P_bar, P_e  # degenerate: no variance
    kappa = (P_bar - P_e) / (1 - P_e)
    return kappa, P_bar, P_e


def cohens_kappa(pairs, categories):
    """pairs: list of (rating_a, rating_b) tuples."""
    n = len(pairs)
    confusion = defaultdict(int)
    for a, b in pairs:
        confusion[(a, b)] += 1
    po = sum(confusion[(c, c)] for c in categories) / n
    row_totals = {c: sum(confusion[(c, b)] for b in categories) for c in categories}
    col_totals = {c: sum(confusion[(a, c)] for a in categories) for c in categories}
    pe = sum((row_totals[c] / n) * (col_totals[c] / n) for c in categories)
    if pe == 1.0:
        return 1.0, po, pe
    kappa = (po - pe) / (1 - pe)
    return kappa, po, pe


def bootstrap_ci(pairs_list_of_lists, stat_fn, categories, n_boot=2000, seed=42):
    """Bootstrap over items (resample items with replacement), recompute stat each time.
    pairs_list_of_lists: list of items, each item is a list of (a,b) rating pairs (could be
    multiple pairwise comparisons per item, e.g. r1-r2, r1-r3, r2-r3)."""
    rng = random.Random(seed)
    n = len(pairs_list_of_lists)
    boots = []
    for _ in range(n_boot):
        sample = [pairs_list_of_lists[rng.randrange(n)] for _ in range(n)]
        flat_pairs = [p for item_pairs in sample for p in item_pairs]
        if not flat_pairs:
            continue
        k, _, _ = stat_fn(flat_pairs, categories)
        boots.append(k)
    boots.sort()
    lo = boots[int(0.025 * len(boots))]
    hi = boots[int(0.975 * len(boots))]
    return lo, hi, statistics.mean(boots)


def main():
    rounds = []
    for i in range(1, N_ROUNDS + 1):
        path = f"{LANE_DIR}/round{i}.jsonl"
        rounds.append(load_round(path))
        print(f"Loaded round {i}: {len(rounds[-1])} items", file=sys.stderr)

    # sanity check: all items present in all rounds
    for i, r in enumerate(rounds, 1):
        missing = set(range(1, N_ITEMS + 1)) - set(r.keys())
        if missing:
            print(f"WARNING round {i} missing items: {missing}", file=sys.stderr)

    common_items = set(range(1, N_ITEMS + 1))
    for r in rounds:
        common_items &= set(r.keys())
    common_items = sorted(common_items)
    print(f"Common items across all rounds: {len(common_items)}", file=sys.stderr)

    # ---- Severity: Fleiss' kappa across 3 rounds (raters = rounds, per item) ----
    category_counts_per_item = []
    for item in common_items:
        counts = Counter()
        for r in rounds:
            counts[r[item]["severity"]] += 1
        category_counts_per_item.append(dict(counts))

    fk, P_bar, P_e = fleiss_kappa(category_counts_per_item, CATEGORIES)

    # ---- Severity: pairwise Cohen's kappa (r1-r2, r1-r3, r2-r3) ----
    pairwise_results = {}
    item_pair_lists = defaultdict(list)  # item -> list of (a,b) tuples across the 3 pairings
    round_pairs = [(0, 1), (0, 2), (1, 2)]
    all_flat_pairs_by_pairing = {}
    for (ri, rj) in round_pairs:
        pairs = [(rounds[ri][item]["severity"], rounds[rj][item]["severity"]) for item in common_items]
        k, po, pe = cohens_kappa(pairs, CATEGORIES)
        pairwise_results[f"round{ri+1}_vs_round{rj+1}"] = {"kappa": k, "percent_agreement": po, "pe": pe}
        all_flat_pairs_by_pairing[(ri, rj)] = pairs
        for idx, item in enumerate(common_items):
            item_pair_lists[item].append(pairs[idx])

    mean_pairwise_kappa = statistics.mean(v["kappa"] for v in pairwise_results.values())
    mean_pairwise_agreement = statistics.mean(v["percent_agreement"] for v in pairwise_results.values())

    # bootstrap CI on mean pairwise cohen's kappa (item-level resampling)
    items_as_pair_lists = [item_pair_lists[item] for item in common_items]
    boot_lo, boot_hi, boot_mean = bootstrap_ci(items_as_pair_lists, cohens_kappa, CATEGORIES)

    # bootstrap CI on Fleiss' kappa (item-level resampling, recompute per-item counts)
    def fleiss_wrapper_over_items(item_indices, categories):
        counts_subset = [category_counts_per_item[i] for i in item_indices]
        k, _, _ = fleiss_kappa(counts_subset, categories)
        return k

    rng = random.Random(7)
    n = len(common_items)
    fleiss_boots = []
    for _ in range(2000):
        idxs = [rng.randrange(n) for _ in range(n)]
        subset = [category_counts_per_item[i] for i in idxs]
        k, _, _ = fleiss_kappa(subset, CATEGORIES)
        fleiss_boots.append(k)
    fleiss_boots.sort()
    fleiss_lo = fleiss_boots[int(0.025 * len(fleiss_boots))]
    fleiss_hi = fleiss_boots[int(0.975 * len(fleiss_boots))]

    # ---- exact match rate (all 3 rounds agree) ----
    exact_match_3 = sum(
        1 for item in common_items
        if len({rounds[r][item]["severity"] for r in range(3)}) == 1
    )
    exact_match_rate = exact_match_3 / len(common_items)

    # ---- verdict (CONFIRM/REJECT) agreement ----
    verdict_pairs_flat = []
    verdict_exact_3 = 0
    for item in common_items:
        verdicts = [rounds[r][item]["verdict"] for r in range(3)]
        if len(set(verdicts)) == 1:
            verdict_exact_3 += 1
        for (ri, rj) in round_pairs:
            verdict_pairs_flat.append((rounds[ri][item]["verdict"], rounds[rj][item]["verdict"]))
    verdict_agree_rate = sum(1 for a, b in verdict_pairs_flat if a == b) / len(verdict_pairs_flat)
    verdict_exact_3_rate = verdict_exact_3 / len(common_items)

    verdict_kappa, verdict_po, verdict_pe = cohens_kappa(verdict_pairs_flat, ["CONFIRM", "REJECT"])

    # ---- distribution of severities per round (sanity / drift check) ----
    round_dists = []
    for r in rounds:
        c = Counter(r[item]["severity"] for item in common_items)
        round_dists.append(dict(c))

    results = {
        "n_items": len(common_items),
        "n_rounds": N_ROUNDS,
        "severity": {
            "fleiss_kappa": fk,
            "fleiss_kappa_bootstrap_ci95": [fleiss_lo, fleiss_hi],
            "P_bar_observed_agreement": P_bar,
            "P_e_expected_agreement": P_e,
            "pairwise_cohens_kappa": pairwise_results,
            "mean_pairwise_cohens_kappa": mean_pairwise_kappa,
            "mean_pairwise_cohens_kappa_bootstrap_ci95": [boot_lo, boot_hi],
            "mean_pairwise_percent_agreement": mean_pairwise_agreement,
            "exact_match_rate_all_3_rounds": exact_match_rate,
            "round_severity_distributions": round_dists,
        },
        "verdict_confirm_reject": {
            "cohens_kappa_pooled_pairs": verdict_kappa,
            "percent_agreement_pooled_pairs": verdict_po,
            "exact_match_rate_all_3_rounds": verdict_exact_3_rate,
        },
    }

    with open(f"{LANE_DIR}/stats_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
