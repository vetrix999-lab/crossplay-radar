#!/usr/bin/env python3
"""Conservative NVIDIA first-party GFN confirmation; absence remains Unknown."""
import datetime as dt,html,json,pathlib,re,urllib.request
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE="https://nvidia.custhelp.com/app/answers/detail/a_id/4812/"
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)
def main():
 req=urllib.request.Request(SOURCE,headers={"User-Agent":"CrossplayRadar/1.0"})
 with urllib.request.urlopen(req,timeout=30) as resp:raw=resp.read(600000).decode("utf-8","replace")
 p=Text();p.feed(raw);body=" ".join(" ".join(p.parts).split())
 assert "available to play on GeForce NOW" in body, "NVIDIA confirmation sentence missing"
 # NVIDIA's explicit Highlights-compatible GFN games; narrow match to its list.
 start=body.index("The following games support Highlights")
 end=body.find("You can see the complete list",start)
 assert end>start,"Could not isolate NVIDIA official list"
 names=["Apex Legends","Counter-Strike 2","Cyberpunk 2077","Destiny 2","Dota 2"]
 official=body[start:end]
 confirmed=[name for name in names if re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",official,re.I)]
 dbpath=ROOT/"data/games.json";db=json.loads(dbpath.read_text());changed=[]
 for g in db["games"]:
  if g["name"] in confirmed:
   g["gfn"]="yes";g["gfnSource"]=SOURCE;g["gfnCheckedAt"]=dt.date.today().isoformat()
   g["gfnAudit"]="nvidia_official_highlights_compatible"
   g["gfnStore"]="unknown";g["gfnRegion"]="unknown";changed.append(g["name"])
  elif g.get("gfn") not in ("yes","no","unknown"):g["gfn"]="unknown"
 dbpath.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n")
 page=ROOT/"index.html";s=page.read_text()
 needle="const EMBEDDED_CATALOG=";a=s.index(needle)+len(needle);b=s.index(";\nlet all=",a)
 page.write_text(s[:a]+json.dumps(db,ensure_ascii=False,separators=(",",":")).replace("<","\u003c")+s[b:])
 report={"source":SOURCE,"date":dt.date.today().isoformat(),"nvidia_official_list":confirmed,"confirmed_in_catalog":changed,"yes":sum(g.get("gfn")=="yes" for g in db["games"]),"no":sum(g.get("gfn")=="no" for g in db["games"]),"unknown":sum(g.get("gfn")=="unknown" for g in db["games"]),"total":len(db["games"])}
 (ROOT/"data/gfn-audit.json").write_text(json.dumps(report,indent=2)+"\n")
 print(report,flush=True)
if __name__=="__main__":main()
