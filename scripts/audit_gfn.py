#!/usr/bin/env python3
"""Compare every catalog entry to the publicly listed GFNDB game catalogue.
A missing match is NOT proof of non-support. No fuzzy title matching."""
import json, re, time, pathlib, urllib.request, urllib.parse, html
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Rows(HTMLParser):
    def __init__(self):
        super().__init__();self.inrow=False;self.incell=False;self.cells=[];self.rows=[];self.buffer=[]
    def handle_starttag(self,t,a):
        if t=="tr":self.inrow=True;self.cells=[]
        if self.inrow and t in ("td","th"):self.incell=True;self.buffer=[]
    def handle_data(self,s):
        if self.incell:self.buffer.append(s)
    def handle_endtag(self,t):
        if t in ("td","th") and self.incell:self.cells.append(" ".join("".join(self.buffer).split()));self.incell=False
        if t=="tr" and self.inrow:
            if self.cells:self.rows.append(self.cells)
            self.inrow=False
def norm(s):return re.sub(r"[^a-z0-9]","",html.unescape(s).lower().replace("’","'"))
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; CrossplayRadarAudit/1.0)"})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode("utf-8","replace")
# GFNDB lists both Ready to Play and Install to Play; collapse them to one status.
catalog={}
for page in range(1,150):
    url="https://gfndb.info/games/?page="+str(page)
    parser=Rows();parser.feed(fetch(url))
    found=0
    for cells in parser.rows:
        if len(cells)<2 or cells[1] not in ("Ready to Play","Install to Play"):continue
        title=cells[0];catalog.setdefault(norm(title),[]).append(title);found+=1
    print(f"Page {page}: {found} games")
    if not found:break
    time.sleep(0.25)
if len(catalog)<3000:raise RuntimeError(f"Only {len(catalog)} GFN titles loaded; aborting to avoid incomplete verification")
path=ROOT/"data/games.json";db=json.loads(path.read_text());yes=0;uncertain=[]
for g in db["games"]:
    hits=catalog.get(norm(g["name"]),[])
    if len(hits)==1:
        g["gfn"]="yes";g["gfnSource"]="https://gfndb.info/games/";g["gfnAudit"]="exact_title_match_in_independent_gfn_catalog";yes+=1
    elif g.get("gfn")!="yes":
        g["gfn"]="unknown";g["gfnAudit"]="no_unique_match_not_proof_of_absence";uncertain.append(g["name"])
path.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n")
page=ROOT/"index.html";content=page.read_text()
prefix="const EMBEDDED_CATALOG=";start=content.index(prefix)+len(prefix);end=content.index(";\nlet all=",start)
content=content[:start]+json.dumps(db,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+content[end:]
page.write_text(content)
(ROOT/"data/gfn-audit.txt").write_text(f"Matched {yes} / {len(db['games'])} titles against {len(catalog)} unique GFN names.\nMissing is not proof of non-support.\n"+"\n".join(uncertain)+"\n")
print(f"Matched {yes}/{len(db['games'])}; unmatched {len(uncertain)}")
