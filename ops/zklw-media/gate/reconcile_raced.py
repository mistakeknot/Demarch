#!/usr/bin/env python3
"""Remove the torrents the gate would have rejected — but ONLY once each has
satisfied its Hit-and-Run obligation. Runs ON grey.

THE GUARD IS THE POINT. Every one of these came from HDBits, a private tracker,
and removing a torrent before its seeding floor is a Hit-and-Run — which is
account-fatal, not a warning. At the time of writing all 24 were less than a day
old, so NONE of them could be touched; the floor (min_seeding_time 20160 minutes
= 14 days, from the qbit-manage ratio-race group) does not clear until
2026-08-08.

So this script is written to be safe to run at any time: it removes only what is
provably past the floor and reports how many days remain on everything else.
Running it early is a no-op, not a mistake.

  dry run (default):  python3 reconcile_raced.py
  actually remove:    python3 reconcile_raced.py --apply

Deletes files along with the torrent (--delete-files is implied by --apply);
the whole point is reclaiming the disk.

Stdlib only. Credentials are read server-side and never appear in argv.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

QBIT = "http://100.123.250.67:8080"
QBM_CONFIG = "/home/mk/grey-media/config/qbit-manage/config.yml"
DISPOSITION = "/root/grey-ops/disposition.json"

# Mirrors the qbit-manage `ratio-race` share_limits group. Kept as a literal
# rather than parsed so that a config edit cannot silently loosen this guard.
MIN_SEEDING_MINUTES = 20160  # 14 days


def qbm_password() -> str:
    in_blk = False
    for line in open(QBM_CONFIG, encoding="utf-8"):
        s = line.strip()
        if s.startswith("qbt:"):
            in_blk = True
            continue
        if in_blk and line[:1] not in (" ", "\t", "\n", "#"):
            break
        if in_blk and s.startswith("pass:"):
            return s.split("pass:", 1)[1].strip().strip("'\"")
    return ""


class Qbit:
    def __init__(self, base: str, password: str):
        self.base = base.rstrip("/")
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        body = urllib.parse.urlencode({"username": "admin", "password": password}).encode()
        req = urllib.request.Request(
            f"{self.base}/api/v2/auth/login", data=body,
            headers={"Referer": self.base, "Origin": self.base})
        with self.op.open(req, timeout=30) as r:
            if r.status not in (200, 204):
                raise RuntimeError(f"login HTTP {r.status}")

    def get(self, path: str):
        req = urllib.request.Request(f"{self.base}{path}", headers={"Referer": self.base})
        with self.op.open(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def post(self, path: str, data: dict):
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(f"{self.base}{path}", data=body,
                                     headers={"Referer": self.base})
        with self.op.open(req, timeout=60) as r:
            return r.read().decode()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="actually remove the eligible torrents and their files")
    args = ap.parse_args()

    try:
        disp = json.load(open(DISPOSITION))
    except OSError as exc:
        print(f"cannot read {DISPOSITION}: {exc}", file=sys.stderr)
        print("generate it with `npm run disposition` in ops/zklw-media/gate and scp it here.",
              file=sys.stderr)
        return 2

    drop_names = set(disp["drop"])
    keep_names = set(disp["keep"])

    pw = qbm_password()
    if not pw:
        print("could not read qbit password", file=sys.stderr)
        return 2
    qb = Qbit(QBIT, pw)
    tors = qb.get("/api/v2/torrents/info")

    eligible, blocked, missing = [], [], []
    seen = set()
    for t in tors:
        name = t["name"]
        if name not in drop_names:
            continue
        seen.add(name)
        seeding_min = int(t.get("seeding_time", 0)) / 60
        remaining = MIN_SEEDING_MINUTES - seeding_min
        row = (name, seeding_min / 1440, remaining / 1440, t.get("size", 0) / 1e9, t["hash"])
        (eligible if remaining <= 0 else blocked).append(row)

    missing = sorted(drop_names - seen)

    print(f"disposition: keep {len(keep_names)}, drop {len(drop_names)}")
    print(f"HnR floor: {MIN_SEEDING_MINUTES} minutes ({MIN_SEEDING_MINUTES/1440:.0f} days)\n")

    if blocked:
        print(f"BLOCKED — still inside the HnR window ({len(blocked)}):")
        for name, seeded_d, remain_d, gb, _ in sorted(blocked, key=lambda r: r[2]):
            print(f"  {remain_d:5.1f}d left  (seeded {seeded_d:4.1f}d, {gb:5.2f}GB)  {name[:64]}")
        print()

    if missing:
        print(f"not present in the client ({len(missing)}) — already gone:")
        for n in missing:
            print(f"  {n[:74]}")
        print()

    if not eligible:
        print("nothing is eligible for removal yet. This is the expected outcome")
        print("until the floor clears — re-run then. No action taken.")
        return 0

    freed = sum(r[3] for r in eligible)
    print(f"ELIGIBLE for removal ({len(eligible)}), frees {freed:.1f}GB:")
    for name, seeded_d, _, gb, _ in eligible:
        print(f"  seeded {seeded_d:5.1f}d  {gb:5.2f}GB  {name[:64]}")

    if not args.apply:
        print("\ndry run — nothing removed. Re-run with --apply to remove these.")
        return 0

    hashes = "|".join(r[4] for r in eligible)
    qb.post("/api/v2/torrents/delete", {"hashes": hashes, "deleteFiles": "true"})
    print(f"\nremoved {len(eligible)} torrents and their files ({freed:.1f}GB reclaimed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
