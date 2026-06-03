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
from src.plotting import domain_miscalibration_bar, reliability_diagram


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
