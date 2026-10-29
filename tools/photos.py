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
MAX_EDGE = 1400
QUALITY = 68
MAX_PHOTOS = 48          # newest photos kept on the page
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


def load(path):
    img = Image.open(path)
    date = None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if m:
        date = m.group(1)
    date = date or exif_date(img) or commit_date(path) or dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=QUALITY, method=6)
    return {
        "building": building_for(path),
        "date": date,
        "caption": caption_for(path.stem),
        "src": "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode(),
        "w": img.width,
        "h": img.height,
        "file": str(path.relative_to(ROOT)),
    }


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
    # always keep each building's first photo so "then and now" has a start
    for b in {p["building"] for p in photos}:
        first = [p for p in photos if p["building"] == b][-1]
        if first not in keep:
            keep.append(first)
    html = Path(page).read_text()
    block = re.compile(r'(<script type="application/json" id="hc-photos">)(.*?)(</script>)', re.S)
    if not block.search(html):
        sys.exit("no hc-photos block in " + page)
    data = json.dumps(keep, ensure_ascii=False).replace("</", "<\\/")
    html = block.sub(lambda m: m.group(1) + data + m.group(3), html, count=1)
    Path(page).write_text(html)
    size = sum(len(p["src"]) for p in keep) / 1e6
    print(f"{len(keep)} photos embedded ({size:.1f} MB), {len(photos) - len(keep)} older left out")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
