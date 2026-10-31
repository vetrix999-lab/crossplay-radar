#!/usr/bin/env python3
"""Conservative full-catalog crossplay discovery; unconfirmed discoveries remain review-only."""
import html, json, pathlib, re, time, urllib.request, urllib.parse
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
DB=ROOT/"data/games.json"
PAGE=ROOT/"index.html"
REPORT=ROOT/"data/catalog-audit.json"
SOURCES={
 "crossplaygames":"https://crossplaygames.com/crossplay?p1=playstation-5&p2=windows-pc",
 "crossplayguide":"https://crossplayguide.com/crossplay/pc-and-playstation/",
 "partyqueue":"https://partyqueue.games/discover/pc-playstation"
}
ALIASES={"minecraft":"Minecraft Bedrock","minecraft bedrock edition":"Minecraft Bedrock","fall guys ultimate knockout":"Fall Guys","diablo 4":"Diablo IV","ark survival ascended":"ARK: Survival Ascended","the texas chain saw massacre":"Texas Chain Saw Massacre","smite 2":"SMITE 2","no mans sky":"No Man's Sky","marvel rivals":"Marvel Rivals","call of duty black ops 6":"Call of Duty Black Ops 6","warhammer 40000 space marine 2":"Warhammer 40000 Space Marine 2","sid meiers civilization vii":"Civilization VII"}
def norm(s):
 s=html.unescape(s).lower().replace("’","'").replace("™","").replace("®","")
 return re.sub(r"[^a-z0-9]+"," ",s).strip()
def canonical(s):
 n=norm(s)
 return norm(ALIASES.get(n,s))
class Parser(HTMLParser):
 def __init__(self):
  super().__init__();self.tags=[];self.links=[];self.cells=[];self.rows=[];self.incell=False;self.cell=[];self.row=[];self.capture=False;self.text=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.tags.append(tag)
  if tag=="a":self.capture=True;self.text=[];self.href=a.get("href","")
  if tag=="tr":self.row=[]
  if tag in ("td","th"):self.incell=True;self.cell=[]
 def handle_data(self,data):
  if self.capture:self.text.append(data)
  if self.incell:self.cell.append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.capture:
   self.links.append((" ".join("".join(self.text).split()),self.href));self.capture=False
  if tag in ("td","th") and self.incell:
   self.row.append(" ".join("".join(self.cell).split()));self.incell=False
  if tag=="tr" and self.row:self.rows.append(self.row)
  if self.tags and self.tags[-1]==tag:self.tags.pop()
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 CrossplayRadar/2.0"})
 with urllib.request.urlopen(req,timeout=35) as r:return r.read().decode("utf-8","replace")
def collect():
 result={};errors={}
 for source,url in SOURCES.items():
  try:
   p=Parser();p.feed(fetch(url));games={}
   if source=="crossplaygames":
    # This page separates positive and negative sections; only the positive section is valid.
    raw=fetch(url);positive=raw.split("Cross-Platform Games for PS5 and Windows PC",1)[-1].split("Games Which Are Compatible With PS5 and Windows PC",1)[0]
    q=Parser();q.feed(positive)
    for title,href in q.links:
     if href and title and not href.startswith("#") and len(title)<90 and len(title)>2:games.setdefault(canonical(title),{"name":title,"url":urllib.parse.urljoin(url,href)})
   elif source=="crossplayguide":
    # Table rows explicitly indicate PC and PS5 in the same plays-together group.
    for row in p.rows:
     if len(row)<3:continue
     name,mode,platforms=row[:3]
     if mode.lower().strip() not in ("yes","mostly","partly"):continue
     if not re.search(r"\bPC\b",platforms) or not re.search(r"\bPS5\b",platforms):continue
     games[canonical(name)]={"name":name,"url":url,"mode":mode}
   else:
    # The collection is PC+PlayStation, so require an exact PS5 detail to avoid PS4-only entries.
    for title,href in p.links:
     if not href or len(title)>90 or len(title)<3:continue
     if not re.search(r"game|guide",href,re.I):continue
     games.setdefault(canonical(title),{"name":title,"url":urllib.parse.urljoin(url,href)})
   if len(games)<10:raise ValueError("Source yielded only %d entries; ignoring it"%len(games))
   result[source]=games
  except Exception as e:errors[source]=str(e)[:200]
  time.sleep(0.4)
 return result,errors
def main():
 db=json.loads(DB.read_text());games=db["games"];original=len(games)
 sources,errors=collect();bykey={canonical(g["name"]):g for g in games}
 evidence={}
 for source,items in sources.items():
  for key,item in items.items():evidence.setdefault(key,[]).append((source,item))
 new=[]
 for key,hits in evidence.items():
  if len({s for s,_ in hits})<2:continue
  if key in bykey:g=bykey[key]
  else:
   # New entries are *review candidates*, never automatically officially verified.
   display=next((v["name"] for s,v in hits if s=="crossplayguide"),hits[0][1]["name"])
   g={"id":max((x.get("id",0) for x in games),default=0)+1,"name":display,"genre":"Other","price":"Unknown","studio":"Unknown","status":"review","platforms":["PS5","PC"],"source":"","notes":"Independent crossplay-directory consensus; platform and game-mode restrictions require official verification.","image":"","verified":False,"crossProgression":"unknown","gfn":"unknown","gfnSource":"","coverStatus":"missing","crossplayAudit":"directory_consensus_needs_official_verification","gfnAudit":"not_verified"}
   games.append(g);bykey[key]=g;new.append(display)
  if g.get("crossplayAudit")=="ps5_pc_not_supported":continue
  g["crossplayConsensusSources"]=[v["url"] for s,v in hits]
  g["crossplayConsensusCount"]=len(hits)
  g["crossplayConsensusProviders"]=[s for s,v in hits]
  if not g.get("verified") and g.get("status")!="unsupported":
   g["status"]="review"
   g["crossplayAudit"]="directory_consensus_needs_official_verification"
 # Never demote existing official verification, and never delete when a source fails.
 db["games"]=games
 REPORT.write_text(json.dumps({"original":original,"total":len(games),"new":new,"sources":{s:len(x) for s,x in sources.items()},"errors":errors,"two_source_matches":sum(len({s for s,_ in h})>=2 for h in evidence.values()),"unverified":sum(not g.get("verified") for g in games)},ensure_ascii=False,indent=2)+"\n")
 DB.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n")
 page=PAGE.read_text();m=re.search(r"const EMBEDDED_CATALOG=([\s\S]*?);\nlet all=",page)
 if not m:raise RuntimeError("Embedded catalog marker missing")
 page=page[:m.start()]+"const EMBEDDED_CATALOG="+json.dumps(db,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+";\nlet all="+page[m.end():]
 PAGE.write_text(page)
 print(REPORT.read_text())
if __name__=="__main__":main()
