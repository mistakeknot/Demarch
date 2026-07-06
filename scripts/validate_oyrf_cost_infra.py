#!/usr/bin/env python3
"""Validate sylveste-oyrf.1 longitudinal cost-calibration infra artifacts.

This is intentionally structural: it proves the public/repo CSV, scheduled
estimator, public live template, transition harness, and cadence plan are wired
well enough for automation and review without requiring private interstat data.
The public live template must stay launch-safe and no longer names held/private
Mythos terminology; the internal transition harness remains the Mythos-specific
measurement artifact.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSV_PATH = ROOT / "data" / "cost-trajectory.csv"
ESTIMATOR = ROOT / "estimate-costs.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "oyrf-cost-calibration.yml"
LIVE_TEMPLATE = ROOT / "docs" / "live" / "closed-loop.md"
MYTHOS_HARNESS = ROOT / "docs" / "specs" / "mythos-transition-harness.md"
CADENCE_PLAN = ROOT / "docs" / "plans" / "2026-04-30-session-cadence-dial-up-plan.md"
DRY_RUN = ROOT / "scripts" / "mythos-transition-dry-run.sh"

REQUIRED_CSV_COLUMNS = [
    "captured_at",
    "window_days",
    "session_count",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "total_cost_usd",
    "cost_per_session_usd",
    "source",
]


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def read_text(path: Path, failures: list[str]) -> str:
    if not path.exists():
        fail(f"missing required artifact: {path.relative_to(ROOT)}", failures)
        return ""
    if not path.is_file():
        fail(f"expected file, got non-file artifact: {path.relative_to(ROOT)}", failures)
        return ""
    return path.read_text(encoding="utf-8")


def validate_csv(failures: list[str]) -> None:
    text = read_text(CSV_PATH, failures)
    if not text:
        return
    rows = list(csv.DictReader(text.splitlines()))
    header = rows[0].keys() if rows else csv.reader(text.splitlines()).__next__()
    header = list(header)
    if header != REQUIRED_CSV_COLUMNS:
        fail(
            "cost trajectory CSV header mismatch: "
            f"expected {REQUIRED_CSV_COLUMNS}, got {header}",
            failures,
        )
    if not rows:
        fail("cost trajectory CSV must include at least one data row", failures)
        return
    for idx, row in enumerate(rows, start=2):
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", row.get("captured_at", "")):
            fail(f"CSV row {idx} captured_at must be UTC ISO-8601 Z", failures)
        for col in ["window_days", "session_count", "total_tokens", "input_tokens", "output_tokens"]:
            try:
                int(row.get(col, ""))
            except ValueError:
                fail(f"CSV row {idx} {col} must be an integer", failures)
        for col in ["total_cost_usd", "cost_per_session_usd"]:
            try:
                float(row.get(col, ""))
            except ValueError:
                fail(f"CSV row {idx} {col} must be numeric", failures)
        if row.get("source") not in {"interstat", "interstat-empty", "dry-run-fixture"}:
            fail(f"CSV row {idx} source must identify interstat provenance", failures)


def validate_public_git_visibility(failures: list[str]) -> None:
    """Ensure the public CSV can actually be committed/published from this repo."""
    rel = CSV_PATH.relative_to(ROOT).as_posix()
    ignore = subprocess.run(
        ["git", "check-ignore", "-q", "--", rel],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if ignore.returncode == 0:
        fail(f"{rel} is ignored; public cost trajectory CSV would not be published", failures)
    if tracked.returncode != 0:
        fail(f"{rel} is not tracked/staged; add it explicitly so scheduled publication can diff and commit it", failures)


def validate_estimator(failures: list[str], run_dry_run: bool) -> None:
    text = read_text(ESTIMATOR, failures)
    if not text:
        return
    if not os.access(ESTIMATOR, os.X_OK):
        fail("estimate-costs.sh must be executable", failures)
    for needle in ["interverse/interstat/scripts/cost-query.sh", "cost-trajectory.csv", "--dry-run"]:
        if needle not in text:
            fail(f"estimate-costs.sh must reference {needle!r}", failures)
    if "/tmp/oyrf-cost-query.err" in text:
        fail("estimate-costs.sh must not write Interstat stderr to predictable /tmp paths", failures)
    if run_dry_run and ESTIMATOR.exists():
        with tempfile.TemporaryDirectory(prefix="oyrf-cost-") as tmp:
            out_path = Path(tmp) / "cost-trajectory.csv"
            result = subprocess.run(
                [str(ESTIMATOR), "--dry-run", f"--output={out_path}"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                fail(
                    "estimate-costs.sh --dry-run failed:\n" + result.stdout[-2000:],
                    failures,
                )
            elif not out_path.exists():
                fail("estimate-costs.sh --dry-run did not write requested output CSV", failures)


def validate_nested_interstat_baseline_fixture(failures: list[str]) -> None:
    """Exercise live-mode parsing against Interstat baseline's nested JSON shape."""
    if not ESTIMATOR.exists():
        return

    with tempfile.TemporaryDirectory(prefix="oyrf-interstat-fixture-") as tmp:
        tmp_path = Path(tmp)
        out_path = tmp_path / "cost-trajectory.csv"
        fake_timeout = tmp_path / "timeout"
        fake_timeout.write_text(
            """#!/usr/bin/env bash
cat <<'JSON'
{
  "measurement_window": {
    "first_session": "2026-04-23T00:00:00Z",
    "last_session": "2026-04-30T00:00:00Z",
    "sessions": 3
  },
  "tokens": {
    "total": 12345,
    "input": 10000,
    "output": 2345
  },
  "cost_usd": 1.2345,
  "landed_changes": {
    "count": 2,
    "source": "fixture"
  },
  "north_star": {
    "tokens_per_landable_change": 6172,
    "usd_per_landable_change": 0.61725
  }
}
JSON
""",
            encoding="utf-8",
        )
        fake_timeout.chmod(0o700)

        # interverse/interstat/scripts/cost-query.sh is private tooling and
        # deliberately gitignored (see .gitignore: interverse/), so it never
        # exists on a fresh clone/CI checkout. estimate-costs.sh checks
        # `[ -x "$COST_QUERY" ]` before ever invoking `timeout`, so without a
        # stub here it always short-circuits to interstat-empty and the fake
        # `timeout` above is never reached. OYRF_COST_QUERY_OVERRIDE points
        # estimate-costs.sh at this stub instead of the real private path;
        # the stub itself is never executed (the fake `timeout` above
        # intercepts first) but must exist and be executable to pass the
        # `-x` check.
        fake_cost_query = tmp_path / "cost-query.sh"
        fake_cost_query.write_text(
            "#!/usr/bin/env bash\necho 'stub: intercepted by fake timeout' >&2\nexit 1\n",
            encoding="utf-8",
        )
        fake_cost_query.chmod(0o700)

        env = os.environ.copy()
        env["PATH"] = f"{tmp_path}:{env.get('PATH', '')}"
        env["OYRF_COST_QUERY_OVERRIDE"] = str(fake_cost_query)
        result = subprocess.run(
            [str(ESTIMATOR), f"--output={out_path}", "--since=2026-04-23T00:00:00Z"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            fail(
                "estimate-costs.sh nested Interstat baseline fixture failed:\n" + result.stdout[-2000:],
                failures,
            )
            return
        if not out_path.exists():
            fail("estimate-costs.sh nested Interstat baseline fixture did not write output CSV", failures)
            return

        rows = list(csv.DictReader(out_path.read_text(encoding="utf-8").splitlines()))
        if not rows:
            fail("estimate-costs.sh nested Interstat baseline fixture wrote no data rows", failures)
            return
        row = rows[-1]
        expected = {
            "session_count": "3",
            "total_tokens": "12345",
            "input_tokens": "10000",
            "output_tokens": "2345",
            "total_cost_usd": "1.234500",
            "cost_per_session_usd": "0.411500",
            "source": "interstat",
        }
        for column, value in expected.items():
            if row.get(column) != value:
                fail(
                    "estimate-costs.sh must parse nested Interstat baseline JSON: "
                    f"expected {column}={value!r}, got {row.get(column)!r}",
                    failures,
                )


def validate_workflow(failures: list[str]) -> None:
    text = read_text(WORKFLOW, failures)
    if not text:
        return
    required_patterns = [
        r"cron:\s*['\"]0 \*/6 \* \* \*['\"]",
        r"bash\s+estimate-costs\.sh",
        r"actions/checkout@v4",
        r"cost-trajectory\.csv",
        r"workflow_dispatch:",
    ]
    for pattern in required_patterns:
        if not re.search(pattern, text):
            fail(f"workflow missing required pattern: {pattern}", failures)


def validate_docs(failures: list[str]) -> None:
    live = read_text(LIVE_TEMPLATE, failures)
    if live:
        for needle in ["cost-trajectory.csv", "closed-loop", "sylveste-oyrf.1"]:
            if needle not in live:
                fail(f"closed-loop template must mention {needle!r}", failures)

    harness = read_text(MYTHOS_HARNESS, failures)
    if harness:
        for needle in ["scripts/mythos-transition-dry-run.sh", "before", "after", "identical workloads", "estimate-costs.sh --dry-run"]:
            if needle not in harness:
                fail(f"Mythos transition harness doc must mention {needle!r}", failures)

    cadence = read_text(CADENCE_PLAN, failures)
    if cadence:
        for needle in ["Week 1", "Week 2", "Week 3", "Week 4", "pre-Mythos", "session cadence"]:
            if needle not in cadence:
                fail(f"cadence plan must mention {needle!r}", failures)

    dry_run_text = read_text(DRY_RUN, failures)
    if dry_run_text:
        if not os.access(DRY_RUN, os.X_OK):
            fail("scripts/mythos-transition-dry-run.sh must be executable", failures)
        for needle in ["--before", "--after", "estimate-costs.sh", "dry-run"]:
            if needle not in dry_run_text:
                fail(f"Mythos dry-run script must mention {needle!r}", failures)


def validate(run_dry_run: bool = False) -> list[str]:
    failures: list[str] = []
    validate_csv(failures)
    validate_public_git_visibility(failures)
    validate_estimator(failures, run_dry_run=run_dry_run)
    validate_nested_interstat_baseline_fixture(failures)
    validate_workflow(failures)
    validate_docs(failures)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dry-run", action="store_true", help="also execute estimate-costs.sh --dry-run")
    args = parser.parse_args(argv)

    failures = validate(run_dry_run=args.run_dry_run)
    if failures:
        print("OYRF cost infra validation failed:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("OYRF cost infra validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
