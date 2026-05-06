"""Command-line entry point for the F6 A/B harness.

Usage::

    python -m scripts.f6_ab_harness \
        --backend legacy \
        --corpus-dir docs/research/f6-ab-corpus \
        --output /tmp/legacy.jsonl \
        --baseline-sha f72d3cfd

This is a thin wrapper around :func:`runner.run_corpus`. F6a ships it primarily
to validate import paths; F6b adds richer flags (parallel, retry, model
override) once the real backends land.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .backends import FakeBackend, LegacyBackend, OntologyBackend
from .metrics import compute_corpus_metrics
from .runner import run_corpus


def _build_backend(name: str):
    if name == "legacy":
        return LegacyBackend()
    if name == "ontology":
        return OntologyBackend()
    if name == "fake":
        return FakeBackend(script={})
    raise SystemExit(f"unknown backend: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, choices=["legacy", "ontology", "fake"])
    parser.add_argument("--corpus-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--metrics-output", type=Path, default=None)
    args = parser.parse_args(argv)

    backend = _build_backend(args.backend)
    aggregate = run_corpus(
        corpus_dir=args.corpus_dir,
        backend=backend,
        baseline_sha=args.baseline_sha,
        output_path=args.output,
    )
    print(
        f"[ab-harness] backend={aggregate.backend_name} "
        f"runs={len(aggregate.results)} skipped={len(aggregate.skipped)} "
        f"wall={aggregate.total_wall_time_sec:.1f}s cost=${aggregate.total_cost_usd:.4f}",
        file=sys.stderr,
    )
    if args.metrics_output:
        metrics = compute_corpus_metrics(
            corpus_dir=args.corpus_dir,
            results=aggregate.results,
            backend_name=aggregate.backend_name,
        )
        args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_output.write_text(
            "review_coverage_per_diff: {:.4f}\n"
            "agent_selection_macro_f1: {:.4f}\n"
            "p0_total: {}\n"
            "p1_total: {}\n"
            "cost_usd_total: {:.4f}\n"
            "cost_per_finding_usd: {:.4f}\n".format(
                metrics.review_coverage_per_diff,
                metrics.agent_selection_macro_f1,
                metrics.p0_total,
                metrics.p1_total,
                metrics.cost_usd_total,
                metrics.cost_per_finding_usd,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
