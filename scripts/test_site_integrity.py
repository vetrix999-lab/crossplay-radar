#!/usr/bin/env python3
"""Static integrity smoke test for the published, self-contained website."""
import json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[1]
data=json.loads((root/"data/games.json").read_text())
html=(root/"index.html").read_text()
match=re.search(r"const EMBEDDED_CATALOG=([\s\S]*?);\nlet all=",html)
assert match,"Embedded catalog missing"
embedded=json.loads(match.group(1))
games=data["games"]
assert embedded["games"]==games,"Published website differs from games.json"
assert len({g["id"] for g in games})==len(games)
assert len({re.sub(r"[^a-z0-9]","",g["name"].lower()) for g in games})==len(games),"Duplicate normalized titles"
assert all(g.get("gfn","unknown") in ("yes","no","unknown") for g in games)
assert 'onerror="this.hidden=true;this.nextElementSibling.hidden=false"' in html,"Broken cover fallback missing"
assert "g.gfn===gfn" in html,"GFN filter missing"
assert "g.genre===genre" in html,"Genre filter missing"
assert "g.verified" in html,"Verified status missing"
assert "loading=\\"lazy\\"" in html,"Lazy image loading missing"
print(json.dumps({"games":len(games),"verified":sum(g.get("verified") for g in games),"with_image_url":sum(bool(g.get("image")) for g in games),"missing_image_url":sum(not g.get("image") for g in games),"gfn_yes":sum(g.get("gfn")=="yes" for g in games),"static_checks":"passed"}))
