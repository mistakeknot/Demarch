"""Ontology backend — wraps lattice-template-based triage.

F6a ship-state: stub raising ``NotImplementedError``. F6b (sylveste-g939) lands
the real wrapper. The wrapper invokes lattice's named templates (e.g.,
``select_personae_for_task``) to choose review agents instead of flux-drive's
score table, then dispatches those agents and synthesises a BackendResult that
matches the legacy contract.

Per the PRD lattice errata (2026-04-27), the new triage targets
``interverse/lattice/`` named templates — not a separate ``ontology-queries``
package. F6a does not constrain how F6b implements the lookup; only that the
backend conforms to :class:`~scripts.f6_ab_harness.backends.base.Backend`.
"""

from __future__ import annotations

from .base import Backend, BackendResult


class OntologyBackend(Backend):
    """Wraps lattice-template triage. F6b will replace the body."""

    name = "ontology"

    def triage(self, *, diff_id: str, diff_text: str, baseline_sha: str) -> BackendResult:
        raise NotImplementedError(
            "F6a ships only the harness contract — sylveste-g939 (F6b) lands the real "
            "ontology wrapper. Until then use FakeBackend in tests."
        )
