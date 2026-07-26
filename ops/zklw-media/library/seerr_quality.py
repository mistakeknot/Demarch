#!/usr/bin/env python3
"""Point Seerr's DEFAULT (non-4K) Radarr/Sonarr at a 4K-remux-first profile.

The problem: Seerr routes an ordinary request to the non-4K instance, which was
pinned to "Streaming 1080p" -- a profile that caps at Bluray-1080p, excludes
remux entirely, and has upgradeAllowed=false. A 4K remux was therefore
unreachable unless the requester explicitly ticked the 4K box, and once a title
landed at 1080p it could never improve.

UHD-Remux is the stated preference expressed as a ladder:
  Remux-2160p > Bluray-2160p > WEB 2160p > Remux-1080p > Bluray-1080p > WEB 1080p
with upgrades enabled, so it takes the best thing available now and climbs
toward a 2160p remux as better releases appear.

The API key is read from Seerr's own settings.json at call time and never passed
as an argument. Only the non-4K servers are touched; the dedicated 4K instances
already use UHD-Remux and are left alone.
"""
import argparse, json, re, urllib.error, urllib.request

SETTINGS = "/home/mk/grey-media/config/jellyseerr/settings.json"
HOST = "100.123.250.67"
BASE = "http://%s:5055" % HOST
TARGET = "UHD-Remux"


def arr_profiles(kind, port):
    """Quality profiles straight from the arr instance (the authority)."""
    k = re.search(r"<ApiKey>([^<]+)</ApiKey>",
                  open("/home/mk/grey-media/config/%s/config.xml" % kind).read()).group(1).strip()
    r = urllib.request.Request("http://%s:%d/api/v3/qualityprofile" % (HOST, port),
                               headers={"X-Api-Key": k})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())


def apikey():
    return json.load(open(SETTINGS))["main"]["apiKey"]


def api(method, path, body=None):
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=d, method=method,
                               headers={"X-Api-Key": apikey(), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=90).read()
    except urllib.error.HTTPError as e:
        print("   HTTP %s %s" % (e.code, e.read()[:300].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    for kind, port in (("radarr", 7878), ("sonarr", 8989)):
        servers = api("GET", "/api/v1/settings/%s" % kind) or []
        for srv in servers:
            tag = "4K" if srv.get("is4k") else "default"
            if srv.get("is4k"):
                print("  [%s] %-10s %-8s leaving on %r" % (kind, srv["name"], tag, srv.get("activeProfileName")))
                continue
            # Resolve the target profile id from the live instance rather than
            # assuming id 7 -- profile ids differ between Radarr and Sonarr.
            # Asking the arr directly rather than via Seerr's proxy endpoint:
            # the proxy 404s for Sonarr, and the arr is the authority regardless.
            profiles = arr_profiles(kind, port)
            match = next((p for p in profiles if p["name"] == TARGET), None)
            if not match:
                print("  [%s] %-10s NO %r profile found" % (kind, srv["name"], TARGET))
                continue
            if srv.get("activeProfileId") == match["id"]:
                print("  [%s] %-10s already on %s" % (kind, srv["name"], TARGET))
                continue
            print("  [%s] %-10s %-8s %r -> %r (id %s -> %s)" % (
                kind, srv["name"], tag, srv.get("activeProfileName"), TARGET,
                srv.get("activeProfileId"), match["id"]))
            if not a.apply:
                continue
            srv["activeProfileId"] = match["id"]
            srv["activeProfileName"] = match["name"]
            # Seerr rejects the payload if it carries `id` -- the route treats it
            # as read-only and 400s. Send the body without it.
            sid = srv.pop("id")
            ok = api("PUT", "/api/v1/settings/%s/%d" % (kind, sid), srv)
            print("        %s" % ("applied" if ok is not None else "FAILED -- not applied"))
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
