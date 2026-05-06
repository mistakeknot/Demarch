"""Metric computation for the F6 A/B harness.

Pre-registered metrics (see ``docs/research/f6-measurement-preregistration.md``):

- **Primary — review-coverage-per-diff.** Per-diff fraction of
  ``expected_findings_themes`` (ground truth) covered by the backend's emitted
  findings, then averaged across the corpus.
- **Secondary — agent-selection F1.** Precision and recall over the
  ``expected_agents`` set, treating ``BackendResult.agents_dispatched`` as the
  predicted set.
- **Secondary — P0/P1 finding count.** Sum of findings with severity P0 or P1
  across the corpus.
- **Secondary — cost-per-finding.** Total backend USD divided by the count of
  emitted findings (defaults to total USD when zero findings, since
  divide-by-zero would obscure the bad case).

The PRD also names ``user-accepted-verdict-rate`` as a secondary metric. It is
deferred to longitudinal data after F6b ships and is *not* gated for the
ship/abandon decision in F6b.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .backends.base import BackendResult


@dataclass(frozen=True)
class AgentSelectionMetrics:
    """Precision / recall / F1 for one diff's agent selection."""

    precision: float
    recall: float
    f1: float
    expected: tuple[str, ...]
    predicted: tuple[str, ...]


@dataclass(frozen=True)
class DiffMetrics:
    """Per-diff metric bundle."""

    diff_id: str
    coverage: float
    """Fraction of expected themes covered by the emitted findings."""

    matched_themes: tuple[str, ...]
    unmatched_themes: tuple[str, ...]
    agent_selection: AgentSelectionMetrics
    p0_count: int
    p1_count: int
    cost_usd: float
    wall_time_sec: float


@dataclass(frozen=True)
class CorpusMetrics:
    """Aggregated across the whole corpus."""

    backend_name: str
    diff_count: int
    review_coverage_per_diff: float
    """Mean of per-diff coverage — the primary metric."""

    agent_selection_macro_f1: float
    agent_selection_macro_precision: float
    agent_selection_macro_recall: float
    p0_total: int
    p1_total: int
    findings_total: int
    cost_usd_total: float
    cost_per_finding_usd: float
    wall_time_total_sec: float
    per_diff: tuple[DiffMetrics, ...] = field(default_factory=tuple)


_TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9]+")


def _tokenise(text: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_SPLIT.split(text) if len(tok) >= 3}


def _theme_covered(theme: str, result: BackendResult) -> bool:
    """A theme is covered when one of the result's findings either declares the theme
    via :attr:`Finding.themes` or matches it on token-overlap of body+title.

    Token-overlap match: a finding covers the theme when ≥ 60% of the theme's
    content tokens (≥ 3 chars) appear in the finding's title+body. This keeps
    the harness deterministic and language-agnostic; F6b may swap in an
    embedding-based matcher provided the threshold is calibrated against this
    corpus and recorded in the ship-decision memo.
    """
    norm_theme = theme.strip().lower()
    if not norm_theme:
        return False
    theme_tokens = _tokenise(norm_theme)
    if not theme_tokens:
        return False
    for finding in result.findings:
        for declared in finding.themes:
            if declared.strip().lower() == norm_theme:
                return True
        haystack = _tokenise(f"{finding.title}\n{finding.body}")
        if not haystack:
            continue
        overlap = theme_tokens & haystack
        if len(overlap) / len(theme_tokens) >= 0.6:
            return True
    return False


def _agent_metrics(expected: tuple[str, ...], predicted: tuple[str, ...]) -> AgentSelectionMetrics:
    exp_set = set(expected)
    pred_set = set(predicted)
    tp = len(exp_set & pred_set)
    fp = len(pred_set - exp_set)
    fn = len(exp_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return AgentSelectionMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        expected=tuple(sorted(exp_set)),
        predicted=tuple(sorted(pred_set)),
    )


def _load_label(corpus_dir: Path, diff_id: str, label_path: str) -> dict:
    target = corpus_dir / label_path
    return json.loads(target.read_text(encoding="utf-8"))


def compute_diff_metrics(
    *,
    result: BackendResult,
    label: dict,
) -> DiffMetrics:
    """Compute metrics for a single diff given the backend's result and ground-truth label."""
    expected_themes = tuple(label.get("expected_findings_themes", ()))
    matched: list[str] = []
    unmatched: list[str] = []
    for theme in expected_themes:
        if _theme_covered(theme, result):
            matched.append(theme)
        else:
            unmatched.append(theme)
    coverage = len(matched) / len(expected_themes) if expected_themes else 0.0

    expected_agents = tuple(label.get("expected_agents", ()))
    agent_metrics = _agent_metrics(expected_agents, result.agents_dispatched)

    severities = [f.severity for f in result.findings]
    p0 = sum(1 for s in severities if s == "P0")
    p1 = sum(1 for s in severities if s == "P1")

    return DiffMetrics(
        diff_id=result.diff_id,
        coverage=coverage,
        matched_themes=tuple(matched),
        unmatched_themes=tuple(unmatched),
        agent_selection=agent_metrics,
        p0_count=p0,
        p1_count=p1,
        cost_usd=result.cost_usd,
        wall_time_sec=result.wall_time_sec,
    )


def compute_corpus_metrics(
    *,
    corpus_dir: Path,
    results: list[BackendResult],
    backend_name: str,
) -> CorpusMetrics:
    """Aggregate per-diff metrics into the corpus-level bundle.

    Loads each diff's label file directly; the manifest's ``label_path``
    column is consulted via convention (``labels/<diff_id>.json``) when no
    explicit row is provided.
    """
    manifest = corpus_dir / "manifest.jsonl"
    label_paths: dict[str, str] = {}
    if manifest.exists():
        with manifest.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                row = json.loads(line)
                label_paths[row["diff_id"]] = row.get(
                    "label_path", f"labels/{row['diff_id']}.json"
                )
    per_diff: list[DiffMetrics] = []
    for result in results:
        label_path = label_paths.get(result.diff_id, f"labels/{result.diff_id}.json")
        label = _load_label(corpus_dir, result.diff_id, label_path)
        per_diff.append(compute_diff_metrics(result=result, label=label))
    diff_count = len(per_diff)
    coverage = sum(d.coverage for d in per_diff) / diff_count if diff_count else 0.0
    macro_f1 = (
        sum(d.agent_selection.f1 for d in per_diff) / diff_count if diff_count else 0.0
    )
    macro_p = (
        sum(d.agent_selection.precision for d in per_diff) / diff_count if diff_count else 0.0
    )
    macro_r = (
        sum(d.agent_selection.recall for d in per_diff) / diff_count if diff_count else 0.0
    )
    findings_total = sum(len(r.findings) for r in results)
    cost_total = sum(r.cost_usd for r in results)
    wall_total = sum(r.wall_time_sec for r in results)
    cost_per_finding = cost_total / findings_total if findings_total else cost_total
    return CorpusMetrics(
        backend_name=backend_name,
        diff_count=diff_count,
        review_coverage_per_diff=coverage,
        agent_selection_macro_f1=macro_f1,
        agent_selection_macro_precision=macro_p,
        agent_selection_macro_recall=macro_r,
        p0_total=sum(d.p0_count for d in per_diff),
        p1_total=sum(d.p1_count for d in per_diff),
        findings_total=findings_total,
        cost_usd_total=cost_total,
        cost_per_finding_usd=cost_per_finding,
        wall_time_total_sec=wall_total,
        per_diff=tuple(per_diff),
    )
