#!/usr/bin/env python3
"""Embed jobsite photos from photos/ into the progress page.

Usage: python3 tools/photos.py index.html

Photos live in one folder per building, e.g. photos/lots-11-14/ or
photos/Lots 11-14/. Anything else (photos/site/ or loose files) is filed
under "Site". The date comes from a YYYY-MM-DD at the start of the file
name, then the camera's EXIF date, then the day the file was committed.
Words after the date become the caption ("2026-11-03 framing starts.jpg").

Each photo is shrunk to a web-sized WebP and written into the page's
<script id="hc-photos"> block, so the page needs no outside image host.
It also stamps the current time into the page's "Last updated" line.

Each building also gets a photo timeline (shown in its sheet on the page):
one photo per date, newest first on the page, up to TIMELINE_MAX frames spread evenly
from the first day to the latest. Those frames are marked "tl": 1. A frame
that has aged out of the newest MAX_PHOTOS is kept as a small thumbnail
marked "old": 1, so the timeline still starts at bare dirt; the gallery
skips old frames.
"""
import base64
import datetime as dt
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "photos"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_EDGE = 1100         # sized for phones; keeps 48 photos well under the 16 MB page limit
QUALITY = 58
MAX_PHOTOS = 48          # newest photos kept on the page
TIMELINE_MAX = 12        # frames per building on its timeline
OLD_EDGE = 560           # older timeline frames are kept small
OLD_QUALITY = 50
CAMERA_NAME = re.compile(r"^(img|dsc|dscn|pxl|photo|image|mvimg|screenshot)?[\s_-]*\d*$", re.I)


def heic_support():
    """iPhones upload HEIC; Pillow reads it through pillow-heif, installed on first need."""
    try:
        import pillow_heif
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pillow-heif"], capture_output=True)
        try:
            import pillow_heif
        except ImportError:
            return False
    pillow_heif.register_heif_opener()
    return True


def building_for(path):
    rel = path.relative_to(PHOTOS)
    if len(rel.parts) > 1:
        m = re.search(r"(\d+)\s*[-_ ]\s*(\d+)", rel.parts[0])
        if m:
            return f"Lots {int(m.group(1))}-{int(m.group(2))}"
    return "Site"


def exif_date(img):
    try:
        exif = img.getexif()
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)
        if raw:
            return dt.datetime.strptime(str(raw)[:10], "%Y:%m:%d").date().isoformat()
    except Exception:
        pass
    return None


def commit_date(path):
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%cs", "-1", "--", str(path)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except Exception:
        return None


def caption_for(stem):
    text = re.sub(r"^\d{4}-\d{2}-\d{2}", "", stem)
    text = re.sub(r"[_-]+", " ", text).strip()
    text = re.sub(r"\s*\(\d+\)$", "", text)
    if not text or CAMERA_NAME.match(text):
        return ""
    return text[0].upper() + text[1:]


def load(path, edge=MAX_EDGE, quality=QUALITY):
    img = Image.open(path)
    date = None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if m:
        date = m.group(1)
    date = date or exif_date(img) or commit_date(path) or dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((edge, edge), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=quality, method=6)
    return {
        "building": building_for(path),
        "date": date,
        "caption": caption_for(path.stem),
        "src": "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode(),
        "w": img.width,
        "h": img.height,
        "file": str(path.relative_to(ROOT)),
    }


def spread(items, n):
    """n items spread evenly from first to last, always keeping both ends."""
    if len(items) <= n:
        return items
    idx = sorted({round(i * (len(items) - 1) / (n - 1)) for i in range(n)})
    return [items[i] for i in idx]


def timeline(photos, keep):
    """Mark each building's timeline frames; return small copies of frames older than the newest photos."""
    kept = {p["file"] for p in keep}
    extra = []
    for b in sorted({p["building"] for p in photos}):
        if b == "Site":
            continue
        days = {}
        for p in sorted((p for p in photos if p["building"] == b), key=lambda p: (p["date"], p["file"])):
            # one frame per day: a captioned photo first, then one already on the page, else the day's first
            cur = days.get(p["date"])
            if cur is None or (bool(p["caption"]), p["file"] in kept) > (bool(cur["caption"]), cur["file"] in kept):
                days[p["date"]] = p
        for p in spread([days[d] for d in sorted(days)], TIMELINE_MAX):
            p["tl"] = 1
            if p["file"] not in kept:
                try:
                    small = load(ROOT / p["file"], OLD_EDGE, OLD_QUALITY)
                except Exception as e:
                    print(f"skipped timeline {p['file']}: {e}", file=sys.stderr)
                    continue
                small.update(date=p["date"], tl=1, old=1)
                extra.append(small)
    return extra


def main(page):
    photos = []
    if PHOTOS.exists() and any(p.suffix.lower() in {".heic", ".heif"} for p in PHOTOS.rglob("*")):
        if not heic_support():
            print("pillow-heif unavailable; HEIC photos will be skipped", file=sys.stderr)
    for path in sorted(PHOTOS.rglob("*")) if PHOTOS.exists() else []:
        if path.suffix.lower() not in EXTS or not path.is_file():
            continue
        try:
            photos.append(load(path))
        except Exception as e:
            print(f"skipped {path.relative_to(ROOT)}: {e}", file=sys.stderr)
    photos.sort(key=lambda p: (p["date"], p["file"]), reverse=True)
    keep = photos[:MAX_PHOTOS]
    keep += timeline(photos, keep)
    html = Path(page).read_text()
    block = re.compile(r'(<script type="application/json" id="hc-photos">)(.*?)(</script>)', re.S)
    if not block.search(html):
        sys.exit("no hc-photos block in " + page)
    data = json.dumps(keep, ensure_ascii=False).replace("</", "<\\/")
    html = block.sub(lambda m: m.group(1) + data + m.group(3), html, count=1)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    html = re.sub(r'(<time id="hc-updated" datetime=")[^"]*(")', lambda m: m.group(1) + now + m.group(2), html, count=1)
    # GitHub Pages serves index.html as is: make sure it starts in standards mode with a charset
    if not html.lstrip().lower().startswith("<!doctype"):
        html = '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n' + html.lstrip()
    Path(page).write_text(html)
    size = sum(len(p["src"]) for p in keep) / 1e6
    old = sum(1 for p in keep if p.get("old"))
    print(f"{len(keep) - old} photos embedded, plus {old} older timeline frames ({size:.1f} MB); "
          f"{len(photos) - len(keep) + old} older left out of the gallery")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
