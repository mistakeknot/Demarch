#!/usr/bin/env python3
"""Adam Curtis's multi-part BBC serials -> Sonarr, plus profile corrections.

His work splits across two apps: feature-length pieces (Bitter Lake,
HyperNormalisation, It Felt Like a Kiss) are movies and come in through the
Radarr TMDb person list; the multi-part serials are TV and must be added here.

tvdbIds are pinned rather than resolved by search at runtime, because search is
actively dangerous for this catalogue -- "Pandora's Box" returns a 2016
true-crime series first and "The Living Dead" returns The Walking Dead. Each id
below was confirmed as BBC Two with the right year before being written down.
"""
import argparse, json, re, urllib.error, urllib.request
HOST = "100.123.250.67"
ARCHIVAL = "Archival-Best"

# tvdbId, title, year -- all confirmed BBC Two / BBC iPlayer
SERIALS = [
    (81168,  "Pandora's Box", 1992),
    (85504,  "The Living Dead", 1995),
    (81170,  "The Mayfair Set", 1999),
    (80447,  "The Trap: What Happened to Our Dream of Freedom", 2007),
    (248988, "All Watched Over by Machines of Loving Grace", 2011),
    (425179, "Russia 1985-1999: TraumaZone", 2022),
]
# Already present; they were on HD/streaming profiles that cannot match a
# 1990s PAL broadcast source.
RETUNE_SERIES = [79362, 79374, 396488]
# Radarr: Curtis features sitting on Ultra-HD, which allows 2160p ONLY. No BBC
# documentary from this era exists in 2160p, so they would search forever.
RETUNE_MOVIES = ["Bitter Lake", "HyperNormalisation"]


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


son = lambda m, p, b=None: call("sonarr", 8989, m, p, b)
rad = lambda m, p, b=None: call("radarr", 7878, m, p, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    sp = {p["name"]: p["id"] for p in son("GET", "qualityprofile")}
    rp = {p["name"]: p["id"] for p in rad("GET", "qualityprofile")}
    root = son("GET", "rootfolder")[0]["path"]
    have = {s["tvdbId"]: s for s in son("GET", "series")}
    print("sonarr root=%s  Archival-Best=%s" % (root, sp.get(ARCHIVAL)))

    print("\n=== add serials ===")
    for tvdb, title, year in SERIALS:
        if tvdb in have:
            print("  %-48s already present" % title[:48]); continue
        if not a.apply:
            print("  DRY-RUN would add %-40s (%s) tvdb=%s" % (title[:40], year, tvdb)); continue
        full = son("GET", "series/lookup?term=tvdb:%d" % tvdb)
        if not full:
            print("  %-48s lookup FAILED" % title[:48]); continue
        s = full[0]
        s.update({"qualityProfileId": sp[ARCHIVAL], "rootFolderPath": root,
                  "monitored": True, "seasonFolder": True,
                  "addOptions": {"monitor": "all", "searchForMissingEpisodes": False}})
        made = son("POST", "series", s)
        print("  %-48s added (%s)" % (title[:48], made["title"] if made else "FAILED"))

    print("\n=== retune existing Curtis serials -> %s ===" % ARCHIVAL)
    for tvdb in RETUNE_SERIES:
        s = have.get(tvdb)
        if not s:
            print("  tvdb=%s not in library" % tvdb); continue
        if s["qualityProfileId"] == sp[ARCHIVAL]:
            print("  %-48s already %s" % (s["title"][:48], ARCHIVAL)); continue
        if not a.apply:
            print("  DRY-RUN would retune %-40s" % s["title"][:40]); continue
        s["qualityProfileId"] = sp[ARCHIVAL]
        son("PUT", "series/%d" % s["id"], s)
        print("  %-48s -> %s" % (s["title"][:48], ARCHIVAL))

    print("\n=== retune Curtis features in Radarr -> %s ===" % ARCHIVAL)
    movies = rad("GET", "movie")
    for name in RETUNE_MOVIES:
        for m in movies:
            if m["title"].lower() == name.lower():
                if m["qualityProfileId"] == rp[ARCHIVAL]:
                    print("  %-48s already %s" % (name, ARCHIVAL)); break
                if not a.apply:
                    print("  DRY-RUN would retune %-40s" % name); break
                m["qualityProfileId"] = rp[ARCHIVAL]
                rad("PUT", "movie/%d" % m["id"], m)
                print("  %-48s -> %s" % (name, ARCHIVAL)); break
        else:
            print("  %-48s NOT FOUND in radarr" % name)
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
