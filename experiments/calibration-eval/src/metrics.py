"""Calibration metrics: ECE, MCE, Brier, AUROC, reliability bins, signed miscalibration.

Pure-numpy and dependency-light so the metrics layer is unit-testable without any
API access, eval harness, or GPU. Everything here operates on two parallel arrays:

    confidences : model-stated confidence, either 0-100 (scale=100) or 0-1 (scale=1)
    correct     : 0/1 (or bool) correctness label for the same items

See ``RQ`` references in the project README for how each metric maps to a research
question.
"""

from __future__ import annotations

import math
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
    "d_prime",
    "meta_d_prime",
    "m_ratio",
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


# ---------------------------------------------------------------------------
# Type-2 SDT: metacognitive sensitivity & efficiency.
#
# The "knows what it knows" construct, controlling for task ability. Plain
# calibration/ECE is a *bias* measure confounded with accuracy; these estimators
# capture *sensitivity* (does confidence discriminate the model's own right from
# wrong answers) and *efficiency* (sensitivity relative to first-order ability).
# ``auroc`` above is the robust nonparametric sensitivity measure; the SDT-units
# views below add meta-d' and the M-ratio.
# ---------------------------------------------------------------------------

# Acklam's rational approximation to the inverse normal CDF, so we avoid a scipy
# dependency. Accurate to ~1e-9 over the open interval (0, 1).
_ACK_A = (-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
          1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00)
_ACK_B = (-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
          6.680131188771972e01, -1.328068155288572e01)
_ACK_C = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
          -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00)
_ACK_D = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
          3.754408661907416e00)


def _norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (quantile function) via Acklam's approximation."""
    p = min(max(p, 1e-16), 1.0 - 1e-16)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return ((((((_ACK_C[0] * q + _ACK_C[1]) * q + _ACK_C[2]) * q + _ACK_C[3]) * q
                  + _ACK_C[4]) * q + _ACK_C[5])
                / (((((_ACK_D[0] * q + _ACK_D[1]) * q + _ACK_D[2]) * q + _ACK_D[3]) * q + 1)))
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return ((((((_ACK_A[0] * r + _ACK_A[1]) * r + _ACK_A[2]) * r + _ACK_A[3]) * r
                  + _ACK_A[4]) * r + _ACK_A[5]) * q
                / ((((((_ACK_B[0] * r + _ACK_B[1]) * r + _ACK_B[2]) * r + _ACK_B[3]) * r
                     + _ACK_B[4]) * r + 1)))
    q = math.sqrt(-2 * math.log(1 - p))
    return (-((((((_ACK_C[0] * q + _ACK_C[1]) * q + _ACK_C[2]) * q + _ACK_C[3]) * q
               + _ACK_C[4]) * q + _ACK_C[5]))
            / (((((_ACK_D[0] * q + _ACK_D[1]) * q + _ACK_D[2]) * q + _ACK_D[3]) * q + 1)))


def _norm_cdf(x: float) -> float:
    """Standard-normal CDF via the error function (stdlib, no scipy)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# Below this first-order d', the M-ratio (meta-d'/d') is too unstable to report
# (corresponds to accuracy ~53%). Suppressed to NaN rather than emitting huge values.
D_PRIME_FLOOR = 0.1


def d_prime(correct: Sequence[float]) -> float:
    """First-order sensitivity (task ability) as a 2AFC-equivalent d'.

    Approximated as sqrt(2) * z(accuracy). This is a *proxy*: it treats the task as
    2AFC, which is rough for >2-option multiple choice. Reported only to form the
    M-ratio denominator. Accuracy is clamped off {0, 1} to keep d' finite.
    """
    corr = np.asarray(correct, dtype=float)
    if corr.size == 0:
        return float("nan")
    acc = min(max(float(corr.mean()), 1e-6), 1 - 1e-6)
    return math.sqrt(2.0) * _norm_ppf(acc)


def meta_d_prime(
    confidences: Sequence[float],
    correct: Sequence[float],
    scale: float = 100.0,
) -> float:
    """Metacognitive sensitivity in d' units.

    Derived from the type-2 ROC area under the equal-variance Gaussian model:
    AUC = Phi(d'/sqrt(2))  =>  meta-d' = sqrt(2) * z(type-2 AUROC). This is a
    deliberately simple estimator; the gold-standard MLE fit (Maniscalco & Lau 2012;
    Fleming's HMeta-d) is noted as future work in the README. Returns NaN when the
    type-2 AUROC is undefined (single outcome class).
    """
    a = auroc(confidences, correct, scale)
    if math.isnan(a):
        return float("nan")
    return math.sqrt(2.0) * _norm_ppf(a)


def m_ratio(
    confidences: Sequence[float],
    correct: Sequence[float],
    scale: float = 100.0,
) -> float:
    """Metacognitive efficiency: meta-d' / d'.

    ~1.0 means metacognition is about as good as first-order ability implies; < 1.0
    indicates inefficiency (confidence carries less information about correctness than
    task performance could support). This is the headline 'knows what it knows' number
    *controlling for capability* — exactly what plain ECE/calibration cannot isolate.

    Returns NaN when meta-d' is undefined or when first-order ability is near chance
    (``|d'| < D_PRIME_FLOOR``, i.e. accuracy ≲ 53%): the ratio is unstable there
    (d'→0 sends it to infinity), so it is suppressed rather than reported as garbage.
    """
    md = meta_d_prime(confidences, correct, scale)
    d = d_prime(correct)
    if math.isnan(md) or math.isnan(d) or abs(d) < D_PRIME_FLOOR:
        return float("nan")
    return md / d


def summarize(
    confidences: Sequence[float],
    correct: Sequence[float],
    n_bins: int = 10,
    scale: float = 100.0,
) -> dict[str, float]:
    """Compute the full metric panel in one call. Handy for per-(model, domain) rows.

    Keys are grouped conceptually: sensitivity/efficiency (the metacognition headline,
    capability-controlled) then the bias panel (calibration, confounded with accuracy).
    """
    conf = to_unit_interval(confidences, scale)
    _, corr = _validate(conf, np.asarray(correct))
    return {
        "n": int(conf.size),
        "accuracy": float(corr.mean()),
        "mean_confidence": float(conf.mean()),
        # --- sensitivity / efficiency (headline: "knows what it knows") ---
        "auroc": auroc(confidences, correct, scale),  # type-2 AUROC, nonparametric
        "d_prime": d_prime(correct),
        "meta_d_prime": meta_d_prime(confidences, correct, scale),
        "m_ratio": m_ratio(confidences, correct, scale),
        # --- bias panel (calibration; confounded with task ability) ---
        "ece": expected_calibration_error(confidences, correct, n_bins, scale),
        "mce": maximum_calibration_error(confidences, correct, n_bins, scale),
        "brier": brier_score(confidences, correct, scale),
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
