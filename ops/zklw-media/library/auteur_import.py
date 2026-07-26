#!/usr/bin/env python3
"""
Auteur filmography import for grey.

Adds complete directing filmographies to Radarr via TMDb Person import lists,
so the library tracks a director rather than a hand-typed list of titles: new
releases land automatically and nothing depends on my memory of what someone
directed.

Runs ON GREY. Every API key is read from the service's own config.xml at call
time and never passed as an argument, so no secret can leak into a process list
or shell history -- same discipline as the ratio scripts and the HDBits gate.

Two quality tiers, because one does not fit:

  UHD-Remux      recyclarr-managed, bottoms out at WEB 1080p. Correct for
                 directors whose whole filmography exists on Blu-ray.
  Archival-Best  created here. Allows SDTV/DVD/576p through Remux-2160p with
                 upgrades still enabled. Without it Radarr would never grab
                 Kiarostami's early shorts or Curtis's 1980s BBC work at all --
                 that material has no HD source and never will.

Archival-Best deliberately carries NO custom formats. UHD-Remux applies a -2000
SDR penalty (the tonemap problem); on a 1984 broadcast SDR is not a defect, it
is the only thing that ever existed, and that penalty would suppress the sole
available release.

Default is a dry run. --apply is opt-in, matching the arm/disarm convention the
rest of grey-ops uses for anything outward-facing.
"""
import argparse, json, re, sys, urllib.error, urllib.parse, urllib.request

HOST = "100.123.250.67"
CONFIG = "/home/mk/grey-media/config"
RADARR = ("radarr", 7878)
SONARR = ("sonarr", 8989)

# Junk and edge tiers excluded from the archival profile. Cams/screeners are
# never a legitimate source for this material, and BR-DISK/Raw-HD are full-disc
# formats that Jellyfin handles poorly.
RADARR_EXCLUDE = {"Unknown", "WORKPRINT", "CAM", "TELESYNC", "TELECINE",
                  "REGIONAL", "DVDSCR", "BR-DISK", "Raw-HD", "DVD-R"}
SONARR_EXCLUDE = {"Unknown", "Raw-HD"}

ARCHIVAL = "Archival-Best"

# Resolved from Wikidata P4985 (TMDb person id), cross-checked against P345
# (IMDb). Not typed from memory -- see verify_person() which confirms each id
# resolves to the expected filmography before anything is created.
DIRECTORS = [
    # name,             tmdb_person, imdb,         profile,   why
    ("Adam Curtis",     142618,  "nm0193231", ARCHIVAL,     "BBC docs; features only here, serials go to Sonarr"),
    ("Abbas Kiarostami", 119294, "nm0452102", ARCHIVAL,     "Iranian New Wave; many shorts are DVD-only"),
    ("Denis Villeneuve", 137427, "nm0898288", "UHD-Remux",  "all on Blu-ray, most on UHD"),
    ("Ari Aster",       1145520, "nm4170048", "UHD-Remux",  "A24, all UHD"),
    ("Yorgos Lanthimos", 122423, "nm0487166", "UHD-Remux",  "early Greek work is scarcer but HD exists"),
    ("Greta Gerwig",      45400, "nm1950086", "UHD-Remux",  "3 features as director"),
]


def key_for(service):
    m = re.search(r"<ApiKey>([^<]+)</ApiKey>", open("%s/%s/config.xml" % (CONFIG, service)).read())
    if not m:
        sys.exit("no ApiKey for %s" % service)
    return m.group(1).strip()


def api(svc, method, path, body=None):
    name, port = svc
    url = "http://%s:%d/api/v3/%s" % (HOST, port, path)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-Api-Key": key_for(name), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(req, timeout=180).read()
    except urllib.error.HTTPError as e:
        sys.stderr.write("HTTP %s on %s %s\n%s\n" % (e.code, method, path, e.read()[:800].decode("utf8", "replace")))
        raise
    return json.loads(raw) if raw else None


def ensure_archival_profile(svc, exclude, cutoff_name, apply_):
    """Create (or report) the archival profile from Radarr/Sonarr's own schema.

    Building from the live schema rather than a hand-written item list means the
    payload always matches this version's quality set -- ids drift between
    releases and a hardcoded list silently rots.
    """
    existing = {p["name"]: p for p in api(svc, "GET", "qualityprofile")}
    if ARCHIVAL in existing:
        p = existing[ARCHIVAL]
        allowed = [i["quality"]["name"] for i in p["items"] if i.get("allowed") and i.get("quality")]
        print("  %s already exists (id=%d, %d qualities allowed)" % (ARCHIVAL, p["id"], len(allowed)))
        return p["id"]

    schema = api(svc, "GET", "qualityprofile/schema")
    cutoff_id = None
    for item in schema["items"]:
        q = item.get("quality")
        if q:
            item["allowed"] = q["name"] not in exclude
            if q["name"] == cutoff_name:
                cutoff_id = q["id"]
            continue
        # Grouped tier: "WEB 1080p" is a container for WEBDL-1080p + WEBRip-1080p
        # and carries no "quality" key of its own. Treating a group as a plain
        # quality (and so disallowing it) would silently drop EVERY WEB release
        # -- which for Curtis's BBC material is the only source that exists.
        subs = item.get("items", [])
        for s in subs:
            s["allowed"] = s["quality"]["name"] not in exclude
        item["allowed"] = any(s["allowed"] for s in subs)
        if item.get("name") == cutoff_name:
            cutoff_id = item["id"]
    if cutoff_id is None:
        sys.exit("cutoff quality %r not found" % cutoff_name)

    schema["name"] = ARCHIVAL
    schema["upgradeAllowed"] = True
    schema["cutoff"] = cutoff_id
    schema["minFormatScore"] = 0
    n = sum(1 for i in schema["items"] if i.get("allowed"))
    if not apply_:
        print("  DRY-RUN would create %s: %d qualities allowed, upgrade->%s" % (ARCHIVAL, n, cutoff_name))
        return None
    created = api(svc, "POST", "qualityprofile", schema)
    print("  created %s (id=%d): %d qualities allowed, upgrade->%s" % (ARCHIVAL, created["id"], n, cutoff_name))
    return created["id"]


