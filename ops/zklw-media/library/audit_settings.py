#!/usr/bin/env python3
"""Read-only audit of grey's request defaults / library management / ratio levers.

Reads every API key server-side from each service's own config, so no secret is
ever passed as an argument. Nothing here writes.
"""
import glob
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"


def xmlkey(d):
    p = "%s/%s/config.xml" % (CFG, d)
    return re.search(r"<ApiKey>([^<]+)</ApiKey>", open(p).read()).group(1).strip()


def get(port, path, k, ver="v3"):
    r = urllib.request.Request("http://%s:%d/api/%s/%s" % (HOST, port, ver, path),
                               headers={"X-Api-Key": k})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=60).read() or b"null")
    except Exception as e:
        return {"__error__": str(e)[:200]}


def hdr(s):
    print("\n" + "=" * 78)
    print("== %s" % s)
    print("=" * 78)


ARRS = [("radarr", 7878), ("sonarr", 8989)]

for name, port in ARRS:
    k = xmlkey(name)
    hdr("%s :: media management" % name.upper())
    mm = get(port, "config/mediamanagement", k)
    for f in ("copyUsingHardlinks", "importExtraFiles", "enableMediaInfo",
              "recycleBin", "recycleBinCleanupDays", "downloadPropersAndRepacks",
              "autoUnmonitorPreviouslyDownloadedMovies",
              "autoUnmonitorPreviouslyDownloadedEpisodes",
              "setPermissionsLinux", "minimumFreeSpaceWhenImporting",
              "rescanAfterRefresh", "skipFreeSpaceCheckWhenImporting"):
        if f in mm:
            print("  %-46s %s" % (f, mm[f]))

    hdr("%s :: download clients" % name.upper())
    dcc = get(port, "config/downloadclient", k)
    for f in ("enableCompletedDownloadHandling", "autoRedownloadFailed",
              "autoRedownloadFailedFromInteractiveSearch", "checkForFinishedDownloadInterval"):
        if f in dcc:
            print("  %-46s %s" % (f, dcc[f]))
    for c in get(port, "downloadclient", k) or []:
        if isinstance(c, dict):
            flds = {x["name"]: x.get("value") for x in c.get("fields", [])}
            print("  - %-16s proto=%-7s prio=%-3s removeComplete=%s removeFailed=%s cat=%s" % (
                c.get("name"), c.get("protocol"), c.get("priority"),
                c.get("removeCompletedDownloads"), c.get("removeFailedDownloads"),
                flds.get("movieCategory") or flds.get("tvCategory") or flds.get("category")))

    hdr("%s :: indexers (seed criteria = ratio/HnR levers)" % name.upper())
    for i in get(port, "indexer", k) or []:
        if not isinstance(i, dict):
            continue
        flds = {x["name"]: x.get("value") for x in i.get("fields", [])}
        print("  - %-30s %-7s prio=%-3s rss=%-5s auto=%-5s ia=%s" % (
            i.get("name", "")[:30], i.get("protocol"), i.get("priority"),
            i.get("enableRss"), i.get("enableAutomaticSearch"), i.get("enableInteractiveSearch")))
        seed = {kk: vv for kk, vv in flds.items()
                if "seed" in kk.lower() or "ratio" in kk.lower()}
        req = {kk: vv for kk, vv in flds.items()
               if kk in ("requiredFlags", "minimumSeeders", "downloadClientId", "categories")}
        if seed:
            print("        seed: %s" % seed)
        if req:
            print("        misc: %s" % req)

    hdr("%s :: delay profiles" % name.upper())
    for d in get(port, "delayprofile", k) or []:
        if isinstance(d, dict):
            print("  %s" % {kk: d.get(kk) for kk in
                            ("id", "enableUsenet", "enableTorrent", "preferredProtocol",
                             "usenetDelay", "torrentDelay", "bypassIfHighestQuality",
                             "bypassIfAboveCustomFormatScore", "minimumCustomFormatScore",
                             "order", "tags")})

    hdr("%s :: quality definitions (min / preferred / max MB-per-min)" % name.upper())
    for q in sorted(get(port, "qualitydefinition", k) or [],
                    key=lambda x: x.get("weight", 0) if isinstance(x, dict) else 0):
        if isinstance(q, dict):
            print("  %-22s min=%-7s pref=%-7s max=%s" % (
                q["quality"]["name"], q.get("minSize"), q.get("preferredSize"), q.get("maxSize")))

    hdr("%s :: custom formats + profile flags" % name.upper())
    cfs = {c["id"]: c["name"] for c in (get(port, "customformat", k) or []) if isinstance(c, dict)}
    print("  existing formats: %s" % sorted(cfs.values()))
    for p in get(port, "qualityprofile", k) or []:
        if not isinstance(p, dict):
            continue
        scored = {fi.get("name"): fi.get("score") for fi in p.get("formatItems", [])
                  if fi.get("score")}
        print("  - %-18s upgradeAllowed=%-5s cutoff=%-4s minFormatScore=%-5s "
              "cutoffFormatScore=%-6s minUpgradeFormatScore=%s" % (
                  p.get("name"), p.get("upgradeAllowed"), p.get("cutoff"),
                  p.get("minFormatScore"), p.get("cutoffFormatScore"),
                  p.get("minUpgradeFormatScore")))
        print("        scored: %s" % scored)

    hdr("%s :: release profiles" % name.upper())
    for rp in get(port, "releaseprofile", k) or []:
        if isinstance(rp, dict):
            print("  %s" % {kk: rp.get(kk) for kk in
                            ("name", "enabled", "required", "ignored", "indexerId", "tags")})

