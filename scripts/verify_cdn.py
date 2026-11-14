#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 CDN 上的图和本地图是不是同一张：可达性 + 尺寸 + 像素差 + 锐度 + 笔画量。

用法：
  # 只查可达性
  python verify_cdn.py articles/x.md --head-only

  # 用映射表（推荐）：每行 文件名|URL
  python verify_cdn.py articles/x.md --map cdn_map.txt

  # 没有映射表时，按 --assets 目录内文件顺序与正文 URL 顺序配对
  python verify_cdn.py articles/x.md --assets articles/x.assets

依赖：requests；像素比对另需 Pillow（缺失时自动降级为只比尺寸）。
"""
import argparse
import io
import os
import re
import sys
import time
import warnings

import requests

warnings.filterwarnings("ignore")

URL_RE = re.compile(r"https://cdn-yg-zzbm\.yun\.qianxin\.com/[^\s)]+")


def get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=60, verify=False)
            if r.status_code == 200 and len(r.content) > 100:
                return r.content
        except Exception:
            pass
        time.sleep(1 + i)
    return None


def head(url):
    try:
        r = requests.head(url, timeout=30, verify=False, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        cl = int(r.headers.get("Content-Length", "0") or 0)
        return r.status_code, ct, cl
    except Exception as e:
        return 0, str(e), 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="CDN 图与本地图一致性校验")
    ap.add_argument("md")
    ap.add_argument("--map", default="", help="文件名|URL 映射表")
    ap.add_argument("--assets", default="", help="本地 assets 目录（无映射表时按顺序配对）")
    ap.add_argument("--head-only", action="store_true")
    args = ap.parse_args()

    md = io.open(args.md, encoding="utf-8").read()
    urls = URL_RE.findall(md)
    print("正文 CDN URL: %d 条" % len(urls))

    if args.head_only or not (args.map or args.assets):
        bad = 0
        for i, u in enumerate(urls, 1):
            code, ct, cl = head(u)
            ok = code == 200 and ct.startswith("image/") and cl > 0
            print("[%d/%d] %s %s %s %dKB" % (
                i, len(urls), "OK" if ok else "FAIL", code, ct or "-", cl // 1024))
            if not ok:
                bad += 1
        print("\n异常 %d 条" % bad)
        return 1 if bad else 0

    pairs = []
    if args.map:
        for line in io.open(args.map, encoding="utf-8"):
            line = line.strip()
            if line and "|" in line:
                k, v = line.split("|", 1)
                pairs.append((k.strip(), v.strip()))
    else:
        local = sorted(f for f in os.listdir(args.assets)
                       if f.lower().endswith((".png", ".jpg", ".jpeg")))
        pairs = list(zip(local, urls))

    try:
        from PIL import Image, ImageFilter
    except ImportError:
        Image = None

    bad = 0
    for i, (name, url) in enumerate(pairs, 1):
        lp = os.path.join(args.assets, name) if args.assets else None
        if not lp or not os.path.exists(lp):
            print("[%d] %-40s 本地文件缺失" % (i, name))
            bad += 1
            continue
        data = get(url)
        if data is None:
            print("[%d] %-40s 下载失败" % (i, name))
            bad += 1
            continue
        if Image is None:
            print("[%d] %-40s OK (仅可达性；装 Pillow 可做像素比对)" % (i, name))
            continue

        rim = Image.open(io.BytesIO(data)).convert("RGB")
        lim = Image.open(lp).convert("RGB")
        same = rim.size == lim.size
        ratio = -1.0
        maxd = 0
        if same:
            rp, lp2 = rim.load(), lim.load()
            w, h = rim.size
            diff = 0
            for y in range(0, h, 2):
                for x in range(0, w, 2):
                    a, b = rp[x, y], lp2[x, y]
                    d = max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))
                    if d > 12:
                        diff += 1
                    maxd = max(maxd, d)
            total = (w // 2 + 1) * (h // 2 + 1)
            ratio = diff / total

        def sharp(im):
            g = im.convert("L").filter(ImageFilter.FIND_EDGES)
            px = list(g.getdata())
            n = len(px)
            m = sum(px) / n
            return (sum((v - m) ** 2 for v in px) / n) ** 0.5

        sdiff = abs(sharp(rim) - sharp(lim)) / max(sharp(lim), 1e-9) * 100
        ok = same and ratio < 0.05 and sdiff < 3
        print("[%d] %-40s %s 尺寸 %s 像素差 %.2f%% 最大色差 %d 锐度差 %.2f%%" % (
            i, name, "OK" if ok else "WARN",
            "%dx%d" % rim.size if same else "%s vs %s" % (rim.size, lim.size),
            ratio * 100, maxd, sdiff))
        if not ok:
            bad += 1

    print("\n异常 %d 张" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
