"""Correctness scorers and the combined confidence scorer.

Pure correctness helpers (``mc_correct``, ``numeric_correct``, ``text_correct``) are
``inspect_ai``-free and unit-testable. ``confidence_scorer`` is the Inspect ``scorer``
that pairs a correctness check with the parsed confidence, recording both into the
sample metadata so ``metrics.py`` can aggregate per (model, domain, elicitation).
"""

from __future__ import annotations

import re
from typing import Optional, Sequence

from src.elicitation import parse_answer_letter, parse_confidence

__all__ = [
    "mc_correct",
    "numeric_correct",
    "text_correct",
    "confidence_scorer",
]


def mc_correct(output: str, target: str, choices: Optional[Sequence[str]] = None) -> bool:
    """Multiple-choice correctness by letter match (e.g. target='B')."""
    pred = parse_answer_letter(output, list(choices) if choices else None)
    if pred is None:
        return False
    return pred.upper() == target.strip().upper()


_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")
_CONF_LINE_RE = re.compile(r"CONFIDENCE:\s*\d{1,3}", re.IGNORECASE)


def numeric_correct(output: str, target: str, tol: float = 1e-6) -> bool:
    """GSM8K-style numeric match: compare the last number in the output to target.

    The trailing ``CONFIDENCE: <int>`` line every elicitation prompt requests is
    stripped first — otherwise the confidence value is always the last number and
    the answer is never compared.
    """
    output = _CONF_LINE_RE.sub("", output)
    nums = _NUM_RE.findall(output.replace(",", ""))
    if not nums:
        return False
    try:
        pred = float(nums[-1])
        gold = float(re.sub(r"[^\d.\-]", "", target))
    except ValueError:
        return False
    return abs(pred - gold) <= tol * max(1.0, abs(gold))


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def text_correct(output: str, target: str) -> bool:
    """Free-text correctness: case/punctuation-insensitive substring containment.

    Intentionally lenient — used for the custom interest-domain set where the gold is
    a short reference phrase. Noise here is acknowledged in the writeup's limitations.
    """
    return _normalize(target) in _normalize(output)


def confidence_scorer(answer_kind: str = "mc"):
    """Inspect scorer: correctness (0/1) + parsed confidence in the sample metadata.

    ``answer_kind`` selects the correctness helper: 'mc' | 'numeric' | 'text'.
    """
    from inspect_ai.scorer import scorer, Score, Target, accuracy, mean, stderr
    from inspect_ai.solver import TaskState

    @scorer(metrics=[accuracy(), mean(), stderr()])
    def _scorer():
        async def score(state: TaskState, target: Target) -> Score:
            output = state.output.completion if state.output else ""
            gold = target.text
            choices = [c.value for c in state.choices] if getattr(state, "choices", None) else None
            modal = state.metadata.get("modal_answer")
            if answer_kind == "numeric":
                ok = numeric_correct(output, gold)
            elif answer_kind == "text":
                ok = text_correct(output, gold)
            elif modal is not None:
                # sampling self-consistency: the agreement confidence refers to the
                # modal answer, so correctness must be judged on it — not on whichever
                # sample happened to be generated last
                ok = modal.strip().upper() == gold.strip().upper()
            else:
                ok = mc_correct(output, gold, choices)

            # confidence may have been set by the solver (sampling); else parse here
            conf = state.metadata.get("confidence")
            if conf is None:
                conf = parse_confidence(output)

            return Score(
                value=1.0 if ok else 0.0,
                answer=output[:500],
                metadata={
                    "correct": bool(ok),
                    "confidence": conf,
                    "domain_type": state.metadata.get("domain_type"),
                    "elicitation": state.metadata.get("elicitation", "verbalized"),
                },
            )

        return score

    return _scorer()
