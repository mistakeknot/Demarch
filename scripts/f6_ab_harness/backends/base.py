"""Backend protocol + result types.

These types are the F6a contract — both backends (legacy + ontology) and the
harness runner consume them. They are frozen at F6a; any change in F6b must
preserve back-compat or restart the A/B baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Finding:
    """A single review finding emitted by a backend.

    Themes are the labels used to compute review-coverage-per-diff (the primary
    metric). A finding "covers" a ground-truth theme when one of its declared
    themes matches the theme. F6b's metric implementation may use either exact
    string match against ``themes`` or a tagger over the prose body — see
    docs/research/f6-measurement-preregistration.md §Metrics.
    """

    title: str
    """One-line summary of the finding."""

    severity: str
    """One of: P0, P1, P2, P3."""

    body: str
    """Full prose body of the finding (markdown)."""

    themes: tuple[str, ...] = ()
    """Free-form theme tags emitted by the backend; used for coverage scoring."""

    agent: str | None = None
    """Which agent emitted this finding (e.g., fd-architecture). None when synthesized."""


@dataclass(frozen=True)
class BackendResult:
    """The complete result of one backend run over one diff."""

    diff_id: str
    """Stable identifier — matches ``manifest.jsonl`` row + label file basename."""

    backend_name: str
    """Either ``legacy`` or ``ontology`` (or ``fake`` for tests)."""

    agents_dispatched: tuple[str, ...]
    """Names of review agents the backend dispatched (Step 1.3 launch list)."""

    findings: tuple[Finding, ...]
    """All findings the backend produced for this diff."""

    cost_usd: float
    """Estimated dollar cost of the run, sourced from ``estimate-costs.sh`` or interstat."""

    wall_time_sec: float
    """Wall-clock seconds the backend took on this diff."""

    backend_metadata: dict[str, str] = field(default_factory=dict)
    """Free-form per-backend metadata (e.g., model used, lattice template fired)."""


class Backend(Protocol):
    """Contract every triage backend must satisfy.

    A backend takes a unified diff (as text) plus the diff's stable id and
    returns a fully-populated :class:`BackendResult`. Backends are expected to
    be deterministic given the same diff + same baseline SHA; non-determinism
    is allowed but should be recorded in ``backend_metadata`` so the F6b
    ship-decision memo can call it out.

    The protocol is intentionally narrow — the F6 A/B is about *triage*
    quality, not orchestration. Backends own their own dispatch, cost
    accounting, and synthesis; the harness only compares the resulting
    BackendResult against ground-truth labels.
    """

    name: str
    """Backend identifier — surfaces in result rows and cost reports."""

    def triage(self, *, diff_id: str, diff_text: str, baseline_sha: str) -> BackendResult:
        """Run triage + dispatch + synthesis on the diff. See class docstring."""
        ...