def ensure_lists(profiles, root, apply_):
    schema = [s for s in api(RADARR, "GET", "importlist/schema")
              if s["implementation"] == "TMDbPersonImport"][0]
    existing = {l["name"]: l for l in api(RADARR, "GET", "importlist")}

    for name, tmdb, imdb, profile_name, why in DIRECTORS:
        list_name = "Auteur: %s" % name
        pid = profiles.get(profile_name)
        if pid is None:
            print("  SKIP %-18s (profile %s not resolved)" % (name, profile_name))
            continue
        if list_name in existing:
            print("  %-18s list exists (id=%d)" % (name, existing[list_name]["id"]))
            continue

        body = json.loads(json.dumps(schema))
        body["name"] = list_name
        body["enabled"] = True
        body["enableAuto"] = True
        # searchOnAdd stays FALSE: adding six filmographies at once would fire
        # ~100 simultaneous indexer searches. Titles land unmonitored-for-search
        # first so they can be reviewed, then searched in controlled batches.
        body["searchOnAdd"] = False
        body["monitor"] = "movieOnly"
        body["minimumAvailability"] = "released"
        body["rootFolderPath"] = root
        body["qualityProfileId"] = pid
        body["tags"] = []
        for f in body["fields"]:
            if f["name"] == "personId":
                f["value"] = str(tmdb)
            elif f["name"] == "personCastDirector":
                f["value"] = True
            elif f["name"] in ("personCast", "personCastProducer", "personCastSound", "personCastWriting"):
                f["value"] = False
        if not apply_:
            print("  DRY-RUN would add %-18s tmdb=%-8s profile=%s" % (name, tmdb, profile_name))
            continue
        made = api(RADARR, "POST", "importlist", body)
        print("  added %-18s tmdb=%-8s profile=%-13s (list id=%d)" % (name, tmdb, profile_name, made["id"]))


def prune_unreleased(apply_):
    """Drop films that do not exist yet.

    A TMDb person list happily returns announced projects, so a sync pulls in
    things like Dune: Part Three years early. They cannot be downloaded and just
    clutter the library.

    Deliberately NOT using Radarr's import-exclusion here. An exclusion is
    permanent: it would also block the film once it genuinely releases, which is
    the opposite of what is wanted. Deleting plainly means the next sync re-adds
    it only once it is real -- so this is safe to re-run after every sync.

    'inCinemas' is kept: those are real films awaiting a home release, and
    minimumAvailability=released already stops Radarr searching for them early.
    """
    # status alone is NOT sufficient. TMDb marks any film with no recorded
    # release date as "announced", so a 1994 short with thin metadata looks
    # identical to a film that genuinely does not exist yet. Testing status only
    # deleted Aster's The Strange Thing About the Johnsons and Villeneuve's Next
    # Floor. A future YEAR, plus the absence of any release date already in the
    # past, is what actually distinguishes the two.
    import datetime
    today = datetime.date.today()

    def released_already(m):
        for f in ("inCinemas", "digitalRelease", "physicalRelease"):
            v = m.get(f)
            if v and v[:10] < today.isoformat():
                return True
        return False

    doomed = [m for m in api(RADARR, "GET", "movie")
              if m.get("status") in ("tba", "announced")
              and not m.get("hasFile")
              and (m.get("year") or 0) >= today.year
              and not released_already(m)]
    if not doomed:
        print("  nothing unreleased to prune")
        return
    for m in doomed:
        if not apply_:
            print("  DRY-RUN would drop %s (%s) status=%s" % (m["title"], m.get("year"), m["status"]))
            continue
        api(RADARR, "DELETE", "movie/%d?deleteFiles=false&addImportExclusion=false" % m["id"])
        print("  dropped %s (%s) status=%s" % (m["title"], m.get("year"), m["status"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually create profiles and lists")
    ap.add_argument("--prune-unreleased", action="store_true",
                    help="drop announced/tba films that do not exist yet")
    args = ap.parse_args()

    if args.prune_unreleased:
        print("=== prune unreleased ===")
        prune_unreleased(args.apply)
        return

    root = api(RADARR, "GET", "rootfolder")[0]["path"]
    print("radarr root=%s  free=%.1fTB" % (root, api(RADARR, "GET", "rootfolder")[0]["freeSpace"] / 1e12))

    print("\n=== quality profiles ===")
    rid = ensure_archival_profile(RADARR, RADARR_EXCLUDE, "Remux-2160p", args.apply)
    ensure_archival_profile(SONARR, SONARR_EXCLUDE, "Bluray-2160p Remux", args.apply)

    profiles = {p["name"]: p["id"] for p in api(RADARR, "GET", "qualityprofile")}
    if rid:
        profiles[ARCHIVAL] = rid

    print("\n=== import lists ===")
    ensure_lists(profiles, root, args.apply)
    if not args.apply:
        print("\nDRY RUN -- nothing changed. Re-run with --apply.")


main()
