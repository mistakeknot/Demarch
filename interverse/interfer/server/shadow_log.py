"""Shadow cost logging for interstat.

Logs counterfactual routing decisions from the confidence cascade to
interstat's local_routing_shadow table. This data feeds sprint cost
summaries showing how much cloud spend was avoided by local routing.

The logger writes directly to SQLite (not via hooks) since it runs
inside the interfer server process, not a Claude Code session.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("interfer.shadow_log")

# Default cloud model used for cost estimation when no specific model is known
DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"

# Fallback pricing (USD per million tokens) — used when costs.yaml is unavailable
_FALLBACK_PRICING: dict[str, tuple[float, float]] = {
    # (input_per_mtok, output_per_mtok)
    "haiku": (0.80, 4.00),
    "sonnet": (3.00, 15.00),
    "opus": (15.00, 75.00),
}

# Pattern to extract parameter count from model names like "Qwen3.5-9B-4bit"
_PARAM_PATTERN = re.compile(r"(\d+)[bB]", re.IGNORECASE)


def _load_pricing() -> dict[str, tuple[float, float]]:
    """Load pricing from costs.yaml, falling back to hardcoded defaults.

    Searches for costs.yaml relative to this file's location in the
    Sylveste monorepo, matching the search pattern in cost-query.sh.
    """
    search_paths = [
        Path(__file__).resolve().parent.parent.parent.parent
        / "core"
        / "intercore"
        / "config"
        / "costs.yaml",
    ]

    # Also check COSTS_YAML env var
    env_path = os.environ.get("COSTS_YAML")
    if env_path:
        search_paths.insert(0, Path(env_path))

    for path in search_paths:
        if path.is_file():
            try:
                return _parse_costs_yaml(path)
            except Exception:
                log.debug("shadow_log: failed to parse %s, using fallback", path)

    return _FALLBACK_PRICING.copy()


def _parse_costs_yaml(path: Path) -> dict[str, tuple[float, float]]:
    """Parse costs.yaml without requiring PyYAML (simple key-value extraction)."""
    text = path.read_text()
    pricing: dict[str, tuple[float, float]] = {}

    current_model: str | None = None
    input_rate: float | None = None
    output_rate: float | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        # Detect model sections: "  haiku:", "  sonnet:", "  opus:"
        if (
            stripped.endswith(":")
            and not stripped.startswith("input")
            and not stripped.startswith("output")
        ):
            candidate = stripped.rstrip(":").strip()
            if candidate in ("haiku", "sonnet", "opus", "models"):
                if candidate != "models":
                    # Save previous model if complete
                    if (
                        current_model
                        and input_rate is not None
                        and output_rate is not None
                    ):
                        pricing[current_model] = (input_rate, output_rate)
                    current_model = candidate
                    input_rate = None
                    output_rate = None
                continue

        # Parse rate values: "input_per_mtok: 3.00"
        if "input_per_mtok" in stripped and current_model:
            try:
                input_rate = float(stripped.split(":")[-1].strip())
            except ValueError:
                pass
        elif "output_per_mtok" in stripped and current_model:
            try:
                output_rate = float(stripped.split(":")[-1].strip())
            except ValueError:
                pass

    # Save last model
    if current_model and input_rate is not None and output_rate is not None:
        pricing[current_model] = (input_rate, output_rate)

    if not pricing:
        raise ValueError("no pricing data found")

    return pricing


# Module-level pricing (loaded once on import)
_PRICING = _load_pricing()


def infer_cloud_model(local_model: str) -> str:
    """Infer which cloud model tier would handle this request.

    Maps local model size to cloud equivalent:
    - < 15B params → haiku (simple tasks)
    - 15-100B params → sonnet (medium tasks)
    - > 100B params → opus (complex tasks)

    Falls back to sonnet if model size can't be determined.
    """
    match = _PARAM_PATTERN.search(local_model)
    if not match:
        return DEFAULT_CLOUD_MODEL

    param_billions = int(match.group(1))

    if param_billions < 15:
        return "claude-haiku-4-5"
    if param_billions <= 100:
        return "claude-sonnet-4-6"
    return "claude-opus-4-7"


def _cloud_cost_usd(model: str, tokens: int) -> float:
    """Estimate cloud cost for a given model and token count.

    Uses output pricing (conservative estimate since we're estimating
    what the cloud model would have generated).
    """
    key = "sonnet"  # default
    model_lower = model.lower()
    for tier in ("haiku", "sonnet", "opus"):
        if tier in model_lower:
            key = tier
            break
    _, output_rate = _PRICING.get(key, _FALLBACK_PRICING["sonnet"])
    return round(tokens * output_rate / 1_000_000, 6)


@dataclass
class ShadowEntry:
    """A single cascade routing decision to log."""

    cascade_decision: str  # "accept", "escalate", "cloud"
    confidence: float
    local_model: str
    local_tokens: int
    cloud_model: str = ""  # auto-inferred if empty
    cloud_tokens_est: int = 0
    probe_time_s: float = 0.0
    models_tried: str = ""
    escalation_count: int = 0
    session_id: str = ""
    bead_id: str = ""


class ShadowLogger:
    """Writes cascade routing decisions to interstat's SQLite DB."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or os.path.join(
            os.path.expanduser("~"), ".claude", "interstat", "metrics.db"
        )
        self._conn: sqlite3.Connection | None = None

    def _ensure_db(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        try:
            self._conn = sqlite3.connect(self._db_path, timeout=5.0)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
        except Exception:
            log.warning("shadow_log: cannot connect to %s", self._db_path)
            raise
        return self._conn

    def log(self, entry: ShadowEntry) -> None:
        """Log a shadow routing entry. Fails silently on DB errors."""
        try:
            conn = self._ensure_db()
        except Exception:
            return  # DB not available — degrade gracefully

        # Auto-infer cloud model from local model if not specified
        cloud_model = entry.cloud_model or infer_cloud_model(entry.local_model)

        # Estimate cloud tokens as same as local (conservative)
        cloud_tokens = entry.cloud_tokens_est or entry.local_tokens
        cloud_cost = _cloud_cost_usd(cloud_model, cloud_tokens)
        local_cost = 0.0  # local inference has no API cost
        savings = cloud_cost - local_cost

        try:
            conn.execute(
                """INSERT INTO local_routing_shadow (
                    timestamp, session_id, bead_id,
                    cascade_decision, confidence,
                    local_model, local_tokens,
                    cloud_model, cloud_tokens_est,
                    local_cost_usd, cloud_cost_usd, hypothetical_savings_usd,
                    probe_time_s, models_tried, escalation_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    entry.session_id,
                    entry.bead_id,
                    entry.cascade_decision,
                    entry.confidence,
                    entry.local_model,
                    entry.local_tokens,
                    cloud_model,
                    cloud_tokens,
                    local_cost,
                    cloud_cost,
                    savings,
                    entry.probe_time_s,
                    entry.models_tried,
                    entry.escalation_count,
                ),
            )
            conn.commit()
        except Exception as exc:
            log.warning("shadow_log: INSERT failed: %s", exc)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
