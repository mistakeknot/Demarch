"""Tests for shadow cost logging."""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from server.shadow_log import (
    ShadowEntry,
    ShadowLogger,
    _cloud_cost_usd,
    _parse_costs_yaml,
    infer_cloud_model,
)


@pytest.fixture
def shadow_db():
    """Create a temp SQLite DB with the local_routing_shadow schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE local_routing_shadow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL DEFAULT '',
            bead_id TEXT NOT NULL DEFAULT '',
            cascade_decision TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.0,
            local_model TEXT NOT NULL,
            local_tokens INTEGER NOT NULL DEFAULT 0,
            cloud_model TEXT NOT NULL DEFAULT '',
            cloud_tokens_est INTEGER NOT NULL DEFAULT 0,
            local_cost_usd REAL NOT NULL DEFAULT 0.0,
            cloud_cost_usd REAL NOT NULL DEFAULT 0.0,
            hypothetical_savings_usd REAL NOT NULL DEFAULT 0.0,
            probe_time_s REAL NOT NULL DEFAULT 0.0,
            models_tried TEXT NOT NULL DEFAULT '',
            escalation_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


def test_cloud_cost_usd_sonnet() -> None:
    """Sonnet pricing: $15/Mtok output."""
    cost = _cloud_cost_usd("claude-sonnet-4-6", 1000)
    assert cost == pytest.approx(0.015, abs=0.001)


def test_cloud_cost_usd_opus() -> None:
    """Opus pricing: $75/Mtok output."""
    cost = _cloud_cost_usd("claude-opus-4-6", 1000)
    assert cost == pytest.approx(0.075, abs=0.001)


def test_cloud_cost_usd_haiku() -> None:
    """Haiku pricing: $4/Mtok output."""
    cost = _cloud_cost_usd("claude-haiku-4-5", 1000)
    assert cost == pytest.approx(0.004, abs=0.001)


def test_shadow_logger_writes_entry(shadow_db: str) -> None:
    """Logger writes a row to local_routing_shadow."""
    logger = ShadowLogger(db_path=shadow_db)
    logger.log(
        ShadowEntry(
            cascade_decision="accept",
            confidence=0.85,
            local_model="qwen3.5-9b-4bit",
            local_tokens=512,
            cloud_tokens_est=512,
            probe_time_s=0.05,
            models_tried="qwen3.5-9b-4bit",
            escalation_count=0,
        )
    )
    logger.close()

    conn = sqlite3.connect(shadow_db)
    rows = conn.execute("SELECT * FROM local_routing_shadow").fetchall()
    conn.close()

    assert len(rows) == 1
    # Column order: id, timestamp, session_id, bead_id, cascade_decision, confidence, ...
    row = rows[0]
    assert row[4] == "accept"  # cascade_decision
    assert row[5] == 0.85  # confidence
    assert row[6] == "qwen3.5-9b-4bit"  # local_model
    assert row[7] == 512  # local_tokens
    assert row[12] > 0  # hypothetical_savings_usd


def test_shadow_logger_cloud_fallback_zero_savings(shadow_db: str) -> None:
    """Cloud fallback has zero local tokens and zero savings."""
    logger = ShadowLogger(db_path=shadow_db)
    logger.log(
        ShadowEntry(
            cascade_decision="cloud",
            confidence=0.2,
            local_model="qwen3.5-9b-4bit",
            local_tokens=0,
            cloud_tokens_est=512,
            probe_time_s=0.03,
            models_tried="qwen3.5-9b-4bit",
            escalation_count=0,
        )
    )
    logger.close()

    conn = sqlite3.connect(shadow_db)
    row = conn.execute(
        "SELECT local_tokens, local_cost_usd, cloud_cost_usd, hypothetical_savings_usd FROM local_routing_shadow"
    ).fetchone()
    conn.close()

    assert row[0] == 0  # local_tokens
    assert row[1] == 0.0  # local_cost_usd
    assert row[2] > 0  # cloud_cost_usd
    assert row[3] > 0  # hypothetical_savings_usd (cloud cost - 0)


def test_shadow_logger_graceful_on_missing_db() -> None:
    """Logger degrades gracefully when DB doesn't exist."""
    logger = ShadowLogger(db_path="/tmp/nonexistent/shadow.db")
    # Should not raise
    logger.log(
        ShadowEntry(
            cascade_decision="accept",
            confidence=0.9,
            local_model="test",
            local_tokens=100,
        )
    )
    logger.close()


