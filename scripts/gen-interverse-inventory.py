#!/usr/bin/env python3
"""Write the generated Interverse inventory ledger to .interwatch/.

This compatibility entrypoint keeps the older generator-style command name
while delegating all drift classification to scripts/interverse_inventory.py.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import interverse_inventory

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".interwatch" / "interverse-inventory.json"


def main() -> int:
    ledger = interverse_inventory.build_inventory(ROOT)
    ledger["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = ledger["summary"]
    print(
        f"Interverse inventory written to {OUTPUT.relative_to(ROOT)}: "
        f"{summary['plugin_count']} plugins, "
        f"{summary['high_drift_count']} high drift, "
        f"{summary['warning_drift_count']} warnings.",
        file=sys.stderr,
    )
    return 1 if summary["high_drift_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
