"""Calibration metrics: ECE, MCE, Brier, AUROC, reliability bins, signed miscalibration.

Pure-numpy and dependency-light so the metrics layer is unit-testable without any
API access, eval harness, or GPU. Everything here operates on two parallel arrays:

    confidences : model-stated confidence, either 0-100 (scale=100) or 0-1 (scale=1)
    correct     : 0/1 (or bool) correctness label for the same items

See ``RQ`` references in the project README for how each metric maps to a research
question.
"""

from __future__ import annotations

from typing import Sequence, TypedDict

import numpy as np

__all__ = [
    "ReliabilityBin",
    "to_unit_interval",
    "expected_calibration_error",
    "maximum_calibration_error",
    "brier_score",
    "auroc",
    "signed_miscalibration",
    "reliability_bins",
    "summarize",
]


class ReliabilityBin(TypedDict):
    """One row of a reliability diagram."""

    lo: float
    hi: float
    count: int
    weight: float  # fraction of all items that fall in this bin
    avg_confidence: float  # mean predicted confidence in the bin (NaN if empty)
    avg_accuracy: float  # mean correctness in the bin (NaN if empty)
    gap: float  # avg_confidence - avg_accuracy (signed; NaN if empty)


def to_unit_interval(confidences: Sequence[float], scale: float = 100.0) -> np.ndarray:
    """Coerce confidences to floats in [0, 1].

    ``scale`` is the maximum of the input range (100 for 0-100 verbalized confidence,
    1 for probabilities). Values are clipped into range defensively, since model
    self-reports occasionally exceed bounds.
    """
    conf = np.asarray(confidences, dtype=float) / float(scale)
    return np.clip(conf, 0.0, 1.0)


