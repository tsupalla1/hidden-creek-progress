#!/usr/bin/env python3
"""Build the website copy of the page, with photos served as separate files.

Usage: python3 tools/web_build.py index.html _site

index.html (the page the weekday refresh writes) carries every photo inside
it, which keeps the claude.ai copy self-contained but makes the page about
15 MB and caps it at the newest 48 photos. For GitHub Pages this script
writes a light copy instead:

- the layout comes from tools/page/template.html, and the data, fonts and
  last-updated time from index.html, so a layout change goes live with the
  next push even before the claude.ai copy has it;
- every photo in photos/ becomes two WebP files in p/: a small one for the
  tiles and a large one for the photo viewer. Phones only fetch the ones
  that scroll into view, and keep them cached between visits;
- the site plan becomes plat.webp;
- recap.pdf, og.jpg, CNAME and the converted drone clips are copied as is.

Converted photos are kept in .cache/photos (by file content), so a run only
converts new uploads. GitHub Actions runs this on every push to main
(.github/workflows/pages.yml).
"""
import base64
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import photos as ph  # noqa: E402  (same date, caption, building and timeline rules as the page)

ROOT = ph.ROOT
CACHE = ROOT / ".cache" / "photos"
SIZES = {"t": (720, 60), "f": (1600, 66)}   # tile/cover, photo viewer
VERSION = "1"                                  # bump to redo every conversion


def convert(path):
    """Write the tile and viewer WebP for one photo; return their names and size."""
    digest = hashlib.sha1(VERSION.encode() + path.read_bytes()).hexdigest()[:16]
    names = {k: f"{digest}-{k}.webp" for k in SIZES}
    meta = CACHE / f"{digest}.json"
    if meta.exists() and all((CACHE / n).exists() for n in names.values()):
        return json.loads(meta.read_text())
    img = Image.open(path)
    date = None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if m:
        date = m.group(1)
    date = date or ph.exif_date(img)
    img = ImageOps.exif_transpose(img).convert("RGB")
    out = {"names": names, "exif_date": date}
    for k, (edge, q) in SIZES.items():
        im = img.copy()
        im.thumbnail((edge, edge), Image.LANCZOS)
        im.save(CACHE / names[k], "WEBP", quality=q, method=6)
        if k == "f":
            out["w"], out["h"] = im.width, im.height
    meta.write_text(json.dumps(out))
    return out


def main(page, site):
    site = Path(site)
    if site.exists():
        shutil.rmtree(site)
    (site / "p").mkdir(parents=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    html = Path(page).read_text()

    # photos as files
    if any(p.suffix.lower() in {".heic", ".heif"} for p in ph.PHOTOS.rglob("*")):
        ph.heic_support()
    photos = []
    for path in sorted(ph.PHOTOS.rglob("*")):
        if path.suffix.lower() not in ph.EXTS or not path.is_file():
            continue
        try:
            c = convert(path)
        except Exception as e:
            print(f"skipped {path.relative_to(ROOT)}: {e}", file=sys.stderr)
            continue
        for n in c["names"].values():
            shutil.copy2(CACHE / n, site / "p" / n)
        date = c["exif_date"] or ph.commit_date(path) or "1970-01-01"
        photos.append({
            "building": ph.building_for(path), "date": date, "caption": ph.caption_for(path.stem),
            "src": "p/" + c["names"]["f"], "thumb": "p/" + c["names"]["t"], "w": c["w"], "h": c["h"],
            "file": str(path.relative_to(ROOT)), "t": ph.added_at(path),
        })
    photos.sort(key=lambda p: (p["date"], p.get("t", ""), p["file"]), reverse=True)
    ph.timeline(photos, photos)  # marks timeline frames; nothing ages out here, so no extra copies

    # page: current layout + current data
    tpl = (ROOT / "tools/page/template.html").read_text()
    grab = lambda rx: re.search(rx, html, re.S)
    data = grab(r'<script type="application/json" id="hc-data">(.*?)</script>').group(1)
    vm = grab(r'<script type="application/json" id="hc-videos">(.*?)</script>')
    plat = grab(r'window\.HC_PLAT = "(.*?)"').group(1)
    fonts = "\n".join(re.findall(r"@font-face \{[^}]*\}", html))
    upd = grab(r'<time id="hc-updated" datetime="([^"]*)"').group(1)
    if plat.startswith("data:image/"):
        ext = plat.split(";")[0].split("/")[1]
        (site / f"plat.{ext}").write_bytes(base64.b64decode(plat.split(",", 1)[1]))
        plat = f"plat.{ext}"
    for k, v in [("{{HC_DATA}}", data), ("{{FONTS}}", fonts), ("{{UPDATED}}", upd),
                 ("{{ICON}}", (ROOT / "tools/page/icon.txt").read_text().strip()), ("{{PLAT}}", plat),
                 ("{{PHOTOS}}", json.dumps(photos, ensure_ascii=False).replace("</", "<\\/")),
                 ("{{VIDEOS}}", vm.group(1) if vm else "[]")]:
        tpl = tpl.replace(k, v)
    if not tpl.lstrip().lower().startswith("<!doctype"):
        tpl = '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n' + tpl.lstrip()
    (site / "index.html").write_text(tpl)

    # everything else the page links to
    for name in ["recap.pdf", "og.jpg", "CNAME", ".nojekyll"]:
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, site / name)
    vids = ROOT / "videos"
    if vids.exists():
        (site / "videos").mkdir()
        for v in vids.iterdir():
            if v.suffix.lower() in {".mp4", ".jpg"}:
                shutil.copy2(v, site / "videos" / v.name)
    size = sum(f.stat().st_size for f in (site / "p").iterdir())
    print(f"{len(photos)} photos as files ({size / 1e6:.1f} MB in all); page {len(tpl) / 1e6:.2f} MB")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
