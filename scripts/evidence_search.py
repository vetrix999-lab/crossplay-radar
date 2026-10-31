#!/usr/bin/env python3
"""Brave Search API evidence discovery. Never promotes a game automatically."""
import datetime as dt,json,os,pathlib,re,time,urllib.parse,urllib.request,urllib.error
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
DB=ROOT/"data/games.json";STATE=ROOT/"data/evidence-search-state.json";REPORT=ROOT/"data/evidence-search-report.json"
API="https://api.search.brave.com/res/v1/web/search"
DOMAINS=("ea.com","epicgames.com","playstation.com","2k.com","ubisoft.com","blizzard.com","seaofthieves.com","warthunder.com","hazelight.se","minecraft.net","warframe.com","bungie.net","capcom.com","bethesda.net","square-enix-games.com","enlisted.net","rockstargames.com","steamcommunity.com","steampowered.com","xbox.com","microsoft.com","bandainamcoent.com","team17.com","support.activision.com","callofduty.com","deadbydaylight.com","riotgames.com","neteasegames.com","gearboxsoftware.com","support.hoyoverse.com")
def official(url):
 try:
  host=(urllib.parse.urlsplit(url).hostname or "").lower()
  return any(host==d or host.endswith("."+d) for d in DOMAINS)
 except ValueError:return False
def fetch(url,headers):
 req=urllib.request.Request(url,headers=headers)
 with urllib.request.urlopen(req,timeout=16) as r:return r.status,r.headers.get("Content-Type","").lower(),r.read(450000)
def brave(query,key):
 url=API+"?"+urllib.parse.urlencode({"q":query,"count":10,"safesearch":"moderate"})
 _,_,data=fetch(url,{"X-Subscription-Token":key,"Accept":"application/json","User-Agent":"CrossplayRadar/1.0"})
 return json.loads(data).get("web",{}).get("results",[])
class Text(HTMLParser):
 def __init__(self):super().__init__();self.words=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style","nav","footer"):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ("script","style","nav","footer"):self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip:self.words.append(data)
def inspect(url,name):
 try:
  code,typ,raw=fetch(url,{"User-Agent":"CrossplayRadar/1.0"})
  if "html" not in typ:return {"fetch":"not_html","http":code}
  parser=Text();parser.feed(raw.decode("utf-8","replace"))
  body=" ".join(" ".join(parser.words).split()).lower()
  tokens=[x for x in re.findall(r"[a-z0-9]+",name.lower()) if len(x)>3]
  title_match=sum(x in body for x in tokens)>=max(1,len(tokens)//2)
  ps5=bool(re.search(r"\bps5\b|playstation\s*5",body))
  pc=bool(re.search(r"\bpc\b|windows|steam",body))
  cross=bool(re.search(r"cross[- ]play|cross[- ]platform (?:play|multiplayer)|play together across platforms",body))
  return {"fetch":"ok","http":code,"title_terms":title_match,"ps5_terms":ps5,"pc_terms":pc,"crossplay_terms":cross,"assessment":"manual_review_required" if title_match and ps5 and pc and cross else "insufficient_evidence"}
 except urllib.error.HTTPError as e:return {"fetch":"http_error","http":e.code}
 except Exception as e:return {"fetch":"error","error":str(e)[:120]}
def save(state,report):
 STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
def main():
 db=json.loads(DB.read_text());pending=[g for g in db["games"] if not g.get("verified") and g.get("status")!="unsupported"]
 state=json.loads(STATE.read_text()) if STATE.exists() else {"version":1,"games":{}}
 state.setdefault("games",{})
 key=os.getenv("BRAVE_SEARCH_API_KEY","").strip()
 if not key:raise SystemExit("MISSING BRAVE_SEARCH_API_KEY: configure GitHub Actions repository secret; no searches executed")
 today=dt.date.today();due=[]
 for g in pending:
  old=state["games"].get(g["name"],{});date=old.get("attempted_at")
  try:fresh=(today-dt.date.fromisoformat(date)).days<30
  except (TypeError,ValueError):fresh=False
  if not fresh:due.append(g)
 counts={"pending_total":len(pending),"due":len(due),"attempted":0,"search_requests":0,"official_candidates":0,"official_pages_fetched":0,"official_page_failures":0,"errors":0,"verified_promotions":0}
 for offset in range(0,len(due),25):
  batch=due[offset:offset+25];limited=False
  for g in batch:
   name=g["name"];q='"'+name.replace('"',"")+'"'
   queries=[q+" PS5 PC crossplay official developer publisher FAQ",q+" PlayStation 5 PC Steam cross-platform multiplayer official support",q+" PS5 PC crossplay patch notes online service status"]
   entry={"attempted_at":today.isoformat(),"status":"pending_review","searches":[],"source_candidates":[],"official_pages":[]}
   found={}
   for query in queries:
    try:
     results=brave(query,key);counts["search_requests"]+=1
     entry["searches"].append({"query":query,"results":len(results)})
     for item in results:
      url=item.get("url","")
      if official(url):found[url]={"url":url,"title":item.get("title",""),"description":item.get("description","")}
    except urllib.error.HTTPError as e:
     entry["searches"].append({"query":query,"error":"HTTP "+str(e.code)});counts["errors"]+=1
     if e.code in (401,403,429):limited=True;entry["attempted_at"]=None;break
    except Exception as e:entry["searches"].append({"query":query,"error":str(e)[:120]});counts["errors"]+=1
    time.sleep(0.2)
   entry["source_candidates"]=list(found.values());counts["official_candidates"]+=len(found)
   for url in list(found)[:8]:
    result=inspect(url,name);entry["official_pages"].append({"url":url,**result})
    counts["official_pages_fetched" if result.get("fetch")=="ok" else "official_page_failures"]+=1
    time.sleep(0.2)
   state["games"][name]=entry;counts["attempted"]+=1
   print("Evidence search",counts["attempted"],"/",len(due),name,flush=True)
   if limited:break
  save(state,{"run_date":today.isoformat(),"counts":counts,"total_saved":len(state["games"]),"remaining":len(due)-counts["attempted"]})
  if limited:print("API limit/authorization failure; progress saved",flush=True);break
 print(json.dumps(counts),flush=True)
if __name__=="__main__":main()
