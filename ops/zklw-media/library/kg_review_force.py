#!/usr/bin/env python3
"""Clear the residue of the KG adoption review queue.

`kg_adopt.py` bails on ANY rejection Radarr reports for a manual-import
candidate. That is the right default, but it strands files over rejections that
are advisory rather than disqualifying:

  "Unknown Movie"              Radarr could not parse a title out of the
                               filename. Irrelevant here -- adoption supplies
                               the movieId explicitly, so nothing is being
                               guessed. KG filenames are frequently untitled
                               (e.g. "Out of the Way!.mkv"), which is the same
                               naming problem that made KG releases parse as
                               quality Unknown.

  "No audio tracks detected"   Correct, and not a defect: Khabarda (1931) is a
                               Georgian SILENT film. Rejecting silent cinema for
                               having no audio is a rule meeting content it was
                               never written for.

Anything NOT on that allow-list still blocks, so a genuinely broken file is not
force-imported.

Import uses importMode=copy against a Radarr with copyUsingHardlinks enabled, so
the library entry and the seeding copy in /data/Movies are the same bytes. The
script asserts that rather than assuming it: a real copy would silently double
the disk for every file it touched.

Dry-run by default; --apply is opt-in.
"""
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import unicodedata

HOST = "100.123.250.67"
CFG = "/home/mk/grey-media/config"
OPS = "/root/grey-ops"
SRC = "/data/Movies"
PROGRESS = "%s/kg-adoption-progress.jsonl" % OPS

# Rejections that do not indicate a bad file, given we supply the movieId.
ALLOWED_REJECTIONS = {
    "unknown movie",
    "no audio tracks detected",
}


def key():
    return re.search(r"<ApiKey>([^<]+)</ApiKey>",
                     open("%s/radarr/config.xml" % CFG).read()).group(1).strip()


