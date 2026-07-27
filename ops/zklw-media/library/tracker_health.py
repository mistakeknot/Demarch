#!/usr/bin/env python3
import json, urllib.parse, urllib.request, http.cookiejar, collections, yaml
cfg = yaml.safe_load(open("/home/mk/grey-media/config/qbit-manage/config.yml")); q = cfg["qbt"]
host = "http://100.123.250.67:8080"
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request(host+"/api/v2/auth/login",
    data=urllib.parse.urlencode({"username": q.get("user"), "password": q.get("pass")}).encode(),
    headers={"Referer": host}), timeout=30).read()
tor = json.loads(op.open(host+"/api/v2/torrents/info", timeout=120).read())
STAT = {0:"disabled",1:"not contacted",2:"working",3:"updating",4:"NOT WORKING"}
agg = collections.defaultdict(collections.Counter); msgs = collections.defaultdict(collections.Counter)
peers = collections.defaultdict(int); states = collections.defaultdict(collections.Counter)
for t in tor[:600]:
    tag = next((x for x in (t.get("tags") or "").split(", ")
                if x in ("hdbits","karagarga","torrentleech","ratio-race")), "untagged")
    states[tag][t["state"]] += 1
    peers[tag] += t.get("num_leechs", 0)
    try:
        trs = json.loads(op.open(host+"/api/v2/torrents/trackers?hash="+t["hash"], timeout=30).read())
    except Exception: continue
    for tr in trs:
        if tr["url"].startswith(("**","[DHT","[PeX","[LSD")): continue
        agg[tag][STAT.get(tr["status"], tr["status"])] += 1
        if tr.get("msg"): msgs[tag][tr["msg"][:70]] += 1
for tag in sorted(agg):
    print("\n== %s ==" % tag)
    print("  tracker status:", dict(agg[tag]))
    print("  states:", dict(states[tag]))
    print("  total leechers visible on our torrents:", peers[tag])
    if msgs[tag]: print("  messages:", dict(msgs[tag].most_common(6)))
