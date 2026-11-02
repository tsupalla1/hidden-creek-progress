"""Rebuild index.html from template.html, carrying over data, fonts, site plan and photos from an existing page."""
import re, sys, json
src, tpl, out, icon = sys.argv[1:5]
h = open(src).read()
t = open(tpl).read()
data = re.search(r'<script type="application/json" id="hc-data">(.*?)</script>', h, re.S).group(1)
photos = re.search(r'<script type="application/json" id="hc-photos">(.*?)</script>', h, re.S).group(1)
plat = re.search(r'window\.HC_PLAT = "(.*?)"', h, re.S).group(1)
fonts = "\n".join(re.findall(r"@font-face \{[^}]*\}", h))
upd = re.search(r'<time id="hc-updated" datetime="([^"]*)"', h).group(1)
ic = open(icon).read().strip()
for k, v in [("{{HC_DATA}}", data), ("{{FONTS}}", fonts), ("{{UPDATED}}", upd), ("{{ICON}}", ic), ("{{PLAT}}", plat), ("{{PHOTOS}}", photos)]:
    assert k in t, k
    t = t.replace(k, v)
open(out, "w").write(t)
print(len(t))
