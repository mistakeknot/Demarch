#!/usr/bin/env python3
"""Live grab test: pull one clean Karagarga release through Radarr."""
import json, re, sys, urllib.request, urllib.error
H="100.123.250.67"; C="/home/mk/grey-media/config"
def k(d): return re.search(r"<ApiKey>([^<]+)</ApiKey>",open("%s/%s/config.xml"%(C,d)).read()).group(1).strip()
def api(method,path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request("http://%s:7878/api/v3/%s"%(H,path),data=data,method=method,
        headers={"X-Api-Key":k("radarr"),"Content-Type":"application/json"})
    try: return json.loads(urllib.request.urlopen(r,timeout=300).read() or b"null")
    except urllib.error.HTTPError as e:
        print("   HTTP",e.code,e.read()[:300].decode("utf8","replace")); return None
rel=api("GET","release?movieId=786") or []
kg=[r for r in rel if "Karagarga" in (r.get("indexer") or "") and not r.get("rejections")]
if not kg: print("no clean KG release"); sys.exit(1)
pick=sorted(kg,key=lambda x:-x.get("size",0))[0]
print("grabbing: %s"%pick.get("title"))
print("  %.2f GB  seeders=%s  indexer=%s"%(pick.get("size",0)/1024**3,pick.get("seeders"),pick.get("indexer")))
out=api("POST","release",pick)
print("  grab response:", "accepted" if out is not None else "FAILED")
