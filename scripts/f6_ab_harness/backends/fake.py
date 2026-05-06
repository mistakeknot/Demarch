"""In-memory deterministic backend for harness tests.

Production code never imports FakeBackend. The harness ships with FakeBackend so
that:

1. The runner is exercised end-to-end at F6a, before either real backend exists.
2. F6b cannot accidentally remove a hot path — the test suite breaks if the
   contract changes shape.

Construct with a dict keyed by diff_id whose values describe the result the
fake should return.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import Backend, BackendResult, Finding


@dataclass
class FakeBackendScript:
    """Pre-baked fake response for one diff."""

    agents_dispatched: tuple[str, ...]
    findings: tuple[Finding, ...]
    cost_usd: float = 0.0
    wall_time_sec: float = 0.0
    backend_metadata: dict[str, str] = field(default_factory=dict)


class FakeBackend(Backend):
    """Returns whatever the script says, or empties when no entry exists."""

    name = "fake"

    def __init__(self, script: dict[str, FakeBackendScript], *, name: str = "fake") -> None:
        self.name = name
        self._script = dict(script)

    def triage(self, *, diff_id: str, diff_text: str, baseline_sha: str) -> BackendResult:
        entry = self._script.get(
            diff_id,
            FakeBackendScript(agents_dispatched=(), findings=()),
        )
        return BackendResult(
            diff_id=diff_id,
            backend_name=self.name,
            agents_dispatched=entry.agents_dispatched,
            findings=entry.findings,
            cost_usd=entry.cost_usd,
            wall_time_sec=entry.wall_time_sec,
            backend_metadata=dict(entry.backend_metadata),
        )
