"""Legacy backend — wraps the current flux-drive triage.

F6a ship-state: stub raising ``NotImplementedError``. F6b (sylveste-g939) lands
the real wrapper. The wrapper invokes flux-drive's deterministic triage (Steps
1.0–1.3 of ``interverse/interflux/skills/flux-drive/SKILL.md``) and synthesises
the BackendResult from the agent dispatch table + per-agent finding files.

The split exists so the F6a corpus + harness contract land *before* the
ontology backend exists. The bead dependency ``g939 → 2n8i`` enforces ordering;
this stub is the mechanical reminder that F6b owes a real implementation.
"""

from __future__ import annotations

from .base import Backend, BackendResult


class LegacyBackend(Backend):
    """Wraps current flux-drive triage. F6b will replace the body."""

    name = "legacy"

    def triage(self, *, diff_id: str, diff_text: str, baseline_sha: str) -> BackendResult:
        raise NotImplementedError(
            "F6a ships only the harness contract — sylveste-g939 (F6b) lands the real "
            "legacy wrapper. Until then use FakeBackend in tests."
        )
