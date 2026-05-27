#!/usr/bin/env python3
"""Apply peerDependencies to plugin.json files based on ARCHITECTURE.json warnings.

Reads ARCHITECTURE.json. For each plugin with discovered strong references
(count >= 3) to other plugins, adds those names to plugin.json's
peerDependencies array. Preserves JSON formatting (2-space indent, trailing
newline) and existing field order.

Idempotent: re-running merges new peers without removing existing ones.

Usage:
  python3 apply-peer-deps.py                 # dry run (default)
  python3 apply-peer-deps.py --apply         # actually write changes
  python3 apply-peer-deps.py --apply --only=interflux,interspect  # subset
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SYLVESTE = Path(__file__).resolve().parent.parent
ARCH = SYLVESTE / "ARCHITECTURE.json"
INTERVERSE = SYLVESTE / "interverse"


def manifest_path(name: str) -> Path:
    return INTERVERSE / name / ".claude-plugin" / "plugin.json"


def merge_peer_deps(manifest: dict, new_peers: list[str]) -> tuple[dict, list[str], list[str]]:
    """Return (updated_manifest, added, already_present)."""
    existing = manifest.get("peerDependencies") or []
    existing_set = set(existing)
    added = [p for p in new_peers if p not in existing_set]
    already = [p for p in new_peers if p in existing_set]
    if not added:
        return manifest, [], already

    merged = sorted(set(existing) | set(new_peers))

    # Preserve key order; insert peerDependencies right after 'keywords' if
    # present, else after 'license', else append.
    new_manifest: dict = {}
    inserted = False
    for k, v in manifest.items():
        if k == "peerDependencies":
            continue
        new_manifest[k] = v
        if not inserted and k in ("keywords", "license", "author"):
            # Insert after the first of these we see (in manifest key order
            # this is whichever comes last among the existing keys).
            pass
    # Simpler: append at end with sorted order. JSON consumers don't care about
    # key order; humans can re-shuffle later.
    new_manifest["peerDependencies"] = merged
    return new_manifest, added, already


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes")
    ap.add_argument(
        "--only",
        default="",
        help="comma-separated plugin names to limit changes to",
    )
    ap.add_argument(
        "--threshold",
        type=int,
        default=3,
        help="min reference count to treat as a 'strong' peer",
    )
    args = ap.parse_args()

    only_filter = {n.strip() for n in args.only.split(",") if n.strip()}

    if not ARCH.exists():
        print(f"ARCHITECTURE.json not found at {ARCH}")
        print("run: python3 Sylveste/scripts/build-architecture-map.py")
        return 1

    graph = json.loads(ARCH.read_text())
    plugins = graph["plugins"]

    summary_added: dict[str, list[str]] = {}
    summary_skipped: dict[str, list[str]] = {}

    for name, p in sorted(plugins.items()):
        if only_filter and name not in only_filter:
            continue
        strong = [
            n for n, c in p["discovered_refs"].items() if c >= args.threshold
        ]
        if not strong:
            continue

        path = manifest_path(name)
        if not path.exists():
            print(f"  skip {name}: no manifest at {path}")
            continue

        manifest = json.loads(path.read_text())
        new_manifest, added, already = merge_peer_deps(manifest, strong)

        if not added:
            continue

        summary_added[name] = added
        if already:
            summary_skipped[name] = already

        if args.apply:
            path.write_text(json.dumps(new_manifest, indent=2) + "\n")
            print(f"  + {name}: added {added}")
        else:
            print(f"  ~ {name}: would add {added}" + (f" (already has {already})" if already else ""))

    print()
    print(f"plugins changed: {len(summary_added)}")
    print(f"mode: {'APPLIED' if args.apply else 'DRY-RUN (rerun with --apply to write)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
