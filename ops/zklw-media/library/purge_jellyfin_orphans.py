#!/usr/bin/env python3
"""Purge Jellyfin library rows orphaned by removing /data/Movies from the library.

Background. /data/Movies is the capital-M twin of the Radarr root /data/movies.
The KG restore hardlinks between them, and a hardlink is one inode under two
names -- which Jellyfin, having no cross-path dedup, renders as two films. On
2026-07-28 the path was removed from the Movies library (both options.xml AND
the .mblink; editing options.xml alone leaves the scanner following the link).

That stopped the bleeding but did not clean the wound:

    Scan Media Library   Completed after 0 minute(s) and 11 seconds
    rows still under /data/Movies: 333

The reason is worth stating plainly, because it is the opposite of what you
would assume. Jellyfin's library validation walks the paths it currently knows
about and removes DB children it can no longer find *underneath those paths*.
Removing a path from a library therefore does not delete its items -- it makes
them unreachable by the validator. They become orphans: never revisited, never
cleaned, but still joined into every query the UI runs. So they keep rendering
as duplicates forever, and rescanning cannot help however many times you run it.
The 11-second scan is the tell -- it was not doing nothing, it was doing all the
work it believed it had.

There is no supported "forget these items" API. `DELETE /Items/{id}` is not it:
that deletes the media from disk, which here would unlink hardlinks that 124
seeding torrents depend on. So the fix is to delete the rows directly.

Two properties make that safe:

  * Every foreign key into BaseItems is ON DELETE CASCADE -- including
    BaseItems.ParentId -> BaseItems.Id, so deleting a folder takes its children
    with it. Enabling `PRAGMA foreign_keys` (SQLite defaults it OFF) means one
    DELETE cleans UserData, MediaStreamInfos, Chapters, AncestorIds, images,
    people maps and the rest.
  * Nothing of value is attached. Measured before writing this: 0 rows under
    /data/Movies carry a play position, a played flag, or a favourite.

THE CASE TRAP, which is the whole reason this is a script and not a one-liner:

    sqlite> select count(*) from BaseItems where Path like '/data/Movies%';
    1712                       -- WRONG: matches BOTH directories
    sqlite> select count(*) from BaseItems where Path glob '/data/Movies*';
    1032                       -- right

SQLite's LIKE is case-insensitive for ASCII. On a box whose entire problem is
two directories differing only in case, LIKE silently unions them, and the
"obvious" cleanup statement would delete the real library along with the
orphans. GLOB is case-sensitive and is the only correct operator here. This is
also why the earlier watch-state check read 3 rows on each side: it used LIKE
and was reporting the same 3 lower-m rows twice.

Jellyfin is stopped for the delete so the WAL is checkpointed and no writer
races us. Everything is backed up first.
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import time
import urllib.request

DB = "/home/mk/grey-media/config/jellyfin/data/jellyfin.db"
CONTAINER = "jellyfin"
HOST = "100.123.250.67"
DOOMED = "/data/Movies*"   # GLOB, case-sensitive. Never LIKE. See the docstring.
KEEP = "/data/movies*"


def api_key():
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    try:
        return c.execute("select AccessToken from ApiKeys limit 1").fetchone()[0]
    finally:
        c.close()


def playing():
    """Refuse to stop the server out from under somebody watching a film."""
    try:
        r = urllib.request.Request("http://%s:8096/Sessions" % HOST,
                                   headers={"X-Emby-Token": api_key()})
        d = json.loads(urllib.request.urlopen(r, timeout=20).read())
    except Exception as e:
        print("  could not read sessions (%s) -- assuming someone is watching" % e)
        return ["unknown"]
    return ["%s: %s" % (s.get("UserName"), (s.get("NowPlayingItem") or {}).get("Name"))
            for s in d if s.get("NowPlayingItem")]


def counts(path):
    c = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    try:
        q = lambda g: c.execute(
            "select count(*) from BaseItems where Path glob ?", (g,)).fetchone()[0]
        movies = c.execute(
            "select count(*) from BaseItems where Type like '%Movie' and Path is not null"
        ).fetchone()[0]
        names = c.execute(
            "select count(*) from (select Name from BaseItems where Type like '%Movie'"
            " and Path is not null group by Name)").fetchone()[0]
        return q(DOOMED), q(KEEP), movies, names
    finally:
        c.close()


def report(label, path):
    doomed, keep, movies, names = counts(path)
    print("  %-8s  /data/Movies*=%-5d  /data/movies*=%-5d  movie rows=%-5d  distinct titles=%d"
          % (label, doomed, keep, movies, names))
    return doomed, keep, movies, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    print("before:")
    doomed, keep, movies, names = report("db", DB)
    if not doomed:
        print("\nnothing to do -- no rows under /data/Movies.")
        return
    print("  orphan rows to delete: %d   (%d duplicate titles should disappear)"
          % (doomed, movies - names))

    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    risky = c.execute(
        "select count(*) from UserData u join BaseItems b on b.Id=u.ItemId"
        " where b.Path glob ? and (u.Played=1 or u.PlaybackPositionTicks>0"
        "                          or u.IsFavorite=1)", (DOOMED,)).fetchone()[0]
    c.close()
    print("  watch state / favourites attached to them: %d" % risky)
    if risky:
        print("  REFUSING: that state would be destroyed. Migrate it to the")
        print("  /data/movies twin first, then rerun.")
        return

    if not a.apply:
        print("\nDRY RUN -- nothing changed. Rerun with --apply.")
        return

    live = playing()
    if live:
        print("\nREFUSING: playback in progress:")
        for s in live:
            print("   ", s)
        return

    print("\nstopping %s" % CONTAINER)
    subprocess.run(["docker", "stop", CONTAINER], check=True,
                   capture_output=True, text=True)
    time.sleep(3)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = "%s.bak-orphanpurge-%s" % (DB, stamp)
    # Copy the sidecars too: a .db without its -wal is not a consistent restore.
    for suf in ("", "-wal", "-shm"):
        if os.path.exists(DB + suf):
            shutil.copy2(DB + suf, bak + suf)
    print("backup: %s (+wal/shm)" % bak)

    try:
        c = sqlite3.connect(DB)
        c.execute("pragma foreign_keys = ON")   # OFF by default; cascade needs it
        assert c.execute("pragma foreign_keys").fetchone()[0] == 1
        n = c.execute("delete from BaseItems where Path glob ?", (DOOMED,)).rowcount
        c.commit()
        print("deleted %d rows (cascade cleaned dependents)" % n)
        c.execute("vacuum")
        c.close()
    except Exception:
        print("delete failed -- restoring backup")
        for suf in ("", "-wal", "-shm"):
            if os.path.exists(bak + suf):
                shutil.copy2(bak + suf, DB + suf)
        subprocess.run(["docker", "start", CONTAINER], check=False)
        raise

    print("\nafter:")
    report("db", DB)

    subprocess.run(["docker", "start", CONTAINER], check=True,
                   capture_output=True, text=True)
    print("started %s" % CONTAINER)
    for _ in range(30):
        time.sleep(5)
        try:
            urllib.request.urlopen("http://%s:8096/System/Info/Public" % HOST,
                                   timeout=10).read()
            print("jellyfin responding")
            return
        except Exception:
            pass
    print("WARNING: jellyfin did not answer within 150s -- check `docker logs jellyfin`")


main()
