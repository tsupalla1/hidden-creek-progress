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
  await page.pdf({
    path: out, format: 'Letter', printBackground: true,
    margin: { top: '0.6in', bottom: '0.6in', left: '0.6in', right: '0.6in' },
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;color:#777;width:100%;text-align:center">Hidden Creek Reserve construction update · page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
  });
  await browser.close();
  console.log('wrote ' + out);
})().catch(e => { console.error(e); process.exit(1); });
