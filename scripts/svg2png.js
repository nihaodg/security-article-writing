// svg2png.js — 用 Playwright Chromium 把 SVG 批量转成 2x PNG，并检查文字越界。
//
// 用法:
//   node svg2png.js <文件或目录> [更多文件或目录...]
//   CHROME_PATH=/path/to/chrome node svg2png.js articles/x.assets
//
// 依赖: npm i playwright && npx playwright install chromium
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  const p = process.env.PLAYWRIGHT_MODULE;
  if (!p) throw new Error('找不到 playwright：先 npm i playwright，或设置 PLAYWRIGHT_MODULE=/path/to/playwright');
  ({ chromium } = require(p));
}
const path = require('path');
const fs = require('fs');

function collect(targets) {
  const files = [];
  for (const t of targets) {
    const p = path.resolve(t);
    if (!fs.existsSync(p)) { console.log('[skip] 不存在: ' + t); continue; }
    if (fs.statSync(p).isDirectory()) {
      for (const f of fs.readdirSync(p)) {
        if (f.toLowerCase().endsWith('.svg')) files.push(path.join(p, f));
      }
    } else if (p.toLowerCase().endsWith('.svg')) {
      files.push(p);
    }
  }
  return [...new Set(files)];
}

(async () => {
  const targets = process.argv.slice(2);
  if (!targets.length) {
    console.log('用法: node svg2png.js <文件或目录> [...]');
    process.exit(2);
  }
  const files = collect(targets);
  if (!files.length) { console.log('没有找到 SVG'); process.exit(2); }

  const launchOpts = { headless: true };
  if (process.env.CHROME_PATH) launchOpts.executablePath = process.env.CHROME_PATH;

  const browser = await chromium.launch(launchOpts);
  const ctx = await browser.newContext({ deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  let bad = 0;

  for (const svgPath of files) {
    const pngPath = svgPath.replace(/\.svg$/i, '.png');
    const svg = fs.readFileSync(svgPath, 'utf8');
    const mw = svg.match(/width="(\d+)"/);
    const mh = svg.match(/height="(\d+)"/);
    if (!mw || !mh) { console.log('[FAIL] 缺少 width/height: ' + svgPath); bad++; continue; }
    const w = parseInt(mw[1], 10), h = parseInt(mh[1], 10);

    await page.setViewportSize({ width: w, height: h });
    await page.setContent(
      `<html><body style="margin:0;padding:0;background:#fff">${svg}</body></html>`,
      { waitUntil: 'networkidle' });

    const out = await page.evaluate(([W, H]) => {
      const o = [];
      document.querySelectorAll('text').forEach(t => {
        const r = t.getBoundingClientRect();
        if (r.x < -1 || r.y < -1 || r.x + r.width > W + 1 || r.y + r.height > H + 1) {
          o.push(t.textContent.slice(0, 24) + ' -> ' +
            [r.x, r.y, r.x + r.width, r.y + r.height].map(v => v.toFixed(0)).join(','));
        }
      });
      return o;
    }, [w, h]);

    if (out.length) {
      console.log('[越界] ' + path.basename(svgPath));
      out.forEach(x => console.log('   ' + x));
      bad++;
    } else {
      console.log('[ok] ' + path.basename(svgPath) + ' ' + w + 'x' + h);
    }
    await page.screenshot({ path: pngPath, fullPage: false });
  }

  await browser.close();
  if (bad) { console.log('\n有 ' + bad + ' 张图需要修'); process.exit(1); }
})().catch(e => { console.error(e.message || e); process.exit(1); });
