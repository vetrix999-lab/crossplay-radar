#!/usr/bin/env python3
"""Match catalog titles against Steam's public store search; never use fuzzy cover matches."""
import json, re, time, urllib.parse, urllib.request, pathlib, html
ROOT=pathlib.Path(__file__).resolve().parents[1]
DB=ROOT/"data/games.json"
PAGE=ROOT/"index.html"
def key(s):
    s=html.unescape(s).lower().replace("’","'").replace("™","").replace("®","")
    return re.sub(r"[^a-z0-9]","",s)
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"CrossplayRadarCatalog/1.0 (GitHub Pages project)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def image_ok(url):
    try:
        req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=10) as r:return r.status==200 and "image/" in r.headers.get("Content-Type","")
    except Exception:return False
db=json.loads(DB.read_text())
games=db["games"]
changed=0; checked=0; failures=[]
for i,g in enumerate(games):
    if g.get("image") and image_ok(g["image"]):
        g["coverStatus"]="http_verified"
        continue
    if g.get("image"):
        g["coverStatus"]="url_failed_review"
    name=g["name"]
    try:
        query=urllib.parse.urlencode({"term":name,"l":"en","cc":"us"})
        result=get("https://store.steampowered.com/api/storesearch/?"+query)
        items=result.get("items",[])
        exact=[item for item in items if key(item.get("name",""))==key(name)]
        if len(exact)!=1:
            failures.append(name+": no unique exact Steam match")
            continue
        item=exact[0]
        appid=item["id"]
        cover=f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
        if not image_ok(cover):
            failures.append(name+": cover unavailable")
            continue
        g["coverStatus"]="http_verified"
        g["steamAppId"]=appid
        g["image"]=cover
        g["imageSource"]=f"https://store.steampowered.com/app/{appid}/"
        changed+=1
    except Exception as exc:
        g["coverStatus"]="missing" if not g.get("image") else "url_failed_review"
        failures.append(name+": "+str(exc)[:80])
    checked+=1
    time.sleep(0.5)
# Keep embedded catalog in sync so GitHub Pages works without separate JSON fetch.
DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n")
page=PAGE.read_text()
prefix="const EMBEDDED_CATALOG="
start=page.index(prefix)+len(prefix)
end=page.index(";
let all=",start)
payload=json.dumps(db,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
page=page[:start]+payload+page[end:]
PAGE.write_text(page)
print(f"Total {len(games)}; covers {sum(bool(g.get('image')) for g in games)}; newly matched {changed}; requests {checked}")
print("Unmatched (review manually):")
print("\n".join(failures))
(ROOT/"data/cover-audit.txt").write_text("
".join(failures)+"\n")
