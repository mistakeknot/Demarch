#!/usr/bin/env python3
"""Apply the 2026-07-27 settings-audit fixes, in dependency order.

Ordering is not cosmetic. Step 1 must land before step 2: the moment Prowlarr
syncs the private trackers into Radarr, Radarr's `removeCompletedDownloads`
starts deleting torrents from qBittorrent after import -- cutting seeding short
against HDBits' 14-day and Karagarga's 30-day minimums. qbit-manage is the only
component allowed to delete torrents (every share_limits group is cleanup:false),
so doing these in the other order would create real hit-and-run exposure.

  1  sylveste-fuh3  Radarr qBittorrent removeCompletedDownloads -> False
  2  sylveste-0exj  tag 1 ("trackers") onto the Radarr/Sonarr Prowlarr apps
  3  sylveste-6c60  maxSize caps on Sonarr (previously Radarr-only)
  4  sylveste-re08  AI Upscale custom format in Sonarr at -10000
  5  sylveste-flkv  cutoffFormatScore 10000 -> 1550 on Best-Available

Dry-run by default; --apply is opt-in. Every API key is read server-side from
each service's own config, so no secret is ever passed as an argument.
"""
import argparse
import json
import re
import urllib.error
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
RADARR = ("radarr", 7878, "v3")
SONARR = ("sonarr", 8989, "v3")
PROWLARR = ("prowlarr", 9696, "v1")

PROFILE = "Best-Available"
ARCHIVAL = "Archival-Best"
TRACKERS_TAG = 1          # Prowlarr tag "trackers" -- HDBits / Karagarga / TorrentLeech
CUTOFF_FORMAT_SCORE = 1550
CAP = 250.0
# Mirrors Radarr's CAPPED set from consolidate_library.py, translated to
# Sonarr's tier names. Sonarr judges maxSize PER EPISODE, so 250 MB/min is
# ~15GB for an hour-long episode -- a backstop against mislabelled releases
# rather than a tight budget.
SONARR_CAPPED = {"Bluray-2160p", "WEBDL-2160p", "WEBRip-2160p", "HDTV-2160p",
                 "Bluray-2160p Remux",
                 "Bluray-1080p", "Bluray-1080p Remux"}
AI_UPSCALE_RE = r"\bAI[ ._-]?Upscale\b"


def key(d):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/%s/config.xml" % (CFG, d)).read()).group(1).strip()


