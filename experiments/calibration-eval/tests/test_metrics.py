"""Unit tests for the pure-numpy metrics and parsers (no API / no inspect_ai)."""

import math

import numpy as np
import pytest

from src.elicitation import (
    logprob_to_confidence,
    parse_answer_letter,
    parse_confidence,
    sampling_confidence,
)
from src.metrics import (
    auroc,
    brier_score,
    d_prime,
    expected_calibration_error,
    m_ratio,
    maximum_calibration_error,
    meta_d_prime,
    reliability_bins,
    signed_miscalibration,
    summarize,
    to_unit_interval,
)
from src.metrics import _norm_cdf, _norm_ppf
from src.scoring import mc_correct, numeric_correct, text_correct


# ----------------------------- metrics ------------------------------------


def test_to_unit_interval_scales_and_clips():
    out = to_unit_interval([0, 50, 100, 150], scale=100)
    assert np.allclose(out, [0.0, 0.5, 1.0, 1.0])


def test_perfect_calibration_zero_ece():
    # confidence exactly equals per-bin accuracy -> ECE 0
    conf = [100, 100, 0, 0]
    correct = [1, 1, 0, 0]
    assert expected_calibration_error(conf, correct, n_bins=10) == pytest.approx(0.0)


def test_total_miscalibration_ece_one():
    # always 100% confident, always wrong -> ECE 1
    conf = [100] * 20
    correct = [0] * 20
    assert expected_calibration_error(conf, correct) == pytest.approx(1.0)
    assert maximum_calibration_error(conf, correct) == pytest.approx(1.0)


def test_brier_bounds():
    assert brier_score([100, 100], [1, 1]) == pytest.approx(0.0)
    assert brier_score([100, 100], [0, 0]) == pytest.approx(1.0)
    assert brier_score([50, 50], [1, 0]) == pytest.approx(0.25)


def test_signed_miscalibration_direction():
    # overconfident: high confidence, low accuracy -> positive
    assert signed_miscalibration([90, 90], [0, 0]) > 0
    # underconfident: low confidence, high accuracy -> negative
    assert signed_miscalibration([10, 10], [1, 1]) < 0


def test_auroc_perfect_and_chance():
    # confidence perfectly separates correct from incorrect
    conf = [10, 20, 80, 90]
    correct = [0, 0, 1, 1]
    assert auroc(conf, correct) == pytest.approx(1.0)
    # reversed -> 0.0
    assert auroc(conf, [1, 1, 0, 0]) == pytest.approx(0.0)


def test_auroc_ties_give_half():
    # all confidences equal -> no discrimination -> 0.5
    assert auroc([50, 50, 50, 50], [1, 0, 1, 0]) == pytest.approx(0.5)


def test_auroc_undefined_single_class():
    assert math.isnan(auroc([10, 90], [1, 1]))


def test_reliability_bins_partition_counts():
    conf = list(range(0, 101, 10))  # 0,10,...,100 -> 11 items
    correct = [1] * 11
    bins = reliability_bins(conf, correct, n_bins=10)
    assert len(bins) == 10
    assert sum(b["count"] for b in bins) == 11
    assert sum(b["weight"] for b in bins) == pytest.approx(1.0)


def test_summarize_keys():
    out = summarize([10, 50, 90], [0, 1, 1])
    for key in (
        "n", "accuracy", "auroc", "d_prime", "meta_d_prime", "m_ratio",
        "ece", "mce", "brier", "signed_miscalibration",
    ):
        assert key in out


# --------------------- type-2 SDT / metacognition -------------------------


def test_norm_ppf_inverts_cdf():
    for p in (0.05, 0.3, 0.5, 0.8, 0.99):
        assert _norm_cdf(_norm_ppf(p)) == pytest.approx(p, abs=1e-6)


def test_norm_ppf_symmetry():
    assert _norm_ppf(0.5) == pytest.approx(0.0, abs=1e-9)
    assert _norm_ppf(0.975) == pytest.approx(1.959963, abs=1e-4)


def test_d_prime_zero_at_chance():
    assert d_prime([1, 1, 0, 0]) == pytest.approx(0.0, abs=1e-6)
    assert d_prime([1, 1, 1, 0]) > 0.5  # above-chance accuracy -> positive d'


def test_meta_d_prime_high_when_confidence_separates():
    md = meta_d_prime([10, 20, 80, 90], [0, 0, 1, 1])  # type-2 AUROC = 1.0
    assert md > 3.0


def test_meta_d_prime_zero_at_chance_sensitivity():
    md = meta_d_prime([50, 50, 50, 50], [1, 0, 1, 0])  # AUROC = 0.5
    assert md == pytest.approx(0.0, abs=0.5)


