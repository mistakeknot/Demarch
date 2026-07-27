#!/usr/bin/env python3
"""Generate recyclarr.yml from LIVE Radarr/Sonarr state.

Generated rather than hand-written so the YAML provably matches what is
deployed: `sync --preview` then reports no changes, which is the whole point of
mirroring. Hand-transcribing quality ladders is how drift gets introduced.

Four deliberate departures from the previous config, each load-bearing:

  * NO quality_definition. TRaSH's size recommendations would overwrite the
    250 MB/min maxSize caps that keep 50-80GB remuxes out. Sizes stay
    API-managed by consolidate_library.py.
  * delete_old_custom_formats: false. The 'AI Upscale' format (-10000) was
    created through the API; recyclarr can only declare formats that exist in
    the TRaSH guides, so it cannot re-create it and must not delete it.
  * reset_unmatched_scores: false. Enabled, it would zero any score recyclarr
    does not know about -- which is exactly the AI Upscale guard.
  * NO SDR penalty. Both profiles cascade to archival SD material where SDR is
    the only source that ever existed, and against min_format_score 0 a -2000
    penalty would reject every such release.

The 'uhd' instances are dropped: the 4K split was retired. Their presence also
broke the config outright, because recyclarr requires instance names to be
unique ACROSS services and both radarr and sonarr defined 'main' and 'uhd'.
"""
import json, re, sys, urllib.request
HOST = "100.123.250.67"
WANT = ("Best-Available", "Archival-Best")

TRASH = {
    "radarr": {"dv": "b337d6812e06c200ec9a2d3cfa9d20a7", "hdr10plus": "caa37d0df9c348912df1fb1d88f9273a",
               "hdr": "493b6d1dbec3c3364c59d7607f7e3405", "x265": "9170d55c319f4fe40da8711ba9d8050d"},
    "sonarr": {"dv": "7c3a61a9c6cb04f52f1544be6d44a026", "hdr10plus": "0c4b99df9206d2cfac3c05ab897dd62a",
               "hdr": "505d871304820ba7106b693be6fe4a9e", "x265": "c9eafd50846d299b862ca9bb6ea91950"},
}


def key(d):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("/home/mk/grey-media/config/%s/config.xml" % d).read()).group(1).strip()


def api(port, d, p):
    r = urllib.request.Request("http://%s:%d/api/v3/%s" % (HOST, port, p), headers={"X-Api-Key": key(d)})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())


def profiles_yaml(port, d):
    out = []
    for prof in api(port, d, "qualityprofile"):
        if prof["name"] not in WANT:
            continue
        cut = prof["cutoff"]
        cutname = None
        for i in prof["items"]:
            if i.get("quality") and i["quality"]["id"] == cut:
                cutname = i["quality"]["name"]
            if not i.get("quality") and i.get("id") == cut:
                cutname = i.get("name")
        out.append("      - name: %s" % prof["name"])
        out.append("        reset_unmatched_scores:")
        out.append("          enabled: false")
        out.append("        upgrade:")
        out.append("          allowed: %s" % str(prof["upgradeAllowed"]).lower())
        out.append("          until_quality: %s" % cutname)
        out.append("          until_score: 10000")
        out.append("        min_format_score: %s" % prof.get("minFormatScore", 0))
        out.append("        quality_sort: top")
        out.append("        qualities:")
        for i in reversed(prof["items"]):
            if not i.get("allowed"):
                continue
            if i.get("quality"):
                out.append("          - name: %s" % i["quality"]["name"])
            else:
                subs = [s["quality"]["name"] for s in i.get("items", []) if s.get("allowed")]
                out.append("          - name: %s" % i.get("name"))
                out.append("            qualities: [ %s ]" % ", ".join(subs))
    return "\n".join(out)


def formats_yaml(svc):
    t = TRASH[svc]
    return "\n".join([
        "    custom_formats:",
        "      # Dolby Vision / HDR10+ / HDR. On an OLED these are far more",
        "      # visible than the last 20 Mbps of bitrate, which is why they",
        "      # matter more here than any remux tier.",
        "      - trash_ids:",
        "          - %s  # DV Boost" % t["dv"],
        "          - %s  # HDR10+ Boost" % t["hdr10plus"],
        "          - %s  # HDR" % t["hdr"],
        "        assign_scores_to:",
        "          - name: Best-Available",
        "            score: 1500",
        "      - trash_ids:",
        "          - %s  # x265" % t["x265"],
        "        assign_scores_to:",
        "          - name: Best-Available",
        "            score: 50",
    ])


HEADER = '''# Recyclarr -- grey media server. REPO-OWNED: edit in the Sylveste repo at
# ops/zklw-media/config/recyclarr/recyclarr.yml and deploy with sync-to-grey.sh.
#
# Policy: best available quality, but NOT massive 4K Blu-ray rips. Remux-2160p
# is excluded from Best-Available (50-80GB untouched disc streams); 2160p
# ENCODES at ~15-30GB sit at the top instead. Radarr's native ordering already
# ranks 2160p encodes above 1080p remux, so only exclusions were needed.
#
# GENERATED FROM LIVE STATE so `recyclarr sync --preview` reports no changes.
# Regenerate with ops/zklw-media/config/recyclarr/generate.py after changing a
# profile through the API.
#
# Deliberately ABSENT, each for a reason:
#   quality_definition   -- would overwrite the 250 MB/min maxSize caps that
#                           keep oversized releases out. Sizes are API-managed.
#   SDR penalty          -- both profiles cascade to archival SD material where
#                           SDR is the only source that ever existed; against
#                           min_format_score 0 a -2000 penalty rejects them all.
#   uhd instances        -- the 4K split was retired. They also broke the config:
#                           recyclarr requires instance names unique ACROSS
#                           services, and 'main'/'uhd' were defined under both.
#
# API keys come from recyclarr.env (untracked, 0600 on grey) so no secret is
# ever committed or passed on a command line.
'''


def main():
    parts = [HEADER, "", "radarr:", "  radarr_main:",
             "    base_url: http://radarr:7878",
             "    api_key: !env_var RADARR_API_KEY",
             "    # false: 'AI Upscale' (-10000) was created via the API and cannot be",
             "    # expressed as a trash_id, so recyclarr must not delete it.",
             "    delete_old_custom_formats: false",
             "    quality_profiles:", profiles_yaml(7878, "radarr"), formats_yaml("radarr"),
             "", "sonarr:", "  sonarr_main:",
             "    base_url: http://sonarr:8989",
             "    api_key: !env_var SONARR_API_KEY",
             "    delete_old_custom_formats: false",
             "    quality_profiles:", profiles_yaml(8989, "sonarr"), formats_yaml("sonarr"), ""]
    open("/root/grey-ops/recyclarr.generated.yml", "w").write("\n".join(parts))
    print("wrote /root/grey-ops/recyclarr.generated.yml")


main()
