"""F6 A/B harness — runner, metrics, and Backend contract for the legacy↔ontology triage A/B test.

This package is shipped at F6a (sylveste-2n8i) as scaffolding only. The two real
backends (legacy flux-drive wrapper, ontology lattice-template wrapper) land in
F6b (sylveste-g939). The runner, metrics module, and Backend protocol are
frozen at F6a so F6b cannot regress the contract.

See docs/research/f6-ab-corpus/README.md and
docs/research/f6-measurement-preregistration.md for the full design.
"""

from .backends.base import Backend, BackendResult, Finding
from .metrics import (
    AgentSelectionMetrics,
    CorpusMetrics,
    DiffMetrics,
    compute_corpus_metrics,
    compute_diff_metrics,
)
from .runner import RunnerResult, run_corpus

__all__ = [
    "Backend",
    "BackendResult",
    "Finding",
    "AgentSelectionMetrics",
    "CorpusMetrics",
    "DiffMetrics",
    "RunnerResult",
    "compute_corpus_metrics",
    "compute_diff_metrics",
    "run_corpus",
]