def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://%s:7878/api/v3%s" % (HOST, path),
                               data=data, method=method,
                               headers={"X-Api-Key": key(),
                                        "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(r, timeout=300).read()
    except urllib.error.HTTPError as e:
        print("      HTTP %s %s" % (e.code, e.read()[:200].decode("utf8", "replace")))
        return None
    return json.loads(raw) if raw else None


def latest_rows():
    out = {}
    for line in open(PROGRESS):
        line = line.strip()
        if line:
            e = json.loads(line)
            out[e.get("dir")] = e
    return out


def movieid_map():
    """dir -> Radarr movieId, from wherever it was recorded.

    kg_adopt omits movieId when it records a `rejected` row, but it keeps it in
    the report's review_from_import list, so the two sources have to be merged
    or most rejected rows look unresolvable when they are not.
    """
    m = {}
    try:
        rep = json.load(open("%s/kg-adoption-report.json" % OPS))
    except (OSError, ValueError):
        rep = {}
    for e in rep.get("review_from_import", []):
        if e.get("dir") and e.get("movieId"):
            m[e["dir"]] = e["movieId"]
    for d, e in latest_rows().items():
        if e.get("movieId"):
            m[d] = e["movieId"]
    return m


def record(entry):
    with open(PROGRESS, "a") as f:
        f.write(json.dumps(entry) + "\n")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def resolve_by_name(d, library):
    """Match a KG folder name back to a Radarr movie.

    kg_adopt adds the movie to Radarr BEFORE attempting import, so for a row
    that failed at the import stage the movie already exists -- the id just was
    not written down. Recovering it by name is safe because the year has to
    agree too, and KG folder names carry the year.

    KG names are awkward in three predictable ways, all handled here:
      "Je, tu, il, elle AKA I, You, He, She (1976)"  -> either side of the AKA
      "Touchez pas au grisbi [+Extras] (1954)"       -> bracket junk
      accents and punctuation vary between KG and TMDb
    """
    m = re.search(r"\((\d{4})\)\s*$", d)
    if not m:
        return None
    year = int(m.group(1))
    stem = d[:m.start()].strip()
    stem = re.sub(r"\[[^\]]*\]", " ", stem)
    parts = [p.strip() for p in re.split(r"\bAKA\b", stem, flags=re.I) if p.strip()]
    wanted = {norm(p) for p in parts if p}
    hits = []
    for mv in library:
        # +/-2: KG folder year, the release filename year and TMDb's year
        # routinely disagree by a year or two on older films (Je, tu, il, elle
        # is variously 1974, 1975 and 1976). The exact normalised title match
        # below is what actually makes this safe, not the year window.
        if abs((mv.get("year") or 0) - year) > 2:
            continue
        titles = {norm(mv.get("title"))} | {norm(t) for t in (mv.get("alternateTitles") or [])
                                            if isinstance(t, str)}
        titles |= {norm(t.get("title")) for t in (mv.get("alternateTitles") or [])
                   if isinstance(t, dict)}
        if titles & wanted:
            hits.append(mv)
    # Only accept an unambiguous match; two candidates means a human should look.
    return hits[0]["id"] if len(hits) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    mm = api("/config/mediamanagement") or {}
    if not mm.get("copyUsingHardlinks"):
        print("REFUSING: copyUsingHardlinks is off -- importMode=copy would "
              "duplicate every file instead of hardlinking.")
        return
    print("hardlinks enabled; importMode=copy will link, not duplicate\n")

    rows = latest_rows()
    mids = movieid_map()
    library = api("/movie") or []
    targets = [(d, e) for d, e in sorted(rows.items())
               if e.get("status") == "review" and e.get("reason") == "rejected"]
    print("review rows with reason=rejected: %d" % len(targets))

    for d, e in targets:
        rej = [str(x).lower() for x in (e.get("rejections") or [])]
        blocking = [x for x in rej if x not in ALLOWED_REJECTIONS]
        if blocking:
            print("  SKIP %-52s blocking rejection: %s" % (d[:52], blocking))
            continue
        mid = e.get("movieId") or mids.get(d)
        folder = os.path.join(SRC, d)
        items = api("/manualimport?folder=" + urllib.parse.quote(folder)
                    + "&filterExistingFiles=true") or []
        vids = [i for i in items if (i.get("size") or 0) > 200 * 1024 ** 2]
        if not vids:
            print("  SKIP %-52s no video item returned" % d[:52])
            continue
        main_item = max(vids, key=lambda i: i.get("size", 0))
        if not mid:
            mid = (main_item.get("movie") or {}).get("id")
        if not mid:
            mid = resolve_by_name(d, library)
        if not mid:
            print("  SKIP %-52s no movieId known (needs a manual match)" % d[:52])
            continue
        if not a.apply:
            print("  DRY-RUN %-48s -> movieId=%s  %.2f GB  overriding %s"
                  % (d[:48], mid, main_item.get("size", 0) / 1024 ** 3, rej))
            continue

        f = {"path": main_item["path"], "movieId": mid,
             "quality": main_item["quality"],
             "languages": main_item.get("languages") or []}
        if main_item.get("releaseGroup"):
            f["releaseGroup"] = main_item["releaseGroup"]
        cmd = api("/command", "POST", {"name": "ManualImport", "files": [f],
                                       "importMode": "copy"})
        import time
        st = {}
        for _ in range(90):
            st = api("/command/%d" % cmd["id"]) or {}
            if st.get("status") in ("completed", "failed", "aborted"):
                break
            time.sleep(1)
        mf = api("/moviefile?movieId=%s" % mid) or []
        if mf:
            p = mf[0]["path"]
            nlink = os.stat(p).st_nlink if os.path.exists(p) else 0
            print("  IMPORTED %-46s nlink=%d %s" % (d[:46], nlink, p[:44]))
            record({"dir": d, "status": "imported", "movieId": mid,
                    "file": p, "nlink": nlink,
                    "forced_over": rej, "via": "kg_review_force"})
        else:
            print("  FAILED   %-46s command=%s" % (d[:46], st.get("status")))

    if not a.apply:
        print("\nDRY RUN -- nothing changed.")


main()
