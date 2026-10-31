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


class GuideParser(HTMLParser):
 def __init__(self):
  super().__init__();self.rows=[];self.row=None;self.cell=None;self.link=None;self.section="";self.heading=False;self.head=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag in ("h2","h3"):self.heading=True;self.head=[]
  if tag=="tr":self.row=[]
  if tag in ("td","th") and self.row is not None:self.cell={"text":[],"links":[]}
  if tag=="a" and self.cell is not None:self.link={"href":attrs.get("href",""),"text":[]}
 def handle_data(self,data):
  if self.heading:self.head.append(data)
  if self.cell is not None:self.cell["text"].append(data)
  if self.link is not None:self.link["text"].append(data)
 def handle_endtag(self,tag):
  if tag in ("h2","h3") and self.heading:
   h=" ".join(" ".join(self.head).split()).lower()
   if "checked by us" in h:self.section="checked"
   elif "not yet verified" in h:self.section="unverified"
   self.heading=False
  if tag=="a" and self.link is not None:
   self.link["text"]=" ".join(" ".join(self.link["text"]).split());self.cell["links"].append(self.link);self.link=None
  if tag in ("td","th") and self.cell is not None:
   self.cell["text"]=" ".join(" ".join(self.cell["text"]).split());self.row.append(self.cell);self.cell=None
  if tag=="tr" and self.row is not None:
   if len(self.row)>=3:self.rows.append((self.section,self.row))
   self.row=None
def guide_candidates(raw,base):
 parser=GuideParser();parser.feed(raw);records=[]
 for section,cells in parser.rows:
  if section not in ("checked","unverified"):continue
  name=cells[0]["text"];status=cells[1]["text"].lower();platforms=cells[2]["text"]
  if not 3<=len(name)<=100 or status not in ("yes","partly","mostly","yes, turn-based"):continue
  if not re.search(r"\bPC\b",platforms,re.I) or not re.search(r"\bPS5\b",platforms,re.I):continue
  links=[x for x in cells[0]["links"] if x["href"] and not x["href"].startswith("#")]
  url=urllib.parse.urljoin(base,links[0]["href"]) if links else ""
  if urllib.parse.urlsplit(url).netloc not in ("crossplayguide.com","www.crossplayguide.com"):continue
  records.append((name,url,"crossplayguide",section,status))
 return records,{"table_rows":len(parser.rows),"valid_pair_records":len(records),"checked":sum(x[3]=="checked" for x in records),"unverified":sum(x[3]=="unverified" for x in records)}

SECONDARY_LISTS=[
 ("crossplayguide","https://crossplayguide.com/crossplay/pc-and-playstation/"),
 ("crossplayable","https://crossplayable.com/")
]
def secondary_candidates():
 candidates=[];reports=[]
 for label,url in SECONDARY_LISTS:
  try:
   if label=="crossplayguide":
    raw=request(url)
    records,counts=guide_candidates(raw,url)
    if counts["valid_pair_records"]<40:raise RuntimeError("Structured game table too small; refuse to import navigation")
    candidates.extend(records)
    reports.append({"source":label,"status":"parsed","url":url,**counts})
   else:
    # Crossplayable requires a separate verified card parser; do not import navigation.
    raw=request("https://crossplayable.com/pairs/steam-ps5")
    reports.append({"source":label,"status":"reachable_not_imported","url":"https://crossplayable.com/pairs/steam-ps5","bytes":len(raw),"reason":"No validated record-level extractor; navigation excluded"})
  except Exception as e:reports.append({"source":label,"status":"failed","url":url,"error":str(e)[:160]})
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
   record={"id":nextid,"name":name,"genre":"Unknown","price":"Unknown","studio":"Unknown","status":"review","platforms":["PS5","PC"],"ps5Availability":"secondary_listing_pending_official","pcAvailability":"secondary_listing_pending_official","source":url,"notes":"PS5-PC platform-pair candidate from CrossplayGames; official platform availability, service status and crossplay evidence not yet verified.","image":"","verified":False,"crossProgression":"unknown","gfn":"unknown","gfnSource":"","gfnCheckedAt":None,"coverStatus":"missing","crossplayAudit":"secondary_pair_listing_pending_official","crossplaySourceSection":section,"crossplaySourceStatus":pair_status,"crossplayCheckedAt":dt.date.today().isoformat()}
   games.append(record);existing.add(canonical(name));nextid+=1;added.append(name)
  except Exception as e:errors.append({"name":name,"error":str(e)[:150]})
  if len(added)%25==0 and added:print("New candidates",len(added),flush=True)
  time.sleep(.1)
 for name,url,provider,section,pair_status in secondary:
  if canonical(name) in existing or canonical(name) in EXCLUDE:continue
  record={"id":nextid,"name":name,"genre":"Unknown","price":"Unknown","studio":"Unknown","status":"review","platforms":["PS5","PC"],"ps5Availability":"secondary_listing_pending_official","pcAvailability":"secondary_listing_pending_official","source":url,"notes":"PS5-PC crossplay candidate from "+provider+" ("+section+", "+pair_status+"); official confirmation pending.","image":"","verified":False,"crossProgression":"unknown","gfn":"unknown","gfnSource":"","coverStatus":"missing","crossplayAudit":"secondary_pair_listing_pending_official","crossplayCheckedAt":dt.date.today().isoformat()}
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
