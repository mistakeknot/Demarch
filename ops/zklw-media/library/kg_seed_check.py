#!/usr/bin/env python3
"""Verify the Karagarga test grab is present and seeding, cleanup untouched."""
import json, urllib.parse, urllib.request, http.cookiejar, yaml, time
cfg=yaml.safe_load(open("/home/mk/grey-media/config/qbit-manage/config.yml")); q=cfg["qbt"]
host="http://100.123.250.67:8080"
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request(host+"/api/v2/auth/login",
    data=urllib.parse.urlencode({"username":q.get("user"),"password":q.get("pass")}).encode(),
    headers={"Referer":host}),timeout=30).read()
tor=json.loads(op.open(host+"/api/v2/torrents/info",timeout=120).read())
hits=[t for t in tor if "Recess" in t["name"] or "Zang-e Tafrih" in t["name"]]
if not hits:
    print("TEST TORRENT NOT FOUND in qBittorrent"); raise SystemExit(1)
for t in hits:
    print("name       : %s"%t["name"][:78])
    print("state      : %s"%t["state"])
    print("progress   : %.1f%%"%(t["progress"]*100))
    print("tags       : %r"%t.get("tags"))
    print("category   : %r"%t.get("category"))
    print("save_path  : %s"%t.get("save_path"))
    print("ratio      : %.3f   uploaded=%.1f MB"%(t.get("ratio",0),t.get("uploaded",0)/1024**2))
    print("added_on   : %s"%time.strftime("%FT%TZ",time.gmtime(t.get("added_on",0))))
    print("seeding_for: %d min"%(t.get("seeding_time",0)//60))
    print("ratio_limit: %s  seeding_time_limit: %s  (-2 = use global, qbit-manage owns these)"%(
        t.get("ratio_limit"), t.get("seeding_time_limit")))
    trs=json.loads(op.open(host+"/api/v2/torrents/trackers?hash="+t["hash"],timeout=30).read())
    for tr in trs:
        if tr["url"].startswith(("**","[DHT","[PeX","[LSD")): continue
        print("tracker    : status=%s msg=%r url=%s"%(tr["status"],tr.get("msg","")[:40],tr["url"][:52]))
