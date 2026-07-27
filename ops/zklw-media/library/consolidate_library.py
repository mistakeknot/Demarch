#!/usr/bin/env python3
"""Collapse the 4K/non-4K split into ONE library at best-available quality.

The split cost a checkbox per request and stored some films twice, and its only
real justification -- "4K lives over here" -- disappeared once the main library
started preferring 2160p anyway.

"Best available, but not massive 4K Blu-ray rips" is expressed as:

  EXCLUDED  Remux-2160p   the untouched UHD disc stream, 50-80GB. This is the
                          thing being ruled out. (Mad Max remux = 50.1GB vs a
                          6.8GB WEB-DL for the same film.)
  EXCLUDED  HDTV-2160p    2160p broadcast capture, not worth the bytes.
  TOP       Bluray-2160p / WEB 2160p    real 4K as an ENCODE, ~15-30GB.
  THEN      Remux-1080p / Bluray-1080p / WEB 1080p
  THEN      720p, DVD, 576p/480p, SDTV   so archival material still resolves.

Radarr's own quality ordering already ranks 2160p encodes above 1080p remux, so
the ladder needs no custom ordering -- only the right exclusions.

A maxSize cap on the 2160p tiers acts as a backstop: an oversized release that
mislabels itself as an encode still gets rejected on size.
"""
import argparse, json, re, urllib.error, urllib.request
HOST = "100.123.250.67"
RADARR = ("radarr", 7878)
SONARR = ("sonarr", 8989)
RADARR4K = ("radarr-4k", 7879)
SONARR4K = ("sonarr-4k", 8990)
PROFILE = "Best-Available"

# Everything NOT listed here is allowed. Remux-2160p is the headline exclusion.
RADARR_EXCLUDE = {"Unknown", "WORKPRINT", "CAM", "TELESYNC", "TELECINE", "REGIONAL",
                  "DVDSCR", "BR-DISK", "Raw-HD", "DVD-R", "Remux-2160p", "HDTV-2160p"}
SONARR_EXCLUDE = {"Unknown", "Raw-HD", "Bluray-2160p Remux", "HDTV-2160p"}
# MB per minute. ~250 MB/min is roughly 30GB for a 2h film; a UHD remux runs
# 400-700 and is excluded by tier anyway, so this mainly catches mislabels.
#
# Remux-1080p and Bluray-1080p are capped too, and that is not belt-and-braces:
# a 1080p remux of Amelie turned up at 44.7GB (~366 MB/min), which is massive
# AND only 1080p -- worse value than the 4K rips being excluded. Excluding the
# tier outright would lose good 20-30GB remuxes, so the size cap is the right
# instrument here rather than the allow-list.
CAP_2160P = 250.0
CAPPED = {"Bluray-2160p", "WEBDL-2160p", "WEBRip-2160p", "Remux-1080p", "Bluray-1080p"}


def key(d):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("/home/mk/grey-media/config/%s/config.xml" % d).read()).group(1).strip()


