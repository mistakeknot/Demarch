"""Probe whether the `reasoning-effort` parameter grades the reasoning budget.

The dose-response experiment (is M-ratio monotone in reasoning budget?) presupposes
that `--reasoning-effort minimal|low|medium|high` actually administers graded doses.
This probe tests that precondition by measuring per-sample `reasoning_tokens` on MMLU
across effort levels. Result (Nous Portal Qwen3.5, 2026-06-16): it does NOT — the dial
is binary (`none`=0, anything-else="reasoning on", budget set by item difficulty), so the
dose-response is not runnable on this provider. See notes/reasoning-effort-not-graded.md.

Usage::

    # 1) run the probes (writes runs/effortprobe-<model>-<effort>/)
    python scripts/probe_reasoning_effort.py run --model qwen3.5-9b \
        --efforts none,minimal,low,medium,high --n 20
    # 2) build the CSV + figure from whatever probe logs exist
    python scripts/probe_reasoning_effort.py report --out figures \
        --summary runs/reasoning_effort_probe.csv

Two-step so the figure regenerates from committed CSV without re-spending on the API.
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

EFFORT_ORDER = ["none", "minimal", "low", "medium", "high", "xhigh", "max"]


def _per_sample_reasoning(log) -> list[int]:
    out = []
    for s in log.samples or []:
        mu = getattr(s, "model_usage", None)
        if mu:
            out.append(list(mu.values())[0].reasoning_tokens or 0)
    return out


def cmd_run(args) -> int:
    model = f"openai-api/nous/{args.model}" if "/" not in args.model else args.model
    short = args.model.split("/")[-1]
    for effort in args.efforts.split(","):
        log_dir = f"runs/effortprobe-{short}-{effort}"
        print(f"probing {short} @ effort={effort} (n={args.n}) -> {log_dir}")
        subprocess.run(
            ["inspect", "eval", "src/tasks.py@calibration_mmlu", "--model", model,
             "--reasoning-effort", effort, "--limit", str(args.n), "--log-dir", log_dir],
            check=True,
        )
    return 0


def cmd_report(args) -> int:
    from inspect_ai.log import read_eval_log

    # discover probe log dirs: runs/effortprobe-<model>-<effort>/  (+ legacy gate dirs)
    rows = []
    patterns = ["runs/effortprobe-*", "runs/gate20-*", "runs/gate-none", "runs/grade-*"]
    seen = set()
    for pat in patterns:
        for d in sorted(glob.glob(pat)):
            evals = glob.glob(os.path.join(d, "*.eval"))
            if not evals:
                continue
            log = read_eval_log(evals[0])
            model = log.eval.model.split("/")[-1]
            effort = (log.eval.model_args or {}).get("reasoning_effort") \
                or getattr(log.eval.model_generate_config, "reasoning_effort", None)
            # fall back to parsing the dir name suffix
            if not effort:
                effort = d.rstrip("/").split("-")[-1]
            key = (model, effort)
            if key in seen:
                continue
            seen.add(key)
            per = _per_sample_reasoning(log)
            if not per:
                continue
            rows.append({
                "model": model, "effort": effort, "n": len(per),
                "mean_reasoning_tokens": round(statistics.mean(per), 1),
                "median_reasoning_tokens": round(statistics.median(per), 1),
                "min": min(per), "max": max(per),
            })

    rows.sort(key=lambda r: (r["model"], EFFORT_ORDER.index(r["effort"])
                             if r["effort"] in EFFORT_ORDER else 99))
    os.makedirs(os.path.dirname(args.summary) or ".", exist_ok=True)
    with open(args.summary, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.summary}")
    for r in rows:
        print(f"  {r['model']:<18} {r['effort']:<8} n={r['n']:<3} "
              f"mean={r['mean_reasoning_tokens']:>8} median={r['median_reasoning_tokens']:>8}")

    _plot(rows, args.out)
    return 0


def _plot(rows, out_dir: str):
    import matplotlib.pyplot as plt

    models = sorted({r["model"] for r in rows})
    fig, ax = plt.subplots(figsize=(8, 5))
    graded_efforts = [e for e in EFFORT_ORDER if e != "none"]
    for model in models:
        mrows = {r["effort"]: r for r in rows if r["model"] == model}
        xs = [e for e in graded_efforts if e in mrows]
        if len(xs) < 2:
            # single-point models (cross-rung extremes): scatter
            for e in mrows:
                if e in graded_efforts:
                    ax.scatter(graded_efforts.index(e), mrows[e]["mean_reasoning_tokens"],
                               s=60, label=f"{model} ({e})")
            continue
        ax.plot([graded_efforts.index(e) for e in xs],
                [mrows[e]["mean_reasoning_tokens"] for e in xs],
                marker="o", linewidth=2, label=model)
    ax.set_xticks(range(len(graded_efforts)))
    ax.set_xticklabels(graded_efforts)
    ax.set_xlabel("reasoning-effort parameter")
    ax.set_ylabel("mean reasoning tokens / sample (MMLU)")
    ax.set_ylim(bottom=0)
    ax.set_title("reasoning-effort is not graded on Nous Portal Qwen3.5\n"
                 "(flat across levels — effort dial is binary none/on)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "reasoning_effort_not_graded.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"wrote {path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", default="qwen3.5-9b")
    r.add_argument("--efforts", default="none,minimal,low,medium,high")
    r.add_argument("--n", type=int, default=20)
    r.set_defaults(func=cmd_run)
    rep = sub.add_parser("report")
    rep.add_argument("--out", default="figures")
    rep.add_argument("--summary", default="runs/reasoning_effort_probe.csv")
    rep.set_defaults(func=cmd_report)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
