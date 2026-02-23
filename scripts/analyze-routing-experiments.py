#!/usr/bin/env python3
"""Analyze heterogeneous routing experiment data from interstat + shadow logs.

Queries interstat metrics.db for per-agent token costs across flux-drive reviews,
parses B2-shadow routing logs, and generates comparison tables.

Usage:
    # Analyze all flux-drive reviews in interstat
    python3 scripts/analyze-routing-experiments.py

    # Analyze with shadow log directory
    python3 scripts/analyze-routing-experiments.py --shadow-dir /tmp/routing-shadow/

    # Output as markdown (for docs/research/heterogeneous-routing-results.md)
    python3 scripts/analyze-routing-experiments.py --format markdown

    # Filter to specific sessions
    python3 scripts/analyze-routing-experiments.py --session-filter "2026-02-23"
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_DB = Path.home() / ".claude" / "interstat" / "metrics.db"

# Agent role mappings from agent-roles.yaml
AGENT_ROLES = {
    "fd-architecture": ("planner", "opus"),
    "fd-systems": ("planner", "opus"),
    "fd-correctness": ("reviewer", "sonnet"),
    "fd-quality": ("reviewer", "sonnet"),
    "fd-safety": ("reviewer", "sonnet"),
    "fd-performance": ("editor", "sonnet"),
    "fd-user-product": ("editor", "sonnet"),
    "fd-game-design": ("editor", "sonnet"),
    "fd-perception": ("checker", "haiku"),
    "fd-resilience": ("checker", "haiku"),
    "fd-decisions": ("checker", "haiku"),
    "fd-people": ("checker", "haiku"),
}

# Model cost per million tokens (approximate, for relative comparison)
MODEL_COSTS = {
    "opus": {"input": 15.0, "output": 75.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "haiku": {"input": 0.80, "output": 4.0},
}

# Map actual model IDs to tiers
MODEL_TIER_MAP = {
    "claude-opus-4-6": "opus",
    "claude-opus-4-5-20251101": "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-sonnet-4-5-20250929": "sonnet",
    "claude-haiku-4-5-20251001": "haiku",
}

SHADOW_PATTERN = re.compile(
    r"\[B2-shadow\] complexity=(C\d) would change model: (\w+) → (\w+)"
)


def connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def query_flux_drive_reviews(conn: sqlite3.Connection, session_filter: str | None = None) -> list[dict]:
    """Get all flux-drive review agent runs grouped by session."""
    where_clause = ""
    params: list = []

    if session_filter:
        where_clause = "AND timestamp LIKE ?"
        params.append(f"{session_filter}%")

    rows = conn.execute(f"""
        SELECT
            session_id,
            COALESCE(subagent_type, agent_name) as agent,
            model,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            total_tokens,
            wall_clock_ms,
            timestamp
        FROM agent_runs
        WHERE (
            COALESCE(subagent_type, agent_name) LIKE '%interflux%'
            OR COALESCE(subagent_type, agent_name) LIKE '%fd-%'
            OR COALESCE(subagent_type, agent_name) LIKE '%intersynth%'
        )
        AND total_tokens IS NOT NULL
        {where_clause}
        ORDER BY session_id, timestamp
    """, params).fetchall()

    return [dict(r) for r in rows]


def normalize_agent_name(agent: str) -> str:
    """Extract the fd-* agent name from various formats."""
    for prefix in ("interflux:review:", "interflux:"):
        if agent.startswith(prefix):
            return agent[len(prefix):]
    return agent


def compute_model_tier(model_id: str | None) -> str:
    if not model_id:
        return "unknown"
    return MODEL_TIER_MAP.get(model_id, "unknown")


def estimate_cost(input_tokens: int, output_tokens: int, tier: str) -> float:
    """Estimate cost in dollars for a given token count and model tier."""
    costs = MODEL_COSTS.get(tier)
    if not costs:
        return 0.0
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000


def parse_shadow_logs(shadow_dir: Path) -> dict[str, list[dict]]:
    """Parse B2-shadow routing logs from stderr captures."""
    results: dict[str, list[dict]] = {}
    if not shadow_dir.exists():
        return results

    for log_file in shadow_dir.glob("routing-shadow-*.log"):
        repo_name = log_file.stem.replace("routing-shadow-", "")
        entries = []
        for line in log_file.read_text().splitlines():
            m = SHADOW_PATTERN.search(line)
            if m:
                entries.append({
                    "complexity": m.group(1),
                    "base_model": m.group(2),
                    "projected_model": m.group(3),
                })
        results[repo_name] = entries

    return results


def group_by_session(runs: list[dict]) -> dict[str, list[dict]]:
    """Group runs by session_id."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        groups[run["session_id"]].append(run)
    return dict(groups)


