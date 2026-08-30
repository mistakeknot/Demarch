"""Internal-confidence probe — GPU-independent core of the introspection flagship.

Implements the parts of the grounding-chain analysis (DESIGN.md §3-4) that need only
captured activation arrays, so they are unit-testable with no GPU, no open weights, and
no API:

- ``fit_confidence_probe`` — the linear probe (Probe A / "Existence"): decode a model's
  *own* per-item correctness from residual-stream activations. Returns **out-of-fold**
  predictions so the reported decoding AUROC is honest (no train-on-test double-dipping,
  DESIGN §8).
- ``layer_sweep`` — fit the probe per layer; find where own-correctness becomes linearly
  decodable (DESIGN Probe A, locus selection).
- ``confidence_direction`` — the steering vector for Probe C (diff-of-means in raw
  activation space; norm-matchable, the standard ActAdd construction).
- ``dissociation_set`` — items where the internal signal and the verbalized report
  disagree; the confabulation-candidate set that Probe C focuses on (DESIGN Probe B->C).

Scoring reuses calibration-eval's type-2 SDT metrics (``_calmetrics``) so internal vs
verbalized vs logprob signals sit on the same footing (Probe B / "Headroom").

The two pieces that genuinely need nnsight + a GPU + open weights — ``capture_activations``
and ``steer_and_reelicit`` — are interface stubs below. They run in the desktop/WSL2
session (DESIGN §7); their signatures are fixed here so the analysis code above is written
and tested against them now.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src._calmetrics import auroc, meta_d_prime, m_ratio


# ---------------------------------------------------------------------------
# Probe A — decode an internal correctness signal (representational)
# ---------------------------------------------------------------------------


@dataclass
class ProbeResult:
    """Output of a fitted confidence probe at one locus/layer."""

    internal_conf: np.ndarray  # out-of-fold P(correct), aligned to input items, in [0,1]
    weight: np.ndarray  # logistic weight in *standardized* feature space, shape [d_model]
    bias: float  # logistic intercept (standardized space)
    feat_mean: np.ndarray  # standardization mean, shape [d_model]
    feat_std: np.ndarray  # standardization std (zeros mapped to 1), shape [d_model]
    auroc: float  # type-2 AUROC of internal_conf vs correctness (out-of-fold)
    meta_d_prime: float  # internal-signal meta-d' (out-of-fold)
    m_ratio: float  # internal-signal M-ratio (out-of-fold)
    n_folds: int


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # numerically stable logistic
    out = np.empty_like(z, dtype=float)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _standardize(
    X: np.ndarray, mean: np.ndarray | None = None, std: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if mean is None:
        mean = X.mean(axis=0)
    if std is None:
        std = X.std(axis=0)
        std = np.where(std == 0.0, 1.0, std)
    return (X - mean) / std, mean, std


def _logreg_fit(
    X: np.ndarray, y: np.ndarray, *, l2: float, lr: float, iters: int
) -> tuple[np.ndarray, float]:
    """L2-regularized logistic regression by full-batch gradient descent.

    numpy-only (matches calibration-eval's scipy-free philosophy) and deterministic, so a
    given (activations, labels) always yields the same probe — important for a
    pre-registered analysis. The intercept is unregularized.
    """
    n, d = X.shape
    w = np.zeros(d, dtype=float)
    b = 0.0
    for _ in range(iters):
        p = _sigmoid(X @ w + b)
        resid = p - y
        grad_w = X.T @ resid / n + l2 * w / n
        grad_b = float(resid.mean())
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def _kfold_indices(n: int, n_folds: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    return [fold for fold in np.array_split(idx, n_folds)]


def fit_confidence_probe(
    activations: np.ndarray,
    correct: Sequence[float],
    *,
    l2: float = 1.0,
    n_folds: int = 5,
    lr: float = 0.5,
    iters: int = 2000,
    seed: int = 0,
) -> ProbeResult:
    """Fit a linear probe that decodes own-correctness from activations (Probe A).

    ``activations`` is ``[n_items, d_model]`` captured at one locus/layer; ``correct`` is
    the 0/1 correctness label per item (from the behavioral eval logs). Predictions are
    produced **out-of-fold** (each item scored by a probe that did not see it), so
    ``auroc`` is an honest held-out decoding estimate, not a fit statistic. The returned
    ``weight``/``bias`` are then refit on *all* items for downstream use.

    The reported meta-d'/M-ratio put the internal signal on the same type-2 SDT footing as
    the verbalized report, enabling the headroom comparison (Probe B).
    """
    X = np.asarray(activations, dtype=float)
    y = np.asarray(correct, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"activations must be 2-D [n_items, d_model], got shape {X.shape}")
    if X.shape[0] != y.shape[0]:
        raise ValueError(f"activations/correct length mismatch: {X.shape[0]} vs {y.shape[0]}")
    n = X.shape[0]
    if n_folds < 2 or n_folds > n:
        raise ValueError(f"n_folds must be in [2, n_items={n}], got {n_folds}")

    folds = _kfold_indices(n, n_folds, seed)
    oof = np.full(n, np.nan, dtype=float)
    for test_idx in folds:
        train_idx = np.setdiff1d(np.arange(n), test_idx, assume_unique=False)
        Xtr, mean, std = _standardize(X[train_idx])
        w, b = _logreg_fit(Xtr, y[train_idx], l2=l2, lr=lr, iters=iters)
        Xte, _, _ = _standardize(X[test_idx], mean, std)
        oof[test_idx] = _sigmoid(Xte @ w + b)

    # full-data refit for the deployed probe weight/direction
    Xall, mean, std = _standardize(X)
    w_all, b_all = _logreg_fit(Xall, y, l2=l2, lr=lr, iters=iters)

    return ProbeResult(
        internal_conf=oof,
        weight=w_all,
        bias=b_all,
        feat_mean=mean,
        feat_std=std,
        auroc=auroc(oof, y, scale=1.0),
        meta_d_prime=meta_d_prime(oof, y, scale=1.0),
        m_ratio=m_ratio(oof, y, scale=1.0),
        n_folds=n_folds,
    )


def layer_sweep(
    activations_by_layer: dict[int, np.ndarray],
    correct: Sequence[float],
    **probe_kwargs,
) -> dict[int, ProbeResult]:
    """Fit ``fit_confidence_probe`` at each layer; the basis for locus selection.

    Returns ``{layer: ProbeResult}``. Read off the layer where decoding AUROC peaks (and,
    with capture at the answer-commitment token, whether it peaks *before* the
    verbalization tokens — the temporal-priority signal for headroom, DESIGN Probe A).
    """
    return {
        layer: fit_confidence_probe(acts, correct, **probe_kwargs)
        for layer, acts in sorted(activations_by_layer.items())
    }


def confidence_direction(
    activations: np.ndarray,
    correct: Sequence[float],
    *,
    high: float = 0.5,
) -> np.ndarray:
    """The steering vector for Probe C: diff-of-means in *raw* activation space.

    ``mean(correct activations) - mean(incorrect activations)``. Kept in raw (un-
    standardized) space so it can be added back to activations directly and norm-matched
    against a random control (DESIGN §4 Probe C, §8 controls). ``high`` lets you split on
    a graded internal-confidence array instead of the binary label by passing those values
    as ``correct`` with a threshold.
    """
    X = np.asarray(activations, dtype=float)
    c = np.asarray(correct, dtype=float)
    hi = c >= high
    lo = ~hi
    if not hi.any() or not lo.any():
        raise ValueError("need both high and low items to form a diff-of-means direction")
    return X[hi].mean(axis=0) - X[lo].mean(axis=0)


# ---------------------------------------------------------------------------
# Probe B -> C — dissociation set (the confabulation-candidate items)
# ---------------------------------------------------------------------------


def dissociation_set(
    internal_conf: Sequence[float],
    verbalized_conf: Sequence[float],
    *,
    internal_scale: float = 1.0,
    verbalized_scale: float = 100.0,
    margin: float = 0.3,
) -> dict[str, np.ndarray]:
    """Items where the internal signal and the verbalized report disagree (DESIGN Probe B).

    Both signals are mapped to [0, 1]. An item is flagged when they differ by more than
    ``margin``. These are the highest-signal targets for the causal test (Probe C): if
    steering the internal signal moves the report on exactly the items where they currently
    diverge, that is the grounding evidence.

    Returns index arrays:
      - ``internal_high_verbal_low``: model "feels" right but reports low confidence
        (introspective headroom the report fails to surface)
      - ``internal_low_verbal_high``: model reports high confidence with no internal
        support (confabulation candidates)
      - ``either``: the union, the Probe-C focus set
    """
    iconf = np.clip(np.asarray(internal_conf, dtype=float) / internal_scale, 0.0, 1.0)
    vconf = np.clip(np.asarray(verbalized_conf, dtype=float) / verbalized_scale, 0.0, 1.0)
    if iconf.shape != vconf.shape:
        raise ValueError(f"signal length mismatch: {iconf.shape} vs {vconf.shape}")
    gap = iconf - vconf
    internal_high = np.where(gap > margin)[0]
    internal_low = np.where(gap < -margin)[0]
    return {
        "internal_high_verbal_low": internal_high,
        "internal_low_verbal_high": internal_low,
        "either": np.union1d(internal_high, internal_low),
    }


# ---------------------------------------------------------------------------
# Probe A capture & Probe C steering — nnsight-backed, run on the GPU host.
# Interfaces are fixed here so the analysis above is written/tested against them now;
# implementations land in the desktop/WSL2 session (DESIGN §7). See ../RUNBOOK once added.
# ---------------------------------------------------------------------------

_GPU_STUB = (
    "{name} needs nnsight + open weights + a GPU and runs in the desktop/WSL2 session "
    "(DESIGN §7). This cloud-session scaffold fixes the interface and tests the "
    "GPU-independent analysis; wire the implementation when the 4090 is reachable."
)


def capture_activations(
    model,
    items: Sequence[dict],
    layers: Sequence[int],
    *,
    locus: str = "answer_token",
):
    """Capture residual-stream activations at ``locus`` for each item, swept over ``layers``.

    Target signature (implemented on the GPU host):
        -> dict[int, np.ndarray]   # {layer: [n_items, d_model]}

    ``locus`` is the pre-registered token to read (DESIGN §8: answer-commitment token by
    default; optionally also the confidence-number token to separate reading vs writing the
    report). Offload to CPU/disk — a single locus token is not a storage bottleneck.
    """
    raise NotImplementedError(_GPU_STUB.format(name="capture_activations"))


def steer_and_reelicit(
    model,
    items: Sequence[dict],
    direction: np.ndarray,
    alphas: Sequence[float],
    layer: int,
):
    """Add ``alpha * direction`` at ``layer``, re-elicit confidence, sweep ``alphas`` (Probe C).

    Target signature (implemented on the GPU host):
        -> dict[float, dict]   # {alpha: {"verbalized_conf": ndarray, "answer_changed": ndarray}}

    Grounded iff stated confidence moves monotonically with alpha; confabulated iff the
    report is unmoved while the decodable signal is clearly shifted. Always run with the
    norm-matched random-direction control and a capability sanity check (DESIGN §8).
    """
    raise NotImplementedError(_GPU_STUB.format(name="steer_and_reelicit"))
