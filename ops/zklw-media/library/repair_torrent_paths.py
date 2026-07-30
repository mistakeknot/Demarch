#!/usr/bin/env python3
"""Repoint torrents left pointing at /data/Movies after the capital-M retirement.

`retire_capital_movies.py move` asked qBittorrent to relocate the 124 torrents
anchored under /data/Movies, waited for them, then renamed whatever was left.
For 35 torrents that worked. For 89 it did not, and the subsequent rename moved
their data anyway -- so they now claim a save_path that no longer exists while
their files sit intact under /data/torrents/kg.

Why this was not caught: `finish` gated on torrent STATE --

    bad = [t for t in torrents(...) if t.get("state") in ("missingFiles", "error")]

-- and a seeding torrent does not touch disk until a peer asks for a piece. All
89 were sitting in stalledUP, reporting perfect health, pointing at nothing.
State is a lagging indicator here; save_path is the leading one. `finish` should
have asserted that no torrent still referenced the old root at all, and it now
does.

The damage is latent rather than done: nothing is lost, but the first peer to
request a piece pushes the torrent into missingFiles and the seed dies. On
private trackers that is standing bled away for no reason, so it wants fixing
before it is noticed rather than after.

The repair is a path update, not a data move. Files were relocated by rename(2)
inside one filesystem, so inodes -- and therefore bytes -- are unchanged. This
verifies every file of every torrent is present at the new location with a
matching size BEFORE touching anything, which catches the realistic failure
(a file left behind by the merge branch) without hashing 425 GB on spinning
RAID5 that is already busy with the restore.
"""
import argparse
import http.cookiejar
import json
import os
import time
import urllib.parse
import urllib.request

import yaml

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
OLD = "/data/Movies"
NEW = "/data/torrents/kg"


def qbt():
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
    # Auth is bypassed for the local subnet and /auth/login answers "Fails."
    # even so; the only meaningful test is whether the API actually responds.
    op.open(h + "/api/v2/app/version", timeout=30).read()
    return op, h


def get(op, h, path):
    return json.loads(op.open(h + "/api/v2" + path, timeout=180).read())


def post(op, h, path, data):
    return op.open(urllib.request.Request(
        h + "/api/v2" + path, data=urllib.parse.urlencode(data).encode(),
        headers={"Referer": h}), timeout=180).read()


def classify(op, h, t):
    """Is every file of this torrent present, correctly sized, under NEW?"""
    sp = (t.get("save_path") or "").rstrip("/")
    dest = NEW + sp[len(OLD):]
    try:
        files = get(op, h, "/torrents/files?hash=" + t["hash"])
    except Exception as e:
        return None, dest, "could not list files: %s" % e
    bad = []
    for f in files:
        p = os.path.join(dest, f["name"])
        try:
            if os.stat(p).st_size != f["size"]:
                bad.append("size mismatch: " + f["name"])
        except OSError:
            bad.append("absent: " + f["name"])
    return (not bad), dest, ("; ".join(bad[:2]) if bad else "%d file(s) verified" % len(files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--recheck", action="store_true",
                    help="force a hash recheck after repointing (slow: hours on HDD)")
    a = ap.parse_args()

    op, h = qbt()
    stale = [t for t in get(op, h, "/torrents/info")
             if (t.get("save_path") or "").startswith(OLD)]
    print("torrents still pointing at %s: %d\n" % (OLD, len(stale)))
    if not stale:
        print("nothing to repair.")
        return

    ok, broken = [], []
    for t in stale:
        good, dest, why = classify(op, h, t)
        (ok if good else broken).append((t, dest, why))

    print("  verified present under %s : %d" % (NEW, len(ok)))
    print("  NOT safe to repoint            : %d" % len(broken))
    for t, dest, why in broken[:10]:
        print("     %-46s %s" % (t["name"][:46], why))
    if not a.apply:
        print("\nDRY RUN -- nothing changed. Rerun with --apply.")
        return
    if not ok:
        print("\nnothing safe to repoint.")
        return

    # Group by destination: one call per directory keeps the request count sane
    # and matches how qBittorrent wants to think about a save path.
    bypath = {}
    for t, dest, _ in ok:
        bypath.setdefault(dest, []).append(t)
    done = 0
    for dest, ts in sorted(bypath.items()):
        os.makedirs(dest, exist_ok=True)
        post(op, h, "/torrents/setLocation",
             {"hashes": "|".join(t["hash"] for t in ts), "location": dest})
        done += len(ts)
        time.sleep(0.5)
    print("\nrepointed %d torrent(s) across %d location(s)" % (done, len(bypath)))

    if a.recheck:
        hs = "|".join(t["hash"] for t, _, _ in ok)
        post(op, h, "/torrents/recheck", {"hashes": hs})
        print("recheck queued for %d torrent(s)" % len(ok))

    time.sleep(10)
    after = [t for t in get(op, h, "/torrents/info")
             if (t.get("save_path") or "").startswith(OLD)]
    bad = [t for t in get(op, h, "/torrents/info")
           if t.get("state") in ("error", "missingFiles")]
    print("still pointing at %s: %d" % (OLD, len(after)))
    print("in error/missingFiles      : %d" % len(bad))
    for t in bad[:10]:
        print("   %-52s %s" % (t["name"][:52], t["state"]))


main()
