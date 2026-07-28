#!/usr/bin/env python3
"""Retire /data/Movies, the capital-M twin of the Radarr root.

/data/Movies is the KG cold-restore destination from jarmusch. /data/movies is
the Radarr library root. Two directories differing only in case is a standing
hazard on this box, not a cosmetic one:

  * Jellyfin scanned both and double-listed 277 films, because hardlinking
    between them (which is correct and free) looks like two films to a scanner
    with no cross-path dedup.
  * Radarr compares paths CASE-INSENSITIVELY, so an import from
    /data/Movies/X into /data/movies/X fails with "Source and destination
    can't be the same" -- a real bug this estate has already hit.

The measurement that makes retirement cheap: of the files under /data/Movies,
1.01 TB is ALREADY hardlinked into the library and only ~30 GB is unique. There
is nothing to copy. The job is to repoint what points at it, then let the
redundant names go.

ORDER MATTERS, for two independent reasons.

  1. The restore is live. kg_restore.sh is mid-run (film ~154 of 676). If the
     destination is retargeted to an EMPTY directory, rsync sees 676 missing
     destinations and re-downloads everything -- weeks at the 1200 KB/s daytime
     cap. So the data moves to the new location BEFORE the script is retargeted;
     rsync then finds films 1-154 present and resumes at 155.

  2. 124 torrents are anchored under /data/Movies and 119 of them are actively
     seeding. qBittorrent must be told to move them, rather than having the
     files moved out from under it -- a torrent whose files vanish stops
     seeding, and on a private tracker that is standing lost for nothing.

Everything here is a rename(2) inside /data (single filesystem, md3), so inodes
survive and every hardlink the library holds stays valid. Nothing is copied and
nothing is deleted except empty directories.

Phases:
    plan      measure and print what each phase would do (default, read-only)
    move      setLocation the 124 torrents, then rename the remaining folders
    retarget  point kg_restore.sh / kg_adopt.py / the nightly at the new root
    finish    verify nothing unique is left, then remove the empty tree
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
OPS = "/root/grey-ops"
OLD = "/data/Movies"
NEW = "/data/torrents/kg"
# Files the restore script and the adoption tooling reference by path.
RETARGET = ["kg_restore.sh", "kg_adopt.py", "kg_restore_nightly.py",
            "kg_review_force.py", "kg_orphan_adopt.py", "kg_fix_samepath.py"]
SERVICE = "kg-restore.service"


def radarr(path):
    k = re.search(r"<ApiKey>([^<]+)</ApiKey>",
                  open("%s/radarr/config.xml" % CFG).read()).group(1).strip()
    r = urllib.request.Request("http://%s:7878/api/v3%s" % (HOST, path),
                               headers={"X-Api-Key": k})
    raw = urllib.request.urlopen(r, timeout=300).read()
    return json.loads(raw) if raw else None


def qbt():
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
    # This qBittorrent bypasses auth for the local subnet and answers "Fails."
    # to /auth/login while the API works, so probe instead of trusting it.
    op.open(h + "/api/v2/app/version", timeout=30).read()
    return op, h


def torrents(op, h):
    return json.loads(op.open(h + "/api/v2/torrents/info", timeout=180).read())


def census():
    uniq = shared = 0
    ub = sb = 0
    for dp, dn, fn in os.walk(OLD):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_nlink > 1:
                shared += 1
                sb += st.st_size
            else:
                uniq += 1
                ub += st.st_size
    return shared, sb, uniq, ub


def cmd_plan():
    shared, sb, uniq, ub = census()
    print("%s -> %s\n" % (OLD, NEW))
    print("  hardlinked into the library (free to unname): %6d files  %.2f TB" % (shared, sb / 1024 ** 4))
    print("  unique to this tree (moves, never deleted)  : %6d files  %.2f TB" % (uniq, ub / 1024 ** 4))
    op, h = qbt()
    anch = [t for t in torrents(op, h) if (t.get("save_path") or "").startswith(OLD)]
    print("  torrents anchored here                      : %6d       %.2f GB"
          % (len(anch), sum(t.get("size", 0) for t in anch) / 1024 ** 3))
    top = [d for d in sorted(os.listdir(OLD)) if os.path.isdir(os.path.join(OLD, d))]
    empty = [d for d in top if not os.listdir(os.path.join(OLD, d))]
    print("  top-level folders                           : %6d (%d empty, awaiting restore)"
          % (len(top), len(empty)))
    print("\n  restore service: %s" % subprocess.run(
        ["systemctl", "is-active", SERVICE], capture_output=True, text=True).stdout.strip())
    print("\nrun `move`, then `retarget`, then `finish`.")


def cmd_move(apply_):
    """Move the data, torrents first so seeding is never orphaned."""
    if apply_:
        print("stopping %s so rsync is not writing mid-move" % SERVICE)
        subprocess.run(["systemctl", "stop", SERVICE], check=False)
        time.sleep(3)
    os.makedirs(NEW, exist_ok=True)
    try:
        os.chown(NEW, 1001, 1001)
    except OSError:
        pass

    op, h = qbt()
    anch = [t for t in torrents(op, h) if (t.get("save_path") or "").startswith(OLD)]
    print("torrents to repoint: %d" % len(anch))
    # Group by the save_path they currently use; each becomes the same relative
    # path under NEW so the torrent's own file layout is unchanged.
    bypath = {}
    for t in anch:
        bypath.setdefault((t.get("save_path") or "").rstrip("/"), []).append(t)
    for sp, ts in sorted(bypath.items()):
        dest = NEW + sp[len(OLD):]
        if not apply_:
            print("  DRY-RUN %-58s -> %s  (%d torrents)" % (sp[:58], dest[:40], len(ts)))
            continue
        os.makedirs(dest, exist_ok=True)
        op.open(urllib.request.Request(
            h + "/api/v2/torrents/setLocation",
            data=urllib.parse.urlencode({"hashes": "|".join(t["hash"] for t in ts),
                                         "location": dest}).encode(),
            headers={"Referer": h}), timeout=180).read()
        print("  moved %d torrent(s) -> %s" % (len(ts), dest[:60]))
        time.sleep(2)

    if apply_:
        print("\nwaiting for qBittorrent to finish moving files...")
        for _ in range(120):
            still = [t for t in torrents(op, h) if (t.get("save_path") or "").startswith(OLD)]
            if not still:
                break
            time.sleep(10)
        print("torrents still anchored at %s: %d" % (OLD, len(still)))

    # Whatever qBittorrent did not move is plain restored data. A rename is
    # instant and inode-preserving, so the library's hardlinks are unaffected.
    left = sorted(os.listdir(OLD)) if os.path.isdir(OLD) else []
    print("\nremaining top-level entries to rename: %d" % len(left))
    moved = merged = 0
    for d in left:
        src, dst = os.path.join(OLD, d), os.path.join(NEW, d)
        if not apply_:
            moved += 1
            continue
        if not os.path.exists(dst):
            os.rename(src, dst)
            moved += 1
        else:
            # Destination exists because qBittorrent already created it. Merge
            # file by file rather than clobbering a directory that is seeding.
            for dp, dn, fn in os.walk(src):
                rel = os.path.relpath(dp, src)
                tgt = os.path.join(dst, rel) if rel != "." else dst
                os.makedirs(tgt, exist_ok=True)
                for f in fn:
                    s, t = os.path.join(dp, f), os.path.join(tgt, f)
                    if not os.path.exists(t):
                        os.rename(s, t)
            merged += 1
    print("renamed=%d merged=%d" % (moved, merged))
    if not apply_:
        print("\nDRY RUN -- nothing changed.")


def cmd_retarget(apply_):
    """Point the restore and adoption tooling at the new root."""
    for name in RETARGET:
        p = os.path.join(OPS, name)
        if not os.path.exists(p):
            print("  skip (absent): %s" % name)
            continue
        s = open(p).read()
        if OLD not in s:
            print("  no reference: %s" % name)
            continue
        n = s.count(OLD)
        if not apply_:
            print("  DRY-RUN %-26s %d reference(s) -> %s" % (name, n, NEW))
            continue
        shutil.copy2(p, p + ".bak-precapital")
        # Word-boundary replace: /data/Movies must not match /data/movies, and
        # the trailing character check keeps /data/Movies-4k (if it ever exists)
        # from being rewritten.
        open(p, "w").write(re.sub(re.escape(OLD) + r"(?![-\w])", NEW, s))
        print("  %-26s rewrote %d reference(s)" % (name, n))
    if apply_:
        subprocess.run(["systemctl", "daemon-reload"], check=False)
    if not apply_:
        print("\nDRY RUN -- nothing changed.")


def cmd_finish(apply_):
    """Verify nothing is stranded, then remove the empty tree and restart."""
    ok = True
    if os.path.isdir(OLD):
        shared, sb, uniq, ub = census()
        print("files still under %s: %d hardlinked, %d unique (%.2f GB)"
              % (OLD, shared, uniq, ub / 1024 ** 3))
        if uniq:
            print("REFUSING to remove: %d unique files would be destroyed." % uniq)
            ok = False
    else:
        print("%s already gone" % OLD)

    movies = radarr("/movie") or []
    missing = [m for m in movies if m.get("hasFile")
               and not os.path.exists(((m.get("movieFile") or {}).get("path") or ""))]
    print("radarr: %d with a file, %d missing on disk" % (
        sum(1 for m in movies if m.get("hasFile")), len(missing)))
    for m in missing[:10]:
        print("   MISSING:", m["title"])
    if missing:
        ok = False

    op, h = qbt()
    bad = [t for t in torrents(op, h) if t.get("state") in ("missingFiles", "error")]
    print("torrents in error/missingFiles: %d" % len(bad))
    for t in bad[:10]:
        print("   %-56s %s" % (t["name"][:56], t["state"]))
    if bad:
        ok = False

    if not ok:
        print("\nNOT SAFE -- fix the above before removing anything.")
        return
    if not apply_:
        print("\nDRY RUN -- would remove the empty tree and restart %s." % SERVICE)
        return
    if os.path.isdir(OLD):
        for dp, dn, fn in os.walk(OLD, topdown=False):
            for d in dn:
                try:
                    os.rmdir(os.path.join(dp, d))
                except OSError:
                    pass
        try:
            os.rmdir(OLD)
            print("removed %s" % OLD)
        except OSError as e:
            print("could not remove %s: %s" % (OLD, e))
    subprocess.run(["systemctl", "start", SERVICE], check=False)
    time.sleep(5)
    print("restore service: %s" % subprocess.run(
        ["systemctl", "is-active", SERVICE], capture_output=True, text=True).stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", nargs="?", default="plan",
                    choices=("plan", "move", "retarget", "finish"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    {"plan": cmd_plan,
     "move": lambda: cmd_move(a.apply),
     "retarget": lambda: cmd_retarget(a.apply),
     "finish": lambda: cmd_finish(a.apply)}[a.phase]()


main()
