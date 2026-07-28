#!/usr/bin/env python3
"""Adopt the KG folders that only exist in the seeding tree.

Jellyfin's Movies library scans BOTH /data/movies (the Radarr root) and
/data/Movies (the KG seeding tree). kg_adopt hardlinks between them, so an
adopted film has one inode under two names -- and Jellyfin, which has no
cross-path dedup, shows it twice. That is the bulk of the duplicate tiles.

The fix is to stop scanning the seeding tree. The obstacle is that a minority of
KG folders were never adopted, so dropping the path would delete those films
from the library's view. This closes that gap: it finds the folders whose video
inode exists ONLY under /data/Movies, matches each to TMDb, adds it to Radarr
and hardlinks it into place. Then the path can be dropped losing nothing.

kg_adopt already tried and gave up on these -- they are its `review` cases. It
requires an exact normalised title match against a candidate list built from the
folder name, and KG folder names defeat that in specific ways:

    "Ah-ga-ssi AKA The Handmaiden (2016)"   romanised title first, English AKA
    "Touchez pas au grisbi [+Extras] (1954)"  bracket junk before the year
    "Dead Souls AKA Les Ames mortes (2018)"   both sides are real titles

So this searches Radarr's TMDb lookup with EVERY title form the folder offers,
pools the candidates, and accepts only when they converge on exactly one tmdbId.
Convergence across independent search terms is what makes it safe -- not the
year window, which is deliberately loose because KG, TMDb and the release
filename routinely disagree by a year on older films.

Anything ambiguous is printed for a human. Never a silent top hit.

Dry-run by default; --apply is opt-in.
"""
import argparse
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
SEED = "/data/Movies"
LIB = "/data/movies"
VIDEO = (".mkv", ".mp4", ".avi", ".m4v", ".mpg", ".mpeg", ".ts", ".wmv", ".mov")
MIN_SIZE = 200 * 1024 ** 2
ADD_PROFILE = 9          # Archival-Best: the profile that tolerates Unknown
YEAR_SLACK = 2
# Advisory, not disqualifying -- we supply the movieId explicitly, so Radarr
# failing to parse a title out of a KG filename tells us nothing we did not
# already handle. Anything else still blocks. (Same allow-list as
# kg_review_force.py, deliberately.)
ALLOWED_REJECTIONS = {"unknown movie", "no audio tracks detected"}