def _validate(confidences: np.ndarray, correct: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    correct = np.asarray(correct, dtype=float)
    if confidences.shape != correct.shape:
        raise ValueError(
            f"confidences and correct must align: {confidences.shape} vs {correct.shape}"
        )
    if confidences.size == 0:
        raise ValueError("empty inputs")
    return confidences, correct


def expected_calibration_error(
    confidences: Sequence[float],
    correct: Sequence[float],
    n_bins: int = 10,
    scale: float = 100.0,
) -> float:
    """Expected Calibration Error (equal-width binning).

    ECE = sum_b (n_b / N) * |acc_b - conf_b|. Lower is better; 0 is perfect.
    """
    conf = to_unit_interval(confidences, scale)
    conf, corr = _validate(conf, np.asarray(correct))
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = conf.size
    for lo, hi in zip(bins[:-1], bins[1:]):
        # left-open bins, except the first which includes 0.0
        mask = (conf > lo) & (conf <= hi)
        if lo == 0.0:
            mask |= conf == 0.0
        if not mask.any():
            continue
        ece += (mask.sum() / n) * abs(conf[mask].mean() - corr[mask].mean())
    return float(ece)


def maximum_calibration_error(
    confidences: Sequence[float],
    correct: Sequence[float],
    n_bins: int = 10,
    scale: float = 100.0,
) -> float:
    """Maximum Calibration Error: the worst per-bin |acc - conf| gap."""
    conf = to_unit_interval(confidences, scale)
    conf, corr = _validate(conf, np.asarray(correct))
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    worst = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (conf > lo) & (conf <= hi)
        if lo == 0.0:
            mask |= conf == 0.0
        if not mask.any():
            continue
        worst = max(worst, abs(conf[mask].mean() - corr[mask].mean()))
    return float(worst)


def brier_score(
    confidences: Sequence[float],
    correct: Sequence[float],
    scale: float = 100.0,
) -> float:
    """Mean squared error between confidence and correctness. Lower is better."""
    conf = to_unit_interval(confidences, scale)
    conf, corr = _validate(conf, np.asarray(correct))
    return float(np.mean((conf - corr) ** 2))


def auroc(
    confidences: Sequence[float],
    correct: Sequence[float],
    scale: float = 100.0,
) -> float:
    """AUROC for selective prediction: does confidence rank correct above incorrect?

    Computed via the rank-based Mann-Whitney equivalence (handles ties with average
    ranks). 0.5 = no discrimination, 1.0 = perfect ranking. Returns NaN when all
    labels are identical (AUROC undefined).
    """
    conf = to_unit_interval(confidences, scale)
    conf, corr = _validate(conf, np.asarray(correct))
    pos = corr == 1
    n_pos = int(pos.sum())
    n_neg = int(conf.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(conf, kind="mergesort")
    ranks = np.empty(conf.size, dtype=float)
    sorted_conf = conf[order]
    # assign average ranks (1-based) to tie groups
    i = 0
    while i < sorted_conf.size:
        j = i
        while j + 1 < sorted_conf.size and sorted_conf[j + 1] == sorted_conf[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    sum_ranks_pos = ranks[pos].sum()
    return float((sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def signed_miscalibration(
    confidences: Sequence[float],
    correct: Sequence[float],
    scale: float = 100.0,
) -> float:
    """Mean(confidence - accuracy). Positive = overconfident, negative = underconfident.

    This is the RQ2 workhorse: compute it per domain to see *direction* of
    miscalibration, not just magnitude (which ECE collapses to absolute value).
    """
    conf = to_unit_interval(confidences, scale)
    conf, corr = _validate(conf, np.asarray(correct))
    return float(conf.mean() - corr.mean())


def reliability_bins(
    confidences: Sequence[float],
    correct: Sequence[float],
    n_bins: int = 10,
    scale: float = 100.0,
) -> list[ReliabilityBin]:
    """Bin items by confidence and return per-bin stats for reliability diagrams."""
    conf = to_unit_interval(confidences, scale)
    conf, corr = _validate(conf, np.asarray(correct))
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = conf.size
    out: list[ReliabilityBin] = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi)
        if lo == 0.0:
            mask |= conf == 0.0
        count = int(mask.sum())
        if count == 0:
            out.append(
                ReliabilityBin(
                    lo=float(lo), hi=float(hi), count=0, weight=0.0,
                    avg_confidence=float("nan"), avg_accuracy=float("nan"),
                    gap=float("nan"),
                )
            )
            continue
        avg_conf = float(conf[mask].mean())
        avg_acc = float(corr[mask].mean())
        out.append(
            ReliabilityBin(
                lo=float(lo), hi=float(hi), count=count, weight=count / n,
                avg_confidence=avg_conf, avg_accuracy=avg_acc,
                gap=avg_conf - avg_acc,
            )
        )
    return out


def summarize(
    confidences: Sequence[float],
    correct: Sequence[float],
    n_bins: int = 10,
    scale: float = 100.0,
) -> dict[str, float]:
    """Compute the full metric panel in one call. Handy for per-(model, domain) rows."""
    conf = to_unit_interval(confidences, scale)
    _, corr = _validate(conf, np.asarray(correct))
    return {
        "n": int(conf.size),
        "accuracy": float(corr.mean()),
        "mean_confidence": float(conf.mean()),
        "ece": expected_calibration_error(confidences, correct, n_bins, scale),
        "mce": maximum_calibration_error(confidences, correct, n_bins, scale),
        "brier": brier_score(confidences, correct, scale),
        "auroc": auroc(confidences, correct, scale),
        "signed_miscalibration": signed_miscalibration(confidences, correct, scale),
    }


if __name__ == "__main__":
    # tiny smoke check so `python src/metrics.py` exercises the math
    rng = np.random.default_rng(42)
    conf = rng.integers(0, 101, size=500)
    # make correctness loosely track confidence so AUROC > 0.5
    corr = (rng.random(500) < conf / 100.0).astype(int)
    from pprint import pprint

    pprint(summarize(conf, corr))
