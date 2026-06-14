"""Bridge to the calibration-eval metrics (DESIGN.md §6 reuse bridge).

The flagship scores the *internal* probe signal on the **exact same type-2 SDT footing**
as the behavioral eval — type-2 AUROC, meta-d', M-ratio — so internal vs verbalized vs
logprob discriminators are directly comparable (Probe B). Rather than re-implement or
pip-install the sibling experiment (whose wheel package is the generic name ``src``, which
would collide with this experiment's own ``src``), we load its ``metrics.py`` by path.

This keeps the metric definitions in exactly one place: any fix to meta-d' over there is
inherited here for free, and there is no second copy to drift.
"""

from __future__ import annotations

import importlib.util
import pathlib

_METRICS_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "calibration-eval" / "src" / "metrics.py"
)

if not _METRICS_PATH.exists():  # pragma: no cover - defensive, sibling-dir contract
    raise ImportError(
        f"calibration-eval metrics not found at {_METRICS_PATH}. The introspection probe "
        "reuses them and expects the sibling experiment to be present in the monorepo."
    )

_spec = importlib.util.spec_from_file_location("calibration_eval_metrics", _METRICS_PATH)
assert _spec and _spec.loader  # for type-checkers
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export the type-2 panel used by the probe. ``scale`` arg is 100.0 for 0-100 verbalized
# confidence and 1.0 for probabilities (the probe emits P(correct) in [0, 1]).
auroc = _mod.auroc
meta_d_prime = _mod.meta_d_prime
m_ratio = _mod.m_ratio
d_prime = _mod.d_prime
summarize = _mod.summarize

__all__ = ["auroc", "meta_d_prime", "m_ratio", "d_prime", "summarize"]
