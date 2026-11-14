/**
 * web_shot.js — 抓真实网页截图（Playwright Chromium）
 *
 * 用法:
 *   node web_shot.js <url> <out.png> [selector] [waitText] [clip] [boxText]
 *
 *   selector  可选。CSS 选择器；或 "text:关键词"（找包含该文本的最小元素）；
 *             "text:关键词@N"（再往上数 N 层祖先）。不给则截整页。
 *   waitText 可选。等页面上出现该文本再截，避免截到加载中状态。
 *   clip     可选。"x,y,w,h" 只截这块区域（页面坐标，脚本会先滚动）。
 *   boxText  可选。输出该文本的设备像素坐标：BOX x,y,w,h，供 png_mark.py 画红框。
 *
 * 环境变量:
 *   CHROME_PATH       指定 Chromium 可执行文件（默认用 Playwright 自带）
 *   PLAYWRIGHT_MODULE playwright 模块路径（默认 require('playwright')）
 *   HIDE_LEFT / HIDE_RIGHT  删除左侧窄栏 / 右侧固定浮标的宽度阈值
 *   SCROLL_MARGIN     滚动时预留的上边距，默认 40
 *
 * 输出:
 *   PNG（deviceScaleFactor=2）
 *   若给 boxText：控制台打印 BOX x,y,w,h（已乘 2）
 */
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

const [, , url, out, selector, waitText, clipArg, boxText] = process.argv;

