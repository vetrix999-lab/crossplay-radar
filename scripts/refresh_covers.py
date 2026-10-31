#!/usr/bin/env python3
"""Audit every cover with actual image bytes; exact Steam and Wikipedia fallbacks."""
import html, json, pathlib, re, time, urllib.error, urllib.parse, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
DB=ROOT/"data/games.json"
PAGE=ROOT/"index.html"
REPORT=ROOT/"data/cover-audit.json"
def key(s):
    s=html.unescape(s).lower().replace("’","'").replace("™","").replace("®","")
    return re.sub(r"[^a-z0-9]","",s)
def request(url,accept="application/json",limit=600000):
    req=urllib.request.Request(url,headers={"User-Agent":"CrossplayRadarCatalog/2.1 (GitHub public catalog; contact via repository issues)","Accept":accept})
    with urllib.request.urlopen(req,timeout=13) as r:
        return r.status,r.headers.get("Content-Type","").lower(),r.read(limit)
def get_json(url):
    status,typ,data=request(url)
    if status!=200:return {}
    return json.loads(data)
def image_ok(url):
    if not url.startswith("https://"):return False
    try:
        status,typ,data=request(url,"image/avif,image/webp,image/png,image/jpeg,image/*",128)
        if status!=200 or not typ.startswith("image/"):return False
        return (data.startswith(b"\\xff\\xd8\\xff") or data.startswith(b"\\x89PNG\\r\\n\\x1a\\n") or data.startswith(b"GIF87a") or data.startswith(b"GIF89a") or data.startswith(b"RIFF") and data[8:12]==b"WEBP" or data.startswith(b"\\x00\\x00\\x00") and b"ftypavif" in data[:32])
    except Exception:return False
def steam_candidates(name,appid=None):
    if appid:
        for stem in ("https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/","https://cdn.akamai.steamstatic.com/steam/apps/"):
            yield stem+str(appid)+"/header.jpg", "https://store.steampowered.com/app/"+str(appid)+"/", "steam_exact"
    try:
        result=get_json("https://store.steampowered.com/api/storesearch/?"+urllib.parse.urlencode({"term":name,"l":"en","cc":"us"}))
        exact=[x for x in result.get("items",[]) if key(x.get("name",""))==key(name)]
        if len(exact)==1:
            appid=exact[0]["id"]
            for stem in ("https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/","https://cdn.akamai.steamstatic.com/steam/apps/"):
                yield stem+str(appid)+"/header.jpg","https://store.steampowered.com/app/"+str(appid)+"/","steam_exact"
    except Exception:pass
def wiki_candidates(name):
    # A fallback illustration, NOT asserted to be the game's official box cover.
    try:
        url="https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(name.replace(" ","_"),safe="")
        obj=get_json(url)
        title=obj.get("title","")
        description=(obj.get("description") or "").lower()
        if key(title)!=key(name) or not any(t in description for t in ("video game","game series","online game","multiplayer game")):return
        thumbnail=(obj.get("thumbnail") or {}).get("source","")
        if thumbnail.startswith("https://"):
            yield thumbnail,obj.get("content_urls",{}).get("desktop",{}).get("page",url),"wikipedia_illustration"
    except Exception:return
def main():
    db=json.loads(DB.read_text());games=db["games"]
    stats={"total":len(games),"existing_checked":0,"existing_passed":0,"existing_failed":0,"steam_added":0,"fallback_added":0,"missing":0,"http_content_verified":0}
    failures=[]
    for index,g in enumerate(games,1):
        existing=g.get("image","")
        valid=False
        if existing:
            stats["existing_checked"]+=1
            valid=image_ok(existing)
            stats["existing_passed" if valid else "existing_failed"]+=1
        if valid:
            g["coverStatus"]="http_content_verified"
            g["coverCheckedAt"]=__import__("datetime").date.today().isoformat()
            stats["http_content_verified"]+=1
            continue
        found=False
        for url,source,kind in list(steam_candidates(g["name"],g.get("steamAppId")))+list(wiki_candidates(g["name"])):
            if image_ok(url):
                g["image"]=url;g["imageSource"]=source;g["coverStatus"]="http_content_verified"
                g["coverCheckedAt"]=__import__("datetime").date.today().isoformat()
                g["coverMatchType"]=kind
                if kind=="steam_exact":stats["steam_added"]+=1
                else:stats["fallback_added"]+=1
                stats["http_content_verified"]+=1;found=True;break
        if not found:
            g["coverStatus"]="url_failed_review" if existing else "missing"
            if not existing:stats["missing"]+=1
            failures.append({"name":g["name"],"reason":"No validated image from exact-title sources","existing_url":existing})
        if index%25==0:print("Cover audit progress",index,"/",len(games),flush=True)
        time.sleep(0.15)
    DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\\n")
    page=PAGE.read_text();prefix="const EMBEDDED_CATALOG=";start=page.index(prefix)+len(prefix)
    end=page.index(";\\nlet all=",start)
    page=page[:start]+json.dumps(db,ensure_ascii=False,separators=(",",":")).replace("<","\\\\u003c")+page[end:]
    PAGE.write_text(page)
    REPORT.write_text(json.dumps({"stats":stats,"unresolved":failures},ensure_ascii=False,indent=2)+"\\n")
    (ROOT/"data/cover-audit.txt").write_text("\\n".join(x["name"]+": "+x["reason"] for x in failures)+"\\n")
    print(json.dumps(stats),flush=True)
if __name__=="__main__":main()
