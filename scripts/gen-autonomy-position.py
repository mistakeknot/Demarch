#!/usr/bin/env python3
"""Regenerate the "current position" block in docs/canon/autonomy.md from state.

The canon page is the single definition of Sylveste's autonomy scales. Two of
the numbers on it are facts about the running system rather than definitions,
and hand-maintained numbers rot:

  * the declared human-delegation level  -> kernel state, via `ic autonomy status`
  * the A:L3 no-touch streak             -> `clavain-cli calibration-streak status`

This script reads both and rewrites the marked block. The kernel is not asked
about A:L3 and clavain-cli is not asked about delegation: each scale is read
from the layer that owns it, and the join happens here, at the repo level.

Usage:
  gen-autonomy-position.py                       # rewrite the block in place
  gen-autonomy-position.py --check               # exit 1 if the block is stale
  gen-autonomy-position.py --allow-unavailable   # render "unavailable" anyway

Exit codes: 0 current/rewritten, 1 stale (--check), 2 the sources could not be
read or the canon page is missing.

Why an unreadable source is exit 2 and not 0 or 1
-------------------------------------------------
`ic` lives in core/intercore, which the monorepo .gitignore's. On a cloud runner
the checkout has no kernel. Without one:

  * reporting "current" would compare an unavailable-block against an
    unavailable-block and pass — a green check that inspected nothing, the same
    vacuity trap that let 21 Kimi manifests drift (see
    .github/workflows/kimi-manifest-drift.yml);
  * reporting "stale" would be a lie: nothing was compared;
  * rewriting would overwrite a true block with "Current position: unavailable"
    and commit that.

So both modes stop at exit 2, "could not verify". `--allow-unavailable` opts
into the old rendering for the rare case where recording the gap is the point.

Real enforcement therefore runs in the pre-commit hook, where the monorepo is
materialised. CI's job is to prove this checker still refuses to report on a
source-less checkout, and to unit-test the rendering the hook depends on.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANON = REPO_ROOT / "docs" / "canon" / "autonomy.md"

BEGIN = "<!-- BEGIN GENERATED: autonomy-position -->"
END = "<!-- END GENERATED: autonomy-position -->"

# The floor table is a second generated region. It is separate from the position
# block because the two answer different questions and change on different
# cadences: the position block is live state (which level is declared right now,
# what the streak reads), while this is the kernel's standing ruling on which
# operations that level gates. Splicing them together would mean a streak tick
# rewrote the floor prose and vice versa.
FLOORS_BEGIN = "<!-- BEGIN GENERATED: autonomy-floors -->"
FLOORS_END = "<!-- END GENERATED: autonomy-floors -->"

# Kept in sync with pkg/autonomy.DefaultLevel — and asserted by
# tests/test_gen_autonomy_position.py when core/ is present. Duplicated deliberately:
# this script must still render something honest when `ic` is unavailable, and
# a wrong guess here is visible in the output rather than silent.
KERNEL_DEFAULT_LEVEL = 2


def resolve_bin(name: str) -> str | None:
    """Resolve a tool, honoring an explicit override.

    IC_BIN / CLAVAIN_CLI_BIN let this run against a freshly-built binary
    without installing it onto PATH first — the kernel change that adds
    `ic autonomy` ships before the binary is rolled out everywhere.
    """
    override = os.environ.get(name.upper().replace("-", "_") + "_BIN")
    if override:
        return override if os.path.isfile(override) else None
    return shutil.which(name)


def run(cmd: list[str]) -> str | None:
    """Run a command, returning stdout or None if it is unavailable/fails."""
    resolved = resolve_bin(cmd[0])
    if resolved is None:
        return None
    cmd = [resolved] + cmd[1:]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def delegation() -> dict:
    """Read the declared delegation level from kernel state."""
    out = run(["ic", "--json", "autonomy", "status"])
    if not out:
        return {"available": False}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"available": False}
    data["available"] = True
    return data


def streak() -> str | None:
    """Read the A:L3 no-touch streak from the OS layer."""
    out = run(["clavain-cli", "calibration-streak", "status"])
    return out or None


# The window the ceiling's observed effect is reported over. Stated on the page
# rather than left implicit: "the ceiling withheld 3 pushes" means nothing
# without knowing over what span, and a hardcoded number in prose would drift.
CEILING_WINDOW = "720h"
CEILING_WINDOW_LABEL = "30 days"


def ceiling() -> dict | None:
    """Read what the delegation ceiling actually withheld, from the audit store.

    The count is computed in SQL by `policy audit --count`, not derived here
    from a listing. A generator that counted rows itself would silently
    undercount past the listing's --limit, and would be recomputing a number
    the audit store is the authority on.
    """
    out = run(["clavain-cli", "policy", "audit", "--count", f"--since={CEILING_WINDOW}"])
    if not out:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# Sentinel for "argument not supplied". None cannot serve: for the streak it is
# a real value meaning "no streak reported", and conflating the two made a
# caller asking for a streak-less render get a live reading instead.
_UNSET = object()


def render(d=_UNSET, s=_UNSET, c=_UNSET) -> str:
    """Render the block from two source readings.

    Both readings are parameters rather than calls so the rendering can be
    tested without a kernel present — which is the only part of this script a
    plugin-less CI checkout can meaningfully exercise.
    """
    if d is _UNSET:
        d = delegation()
    if s is _UNSET:
        s = streak()
    if c is _UNSET:
        c = ceiling()
    lines: list[str] = [BEGIN, ""]
    lines.append("<!-- Regenerated by scripts/gen-autonomy-position.py. Do not hand-edit. -->")
    lines.append("")

    if not d.get("available"):
        lines.append(
            "**Current position: unavailable.** `ic` could not be reached when this "
            "block was generated, so no live value is recorded here. Run "
            "`scripts/gen-autonomy-position.py` on a machine with the kernel installed."
        )
    elif d.get("declared"):
        lines.append(
            f"**Declared delegation level: L{d['level']}** — {d['name']}. "
            f"New runs inherit `auto_advance={str(d['derives_auto_advance']).lower()}`."
        )
    else:
        lines.append(
            f"**Delegation level: not declared.** The kernel falls back to "
            f"L{d['level']} ({d['name']}), so new runs inherit "
            f"`auto_advance={str(d['derives_auto_advance']).lower()}`."
        )
        lines.append("")
        lines.append(
            "> This is the honest state, not a placeholder. Prose across the repo "
            "has long said \"currently operating at L1–L2\", but a band is not a "
            "machine fact and nothing ever recorded which rung was in force. "
            "Declare one with `ic config set autonomy.delegation_level <0-5>`."
        )

    if s:
        lines.append("")
        lines.append(f"**Track A evidence:** `{s}`")
        lines.append("")
        lines.append(
            "Track levels are earned, never set — this is evidence that may justify "
            "a delegation decision, not a delegation level itself (see §5, §7)."
        )

    if c is not None:
        lines.append("")
        with_evidence = c.get("with_evidence", 0)
        capped = c.get("capped", 0)
        if with_evidence == 0:
            # 0-of-0 is not a rate. Reporting "0 withheld" against an empty
            # window would read as "the ceiling never fires", which is a claim
            # this data cannot support.
            lines.append(
                f"**Ceiling evidence (last {CEILING_WINDOW_LABEL}):** no decisions "
                "carrying delegation evidence yet, so the ceiling has not been "
                "observed either acting or standing aside. An empty window, not a "
                "zero rate."
            )
        else:
            by_op = c.get("capped_by_op") or {}
            detail = ""
            if by_op:
                detail = " (" + ", ".join(
                    f"`{op}` \u00d7{n}" for op, n in sorted(by_op.items())
                ) + ")"
            lines.append(
                f"**Ceiling evidence (last {CEILING_WINDOW_LABEL}):** {capped} of "
                f"{with_evidence} recorded decisions were withheld by the delegation "
                f"level rather than by policy{detail}."
            )

    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def render_floors(d=_UNSET) -> str:
    """Render the operation-floor table from the kernel's rulings.

    The table is the kernel's, not this page's: `pkg/autonomy.Rulings()` carries
    both the floor and the reason for it, so an op that gains or loses a floor
    changes this section with no doc edit. The prose that used to live here
    asserted the list by hand, which is how it went stale.
    """
    if d is _UNSET:
        d = delegation()
    ops = d.get("ops") or []

    lines: list[str] = [FLOORS_BEGIN, ""]
    lines.append("<!-- Regenerated by scripts/gen-autonomy-position.py. Do not hand-edit. -->")
    lines.append("")
    lines.append(
        "**Which operations carry a floor** is a kernel fact, not a policy one. "
        "This table is generated from `pkg/autonomy.Rulings()` — change the floor "
        "there and this section follows; editing it here accomplishes nothing."
    )
    lines.append("")
    lines.append("| Operation | Floor | Why |")
    lines.append("| --- | --- | --- |")
    for op in ops:
        floor = op.get("floor", 0)
        shown = f"**L{floor}**" if floor else "none"
        lines.append(f"| `{op.get('op')}` | {shown} | {op.get('reason', '')} |")
    lines.append("")
    lines.append(
        "An operation *absent* from this table has never been ruled on. `none` is "
        "a recorded exemption, not an omission — the distinction is the point of "
        "listing exempt operations at all. Ops with no floor are governed by "
        "policy exactly as they were before the ceiling existed."
    )
    lines.append("")
    lines.append(FLOORS_END)
    return "\n".join(lines)


def splice(text: str, block: str, begin: str = BEGIN, end: str = END) -> str:
    pattern = re.compile(
        re.escape(begin) + r".*?" + re.escape(end), re.DOTALL
    )
    if not pattern.search(text):
        raise SystemExit(
            f"error: markers not found in {CANON.relative_to(REPO_ROOT)}\n"
            f"       expected a block delimited by:\n         {begin}\n         {end}"
        )
    return pattern.sub(lambda _: block, text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the block is stale instead of rewriting it",
    )
    ap.add_argument(
        "--allow-unavailable",
        action="store_true",
        help="render 'Current position: unavailable' instead of exiting 2 when "
        "the kernel cannot be reached",
    )
    args = ap.parse_args()

    if not CANON.exists():
        print(f"error: {CANON} does not exist", file=sys.stderr)
        return 2

    d = delegation()
    if not d.get("available") and not args.allow_unavailable:
        verb = "verify" if args.check else "regenerate"
        print(
            f"error: cannot {verb} the autonomy position block — "
            "`ic autonomy status` is unreachable,\n"
            "       so the declared delegation level could not be read. This is "
            "not 'stale' and not\n"
            "       'current': nothing was compared. Set IC_BIN, run where "
            "core/intercore is\n"
            "       materialised, or pass --allow-unavailable to record the gap "
            "deliberately.",
            file=sys.stderr,
        )
        return 2

    # An `ic` new enough to answer `autonomy status` but too old to report `ops`
    # is the vacuity trap wearing a different hat: the floor table would render
    # empty and the rewrite would silently delete a true list. Absent is not the
    # same as none — a kernel with no floors at all still emits `"ops": []`.
    if d.get("available") and d.get("ops") is None and not args.allow_unavailable:
        print(
            "error: `ic autonomy status --json` returned no `ops` field, so the "
            "operation-floor\n"
            "       table could not be read. This is an `ic` older than the "
            "floor table; rendering\n"
            "       an empty table would delete a true list. Rebuild `ic` from "
            "core/intercore, or\n"
            "       pass --allow-unavailable to record the gap deliberately.",
            file=sys.stderr,
        )
        return 2

    current = CANON.read_text(encoding="utf-8")
    updated = splice(current, render(d, streak(), ceiling()))
    updated = splice(updated, render_floors(d), FLOORS_BEGIN, FLOORS_END)

    if current == updated:
        print("autonomy position block is current")
        return 0

    if args.check:
        print(
            "autonomy position block is STALE — run scripts/gen-autonomy-position.py",
            file=sys.stderr,
        )
        return 1

    CANON.write_text(updated, encoding="utf-8")
    print(f"rewrote autonomy position block in {CANON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
