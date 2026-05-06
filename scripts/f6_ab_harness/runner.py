"""Corpus runner — drives one backend over the F6 A/B corpus and emits results JSONL.

Usage::

    from scripts.f6_ab_harness import run_corpus
    from scripts.f6_ab_harness.backends import FakeBackend

    result = run_corpus(
        corpus_dir=Path("docs/research/f6-ab-corpus"),
        backend=FakeBackend(script={...}),
        baseline_sha="f72d3cfd...",
        output_path=Path("/tmp/legacy-results.jsonl"),
    )

The runner reads ``manifest.jsonl``, materialises each diff (preferring
``diffs/<id>.diff`` when present, otherwise ``git show <sha>``), invokes the
backend, and records one JSONL row per diff.

The runner is intentionally simple: no parallelism, no retry, no caching. F6b
adds those concerns if the A/B execution time becomes a constraint; for the
30-diff corpus a serial run is well under an hour even with real backends.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .backends.base import Backend, BackendResult


@dataclass(frozen=True)
class CorpusEntry:
    """One row of ``manifest.jsonl``."""

    diff_id: str
    sha: str
    summary: str
    label_path: str
    diff_snapshot_path: str | None = None


@dataclass
class RunnerResult:
    """Aggregate result of one corpus run with one backend."""

    backend_name: str
    baseline_sha: str
    corpus_dir: str
    results: list[BackendResult] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    """List of (diff_id, reason) for diffs that could not be materialised."""

    total_wall_time_sec: float = 0.0
    total_cost_usd: float = 0.0


def _read_manifest(corpus_dir: Path) -> Iterable[CorpusEntry]:
    manifest = corpus_dir / "manifest.jsonl"
    if not manifest.exists():
        raise FileNotFoundError(
            f"Corpus manifest not found at {manifest}. F6a ships the manifest skeleton; "
            "did the corpus directory get truncated?"
        )
    with manifest.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            yield CorpusEntry(
                diff_id=row["diff_id"],
                sha=row["sha"],
                summary=row.get("summary", ""),
                label_path=row["label_path"],
                diff_snapshot_path=row.get("diff_snapshot_path"),
            )


def _materialise_diff(entry: CorpusEntry, corpus_dir: Path, repo_root: Path) -> str | None:
    """Return the unified-diff text for ``entry`` or None if it cannot be produced."""
    if entry.diff_snapshot_path:
        snapshot = corpus_dir / entry.diff_snapshot_path
        if snapshot.exists():
            return snapshot.read_text(encoding="utf-8")
    try:
        proc = subprocess.run(
            ["git", "show", "--no-color", entry.sha],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    # Some diffs include binary blobs (e.g., GGUF docs, embedded images) that are
    # not valid UTF-8. Decode with replacement so the harness stays robust on the
    # full corpus; backends that need byte-accurate input can re-fetch via the SHA.
    return proc.stdout.decode("utf-8", errors="replace")


def _serialise_result(result: BackendResult) -> dict:
    return {
        "diff_id": result.diff_id,
        "backend_name": result.backend_name,
        "agents_dispatched": list(result.agents_dispatched),
        "findings": [
            {
                "title": f.title,
                "severity": f.severity,
                "body": f.body,
                "themes": list(f.themes),
                "agent": f.agent,
            }
            for f in result.findings
        ],
        "cost_usd": result.cost_usd,
        "wall_time_sec": result.wall_time_sec,
        "backend_metadata": dict(result.backend_metadata),
    }


def run_corpus(
    *,
    corpus_dir: Path,
    backend: Backend,
    baseline_sha: str,
    output_path: Path,
    repo_root: Path | None = None,
) -> RunnerResult:
    """Drive ``backend`` over every diff in ``corpus_dir`` and write JSONL to ``output_path``.

    Args:
        corpus_dir: Path to ``docs/research/f6-ab-corpus``.
        backend: Implementation of :class:`Backend`.
        baseline_sha: Frozen-baseline SHA from the pre-registration doc; passed to each
            backend invocation so backends that depend on baseline state stay reproducible.
        output_path: Where to write per-diff result JSONL.
        repo_root: Git repo root used for ``git show`` materialisation. Defaults to the
            ``corpus_dir``'s nearest git ancestor.

    Returns:
        :class:`RunnerResult` summarising the run. Caller is responsible for downstream
        metric computation via :func:`metrics.compute_corpus_metrics`.
    """
    repo_root = repo_root or _find_git_root(corpus_dir)
    aggregate = RunnerResult(
        backend_name=backend.name,
        baseline_sha=baseline_sha,
        corpus_dir=str(corpus_dir),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for entry in _read_manifest(corpus_dir):
            diff_text = _materialise_diff(entry, corpus_dir, repo_root)
            if diff_text is None:
                aggregate.skipped.append((entry.diff_id, "diff materialisation failed"))
                continue
            t0 = time.perf_counter()
            try:
                result = backend.triage(
                    diff_id=entry.diff_id,
                    diff_text=diff_text,
                    baseline_sha=baseline_sha,
                )
            except NotImplementedError as exc:
                aggregate.skipped.append((entry.diff_id, f"backend stub: {exc}"))
                continue
            elapsed = time.perf_counter() - t0
            if result.wall_time_sec == 0.0:
                result = _with_wall_time(result, elapsed)
            aggregate.results.append(result)
            aggregate.total_wall_time_sec += result.wall_time_sec
            aggregate.total_cost_usd += result.cost_usd
            out.write(json.dumps(_serialise_result(result)) + "\n")
    return aggregate


def _with_wall_time(result: BackendResult, elapsed: float) -> BackendResult:
    """Backends that don't self-time get the runner's wall clock substituted in."""
    return BackendResult(
        diff_id=result.diff_id,
        backend_name=result.backend_name,
        agents_dispatched=result.agents_dispatched,
        findings=result.findings,
        cost_usd=result.cost_usd,
        wall_time_sec=elapsed,
        backend_metadata=result.backend_metadata,
    )


def _find_git_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"No git root found above {start}")
