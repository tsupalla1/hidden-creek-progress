// Print the progress page to a PDF for investors.
// Usage: node tools/recap_pdf.js index.html recap.pdf
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [page_, out] = process.argv.slice(2);
  if (!page_ || !out) { console.error('usage: node tools/recap_pdf.js index.html recap.pdf'); process.exit(1); }
  const browser = await chromium.launch();
  const page = await browser.newPage();
  // serve d3 from the copy in tools/vendor, since sandboxes may not reach the CDN
  await page.route('**/d3.min.js', r => r.fulfill({ path: path.join(__dirname, 'vendor', 'd3-7.8.5.min.js'), contentType: 'text/javascript' }));
  await page.emulateMedia({ media: 'print', colorScheme: 'light' });
  await page.goto('file://' + path.resolve(page_), { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.querySelector('#bldg-cards .hc-bldg'), null, { timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  // print small JPEG copies of the photos; Chromium would otherwise embed them uncompressed and the PDF balloons
  await page.evaluate(async () => {
    for (const img of document.querySelectorAll('#photos img')) {
      img.loading = 'eager';
      await img.decode().catch(() => {});
      if (!img.naturalWidth) continue;
      const s = Math.min(1, 700 / img.naturalWidth), c = document.createElement('canvas');
      c.width = Math.round(img.naturalWidth * s); c.height = Math.round(img.naturalHeight * s);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      img.src = c.toDataURL('image/jpeg', 0.72);
      await img.decode().catch(() => {});
    }
  });
  // same for the site plan image inside the SVG
  await page.evaluate(async () => {
    const im = document.getElementById('hc-plat'); if (!im || !im.getAttribute('href')) return;
    const img = new Image(); img.src = im.getAttribute('href'); await img.decode().catch(() => {});
    if (!img.naturalWidth) return;
    const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
    const ctx = c.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height); ctx.drawImage(img, 0, 0);
    im.setAttribute('href', c.toDataURL('image/jpeg', 0.7));
    await new Promise(r => setTimeout(r, 200));
  });
  // print the whole site plan, not the phone close-up
  await page.evaluate(() => { const b = document.getElementById('v-all'); if (b) b.click(); });
  await page.waitForTimeout(600);
  await page.pdf({
    path: out, format: 'Letter', printBackground: true,
    margin: { top: '0.6in', bottom: '0.6in', left: '0.6in', right: '0.6in' },
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;color:#777;width:100%;text-align:center">Hidden Creek Reserve construction update · page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
  });
  await browser.close();
  console.log('wrote ' + out);
})().catch(e => { console.error(e); process.exit(1); });
