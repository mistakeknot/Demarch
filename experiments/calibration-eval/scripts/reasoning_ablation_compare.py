"""Compare reasoning-ON vs reasoning-OFF runs across the Qwen3.5 ladder.

Usage::

    python scripts/reasoning_ablation_compare.py \
        --on-dir /path/to/reasoning-on/runs --off-dir runs --out figures

Reads Inspect ``.eval`` logs from both directories, computes per-rung pooled
verbalized panels (H1: M-ratio / type-2 AUROC) and custom-set sampling AUROC
(H2), writes ``figures/reasoning_ablation.png`` and prints a markdown table
for the PR.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.metrics import summarize  # noqa: E402

LADDER = [
    "qwen3.5-9b",
    "qwen3.5-27b",
    "qwen3.5-35b-a3b",
    "qwen3.5-122b-a10b",
    "qwen3.5-397b-a17b",
]


def collect(log_dir: str) -> dict[tuple[str, str], tuple[list, list]]:
    """(rung, arm) -> (confidences, correct); arm in verbalized/sampling/reflect.

    Verbalized pools custom + anchors; sampling/reflect only ran on the custom set.
    """
    from inspect_ai.log import read_eval_log

    pools: dict[tuple[str, str], tuple[list, list]] = {}
    for path in sorted(glob.glob(os.path.join(log_dir, "*.eval"))):
        log = read_eval_log(path, header_only=True)
        model = log.eval.model.split("/")[-1]
        if model not in LADDER or log.status != "success":
            continue
        ta = log.eval.task_args or {}
        arm = "reflect" if ta.get("reflect") else ta.get("elicitation", "verbalized")
        log = read_eval_log(path)
        for sample in log.samples or []:
            md = next(iter(sample.scores.values())).metadata or {}
            if md.get("confidence") is None:
                continue
            conf, corr = pools.setdefault((model, arm), ([], []))
            conf.append(float(md["confidence"]))
            corr.append(1.0 if md.get("correct") else 0.0)
    return pools


def panel(pools, rung, arm):
    if (rung, arm) not in pools:
        return None
    return summarize(*pools[(rung, arm)])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--on-dir", required=True, help="runs dir with reasoning-ON logs")
    ap.add_argument("--off-dir", required=True, help="runs dir with reasoning-OFF logs")
    ap.add_argument("--out", default="figures")
    args = ap.parse_args(argv)

    on = collect(args.on_dir)
    off = collect(args.off_dir)

    # --- markdown table (pooled verbalized; H1) ---
    print("\n### H1 — pooled verbalized, reasoning ON vs OFF\n")
    print("| rung | mode | n | acc | type-2 AUROC | d' | meta-d' | M-ratio | ECE |")
    print("|---|---|---|---|---|---|---|---|---|")
    for rung in LADDER:
        for mode, pools in (("ON", on), ("OFF", off)):
            st = panel(pools, rung, "verbalized")
            if st is None:
                continue
            print(
                f"| {rung} | {mode} | {st['n']} | {st['accuracy']:.3f} | "
                f"{st['auroc']:.3f} | {st['d_prime']:.2f} | {st['meta_d_prime']:.2f} | "
                f"**{st['m_ratio']:.3f}** | {st['ece']:.3f} |"
            )

    print("\n### H2 — custom-set sampling self-consistency AUROC, ON vs OFF\n")
    print("| rung | ON | OFF |")
    print("|---|---|---|")
    for rung in LADDER:
        a = panel(on, rung, "sampling")
        b = panel(off, rung, "sampling")
        fmt = lambda s: f"{s['auroc']:.3f}" if s else "—"
        print(f"| {rung} | {fmt(a)} | {fmt(b)} |")

    # --- figure ---
    import matplotlib.pyplot as plt

    x = list(range(len(LADDER)))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    specs = [
        (axes[0], "verbalized", "m_ratio", "M-ratio (meta-d' / d')", 1.0, "ideal"),
        (axes[1], "verbalized", "auroc", "type-2 AUROC (verbalized)", 0.5, "chance"),
        (axes[2], "sampling", "auroc", "type-2 AUROC (sampling, custom set)", 0.5, "chance"),
    ]
    for ax, arm, metric, label, ref, refname in specs:
        for mode, pools, style in (("reasoning ON", on, "-o"), ("reasoning OFF", off, "--s")):
            ys = []
            for rung in LADDER:
                st = panel(pools, rung, arm)
                ys.append(st[metric] if st else float("nan"))
            ax.plot(x, ys, style, linewidth=2, label=mode)
        ax.axhline(ref, color="grey", linestyle=":", linewidth=1, label=refname)
        ax.set_xticks(x)
        ax.set_xticklabels(LADDER, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8)
    fig.suptitle("Reasoning-mode ablation — Qwen3.5 ladder")
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "reasoning_ablation.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
