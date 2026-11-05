#!/usr/bin/env python3
"""Put drone videos from videos/ on the progress page.

Usage: python3 tools/videos.py index.html   (tools/photos.py also runs it)

Drop a clip (MP4 or MOV) in videos/. Each clip is turned into a phone-friendly
MP4 (at most 1920 px wide, H.264, no sound, starts playing before it has fully
downloaded) plus a poster frame (<name>.jpg), both kept in videos/. The original
is replaced, so the repo holds only the small copy. A clip already converted
(tagged "hc-web") is left alone.

Longer flyovers can live on YouTube instead: add a line to videos/youtube.txt,
  2026-11-05 Full site flyover | https://youtu.be/XXXXXXXXXXX

The date comes from a YYYY-MM-DD at the start of the file name, then the
camera's recording date, then the day the file was committed. Words after the
date become the caption. The list is written into the page's
<script id="hc-videos"> block; with no videos the section stays hidden.
"""
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from photos import caption_for, commit_date  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VIDEOS = ROOT / "videos"
EXTS = {".mp4", ".mov", ".m4v"}
TAG = "hc-web"
MAX_MB = 40              # a bigger result is redone at 1280 px
DRONE_NAME = re.compile(r"^(dji|dji_fly|hover|mavic|pxl|vid|mvi|gopr|gx)?[\s_-]*[\d_]*$", re.I)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def is_web(info):
    return info.get("format", {}).get("tags", {}).get("comment") == TAG


def recorded(info):
    for tags in [info.get("format", {}).get("tags", {})] + [s.get("tags", {}) for s in info.get("streams", [])]:
        t = tags.get("creation_time")
        if t and not t.startswith("1970"):
            return t[:10]
    return None


def encode(src, dst, width, crf):
    vf = f"scale='min({width},iw)':-2,format=yuv420p"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-an", "-vf", vf,
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-profile:v", "high",
                    "-movflags", "+faststart", "-map_metadata", "0", "-metadata", f"comment={TAG}", str(dst)],
                   check=True)


def convert(path):
    """Replace a raw clip with its web copy; return the web copy's path."""
    final = path.with_suffix(".mp4")
    tmp = path.with_name(path.stem + ".web-tmp.mp4")
    encode(path, tmp, 1920, 26)
    if tmp.stat().st_size > MAX_MB * 1e6:
        encode(path, tmp, 1280, 28)
    if path != final and final.exists():
        sys.exit(f"{final.relative_to(ROOT)} already exists; rename {path.name}")
    path.unlink()
    tmp.replace(final)
    print(f"converted {path.name} -> {final.name} ({final.stat().st_size / 1e6:.1f} MB)")
    return final


def poster(path):
    jpg = path.with_suffix(".jpg")
    if not jpg.exists() or jpg.stat().st_mtime < path.stat().st_mtime:
        dur = float(probe(path).get("format", {}).get("duration") or 0)
        at = min(1.0, dur / 2) if dur else 0
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(at), "-i", str(path), "-frames:v", "1",
                        "-vf", "scale='min(1280,iw)':-2", "-q:v", "4", str(jpg)], check=True)
    return jpg


def caption(stem):
    text = caption_for(stem)
    return "" if DRONE_NAME.match(re.sub(r"^\d{4}-\d{2}-\d{2}", "", stem).strip()) else text


def clips():
    found = []
    if not VIDEOS.exists():
        return found
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found; videos left as they are", file=sys.stderr)
    for path in sorted(VIDEOS.iterdir()):
        if path.suffix.lower() not in EXTS or not path.is_file() or ".web-tmp" in path.name:
            continue
        try:
            info = probe(path) if shutil.which("ffprobe") else {}
            date = (re.match(r"\d{4}-\d{2}-\d{2}", path.stem) or [None])[0] or recorded(info) or commit_date(path)
            if shutil.which("ffmpeg"):
                if not is_web(info):
                    path = convert(path)
                jpg = poster(path)
            else:
                jpg = path.with_suffix(".jpg")
            entry = {"src": str(path.relative_to(ROOT)), "date": date or dt.date.today().isoformat(),
                     "caption": caption(path.stem)}
            if jpg.exists():
                entry["poster"] = str(jpg.relative_to(ROOT))
            found.append(entry)
        except Exception as e:
            print(f"skipped {path.name}: {e}", file=sys.stderr)
    links = VIDEOS / "youtube.txt"
    if links.exists():
        for line in links.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "http" not in line:
                continue
            text, _, url = line.rpartition("|") if "|" in line else ("", "", line)
            text = text.strip()
            m = re.match(r"(\d{4}-\d{2}-\d{2})\s*(.*)", text)
            found.append({"youtube": url.strip(), "date": m.group(1) if m else None,
                          "caption": (m.group(2) if m else text).strip()})
    return found


def main(page):
    found = clips()
    html = Path(page).read_text()
    block = re.compile(r'(<script type="application/json" id="hc-videos">)(.*?)(</script>)', re.S)
    if not block.search(html):
        print("no hc-videos block in page; rebuild it from tools/page/template.html", file=sys.stderr)
        return
    data = json.dumps(found, ensure_ascii=False).replace("</", "<\\/")
    Path(page).write_text(block.sub(lambda m: m.group(1) + data + m.group(3), html, count=1))
    print(f"{len(found)} videos listed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
