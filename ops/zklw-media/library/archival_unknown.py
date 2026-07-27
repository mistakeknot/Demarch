#!/usr/bin/env python3
"""Make Karagarga's archival catalogue grabbable (sylveste-ai77).

The problem: KG release names frequently carry no quality tag at all --
"Avaliha AKA First Graders 1984 Iran [Avaliha]" -- so Radarr parses quality as
`Unknown`, and every profile excludes Unknown. That rejects the majority of KG
results with "Unknown is not wanted in profile", precisely for the Curtis and
Kiarostami material where KG is the only source that exists.

Why `Unknown` must NOT be allowed on Best-Available: it is the catch-all for
anything unparseable, so allowing it library-wide would let untagged junk
satisfy a mainstream title that is merely waiting for a proper WEB-DL.

The fix is to scope it. `Archival-Best` already exists, is already what the
Curtis and Kiarostami import lists point at, and is currently used by almost
nothing because the 4K consolidation flattened every existing movie onto
Best-Available. So:

  1. Redefine Archival-Best as "Best-Available, plus Unknown". It previously
     also allowed Remux-2160p / HDTV-2160p, which contradicts the no-massive-
     remux doctrine and is meaningless for pre-HD material anyway.
  2. Have the two archival import lists tag what they own, so membership is
     declarative and self-maintaining rather than a hardcoded title list.
  3. Move only tagged, monitored, FILE-LESS movies onto Archival-Best. Skipping
     movies that already have a file is what guarantees nothing downgrades.
  4. Point the four non-archival lists at Best-Available; they still reference
     the retired UHD-Remux profile, so every newly-imported Villeneuve/Aster/
     Lanthimos/Gerwig title lands on a profile nothing else uses.

Unknown ranks lowest in Radarr's quality ordering, so a parseable release still
wins whenever one exists; Unknown is a fallback, not a preference. Radarr's
Unknown quality definition caps at 100 MB/min, and `AI Upscale` still scores
-10000, so the usual guards remain in force.

Dry-run by default; --apply is opt-in.
"""
import argparse
import json
import re
import urllib.error
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
BEST = "Best-Available"
ARCHIVAL = "Archival-Best"
ARCHIVAL_TAG = "archival"
ARCHIVAL_LISTS = ("Auteur: Adam Curtis", "Auteur: Abbas Kiarostami")
CUTOFF_FORMAT_SCORE = 1550


