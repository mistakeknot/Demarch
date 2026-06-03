"""Reliability diagrams and summary figures.

``matplotlib`` is imported lazily inside each function so the module imports without
a plotting backend installed (keeps ``metrics``/``scoring`` import chains light).
"""

from __future__ import annotations

from typing import Optional, Sequence

from src.metrics import ReliabilityBin, reliability_bins, summarize

__all__ = ["reliability_diagram", "domain_miscalibration_bar"]


def reliability_diagram(
    confidences: Sequence[float],
    correct: Sequence[float],
    n_bins: int = 10,
    scale: float = 100.0,
    title: str = "Reliability diagram",
    out_path: Optional[str] = None,
    ax=None,
):
    """Plot a binned reliability diagram (accuracy vs confidence).

    The diagonal is perfect calibration; bars below it are overconfidence, above it
    underconfidence. Bin widths are annotated by count. Returns the matplotlib Axes.
    """
    import matplotlib.pyplot as plt

    bins: list[ReliabilityBin] = reliability_bins(confidences, correct, n_bins, scale)
    stats = summarize(confidences, correct, n_bins, scale)

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))

    centers = [(b["lo"] + b["hi"]) / 2 for b in bins]
    accs = [b["avg_accuracy"] if b["count"] else 0.0 for b in bins]
    width = 1.0 / n_bins

    ax.bar(centers, accs, width=width * 0.9, edgecolor="black", alpha=0.75,
           label="accuracy", color="#4878d0")
    # gap-to-confidence overlay
    for b, c in zip(bins, centers):
        if b["count"] == 0:
            continue
        ax.plot([c, c], [b["avg_accuracy"], b["avg_confidence"]],
                color="#d65f5f", linewidth=1.5, alpha=0.6)

    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="perfect")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("confidence")
    ax.set_ylabel("accuracy")
    sign = "over" if stats["signed_miscalibration"] > 0 else "under"
    ax.set_title(
        f"{title}\nECE={stats['ece']:.3f}  Brier={stats['brier']:.3f}  "
        f"({sign}confident {abs(stats['signed_miscalibration']):.3f})"
    )
    ax.legend(loc="upper left", fontsize=8)

    if out_path:
        import matplotlib.pyplot as plt
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
    return ax


def domain_miscalibration_bar(
    by_domain: dict[str, dict[str, float]],
    metric: str = "signed_miscalibration",
    title: str = "Signed miscalibration by domain",
    out_path: Optional[str] = None,
    ax=None,
):
    """Bar chart of a metric across domain types (the RQ2 headline figure).

    ``by_domain`` maps domain_type -> the dict returned by ``metrics.summarize``.
    """
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))

    domains = list(by_domain.keys())
    values = [by_domain[d][metric] for d in domains]
    colors = ["#d65f5f" if v > 0 else "#4878d0" for v in values]

    ax.bar(domains, values, color=colors, edgecolor="black", alpha=0.8)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel(metric)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=20)

    if out_path:
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
    return ax