def test_meta_d_prime_nan_single_class():
    assert math.isnan(meta_d_prime([10, 90], [1, 1]))


def test_m_ratio_nan_at_chance_accuracy():
    # accuracy 0.5 -> d' ~ 0 -> efficiency undefined
    assert math.isnan(m_ratio([10, 20, 80, 90], [0, 1, 0, 1]))


def test_m_ratio_finite_positive_when_sensitive():
    val = m_ratio([10, 20, 80, 90, 95, 99], [0, 0, 1, 1, 1, 1])
    assert not math.isnan(val) and val > 0


def test_ideal_type2_auroc_anchors():
    # closed-form ideal type-2 AUROC must match the SDT simulation to ~0.005
    from src.metrics import _ideal_type2_auroc
    assert _ideal_type2_auroc(0.0) == pytest.approx(0.5, abs=1e-6)
    assert _ideal_type2_auroc(0.5) == pytest.approx(0.615, abs=0.005)
    assert _ideal_type2_auroc(1.0) == pytest.approx(0.722, abs=0.005)
    assert _ideal_type2_auroc(2.0) == pytest.approx(0.886, abs=0.005)


def test_m_ratio_ideal_observer_near_one():
    # An ideal equal-variance SDT observer has true meta-d' == d', so the estimator
    # must read M-ratio ~1.0. (The old sqrt(2)*z(AUROC) estimator read ~0.84 here.)
    rng = np.random.default_rng(7)
    for d_true in (0.75, 1.5):
        n = 60000
        s1 = rng.normal(d_true, 1.0, n)  # signal interval
        s2 = rng.normal(0.0, 1.0, n)     # noise interval
        correct = (s1 > s2).astype(int)
        conf = np.abs(s1 - s2)           # ideal (boundary-distance) confidence
        conf01 = (conf.argsort().argsort() / n) * 100  # monotone -> 0-100
        assert m_ratio(conf01, correct) == pytest.approx(1.0, abs=0.08)


# ----------------------- logprob elicitation ------------------------------


class _Tok:
    def __init__(self, token, logprob):
        self.token = token
        self.logprob = logprob


def test_logprob_to_confidence_reads_chosen_token():
    toks = [_Tok("ANSWER", -0.1), _Tok(":", -0.01), _Tok("B", math.log(0.9))]
    assert logprob_to_confidence(toks, "B") == 90


def test_logprob_to_confidence_missing_token():
    toks = [_Tok("A", math.log(0.7))]
    assert logprob_to_confidence(toks, "C") is None
    assert logprob_to_confidence(toks, "C", default=50) == 50


def test_logprob_to_confidence_none_answer():
    assert logprob_to_confidence([_Tok("A", -0.1)], None) is None


def test_mismatched_shapes_raise():
    with pytest.raises(ValueError):
        expected_calibration_error([10, 20], [1])


# ----------------------------- parsers ------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The answer is 4.\nCONFIDENCE: 80", 80),
        ("CONFIDENCE:7", 7),
        ("confidence: 150", 100),  # clamp
        ("I am about 65% sure", 65),  # fallback to bare percent
        ("no idea", None),
    ],
)
def test_parse_confidence(text, expected):
    assert parse_confidence(text) == expected


def test_parse_confidence_default():
    assert parse_confidence("", default=50) == 50


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ANSWER: C", "C"),
        ("My answer is b) because...", "B"),
        ("ANSWER: g", "G"),
    ],
)
def test_parse_answer_letter(text, expected):
    assert parse_answer_letter(text) == expected


def test_parse_answer_letter_by_choice_text():
    choices = ["Paris", "London", "Berlin"]
    assert parse_answer_letter("It is clearly London.", choices) == "B"


def test_sampling_confidence_modal_and_fraction():
    modal, frac = sampling_confidence(["A", "A", "B", "A", None])
    assert modal == "A"
    assert frac == pytest.approx(3 / 4)  # None excluded


# --------------------------- correctness ----------------------------------


def test_mc_correct():
    assert mc_correct("ANSWER: B", "B")
    assert not mc_correct("ANSWER: A", "B")


def test_numeric_correct():
    assert numeric_correct("So the total is 42.", "42")
    assert numeric_correct("answer: 1,234", "1234")
    assert not numeric_correct("about 41", "42")


def test_numeric_correct_ignores_confidence_line():
    # the elicitation prompt appends CONFIDENCE: <int>; it must not be
    # mistaken for the answer
    assert numeric_correct("her earnings are $18.\n\nCONFIDENCE: 100", "18")
    assert not numeric_correct("the answer is 7.\nCONFIDENCE: 95", "95")


def test_text_correct_lenient():
    assert text_correct("It is the Mona Lisa, by da Vinci.", "mona lisa")
    assert not text_correct("It is The Scream.", "mona lisa")
