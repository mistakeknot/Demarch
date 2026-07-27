#!/usr/bin/env python3
"""Assess whether grey's seeding stock can be cross-seeded (sylveste-aado.5).

Cross-seeding means announcing data you ALREADY hold to a second tracker that
carries a torrent of byte-identical content. Done right it is the best ratio
lever there is: upload credit on two trackers for zero extra disk and zero extra
download. Done wrong it is a ban.

The whole question is whether the overlap exists. Two trackers carrying the same
FILM is worthless -- cross-seed needs the same FILE. HDBits is HD-only with
heavy internal encoding; Karagarga specialises in rare and arthouse material,
much of it DVD-sourced. The prior is that overlap is small, but the prior is not
evidence, so this measures it.

Method: sample torrents grey already seeds, search Prowlarr for each title, and
count hits on a DIFFERENT tracker whose size matches. Exact size equality is a
strong proxy for identical content -- not proof (a cross-seed tool would confirm
by piece hashes) but sufficient to decide whether the overlap is worth tooling.

Queries are paced. Private trackers care about query volume, and the point of
this exercise is to protect standing on them.

Read-only. This script changes nothing; it produces a verdict.
"""
import collections
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
SAMPLE_PER_TRACKER = 22
PACE_SECONDS = 4
# Exact equality is too strict: trackers sometimes differ by a stray NFO or
# padding file. 0.5% tolerance keeps genuine matches without inviting noise.
SIZE_TOLERANCE = 0.005


def prowlarr_key():
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/prowlarr/config.xml" % CFG).read()).group(1).strip()


def qbit():
    cfg = yaml.safe_load(open("%s/qbit-manage/config.yml" % CFG))
    q = cfg["qbt"]
    host = "http://%s:8080" % HOST
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(urllib.request.Request(
        host + "/api/v2/auth/login",
        data=urllib.parse.urlencode({"username": q.get("user"),
                                     "password": q.get("pass")}).encode(),
        headers={"Referer": host}), timeout=30).read()
    return json.loads(op.open(host + "/api/v2/torrents/info", timeout=120).read())


def search(term, key):
    url = "http://%s:9696/api/v1/search?%s" % (
        HOST, urllib.parse.urlencode({"query": term, "type": "search"}))
    r = urllib.request.Request(url, headers={"X-Api-Key": key})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=180).read() or b"[]")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return []


def clean(name):
    """Reduce a torrent name to something a tracker search will match."""
    n = re.sub(r"\.(mkv|mp4|avi|m4v)$", "", name, flags=re.I)
    n = re.sub(r"[._]", " ", n)
    n = re.sub(r"\[.*?\]|\(.*?\)", " ", n)
    m = re.match(r"(.*?)(19\d{2}|20\d{2})", n)
    if m:
        n = "%s %s" % (m.group(1), m.group(2))
    return re.sub(r"\s+", " ", n).strip()[:70]


def main():
    key = prowlarr_key()
    tor = qbit()
    by = collections.defaultdict(list)
    for t in tor:
        tag = next((x for x in (t.get("tags") or "").split(", ")
                    if x in ("hdbits", "karagarga", "torrentleech")), None)
        if tag:
            by[tag].append(t)
    print("seeding stock: %s" % {k: len(v) for k, v in by.items()})

    results = collections.Counter()
    hits = []
    for tag in ("hdbits", "karagarga"):
        stock = by.get(tag, [])[:SAMPLE_PER_TRACKER]
        print("\n=== sampling %d %s torrents ===" % (len(stock), tag))
        for t in stock:
            term = clean(t["name"])
            if not term:
                continue
            res = search(term, key)
            other = [r for r in res
                     if (r.get("indexer") or "").lower() != tag
                     and (r.get("indexer") or "").lower() in ("hdbits", "karagarga",
                                                              "torrentleech")]
            match = [r for r in other
                     if t["size"] and abs(r.get("size", 0) - t["size"]) / t["size"] <= SIZE_TOLERANCE]
            results["%s_searched" % tag] += 1
            if match:
                results["%s_crossable" % tag] += 1
                hits.append((tag, t["name"][:44], match[0].get("indexer"),
                             match[0].get("size", 0) / 1024 ** 3))
            print("  %-46s other-tracker hits=%-3d size-match=%d"
                  % (t["name"][:46], len(other), len(match)))
            time.sleep(PACE_SECONDS)

    print("\n" + "=" * 70)
    print("VERDICT DATA")
    for tag in ("hdbits", "karagarga"):
        s = results["%s_searched" % tag]
        c = results["%s_crossable" % tag]
        if s:
            print("  %-11s %d/%d sampled torrents have a size-matched twin elsewhere (%.0f%%)"
                  % (tag, c, s, 100.0 * c / s))
    print("\n  cross-seedable examples:")
    for tag, name, idx, gb in hits[:12]:
        print("     %-10s %-44s -> %s (%.2f GB)" % (tag, name, idx, gb))
    if not hits:
        print("     NONE found in the sample")


main()
