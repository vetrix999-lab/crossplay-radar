#!/usr/bin/env python3
"""Discover PS5-PC crossplay candidates from a platform-pair catalog; never auto-verify."""
import datetime as dt,html,json,pathlib,re,time,urllib.parse,urllib.request
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
DB=ROOT/"data/games.json";PAGE=ROOT/"index.html";REPORT=ROOT/"data/discovery-report.json"
LIST="https://crossplaygames.com/crossplay?p1=playstation-5&p2=windows-pc"
def request(url):
 req=urllib.request.Request(url,headers={"User-Agent":"CrossplayRadar/1.0 (public catalog discovery)"})
 with urllib.request.urlopen(req,timeout=25) as r:return r.read(1000000).decode("utf-8","replace")
class Links(HTMLParser):
 def __init__(self):super().__init__();self.href=None;self.buffer=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":self.href=dict(attrs).get("href");self.buffer=[]
 def handle_data(self,data):
  if self.href is not None:self.buffer.append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.href is not None:
   name=html.unescape(" ".join(self.buffer)).strip()
   if re.search(r"^https?://(?:www\.)?crossplaygames\.com/games/|^/games/",self.href) and name and len(name)<110:self.links.append((name,urllib.parse.urljoin(LIST,self.href)))
   self.href=None
def norm(name):return re.sub(r"[^a-z0-9]","",name.lower().replace("’","'").replace("™",""))
ALIASES={"diablo4":"diabloiv","fallguysultimateknockout":"fallguys","hoodoutlawslegends":"hoodoutlawsandlegends","finalfantasyxivonline":"finalfantasyxiv","theelderscrollsonline":"elderscrollsonline","tomclancysxdefiant":"xdefiant","rainbowsixsiege":"rainbowsixsiegex"}
EXCLUDE={"overwatch","tomclancysghostreconfrontline","spellbreak"}
def canonical(name):
 n=norm(name)
 return ALIASES.get(n,n)

SECONDARY_LISTS=[
 ("crossplayguide","https://crossplayguide.com/crossplay/pc-and-playstation/"),
 ("crossplayable","https://crossplayable.com/")
]
def secondary_candidates():
 candidates=[];reports=[]
 for label,url in SECONDARY_LISTS:
  try:
   raw=request(url)
   # Each candidate must have a linked game page and PS5 and PC in its local card.
   cards=re.split(r"</(?:article|tr|li)>",raw,flags=re.I)
   found=0
   for card in cards:
    visible=html.unescape(re.sub(r"<[^>]+>"," ",card))
    if not (re.search(r"\bPC\b",visible,re.I) and re.search(r"\bPS5\b",visible,re.I)):continue
    if not re.search(r"cross.?play|plays together",visible,re.I):continue
    match=re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',card,re.I|re.S)
    if not match:continue
    name=html.unescape(re.sub(r"<[^>]+>"," ",match.group(2))).strip()
    if not 3<=len(name)<=85:continue
    if name.lower() in ("skip to content","can we play?  crossplay ."):continue
    if urllib.parse.urlsplit(urllib.parse.urljoin(url,match.group(1))).path in ("","/"):continue
    if "#" in match.group(1):continue
    if re.search(r"crossplay games|view all|learn more",name,re.I):continue
    candidates.append((name,urllib.parse.urljoin(url,match.group(1)),label));found+=1
   reports.append({"source":label,"status":"ok","candidates":found,"url":url})
  except Exception as e:reports.append({"source":label,"status":"failed","error":str(e)[:160],"url":url})
 return candidates,reports

def main():
 catalog=json.loads(DB.read_text());games=catalog["games"];existing={canonical(g["name"]) for g in games}
 page=request(LIST);p=Links();p.feed(page)
 found={canonical(name):(name,url) for name,url in p.links}
 added=[];errors=[];secondary,source_results=secondary_candidates();nextid=max(g["id"] for g in games)+1
 for name,url in found.values():
  if canonical(name) in existing or canonical(name) in EXCLUDE:continue
  try:
   detail=request(url)
   # Source must explicitly describe PS5 and Windows PC crossplay on this game's page.
   plain=re.sub(r"<[^>]+>"," ",detail)
   plain=html.unescape(plain)
   if not re.search(r"supports crossplay across the following platforms.{0,260}PS5",plain,re.I|re.S):continue
   if not re.search(r"supports crossplay across the following platforms.{0,260}(?:Windows PC|Steam)",plain,re.I|re.S):continue
   record={"id":nextid,"name":name,"genre":"Unknown","price":"Unknown","studio":"Unknown","status":"review","platforms":["PS5","PC"],"ps5Availability":"secondary_listing_pending_official","pcAvailability":"secondary_listing_pending_official","source":url,"notes":"PS5-PC platform-pair candidate from CrossplayGames; official platform availability, service status and crossplay evidence not yet verified.","image":"","verified":False,"crossProgression":"unknown","gfn":"unknown","gfnSource":"","gfnCheckedAt":None,"coverStatus":"missing","crossplayAudit":"secondary_pair_listing_pending_official","crossplayCheckedAt":dt.date.today().isoformat()}
   games.append(record);existing.add(canonical(name));nextid+=1;added.append(name)
  except Exception as e:errors.append({"name":name,"error":str(e)[:150]})
  if len(added)%25==0 and added:print("New candidates",len(added),flush=True)
  time.sleep(.1)
 for name,url,provider in secondary:
  if canonical(name) in existing or canonical(name) in EXCLUDE:continue
  record={"id":nextid,"name":name,"genre":"Unknown","price":"Unknown","studio":"Unknown","status":"review","platforms":["PS5","PC"],"ps5Availability":"secondary_listing_pending_official","pcAvailability":"secondary_listing_pending_official","source":url,"notes":"PS5-PC crossplay candidate from "+provider+"; official confirmation pending.","image":"","verified":False,"crossProgression":"unknown","gfn":"unknown","gfnSource":"","coverStatus":"missing","crossplayAudit":"secondary_pair_listing_pending_official","crossplayCheckedAt":dt.date.today().isoformat()}
  games.append(record);existing.add(canonical(name));nextid+=1;added.append(name)
 catalog["updated"]=dt.date.today().isoformat()
 DB.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n")
 source=PAGE.read_text()
 replacement="const EMBEDDED_CATALOG="+json.dumps(catalog,ensure_ascii=False,separators=(",",":")).replace("<","\u003c")+";\nlet all="
 source,count=re.subn(r"const EMBEDDED_CATALOG=[\s\S]*?;\nlet all=",lambda _:replacement,source,count=1)
 if count!=1:raise RuntimeError("Could not update embedded catalog")
 PAGE.write_text(source)
 REPORT.write_text(json.dumps({"checked_at":dt.date.today().isoformat(),"listing":LIST,"listing_games":len(found),"additional_sources":source_results,"new_candidates":len(added),"names":added,"errors":errors,"catalog_total":len(games),"verified_promotions":0},ensure_ascii=False,indent=2)+"\n")
 print("Discovery complete",len(found),"listed,",len(added),"new,",len(games),"total",flush=True)
if __name__=="__main__":main()
