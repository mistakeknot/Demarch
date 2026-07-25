#!/usr/bin/env python3
"""Add a `ratio-race` share_limits group to qbit-manage's config on grey.

Racing without retention fills a 44 TB array; retention without HnR floors gets
the account penalised. This adds the group that governs raced torrents, sitting
inside the existing "HnR FIREWALL" posture rather than around it.

Deliberately lands with cleanup:false, matching every other group in that file.
qbit-manage stays the ONLY component allowed to remove a torrent, and it still
removes nothing until someone flips cleanup on. Turning cleanup:true is the same
class of decision as arming the RSS rule, and must not happen before the racer
has actually produced torrents whose HnR obligations are provably satisfied.

min_seeding_time is 20160 minutes (14 days), matching the existing hdbits group.
DESIGN.md records HDBits HnR as "none reported, unconfirmed -- seed long anyway",
so the floor is deliberately conservative.

Writes a timestamped backup first and refuses to write if the result does not
re-read cleanly. Idempotent: re-running detects the group and exits.

Usage:  patch_qbm_race_group.py [--apply]   (default is a diff preview)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time

CONFIG = "/home/mk/grey-media/config/qbit-manage/config.yml"

GROUP = """  ratio-race:
    priority: 0
    include_any_tags:
    - ratio-race
    max_ratio: 100.0
    max_seeding_time: -1
    min_seeding_time: 20160
    cleanup: false
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    try:
        text = open(CONFIG, encoding="utf-8").read()
    except OSError as exc:
        print(f"cannot read {CONFIG}: {exc}", file=sys.stderr)
        return 1

    if "ratio-race:" in text:
        print("ratio-race group already present — nothing to do")
        return 0
    if "share_limits:" not in text:
        print("no share_limits section found — refusing to guess", file=sys.stderr)
        return 1

    # Insert ahead of the catch-all `default:` group. Order matters to
    # qbit-manage only via `priority`, but keeping default last matches how a
    # human reads the file.
    lines = text.splitlines(keepends=True)
    out, inserted, in_sl = [], False, False
    for line in lines:
        if line.startswith("share_limits:"):
            in_sl = True
        elif in_sl and line.startswith("  default:") and not inserted:
            out.append(GROUP)
            inserted = True
        out.append(line)
    if not inserted:
        # no default group; append at end of the share_limits block
        out.append(GROUP)
        inserted = True
    new = "".join(out)

    if not args.apply:
        print("--- preview (not written) ---")
        print(GROUP)
        print(f"would insert into {CONFIG} ({len(text)} -> {len(new)} bytes)")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = f"{CONFIG}.bak-{stamp}"
    shutil.copy2(CONFIG, backup)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        fh.write(new)

    check = open(CONFIG, encoding="utf-8").read()
    if "ratio-race:" not in check or len(check) < len(text):
        shutil.copy2(backup, CONFIG)
        print("post-write verification failed — restored backup", file=sys.stderr)
        return 2

    print(f"backup: {backup}")
    print(f"wrote {CONFIG}: ratio-race group added (cleanup:false, min_seeding_time 20160m)")
    print("qbit-manage picks it up on its next 30-minute cycle; it will report the")
    print("group with 0 torrents until the RSS racer is armed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
