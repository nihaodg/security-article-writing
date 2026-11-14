// mac_term_shot.js — 用 Playwright Chromium 截 HTML → PNG
// 用法: node mac_term_shot.js <html> <png> <width> <height>
// 可选: CHROME_PATH=/path/to/chrome node mac_term_shot.js ...
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  const p = process.env.PLAYWRIGHT_MODULE;
  if (!p) throw new Error('找不到 playwright：先 npm i playwright，或设置 PLAYWRIGHT_MODULE=/path/to/playwright');
  ({ chromium } = require(p));
}
const path = require('path');

(async () => {
  const [htmlPath, pngPath, w, h] = process.argv.slice(2);
  if (!htmlPath || !pngPath) {
    console.error('用法: node mac_term_shot.js <html> <png> <width> <height>');
    process.exit(2);
  }
  const launchOpts = { headless: true };
  if (process.env.CHROME_PATH) launchOpts.executablePath = process.env.CHROME_PATH;

  const browser = await chromium.launch(launchOpts);
  const page = await browser.newPage({
    viewport: { width: parseInt(w) + 80, height: parseInt(h) + 80 },
    deviceScaleFactor: 2
  });
  await page.goto('file:///' + path.resolve(htmlPath).replace(/\\/g, '/'));
  await page.waitForTimeout(400);
  const el = await page.$('.wrap');
  if (!el) throw new Error('找不到 .wrap 元素');
  await el.screenshot({ path: pngPath });
  await browser.close();
  console.log('SAVED:', pngPath);
})().catch(e => { console.error(e.message || e); process.exit(1); });
