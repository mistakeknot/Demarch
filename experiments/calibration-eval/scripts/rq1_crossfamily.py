"""Cross-family RQ1 synthesis: metacognitive efficiency vs scale, by reasoning mode.

Reads pooled-verbalized M-ratio / type-2 AUROC for each model across one or more runs
dirs, groups models into within-family size ladders, and plots M-ratio vs ladder rank
with families colored by reasoning mode. Tests whether the RQ1 "inversion" (efficiency
rises in some families, falls in others) tracks reasoning mode rather than family.

Usage::

    python scripts/rq1_crossfamily.py --runs-dir runs \
        --runs-dir /home/user/Sylveste/experiments/calibration-eval/runs \
        --out figures --summary runs/rq1_crossfamily.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.metrics import summarize  # noqa: E402

# family -> (reasoning?, ordered rungs small->large by model-name substring)
FAMILIES = {
    "Ministral": (False, ["ministral-3b", "ministral-8b", "ministral-14b"]),
    "Gemma3": (False, ["gemma-3-12b", "gemma-3-27b"]),
    "Hermes4": (False, ["hermes-4-70b", "hermes-4-405b"]),
    "Qwen3": (True, ["qwen3-8b", "qwen3-14b", "qwen3-32b"]),
    "Qwen3.5": (True, ["qwen3.5-9b", "qwen3.5-27b", "qwen3.5-35b-a3b",
                       "qwen3.5-122b-a10b", "qwen3.5-397b-a17b"]),
}


def pooled_verbalized(runs_dirs: list[str]) -> dict[str, tuple[list, list]]:
    from inspect_ai.log import read_eval_log

    pools: dict[str, tuple[list, list]] = {}
    seen_files = set()
    for d in runs_dirs:
        for p in sorted(glob.glob(os.path.join(d, "*.eval"))):
            real = os.path.realpath(p)
            if real in seen_files:
                continue
            seen_files.add(real)
            h = read_eval_log(p, header_only=True)
            if h.status != "success":
                continue
            ta = h.eval.task_args or {}
            if ta.get("elicitation", "verbalized") != "verbalized" or ta.get("reflect"):
                continue
            model = h.eval.model.split("/")[-1]
            log = read_eval_log(p)
            for s in log.samples or []:
                md = next(iter(s.scores.values())).metadata or {}
                if md.get("confidence") is None:
                    continue
                conf, corr = pools.setdefault(model, ([], []))
                conf.append(float(md["confidence"]))
                corr.append(1.0 if md.get("correct") else 0.0)
    return pools


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-dir", action="append", required=True, dest="runs_dirs")
    ap.add_argument("--out", default="figures")
    ap.add_argument("--summary", default="runs/rq1_crossfamily.csv")
    args = ap.parse_args(argv)

    pools = pooled_verbalized(args.runs_dirs)

    rows = []
    fam_stats: dict[str, list] = {}
    for fam, (reasoning, rungs) in FAMILIES.items():
        pts = []
        for rank, sub in enumerate(rungs):
            match = next((m for m in pools if sub in m), None)
            if not match:
                continue
            st = summarize(*pools[match])
            pts.append((rank, match, st))
            rows.append({
                "family": fam, "reasoning": reasoning, "rank": rank, "model": match,
                "n": st["n"], "accuracy": round(st["accuracy"], 3),
                "auroc": round(st["auroc"], 3), "d_prime": round(st["d_prime"], 3),
                "meta_d_prime": round(st["meta_d_prime"], 3),
                "m_ratio": round(st["m_ratio"], 3), "ece": round(st["ece"], 3),
            })
        if len(pts) >= 2:
            fam_stats[fam] = pts

    os.makedirs(os.path.dirname(args.summary) or ".", exist_ok=True)
    with open(args.summary, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.summary}")

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, metric, label, ref, refname in (
        (axes[0], "m_ratio", "M-ratio (meta-d′ / d′)", 1.0, "ideal"),
        (axes[1], "auroc", "type-2 AUROC", 0.5, "chance"),
    ):
        for fam, pts in fam_stats.items():
            reasoning = FAMILIES[fam][0]
            color = "#d62728" if reasoning else "#1f77b4"
            style = "-o" if reasoning else "--s"
            xs = [p[0] for p in pts]
            ys = [p[2][metric] for p in pts]
            ax.plot(xs, ys, style, color=color, alpha=0.8, linewidth=2,
                    label=f"{fam} {'(reasoning)' if reasoning else '(non-reason)'}")
        ax.axhline(ref, color="grey", linestyle=":", linewidth=1, label=refname)
        ax.set_xlabel("ladder rank (small → large within family)")
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=7, loc="best")
    fig.suptitle("RQ1 cross-family: does metacognitive efficiency track scale or reasoning mode?\n"
                 "red = reasoning families, blue = non-reasoning (verbalized confidence)")
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "rq1_crossfamily.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"wrote {path}")
    for r in rows:
        print(f"  {r['family']:<9} {r['model']:<20} M={r['m_ratio']:<6} "
              f"AUROC={r['auroc']:<6} acc={r['accuracy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