def analyze_session(session_id: str, runs: list[dict]) -> dict:
    """Analyze a single review session."""
    agents = []
    total_input = 0
    total_output = 0
    total_tokens = 0
    actual_cost = 0.0
    projected_cost = 0.0

    for run in runs:
        agent = normalize_agent_name(run["agent"])
        tier = compute_model_tier(run["model"])
        inp = run["input_tokens"] or 0
        out = run["output_tokens"] or 0
        tok = run["total_tokens"] or 0

        cost = estimate_cost(inp, out, tier)

        # Compute projected cost under role-aware routing
        role_info = AGENT_ROLES.get(agent)
        if role_info:
            projected_tier = role_info[1]
            proj_cost = estimate_cost(inp, out, projected_tier)
        else:
            projected_tier = tier
            proj_cost = cost

        agents.append({
            "agent": agent,
            "model_tier": tier,
            "projected_tier": projected_tier,
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": tok,
            "actual_cost": cost,
            "projected_cost": proj_cost,
            "wall_ms": run.get("wall_clock_ms") or 0,
        })

        total_input += inp
        total_output += out
        total_tokens += tok
        actual_cost += cost
        projected_cost += proj_cost

    savings = actual_cost - projected_cost if actual_cost > 0 else 0
    savings_pct = (savings / actual_cost * 100) if actual_cost > 0 else 0

    return {
        "session_id": session_id,
        "agent_count": len(agents),
        "agents": agents,
        "total_input": total_input,
        "total_output": total_output,
        "total_tokens": total_tokens,
        "actual_cost": actual_cost,
        "projected_cost": projected_cost,
        "savings": savings,
        "savings_pct": savings_pct,
    }


def format_table(fmt: str, headers: list[str], rows: list[list[str]]) -> str:
    """Format a table in markdown or plain text."""
    if fmt == "markdown":
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)
    else:
        col_widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
        lines = ["  ".join(h.ljust(w) for h, w in zip(headers, col_widths))]
        lines.append("  ".join("-" * w for w in col_widths))
        for row in rows:
            lines.append("  ".join(r.ljust(w) for r, w in zip(row, col_widths)))
        return "\n".join(lines)


