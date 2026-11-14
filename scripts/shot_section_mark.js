/**
 * shot_section_mark.js — 按段落截区域 + 定位要框住的句子 + 输出红框坐标
 *
 * 用法:
 *   node shot_section_mark.js <url> <out.png> <起始文字> [段数] [x] [宽] [要框住的句子]
 *
 * 例:
 *   node shot_section_mark.js "https://example.com/post" \
 *     articles/x.assets/fig-7-page.png "漏洞描述" 4 0 1265 "CVE-2025-53773"
 *
 * 行为:
 *   1. 找到包含 <起始文字> 的第一个 <p>，向下取 N 个段落；
 *   2. 先滚到该区域，再按 clip 截图（deviceScaleFactor=2）；
 *   3. 若给 <要框住的句子>，找到包含它的段落，写出 <out.png>.box.json：
 *      {"x":..., "y":..., "w":..., "h":...}，坐标已乘 2；
 *   4. 用 png_mark.py 读取 box.json 画红框 + 来源条。
 *
 * 环境变量:
 *   CHROME_PATH       指定 Chromium（默认 Playwright 自带）
 *   PLAYWRIGHT_MODULE playwright 模块路径
 */
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  const p = process.env.PLAYWRIGHT_MODULE;
  if (!p) throw new Error('找不到 playwright：先 npm i playwright，或设置 PLAYWRIGHT_MODULE=/path/to/playwright');
  ({ chromium } = require(p));
}
const fs = require('fs');
const path = require('path');

const [, , url, out, kw, nStr, xStr, wStr, mark] = process.argv;
if (!url || !out || !kw) {
  console.error('用法: node shot_section_mark.js <url> <out.png> <起始文字> [段数] [x] [宽] [要框住的句子]');
  process.exit(2);
}
const N = Number(nStr || 4);
const X = Number(xStr || 0);
const W = Number(wStr || 1265);

(async () => {
  const launchOpts = { headless: true };
  if (process.env.CHROME_PATH) launchOpts.executablePath = process.env.CHROME_PATH;

  const browser = await chromium.launch(launchOpts);
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  await page.goto(url, { timeout: 45000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const info = await page.evaluate(([kw, N, mark]) => {
    const ps = [...document.querySelectorAll('p')];
    const i = ps.findIndex((p) => (p.innerText || '').includes(kw));
    if (i < 0) return null;
    const sel = ps.slice(i, i + N);
    const rects = sel.map((e) => e.getBoundingClientRect());
    const top = Math.min(...rects.map((r) => r.top + window.scrollY));
    const bot = Math.max(...rects.map((r) => r.bottom + window.scrollY));
    let mk = null;
    if (mark) {
      const hit = sel.find((e) => (e.innerText || '').includes(mark));
      if (hit) {
        const r = hit.getBoundingClientRect();
        mk = {
          x: r.left + window.scrollX, y: r.top + window.scrollY,
          w: r.width, h: r.height,
        };
      }
    }
    return { top, bot, mk };
  }, [kw, N, mark]);

  if (!info) {
    console.log('  [fail] 没找到段落: ' + kw);
    await browser.close();
    return;
  }

  const y = Math.max(0, info.top - 30);
  const h = Math.min(1400, info.bot - info.top + 60);
  await page.evaluate((ty) => window.scrollTo(0, Math.max(0, ty - 60)), y);
  await page.waitForTimeout(800);
  const sy = await page.evaluate(() => window.scrollY);

  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  await page.screenshot({ path: out, clip: { x: X, y: y - sy, width: W, height: h } });

  if (info.mk) {
    const box = {
      x: Math.round((info.mk.x - X) * 2),
      y: Math.round((info.mk.y - y) * 2),
      w: Math.round(info.mk.w * 2),
      h: Math.round(info.mk.h * 2),
    };
    fs.writeFileSync(out + '.box.json', JSON.stringify(box));
    console.log('  [ok] 红框位置 ' + JSON.stringify(box));
  } else {
    console.log('  [warn] 没找到要框的句子');
  }
  console.log('  [ok] -> ' + out);
  await browser.close();
})().catch((e) => { console.error('  [error] ' + (e.message || e)); process.exit(1); });
