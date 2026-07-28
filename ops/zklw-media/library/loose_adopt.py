#!/usr/bin/env python3
"""Organise the loose, seeded video files sitting in the Radarr root.

209 video files live directly in /data/movies rather than in a movie folder.
Jellyfin scans that root, so each one is presented to users as its own film --
which is where most of the visible "duplicates" come from: After Lucia appears
as a proper library entry AND again as a bare 720p REPACK file.

THE CONSTRAINT THAT SHAPES EVERYTHING HERE: all 209 are actively seeded by
qBittorrent FROM THAT EXACT PATH. Moving them the obvious way would break 209
torrents across HDBits, Karagarga and TorrentLeech at once. So this runs in two
phases that are safe in this order and no other:

  import    ManualImport with importMode=copy against a Radarr that has
            copyUsingHardlinks enabled. That creates a second NAME for the same
            inode inside a proper movie folder. Zero bytes copied, and the path
            qBittorrent knows is untouched.

  add       Most of these files are not in Radarr AT ALL (156 of 209), so there
            is nothing to import them onto. This looks each one up, adds the
            film, then imports it. Added UNMONITORED with searchForMovie=False,
            matching kg_adopt: the file is already owned and seeded, so waking
            156 tracker searches would be pure cost. Never a silent top hit --
            an ambiguous or absent lookup is reported, not guessed.

  relocate  Only once the hardlink exists, tell qBittorrent to move the torrent
            to /data/torrents/movies. /data is a single filesystem (md3), so
            this is a rename(2): the inode survives, therefore the library's
            hardlink stays valid, and the Radarr root is left clean.

Run import first, verify, then relocate. Doing relocate first would leave the
library with nothing to point at.

UPGRADES. The brief was "import all 209, let Radarr upgrade". Radarr keeps one
file per movie, so importing over an existing film REPLACES it -- that is an
upgrade when the new file is better and a silent downgrade when it is not.
So the profile decides: a movie with no file always imports; a movie that
already has one imports only if the loose file ranks strictly higher in that
movie's own quality profile. Anything else is reported, never guessed.

Dry-run by default; --apply is opt-in.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
ROOT = "/data/movies"
SEED_DIR = "/data/torrents/movies"
VIDEO = (".mkv", ".mp4", ".avi", ".m4v", ".mpg", ".mpeg", ".ts", ".wmv", ".mov")
MIN_SIZE = 200 * 1024 ** 2
# Archival-Best is the profile that tolerates Unknown quality, which is what
# this material needs. It is close to inert either way: these are added
# unmonitored, so the profile never drives a grab.
ADD_PROFILE = 9
YEAR_SLACK = 1


def key(svc="radarr"):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/%s/config.xml" % (CFG, svc)).read()).group(1).strip()


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


def qbt():
    """Log in to qBittorrent using the credential qbit-manage already holds.

    Read server-side and never passed as an argument, so it cannot leak into a
    process list or a shell history.
    """
    import http.cookiejar
    import yaml
    q = yaml.safe_load(open("%s/qbit-manage/config.yml" % CFG))["qbt"]
    h = "http://%s:8080" % HOST
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        op.open(urllib.request.Request(
            h + "/api/v2/auth/login",
            data=urllib.parse.urlencode({"username": q.get("user"),
                                         "password": q.get("pass")}).encode(),
            headers={"Referer": h}), timeout=30).read()
    except urllib.error.HTTPError:
        pass
    # Do not trust the login response. This qBittorrent bypasses auth for the
    # local subnet, so /auth/login answers "Fails." while the API is perfectly
    # usable. What matters is whether an authenticated call works, so ask.
    try:
        urllib.request.urlopen  # noqa: B018  (kept explicit for clarity)
        op.open(h + "/api/v2/app/version", timeout=30).read()
    except urllib.error.HTTPError as e:
        raise SystemExit("qBittorrent is not usable (HTTP %s) -- check the "
                         "credential in qbit-manage config.yml" % e.code)
    return op, h


def loose_files():
    out = []
    for f in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, f)
        if f.lower().endswith(VIDEO) and os.path.isfile(p) and os.path.getsize(p) > MIN_SIZE:
            out.append(p)
    return out


def rank_map(profile):
    """Position of each quality id within a profile: higher index = better.

    Radarr orders `items` worst-first, and groups (e.g. "WEB 1080p") nest their
    members. Flattening in order preserves the ranking the user actually
    configured, which is the only ranking that should decide a replacement.
    """
    rank, i = {}, 0
    for it in profile.get("items", []):
        for q in (it.get("items") or [it]):
            qq = q.get("quality") or {}
            if qq.get("id") is not None:
                rank[qq["id"]] = i
                i += 1
    return rank


def cmd_import(apply_):
    mm = api("/config/mediamanagement") or {}
    if not mm.get("copyUsingHardlinks"):
        print("REFUSING: copyUsingHardlinks is off -- importMode=copy would duplicate "
              "%d files instead of hardlinking them." % len(loose_files()))
        return
    print("hardlinks enabled; importMode=copy will link, not duplicate\n")

    profiles = {p["id"]: p for p in (api("/qualityprofile") or [])}
    stats = {"imported": 0, "upgrade": 0, "skip_worse": 0, "unmatched": 0, "failed": 0}
    unmatched, worse = [], []

    for p in loose_files():
        name = os.path.basename(p)
        parsed = api("/parse?title=" + urllib.parse.quote(name)) or {}
        movie = parsed.get("movie") or {}
        quality = (parsed.get("parsedMovieInfo") or {}).get("quality")
        mid = movie.get("id")
        if not mid:
            stats["unmatched"] += 1
            unmatched.append(name)
            continue

        full = api("/movie/%d" % mid) or {}
        prof = profiles.get(full.get("qualityProfileId")) or {}
        rk = rank_map(prof)
        newq = ((quality or {}).get("quality") or {}).get("id")
        verb = "IMPORT"
        if full.get("hasFile"):
            cur = (full.get("movieFile") or {}).get("quality") or {}
            curq = (cur.get("quality") or {}).get("id")
            if rk.get(newq, -1) <= rk.get(curq, -1):
                stats["skip_worse"] += 1
                worse.append((name, full.get("title")))
                continue
            verb = "UPGRADE"

        if not apply_:
            print("  DRY-RUN %-8s %-52s -> %s (%s)" % (verb, name[:52], full.get("title"), full.get("year")))
            stats["upgrade" if verb == "UPGRADE" else "imported"] += 1
            continue

        f = {"path": p, "movieId": mid, "quality": quality,
             "languages": (parsed.get("parsedMovieInfo") or {}).get("languages") or []}
        cmd = api("/command", "POST",
                  {"name": "ManualImport", "files": [f], "importMode": "copy"})
        st = {}
        for _ in range(60):
            st = api("/command/%d" % cmd["id"]) or {}
            if st.get("status") in ("completed", "failed", "aborted"):
                break
            time.sleep(1)
        mf = api("/moviefile?movieId=%d" % mid) or []
        linked = [x for x in mf if os.path.exists(x["path"]) and os.stat(x["path"]).st_ino == os.stat(p).st_ino]
        if linked:
            stats["upgrade" if verb == "UPGRADE" else "imported"] += 1
            print("  %-8s %-46s nlink=%d %s" % (
                verb, name[:46], os.stat(p).st_nlink, full.get("title")))
        else:
            stats["failed"] += 1
            print("  FAILED   %-46s command=%s" % (name[:46], st.get("status")))

    print("\n" + "=" * 68)
    print("import summary: %s" % stats)
    if unmatched:
        print("\nno Radarr movie matched (left alone, still seeding):")
        for n in unmatched[:25]:
            print("   ", n[:76])
        if len(unmatched) > 25:
            print("    ... and %d more" % (len(unmatched) - 25))
    if worse:
        print("\nnot an upgrade over the copy already in the library (left alone):")
        for n, t in worse[:25]:
            print("    %-58s vs %s" % (n[:58], t))
        if len(worse) > 25:
            print("    ... and %d more" % (len(worse) - 25))
    if not apply_:
        print("\nDRY RUN -- nothing changed.")


def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def title_year(name):
    """Pull a searchable title and year out of a scene filename.

    Release names put the year immediately after the title, so everything left
    of the first 19xx/20xx is the title -- including AKA forms, which are split
    because the tracker's preferred title is often not TMDb's.
    """
    n = re.sub(r"\.(mkv|mp4|avi|m4v|mpg|mpeg|ts|wmv|mov)$", "", name, flags=re.I)
    n = re.sub(r"[._]", " ", n)
    m = re.search(r"\b(19\d{2}|20\d{2})\b", n)
    if not m:
        return None, None
    stem = re.sub(r"[\(\)\[\]]", " ", n[:m.start()])
    parts = [p.strip() for p in re.split(r"\bAKA\b", stem, flags=re.I) if p.strip()]
    return parts, int(m.group(1))


def cmd_add(apply_):
    """Add the films Radarr does not have, then hardlink-import them."""
    mm = api("/config/mediamanagement") or {}
    if not mm.get("copyUsingHardlinks"):
        print("REFUSING: copyUsingHardlinks is off -- would duplicate, not link.")
        return
    added = imported = ambiguous = nolookup = noyear = skipped = 0
    report = {"ambiguous": [], "nolookup": [], "noyear": []}

    for p in loose_files():
        name = os.path.basename(p)
        if (api("/parse?title=" + urllib.parse.quote(name)) or {}).get("movie", {}).get("id"):
            skipped += 1
            continue
        parts, year = title_year(name)
        if not parts:
            noyear += 1
            report["noyear"].append(name)
            continue
        want = {norm(x) for x in parts}
        hits, seen = [], set()
        for term in parts:
            for c in (api("/movie/lookup?term=" + urllib.parse.quote("%s %d" % (term, year))) or []):
                if c.get("tmdbId") in seen:
                    continue
                seen.add(c["tmdbId"])
                titles = {norm(c.get("title")), norm(c.get("originalTitle"))}
                titles |= {norm(t.get("title")) for t in (c.get("alternateTitles") or [])
                           if isinstance(t, dict)}
                if titles & want and abs((c.get("year") or 0) - year) <= YEAR_SLACK:
                    hits.append(c)
        # exactly one tmdbId, or a human looks at it
        uniq = {c["tmdbId"]: c for c in hits}
        if len(uniq) != 1:
            if uniq:
                ambiguous += 1
                report["ambiguous"].append((name, [(c["title"], c["year"]) for c in uniq.values()][:4]))
            else:
                nolookup += 1
                report["nolookup"].append(name)
            continue
        c = list(uniq.values())[0]

        if not apply_:
            print("  DRY-RUN ADD %-50s -> %s (%s) tmdb=%s" % (name[:50], c["title"], c["year"], c["tmdbId"]))
            added += 1
            continue

        c.update({"qualityProfileId": ADD_PROFILE, "rootFolderPath": ROOT,
                  "monitored": False, "minimumAvailability": "released",
                  "addOptions": {"searchForMovie": False}})
        mv = api("/movie", "POST", c)
        if not mv:
            continue
        added += 1
        parsed = api("/parse?title=" + urllib.parse.quote(name)) or {}
        q = (parsed.get("parsedMovieInfo") or {}).get("quality")
        cmd = api("/command", "POST", {"name": "ManualImport", "importMode": "copy",
                                       "files": [{"path": p, "movieId": mv["id"], "quality": q,
                                                  "languages": (parsed.get("parsedMovieInfo") or {}).get("languages") or []}]})
        for _ in range(60):
            st = api("/command/%d" % cmd["id"]) or {}
            if st.get("status") in ("completed", "failed", "aborted"):
                break
            time.sleep(1)
        mf = api("/moviefile?movieId=%d" % mv["id"]) or []
        if any(os.path.exists(x["path"]) and os.stat(x["path"]).st_ino == os.stat(p).st_ino for x in mf):
            imported += 1
            print("  ADDED+LINKED %-44s nlink=%d %s" % (name[:44], os.stat(p).st_nlink, c["title"][:24]))
        else:
            print("  ADDED, import failed %-40s %s" % (name[:40], c["title"][:24]))

    print("\n" + "=" * 68)
    print("added=%d imported=%d | ambiguous=%d no-lookup=%d no-year=%d already-known=%d"
          % (added, imported, ambiguous, nolookup, noyear, skipped))
    for k, label in (("ambiguous", "more than one candidate -- needs a human"),
                     ("nolookup", "no TMDb match on any title form"),
                     ("noyear", "no year in the filename")):
        if report[k]:
            print("\n%s (%d):" % (label, len(report[k])))
            for row in report[k][:15]:
                print("    ", (row[0] if isinstance(row, tuple) else row)[:74])
                if isinstance(row, tuple):
                    print("        candidates:", row[1])
    if not apply_:
        print("\nDRY RUN -- nothing changed.")


def cmd_relocate(apply_):
    """Move the torrents out of the Radarr root, now that hardlinks exist.

    The guard is by INODE, not by path. A file is moved only when the library
    already holds a hardlink to the same inode inside a movie folder -- then
    renaming this name is invisible to Radarr and to Jellyfin.

    That is deliberately stricter than "is this the registered movieFile". A
    loose file nobody has matched yet is currently the ONLY way its film shows
    up in Jellyfin, ugly filename and all. Moving it out of the scanned root
    would quietly delete it from the library's view, so those stay put and get
    reported instead.

    A second case is equally safe and easy to miss: a loose file whose film the
    library already serves from a DIFFERENT file. That one is not the only copy
    Jellyfin sees -- it is the redundant second tile that started this whole
    investigation -- so moving it removes a duplicate rather than losing a film.
    """
    inodes, has_file = set(), set()
    for m in (api("/movie") or []):
        f = m.get("movieFile") or {}
        p = f.get("path")
        if m.get("hasFile"):
            has_file.add(m["id"])
        if p and os.path.exists(p):
            try:
                inodes.add(os.stat(p).st_ino)
            except OSError:
                pass
    op, h = qbt()
    tor = json.loads(op.open(h + "/api/v2/torrents/info", timeout=180).read())
    # Torrent-centric, not file-centric: a torrent in the Radarr root may be a
    # bare file OR a release-named folder, and both shapes produce the same
    # spurious Jellyfin entry.
    inroot = [t for t in tor if (t.get("save_path") or "").rstrip("/") == ROOT]

    def videos(cp):
        if os.path.isfile(cp):
            return [cp] if cp.lower().endswith(VIDEO) and os.path.getsize(cp) > MIN_SIZE else []
        out = []
        for dp, dn, fn in os.walk(cp):
            for f in fn:
                p = os.path.join(dp, f)
                if f.lower().endswith(VIDEO) and os.path.getsize(p) > MIN_SIZE:
                    out.append(p)
        return out

    todo, redundant, nolink = [], [], []
    for t in inroot:
        cp = (t.get("content_path") or "").rstrip("/")
        vids = videos(cp) if cp and os.path.exists(cp) else []
        if not vids:
            continue
        if all(os.stat(v).st_ino in inodes for v in vids):
            todo.append((cp, t))
            continue
        served = all(((api("/parse?title=" + urllib.parse.quote(os.path.basename(v))) or {})
                      .get("movie") or {}).get("id") in has_file for v in vids)
        (redundant if served else nolink).append((cp, t))

    print("torrents saving into the Radarr root: %d" % len(inroot))
    print("  relocate: library holds a hardlink to every video  : %d" % len(todo))
    print("  relocate: film already served by a different file  : %d" % len(redundant))
    print("  HELD, no library entry -- only copy Jellyfin sees  : %d" % len(nolink))
    for p, _ in nolink[:14]:
        print("     held:", os.path.basename(p)[:70])
    todo += redundant

    if not apply_:
        print("\nDRY RUN -- would move %d torrents to %s" % (len(todo), SEED_DIR))
        return
    if not todo:
        print("\nnothing to do")
        return

    os.makedirs(SEED_DIR, exist_ok=True)
    os.chown(SEED_DIR, 1001, 1001)
    moved = 0
    for i in range(0, len(todo), 25):
        chunk = todo[i:i + 25]
        op.open(urllib.request.Request(
            h + "/api/v2/torrents/setLocation",
            data=urllib.parse.urlencode({"hashes": "|".join(t["hash"] for _, t in chunk),
                                         "location": SEED_DIR}).encode(),
            headers={"Referer": h}), timeout=120).read()
        moved += len(chunk)
        time.sleep(3)
    print("\nrequested relocation of %d torrents to %s" % (moved, SEED_DIR))
    print("verify with: loose_adopt.py verify")


def cmd_verify():
    """Confirm the invariant that matters: seeding intact AND root clean."""
    op, h = qbt()
    tor = json.loads(op.open(h + "/api/v2/torrents/info", timeout=180).read())
    bad = [t for t in tor if t.get("state") in ("missingFiles", "error")]
    still = loose_files()
    inroot = [t for t in tor if (t.get("save_path") or "").rstrip("/") == ROOT]
    print("torrents total              : %d" % len(tor))
    print("torrents in error/missing   : %d %s" % (len(bad), "<-- INVESTIGATE" if bad else "OK"))
    for t in bad[:10]:
        print("     %-58s %s" % (t["name"][:58], t["state"]))
    print("torrents still saving to %s: %d" % (ROOT, len(inroot)))
    print("loose video files left in the Radarr root: %d" % len(still))
    for p in still[:10]:
        print("     ", os.path.basename(p)[:74])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=("import", "add", "relocate", "verify"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    {"import": lambda: cmd_import(a.apply),
     "add": lambda: cmd_add(a.apply),
     "relocate": lambda: cmd_relocate(a.apply),
     "verify": cmd_verify}[a.phase]()


main()
