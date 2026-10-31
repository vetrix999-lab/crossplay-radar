#!/usr/bin/env python3
"""Offline integrity tests for the full Crossplay Radar catalog."""
import json,re,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class CatalogTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.db=json.loads((ROOT/"data/games.json").read_text())
  cls.games=cls.db["games"]
  cls.page=(ROOT/"index.html").read_text()
 def test_nonempty_unique_titles(self):
  self.assertGreaterEqual(len(self.games),200)
  titles=[re.sub(r"[^a-z0-9]","",g["name"].lower()) for g in self.games]
  self.assertEqual(len(titles),len(set(titles)))
 def test_verified_only_when_supported(self):
  for g in self.games:
   with self.subTest(game=g["name"]):
    self.assertTrue(g["name"].strip())
    self.assertIn(g.get("genre"),("Shooter","Action","Adventure","Survival","RPG","Strategy","Racing","Sports","Fighting","Party","Puzzle","Platformer","Simulation","MMO","Other","Sandbox","Horror","Co-op","MOBA","Battle Royale","Casual","Rhythm","Card","MMORPG","Open World","Unknown"))
    self.assertIsInstance(g.get("verified"),bool)
    if g.get("verified"):
     self.assertTrue(g.get("source"))
     self.assertNotIn(g.get("status"),("review","unsupported","upcoming","rejected","pending"))
    if g.get("crossplayAudit") in ("ps5_pc_not_supported","developer_confirms_not_available"):
     self.assertFalse(g.get("verified"))
 def test_embedded_catalog_identical(self):
  m=re.search(r"const EMBEDDED_CATALOG=([\s\S]*?);\nlet all=",self.page)
  self.assertIsNotNone(m)
  embedded=json.loads(m.group(1))
  self.assertEqual(embedded,self.db)
 def test_images_are_https_or_missing(self):
  for g in self.games:
   self.assertTrue(not g.get("image") or g["image"].startswith("https://"),g["name"])
if __name__=="__main__":unittest.main()
