"""End-to-end test for the F6 A/B harness scaffolding.

Exercises the runner + metrics + Backend protocol with FakeBackend so the
contract is locked in at F6a — F6b cannot regress the surface without
breaking this suite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.f6_ab_harness import (
    compute_corpus_metrics,
    run_corpus,
)
from scripts.f6_ab_harness.backends import (
    FakeBackend,
    LegacyBackend,
    OntologyBackend,
)
from scripts.f6_ab_harness.backends.base import Finding
from scripts.f6_ab_harness.backends.fake import FakeBackendScript


def _write_corpus(tmp: Path) -> Path:
    corpus = tmp / "corpus"
    (corpus / "labels").mkdir(parents=True)
    (corpus / "diffs").mkdir(parents=True)

    manifest_rows = [
        {
            "diff_id": "d01-fixture-validation",
            "sha": "0000000000000000000000000000000000000001",
            "summary": "feat(api): add input validation to /users",
            "label_path": "labels/d01-fixture-validation.json",
            "diff_snapshot_path": "diffs/d01-fixture-validation.diff",
        },
        {
            "diff_id": "d02-fixture-perf",
            "sha": "0000000000000000000000000000000000000002",
            "summary": "perf(query): batch DB lookup",
            "label_path": "labels/d02-fixture-perf.json",
            "diff_snapshot_path": "diffs/d02-fixture-perf.diff",
        },
    ]
    (corpus / "manifest.jsonl").write_text(
        "\n".join(json.dumps(r) for r in manifest_rows) + "\n",
        encoding="utf-8",
    )

    (corpus / "labels" / "d01-fixture-validation.json").write_text(
        json.dumps(
            {
                "diff_id": "d01-fixture-validation",
                "sha": "0000000000000000000000000000000000000001",
                "summary": "feat(api): add input validation",
                "domain_hints": ["web-api"],
                "expected_agents": ["fd-safety", "fd-correctness"],
                "expected_findings_themes": [
                    "input validation introduces new attack surface for injection",
                    "missing rate limit allows downstream resource exhaustion",
                ],
                "rationale": "API change — safety + correctness mandatory.",
                "complexity": "small",
                "discriminating": True,
                "labeler": "test-fixture",
                "labeler_notes": "fixture only",
                "human_validated": False,
                "label_version": "v1.0.0",
            }
        ),
        encoding="utf-8",
    )
    (corpus / "labels" / "d02-fixture-perf.json").write_text(
        json.dumps(
            {
                "diff_id": "d02-fixture-perf",
                "sha": "0000000000000000000000000000000000000002",
                "summary": "perf(query): batch DB lookup",
                "domain_hints": ["web-api"],
                "expected_agents": ["fd-performance"],
                "expected_findings_themes": [
                    "batched lookup may hide N+1 regression on small queries",
                ],
                "rationale": "Performance-tagged commit; fd-performance fires.",
                "complexity": "small",
                "discriminating": False,
                "labeler": "test-fixture",
                "labeler_notes": "fixture only",
                "human_validated": False,
                "label_version": "v1.0.0",
            }
        ),
        encoding="utf-8",
    )

    (corpus / "diffs" / "d01-fixture-validation.diff").write_text(
        "diff --git a/api.py b/api.py\n+def add_user(payload):\n+    return validate(payload)\n",
        encoding="utf-8",
    )
    (corpus / "diffs" / "d02-fixture-perf.diff").write_text(
        "diff --git a/query.py b/query.py\n"
        "+def fetch_users(ids):\n"
        "+    return db.fetch_many(ids)\n",
        encoding="utf-8",
    )
    return corpus


def test_runner_writes_results_and_aggregates(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path)
    backend = FakeBackend(
        script={
            "d01-fixture-validation": FakeBackendScript(
                agents_dispatched=("fd-safety", "fd-correctness"),
                findings=(
                    Finding(
                        title="Validation lacks injection guard",
                        severity="P1",
                        body="adding input validation introduces new attack surface for injection",
                        themes=("input validation introduces new attack surface for injection",),
                        agent="fd-safety",
                    ),
                    Finding(
                        title="No rate limiter",
                        severity="P2",
                        body="missing rate limit allows downstream resource exhaustion",
                        themes=("missing rate limit allows downstream resource exhaustion",),
                        agent="fd-correctness",
                    ),
                ),
                cost_usd=0.42,
            ),
            "d02-fixture-perf": FakeBackendScript(
                agents_dispatched=("fd-performance",),
                findings=(
                    Finding(
                        title="Possible N+1 regression",
                        severity="P1",
                        body="batched lookup may hide n+1 regression on small queries",
                        themes=("batched lookup may hide N+1 regression on small queries",),
                        agent="fd-performance",
                    ),
                ),
                cost_usd=0.13,
            ),
        }
    )

    out = tmp_path / "results.jsonl"
    aggregate = run_corpus(
        corpus_dir=corpus,
        backend=backend,
        baseline_sha="deadbeef",
        output_path=out,
        repo_root=tmp_path,
    )

    assert len(aggregate.results) == 2
    assert aggregate.skipped == []
    assert pytest.approx(aggregate.total_cost_usd, rel=1e-3) == 0.55

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert {r["diff_id"] for r in rows} == {"d01-fixture-validation", "d02-fixture-perf"}

    metrics = compute_corpus_metrics(
        corpus_dir=corpus,
        results=aggregate.results,
        backend_name=backend.name,
    )
    assert metrics.diff_count == 2
    assert metrics.review_coverage_per_diff == pytest.approx(1.0)
    assert metrics.agent_selection_macro_f1 == pytest.approx(1.0)
    assert metrics.p1_total == 2
    assert metrics.p0_total == 0
    assert metrics.findings_total == 3
    assert metrics.cost_usd_total == pytest.approx(0.55, rel=1e-3)


def test_runner_skips_when_backend_stub_raises(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path)
    out = tmp_path / "results.jsonl"
    aggregate = run_corpus(
        corpus_dir=corpus,
        backend=LegacyBackend(),
        baseline_sha="deadbeef",
        output_path=out,
        repo_root=tmp_path,
    )
    assert aggregate.results == []
    assert {diff_id for diff_id, _ in aggregate.skipped} == {
        "d01-fixture-validation",
        "d02-fixture-perf",
    }
    aggregate2 = run_corpus(
        corpus_dir=corpus,
        backend=OntologyBackend(),
        baseline_sha="deadbeef",
        output_path=out,
        repo_root=tmp_path,
    )
    assert aggregate2.results == []
    assert all("backend stub" in reason for _, reason in aggregate2.skipped)


def test_metrics_partial_coverage_and_agent_selection(tmp_path: Path) -> None:
    corpus = _write_corpus(tmp_path)
    backend = FakeBackend(
        script={
            "d01-fixture-validation": FakeBackendScript(
                agents_dispatched=("fd-safety",),
                findings=(
                    Finding(
                        title="Validation lacks injection guard",
                        severity="P1",
                        body="injection surface concern",
                        themes=("input validation introduces new attack surface for injection",),
                        agent="fd-safety",
                    ),
                ),
                cost_usd=0.20,
            ),
            "d02-fixture-perf": FakeBackendScript(
                agents_dispatched=(),
                findings=(),
                cost_usd=0.05,
            ),
        }
    )
    out = tmp_path / "results.jsonl"
    aggregate = run_corpus(
        corpus_dir=corpus,
        backend=backend,
        baseline_sha="deadbeef",
        output_path=out,
        repo_root=tmp_path,
    )
    metrics = compute_corpus_metrics(
        corpus_dir=corpus,
        results=aggregate.results,
        backend_name=backend.name,
    )
    # diff 1 covers 1/2 themes; diff 2 covers 0/1 themes — average 0.25.
    assert metrics.review_coverage_per_diff == pytest.approx(0.25)
    # agent selection — diff 1: precision 1.0, recall 0.5, f1 ~0.667; diff 2: 0.
    assert metrics.agent_selection_macro_precision == pytest.approx(0.5)
    assert metrics.agent_selection_macro_recall == pytest.approx(0.25)
    # cost_per_finding — total $0.25 / 1 finding = 0.25.
    assert metrics.cost_per_finding_usd == pytest.approx(0.25)