def call(svc, method, path, body=None):
    d, port = svc
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:%d/api/v3/%s" % (HOST, port, path), data=data, method=method,
                               headers={"X-Api-Key": key(d), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=240).read()
    except urllib.error.HTTPError as e:
        print("    HTTP %s %s" % (e.code, e.read()[:250].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def ensure_profile(svc, exclude, cutoff_name, apply_):
    existing = {p["name"]: p for p in call(svc, "GET", "qualityprofile")}
    if PROFILE in existing:
        print("  %s exists (id=%d)" % (PROFILE, existing[PROFILE]["id"]))
        return existing[PROFILE]["id"]
    schema = call(svc, "GET", "qualityprofile/schema")
    cutoff = None
    for item in schema["items"]:
        q = item.get("quality")
        if q:
            item["allowed"] = q["name"] not in exclude
            if q["name"] == cutoff_name:
                cutoff = q["id"]
        else:
            subs = item.get("items", [])
            for s in subs:
                s["allowed"] = s["quality"]["name"] not in exclude
            item["allowed"] = any(s["allowed"] for s in subs)
            if item.get("name") == cutoff_name:
                cutoff = item["id"]
    if cutoff is None:
        print("  cutoff %r missing" % cutoff_name); return None
    schema.update({"name": PROFILE, "upgradeAllowed": True, "cutoff": cutoff, "minFormatScore": 0})
    n = sum(1 for i in schema["items"] if i.get("allowed"))
    if not apply_:
        print("  DRY-RUN would create %s (%d tiers, top=%s)" % (PROFILE, n, cutoff_name)); return None
    made = call(svc, "POST", "qualityprofile", schema)
    print("  created %s id=%d (%d tiers, top=%s)" % (PROFILE, made["id"], n, cutoff_name))
    return made["id"]


def cap_sizes(svc, apply_):
    for qd in call(svc, "GET", "qualitydefinition"):
        if qd["quality"]["name"] not in CAPPED:
            continue
        if qd.get("maxSize") == CAP_2160P:
            continue
        if not apply_:
            print("  DRY-RUN cap %-14s maxSize %s -> %s MB/min" % (
                qd["quality"]["name"], qd.get("maxSize"), CAP_2160P)); continue
        qd["maxSize"] = CAP_2160P
        call(svc, "PUT", "qualitydefinition/%d" % qd["id"], qd)
        print("  capped %-14s at %s MB/min" % (qd["quality"]["name"], CAP_2160P))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    print("=== 1. stop the 4K instances grabbing ===")
    for svc, kind in ((RADARR4K, "movie"), (SONARR4K, "series")):
        q = call(svc, "GET", "queue?pageSize=200") or {}
        seen = set()
        for r in q.get("records", []):
            if r.get("downloadId") in seen:
                continue
            seen.add(r.get("downloadId"))
            if not a.apply:
                print("  DRY-RUN would cancel: %s" % r.get("title", "")[:70]); continue
            call(svc, "DELETE", "queue/%d?removeFromClient=true&blocklist=false" % r["id"])
            print("  cancelled: %s" % r.get("title", "")[:70])
        items = call(svc, "GET", kind) or []
        if a.apply:
            for m in items:
                if m.get("monitored"):
                    m["monitored"] = False
                    call(svc, "PUT", "%s/%d" % (kind, m["id"]), m)
            print("  unmonitored %d %s in %s" % (len(items), kind, svc[0]))
        else:
            print("  DRY-RUN would unmonitor %d %s in %s" % (len(items), kind, svc[0]))

    print("\n=== 2. unified profile ===")
    rid = ensure_profile(RADARR, RADARR_EXCLUDE, "Bluray-2160p", a.apply)
    sid = ensure_profile(SONARR, SONARR_EXCLUDE, "Bluray-2160p", a.apply)

    print("\n=== 3. size backstop ===")
    cap_sizes(RADARR, a.apply)

    print("\n=== 4. AI-upscale guard on the new profile ===")
    cfs = {c["name"]: c for c in call(RADARR, "GET", "customformat")}
    cf = cfs.get("AI Upscale")
    if cf and rid and a.apply:
        prof = call(RADARR, "GET", "qualityprofile/%d" % rid)
        items = prof.get("formatItems", [])
        hit = next((i for i in items if i.get("format") == cf["id"]), None)
        if hit:
            hit["score"] = -10000
        else:
            items.append({"format": cf["id"], "name": "AI Upscale", "score": -10000})
        prof["formatItems"] = items
        call(RADARR, "PUT", "qualityprofile/%d" % rid, prof)
        print("  AI Upscale scored -10000 on %s" % PROFILE)
    elif not a.apply:
        print("  DRY-RUN would score AI Upscale -10000 on %s" % PROFILE)

    print("\n=== 5. migrate whole library onto %s ===" % PROFILE)
    for svc, kind, pid in ((RADARR, "movie", rid), (SONARR, "series", sid)):
        items = call(svc, "GET", kind) or []
        moved = sum(1 for m in items if m["qualityProfileId"] != pid)
        if not a.apply or not pid:
            print("  DRY-RUN would move %d/%d %s" % (moved, len(items), kind)); continue
        for m in items:
            if m["qualityProfileId"] != pid:
                m["qualityProfileId"] = pid
                call(svc, "PUT", "%s/%d" % (kind, m["id"]), m)
        print("  moved %d/%d %s onto %s" % (moved, len(items), kind, PROFILE))

    print("\n=== 6. rescue titles that exist ONLY in the 4K instances ===")
    # These were requested as 4K and never existed in the main library. Simply
    # unmonitoring the 4K instance would orphan them -- they would silently
    # never download anywhere. They have to be carried across.
    main_ids = {m["tmdbId"] for m in (call(RADARR, "GET", "movie") or [])}
    orphans = [m for m in (call(RADARR4K, "GET", "movie") or []) if m["tmdbId"] not in main_ids]
    print("  %d movies only in radarr-4k" % len(orphans))
    root = call(RADARR, "GET", "rootfolder")[0]["path"]
    added = []
    for m in orphans:
        if not a.apply or not rid:
            print("     DRY-RUN would carry over %-40s %s" % (m["title"][:40], m.get("year")))
            continue
        full = call(RADARR, "GET", "movie/lookup/tmdb?tmdbId=%d" % m["tmdbId"])
        if not full:
            print("     lookup failed: %s" % m["title"]); continue
        full.update({"qualityProfileId": rid, "rootFolderPath": root, "monitored": True,
                     "minimumAvailability": "released", "addOptions": {"searchForMovie": False}})
        if call(RADARR, "POST", "movie", full):
            added.append(m)
            print("     carried over %-40s %s" % (m["title"][:40], m.get("year")))
    if added and a.apply:
        ids = [x["id"] for x in (call(RADARR, "GET", "movie") or [])
               if x["tmdbId"] in {o["tmdbId"] for o in added}]
        c = call(RADARR, "POST", "command", {"name": "MoviesSearch", "movieIds": ids})
        print("  searching %d carried-over titles (cmd %s)" % (len(ids), (c or {}).get("id")))

    withfile = [m for m in orphans if m.get("hasFile")]
    if withfile:
        print("\n  NOTE: %d carried-over title(s) still have their file under /data/movies-4k."
              % len(withfile))
        for m in withfile:
            print("     %s (%s) -- file stays put until the 4K dirs are merged" % (m["title"], m.get("year")))

    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
