"""Aggregate Inspect eval logs into per-(model, domain) calibration metrics + figures.

Usage::

    python -m src.analyze runs/*.eval --out figures --summary runs/summary.csv

Reads Inspect ``.eval`` logs (via ``inspect_ai.log.read_eval_log``), pulls the parsed
``confidence`` and ``correct`` fields out of each sample's score metadata, groups by
domain_type, and writes:

  * a reliability diagram per (model, elicitation, domain)
  * the RQ2 signed-miscalibration-by-domain bar chart per model
  * a tidy summary CSV (one row per model x elicitation x domain)

This is the bridge from raw run outputs to the figures the writeup claims (5.9).
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict

from src.metrics import summarize
from src.plotting import domain_miscalibration_bar, reliability_diagram, rq1_ladder_plot


def _extract(log) -> list[dict]:
    """Pull (model, elicitation, domain, confidence, correct) rows from a log."""
    rows: list[dict] = []
    model = log.eval.model
    for sample in log.samples or []:
        score = next(iter(sample.scores.values())) if sample.scores else None
        if score is None:
            continue
        md = score.metadata or {}
        conf = md.get("confidence")
        if conf is None:
            continue  # unparseable confidence -> excluded, counted separately upstream
        rows.append(
            {
                "model": model,
                "elicitation": md.get("elicitation", "verbalized"),
                "domain": md.get("domain_type", "unknown"),
                "confidence": float(conf),
                "correct": 1.0 if md.get("correct") else 0.0,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="+", help="Inspect .eval log files")
    ap.add_argument("--out", default="figures", help="figure output dir")
    ap.add_argument("--summary", default="runs/summary.csv", help="summary CSV path")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument(
        "--ladder", action="append", default=None, metavar="SUB1,SUB2,...",
        help="ordered comma-separated model-name substrings (small -> large) forming one "
             "capability ladder; emits the RQ1 sensitivity-vs-capability figure for the "
             "verbalized arm. Repeat the flag for additional ladders (one figure each).",
    )
    args = ap.parse_args(argv)

    from inspect_ai.log import read_eval_log

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.dirname(args.summary) or ".", exist_ok=True)

    # group rows: (model, elicitation, domain) -> {confidences, correct}
    grouped: dict[tuple, dict[str, list]] = defaultdict(
        lambda: {"confidence": [], "correct": []}
    )
    for path in args.logs:
        log = read_eval_log(path)
        for r in _extract(log):
            key = (r["model"], r["elicitation"], r["domain"])
            grouped[key]["confidence"].append(r["confidence"])
            grouped[key]["correct"].append(r["correct"])

    # per-model domain summaries for the RQ2 bar chart
    per_model_domain: dict[tuple, dict[str, dict]] = defaultdict(dict)
    summary_rows: list[dict] = []

    for (model, elicit, domain), data in sorted(grouped.items()):
        stats = summarize(data["confidence"], data["correct"], n_bins=args.bins)
        summary_rows.append({"model": model, "elicitation": elicit, "domain": domain, **stats})
        per_model_domain[(model, elicit)][domain] = stats

        safe = f"{model}_{elicit}_{domain}".replace("/", "-").replace(" ", "_")
        reliability_diagram(
            data["confidence"], data["correct"], n_bins=args.bins,
            title=f"{model} · {elicit} · {domain}",
            out_path=os.path.join(args.out, f"reliability_{safe}.png"),
        )

    for (model, elicit), by_domain in per_model_domain.items():
        safe = f"{model}_{elicit}".replace("/", "-").replace(" ", "_")
        domain_miscalibration_bar(
            by_domain,
            title=f"Signed miscalibration by domain — {model} ({elicit})",
            out_path=os.path.join(args.out, f"rq2_domains_{safe}.png"),
        )

    # RQ1: sensitivity vs capability across each requested ladder (verbalized arm)
    for ladder_spec in args.ladder or []:
        rungs = [r.strip() for r in ladder_spec.split(",") if r.strip()]
        ladder_stats: dict[str, dict[str, dict]] = {}
        for rung in rungs:
            doms: dict[str, dict[str, list]] = defaultdict(
                lambda: {"confidence": [], "correct": []}
            )
            for (model, elicit, domain), data in grouped.items():
                if elicit != "verbalized" or rung not in model:
                    continue
                doms[domain]["confidence"] += data["confidence"]
                doms[domain]["correct"] += data["correct"]
            if not doms:
                print(f"ladder rung {rung!r}: no verbalized rows matched — skipped")
                continue
            stats = {
                d: summarize(v["confidence"], v["correct"], n_bins=args.bins)
                for d, v in doms.items()
            }
            all_conf = [c for v in doms.values() for c in v["confidence"]]
            all_corr = [c for v in doms.values() for c in v["correct"]]
            stats["pooled"] = summarize(all_conf, all_corr, n_bins=args.bins)
            ladder_stats[rung] = stats
        if len(ladder_stats) >= 2:
            safe = f"{rungs[0]}_to_{rungs[-1]}".replace("/", "-").replace(" ", "_")
            rq1_ladder_plot(
                ladder_stats, rungs,
                out_path=os.path.join(args.out, f"rq1_ladder_{safe}.png"),
            )

    if summary_rows:
        with open(args.summary, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

    print(f"Wrote {len(summary_rows)} summary rows to {args.summary}")
    print(f"Figures in {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
