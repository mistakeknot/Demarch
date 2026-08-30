"""Introspection probe (Step 2 flagship): is stated confidence grounded or confabulated?

GPU-independent analysis core lives in ``probe.py`` and is unit-tested without nnsight or a
GPU. See ``../DESIGN.md`` for the full grounding-chain design and ``../PREREGISTRATION.md``
for the locked hypotheses and analysis plan.
"""

__all__ = ["probe"]
