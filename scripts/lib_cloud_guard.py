"""lib_cloud_guard — Python sibling of lib-cloud-guard.sh.

Used by Python scripts that invoke `bd` so they degrade the same way:
cleanly + read-only on cloud, loudly + actionably on workstation.

Usage:

    from lib_cloud_guard import cloud_session, cloud_log_skip, workstation_log_missing_bd
    import shutil, sys

    if cloud_session():
        cloud_log_skip("backfill-bead-labels")
        sys.exit(0)

    if shutil.which("bd") is None:
        workstation_log_missing_bd("backfill-bead-labels")
        sys.exit(0)

Detection mirrors the bash lib: env vars only, never `which bd`. See
lib-cloud-guard.sh for rationale.
"""
from __future__ import annotations

import os
import sys


def cloud_session() -> bool:
    """True iff the current process is in a Claude Code cloud_default session."""
    if os.environ.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE") == "cloud_default":
        return True
    if os.environ.get("IS_SANDBOX") == "yes":
        return True
    return False


def cloud_log_skip(op: str = "operation") -> None:
    """Stderr message: cloud read-only mode, skipping a bd-dependent op."""
    rem = os.environ.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE", "unset")
    sb = os.environ.get("IS_SANDBOX", "unset")
    print(
        f"{op}: cloud read-only mode "
        f"(CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE={rem}, IS_SANDBOX={sb}) "
        f"— skipping bd-dependent path",
        file=sys.stderr,
    )


def workstation_log_missing_bd(op: str = "operation") -> None:
    """Stderr message: bd is missing on a workstation (not cloud). Actionable."""
    print(
        f"{op}: bd not on PATH (and not a cloud session) — "
        f"install bd (https://github.com/gastownhall/beads) or fix your PATH",
        file=sys.stderr,
    )
