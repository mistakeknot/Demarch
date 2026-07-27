#!/usr/bin/env python3
"""Prefer freeleech releases, to protect tracker ratio (sylveste-fo1y).

On HDBits a freeleech grab costs no download credit and a halfleech grab costs
half, so preferring them is the highest-leverage per-grab ratio lever short of
cross-seeding. Prowlarr passes the tracker's flags through as `indexerFlags`, and
both arrs can score on them via IndexerFlagSpecification.

Measured on a sample of ~1600 releases before writing this:

    HDBits        45 G_Freeleech, 14 freeleech+internal, 61 G_Halfleech,
                  18 halfleech+internal, 5 unflagged
    TorrentLeech  295 G_Freeleech of 619
    Karagarga     0 flagged -- KG reports no flags at all, so this lever
                  simply does not apply there (its Prowlarr `freeleech`
                  field is a search FILTER, not a flag reporter)

HALFLEECH IS INCLUDED DELIBERATELY, and goes beyond a strict reading of the
brief. HDBits carries more halfleech than freeleech (79 vs 59 in the sample), so
scoring only full freeleech would capture under half the available benefit. It
is the same mechanism at half the weight and carries no extra risk.

SCORING. Freeleech +100, halfleech +50. Both sit above x265's +50-ish nudge, so
between two otherwise-equal releases the cheaper one wins -- and both sit far
below the 1500 assigned to DV/HDR10+/HDR, so ratio can never outrank picture
quality. That ordering is the whole point: this is a tie-breaker, not a
preference for worse video.

NOTE the enums differ between the two services and must not be shared:

    Radarr   1 G Freeleech   2 G Halfleech   256 G Freeleech75   512 G Freeleech25
    Sonarr   1 Freeleech     2 Halfleech      32 Freeleech75      64 Freeleech25

Freeleech and halfleech happen to coincide at 1 and 2; the partial tiers do not.
The tables below are per-service so a future edit cannot quietly get it wrong.

Dry-run by default; --apply is opt-in.
"""
import argparse
import json
import re
import urllib.error
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
RADARR = ("radarr", 7878)
SONARR = ("sonarr", 8989)
PROFILES = ("Best-Available", "Archival-Best")

# service -> [(format name, indexer-flag enum value, score)]
FORMATS = {
    "radarr": [("Freeleech", 1, 100), ("Halfleech", 2, 50)],
    "sonarr": [("Freeleech", 1, 100), ("Halfleech", 2, 50)],
}


def key(d):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/%s/config.xml" % (CFG, d)).read()).group(1).strip()


def api(svc, method, path, body=None):
    d, port = svc
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:%d/api/v3/%s" % (HOST, port, path),
                               data=data, method=method,
                               headers={"X-Api-Key": key(d), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=180).read()
    except urllib.error.HTTPError as e:
        print("      HTTP %s %s" % (e.code, e.read()[:250].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def ensure_format(svc, name, flag, apply_):
    existing = {c["name"]: c for c in (api(svc, "GET", "customformat") or [])}
    if name in existing:
        print("  %-10s custom format exists id=%d" % (name, existing[name]["id"]))
        return existing[name]
    if not apply_:
        print("  DRY-RUN would create %r (IndexerFlag=%d)" % (name, flag))
        return None
    cf = api(svc, "POST", "customformat", {
        "name": name,
        "includeCustomFormatWhenRenaming": False,
        "specifications": [{
            "name": name,
            "implementation": "IndexerFlagSpecification",
            "negate": False, "required": True,
            "fields": [{"name": "value", "value": flag}]}]})
    print("  %-10s created id=%s (IndexerFlag=%d)" % (name, (cf or {}).get("id"), flag))
    return cf


def score_on_profiles(svc, cf, score, apply_):
    if not cf:
        return
    for p in api(svc, "GET", "qualityprofile") or []:
        if p["name"] not in PROFILES:
            continue
        items = p.get("formatItems", [])
        hit = next((i for i in items if i.get("format") == cf["id"]), None)
        if hit and hit.get("score") == score:
            print("     %-16s already %+d" % (p["name"], score))
            continue
        if not apply_:
            print("     DRY-RUN %-16s -> %+d" % (p["name"], score))
            continue
        if hit:
            hit["score"] = score
        else:
            items.append({"format": cf["id"], "name": cf["name"], "score": score})
        p["formatItems"] = items
        if api(svc, "PUT", "qualityprofile/%d" % p["id"], p) is not None:
            print("     %-16s -> %+d" % (p["name"], score))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    for svc in (RADARR, SONARR):
        print("\n=== %s ===" % svc[0].upper())
        for name, flag, score in FORMATS[svc[0]]:
            cf = ensure_format(svc, name, flag, a.apply)
            score_on_profiles(svc, cf, score, a.apply)
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