def key():
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/radarr/config.xml" % CFG).read()).group(1).strip()


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:7878/api/v3%s" % (HOST, path),
                               data=data, method=method,
                               headers={"X-Api-Key": key(), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=300).read()
    except urllib.error.HTTPError as e:
        print("      HTTP %s %s" % (e.code, e.read()[:200].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def video_inodes(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.lower().endswith(VIDEO):
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size > MIN_SIZE:
                    out.setdefault(st.st_ino, []).append(p)
    return out


def orphan_dirs():
    """Top-level /data/Movies folders holding a video the library cannot see."""
    lib, seed = video_inodes(LIB), video_inodes(SEED)
    only = set(seed) - set(lib)
    dirs = {}
    for ino in only:
        for p in seed[ino]:
            d = p[len(SEED) + 1:].split("/")[0]
            dirs.setdefault(d, []).append((ino, p))
    return dirs


def title_forms(dirname):
    """Every title the folder name plausibly offers, plus its year."""
    m = re.search(r"\((\d{4})\)\s*$", dirname)
    if m:
        year, stem = int(m.group(1)), dirname[:m.start()]
    else:
        m2 = re.search(r"\b(19\d{2}|20\d{2})\b", dirname)
        if not m2:
            return [], None
        year, stem = int(m2.group(1)), dirname[:m2.start()]
    stem = re.sub(r"\[[^\]]*\]", " ", stem)          # [+Extras]
    stem = re.sub(r"\.(mkv|mp4|avi|m4v)$", "", stem, flags=re.I)
    stem = re.sub(r"[._]", " ", stem)
    parts = [re.sub(r"\s+", " ", p).strip(" -(")
             for p in re.split(r"\bAKA\b", stem, flags=re.I)]
    return [p for p in parts if p], year


def resolve(forms, year):
    """Pool candidates from every title form; accept only a single tmdbId."""
    want = {norm(f) for f in forms}
    uniq = {}
    for term in forms:
        for c in (api("/movie/lookup?term=" + urllib.parse.quote("%s %d" % (term, year))) or []):
            titles = {norm(c.get("title")), norm(c.get("originalTitle"))}
            titles |= {norm(t.get("title")) for t in (c.get("alternateTitles") or [])
                       if isinstance(t, dict)}
            if titles & want and abs((c.get("year") or 0) - year) <= YEAR_SLACK:
                uniq[c["tmdbId"]] = c
    return list(uniq.values())


MULTIPART = re.compile(r"\b(cd|disc|disk|pt)[ ._-]?[12ab]\b", re.I)


def pick_file(files, forms):
    """Choose which video in the folder is actually the feature.

    Largest-wins is wrong here and quietly mis-files things: the KG folder
    "No Data Plan (2019)" also contains At.Land.1944.720p.x264.mkv, which is
    bigger AND is a different film that has its own folder. Radarr's parser
    does not save us either -- given the folder as context it reports BOTH
    files as "No Data Plan".

    So the filename decides. A file whose name carries one of the folder's own
    title forms is the feature; size only breaks ties among those.
    """
    named = [(ino, p) for ino, p in files
             if any(norm(f) and norm(f) in norm(os.path.basename(p)) for f in forms)]
    pool = named or files
    if all(MULTIPART.search(os.path.basename(p)) for _, p in pool):
        return None
    pool = [(ino, p) for ino, p in pool if not MULTIPART.search(os.path.basename(p))]
    return max(pool, key=lambda x: os.path.getsize(x[1]))[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    mm = api("/config/mediamanagement") or {}
    if not mm.get("copyUsingHardlinks"):
        print("REFUSING: copyUsingHardlinks is off -- importMode=copy would "
              "duplicate the seeding copy instead of linking to it.")
        return
    print("hardlinks enabled; importMode=copy will link, not duplicate\n")

    dirs = orphan_dirs()
    print("KG folders whose film the library cannot see: %d\n" % len(dirs))
    by_tmdb = {m.get("tmdbId"): m for m in (api("/movie") or [])}
    done = amb = none = failed = 0
    report = {"ambiguous": [], "none": []}

    for d, files in sorted(dirs.items()):
        forms, year = title_forms(d)
        if not forms:
            none += 1
            report["none"].append((d, "no year in the folder name"))
            continue
        hits = resolve(forms, year)
        if len(hits) != 1:
            if hits:
                amb += 1
                report["ambiguous"].append((d, [(c["title"], c["year"]) for c in hits][:4]))
            else:
                none += 1
                report["none"].append((d, "no TMDb match on %s" % (forms,)))
            continue
        c = hits[0]
        path = pick_file(files, forms)
        if path is None:
            none += 1
            report["none"].append((d, "multi-part (cd1/cd2) -- Radarr cannot represent this"))
            continue

        if not a.apply:
            print("  DRY-RUN %-50s -> %s (%s)" % (d[:50], c["title"], c["year"]))
            done += 1
            continue

        mv = by_tmdb.get(c["tmdbId"])
        if not mv:
            c.update({"qualityProfileId": ADD_PROFILE, "rootFolderPath": LIB,
                      "monitored": False, "minimumAvailability": "released",
                      "addOptions": {"searchForMovie": False}})
            mv = api("/movie", "POST", c)
            if not mv:
                failed += 1
                continue
        # Take quality/languages from Radarr's own manual-import listing rather
        # than from /parse. Parsing a bare name like "Touchez pas au Grisbi .avi"
        # yields a quality object Radarr then silently refuses to import with.
        item = None
        for i in (api("/manualimport?folder=" + urllib.parse.quote(os.path.join(SEED, d))
                      + "&filterExistingFiles=true") or []):
            if i.get("path") == path:
                item = i
                break
        if item is None:
            failed += 1
            print("  FAILED  %-46s not offered by manualimport" % d[:46])
            continue
        blocking = [r.get("reason") if isinstance(r, dict) else r
                    for r in (item.get("rejections") or [])]
        blocking = [r for r in blocking if str(r).lower() not in ALLOWED_REJECTIONS]
        if blocking:
            failed += 1
            print("  FAILED  %-46s %s" % (d[:46], blocking))
            continue
        f = {"path": path, "movieId": mv["id"], "quality": item["quality"],
             "languages": item.get("languages") or []}
        if item.get("releaseGroup"):
            f["releaseGroup"] = item["releaseGroup"]
        cmd = api("/command", "POST", {"name": "ManualImport", "importMode": "copy",
                                       "files": [f]})
        for _ in range(90):
            st = api("/command/%d" % cmd["id"]) or {}
            if st.get("status") in ("completed", "failed", "aborted"):
                break
            time.sleep(1)
        mf = api("/moviefile?movieId=%d" % mv["id"]) or []
        if any(os.path.exists(x["path"]) and os.stat(x["path"]).st_ino == os.stat(path).st_ino
               for x in mf):
            done += 1
            print("  ADOPTED %-46s nlink=%d %s" % (d[:46], os.stat(path).st_nlink, c["title"][:22]))
        else:
            failed += 1
            print("  FAILED  %-46s %s" % (d[:46], st.get("status")))

    print("\n" + "=" * 70)
    print("adopted=%d ambiguous=%d unmatched=%d failed=%d" % (done, amb, none, failed))
    for k, label in (("ambiguous", "more than one candidate -- needs a human"),
                     ("none", "no match")):
        if report[k]:
            print("\n%s (%d):" % (label, len(report[k])))
            for d, why in report[k]:
                print("    %-52s %s" % (d[:52], why))
    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
