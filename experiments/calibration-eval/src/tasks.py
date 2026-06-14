"""Inspect task definitions for the calibration eval.

Each task pairs a dataset with an elicitation solver and the confidence scorer. Run
them with the Inspect CLI, e.g.::

    inspect eval src/tasks.py@calibration_custom --model anthropic/claude-opus-4-8
    inspect eval src/tasks.py@calibration_mmlu   --model anthropic/claude-sonnet-4-6 --limit 200

The custom interest-domain task (RQ2) is the distinctive one; the public-benchmark
tasks (MMLU/GPQA/TruthfulQA/GSM8K) anchor it against known calibration baselines.

Note: model strings change — verify current identifiers before running. Public
datasets load via HuggingFace; the first run downloads them.
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, hf_dataset, json_dataset

from src.elicitation import (
    logprob_confidence,
    sampling_self_consistency,
    verbalized_confidence,
)
from src.scoring import confidence_scorer

# anchored to the experiment root so both `inspect eval` (resolves relative to this
# file) and programmatic eval() from the repo (resolves relative to cwd) find it
CUSTOM_FILE = str(Path(__file__).resolve().parent.parent / "data" / "interest_domain.jsonl")


# ---------------------------------------------------------------------------
# Custom interest-domain set (RQ2) — the study's distinctive contribution
# ---------------------------------------------------------------------------


def _custom_record_to_sample(record: dict) -> Sample:
    return Sample(
        id=record.get("id"),
        input=record["question"],
        choices=record.get("choices"),
        target=record["target"],
        metadata={"domain_type": record.get("domain_type", "unknown")},
    )


def _custom_dataset(path: str = CUSTOM_FILE):
    return json_dataset(path, sample_fields=_custom_record_to_sample)


@task
def calibration_custom(elicitation: str = "verbalized", reflect: bool = False) -> Task:
    """Calibration on the author's balanced interest-domain set (RQ2 + RQ4).

    ``elicitation``: 'verbalized' | 'logprob' | 'sampling'.
    ``reflect=True`` swaps in the introspective-reflection prompt (RQ4; verbalized only).
    """
    if elicitation == "sampling":
        solver = sampling_self_consistency()
    elif elicitation == "logprob":
        solver = logprob_confidence()
    else:
        solver = verbalized_confidence(reflect=reflect)
    return Task(
        dataset=_custom_dataset(),
        solver=solver,
        scorer=confidence_scorer(answer_kind="mc"),
    )


# ---------------------------------------------------------------------------
# Public-benchmark anchors
# ---------------------------------------------------------------------------


def _mmlu_to_sample(record: dict) -> Sample:
    return Sample(
        input=record["question"],
        choices=record["choices"],
        target="ABCD"[int(record["answer"])],
        metadata={"domain_type": "verifiable_technical", "subject": record.get("subject")},
    )


@task
def calibration_mmlu(reflect: bool = False) -> Task:
    """MMLU multiple-choice calibration anchor (broad knowledge)."""
    return Task(
        dataset=hf_dataset(
            "cais/mmlu", name="all", split="test", sample_fields=_mmlu_to_sample,
        ),
        solver=verbalized_confidence(reflect=reflect),
        scorer=confidence_scorer(answer_kind="mc"),
    )


def _gpqa_to_sample(record: dict) -> Sample:
    # gpqa_diamond stores the correct answer and three distractors as columns;
    # multiple_choice() shuffles, so we present them in a fixed order here.
    choices = [
        record["Correct Answer"],
        record["Incorrect Answer 1"],
        record["Incorrect Answer 2"],
        record["Incorrect Answer 3"],
    ]
    return Sample(
        input=record["Question"],
        choices=choices,
        target="A",  # correct answer placed first; shuffle_choices below remaps it
        metadata={"domain_type": "verifiable_technical"},
    )


@task
def calibration_gpqa(reflect: bool = False) -> Task:
    """GPQA-Diamond: hard science, calibration at the frontier of competence."""
    return Task(
        dataset=hf_dataset(
            "Idavidrein/gpqa", name="gpqa_diamond", split="train",
            sample_fields=_gpqa_to_sample, shuffle_choices=42,
        ),
        solver=verbalized_confidence(reflect=reflect),
        scorer=confidence_scorer(answer_kind="mc"),
    )


def _truthfulqa_to_sample(record: dict) -> Sample:
    choices = record["mc1_targets"]["choices"]
    labels = record["mc1_targets"]["labels"]
    target = "ABCDEFGH"[labels.index(1)]
    return Sample(
        input=record["question"],
        choices=choices,
        target=target,
        metadata={"domain_type": "contested_factual"},
    )


@task
def calibration_truthfulqa(reflect: bool = False) -> Task:
    """TruthfulQA (MC1): items models tend to get *confidently* wrong."""
    return Task(
        dataset=hf_dataset(
            # mc1 places the correct answer near the front (target is overwhelmingly
            # "A"); shuffle so position bias can't masquerade as accuracy
            "truthfulqa/truthful_qa", name="multiple_choice", split="validation",
            sample_fields=_truthfulqa_to_sample, shuffle_choices=42,
        ),
        solver=verbalized_confidence(reflect=reflect),
        scorer=confidence_scorer(answer_kind="mc"),
    )


def _gsm8k_to_sample(record: dict) -> Sample:
    # gold answer is after the '####' delimiter
    answer = record["answer"].split("####")[-1].strip()
    return Sample(
        input=record["question"],
        target=answer,
        metadata={"domain_type": "verifiable_technical"},
    )


@task
def calibration_gsm8k(reflect: bool = False) -> Task:
    """GSM8K: grade-school math; verifiable numeric correctness."""
    return Task(
        dataset=hf_dataset(
            "openai/gsm8k", name="main", split="test", sample_fields=_gsm8k_to_sample,
        ),
        solver=verbalized_confidence(reflect=reflect),
        scorer=confidence_scorer(answer_kind="numeric"),
    )