def key(d):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/%s/config.xml" % (CFG, d)).read()).group(1).strip()


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:7878/api/v3/%s" % (HOST, path),
                               data=data, method=method,
                               headers={"X-Api-Key": key("radarr"),
                                        "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=240).read()
    except urllib.error.HTTPError as e:
        print("      HTTP %s %s" % (e.code, e.read()[:250].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def allowed_names(profile):
    """Flatten a profile's allowed qualities, descending into group tiers."""
    out = set()
    for it in profile["items"]:
        q = it.get("quality")
        if q:
            if it.get("allowed"):
                out.add(q["name"])
        else:
            for s in it.get("items", []):
                if s.get("allowed"):
                    out.add(s["quality"]["name"])
    return out


def step1_profile(apply_):
    print("\n=== 1. Archival-Best := Best-Available + Unknown ===")
    profs = {p["name"]: p for p in api("GET", "qualityprofile") or []}
    best, arch = profs.get(BEST), profs.get(ARCHIVAL)
    if not best or not arch:
        print("  missing profile"); return None
    want = allowed_names(best) | {"Unknown"}
    have = allowed_names(arch)
    if have == want and arch.get("cutoffFormatScore") == CUTOFF_FORMAT_SCORE \
            and arch.get("cutoff") == best.get("cutoff"):
        print("  already correct (%d qualities, Unknown allowed)" % len(have))
        return arch["id"]
    print("  adding   : %s" % sorted(want - have))
    print("  removing : %s" % sorted(have - want))
    for it in arch["items"]:
        q = it.get("quality")
        if q:
            it["allowed"] = q["name"] in want
        else:
            for s in it.get("items", []):
                s["allowed"] = s["quality"]["name"] in want
            it["allowed"] = any(s["allowed"] for s in it.get("items", []))
    arch["cutoff"] = best["cutoff"]
    arch["cutoffFormatScore"] = CUTOFF_FORMAT_SCORE
    arch["minFormatScore"] = 0
    if not apply_:
        print("  DRY-RUN would update %s (cutoff=%s cutoffFmt=%d)"
              % (ARCHIVAL, best["cutoff"], CUTOFF_FORMAT_SCORE))
        return arch["id"]
    if api("PUT", "qualityprofile/%d" % arch["id"], arch) is not None:
        print("  updated %s: %d qualities, Unknown allowed, cutoffFmt=%d"
              % (ARCHIVAL, len(want), CUTOFF_FORMAT_SCORE))
    return arch["id"]


def step2_lists(arch_id, best_id, apply_):
    print("\n=== 2. import lists: tag the archival ones, retarget the rest ===")
    tags = {t["label"]: t["id"] for t in api("GET", "tag") or []}
    tid = tags.get(ARCHIVAL_TAG)
    if tid is None:
        if not apply_:
            print("  DRY-RUN would create tag %r" % ARCHIVAL_TAG)
        else:
            tid = (api("POST", "tag", {"label": ARCHIVAL_TAG}) or {}).get("id")
            print("  created tag %r id=%s" % (ARCHIVAL_TAG, tid))
    else:
        print("  tag %r exists id=%d" % (ARCHIVAL_TAG, tid))

    for l in api("GET", "importlist") or []:
        archival = l["name"] in ARCHIVAL_LISTS
        want_prof = arch_id if archival else best_id
        want_tags = sorted(set((l.get("tags") or []) + ([tid] if archival and tid else [])))
        if l.get("qualityProfileId") == want_prof and sorted(l.get("tags") or []) == want_tags:
            print("  %-28s ok" % l["name"][:28])
            continue
        if not apply_:
            print("  DRY-RUN %-28s prof %s->%s tags %s->%s"
                  % (l["name"][:28], l.get("qualityProfileId"), want_prof,
                     l.get("tags"), want_tags))
            continue
        l["qualityProfileId"] = want_prof
        l["tags"] = want_tags
        if api("PUT", "importlist/%d" % l["id"], l) is not None:
            print("  %-28s prof=%s tags=%s" % (l["name"][:28], want_prof, want_tags))
    if apply_:
        c = api("POST", "command", {"name": "ImportListSync"})
        print("  triggered ImportListSync (cmd %s)" % (c or {}).get("id"))
    return tid


def seerr(path):
    """Query Seerr, which already holds a working TMDb credential.

    Radarr applies an import list's tags only when it ADDS a movie, so a list
    sync will never retroactively tag the titles it imported before the tag
    existed. The filmographies therefore have to be resolved independently, and
    Seerr's person endpoint is the one TMDb-backed source already running here
    -- no new API key, and nothing new to keep in sync.
    """
    s = json.load(open("%s/jellyseerr/settings.json" % CFG))
    r = urllib.request.Request("http://%s:5055/api/v1/%s" % (HOST, path),
                               headers={"X-Api-Key": s["main"]["apiKey"]})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=120).read() or b"null")
    except urllib.error.HTTPError as e:
        print("      seerr HTTP %s %s" % (e.code, e.read()[:160].decode("utf8", "replace")))
        return None


def step2b_tag_filmographies(tid, apply_):
    print("\n=== 2b. tag the archival directors' filmographies ===")
    if tid is None:
        print("  no tag id (dry run) -- would resolve filmographies and tag matches")
        return
    wanted = set()
    for name, pid in (("Adam Curtis", 142618), ("Abbas Kiarostami", 119294)):
        cr = seerr("person/%d/combined_credits" % pid)
        if not cr:
            print("  %-18s LOOKUP FAILED" % name); continue
        ids = {c["id"] for c in cr.get("crew", [])
               if c.get("job") == "Director" and c.get("mediaType") == "movie"}
        print("  %-18s %d directed features/shorts" % (name, len(ids)))
        wanted |= ids
    if not wanted:
        print("  resolved nothing -- aborting tag step"); return
    movies = api("GET", "movie") or []
    todo = [m for m in movies if m.get("tmdbId") in wanted and tid not in (m.get("tags") or [])]
    print("  in library and untagged: %d" % len(todo))
    for m in todo:
        if not apply_:
            print("     DRY-RUN tag %-44s %s" % (m["title"][:44], m.get("year")))
            continue
        m["tags"] = sorted(set((m.get("tags") or []) + [tid]))
        if api("PUT", "movie/%d" % m["id"], m) is not None:
            print("     tagged %-44s %s" % (m["title"][:44], m.get("year")))


def step3_move(arch_id, tid, apply_):
    print("\n=== 3. move tagged, file-less movies onto Archival-Best ===")
    if tid is None:
        print("  no tag yet -- rerun after the list sync has tagged its movies")
        return
    movies = api("GET", "movie") or []
    tagged = [m for m in movies if tid in (m.get("tags") or [])]
    print("  movies carrying %r: %d" % (ARCHIVAL_TAG, len(tagged)))
    # Only file-less movies move. A movie that already has a file could be
    # re-evaluated against a wider quality set, and this must never cause a
    # downgrade of something already satisfied.
    todo = [m for m in tagged if not m.get("hasFile") and m["qualityProfileId"] != arch_id]
    skipped = [m for m in tagged if m.get("hasFile")]
    print("  already have a file, left alone: %d" % len(skipped))
    print("  to move: %d" % len(todo))
    for m in todo:
        if not apply_:
            print("     DRY-RUN %-46s %s" % (m["title"][:46], m.get("year")))
            continue
        m["qualityProfileId"] = arch_id
        if api("PUT", "movie/%d" % m["id"], m) is not None:
            print("     moved %-46s %s" % (m["title"][:46], m.get("year")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    profs = {p["name"]: p for p in api("GET", "qualityprofile") or []}
    best_id = profs[BEST]["id"]
    arch_id = step1_profile(a.apply)
    tid = step2_lists(arch_id, best_id, a.apply)
    step2b_tag_filmographies(tid, a.apply)
    step3_move(arch_id, tid, a.apply)
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
