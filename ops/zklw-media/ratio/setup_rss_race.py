#!/usr/bin/env python3
"""Build the supply-side fresh-release path: Prowlarr RSS -> qBittorrent auto-download.

This is the lever that actually earns ratio. Radarr/Sonarr are demand-driven —
they grab what somebody asked for — and ratio is earned supply-side, by being an
early seeder on brand-new uploads regardless of whether anyone requested them.
Radarr's wanted-list model structurally cannot do that, so the grab happens in
qBittorrent's native RSS auto-downloader instead, fed by Prowlarr's torznab
endpoint. No new container, and it stays clear of the *arr library management.

CREATED DISARMED. The rule is written with enabled=False, so the feed is
subscribed and the filter is in place but nothing is grabbed until someone
flips it on deliberately. Arming it is an outward-facing act: grey starts
pulling new uploads off a private tracker and announcing them, and every
grabbed torrent inherits that tracker's Hit-and-Run obligation.

  arm:     setup_rss_race.py --arm
  disarm:  setup_rss_race.py --disarm
  status:  setup_rss_race.py --status

Safety rails that must stay true while this is armed:
  - qbit-manage keeps cleanup:false, so nothing deletes a torrent out from under
    its HnR obligation. It is the only component allowed to remove torrents.
  - The race category is separate from radarr/sonarr so library management and
    ratio-seeding never fight over the same torrent.
  - Size bounds keep a runaway feed from eating the array; grey has ~35 TB free
    and no retention aging is enabled yet.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

QBIT = "http://100.123.250.67:8080"
PROWLARR = "http://prowlarr:9696"
QBM_CONFIG = "/home/mk/grey-media/config/qbit-manage/config.yml"
PROWLARR_XML = "/home/mk/grey-media/config/prowlarr/config.xml"

RULE_NAME = "ratio-race-hdbits"
CATEGORY = "ratio-race"
SAVE_PATH = "/data/torrents/race"
FEED_NAME = "hdbits-new"

# HDBits only. TorrentLeech is the tracker where grey's upload measurably
# converts, but TL mandates the seedbox be declared in-profile and enforces
# strict 4-10 day HnR -- arming a racer there before that is verified risks the
# account. Karagarga is excluded outright: it is seedbox-hostile and grey
# already carries unresolved datacenter-IP exposure there.
INDEXER_ID = 1

# Bound what a race is allowed to pull. A fresh 1080p ENCODE is the sweet spot:
# small enough to finish before the swarm saturates, big enough to be worth
# seeding.
#
# qBittorrent's RSS rules have NO size filter — only title regex — so size has
# to be controlled through naming conventions. Blacklisting large formats does
# not work: a first pass excluding REMUX/2160p/COMPLETE.BLURAY still admitted
# "Tabi to Hibi 2025 1080p Blu-ray AVC DTS-HD MA 5.1-DStudio" at 47 GB, because
# an untouched 1080p disc is none of those things.
#
# So WHITELIST encodes instead. Scene/P2P encodes always carry an explicit codec
# tag (x264/x265/H.264/H.265); untouched discs and remuxes are labelled AVC/VC-1
# and never carry one. Requiring the codec tag excludes the whole large-format
# family by construction rather than by enumeration.
MUST_CONTAIN = r"(?=.*\b(1080p|720p)\b)(?=.*(x264|x265|[hH]\.?26[45]))"
MUST_NOT_CONTAIN = r"REMUX|2160p|\bUHD\b|COMPLETE\.?BLURAY|BluRay\.DiSC|\bDiSC\b"


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


def prowlarr_key() -> str:
    for line in open(PROWLARR_XML, encoding="utf-8", errors="ignore"):
        if "<ApiKey>" in line:
            return line.split("<ApiKey>")[1].split("</ApiKey>")[0].strip()
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

    def call(self, path: str, data: dict | None = None) -> str:
        body = urllib.parse.urlencode(data).encode() if data else None
        req = urllib.request.Request(f"{self.base}{path}", data=body,
                                     headers={"Referer": self.base})
        with self.op.open(req, timeout=60) as r:
            return r.read().decode()


def rule_def(enabled: bool, feed_url: str) -> dict:
    return {
        "enabled": enabled,
        "mustContain": MUST_CONTAIN,
        "mustNotContain": MUST_NOT_CONTAIN,
        "useRegex": True,
        "episodeFilter": "",
        "smartFilter": False,
        "previouslyMatchedEpisodes": [],
        "affectedFeeds": [feed_url],
        "ignoreDays": 0,
        "lastMatch": "",
        "addPaused": False,
        "assignedCategory": CATEGORY,
        "savePath": SAVE_PATH,
        "torrentContentLayout": "Original",
        "torrentParams": {
            "category": CATEGORY,
            "save_path": SAVE_PATH,
            "tags": ["ratio-race"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", action="store_true", help="enable the auto-download rule")
    ap.add_argument("--disarm", action="store_true", help="disable it")
    ap.add_argument("--status", action="store_true", help="show current state only")
    args = ap.parse_args()

    pw, pk = qbm_password(), prowlarr_key()
    if not pw or not pk:
        print(f"secret resolution failed (qbit={len(pw)} prowlarr={len(pk)})", file=sys.stderr)
        return 2
    feed_url = f"{PROWLARR}/{INDEXER_ID}/api?apikey={pk}&t=search&cat=2000&extended=1"

    qb = Qbit(QBIT, pw)

    if args.status:
        rules = json.loads(qb.call("/api/v2/rss/rules") or "{}")
        feeds = json.loads(qb.call("/api/v2/rss/items?withData=false") or "{}")
        prefs = json.loads(qb.call("/api/v2/app/preferences") or "{}")
        r = rules.get(RULE_NAME)
        # A rule with enabled=True is NOT sufficient. qBittorrent has two global
        # master switches, both OFF by default, and with either off the rule sits
        # there looking armed while silently never grabbing anything.
        print(f"GLOBAL rss_processing_enabled       = {prefs.get('rss_processing_enabled')}")
        print(f"GLOBAL rss_auto_downloading_enabled = {prefs.get('rss_auto_downloading_enabled')}")
        print(f"GLOBAL rss_refresh_interval         = {prefs.get('rss_refresh_interval')} min")
        if not (prefs.get("rss_processing_enabled") and prefs.get("rss_auto_downloading_enabled")):
            print("  !! RSS subsystem is OFF — no rule can fire. Run with --arm.")
        print(f"feeds subscribed: {list(feeds.keys())}")
        if not r:
            print(f"rule {RULE_NAME!r}: ABSENT")
        else:
            print(f"rule {RULE_NAME!r}: enabled={r.get('enabled')} "
                  f"category={r.get('assignedCategory')} savePath={r.get('savePath')}")
            print(f"  mustNotContain={r.get('mustNotContain')!r}")
        return 0

    # Subscribe the feed (idempotent: qbit 409s on a duplicate path, which is fine)
    try:
        qb.call("/api/v2/rss/addFeed", {"url": feed_url, "path": FEED_NAME})
        print(f"feed subscribed as {FEED_NAME!r}")
    except urllib.error.HTTPError as e:
        print(f"feed add: HTTP {e.code} (already present is expected on re-run)")

    enabled = bool(args.arm)
    qb.call("/api/v2/rss/setRule", {
        "ruleName": RULE_NAME,
        "ruleDef": json.dumps(rule_def(enabled, feed_url)),
    })

    # The two global master switches. Both default to False, and a per-rule
    # enabled=True does nothing without them -- the rule reports as armed,
    # qBittorrent's own matchingArticles happily lists matches, and not one
    # byte is ever grabbed. Found the hard way: rule armed, 15 matching
    # articles confirmed by qbit itself, zero downloads.
    qb.call("/api/v2/app/setPreferences", {"json": json.dumps({
        "rss_processing_enabled": enabled,
        "rss_auto_downloading_enabled": enabled,
    })})
    prefs = json.loads(qb.call("/api/v2/app/preferences") or "{}")
    print(f"global rss_processing_enabled       = {prefs.get('rss_processing_enabled')}")
    print(f"global rss_auto_downloading_enabled = {prefs.get('rss_auto_downloading_enabled')}")
    state = "ARMED — grey will now grab new HDBits uploads" if enabled else "DISARMED (created, not grabbing)"
    print(f"rule {RULE_NAME!r} written: {state}")
    print(f"  category={CATEGORY} savePath={SAVE_PATH}")
    print(f"  mustContain    = {MUST_CONTAIN}")
    print(f"  mustNotContain = {MUST_NOT_CONTAIN}")
    print("  size is controlled by requiring an explicit codec tag (encodes only) —")
    print("  qBittorrent RSS rules have no size filter, and qbit-manage governs")
    print("  seeding limits AFTER a grab, never which torrents get grabbed.")
    if enabled:
        print("  REMINDER: qbit-manage must keep cleanup:false so nothing deletes "
              "a torrent before its HnR obligation is met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
