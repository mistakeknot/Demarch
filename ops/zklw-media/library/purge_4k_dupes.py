#!/usr/bin/env python3
"""Delete the orphaned 1080p/duplicate files left in /data/movies-4k.

Irreversible, so every precondition is re-checked against live state at the
moment of deletion rather than trusting an earlier survey. A file is removed
ONLY if all four hold:

  1. hardlink count == 1     -- not shared with seeding torrent data. (The
                                /data/tv-4k Westworld files are hardlinked into
                                /data/torrents and must never be touched here.)
  2. no torrent references it -- deleting live torrent data is a hit-and-run,
                                which is account-fatal on a private tracker.
  3. Radarr holds the film with a file...
  4. ...at a path OUTSIDE /data/movies-4k -- i.e. a real replacement exists and
                                we are not deleting the copy still in use.

Any file failing any check is skipped loudly rather than removed.
"""
import argparse, json, os, re, urllib.parse, urllib.request, http.cookiejar

HOST = "100.123.250.67"
TARGET_DIR = "/data/movies-4k"


def qbit_torrent_paths():
    inb = False
    pw = None
    for line in open("/home/mk/grey-media/config/qbit-manage/config.yml"):
        s = line.strip()
        if s.startswith("qbt:"):
            inb = True; continue
        if inb and line.strip() and not re.match(r"^[ \t#]", line): break
        if inb and s.startswith("pass:"): pw = s[5:].strip().strip("'\""); break
    qb = "http://%s:8080" % HOST
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(qb + "/api/v2/auth/login",
            data=urllib.parse.urlencode({"username": "admin", "password": pw}).encode(),
            headers={"Referer": qb, "Origin": qb}), timeout=30)
    tor = json.loads(op.open(urllib.request.Request(qb + "/api/v2/torrents/info",
                     headers={"Referer": qb}), timeout=180).read())
    paths = set()
    for t in tor:
        for k in ("content_path", "save_path"):
            if t.get(k):
                paths.add(t[k])
    return paths


def radarr_movies():
    k = re.search(r"<ApiKey>([^<]+)</ApiKey>",
                  open("/home/mk/grey-media/config/radarr/config.xml").read()).group(1).strip()
    r = urllib.request.Request("http://%s:7878/api/v3/movie" % HOST, headers={"X-Api-Key": k})
    return json.loads(urllib.request.urlopen(r, timeout=180).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    tor_paths = qbit_torrent_paths()
    movies = radarr_movies()
    freed = 0

    for dirpath, _, files in os.walk(TARGET_DIR):
        for fn in files:
            if not fn.lower().endswith((".mkv", ".mp4", ".avi", ".m4v")):
                continue
            p = os.path.join(dirpath, fn)
            st = os.stat(p)

            if st.st_nlink != 1:
                print("  SKIP (hardlinked x%d, shared data): %s" % (st.st_nlink, fn[:60])); continue
            if any(p == tp or p.startswith(tp.rstrip("/") + "/") for tp in tor_paths):
                print("  SKIP (torrent data - would be a hit-and-run): %s" % fn[:60]); continue

            match = next((m for m in movies
                          if (m.get("movieFile") or {}).get("path")
                          and m["title"].split(":")[0].lower()[:12] in fn.lower().replace(".", " ")), None)
            # Match on the containing folder name, which Radarr controls.
            folder = os.path.basename(dirpath)
            match = next((m for m in movies if m.get("hasFile") and
                          (m.get("movieFile") or {}).get("path", "").find("/data/movies/") == 0 and
                          folder.split(" (")[0].lower().replace(" - ", " ").replace(":", "")
                          in m["title"].lower().replace(":", "").replace(" - ", " ")), match)
            if not match:
                print("  SKIP (no confirmed replacement in main library): %s" % fn[:60]); continue
            rp = (match.get("movieFile") or {}).get("path", "")
            if rp.startswith(TARGET_DIR):
                print("  SKIP (Radarr still points AT this copy): %s" % fn[:60]); continue

            gb = st.st_size / 1e9
            if not a.apply:
                print("  DRY-RUN would delete %-58s %.1fGB  (replacement: %s)" % (
                    fn[:58], gb, os.path.basename(rp)[:40]))
                freed += st.st_size
                continue
            os.remove(p)
            freed += st.st_size
            print("  deleted %-58s %.1fGB" % (fn[:58], gb))

    # tidy now-empty film folders
    for dirpath, dirnames, files in os.walk(TARGET_DIR, topdown=False):
        if dirpath != TARGET_DIR and not os.listdir(dirpath):
            if a.apply:
                os.rmdir(dirpath); print("  removed empty dir %s" % os.path.basename(dirpath))
            else:
                print("  DRY-RUN would remove empty dir %s" % os.path.basename(dirpath))

    print("\n%s %.1f GB" % ("freed" if a.apply else "would free", freed / 1e9))
    if not a.apply:
        print("DRY RUN -- nothing deleted.")


main()