def test_shadow_logger_multiple_entries(shadow_db: str) -> None:
    """Multiple log entries accumulate correctly."""
    logger = ShadowLogger(db_path=shadow_db)
    for i in range(5):
        logger.log(
            ShadowEntry(
                cascade_decision="accept",
                confidence=0.8 + i * 0.01,
                local_model=f"model-{i}",
                local_tokens=100 * (i + 1),
            )
        )
    logger.close()

    conn = sqlite3.connect(shadow_db)
    count = conn.execute("SELECT COUNT(*) FROM local_routing_shadow").fetchone()[0]
    conn.close()

    assert count == 5


# ---------------------------------------------------------------------------
# Model tier inference
# ---------------------------------------------------------------------------


def test_infer_cloud_model_small() -> None:
    """Small models (< 15B) map to haiku."""
    assert infer_cloud_model("Qwen3.5-9B-4bit") == "claude-haiku-4-5"
    assert (
        infer_cloud_model("mlx-community/Qwen2.5-0.5B-Instruct-4bit")
        == "claude-haiku-4-5"
    )


def test_infer_cloud_model_medium() -> None:
    """Medium models (15-100B) map to sonnet."""
    assert infer_cloud_model("Qwen3.5-35B-A3B-4bit") == "claude-sonnet-4-6"
    assert infer_cloud_model("some-model-70b-instruct") == "claude-sonnet-4-6"


def test_infer_cloud_model_large() -> None:
    """Large models (> 100B) map to opus."""
    assert infer_cloud_model("Qwen3.5-397B-A17B-4bit") == "claude-opus-4-7"


def test_infer_cloud_model_unknown() -> None:
    """Unknown model names default to sonnet."""
    assert infer_cloud_model("some-mystery-model") == "claude-sonnet-4-6"


def test_infer_cloud_model_case_insensitive() -> None:
    """Parameter extraction is case insensitive."""
    assert infer_cloud_model("model-9b-4bit") == "claude-haiku-4-5"
    assert infer_cloud_model("model-9B-4bit") == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# Costs.yaml parsing
# ---------------------------------------------------------------------------


def test_parse_costs_yaml(tmp_path) -> None:
    """Parse a costs.yaml file correctly."""
    costs_file = tmp_path / "costs.yaml"
    costs_file.write_text("""
models:
  haiku:
    input_per_mtok: 1.00
    output_per_mtok: 5.00
  sonnet:
    input_per_mtok: 4.00
    output_per_mtok: 20.00
  opus:
    input_per_mtok: 20.00
    output_per_mtok: 100.00
""")
    pricing = _parse_costs_yaml(costs_file)
    assert pricing["haiku"] == (1.00, 5.00)
    assert pricing["sonnet"] == (4.00, 20.00)
    assert pricing["opus"] == (20.00, 100.00)


# ---------------------------------------------------------------------------
# Auto-inferred cloud model in logger
# ---------------------------------------------------------------------------


def test_logger_auto_infers_cloud_model(shadow_db: str) -> None:
    """When cloud_model is empty, logger infers from local model size."""
    logger = ShadowLogger(db_path=shadow_db)
    logger.log(
        ShadowEntry(
            cascade_decision="accept",
            confidence=0.9,
            local_model="Qwen3.5-9B-4bit",
            local_tokens=256,
        )
    )
    logger.close()

    conn = sqlite3.connect(shadow_db)
    row = conn.execute("SELECT cloud_model FROM local_routing_shadow").fetchone()
    conn.close()

    assert row[0] == "claude-haiku-4-5"


def test_logger_uses_explicit_cloud_model(shadow_db: str) -> None:
    """When cloud_model is set, logger uses it as-is."""
    logger = ShadowLogger(db_path=shadow_db)
    logger.log(
        ShadowEntry(
            cascade_decision="accept",
            confidence=0.9,
            local_model="Qwen3.5-9B-4bit",
            local_tokens=256,
            cloud_model="claude-opus-4-6",
        )
    )
    logger.close()

    conn = sqlite3.connect(shadow_db)
    row = conn.execute("SELECT cloud_model FROM local_routing_shadow").fetchone()
    conn.close()

    assert row[0] == "claude-opus-4-6"
