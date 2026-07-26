#!/usr/bin/env python3
"""Remove two classes of bad grab and stop them recurring.

1. WRONG SERIES. Adam Curtis's "The Living Dead" (1995) fuzzy-matched releases of
   "The Living and the Dead" (2016 BBC One drama). Both are BBC, both have a
   3-episode S01, and the titles differ by one word -- Sonarr accepted it. Fixed
   by blocklisting the grabs and adding a release profile that rejects the
   colliding string, scoped by TAG to the Curtis series so the 2016 show remains
   grabbable if it is ever actually wanted.

2. FAKE 4K. "Prisoners.2013.BluRay.2160p.AI.Upscale...DV.HDR10+" is a 1080p
   source machine-upscaled and relabelled as 2160p. It satisfies a 2160p-first
   profile on paper while being worse than the honest 1080p remux. Fixed by
   blocklisting it and adding a custom format that scores AI upscales into the
   ground.

Note: recyclarr owns UHD-Remux's custom formats with delete_old_custom_formats,
so the AI-upscale format below must also be mirrored into recyclarr.yml or a
future recyclarr run will drop it.
"""
import argparse, json, re, urllib.error, urllib.request
HOST = "100.123.250.67"
BAD_SERIES_TERM = "Living and the Dead"
UPSCALE_RE = r"upscale"


def key(s):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("/home/mk/grey-media/config/%s/config.xml" % s).read()).group(1).strip()


def call(svc, port, method, path, body=None):
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:%d/api/v3/%s" % (HOST, port, path), data=d, method=method,
                               headers={"X-Api-Key": key(svc), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=180).read()
    except urllib.error.HTTPError as e:
        print("    HTTP %s %s" % (e.code, e.read()[:250].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


rad = lambda m, p, b=None: call("radarr", 7878, m, p, b)
son = lambda m, p, b=None: call("sonarr", 8989, m, p, b)


def purge(which, fn, port, pattern, apply_):
    q = fn("GET", "queue?pageSize=200")
    hits = [r for r in q.get("records", []) if re.search(pattern, r.get("title", ""), re.I)]
    seen = set()
    for r in hits:
        if r.get("downloadId") in seen:
            continue
        seen.add(r.get("downloadId"))
        if not apply_:
            print("  DRY-RUN would blocklist+remove: %s" % r.get("title", "")[:70]); continue
        fn("DELETE", "queue/%d?removeFromClient=true&blocklist=true&skipRedownload=false" % r["id"])
        print("  removed+blocklisted: %s" % r.get("title", "")[:70])
    if not hits:
        print("  (%s: nothing matching %r in queue)" % (which, pattern))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    print("=== 1. wrong-series grabs (sonarr) ===")
    purge("sonarr", son, 8989, BAD_SERIES_TERM.replace(" ", "[. ]"), a.apply)

    print("\n=== 2. AI-upscale grabs (radarr) ===")
    purge("radarr", rad, 7878, UPSCALE_RE, a.apply)

    print("\n=== 3. guard: sonarr release profile scoped to Curtis series ===")
    series = {s["tvdbId"]: s for s in son("GET", "series")}
    target = series.get(85504)
    if not target:
        print("  The Living Dead (tvdb 85504) not in library")
    else:
        tags = {t["label"]: t["id"] for t in son("GET", "tag")}
        tid = tags.get("curtis-strict")
        if tid is None and a.apply:
            tid = son("POST", "tag", {"label": "curtis-strict"})["id"]
            print("  created tag curtis-strict (%s)" % tid)
        if a.apply and tid is not None and tid not in target.get("tags", []):
            target["tags"] = list(target.get("tags", [])) + [tid]
            son("PUT", "series/%d" % target["id"], target)
            print("  tagged %s" % target["title"])
        existing = [p for p in (son("GET", "releaseprofile") or [])
                    if p.get("name") == "Curtis strict title"]
        if existing:
            print("  release profile already present")
        elif not a.apply:
            print("  DRY-RUN would add release profile ignoring %r" % BAD_SERIES_TERM)
        else:
            son("POST", "releaseprofile", {
                "name": "Curtis strict title", "enabled": True,
                "required": [], "ignored": [BAD_SERIES_TERM],
                "tags": [tid] if tid else [], "indexerId": 0})
            print("  added release profile ignoring %r (tag-scoped)" % BAD_SERIES_TERM)

    print("\n=== 4. guard: radarr custom format for AI upscales ===")
    cfs = {c["name"]: c for c in rad("GET", "customformat")}
    if "AI Upscale" in cfs:
        print("  custom format already present")
        cf = cfs["AI Upscale"]
    elif not a.apply:
        print("  DRY-RUN would create 'AI Upscale' custom format"); cf = None
    else:
        cf = rad("POST", "customformat", {
            "name": "AI Upscale", "includeCustomFormatWhenRenaming": False,
            "specifications": [{
                "name": "AI Upscale", "implementation": "ReleaseTitleSpecification",
                "negate": False, "required": True,
                "fields": [{"name": "value", "value": r"\bAI[ ._-]?Upscale\b"}]}]})
        print("  created custom format 'AI Upscale' (id=%s)" % (cf or {}).get("id"))

    if cf and a.apply:
        for prof in rad("GET", "qualityprofile"):
            if prof["name"] not in ("UHD-Remux", "Archival-Best"):
                continue
            items = prof.get("formatItems", [])
            hit = next((i for i in items if i.get("format") == cf["id"]), None)
            if hit is None:
                items.append({"format": cf["id"], "name": "AI Upscale", "score": -10000})
            else:
                hit["score"] = -10000
            prof["formatItems"] = items
            rad("PUT", "qualityprofile/%d" % prof["id"], prof)
            print("  scored AI Upscale -10000 in %s" % prof["name"])

    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
