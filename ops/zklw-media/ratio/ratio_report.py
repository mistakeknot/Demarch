#!/usr/bin/env python3
"""Read ratio-telemetry.jsonl and report whether grey's upload is trending up.

Deltas are computed here rather than stored by the collector, so a missed cron
run costs resolution but never corrupts the series.

One wrinkle worth knowing: per-torrent `uploaded` counters vanish when a torrent
is removed, so summing them can make upload appear to go *down* across a prune.
The session-wide `transfer.up_info_data` counter does not have that problem but
resets when qBittorrent restarts. This report shows both and flags the
disagreement rather than silently picking one.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys

DEFAULT_IN = "/data/backups/ratio-telemetry.jsonl"


def load(path: str) -> list[dict]:
    snaps = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        snaps.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return []
    return sorted(snaps, key=lambda s: s.get("epoch", 0))


def per_day(delta_bytes: int, delta_secs: int) -> float:
    if delta_secs <= 0:
        return 0.0
    return delta_bytes / delta_secs * 86400


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="path", default=DEFAULT_IN)
    ap.add_argument("--last", type=int, default=14, help="show at most N intervals")
    args = ap.parse_args()

    snaps = load(args.path)
    if not snaps:
        print("no snapshots yet — run ratio_snapshot.py first")
        return 1
    if len(snaps) == 1:
        s = snaps[0]
        o = s["overall"]
        print(f"baseline only ({s['ts']}):")
        print(f"  {o['n']} torrents, up={o['uploaded']/1e9:.1f}GB, "
              f"zero-upload={o['zero_upload']}, ratio={o['ratio']:.4f}")
        print("  need a second snapshot before a rate can be computed")
        return 0

    first, last = snaps[0], snaps[-1]
    print(f"span: {first['ts']}  ->  {last['ts']}   ({len(snaps)} snapshots)")
    print()

    print(f"{'interval end':26s} {'sum-up/day':>12s} {'session-up/day':>15s} {'zero-up':>8s} {'torrents':>9s}")
    for prev, cur in list(zip(snaps, snaps[1:]))[-args.last:]:
        dt = cur.get("epoch", 0) - prev.get("epoch", 0)
        d_sum = cur["overall"]["uploaded"] - prev["overall"]["uploaded"]
        d_ses = cur["transfer"]["up_info_data"] - prev["transfer"]["up_info_data"]
        flag = ""
        if d_sum < 0:
            flag = "  <- torrents removed"
        if d_ses < 0:
            flag = "  <- qbit restarted"
        print(f"{cur['ts']:26s} {per_day(d_sum, dt)/1e9:11.2f}G {per_day(d_ses, dt)/1e9:14.2f}G "
              f"{cur['overall']['zero_upload']:8d} {cur['overall']['n']:9d}{flag}")

    print()
    dt = last.get("epoch", 0) - first.get("epoch", 0)
    d_sum = last["overall"]["uploaded"] - first["overall"]["uploaded"]
    print(f"whole-span average: {per_day(d_sum, dt)/1e9:.2f} GB/day uploaded")
    print(f"zero-upload torrents: {first['overall']['zero_upload']} -> {last['overall']['zero_upload']}")
    print(f"BASELINE for sylveste-aado was ~10 GB/day and 370 zero-upload on 2026-07-24.")

    print()
    print("per-tracker, latest snapshot:")
    for host, b in sorted(last["trackers"].items(), key=lambda kv: -kv[1]["uploaded"]):
        prev_b = first["trackers"].get(host)
        gain = (b["uploaded"] - prev_b["uploaded"]) / 1e9 if prev_b else 0.0
        print(f"  {host:26s} n={b['n']:4d} up={b['uploaded']/1e9:8.1f}GB "
              f"(+{gain:.1f}GB over span) ratio={b['ratio']:.4f} zero={b['zero_upload']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
