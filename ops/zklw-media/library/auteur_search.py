#!/usr/bin/env python3
"""Kick off searches for the auteur filmographies, in paced batches.

Scoped deliberately narrowly: only titles added by the auteur import lists (or
the Curtis features retuned alongside them). The pre-existing ~247-title library
is left untouched -- a blanket search would start re-downloading things that are
already fine.

Batched with pauses because these are private trackers. Radarr does pace its own
indexer calls, but firing ~140 searches as one command still produces a burst
worth spreading out.
"""
import argparse, json, re, time, urllib.error, urllib.request
HOST = "100.123.250.67"
AUTEUR_PROFILES = {"Archival-Best", "UHD-Remux"}
EXTRA_TITLES = {"bitter lake", "hypernormalisation"}   # retuned, added earlier


def key(s):
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("/home/mk/grey-media/config/%s/config.xml" % s).read()).group(1).strip()


def call(svc, port, method, path, body=None):
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:%d/api/v3/%s" % (HOST, port, path), data=d, method=method,
                               headers={"X-Api-Key": key(svc), "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=180).read()
    except urllib.error.HTTPError as e:
        print("   HTTP %s %s" % (e.code, e.read()[:200].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


rad = lambda m, p, b=None: call("radarr", 7878, m, p, b)
son = lambda m, p, b=None: call("sonarr", 8989, m, p, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--pause", type=int, default=45)
    a = ap.parse_args()

    prof = {p["id"]: p["name"] for p in rad("GET", "qualityprofile")}
    # A same-day string compare is wrong here: Radarr stamps `added` in UTC while
    # the box runs ahead of the operator's local date, so "today" silently
    # excluded most of the modern additions. A 48h window is unambiguous, and
    # safe because every recent addition to this library came from this job.
    import datetime
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    movies = rad("GET", "movie")

    targets = []
    for m in movies:
        if m.get("hasFile") or not m.get("monitored"):
            continue
        pname = prof.get(m["qualityProfileId"])
        if pname not in AUTEUR_PROFILES:
            continue
        # Archival-Best exists solely for this job, so everything on it is ours.
        # UHD-Remux predates it and holds unrelated library titles, so there it
        # is restricted to what was added today.
        if pname == "Archival-Best" or (m.get("added") or "") >= cutoff \
           or m["title"].lower() in EXTRA_TITLES:
            targets.append(m)

    print("radarr: %d titles to search" % len(targets))
    for m in sorted(targets, key=lambda x: (x.get("year") or 0))[:5]:
        print("   e.g. %s (%s)" % (m["title"], m.get("year")))

    series = [s for s in son("GET", "series")
              if s["qualityProfileId"] == next(
                  (p["id"] for p in son("GET", "qualityprofile") if p["name"] == "Archival-Best"), -1)]
    print("sonarr: %d series to search" % len(series))
    for s in series:
        print("   %s (%s)" % (s["title"], s.get("year")))

    if not a.apply:
        print("\nDRY RUN -- no searches issued.")
        return

    ids = [m["id"] for m in targets]
    for i in range(0, len(ids), a.batch):
        chunk = ids[i:i + a.batch]
        c = rad("POST", "command", {"name": "MoviesSearch", "movieIds": chunk})
        print("  movie batch %d-%d issued (cmd %s)" % (i + 1, i + len(chunk), c["id"] if c else "ERR"))
        if i + a.batch < len(ids):
            time.sleep(a.pause)

    for s in series:
        c = son("POST", "command", {"name": "SeriesSearch", "seriesId": s["id"]})
        print("  series search %-46s (cmd %s)" % (s["title"][:46], c["id"] if c else "ERR"))
        time.sleep(10)
    print("\nall searches issued")


main()