# ---------------------------------------------------------------- prowlarr
hdr("PROWLARR :: indexers")
try:
    pk = xmlkey("prowlarr")
    for i in get(9696, "indexer", pk, ver="v1") or []:
        if not isinstance(i, dict):
            continue
        flds = {x["name"]: x.get("value") for x in i.get("fields", [])}
        interesting = {kk: vv for kk, vv in flds.items()
                       if any(t in kk.lower() for t in
                              ("seed", "ratio", "freeleech", "flag", "filter", "limit"))}
        print("  - %-24s prio=%-3s enabled=%-5s proto=%s" % (
            i.get("name", "")[:24], i.get("priority"), i.get("enable"), i.get("protocol")))
        if interesting:
            print("        %s" % interesting)
    st = get(9696, "indexerstats", pk, ver="v1")
    if isinstance(st, dict):
        for row in st.get("indexers", []):
            print("  stats %-24s grabs=%-5s queries=%-6s fails=%s" % (
                row.get("indexerName", "")[:24], row.get("numberOfGrabs"),
                row.get("numberOfQueries"), row.get("numberOfFailedGrabs")))
except Exception as e:
    print("  prowlarr probe failed: %s" % e)

# ---------------------------------------------------------------- seerr
hdr("SEERR :: request defaults")
cands = glob.glob("%s/*/settings.json" % CFG) + glob.glob("%s/*/*/settings.json" % CFG)
sfile = next((c for c in cands if "seerr" in c.lower()), None)
print("  settings file: %s" % sfile)
if sfile:
    s = json.load(open(sfile))
    m = s.get("main", {})
    for f in ("defaultPermissions", "partialRequestsEnabled", "enableSpecialEpisodes",
              "movie4kEnabled", "series4kEnabled", "hideAvailable", "locale",
              "originalLanguage", "region", "streamingRegion"):
        if f in m:
            print("  main.%-28s %s" % (f, m[f]))
    for kind in ("radarr", "sonarr"):
        for srv in s.get(kind, []):
            print("  %s[%s] default=%s is4k=%s profile=%s rootFolder=%s "
                  "minAvail=%s tags=%s animeProfile=%s" % (
                      kind, srv.get("name"), srv.get("isDefault"), srv.get("is4k"),
                      srv.get("activeProfileName") or srv.get("activeProfileId"),
                      srv.get("activeDirectory"), srv.get("minimumAvailability"),
                      srv.get("tags"), srv.get("activeAnimeProfileId")))

# ---------------------------------------------------------------- qbit
hdr("QBITTORRENT :: preferences of interest")
qc = glob.glob("%s/qbittorrent/qBittorrent/qBittorrent.conf" % CFG) + \
     glob.glob("%s/**/qBittorrent.conf" % CFG, recursive=True)
if qc:
    txt = open(qc[0]).read()
    for line in txt.splitlines():
        if any(t in line for t in ("MaxRatio", "MaxSeedingTime", "GlobalMaxRatio", "Preallocation",
                                   "DiskWriteCacheSize", "MaxActive", "MaxConnec", "UploadSlots",
                                   "MaxUploads", "PortRangeMin", "Encryption", "AlternativeGlobal",
                                   "GlobalUP", "GlobalDL", "IgnoreLimits", "AnonymousMode",
                                   "QueueingSystemEnabled", "TempPathEnabled", "IncompleteFiles")):
            print("  %s" % line.strip())

hdr("QBIT-MANAGE :: share limits")
qm = glob.glob("%s/**/config.yml" % CFG, recursive=True)
for f in qm:
    if "qbit" in f.lower():
        print("  --- %s" % f)
        inside = False
        for line in open(f):
            if re.match(r"^share_limits:", line):
                inside = True
            elif inside and re.match(r"^\S", line):
                break
            if inside:
                print("  %s" % line.rstrip())

hdr("DISK / LIBRARY SIZES")
for cmd in ("df -h /data /home 2>/dev/null",
            "du -sh /data/* 2>/dev/null | sort -h | tail -20"):
    print("  $ %s" % cmd)
    try:
        print("\n".join("    " + l for l in subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300).stdout.splitlines()))
    except Exception as e:
        print("    failed: %s" % e)
