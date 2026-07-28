#!/usr/bin/env python3
"""Pause torrents on jarmusch that grey is also seeding (sylveste-inxe).

The jarmusch -> grey migration moved the data but left the originals loaded on
jarmusch. Comparing infohashes found 432 torrents present on BOTH machines,
spanning HDBits and Karagarga stock. Seeding one infohash from two IPs is the
fastest way to be banned from a private tracker.

Runs ON jarmusch. Credentials come from the FIRST TWO LINES of stdin and the
infohashes to pause from the remaining lines, so nothing sensitive is ever
passed as an argument or appears in a process list.

PAUSE, NEVER DELETE. This keeps the data and the .torrent exactly where they
are and is undone by resuming. It only removes the second announcement source.
Grey already seeds every one of these, is the connectable side (jarmusch is
behind a firewall with effectively zero upload), and is governed by qbit-manage
share limits -- so nothing loses a seeder.

Torrents unique to jarmusch are left strictly alone: they are the ones grey does
NOT have, so pausing them would lose real seeding.

Usage, from clavain:

    export OP_SERVICE_ACCOUNT_TOKEN="$(cat ~/.config/op-migrate.token)"
    { printf '%s\\n%s\\n' \\
        "$(op read op://zklw-migrate/qbit-jarmusch/username)" \\
        "$(op read op://zklw-migrate/qbit-jarmusch/password)"
      cat overlap.txt; } | ssh jarmusch 'python3 /tmp/jarmusch_dupes.py'

Add --apply to actually pause; the default is a read-only report that also
answers whether the duplicates are announcing.
"""
import collections
import http.cookiejar
import json
import sys
import urllib.parse
import urllib.request

data = sys.stdin.read().splitlines()
if len(data) < 3:
    print("expected: username, password, then one infohash per line on stdin")
    sys.exit(2)
user, pw = data[0].strip(), data[1].strip()
hashes = {h.strip().lower() for h in data[2:] if h.strip()}
apply_ = "--apply" in sys.argv

HOST = "http://127.0.0.1:8080"
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
resp = op.open(urllib.request.Request(
    HOST + "/api/v2/auth/login",
    data=urllib.parse.urlencode({"username": user, "password": pw}).encode(),
    headers={"Referer": HOST}), timeout=30).read()
if b"Ok" not in resp:
    print("LOGIN FAILED -- check the credential in op://zklw-migrate/qbit-jarmusch")
    sys.exit(1)
print("login ok; %d infohashes supplied" % len(hashes))

tor = json.loads(op.open(HOST + "/api/v2/torrents/info", timeout=120).read())
dupes = [t for t in tor if t["hash"].lower() in hashes]
uniq = [t for t in tor if t["hash"].lower() not in hashes]
print("jarmusch holds %d torrents" % len(tor))
print("  also on grey (duplicates) : %d" % len(dupes))
print("  unique to jarmusch        : %d   <- left alone" % len(uniq))


def announcing(state):
    return state not in ("pausedUP", "pausedDL", "stoppedUP", "stoppedDL",
                         "error", "missingFiles", "checkingUP", "checkingDL")


print("\nduplicate states:", dict(collections.Counter(t["state"] for t in dupes)))
live = [t for t in dupes if announcing(t["state"])]
print("ANNOUNCING duplicates -- the actual two-IP exposure: %d" % len(live))
print("uploaded by duplicates so far: %.2f GB"
      % (sum(t.get("uploaded", 0) for t in dupes) / 1024 ** 3))
print("unique-to-jarmusch states:", dict(collections.Counter(t["state"] for t in uniq)))

if not apply_:
    print("\nDRY RUN -- would pause %d announcing duplicates and leave %d unique "
          "torrents untouched. Re-run with --apply." % (len(live), len(uniq)))
    sys.exit(0)

if not live:
    print("\nnothing announcing; no action taken")
    sys.exit(0)

# qBittorrent renamed /pause to /stop in 5.x; try both so this works either way.
done = 0
for i in range(0, len(live), 50):
    chunk = "|".join(t["hash"] for t in live[i:i + 50])
    for endpoint in ("/api/v2/torrents/pause", "/api/v2/torrents/stop"):
        try:
            op.open(urllib.request.Request(
                HOST + endpoint,
                data=urllib.parse.urlencode({"hashes": chunk}).encode(),
                headers={"Referer": HOST}), timeout=60).read()
            done += len(live[i:i + 50])
            break
        except urllib.error.HTTPError:
            continue
print("\npaused %d duplicate torrents (data untouched; resume to undo)" % done)
