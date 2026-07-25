"""Stop (never delete) the 6 Karagarga featured torrents whose tracker asks
seeders to step back. Reversible: files untouched, torrent entries retained.
Usage: kg_stop6.py [dry|apply]"""
import json,subprocess,sys
CFG="/home/mk/grey-media/config"; U="http://100.123.250.67:8080"
MODE=sys.argv[1] if len(sys.argv)>1 else "dry"
def qbpass():
    inblk=False
    for line in open(f"{CFG}/qbit-manage/config.yml",encoding="utf-8"):
        s=line.strip()
        if s.startswith("qbt:"): inblk=True; continue
        if inblk and line[:1] not in (" ","\t","\n","#"): break
        if inblk and s.startswith("pass:"): return s.split("pass:",1)[1].strip().strip("'\"")
    return ""
subprocess.run(["curl","-s","-c","/tmp/.s6","-H",f"Referer: {U}","-H",f"Origin: {U}",
  "--data-urlencode","username=admin","--data-urlencode",f"password={qbpass()}",
  f"{U}/api/v2/auth/login","-o","/dev/null"],capture_output=True)
def g(p):
    return json.loads(subprocess.run(["curl","-s","-b","/tmp/.s6",f"{U}{p}"],capture_output=True,text=True).stdout or "[]")
SIX=["1d8e950436d6fa0a51a2179d1c8de0261575b54e","b5e50dd668d7b5bdac87d81b1f9813c45c10011e",
     "d210b6efc41c2a5c20c775d2b516f7bc7e6d4237","2209a7e31396630fdf87adb8d869dc7179877167",
     "0e3703abb064ddfd7b7ac769534539b8c70e2b93","4d68bd6287c2a59f1b403e40c0d5b9c08d5146a0"]
acted=0
for h in SIX:
    info=g(f"/api/v2/torrents/info?hashes={h}")
    if not info: print(f"SKIP  (absent) {h[:12]}"); continue
    t=info[0]
    trs=[x for x in g(f"/api/v2/torrents/trackers?hash={h}") if x["url"].startswith("http")]
    msg=(trs[0].get("msg") or "") if trs else ""
    # guard on the FULL message — truncating before matching is how the first
    # attempt silently skipped everything
    if "time for others" not in msg:
        print(f"SKIP  {t['name'][:50]} — msg no longer the featured notice: {msg[:60]!r}")
        continue
    # guard: never stop something that is actively uploading to a real leecher
    if t.get("num_leechs",0) > 0 or t.get("upspeed",0) > 0:
        print(f"SKIP  {t['name'][:50]} — actively uploading (leechers={t.get('num_leechs')}, {t.get('upspeed')}B/s)")
        continue
    if MODE=="apply":
        rc=subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-b","/tmp/.s6",
          "-H",f"Referer: {U}","--data",f"hashes={h}",f"{U}/api/v2/torrents/stop"],
          capture_output=True,text=True).stdout
        print(f"STOPPED http={rc}  {t['name'][:52]}"); acted+=1
    else:
        print(f"WOULD STOP  {t['name'][:52]}  (seeds={t.get('num_complete')}, leechers={t.get('num_incomplete')})")
print(f"\n--- states now ---")
for h in SIX:
    d=g(f"/api/v2/torrents/info?hashes={h}")
    print(f"  {d[0]['state']:12s} {d[0]['name'][:52]}" if d else f"  ABSENT {h[:12]}")
allt=g("/api/v2/torrents/info")
import collections
print(f"\ntotal {len(allt)} torrents; states {dict(collections.Counter(x['state'] for x in allt))}")
print(f"acted on {acted}")
