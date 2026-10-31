#!/usr/bin/env python3
"""Review existing Brave evidence; no new searches or automatic verification."""
import datetime as dt,json,pathlib,re,time,urllib.parse,urllib.request,urllib.error
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
INPUT=ROOT/"data/evidence-search-state.json"
OUTPUT=ROOT/"data/evidence-content-review.json"
REPORT=ROOT/"data/evidence-content-report.json"
COMMUNITY=("steamcommunity.com","reddit.com","forums.","community.","answers.")
def category(url):
 host=(urllib.parse.urlsplit(url).hostname or "").lower()
 if any(x in host for x in COMMUNITY) or "/discussions/" in url:return "community"
 if host.endswith(("steampowered.com","playstation.com","epicgames.com","ea.com","ubisoft.com","2k.com","activision.com","callofduty.com","bethesda.net","blizzard.com","minecraft.net","warframe.com","bungie.net","nvidia.com","xbox.com","microsoft.com","capcom.com","square-enix-games.com","bandainamcoent.com","hazelight.se","seaofthieves.com","warthunder.com","deadbydaylight.com","riotgames.com","neteasegames.com","gearboxsoftware.com","team17.com")):return "official_candidate"
 return "unclassified"
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style","nav","footer"):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ("script","style","nav","footer"):self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
def retrieve(url):
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"CrossplayRadar/1.0 evidence audit","Accept":"text/html"})
  with urllib.request.urlopen(req,timeout=14) as r:
   if "html" not in r.headers.get("Content-Type","").lower():return "not_html",""
   raw=r.read(500000)
  p=Parser();p.feed(raw.decode("utf-8","replace"))
  return "ok"," ".join(" ".join(p.parts).split())
 except urllib.error.HTTPError as e:return "http_"+str(e.code),""
 except Exception as e:return "fetch_error:"+str(e)[:80],""
def evaluate(name,content):
 lower=content.lower()
 cross=list(re.finditer(r"cross[- ]play|cross[- ]platform(?: multiplayer| play)?|play (?:together|with friends) across platforms",lower))
 windows=[]
 for match in cross[:20]:
  snippet=content[max(0,match.start()-240):min(len(content),match.end()+280)]
  s=snippet.lower()
  ps=bool(re.search(r"\bps5\b|playstation\s*5|playstation\s*4",s))
  pc=bool(re.search(r"\bpc\b|steam|windows",s))
  neg=bool(re.search(r"no cross[- ]play|does not support cross[- ]play|cross[- ]progression only|cross[- ]save only",s))
  if ps and pc and not neg:windows.append(snippet[:550])
 return {"crossplay_mentions":len(cross),"pair_contexts":windows[:3],"assessment":"strong_review_candidate" if windows else "insufficient_pair_context"}
def main():
 state=json.loads(INPUT.read_text())["games"]
 old=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {"games":{}}
 results=old.setdefault("games",{})
 today=dt.date.today().isoformat()
 stats={"games_total":len(state),"games_reviewed":0,"sources_total":0,"community_excluded":0,"official_candidates":0,"official_pages_ok":0,"official_pages_failed":0,"strong_review_candidates":0,"automatic_verified":0}
 for index,(name,entry) in enumerate(state.items()):
  candidates=entry.get("source_candidates",[])
  saved=results.setdefault(name,{"sources":{},"last_reviewed":today})
  for candidate in candidates:
   url=candidate["url"];classification=category(url)
   stats["sources_total"]+=1
   if classification=="community":stats["community_excluded"]+=1
   if classification!="official_candidate":continue
   stats["official_candidates"]+=1
   previous=saved["sources"].get(url,{})
   if previous.get("fetch")=="ok" and previous.get("checked_at")==today:
    record=previous
   else:
    fetch,body=retrieve(url)
    record={"url":url,"classification":classification,"fetch":fetch,"checked_at":today,"title":candidate.get("title","")}
    if fetch=="ok":record.update(evaluate(name,body))
    saved["sources"][url]=record
    time.sleep(.1)
   if record["fetch"]=="ok":
    stats["official_pages_ok"]+=1
    if record.get("assessment")=="strong_review_candidate":stats["strong_review_candidates"]+=1
   else:stats["official_pages_failed"]+=1
  stats["games_reviewed"]+=1
  if (index+1)%25==0 or index+1==len(state):
   OUTPUT.write_text(json.dumps(old,ensure_ascii=False,indent=2)+"\n")
   REPORT.write_text(json.dumps({"checked_at":today,"counts":stats,"remaining":len(state)-index-1},ensure_ascii=False,indent=2)+"\n")
   print("Content review",index+1,"/",len(state),stats,flush=True)
if __name__=="__main__":main()
