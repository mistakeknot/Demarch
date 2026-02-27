#!/usr/bin/env python3
"""Backfill Philosophy Alignment Protocol to all subproject AGENTS.md files.

Inserts after the first heading + its description paragraph.
Usage: python3 scripts/backfill-philosophy-protocol.py [--dry-run]
"""

import os
import sys
from pathlib import Path

DEMARCH_ROOT = Path(__file__).resolve().parent.parent
DRY_RUN = "--dry-run" in sys.argv

TARGETS = [
    # Core
    "core/intercore/AGENTS.md",
    "core/intermute/AGENTS.md",
    "core/interbench/AGENTS.md",
    "core/marketplace/AGENTS.md",
    "core/agent-rig/AGENTS.md",
    # OS
    "os/clavain/AGENTS.md",
    # Apps
    "apps/autarch/AGENTS.md",
    "apps/intercom/AGENTS.md",
    # SDK
    "sdk/interbase/AGENTS.md",
    # Interverse plugins
    "interverse/interchart/AGENTS.md",
    "interverse/interdoc/AGENTS.md",
    "interverse/interfluence/AGENTS.md",
    "interverse/interflux/AGENTS.md",
    "interverse/interkasten/AGENTS.md",
    "interverse/interlearn/AGENTS.md",
    "interverse/interlock/AGENTS.md",
    "interverse/intermux/AGENTS.md",
    "interverse/intername/AGENTS.md",
    "interverse/interpath/AGENTS.md",
    "interverse/interserve/AGENTS.md",
    "interverse/intertrust/AGENTS.md",
    "interverse/interwatch/AGENTS.md",
    "interverse/tldr-swinton/AGENTS.md",
    "interverse/tool-time/AGENTS.md",
    "interverse/tuivision/AGENTS.md",
]

def compute_relpath(target: str) -> str:
    target_dir = (DEMARCH_ROOT / target).parent
    philosophy = DEMARCH_ROOT / "PHILOSOPHY.md"
    return os.path.relpath(philosophy, target_dir)

def build_protocol(relpath: str) -> str:
    return f"""
## Canonical References
1. [`PHILOSOPHY.md`]({relpath}) — direction for ideation and planning decisions.
2. `CLAUDE.md` — implementation details, architecture, testing, and release workflow.

## Philosophy Alignment Protocol
Review [`PHILOSOPHY.md`]({relpath}) during:
- Intake/scoping
- Brainstorming
- Planning
- Execution kickoff
- Review/gates
- Handoff/retrospective

For brainstorming/planning outputs, add two short lines:
- **Alignment:** one sentence on how the proposal supports the module's purpose within Demarch's philosophy.
- **Conflict/Risk:** one sentence on any tension with philosophy (or 'none').

If a high-value change conflicts with philosophy, either:
- adjust the plan to align, or
- create follow-up work to update `PHILOSOPHY.md` explicitly.
"""

def find_insert_point(lines: list[str]) -> int:
    """Find the line index after the first heading + its description paragraph."""
    heading_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            heading_idx = i
            break

    if heading_idx is None:
        return 0

    # Walk forward past description text until we hit a blank line or ## heading
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "" or stripped.startswith("## "):
            return i

    return len(lines)

def main():
    inserted = 0
    skipped = 0
    missing = 0

    for target in TARGETS:
        filepath = DEMARCH_ROOT / target
        if not filepath.exists():
            print(f"MISSING: {target}")
            missing += 1
            continue

        content = filepath.read_text()
        if "Philosophy Alignment Protocol" in content:
            print(f"SKIP: {target} (already has protocol)")
            skipped += 1
            continue

        relpath = compute_relpath(target)

        if DRY_RUN:
            print(f"WOULD INSERT: {target} (relpath: {relpath})")
            inserted += 1
            continue

        lines = content.splitlines(keepends=True)
        insert_at = find_insert_point([l.rstrip("\n") for l in lines])
        protocol = build_protocol(relpath)

        new_lines = lines[:insert_at] + [protocol + "\n"] + lines[insert_at:]
        filepath.write_text("".join(new_lines))
        print(f"INSERTED: {target} (line {insert_at}, relpath: {relpath})")
        inserted += 1

    print(f"\nSummary: {inserted} inserted, {skipped} skipped, {missing} missing")

if __name__ == "__main__":
    main()