(async () => {
  if (!url || !out) {
    console.error('用法: node web_shot.js <url> <out.png> [selector] [waitText] [clip] [boxText]');
    process.exit(2);
  }

  const launchOpts = {
    headless: true,
    args: ['--disable-blink-features=AutomationControlled', '--hide-scrollbars'],
  };
  if (process.env.CHROME_PATH) launchOpts.executablePath = process.env.CHROME_PATH;

  const browser = await chromium.launch(launchOpts);
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 2,
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
      'Chrome/131.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    await page.goto(url, { timeout: 45000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);

    // 关掉常见的 cookie / 遮罩弹窗
    await page.evaluate(() => {
      const kill = [
        'button[id*="cookie" i]', 'button[class*="cookie" i]',
        'button[aria-label*="close" i]', 'button[aria-label*="Close" i]',
        'div[id*="onetrust" i]', 'div[id*="truste" i]',
        'div[aria-modal="true"]',
      ];
      for (const sel of kill) {
        document.querySelectorAll(sel).forEach((el) => el.remove());
      }
    });
    await page.waitForTimeout(800);

    // 隐藏左侧窄栏（目录）与右侧固定浮标，避免混进截图。
    // 只删小块元素，不动大容器，否则会把整棵子树带走。
    const hideLeft = Number(process.env.HIDE_LEFT || 0);
    if (hideLeft) {
      await page.evaluate((lim) => {
        document.querySelectorAll('body li, body nav, body aside').forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.width && r.width < 320 && r.x < lim) el.remove();
        });
      }, hideLeft);
      await page.waitForTimeout(300);
    }
    const hideRight = Number(process.env.HIDE_RIGHT || 0);
    if (hideRight) {
      await page.evaluate((lim) => {
        document.querySelectorAll('body *').forEach((el) => {
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          if (cs.position === 'fixed') { el.remove(); return; }
          if (r.width && r.width < 300 && r.x + r.width > lim) el.remove();
        });
      }, hideRight);
      await page.waitForTimeout(300);
    }

    if (waitText) {
      await page.waitForFunction(
        (t) => document.body.innerText.includes(t),
        waitText,
        { timeout: 20000 }
      ).catch(() => console.log('  [warn] 没等到文本: ' + waitText));
      await page.waitForTimeout(500);
    }

    fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });

    if (selector && selector.startsWith('text:')) {
      // text:关键词  -> 找包含该文本的最小元素
      // text:关键词@N -> 再往上数 N 层祖先
      const raw = selector.slice(5);
      const at = raw.lastIndexOf('@');
      const kw = at > 0 ? raw.slice(0, at) : raw;
      const up = at > 0 ? Number(raw.slice(at + 1)) : 0;
      const handle = await page.evaluateHandle(
        ([kw, up]) => {
          const els = [...document.querySelectorAll('p,li,td,th,h1,h2,h3,h4,span,div,pre,code')];
          const hits = els.filter((e) => {
            const t = e.innerText || e.textContent || '';
            return t.includes(kw) && e.getBoundingClientRect().height > 0;
          });
          if (!hits.length) return null;
          hits.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
          let e = hits[0];
          for (let i = 0; i < up; i++) e = e.parentElement;
          return e;
        },
        [kw, up]
      );
      const el = handle.asElement();
      if (!el) {
        console.log('  [fail] 没找到含 "' + kw + '" 的元素');
      } else {
        await el.screenshot({ path: out });
        const bb = await el.boundingBox();
        console.log(
          `  [ok] 元素截图 -> ${out}  区域 x=${Math.round(bb.x)} y=${Math.round(bb.y)} ` +
          `w=${Math.round(bb.width)} h=${Math.round(bb.height)}`
        );
      }
    } else if (selector) {
      const el = await page.$(selector);
      if (!el) {
        console.log('  [fail] 找不到元素: ' + selector);
        await page.screenshot({ path: out, fullPage: true });
        console.log('  已改为整页截图 -> ' + out);
      } else {
        await el.screenshot({ path: out });
        console.log('  [ok] 元素截图 -> ' + out);
      }
    } else if (clipArg) {
      const [x, y, w, h] = clipArg.split(',').map(Number);
      // 目标可能在视口外，先滚过去，再按视口坐标截
      const margin = Number(process.env.SCROLL_MARGIN || 40);
      if (y > 0) {
        await page.evaluate(
          ([ty, mg]) => window.scrollTo(0, Math.max(0, ty - mg)),
          [y, margin]
        );
        await page.waitForTimeout(700);
      }
      const sy = await page.evaluate(() => window.scrollY);
      const cy = y > 0 ? y - sy : y;
      await page.screenshot({ path: out, clip: { x, y: cy, width: w, height: h } });
      console.log(`  [ok] 区域截图 ${clipArg} (scrollY=${sy}, 实际 y=${cy}) -> ` + out);
    } else {
      await page.screenshot({ path: out, fullPage: true });
      console.log('  [ok] 整页截图 -> ' + out);
    }

    const title = await page.title();
    console.log('  页面标题: ' + title);

    // 找到要标注的文本，输出它相对截图原点的设备像素坐标
    if (boxText) {
      const info = await page.evaluate(
        ([kw, clip]) => {
          const els = [...document.querySelectorAll('p,li,td,th,h1,h2,h3,h4,span,div,pre,code,a')];
          const hits = els.filter((e) => {
            const t = e.innerText || e.textContent || '';
            const r = e.getBoundingClientRect();
            return t.includes(kw) && r.width > 20 && r.height > 4;
          });
          if (!hits.length) return null;
          // 选文本最短的，避免命中整个祖先容器
          hits.sort((a, b) => ((a.innerText || '').length) - ((b.innerText || '').length));
          const el = hits[0];
          const r = el.getBoundingClientRect();
          let ox, oy;
          if (clip) { ox = clip[0]; oy = clip[1]; }
          else { ox = -window.scrollX; oy = -window.scrollY; }  // 整页坐标
          return {
            text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70),
            box: [
              Math.round((r.x - ox) * 2), Math.round((r.y - oy) * 2),
              Math.round(r.width * 2), Math.round(r.height * 2),
            ],
          };
        },
        [boxText, clipArg ? clipArg.split(',').map(Number) : null]
      );
      if (info) {
        console.log('  标注目标: ' + info.text);
        console.log('  BOX ' + info.box.join(','));
      } else {
        console.log('  [warn] 没找到要标注的文本: ' + boxText);
      }
    }
  } catch (e) {
    console.log('  [error] ' + (e.message || e));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
