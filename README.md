# Hidden Creek Reserve progress

Construction progress page for Hidden Creek Reserve, townhomes in Shawnee, Kansas. It updates each weekday evening from the field notes.

- `index.html` is the page, served by GitHub Pages. Its data sits in the `hc-data` block (buildings, latest, milestones, upcoming, schedule, recap).
- `photos/` holds jobsite photos, one folder per building. See `photos/README.md`.
- `videos/` holds drone clips for the "From the air" section, hidden until a clip is there. See `videos/README.md`.
- `python3 tools/photos.py index.html` embeds the photos into the page, then runs `tools/videos.py`, which shrinks new clips with ffmpeg and lists them in the page's `hc-videos` block.
- `node tools/recap_pdf.js index.html recap.pdf` prints the PDF version linked from the weekly recap.
- `tools/page/template.html` is the page layout (phone first). To change the layout, edit it and run `python3 tools/page/build.py index.html tools/page/template.html index.html tools/page/icon.txt`, then `tools/photos.py` again. The build carries over the current data, site plan and photos.
- `og.jpg` is the preview image shown when the link is texted or posted.
