#!/usr/bin/env python3
"""Resume-safe official-source evidence triage across every catalog game.

Never auto-promotes: a text match cannot prove current PS5-PC multiplayer support.
"""
import datetime,json,pathlib,re,time,urllib.parse,urllib.request
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data/games.json";QUEUE=ROOT/"data/verification-queue.json"
ALLOWED=("ea.com","help.ea.com","news.ea.com","epicgames.com","playstation.com","2k.com","ubisoft.com","blizzard.com","seaofthieves.com","warthunder.com","arrowhead.zendesk.com","support.deadbydaylight.com","hazelight.se","minecraft.net","warframe.com","bungie.net","capcom.com","bethesda.net","square-enix-games.com","enlisted.net","rockstargames.com","steamcommunity.com")
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style","nav","footer"):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ("script","style","nav","footer"):self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def official(url):
 try:
  host=(urllib.parse.urlparse(url).hostname or "").lower()
  return any(host==d or host.endswith("."+d) for d in ALLOWED)
 except Exception:return False
def inspect(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 CrossplayRadarEvidenceAudit/1.0"})
 with urllib.request.urlopen(req,timeout=12) as response:
  typ=response.headers.get("Content-Type","")
  if "html" not in typ:return {"result":"not_html","http":response.status}
  raw=response.read(450000).decode("utf-8","replace")
 p=Text();p.feed(raw);content=" ".join(" ".join(p.parts).split()).lower()
 platform=bool(re.search(r"playstation\s*5|\bps5\b",content)) and bool(re.search(r"\bpc\b|windows|steam",content))
 cross=bool(re.search(r"cross[- ]play|cross[- ]platform play|play together across platforms",content))
 return {"result":"official_page_pair_and_crossplay_terms_needs_manual_context" if platform and cross else "official_page_insufficient_pair_evidence","http":200,"platform_terms":platform,"crossplay_terms":cross}
def main():
 db=json.loads(DATA.read_text());old={}
 if QUEUE.exists():
  try:old={x["name"]:x for x in json.loads(QUEUE.read_text()).get("items",[])}
  except Exception:pass
 today=datetime.date.today().isoformat();items=[];counts={}
 for n,g in enumerate(db["games"],1):
  name=g["name"];url=g.get("source","");verified=bool(g.get("verified"));rejected=g.get("status")=="unsupported"
  item={"name":name,"id":g.get("id"),"classification":"Rejected" if rejected else "Verified" if verified else "Pending","source":url,"checkedAt":g.get("crossplayCheckedAt"),"officialSource":official(url),"review":"not_checked","nextAction":"manual_official_pair_and_live_service_review"}
  previous=old.get(name,{})
  if official(url) and url.startswith("https://"):
   if previous.get("evidenceFetchedAt")==today and previous.get("source")==url:
    item.update({k:v for k,v in previous.items() if k in ("review","evidenceFetchedAt","error")})
   else:
    try:item["review"]=inspect(url);item["evidenceFetchedAt"]=today
    except Exception as e:item["review"]="fetch_failed";item["error"]=str(e)[:180]
    time.sleep(0.15)
  elif url:item["review"]="source_not_in_official_allowlist"
  else:item["review"]="no_source"
  if verified:item["nextAction"]="revalidate_live_service_and_official_context"
  if rejected:item["nextAction"]="periodically_check_relaunch_or_platform_changes"
  items.append(item);k=item["classification"];counts[k]=counts.get(k,0)+1
  if n%25==0:print("Official-source triage",n,"/",len(db["games"]),flush=True)
  # Save progress after every batch so the next run can resume if interrupted.
  if n%25==0:QUEUE.write_text(json.dumps({"processed":n,"total":len(db["games"]),"counts":counts,"items":items},ensure_ascii=False,indent=2)+"\n")
 QUEUE.write_text(json.dumps({"processed":len(items),"total":len(db["games"]),"counts":counts,"items":items},ensure_ascii=False,indent=2)+"\n")
 print(json.dumps({"processed":len(items),"counts":counts,"official_pages_attempted":sum(bool(x.get("evidenceFetchedAt")==today) for x in items)}),flush=True)
if __name__=="__main__":main()
