# Hidden Creek Reserve progress

Construction progress page for Hidden Creek Reserve, townhomes in Shawnee, Kansas. It updates every weekday at noon and 5 PM Central from the field notes.

- `index.html` is the page, served by GitHub Pages. Its data sits in the `hc-data` block (buildings, latest, milestones, upcoming, schedule, recap).
- `photos/` holds jobsite photos, one folder per building. See `photos/README.md`.
- `videos/` holds drone clips for the "From the air" section, hidden until a clip is there. See `videos/README.md`.
- `python3 tools/photos.py index.html` embeds the photos into the page, then runs `tools/videos.py`, which shrinks new clips with ffmpeg and lists them in the page's `hc-videos` block.
- `node tools/recap_pdf.js index.html recap.pdf` prints the PDF version linked from the weekly recap.
- `tools/page/template.html` is the page layout (phone first). To change the layout, edit it and run `python3 tools/page/build.py index.html tools/page/template.html index.html tools/page/icon.txt`, then `tools/photos.py` again. The build carries over the current data, site plan and photos.
- `tools/web_build.py` builds the website copy in `_site/`: the same page with every photo as its own small file (loaded only as people scroll) instead of packed inside the page. The "Publish website" GitHub Action runs it on every push to `main`, so the weekday refresh needs no change. It takes the layout from `tools/page/template.html`, so a layout change goes live on the site with the next push. This only takes effect once Settings > Pages > Source is set to **GitHub Actions**; until then the site serves `index.html` from `main` as before.
- `index.html` keeps the photos packed inside (newest 48) because the claude.ai copy of the page needs to be self-contained.
- `og.jpg` is the preview image shown when the link is texted or posted.
