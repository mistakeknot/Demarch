"""Confidence-elicitation methods and parsers.

Three elicitation strategies from the spec (Section 5.4):

1. ``verbalized`` — ask for an answer plus an integer confidence 0-100. The primary
   method; works on every model, closed or open.
2. ``logprob``    — use probability mass on the chosen answer token. Only where the
   provider exposes logprobs; many closed APIs do not. Falls back gracefully.
3. ``sampling``   — sample N completions and use answer-agreement frequency as an
   implicit confidence (self-consistency).

The pure parsing helpers (``parse_confidence``, ``parse_answer_letter``) carry no
``inspect_ai`` dependency so they stay unit-testable. Inspect ``solver`` builders
import ``inspect_ai`` lazily inside the function body, so this module imports cleanly
even when the eval harness is not installed.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

__all__ = [
    "VERBALIZED_SYSTEM",
    "REFLECTION_SYSTEM",
    "parse_confidence",
    "parse_answer_letter",
    "verbalized_confidence",
    "sampling_self_consistency",
    "logprob_confidence_note",
]

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

VERBALIZED_SYSTEM = (
    "Answer the question as accurately as you can. On the final line, state your "
    "confidence that your answer is correct as an integer from 0 to 100, formatted "
    "exactly as:\nCONFIDENCE: <int>"
)

# RQ4: introspective-reflection variant. Asks the model to reason about its own
# certainty before committing a number. We test whether this helps or hurts.
REFLECTION_SYSTEM = (
    "Answer the question as accurately as you can. Before stating your confidence, "
    "briefly reflect on how sure you are and why — what would make you wrong, and "
    "how well do you actually know this? Then, on the final line, state your "
    "calibrated confidence that your answer is correct as an integer from 0 to 100, "
    "formatted exactly as:\nCONFIDENCE: <int>"
)

# ---------------------------------------------------------------------------
# Pure parsers (no inspect_ai dependency)
# ---------------------------------------------------------------------------

_CONF_RE = re.compile(r"CONFIDENCE:\s*(\d{1,3})", re.IGNORECASE)
# Match a confidence given as a bare percentage, used only as a fallback.
_PCT_RE = re.compile(r"(\d{1,3})\s*%")


def parse_confidence(text: str, default: Optional[int] = None) -> Optional[int]:
    """Extract an integer confidence 0-100 from model output.

    Prefers the exact ``CONFIDENCE: <int>`` line; falls back to the last bare
    percentage if the structured line is missing; clamps to [0, 100]. Returns
    ``default`` when nothing parseable is found.
    """
    if not text:
        return default
    m = _CONF_RE.search(text)
    if m is None:
        pcts = _PCT_RE.findall(text)
        if not pcts:
            return default
        value = int(pcts[-1])
    else:
        value = int(m.group(1))
    return max(0, min(100, value))


def parse_answer_letter(text: str, choices: Optional[list[str]] = None) -> Optional[str]:
    """Extract a multiple-choice answer letter (A-Z) from model output.

    Looks for ``ANSWER: X`` first, then a standalone leading letter, then (if
    ``choices`` given) a substring match against the option text. Case-insensitive;
    returns an uppercase letter or ``None``.
    """
    if not text:
        return None
    m = re.search(r"ANSWER:\s*([A-Za-z])", text)
    if m:
        return m.group(1).upper()
    m = re.search(r"\b([A-Za-z])\b[\).:]", text)
    if m:
        return m.group(1).upper()
    if choices:
        lowered = text.lower()
        for i, choice in enumerate(choices):
            if choice and choice.lower() in lowered:
                return chr(ord("A") + i)
    return None


def sampling_confidence(answers: list[Optional[str]]) -> tuple[Optional[str], float]:
    """Self-consistency confidence from N sampled answers.

    Returns ``(modal_answer, agreement_fraction)`` where the fraction is the share
    of (non-None) samples that agree with the most common answer — an implicit
    confidence in [0, 1]. Returns ``(None, 0.0)`` if no parseable answers.
    """
    valid = [a for a in answers if a is not None]
    if not valid:
        return None, 0.0
    counts = Counter(valid)
    modal, n = counts.most_common(1)[0]
    return modal, n / len(valid)


# ---------------------------------------------------------------------------
# Inspect solver builders (inspect_ai imported lazily)
# ---------------------------------------------------------------------------


def verbalized_confidence(reflect: bool = False):
    """Inspect solver: elicit answer + verbalized confidence in one generation.

    Set ``reflect=True`` for the RQ4 introspective-reflection prompt.
    """
    from inspect_ai.solver import generate, system_message, solver, Generate, TaskState

    sys = system_message(REFLECTION_SYSTEM if reflect else VERBALIZED_SYSTEM)
    gen = generate()

    @solver
    def _verbalized():
        async def solve(state: TaskState, generate_fn: Generate) -> TaskState:
            state = await sys(state, generate_fn)
            state = await gen(state, generate_fn)
            text = state.output.completion if state.output else ""
            state.metadata["elicitation"] = "verbalized_reflect" if reflect else "verbalized"
            state.metadata["confidence"] = parse_confidence(text)
            return state

        return solve

    return _verbalized()


def sampling_self_consistency(n: int = 10):
    """Inspect solver: sample N completions, use answer-agreement as confidence.

    Records ``metadata['confidence']`` as an integer 0-100 (agreement fraction * 100)
    and ``metadata['sampled_answers']`` for later inspection.
    """
    from inspect_ai.solver import generate, system_message, solver, Generate, TaskState

    sys = system_message(VERBALIZED_SYSTEM)

    @solver
    def _sampling():
        async def solve(state: TaskState, generate_fn: Generate) -> TaskState:
            state = await sys(state, generate_fn)
            choices = [c.value for c in state.choices] if getattr(state, "choices", None) else None
            answers: list[Optional[str]] = []
            for _ in range(n):
                state = await generate_fn(state)
                text = state.output.completion if state.output else ""
                answers.append(parse_answer_letter(text, choices))
            modal, agreement = sampling_confidence(answers)
            state.metadata["elicitation"] = "sampling"
            state.metadata["sampled_answers"] = answers
            state.metadata["modal_answer"] = modal
            state.metadata["confidence"] = int(round(agreement * 100))
            return state

        return solve

    return _sampling()


def logprob_confidence_note() -> str:
    """Return guidance on the logprob method.

    Logprob elicitation reads probability mass on the chosen answer token directly
    from the API response (``logprobs``). Availability is provider-specific: the
    Anthropic API does not currently expose token logprobs for chat completions, so
    this method is only runnable on open models (via vLLM/HF) and OpenAI-compatible
    endpoints that return ``logprobs``. When unavailable, record it as N/A in the run
    log rather than substituting another method — the *availability gap itself* is a
    finding worth reporting (RQ3).
    """
    return logprob_confidence_note.__doc__ or ""
