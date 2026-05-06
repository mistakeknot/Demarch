"""Backend implementations for the F6 A/B harness.

- ``base`` — Backend protocol + result dataclasses (frozen at F6a).
- ``legacy`` — wraps the current flux-drive triage. F6a ships a stub; F6b lands the real wrapper.
- ``ontology`` — wraps the lattice-template triage. F6a ships a stub; F6b lands the real wrapper.
- ``fake`` — deterministic in-memory backend used by the harness test suite.
"""

from .base import Backend, BackendResult, Finding
from .fake import FakeBackend
from .legacy import LegacyBackend
from .ontology import OntologyBackend

__all__ = [
    "Backend",
    "BackendResult",
    "FakeBackend",
    "Finding",
    "LegacyBackend",
    "OntologyBackend",
]
