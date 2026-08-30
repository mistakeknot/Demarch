"""Tests for the GPU-independent probe core.

No nnsight, no GPU, no API: synthetic activations with a known relationship to correctness
exercise the decode (Probe A), the steering-direction construction (Probe C), and the
dissociation selector (Probe B). Verifies the calibration-eval metric bridge wires up.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.probe import (
    ProbeResult,
    confidence_direction,
    dissociation_set,
    fit_confidence_probe,
    layer_sweep,
)
from src._calmetrics import auroc, m_ratio


def _synthetic(n=400, d=32, signal=2.0, seed=0):
    """Activations where one direction carries correctness, the rest is noise."""
    rng = np.random.default_rng(seed)
    correct = rng.integers(0, 2, size=n).astype(float)
    direction = rng.standard_normal(d)
    direction /= np.linalg.norm(direction)
    acts = rng.standard_normal((n, d))
    acts += signal * (correct[:, None] - 0.5) * direction[None, :]
    return acts, correct, direction


# --- Probe A: decode --------------------------------------------------------


def test_probe_decodes_planted_signal():
    acts, correct, _ = _synthetic(signal=2.5)
    res = fit_confidence_probe(acts, correct, seed=1)
    assert isinstance(res, ProbeResult)
    # a strong planted signal should be decodable well above chance, out-of-fold
    assert res.auroc > 0.8
    assert res.internal_conf.shape == correct.shape
    assert not np.isnan(res.internal_conf).any()  # every item scored out-of-fold
    assert (res.internal_conf >= 0).all() and (res.internal_conf <= 1).all()


def test_probe_on_pure_noise_is_chance():
    rng = np.random.default_rng(7)
    acts = rng.standard_normal((300, 16))
    correct = rng.integers(0, 2, size=300).astype(float)  # independent of acts
    res = fit_confidence_probe(acts, correct, seed=2)
    # out-of-fold AUROC on label-independent features should sit near 0.5
    assert 0.4 < res.auroc < 0.6


def test_probe_oof_auroc_matches_calmetrics():
    acts, correct, _ = _synthetic(signal=1.5)
    res = fit_confidence_probe(acts, correct, seed=3)
    # the ProbeResult.auroc must be exactly the bridged metric on the OOF predictions
    assert res.auroc == pytest.approx(auroc(res.internal_conf, correct, scale=1.0))
    assert res.m_ratio == pytest.approx(m_ratio(res.internal_conf, correct, scale=1.0), nan_ok=True)


def test_probe_is_deterministic():
    acts, correct, _ = _synthetic(signal=2.0)
    a = fit_confidence_probe(acts, correct, seed=5)
    b = fit_confidence_probe(acts, correct, seed=5)
    assert a.auroc == b.auroc
    np.testing.assert_array_equal(a.internal_conf, b.internal_conf)


def test_fit_validates_shapes():
    with pytest.raises(ValueError):
        fit_confidence_probe(np.zeros((10,)), np.zeros(10))  # 1-D activations
    with pytest.raises(ValueError):
        fit_confidence_probe(np.zeros((10, 4)), np.zeros(9))  # length mismatch
    with pytest.raises(ValueError):
        fit_confidence_probe(np.zeros((10, 4)), np.zeros(10), n_folds=1)  # too few folds


# --- layer sweep ------------------------------------------------------------


def test_layer_sweep_returns_result_per_layer():
    acts_hi, correct, _ = _synthetic(signal=3.0, seed=10)
    acts_lo, _, _ = _synthetic(signal=0.0, seed=10)  # same labels, no signal
    sweep = layer_sweep({5: acts_lo, 12: acts_hi}, correct, seed=4)
    assert set(sweep) == {5, 12}
    # the layer carrying the planted signal should decode better
    assert sweep[12].auroc > sweep[5].auroc


# --- Probe C: steering direction -------------------------------------------


def test_confidence_direction_recovers_planted_axis():
    acts, correct, planted = _synthetic(signal=3.0, seed=20)
    direction = confidence_direction(acts, correct)
    assert direction.shape == planted.shape
    # diff-of-means should align with the planted correctness axis (cosine near +/-1)
    cos = float(direction @ planted / (np.linalg.norm(direction) * np.linalg.norm(planted)))
    assert abs(cos) > 0.7


def test_confidence_direction_needs_both_classes():
    acts = np.random.default_rng(0).standard_normal((20, 8))
    with pytest.raises(ValueError):
        confidence_direction(acts, np.ones(20))  # all "high", no contrast


# --- Probe B: dissociation set ---------------------------------------------


def test_dissociation_splits_by_direction():
    # item 0: internal high (0.9), verbal low (10/100) -> internal_high_verbal_low
    # item 1: internal low (0.1), verbal high (90/100) -> internal_low_verbal_high
    # item 2: agree (0.8 vs 80) -> neither
    internal = [0.9, 0.1, 0.8]
    verbal = [10, 90, 80]
    out = dissociation_set(internal, verbal, margin=0.3)
    assert out["internal_high_verbal_low"].tolist() == [0]
    assert out["internal_low_verbal_high"].tolist() == [1]
    assert out["either"].tolist() == [0, 1]


def test_dissociation_validates_shapes():
    with pytest.raises(ValueError):
        dissociation_set([0.5, 0.5], [50])
