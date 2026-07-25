#!/usr/bin/env python3
"""Ratio telemetry for grey-area.

Appends one JSON line per run to a telemetry log so we can answer the only
question that matters for the ratio engine: *is upload going up?*

The epic (sylveste-aado) is judged against a baseline captured 2026-07-24:
86 GB uploaded across 8 days, 370 of 444 torrents with zero upload ever.
Without a time series those numbers are unfalsifiable, so this runs first —
before cross-seed, RSS racing, or any retention change lands.

Per-torrent `uploaded` is cumulative since the torrent was added, so the
delta between two snapshots is real bytes moved in that window. Deltas are
computed at read time (see `ratio_report.py`), not stored, so a missed run
degrades resolution rather than corrupting the series.

Stdlib only — grey has no venv for ops scripts and this must never be the
reason a cron run fails.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from http.cookiejar import CookieJar

DEFAULT_QBIT = "http://100.123.250.67:8080"
DEFAULT_OUT = "/data/backups/ratio-telemetry.jsonl"
# qbit-manage is the canonical place this password already lives on grey.
# Reading it here avoids introducing a second copy of the secret.
QBM_CONFIG = "/home/mk/grey-media/config/qbit-manage/config.yml"


def read_password() -> str:
    """Env var wins; otherwise lift it from qbit-manage's config."""
    env = os.environ.get("QBIT_PASS")
    if env:
        return env
    try:
        with open(QBM_CONFIG, encoding="utf-8") as fh:
            in_qbt = False
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("qbt:"):
                    in_qbt = True
                    continue
                # any new top-level key ends the qbt block
                if in_qbt and line[:1] not in (" ", "\t", "\n", "#"):
                    break
                if in_qbt and stripped.startswith("pass:"):
                    return stripped.split("pass:", 1)[1].strip().strip("'\"")
    except OSError as exc:
        print(f"could not read {QBM_CONFIG}: {exc}", file=sys.stderr)
    return ""


class Qbit:
    def __init__(self, base: str, password: str, user: str = "admin"):
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )
        self._login(user, password)

    def _login(self, user: str, password: str) -> None:
        body = urllib.parse.urlencode({"username": user, "password": password}).encode()
        req = urllib.request.Request(
            f"{self.base}/api/v2/auth/login",
            data=body,
            # qBittorrent 5.x rejects the login without a matching Referer/Origin.
            headers={"Referer": self.base, "Origin": self.base},
        )
        with self.opener.open(req, timeout=30) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"qbit login HTTP {resp.status}")

    def get(self, path: str):
        req = urllib.request.Request(f"{self.base}{path}", headers={"Referer": self.base})
        with self.opener.open(req, timeout=60) as resp:
            return json.loads(resp.read().decode())


def tracker_host(torrent: dict) -> str:
    url = torrent.get("tracker") or ""
    if "//" in url:
        return url.split("//", 1)[1].split("/", 1)[0]
    return "(none)"


def collect(qb: Qbit) -> dict:
    torrents = qb.get("/api/v2/torrents/info")
    transfer = qb.get("/api/v2/transfer/info")

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "n": 0,
            "size": 0,
            "uploaded": 0,
            "downloaded": 0,
            "zero_upload": 0,
            "seeding": 0,
            "incomplete": 0,
            "with_peers": 0,
        }
    )
    overall = dict(buckets["__overall__"])

    for t in torrents:
        for key in (tracker_host(t), "__overall__"):
            b = buckets[key]
            b["n"] += 1
            b["size"] += t.get("size", 0)
            b["uploaded"] += t.get("uploaded", 0)
            b["downloaded"] += t.get("downloaded", 0)
            if t.get("uploaded", 0) == 0:
                b["zero_upload"] += 1
            if t.get("state") in ("stalledUP", "uploading", "queuedUP", "forcedUP"):
                b["seeding"] += 1
            if t.get("progress", 0) < 1.0:
                b["incomplete"] += 1
            if t.get("num_leechs", 0) or t.get("num_seeds", 0):
                b["with_peers"] += 1

    overall = buckets.pop("__overall__")
    for b in list(buckets.values()) + [overall]:
        b["ratio"] = round(b["uploaded"] / b["downloaded"], 5) if b["downloaded"] else 0.0

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "epoch": int(time.time()),
        "overall": overall,
        "trackers": dict(buckets),
        # session-wide counters; survive individual torrent removal, unlike the
        # per-torrent sums above, so they catch upload from since-deleted torrents
        "transfer": {
            "up_info_data": transfer.get("up_info_data", 0),
            "dl_info_data": transfer.get("dl_info_data", 0),
            "connection_status": transfer.get("connection_status"),
            "external_ip": transfer.get("last_external_address_v4"),
        },
    }


def human(snap: dict) -> str:
    o = snap["overall"]
    lines = [
        f"{snap['ts']}  conn={snap['transfer']['connection_status']} ip={snap['transfer']['external_ip']}",
        f"  overall: {o['n']} torrents  {o['size']/1e12:.2f}TB  "
        f"up={o['uploaded']/1e9:.1f}GB dl={o['downloaded']/1e9:.1f}GB ratio={o['ratio']:.4f}",
        f"  zero-upload={o['zero_upload']}  seeding={o['seeding']}  "
        f"incomplete={o['incomplete']}  with-peers={o['with_peers']}",
    ]
    for host, b in sorted(snap["trackers"].items(), key=lambda kv: -kv[1]["uploaded"]):
        lines.append(
            f"    {host:26s} n={b['n']:4d} up={b['uploaded']/1e9:8.1f}GB "
            f"ratio={b['ratio']:.4f} zero={b['zero_upload']:4d} peers={b['with_peers']}"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--qbit", default=os.environ.get("QBIT_URL", DEFAULT_QBIT))
    ap.add_argument("--out", default=os.environ.get("RATIO_OUT", DEFAULT_OUT))
    ap.add_argument("--print", dest="show", action="store_true", help="print human summary")
    ap.add_argument("--no-write", action="store_true", help="collect but do not append")
    args = ap.parse_args()

    password = read_password()
    if not password:
        print("no qbit password (set QBIT_PASS or fix qbit-manage config)", file=sys.stderr)
        return 2

    try:
        qb = Qbit(args.qbit, password)
        snap = collect(qb)
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print(f"collection failed: {exc}", file=sys.stderr)
        return 1

    if not args.no_write:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(snap, separators=(",", ":")) + "\n")

    if args.show or args.no_write:
        print(human(snap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
