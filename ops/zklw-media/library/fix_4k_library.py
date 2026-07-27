#!/usr/bin/env python3
"""Make the 4K library actually 4K.

The dedicated 4K Radarr was running UHD-Remux, whose ladder falls back through
Remux-1080p / Bluray-1080p / WEB 1080p. That fallback is right for the main
library ("give me the best that exists") and wrong for a 4K shelf, where it lets
a 1080p release satisfy a 4K request. Result: /data/movies-4k held two films and
neither was 4K -- including a "1080p UHD BluRay" encode, which is 1920x1080
sourced from the UHD disc, so it carries DV/HDR10 and a 20GB size while not
being 4K at all.

UHD-Strict allows only genuine 2160p tiers. If no 2160p release exists, the 4K
library correctly stays empty rather than quietly filling with 1080p.

HDTV-2160p is excluded: 2160p broadcast captures are not what this shelf is for.
"""
import argparse, json, re, urllib.error, urllib.request
HOST = "100.123.250.67"
RADARR4K = ("radarr-4k", 7879)
SONARR4K = ("sonarr-4k", 8990)
STRICT = "UHD-Strict"
ALLOW_RADARR = {"Remux-2160p", "Bluray-2160p", "WEBDL-2160p", "WEBRip-2160p", "WEB 2160p"}
ALLOW_SONARR = {"Bluray-2160p Remux", "Bluray-2160p", "WEBDL-2160p", "WEBRip-2160p", "WEB 2160p"}


def key(d):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("/home/mk/grey-media/config/%s/config.xml" % d).read()).group(1).strip()


def call(svc, method, path, body=None):
    d, port = svc
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:%d/api/v3/%s" % (HOST, port, path), data=data, method=method,
                               headers={"X-Api-Key": key(d), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=180).read()
    except urllib.error.HTTPError as e:
        print("    HTTP %s %s" % (e.code, e.read()[:250].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def ensure_strict(svc, allow, cutoff_name, apply_):
    existing = {p["name"]: p for p in call(svc, "GET", "qualityprofile")}
    if STRICT in existing:
        print("  %s exists (id=%d)" % (STRICT, existing[STRICT]["id"]))
        return existing[STRICT]["id"]
    schema = call(svc, "GET", "qualityprofile/schema")
    cutoff = None
    for item in schema["items"]:
        q = item.get("quality")
        if q:
            item["allowed"] = q["name"] in allow
            if q["name"] == cutoff_name:
                cutoff = q["id"]
        else:
            subs = item.get("items", [])
            for s in subs:
                s["allowed"] = s["quality"]["name"] in allow
            item["allowed"] = any(s["allowed"] for s in subs)
            if item.get("name") == cutoff_name:
                cutoff = item["id"]
    if cutoff is None:
        print("  cutoff %r not found" % cutoff_name); return None
    schema.update({"name": STRICT, "upgradeAllowed": True, "cutoff": cutoff, "minFormatScore": 0})
    n = sum(1 for i in schema["items"] if i.get("allowed"))
    if not apply_:
        print("  DRY-RUN would create %s (%d tiers, all 2160p)" % (STRICT, n)); return None
    made = call(svc, "POST", "qualityprofile", schema)
    print("  created %s id=%d (%d tiers, all 2160p)" % (STRICT, made["id"], n))
    return made["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    print("=== radarr-4k ===")
    rid = ensure_strict(RADARR4K, ALLOW_RADARR, "Remux-2160p", a.apply)
    movies = call(RADARR4K, "GET", "movie") or []
    print("  library: %d movies, %d with files" % (len(movies), sum(1 for m in movies if m.get("hasFile"))))
    for m in movies:
        f = m.get("movieFile") or {}
        q = ((f.get("quality") or {}).get("quality") or {}).get("name")
        if m.get("hasFile") and q and "2160" not in q:
            print("    NOT 4K: %-34s %s  %s" % (m["title"][:34], m.get("year"), q))
    if rid and a.apply:
        for m in movies:
            if m["qualityProfileId"] != rid:
                m["qualityProfileId"] = rid
                call(RADARR4K, "PUT", "movie/%d" % m["id"], m)
        print("  moved %d movies to %s" % (len(movies), STRICT))
        sub = [m["id"] for m in movies if not m.get("hasFile") or
               "2160" not in (((m.get("movieFile") or {}).get("quality") or {}).get("quality") or {}).get("name", "")]
        if sub:
            c = call(RADARR4K, "POST", "command", {"name": "MoviesSearch", "movieIds": sub[:40]})
            print("  searching %d titles for true 2160p (cmd %s)" % (len(sub[:40]), (c or {}).get("id")))

    print("\n=== sonarr-4k ===")
    sid = ensure_strict(SONARR4K, ALLOW_SONARR, "Bluray-2160p Remux", a.apply)
    series = call(SONARR4K, "GET", "series") or []
    print("  library: %d series" % len(series))
    if sid and a.apply:
        for s in series:
            if s["qualityProfileId"] != sid:
                s["qualityProfileId"] = sid
                call(SONARR4K, "PUT", "series/%d" % s["id"], s)
        print("  moved %d series to %s" % (len(series), STRICT))

    if not a.apply:
        print("\nDRY RUN -- nothing changed.")
        return

    # Point Seerr's 4K servers at the strict profile so future 4K requests
    # cannot be satisfied by a 1080p release.
    st = json.load(open("/home/mk/grey-media/config/jellyseerr/settings.json"))
    apikey = st["main"]["apiKey"]
    for kind, newid in (("radarr", rid), ("sonarr", sid)):
        if not newid:
            continue
        r = urllib.request.Request("http://%s:5055/api/v1/settings/%s" % (HOST, kind),
                                   headers={"X-Api-Key": apikey})
        for srv in json.loads(urllib.request.urlopen(r, timeout=60).read()):
            if not srv.get("is4k"):
                continue
            srv["activeProfileId"] = newid
            srv["activeProfileName"] = STRICT
            sid_ = srv.pop("id")
            req = urllib.request.Request(
                "http://%s:5055/api/v1/settings/%s/%d" % (HOST, kind, sid_),
                data=json.dumps(srv).encode(), method="PUT",
                headers={"X-Api-Key": apikey, "Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=60)
                print("  seerr %s 4K server -> %s" % (kind, STRICT))
            except urllib.error.HTTPError as e:
                print("  seerr %s FAILED %s %s" % (kind, e.code, e.read()[:200].decode("utf8", "replace")))


main()
