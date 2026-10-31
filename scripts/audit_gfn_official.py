#!/usr/bin/env python3
"""Conservative GeForce NOW audit from NVIDIA's own explicit game list."""
import datetime as dt,json,pathlib,re,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
DB=ROOT/"data/games.json"
PAGE=ROOT/"index.html"
REPORT=ROOT/"data/gfn-audit.json"
SOURCE="https://nvidia.custhelp.com/app/answers/detail/a_id/4812/"
NAMES=("Apex Legends","Counter-Strike 2","Cyberpunk 2077","Destiny 2","Dota 2")
def main():
 req=urllib.request.Request(SOURCE,headers={"User-Agent":"CrossplayRadar/1.0","Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=25) as response:
  raw=response.read(400000).decode("utf-8","replace")
 plain=re.sub(r"<[^>]+>"," ",raw)
 plain=" ".join(plain.split())
 if not ("GeForce NOW" in plain and "Highlights" in plain):
  raise RuntimeError("NVIDIA source structure changed; refuse promotions")
 db=json.loads(DB.read_text());matched=[]
 for g in db["games"]:
  name=g["name"]
  if name in NAMES and re.search(r"(?<![\w])"+re.escape(name)+r"(?![\w])",plain,re.I):
   g["gfn"]="yes";g["gfnSource"]=SOURCE;g["gfnCheckedAt"]=dt.date.today().isoformat()
   g["gfnAudit"]="official_nvidia_support_page_explicitly_lists_game"
   g["gfnStore"]="unknown";g["gfnRegion"]="regional_availability_may_vary"
   matched.append(name)
  elif g.get("gfn") not in ("yes","no"):
   g["gfn"]="unknown"
 if not matched:raise RuntimeError("No exact-title NVIDIA matches; refuse empty audit")
 DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n")
 page=PAGE.read_text();start=page.index("const EMBEDDED_CATALOG=")+len("const EMBEDDED_CATALOG=")
 end=page.index(";\nlet all=",start)
 PAGE.write_text(page[:start]+json.dumps(db,ensure_ascii=False,separators=(",",":")).replace("<","\u003c")+page[end:])
 REPORT.write_text(json.dumps({"date":dt.date.today().isoformat(),"source":SOURCE,"official_confirmed":matched,"yes":sum(g.get("gfn")=="yes" for g in db["games"]),"no":sum(g.get("gfn")=="no" for g in db["games"]),"unknown":sum(g.get("gfn")=="unknown" for g in db["games"]),"total":len(db["games"]),"scope":"NVIDIA support article explicitly lists a small subset, not complete GFN catalog"},ensure_ascii=False,indent=2)+"\n")
 print("Official NVIDIA confirmed",matched,flush=True)
if __name__=="__main__":main()