def api(svc, method, path, body=None):
    d, port, ver = svc
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:%d/api/%s/%s" % (HOST, port, ver, path),
                               data=data, method=method,
                               headers={"X-Api-Key": key(d), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=180).read()
    except urllib.error.HTTPError as e:
        print("      HTTP %s %s" % (e.code, e.read()[:300].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def step1_removal(apply_):
    print("\n=== 1. sylveste-fuh3 :: Radarr must not delete torrents ===")
    for c in api(RADARR, "GET", "downloadclient") or []:
        if c.get("protocol") != "torrent":
            continue
        if not c.get("removeCompletedDownloads"):
            print("  %s already removeCompletedDownloads=False" % c["name"])
            continue
        if not apply_:
            print("  DRY-RUN %s removeCompletedDownloads True -> False" % c["name"])
            continue
        c["removeCompletedDownloads"] = False
        if api(RADARR, "PUT", "downloadclient/%d" % c["id"], c) is not None:
            print("  %s removeCompletedDownloads -> False" % c["name"])


def step2_indexer_tags(apply_):
    print("\n=== 2. sylveste-0exj :: let the live arrs see the private trackers ===")
    changed = False
    for a in api(PROWLARR, "GET", "applications") or []:
        # The 4K apps already carry the tag; they are retired but harmless.
        if a.get("name") not in ("Radarr", "Sonarr"):
            continue
        tags = list(a.get("tags") or [])
        if TRACKERS_TAG in tags:
            print("  %s already tagged trackers" % a["name"])
            continue
        if not apply_:
            print("  DRY-RUN %s tags %s -> %s" % (a["name"], tags, tags + [TRACKERS_TAG]))
            continue
        a["tags"] = tags + [TRACKERS_TAG]
        if api(PROWLARR, "PUT", "applications/%d" % a["id"], a) is not None:
            print("  %s tags -> %s" % (a["name"], a["tags"]))
            changed = True
    if changed and apply_:
        c = api(PROWLARR, "POST", "command", {"name": "ApplicationIndexerSync"})
        print("  triggered ApplicationIndexerSync (cmd %s)" % (c or {}).get("id"))


def step3_sonarr_caps(apply_):
    print("\n=== 3. sylveste-6c60 :: size caps on Sonarr ===")
    for qd in api(SONARR, "GET", "qualitydefinition") or []:
        name = qd["quality"]["name"]
        if name not in SONARR_CAPPED:
            continue
        if qd.get("maxSize") == CAP:
            print("  %-22s already capped at %s" % (name, CAP))
            continue
        if not apply_:
            print("  DRY-RUN cap %-22s maxSize %s -> %s MB/min" % (name, qd.get("maxSize"), CAP))
            continue
        qd["maxSize"] = CAP
        if api(SONARR, "PUT", "qualitydefinition/%d" % qd["id"], qd) is not None:
            print("  capped %-22s at %s MB/min" % (name, CAP))


def step4_sonarr_ai_upscale(apply_):
    print("\n=== 4. sylveste-re08 :: AI Upscale guard on Sonarr ===")
    cfs = {c["name"]: c for c in (api(SONARR, "GET", "customformat") or [])}
    cf = cfs.get("AI Upscale")
    if not cf:
        if not apply_:
            print("  DRY-RUN would create custom format 'AI Upscale' (%s)" % AI_UPSCALE_RE)
        else:
            cf = api(SONARR, "POST", "customformat", {
                "name": "AI Upscale",
                "includeCustomFormatWhenRenaming": False,
                "specifications": [{
                    "name": "AI Upscale",
                    "implementation": "ReleaseTitleSpecification",
                    "negate": False, "required": True,
                    "fields": [{"name": "value", "value": AI_UPSCALE_RE}]}]})
            print("  created custom format 'AI Upscale' id=%s" % (cf or {}).get("id"))
    else:
        print("  custom format 'AI Upscale' exists id=%d" % cf["id"])
    if not cf:
        return
    for p in api(SONARR, "GET", "qualityprofile") or []:
        if p["name"] not in (PROFILE, ARCHIVAL):
            continue
        items = p.get("formatItems", [])
        hit = next((i for i in items if i.get("format") == cf["id"]), None)
        if hit and hit.get("score") == -10000:
            print("  %-16s already scores AI Upscale -10000" % p["name"])
            continue
        if not apply_:
            print("  DRY-RUN score AI Upscale -10000 on %s" % p["name"])
            continue
        if hit:
            hit["score"] = -10000
        else:
            items.append({"format": cf["id"], "name": "AI Upscale", "score": -10000})
        p["formatItems"] = items
        if api(SONARR, "PUT", "qualityprofile/%d" % p["id"], p) is not None:
            print("  %-16s AI Upscale -> -10000" % p["name"])


def step5_cutoff_score(apply_):
    print("\n=== 5. sylveste-flkv :: reachable cutoffFormatScore ===")
    # 10000 is unreachable: the ceiling is 1500+1500+1500+50 and DV/HDR10+/HDR
    # rarely co-occur, so every title stayed permanently "below cutoff" and the
    # arrs never stopped hunting upgrades. 1550 = correct quality + any HDR
    # flavour + x265. Archival SD still cannot reach it and will keep searching;
    # that is inherent to scoring HDR on material that has none, and the quality
    # cutoff still bounds what actually gets grabbed.
    for svc in (RADARR, SONARR):
        for p in api(svc, "GET", "qualityprofile") or []:
            if p["name"] != PROFILE:
                continue
            if p.get("cutoffFormatScore") == CUTOFF_FORMAT_SCORE:
                print("  %-7s %s already at %d" % (svc[0], PROFILE, CUTOFF_FORMAT_SCORE))
                continue
            if not apply_:
                print("  DRY-RUN %-7s %s cutoffFormatScore %s -> %d" % (
                    svc[0], PROFILE, p.get("cutoffFormatScore"), CUTOFF_FORMAT_SCORE))
                continue
            p["cutoffFormatScore"] = CUTOFF_FORMAT_SCORE
            if api(svc, "PUT", "qualityprofile/%d" % p["id"], p) is not None:
                print("  %-7s %s cutoffFormatScore -> %d" % (svc[0], PROFILE, CUTOFF_FORMAT_SCORE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    step1_removal(a.apply)
    step2_indexer_tags(a.apply)
    step3_sonarr_caps(a.apply)
    step4_sonarr_ai_upscale(a.apply)
    step5_cutoff_score(a.apply)
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