def generate_report(sessions: list[dict], shadow_data: dict, fmt: str) -> str:
    """Generate the full analysis report."""
    lines = []

    if fmt == "markdown":
        lines.append("# Heterogeneous Routing Experiment Results\n")
        lines.append(f"**Date:** {__import__('datetime').date.today()}")
        lines.append(f"**Sessions analyzed:** {len(sessions)}\n")

    # Summary table
    lines.append("\n## Session Summary\n" if fmt == "markdown" else "\n=== Session Summary ===\n")
    headers = ["Session", "Agents", "Total Tokens", "B1 Cost", "B2 Projected", "Savings", "Savings %"]
    rows = []
    total_actual = 0.0
    total_projected = 0.0

    for s in sessions:
        rows.append([
            s["session_id"][:12] + "...",
            str(s["agent_count"]),
            f"{s['total_tokens']:,}",
            f"${s['actual_cost']:.4f}",
            f"${s['projected_cost']:.4f}",
            f"${s['savings']:.4f}",
            f"{s['savings_pct']:.1f}%",
        ])
        total_actual += s["actual_cost"]
        total_projected += s["projected_cost"]

    lines.append(format_table(fmt, headers, rows))

    total_savings = total_actual - total_projected
    total_pct = (total_savings / total_actual * 100) if total_actual > 0 else 0
    lines.append(f"\n**Totals:** B1=${total_actual:.4f}, B2=${total_projected:.4f}, "
                 f"Savings=${total_savings:.4f} ({total_pct:.1f}%)\n")

    # Per-agent analysis
    lines.append("\n## Per-Agent Model Tier Analysis\n" if fmt == "markdown" else "\n=== Per-Agent Tiers ===\n")

    agent_stats: dict[str, dict] = defaultdict(lambda: {
        "runs": 0, "actual_tiers": defaultdict(int), "projected_tier": "",
        "total_actual_cost": 0.0, "total_projected_cost": 0.0,
    })

    for s in sessions:
        for a in s["agents"]:
            agent = a["agent"]
            stats = agent_stats[agent]
            stats["runs"] += 1
            stats["actual_tiers"][a["model_tier"]] += 1
            stats["projected_tier"] = a["projected_tier"]
            stats["total_actual_cost"] += a["actual_cost"]
            stats["total_projected_cost"] += a["projected_cost"]

    headers = ["Agent", "Role", "Runs", "Current Tier(s)", "Projected", "Savings %"]
    rows = []
    for agent in sorted(agent_stats):
        stats = agent_stats[agent]
        role = AGENT_ROLES.get(agent, ("—", "—"))[0]
        tiers = ", ".join(f"{t}({n})" for t, n in sorted(stats["actual_tiers"].items(), key=lambda x: -x[1]))
        actual_total = stats["total_actual_cost"]
        projected_total = stats["total_projected_cost"]
        save_pct = ((actual_total - projected_total) / actual_total * 100) if actual_total > 0 else 0
        rows.append([agent, role, str(stats["runs"]), tiers, stats["projected_tier"], f"{save_pct:.1f}%"])

    lines.append(format_table(fmt, headers, rows))

    # Shadow data analysis (if available)
    if shadow_data:
        lines.append("\n## Shadow Routing Divergence\n" if fmt == "markdown" else "\n=== Shadow Data ===\n")
        headers = ["Repo", "Shadow Entries", "Downgrades", "Upgrades"]
        rows = []
        for repo, entries in sorted(shadow_data.items()):
            downgrades = sum(1 for e in entries if _tier_rank(e["projected_model"]) < _tier_rank(e["base_model"]))
            upgrades = sum(1 for e in entries if _tier_rank(e["projected_model"]) > _tier_rank(e["base_model"]))
            rows.append([repo, str(len(entries)), str(downgrades), str(upgrades)])
        lines.append(format_table(fmt, headers, rows))

    # Recommendations
    lines.append("\n## Routing Recommendations\n" if fmt == "markdown" else "\n=== Recommendations ===\n")
    if total_pct > 5:
        lines.append(f"- B2 role-aware routing projects **{total_pct:.1f}% cost savings** across {len(sessions)} reviews.")
        lines.append("- Recommend switching `complexity.mode: shadow` → `enforce` for trial.")
    else:
        lines.append(f"- B2 role-aware routing projects only **{total_pct:.1f}% savings** — minimal benefit.")
        lines.append("- Recommend keeping `complexity.mode: shadow` for continued data collection.")

    checker_agents = [a for a in agent_stats if AGENT_ROLES.get(a, ("", ""))[0] == "checker"]
    if checker_agents:
        lines.append(f"- Checker agents ({', '.join(checker_agents)}) are candidates for Haiku downgrade.")
        lines.append("  - **Safety gate:** Verify unique finding rate < 5% before enabling.")

    return "\n".join(lines)


def _tier_rank(tier: str) -> int:
    return {"haiku": 1, "sonnet": 2, "opus": 3}.get(tier, 0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Analyze routing experiment data")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="interstat database path")
    parser.add_argument("--shadow-dir", type=Path, help="directory of B2-shadow log files")
    parser.add_argument("--session-filter", help="filter sessions by date prefix (e.g., 2026-02-23)")
    parser.add_argument("--format", choices=["plain", "markdown"], default="plain", help="output format")
    parser.add_argument("--output", type=Path, help="write output to file instead of stdout")
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"Error: interstat database not found at {args.db}", file=sys.stderr)
        return 1

    conn = connect_db(args.db)
    try:
        runs = query_flux_drive_reviews(conn, args.session_filter)
    finally:
        conn.close()

    if not runs:
        print("No flux-drive review data found in interstat.", file=sys.stderr)
        return 1

    grouped = group_by_session(runs)
    sessions = [analyze_session(sid, runs) for sid, runs in grouped.items()]

    # Parse shadow logs if available
    shadow_data: dict[str, list[dict]] = {}
    if args.shadow_dir:
        shadow_data = parse_shadow_logs(args.shadow_dir)

    report = generate_report(sessions, shadow_data, args.format)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
