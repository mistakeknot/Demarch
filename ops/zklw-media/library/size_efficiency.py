#!/usr/bin/env python3
"""Make "best quality per byte" expressible (sylveste-3g1t).

The 250 MB/min caps stop bloat. Nothing expressed the other half — preferring
the *efficient* release — and the minSize floors were actively rejecting it.

Measured before this change, via interactive search:

    Dune              9.5 GB and 12.7 GB 2160p x265 DV HDR  rejected, min 15.4 GB
    Blade Runner 2049 9.9 GB and 11.3 GB 2160p DV HDR       rejected, min 16.3 GB
    Arrival           8.0 GB 2160p x265 HDR (Tigole)        rejected, min 11.6 GB
    Midsommar         11.2 GB 2160p x265 HDR                rejected, min 14.6 GB
    Poor Things       4.5 GB 2160p WEBRip x265              rejected, min 4.8 GB

Those are exactly the releases a size-conscious library wants. A 155-minute Dune
at 9.5 GB is 63 MB/min; the floor demanded 102.

The floors cannot simply go to zero: the same searches turned up a 1.71 GB
"2160p UHD BluRay" for Hereditary (13.8 MB/min), which is not a 4K source in any
meaningful sense. So the floors move to roughly half the credible-encode
bitrate — low enough to admit a good HEVC encode, high enough that a sub-2 GB
"2160p" still fails.

`preferredSize` is the positive half. Radarr and Sonarr rank releases *within a
quality tier* by proximity to it, so it is what actually chooses between a 15 GB
and a 30 GB encode of the same film. Left null — as it was on every HD tier —
nothing preferred the smaller, and the biggest release under the cap tended to
win. The values below sit at a good-encode bitrate rather than at the cap.

Units are MB/min; multiply by 0.1333 for Mbps. Changing quality definitions does
NOT retroactively re-grab: RSS surfaces only newly-posted releases, and the back
catalogue is re-evaluated only by an explicit search. So this is safe to apply
to a populated library.

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

# tier -> (minSize, preferredSize).  None = leave the existing value alone.
# maxSize is untouched here; consolidate_library.py / apply_audit_fixes.py own it.
RADARR_SIZES = {
    # 2160p. 45 MB/min ~= 6 Mbps: below that a 2160p claim is not credible.
    # Preferred 130 ~= 17 Mbps, a strong HEVC 4K encode -- roughly 16 GB for a
    # 2h film, against the 250 cap's 30 GB.
    "Bluray-2160p":  (45.0, 130.0),
    "WEBDL-2160p":   (25.0, 100.0),
    "WEBRip-2160p":  (25.0, 100.0),
    # 1080p. Good x265 1080p runs 3-6 GB for a 2h film = 25-50 MB/min; the old
    # 50.8 floor rejected the whole band.
    "Bluray-1080p":  (22.0, 60.0),
    "WEBDL-1080p":   (None, 50.0),
    "WEBRip-1080p":  (None, 50.0),
    "HDTV-1080p":    (None, 50.0),
    # Remux is by definition untouched video; preferring "small" is meaningless,
    # so preferred sits near the cap and the floor is left where it is.
    "Remux-1080p":   (None, 200.0),
    # Excluded by Best-Available, so nothing can be grabbed from these tiers.
    # Set anyway as defence in depth: a future profile edit that re-allows one
    # must not silently reopen a tier with no size preference at all.
    "HDTV-2160p":    (None, 100.0),
    "Remux-2160p":   (None, 400.0),
}

SONARR_SIZES = {
    "Bluray-2160p":       (45.0, 130.0),
    "WEBDL-2160p":        (20.0, 100.0),
    "WEBRip-2160p":       (20.0, 100.0),
    "Bluray-1080p":       (22.0, 60.0),
    "WEBDL-1080p":        (None, 50.0),
    "WEBRip-1080p":       (None, 50.0),
    "HDTV-1080p":         (None, 50.0),
    "Bluray-1080p Remux": (None, 200.0),
    # Excluded by Best-Available; set for the same defence-in-depth reason.
    # preferredSize must not exceed maxSize -- Sonarr accepts the PUT but
    # silently drops the value, so 400 against this tier's 250 cap left it null.
    "HDTV-2160p":         (None, 100.0),
    "Bluray-2160p Remux": (None, 250.0),
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


def apply_sizes(svc, table, apply_):
    print("\n=== %s ===" % svc[0].upper())
    print("  %-22s %-18s %-18s %s" % ("tier", "min", "preferred", "max"))
    for qd in api(svc, "GET", "qualitydefinition") or []:
        name = qd["quality"]["name"]
        if name not in table:
            continue
        want_min, want_pref = table[name]
        cur_min, cur_pref = qd.get("minSize"), qd.get("preferredSize")
        new_min = cur_min if want_min is None else want_min
        if cur_min == new_min and cur_pref == want_pref:
            print("  %-22s %-18s %-18s ok" % (name, cur_min, cur_pref))
            continue
        arrow = lambda a, b: ("%s" % a) if a == b else ("%s -> %s" % (a, b))
        print("  %-22s %-18s %-18s %s" % (
            name, arrow(cur_min, new_min), arrow(cur_pref, want_pref),
            "" if apply_ else "(dry-run)"))
        if not apply_:
            continue
        qd["minSize"] = new_min
        qd["preferredSize"] = want_pref
        api(svc, "PUT", "qualitydefinition/%d" % qd["id"], qd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    apply_sizes(RADARR, RADARR_SIZES, a.apply)
    apply_sizes(SONARR, SONARR_SIZES, a.apply)
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
